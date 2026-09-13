"""Train-in-app round (WP4b) — the GUI asks for training through CoachState;
the Teacher daemon picks the request up and routes it to the jepa_v2 pipeline
(legacy only when ALLOW_LEGACY_NEURAL_TRAINING is on).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture
def state_manager():
    from Programma_CS2_RENAN.backend.storage.state_manager import StateManager
    from Programma_CS2_RENAN.tests._memory_db import MemoryDB

    return StateManager(db=MemoryDB())


def test_request_training_round_trip(state_manager):
    assert state_manager.request_training("jepa_v2", 200) is True
    state = state_manager.get_state()
    assert state.training_requested is True
    assert state.training_request_model == "jepa_v2"
    assert state.training_request_steps == 200

    assert state_manager.pop_training_request() == {"model_type": "jepa_v2", "steps": 200}
    assert state_manager.get_state().training_requested is False
    assert state_manager.pop_training_request() is None


def test_a_pending_request_is_not_overwritten(state_manager):
    assert state_manager.request_training("jepa_v2", 200) is True
    assert state_manager.request_training("jepa_v2", 5000) is False
    assert state_manager.pop_training_request() == {"model_type": "jepa_v2", "steps": 200}


def test_stop_request_round_trip(state_manager):
    assert state_manager.stop_requested() is False
    state_manager.request_training_stop()
    assert state_manager.stop_requested() is True
    state_manager.clear_stop_request()
    assert state_manager.stop_requested() is False


def _forbid_legacy(monkeypatch):
    from Programma_CS2_RENAN.backend.nn import coach_manager

    class _Boom:
        def __init__(self, *a, **k):
            raise AssertionError("legacy CoachTrainingManager must not be constructed")

    monkeypatch.setattr(coach_manager, "CoachTrainingManager", _Boom)


def test_teacher_routes_a_request_to_the_v2_pipeline(monkeypatch, state_manager):
    from Programma_CS2_RENAN.backend.nn import training_pipeline
    from Programma_CS2_RENAN.core import config, session_engine

    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: False if key == "ALLOW_LEGACY_NEURAL_TRAINING" else default,
    )
    _forbid_legacy(monkeypatch)
    calls: list[dict] = []

    def fake_cycle(**kwargs):
        calls.append(kwargs)
        assert kwargs["stop"]() is False
        return SimpleNamespace(status="success", steps=kwargs["steps"], reason="")

    monkeypatch.setattr(training_pipeline, "run_v2_training_cycle", fake_cycle)

    assert session_engine._run_training_cycle("request", steps=200, state=state_manager) is True
    assert len(calls) == 1 and calls[0]["steps"] == 200

    state_manager.request_training_stop()
    assert session_engine._run_training_cycle("request", steps=10, state=state_manager) is True
    # the stop flag is consumed by the run: a stale flag must not kill the next one
    assert state_manager.stop_requested() is False


def test_teacher_uses_legacy_only_when_allowed(monkeypatch, state_manager):
    from Programma_CS2_RENAN.backend.nn import coach_manager, training_pipeline
    from Programma_CS2_RENAN.core import config, session_engine

    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: True if key == "ALLOW_LEGACY_NEURAL_TRAINING" else default,
    )
    legacy_calls: list[str] = []

    class _Legacy:
        def run_full_cycle(self, context=None):
            legacy_calls.append("run_full_cycle")

    monkeypatch.setattr(coach_manager, "CoachTrainingManager", _Legacy)
    monkeypatch.setattr(
        training_pipeline,
        "run_v2_training_cycle",
        lambda **kw: (_ for _ in ()).throw(AssertionError("v2 must not run")),
    )

    assert session_engine._run_training_cycle("auto", steps=None, state=state_manager) is True
    assert legacy_calls == ["run_full_cycle"]


def test_training_lock_makes_the_cycle_skip_when_busy(monkeypatch, state_manager):
    from Programma_CS2_RENAN.backend.control.ml_controller import _TRAINING_LOCK
    from Programma_CS2_RENAN.backend.nn import training_pipeline
    from Programma_CS2_RENAN.core import session_engine

    monkeypatch.setattr(
        training_pipeline,
        "run_v2_training_cycle",
        lambda **kw: (_ for _ in ()).throw(AssertionError("must not run under a held lock")),
    )
    assert _TRAINING_LOCK.acquire(blocking=False)
    try:
        assert session_engine._run_training_cycle("request", steps=5, state=state_manager) is False
    finally:
        _TRAINING_LOCK.release()
