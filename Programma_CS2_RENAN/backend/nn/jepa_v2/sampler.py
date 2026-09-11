"""Window sampler for JEPA v2 pre-training (Parte III §5.2, C-10/C-11).

Reads safetensors shards exported by the v2 pipeline (D-11 layout:
``DIR/<split>/<demo_name>.safetensors``). Each shard contains ``x_num``
(L, 21), ``x_cat`` (L, 3), and round-level label tensors.

``ShardIndex`` lists and memory-maps shards.  ``WindowSampler`` yields
batches of ``(x_num, x_cat, meta)`` with random or fixed offsets per
split.  ``probe_batch`` returns fixed validation windows with D-17
labels for linear-probe evaluation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np
import torch
from safetensors import safe_open

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

log = logging.getLogger(__name__)

LABEL_HORIZON_TICKS: int = 128
_HEALTH_COL: int = CS2_V2.numeric_names.index("health")
_ENEMIES_COL: int = CS2_V2.numeric_names.index("enemies_visible")


@dataclass(frozen=True)
class EpisodeInfo:
    """Metadata for a single episode within a shard."""

    shard_idx: int
    demo_name: str
    length: int


class ShardIndex:
    """Lists safetensors shards under ``root_dir/<split>/`` and memory-maps them.

    Parte III §5.2, D-11 layout.
    """

    def __init__(self, root_dir: str | Path, split: str) -> None:
        self.root = Path(root_dir) / split
        self.split = split
        self.paths: List[Path] = sorted(self.root.glob("*.safetensors"))
        if not self.paths:
            raise FileNotFoundError(f"No safetensors shards in {self.root}")

        self.episodes: List[EpisodeInfo] = []

        for i, p in enumerate(self.paths):
            with safe_open(str(p), framework="pt", device="cpu") as f:
                keys = f.keys()
                if "x_num" not in keys:
                    log.warning("Shard %s missing x_num, skipping", p.name)
                    continue
                length = f.get_tensor("x_num").shape[0]
            demo = p.stem
            self.episodes.append(EpisodeInfo(shard_idx=i, demo_name=demo, length=length))

        if not self.episodes:
            raise ValueError(f"No valid episodes found in {self.root}")

        self._cache: Dict[int, Dict[str, torch.Tensor]] = {}

        log.info(
            "ShardIndex[%s]: %d shards, %d episodes, %d total ticks",
            split,
            len(self.paths),
            len(self.episodes),
            sum(e.length for e in self.episodes),
        )

    def load_episode(self, ep: EpisodeInfo) -> Dict[str, torch.Tensor]:
        """Load all tensors from an episode's shard (cached after first read)."""
        if ep.shard_idx in self._cache:
            return self._cache[ep.shard_idx]
        with safe_open(str(self.paths[ep.shard_idx]), framework="pt", device="cpu") as f:
            data = {k: f.get_tensor(k) for k in f.keys()}
        self._cache[ep.shard_idx] = data
        return data


class WindowSampler:
    """Yields batches of windows for JEPA v2 training/validation.

    Parte III §5.2: windows of ``cfg.window_ticks`` (384) ticks,
    batch size ``cfg.batch_size`` (128). Episodes shorter than
    ``window_ticks`` are skipped. Random offsets for train, fixed
    for validation.
    """

    def __init__(
        self,
        index: ShardIndex,
        cfg: JepaV2Config,
        split: str,
        seed: int = 0,
        fixed_offsets: bool = False,
    ) -> None:
        self.index = index
        self.cfg = cfg
        self.split = split
        self.seed = seed
        self.fixed_offsets = fixed_offsets

        self.window_ticks = cfg.window_ticks
        self.batch_size = cfg.batch_size

        self.valid_episodes = [e for e in index.episodes if e.length >= self.window_ticks]
        if not self.valid_episodes:
            raise ValueError(f"No episodes with length >= {self.window_ticks} in {split}")

        log.info(
            "WindowSampler[%s]: %d/%d episodes valid (>=%d ticks), fixed=%s",
            split,
            len(self.valid_episodes),
            len(index.episodes),
            self.window_ticks,
            fixed_offsets,
        )

    def __iter__(self) -> Iterator[Tuple[torch.Tensor, torch.Tensor, List[dict]]]:
        rng = np.random.default_rng(self.seed)
        ep_indices = np.arange(len(self.valid_episodes))
        x_num_batch: List[torch.Tensor] = []
        x_cat_batch: List[torch.Tensor] = []
        meta_batch: List[dict] = []

        while True:
            rng.shuffle(ep_indices)

            for ei in ep_indices:
                ep = self.valid_episodes[ei]
                max_offset = ep.length - self.window_ticks

                if self.fixed_offsets:
                    offset = 0
                else:
                    offset = int(rng.integers(0, max_offset + 1))

                data = self.index.load_episode(ep)
                x_num = data["x_num"][offset : offset + self.window_ticks].unsqueeze(0)
                x_cat = data["x_cat"][offset : offset + self.window_ticks].unsqueeze(0)

                x_num_batch.append(x_num)
                x_cat_batch.append(x_cat)
                meta_batch.append(
                    {"demo": ep.demo_name, "offset": offset, "shard_idx": ep.shard_idx}
                )

                if len(x_num_batch) == self.batch_size:
                    yield (
                        torch.cat(x_num_batch, dim=0),
                        torch.cat(x_cat_batch, dim=0),
                        meta_batch,
                    )
                    x_num_batch = []
                    x_cat_batch = []
                    meta_batch = []


