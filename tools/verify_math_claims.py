#!/usr/bin/env python3
"""Empirical verification of the mathematical claims in CORREZIONE_NUCLEO_NEURALE (Parte II).

Read-only against the production monolith (SQLite ``mode=ro``). Never opens the
database for writing, never touches the ingestion queue, runs on CPU only.

What it measures, on real pro ticks:

  T1  tick rate (ticks/second) estimated from time_in_round vs tick inside rounds
  T2  per-tick feature deltas of the 25-dim production vector at horizons
      h in {1, 8, 32, 128, 640} ticks, and the R^2 of the identity predictor
      x_{t+h} := x_t against the mean predictor
  T3  "slow feature" census: fraction of 11-tick windows in which each feature
      is exactly constant; kast_estimate constancy; round_phase vs equipment_value
  T4  archived jepa_brain.pt (2026-08-03) vs random init vs raw features:
      RankMe / std_min / cosine off-diagonal on 10-tick context embeddings,
      EMA drift between context and target encoders
  T5  predictor vs identity: MSE and InfoNCE (in-batch negatives, learned tau)
      at horizons 1/32/128/640 ticks, for the archived predictor, the identity
      map in target-encoder space, and a random-init model
  T6  linear probes (logistic regression, GroupKFold by demo) for external
      labels: round_won (roundstats), death within 2 s, enemy visible within 2 s
      on raw window-mean features (25-d), archived embeddings (256-d),
      random-init embeddings (256-d)
  T7  SIGReg (Epps-Pulley, le-wm implementation) value of archived embeddings
      vs an isotropic Gaussian of the same shape

Note: the archived run docs/research/verify_math_claims_2026-09-05.json was produced by the first
version of this script, which matched player names exactly (30 of 48 pairs yielded ticks — the D8
finding). This version resolves names case/space-insensitively; re-running will therefore cover more
pairs and shift the numbers slightly without changing the conclusions.

Usage (from repo root, with the repo .venv):
  CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/bin/python tools/verify_math_claims.py \
      --pairs 48 --ticks-per-pair 40000 --stride 64 --out docs/research/verify_math_claims_2026-09-05.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
import torch  # noqa: E402

torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from Programma_CS2_RENAN.backend.nn.collapse_metrics import (  # noqa: E402
    compute_collapse_metrics,
    compute_ema_drift,
)
from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel  # noqa: E402
from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (  # noqa: E402
    FEATURE_NAMES,
    FeatureExtractor,
)

CONTEXT_LEN = 10  # training_orchestrator.py: context window 10 ticks
TARGET_LEN = 1  # training_orchestrator.py: target 1 tick (window 11)
HORIZONS = (1, 8, 32, 128, 640)
DEATH_HORIZON_TICKS = 128  # ~2 s at 64 Hz
ARCHIVE = REPO / "Programma_CS2_RENAN/models/global/archive_pre_rebuild_2026-09-01/jepa_brain.pt"

PTS_COLS = [
    "tick",
    "round_number",
    "time_in_round",
    "health",
    "armor",
    "is_crouching",
    "is_scoped",
    "has_helmet",
    "has_defuser",
    "active_weapon",
    "equipment_value",
    "enemies_visible",
    "is_blinded",
    "pos_x",
    "pos_y",
    "pos_z",
    "view_x",
    "view_y",
    "bomb_planted",
    "teammates_alive",
    "enemies_alive",
    "team_economy",
    "map_name",
]


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def open_ro() -> sqlite3.Connection:
    db = os.path.realpath(REPO / "Programma_CS2_RENAN/backend/storage/database.db")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=120)
    con.execute("PRAGMA query_only=1")
    return con


def select_pairs(con: sqlite3.Connection, n_pairs: int, seed: int) -> List[Tuple[str, str]]:
    rows = con.execute(
        "SELECT demo_name, player_name, COUNT(*) AS n FROM roundstats "
        "GROUP BY demo_name, player_name HAVING n >= 12"
    ).fetchall()
    by_demo: Dict[str, List[str]] = defaultdict(list)
    for demo, player, _ in rows:
        by_demo[demo].append(player)
    demos = sorted(by_demo)
    rng = random.Random(seed)
    rng.shuffle(demos)
    pairs: List[Tuple[str, str]] = []
    # round-robin over demos so that ≥ n_pairs/2 distinct demos are covered
    while len(pairs) < n_pairs and demos:
        for demo in list(demos):
            if not by_demo[demo]:
                demos.remove(demo)
                continue
            player = by_demo[demo].pop(rng.randrange(len(by_demo[demo])))
            pairs.append((demo, player))
            if len(pairs) >= n_pairs:
                break
    return pairs


def resolve_stored_name(con: sqlite3.Connection, demo: str, player: str) -> str | None:
    """D8 (Parte III §2.4): roundstats stores lower/strip names, playertickstate keeps the raw
    spelling (leading spaces, capitals). Resolve the stored spelling via the demo's distinct names
    (indexed on demo_name) so the tick query can still use ix_pts_player_demo."""
    want = player.strip().casefold()
    for (name,) in con.execute(
        "SELECT DISTINCT player_name FROM playertickstate WHERE demo_name = ?", (demo,)
    ):
        if str(name).strip().casefold() == want:
            return name
    return None


def fetch_ticks(con: sqlite3.Connection, demo: str, player: str, limit: int) -> List[dict]:
    stored = resolve_stored_name(con, demo, player)
    if stored is None:
        _log(f"  D8: no playertickstate rows for {demo!r} / {player!r} (name mismatch) — skipped")
        return []
    q = (
        f"SELECT {', '.join(PTS_COLS)} FROM playertickstate "
        "WHERE demo_name = ? AND player_name = ? ORDER BY tick LIMIT ?"
    )
    return [dict(zip(PTS_COLS, r)) for r in con.execute(q, (demo, stored, limit))]


def estimate_tick_rate(ticks: List[dict]) -> List[float]:
    est = []
    by_round: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
    for d in ticks:
        if d["time_in_round"] is not None:
            by_round[d["round_number"]].append((d["tick"], float(d["time_in_round"])))
    for rnd, seq in by_round.items():
        if len(seq) < 200:
            continue
        t = np.array([s[0] for s in seq], dtype=float)
        s = np.array([s[1] for s in seq], dtype=float)
        if s.max() - s.min() < 5.0:
            continue
        slope = np.polyfit(t, s, 1)[0]  # seconds per tick
        if slope > 0:
            est.append(1.0 / slope)
    return est


class Segment:
    """Contiguous ticks of one (demo, player) with features, health, round ids."""

    def __init__(self, demo: str, player: str, ticks: List[dict]):
        self.demo = demo
        self.player = player
        self.tick = np.array([d["tick"] for d in ticks], dtype=np.int64)
        self.round = np.array([d["round_number"] for d in ticks], dtype=np.int64)
        self.health = np.array([d["health"] for d in ticks], dtype=np.float32)
        self.enemies_visible = np.array(
            [d["enemies_visible"] or 0 for d in ticks], dtype=np.float32
        )
        map_name = ticks[0]["map_name"]
        self.X = FeatureExtractor.extract_batch(ticks, map_name=map_name)  # (T, 25)


def delta_stats(segs: List[Segment]) -> dict:
    out = {}
    allX = np.concatenate([s.X for s in segs], axis=0)
    mu = allX.mean(axis=0)
    var = allX.var(axis=0)
    out["feature_mean"] = mu.tolist()
    out["feature_std"] = np.sqrt(var).tolist()
    for h in HORIZONS:
        num = np.zeros(allX.shape[1])
        den = np.zeros(allX.shape[1])
        absd = np.zeros(allX.shape[1])
        zero = np.zeros(allX.shape[1])
        n = 0
        for s in segs:
            if len(s.X) <= h:
                continue
            same = (s.round[h:] == s.round[:-h]) & (s.tick[h:] - s.tick[:-h] == h)
            a = s.X[:-h][same]
            b = s.X[h:][same]
            if len(a) == 0:
                continue
            d = b - a
            num += (d**2).sum(axis=0)
            den += ((b - mu) ** 2).sum(axis=0)
            absd += np.abs(d).sum(axis=0)
            zero += (np.abs(d) < 1e-7).sum(axis=0)
            n += len(a)
        r2_per_feature = 1.0 - num / np.maximum(den, 1e-12)
        out[f"h{h}"] = {
            "n_pairs": int(n),
            "identity_r2_total": float(1.0 - num.sum() / max(den.sum(), 1e-12)),
            "identity_r2_per_feature": r2_per_feature.tolist(),
            "mean_abs_delta_per_feature": (absd / max(n, 1)).tolist(),
            "rms_delta_per_feature": np.sqrt(num / max(n, 1)).tolist(),
            "frac_zero_delta_per_feature": (zero / max(n, 1)).tolist(),
            "mean_abs_delta_overall": float(absd.sum() / max(n * allX.shape[1], 1)),
        }
    return out


def make_windows(segs: List[Segment], stride: int, max_h: int) -> dict:
    """Windows of CONTEXT_LEN ticks; targets at every horizon; labels."""
    ctx, tgt = [], {h: [] for h in HORIZONS}
    death, enemy, groups, rounds, players, tick0 = [], [], [], [], [], []
    for s in segs:
        T = len(s.X)
        for i in range(0, T - CONTEXT_LEN - max_h - DEATH_HORIZON_TICKS, stride):
            j = i + CONTEXT_LEN  # first target index (h=1 target is X[j])
            if (
                s.round[i] != s.round[j + max_h - 1]
                or s.tick[j + max_h - 1] - s.tick[i] != CONTEXT_LEN + max_h - 1
            ):
                continue
            if s.health[j - 1] <= 0:
                continue  # player already dead at end of context
            ctx.append(s.X[i:j])
            for h in HORIZONS:
                tgt[h].append(s.X[j + h - 1])
            fut = s.health[j : j + DEATH_HORIZON_TICKS]
            death.append(1 if (fut <= 0).any() else 0)
            enemy.append(1 if (s.enemies_visible[j : j + DEATH_HORIZON_TICKS] > 0).any() else 0)
            groups.append(s.demo)
            rounds.append(int(s.round[j]))
            players.append(s.player.strip())
            tick0.append(int(s.tick[j]))
    return {
        "ctx": np.stack(ctx).astype(np.float32),
        "tgt": {h: np.stack(v).astype(np.float32) for h, v in tgt.items()},
        "death": np.array(death),
        "enemy": np.array(enemy),
        "demo": np.array(groups),
        "round": np.array(rounds),
        "player": np.array(players),
    }


def attach_round_won(con: sqlite3.Connection, W: dict) -> np.ndarray:
    demos = sorted(set(W["demo"].tolist()))
    rw: Dict[Tuple[str, int, str], int] = {}
    for demo in demos:
        for rnd, player, won in con.execute(
            "SELECT round_number, player_name, round_won FROM roundstats WHERE demo_name = ?",
            (demo,),
        ):
            rw[(demo, int(rnd), str(player).strip())] = int(bool(won))
    y = np.array(
        [rw.get((d, int(r), p), -1) for d, r, p in zip(W["demo"], W["round"], W["player"])]
    )
    return y


@torch.no_grad()
def encode(
    model: JEPACoachingModel, x: np.ndarray, which: str = "context", bs: int = 4096
) -> torch.Tensor:
    enc = model.context_encoder if which == "context" else model.target_encoder
    outs = []
    for i in range(0, len(x), bs):
        xb = torch.from_numpy(x[i : i + bs])
        if xb.dim() == 2:
            xb = xb.unsqueeze(1)
        outs.append(enc(xb).mean(dim=1))
    return torch.cat(outs)


@torch.no_grad()
def predict(model: JEPACoachingModel, s_ctx: torch.Tensor, bs: int = 4096) -> torch.Tensor:
    return torch.cat([model.predictor(s_ctx[i : i + bs]) for i in range(0, len(s_ctx), bs)])


def infonce(
    pred: torch.Tensor, target: torch.Tensor, tau: float, bs: int = 256, seed: int = 0
) -> dict:
    bs = int(min(bs, len(pred)))
    g = torch.Generator().manual_seed(seed)
    perm = torch.randperm(len(pred), generator=g)
    pred, target = pred[perm], target[perm]
    p = torch.nn.functional.normalize(pred, dim=1)
    t = torch.nn.functional.normalize(target, dim=1)
    losses, accs = [], []
    for i in range(0, len(p) - bs + 1, bs):
        logits = (p[i : i + bs] @ t[i : i + bs].T) / tau
        labels = torch.arange(bs)
        losses.append(torch.nn.functional.cross_entropy(logits, labels).item())
        accs.append((logits.argmax(dim=1) == labels).float().mean().item())
    return {
        "loss": float(np.mean(losses)),
        "top1": float(np.mean(accs)),
        "chance_loss": math.log(bs),
        "batch": bs,
    }


def sigreg_epps_pulley(
    proj: torch.Tensor, num_proj: int = 1024, knots: int = 17, t_max: float = 3.0, seed: int = 0
) -> float:
    """SIGReg exactly as in lucas-maes/le-wm module.py (trapezoid on [0, t_max], Gaussian window)."""
    g = torch.Generator().manual_seed(seed)
    t = torch.linspace(0, t_max, knots)
    dt = t_max / (knots - 1)
    weights = torch.full((knots,), 2 * dt)
    weights[[0, -1]] = dt
    phi = torch.exp(-t.square() / 2.0)
    weights = weights * phi
    A = torch.randn(proj.size(-1), num_proj, generator=g)
    A = A / A.norm(p=2, dim=0, keepdim=True)
    x_t = (proj @ A).unsqueeze(-1) * t  # (N, M, K)
    err = (x_t.cos().mean(-3) - phi).square() + x_t.sin().mean(-3).square()  # (M, K)
    return float(((err @ weights) * proj.size(-2)).mean())


def probes(
    features: Dict[str, np.ndarray], labels: Dict[str, np.ndarray], groups: np.ndarray, seed: int
) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler

    out = {}
    gkf = GroupKFold(n_splits=5)
    for lname, y in labels.items():
        valid = y >= 0
        out[lname] = {
            "n": int(valid.sum()),
            "positive_rate": float(y[valid].mean()) if valid.any() else None,
        }
        if valid.sum() < 500 or y[valid].min() == y[valid].max():
            continue
        for fname, X in features.items():
            Xv, yv, gv = X[valid], y[valid], groups[valid]
            aucs = []
            for tr, te in gkf.split(Xv, yv, gv):
                if yv[tr].min() == yv[tr].max() or yv[te].min() == yv[te].max():
                    continue
                sc = StandardScaler().fit(Xv[tr])
                clf = LogisticRegression(
                    max_iter=3000, C=1.0, class_weight="balanced", random_state=seed
                )
                clf.fit(sc.transform(Xv[tr]), yv[tr])
                aucs.append(roc_auc_score(yv[te], clf.decision_function(sc.transform(Xv[te]))))
            out[lname][fname] = {
                "auroc_mean": float(np.mean(aucs)),
                "auroc_std": float(np.std(aucs)),
                "folds": len(aucs),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=48)
    ap.add_argument("--ticks-per-pair", type=int, default=40000)
    ap.add_argument("--stride", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=str, default="docs/research/verify_math_claims.json")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    t0 = time.time()
    con = open_ro()
    pairs = select_pairs(con, args.pairs, args.seed)
    _log(f"selected {len(pairs)} (demo, player) pairs over {len(set(p[0] for p in pairs))} demos")

    segs: List[Segment] = []
    tick_rates: List[float] = []
    for k, (demo, player) in enumerate(pairs):
        ticks = fetch_ticks(con, demo, player, args.ticks_per_pair)
        if len(ticks) < CONTEXT_LEN + max(HORIZONS) + DEATH_HORIZON_TICKS + 1:
            continue
        tick_rates += estimate_tick_rate(ticks)
        segs.append(Segment(demo, player, ticks))
        if k % 8 == 0:
            _log(f"  fetched+extracted {k + 1}/{len(pairs)} ({len(ticks)} ticks)")
    if not segs:
        raise RuntimeError(
            "No (demo, player) pair yielded ticks — check the roundstats/playertickstate name "
            "alignment (D8, Parte III §2.4) and the --ticks-per-pair value."
        )
    n_ticks = int(sum(len(s.X) for s in segs))
    _log(f"total ticks: {n_ticks}; tick-rate estimates: {len(tick_rates)}")

    results: dict = {
        "meta": {
            "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pairs": len(segs),
            "demos": len(set(s.demo for s in segs)),
            "ticks": n_ticks,
            "context_len": CONTEXT_LEN,
            "target_len": TARGET_LEN,
            "horizons": list(HORIZONS),
            "feature_names": list(FEATURE_NAMES),
            "checkpoint": str(ARCHIVE.relative_to(REPO)),
            "torch": torch.__version__,
        }
    }
    # T1
    tr = np.array(tick_rates)
    results["T1_tick_rate"] = {
        "median": float(np.median(tr)) if len(tr) else None,
        "p05": float(np.percentile(tr, 5)) if len(tr) else None,
        "p95": float(np.percentile(tr, 95)) if len(tr) else None,
        "n_rounds": int(len(tr)),
        "ms_per_tick_at_median": float(1000.0 / np.median(tr)) if len(tr) else None,
    }
    # T2
    _log("T2 delta statistics")
    results["T2_deltas"] = delta_stats(segs)
    # T3
    _log("T3 slow-feature census")
    allX = np.concatenate([s.X for s in segs], axis=0)
    const_frac = np.zeros(allX.shape[1])
    n_win = 0
    for s in segs:
        T = len(s.X)
        for i in range(0, T - CONTEXT_LEN - 1, args.stride):
            w = s.X[i : i + CONTEXT_LEN + 1]
            if s.round[i] != s.round[i + CONTEXT_LEN]:
                continue
            const_frac += np.abs(w - w[0]).max(axis=0) < 1e-7
            n_win += 1
    idx = {n: i for i, n in enumerate(FEATURE_NAMES)}
    ev = allX[:, idx["equipment_value"]]
    rp = allX[:, idx["round_phase"]]
    results["T3_slow_features"] = {
        "windows": int(n_win),
        "frac_constant_in_11_tick_window": (const_frac / max(n_win, 1)).tolist(),
        "kast_estimate_unique_values": np.unique(allX[:, idx["kast_estimate"]]).tolist()[:5],
        "map_id_unique_values_count": int(len(np.unique(allX[:, idx["map_id"]]))),
        "round_phase_unique_values": np.unique(rp).tolist(),
        "round_phase_is_function_of_equipment_value": bool(
            all(len(np.unique(rp[ev == v])) == 1 for v in np.unique(ev)[:2000])
        ),
    }
    # windows
    _log("building windows")
    W = make_windows(segs, args.stride, max(HORIZONS))
    W["round_won"] = attach_round_won(con, W)
    results_rw = con.execute("SELECT AVG(round_won), COUNT(*) FROM roundstats").fetchone()
    con.close()
    _log(
        f"windows: {len(W['ctx'])}; round_won labelled: {(W['round_won'] >= 0).sum()}; death+: {W['death'].sum()}; enemy+: {W['enemy'].sum()}"
    )

    # models
    arch = JEPACoachingModel(input_dim=25, output_dim=10)
    sd = torch.load(ARCHIVE, map_location="cpu", weights_only=True)
    arch.load_state_dict(sd, strict=True)
    arch.eval()
    torch.manual_seed(args.seed + 1)
    rnd = JEPACoachingModel(input_dim=25, output_dim=10)
    rnd.eval()
    tau_arch = float(torch.exp(arch.log_temperature.detach()))
    results["T4_checkpoint"] = {
        "tau_learned": tau_arch,
        "ema_drift_context_vs_target": compute_ema_drift(
            arch.context_encoder.parameters(), arch.target_encoder.parameters()
        ),
        "ema_drift_random_init": compute_ema_drift(
            rnd.context_encoder.parameters(), rnd.target_encoder.parameters()
        ),
        "param_norm_context": float(
            sum(p.detach().norm() ** 2 for p in arch.context_encoder.parameters()) ** 0.5
        ),
        "param_norm_target": float(
            sum(p.detach().norm() ** 2 for p in arch.target_encoder.parameters()) ** 0.5
        ),
    }
    _log("T4 embeddings + collapse metrics")
    s_ctx_a = encode(arch, W["ctx"], "context")
    s_ctx_r = encode(rnd, W["ctx"], "context")
    s_tgt_a = {h: encode(arch, W["tgt"][h], "target") for h in HORIZONS}
    s_tgt_r = {h: encode(rnd, W["tgt"][h], "target") for h in HORIZONS}
    ctx_in_tgt_a = encode(arch, W["ctx"], "target")  # identity predictor in target space
    ctx_in_tgt_r = encode(rnd, W["ctx"], "target")
    raw_mean = torch.from_numpy(W["ctx"].mean(axis=1))
    results["T4_collapse_metrics"] = {
        "archived_context_embeddings": compute_collapse_metrics(s_ctx_a),
        "archived_target_embeddings_h1": compute_collapse_metrics(s_tgt_a[1]),
        "random_init_context_embeddings": compute_collapse_metrics(s_ctx_r),
        "raw_window_mean_features_25d": compute_collapse_metrics(raw_mean),
        "isotropic_gaussian_256d_same_n": compute_collapse_metrics(torch.randn(len(s_ctx_a), 256)),
        "n": int(len(s_ctx_a)),
    }
    # T5
    _log("T5 predictor vs identity")
    pred_a = predict(arch, s_ctx_a)
    pred_r = predict(rnd, s_ctx_r)
    T5 = {}
    for h in HORIZONS:
        row = {}
        row["mse_archived_predictor"] = float(((pred_a - s_tgt_a[h]) ** 2).mean())
        row["mse_identity_target_space"] = float(((ctx_in_tgt_a - s_tgt_a[h]) ** 2).mean())
        row["mse_context_embedding_as_prediction"] = float(((s_ctx_a - s_tgt_a[h]) ** 2).mean())
        row["mse_random_model_predictor"] = float(((pred_r - s_tgt_r[h]) ** 2).mean())
        row["mse_random_model_identity"] = float(((ctx_in_tgt_r - s_tgt_r[h]) ** 2).mean())
        row["target_variance_per_dim_mean"] = float(s_tgt_a[h].var(dim=0).mean())
        row["cos_archived_pred_vs_target"] = float(
            torch.nn.functional.cosine_similarity(pred_a, s_tgt_a[h]).mean()
        )
        row["cos_identity_vs_target"] = float(
            torch.nn.functional.cosine_similarity(ctx_in_tgt_a, s_tgt_a[h]).mean()
        )
        # negatives triviality: cosine of target vs (identity-positive | other windows | random unit vectors)
        tn = torch.nn.functional.normalize(s_tgt_a[h], dim=1)
        pn = torch.nn.functional.normalize(ctx_in_tgt_a, dim=1)
        gperm = torch.randperm(len(tn), generator=torch.Generator().manual_seed(args.seed + h))
        row["cos_positive_identity"] = float((pn * tn).sum(1).mean())
        row["cos_negative_other_window"] = float((tn[gperm] * tn).sum(1).mean())
        row["cos_negative_random_unit"] = float(
            (torch.nn.functional.normalize(torch.randn_like(tn), dim=1) * tn).sum(1).mean()
        )
        row["infonce_archived_predictor"] = infonce(pred_a, s_tgt_a[h], tau_arch, seed=args.seed)
        row["infonce_identity_target_space"] = infonce(
            ctx_in_tgt_a, s_tgt_a[h], tau_arch, seed=args.seed
        )
        row["infonce_random_model_identity"] = infonce(
            ctx_in_tgt_r, s_tgt_r[h], 0.07, seed=args.seed
        )
        # raw-space identity
        rawc = W["ctx"][:, -1, :]
        rawt = W["tgt"][h]
        row["raw_identity_r2_last_context_tick"] = float(
            1.0 - ((rawt - rawc) ** 2).sum() / ((rawt - rawt.mean(0)) ** 2).sum()
        )
        T5[f"h{h}"] = row
    results["T5_predictor_vs_identity"] = T5
    # T6
    _log("T6 linear probes")
    feats = {
        "raw_window_mean_25d": W["ctx"].mean(axis=1),
        "raw_last_tick_25d": W["ctx"][:, -1, :],
        "archived_context_embedding_256d": s_ctx_a.numpy(),
        "random_init_context_embedding_256d": s_ctx_r.numpy(),
    }
    labels = {
        "round_won": W["round_won"],
        "death_within_128_ticks": W["death"],
        "enemy_visible_within_128_ticks": W["enemy"],
    }
    results["T6_probes"] = probes(feats, labels, W["demo"], args.seed)
    results["T6_probes"]["roundstats_global_round_won_rate"] = float(results_rw[0])
    results["T6_probes"]["roundstats_rows"] = int(results_rw[1])
    # T7
    _log("T7 SIGReg")
    n_sig = min(4096, len(s_ctx_a))
    results["T7_sigreg"] = {
        "archived_context_embeddings": sigreg_epps_pulley(s_ctx_a[:n_sig]),
        "archived_context_embeddings_standardized": sigreg_epps_pulley(
            (s_ctx_a[:n_sig] - s_ctx_a[:n_sig].mean(0)) / (s_ctx_a[:n_sig].std(0) + 1e-6)
        ),
        "random_init_context_embeddings": sigreg_epps_pulley(s_ctx_r[:n_sig]),
        "isotropic_gaussian_256d": sigreg_epps_pulley(torch.randn(n_sig, 256)),
        "collapsed_constant_plus_noise_1e-3": sigreg_epps_pulley(
            torch.ones(n_sig, 256) + 1e-3 * torch.randn(n_sig, 256)
        ),
        "n": n_sig,
    }
    results["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    _log(f"wrote {out} in {results['meta']['elapsed_s']} s")
    # short console summary
    d1 = results["T2_deltas"]["h1"]
    print("\n=== SUMMARY ===")
    print(f"tick rate median: {results['T1_tick_rate']['median']}")
    print(
        f"identity R2 total h=1: {d1['identity_r2_total']:.5f}; mean|delta| h=1: {d1['mean_abs_delta_overall']:.2e}"
    )
    for h in HORIZONS:
        print(
            f"  h={h:4d} identity R2 total: {results['T2_deltas'][f'h{h}']['identity_r2_total']:.5f}"
        )
    cm = results["T4_collapse_metrics"]
    for k in (
        "archived_context_embeddings",
        "random_init_context_embeddings",
        "raw_window_mean_features_25d",
    ):
        print(
            f"RankMe {k}: {cm[k]['effective_rank']:.2f} std_min {cm[k]['std_min']:.4f} cos {cm[k]['cosine_offdiag_mean']:.4f}"
        )
    for h in (1, 128):
        r = T5[f"h{h}"]
        print(
            f"h={h}: mse pred {r['mse_archived_predictor']:.4e} vs identity {r['mse_identity_target_space']:.4e}; "
            f"InfoNCE pred {r['infonce_archived_predictor']['loss']:.3f}/{r['infonce_archived_predictor']['top1']:.3f} "
            f"identity {r['infonce_identity_target_space']['loss']:.3f}/{r['infonce_identity_target_space']['top1']:.3f}"
        )
    for lname, res in results["T6_probes"].items():
        if not isinstance(res, dict):
            continue
        line = " | ".join(
            f"{k}: {v['auroc_mean']:.3f}±{v['auroc_std']:.3f}"
            for k, v in res.items()
            if isinstance(v, dict)
        )
        print(f"probe {lname} (n={res['n']}, pos={res['positive_rate']}): {line}")
    print(
        "SIGReg:",
        {k: (round(v, 3) if isinstance(v, float) else v) for k, v in results["T7_sigreg"].items()},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
