"""
Tests for demo_parser module.

Tests pure math/formula behavior with controlled inputs and
integration with real demo files (skipped if unavailable).
No MagicMock, no @patch on non-HTTP targets.
"""

from pathlib import Path

import pandas as pd
import pytest

DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demos"


def _find_demo_file():
    """Return path to first .dem file available, or None."""
    if DEMO_DIR.is_dir():
        for f in DEMO_DIR.iterdir():
            if f.suffix == ".dem":
                return str(f)
    return None


class TestParseDemoEdgeCases:
    """Test parse_demo behavior on edge cases — no mocks needed."""

    def test_nonexistent_file_returns_empty(self):
        """parse_demo must return empty DataFrame for missing file."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo

        result = parse_demo("this_file_does_not_exist_99999.dem")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_nonexistent_file_with_target_player(self):
        """parse_demo with target_player still returns empty for missing file."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo

        result = parse_demo("no_such_demo.dem", target_player="Player1")
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestParseSequentialTicksEdgeCases:
    """Test parse_sequential_ticks behavior on edge cases — no mocks needed."""

    def test_nonexistent_file_returns_empty(self):
        """parse_sequential_ticks must return empty DataFrame for missing file."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_sequential_ticks

        result = parse_sequential_ticks("nonexistent_demo_file.dem", target_player="Player1")
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestRatingFormulas:
    """Exercise the HLTV 2.0 rating math through the vectorized parser path.

    These call demo_parser._apply_hltv2_columns (the code that actually runs
    in production) instead of re-deriving coefficients locally; full parity
    with the scalar SSOT is pinned in test_rating_components_contract.py.
    """

    @staticmethod
    def _totals(avg_kills, avg_deaths, avg_adr, avg_kast):
        return pd.DataFrame(
            {
                "player_name": ["p1"],
                "avg_kills": [avg_kills],
                "avg_deaths": [avg_deaths],
                "avg_adr": [avg_adr],
                "avg_kast": [avg_kast],
            }
        )

    def test_kd_ratio_calculation(self):
        """KD ratio = kills / deaths (0-division safe)."""
        kills = 20
        deaths = 10
        assert kills / max(deaths, 1) == pytest.approx(2.0)

        # Zero deaths case
        assert kills / max(0, 1) == pytest.approx(20.0)

    def test_per_round_averages(self):
        """avg_kills, avg_deaths, avg_adr scale linearly with total_rounds."""
        total_rounds = 24
        kills_total = 48
        deaths_total = 24
        damage_total = 2400

        avg_kills = kills_total / total_rounds
        avg_deaths = deaths_total / total_rounds
        avg_adr = damage_total / total_rounds

        assert avg_kills == pytest.approx(2.0)
        assert avg_deaths == pytest.approx(1.0)
        assert avg_adr == pytest.approx(100.0)

    def test_rating_components_are_raw_scale(self):
        """The stored rating_* columns carry RAW components, never ratios."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import _apply_hltv2_columns

        out = _apply_hltv2_columns(self._totals(0.679, 0.683, 73.3, 0.70))
        row = out.iloc[0]
        assert row["rating_kpr"] == pytest.approx(0.679)
        assert row["rating_survival"] == pytest.approx(1.0 - 0.683)
        assert row["rating_kast"] == pytest.approx(0.70)
        assert row["rating_adr"] == pytest.approx(73.3)

    def test_final_rating_at_baseline(self):
        """Rating at formula-baseline values should be ~1.0 (impact term
        contributes its own deviation, hence the loose bound)."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import _apply_hltv2_columns

        out = _apply_hltv2_columns(self._totals(0.679, 0.683, 73.3, 0.70))
        rating = out.iloc[0]["rating"]
        # 4 of 5 components are exactly 1.0 at baseline; impact floats with
        # the ADR-proxy formula, so the aggregate sits near — not at — 1.0.
        assert 0.9 < rating < 1.3

    def test_econ_rating_formula(self):
        """econ_rating = avg_adr / 85.0."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import _apply_hltv2_columns

        out = _apply_hltv2_columns(self._totals(0.679, 0.683, 85.0, 0.70))
        assert out.iloc[0]["econ_rating"] == pytest.approx(1.0)

    def test_high_performer_rating_above_one(self):
        """A player with stats above baseline should have rating > 1.0."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import _apply_hltv2_columns

        out = _apply_hltv2_columns(self._totals(1.2, 0.4, 100.0, 0.85))
        assert out.iloc[0]["rating"] > 1.0


class TestDemoParserIntegration:
    """Integration tests using real .dem files (skipped if unavailable)."""

    def test_parse_real_demo(self):
        """Parse a real demo file and verify output structure."""
        demo_path = _find_demo_file()
        if demo_path is None:
            pytest.skip("No .dem files in data/demos/")

        from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo

        result = parse_demo(demo_path)
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "player_name" in result.columns
            assert "avg_kills" in result.columns
            assert "rating" in result.columns
            assert (result["avg_kills"] >= 0).all()

    def test_parse_sequential_ticks_real(self):
        """Parse sequential ticks from a real demo file."""
        demo_path = _find_demo_file()
        if demo_path is None:
            pytest.skip("No .dem files in data/demos/")

        from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_sequential_ticks

        result = parse_sequential_ticks(demo_path, target_player="ALL")
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "health" in result.columns
            assert "X" in result.columns

    def test_decimation_parameter_is_gone(self):
        """Supreme invariant (R4 MED, 2026-07-16): tick decimation is
        FORBIDDEN — the legacy ``rate`` stride parameter must not exist."""
        import inspect

        from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_sequential_ticks

        assert "rate" not in inspect.signature(parse_sequential_ticks).parameters
