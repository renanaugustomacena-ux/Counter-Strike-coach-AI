#!/usr/bin/env python3
"""
Parallel batch ingestion script for pro CS2 demo files.

Processes all .dem files from DEMO_PRO_PLAYERS directory into the project database.
Resumable: skips already-ingested demos.
Uses multiprocessing to leverage all CPU cores.

Usage:
    python batch_ingest.py [--workers N] [--limit N]
"""
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_LOG_LEVEL"] = "warning"

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Centralized logging
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger

logger = get_tool_logger("batch_ingest")


def ingest_one_demo(demo_path_str: str) -> dict:
    """Worker function: ingest a single demo file. Runs in a separate process."""
    import os
    import sys
    import time
    from pathlib import Path

    os.environ["KIVY_NO_ARGS"] = "1"
    os.environ["KIVY_LOG_LEVEL"] = "warning"

    sys.path.insert(0, str(Path(__file__).parent))

    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask
    from Programma_CS2_RENAN.backend.storage.storage_manager import StorageManager
    from Programma_CS2_RENAN.run_ingestion import _ingest_single_demo

    demo_path = Path(demo_path_str)
    t0 = time.time()

    # The IngestionTask row is the authoritative state machine for this demo.
    # The previous implementation put the final status update inside the same
    # try: block as the worker call — when _ingest_single_demo raised, the
    # update was skipped and the row stayed at "queued" forever. That silent
    # desync is what made the Apr 2026 run show 0 failed rows after 301 hard
    # failures. This function now guarantees the row is flipped to
    # "completed" or "failed" in a finally: block regardless of exception.

    db = get_db_manager()
    storage = StorageManager()

    # 1. Ensure task record exists, reset from "failed" to "queued" for retry.
    with db.get_session() as session:
        existing = session.exec(
            select(IngestionTask).where(IngestionTask.demo_path == demo_path_str)
        ).first()
        if not existing:
            session.add(IngestionTask(demo_path=demo_path_str, is_pro=True, status="queued"))
            session.commit()
        elif existing.status == "failed":
            existing.status = "queued"
            existing.retry_count = 0
            existing.error_message = None
            session.add(existing)
            session.commit()

    # 2. Flip to "processing" before work starts so stale-lock sweeps can
    #    identify in-flight rows by updated_at age.
    with db.get_session() as session:
        task = session.exec(
            select(IngestionTask).where(IngestionTask.demo_path == demo_path_str)
        ).first()
        if task:
            task.status = "processing"
            task.error_message = None
            session.add(task)
            session.commit()

    success = False
    msg = "Worker did not record a result"
    try:
        success, msg = _ingest_single_demo(db, storage, demo_path, is_pro=True)
    except Exception as exc:  # noqa: BLE001 — boundary: must catch to record failure
        success = False
        msg = f"Worker exception: {exc!r}"
    finally:
        # 3. Authoritative final status update — runs on both success and
        #    exception paths. error_message truncated so a giant SQL traceback
        #    does not blow up the VARCHAR column.
        truncated_msg = (msg or "")[:512]
        try:
            with db.get_session() as session:
                task = session.exec(
                    select(IngestionTask).where(IngestionTask.demo_path == demo_path_str)
                ).first()
                if task:
                    task.status = "completed" if success else "failed"
                    task.error_message = truncated_msg
                    if not success:
                        task.retry_count = (task.retry_count or 0) + 1
                    session.add(task)
                    session.commit()
        except Exception as status_exc:  # noqa: BLE001 — loud log, do not mask worker result
            logger.error(
                "Failed to update IngestionTask status for %s: %r",
                demo_path.name,
                status_exc,
            )

    elapsed = time.time() - t0
    return {
        "demo": demo_path.name,
        "success": success,
        "msg": msg,
        "elapsed": elapsed,
    }


def get_already_ingested():
    """Return set of demo stems already in PlayerMatchStats."""
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    db = get_db_manager()
    with db.get_session() as session:
        names = session.exec(select(PlayerMatchStats.demo_name).distinct()).all()
    return set(names)


