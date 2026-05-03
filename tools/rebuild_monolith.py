#!/usr/bin/env python3
"""
Rebuild the monolith DB (PlayerMatchStats + PlayerTickState) from existing
per-match databases WITHOUT re-parsing .dem files.

Per-match DBs in DEMO_PRO_PLAYERS/match_data/ already contain full tick data.
This script reads them, transforms to monolith schema, and bulk-writes.

For PlayerMatchStats: still needs parse_demo() per .dem file (fast, header only).

Optimised for write throughput: raw sqlite3 + aggressive PRAGMAs + executemany +
index drop/recreate.  Safe because this is an offline, re-runnable tool.

Usage:
    python tools/rebuild_monolith.py          # incremental (skip existing demos)
    python tools/rebuild_monolith.py --full   # clear + full rebuild
"""
import hashlib
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Programma_CS2_RENAN.core.config import CORE_DB_DIR, get_pro_demo_base

DEMO_BASE = get_pro_demo_base()
MATCH_DATA_DIR = DEMO_BASE / "match_data"
MONOLITH_DB_PATH = os.path.join(CORE_DB_DIR, "database.db")

# Column mapping: per-match matchtickstate -> monolith playertickstate
COLUMN_MAP = {
    "tick": "tick",
    "player_name": "player_name",
    # steamid is forwarded so a player's identity survives nickname collisions
    # and team changes. Added in migration d4e5f6a7b8c9 (D1 prereq).
    "steamid": "steamid",
    "pos_x": "pos_x",
    "pos_y": "pos_y",
    "pos_z": "pos_z",
    "yaw": "view_x",
    "pitch": "view_y",
    "health": "health",
    "armor": "armor",
    "is_crouching": "is_crouching",
    "is_scoped": "is_scoped",
    "active_weapon": "active_weapon",
    "equipment_value": "equipment_value",
    "enemies_visible": "enemies_visible",
    "is_blinded": "is_blinded",
    "round_number": "round_number",
    "time_in_round": "time_in_round",
    "bomb_planted": "bomb_planted",
    "teammates_alive": "teammates_alive",
    "enemies_alive": "enemies_alive",
    "team_economy": "team_economy",
    "map_name": "map_name",
}

# Columns written to playertickstate (excludes autoincrement id).
# Order is ARBITRARY for the INSERT statement (column-listed insert is safe
# against schema-position drift) but must match the order of values appended
# to the row tuple in rebuild_tick_data. Adding a new column requires updating
# (1) this list, (2) COLUMN_MAP if the source column has a different name,
# and (3) the df.reindex() call so the value lands at the right tuple index.
TICK_INSERT_COLUMNS = [
    "created_at",
    "match_id",
    "tick",
    "player_name",
    "demo_name",
    "pos_x",
    "pos_y",
    "pos_z",
    "view_x",
    "view_y",
    "health",
    "armor",
    "is_crouching",
    "is_scoped",
    "has_helmet",
    "has_defuser",
    "active_weapon",
    "equipment_value",
    "enemies_visible",
    "is_blinded",
    "round_outcome",
    "round_number",
    "time_in_round",
    "bomb_planted",
    "teammates_alive",
    "enemies_alive",
    "team_economy",
    "map_name",
    # steamid added by migration d4e5f6a7b8c9 (D1 prereq).
    "steamid",
]

TICK_INSERT_SQL = (
    f"INSERT INTO playertickstate ({','.join(TICK_INSERT_COLUMNS)}) "
    f"VALUES ({','.join('?' * len(TICK_INSERT_COLUMNS))})"
)

# Indexes on playertickstate (from db_models.py)
PLAYERTICKSTATE_INDEXES = [
    ("ix_tick_demo_tick", "CREATE INDEX ix_tick_demo_tick ON playertickstate (demo_name, tick)"),
    (
        "ix_pts_player_demo",
        "CREATE INDEX ix_pts_player_demo ON playertickstate (player_name, demo_name)",
    ),
    (
        "ix_playertickstate_match_id",
        "CREATE INDEX ix_playertickstate_match_id ON playertickstate (match_id)",
    ),
    ("ix_playertickstate_tick", "CREATE INDEX ix_playertickstate_tick ON playertickstate (tick)"),
    (
        "ix_playertickstate_player_name",
        "CREATE INDEX ix_playertickstate_player_name ON playertickstate (player_name)",
    ),
    (
        "ix_playertickstate_demo_name",
        "CREATE INDEX ix_playertickstate_demo_name ON playertickstate (demo_name)",
    ),
]

