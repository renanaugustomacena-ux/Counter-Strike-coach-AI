"""
Engagement Range Analytics — Kill distance analysis and named position registry.

Fusion Plan Proposal 7: Spatial Intelligence Expansion.

This module is ADDITIVE — it does not modify spatial_data.py. It provides:
1. NamedPosition registry for human-readable callout positions
2. Engagement range classification from kill-event positions
3. Role-specific range profile comparison against baselines

Usage:
    from Programma_CS2_RENAN.backend.analysis.engagement_range import (
        EngagementRangeAnalyzer, NamedPositionRegistry
    )
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from Programma_CS2_RENAN.core.map_callouts import (  # noqa: F401 — re-exported
    NamedPosition,
    NamedPositionRegistry,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.analysis.engagement_range")


# ---------------------------------------------------------------------------
# Engagement Range Analyzer
# ---------------------------------------------------------------------------

# Range classification thresholds (world units)
RANGE_CLOSE = 500
RANGE_MEDIUM = 1500
RANGE_LONG = 3000


@dataclass
class EngagementProfile:
    """Distribution of kill distances by range category."""

    close_pct: float = 0.0  # < 500 units
    medium_pct: float = 0.0  # 500-1500 units
    long_pct: float = 0.0  # 1500-3000 units
    extreme_pct: float = 0.0  # > 3000 units
    avg_distance: float = 0.0
    total_kills: int = 0


# Expected engagement profiles by role (pro baselines)
_ROLE_RANGE_BASELINES: Dict[str, EngagementProfile] = {
    "awper": EngagementProfile(close_pct=0.10, medium_pct=0.30, long_pct=0.45, extreme_pct=0.15),
    "entry_fragger": EngagementProfile(
        close_pct=0.40, medium_pct=0.40, long_pct=0.15, extreme_pct=0.05
    ),
    "support": EngagementProfile(close_pct=0.25, medium_pct=0.45, long_pct=0.25, extreme_pct=0.05),
    "lurker": EngagementProfile(close_pct=0.35, medium_pct=0.35, long_pct=0.20, extreme_pct=0.10),
    "igl": EngagementProfile(close_pct=0.25, medium_pct=0.40, long_pct=0.25, extreme_pct=0.10),
    "flex": EngagementProfile(close_pct=0.25, medium_pct=0.40, long_pct=0.25, extreme_pct=0.10),
}


class EngagementRangeAnalyzer:
    """
    Analyzes kill distances to build engagement range profiles.

    Uses kill event positions (from demo_parser enrichment) or
    tick-level positions at the time of kills.
    """

    def __init__(self):
        self.position_registry = NamedPositionRegistry()

    @staticmethod
    def compute_kill_distance(
        killer_x: float,
        killer_y: float,
        killer_z: float,
        victim_x: float,
        victim_y: float,
        victim_z: float,
    ) -> float:
        """Euclidean distance between killer and victim in world units."""
        return math.sqrt(
            (killer_x - victim_x) ** 2 + (killer_y - victim_y) ** 2 + (killer_z - victim_z) ** 2
        )

    @staticmethod
    def classify_range(distance: float) -> str:
        """Classify engagement distance into categories."""
        if distance < RANGE_CLOSE:
            return "close"
        elif distance < RANGE_MEDIUM:
            return "medium"
        elif distance < RANGE_LONG:
            return "long"
        return "extreme"

    def compute_profile(self, kill_distances: List[float]) -> EngagementProfile:
        """
        Build an engagement range profile from a list of kill distances.

        Args:
            kill_distances: List of Euclidean distances for each kill.

        Returns:
            EngagementProfile with distribution and statistics.
        """
        if not kill_distances:
            return EngagementProfile()

        total = len(kill_distances)
        close = sum(1 for d in kill_distances if d < RANGE_CLOSE)
        medium = sum(1 for d in kill_distances if RANGE_CLOSE <= d < RANGE_MEDIUM)
        long_ = sum(1 for d in kill_distances if RANGE_MEDIUM <= d < RANGE_LONG)
        extreme = sum(1 for d in kill_distances if d >= RANGE_LONG)

        return EngagementProfile(
            close_pct=close / total,
            medium_pct=medium / total,
            long_pct=long_ / total,
            extreme_pct=extreme / total,
            avg_distance=sum(kill_distances) / total,
            total_kills=total,
        )

    def compare_to_role(self, profile: EngagementProfile, role: str) -> List[str]:
        """
        Compare a player's engagement profile to role-specific baseline.

        Args:
            profile: Player's computed engagement profile.
            role: Player's classified role (e.g., "awper", "entry_fragger").

        Returns:
            List of coaching observations (strings).
        """
        baseline = _ROLE_RANGE_BASELINES.get(role.lower().replace(" ", "_"))
        if not baseline or profile.total_kills < 5:
            return []

        observations = []
        threshold = 0.15  # 15% deviation triggers observation

        if profile.close_pct - baseline.close_pct > threshold:
            observations.append(
                f"Taking more close-range fights than typical {role}s "
                f"({profile.close_pct:.0%} vs {baseline.close_pct:.0%}). "
                f"Consider holding longer angles."
            )
        elif baseline.close_pct - profile.close_pct > threshold:
            observations.append(
                f"Fewer close-range engagements than typical {role}s. "
                f"You may be playing too passively for your role."
            )

        if profile.long_pct - baseline.long_pct > threshold:
            observations.append(
                f"More long-range kills than expected for {role} "
                f"({profile.long_pct:.0%} vs {baseline.long_pct:.0%})."
            )
        elif baseline.long_pct - profile.long_pct > threshold:
            observations.append(
                f"Fewer long-range kills than expected for {role}. "
                f"Consider utilizing sightlines better."
            )

        return observations

    def annotate_kill_position(self, map_name: str, x: float, y: float, z: float = 0.0) -> str:
        """
        Annotate a kill position with the nearest named callout.

        Returns:
            Position name (e.g., "A Site") or "Unknown Position".
        """
        pos = self.position_registry.find_nearest(map_name, x, y, z)
        return pos.name if pos else "Unknown Position"

    def analyze_match_engagements(
        self,
        kill_events: List[Dict],
        map_name: str,
        player_role: str = "flex",
    ) -> Dict:
        """
        Full engagement analysis for a player's kills in a match.

        Args:
            kill_events: List of dicts with keys:
                killer_x, killer_y, killer_z, victim_x, victim_y, victim_z
            map_name: CS2 map name.
            player_role: Player's classified role for baseline comparison.

        Returns:
            Dict with profile, observations, and annotated kills.
        """
        # O-03: Validate map_name before processing — missing metadata silently
        # produces "Unknown Position" for all kills, making analysis worthless.
        if not map_name:
            logger.warning("O-03: analyze_match_engagements called without map_name")

        distances = []
        annotated = []

        for ev in kill_events:
            required = ("killer_x", "killer_y", "victim_x", "victim_y")
            if not all(k in ev for k in required):
                logger.warning("Skipping kill event missing coordinates: %s", list(ev.keys()))
                continue
            dist = self.compute_kill_distance(
                ev.get("killer_x", 0),
                ev.get("killer_y", 0),
                ev.get("killer_z", 0),
                ev.get("victim_x", 0),
                ev.get("victim_y", 0),
                ev.get("victim_z", 0),
            )
            distances.append(dist)

            killer_pos = self.annotate_kill_position(
                map_name,
                ev.get("killer_x", 0),
                ev.get("killer_y", 0),
                ev.get("killer_z", 0),
            )
            victim_pos = self.annotate_kill_position(
                map_name,
                ev.get("victim_x", 0),
                ev.get("victim_y", 0),
                ev.get("victim_z", 0),
            )
            annotated.append(
                {
                    "distance": dist,
                    "range": self.classify_range(dist),
                    "killer_position": killer_pos,
                    "victim_position": victim_pos,
                }
            )

        profile = self.compute_profile(distances)
        observations = self.compare_to_role(profile, player_role)

        return {
            "profile": profile,
            "observations": observations,
            "annotated_kills": annotated,
        }


def get_engagement_range_analyzer() -> EngagementRangeAnalyzer:
    """Factory function for EngagementRangeAnalyzer (consistent with other analysis modules)."""
    return EngagementRangeAnalyzer()
