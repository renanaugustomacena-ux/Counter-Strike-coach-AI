#!/usr/bin/env python3
"""Event positives per horizon for the horizon-conditioned value heads (HEPA-style hazards).

Context: CORREZIONE_NUCLEO_NEURALE_PARTE_II.md §8 (hazard, survival CDF, h-AUROC; §8.4
Corollario 2 on rare events) and §9 (ECE with M = 15 bins), CORREZIONE_NUCLEO_NEURALE_PARTE_III.md
§7.5 (``value_heads.py``: dense horizons, events death / round lost / first contact, calibration per
horizon) and §3 (episode = same round, strictly consecutive ticks, >= 64 ticks).

Read-only against the production monolith (SQLite ``mode=ro`` + ``PRAGMA query_only=1``), CPU only.
Reuses the proven access pattern of tools/verify_math_claims.py: ``select_pairs`` on roundstats,
``resolve_stored_name`` (D8 name alignment), ``fetch_ticks`` on ``ix_pts_player_demo``.

What it measures, on real pro ticks:

  E1  token = 8 ticks (125 ms at 64 Hz); for each token whose end tick has health > 0, labels
      death / damage / contact_new / contact_any / blinded within H tokens, H in
      {1,2,3,4,6,8,12,16,24,32,48,64} (0.125 s ... 8 s). The horizon is clipped at the episode end
      (never crossing the round boundary): a token whose remaining episode is shorter than H is kept
      and labelled on the available ticks (right-censoring counted as "no event"). The same numbers
      are also reported on the subset of tokens whose full horizon lies inside the episode.
      Per horizon: tokens, positives, rate, DISTINCT episodes with >= 1 positive token.
  E2  per-episode labels joined from roundstats on (demo_name, round_number, normalized name):
      round_won, opening_death, opening_kill, kast.
  E3  extrapolation to the full database (225 demos in roundstats) with two factors —
      demos_in_db / demos_in_sample (as requested; ignores the other players of each demo and the
      40 000-tick truncation) and estimated_db_ticks / sample_ticks (COUNT(*) per sampled pair on
      ix_pts_player_demo × pairs in playermatchstats) — and to a 70/15/15 split (expected VAL).
  E4  calibration-noise experiment: logistic regression (unweighted, StandardScaler, C = 1) on 8 raw
      token features for death_within_H, H in {4, 16, 64}, GroupKFold(5) by demo; per held-out fold
      AUROC, Brier, ECE with 15 equal-width bins (same definition as
      tools/eval_harness.py::expected_calibration_error) and 15 equal-mass bins; bootstrap
      (200 resamples of episodes) standard error of ECE on the pooled out-of-fold predictions, also
      at sub-sampled numbers of episodes (how many positives a stable ECE needs).

Usage (from repo root, CPU only):
  CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/bin/python tools/measure_event_horizons.py \
      --pairs 72 --ticks-per-pair 40000 --seed 0 \
      --out docs/research/event_horizons_2026-09-05.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from Programma_CS2_RENAN.core.tick_rate import DEFAULT_TICK_RATE  # noqa: E402
from tools.verify_math_claims import (  # noqa: E402  (imports torch on CPU; does not run main())
    fetch_ticks,
    open_ro,
    select_pairs,
)

TICK_RATE_HZ = DEFAULT_TICK_RATE
TOKEN_TICKS = 8
HORIZONS_TOK: Tuple[int, ...] = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)
MIN_EPISODE_TICKS = 64  # Parte III §3
EVENT_LABELS: Tuple[str, ...] = ("death", "damage", "contact_new", "contact_any", "blinded")
ROUND_LABELS: Tuple[str, ...] = ("round_won", "opening_death", "opening_kill", "kast")
CAL_HORIZONS: Tuple[int, ...] = (4, 16, 64)
CAL_FEATURES: Tuple[str, ...] = (
    "health",
    "armor",
    "enemies_visible",
    "teammates_alive",
    "enemies_alive",
    "time_in_round",
    "equipment_value",
    "is_blinded",
)
N_BINS = 15  # Parte II §9.1
SPLIT = {"train": 0.70, "val": 0.15, "test": 0.15}
BOOT_FRACTIONS: Tuple[float, ...] = (0.05, 0.1, 0.2, 0.5, 1.0)
NUMERIC_COLS: Tuple[str, ...] = (
    "tick",
    "round_number",
    "health",
    "armor",
    "enemies_visible",
    "is_blinded",
    "teammates_alive",
    "enemies_alive",
    "time_in_round",
    "equipment_value",
)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# E1: episodes and token labels
# ---------------------------------------------------------------------------
def to_arrays(ticks: List[dict]) -> Dict[str, np.ndarray]:
    return {
        c: np.array([np.nan if d[c] is None else d[c] for d in ticks], dtype=np.float64)
        for c in NUMERIC_COLS
    }


def split_episodes(tick: np.ndarray, rnd: np.ndarray) -> List[Tuple[int, int]]:
    """Contiguous runs with tick[i+1] - tick[i] == 1 and constant round_number (Parte III §3)."""
    if len(tick) == 0:
        return []
    brk = np.where((np.diff(tick) != 1) | (np.diff(rnd) != 0))[0] + 1
    bounds = np.concatenate([[0], brk, [len(tick)]]).astype(int)
    return [(int(a), int(b)) for a, b in zip(bounds[:-1], bounds[1:])]


def next_event_index(cond: np.ndarray) -> np.ndarray:
    """nxt[i] = smallest j >= i with cond[j], else len(cond) (sentinel)."""
    n = cond.shape[0]
    idx = np.where(cond, np.arange(n), n)
    return np.minimum.accumulate(idx[::-1])[::-1]


def episode_tokens(h: np.ndarray, ev: np.ndarray, bl: np.ndarray):
    """Token ends (index 8k+7) alive with >= 1 horizon tick; labels per horizon; full-horizon mask."""
    n = len(h)
    ends = np.arange(n // TOKEN_TICKS) * TOKEN_TICKS + (TOKEN_TICKS - 1)
    ends = ends[ends <= n - 2]
    ends = ends[h[ends] > 0]
    false0 = np.zeros(1, dtype=bool)
    conds = {
        "death": h <= 0,
        "damage": np.concatenate([false0, h[1:] < h[:-1]]),
        "contact_new": np.concatenate([false0, (ev[1:] > 0) & (ev[:-1] == 0)]),
        "contact_any": ev > 0,
        "blinded": np.concatenate([false0, (bl[1:] == 1) & (bl[:-1] == 0)]),
    }
    nxt = {k: next_event_index(v) for k, v in conds.items()}
    labels: Dict[str, Dict[int, np.ndarray]] = {k: {} for k in EVENT_LABELS}
    full: Dict[int, np.ndarray] = {}
    for H in HORIZONS_TOK:
        hi = ends + H * TOKEN_TICKS
        full[H] = hi <= n - 1
        hi_c = np.minimum(hi, n - 1)
        for k in EVENT_LABELS:
            labels[k][H] = nxt[k][ends + 1] <= hi_c
    return ends, labels, full


def round_labels_for_pair(con, demo: str, player: str) -> Dict[int, Dict[str, Optional[int]]]:
    out: Dict[int, Dict[str, Optional[int]]] = {}
    for rnd, won, od, ok, kast in con.execute(
        "SELECT round_number, round_won, opening_death, opening_kill, kast FROM roundstats "
        "WHERE demo_name = ? AND player_name = ?",
        (demo, player),
    ):
        out[int(rnd)] = {
            "round_won": None if won is None else int(bool(won)),
            "opening_death": None if od is None else int(bool(od)),
            "opening_kill": None if ok is None else int(bool(ok)),
            "kast": None if kast is None else int(bool(kast)),
        }
    return out


def count_pair_ticks(con, demo: str, stored_name: str) -> int:
    row = con.execute(
        "SELECT COUNT(*) FROM playertickstate WHERE demo_name = ? AND player_name = ?",
        (demo, stored_name),
    ).fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# E4: calibration metrics
# ---------------------------------------------------------------------------
def ece_equal_width(y: np.ndarray, p: np.ndarray, n_bins: int = N_BINS) -> float:
    """Sum_m |B_m|/n · |mean(y in B_m) − mean(p in B_m)| on equal-width bins of [0, 1]
    (tools/eval_harness.py::expected_calibration_error with n_bins = 15; Parte II §9.1)."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    b = np.clip(np.digitize(p, edges[1:-1], right=False), 0, n_bins - 1)
    sy = np.bincount(b, weights=y, minlength=n_bins)
    sp = np.bincount(b, weights=p, minlength=n_bins)
    return float(np.abs(sy - sp).sum() / len(y))


