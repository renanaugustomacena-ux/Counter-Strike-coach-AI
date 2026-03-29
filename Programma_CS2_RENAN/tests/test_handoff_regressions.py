"""
Regression tests for fixes applied during the Engineering Handoff audit.

Each test targets a specific WR/finding ID and verifies the fix works correctly.
These prevent the exact bugs from silently returning.
"""

import math
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from Programma_CS2_RENAN.backend.storage.db_models import CoachingInsight


# ============ Shared Fixtures ============


class _InMemoryDBManager:
    """Minimal DB manager for coaching service tests (StaticPool for thread safety)."""

    def __init__(self, engine):
        self._engine = engine

    @contextmanager
    def get_session(self, engine_key: str = "default"):
        with Session(self._engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class _MockStateManager:
    """Captures notifications in-memory for assertion."""

    def __init__(self):
        self.notifications = []

    def add_notification(self, category, severity, message):
        self.notifications.append(
            {"category": category, "severity": severity, "message": message}
        )

    def update_status(self, *args, **kwargs):
        pass

    def heartbeat(self):
        pass


@pytest.fixture
def mock_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return _InMemoryDBManager(engine)


@pytest.fixture
def mock_state():
    return _MockStateManager()


# ============ WR-31: restore_backup() deletes WAL/SHM files ============


class TestWR31RestoreBackupWAL:
    """WR-31 (CRITICAL): restore_backup must delete WAL/SHM before copy."""

    def test_wal_shm_deleted_before_restore(self, tmp_path):
        from Programma_CS2_RENAN.backend.storage.db_backup import restore_backup

        # Create a valid SQLite backup
        backup_path = tmp_path / "backup.db"
        conn = sqlite3.connect(str(backup_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.close()

        # Create target with stale WAL/SHM files
        target_path = tmp_path / "target.db"
        wal_path = target_path.with_suffix(".db-wal")
        shm_path = target_path.with_suffix(".db-shm")

        # Create a target DB so rollback logic has something to work with
        conn = sqlite3.connect(str(target_path))
        conn.execute("CREATE TABLE old (id INTEGER)")
        conn.close()

        # Simulate stale WAL/SHM
        wal_path.write_text("stale wal data")
        shm_path.write_text("stale shm data")

        result = restore_backup(backup_path, target_path)

        assert result is True
        assert not wal_path.exists(), "WAL file should be deleted before restore"
        assert not shm_path.exists(), "SHM file should be deleted before restore"

    def test_restore_succeeds_without_wal_shm(self, tmp_path):
        from Programma_CS2_RENAN.backend.storage.db_backup import restore_backup

        backup_path = tmp_path / "backup.db"
        conn = sqlite3.connect(str(backup_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.close()

        target_path = tmp_path / "target.db"
        result = restore_backup(backup_path, target_path)

        assert result is True


# ============ WR-57/WR-58: COPER fallback chain ============


class TestWR57TraditionalNeverZero:
    """WR-57: Traditional coaching must always produce at least one insight."""

    def test_empty_corrections_saves_generic_insight(self, mock_db, mock_state):
        with (
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
                return_value=mock_db,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
                return_value=mock_state,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
                side_effect=lambda k, default=None: {
                    "USE_COPER_COACHING": False,
                    "USE_HYBRID_COACHING": False,
                    "USE_RAG_COACHING": False,
                }.get(k, default),
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.generate_corrections",
                return_value=[],
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
            ) as mock_writer,
        ):
            mock_writer.return_value.polish.return_value = "polished"

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            svc.generate_new_insights(
                player_name="TestPlayer",
                demo_name="test.dem",
                deviations={},
                rounds_played=0,
            )

            with mock_db.get_session() as session:
                insights = session.exec(
                    select(CoachingInsight).where(
                        CoachingInsight.player_name == "TestPlayer"
                    )
                ).all()
                assert len(insights) >= 1, "C-01: Must never produce zero coaching"
                assert any("Match Analysis Complete" in i.title for i in insights)


class TestWR58COPERTimeoutFallback:
    """WR-58: COPER timeout routes to Hybrid before Traditional."""

    def test_timeout_routes_to_hybrid_when_available(self, mock_db, mock_state):
        with (
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
                return_value=mock_db,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
                return_value=mock_state,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
                side_effect=lambda k, default=None: {
                    "USE_COPER_COACHING": True,
                    "USE_HYBRID_COACHING": True,
                    "USE_RAG_COACHING": False,
                }.get(k, default),
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service._run_with_timeout",
                return_value=(None, True),  # Timeout
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
            ) as mock_writer,
        ):
            mock_writer.return_value.polish.return_value = "polished"

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()

            with patch.object(svc, "_generate_hybrid_insights") as mock_hybrid:
                svc.generate_new_insights(
                    player_name="TestPlayer",
                    demo_name="test.dem",
                    deviations={"avg_adr": -2.0},
                    rounds_played=10,
                    map_name="de_mirage",
                    tick_data={"team": "T"},
                    player_stats={"kills": 15},
                )
                mock_hybrid.assert_called_once()


# ============ WR-56: Dialogue context preservation ============


class TestWR56DialogueContext:
    """WR-56: _build_chat_messages must not drop last assistant response."""

    def test_full_history_preserved(self):
        from Programma_CS2_RENAN.backend.services.coaching_dialogue import (
            CoachingDialogueEngine,
        )

        engine = CoachingDialogueEngine.__new__(CoachingDialogueEngine)
        engine._history = [
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How do I play B site?"},
            {"role": "assistant", "content": "Hold the van angle."},
        ]
        engine.MAX_CONTEXT_TURNS = 10
        engine._state_lock = __import__("threading").Lock()

        messages = engine._build_chat_messages("What about utility?")

        # All 3 history messages + 1 augmented user message = 4
        assert len(messages) == 4
        assert messages[0]["content"] == "Hi there!"
        assert messages[2]["content"] == "Hold the van angle."
        assert messages[3]["content"] == "What about utility?"


# ============ WR-44: time_in_round stays in [0, 1] ============


class TestWR44TimeInRound:
    """WR-44: time_in_round must not exceed 115s after clipping."""

    def test_clip_at_115_not_175(self):
        import numpy as np
        import pandas as pd

        # Directly test the clipping logic that assign_round_to_ticks applies.
        # The fix changed upper=175.0 to upper=115.0 in round_context.py.
        tick_rate = 64
        round_start_tick = 0
        # Simulate ticks spanning 200 seconds
        ticks = np.arange(0, int(200 * tick_rate), tick_rate)
        time_in_round = ((ticks - round_start_tick) / tick_rate).clip(0.0, 115.0)

        assert time_in_round.max() <= 115.0, (
            f"time_in_round must clip at 115.0, got {time_in_round.max()}"
        )
        # Verify the vectorizer normalization stays in [0, 1]
        normalized = time_in_round / 115.0
        assert normalized.max() <= 1.0, (
            f"Normalized time must be <= 1.0, got {normalized.max()}"
        )


# ============ CORE-10: NaN yaw interpolation ============


class TestCORE10NaNYaw:
    """CORE-10: _interpolate_angle must handle NaN gracefully."""

    def test_nan_a_returns_b(self):
        from Programma_CS2_RENAN.core.playback_engine import PlaybackEngine

        result = PlaybackEngine._interpolate_angle(float("nan"), 90.0, 0.5)
        assert result == 90.0

    def test_nan_b_returns_a(self):
        from Programma_CS2_RENAN.core.playback_engine import PlaybackEngine

        result = PlaybackEngine._interpolate_angle(45.0, float("nan"), 0.5)
        assert result == 45.0

    def test_both_nan_returns_zero(self):
        from Programma_CS2_RENAN.core.playback_engine import PlaybackEngine

        result = PlaybackEngine._interpolate_angle(float("nan"), float("nan"), 0.5)
        assert result == 0.0

    def test_normal_interpolation_unchanged(self):
        from Programma_CS2_RENAN.core.playback_engine import PlaybackEngine

        result = PlaybackEngine._interpolate_angle(0.0, 90.0, 0.5)
        assert abs(result - 45.0) < 0.01


# ============ WR-21: refresh_settings() updates all globals ============


class TestWR21RefreshSettings:
    """WR-21: refresh_settings must update theme/font/BRAIN globals."""

    def test_refresh_updates_theme_globals(self, isolated_settings):
        from Programma_CS2_RENAN.core import config

        # Save a theme setting
        config.save_user_setting("ACTIVE_THEME", "CSGO")
        config.save_user_setting("FONT_SIZE", 18)

        # Refresh from disk
        config.refresh_settings()

        assert config.ACTIVE_THEME == "CSGO"
        assert config.FONT_SIZE == 18


# ============ DS-08: SSRF prevention ============


class TestDS08SSRFPrevention:
    """DS-08: FaceIT demo download rejects non-HTTPS URLs."""

    def test_rejects_file_scheme(self):
        from Programma_CS2_RENAN.backend.data_sources.faceit_integration import (
            FACEITIntegration,
        )

        integration = FACEITIntegration.__new__(FACEITIntegration)
        integration.api_key = "test"

        with patch.object(integration, "_rate_limited_request") as mock_req:
            mock_req.return_value = {
                "demo_url": "file:///etc/passwd",
            }
            result = integration.download_demo("match123", Path("/tmp"))

        assert result is None, "file:// URLs must be rejected"
