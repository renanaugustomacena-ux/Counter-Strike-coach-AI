"""In-memory stand-in for ``DatabaseManager`` used by the honest-dashboard tests.

Every SQLModel table is created on a private ``sqlite:///:memory:`` engine;
``get_session`` mirrors the production context-manager contract (commit on
exit, rollback on error) so view-models and ``AnalyticsEngine`` run unchanged.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine

from Programma_CS2_RENAN.backend.storage.db_models import CoachingInsight, PlayerMatchStats

_T0 = datetime(2026, 3, 1, 20, 0, tzinfo=timezone.utc)


class MemoryDB:
    def __init__(self):
        self.engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self, engine_key: str = "default"):
        with Session(self.engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


def add_match(
    session: Session,
    player: str,
    demo: str,
    *,
    is_pro: bool,
    rating: float | None = 1.0,
    days: int = 0,
    **fields,
) -> PlayerMatchStats:
    row = PlayerMatchStats(
        player_name=player,
        demo_name=demo,
        is_pro=is_pro,
        rating=rating,
        match_date=_T0 + timedelta(days=days),
        kd_ratio=fields.pop("kd_ratio", 1.1),
        avg_adr=fields.pop("avg_adr", 80.0),
        avg_kast=fields.pop("avg_kast", 0.7),
        **fields,
    )
    session.add(row)
    session.flush()
    return row


def add_insight(
    session: Session, player: str, demo: str, message: str = "Your aim is fine."
) -> None:
    session.add(
        CoachingInsight(
            player_name=player,
            demo_name=demo,
            title="t",
            severity="LOW",
            message=message,
            focus_area="aim",
        )
    )
    session.flush()


def seed_pro_only(db: MemoryDB) -> None:
    """Two pro demos, two pro players each, no personal rows at all."""
    with db.get_session() as s:
        for day, demo in enumerate(("navi-vs-vitality-mirage.dem", "faze-vs-g2-inferno.dem")):
            for player, rating in (("s1mple", 1.35), ("ZywOo", 1.41)):
                add_match(s, player, demo, is_pro=True, rating=rating, days=day)


def seed_personal(db: MemoryDB, player: str = "me", demos: int = 2) -> None:
    with db.get_session() as s:
        for i in range(demos):
            add_match(
                s,
                player,
                f"my_match_{i}_dust2.dem",
                is_pro=False,
                rating=0.95 + i / 10,
                days=10 + i,
            )
