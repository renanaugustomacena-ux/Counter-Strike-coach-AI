"""Honest dashboard (WP1) — the Coach screen shows only the user's own insights.

Before: ``CoachViewModel._bg_load`` fell back to the last ten
``CoachingInsight`` rows of ANYONE when the user had none, and guessed
provenance with ``player_name != player``. The author's live DB held 48
such rows written by a unit test, all second-person template text.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from Programma_CS2_RENAN.tests._memory_db import MemoryDB, add_insight

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def vm_db(qapp, monkeypatch):
    import Programma_CS2_RENAN.backend.storage.database as database
    import Programma_CS2_RENAN.core.config as config
    from Programma_CS2_RENAN.apps.qt_app.viewmodels.coach_vm import CoachViewModel

    db = MemoryDB()
    monkeypatch.setattr(database, "get_db_manager", lambda: db)
    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: "me" if key == "CS2_PLAYER_NAME" else default,
    )
    return CoachViewModel(), db


def test_no_personal_insights_means_no_insights(vm_db):
    vm, db = vm_db
    with db.get_session() as s:
        add_insight(
            s,
            "__test_nonexistent_player__",
            "__test.dem",
            "Your performance was close to baseline.",
        )
        add_insight(s, "s1mple", "navi-mirage.dem", "Your aim is elite.")

    assert vm._bg_load() == []


def test_only_the_users_insights_are_returned(vm_db):
    vm, db = vm_db
    with db.get_session() as s:
        add_insight(s, "s1mple", "navi-mirage.dem", "Your aim is elite.")
        add_insight(s, "me", "my_match_0_dust2.dem", "Your crosshair placement drifts low.")

    rows = vm._bg_load()
    assert [r["player_name"] for r in rows] == ["me"]
    assert rows[0]["is_pro"] is False


def test_unset_player_name_returns_nothing(vm_db, monkeypatch):
    import Programma_CS2_RENAN.core.config as config

    vm, db = vm_db
    monkeypatch.setattr(
        config, "get_setting", lambda key, default=None: "" if key == "CS2_PLAYER_NAME" else default
    )
    with db.get_session() as s:
        add_insight(s, "s1mple", "navi-mirage.dem")
    assert vm._bg_load() == []
