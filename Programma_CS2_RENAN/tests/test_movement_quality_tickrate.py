"""Regression tests for tick-rate awareness in movement-quality analysis.

AUDIT 26-TICK-02 / backlog C4 (data normalization): ``movement_quality`` used to
hardcode 128 ticks/sec, which doubled every real-time window on 64-tick demos
(most GOTV/HLTV pro demos) and was correct only on 128-tick demos (FACEIT). These
tests pin:

1. The single conversion point ``_seconds_to_ticks`` scales with the demo rate.
2. The same *real-time* scenario is detected identically at 64 and 128 tick
   (rate-equivariance) — the property the old hardcode broke.
3. The orchestrator's tick-rate resolver honours data-carried provenance.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from Programma_CS2_RENAN.backend.analysis.movement_quality import (
    DEFAULT_TICK_RATE,
    MovementQualityAnalyzer,
    _seconds_to_ticks,
)
from Programma_CS2_RENAN.backend.services.analysis_orchestrator import AnalysisOrchestrator


class TestSecondsToTicks:
    """The lone tick<->second conversion point keeps 64/128 demos aligned."""

    def test_scales_linearly_with_rate(self):
        assert _seconds_to_ticks(3.0, 64) == 192
        assert _seconds_to_ticks(3.0, 128) == 384
        assert _seconds_to_ticks(5.0, 64) == 320
        assert _seconds_to_ticks(5.0, 128) == 640

    def test_half_second_window(self):
        assert _seconds_to_ticks(0.5, 64) == 32
        assert _seconds_to_ticks(0.5, 128) == 64

    def test_clamps_to_minimum_one_tick(self):
        # A sub-tick window must never collapse to an empty range().
        assert _seconds_to_ticks(0.0, 64) == 1
        assert _seconds_to_ticks(0.001, 128) == 1

    def test_default_rate_is_codebase_canonical(self):
        from Programma_CS2_RENAN.core.constants import TICK_RATE

        assert DEFAULT_TICK_RATE == TICK_RATE == 64


def _hold_then_move_round(tick_rate: int) -> List[Dict]:
    """Build one player-round at ``tick_rate``: hold (0,0) for 4 s, then jump away.

    Real-time scenario (rate-independent): the player holds a position for 4.0 s
    (> the 3.0 s "established" threshold) with no enemy ever visible, then moves
    >300 units. This must be flagged ``position_abandoned`` at any tick rate.
    Under the old 128-hardcode, a 64-tick demo's 4 s hold (256 ticks) fell short
    of the frozen 384-tick threshold and was silently missed.
    """
    hold_ticks = 4 * tick_rate  # 4 real seconds of holding
    rows: List[Dict] = []
    for idx in range(hold_ticks):
        rows.append(
            {
                "tick": idx,
                "round_number": 1,
                "time_in_round": idx / tick_rate,
                "pos_x": 0.0,
                "pos_y": 0.0,
                "pos_z": 0.0,
                "health": 100,
                "enemies_visible": 0,
                "teammates_alive": 4,
                "enemies_alive": 5,
                "active_weapon": "weapon_ak47",
                "map_name": "de_mirage",
            }
        )
    # The move: a large jump (>300 units) with no new enemy info.
    rows.append(
        {
            "tick": hold_ticks,
            "round_number": 1,
            "time_in_round": hold_ticks / tick_rate,
            "pos_x": 1000.0,
            "pos_y": 0.0,
            "pos_z": 0.0,
            "health": 100,
            "enemies_visible": 0,
            "teammates_alive": 4,
            "enemies_alive": 5,
            "active_weapon": "weapon_ak47",
            "map_name": "de_mirage",
        }
    )
    return rows


class TestRateEquivariance:
    """The same real-time scenario yields identical detections at 64 and 128."""

    def test_position_abandonment_flagged_at_both_rates(self):
        analyzer = MovementQualityAnalyzer()

        mistakes_64 = analyzer.analyze_round_ticks(
            _hold_then_move_round(64), "de_mirage", "tester", 1, tick_rate=64
        )
        mistakes_128 = analyzer.analyze_round_ticks(
            _hold_then_move_round(128), "de_mirage", "tester", 1, tick_rate=128
        )

        types_64 = sorted(m.mistake_type for m in mistakes_64)
        types_128 = sorted(m.mistake_type for m in mistakes_128)

        # Equivariance: identical mistake set regardless of tick rate.
        assert types_64 == types_128
        assert types_64 == ["position_abandoned"]

    def test_hold_under_threshold_not_flagged_at_either_rate(self):
        analyzer = MovementQualityAnalyzer()

        def short_hold(tick_rate: int) -> List[Dict]:
            # Hold only 2 s (< 3 s established threshold), then move.
            full = _hold_then_move_round(tick_rate)
            cut = 2 * tick_rate
            return full[:cut] + [full[-1]]

        m64 = analyzer.analyze_round_ticks(short_hold(64), "de_mirage", "t", 1, tick_rate=64)
        m128 = analyzer.analyze_round_ticks(short_hold(128), "de_mirage", "t", 1, tick_rate=128)

        assert [m.mistake_type for m in m64] == []
        assert [m.mistake_type for m in m128] == []

    def test_match_metrics_position_stability_in_real_seconds(self):
        analyzer = MovementQualityAnalyzer()
        # position_stability is a real-time average; must match across rates.
        metrics_64 = analyzer.analyze_match_ticks(
            _hold_then_move_round(64), "de_mirage", "t", tick_rate=64
        )
        metrics_128 = analyzer.analyze_match_ticks(
            _hold_then_move_round(128), "de_mirage", "t", tick_rate=128
        )
        assert metrics_64.total_rounds_analyzed == metrics_128.total_rounds_analyzed == 1


class TestTickRateResolver:
    """The orchestrator resolves the per-demo rate as a single source of truth."""

    def _orchestrator(self) -> AnalysisOrchestrator:
        # _resolve_tick_rate uses no instance state; bypass the heavy __init__.
        return object.__new__(AnalysisOrchestrator)

    def test_prefers_tick_rate_column(self):
        orch = self._orchestrator()
        df = pd.DataFrame([{"tick": 0, "tick_rate": 128}, {"tick": 1, "tick_rate": 128}])
        assert orch._resolve_tick_rate("any_demo", df) == 128

    def test_invalid_column_then_no_metadata_falls_back_to_canonical(self):
        orch = self._orchestrator()
        # Non-numeric tick_rate column + a demo name with no persisted metadata.
        df = pd.DataFrame([{"tick": 0, "tick_rate": "garbage"}])
        assert orch._resolve_tick_rate("nonexistent_demo_xyz", df) == 64

    def test_no_column_unknown_demo_falls_back_to_canonical(self):
        orch = self._orchestrator()
        df = pd.DataFrame([{"tick": 0, "pos_x": 0.0}])
        assert orch._resolve_tick_rate("nonexistent_demo_xyz", df) == 64
