"""One writer per run, and both training paths wired to it.

Covers the fragmentation invariant (exactly one event file per run) and the
production callback chain in run_full_training_cycle, which is the path that
actually trains models — the legacy jepa_train.train_jepa_pretrain entry is
not what production uses.
"""

import argparse
import tempfile
from pathlib import Path

import pytest
import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.embedding_projector import EmbeddingProjector
from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback
from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry

pytestmark = pytest.mark.timeout(60)


class _StubModel(nn.Module):
    def __init__(self, d_in=8, d_out=16):
        super().__init__()
        self.context_encoder = nn.Linear(d_in, d_out)
        self.target_encoder = nn.Linear(d_in, d_out)


class TestSingleWriter:
    """Every component shares one SummaryWriter, so one event file per run."""

    def test_shared_writer_produces_single_event_file(self):
        log_dir = tempfile.mkdtemp(prefix="test_tb_integration_")
        tb = TensorBoardCallback(log_dir=log_dir, model_type="jepa_pretrain")
        projector = EmbeddingProjector(tb_writer=tb.writer, interval=1)
        callbacks = CallbackRegistry([tb, projector])

        model = _StubModel()
        probe = {"context": torch.randn(16, 8)}

        callbacks.fire(
            "on_train_start",
            model=model,
            config={"model_type": "jepa_pretrain", "probe_batch": probe},
        )
        for epoch in range(2):
            callbacks.fire(
                "on_epoch_end",
                epoch=epoch,
                train_loss=1.0,
                val_loss=1.0,
                model=model,
            )
        callbacks.close_all()

        events = list(Path(log_dir).glob("events.out.tfevents.*"))
        assert len(events) == 1, f"expected 1 event file, found {len(events)}: {events}"

    def test_event_file_contains_collapse_tags(self):
        ea = pytest.importorskip("tensorboard.backend.event_processing.event_accumulator")

        log_dir = tempfile.mkdtemp(prefix="test_tb_tags_")
        tb = TensorBoardCallback(log_dir=log_dir, model_type="jepa_pretrain")
        callbacks = CallbackRegistry([tb])

        model = _StubModel()
        callbacks.fire(
            "on_train_start",
            model=model,
            config={
                "model_type": "jepa_pretrain",
                "probe_batch": {"context": torch.randn(16, 8)},
            },
        )
        callbacks.fire("on_epoch_end", epoch=0, train_loss=1.0, val_loss=1.0, model=model)
        callbacks.close_all()

        acc = ea.EventAccumulator(log_dir)
        acc.Reload()
        tags = set(acc.Tags()["scalars"])
        assert "embed/std_mean" in tags
        assert "embed/effective_rank" in tags


class TestProbeShapeTolerance:
    """Two training paths hand over differently shaped batches.

    jepa_train's dataloader yields dicts with a "context" key; the production
    TrainingOrchestrator yields raw window tensors (rows 0..N-1 context, last
    row target). Both must work, and an unusable shape must not spam or crash.
    """

    def _record(self):
        cb = TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_shape_"))
        scalars = {}

        class _W:
            def add_scalar(self, tag, value, step):
                scalars.setdefault(tag, []).append(value)

            def add_custom_scalars(self, *a, **kw):
                pass

            def add_histogram(self, *a, **kw):
                pass

            def flush(self):
                pass

            def close(self):
                pass

        cb.writer = _W()
        return cb, scalars

    def test_dict_batch(self):
        cb, scalars = self._record()
        model = _StubModel()
        cb.on_train_start(model=model, config={"probe_batch": {"context": torch.randn(16, 8)}})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)
        assert "embed/std_mean" in scalars

    def test_raw_tensor_batch(self):
        cb, scalars = self._record()
        model = _StubModel()
        cb.on_train_start(model=model, config={"probe_batch": torch.randn(16, 8)})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)
        assert "embed/std_mean" in scalars

    def test_sequence_batch(self):
        cb, scalars = self._record()
        model = _StubModel()
        cb.on_train_start(model=model, config={"probe_batch": [torch.randn(16, 8)]})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)
        assert "embed/std_mean" in scalars

    def test_incompatible_shape_disables_quietly_after_one_warning(self, caplog):
        cb, scalars = self._record()
        model = _StubModel(d_in=8)
        # Wrong feature width: the encoder expects 8, this gives 99.
        cb.on_train_start(model=model, config={"probe_batch": torch.randn(16, 99)})

        with caplog.at_level("WARNING"):
            cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)
            cb.on_epoch_end(epoch=1, train_loss=1.0, val_loss=1.0, model=model)

        assert not any(t.startswith("embed/") for t in scalars)
        hits = [r for r in caplog.records if "probe batch" in r.getMessage().lower()]
        assert len(hits) == 1, "must warn once, then stay quiet"


class TestProductionCallbackChain:
    """run_full_training_cycle is the entry point that actually trains."""

    def _args(self, tmp):
        return argparse.Namespace(no_tensorboard=False, tb_logdir=tmp)

    def test_registers_projector_on_shared_writer(self):
        from run_full_training_cycle import _build_callbacks

        registry = _build_callbacks(self._args(tempfile.mkdtemp(prefix="test_tb_prod_")))
        kinds = {c.__class__.__name__ for c in registry.callbacks}

        assert "TensorBoardCallback" in kinds
        assert "MaturityObservatory" in kinds
        assert "EmbeddingProjector" in kinds, "Layer 4 must be in the production chain"

        tb = next(c for c in registry.callbacks if c.__class__.__name__ == "TensorBoardCallback")
        proj = next(c for c in registry.callbacks if c.__class__.__name__ == "EmbeddingProjector")
        assert proj._writer is tb.writer, "projector must share the writer, not open its own"
        registry.close_all()

    def test_tb_logdir_defaults_to_none_for_run_scoping(self):
        """default=RUNS_DIR would defeat build_run_dir()'s per-run directories."""
        import run_full_training_cycle as rftc

        parser = rftc._build_parser() if hasattr(rftc, "_build_parser") else None
        if parser is None:
            pytest.skip("no _build_parser factory exposed")
        args = parser.parse_args([])
        assert args.tb_logdir is None
