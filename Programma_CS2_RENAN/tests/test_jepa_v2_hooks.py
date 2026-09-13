"""Train-in-app round (WP4b) — optional progress/stop hooks on the jepa_v2
trainer and CLI.  No-ops by default: training semantics are unchanged.
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest
import torch

from Programma_CS2_RENAN.backend.nn import persistence
from Programma_CS2_RENAN.backend.nn.jepa_v2.sampler import ShardIndex, WindowSampler
from Programma_CS2_RENAN.backend.nn.jepa_v2.trainer import JepaV2Trainer
from Programma_CS2_RENAN.tests.jepa_v2_synth import TINY_CONFIG_OVERRIDES
from Programma_CS2_RENAN.tests.test_jepa_v2_training_smoke import (  # noqa: F401
    _SMOKE_CFG,
    shard_dir,
)

pytestmark = pytest.mark.timeout(120)


def _sampler(root):
    return WindowSampler(ShardIndex(root, "train"), _SMOKE_CFG, "train", seed=42)


def test_progress_hook_sees_every_step(shard_dir):
    cfg = dataclasses.replace(_SMOKE_CFG, steps=6, probe_every=0)
    seen: list[tuple[int, int, float]] = []
    trainer = JepaV2Trainer(
        cfg=cfg,
        device=torch.device("cpu"),
        dry_run=True,
        progress_cb=lambda step, total, info: seen.append((step, total, float(info["loss"]))),
    )

    assert trainer.run(_sampler(shard_dir)) is True

    assert [step for step, _, _ in seen] == [1, 2, 3, 4, 5, 6]
    assert {total for _, total, _ in seen} == {6}


def test_stop_hook_ends_the_run_early_with_a_resumable_checkpoint(shard_dir):
    cfg = dataclasses.replace(_SMOKE_CFG, steps=50, probe_every=0)
    holder: dict = {}
    trainer = JepaV2Trainer(
        cfg=cfg,
        device=torch.device("cpu"),
        stop_cb=lambda: holder["trainer"].step >= 3,
    )
    holder["trainer"] = trainer

    assert trainer.run(_sampler(shard_dir)) is False

    assert trainer.step == 3
    # a soft stop parks the run at a safe checkpoint so the next run resumes
    assert persistence.get_model_path("jepa_v2_full").exists()


def test_run_jepa_v2_forwards_hooks_overrides_and_reports(shard_dir):
    from Programma_CS2_RENAN.backend.nn.jepa_v2.cli import run_jepa_v2

    seen: list[int] = []
    sink: dict = {}
    args = SimpleNamespace(
        data_dir=str(shard_dir),
        steps=4,
        probe_every=None,
        no_tensorboard=True,
        dry_run=True,
        no_resume=True,
        seed=42,
        config_overrides=dict(TINY_CONFIG_OVERRIDES),
        progress_cb=lambda step, total, info: seen.append(step),
        stop_cb=None,
        result_sink=sink,
    )

    assert run_jepa_v2(args) is True

    assert seen == [1, 2, 3, 4]
    assert sink["steps"] == 4
    assert sink["device"] == "cpu"
    assert sink["stopped"] is False
    assert sink["d_model"] == 32
