"""Known CS2 competitive maps — the single authority (map-SSOT, CP0 #2).

Pass 1 found TWELVE divergent known-map lists (8, 9 or 11 entries
depending on the file's age). Filename-derived map detection then
disagreed between tools: a demo named ``...-train-...`` was a known map
to match_utils but "de_unknown" to rebuild_monolith. This module is the
one list every "is this a known map?" check imports.

Deliberate NON-consumers (subsets with different semantics, not drift):
- Goliath/ui_diagnostic REQUIRED_MAPS — asset-presence probes over the
  radar-backed subset.
- spatial_data.SPATIAL_REGISTRY — maps with calibrated radar geometry.
"""

from __future__ import annotations

import re

# Bare names (no de_ prefix), superset of every list found in Pass 1.
KNOWN_MAP_NAMES: frozenset[str] = frozenset(
    {
        "mirage",
        "inferno",
        "dust2",
        "overpass",
        "ancient",
        "anubis",
        "nuke",
        "vertigo",
        "train",
        "cache",
        "office",
    }
)

# de_-prefixed ids (``de_mirage``) — the storage/display convention.
KNOWN_MAP_IDS: frozenset[str] = frozenset(f"de_{m}" for m in KNOWN_MAP_NAMES)

# Compiled alternation for filename sniffing (longest-first so e.g. a
# future "trainyard" can't be shadowed by "train").
MAP_NAME_RE: re.Pattern[str] = re.compile(
    "(" + "|".join(sorted(KNOWN_MAP_NAMES, key=len, reverse=True)) + ")"
)


def bare_name(map_id: str) -> str:
    """``de_mirage`` -> ``mirage`` (idempotent on bare names)."""
    return map_id[3:] if map_id.startswith("de_") else map_id


def is_known_map(name: str) -> bool:
    """True for either convention (``mirage`` or ``de_mirage``)."""
    return bare_name(str(name).lower()) in KNOWN_MAP_NAMES


def sniff_map_from_text(text: str) -> str | None:
    """First known map mentioned in ``text`` (demo filenames), else None."""
    m = MAP_NAME_RE.search(str(text).lower())
    return m.group(1) if m else None
