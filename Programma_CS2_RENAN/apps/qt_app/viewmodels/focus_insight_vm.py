"""FocusInsightViewModel — surfaces "what to work on" insights to the dashboard.

Stub implementation for Phase 1. A future revision will compute the largest
negative delta vs pro-average from PerformanceViewModel data and rank
focus areas by gap × frequency. For now, returns a placeholder so the
dashboard composition can be validated end-to-end.

Public surface (signal contract — kept stable for the eventual swap):
    insight_changed(dict)
        Fires once data is available. Dict shape:
            {
                "area": str,        # e.g. "Utility usage"
                "body": str,        # 1–2 sentence insight
                "navigate_to": str, # screen name to open ("performance", "")
            }
        ``navigate_to`` may be empty when no follow-up screen is meaningful.

    has_data_changed(bool)
        Fires after load — True when there's enough analyzed data for an
        insight, False when the dashboard should render the empty branch.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_focus_insight_vm")


class FocusInsightViewModel(QObject):
    """Returns the top focus area for the dashboard hero pair."""

    insight_changed = Signal(dict)
    has_data_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._loading = False

    def load(self) -> None:
        if self._loading:
            return
        self._loading = True
        worker = Worker(self._bg_compute)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    @staticmethod
    def _bg_compute() -> dict:
        """Stub: detect whether the user has any analyzed matches.

        A future revision will read PerformanceViewModel-equivalent
        aggregates from the DB and compute the largest delta-vs-pro.
        For now we just check whether there is any user data at all.
        """
        try:
            from sqlmodel import select

            from Programma_CS2_RENAN.apps.qt_app.core.match_utils import (  # noqa: F401
                extract_map_name,
            )
            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
            from Programma_CS2_RENAN.core.config import get_setting
        except Exception as exc:
            logger.debug("FocusInsightVM imports failed: %s", exc)
            return {"has_data": False}

        try:
            player = get_setting("CS2_PLAYER_NAME", "")
            with get_db_manager().get_session() as session:
                query = select(PlayerMatchStats)
                if player:
                    query = query.where(
                        PlayerMatchStats.player_name == player
                    ).where(PlayerMatchStats.is_pro == False)  # noqa: E712
                else:
                    query = query.where(PlayerMatchStats.is_pro == False)  # noqa: E712
                query = query.limit(1)
                row = session.exec(query).first()
                return {"has_data": row is not None}
        except Exception as exc:
            logger.debug("FocusInsightVM query failed: %s", exc)
            return {"has_data": False}

    def _on_loaded(self, data: dict) -> None:
        self._loading = False
        has_data = bool(data.get("has_data"))
        self.has_data_changed.emit(has_data)
        if has_data:
            # Stub insight — the real computation will replace this body
            # with a PerformanceVM-driven delta-vs-pro highlight.
            self.insight_changed.emit(
                {
                    "area": "Utility usage",
                    "body": (
                        "Your utility damage trails the pro baseline on the "
                        "maps you play most. Open Performance to see the "
                        "per-map breakdown."
                    ),
                    "navigate_to": "performance",
                }
            )
        else:
            self.insight_changed.emit(
                {
                    "area": "",
                    "body": "",
                    "navigate_to": "",
                }
            )

    def _on_error(self, msg: str) -> None:
        self._loading = False
        logger.warning("FocusInsightVM load failed: %s", msg)
        self.has_data_changed.emit(False)
