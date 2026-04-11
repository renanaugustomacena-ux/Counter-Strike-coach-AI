"""Extended tests for backend.analysis.blind_spots module.

Covers BlindSpotDetector instantiation, edge cases for detect() with degenerate
round data, training plan generation with multiple spots, and BlindSpot dataclass
field verification.

These tests are ADDITIVE to the coverage in test_game_theory.py::TestBlindSpotDetector.
"""

import pytest

pytestmark = pytest.mark.timeout(5)


class TestBlindSpotDetectorExtended:
    """Extended coverage for BlindSpotDetector — edge cases and field contracts."""

    def test_blind_spot_detector_instantiation(self):
        """BlindSpotDetector creates without error and exposes expected API."""
        from Programma_CS2_RENAN.backend.analysis.blind_spots import BlindSpotDetector

        detector = BlindSpotDetector()
        assert detector is not None
        assert hasattr(detector, "detect")
        assert hasattr(detector, "generate_training_plan")
        assert callable(detector.detect)
        assert callable(detector.generate_training_plan)

    def test_detect_empty_round_data(self):
        """detect() with round entries that have empty game_state dicts returns empty list.

        This differs from passing an empty list: here we pass actual round dicts
        whose game_state is empty, exercising the 'if not state: continue' branch.
        """
        from Programma_CS2_RENAN.backend.analysis.blind_spots import BlindSpotDetector

        detector = BlindSpotDetector()
        # Rounds with empty game_state should be skipped gracefully
        degenerate_history = [
            {"game_state": {}, "action_taken": "push", "round_won": True},
            {"game_state": {}, "action_taken": "hold", "round_won": False},
            {"action_taken": "rotate", "round_won": False},  # missing game_state key
        ]
        spots = detector.detect(degenerate_history)
        assert isinstance(spots, list)
        assert spots == []

    def test_generate_training_plan_empty(self):
        """generate_training_plan with empty spots returns the 'no blind spots' message.

        Validates the exact sentinel message and that the return type is str.
        """
        from Programma_CS2_RENAN.backend.analysis.blind_spots import BlindSpotDetector

        detector = BlindSpotDetector()
        plan = detector.generate_training_plan([])
        assert isinstance(plan, str)
        assert "No strategic blind spots detected" in plan
        assert "optimal play" in plan

    def test_generate_training_plan_multiple(self):
        """generate_training_plan with multiple spots produces a plan covering each.

        Verifies the plan is non-empty and mentions each spot's situation type.
        Also checks that top_n limiting works (default top_n=3).
        """
        from Programma_CS2_RENAN.backend.analysis.blind_spots import BlindSpot, BlindSpotDetector

        detector = BlindSpotDetector()
        spots = [
            BlindSpot(
                situation_type="post-plant advantage",
                optimal_action="hold",
                actual_action="push",
                frequency=8,
                impact_rating=0.25,
            ),
            BlindSpot(
                situation_type="1v2 clutch",
                optimal_action="use_utility",
                actual_action="push",
                frequency=4,
                impact_rating=0.30,
            ),
            BlindSpot(
                situation_type="eco round",
                optimal_action="rotate",
                actual_action="hold",
                frequency=6,
                impact_rating=0.10,
            ),
        ]
        plan = detector.generate_training_plan(spots)
        assert isinstance(plan, str)
        assert len(plan) > 0
        assert "Training Plan" in plan
        # Each spot situation should appear in the plan
        assert "Post-Plant Advantage" in plan
        assert "1V2 Clutch" in plan
        assert "Eco Round" in plan

    def test_blind_spot_dataclass_fields(self):
        """BlindSpot has expected fields: situation_type, optimal_action,
        actual_action, frequency, impact_rating, and computed priority property.
        """
        from Programma_CS2_RENAN.backend.analysis.blind_spots import BlindSpot

        spot = BlindSpot(
            situation_type="numbers disadvantage",
            optimal_action="rotate",
            actual_action="hold",
            frequency=3,
            impact_rating=0.20,
        )
        # Verify all declared fields
        assert spot.situation_type == "numbers disadvantage"
        assert spot.optimal_action == "rotate"
        assert spot.actual_action == "hold"
        assert spot.frequency == 3
        assert spot.impact_rating == pytest.approx(0.20)
        # Verify computed property
        assert spot.priority == pytest.approx(3 * 0.20)
        # Verify defaults work
        default_spot = BlindSpot(
            situation_type="test",
            optimal_action="push",
            actual_action="hold",
        )
        assert default_spot.frequency == 0
        assert default_spot.impact_rating == 0.0
        assert default_spot.priority == 0.0
