"""Shared helpers for match-related rendering — map name extraction, etc.

PlayerMatchStats stores the demo filename, not the map name. The map is
embedded in the filename in two formats:
    de_*/cs_*/ar_* prefix (community + matchmaking demos)
    bare map name (pro demo filenames like ``m1-mirage.dem``)

``extract_map_name`` covers both. Returns ``"Unknown Map"`` when the
filename matches neither.
"""

from __future__ import annotations

import re

# Match the map prefix + alphanumeric body but STOP at the second
# underscore so demo filenames like ``match_de_mirage_2026-04-30`` yield
# ``de_mirage`` not ``de_mirage_2026``. ``[a-z0-9]+`` deliberately
# excludes ``_`` so the suffix never gets swallowed.
_MAP_PATTERN = re.compile(r"(de_[a-z0-9]+|cs_[a-z0-9]+|ar_[a-z0-9]+)")
# map-SSOT (CP0 #2): the authority lives in core.known_maps.
from Programma_CS2_RENAN.core.known_maps import KNOWN_MAP_NAMES as _KNOWN_MAPS


def extract_map_name(demo_name: str) -> str:
    """Return the map id (``de_mirage``) embedded in a demo filename."""
    if not demo_name:
        return "Unknown Map"
    m = _MAP_PATTERN.search(demo_name)
    if m:
        return m.group(1)
    demo_lower = demo_name.lower()
    for known in _KNOWN_MAPS:
        if known in demo_lower:
            return f"de_{known}"
    return "Unknown Map"


def map_short_name(demo_name: str) -> str:
    """Return the bare map name with prefix stripped (``mirage``)."""
    full = extract_map_name(demo_name)
    if full == "Unknown Map":
        return "—"
    if "_" in full:
        return full.split("_", 1)[1]
    return full


def count_personal_and_pro(matches: list[dict]) -> tuple[int, int]:
    """(personal row count, DISTINCT pro demo count) for a matches payload.

    Personal counts loaded rows; pro counts distinct ``demo_name`` values
    across ``is_pro`` rows — PlayerMatchStats stores one row per
    (demo, player), so raw pro rows would inflate ~10× per demo. Shared by
    the Home matches chip and the Match History header caption.
    """
    personal = sum(1 for m in matches if not m.get("is_pro"))
    pro_demos = {m["demo_name"] for m in matches if m.get("is_pro") and m.get("demo_name")}
    return personal, len(pro_demos)
