"""Meta-drift tick attribution contract (R4 HIGH fixes, 2026-07-16).

``calculate_spatial_drift`` used to JOIN PlayerTickState.match_id against
PlayerMatchStats.id — unrelated ID spaces — and never filtered by map, so
per-map drift was computed from random cross-map ticks. The fixed version
attributes ticks via demo_name (WR-76 suffix stripped) and filters on
PlayerTickState.map_name.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

import Programma_CS2_RENAN.backend.processing.baselines.meta_drift as md
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, PlayerTickState

_NOW = datetime.now(timezone.utc)


class _TestDB:
    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def get_session(self):
        with Session(self.engine, expire_on_commit=False) as session:
            yield session
            session.commit()


def _tick(demo, tick, x, y, map_name):
    return PlayerTickState(
        demo_name=demo,
        player_name="s1mple",
        tick=tick,
        pos_x=x,
        pos_y=y,
        map_name=map_name,
    )


@pytest.fixture
def seeded_db(monkeypatch):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(
        engine, tables=[PlayerMatchStats.__table__, PlayerTickState.__table__]
    )
    with Session(engine) as s:
        # Legacy-suffixed stats rows: one historical, one recent (WR-76 shape).
        s.add(
            PlayerMatchStats(
                player_name="s1mple",
                demo_name="old-demo.dem_s1mple",
                is_pro=True,
                processed_at=_NOW - timedelta(days=60),
            )
        )
        s.add(
            PlayerMatchStats(
                player_name="ZywOo",
                demo_name="new-demo.dem_ZywOo",
                is_pro=True,
                processed_at=_NOW,
            )
        )
        # de_mirage: centroids far apart between eras → real drift.
        for i in range(5):
            s.add(_tick("old-demo", i * 128, -2000.0, 800.0, "de_mirage"))
            s.add(_tick("new-demo", i * 128, -500.0, -1200.0, "de_mirage"))
        # de_nuke: identical centroids between eras → zero drift. If the map
        # filter were missing, these rows would contaminate de_mirage's drift.
        for i in range(5):
            s.add(_tick("old-demo", i * 128, 100.0, 100.0, "de_nuke"))
            s.add(_tick("new-demo", i * 128, 100.0, 100.0, "de_nuke"))
        s.commit()

    db = _TestDB(engine)
    monkeypatch.setattr(md, "get_db_manager", lambda: db)
    return db


class TestSpatialDriftAttribution:
    def test_drift_detected_on_shifted_map(self, seeded_db):
        drift = md.MetaDriftEngine.calculate_spatial_drift("de_mirage")
        assert drift > 0.0, "eras with far-apart centroids must show drift"

    def test_map_filter_isolates_maps(self, seeded_db):
        """de_nuke centroids are identical — drift must be exactly 0 there."""
        drift = md.MetaDriftEngine.calculate_spatial_drift("de_nuke")
        assert drift == pytest.approx(0.0)

    def test_unknown_map_returns_zero(self, seeded_db):
        assert md.MetaDriftEngine.calculate_spatial_drift("de_train") == 0.0

    def test_zero_when_single_era(self, monkeypatch):
        """Only recent demos → nothing to compare against → 0.0."""
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(
            engine, tables=[PlayerMatchStats.__table__, PlayerTickState.__table__]
        )
        with Session(engine) as s:
            s.add(
                PlayerMatchStats(
                    player_name="donk",
                    demo_name="solo-demo.dem_donk",
                    is_pro=True,
                    processed_at=_NOW,
                )
            )
            s.add(_tick("solo-demo", 0, 1.0, 1.0, "de_mirage"))
            s.commit()
        db = _TestDB(engine)
        monkeypatch.setattr(md, "get_db_manager", lambda: db)
        assert md.MetaDriftEngine.calculate_spatial_drift("de_mirage") == 0.0
