"""
Tests for experience_bank.py — Tier 3: Experience Bank logic.

Verifies:
1. ExperienceContext data structure
2. Context hashing is deterministic
3. SynthesizedAdvice data structure
4. Query string generation
"""

import pytest


class TestExperienceContext:
    """Verify ExperienceContext data structure and methods."""

    def test_context_creation(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_mirage",
            round_phase="full_buy",
            side="CT",
            position_area="A-site",
            health_range="full",
            teammates_alive=4,
            enemies_alive=3,
        )
        assert ctx.map_name == "de_mirage"
        assert ctx.side == "CT"
        assert ctx.teammates_alive == 4

    def test_context_hash_deterministic(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx1 = ExperienceContext(
            map_name="de_mirage", round_phase="full_buy", side="CT"
        )
        ctx2 = ExperienceContext(
            map_name="de_mirage", round_phase="full_buy", side="CT"
        )
        assert ctx1.compute_hash() == ctx2.compute_hash(), (
            "Same context should produce same hash"
        )

    def test_different_context_different_hash(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx1 = ExperienceContext(
            map_name="de_mirage", round_phase="full_buy", side="CT"
        )
        ctx2 = ExperienceContext(
            map_name="de_dust2", round_phase="eco", side="T"
        )
        assert ctx1.compute_hash() != ctx2.compute_hash(), (
            "Different contexts should produce different hashes"
        )

    def test_query_string_contains_key_info(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_inferno",
            round_phase="eco",
            side="T",
            position_area="Banana",
            health_range="damaged",
            teammates_alive=3,
            enemies_alive=5,
        )
        query = ctx.to_query_string()

        assert "de_inferno" in query
        assert "T-side" in query
        assert "eco" in query
        assert "Banana" in query
        assert "damaged" in query
        assert "3v5" in query

    def test_query_string_omits_defaults(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_mirage",
            round_phase="full_buy",
            side="CT",
            health_range="full",  # default — should not appear in query
        )
        query = ctx.to_query_string()
        assert "full health" not in query, (
            "Default health_range ('full') should not appear in query string"
        )

    def test_context_defaults(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_mirage", round_phase="full_buy", side="CT"
        )
        assert ctx.position_area is None
        assert ctx.health_range == "full"
        assert ctx.equipment_tier == "full"
        assert ctx.teammates_alive == 5
        assert ctx.enemies_alive == 5


class TestSynthesizedAdvice:
    """Verify SynthesizedAdvice data structure."""

    def test_advice_creation(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import SynthesizedAdvice

        advice = SynthesizedAdvice(
            narrative="You should use utility here",
            pro_references=["s1mple", "NiKo"],
            confidence=0.85,
            focus_area="utility",
            experiences_used=5,
        )
        assert advice.confidence == 0.85
        assert advice.focus_area == "utility"
        assert len(advice.pro_references) == 2
        assert advice.experiences_used == 5

    def test_advice_confidence_range(self):
        """Confidence should be between 0 and 1."""
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import SynthesizedAdvice

        advice = SynthesizedAdvice(
            narrative="test",
            pro_references=[],
            confidence=0.5,
            focus_area="aim",
            experiences_used=0,
        )
        assert 0.0 <= advice.confidence <= 1.0
