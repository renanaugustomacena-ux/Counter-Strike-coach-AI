"""
Role Threshold Store

Dynamic threshold storage for role classification.
Thresholds are LEARNED from real data (HLTV, demos), NEVER hardcoded.

Anti-Mock Principle:
    - All thresholds start as None (unknown)
    - Values are populated from pro player data
    - If insufficient data, classifier returns UNKNOWN with 0% confidence
    - Coach never learns from fake/mock data
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.role_thresholds")


@dataclass
class LearnedThreshold:
    """A threshold value learned from real data."""

    value: Optional[float] = None  # None = not yet learned
    sample_count: int = 0  # How many samples contributed
    last_updated: Optional[datetime] = None
    source: str = "unknown"  # "hltv", "demo_parser", "ml_model"


class RoleThresholdStore:
    """
    Dynamic threshold storage - learned from real data, NEVER mocked.

    Philosophy:
        - All thresholds initialize to None (cold start)
        - Values are computed from real pro player statistics
        - If a threshold is None, the classifier cannot use it
        - Minimum sample count required before threshold is valid

    Data Sources:
        1. HLTV Scraper: Pro player stats → compute role thresholds
        2. Demo Parser: User matches → validate/refine thresholds
        3. ML Model: Over time, learns optimal thresholds
    """

    # Minimum samples required before a threshold is considered valid
    MIN_SAMPLES_FOR_VALIDITY = 10

    def __init__(self):
        """Initialize with empty thresholds (cold start state)."""
        self._thresholds: Dict[str, LearnedThreshold] = {
            # Role detection stat names - values are None until learned
            "awp_kill_ratio": LearnedThreshold(),
            "entry_rate": LearnedThreshold(),
            "assist_rate": LearnedThreshold(),
            "survival_rate": LearnedThreshold(),
            "solo_kill_rate": LearnedThreshold(),
            "first_death_rate": LearnedThreshold(),
            "utility_damage_rate": LearnedThreshold(),
            "clutch_rate": LearnedThreshold(),
            "trade_rate": LearnedThreshold(),
        }
        self._is_initialized = False
        logger.info("RoleThresholdStore initialized in COLD START state (no learned thresholds)")

    def get_threshold(self, stat_name: str) -> Optional[float]:
        """
        Get a threshold value if it has been learned.

        Returns:
            The threshold value, or None if not yet learned or insufficient samples.
        """
        threshold = self._thresholds.get(stat_name)
        if threshold is None:
            return None

        # Only return value if we have sufficient samples
        if threshold.sample_count < self.MIN_SAMPLES_FOR_VALIDITY:
            return None

        return threshold.value

    def is_cold_start(self) -> bool:
        """
        Check if the store is in cold start state.

        A cold start means insufficient data to reliably classify roles.
        The coach should remain silent or return UNKNOWN in this state.
        """
        valid_thresholds = sum(
            1
            for t in self._thresholds.values()
            if t.value is not None and t.sample_count >= self.MIN_SAMPLES_FOR_VALIDITY
        )

        # Require at least 3 valid thresholds to exit cold start
        return valid_thresholds < 3

    def validate_consistency(self) -> bool:
        """Check that learned thresholds form a consistent partition (no gaps/overlaps).

        NOTE (F2-19): The current validation only checks that individual threshold values
        are positive. This method is a placeholder for future partition-consistency
        verification (e.g., ensuring role boundaries do not overlap or leave gaps).
        Returns True unconditionally until the full partition check is implemented.
        """
        # TODO: Verify that threshold boundaries partition the stat-space without
        # gaps or overlaps across role archetypes (entry_rate, survival_rate, etc.).
        return True

    def get_readiness_report(self) -> Dict[str, Any]:
        """Get a report on threshold readiness for debugging."""
        return {
            "is_cold_start": self.is_cold_start(),
            "thresholds": {
                name: {
                    "value": t.value,
                    "samples": t.sample_count,
                    "valid": t.sample_count >= self.MIN_SAMPLES_FOR_VALIDITY,
                    "source": t.source,
                }
                for name, t in self._thresholds.items()
            },
        }

    def learn_from_pro_data(
        self, pro_stats: List[Dict[str, float]], known_roles: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Learn thresholds from real pro player statistics.

        Args:
            pro_stats: List of player stat dictionaries from HLTV or demos
            known_roles: Optional mapping of player_name -> role for labeled data

        This calculates thresholds as statistical boundaries (e.g., 75th percentile)
        that separate role archetypes.
        """
        import numpy as np

        if not pro_stats:
            logger.warning("learn_from_pro_data called with empty data - no learning performed")
            return

        logger.info("Learning thresholds from %s pro player records", len(pro_stats))

        # Calculate thresholds using percentile analysis
        now = datetime.now()

        # AWP Kill Ratio - AWPers have high awp_kills / total_kills
        awp_ratios = [s.get("awp_kills", 0) / max(s.get("total_kills", 1), 1) for s in pro_stats]
        if awp_ratios:
            # 75th percentile - players above this are likely AWPers
            self._thresholds["awp_kill_ratio"].value = float(np.percentile(awp_ratios, 75))
            self._thresholds["awp_kill_ratio"].sample_count = len(awp_ratios)
            self._thresholds["awp_kill_ratio"].last_updated = now
            self._thresholds["awp_kill_ratio"].source = "hltv"

        # Entry Rate - entry_frags per round
        entry_rates = [
            s.get("entry_frags", 0) / max(s.get("rounds_played", 1), 1) for s in pro_stats
        ]
        if entry_rates:
            self._thresholds["entry_rate"].value = float(np.percentile(entry_rates, 70))
            self._thresholds["entry_rate"].sample_count = len(entry_rates)
            self._thresholds["entry_rate"].last_updated = now
            self._thresholds["entry_rate"].source = "hltv"

        # Assist Rate - assists per round
        assist_rates = [s.get("assists", 0) / max(s.get("rounds_played", 1), 1) for s in pro_stats]
        if assist_rates:
            self._thresholds["assist_rate"].value = float(np.percentile(assist_rates, 70))
            self._thresholds["assist_rate"].sample_count = len(assist_rates)
            self._thresholds["assist_rate"].last_updated = now
            self._thresholds["assist_rate"].source = "hltv"

        # Survival Rate - rounds survived / rounds played
        survival_rates = [
            s.get("rounds_survived", 0) / max(s.get("rounds_played", 1), 1) for s in pro_stats
        ]
        if survival_rates:
            self._thresholds["survival_rate"].value = float(np.percentile(survival_rates, 70))
            self._thresholds["survival_rate"].sample_count = len(survival_rates)
            self._thresholds["survival_rate"].last_updated = now
            self._thresholds["survival_rate"].source = "hltv"

        # Solo Kill Rate - for lurkers
        solo_rates = [s.get("solo_kills", 0) / max(s.get("total_kills", 1), 1) for s in pro_stats]
        if solo_rates:
            self._thresholds["solo_kill_rate"].value = float(np.percentile(solo_rates, 70))
            self._thresholds["solo_kill_rate"].sample_count = len(solo_rates)
            self._thresholds["solo_kill_rate"].last_updated = now
            self._thresholds["solo_kill_rate"].source = "hltv"

        self._is_initialized = True
        logger.info("Threshold learning complete. Cold start: %s", self.is_cold_start())

    def persist_to_db(self, db_session) -> None:
        """Persist learned thresholds to database for recovery across restarts."""
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.db_models import RoleThresholdRecord

        for name, threshold in self._thresholds.items():
            existing = db_session.exec(
                select(RoleThresholdRecord).where(RoleThresholdRecord.stat_name == name)
            ).first()
            if existing:
                existing.value = threshold.value
                existing.sample_count = threshold.sample_count
                existing.source = threshold.source
                existing.last_updated = threshold.last_updated
                db_session.add(existing)
            else:
                record = RoleThresholdRecord(
                    stat_name=name,
                    value=threshold.value,
                    sample_count=threshold.sample_count,
                    source=threshold.source,
                    last_updated=threshold.last_updated,
                )
                db_session.add(record)
        logger.info("Persisted %d thresholds to database", len(self._thresholds))

    def load_from_db(self, db_session) -> bool:
        """Load previously learned thresholds from database.

        Returns True if thresholds were loaded, False if cold start.
        """
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.db_models import RoleThresholdRecord

        records = db_session.exec(select(RoleThresholdRecord)).all()
        if not records:
            logger.info("No persisted thresholds found — cold start")
            return False

        loaded = 0
        for record in records:
            if record.stat_name in self._thresholds:
                t = self._thresholds[record.stat_name]
                t.value = record.value
                t.sample_count = record.sample_count
                t.source = record.source
                t.last_updated = record.last_updated
                loaded += 1

        if loaded > 0:
            self._is_initialized = True
        logger.info("Loaded %d/%d thresholds from database", loaded, len(records))
        return loaded > 0


# Singleton instance
_threshold_store: Optional[RoleThresholdStore] = None


def get_role_threshold_store() -> RoleThresholdStore:
    """Get the singleton RoleThresholdStore instance."""
    global _threshold_store
    if _threshold_store is None:
        _threshold_store = RoleThresholdStore()
    return _threshold_store
