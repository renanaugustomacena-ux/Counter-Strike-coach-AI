"""Contract tests for the PlayerMatchStats ``rating_*`` column scale.

The columns carry RAW HLTV 2.0 components (rating_survival = 1-dpr,
rating_kast = kast ratio, rating_impact = HLTV impact, rating_kpr = kpr,
rating_adr = adr); baseline normalization happens ONLY inside the
``rating`` aggregate. pro_baseline.py, skill_assessment.py and
coach_manager.py all consume the raw scale.

History: aggregate_match_stats_sql once wrote baseline-normalized ratios
into these columns while demo_parser/base_features wrote raw values — the
same column meant two different things depending on which writer produced
the row, and every downstream Z-score against pro_baseline was silently
corrupted for tool-written rows. These tests pin all three writers to
rating.compute_rating_components so the scales can never diverge again.
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from Programma_CS2_RENAN.backend.processing.feature_engineering.kast import estimate_kast_from_stats
from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
    BASELINE_ADR,
    BASELINE_DPR_COMPLEMENT,
    BASELINE_KAST,
    BASELINE_KPR,
    compute_hltv2_rating,
    compute_impact_rating,
    compute_rating_components,
    compute_survival_rating,
)

# ─── SSOT: compute_rating_components ──────────────────────────────────


class TestComputeRatingComponents:
    def test_components_are_raw_scale_at_pro_baseline(self):
        """At formula-baseline inputs the raw components equal the inputs,
        NOT 1.0 ratios — that is the whole point of the contract."""
        c = compute_rating_components(
            kpr=BASELINE_KPR,
            dpr=1.0 - BASELINE_DPR_COMPLEMENT,
            kast=BASELINE_KAST,
            avg_adr=BASELINE_ADR,
        )
        assert c["rating_kpr"] == pytest.approx(BASELINE_KPR)
        assert c["rating_survival"] == pytest.approx(BASELINE_DPR_COMPLEMENT)
        assert c["rating_kast"] == pytest.approx(BASELINE_KAST)
        assert c["rating_adr"] == pytest.approx(BASELINE_ADR)

    def test_impact_includes_survival_penalty(self):
        """rating_impact must be the dpr-aware ('true') impact."""
        c = compute_rating_components(kpr=0.7, dpr=0.6, kast=0.72, avg_adr=80.0)
        assert c["rating_impact"] == pytest.approx(compute_impact_rating(0.7, 80.0, dpr=0.6))
        # And strictly below the dpr-less variant (which omits the penalty).
        assert c["rating_impact"] < compute_impact_rating(0.7, 80.0)

    def test_aggregate_matches_compute_hltv2_rating(self):
        c = compute_rating_components(kpr=0.7, dpr=0.6, kast=0.72, avg_adr=80.0)
        assert c["rating"] == pytest.approx(
            compute_hltv2_rating(
                kpr=0.7, dpr=0.6, kast=0.72, avg_adr=80.0, impact=c["rating_impact"]
            )
        )

    def test_survival_is_raw_not_normalized(self):
        """A prior draft divided by BASELINE_DPR_COMPLEMENT — assert it never
        comes back."""
        c = compute_rating_components(kpr=0.7, dpr=0.5, kast=0.72, avg_adr=80.0)
        assert c["rating_survival"] == pytest.approx(0.5)
        assert c["rating_survival"] != pytest.approx(0.5 / BASELINE_DPR_COMPLEMENT)

    def test_kast_is_raw_not_normalized(self):
        c = compute_rating_components(kpr=0.7, dpr=0.5, kast=0.84, avg_adr=80.0)
        assert c["rating_kast"] == pytest.approx(0.84)
        assert c["rating_kast"] != pytest.approx(0.84 / BASELINE_KAST)

    def test_survival_uses_canonical_helper(self):
        c = compute_rating_components(kpr=0.7, dpr=0.35, kast=0.72, avg_adr=80.0)
        assert c["rating_survival"] == pytest.approx(compute_survival_rating(0.35))


# ─── Parity: demo_parser vectorized path ──────────────────────────────


class TestDemoParserParity:
    """demo_parser._apply_hltv2_columns is a vectorized replica of the SSOT.
    Any drift between the two is a data-corruption bug."""

    @pytest.fixture
    def totals(self):
        return pd.DataFrame(
            {
                "player_name": ["pro", "average", "weak"],
                "avg_kills": [0.85, 0.679, 0.45],
                "avg_deaths": [0.50, 0.683, 0.95],
                "avg_adr": [95.0, 73.3, 48.0],
                "avg_kast": [0.82, 0.70, 0.55],
            }
        )

    def test_columns_match_ssot_row_by_row(self, totals):
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import _apply_hltv2_columns

        out = _apply_hltv2_columns(totals.copy())
        for _, row in out.iterrows():
            expected = compute_rating_components(
                kpr=row["avg_kills"],
                dpr=row["avg_deaths"],
                kast=row["avg_kast"],
                avg_adr=row["avg_adr"],
            )
            for key in (
                "rating_kpr",
                "rating_survival",
                "rating_kast",
                "rating_impact",
                "rating_adr",
                "rating",
            ):
                assert row[key] == pytest.approx(expected[key], rel=1e-9), (
                    f"{row['player_name']}: {key} diverged from SSOT "
                    f"({row[key]} vs {expected[key]})"
                )

    def test_impact_rounds_is_not_aliased_to_rating_impact(self, totals):
        """R4 (impact_rounds contract): the legacy alias wrote the HLTV
        impact RATING (~1.1-1.8) into impact_rounds, whose canonical
        semantics are the SHARE of rounds with >=1 kill ([0, 1] — what the
        SQL aggregator writes and what every baseline consumer assumes).
        The HLTV block must leave impact_rounds alone."""
        from Programma_CS2_RENAN.backend.data_sources.demo_parser import _apply_hltv2_columns

        df = totals.copy()
        df["impact_rounds"] = [0.6, 0.5, 0.3]  # share written by the caller
        out = _apply_hltv2_columns(df)
        assert out["impact_rounds"].tolist() == [0.6, 0.5, 0.3]
        assert not (out["impact_rounds"] == out["rating_impact"]).any()


# ─── Parity: aggregate_match_stats_sql builder ────────────────────────


class TestAggregateBuilderParity:
    """_build_player_match_stats must persist the SSOT raw components."""

    @staticmethod
    def _synthetic_inputs():
        rounds = 24
        kills, deaths, assists, damage, hs_kills = 20, 15, 5, 1800, 9
        meta = {
            "round_count": rounds,
            "is_pro_match": False,
            "demo_name": "synthetic-parity-check.dem",
            "match_date": datetime(2026, 7, 1, tzinfo=timezone.utc),
        }
        agg = {
            "player_name": "SyntheticPlayer",
            "steamid": "76561190000000000",
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "damage": damage,
            "hs_kills": hs_kills,
            "rounds_played": rounds,
            "kills_list": [1] * 20 + [0] * 4,
            "adr_list": [75.0] * 24,
            "enemies_blinded": 6,
            "he_dmg": 120,
            "molly_dmg": 80,
            "smoke_throws": 10,
            "trade_kills": 4,
            "was_traded": 3,
            "avg_trade_response_ticks": 180.0,
        }
        return meta, agg, rounds, kills, deaths, assists, damage

    def test_builder_matches_ssot(self, tmp_path):
        from Programma_CS2_RENAN.tools.aggregate_match_stats_sql import _build_player_match_stats

        meta, agg, rounds, kills, deaths, assists, damage = self._synthetic_inputs()
        record = _build_player_match_stats(meta, agg, tmp_path / "match_x.db")

        kpr = kills / rounds
        dpr = deaths / rounds
        kast = estimate_kast_from_stats(kills, assists, deaths, rounds)
        expected = compute_rating_components(kpr=kpr, dpr=dpr, kast=kast, avg_adr=damage / rounds)

        assert record.rating_kpr == pytest.approx(expected["rating_kpr"])
        assert record.rating_survival == pytest.approx(expected["rating_survival"])
        assert record.rating_kast == pytest.approx(expected["rating_kast"])
        assert record.rating_impact == pytest.approx(expected["rating_impact"])
        assert record.rating_adr == pytest.approx(expected["rating_adr"])
        assert record.rating == pytest.approx(expected["rating"])

    def test_builder_survival_is_raw(self, tmp_path):
        """Regression pin for the normalized-ratio draft: with dpr=0.625 the
        raw survival is 0.375; the broken draft wrote 0.375/0.317 ≈ 1.18."""
        from Programma_CS2_RENAN.tools.aggregate_match_stats_sql import _build_player_match_stats

        meta, agg, rounds, _, deaths, _, _ = self._synthetic_inputs()
        record = _build_player_match_stats(meta, agg, tmp_path / "match_x.db")
        assert record.rating_survival == pytest.approx(1.0 - deaths / rounds)
        assert record.rating_survival < 1.0
