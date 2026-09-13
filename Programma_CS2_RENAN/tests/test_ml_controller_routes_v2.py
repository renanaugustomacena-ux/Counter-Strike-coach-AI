"""Train-in-app round (WP4b) — MLController (console ``ml start``,
``/api/training/start``) runs the jepa_v2 pipeline with a stop hook wired to
the operator's soft-stop, and releases the training lock afterwards.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace


def _no_legacy(monkeypatch):
    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: False if key == "ALLOW_LEGACY_NEURAL_TRAINING" else default,
    )


def test_start_training_runs_the_v2_pipeline_and_releases_the_lock(monkeypatch):
    from Programma_CS2_RENAN.backend.control.ml_controller import _TRAINING_LOCK, MLController
    from Programma_CS2_RENAN.backend.nn import training_pipeline

    _no_legacy(monkeypatch)
    calls: list[dict] = []

    def fake_cycle(**kwargs):
        calls.append(kwargs)
        assert kwargs["stop"]() is False
        return SimpleNamespace(status="success", steps=1, reason="")

    monkeypatch.setattr(training_pipeline, "run_v2_training_cycle", fake_cycle)

    controller = MLController()
    controller.start_training()
    thread = controller.thread
    assert thread is not None
    thread.join(10)

    assert len(calls) == 1
    assert controller.get_status()["is_running"] is False
    assert _TRAINING_LOCK.acquire(blocking=False), "training lock leaked"
    _TRAINING_LOCK.release()


def test_stop_training_reaches_the_pipeline_hook(monkeypatch):
    from Programma_CS2_RENAN.backend.control.ml_controller import MLController
    from Programma_CS2_RENAN.backend.nn import training_pipeline

    _no_legacy(monkeypatch)
    started = threading.Event()
    outcome: dict = {}

    def fake_cycle(**kwargs):
        started.set()
        deadline = time.monotonic() + 10
        while not kwargs["stop"]():
            if time.monotonic() > deadline:
                outcome["timeout"] = True
                return SimpleNamespace(status="failed", steps=0, reason="hook never flipped")
            time.sleep(0.01)
        outcome["stopped"] = True
        return SimpleNamespace(status="stopped", steps=3, reason="")

    monkeypatch.setattr(training_pipeline, "run_v2_training_cycle", fake_cycle)

    controller = MLController()
    controller.start_training()
    assert started.wait(5)
    controller.stop_training()
    controller.thread.join(15)

    assert outcome == {"stopped": True}
    assert controller.get_status()["is_running"] is False
