"""GAP-06 tests for tools/rescrape_placeholder_pros.py.

Exercises listing, URL construction, dry-run output, and the live-path
plumbing with a stubbed HLTVStatFetcher (no network).
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from Programma_CS2_RENAN.backend.knowledge.pro_demo_miner import _DEFAULT_STATS_SENTINEL
from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard
from tools import rescrape_placeholder_pros as mod


def _make_card(player_id: int, default: bool = True, **overrides) -> ProPlayerStatCard:
    if default:
        rating, kpr, dpr, adr, kast, impact, hs, maps = _DEFAULT_STATS_SENTINEL
    else:
        rating, kpr, dpr, adr, kast, impact, hs, maps = (
            1.30,
            0.78,
            0.62,
            85.0,
            0.74,
            1.20,
            0.50,
            500,
        )
    return ProPlayerStatCard(
        player_id=player_id,
        rating_2_0=overrides.get("rating_2_0", rating),
        kpr=overrides.get("kpr", kpr),
        dpr=overrides.get("dpr", dpr),
        adr=overrides.get("adr", adr),
        kast=overrides.get("kast", kast),
        impact=overrides.get("impact", impact),
        headshot_pct=overrides.get("headshot_pct", hs),
        maps_played=overrides.get("maps_played", maps),
    )


@pytest.fixture
def patched_hltv_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    class _FakeMgr:
        @contextmanager
        def get_session(self):
            with Session(engine) as s:
                yield s

    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.storage.database.get_hltv_db_manager",
        lambda: _FakeMgr(),
    )
    return engine


def _seed(engine, rows):
    """rows: list of (hltv_id, nickname, is_default)"""
    with Session(engine) as s:
        for hid, nick, is_default in rows:
            s.add(ProPlayer(hltv_id=hid, nickname=nick))
            s.add(_make_card(hid, default=is_default))
        s.commit()


def test_list_placeholders_returns_only_defaults(patched_hltv_db):
    _seed(
        patched_hltv_db,
        [
            (1, "alex", True),
            (2, "zywoo", False),
            (3, "siuhy", True),
        ],
    )
    placeholders = mod._list_placeholders()
    nicks = [n for _, n in placeholders]
    assert nicks == ["alex", "siuhy"]  # sorted, defaults only


def test_list_placeholders_empty_when_clean(patched_hltv_db):
    _seed(patched_hltv_db, [(1, "donk", False), (2, "zywoo", False)])
    assert mod._list_placeholders() == []


def test_build_url_lowercase_and_canonical():
    url = mod._build_url(11893, "ZywOo")
    assert url == "https://www.hltv.org/stats/players/11893/zywoo"


def test_dry_run_lists_and_does_not_call_fetcher(patched_hltv_db, capsys, monkeypatch):
    _seed(patched_hltv_db, [(7, "Alkaren", True), (8, "biguzera", True)])
    fetcher_class = MagicMock()
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher.HLTVStatFetcher",
        fetcher_class,
    )
    rc = mod.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Placeholder cards in HLTV DB: 2" in out
    assert "Alkaren" in out
    assert "[DRY-RUN]" in out
    fetcher_class.assert_not_called()  # no instantiation in dry-run


def test_apply_invokes_fetcher_per_player(patched_hltv_db, capsys, monkeypatch):
    _seed(patched_hltv_db, [(7, "Alkaren", True), (8, "biguzera", True)])

    fake = MagicMock()
    fake.preflight_check.return_value = True
    fake.fetch_and_save_player.return_value = True
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher.HLTVStatFetcher",
        lambda: fake,
    )
    # Stub _still_default to simulate cleared sentinel
    monkeypatch.setattr(mod, "_still_default", lambda hid: False)

    rc = mod.main(["--apply"])
    assert rc == 0
    assert fake.fetch_and_save_player.call_count == 2
    out = capsys.readouterr().out
    assert "ok=2" in out and "fail=0" in out


def test_apply_returns_nonzero_on_remaining_default(patched_hltv_db, monkeypatch, capsys):
    _seed(patched_hltv_db, [(9, "snow", True)])
    fake = MagicMock()
    fake.preflight_check.return_value = True
    fake.fetch_and_save_player.return_value = True
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher.HLTVStatFetcher",
        lambda: fake,
    )
    # Card is STILL default after the "successful" rescrape
    monkeypatch.setattr(mod, "_still_default", lambda hid: True)

    rc = mod.main(["--apply"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "still_default=1" in out
    assert "snow" in out


def test_limit_caps_iterations(patched_hltv_db, monkeypatch, capsys):
    _seed(
        patched_hltv_db,
        [(i, f"player{i}", True) for i in range(5)],
    )
    fake = MagicMock()
    fake.preflight_check.return_value = True
    fake.fetch_and_save_player.return_value = True
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher.HLTVStatFetcher",
        lambda: fake,
    )
    monkeypatch.setattr(mod, "_still_default", lambda hid: False)

    rc = mod.main(["--apply", "--limit", "2"])
    assert rc == 0
    assert fake.fetch_and_save_player.call_count == 2


def test_apply_aborts_on_preflight_fail(patched_hltv_db, monkeypatch, capsys):
    _seed(patched_hltv_db, [(9, "snow", True)])
    fake = MagicMock()
    fake.preflight_check.return_value = False
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher.HLTVStatFetcher",
        lambda: fake,
    )
    rc = mod.main(["--apply"])
    assert rc == 2
    out = capsys.readouterr().out
    assert "Preflight failed" in out
    fake.fetch_and_save_player.assert_not_called()


def test_apply_records_fetcher_failures(patched_hltv_db, monkeypatch, capsys):
    _seed(patched_hltv_db, [(9, "snow", True), (10, "susp", True)])
    fake = MagicMock()
    fake.preflight_check.return_value = True
    # snow succeeds, susp returns False
    fake.fetch_and_save_player.side_effect = [True, False]
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher.HLTVStatFetcher",
        lambda: fake,
    )
    monkeypatch.setattr(mod, "_still_default", lambda hid: False)

    rc = mod.main(["--apply"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "ok=1 fail=1" in out
    assert "susp" in out


def test_idempotent_when_no_placeholders(patched_hltv_db, capsys):
    rc = mod.main(["--apply"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "nothing to do" in out.lower()
