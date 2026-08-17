"""MatchDetailViewModel — QObject port of data_viewmodels.MatchDetailViewModel."""

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_match_detail_vm")


class MatchDetailViewModel(QObject):
    """Loads match stats, rounds, insights, HLTV breakdown in background."""

    data_changed = Signal(dict, list, list, dict)  # stats, rounds, insights, hltv
    is_loading_changed = Signal(bool)
    error_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = False

    @property
    def is_loading(self):
        return self._is_loading

    def load_detail(self, demo_name: str):
        if not demo_name or not demo_name.strip():
            self.error_changed.emit("No demo selected.")
            return
        if self._is_loading:
            return
        self._is_loading = True
        self.is_loading_changed.emit(True)
        self.error_changed.emit("")

        worker = Worker(self._bg_load, demo_name)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _bg_load(self, demo_name: str):
        player = get_setting("CS2_PLAYER_NAME", "")

        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import (
            CoachingInsight,
            PlayerMatchStats,
            RoundStats,
        )

        with get_db_manager().get_session() as session:
            # Try user's name first, then any player in that demo
            match_stats = None
            if player:
                match_stats = session.exec(
                    select(PlayerMatchStats).where(
                        PlayerMatchStats.demo_name == demo_name,
                        PlayerMatchStats.player_name == player,
                    )
                ).first()
            if match_stats is None:
                match_stats = session.exec(
                    select(PlayerMatchStats).where(
                        PlayerMatchStats.demo_name == demo_name,
                    )
                ).first()

            # Use the actual player name from the match for round/insight queries
            effective_player = match_stats.player_name if match_stats else player

            rounds = session.exec(
                select(RoundStats)
                .where(
                    RoundStats.demo_name == demo_name,
                    RoundStats.player_name == effective_player,
                )
                .order_by(RoundStats.round_number.asc())
            ).all()

            insights = session.exec(
                select(CoachingInsight)
                .where(CoachingInsight.demo_name == demo_name)
                .order_by(CoachingInsight.created_at.desc())
            ).all()

            stats_dict = {}
            if match_stats:
                # Every field below exists on backend.storage.db_models
                # .PlayerMatchStats (frame-09 Overview consumes them). The
                # kill-enrichment pct fields are model columns too, though
                # older ingests may have left them at their 0.0 default.
                stats_dict = {
                    "demo_name": match_stats.demo_name,
                    "match_date": match_stats.match_date,
                    "rating": match_stats.rating,
                    "avg_kills": match_stats.avg_kills,
                    "avg_deaths": match_stats.avg_deaths,
                    "avg_adr": match_stats.avg_adr,
                    "avg_kast": match_stats.avg_kast,
                    "kd_ratio": match_stats.kd_ratio,
                    "avg_hs": match_stats.avg_hs,
                    "kpr": match_stats.kpr,
                    "dpr": match_stats.dpr,
                    # HLTV 2.0 per-match components
                    "rating_impact": match_stats.rating_impact,
                    "rating_survival": match_stats.rating_survival,
                    "rating_kast": match_stats.rating_kast,
                    "rating_kpr": match_stats.rating_kpr,
                    "rating_adr": match_stats.rating_adr,
                    # Trade / duel metrics (ratios 0-1)
                    "trade_kill_ratio": match_stats.trade_kill_ratio,
                    "was_traded_ratio": match_stats.was_traded_ratio,
                    "opening_duel_win_pct": match_stats.opening_duel_win_pct,
                    "clutch_win_pct": match_stats.clutch_win_pct,
                    "positional_aggression_score": match_stats.positional_aggression_score,
                    # Kill enrichment (ratios 0-1)
                    "thrusmoke_kill_pct": match_stats.thrusmoke_kill_pct,
                    "wallbang_kill_pct": match_stats.wallbang_kill_pct,
                    "noscope_kill_pct": match_stats.noscope_kill_pct,
                    "blind_kill_pct": match_stats.blind_kill_pct,
                    # Utility breakdown
                    "he_damage_per_round": match_stats.he_damage_per_round,
                    "molotov_damage_per_round": match_stats.molotov_damage_per_round,
                    "smokes_per_round": match_stats.smokes_per_round,
                    "flash_assists": match_stats.flash_assists,
                    "unused_utility_per_round": match_stats.unused_utility_per_round,
                }

            rounds_data = [
                {
                    "round_number": r.round_number,
                    "side": r.side,
                    "kills": r.kills,
                    "deaths": r.deaths,
                    "damage_dealt": r.damage_dealt,
                    "opening_kill": r.opening_kill,
                    # RoundStats.opening_death — feeds the Overview OK-delta caption
                    "opening_death": r.opening_death,
                    "equipment_value": r.equipment_value,
                    "round_won": r.round_won,
                }
                for r in rounds
            ]

            insights_data = [
                {
                    "title": i.title,
                    "message": i.message,
                    "severity": i.severity,
                    "focus_area": i.focus_area,
                }
                for i in insights
            ]

        breakdown = {}
        try:
            from Programma_CS2_RENAN.backend.reporting.analytics import analytics

            # R4 MED: use the match's effective player — on a demo where the
            # configured user did not play (e.g. a pro demo) the stats and
            # rounds show the demo's actual player, but this card showed the
            # configured user's aggregate: mislabeled data.
            breakdown = analytics.get_hltv2_breakdown(effective_player) or {}
        except Exception as e:
            logger.warning("hltv_breakdown.bg_fetch_failed: %s", e)

        return (stats_dict, rounds_data, insights_data, breakdown)

    def _on_loaded(self, result):
        self._is_loading = False
        self.is_loading_changed.emit(False)
        if result:
            stats, rounds, insights, breakdown = result
            self.data_changed.emit(stats, rounds, insights, breakdown)

    def _on_error(self, msg):
        logger.error("match_detail_vm.load_failed: %s", msg)
        self._is_loading = False
        self.is_loading_changed.emit(False)
        self.error_changed.emit(str(msg))
