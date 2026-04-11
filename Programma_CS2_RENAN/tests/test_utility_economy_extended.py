"""
Extended tests for utility_economy.py — UtilityAnalyzer and EconomyOptimizer.

Covers:
  - EconomyOptimizer instantiation
  - UtilityAnalyzer instantiation
  - Zero utility throws do not cause ZeroDivisionError
  - Economy analysis returns expected dict structure
"""

import pytest

pytestmark = pytest.mark.timeout(5)


class TestEconomyOptimizerInstantiation:
    """EconomyOptimizer must instantiate cleanly with expected attributes."""

    def test_economy_optimizer_instantiation(self):
        """EconomyOptimizer creates without error and exposes weapon costs and thresholds."""
        from Programma_CS2_RENAN.backend.analysis.utility_economy import EconomyOptimizer

        optimizer = EconomyOptimizer()

        assert optimizer is not None
        assert isinstance(optimizer.WEAPON_COSTS, dict)
        assert len(optimizer.WEAPON_COSTS) > 0
        # Verify key thresholds are set
        assert optimizer.FULL_BUY_THRESHOLD > 0
        assert optimizer.FORCE_BUY_THRESHOLD > 0
        assert optimizer.FULL_BUY_THRESHOLD > optimizer.FORCE_BUY_THRESHOLD
        # Verify recommend method is callable
        assert callable(getattr(optimizer, "recommend", None))


class TestUtilityAnalyzerInstantiation:
    """UtilityAnalyzer must instantiate cleanly with expected attributes."""

    def test_utility_analyzer_instantiation(self):
        """UtilityAnalyzer creates without error and has PRO_BASELINES for all utility types."""
        from Programma_CS2_RENAN.backend.analysis.utility_economy import (
            UtilityAnalyzer,
            UtilityType,
        )

        analyzer = UtilityAnalyzer()

        assert analyzer is not None
        assert isinstance(analyzer.PRO_BASELINES, dict)
        # Every UtilityType must have a baseline entry
        for ut in UtilityType:
            assert ut in analyzer.PRO_BASELINES, f"Missing PRO_BASELINE for {ut.value}"
        # Verify analyze method is callable
        assert callable(getattr(analyzer, "analyze", None))


class TestZeroThrownNoDivisionError:
    """Zero utility throws must not cause ZeroDivisionError anywhere in the analysis pipeline."""

    def test_zero_thrown_no_division_error(self):
        """Analyzing stats with all thrown counts at zero produces valid results."""
        from Programma_CS2_RENAN.backend.analysis.utility_economy import UtilityAnalyzer

        analyzer = UtilityAnalyzer()

        # All zeros: no utility thrown at all
        stats = {
            "molotov_thrown": 0,
            "molotov_damage": 0,
            "he_grenade_thrown": 0,
            "he_grenade_damage": 0,
            "flash_thrown": 0,
            "flash_affected": 0,
            "smoke_thrown": 0,
            "rounds_played": 0,
        }

        # Must not raise ZeroDivisionError
        report = analyzer.analyze(stats)

        assert report is not None
        # All effectiveness scores must be valid floats in [0, 1]
        for ut, ut_stats in report.utility_stats.items():
            assert (
                0.0 <= ut_stats.effectiveness_score <= 1.0
            ), f"{ut.value} effectiveness {ut_stats.effectiveness_score} out of [0,1]"
        # Overall score must be valid
        assert 0.0 <= report.overall_score <= 1.0
        # Economy impact should be zero (nothing thrown)
        assert report.economy_impact == 0.0


class TestEconomyImpactReturnsDict:
    """Economy analysis (via UtilityReport) must return the expected data structure."""

    def test_economy_impact_returns_dict(self):
        """UtilityReport contains overall_score, utility_stats dict, recommendations list, and economy_impact float."""
        from Programma_CS2_RENAN.backend.analysis.utility_economy import (
            UtilityAnalyzer,
            UtilityReport,
            UtilityStats,
            UtilityType,
        )

        analyzer = UtilityAnalyzer()

        stats = {
            "molotov_thrown": 8,
            "molotov_damage": 200,
            "he_grenade_thrown": 4,
            "he_grenade_damage": 80,
            "flash_thrown": 12,
            "flash_affected": 10,
            "smoke_thrown": 15,
            "rounds_played": 24,
        }

        report = analyzer.analyze(stats)

        # Verify type
        assert isinstance(report, UtilityReport)

        # overall_score: float in [0, 1]
        assert isinstance(report.overall_score, float)
        assert 0.0 <= report.overall_score <= 1.0

        # utility_stats: dict mapping UtilityType -> UtilityStats
        assert isinstance(report.utility_stats, dict)
        assert len(report.utility_stats) == len(UtilityType)
        for ut in UtilityType:
            assert ut in report.utility_stats, f"Missing stats for {ut.value}"
            entry = report.utility_stats[ut]
            assert isinstance(entry, UtilityStats)
            assert isinstance(entry.total_thrown, int)
            assert isinstance(entry.damage_dealt, (int, float))
            assert isinstance(entry.enemies_affected, int)
            assert 0.0 <= entry.effectiveness_score <= 1.0

        # recommendations: list of strings
        assert isinstance(report.recommendations, list)
        for rec in report.recommendations:
            assert isinstance(rec, str)

        # economy_impact: non-negative float
        assert isinstance(report.economy_impact, (int, float))
        assert report.economy_impact >= 0.0
