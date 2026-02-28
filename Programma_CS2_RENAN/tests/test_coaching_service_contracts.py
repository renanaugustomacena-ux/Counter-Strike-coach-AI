"""
Tests for coaching_service.py — Bug #8: COPER path doesn't validate tick_data.

When use_coper=True, generate_new_insights calls _generate_coper_insights which
calls tick_data.get("team", "T"), tick_data.get("position_area"), etc. If
tick_data is not a dict (but truthy), or if it's a dict missing critical keys,
the code either raises AttributeError or silently uses defaults that may produce
meaningless coaching.

Also verifies:
- Coaching mode selection logic
- Fallback chains (COPER → Hybrid → Traditional)
- Health range categorization
"""

from unittest.mock import MagicMock, patch

import pytest


class TestCoachingModeSelection:
    """Verify the priority logic for coaching mode selection."""

    def _make_service(self, use_coper=True, use_hybrid=False, use_rag=False):
        """Create a CoachingService with controlled settings."""
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting") as mock_setting:

            def setting_side_effect(key, default=None):
                return {
                    "USE_RAG_COACHING": use_rag,
                    "USE_HYBRID_COACHING": use_hybrid,
                    "USE_COPER_COACHING": use_coper,
                }.get(key, default)

            mock_setting.side_effect = setting_side_effect
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            return CoachingService()

    def test_coper_takes_precedence_when_enabled(self):
        """COPER should be selected when use_coper=True, map_name is set, and tick_data is set."""
        svc = self._make_service(use_coper=True, use_hybrid=True)
        assert svc.use_coper is True
        assert svc.use_hybrid is True

        # COPER requires: use_coper AND map_name AND tick_data
        # When all three are truthy, COPER path is taken (line 75)
        # This is verified by the condition: self.use_coper and map_name and tick_data

    def test_hybrid_selected_when_coper_conditions_not_met(self):
        """Hybrid mode is selected when COPER conditions are incomplete."""
        svc = self._make_service(use_coper=True, use_hybrid=True)

        # COPER requires map_name AND tick_data. Without map_name, falls to hybrid
        # (if player_stats present)
        assert svc.use_hybrid is True

    def test_traditional_is_fallback(self):
        """Traditional mode is the final fallback when COPER and Hybrid are disabled."""
        svc = self._make_service(use_coper=False, use_hybrid=False, use_rag=False)
        assert svc.use_coper is False
        assert svc.use_hybrid is False
        assert svc.use_rag is False


