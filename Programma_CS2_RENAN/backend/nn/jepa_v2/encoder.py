"""EncoderV2 — causal Transformer encoder for JEPA v2.

Taps are collected at every layer boundary for SIGReg and probes.  The served
representation is ``taps[served_tap]`` WITHOUT a final norm — a separate
``head_norm`` RMSNorm exists for downstream heads but is NOT applied to the
served output (CORREZIONE_NUCLEO_NEURALE Parte III section 4.5, D-15).
"""

from __future__ import annotations

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.jepa_v2.blocks import RMSNorm, TransformerBlock
from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.tokenizer import TokenizerV2


class EncoderV2(nn.Module):
    """JEPA v2 causal Transformer encoder (Parte III section 4.5, C-5)."""

    def __init__(self, cfg: JepaV2Config):
        super().__init__()
        self.cfg = cfg
        self.tokenizer = TokenizerV2(cfg)
        self.blocks = nn.ModuleList(
            [
                TransformerBlock(cfg.d_model, cfg.n_heads, cfg.d_ff, cfg.rope_theta, cfg.dropout)
                for _ in range(cfg.n_layers)
            ]
        )
        self.head_norm = RMSNorm(cfg.d_model)

    def forward(
        self,
        x_num: torch.Tensor,
        x_cat: torch.Tensor,
        return_taps: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]]:
        """Encode tick-level features into a token-level latent sequence.

        Args:
            x_num: (B, L, 21) float — raw numeric features.
            x_cat: (B, L, 3) int64 — categorical indices.
            return_taps: if True, also return the list of intermediate
                representations ``[h0, h1, ..., h_{n_layers}]``.

        Returns:
            ``z`` = ``taps[cfg.served_tap]`` (B, T, d_model) WITHOUT any norm
            (Parte III section 4.5, D-16), or ``(z, taps)`` when
            ``return_taps=True``.  Apply :meth:`for_heads` to obtain the
            RMS-normalised view for downstream heads.
        """
        h = self.tokenizer(x_num, x_cat)  # (B, T, d_model)
        taps: list[torch.Tensor] = [h]
        for blk in self.blocks:
            h = blk(h)
            taps.append(h)
        z = taps[self.cfg.served_tap]
        if return_taps:
            return z, taps
        return z

    def for_heads(self, z: torch.Tensor) -> torch.Tensor:
        """RMS-normalised view of a served representation, for heads only.

        Never feed this to SIGReg or to the prediction loss (Parte II
        section 2.3.3: a fixed-norm manifold cannot be Gaussian).
        """
        return self.head_norm(z)
