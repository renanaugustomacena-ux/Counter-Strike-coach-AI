"""OI-2 — backfill real match dates + provenance onto playermatchstats.

Every historical PlayerMatchStats row carries an ingestion wall-clock
``match_date`` (no writer ever set it) — the "chronological" split was
really ingestion-ordered. This tool resolves a better date per demo via the
match_date_resolver ladder, plus an optional HLTV event-date rung when
hltv_metadata.db carries ProEvent rows whose name is contained in the demo
name (exact unique containment only — never a guess).

Only rows whose current provenance is 'ingested_at' (or NULL) are upgraded;
a real source is never overwritten by a weaker one.

Usage (on the machine holding the monolith — the Linux data box):
    python tools/backfill_match_dates.py            # dry-run report
    python tools/backfill_match_dates.py --apply    # write updates

After applying, re-run split assignment so boundaries follow real dates.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_script_dir = Path(__file__).parent.absolute()
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Programma_CS2_RENAN.backend.ingestion.match_date_resolver import (  # noqa: E402
    SOURCE_INGESTED_AT,
    resolve_match_date,
)

STORAGE_DIR = _project_root / "Programma_CS2_RENAN" / "backend" / "storage"
MONOLITH_DB = STORAGE_DIR / "database.db"
HLTV_DB = STORAGE_DIR / "hltv_metadata.db"

SOURCE_HLTV_EVENT = "hltv_event_date"

# Provenance values this tool may overwrite. Anything else is already a
# real source and is left alone.
_UPGRADABLE = {None, "", SOURCE_INGESTED_AT}


def _load_event_dates() -> list[tuple[str, datetime]]:
    """(normalized_event_name, start_date) pairs from hltv_metadata.db."""
    if not HLTV_DB.exists():
        return []
    try:
        with sqlite3.connect(f"file:{HLTV_DB}?mode=ro&immutable=1", uri=True) as conn:
            rows = conn.execute(
                "SELECT name, start_date FROM proevent WHERE start_date IS NOT NULL"
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    out = []
    for name, start in rows:
        if not name or not start:
            continue
        norm = "".join(c if c.isalnum() else "-" for c in str(name).lower())
        try:
            dt = datetime.fromisoformat(str(start))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        out.append((norm, dt))
    return out


def _hltv_event_date(demo_name: str, events: list[tuple[str, datetime]]):
    """Unique exact-containment match of an event slug in the demo name."""
    name = demo_name.lower()
    hits = [(slug, dt) for slug, dt in events if len(slug) >= 8 and slug in name]
    if len(hits) == 1:
        return hits[0][1]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Write updates (default: dry-run)")
    parser.add_argument("--db", type=Path, default=MONOLITH_DB, help="Monolith database path")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"[ABORT] monolith not found: {args.db}")
        return 2

    events = _load_event_dates()
    print(f"Match-date backfill — {args.db} ({'APPLY' if args.apply else 'dry-run'})")
    print(f"HLTV event-date rung: {len(events)} dated events available")

    if args.apply:
        conn = sqlite3.connect(args.db)
    else:
        # Dry-run must not create -wal/-shm side files on the monolith.
        conn = sqlite3.connect(f"file:{args.db}?mode=ro&immutable=1", uri=True)
    try:
        try:
            rows = conn.execute(
                "SELECT id, demo_name, match_date_source FROM playermatchstats"
            ).fetchall()
        except sqlite3.OperationalError as e:
            print(f"[ABORT] {e} — run `alembic upgrade head` first (a7b8c9d0e1f2)")
            return 2

        per_source: Counter = Counter()
        updates: list[tuple[str, str, int]] = []
        for row_id, demo_name, current_source in rows:
            if current_source not in _UPGRADABLE:
                per_source[f"kept:{current_source}"] += 1
                continue
            stem = Path(str(demo_name)).stem
            event_dt = _hltv_event_date(stem, events)
            if event_dt is not None:
                resolved, source = event_dt, SOURCE_HLTV_EVENT
            else:
                resolved, source = resolve_match_date(stem, None)
            per_source[source] += 1
            if source != SOURCE_INGESTED_AT:
                updates.append((resolved.isoformat(), source, row_id))

        print(f"Rows scanned: {len(rows)}")
        for source, count in sorted(per_source.items()):
            print(f"  {source}: {count}")
        print(f"Upgradable rows: {len(updates)}")

        if args.apply and updates:
            conn.executemany(
                "UPDATE playermatchstats SET match_date = ?, match_date_source = ? WHERE id = ?",
                updates,
            )
            conn.commit()
            print(f"[WRITE] {len(updates)} rows updated. Re-run split assignment next.")
        elif not args.apply:
            print("Dry-run complete. Re-run with --apply to write.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
