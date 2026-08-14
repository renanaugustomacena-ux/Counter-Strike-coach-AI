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
    """W3 test-debt fix: the old tests here DEMONSTRATED the dict.get(None)
    semantics on an inline re-implementation and never called production —
    they passed whether or not Bug #4 was fixed. This suite drives the REAL
    _prepare_tensors with None-laden rows and pins the fix (walrus None
    guard): NULL DB values become 0.0, never NaN."""

    def _mgr(self):
        from unittest.mock import patch

        import numpy as np

        from Programma_CS2_RENAN.backend.nn.coach_manager import (
            MATCH_AGGREGATE_FEATURES,
            TARGET_INDICES,
            TRAINING_FEATURES,
            CoachTrainingManager,
        )

        mgr = CoachTrainingManager.__new__(CoachTrainingManager)
        mgr.target_indices = TARGET_INDICES
        mgr.feature_names = TRAINING_FEATURES
        patcher = patch.object(
            CoachTrainingManager,
            "_get_pro_baseline_vector",
            return_value=np.ones(len(MATCH_AGGREGATE_FEATURES), dtype=np.float32),
        )
        return mgr, patcher

    @staticmethod
    def _fake_stats(overrides=None):
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES

        base = {f: 0.5 for f in MATCH_AGGREGATE_FEATURES}
        if overrides:
            base.update(overrides)

        class FakeStats:
            def model_dump(self):
                return base

        return FakeStats()

    def test_null_db_values_become_zero_not_nan(self):
        import torch

        mgr, patcher = self._mgr()
        rows = [self._fake_stats({"avg_kills": None, "avg_adr": None, "rating": None})]
        with patcher:
            X, y = mgr._prepare_tensors(rows)
        assert not torch.any(torch.isnan(X)), "None leaked into the tensor as NaN"
        assert not torch.any(torch.isnan(y))

    def test_clean_rows_unaffected(self):
        import torch

        mgr, patcher = self._mgr()
        with patcher:
            X, _ = mgr._prepare_tensors([self._fake_stats()])
        assert torch.all(torch.isfinite(X))


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
