"""GAP-05 · Purge stale ProPlayer / ProPlayerStatCard rows from the MAIN DB.

Context
-------
The canonical pro reference lives in `hltv_metadata.db` (get_hltv_db_manager).
The main `database.db` should NOT replicate those rows — it links to them
via `PlayerMatchStats.pro_player_id -> ProPlayer.hltv_id` (cross-DB logical
reference, no FK). In the current DB state there are 2 stale seed rows
(zywoo=11893, s1mple=7998) left over from early testing. These can drift from
the canonical HLTV snapshot, so this tool deletes them.

Safe-by-default
---------------
- `--dry-run` (default): prints what would be deleted, mutates nothing.
- `--apply`: performs the purge inside a single transaction.
- Before `--apply`, a timestamped file-copy backup of the main DB is taken
  alongside the original (pattern used by AUDIT §8 CHAT-06 cleanup:
  `database.db.pre_gap05_<iso>`).
- Idempotent: if 0 ProPlayer rows exist in main DB, this is a no-op.

Usage
-----
    ./.venv/bin/python tools/sync_pro_players.py              # dry-run
    ./.venv/bin/python tools/sync_pro_players.py --apply      # execute
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from Programma_CS2_RENAN.observability.logger_setup import get_logger  # noqa: E402

logger = get_logger("cs2analyzer.sync_pro_players")


def _count_stale() -> dict:
    from sqlmodel import func, select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard, ProTeam

    db = get_db_manager()
    with db.get_session() as s:
        np = s.exec(select(func.count()).select_from(ProPlayer)).one()
        ns = s.exec(select(func.count()).select_from(ProPlayerStatCard)).one()
        nt = s.exec(select(func.count()).select_from(ProTeam)).one()
        rows = s.exec(select(ProPlayer)).all()
    return {
        "proplayer_count": int(np),
        "proplayerstatcard_count": int(ns),
        "proteam_count": int(nt),
        "samples": [{"id": r.id, "hltv_id": r.hltv_id, "nickname": r.nickname} for r in rows[:5]],
    }


def _backup_main_db() -> Path:
    """Copy the main database file to a timestamped sibling. Returns backup path."""
    from Programma_CS2_RENAN.core.config import CORE_DB_DIR

    src = Path(CORE_DB_DIR) / "database.db"
    if not src.exists():
        raise FileNotFoundError(f"main DB not at {src}")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = src.with_name(f"database.db.pre_gap05_{ts}")
    shutil.copy2(src, dst)
    logger.info("Backed up main DB: %s (%.1f MB)", dst, dst.stat().st_size / 1_048_576)
    return dst


def _apply_purge() -> dict:
    from sqlmodel import delete

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard, ProTeam

    db = get_db_manager()
    with db.get_session() as s:
        # Delete stat cards first (FK-safe ordering even though FK is cross-DB logical)
        r_card = s.exec(delete(ProPlayerStatCard)).rowcount
        r_player = s.exec(delete(ProPlayer)).rowcount
        r_team = s.exec(delete(ProTeam)).rowcount
        s.commit()
    return {
        "deleted_proplayerstatcard": int(r_card or 0),
        "deleted_proplayer": int(r_player or 0),
        "deleted_proteam": int(r_team or 0),
    }


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="GAP-05 stale-pro purge")
    p.add_argument(
        "--apply",
        action="store_true",
        help="execute the purge (default is dry-run)",
    )
    p.add_argument(
        "--skip-backup",
        action="store_true",
        help="skip DB backup (ONLY with --apply; use if already backed up)",
    )
    args = p.parse_args(argv)

    before = _count_stale()
    print(f"[sync_pro_players] Before: {before}")
    logger.info("Before: %s", before)

    if before["proplayer_count"] == 0 and before["proplayerstatcard_count"] == 0:
        print("[sync_pro_players] No stale pro rows in main DB — nothing to do (idempotent).")
        return 0

    if not args.apply:
        print(
            f"[DRY-RUN] Would delete {before['proplayer_count']} proplayer, "
            f"{before['proplayerstatcard_count']} proplayerstatcard, "
            f"{before['proteam_count']} proteam rows. Re-run with --apply to execute."
        )
        return 0

    if not args.skip_backup:
        bp = _backup_main_db()
        print(f"[sync_pro_players] Backup written: {bp}")

    result = _apply_purge()
    print(f"[sync_pro_players] Purged: {result}")

    after = _count_stale()
    print(f"[sync_pro_players] After: {after}")

    assert after["proplayer_count"] == 0, "purge failed — proplayer rows remain"
    assert after["proplayerstatcard_count"] == 0, "purge failed — statcard rows remain"
    return 0


if __name__ == "__main__":
    sys.exit(main())
