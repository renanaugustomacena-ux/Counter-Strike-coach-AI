"""F-0009 regression: release() never destroys a FOREIGN live lock.

The docstring always claimed 'releasing an unheld lock is a no-op' but
the body unlinked whatever existed — a stray release(name) defeated the
D-track / HLTV-track mutual exclusion."""

import os

from Programma_CS2_RENAN.core import lock_files


def _use_tmp_lock_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(lock_files, "_lock_path", lambda name: tmp_path / f"{name}.lock")


def test_release_ignores_foreign_live_lock(monkeypatch, tmp_path):
    _use_tmp_lock_dir(monkeypatch, tmp_path)
    path = tmp_path / "d_track_running.lock"
    foreign_pid = os.getpid() + 1  # "another" process; liveness not required for the guard
    monkeypatch.setattr(
        lock_files, "_read_lock", lambda p: (foreign_pid, "2026-01-01T00:00:00+00:00")
    )
    path.write_text(f"{foreign_pid}\n2026-01-01T00:00:00+00:00")
    lock_files._held_locks.discard("d_track_running")

    lock_files.release("d_track_running")

    assert path.exists(), "foreign live lock was destroyed"


def test_release_removes_own_held_lock(monkeypatch, tmp_path):
    _use_tmp_lock_dir(monkeypatch, tmp_path)
    path = tmp_path / "mine.lock"
    path.write_text(f"{os.getpid()}\nnow")
    lock_files._held_locks.add("mine")
    try:
        lock_files.release("mine")
        assert not path.exists()
    finally:
        lock_files._held_locks.discard("mine")


def test_release_removes_own_pid_lock_even_if_untracked(monkeypatch, tmp_path):
    """Crash-recovery shape: our PID on disk but bookkeeping lost."""
    _use_tmp_lock_dir(monkeypatch, tmp_path)
    path = tmp_path / "orphaned.lock"
    monkeypatch.setattr(
        lock_files, "_read_lock", lambda p: (os.getpid(), "2026-01-01T00:00:00+00:00")
    )
    path.write_text(f"{os.getpid()}\nnow")
    lock_files._held_locks.discard("orphaned")

    lock_files.release("orphaned")
    assert not path.exists()
