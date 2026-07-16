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


def _is_pid_alive_windows(pid: int) -> bool:
    """Windows liveness probe (26-WIN-02).

    POSIX ``os.kill(pid, 0)`` is unreliable on Windows: for a non-existent PID it
    raises ``OSError(WinError 87)`` instead of ``ProcessLookupError`` — which the
    POSIX branch would let propagate as an uncaught error out of ``acquire`` /
    ``holder_pid`` — and for a process that has already exited but whose handle is
    still referenced it *returns success* (a false "alive" that would leave a stale
    lock unreclaimed). Instead we open the process and read its exit code: a live
    process reports ``STILL_ACTIVE``; an exited one reports its real exit code even
    while a handle lingers; a non-existent PID cannot be opened at all.

    Caveat: a process that genuinely exits with code 259 (``STILL_ACTIVE``) reads as
    alive — a documented Windows limitation, negligible for lock-holder tools.
    """
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    ERROR_ACCESS_DENIED = 5

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # Non-existent PID (ERROR_INVALID_PARAMETER) -> dead. Access-denied means
        # the PID belongs to a live, more-privileged process -> alive (mirrors the
        # POSIX PermissionError branch).
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _is_pid_alive(pid: int) -> bool:
    """True iff a process with ``pid`` is currently alive on this host."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # POSIX os.kill(pid, 0) is unreliable on Windows (26-WIN-02): it crashes on
        # non-existent PIDs and false-positives on handle-retained exited processes.
        return _is_pid_alive_windows(pid)
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

    R4 HIGH (2026-07-16): the old read→check→write_text sequence was a
    TOCTOU — two processes could both pass the liveness check and both
    believe they hold the lock (last writer wins). Acquisition is now an
    atomic O_CREAT|O_EXCL create; reclaiming a stale lock goes through an
    atomic os.replace so only ONE contender performs the takeover and the
    losers loop back to re-evaluate.
    """
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    path = _lock_path(name)

    payload = f"{os.getpid()} {datetime.now(timezone.utc).isoformat()}\n"
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing = _read_lock(path)
            if existing is not None:
                pid, iso = existing
                if _is_pid_alive(pid):
                    raise LockConflict(f"lock {name!r} held by live process pid={pid} since {iso}")
            # Stale (dead holder) or unreadable half-written lock: steal it
            # atomically — os.replace succeeds for exactly one contender;
            # everyone else loops and re-evaluates the fresh state.
            stale = path.with_name(f"{path.name}.stale.{os.getpid()}")
            try:
                os.replace(path, stale)
            except FileNotFoundError:
                continue  # already reclaimed by someone else; retry O_EXCL
            try:
                stale.unlink()
            except FileNotFoundError:
                pass
            continue

        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
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
