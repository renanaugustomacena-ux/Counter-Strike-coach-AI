#!/usr/bin/env python3
"""Episode-length census of ``playertickstate`` (read-only) for the JEPA v2 window-length decision.

Episode = maximal run of rows of one ``(demo_name, player_name, round_number)`` whose ``tick``
values are strictly consecutive (``tick[i+1] - tick[i] == 1``), after collapsing duplicate ticks.
This is the definition of Parte I §7.3 / Parte III §3 (D-22 structural). The window today is
48 token = 384 tick (6 s); the alternatives under discussion are 96 = 768 and 128 = 1024 tick.

What it measures, on real rows of the monolith:

  (a) histogram of episode lengths (bins in seconds at 64 Hz), as fraction of episodes and of ticks
  (b) for L in {384, 768, 1024, 1536, 2048} tick: fraction of episodes with length >= L, fraction
      of all ticks lying in such episodes, expected number of non-overlapping windows per episode
  (c) tick-gap statistics: fraction of consecutive rows whose tick difference != 1, gap-size
      distribution (1, 2-7, 8-63, 64+), and how many episode breaks are due only to a 2-7 gap
      (what a tolerance of up to 7 missing ticks would recover)
  (d) episodes where the player is dead (health <= 0) for > 50 % of the ticks, and the length
      distribution of the alive-only prefix (episode start .. first health <= 0)
  (e) duplicate rows: the same tick twice for the same (demo, player)

Round semantics (``backend/data_sources/round_context.py:201-221``): ``round_number`` is assigned
by backward ``merge_asof`` on the ``round_freeze_end`` tick, warmup ticks fall into round 1, and a
round's rows run until the next ``round_freeze_end``; an episode therefore also contains the
post-round period and the freeze time of the following round. Variants exclude round 1 for that
reason. Tick rate is assumed 64 Hz (Parte II §12.2, T1: median 64.0).

Access pattern identical to ``tools/verify_math_claims.py``: (demo, player) pairs from
``roundstats``, raw spelling via ``resolve_stored_name`` (D8), then a single indexed, LIMIT-bounded
query per pair on ``ix_pts_player_demo``. Never writes, never opens the DB without ``mode=ro``.

Usage (repo root, CPU only):
  CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/bin/python tools/measure_episode_lengths.py \\
      --demos 40 --players-per-demo 3 --ticks-per-pair 120000 --seed 0 \\
      --out docs/research/episode_lengths_2026-09-05.json
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.verify_math_claims import _log, open_ro, resolve_stored_name  # noqa: E402

TICK_RATE = 64.0
BIN_EDGES_S: List[float] = [0, 1, 2, 4, 6, 8, 12, 16, 24, 40, 60, 115]
BIN_LABELS: List[str] = [
    "<1",
    "1-2",
    "2-4",
    "4-6",
    "6-8",
    "8-12",
    "12-16",
    "16-24",
    "24-40",
    "40-60",
    "60-115",
    ">115",
]
WINDOW_LENGTHS: Tuple[int, ...] = (384, 768, 1024, 1536, 2048)
GAP_TOLERANCE = 7  # ticks; "2-7" gap class
DEAD_FRACTION_THRESHOLD = 0.5
PTS_QUERY = (
    "SELECT tick, round_number, health FROM playertickstate "
    "WHERE demo_name = ? AND player_name = ? ORDER BY tick LIMIT ?"
)


# --------------------------------------------------------------------------- selection / fetch


def select_demo_players(
    con: sqlite3.Connection, n_demos: int, per_demo: int, seed: int
) -> List[Tuple[str, str]]:
    """Same population as verify_math_claims.select_pairs (roundstats, >= 12 rounds), but a fixed
    number of demos with up to ``per_demo`` players each."""
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
    for demo in demos[:n_demos]:
        players = sorted(by_demo[demo])
        rng.shuffle(players)
        pairs.extend((demo, p) for p in players[:per_demo])
    return pairs


def fetch_thr(
    con: sqlite3.Connection, demo: str, stored: str, limit: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """(tick, round_number, health) ordered by tick; NULL health counted and mapped to 0."""
    rows = con.execute(PTS_QUERY, (demo, stored, limit)).fetchall()
    if not rows:
        empty = np.zeros(0, dtype=np.int64)
        return empty, empty, empty, 0
    n_null_health = sum(1 for r in rows if r[2] is None)
    tick = np.fromiter((int(r[0]) for r in rows), dtype=np.int64, count=len(rows))
    rnd = np.fromiter(
        (int(r[1]) if r[1] is not None else 1 for r in rows), dtype=np.int64, count=len(rows)
    )
    hp = np.fromiter(
        (int(r[2]) if r[2] is not None else 0 for r in rows), dtype=np.int64, count=len(rows)
    )
    return tick, rnd, hp, n_null_health


# --------------------------------------------------------------------------- segmentation


def dedupe_ticks(
    tick: np.ndarray, rnd: np.ndarray, hp: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Collapse rows that repeat the previous tick (input is sorted by tick). Returns n_duplicates."""
    if len(tick) == 0:
        return tick, rnd, hp, 0
    keep = np.ones(len(tick), dtype=bool)
    keep[1:] = tick[1:] != tick[:-1]
    return tick[keep], rnd[keep], hp[keep], int((~keep).sum())


