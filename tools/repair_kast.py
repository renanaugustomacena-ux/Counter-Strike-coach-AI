#!/usr/bin/env python3
"""
Repair KAST values in PlayerMatchStats using event-accurate per-round data
from the RoundStats table.

Replaces the inflated estimate_kast_from_stats() approximation (avg ~0.91)
with the actual KAST ratio computed from round-level K/A/S/T binary flags
(expected avg ~0.70-0.75 for pro data).

Usage:
    python tools/repair_kast.py           # repair all players
    python tools/repair_kast.py --dry-run # preview changes without writing
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = str(PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db")


def main() -> None:
    import sqlite3

    dry_run = "--dry-run" in sys.argv

    print("=== KAST Repair ===")
    if dry_run:
        print("    MODE: Dry run (no changes written)\n")
    else:
        print("    MODE: Live repair\n")

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    # ── Before stats ──
    before = conn.execute(
        "SELECT COUNT(*), AVG(avg_kast), MIN(avg_kast), MAX(avg_kast) "
        "FROM playermatchstats WHERE is_pro = 1"
    ).fetchone()
    print(
        f"BEFORE: {before[0]} pro rows, avg_kast={before[1]:.4f}, "
        f"min={before[2]:.4f}, max={before[3]:.4f}"
    )

    # ── Compute correct KAST from roundstats ──
    # For each (demo_name, player_name): avg_kast = SUM(kast) / COUNT(*)
    repair_data = conn.execute(
        """
        SELECT r.demo_name, r.player_name,
               CAST(SUM(r.kast) AS REAL) / COUNT(*) AS avg_kast,
               COUNT(*) AS rounds_played
        FROM roundstats r
        INNER JOIN playermatchstats p
            ON r.demo_name = p.demo_name AND LOWER(r.player_name) = LOWER(p.player_name)
        WHERE p.is_pro = 1
        GROUP BY r.demo_name, r.player_name
    """
    ).fetchall()

    print(f"\nFound {len(repair_data)} (demo, player) pairs to repair.")

    if not repair_data:
        print("Nothing to repair — roundstats may be empty or not linked.")
        conn.close()
        return

    # ── Apply updates ──
    updated = 0
    for demo_name, player_name, avg_kast, rounds_played in repair_data:
        if not dry_run:
            conn.execute(
                "UPDATE playermatchstats SET avg_kast = ? "
                "WHERE demo_name = ? AND LOWER(player_name) = LOWER(?)",
                (avg_kast, demo_name, player_name),
            )
        updated += 1

    if not dry_run:
        conn.commit()

    # ── After stats ──
    after = conn.execute(
        "SELECT COUNT(*), AVG(avg_kast), MIN(avg_kast), MAX(avg_kast) "
        "FROM playermatchstats WHERE is_pro = 1"
    ).fetchone()

    print(
        f"\nAFTER:  {after[0]} pro rows, avg_kast={after[1]:.4f}, "
        f"min={after[2]:.4f}, max={after[3]:.4f}"
    )
    print(f"\nUpdated: {updated} rows {'(dry run)' if dry_run else ''}")

    # Sanity: show distribution
    dist = conn.execute(
        """
        SELECT
            CASE
                WHEN avg_kast < 0.5 THEN '<0.50'
                WHEN avg_kast < 0.6 THEN '0.50-0.59'
                WHEN avg_kast < 0.7 THEN '0.60-0.69'
                WHEN avg_kast < 0.8 THEN '0.70-0.79'
                WHEN avg_kast < 0.9 THEN '0.80-0.89'
                ELSE '0.90+'
            END AS bucket,
            COUNT(*)
        FROM playermatchstats WHERE is_pro = 1
        GROUP BY bucket ORDER BY bucket
    """
    ).fetchall()
    print("\nKAST distribution:")
    for bucket, count in dist:
        print(f"  {bucket}: {count}")

    conn.close()

    # DL-1: Record provenance for KAST repair
    if not dry_run and updated > 0:
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager

        get_db_manager().record_lineage(
            entity_type="batch_kast_repair",
            entity_id=updated,
            source_demo="all_pro_demos",
            processing_step="kast_repair",
        )


if __name__ == "__main__":
    main()
