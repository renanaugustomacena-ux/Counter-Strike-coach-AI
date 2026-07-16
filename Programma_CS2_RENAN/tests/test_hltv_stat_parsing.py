"""HLTV numeric parsing contract (R4 HIGH fix, 2026-07-16).

``_safe_float`` blindly mapped every comma to a decimal point, so HLTV's
thousands-separated counters ("39,606" rounds played) collapsed to 39.606
→ int 39, silently poisoning every ratio built on them. These tests pin
the disambiguation: digit-grouped commas are thousands separators; a lone
comma stays a decimal separator (legacy behaviour).
"""

import pytest

from Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher import HLTVStatFetcher


def _fetcher():
    # __init__ wires network/session state we don't need for pure parsing.
    return HLTVStatFetcher.__new__(HLTVStatFetcher)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Thousands-grouped counters (the R4 HIGH corruption class)
        ("39,606", 39606.0),
        ("2,642", 2642.0),
        ("12,345", 12345.0),
        ("1,234.5", 1234.5),
        ("1,234,567", 1234567.0),
        # Decimal comma (legacy behaviour preserved)
        ("0,85", 0.85),
        ("12,34", 12.34),
        # Plain values
        ("0.85", 0.85),
        ("1.3", 1.3),
        ("847", 847.0),
        # Percent suffix
        ("71.2%", 71.2),
        ("46,3%", 46.3),
        # Missing / sentinel values
        ("-", 0.0),
        ("N/A", 0.0),
        ("nan", 0.0),
        ("", 0.0),
        (None, 0.0),
        # Garbage stays 0.0, never raises
        ("abc", 0.0),
        ("%", 0.0),
    ],
)
def test_safe_float(raw, expected):
    assert _fetcher()._safe_float(raw) == pytest.approx(expected)
