"""
Automated Backup Strategy — Task [5.4]

WAL-safe backup system for the three-tier storage architecture:
  - Tier 1-2: Monolith database.db (WAL checkpoint before copy)
  - Tier 3:   Per-match SQLite files via MATCH_DATA_PATH (tar.gz archive)

Governance: Rule 4 §3.1 (Durability guarantees), Rule 4 §8.1 (Backup/restore must be tested)
"""

import os
import shutil
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from Programma_CS2_RENAN.core.config import CORE_DB_DIR, USER_DATA_ROOT
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.db_backup")

_MONOLITH_DB = Path(CORE_DB_DIR) / "database.db"
_DEFAULT_BACKUP_ROOT = Path(USER_DATA_ROOT) / "backups"


def _get_match_data_dir() -> Path:
    """Dynamically resolve match data directory for backup operations."""
    from Programma_CS2_RENAN.core.config import MATCH_DATA_PATH

    return Path(MATCH_DATA_PATH)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_monolith(target_dir: Optional[Path] = None) -> Path:
    """
    Create a WAL-safe backup of the monolith database.

    1. PRAGMA wal_checkpoint(TRUNCATE) to flush WAL into main db file
    2. shutil.copy2() to preserve metadata timestamps
    3. Naming: database_{YYYYMMDD_HHMMSS}.db
    """
    if target_dir is None:
        target_dir = _DEFAULT_BACKUP_ROOT / "database"
    target_dir.mkdir(parents=True, exist_ok=True)

    if not _MONOLITH_DB.exists():
        raise FileNotFoundError(f"Monolith database not found: {_MONOLITH_DB}")

    # P0-05: Use SQLite Online Backup API instead of WAL checkpoint + shutil.copy2.
    # The previous approach had a TOCTOU race: between checkpoint completion and
    # file copy, another thread could write via SQLAlchemy, re-creating the WAL.
    # sqlite3.backup() is atomic and handles concurrent writes correctly.
    backup_name = f"database_{_timestamp()}.db"
    backup_path = target_dir / backup_name

    logger.info("Creating backup via SQLite Online Backup API...")
    source = sqlite3.connect(str(_MONOLITH_DB), timeout=10)
    dest = sqlite3.connect(str(backup_path))
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()

    # P2-08: Verify backup integrity after creation
    verify_conn = sqlite3.connect(str(backup_path))
    try:
        result = verify_conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] != "ok":
            logger.error("Backup integrity check FAILED: %s", result[0])
            backup_path.unlink(missing_ok=True)
            raise RuntimeError(f"Backup integrity check failed: {result[0]}")
    finally:
        verify_conn.close()

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info(
        "Monolith backup created and verified: %s (%s MB)", backup_path, format(size_mb, ".2f")
    )
    return backup_path


def backup_match_data(target_dir: Optional[Path] = None) -> Path:
    """
    Create a tar.gz archive of the per-match SQLite partitions.

    Skips in-progress WAL (.db-wal) and SHM (.db-shm) files to avoid
    capturing transient state.
    """
    if target_dir is None:
        target_dir = _DEFAULT_BACKUP_ROOT / "match_data"
    target_dir.mkdir(parents=True, exist_ok=True)

    match_data_dir = _get_match_data_dir()

    if not match_data_dir.exists():
        logger.warning("Match data directory not found: %s", match_data_dir)
        raise FileNotFoundError(f"Match data directory not found: {match_data_dir}")

    archive_name = f"match_data_{_timestamp()}.tar.gz"
    archive_path = target_dir / archive_name

    skip_extensions = {".db-wal", ".db-shm"}

    with tarfile.open(str(archive_path), "w:gz") as tar:
        for entry in match_data_dir.iterdir():
            if entry.suffix in skip_extensions:
                logger.debug("Skipping transient file: %s", entry.name)
                continue
            # WAL checkpoint each .db file before archiving to flush pending writes
            if entry.suffix == ".db":
                # P0-06: Wrap in try/finally to prevent connection leak on checkpoint failure.
                try:
                    conn = sqlite3.connect(str(entry), timeout=10)
                    try:
                        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    finally:
                        conn.close()
                except Exception as e:
                    logger.warning("WAL checkpoint failed for %s: %s", entry.name, e)
            tar.add(str(entry), arcname=entry.name)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    logger.info("Match data backup created: %s (%s MB)", archive_path, format(size_mb, ".2f"))
    return archive_path


def rotate_backups(backup_dir: Optional[Path] = None, keep_count: int = 5) -> int:
    """
    Delete oldest backups beyond the retention limit.

    Returns the number of backups deleted.
    """
    if backup_dir is None:
        backup_dir = _DEFAULT_BACKUP_ROOT

    if not backup_dir.exists():
        return 0

    deleted = 0
    # Process each subdirectory (database/, match_data/)
    for sub_dir in backup_dir.iterdir():
        if not sub_dir.is_dir():
            continue

        backups = sorted(sub_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        excess = len(backups) - keep_count

        if excess <= 0:
            continue

        for old_backup in backups[:excess]:
            size_mb = old_backup.stat().st_size / (1024 * 1024)
            try:
                old_backup.unlink()
            except OSError as e:
                logger.warning("Could not delete old backup %s: %s", old_backup.name, e)
                continue
            logger.info("Rotated (deleted): %s (%s MB)", old_backup.name, format(size_mb, ".2f"))
            deleted += 1

    if deleted:
        logger.info("Rotation complete: %s old backup(s) removed", deleted)
    return deleted


def restore_backup(backup_path: Path, target_path: Path) -> bool:
    """
    Restore a database backup with integrity verification.

    1. Validate backup file exists and is non-zero
    2. Copy to target location
    3. Execute PRAGMA integrity_check
    4. Return True only if integrity passes; rollback on failure
    """
    if not backup_path.exists():
        logger.error("Backup file not found: %s", backup_path)
        return False

    if backup_path.stat().st_size == 0:
        logger.error("Backup file is empty: %s", backup_path)
        return False

    # Preserve existing file for rollback
    rollback_path = None
    if target_path.exists():
        rollback_path = target_path.with_suffix(".db.rollback")
        shutil.copy2(str(target_path), str(rollback_path))

    try:
        # Remove WAL/SHM files before restoring — SQLite would replay stale WAL
        # transactions on top of the restored backup, corrupting it (STOR-01).
        wal_path = target_path.with_suffix(".db-wal")
        shm_path = target_path.with_suffix(".db-shm")
        if wal_path.exists():
            wal_path.unlink()
        if shm_path.exists():
            shm_path.unlink()

        shutil.copy2(str(backup_path), str(target_path))

        # Integrity check on the restored database
        conn = sqlite3.connect(str(target_path))
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                raise RuntimeError(f"Integrity check failed: {result[0]}")
        finally:
            conn.close()

        logger.info("Backup restored successfully: %s -> %s", backup_path, target_path)

        # Clean up rollback file on success
        if rollback_path and rollback_path.exists():
            rollback_path.unlink()

        return True

    except Exception as e:
        logger.error("Restore failed: %s", e)
        # Rollback — restore the original file
        if rollback_path and rollback_path.exists():
            shutil.copy2(str(rollback_path), str(target_path))
            rollback_path.unlink()
            logger.info("Rollback completed — original database restored")
        return False
