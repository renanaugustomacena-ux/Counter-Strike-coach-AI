"""OI-2 — resolve a demo's REAL match date with an honest provenance marker.

``PlayerMatchStats.match_date`` historically defaulted to ``datetime.now()``
(ingestion wall-clock), so the "chronological anti-leak" split actually
ordered by ingestion order. This resolver derives the best available true
date and names its source, so downstream consumers can tell real chronology
from ingestion order.

Resolution ladder (best first):

  1. ``filename_date``  — an 8-digit YYYYMMDD token in the demo name
                          (e.g. ``demo_mirage_20240615``)
  2. ``filename_year``  — a leading ``YYYY-`` HLTV-archive prefix
                          (e.g. ``2023-natus-vincere-vs-faze-m1-inferno``);
                          coarse (Jan 1 of that year)
  3. ``file_mtime``     — the .dem file's modification time (destroyed by
                          copies/moves — weakest real signal)
  4. ``ingested_at``    — now(); NOT a match date. Splits treat rows with
                          this source as ingestion-ordered.

An ``hltv_event_date`` rung (ProEvent.start_date join) exists only in
``tools/backfill_match_dates.py`` — it needs the populated hltv_metadata.db
on the data box.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

# Provenance markers, strongest to weakest.
SOURCE_FILENAME_DATE = "filename_date"
SOURCE_FILENAME_YEAR = "filename_year"
SOURCE_FILE_MTIME = "file_mtime"
SOURCE_INGESTED_AT = "ingested_at"

# Sources that carry real (if coarse) match chronology. Everything else is
# ingestion-ordered.
CHRONOLOGICAL_SOURCES = frozenset({SOURCE_FILENAME_DATE, SOURCE_FILENAME_YEAR, "hltv_event_date"})

# CS:GO/CS2 era sanity bounds for parsed dates.
_MIN_YEAR = 2012
_MAX_YEAR = 2035

_DATE_TOKEN_RE = re.compile(r"(?:^|[^0-9])((?:19|20)\d{6})(?:[^0-9]|$)")
_YEAR_PREFIX_RE = re.compile(r"^((?:19|20)\d{2})-")


def _parse_date_token(demo_name: str) -> Optional[datetime]:
    for match in _DATE_TOKEN_RE.finditer(demo_name):
        token = match.group(1)
        try:
            dt = datetime.strptime(token, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if _MIN_YEAR <= dt.year <= _MAX_YEAR:
            return dt
    return None


def _parse_year_prefix(demo_name: str) -> Optional[datetime]:
    match = _YEAR_PREFIX_RE.match(demo_name)
    if not match:
        return None
    year = int(match.group(1))
    if _MIN_YEAR <= year <= _MAX_YEAR:
        return datetime(year, 1, 1, tzinfo=timezone.utc)
    return None


def resolve_match_date(demo_name: str, dem_path: Optional[Path] = None) -> Tuple[datetime, str]:
    """Return ``(match_date_utc, source)`` for a demo (see module docstring)."""
    dt = _parse_date_token(demo_name)
    if dt is not None:
        return dt, SOURCE_FILENAME_DATE

    dt = _parse_year_prefix(demo_name)
    if dt is not None:
        return dt, SOURCE_FILENAME_YEAR

    if dem_path is not None:
        try:
            path = Path(dem_path)
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if _MIN_YEAR <= mtime.year <= _MAX_YEAR:
                    return mtime, SOURCE_FILE_MTIME
        except OSError:
            pass

    return datetime.now(timezone.utc), SOURCE_INGESTED_AT
