"""Tests for jepa_v2/probes.py — CPU only, fast (<20 s total).

Covers: calibration metrics, temperature scaling, linear probe, group k-fold
probe, permutation AUROC, leakage guard, RankMe, kNN accuracy, delta_pos R²,
and the markdown report helper.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import pytest
from numpy.typing import NDArray

from Programma_CS2_RENAN.backend.nn.jepa_v2.probes import (
    GroupProbeResult,
    ProbeResult,
    apply_temperature,
    brier_score,
    brier_skill_score,
    delta_pos_r2,
    expected_calibration_error,
    fit_linear_probe,
    fit_temperature,
    group_kfold_probe,
    knn_accuracy,
    leakage_guard,
    markdown_report,
    max_calibration_error,
    negative_log_likelihood,
    permutation_auroc,
    rankme,
)

SEED = 42


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def balanced_binary_data() -> Tuple[NDArray, NDArray, NDArray, NDArray, NDArray]:
    """Separable 2-class data with ~50/50 prevalence and 6 groups."""
    rng = np.random.default_rng(SEED)
    n = 600
    d = 16
    y = np.array([0] * (n // 2) + [1] * (n // 2))
    x = rng.standard_normal((n, d))
    x[y == 1] += 2.0
    groups = np.tile(np.arange(6), n // 6)
    # Shuffle all arrays together so train/val splits have both classes.
    idx = rng.permutation(n)
    x, y, groups = x[idx], y[idx], groups[idx]
    return x, y, groups, x, y


@pytest.fixture()
def perfectly_calibrated_probs() -> Tuple[NDArray, NDArray]:
    """Probabilities and labels where labels ~ Bernoulli(p) (well-calibrated)."""
    rng = np.random.default_rng(SEED)
    n = 20_000
    p = rng.uniform(0.1, 0.9, n)
    y = (rng.random(n) < p).astype(np.float64)
    return p, y


# ---------------------------------------------------------------------------
# ECE tests
# ---------------------------------------------------------------------------
class TestCalibrationMetrics:
    def test_ece_perfect_is_near_zero(
        self, perfectly_calibrated_probs: Tuple[NDArray, NDArray]
    ) -> None:
        p, y = perfectly_calibrated_probs
        ece = expected_calibration_error(p, y, strategy="width")
        assert ece < 0.02, f"ECE on perfectly calibrated data too high: {ece}"

    def test_ece_equal_mass_near_zero(
        self, perfectly_calibrated_probs: Tuple[NDArray, NDArray]
    ) -> None:
        p, y = perfectly_calibrated_probs
        ece = expected_calibration_error(p, y, strategy="mass")
        assert ece < 0.02, f"ECE-mass on perfectly calibrated data: {ece}"

    def test_ece_all_wrong_is_large(self) -> None:
        p = np.ones(100)
        y = np.zeros(100)
        ece = expected_calibration_error(p, y, strategy="width")
        assert ece > 0.9

    def test_mce_perfect_near_zero(
        self, perfectly_calibrated_probs: Tuple[NDArray, NDArray]
    ) -> None:
        p, y = perfectly_calibrated_probs
        mce = max_calibration_error(p, y)
        assert mce < 0.05

    def test_mce_all_wrong(self) -> None:
        p = np.ones(100)
        y = np.zeros(100)
        mce = max_calibration_error(p, y)
        assert mce > 0.9

    def test_brier_perfect(self) -> None:
        y = np.array([0, 1, 1, 0])
        p = np.array([0.0, 1.0, 1.0, 0.0])
        assert brier_score(p, y) == pytest.approx(0.0)

    def test_brier_skill_positive_for_good_pred(self) -> None:
        rng = np.random.default_rng(SEED)
        y = rng.integers(0, 2, 1000).astype(float)
        p = y * 0.8 + (1 - y) * 0.2
        bss = brier_skill_score(p, y)
        assert bss > 0.0

    def test_nll_perfect_near_zero(self) -> None:
        y = np.array([0, 1, 1, 0], dtype=float)
        p = np.array([1e-10, 1.0 - 1e-10, 1.0 - 1e-10, 1e-10])
        nll = negative_log_likelihood(p, y)
        assert nll < 0.001

    def test_ece_empty(self) -> None:
        assert expected_calibration_error(np.array([]), np.array([])) == 0.0

    def test_ece_invalid_strategy(self) -> None:
        with pytest.raises(ValueError, match="Unknown strategy"):
            expected_calibration_error(np.array([0.5]), np.array([1]), strategy="bad")


# ---------------------------------------------------------------------------
# Temperature scaling tests
# ---------------------------------------------------------------------------
class TestTemperatureScaling:
    def test_fit_temperature_reduces_nll(self) -> None:
        rng = np.random.default_rng(SEED)
        n = 2000
        y = rng.integers(0, 2, n).astype(float)
        logits = y * 4.0 - 2.0 + rng.standard_normal(n) * 0.5
        t = fit_temperature(logits, y)
        nll_fitted = negative_log_likelihood(apply_temperature(logits, t), y)
        nll_uncal = negative_log_likelihood(apply_temperature(logits, 1.0), y)
        assert nll_fitted <= nll_uncal + 1e-9

    def test_fit_temperature_recovers_scaling(self) -> None:
        rng = np.random.default_rng(SEED)
        n = 10_000
        p = rng.uniform(0.05, 0.95, n)
        y = (rng.random(n) < p).astype(np.float64)
        logits = np.log(p / (1.0 - p))
        k = 3.0
        t = fit_temperature(logits * k, y)
        assert abs(t - k) < 1.0, f"Expected T≈{k}, got {t}"

    def test_temperature_preserves_binary_decision(
        self, balanced_binary_data: Tuple[NDArray, ...]
    ) -> None:
        x, y, groups, _, _ = balanced_binary_data
        n = len(y)
        mid = n // 2
        result = fit_linear_probe(x[:mid], y[:mid], x[mid:], y[mid:], seed=SEED)
        np.testing.assert_array_equal(result.probs_raw > 0.5, result.probs_calibrated > 0.5)

    def test_temperature_one_is_sigmoid(self) -> None:
        logits = np.array([-1.0, 0.0, 1.0])
        p = apply_temperature(logits, 1.0)
        expected = 1.0 / (1.0 + np.exp(-logits))
        np.testing.assert_allclose(p, expected, atol=1e-12)


# ---------------------------------------------------------------------------
# Linear probe tests
# ---------------------------------------------------------------------------
class TestLinearProbe:
    def test_fit_linear_probe_separable(self, balanced_binary_data: Tuple[NDArray, ...]) -> None:
        x, y, groups, _, _ = balanced_binary_data
        n = len(y)
        mid = n // 2
        result = fit_linear_probe(x[:mid], y[:mid], x[mid:], y[mid:], seed=SEED)
        assert isinstance(result, ProbeResult)
        assert result.auroc > 0.8
        assert result.temperature > 0.0
        assert len(result.probs_raw) == n - mid

    def test_probe_result_frozen(self, balanced_binary_data: Tuple[NDArray, ...]) -> None:
        x, y, *_ = balanced_binary_data
        n = len(y)
        mid = n // 2
        result = fit_linear_probe(x[:mid], y[:mid], x[mid:], y[mid:], seed=SEED)
        with pytest.raises(AttributeError):
            result.auroc = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Group k-fold probe tests
# ---------------------------------------------------------------------------
class TestGroupKFoldProbe:
    def test_kfold_separable(self, balanced_binary_data: Tuple[NDArray, ...]) -> None:
        x, y, groups, _, _ = balanced_binary_data
        result = group_kfold_probe(x, y, groups, seed=SEED)
        assert isinstance(result, GroupProbeResult)
        assert result.auroc_mean > 0.8
        assert result.n_folds_used == 5
        assert len(result.auroc_per_fold) == 5

    def test_kfold_all_skipped(self, caplog: pytest.LogCaptureFixture) -> None:
        rng = np.random.default_rng(SEED)
        n = 300
        x = rng.standard_normal((n, 8))
        y = np.zeros(n, dtype=int)
        groups = np.tile(np.arange(5), n // 5)
        with caplog.at_level(logging.WARNING):
            result = group_kfold_probe(x, y, groups, seed=SEED)
        assert result.n_folds_used == 0
        assert result.auroc_mean == 0.0
        assert "skipped" in caplog.text.lower()

    def test_kfold_oof_coverage(self, balanced_binary_data: Tuple[NDArray, ...]) -> None:
        from sklearn.metrics import roc_auc_score

        x, y, groups, _, _ = balanced_binary_data
        result = group_kfold_probe(x, y, groups, seed=SEED)
        assert result.oof_mask.all(), "GroupKFold(5) should cover every sample"
        pooled_auc = roc_auc_score(
            result.oof_labels[result.oof_mask], result.oof_probs[result.oof_mask]
        )
        assert pooled_auc > 0.8

    def test_kfold_partial_skip(self, caplog: pytest.LogCaptureFixture) -> None:
        rng = np.random.default_rng(SEED)
        n = 300
        x = rng.standard_normal((n, 8))
        y = np.zeros(n, dtype=int)
        groups = np.tile(np.arange(6), n // 6)
        # positives only in 2 of 6 groups -> some folds have single class
        g0_mask = groups == 0
        g1_mask = groups == 1
        y[g0_mask] = 1
        y[g1_mask] = 1
        x[y == 1] += 3.0
        with caplog.at_level(logging.WARNING):
            result = group_kfold_probe(x, y, groups, seed=SEED, n_splits=5)
        assert 0 < result.n_folds_used < 5


# ---------------------------------------------------------------------------
# Permutation AUROC tests
# ---------------------------------------------------------------------------
class TestPermutationAuroc:
    def test_permutation_near_chance(self, balanced_binary_data: Tuple[NDArray, ...]) -> None:
        x, y, groups, _, _ = balanced_binary_data
        perm_auc = permutation_auroc(x, y, groups, seed=SEED)
        assert 0.35 < perm_auc < 0.65, f"Permutation AUROC not near 0.5: {perm_auc}"


# ---------------------------------------------------------------------------
# Leakage guard tests (Parte I §7.8, §3.8; A-39)
# ---------------------------------------------------------------------------
class TestLeakageGuard:
    def test_side_flagged(self) -> None:
        """'side' is both a schema categorical and a probe label -> flagged."""
        label_sources = frozenset({"side", "round_won"})
        schema = frozenset({"health", "armor", "side", "enemies_visible"})
        is_clean, offenders = leakage_guard(label_sources, schema)
        assert not is_clean
        assert "side" in offenders

    def test_future_derived_allowed(self) -> None:
        """death_within_2s derives from health (future) but is in allow_future."""
        label_sources = frozenset({"death_within_2s", "contact_new_within_2s"})
        schema = frozenset({"health", "enemies_visible"})
        is_clean, offenders = leakage_guard(
            label_sources,
            schema,
            allow_future=frozenset({"death_within_2s", "contact_new_within_2s"}),
        )
        assert is_clean
        assert len(offenders) == 0

    def test_clean_labels(self) -> None:
        label_sources = frozenset({"round_won", "opening_death"})
        schema = frozenset({"health", "armor", "pos_x"})
        is_clean, offenders = leakage_guard(label_sources, schema)
        assert is_clean
        assert len(offenders) == 0

    def test_mixed_leakage_and_future(self) -> None:
        label_sources = frozenset({"side", "death_within_2s"})
        schema = frozenset({"side", "health"})
        is_clean, offenders = leakage_guard(
            label_sources, schema, allow_future=frozenset({"death_within_2s"})
        )
        assert not is_clean
        assert offenders == frozenset({"side"})


# ---------------------------------------------------------------------------
# RankMe tests
# ---------------------------------------------------------------------------
class TestRankMe:
    def test_rank_8_matrix(self) -> None:
        """A rank-8 matrix embedded in 64-d should have RankMe ~8."""
        rng = np.random.default_rng(SEED)
        base = rng.standard_normal((4096, 8))
        q, _ = np.linalg.qr(rng.standard_normal((64, 8)), mode="reduced")
        z = base @ q.T
        r = rankme(z)
        assert 7.0 < r < 9.0, f"RankMe for rank-8: {r}"

    def test_isotropic_gaussian_high_rank(self) -> None:
        """Isotropic Gaussian in 128-d should have RankMe >= 60."""
        rng = np.random.default_rng(SEED)
        z = rng.standard_normal((4096, 128)).astype(np.float32)
        r = rankme(z)
        assert r >= 60, f"RankMe for isotropic Gaussian 128-d: {r}"

    def test_collapsed_low_rank(self) -> None:
        """Near-constant embeddings should have low RankMe."""
        z = (
            np.ones((100, 32), dtype=np.float32)
            + np.random.default_rng(SEED).standard_normal((100, 32)) * 1e-6
        )
        r = rankme(z)
        assert r < 5.0, f"RankMe for near-constant: {r}"

    def test_few_samples_returns_zero(self) -> None:
        z = np.array([[1.0, 2.0]], dtype=np.float32)
        r = rankme(z)
        assert r == 0.0


# ---------------------------------------------------------------------------
# kNN accuracy tests
# ---------------------------------------------------------------------------
class TestKnnAccuracy:
    def test_knn_separable(self, balanced_binary_data: Tuple[NDArray, ...]) -> None:
        x, y, groups, _, _ = balanced_binary_data
        n = len(y)
        mid = n // 2
        acc = knn_accuracy(x[:mid], y[:mid], x[mid:], y[mid:])
        assert acc > 0.7


# ---------------------------------------------------------------------------
# Delta-position R² tests
# ---------------------------------------------------------------------------
class TestDeltaPosR2:
    def test_predictable_target(self) -> None:
        rng = np.random.default_rng(SEED)
        n = 500
        d = 16
        x = rng.standard_normal((n, d))
        w = rng.standard_normal(d)
        y = x @ w + rng.standard_normal(n) * 0.1
        groups = np.tile(np.arange(5), n // 5)
        r2 = delta_pos_r2(x, y, groups, seed=SEED)
        assert r2 > 0.8

    def test_noise_target_low_r2(self) -> None:
        rng = np.random.default_rng(SEED)
        n = 500
        d = 16
        x = rng.standard_normal((n, d))
        y = rng.standard_normal(n)
        groups = np.tile(np.arange(5), n // 5)
        r2 = delta_pos_r2(x, y, groups, seed=SEED)
        assert r2 < 0.05, f"Noise R² too high: {r2}"

    def test_without_groups(self) -> None:
        rng = np.random.default_rng(SEED)
        n = 500
        d = 8
        x = rng.standard_normal((n, d))
        w = rng.standard_normal(d)
        y = x @ w + rng.standard_normal(n) * 0.1
        r2 = delta_pos_r2(x, y, seed=SEED)
        assert r2 > 0.8


# ---------------------------------------------------------------------------
# Report helper tests
# ---------------------------------------------------------------------------
class TestMarkdownReport:
    def test_report_contains_rankme(self) -> None:
        result = GroupProbeResult(
            auroc_mean=0.85,
            auroc_std=0.02,
            auroc_per_fold=[0.83, 0.85, 0.87],
            ece_mean=0.01,
            temperature_mean=1.5,
            ece_calibrated_mean=0.005,
            n_folds_used=3,
            oof_probs=np.zeros(10),
            oof_labels=np.zeros(10),
            oof_mask=np.ones(10, dtype=bool),
        )
        md = markdown_report({"round_won": result}, rankme_value=72.5)
        assert "72.50" in md
        assert "round_won" in md
        assert "AUROC" in md

    def test_report_with_extra(self) -> None:
        result = GroupProbeResult(
            auroc_mean=0.85,
            auroc_std=0.02,
            auroc_per_fold=[0.85],
            ece_mean=0.01,
            temperature_mean=1.0,
            ece_calibrated_mean=0.01,
            n_folds_used=1,
            oof_probs=np.zeros(5),
            oof_labels=np.zeros(5),
            oof_mask=np.ones(5, dtype=bool),
        )
        md = markdown_report(
            {"test": result},
            rankme_value=64.0,
            extra={"knn_accuracy": 0.91},
        )
        assert "knn_accuracy" in md
        assert "0.9100" in md
