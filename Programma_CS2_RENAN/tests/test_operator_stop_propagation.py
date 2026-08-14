"""F-0032 regression: the operator STOP exception must PROPAGATE out of
every training phase and out of run_full_cycle, so MLController's
graceful `except TrainingStopRequested` path is reachable.

Pre-fix the guards said `except StopIteration: raise` — an exception
check_state() stopped raising at F5-16 — so Stop fell into each phase's
broad `except Exception`, the phase logged "Training Failed", the NEXT
phase started, and the final status reported a crash."""

from unittest.mock import MagicMock, patch

import pytest

from Programma_CS2_RENAN.backend.control.ml_controller import TrainingStopRequested
from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager


def _mgr() -> CoachTrainingManager:
    return CoachTrainingManager.__new__(CoachTrainingManager)


def test_jepa_phase_reraises_stop():
    mgr = _mgr()
    with patch(
        "Programma_CS2_RENAN.backend.nn.coach_manager.TrainingOrchestrator"
    ) as orch_cls:
        orch_cls.return_value.run_training.side_effect = TrainingStopRequested("stop")
        with pytest.raises(TrainingStopRequested):
            mgr.run_jepa_pretraining(context=MagicMock())


def test_rap_phase_reraises_stop():
    mgr = _mgr()
    with patch(
        "Programma_CS2_RENAN.backend.nn.coach_manager.TrainingOrchestrator"
    ) as orch_cls:
        orch_cls.return_value.run_training.side_effect = TrainingStopRequested("stop")
        with pytest.raises(TrainingStopRequested):
            mgr.run_rap_cycle(context=MagicMock())


def test_run_full_cycle_reraises_stop_not_cycle_failed(monkeypatch):
    """Stop between phases must NOT become 'Cycle Failed' + next phase."""
    mgr = _mgr()
    mgr.check_prerequisites = MagicMock(return_value=(True, "Ready"))
    mgr.assign_dataset_splits = MagicMock()
    mgr._execute_training_phases = MagicMock()

    state = MagicMock()
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.storage.state_manager.get_state_manager", lambda: state
    )

    context = MagicMock()
    context.check_state.side_effect = TrainingStopRequested("operator stop")

    with pytest.raises(TrainingStopRequested):
        mgr.run_full_cycle(context=context)

    # The crash path must not have fired.
    for call in state.set_error.call_args_list:
        assert "Cycle Failed" not in str(call), "stop was misreported as a crash"


def test_ordinary_crash_still_reports_cycle_failed(monkeypatch):
    """The broad-except crash path stays intact for real failures."""
    mgr = _mgr()
    mgr.check_prerequisites = MagicMock(return_value=(True, "Ready"))
    mgr.assign_dataset_splits = MagicMock(side_effect=RuntimeError("boom"))

    state = MagicMock()
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.storage.state_manager.get_state_manager", lambda: state
    )

    mgr.run_full_cycle(context=None)  # must not raise
    assert any("Cycle Failed" in str(c) for c in state.set_error.call_args_list)
