"""RAP window fetcher contract (R4 CRIT + WR-76 fixes, 2026-07-16).

``_fetch_rap_windows`` used to ``order_by(tick)`` alone, interleaving all
players' rows inside each window — the RAP consumers compute inter-row
position deltas and LTC timespans, so the training signal crossed players.
It also used the raw legacy-suffixed ``PlayerMatchStats.demo_name``
(``stem.dem_Player``) while ``PlayerTickState`` stores the bare stem,
yielding zero windows on legacy data (WR-76). These tests pin the fixed
contract: single-player windows, strictly ascending ticks, suffix strip.
"""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlmodel import Session, SQLModel, create_engine

from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager
from Programma_CS2_RENAN.backend.storage.db_models import (
    DatasetSplit,
    PlayerMatchStats,
    PlayerTickState,
)

_DEMO_STEM = "furia-vs-navi-m1-mirage"
_LEGACY_STATS_NAME = f"{_DEMO_STEM}.dem_s1mple"


class _TestDB:
    """Minimal stand-in for DatabaseManager exposing get_session()."""

    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def get_session(self):
        # expire_on_commit=False mirrors the real DatabaseManager sessions:
        # returned rows stay readable after the session closes.
        with Session(self.engine, expire_on_commit=False) as session:
            yield session
            session.commit()


def _tick_row(player: str, tick: int) -> PlayerTickState:
    return PlayerTickState(
        demo_name=_DEMO_STEM,
        player_name=player,
        tick=tick,
        pos_x=float(tick),
        pos_y=float(tick) * 0.5,
        map_name="de_mirage",
    )


@pytest.fixture
def seeded_db():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(
        engine, tables=[PlayerMatchStats.__table__, PlayerTickState.__table__]
    )
    with Session(engine) as s:
        # Legacy-suffixed stats row (WR-76 shape); tick rows carry the stem.
        s.add(
            PlayerMatchStats(
                player_name="s1mple",
                demo_name=_LEGACY_STATS_NAME,
                is_pro=True,
                dataset_split=DatasetSplit.TRAIN,
            )
        )
        # Interleaved rows exactly like the real monolith: for each tick,
        # one row per player (order_by(tick) alone would interleave them).
        for tick in range(0, 120):
            for player in ("s1mple", "ZywOo"):
                s.add(_tick_row(player, tick))
        # A third player with a run too short for one window.
        for tick in range(0, 30):
            s.add(_tick_row("short-run-guy", tick))
        s.commit()
    return _TestDB(engine)


def _fetch(seeded_db, completed, window_size=50):
    fake_self = SimpleNamespace(
        db=seeded_db,
        _get_completed_demo_names=lambda: completed,
    )
    return CoachTrainingManager._fetch_rap_windows(
        fake_self, is_pro=True, split=DatasetSplit.TRAIN, window_size=window_size
    )


class TestRapWindowFetcher:
    def test_wr76_legacy_suffix_stripped(self, seeded_db):
        """Suffixed stats name must still find the stem-named tick rows."""
        windows = _fetch(seeded_db, completed={_DEMO_STEM})
        assert windows, (
            "zero windows — the WR-76 '.dem_<player>' suffix was not "
            "stripped before matching PlayerTickState.demo_name"
        )

    def test_windows_are_single_player(self, seeded_db):
        """R4 CRIT: every window must belong to exactly one player."""
        windows = _fetch(seeded_db, completed=None)
        assert windows
        for w in windows:
            players = {t.player_name for t in w}
            assert len(players) == 1, f"interleaved window: {players}"

    def test_window_ticks_strictly_ascending(self, seeded_db):
        """Deltas/timespans are only meaningful on an ordered POV stream."""
        windows = _fetch(seeded_db, completed=None)
        for w in windows:
            ticks = [t.tick for t in w]
            assert ticks == sorted(ticks)
            assert len(set(ticks)) == len(ticks), "duplicate ticks in window"

    def test_expected_window_count(self, seeded_db):
        """120 ticks/player at window 50 → 2 windows each for 2 players."""
        windows = _fetch(seeded_db, completed=None, window_size=50)
        assert len(windows) == 4
        assert all(len(w) == 50 for w in windows)

    def test_short_player_runs_skipped(self, seeded_db):
        """Runs shorter than window_size produce no windows and no crash."""
        windows = _fetch(seeded_db, completed=None, window_size=50)
        assert all(w[0].player_name != "short-run-guy" for w in windows)
