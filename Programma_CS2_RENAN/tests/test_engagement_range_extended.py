"""Extended tests for backend.analysis.engagement_range module.

Covers EngagementRangeAnalyzer instantiation, kill distance edge cases (same point,
full 3D), NamedPositionRegistry with empty/custom registries, and analyze_match_engagements
with empty input.

These tests are ADDITIVE to the coverage in test_game_theory.py::TestEngagementRangeAnalyzer
and test_game_theory.py::TestNamedPositionRegistry.
"""

import math

import pytest

pytestmark = pytest.mark.timeout(5)


class TestEngagementRangeAnalyzerExtended:
    """Extended coverage for EngagementRangeAnalyzer — edge cases and instantiation."""

    def test_engagement_range_analyzer_instantiation(self):
        """EngagementRangeAnalyzer creates without error and exposes expected API."""
        from Programma_CS2_RENAN.backend.analysis.engagement_range import EngagementRangeAnalyzer

        analyzer = EngagementRangeAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "compute_kill_distance")
        assert hasattr(analyzer, "classify_range")
        assert hasattr(analyzer, "compute_profile")
        assert hasattr(analyzer, "compare_to_role")
        assert hasattr(analyzer, "analyze_match_engagements")
        # Should have a position_registry attribute from __init__
        assert hasattr(analyzer, "position_registry")
        assert analyzer.position_registry is not None

    def test_compute_kill_distance_same_point(self):
        """Distance between identical coordinates is exactly 0.

        This is a degenerate case (self-kill or position overlap) that must not
        raise or produce NaN.
        """
        from Programma_CS2_RENAN.backend.analysis.engagement_range import EngagementRangeAnalyzer

        dist = EngagementRangeAnalyzer.compute_kill_distance(
            100.0,
            200.0,
            300.0,
            100.0,
            200.0,
            300.0,
        )
        assert dist == 0.0

    def test_compute_kill_distance_3d(self):
        """Distance calculation correctly uses all 3 axes.

        Uses a known 3D vector: (3, 4, 0) -> (0, 0, 5).
        Expected distance = sqrt(9 + 16 + 25) = sqrt(50).
        """
        from Programma_CS2_RENAN.backend.analysis.engagement_range import EngagementRangeAnalyzer

        dist = EngagementRangeAnalyzer.compute_kill_distance(
            3.0,
            4.0,
            0.0,
            0.0,
            0.0,
            5.0,
        )
        expected = math.sqrt(9.0 + 16.0 + 25.0)
        assert dist == pytest.approx(expected, abs=1e-9)

    def test_compute_kill_distance_negative_coords(self):
        """Distance is correct with negative coordinates (common in CS2 maps)."""
        from Programma_CS2_RENAN.backend.analysis.engagement_range import EngagementRangeAnalyzer

        # (-100, -200, 0) to (100, 200, 0) = sqrt(200^2 + 400^2) = sqrt(200000)
        dist = EngagementRangeAnalyzer.compute_kill_distance(
            -100.0,
            -200.0,
            0.0,
            100.0,
            200.0,
            0.0,
        )
        expected = math.sqrt(200.0**2 + 400.0**2)
        assert dist == pytest.approx(expected, abs=1e-9)


class TestNamedPositionRegistryExtended:
    """Extended coverage for NamedPositionRegistry — empty and custom registries."""

    def test_named_position_registry_empty(self):
        """A registry queried for a non-existent map returns None for any coordinates.

        Unlike test_unknown_map_returns_none (which uses the populated registry),
        this tests that the registry handles any arbitrary map name gracefully.
        """
        from Programma_CS2_RENAN.backend.analysis.engagement_range import NamedPositionRegistry

        registry = NamedPositionRegistry()
        # Query a map that has zero positions registered
        result = registry.find_nearest("de_completely_fake_map", 0.0, 0.0, 0.0)
        assert result is None
        # Also verify get_positions returns empty list
        positions = registry.get_positions("de_completely_fake_map")
        assert positions == []

    def test_analyze_empty_kills(self):
        """Analyzing an empty kill list returns safe default with zero profile.

        Verifies the full return dict structure, not just total_kills == 0.
        """
        from Programma_CS2_RENAN.backend.analysis.engagement_range import (
            EngagementProfile,
            EngagementRangeAnalyzer,
        )

        analyzer = EngagementRangeAnalyzer()
        result = analyzer.analyze_match_engagements([], "de_dust2", "flex")

        # Validate return structure
        assert isinstance(result, dict)
        assert "profile" in result
        assert "observations" in result
        assert "annotated_kills" in result

        # Profile should be a zero-valued EngagementProfile
        profile = result["profile"]
        assert isinstance(profile, EngagementProfile)
        assert profile.total_kills == 0
        assert profile.avg_distance == 0.0
        assert profile.close_pct == 0.0
        assert profile.medium_pct == 0.0
        assert profile.long_pct == 0.0
        assert profile.extreme_pct == 0.0

        # No observations from zero kills
        assert result["observations"] == []
        # No annotated kills
        assert result["annotated_kills"] == []
