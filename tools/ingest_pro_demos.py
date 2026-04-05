#!/usr/bin/env python3
"""
One-shot script: clear stale ingestion state, re-ingest ALL pro .dem files
(including already-archived ones), populate monolith DB, then retrain.

Usage:
    python tools/ingest_pro_demos.py                # incremental: skip already-ingested
    python tools/ingest_pro_demos.py --full          # full rebuild: re-ingest everything
    python tools/ingest_pro_demos.py --retrain-only  # skip ingestion, just retrain
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEMO_BASE = Path("/media/renan/New Volume/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS")


def _run_retraining():
    """Run the 5-phase coach training cycle on existing monolith data."""
    from sqlalchemy import text

    from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database

    print("=== CS2 Coach AI — Retrain Only ===\n")

    print("[1/2] Initializing database...")
    init_database()
    db = get_db_manager()

    # Report current data
    with db.get_session() as session:
        demo_count = session.exec(text(
            "SELECT COUNT(DISTINCT demo_name) FROM playertickstate"
        )).scalar() or 0
        tick_count = session.exec(text(
            "SELECT COUNT(*) FROM playertickstate"
        )).scalar() or 0
    print(f"  Monolith has {tick_count:,} ticks from {demo_count} demos.\n")

    if tick_count == 0:
        print("  ERROR: No tick data in monolith. Run rebuild_monolith.py first.")
        return

    print("[2/2] Retraining coach models...")
    manager = CoachTrainingManager()
    ready, reason = manager.check_prerequisites()
    if not ready:
        print(f"  Prerequisites not met: {reason}")
        return

    print(f"  Prerequisites OK ({reason}). Starting full training cycle...")
    manager.run_full_cycle()
    print("  Retraining complete.")
    print("\n=== Done ===")


def main():
    import hashlib

    from sqlalchemy import text
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask, PlayerMatchStats
    from Programma_CS2_RENAN.backend.storage.storage_manager import StorageManager
    from Programma_CS2_RENAN.core.config import save_user_setting
    from Programma_CS2_RENAN.run_ingestion import _queue_files, process_queued_tasks

    full_rebuild = "--full" in sys.argv

    print("=== CS2 Coach AI — Pro Demo Ingestion + Retraining ===")
    if full_rebuild:
        print("    MODE: Full rebuild (re-ingesting ALL demos)\n")
    else:
        print("    MODE: Incremental (skipping already-ingested)\n")

    # ── Step 1: Init databases ─────────────────────────────────────────────
    print("[1/5] Initializing database...")
    init_database()
    db = get_db_manager()
    print("  Done.\n")

    # ── Step 2: Discover ALL .dem files ────────────────────────────────────
    print("[2/5] Discovering demo files...")
    save_user_setting("PRO_DEMO_PATH", str(DEMO_BASE))

    if full_rebuild:
        # Scan everywhere including ingested/
        all_demos = sorted(DEMO_BASE.rglob("*.dem"))
    else:
        # Skip the ingested/ subfolder
        all_demos = [p for p in DEMO_BASE.rglob("*.dem") if "ingested" not in p.parts]

    print(f"  Found {len(all_demos)} demo(s) on disk.")

    if not all_demos:
        print("  No demos found — nothing to do.\n")
        return

    # ── Step 3: Clear stale state (full rebuild only) ──────────────────────
    if full_rebuild:
        print("\n[3/5] Clearing stale ingestion state for full rebuild...")

        with db.get_session() as session:
            # Clear all IngestionTask entries
            old_tasks = session.exec(select(IngestionTask)).all()
            for t in old_tasks:
                session.delete(t)
            session.commit()
        print(f"  Cleared {len(old_tasks)} IngestionTask entries.")

        with db.get_session() as session:
            # Clear pro PlayerMatchStats
            pro_stats = session.exec(
                select(PlayerMatchStats).where(PlayerMatchStats.is_pro == True)  # noqa: E712
            ).all()
            for s in pro_stats:
                session.delete(s)
            session.commit()
        print(f"  Cleared {len(pro_stats)} pro PlayerMatchStats rows.")

        # Clear pro PlayerTickState rows (use raw SQL for bulk delete)
        with db.get_session() as session:
            tick_count_before = session.exec(text("SELECT COUNT(*) FROM playertickstate")).scalar() or 0
            if tick_count_before > 0:
                session.exec(text("DELETE FROM playertickstate"))
                session.commit()
        print(f"  Cleared {tick_count_before} PlayerTickState rows.")

        # Delete per-match DBs for these demos so duplicate check passes
        pro_demo_stems = {d.stem for d in all_demos}
        match_data_dir = DEMO_BASE / "match_data"
        deleted_dbs = 0
        for stem in pro_demo_stems:
            match_id = int(hashlib.sha256(stem.encode()).hexdigest(), 16) % (2**63 - 1)
            db_path = match_data_dir / f"match_{match_id}.db"
            for suffix in ("", "-shm", "-wal"):
                p = Path(str(db_path) + suffix)
                if p.exists():
                    p.unlink()
                    if not suffix:
                        deleted_dbs += 1
        print(f"  Deleted {deleted_dbs} per-match DB files (will be recreated).")

        # Bypass duplicate check for this run
        import Programma_CS2_RENAN.run_ingestion as ri

        ri._check_duplicate_demo = lambda _db, _demo: False
        print("  Duplicate check bypassed for full rebuild.")
    else:
        print("\n[3/5] Clearing stale queue entries...")
        with db.get_session() as session:
            stale = session.exec(
                select(IngestionTask).where(IngestionTask.status.in_(["queued", "failed"]))
            ).all()
            cleared = 0
            for task in stale:
                if not Path(task.demo_path).exists():
                    session.delete(task)
                    cleared += 1
            session.commit()
        print(f"  Cleared {cleared} stale tasks.")

    print()

    # ── Step 4: Queue and ingest ───────────────────────────────────────────
    print(f"[4/5] Queuing and ingesting {len(all_demos)} pro demos...")
    for d in sorted(all_demos):
        print(f"    {d.name}")

    with db.get_session() as session:
        _queue_files(session, all_demos, is_pro=True)
        session.commit()

    storage = StorageManager()
    process_queued_tasks(db, storage, is_pro=True, high_priority=True, limit=0)

    # Report final ingestion results
    with db.get_session() as session:
        pro_count = session.exec(
            select(PlayerMatchStats).where(PlayerMatchStats.is_pro == True)  # noqa: E712
        ).all()
    print(f"\n  Ingestion complete. Pro PlayerMatchStats rows: {len(pro_count)}")

    with db.get_session() as session:
        tick_total = session.exec(text("SELECT COUNT(*) FROM playertickstate")).scalar() or 0
    print(f"  Pro PlayerTickState rows: {tick_total}")

    print()

    # ── Step 5: Retrain coach models ───────────────────────────────────────
    print("[5/5] Retraining coach models (this may take a few minutes)...")
    manager = CoachTrainingManager()
    ready, reason = manager.check_prerequisites()
    if not ready:
        print(f"  Prerequisites not met: {reason}")
        print("  Skipping retraining — ingest more demos first.")
    else:
        print(f"  Prerequisites OK ({reason}). Starting full cycle...")
        manager.run_full_cycle()
        print("  Retraining complete.")

    print("\n=== Done ===")


if __name__ == "__main__":
    if "--retrain-only" in sys.argv:
        _run_retraining()
    else:
        main()
