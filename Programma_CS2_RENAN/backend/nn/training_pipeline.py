"""In-app training cycle (WP4b): the developer's jepa_v2 run as one function.

``run_v2_training_cycle`` does exactly what ``run_full_training_cycle.py
--model-type jepa_v2`` does on the training box — assign dataset splits,
export episode shards, run ``jepa_v2.cli.run_jepa_v2`` — and then records the
run in the ``TrainedModel`` registry.  It always runs in a background process
(the Session Engine's Teacher daemon, or the console's ``MLController``),
never in the GUI process.

Caveat stated in the UI and the docs: the coach's advice text does not consume
the encoder until CORREZIONE Parte III steps 6-8 land (D-33).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional

from Programma_CS2_RENAN import __version__
from Programma_CS2_RENAN.observability.logger_setup import get_logger

log = get_logger("cs2analyzer.training_pipeline")

ProgressHook = Callable[[int, int, Dict[str, Any]], None]
StopHook = Callable[[], bool]

# CoachState telemetry is a DB write: report at most once a second (and at the end).
_PROGRESS_MIN_INTERVAL = 1.0
_ENCODER_VERSION = "jepa_v2_encoder"


@dataclass
class TrainingRunResult:
    status: str  # "success" | "stopped" | "failed" | "skipped" | "dry_run"
    reason: str = ""
    steps: int = 0
    checkpoint: str = ""
    trained_model_id: Optional[int] = None
    export: Any = None  # episode_export.ExportSummary
    metrics: Dict[str, Any] = field(default_factory=dict)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_v2_training_cycle(
    *,
    steps: Optional[int] = None,
    probe_every: Optional[int] = None,
    progress: Optional[ProgressHook] = None,
    stop: Optional[StopHook] = None,
    dry_run: bool = False,
    db=None,
    db_path: Optional[str] = None,
    data_dir=None,
    state=None,
    config_overrides: Optional[Dict[str, Any]] = None,
    full_export: bool = False,
    model_type: str = "jepa_v2",
) -> TrainingRunResult:
    """Assign splits → export shards → train jepa_v2 → register the run.

    ``db`` (a DatabaseManager-like with ``get_session``), ``db_path`` (the
    SQLite file the exporter reads), ``data_dir`` (shard root) and ``state``
    (a StateManager-like) default to the configured application ones.
    ``progress(step, total, info)`` and ``stop() -> bool`` are optional hooks.
    """
    if model_type != "jepa_v2":
        return TrainingRunResult("failed", reason=f"unknown model type {model_type!r}")

    from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager
    from Programma_CS2_RENAN.backend.storage.episode_export import export_episodes
    from Programma_CS2_RENAN.core import config

    if db is None:
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager

        db = get_db_manager()
    if state is None:
        from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

        state = get_state_manager()
    if db_path is None:
        db_path = config.DATABASE_URL.replace("sqlite:///", "")
    if data_dir is None:
        data_dir = config.jepa_v2_data_dir()
    data_dir = Path(data_dir)

    started = datetime.now(timezone.utc)
    log.info(
        "jepa_v2 training cycle: db=%s shards=%s steps=%s dry_run=%s",
        db_path,
        data_dir,
        steps,
        dry_run,
    )

    # 1. Chronological 70/15/15 splits (the exporter reads dataset_split).
    state.update_status("teacher", "Learning", "jepa_v2 · assigning dataset splits")
    manager = CoachTrainingManager()
    manager.db = db
    manager.assign_dataset_splits()

    # 2. Episode shards (incremental: unchanged demos are reused).
    state.update_status("teacher", "Learning", "jepa_v2 · exporting episode shards")
    summary = export_episodes(data_dir, db_path=db_path, profile="medium", full=full_export)
    n_train = int(summary.by_split.get("train", 0))
    n_val = int(summary.by_split.get("val", 0))
    if n_train == 0 or n_val == 0:
        reason = (
            "not enough analyzed demos with train and val splits "
            f"(train={n_train}, val={n_val}); analyze more demos first"
        )
        log.warning("jepa_v2 training skipped: %s", reason)
        state.update_status("teacher", "Idle", reason)
        return TrainingRunResult("skipped", reason=reason, export=summary)

    # 3. Train — progress throttled into CoachState, stop polled by the trainer.
    t0 = time.monotonic()
    last_report = {"t": 0.0}
    last_step = {"n": 0}
    stop_hit = {"v": False}

    def _progress(step: int, total: int, info: Dict[str, Any]) -> None:
        last_step["n"] = step
        if progress is not None:
            progress(step, total, info)
        now = time.monotonic()
        if step == total or now - last_report["t"] >= _PROGRESS_MIN_INTERVAL:
            last_report["t"] = now
            elapsed = now - t0
            eta = (elapsed / step) * (total - step) if step else 0.0
            state.update_training_progress(
                step,
                total,
                float(info.get("loss", 0.0)),
                float(info.get("L_next", 0.0)),
                eta,
            )

    def _stop() -> bool:
        if stop is not None and stop():
            stop_hit["v"] = True
            return True
        return False

    sink: Dict[str, Any] = {}
    args = SimpleNamespace(
        steps=steps,
        probe_every=probe_every,
        data_dir=str(data_dir),
        dry_run=dry_run,
        no_tensorboard=False,
        tb_logdir=None,
        seed=None,
        no_resume=False,
        progress_cb=_progress,
        stop_cb=_stop,
        config_overrides=config_overrides,
        result_sink=sink,
    )
    state.update_status(
        "teacher", "Learning", f"jepa_v2 · training on {n_train} train / {n_val} val demos"
    )
    ok = False
    error = ""
    try:
        from Programma_CS2_RENAN.backend.nn.jepa_v2.cli import run_jepa_v2

        ok = bool(run_jepa_v2(args))
    except Exception as exc:  # the run is reported, never propagated to a daemon loop
        log.exception("jepa_v2 training crashed")
        error = f"{type(exc).__name__}: {exc}"

    finished = datetime.now(timezone.utc)
    trained_steps = int(sink.get("steps", last_step["n"]) or last_step["n"])
    if dry_run:
        status = "dry_run"
    elif ok:
        status = "success"
    elif stop_hit["v"]:
        status = "stopped"
    else:
        status = "failed"

    metrics: Dict[str, Any] = {
        "best_auroc": sink.get("best_auroc"),
        "run_dir": sink.get("run_dir"),
        "export": {
            "shards": summary.shards,
            "episodes": summary.episodes,
            "ticks": summary.ticks,
            "reused": summary.reused,
        },
    }
    if error:
        metrics["error"] = error
    result = TrainingRunResult(
        status=status, reason=error, steps=trained_steps, export=summary, metrics=metrics
    )

    state.update_training_progress(0, 0, 0.0, 0.0, 0.0)
    if dry_run:
        state.update_status(
            "teacher", "Idle", f"jepa_v2 dry run · {trained_steps} steps, nothing written"
        )
        return result

    # 4. Register the run (the checkpoint may be absent after a failure).
    from Programma_CS2_RENAN.backend.nn import persistence
    from Programma_CS2_RENAN.backend.nn.training_registry import record_trained_model

    checkpoint = persistence.get_model_path(_ENCODER_VERSION)
    sha = _sha256(checkpoint) if checkpoint.exists() else ""
    try:
        from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

        schema_fp = CS2_V2.fingerprint()
    except Exception:  # schema module missing: recorded as unknown, never fatal
        schema_fp = ""
    with db.get_session() as session:
        row = record_trained_model(
            session,
            model_type="jepa_v2",
            version_name=_ENCODER_VERSION,
            relative_path=persistence._registry_key(checkpoint),
            status=status,
            sha256=sha,
            steps=trained_steps,
            demos_train=n_train,
            demos_val=n_val,
            export_fingerprint=summary.fingerprint,
            schema_fingerprint=schema_fp,
            device=str(sink.get("device", "")),
            app_version=__version__,
            started_at=started,
            finished_at=finished,
            metrics=metrics,
        )
        session.commit()
        result.trained_model_id = row.id
    result.checkpoint = str(checkpoint) if checkpoint.exists() else ""

    if status == "success":
        detail = f"Trained jepa_v2 · {trained_steps} steps · {n_train} demos"
        state.update_status("teacher", "Idle", detail)
    elif status == "stopped":
        state.update_status("teacher", "Idle", f"Training stopped at step {trained_steps}")
    else:
        state.update_status("teacher", "Error", f"Training failed: {error or 'aborted'}")
    log.info("jepa_v2 training cycle -> %s (%d steps)", status, trained_steps)
    return result
