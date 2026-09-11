"""Window sampler over the safetensors episode export (CORREZIONE Parte III §3, §4.7).

Shard layout (tools/export_episodes.py, contract D-11): one file per demo holding the
concatenated ticks of every episode (``x_num`` [N, 21], ``x_cat`` [N, 3], ``health`` [N],
``enemies_visible`` [N], ...), the CSR ``episode_offsets`` [E + 1], ``episode_meta`` [E, 4]
(round_number, tick_start, tick_end, player_idx) and per-episode ``labels_round`` [E, 8] /
``labels_mask`` [E, 8].

Every window is a contiguous slice of ONE episode (an episode never crosses a round or a
player, D-10), so a window can never straddle two episodes.  Episodes shorter than a window
are skipped and counted (J-5: never pad).  Labels for the probes (D-17) are derived inside the
window's own episode.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np
import torch
from safetensors import safe_open

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

log = logging.getLogger(__name__)

LABEL_HORIZON_TICKS: int = 128  # 2 s at 64 Hz (D-17)
_HEALTH_COL: int = CS2_V2.numeric_names.index("health")
_ENEMIES_COL: int = CS2_V2.numeric_names.index("enemies_visible")
# Column order of labels_round written by tools/export_episodes.py (D-11).
LABELS_ROUND_COLUMNS: Tuple[str, ...] = (
    "round_won",
    "kills",
    "deaths",
    "kast",
    "round_rating",
    "opening_kill",
    "opening_death",
    "side_is_ct",
)
_LABEL_COL: Dict[str, int] = {name: i for i, name in enumerate(LABELS_ROUND_COLUMNS)}
PROBE_LABEL_NAMES: Tuple[str, ...] = (
    "round_won",
    "opening_death",
    "side",
    "death_within_2s",
    "contact_new_within_2s",
    "enemy_visible_any_within_2s",
)
_MAX_CACHED_SHARDS: int = 48  # ~5 GB of medium-profile shards


@dataclass(frozen=True)
class EpisodeInfo:
    """One episode of one shard: a half-open tick range ``[start, end)``."""

    shard_idx: int
    demo_name: str
    ep_idx: int
    start: int
    end: int
    round_number: int
    player_idx: int

    @property
    def length(self) -> int:
        return self.end - self.start


class ShardIndex:
    """Lists the shards under ``root_dir/<split>/`` and their episodes (D-11)."""

    def __init__(self, root_dir: str | Path, split: str) -> None:
        self.root = Path(root_dir) / split
        self.split = split
        self.paths: List[Path] = sorted(self.root.glob("*.safetensors"))
        if not self.paths:
            raise FileNotFoundError(f"No safetensors shards in {self.root}")
        self.episodes: List[EpisodeInfo] = []
        for shard_idx, path in enumerate(self.paths):
            self.episodes.extend(_read_episode_table(path, shard_idx))
        if not self.episodes:
            raise ValueError(f"No episodes found in {self.root}")
        self._cache: "OrderedDict[int, Dict[str, torch.Tensor]]" = OrderedDict()
        log.info(
            "ShardIndex[%s]: %d shards, %d episodes, %d ticks",
            split,
            len(self.paths),
            len(self.episodes),
            sum(e.length for e in self.episodes),
        )

    def load_shard(self, shard_idx: int) -> Dict[str, torch.Tensor]:
        """All tensors of one shard (LRU-cached, at most ``_MAX_CACHED_SHARDS`` shards)."""
        cached = self._cache.get(shard_idx)
        if cached is not None:
            self._cache.move_to_end(shard_idx)
            return cached
        with safe_open(str(self.paths[shard_idx]), framework="pt", device="cpu") as f:
            data = {k: f.get_tensor(k) for k in f.keys()}
        self._cache[shard_idx] = data
        if len(self._cache) > _MAX_CACHED_SHARDS:
            self._cache.popitem(last=False)
        return data

    def load_episode(self, ep: EpisodeInfo) -> Dict[str, torch.Tensor]:
        """Tensors of the shard holding ``ep``; slice them with ``ep.start``/``ep.end``."""
        return self.load_shard(ep.shard_idx)

    def episode_lookup(self) -> Dict[Tuple[int, int], EpisodeInfo]:
        return {(e.shard_idx, e.ep_idx): e for e in self.episodes}


def _read_episode_table(path: Path, shard_idx: int) -> List[EpisodeInfo]:
    with safe_open(str(path), framework="pt", device="cpu") as f:
        keys = set(f.keys())
        if "x_num" not in keys:
            log.warning("Shard %s has no x_num, skipped", path.name)
            return []
        if "episode_offsets" not in keys:
            raise ValueError(f"{path.name}: missing episode_offsets (D-11 layout required)")
        n_ticks = int(f.get_slice("x_num").get_shape()[0])
        offsets = [int(v) for v in f.get_tensor("episode_offsets").tolist()]
        meta = f.get_tensor("episode_meta").tolist() if "episode_meta" in keys else None
    if not offsets or offsets[0] != 0 or offsets[-1] != n_ticks:
        raise ValueError(f"{path.name}: episode_offsets do not cover x_num ({offsets[:3]}...)")
    episodes: List[EpisodeInfo] = []
    for e in range(len(offsets) - 1):
        start, end = offsets[e], offsets[e + 1]
        if end <= start:
            raise ValueError(f"{path.name}: empty episode {e}")
        round_number = int(meta[e][0]) if meta else 0
        player_idx = int(meta[e][3]) if meta else 0
        episodes.append(EpisodeInfo(shard_idx, path.stem, e, start, end, round_number, player_idx))
    return episodes


def _window_meta(ep: EpisodeInfo, offset: int) -> dict:
    return {
        "demo": ep.demo_name,
        "shard_idx": ep.shard_idx,
        "ep_idx": ep.ep_idx,
        "offset": offset,
        "start": ep.start,
        "round_number": ep.round_number,
        "player_idx": ep.player_idx,
    }


class WindowSampler:
    """Yields batches of ``cfg.batch_size`` windows of ``cfg.window_ticks`` ticks.

    Train: one uniformly random offset per episode and epoch (epoch-seeded), episodes shuffled.
    Validation (``fixed_offsets``): one offset per episode drawn once from ``seed``, fixed
    across epochs, deterministic order.
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
        self.skipped_short = len(index.episodes) - len(self.valid_episodes)
        if not self.valid_episodes:
            raise ValueError(f"No episodes with length >= {self.window_ticks} in {split}")
        rng = np.random.default_rng(seed)
        self._fixed = [
            int(rng.integers(0, e.length - self.window_ticks + 1)) for e in self.valid_episodes
        ]
        log.info(
            "WindowSampler[%s]: %d/%d episodes usable (>= %d ticks), %d skipped, fixed=%s",
            split,
            len(self.valid_episodes),
            len(index.episodes),
            self.window_ticks,
            self.skipped_short,
            fixed_offsets,
        )

    def _slice(self, ep: EpisodeInfo, offset: int) -> Tuple[torch.Tensor, torch.Tensor]:
        data = self.index.load_episode(ep)
        lo = ep.start + offset
        hi = lo + self.window_ticks
        return data["x_num"][lo:hi], data["x_cat"][lo:hi]

    def __iter__(self) -> Iterator[Tuple[torch.Tensor, torch.Tensor, List[dict]]]:
        n = len(self.valid_episodes)
        epoch = 0
        x_num_batch: List[torch.Tensor] = []
        x_cat_batch: List[torch.Tensor] = []
        meta_batch: List[dict] = []
        while True:  # a partial batch carries over into the next epoch
            rng = np.random.default_rng(self.seed + epoch * 1_000_003)
            order = np.arange(n) if self.fixed_offsets else rng.permutation(n)
            for ei in order:
                ep = self.valid_episodes[int(ei)]
                if self.fixed_offsets:
                    offset = self._fixed[int(ei)]
                else:
                    offset = int(rng.integers(0, ep.length - self.window_ticks + 1))
                x_num, x_cat = self._slice(ep, offset)
                x_num_batch.append(x_num.unsqueeze(0))
                x_cat_batch.append(x_cat.unsqueeze(0))
                meta_batch.append(_window_meta(ep, offset))
                if len(x_num_batch) == self.batch_size:
                    yield torch.cat(x_num_batch, 0), torch.cat(x_cat_batch, 0), meta_batch
                    x_num_batch, x_cat_batch, meta_batch = [], [], []
            epoch += 1


