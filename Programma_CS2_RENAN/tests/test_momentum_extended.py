"""
Extended tests for momentum.py — MomentumTracker and predict_performance_adjustment.

Covers:
  - Tracker initialization with neutral state
  - Consecutive wins increase momentum
  - Consecutive losses decrease momentum
  - Alternating wins/losses keep multiplier near neutral
  - predict_performance_adjustment returns finite values
"""

import math

import pytest

pytestmark = pytest.mark.timeout(5)


class TestMomentumTrackerInit:
    """MomentumTracker must initialize in a well-defined neutral state."""

    def test_momentum_tracker_init(self):
        """MomentumTracker initializes with multiplier=1.0, neutral streak, empty history."""
        from Programma_CS2_RENAN.backend.analysis.momentum import MomentumTracker

        tracker = MomentumTracker()

        assert tracker.state.current_multiplier == 1.0
        assert tracker.state.streak_length == 0
        assert tracker.state.streak_type == "neutral"
        assert not tracker.state.is_tilted
        assert not tracker.state.is_hot
        assert len(tracker.history) == 0


class TestMomentumIncreasesOnWinStreak:
    """Consecutive wins must push the multiplier above 1.0 monotonically."""

    def test_momentum_increases_on_win_streak(self):
        """Each additional consecutive win increases the momentum multiplier."""
        from Programma_CS2_RENAN.backend.analysis.momentum import MomentumTracker

        tracker = MomentumTracker()
        previous_multiplier = 1.0

        for round_num in range(1, 7):
            tracker.update(round_won=True, round_number=round_num)
            current = tracker.state.current_multiplier
            assert current >= previous_multiplier, (
                f"Round {round_num}: multiplier {current:.4f} did not increase "
                f"from {previous_multiplier:.4f} after win"
            )
            previous_multiplier = current

        # After 6 consecutive wins, must be meaningfully above 1.0
        assert tracker.state.current_multiplier > 1.0


class TestMomentumDecreasesOnLossStreak:
    """Consecutive losses must push the multiplier below 1.0 monotonically."""

    def test_momentum_decreases_on_loss_streak(self):
        """Each additional consecutive loss decreases the momentum multiplier."""
        from Programma_CS2_RENAN.backend.analysis.momentum import MomentumTracker

        tracker = MomentumTracker()
        previous_multiplier = 1.0

        for round_num in range(1, 7):
            tracker.update(round_won=False, round_number=round_num)
            current = tracker.state.current_multiplier
            assert current <= previous_multiplier, (
                f"Round {round_num}: multiplier {current:.4f} did not decrease "
                f"from {previous_multiplier:.4f} after loss"
            )
            previous_multiplier = current

        # After 6 consecutive losses, must be meaningfully below 1.0
        assert tracker.state.current_multiplier < 1.0


class TestAlternatingWinsLossesNearNeutral:
    """Alternating W/L/W/L pattern should keep the multiplier close to 1.0."""

    def test_alternating_wins_losses_near_neutral(self):
        """12 alternating outcomes keep multiplier within a narrow band around 1.0."""
        from Programma_CS2_RENAN.backend.analysis.momentum import MomentumTracker

        tracker = MomentumTracker()

        for round_num in range(1, 13):
            won = round_num % 2 == 1  # W, L, W, L, ...
            tracker.update(round_won=won, round_number=round_num)

        multiplier = tracker.state.current_multiplier
        # With alternating outcomes, streak never exceeds 1,
        # so multiplier should stay within [0.96, 1.05]
        assert (
            0.90 <= multiplier <= 1.10
        ), f"Alternating W/L multiplier {multiplier:.4f} drifted too far from 1.0"


class TestPredictPerformanceAdjustmentBounded:
    """predict_performance_adjustment must always return finite values."""

    def test_predict_performance_adjustment_bounded(self):
        """Adjusted rating is finite for all valid multiplier/rating combinations."""
        from Programma_CS2_RENAN.backend.analysis.momentum import (
            MULTIPLIER_MAX,
            MULTIPLIER_MIN,
            MomentumState,
            predict_performance_adjustment,
        )

        test_cases = [
            # (multiplier, base_rating)
            (1.0, 1.0),  # Neutral
            (MULTIPLIER_MAX, 2.0),  # Max momentum, high rating
            (MULTIPLIER_MIN, 0.5),  # Min momentum, low rating
            (1.0, 0.0),  # Zero base rating
            (MULTIPLIER_MAX, 0.0),  # Max momentum, zero rating
            (1.15, 1.35),  # Typical pro rating with moderate momentum
        ]

        for multiplier, base_rating in test_cases:
            state = MomentumState(current_multiplier=multiplier)
            result = predict_performance_adjustment(state, base_rating)
            assert math.isfinite(result), (
                f"Non-finite result {result} for multiplier={multiplier}, "
                f"base_rating={base_rating}"
            )
            # Result must equal multiplier * base_rating
            expected = multiplier * base_rating
            assert abs(result - expected) < 1e-9, f"Expected {expected}, got {result}"
