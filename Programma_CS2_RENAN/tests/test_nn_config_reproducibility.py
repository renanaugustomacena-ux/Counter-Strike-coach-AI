"""
CI tests for neural network config: seed reproducibility, device detection,
and constant consistency.

Covers: set_global_seed, get_device, GLOBAL_SEED, INPUT_DIM/OUTPUT_DIM
contract, and training determinism.

Target: 100% coverage of config.py public functions.
"""

import numpy as np
import pytest
import torch

from Programma_CS2_RENAN.backend.nn.config import (
    BATCH_SIZE,
    GLOBAL_SEED,
    HIDDEN_DIM,
    INPUT_DIM,
    OUTPUT_DIM,
    get_device,
    set_global_seed,
)

# ─── set_global_seed ──────────────────────────────────────────────────


class TestSetGlobalSeed:
    def test_seed_default_is_42(self):
        assert GLOBAL_SEED == 42

    def test_torch_deterministic_after_seed(self):
        """After set_global_seed, torch should produce deterministic results."""
        set_global_seed(42)
        t1 = torch.randn(10)
        set_global_seed(42)
        t2 = torch.randn(10)
        assert torch.equal(t1, t2), "Same seed should produce same random tensor"

    def test_numpy_deterministic_after_seed(self):
        """After set_global_seed, numpy should produce deterministic results."""
        set_global_seed(42)
        a1 = np.random.randn(10)
        set_global_seed(42)
        a2 = np.random.randn(10)
        np.testing.assert_array_equal(a1, a2)

    def test_different_seeds_different_results(self):
        """Different seeds should produce different random numbers."""
        set_global_seed(42)
        t1 = torch.randn(10)
        set_global_seed(99)
        t2 = torch.randn(10)
        assert not torch.equal(t1, t2)

    def test_cudnn_deterministic_enabled(self):
        """torch.backends.cudnn.deterministic should be True after seed."""
        set_global_seed(42)
        assert torch.backends.cudnn.deterministic is True

    def test_cudnn_benchmark_disabled(self):
        """torch.backends.cudnn.benchmark should be False after seed."""
        set_global_seed(42)
        assert torch.backends.cudnn.benchmark is False

    def test_training_reproducibility(self):
        """A simple training step should be reproducible with same seed."""
        results = []
        for _ in range(2):
            set_global_seed(42)
            model = torch.nn.Linear(10, 5)
            optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
            x = torch.randn(4, 10)
            y = torch.randn(4, 5)
            loss = torch.nn.functional.mse_loss(model(x), y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            results.append(loss.item())
        assert abs(results[0] - results[1]) < 1e-6, "Training should be reproducible"

    def test_custom_seed_value(self):
        """Non-default seed should also produce determinism."""
        set_global_seed(12345)
        t1 = torch.randn(5)
        set_global_seed(12345)
        t2 = torch.randn(5)
        assert torch.equal(t1, t2)


# ─── get_device ───────────────────────────────────────────────────────


class TestGetDevice:
    def test_returns_torch_device(self):
        device = get_device()
        assert isinstance(device, torch.device)

    def test_device_is_valid(self):
        """Device should be either 'cpu' or 'cuda:N'."""
        device = get_device()
        assert device.type in ("cpu", "cuda")

    def test_device_is_cached(self):
        """Same device should be returned on subsequent calls."""
        d1 = get_device()
        d2 = get_device()
        assert d1 == d2

    def test_tensor_can_be_moved_to_device(self):
        """Should be able to move a tensor to the detected device."""
        device = get_device()
        t = torch.randn(3, 3)
        t_moved = t.to(device)
        assert t_moved.device.type == device.type


# ─── Constants Consistency ────────────────────────────────────────────


class TestConfigConstants:
    def test_input_dim_matches_metadata_dim(self):
        """INPUT_DIM must match METADATA_DIM from vectorizer."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert INPUT_DIM == METADATA_DIM == 25

    def test_output_dim_positive(self):
        assert OUTPUT_DIM > 0

    def test_hidden_dim_positive(self):
        assert HIDDEN_DIM > 0

    def test_batch_size_reasonable(self):
        assert 1 <= BATCH_SIZE <= 256

    def test_jepa_model_dimensions_consistent(self):
        """JEPA model should instantiate with config constants."""
        from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel

        model = JEPACoachingModel(input_dim=INPUT_DIM, output_dim=INPUT_DIM)
        # Verify input dimension flows through
        x = torch.randn(2, 10, INPUT_DIM)
        with torch.no_grad():
            emb = model.context_encoder(x)
        assert emb.shape[0] == 2
        assert emb.shape[1] == 10
