"""Tests for JEPA v2 sampler: window shapes, determinism, episode boundary,
short episode skipping, and D-17 label derivation (Parte III §5.2).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest
import torch
from safetensors.torch import save_file

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.sampler import (
    LABEL_HORIZON_TICKS,
    ShardIndex,
    WindowSampler,
    _derive_d17_labels,
    probe_batch,
)

pytestmark = pytest.mark.timeout(30)

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
)


def _write_shard(
    path: Path,
    length: int,
    with_labels: bool = True,
    death_at: int | None = None,
    enemies_visible_at: int | None = None,
    round_won: float = 1.0,
) -> None:
    """Write a synthetic safetensors shard."""
    rng = np.random.default_rng(42)
    x_num = torch.from_numpy(rng.standard_normal((length, 21)).astype(np.float32))
    x_num[:, 0] = 100.0
    if death_at is not None and death_at < length:
        x_num[death_at, 0] = 0.0

    x_num[:, 8] = 0.0
    if enemies_visible_at is not None and enemies_visible_at < length:
        x_num[enemies_visible_at, 8] = 1.0

    x_cat = torch.zeros(length, 3, dtype=torch.int64)

    tensors = {"x_num": x_num, "x_cat": x_cat}

    if with_labels:
        labels_round = torch.zeros(length, 3)
        labels_round[:, 0] = round_won
        labels_mask = torch.ones(length)
        tensors["labels_round"] = labels_round
        tensors["labels_mask"] = labels_mask

    save_file(tensors, str(path))


@pytest.fixture()
def shard_dir(tmp_path: Path) -> Path:
    """Create a temporary shard directory with train/val splits."""
    for split in ("train", "val"):
        d = tmp_path / split
        d.mkdir()
        for i in range(6):
            _write_shard(d / f"demo_{i:03d}.safetensors", length=600, round_won=float(i % 2))
    return tmp_path


@pytest.fixture()
def short_shard_dir(tmp_path: Path) -> Path:
    """Shards where some episodes are too short."""
    d = tmp_path / "train"
    d.mkdir()
    _write_shard(d / "short.safetensors", length=10)
    _write_shard(d / "long.safetensors", length=600)
    return tmp_path


class TestShardIndex:
    def test_lists_shards(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        assert len(idx.episodes) == 6
        assert all(e.length == 600 for e in idx.episodes)

    def test_no_shards_raises(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        with pytest.raises(FileNotFoundError):
            ShardIndex(tmp_path, "empty")

    def test_load_episode(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        data = idx.load_episode(idx.episodes[0])
        assert "x_num" in data
        assert data["x_num"].shape == (600, 21)
        assert data["x_cat"].shape == (600, 3)


class TestWindowSampler:
    def test_window_shapes(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        sampler = WindowSampler(idx, _SMOKE_CFG, "train", seed=0)
        x_num, x_cat, meta = next(iter(sampler))
        assert x_num.shape == (_SMOKE_CFG.batch_size, _SMOKE_CFG.window_ticks, 21)
        assert x_cat.shape == (_SMOKE_CFG.batch_size, _SMOKE_CFG.window_ticks, 3)
        assert len(meta) == _SMOKE_CFG.batch_size

    def test_determinism(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        s1 = WindowSampler(idx, _SMOKE_CFG, "train", seed=99)
        s2 = WindowSampler(idx, _SMOKE_CFG, "train", seed=99)
        x1, _, _ = next(iter(s1))
        x2, _, _ = next(iter(s2))
        assert torch.equal(x1, x2)

    def test_different_seeds(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        s1 = WindowSampler(idx, _SMOKE_CFG, "train", seed=1)
        s2 = WindowSampler(idx, _SMOKE_CFG, "train", seed=2)
        x1, _, _ = next(iter(s1))
        x2, _, _ = next(iter(s2))
        assert not torch.equal(x1, x2)

    def test_episode_boundary_respect(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        sampler = WindowSampler(idx, _SMOKE_CFG, "train", seed=0)
        _, _, meta = next(iter(sampler))
        for m in meta:
            ep = idx.episodes[m["shard_idx"]]
            assert m["offset"] + _SMOKE_CFG.window_ticks <= ep.length

    def test_short_episode_skipping(self, short_shard_dir: Path) -> None:
        idx = ShardIndex(short_shard_dir, "train")
        cfg = dataclasses.replace(_SMOKE_CFG, batch_size=32)
        sampler = WindowSampler(idx, cfg, "train", seed=0)
        assert len(sampler.valid_episodes) == 1
        assert sampler.valid_episodes[0].demo_name == "long"

    def test_fixed_offsets(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        sampler = WindowSampler(idx, _SMOKE_CFG, "train", seed=0, fixed_offsets=True)
        _, _, meta = next(iter(sampler))
        for m in meta:
            assert m["offset"] == 0


class TestLabelDerivation:
    def test_death_within_2s(self, tmp_path: Path) -> None:
        d = tmp_path / "val"
        d.mkdir()
        wt = _SMOKE_CFG.window_ticks
        ep_len = wt + 200
        _write_shard(d / "ep.safetensors", length=ep_len, death_at=wt + 50)

        idx = ShardIndex(tmp_path, "val")
        data = idx.load_episode(idx.episodes[0])
        labels = _derive_d17_labels(data, 0, wt)
        assert labels["death_within_2s"] == 1.0

    def test_no_death_beyond_horizon(self, tmp_path: Path) -> None:
        d = tmp_path / "val"
        d.mkdir()
        wt = _SMOKE_CFG.window_ticks
        ep_len = wt + 200
        _write_shard(d / "ep.safetensors", length=ep_len, death_at=wt + LABEL_HORIZON_TICKS + 10)

        idx = ShardIndex(tmp_path, "val")
        data = idx.load_episode(idx.episodes[0])
        labels = _derive_d17_labels(data, 0, wt)
        assert labels["death_within_2s"] == 0.0

    def test_contact_new_within_2s(self, tmp_path: Path) -> None:
        d = tmp_path / "val"
        d.mkdir()
        wt = _SMOKE_CFG.window_ticks
        ep_len = wt + 200
        _write_shard(d / "ep.safetensors", length=ep_len, enemies_visible_at=wt + 30)

        idx = ShardIndex(tmp_path, "val")
        data = idx.load_episode(idx.episodes[0])
        labels = _derive_d17_labels(data, 0, wt)
        assert labels["contact_new_within_2s"] == 1.0

    def test_round_labels(self, tmp_path: Path) -> None:
        d = tmp_path / "val"
        d.mkdir()
        _write_shard(d / "ep.safetensors", length=600, round_won=1.0)
        idx = ShardIndex(tmp_path, "val")
        data = idx.load_episode(idx.episodes[0])
        labels = _derive_d17_labels(data, 0, _SMOKE_CFG.window_ticks)
        assert labels["round_won"] == 1.0


class TestProbeBatch:
    def test_probe_batch_shapes(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "val")
        n = 16
        x_num, x_cat, meta, labels = probe_batch(idx, _SMOKE_CFG, n_windows=n)
        assert x_num.shape == (n, _SMOKE_CFG.window_ticks, 21)
        assert x_cat.shape == (n, _SMOKE_CFG.window_ticks, 3)
        assert len(meta) == n
        for name in ("round_won", "death_within_2s", "contact_new_within_2s"):
            assert name in labels
            assert labels[name].shape == (n,)
