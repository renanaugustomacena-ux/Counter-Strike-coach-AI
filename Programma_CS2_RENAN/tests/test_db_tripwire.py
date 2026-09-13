"""Honest dashboard (WP1) — the real-DB tripwire helper used by conftest.

The session hook snapshots row counts of the production ``database.db``
at start and fails the run if any test changed them (unless the run is
explicitly an integration run). ``tests/test_services.py`` wrote 48
second-person insight rows into the author's DB this way.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from Programma_CS2_RENAN.tests._db_tripwire import WATCHED_TABLES, changed_tables, snapshot_counts


def _db_with(path: Path, insights: int) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE coachinginsight (id INTEGER PRIMARY KEY, player_name TEXT)")
    con.execute("CREATE TABLE playermatchstats (id INTEGER PRIMARY KEY, player_name TEXT)")
    for i in range(insights):
        con.execute("INSERT INTO coachinginsight (player_name) VALUES (?)", (f"p{i}",))
    con.commit()
    con.close()


def test_snapshot_counts_every_watched_table_that_exists(tmp_path):
    db = tmp_path / "database.db"
    _db_with(db, insights=3)

    counts = snapshot_counts(db)

    assert counts["coachinginsight"] == 3
    assert counts["playermatchstats"] == 0
    assert set(counts) <= set(WATCHED_TABLES)
    assert "playerprofile" not in counts, "missing tables are simply not watched"


def test_snapshot_is_empty_when_the_database_is_absent(tmp_path):
    assert snapshot_counts(tmp_path / "nope.db") == {}


def test_changed_tables_reports_only_the_deltas():
    before = {"coachinginsight": 3, "playermatchstats": 2}
    after = {"coachinginsight": 5, "playermatchstats": 2}
    assert changed_tables(before, after) == {"coachinginsight": (3, 5)}
    assert changed_tables(before, before) == {}


def test_snapshot_does_not_leave_wal_or_shm_files_behind(tmp_path):
    """SESSION_HANDOFF: plain ``mode=ro`` still creates -wal/-shm on NTFS."""
    db = tmp_path / "database.db"
    _db_with(db, insights=1)
    snapshot_counts(db)
    assert not (tmp_path / "database.db-wal").exists()
    assert not (tmp_path / "database.db-shm").exists()
