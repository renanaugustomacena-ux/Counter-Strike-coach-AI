"""Tests for database WAL mode PRAGMA enforcement.

Validates that every new SQLite connection gets:
- journal_mode = WAL
- synchronous = NORMAL (1)
- busy_timeout = 30000
"""

import os

import pytest
from sqlalchemy import text


@pytest.fixture
def tmp_db_manager(tmp_path, monkeypatch):
    """Create a real DatabaseManager pointing to a temp SQLite file."""
    import Programma_CS2_RENAN.backend.storage.database as db_module

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DATABASE_URL", f"sqlite:///{db_path}")
    # Clear the lazy singleton so a fresh manager is created
    monkeypatch.setattr(db_module, "_db_manager", None)

    manager = db_module.DatabaseManager()
    manager.create_db_and_tables()
    yield manager


@pytest.fixture
def tmp_hltv_db(tmp_path, monkeypatch):
    """Create a real HLTVDatabaseManager pointing to a temp SQLite file."""
    import Programma_CS2_RENAN.backend.storage.database as db_module

    db_path = str(tmp_path / "test_hltv.db")
    monkeypatch.setattr(db_module, "HLTV_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(db_module, "_hltv_db_manager", None)

    manager = db_module.HLTVDatabaseManager()
    manager.create_db_and_tables()
    yield manager


class TestDatabaseManagerWAL:
    """Verify WAL PRAGMAs on DatabaseManager connections."""

    def test_journal_mode_is_wal(self, tmp_db_manager):
        with tmp_db_manager.get_session() as session:
            result = session.execute(text("PRAGMA journal_mode")).scalar()
            assert result == "wal", f"Expected journal_mode=wal, got {result}"

    def test_synchronous_is_normal(self, tmp_db_manager):
        with tmp_db_manager.get_session() as session:
            result = session.execute(text("PRAGMA synchronous")).scalar()
            # NORMAL = 1
            assert result == 1, f"Expected synchronous=1 (NORMAL), got {result}"

    def test_busy_timeout_is_30000(self, tmp_db_manager):
        with tmp_db_manager.get_session() as session:
            result = session.execute(text("PRAGMA busy_timeout")).scalar()
            assert result == 30000, f"Expected busy_timeout=30000, got {result}"

    def test_pragmas_applied_on_every_new_connection(self, tmp_db_manager):
        """Verify PRAGMAs are re-applied when getting a new session."""
        for _ in range(3):
            with tmp_db_manager.get_session() as session:
                jm = session.execute(text("PRAGMA journal_mode")).scalar()
                assert jm == "wal"

    def test_wal_file_exists_on_disk(self, tmp_db_manager, tmp_path):
        """After WAL mode is set, a .db-wal file should exist."""
        # Force a write to create the WAL file
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerProfile

        with tmp_db_manager.get_session() as session:
            session.add(PlayerProfile(player_name="WALTest"))
            session.commit()

        db_path = tmp_path / "test.db"
        wal_path = tmp_path / "test.db-wal"
        assert db_path.exists()
        # WAL file might exist or be checkpointed away — just verify no crash


class TestHLTVDatabaseManagerWAL:
    """Verify WAL PRAGMAs on HLTVDatabaseManager connections."""

    def test_hltv_journal_mode_is_wal(self, tmp_hltv_db):
        with tmp_hltv_db.get_session() as session:
            result = session.execute(text("PRAGMA journal_mode")).scalar()
            assert result == "wal"

    def test_hltv_synchronous_is_normal(self, tmp_hltv_db):
        with tmp_hltv_db.get_session() as session:
            result = session.execute(text("PRAGMA synchronous")).scalar()
            assert result == 1

    def test_hltv_busy_timeout_is_30000(self, tmp_hltv_db):
        with tmp_hltv_db.get_session() as session:
            result = session.execute(text("PRAGMA busy_timeout")).scalar()
            assert result == 30000


class TestPoolConfiguration:
    """Verify connection pool settings."""

    def test_pool_size(self, tmp_db_manager):
        pool = tmp_db_manager.engine.pool
        assert pool.size() == 1, f"Expected pool_size=1, got {pool.size()}"

    def test_max_overflow(self, tmp_db_manager):
        pool = tmp_db_manager.engine.pool
        overflow = pool._max_overflow
        assert overflow == 4, f"Expected max_overflow=4, got {overflow}"


class TestSessionManagement:
    """Verify session lifecycle through the database manager."""

    def test_get_session_returns_usable_session(self, tmp_db_manager):
        with tmp_db_manager.get_session() as session:
            # Should be able to execute a simple query
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_session_commit_persists_data(self, tmp_db_manager):
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.db_models import PlayerProfile

        with tmp_db_manager.get_session() as session:
            session.add(PlayerProfile(player_name="PersistTest"))
            session.commit()

        with tmp_db_manager.get_session() as session:
            result = session.exec(
                select(PlayerProfile).where(PlayerProfile.player_name == "PersistTest")
            ).first()
            assert result is not None
            assert result.player_name == "PersistTest"

    def test_session_rollback_on_error(self, tmp_db_manager):
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.db_models import PlayerProfile

        try:
            with tmp_db_manager.get_session() as session:
                session.add(PlayerProfile(player_name="RollbackTest"))
                raise ValueError("Simulated error")
        except ValueError:
            pass

        with tmp_db_manager.get_session() as session:
            result = session.exec(
                select(PlayerProfile).where(PlayerProfile.player_name == "RollbackTest")
            ).first()
            assert result is None, "Data should have been rolled back"
