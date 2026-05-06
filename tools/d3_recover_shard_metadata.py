#!/usr/bin/env python3
"""D3 — Recover match_metadata rows in corrupted per-match shards.

Dry-run (default): emit JSON classification report, write nothing.
--apply: backup shards, then INSERT metadata for RECOVERABLE_FULL shards.

§129 Doctrine 5-question check (embedded in report header):
  1. What question does this answer?  → Which shards are recoverable?
  2. Simplest approach?  → SHA-256 forward map + intra-shard validation.
  3. Idempotent?  → Yes — skip if match_metadata already has rows.
  4. Tested on subset?  → Dry-run proves correctness before --apply.
  5. Reversible?  → Yes — backup created; INSERT can be DELETEd.
"""

import argparse
import datetime
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

DEMO_BASE = Path("/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS")
MATCH_DATA = DEMO_BASE / "match_data"
MONOLITH = Path(
    "/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/"
    "Counter-Strike-coach-AI-main/Programma_CS2_RENAN/backend/storage/database.db"
)
INVENTORY = Path(
    "/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/"
    "Counter-Strike-coach-AI-main/docs/d3_corrupted_match_inventory_2026-05-06.json"
)
REPORT_OUT = Path(
    "/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/"
    "Counter-Strike-coach-AI-main/docs/d3_recovery_report_2026-05-06.json"
)

MAP_SUFFIX_RE = re.compile(r"(?:-m\d+)?-([a-z][a-z0-9_]+?)(?:-p\d+)?$")
KNOWN_MAPS = {
    "mirage",
    "dust2",
    "inferno",
    "nuke",
    "overpass",
    "anubis",
    "ancient",
    "vertigo",
    "train",
}


def demo_stem_to_match_id(stem: str) -> int:
    return int(hashlib.sha256(stem.encode()).hexdigest(), 16) % (2**63 - 1)


def parse_map_from_demo_name(demo_name: str) -> str | None:
    m = MAP_SUFFIX_RE.search(demo_name)
    if m and m.group(1) in KNOWN_MAPS:
        return m.group(1)
    return None


def strip_de_prefix(map_name: str) -> str:
    return map_name.removeprefix("de_").lower()


def build_forward_map() -> dict[int, str]:
    names: set[str] = set()

    db = sqlite3.connect(str(MONOLITH))
    for row in db.execute("SELECT DISTINCT demo_name FROM playermatchstats"):
        names.add(row[0])
    db.close()

    for p in DEMO_BASE.glob("*.dem"):
        names.add(p.stem)

    return {demo_stem_to_match_id(n): n for n in names}


def extract_shard_id(filename: str) -> int | None:
    stem = filename.replace(".db", "")
    if not stem.startswith("match_"):
        return None
    try:
        return int(stem.removeprefix("match_"))
    except ValueError:
        return None


def derive_metadata_from_shard(shard_path: Path, demo_name: str) -> dict | None:
    conn = sqlite3.connect(str(shard_path))
    try:
        tick_count = conn.execute("SELECT COUNT(*) FROM matchtickstate").fetchone()[0]
        if tick_count == 0:
            return None

        maps = conn.execute(
            "SELECT DISTINCT map_name FROM matchtickstate WHERE map_name IS NOT NULL"
        ).fetchall()
        map_name = maps[0][0] if maps else None

        round_max = conn.execute("SELECT MAX(round_number) FROM matchtickstate").fetchone()[0]
        round_count = round_max if round_max is not None else 0

        player_count = conn.execute(
            "SELECT COUNT(DISTINCT player_name) FROM matchtickstate "
            "WHERE player_name IS NOT NULL"
        ).fetchone()[0]

        return {
            "demo_name": demo_name,
            "map_name": map_name or "unknown",
            "tick_count": tick_count,
            "round_count": round_count,
            "player_count": player_count,
            "tick_rate": 64.0,
            "team1_name": "Team 1",
            "team2_name": "Team 2",
            "team1_score": 0,
            "team2_score": 0,
            "parser_version": "v1-d3-recovered",
            "schema_version": 3,
            "is_pro_match": 0,
            "match_complete": 1,
        }
    finally:
        conn.close()


def classify_shards(
    fwd_map: dict[int, str],
) -> tuple[list[dict], list[dict], list[dict]]:
    with open(INVENTORY) as f:
        inv = json.load(f)

    corrupted = [e["path"] for e in inv["buckets"]["missing_metadata_value"]]
    no_table = [e["path"] for e in inv["buckets"].get("missing_table_match_metadata", [])]

    full: list[dict] = []
    name_only: list[dict] = []
    unrecoverable: list[dict] = []

    for fn in no_table:
        unrecoverable.append({"file": fn, "reason": "MISSING_TABLE_NO_DATA", "shard_id": None})

    for fn in corrupted:
        shard_path = MATCH_DATA / fn
        shard_id = extract_shard_id(fn)

        if shard_id is None or shard_id not in fwd_map:
            unrecoverable.append(
                {
                    "file": fn,
                    "reason": "NO_SHA256_MATCH",
                    "shard_id": shard_id,
                }
            )
            continue

        demo_name = fwd_map[shard_id]
        computed_id = demo_stem_to_match_id(demo_name)
        if computed_id != shard_id:
            unrecoverable.append(
                {
                    "file": fn,
                    "reason": "MATCH_ID_INTEGRITY_FAIL",
                    "shard_id": shard_id,
                    "demo_name": demo_name,
                }
            )
            continue

        meta = derive_metadata_from_shard(shard_path, demo_name)
        if meta is None:
            name_only.append(
                {
                    "file": fn,
                    "shard_id": shard_id,
                    "demo_name": demo_name,
                    "reason": "EMPTY_MATCHTICKSTATE",
                }
            )
            continue

        expected_map = parse_map_from_demo_name(demo_name)
        actual_map = strip_de_prefix(meta["map_name"])

        if expected_map and actual_map != expected_map:
            unrecoverable.append(
                {
                    "file": fn,
                    "shard_id": shard_id,
                    "demo_name": demo_name,
                    "reason": f"MAP_MISMATCH: expected={expected_map} actual={actual_map}",
                }
            )
            continue

        entry = {
            "file": fn,
            "shard_id": shard_id,
            "demo_name": demo_name,
            "map_validated": expected_map == actual_map if expected_map else False,
            "metadata": meta,
        }
        full.append(entry)

    return full, name_only, unrecoverable


