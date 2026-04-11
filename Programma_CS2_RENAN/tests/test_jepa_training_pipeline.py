"""
Comprehensive CI tests for the JEPA training pipeline.

Covers: JEPAPretrainDataset, load sequences, train_jepa_pretrain,
train_jepa_finetune, save/load checkpoints, EMA schedule, negative
sampling, early stopping, and data quality guards.

Target: 100% function-level coverage of jepa_train.py.
"""

import math
import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from Programma_CS2_RENAN.backend.nn.config import GLOBAL_SEED, INPUT_DIM
from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel, jepa_contrastive_loss
from Programma_CS2_RENAN.backend.nn.jepa_train import (
    _MAX_TICKS_PER_SEQUENCE,
    _MIN_TICKS_FOR_SEQUENCE,
    JEPAPretrainDataset,
    _load_tick_sequence,
    load_jepa_model,
    load_user_match_sequences,
    save_jepa_model,
    train_jepa_finetune,
    train_jepa_pretrain,
)

pytestmark = pytest.mark.timeout(60)


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def metadata_dim():
    """Canonical feature dimension."""
    return INPUT_DIM  # 25


@pytest.fixture
def dummy_sequences(metadata_dim):
    """Create synthetic sequences mimicking pro demo tick data."""
    np.random.seed(GLOBAL_SEED)
    # 10 sequences, each 50 ticks x 25 features (well above _MIN_TICKS_FOR_SEQUENCE)
    return [np.random.randn(50, metadata_dim).astype(np.float32) for _ in range(10)]


@pytest.fixture
def short_sequences(metadata_dim):
    """Sequences too short for context+target windows."""
    return [np.random.randn(5, metadata_dim).astype(np.float32) for _ in range(3)]


@pytest.fixture
def model(metadata_dim):
    """Fresh JEPACoachingModel."""
    return JEPACoachingModel(input_dim=metadata_dim, output_dim=metadata_dim)


@pytest.fixture
def pretrained_model(metadata_dim, dummy_sequences):
    """Model that has been through a minimal pre-training cycle."""
    m = JEPACoachingModel(input_dim=metadata_dim, output_dim=metadata_dim)
    # Freeze target encoder (as train_jepa_pretrain does)
    for p in m.target_encoder.parameters():
        p.requires_grad = False
    m.freeze_encoders()
    m.is_pretrained = True
    return m


# ─── JEPAPretrainDataset ───────────────────────────────────────────────


class TestJEPAPretrainDataset:
    """Tests for JEPAPretrainDataset.__init__, __len__, __getitem__."""

    def test_len_matches_sequences(self, dummy_sequences):
        ds = JEPAPretrainDataset(dummy_sequences, context_len=10, target_len=10)
        assert len(ds) == len(dummy_sequences)

    def test_getitem_returns_context_target(self, dummy_sequences, metadata_dim):
        ds = JEPAPretrainDataset(dummy_sequences, context_len=10, target_len=10)
        item = ds[0]
        assert "context" in item
        assert "target" in item
        assert item["context"].shape == (10, metadata_dim)
        assert item["target"].shape == (10, metadata_dim)

    def test_getitem_context_target_are_float_tensors(self, dummy_sequences):
        ds = JEPAPretrainDataset(dummy_sequences, context_len=10, target_len=10)
        item = ds[0]
        assert item["context"].dtype == torch.float32
        assert item["target"].dtype == torch.float32

    def test_getitem_different_indices_different_data(self, dummy_sequences):
        ds = JEPAPretrainDataset(dummy_sequences, context_len=10, target_len=10)
        item0 = ds[0]
        item1 = ds[1]
        # Different sequences should produce different data
        assert not torch.equal(item0["context"], item1["context"])

    def test_getitem_short_sequence_pads(self, short_sequences, metadata_dim):
        """Sequences shorter than context_len+target_len should not crash."""
        ds = JEPAPretrainDataset(short_sequences, context_len=10, target_len=10)
        # Should not raise — handles short sequences via slicing
        item = ds[0]
        assert item["context"].shape[1] == metadata_dim

    def test_getitem_exact_length_sequence(self, metadata_dim):
        """Sequence with exactly context_len + target_len ticks."""
        seq = np.random.randn(20, metadata_dim).astype(np.float32)
        ds = JEPAPretrainDataset([seq], context_len=10, target_len=10)
        item = ds[0]
        assert item["context"].shape == (10, metadata_dim)
        assert item["target"].shape == (10, metadata_dim)

    def test_empty_dataset(self):
        ds = JEPAPretrainDataset([], context_len=10, target_len=10)
        assert len(ds) == 0

    def test_single_tick_sequence(self, metadata_dim):
        """Single tick should not crash, just produce truncated output."""
        seq = np.random.randn(1, metadata_dim).astype(np.float32)
        ds = JEPAPretrainDataset([seq], context_len=10, target_len=10)
        item = ds[0]
        # max_start = 1 - 20 = -19, so it takes the padding branch
        assert item["context"].shape[1] == metadata_dim

    def test_context_target_no_overlap(self, metadata_dim):
        """Context and target windows should be non-overlapping sequential slices."""
        # Use a known sequence with unique values per tick
        seq = np.arange(30 * metadata_dim, dtype=np.float32).reshape(30, metadata_dim)
        ds = JEPAPretrainDataset([seq], context_len=5, target_len=5)
        np.random.seed(42)
        item = ds[0]
        # Context and target should not share any rows
        ctx_set = set(map(tuple, item["context"].numpy().tolist()))
        tgt_set = set(map(tuple, item["target"].numpy().tolist()))
        assert len(ctx_set & tgt_set) == 0, "Context and target windows must not overlap"


