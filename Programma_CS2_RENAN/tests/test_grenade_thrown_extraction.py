"""GAP-02 regression tests for grenade_thrown event extraction.

Covers:
- Unit: mocked DemoParser emits grenade_thrown rows → correct MatchEventState
  objects built, throw origin resolved from tick state.
- Unit: weapon field passes through (smokegrenade, molotov, flashbang…).
- Unit: missing player name (no steamid match + no user_name) → row skipped.
- Integration (opt-in): real overpass demo → thrown count > 0 AND
  thrown ≥ (smoke_start + molotov_start + flash_detonate + he_detonate)
  minus the grace window for nades never detonating (round-end truncation).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

_OVERPASS = Path(
    "/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/"
    "DEMO_PRO_PLAYERS/astralis-vs-furia-m1-overpass.dem"
)


def _make_df_ticks():
    """Minimal df_ticks with X/Y/Z + state columns needed by _lookup_state."""
    return pd.DataFrame(
        [
            {
                "tick": 1000,
                "player_name": "HooXi",
                "player_steamid": 76561197998926770,
                "team_name": "Astralis",
                "health": 100,
                "armor": 100,
                "equipment_value": 4700,
                "X": 512.0,
                "Y": -128.0,
                "Z": 64.5,
            },
            {
                "tick": 2000,
                "player_name": "Staehr",
                "player_steamid": 76561198005107817,
                "team_name": "Astralis",
                "health": 88,
                "armor": 83,
                "equipment_value": 5100,
                "X": -400.0,
                "Y": 700.0,
                "Z": 32.0,
            },
        ]
    )


def _fake_parse_events_factory(grenade_thrown_df):
    """Return a parse_events(list) side-effect that yields only grenade_thrown
    rows and empty frames for every other event type requested.
    """

    def _side(event_list):
        if event_list == ["grenade_thrown"]:
            return [("grenade_thrown", grenade_thrown_df)]
        # Any other event list → empty frame tuple list
        return [(name, pd.DataFrame()) for name in event_list]

    return _side


@pytest.fixture
def mock_match_manager():
    mgr = MagicMock()
    mgr.captured_events = []

    def _store(match_id, events):
        mgr.captured_events.extend(events)
        return len(events)

    mgr.store_event_batch.side_effect = _store
    return mgr


def test_grenade_thrown_builds_matcheventstate(mock_match_manager):
    """mocked parser → grenade_thrown rows produce MatchEventState with
    weapon, tick, player, and throw-origin position sourced from tick state."""
    from Programma_CS2_RENAN.run_ingestion import _extract_and_store_events

    thrown = pd.DataFrame(
        [
            {
                "tick": 1000,
                "user_name": "HooXi",
                "user_steamid": 76561197998926770,
                "weapon": "smokegrenade",
            },
            {
                "tick": 2000,
                "user_name": "Staehr",
                "user_steamid": 76561198005107817,
                "weapon": "molotov",
            },
        ]
    )
    df_ticks = _make_df_ticks()

    mock_parser = MagicMock()
    mock_parser.parse_events.side_effect = _fake_parse_events_factory(thrown)
    with patch("demoparser2.DemoParser", MagicMock(return_value=mock_parser)):
        _extract_and_store_events(
            demo_path="fake.dem",
            match_id=1,
            match_manager=mock_match_manager,
            df_ticks=df_ticks,
        )

    thrown_evts = [
        e for e in mock_match_manager.captured_events if e.event_type == "grenade_thrown"
    ]
    assert len(thrown_evts) == 2

    smoke = next(e for e in thrown_evts if e.weapon == "smokegrenade")
    assert smoke.tick == 1000
    assert smoke.player_name == "HooXi"
    assert smoke.player_team == "Astralis"
    # Throw origin sourced from tick state (X=512.0, Y=-128.0, Z=64.5)
    assert smoke.pos_x == pytest.approx(512.0)
    assert smoke.pos_y == pytest.approx(-128.0)
    assert smoke.pos_z == pytest.approx(64.5)

    molotov = next(e for e in thrown_evts if e.weapon == "molotov")
    assert molotov.tick == 2000
    assert molotov.player_name == "Staehr"
    assert molotov.pos_x == pytest.approx(-400.0)


def test_grenade_thrown_skips_rows_with_unresolvable_player(mock_match_manager):
    """If steamid is unknown and user_name is empty, row is skipped (no
    bogus empty-string player rows pollute the event table)."""
    from Programma_CS2_RENAN.run_ingestion import _extract_and_store_events

    thrown = pd.DataFrame(
        [
            {
                "tick": 5000,
                "user_name": "",
                "user_steamid": 42,  # not in sid_to_name
                "weapon": "flashbang",
            },
            {
                "tick": 1000,
                "user_name": "HooXi",
                "user_steamid": 76561197998926770,
                "weapon": "hegrenade",
            },
        ]
    )

    mock_parser = MagicMock()
    mock_parser.parse_events.side_effect = _fake_parse_events_factory(thrown)
    with patch("demoparser2.DemoParser", MagicMock(return_value=mock_parser)):
        _extract_and_store_events("fake.dem", 1, mock_match_manager, _make_df_ticks())

    thrown_evts = [
        e for e in mock_match_manager.captured_events if e.event_type == "grenade_thrown"
    ]
    # Only HooXi's HE is kept — unresolvable row dropped.
    assert len(thrown_evts) == 1
    assert thrown_evts[0].weapon == "hegrenade"


def test_grenade_thrown_survives_parser_exception(mock_match_manager):
    """If demoparser2 raises on grenade_thrown, the block logs a warning and
    continues — does not abort the whole event pipeline."""
    from Programma_CS2_RENAN.run_ingestion import _extract_and_store_events

    def _side(event_list):
        if event_list == ["grenade_thrown"]:
            raise RuntimeError("parser blew up")
        return [(name, pd.DataFrame()) for name in event_list]

    mock_parser = MagicMock()
    mock_parser.parse_events.side_effect = _side
    with patch("demoparser2.DemoParser", MagicMock(return_value=mock_parser)):
        # Should not raise
        _extract_and_store_events("fake.dem", 1, mock_match_manager, _make_df_ticks())

    # No grenade_thrown events captured, but function returned normally.
    thrown_evts = [
        e for e in mock_match_manager.captured_events if e.event_type == "grenade_thrown"
    ]
    assert thrown_evts == []


@pytest.mark.integration
def test_real_overpass_thrown_geq_detonated():
    """Real-demo invariant: every detonated nade must have been thrown,
    so thrown count ≥ sum(detonate + start) events. Allows a margin for
    round-end truncation where thrown nades never detonate.
    """
    if os.environ.get("CS2_INTEGRATION_TESTS") != "1":
        pytest.skip("Requires CS2_INTEGRATION_TESTS=1 and real demo")
    if not _OVERPASS.exists():
        pytest.skip(f"canonical test demo missing at {_OVERPASS}")

    from demoparser2 import DemoParser

    p = DemoParser(str(_OVERPASS))
    thrown_res = p.parse_events(["grenade_thrown"])
    thrown_df = thrown_res[0][1] if thrown_res else pd.DataFrame()
    thrown_count = len(thrown_df)

    # Count detonate/startburn events across grenade families
    det_count = 0
    for evts in [
        ["smokegrenade_detonate"],
        ["inferno_startburn"],
        ["flashbang_detonate"],
        ["hegrenade_detonate"],
    ]:
        r = p.parse_events(evts)
        if r:
            for _, df in r:
                det_count += len(df)

    assert thrown_count > 0, "Expected grenade_thrown events on overpass demo"
    # thrown ≥ detonated is the physical invariant (a detonation implies a
    # prior throw). Parser may split incendiary vs molotov and still the
    # invariant holds because every detonation maps to exactly one throw.
    assert thrown_count >= det_count, (
        f"thrown={thrown_count} < detonated={det_count}; physical invariant "
        "violated — investigate demoparser2 schema change."
    )
