"""
Pre-training data quality report (Phase 3D).

Runs a battery of checks on the ingested data BEFORE training starts.
Returns a DataQualityReport that the TrainingOrchestrator inspects
to decide whether to proceed or abort.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.data_quality")


@dataclass
class DataQualityReport:
    """Summary of pre-training data quality checks."""

    total_tick_rows: int = 0
    train_rows: int = 0
    val_rows: int = 0
    test_rows: int = 0

    # Per-demo quality metrics
    zero_position_rate: float = 0.0  # fraction of ticks with (0,0,0) position
    nan_rate: float = 0.0  # fraction of ticks with NaN in any column

    # Class balance
    round_outcome_distribution: Dict[str, int] = field(default_factory=dict)

    # Match completeness
    complete_matches: int = 0
    incomplete_matches: int = 0

    # Issues found
    issues: List[str] = field(default_factory=list)
    passed: bool = True

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"Data Quality Report: {status}",
            f"  Total ticks: {self.total_tick_rows:,}",
            f"  Train/Val/Test: {self.train_rows:,}/{self.val_rows:,}/{self.test_rows:,}",
            f"  Zero-position rate: {self.zero_position_rate:.2%}",
            f"  Complete matches: {self.complete_matches}, Incomplete: {self.incomplete_matches}",
        ]
        if self.issues:
            lines.append(f"  Issues ({len(self.issues)}):")
            for issue in self.issues:
                lines.append(f"    - {issue}")
        return "\n".join(lines)


def run_pre_training_quality_check(
    min_samples: int = 1000,
    max_zero_position_rate: float = 0.10,
) -> DataQualityReport:
    """Run pre-training quality checks on ingested data.

    Args:
        min_samples: Minimum total tick rows required.
        max_zero_position_rate: Maximum allowed fraction of (0,0,0) positions.

    Returns:
        DataQualityReport with pass/fail verdict.
    """
    report = DataQualityReport()

    try:
        from sqlmodel import func, select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, PlayerTickState

        db = get_db_manager()

        # 1. Count total tick rows and split distribution
        with db.get_session() as session:
            report.total_tick_rows = session.exec(
                select(func.count()).select_from(PlayerTickState)
            ).one()

        # 2. Count by dataset split
        with db.get_session() as session:
            for split_name in ("train", "val", "test"):
                count = session.exec(
                    select(func.count())
                    .select_from(PlayerMatchStats)
                    .where(PlayerMatchStats.dataset_split == split_name)
                ).one()
                setattr(report, f"{split_name}_rows", count)

        # 3. Zero-position rate (sample up to 10K ticks for efficiency)
        with db.get_session() as session:
            sample_total = min(report.total_tick_rows, 10000)
            if sample_total > 0:
                zero_count = session.exec(
                    select(func.count())
                    .select_from(PlayerTickState)
                    .where(
                        PlayerTickState.pos_x == 0.0,
                        PlayerTickState.pos_y == 0.0,
                        PlayerTickState.pos_z == 0.0,
                    )
                ).one()
                report.zero_position_rate = zero_count / max(report.total_tick_rows, 1)

        # 4. Match completeness (via match data manager)
        try:
            from Programma_CS2_RENAN.backend.storage.match_data_manager import (
                get_match_data_manager,
            )

            mdm = get_match_data_manager()
            match_ids = mdm.list_available_matches()
            for mid in match_ids:
                meta = mdm.get_metadata(mid)
                if meta and getattr(meta, "match_complete", False):
                    report.complete_matches += 1
                else:
                    report.incomplete_matches += 1
        except Exception as e:
            logger.debug("Match completeness check skipped: %s", e)

        # 5. Verdict
        if report.total_tick_rows < min_samples:
            report.issues.append(
                f"Insufficient data: {report.total_tick_rows:,} ticks < {min_samples:,} minimum"
            )
            report.passed = False

        if report.zero_position_rate > max_zero_position_rate:
            report.issues.append(
                f"Zero-position rate {report.zero_position_rate:.1%} exceeds "
                f"{max_zero_position_rate:.0%} threshold"
            )
            report.passed = False

        if report.train_rows == 0:
            report.issues.append("No demos assigned to 'train' split")
            report.passed = False

    except Exception as e:
        report.issues.append(f"Quality check failed: {e}")
        report.passed = False
        logger.error("Pre-training quality check failed: %s", e, exc_info=True)

    logger.info(report.summary())
    return report
