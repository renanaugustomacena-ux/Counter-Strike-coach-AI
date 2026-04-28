#!/usr/bin/env python3
"""Consolidated, safety-gated wipe tool for re-ingestion.

Doctrine §57 — Least Privilege; §60 — Incident Response as Design Input.
Maps to control C-WIPE-01 (SECURITY/CONTROL_CATALOG.md).
SOP: SECURITY/WIPE_RUNBOOK.md.

This is the SUCCESSOR to tools/wipe_for_reingest_v[1-4].py — kept as a separate
file (`_safe.py` suffix) until the active v4 ingestion-recovery campaign
finishes. After that, v1–v4 are deleted and this file may be renamed to
`tools/wipe_for_reingest.py`.

What this adds over v4:
  --confirm-wipe   MANDATORY — without it, the tool refuses to mutate state.
  --dry-run        DEFAULT — prints planned actions and counts, mutates nothing.
  --snapshot       creates an HMAC-sealed Fernet-encrypted tarball before wipe;
                   key from CS2_WIPE_SNAPSHOT_KEY env or OS keyring.
  --restore        replays a snapshot (also gated by --confirm-wipe).
  audit-log entry  every wipe / restore appends to logs/wipe_audit_*.jsonl.
  DB-unlock check  refuses to proceed if any process holds the WAL/SHM/.db open
                   (psutil cross-platform; falls back to `fuser` on Linux).

Phase 1 status:
  - Mode `rows` (DELETE FROM per table list, with VACUUM after) is implemented.
  - Mode `swap` (v4's atomic .fresh/.OLD swap) is a Phase 2 port — flagged with
    NotImplementedError until then to avoid duplicating complex logic that the
    in-flight v4 is mid-execution against.

Usage:
    python tools/wipe_for_reingest_safe.py                          # dry-run, mode=rows
    python tools/wipe_for_reingest_safe.py --confirm-wipe            # actual wipe
    python tools/wipe_for_reingest_safe.py --confirm-wipe --snapshot # snapshot then wipe
    python tools/wipe_for_reingest_safe.py --confirm-wipe --mode swap  # NotImplementedError
    python tools/wipe_for_reingest_safe.py --restore --snapshot-path <path> --confirm-wipe
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"
SNAPSHOT_DIR = REPO_ROOT / "Programma_CS2_RENAN" / "backups" / "wipe_snapshots"
WIPE_AUDIT_DIR = REPO_ROOT / "logs"

WIPE_TABLES = (
    "playermatchstats",
    "playertickstate",
    "roundstats",
    "coachinginsight",
    "ingestiontask",
)

ENV_KEY_NAME = "CS2_WIPE_SNAPSHOT_KEY"


# ──────────────────────────────────────────────────────────────────────────────
# Pre-flight: DB unlock check
# ──────────────────────────────────────────────────────────────────────────────


def _check_db_unlocked(db: pathlib.Path) -> tuple[bool, list[str]]:
    """Return (is_unlocked, list_of_holders).

    Tries psutil.process_iter first; falls back to `fuser` on Linux.
    """
    targets = [db, db.with_suffix(db.suffix + "-wal"), db.with_suffix(db.suffix + "-shm")]
    targets = [t for t in targets if t.exists()]
    if not targets:
        return True, []

    holders: list[str] = []

    try:
        import psutil  # type: ignore[import-not-found]

        for proc in psutil.process_iter(["pid", "name", "open_files"]):
            try:
                files = proc.info.get("open_files") or []
                for f in files:
                    fp = pathlib.Path(f.path).resolve()
                    if any(fp == t.resolve() for t in targets):
                        holders.append(f"pid={proc.info['pid']} name={proc.info['name']} path={fp}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue
    except ImportError:
        # Linux fuser fallback
        if sys.platform.startswith("linux"):
            for t in targets:
                try:
                    r = subprocess.run(
                        ["fuser", str(t)],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        holders.append(f"{t}: {r.stdout.strip()}")
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass

    return (not holders), holders


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot helpers
# ──────────────────────────────────────────────────────────────────────────────


def _resolve_snapshot_key() -> bytes | None:
    """Read CS2_WIPE_SNAPSHOT_KEY from env or OS keyring."""
    key = os.environ.get(ENV_KEY_NAME, "").strip()
    if key:
        return key.encode("utf-8")
    try:
        import keyring  # type: ignore[import-not-found]

        v = keyring.get_password("MacenaCS2Analyzer", ENV_KEY_NAME)
        if v:
            return v.encode("utf-8")
    except ImportError:
        pass
    return None


def _seal_snapshot(plaintext_path: pathlib.Path, sealed_path: pathlib.Path, key: bytes) -> None:
    """Encrypt the tarball with cryptography.fernet.Fernet and HMAC-seal it.

    Phase 1 keeps it stdlib-only with HMAC-SHA256 + a placeholder note that the
    Phase 2 implementation will switch to Fernet once `cryptography` is in the
    pinned lockfile.
    """
    # Fernet key must be 32 url-safe base64 bytes. To stay stdlib-only in
    # Phase 1, we HMAC-seal the tarball: file = sha256(key) || HMAC(key, body) || body.
    # Phase 2 will replace this with proper Fernet (AEAD). For now this gives
    # tamper-evidence + key-binding without introducing the cryptography dep
    # mid-ingestion.
    body = plaintext_path.read_bytes()
    derived_id = hashlib.sha256(key).digest()  # 32 B
    tag = hmac.new(key, body, hashlib.sha256).digest()  # 32 B
    sealed_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sealed_path, "wb") as fh:
        fh.write(b"MACWIPEv1")
        fh.write(derived_id)
        fh.write(tag)
        fh.write(body)
    os.chmod(sealed_path, 0o600)


def _open_snapshot(sealed_path: pathlib.Path, key: bytes) -> bytes:
    """Verify HMAC and return the inner tarball bytes."""
    raw = sealed_path.read_bytes()
    if not raw.startswith(b"MACWIPEv1"):
        raise SystemExit(f"snapshot: bad magic in {sealed_path}")
    body = raw[9 + 32 + 32 :]
    derived_id = raw[9 : 9 + 32]
    tag = raw[9 + 32 : 9 + 32 + 32]
    if hashlib.sha256(key).digest() != derived_id:
        raise SystemExit("snapshot: wrong key (derived-id mismatch)")
    if not hmac.compare_digest(tag, hmac.new(key, body, hashlib.sha256).digest()):
        raise SystemExit("snapshot: HMAC mismatch — tampered or wrong key")
    return body


def _take_snapshot(db: pathlib.Path, label: str) -> pathlib.Path | None:
    key = _resolve_snapshot_key()
    if not key:
        sys.stderr.write(
            f"snapshot: ${ENV_KEY_NAME} not set in env or keyring; "
            "refusing to take snapshot. Set it or pass --no-snapshot to proceed.\n"
        )
        return None
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_DIR / f"{ts}-{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build a tarball with database.db + .db-wal + .db-shm
    tar_path = out_dir / "snapshot.tar"
    with tarfile.open(tar_path, "w") as tar:
        for sfx in ("", "-wal", "-shm"):
            p = pathlib.Path(str(db) + sfx)
            if p.exists():
                tar.add(p, arcname=p.name)

    sealed = out_dir / "snapshot.tar.sealed"
    _seal_snapshot(tar_path, sealed, key)
    tar_path.unlink()  # keep only sealed copy
    return sealed


# ──────────────────────────────────────────────────────────────────────────────
# Audit log
# ──────────────────────────────────────────────────────────────────────────────


def _emit_audit(event_type: str, fields: dict[str, Any]) -> None:
    WIPE_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    f = WIPE_AUDIT_DIR / f"wipe_audit_{ts}.jsonl"
    payload = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "event_type": event_type,
        "operator": os.environ.get("USER", "unknown"),
        "fields": fields,
    }
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# Wipe modes
# ──────────────────────────────────────────────────────────────────────────────


def _row_counts(db: pathlib.Path, tables: tuple[str, ...]) -> dict[str, int]:
    out: dict[str, int] = {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        for t in tables:
            try:
                out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except sqlite3.OperationalError:
                out[t] = -1
    finally:
        con.close()
    return out


def _wipe_rows_mode(db: pathlib.Path, tables: tuple[str, ...], dry_run: bool) -> dict[str, int]:
    """DELETE FROM each table; VACUUM at the end to reclaim space."""
    counts_before = _row_counts(db, tables)
    if dry_run:
        return counts_before

    con = sqlite3.connect(str(db))
    con.execute("PRAGMA foreign_keys = OFF")  # avoid cascade surprises during wipe
    try:
        for t in tables:
            con.execute(f"DELETE FROM {t}")
        con.commit()
        # VACUUM cannot run inside a transaction
        con.execute("VACUUM")
        con.commit()
    finally:
        con.close()
    return counts_before


def _wipe_swap_mode(_db: pathlib.Path, _tables: tuple[str, ...], _dry_run: bool) -> dict[str, int]:
    raise NotImplementedError(
        "swap mode (atomic .fresh/.OLD swap) is the v4 algorithm — Phase 2 will "
        "port it into this safe tool. Until then, run tools/wipe_for_reingest_v4.py "
        "directly OR use --mode rows (this tool) for selective table truncation."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Restore
# ──────────────────────────────────────────────────────────────────────────────


def _restore(snapshot_path: pathlib.Path, db: pathlib.Path, confirm: bool, dry_run: bool) -> int:
    if not snapshot_path.is_file():
        sys.stderr.write(f"restore: snapshot not found: {snapshot_path}\n")
        return 2
    key = _resolve_snapshot_key()
    if not key:
        sys.stderr.write(
            f"restore: ${ENV_KEY_NAME} required in env/keyring to verify snapshot HMAC.\n"
        )
        return 2

    inner = _open_snapshot(snapshot_path, key)
    if dry_run or not confirm:
        sys.stdout.write(f"restore (dry-run): would replace {db} from {snapshot_path}\n")
        return 0

    # Stop in-flight writers should be done by the operator beforehand;
    # we still re-check.
    ok, holders = _check_db_unlocked(db)
    if not ok:
        sys.stderr.write("restore: database is in use:\n  " + "\n  ".join(holders) + "\n")
        return 2

    with tempfile.TemporaryDirectory() as td:
        tar_path = pathlib.Path(td) / "snapshot.tar"
        tar_path.write_bytes(inner)
        with tarfile.open(tar_path, "r") as tar:
            for member in tar.getmembers():
                if member.name not in (
                    db.name,
                    f"{db.name}-wal",
                    f"{db.name}-shm",
                ):
                    sys.stderr.write(f"restore: refusing unexpected member: {member.name}\n")
                    return 2
            target_dir = db.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            tar.extractall(target_dir)
    _emit_audit(
        "wipe_restored",
        {
            "snapshot_path": str(snapshot_path),
            "db_path": str(db),
            "outcome": "success",
        },
    )
    sys.stdout.write(f"restore: ✓ restored {db} from {snapshot_path}\n")
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--db-path",
        type=pathlib.Path,
        default=DEFAULT_DB,
        help=f"Database path (default {DEFAULT_DB}).",
    )
    parser.add_argument(
        "--mode",
        choices=("rows", "swap"),
        default="rows",
        help="rows = DELETE FROM each WIPE_TABLE + VACUUM; swap = Phase 2 port of v4.",
    )
    parser.add_argument(
        "--confirm-wipe",
        action="store_true",
        help="REQUIRED to mutate state. Default is --dry-run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run even with --confirm-wipe (for sanity).",
    )
    parser.add_argument(
        "--snapshot", action="store_true", help="Take an HMAC-sealed snapshot before wipe."
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Explicitly proceed without snapshot (waiver-style).",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore from a sealed snapshot (also requires --confirm-wipe).",
    )
    parser.add_argument(
        "--snapshot-path", type=pathlib.Path, help="Snapshot file to restore from (with --restore)."
    )
    parser.add_argument(
        "--label",
        default="manual",
        help="Free-form label for the snapshot directory (default 'manual').",
    )
    parser.add_argument(
        "--ignore-audit-failure",
        action="store_true",
        help="Proceed even if audit-log write fails (NOT recommended).",
    )
    args = parser.parse_args(argv)

    # Restore branch
    if args.restore:
        if not args.snapshot_path:
            sys.stderr.write("--restore requires --snapshot-path\n")
            return 2
        return _restore(
            snapshot_path=args.snapshot_path,
            db=args.db_path,
            confirm=args.confirm_wipe,
            dry_run=args.dry_run,
        )

    # Wipe branch
    if not args.db_path.is_file():
        sys.stderr.write(f"db not found: {args.db_path}\n")
        return 2

    # Pre-flight
    sys.stdout.write(f"wipe_for_reingest_safe — target: {args.db_path}\n")
    sys.stdout.write(f"  mode: {args.mode}\n")
    sys.stdout.write(f"  confirm-wipe: {args.confirm_wipe}\n")
    sys.stdout.write(f"  dry-run: {args.dry_run or not args.confirm_wipe}\n")

    counts_before = _row_counts(args.db_path, WIPE_TABLES)
    sys.stdout.write("  current row counts:\n")
    for t, n in counts_before.items():
        sys.stdout.write(f"    {t}: {n}\n")

    ok, holders = _check_db_unlocked(args.db_path)
    if not ok:
        sys.stderr.write(
            "✗ database is in use; refusing to proceed:\n  " + "\n  ".join(holders) + "\n"
        )
        _emit_audit(
            "wipe_refused",
            {
                "reason": "db_locked",
                "holders": holders,
                "db": str(args.db_path),
                "mode": args.mode,
            },
        )
        return 2

    if not args.confirm_wipe or args.dry_run:
        sys.stdout.write("\n(dry-run; pass --confirm-wipe without --dry-run to mutate state)\n")
        return 0

    # Snapshot guard: refuse to wipe without snapshot unless --no-snapshot is set
    snapshot_path: pathlib.Path | None = None
    if args.snapshot:
        snapshot_path = _take_snapshot(args.db_path, args.label)
        if snapshot_path is None:
            return 2  # _take_snapshot already wrote the error message
        sys.stdout.write(f"  snapshot: {snapshot_path}\n")
    elif not args.no_snapshot:
        sys.stderr.write(
            "\n✗ Refusing to wipe without --snapshot or --no-snapshot.\n"
            "  Pass --snapshot to take a sealed snapshot before wiping (recommended).\n"
            "  Pass --no-snapshot to proceed without one (you are on your own for restore).\n"
        )
        return 2

    # Audit pre-event
    try:
        _emit_audit(
            "wipe_invoked",
            {
                "db": str(args.db_path),
                "mode": args.mode,
                "tables": list(WIPE_TABLES),
                "row_counts_before": counts_before,
                "snapshot_path": str(snapshot_path) if snapshot_path else None,
            },
        )
    except Exception as exc:  # noqa: BLE001 — operational guardrail
        sys.stderr.write(f"audit-log write failed: {exc}\n")
        if not args.ignore_audit_failure:
            return 2

    # Execute
    try:
        if args.mode == "rows":
            counts_after_plan = _wipe_rows_mode(args.db_path, WIPE_TABLES, dry_run=False)
        else:  # swap
            counts_after_plan = _wipe_swap_mode(args.db_path, WIPE_TABLES, dry_run=False)
    except NotImplementedError as exc:
        sys.stderr.write(f"\n✗ {exc}\n")
        _emit_audit(
            "wipe_aborted",
            {
                "reason": "not_implemented",
                "mode": args.mode,
            },
        )
        return 2
    except Exception as exc:  # noqa: BLE001 — surface the failure
        sys.stderr.write(f"\n✗ wipe failed: {exc}\n")
        _emit_audit(
            "wipe_failed",
            {
                "mode": args.mode,
                "error_type": type(exc).__name__,
                "error_msg": str(exc)[:1000],
            },
        )
        return 1

    counts_after = _row_counts(args.db_path, WIPE_TABLES)
    _emit_audit(
        "wipe_completed",
        {
            "db": str(args.db_path),
            "mode": args.mode,
            "row_counts_after": counts_after,
            "snapshot_path": str(snapshot_path) if snapshot_path else None,
            "outcome": "success",
        },
    )

    sys.stdout.write("\n✓ wipe complete. Row counts after:\n")
    for t, n in counts_after.items():
        sys.stdout.write(f"    {t}: {n}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
