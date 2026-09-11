"""Smoke test for JEPA v2 training loop (Parte III §5.3).

60 steps on synthetic shards: loss decreasing, checkpoint written, resume
works, determinism (D-20), collapse abort.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest
import torch

from Programma_CS2_RENAN.backend.nn import persistence
from Programma_CS2_RENAN.backend.nn.config import set_global_seed
from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.encoder import EncoderV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.sampler import ShardIndex, WindowSampler, probe_batch
from Programma_CS2_RENAN.backend.nn.jepa_v2.telemetry import Telemetry
from Programma_CS2_RENAN.backend.nn.jepa_v2.trainer import JepaV2Trainer, cosine_lr
from Programma_CS2_RENAN.tests.jepa_v2_synth import episode_spec, write_synthetic_shard

pytestmark = pytest.mark.timeout(120)

_SMOKE_CFG = dataclasses.replace(
    JepaV2Config(),
    tokens_per_window=16,
    horizons=(1, 2, 4),
    d_model=32,
    n_heads=4,
    n_layers=2,
    served_tap=1,
    proj_hidden=32,
    proj_out=16,
    predictor_layers=1,
    sigreg_num_proj=64,
    batch_size=32,
    steps=60,
    warmup_steps=5,
    probe_every=20,
    lr_max=1e-3,
    lr_min=1e-5,
    probe_windows=64,
    abort_rankme_below=1.5,
    abort_std_min_below=1e-6,
    seed=42,
)


def _write_shard(
    path: Path,
    length: int,
    demo_id: int = 0,
) -> None:
    """Write a D-11 shard with two episodes (one per player) and varied labels."""
    write_synthetic_shard(
        path,
        [
            episode_spec(
                length // 2,
                round_number=1,
                player_idx=0,
                round_won=float(demo_id % 2),
                opening_death=float((demo_id + 1) % 2),
                side_is_ct=float(demo_id % 2),
            ),
            episode_spec(
                length - length // 2,
                round_number=2,
                player_idx=1,
                round_won=1.0 - float(demo_id % 2),
                opening_death=float(demo_id % 2),
                side_is_ct=1.0 - float(demo_id % 2),
            ),
        ],
        seed=42 + demo_id,
    )


@pytest.fixture()
def shard_dir(tmp_path: Path) -> Path:
    for split in ("train", "val"):
        d = tmp_path / split
        d.mkdir()
        for i in range(8):
            _write_shard(d / f"demo_{i:03d}.safetensors", length=600, demo_id=i)
    return tmp_path


@pytest.fixture()
def patched_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(persistence, "BASE_NN_DIR", tmp_path / "models")
    (tmp_path / "models" / "global").mkdir(parents=True)
    return tmp_path / "models"


def _build_trainer(
    shard_dir: Path,
    models_dir: Path,
    seed: int = 42,
    cfg: JepaV2Config | None = None,
) -> tuple[JepaV2Trainer, WindowSampler]:
    if cfg is None:
        cfg = dataclasses.replace(_SMOKE_CFG, seed=seed)
    set_global_seed(cfg.seed)
    device = torch.device("cpu")

    train_index = ShardIndex(shard_dir, "train")
    val_index = ShardIndex(shard_dir, "val")

    train_sampler = WindowSampler(train_index, cfg, "train", seed=cfg.seed)

    probe_x_num, probe_x_cat, probe_meta, probe_labels = probe_batch(
        val_index,
        cfg,
        n_windows=cfg.probe_windows,
        seed=cfg.seed + 1,
    )
    probe_demos = [m["demo"] for m in probe_meta]

    telemetry = Telemetry(
        cfg=cfg,
        probe_x_num=probe_x_num,
        probe_x_cat=probe_x_cat,
        probe_labels=probe_labels,
        probe_demos=probe_demos,
        writer=None,
    )

    trainer = JepaV2Trainer(
        cfg=cfg,
        device=device,
        telemetry=telemetry,
    )
    return trainer, train_sampler


class TestCosineSchedule:
    def test_warmup_linear(self) -> None:
        lr0 = cosine_lr(0, _SMOKE_CFG)
        lr_mid = cosine_lr(2, _SMOKE_CFG)
        lr_at_boundary = cosine_lr(_SMOKE_CFG.warmup_steps, _SMOKE_CFG)
        assert lr0 < lr_mid < lr_at_boundary
        assert abs(lr_at_boundary - _SMOKE_CFG.lr_max) < 1e-6

    def test_cosine_decay(self) -> None:
        lr_after_warmup = cosine_lr(_SMOKE_CFG.warmup_steps, _SMOKE_CFG)
        lr_end = cosine_lr(_SMOKE_CFG.steps - 1, _SMOKE_CFG)
        assert abs(lr_after_warmup - _SMOKE_CFG.lr_max) < 1e-6
        assert lr_end < lr_after_warmup


@pytest.mark.slow
class TestTrainingSmoke:
    def test_loss_decreasing(self, shard_dir: Path, patched_persistence: Path) -> None:
        trainer, sampler = _build_trainer(shard_dir, patched_persistence)
        data_iter = iter(sampler)

        early_losses = []
        late_losses = []
        for s in range(_SMOKE_CFG.steps):
            x_num, x_cat, _ = next(data_iter)
            info = trainer.train_step(x_num, x_cat)
            if s < 10:
                early_losses.append(info["loss"])
            if s >= _SMOKE_CFG.steps - 10:
                late_losses.append(info["loss"])

        early_mean = np.mean(early_losses)
        late_mean = np.mean(late_losses)
        assert (
            late_mean < early_mean
        ), f"Loss did not decrease: early={early_mean:.4f} late={late_mean:.4f}"

    def test_checkpoint_written(self, shard_dir: Path, patched_persistence: Path) -> None:
        trainer, sampler = _build_trainer(shard_dir, patched_persistence)
        success = trainer.run(sampler)
        assert success

        encoder_path = patched_persistence / "global" / "jepa_v2_encoder.pt"
        full_path = patched_persistence / "global" / "jepa_v2_full.pt"
        assert encoder_path.exists()
        assert full_path.exists()

    def test_best_checkpoint_not_overwritten(
        self, shard_dir: Path, patched_persistence: Path
    ) -> None:
        """Encoder checkpoint saved at best eval step, not overwritten at end."""
        trainer, sampler = _build_trainer(shard_dir, patched_persistence)
        success = trainer.run(sampler)
        assert success

        extra = trainer._read_sidecar_extra("jepa_v2_encoder")
        assert extra is not None
        encoder_step = extra["step"]
        best = max(trainer.telemetry.history, key=lambda r: r.mean_auroc)
        assert encoder_step == best.step

    def test_resume(self, shard_dir: Path, patched_persistence: Path) -> None:
        trainer1, sampler1 = _build_trainer(shard_dir, patched_persistence)
        trainer1.run(sampler1)
        assert trainer1.step == _SMOKE_CFG.steps

        trainer2, sampler2 = _build_trainer(shard_dir, patched_persistence)
        resumed = trainer2.load_full_checkpoint()
        assert resumed
        assert trainer2.step == _SMOKE_CFG.steps

    def test_determinism_d20(self, shard_dir: Path, patched_persistence: Path) -> None:
        """D-20: two runs same seed on CPU → identical weights."""

        def run_and_get_weights(seed: int = 42) -> dict:
            tr, sam = _build_trainer(shard_dir, patched_persistence, seed=seed)
            data_it = iter(sam)
            for _ in range(20):
                xn, xc, _ = next(data_it)
                tr.train_step(xn, xc)
            return {k: v.clone() for k, v in tr.encoder.state_dict().items()}

        w1 = run_and_get_weights(42)
        w2 = run_and_get_weights(42)

        for k in w1:
            assert torch.equal(w1[k], w2[k]), f"Weight mismatch at {k}"


@pytest.mark.slow
class TestCollapseAbort:
    def test_abort_on_collapse(self, shard_dir: Path, patched_persistence: Path) -> None:
        """Trigger collapse abort by injecting a constant-output encoder."""
        cfg = dataclasses.replace(
            _SMOKE_CFG,
            probe_every=5,
            steps=30,
            abort_rankme_below=100.0,
            abort_std_min_below=100.0,
        )
        trainer, sampler = _build_trainer(shard_dir, patched_persistence, cfg=cfg)
        success = trainer.run(sampler)
        assert not success


class TestFactoryIntegration:
    def test_jepa_v2_type_constant(self) -> None:
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        assert ModelFactory.TYPE_JEPA_V2 == "jepa_v2"

    def test_jepa_v2_checkpoint_name(self) -> None:
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        assert ModelFactory.get_checkpoint_name("jepa_v2") == "jepa_v2_encoder"

    def test_jepa_v2_model_instance(self) -> None:
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("jepa_v2")
        assert isinstance(model, EncoderV2)
