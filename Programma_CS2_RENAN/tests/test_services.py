"""
Service-layer tests for Macena CS2 Analyzer.

Tests service instantiation and API contracts. Anything that WRITES goes
through an in-memory database: the coaching test below used to run against
the real ``database.db`` and left 48 ``__test_nonexistent_player__`` insight
rows behind (D-50; ``conftest.py`` now trips on any such write).
"""

import pytest


@pytest.fixture
def isolated_coaching_db(monkeypatch):
    """Route CoachingService's DB handle to a throwaway in-memory database."""
    import Programma_CS2_RENAN.backend.services.coaching_service as coaching_service
    from Programma_CS2_RENAN.tests._memory_db import MemoryDB

    db = MemoryDB()
    monkeypatch.setattr(coaching_service, "get_db_manager", lambda: db)
    return db


class TestCoachingService:
    def test_instantiation(self, isolated_coaching_db):
        """CoachingService can be instantiated."""
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        cs = CoachingService()
        assert callable(getattr(cs, "generate_new_insights", None))

    def test_generate_new_insights_graceful_empty(self, isolated_coaching_db):
        """CoachingService.generate_new_insights handles empty input gracefully."""
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService
        from Programma_CS2_RENAN.backend.storage.db_models import CoachingInsight

        cs = CoachingService()
        result = cs.generate_new_insights(
            player_name="__test_nonexistent_player__",
            demo_name="__test.dem",
            deviations={},
            rounds_played=0,
        )
        # With empty deviations, should return None or an empty list
        assert result is None or isinstance(result, list)
        # Whatever it wrote landed in the throwaway DB, not in database.db.
        with isolated_coaching_db.get_session() as session:
            written = session.exec(select(CoachingInsight)).all()
        assert all(r.player_name == "__test_nonexistent_player__" for r in written)


class TestAnalysisService:
    def test_instantiation(self):
        """AnalysisService singleton can be obtained."""
        from Programma_CS2_RENAN.backend.services.analysis_service import get_analysis_service

        svc = get_analysis_service()
        assert callable(getattr(svc, "analyze_latest_performance", None))

    def test_drift_check_callable(self):
        """AnalysisService drift detection returns a result."""
        from Programma_CS2_RENAN.backend.services.analysis_service import get_analysis_service

        svc = get_analysis_service()
        result = svc.check_for_drift(player_name="__test_nonexistent__")
        assert isinstance(result, dict), f"check_for_drift should return dict, got {type(result)}"


class TestVisualizationService:
    def test_instantiation(self):
        """VisualizationService can be instantiated."""
        from Programma_CS2_RENAN.backend.services.visualization_service import VisualizationService

        viz = VisualizationService()
        assert callable(getattr(viz, "plot_comparison_v2", None))

    def test_plot_with_real_data(self, seeded_db_session):
        """VisualizationService plot_comparison_v2 works with seeded DB data."""
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.services.visualization_service import VisualizationService
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

        records = seeded_db_session.exec(select(PlayerMatchStats).limit(2)).all()
        assert len(records) >= 2, "Seeded DB should have at least 2 PlayerMatchStats"

        r1, r2 = records[0], records[1]
        # Keys must match numeric_feats in visualization_service.py
        stats1 = {
            "avg_kills": r1.avg_kills,
            "avg_adr": r1.avg_adr,
            "avg_hs": r1.avg_hs,
            "avg_kast": r1.avg_kast,
            "accuracy": r1.accuracy,
        }
        stats2 = {
            "avg_kills": r2.avg_kills,
            "avg_adr": r2.avg_adr,
            "avg_hs": r2.avg_hs,
            "avg_kast": r2.avg_kast,
            "accuracy": r2.accuracy,
        }

        viz = VisualizationService()
        buf = viz.plot_comparison_v2(r1.player_name, r2.player_name, stats1, stats2)
        assert buf is not None
        assert buf.getbuffer().nbytes > 100, "Plot buffer should contain meaningful PNG data"


class TestCoachingDialogueEngine:
    def test_instantiation(self):
        """CoachingDialogueEngine can be instantiated."""
        from Programma_CS2_RENAN.backend.services.coaching_dialogue import CoachingDialogueEngine

        cde = CoachingDialogueEngine()
        assert isinstance(cde.is_available, bool)
        assert callable(getattr(cde, "start_session", None))
        assert callable(getattr(cde, "respond", None))
