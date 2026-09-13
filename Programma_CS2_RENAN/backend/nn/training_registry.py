"""Registry of models trained on this machine (WP4b).

One ``TrainedModel`` row per run; ``is_active`` marks the latest *successful*
run per model type.  ``persistence.load_nn``'s filename ladder is unchanged —
the registry is the record and the UI surface ("Active model: … · trained …").
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from Programma_CS2_RENAN.backend.storage.db_models import TrainedModel


def record_trained_model(
    session: Session,
    *,
    model_type: str,
    version_name: str,
    relative_path: str,
    status: str,
    sha256: str = "",
    steps: int = 0,
    demos_train: int = 0,
    demos_val: int = 0,
    export_fingerprint: str = "",
    schema_fingerprint: str = "",
    device: str = "",
    app_version: str = "",
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> TrainedModel:
    """Insert one run.  A ``success`` demotes the previous active row of the
    same model type; ``stopped`` / ``failed`` runs are kept as history only."""
    row = TrainedModel(
        model_type=model_type,
        version_name=version_name,
        relative_path=relative_path,
        sha256=sha256,
        steps=int(steps),
        demos_train=int(demos_train),
        demos_val=int(demos_val),
        export_fingerprint=export_fingerprint,
        schema_fingerprint=schema_fingerprint,
        device=device,
        app_version=app_version,
        status=status,
        started_at=started_at or datetime.now(timezone.utc),
        finished_at=finished_at,
        metrics_json=json.dumps(metrics or {}, sort_keys=True, default=str),
        is_active=False,
    )
    if status == "success":
        previous = session.exec(
            select(TrainedModel).where(
                TrainedModel.model_type == model_type,
                TrainedModel.is_active == True,  # noqa: E712
            )
        ).all()
        for old in previous:
            old.is_active = False
            session.add(old)
        row.is_active = True
    session.add(row)
    session.flush()
    return row


def active_trained_model(session: Session, model_type: str) -> Optional[TrainedModel]:
    """The latest successful run of ``model_type`` on this machine, if any."""
    return session.exec(
        select(TrainedModel)
        .where(
            TrainedModel.model_type == model_type,
            TrainedModel.is_active == True,  # noqa: E712
        )
        .order_by(TrainedModel.id.desc())  # type: ignore[union-attr]
    ).first()


def active_model_summary(session: Session, model_type: str) -> Optional[Dict[str, Any]]:
    """Plain-dict view of the active model for the GUI (signals carry dicts)."""
    row = active_trained_model(session, model_type)
    if row is None:
        return None
    return {
        "id": row.id,
        "model_type": row.model_type,
        "version_name": row.version_name,
        "relative_path": row.relative_path,
        "steps": int(row.steps),
        "demos_train": int(row.demos_train),
        "demos_val": int(row.demos_val),
        "finished_at": row.finished_at.isoformat() if row.finished_at else "",
        "sha256": (row.sha256 or "")[:12],
        "app_version": row.app_version,
    }