def _episode_health(data: Dict[str, torch.Tensor], ep: EpisodeInfo) -> torch.Tensor:
    if "health" in data:
        return data["health"][ep.start : ep.end]
    return data["x_num"][ep.start : ep.end, _HEALTH_COL]


def _episode_enemies(data: Dict[str, torch.Tensor], ep: EpisodeInfo) -> torch.Tensor:
    if "enemies_visible" in data:
        return data["enemies_visible"][ep.start : ep.end]
    return data["x_num"][ep.start : ep.end, _ENEMIES_COL]


def _round_label(data: Dict[str, torch.Tensor], ep: EpisodeInfo, name: str) -> Optional[float]:
    lr = data.get("labels_round")
    lm = data.get("labels_mask")
    if lr is None or lm is None or lr.dim() != 2 or lr.shape[1] < len(LABELS_ROUND_COLUMNS):
        return None
    col = _LABEL_COL[name]
    if ep.ep_idx >= lr.shape[0] or float(lm[ep.ep_idx, col]) < 0.5:
        return None
    value = float(lr[ep.ep_idx, col])
    return None if value != value else value  # NaN guard


def _derive_d17_labels(
    data: Dict[str, torch.Tensor],
    ep: EpisodeInfo,
    offset: int,
    window_ticks: int,
) -> Dict[str, Optional[float]]:
    """Probe labels for the window ``[offset, offset + window_ticks)`` of episode ``ep`` (D-17).

    Episode-level labels come from ``labels_round``; the event labels look at the
    ``LABEL_HORIZON_TICKS`` ticks that follow the window INSIDE the same episode.
    ``None`` marks an undefined label: the player is already dead at the window's last tick
    (death), enemies are already visible (new contact), or the mask is off.
    """
    end = offset + window_ticks  # exclusive, relative to the episode start
    last = end - 1
    horizon = min(end + LABEL_HORIZON_TICKS, ep.length)
    health = _episode_health(data, ep)
    enemies = _episode_enemies(data, ep)

    labels: Dict[str, Optional[float]] = {
        "round_won": _round_label(data, ep, "round_won"),
        "opening_death": _round_label(data, ep, "opening_death"),
        "side": _round_label(data, ep, "side_is_ct"),
    }
    if float(health[last]) <= 0.0:
        labels["death_within_2s"] = None
    else:
        future = health[end:horizon]
        labels["death_within_2s"] = 1.0 if future.numel() and float(future.min()) <= 0.0 else 0.0

    future_enemies = enemies[end:horizon]
    any_visible = 1.0 if future_enemies.numel() and float(future_enemies.max()) > 0.0 else 0.0
    labels["enemy_visible_any_within_2s"] = any_visible if end < ep.length else None
    if float(enemies[last]) > 0.0:
        labels["contact_new_within_2s"] = None
    else:
        labels["contact_new_within_2s"] = any_visible
    return labels


