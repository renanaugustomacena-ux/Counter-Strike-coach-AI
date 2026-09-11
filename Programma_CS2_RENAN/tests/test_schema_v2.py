"""Tests for the v2 feature schema, extraction functions, and v1→v2 remap (D-04..D-07).

Covers:
- Schema invariants (fingerprint, dimensions, vocab sizes).
- extract_v2 output dtypes/shapes/ranges.
- remap_v1_to_v2(extract(tick)) == extract_v2(tick) on 2000 synthetic ticks.
- extract_frame_v2 == stacked extract_v2.
- vocab_index fallback with throttled WARNING.
- Integration test (marked, requires CS2_INTEGRATION_TESTS=1).
"""

import logging
import os
import random

import numpy as np
import pandas as pd
import pytest

from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import (
    CS2_V2,
    Kind,
    _reset_vocab_fallback_state_for_tests,
)
from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
    WEAPON_CLASS_MAP,
    FeatureExtractor,
    extract_frame_v2,
    extract_v2,
    remap_v1_to_v2,
)

EXPECTED_FINGERPRINT = "e26556888a54cf005f961abc8b0f7c7fcf64f8d4f075b56195306ae79a7ac26c"

MAPS = [
    "de_ancient",
    "de_anubis",
    "de_dust2",
    "de_inferno",
    "de_mirage",
    "de_nuke",
    "de_overpass",
    "de_train",
    "de_vertigo",
]
WEAPONS = list(WEAPON_CLASS_MAP.keys())[:20]
SIDES = ["CT", "T"]


# ---------------------------------------------------------------------------
# Schema invariant tests
# ---------------------------------------------------------------------------