def ece_equal_mass(y: np.ndarray, p: np.ndarray, n_bins: int = N_BINS) -> float:
    """Same statistic on n_bins rank-based (quantile) bins of equal population."""
    order = np.argsort(p, kind="stable")
    tot = 0.0
    for chunk in np.array_split(order, n_bins):
        if len(chunk):
            tot += abs(float(y[chunk].sum()) - float(p[chunk].sum()))
    return float(tot / len(y))


def bootstrap_ece(
    y: np.ndarray, p: np.ndarray, ep: np.ndarray, n_boot: int, frac: float, rng: np.random.Generator
) -> Dict[str, float]:
    """Resample episodes with replacement (n_draw = frac · E episodes); SE = std over resamples."""
    _, inv = np.unique(ep, return_inverse=True)
    n_ep = int(inv.max()) + 1
    n_draw = max(1, int(round(frac * n_ep)))
    ew, em, npos, ntok = [], [], [], []
    for _ in range(n_boot):
        counts = np.bincount(rng.integers(0, n_ep, n_draw), minlength=n_ep)
        idx = np.repeat(np.arange(len(y)), counts[inv])
        if len(idx) == 0:
            continue
        yb, pb = y[idx], p[idx]
        ew.append(ece_equal_width(yb, pb))
        em.append(ece_equal_mass(yb, pb))
        npos.append(float(yb.sum()))
        ntok.append(float(len(yb)))
    return {
        "fraction_of_episodes": frac,
        "episodes_drawn": n_draw,
        "n_boot": len(ew),
        "tokens_mean": float(np.mean(ntok)),
        "positives_mean": float(np.mean(npos)),
        "positives_min": float(np.min(npos)),
        "ece_width_mean": float(np.mean(ew)),
        "ece_width_se": float(np.std(ew, ddof=1)) if len(ew) > 1 else None,
        "ece_mass_mean": float(np.mean(em)),
        "ece_mass_se": float(np.std(em, ddof=1)) if len(em) > 1 else None,
    }