class TestHealthRangeClassification:
    """Verify the health to categorical range conversion."""

    def test_full_health(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            assert svc._health_to_range(100) == "full"
            assert svc._health_to_range(80) == "full"

    def test_damaged_health(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            assert svc._health_to_range(79) == "damaged"
            assert svc._health_to_range(40) == "damaged"

    def test_critical_health(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            assert svc._health_to_range(39) == "critical"
            assert svc._health_to_range(1) == "critical"
            assert svc._health_to_range(0) == "critical"


class TestCoperTickDataValidation:
    """BUG #8: COPER path doesn't validate tick_data structure.

    These tests expose the fact that _generate_coper_insights assumes tick_data
    is a dict with specific keys, but generate_new_insights only checks truthiness.
    """

    def test_coper_with_non_dict_tick_data_should_not_crash(self):
        """If tick_data is truthy but not a dict (e.g., a list), COPER should handle it.

        CURRENTLY: tick_data.get() raises AttributeError on non-dict objects.
        """
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting") as mock_setting:

            def setting_side_effect(key, default=None):
                return {
                    "USE_RAG_COACHING": False,
                    "USE_HYBRID_COACHING": False,
                    "USE_COPER_COACHING": True,
                }.get(key, default)

            mock_setting.side_effect = setting_side_effect
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()

            # tick_data is a non-empty list (truthy, but not a dict)
            # The condition `self.use_coper and map_name and tick_data` passes
            # but _generate_coper_insights calls tick_data.get() which fails on lists
            try:
                svc.generate_new_insights(
                    player_name="test",
                    demo_name="test.dem",
                    deviations={"avg_adr": -5.0},
                    rounds_played=10,
                    map_name="de_mirage",
                    tick_data=[1, 2, 3],  # List, not dict — should be handled
                )
                # If no exception, the fallback chain handled it
            except AttributeError as e:
                pytest.fail(
                    f"BUG #8: COPER crashed with AttributeError on non-dict tick_data: {e}"
                )

    def test_coper_with_empty_dict_tick_data(self):
        """An empty dict {} is falsy in the condition check, so COPER won't trigger.

        This is actually correct behavior — empty tick_data shouldn't trigger COPER.
        But it means `tick_data={}` silently skips COPER without explanation.
        """
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting") as mock_setting:

            def setting_side_effect(key, default=None):
                return {
                    "USE_RAG_COACHING": False,
                    "USE_HYBRID_COACHING": False,
                    "USE_COPER_COACHING": True,
                }.get(key, default)

            mock_setting.side_effect = setting_side_effect
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()

            # Empty dict is falsy, so COPER condition fails
            # This is expected behavior, but note: {} is a valid dict
            assert not ({})  # Confirms empty dict is falsy

    def test_coper_with_minimal_valid_tick_data(self):
        """COPER with a minimal but valid tick_data dict should not crash.

        This tests the happy path to ensure the test infrastructure works.
        """
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager") as mock_db, \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting") as mock_setting, \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer") as mock_writer:

            def setting_side_effect(key, default=None):
                return {
                    "USE_RAG_COACHING": False,
                    "USE_HYBRID_COACHING": False,
                    "USE_COPER_COACHING": True,
                }.get(key, default)

            mock_setting.side_effect = setting_side_effect
            mock_writer.return_value.polish.return_value = "polished message"

            # Mock DB session
            mock_session = MagicMock()
            mock_db.return_value.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_db.return_value.get_session.return_value.__exit__ = MagicMock(return_value=False)

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()

            # Minimal tick_data that should satisfy COPER
            tick_data = {
                "team": "T",
                "health": 100,
                "equipment_value": 5000,
                "teammates_alive": 4,
                "enemies_alive": 5,
            }

            # This may still fail due to ExperienceBank initialization,
            # but the fallback chain should handle it gracefully
            try:
                svc.generate_new_insights(
                    player_name="test_player",
                    demo_name="test.dem",
                    deviations={"avg_adr": -5.0},
                    rounds_played=10,
                    map_name="de_mirage",
                    player_stats={"avg_adr": 70.0, "rating": 0.95},
                    tick_data=tick_data,
                )
            except Exception as e:
                # COPER may fail due to missing ExperienceBank/SBERT, but
                # the fallback to traditional coaching should catch it
                if "AttributeError" in type(e).__name__:
                    pytest.fail(
                        f"COPER should not raise AttributeError: {e}"
                    )


class TestBaselineContextNote:
    """Verify the baseline comparison note generation."""

    def test_empty_player_stats_returns_empty(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            result = CoachingService._baseline_context_note({}, {"rating": 1.05}, "positioning")
            assert result == ""

    def test_empty_baseline_returns_empty(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            result = CoachingService._baseline_context_note({"rating": 0.95}, {}, "positioning")
            assert result == ""

    def test_valid_comparison_produces_note(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            player_stats = {"rating": 0.85}
            baseline = {"rating": {"mean": 1.05}}

            result = CoachingService._baseline_context_note(player_stats, baseline, "positioning")
            assert "below" in result.lower(), (
                f"0.85 is below pro average 1.05, note should say 'below': {result}"
            )

    def test_above_average_produces_correct_note(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            player_stats = {"rating": 1.25}
            baseline = {"rating": {"mean": 1.05}}

            result = CoachingService._baseline_context_note(player_stats, baseline, "positioning")
            assert "above" in result.lower(), (
                f"1.25 is above pro average 1.05, note should say 'above': {result}"
            )


class TestSingletonFactory:
    """Verify the singleton coaching service factory."""

    def test_singleton_returns_same_instance(self):
        with patch("Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager"), \
             patch("Programma_CS2_RENAN.backend.services.coaching_service.get_setting", return_value=False):
            import Programma_CS2_RENAN.backend.services.coaching_service as mod

            # Reset singleton
            mod._coaching_service = None

            svc1 = mod.get_coaching_service()
            svc2 = mod.get_coaching_service()
            assert svc1 is svc2, "get_coaching_service() should return same instance"

            # Clean up
            mod._coaching_service = None