def gap_census(tick: np.ndarray, rnd: np.ndarray, hp: np.ndarray) -> Dict[str, object]:
    """Counts over consecutive (deduped) rows: tick difference classes, split by round change.
    Also the context of within-round gaps: health before/after, offset from the round change,
    and whether the run after the gap continues up to the next round change."""
    if len(tick) < 2:
        return {}
    d = np.diff(tick)
    same_round = rnd[1:] == rnd[:-1]
    g2_7 = (d >= 2) & (d <= GAP_TOLERANCE)
    g8_63 = (d >= 8) & (d <= 63)
    g64 = d >= 64
    within = (d != 1) & same_round
    # round-change start indices (row index where a new round_number begins), plus pair start
    starts = np.concatenate([[0], np.nonzero(~same_round)[0] + 1])
    idx = np.nonzero(within)[0]  # gap between row idx and idx+1
    seg_start = starts[np.searchsorted(starts, idx, side="right") - 1]
    offset_ticks = tick[idx] - tick[seg_start]
    # does the run after the gap continue (with diff==1) up to the next round change / pair end?
    brk_any = np.nonzero((d != 1) | ~same_round)[0]
    next_brk_pos = np.searchsorted(brk_any, idx, side="right")
    next_brk = np.where(
        next_brk_pos < len(brk_any), brk_any[np.minimum(next_brk_pos, len(brk_any) - 1)], len(d)
    )
    next_is_round_change = np.where(
        next_brk < len(d), ~same_round[np.minimum(next_brk, len(d) - 1)], True
    )
    after_len = tick[np.minimum(next_brk, len(tick) - 1)] - tick[idx + 1] + 1
    return {
        "n_diffs": int(len(d)),
        "diff_eq_1": int((d == 1).sum()),
        "gap_2_7": int(g2_7.sum()),
        "gap_8_63": int(g8_63.sum()),
        "gap_64_plus": int(g64.sum()),
        "round_changes": int((~same_round).sum()),
        "round_changes_with_gap": int(((d != 1) & ~same_round).sum()),
        "within_round_gap_2_7": int((g2_7 & same_round).sum()),
        "within_round_gap_8_63": int((g8_63 & same_round).sum()),
        "within_round_gap_64_plus": int((g64 & same_round).sum()),
        "max_gap": int(d.max()),
        "within_gap_dead_before": int((hp[idx] <= 0).sum()),
        "within_gap_alive_before": int((hp[idx] > 0).sum()),
        "within_gap_respawn_across": int(((hp[idx] <= 0) & (hp[idx + 1] > 0)).sum()),
        "within_gap_death_across": int(((hp[idx] > 0) & (hp[idx + 1] <= 0)).sum()),
        "within_gap_next_run_reaches_round_change": int(next_is_round_change.sum()),
        "_offsets": offset_ticks.astype(np.int64),
        "_after_len": after_len.astype(np.int64),
        "_gap_sizes": d[idx].astype(np.int64),
    }


