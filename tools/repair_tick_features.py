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

DEMO_BASE = Path("/media/renan/New Volume/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS")
DB_PATH = str(
    PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"
)

# Fields we need from demoparser2 to repair
_REPAIR_FIELDS = [
    "player_name",
    "ducking",        # → is_crouching
    "flash_duration", # → is_blinded (> 0)
    "has_helmet",
    "has_defuser",
]


def _build_demo_path_map() -> dict:
    return {p.stem: p for p in DEMO_BASE.rglob("*.dem")}


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

        # Compute corrected columns
        df["player_name"] = df["player_name"].astype(str).str.strip().str.lower()
        df["_cr"] = df.get("ducking", pd.Series(0, index=df.index)).astype(bool).astype(int)
        df["_bl"] = (df.get("flash_duration", pd.Series(0.0, index=df.index)).astype(float) > 0).astype(int)
        df["_hm"] = df.get("has_helmet", pd.Series(False, index=df.index)).astype(bool).astype(int)
        df["_df"] = df.get("has_defuser", pd.Series(False, index=df.index)).astype(bool).astype(int)

        # Strategy: load into temp table, then UPDATE FROM (SQLite 3.33+)
        conn.execute("DROP TABLE IF EXISTS _repair")
        conn.execute("""
            CREATE TEMP TABLE _repair (
                player_name TEXT NOT NULL,
                tick INTEGER NOT NULL,
                cr INTEGER NOT NULL,
                bl INTEGER NOT NULL,
                hm INTEGER NOT NULL,
                df INTEGER NOT NULL
            )
        """)

        # Bulk INSERT into temp table
        repair_data = list(zip(
            df["player_name"],
            df["tick"].astype(int),
            df["_cr"],
            df["_bl"],
            df["_hm"],
            df["_df"],
        ))
        conn.executemany(
            "INSERT INTO _repair(player_name, tick, cr, bl, hm, df) VALUES (?,?,?,?,?,?)",
            repair_data,
        )

        # Single UPDATE FROM — joins on (player_name, tick) within this demo
        conn.execute("""
            UPDATE playertickstate
            SET is_crouching = r.cr,
                is_blinded   = r.bl,
                has_helmet   = r.hm,
                has_defuser  = r.df
            FROM _repair r
            WHERE playertickstate.demo_name = ?
              AND playertickstate.player_name = r.player_name
              AND playertickstate.tick = r.tick
        """, (demo_name,))

        conn.execute("DROP TABLE _repair")
        conn.commit()

        elapsed = time.monotonic() - t_demo
        print(f"{len(repair_data):,} ticks ({elapsed:.1f}s)", flush=True)
        total_updated += len(repair_data)

    conn.close()
    total_elapsed = time.monotonic() - t_start

    print(f"\n=== Done ({total_elapsed:.0f}s) ===", flush=True)
    print(f"  Total ticks processed: {total_updated:,}", flush=True)


if __name__ == "__main__":
    main()
