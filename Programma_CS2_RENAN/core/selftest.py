"""Headless runtime probe — ``Macena_CS2_Analyzer.exe --selftest``.

The packaged build was packed and uploaded by CI but never executed, so a
whole class of install-only failures (read-only install directory, bundle
paths that do not match the resource resolver, missing factory models)
could ship unseen.  This probe resolves every runtime path the app relies
on, proves the data root is writable, opens the database when one exists
and lists the models it can see — with no Qt, no daemon and no network —
then exits non-zero if any of that fails.  The build script and the CI
dist stage run it against the frozen exe; ``pytest`` runs it in dev.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Tuple

_SQLITE_PREFIX = "sqlite:///"


def _can_write(path: str) -> bool:
    """True when a file can be created and removed under ``path``."""
    try:
        os.makedirs(path, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".selftest-", delete=True):
            pass
        return True
    except OSError:
        return False


def _db_path_from_url(url: str) -> str:
    return url[len(_SQLITE_PREFIX) :] if url.startswith(_SQLITE_PREFIX) else url


def _probe_db(path: str) -> Tuple[bool, bool, str]:
    """(exists, ok, detail). A missing database is fine: first boot creates it."""
    if not os.path.exists(path):
        return False, True, "absent (created on first boot)"
    # SESSION_HANDOFF: plain ``mode=ro`` still creates -shm/-wal on NTFS;
    # ``immutable=1`` is the only truly non-destructive read.
    uri = f"file:{Path(path).as_posix()}?mode=ro&immutable=1"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            con.execute("SELECT 1").fetchone()
            tables = con.execute(
                "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
            ).fetchone()[0]
        finally:
            con.close()
        return True, True, f"{tables} tables"
    except sqlite3.Error as exc:
        return True, False, str(exc)


def _list_pt(directory: Path) -> list:
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.glob("*.pt"))


def run_selftest() -> dict:
    """Resolve, probe and report. Never raises; ``report["ok"]`` carries the verdict."""
    from Programma_CS2_RENAN.core import config

    frozen = bool(getattr(sys, "frozen", False))
    db_path = _db_path_from_url(config.DATABASE_URL)
    db_exists, db_ok, db_detail = _probe_db(db_path)
    models_dir = Path(config.MODELS_DIR)
    factory_dir = Path(config.get_resource_path(os.path.join("models", "global")))
    docs_dir = config.get_resource_path(os.path.join("data", "docs"))
    docs_ok = os.path.isdir(docs_dir) and any(Path(docs_dir).glob("*.md"))
    writable = _can_write(config.USER_DATA_ROOT)

    report = {
        "frozen": frozen,
        "executable": sys.executable,
        "base_dir": config.BASE_DIR,
        "user_data_root": config.USER_DATA_ROOT,
        "user_data_root_writable": writable,
        "db_path": db_path,
        "db_exists": db_exists,
        "db_ok": db_ok,
        "db_detail": db_detail,
        "models_dir": str(models_dir),
        "models": _list_pt(models_dir / "global"),
        "factory_models_dir": str(factory_dir),
        "factory_models": _list_pt(factory_dir),
        "log_dir": config.LOG_DIR,
        "resource_docs_dir": docs_dir,
        "resource_docs_ok": bool(docs_ok),
    }
    report["ok"] = bool(writable and db_ok and docs_ok)
    return report


def main(argv=None) -> int:
    report = run_selftest()
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
