"""ProComparisonViewModel — loads pro player stats for side-by-side comparison."""

from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_pro_comparison_vm")

# Metrics to compare, with display name and whether "lower is better"
COMPARISON_METRICS = [
    # (db_field, display_name, lower_is_better)
    ("rating_2_0", "Rating 2.0", False),
    ("kpr", "Kills / Round", False),
    ("dpr", "Deaths / Round", True),
    ("adr", "Damage / Round", False),
    ("kast", "KAST", False),
    ("headshot_pct", "Headshot %", False),
    ("impact", "Impact Rating", False),
    ("opening_duel_win_pct", "Opening Duel Win %", False),
    ("opening_kill_ratio", "Opening Kill Ratio", False),
    ("clutch_win_count", "Clutch Wins", False),
    ("multikill_round_pct", "Multikill Round %", False),
    ("maps_played", "Maps Played", False),
]


class ProComparisonViewModel(QObject):
    """Fetches pro player data for comparison."""

    players_loaded = Signal(list)  # [{hltv_id, nickname, team}]
    comparison_ready = Signal(dict, dict, str, str)  # stats_a, stats_b, name_a, name_b
    error_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def load_pro_list(self):
        worker = Worker(self._bg_load_players)
        worker.signals.result.connect(self._on_players)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def compare_pros(self, hltv_id_a: int, hltv_id_b: int):
        worker = Worker(self._bg_compare_pros, hltv_id_a, hltv_id_b)
        worker.signals.result.connect(self._on_comparison)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def compare_user_vs_pro(self, hltv_id: int):
        worker = Worker(self._bg_compare_user_vs_pro, hltv_id)
        worker.signals.result.connect(self._on_comparison)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    # ── Background tasks ──

    @staticmethod
    def _bg_load_players() -> List[Dict]:
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProTeam

        with get_hltv_db_manager().get_session() as s:
            players = s.exec(
                select(ProPlayer).order_by(ProPlayer.nickname)
            ).all()
            # Fetch team names
            teams = {t.hltv_id: t.name for t in s.exec(select(ProTeam)).all()}

            return [
                {
                    "hltv_id": p.hltv_id,
                    "nickname": p.nickname,
                    "team": teams.get(p.team_id, "—"),
                }
                for p in players
            ]

    @staticmethod
    def _bg_compare_pros(id_a: int, id_b: int):
        stats_a, name_a = ProComparisonViewModel._get_pro_stats(id_a)
        stats_b, name_b = ProComparisonViewModel._get_pro_stats(id_b)
        return stats_a, stats_b, name_a, name_b

    @staticmethod
    def _bg_compare_user_vs_pro(pro_id: int):
        user_stats, user_name = ProComparisonViewModel._get_user_stats()
        pro_stats, pro_name = ProComparisonViewModel._get_pro_stats(pro_id)
        return user_stats, pro_stats, user_name, pro_name

    @staticmethod
    def _get_pro_stats(hltv_id: int):
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard

        with get_hltv_db_manager().get_session() as s:
            player = s.exec(
                select(ProPlayer).where(ProPlayer.hltv_id == hltv_id)
            ).first()
            card = s.exec(
                select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == hltv_id)
            ).first()

        if not player or not card:
            return {}, "Unknown"

        stats = {}
        for field, _, _ in COMPARISON_METRICS:
            val = getattr(card, field, 0.0)
            stats[field] = float(val) if val is not None else 0.0

        return stats, player.nickname

    @staticmethod
    def _get_user_stats():
        from sqlalchemy import func
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
        from Programma_CS2_RENAN.core.config import get_setting

        player = get_setting("CS2_PLAYER_NAME", "")
        if not player:
            return {}, "You"

        with get_db_manager().get_session() as s:
            count = s.exec(
                select(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.player_name == player,
                    PlayerMatchStats.is_pro == False,  # noqa: E712
                )
            ).one()

            if not count or count == 0:
                return {}, player  # Empty — no personal matches

            row = s.exec(
                select(
                    func.avg(PlayerMatchStats.rating).label("rating_2_0"),
                    func.avg(PlayerMatchStats.kpr).label("kpr"),
                    func.avg(PlayerMatchStats.dpr).label("dpr"),
                    func.avg(PlayerMatchStats.avg_adr).label("adr"),
                    func.avg(PlayerMatchStats.avg_kast).label("kast"),
                    func.avg(PlayerMatchStats.avg_hs).label("headshot_pct"),
                    func.avg(PlayerMatchStats.opening_duel_win_pct).label("opening_duel_win_pct"),
                    func.avg(PlayerMatchStats.clutch_win_pct).label("clutch_win_count"),
                ).where(
                    PlayerMatchStats.player_name == player,
                    PlayerMatchStats.is_pro == False,  # noqa: E712
                )
            ).first()

        if not row or row[0] is None:
            return {}, player

        field_names = [
            "rating_2_0", "kpr", "dpr", "adr", "kast",
            "headshot_pct", "opening_duel_win_pct", "clutch_win_count",
        ]
        stats = {}
        for i, name in enumerate(field_names):
            stats[name] = float(row[i]) if row[i] is not None else 0.0

        # Fields not in PlayerMatchStats — set to 0
        stats.setdefault("impact", 0.0)
        stats.setdefault("opening_kill_ratio", 0.0)
        stats.setdefault("multikill_round_pct", 0.0)
        stats.setdefault("maps_played", count)

        return stats, player

    # ── Signal handlers ──

    def _on_players(self, data):
        if data is not None:
            self.players_loaded.emit(data)

    def _on_comparison(self, result):
        if result is not None:
            stats_a, stats_b, name_a, name_b = result
            self.comparison_ready.emit(stats_a, stats_b, name_a, name_b)

    def _on_error(self, msg):
        logger.error("pro_comparison_vm error: %s", msg)
        self.error_changed.emit(str(msg))
