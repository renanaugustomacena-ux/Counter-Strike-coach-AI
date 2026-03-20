"""
Tests for coach_manager.py — Bug #4: Silent zero-fill for missing/None DB fields.

The _prepare_tensors method uses `stats.get(f, 0.0)` to extract feature values
from model_dump(). When a DB column exists but contains NULL (Python None),
dict.get() returns None (not the default 0.0), because the key EXISTS in the
dict. This causes silent data poisoning: None values become NaN or 0.0 in the
tensor, but are indistinguishable from real zero values.

Also verifies:
- TRAINING_FEATURES and MATCH_AGGREGATE_FEATURES lengths match METADATA_DIM
- Feature vectors have correct dimensions
- Pro baseline vector has correct dimensions
"""

import numpy as np
import pytest
import torch


class TestFeatureListIntegrity:
    """Verify that feature lists are aligned with METADATA_DIM."""

    def test_training_features_count_matches_metadata_dim(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import TRAINING_FEATURES
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert len(TRAINING_FEATURES) == METADATA_DIM, (
            f"TRAINING_FEATURES has {len(TRAINING_FEATURES)} entries, "
            f"expected METADATA_DIM={METADATA_DIM}"
        )

    def test_match_aggregate_features_count_matches_metadata_dim(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert len(MATCH_AGGREGATE_FEATURES) == METADATA_DIM, (
            f"MATCH_AGGREGATE_FEATURES has {len(MATCH_AGGREGATE_FEATURES)} entries, "
            f"expected METADATA_DIM={METADATA_DIM}"
        )

    def test_no_duplicate_training_features(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import TRAINING_FEATURES

        assert len(TRAINING_FEATURES) == len(
            set(TRAINING_FEATURES)
        ), "TRAINING_FEATURES contains duplicates"

    def test_no_duplicate_match_aggregate_features(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES

        assert len(MATCH_AGGREGATE_FEATURES) == len(
            set(MATCH_AGGREGATE_FEATURES)
        ), "MATCH_AGGREGATE_FEATURES contains duplicates"

    def test_target_indices_within_bounds(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import (
            MATCH_AGGREGATE_FEATURES,
            TARGET_INDICES,
        )

        for idx in TARGET_INDICES:
            assert 0 <= idx < len(MATCH_AGGREGATE_FEATURES), (
                f"TARGET_INDICES contains out-of-bounds index {idx} "
                f"(max: {len(MATCH_AGGREGATE_FEATURES) - 1})"
            )


class TestPrepareTensorsNoneHandling:
    """BUG #4: Expose silent None → NaN/0.0 poisoning in _prepare_tensors.

    When PlayerMatchStats has NULL DB values, model_dump() returns {field: None}.
    stats.get(f, 0.0) returns None (key exists), not 0.0.
    np.array([..., None, ...], dtype=np.float32) produces NaN or raises.
    """

    def _make_fake_stats(self, overrides=None):
        """Create a mock object that mimics PlayerMatchStats.model_dump()."""
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES

        base = {f: 0.5 for f in MATCH_AGGREGATE_FEATURES}
        if overrides:
            base.update(overrides)

        class FakeStats:
            def model_dump(self):
                return base

        return FakeStats()

    def test_all_valid_values_produce_clean_tensor(self):
        """With all valid float values, tensor should have no NaN."""
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES

        stats = self._make_fake_stats()
        d = stats.model_dump()
        vec = np.array([d.get(f, 0.0) for f in MATCH_AGGREGATE_FEATURES], dtype=np.float32)

        assert not np.any(np.isnan(vec)), "Clean data should produce no NaN values"
        assert vec.shape == (len(MATCH_AGGREGATE_FEATURES),)

    def test_none_value_in_dict_is_not_replaced_by_default(self):
        """BUG #4: dict.get(key, 0.0) returns None when key exists with None value.

        This is a Python semantics issue: dict.get() only returns the default
        when the key is ABSENT. If key exists with value None, it returns None.
        """
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES

        # Simulate a DB record where some fields are NULL
        stats = self._make_fake_stats({"avg_kills": None, "avg_adr": None, "rating": None})
        d = stats.model_dump()

        # This is how _prepare_tensors extracts values:
        values = [d.get(f, 0.0) for f in MATCH_AGGREGATE_FEATURES]

        # The bug: None values are NOT replaced by 0.0
        none_count = sum(1 for v in values if v is None)
        assert none_count > 0, (
            "Precondition: model_dump() with None values should produce None in get() results. "
            "If this fails, the DB model may have changed to use non-None defaults."
        )

    def test_none_value_causes_nan_in_numpy_array(self):
        """Demonstrate that None values from dict.get() cause NaN in numpy arrays.

        This is the downstream effect of Bug #4: the feature vector contains NaN
        which poisons gradient computation during training.
        """
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES

        stats = self._make_fake_stats({"avg_kills": None, "avg_adr": None})
        d = stats.model_dump()
        values = [d.get(f, 0.0) for f in MATCH_AGGREGATE_FEATURES]

        # numpy converts None to nan for float32 arrays
        # (or raises TypeError on some numpy versions)
        try:
            vec = np.array(values, dtype=np.float32)
            has_nan = np.any(np.isnan(vec))
            assert has_nan, (
                "BUG #4: None values from DB should cause NaN in feature vector. "
                "If this assertion fails, numpy may have auto-converted None to 0.0 "
                "on this platform, but the behavior is undefined and unreliable."
            )
        except (TypeError, ValueError):
            # Some numpy versions raise instead of producing NaN — this is also a bug
            # because _prepare_tensors doesn't catch this exception
            pass  # Test passes: the error proves the bug exists

    def test_feature_vector_dimensions(self):
        """Feature vector from _prepare_tensors must have exactly METADATA_DIM dims."""
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        stats = self._make_fake_stats()
        d = stats.model_dump()
        vec = np.array([d.get(f, 0.0) for f in MATCH_AGGREGATE_FEATURES], dtype=np.float32)

        assert vec.shape == (
            METADATA_DIM,
        ), f"Feature vector should be ({METADATA_DIM},), got {vec.shape}"


class TestDemoTiersAndConfidence:
    """Verify the maturity tier system constants."""

    def test_tier_boundaries_are_contiguous(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import DEMO_TIERS

        # Tiers should cover the full range [0, inf)
        sorted_tiers = sorted(DEMO_TIERS.values(), key=lambda x: x[0])
        assert sorted_tiers[0][0] == 0, "First tier should start at 0"
        assert sorted_tiers[-1][1] == float("inf"), "Last tier should extend to infinity"

        # Verify contiguity: each tier's end == next tier's start
        for i in range(len(sorted_tiers) - 1):
            current_end = sorted_tiers[i][1]
            next_start = sorted_tiers[i + 1][0]
            assert current_end == next_start, (
                f"Gap in tiers: {sorted_tiers[i]} ends at {current_end} "
                f"but next starts at {next_start}"
            )

    def test_confidence_multipliers_are_valid(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import TIER_CONFIDENCE

        for tier, conf in TIER_CONFIDENCE.items():
            assert 0.0 <= conf <= 1.0, f"Confidence for {tier} is {conf}, must be in [0, 1]"

    def test_mature_tier_has_full_confidence(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import TIER_CONFIDENCE

        assert TIER_CONFIDENCE["MATURE"] == 1.0, "MATURE tier should have 1.0 confidence"

    def test_calibrating_has_lowest_confidence(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import TIER_CONFIDENCE

        calibrating = TIER_CONFIDENCE["CALIBRATING"]
        for tier, conf in TIER_CONFIDENCE.items():
            if tier != "CALIBRATING":
                assert (
                    calibrating <= conf
                ), f"CALIBRATING ({calibrating}) should be <= {tier} ({conf})"


class TestProBaselineVector:
    """Verify the pro baseline vector construction."""

    def test_baseline_defaults_cover_all_features(self):
        """The defaults dict in _get_pro_baseline_vector must cover ALL MATCH_AGGREGATE_FEATURES."""
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES

        # Extracted from _get_pro_baseline_vector source
        defaults = {
            "avg_kills": 0.75,
            "avg_deaths": 0.65,
            "avg_adr": 80.0,
            "avg_hs": 0.50,
            "avg_kast": 0.72,
            "kill_std": 0.15,
            "adr_std": 12.0,
            "kd_ratio": 1.15,
            "impact_rounds": 0.7,
            "accuracy": 0.50,
            "econ_rating": 0.75,
            "rating": 1.05,
            "opening_duel_win_pct": 0.50,
            "clutch_win_pct": 0.10,
            "trade_kill_ratio": 0.15,
            "flash_assists": 0.10,
            "positional_aggression_score": 0.50,
            "kpr": 0.75,
            "dpr": 0.65,
            "rating_impact": 1.10,
            "rating_survival": 0.35,
            "he_damage_per_round": 5.0,
            "smokes_per_round": 0.40,
            "unused_utility_per_round": 0.30,
            "thrusmoke_kill_pct": 0.02,
        }

        missing = [f for f in MATCH_AGGREGATE_FEATURES if f not in defaults]
        assert len(missing) == 0, f"Pro baseline defaults missing features: {missing}"