KNOWN_CS2_MAPS = {"mirage", "dust2", "inferno", "nuke", "overpass", "anubis", "ancient", "vertigo"}


def demo_stem_to_match_id(stem: str) -> int:
    return int(hashlib.sha256(stem.encode()).hexdigest(), 16) % (2**63 - 1)


def _set_bulk_pragmas(conn: sqlite3.Connection) -> None:
    """Set aggressive PRAGMAs for offline bulk rebuild (not production)."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-2000000")  # 2 GB
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=4294967296")  # 4 GB
    conn.execute("PRAGMA busy_timeout=120000")  # 2 min


def _restore_pragmas(conn: sqlite3.Connection) -> None:
    """Restore conservative PRAGMAs after bulk operations."""
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-2000")  # ~2 MB default
    conn.execute("PRAGMA temp_store=DEFAULT")
    conn.execute("PRAGMA mmap_size=0")


def _drop_tick_indexes(conn: sqlite3.Connection) -> None:
    """Drop all playertickstate indexes for faster bulk insert."""
    for idx_name, _ in PLAYERTICKSTATE_INDEXES:
        conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
    conn.commit()
    print("  Dropped 6 playertickstate indexes for bulk load.")


def _recreate_tick_indexes(conn: sqlite3.Connection) -> None:
    """Recreate all playertickstate indexes after bulk insert."""
    print("  Recreating 6 playertickstate indexes (this may take a while)...")
    t0 = time.monotonic()
    for idx_name, create_sql in PLAYERTICKSTATE_INDEXES:
        ti = time.monotonic()
        conn.execute(create_sql)
        print(f"    {idx_name} ({time.monotonic() - ti:.1f}s)")
    conn.commit()
    print(f"  All indexes recreated ({time.monotonic() - t0:.1f}s total).")


def _infer_map_name(stem: str) -> str:
    """Infer map name from demo file stem (e.g. 'furia-vs-navi-m1-mirage' -> 'de_mirage')."""
    parts = stem.split("-")
    return next((f"de_{p}" for p in reversed(parts) if p in KNOWN_CS2_MAPS), "de_unknown")


def _synthetic_demo_paths_from_match_dbs(match_data_dir: Path) -> list[Path]:
    """Build synthetic demo paths from match_*.db files (D1 source mode).

    rebuild_tick_data() drives off ``demo_path.stem`` to compute match_id
    and to populate the ``demo_name`` column. The legacy mode walks the
    .dem files on disk; D1 needs to process every match_*.db regardless
    of whether the source .dem still exists. Each match_*.db carries
    ``match_metadata.demo_name``; we read it and synthesize a Path so
    the existing function logic works unchanged.

    Files missing the ``match_metadata`` table or the ``demo_name`` row
    are skipped; D3 phase handles their recovery separately.
    """
    if not match_data_dir.is_dir():
        return []
    paths: list[Path] = []
    for match_db in sorted(match_data_dir.glob("match_*.db")):
        try:
            con = sqlite3.connect(f"file:{match_db}?mode=ro&immutable=1", uri=True)
            row = con.execute("SELECT demo_name FROM match_metadata LIMIT 1").fetchone()
            con.close()
        except sqlite3.OperationalError:
            # match_metadata table absent (corrupted file); skip.
            continue
        if not row or not row[0]:
            continue
        demo_stem = str(row[0])
        if demo_stem.endswith(".dem"):
            demo_stem = demo_stem[: -len(".dem")]
        # Synthetic prefix makes it obvious in logs that the path is not real.
        paths.append(Path(f"/synthetic-from-match-db/{demo_stem}.dem"))
    return paths


def _check_disk_or_abort(threshold_gb: float, anchor: Path) -> None:
    """Abort the run if the filesystem holding ``anchor`` has less than
    ``threshold_gb`` GB free. Used to prevent D1 from filling the disk
    during the ~414M-row tick migration.
    """
    if threshold_gb <= 0:
        return
    import shutil

    free = shutil.disk_usage(anchor).free
    if free < threshold_gb * (1024**3):
        raise RuntimeError(
            f"Disk pressure abort: {free / 1024**3:.1f} GB free at {anchor} "
            f"(threshold {threshold_gb} GB)"
        )


def _write_checkpoint(path: Path | None, state: dict) -> None:
    """Persist per-match progress to a JSON checkpoint file.

    Resume after a kill picks up at the next unprocessed demo. State
    schema:
      {
        "started_at": iso_str,
        "completed": [demo_stem, ...],
        "errors":    [{"demo": str, "error": str, "at": iso_str}, ...],
        "in_progress": str | null,
        "wall_clock_seconds": float,
      }
    """
    if path is None:
        return
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def _load_checkpoint(path: Path | None) -> dict:
    """Read existing checkpoint state if present; otherwise return seed state."""
    if path is None or not path.exists():
        return {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed": [],
            "errors": [],
            "in_progress": None,
            "wall_clock_seconds": 0.0,
        }
    import json

    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed": [],
            "errors": [],
            "in_progress": None,
            "wall_clock_seconds": 0.0,
        }


def rebuild_tick_data(
    db_manager,
    all_demos: list[Path],
    incremental: bool = False,
    *,
    checkpoint_path: Path | None = None,
    disk_abort_gb: float = 0.0,
    wal_checkpoint_every: int = 0,
    match_id_filter: int | None = None,
    limit: int | None = None,
):
    """Read per-match DBs and write to monolith PlayerTickState via raw sqlite3.

    D1 additions (all opt-in via kwargs; legacy positional callers unchanged):
      checkpoint_path: persist per-match progress here; resume skips completed.
      disk_abort_gb: abort if the disk falls below this much free.
      wal_checkpoint_every: PRAGMA wal_checkpoint(TRUNCATE) every N demos.
      match_id_filter: process only the demo whose stem hashes to this id.
      limit: process at most N demos this run.
    """
    from sqlalchemy import text

    total_ticks = 0
    demos_processed = 0

    # Optional pre-loop filters (D1 additions)
    if match_id_filter is not None:
        all_demos = [p for p in all_demos if demo_stem_to_match_id(p.stem) == match_id_filter]
        print(f"  --match-id filter: {len(all_demos)} demo(s) match id {match_id_filter}.")
    if limit is not None and limit > 0:
        all_demos = all_demos[:limit]
        print(f"  --limit applied: processing at most {len(all_demos)} demo(s).")

    # Load checkpoint state for resume (D1 addition)
    checkpoint = _load_checkpoint(checkpoint_path)
    completed_via_checkpoint = set(checkpoint.get("completed") or [])
    if completed_via_checkpoint:
        print(f"  Checkpoint resume: {len(completed_via_checkpoint)} demo(s) already done.")
    run_started = time.monotonic()

    # Determine existing demos for incremental mode
    if incremental:
        with db_manager.get_session() as session:
            existing = session.exec(text("SELECT DISTINCT demo_name FROM playertickstate")).all()
            existing_stems = {row[0] for row in existing}
        print(f"  Incremental mode: {len(existing_stems)} demos already in monolith.")
    else:
        existing_stems = set()
        # Clear existing tick data via SQLAlchemy (once)
        with db_manager.get_session() as session:
            old_count = session.exec(text("SELECT COUNT(*) FROM playertickstate")).scalar()
            if old_count and old_count > 0:
                session.exec(text("DELETE FROM playertickstate"))
                session.commit()
                print(f"  Cleared {old_count:,} old PlayerTickState rows.")

    # --- Raw sqlite3 for bulk writes ---
    mono_conn = sqlite3.connect(MONOLITH_DB_PATH, timeout=120)
    _set_bulk_pragmas(mono_conn)

    # Drop indexes for full rebuild (not incremental)
    if not incremental:
        _drop_tick_indexes(mono_conn)

    chunk_size = 200_000

    for demo_path in all_demos:
        stem = demo_path.stem

        if stem in existing_stems:
            print(f"  SKIP {stem} -- already in monolith")
            continue

        if stem in completed_via_checkpoint:
            print(f"  SKIP {stem} -- already in checkpoint (resume)")
            continue

        # Disk-pressure abort BEFORE reading source so we don't half-write
        # under low-disk conditions.
        try:
            _check_disk_or_abort(disk_abort_gb, Path(MONOLITH_DB_PATH).parent)
        except RuntimeError as disk_err:
            print(f"  ABORT {stem} -- {disk_err}")
            checkpoint["errors"].append(
                {
                    "demo": stem,
                    "error": str(disk_err),
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            checkpoint["wall_clock_seconds"] = time.monotonic() - run_started
            _write_checkpoint(checkpoint_path, checkpoint)
            break

        match_id = demo_stem_to_match_id(stem)
        match_db_path = MATCH_DATA_DIR / f"match_{match_id}.db"

        if not match_db_path.exists():
            print(f"  SKIP {stem} -- no per-match DB")
            continue

        # Mark in-progress before the heavy work so a kill mid-flight
        # leaves a breadcrumb for diagnosis.
        checkpoint["in_progress"] = stem
        _write_checkpoint(checkpoint_path, checkpoint)

        t0 = time.monotonic()

        try:
            # Open source per-match DB with tuned PRAGMAs
            src_conn = sqlite3.connect(str(match_db_path), timeout=30)
            src_conn.execute("PRAGMA journal_mode=WAL")
            src_conn.execute("PRAGMA synchronous=NORMAL")
            src_conn.execute("PRAGMA cache_size=-200000")  # 200 MB
            src_conn.execute("PRAGMA mmap_size=1073741824")  # 1 GB
            src_conn.execute("PRAGMA busy_timeout=30000")

            # Detect tick table name
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", src_conn)
            table_names = tables["name"].tolist()

            if "matchtickstate" in table_names:
                source_table = "matchtickstate"
            elif "match_tick_state" in table_names:
                source_table = "match_tick_state"
            else:
                print(f"  SKIP {stem} -- no tick table (tables: {table_names})")
                src_conn.close()
                continue

            # Build SELECT with only columns that exist in source
            src_cols = pd.read_sql(f"PRAGMA table_info({source_table})", src_conn)
            available_cols = set(src_cols["name"].tolist())

            select_cols = []
            rename_map = {}
            for src_col, dst_col in COLUMN_MAP.items():
                if src_col in available_cols:
                    select_cols.append(src_col)
                    if src_col != dst_col:
                        rename_map[src_col] = dst_col

            if not select_cols:
                print(f"  SKIP {stem} -- no matching columns")
                src_conn.close()
                continue

            # Read entire source table into memory, then release source DB
            df = pd.read_sql(f"SELECT {','.join(select_cols)} FROM {source_table}", src_conn)
            src_conn.close()

            if df.empty:
                print(f"  SKIP {stem} -- empty table")
                continue

            # Rename to monolith schema
            df = df.rename(columns=rename_map)

            # Add monolith-only columns
            now_utc = datetime.now(timezone.utc).isoformat()
            df["match_id"] = match_id
            df["demo_name"] = stem
            df["created_at"] = now_utc

            # Fill missing columns with schema defaults
            for col in ("round_number", "teammates_alive", "enemies_alive", "team_economy"):
                if col not in df.columns:
                    df[col] = 0
            if "time_in_round" not in df.columns:
                df["time_in_round"] = 0.0
            if "bomb_planted" not in df.columns:
                df["bomb_planted"] = 0
            for col in ("has_helmet", "has_defuser"):
                if col not in df.columns:
                    df[col] = 0
            if "round_outcome" not in df.columns:
                df["round_outcome"] = None
            # steamid is nullable; legacy match_tick_state (empty deprecated
            # table) lacked the column — fill with None so reindex doesn't
            # produce NaN (which sqlite3 would store as a float).
            if "steamid" not in df.columns:
                df["steamid"] = None

            # Infer map_name if absent or invalid
            if "map_name" not in df.columns or df["map_name"].iloc[0] in (
                None,
                "",
                "de_unknown",
            ):
                df["map_name"] = _infer_map_name(stem)

            # Reorder columns to match INSERT statement; NaN -> None for sqlite3
            df = df.reindex(columns=TICK_INSERT_COLUMNS)
            df = df.where(pd.notna(df), None)

            # Write in chunks within a single implicit transaction per demo
            rows_written = 0
            for start in range(0, len(df), chunk_size):
                chunk = df.iloc[start : start + chunk_size]
                rows = list(chunk.itertuples(index=False, name=None))
                mono_conn.executemany(TICK_INSERT_SQL, rows)
                rows_written += len(rows)
            mono_conn.commit()  # One commit per demo

            elapsed = time.monotonic() - t0
            total_ticks += rows_written
            demos_processed += 1
            rate_mb = (rows_written * 28 * 8) / (1024 * 1024 * max(elapsed, 0.001))
            print(f"  OK {stem}: {rows_written:,} ticks ({elapsed:.1f}s, ~{rate_mb:.0f} MB/s)")

            # D1: per-match checkpoint write + periodic WAL checkpoint.
            checkpoint["completed"].append(stem)
            checkpoint["in_progress"] = None
            checkpoint["wall_clock_seconds"] = time.monotonic() - run_started
            _write_checkpoint(checkpoint_path, checkpoint)
            if wal_checkpoint_every > 0 and demos_processed % wal_checkpoint_every == 0:
                try:
                    mono_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    mono_conn.commit()
                    print(f"  WAL checkpoint truncated after {demos_processed} demos")
                except sqlite3.OperationalError as wal_err:
                    print(f"  WAL checkpoint warning: {wal_err}")

        except Exception as e:
            try:
                mono_conn.rollback()
            except Exception:
                pass
            print(f"  ERROR {stem}: {e}")
            checkpoint["errors"].append(
                {
                    "demo": stem,
                    "error": str(e),
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            checkpoint["in_progress"] = None
            checkpoint["wall_clock_seconds"] = time.monotonic() - run_started
            _write_checkpoint(checkpoint_path, checkpoint)
            continue

    # Recreate indexes after bulk load (full rebuild only)
    if not incremental:
        _recreate_tick_indexes(mono_conn)

    _restore_pragmas(mono_conn)
    mono_conn.close()

    return demos_processed, total_ticks


def _sanitize_stat(val):
    """Sanitize a single stat value: NaN/Inf -> 0.0."""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return 0.0
    return val


def rebuild_match_stats(db_manager, all_demos: list[Path]):
    """Parse .dem files for aggregate stats and bulk-write PlayerMatchStats."""
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    # Clear existing pro stats via SQLAlchemy (respects ORM constraints)
    with db_manager.get_session() as session:
        old_stats = session.exec(
            select(PlayerMatchStats).where(PlayerMatchStats.is_pro == True)  # noqa: E712
        ).all()
        for s in old_stats:
            session.delete(s)
        session.commit()
    print(f"  Cleared {len(old_stats)} old pro PlayerMatchStats.")

    # Discover column names from schema (minus autoincrement id)
    stats_conn = sqlite3.connect(MONOLITH_DB_PATH, timeout=120)
    _set_bulk_pragmas(stats_conn)

    col_info = stats_conn.execute("PRAGMA table_info(playermatchstats)").fetchall()
    all_columns = [row[1] for row in col_info if row[1] != "id"]

    stats_insert_sql = (
        f"INSERT OR REPLACE INTO playermatchstats ({','.join(all_columns)}) "
        f"VALUES ({','.join('?' * len(all_columns))})"
    )

    # Columns with non-zero defaults
    special_defaults = {
        "dataset_split": "UNASSIGNED",
        "data_quality": "partial",
        "sample_weight": 1.0,
    }

    all_rows = []
    total_parsed = 0

    for demo_path in all_demos:
        t0 = time.monotonic()
        try:
            df = parse_demo(str(demo_path), target_player="ALL")
            if df.empty:
                print(f"  SKIP {demo_path.stem} -- parse_demo returned empty")
                continue

            clean_demo_name = demo_path.stem
            now_utc = datetime.now(timezone.utc).isoformat()

            for _, row in df.iterrows():
                stats_dict = row.to_dict()
                p_name = stats_dict.pop("player_name", "unknown")

                # Sanitize NaN/Inf (R3-H09)
                for key in list(stats_dict.keys()):
                    stats_dict[key] = _sanitize_stat(stats_dict[key])

                # Clamp rating to [0, 5.0] (DB CHECK constraint)
                if "rating" in stats_dict:
                    stats_dict["rating"] = max(0.0, min(5.0, float(stats_dict["rating"])))

                # Clamp avg_kills, avg_adr >= 0 (DB CHECK constraints)
                for field in ("avg_kills", "avg_adr"):
                    if field in stats_dict and stats_dict[field] < 0:
                        stats_dict[field] = 0.0

                # Build row tuple matching column order from schema
                row_values = []
                for col in all_columns:
                    if col == "player_name":
                        row_values.append(p_name)
                    elif col == "demo_name":
                        row_values.append(clean_demo_name)
                    elif col == "is_pro":
                        row_values.append(1)  # sqlite3 boolean
                    elif col == "pro_player_id":
                        row_values.append(None)  # Phase 3 handles linking
                    elif col in ("match_date", "processed_at"):
                        row_values.append(now_utc)
                    elif col in stats_dict:
                        row_values.append(stats_dict[col])
                    elif col in special_defaults:
                        row_values.append(special_defaults[col])
                    else:
                        row_values.append(0.0)  # Numeric default

                all_rows.append(tuple(row_values))

            elapsed = time.monotonic() - t0
            total_parsed += len(df)
            print(f"  OK {demo_path.stem}: {len(df)} players ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  ERROR {demo_path.stem}: {e}")
            continue

    # Single bulk insert for all player stats
    if all_rows:
        stats_conn.executemany(stats_insert_sql, all_rows)
        stats_conn.commit()
        print(f"  Bulk-inserted {len(all_rows)} PlayerMatchStats rows (1 commit).")

    _restore_pragmas(stats_conn)
    stats_conn.close()

    return total_parsed


def _parse_argv(argv: list[str]):
    import argparse

    parser = argparse.ArgumentParser(
        prog="rebuild_monolith",
        description=(
            "Rebuild monolith DB from per-match DBs. D1 phase of the v3 "
            "restoration plan: --phase tick-only --source match-dbs."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Legacy: clear playertickstate before rebuilding (default: incremental).",
    )
    parser.add_argument(
        "--phase",
        choices=("full", "tick-only", "match-stats-only", "linker-only"),
        default="full",
        help="Which phase(s) to run. D1 uses 'tick-only' (default: full = legacy 1+2+3).",
    )
    parser.add_argument(
        "--source",
        choices=("dem-files", "match-dbs"),
        default="dem-files",
        help=(
            "Demo enumeration source. 'dem-files' walks DEMO_PRO_PLAYERS for .dem "
            "files (legacy). 'match-dbs' enumerates match_*.db files directly so "
            "matches without surviving .dem files still get migrated (D1)."
        ),
    )
    parser.add_argument(
        "--match-id",
        type=int,
        default=None,
        help="Process only the demo whose stem hashes to this match_id (debug).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N demos this run (smoke test / resume slice).",
    )
    parser.add_argument(
        "--checkpoint-file",
        type=Path,
        default=Path("Programma_CS2_RENAN/backups/tick_migration_state.json"),
        help="JSON file recording per-match progress for resume after kill.",
    )
    parser.add_argument(
        "--disk-abort-gb",
        type=float,
        default=50.0,
        help="Abort if MONOLITH_DB_PATH disk falls below this many GB free.",
    )
    parser.add_argument(
        "--wal-checkpoint-every",
        type=int,
        default=10,
        help="PRAGMA wal_checkpoint(TRUNCATE) every N demos (0 disables).",
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help=(
            "Skip d_track_running lock acquisition. Only use after manually "
            "stopping hltv_sync_service and confirming via ps."
        ),
    )
    return parser.parse_args(argv)


def _enumerate_demos(source: str) -> list[Path]:
    if source == "match-dbs":
        paths = _synthetic_demo_paths_from_match_dbs(MATCH_DATA_DIR)
        print(f"Source=match-dbs: enumerated {len(paths)} match_*.db files.")
        return paths
    paths = sorted(DEMO_BASE.rglob("*.dem"))
    print(f"Source=dem-files: found {len(paths)} .dem files on disk.")
    return paths


def main():
    from sqlalchemy import text

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
    from Programma_CS2_RENAN.core.config import save_user_setting

    args = _parse_argv(sys.argv[1:])
    incremental = not args.full

    print("=== CS2 Coach AI -- Rebuild Monolith from Per-Match DBs ===")
    print(f"  Phase:               {args.phase}")
    print(f"  Source:              {args.source}")
    print(f"  Mode:                {'incremental' if incremental else 'full (clears tickstate)'}")
    print(f"  Checkpoint:          {args.checkpoint_file}")
    print(f"  Disk abort threshold: {args.disk_abort_gb} GB")
    print(f"  WAL checkpoint every: {args.wal_checkpoint_every} demos")
    print(f"  Lock acquisition:    {'OFF (escape hatch)' if args.no_lock else 'd_track_running'}")
    print()

    # Acquire lock unless explicitly disabled. The lock blocks hltv_sync_service
    # and ad-hoc ingestion from concurrent main-DB writes (see
    # docs/concurrency_policy.md).
    lock_acquired = False
    if not args.no_lock:
        from Programma_CS2_RENAN.core import lock_files

        lock_files.install_signal_handlers()
        try:
            lock_files.acquire("d_track_running")
            lock_acquired = True
            print("  Lock acquired: d_track_running\n")
        except lock_files.LockConflict as conflict:
            print(f"  Lock acquisition FAILED: {conflict}")
            print("  Stop the conflicting process or pass --no-lock to override.")
            sys.exit(2)

    try:
        # Init
        init_database()
        db = get_db_manager()
        save_user_setting("PRO_DEMO_PATH", str(DEMO_BASE))

        all_demos = _enumerate_demos(args.source)
        print(f"Per-match DB directory: {MATCH_DATA_DIR}\n")

        if not all_demos:
            print("No demos to process. Nothing to rebuild.")
            return

        run_phases = {
            "full": ("tick", "stats", "linker"),
            "tick-only": ("tick",),
            "match-stats-only": ("stats",),
            "linker-only": ("linker",),
        }[args.phase]

        demos_done = 0
        tick_total = 0
        stats_total = 0
        t_ticks = 0.0
        t_stats = 0.0

        if "tick" in run_phases:
            print("--- Phase 1: Rebuilding PlayerTickState ---")
            t_start = time.monotonic()
            demos_done, tick_total = rebuild_tick_data(
                db,
                all_demos,
                incremental=incremental,
                checkpoint_path=args.checkpoint_file,
                disk_abort_gb=args.disk_abort_gb,
                wal_checkpoint_every=args.wal_checkpoint_every,
                match_id_filter=args.match_id,
                limit=args.limit,
            )
            t_ticks = time.monotonic() - t_start
            print(
                f"\n  Phase 1 complete: {tick_total:,} new ticks from "
                f"{demos_done} demos ({t_ticks:.1f}s)\n"
            )

        if "stats" in run_phases:
            print("--- Phase 2: Rebuilding PlayerMatchStats from .dem files ---")
            t_start = time.monotonic()
            stats_total = rebuild_match_stats(db, all_demos)
            t_stats = time.monotonic() - t_start
            print(f"\n  Phase 2 complete: {stats_total} PlayerMatchStats rows ({t_stats:.1f}s)\n")

        if "linker" in run_phases:
            print("--- Phase 3: Linking PlayerMatchStats to HLTV ProPlayer records ---")
            try:
                from Programma_CS2_RENAN.backend.processing.baselines.pro_player_linker import (
                    ProPlayerLinker,
                )

                result = ProPlayerLinker().backfill_all()
                print(
                    f"  Linked: {result['linked']}, "
                    f"Unresolved: {result['unresolved']} {result['unresolved_names']}\n"
                )
            except Exception as e:
                print(f"  WARNING: Pro player linking failed: {e}\n")

        # Summary
        with db.get_session() as session:
            final_ticks = session.exec(text("SELECT COUNT(*) FROM playertickstate")).scalar() or 0
            final_demos = (
                session.exec(text("SELECT COUNT(DISTINCT demo_name) FROM playertickstate")).scalar()
                or 0
            )
            final_stats = (
                session.exec(
                    text("SELECT COUNT(*) FROM playermatchstats WHERE is_pro = 1")
                ).scalar()
                or 0
            )

        # DL-1: Record provenance for monolith rebuild
        if demos_done > 0 and "tick" in run_phases:
            db.record_lineage(
                entity_type="batch_monolith_rebuild",
                entity_id=tick_total,
                source_demo=f"{demos_done}_demos",
                processing_step="monolith_rebuild",
            )

        print("=== Summary ===")
        print(f"  PlayerTickState:  {final_ticks:,} ticks from {final_demos} demos")
        print(f"  PlayerMatchStats: {final_stats} pro rows")
        print(f"  Total time:       {t_ticks + t_stats:.1f}s")
    finally:
        if lock_acquired:
            from Programma_CS2_RENAN.core import lock_files

            lock_files.release("d_track_running")
            print("\n  Lock released: d_track_running")


if __name__ == "__main__":
    main()
