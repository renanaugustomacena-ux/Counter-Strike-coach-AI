"""JEPA window fetcher contract (R4 CRIT fix, 2026-07-16).

The JEPA consumer builds (context, target) as positional slices of its
batch — rows 0..9 are the context, row 10 the next-step target. The old
flat ``_fetch_jepa_ticks`` feed returned randomly-subsampled unordered rows
spanning players and demos, so "next-step prediction" trained on unrelated
pairs. ``_fetch_jepa_windows`` must return contiguous single-player windows
while preserving B1 seed rotation and DET-01 determinism.
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

_DEMO = "vitality-vs-spirit-m2-inferno"
_WINDOW = 11


class _TestDB:
    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def get_session(self):
        with Session(self.engine, expire_on_commit=False) as session:
            yield session
            session.commit()


@pytest.fixture
def seeded_db():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(
        engine, tables=[PlayerMatchStats.__table__, PlayerTickState.__table__]
    )
    with Session(engine) as s:
        s.add(
            PlayerMatchStats(
                player_name="ZywOo",
                demo_name=f"{_DEMO}.dem_ZywOo",
                is_pro=True,
                dataset_split=DatasetSplit.TRAIN,
            )
        )
        # Two players, interleaved insertion, 80 ticks each.
        for tick in range(0, 80):
            for player in ("ZywOo", "donk"):
                s.add(
                    PlayerTickState(
                        demo_name=_DEMO,
                        player_name=player,
                        tick=tick,
                        pos_x=float(tick),
                        map_name="de_inferno",
                    )
                )
        s.commit()
    return _TestDB(engine)


def _fetch(seeded_db, seed=42, n_windows=6):
    fake_self = SimpleNamespace(
        db=seeded_db,
        _get_completed_demo_names=lambda: None,
    )
    # Bind the real anchor sampler onto the fake self so the whole chain runs.
    fake_self._fetch_jepa_ticks = lambda **kw: CoachTrainingManager._fetch_jepa_ticks(
        fake_self, **kw
    )
    return CoachTrainingManager._fetch_jepa_windows(
        fake_self,
        is_pro=True,
        split=DatasetSplit.TRAIN,
        seed=seed,
        n_windows=n_windows,
        window_len=_WINDOW,
    )


class TestJepaWindowFetcher:
    def test_windows_are_contiguous_single_player(self, seeded_db):
        windows = _fetch(seeded_db)
        assert windows, "no windows returned"
        for w in windows:
            assert len(w) == _WINDOW
            players = {t.player_name for t in w}
            assert len(players) == 1, f"window mixes players: {players}"
            ticks = [t.tick for t in w]
            assert ticks == sorted(ticks)
            assert len(set(ticks)) == _WINDOW, "duplicate ticks in window"

    def test_deterministic_for_same_seed(self, seeded_db):
        a = _fetch(seeded_db, seed=42)
        b = _fetch(seeded_db, seed=42)
        assert [[t.id for t in w] for w in a] == [[t.id for t in w] for w in b]

    def test_different_seeds_differ(self, seeded_db):
        a = _fetch(seeded_db, seed=42, n_windows=4)
        b = _fetch(seeded_db, seed=43, n_windows=4)
        assert [[t.id for t in w] for w in a] != [[t.id for t in w] for w in b]

    def test_end_of_stream_anchors_dropped(self, seeded_db):
        """Anchors within window_len of a player's last tick can't fill a
        window and must be dropped, never padded or mixed."""
        windows = _fetch(seeded_db, n_windows=40)
        for w in windows:
            assert len(w) == _WINDOW
            # Last window tick must exist within the player's 0..79 range.
            assert w[-1].tick <= 79