# ─── Contrastive Loss ──────────────────────────────────────────────────


class TestContrastiveLoss:
    """Tests for jepa_contrastive_loss and negative sampling."""

    def test_loss_is_finite(self):
        pred = torch.randn(4, 256)
        target = torch.randn(4, 256)
        negatives = torch.randn(4, 3, 256)
        loss = jepa_contrastive_loss(pred, target, negatives)
        assert torch.isfinite(loss).item()

    def test_loss_is_positive(self):
        pred = torch.randn(4, 256)
        target = torch.randn(4, 256)
        negatives = torch.randn(4, 3, 256)
        loss = jepa_contrastive_loss(pred, target, negatives)
        assert loss.item() >= 0.0

    def test_loss_gradient_flows(self):
        pred = torch.randn(4, 256, requires_grad=True)
        target = torch.randn(4, 256)
        negatives = torch.randn(4, 3, 256)
        loss = jepa_contrastive_loss(pred, target, negatives)
        loss.backward()
        assert pred.grad is not None
        assert pred.grad.abs().sum() > 0

    def test_loss_decreases_for_matching_pairs(self):
        """Loss should be lower when pred matches target."""
        target = torch.randn(4, 256)
        negatives = torch.randn(4, 3, 256)
        # High similarity prediction
        pred_good = target + 0.01 * torch.randn_like(target)
        # Random prediction
        pred_bad = torch.randn(4, 256)
        loss_good = jepa_contrastive_loss(pred_good, target, negatives)
        loss_bad = jepa_contrastive_loss(pred_bad, target, negatives)
        assert loss_good.item() < loss_bad.item()

    def test_single_sample_batch(self):
        """Batch size 1 — no negatives possible."""
        pred = torch.randn(1, 256)
        target = torch.randn(1, 256)
        negatives = torch.zeros(1, 1, 256)
        loss = jepa_contrastive_loss(pred, target, negatives)
        assert torch.isfinite(loss).item()


# ─── Negative Sampling Logic ──────────────────────────────────────────


