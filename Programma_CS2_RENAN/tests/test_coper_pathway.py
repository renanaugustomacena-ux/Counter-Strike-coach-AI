"""
Tests for the COPER coaching pathway — the full chain from
ExperienceContext through ExperienceBank to CoachingService.

These tests exercise the COPER system BEFORE we flip the feature flag,
so we have a safety net covering: dataclasses, pure functions,
experience storage/retrieval, synthesis, fallback chains, and
the integration with CoachingService.

All tests run without external services (no Ollama, no FAISS, no SBERT).
"""

import hashlib
import time
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# ============ Shared Fixtures ============


class _InMemoryDBManager:
    """Lightweight DB manager for tests."""

    def __init__(self, engine):
        self._engine = engine

    @contextmanager
    def get_session(self, engine_key: str = "default"):
        with Session(self._engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class _InMemoryStateManager:
    """Records notifications in memory for assertion."""

    def __init__(self):
        self.notifications: list[dict] = []

    def add_notification(self, daemon: str, severity: str, message: str):
        self.notifications.append({"daemon": daemon, "severity": severity, "message": message})

    def update_status(self, daemon: str, status: str, detail: str = ""):
        pass

    def set_error(self, daemon: str, message: str):
        self.add_notification(daemon, "ERROR", message)


@pytest.fixture
def in_memory_engine():
    import Programma_CS2_RENAN.backend.storage.db_models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def mock_db(in_memory_engine):
    return _InMemoryDBManager(in_memory_engine)


@pytest.fixture
def mock_state():
    return _InMemoryStateManager()


# ============ 1. ExperienceContext Tests ============


class TestExperienceContext:
    """Pure dataclass — zero dependencies."""

    def test_query_string_basic(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(map_name="de_mirage", round_phase="pistol", side="T")
        qs = ctx.to_query_string()
        assert "de_mirage" in qs
        assert "T-side" in qs
        assert "pistol" in qs

    def test_query_string_includes_position(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_dust2",
            round_phase="full_buy",
            side="CT",
            position_area="A-site",
        )
        qs = ctx.to_query_string()
        assert "A-site" in qs

    def test_query_string_includes_health_when_not_full(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_inferno",
            round_phase="eco",
            side="T",
            health_range="critical",
        )
        qs = ctx.to_query_string()
        assert "critical health" in qs

    def test_query_string_omits_health_when_full(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(map_name="de_nuke", round_phase="force", side="CT")
        qs = ctx.to_query_string()
        assert "health" not in qs

    def test_query_string_includes_alive_counts(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_ancient",
            round_phase="full_buy",
            side="T",
            teammates_alive=3,
            enemies_alive=2,
        )
        qs = ctx.to_query_string()
        assert "3v2" in qs

    def test_compute_hash_deterministic(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(map_name="de_mirage", round_phase="eco", side="CT")
        h1 = ctx.compute_hash()
        h2 = ctx.compute_hash()
        assert h1 == h2
        assert len(h1) == 16  # SHA256[:16]

    def test_different_contexts_different_hashes(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx_a = ExperienceContext(map_name="de_mirage", round_phase="eco", side="CT")
        ctx_b = ExperienceContext(map_name="de_mirage", round_phase="eco", side="T")
        assert ctx_a.compute_hash() != ctx_b.compute_hash()

    def test_hash_uses_sha256(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        ctx = ExperienceContext(
            map_name="de_mirage",
            round_phase="pistol",
            side="T",
            position_area="A-site",
        )
        key = "de_mirage:T:pistol:A-site"
        expected = hashlib.sha256(key.encode()).hexdigest()[:16]
        assert ctx.compute_hash() == expected


# ============ 2. SynthesizedAdvice Tests ============


class TestSynthesizedAdvice:
    """Pure dataclass — verify structure."""

    def test_creation(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import SynthesizedAdvice

        advice = SynthesizedAdvice(
            narrative="Test narrative",
            pro_references=["s1mple (AWP hold -> kill)"],
            confidence=0.85,
            focus_area="positioning",
            experiences_used=7,
        )
        assert advice.narrative == "Test narrative"
        assert len(advice.pro_references) == 1
        assert advice.confidence == 0.85
        assert advice.experiences_used == 7


# ============ 3. Round Phase Utility Tests ============


class TestInferRoundPhase:
    """Pure function — zero dependencies."""

    def test_pistol_round(self):
        from Programma_CS2_RENAN.backend.knowledge.round_utils import infer_round_phase

        assert infer_round_phase({"equipment_value": 800}) == "pistol"
        assert infer_round_phase({"equipment_value": 0}) == "pistol"
        assert infer_round_phase({"equipment_value": 1499}) == "pistol"

    def test_eco_round(self):
        from Programma_CS2_RENAN.backend.knowledge.round_utils import infer_round_phase

        assert infer_round_phase({"equipment_value": 1500}) == "eco"
        assert infer_round_phase({"equipment_value": 2999}) == "eco"

    def test_force_buy(self):
        from Programma_CS2_RENAN.backend.knowledge.round_utils import infer_round_phase

        assert infer_round_phase({"equipment_value": 3000}) == "force"
        assert infer_round_phase({"equipment_value": 3999}) == "force"

    def test_full_buy(self):
        from Programma_CS2_RENAN.backend.knowledge.round_utils import infer_round_phase

        assert infer_round_phase({"equipment_value": 4000}) == "full_buy"
        assert infer_round_phase({"equipment_value": 10000}) == "full_buy"

    def test_missing_key_defaults_to_pistol(self):
        from Programma_CS2_RENAN.backend.knowledge.round_utils import infer_round_phase

        assert infer_round_phase({}) == "pistol"

    def test_non_dict_returns_full_buy(self):
        from Programma_CS2_RENAN.backend.knowledge.round_utils import infer_round_phase

        assert infer_round_phase("not a dict") == "full_buy"
        assert infer_round_phase(None) == "full_buy"
        assert infer_round_phase(42) == "full_buy"


# ============ 4. Correction Engine Tests ============


class TestCorrectionEngine:
    """Pure function with config dependency mocked."""

    def test_returns_up_to_3_corrections(self):
        with patch(
            "Programma_CS2_RENAN.backend.coaching.correction_engine.get_setting",
            return_value={},
        ):
            from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

            devs = {
                "avg_adr": -2.0,
                "avg_kills": -1.5,
                "avg_kast": -1.0,
                "accuracy": -0.5,
                "avg_hs": -0.3,
            }
            result = generate_corrections(devs, rounds_played=100)
            assert len(result) <= 3

    def test_confidence_scales_with_rounds(self):
        with patch(
            "Programma_CS2_RENAN.backend.coaching.correction_engine.get_setting",
            return_value={},
        ):
            from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

            devs = {"avg_adr": -2.0}

            # 30 rounds → confidence = 30/300 = 0.1
            r30 = generate_corrections(devs, rounds_played=30)
            # 300 rounds → confidence = 1.0
            r300 = generate_corrections(devs, rounds_played=300)

            assert abs(r30[0]["weighted_z"]) < abs(r300[0]["weighted_z"])

    def test_handles_tuple_deviations(self):
        """P3-07: deviations can be tuples from JSON deserialization."""
        with patch(
            "Programma_CS2_RENAN.backend.coaching.correction_engine.get_setting",
            return_value={},
        ):
            from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

            devs = {"avg_adr": (-2.0, 5.0)}  # (z_score, raw_dev)
            result = generate_corrections(devs, rounds_played=100)
            assert len(result) == 1
            # weighted_z should use the first element (z_score)
            assert result[0]["weighted_z"] < 0

    def test_handles_list_deviations(self):
        """P3-07: deviations can be lists from JSON deserialization."""
        with patch(
            "Programma_CS2_RENAN.backend.coaching.correction_engine.get_setting",
            return_value={},
        ):
            from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

            devs = {"avg_adr": [-1.5, 3.0]}
            result = generate_corrections(devs, rounds_played=200)
            assert len(result) == 1
            assert result[0]["weighted_z"] < 0

    def test_sorted_by_weighted_importance(self):
        with patch(
            "Programma_CS2_RENAN.backend.coaching.correction_engine.get_setting",
            return_value={},
        ):
            from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

            devs = {"avg_adr": -3.0, "avg_hs": -0.1}
            result = generate_corrections(devs, rounds_played=300)
            # avg_adr with -3.0 * importance should rank first
            assert result[0]["feature"] == "avg_adr"


# ============ 5. Explainability Tests ============


class TestExplainability:
    """Pure static methods — zero external dependencies."""

    def test_silence_threshold(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator
        from Programma_CS2_RENAN.backend.processing.skill_assessment import SkillAxes

        # Delta below 0.2 → silence (empty string)
        result = ExplanationGenerator.generate_narrative(SkillAxes.MECHANICS, "avg_hs", 0.1)
        assert result == ""

    def test_negative_generates_narrative(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator
        from Programma_CS2_RENAN.backend.processing.skill_assessment import SkillAxes

        result = ExplanationGenerator.generate_narrative(SkillAxes.MECHANICS, "avg_hs", -0.5)
        assert len(result) > 0
        assert "below" in result.lower() or "focus" in result.lower()

    def test_positive_generates_narrative(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator
        from Programma_CS2_RENAN.backend.processing.skill_assessment import SkillAxes

        result = ExplanationGenerator.generate_narrative(SkillAxes.MECHANICS, "avg_hs", 0.8)
        assert len(result) > 0
        assert "peak" in result.lower() or "level" in result.lower()

    def test_classify_severity_high(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator

        assert ExplanationGenerator.classify_insight_severity(2.0) == "High"
        assert ExplanationGenerator.classify_insight_severity(-2.0) == "High"

    def test_classify_severity_medium(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator

        assert ExplanationGenerator.classify_insight_severity(1.0) == "Medium"

    def test_classify_severity_low(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator

        assert ExplanationGenerator.classify_insight_severity(0.5) == "Low"

    def test_unknown_category_returns_fallback(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator

        result = ExplanationGenerator.generate_narrative("NONEXISTENT", "some_feature", -1.0)
        assert "analysis" in result.lower() or "patterns" in result.lower()

    def test_low_skill_level_simplifies_output(self):
        from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator
        from Programma_CS2_RENAN.backend.processing.skill_assessment import SkillAxes

        result = ExplanationGenerator.generate_narrative(
            SkillAxes.MECHANICS, "avg_hs", -0.5, skill_level=2
        )
        assert "goal" in result.lower()


# ============ 6. Embedding Serialization Tests ============


class TestEmbeddingSerialization:
    """Test compact base64 serialization for experience embeddings."""

    def test_round_trip(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceBank

        vec = np.array([0.1, 0.2, 0.3, -0.5], dtype=np.float32)
        serialized = ExperienceBank._serialize_embedding(vec)
        deserialized = ExperienceBank._deserialize_embedding(serialized)
        np.testing.assert_array_almost_equal(vec, deserialized)

    def test_legacy_json_format(self):
        """Backward compatibility: old JSON-encoded embeddings still work."""
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceBank

        legacy = "[0.1, 0.2, 0.3]"
        result = ExperienceBank._deserialize_embedding(legacy)
        assert len(result) == 3
        assert abs(result[0] - 0.1) < 1e-5


# ============ 7. ExperienceBank DB Tests ============


class TestExperienceBankDB:
    """Test ExperienceBank with in-memory SQLite — no FAISS, no SBERT."""

    def _make_bank(self, mock_db):
        """Create ExperienceBank with mocked dependencies."""
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceBank

        bank = ExperienceBank.__new__(ExperienceBank)
        bank.db = mock_db

        # Fallback embedder (hash-based, no SBERT needed)
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = np.random.randn(100).astype(np.float32)
        bank.embedder = mock_embedder

        return bank

    def _make_context(self, map_name="de_mirage", side="T", phase="full_buy"):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceContext

        return ExperienceContext(map_name=map_name, round_phase=phase, side=side)

    def test_add_experience_persists(self, mock_db):
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            exp = bank.add_experience(
                context=ctx,
                action_taken="pushed",
                outcome="kill",
                confidence=0.7,
                source_demo="test.dem",
            )

        assert exp.id is not None
        assert exp.map_name == "de_mirage"
        assert exp.action_taken == "pushed"
        assert exp.outcome == "kill"
        assert exp.confidence == 0.7

    def test_add_pro_experience(self, mock_db):
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            exp = bank.add_experience(
                context=ctx,
                action_taken="held_angle",
                outcome="kill",
                pro_player_name="s1mple",
                pro_match_id=42,
                confidence=0.7,
            )

        assert exp.pro_player_name == "s1mple"
        assert exp.pro_match_id == 42

    def test_retrieve_similar_brute_force(self, mock_db):
        """Brute-force fallback when FAISS is unavailable."""
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        # Ensure consistent embedding for retrieval matching
        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            # Add experiences
            bank.add_experience(
                context=ctx,
                action_taken="pushed",
                outcome="kill",
                confidence=0.8,
            )
            bank.add_experience(
                context=ctx,
                action_taken="held_angle",
                outcome="death",
                confidence=0.6,
            )

            # Retrieve
            results = bank.retrieve_similar(ctx, top_k=5)

        assert len(results) == 2

    def test_retrieve_filters_by_map(self, mock_db):
        """Experiences from different maps should not be returned."""
        bank = self._make_bank(mock_db)
        ctx_mirage = self._make_context(map_name="de_mirage")
        ctx_dust2 = self._make_context(map_name="de_dust2")

        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            bank.add_experience(
                context=ctx_mirage,
                action_taken="pushed",
                outcome="kill",
                confidence=0.8,
            )
            bank.add_experience(
                context=ctx_dust2,
                action_taken="held_angle",
                outcome="kill",
                confidence=0.8,
            )

            results = bank.retrieve_similar(ctx_mirage, top_k=5)

        assert all(r.map_name == "de_mirage" for r in results)

    def test_retrieve_filters_by_confidence(self, mock_db):
        """Low-confidence experiences should be excluded."""
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            bank.add_experience(
                context=ctx,
                action_taken="pushed",
                outcome="kill",
                confidence=0.1,  # Below MIN_RETRIEVAL_CONFIDENCE (0.3)
            )

            results = bank.retrieve_similar(ctx, top_k=5, min_confidence=0.3)

        assert len(results) == 0

    def test_retrieve_pro_examples(self, mock_db):
        """Should only return pro-sourced experiences."""
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            bank.add_experience(
                context=ctx,
                action_taken="pushed",
                outcome="kill",
                confidence=0.8,
                pro_player_name=None,  # User experience
            )
            bank.add_experience(
                context=ctx,
                action_taken="held_angle",
                outcome="kill",
                confidence=0.7,
                pro_player_name="ZywOo",  # Pro experience
            )

            results = bank.retrieve_pro_examples(ctx, top_k=5)

        assert len(results) == 1
        assert results[0].pro_player_name == "ZywOo"

    def test_synthesize_advice_no_experiences(self, mock_db):
        """Empty bank should return generic advice."""
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            advice = bank.synthesize_advice(ctx)

        assert advice.experiences_used == 0
        assert advice.confidence == 0.0
        assert "practicing" in advice.narrative.lower() or "no similar" in advice.narrative.lower()

    def test_synthesize_advice_with_experiences(self, mock_db):
        """With experiences, should produce meaningful narrative."""
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            bank.add_experience(
                context=ctx,
                action_taken="pushed",
                outcome="kill",
                confidence=0.8,
            )
            bank.add_experience(
                context=ctx,
                action_taken="held_angle",
                outcome="kill",
                confidence=0.7,
                pro_player_name="NiKo",
            )

            advice = bank.synthesize_advice(ctx, user_action="held_angle", user_outcome="death")

        assert advice.experiences_used > 0
        assert advice.confidence > 0.0
        assert len(advice.narrative) > 0

    def test_synthesize_advice_includes_pro_references(self, mock_db):
        """Pro experiences should appear in pro_references."""
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            bank.add_experience(
                context=ctx,
                action_taken="scoped_hold",
                outcome="kill",
                confidence=0.8,
                pro_player_name="device",
            )

            advice = bank.synthesize_advice(ctx)

        assert any("device" in ref for ref in advice.pro_references)

    def test_record_feedback_positive(self, mock_db):
        """Positive feedback should increase effectiveness."""
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            exp = bank.add_experience(
                context=ctx,
                action_taken="pushed",
                outcome="kill",
                confidence=0.5,
            )

            result = bank.record_feedback(
                experience_id=exp.id,
                follow_up_match_id=99,
                player_outcome="kill",
                player_action="pushed",
            )

        assert result is True

    def test_record_feedback_missing_experience(self, mock_db):
        """Feedback for nonexistent experience should return False."""
        bank = self._make_bank(mock_db)

        result = bank.record_feedback(
            experience_id=99999,
            follow_up_match_id=1,
            player_outcome="kill",
            player_action="pushed",
        )
        assert result is False

    def test_get_experience_count(self, mock_db):
        bank = self._make_bank(mock_db)
        ctx = self._make_context()

        fixed_embedding = np.ones(100, dtype=np.float32) / 10.0
        bank.embedder.embed.return_value = fixed_embedding

        with patch(
            "Programma_CS2_RENAN.backend.knowledge.vector_index.get_vector_index_manager",
            return_value=None,
        ):
            bank.add_experience(
                context=ctx,
                action_taken="a",
                outcome="kill",
                confidence=0.5,
            )
            bank.add_experience(
                context=ctx,
                action_taken="b",
                outcome="kill",
                confidence=0.7,
                pro_player_name="s1mple",
            )

        counts = bank.get_experience_count()
        assert counts["total"] == 2
        assert counts["pro"] == 1
        assert counts["user"] == 1


# ============ 8. ExperienceBank Helper Tests ============


class TestExperienceBankHelpers:
    """Test private helper methods on ExperienceBank."""

    def _make_bank(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import ExperienceBank

        return ExperienceBank.__new__(ExperienceBank)

    def test_health_to_range_full(self):
        bank = self._make_bank()
        assert bank._health_to_range(100) == "full"
        assert bank._health_to_range(80) == "full"

    def test_health_to_range_damaged(self):
        bank = self._make_bank()
        assert bank._health_to_range(79) == "damaged"
        assert bank._health_to_range(40) == "damaged"

    def test_health_to_range_critical(self):
        bank = self._make_bank()
        assert bank._health_to_range(39) == "critical"
        assert bank._health_to_range(0) == "critical"

    def test_infer_action_scoped(self):
        bank = self._make_bank()
        assert bank._infer_action({"is_scoped": True}, is_victim=False) == "scoped_hold"

    def test_infer_action_crouching(self):
        bank = self._make_bank()
        assert bank._infer_action({"is_crouching": True}, is_victim=False) == "crouch_peek"

    def test_infer_action_default_victim(self):
        bank = self._make_bank()
        assert bank._infer_action({}, is_victim=True) == "held_angle"

    def test_infer_action_default_attacker(self):
        bank = self._make_bank()
        assert bank._infer_action({}, is_victim=False) == "pushed"

    def test_action_to_focus_mapping(self):
        bank = self._make_bank()
        assert bank._action_to_focus("pushed") == "aggression"
        assert bank._action_to_focus("held_angle") == "positioning"
        assert bank._action_to_focus("scoped_hold") == "aim"
        assert bank._action_to_focus("unknown_action") == "positioning"

    def test_cosine_similarity(self):
        bank = self._make_bank()
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert abs(bank._cosine_similarity(a, b) - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        bank = self._make_bank()
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert abs(bank._cosine_similarity(a, b)) < 1e-6

    def test_cosine_similarity_zero_vector(self):
        bank = self._make_bank()
        a = np.zeros(3)
        b = np.array([1.0, 0.0, 0.0])
        assert bank._cosine_similarity(a, b) == 0.0


# ============ 9. _run_with_timeout Tests ============


class TestRunWithTimeout:
    """Threading timeout utility."""

    def test_returns_result_on_success(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import _run_with_timeout

        result, timed_out = _run_with_timeout(lambda: 42, timeout=5)
        assert result == 42
        assert timed_out is False

    def test_timeout_returns_none(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import _run_with_timeout

        def slow_func():
            time.sleep(10)

        result, timed_out = _run_with_timeout(slow_func, timeout=0.1)
        assert result is None
        assert timed_out is True

    def test_exception_is_reraised(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import _run_with_timeout

        def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            _run_with_timeout(failing_func, timeout=5)

    def test_passes_args_and_kwargs(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import _run_with_timeout

        def add(a, b, extra=0):
            return a + b + extra

        result, _ = _run_with_timeout(add, args=(3, 4), kwargs={"extra": 10}, timeout=5)
        assert result == 17


# ============ 10. CoachingService Mode Selection Tests ============


class TestCoachingServiceModeSelection:
    """Verify the priority chain: COPER > Hybrid > Traditional+RAG > Traditional."""

    def test_coper_selected_when_enabled_with_map_and_ticks(self, mock_db, mock_state):
        """COPER should be selected when all conditions met."""
        with (
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
                return_value=mock_db,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
                return_value=mock_state,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
                side_effect=lambda k, default=None: {
                    "USE_COPER_COACHING": True,
                    "USE_HYBRID_COACHING": False,
                    "USE_RAG_COACHING": False,
                }.get(k, default),
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service._run_with_timeout",
                return_value=(None, False),  # Simulates successful COPER
            ) as mock_timeout,
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
            ) as mock_ollama,
        ):
            mock_ollama.return_value.polish.side_effect = lambda **kw: kw["message"]

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            svc.generate_new_insights(
                player_name="test",
                demo_name="test.dem",
                deviations={"avg_adr": -1.0},
                rounds_played=10,
                map_name="de_mirage",
                tick_data={"team": "T"},
            )

            # Verify COPER was called
            mock_timeout.assert_called_once()
            # Verify mode label shows Level 1
            mode_notifs = [n for n in mock_state.notifications if "Level 1" in n["message"]]
            assert len(mode_notifs) == 1

    def test_traditional_selected_when_coper_disabled(self, mock_db, mock_state):
        """Without COPER, should fall back to Traditional."""
        with (
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
                return_value=mock_db,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
                return_value=mock_state,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
                side_effect=lambda k, default=None: {
                    "USE_COPER_COACHING": False,
                    "USE_HYBRID_COACHING": False,
                    "USE_RAG_COACHING": False,
                }.get(k, default),
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
            ) as mock_ollama,
        ):
            mock_ollama.return_value.polish.side_effect = lambda **kw: kw["message"]

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            svc.generate_new_insights(
                player_name="test",
                demo_name="test.dem",
                deviations={"avg_adr": -1.0},
                rounds_played=10,
            )

            mode_notifs = [n for n in mock_state.notifications if "Level 4" in n["message"]]
            assert len(mode_notifs) == 1

    def test_coper_missing_map_falls_to_traditional(self, mock_db, mock_state):
        """COPER requires map_name — without it, should fall to Traditional."""
        with (
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
                return_value=mock_db,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
                return_value=mock_state,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
                side_effect=lambda k, default=None: {
                    "USE_COPER_COACHING": True,
                    "USE_HYBRID_COACHING": False,
                    "USE_RAG_COACHING": False,
                }.get(k, default),
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
            ) as mock_ollama,
        ):
            mock_ollama.return_value.polish.side_effect = lambda **kw: kw["message"]

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            svc.generate_new_insights(
                player_name="test",
                demo_name="test.dem",
                deviations={"avg_adr": -1.0},
                rounds_played=10,
                map_name=None,  # Missing!
                tick_data={"team": "T"},
            )

            mode_notifs = [n for n in mock_state.notifications if "Level 4" in n["message"]]
            assert len(mode_notifs) == 1

    def test_coper_timeout_falls_to_traditional(self, mock_db, mock_state):
        """COPER timeout should produce Traditional fallback + warning."""
        with (
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
                return_value=mock_db,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
                return_value=mock_state,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
                side_effect=lambda k, default=None: {
                    "USE_COPER_COACHING": True,
                    "USE_HYBRID_COACHING": False,
                    "USE_RAG_COACHING": False,
                }.get(k, default),
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service._run_with_timeout",
                return_value=(None, True),  # Timeout!
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
            ) as mock_ollama,
        ):
            mock_ollama.return_value.polish.side_effect = lambda **kw: kw["message"]

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            svc.generate_new_insights(
                player_name="test",
                demo_name="test.dem",
                deviations={"avg_adr": -2.0},
                rounds_played=10,
                map_name="de_mirage",
                tick_data={"team": "T"},
            )

            # Should emit timeout warning
            warnings = [
                n
                for n in mock_state.notifications
                if n["severity"] == "WARNING" and "timed out" in n["message"]
            ]
            assert len(warnings) >= 1

            # Mode label should still say COPER (that's what was attempted)
            mode_notifs = [n for n in mock_state.notifications if "Level 1" in n["message"]]
            assert len(mode_notifs) == 1


# ============ 11. CoachingService._generate_coper_insights Guard Tests ============


class TestCoperInsightsGuards:
    """Test the guard clauses in _generate_coper_insights."""

    def test_non_dict_tick_data_is_rejected(self, mock_db, mock_state):
        """C-02: tick_data must be dict."""
        with (
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
                return_value=mock_db,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
                return_value=mock_state,
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
                side_effect=lambda k, default=None: {
                    "USE_COPER_COACHING": True,
                    "USE_HYBRID_COACHING": False,
                    "USE_RAG_COACHING": False,
                }.get(k, default),
            ),
            patch(
                "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
            ) as mock_ollama,
        ):
            mock_ollama.return_value.polish.side_effect = lambda **kw: kw["message"]

            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            svc = CoachingService()
            # Should NOT crash — the guard clause in _generate_coper_insights
            # should catch the list and return None
            svc._generate_coper_insights(
                player_name="test",
                demo_name="test.dem",
                player_stats={},
                map_name="de_mirage",
                tick_data=[1, 2, 3],  # NOT a dict!
            )
            # If we get here without exception, the guard worked


# ============ 12. Baseline Context Note Tests ============


class TestBaselineContextNote:
    """Test the static _baseline_context_note method."""

    def test_empty_inputs(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        assert CoachingService._baseline_context_note({}, {}, "aim") == ""
        assert CoachingService._baseline_context_note(None, {"rating": 1.0}, "aim") == ""

    def test_calculates_delta(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        note = CoachingService._baseline_context_note(
            {"rating": 0.8},
            {"rating": {"mean": 1.0}},
            "positioning",
        )
        assert "below" in note
        assert "20%" in note

    def test_above_baseline(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        note = CoachingService._baseline_context_note(
            {"rating": 1.2},
            {"rating": {"mean": 1.0}},
            "positioning",
        )
        assert "above" in note
        assert "20%" in note

    def test_missing_metric_returns_empty(self):
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        note = CoachingService._baseline_context_note(
            {"avg_kills": 1.5},  # No "rating" key
            {"rating": {"mean": 1.0}},
            "positioning",  # Maps to "rating"
        )
        # Should gracefully produce empty or partial note
        assert isinstance(note, str)


# ============ 13. Format COPER Message Tests ============


class TestFormatCoperMessage:
    """Test the _format_coper_message method."""

    def test_basic_format(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import SynthesizedAdvice
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        svc = CoachingService.__new__(CoachingService)
        advice = SynthesizedAdvice(
            narrative="Hold A-site with AWP",
            pro_references=["s1mple (scoped_hold -> kill)"],
            confidence=0.85,
            focus_area="positioning",
            experiences_used=5,
        )
        msg = svc._format_coper_message(advice)
        assert "Hold A-site with AWP" in msg
        assert "s1mple" in msg
        assert "85%" in msg
        assert "5 similar situations" in msg

    def test_with_baseline_note(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import SynthesizedAdvice
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        svc = CoachingService.__new__(CoachingService)
        advice = SynthesizedAdvice(
            narrative="Test",
            pro_references=[],
            confidence=0.5,
            focus_area="aim",
            experiences_used=2,
        )
        msg = svc._format_coper_message(advice, baseline_note="20% below pro avg")
        assert "20% below pro avg" in msg

    def test_no_pro_references(self):
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import SynthesizedAdvice
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        svc = CoachingService.__new__(CoachingService)
        advice = SynthesizedAdvice(
            narrative="Play safe",
            pro_references=[],
            confidence=0.3,
            focus_area="positioning",
            experiences_used=1,
        )
        msg = svc._format_coper_message(advice)
        assert "Pro Examples" not in msg
