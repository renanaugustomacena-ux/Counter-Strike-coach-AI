"""SIGReg — Epps-Pulley distributional regulariser toward N(0, I).

Identical to lucas-maes/le-wm ``module.py``; parity with the reference
implementations in ``tools/verify_math_claims.py:sigreg_epps_pulley`` and
``tools/measure_sigreg_sample_size.py:sigreg_reference`` is tested at
rel-tolerance 1e-5 (CORREZIONE_NUCLEO_NEURALE Parte III section 4.2).

Directions are always drawn in float32 regardless of input dtype (D-15).
Temporal SIGReg computes per-window and averages over the batch — tokens
are never pooled across windows (decisions A-12).
"""

from __future__ import annotations

import torch
import torch.nn as nn


class SIGReg(nn.Module):
    """Epps-Pulley SIGReg statistic with trapezoidal quadrature."""

    def __init__(self, knots: int = 17, num_proj: int = 1024, t_max: float = 3.0):
        super().__init__()
        t = torch.linspace(0.0, t_max, knots)
        dt = t_max / (knots - 1)
        weights = torch.full((knots,), 2.0 * dt)
        weights[0] = dt
        weights[-1] = dt
        phi = torch.exp(-t.square() / 2.0)
        self.register_buffer("t", t)
        self.register_buffer("phi", phi)
        self.register_buffer("weights", weights * phi)
        self.num_proj = num_proj

    def forward(self, proj: torch.Tensor, generator: torch.Generator | None = None) -> torch.Tensor:
        """Compute the statistic.  Axis -2 is the *sample* dimension.

        Args:
            proj: ``(..., N, D)`` — the last two axes are (sample, features).
            generator: seeded Generator for direction sampling.

        Returns:
            Scalar loss averaged over M directions and leading batch dims.
        """
        n = proj.size(-2)
        d = proj.size(-1)
        # D-15: directions in float32; preserve float64 for gradcheck
        compute_dtype = torch.float64 if proj.dtype == torch.float64 else torch.float32
        a = torch.randn(
            d, self.num_proj, device=proj.device, dtype=compute_dtype, generator=generator
        )
        a = a / a.norm(p=2, dim=0, keepdim=True)

        proj_f = proj.to(compute_dtype)
        t = self.t.to(compute_dtype)
        phi = self.phi.to(compute_dtype)
        w = self.weights.to(compute_dtype)
        x_t = (proj_f @ a).unsqueeze(-1) * t  # (..., N, M, K)
        err = (x_t.cos().mean(-3) - phi).square() + x_t.sin().mean(-3).square()
        return ((err @ w) * n).mean()


def sigreg_batch(u: torch.Tensor, reg: SIGReg, g: torch.Generator | None = None) -> torch.Tensor:
    """Batch SIGReg: for each time-step t the B windows form the sample.

    ``u``: (B, T, d).  LeWM Algorithm 3.
    """
    return reg(u.transpose(0, 1), g)


def sigreg_temporal(u: torch.Tensor, reg: SIGReg, g: torch.Generator | None = None) -> torch.Tensor:
    """Temporal SIGReg: for each window the T tokens form the sample.

    ``u``: (B, T, d).  LeNEPA equation 2.  Result is averaged over the batch.
    """
    return reg(u, g)
