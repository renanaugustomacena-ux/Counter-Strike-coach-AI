"""MatchHistoryViewModel — QObject port of data_viewmodels.MatchHistoryViewModel."""

from threading import Event

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_match_history_vm")


class MatchHistoryViewModel(QObject):
    """Loads user match list in background. Signals auto-marshal to main thread."""

    matches_changed = Signal(list)
    is_loading_changed = Signal(bool)
    error_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = False
        self._cancel = Event()

    @property
    def is_loading(self):
        return self._is_loading

    def load_matches(self):
        if self._is_loading:
            return
        self._cancel.clear()
        self._is_loading = True
        self.is_loading_changed.emit(True)
        self.error_changed.emit("")

        worker = Worker(self._bg_load)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def cancel(self):
        self._cancel.set()

    def _bg_load(self):
        from sqlmodel import or_, select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

        player = get_setting("CS2_PLAYER_NAME", "")

        with get_db_manager().get_session() as session:
            # Show user matches first (filtered by player name), then all pro matches.
            # Exclude stub-quality rows (registered_only / partial / none) — they
            # carry only ~7 of 47 columns and would inflate the dashboard chip
            # without contributing meaningful per-row stats. Real rows are tagged
            # full_sql / full_sql_round_count_anomaly / complete / is_pro_overridden.
            # R4 MED: SQL three-valued logic — NULL NOT IN (...) is NULL, so
            # pre-migration rows with NULL data_quality vanished silently.
            # Untagged rows are legacy full rows: keep them.
            query = select(PlayerMatchStats).where(
                or_(
                    PlayerMatchStats.data_quality.is_(None),
                    PlayerMatchStats.data_quality.not_in(("registered_only", "partial", "none")),
                )
            )
            if player:
                query = query.where(
                    (PlayerMatchStats.player_name == player)
                    | (PlayerMatchStats.is_pro == True)  # noqa: E712
                )
            query = query.order_by(PlayerMatchStats.match_date.desc()).limit(50)
            results = session.exec(query).all()
            match_data = [
                {
                    "demo_name": m.demo_name,
                    "match_date": m.match_date,
                    "rating": m.rating,
                    "avg_kills": m.avg_kills,
                    "avg_deaths": m.avg_deaths,
                    "avg_adr": m.avg_adr,
                    "avg_kast": m.avg_kast,
                    "kd_ratio": m.kd_ratio,
                    "is_pro": m.is_pro,
                    "player_name": m.player_name,
                }
                for m in results
            ]

        if self._cancel.is_set():
            return []
        return match_data

    def _on_loaded(self, data):
        self._is_loading = False
        self.is_loading_changed.emit(False)
        if data is not None:
            self.matches_changed.emit(data)

    def _on_error(self, msg):
        logger.error("match_history_vm.load_failed: %s", msg)
        self._is_loading = False
        self.is_loading_changed.emit(False)
        self.error_changed.emit(str(msg))