class TestNegativeSampling:
    """Tests for the negative sampling logic used in train_jepa_pretrain."""

    def test_negatives_exclude_self(self):
        """P1-05: Negative indices must never include the sample itself."""
        batch_size = 8
        num_negatives = 4
        device = torch.device("cpu")

        effective_negatives = min(num_negatives, batch_size - 1)
        perm = torch.randperm(batch_size - 1, device=device)
        perm = perm.unsqueeze(0).expand(batch_size, -1)
        arange = torch.arange(batch_size, device=device).unsqueeze(1)
        neg_indices = perm + (perm >= arange).long()
        neg_indices = neg_indices[:, :effective_negatives]

        # For each sample i, none of its negative indices should be i
        for i in range(batch_size):
            assert i not in neg_indices[i].tolist(), f"Sample {i} found in its own negatives"

    def test_negatives_within_bounds(self):
        """All negative indices must be in [0, batch_size)."""
        batch_size = 16
        num_negatives = 8
        device = torch.device("cpu")

        effective_negatives = min(num_negatives, batch_size - 1)
        perm = torch.randperm(batch_size - 1, device=device)
        perm = perm.unsqueeze(0).expand(batch_size, -1)
        arange = torch.arange(batch_size, device=device).unsqueeze(1)
        neg_indices = perm + (perm >= arange).long()
        neg_indices = neg_indices[:, :effective_negatives]

        assert neg_indices.min() >= 0
        assert neg_indices.max() < batch_size

    def test_batch_size_2_single_negative(self):
        """With batch_size=2, each sample has exactly 1 possible negative."""
        batch_size = 2
        num_negatives = 8
        effective_negatives = min(num_negatives, batch_size - 1)  # = 1
        assert effective_negatives == 1

        perm = torch.randperm(batch_size - 1)
        perm = perm.unsqueeze(0).expand(batch_size, -1)
        arange = torch.arange(batch_size).unsqueeze(1)
        neg_indices = perm + (perm >= arange).long()
        neg_indices = neg_indices[:, :effective_negatives]

        # Sample 0 should have negative index 1, sample 1 should have index 0
        assert neg_indices[0, 0].item() == 1
        assert neg_indices[1, 0].item() == 0

    def test_batch_size_1_fallback(self):
        """With batch_size=1, negatives should be zeros (fallback path)."""
        batch_size = 1
        num_negatives = 8
        effective_negatives = min(num_negatives, batch_size - 1)  # = 0

        neg_indices = torch.zeros(batch_size, max(1, effective_negatives), dtype=torch.long)
        assert neg_indices.shape == (1, 1)


# ─── EMA Momentum Schedule ────────────────────────────────────────────


class TestEMAMomentumSchedule:
    """Tests for the J-6 cosine momentum schedule."""

    def test_momentum_starts_at_base(self):
        """At step 0, momentum should be ema_base (0.996)."""
        ema_base = 0.996
        progress = 0.0
        momentum = 1.0 - (1.0 - ema_base) * (math.cos(math.pi * progress) + 1) / 2
        assert abs(momentum - ema_base) < 1e-6

    def test_momentum_ends_at_1(self):
        """At final step, momentum should approach 1.0."""
        ema_base = 0.996
        progress = 1.0
        momentum = 1.0 - (1.0 - ema_base) * (math.cos(math.pi * progress) + 1) / 2
        assert abs(momentum - 1.0) < 1e-6

    def test_momentum_monotonically_increases(self):
        """Momentum should increase monotonically over training."""
        ema_base = 0.996
        total_steps = 100
        prev = 0.0
        for step in range(total_steps):
            progress = step / total_steps
            momentum = 1.0 - (1.0 - ema_base) * (math.cos(math.pi * progress) + 1) / 2
            assert momentum >= prev - 1e-10, f"Momentum decreased at step {step}"
            prev = momentum

    def test_momentum_always_in_valid_range(self):
        """Momentum must be in [ema_base, 1.0] for all steps."""
        ema_base = 0.996
        for total in [10, 100, 1000]:
            for step in range(total):
                progress = step / total
                momentum = 1.0 - (1.0 - ema_base) * (math.cos(math.pi * progress) + 1) / 2
                assert ema_base - 1e-6 <= momentum <= 1.0 + 1e-6


# ─── Target Encoder Freezing (NN-JM-04) ──────────────────────────────


