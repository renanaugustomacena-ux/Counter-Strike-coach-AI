"""Regression tests for CHAT-07 experience-bank dedup (AUDIT §8.7).

`ExperienceBank.retrieve_*` previously returned near-duplicate rows when
top_k semantic matches happened to share `(action, outcome, map, pro)`.
The user observed three identical "aggressive_push → traded on dust2"
rows in a single retrieval batch. `_dedup_experiences` greedily filters
those out, but falls back to spillover entries when uniques < top_k.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest


@pytest.fixture
def dedup():
    from Programma_CS2_RENAN.backend.knowledge.experience_bank import _dedup_experiences

    return _dedup_experiences


@dataclass
class _Exp:
    id: int
    action_taken: str
    outcome: str
    map_name: str
    pro_player_name: Optional[str] = None


class TestDedupExperiences:
    def test_drops_exact_duplicates(self, dedup):
        items = [
            _Exp(1, "aggressive_push", "traded", "dust2", "torzsi"),
            _Exp(2, "aggressive_push", "traded", "dust2", "torzsi"),
            _Exp(3, "aggressive_push", "traded", "dust2", "jame"),
        ]
        out = dedup(items, top_k=3)
        assert [e.id for e in out] == [1, 3, 2]  # uniques first, then spillover

    def test_keeps_distinct_action_outcome_pairs(self, dedup):
        items = [
            _Exp(1, "aggressive_push", "traded", "dust2", "torzsi"),
            _Exp(2, "entry_frag", "kill", "mirage", "donk"),
            _Exp(3, "multi_kill", "round_win", "nuke", "ZywOo"),
        ]
        out = dedup(items, top_k=3)
        assert [e.id for e in out] == [1, 2, 3]  # all unique, order preserved

    def test_top_k_caps_unique_results(self, dedup):
        items = [_Exp(i, f"a{i}", "ok", "mirage", f"p{i}") for i in range(5)]
        out = dedup(items, top_k=2)
        assert len(out) == 2
        assert [e.id for e in out] == [0, 1]

    def test_falls_back_to_spillover_when_uniques_short(self, dedup):
        # Only 2 unique tuples but caller wants 4 items
        items = [
            _Exp(1, "aggressive_push", "traded", "dust2", "torzsi"),
            _Exp(2, "aggressive_push", "traded", "dust2", "torzsi"),
            _Exp(3, "entry_frag", "kill", "mirage", "donk"),
            _Exp(4, "entry_frag", "kill", "mirage", "donk"),
        ]
        out = dedup(items, top_k=4)
        assert len(out) == 4
        # Two uniques first, then two spillover repeats
        assert [e.id for e in out] == [1, 3, 2, 4]

    def test_handles_empty_input(self, dedup):
        assert dedup([], top_k=3) == []

    def test_handles_top_k_larger_than_input(self, dedup):
        items = [_Exp(1, "a", "b", "c", "d")]
        out = dedup(items, top_k=10)
        assert out == items

    def test_distinguishes_pro_player_name(self, dedup):
        # Same action/outcome/map but different pros — keep both
        items = [
            _Exp(1, "aggressive_push", "traded", "dust2", "torzsi"),
            _Exp(2, "aggressive_push", "traded", "dust2", "jame"),
            _Exp(3, "aggressive_push", "traded", "dust2", "donk"),
        ]
        out = dedup(items, top_k=3)
        assert [e.pro_player_name for e in out] == ["torzsi", "jame", "donk"]
