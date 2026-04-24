"""GAP-01 regression tests for _parse_demo_header_meta().

Covers:
- 64-tick demo (CS2 competitive default) → returns 64.0
- 128-tick demo (MR15 / pug / tournament) → returns 128.0
- Out-of-range tick_rate (e.g. 16, 512) → falls back to 64.0 + WARN
- Missing map_name / tick_rate keys → safe defaults
- Non-numeric tick_rate → fallback + WARN
- parse_header() raises → (de_unknown, 64.0) without propagating

The helper is pure given a mocked demoparser2.DemoParser, so tests do
not touch real .dem files.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from Programma_CS2_RENAN.run_ingestion import _parse_demo_header_meta


@pytest.fixture
def runner_log_propagate():
    """Project's get_logger() sets propagate=False, which hides records from
    pytest's caplog. Flip it on for the test and restore after.
    """
    lg = logging.getLogger("cs2analyzer.ingestion_runner")
    prior = lg.propagate
    lg.propagate = True
    try:
        yield
    finally:
        lg.propagate = prior


def _patch_parser(header_dict):
    """Return a ctx manager patching demoparser2.DemoParser to yield given header."""
    mock_instance = MagicMock()
    mock_instance.parse_header.return_value = header_dict
    mock_cls = MagicMock(return_value=mock_instance)
    return patch("demoparser2.DemoParser", mock_cls)


def test_64_tick_demo_returns_64():
    with _patch_parser({"map_name": "de_overpass", "tick_rate": 64}):
        assert _parse_demo_header_meta("dummy.dem") == ("de_overpass", 64.0)


def test_128_tick_demo_returns_128():
    with _patch_parser({"map_name": "de_mirage", "tick_rate": 128}):
        assert _parse_demo_header_meta("dummy.dem") == ("de_mirage", 128.0)


def test_float_tick_rate_is_preserved():
    # Some demos report tick_rate as float (e.g. subtick resampled output)
    with _patch_parser({"map_name": "de_nuke", "tick_rate": 64.0}):
        assert _parse_demo_header_meta("dummy.dem") == ("de_nuke", 64.0)


def test_below_range_falls_back(caplog, runner_log_propagate):
    caplog.set_level(logging.WARNING, logger="cs2analyzer.ingestion_runner")
    with _patch_parser({"map_name": "de_dust2", "tick_rate": 16}):
        name, tr = _parse_demo_header_meta("dummy.dem")
    assert (name, tr) == ("de_dust2", 64.0)
    assert any("GAP-01" in rec.message and "outside" in rec.message for rec in caplog.records)


def test_above_range_falls_back(caplog, runner_log_propagate):
    caplog.set_level(logging.WARNING, logger="cs2analyzer.ingestion_runner")
    with _patch_parser({"map_name": "de_ancient", "tick_rate": 512}):
        name, tr = _parse_demo_header_meta("dummy.dem")
    assert (name, tr) == ("de_ancient", 64.0)
    assert any("GAP-01" in rec.message for rec in caplog.records)


def test_non_numeric_tick_rate_falls_back(caplog, runner_log_propagate):
    caplog.set_level(logging.WARNING, logger="cs2analyzer.ingestion_runner")
    with _patch_parser({"map_name": "de_inferno", "tick_rate": "fast"}):
        name, tr = _parse_demo_header_meta("dummy.dem")
    assert (name, tr) == ("de_inferno", 64.0)
    assert any("not numeric" in rec.message for rec in caplog.records)


def test_missing_tick_rate_key_uses_default():
    with _patch_parser({"map_name": "de_anubis"}):
        assert _parse_demo_header_meta("dummy.dem") == ("de_anubis", 64.0)


def test_missing_map_name_uses_de_unknown():
    with _patch_parser({"tick_rate": 128}):
        assert _parse_demo_header_meta("dummy.dem") == ("de_unknown", 128.0)


def test_literal_unknown_map_coerced_to_de_unknown():
    with _patch_parser({"map_name": "unknown", "tick_rate": 64}):
        assert _parse_demo_header_meta("dummy.dem") == ("de_unknown", 64.0)


def test_parse_header_raises_returns_safe_defaults(caplog, runner_log_propagate):
    caplog.set_level(logging.WARNING, logger="cs2analyzer.ingestion_runner")
    mock_instance = MagicMock()
    mock_instance.parse_header.side_effect = RuntimeError("corrupt demo")
    mock_cls = MagicMock(return_value=mock_instance)
    with patch("demoparser2.DemoParser", mock_cls):
        assert _parse_demo_header_meta("corrupt.dem") == ("de_unknown", 64.0)
    assert any("Failed to read demo header" in rec.message for rec in caplog.records)


def test_tick_rate_zero_falls_back():
    # header key present but value is 0 / None — the `or 64` guard must kick in
    with _patch_parser({"map_name": "de_train", "tick_rate": 0}):
        # falsy → fallback via `or default_tr` → 64.0
        assert _parse_demo_header_meta("dummy.dem") == ("de_train", 64.0)


@pytest.mark.integration
def test_real_overpass_demo_header_if_present():
    """If the canonical test demo is available locally, parse its header
    and confirm the helper returns something sensible.

    Marked 'integration' and skipped unless CS2_INTEGRATION_TESTS=1.
    """
    import os
    from pathlib import Path

    if os.environ.get("CS2_INTEGRATION_TESTS") != "1":
        pytest.skip("Requires CS2_INTEGRATION_TESTS=1 and real demo")

    demo = Path(
        "/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/"
        "DEMO_PRO_PLAYERS/astralis-vs-furia-m1-overpass.dem"
    )
    if not demo.exists():
        pytest.skip(f"canonical test demo missing at {demo}")

    name, tr = _parse_demo_header_meta(demo)
    assert name.startswith("de_")
    assert 32.0 <= tr <= 256.0
