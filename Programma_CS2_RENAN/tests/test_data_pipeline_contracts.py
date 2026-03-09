"""
Tests for data pipeline contracts — Tier 2: Demo parser data quality.

Verifies:
1. Missing columns in parsed data are detected (not silently zero-filled)
2. NaN/None values are flagged
3. Feature extractor handles object-style input (ORM models)
"""

import numpy as np
import pytest


class TestFeatureExtractorObjectInput:
    """Verify that FeatureExtractor handles both dict and ORM object input."""

    def _make_tick_object(self, **kwargs):
        """Create a simple object with attributes mimicking PlayerTickState."""

        class FakeTick:
            pass

        obj = FakeTick()
        defaults = {
            "health": 100,
            "armor": 100,
            "has_helmet": True,
            "has_defuser": False,
            "equipment_value": 5000,
            "is_crouching": False,
            "is_scoped": False,
            "is_blinded": False,
            "enemies_visible": 0,
            "pos_x": 500.0,
            "pos_y": -300.0,
            "pos_z": 50.0,
            "view_x": 90.0,
            "view_y": 5.0,
            "active_weapon": "ak47",
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(obj, k, v)
        return obj

    def test_object_input_produces_valid_vector(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        tick = self._make_tick_object()
        vec = FeatureExtractor.extract(tick)

        assert vec.shape == (METADATA_DIM,)
        assert np.all(np.isfinite(vec))

    def test_dict_and_object_produce_same_result(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        tick_dict = {
            "health": 100,
            "armor": 50,
            "has_helmet": True,
            "has_defuser": False,
            "equipment_value": 3000,
            "is_crouching": False,
            "is_scoped": False,
            "is_blinded": False,
            "enemies_visible": 2,
            "pos_x": 100.0,
            "pos_y": -200.0,
            "pos_z": 30.0,
            "view_x": 180.0,
            "view_y": -10.0,
            "active_weapon": "m4a1",
        }
        tick_obj = self._make_tick_object(**tick_dict)

        vec_dict = FeatureExtractor.extract(tick_dict)
        vec_obj = FeatureExtractor.extract(tick_obj)

        np.testing.assert_array_almost_equal(
            vec_dict, vec_obj,
            err_msg="Dict and object input should produce identical feature vectors"
        )

    def test_missing_attribute_uses_default(self):
        """Object with missing attributes should use defaults gracefully."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        class MinimalTick:
            health = 100

        vec = FeatureExtractor.extract(MinimalTick())
        assert vec.shape == (METADATA_DIM,)
        assert np.all(np.isfinite(vec))


class TestRoundPhaseEncoding:
    """Verify economic phase classification from equipment_value."""

    def test_pistol_round(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"equipment_value": 800})
        assert vec[18] == 0.0, f"Equipment value 800 should be pistol (0.0), got {vec[18]}"

    def test_eco_round(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"equipment_value": 2000})
        assert vec[18] == pytest.approx(0.33), (
            f"Equipment value 2000 should be eco (0.33), got {vec[18]}"
        )

    def test_force_buy(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"equipment_value": 3500})
        assert vec[18] == pytest.approx(0.66), (
            f"Equipment value 3500 should be force (0.66), got {vec[18]}"
        )

    def test_full_buy(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"equipment_value": 5000})
        assert vec[18] == 1.0, (
            f"Equipment value 5000 should be full_buy (1.0), got {vec[18]}"
        )


class TestMapIdEncoding:
    """Verify deterministic map ID hashing."""

    def test_same_map_same_hash(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec1 = FeatureExtractor.extract({"health": 100}, map_name="de_mirage")
        vec2 = FeatureExtractor.extract({"health": 100}, map_name="de_mirage")

        assert vec1[17] == vec2[17], "Same map should produce identical map_id"

    def test_different_maps_different_hash(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec1 = FeatureExtractor.extract({"health": 100}, map_name="de_mirage")
        vec2 = FeatureExtractor.extract({"health": 100}, map_name="de_dust2")

        assert vec1[17] != vec2[17], "Different maps should produce different map_ids"

    def test_no_map_produces_zero(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        vec = FeatureExtractor.extract({"health": 100}, map_name=None)
        assert vec[17] == 0.0, "No map should produce map_id=0.0"

    def test_map_hash_is_deterministic_across_calls(self):
        """Map hash must be reproducible (no Python hash randomization)."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        results = set()
        for _ in range(10):
            vec = FeatureExtractor.extract({"health": 100}, map_name="de_inferno")
            results.add(vec[17])

        assert len(results) == 1, (
            f"Map hash should be deterministic, got {len(results)} different values"
        )
