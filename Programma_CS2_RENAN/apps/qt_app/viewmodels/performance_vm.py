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
    # Cluster F — context layer: percentile rank of the user's averages
    # vs the pro cohort. Dict keys: rating, kd, adr, kast — each a float
    # in [0.0, 1.0] (0.0 = below all pros, 1.0 = above all pros). Empty
    # dict if user has no matches yet (pro_overview mode) or pro cohort
    # empty. Emitted alongside data_changed so the screen can render a
    # context strip under the hero stats without breaking existing
    # consumers of data_changed's 5-tuple shape.
    context_changed = Signal(dict)
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
            return ([], {}, {}, {}, False, {})

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

        # Compute percentile-vs-pro context (Cluster F). Cheap aggregation
        # via SQL — averages over the pro cohort's complete/full_sql rows
        # then ranks the user's average within the pro distribution.
        context = {}
        if not is_pro_overview and history:
            try:
                context = self._compute_pro_percentiles(history)
            except Exception as exc:  # noqa: BLE001 — surface as empty context
                logger.warning("performance_vm.percentile_compute_failed: %s", exc)
                context = {}

        return (
            history or [],
            map_stats or {},
            sw or {},
            utility or {},
            is_pro_overview,
            context,
        )

    @staticmethod
    def _compute_pro_percentiles(history: list) -> dict:
        """Rank the user's average rating/K-D/ADR/KAST inside the pro cohort.

        Returns dict with float values in [0.0, 1.0] representing the
        share of pros the user beats on each metric. Higher = better
        (lower-is-better metrics like deaths-per-round are not part of
        the hero strip so we don't need to invert anything here).
        """
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

        # User averages from the history we already loaded (avoids a
        # second pass through the user's matches).
        ratings = [float(h.get("rating") or 0) for h in history if h.get("rating")]
        kds = [float(h.get("kd_ratio") or 0) for h in history if h.get("kd_ratio")]
        adrs = [float(h.get("avg_adr") or 0) for h in history if h.get("avg_adr")]
        kasts = [float(h.get("avg_kast") or 0) for h in history if h.get("avg_kast")]
        u_rating = sum(ratings) / len(ratings) if ratings else 0.0
        u_kd = sum(kds) / len(kds) if kds else 0.0
        u_adr = sum(adrs) / len(adrs) if adrs else 0.0
        u_kast = sum(kasts) / len(kasts) if kasts else 0.0

        # Pro cohort: every is_pro=True row tagged with computed quality.
        with get_db_manager().get_session() as session:
            pro_rows = session.exec(
                select(
                    PlayerMatchStats.rating,
                    PlayerMatchStats.kd_ratio,
                    PlayerMatchStats.avg_adr,
                    PlayerMatchStats.avg_kast,
                ).where(
                    PlayerMatchStats.is_pro == True,  # noqa: E712
                    PlayerMatchStats.data_quality.not_in(("registered_only", "partial", "none")),
                )
            ).all()

        if not pro_rows:
            return {}

        def _pct(user_v: float, pro_vals: list[float]) -> float:
            cleaned = [float(v) for v in pro_vals if v is not None]
            if not cleaned:
                return 0.0
            beaten = sum(1 for v in cleaned if user_v >= v)
            return beaten / len(cleaned)

        return {
            "rating": _pct(u_rating, [r[0] for r in pro_rows]),
            "kd": _pct(u_kd, [r[1] for r in pro_rows]),
            "adr": _pct(u_adr, [r[2] for r in pro_rows]),
            "kast": _pct(u_kast, [r[3] for r in pro_rows]),
        }

    def _on_loaded(self, result):
        self._is_loading = False
        self.is_loading_changed.emit(False)
        if result:
            history, map_stats, sw, utility, is_pro_overview, context = result
            self.data_changed.emit(history, map_stats, sw, utility, is_pro_overview)
            self.context_changed.emit(context or {})

    def _on_error(self, msg):
        logger.error("performance_vm.load_failed: %s", msg)
        self._is_loading = False
        self.is_loading_changed.emit(False)
        self.error_changed.emit(str(msg))
