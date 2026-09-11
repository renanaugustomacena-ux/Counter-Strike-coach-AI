"""TokenizerV2 — patch-based tokeniser for the JEPA v2 encoder.

Conv1d on numeric features with patch_ticks kernel/stride; categorical
embeddings per tick averaged over the patch; concat and project to d_model.
No absolute positions — RoPE handles relative indexing in the attention
(CORREZIONE_NUCLEO_NEURALE Parte III section 4.4, D-15).
"""

from __future__ import annotations

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config


class TokenizerV2(nn.Module):
    """Convert raw tick-level features into a sequence of token embeddings."""

    def __init__(self, cfg: JepaV2Config):
        super().__init__()
        self.patch_ticks = cfg.patch_ticks
        self.conv = nn.Conv1d(
            cfg.numeric_dim, cfg.d_num, kernel_size=cfg.patch_ticks, stride=cfg.patch_ticks
        )
        self.cat_embeds = nn.ModuleList(
            [nn.Embedding(v, e) for v, e in zip(cfg.cat_vocab_sizes, cfg.cat_embed_dims)]
        )
        cat_total = sum(cfg.cat_embed_dims)
        self.proj = nn.Linear(cfg.d_num + cat_total, cfg.d_model)

    def forward(self, x_num: torch.Tensor, x_cat: torch.Tensor) -> torch.Tensor:
        """Tokenise raw features.

        Args:
            x_num: (B, L, numeric_dim) float — L = tokens_per_window * patch_ticks.
            x_cat: (B, L, n_cat) int64 — categorical indices.

        Returns:
            (B, T, d_model) token embeddings where T = L / patch_ticks.
        """
        # numeric path: Conv1d expects (B, C, L)
        num_tokens = self.conv(x_num.transpose(1, 2)).transpose(1, 2)  # (B, T, d_num)

        # categorical path: embed each tick then average over the patch
        b, l, n_cat = x_cat.shape
        t = l // self.patch_ticks
        cat_parts: list[torch.Tensor] = []
        for i, emb in enumerate(self.cat_embeds):
            e = emb(x_cat[..., i])  # (B, L, e_i)
            e = e.reshape(b, t, self.patch_ticks, -1).mean(dim=2)  # (B, T, e_i)
            cat_parts.append(e)
        cat_tokens = torch.cat(cat_parts, dim=-1)  # (B, T, sum(cat_embed_dims))

        return self.proj(torch.cat([num_tokens, cat_tokens], dim=-1))
