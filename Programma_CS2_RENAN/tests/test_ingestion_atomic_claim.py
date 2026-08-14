"""F-0037 regression: exactly ONE runner wins each queued task.

Pre-fix: process_queued_tasks snapshot-SELECTed the queue and blindly
wrote status='processing' per task — every concurrent trigger surface
(home screen, settings, console ingest, batch_ingest, ingest_pro_demos)
took the same snapshot and double-parsed the same demos."""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


def _lazy_ri():
    from Programma_CS2_RENAN import run_ingestion

    return run_ingestion


class _DB:
    def __init__(self, engine):
        self._engine = engine

    @contextmanager
    def get_session(self, engine_key="default"):
        with Session(self._engine, expire_on_commit=False) as session:
            yield session


def _engine():
    from Programma_CS2_RENAN.backend.storage.db_models import CoachState, IngestionTask

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine, tables=[IngestionTask.__table__, CoachState.__table__])
    return engine


def _queue(engine, path="a.dem", is_pro=False):
    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask

    with Session(engine) as s:
        t = IngestionTask(
            demo_path=path,
            status="queued",
            is_pro=is_pro,
            updated_at=datetime.now(timezone.utc),
        )
        s.add(t)
        s.commit()
        return t.id


def test_claim_is_exclusive():
    ri = _lazy_ri()
    engine = _engine()
    task_id = _queue(engine)
    db = _DB(engine)
    assert ri._claim_task(db, task_id) is True, "first claim must win"
    assert ri._claim_task(db, task_id) is False, "second claim must lose"


def test_preclaimed_task_is_skipped_not_double_processed():
    ri = _lazy_ri()
    engine = _engine()
    id_mine = _queue(engine, "mine.dem")
    id_theirs = _queue(engine, "theirs.dem")
    db = _DB(engine)

    # Another runner claims one task between our snapshot and our loop.
    assert ri._claim_task(db, id_theirs)

    ingested = []
    with patch.object(
        ri, "_ingest_single_demo", side_effect=lambda *a: ingested.append(str(a[2])) or (True, "ok")
    ):
        with patch.object(ri, "_check_duplicate_demo", return_value=False):
            ri.process_queued_tasks(db, MagicMock(), is_pro=False, high_priority=False)

    assert len(ingested) == 1, f"exactly one task must be processed, got {ingested}"
    assert "mine" in ingested[0]

    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask

    with Session(engine) as s:
        mine = s.get(IngestionTask, id_mine)
        theirs = s.get(IngestionTask, id_theirs)
    assert mine.status == "completed"
    assert theirs.status == "processing", "the other runner's claim must be untouched"
