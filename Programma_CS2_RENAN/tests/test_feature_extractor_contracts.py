"""
Tests for vectorizer.py FeatureExtractor — Tier 2: Feature extraction contracts.

Verifies:
1. Output shape is exactly (METADATA_DIM,) = (25,)
2. Feature values are in expected ranges (normalized)
3. No NaN/Inf in output for valid inputs
4. Missing input fields handled gracefully (not silently producing zeros)
5. Batch extraction consistency
6. Feature name list matches dimension count
"""

import math

import numpy as np
import pytest


class TestFeatureVectorDimensions:
    """Verify output shape contract."""

    def test_output_shape_is_metadata_dim(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        tick = {"health": 100, "armor": 100, "pos_x": 500, "pos_y": -300, "pos_z": 50}
        vec = FeatureExtractor.extract(tick)

        assert vec.shape == (METADATA_DIM,), (
            f"Output shape should be ({METADATA_DIM},), got {vec.shape}"
        )

    def test_output_dtype_is_float32(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"health": 100})
        assert vec.dtype == np.float32

    def test_metadata_dim_constant_is_25(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert METADATA_DIM == 25, f"METADATA_DIM should be 25, got {METADATA_DIM}"


class TestFeatureValueRanges:
    """Verify that normalized feature values are in expected ranges."""

    def test_health_normalized_0_to_1(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"health": 100})
        assert 0.0 <= vec[0] <= 1.0, f"Health should be [0,1], got {vec[0]}"

    def test_zero_health(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"health": 0})
        assert vec[0] == 0.0

    def test_armor_normalized(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"armor": 100})
        assert 0.0 <= vec[1] <= 1.0

    def test_binary_features_are_0_or_1(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        tick = {
            "health": 100,
            "has_helmet": True,
            "has_defuser": True,
            "is_crouching": True,
            "is_scoped": False,
            "is_blinded": False,
        }
        vec = FeatureExtractor.extract(tick)

        # has_helmet=vec[2], has_defuser=vec[3], is_crouching=vec[5], is_scoped=vec[6], is_blinded=vec[7]
        for idx, name in [(2, "has_helmet"), (3, "has_defuser"), (5, "is_crouching"),
                          (6, "is_scoped"), (7, "is_blinded")]:
            assert vec[idx] in (0.0, 1.0), f"{name} (idx={idx}) should be 0 or 1, got {vec[idx]}"

    def test_view_angles_sin_cos_range(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"view_x": 270.0})
        # vec[12] = sin(yaw), vec[13] = cos(yaw)
        assert -1.0 <= vec[12] <= 1.0, f"sin(yaw) out of range: {vec[12]}"
        assert -1.0 <= vec[13] <= 1.0, f"cos(yaw) out of range: {vec[13]}"

    def test_weapon_class_encoding(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        # AK47 should be 0.6 (rifle class)
        vec = FeatureExtractor.extract({"active_weapon": "ak47"})
        assert vec[19] == pytest.approx(0.6), f"AK47 weapon class should be 0.6, got {vec[19]}"

    def test_unknown_weapon_gets_default(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"active_weapon": "nonexistent_weapon"})
        assert vec[19] == pytest.approx(0.1), f"Unknown weapon should be 0.1, got {vec[19]}"

    def test_weapon_prefix_stripping(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"active_weapon": "weapon_ak47"})
        assert vec[19] == pytest.approx(0.6), (
            f"weapon_ak47 should strip prefix and map to 0.6, got {vec[19]}"
        )


class TestNoNaNInOutput:
    """Verify that output never contains NaN or Inf."""

    def test_empty_dict_no_nan(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({})
        assert np.all(np.isfinite(vec)), (
            f"Empty input should not produce NaN/Inf. Non-finite at: {np.where(~np.isfinite(vec))}"
        )

    def test_all_zeros_no_nan(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        tick = {"health": 0, "armor": 0, "pos_x": 0, "pos_y": 0, "pos_z": 0}
        vec = FeatureExtractor.extract(tick)
        assert np.all(np.isfinite(vec))

    def test_extreme_values_no_nan(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        tick = {
            "health": 999999,
            "armor": -100,
            "pos_x": 1e10,
            "pos_y": -1e10,
            "pos_z": 1e10,
            "equipment_value": -1,
        }
        vec = FeatureExtractor.extract(tick)
        assert np.all(np.isfinite(vec)), (
            f"Extreme values should be handled gracefully. Non-finite at: "
            f"{np.where(~np.isfinite(vec))}"
        )


class TestContextFeatures:
    """Verify context-dependent features (indices 20-24)."""

    def test_context_features_default_to_zero(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"health": 100}, context=None)
        # Features 20-24 should be 0.0 when no context
        for idx in range(20, 25):
            assert vec[idx] == 0.0, f"Context feature {idx} should be 0.0 without context, got {vec[idx]}"

    def test_context_features_with_values(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        ctx = {
            "time_in_round": 60.0,
            "bomb_planted": True,
            "teammates_alive": 3,
            "enemies_alive": 2,
            "team_economy": 8000,
        }
        vec = FeatureExtractor.extract({"health": 100}, context=ctx)

        assert vec[20] > 0.0, "time_in_round should be > 0"
        assert vec[21] == 1.0, "bomb_planted should be 1.0"
        assert vec[22] > 0.0, "teammates_alive should be > 0"
        assert vec[23] > 0.0, "enemies_alive should be > 0"
        assert vec[24] > 0.0, "team_economy should be > 0"


class TestBatchExtraction:
    """Verify batch extraction consistency."""

    def test_batch_output_shape(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        ticks = [{"health": 100}, {"health": 50}, {"health": 0}]
        result = FeatureExtractor.extract_batch(ticks)

        assert result.shape == (3, METADATA_DIM), (
            f"Batch shape should be (3, {METADATA_DIM}), got {result.shape}"
        )

    def test_batch_matches_individual_extraction(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        ticks = [{"health": 100, "pos_x": 500}, {"health": 50, "pos_y": -300}]
        batch_result = FeatureExtractor.extract_batch(ticks)

        for i, tick in enumerate(ticks):
            individual = FeatureExtractor.extract(tick)
            np.testing.assert_array_equal(
                batch_result[i], individual,
                err_msg=f"Batch[{i}] differs from individual extraction"
            )


class TestFeatureNames:
    """Verify feature name consistency."""

    def test_feature_names_count_matches_dim(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        names = FeatureExtractor.get_feature_names()
        assert len(names) == METADATA_DIM, (
            f"Feature names count ({len(names)}) != METADATA_DIM ({METADATA_DIM})"
        )

    def test_no_duplicate_feature_names(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        names = FeatureExtractor.get_feature_names()
        assert len(names) == len(set(names)), "Duplicate feature names found"
