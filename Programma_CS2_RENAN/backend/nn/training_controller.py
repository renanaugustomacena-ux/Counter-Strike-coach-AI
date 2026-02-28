"""
Training Controller

Manages Coach training cycles:
1. Demo deduplication
2. Diversity checks
3. Monthly quota management
4. Stop-start logic

Adheres to GEMINI.md:
- Resource lifecycle management
- Controlled training
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import numpy as np
from sqlmodel import col, func, select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.training_control")


@dataclass
class TrainingDecision:
    should_train: bool
    reason: str
    diversity_score: float = 0.0


class TrainingController:
    """Controls when and how the Coach trains."""

    MAX_DEMOS_PER_MONTH = 10
    MIN_DIVERSITY_SCORE = 0.3  # Lower threshold for initial implementation

    def __init__(self):
        self.db = get_db_manager()

    def should_train_on_demo(
        self, demo_path: str, match_stats: PlayerMatchStats
    ) -> TrainingDecision:
        """
        Determine if a newly processed demo should be used for training.
        """
        try:
            # 1. Check monthly limit
            month_count = self._get_monthly_training_count()
            if month_count >= self.MAX_DEMOS_PER_MONTH:
                return TrainingDecision(
                    False,
                    f"Monthly training limit reached ({month_count}/{self.MAX_DEMOS_PER_MONTH})",
                )

            # 2. Check for duplicates (simplified logic)
            # In a real system, we'd hash the demo file.
            # Here we check if we already have stats for this match_id/map/date
            # But since match_stats is already processed, we assume it's "new" to the DB
            # We strictly check if it's "repetitive" data

            # 3. Check diversity
            diversity = self._calculate_diversity_score(match_stats)
            if diversity < self.MIN_DIVERSITY_SCORE:
                return TrainingDecision(
                    False,
                    f"Low diversity ({diversity:.2f}). Gameplay too similar to existing data.",
                    diversity,
                )

            return TrainingDecision(True, "Demo approved for training", diversity)

        except Exception as e:
            logger.error("Error in training control: %s", e)
            # Fail safe: don't train on error
            return TrainingDecision(False, f"Error: {e}")

    def _get_monthly_training_count(self) -> int:
        """Count demos used for training in last 30 days."""
        # For this prototype, we'll count total matches added in last 30 days
        # A real implementation would have a separate TrainingLog table
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        with self.db.get_session() as session:
            count = session.exec(
                select(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.processed_at >= thirty_days_ago
                )
            ).one()
            return count

    def _calculate_diversity_score(self, new_stats: PlayerMatchStats) -> float:
        """
        Calculate how different this match is from recent training data.
        Returns 0.0 (identical) to 1.0 (completely unique).
        """
        with self.db.get_session() as session:
            # Get last 5 matches
            recent_matches = session.exec(
                select(PlayerMatchStats)
                .order_by(col(PlayerMatchStats.processed_at).desc())
                .limit(5)
            ).all()

        if not recent_matches:
            return 1.0  # First match is always diverse

        # extract feature vector
        new_vec = self._extract_features(new_stats)

        similarities = []
        for match in recent_matches:
            # Skip self if it was just added
            if match.id == new_stats.id:
                continue

            old_vec = self._extract_features(match)
            sim = self._cosine_similarity(new_vec, old_vec)
            similarities.append(sim)

        if not similarities:
            return 1.0

        avg_similarity = sum(similarities) / len(similarities)

        # Diversity is inverse of similarity
        # If very similar (0.9), diversity is 0.1
        return 1.0 - avg_similarity

    def _extract_features(self, stats: PlayerMatchStats) -> np.ndarray:
        """Extract key stats for similarity comparison."""
        # Feature centering (approximate z-scaling) to make cosine similarity effective
        # Baselines: Kills(15), Deaths(15), ADR(75), HS(0.4), Util(20), Opening(0.5)
        return np.array(
            [
                (stats.avg_kills - 15) / 10.0,
                (stats.avg_deaths - 15) / 10.0,
                (stats.avg_adr - 75) / 25.0,
                (stats.avg_hs - 0.4) / 0.2,
                ((stats.utility_blind_time or 0) - 20) / 20.0,
                ((stats.opening_duel_win_pct or 0) - 0.5) / 0.3,
            ]
        )

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)


def get_training_controller() -> TrainingController:
    return TrainingController()
