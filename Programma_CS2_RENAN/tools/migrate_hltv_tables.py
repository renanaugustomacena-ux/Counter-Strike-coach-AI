"""
One-time migration: Move HLTV tables from database.db to hltv_metadata.db.

Copies HLTVDownload, ProPlayer, ProTeam, ProPlayerStatCard rows from the
monolith database into the new dedicated HLTV metadata database.

Usage:
    python -m Programma_CS2_RENAN.tools.migrate_hltv_tables              # Copy only (safe)
    python -m Programma_CS2_RENAN.tools.migrate_hltv_tables --drop-old   # Copy + drop from monolith
"""

import sqlite3
import sys
from pathlib import Path

from Programma_CS2_RENAN.core.config import CORE_DB_DIR
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.migrate_hltv")

MONOLITH_PATH = Path(CORE_DB_DIR) / "database.db"
HLTV_PATH = Path(CORE_DB_DIR) / "hltv_metadata.db"

# Tables to migrate (SQLModel lowercase names)
TABLES = ["hltvdownload", "proplayer", "proteam", "proplayerstatcard"]


def migrate(drop_old: bool = False) -> bool:
    """
    Migrate HLTV tables from monolith to hltv_metadata.db.

    Args:
        drop_old: If True, drop migrated tables from monolith after copy.

    Returns:
        True if migration succeeded, False otherwise.
    """
    if not MONOLITH_PATH.exists():
        logger.warning("Monolith database not found at %s — nothing to migrate.", MONOLITH_PATH)
        return False

    logger.info("Migrating HLTV tables: %s -> %s", MONOLITH_PATH, HLTV_PATH)

    src = sqlite3.connect(str(MONOLITH_PATH))
    dst = sqlite3.connect(str(HLTV_PATH))
    dst.execute("PRAGMA journal_mode=WAL")
    dst.execute("PRAGMA synchronous=NORMAL")

    migrated = 0

    for table in TABLES:
        # Check if source table exists
        exists = src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            logger.info("  [SKIP] %s not found in monolith", table)
            continue

        # Check source row count
        src_count = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if src_count == 0:
            logger.info("  [SKIP] %s is empty in monolith", table)
            continue

        # Get CREATE TABLE statement
        schema = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()[0]

        # Create table in destination (drop first if exists to avoid schema conflicts)
        dst.execute(f"DROP TABLE IF EXISTS {table}")
        dst.execute(schema)

        # Copy data
        rows = src.execute(f"SELECT * FROM {table}").fetchall()
        if rows:
            placeholders = ",".join(["?"] * len(rows[0]))
            dst.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)

        # Verify
        dst_count = dst.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if src_count != dst_count:
            logger.error(
                "  [FAIL] %s: row count mismatch (src=%d, dst=%d)",
                table, src_count, dst_count,
            )
            dst.rollback()
            src.close()
            dst.close()
            return False

        logger.info("  [OK] %s: %d rows migrated", table, dst_count)
        migrated += 1

        if drop_old:
            src.execute(f"DROP TABLE {table}")
            logger.info("  [DROPPED] %s from monolith", table)

    dst.commit()
    dst.close()

    if drop_old and migrated > 0:
        src.execute("VACUUM")
    src.commit()
    src.close()

    logger.info("Migration complete: %d tables processed.", migrated)
    return True


if __name__ == "__main__":
    drop = "--drop-old" in sys.argv
    success = migrate(drop_old=drop)
    sys.exit(0 if success else 1)
