"""Tests for jepa_v2.sampler: multi-episode shards, window slicing, D-17 labels."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest
import torch

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.sampler import (
    LABEL_HORIZON_TICKS,
    PROBE_LABEL_NAMES,
    ShardIndex,
    WindowSampler,
    _derive_d17_labels,
    probe_batch,
)
from Programma_CS2_RENAN.tests.jepa_v2_synth import episode_spec, write_synthetic_shard

_CFG = JepaV2Config(
    patch_ticks=8,
    tokens_per_window=16,  # 128-tick windows keep the fixtures small
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
    probe_windows=64,
)
WT = _CFG.window_ticks  # 128


@pytest.fixture()
def shard_dir(tmp_path: Path) -> Path:
    """6 shards per split, 3 episodes each (two players), lengths 600/400/150."""
    for split in ("train", "val"):
        d = tmp_path / split
        d.mkdir()
        for i in range(6):
            write_synthetic_shard(
                d / f"demo_{i:03d}.safetensors",
                [
                    episode_spec(600, round_number=1, player_idx=0, round_won=float(i % 2)),
                    episode_spec(400, round_number=2, player_idx=0, round_won=float((i + 1) % 2)),
                    episode_spec(150, round_number=1, player_idx=1, side_is_ct=0.0),
                ],
                seed=i,
            )
    return tmp_path


class TestShardIndex:
    def test_lists_every_episode(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        assert len(idx.paths) == 6
        assert len(idx.episodes) == 18
        first = [e for e in idx.episodes if e.shard_idx == 0]
        assert [e.length for e in first] == [600, 400, 150]
        assert [e.start for e in first] == [0, 600, 1000]
        assert [e.round_number for e in first] == [1, 2, 1]
        assert [e.player_idx for e in first] == [0, 0, 1]

    def test_no_shards_raises(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        with pytest.raises(FileNotFoundError):
            ShardIndex(tmp_path, "empty")

    def test_missing_offsets_rejected(self, tmp_path: Path) -> None:
        from safetensors.torch import save_file

        d = tmp_path / "train"
        d.mkdir()
        save_file(
            {"x_num": torch.zeros(10, 21), "x_cat": torch.zeros(10, 3)}, str(d / "a.safetensors")
        )
        with pytest.raises(ValueError, match="episode_offsets"):
            ShardIndex(tmp_path, "train")

    def test_load_episode_returns_shard_tensors(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        data = idx.load_episode(idx.episodes[0])
        assert data["x_num"].shape == (1150, 21)
        assert data["labels_round"].shape == (3, 8)
        assert idx.load_episode(idx.episodes[1]) is data  # same shard, cached


class TestWindowSampler:
    def test_window_shapes(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        x_num, x_cat, meta = next(iter(WindowSampler(idx, _CFG, "train", seed=0)))
        assert x_num.shape == (_CFG.batch_size, WT, 21)
        assert x_cat.shape == (_CFG.batch_size, WT, 3)
        assert len(meta) == _CFG.batch_size

    def test_windows_never_cross_an_episode(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        lookup = idx.episode_lookup()
        for _, (x_num, _, meta) in zip(range(3), iter(WindowSampler(idx, _CFG, "train", seed=0))):
            for i, m in enumerate(meta):
                ep = lookup[(m["shard_idx"], m["ep_idx"])]
                assert 0 <= m["offset"] <= ep.length - WT
                lo = ep.start + m["offset"]
                expected = idx.load_episode(ep)["x_num"][lo : lo + WT]
                assert torch.equal(x_num[i], expected)

    def test_short_episodes_skipped(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        cfg = dataclasses.replace(
            _CFG, tokens_per_window=32
        )  # 256 ticks: the 150-tick episodes drop
        sampler = WindowSampler(idx, cfg, "train", seed=0)
        assert len(sampler.valid_episodes) == 12
        assert sampler.skipped_short == 6

    def test_determinism_per_seed(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        x1, _, m1 = next(iter(WindowSampler(idx, _CFG, "train", seed=99)))
        x2, _, m2 = next(iter(WindowSampler(idx, _CFG, "train", seed=99)))
        x3, _, _ = next(iter(WindowSampler(idx, _CFG, "train", seed=7)))
        assert torch.equal(x1, x2) and m1 == m2
        assert not torch.equal(x1, x3)

    def test_fixed_offsets_stable_across_epochs(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "train")
        cfg = dataclasses.replace(_CFG, batch_size=18)
        it = iter(WindowSampler(idx, cfg, "val", seed=0, fixed_offsets=True))
        x1, _, m1 = next(it)
        x2, _, m2 = next(it)  # second epoch
        assert m1 == m2 and torch.equal(x1, x2)


class TestLabelDerivation:
    def _single(self, tmp_path: Path, spec: dict) -> tuple:
        d = tmp_path / "val"
        d.mkdir(exist_ok=True)
        write_synthetic_shard(d / "ep.safetensors", [episode_spec(80, player_idx=1), spec])
        idx = ShardIndex(tmp_path, "val")
        ep = idx.episodes[1]  # the second episode: offsets must be honoured
        return idx.load_episode(ep), ep

    def test_death_within_horizon(self, tmp_path: Path) -> None:
        data, ep = self._single(tmp_path, episode_spec(WT + 300, death_at=WT + 50))
        labels = _derive_d17_labels(data, ep, 0, WT)
        assert labels["death_within_2s"] == 1.0

    def test_death_beyond_horizon(self, tmp_path: Path) -> None:
        data, ep = self._single(
            tmp_path, episode_spec(WT + 400, death_at=WT + LABEL_HORIZON_TICKS + 10)
        )
        assert _derive_d17_labels(data, ep, 0, WT)["death_within_2s"] == 0.0

    def test_dead_at_window_end_is_undefined(self, tmp_path: Path) -> None:
        data, ep = self._single(tmp_path, episode_spec(WT + 100, death_at=WT + 20))
        offset = ep.length - WT  # the window ends on the death tick
        assert _derive_d17_labels(data, ep, offset, WT)["death_within_2s"] is None

    def test_contact_new(self, tmp_path: Path) -> None:
        data, ep = self._single(tmp_path, episode_spec(WT + 300, enemies_from=WT + 30))
        labels = _derive_d17_labels(data, ep, 0, WT)
        assert labels["contact_new_within_2s"] == 1.0
        assert labels["enemy_visible_any_within_2s"] == 1.0
        later = _derive_d17_labels(data, ep, 60, WT)  # enemies already visible at the last tick
        assert later["contact_new_within_2s"] is None
        assert later["enemy_visible_any_within_2s"] == 1.0

    def test_round_labels_come_from_the_episode_row(self, tmp_path: Path) -> None:
        data, ep = self._single(
            tmp_path, episode_spec(WT + 50, round_won=0.0, opening_death=1.0, side_is_ct=0.0)
        )
        labels = _derive_d17_labels(data, ep, 0, WT)
        assert labels["round_won"] == 0.0
        assert labels["opening_death"] == 1.0
        assert labels["side"] == 0.0

    def test_masked_round_label_is_none(self, tmp_path: Path) -> None:
        data, ep = self._single(tmp_path, episode_spec(WT + 50, round_won=None))
        assert _derive_d17_labels(data, ep, 0, WT)["round_won"] is None


class TestProbeBatch:
    def test_shapes_and_label_keys(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "val")
        x_num, x_cat, meta, labels = probe_batch(idx, _CFG, n_windows=16)
        assert x_num.shape == (16, WT, 21) and x_cat.shape == (16, WT, 3)
        assert len(meta) == 16 and {"demo", "ep_idx", "offset"} <= set(meta[0])
        for name in PROBE_LABEL_NAMES:
            assert labels[name].shape == (16,)
        assert set(np.unique(labels["round_won"][~np.isnan(labels["round_won"])])) <= {0.0, 1.0}
        assert np.all(labels["death_within_2s"][~np.isnan(labels["death_within_2s"])] == 0.0)

    def test_deterministic(self, shard_dir: Path) -> None:
        idx = ShardIndex(shard_dir, "val")
        a = probe_batch(idx, _CFG, n_windows=8, seed=3)
        b = probe_batch(idx, _CFG, n_windows=8, seed=3)
        assert torch.equal(a[0], b[0]) and a[2] == b[2]
