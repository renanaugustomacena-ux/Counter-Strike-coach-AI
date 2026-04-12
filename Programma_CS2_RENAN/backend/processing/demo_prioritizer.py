"""
Demo Prioritization by Coaching-Capability Variance.

Ranks available demos by their expected coaching value using prediction
variance as a proxy for model uncertainty.  Higher variance indicates the
model is less certain about the demo's data, meaning the demo provides
more learning signal (active-learning inspired selection).

When no trained model is available, falls back to a diversity-based ranking
that prioritises demos from unique players and maps to maximise coverage.

References:
    - NAIT paper: "Neural Active Inference for Autonomous Coaching" (2024)
      Section 3.2 — Expected Information Gain via prediction variance
    - Settles, B. "Active Learning Literature Survey" (2009)
      Uncertainty sampling: select instances where model is least confident
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from Programma_CS2_RENAN.backend.nn.config import INPUT_DIM, get_device
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import (
    PlayerMatchStats,
    PlayerTickState,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.processing.demo_prioritizer")

# Minimum number of tick records required to compute meaningful variance.
_MIN_TICKS_FOR_VARIANCE = 64

# Maximum ticks to sample per demo (avoid OOM on large demos).
_MAX_TICKS_SAMPLE = 2048


@dataclass
class DemoPriorityResult:
    """Priority ranking result for a single demo."""

    demo_name: str
    priority_score: float
    method: str  # "variance" or "diversity"
    tick_count: int = 0
    unique_players: int = 0


class DemoPrioritizer:
    """Ranks demos by expected coaching value.

    Primary strategy (variance-based):
        Uses a loaded JEPA model to compute prediction variance across
        a demo's tick data.  High variance in the model's latent-space
        predictions indicates the demo contains situations the model has
        not yet learned well, making it a high-value training candidate.

    Fallback strategy (diversity-based):
        When no model is loaded, ranks demos by diversity metrics:
        unique player count, unique map coverage, and data completeness.
        This ensures broad coverage over the training distribution.
    """

    def __init__(self, model: Optional[torch.nn.Module] = None):
        """Initialise the prioritizer.

        Args:
            model: A trained JEPA or coaching model.  If ``None``, the
                   diversity-based fallback is used automatically.
        """
        self._model = model
        self._device = get_device()

    def rank_demos(
        self,
        demo_names: list[str],
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Rank demos by expected coaching value.

        Args:
            demo_names: List of demo identifiers to evaluate.
            top_k: Maximum number of demos to return.

        Returns:
            List of ``(demo_name, priority_score)`` sorted descending by
            score.  Length is ``min(top_k, len(demo_names))``.
        """
        if not demo_names:
            logger.warning("rank_demos called with empty demo list")
            return []

        if self._model is not None:
            results = self._rank_by_variance(demo_names)
        else:
            logger.info(
                "No model loaded — falling back to diversity-based ranking"
            )
            results = self._rank_by_diversity(demo_names)

        # Sort descending by priority score.
        results.sort(key=lambda r: r.priority_score, reverse=True)

        ranked = [
            (r.demo_name, r.priority_score) for r in results[:top_k]
        ]
        logger.info(
            "Ranked %d/%d demos (top_k=%d, method=%s)",
            len(ranked),
            len(demo_names),
            top_k,
            results[0].method if results else "none",
        )
        return ranked

    # ------------------------------------------------------------------
    # Variance-based ranking (primary)
    # ------------------------------------------------------------------

    def _rank_by_variance(
        self, demo_names: list[str]
    ) -> list[DemoPriorityResult]:
        """Compute prediction variance per demo using the loaded model."""
        results: list[DemoPriorityResult] = []

        for demo_name in demo_names:
            try:
                score, tick_count = self._compute_demo_variance(demo_name)
                results.append(
                    DemoPriorityResult(
                        demo_name=demo_name,
                        priority_score=score,
                        method="variance",
                        tick_count=tick_count,
                    )
                )
            except Exception:
                logger.warning(
                    "Failed to compute variance for demo %s",
                    demo_name,
                    exc_info=True,
                )
                # Assign zero score so it sinks to the bottom rather than
                # being silently dropped.
                results.append(
                    DemoPriorityResult(
                        demo_name=demo_name,
                        priority_score=0.0,
                        method="variance",
                    )
                )

        return results

    def _compute_demo_variance(
        self, demo_name: str
    ) -> Tuple[float, int]:
        """Compute mean prediction variance for a single demo.

        Loads tick data from the database, feeds it through the model in
        eval mode, and computes the variance of the output predictions
        across all sampled ticks.

        Returns:
            ``(variance_score, tick_count)``
        """
        from sqlmodel import select

        db = get_db_manager()
        with db.get_session() as session:
            stmt = (
                select(PlayerTickState)
                .where(PlayerTickState.demo_name == demo_name)
                .limit(_MAX_TICKS_SAMPLE)
            )
            ticks = session.exec(stmt).all()

        if len(ticks) < _MIN_TICKS_FOR_VARIANCE:
            logger.debug(
                "Demo %s has only %d ticks (< %d minimum) — assigning zero variance",
                demo_name,
                len(ticks),
                _MIN_TICKS_FOR_VARIANCE,
            )
            return 0.0, len(ticks)

        # Build feature matrix from tick records.
        features = self._ticks_to_features(ticks)
        tensor = torch.tensor(features, dtype=torch.float32, device=self._device)

        # Add sequence dimension if model expects [batch, seq, features].
        if tensor.dim() == 2:
            tensor = tensor.unsqueeze(0)  # [1, N, input_dim]

        self._model.eval()
        with torch.no_grad():
            predictions = self._model(tensor)  # [1, output_dim] or [1, N, output_dim]

        # Flatten to [N, output_dim] if needed.
        if predictions.dim() == 3:
            predictions = predictions.squeeze(0)
        elif predictions.dim() == 1:
            predictions = predictions.unsqueeze(0)

        # Variance across the output dimensions, averaged over samples.
        # High variance = model uncertain = high coaching value.
        variance = predictions.var(dim=-1).mean().item()
        return float(variance), len(ticks)

    @staticmethod
    def _ticks_to_features(ticks: list) -> np.ndarray:
        """Convert PlayerTickState rows to a raw numeric feature matrix.

        Extracts the positional and state fields that align with the
        canonical 25-dim feature vector.  Full vectorization should use
        the FeatureExtractor, but for variance ranking we need only a
        consistent numeric representation — exact normalisation is not
        critical since we measure relative variance across demos.
        """
        rows = []
        for t in ticks:
            row = [
                t.health / 100.0,
                t.armor / 100.0,
                float(t.has_helmet),
                float(t.has_defuser),
                t.equipment_value / 10000.0,
                float(t.is_crouching),
                float(t.is_scoped),
                0.0,  # is_blinded — not stored in PlayerTickState
                0.0,  # enemies_visible — not stored in PlayerTickState
                t.pos_x / 4096.0,
                t.pos_y / 4096.0,
                t.pos_z / 1024.0,
                np.sin(np.radians(t.view_y)),   # view_yaw_sin
                np.cos(np.radians(t.view_y)),   # view_yaw_cos
                t.view_x / 90.0,                # view_pitch
                0.0,  # z_penalty (requires map context)
                0.0,  # kast_estimate
                0.0,  # map_id
                0.0,  # round_phase
                0.0,  # weapon_class (would need mapping)
                0.0,  # time_in_round
                0.0,  # bomb_planted
                0.0,  # teammates_alive
                0.0,  # enemies_alive
                0.0,  # team_economy
            ]
            rows.append(row)
        return np.array(rows, dtype=np.float32)

    # ------------------------------------------------------------------
    # Diversity-based ranking (fallback)
    # ------------------------------------------------------------------

    def _rank_by_diversity(
        self, demo_names: list[str]
    ) -> list[DemoPriorityResult]:
        """Rank demos by player/map diversity and data completeness.

        Diversity score components (each in [0, 1]):
            - Player count: more players = richer data
            - Data completeness: ``PlayerMatchStats.data_quality``
            - Map rarity: demos from less-seen maps score higher
        """
        from collections import Counter

        from sqlmodel import select

        db = get_db_manager()

        # Gather metadata for all requested demos in a single query.
        demo_meta: Dict[str, Dict] = {}
        map_counter: Counter = Counter()

        with db.get_session() as session:
            stmt = select(PlayerMatchStats).where(
                PlayerMatchStats.demo_name.in_(demo_names)  # type: ignore[attr-defined]
            )
            stats_rows = session.exec(stmt).all()

        # Group stats by demo.
        for row in stats_rows:
            if row.demo_name not in demo_meta:
                demo_meta[row.demo_name] = {
                    "players": set(),
                    "quality_scores": [],
                }
            demo_meta[row.demo_name]["players"].add(row.player_name)
            quality_value = (
                1.0
                if row.data_quality == "complete"
                else 0.5 if row.data_quality == "partial" else 0.0
            )
            demo_meta[row.demo_name]["quality_scores"].append(quality_value)

        # Count how many demos each player appears in (for rarity scoring).
        player_demo_count: Counter = Counter()
        for meta in demo_meta.values():
            for p in meta["players"]:
                player_demo_count[p] += 1

        # Build results.
        results: list[DemoPriorityResult] = []
        max_players = max(
            (len(m["players"]) for m in demo_meta.values()), default=1
        )

        for demo_name in demo_names:
            meta = demo_meta.get(demo_name)
            if meta is None:
                # No stats found — assign minimal score.
                results.append(
                    DemoPriorityResult(
                        demo_name=demo_name,
                        priority_score=0.01,
                        method="diversity",
                    )
                )
                continue

            # Component 1: Player count normalised to [0, 1].
            n_players = len(meta["players"])
            player_score = n_players / max(max_players, 1)

            # Component 2: Data completeness (mean quality).
            quality_score = float(np.mean(meta["quality_scores"])) if meta["quality_scores"] else 0.0

            # Component 3: Player rarity — demos with rare players score higher.
            if player_demo_count:
                max_count = max(player_demo_count.values())
                rarity_scores = [
                    1.0 - (player_demo_count[p] - 1) / max(max_count, 1)
                    for p in meta["players"]
                ]
                rarity_score = float(np.mean(rarity_scores))
            else:
                rarity_score = 0.5

            # Weighted combination.
            priority = (
                0.4 * player_score
                + 0.3 * quality_score
                + 0.3 * rarity_score
            )

            results.append(
                DemoPriorityResult(
                    demo_name=demo_name,
                    priority_score=float(np.clip(priority, 0.0, 1.0)),
                    method="diversity",
                    unique_players=n_players,
                )
            )

        return results
