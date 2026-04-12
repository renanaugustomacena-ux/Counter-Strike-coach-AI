"""
Robust Demo Quality Scoring via Huber Contamination Model.

Evaluates the data quality of ingested demos using statistical methods
that are robust to contaminated observations.  Uses the Huber contamination
model assumption: the majority of data is "clean" (drawn from a nominal
distribution), while a fraction epsilon is arbitrarily corrupted.

The scorer detects:
    - Incomplete demos (low tick coverage)
    - Feature sparsity (excessive zero-valued features)
    - Statistical outliers in key match metrics (kills, deaths, ADR)
    - Warmup/truncated demos via tick-count heuristics

Quality scoring uses the Interquartile Range (IQR) method for outlier
detection, which provides breakdown-point robustness up to 25% contamination
(matching the Huber epsilon model for moderate contamination).

References:
    - Huber, P.J. "Robust Statistics" (1981), Chapter 1.2 —
      epsilon-contamination model: F = (1 - eps) * G + eps * H
    - Rousseeuw, P.J. & Croux, C. "Alternatives to the Median Absolute
      Deviation" (1993) — robust scale estimators
    - PPI (Prediction-Powered Inference): Angelopoulos et al. (2023) —
      using model predictions to adjust statistical estimates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

import numpy as np

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, PlayerTickState
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.processing.demo_quality")

# Expected tick count for a full CS2 competitive match.
# 30 rounds * ~115 seconds * 64 ticks/s * 10 players ~ 2.2M ticks.
# We use a conservative per-player estimate for a single demo:
# ~25 rounds * 100s * 64 ticks = ~160k ticks per player.
# With 10 players in a demo: ~1.6M total ticks.
# Minimum viable: 10 rounds * 80s * 64 * 10 = ~512k ticks.
_EXPECTED_TICKS_PER_DEMO = 1_600_000
_MIN_VIABLE_TICKS = 512_000

# IQR multiplier for outlier fences (Tukey's method).
# 1.5 = standard outlier, 3.0 = extreme outlier.
_IQR_MULTIPLIER_MODERATE = 1.5
_IQR_MULTIPLIER_EXTREME = 3.0

# Thresholds for quality classification.
_QUALITY_THRESHOLD_USE = 0.7
_QUALITY_THRESHOLD_REVIEW = 0.4

# Features in PlayerTickState that should be non-zero in normal gameplay.
_NONZERO_TICK_FIELDS = [
    "health",
    "armor",
    "pos_x",
    "pos_y",
    "pos_z",
    "equipment_value",
]


@dataclass
class OutlierFlag:
    """Single outlier detection result for a metric."""

    metric_name: str
    value: float
    lower_fence: float
    upper_fence: float
    severity: Literal["moderate", "extreme"]

    @property
    def is_low(self) -> bool:
        return self.value < self.lower_fence

    @property
    def is_high(self) -> bool:
        return self.value > self.upper_fence


@dataclass
class DemoQualityReport:
    """Comprehensive quality assessment for a single demo.

    Attributes:
        demo_name: Identifier of the assessed demo.
        quality_score: Overall quality in [0, 1].  Higher is better.
        tick_coverage: Ratio of actual ticks to expected ticks, clamped to [0, 1].
        feature_completeness: Fraction of non-zero values across key tick fields.
        outlier_flags: List of detected statistical outliers.
        recommendation: Actionable label — ``"use"``, ``"review"``, or ``"skip"``.
        detail: Human-readable summary of findings.
    """

    demo_name: str
    quality_score: float
    tick_coverage: float
    feature_completeness: float
    outlier_flags: list[OutlierFlag] = field(default_factory=list)
    recommendation: Literal["use", "review", "skip"] = "review"
    detail: str = ""


class DemoQualityScorer:
    """Scores demo data quality using robust statistical methods.

    The scorer operates in three phases:
        1. **Tick coverage**: How complete is the demo's tick data relative
           to an expected full match?
        2. **Feature completeness**: What fraction of tick-level features
           contain meaningful (non-zero) values?
        3. **Outlier detection**: Are the demo's aggregate match statistics
           (kills, deaths, ADR) within normal bounds using IQR fencing?

    The final quality score is a weighted combination of these components,
    and the recommendation is derived from threshold comparisons.
    """

    def score_demo(self, demo_name: str) -> DemoQualityReport:
        """Compute quality report for a single demo.

        Args:
            demo_name: The demo identifier to evaluate.

        Returns:
            A ``DemoQualityReport`` with all quality metrics populated.
        """
        logger.info("Scoring quality for demo: %s", demo_name)

        tick_coverage = self._compute_tick_coverage(demo_name)
        feature_completeness = self._compute_feature_completeness(demo_name)
        outlier_flags = self._detect_outliers(demo_name)

        # Weighted quality score.
        # Tick coverage is the strongest signal (incomplete = unreliable).
        # Feature completeness catches parsing failures.
        # Outlier penalty reduces score for anomalous demos.
        outlier_penalty = min(len(outlier_flags) * 0.1, 0.4)

        quality_score = float(
            np.clip(
                0.45 * tick_coverage + 0.35 * feature_completeness + 0.20 * (1.0 - outlier_penalty),
                0.0,
                1.0,
            )
        )

        # Derive recommendation.
        if quality_score >= _QUALITY_THRESHOLD_USE and not any(
            f.severity == "extreme" for f in outlier_flags
        ):
            recommendation: Literal["use", "review", "skip"] = "use"
        elif quality_score >= _QUALITY_THRESHOLD_REVIEW:
            recommendation = "review"
        else:
            recommendation = "skip"

        detail_parts = [
            f"tick_coverage={tick_coverage:.3f}",
            f"feature_completeness={feature_completeness:.3f}",
            f"outliers={len(outlier_flags)}",
        ]
        if outlier_flags:
            flag_summary = "; ".join(
                f"{f.metric_name}={f.value:.2f} ({f.severity})" for f in outlier_flags
            )
            detail_parts.append(f"flagged=[{flag_summary}]")

        report = DemoQualityReport(
            demo_name=demo_name,
            quality_score=quality_score,
            tick_coverage=tick_coverage,
            feature_completeness=feature_completeness,
            outlier_flags=outlier_flags,
            recommendation=recommendation,
            detail=", ".join(detail_parts),
        )

        logger.info(
            "Demo %s quality: %.3f (%s) — %s",
            demo_name,
            quality_score,
            recommendation,
            report.detail,
        )
        return report

    def score_demos_batch(self, demo_names: list[str]) -> list[DemoQualityReport]:
        """Score multiple demos and return sorted by quality descending.

        Args:
            demo_names: List of demo identifiers.

        Returns:
            List of ``DemoQualityReport`` sorted by ``quality_score`` descending.
        """
        reports = []
        for name in demo_names:
            try:
                reports.append(self.score_demo(name))
            except Exception:
                logger.warning("Failed to score demo %s", name, exc_info=True)
                reports.append(
                    DemoQualityReport(
                        demo_name=name,
                        quality_score=0.0,
                        tick_coverage=0.0,
                        feature_completeness=0.0,
                        recommendation="skip",
                        detail="scoring failed",
                    )
                )

        reports.sort(key=lambda r: r.quality_score, reverse=True)
        return reports

    # ------------------------------------------------------------------
    # Component 1: Tick coverage
    # ------------------------------------------------------------------

    def _compute_tick_coverage(self, demo_name: str) -> float:
        """Compute tick coverage ratio for a demo.

        Returns:
            Ratio in [0, 1] where 1.0 means the demo has at least as many
            ticks as expected for a full match.
        """
        from sqlmodel import func, select

        db = get_db_manager()
        with db.get_session() as session:
            stmt = select(func.count(PlayerTickState.id)).where(
                PlayerTickState.demo_name == demo_name
            )
            tick_count = session.exec(stmt).one()

        if tick_count is None or tick_count == 0:
            logger.debug("Demo %s has no tick data", demo_name)
            return 0.0

        coverage = float(np.clip(tick_count / _EXPECTED_TICKS_PER_DEMO, 0.0, 1.0))

        if tick_count < _MIN_VIABLE_TICKS:
            logger.debug(
                "Demo %s has low tick count: %d (min viable: %d)",
                demo_name,
                tick_count,
                _MIN_VIABLE_TICKS,
            )

        return coverage

    # ------------------------------------------------------------------
    # Component 2: Feature completeness
    # ------------------------------------------------------------------

    def _compute_feature_completeness(self, demo_name: str) -> float:
        """Compute fraction of non-zero values across key tick fields.

        Samples up to 500 ticks to avoid scanning the entire table.

        Returns:
            Ratio in [0, 1] where 1.0 means all sampled tick fields
            contain non-zero values.
        """
        from sqlmodel import select

        db = get_db_manager()
        with db.get_session() as session:
            stmt = select(PlayerTickState).where(PlayerTickState.demo_name == demo_name).limit(500)
            ticks = session.exec(stmt).all()

        if not ticks:
            return 0.0

        total_checks = 0
        nonzero_count = 0

        for tick in ticks:
            for field_name in _NONZERO_TICK_FIELDS:
                total_checks += 1
                value = getattr(tick, field_name, 0)
                if value != 0:
                    nonzero_count += 1

        return nonzero_count / max(total_checks, 1)

    # ------------------------------------------------------------------
    # Component 3: Outlier detection (IQR / Huber contamination)
    # ------------------------------------------------------------------

    def _detect_outliers(self, demo_name: str) -> list[OutlierFlag]:
        """Detect statistical outliers in aggregate match statistics.

        Uses the IQR (Interquartile Range) method, which is robust to
        contamination up to 25% (matching Huber's epsilon-contamination
        model for moderate corruption levels).

        The method computes fences from ALL demos in the database, then
        checks whether the target demo's metrics fall outside those fences.

        Returns:
            List of ``OutlierFlag`` for each metric that exceeds fences.
        """
        from sqlmodel import select

        db = get_db_manager()

        # Load all PlayerMatchStats for the reference distribution.
        with db.get_session() as session:
            all_stats = session.exec(select(PlayerMatchStats)).all()

        if len(all_stats) < 10:
            logger.debug(
                "Insufficient reference data (%d rows) for outlier detection — skipping",
                len(all_stats),
            )
            return []

        # Metrics to check and their accessors.
        metrics_to_check = {
            "avg_kills": lambda s: s.avg_kills,
            "avg_deaths": lambda s: s.avg_deaths,
            "avg_adr": lambda s: s.avg_adr,
            "kd_ratio": lambda s: s.kd_ratio,
            "avg_kast": lambda s: s.avg_kast,
        }

        # Build reference distributions from all demos.
        reference: Dict[str, np.ndarray] = {}
        for metric_name, accessor in metrics_to_check.items():
            values = [accessor(s) for s in all_stats if accessor(s) is not None]
            if values:
                reference[metric_name] = np.array(values, dtype=np.float64)

        # Get target demo's stats.
        target_stats = [s for s in all_stats if s.demo_name == demo_name]
        if not target_stats:
            logger.debug(
                "No PlayerMatchStats found for demo %s — skipping outlier detection",
                demo_name,
            )
            return []

        flags: list[OutlierFlag] = []

        for metric_name, accessor in metrics_to_check.items():
            if metric_name not in reference:
                continue

            ref_values = reference[metric_name]
            q1, q3 = np.percentile(ref_values, [25, 75])
            iqr = q3 - q1

            if iqr < 1e-9:
                # Zero spread — all values identical, no outlier possible.
                continue

            lower_moderate = q1 - _IQR_MULTIPLIER_MODERATE * iqr
            upper_moderate = q3 + _IQR_MULTIPLIER_MODERATE * iqr
            lower_extreme = q1 - _IQR_MULTIPLIER_EXTREME * iqr
            upper_extreme = q3 + _IQR_MULTIPLIER_EXTREME * iqr

            # Average the metric across all players in this demo.
            demo_values = [accessor(s) for s in target_stats if accessor(s) is not None]
            if not demo_values:
                continue
            demo_mean = float(np.mean(demo_values))

            # Check extreme first, then moderate.
            if demo_mean < lower_extreme or demo_mean > upper_extreme:
                flags.append(
                    OutlierFlag(
                        metric_name=metric_name,
                        value=demo_mean,
                        lower_fence=lower_extreme,
                        upper_fence=upper_extreme,
                        severity="extreme",
                    )
                )
            elif demo_mean < lower_moderate or demo_mean > upper_moderate:
                flags.append(
                    OutlierFlag(
                        metric_name=metric_name,
                        value=demo_mean,
                        lower_fence=lower_moderate,
                        upper_fence=upper_moderate,
                        severity="moderate",
                    )
                )

        if flags:
            logger.info(
                "Demo %s has %d outlier flags: %s",
                demo_name,
                len(flags),
                ", ".join(f"{f.metric_name}({f.severity})" for f in flags),
            )

        return flags