def main():
    import argparse
    import multiprocessing

    parser = argparse.ArgumentParser(description="Parallel batch ingest pro demos")
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Number of parallel workers (0=auto, based on RAM)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max demos to process (0=all)")
    parser.add_argument(
        "--demo-dir", type=str, default="", help="Demo directory (default: PRO_DEMO_PATH setting)"
    )
    parser.add_argument(
        "--no-train",
        action="store_true",
        help="Skip the auto-training pass after ingestion. Use run_full_training_cycle.py "
        "(or train.sh) separately when training is desired.",
    )
    args = parser.parse_args()

    if args.demo_dir:
        demo_dir = Path(args.demo_dir)
    else:
        # Use get_pro_demo_base() so a stale PRO_DEMO_PATH (e.g. SSD remounted
        # at a new path on another machine) auto-recovers via the DP-06 scan
        # over /media/<user>/*/ for the Counter-Strike-coach-AI suffix.
        from Programma_CS2_RENAN.core.config import get_pro_demo_base

        demo_dir = get_pro_demo_base()
    all_demos = sorted(p for p in demo_dir.rglob("*.dem") if not p.is_symlink())

    already_ingested = get_already_ingested()
    pending = [d for d in all_demos if d.stem not in already_ingested]

    if args.limit > 0:
        pending = pending[: args.limit]

    # Auto-detect workers: ~6 GB RAM per worker, leave 12 GB headroom
    total_ram_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024**3)
    max_by_ram = max(1, int((total_ram_gb - 12) / 6))
    max_by_cpu = max(1, multiprocessing.cpu_count() // 2)
    workers = args.workers if args.workers > 0 else min(max_by_ram, max_by_cpu, 8)

    logger.info("=" * 70)
    logger.info("PARALLEL BATCH INGESTION START")
    logger.info("Total demos available: %d", len(all_demos))
    logger.info("Already ingested: %d", len(already_ingested))
    logger.info("Pending: %d", len(pending))
    logger.info(
        "Workers: %d (RAM: %.0f GB, CPUs: %d)", workers, total_ram_gb, multiprocessing.cpu_count()
    )
    logger.info("=" * 70)

    if not pending:
        logger.info("Nothing to ingest. All demos are already processed.")
        return

    success_count = 0
    fail_count = 0
    batch_start = time.time()

    # Prevent DataFrame-accumulation memory leaks by recycling workers after each
    # task. `max_tasks_per_child` is Python 3.11+ on ProcessPoolExecutor; on 3.10
    # we fall back (workers keep their memory, but 3.10 is the supported minimum
    # per CLAUDE.md so don't crash on it).
    pool_kwargs = {"max_workers": workers}
    if sys.version_info >= (3, 11):
        pool_kwargs["max_tasks_per_child"] = 1
    with ProcessPoolExecutor(**pool_kwargs) as executor:
        # Submit all jobs
        future_to_demo = {executor.submit(ingest_one_demo, str(demo)): demo for demo in pending}

        for i, future in enumerate(as_completed(future_to_demo), 1):
            demo = future_to_demo[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"demo": demo.name, "success": False, "msg": str(e), "elapsed": 0}

            if result["success"]:
                success_count += 1
                logger.info(
                    "[%d/%d] SUCCESS in %.1fs — %s",
                    i,
                    len(pending),
                    result["elapsed"],
                    result["demo"],
                )
            else:
                fail_count += 1
                logger.error(
                    "[%d/%d] FAILED in %.1fs — %s: %s",
                    i,
                    len(pending),
                    result["elapsed"],
                    result["demo"],
                    result["msg"][:200],
                )

            elapsed_total = time.time() - batch_start
            demos_per_sec = i / elapsed_total
            remaining = (len(pending) - i) / demos_per_sec if demos_per_sec > 0 else 0
            logger.info(
                "Progress: %d/%d (%.0f%%) | %.1f demos/min | ETA: %.0f min",
                i,
                len(pending),
                i / len(pending) * 100,
                demos_per_sec * 60,
                remaining / 60,
            )

    batch_elapsed = time.time() - batch_start
    logger.info("=" * 70)
    logger.info("PARALLEL BATCH INGESTION COMPLETE")
    logger.info("Total time: %.0f min (%.1f hours)", batch_elapsed / 60, batch_elapsed / 3600)
    logger.info("Success: %d | Failed: %d | Total: %d", success_count, fail_count, len(pending))
    logger.info("Throughput: %.1f demos/min", len(pending) / (batch_elapsed / 60))
    logger.info("=" * 70)

    # After ingestion completes, start training automatically unless the caller
    # explicitly opted out (e.g. ingest.sh keeps ingest/train phases separate).
    if success_count > 0 and not args.no_train:
        logger.info("Starting ML training automatically...")
        try:
            run_training_after_ingestion()
        except Exception as e:
            logger.error("Training failed: %s", e)
    elif args.no_train:
        logger.info("--no-train set — skipping auto-training. Run train.sh to train.")


def run_training_after_ingestion():
    """Run the full ML training pipeline after ingestion completes."""
    logger.info("=" * 70)
    logger.info("ML TRAINING — AUTO-START AFTER INGESTION")
    logger.info("=" * 70)

    from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager

    manager = CoachTrainingManager()

    # Step 1: Assign dataset splits (70/15/15 train/val/test)
    logger.info("Step 1: Assigning dataset splits...")
    manager.assign_dataset_splits()

    # Step 2: JEPA Self-Supervised Pre-training on pro data
    logger.info("Step 2: JEPA Self-Supervised Pre-training...")
    try:
        manager.run_jepa_pretraining()
        logger.info("JEPA pre-training completed.")
    except Exception as e:
        logger.error("JEPA pre-training failed: %s", e)

    # Step 3: Supervised training on pro baseline
    logger.info("Step 3: Pro baseline training (supervised)...")
    try:
        from Programma_CS2_RENAN.backend.nn.persistence import save_nn

        pro_model = manager._train_phase(is_pro=True)
        if pro_model:
            save_nn(pro_model, "latest", user_id=None)
            logger.info("Pro baseline model saved.")
        else:
            logger.warning("Pro baseline training returned no model (insufficient data?)")
    except Exception as e:
        logger.error("Pro baseline training failed: %s", e)

    logger.info("=" * 70)
    logger.info("ML TRAINING COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
