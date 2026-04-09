"""PerformanceViewModel — QObject port of data_viewmodels.PerformanceViewModel."""

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_performance_vm")


class PerformanceViewModel(QObject):
    """Loads performance analytics in background."""

    data_changed = Signal(
        list, dict, dict, dict, bool
    )  # history, map_stats, sw, utility, is_pro_overview
    is_loading_changed = Signal(bool)
    error_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = False

    @property
    def is_loading(self):
        return self._is_loading

    def load_performance(self):
        if self._is_loading:
            return
        self._is_loading = True
        self.is_loading_changed.emit(True)
        self.error_changed.emit("")

        worker = Worker(self._bg_load)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _bg_load(self):
        player = get_setting("CS2_PLAYER_NAME", "")
        if not player:
            raise ValueError("Player name not set. Go to Profile or run the Setup Wizard.")

        try:
            from Programma_CS2_RENAN.backend.reporting.analytics import analytics
        except ImportError as exc:
            logger.warning("Analytics module unavailable: %s", exc)
            return ([], {}, {}, {}, False)

        # Check if user has personal matches — determines provenance labeling
        from sqlalchemy import func as sa_func
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

        with get_db_manager().get_session() as session:
            user_count = session.exec(
                select(sa_func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.player_name == player,
                    PlayerMatchStats.is_pro == False,  # noqa: E712
                )
            ).one()
        is_pro_overview = not (user_count and user_count > 0)

        history = analytics.get_rating_history(player, limit=50)
        map_stats = analytics.get_per_map_stats(player)
        sw = analytics.get_strength_weakness(player)
        utility = analytics.get_utility_breakdown(player)

        return (
            history or [],
            map_stats or {},
            sw or {},
            utility or {},
            is_pro_overview,
        )

    def _on_loaded(self, result):
        self._is_loading = False
        self.is_loading_changed.emit(False)
        if result:
            history, map_stats, sw, utility, is_pro_overview = result
            self.data_changed.emit(history, map_stats, sw, utility, is_pro_overview)

    def _on_error(self, msg):
        logger.error("performance_vm.load_failed: %s", msg)
        self._is_loading = False
        self.is_loading_changed.emit(False)
        self.error_changed.emit(str(msg))
