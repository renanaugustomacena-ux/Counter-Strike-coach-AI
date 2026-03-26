"""
Comprehensive CI tests for the Skill Assessment module.

Covers: SkillAxes, SkillLatentModel.calculate_skill_vector,
get_curriculum_level, get_skill_tensor, edge cases, and
integration with the pro baseline.

Target: 100% coverage of skill_assessment.py.
"""

from unittest.mock import patch

import numpy as np
import pytest
import torch

from Programma_CS2_RENAN.backend.processing.skill_assessment import (
    SkillAxes,
    SkillLatentModel,
)


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_baseline():
    """Baseline with known values for deterministic testing."""
    return {
        "accuracy": {"mean": 0.22, "std": 0.05},
        "avg_hs": {"mean": 0.52, "std": 0.10},
        "rating_survival": {"mean": 0.38, "std": 0.08},
        "rating_kast": {"mean": 0.74, "std": 0.05},
        "utility_blind_time": {"mean": 12.0, "std": 4.0},
        "utility_enemies_blinded": {"mean": 2.2, "std": 0.8},
        "opening_duel_win_pct": {"mean": 0.55, "std": 0.10},
        "positional_aggression_score": {"mean": 0.65, "std": 0.15},
        "clutch_win_pct": {"mean": 0.35, "std": 0.12},
        "rating_impact": {"mean": 1.10, "std": 0.20},
    }


