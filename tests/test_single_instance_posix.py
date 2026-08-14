"""F-0010 regression: POSIX single-instance enforcement is REAL.

The guard used to return True unconditionally off-Windows ("the project
currently targets Windows-only deployments") — contradicting the Linux
deploy doctrine and permitting concurrent SQLite writers."""

from unittest.mock import patch

import pytest

from Programma_CS2_RENAN.core import lifecycle as lc
from Programma_CS2_RENAN.core import lock_files


@pytest.fixture
def mgr(tmp_path, monkeypatch):
    monkeypatch.setattr(lock_files, "_lock_path", lambda name: tmp_path / f"{name}.lock")
    m = lc.AppLifecycleManager.__new__(lc.AppLifecycleManager)
    m._instance_mutex = None
    yield m
    lock_files._held_locks.discard("app_single_instance")


def test_first_instance_acquires(mgr, monkeypatch):
    monkeypatch.setattr(lc.sys, "platform", "linux")
    assert mgr.ensure_single_instance() is True
    assert lock_files.is_held("app_single_instance")


def test_second_instance_refused(mgr, monkeypatch):
    monkeypatch.setattr(lc.sys, "platform", "linux")
    assert mgr.ensure_single_instance() is True
    # A "second process": conflict comes from the live on-disk lock.
    with patch.object(lock_files, "acquire", side_effect=lock_files.LockConflict("held")):
        m2 = lc.AppLifecycleManager.__new__(lc.AppLifecycleManager)
        m2._instance_mutex = None
        assert m2.ensure_single_instance() is False
