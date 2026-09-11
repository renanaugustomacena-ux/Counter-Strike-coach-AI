#!/usr/bin/env python
"""Task M4 (2026-09-05, read-only): side-label availability and player-name join coverage (D8).

Measures, against the production monolith opened strictly read-only:

  (a) roundstats.side: value histogram, NULL/empty rate, constancy per (demo, round, player),
      half-time flips per (demo, player), fraction of demos where every player has both sides.
  (b) roundstats.player_name (normalized at ingestion) vs playermatchstats.player_name (raw
      spelling, same source as playertickstate) under three matchings: exact, strip().lower(),
      NFKC + drop Cf + strip().casefold(); per-demo and global coverage; residuals with repr().
      Plus, for every (demo, player) pair, an indexed existence probe in playertickstate
      (ix_pts_player_demo) so the true label<->tick join coverage is measured on all 225 demos.
  (c) Proxy check on 15 demos (seed 0): SELECT DISTINCT player_name FROM playertickstate WHERE
      demo_name=? (ix_playertickstate_demo_name) compared with the playermatchstats set.
  (d) steamid as alternative key: playertickstate.steamid sampled per demo (bounded LIMIT slices
      on ix_tick_demo_tick), playermatchstats.steamid fill rate.
  (e) Rows touched by the D8 migration UPDATE, estimated without scanning playertickstate:
      (# playermatchstats rows whose name changes under lower(trim())) x (rows per player-match,
      measured with bounded COUNT(*) on ix_pts_player_demo for a few pairs).

Never writes to the database. Every long query runs under a wall-clock deadline (progress
handler) and every phase has a budget; the JSON records what was skipped.

Usage (CPU only, from the repo root):
    CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/bin/python tools/measure_name_join_coverage.py
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import statistics
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
DB_LINK = REPO / "Programma_CS2_RENAN/backend/storage/database.db"
OUT_JSON = REPO / "docs/research/name_join_coverage_2026-09-05.json"

MR12_HALF_FLIP_ROUND = 13
REGULATION_ROUNDS = 24
TEAM_SIZE = 5

T0 = time.monotonic()


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] +{time.monotonic() - T0:7.1f}s {msg}", flush=True)


# --------------------------------------------------------------------------------------------
# DB access (read-only, bounded)
# --------------------------------------------------------------------------------------------


def open_ro() -> Tuple[sqlite3.Connection, str]:
    path = os.path.realpath(DB_LINK)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=120)
    con.execute("PRAGMA query_only=1")
    return con, path


class Bounded:
    """Run one query under a wall-clock deadline; returns None when interrupted."""

    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con
        self.timeouts = 0

    def rows(self, sql: str, params: Sequence = (), seconds: float = 60.0) -> Optional[list]:
        t_end = time.monotonic() + seconds
        self.con.set_progress_handler(lambda: 1 if time.monotonic() > t_end else 0, 20000)
        try:
            return self.con.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            if "interrupt" in str(exc).lower():
                self.timeouts += 1
                return None
            raise
        finally:
            self.con.set_progress_handler(None, 0)

    def plan(self, sql: str, params: Sequence = ()) -> List[str]:
        return [r[3] for r in self.con.execute("EXPLAIN QUERY PLAN " + sql, params)]


# --------------------------------------------------------------------------------------------
# Normalizers (matching 1/2/3 of the task)
# --------------------------------------------------------------------------------------------


def norm_exact(s: str) -> str:
    return s


def norm_strip_lower(s: str) -> str:
    return s.strip().lower()


def norm_nfkc_casefold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = "".join(ch for ch in s if not unicodedata.category(ch).startswith("Cf"))
    return s.strip().casefold()


MATCHINGS: List[Tuple[str, Callable[[str], str]]] = [
    ("exact", norm_exact),
    ("strip_lower", norm_strip_lower),
    ("nfkc_cf_strip_casefold", norm_nfkc_casefold),
]


def name_traits(s: str) -> Dict[str, bool]:
    return {
        "has_upper": any(ch.isupper() for ch in s),
        "has_leading_or_trailing_ws": s != s.strip(),
        "has_inner_ws": any(ch.isspace() for ch in s.strip()),
        "has_non_ascii": any(ord(ch) > 127 for ch in s),
        "has_format_char_Cf": any(unicodedata.category(ch).startswith("Cf") for ch in s),
        "nfkc_changes": unicodedata.normalize("NFKC", s) != s,
        "lower_ne_casefold": s.lower() != s.casefold(),
    }


# --------------------------------------------------------------------------------------------
# (a) side
# --------------------------------------------------------------------------------------------


def phase_side(con: sqlite3.Connection) -> dict:
    _log("(a) roundstats.side")
    rows = con.execute(
        "SELECT demo_name, round_number, player_name, side FROM roundstats "
        "ORDER BY demo_name, player_name, round_number"
    ).fetchall()
    n = len(rows)
    side_counts = Counter(("<NULL>" if s is None else s) for _, _, _, s in rows)
    n_null_or_empty = sum(1 for _, _, _, s in rows if s is None or str(s).strip() == "")

    per_key: Dict[Tuple[str, int, str], List[str]] = defaultdict(list)
    per_dp: Dict[Tuple[str, str], List[Tuple[int, str]]] = defaultdict(list)
    per_dr: Dict[Tuple[str, int], Counter] = defaultdict(Counter)
    demo_max_round: Dict[str, int] = defaultdict(int)
    for demo, rnd, player, side in rows:
        per_key[(demo, rnd, player)].append(side)
        per_dp[(demo, player)].append((rnd, side))
        per_dr[(demo, rnd)][side] += 1
        demo_max_round[demo] = max(demo_max_round[demo], rnd)

    multi_row = sum(1 for v in per_key.values() if len(v) > 1)
    conflicting = sum(1 for v in per_key.values() if len(set(v)) > 1)

    first_flip = Counter()
    all_flip_rounds = Counter()
    dp_both = 0
    dp_total = 0
    demos_all_both: Set[str] = set()
    demos_not_all_both: Dict[str, List[str]] = defaultdict(list)
    rounds_missing = 0
    for (demo, player), seq in per_dp.items():
        seq.sort()
        dp_total += 1
        sides = {s for _, s in seq}
        if len(sides) >= 2:
            dp_both += 1
        else:
            demos_not_all_both[demo].append(player)
        expected_rounds = set(range(1, demo_max_round[demo] + 1))
        rounds_missing += len(expected_rounds - {r for r, _ in seq})
        flips = [r for (r0, s0), (r, s) in zip(seq, seq[1:]) if s != s0]
        if flips:
            first_flip[flips[0]] += 1
            all_flip_rounds.update(flips)
    demos = sorted(demo_max_round)
    demos_all_both = {d for d in demos if d not in demos_not_all_both}

    balanced_5v5 = sum(
        1 for c in per_dr.values() if c.get("CT", 0) == TEAM_SIZE and c.get("T", 0) == TEAM_SIZE
    )
    reg_demos = [d for d in demos if demo_max_round[d] <= REGULATION_ROUNDS]
    ot_demos = [d for d in demos if demo_max_round[d] > REGULATION_ROUNDS]
    ot_flip_rounds = Counter()
    for (demo, _), seq in per_dp.items():
        if demo_max_round[demo] > REGULATION_ROUNDS:
            seq.sort()
            ot_flip_rounds.update(
                r for (r0, s0), (r, s) in zip(seq, seq[1:]) if s != s0 and r > REGULATION_ROUNDS
            )

    rs_names = con.execute("SELECT DISTINCT player_name FROM roundstats").fetchall()
    rs_not_normalized = [repr(x) for (x,) in rs_names if x != x.strip().lower()]

    out = {
        "rows": n,
        "demos": len(demos),
        "side_values": dict(side_counts),
        "null_or_empty_rows": n_null_or_empty,
        "null_or_empty_rate": n_null_or_empty / n if n else None,
        "groups_demo_round_player": len(per_key),
        "groups_with_multiple_rows": multi_row,
        "groups_with_conflicting_side": conflicting,
        "demo_round_groups": len(per_dr),
        "demo_round_groups_exactly_5CT_5T": balanced_5v5,
        "demo_player_pairs": dp_total,
        "demo_player_pairs_with_both_sides": dp_both,
        "demo_player_pairs_with_both_sides_frac": dp_both / dp_total if dp_total else None,
        "demos_where_every_player_has_both_sides": len(demos_all_both),
        "demos_where_every_player_has_both_sides_frac": (
            len(demos_all_both) / len(demos) if demos else None
        ),
        "demos_with_a_single_side_player": {d: v for d, v in demos_not_all_both.items()},
        "rounds_missing_for_some_player": rounds_missing,
        "first_flip_round_histogram": {str(k): v for k, v in sorted(first_flip.items())},
        "all_flip_rounds_histogram": {str(k): v for k, v in sorted(all_flip_rounds.items())},
        "first_flip_at_round_13_frac_of_pairs": (
            first_flip.get(MR12_HALF_FLIP_ROUND, 0) / dp_total if dp_total else None
        ),
        "regulation_only_demos_max_round_le_24": len(reg_demos),
        "overtime_demos_max_round_gt_24": len(ot_demos),
        "overtime_flip_rounds_histogram": {str(k): v for k, v in sorted(ot_flip_rounds.items())},
        "max_round_histogram": {
            str(k): v for k, v in sorted(Counter(demo_max_round.values()).items())
        },
        "roundstats_distinct_names": len(rs_names),
        "roundstats_names_not_strip_lower": rs_not_normalized,
    }
    _log(
        f"    side={dict(side_counts)} null/empty={n_null_or_empty} conflicting={conflicting} "
        f"pairs_both_sides={dp_both}/{dp_total} demos_all_both={len(demos_all_both)}/{len(demos)} "
        f"first_flip@13={first_flip.get(13, 0)}"
    )
    return out


# --------------------------------------------------------------------------------------------
# (b) name alignment roundstats vs playermatchstats
# --------------------------------------------------------------------------------------------


def phase_names(con: sqlite3.Connection) -> Tuple[dict, Dict[str, Set[str]], Dict[str, Set[str]]]:
    _log("(b) roundstats.player_name vs playermatchstats.player_name")
    rs: Dict[str, Set[str]] = defaultdict(set)
    for demo, name in con.execute("SELECT DISTINCT demo_name, player_name FROM roundstats"):
        rs[demo].add(name)
    pms: Dict[str, Set[str]] = defaultdict(set)
    pms_rows = 0
    for demo, name in con.execute("SELECT demo_name, player_name FROM playermatchstats"):
        pms[demo].add(name)
        pms_rows += 1
    demos_rs, demos_pms = set(rs), set(pms)
    demos = sorted(demos_rs & demos_pms)

    per_demo: Dict[str, dict] = {}
    totals = {
        k: {
            "rs_matched": 0,
            "pms_matched": 0,
            "rs_total": 0,
            "pms_total": 0,
            "demos_full_rs_coverage": 0,
            "rs_key_collisions": 0,
            "pms_key_collisions": 0,
        }
        for k, _ in MATCHINGS
    }
    residual: Dict[str, List[dict]] = {k: [] for k, _ in MATCHINGS}
    for demo in demos:
        rec: dict = {"n_rs": len(rs[demo]), "n_pms": len(pms[demo])}
        for key, fn in MATCHINGS:
            pms_keys = Counter(fn(x) for x in pms[demo])
            rs_keys = Counter(fn(x) for x in rs[demo])
            rs_m = sum(1 for x in rs[demo] if fn(x) in pms_keys)
            pms_m = sum(1 for x in pms[demo] if fn(x) in rs_keys)
            rec[key] = {"rs_matched": rs_m, "pms_matched": pms_m}
            t = totals[key]
            t["rs_matched"] += rs_m
            t["pms_matched"] += pms_m
            t["rs_total"] += len(rs[demo])
            t["pms_total"] += len(pms[demo])
            t["demos_full_rs_coverage"] += int(rs_m == len(rs[demo]))
            t["rs_key_collisions"] += sum(v - 1 for v in rs_keys.values() if v > 1)
            t["pms_key_collisions"] += sum(v - 1 for v in pms_keys.values() if v > 1)
            for x in sorted(rs[demo]):
                if fn(x) not in pms_keys:
                    residual[key].append({"demo": demo, "table": "roundstats", "name": repr(x)})
            for x in sorted(pms[demo]):
                if fn(x) not in rs_keys:
                    residual[key].append(
                        {"demo": demo, "table": "playermatchstats", "name": repr(x)}
                    )
        per_demo[demo] = rec

    # why exact fails: traits of the PMS raw names that differ from their strip().lower() form
    pms_all_names = sorted({x for s in pms.values() for x in s})
    rs_all_names = sorted({x for s in rs.values() for x in s})
    trait_counts = Counter()
    changed_names = [x for x in pms_all_names if x != x.strip().lower()]
    for x in changed_names:
        for k, v in name_traits(x).items():
            trait_counts[k] += int(v)
    # global distinct-name view (the one quoted in Parte III §2.4: 47/105 vs 109)
    pms_exact = set(pms_all_names)
    rs_unmatched_global_exact = [x for x in rs_all_names if x not in pms_exact]
    pms_by_norm3 = {norm_nfkc_casefold(x) for x in pms_all_names}
    rs_unmatched_global_norm3 = [
        repr(x) for x in rs_all_names if norm_nfkc_casefold(x) not in pms_by_norm3
    ]
    pms_by_norm2 = {norm_strip_lower(x) for x in pms_all_names}
    rs_unmatched_global_norm2 = [
        repr(x) for x in rs_all_names if norm_strip_lower(x) not in pms_by_norm2
    ]
    # names for which strip().lower() and NFKC/casefold disagree
    norm_disagree = [
        repr(x)
        for x in pms_all_names + rs_all_names
        if norm_strip_lower(x) != norm_nfkc_casefold(x)
    ]
    pms_extra_rows = {
        d: sorted(repr(x) for x in pms[d]) for d in demos if len(pms[d]) != len(rs[d])
    }

    out = {
        "demos_roundstats": len(demos_rs),
        "demos_playermatchstats": len(demos_pms),
        "demos_common": len(demos),
        "demos_only_roundstats": sorted(demos_rs - demos_pms),
        "demos_only_playermatchstats": sorted(demos_pms - demos_rs),
        "playermatchstats_rows": pms_rows,
        "roundstats_distinct_names_global": len(rs_all_names),
        "playermatchstats_distinct_names_global": len(pms_all_names),
        "global_distinct_rs_names_without_exact_match": len(rs_unmatched_global_exact),
        "global_distinct_rs_names_without_strip_lower_match": rs_unmatched_global_norm2,
        "global_distinct_rs_names_without_nfkc_casefold_match": rs_unmatched_global_norm3,
        "names_where_strip_lower_ne_nfkc_casefold": sorted(set(norm_disagree)),
        "pms_names_changed_by_strip_lower": len(changed_names),
        "pms_names_changed_by_strip_lower_traits": dict(trait_counts),
        "pms_names_changed_by_strip_lower_list": [repr(x) for x in changed_names],
        "demos_with_pms_count_ne_rs_count": pms_extra_rows,
        "coverage": {
            k: {
                **t,
                "rs_coverage": t["rs_matched"] / t["rs_total"] if t["rs_total"] else None,
                "pms_coverage": t["pms_matched"] / t["pms_total"] if t["pms_total"] else None,
                "demos_full_rs_coverage_frac": (
                    t["demos_full_rs_coverage"] / len(demos) if demos else None
                ),
            }
            for k, t in totals.items()
        },
        "residual_unmatched": {k: v for k, v in residual.items()},
        "per_demo": per_demo,
    }
    for k, t in out["coverage"].items():
        _log(
            f"    {k:24s} rs {t['rs_matched']}/{t['rs_total']} = {t['rs_coverage']:.4f}   "
            f"pms {t['pms_matched']}/{t['pms_total']} = {t['pms_coverage']:.4f}   "
            f"demos fully covered {t['demos_full_rs_coverage']}/{len(demos)}"
        )
    return out, rs, pms


# --------------------------------------------------------------------------------------------
# (b2) existence probes in playertickstate for every (demo, player) pair
# --------------------------------------------------------------------------------------------

EXISTS_SQL = "SELECT 1 FROM playertickstate WHERE demo_name = ? AND player_name = ? LIMIT 1"


def phase_tick_probes(
    bq: Bounded, rs: Dict[str, Set[str]], pms: Dict[str, Set[str]], budget_s: float
) -> dict:
    _log(f"(b2) indexed existence probes in playertickstate for all pairs (budget {budget_s:.0f}s)")
    plan = bq.plan(EXISTS_SQL, ("x", "y"))
    _log(f"    plan: {plan}")
    t_end = time.monotonic() + budget_s
    cache: Dict[Tuple[str, str], Optional[bool]] = {}
    lookups = 0

    def exists(demo: str, name: str) -> Optional[bool]:
        nonlocal lookups
        key = (demo, name)
        if key not in cache:
            if time.monotonic() > t_end:
                return None
            r = bq.rows(EXISTS_SQL, key, seconds=30)
            lookups += 1
            cache[key] = None if r is None else bool(r)
        return cache[key]

    demos = sorted(set(rs) & set(pms))
    pms_probe = Counter()
    rs_exact = Counter()
    rs_resolved = Counter()
    rs_resolved_ambiguous = 0
    rs_unresolved: List[dict] = []
    probes_done = 0
    for i, demo in enumerate(demos):
        pms_by_key: Dict[str, List[str]] = defaultdict(list)
        for raw in pms[demo]:
            pms_by_key[norm_nfkc_casefold(raw)].append(raw)
            e = exists(demo, raw)
            pms_probe["skipped" if e is None else ("hit" if e else "miss")] += 1
        for name in rs[demo]:
            e = exists(demo, name)
            rs_exact["skipped" if e is None else ("hit" if e else "miss")] += 1
            cands = pms_by_key.get(norm_nfkc_casefold(name), [])
            if len(cands) > 1:
                rs_resolved_ambiguous += 1
            hit: Optional[bool] = False
            for raw in cands:
                e2 = exists(demo, raw)
                if e2 is None:
                    hit = None
                    break
                if e2:
                    hit = True
                    break
            rs_resolved["skipped" if hit is None else ("hit" if hit else "miss")] += 1
            if hit is False:
                rs_unresolved.append(
                    {
                        "demo": demo,
                        "roundstats_name": repr(name),
                        "pms_candidates": [repr(c) for c in cands],
                    }
                )
        probes_done = i + 1
        if (i + 1) % 25 == 0:
            _log(f"    {i + 1}/{len(demos)} demos, {lookups} lookups, timeouts={bq.timeouts}")
        if time.monotonic() > t_end:
            _log(f"    budget exhausted after {i + 1} demos")
            break

    rs_total = sum(rs_exact.values())
    out = {
        "query": EXISTS_SQL,
        "query_plan": plan,
        "demos_probed": probes_done,
        "index_lookups": lookups,
        "lookup_timeouts": bq.timeouts,
        "pms_pairs": dict(pms_probe),
        "pms_pairs_with_ticks_frac": pms_probe["hit"]
        / max(1, pms_probe["hit"] + pms_probe["miss"]),
        "rs_pairs_exact_equality": dict(rs_exact),
        "rs_pairs_exact_equality_hit_frac": rs_exact["hit"]
        / max(1, rs_exact["hit"] + rs_exact["miss"]),
        "rs_pairs_resolved_via_pms_nfkc_casefold": dict(rs_resolved),
        "rs_pairs_resolved_hit_frac": rs_resolved["hit"]
        / max(1, rs_resolved["hit"] + rs_resolved["miss"]),
        "rs_pairs_resolution_ambiguous": rs_resolved_ambiguous,
        "rs_pairs_total_seen": rs_total,
        "rs_pairs_without_ticks_after_resolution": rs_unresolved,
    }
    _log(
        f"    pms {dict(pms_probe)}  rs exact {dict(rs_exact)}  rs resolved {dict(rs_resolved)}  "
        f"lookups={lookups} timeouts={bq.timeouts}"
    )
    return out


# --------------------------------------------------------------------------------------------
# (c) DISTINCT proxy check on 15 demos
# --------------------------------------------------------------------------------------------

DISTINCT_SQL = "SELECT DISTINCT player_name FROM playertickstate WHERE demo_name = ?"


def phase_distinct(
    bq: Bounded, demos15: List[str], pms: Dict[str, Set[str]], budget_s: float, per_query_s: float
) -> dict:
    _log(
        f"(c) DISTINCT player_name on {len(demos15)} demos (budget {budget_s:.0f}s, {per_query_s:.0f}s/query)"
    )
    plan = bq.plan(DISTINCT_SQL, ("x",))
    _log(f"    plan: {plan}")
    t_end = time.monotonic() + budget_s
    per_demo = []
    n_equal = n_done = n_timeout = 0
    for demo in demos15:
        if time.monotonic() > t_end:
            per_demo.append({"demo": demo, "status": "skipped_budget"})
            continue
        t = time.monotonic()
        r = bq.rows(DISTINCT_SQL, (demo,), seconds=per_query_s)
        dt = time.monotonic() - t
        if r is None:
            n_timeout += 1
            per_demo.append({"demo": demo, "status": "timeout", "seconds": round(dt, 2)})
            _log(f"    {demo}: TIMEOUT after {dt:.1f}s")
            continue
        pts = {x for (x,) in r}
        ref = pms[demo]
        eq = pts == ref
        n_done += 1
        n_equal += int(eq)
        per_demo.append(
            {
                "demo": demo,
                "status": "ok",
                "seconds": round(dt, 2),
                "n_pts": len(pts),
                "n_pms": len(ref),
                "equal": eq,
                "in_pts_not_pms": sorted(repr(x) for x in pts - ref),
                "in_pms_not_pts": sorted(repr(x) for x in ref - pts),
                "pts_names": sorted(repr(x) for x in pts),
            }
        )
        _log(f"    {demo}: {dt:.1f}s, {len(pts)} names, equal_to_pms={eq}")
    return {
        "query": DISTINCT_SQL,
        "query_plan": plan,
        "demos_sampled": demos15,
        "done": n_done,
        "equal": n_equal,
        "timeouts": n_timeout,
        "seconds_per_query": [d["seconds"] for d in per_demo if d.get("status") == "ok"],
        "per_demo": per_demo,
    }


# --------------------------------------------------------------------------------------------
# (d) steamid
# --------------------------------------------------------------------------------------------

BOUNDS_SQL = "SELECT MIN(tick), MAX(tick) FROM playertickstate WHERE demo_name = ?"
SLICE_SQL = (
    "SELECT player_name, steamid, typeof(steamid) FROM playertickstate "
    "WHERE demo_name = ? AND tick >= ? ORDER BY tick LIMIT ?"
)


def phase_steamid(
    con: sqlite3.Connection,
    bq: Bounded,
    demos15: List[str],
    pms: Dict[str, Set[str]],
    rows_per_demo: int,
    budget_s: float,
) -> dict:
    _log(
        f"(d) steamid: {rows_per_demo} sampled rows/demo on {len(demos15)} demos (budget {budget_s:.0f}s)"
    )
    pms_sid = con.execute(
        "SELECT COUNT(*), SUM(steamid IS NULL), SUM(steamid = 0), COUNT(DISTINCT steamid) FROM playermatchstats"
    ).fetchone()
    _log(
        f"    playermatchstats.steamid: rows={pms_sid[0]} null={pms_sid[1]} zero={pms_sid[2]} distinct={pms_sid[3]}"
    )
    _log(f"    slice plan: {bq.plan(SLICE_SQL, ('x', 0, 1))}")
    t_end = time.monotonic() + budget_s
    n_slices = 3
    per_slice = rows_per_demo // n_slices
    per_demo = []
    name_to_sids: Dict[str, Set[int]] = defaultdict(set)
    sid_to_names: Dict[int, Set[str]] = defaultdict(set)
    agg = Counter()
    for demo in demos15:
        if time.monotonic() > t_end:
            per_demo.append({"demo": demo, "status": "skipped_budget"})
            continue
        t = time.monotonic()
        b = bq.rows(BOUNDS_SQL, (demo,), seconds=30)
        if not b or b[0][0] is None:
            per_demo.append({"demo": demo, "status": "no_bounds"})
            continue
        tmin, tmax = b[0]
        starts = [tmin + int((tmax - tmin) * f) for f in (0.0, 0.5, 0.9)]
        rows: List[tuple] = []
        timed_out = False
        for s in starts:
            r = bq.rows(SLICE_SQL, (demo, s, per_slice), seconds=60)
            if r is None:
                timed_out = True
                break
            rows.extend(r)
        dt = time.monotonic() - t
        if timed_out:
            per_demo.append({"demo": demo, "status": "timeout", "seconds": round(dt, 2)})
            _log(f"    {demo}: TIMEOUT")
            continue
        by_player: Dict[str, Counter] = defaultdict(Counter)
        types = Counter()
        for name, sid, ty in rows:
            by_player[name][sid] += 1
            types[ty] += 1
        players = {}
        sids_seen: Dict[int, Set[str]] = defaultdict(set)
        for name, c in by_player.items():
            valid = {s for s in c if s is not None and s != 0}
            players[repr(name)] = {
                "rows": sum(c.values()),
                "null": c.get(None, 0),
                "zero": c.get(0, 0),
                "distinct_valid_steamids": len(valid),
                "steamids": sorted(str(s) for s in valid),
            }
            for s in valid:
                sids_seen[s].add(name)
                name_to_sids[norm_nfkc_casefold(name)].add(s)
                sid_to_names[s].add(norm_nfkc_casefold(name))
        shared = {
            str(s): sorted(repr(n) for n in names)
            for s, names in sids_seen.items()
            if len(names) > 1
        }
        n_null = sum(p["null"] for p in players.values())
        n_zero = sum(p["zero"] for p in players.values())
        one_each = all(p["distinct_valid_steamids"] == 1 for p in players.values())
        pts_names = set(by_player)
        agg["rows"] += len(rows)
        agg["null"] += n_null
        agg["zero"] += n_zero
        agg["players"] += len(players)
        agg["players_exactly_one_valid_sid"] += sum(
            1 for p in players.values() if p["distinct_valid_steamids"] == 1
        )
        agg["players_multi_sid"] += sum(
            1 for p in players.values() if p["distinct_valid_steamids"] > 1
        )
        agg["players_no_valid_sid"] += sum(
            1 for p in players.values() if p["distinct_valid_steamids"] == 0
        )
        agg["demos_ok"] += 1
        agg["demos_unique_per_player"] += int(one_each and not shared)
        agg["demos_sample_names_eq_pms"] += int(pts_names == pms[demo])
        per_demo.append(
            {
                "demo": demo,
                "status": "ok",
                "seconds": round(dt, 2),
                "tick_min": tmin,
                "tick_max": tmax,
                "slice_starts": starts,
                "rows": len(rows),
                "typeof": dict(types),
                "null": n_null,
                "zero": n_zero,
                "players_in_sample": len(players),
                "sample_names_equal_pms": pts_names == pms[demo],
                "in_sample_not_pms": sorted(repr(x) for x in pts_names - pms[demo]),
                "in_pms_not_sample": sorted(repr(x) for x in pms[demo] - pts_names),
                "one_valid_steamid_per_player": one_each,
                "steamids_shared_by_players": shared,
                "players": players,
            }
        )
        _log(
            f"    {demo}: {dt:.1f}s rows={len(rows)} players={len(players)} null={n_null} zero={n_zero} "
            f"one_sid_each={one_each} shared={len(shared)} names_eq_pms={pts_names == pms[demo]}"
        )
    cross = {
        "normalized_names_with_multiple_steamids_across_demos": {
            n: sorted(str(s) for s in v) for n, v in name_to_sids.items() if len(v) > 1
        },
        "steamids_with_multiple_normalized_names_across_demos": {
            str(s): sorted(v) for s, v in sid_to_names.items() if len(v) > 1
        },
        "distinct_normalized_names_in_sample": len(name_to_sids),
        "distinct_steamids_in_sample": len(sid_to_names),
    }
    return {
        "playermatchstats_steamid": {
            "rows": pms_sid[0],
            "null": pms_sid[1],
            "zero": pms_sid[2] or 0,
            "distinct": pms_sid[3],
        },
        "roundstats_has_steamid_column": False,
        "sample_rows_per_demo_target": rows_per_demo,
        "slices_per_demo": n_slices,
        "aggregate": dict(agg),
        "cross_demo": cross,
        "per_demo": per_demo,
    }


# --------------------------------------------------------------------------------------------
# (e) migration sizing without a table scan
# --------------------------------------------------------------------------------------------

COUNT_SQL = "SELECT COUNT(*) FROM playertickstate WHERE demo_name = ? AND player_name = ?"


def phase_migration(
    con: sqlite3.Connection,
    bq: Bounded,
    demos15: List[str],
    pms: Dict[str, Set[str]],
    players_per_demo: int,
    budget_s: float,
    per_query_s: float,
    db_bytes: int,
) -> dict:
    _log(
        f"(e) migration sizing: COUNT(*) per (demo, player) for {players_per_demo} players x {len(demos15)} demos"
    )
    # (1) fraction of playermatchstats rows whose name changes — Python and SQLite semantics
    pms_rows = con.execute(
        "SELECT demo_name, player_name, lower(trim(player_name)) FROM playermatchstats"
    ).fetchall()
    n_rows = len(pms_rows)
    changed_sqlite = [(d, n) for d, n, ln in pms_rows if n != ln]
    changed_python = [(d, n) for d, n, _ in pms_rows if n != n.strip().lower()]
    semantics_diff = [
        repr(n)
        for d, n, ln in pms_rows
        if (n != ln) != (n != n.strip().lower()) or (n != ln and ln != n.strip().lower())
    ]
    _log(
        f"    playermatchstats rows changed by lower(trim()): sqlite={len(changed_sqlite)} python={len(changed_python)} "
        f"of {n_rows}; semantics differ on {len(semantics_diff)} names"
    )
    plan = bq.plan(COUNT_SQL, ("x", "y"))
    _log(f"    count plan: {plan}")
    # (2) rows per player-match on bounded samples
    t_end = time.monotonic() + budget_s
    rng = random.Random(0)
    counts = []
    for demo in demos15:
        names = sorted(pms[demo])
        rng.shuffle(names)
        for name in names[:players_per_demo]:
            if time.monotonic() > t_end:
                break
            t = time.monotonic()
            r = bq.rows(COUNT_SQL, (demo, name), seconds=per_query_s)
            dt = time.monotonic() - t
            if r is None:
                counts.append(
                    {
                        "demo": demo,
                        "player": repr(name),
                        "status": "timeout",
                        "seconds": round(dt, 2),
                    }
                )
                _log(f"    {demo} / {name!r}: TIMEOUT")
                continue
            counts.append(
                {
                    "demo": demo,
                    "player": repr(name),
                    "status": "ok",
                    "rows": r[0][0],
                    "seconds": round(dt, 2),
                }
            )
            _log(f"    {demo} / {name!r}: {r[0][0]} rows in {dt:.1f}s")
    ok = [c["rows"] for c in counts if c["status"] == "ok"]
    est = {}
    if ok:
        mean = statistics.fmean(ok)
        est = {
            "rows_per_player_match_mean": mean,
            "rows_per_player_match_median": statistics.median(ok),
            "rows_per_player_match_min": min(ok),
            "rows_per_player_match_max": max(ok),
            "rows_per_player_match_stdev": statistics.pstdev(ok) if len(ok) > 1 else 0.0,
            "n_measured_pairs": len(ok),
            "playertickstate_rows_estimate": mean * n_rows,
            "playertickstate_rows_estimate_min_max": [min(ok) * n_rows, max(ok) * n_rows],
            "bytes_per_row_incl_indexes_estimate": db_bytes / (mean * n_rows),
            "rows_touched_by_update_estimate_sqlite_semantics": len(changed_sqlite) * mean,
            "rows_touched_by_update_estimate_min_max": [
                len(changed_sqlite) * min(ok),
                len(changed_sqlite) * max(ok),
            ],
            "rows_touched_frac_of_table": len(changed_sqlite) / n_rows,
        }
    return {
        "playermatchstats_rows": n_rows,
        "pms_rows_changed_lower_trim_sqlite": len(changed_sqlite),
        "pms_rows_changed_strip_lower_python": len(changed_python),
        "pms_names_where_sqlite_and_python_normalization_differ": semantics_diff,
        "pms_rows_changed_frac": len(changed_sqlite) / n_rows if n_rows else None,
        "count_query": COUNT_SQL,
        "count_query_plan": plan,
        "counts": counts,
        "estimate": est,
        "exact_count_recipe": "SUM over the changed (demo_name, player_name) playermatchstats pairs of "
        "SELECT COUNT(*) FROM playertickstate WHERE demo_name=? AND player_name=? "
        "(covering index ix_pts_player_demo; no table scan)",
    }


# --------------------------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-demos", type=int, default=15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--probe-budget", type=float, default=240.0)
    ap.add_argument("--distinct-budget", type=float, default=360.0)
    ap.add_argument("--distinct-per-query", type=float, default=75.0)
    ap.add_argument("--steamid-budget", type=float, default=180.0)
    ap.add_argument("--steamid-rows", type=int, default=2000)
    ap.add_argument("--count-budget", type=float, default=240.0)
    ap.add_argument("--count-per-query", type=float, default=60.0)
    ap.add_argument("--count-players", type=int, default=2)
    ap.add_argument("--out", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    con, path = open_ro()
    bq = Bounded(con)
    db_bytes = os.path.getsize(path)
    wal = path + "-wal"
    wal_bytes = os.path.getsize(wal) if os.path.exists(wal) else 0
    _log(
        f"db={path} size={db_bytes / 1e9:.1f} GB wal={wal_bytes / 1e9:.2f} GB journal={con.execute('PRAGMA journal_mode').fetchone()[0]}"
    )

    result: dict = {
        "meta": {
            "date": "2026-09-05",
            "task": "M4 name-join coverage (D8, Parte III §2.4)",
            "db_path": path,
            "db_bytes": db_bytes,
            "wal_bytes": wal_bytes,
            "read_only": True,
            "seed": args.seed,
            "n_demos_sampled": args.n_demos,
            "argv": sys.argv[1:],
            "sqlite_version": sqlite3.sqlite_version,
            "python": sys.version.split()[0],
        }
    }
    result["a_side"] = phase_side(con)
    result["b_names"], rs, pms = phase_names(con)
    demos_all = sorted(set(rs) & set(pms))
    demos15 = random.Random(args.seed).sample(demos_all, min(args.n_demos, len(demos_all)))
    result["meta"]["demos_sampled"] = demos15

    result["b2_tick_probes"] = phase_tick_probes(bq, rs, pms, args.probe_budget)
    result["c_distinct_proxy"] = phase_distinct(
        bq, demos15, pms, args.distinct_budget, args.distinct_per_query
    )
    result["d_steamid"] = phase_steamid(
        con, bq, demos15, pms, args.steamid_rows, args.steamid_budget
    )
    result["e_migration"] = phase_migration(
        con, bq, demos15, pms, args.count_players, args.count_budget, args.count_per_query, db_bytes
    )
    result["meta"]["runtime_seconds"] = round(time.monotonic() - T0, 1)
    result["meta"]["query_timeouts_total"] = bq.timeouts
    con.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    _log(
        f"wrote {args.out} ({args.out.stat().st_size / 1e3:.0f} kB) in {result['meta']['runtime_seconds']}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
