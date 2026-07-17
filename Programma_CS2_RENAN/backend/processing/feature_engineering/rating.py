"""
Unified HLTV 2.0 Rating Calculator.

CRITICAL: All rating computations across the pipeline MUST go through this module.
Both demo_parser.py and base_features.py MUST use these functions to prevent
'Inference-Training Skew' where the parser produces one rating but the
training pipeline produces another.

Reference: Reverse-engineered HLTV 2.0 coefficients (Leetify / open-source match data).

CONTRACT — kast argument semantics (CRITICAL):
  - compute_hltv2_rating() / compute_rating_components() → kast as RATIO
    (0.0 – 1.0, e.g. 0.72). The percentage-based regression variant was
    removed (F2-39/R4 LOW) precisely because its different kast semantics
    invited silently wrong ×100 ratings.
"""

from Programma_CS2_RENAN.observability.logger_setup import get_logger

_rating_logger = get_logger("cs2analyzer.rating")

# --- HLTV 2.0 Rating Formula Normalization Constants ---
# These are part of the reverse-engineered HLTV 2.0 rating formula, NOT
# empirical population means. The formula normalizes each component by
# its baseline so that an average pro player rates ~1.0.
# The pro population mean KAST (~0.74 in pro_baseline.py) differs from
# the formula constant (0.70) because HLTV uses a fixed denominator.
# See: docs/strategic_insights/HLTV_RATING_2_0_REVERSE_ENGINEERING.md
BASELINE_KPR = 0.679
BASELINE_DPR_COMPLEMENT = 0.317  # 1 - avg_DPR
BASELINE_KAST = 0.70  # R3-01: formula constant, not population mean
BASELINE_IMPACT = 1.0
BASELINE_ADR = 73.3

# --- HLTV 2.0 Regression Coefficients ---
# Reverse-engineered via linear regression on scraped HLTV player data.
# R²=0.995, RMSE=0.0046, MAE=0.0021 on 80/20 holdout.
# See docs/strategic_insights/HLTV_RATING_2_0_REVERSE_ENGINEERING.md
HLTV2_COEFF_KAST = 0.00738764
HLTV2_COEFF_KPR = 0.35912389
HLTV2_COEFF_DPR = -0.53295080
HLTV2_COEFF_IMPACT = 0.23726030
HLTV2_COEFF_ADR = 0.00323970
HLTV2_INTERCEPT = 0.15872723


def compute_impact_rating(kpr: float, avg_adr: float = 0.0, dpr: float = None) -> float:
    """
    Computes HLTV 2.0 Impact Rating.

    Full formula: 2.13*KPR + 0.42*AssistPR - 0.41*SurvivalPR
    When dpr is provided, the survival penalty (-0.41*(1-dpr)) is applied.
    When dpr is None, the term is omitted — result is systematically
    ~0.1–0.2 pts higher than the true impact for typical DPR values.

    Args:
        kpr:     Kills per round (ratio, e.g. 0.72)
        avg_adr: Average damage per round (raw, e.g. 85.3)
        dpr:     Deaths per round (ratio, e.g. 0.65). Optional.
                 When provided, the survival penalty is included.

    Returns:
        Impact rating (raw, typically ~0.8 – 1.4 for pros)
    """
    result = (kpr * 2.13) + (avg_adr / 100.0 * 0.42)
    if dpr is not None:
        survival_pr = 1.0 - dpr
        result -= 0.41 * survival_pr
    return result


def compute_survival_rating(dpr: float) -> float:
    """
    Computes HLTV 2.0 Survival Rating component.

    Args:
        dpr: Deaths per round (ratio, e.g. 0.65)

    Returns:
        Survival rating (raw, higher is better)
    """
    return 1.0 - dpr


def compute_rating_components(
    kpr: float,
    dpr: float,
    kast: float,
    avg_adr: float,
) -> dict:
    """
    Single source of truth for the PlayerMatchStats ``rating_*`` columns.

    CONTRACT — column scale is RAW components (NOT baseline-normalized):
        rating_kpr      = kpr                                  (~0.68 avg pro)
        rating_survival = 1 - dpr                              (~0.32 avg pro)
        rating_kast     = kast ratio 0-1                       (~0.70 avg pro)
        rating_impact   = compute_impact_rating(kpr, adr, dpr) (~1.0-1.4 pro)
        rating_adr      = avg_adr                              (~73-85 pro)
        rating          = compute_hltv2_rating(...) aggregate  (~1.0 avg pro)

    Baseline normalization (``/ BASELINE_*``) happens ONLY inside the
    ``rating`` aggregate. pro_baseline.py, skill_assessment.py and
    coach_manager.py all consume the raw scale — writing normalized ratios
    into these columns silently corrupts every downstream Z-score.

    Every PlayerMatchStats writer MUST use this function. The vectorized
    DataFrame path in demo_parser._apply_hltv2_columns replicates it and is
    pinned by the parity test in test_rating_components_contract.py.

    Args:
        kpr: Kills per round (ratio, e.g. 0.72)
        dpr: Deaths per round (ratio, e.g. 0.65)
        kast: KAST ratio (0.0 - 1.0, e.g. 0.72)
        avg_adr: Average damage per round (raw, e.g. 85.3)

    Returns:
        Dict with keys rating_kpr, rating_survival, rating_kast,
        rating_impact, rating_adr, rating.
    """
    impact = compute_impact_rating(kpr, avg_adr, dpr=dpr)
    return {
        "rating_kpr": kpr,
        "rating_survival": compute_survival_rating(dpr),
        "rating_kast": kast,
        "rating_impact": impact,
        "rating_adr": avg_adr,
        "rating": compute_hltv2_rating(kpr, dpr, kast, avg_adr, impact=impact),
    }


def compute_hltv2_rating(
    kpr: float,
    dpr: float,
    kast: float,
    avg_adr: float,
    impact: float = None,
) -> float:
    """
    Computes the unified HLTV 2.0 Rating.

    Each of the 5 components is normalized against pro-baseline:
        R = (kill + survival + kast + impact + damage) / 5

    Args:
        kpr: Kills per round (ratio, e.g. 0.72)
        dpr: Deaths per round (ratio, e.g. 0.65)
        kast: KAST ratio (0.0 - 1.0, e.g. 0.72)
        avg_adr: Average damage per round (raw, e.g. 85.3)
        impact: Pre-computed impact rating. If None, auto-computed from kpr+adr.

    Returns:
        HLTV 2.0 Rating (float, ~1.0 for average pro)
    """
    if impact is None:
        impact = compute_impact_rating(kpr, avg_adr, dpr=dpr)

    r_kill = kpr / BASELINE_KPR
    r_surv = compute_survival_rating(dpr) / BASELINE_DPR_COMPLEMENT
    r_kast = kast / BASELINE_KAST
    r_imp = impact / BASELINE_IMPACT
    r_dmg = avg_adr / BASELINE_ADR

    # NOTE (F2-40): this per-component average deliberately diverges from
    # HLTV's published regression formula (coefficients above, function
    # removed in F2-39/R4 LOW): each term here is independently
    # interpretable for per-component deviation analysis. Do NOT
    # "reconcile" it to the regression — the divergence is by design.
    return (r_kill + r_surv + r_kast + r_imp + r_dmg) / 5.0


# F2-39 → R4 LOW (2026-07-17): compute_hltv2_rating_regression DELETED.
# It had zero production call sites and carried DIFFERENT kast semantics
# (percentage vs ratio) — an invitation to call the wrong formula. The
# regression coefficients above are retained for documentation; see
# docs/strategic_insights/HLTV_RATING_2_0_REVERSE_ENGINEERING.md.