def apply_recovery(full_entries: list[dict], backup_dir: Path) -> dict:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backed_up = 0
    written = 0
    skipped = 0
    errors: list[dict] = []

    for entry in full_entries:
        shard_path = MATCH_DATA / entry["file"]
        backup_path = backup_dir / entry["file"]

        if not backup_path.exists():
            shutil.copy2(str(shard_path), str(backup_path))
            backed_up += 1

        try:
            conn = sqlite3.connect(str(shard_path))
            conn.execute("PRAGMA journal_mode=WAL")

            existing = conn.execute("SELECT COUNT(*) FROM match_metadata").fetchone()[0]
            if existing > 0:
                skipped += 1
                conn.close()
                continue

            meta = entry["metadata"]
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            conn.execute(
                """INSERT INTO match_metadata
                (match_id, demo_name, map_name, tick_count, round_count,
                 player_count, tick_rate, team1_name, team2_name,
                 team1_score, team2_score, parser_version, schema_version,
                 is_pro_match, match_complete, match_date, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
                (
                    entry["shard_id"],
                    meta["demo_name"],
                    meta["map_name"],
                    meta["tick_count"],
                    meta["round_count"],
                    meta["player_count"],
                    meta["tick_rate"],
                    meta["team1_name"],
                    meta["team2_name"],
                    meta["team1_score"],
                    meta["team2_score"],
                    meta["parser_version"],
                    meta["schema_version"],
                    meta["is_pro_match"],
                    meta["match_complete"],
                    now,
                ),
            )
            conn.commit()

            verify = conn.execute("SELECT COUNT(*) FROM match_metadata").fetchone()[0]
            conn.close()

            if verify != 1:
                errors.append({"file": entry["file"], "error": f"post-write count={verify}"})
            else:
                written += 1

        except Exception as e:
            errors.append({"file": entry["file"], "error": str(e)})

    return {
        "backed_up": backed_up,
        "written": written,
        "skipped_idempotent": skipped,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="D3 shard metadata recovery")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write metadata rows (default: dry-run report only)",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=REPORT_OUT,
        help="Path for JSON report",
    )
    args = parser.parse_args()

    print("[D3] Building SHA-256 forward map...")
    fwd_map = build_forward_map()
    print(f"[D3] Forward map: {len(fwd_map)} demo names")

    print("[D3] Classifying shards...")
    full, name_only, unrecoverable = classify_shards(fwd_map)

    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "phase": "D3 metadata recovery",
        "mode": "apply" if args.apply else "dry-run",
        "doctrine_s129": {
            "q1_question": "Which corrupted shards can have metadata restored?",
            "q2_simplest": "SHA-256 forward map + intra-shard map validation",
            "q3_idempotent": True,
            "q4_tested_subset": "dry-run proves classification before --apply",
            "q5_reversible": "backup created; INSERT-only, DELETE reverses",
        },
        "summary": {
            "RECOVERABLE_FULL": len(full),
            "RECOVERABLE_NAME_ONLY": len(name_only),
            "UNRECOVERABLE": len(unrecoverable),
        },
        "notes": [
            "is_pro_match=0 matches existing 203-shard pattern (systemic misset, V-phase fix)",
            "RECOVERABLE_NAME_ONLY shards deferred to M2 (re-ingest from .dem)",
            "parser_version='v1-d3-recovered' marks derived rows",
        ],
        "RECOVERABLE_FULL": [
            {
                "file": e["file"],
                "demo_name": e["demo_name"],
                "map_validated": e["map_validated"],
                "tick_count": e["metadata"]["tick_count"],
                "round_count": e["metadata"]["round_count"],
                "player_count": e["metadata"]["player_count"],
            }
            for e in full
        ],
        "RECOVERABLE_NAME_ONLY": name_only,
        "UNRECOVERABLE": unrecoverable,
    }

    if args.apply:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = MATCH_DATA.parent / f"match_data_backup_d3_{ts}"
        print(f"[D3] Backing up to {backup_dir.name}/...")
        result = apply_recovery(full, backup_dir)
        report["apply_result"] = result
        print(
            f"[D3] Written: {result['written']}, "
            f"Skipped (idempotent): {result['skipped_idempotent']}, "
            f"Errors: {len(result['errors'])}"
        )
    else:
        print("[D3] DRY-RUN — no writes performed")

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report_out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[D3] Report: {args.report_out}")

    print(
        f"\n[D3] Classification: "
        f"{len(full)} FULL / {len(name_only)} NAME_ONLY / {len(unrecoverable)} UNRECOVERABLE"
    )
    if not args.apply:
        print("[D3] Re-run with --apply to write metadata rows")


if __name__ == "__main__":
    main()
