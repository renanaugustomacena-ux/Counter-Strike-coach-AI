"""Honest dashboard (WP1) — Match Detail never presents a random pro row as the user.

Before: when the configured player was not in the demo, the VM took an
arbitrary ``.first()`` row and then asked analytics for that pro's
"HLTV 2.0" aggregate through the broken all-rows filter.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from Programma_CS2_RENAN.tests._memory_db import MemoryDB, add_insight, add_match

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def vm_db(qapp, monkeypatch):
    import Programma_CS2_RENAN.apps.qt_app.viewmodels.match_detail_vm as vm_module
    import Programma_CS2_RENAN.backend.storage.database as database

    db = MemoryDB()
    monkeypatch.setattr(database, "get_db_manager", lambda: db)
    monkeypatch.setattr(
        vm_module,
        "get_setting",
        lambda key, default=None: "me" if key == "CS2_PLAYER_NAME" else default,
    )
    return vm_module.MatchDetailViewModel(), db


def test_pro_demo_is_labelled_a_pro_view_with_a_deterministic_player(vm_db):
    vm, db = vm_db
    with db.get_session() as s:
        add_match(s, "ZywOo", "navi-vs-vitality-mirage.dem", is_pro=True, rating=1.41)
        add_match(s, "s1mple", "navi-vs-vitality-mirage.dem", is_pro=True, rating=1.35)
        add_insight(s, "s1mple", "navi-vs-vitality-mirage.dem", "s1mple insight")
        add_insight(s, "ZywOo", "navi-vs-vitality-mirage.dem", "ZywOo insight")

    stats, rounds, insights, breakdown = vm._bg_load("navi-vs-vitality-mirage.dem")

    assert stats["is_pro_view"] is True
    assert stats["player_name"] == "s1mple", "alphabetical, never an arbitrary .first()"
    assert stats["players"] == ["ZywOo", "s1mple"] or stats["players"] == ["s1mple", "ZywOo"]
    assert [i["message"] for i in insights] == ["s1mple insight"]
    assert breakdown == {}, "no cross-match aggregate for a pro player"


def test_own_demo_is_the_users_view(vm_db):
    vm, db = vm_db
    with db.get_session() as s:
        add_match(s, "me", "my_match_0_dust2.dem", is_pro=False, rating=0.98)
        add_match(s, "teammate", "my_match_0_dust2.dem", is_pro=False, rating=1.2)
        add_insight(s, "me", "my_match_0_dust2.dem", "Your crosshair drifts low.")
        add_insight(s, "teammate", "my_match_0_dust2.dem", "teammate insight")

    stats, _rounds, insights, _breakdown = vm._bg_load("my_match_0_dust2.dem")

    assert stats["is_pro_view"] is False
    assert stats["player_name"] == "me"
    assert stats["rating"] == 0.98
    assert [i["message"] for i in insights] == ["Your crosshair drifts low."]


def test_screen_title_says_whose_match_a_pro_view_is(qapp):
    from Programma_CS2_RENAN.apps.qt_app.screens.match_detail_screen import MatchDetailScreen

    screen = MatchDetailScreen()
    try:
        stats = {
            "demo_name": "navi-vs-vitality-mirage.dem",
            "player_name": "s1mple",
            "is_pro_view": True,
            "players": ["s1mple", "ZywOo"],
            "rating": 1.35,
        }
        screen._on_data(stats, [], [], {})
        title = screen._title_label.text()
        assert "Pro demo" in title and "s1mple" in title

        stats_own = dict(stats, player_name="me", is_pro_view=False)
        screen._on_data(stats_own, [], [], {})
        assert "Pro demo" not in screen._title_label.text()
    finally:
        screen.deleteLater()


def test_unknown_demo_returns_an_empty_payload(vm_db):
    vm, _db = vm_db
    stats, rounds, insights, breakdown = vm._bg_load("nothing_here.dem")
    assert stats == {} and rounds == [] and insights == [] and breakdown == {}
