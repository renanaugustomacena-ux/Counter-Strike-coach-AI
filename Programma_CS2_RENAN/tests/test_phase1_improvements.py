"""
Phase 1 improvement tests: Z-penalty, fuzzy nickname matching, outlier trimming,
and maturity tier lookup logic.

No MagicMock, no @patch. Pure-function tests with controlled inputs.
"""

import numpy as np
import pandas as pd
import pytest

from Programma_CS2_RENAN.backend.nn.coach_manager import DEMO_TIERS, TIER_CONFIDENCE
from Programma_CS2_RENAN.backend.processing.baselines.nickname_resolver import NicknameResolver
from Programma_CS2_RENAN.backend.processing.connect_map_context import distance_with_z_penalty
from Programma_CS2_RENAN.backend.processing.validation.sanity import LIMITS, validate_and_trim


class TestVerticality:
    def test_z_penalty_logic(self):
        """Test that Z-axis difference applies penalty on multi-level maps."""
        # Case 1: Same level (Z diff < 200) — standard 3D Euclidean
        pos_a = (0, 0, 0)
        pos_b = (100, 0, 100)
        dist_3d = np.linalg.norm(np.array(pos_a) - np.array(pos_b))

        result_same_level = distance_with_z_penalty(pos_a, pos_b, z_threshold=200)
        assert result_same_level == pytest.approx(dist_3d, abs=0.01)

        # Case 2: Different levels (Z diff > 200)
        pos_c = (0, 0, 0)
        pos_d = (100, 0, 300)
        # XY_dist=100, Z_diff=300, factor=2.0 → 100 + 600 = 700
        result_diff_level = distance_with_z_penalty(
            pos_c, pos_d, z_threshold=200, z_penalty_factor=2.0
        )
        assert result_diff_level == pytest.approx(700.0, abs=0.01)


class TestFuzzyNickname:
    def test_fuzzy_match_logic(self):
        """Test Levenshtein fuzzy matching logic."""
        candidates = ["s1mple", "ZywOo", "NiKo", "m0NESY", "donk"]

        # Exact match
        assert NicknameResolver._fuzzy_match("s1mple", candidates) == "s1mple"
        # Case insensitive
        assert NicknameResolver._fuzzy_match("zywoo", candidates) == "ZywOo"
        # Fuzzy match (typo)
        assert NicknameResolver._fuzzy_match("simple", candidates) == "s1mple"
        # Leet-speak gap below 0.8 threshold
        assert NicknameResolver._fuzzy_match("monsey", candidates) is None
        # Near-match with higher similarity
        assert NicknameResolver._fuzzy_match("m0nesy", candidates) == "m0NESY"
        # No match
        assert NicknameResolver._fuzzy_match("Renan", candidates) is None


class TestOutlierTrimming:
    def test_trimming_outliers(self):
        """Test that validate_and_trim clamps values."""
        df = pd.DataFrame({"adr": [-50.0, 100.0, 300.0], "kills": [5, 5, 5], "round": [1, 2, 3]})

        # Strict mode should raise
        with pytest.raises(ValueError):
            validate_and_trim(df, strict=True)

        # Trim mode should clamp
        trimmed = validate_and_trim(df, strict=False)
        assert trimmed["adr"].iloc[0] == 0.0  # Clamped min
        assert trimmed["adr"].iloc[1] == 100.0  # Unchanged
        assert trimmed["adr"].iloc[2] == 200.0  # Clamped max


class TestMaturityTiers:
    """Pure-function tests for DEMO_TIERS and TIER_CONFIDENCE lookup."""

    def _tier_for_count(self, count: int) -> str:
        """Replicate the tier lookup logic from get_maturity_tier."""
        for tier_name, (min_demos, max_demos) in DEMO_TIERS.items():
            if min_demos <= count < max_demos:
                return tier_name
        return "MATURE"

    def test_calibrating_tier(self):
        assert self._tier_for_count(0) == "CALIBRATING"
        assert self._tier_for_count(20) == "CALIBRATING"
        assert self._tier_for_count(49) == "CALIBRATING"
        assert TIER_CONFIDENCE["CALIBRATING"] == 0.5

    def test_learning_tier(self):
        assert self._tier_for_count(50) == "LEARNING"
        assert self._tier_for_count(100) == "LEARNING"
        assert self._tier_for_count(199) == "LEARNING"
        assert TIER_CONFIDENCE["LEARNING"] == 0.8

    def test_mature_tier(self):
        assert self._tier_for_count(200) == "MATURE"
        assert self._tier_for_count(250) == "MATURE"
        assert self._tier_for_count(1000) == "MATURE"
        assert TIER_CONFIDENCE["MATURE"] == 1.0

    def test_tier_boundaries_are_contiguous(self):
        """Verify tier boundaries cover the full range without gaps."""
        prev_max = 0
        for tier_name, (min_demos, max_demos) in DEMO_TIERS.items():
            assert (
                min_demos == prev_max
            ), f"Gap at tier {tier_name}: expected min={prev_max}, got {min_demos}"
            prev_max = max_demos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
