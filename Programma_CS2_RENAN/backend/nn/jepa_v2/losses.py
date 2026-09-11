"""JEPA v2 loss function.

L = w_next * L_next + w_multi * L_multi + lambda_T * L_sig_T + lambda_B * L_sig_B

All prediction terms are MSE in projector space.  No EMA, no stop-gradient,
no negatives, no queue.  The projector is shared between prediction and target
(CORREZIONE_NUCLEO_NEURALE Parte III section 4.6, C-8).

S_straight (temporal straightness proxy) is returned as a diagnostic but does
not enter the loss (Parte II section 6.3).
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.sigreg import SIGReg, sigreg_batch, sigreg_temporal


def _s_straight(z: torch.Tensor) -> torch.Tensor:
    """Temporal straightness: mean cosine between consecutive latent deltas.

    S_straight ~ 1 means the trajectory is a straight line in latent space.
    Parte II section 6.3.
    """
    v = z[:, 1:, :] - z[:, :-1, :]  # (B, T-1, d)
    if v.size(1) < 2:
        return torch.tensor(0.0, device=z.device, dtype=z.dtype)
    v1 = F.normalize(v[:, :-1], dim=-1)
    v2 = F.normalize(v[:, 1:], dim=-1)
    return (v1 * v2).sum(dim=-1).mean()


def jepa_v2_loss(
    z: torch.Tensor,
    taps: list[torch.Tensor],
    pred_fn: torch.nn.Module,
    proj: torch.nn.Module,
    cfg: JepaV2Config,
    sigreg: SIGReg,
    step: int,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Compute the full JEPA v2 loss.

    Args:
        z: (B, T, d_model) — encoder output.
        taps: list of intermediate representations ``[h0, h1, ..., h_{n_layers}]``.
        pred_fn: PredictorV2 module.
        proj: ProjectorV2 module (shared for prediction and target).
        cfg: JepaV2Config.
        sigreg: SIGReg module.
        step: global training step (seeds the direction generator).

    Returns:
        ``(loss, info_dict)`` where info_dict has per-component losses and
        S_straight.
    """
    g = torch.Generator(device=z.device).manual_seed(cfg.seed * 1_000_003 + step)
    u = proj(z)  # (B, T, proj_out)

    # L_next: next-token prediction (Parte III section 4.6)
    zhat1 = pred_fn(z, horizon_idx=0)
    l_next = F.mse_loss(proj(zhat1[:, :-1]), u[:, 1:])

    # L_multi: multi-horizon prediction over horizons[1:]
    l_multi = torch.tensor(0.0, device=z.device, dtype=z.dtype)
    n_multi = max(1, len(cfg.horizons) - 1)
    for hi, h in enumerate(cfg.horizons[1:], start=1):
        zh = pred_fn(z, horizon_idx=hi)
        l_multi = l_multi + F.mse_loss(proj(zh[:, :-h]), u[:, h:])
    l_multi = l_multi / n_multi

    # SIGReg temporal on projector output of selected taps
    l_sig_t = torch.tensor(0.0, device=z.device, dtype=z.dtype)
    for k in cfg.sigreg_taps:
        l_sig_t = l_sig_t + sigreg_temporal(proj(taps[k]), sigreg, g)
    l_sig_t = l_sig_t / len(cfg.sigreg_taps)

    # SIGReg batch on the projected encoder output
    l_sig_b = sigreg_batch(u, sigreg, g)

    loss = (
        cfg.w_next * l_next
        + cfg.w_multi * l_multi
        + cfg.lambda_sigreg_temporal * l_sig_t
        + cfg.lambda_sigreg_batch * l_sig_b
    )

    info = {
        "L_next": float(l_next.detach()),
        "L_multi": float(l_multi.detach()),
        "sig_T": float(l_sig_t.detach()),
        "sig_B": float(l_sig_b.detach()),
        "S_straight": float(_s_straight(z.detach())),
        "loss": float(loss.detach()),
    }
    return loss, info