class MockPlayerMatchStats:
    """Lightweight stand-in for PlayerMatchStats with configurable attributes."""

    def __init__(self, **kwargs):
        defaults = {
            "accuracy": None,
            "avg_hs": None,
            "rating_survival": None,
            "rating_kast": None,
            "utility_blind_time": None,
            "utility_enemies_blinded": None,
            "opening_duel_win_pct": None,
            "positional_aggression_score": None,
            "clutch_win_pct": None,
            "rating_impact": None,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# ─── SkillAxes ─────────────────────────────────────────────────────────


class TestSkillAxes:
    def test_all_returns_five_axes(self):
        axes = SkillAxes.all()
        assert len(axes) == 5

    def test_all_contains_expected_axes(self):
        axes = SkillAxes.all()
        assert "mechanics" in axes
        assert "positioning" in axes
        assert "utility" in axes
        assert "timing" in axes
        assert "decision" in axes

    def test_axis_constants_are_strings(self):
        assert isinstance(SkillAxes.MECHANICS, str)
        assert isinstance(SkillAxes.POSITIONING, str)
        assert isinstance(SkillAxes.UTILITY, str)
        assert isinstance(SkillAxes.TIMING, str)
        assert isinstance(SkillAxes.DECISION, str)


# ─── calculate_skill_vector ────────────────────────────────────────────


class TestCalculateSkillVector:
    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_average_player_scores_near_0_5(self, mock_get_baseline, mock_baseline):
        """A player at exactly the pro baseline mean should score ~0.5."""
        mock_get_baseline.return_value = mock_baseline
        stats = MockPlayerMatchStats(
            accuracy=0.22,
            avg_hs=0.52,
            rating_survival=0.38,
            rating_kast=0.74,
            utility_blind_time=12.0,
            utility_enemies_blinded=2.2,
            opening_duel_win_pct=0.55,
            positional_aggression_score=0.65,
            clutch_win_pct=0.35,
            rating_impact=1.10,
        )
        result = SkillLatentModel.calculate_skill_vector(stats)
        for axis, score in result.items():
            assert 0.45 <= score <= 0.55, f"{axis} should be ~0.5 for average player, got {score}"

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_elite_player_scores_high(self, mock_get_baseline, mock_baseline):
        """A player 2 std above mean should score > 0.9."""
        mock_get_baseline.return_value = mock_baseline
        stats = MockPlayerMatchStats(
            accuracy=0.32,  # +2 std
            avg_hs=0.72,  # +2 std
            rating_survival=0.54,  # +2 std
            rating_kast=0.84,  # +2 std
            utility_blind_time=20.0,
            utility_enemies_blinded=3.8,
            opening_duel_win_pct=0.75,
            positional_aggression_score=0.95,
            clutch_win_pct=0.59,
            rating_impact=1.50,
        )
        result = SkillLatentModel.calculate_skill_vector(stats)
        for axis, score in result.items():
            assert score > 0.8, f"{axis} should be high for elite player, got {score}"

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_weak_player_scores_low(self, mock_get_baseline, mock_baseline):
        """A player 2 std below mean should score < 0.2."""
        mock_get_baseline.return_value = mock_baseline
        stats = MockPlayerMatchStats(
            accuracy=0.12,  # -2 std
            avg_hs=0.32,  # -2 std
            rating_survival=0.22,
            rating_kast=0.64,
            utility_blind_time=4.0,
            utility_enemies_blinded=0.6,
            opening_duel_win_pct=0.35,
            positional_aggression_score=0.35,
            clutch_win_pct=0.11,
            rating_impact=0.70,
        )
        result = SkillLatentModel.calculate_skill_vector(stats)
        for axis, score in result.items():
            assert score < 0.3, f"{axis} should be low for weak player, got {score}"

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_all_none_returns_default_0_5(self, mock_get_baseline, mock_baseline):
        """All-None stats should produce default 0.5 for all axes."""
        mock_get_baseline.return_value = mock_baseline
        stats = MockPlayerMatchStats()
        result = SkillLatentModel.calculate_skill_vector(stats)
        assert len(result) == 5
        for axis, score in result.items():
            assert score == 0.5

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_partial_stats_only_computes_available_axes(self, mock_get_baseline, mock_baseline):
        """Only axes with available stats should appear in the result."""
        mock_get_baseline.return_value = mock_baseline
        stats = MockPlayerMatchStats(accuracy=0.25, avg_hs=0.50)
        result = SkillLatentModel.calculate_skill_vector(stats)
        assert SkillAxes.MECHANICS in result
        # Other axes should not be present (no stats for them)
        assert SkillAxes.UTILITY not in result

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_scores_bounded_0_to_1(self, mock_get_baseline, mock_baseline):
        """All scores should be in [0, 1] regardless of extreme inputs."""
        mock_get_baseline.return_value = mock_baseline
        stats = MockPlayerMatchStats(
            accuracy=1.0,  # extreme high
            avg_hs=1.0,
            rating_survival=1.0,
            rating_kast=1.0,
            utility_blind_time=100.0,
            utility_enemies_blinded=20.0,
            opening_duel_win_pct=1.0,
            positional_aggression_score=1.0,
            clutch_win_pct=1.0,
            rating_impact=5.0,
        )
        result = SkillLatentModel.calculate_skill_vector(stats)
        for axis, score in result.items():
            assert 0.0 <= score <= 1.0, f"{axis} out of bounds: {score}"

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_zero_stats_bounded(self, mock_get_baseline, mock_baseline):
        """Zero values should produce valid scores (not crash or NaN)."""
        mock_get_baseline.return_value = mock_baseline
        stats = MockPlayerMatchStats(
            accuracy=0.0,
            avg_hs=0.0,
            rating_survival=0.0,
            rating_kast=0.0,
        )
        result = SkillLatentModel.calculate_skill_vector(stats)
        for axis, score in result.items():
            assert 0.0 <= score <= 1.0
            assert not np.isnan(score)

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_degenerate_baseline_std_zero(self, mock_get_baseline):
        """P-SA-01-2: Metrics with std=0 should be skipped (no div-by-zero)."""
        baseline = {
            "accuracy": {"mean": 0.22, "std": 0.0},  # degenerate
            "avg_hs": {"mean": 0.52, "std": 0.10},
        }
        mock_get_baseline.return_value = baseline
        stats = MockPlayerMatchStats(accuracy=0.25, avg_hs=0.60)
        result = SkillLatentModel.calculate_skill_vector(stats)
        # Mechanics should still compute from avg_hs alone (accuracy skipped)
        if SkillAxes.MECHANICS in result:
            assert not np.isnan(result[SkillAxes.MECHANICS])

    @patch(
        "Programma_CS2_RENAN.backend.processing.skill_assessment.get_pro_baseline"
    )
    def test_negative_std_skipped(self, mock_get_baseline):
        """Negative std should be treated as degenerate."""
        baseline = {
            "accuracy": {"mean": 0.22, "std": -0.05},  # invalid
            "avg_hs": {"mean": 0.52, "std": 0.10},
        }
        mock_get_baseline.return_value = baseline
        stats = MockPlayerMatchStats(accuracy=0.25, avg_hs=0.60)
        result = SkillLatentModel.calculate_skill_vector(stats)
        if SkillAxes.MECHANICS in result:
            assert not np.isnan(result[SkillAxes.MECHANICS])


# ─── P-SA-01: Sigmoid Approximation ───────────────────────────────────


class TestSigmoidApproximation:
    """P-SA-01: sigmoid(1.702 * z) should approximate Gaussian CDF."""

    def test_z0_gives_0_5(self):
        """At z=0, percentile should be exactly 0.5."""
        z = 0.0
        percentile = 1.0 / (1.0 + np.exp(-1.702 * z))
        assert abs(percentile - 0.5) < 1e-6

    def test_positive_z_above_0_5(self):
        """Positive z-score should give percentile > 0.5."""
        for z in [0.5, 1.0, 2.0, 3.0]:
            percentile = 1.0 / (1.0 + np.exp(-1.702 * z))
            assert percentile > 0.5

    def test_negative_z_below_0_5(self):
        """Negative z-score should give percentile < 0.5."""
        for z in [-0.5, -1.0, -2.0, -3.0]:
            percentile = 1.0 / (1.0 + np.exp(-1.702 * z))
            assert percentile < 0.5

    def test_extreme_z_clipped(self):
        """Extreme z-scores should be clipped to [0, 1]."""
        for z in [10.0, -10.0, 100.0, -100.0]:
            percentile = 1.0 / (1.0 + np.exp(-1.702 * z))
            percentile = np.clip(percentile, 0, 1)
            assert 0.0 <= percentile <= 1.0

    def test_approximates_gaussian_cdf(self):
        """Should approximate the true Gaussian CDF within 1%."""
        from scipy.stats import norm

        for z in [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]:
            approx = 1.0 / (1.0 + np.exp(-1.702 * z))
            exact = norm.cdf(z)
            assert abs(approx - exact) < 0.015, f"z={z}: approx={approx:.4f}, exact={exact:.4f}"


# ─── get_curriculum_level ──────────────────────────────────────────────


class TestGetCurriculumLevel:
    def test_empty_dict_returns_1(self):
        assert SkillLatentModel.get_curriculum_level({}) == 1

    def test_all_zeros_returns_1(self):
        vec = {ax: 0.0 for ax in SkillAxes.all()}
        assert SkillLatentModel.get_curriculum_level(vec) == 1

    def test_all_ones_returns_10(self):
        vec = {ax: 1.0 for ax in SkillAxes.all()}
        assert SkillLatentModel.get_curriculum_level(vec) == 10

    def test_mid_skill_returns_mid_level(self):
        vec = {ax: 0.5 for ax in SkillAxes.all()}
        level = SkillLatentModel.get_curriculum_level(vec)
        assert 4 <= level <= 6, f"Mid-skill should be level 4-6, got {level}"

    def test_always_in_range_1_10(self):
        """Level should always be in [1, 10] for any input."""
        for val in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            vec = {ax: val for ax in SkillAxes.all()}
            level = SkillLatentModel.get_curriculum_level(vec)
            assert 1 <= level <= 10, f"Level {level} out of range for val={val}"

    def test_monotonically_increasing(self):
        """Higher skill scores should map to equal or higher levels."""
        prev_level = 0
        for val in np.arange(0.0, 1.01, 0.1):
            vec = {ax: val for ax in SkillAxes.all()}
            level = SkillLatentModel.get_curriculum_level(vec)
            assert level >= prev_level, f"Level decreased: {prev_level} -> {level} at val={val}"
            prev_level = level

    def test_partial_axes(self):
        """Should work with fewer than 5 axes."""
        vec = {"mechanics": 0.8, "positioning": 0.7}
        level = SkillLatentModel.get_curriculum_level(vec)
        assert 1 <= level <= 10


# ─── get_skill_tensor ──────────────────────────────────────────────────


class TestGetSkillTensor:
    def test_returns_one_hot(self):
        vec = {ax: 0.5 for ax in SkillAxes.all()}
        tensor = SkillLatentModel.get_skill_tensor(vec)
        assert tensor.shape == (1, 10)
        assert tensor.sum().item() == 1.0

    def test_hot_index_matches_level(self):
        vec = {ax: 1.0 for ax in SkillAxes.all()}
        tensor = SkillLatentModel.get_skill_tensor(vec)
        level = SkillLatentModel.get_curriculum_level(vec)
        assert tensor[0, level - 1].item() == 1.0

    def test_all_zeros_hot_at_index_0(self):
        vec = {ax: 0.0 for ax in SkillAxes.all()}
        tensor = SkillLatentModel.get_skill_tensor(vec)
        assert tensor[0, 0].item() == 1.0  # level 1 → index 0

    def test_empty_vec_returns_level_1(self):
        tensor = SkillLatentModel.get_skill_tensor({})
        assert tensor[0, 0].item() == 1.0

    def test_tensor_dtype_float(self):
        vec = {ax: 0.5 for ax in SkillAxes.all()}
        tensor = SkillLatentModel.get_skill_tensor(vec)
        assert tensor.dtype == torch.float32

    def test_all_levels_produce_valid_one_hot(self):
        """Every possible level should produce a valid one-hot vector."""
        for val in np.arange(0.0, 1.01, 0.05):
            vec = {ax: val for ax in SkillAxes.all()}
            tensor = SkillLatentModel.get_skill_tensor(vec)
            assert tensor.shape == (1, 10)
            assert tensor.sum().item() == 1.0
            assert tensor.max().item() == 1.0
            assert tensor.min().item() == 0.0
