"""Honest dashboard (WP1) — the purge tool removes test-written rows, nothing else."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))


def _make_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE coachinginsight (id INTEGER PRIMARY KEY, player_name TEXT, demo_name TEXT,
            title TEXT, severity TEXT, message TEXT, focus_area TEXT, user_id TEXT, created_at TEXT);
        CREATE TABLE playermatchstats (id INTEGER PRIMARY KEY, player_name TEXT, demo_name TEXT, is_pro INTEGER);
        CREATE TABLE playerprofile (id INTEGER PRIMARY KEY, player_name TEXT);
        INSERT INTO coachinginsight (player_name, demo_name, title, severity, message, focus_area)
            VALUES ('__test_nonexistent_player__', '__test.dem', 't', 'LOW', 'Your performance...', 'x'),
                   ('__test_nonexistent_player__', '__test.dem', 't', 'LOW', 'Your performance...', 'x'),
                   ('__test_other__', 'demo.dem', 't', 'LOW', 'm', 'x'),
                   ('Knowledge_mc', 'real.dem', 't', 'LOW', 'real insight', 'x');
        INSERT INTO playermatchstats (player_name, demo_name, is_pro) VALUES
                   ('__test_player__', '__t.dem', 0), ('Knowledge_mc', 'real.dem', 0);
        INSERT INTO playerprofile (player_name) VALUES ('__test_profile__'), ('Knowledge_mc');
        """
    )
    con.commit()
    con.close()


def _count(path: Path, table: str, where: str = "1=1") -> int:
    con = sqlite3.connect(path)
    try:
        return con.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchone()[0]
    finally:
        con.close()


def test_dry_run_reports_but_deletes_nothing(tmp_path):
    import purge_test_pollution as tool

    db = tmp_path / "database.db"
    _make_db(db)

    report = tool.purge(db, apply=False)

    assert report == {"coachinginsight": 3, "playermatchstats": 1, "playerprofile": 1}
    assert _count(db, "coachinginsight") == 4
    assert _count(db, "playermatchstats") == 2


def test_apply_backs_up_first_then_deletes_only_test_rows(tmp_path):
    import purge_test_pollution as tool

    db = tmp_path / "database.db"
    _make_db(db)
    backups: list[Path] = []

    report = tool.purge(db, apply=True, backup=lambda p: backups.append(p) or tmp_path / "bk.db")

    assert backups == [db]
    assert report == {"coachinginsight": 3, "playermatchstats": 1, "playerprofile": 1}
    assert _count(db, "coachinginsight") == 1
    assert _count(db, "coachinginsight", "player_name = 'Knowledge_mc'") == 1
    assert _count(db, "playermatchstats") == 1
    assert _count(db, "playerprofile") == 1


def test_apply_refuses_to_proceed_when_the_backup_fails(tmp_path):
    import purge_test_pollution as tool

    db = tmp_path / "database.db"
    _make_db(db)

    def _boom(_path):
        raise RuntimeError("disk full")

    with pytest.raises(RuntimeError, match="disk full"):
        tool.purge(db, apply=True, backup=_boom)
    assert _count(db, "coachinginsight") == 4, "nothing may be deleted without a backup"
