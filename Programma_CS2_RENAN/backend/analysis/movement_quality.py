"""
Movement Quality Analysis — Detect 4 common positioning mistakes from tick data.

Based on MLMove paper (SIGGRAPH 2024, Stanford/Activision/NVIDIA) findings:
1. Leaving high ground unnecessarily
2. Leaving established positions prematurely
3. Being overly aggressive when trading
4. Being overly passive when supporting

This module is ADDITIVE — it does not modify METADATA_DIM=25. Movement metrics
are computed as derived features from existing tick data, stored in analysis
results, not added to the feature vector.

Usage:
    from Programma_CS2_RENAN.backend.analysis.movement_quality import (
        MovementQualityAnalyzer, get_movement_quality_analyzer,
    )
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from Programma_CS2_RENAN.core.map_callouts import get_callout
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.analysis.movement_quality")

# --- Thresholds ---
# CS2: 128 ticks/sec
_TICKS_PER_SECOND = 128
# Minimum position hold time to count as "established" (3 seconds)
_ESTABLISHED_HOLD_TICKS = 3 * _TICKS_PER_SECOND
# Minimum Z-axis descent to flag high ground abandonment (units)
_HIGH_GROUND_DROP = 100.0
# Ticks around a kill/death event to consider "in combat"
_COMBAT_PROXIMITY_TICKS = 64
# Distance (world units) to count as "nearby" a teammate for trading
_TRADE_SUPPORT_DISTANCE = 800.0
# Distance for "within audio range" of an engagement
_AUDIO_RANGE_DISTANCE = 1500.0
# Minimum movement to count as "advanced" toward engagement
_ADVANCE_THRESHOLD = 100.0
# Position change threshold (world units) to count as "moved"
_MOVEMENT_THRESHOLD = 300.0
# Seconds after teammate death to check for push behavior
_TRADE_WINDOW_SECONDS = 5
_TRADE_WINDOW_TICKS = _TRADE_WINDOW_SECONDS * _TICKS_PER_SECOND


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------


@dataclass
class MovementMistake:
    """A detected movement/positioning mistake."""

    mistake_type: str  # high_ground_abandoned, position_abandoned,
    # over_aggressive_trade, over_passive_support
    round_number: int
    tick: int
    time_in_round: float  # seconds
    description: str
    callout: str  # map position where it happened
    severity: float = 0.5  # 0.0–1.0 scale


@dataclass
class MovementMetrics:
    """Aggregate movement quality metrics for a match or set of rounds."""

    map_coverage_score: float = 0.0  # fraction of callout positions visited
    high_ground_utilization: float = 0.0  # time in elevated positions / total alive time
    position_stability: float = 0.0  # mean time (sec) at each position before moving
    total_rounds_analyzed: int = 0
    mistakes: List[MovementMistake] = field(default_factory=list)

    @property
    def mistake_count(self) -> int:
        return len(self.mistakes)

    @property
    def mistakes_per_round(self) -> float:
        if self.total_rounds_analyzed == 0:
            return 0.0
        return len(self.mistakes) / self.total_rounds_analyzed

    def summary(self) -> str:
        """One-line summary for coaching context."""
        if not self.mistakes:
            return "No movement mistakes detected."
        counts: Dict[str, int] = {}
        for m in self.mistakes:
            counts[m.mistake_type] = counts.get(m.mistake_type, 0) + 1
        parts = [f"{v}x {k.replace('_', ' ')}" for k, v in sorted(counts.items())]
        return f"Movement issues ({self.total_rounds_analyzed} rounds): {', '.join(parts)}."


# ---------------------------------------------------------------------------
# Tick data helpers
# ---------------------------------------------------------------------------


def _distance_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _distance_3d(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class MovementQualityAnalyzer:
    """
    Analyzes tick-level movement data for common positioning mistakes.

    Expects tick data as a list of dicts (one per tick per player) with keys:
    tick, round_number, time_in_round, pos_x, pos_y, pos_z, health,
    enemies_visible, teammates_alive, enemies_alive, active_weapon, map_name.

    This is the format returned by querying PlayerTickState and converting
    to dicts, or from the demo_loader pipeline.
    """

    def analyze_round_ticks(
        self,
        ticks: List[Dict],
        map_name: str,
        player_name: str = "",
        round_number: int = 0,
    ) -> List[MovementMistake]:
        """
        Analyze a single round's tick data for movement mistakes.

        Args:
            ticks: Chronologically sorted tick dicts for one player, one round.
            map_name: Map identifier for callout lookup.
            player_name: For logging context.
            round_number: For result attribution.

        Returns:
            List of detected MovementMistake instances.
        """
        if len(ticks) < _TICKS_PER_SECOND:
            return []  # Not enough data for meaningful analysis

        mistakes: List[MovementMistake] = []
        rn = round_number or (ticks[0].get("round_number", 0) if ticks else 0)

        # Build combat tick set (ticks near kills/deaths)
        combat_ticks = self._find_combat_ticks(ticks)

        mistakes.extend(self._detect_high_ground_abandonment(ticks, map_name, rn, combat_ticks))
        mistakes.extend(self._detect_premature_position_abandonment(ticks, map_name, rn))
        mistakes.extend(self._detect_over_aggressive_trading(ticks, map_name, rn))
        mistakes.extend(self._detect_over_passive_supporting(ticks, map_name, rn))

        return mistakes

    def analyze_match_ticks(
        self,
        all_ticks: List[Dict],
        map_name: str,
        player_name: str = "",
    ) -> MovementMetrics:
        """
        Analyze an entire match's tick data for movement quality.

        Args:
            all_ticks: All ticks for one player across all rounds, sorted by tick.
            map_name: Map identifier.
            player_name: For logging.

        Returns:
            MovementMetrics with aggregate stats and per-round mistakes.
        """
        # Partition by round
        by_round: Dict[int, List[Dict]] = {}
        for t in all_ticks:
            rn = t.get("round_number", 0)
            by_round.setdefault(rn, []).append(t)

        all_mistakes: List[MovementMistake] = []
        visited_callouts: set = set()
        total_alive_ticks = 0
        total_elevated_ticks = 0
        position_hold_times: List[float] = []

        for rn, round_ticks in sorted(by_round.items()):
            # Per-round mistake detection
            mistakes = self.analyze_round_ticks(round_ticks, map_name, player_name, rn)
            all_mistakes.extend(mistakes)

            # Aggregate metrics
            prev_callout = None
            hold_start = 0
            for t in round_ticks:
                if t.get("health", 0) <= 0:
                    continue
                total_alive_ticks += 1

                # Elevated position tracking
                z = t.get("pos_z", 0.0)
                if z > 50:  # above ground level
                    total_elevated_ticks += 1

                # Callout coverage
                callout = get_callout(
                    map_name, t.get("pos_x", 0), t.get("pos_y", 0), t.get("pos_z", 0)
                )
                if callout != "unknown area":
                    visited_callouts.add(callout)

                # Position stability
                if callout != prev_callout:
                    if prev_callout is not None and hold_start > 0:
                        hold_ticks = t.get("tick", 0) - hold_start
                        if hold_ticks > 0:
                            position_hold_times.append(hold_ticks / _TICKS_PER_SECOND)
                    hold_start = t.get("tick", 0)
                    prev_callout = callout

        # Compute aggregate metrics
        from Programma_CS2_RENAN.core.map_callouts import get_callout_registry

        registry = get_callout_registry()
        total_callouts = len(registry.get_positions(map_name))

        return MovementMetrics(
            map_coverage_score=(
                len(visited_callouts) / total_callouts if total_callouts > 0 else 0.0
            ),
            high_ground_utilization=(
                total_elevated_ticks / total_alive_ticks if total_alive_ticks > 0 else 0.0
            ),
            position_stability=(
                sum(position_hold_times) / len(position_hold_times) if position_hold_times else 0.0
            ),
            total_rounds_analyzed=len(by_round),
            mistakes=all_mistakes,
        )

    # ------------------------------------------------------------------
    # Detector 1: High ground abandonment
    # ------------------------------------------------------------------

    def _detect_high_ground_abandonment(
        self,
        ticks: List[Dict],
        map_name: str,
        round_number: int,
        combat_ticks: set,
    ) -> List[MovementMistake]:
        """Flag when player descends from elevated position without combat context."""
        mistakes = []
        for i in range(1, len(ticks)):
            prev_z = ticks[i - 1].get("pos_z", 0.0)
            curr_z = ticks[i].get("pos_z", 0.0)
            health = ticks[i].get("health", 0)

            if health <= 0:
                continue

            z_drop = prev_z - curr_z
            if z_drop >= _HIGH_GROUND_DROP:
                tick_num = ticks[i].get("tick", 0)
                # Check if this was during combat (justified descent)
                if tick_num in combat_ticks:
                    continue

                callout = get_callout(
                    map_name,
                    ticks[i].get("pos_x", 0),
                    ticks[i].get("pos_y", 0),
                    curr_z,
                )
                mistakes.append(
                    MovementMistake(
                        mistake_type="high_ground_abandoned",
                        round_number=round_number,
                        tick=tick_num,
                        time_in_round=ticks[i].get("time_in_round", 0.0),
                        description=(
                            f"Dropped {z_drop:.0f} units from elevated position "
                            f"near {callout} without enemy contact"
                        ),
                        callout=callout,
                        severity=min(z_drop / 300.0, 1.0),
                    )
                )
        return mistakes

    # ------------------------------------------------------------------
    # Detector 2: Premature position abandonment
    # ------------------------------------------------------------------

    def _detect_premature_position_abandonment(
        self,
        ticks: List[Dict],
        map_name: str,
        round_number: int,
    ) -> List[MovementMistake]:
        """Flag when player leaves a held position without new information."""
        mistakes = []
        hold_start_idx = 0
        hold_x = ticks[0].get("pos_x", 0.0)
        hold_y = ticks[0].get("pos_y", 0.0)

        for i in range(1, len(ticks)):
            health = ticks[i].get("health", 0)
            if health <= 0:
                continue

            curr_x = ticks[i].get("pos_x", 0.0)
            curr_y = ticks[i].get("pos_y", 0.0)
            dist = _distance_2d(hold_x, hold_y, curr_x, curr_y)

            if dist < _MOVEMENT_THRESHOLD:
                continue  # Still in position

            # Player moved — check if they held long enough to count as "established"
            hold_duration = i - hold_start_idx
            if hold_duration >= _ESTABLISHED_HOLD_TICKS:
                # Check if there was new information (enemies visible)
                had_new_info = False
                for j in range(max(0, i - _TICKS_PER_SECOND), i):
                    if ticks[j].get("enemies_visible", 0) > 0:
                        had_new_info = True
                        break

                if not had_new_info:
                    callout = get_callout(map_name, hold_x, hold_y, ticks[i].get("pos_z", 0))
                    hold_sec = hold_duration / _TICKS_PER_SECOND
                    mistakes.append(
                        MovementMistake(
                            mistake_type="position_abandoned",
                            round_number=round_number,
                            tick=ticks[i].get("tick", 0),
                            time_in_round=ticks[i].get("time_in_round", 0.0),
                            description=(
                                f"Left established position at {callout} "
                                f"(held {hold_sec:.1f}s) without new enemy information"
                            ),
                            callout=callout,
                            severity=min(hold_sec / 10.0, 1.0),
                        )
                    )

            # Reset hold tracking
            hold_start_idx = i
            hold_x = curr_x
            hold_y = curr_y

        return mistakes

    # ------------------------------------------------------------------
    # Detector 3: Over-aggressive trading
    # ------------------------------------------------------------------

    def _detect_over_aggressive_trading(
        self,
        ticks: List[Dict],
        map_name: str,
        round_number: int,
    ) -> List[MovementMistake]:
        """Flag when player pushes after teammate death without support nearby."""
        mistakes = []

        for i in range(1, len(ticks)):
            health = ticks[i].get("health", 0)
            if health <= 0:
                continue

            prev_teammates = ticks[i - 1].get("teammates_alive", 4)
            curr_teammates = ticks[i].get("teammates_alive", 4)

            if curr_teammates >= prev_teammates:
                continue  # No teammate lost

            # Teammate died — check if player pushes in the next N ticks
            push_start_x = ticks[i].get("pos_x", 0.0)
            push_start_y = ticks[i].get("pos_y", 0.0)

            end_idx = min(i + _TRADE_WINDOW_TICKS, len(ticks))
            max_advance = 0.0
            for j in range(i + 1, end_idx):
                if ticks[j].get("health", 0) <= 0:
                    break
                jx = ticks[j].get("pos_x", 0.0)
                jy = ticks[j].get("pos_y", 0.0)
                dist = _distance_2d(push_start_x, push_start_y, jx, jy)
                max_advance = max(max_advance, dist)

            if max_advance < _MOVEMENT_THRESHOLD:
                continue  # Player didn't push

            # Check if another teammate was nearby for support
            # We only have this player's ticks, so we use teammates_alive as proxy
            remaining_teammates = curr_teammates
            if remaining_teammates >= 2:
                continue  # At least 2 teammates — probably coordinated

            # Solo push after teammate death with no support
            callout = get_callout(map_name, push_start_x, push_start_y, ticks[i].get("pos_z", 0))
            mistakes.append(
                MovementMistake(
                    mistake_type="over_aggressive_trade",
                    round_number=round_number,
                    tick=ticks[i].get("tick", 0),
                    time_in_round=ticks[i].get("time_in_round", 0.0),
                    description=(
                        f"Pushed {max_advance:.0f} units from {callout} "
                        f"after teammate death in a "
                        f"{curr_teammates + 1}v{ticks[i].get('enemies_alive', 5)} "
                        f"without teammate support nearby"
                    ),
                    callout=callout,
                    severity=0.7,
                )
            )

        return mistakes

    # ------------------------------------------------------------------
    # Detector 4: Over-passive supporting
    # ------------------------------------------------------------------

    def _detect_over_passive_supporting(
        self,
        ticks: List[Dict],
        map_name: str,
        round_number: int,
    ) -> List[MovementMistake]:
        """Flag when player doesn't advance while teammate is engaged nearby."""
        mistakes = []
        # Detect engagement windows: periods where enemies_alive drops
        # (indicating teammate is fighting)
        for i in range(1, len(ticks)):
            health = ticks[i].get("health", 0)
            if health <= 0:
                continue

            prev_enemies = ticks[i - 1].get("enemies_alive", 5)
            curr_enemies = ticks[i].get("enemies_alive", 5)

            if curr_enemies >= prev_enemies:
                continue  # No enemy eliminated, no engagement signal

            # Enemy was eliminated (teammate got a kill) — did this player advance?
            engagement_x = ticks[i].get("pos_x", 0.0)
            engagement_y = ticks[i].get("pos_y", 0.0)

            # Check movement in the 3 seconds after
            check_window = min(i + 3 * _TICKS_PER_SECOND, len(ticks))
            max_movement = 0.0
            for j in range(i + 1, check_window):
                if ticks[j].get("health", 0) <= 0:
                    break
                jx = ticks[j].get("pos_x", 0.0)
                jy = ticks[j].get("pos_y", 0.0)
                dist = _distance_2d(engagement_x, engagement_y, jx, jy)
                max_movement = max(max_movement, dist)

            if max_movement >= _ADVANCE_THRESHOLD:
                continue  # Player did advance

            # Player stayed put while teammate created an opening
            enemies_remaining = curr_enemies
            teammates = ticks[i].get("teammates_alive", 4)
            if teammates + 1 <= enemies_remaining:
                continue  # Man disadvantage — being passive is justified

            callout = get_callout(map_name, engagement_x, engagement_y, ticks[i].get("pos_z", 0))
            mistakes.append(
                MovementMistake(
                    mistake_type="over_passive_support",
                    round_number=round_number,
                    tick=ticks[i].get("tick", 0),
                    time_in_round=ticks[i].get("time_in_round", 0.0),
                    description=(
                        f"Remained stationary at {callout} after teammate "
                        f"eliminated an enemy "
                        f"({teammates + 1}v{enemies_remaining} advantage) "
                        f"— did not capitalize on opening"
                    ),
                    callout=callout,
                    severity=0.5,
                )
            )

        return mistakes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_combat_ticks(self, ticks: List[Dict]) -> set:
        """Build set of tick numbers that are near combat events."""
        combat_ticks: set = set()
        for i, t in enumerate(ticks):
            # Near health drops or kills
            is_combat = False
            if i > 0:
                prev_h = ticks[i - 1].get("health", 100)
                curr_h = t.get("health", 100)
                if curr_h < prev_h:
                    is_combat = True

            if t.get("enemies_visible", 0) > 0:
                is_combat = True

            if is_combat:
                tick_num = t.get("tick", 0)
                for offset in range(-_COMBAT_PROXIMITY_TICKS, _COMBAT_PROXIMITY_TICKS + 1):
                    combat_ticks.add(tick_num + offset)

        return combat_ticks


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------

_analyzer: Optional[MovementQualityAnalyzer] = None


def get_movement_quality_analyzer() -> MovementQualityAnalyzer:
    """Get or create the singleton MovementQualityAnalyzer."""
    global _analyzer  # noqa: PLW0603
    if _analyzer is None:
        _analyzer = MovementQualityAnalyzer()
    return _analyzer