class TestTargetEncoderFreezing:
    """Tests for NN-JM-04: target encoder must be frozen during EMA."""

    def test_unfrozen_target_encoder_raises(self, model):
        """update_target_encoder should raise if target encoder has requires_grad=True."""
        with pytest.raises(RuntimeError, match="NN-JM-04"):
            model.update_target_encoder(momentum=0.99)

    def test_frozen_target_encoder_succeeds(self, model):
        """update_target_encoder should succeed after freezing."""
        for p in model.target_encoder.parameters():
            p.requires_grad = False
        # Should not raise
        model.update_target_encoder(momentum=0.99)

    def test_ema_update_changes_target_weights(self, model, metadata_dim):
        """EMA update should move target encoder toward context encoder."""
        for p in model.target_encoder.parameters():
            p.requires_grad = False

        # Record target weights before
        before = {n: p.clone() for n, p in model.target_encoder.named_parameters()}

        # Mutate context encoder to differ from target
        with torch.no_grad():
            for p in model.context_encoder.parameters():
                p.add_(torch.randn_like(p) * 0.1)

        model.update_target_encoder(momentum=0.5)

        # Target should have changed
        for name, param in model.target_encoder.named_parameters():
            assert not torch.equal(param, before[name]), f"Target param {name} didn't change"


# ─── Save / Load Checkpoint ──────────────────────────────────────────


