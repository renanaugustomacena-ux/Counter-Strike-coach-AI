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

# Columns written to playertickstate (excludes autoincrement id)
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


def rebuild_tick_data(db_manager, all_demos: list[Path], incremental: bool = False):
    """Read per-match DBs and write to monolith PlayerTickState via raw sqlite3."""
    from sqlalchemy import text

    total_ticks = 0
    demos_processed = 0

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

        match_id = demo_stem_to_match_id(stem)
        match_db_path = MATCH_DATA_DIR / f"match_{match_id}.db"

        if not match_db_path.exists():
            print(f"  SKIP {stem} -- no per-match DB")
            continue

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

        except Exception as e:
            try:
                mono_conn.rollback()
            except Exception:
                pass
            print(f"  ERROR {stem}: {e}")
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


def main():
    from sqlalchemy import text

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
    from Programma_CS2_RENAN.core.config import save_user_setting

    print("=== CS2 Coach AI -- Rebuild Monolith from Per-Match DBs ===\n")

    # Init
    init_database()
    db = get_db_manager()
    save_user_setting("PRO_DEMO_PATH", str(DEMO_BASE))

    # Discover all demos (including ingested/)
    all_demos = sorted(DEMO_BASE.rglob("*.dem"))
    print(f"Found {len(all_demos)} .dem files on disk.")
    print(f"Per-match DB directory: {MATCH_DATA_DIR}\n")

    if not all_demos:
        print("No demos found. Nothing to rebuild.")
        return

    # Phase 1: Tick data from per-match DBs (fast -- no .dem parsing)
    incremental = "--full" not in sys.argv
    if incremental:
        print("--- Phase 1: Rebuilding PlayerTickState (incremental -- use --full to clear) ---")
    else:
        print("--- Phase 1: Rebuilding PlayerTickState from per-match DBs ---")
    t_start = time.monotonic()
    demos_done, tick_total = rebuild_tick_data(db, all_demos, incremental=incremental)
    t_ticks = time.monotonic() - t_start
    print(
        f"\n  Phase 1 complete: {tick_total:,} new ticks from {demos_done} demos ({t_ticks:.1f}s)\n"
    )

    # Phase 2: Aggregate stats from .dem files (parse_demo is fast for headers)
    print("--- Phase 2: Rebuilding PlayerMatchStats from .dem files ---")
    t_start = time.monotonic()
    stats_total = rebuild_match_stats(db, all_demos)
    t_stats = time.monotonic() - t_start
    print(f"\n  Phase 2 complete: {stats_total} PlayerMatchStats rows ({t_stats:.1f}s)\n")

    # Phase 3: Backfill pro_player_id from HLTV NicknameResolver
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
            session.exec(text("SELECT COUNT(*) FROM playermatchstats WHERE is_pro = 1")).scalar()
            or 0
        )

    print("=== Summary ===")
    print(f"  PlayerTickState:  {final_ticks:,} ticks from {final_demos} demos")
    print(f"  PlayerMatchStats: {final_stats} pro rows")
    print(f"  Total time:       {t_ticks + t_stats:.1f}s")
    print("\nMonolith is ready. Run: python tools/ingest_pro_demos.py --retrain-only")


if __name__ == "__main__":
    main()
