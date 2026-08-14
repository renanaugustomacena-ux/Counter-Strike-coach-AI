"""F-0016 regression: round_end winner normalizes every known dtype shape
to CT/T. The registry documents `winner: int (team_num 2/3)`; the old
str()-cast compared "3".upper() == "CT" — never true — so round_won was
silently always-False on int-emitting demos."""

import pandas as pd

from Programma_CS2_RENAN.backend.processing.round_stats_builder import (
    _build_round_boundaries,
    _normalize_winner,
)


class TestNormalizeWinner:
    def test_registry_int_dtype(self):
        assert _normalize_winner(3) == "CT"
        assert _normalize_winner(2) == "T"
        assert _normalize_winner(3.0) == "CT"

    def test_string_shapes(self):
        assert _normalize_winner("CT") == "CT"
        assert _normalize_winner("terrorist") == "T"
        assert _normalize_winner(" Counter-Terrorist ") == "CT"
        assert _normalize_winner("3") == "CT"

    def test_unknown_and_missing(self):
        assert _normalize_winner(None) is None
        assert _normalize_winner("draw") is None
        assert _normalize_winner(float("nan")) is None


def test_boundaries_carry_normalized_winner():
    df = pd.DataFrame({"tick": [1000, 2000], "winner": [3, 2]})
    bounds = _build_round_boundaries(df)
    assert [b["winner"] for b in bounds] == ["CT", "T"]
