"""GAP-03 regression tests for trade-kill response timing.

The trade_kill_detector already computes per-trade `response_ticks`; the gap
was that nothing persisted that value to PlayerMatchStats.avg_trade_response_ticks.
This module verifies:

- `_integrate_trade_kills` accumulates response_ticks into each trader's
  per-round stat dict under `trade_response_ticks_sum` + `trade_response_count`.
- `aggregate_round_stats_to_match` emits `avg_trade_response_ticks` from
  those accumulators.
- Missing trades → avg_trade_response_ticks defaults to 0.0 (schema default).
- Multi-trade averaging is correct across rounds.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from Programma_CS2_RENAN.backend.data_sources.trade_kill_detector import TradeKillResult
from Programma_CS2_RENAN.backend.processing.round_stats_builder import (
    _integrate_trade_kills,
    aggregate_round_stats_to_match,
)


def _make_round_player_stats(players_per_round):
    """Build a minimal round_player_stats dict with the fields _integrate_trade_kills
    reads/writes. players_per_round: {round_num: [player_names_lower]}.
    """
    d = {}
    for rn, players in players_per_round.items():
        for p in players:
            d[(rn, p)] = {
                "demo_name": "astralis-vs-furia-m1-overpass",
                "round_number": rn,
                "player_name": p,
                "side": "CT",
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "damage_dealt": 0,
                "headshot_kills": 0,
                "trade_kills": 0,
                "was_traded": False,
                "trade_response_ticks_sum": 0,
                "trade_response_count": 0,
                "thrusmoke_kills": 0,
                "wallbang_kills": 0,
                "noscope_kills": 0,
                "blind_kills": 0,
                "opening_kill": False,
                "opening_death": False,
                "he_damage": 0.0,
                "molotov_damage": 0.0,
                "flashes_thrown": 0,
                "smokes_thrown": 0,
                "flash_assists": 0,
                "blind_time_on_enemies": 0.0,
                "enemies_blinded": set(),
                "equipment_value": 0,
                "round_won": False,
                "mvp": False,
                "kast": False,
                "round_rating": None,
            }
    return d


def _patched_analyze_demo_trades(trade_details):
    """Return a context patching analyze_demo_trades to yield given details."""
    result = TradeKillResult(
        total_kills=len(trade_details) * 2,
        trade_kills=len(trade_details),
        players_traded=len(trade_details),
        trade_details=trade_details,
    )
    return patch(
        "Programma_CS2_RENAN.backend.data_sources.trade_kill_detector.analyze_demo_trades",
        return_value=(result, {}),
    )


def test_integrate_trade_kills_accumulates_response_ticks():
    rps = _make_round_player_stats({1: ["alice", "bob"]})
    details = [
        {
            "round": 1,
            "trade_killer": "alice",
            "original_killer": "carol",  # enemy who killed bob
            "original_victim": "bob",
            "trade_tick": 1100,
            "original_tick": 1000,
            "response_ticks": 100,
        }
    ]
    with _patched_analyze_demo_trades(details):
        _integrate_trade_kills(parser=MagicMock(), round_player_stats=rps)

    assert rps[(1, "alice")]["trade_kills"] == 1
    assert rps[(1, "alice")]["trade_response_ticks_sum"] == 100
    assert rps[(1, "alice")]["trade_response_count"] == 1
    assert rps[(1, "bob")]["was_traded"] is True


def test_integrate_skips_zero_or_negative_response_ticks():
    """Degenerate cases (simultaneous tick, out-of-order data) must not
    pollute the average — count stays 0 so aggregation returns 0.0."""
    rps = _make_round_player_stats({1: ["alice", "bob"]})
    details = [
        {
            "round": 1,
            "trade_killer": "alice",
            "original_killer": "carol",
            "original_victim": "bob",
            "trade_tick": 1000,
            "original_tick": 1000,  # same tick
            "response_ticks": 0,
        }
    ]
    with _patched_analyze_demo_trades(details):
        _integrate_trade_kills(parser=MagicMock(), round_player_stats=rps)

    assert rps[(1, "alice")]["trade_kills"] == 1  # still counted
    assert rps[(1, "alice")]["trade_response_ticks_sum"] == 0
    assert rps[(1, "alice")]["trade_response_count"] == 0


def test_aggregate_emits_avg_trade_response_ticks():
    rps = _make_round_player_stats({1: ["alice"], 2: ["alice"]})
    # Simulate two trades in different rounds: 100 ticks and 50 ticks → avg 75
    rps[(1, "alice")]["trade_kills"] = 1
    rps[(1, "alice")]["trade_response_ticks_sum"] = 100
    rps[(1, "alice")]["trade_response_count"] = 1
    rps[(1, "alice")]["kills"] = 1
    rps[(2, "alice")]["trade_kills"] = 1
    rps[(2, "alice")]["trade_response_ticks_sum"] = 50
    rps[(2, "alice")]["trade_response_count"] = 1
    rps[(2, "alice")]["kills"] = 1

    round_stats = list(rps.values())
    enrichment = aggregate_round_stats_to_match(round_stats, "alice")

    assert enrichment["avg_trade_response_ticks"] == pytest.approx(75.0)
    assert enrichment["trade_kill_ratio"] == pytest.approx(2 / 2)  # 2 trades / 2 kills


def test_aggregate_returns_zero_when_no_trades():
    """Player with kills but no trade kills → avg = 0.0 (schema default)."""
    rps = _make_round_player_stats({1: ["alice"]})
    rps[(1, "alice")]["kills"] = 3
    rps[(1, "alice")]["deaths"] = 1

    enrichment = aggregate_round_stats_to_match(list(rps.values()), "alice")

    assert enrichment["avg_trade_response_ticks"] == 0.0


def test_aggregate_averages_multi_trade_within_round():
    rps = _make_round_player_stats({1: ["alice"]})
    rps[(1, "alice")]["trade_kills"] = 3
    rps[(1, "alice")]["trade_response_ticks_sum"] = 60 + 80 + 100  # = 240
    rps[(1, "alice")]["trade_response_count"] = 3
    rps[(1, "alice")]["kills"] = 3

    enrichment = aggregate_round_stats_to_match(list(rps.values()), "alice")

    assert enrichment["avg_trade_response_ticks"] == pytest.approx(80.0)


def test_integrate_analyze_demo_trades_exception_logs_and_continues(caplog):
    import logging

    # Force analyze_demo_trades to raise. _integrate_trade_kills must swallow.
    rps = _make_round_player_stats({1: ["alice", "bob"]})
    with patch(
        "Programma_CS2_RENAN.backend.data_sources.trade_kill_detector.analyze_demo_trades",
        side_effect=RuntimeError("parser down"),
    ):
        # propagate the project logger so caplog can see it
        lg = logging.getLogger("cs2analyzer.round_stats_builder")
        prior = lg.propagate
        lg.propagate = True
        try:
            caplog.set_level(logging.WARNING, logger="cs2analyzer.round_stats_builder")
            _integrate_trade_kills(parser=MagicMock(), round_player_stats=rps)
        finally:
            lg.propagate = prior

    assert rps[(1, "alice")]["trade_response_count"] == 0
    assert any("skipped" in rec.message for rec in caplog.records)
