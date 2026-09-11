"""ProjectorV2 — MLP projector for JEPA v2 latent space.

Linear(d_model, proj_hidden) -> GELU -> Linear(proj_hidden, proj_out) with
no normalisation layer ("Guillotine" — discarded at inference).
CORREZIONE_NUCLEO_NEURALE Parte III section 4.5, C-6.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config


class ProjectorV2(nn.Module):
    """d_model -> proj_hidden -> proj_out, GELU, no final norm (D-15)."""

    def __init__(self, cfg: JepaV2Config):
        super().__init__()
        self.fc1 = nn.Linear(cfg.d_model, cfg.proj_hidden)
        self.fc2 = nn.Linear(cfg.proj_hidden, cfg.proj_out)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(torch.nn.functional.gelu(self.fc1(x)))
