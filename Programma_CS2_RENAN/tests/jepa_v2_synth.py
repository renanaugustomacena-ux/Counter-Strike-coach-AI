"""Synthetic safetensors shards in the exact layout of tools/export_episodes.py (D-11).

Shared by the jepa_v2 sampler, training-smoke and benchmark tests so that every test
exercises multi-episode shards with per-episode labels, like the real export.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from safetensors.torch import save_file

NUMERIC_DIM = 21
HEALTH_COL = 0
ENEMIES_COL = 8
SIDE_COL = 2  # x_cat column of the side categorical (CT=0, T=1, unknown=2)


def episode_spec(
    length: int,
    *,
    round_number: int = 1,
    player_idx: int = 0,
    round_won: Optional[float] = 1.0,
    opening_death: float = 0.0,
    side_is_ct: float = 1.0,
    death_at: Optional[int] = None,
    enemies_from: Optional[int] = None,
) -> Dict[str, Any]:
    """Describe one episode; ``death_at``/``enemies_from`` are ticks relative to its start."""
    return {
        "length": length,
        "round_number": round_number,
        "player_idx": player_idx,
        "round_won": round_won,
        "opening_death": opening_death,
        "side_is_ct": side_is_ct,
        "death_at": death_at,
        "enemies_from": enemies_from,
    }


def write_synthetic_shard(
    path: Path,
    episodes: List[Dict[str, Any]],
    *,
    seed: int = 0,
    with_labels: bool = True,
    demo_name: Optional[str] = None,
) -> None:
    """Write a D-11 shard holding ``episodes`` (see :func:`episode_spec`)."""
    rng = np.random.default_rng(seed)
    x_num_parts: List[np.ndarray] = []
    x_cat_parts: List[np.ndarray] = []
    health_parts: List[np.ndarray] = []
    enemies_parts: List[np.ndarray] = []
    offsets = [0]
    meta_rows: List[List[int]] = []
    label_rows: List[List[float]] = []
    mask_rows: List[List[int]] = []
    tick_cursor = 0
    for spec in episodes:
        n = int(spec["length"])
        if spec["death_at"] is not None and spec["death_at"] < n:
            n = int(spec["death_at"]) + 1  # the export cuts at the death tick (D-10)
        x_num = rng.standard_normal((n, NUMERIC_DIM)).astype(np.float32)
        health = np.full(n, 100.0, dtype=np.float32)
        if spec["death_at"] is not None and spec["death_at"] < spec["length"]:
            health[-1] = 0.0
        enemies = np.zeros(n, dtype=np.float32)
        if spec["enemies_from"] is not None and spec["enemies_from"] < n:
            enemies[int(spec["enemies_from"]) :] = 1.0
        x_num[:, HEALTH_COL] = health / 100.0
        x_num[:, ENEMIES_COL] = np.minimum(enemies / 5.0, 1.0)
        x_cat = np.zeros((n, 3), dtype=np.int64)
        x_cat[:, SIDE_COL] = 0 if float(spec["side_is_ct"]) == 1.0 else 1
        x_num_parts.append(x_num)
        x_cat_parts.append(x_cat)
        health_parts.append(health)
        enemies_parts.append(enemies)
        offsets.append(offsets[-1] + n)
        meta_rows.append(
            [int(spec["round_number"]), tick_cursor, tick_cursor + n - 1, int(spec["player_idx"])]
        )
        tick_cursor += n + 200
        rw = spec["round_won"]
        label_rows.append(
            [
                np.nan if rw is None else float(rw),
                1.0,
                0.0,
                1.0,
                np.nan,
                0.0,
                float(spec["opening_death"]),
                float(spec["side_is_ct"]),
            ]
        )
        mask_rows.append([0 if rw is None else 1, 1, 1, 1, 0, 1, 1, 1])
    n_total = offsets[-1]
    tensors: Dict[str, torch.Tensor] = {
        "x_num": torch.from_numpy(np.concatenate(x_num_parts)),
        "x_cat": torch.from_numpy(np.concatenate(x_cat_parts)),
        "health": torch.from_numpy(np.concatenate(health_parts)),
        "enemies_visible": torch.from_numpy(np.concatenate(enemies_parts)),
        "tick": torch.arange(n_total, dtype=torch.int64),
        "filled": torch.zeros(n_total, dtype=torch.uint8),
        "raw_pos_view": torch.zeros(n_total, 5, dtype=torch.float32),
        "actions": torch.zeros(n_total, 5, dtype=torch.float32),
        "episode_offsets": torch.tensor(offsets, dtype=torch.int64),
        "episode_meta": torch.tensor(meta_rows, dtype=torch.int64),
    }
    if with_labels:
        tensors["labels_round"] = torch.tensor(label_rows, dtype=torch.float32)
        tensors["labels_mask"] = torch.tensor(mask_rows, dtype=torch.uint8)
    metadata = {
        "demo_name": demo_name or path.stem,
        "map_name": "de_mirage",
        "tick_rate": "64.0",
        "players": json.dumps([f"player{p}" for p in range(len(episodes))]),
        "split": path.parent.name,
        "export_version": "1",
    }
    save_file(tensors, str(path), metadata=metadata)
