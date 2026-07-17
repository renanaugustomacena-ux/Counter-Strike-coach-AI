#!/usr/bin/env python3
"""
Repair dead tick features in playertickstate by re-reading .dem files.

Fixes 4 features that were incorrectly ingested:
  - is_crouching: demoparser2 field is "ducking", not "is_crouching"
  - is_blinded:   demoparser2 field is "flash_duration" (float > 0 means blinded)
  - has_helmet:   was never written to monolith (column was missing)
  - has_defuser:  was never written to monolith (column was missing)

Uses a temp-table + UPDATE FROM strategy per demo for bulk performance.
Does NOT delete or re-create rows — safe for roundstats/KAST linkage.

Usage:
    python tools/repair_tick_features.py
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Programma_CS2_RENAN.core.config import get_pro_demo_base

DEMO_BASE = get_pro_demo_base()
DB_PATH = str(PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db")

# Fields we need from demoparser2 to repair
_REPAIR_FIELDS = [
    "player_name",
    "ducking",  # → is_crouching
    "flash_duration",  # → is_blinded (> 0)
    "has_helmet",
    "has_defuser",
]


def _build_demo_path_map() -> dict:
    return {p.stem: p for p in DEMO_BASE.rglob("*.dem") if not p.is_symlink()}


def _run_repair_update(conn, demo_name: str, available: dict) -> None:
    """Apply the temp-table UPDATE FROM for one demo.

    ``available`` maps playertickstate column -> temp-table column for the
    fields the parser actually returned. The monolith stores player_name in
    the ORIGINAL case from the parser ("ZywOo", "apEX"); the temp table is
    lower+strip. An exact join here silently skipped every mixed-case
    player (~half the monolith), so join on LOWER(TRIM()) instead.
    """
    set_clause = ", ".join(f"{col} = r.{tmp}" for col, tmp in available.items())
    conn.execute(
        f"""
        UPDATE playertickstate
        SET {set_clause}
        FROM _repair r
        WHERE playertickstate.demo_name = ?
          AND LOWER(TRIM(playertickstate.player_name)) = r.player_name
          AND playertickstate.tick = r.tick
    """,
        (demo_name,),
    )


def main() -> None:
    import sqlite3

    import pandas as pd
    from demoparser2 import DemoParser

    from Programma_CS2_RENAN.backend.storage.database import init_database

    print("=== Tick Feature Repair (temp-table strategy) ===", flush=True)

    init_database()

    conn = sqlite3.connect(DB_PATH, timeout=120)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA cache_size=-200000")  # 200 MB

    demo_path_map = _build_demo_path_map()

    demo_names = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT demo_name FROM playertickstate ORDER BY demo_name"
        ).fetchall()
    ]
    print(f"Demos to repair: {len(demo_names)}\n", flush=True)

    total_updated = 0
    t_start = time.monotonic()

    for i, demo_name in enumerate(demo_names, 1):
        dem_path = demo_path_map.get(demo_name)
        if dem_path is None:
            print(f"[{i:02d}/{len(demo_names)}] SKIP (no .dem): {demo_name}", flush=True)
            continue

        t_demo = time.monotonic()
        print(f"[{i:02d}/{len(demo_names)}] {demo_name} ...", end=" ", flush=True)

        # Parse only the repair fields from the .dem file
        try:
            parser = DemoParser(str(dem_path))
            raw_ticks = parser.parse_ticks(_REPAIR_FIELDS)
            df = pd.DataFrame(raw_ticks)
        except Exception as e:
            print(f"PARSE ERROR: {e}", flush=True)
            continue

        if df.empty:
            print("empty", flush=True)
            continue

        # Compute corrected columns. ANTI-FABRICATION: a field the parser
        # did not return must NOT be "repaired" to a default — that would
        # overwrite the whole demo with fabricated zeros. Missing fields
        # are excluded from the UPDATE instead.
        df["player_name"] = df["player_name"].astype(str).str.strip().str.lower()
        available: dict = {}
        if "ducking" in df.columns:
            df["_cr"] = df["ducking"].astype(bool).astype(int)
            available["is_crouching"] = "_cr"
        if "flash_duration" in df.columns:
            df["_bl"] = (df["flash_duration"].astype(float) > 0).astype(int)
            available["is_blinded"] = "_bl"
        if "has_helmet" in df.columns:
            df["_hm"] = df["has_helmet"].astype(bool).astype(int)
            available["has_helmet"] = "_hm"
        if "has_defuser" in df.columns:
            df["_df"] = df["has_defuser"].astype(bool).astype(int)
            available["has_defuser"] = "_df"

        missing = {"is_crouching", "is_blinded", "has_helmet", "has_defuser"} - set(available)
        if missing:
            print(f"WARN missing parser fields, NOT repairing: {sorted(missing)} ...", end=" ")
        if not available:
            print("no repairable fields", flush=True)
            continue

        # Strategy: load into temp table, then UPDATE FROM (SQLite 3.33+)
        temp_cols = list(available.values())  # e.g. ["_cr", "_bl", ...]
        conn.execute("DROP TABLE IF EXISTS _repair")
        conn.execute(
            "CREATE TEMP TABLE _repair (player_name TEXT NOT NULL, tick INTEGER NOT NULL, "
            + ", ".join(f"{c} INTEGER NOT NULL" for c in temp_cols)
            + ")"
        )

        # Bulk INSERT into temp table
        repair_data = list(
            zip(df["player_name"], df["tick"].astype(int), *(df[c] for c in temp_cols))
        )
        conn.executemany(
            f"INSERT INTO _repair(player_name, tick, {', '.join(temp_cols)}) "
            f"VALUES ({', '.join('?' * (2 + len(temp_cols)))})",
            repair_data,
        )
        # Without this index the UPDATE FROM plans "SCAN r" as the inner loop:
        # O(demo_rows × temp_rows) — measured runaway (>40 min, days-scale
        # projection) on the 429M-row monolith. With it: indexed probes.
        conn.execute("CREATE INDEX _repair_idx ON _repair(player_name, tick)")

        # Single UPDATE FROM — joins on (player_name, tick) within this demo
        # (case/space-insensitive on the monolith side, see _run_repair_update).
        _run_repair_update(conn, demo_name, available)

        conn.execute("DROP TABLE _repair")
        conn.commit()

        # DL-1: Record provenance for tick feature repair
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager

        get_db_manager().record_lineage(
            entity_type="batch_tick_repair",
            entity_id=len(repair_data),
            source_demo=demo_name,
            processing_step="tick_feature_repair",
        )

        elapsed = time.monotonic() - t_demo
        print(f"{len(repair_data):,} ticks ({elapsed:.1f}s)", flush=True)
        total_updated += len(repair_data)

    conn.close()
    total_elapsed = time.monotonic() - t_start

    print(f"\n=== Done ({total_elapsed:.0f}s) ===", flush=True)
    print(f"  Total ticks processed: {total_updated:,}", flush=True)


if __name__ == "__main__":
    main()
