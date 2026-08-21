"""F-0021 — flash-bait detection keys on a REAL blind signal.

CS2 demos emit no ``player_blind`` events; production tick frames carry no
``event_type`` column at all. The old detector returned the degenerate 1.0
(all-bait) whenever flashes existed without ``player_blind`` rows, and its
only real-world behavior was silent 0.0.
"""

import pandas as pd
import pytest

from Programma_CS2_RENAN.backend.analysis.deception_index import DeceptionAnalyzer

TICK_RATE = 64.0


@pytest.fixture
def analyzer():
    return DeceptionAnalyzer()


def _event_frame(rows):
    return pd.DataFrame(rows)


class TestFlashBaitSignal:
    def test_is_blinded_transitions_make_flashes_effective(self, analyzer):
        # Flash at tick 100 followed by an is_blinded=True row inside the
        # window; flash at tick 5000 with no blind follow-up = bait.
        df = _event_frame(
            [
                {"tick": 100, "event_type": "flashbang_throw", "is_blinded": False},
                {"tick": 130, "event_type": "tick", "is_blinded": True},
                {"tick": 5000, "event_type": "flashbang_throw", "is_blinded": False},
                {"tick": 5010, "event_type": "tick", "is_blinded": False},
            ]
        )
        rate = analyzer._detect_flash_baits(df, tick_rate=TICK_RATE)
        assert rate == pytest.approx(0.5)

    def test_player_blind_events_still_supported(self, analyzer):
        df = _event_frame(
            [
                {"tick": 100, "event_type": "flashbang_throw"},
                {"tick": 120, "event_type": "player_blind"},
            ]
        )
        assert analyzer._detect_flash_baits(df, tick_rate=TICK_RATE) == pytest.approx(0.0)

    def test_no_blind_signal_is_honest_dark_not_all_bait(self, analyzer):
        # Flashes present but NO blind signal of any kind (no player_blind
        # rows possible, no is_blinded column) -> 0.0, never 1.0.
        df = _event_frame(
            [
                {"tick": 100, "event_type": "flashbang_throw"},
                {"tick": 200, "event_type": "flashbang_throw"},
            ]
        )
        assert analyzer._detect_flash_baits(df, tick_rate=TICK_RATE) == 0.0

    def test_blind_signal_present_but_never_fires_is_all_bait(self, analyzer):
        # is_blinded column EXISTS (signal available) and stays False ->
        # every flash genuinely blinded nobody -> 1.0 is honest.
        df = _event_frame(
            [
                {"tick": 100, "event_type": "flashbang_throw", "is_blinded": False},
                {"tick": 130, "event_type": "tick", "is_blinded": False},
            ]
        )
        assert analyzer._detect_flash_baits(df, tick_rate=TICK_RATE) == pytest.approx(1.0)

    def test_tickstate_shaped_frame_is_dark(self, analyzer):
        # Production frame: PlayerTickState columns, no event_type at all.
        df = pd.DataFrame(
            [
                {"tick": 1, "player_name": "a", "pos_x": 0.0, "is_blinded": False},
                {"tick": 2, "player_name": "a", "pos_x": 1.0, "is_blinded": True},
            ]
        )
        assert analyzer._detect_flash_baits(df, tick_rate=TICK_RATE) == 0.0