def split_episodes(tick: np.ndarray, rnd: np.ndarray, tol: int) -> Tuple[np.ndarray, np.ndarray]:
    """Start/end row indices of episodes. tol=1: strict (break when diff != 1);
    tol=7: break only when diff > 7 (a 2-7 gap is bridged). Round changes always break."""
    if len(tick) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    d = np.diff(tick)
    brk = (d > tol) | (rnd[1:] != rnd[:-1])
    starts = np.concatenate([[0], np.nonzero(brk)[0] + 1]).astype(np.int64)
    ends = np.concatenate([starts[1:], [len(tick)]]).astype(np.int64)
    return starts, ends


def episode_records(
    tick: np.ndarray,
    rnd: np.ndarray,
    hp: np.ndarray,
    starts: np.ndarray,
    ends: np.ndarray,
    censored_last: bool,
) -> Dict[str, np.ndarray]:
    """Per-episode arrays: span length in ticks, round, dead fraction, alive prefix, censoring."""
    n = len(starts)
    length = np.zeros(n, dtype=np.int64)
    rounds = np.zeros(n, dtype=np.int64)
    dead_frac = np.zeros(n, dtype=np.float64)
    alive_prefix = np.zeros(n, dtype=np.int64)
    died = np.zeros(n, dtype=bool)
    for i, (s, e) in enumerate(zip(starts, ends)):
        length[i] = int(tick[e - 1] - tick[s] + 1)  # == e - s for strict episodes
        rounds[i] = int(rnd[s])
        dead = hp[s:e] <= 0
        dead_frac[i] = float(dead.mean())
        if dead.any():
            died[i] = True
            first_dead = int(np.argmax(dead))
            alive_prefix[i] = int(tick[s + first_dead] - tick[s]) if first_dead > 0 else 0
        else:
            alive_prefix[i] = length[i]
    censored = np.zeros(n, dtype=bool)
    if censored_last and n:
        censored[-1] = True
    # head = episode begins at a round change (or at the first fetched row): the live phase
    # starts here (round_freeze_end). tail = begins after a within-round gap.
    head = np.ones(n, dtype=bool)
    ends_at_round_change = np.ones(n, dtype=bool)
    for i, (s, e) in enumerate(zip(starts, ends)):
        head[i] = s == 0 or rnd[s - 1] != rnd[s]
        ends_at_round_change[i] = e == len(rnd) or rnd[e] != rnd[e - 1]
    return {
        "length": length,
        "round": rounds,
        "dead_frac": dead_frac,
        "alive_prefix": alive_prefix,
        "died": died,
        "censored": censored,
        "head": head,
        "ends_at_round_change": ends_at_round_change,
    }


# --------------------------------------------------------------------------- statistics


def _bin_edges_ticks() -> List[int]:
    return [int(round(s * TICK_RATE)) for s in BIN_EDGES_S]


def histogram(lengths: np.ndarray) -> List[dict]:
    edges = _bin_edges_ticks() + [1 << 62]
    total_ticks = int(lengths.sum()) if len(lengths) else 0
    out = []
    for i, label in enumerate(BIN_LABELS):
        lo, hi = edges[i], edges[i + 1]
        m = (lengths >= lo) & (lengths < hi)
        out.append(
            {
                "bin_s": label,
                "lo_ticks": lo,
                "hi_ticks": None if hi >= (1 << 62) else hi,
                "n_episodes": int(m.sum()),
                "frac_episodes": float(m.mean()) if len(lengths) else 0.0,
                "n_ticks": int(lengths[m].sum()),
                "frac_ticks": float(lengths[m].sum() / total_ticks) if total_ticks else 0.0,
            }
        )
    return out