def calibration_experiment(
    X: np.ndarray, y: np.ndarray, groups: np.ndarray, episodes: np.ndarray, seed: int, n_boot: int
) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(seed)
    gkf = GroupKFold(n_splits=5)
    folds = []
    oof_p = np.full(len(y), np.nan)
    for k, (tr, te) in enumerate(gkf.split(X, y, groups)):
        if y[tr].min() == y[tr].max():
            folds.append({"fold": k, "skipped": "single class in train"})
            continue
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(max_iter=3000, C=1.0, random_state=seed)
        clf.fit(sc.transform(X[tr]), y[tr])
        p = clf.predict_proba(sc.transform(X[te]))[:, 1]
        oof_p[te] = p
        yt = y[te].astype(np.float64)
        folds.append(
            {
                "fold": k,
                "n_test": int(len(te)),
                "positives_test": int(yt.sum()),
                "episodes_test": int(len(np.unique(episodes[te]))),
                "demos_test": int(len(np.unique(groups[te]))),
                "auroc": float(roc_auc_score(yt, p)) if yt.min() != yt.max() else None,
                "brier": float(np.mean((p - yt) ** 2)),
                "ece_width": ece_equal_width(yt, p),
                "ece_mass": ece_equal_mass(yt, p),
            }
        )
    ok = [f for f in folds if "skipped" not in f]

    def ms(key: str) -> Dict[str, Optional[float]]:
        v = [f[key] for f in ok if f.get(key) is not None]
        return {
            "mean": float(np.mean(v)) if v else None,
            "std": float(np.std(v, ddof=1)) if len(v) > 1 else None,
        }

    m = ~np.isnan(oof_p)
    yo, po, eo = y[m].astype(np.float64), oof_p[m], episodes[m]
    pooled = {
        "n": int(m.sum()),
        "positives": int(yo.sum()),
        "episodes": int(len(np.unique(eo))),
        "prevalence": float(yo.mean()),
        "brier_constant_predictor": float(yo.mean() * (1 - yo.mean())),
        "auroc": float(roc_auc_score(yo, po)) if yo.min() != yo.max() else None,
        "brier": float(np.mean((po - yo) ** 2)),
        "ece_width": ece_equal_width(yo, po),
        "ece_mass": ece_equal_mass(yo, po),
        "p_max": float(po.max()),
        "p_quantiles_50_90_99": [float(q) for q in np.quantile(po, [0.5, 0.9, 0.99])],
    }
    boot = {str(f): bootstrap_ece(yo, po, eo, n_boot, f, rng) for f in BOOT_FRACTIONS}
    return {
        "folds": folds,
        "fold_summary": {k: ms(k) for k in ("auroc", "brier", "ece_width", "ece_mass")},
        "pooled_oof": pooled,
        "bootstrap_episodes": boot,
    }


