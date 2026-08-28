"""DOCTRINE D-13 regression — the P9-02 collapse feed must not false-fire.

Production JEPA batches are ONE contiguous window (R4 CRIT), so
``_log_embedding_diversity`` saw B=1 on every batch and returned a constant
0.0 ("unmeasurable" conflated with "collapsed"); the orchestrator averaged
those sentinels and the EmbeddingCollapseDetector hard-aborted EVERY
multi-epoch run at epoch 2. The fix: None for unmeasurable batches, and a
CROSS-window variance computed over the epoch's pooled embeddings feeds the
detector instead. These tests exercise the real trainer method, the real
detector, and the real ``_run_epoch_loop`` D-13 branch.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import torch

from Programma_CS2_RENAN.backend.nn.early_stopping import (
    EmbeddingCollapseDetector,
    EmbeddingCollapseError,
)
from Programma_CS2_RENAN.backend.nn.jepa_trainer import JEPATrainer


def _make_orchestrator(**kwargs):
    with patch(
        "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
        return_value=torch.device("cpu"),
    ):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        return TrainingOrchestrator(MagicMock(), model_type="jepa", **kwargs)


class TestDiversityMeasurement:
    def test_single_window_batch_is_unmeasurable_not_collapsed(self):
        # Real method; it uses no trainer state.
        shell = object.__new__(JEPATrainer)
        assert JEPATrainer._log_embedding_diversity(shell, torch.randn(1, 8)) is None

    def test_real_batch_measures_variance(self):
        shell = object.__new__(JEPATrainer)
        v = JEPATrainer._log_embedding_diversity(shell, torch.randn(16, 8))
        assert isinstance(v, float) and v > 0.01

    def test_incident_mechanism_two_zero_epochs_abort(self):
        # Pins WHY the 0.0 sentinel was fatal: the detector treats it as a
        # collapsed epoch and aborts at patience=2 — exactly what every
        # orchestrated run hit at epoch 2 before the fix.
        det = EmbeddingCollapseDetector(threshold=0.01, patience=2)
        det.update(0.0)
        with pytest.raises(EmbeddingCollapseError):
            det.update(0.0)


class TestCrossWindowFeed:
    """The orchestrator's D-13 branch, run through the real epoch loop."""

    def _loop(self, orch, trainer, embeddings_per_epoch):
        def _epoch(tr, batches, is_train=True, context=None):
            if is_train:
                orch._last_epoch_variances = []  # B=1: nothing measurable
                orch._last_epoch_embeddings = list(embeddings_per_epoch)
            return 1.5

        with patch.object(orch, "_run_epoch", side_effect=_epoch):
            with patch.object(orch, "_fetch_batches", return_value=[[1, 2, 3]]):
                return orch._run_epoch_loop(trainer, MagicMock(), [[1]], None)

    def test_healthy_cross_window_variance_completes(self):
        orch = _make_orchestrator(max_epochs=4, patience=10)
        orch.dry_run = True
        trainer = MagicMock()
        trainer.embedding_collapse_detector = EmbeddingCollapseDetector(threshold=0.01, patience=2)
        trainer.scheduler = None
        healthy = [torch.randn(8) for _ in range(16)]  # distinct windows

        final = self._loop(orch, trainer, healthy)

        assert final == 4  # ran to max_epochs — no false abort

    def test_true_collapse_still_aborts(self):
        # The hard-stop must stay ALIVE: identical embeddings across windows
        # (genuine collapse) abort within patience.
        orch = _make_orchestrator(max_epochs=5, patience=10)
        orch.dry_run = True
        trainer = MagicMock()
        trainer.embedding_collapse_detector = EmbeddingCollapseDetector(threshold=0.01, patience=2)
        trainer.scheduler = None
        collapsed = [torch.ones(8) for _ in range(16)]  # one point

        with pytest.raises(EmbeddingCollapseError):
            self._loop(orch, trainer, collapsed)

    def test_within_batch_variance_still_takes_precedence(self):
        # When real (B>=2) measurements exist, the classic within-batch mean
        # is used — the F-0024 contract from the existing flow tests holds.
        orch = _make_orchestrator(max_epochs=3, patience=10)
        orch.dry_run = True
        trainer = MagicMock()
        trainer.embedding_collapse_detector = EmbeddingCollapseDetector(threshold=0.01, patience=2)
        trainer.scheduler = None

        def _epoch(tr, batches, is_train=True, context=None):
            if is_train:
                orch._last_epoch_variances = [0.5, 0.6]
                # collapsed-looking embeddings must NOT override real measurements
                orch._last_epoch_embeddings = [torch.ones(8) for _ in range(4)]
            return 1.5

        with patch.object(orch, "_run_epoch", side_effect=_epoch):
            with patch.object(orch, "_fetch_batches", return_value=[[1, 2, 3]]):
                final = orch._run_epoch_loop(trainer, MagicMock(), [[1]], None)
        assert final == 3
