#!/usr/bin/env python3
"""
Populate the RoundStats table + enrich PlayerMatchStats from ingested pro .dem files.

Reads each .dem file via demoparser2, builds per-round per-player stats using
round_stats_builder, enriches with equipment_value from playertickstate, bulk-inserts
into the roundstats table, AND writes match-level enrichment fields into
playermatchstats (kill-type percentages, utility-per-round metrics, flash assists,
blind time / distinct enemies blinded, trade kill ratios, opening duel win rate).

Previously (Q1-02 bug): the enrichment dict returned by enrich_from_demo() was
discarded via `_, round_stats_dicts = ...` and playermatchstats never saw the
match-level aggregates. This caused 11 columns (thrusmoke_kill_pct, wallbang_kill_pct,
noscope_kill_pct, blind_kill_pct, he_damage_per_round, molotov_damage_per_round,
smokes_per_round, flash_assists, utility_blind_time, utility_enemies_blinded,
trade_kill_ratio/was_traded_ratio) to be 0.0 across all rows. Fixed by capturing
the enrichment dict and issuing an UPDATE for every (demo_name, player_name) pair.

Idempotent: skips demos that already have RoundStats rows (can be re-run safely).
Use --full to re-process all demos regardless.

Usage:
    python tools/populate_round_stats.py            # skip already-processed demos
    python tools/populate_round_stats.py --full     # re-process all demos
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Programma_CS2_RENAN.core.config import get_pro_demo_base

DEMO_BASE = get_pro_demo_base()
DB_PATH = str(PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db")

# RoundStats model columns we populate from the builder dict.
# Fields absent from the model (noscope_kills, blind_kills, flash_assists) are excluded.
_COLUMNS = [
    "demo_name",
    "round_number",
    "player_name",
    "side",
    "kills",
    "deaths",
    "assists",
    "damage_dealt",
    "headshot_kills",
    "trade_kills",
    "was_traded",
    "thrusmoke_kills",
    "wallbang_kills",
    "opening_kill",
    "opening_death",
    "he_damage",
    "molotov_damage",
    "flashes_thrown",
    "smokes_thrown",
    "equipment_value",
    "round_won",
    "mvp",
    "kast",
    "round_rating",
    "created_at",
]

_INSERT_SQL = (
    "INSERT OR IGNORE INTO roundstats ("
    + ", ".join(_COLUMNS)
    + ") VALUES ("
    + ", ".join("?" * len(_COLUMNS))
    + ")"
)

# Q1-02: Enrichment keys (from round_stats_builder.aggregate_round_stats_to_match)
# mapped to playermatchstats columns. These are the fields we UPDATE after the
# roundstats INSERT. Any enrichment key NOT in this list is ignored.
_ENRICHMENT_TO_PLAYERMATCHSTATS = {
    "trade_kill_ratio": "trade_kill_ratio",
    "was_traded_ratio": "was_traded_ratio",
    "thrusmoke_kill_pct": "thrusmoke_kill_pct",
    "wallbang_kill_pct": "wallbang_kill_pct",
    "noscope_kill_pct": "noscope_kill_pct",
    "blind_kill_pct": "blind_kill_pct",
    "he_damage_per_round": "he_damage_per_round",
    "molotov_damage_per_round": "molotov_damage_per_round",
    "smokes_per_round": "smokes_per_round",
    "flash_assists": "flash_assists",
    "utility_blind_time": "utility_blind_time",
    "utility_enemies_blinded": "utility_enemies_blinded",
    "opening_duel_win_pct": "opening_duel_win_pct",
}


def _build_demo_path_map() -> dict:
    """Scan DEMO_BASE for all .dem files, keyed by stem (demo_name)."""
    return {p.stem: p for p in DEMO_BASE.rglob("*.dem")}


def _fetch_equipment_value_by_round(conn, demo_name: str) -> dict:
    """
    Return first-tick equipment_value for each (player_name, round_number).

    SQLite guarantees that non-aggregated columns in a GROUP BY query return
    the value from the row containing MIN()/MAX() of the aggregate column.
    MIN(tick) therefore gives the buy-phase equipment_value at round start.
    """
    rows = conn.execute(
        """
        SELECT player_name, round_number, MIN(tick), equipment_value
        FROM playertickstate
        WHERE demo_name = ?
        GROUP BY player_name, round_number
        """,
        (demo_name,),
    ).fetchall()
    return {(r[0], r[1]): r[3] for r in rows}


def main() -> None:
    import sqlite3

    from Programma_CS2_RENAN.backend.processing.round_stats_builder import enrich_from_demo
    from Programma_CS2_RENAN.backend.storage.database import init_database

    full_rebuild = "--full" in sys.argv

    print("=== RoundStats Population ===")
    print(f"    MODE: {'Full rebuild' if full_rebuild else 'Incremental'}\n")

    # Ensure schema is up to date (adds kast column if not yet present)
    init_database()

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")

    demo_path_map = _build_demo_path_map()

    demo_names = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT demo_name FROM playertickstate ORDER BY demo_name"
        ).fetchall()
    ]
    print(f"Found {len(demo_names)} demos in playertickstate.\n")

    total_inserted = 0
    total_skipped = 0
    total_failed = 0

    for i, demo_name in enumerate(demo_names, 1):
        dem_path = demo_path_map.get(demo_name)
        if dem_path is None:
            print(f"[{i:02d}/{len(demo_names)}] SKIP (no .dem file on disk): {demo_name}")
            total_failed += 1
            continue

        # Incremental mode: skip demos that already have round stats
        if not full_rebuild:
            existing = conn.execute(
                "SELECT COUNT(*) FROM roundstats WHERE demo_name = ?", (demo_name,)
            ).fetchone()[0]
            if existing > 0:
                print(f"[{i:02d}/{len(demo_names)}] SKIP ({existing} rows exist): {demo_name}")
                total_skipped += existing
                continue

        print(f"[{i:02d}/{len(demo_names)}] Processing: {demo_name} ...", end=" ", flush=True)

        # Build round stats AND match-level enrichment from the .dem file.
        # Q1-02: The enrichment dict was previously discarded; it is now used to
        # UPDATE playermatchstats below.
        enrichment_by_player, round_stats_dicts = enrich_from_demo(str(dem_path), demo_name)
        if not round_stats_dicts:
            print("WARN: no round stats built — demo may lack round_end events")
            total_failed += 1
            continue

        # Enrich equipment_value from playertickstate (first tick per player/round)
        equip_map = _fetch_equipment_value_by_round(conn, demo_name)

        # Full rebuild: delete existing rows for this demo before re-inserting
        if full_rebuild:
            conn.execute("DELETE FROM roundstats WHERE demo_name = ?", (demo_name,))

        # Batch insert via INSERT OR IGNORE (idempotent via UniqueConstraint)
        now_str = datetime.now(timezone.utc).isoformat()
        rows_to_insert = []
        for stats in round_stats_dicts:
            player = stats.get("player_name", "")
            rnum = stats.get("round_number", 0)
            ev = equip_map.get((player, rnum), 0)

            rows_to_insert.append(
                (
                    stats.get("demo_name", demo_name),
                    rnum,
                    player,
                    stats.get("side", "unknown"),
                    int(stats.get("kills", 0)),
                    int(stats.get("deaths", 0)),
                    int(stats.get("assists", 0)),
                    int(stats.get("damage_dealt", 0)),
                    int(stats.get("headshot_kills", 0)),
                    int(stats.get("trade_kills", 0)),
                    int(bool(stats.get("was_traded", False))),
                    int(stats.get("thrusmoke_kills", 0)),
                    int(stats.get("wallbang_kills", 0)),
                    int(bool(stats.get("opening_kill", False))),
                    int(bool(stats.get("opening_death", False))),
                    float(stats.get("he_damage", 0.0)),
                    float(stats.get("molotov_damage", 0.0)),
                    int(stats.get("flashes_thrown", 0)),
                    int(stats.get("smokes_thrown", 0)),
                    int(ev),
                    int(bool(stats.get("round_won", False))),
                    int(bool(stats.get("mvp", False))),
                    int(bool(stats.get("kast", False))),
                    stats.get("round_rating"),
                    now_str,
                )
            )

        conn.executemany(_INSERT_SQL, rows_to_insert)
        conn.commit()

        # Count how many were actually inserted (vs ignored by IGNORE)
        after = conn.execute(
            "SELECT COUNT(*) FROM roundstats WHERE demo_name = ?", (demo_name,)
        ).fetchone()[0]
        newly_inserted = after - (0 if full_rebuild else 0)

        # Q1-02: Update playermatchstats with match-level enrichment for every
        # (demo_name, player_name) pair that has a row. UPDATE with no matching
        # row is a no-op, so players without existing stats are silently skipped
        # (they will be enriched when their playermatchstats row is created by
        # whichever ingestion pipeline owns that table).
        pms_updates = 0
        for player_name, enrichment in enrichment_by_player.items():
            # Build column list from whatever enrichment keys are present
            set_clauses = []
            values = []
            for enrich_key, col_name in _ENRICHMENT_TO_PLAYERMATCHSTATS.items():
                if enrich_key in enrichment:
                    set_clauses.append(f"{col_name} = ?")
                    values.append(float(enrichment[enrich_key]))
            if not set_clauses:
                continue
            values.extend([demo_name, player_name])
            conn.execute(
                f"UPDATE playermatchstats SET {', '.join(set_clauses)} "
                f"WHERE demo_name = ? AND player_name = ?",
                values,
            )
            if conn.total_changes:
                pms_updates += 1
        conn.commit()

        print(
            f"inserted {len(rows_to_insert)} roundstats rows, "
            f"enriched {pms_updates}/{len(enrichment_by_player)} playermatchstats "
            f"({after} total roundstats for this demo)"
        )
        total_inserted += len(rows_to_insert)

    conn.close()

    print("\n=== Done ===")
    print(f"  Processed: {total_inserted:,} rows inserted")
    print(f"  Skipped (already present): {total_skipped:,} rows")
    print(f"  Failed / missing .dem: {total_failed} demos")

    # Final count
    conn2 = sqlite3.connect(DB_PATH, timeout=10)
    total_rows = conn2.execute("SELECT COUNT(*) FROM roundstats").fetchone()[0]
    demos_covered = conn2.execute("SELECT COUNT(DISTINCT demo_name) FROM roundstats").fetchone()[0]
    conn2.close()
    print(f"\n  Total roundstats rows: {total_rows:,}")
    print(f"  Demos covered: {demos_covered}")


if __name__ == "__main__":
    main()
