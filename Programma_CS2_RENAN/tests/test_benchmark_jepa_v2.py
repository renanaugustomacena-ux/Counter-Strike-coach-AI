"""Tests for tools/benchmark_jepa_v2_vs_legacy.py.

Synthetic shards on CPU, small config. Validates:
  - end-to-end run completes and produces report+JSON
  - verdict logic on injected numbers
  - same windows shared across contenders (structural)
  - missing legacy checkpoint handled gracefully
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.encoder import EncoderV2
from Programma_CS2_RENAN.tests.jepa_v2_synth import episode_spec, write_synthetic_shard
from tools.benchmark_jepa_v2_vs_legacy import (
    _encode_raw,
    _encode_v2,
    compute_verdict,
    draw_windows,
    run_benchmark,
)

pytestmark = pytest.mark.timeout(30)

_SMALL_CFG = dataclasses.replace(
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
    rng: np.random.Generator,
    with_labels: bool = True,
) -> None:
    """Write a D-11 shard with three episodes and random round outcomes."""
    write_synthetic_shard(
        path,
        [
            episode_spec(
                length,
                round_number=r + 1,
                player_idx=r % 2,
                round_won=float(rng.random() > 0.5),
                opening_death=float(rng.random() > 0.8),
                side_is_ct=float(r % 2),
                enemies_from=int(rng.integers(0, length)) if rng.random() > 0.5 else None,
            )
            for r in range(3)
        ],
        seed=int(rng.integers(0, 1_000_000)),
        with_labels=with_labels,
    )


@pytest.fixture()
def shard_dir(tmp_path: Path) -> Path:
    """Create shards for val split with enough demos for GroupKFold(5)."""
    rng = np.random.default_rng(123)
    d = tmp_path / "val"
    d.mkdir()
    for i in range(10):
        _write_shard(d / f"demo_{i:03d}.safetensors", length=600, rng=rng)
    return tmp_path


@pytest.fixture()
def saved_checkpoint(tmp_path: Path) -> Path:
    """Save a small EncoderV2 checkpoint."""
    model = EncoderV2(_SMALL_CFG)
    ckpt_path = tmp_path / "encoder.pt"
    torch.save(model.state_dict(), ckpt_path)
    return ckpt_path


class TestVerdict:
    """Verdict logic on injected numbers — no data, no torch."""

    def test_pass_all_criteria(self) -> None:
        passed, reasons = compute_verdict(
            b_aurocs={"round_won": 0.85, "death_within_2s": 0.90},
            r_aurocs={"round_won": 0.76, "death_within_2s": 0.84},
            rankme_b=80.0,
        )
        assert passed is True
        assert reasons == []

    def test_fail_round_won_below_threshold(self) -> None:
        passed, reasons = compute_verdict(
            b_aurocs={"round_won": 0.75, "death_within_2s": 0.90},
            r_aurocs={"round_won": 0.70, "death_within_2s": 0.80},
            rankme_b=80.0,
        )
        assert passed is False
        assert any("0.760" in r for r in reasons)

    def test_fail_round_won_below_raw(self) -> None:
        passed, reasons = compute_verdict(
            b_aurocs={"round_won": 0.77, "death_within_2s": 0.90},
            r_aurocs={"round_won": 0.78, "death_within_2s": 0.80},
            rankme_b=80.0,
        )
        assert passed is False
        assert any("AUROC_R(round_won)" in r for r in reasons)

    def test_fail_death_below_threshold(self) -> None:
        passed, reasons = compute_verdict(
            b_aurocs={"round_won": 0.85, "death_within_2s": 0.83},
            r_aurocs={"round_won": 0.76, "death_within_2s": 0.80},
            rankme_b=80.0,
        )
        assert passed is False
        assert any("0.838" in r for r in reasons)

    def test_fail_death_below_raw(self) -> None:
        passed, reasons = compute_verdict(
            b_aurocs={"round_won": 0.85, "death_within_2s": 0.85},
            r_aurocs={"round_won": 0.76, "death_within_2s": 0.86},
            rankme_b=80.0,
        )
        assert passed is False
        assert any("AUROC_R_lasttick" in r for r in reasons)

    def test_fail_rankme(self) -> None:
        passed, reasons = compute_verdict(
            b_aurocs={"round_won": 0.85, "death_within_2s": 0.90},
            r_aurocs={"round_won": 0.76, "death_within_2s": 0.80},
            rankme_b=50.0,
        )
        assert passed is False
        assert any("RankMe" in r for r in reasons)


class TestSameWindows:
    """Contenders share the exact same windows (structural guarantee)."""

    def test_draw_once_encode_twice(self, shard_dir: Path) -> None:
        ws = draw_windows(str(shard_dir), _SMALL_CFG, seed=42, n_windows=32)
        reps_r = _encode_raw(ws)
        model = EncoderV2(_SMALL_CFG)
        model.eval()
        reps_b = _encode_v2(model, ws, torch.device("cpu"))

        assert reps_r["r_mean"].shape[0] == reps_b["b_mean"].shape[0] == ws.n
        assert reps_r["r_mean"].shape[0] == 32


class TestMissingLegacy:
    """Graceful skip when legacy checkpoint is absent."""

    def test_no_crash_missing_legacy(
        self,
        shard_dir: Path,
        saved_checkpoint: Path,
        tmp_path: Path,
    ) -> None:
        out_md = str(tmp_path / "report.md")
        out_json = str(tmp_path / "report.json")
        passed, report = run_benchmark(
            data_dir=str(shard_dir),
            checkpoint_path=str(saved_checkpoint),
            out_path=out_md,
            cfg=_SMALL_CFG,
            legacy_checkpoint=str(tmp_path / "nonexistent.pt"),
            json_path=out_json,
            n_windows=32,
            seeds=(0,),
            device_str="cpu",
        )
        assert Path(out_md).exists()
        assert Path(out_json).exists()
        data = json.loads(Path(out_json).read_text())
        assert "A_mean" not in data["contenders"]


@pytest.mark.slow
@pytest.mark.timeout(120)
class TestEndToEnd:
    """Full benchmark run on synthetic data, CPU, one seed."""

    def test_run_produces_report_and_json(
        self,
        shard_dir: Path,
        saved_checkpoint: Path,
        tmp_path: Path,
    ) -> None:
        out_md = str(tmp_path / "out" / "report.md")
        out_json = str(tmp_path / "out" / "report.json")
        passed, report = run_benchmark(
            data_dir=str(shard_dir),
            checkpoint_path=str(saved_checkpoint),
            out_path=out_md,
            cfg=_SMALL_CFG,
            legacy_checkpoint=None,
            json_path=out_json,
            n_windows=64,
            seeds=(0,),
            device_str="cpu",
        )
        assert Path(out_md).exists()
        assert "Verdict" in report

        assert Path(out_json).exists()
        data = json.loads(Path(out_json).read_text())
        assert data["verdict"] in ("PASS", "FAIL")
        assert "B_mean" in data["contenders"]
        assert "R_mean" in data["contenders"]
        assert "R_last" in data["contenders"]

        for cname in ("B_mean", "R_mean"):
            seed_data = data["contenders"][cname]["0"]
            assert "rankme" in seed_data
            assert seed_data["rankme"] > 0
            assert "probes" in seed_data
            assert "round_won" in seed_data["probes"]


class TestLegacyBridgeAlignment:
    """D-39: the 21→25-d bridge for contender A must respect the v1 slot order.

    v2 numerics are v1 slots ``[0..15, 20..24]`` (schema_v2.py); the four
    retired slots 16-19 (kast_estimate, map_id, round_phase, weapon_class)
    sit in the MIDDLE.  Padding four zeros at the END fed time_in_round /
    bomb_planted / teammates_alive / enemies_alive into the legacy encoder's
    slots 16-19 and team_economy into slot 20 — contender A was garbage,
    not "approximate".
    """

    def test_bridge_round_trips_through_remap_v1_to_v2(self) -> None:
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            remap_v1_to_v2,
        )
        from tools.benchmark_jepa_v2_vs_legacy import _bridge_v2_to_v1

        x21 = torch.randn(3, 5, 21)
        x25 = _bridge_v2_to_v1(x21)
        assert x25.shape == (3, 5, 25)
        assert torch.equal(x25[..., 16:20], torch.zeros(3, 5, 4))
        for b in range(3):
            for t in range(5):
                num, _cat = remap_v1_to_v2(x25[b, t].numpy(), None, None, None)
                assert np.allclose(num, x21[b, t].numpy())