class TestSchemaInvariants:
    def test_fingerprint_stability(self):
        assert CS2_V2.fingerprint() == EXPECTED_FINGERPRINT

    def test_numeric_dim_is_21(self):
        assert CS2_V2.numeric_dim == 21

    def test_categorical_vocab_sizes(self):
        assert CS2_V2.categorical_vocab_sizes == [10, 9, 3]

    def test_numeric_names_count(self):
        assert len(CS2_V2.numeric_names) == 21

    def test_categorical_names_count(self):
        assert len(CS2_V2.categorical_names) == 3

    def test_no_duplicate_field_names(self):
        names = [f.name for f in CS2_V2.fields]
        assert len(set(names)) == len(names)

    def test_numeric_fields_are_numeric_kind(self):
        for f in CS2_V2.numeric_fields:
            assert f.kind == Kind.numeric

    def test_categorical_fields_are_categorical_kind(self):
        for f in CS2_V2.categorical_fields:
            assert f.kind == Kind.categorical

    def test_fingerprint_changes_on_field_change(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import (
            FeatureSchema,
            SchemaField,
        )

        modified = FeatureSchema(
            schema_id=CS2_V2.schema_id,
            version=CS2_V2.version,
            fields=CS2_V2.fields + (SchemaField("extra", Kind.numeric, "extra", "x"),),
        )
        assert modified.fingerprint() != CS2_V2.fingerprint()

    def test_fingerprint_ignores_schema_id_version(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import (
            FeatureSchema,
        )

        copy = FeatureSchema(schema_id="other_id", version=99, fields=CS2_V2.fields)
        assert copy.fingerprint() == CS2_V2.fingerprint()

    def test_to_json_roundtrips(self):
        import json

        parsed = json.loads(CS2_V2.to_json())
        assert parsed["schema_id"] == "cs2_v2"
        assert parsed["version"] == 1
        assert len(parsed["fields"]) == len(CS2_V2.fields)

    def test_categorical_vocab_sizes_is_list(self):
        result = CS2_V2.categorical_vocab_sizes
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# extract_v2 output tests
# ---------------------------------------------------------------------------


def _make_tick(rng: random.Random) -> dict:
    """Generate a synthetic tick with all fields populated."""
    return {
        "health": rng.randint(0, 100),
        "armor": rng.randint(0, 100),
        "has_helmet": rng.choice([True, False]),
        "has_defuser": rng.choice([True, False]),
        "equipment_value": rng.randint(0, 16000),
        "is_crouching": rng.choice([True, False]),
        "is_scoped": rng.choice([True, False]),
        "flash_duration": rng.choice([0.0, 0.0, 0.0, rng.uniform(0.1, 5.0)]),
        "is_blinded": rng.choice([True, False]),
        "enemies_visible": rng.randint(0, 5),
        "pos_x": rng.uniform(-4096, 4096),
        "pos_y": rng.uniform(-4096, 4096),
        "pos_z": rng.uniform(-1024, 1024),
        "view_x": rng.uniform(-180, 180),
        "view_y": rng.uniform(-90, 90),
        "active_weapon": rng.choice(WEAPONS + [None]),
        "time_in_round": rng.uniform(0, 175),
        "bomb_planted": rng.choice([True, False]),
        "teammates_alive": rng.randint(0, 4),
        "enemies_alive": rng.randint(0, 5),
        "team_economy": rng.randint(0, 20000),
    }


class TestExtractV2:
    def test_output_dtypes(self):
        tick = _make_tick(random.Random(42))
        num, cat = extract_v2(tick, map_name="de_dust2", side="CT")
        assert num.dtype == np.float32
        assert cat.dtype == np.int64

    def test_output_shapes(self):
        tick = _make_tick(random.Random(42))
        num, cat = extract_v2(tick, map_name="de_dust2", side="CT")
        assert num.shape == (21,)
        assert cat.shape == (3,)

    def test_numeric_no_nan(self):
        tick = _make_tick(random.Random(42))
        num, _ = extract_v2(tick, map_name="de_dust2", side="CT")
        assert not np.any(np.isnan(num))
        assert not np.any(np.isinf(num))

    def test_categorical_in_range(self):
        rng = random.Random(42)
        for _ in range(100):
            tick = _make_tick(rng)
            map_name = rng.choice(MAPS + [None])
            side = rng.choice(SIDES + [None])
            _, cat = extract_v2(tick, map_name=map_name, side=side)
            assert 0 <= cat[0] < 10, f"map_id out of range: {cat[0]}"
            assert 0 <= cat[1] < 9, f"weapon_class out of range: {cat[1]}"
            assert 0 <= cat[2] < 3, f"side out of range: {cat[2]}"

    def test_has_helmet_none_fallback(self):
        tick = {"armor": 50, "has_helmet": None}
        num, _ = extract_v2(tick)
        assert num[2] == 1.0

        tick2 = {"armor": 0, "has_helmet": None}
        num2, _ = extract_v2(tick2)
        assert num2[2] == 0.0

    def test_map_auto_resolve(self):
        tick = _make_tick(random.Random(42))
        tick["map_name"] = "de_nuke"
        num, cat = extract_v2(tick)
        assert cat[0] == CS2_V2.fields[-3].vocab.index("de_nuke")
        assert num[15] > 0.0 or abs(tick["pos_z"] - (-495)) < 1e-6


# ---------------------------------------------------------------------------
# remap_v1_to_v2(extract(tick)) == extract_v2(tick) on 2000 random ticks
# ---------------------------------------------------------------------------


class TestRemapEquivalence:
    def test_2000_random_ticks(self):
        rng = random.Random(12345)
        mismatches = 0
        for _ in range(2000):
            tick = _make_tick(rng)
            map_name = rng.choice(MAPS)
            side = rng.choice(SIDES)
            weapon = tick.get("active_weapon")

            v1 = FeatureExtractor.extract(tick, map_name=map_name)
            rnum, rcat = remap_v1_to_v2(v1, map_name, weapon, side)
            enum, ecat = extract_v2(tick, map_name=map_name, side=side)

            if not np.allclose(rnum, enum, atol=1e-6):
                mismatches += 1
                if mismatches <= 3:
                    diff = np.abs(rnum - enum)
                    bad = np.where(diff > 1e-6)[0]
                    pytest.fail(
                        f"Numeric mismatch at indices {bad}: "
                        f"remap={rnum[bad]}, extract={enum[bad]}, "
                        f"diff={diff[bad]}"
                    )
            assert np.array_equal(rcat, ecat)

        assert mismatches == 0, f"{mismatches}/2000 ticks had numeric mismatches"


# ---------------------------------------------------------------------------
# extract_frame_v2 == stacked extract_v2
# ---------------------------------------------------------------------------


class TestFrameEquivalence:
    def test_frame_matches_stacked(self):
        rng = random.Random(99)
        ticks = [_make_tick(rng) for _ in range(200)]
        map_name = "de_nuke"
        side = "T"

        df = pd.DataFrame(ticks)
        fnum, fcat = extract_frame_v2(df, map_name=map_name, side=side)

        for i, t in enumerate(ticks):
            enum, ecat = extract_v2(t, map_name=map_name, side=side)
            if not np.allclose(fnum[i], enum, atol=1e-6):
                diff = np.abs(fnum[i] - enum)
                bad = np.where(diff > 1e-6)[0]
                pytest.fail(
                    f"Row {i} numeric mismatch at indices {bad}: "
                    f"frame={fnum[i][bad]}, single={enum[bad]}, diff={diff[bad]}"
                )
            assert np.array_equal(fcat[i], ecat), f"Row {i} cat mismatch"

    def test_frame_matches_stacked_with_nan(self):
        """NaN in numeric columns must produce same result as scalar path."""
        rng = random.Random(77)
        ticks = [_make_tick(rng) for _ in range(200)]
        nan_cols = ["health", "time_in_round", "enemies_visible"]
        for t in ticks:
            if rng.random() < 0.1:
                col = rng.choice(nan_cols)
                t[col] = float("nan")

        map_name = "de_inferno"
        side = "CT"
        df = pd.DataFrame(ticks)
        fnum, fcat = extract_frame_v2(df, map_name=map_name, side=side)

        for i, t in enumerate(ticks):
            enum, ecat = extract_v2(t, map_name=map_name, side=side)
            if not np.allclose(fnum[i], enum, atol=1e-6):
                diff = np.abs(fnum[i] - enum)
                bad = np.where(diff > 1e-6)[0]
                pytest.fail(
                    f"Row {i} numeric mismatch at indices {bad}: "
                    f"frame={fnum[i][bad]}, single={enum[bad]}, diff={diff[bad]}"
                )
            assert np.array_equal(fcat[i], ecat), f"Row {i} cat mismatch"

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["health", "armor"])
        num, cat = extract_frame_v2(df, map_name="de_dust2", side="CT")
        assert num.shape == (0, 21)
        assert cat.shape == (0, 3)


# ---------------------------------------------------------------------------
# vocab_index fallback tests
# ---------------------------------------------------------------------------


class TestVocabFallback:
    def setup_method(self):
        _reset_vocab_fallback_state_for_tests()

    def test_unknown_map_falls_back_to_other(self):
        idx = CS2_V2.vocab_index("map_id", "de_nonexistent")
        assert idx == 9

    def test_unknown_weapon_falls_back_to_other(self):
        idx = CS2_V2.vocab_index("weapon_class", "plasma_rifle")
        assert idx == 8

    def test_unknown_side_falls_back_to_unknown(self):
        idx = CS2_V2.vocab_index("side", "SPEC")
        assert idx == 2

    def test_fallback_logs_warning(self, caplog):
        _reset_vocab_fallback_state_for_tests()
        parent = logging.getLogger("cs2analyzer")
        orig = parent.propagate
        parent.propagate = True
        try:
            with caplog.at_level(logging.WARNING, logger="cs2analyzer.schema_v2"):
                CS2_V2.vocab_index("map_id", "de_zoo_unique_test")
            assert any("de_zoo_unique_test" in r.message for r in caplog.records)
        finally:
            parent.propagate = orig

    def test_fallback_throttled(self, caplog):
        _reset_vocab_fallback_state_for_tests()
        parent = logging.getLogger("cs2analyzer")
        orig = parent.propagate
        parent.propagate = True
        try:
            with caplog.at_level(logging.WARNING, logger="cs2analyzer.schema_v2"):
                CS2_V2.vocab_index("map_id", "de_throttle_unique_test")
                caplog.clear()
                CS2_V2.vocab_index("map_id", "de_throttle_unique_test")
            assert not any("de_throttle_unique_test" in r.message for r in caplog.records)
        finally:
            parent.propagate = orig

    def test_valid_value_no_fallback(self):
        idx = CS2_V2.vocab_index("map_id", "de_dust2")
        assert idx == 2

    def test_no_vocab_raises(self):
        with pytest.raises(ValueError, match="no vocabulary"):
            CS2_V2.vocab_index("health", "high")

    def test_unknown_field_raises(self):
        with pytest.raises(KeyError, match="No field named"):
            CS2_V2.vocab_index("nonexistent", "value")


# ---------------------------------------------------------------------------
# Weapon class mapping tests
# ---------------------------------------------------------------------------


class TestWeaponClassMapping:
    def test_known_weapons_map_correctly(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            _weapon_to_class_name,
        )

        assert _weapon_to_class_name("ak47") == "rifle"
        assert _weapon_to_class_name("awp") == "sniper"
        assert _weapon_to_class_name("glock") == "pistol"
        assert _weapon_to_class_name("knife") == "knife"
        assert _weapon_to_class_name("flashbang") == "grenade"
        assert _weapon_to_class_name("nova") == "heavy"
        assert _weapon_to_class_name("mac10") == "smg"
        assert _weapon_to_class_name("taser") == "other"

    def test_weapon_prefix_stripped(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            _weapon_to_class_name,
        )

        assert _weapon_to_class_name("weapon_ak47") == "rifle"

    def test_unknown_weapon_maps_to_other(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            _weapon_to_class_name,
        )

        assert _weapon_to_class_name("railgun") == "other"

    def test_0xFFFFFF_maps_to_none(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            _weapon_to_class_name,
        )

        assert _weapon_to_class_name("16777215") == "none"


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.timeout(600)
class TestSchemaIntegration:
    """Requires CS2_INTEGRATION_TESTS=1 and access to the monolith."""

    @pytest.fixture(autouse=True)
    def _skip_unless_enabled(self):
        if not os.environ.get("CS2_INTEGRATION_TESTS"):
            pytest.skip("CS2_INTEGRATION_TESTS not set")

    def test_frame_and_scalar_paths_agree_on_real_ticks(self):
        """100,000 real monolith rows: frame path == scalar path == v1 remap (D-06)."""
        import sqlite3

        import pandas as pd

        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
            extract_frame_v2,
            extract_v2,
            remap_v1_to_v2,
        )

        db_path = os.path.realpath(
            os.path.join(os.path.dirname(__file__), "..", "backend", "storage", "database.db")
        )
        if not os.path.exists(db_path):
            pytest.skip("monolith not found")
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=60)
        conn.execute("PRAGMA query_only=1")
        try:
            demo = conn.execute("SELECT demo_name FROM playermatchstats LIMIT 1").fetchone()
            if demo is None:
                pytest.skip("no playermatchstats rows")
            df = pd.read_sql_query(
                "SELECT * FROM playertickstate WHERE demo_name = ? ORDER BY tick LIMIT 100000",
                conn,
                params=(demo[0],),
            )
        finally:
            conn.close()
        if len(df) < 1000:
            pytest.skip("not enough tick rows")
        map_name = str(df["map_name"].iloc[0])
        x_num, x_cat = extract_frame_v2(df, map_name=map_name, side="CT")
        assert x_num.shape == (len(df), 21) and x_cat.shape == (len(df), 3)
        assert not np.any(np.isnan(x_num)) and not np.any(np.isinf(x_num))
        assert x_num[:, 0].min() >= 0.0 and x_num[:, 0].max() <= 1.0  # health
        rng = np.random.default_rng(0)
        for i in rng.choice(len(df), size=min(5000, len(df)), replace=False):
            tick = df.iloc[int(i)].to_dict()
            num, cat = extract_v2(tick, map_name=map_name, side="CT")
            np.testing.assert_allclose(num, x_num[i], atol=1e-6, err_msg=f"row {i} scalar vs frame")
            assert cat.tolist() == x_cat[i].tolist(), f"row {i} categorical scalar vs frame"
            v1 = FeatureExtractor.extract(tick, map_name=map_name)
            num_r, cat_r = remap_v1_to_v2(v1, map_name, tick.get("active_weapon"), "CT")
            np.testing.assert_allclose(num_r, num, atol=1e-6, err_msg=f"row {i} v1 remap vs v2")
            assert cat_r.tolist() == cat.tolist(), f"row {i} categorical remap vs v2"
