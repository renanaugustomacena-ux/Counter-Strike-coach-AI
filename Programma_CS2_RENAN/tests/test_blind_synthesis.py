"""Regression tests for the CS2 blind-event synthesis (round_stats_builder).

Pass-2 finding: modern CS2 demos emit ZERO `player_blind` events (a CS:GO
game event), so flash_assists / utility_blind_time / utility_enemies_blinded
were 0.0 for every player of every demo — and coach_manager compared those
zeros against pro baselines. The builder now reconstructs blind events from
per-tick flash_duration transitions attributed via flashbang_detonate.
"""

import pandas as pd
import pytest

from Programma_CS2_RENAN.backend.processing.round_stats_builder import (
    _BLIND_EPSILON,
    _synthesize_blind_events_from_ticks,
)


class _FakeParser:
    """demoparser2 boundary stand-in: fixed tick/event/header payloads."""

    def __init__(self, ticks_df, events_by_name, tick_rate=64):
        self._ticks = ticks_df
        self._events = events_by_name
        self._tick_rate = tick_rate

    def parse_ticks(self, fields):
        return self._ticks

    def parse_events(self, names, **kwargs):
        name = names[0]
        df = self._events.get(name, pd.DataFrame())
        return [(name, df)]

    def parse_header(self):
        return {"tick_rate": self._tick_rate}


def _ticks(rows):
    return pd.DataFrame(rows, columns=["player_name", "tick", "flash_duration"])


def _detos(rows):
    return pd.DataFrame(rows, columns=["tick", "user_name"])


class TestBlindSynthesis:
    def test_transition_produces_attributed_event(self):
        ticks = _ticks(
            [
                ("victim", 100, 0.0),
                ("victim", 101, 0.0),
                ("victim", 102, 2.5),  # flashed here
                ("victim", 103, 2.4),
                ("thrower", 100, 0.0),
                ("thrower", 103, 0.0),
            ]
        )
        parser = _FakeParser(ticks, {"flashbang_detonate": _detos([(102, "thrower")])})
        out = _synthesize_blind_events_from_ticks(parser)
        assert len(out) == 1
        ev = out.iloc[0]
        assert ev["user_name"] == "victim"
        assert ev["attacker_name"] == "thrower"
        assert ev["blind_duration"] == pytest.approx(2.5)
        assert int(ev["tick"]) == 102

    def test_reflash_counts_as_second_event(self):
        ticks = _ticks(
            [
                ("victim", 100, 0.0),
                ("victim", 102, 2.0),  # first flash
                ("victim", 110, 1.5),  # decaying
                ("victim", 112, 3.0),  # re-flashed while still blind
                ("victim", 120, 2.0),
            ]
        )
        detos = _detos([(102, "a"), (112, "b")])
        parser = _FakeParser(ticks, {"flashbang_detonate": detos})
        out = _synthesize_blind_events_from_ticks(parser)
        assert len(out) == 2
        assert list(out["attacker_name"]) == ["a", "b"]

    def test_no_detonation_in_window_is_skipped_not_fabricated(self):
        ticks = _ticks([("victim", 100, 0.0), ("victim", 102, 2.5)])
        # detonation 500 ticks earlier — cannot be the cause
        parser = _FakeParser(ticks, {"flashbang_detonate": _detos([(-398, "x")])})
        out = _synthesize_blind_events_from_ticks(parser)
        assert out.empty, "unattributable transitions must be skipped, never guessed"

    def test_decay_and_jitter_do_not_emit_events(self):
        ticks = _ticks(
            [
                ("victim", 100, 3.0),
                ("victim", 101, 2.9),
                ("victim", 102, 2.8 + _BLIND_EPSILON / 10),  # sub-epsilon jitter
                ("victim", 103, 2.7),
            ]
        )
        parser = _FakeParser(ticks, {"flashbang_detonate": _detos([(99, "t")])})
        out = _synthesize_blind_events_from_ticks(parser)
        # first row starts already-blind (3.0 > 0 + eps) and IS attributable
        # to the tick-99 detonation; decay/jitter afterwards must not emit.
        assert len(out) == 1

    def test_no_detonations_at_all_returns_empty(self):
        ticks = _ticks([("v", 100, 0.0), ("v", 102, 2.5)])
        parser = _FakeParser(ticks, {"flashbang_detonate": pd.DataFrame()})
        assert _synthesize_blind_events_from_ticks(parser).empty
