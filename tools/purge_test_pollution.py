"""Remove rows that unit tests wrote into the real database (D-50).

``tests/test_services.py`` used to run the real ``CoachingService`` against
``database.db`` with the player ``__test_nonexistent_player__``; 48
second-person insight rows accumulated over months and the Coach screen
served them to the user as advice. This tool deletes rows whose
``player_name`` starts with ``__test`` from the tables that carry player
rows — nothing else — and only after a verified backup.

Usage::

    python tools/purge_test_pollution.py            # dry run: report only
    python tools/purge_test_pollution.py --apply    # backup, then delete
    python tools/purge_test_pollution.py --db PATH  # another database file
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Tables with a player_name column that tests were seen (or could be) writing.
TABLES = ("coachinginsight", "playermatchstats", "playerprofile")
# SQL LIKE pattern for "starts with __test"; underscores are LIKE wildcards
# and must be escaped.
_PATTERN = r"\_\_test%"


def default_db_path() -> Path:
    return REPO / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"


def _existing_tables(con: sqlite3.Connection) -> set:
    return {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def find_pollution(db_path: Path) -> Dict[str, int]:
    """{table: number of ``__test*`` rows} for every watched table that exists."""
    con = sqlite3.connect(str(db_path))
    try:
        existing = _existing_tables(con)
        report: Dict[str, int] = {}
        for table in TABLES:
            if table not in existing:
                continue
            report[table] = con.execute(
                f"SELECT count(*) FROM {table} WHERE player_name LIKE ? ESCAPE '\\'",
                (_PATTERN,),
            ).fetchone()[0]
        return report
    finally:
        con.close()


def _default_backup(db_path: Path) -> Path:
    """Verified copy via the SQLite online-backup API (same path as db_backup.py)."""
    from Programma_CS2_RENAN.backend.storage import db_backup

    if db_path.resolve() == db_backup._MONOLITH_DB.resolve():
        return db_backup.backup_monolith()

    target_dir = db_path.parent / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = target_dir / f"{db_path.stem}_{stamp}{db_path.suffix}"
    source = sqlite3.connect(str(db_path))
    try:
        dest = sqlite3.connect(str(backup_path))
        try:
            source.backup(dest)
            if dest.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("backup integrity check failed")
        finally:
            dest.close()
    finally:
        source.close()
    return backup_path


def purge(
    db_path: Path,
    apply: bool = False,
    backup: Optional[Callable[[Path], Path]] = None,
) -> Dict[str, int]:
    """Report (and with ``apply=True`` delete) the ``__test*`` rows.

    The backup runs BEFORE any delete and any backup failure propagates —
    nothing is removed without a verified copy.
    """
    db_path = Path(db_path)
    report = find_pollution(db_path)
    if not apply or not any(report.values()):
        return report

    (backup or _default_backup)(db_path)

    con = sqlite3.connect(str(db_path))
    try:
        for table, count in report.items():
            if count:
                con.execute(
                    f"DELETE FROM {table} WHERE player_name LIKE ? ESCAPE '\\'",
                    (_PATTERN,),
                )
        con.commit()
    finally:
        con.close()
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, default=default_db_path(), help="database file")
    parser.add_argument("--apply", action="store_true", help="back up, then delete the rows")
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"no database at {args.db}")
        return 1
    report = purge(args.db, apply=args.apply)
    mode = "deleted" if args.apply else "would delete"
    total = sum(report.values())
    for table, count in report.items():
        print(f"{table}: {mode} {count} row(s) with player_name LIKE '__test%'")
    # ASCII only: the Windows console is cp1252 (D-28 class).
    print(f"total: {total} ({'applied' if args.apply else 'dry run - pass --apply to delete'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
