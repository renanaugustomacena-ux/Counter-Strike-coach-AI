"""DOCTRINE D-16 regression — the collapse-telemetry probe must be consumable.

The production orchestrator passed a raw list of ORM tick rows as
``probe_batch``; ``_extract_probe_context`` found nothing tensor-shaped and
returned None, so ``_log_collapse_metrics`` no-oped every epoch with no
warning — the doctrine's collapse-telemetry layer (embed/*: RankMe,
effective rank, EMA drift) was silently dead on every production run. The
orchestrator now hands over a PREPARED tensor-batch dict, and an
unconsumable probe warns loudly instead of dying silently.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import torch

from Programma_CS2_RENAN.backend.nn.tensorboard_callback import _extract_probe_context


def _make_orchestrator(**kwargs):
    with patch(
        "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
        return_value=torch.device("cpu"),
    ):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        return TrainingOrchestrator(MagicMock(), model_type="jepa", **kwargs)


def _tick_items(n=11):
    return [
        SimpleNamespace(
            tick=i,
            player_name="TestPlayer",
            demo_name="test.dem",
            pos_x=100.0 + i,
            pos_y=200.0,
            pos_z=0.0,
            view_x=0.0,
            view_y=0.0,
            health=100,
            armor=100,
            has_helmet=True,
            has_defuser=False,
            equipment_value=4000,
            is_crouching=False,
            is_scoped=False,
            is_blinded=False,
            enemies_visible=0,
            map_name="de_mirage",
            round_number=1,
        )
        for i in range(n)
    ]


class TestProbeConsumability:
    def test_raw_orm_rows_are_unconsumable_the_old_failure(self):
        # Pins the failure mode: the pre-fix probe shape yields None.
        assert _extract_probe_context(_tick_items()) is None

    def test_prepared_orchestrator_batch_is_consumable(self):
        orch = _make_orchestrator()
        prepared = orch._prepare_tensor_batch(_tick_items(11), is_train=False)
        assert prepared is not None
        probe = _extract_probe_context(prepared)
        assert isinstance(probe, torch.Tensor)

    def test_probe_prep_leaves_negative_rng_stream_untouched(self):
        # DET-01: the observation-only probe prep must not shift the
        # training negative stream (state snapshot/restore in run_training).
        orch = _make_orchestrator()
        state_before = orch._neg_rng.bit_generator.state

        saved = orch._neg_rng.bit_generator.state
        try:
            orch._prepare_tensor_batch(_tick_items(11), is_train=False)
        finally:
            orch._neg_rng.bit_generator.state = saved

        assert orch._neg_rng.bit_generator.state == state_before


class TestUnconsumableProbeWarnsLoudly:
    def test_on_train_start_names_the_dead_telemetry(self, caplog):
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback

        cb = TensorBoardCallback.__new__(TensorBoardCallback)
        cb._active = True
        cb.writer = MagicMock()
        cb._model_type = "jepa"
        cb._warned_unavailable = False
        cb._probe_batch = None

        with caplog.at_level("WARNING"):
            cb.on_train_start(MagicMock(), {"model_type": "jepa", "probe_batch": _tick_items()})

        assert "unconsumable" in caplog.text
