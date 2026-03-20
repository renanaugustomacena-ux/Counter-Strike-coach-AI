"""
Test coaching service fallback chain (P9-03).

Validates that the CoachingService correctly selects modes and
transitions through the fallback chain:

    COPER → Hybrid → Traditional+RAG → Traditional

Each test patches only the external boundaries (DB, experience bank,
hybrid engine) to isolate fallback logic from real infrastructure.
"""

import logging
from unittest.mock import MagicMock, call, patch

import pytest


@pytest.fixture
def coaching_service(mock_db_manager):
    """CoachingService with in-memory DB and all modes disabled by default."""
    with patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
        return_value=mock_db_manager,
    ):
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        svc = CoachingService()
        # Start with everything off — tests enable selectively
        svc.use_coper = False
        svc.use_hybrid = False
        svc.use_rag = False
        svc.db_manager = mock_db_manager
        return svc


@pytest.fixture
def deviations():
    return {"avg_adr": -15.0, "avg_kills": -3.0, "accuracy": 0.05}


@pytest.fixture
def player_stats():
    return {"avg_kills": 18.0, "avg_adr": 75.0, "avg_hs": 0.45, "rating": 1.02}


@pytest.fixture
def tick_data():
    return {
        "team": "CT",
        "position_area": "B_site",
        "health": 85,
        "teammates_alive": 4,
        "enemies_alive": 3,
        "action": "hold",
        "outcome": "survived",
    }


# ───────────────────────────────────────────────────────────
#  Mode Selection Tests
# ───────────────────────────────────────────────────────────


class TestModeSelection:
    """Verify correct mode is selected based on flags and data availability."""

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[],
    )
    def test_traditional_mode_when_all_flags_off(self, mock_gen, coaching_service, deviations):
        """With all modes disabled, Traditional is used (generate_corrections called)."""
        coaching_service.generate_new_insights(
            player_name="TestPlayer",
            demo_name="test.dem",
            deviations=deviations,
            rounds_played=15,
        )
        mock_gen.assert_called_once_with(deviations, 15)

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service._save_corrections_as_insights",
    )
    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[{"feature": "aim", "weighted_z": -1.5}],
    )
    def test_traditional_rag_mode_calls_enhance(
        self, mock_gen, mock_save, coaching_service, deviations
    ):
        """With USE_RAG_COACHING=True, _enhance_with_rag is called."""
        coaching_service.use_rag = True

        with patch.object(coaching_service, "_enhance_with_rag", return_value=[]) as mock_rag:
            coaching_service.generate_new_insights(
                player_name="TestPlayer",
                demo_name="test.dem",
                deviations=deviations,
                rounds_played=15,
                map_name="de_mirage",
            )
            mock_rag.assert_called_once()

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[],
    )
    def test_hybrid_selected_over_traditional(
        self, mock_gen, coaching_service, deviations, player_stats
    ):
        """Hybrid is selected when flag is on and player_stats is provided."""
        coaching_service.use_hybrid = True

        with patch.object(coaching_service, "_generate_hybrid_insights") as mock_hybrid:
            coaching_service.generate_new_insights(
                player_name="TestPlayer",
                demo_name="test.dem",
                deviations=deviations,
                rounds_played=15,
                player_stats=player_stats,
            )
            mock_hybrid.assert_called_once()
            # Traditional generate_corrections should NOT be called
            mock_gen.assert_not_called()

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[],
    )
    def test_coper_selected_over_hybrid(
        self, mock_gen, coaching_service, deviations, player_stats, tick_data
    ):
        """COPER takes priority when all preconditions are met."""
        coaching_service.use_coper = True
        coaching_service.use_hybrid = True

        with patch.object(coaching_service, "_generate_coper_insights") as mock_coper:
            coaching_service.generate_new_insights(
                player_name="TestPlayer",
                demo_name="test.dem",
                deviations=deviations,
                rounds_played=15,
                player_stats=player_stats,
                map_name="de_mirage",
                tick_data=tick_data,
            )
            mock_coper.assert_called_once()
            mock_gen.assert_not_called()

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[],
    )
    def test_coper_falls_to_hybrid_without_tick_data(
        self, mock_gen, coaching_service, deviations, player_stats
    ):
        """COPER requires tick_data; without it, falls to Hybrid."""
        coaching_service.use_coper = True
        coaching_service.use_hybrid = True

        with patch.object(coaching_service, "_generate_hybrid_insights") as mock_hybrid:
            coaching_service.generate_new_insights(
                player_name="TestPlayer",
                demo_name="test.dem",
                deviations=deviations,
                rounds_played=15,
                player_stats=player_stats,
                map_name="de_mirage",
                tick_data=None,  # No tick_data → COPER precondition not met
            )
            mock_hybrid.assert_called_once()

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[],
    )
    def test_coper_falls_to_traditional_without_map_and_ticks(
        self, mock_gen, coaching_service, deviations
    ):
        """COPER requires map_name AND tick_data; without both, falls to Traditional."""
        coaching_service.use_coper = True
        coaching_service.use_hybrid = False

        coaching_service.generate_new_insights(
            player_name="TestPlayer",
            demo_name="test.dem",
            deviations=deviations,
            rounds_played=15,
        )
        mock_gen.assert_called_once()


