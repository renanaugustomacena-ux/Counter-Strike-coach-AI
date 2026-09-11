"""Probe and calibration toolkit for JEPA v2 evaluation.

Self-contained: numpy + scikit-learn; torch only for ``rankme`` (via
``collapse_metrics``). No imports from the rest of ``jepa_v2``.

Probe protocol (CORREZIONE_NUCLEO_NEURALE Parte I §7.8, §3.8;
Parte III §5.1): StandardScaler + LogisticRegression(C=1, class_weight="balanced",
max_iter=3000), GroupKFold(5) by demo, temperature scaling (Guo 2017),
ECE M=15 equal-width bins.

Calibration protocol (Parte II §9.1-9.3; Parte III §5.1): ECE, MCE, Brier,
Brier skill score, NLL; temperature T fitted by minimising NLL on validation
logits (bounded golden-section search, no scipy). ``class_weight="balanced"``
shifts the intercept (B12): AUROC is unaffected but post-temperature
probabilities carry the prior shift. Both balanced AUROC and calibrated
probabilities after temperature scaling are reported.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (Parte II §9.1; Parte III §5.1; C-18)
# ---------------------------------------------------------------------------
ECE_BINS: int = 15
LR_C: float = 1.0
LR_MAX_ITER: int = 3000
GKFOLD_SPLITS: int = 5
KNN_K: int = 20

# Temperature bounds: parametrise as w = 1/T so NLL is convex in w.
_W_LO: float = 1.0 / 20.0  # T_max = 20
_W_HI: float = 20.0  # T_min = 0.05


# ---------------------------------------------------------------------------
# Calibration metrics (Parte II §9.1-9.3)
# ---------------------------------------------------------------------------
def expected_calibration_error(
    probs: NDArray[np.floating],
    labels: NDArray[np.integer | np.floating],
    n_bins: int = ECE_BINS,
    strategy: str = "width",
) -> float:
    """ECE with equal-width or equal-mass bins (Guo 2017 eq. 3).

    Args:
        probs: predicted probabilities in [0, 1].
        labels: binary ground truth {0, 1}.
        n_bins: number of bins (default 15, Parte II §9.1).
        strategy: ``"width"`` (equal-width) or ``"mass"`` (equal-mass / quantile).

    Returns:
        ECE as a float in [0, 1].
    """
    p = np.asarray(probs, dtype=np.float64).ravel()
    y = np.asarray(labels, dtype=np.float64).ravel()
    n = len(p)
    if n == 0:
        return 0.0
    if strategy == "width":
        edges = np.linspace(0.0, 1.0, n_bins + 1)
        b = np.clip(np.digitize(p, edges[1:-1], right=False), 0, n_bins - 1)
        sy = np.bincount(b, weights=y, minlength=n_bins)
        sp = np.bincount(b, weights=p, minlength=n_bins)
        return float(np.abs(sy - sp).sum() / n)
    if strategy == "mass":
        order = np.argsort(p, kind="stable")
        tot = 0.0
        for chunk in np.array_split(order, n_bins):
            if len(chunk):
                tot += abs(float(y[chunk].sum()) - float(p[chunk].sum()))
        return float(tot / n)
    raise ValueError(f"Unknown strategy {strategy!r}; use 'width' or 'mass'.")


def max_calibration_error(
    probs: NDArray[np.floating],
    labels: NDArray[np.integer | np.floating],
    n_bins: int = ECE_BINS,
) -> float:
    """MCE: max per-bin |mean(y) - mean(p)| (Guo 2017 eq. 5)."""
    p = np.asarray(probs, dtype=np.float64).ravel()
    y = np.asarray(labels, dtype=np.float64).ravel()
    n = len(p)
    if n == 0:
        return 0.0
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    b = np.clip(np.digitize(p, edges[1:-1], right=False), 0, n_bins - 1)
    counts = np.bincount(b, minlength=n_bins).astype(np.float64)
    sy = np.bincount(b, weights=y, minlength=n_bins)
    sp = np.bincount(b, weights=p, minlength=n_bins)
    mask = counts > 0
    if not mask.any():
        return 0.0
    per_bin = np.abs(sy[mask] / counts[mask] - sp[mask] / counts[mask])
    return float(per_bin.max())


def brier_score(
    probs: NDArray[np.floating],
    labels: NDArray[np.integer | np.floating],
) -> float:
    """Mean squared error between predicted probabilities and binary labels."""
    p = np.asarray(probs, dtype=np.float64).ravel()
    y = np.asarray(labels, dtype=np.float64).ravel()
    return float(np.mean((p - y) ** 2))


def brier_skill_score(
    probs: NDArray[np.floating],
    labels: NDArray[np.integer | np.floating],
) -> float:
    """Brier skill score vs the constant (prevalence) predictor. 1 = perfect."""
    p = np.asarray(probs, dtype=np.float64).ravel()
    y = np.asarray(labels, dtype=np.float64).ravel()
    bs = float(np.mean((p - y) ** 2))
    prevalence = float(y.mean())
    bs_ref = float(np.mean((prevalence - y) ** 2))
    if bs_ref == 0.0:
        return 0.0
    return 1.0 - bs / bs_ref


def negative_log_likelihood(
    probs: NDArray[np.floating],
    labels: NDArray[np.integer | np.floating],
    eps: float = 1e-15,
) -> float:
    """Mean binary NLL (cross-entropy)."""
    p = np.clip(np.asarray(probs, dtype=np.float64).ravel(), eps, 1.0 - eps)
    y = np.asarray(labels, dtype=np.float64).ravel()
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


# ---------------------------------------------------------------------------
# Temperature scaling (Guo 2017; Parte II §9.1-9.3)
# ---------------------------------------------------------------------------
def _nll_at_w(logits: NDArray, y: NDArray, w: float) -> float:
    """NLL of sigmoid(w * logits) vs y. Convex in w."""
    z = w * logits
    return float(np.mean(np.logaddexp(0.0, -z * (2.0 * y - 1.0))))


def fit_temperature(
    logits: NDArray[np.floating],
    labels: NDArray[np.integer | np.floating],
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float:
    """Fit temperature T minimising NLL on validation logits (Guo 2017).

    Parametrised as w = 1/T; golden-section search on w in [1/20, 20].
    NLL is convex in w so the global minimum is guaranteed.

    Returns:
        T (positive float). T > 1 means the model is overconfident.
    """
    z = np.asarray(logits, dtype=np.float64).ravel()
    y = np.asarray(labels, dtype=np.float64).ravel()

    gr = (math.sqrt(5.0) + 1.0) / 2.0
    a, b = _W_LO, _W_HI
    c = b - (b - a) / gr
    d = a + (b - a) / gr
    for _ in range(max_iter):
        if abs(b - a) < tol:
            break
        if _nll_at_w(z, y, c) < _nll_at_w(z, y, d):
            b = d
        else:
            a = c
        c = b - (b - a) / gr
        d = a + (b - a) / gr
    w_star = (a + b) / 2.0
    return 1.0 / w_star


def apply_temperature(
    logits: NDArray[np.floating],
    temperature: float,
) -> NDArray[np.float64]:
    """Apply temperature scaling: probabilities = sigmoid(logits / T)."""
    z = np.asarray(logits, dtype=np.float64).ravel() / temperature
    return 1.0 / (1.0 + np.exp(-z))


# ---------------------------------------------------------------------------
# Linear probe (Parte I §7.8; Parte III §5.1; C-18)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, eq=False)
class ProbeResult:
    """Result of a single train/val linear probe."""

    auroc: float
    ece: float
    mce: float
    brier: float
    brier_skill: float
    nll: float
    temperature: float
    ece_calibrated: float
    probs_raw: NDArray[np.float64]
    probs_calibrated: NDArray[np.float64]
    labels_val: NDArray[np.float64]


def fit_linear_probe(
    z_train: NDArray[np.floating],
    y_train: NDArray[np.integer | np.floating],
    z_val: NDArray[np.floating],
    y_val: NDArray[np.integer | np.floating],
    *,
    seed: int = 0,
) -> ProbeResult:
    """Fit a linear probe and return calibration metrics.

    StandardScaler + LogisticRegression(C=1, class_weight="balanced",
    max_iter=3000) (Parte III §5.1). Temperature T fitted on validation set.
    """
    sc = StandardScaler().fit(z_train)
    clf = LogisticRegression(
        C=LR_C,
        class_weight="balanced",
        max_iter=LR_MAX_ITER,
        random_state=seed,
    )
    clf.fit(sc.transform(z_train), y_train)

    z_val_s = sc.transform(z_val)
    logits = clf.decision_function(z_val_s)
    auroc_val = float(roc_auc_score(y_val, logits))

    probs_raw = clf.predict_proba(z_val_s)[:, 1]
    y_f = np.asarray(y_val, dtype=np.float64)

    ece_val = expected_calibration_error(probs_raw, y_f)
    mce_val = max_calibration_error(probs_raw, y_f)
    bs = brier_score(probs_raw, y_f)
    bss = brier_skill_score(probs_raw, y_f)
    nll_val = negative_log_likelihood(probs_raw, y_f)

    temp = fit_temperature(logits, y_f)
    probs_cal = apply_temperature(logits, temp)
    ece_cal = expected_calibration_error(probs_cal, y_f)

    return ProbeResult(
        auroc=auroc_val,
        ece=ece_val,
        mce=mce_val,
        brier=bs,
        brier_skill=bss,
        nll=nll_val,
        temperature=temp,
        ece_calibrated=ece_cal,
        probs_raw=probs_raw,
        probs_calibrated=probs_cal,
        labels_val=y_f,
    )


# ---------------------------------------------------------------------------
# Group k-fold probe (Parte I §7.8; C-18)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, eq=False)
class GroupProbeResult:
    """Result of a GroupKFold(5) cross-validated linear probe."""

    auroc_mean: float
    auroc_std: float
    auroc_per_fold: List[float]
    ece_mean: float
    temperature_mean: float
    ece_calibrated_mean: float
    n_folds_used: int
    oof_probs: NDArray[np.float64]
    oof_labels: NDArray[np.float64]
    oof_mask: NDArray[np.bool_]


def group_kfold_probe(
    z: NDArray[np.floating],
    y: NDArray[np.integer | np.floating],
    groups: NDArray,
    seed: int = 0,
    n_splits: int = GKFOLD_SPLITS,
) -> GroupProbeResult:
    """GroupKFold cross-validated linear probe.

    Folds where train or test has a single class are skipped with a warning
    (Parte I §7.8).
    """
    gkf = GroupKFold(n_splits=n_splits)
    y_arr = np.asarray(y, dtype=np.float64)
    z_arr = np.asarray(z, dtype=np.float64)

    aucs: List[float] = []
    eces: List[float] = []
    temps: List[float] = []
    eces_cal: List[float] = []
    oof_probs = np.full(len(y_arr), np.nan, dtype=np.float64)
    oof_labels = y_arr.copy()

    for k, (tr, te) in enumerate(gkf.split(z_arr, y_arr, groups)):
        if y_arr[tr].min() == y_arr[tr].max() or y_arr[te].min() == y_arr[te].max():
            log.warning("Fold %d skipped: single class in train or test.", k)
            continue

        result = fit_linear_probe(z_arr[tr], y_arr[tr], z_arr[te], y_arr[te], seed=seed)
        aucs.append(result.auroc)
        eces.append(result.ece)
        temps.append(result.temperature)
        eces_cal.append(result.ece_calibrated)
        oof_probs[te] = result.probs_raw

    n_used = len(aucs)
    oof_mask = ~np.isnan(oof_probs)

    return GroupProbeResult(
        auroc_mean=float(np.mean(aucs)) if aucs else 0.0,
        auroc_std=float(np.std(aucs, ddof=0)) if aucs else 0.0,
        auroc_per_fold=aucs,
        ece_mean=float(np.mean(eces)) if eces else 0.0,
        temperature_mean=float(np.mean(temps)) if temps else 0.0,
        ece_calibrated_mean=float(np.mean(eces_cal)) if eces_cal else 0.0,
        n_folds_used=n_used,
        oof_probs=oof_probs,
        oof_labels=oof_labels,
        oof_mask=oof_mask,
    )


# ---------------------------------------------------------------------------
# Permutation AUROC (Parte I §7.8, §3.8)
# ---------------------------------------------------------------------------
def permutation_auroc(
    z: NDArray[np.floating],
    y: NDArray[np.integer | np.floating],
    groups: NDArray,
    seed: int = 0,
    n_splits: int = GKFOLD_SPLITS,
) -> float:
    """AUROC of a probe trained on labels permuted within each group.

    Should be ~0.5 for non-leaky labels (Parte I §7.8).
    """
    rng = np.random.default_rng(seed)
    y_arr = np.asarray(y).copy()
    unique_groups = np.unique(groups)
    for g in unique_groups:
        mask = groups == g
        y_arr[mask] = rng.permutation(y_arr[mask])

    result = group_kfold_probe(z, y_arr, groups, seed=seed, n_splits=n_splits)
    return result.auroc_mean


# ---------------------------------------------------------------------------
# Leakage guard (Parte I §7.8, §3.8; Parte II §5.1; A-39)
# ---------------------------------------------------------------------------
def leakage_guard(
    label_sources: FrozenSet[str],
    schema_fields: FrozenSet[str],
    allow_future: FrozenSet[str] = frozenset(),
) -> Tuple[bool, FrozenSet[str]]:
    """Check whether label source columns leak into the schema.

    Name-level check: ``label_sources ∩ schema_fields - allow_future``.
    Labels like ``death_within_2s`` and ``contact_new_within_2s`` derive from
    future values of schema columns (health, enemies_visible) but are declared
    safe via ``allow_future`` by the caller (A-39).

    Args:
        label_sources: names of columns the labels were derived from.
        schema_fields: names of schema input fields.
        allow_future: label source names allowed despite overlap (future-derived).

    Returns:
        ``(is_clean, offenders)`` where ``is_clean`` is True when no leakage
        is detected and ``offenders`` is the set of overlapping names.
    """
    offenders = frozenset(sorted((label_sources & schema_fields) - allow_future))
    return len(offenders) == 0, offenders


# ---------------------------------------------------------------------------
# RankMe (Parte II §3.2; collapse_metrics.py)
# ---------------------------------------------------------------------------
def rankme(embeddings: "np.ndarray | object") -> float:
    """Effective rank on L2-normalized rows (RankMe, Garrido 2023).

    Delegates to ``collapse_metrics.compute_collapse_metrics`` to ensure a
    single implementation (Parte II §3.2). Accepts numpy arrays (converted to
    torch) or torch tensors.

    Returns 0.0 when fewer than 2 samples.
    """
    import torch

    from Programma_CS2_RENAN.backend.nn.collapse_metrics import compute_collapse_metrics

    if isinstance(embeddings, np.ndarray):
        t = torch.from_numpy(embeddings.astype(np.float32))
    elif isinstance(embeddings, torch.Tensor):
        t = embeddings
    else:
        raise TypeError(f"Expected ndarray or Tensor, got {type(embeddings)}")
    metrics = compute_collapse_metrics(t)
    return float(metrics["effective_rank"])


# ---------------------------------------------------------------------------
# kNN accuracy (Parte I §7.7; Parte III §5.2; C-18)
# ---------------------------------------------------------------------------
def knn_accuracy(
    z_train: NDArray[np.floating],
    y_train: NDArray[np.integer | np.floating],
    z_val: NDArray[np.floating],
    y_val: NDArray[np.integer | np.floating],
    k: int = KNN_K,
) -> float:
    """k-NN accuracy on normalized embeddings."""
    sc = StandardScaler().fit(z_train)
    clf = KNeighborsClassifier(n_neighbors=k)
    clf.fit(sc.transform(z_train), y_train)
    return float(clf.score(sc.transform(z_val), y_val))


# ---------------------------------------------------------------------------
# Delta-position R² (Parte I §7.7; Parte III §5.2)
# ---------------------------------------------------------------------------
def delta_pos_r2(
    z: NDArray[np.floating],
    y: NDArray[np.floating],
    groups: Optional[NDArray] = None,
    seed: int = 0,
    n_splits: int = GKFOLD_SPLITS,
) -> float:
    """Cross-validated Ridge R² for predicting Δpos from embeddings.

    Uses GroupKFold when ``groups`` is provided, KFold otherwise.
    """
    z_arr = np.asarray(z, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)

    if groups is not None:
        cv = GroupKFold(n_splits=n_splits)
        splits = list(cv.split(z_arr, y_arr, groups))
    else:
        cv = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
        splits = list(cv.split(z_arr, y_arr))

    r2s: List[float] = []
    for tr, te in splits:
        sc = StandardScaler().fit(z_arr[tr])
        ridge = Ridge(alpha=1.0)
        ridge.fit(sc.transform(z_arr[tr]), y_arr[tr])
        r2s.append(float(ridge.score(sc.transform(z_arr[te]), y_arr[te])))
    return float(np.mean(r2s)) if r2s else 0.0


# ---------------------------------------------------------------------------
# Report helper
# ---------------------------------------------------------------------------
def markdown_report(
    results: Dict[str, GroupProbeResult],
    rankme_value: float,
    extra: Optional[Dict[str, float]] = None,
) -> str:
    """Generate a markdown summary table of probe results.

    Args:
        results: mapping label_name -> GroupProbeResult.
        rankme_value: RankMe of the evaluated embeddings.
        extra: optional dict of additional metrics (e.g. knn_accuracy, dpos_r2).

    Returns:
        Markdown string.
    """
    lines: List[str] = [
        "# Probe & Calibration Report",
        "",
        f"**RankMe**: {rankme_value:.2f}",
        "",
    ]
    if extra:
        for k, v in extra.items():
            lines.append(f"**{k}**: {v:.4f}")
        lines.append("")

    lines.append("| Label | AUROC (μ±σ) | ECE | T | ECE_cal | Folds |")
    lines.append("|-------|-------------|-----|---|---------|-------|")
    for name, r in results.items():
        lines.append(
            f"| {name} | {r.auroc_mean:.4f}±{r.auroc_std:.4f} "
            f"| {r.ece_mean:.4f} | {r.temperature_mean:.2f} "
            f"| {r.ece_calibrated_mean:.4f} | {r.n_folds_used} |"
        )
    lines.append("")
    return "\n".join(lines)