def feasibility(lengths: np.ndarray) -> List[dict]:
    total_ticks = int(lengths.sum()) if len(lengths) else 0
    out = []
    for L in WINDOW_LENGTHS:
        ge = lengths >= L
        windows = lengths // L
        out.append(
            {
                "L_ticks": L,
                "L_tokens": L // 8,
                "L_seconds": L / TICK_RATE,
                "frac_episodes_ge_L": float(ge.mean()) if len(lengths) else 0.0,
                "n_episodes_ge_L": int(ge.sum()),
                "frac_ticks_in_episodes_ge_L": (
                    float(lengths[ge].sum() / total_ticks) if total_ticks else 0.0
                ),
                "expected_nonoverlapping_windows_per_episode": (
                    float(windows.mean()) if len(lengths) else 0.0
                ),
                "total_nonoverlapping_windows": int(windows.sum()),
                "frac_ticks_covered_by_nonoverlapping_windows": (
                    float((windows * L).sum() / total_ticks) if total_ticks else 0.0
                ),
                "windows_per_million_ticks": (
                    float(windows.sum() / total_ticks * 1e6) if total_ticks else 0.0
                ),
            }
        )
    return out


def quantiles(lengths: np.ndarray) -> dict:
    if len(lengths) == 0:
        return {"n": 0}
    q = np.percentile(lengths, [10, 25, 50, 75, 90])
    return {
        "n": int(len(lengths)),
        "total_ticks": int(lengths.sum()),
        "mean_ticks": float(lengths.mean()),
        "p10_ticks": float(q[0]),
        "p25_ticks": float(q[1]),
        "median_ticks": float(q[2]),
        "p75_ticks": float(q[3]),
        "p90_ticks": float(q[4]),
        "min_ticks": int(lengths.min()),
        "max_ticks": int(lengths.max()),
        "mean_s": float(lengths.mean() / TICK_RATE),
        "median_s": float(q[2] / TICK_RATE),
        "p10_s": float(q[0] / TICK_RATE),
        "p90_s": float(q[4] / TICK_RATE),
    }


def variant(lengths: np.ndarray, description: str) -> dict:
    return {
        "description": description,
        "summary": quantiles(lengths),
        "histogram": histogram(lengths),
        "feasibility": feasibility(lengths),
    }


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# --------------------------------------------------------------------------- main


