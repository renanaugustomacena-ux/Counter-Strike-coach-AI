"""Merge a secondary pro-demo pool into the primary pool.

The project identifies a demo by `Path.stem` (basename without `.dem`). The
same stem referenced twice is the same match from the system's perspective
(see `Programma_CS2_RENAN/run_ingestion.py:44-112` for the canonical
three-tier dedup). This tool uses the same semantics, case-insensitive, to
split the source pool into:

- duplicates — stem already ingested (PlayerMatchStats) or already present
  in the target pool. These are DELETED from source to reclaim drive space.
- unique    — new stems. These are MOVED into the target pool.
- skipped   — files smaller than MIN_DEMO_SIZE (DS-12, 10 MB). Left in
  place and logged.

Dry-run by default. Pass --execute to actually touch the filesystem.

Usage:
    python tools/merge_demo_pool.py \
        --source "/media/renan/New Volume1/BASE_PER_DEMO/DEMO_PRO_PLAYERS" \
        --target "/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS" \
        [--execute]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# Allow direct `python tools/merge_demo_pool.py ...` invocation.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import logging

from sqlmodel import select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger

logger = get_tool_logger("merge_demo_pool", console=False)
# get_tool_logger's console handler is suppressed; this tool renders its own
# stdout progress via the StreamHandler below to keep the plain message format.
_stdout = logging.StreamHandler(sys.stdout)
_stdout.setFormatter(logging.Formatter("%(message)s"))
_stdout.setLevel(logging.INFO)
logger.addHandler(_stdout)
logger.setLevel(logging.INFO)

MIN_DEMO_SIZE_BYTES = 10 * 1024 * 1024  # DS-12


def _known_stems_from_db() -> set[str]:
    with get_db_manager().get_session() as session:
        rows = session.exec(select(PlayerMatchStats.demo_name).distinct()).all()
    return {str(name).lower() for name in rows if name}


def _known_stems_from_dir(target: Path) -> set[str]:
    if not target.exists():
        return set()
    return {p.stem.lower() for p in target.rglob("*.dem") if not p.is_symlink()}


def _iter_source_demos(source: Path):
    for p in sorted(source.rglob("*.dem")):
        if p.is_symlink():
            continue
        yield p


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source pool directory (files here will be moved or deleted)",
    )
    parser.add_argument(
        "--target", required=True, help="Target pool directory (unique files moved here)"
    )
    parser.add_argument(
        "--execute", action="store_true", help="Actually touch the filesystem. Default is dry-run."
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()

    if not source.exists():
        logger.error("Source does not exist: %s", source)
        return 2
    if not target.exists():
        logger.error("Target does not exist: %s", target)
        return 2
    if source == target:
        logger.error("Source and target resolve to the same path: %s", source)
        return 2

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    logger.info("=" * 70)
    logger.info("MERGE POOL %s", mode)
    logger.info("Source: %s", source)
    logger.info("Target: %s", target)
    logger.info("=" * 70)

    known_db = _known_stems_from_db()
    known_target = _known_stems_from_dir(target)
    known = known_db | known_target
    logger.info(
        "Known stems — DB: %d, target dir: %d, union: %d",
        len(known_db),
        len(known_target),
        len(known),
    )

    candidates = list(_iter_source_demos(source))
    logger.info("Source .dem candidates: %d", len(candidates))

    dup_count = move_count = skip_count = err_count = 0
    dup_bytes = move_bytes = 0

    for src_file in candidates:
        size = src_file.stat().st_size
        stem_key = src_file.stem.lower()

        if size < MIN_DEMO_SIZE_BYTES:
            logger.warning("SKIP (too small, %d bytes): %s", size, src_file.name)
            skip_count += 1
            continue

        if stem_key in known:
            logger.info("DUP   %s  (%.0f MB) — will delete from source", src_file.name, size / 1e6)
            dup_count += 1
            dup_bytes += size
            if args.execute:
                try:
                    src_file.unlink()
                except Exception as exc:
                    logger.error("  delete failed: %s", exc)
                    err_count += 1
            continue

        dst_file = target / src_file.name
        if dst_file.exists():
            # Same basename landed here via another path — treat as dup.
            logger.warning("DUP-name at target (%s) — deleting source copy", dst_file.name)
            dup_count += 1
            dup_bytes += size
            if args.execute:
                try:
                    src_file.unlink()
                except Exception as exc:
                    logger.error("  delete failed: %s", exc)
                    err_count += 1
            continue

        logger.info("MOVE  %s  (%.0f MB) -> %s", src_file.name, size / 1e6, dst_file)
        move_count += 1
        move_bytes += size
        if args.execute:
            try:
                shutil.move(str(src_file), str(dst_file))
                known.add(stem_key)  # future files in this run see it as known
            except Exception as exc:
                logger.error("  move failed: %s", exc)
                err_count += 1

    logger.info("=" * 70)
    logger.info("SUMMARY (%s)", mode)
    logger.info("  Moved   : %d files (%.1f GB)", move_count, move_bytes / 1e9)
    logger.info(
        "  Deleted : %d duplicate files (%.1f GB reclaimed on source)", dup_count, dup_bytes / 1e9
    )
    logger.info("  Skipped : %d too-small files", skip_count)
    logger.info("  Errors  : %d", err_count)
    logger.info("=" * 70)
    if not args.execute:
        logger.info("Dry-run only. Re-run with --execute to apply changes.")

    return 0 if err_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
