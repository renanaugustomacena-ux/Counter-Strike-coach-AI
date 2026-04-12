"""AppState — singleton QObject that polls CoachState from DB every 10 seconds.

Emits typed signals consumed by any Qt screen (HomeScreen, etc.).
Read-only: the Qt app does NOT write to CoachState — that's session_engine's job.
"""

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_app_state")

_instance: "AppState | None" = None


def get_app_state() -> "AppState":
    """Return the global AppState singleton (created on first call)."""
    global _instance  # noqa: PLW0603
    if _instance is None:
        _instance = AppState()
    return _instance


class AppState(QObject):
    """Polls CoachState DB row (id=1) and emits change signals."""

    service_active_changed = Signal(bool)
    coach_status_changed = Signal(str)
    parsing_progress_changed = Signal(float)
    belief_confidence_changed = Signal(float)
    total_matches_changed = Signal(int)
    training_changed = Signal(dict)
    notification_received = Signal(str, str)  # (severity, message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prev: dict = {}
        self._timer: QTimer | None = None

    @property
    def cached_state(self) -> dict:
        """Public accessor for last-polled state snapshot (SA-25/26)."""
        return self._prev

    def start_polling(self):
        """Start the 10-second poll loop. Call once from app.py after show()."""
        if self._timer is not None:
            return
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(10_000)
        self._poll()  # immediate first read

    def stop_polling(self):
        """Stop polling (for cleanup)."""
        if self._timer is not None:
            self._timer.stop()

    # ── Internal ──

    def _poll(self):
        worker = Worker(self._bg_read)
        worker.signals.result.connect(self._apply)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    @staticmethod
    def _bg_read():
        """Background thread: read CoachState singleton row.

        Returns None if the DB is unavailable or CoachState row doesn't exist.
        """
        from datetime import datetime, timezone

        try:
            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import CoachState
        except Exception:
            return None

        try:
            with get_db_manager().get_session() as session:
                try:
                    state = session.get(CoachState, 1)
                except Exception as exc:
                    logger.debug("AppState: CoachState query failed: %s", exc)
                    return None
                if state is None:
                    return None

                delta = 9999.0
                if state.last_heartbeat is not None:
                    now = datetime.now(timezone.utc)
                    hb = state.last_heartbeat
                    if hb.tzinfo is None:
                        hb = hb.replace(tzinfo=timezone.utc)
                    delta = (now - hb).total_seconds()

                # Query unread notifications and mark them read
                from sqlalchemy import select

                from Programma_CS2_RENAN.backend.storage.db_models import ServiceNotification

                notifs = []
                try:
                    rows = session.exec(
                        select(ServiceNotification)
                        .where(ServiceNotification.is_read == False)  # noqa: E712
                        .order_by(ServiceNotification.created_at)
                        .limit(5)
                    ).all()
                    for row in rows:
                        notifs.append({"severity": row.severity, "message": row.message})
                        row.is_read = True
                    if rows:
                        session.commit()
                except Exception as exc:
                    logger.debug("Notification poll skipped: %s", exc)

                # Count actual analyzed demos (distinct demo files in PlayerMatchStats)
                from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

                try:
                    from sqlalchemy import func as sa_func

                    demo_count = (
                        session.exec(
                            select(sa_func.count(sa_func.distinct(PlayerMatchStats.demo_name)))
                        ).one()
                        or 0
                    )
                except Exception:
                    demo_count = int(state.total_matches_processed)

                return {
                    "service_active": delta < 300,
                    "coach_status": state.ingest_status or "Idle",
                    "parsing_progress": float(state.parsing_progress),
                    "belief_confidence": float(state.belief_confidence),
                    "total_matches": int(demo_count),
                    "current_epoch": int(state.current_epoch),
                    "total_epochs": int(state.total_epochs),
                    "train_loss": float(state.train_loss),
                    "val_loss": float(state.val_loss),
                    "eta_seconds": float(state.eta_seconds),
                    "notifications": notifs,
                }
        except Exception as exc:
            logger.debug("AppState: DB read failed: %s", exc)
            return None

    def _apply(self, data):
        if data is None:
            return

        prev = self._prev

        if data.get("service_active") != prev.get("service_active"):
            self.service_active_changed.emit(data["service_active"])

        if data.get("coach_status") != prev.get("coach_status"):
            self.coach_status_changed.emit(data["coach_status"])

        if data.get("parsing_progress") != prev.get("parsing_progress"):
            self.parsing_progress_changed.emit(data["parsing_progress"])

        if data.get("belief_confidence") != prev.get("belief_confidence"):
            self.belief_confidence_changed.emit(data["belief_confidence"])

        if data.get("total_matches") != prev.get("total_matches"):
            self.total_matches_changed.emit(data["total_matches"])

        # Training bundle — emit if any training field changed
        t_keys = ("current_epoch", "total_epochs", "train_loss", "val_loss", "eta_seconds")
        if any(data.get(k) != prev.get(k) for k in t_keys):
            self.training_changed.emit({k: data[k] for k in t_keys})

        # Emit any new notifications
        for n in data.get("notifications", []):
            self.notification_received.emit(n["severity"], n["message"])

        self._prev = data

    def _on_error(self, msg):
        logger.warning("AppState poll error: %s", msg)