# ───────────────────────────────────────────────────────────
#  Fallback Chain Tests (exception-driven)
# ───────────────────────────────────────────────────────────


class TestFallbackChain:
    """Verify exception-triggered fallbacks between modes."""

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[],
    )
    def test_coper_exception_falls_to_hybrid(
        self, mock_gen, coaching_service, deviations, player_stats, tick_data
    ):
        """When COPER raises internally, Hybrid is attempted."""
        coaching_service.use_coper = True
        coaching_service.use_hybrid = True

        # Patch ExperienceBank import to fail — triggers COPER's except block
        with patch.dict(
            "sys.modules",
            {"Programma_CS2_RENAN.backend.knowledge.experience_bank": None},
        ):
            with patch.object(coaching_service, "_generate_hybrid_insights") as mock_hybrid:
                coaching_service.generate_new_insights(
                    player_name="TestPlayer",
                    demo_name="test.dem",
                    deviations=deviations,
                    rounds_played=15,
                    player_stats=player_stats,
                    map_name="de_mirage",
                    tick_data=tick_data,
                )
                # COPER internally catches, checks use_hybrid → calls Hybrid
                mock_hybrid.assert_called_once()

    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service._save_corrections_as_insights",
    )
    @patch(
        "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
        return_value=[{"feature": "aim", "weighted_z": -1.0}],
    )
    def test_coper_exception_falls_to_traditional_when_hybrid_off(
        self, mock_gen, mock_save, coaching_service, deviations, tick_data
    ):
        """When COPER fails and Hybrid is off, Traditional is used."""
        coaching_service.use_coper = True
        coaching_service.use_hybrid = False

        with patch.dict(
            "sys.modules",
            {"Programma_CS2_RENAN.backend.knowledge.experience_bank": None},
        ):
            coaching_service.generate_new_insights(
                player_name="TestPlayer",
                demo_name="test.dem",
                deviations=deviations,
                rounds_played=15,
                map_name="de_mirage",
                tick_data=tick_data,
            )
            # Traditional fallback should call generate_corrections
            mock_gen.assert_called_once_with(deviations, 15)


# ───────────────────────────────────────────────────────────
#  Docstring & Architecture Tests
# ───────────────────────────────────────────────────────────


class TestArchitecturalDocumentation:
    """Verify that P9-03 documentation requirements are met."""

    def test_coaching_service_has_mode_docstring(self):
        """CoachingService class must document the mode priority chain."""
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        doc = CoachingService.__doc__
        assert doc is not None, "CoachingService missing class docstring"
        assert "COPER" in doc
        assert "Hybrid" in doc
        assert "Traditional" in doc
        assert "Fallback" in doc

    def test_generate_new_insights_has_mode_priority_docstring(self):
        """generate_new_insights must document mode priority."""
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        doc = CoachingService.generate_new_insights.__doc__
        assert doc is not None
        assert "COPER" in doc
        assert "priority" in doc.lower() or "mode" in doc.lower()

    def test_singleton_factory_exists(self):
        """get_coaching_service() singleton factory must exist."""
        from Programma_CS2_RENAN.backend.services.coaching_service import get_coaching_service

        assert callable(get_coaching_service)