def probe_batch(
    index: ShardIndex,
    cfg: JepaV2Config,
    n_windows: Optional[int] = None,
    seed: int = 42,
) -> Tuple[torch.Tensor, torch.Tensor, List[dict], Dict[str, np.ndarray]]:
    """Fixed windows (with replacement over episodes) plus their D-17 labels.

    Returns ``(x_num, x_cat, meta_list, labels_dict)``; each label array holds NaN where the
    label is undefined for that window.
    """
    n = cfg.probe_windows if n_windows is None else n_windows
    rng = np.random.default_rng(seed)
    valid = [e for e in index.episodes if e.length >= cfg.window_ticks]
    if not valid:
        raise ValueError("No episode is long enough for a probe window")
    x_num_list: List[torch.Tensor] = []
    x_cat_list: List[torch.Tensor] = []
    meta_list: List[dict] = []
    label_rows: List[Dict[str, Optional[float]]] = []
    while len(x_num_list) < n:
        ep = valid[int(rng.integers(0, len(valid)))]
        offset = int(rng.integers(0, ep.length - cfg.window_ticks + 1))
        data = index.load_episode(ep)
        lo, hi = ep.start + offset, ep.start + offset + cfg.window_ticks
        x_num_list.append(data["x_num"][lo:hi].unsqueeze(0))
        x_cat_list.append(data["x_cat"][lo:hi].unsqueeze(0))
        meta_list.append(_window_meta(ep, offset))
        label_rows.append(_derive_d17_labels(data, ep, offset, cfg.window_ticks))
    labels: Dict[str, np.ndarray] = {
        name: np.array(
            [np.nan if row.get(name) is None else row[name] for row in label_rows],
            dtype=np.float64,
        )
        for name in PROBE_LABEL_NAMES
    }
    return torch.cat(x_num_list, 0), torch.cat(x_cat_list, 0), meta_list, labels