def concat(records: List[Dict[str, np.ndarray]], key: str) -> np.ndarray:
    if not records:
        return np.zeros(0, dtype=np.int64)
    return np.concatenate([r[key] for r in records])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--demos", type=int, default=40)
    ap.add_argument("--players-per-demo", type=int, default=3)
    ap.add_argument("--ticks-per-pair", type=int, default=120_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--max-minutes", type=float, default=15.0, help="stop fetching new pairs after this"
    )
    ap.add_argument(
        "--out", type=Path, default=REPO / "docs/research/episode_lengths_2026-09-05.json"
    )
    args = ap.parse_args()

    t0 = time.time()
    con = open_ro()
    _log("DB opened read-only (mode=ro, query_only=1)")
    pairs = select_demo_players(con, args.demos, args.players_per_demo, args.seed)
    _log(
        f"selected {len(pairs)} (demo, player) pairs over {len({d for d, _ in pairs})} demos, seed={args.seed}"
    )

    strict: List[Dict[str, np.ndarray]] = []
    tolerant: List[Dict[str, np.ndarray]] = []
    gaps_total: Dict[str, int] = defaultdict(int)
    gap_arrays: Dict[str, List[np.ndarray]] = defaultdict(list)
    per_pair: List[dict] = []
    n_resolved = n_unresolved = n_censored_pairs = 0
    total_rows = total_dups = total_null_health = 0
    pairs_with_dups = 0

    for k, (demo, player) in enumerate(pairs, 1):
        if (time.time() - t0) / 60.0 > args.max_minutes:
            _log(f"time budget {args.max_minutes} min reached after {k - 1} pairs — stopping fetch")
            break
        stored = resolve_stored_name(con, demo, player)
        if stored is None:
            n_unresolved += 1
            _log(f"[{k}/{len(pairs)}] D8: no rows for {demo!r}/{player!r} — skipped")
            continue
        t1 = time.time()
        tick, rnd, hp, n_null = fetch_thr(con, demo, stored, args.ticks_per_pair)
        if len(tick) == 0:
            n_unresolved += 1
            _log(f"[{k}/{len(pairs)}] no rows for {demo!r}/{stored!r} — skipped")
            continue
        n_resolved += 1
        total_rows += len(tick)
        total_null_health += n_null
        censored = len(tick) >= args.ticks_per_pair
        n_censored_pairs += int(censored)
        tick, rnd, hp, n_dup = dedupe_ticks(tick, rnd, hp)
        total_dups += n_dup
        pairs_with_dups += int(n_dup > 0)
        for key, val in gap_census(tick, rnd, hp).items():
            if key.startswith("_"):
                gap_arrays[key].append(val)
            elif key == "max_gap":
                gaps_total[key] = max(gaps_total[key], val)
            else:
                gaps_total[key] += val
        s1, e1 = split_episodes(tick, rnd, 1)
        s7, e7 = split_episodes(tick, rnd, GAP_TOLERANCE)
        rec1 = episode_records(tick, rnd, hp, s1, e1, censored)
        rec7 = episode_records(tick, rnd, hp, s7, e7, censored)
        strict.append(rec1)
        tolerant.append(rec7)
        per_pair.append(
            {
                "demo": demo,
                "player_roundstats": player,
                "player_stored": stored,
                "rows": int(len(tick) + n_dup),
                "duplicates": n_dup,
                "null_health": n_null,
                "tick_first": int(tick[0]),
                "tick_last": int(tick[-1]),
                "rounds_seen": int(len(np.unique(rnd))),
                "episodes_strict": int(len(s1)),
                "episodes_tol7": int(len(s7)),
                "censored_last_episode": censored,
            }
        )
        _log(
            f"[{k}/{len(pairs)}] {demo[:48]!r}/{stored!r}: {len(tick) + n_dup} rows in "
            f"{time.time() - t1:.1f}s, rounds {len(np.unique(rnd))}, episodes {len(s1)} "
            f"(tol7 {len(s7)}), dups {n_dup}, censored={censored}"
        )

    # ---- assemble
    L = concat(strict, "length")
    R = concat(strict, "round")
    C = concat(strict, "censored")
    D = concat(strict, "dead_frac")
    A = concat(strict, "alive_prefix")
    died = concat(strict, "died")
    L7 = concat(tolerant, "length")
    C7 = concat(tolerant, "censored")
    R7 = concat(tolerant, "round")

    H = concat(strict, "head")
    E = concat(strict, "ends_at_round_change")
    ok = ~C
    ok_r = ok & (R != 1)
    ok7 = ~C7
    ok7_r = ok7 & (R7 != 1)

    offsets = (
        np.concatenate(gap_arrays["_offsets"])
        if gap_arrays["_offsets"]
        else np.zeros(0, dtype=np.int64)
    )
    after_len = (
        np.concatenate(gap_arrays["_after_len"])
        if gap_arrays["_after_len"]
        else np.zeros(0, dtype=np.int64)
    )
    gap_sizes = (
        np.concatenate(gap_arrays["_gap_sizes"])
        if gap_arrays["_gap_sizes"]
        else np.zeros(0, dtype=np.int64)
    )
    small = (gap_sizes >= 2) & (gap_sizes <= GAP_TOLERANCE)
    gap_context = {
        "n_within_round_gaps": int(len(gap_sizes)),
        "gap_size_counts": (
            {str(int(g)): int(c) for g, c in zip(*np.unique(gap_sizes, return_counts=True))}
            if len(gap_sizes)
            else {}
        ),
        "offset_from_round_change_s": quantiles(offsets) if len(offsets) else {"n": 0},
        "offset_from_round_change_s_gap_2_7": (
            quantiles(offsets[small]) if small.any() else {"n": 0}
        ),
        "run_after_gap_length": quantiles(after_len) if len(after_len) else {"n": 0},
        "run_after_gap_length_gap_2_7": quantiles(after_len[small]) if small.any() else {"n": 0},
        "note": "offset = tick of the row before the gap minus tick of the current round change "
        "(quantiles in ticks and seconds); run_after_gap = strict run length that follows the gap",
    }

    n_diffs = max(gaps_total.get("n_diffs", 0), 1)
    gaps = {
        **{k: int(v) for k, v in gaps_total.items()},
        "within_round_gap_context": gap_context,
        "frac_diff_ne_1": float(1.0 - gaps_total.get("diff_eq_1", 0) / n_diffs),
        "frac_diff_ne_1_excluding_round_changes": float(
            (
                gaps_total.get("gap_2_7", 0)
                + gaps_total.get("gap_8_63", 0)
                + gaps_total.get("gap_64_plus", 0)
                - gaps_total.get("round_changes_with_gap", 0)
            )
            / n_diffs
        ),
        "gap_size_distribution_of_diffs": {
            "1": float(gaps_total.get("diff_eq_1", 0) / n_diffs),
            "2-7": float(gaps_total.get("gap_2_7", 0) / n_diffs),
            "8-63": float(gaps_total.get("gap_8_63", 0) / n_diffs),
            "64+": float(gaps_total.get("gap_64_plus", 0) / n_diffs),
        },
        "gap_size_distribution_of_gaps_only": (
            lambda g: {
                "2-7": float(gaps_total.get("gap_2_7", 0) / g),
                "8-63": float(gaps_total.get("gap_8_63", 0) / g),
                "64+": float(gaps_total.get("gap_64_plus", 0) / g),
            }
        )(
            max(
                1,
                gaps_total.get("gap_2_7", 0)
                + gaps_total.get("gap_8_63", 0)
                + gaps_total.get("gap_64_plus", 0),
            )
        ),
        "episodes_strict": int(len(L)),
        "episodes_tol7": int(len(L7)),
        "episode_breaks_due_only_to_gap_2_7": int(gaps_total.get("within_round_gap_2_7", 0)),
        "frac_strict_episodes_created_by_gap_2_7": float(
            gaps_total.get("within_round_gap_2_7", 0) / max(1, len(L))
        ),
        "note": "within_round_gap_* count breaks inside one round_number; round_changes_with_gap are "
        "boundaries that coincide with a round change (an episode boundary anyway).",
    }

    dead_majority = D > DEAD_FRACTION_THRESHOLD
    death = {
        "threshold_dead_fraction": DEAD_FRACTION_THRESHOLD,
        "n_episodes": int(ok.sum()),
        "frac_episodes_dead_majority": float(dead_majority[ok].mean()) if ok.any() else 0.0,
        "frac_episodes_with_any_death": float(died[ok].mean()) if ok.any() else 0.0,
        "frac_ticks_dead_overall": float((D[ok] * L[ok]).sum() / max(1, L[ok].sum())),
        "frac_ticks_in_alive_prefix": float(A[ok].sum() / max(1, L[ok].sum())),
        "alive_prefix_all_episodes": variant(
            A[ok],
            "alive-only prefix (start .. first health<=0, or whole episode if never dead), strict, uncensored, all rounds",
        ),
        "alive_prefix_excl_round1": variant(
            A[ok_r], "alive-only prefix, strict, uncensored, round_number != 1"
        ),
        "alive_prefix_head_excl_round1": variant(
            A[ok_r & H],
            "alive-only prefix of HEAD episodes (start at round_freeze_end), uncensored, round != 1: the usable live phase",
        ),
        "alive_prefix_head_with_death_excl_round1": variant(
            A[ok_r & H & died],
            "alive-only prefix of head episodes in which the player dies, round != 1",
        ),
        "alive_prefix_episodes_with_death": variant(
            A[ok & died],
            "alive-only prefix restricted to episodes in which health<=0 occurs (live phase until death)",
        ),
        "alive_prefix_episodes_without_death": variant(
            A[ok & ~died],
            "episodes in which the player never has health<=0 (survivors: includes post-round and next freeze time)",
        ),
    }

    dups = {
        "duplicate_rows": int(total_dups),
        "rows_fetched": int(total_rows),
        "frac_duplicate_rows": float(total_dups / max(1, total_rows)),
        "pairs_with_duplicates": int(pairs_with_dups),
        "pairs_measured": int(n_resolved),
        "null_health_rows": int(total_null_health),
    }

    result = {
        "meta": {
            "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_sha": _git_sha(),
            "script": "tools/measure_episode_lengths.py",
            "db": "Programma_CS2_RENAN/backend/storage/database.db (mode=ro, query_only=1)",
            "seed": args.seed,
            "demos_requested": args.demos,
            "players_per_demo": args.players_per_demo,
            "ticks_per_pair_limit": args.ticks_per_pair,
            "pairs_selected": len(pairs),
            "pairs_measured": n_resolved,
            "pairs_unresolved_D8": n_unresolved,
            "demos_measured": len({p["demo"] for p in per_pair}),
            "pairs_hitting_limit": n_censored_pairs,
            "rows_fetched": total_rows,
            "tick_rate_assumed_hz": TICK_RATE,
            "episode_definition": "maximal run of one (demo, player, round_number) with tick[i+1]-tick[i]==1 after dropping duplicate ticks; last episode of a pair that hit the LIMIT is censored and excluded from length statistics",
            "round_semantics": "round_number anchored on round_freeze_end (round_context.py:201-221); warmup -> round 1; a round's rows extend to the next round_freeze_end (post-round + next freeze time included)",
            "bins_seconds": BIN_LABELS,
            "bin_edges_ticks": _bin_edges_ticks(),
            "window_lengths_ticks": list(WINDOW_LENGTHS),
            "runtime_seconds": None,
        },
        "a_b_episode_lengths": {
            "strict_all": variant(L[ok], "strict episodes (diff==1), uncensored, all rounds"),
            "strict_excl_round1": variant(
                L[ok_r],
                "strict episodes, uncensored, round_number != 1 (drops warmup-contaminated round 1)",
            ),
            "tol7_all": variant(
                L7[ok7],
                "episodes bridging gaps of 2-7 ticks (length = tick span), uncensored, all rounds",
            ),
            "tol7_excl_round1": variant(
                L7[ok7_r], "tolerance-7 episodes, uncensored, round_number != 1"
            ),
            "strict_head_excl_round1": variant(
                L[ok_r & H],
                "strict episodes that START at a round change (live phase from round_freeze_end), uncensored, round != 1",
            ),
            "strict_tail_excl_round1": variant(
                L[ok_r & ~H],
                "strict episodes that start AFTER a within-round gap (run after the gap), uncensored, round != 1",
            ),
            "censored_episodes_excluded": int(C.sum()),
            "round1_episodes": int((R == 1).sum()),
            "head_episodes": int(H.sum()),
            "tail_episodes": int((~H).sum()),
            "head_episodes_ending_at_round_change": int((H & E).sum()),
            "tail_episodes_ending_at_round_change": int((~H & E).sum()),
        },
        "c_gaps": gaps,
        "d_death": death,
        "e_duplicates": dups,
        "per_pair": per_pair,
    }
    result["meta"]["runtime_seconds"] = round(time.time() - t0, 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    _log(
        f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KB) in {result['meta']['runtime_seconds']} s"
    )

    fa = result["a_b_episode_lengths"]["strict_all"]["feasibility"]
    for row in fa:
        _log(
            f"L={row['L_ticks']:5d} ({row['L_tokens']:3d} tok): episodes>=L {row['frac_episodes_ge_L']:.3f}, "
            f"ticks in them {row['frac_ticks_in_episodes_ge_L']:.3f}, windows/episode {row['expected_nonoverlapping_windows_per_episode']:.2f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
