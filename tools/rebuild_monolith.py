#!/usr/bin/env python3
"""
Rebuild the monolith DB (PlayerMatchStats + PlayerTickState) from existing
per-match databases WITHOUT re-parsing .dem files.

Per-match DBs in DEMO_PRO_PLAYERS/match_data/ already contain full tick data.
This script reads them, transforms to monolith schema, and bulk-writes.

For PlayerMatchStats: still needs parse_demo() per .dem file (fast, header only).

Usage:
    python tools/rebuild_monolith.py
"""
import hashlib
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEMO_BASE = Path("/media/admin/usb-ssd/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS")
MATCH_DATA_DIR = DEMO_BASE / "match_data"

# Column mapping: per-match matchtickstate → monolith playertickstate
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


def demo_stem_to_match_id(stem: str) -> int:
    return int(hashlib.sha256(stem.encode()).hexdigest(), 16) % (2**63 - 1)


def rebuild_tick_data(db_manager, all_demos: list[Path], incremental: bool = False):
    """Read per-match DBs and write to monolith PlayerTickState."""
    from sqlalchemy import text

    monolith_engine = db_manager.engine
    total_ticks = 0
    demos_processed = 0

    if incremental:
        # Skip demos already in monolith
        with db_manager.get_session() as session:
            existing = session.exec(text("SELECT DISTINCT demo_name FROM playertickstate")).all()
            existing_stems = {row[0] for row in existing}
        print(f"  Incremental mode: {len(existing_stems)} demos already in monolith.")
    else:
        existing_stems = set()
        # Clear existing tick data
        with db_manager.get_session() as session:
            old_count = session.exec(text("SELECT COUNT(*) FROM playertickstate")).scalar()
            if old_count and old_count > 0:
                session.exec(text("DELETE FROM playertickstate"))
                session.commit()
                print(f"  Cleared {old_count:,} old PlayerTickState rows.")

    for demo_path in all_demos:
        stem = demo_path.stem

        if stem in existing_stems:
            print(f"  SKIP {stem} — already in monolith")
            continue
        match_id = demo_stem_to_match_id(stem)
        match_db_path = MATCH_DATA_DIR / f"match_{match_id}.db"

        if not match_db_path.exists():
            print(f"  SKIP {stem} — no per-match DB")
            continue

        t0 = time.monotonic()

        try:
            conn = sqlite3.connect(str(match_db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            # Check which table exists
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
            table_names = tables["name"].tolist()

            if "matchtickstate" in table_names:
                source_table = "matchtickstate"
            elif "match_tick_state" in table_names:
                source_table = "match_tick_state"
            else:
                print(f"  SKIP {stem} — no tick table in DB (tables: {table_names})")
                conn.close()
                continue

            # Read source columns that exist
            src_cols = pd.read_sql(f"PRAGMA table_info({source_table})", conn)
            available_cols = set(src_cols["name"].tolist())

            # Build SELECT with only available columns
            select_cols = []
            rename_map = {}
            for src_col, dst_col in COLUMN_MAP.items():
                if src_col in available_cols:
                    select_cols.append(src_col)
                    if src_col != dst_col:
                        rename_map[src_col] = dst_col

            if not select_cols:
                print(f"  SKIP {stem} — no matching columns")
                conn.close()
                continue

            # Read in chunks to manage memory (650K+ rows per match)
            chunk_size = 50_000
            chunks_written = 0
            for chunk in pd.read_sql(
                f"SELECT {','.join(select_cols)} FROM {source_table}",
                conn,
                chunksize=chunk_size,
            ):
                chunk = chunk.rename(columns=rename_map)
                chunk["match_id"] = match_id
                chunk["demo_name"] = stem
                chunk["created_at"] = datetime.now(timezone.utc)

                # Fill missing monolith columns with defaults
                for col in [
                    "round_number",
                    "time_in_round",
                    "bomb_planted",
                    "teammates_alive",
                    "enemies_alive",
                    "team_economy",
                ]:
                    if col not in chunk.columns:
                        default = 0.0 if col == "time_in_round" else 0
                        chunk[col] = default

                # Infer map_name from demo stem if not in per-match DB
                if "map_name" not in chunk.columns or chunk["map_name"].iloc[0] in (
                    None,
                    "",
                    "de_unknown",
                ):
                    known_maps = {
                        "mirage",
                        "dust2",
                        "inferno",
                        "nuke",
                        "overpass",
                        "anubis",
                        "ancient",
                        "vertigo",
                    }
                    parts = stem.split("-")
                    inferred = next(
                        (f"de_{p}" for p in reversed(parts) if p in known_maps), "de_unknown"
                    )
                    chunk["map_name"] = inferred

                chunk.to_sql(
                    "playertickstate",
                    monolith_engine,
                    if_exists="append",
                    index=False,
                )
                chunks_written += len(chunk)

            conn.close()
            elapsed = time.monotonic() - t0
            total_ticks += chunks_written
            demos_processed += 1
            print(f"  OK {stem}: {chunks_written:,} ticks ({elapsed:.1f}s)")

        except Exception as e:
            print(f"  ERROR {stem}: {e}")
            continue

    return demos_processed, total_ticks


def rebuild_match_stats(db_manager, all_demos: list[Path]):
    """Parse .dem files for aggregate stats and write PlayerMatchStats."""
    # Clear existing pro stats
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
    from Programma_CS2_RENAN.run_ingestion import _save_player_stats

    with db_manager.get_session() as session:
        old_stats = session.exec(
            select(PlayerMatchStats).where(PlayerMatchStats.is_pro == True)  # noqa: E712
        ).all()
        for s in old_stats:
            session.delete(s)
        session.commit()
    print(f"  Cleared {len(old_stats)} old pro PlayerMatchStats.")

    total_stats = 0
    for demo_path in all_demos:
        t0 = time.monotonic()
        try:
            df = parse_demo(str(demo_path), target_player="ALL")
            if df.empty:
                print(f"  SKIP {demo_path.stem} — parse_demo returned empty")
                continue

            for _, row in df.iterrows():
                _save_player_stats(db_manager, row, demo_path.name, is_pro=True)

            elapsed = time.monotonic() - t0
            total_stats += len(df)
            print(f"  OK {demo_path.stem}: {len(df)} players ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  ERROR {demo_path.stem}: {e}")
            continue

    return total_stats


def main():
    from sqlalchemy import text

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
    from Programma_CS2_RENAN.core.config import save_user_setting

    print("=== CS2 Coach AI — Rebuild Monolith from Per-Match DBs ===\n")

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

    # Phase 1: Tick data from per-match DBs (fast — no .dem parsing)
    incremental = "--full" not in sys.argv
    if incremental:
        print("--- Phase 1: Rebuilding PlayerTickState (incremental — use --full to clear) ---")
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
