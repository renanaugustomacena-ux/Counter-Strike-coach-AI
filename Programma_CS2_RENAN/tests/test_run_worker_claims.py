"""F-0015 regression: run_worker's stale threshold follows the P4-B SSOT
setting, and a claimed-but-skipped pro task is RELEASED back to queued.

Pre-fix: a hardcoded 5-minute copy of the threshold P4-B raised to 30
minutes re-queued demos mid-parse (duplicate processing), and the skip
branch left its freshly claimed task stuck in 'processing'."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine, select

from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask

# NB: run_worker is imported INSIDE tests — the entry script self-inserts
# Programma_CS2_RENAN into sys.path (S5), which at collection time makes
# `import tools` resolve the ptools package and breaks root-tests imports.


def _run_worker():
    from Programma_CS2_RENAN import run_worker

    return run_worker


class _DB:
    def __init__(self, engine):
        self._engine = engine

    @contextmanager
    def get_session(self, engine_key="default"):
        with Session(self._engine, expire_on_commit=False) as session:
            yield session


def _engine():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[IngestionTask.__table__])
    return engine


def _add_task(engine, status="processing", minutes_old=0, is_pro=True):
    with Session(engine) as s:
        t = IngestionTask(
            demo_path="x.dem",
            status=status,
            is_pro=is_pro,
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_old),
        )
        s.add(t)
        s.commit()
        return t.id


def test_recovery_threshold_uses_p4b_setting(monkeypatch):
    """A 10-minute-old processing task must NOT be recovered (default 30 min)."""
    engine = _engine()
    _add_task(engine, minutes_old=10)
    monkeypatch.setattr(
        "Programma_CS2_RENAN.core.config.get_setting",
        lambda key, default=None: default,
    )
    _run_worker()._recover_stale_tasks(_DB(engine))
    with Session(engine) as s:
        assert (
            s.exec(select(IngestionTask)).first().status == "processing"
        ), "10-min-old task recovered — the 5-minute copy is back"


def test_recovery_fires_past_the_threshold(monkeypatch):
    engine = _engine()
    _add_task(engine, minutes_old=45)
    monkeypatch.setattr(
        "Programma_CS2_RENAN.core.config.get_setting",
        lambda key, default=None: default,
    )
    _run_worker()._recover_stale_tasks(_DB(engine))
    with Session(engine) as s:
        assert s.exec(select(IngestionTask)).first().status == "queued"


def test_release_claim_requeues_processing_task():
    engine = _engine()
    task_id = _add_task(engine, status="processing")
    _run_worker()._release_claim(_DB(engine), task_id)
    with Session(engine) as s:
        assert s.get(IngestionTask, task_id).status == "queued"
