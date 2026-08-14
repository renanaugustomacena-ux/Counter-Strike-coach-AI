"""F-0043 regression: run_training returns False on every abort path and
True on completion — the CLI exits 3 when a phase aborts instead of
reporting success with zero training done (T-DIAG root cause)."""

from unittest.mock import MagicMock, patch

import torch

from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator


def _orch() -> TrainingOrchestrator:
    with patch(
        "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
        return_value=torch.device("cpu"),
    ):
        return TrainingOrchestrator(MagicMock(), model_type="jepa")


def test_quality_gate_abort_returns_false():
    orch = _orch()
    with patch("Programma_CS2_RENAN.backend.nn.data_quality.run_pre_training_quality_check") as qc:
        qc.return_value = MagicMock(passed=False, summary=lambda: "bad data")
        assert orch.run_training() is False


def test_no_data_abort_returns_false():
    orch = _orch()
    with patch("Programma_CS2_RENAN.backend.nn.data_quality.run_pre_training_quality_check") as qc:
        qc.return_value = MagicMock(passed=True)
        with patch.object(orch, "_load_or_init_model", return_value=MagicMock()):
            with patch.object(orch, "_fetch_batches", return_value=[]):
                orch.TrainerClass = MagicMock()
                assert orch.run_training() is False


def test_completed_training_returns_true():
    orch = _orch()
    with patch("Programma_CS2_RENAN.backend.nn.data_quality.run_pre_training_quality_check") as qc:
        qc.return_value = MagicMock(passed=True)
        with patch.object(orch, "_load_or_init_model", return_value=MagicMock()):
            batches = [[1] * 11 for _ in range(20)]
            with patch.object(orch, "_fetch_batches", return_value=batches):
                with patch.object(orch, "_run_epoch_loop", return_value=1):
                    with patch.object(orch, "_finalize_training"):
                        orch.TrainerClass = MagicMock()
                        orch.callbacks = MagicMock()
                        assert orch.run_training() is True
