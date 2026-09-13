"""Boot round (WP3) — a second launch raises the first window (QLocalServer)."""

from __future__ import annotations

import os
import time
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _pump(qapp, until, seconds: float = 2.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not until():
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()


def test_second_instance_raises_the_first(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.instance_guard import (
        InstanceGuard,
        notify_running_instance,
    )

    name = f"macena-test-{uuid4().hex}"
    raised: list[int] = []
    guard = InstanceGuard(name)
    try:
        assert guard.listen(lambda: raised.append(1)) is True
        assert notify_running_instance(name, timeout_ms=1000) is True
        _pump(qapp, until=lambda: bool(raised))
        assert raised == [1]
    finally:
        guard.close()


def test_notify_returns_false_when_nobody_listens(qapp):
    from Programma_CS2_RENAN.apps.qt_app.core.instance_guard import notify_running_instance

    assert notify_running_instance(f"macena-none-{uuid4().hex}", timeout_ms=200) is False


def test_listen_recovers_a_stale_server_name(qapp):
    """A crashed first instance may leave the socket name behind (POSIX)."""
    from Programma_CS2_RENAN.apps.qt_app.core.instance_guard import InstanceGuard

    name = f"macena-stale-{uuid4().hex}"
    first = InstanceGuard(name)
    assert first.listen(lambda: None) is True
    first.close()
    second = InstanceGuard(name)
    try:
        assert second.listen(lambda: None) is True
    finally:
        second.close()
