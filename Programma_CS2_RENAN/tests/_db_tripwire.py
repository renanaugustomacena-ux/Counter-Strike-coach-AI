"""Real-database tripwire (D-50): row-count snapshots of ``database.db``.

``conftest.py`` snapshots the production database at session start and
compares at session end; any change fails the run unless it is an
explicit integration run (``CS2_INTEGRATION_TESTS=1``). Reads use
``mode=ro`` (not ``immutable``) so rows still sitting in the WAL are seen.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Tuple

WATCHED_TABLES = (
    "coachinginsight",
    "playermatchstats",
    "roundstats",
    "playerprofile",
    "ingestiontask",
)


def snapshot_counts(db_path) -> Dict[str, int]:
    """{table: row count} for every watched table that exists; {} when no DB."""
    path = Path(db_path)
    if not path.exists():
        return {}
    uri = f"file:{path.as_posix()}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error:
        return {}
    try:
        existing = {
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        return {
            table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in WATCHED_TABLES
            if table in existing
        }
    except sqlite3.Error:
        return {}
    finally:
        con.close()


def changed_tables(before: Dict[str, int], after: Dict[str, int]) -> Dict[str, Tuple[int, int]]:
    """{table: (before, after)} for every table whose count moved."""
    return {
        table: (before[table], after.get(table, before[table]))
        for table in before
        if after.get(table, before[table]) != before[table]
    }
