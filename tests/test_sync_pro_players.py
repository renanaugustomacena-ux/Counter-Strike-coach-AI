"""GAP-05 tests for tools/sync_pro_players.py.

Uses an in-memory SQLite engine patched into get_db_manager() so we exercise
the real `_count_stale` + `_apply_purge` logic without touching database.db.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, func, select

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from Programma_CS2_RENAN.backend.storage.db_models import (  # noqa: E402
    ProPlayer,
    ProPlayerStatCard,
    ProTeam,
)
from tools import sync_pro_players  # noqa: E402


@pytest.fixture
def patched_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    class _FakeMgr:
        @contextmanager
        def get_session(self):
            with Session(engine) as s:
                yield s

    mgr = _FakeMgr()
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.storage.database.get_db_manager",
        lambda: mgr,
    )
    return engine


def _seed_stale(engine):
    with Session(engine) as s:
        s.add(ProPlayer(hltv_id=11893, nickname="zywoo"))
        s.add(ProPlayer(hltv_id=7998, nickname="s1mple"))
        s.add(ProPlayerStatCard(player_id=11893, rating_2_0=1.30))
        s.add(ProPlayerStatCard(player_id=7998, rating_2_0=1.28))
        s.commit()


def test_dry_run_does_not_mutate(patched_db, capsys):
    _seed_stale(patched_db)
    rc = sync_pro_players.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[DRY-RUN]" in out
    assert "Would delete 2 proplayer" in out

    # Still 2 rows
    with Session(patched_db) as s:
        assert s.exec(select(func.count()).select_from(ProPlayer)).one() == 2
        assert s.exec(select(func.count()).select_from(ProPlayerStatCard)).one() == 2


def test_apply_purges_all_stale(patched_db, capsys, monkeypatch):
    _seed_stale(patched_db)
    # Skip the file backup — no real DB file
    rc = sync_pro_players.main(["--apply", "--skip-backup"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Purged" in out
    with Session(patched_db) as s:
        assert s.exec(select(func.count()).select_from(ProPlayer)).one() == 0
        assert s.exec(select(func.count()).select_from(ProPlayerStatCard)).one() == 0
        assert s.exec(select(func.count()).select_from(ProTeam)).one() == 0


def test_idempotent_when_already_empty(patched_db, capsys):
    rc = sync_pro_players.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "nothing to do" in out.lower()


def test_apply_idempotent_second_run(patched_db, capsys):
    _seed_stale(patched_db)
    sync_pro_players.main(["--apply", "--skip-backup"])
    capsys.readouterr()  # flush
    rc = sync_pro_players.main(["--apply", "--skip-backup"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "nothing to do" in out.lower()
