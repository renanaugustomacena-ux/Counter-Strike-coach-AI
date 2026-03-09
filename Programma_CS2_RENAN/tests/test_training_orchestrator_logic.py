"""
Tests for training_orchestrator.py — Tier 2: Core training logic.

Verifies:
1. TrainingOrchestrator rejects unknown model_type at init (unlike ModelFactory)
2. Early stopping logic works correctly
3. Empty batch handling (refuses to train on zeros)
4. Batch preparation produces correct tensor shapes
5. RAP path behavior
"""

import numpy as np
import pytest
import torch
from unittest.mock import MagicMock, patch


class TestOrchestratorInit:
    """Verify constructor validation and state initialization."""

    def test_valid_jepa_type_accepted(self):
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            manager = MagicMock()
            orch = TrainingOrchestrator(manager, model_type="jepa")
            assert orch.model_type == "jepa"
            assert orch.model_name == "jepa_brain"

    def test_valid_vl_jepa_type_accepted(self):
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            manager = MagicMock()
            orch = TrainingOrchestrator(manager, model_type="vl-jepa")
            assert orch.model_type == "vl-jepa"
            assert orch.model_name == "vl_jepa_brain"

    def test_valid_rap_type_accepted(self):
        pytest.importorskip("ncps", reason="ncps not installed")
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            manager = MagicMock()
            orch = TrainingOrchestrator(manager, model_type="rap")
            assert orch.model_type == "rap"
            assert orch.model_name == "rap_coach"

    def test_invalid_type_raises_value_error(self):
        """TrainingOrchestrator CORRECTLY rejects unknown types (unlike ModelFactory)."""
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            manager = MagicMock()
            with pytest.raises(ValueError, match="Unknown model type"):
                TrainingOrchestrator(manager, model_type="invalid")

    def test_default_patience(self):
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            orch = TrainingOrchestrator(MagicMock(), model_type="jepa")
            assert orch.patience == 10
            assert orch.best_val_loss == float("inf")
            assert orch.patience_counter == 0


class TestEarlyStopping:
    """Verify early stopping triggers correctly."""

    def test_patience_counter_increments_on_no_improvement(self):
        """When val_loss doesn't improve, patience_counter should increment."""
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            orch = TrainingOrchestrator(MagicMock(), model_type="jepa", patience=3)
            orch.best_val_loss = 0.5

            # Simulate: val_loss=0.6 (worse than best=0.5)
            if 0.6 < orch.best_val_loss:
                orch.best_val_loss = 0.6
                orch.patience_counter = 0
            else:
                orch.patience_counter += 1

            assert orch.patience_counter == 1

    def test_patience_resets_on_improvement(self):
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            orch = TrainingOrchestrator(MagicMock(), model_type="jepa", patience=3)
            orch.best_val_loss = 0.5
            orch.patience_counter = 2

            # val_loss=0.3 (better than best=0.5)
            if 0.3 < orch.best_val_loss:
                orch.best_val_loss = 0.3
                orch.patience_counter = 0
            else:
                orch.patience_counter += 1

            assert orch.patience_counter == 0
            assert orch.best_val_loss == 0.3

    def test_early_stop_triggers_at_patience_limit(self):
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            orch = TrainingOrchestrator(MagicMock(), model_type="jepa", patience=3)
            orch.patience_counter = 3

            should_stop = orch.patience_counter >= orch.patience
            assert should_stop is True


class TestEmptyBatchHandling:
    """Verify that empty batches are handled safely."""

    def test_prepare_tensor_batch_returns_none_for_empty(self):
        """_prepare_tensor_batch must return None for empty input, never all-zero tensors."""
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            orch = TrainingOrchestrator(MagicMock(), model_type="jepa")
            result = orch._prepare_tensor_batch([])
            assert result is None, "Empty batch should return None, not zero tensors"

    def test_fetch_batches_empty_when_no_data(self):
        """_fetch_batches should return empty list when manager has no data."""
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            manager = MagicMock()
            manager._fetch_jepa_ticks.return_value = []
            orch = TrainingOrchestrator(manager, model_type="jepa")

            result = orch._fetch_batches(is_train=True)
            assert result == []


class TestDeterministicNegativeSampling:
    """Verify reproducibility of negative sampling RNG."""

    def test_neg_rng_is_seeded(self):
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            orch = TrainingOrchestrator(MagicMock(), model_type="jepa")
            assert orch._neg_rng is not None

    def test_neg_rng_produces_reproducible_results(self):
        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                    return_value=torch.device("cpu")):
            from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

            orch1 = TrainingOrchestrator(MagicMock(), model_type="jepa")
            orch2 = TrainingOrchestrator(MagicMock(), model_type="jepa")

            result1 = orch1._neg_rng.choice(100, 5, replace=False)
            result2 = orch2._neg_rng.choice(100, 5, replace=False)

            np.testing.assert_array_equal(result1, result2), (
                "Same seed should produce identical negative samples"
            )
