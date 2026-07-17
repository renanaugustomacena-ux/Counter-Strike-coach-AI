#!/usr/bin/env python3
"""One-shot repair: rating_* columns of full_sql* rows back to RAW scale.

Context (R4 MED, 2026-07-17): aggregate_match_stats_sql.py used to write
baseline-normalized RATIOS into the PlayerMatchStats rating_* columns
(survival/0.317, kast/0.70, kpr/0.679, adr/73.3) while demo_parser and
base_features wrote RAW components — and every consumer (pro_baseline,
skill_assessment Z-scores, coach_manager, the 25-dim feature list at
indices 19-20) assumes RAW. On the production monolith 1571 of 2501
full_sql* rows carried the wrong scale. The writer is fixed (SSOT
rating.compute_rating_components); this tool repairs the DATA.

The source columns (kpr, dpr, avg_kast, avg_adr) are raw and intact, so
the repair is a deterministic recomputation — idempotent by construction
(recomputing already-raw rows yields the same values).

Only rows with data_quality IN ('full_sql', 'full_sql_round_count_anomaly')
are touched: 'complete' rows came from demo_parser and are already raw.

Standalone stdlib-only ON PURPOSE: the monolith lives on the SSD reachable
from WSL where the project venv does not exist. The formulas mirror
rating.compute_rating_components — keep in lockstep (see
test_rating_components_contract.py for the SSOT contract).

Usage:
    python3 repair_rating_scale.py --db /path/to/database.db            # dry-run
    python3 repair_rating_scale.py --db /path/to/database.db --commit   # repair
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# HLTV 2.0 formula constants — MUST mirror
# backend/processing/feature_engineering/rating.py
BASELINE_KPR = 0.679
BASELINE_DPR_COMPLEMENT = 0.317
BASELINE_KAST = 0.70
BASELINE_IMPACT = 1.0
BASELINE_ADR = 73.3

TARGET_QUALITIES = ("full_sql", "full_sql_round_count_anomaly")


def compute_components(kpr: float, dpr: float, kast: float, avg_adr: float) -> dict:
    """Raw components + normalized aggregate (mirror of the SSOT)."""
    impact = (kpr * 2.13) + (avg_adr / 100.0 * 0.42) - 0.41 * (1.0 - dpr)
    rating = (
        kpr / BASELINE_KPR
        + (1.0 - dpr) / BASELINE_DPR_COMPLEMENT
        + kast / BASELINE_KAST
        + impact / BASELINE_IMPACT
        + avg_adr / BASELINE_ADR
    ) / 5.0
    return {
        "rating_kpr": kpr,
        "rating_survival": 1.0 - dpr,
        "rating_kast": kast,
        "rating_impact": impact,
        "rating_adr": avg_adr,
        "rating": max(0.0, min(5.0, rating)),
    }


def dump_backup(con: sqlite3.Connection, db_path: Path) -> Path:
    """CSV dump of the whole playermatchstats table next to the DB."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = db_path.parent / f"playermatchstats.pre_rating_repair_{stamp}.csv"
    cur = con.execute("SELECT * FROM playermatchstats")
    cols = [d[0] for d in cur.description]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(cur.fetchall())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument(
        "--commit", action="store_true", help="write the repair (default: dry-run report)"
    )
    args = ap.parse_args()

    if not args.db.exists():
        print(f"ERROR: DB not found: {args.db}", file=sys.stderr)
        return 2

    mode = "rw" if args.commit else "ro"
    con = sqlite3.connect(f"file:{args.db}?mode={mode}", uri=True, timeout=60)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        """
        SELECT id, demo_name, player_name, data_quality,
               kpr, dpr, avg_kast, avg_adr,
               rating_kpr, rating_survival, rating_kast, rating_impact,
               rating_adr, rating
        FROM playermatchstats
        WHERE data_quality IN (?, ?)
        """,
        TARGET_QUALITIES,
    ).fetchall()

    changed = []
    for r in rows:
        want = compute_components(
            float(r["kpr"] or 0.0),
            float(r["dpr"] or 0.0),
            float(r["avg_kast"] or 0.0),
            float(r["avg_adr"] or 0.0),
        )
        deltas = {
            k: (float(r[k] or 0.0), v)
            for k, v in want.items()
            if abs(float(r[k] or 0.0) - v) > 1e-9
        }
        if deltas:
            changed.append((r["id"], r["demo_name"], r["player_name"], deltas, want))

    print(f"rows in scope (full_sql*): {len(rows)}")
    print(f"rows needing repair:       {len(changed)}")
    if changed:
        sample = changed[0]
        print(f"example: id={sample[0]} {sample[1]}/{sample[2]}")
        for k, (old, new) in sample[3].items():
            print(f"    {k}: {old:.4f} -> {new:.4f}")

    if not args.commit:
        print("\nDRY-RUN — nothing written. Re-run with --commit to repair.")
        con.close()
        return 0

    if not changed:
        print("Nothing to repair — already consistent.")
        con.close()
        return 0

    backup = dump_backup(con, args.db)
    print(f"backup written: {backup}")

    with con:  # single transaction
        for row_id, _demo, _player, _deltas, want in changed:
            con.execute(
                """
                UPDATE playermatchstats
                SET rating_kpr = ?, rating_survival = ?, rating_kast = ?,
                    rating_impact = ?, rating_adr = ?, rating = ?
                WHERE id = ?
                """,
                (
                    want["rating_kpr"],
                    want["rating_survival"],
                    want["rating_kast"],
                    want["rating_impact"],
                    want["rating_adr"],
                    want["rating"],
                    row_id,
                ),
            )

    # Phase 2 — impact_rounds of 'complete' rows: the legacy demo_parser
    # aliased the HLTV impact RATING (~1.1-1.8) into impact_rounds, whose
    # canonical semantics are the SHARE of rounds with >=1 kill ([0, 1]).
    # Recompute from RoundStats where per-round rows exist.
    phase2 = con.execute(
        """
        SELECT p.id, s.share
        FROM playermatchstats p
        JOIN (
            SELECT demo_name, player_name,
                   CAST(SUM(CASE WHEN kills > 0 THEN 1 ELSE 0 END) AS REAL)
                       / COUNT(*) AS share
            FROM roundstats
            GROUP BY demo_name, player_name
        ) s ON s.demo_name = p.demo_name AND s.player_name = p.player_name
        WHERE p.data_quality = 'complete'
          AND ABS(p.impact_rounds - s.share) > 1e-9
        """
    ).fetchall()
    if phase2:
        with con:
            for row_id, share in phase2:
                con.execute(
                    "UPDATE playermatchstats SET impact_rounds = ? WHERE id = ?",
                    (float(share), row_id),
                )
    print(f"phase 2 (complete rows, impact_rounds share): {len(phase2)} repaired")

    # Post-repair verification: nothing in scope may still diverge.
    remaining = 0
    for r in con.execute(
        """
        SELECT kpr, dpr, avg_kast, avg_adr,
               rating_kpr, rating_survival, rating_kast, rating_impact,
               rating_adr, rating
        FROM playermatchstats WHERE data_quality IN (?, ?)
        """,
        TARGET_QUALITIES,
    ):
        want = compute_components(
            float(r["kpr"] or 0.0),
            float(r["dpr"] or 0.0),
            float(r["avg_kast"] or 0.0),
            float(r["avg_adr"] or 0.0),
        )
        if any(abs(float(r[k] or 0.0) - v) > 1e-9 for k, v in want.items()):
            remaining += 1
    con.close()

    print(f"repaired: {len(changed)} rows; still divergent after repair: {remaining}")
    if remaining:
        print("ERROR: verification failed", file=sys.stderr)
        return 1
    print("VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
