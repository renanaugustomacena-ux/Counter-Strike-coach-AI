"""Regression tests for CHAT-02 third-person tutor mode (AUDIT §8.2).

Covers the deterministic 2nd-person → 3rd-person rewriter used when the
coaching dialogue injects pro-player insights in tutor mode (user has no
personal match data). Failures here mean the LLM will be re-fed fabricated
"your stats" critiques authored for a different player.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def rewrite():
    from Programma_CS2_RENAN.backend.services.coaching_dialogue import _to_third_person

    return _to_third_person


class TestThirdPersonTransform:
    """_to_third_person rewrites 2nd-person pronouns and optionally attributes."""

    def test_rewrites_you_are_to_they_are(self, rewrite):
        # "You" at sentence start → "They"; prefix attribution added.
        assert rewrite("You are 36% slower than the baseline.", "donk") == (
            "[donk] They are 36% slower than the baseline."
        )

    def test_rewrites_your_possessive(self, rewrite):
        assert rewrite("Your KAST is lagging.", "magixx") == ("[magixx] Their KAST is lagging.")

    def test_rewrites_you_were(self, rewrite):
        out = rewrite("You were exposed to multiple angles for several seconds.", "zywoo")
        assert out == "[zywoo] They were exposed to multiple angles for several seconds."

    def test_mixed_case_preserved_on_sentence_start(self, rewrite):
        out = rewrite("You should rotate earlier. Your timing is late.", "ropz")
        assert out == "[ropz] They should rotate earlier. Their timing is late."

    def test_midsentence_you_stays_lowercase(self, rewrite):
        out = rewrite("Smoke Jungle before you peek it.", "donk", attribute=False)
        # "you" mid-sentence → "they" (lowercase preserved)
        assert out == "Smoke Jungle before they peek it."

    def test_no_pronouns_only_prefix_when_attribute_true(self, rewrite):
        out = rewrite("Clutch play: prioritize the objective over the hunt.", "donk")
        assert out == "[donk] Clutch play: prioritize the objective over the hunt."

    def test_no_double_prefix_on_rerun(self, rewrite):
        first = rewrite("Your KAST is lagging.", "donk")
        second = rewrite(first, "donk")
        assert second.count("[donk]") == 1

    def test_attribute_false_strips_prefix(self, rewrite):
        out = rewrite("You are slow.", "donk", attribute=False)
        assert out == "They are slow."
        assert "[donk]" not in out

    def test_preserves_stat_numbers_and_percent(self, rewrite):
        out = rewrite("You are 36% slower, your HS drop is 12.4%.", "donk")
        assert "36%" in out and "12.4%" in out

    def test_handles_empty_string(self, rewrite):
        assert rewrite("", "donk") == "[donk] "

    def test_does_not_create_they_for_your_substrings(self, rewrite):
        # Word-boundary check: "contour" must not become "conttheir"
        out = rewrite("Contour your angle before you peek.", "donk", attribute=False)
        assert "conttheir" not in out
        assert "their angle" in out
        assert "they peek" in out


# ===========================================================================
# R4 MED (2026-07-16) — round-pattern word boundary
# ===========================================================================


class TestRoundPatternBoundary:
    """The trailing 'r' of any word used to match ("...tips foR 5 players"),
    misrouting messages to round_query — strongest-signal intent."""

    @staticmethod
    def _matches(text):
        from Programma_CS2_RENAN.backend.services.coaching_dialogue import _ROUND_PATTERN

        return _ROUND_PATTERN.search(text.lower())

    def test_word_trailing_r_does_not_match(self):
        assert self._matches("any tips for 5 players pushing B?") is None

    def test_round_forms_still_match(self):
        for text, expected in [
            ("what happened in round 5?", "5"),
            ("show me R12", "12"),
            ("rounds 5-10 were rough", "5"),
            ("round 5 to 10 analysis", "5"),
        ]:
            m = self._matches(text)
            assert m is not None, text
            assert m.group(1) == expected

    def test_range_second_group(self):
        m = self._matches("rounds 5 to 10")
        assert m.group(2) == "10"
