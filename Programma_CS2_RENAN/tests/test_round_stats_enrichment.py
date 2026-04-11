"""
Tests for round_stats_builder enrichment pipeline (Fusion Plan Phase 1).

Validates:
- aggregate_round_stats_to_match() with synthetic data
- Trade kill ratio, utility breakdown, kill enrichment calculations
- Flash assist detection logic
- Edge cases (zero kills, empty rounds, no events)
"""

import sys

import pytest

from Programma_CS2_RENAN.backend.processing.round_stats_builder import (
    aggregate_round_stats_to_match,
)


def _make_round_stat(
    player_name="testplayer",
    round_number=1,
    kills=2,
    deaths=1,
    assists=0,
    damage_dealt=150,
    headshot_kills=1,
    trade_kills=0,
    was_traded=False,
    thrusmoke_kills=0,
    wallbang_kills=0,
    noscope_kills=0,
    blind_kills=0,
    opening_kill=False,
    opening_death=False,
    he_damage=0.0,
    molotov_damage=0.0,
    flashes_thrown=0,
    smokes_thrown=0,
    flash_assists=0,
    round_won=True,
    blind_time_on_enemies=0.0,
    enemies_blinded=None,
):
    return {
        "demo_name": "test.dem",
        "round_number": round_number,
        "player_name": player_name,
        "side": "CT",
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "damage_dealt": damage_dealt,
        "headshot_kills": headshot_kills,
        "trade_kills": trade_kills,
        "was_traded": was_traded,
        "thrusmoke_kills": thrusmoke_kills,
        "wallbang_kills": wallbang_kills,
        "noscope_kills": noscope_kills,
        "blind_kills": blind_kills,
        "opening_kill": opening_kill,
        "opening_death": opening_death,
        "he_damage": he_damage,
        "molotov_damage": molotov_damage,
        "flashes_thrown": flashes_thrown,
        "smokes_thrown": smokes_thrown,
        "flash_assists": flash_assists,
        # Q1-01: Utility blind metrics — sum of enemy blind durations and the
        # set of distinct enemies blinded this round.
        "blind_time_on_enemies": blind_time_on_enemies,
        "enemies_blinded": set(enemies_blinded) if enemies_blinded else set(),
        "equipment_value": 4750,
        "round_won": round_won,
        "mvp": False,
        "round_rating": None,
    }


