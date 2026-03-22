"""
Pro Cognitive Bridge

A translation layer that allows the Coach to assimilate "Player Cards"
from HLTV as a unified, stable object. It maps professional Reputations (Stats)
to the Coach's internal cognitive parameters.
"""

import json
from typing import Dict

from Programma_CS2_RENAN.backend.storage.db_models import ProPlayerStatCard
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.pro_bridge")

ESTIMATED_ROUNDS_PER_MATCH = 24.0


class PlayerCardAssimilator:
    """
    Assimilates a ProPlayerStatCard into the Coach's mental model.
    Ensures that the Coach only interacts with a stable set of derived metrics.
    """

    def __init__(self, card: ProPlayerStatCard):
        self.card = card
        try:
            self.details = json.loads(card.detailed_stats_json)
        except (json.JSONDecodeError, TypeError):
            self.details = {}

    def get_coach_baseline(self) -> Dict[str, float]:
        """
        Translates the professional card into the Coach's expected baseline format.
        This provides a "Contextual Pro Baseline" specific to this player.
        """
        # P3-02: Use per-round rates directly (KPR/DPR) to match the scale used by
        # base_features.extract_match_stats() and pro_baseline.py. The previous code
        # multiplied by ESTIMATED_ROUNDS_PER_MATCH (24), producing total-kills-per-match
        # which was 10-20x larger than user stats, making all z-score comparisons invalid.
        baseline = {
            "avg_kills": self.card.kpr,
            "avg_deaths": self.card.dpr,
            "avg_adr": self.card.adr,
            "avg_hs": self._extract_hs_ratio(),
            # V-2: Defensive normalization for old DB records with percentage values.
            "avg_kast": self.card.kast / 100.0 if self.card.kast > 1.0 else self.card.kast,
            "kd_ratio": self.card.kpr / self.card.dpr if self.card.dpr > 0 else self.card.kpr,
            "impact_rounds": self.card.impact,
            "rating": self.card.rating_2_0,
        }

        # Merge in granular details from the JSON if available
        # e.g., mapping "clutches" or "entry" stats
        baseline.update(self._map_detailed_metrics())

        return baseline

    def _extract_hs_ratio(self) -> float:
        """Helper to get HS ratio from card or details."""
        # Core overview usually provides HS %
        # In our spider, we saved it in card_data["core"]["headshot_pct"]
        # which might be in detailed_stats_json if not a direct column
        # V-2: Defensive normalization — JSON details may contain raw percentages.
        raw = self.details.get("core", {}).get("headshot_pct", 0.45)
        return raw / 100.0 if raw > 1.0 else raw

    def _map_detailed_metrics(self) -> Dict[str, float]:
        """
        Maps HLTV-specific detailed metrics to Coach parameters.
        Uses cognitive defaults if metrics are missing.
        """
        mapped = {}

        # Opening Duels (Reputation for Aggression)
        opening = self.details.get("individual", {}).get("total_opening_kills", "0")
        try:
            # Heuristic for entry rate: total opening kills / assumed rounds sample
            ASSUMED_ROUNDS_SAMPLE = 100.0
            mapped["entry_rate"] = (
                float(opening) / ASSUMED_ROUNDS_SAMPLE if float(opening) > 0 else 0.25
            )
        except (ValueError, TypeError):
            mapped["entry_rate"] = 0.25

        # Utility Usage (Reputation for Support)
        util_dmg = self.details.get("individual", {}).get("utility_damage_per_round", "0")
        try:
            mapped["utility_damage"] = float(util_dmg)
        except (ValueError, TypeError):
            mapped["utility_damage"] = 45.0  # Pro Average default

        return mapped

    def get_player_archetype(self) -> str:
        """
        Classifies the player based on the full card profile.
        Used by the Coach to adjust the tone of advice.
        """
        if self.card.impact > 1.3:
            return "Star Fragger"
        if self.card.kast > 0.75:
            return "Support Anchor"
        if self._is_awper():
            return "Sniper Specialist"
        return "All-Rounder"

    def _is_awper(self) -> bool:
        """Detects if player is primarily an AWPer from weapon usage."""
        weapons = self.details.get("weapons", {})
        awp_kills = weapons.get("AWP", 0)
        total_kills = sum(weapons.values()) if weapons else 1
        return (awp_kills / total_kills) > 0.4 if weapons else False


def get_pro_baseline_for_coach(card: ProPlayerStatCard) -> Dict[str, float]:
    """Factory to get baseline directly from a Card."""
    assimilator = PlayerCardAssimilator(card)
    return assimilator.get_coach_baseline()
