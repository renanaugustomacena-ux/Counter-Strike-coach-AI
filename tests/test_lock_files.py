"""Tests for ``Programma_CS2_RENAN.core.lock_files``.

Covers acquire / release / dead-PID reclaim / live-PID conflict /
context manager / signal handler installation.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from Programma_CS2_RENAN.core import lock_files


@pytest.fixture(autouse=True)
def _isolated_lock_dir(monkeypatch, tmp_path):
    """Each test gets its own .locks directory so they cannot collide."""
    monkeypatch.setattr(lock_files, "_LOCK_DIR", tmp_path / ".locks")
    # Reset the in-process held-locks set so test order doesn't matter.
    monkeypatch.setattr(lock_files, "_held_locks", set())
    yield


def test_acquire_creates_lock_file_with_pid_and_timestamp():
    path = lock_files.acquire("phase_d_track")
    assert path.exists()
    text = path.read_text().strip()
    pid_str, iso = text.split(maxsplit=1)
    assert int(pid_str) == os.getpid()
    assert "T" in iso  # ISO 8601 has a T separator


def test_acquire_then_release_removes_lock_file():
    lock_files.acquire("phase_d_track")
    lock_files.release("phase_d_track")
    assert not lock_files._lock_path("phase_d_track").exists()


def test_release_is_idempotent():
    # Releasing an unheld lock must not raise.
    lock_files.release("never_acquired")


def test_acquire_raises_on_live_pid_conflict():
    lock_files.acquire("phase_d_track")
    # Same process trying to acquire again sees its own live PID.
    with pytest.raises(lock_files.LockConflict) as excinfo:
        lock_files.acquire("phase_d_track")
    assert "phase_d_track" in str(excinfo.value)
    assert str(os.getpid()) in str(excinfo.value)


def test_acquire_reclaims_stale_lock_with_dead_pid(tmp_path):
    # Spawn a child, capture its PID, wait for it to exit, then write
    # that dead PID into the lock file.
    proc = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(0)"])
    proc.wait()
    dead_pid = proc.pid

    lock_path = lock_files._lock_path("phase_d_track")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(f"{dead_pid} 2026-01-01T00:00:00+00:00\n")

    # acquire must reclaim because the PID is dead.
    returned = lock_files.acquire("phase_d_track")
    assert returned == lock_path
    text = lock_path.read_text().strip()
    new_pid_str = text.split(maxsplit=1)[0]
    assert int(new_pid_str) == os.getpid()


def test_is_held_reflects_live_holder():
    assert not lock_files.is_held("phase_d_track")
    lock_files.acquire("phase_d_track")
    assert lock_files.is_held("phase_d_track")
    lock_files.release("phase_d_track")
    assert not lock_files.is_held("phase_d_track")


def test_holder_pid_returns_pid_for_live_holder():
    assert lock_files.holder_pid("phase_d_track") is None
    lock_files.acquire("phase_d_track")
    assert lock_files.holder_pid("phase_d_track") == os.getpid()


def test_holder_pid_returns_none_for_stale_lock():
    proc = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(0)"])
    proc.wait()
    dead_pid = proc.pid

    lock_path = lock_files._lock_path("phase_d_track")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(f"{dead_pid} 2026-01-01T00:00:00+00:00\n")

    assert lock_files.holder_pid("phase_d_track") is None


def test_liveness_handles_never_allocated_pid():
    # 26-WIN-02 regression: a never-allocated PID must read as dead and be
    # reclaimable, never crash the liveness probe. On Windows the POSIX
    # os.kill(pid, 0) idiom raised an uncaught OSError(WinError 87) here, so
    # acquire()/holder_pid()/is_held() exploded instead of returning.
    lock_path = lock_files._lock_path("phase_d_track")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("999999 2026-01-01T00:00:00+00:00\n")

    assert lock_files._is_pid_alive(999999) is False
    assert lock_files.holder_pid("phase_d_track") is None
    assert lock_files.is_held("phase_d_track") is False
    # acquire must reclaim (not raise) since the holder is not a live process.
    returned = lock_files.acquire("phase_d_track")
    assert returned == lock_path
    assert int(lock_path.read_text().split()[0]) == os.getpid()


def test_context_manager_releases_on_normal_exit():
    with lock_files.lock("phase_d_track") as path:
        assert path.exists()
    assert not lock_files._lock_path("phase_d_track").exists()


def test_context_manager_releases_on_exception():
    class _BoomError(RuntimeError):
        pass

    with pytest.raises(_BoomError):
        with lock_files.lock("phase_d_track"):
            raise _BoomError("intentional")
    assert not lock_files._lock_path("phase_d_track").exists()


def test_lock_name_with_path_separators_is_sanitized():
    # A malicious-looking name should not escape the lock directory.
    path = lock_files.acquire("../etc/shadow")
    assert path.parent == lock_files._LOCK_DIR
    assert ".." not in path.name
    assert "/" not in path.name


def test_install_signal_handlers_replaces_handler():
    prior_term = signal.signal(signal.SIGTERM, signal.SIG_DFL)
    prior_int = signal.getsignal(signal.SIGINT)
    try:
        lock_files.install_signal_handlers()
        current_term = signal.getsignal(signal.SIGTERM)
        assert current_term is not signal.SIG_DFL
        assert current_term is not signal.SIG_IGN
    finally:
        signal.signal(signal.SIGTERM, prior_term)
        # install_signal_handlers() also replaces SIGINT — restore it too, otherwise
        # the custom handler (which re-raises via os.kill) leaks into the rest of the
        # pytest session and fires a spurious KeyboardInterrupt during teardown on the
        # Windows CI runner, exiting non-zero despite all tests passing (AUDIT 26-WIN-01).
        signal.signal(signal.SIGINT, prior_int)
