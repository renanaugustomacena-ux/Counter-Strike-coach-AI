"""
Utility Efficiency Analyzer

Analyzes grenade and utility usage effectiveness.
Provides insights on smoke, flash, molotov, and HE efficiency.

Features:
- Utility damage scoring
- Flash efficiency metrics
- Smoke placement analysis
- Economy-per-utility tracking
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.utility_analyzer")


class UtilityType(Enum):
    """Types of utility."""

    SMOKE = "smoke"
    FLASH = "flash"
    MOLOTOV = "molotov"
    HE = "he_grenade"


@dataclass
class UtilityStats:
    """Statistics for utility usage."""

    utility_type: UtilityType
    total_thrown: int
    damage_dealt: float
    enemies_affected: int
    effectiveness_score: float  # 0-1 normalized


@dataclass
class UtilityReport:
    """Complete utility analysis report."""

    overall_score: float
    utility_stats: Dict[UtilityType, UtilityStats]
    recommendations: List[str]
    economy_impact: float  # $ value of utility effectiveness


class UtilityAnalyzer:
    """
    Analyzes utility usage and provides recommendations.

    Scoring based on:
    - Damage per utility (molotov/HE)
    - Enemies flashed (flash)
    - Strategic value (smokes)
    """

    # P8-06: Pro utility baselines. Hand-estimated from manual analysis of
    # pro match VODs. Validation: compute actual averages from parsed pro demo
    # files and update with empirical values.
    # - Molotov: avg damage per throw from pro demos (estimated 30-40 HP)
    # - HE: avg damage per throw from pro demos (estimated 20-30 HP)
    # - Flash: avg enemies blinded per throw from pro demos (estimated 1.0-1.5)
    # - Smoke: strategic value is a normalized 0-1 score (no direct measurement)
    # - usage_rate: fraction of buy rounds where utility type is purchased
    PRO_BASELINES = {
        UtilityType.MOLOTOV: {"damage_per_throw": 35, "usage_rate": 0.7},
        UtilityType.HE: {"damage_per_throw": 25, "usage_rate": 0.5},
        UtilityType.FLASH: {"enemies_per_flash": 1.2, "usage_rate": 0.8},
        UtilityType.SMOKE: {"strategic_value": 0.9, "usage_rate": 0.9},
    }

    def __init__(self):
        pass

    def analyze(self, player_stats: Dict) -> UtilityReport:
        """
        Analyze utility usage from player stats.

        Args:
            player_stats: Dictionary with utility statistics

        Returns:
            UtilityReport with scores and recommendations
        """
        utility_stats = {}
        recommendations = []

        # Analyze each utility type
        for util_type in UtilityType:
            stats = self._analyze_utility_type(player_stats, util_type)
            utility_stats[util_type] = stats

            # Generate recommendations
            if stats.effectiveness_score < 0.5:
                recommendations.append(self._generate_recommendation(util_type, stats))

        # Calculate overall score
        overall_score = np.mean([s.effectiveness_score for s in utility_stats.values()])

        # Calculate economy impact
        economy_impact = self._calculate_economy_impact(utility_stats)

        return UtilityReport(
            overall_score=overall_score,
            utility_stats=utility_stats,
            recommendations=recommendations,
            economy_impact=economy_impact,
        )

    def _analyze_utility_type(self, stats: Dict, util_type: UtilityType) -> UtilityStats:
        """Analyze specific utility type."""
        prefix = util_type.value

        thrown = stats.get(f"{prefix}_thrown", 0)
        damage = stats.get(f"{prefix}_damage", 0)
        affected = stats.get(f"{prefix}_affected", 0)

        # Calculate effectiveness
        if util_type in [UtilityType.MOLOTOV, UtilityType.HE]:
            damage_per_throw = damage / max(thrown, 1)
            baseline = self.PRO_BASELINES[util_type]["damage_per_throw"]
            effectiveness = min(damage_per_throw / baseline, 1.0)
        elif util_type == UtilityType.FLASH:
            affected_per_throw = affected / max(thrown, 1)
            baseline = self.PRO_BASELINES[util_type]["enemies_per_flash"]
            effectiveness = min(affected_per_throw / baseline, 1.0)
        else:  # Smoke
            usage_rate = thrown / max(stats.get("rounds_played", 20), 1)
            baseline = self.PRO_BASELINES[util_type]["usage_rate"]
            effectiveness = min(usage_rate / baseline, 1.0)

        return UtilityStats(
            utility_type=util_type,
            total_thrown=thrown,
            damage_dealt=damage,
            enemies_affected=affected,
            effectiveness_score=effectiveness,
        )

    def _generate_recommendation(self, util_type: UtilityType, stats: UtilityStats) -> str:
        """Generate improvement recommendation."""
        recommendations = {
            UtilityType.MOLOTOV: "Practice damage lineups. Target 35+ damage per molly.",
            UtilityType.HE: "Use HE grenades for anti-eco. Stack with teammates.",
            UtilityType.FLASH: "Coordinate flashes with entry. Aim for 1+ enemy per flash.",
            UtilityType.SMOKE: "Use all smokes each round. Learn 3+ lineups per map.",
        }
        # Emoji stripped — presentation is UI concern
        return f"{util_type.value.title()}: {recommendations.get(util_type, 'Improve utility usage')}"

    def _calculate_economy_impact(self, utility_stats: Dict) -> float:
        """Calculate dollar value of utility efficiency."""
        # Utility costs
        costs = {
            UtilityType.MOLOTOV: 400,
            UtilityType.HE: 300,
            UtilityType.FLASH: 200,
            UtilityType.SMOKE: 300,
        }

        total_value = 0
        for util_type, stats in utility_stats.items():
            cost = costs.get(util_type, 0)
            value = cost * stats.effectiveness_score * stats.total_thrown
            total_value += value

        return total_value


def get_utility_analyzer() -> UtilityAnalyzer:
    """Factory function."""
    return UtilityAnalyzer()


# =============================================================================
# Economy Optimizer
# =============================================================================


@dataclass
class EconomyDecision:
    """Recommended economy decision."""

    action: str  # "full-buy", "force-buy", "eco", "half-buy"
    confidence: float
    reasoning: str
    recommended_weapons: List[str]


class EconomyOptimizer:
    """
    Optimizes buy decisions based on economy state.

    Considers:
    - Current money
    - Round number
    - Score differential
    - Loss bonus
    """

    # Weapon costs
    WEAPON_COSTS = {
        "AK-47": 2700,
        "M4A4": 3100,
        "M4A1-S": 2900,
        "AWP": 4750,
        "Galil": 1800,
        "Famas": 2050,
        "MAC-10": 1050,
        "MP9": 1250,
        "UMP": 1200,
        "Deagle": 700,
        "P250": 300,
        "Five-Seven": 500,
    }

    FULL_BUY_THRESHOLD = 4000  # Minimum for full buy
    FORCE_BUY_THRESHOLD = 2000  # Minimum for force

    # P3-12: MR format → second-half pistol round number.
    # MR12 (CS2 default since Sep 2023): halftime after round 12, pistol at 13.
    # MR13: halftime after round 15, pistol at 16 (tournament/legacy formats).
    HALF_ROUND = {12: 13, 13: 16}
    MR_FORMAT_DEFAULT = 12

    def __init__(self):
        pass

    def recommend(
        self,
        current_money: int,
        round_number: int,
        is_ct: bool = True,
        score_diff: int = 0,
        loss_bonus: int = 1900,
        mr_format: int = MR_FORMAT_DEFAULT,
    ) -> EconomyDecision:
        """
        Recommend economy decision.

        Args:
            current_money: Player's current money
            round_number: Current round number
            is_ct: Whether player is CT
            score_diff: Score difference (positive = winning)
            loss_bonus: Current loss bonus amount
            mr_format: Max Rounds format (12 or 13). Default: 12 (CS2 standard).

        Returns:
            EconomyDecision with recommendation
        """
        # Special round handling
        if round_number == 1:
            return self._pistol_round_decision(current_money, is_ct)

        # P3-12: configurable half-round detection instead of hardcoded [13, 25]
        half_round = self.HALF_ROUND.get(mr_format, 13)
        if round_number == half_round:
            return self._overtime_decision(current_money, is_ct)

        # Standard decision logic
        if current_money >= self.FULL_BUY_THRESHOLD + 1000:
            return self._full_buy_decision(current_money, is_ct)

        elif current_money >= self.FORCE_BUY_THRESHOLD:
            # Force or save decision
            if round_number <= 3 or score_diff <= -5:
                return self._force_buy_decision(current_money, is_ct)
            else:
                return self._half_buy_decision(current_money, is_ct)

        else:
            # Eco round
            return self._eco_decision(current_money, is_ct, loss_bonus)

    def _pistol_round_decision(self, money: int, is_ct: bool) -> EconomyDecision:
        """Pistol round recommendation."""
        if is_ct:
            return EconomyDecision(
                action="pistol",
                confidence=0.95,
                reasoning="Pistol round: Buy armor + utility",
                recommended_weapons=["USP-S", "Kevlar", "Kit"],
            )
        else:
            return EconomyDecision(
                action="pistol",
                confidence=0.95,
                reasoning="Pistol round: Buy armor or Tec-9",
                recommended_weapons=["Glock", "Kevlar", "Flash x2"],
            )

    def _full_buy_decision(self, money: int, is_ct: bool) -> EconomyDecision:
        """Full buy recommendation."""
        if is_ct:
            weapons = ["M4A4", "Kevlar+Helmet", "Full utility"]
        else:
            weapons = ["AK-47", "Kevlar+Helmet", "Full utility"]

        return EconomyDecision(
            action="full-buy",
            confidence=0.9,
            reasoning=f"Full buy: ${money} available",
            recommended_weapons=weapons,
        )

    def _force_buy_decision(self, money: int, is_ct: bool) -> EconomyDecision:
        """Force buy recommendation."""
        if is_ct:
            weapons = ["Famas", "Kevlar", "Flash"]
        else:
            weapons = ["Galil", "Kevlar", "Flash"]

        return EconomyDecision(
            action="force-buy",
            confidence=0.7,
            reasoning=f"Force buy: Maximize impact with ${money}",
            recommended_weapons=weapons,
        )

    def _half_buy_decision(self, money: int, is_ct: bool) -> EconomyDecision:
        """Half buy (SMG) recommendation."""
        return EconomyDecision(
            action="half-buy",
            confidence=0.65,
            reasoning=f"Half-buy: SMG + utility with ${money}",
            recommended_weapons=["UMP" if is_ct else "MAC-10", "Kevlar", "Flash"],
        )

    def _eco_decision(self, money: int, is_ct: bool, loss_bonus: int) -> EconomyDecision:
        """Eco round recommendation."""
        next_round_money = money + loss_bonus

        if money >= 500:
            weapons = ["P250", "Flash"]
        else:
            weapons = ["Default pistol"]

        return EconomyDecision(
            action="eco",
            confidence=0.85,
            reasoning=f"Eco: Save for ${next_round_money} next round",
            recommended_weapons=weapons,
        )

    def _overtime_decision(self, money: int, is_ct: bool) -> EconomyDecision:
        """Overtime/half change recommendation."""
        return EconomyDecision(
            action="full-buy",
            confidence=0.95,
            reasoning="Critical round: Full buy regardless",
            recommended_weapons=["Best weapons", "Full utility"],
        )


def get_economy_optimizer() -> EconomyOptimizer:
    """Factory function."""
    return EconomyOptimizer()


if __name__ == "__main__":
    # Self-tests
    logger.info("=== Utility Analyzer Test ===")

    analyzer = UtilityAnalyzer()
    # NOTE: Synthetic values for self-test only — not representative of real match data.
    stats = {
        "molotov_thrown": 10,
        "molotov_damage": 280,
        "he_grenade_thrown": 5,
        "he_grenade_damage": 98,
        "flash_thrown": 15,
        "flash_affected": 12,
        "smoke_thrown": 18,
        "rounds_played": 24,
    }

    report = analyzer.analyze(stats)
    logger.info("Overall Utility Score: %.0f%%", report.overall_score * 100)
    logger.info("Economy Impact: $%.0f", report.economy_impact)
    logger.info("Recommendations: %s", len(report.recommendations))

    logger.info("=== Economy Optimizer Test ===")

    optimizer = EconomyOptimizer()

    scenarios = [
        ("Pistol round", 800, 1, True),
        ("Full buy", 5500, 5, True),
        ("Force buy", 2500, 3, False),
        ("Eco round", 1200, 4, True),
    ]

    for name, money, round_num, is_ct in scenarios:
        decision = optimizer.recommend(money, round_num, is_ct)
        logger.info("%s: %s - %s", name, decision.action, decision.reasoning)
