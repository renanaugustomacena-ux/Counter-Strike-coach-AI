#!/usr/bin/env python3
"""D4 — Disk hygiene audit for CS2 Coach AI.

Read-only inventory of two artifact families:

1. ``DEMO_PRO_PLAYERS/match_data/match_*.db`` per-match shards. Each is
   compared against the monolith (``playertickstate``) to compute a
   recommended action: KEEP / RM_AFTER_BACKUP / INVESTIGATE.

2. ``Programma_CS2_RENAN/backups/backup_startup_auto_*.db`` (and the
   one-off ``pre-restoration-*.db``). Retention rule: keep 3 most recent
   + 1 per calendar month for the last 6 months; older = PRUNE candidate.

NO files are deleted. Output is a single JSON written to
``docs/match_db_audit_<UTC_TS>.json``. The owner runs any deletion
themselves.

Usage:
    ./.venv/bin/python tools/d4_disk_hygiene_audit.py
    ./.venv/bin/python tools/d4_disk_hygiene_audit.py --report-out docs/d4_audit.json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Programma_CS2_RENAN.core.config import CORE_DB_DIR, get_pro_demo_base

DEMO_BASE = get_pro_demo_base()
MATCH_DATA_DIR = DEMO_BASE / "match_data"
MONOLITH_DB_PATH = Path(CORE_DB_DIR) / "database.db"
BACKUPS_DIR = PROJECT_ROOT / "Programma_CS2_RENAN" / "backups"

RETENTION_KEEP_RECENT = 3
RETENTION_MONTHS = 6


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _safe_count(conn: sqlite3.Connection, query: str, params: tuple = ()) -> int:
    try:
        return int(conn.execute(query, params).fetchone()[0])
    except sqlite3.Error:
        return -1


def _audit_match_dbs(monolith_conn: sqlite3.Connection) -> list[dict]:
    """Per-shard tick parity vs monolith. RM_AFTER_BACKUP only when ticks match exactly."""
    out = []
    if not MATCH_DATA_DIR.exists():
        return out
    for path in sorted(MATCH_DATA_DIR.glob("match_*.db")):
        try:
            stat = path.stat()
        except OSError as e:
            out.append(
                {
                    "path": str(path),
                    "error": f"stat failed: {e}",
                    "recommended_action": "INVESTIGATE",
                }
            )
            continue

        # Source tick count.
        src_ticks = -1
        src_demo_name = None
        try:
            src = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
            src_ticks = _safe_count(src, "SELECT COUNT(*) FROM matchtickstate")
            row = src.execute("SELECT demo_name FROM match_metadata LIMIT 1").fetchone()
            src_demo_name = row[0] if row else None
            src.close()
        except sqlite3.Error as e:
            out.append(
                {
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "mtime_iso": _iso(stat.st_mtime),
                    "tick_count_source": -1,
                    "tick_count_monolith": -1,
                    "data_quality_in_main": None,
                    "recommended_action": "INVESTIGATE",
                    "reason": f"source read failed: {e}",
                }
            )
            continue

        # Monolith tick count under matching demo_name (or filename-derived stem).
        mono_ticks = -1
        dq_in_main = None
        if src_demo_name:
            mono_ticks = _safe_count(
                monolith_conn,
                "SELECT COUNT(*) FROM playertickstate WHERE demo_name=?",
                (src_demo_name,),
            )
            row = monolith_conn.execute(
                "SELECT data_quality FROM playermatchstats WHERE demo_name=? LIMIT 1",
                (src_demo_name,),
            ).fetchone()
            dq_in_main = row[0] if row else None

        if src_demo_name is None or mono_ticks == 0 or mono_ticks == -1:
            action = "INVESTIGATE"
            reason = "missing monolith counterpart"
        elif src_ticks > 0 and src_ticks == mono_ticks:
            action = "RM_AFTER_BACKUP"
            reason = "tick parity OK + already in monolith"
        elif src_ticks > mono_ticks:
            action = "INVESTIGATE"
            reason = f"source has more ticks ({src_ticks}>{mono_ticks})"
        else:
            action = "KEEP"
            reason = f"src_ticks={src_ticks} mono_ticks={mono_ticks}"

        out.append(
            {
                "path": str(path),
                "demo_name": src_demo_name,
                "size_bytes": stat.st_size,
                "mtime_iso": _iso(stat.st_mtime),
                "tick_count_source": src_ticks,
                "tick_count_monolith": mono_ticks,
                "data_quality_in_main": dq_in_main,
                "recommended_action": action,
                "reason": reason,
            }
        )
    return out


def _audit_startup_backups() -> list[dict]:
    """3 most recent + 1/month for 6 months → KEEP. Older → PRUNE_PER_RETENTION_POLICY."""
    out = []
    if not BACKUPS_DIR.exists():
        return out

    # Only score the .db files here; sidecars (-shm, -wal, -journal) inherit parent decision.
    files = sorted(
        [p for p in BACKUPS_DIR.glob("backup_startup_auto_*.db") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # Add pre-restoration backups too.
    files += sorted(
        [p for p in BACKUPS_DIR.glob("pre-restoration-*.db") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    keep_recent_paths = {p for p in files[:RETENTION_KEEP_RECENT]}
    one_per_month: dict[str, Path] = {}
    for p in files:
        ym = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m")
        # First seen per month is the newest (files already mtime-desc).
        one_per_month.setdefault(ym, p)

    now = datetime.now(timezone.utc)

    months_to_keep = set()
    yr, mo = now.year, now.month
    for _ in range(RETENTION_MONTHS):
        months_to_keep.add(f"{yr:04d}-{mo:02d}")
        mo -= 1
        if mo == 0:
            mo = 12
            yr -= 1

    keep_monthly_paths = {p for ym, p in one_per_month.items() if ym in months_to_keep}

    for p in files:
        stat = p.stat()
        ym = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m")
        if p in keep_recent_paths or p in keep_monthly_paths:
            decision = "KEEP"
        else:
            decision = "PRUNE_PER_RETENTION_POLICY"
        out.append(
            {
                "path": str(p),
                "size_bytes": stat.st_size,
                "mtime_iso": _iso(stat.st_mtime),
                "year_month": ym,
                "recommended_retention": decision,
                "policy": (
                    f"keep {RETENTION_KEEP_RECENT} most recent + 1 per month "
                    f"for {RETENTION_MONTHS} months"
                ),
            }
        )
    return out


def _build_summary(match_dbs: list[dict], backups: list[dict]) -> dict:
    by_action = defaultdict(int)
    by_action_size = defaultdict(int)
    for r in match_dbs:
        by_action[r.get("recommended_action", "?")] += 1
        by_action_size[r.get("recommended_action", "?")] += r.get("size_bytes", 0)
    backups_keep = sum(1 for b in backups if b["recommended_retention"] == "KEEP")
    backups_prune = len(backups) - backups_keep
    backups_prune_size = sum(
        b["size_bytes"] for b in backups if b["recommended_retention"] != "KEEP"
    )
    return {
        "match_db_files_total": len(match_dbs),
        "match_db_action_counts": dict(by_action),
        "match_db_action_size_bytes": dict(by_action_size),
        "match_db_potential_reclaim_bytes": by_action_size.get("RM_AFTER_BACKUP", 0),
        "startup_backups_total": len(backups),
        "startup_backups_keep": backups_keep,
        "startup_backups_prune_candidates": backups_prune,
        "startup_backups_prune_reclaim_bytes": backups_prune_size,
    }


def main():
    p = argparse.ArgumentParser(description="D4 disk hygiene audit (read-only).")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    p.add_argument(
        "--report-out",
        type=Path,
        default=Path(f"docs/match_db_audit_{ts}.json"),
        help="JSON report destination.",
    )
    args = p.parse_args()

    print(f"D4 audit running. Monolith: {MONOLITH_DB_PATH}")
    if not MONOLITH_DB_PATH.exists():
        print(f"  ERROR: monolith DB not found at {MONOLITH_DB_PATH}")
        sys.exit(1)

    mono = sqlite3.connect(f"file:{MONOLITH_DB_PATH}?mode=ro", uri=True, timeout=30)
    try:
        match_dbs = _audit_match_dbs(mono)
    finally:
        mono.close()
    backups = _audit_startup_backups()
    summary = _build_summary(match_dbs, backups)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "D4 disk hygiene audit",
        "monolith_db_path": str(MONOLITH_DB_PATH),
        "match_data_dir": str(MATCH_DATA_DIR),
        "backups_dir": str(BACKUPS_DIR),
        "summary": summary,
        "match_db_files": match_dbs,
        "startup_backups": backups,
    }

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2, default=str))
    print(f"D4 report written: {args.report_out}")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
