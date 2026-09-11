"""Export SQLite monolith to safetensors training shards (Parte III §3, D-10/D-11).

Usage::

    PYTHONPATH=. .venv/bin/python tools/export_episodes.py \\
        --out DIR [--profile full|medium|sample] [--db PATH] [--seed 0] \\
        [--demos N] [--workers K]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import sqlite3
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from safetensors.numpy import save_file

REPO = Path(__file__).resolve().parent.parent

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

ROUNDSTATS_LABEL_COLS = [
    "round_number",
    "round_won",
    "kills",
    "deaths",
    "kast",
    "round_rating",
    "opening_kill",
    "opening_death",
    "side",
]

MATCH_STATS_DEMO_SUFFIX_RE = re.compile(r"\.dem_.*$", re.IGNORECASE)

CHRONOLOGICAL_SOURCES = frozenset({"filename_date", "filename_year", "hltv_event_date"})

MIN_EPISODE_TICKS = 64
GAP_TOLERANCE = 7
EXPORT_VERSION = "1"


# --------------------------------------------------------------------------- logging


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- DB access


def open_ro(db_path: Optional[str] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = os.path.realpath(REPO / "Programma_CS2_RENAN/backend/storage/database.db")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=120)
    con.execute("PRAGMA query_only=1")
    return con


def _normalize_demo_name(demo_name: str | None) -> str:
    return MATCH_STATS_DEMO_SUFFIX_RE.sub("", demo_name or "").removesuffix(".dem")


def _normalize_player_name(name: Any) -> str:
    if name is None:
        return ""
    if isinstance(name, float) and math.isnan(name):
        return ""
    return str(name).strip().casefold()


# --------------------------------------------------------------------------- git / versions


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _demoparser_version() -> str:
    try:
        return importlib.metadata.version("demoparser2")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


# --------------------------------------------------------------------------- tick data


def _fetch_player_ticks(con: sqlite3.Connection, demo: str, stored_name: str) -> pd.DataFrame:
    q = (
        f"SELECT {', '.join(PTS_COLS)} FROM playertickstate "
        "WHERE demo_name = ? AND player_name = ? ORDER BY tick"
    )
    rows = con.execute(q, (demo, stored_name)).fetchall()
    if not rows:
        return pd.DataFrame(columns=PTS_COLS)
    return pd.DataFrame(rows, columns=PTS_COLS)


# --------------------------------------------------------------------------- segmentation


def _dedupe(df: pd.DataFrame) -> pd.DataFrame:
    tick = df["tick"].values
    if len(tick) == 0:
        return df
    keep = np.ones(len(tick), dtype=bool)
    keep[1:] = tick[1:] != tick[:-1]
    return df.iloc[np.nonzero(keep)[0]].reset_index(drop=True)


def _drop_warmup(df: pd.DataFrame) -> pd.DataFrame:
    mask = ~((df["round_number"].values == 1) & (df["time_in_round"].values == 0))
    return df.iloc[np.nonzero(mask)[0]].reset_index(drop=True)


def _split_episodes(tick: np.ndarray, rnd: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    if len(tick) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    d = np.diff(tick)
    brk = (d > GAP_TOLERANCE) | (rnd[1:] != rnd[:-1])
    starts = np.concatenate([[0], np.nonzero(brk)[0] + 1]).astype(np.int64)
    ends = np.concatenate([starts[1:], [len(tick)]]).astype(np.int64)
    return starts, ends


def _bridge_episode(
    df_ep: pd.DataFrame,
) -> Tuple[pd.DataFrame, np.ndarray]:
    """Forward-fill gaps of 2..7 ticks within an episode. Returns (bridged_df, filled_mask)."""
    tick = df_ep["tick"].values.astype(np.int64)
    n = len(tick)
    if n == 0:
        return df_ep, np.zeros(0, dtype=np.uint8)

    diffs = np.diff(tick)
    repeats = np.ones(n, dtype=np.int64)
    repeats[:-1] = np.where(diffs <= GAP_TOLERANCE, diffs, 1)

    total = int(repeats.sum())
    src_idx = np.repeat(np.arange(n), repeats)

    filled = np.ones(total, dtype=np.uint8)
    orig_positions = np.zeros(total, dtype=bool)
    cumsum = np.concatenate([[0], np.cumsum(repeats[:-1])])
    orig_positions[cumsum] = True
    filled[orig_positions] = 0

    bridged_df = df_ep.iloc[src_idx].reset_index(drop=True)
    new_ticks = np.arange(tick[0], tick[0] + total, dtype=np.int64)
    bridged_df["tick"] = new_ticks

    return bridged_df, filled


def _cut_at_death(df_ep: pd.DataFrame, filled: np.ndarray) -> Tuple[pd.DataFrame, np.ndarray]:
    """Cut episode at first health <= 0, keeping the death tick."""
    hp = pd.to_numeric(df_ep["health"], errors="coerce").values
    dead_mask = hp <= 0
    dead_idx = np.nonzero(dead_mask)[0]
    if len(dead_idx) == 0:
        return df_ep, filled
    cut = dead_idx[0] + 1
    return df_ep.iloc[:cut].reset_index(drop=True), filled[:cut]


# --------------------------------------------------------------------------- actions


def _wrap_delta_yaw(d: np.ndarray) -> np.ndarray:
    """Wrap to (-180, 180]."""
    return 180.0 - ((180.0 - d) % 360.0)


def _compute_actions(raw_pos_view: np.ndarray, offsets: np.ndarray) -> np.ndarray:
    """Compute per-tick actions [N,5]: (dx,dy,dz)/8, dyaw/180, dpitch/90.

    Actions point toward the NEXT tick. Last tick of each episode gets zeros.
    """
    n = raw_pos_view.shape[0]
    actions = np.zeros((n, 5), dtype=np.float32)

    for i in range(len(offsets) - 1):
        s, e = int(offsets[i]), int(offsets[i + 1])
        if e - s < 2:
            continue
        ep = raw_pos_view[s:e]
        dx = np.diff(ep[:, 0])
        dy = np.diff(ep[:, 1])
        dz = np.diff(ep[:, 2])
        dyaw = _wrap_delta_yaw(np.diff(ep[:, 3]))
        dpitch = np.diff(ep[:, 4])

        actions[s : e - 1, 0] = dx / 8.0
        actions[s : e - 1, 1] = dy / 8.0
        actions[s : e - 1, 2] = dz / 8.0
        actions[s : e - 1, 3] = dyaw / 180.0
        actions[s : e - 1, 4] = dpitch / 90.0

    return actions


# --------------------------------------------------------------------------- labels


def _fetch_round_labels(
    con: sqlite3.Connection, demo: str, player: str
) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for row in con.execute(
        "SELECT round_number, round_won, kills, deaths, kast, round_rating, "
        "opening_kill, opening_death, side "
        "FROM roundstats WHERE demo_name = ? AND player_name = ?",
        (demo, player),
    ):
        rnd = int(row[0])
        out[rnd] = {
            "round_won": None if row[1] is None else float(bool(row[1])),
            "kills": None if row[2] is None else float(row[2]),
            "deaths": None if row[3] is None else float(row[3]),
            "kast": None if row[4] is None else float(bool(row[4])),
            "round_rating": None if row[5] is None else float(row[5]),
            "opening_kill": None if row[6] is None else float(bool(row[6])),
            "opening_death": None if row[7] is None else float(bool(row[7])),
            "side_is_ct": None if row[8] is None else float(row[8] == "CT"),
        }
    return out


def _build_episode_labels(
    round_numbers: np.ndarray,
    norm_names: List[str],
    per_player_labels: Dict[str, Dict[int, Dict[str, Any]]],
) -> Tuple[np.ndarray, np.ndarray]:
    """Build labels_round [E,8] f32 and labels_mask [E,8] u8 per episode+player."""
    n_ep = len(round_numbers)
    label_keys = [
        "round_won",
        "kills",
        "deaths",
        "kast",
        "round_rating",
        "opening_kill",
        "opening_death",
        "side_is_ct",
    ]
    labels = np.full((n_ep, 8), np.nan, dtype=np.float32)
    mask = np.zeros((n_ep, 8), dtype=np.uint8)

    for i in range(n_ep):
        rnd_int = int(round_numbers[i])
        player_labels = per_player_labels.get(norm_names[i], {})
        if rnd_int not in player_labels:
            continue
        rl = player_labels[rnd_int]
        for j, key in enumerate(label_keys):
            val = rl.get(key)
            if val is not None:
                labels[i, j] = val
                mask[i, j] = 1

    return labels, mask


# --------------------------------------------------------------------------- per-demo export


def _resolve_player_names_from_pms(pms_rows: List[Tuple[str, ...]]) -> Dict[str, str]:
    """Build normalized -> stored spelling from PMS rows (player_name column)."""
    mapping: Dict[str, str] = {}
    for row in pms_rows:
        raw = row[0]
        key = _normalize_player_name(raw)
        if key and key not in mapping:
            mapping[key] = raw
    return mapping


def _process_demo(
    db_path: str | None,
    demo_name: str,
    pms_rows: List[Dict[str, Any]],
    split: str,
    profile: str,
    seed: int,
) -> Dict[str, Any] | None:
    """Process one demo into a safetensors shard. Returns shard info or None."""

    con = open_ro(db_path)
    try:
        return _process_demo_inner(con, demo_name, pms_rows, split, profile, seed)
    finally:
        con.close()


def _process_demo_inner(
    con: sqlite3.Connection,
    demo_name: str,
    pms_rows: List[Dict[str, Any]],
    split: str,
    profile: str,
    seed: int,
) -> Dict[str, Any] | None:
    from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
        extract_frame_v2,
    )

    player_names_stored: Dict[str, str] = {}
    for r in pms_rows:
        key = _normalize_player_name(r["player_name"])
        if key and key not in player_names_stored:
            player_names_stored[key] = r["player_name"]

    players_ordered: List[str] = sorted(player_names_stored.keys())
    player_idx_map = {p: i for i, p in enumerate(players_ordered)}

    all_episodes: List[Dict[str, Any]] = []
    map_name_modal: Optional[str] = None
    map_counts: Dict[str, int] = {}

    for norm_name in players_ordered:
        stored = player_names_stored.get(norm_name)
        if stored is None:
            _log(f"  skip {norm_name} in {demo_name}: no stored name")
            continue
        pidx = player_idx_map[norm_name]

        df = _fetch_player_ticks(con, demo_name, stored)
        if df.empty:
            continue

        for _, v in df["map_name"].value_counts().items():
            mn = _
            if mn and mn != "de_unknown":
                map_counts[mn] = map_counts.get(mn, 0) + v

        df = _dedupe(df)
        df = _drop_warmup(df)
        if df.empty:
            continue

        tick = df["tick"].values.astype(np.int64)
        rnd = df["round_number"].values.astype(np.int64)
        starts, ends = _split_episodes(tick, rnd)

        for si in range(len(starts)):
            s, e = int(starts[si]), int(ends[si])
            ep_df = df.iloc[s:e].reset_index(drop=True)
            ep_df_bridged, filled = _bridge_episode(ep_df)
            ep_df_bridged, filled = _cut_at_death(ep_df_bridged, filled)

            if len(ep_df_bridged) < MIN_EPISODE_TICKS:
                continue

            ep_rnd = int(ep_df_bridged["round_number"].iloc[0])
            ep_tick_start = int(ep_df_bridged["tick"].iloc[0])
            ep_tick_end = int(ep_df_bridged["tick"].iloc[-1])

            all_episodes.append(
                {
                    "df": ep_df_bridged,
                    "filled": filled,
                    "round_number": ep_rnd,
                    "tick_start": ep_tick_start,
                    "tick_end": ep_tick_end,
                    "player_idx": pidx,
                    "norm_name": norm_name,
                }
            )

    if not all_episodes:
        return None

    all_episodes = _apply_profile(all_episodes, profile, seed)
    if not all_episodes:
        return None

    if map_counts:
        map_name_modal = max(map_counts, key=map_counts.get)  # type: ignore[arg-type]
    map_for_extract = map_name_modal if map_name_modal and map_name_modal != "de_unknown" else None

    all_round_labels: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for ep in all_episodes:
        norm = ep["norm_name"]
        if norm not in all_round_labels:
            stored = player_names_stored.get(norm)
            if stored:
                all_round_labels[norm] = _fetch_round_labels_resolved(con, demo_name, norm, stored)
            else:
                all_round_labels[norm] = {}

    all_x_num: List[np.ndarray] = []
    all_x_cat: List[np.ndarray] = []
    all_raw: List[np.ndarray] = []
    all_health: List[np.ndarray] = []
    all_ev: List[np.ndarray] = []
    all_tick: List[np.ndarray] = []
    all_filled: List[np.ndarray] = []
    offsets: List[int] = [0]
    ep_meta: List[List[int]] = []
    ep_round_numbers: List[int] = []

    for ep in all_episodes:
        ep_df = ep["df"]
        filled = ep["filled"]

        # Side per (player, round) from roundstats (100 % coverage measured, A20);
        # an episode never crosses a round, so one side per episode is exact (D-05).
        round_label = all_round_labels.get(ep["norm_name"], {}).get(ep["round_number"], {})
        side_is_ct = round_label.get("side_is_ct")
        side = None if side_is_ct is None else ("CT" if side_is_ct == 1.0 else "T")
        x_num, x_cat = extract_frame_v2(ep_df, map_name=map_for_extract, side=side)

        raw = np.zeros((len(ep_df), 5), dtype=np.float32)
        raw[:, 0] = (
            pd.to_numeric(ep_df["pos_x"], errors="coerce").fillna(0).values.astype(np.float32)
        )
        raw[:, 1] = (
            pd.to_numeric(ep_df["pos_y"], errors="coerce").fillna(0).values.astype(np.float32)
        )
        raw[:, 2] = (
            pd.to_numeric(ep_df["pos_z"], errors="coerce").fillna(0).values.astype(np.float32)
        )
        raw[:, 3] = (
            pd.to_numeric(ep_df["view_x"], errors="coerce").fillna(0).values.astype(np.float32)
        )
        raw[:, 4] = (
            pd.to_numeric(ep_df["view_y"], errors="coerce").fillna(0).values.astype(np.float32)
        )

        hp = pd.to_numeric(ep_df["health"], errors="coerce").fillna(0).values.astype(np.float32)
        ev = (
            pd.to_numeric(ep_df["enemies_visible"], errors="coerce")
            .fillna(0)
            .values.astype(np.float32)
        )
        tk = ep_df["tick"].values.astype(np.int64)

        all_x_num.append(x_num)
        all_x_cat.append(x_cat)
        all_raw.append(raw)
        all_health.append(hp)
        all_ev.append(ev)
        all_tick.append(tk)
        all_filled.append(filled)
        offsets.append(offsets[-1] + len(ep_df))
        ep_meta.append([ep["round_number"], ep["tick_start"], ep["tick_end"], ep["player_idx"]])
        ep_round_numbers.append(ep["round_number"])

    episode_offsets = np.array(offsets, dtype=np.int64)
    episode_meta_arr = np.array(ep_meta, dtype=np.int64)

    ep_norm_names = [ep["norm_name"] for ep in all_episodes]
    labels_round, labels_mask = _build_episode_labels(
        np.array(ep_round_numbers, dtype=np.int64), ep_norm_names, all_round_labels
    )

    x_num_cat = np.concatenate(all_x_num, axis=0)
    x_cat_cat = np.concatenate(all_x_cat, axis=0)
    raw_cat = np.concatenate(all_raw, axis=0)
    health_cat = np.concatenate(all_health, axis=0)
    ev_cat = np.concatenate(all_ev, axis=0)
    tick_cat = np.concatenate(all_tick, axis=0)
    filled_cat = np.concatenate(all_filled, axis=0)

    actions = _compute_actions(raw_cat, episode_offsets)

    from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

    match_date_str = ""
    match_date_source_str = ""
    for r in pms_rows:
        md = r.get("match_date")
        if md:
            match_date_str = str(md)
        mds = r.get("match_date_source")
        if mds:
            match_date_source_str = str(mds)

    players_list = [player_names_stored.get(p, p) for p in players_ordered]

    tensors = {
        "x_num": x_num_cat,
        "x_cat": x_cat_cat,
        "raw_pos_view": raw_cat,
        "actions": actions,
        "health": health_cat,
        "enemies_visible": ev_cat,
        "tick": tick_cat,
        "filled": filled_cat,
        "episode_offsets": episode_offsets,
        "episode_meta": episode_meta_arr,
        "labels_round": labels_round,
        "labels_mask": labels_mask,
    }

    metadata = {
        "demo_name": demo_name,
        "map_name": map_name_modal or "de_unknown",
        "tick_rate": "64",
        "players": json.dumps(players_list),
        "schema_fingerprint": CS2_V2.fingerprint(),
        "split": split,
        "match_date": match_date_str,
        "match_date_source": match_date_source_str,
        "export_version": EXPORT_VERSION,
        "git_sha": _git_sha(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "tensors": tensors,
        "metadata": metadata,
        "demo_name": demo_name,
        "split": split,
        "n_ticks": int(x_num_cat.shape[0]),
        "n_episodes": int(len(ep_meta)),
        "players": players_list,
        "match_date": match_date_str,
        "match_date_source": match_date_source_str,
    }


def _fetch_round_labels_resolved(
    con: sqlite3.Connection,
    demo_name: str,
    norm_name: str,
    stored_name: str,
) -> Dict[int, Dict[str, Any]]:
    """Fetch round labels using normalized name for roundstats (stored lower-stripped)."""
    labels = _fetch_round_labels(con, demo_name, norm_name)
    if not labels:
        labels = _fetch_round_labels(con, demo_name, stored_name)
    return labels


# --------------------------------------------------------------------------- profile selection


def _apply_profile(episodes: List[Dict[str, Any]], profile: str, seed: int) -> List[Dict[str, Any]]:
    if profile == "full":
        return episodes

    if profile == "medium":
        by_player: Dict[int, List[Dict[str, Any]]] = {}
        for ep in episodes:
            pidx = ep["player_idx"]
            by_player.setdefault(pidx, []).append(ep)
        # Seeded random choice (not the longest): the longest episodes are the
        # rounds the player survived, which starves the death labels (A17/A18).
        result: List[Dict[str, Any]] = []
        for pidx in sorted(by_player):
            eps = sorted(by_player[pidx], key=lambda e: e["tick_start"])
            if len(eps) > 8:
                rng = np.random.default_rng(seed * 1_000_003 + pidx)
                keep = sorted(rng.choice(len(eps), size=8, replace=False).tolist())
                eps = [eps[i] for i in keep]
            result.extend(eps)
        return result

    if profile == "sample":
        episodes.sort(key=lambda e: len(e["df"]), reverse=True)
        selected = episodes[:2]
        for ep in selected:
            if len(ep["df"]) > 448:
                ep["df"] = ep["df"].iloc[:448].reset_index(drop=True)
                ep["filled"] = ep["filled"][:448]
                ep["tick_end"] = int(ep["df"]["tick"].iloc[-1])
        return selected

    return episodes


# --------------------------------------------------------------------------- write


def _write_shard(
    out_dir: Path, split: str, demo_name: str, result: Dict[str, Any]
) -> Tuple[str, str]:
    split_dir = out_dir / split
    split_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{demo_name}.safetensors"
    fpath = split_dir / fname
    save_file(result["tensors"], str(fpath), metadata=result["metadata"])
    sha = _sha256_file(fpath)
    return fname, sha


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _write_manifest(
    out_dir: Path,
    split: str,
    demos: List[Dict[str, Any]],
    warnings: List[str],
    seed: int,
) -> None:
    from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

    demos_sorted = sorted(demos, key=lambda d: d["demo_name"])

    total_ticks = sum(d["n_ticks"] for d in demos_sorted)
    total_episodes = sum(d["n_episodes"] for d in demos_sorted)

    manifest = {
        "schema_fingerprint": CS2_V2.fingerprint(),
        "export_version": EXPORT_VERSION,
        "git_sha": _git_sha(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "demoparser_version": _demoparser_version(),
        "seed": seed,
        "split": split,
        "demos": [
            {
                "demo_name": d["demo_name"],
                "file": d["file"],
                "sha256": d["sha256"],
                "match_date": d.get("match_date", ""),
                "match_date_source": d.get("match_date_source", ""),
                "n_ticks": d["n_ticks"],
                "n_episodes": d["n_episodes"],
                "players": d["players"],
            }
            for d in demos_sorted
        ],
        "totals": {
            "n_demos": len(demos_sorted),
            "n_ticks": total_ticks,
            "n_episodes": total_episodes,
        },
        "warnings": warnings,
    }

    split_dir = out_dir / split
    split_dir.mkdir(parents=True, exist_ok=True)
    with open(split_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)


# --------------------------------------------------------------------------- main pipeline


def _load_pms_groups(
    con: sqlite3.Connection,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group playermatchstats rows by normalized demo name."""
    rows = con.execute(
        "SELECT demo_name, player_name, match_date, match_date_source, dataset_split "
        "FROM playermatchstats"
    ).fetchall()
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for demo_raw, player, match_date, mds, ds in rows:
        norm_demo = _normalize_demo_name(demo_raw)
        groups.setdefault(norm_demo, []).append(
            {
                "demo_name_raw": demo_raw,
                "player_name": player,
                "match_date": match_date,
                "match_date_source": mds,
                "dataset_split": ds,
            }
        )
    return groups


