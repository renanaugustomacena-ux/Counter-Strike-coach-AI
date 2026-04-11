#!/usr/bin/env python3
"""
Repair equipment_value in PlayerTickState for demos where it's all zeros.

Re-extracts current_equip_value from .dem files using demoparser2,
then batch-updates the monolith via a temp table + SQL UPDATE.

Usage:
    python tools/repair_equipment_value.py
"""
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEMO_BASE = Path("/media/admin/usb-ssd/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS")
DB_PATH = PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"

# The 8 demos with equipment_value=0 (from tick census)
AFFECTED_DEMOS = [
    "falcons-vs-parivision-m1-mirage",
    "falcons-vs-parivision-m2-dust2",
    "falcons-vs-parivision-m3-inferno",
    "furia-vs-aurora-m1-dust2",
    "furia-vs-aurora-m2-mirage",
    "furia-vs-natus-vincere-m1-mirage",
    "furia-vs-natus-vincere-m2-inferno",
    "furia-vs-natus-vincere-m3-dust2",
]


def find_dem_file(demo_stem: str) -> Path | None:
    """Find the .dem file matching a demo stem name."""
    matches = list(DEMO_BASE.rglob(f"{demo_stem}.dem"))
    return matches[0] if matches else None


def extract_equipment_value(dem_path: Path) -> list[tuple]:
    """Extract (tick, player_name, equipment_value) from a .dem file.

    Returns list of (tick, player_name, equipment_value) tuples.
    """
    from demoparser2 import DemoParser

    parser = DemoParser(str(dem_path))
    df = parser.parse_ticks(["current_equip_value", "player_name"])

    # Resolve column names
    if "current_equip_value" not in df.columns:
        # Try alternative names
        for alt in ["equipment_value", "equip_value"]:
            if alt in df.columns:
                df = df.rename(columns={alt: "current_equip_value"})
                break

    if "current_equip_value" not in df.columns:
        print(f"  WARNING: No equipment_value field found in {dem_path.name}")
        return []

    p_col = "player_name" if "player_name" in df.columns else "name"
    if p_col != "player_name":
        df = df.rename(columns={p_col: "player_name"})

    # Filter to rows with non-zero values
    df = df[df["current_equip_value"] > 0]

    return list(zip(df["tick"], df["player_name"], df["current_equip_value"]))


def repair_demo(conn: sqlite3.Connection, demo_stem: str) -> int:
    """Repair equipment_value for a single demo. Returns rows updated."""
    dem_path = find_dem_file(demo_stem)
    if not dem_path:
        print(f"  SKIP {demo_stem} — .dem file not found")
        return 0

    print(f"  Extracting {dem_path.name}...", end="", flush=True)
    t0 = time.monotonic()

    tuples = extract_equipment_value(dem_path)
    if not tuples:
        print(f" no data")
        return 0

    t_extract = time.monotonic() - t0
    print(f" {len(tuples):,} rows ({t_extract:.1f}s)")

    # Build lookup dict: (tick, player_name) -> equipment_value
    lookup = {}
    for tick, pname, eqval in tuples:
        lookup[(int(tick), str(pname))] = int(eqval)

    # Batch UPDATE: read monolith rows for this demo, update in chunks
    c = conn.cursor()
    BATCH = 50_000
    total_updated = 0

    # Get all ticks with equipment_value=0 for this demo
    c.execute(
        "SELECT rowid, tick, player_name FROM playertickstate "
        "WHERE demo_name = ? AND equipment_value = 0",
        (demo_stem,),
    )

    updates = []
    for rowid, tick, pname in c:
        key = (int(tick), str(pname))
        eqval = lookup.get(key)
        if eqval and eqval > 0:
            updates.append((eqval, rowid))

        if len(updates) >= BATCH:
            c2 = conn.cursor()
            c2.executemany(
                "UPDATE playertickstate SET equipment_value = ? WHERE rowid = ?",
                updates,
            )
            total_updated += len(updates)
            conn.commit()
            elapsed = time.monotonic() - t0
            print(f"    chunk: {total_updated:,} updated ({elapsed:.0f}s)", flush=True)
            updates = []

    # Final batch
    if updates:
        c2 = conn.cursor()
        c2.executemany(
            "UPDATE playertickstate SET equipment_value = ? WHERE rowid = ?",
            updates,
        )
        total_updated += len(updates)
        conn.commit()

    elapsed = time.monotonic() - t0
    print(f"  → {total_updated:,} rows updated ({elapsed:.1f}s)")
    return total_updated


def main():
    print("=== Equipment Value Repair ===\n")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA cache_size=-200000")  # 200MB cache for large UPDATEs

    total_updated = 0
    for demo in AFFECTED_DEMOS:
        updated = repair_demo(conn, demo)
        total_updated += updated

    # Verification
    print(f"\n=== Verification ===")
    c = conn.cursor()
    for demo in AFFECTED_DEMOS:
        c.execute(
            "SELECT COUNT(*), SUM(CASE WHEN equipment_value > 0 THEN 1 ELSE 0 END) "
            "FROM playertickstate WHERE demo_name = ?",
            (demo,),
        )
        total, nonzero = c.fetchone()
        pct = (nonzero or 0) / total * 100 if total else 0
        status = "OK" if pct > 50 else "STILL BROKEN"
        print(f"  {demo[:50]:<52} {pct:>5.1f}% non-zero [{status}]")

    conn.close()
    print(f"\nTotal rows updated: {total_updated:,}")


if __name__ == "__main__":
    main()
