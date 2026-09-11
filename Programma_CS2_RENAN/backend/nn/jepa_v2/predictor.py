"""PredictorV2 — horizon-conditioned causal predictor for JEPA v2.

Two causal Transformer blocks with FiLM conditioning on a learned horizon
embedding.  Predicts the latent z_{t+h} from z_{<=t} for each horizon h.
CORREZIONE_NUCLEO_NEURALE Parte III section 4.5, C-7.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.jepa_v2.blocks import FiLM, TransformerBlock
from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config


class PredictorV2(nn.Module):
    """Causal predictor with FiLM horizon conditioning (Parte III section 4.5)."""

    def __init__(self, cfg: JepaV2Config):
        super().__init__()
        n_horizons = len(cfg.horizons)
        self.horizon_embed = nn.Embedding(n_horizons, cfg.d_model)
        self.blocks = nn.ModuleList()
        self.films = nn.ModuleList()
        for _ in range(cfg.predictor_layers):
            self.blocks.append(
                TransformerBlock(cfg.d_model, cfg.n_heads, cfg.d_ff, cfg.rope_theta, cfg.dropout)
            )
            self.films.append(FiLM(cfg.d_model, cfg.d_model))

    def forward(self, z: torch.Tensor, horizon_idx: int) -> torch.Tensor:
        """Predict future latents.

        Args:
            z: (B, T, d_model) — encoder output.
            horizon_idx: index into ``cfg.horizons`` (0-based).

        Returns:
            (B, T, d_model) — predicted latent at each position.
        """
        h_emb = self.horizon_embed(torch.tensor(horizon_idx, device=z.device))  # (d_model,)
        h = z
        for blk, film in zip(self.blocks, self.films):
            h = blk(h)
            h = film(h, h_emb)
        return h
