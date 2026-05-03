#!/usr/bin/env python3
"""H1 migration — extend hltv_metadata.db schema for v3 plan.

hltv_metadata.db is intentionally outside Alembic management (alembic.ini
binds only database.db). Schema for the HLTV-side tables evolves via
SQLModel ``create_all()`` invoked by this idempotent one-off script.

What this migration adds (per v3 plan §11 H1):
  - ProEvent           — HLTV events (LAN tournaments, online cups, qualifiers)
  - ProTournament      — multi-event tournament series
  - ProHead2Head       — aggregate head-to-head between two pro teams
  - ProMapRecord       — per-team-or-player per-map performance

What this migration does NOT change:
  - Existing ProPlayer, ProTeam, ProPlayerStatCard schemas stay untouched.
    The v3 H2 scraper extension populates additional `detailed_stats_json`
    keys without schema changes (the field is already free-form JSON
    capped at 8 KB by ``ProPlayerStatCard.validate_detailed_stats_size``).
  - The ``time_span`` composite-uniqueness change for ProPlayerStatCard
    described in v3 plan §11 H1.2 is deferred to its own migration when
    the per-window backfill is actually attempted (Phase H3 / A1 of the
    v3 plan).

Idempotency:
  - SQLModel.metadata.create_all(checkfirst=True) skips existing tables.
  - Re-running this script is a no-op.

Usage:
  ./.venv/bin/python -m Programma_CS2_RENAN.tools.migrate_hltv_schema_2026_05

Concurrency:
  - Acquires the ``hltv_schema_migration`` lock so two concurrent runs
    cannot race on the same hltv_metadata.db.
  - Does NOT acquire ``d_track_running``; this migration touches the
    HLTV DB only and is safe to run while D-track is migrating ticks
    on database.db.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow direct script invocation by adding repo root to sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlmodel import SQLModel  # noqa: E402

from Programma_CS2_RENAN.core import lock_files  # noqa: E402


def _hltv_engine():
    """Get a SQLAlchemy engine bound to hltv_metadata.db.

    Reuses the existing manager so the engine config (PRAGMAs, pool, etc.)
    matches every other consumer of the HLTV DB.
    """
    from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager

    return get_hltv_db_manager().engine


def _existing_tables(engine) -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(engine).get_table_names())


def main() -> int:
    # CRITICAL: import only the 4 new HLTV-side tables and pass them
    # explicitly to create_all(). SQLModel.metadata is GLOBAL — it
    # contains every table defined anywhere (including main-DB tables
    # like playertickstate, playermatchstats, ingestiontask). Calling
    # create_all(engine) without a `tables` filter would create those
    # main-DB tables in hltv_metadata.db too, which violates the
    # long-standing separation principle ("HLTV DB is SEPARATE —
    # conflating them = trust below zero").
    from Programma_CS2_RENAN.backend.storage.db_models import (
        ProEvent,
        ProHead2Head,
        ProMapRecord,
        ProTournament,
    )

    new_table_classes = [ProEvent, ProTournament, ProHead2Head, ProMapRecord]
    new_table_objects = [cls.__table__ for cls in new_table_classes]

    lock_files.install_signal_handlers()
    with lock_files.lock("hltv_schema_migration"):
        engine = _hltv_engine()

        before = _existing_tables(engine)
        print("=== H1 migration — hltv_metadata.db schema extension ===")
        print(f"  Started:     {datetime.now(timezone.utc).isoformat()}")
        print(f"  Tables before: {sorted(before)}")

        # Only the 4 new tables. checkfirst=True makes create_all skip
        # tables that already exist; idempotent re-run path.
        SQLModel.metadata.create_all(
            engine,
            tables=new_table_objects,
            checkfirst=True,
        )

        after = _existing_tables(engine)
        added = sorted(after - before)
        unchanged = sorted(before & after)

        print(f"  Tables after:  {sorted(after)}")
        print(f"  Tables added:  {added}")
        print(f"  Tables kept:   {unchanged}")
        print(f"  Finished:    {datetime.now(timezone.utc).isoformat()}")

        # Verification: every expected new table is present, and NO
        # main-DB tables leaked in (separation principle).
        expected_new = {cls.__tablename__.lower() for cls in new_table_classes}
        missing = expected_new - {t.lower() for t in after}
        if missing:
            print(f"  FAILED: expected tables not created: {sorted(missing)}")
            return 2

        # Disallowed-leak guard: any main-DB table appearing here means
        # the script broke the separation principle.
        forbidden = {
            "playertickstate",
            "playermatchstats",
            "ingestiontask",
            "coachinginsight",
            "coachingexperience",
            "matchresult",
            "roundstats",
            "mapveto",
            "playerprofile",
            "coachstate",
            "calibrationsnapshot",
            "datalineage",
            "dataqualitymetric",
            "ext_playerplaystyle",
            "ext_teamroundstats",
            "rolethresholdrecord",
            "servicenotification",
            "tacticalknowledge",
        }
        leaked = forbidden & {t.lower() for t in after}
        if leaked:
            print(
                f"  FAILED (separation principle): main-DB tables leaked into hltv DB: {sorted(leaked)}"
            )
            return 3

        print("  Result: OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
