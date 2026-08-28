"""DOCTRINE D-14 regression — one concept label per SAMPLE, not per tick.

The orchestrator's VL branch used to pass one RoundStats per CONTEXT TICK
for a ONE-window batch: (10, 16) labels against (1, 16) logits crashed
``F.binary_cross_entropy_with_logits`` (no broadcast) on the first batch
whose window had >=2 labeled ticks — and when exactly one tick resolved, it
silently paired an arbitrary tick's label with the whole window's logits.
The orchestrator now collapses to the LAST context tick's RoundStats, and
``_resolve_concept_labels`` carries a loud batch-shape contract. These tests
run the REAL trainer + model end-to-end on CPU.
"""

from __future__ import annotations

import math

import pytest
import torch

from Programma_CS2_RENAN.backend.nn.jepa_model import VLJEPACoachingModel
from Programma_CS2_RENAN.backend.nn.jepa_trainer import JEPATrainer, _resolve_concept_labels
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.backend.storage.db_models import RoundStats


def _round_stats() -> RoundStats:
    return RoundStats(
        demo_name="d",
        player_name="p",
        round_number=1,
        side="T",
        kills=2,
        deaths=0,
        damage_dealt=180,
        round_won=True,
        opening_kill=True,
        equipment_value=4500,
    )


def _trainer() -> JEPATrainer:
    model = VLJEPACoachingModel(input_dim=METADATA_DIM, output_dim=10, latent_dim=64)
    return JEPATrainer(model, t_max=10)


class TestResolveConceptLabelsContract:
    def test_per_tick_labels_raise_named_error(self):
        # The exact pre-fix orchestrator shape: 10 per-tick labels for a
        # 1-window logits batch. Must fail LOUDLY with the D-14 name, not
        # crash later inside BCE (or silently mispair).
        logits = torch.randn(1, 16)
        with pytest.raises(ValueError, match="D-14"):
            _resolve_concept_labels([_round_stats()] * 10, logits, torch.device("cpu"))

    def test_one_label_per_sample_passes(self):
        logits = torch.randn(1, 16)
        labels, out_logits = _resolve_concept_labels([_round_stats()], logits, torch.device("cpu"))
        assert labels.shape == (1, 16)
        assert out_logits.shape == (1, 16)


class TestTrainStepVlEndToEnd:
    def test_single_window_batch_trains_with_one_label(self):
        # The repaired production shape: (1, 10, 25) window, one RoundStats.
        trainer = _trainer()
        result = trainer.train_step_vl(
            x_context=torch.randn(1, 10, METADATA_DIM),
            x_target=torch.randn(1, 1, METADATA_DIM),
            negatives=torch.randn(1, 5, METADATA_DIM),
            round_stats=[_round_stats()],
        )
        assert result["label_source"] == "round_stats"
        assert math.isfinite(result["total_loss"])
        assert result["concept_loss"] >= 0.0

    def test_per_tick_labels_fail_loudly_not_opaquely(self):
        # Before the fix this died inside torch BCE with an unnamed shape
        # error (or trained on a mispaired label); now the D-14 contract
        # names the caller's mistake.
        trainer = _trainer()
        with pytest.raises(ValueError, match="D-14"):
            trainer.train_step_vl(
                x_context=torch.randn(1, 10, METADATA_DIM),
                x_target=torch.randn(1, 1, METADATA_DIM),
                negatives=torch.randn(1, 5, METADATA_DIM),
                round_stats=[_round_stats()] * 10,
            )
