"""
User Onboarding Workflow

Manages new user experience:
1. First demo upload requirement
2. Baseline establishment
3. Coach readiness tracking

Adheres to GEMINI.md:
- Explicit state management
- User-centric design
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from sqlmodel import func, select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.onboarding")


class OnboardingStage:
    AWAITING_FIRST_DEMO = "awaiting_first_demo"
    BUILDING_BASELINE = "building_baseline"
    COACH_READY = "coach_ready"


@dataclass
class OnboardingStatus:
    stage: str
    demos_uploaded: int
    demos_required: int
    demos_recommended: int
    coach_ready: bool
    baseline_stable: bool
    message: str


class UserOnboardingManager:
    """Manages new user onboarding flow."""

    MIN_INITIAL_DEMOS = 1
    RECOMMENDED_DEMOS = 3
    _CACHE_TTL_SECONDS = 60  # TASK 2.16.1: Cache demo count for 60 seconds

    def __init__(self):
        self.db = get_db_manager()
        # TASK 2.16.1: In-memory cache for demo counts
        self._demo_count_cache: Dict[str, Tuple[int, float]] = {}  # user_id -> (count, timestamp)

    def get_status(self, user_id: str = "default_user") -> OnboardingStatus:
        """Get current onboarding status for user."""
        demos_uploaded = self._count_user_demos(user_id)
        stage = self._determine_stage(demos_uploaded)

        message = self._get_stage_message(stage, demos_uploaded)

        return OnboardingStatus(
            stage=stage,
            demos_uploaded=demos_uploaded,
            demos_required=self.MIN_INITIAL_DEMOS,
            demos_recommended=self.RECOMMENDED_DEMOS,
            coach_ready=demos_uploaded >= self.MIN_INITIAL_DEMOS,
            baseline_stable=demos_uploaded >= self.RECOMMENDED_DEMOS,
            message=message,
        )

    def _count_user_demos(self, user_id: str) -> int:
        """
        Count processed demos for user.

        TASK 2.16.1: Uses TTL-based cache to avoid repeated DB queries
        during the same session or rapid UI refreshes.
        """
        now = time.monotonic()

        # Check cache
        if user_id in self._demo_count_cache:
            cached_count, cached_time = self._demo_count_cache[user_id]
            if now - cached_time < self._CACHE_TTL_SECONDS:
                return cached_count

        # Cache miss or expired: query DB
        with self.db.get_session() as session:
            count = session.exec(select(func.count(PlayerMatchStats.id))).one()

        # Update cache
        self._demo_count_cache[user_id] = (count, now)
        return count

    def invalidate_cache(self, user_id: str = None) -> None:
        """
        TASK 2.16.1: Invalidate the demo count cache.

        Call this after a new demo is uploaded to ensure the next
        get_status() call reflects the updated count immediately.
        """
        if user_id:
            self._demo_count_cache.pop(user_id, None)
        else:
            self._demo_count_cache.clear()

    def _determine_stage(self, count: int) -> str:
        if count == 0:
            return OnboardingStage.AWAITING_FIRST_DEMO
        elif count < self.RECOMMENDED_DEMOS:
            return OnboardingStage.BUILDING_BASELINE
        else:
            return OnboardingStage.COACH_READY

    def _get_stage_message(self, stage: str, count: int) -> str:
        if stage == OnboardingStage.AWAITING_FIRST_DEMO:
            return "👋 Welcome! Please upload your first CS2 demo to initialize the Coach."
        elif stage == OnboardingStage.BUILDING_BASELINE:
            remaining = self.RECOMMENDED_DEMOS - count
            return (
                f"📈 Coach initializing... Upload {remaining} more demo(s) for a stable baseline."
            )
        else:
            return "✅ Coach is ready! Personalized analysis active."


def get_onboarding_manager() -> UserOnboardingManager:
    return UserOnboardingManager()
