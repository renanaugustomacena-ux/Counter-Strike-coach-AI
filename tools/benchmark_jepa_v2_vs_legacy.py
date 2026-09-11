#!/usr/bin/env python3
"""Benchmark jepa_v2 encoder vs raw features and legacy JEPAEncoder.

Computes frozen-encoder metrics on the same windows for three contenders:
  B = EncoderV2 (mean-pooled 128-d served representation)
  R = raw numeric features (21-d, window-mean and last-tick variants)
  A = legacy JEPAEncoder from archived JEPACoachingModel (256-d, optional)

Verdict per CORREZIONE_NUCLEO_NEURALE Parte III §5.3 (D-18):
  PASS iff AUROC_B(round_won) > AUROC_R(round_won) AND > 0.760
             AND AUROC_B(death_within_2s) > AUROC_R_lasttick AND > 0.838
             AND RankMe_B >= 64
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from numpy.typing import NDArray

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.encoder import EncoderV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.probes import (
    GroupProbeResult,
    delta_pos_r2,
    group_kfold_probe,
    knn_accuracy,
    rankme,
)
from Programma_CS2_RENAN.backend.nn.jepa_v2.sampler import ShardIndex, probe_batch

log = logging.getLogger(__name__)

PROBE_LABELS: Tuple[str, ...] = (
    "round_won",
    "death_within_2s",
    "contact_new_within_2s",
    "opening_death",
    "side",
)
AUROC_THRESHOLD_ROUND_WON: float = 0.760
AUROC_THRESHOLD_DEATH: float = 0.838
RANKME_THRESHOLD: float = 64.0

_POS_COLS: Tuple[int, ...] = (9, 10, 11)
_ENCODE_CHUNK: int = 256

_DEFAULT_LEGACY_PATH = (
    "Programma_CS2_RENAN/models/global/" "archive_pre_rebuild_2026-09-01/jepa_brain.pt"
)


# ── data drawing ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class WindowSet:
    """Fixed windows drawn once, shared by all contenders."""

    x_num: torch.Tensor
    x_cat: torch.Tensor
    meta: List[dict]
    labels: Dict[str, NDArray[np.float64]]
    groups: NDArray
    n: int


def draw_windows(
    data_dir: str,
    cfg: JepaV2Config,
    seed: int,
    n_windows: int,
    split: str = "val",
) -> WindowSet:
    """Draw ``n_windows`` from ``split`` with ``probe_batch``."""
    idx = ShardIndex(data_dir, split)
    x_num, x_cat, meta, labels = probe_batch(idx, cfg, n_windows=n_windows, seed=seed)
    groups = np.array([m["demo"] for m in meta])
    return WindowSet(
        x_num=x_num,
        x_cat=x_cat,
        meta=meta,
        labels=labels,
        groups=groups,
        n=x_num.shape[0],
    )


# ── contender representations ────────────────────────────────────────


def _encode_v2(
    model: EncoderV2,
    ws: WindowSet,
    device: torch.device,
) -> Dict[str, NDArray[np.float64]]:
    """Contender B: mean-pooled and last-token from EncoderV2."""
    model.eval()
    all_mean: List[NDArray] = []
    all_last: List[NDArray] = []
    n = ws.x_num.shape[0]
    with torch.no_grad():
        for i in range(0, n, _ENCODE_CHUNK):
            xn = ws.x_num[i : i + _ENCODE_CHUNK].to(device)
            xc = ws.x_cat[i : i + _ENCODE_CHUNK].to(device)
            z = model(xn, xc)
            all_mean.append(z.mean(dim=1).cpu().numpy())
            all_last.append(z[:, -1, :].cpu().numpy())
    return {
        "b_mean": np.concatenate(all_mean, axis=0).astype(np.float64),
        "b_last": np.concatenate(all_last, axis=0).astype(np.float64),
    }


def _encode_raw(ws: WindowSet) -> Dict[str, NDArray[np.float64]]:
    """Contender R: raw 21-d window-mean and last-tick."""
    x = ws.x_num.numpy()
    return {
        "r_mean": x.mean(axis=1).astype(np.float64),
        "r_last": x[:, -1, :].astype(np.float64),
    }


def _load_legacy_encoder(
    path: str,
    device: torch.device,
) -> Optional[torch.nn.Module]:
    """Load archived JEPAEncoder from JEPACoachingModel checkpoint."""
    from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel

    p = Path(path)
    if not p.exists():
        log.warning("Legacy checkpoint not found at %s — skipping contender A.", path)
        return None
    try:
        arch = JEPACoachingModel(input_dim=25, output_dim=10)
        sd = torch.load(str(p), map_location="cpu", weights_only=True)
        arch.load_state_dict(sd, strict=True)
        arch.eval()
        return arch.context_encoder.to(device)
    except Exception as exc:
        log.warning("Cannot load legacy checkpoint: %s — skipping contender A.", exc)
        return None


def _encode_legacy(
    encoder: torch.nn.Module,
    ws: WindowSet,
    device: torch.device,
) -> Dict[str, NDArray[np.float64]]:
    """Contender A: legacy 256-d mean over ticks (approximate, informational).

    Legacy JEPAEncoder expects 25-d input. The v2 schema has 21 numeric
    features. This bridge is approximate: the four missing v1 slots
    (kast_estimate, map_id, round_phase, weapon_class) are filled with
    zeros. D-18 verdict does NOT depend on contender A (Parte III §5.3).
    """
    encoder.eval()
    x = ws.x_num
    pad = torch.zeros(x.shape[0], x.shape[1], 4, dtype=x.dtype)
    x25 = torch.cat([x, pad], dim=2)
    all_mean: List[NDArray] = []
    n = x25.shape[0]
    with torch.no_grad():
        for i in range(0, n, _ENCODE_CHUNK):
            chunk = x25[i : i + _ENCODE_CHUNK].to(device)
            z = encoder(chunk)
            all_mean.append(z.mean(dim=1).cpu().numpy())
    return {
        "a_mean": np.concatenate(all_mean, axis=0).astype(np.float64),
    }


# ── Δpos target ──────────────────────────────────────────────────────


def _build_delta_pos_target(
    ws: WindowSet,
    horizon_ticks: int,
    data_dir: str,
    split: str,
    cfg: JepaV2Config,
) -> Tuple[Optional[NDArray[np.float64]], Optional[NDArray[np.bool_]]]:
    """Build Δpos target from shards: position at (end + horizon) − position at end.

    Returns (delta_pos [N,3], valid_mask [N]) or (None, None) if unavailable.
    """
    try:
        idx = ShardIndex(data_dir, split)
    except (FileNotFoundError, ValueError):
        return None, None

    lookup = idx.episode_lookup()
    n = ws.n
    delta = np.full((n, 3), np.nan, dtype=np.float64)
    valid = np.zeros(n, dtype=bool)
    wt = cfg.window_ticks

    for i, m in enumerate(ws.meta):
        ep = lookup.get((m["shard_idx"], m["ep_idx"]))
        if ep is None:
            continue
        end_tick = m["offset"] + wt  # relative to the episode start
        future_tick = end_tick + horizon_ticks
        if future_tick >= ep.length:
            continue  # the future position must lie inside the same episode
        x_num = idx.load_episode(ep)["x_num"]
        pos_end = x_num[ep.start + end_tick - 1, list(_POS_COLS)].numpy().astype(np.float64)
        pos_future = x_num[ep.start + future_tick, list(_POS_COLS)].numpy().astype(np.float64)
        delta[i] = pos_future - pos_end
        valid[i] = True

    if valid.sum() < 20:
        return None, None
    return delta, valid


# ── metrics computation ──────────────────────────────────────────────


def _nan_safe_mask(y: NDArray) -> NDArray[np.bool_]:
    return np.isfinite(y)


@dataclass
class ContenderMetrics:
    """All metrics for one contender on one seed."""

    probe_results: Dict[str, Optional[GroupProbeResult]]
    rankme_val: float
    knn_acc: Optional[float]
    dpos_r2_05s: Optional[float]
    dpos_r2_2s: Optional[float]


def compute_metrics_for_contender(
    name: str,
    z: NDArray[np.float64],
    ws: WindowSet,
    data_dir: str,
    split: str,
    cfg: JepaV2Config,
    seed: int,
) -> ContenderMetrics:
    """Run full metric suite on one representation."""
    groups = ws.groups
    probe_results: Dict[str, Optional[GroupProbeResult]] = {}

    for label_name in PROBE_LABELS:
        y = ws.labels.get(label_name)
        if y is None:
            probe_results[label_name] = None
            continue
        mask = _nan_safe_mask(y)
        if mask.sum() < 20:
            probe_results[label_name] = None
            continue
        z_m, y_m, g_m = z[mask], y[mask], groups[mask]
        n_classes = len(np.unique(y_m[np.isfinite(y_m)]))
        if n_classes < 2:
            probe_results[label_name] = None
            continue
        probe_results[label_name] = group_kfold_probe(z_m, y_m, g_m, seed=seed)

    rm = rankme(z)

    knn = None
    y_rw = ws.labels.get("round_won")
    if y_rw is not None:
        mask = _nan_safe_mask(y_rw)
        if mask.sum() >= 40:
            z_m, y_m = z[mask], y_rw[mask]
            n_tr = int(len(z_m) * 0.8)
            knn = knn_accuracy(z_m[:n_tr], y_m[:n_tr], z_m[n_tr:], y_m[n_tr:])

    dpos_05: Optional[float] = None
    dpos_2: Optional[float] = None

    for horizon_ticks, attr in [(32, "dpos_05"), (128, "dpos_2")]:
        dp, valid = _build_delta_pos_target(ws, horizon_ticks, data_dir, split, cfg)
        if dp is not None and valid is not None:
            z_v, dp_v, g_v = z[valid], dp[valid], groups[valid]
            r2 = delta_pos_r2(z_v, dp_v, g_v, seed=seed)
            if attr == "dpos_05":
                dpos_05 = r2
            else:
                dpos_2 = r2

    return ContenderMetrics(
        probe_results=probe_results,
        rankme_val=rm,
        knn_acc=knn,
        dpos_r2_05s=dpos_05,
        dpos_r2_2s=dpos_2,
    )


# ── verdict ──────────────────────────────────────────────────────────


def compute_verdict(
    b_aurocs: Dict[str, float],
    r_aurocs: Dict[str, float],
    rankme_b: float,
) -> Tuple[bool, List[str]]:
    """Verdict per D-18 (Parte III §5.3).

    Args:
        b_aurocs: mean AUROC over seeds for contender B (keyed by label).
        r_aurocs: mean AUROC over seeds for contender R (keyed by label).
            Expects ``round_won`` for R_windowmean, ``death_within_2s``
            for R_lasttick.
        rankme_b: mean RankMe over seeds for contender B (mean-pooled).

    Returns:
        (passed, reasons) — reasons list is non-empty on failure.
    """
    reasons: List[str] = []

    auroc_b_rw = b_aurocs.get("round_won", 0.0)
    auroc_r_rw = r_aurocs.get("round_won", 0.0)
    if auroc_b_rw <= auroc_r_rw:
        reasons.append(
            f"AUROC_B(round_won) {auroc_b_rw:.4f} <= AUROC_R(round_won) {auroc_r_rw:.4f}"
        )
    if auroc_b_rw <= AUROC_THRESHOLD_ROUND_WON:
        reasons.append(
            f"AUROC_B(round_won) {auroc_b_rw:.4f} <= threshold {AUROC_THRESHOLD_ROUND_WON:.3f}"
        )

    auroc_b_dw = b_aurocs.get("death_within_2s", 0.0)
    auroc_r_dw = r_aurocs.get("death_within_2s", 0.0)
    if auroc_b_dw <= auroc_r_dw:
        reasons.append(
            f"AUROC_B(death_within_2s) {auroc_b_dw:.4f} <= AUROC_R_lasttick {auroc_r_dw:.4f}"
        )
    if auroc_b_dw <= AUROC_THRESHOLD_DEATH:
        reasons.append(
            f"AUROC_B(death_within_2s) {auroc_b_dw:.4f} <= threshold {AUROC_THRESHOLD_DEATH:.3f}"
        )

    if rankme_b < RANKME_THRESHOLD:
        reasons.append(f"RankMe_B {rankme_b:.2f} < threshold {RANKME_THRESHOLD}")

    return len(reasons) == 0, reasons


# ── report generation ────────────────────────────────────────────────


def _fmt(v: Optional[float], decimals: int = 4) -> str:
    if v is None:
        return "n/a"
    return f"{v:.{decimals}f}"


def _load_historical_row() -> Optional[Dict[str, Any]]:
    """Load T6/T4 from verify_math_claims JSON (Parte III §5.2, A-19)."""
    p = Path("docs/research/verify_math_claims_2026-09-05.json")
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        return {
            "T6": d.get("T6_probes"),
            "T4": d.get("T4_collapse_metrics"),
        }
    except (json.JSONDecodeError, OSError):
        return None


def _read_sidecar_info(checkpoint_path: str) -> Dict[str, str]:
    """Read schema_fingerprint and step from v2 sidecar, if available."""
    meta_path = Path(checkpoint_path).with_suffix("").with_suffix(".pt.meta.json")
    if not meta_path.exists():
        meta_path = Path(checkpoint_path + ".meta.json")
    if not meta_path.exists():
        return {"schema_fingerprint": "unavailable", "step": "unavailable"}
    try:
        meta = json.loads(meta_path.read_text())
        fp = meta.get("schema_fingerprint", "unavailable")
        step = str(meta.get("extra", {}).get("step", "unavailable"))
        return {"schema_fingerprint": fp, "step": step}
    except (json.JSONDecodeError, OSError):
        return {"schema_fingerprint": "unavailable", "step": "unavailable"}


def generate_report(
    all_contender_metrics: Dict[str, Dict[int, ContenderMetrics]],
    seeds: Sequence[int],
    passed: bool,
    verdict_reasons: List[str],
    checkpoint_path: str,
    data_dir: str,
    elapsed_s: float,
) -> str:
    """Generate the markdown benchmark report."""
    lines: List[str] = []
    lines.append("# JEPA v2 vs Legacy Benchmark Report")
    lines.append("")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    lines.append(f"**Seeds**: {list(seeds)}")
    lines.append(f"**Checkpoint**: `{checkpoint_path}`")

    sidecar = _read_sidecar_info(checkpoint_path)
    lines.append(f"**Schema fingerprint**: `{sidecar['schema_fingerprint']}`")
    lines.append(f"**Training step**: {sidecar['step']}")
    lines.append(f"**Data dir**: `{data_dir}`")
    lines.append(f"**Elapsed**: {elapsed_s:.1f}s")
    lines.append("")

    verdict_str = "PASS" if passed else "FAIL"
    lines.append(f"## Verdict: **{verdict_str}**")
    lines.append("")
    if not passed:
        for r in verdict_reasons:
            lines.append(f"- {r}")
        lines.append("")
    lines.append("Criteria (D-18, Parte III §5.3):")
    lines.append(f"- AUROC_B(round_won) > AUROC_R(round_won) AND > {AUROC_THRESHOLD_ROUND_WON}")
    lines.append(f"- AUROC_B(death_within_2s) > AUROC_R_lasttick AND > {AUROC_THRESHOLD_DEATH}")
    lines.append(f"- RankMe_B >= {RANKME_THRESHOLD}")
    lines.append("")

    def _mean_auroc(contender: str, label: str) -> Tuple[float, float]:
        vals = []
        for s in seeds:
            m = all_contender_metrics[contender].get(s)
            if m is None:
                continue
            pr = m.probe_results.get(label)
            if pr is not None and pr.n_folds_used > 0:
                vals.append(pr.auroc_mean)
        if not vals:
            return 0.0, 0.0
        return float(np.mean(vals)), float(np.std(vals))

    def _mean_scalar(contender: str, attr: str) -> Tuple[Optional[float], Optional[float]]:
        vals = []
        for s in seeds:
            m = all_contender_metrics[contender].get(s)
            if m is None:
                continue
            v = getattr(m, attr, None)
            if v is not None:
                vals.append(v)
        if not vals:
            return None, None
        return float(np.mean(vals)), float(np.std(vals))

    contenders = list(all_contender_metrics.keys())
    lines.append("## Probe AUROC (mean ± std over seeds)")
    lines.append("")
    header = "| Label |"
    sep = "|-------|"
    for c in contenders:
        header += f" {c} |"
        sep += "------|"
    lines.append(header)
    lines.append(sep)
    for label in PROBE_LABELS:
        row = f"| {label} |"
        for c in contenders:
            mu, sd = _mean_auroc(c, label)
            if mu == 0.0 and sd == 0.0:
                row += " n/a |"
            else:
                row += f" {mu:.4f}±{sd:.4f} |"
        lines.append(row)
    lines.append("")

    lines.append("## Collapse & Extra Metrics (mean ± std over seeds)")
    lines.append("")
    header2 = "| Metric |"
    sep2 = "|--------|"
    for c in contenders:
        header2 += f" {c} |"
        sep2 += "------|"
    lines.append(header2)
    lines.append(sep2)
    for attr, name in [
        ("rankme_val", "RankMe"),
        ("knn_acc", "kNN-20 acc"),
        ("dpos_r2_05s", "Δpos R² 0.5s"),
        ("dpos_r2_2s", "Δpos R² 2.0s"),
    ]:
        row = f"| {name} |"
        for c in contenders:
            mu, sd = _mean_scalar(c, attr)
            if mu is None:
                row += " n/a |"
            else:
                row += f" {mu:.4f}±{_fmt(sd)} |"
        lines.append(row)
    lines.append("")

    hist = _load_historical_row()
    if hist and hist.get("T6"):
        lines.append("## Historical Reference (verify_math_claims 2026-09-05)")
        lines.append("")
        t6 = hist["T6"]
        lines.append("| Label | raw_mean | raw_last | archived_256d | random_256d |")
        lines.append("|-------|----------|----------|---------------|-------------|")
        for lbl, key in [
            ("round_won", "round_won"),
            ("death_within_128_ticks", "death_within_128_ticks"),
            ("enemy_visible_within_128", "enemy_visible_within_128_ticks"),
        ]:
            entry = t6.get(key, {})
            rm = entry.get("raw_window_mean_25d", {})
            rl = entry.get("raw_last_tick_25d", {})
            ar = entry.get("archived_context_embedding_256d", {})
            rn = entry.get("random_init_context_embedding_256d", {})
            lines.append(
                f"| {lbl} "
                f"| {_fmt(rm.get('auroc_mean'))}±{_fmt(rm.get('auroc_std'))} "
                f"| {_fmt(rl.get('auroc_mean'))}±{_fmt(rl.get('auroc_std'))} "
                f"| {_fmt(ar.get('auroc_mean'))}±{_fmt(ar.get('auroc_std'))} "
                f"| {_fmt(rn.get('auroc_mean'))}±{_fmt(rn.get('auroc_std'))} |"
            )
        lines.append("")
        t4 = hist.get("T4", {})
        arc = t4.get("archived_context_embeddings", {})
        if arc:
            lines.append(
                f"Archived encoder RankMe: {_fmt(arc.get('effective_rank'), 2)} "
                f"(d=256, ratio={_fmt(arc.get('effective_rank', 0) / 256, 3)})"
            )
        lines.append("")

    lines.append("## Known Issues")
    lines.append("")
    lines.append(
        "- Contender A uses an approximate 21→25-d bridge (four missing "
        "v1 slots filled with zeros). Results are informational only."
    )
    lines.append(
        "- `enemy_visible_within_2s` label is not in `probe_batch`'s "
        "D-17 set; only `contact_new_within_2s` is evaluated."
    )
    lines.append("")
    return "\n".join(lines)


# ── main entry point ─────────────────────────────────────────────────


def _resolve_device(device_str: str) -> torch.device:
    if device_str == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
    return torch.device(device_str)


def run_benchmark(
    data_dir: str,
    checkpoint_path: str,
    out_path: str,
    *,
    cfg: JepaV2Config = JepaV2Config(),
    legacy_checkpoint: Optional[str] = None,
    json_path: Optional[str] = None,
    n_windows: int = 8000,
    seeds: Sequence[int] = (0, 1, 2),
    device_str: str = "auto",
) -> Tuple[bool, str]:
    """Run the full benchmark. Returns (passed, report_markdown)."""
    t0 = time.monotonic()
    device = _resolve_device(device_str)
    log.info("Device: %s", device)

    encoder = EncoderV2(cfg).to(device)
    sd = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    encoder.load_state_dict(sd, strict=True)
    encoder.eval()

    legacy_enc = None
    if legacy_checkpoint:
        legacy_enc = _load_legacy_encoder(legacy_checkpoint, device)

    all_metrics: Dict[str, Dict[int, ContenderMetrics]] = {
        "B_mean": {},
        "B_last": {},
        "R_mean": {},
        "R_last": {},
    }
    if legacy_enc is not None:
        all_metrics["A_mean"] = {}

    split = "val"

    for seed in seeds:
        log.info("=== Seed %d ===", seed)
        ws = draw_windows(data_dir, cfg, seed, n_windows, split)

        reps_b = _encode_v2(encoder, ws, device)
        reps_r = _encode_raw(ws)

        for rep_key, z in [
            ("B_mean", reps_b["b_mean"]),
            ("B_last", reps_b["b_last"]),
            ("R_mean", reps_r["r_mean"]),
            ("R_last", reps_r["r_last"]),
        ]:
            all_metrics[rep_key][seed] = compute_metrics_for_contender(
                rep_key,
                z,
                ws,
                data_dir,
                split,
                cfg,
                seed,
            )

        if legacy_enc is not None:
            reps_a = _encode_legacy(legacy_enc, ws, device)
            all_metrics["A_mean"][seed] = compute_metrics_for_contender(
                "A_mean",
                reps_a["a_mean"],
                ws,
                data_dir,
                split,
                cfg,
                seed,
            )

    def _seed_mean_auroc(contender: str, label: str) -> float:
        vals = []
        for s in seeds:
            m = all_metrics[contender].get(s)
            if m is None:
                continue
            pr = m.probe_results.get(label)
            if pr is not None and pr.n_folds_used > 0:
                vals.append(pr.auroc_mean)
        return float(np.mean(vals)) if vals else 0.0

    def _seed_mean_rankme(contender: str) -> float:
        vals = [all_metrics[contender][s].rankme_val for s in seeds if s in all_metrics[contender]]
        return float(np.mean(vals)) if vals else 0.0

    b_aurocs = {
        "round_won": _seed_mean_auroc("B_mean", "round_won"),
        "death_within_2s": _seed_mean_auroc("B_mean", "death_within_2s"),
    }
    r_aurocs = {
        "round_won": _seed_mean_auroc("R_mean", "round_won"),
        "death_within_2s": _seed_mean_auroc("R_last", "death_within_2s"),
    }
    rankme_b = _seed_mean_rankme("B_mean")

    passed, reasons = compute_verdict(b_aurocs, r_aurocs, rankme_b)

    elapsed = time.monotonic() - t0
    report = generate_report(
        all_metrics,
        seeds,
        passed,
        reasons,
        checkpoint_path,
        data_dir,
        elapsed,
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    log.info("Report written to %s", out)

    if json_path:
        json_out = _build_json_output(all_metrics, seeds, passed, reasons, rankme_b)
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(json_out, indent=2) + "\n")
        log.info("JSON written to %s", json_path)

    return passed, report


def _build_json_output(
    all_metrics: Dict[str, Dict[int, ContenderMetrics]],
    seeds: Sequence[int],
    passed: bool,
    reasons: List[str],
    rankme_b: float,
) -> Dict[str, Any]:
    """Build JSON-serializable summary."""
    out: Dict[str, Any] = {
        "verdict": "PASS" if passed else "FAIL",
        "reasons": reasons,
        "rankme_b_mean": rankme_b,
        "seeds": list(seeds),
        "contenders": {},
    }
    for cname, seed_map in all_metrics.items():
        c_out: Dict[str, Any] = {}
        for s, m in seed_map.items():
            s_out: Dict[str, Any] = {
                "rankme": m.rankme_val,
                "knn_acc": m.knn_acc,
                "dpos_r2_05s": m.dpos_r2_05s,
                "dpos_r2_2s": m.dpos_r2_2s,
                "probes": {},
            }
            for label, pr in m.probe_results.items():
                if pr is None:
                    s_out["probes"][label] = None
                else:
                    s_out["probes"][label] = {
                        "auroc_mean": pr.auroc_mean,
                        "auroc_std": pr.auroc_std,
                        "ece_mean": pr.ece_mean,
                        "ece_calibrated_mean": pr.ece_calibrated_mean,
                        "temperature_mean": pr.temperature_mean,
                        "n_folds_used": pr.n_folds_used,
                    }
            c_out[str(s)] = s_out
        out["contenders"][cname] = c_out
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Benchmark jepa_v2 encoder vs raw features and legacy.",
    )
    p.add_argument("--data-dir", required=True, help="Root of safetensors shards.")
    p.add_argument(
        "--checkpoint",
        default=None,
        help="Checkpoint name for persistence.load_nn (e.g. 'jepa_v2_encoder').",
    )
    p.add_argument(
        "--checkpoint-path",
        default=None,
        help="Direct path to EncoderV2 state_dict .pt file.",
    )
    p.add_argument(
        "--legacy-checkpoint",
        default=_DEFAULT_LEGACY_PATH,
        help="Path to archived legacy JEPACoachingModel checkpoint.",
    )
    p.add_argument(
        "--out",
        default="docs/benchmarks/jepa_v2_vs_legacy.md",
        help="Output markdown report path.",
    )
    p.add_argument("--json", default=None, help="Optional JSON output path.")
    p.add_argument("--n-windows", type=int, default=8000)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    p.add_argument("--device", default="auto")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)

    if args.checkpoint_path:
        ckpt_path = args.checkpoint_path
    elif args.checkpoint:
        from Programma_CS2_RENAN.backend.nn.persistence import get_model_path

        ckpt_path = str(get_model_path(args.checkpoint))
    else:
        sys.exit("Provide --checkpoint or --checkpoint-path.")

    passed, _ = run_benchmark(
        data_dir=args.data_dir,
        checkpoint_path=ckpt_path,
        out_path=args.out,
        legacy_checkpoint=args.legacy_checkpoint,
        json_path=args.json,
        n_windows=args.n_windows,
        seeds=args.seeds,
        device_str=args.device,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
