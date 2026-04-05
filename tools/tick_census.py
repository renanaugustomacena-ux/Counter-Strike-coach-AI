#!/usr/bin/env python3
"""
Full-corpus tick quality census.

Iterates through the monolith PlayerTickState in chunks (by rowid range),
computing per-demo and per-feature quality metrics. Identifies demos with
dead feature dimensions (>90% zero) that need repair.

Output: per-demo quality report + aggregate summary.

Usage:
    python tools/tick_census.py
"""
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"

# Features to audit (column name → feature index in 25-dim vector)
AUDIT_COLUMNS = {
    "health": 0,
    "armor": 1,
    # has_helmet (idx 2) and has_defuser (idx 3) not in monolith — only per-match DBs
    "equipment_value": 4,
    "is_crouching": 5,
    "is_scoped": 6,
    "is_blinded": 7,
    "enemies_visible": 8,
    "pos_x": 9,
    "pos_y": 10,
    "pos_z": 11,
    "time_in_round": 20,
    "bomb_planted": 21,
    "teammates_alive": 22,
    "enemies_alive": 23,
    "team_economy": 24,
}

# Binary/low-frequency features where high zero rate is normal
EXPECTED_LOW_FREQUENCY = {"is_crouching", "is_scoped", "is_blinded", "bomb_planted"}

# Threshold: flag if a non-low-frequency feature is >90% zero in a demo
ZERO_RATE_THRESHOLD = 0.90

CHUNK_SIZE = 100_000


def run_census():
    """Run the full tick census and print per-demo quality report."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # Get rowid range and demo list
    c.execute("SELECT MIN(rowid), MAX(rowid) FROM playertickstate")
    min_id, max_id = c.fetchone()
    if not min_id:
        print("No ticks in database.")
        return

    c.execute("SELECT DISTINCT demo_name FROM playertickstate")
    all_demos = [r[0] for r in c.fetchall()]

    print(f"=== Tick Census ===")
    print(f"Total rowid range: {min_id:,} — {max_id:,}")
    print(f"Demos: {len(all_demos)}")
    print(f"Chunk size: {CHUNK_SIZE:,}\n")

    # Per-demo accumulators
    demo_stats = defaultdict(lambda: {
        "total": 0,
        "zero_counts": defaultdict(int),
        "min_vals": defaultdict(lambda: float("inf")),
        "max_vals": defaultdict(lambda: float("-inf")),
        "map_name": None,
    })

    # Build column list for SELECT
    col_names = list(AUDIT_COLUMNS.keys()) + ["demo_name", "map_name"]
    col_select = ", ".join(col_names)

    t0 = time.monotonic()
    total_processed = 0
    current_id = min_id

    while current_id <= max_id:
        end_id = current_id + CHUNK_SIZE - 1
        c.execute(
            f"SELECT {col_select} FROM playertickstate "
            f"WHERE rowid BETWEEN ? AND ?",
            (current_id, end_id),
        )
        rows = c.fetchall()

        for row in rows:
            vals = dict(zip(col_names, row))
            demo = vals["demo_name"]
            ds = demo_stats[demo]
            ds["total"] += 1
            if vals["map_name"]:
                ds["map_name"] = vals["map_name"]

            for col in AUDIT_COLUMNS:
                v = vals.get(col, 0) or 0
                if v == 0:
                    ds["zero_counts"][col] += 1
                if isinstance(v, (int, float)):
                    ds["min_vals"][col] = min(ds["min_vals"][col], v)
                    ds["max_vals"][col] = max(ds["max_vals"][col], v)

        total_processed += len(rows)
        current_id = end_id + 1

        # Progress every 5M rows
        if total_processed % 5_000_000 < CHUNK_SIZE:
            elapsed = time.monotonic() - t0
            pct = (current_id - min_id) / (max_id - min_id + 1) * 100
            print(f"  Progress: {total_processed:>12,} rows ({pct:.0f}%) — {elapsed:.0f}s")

    elapsed = time.monotonic() - t0
    print(f"\n  Processed {total_processed:,} rows in {elapsed:.1f}s\n")

    # === Report ===
    print("=" * 100)
    print(f"{'Demo':<50} {'Ticks':>10} {'Map':<14} {'Issues'}")
    print("-" * 100)

    issues_by_demo = {}
    global_zero = defaultdict(int)
    global_total = 0

    for demo in sorted(demo_stats.keys()):
        ds = demo_stats[demo]
        total = ds["total"]
        global_total += total
        issues = []

        for col, feat_idx in AUDIT_COLUMNS.items():
            zero_count = ds["zero_counts"].get(col, 0)
            zero_rate = zero_count / max(total, 1)
            global_zero[col] += zero_count

            # Flag non-low-frequency features with high zero rate
            if col not in EXPECTED_LOW_FREQUENCY and zero_rate > ZERO_RATE_THRESHOLD:
                issues.append(f"{col}={zero_rate:.0%}zero")

        issue_str = ", ".join(issues) if issues else "OK"
        map_name = ds.get("map_name") or "unknown"

        # Only print demos with issues, unless total demos < 20
        if issues or len(all_demos) <= 20:
            print(f"  {demo[:48]:<50} {total:>10,} {map_name:<14} {issue_str}")

        if issues:
            issues_by_demo[demo] = issues

    # === Global summary ===
    print("\n" + "=" * 100)
    print("GLOBAL FEATURE QUALITY SUMMARY")
    print("-" * 100)
    print(f"{'Feature':<20} {'Idx':>4} {'Zero Rate':>10} {'Min':>12} {'Max':>12} {'Status'}")
    print("-" * 100)

    for col, feat_idx in AUDIT_COLUMNS.items():
        zero_total = global_zero.get(col, 0)
        zero_rate = zero_total / max(global_total, 1)

        # Aggregate min/max across demos
        g_min = float("inf")
        g_max = float("-inf")
        for ds in demo_stats.values():
            if col in ds["min_vals"]:
                g_min = min(g_min, ds["min_vals"][col])
            if col in ds["max_vals"]:
                g_max = max(g_max, ds["max_vals"][col])

        if col in EXPECTED_LOW_FREQUENCY:
            status = "OK (low-freq expected)"
        elif zero_rate > ZERO_RATE_THRESHOLD:
            status = "CRITICAL — dead dimension"
        elif zero_rate > 0.5:
            status = "DEGRADED"
        elif zero_rate > 0.1:
            status = "WARN"
        else:
            status = "HEALTHY"

        print(f"  {col:<20} {feat_idx:>4} {zero_rate:>9.1%} {g_min:>12.1f} {g_max:>12.1f} {status}")

    # === Repair recommendations ===
    print("\n" + "=" * 100)
    print("REPAIR RECOMMENDATIONS")
    print("-" * 100)

    if issues_by_demo:
        affected_demos = list(issues_by_demo.keys())
        # Group by issue type
        issue_types = defaultdict(list)
        for demo, issues in issues_by_demo.items():
            for issue in issues:
                col = issue.split("=")[0]
                issue_types[col].append(demo)

        for col, demos in sorted(issue_types.items()):
            print(f"\n  {col}: {len(demos)} demos affected")
            for d in demos[:5]:
                print(f"    - {d}")
            if len(demos) > 5:
                print(f"    ... and {len(demos) - 5} more")
    else:
        print("  No critical issues found. All features healthy.")

    print(f"\n  Total demos with issues: {len(issues_by_demo)}/{len(all_demos)}")

    conn.close()
    return issues_by_demo


if __name__ == "__main__":
    run_census()
