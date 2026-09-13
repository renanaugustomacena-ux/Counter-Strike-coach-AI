"""Train-in-app round (WP4b) — the TrainedModel registry records every local
training run; the latest success per model type is the active model.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _record(session, registry, **overrides):
    fields = dict(
        model_type="jepa_v2",
        version_name="jepa_v2_encoder",
        relative_path="global/jepa_v2_encoder.pt",
        sha256="abc",
        steps=200,
        demos_train=7,
        demos_val=1,
        status="success",
        started_at=datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 9, 13, 10, 5, tzinfo=timezone.utc),
        metrics={"best_auroc": 0.61},
    )
    fields.update(overrides)
    return registry.record_trained_model(session, **fields)


def test_the_latest_success_is_active_and_demotes_the_previous_one():
    from Programma_CS2_RENAN.backend.nn import training_registry
    from Programma_CS2_RENAN.tests._memory_db import MemoryDB

    db = MemoryDB()
    with db.get_session() as session:
        first = _record(session, training_registry)
        second = _record(session, training_registry, steps=400)
        session.flush()
        assert first.is_active is False
        assert second.is_active is True
        active = training_registry.active_trained_model(session, "jepa_v2")
        assert active is not None and active.id == second.id
        assert active.metrics_json and '"best_auroc"' in active.metrics_json


def test_stopped_and_failed_runs_are_kept_but_never_active():
    from Programma_CS2_RENAN.backend.nn import training_registry
    from Programma_CS2_RENAN.tests._memory_db import MemoryDB

    db = MemoryDB()
    with db.get_session() as session:
        good = _record(session, training_registry)
        _record(session, training_registry, status="stopped", steps=37)
        _record(session, training_registry, status="failed", steps=0, sha256="")
        session.flush()
        active = training_registry.active_trained_model(session, "jepa_v2")
        assert active is not None and active.id == good.id
        assert training_registry.active_trained_model(session, "coach_v2") is None
        summary = training_registry.active_model_summary(session, "jepa_v2")
        assert summary["version_name"] == "jepa_v2_encoder"
        assert summary["steps"] == 200 and summary["demos_train"] == 7
        assert summary["finished_at"].startswith("2026-09-13")


def test_trained_model_is_a_monolith_table():
    from Programma_CS2_RENAN.backend.storage import database
    from Programma_CS2_RENAN.backend.storage.db_models import TrainedModel

    assert TrainedModel.__table__ in database._MONOLITH_TABLES


def test_coach_state_carries_the_training_request_channel():
    from Programma_CS2_RENAN.backend.storage.db_models import CoachState

    state = CoachState()
    assert state.training_requested is False
    assert state.training_request_model == ""
    assert state.training_request_steps == 0
    assert state.training_stop_requested is False


def test_migration_adds_the_registry_table_and_the_request_columns():
    versions = PROJECT_ROOT / "alembic" / "versions"
    matches = [
        p
        for p in versions.glob("*.py")
        if 'down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"' in p.read_text()
    ]
    assert len(matches) == 1, matches
    text = matches[0].read_text(encoding="utf-8")
    assert re.search(r'"trainedmodel"', text)
    for column in ("training_requested", "training_request_model", "training_request_steps"):
        assert column in text, column
    assert "training_stop_requested" in text
    assert "def downgrade" in text
