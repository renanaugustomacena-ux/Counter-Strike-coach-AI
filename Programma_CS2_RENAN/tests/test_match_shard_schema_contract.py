"""POV-TBL-01 regression guard: shard table-name contract.

The POV-RAP-FIX incident (Sprint A, 2026-04-26) silently dropped every RAP
training batch because the ORM model pointed at `match_tick_state` while the
ingestion writer stored rows in `matchtickstate`. These tests pin the
tablename contract so a model rename or SQLModel upgrade cannot reopen the
wound undetected.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from Programma_CS2_RENAN.backend.storage.match_data_manager import (
    MatchEventState,
    MatchMetadata,
    MatchTickState,
)


class TestShardTableNameContract:
    """Pin __tablename__ values for all three shard models."""

    def test_matchtickstate_tablename_pinned(self):
        assert MatchTickState.__tablename__ == "matchtickstate"

    def test_matcheventstate_tablename_pinned(self):
        assert MatchEventState.__tablename__ == "match_event_state"

    def test_matchmetadata_tablename_pinned(self):
        assert MatchMetadata.__tablename__ == "match_metadata"


class TestShardCreation:
    """Verify a fresh shard contains exactly the expected tables."""

    @pytest.fixture()
    def tmp_shard_engine(self, tmp_path: Path):
        db_path = tmp_path / "test_shard.db"
        engine = create_engine(f"sqlite:///{db_path}", echo=False)
        SQLModel.metadata.create_all(
            engine,
            tables=[
                MatchTickState.__table__,
                MatchEventState.__table__,
                MatchMetadata.__table__,
            ],
        )
        return engine, db_path

    def test_shard_contains_expected_tables(self, tmp_shard_engine):
        engine, db_path = tmp_shard_engine
        conn = sqlite3.connect(str(db_path))
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()

        assert "matchtickstate" in tables
        assert "match_event_state" in tables
        assert "match_metadata" in tables

    def test_orm_write_read_same_table(self, tmp_shard_engine):
        """Ingestion-path write and ORM read must hit the same table."""
        engine, db_path = tmp_shard_engine

        with Session(engine) as session:
            row = MatchTickState(
                tick=100,
                round_number=1,
                player_name="test_player",
                steamid=12345,
                team="CT",
            )
            session.add(row)
            session.commit()

        conn = sqlite3.connect(str(db_path))
        raw_count = conn.execute("SELECT COUNT(*) FROM matchtickstate").fetchone()[0]
        conn.close()

        assert raw_count == 1, (
            "ORM wrote to a different table than 'matchtickstate' — " "POV-RAP-FIX regression"
        )