def _determine_split(pms_rows: List[Dict[str, Any]]) -> str | None:
    """Determine split from PMS rows. Returns lowercase split or None."""
    splits = set()
    for r in pms_rows:
        ds = r.get("dataset_split")
        if ds is None:
            continue
        ds_str = str(ds).strip().upper()
        if ds_str in ("TRAIN", "VAL", "TEST"):
            splits.add(ds_str.lower())
    if len(splits) == 1:
        return splits.pop()
    if len(splits) > 1:
        _log(f"  mixed splits {splits} — skipping")
        return None
    return None


def run_export(args: argparse.Namespace) -> None:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    con = open_ro(args.db)
    pms_groups = _load_pms_groups(con)
    con.close()

    demo_names = sorted(pms_groups.keys())
    if args.demos and args.demos > 0:
        rng = np.random.RandomState(args.seed)
        if args.demos < len(demo_names):
            indices = rng.choice(len(demo_names), size=args.demos, replace=False)
            demo_names = sorted(demo_names[i] for i in indices)

    if args.profile == "sample":
        rng = np.random.RandomState(args.seed)
        if len(demo_names) > 16:
            indices = rng.choice(len(demo_names), size=16, replace=False)
            demo_names = sorted(demo_names[int(i)] for i in indices)

    skipped_unassigned = 0
    skipped_empty = 0
    split_demos: Dict[str, List[Dict[str, Any]]] = {}
    split_warnings: Dict[str, List[str]] = {}

    tasks: List[Tuple[str, str, List[Dict[str, Any]]]] = []
    for demo in demo_names:
        pms_rows = pms_groups[demo]
        split = _determine_split(pms_rows)
        if split is None:
            skipped_unassigned += 1
            continue
        tasks.append((demo, split, pms_rows))

    _log(
        f"Export: {len(tasks)} demos ({skipped_unassigned} skipped unassigned), "
        f"profile={args.profile}, workers={args.workers}"
    )

    def process_one(item: Tuple[str, str, List[Dict[str, Any]]]) -> Dict[str, Any] | None:
        demo, split, pms_rows = item
        return _process_demo(args.db, demo, pms_rows, split, args.profile, args.seed)

    results: List[Tuple[str, Dict[str, Any]]] = []
    if args.workers <= 1:
        for item in tasks:
            result = process_one(item)
            if result is not None:
                results.append((item[1], result))
            else:
                skipped_empty += 1
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process_one, item): item for item in tasks}
            for future in as_completed(futures):
                item = futures[future]
                result = future.result()
                if result is not None:
                    results.append((item[1], result))
                else:
                    skipped_empty += 1

    for split, result in results:
        fname, sha = _write_shard(out_dir, split, result["demo_name"], result)
        entry = {
            "demo_name": result["demo_name"],
            "file": fname,
            "sha256": sha,
            "n_ticks": result["n_ticks"],
            "n_episodes": result["n_episodes"],
            "players": result["players"],
            "match_date": result.get("match_date", ""),
            "match_date_source": result.get("match_date_source", ""),
        }
        split_demos.setdefault(split, []).append(entry)

        mds = result.get("match_date_source", "")
        if mds and mds not in CHRONOLOGICAL_SOURCES:
            warnings = split_warnings.setdefault(split, [])
            warnings.append(
                f"OI-2: demo {result['demo_name']} match_date_source={mds} " f"is not chronological"
            )

    for split, demos in split_demos.items():
        _write_manifest(out_dir, split, demos, split_warnings.get(split, []), args.seed)

    total_shards = sum(len(d) for d in split_demos.values())
    total_episodes = sum(e["n_episodes"] for d in split_demos.values() for e in d)
    total_ticks = sum(e["n_ticks"] for d in split_demos.values() for e in d)
    _log(
        f"Done: {total_shards} shards, {total_episodes} episodes, "
        f"{total_ticks} ticks, {skipped_empty} empty demos, "
        f"{skipped_unassigned} unassigned"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export episodes to safetensors shards")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument(
        "--profile",
        choices=["full", "medium", "sample"],
        default="medium",
        help="Export profile",
    )
    parser.add_argument("--db", default=None, help="Path to database file")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--demos", type=int, default=None, help="Limit number of demos")
    parser.add_argument("--workers", type=int, default=1, help="Worker threads")
    args = parser.parse_args()
    run_export(args)


if __name__ == "__main__":
    main()
