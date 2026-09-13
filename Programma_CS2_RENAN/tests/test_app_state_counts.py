"""Honest dashboard (WP1) — AppState reports personal and pro demo counts separately.

Before: one unfiltered ``count(distinct demo_name)`` over every row was
emitted as ``total_matches`` and rendered as "Sample count · N personal
demos analyzed" (Coach) and the Home Matches chip.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from Programma_CS2_RENAN.tests._memory_db import MemoryDB, add_match, seed_personal, seed_pro_only

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _base_payload(**overrides):
    data = {
        "service_active": True,
        "coach_status": "Idle",
        "parsing_progress": 0.0,
        "belief_confidence": 0.0,
        "total_matches": 0,
        "pro_matches": 0,
        "current_epoch": 0,
        "total_epochs": 0,
        "train_loss": 0.0,
        "val_loss": 0.0,
        "eta_seconds": 0.0,
        "notifications": [],
    }
    data.update(overrides)
    return data


def test_counts_are_split_by_identity_and_pro_flag():
    from Programma_CS2_RENAN.apps.qt_app.core.app_state import count_personal_and_pro_demos

    db = MemoryDB()
    seed_pro_only(db)  # 2 pro demos x 2 players = 4 rows
    seed_personal(db, "me", demos=3)
    with db.get_session() as s:
        add_match(s, "me", "pro-final-nuke.dem", is_pro=True, rating=1.6)  # pro row, same nickname
        add_match(s, "someone_else", "their_match.dem", is_pro=False)
        personal, pro = count_personal_and_pro_demos(s, "me")

    assert personal == 3
    assert pro == 3  # navi-vs-vitality, faze-vs-g2, pro-final-nuke — distinct demos, not rows


def test_unset_player_name_counts_no_personal_demos():
    from Programma_CS2_RENAN.apps.qt_app.core.app_state import count_personal_and_pro_demos

    db = MemoryDB()
    seed_personal(db, "me", demos=2)
    with db.get_session() as s:
        assert count_personal_and_pro_demos(s, "") == (0, 0)


def test_apply_emits_personal_as_total_and_pro_separately(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.app_state import AppState

    state = AppState()
    totals: list[int] = []
    pros: list[int] = []
    state.total_matches_changed.connect(totals.append)
    state.pro_matches_changed.connect(pros.append)

    state._apply(_base_payload(total_matches=3, pro_matches=120))
    assert totals == [3]
    assert pros == [120]

    state._apply(_base_payload(total_matches=3, pro_matches=121))
    assert totals == [3], "unchanged personal count must not re-emit"
    assert pros == [120, 121]
