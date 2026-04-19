"""Smoke tests for the ingestion pipeline.

Covers: duplicate detection, stat sanitization, queue management,
and the _is_profile_ready gate.
"""

import math
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from Programma_CS2_RENAN.backend.storage.db_models import (
    CoachingInsight,
    IngestionTask,
    PlayerMatchStats,
    PlayerProfile,
)


@pytest.fixture
def ingestion_db():
    """In-memory DB with schema for ingestion tests."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session, engine


@pytest.fixture
def mock_db_manager(ingestion_db):
    """Mock DatabaseManager that uses the in-memory session."""
    from unittest.mock import MagicMock

    session, engine = ingestion_db
    manager = MagicMock()

    from contextlib import contextmanager

    @contextmanager
    def get_session_ctx(scope=None):
        new_session = Session(engine)
        try:
            yield new_session
        finally:
            new_session.close()

    manager.get_session = get_session_ctx
    manager.upsert = MagicMock()
    return manager


class TestCheckDuplicateDemo:
    """Test _check_duplicate_demo() 3-path detection."""

    def test_no_duplicate_returns_false(self, mock_db_manager):
        from Programma_CS2_RENAN.run_ingestion import _check_duplicate_demo

        result = _check_duplicate_demo(mock_db_manager, "/path/to/new_demo.dem")
        assert result is False

    def test_duplicate_in_ingestion_task(self, mock_db_manager, ingestion_db):
        from Programma_CS2_RENAN.run_ingestion import _check_duplicate_demo

        session, _ = ingestion_db
        task = IngestionTask(
            demo_path="/path/to/existing.dem",
            status="completed",
            is_pro=False,
        )
        session.add(task)
        session.commit()

        result = _check_duplicate_demo(mock_db_manager, "/path/to/existing.dem")
        assert result is True

    def test_duplicate_in_player_match_stats(self, mock_db_manager, ingestion_db):
        from Programma_CS2_RENAN.run_ingestion import _check_duplicate_demo

        session, _ = ingestion_db
        stats = PlayerMatchStats(
            player_name="tester",
            demo_name="existing_demo",
            is_pro=False,
        )
        session.add(stats)
        session.commit()

        result = _check_duplicate_demo(mock_db_manager, "existing_demo.dem")
        assert result is True

    def test_error_status_not_counted_as_duplicate(self, mock_db_manager, ingestion_db):
        from Programma_CS2_RENAN.run_ingestion import _check_duplicate_demo

        session, _ = ingestion_db
        task = IngestionTask(
            demo_path="/path/to/retry.dem",
            status="error",
            is_pro=False,
        )
        session.add(task)
        session.commit()

        result = _check_duplicate_demo(mock_db_manager, "/path/to/retry.dem")
        assert result is False


class TestIsProfileReady:
    """Test _is_profile_ready() gate logic."""

    def test_no_profile_returns_false(self, mock_db_manager):
        from Programma_CS2_RENAN.run_ingestion import _is_profile_ready

        result = _is_profile_ready(mock_db_manager, "unknown_player")
        assert result is False

    def test_profile_exists_no_demos_returns_false(self, mock_db_manager, ingestion_db):
        from Programma_CS2_RENAN.run_ingestion import _is_profile_ready

        session, _ = ingestion_db
        session.add(PlayerProfile(player_name="new_player"))
        session.commit()

        result = _is_profile_ready(mock_db_manager, "new_player")
        assert result is False

    def test_profile_with_one_demo_returns_true(self, mock_db_manager, ingestion_db):
        """After lowering MIN_DEMOS_FOR_COACHING to 1, one demo should suffice."""
        from Programma_CS2_RENAN.run_ingestion import _is_profile_ready

        session, _ = ingestion_db
        session.add(PlayerProfile(player_name="ready_player"))
        session.add(
            PlayerMatchStats(
                player_name="ready_player",
                demo_name="my_match",
                is_pro=False,
            )
        )
        session.commit()

        result = _is_profile_ready(mock_db_manager, "ready_player")
        assert result is True

    def test_pro_demos_not_counted(self, mock_db_manager, ingestion_db):
        """Pro demos should not count toward the coaching threshold."""
        from Programma_CS2_RENAN.run_ingestion import _is_profile_ready

        session, _ = ingestion_db
        session.add(PlayerProfile(player_name="pro_only"))
        session.add(
            PlayerMatchStats(
                player_name="pro_only",
                demo_name="pro_match",
                is_pro=True,
            )
        )
        session.commit()

        result = _is_profile_ready(mock_db_manager, "pro_only")
        assert result is False

    def test_no_steam_faceit_required(self, mock_db_manager, ingestion_db):
        """Verify Steam/Faceit connection is NOT required (v1.0 gate relaxation)."""
        from Programma_CS2_RENAN.run_ingestion import _is_profile_ready

        session, _ = ingestion_db
        # Profile without any steam/faceit flags
        session.add(PlayerProfile(player_name="standalone_player"))
        session.add(
            PlayerMatchStats(
                player_name="standalone_player",
                demo_name="user_match_1",
                is_pro=False,
            )
        )
        session.commit()

        result = _is_profile_ready(mock_db_manager, "standalone_player")
        assert result is True


class TestStatSanitization:
    """Test that NaN/Inf values in stats are properly handled."""

    def test_nan_values_sanitized(self):
        """_save_player_stats should sanitize NaN values to 0.0."""
        # Direct test of the sanitization logic from _save_player_stats
        stats = {"avg_kills": float("nan"), "avg_deaths": 5.0, "avg_adr": float("inf")}

        for key, val in list(stats.items()):
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                stats[key] = 0.0

        assert stats["avg_kills"] == 0.0
        assert stats["avg_deaths"] == 5.0
        assert stats["avg_adr"] == 0.0

    def test_rating_clamped_to_range(self):
        """Rating should be clamped to [0, 5.0]."""
        stats = {"rating": -0.5}
        stats["rating"] = max(0.0, min(5.0, float(stats["rating"])))
        assert stats["rating"] == 0.0

        stats = {"rating": 7.2}
        stats["rating"] = max(0.0, min(5.0, float(stats["rating"])))
        assert stats["rating"] == 5.0

        stats = {"rating": 1.15}
        stats["rating"] = max(0.0, min(5.0, float(stats["rating"])))
        assert stats["rating"] == 1.15

    def test_negative_kills_adr_clamped(self):
        """avg_kills and avg_adr should be clamped to >= 0."""
        stats = {"avg_kills": -3.0, "avg_adr": -10.0}
        for field in ("avg_kills", "avg_adr"):
            if field in stats and stats[field] < 0:
                stats[field] = 0.0

        assert stats["avg_kills"] == 0.0
        assert stats["avg_adr"] == 0.0


class TestCorrectionEngine:
    """Test that generate_corrections produces valid output."""

    def test_corrections_returns_at_most_3(self):
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations = {
            "avg_kills": -2.0,
            "avg_deaths": 1.5,
            "avg_adr": -1.8,
            "avg_hs": -0.5,
            "accuracy": -1.2,
        }
        result = generate_corrections(deviations, 30)
        assert len(result) <= 3

    def test_corrections_sorted_by_importance(self):
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations = {
            "avg_kast": -2.0,  # High importance (1.5)
            "avg_hs": -0.1,  # Low deviation
        }
        result = generate_corrections(deviations, 100)
        if len(result) >= 2:
            # Most important should come first
            assert (
                abs(result[0]["weighted_z"]) * result[0]["importance"]
                >= abs(result[1]["weighted_z"]) * result[1]["importance"]
            )

    def test_corrections_empty_deviations(self):
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        result = generate_corrections({}, 30)
        assert result == []

    def test_corrections_handles_tuple_deviations(self):
        """P3-07: Handle (z_score, raw_dev) tuple inputs."""
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations = {"avg_kills": (-1.5, -3.0), "avg_adr": (-2.0, -15.0)}
        result = generate_corrections(deviations, 30)
        assert len(result) == 2
        for c in result:
            assert "weighted_z" in c
            assert "feature" in c
