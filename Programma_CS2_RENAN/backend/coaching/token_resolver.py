import json
from typing import Any, Dict, Optional

from sqlmodel import select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.token_resolver")


class PlayerTokenResolver:
    """
    Resolves static "Player Tokens" (Cards) for the AI Coach.
    Allows the Brain to compare dynamic match performance against long-term Pro profiles.
    """

    def __init__(self):
        self.db = get_db_manager()

    def get_player_token(self, player_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the complete static profile (Token) for a professional player.
        """
        with self.db.get_session() as session:
            # 1. Find the Player ID
            pro = session.exec(select(ProPlayer).where(ProPlayer.nickname == player_name)).first()

            if not pro:
                logger.debug("No Pro Token found for %s", player_name)
                return None

            # 2. Fetch the latest Stat Card
            card = session.exec(
                select(ProPlayerStatCard)
                .where(ProPlayerStatCard.player_id == pro.hltv_id)
                .order_by(ProPlayerStatCard.last_updated.desc())
            ).first()

            if not card:
                logger.warning("Pro Player %s exists but has no Stat Card Token.", player_name)
                return None

            return self._build_token_dict(pro, card)

    def _build_token_dict(self, player: ProPlayer, card: ProPlayerStatCard) -> Dict[str, Any]:
        """Assembles the high-fidelity Token dictionary."""
        try:
            detailed_stats = (
                json.loads(card.detailed_stats_json) if card.detailed_stats_json else {}
            )
        except (json.JSONDecodeError, TypeError):
            logger.warning("Malformed detailed_stats_json for player %s", player.nickname)
            detailed_stats = {}

        token = {
            "identity": {
                "name": player.nickname,
                "real_name": player.real_name,
                "hltv_id": player.hltv_id,
            },
            "core_metrics": {
                "rating": card.rating_2_0,
                "adr": card.adr,
                "kast": card.kast,
                "kpr": card.kpr,
                "dpr": card.dpr,
                "hs_pct": card.headshot_pct,
                "maps_played": card.maps_played,
            },
            "tactical_baselines": {
                "opening_win_pct": card.opening_duel_win_pct,
                "opening_kill_ratio": card.opening_kill_ratio,
                "clutches_won": card.clutch_win_count,
                "multikill_round_pct": card.multikill_round_pct,
            },
            "granular_data": detailed_stats,
            "metadata": {
                "last_updated": card.last_updated.isoformat(),
                "time_span": card.time_span,
            },
        }
        return token

    def compare_performance_to_token(
        self, match_stats: Dict[str, Any], token: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compares specific match stats against the static Token reference.
        Returns a 'Correction Delta' used by the Coach for expert assessment.
        """
        core = token["core_metrics"]
        baselines = token["tactical_baselines"]

        comparison = {
            "player": token["identity"]["name"],
            "deltas": {
                "rating": match_stats.get("rating", 0) - core["rating"],
                "adr": match_stats.get("avg_adr", 0) - core["adr"],
                "kast": match_stats.get("avg_kast", 0) - core["kast"],
                "accuracy_vs_hs": match_stats.get("avg_hs", 0) - core["hs_pct"],
            },
            "is_underperforming": match_stats.get("rating", 0) < (core["rating"] * 0.85),
        }

        return comparison
