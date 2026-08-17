"""TensorBoardCallback must log collapse metrics from a fixed probe batch.

The probe batch is sampled once at train start and reused every epoch:
metrics computed over varying batches would conflate change in the model with
change in the input, making the epoch-over-epoch trend — the entire signal —
uninterpretable.
"""

import tempfile

import pytest
import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback

pytestmark = pytest.mark.timeout(60)


class _StubModel(nn.Module):
    """Minimal stand-in exposing the JEPA attribute names the callback reads."""

    def __init__(self, d_in=8, d_out=16):
        super().__init__()
        self.context_encoder = nn.Linear(d_in, d_out)
        self.target_encoder = nn.Linear(d_in, d_out)


class _RecordingWriter:
    """Captures add_scalar calls without touching disk."""

    def __init__(self):
        self.scalars = {}

    def add_scalar(self, tag, value, step):
        self.scalars.setdefault(tag, []).append((step, value))

    def add_custom_scalars(self, *a, **kw):
        pass

    def add_histogram(self, *a, **kw):
        pass

    def flush(self):
        pass

    def close(self):
        pass


def _callback_with_recorder():
    cb = TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_collapse_"))
    rec = _RecordingWriter()
    cb.writer = rec
    return cb, rec


class TestCollapseLogging:
    """embed/* scalars appear only when a probe batch and encoder are present."""

    def test_logs_embed_scalars_each_epoch(self):
        cb, rec = _callback_with_recorder()
        model = _StubModel()
        probe = {"context": torch.randn(32, 8)}

        cb.on_train_start(model=model, config={"probe_batch": probe})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)

        for tag in (
            "embed/std_mean",
            "embed/std_min",
            "embed/effective_rank",
            "embed/cosine_offdiag_mean",
            "embed/ema_drift",
        ):
            assert tag in rec.scalars, f"missing {tag}"

    def test_no_probe_batch_skips_without_raising(self):
        cb, rec = _callback_with_recorder()
        model = _StubModel()

        cb.on_train_start(model=model, config={})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)

        assert not any(t.startswith("embed/") for t in rec.scalars)

    def test_probe_batch_is_fixed_across_epochs(self):
        cb, rec = _callback_with_recorder()
        model = _StubModel()
        probe = {"context": torch.randn(32, 8)}

        cb.on_train_start(model=model, config={"probe_batch": probe})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)
        cb.on_epoch_end(epoch=1, train_loss=1.0, val_loss=1.0, model=model)

        # The model never trained between epochs, so a fixed probe must give
        # identical values. A freshly sampled batch would not.
        vals = [v for _, v in rec.scalars["embed/std_mean"]]
        assert abs(vals[0] - vals[1]) < 1e-6

    def test_model_without_encoders_is_skipped(self):
        cb, rec = _callback_with_recorder()
        model = nn.Linear(4, 4)  # no context_encoder attribute

        cb.on_train_start(model=model, config={"probe_batch": {"context": torch.randn(8, 4)}})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)

        assert not any(t.startswith("embed/") for t in rec.scalars)
