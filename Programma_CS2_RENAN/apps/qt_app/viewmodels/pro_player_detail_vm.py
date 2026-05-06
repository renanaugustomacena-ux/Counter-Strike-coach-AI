"""ProPlayerDetailViewModel — fetches one pro's full profile by hltv_id.

Reads from hltv_metadata.db (ProPlayer, ProPlayerStatCard, ProTeam) and
emits a single composite dict keyed by all-time time_span. Sub-tabs
for 3M / 6M / 12M time spans are out of scope for this minimal pass —
see docs/master plan for the full keyspace; this VM ships the
all-time view that powers the drill-down screen.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_pro_player_detail_vm")


class ProPlayerDetailViewModel(QObject):
    """Loads a single pro player's profile for the drill-down screen."""

    profile_loaded = Signal(dict)  # composite dict with player + stats + team
    error_changed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def load_pro(self, hltv_id: int) -> None:
        worker = Worker(self._bg_load, hltv_id)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    @staticmethod
    def _bg_load(hltv_id: int) -> Dict[str, Any]:
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import (
            ProPlayer,
            ProPlayerStatCard,
            ProTeam,
        )

        with get_hltv_db_manager().get_session() as s:
            player = s.exec(select(ProPlayer).where(ProPlayer.hltv_id == hltv_id)).first()
            if player is None:
                return {"error": f"Player hltv_id={hltv_id} not found"}

            team = None
            if player.team_id:
                team = s.exec(select(ProTeam).where(ProTeam.hltv_id == player.team_id)).first()

            # Prefer all_time stat card; fall back to whatever exists.
            cards = s.exec(
                select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == hltv_id)
            ).all()
            preferred = None
            for c in cards:
                if (c.time_span or "").lower() in ("all_time", "alltime", "all"):
                    preferred = c
                    break
            if preferred is None and cards:
                preferred = cards[0]

            # Decode detailed_stats_json with a guard — corrupt JSON is
            # surfaced as an empty dict so the screen doesn't crash.
            detailed: Dict[str, Any] = {}
            if preferred and preferred.detailed_stats_json:
                try:
                    detailed = json.loads(preferred.detailed_stats_json)
                except (json.JSONDecodeError, TypeError):
                    detailed = {}

            return {
                "hltv_id": player.hltv_id,
                "nickname": player.nickname,
                "real_name": player.real_name or "",
                "country": player.country or "",
                "age": player.age,
                "team_name": team.name if team else "—",
                "team_rank": team.world_rank if team else None,
                "stat_card": {
                    "time_span": preferred.time_span if preferred else "n/a",
                    "rating_2_0": preferred.rating_2_0 if preferred else 0.0,
                    "kpr": preferred.kpr if preferred else 0.0,
                    "dpr": preferred.dpr if preferred else 0.0,
                    "adr": preferred.adr if preferred else 0.0,
                    "kast": preferred.kast if preferred else 0.0,
                    "headshot_pct": preferred.headshot_pct if preferred else 0.0,
                    "impact": preferred.impact if preferred else 0.0,
                    "opening_duel_win_pct": (preferred.opening_duel_win_pct if preferred else 0.0),
                    "opening_kill_ratio": (preferred.opening_kill_ratio if preferred else 0.0),
                    "clutch_win_count": preferred.clutch_win_count if preferred else 0,
                    "multikill_round_pct": (preferred.multikill_round_pct if preferred else 0.0),
                    "maps_played": preferred.maps_played if preferred else 0,
                },
                "detailed": detailed,
                "available_time_spans": sorted({(c.time_span or "n/a") for c in cards}),
            }

    def _on_loaded(self, result: Dict[str, Any]) -> None:
        if "error" in result:
            self.error_changed.emit(str(result["error"]))
            return
        self.profile_loaded.emit(result)

    def _on_error(self, msg: str) -> None:
        logger.error("pro_player_detail_vm.load_failed: %s", msg)
        self.error_changed.emit(str(msg))
