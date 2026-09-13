"""Train-in-app round (WP4b) — the Train action asks the background service
for a run through CoachState and tells the user what happened, honestly.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _FakeStateManager:
    def __init__(self, *, heartbeat_age_s=5.0, ml_status="Idle", pending=False):
        hb = None
        if heartbeat_age_s is not None:
            hb = datetime.now(timezone.utc) - timedelta(seconds=heartbeat_age_s)
        self._state = SimpleNamespace(
            last_heartbeat=hb, ml_status=ml_status, training_requested=pending
        )
        self.requests: list[tuple[str, int]] = []
        self.stops = 0

    def get_state(self):
        return self._state

    def request_training(self, model_type, steps):
        if self._state.training_requested:
            return False
        self._state.training_requested = True
        self.requests.append((model_type, int(steps)))
        return True

    def request_training_stop(self):
        self.stops += 1


def _vm(monkeypatch, fake):
    from Programma_CS2_RENAN.apps.qt_app.viewmodels import training_vm

    monkeypatch.setattr(training_vm, "get_state_manager", lambda: fake)
    return training_vm.TrainingViewModel(), training_vm


def test_a_live_service_gets_the_request_queued(monkeypatch):
    fake = _FakeStateManager()
    vm, module = _vm(monkeypatch, fake)
    assert module.TrainingViewModel._request(200) == ("success", "queued")
    assert fake.requests == [("jepa_v2", 200)]


def test_an_offline_service_is_reported_not_queued(monkeypatch):
    fake = _FakeStateManager(heartbeat_age_s=900)
    vm, module = _vm(monkeypatch, fake)
    assert module.TrainingViewModel._request(200) == ("warning", "offline")
    assert fake.requests == []

    never = _FakeStateManager(heartbeat_age_s=None)
    _vm(monkeypatch, never)
    assert module.TrainingViewModel._request(200) == ("warning", "offline")


def test_a_running_or_pending_run_is_not_queued_twice(monkeypatch):
    busy = _FakeStateManager(ml_status="Learning")
    vm, module = _vm(monkeypatch, busy)
    assert module.TrainingViewModel._request(200) == ("warning", "busy")

    pending = _FakeStateManager(pending=True)
    _vm(monkeypatch, pending)
    assert module.TrainingViewModel._request(200) == ("warning", "pending")
    assert pending.requests == []


def test_request_training_runs_off_the_gui_thread_and_emits_a_message(qapp, monkeypatch):
    fake = _FakeStateManager()
    vm, _ = _vm(monkeypatch, fake)
    seen: list[tuple[str, str]] = []
    vm.message.connect(lambda severity, text: seen.append((severity, text)))

    vm.request_training(2000)
    for _ in range(200):
        qapp.processEvents()
        if seen:
            break
        import time

        time.sleep(0.01)

    assert fake.requests == [("jepa_v2", 2000)]
    assert seen and seen[0][0] == "success" and seen[0][1]


def test_request_stop_reaches_the_state_manager(qapp, monkeypatch):
    fake = _FakeStateManager(ml_status="Learning")
    vm, _ = _vm(monkeypatch, fake)
    seen: list[tuple[str, str]] = []
    vm.message.connect(lambda severity, text: seen.append((severity, text)))

    vm.request_stop()
    for _ in range(200):
        qapp.processEvents()
        if seen:
            break
        import time

        time.sleep(0.01)

    assert fake.stops == 1
    assert seen and seen[0][0] == "info"
