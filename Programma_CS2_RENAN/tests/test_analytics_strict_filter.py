"""Honest dashboard (WP1) — AnalyticsEngine never substitutes pro rows for the user.

Before: ``_player_filter`` returned ``(True,)`` (no WHERE clause) when the
user had zero personal rows, so every Performance number became an average
over all players of all pro matches and was then labelled "personal".
Doctrine: absent beats fabricated.
"""

from __future__ import annotations

import pytest

from Programma_CS2_RENAN.backend.reporting.analytics import AnalyticsEngine
from Programma_CS2_RENAN.tests._memory_db import MemoryDB, add_match, seed_personal, seed_pro_only


@pytest.fixture
def engine():
    db = MemoryDB()
    eng = AnalyticsEngine.__new__(AnalyticsEngine)
    eng.db = db
    return eng, db


def test_personal_queries_are_empty_when_only_pro_rows_exist(engine):
    eng, db = engine
    seed_pro_only(db)

    assert eng.get_rating_history("me") == []
    assert eng.get_per_map_stats("me") == {}
    assert eng.get_strength_weakness("me") == {"strengths": [], "weaknesses": []}
    assert eng.get_utility_breakdown("me") == {}
    assert eng.get_hltv2_breakdown("me") == {}


def test_personal_queries_see_only_the_users_own_rows(engine):
    eng, db = engine
    seed_pro_only(db)
    seed_personal(db, "me", demos=2)

    history = eng.get_rating_history("me")
    assert [h["demo_name"] for h in history] == ["my_match_0_dust2.dem", "my_match_1_dust2.dem"]
    assert all(0.9 < h["rating"] < 1.1 for h in history), "pro ratings (1.35/1.41) must not leak"
    maps = eng.get_per_map_stats("me")
    assert set(maps) == {"de_dust2"}
    assert maps["de_dust2"]["matches"] == 2


def test_pro_rows_of_the_same_nickname_are_excluded(engine):
    """A pro row tagged with the user's nickname is still not the user's data."""
    eng, db = engine
    with db.get_session() as s:
        add_match(s, "me", "pro-final-nuke.dem", is_pro=True, rating=1.6)
    assert eng.get_rating_history("me") == []


def test_per_map_stats_never_fabricate_a_neutral_rating(engine):
    eng, db = engine
    with db.get_session() as s:
        add_match(s, "me", "my_ancient.dem", is_pro=False, rating=None, kd_ratio=None)
    maps = eng.get_per_map_stats("me")
    assert maps["de_ancient"]["rating"] is None
    assert maps["de_ancient"]["kd"] is None
    assert maps["de_ancient"]["matches"] == 1


def test_pro_cohort_queries_are_explicit_and_pro_only(engine):
    eng, db = engine
    seed_pro_only(db)
    seed_personal(db, "me", demos=1)

    history = eng.get_pro_cohort_history(limit=50)
    assert len(history) == 4
    assert all(
        h["rating"] >= 1.35 for h in history
    ), "the personal 0.95 row must not be in the cohort"
    maps = eng.get_pro_cohort_map_stats()
    assert set(maps) == {"de_mirage", "de_inferno"}
    assert eng.get_pro_cohort_summary() == {"matches": 2, "players": 2}


def test_pro_cohort_summary_is_zero_on_an_empty_database(engine):
    eng, _db = engine
    assert eng.get_pro_cohort_summary() == {"matches": 0, "players": 0}
    assert eng.get_pro_cohort_history() == []
    assert eng.get_pro_cohort_map_stats() == {}
