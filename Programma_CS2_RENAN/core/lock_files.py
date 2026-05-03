"""Lock file utilities for D-track ↔ HLTV-track concurrency.

Used to prevent concurrent writers on database.db during long-running
data-migration phases. Each tool acquires a named lock at startup and
releases it on exit (signal-handled). A second tool trying to acquire
the same name finds the lock file and raises LockConflict, unless the
holder PID is dead — in which case the lock is reclaimed.

Lock file format: one line ``<pid> <iso_timestamp>`` written atomically.
Lock directory: ``<repo_root>/.locks/<name>.lock``.

Why repo-root .locks/ and not /tmp or /var/run:
  - Locks must survive across user sessions (a long migration may run
    overnight) but not across machine reboots; .locks/ is wiped by
    .gitignore + manual cleanup, not by /tmp's reboot semantics.
  - Repo-local locks make it obvious which workspace owns the lock
    when multiple checkouts of the project exist.
"""

from __future__ import annotations

import os
import signal
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional, Set, Tuple

# Locks live under ``<repo_root>/.locks/``. The repo root is two levels up
# from this file (``Programma_CS2_RENAN/core/lock_files.py``).
_LOCK_DIR = Path(__file__).resolve().parents[2] / ".locks"

_held_locks: Set[str] = set()


class LockConflict(RuntimeError):
    """Raised when a named lock is already held by a live process."""


def _lock_path(name: str) -> Path:
    # Sanitize so callers can't escape the lock directory.
    safe = name.replace("/", "_").replace("..", "_").replace(os.sep, "_")
    return _LOCK_DIR / f"{safe}.lock"


def _read_lock(path: Path) -> Optional[Tuple[int, str]]:
    """Return (pid, iso_ts) from a lock file, or None if missing/malformed."""
    try:
        text = path.read_text().strip()
    except FileNotFoundError:
        return None
    try:
        pid_str, iso = text.split(maxsplit=1)
        return int(pid_str), iso
    except ValueError:
        return None


def _is_pid_alive(pid: int) -> bool:
    """True iff a process with ``pid`` is currently alive on this host."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)  # Signal 0 = liveness probe; raises if dead
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by another user; treat as alive.
        return True


def acquire(name: str) -> Path:
    """Acquire a named lock and return the lock file path.

    Raises LockConflict if a live process already holds the lock.
    Reclaims the lock if the holder PID is dead (process crashed
    without releasing).
    """
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    path = _lock_path(name)

    existing = _read_lock(path)
    if existing is not None:
        pid, iso = existing
        if _is_pid_alive(pid):
            raise LockConflict(f"lock {name!r} held by live process pid={pid} since {iso}")
        # Stale lock; the holder PID is dead. Fall through to reclaim.

    iso_now = datetime.now(timezone.utc).isoformat()
    path.write_text(f"{os.getpid()} {iso_now}\n")
    _held_locks.add(name)
    return path


def release(name: str) -> None:
    """Release a named lock. Idempotent — releasing an unheld lock is a no-op."""
    path = _lock_path(name)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    _held_locks.discard(name)


def is_held(name: str) -> bool:
    """True iff the named lock is currently held by a live process."""
    existing = _read_lock(_lock_path(name))
    if existing is None:
        return False
    return _is_pid_alive(existing[0])


def holder_pid(name: str) -> Optional[int]:
    """Return the PID currently holding the named lock, or None if unheld."""
    existing = _read_lock(_lock_path(name))
    if existing is None:
        return None
    pid, _iso = existing
    return pid if _is_pid_alive(pid) else None


@contextmanager
def lock(name: str) -> Iterator[Path]:
    """Context manager: acquire on enter, release on exit (incl. exceptions)."""
    path = acquire(name)
    try:
        yield path
    finally:
        release(name)


def _release_all_on_signal(signum, _frame):
    for name in list(_held_locks):
        release(name)
    # Re-raise the original signal with default disposition so the
    # process actually terminates (otherwise we just swallow SIGTERM).
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def install_signal_handlers() -> None:
    """Install SIGTERM/SIGINT handlers that release held locks before exit.

    Call once per process at startup. Idempotent across re-installation
    because ``signal.signal`` replaces the prior handler.
    """
    signal.signal(signal.SIGTERM, _release_all_on_signal)
    signal.signal(signal.SIGINT, _release_all_on_signal)