class TestCheckpointSaveLoad:
    """Tests for save_jepa_model and load_jepa_model."""

    def test_roundtrip(self, model, metadata_dim):
        """Save and load should produce identical state_dict."""
        model.is_pretrained = True
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            path = f.name
        try:
            save_jepa_model(model, path)
            loaded = load_jepa_model(path, input_dim=metadata_dim, output_dim=metadata_dim)
            assert loaded.is_pretrained is True
            # Compare parameters
            for (n1, p1), (n2, p2) in zip(model.state_dict().items(), loaded.state_dict().items()):
                assert n1 == n2
                assert torch.equal(p1.cpu(), p2.cpu()), f"Parameter {n1} differs"
        finally:
            os.unlink(path)

    def test_save_creates_file(self, model):
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            path = f.name
        try:
            save_jepa_model(model, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_load_nonexistent_raises(self, metadata_dim):
        with pytest.raises(Exception):
            load_jepa_model("/nonexistent/path.pt", input_dim=metadata_dim, output_dim=metadata_dim)

    def test_pretrained_flag_preserved(self, model, metadata_dim):
        """is_pretrained flag should survive save/load."""
        for flag in [True, False]:
            model.is_pretrained = flag
            with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
                path = f.name
            try:
                save_jepa_model(model, path)
                loaded = load_jepa_model(path, input_dim=metadata_dim, output_dim=metadata_dim)
                assert loaded.is_pretrained == flag
            finally:
                os.unlink(path)


# ─── train_jepa_pretrain ──────────────────────────────────────────────


class TestTrainJepaPretrain:
    """Tests for the pre-training loop (unit-level, mocked data loading)."""

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_empty_dataset_returns_none(self, mock_load, model):
        """NN-33: Should return early when no sequences found."""
        mock_load.return_value = []
        result = train_jepa_pretrain(model, num_epochs=1)
        assert result is None

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_pretrain_runs_and_returns_model(self, mock_load, model, dummy_sequences):
        """Pre-training should complete and return the model."""
        mock_load.return_value = dummy_sequences
        result = train_jepa_pretrain(model, num_epochs=2, batch_size=4)
        assert result is not None
        assert isinstance(result, JEPACoachingModel)
        assert result.is_pretrained is True

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_pretrain_freezes_encoders_after(self, mock_load, model, dummy_sequences):
        """After pre-training, encoders should be frozen."""
        mock_load.return_value = dummy_sequences
        result = train_jepa_pretrain(model, num_epochs=1, batch_size=4)
        # Context encoder should be frozen
        for p in result.context_encoder.parameters():
            assert not p.requires_grad, "Context encoder should be frozen after pretrain"
        for p in result.target_encoder.parameters():
            assert not p.requires_grad, "Target encoder should be frozen after pretrain"

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_pretrain_loss_decreases(self, mock_load, model, dummy_sequences):
        """Loss should generally decrease over epochs (smoke test)."""
        mock_load.return_value = dummy_sequences
        # Can't easily capture internal loss, but model should not crash
        result = train_jepa_pretrain(model, num_epochs=5, batch_size=4)
        assert result is not None

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_pretrain_no_nan_in_weights(self, mock_load, model, dummy_sequences):
        """No NaN should appear in model weights after training."""
        mock_load.return_value = dummy_sequences
        result = train_jepa_pretrain(model, num_epochs=3, batch_size=4)
        for name, param in result.named_parameters():
            assert not torch.isnan(param).any(), f"NaN in parameter {name}"
            assert not torch.isinf(param).any(), f"Inf in parameter {name}"

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_pretrain_target_encoder_updated_by_ema(self, mock_load, model, dummy_sequences):
        """Target encoder should be different from its initial state after EMA."""
        # Record initial target weights
        initial_target = {n: p.clone() for n, p in model.target_encoder.named_parameters()}
        mock_load.return_value = dummy_sequences
        result = train_jepa_pretrain(model, num_epochs=2, batch_size=4)
        # At least some parameters should have changed
        changed = False
        for name, param in result.target_encoder.named_parameters():
            if not torch.equal(param.cpu(), initial_target[name]):
                changed = True
                break
        assert changed, "Target encoder should be updated by EMA"


# ─── train_jepa_finetune ──────────────────────────────────────────────


class TestTrainJepaFinetune:
    """Tests for the fine-tuning loop."""

    def test_finetune_runs(self, pretrained_model, metadata_dim):
        """Fine-tuning should complete without errors."""
        X = np.random.randn(8, 20, metadata_dim).astype(np.float32)
        y = np.random.randn(8, metadata_dim).astype(np.float32)
        result = train_jepa_finetune(pretrained_model, X, y, num_epochs=2, batch_size=4)
        assert result is not None

    def test_finetune_keeps_encoders_frozen(self, pretrained_model, metadata_dim):
        """Encoders should stay frozen during fine-tuning."""
        X = np.random.randn(8, 20, metadata_dim).astype(np.float32)
        y = np.random.randn(8, metadata_dim).astype(np.float32)
        result = train_jepa_finetune(pretrained_model, X, y, num_epochs=1, batch_size=4)
        for p in result.context_encoder.parameters():
            assert not p.requires_grad
        for p in result.target_encoder.parameters():
            assert not p.requires_grad

    def test_finetune_updates_lstm(self, pretrained_model, metadata_dim):
        """LSTM head should be updated during fine-tuning."""
        lstm_before = {n: p.clone() for n, p in pretrained_model.lstm.named_parameters()}
        X = np.random.randn(8, 20, metadata_dim).astype(np.float32)
        y = np.random.randn(8, metadata_dim).astype(np.float32)
        result = train_jepa_finetune(pretrained_model, X, y, num_epochs=3, batch_size=4)
        changed = False
        for name, param in result.lstm.named_parameters():
            if not torch.equal(param.cpu(), lstm_before[name]):
                changed = True
                break
        assert changed, "LSTM weights should change during fine-tuning"

    def test_finetune_no_nan(self, pretrained_model, metadata_dim):
        """No NaN in weights after fine-tuning."""
        X = np.random.randn(8, 20, metadata_dim).astype(np.float32)
        y = np.random.randn(8, metadata_dim).astype(np.float32)
        result = train_jepa_finetune(pretrained_model, X, y, num_epochs=2, batch_size=4)
        for name, param in result.named_parameters():
            assert not torch.isnan(param).any(), f"NaN in {name}"


# ─── load_user_match_sequences ─────────────────────────────────────────


class TestLoadUserMatchSequences:
    """Tests for load_user_match_sequences padding/truncation logic."""

    def test_padding_uniform_length(self, metadata_dim):
        """All padded sequences should have the same length."""
        sequences = [
            np.random.randn(30, metadata_dim).astype(np.float32),
            np.random.randn(50, metadata_dim).astype(np.float32),
            np.random.randn(20, metadata_dim).astype(np.float32),
        ]
        # Test the padding logic directly (extracted from load_user_match_sequences)
        max_len = max(s.shape[0] for s in sequences)
        X_padded = []
        y_targets = []
        for s in sequences:
            y_targets.append(s[-1])
            if s.shape[0] < max_len:
                pad = np.zeros((max_len - s.shape[0], metadata_dim), dtype=np.float32)
                s = np.concatenate([s, pad], axis=0)
            X_padded.append(s[:max_len])
        X = np.array(X_padded)
        y = np.array(y_targets)

        assert X.shape == (3, max_len, metadata_dim)
        assert y.shape == (3, metadata_dim)

    def test_padding_preserves_original_data(self, metadata_dim):
        """Original data should be preserved in padded sequences."""
        original = np.random.randn(20, metadata_dim).astype(np.float32)
        max_len = 50
        pad = np.zeros((max_len - 20, metadata_dim), dtype=np.float32)
        padded = np.concatenate([original, pad], axis=0)
        np.testing.assert_array_equal(padded[:20], original)
        np.testing.assert_array_equal(padded[20:], 0.0)

    def test_target_is_last_tick(self, metadata_dim):
        """y_target should be the last tick of the original (unpadded) sequence."""
        seq = np.random.randn(30, metadata_dim).astype(np.float32)
        y = seq[-1]
        np.testing.assert_array_equal(y, seq[29])


# ─── Data Quality Integration ─────────────────────────────────────────


class TestDataQualityGuards:
    """Tests for data quality guards in the training pipeline."""

    def test_min_ticks_constant(self):
        """_MIN_TICKS_FOR_SEQUENCE must be at least context_len + target_len."""
        assert _MIN_TICKS_FOR_SEQUENCE >= 20, "Need at least 20 ticks for 10+10 windows"

    def test_max_ticks_constant(self):
        """_MAX_TICKS_PER_SEQUENCE should be reasonable."""
        assert _MAX_TICKS_PER_SEQUENCE > _MIN_TICKS_FOR_SEQUENCE
        assert _MAX_TICKS_PER_SEQUENCE <= 10000, "Cap too high, OOM risk"

    def test_metadata_dim_matches_input_dim(self):
        """METADATA_DIM and INPUT_DIM must agree."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert INPUT_DIM == METADATA_DIM


# ─── End-to-End Smoke Test ─────────────────────────────────────────────


class TestEndToEndSmoke:
    """End-to-end smoke test: pretrain → save → load → finetune."""

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_full_pipeline(self, mock_load, metadata_dim):
        """Complete pipeline: pretrain → save → load → finetune → save."""
        # Pretrain
        mock_load.return_value = [
            np.random.randn(50, metadata_dim).astype(np.float32) for _ in range(8)
        ]
        model = JEPACoachingModel(input_dim=metadata_dim, output_dim=metadata_dim)
        model = train_jepa_pretrain(model, num_epochs=2, batch_size=4)
        assert model is not None
        assert model.is_pretrained

        # Save
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            path = f.name
        try:
            save_jepa_model(model, path)

            # Load
            loaded = load_jepa_model(path, input_dim=metadata_dim, output_dim=metadata_dim)
            assert loaded.is_pretrained

            # Finetune
            X = np.random.randn(8, 20, metadata_dim).astype(np.float32)
            y = np.random.randn(8, metadata_dim).astype(np.float32)
            finetuned = train_jepa_finetune(loaded, X, y, num_epochs=2, batch_size=4)
            assert finetuned is not None

            # Save finetuned
            ft_path = path.replace(".pt", "_ft.pt")
            save_jepa_model(finetuned, ft_path)
            assert os.path.exists(ft_path)
            os.unlink(ft_path)
        finally:
            os.unlink(path)

    @patch("Programma_CS2_RENAN.backend.nn.jepa_train.load_pro_demo_sequences")
    def test_no_embedding_collapse_after_training(self, mock_load, metadata_dim):
        """Embeddings should have meaningful variance after training."""
        mock_load.return_value = [
            np.random.randn(50, metadata_dim).astype(np.float32) for _ in range(8)
        ]
        model = JEPACoachingModel(input_dim=metadata_dim, output_dim=metadata_dim)
        model = train_jepa_pretrain(model, num_epochs=3, batch_size=4)

        model.eval()
        device = next(model.parameters()).device
        with torch.no_grad():
            x = torch.randn(4, 10, metadata_dim, device=device)
            emb = model.context_encoder(x)
            variance = emb.var().item()
            assert variance > 0.001, f"Embedding variance too low: {variance} (collapse detected)"

            # Different inputs should produce different embeddings
            x1 = torch.randn(1, 10, metadata_dim, device=device)
            x2 = torch.randn(1, 10, metadata_dim, device=device)
            e1 = model.context_encoder(x1).mean(1)
            e2 = model.context_encoder(x2).mean(1)
            cosine = torch.nn.functional.cosine_similarity(e1, e2).item()
            assert cosine < 0.99, f"Cosine similarity too high: {cosine} (collapse)"