class TestAggregateRoundStatsToMatch:

    def test_basic_trade_kill_ratio(self):
        """Trade kill ratio = trade_kills / total_kills."""
        rounds = [
            _make_round_stat(kills=3, trade_kills=1),
            _make_round_stat(kills=2, trade_kills=1, round_number=2),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["trade_kill_ratio"] == pytest.approx(2 / 5)  # 2 trades / 5 kills

    def test_was_traded_ratio(self):
        """Was-traded ratio = rounds_where_traded / total_deaths."""
        rounds = [
            _make_round_stat(deaths=1, was_traded=True),
            _make_round_stat(deaths=1, was_traded=False, round_number=2),
            _make_round_stat(deaths=0, was_traded=False, round_number=3),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["was_traded_ratio"] == pytest.approx(1 / 2)  # 1 traded / 2 deaths

    def test_kill_enrichment_percentages(self):
        """Wallbang, thrusmoke, noscope, blind kill percentages."""
        rounds = [
            _make_round_stat(
                kills=4,
                wallbang_kills=1,
                thrusmoke_kills=1,
                noscope_kills=0,
                blind_kills=0,
            ),
            _make_round_stat(
                kills=6,
                wallbang_kills=1,
                thrusmoke_kills=0,
                noscope_kills=2,
                blind_kills=1,
                round_number=2,
            ),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        total = 10
        assert result["wallbang_kill_pct"] == pytest.approx(2 / total)
        assert result["thrusmoke_kill_pct"] == pytest.approx(1 / total)
        assert result["noscope_kill_pct"] == pytest.approx(2 / total)
        assert result["blind_kill_pct"] == pytest.approx(1 / total)

    def test_utility_breakdown(self):
        """HE/molotov damage per round, smokes per round."""
        rounds = [
            _make_round_stat(he_damage=30.0, molotov_damage=20.0, smokes_thrown=1),
            _make_round_stat(he_damage=50.0, molotov_damage=0.0, smokes_thrown=2, round_number=2),
            _make_round_stat(he_damage=0.0, molotov_damage=10.0, smokes_thrown=0, round_number=3),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["he_damage_per_round"] == pytest.approx(80.0 / 3)
        assert result["molotov_damage_per_round"] == pytest.approx(30.0 / 3)
        assert result["smokes_per_round"] == pytest.approx(3 / 3)

    def test_flash_assists(self):
        """Flash assists are summed across rounds."""
        rounds = [
            _make_round_stat(flash_assists=1),
            _make_round_stat(flash_assists=2, round_number=2),
            _make_round_stat(flash_assists=0, round_number=3),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["flash_assists"] == 3.0

    def test_opening_duel_win_pct(self):
        """Opening duel win % = opening_kills / (opening_kills + opening_deaths)."""
        rounds = [
            _make_round_stat(opening_kill=True, opening_death=False),
            _make_round_stat(opening_kill=False, opening_death=True, round_number=2),
            _make_round_stat(opening_kill=True, opening_death=False, round_number=3),
            _make_round_stat(opening_kill=False, opening_death=False, round_number=4),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["opening_duel_win_pct"] == pytest.approx(2 / 3)

    def test_zero_kills_no_division_error(self):
        """Zero kills should produce 0.0 ratios, not division errors."""
        rounds = [
            _make_round_stat(kills=0, trade_kills=0, wallbang_kills=0),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["trade_kill_ratio"] == 0.0
        assert result["wallbang_kill_pct"] == 0.0
        assert result["thrusmoke_kill_pct"] == 0.0
        assert result["noscope_kill_pct"] == 0.0
        assert result["blind_kill_pct"] == 0.0

    def test_empty_round_stats(self):
        """Empty round stats returns empty dict."""
        result = aggregate_round_stats_to_match([], "testplayer")
        assert result == {}

    def test_filters_by_player_name(self):
        """Only aggregates stats for the specified player."""
        rounds = [
            _make_round_stat(player_name="alice", kills=5, trade_kills=2),
            _make_round_stat(player_name="bob", kills=3, trade_kills=3),
        ]
        result_alice = aggregate_round_stats_to_match(rounds, "alice")
        result_bob = aggregate_round_stats_to_match(rounds, "bob")

        assert result_alice["trade_kill_ratio"] == pytest.approx(2 / 5)
        assert result_bob["trade_kill_ratio"] == pytest.approx(3 / 3)

    def test_no_opening_duels_no_key(self):
        """If player had no opening duels, opening_duel_win_pct is not in result."""
        rounds = [
            _make_round_stat(opening_kill=False, opening_death=False),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert "opening_duel_win_pct" not in result

    def test_utility_blind_time_sums_across_rounds(self):
        """utility_blind_time = sum of blind_time_on_enemies across all rounds."""
        rounds = [
            _make_round_stat(blind_time_on_enemies=1.5, enemies_blinded={"enemy_a"}),
            _make_round_stat(
                blind_time_on_enemies=2.3,
                enemies_blinded={"enemy_b", "enemy_c"},
                round_number=2,
            ),
            _make_round_stat(blind_time_on_enemies=0.0, round_number=3),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["utility_blind_time"] == pytest.approx(3.8)

    def test_utility_enemies_blinded_is_distinct_union(self):
        """utility_enemies_blinded = count of distinct enemies blinded across the match.

        The same enemy blinded in multiple rounds must count only once.
        """
        rounds = [
            _make_round_stat(enemies_blinded={"enemy_a", "enemy_b"}),
            _make_round_stat(
                enemies_blinded={"enemy_b", "enemy_c"}, round_number=2
            ),  # enemy_b is a duplicate
            _make_round_stat(enemies_blinded={"enemy_a"}, round_number=3),  # enemy_a duplicate
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        # Distinct union: {enemy_a, enemy_b, enemy_c} = 3
        assert result["utility_enemies_blinded"] == pytest.approx(3.0)

    def test_utility_blind_metrics_zero_when_no_blinds(self):
        """Missing blind data should produce 0.0, not raise."""
        rounds = [
            _make_round_stat(),  # no blind_time_on_enemies / enemies_blinded
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        assert result["utility_blind_time"] == 0.0
        assert result["utility_enemies_blinded"] == 0.0

    def test_utility_blind_metrics_per_player_isolation(self):
        """utility_blind_time/enemies_blinded must not leak between players."""
        rounds = [
            _make_round_stat(
                player_name="alice",
                blind_time_on_enemies=2.0,
                enemies_blinded={"x", "y"},
            ),
            _make_round_stat(
                player_name="bob",
                blind_time_on_enemies=1.0,
                enemies_blinded={"z"},
                round_number=2,
            ),
        ]
        alice = aggregate_round_stats_to_match(rounds, "alice")
        bob = aggregate_round_stats_to_match(rounds, "bob")
        assert alice["utility_blind_time"] == pytest.approx(2.0)
        assert alice["utility_enemies_blinded"] == pytest.approx(2.0)
        assert bob["utility_blind_time"] == pytest.approx(1.0)
        assert bob["utility_enemies_blinded"] == pytest.approx(1.0)

    def test_enrichment_keys_are_playermatchstats_fields(self):
        """All returned keys must correspond to PlayerMatchStats fields."""
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

        rounds = [
            _make_round_stat(
                kills=3,
                trade_kills=1,
                wallbang_kills=1,
                he_damage=20.0,
                flash_assists=1,
                opening_kill=True,
            ),
        ]
        result = aggregate_round_stats_to_match(rounds, "testplayer")
        pms_fields = set(PlayerMatchStats.model_fields.keys())

        for key in result:
            assert key in pms_fields, f"Enrichment key '{key}' not in PlayerMatchStats"


class TestEnrichFromDemoImport:
    """Verify that the enrich_from_demo function is importable and has correct signature."""

    def test_import(self):
        from Programma_CS2_RENAN.backend.processing.round_stats_builder import enrich_from_demo

        assert callable(enrich_from_demo)

    def test_event_registry_import(self):
        from Programma_CS2_RENAN.backend.data_sources.event_registry import (
            EVENT_REGISTRY,
            get_coverage_report,
        )

        assert "player_blind" in EVENT_REGISTRY
        assert EVENT_REGISTRY["player_blind"].implemented is True

    def test_trade_kill_detector_import(self):
        from Programma_CS2_RENAN.backend.data_sources.trade_kill_detector import (
            TradeKillResult,
            analyze_demo_trades,
            detect_trade_kills,
        )

        assert callable(detect_trade_kills)
        assert callable(analyze_demo_trades)
