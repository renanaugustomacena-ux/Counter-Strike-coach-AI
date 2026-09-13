"""Honest dashboard (WP1) — Performance shows the user's data or an honest empty state.

Before: with zero personal rows the screen rendered a cross-player pro
average as a hero strip with green/red judgement and captioned it
"N personal demos analyzed" (N = pro rows). Now: personal sections need
personal rows; pro data appears only in an explicitly labelled
third-person "Pro reference" block.
"""

from __future__ import annotations

import os
import re

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel

from Programma_CS2_RENAN.tests._memory_db import MemoryDB, seed_personal, seed_pro_only

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MACENA_UI_ANIMATIONS", "0")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _flush(qapp):
    for _ in range(4):
        qapp.processEvents()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


# ── ViewModel ──


@pytest.fixture
def vm_db(qapp, monkeypatch):
    import Programma_CS2_RENAN.apps.qt_app.viewmodels.performance_vm as vm_module
    import Programma_CS2_RENAN.backend.reporting.analytics as analytics_module
    import Programma_CS2_RENAN.backend.storage.database as database

    db = MemoryDB()
    monkeypatch.setattr(database, "get_db_manager", lambda: db)
    monkeypatch.setattr(analytics_module.analytics, "db", db)
    monkeypatch.setattr(
        vm_module,
        "get_setting",
        lambda key, default=None: "me" if key == "CS2_PLAYER_NAME" else default,
    )
    return vm_module.PerformanceViewModel(), db


def test_vm_pro_only_database_yields_an_overview_with_no_personal_numbers(vm_db):
    vm, db = vm_db
    seed_pro_only(db)

    history, map_stats, sw, utility, is_pro_overview, context, meta = vm._bg_load()

    assert is_pro_overview is True
    assert sw == {} and utility == {} and context == {}
    assert meta == {"personal_demos": 0, "pro_matches": 2, "pro_players": 2}
    assert len(history) == 4 and all(h["rating"] >= 1.35 for h in history)
    assert set(map_stats) == {"de_mirage", "de_inferno"}


def test_vm_personal_rows_yield_the_users_own_analytics(vm_db):
    vm, db = vm_db
    seed_pro_only(db)
    seed_personal(db, "me", demos=2)

    history, map_stats, _sw, _utility, is_pro_overview, _context, meta = vm._bg_load()

    assert is_pro_overview is False
    assert [h["demo_name"] for h in history] == ["my_match_0_dust2.dem", "my_match_1_dust2.dem"]
    assert set(map_stats) == {"de_dust2"}
    assert meta["personal_demos"] == 2


# ── Screen ──


def _texts(widget) -> list[str]:
    return [lbl.text() for lbl in widget.findChildren(QLabel) if lbl.isVisibleTo(widget)]


def _pro_history():
    return [
        {
            "rating": 1.35,
            "match_date": None,
            "demo_name": "navi-vs-vitality-mirage.dem",
            "kd_ratio": 1.3,
            "avg_adr": 88.0,
            "avg_kast": 0.76,
        },
        {
            "rating": 1.41,
            "match_date": None,
            "demo_name": "navi-vs-vitality-mirage.dem",
            "kd_ratio": 1.4,
            "avg_adr": 91.0,
            "avg_kast": 0.78,
        },
        {
            "rating": 1.35,
            "match_date": None,
            "demo_name": "faze-vs-g2-inferno.dem",
            "kd_ratio": 1.3,
            "avg_adr": 88.0,
            "avg_kast": 0.76,
        },
        {
            "rating": 1.41,
            "match_date": None,
            "demo_name": "faze-vs-g2-inferno.dem",
            "kd_ratio": 1.4,
            "avg_adr": 91.0,
            "avg_kast": 0.78,
        },
    ]


@pytest.fixture
def screen(qapp):
    from Programma_CS2_RENAN.apps.qt_app.screens.performance_screen import PerformanceScreen

    widget = PerformanceScreen()
    widget.resize(1280, 900)
    widget.show()
    _flush(qapp)
    yield widget
    widget.close()
    widget.deleteLater()
    _flush(qapp)


def test_screen_pro_overview_has_no_hero_strip_and_no_personal_caption(qapp, screen):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.hero_stats_strip import HeroStatsStrip

    screen._on_data(
        _pro_history(),
        {"de_mirage": {"rating": 1.38, "adr": 89.5, "kd": 1.35, "matches": 2}},
        {},
        {},
        True,
        {"personal_demos": 0, "pro_matches": 2, "pro_players": 2},
    )
    _flush(qapp)

    from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState

    assert (
        screen.findChildren(HeroStatsStrip) == []
    ), "pro averages must never render as the user's hero stats"
    assert screen._count_caption.text() == ""
    honest = [
        w
        for w in screen.findChildren(EmptyState)
        if w.isVisibleTo(screen) and "No personal demos" in w._title_label.text()
    ]
    assert len(honest) == 1, "the honest empty state must be on screen alongside the reference"
    texts = " | ".join(_texts(screen))
    # The old caption claimed "N personal demos analyzed" with N = pro rows;
    # the honest copy ("No personal demos analyzed yet") is fine.
    assert not re.search(r"\d+ personal demos analyzed", texts), texts
    assert "Pro reference" in texts
    assert "2 matches" in texts and "2 players" in texts


def test_screen_personal_data_renders_hero_and_honest_count(qapp, screen):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.hero_stats_strip import HeroStatsStrip

    history = [
        {
            "rating": 0.95,
            "match_date": None,
            "demo_name": "my_match_0_dust2.dem",
            "kd_ratio": 1.0,
            "avg_adr": 70.0,
            "avg_kast": 0.66,
        },
        {
            "rating": 1.05,
            "match_date": None,
            "demo_name": "my_match_1_dust2.dem",
            "kd_ratio": 1.1,
            "avg_adr": 75.0,
            "avg_kast": 0.7,
        },
    ]
    screen._on_data(
        history,
        {"de_dust2": {"rating": 1.0, "adr": 72.5, "kd": 1.05, "matches": 2}},
        {"strengths": [("ADR", 0.8)], "weaknesses": []},
        {},
        False,
        {"personal_demos": 2, "pro_matches": 2, "pro_players": 2},
    )
    _flush(qapp)

    from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState

    assert len(screen.findChildren(HeroStatsStrip)) == 1
    assert screen._count_caption.text().startswith("2 ")
    assert not screen._empty_state.isVisibleTo(screen)
    assert not [w for w in screen.findChildren(EmptyState) if w.isVisibleTo(screen)]
    assert "Pro reference" not in " | ".join(_texts(screen))


def test_map_tile_shows_a_dash_for_a_missing_rating(qapp):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.map_tile import MapTile

    tile = MapTile()
    tile.set_data("Ancient", None, 0.0, 0.0, 1)
    assert tile.rating_text() == "—"
    tile.set_data("Ancient", 1.23, 80.0, 1.1, 3)
    assert tile.rating_text().startswith("1.23")
