"""Root-tree tests for tools/coach_answer_eval.py (GAP-15).

Covers the pure scoring layer only — no DB, no LLM: normalization of
LLM typography (Unicode dashes/NBSP), token-coverage fact matching for
paraphrased demo names, and the three check modes (all / any / cluster).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from coach_answer_eval import Fixture, _fact_present, _normalize, score_answer


class TestNormalize:
    def test_unicode_dashes_folded(self):
        assert _normalize("faze‑vs–spirit") == "faze-vs-spirit"

    def test_nbsp_folded_and_lowercased(self):
        assert _normalize("B8 MOUZ") == "b8 mouz"


class TestFactPresent:
    def test_exact_substring(self):
        assert _fact_present("spirit-vs-faze-m2-nuke", "... spirit-vs-faze-m2-nuke ...")

    def test_unicode_typography_still_matches(self):
        answer = _normalize("The match spirit‑vs‑faze‑m2‑nuke was tense")
        assert _fact_present("spirit-vs-faze-m2-nuke", answer)

    def test_paraphrase_via_token_coverage(self):
        answer = _normalize(
            "Match chosen: cs asia championships 2026 - B8 versus MOUZ on ancient (map 2)"
        )
        assert _fact_present("cs-asia-championships-2026__b8-vs-mouz-m2-ancient", answer)

    def test_unrelated_answer_rejected(self):
        assert not _fact_present(
            "cs-asia-championships-2026__b8-vs-mouz-m2-ancient",
            _normalize("navi beat vitality on inferno"),
        )


class TestScoreAnswer:
    def test_all_mode_fractional(self):
        fx = Fixture("f1", "player_stats", "q", ["donk", "spirit-vs-faze-m1-mirage"])
        res = score_answer(fx, "donk topped the scoreboard.")
        assert res.score == 0.5
        assert res.facts_found == ["donk"]

    def test_any_mode_binary(self):
        fx = Fixture("f2", "free", "q", ["alpha", "beta"], check="any")
        assert score_answer(fx, "nothing relevant").score == 0.0
        assert score_answer(fx, "beta appears").score == 1.0

    def test_cluster_mode_requires_three_players(self):
        fx = Fixture(
            "f3",
            "free_choice",
            "q",
            ["demo-a|p1|p2|p3|p4", "demo-b|q1|q2|q3"],
            check="cluster",
        )
        assert score_answer(fx, "p1 did a thing with p2").score == 0.0
        hit = score_answer(fx, "p1 and p2 traded while p3 lurked")
        assert hit.score == 1.0
        assert hit.facts_found[0] == "demo-a"
