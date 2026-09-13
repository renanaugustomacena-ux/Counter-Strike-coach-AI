"""TrainingViewModel — the app's Train action (WP4b).

Training never runs in the GUI process: the view-model writes a request into
``CoachState`` (``StateManager.request_training``) and the Session Engine's
Teacher daemon picks it up within a few seconds.  Every outcome is reported
honestly: queued, service offline, a run already in progress, a request
already pending.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_training_vm")

MODEL_TYPE = "jepa_v2"
TRAINING_CAPTION = (
    "Trains the JEPA v2 encoder on your analyzed demos, in the background service. "
    "The coach's advice text does not use it until CORREZIONE Parte III steps 6-8 land."
)
# The Teacher heartbeats every few seconds; AppState calls the service
# "online" under 300 s as well (app_state._bg_read).
_SERVICE_ALIVE_SECONDS = 300.0

_MESSAGES = {
    "queued": ("home.train_queued", "Queued — the background service starts within a few seconds"),
    "offline": (
        "home.train_offline",
        "Service offline — start the background service first (Service chip on the Dashboard)",
    ),
    "busy": ("home.train_busy", "A training run is already in progress"),
    "pending": ("home.train_pending", "A training request is already waiting for the service"),
    "stop_sent": ("home.train_stop_sent", "Stop requested — the run parks a checkpoint and ends"),
    "error": ("home.train_error", "Could not reach the database: {error}"),
}


class TrainingViewModel(QObject):
    """Queue a jepa_v2 training run (or a stop) off the GUI thread."""

    message = Signal(str, str)  # (severity: info | success | warning | error, text)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False

    # ── Actions ──

    def request_training(self, steps: int) -> None:
        if self._busy:
            return
        self._busy = True
        worker = Worker(self._request, int(steps))
        worker.signals.result.connect(self._on_outcome)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def request_stop(self) -> None:
        if self._busy:
            return
        self._busy = True
        worker = Worker(self._stop)
        worker.signals.result.connect(self._on_outcome)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    # ── Worker thread (DB only, no widget access) ──

    @staticmethod
    def _service_alive(state) -> bool:
        heartbeat = getattr(state, "last_heartbeat", None)
        if heartbeat is None:
            return False
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - heartbeat).total_seconds() < _SERVICE_ALIVE_SECONDS

    @staticmethod
    def _request(steps: int) -> Tuple[str, str]:
        manager = get_state_manager()
        state = manager.get_state()
        if not TrainingViewModel._service_alive(state):
            return "warning", "offline"
        if str(getattr(state, "ml_status", "") or "").strip().lower() == "learning":
            return "warning", "busy"
        if getattr(state, "training_requested", False):
            return "warning", "pending"
        if not manager.request_training(MODEL_TYPE, steps):
            return "warning", "pending"
        logger.info("Training requested from the app: %s, %d steps", MODEL_TYPE, steps)
        return "success", "queued"

    @staticmethod
    def _stop() -> Tuple[str, str]:
        get_state_manager().request_training_stop()
        logger.info("Training stop requested from the app")
        return "info", "stop_sent"

    # ── GUI thread ──

    def _on_outcome(self, outcome) -> None:
        self._busy = False
        severity, key = outcome
        i18n_key, fallback = _MESSAGES[key]
        self.message.emit(severity, i18n.get_text(i18n_key, fallback))

    def _on_error(self, error) -> None:
        self._busy = False
        logger.error("Training request failed: %s", error)
        i18n_key, fallback = _MESSAGES["error"]
        self.message.emit("error", i18n.get_text(i18n_key, fallback).replace("{error}", str(error)))
