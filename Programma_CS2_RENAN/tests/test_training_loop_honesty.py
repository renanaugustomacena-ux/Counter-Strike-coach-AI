"""DOCTRINE D-18/D-19/D-21/D-22 regressions — training-loop honesty batch.

- D-18: validation must score with the LEARNED temperature, not the 0.07
  default, or best-checkpoint ranking is scaled off-objective.
- D-19: the P3-C "ABORTED" gate must return non-success (F-0043) — it used
  to log ABORTED and let run_training report True.
- D-21: the minimum-data gate must count REAL rows (windows are the batch
  unit; multiplying by batch_size overstated JEPA rows ~3x).
- D-22 (R5-lite): a JEPA window crossing the round reset is not a next-step
  pair (spawn teleport) — dropped, never padded (J-5), via real SQL.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
import torch
from sqlmodel import Session, SQLModel, create_engine

from Programma_CS2_RENAN.backend.storage.db_models import PlayerTickState


def _make_orchestrator(**kwargs):
    with patch(
        "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
        return_value=torch.device("cpu"),
    ):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        return TrainingOrchestrator(MagicMock(), model_type="jepa", **kwargs)


class TestP3CAbortReturnsFailure:
    def test_high_fallback_rate_returns_false(self):
        orch = _make_orchestrator()
        orch._total_samples = 100
        orch._total_fallbacks = 40  # 40% > 30% threshold
        assert orch._finalize_training(MagicMock(), final_epoch=3) is False

    def test_healthy_run_returns_true(self):
        orch = _make_orchestrator()
        orch._total_samples = 100
        orch._total_fallbacks = 5
        assert orch._finalize_training(MagicMock(), final_epoch=3) is True


class TestSampleGateCountsRealRows:
    def _run(self, windows):
        orch = _make_orchestrator(max_epochs=1)
        orch.manager._fetch_jepa_windows.return_value = windows
        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        orch.TrainerClass = MagicMock(return_value=MagicMock())
        with patch(
            "Programma_CS2_RENAN.backend.nn.data_quality.run_pre_training_quality_check"
        ) as qc:
            qc.return_value = MagicMock(passed=True)
            with patch("Programma_CS2_RENAN.backend.nn.factory.ModelFactory") as mf:
                mf.get_model.return_value = mock_model
                with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.load_nn"):
                    with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.save_nn"):
                        with patch.object(orch, "_run_epoch_loop", return_value=1):
                            with patch.object(orch, "_finalize_training", return_value=True):
                                return orch.run_training()

    def test_44_real_rows_abort(self):
        # 4 windows x 11 ticks = 44 rows < 100 minimum. Under the old
        # windows*batch_size fiction this passed as "128 samples".
        assert self._run([[MagicMock()] * 11 for _ in range(4)]) is False

    def test_110_real_rows_pass(self):
        assert self._run([[MagicMock()] * 11 for _ in range(10)]) is True


class TestRoundBoundaryWindowGuard:
    """D-22 through the REAL window-expansion SQL on an in-memory DB."""

    def _manager_with_ticks(self, monkeypatch, rows):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            for r in rows:
                s.add(r)
            s.commit()

        class _FakeDB:
            @contextmanager
            def get_session(self):
                with Session(engine) as s:
                    yield s

        from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager

        mgr = CoachTrainingManager.__new__(CoachTrainingManager)
        mgr.db = _FakeDB()
        return mgr

    def _ticks(self, n, start_round, boundary_at=None):
        rows = []
        for i in range(n):
            rnd = start_round + (1 if boundary_at is not None and i >= boundary_at else 0)
            rows.append(
                PlayerTickState(
                    tick=i,
                    player_name="p1",
                    demo_name="demo-a",
                    round_number=rnd,
                )
            )
        return rows

    def test_same_round_window_kept(self, monkeypatch):
        mgr = self._manager_with_ticks(monkeypatch, self._ticks(11, start_round=3))
        anchors = [PlayerTickState(tick=0, player_name="p1", demo_name="demo-a", round_number=3)]
        monkeypatch.setattr(mgr, "_fetch_jepa_ticks", lambda **kw: anchors)

        windows = mgr._fetch_jepa_windows(is_pro=True, n_windows=1, window_len=11)

        assert len(windows) == 1
        assert [t.tick for t in windows[0]] == list(range(11))

    def test_cross_round_window_dropped_never_padded(self, monkeypatch):
        # Round flips at tick 6 — the window spans the reset: J-5 drop.
        mgr = self._manager_with_ticks(monkeypatch, self._ticks(11, start_round=3, boundary_at=6))
        anchors = [PlayerTickState(tick=0, player_name="p1", demo_name="demo-a", round_number=3)]
        monkeypatch.setattr(mgr, "_fetch_jepa_ticks", lambda **kw: anchors)

        windows = mgr._fetch_jepa_windows(is_pro=True, n_windows=1, window_len=11)

        assert windows == []


class TestValLossUsesLearnedTemperature:
    def test_eval_scores_with_model_tau(self):
        import math

        from Programma_CS2_RENAN.backend.nn.jepa_model import (
            JEPACoachingModel,
            jepa_contrastive_loss,
        )
        from Programma_CS2_RENAN.backend.nn.jepa_trainer import JEPATrainer
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        torch.manual_seed(42)
        model = JEPACoachingModel(input_dim=METADATA_DIM, output_dim=10)
        trainer = JEPATrainer(model, t_max=10)
        model.eval()  # deterministic forward for the reference computation
        with torch.no_grad():
            model.log_temperature.fill_(math.log(0.5))  # tau far from 0.07

        batch = {
            "context": torch.randn(1, 10, METADATA_DIM),
            "target": torch.randn(1, 1, METADATA_DIM),
            "negatives": torch.randn(1, 5, METADATA_DIM),
        }
        orch = _make_orchestrator()
        loss_val = orch._eval_step_jepa(trainer, batch)

        with torch.no_grad():
            pred, target = model.forward_jepa_pretrain(batch["context"], batch["target"])
            neg = trainer.encode_raw_negatives(batch["negatives"], 10)
            with_tau = jepa_contrastive_loss(pred, target, neg, torch.tensor(0.5)).item()
            with_default = jepa_contrastive_loss(pred, target, neg).item()

        assert loss_val == pytest.approx(with_tau, rel=1e-4)
        # The old default-temperature scoring produced a DIFFERENT ranking
        # quantity — pin that the divergence is real for a drifted tau.
        assert abs(with_tau - with_default) > 1e-6
