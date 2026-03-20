"""
Tests for persistence.py — Bug #1: Stale checkpoint handling.

Originally, load_nn() detected architecture mismatches (size mismatch on
load_state_dict) and set model._stale_checkpoint = True, but NO caller in the
entire codebase checked this flag — models silently ran with RANDOM WEIGHTS.

The fix: load_nn() now raises StaleCheckpointError on dimension mismatch,
forcing all callers to handle the error explicitly.

These tests verify:
1. StaleCheckpointError is raised on architecture mismatch
2. Normal loads work correctly (weights match checkpoint)
3. Missing checkpoints return the model unchanged
4. Corrupted checkpoints are handled explicitly
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import torch
import torch.nn as nn


@pytest.fixture
def model_dir(tmp_path):
    """Temporary directory for model checkpoints."""
    d = tmp_path / "models" / "global"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def small_model():
    """A simple model with input_dim=10 for testing dimension mismatches."""
    return nn.Sequential(nn.Linear(10, 5), nn.ReLU(), nn.Linear(5, 2))


@pytest.fixture
def large_model():
    """A simple model with input_dim=25 (production size)."""
    return nn.Sequential(nn.Linear(25, 5), nn.ReLU(), nn.Linear(5, 2))


class TestStaleCheckpointDetection:
    """Verify that load_nn correctly detects architecture mismatches."""

    def test_dimension_mismatch_raises_stale_checkpoint_error(
        self, model_dir, small_model, large_model
    ):
        """When loading a checkpoint saved with different dimensions,
        load_nn must raise StaleCheckpointError."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError, match="is incompatible"):
                load_nn("latest", large_model)

    def test_stale_error_contains_path_info(self, model_dir, small_model, large_model):
        """StaleCheckpointError message must include the checkpoint path for debugging."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError) as exc_info:
                load_nn("latest", large_model)

            assert str(checkpoint_path) in str(
                exc_info.value
            ), "Error message should contain the checkpoint path"

    def test_stale_error_chains_original_runtime_error(self, model_dir, small_model, large_model):
        """StaleCheckpointError must chain the original RuntimeError via __cause__."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError) as exc_info:
                load_nn("latest", large_model)

            assert (
                exc_info.value.__cause__ is not None
            ), "StaleCheckpointError should chain the original RuntimeError"
            assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_normal_load_succeeds(self, model_dir, small_model):
        """A successful load should return the model with correct weights, no error."""
        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        fresh_model = nn.Sequential(nn.Linear(10, 5), nn.ReLU(), nn.Linear(5, 2))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            result = load_nn("latest", fresh_model)

        assert not getattr(
            result, "_stale_checkpoint", False
        ), "Successful load should NOT have stale flag"

    def test_model_weights_differ_after_successful_load(self, model_dir, small_model):
        """After a successful load, model weights should match the checkpoint, not be random."""
        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        fresh_model = nn.Sequential(nn.Linear(10, 5), nn.ReLU(), nn.Linear(5, 2))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            result = load_nn("latest", fresh_model)

        for p_loaded, p_original in zip(result.parameters(), small_model.parameters()):
            assert torch.allclose(
                p_loaded, p_original
            ), "Loaded model weights should match checkpoint"

    def test_no_checkpoint_raises_file_not_found(self, model_dir):
        """When no checkpoint exists, load_nn must raise FileNotFoundError (NN-14)."""
        model = nn.Sequential(nn.Linear(10, 5))

        nonexistent = model_dir / "nonexistent.pt"
        with (
            patch(
                "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
                return_value=nonexistent,
            ),
            patch(
                "Programma_CS2_RENAN.backend.nn.persistence.get_factory_model_path",
                return_value=nonexistent,
            ),
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(FileNotFoundError):
                load_nn("latest", model)


class TestStaleCheckpointPreventsInference:
    """Verify that stale checkpoints cannot be silently used for inference."""

    def test_stale_checkpoint_prevents_silent_usage(self, model_dir, small_model, large_model):
        """load_nn must raise StaleCheckpointError, preventing silent inference
        with random weights. This was Bug #1 — now fixed."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError):
                load_nn("latest", large_model)

    def test_stale_error_is_runtime_error_subclass(self):
        """StaleCheckpointError should be a RuntimeError subclass so existing
        except RuntimeError handlers still catch it when appropriate."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        assert issubclass(StaleCheckpointError, RuntimeError)


class TestCorruptedCheckpoints:
    """Verify handling of corrupted or invalid checkpoint files."""

    def test_corrupted_file_raises(self, model_dir):
        """A corrupted checkpoint file must raise — production re-raises (NN-14)."""
        checkpoint_path = model_dir / "latest.pt"
        checkpoint_path.write_bytes(b"not a valid pytorch checkpoint")

        model = nn.Sequential(nn.Linear(10, 5))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(Exception):
                load_nn("latest", model)

    def test_empty_file_raises(self, model_dir):
        """An empty checkpoint file must raise — production re-raises (NN-14)."""
        checkpoint_path = model_dir / "latest.pt"
        checkpoint_path.write_bytes(b"")

        model = nn.Sequential(nn.Linear(10, 5))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(Exception):
                load_nn("latest", model)