def _derive_d17_labels(
    data: Dict[str, torch.Tensor],
    offset: int,
    window_ticks: int,
) -> Dict[str, Optional[float]]:
    """Derive D-17 probe labels for one window.

    Labels:
      - round_won, opening_death, side: from labels_round (if present)
      - death_within_2s: health <= 0 within LABEL_HORIZON_TICKS after window end
      - contact_new_within_2s: enemies_visible==0 at last tick, >0 within
        LABEL_HORIZON_TICKS after window end
    """
    labels: Dict[str, Optional[float]] = {}
    end = offset + window_ticks

    if "labels_round" in data and "labels_mask" in data:
        lr = data["labels_round"]
        lm = data["labels_mask"]
        mid = offset + window_ticks // 2
        idx = min(mid, lr.shape[0] - 1) if lr.dim() >= 1 and lr.shape[0] > 0 else 0
        if lm.dim() >= 1 and lm.shape[0] > idx and float(lm[idx]) > 0.5:
            if lr.dim() == 2 and lr.shape[1] >= 3:
                labels["round_won"] = float(lr[idx, 0])
                labels["opening_death"] = float(lr[idx, 1])
                labels["side"] = float(lr[idx, 2])
            elif lr.dim() == 1:
                labels["round_won"] = float(lr[idx])
        else:
            labels["round_won"] = None
            labels["opening_death"] = None
            labels["side"] = None
    else:
        labels["round_won"] = None
        labels["opening_death"] = None
        labels["side"] = None

    x_num = data["x_num"]
    ep_len = x_num.shape[0]
    horizon_end = min(end + LABEL_HORIZON_TICKS, ep_len)

    if end < ep_len:
        future_health = x_num[end:horizon_end, _HEALTH_COL]
        labels["death_within_2s"] = 1.0 if float(future_health.min()) <= 0.0 else 0.0
    else:
        labels["death_within_2s"] = None

    if end < ep_len:
        last_enemies = float(x_num[end - 1, _ENEMIES_COL])
        if last_enemies == 0.0:
            future_enemies = x_num[end:horizon_end, _ENEMIES_COL]
            labels["contact_new_within_2s"] = 1.0 if float(future_enemies.max()) > 0.0 else 0.0
        else:
            labels["contact_new_within_2s"] = 0.0
    else:
        labels["contact_new_within_2s"] = None

    return labels


def probe_batch(
    index: ShardIndex,
    cfg: JepaV2Config,
    n_windows: Optional[int] = None,
    seed: int = 42,
) -> Tuple[torch.Tensor, torch.Tensor, List[dict], Dict[str, np.ndarray]]:
    """Return fixed validation windows with D-17 labels for probe evaluation.

    Returns:
        ``(x_num, x_cat, meta_list, labels_dict)`` where labels_dict maps
        label name → float array (NaN for missing).
    """
    if n_windows is None:
        n_windows = cfg.probe_windows

    rng = np.random.default_rng(seed)
    valid_episodes = [e for e in index.episodes if e.length >= cfg.window_ticks]
    if not valid_episodes:
        raise ValueError("No valid episodes for probe_batch")

    x_num_list: List[torch.Tensor] = []
    x_cat_list: List[torch.Tensor] = []
    meta_list: List[dict] = []
    all_labels: List[Dict[str, Optional[float]]] = []

    while len(x_num_list) < n_windows:
        ep = valid_episodes[int(rng.integers(0, len(valid_episodes)))]
        max_off = ep.length - cfg.window_ticks
        offset = int(rng.integers(0, max_off + 1))

        data = index.load_episode(ep)
        x_num_list.append(data["x_num"][offset : offset + cfg.window_ticks].unsqueeze(0))
        x_cat_list.append(data["x_cat"][offset : offset + cfg.window_ticks].unsqueeze(0))
        meta_list.append({"demo": ep.demo_name, "offset": offset})

        window_labels = _derive_d17_labels(data, offset, cfg.window_ticks)
        all_labels.append(window_labels)

    label_names = ["round_won", "opening_death", "side", "death_within_2s", "contact_new_within_2s"]
    labels_dict: Dict[str, np.ndarray] = {}
    for name in label_names:
        arr = np.array(
            [lb.get(name, np.nan) if lb.get(name) is not None else np.nan for lb in all_labels],
            dtype=np.float64,
        )
        labels_dict[name] = arr

    return (
        torch.cat(x_num_list, dim=0),
        torch.cat(x_cat_list, dim=0),
        meta_list,
        labels_dict,
    )
