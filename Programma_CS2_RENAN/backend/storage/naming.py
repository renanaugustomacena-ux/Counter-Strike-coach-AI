"""Player-name normalisation (§2.4, D-08).

roundstats names are lower-stripped at ingestion; playermatchstats and
playertickstate preserve the original spelling.  Every join must go
through normalisation to avoid the 46 % miss rate measured on the corpus
(docs/research/name_join_coverage_2026-09-05.json).
"""

from __future__ import annotations

import math
import sqlite3
from typing import Union

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.storage.naming")

_RESOLVE_LIMIT = 64


def normalize_player_name(name: Union[str, float, None]) -> str:
    """Canonical form: ``str(name).strip().casefold()``, None/NaN → ``""``."""
    if name is None:
        return ""
    if isinstance(name, float) and math.isnan(name):
        return ""
    return str(name).strip().casefold()


def resolve_stored_names(
    conn: sqlite3.Connection,
    demo_name: str,
) -> dict[str, str]:
    """Map *normalised* player name → first stored spelling for *demo_name*.

    Primary source is ``playermatchstats``; if that yields an empty
    mapping the ``playertickstate`` table is tried once (LIMIT bounded).
    When two stored names collapse to the same normalised key a WARNING
    is emitted and the first row wins.
    """
    mapping: dict[str, str] = {}

    rows = conn.execute(
        "SELECT DISTINCT player_name FROM playermatchstats " "WHERE demo_name = ?",
        (demo_name,),
    ).fetchall()

    if not rows:
        rows = conn.execute(
            "SELECT DISTINCT player_name FROM playertickstate " "WHERE demo_name = ? LIMIT ?",
            (demo_name, _RESOLVE_LIMIT),
        ).fetchall()

    for (raw_name,) in rows:
        key = normalize_player_name(raw_name)
        if key in mapping:
            logger.warning(
                "Collision: %r and %r both normalise to %r for demo %s; " "keeping %r",
                mapping[key],
                raw_name,
                key,
                demo_name,
                mapping[key],
            )
            continue
        mapping[key] = raw_name

    return mapping


def resolve_name(
    mapping: dict[str, str],
    name: Union[str, float, None],
) -> str:
    """Look up the stored spelling for *name*; fall back to normalised form."""
    key = normalize_player_name(name)
    return mapping.get(key, key)