# ---------------------------------------------------------------------------
# Italian markdown tables
# ---------------------------------------------------------------------------
def it_num(x: Optional[float], nd: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/d"
    if nd == 0:
        s = f"{int(round(x)):,}"
    else:
        s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def it_pct(x: Optional[float], nd: int = 2) -> str:
    return "n/d" if x is None else it_num(100.0 * x, nd) + " %"


def tables_it(res: dict) -> str:
    s = res["sample"]
    out: List[str] = []
    out.append(
        "**Campione (2026-09-05, sola lettura).** "
        f"{s['pairs_with_ticks']} coppie (demo, giocatore) su {s['pairs_requested']} richieste "
        f"({s['demos_with_ticks']} demo distinte), {it_num(s['ticks'], 0)} tick, "
        f"{it_num(s['episodes'], 0)} episodi (≥ {MIN_EPISODE_TICKS} tick), "
        f"{it_num(s['tokens_alive'], 0)} token vivi (8 tick = 125 ms); round coperti per coppia: "
        f"{it_num(s['rounds_per_pair_mean'], 1)} in media (round {s['round_min']}–{s['round_max']}). "
        f"Fattori di estrapolazione: ×{it_num(res['scaling']['factor_demos'], 2)} per demo "
        f"(225/{s['demos_with_ticks']}), ×{it_num(res['scaling']['factor_ticks'], 1)} per tick "
        f"(≈ {it_num(res['scaling']['estimated_db_ticks'] / 1e6, 1)} M tick stimati nel DB / "
        f"{it_num(s['ticks'] / 1e6, 2)} M nel campione); VAL = 15 %."
    )
    names = {
        "death": "morte entro H (health ≤ 0)",
        "damage": "danno entro H (health decresce)",
        "contact_new": "nuovo contatto entro H (enemies_visible 0 → > 0)",
        "contact_any": "nemico visibile entro H (enemies_visible > 0 in un tick qualsiasi)",
        "blinded": "accecato entro H (is_blinded 0 → 1)",
    }
    for lab in EVENT_LABELS:
        out.append("")
        out.append(
            f"**Tabella — {names[lab]}.** Orizzonte troncato alla fine dell'episodio (primario); "
            "«f.p.» = solo token con orizzonte pieno dentro l'episodio; «VAL att.» = positivi attesi "
            "nello split VAL (15 %) del DB completo con il fattore per demo / per tick."
        )
        out.append(
            "| H (token) | s | token | positivi | tasso | episodi ≥ 1 pos. | token f.p. | positivi f.p. | tasso f.p. | VAL att. (×demo) | VAL att. (×tick) |"
        )
        out.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for H in HORIZONS_TOK:
            e = res["events"][lab][str(H)]
            x = res["scaling"]["expected_positives"][lab][str(H)]
            out.append(
                f"| {H} | {it_num(e['seconds'], 3)} | {it_num(e['n_tokens'], 0)} | {it_num(e['positives'], 0)} | "
                f"{it_pct(e['rate'])} | {it_num(e['episodes_with_positive'], 0)} | {it_num(e['n_tokens_full'], 0)} | "
                f"{it_num(e['positives_full'], 0)} | {it_pct(e['rate_full'])} | "
                f"{it_num(x['val_by_demos'], 0)} | {it_num(x['val_by_ticks'], 0)} |"
            )
    out.append("")
    out.append(
        "**Tabella — etichette per episodio da `roundstats` (join su demo, round, nome normalizzato).**"
    )
    out.append(
        "| etichetta | episodi con etichetta | episodi positivi | tasso (episodi) | token vivi con etichetta | tasso (token) | episodi pos. attesi in VAL (×demo) | (×tick) |"
    )
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for lab in ROUND_LABELS:
        e = res["episode_labels"][lab]
        x = res["scaling"]["expected_episode_positives"][lab]
        out.append(
            f"| {lab} | {it_num(e['episodes_labelled'], 0)} | {it_num(e['episodes_positive'], 0)} | "
            f"{it_pct(e['episode_rate'])} | {it_num(e['tokens_labelled'], 0)} | {it_pct(e['token_rate'])} | "
            f"{it_num(x['val_by_demos'], 0)} | {it_num(x['val_by_ticks'], 0)} |"
        )
    out.append(
        f"Episodi senza etichetta di round: {it_num(res['episode_labels']['episodes_without_round_label'], 0)} "
        f"su {it_num(s['episodes'], 0)}."
    )
    out.append("")
    out.append(
        "**Tabella — esperimento di calibrazione (regressione logistica su 8 feature grezze del token, "
        "GroupKFold(5) per demo, morte entro H).** μ ± σ sui 5 fold; SE = deviazione standard "
        "dell'ECE su 200 ricampionamenti bootstrap degli episodi delle predizioni out-of-fold; "
        "«Brier cost.» = π(1 − π) del predittore costante."
    )
    out.append(
        "| H (token) | s | token OOF | positivi | episodi | AUROC | Brier | Brier cost. | ECE larg. (15) | ECE massa (15) | SE ECE larg. | SE ECE massa |"
    )
    out.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for H in CAL_HORIZONS:
        c = res["calibration"][str(H)]
        fs, po = c["fold_summary"], c["pooled_oof"]
        b1 = c["bootstrap_episodes"]["1.0"]

        def pm(k: str, nd: int = 3) -> str:
            return f"{it_num(fs[k]['mean'], nd)} ± {it_num(fs[k]['std'], nd)}"

        out.append(
            f"| {H} | {it_num(H * TOKEN_TICKS / TICK_RATE_HZ, 3)} | {it_num(po['n'], 0)} | {it_num(po['positives'], 0)} | "
            f"{it_num(po['episodes'], 0)} | {pm('auroc')} | {pm('brier', 4)} | {it_num(po['brier_constant_predictor'], 4)} | "
            f"{pm('ece_width', 4)} | {pm('ece_mass', 4)} | {it_num(b1['ece_width_se'], 4)} | {it_num(b1['ece_mass_se'], 4)} |"
        )
    out.append("")
    out.append(
        "**Tabella — errore standard dell'ECE in funzione del numero di positivi (bootstrap di una frazione "
        "degli episodi, 200 ricampionamenti, predizioni out-of-fold).**"
    )
    out.append(
        "| H (token) | frazione episodi | episodi | token medi | positivi medi | ECE larg. media | SE ECE larg. | ECE massa media | SE ECE massa |"
    )
    out.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for H in CAL_HORIZONS:
        for f in BOOT_FRACTIONS:
            b = res["calibration"][str(H)]["bootstrap_episodes"][str(f)]
            out.append(
                f"| {H} | {it_num(f, 2)} | {it_num(b['episodes_drawn'], 0)} | {it_num(b['tokens_mean'], 0)} | "
                f"{it_num(b['positives_mean'], 1)} | {it_num(b['ece_width_mean'], 4)} | {it_num(b['ece_width_se'], 4)} | "
                f"{it_num(b['ece_mass_mean'], 4)} | {it_num(b['ece_mass_se'], 4)} |"
            )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--pairs", type=int, default=72)
    ap.add_argument("--ticks-per-pair", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--bootstrap", type=int, default=200)
    ap.add_argument("--out", type=str, default="docs/research/event_horizons_2026-09-05.json")
    ap.add_argument(
        "--tables-out", type=str, default=None, help="optional path for the Italian markdown tables"
    )
    args = ap.parse_args()

    t0 = time.time()
    np.random.seed(args.seed)
    con = open_ro()
    demos_in_db = int(con.execute("SELECT COUNT(DISTINCT demo_name) FROM roundstats").fetchone()[0])
    pairs_in_db = int(con.execute("SELECT COUNT(*) FROM playermatchstats").fetchone()[0])
    pairs = select_pairs(con, args.pairs, args.seed)
    log(
        f"selected {len(pairs)} (demo, player) pairs over {len(set(p[0] for p in pairs))} demos; "
        f"db: {demos_in_db} demos in roundstats, {pairs_in_db} playermatchstats rows"
    )

    # accumulators (token level)
    tok_feat: List[np.ndarray] = []
    tok_ep: List[np.ndarray] = []
    tok_demo: List[np.ndarray] = []
    tok_round: List[np.ndarray] = []
    tok_labels: Dict[str, Dict[int, List[np.ndarray]]] = {
        k: {H: [] for H in HORIZONS_TOK} for k in EVENT_LABELS
    }
    tok_full: Dict[int, List[np.ndarray]] = {H: [] for H in HORIZONS_TOK}
    tok_tir_zero: List[np.ndarray] = []
    # accumulators (episode level)
    ep_records: List[dict] = []
    skipped: List[dict] = []
    full_counts: Dict[str, int] = {}
    demo_index: Dict[str, int] = {}
    n_ticks = 0
    n_ticks_short_episodes = 0
    rounds_per_pair: List[int] = []
    ep_id = 0

    from tools.verify_math_claims import resolve_stored_name

    for k, (demo, player) in enumerate(pairs):
        t1 = time.time()
        ticks = fetch_ticks(con, demo, player, args.ticks_per_pair)
        if not ticks:
            skipped.append(
                {"demo": demo, "player": player, "reason": "no ticks (D8 name mismatch or empty)"}
            )
            log(f"  pair {k + 1}/{len(pairs)}: {demo!r}/{player!r} yielded no ticks — skipped")
            continue
        stored = resolve_stored_name(con, demo, player)
        full_counts[f"{demo}|{player}"] = (
            count_pair_ticks(con, demo, stored) if stored else len(ticks)
        )
        A = to_arrays(ticks)
        n_ticks += len(ticks)
        rlab = round_labels_for_pair(con, demo, player)
        di = demo_index.setdefault(demo, len(demo_index))
        rounds_per_pair.append(int(len(np.unique(A["round_number"]))))
        for a, b in split_episodes(A["tick"], A["round_number"]):
            if b - a < MIN_EPISODE_TICKS:
                n_ticks_short_episodes += b - a
                continue
            h = A["health"][a:b]
            ev = np.nan_to_num(A["enemies_visible"][a:b], nan=0.0)
            bl = np.nan_to_num(A["is_blinded"][a:b], nan=0.0)
            ends, labels, full = episode_tokens(h, ev, bl)
            rnd = int(A["round_number"][a])
            rl = rlab.get(rnd)
            ep_records.append(
                {
                    "episode": ep_id,
                    "pair": k,
                    "demo": di,
                    "round": rnd,
                    "ticks": int(b - a),
                    "tokens_alive": int(len(ends)),
                    "round_labels": rl,
                }
            )
            if len(ends):
                tok_feat.append(np.stack([A[c][a:b][ends] for c in CAL_FEATURES], axis=1))
                tok_ep.append(np.full(len(ends), ep_id, dtype=np.int64))
                tok_demo.append(np.full(len(ends), di, dtype=np.int64))
                tok_round.append(np.full(len(ends), rnd, dtype=np.int64))
                tir = A["time_in_round"][a:b][ends]
                tok_tir_zero.append(np.nan_to_num(tir, nan=0.0) <= 0.0)
                for lab in EVENT_LABELS:
                    for H in HORIZONS_TOK:
                        tok_labels[lab][H].append(labels[lab][H])
                for H in HORIZONS_TOK:
                    tok_full[H].append(full[H])
            ep_id += 1
        if k % 8 == 0 or k == len(pairs) - 1:
            log(
                f"  pair {k + 1}/{len(pairs)}: {len(ticks)} ticks (full {full_counts[f'{demo}|{player}']}), "
                f"episodes so far {ep_id}, {time.time() - t1:.1f}s"
            )
    if not tok_ep:
        raise RuntimeError("no tokens collected — check name alignment (D8) and --ticks-per-pair")

    X = np.concatenate(tok_feat).astype(np.float64)
    X = np.where(np.isnan(X), np.nanmean(X, axis=0), X)
    EP = np.concatenate(tok_ep)
    DEMO = np.concatenate(tok_demo)
    TIR0 = np.concatenate(tok_tir_zero)
    Y = {lab: {H: np.concatenate(tok_labels[lab][H]) for H in HORIZONS_TOK} for lab in EVENT_LABELS}
    F = {H: np.concatenate(tok_full[H]) for H in HORIZONS_TOK}
    n_tok = int(len(EP))
    n_demos = len(demo_index)
    log(
        f"tokens alive: {n_tok}; episodes: {ep_id}; demos: {n_demos}; ticks: {n_ticks} "
        f"({n_ticks_short_episodes} in episodes < {MIN_EPISODE_TICKS} ticks); elapsed {time.time() - t0:.0f}s"
    )

    # E1
    events: Dict[str, Dict[str, dict]] = {}
    for lab in EVENT_LABELS:
        events[lab] = {}
        for H in HORIZONS_TOK:
            y, f = Y[lab][H], F[H]
            events[lab][str(H)] = {
                "seconds": H * TOKEN_TICKS / TICK_RATE_HZ,
                "n_tokens": n_tok,
                "positives": int(y.sum()),
                "rate": float(y.mean()),
                "episodes_with_positive": int(len(np.unique(EP[y]))),
                "n_tokens_full": int(f.sum()),
                "positives_full": int(y[f].sum()),
                "rate_full": float(y[f].mean()) if f.any() else None,
                "episodes_with_positive_full": int(len(np.unique(EP[y & f]))),
            }
    # E2
    episode_labels: Dict[str, dict] = {}
    ep_to_labels = {r["episode"]: r["round_labels"] for r in ep_records}
    for lab in ROUND_LABELS:
        vals = [
            (r["episode"], r["round_labels"][lab])
            for r in ep_records
            if r["round_labels"] is not None and r["round_labels"][lab] is not None
        ]
        pos_eps = {e for e, v in vals if v == 1}
        tok_lab = np.array(
            [ep_to_labels[e][lab] if ep_to_labels[e] is not None else None for e in EP],
            dtype=object,
        )
        has = np.array([v is not None for v in tok_lab])
        tok_pos = np.array([v == 1 for v in tok_lab])
        episode_labels[lab] = {
            "episodes_labelled": int(len(vals)),
            "episodes_positive": int(len(pos_eps)),
            "episode_rate": float(len(pos_eps) / len(vals)) if vals else None,
            "tokens_labelled": int(has.sum()),
            "tokens_positive": int(tok_pos.sum()),
            "token_rate": float(tok_pos.sum() / has.sum()) if has.any() else None,
        }
    episode_labels["episodes_without_round_label"] = int(
        sum(1 for r in ep_records if r["round_labels"] is None)
    )
    episode_labels["distinct_rounds"] = int(len({(r["pair"], r["round"]) for r in ep_records}))

    # E3
    fc = np.array(list(full_counts.values()), dtype=np.float64)
    est_db_ticks = float(fc.mean() * pairs_in_db)
    factor_demos = demos_in_db / n_demos
    factor_ticks = est_db_ticks / n_ticks
    expected: Dict[str, Dict[str, dict]] = {}
    for lab in EVENT_LABELS:
        expected[lab] = {}
        for H in HORIZONS_TOK:
            e = events[lab][str(H)]
            expected[lab][str(H)] = {
                "sample_positives": e["positives"],
                "db_by_demos": e["positives"] * factor_demos,
                "val_by_demos": e["positives"] * factor_demos * SPLIT["val"],
                "db_by_ticks": e["positives"] * factor_ticks,
                "val_by_ticks": e["positives"] * factor_ticks * SPLIT["val"],
                "episodes_with_positive_val_by_demos": e["episodes_with_positive"]
                * factor_demos
                * SPLIT["val"],
                "episodes_with_positive_val_by_ticks": e["episodes_with_positive"]
                * factor_ticks
                * SPLIT["val"],
            }
    expected_ep: Dict[str, dict] = {}
    for lab in ROUND_LABELS:
        e = episode_labels[lab]
        expected_ep[lab] = {
            "sample_episodes_positive": e["episodes_positive"],
            "val_by_demos": e["episodes_positive"] * factor_demos * SPLIT["val"],
            "val_by_ticks": e["episodes_positive"] * factor_ticks * SPLIT["val"],
        }
    scaling = {
        "demos_in_db": demos_in_db,
        "demos_in_sample": n_demos,
        "factor_demos": factor_demos,
        "pairs_in_db": pairs_in_db,
        "pairs_in_sample": len(full_counts),
        "sample_ticks": n_ticks,
        "full_ticks_per_sampled_pair": {
            "mean": float(fc.mean()),
            "min": float(fc.min()),
            "max": float(fc.max()),
        },
        "sample_fraction_of_sampled_pairs": float(n_ticks / fc.sum()),
        "estimated_db_ticks": est_db_ticks,
        "factor_ticks": factor_ticks,
        "split": SPLIT,
        "note": "factor_demos = demos_in_db/demos_in_sample as requested (one player and the first "
        "40 000 ticks per demo → lower bound); factor_ticks = estimated_db_ticks/sample_ticks "
        "(mean COUNT(*) of the sampled pairs × playermatchstats rows) → full-database estimate "
        "assuming the early-round sample is representative",
        "expected_positives": expected,
        "expected_episode_positives": expected_ep,
    }

    # E4
    calibration: Dict[str, dict] = {}
    for H in CAL_HORIZONS:
        log(f"calibration experiment: death_within_{H} (positives {int(Y['death'][H].sum())})")
        calibration[str(H)] = calibration_experiment(
            X, Y["death"][H].astype(np.int64), DEMO, EP, args.seed, args.bootstrap
        )
        b = calibration[str(H)]["bootstrap_episodes"]["1.0"]
        log(
            f"  pooled AUROC {calibration[str(H)]['pooled_oof']['auroc']}, ECE width "
            f"{calibration[str(H)]['pooled_oof']['ece_width']:.4f} (SE {b['ece_width_se']:.4f}), ECE mass "
            f"{calibration[str(H)]['pooled_oof']['ece_mass']:.4f} (SE {b['ece_mass_se']:.4f})"
        )

    res = {
        "meta": {
            "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "script": "tools/measure_event_horizons.py",
            "seed": args.seed,
            "tick_rate_hz": TICK_RATE_HZ,
            "token_ticks": TOKEN_TICKS,
            "horizons_tokens": list(HORIZONS_TOK),
            "horizons_seconds": [H * TOKEN_TICKS / TICK_RATE_HZ for H in HORIZONS_TOK],
            "min_episode_ticks": MIN_EPISODE_TICKS,
            "calibration_horizons": list(CAL_HORIZONS),
            "calibration_features": list(CAL_FEATURES),
            "ece_bins": N_BINS,
            "bootstrap_resamples": args.bootstrap,
            "definitions": {
                "token": "8 consecutive ticks of one episode; token end = tick index 8k+7; kept if health > 0 at the end and >= 1 horizon tick exists",
                "episode": "same (demo, player, round_number), tick[i+1]-tick[i] == 1, length >= 64 ticks (Parte III §3)",
                "horizon": "ticks (end, end + 8H] clipped at the episode end (right-censoring counted as no event); *_full restricts to tokens with end + 8H <= last episode tick",
                "death": "health <= 0 at any tick of the horizon",
                "damage": "health[j] < health[j-1] for some j in the horizon (j-1 may be the token end)",
                "contact_new": "enemies_visible[j] > 0 and enemies_visible[j-1] == 0 for some j in the horizon",
                "contact_any": "enemies_visible[j] > 0 for some j in the horizon",
                "blinded": "is_blinded[j] == 1 and is_blinded[j-1] == 0 for some j in the horizon",
                "ece_width": "sum_m |B_m|/n · |mean(y|B_m) - mean(p|B_m)|, 15 equal-width bins (tools/eval_harness.py::expected_calibration_error)",
                "ece_mass": "same on 15 rank-based bins of equal population",
                "bootstrap": "episodes resampled with replacement on pooled out-of-fold predictions; SE = std over resamples",
            },
            "elapsed_s": round(time.time() - t0, 1),
        },
        "sample": {
            "pairs_requested": len(pairs),
            "pairs_with_ticks": len(full_counts),
            "pairs_skipped": skipped,
            "demos_with_ticks": n_demos,
            "ticks": n_ticks,
            "ticks_in_short_episodes": n_ticks_short_episodes,
            "episodes": ep_id,
            "episodes_with_alive_tokens": int(len(np.unique(EP))),
            "tokens_alive": n_tok,
            "tokens_time_in_round_zero": int(TIR0.sum()),
            "tokens_time_in_round_zero_frac": float(TIR0.mean()),
            "rounds_per_pair_mean": float(np.mean(rounds_per_pair)),
            "round_min": int(min(r["round"] for r in ep_records)),
            "round_max": int(max(r["round"] for r in ep_records)),
            "episode_length_ticks": {
                "mean": float(np.mean([r["ticks"] for r in ep_records])),
                "median": float(np.median([r["ticks"] for r in ep_records])),
                "max": int(max(r["ticks"] for r in ep_records)),
            },
        },
        "events": events,
        "episode_labels": episode_labels,
        "scaling": scaling,
        "calibration": calibration,
    }
    res["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out = Path(args.out)
    if not out.is_absolute():
        out = REPO / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    log(f"wrote {out} ({out.stat().st_size} bytes) in {res['meta']['elapsed_s']}s")

    md = tables_it(res)
    if args.tables_out:
        Path(args.tables_out).write_text(md + "\n", encoding="utf-8")
        log(f"wrote tables to {args.tables_out}")
    print("\n" + md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
