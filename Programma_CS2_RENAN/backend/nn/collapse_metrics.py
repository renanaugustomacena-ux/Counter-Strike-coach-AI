"""Representation-collapse metrics for JEPA embeddings.

Pure functions over tensors: no TensorBoard, no model coupling, no I/O.

Collapse is the failure where the encoder emits near-constant embeddings. The
predictor then satisfies its objective trivially and the loss curve looks
healthy while nothing has been learned. The InfoNCE / concept / diversity
losses already logged cannot distinguish that state from success; these
metrics can.

`effective_rank` follows RankMe (Garrido et al., 2023): the entropy-based
effective rank of the embedding matrix's singular values. Note it is computed
on the *uncentered* matrix deliberately — centering first would subtract the
dominant mean direction that collapse produces, leaving isotropic residual
noise that scores as high rank, i.e. reporting "healthy" during collapse.
"""

from typing import Dict, Iterable

import torch

_EPS = 1e-12

_ZERO: Dict[str, float] = {
    "std_mean": 0.0,
    "std_min": 0.0,
    "effective_rank": 0.0,
    "cosine_offdiag_mean": 0.0,
}


def compute_collapse_metrics(embeddings: torch.Tensor) -> Dict[str, float]:
    """Return collapse indicators for an embedding matrix.

    Args:
        embeddings: tensor of shape [N, D], or any shape whose trailing
            dimension is the feature dimension (it is flattened to [-1, D]).

    Returns:
        dict with keys std_mean, std_min, effective_rank, cosine_offdiag_mean.
        All-zeros when fewer than 2 samples are available.

    Collapse signatures: std_mean and std_min approach 0, effective_rank
    approaches 1, cosine_offdiag_mean approaches 1.
    """
    e = embeddings.detach().float()
    if e.dim() > 2:
        e = e.reshape(-1, e.shape[-1])
    if e.dim() != 2 or e.shape[0] < 2:
        return dict(_ZERO)

    n = e.shape[0]
    # L2-normalize so a model that merely shrinks its output magnitude is not
    # mistaken for one that collapsed in direction.
    z = torch.nn.functional.normalize(e, dim=1, eps=_EPS)

    std = z.std(dim=0)

    sv = torch.linalg.svdvals(z)
    p = sv / sv.sum().clamp(min=_EPS)
    entropy = -(p * torch.log(p.clamp(min=_EPS))).sum()
    effective_rank = float(torch.exp(entropy))

    sim = z @ z.T
    offdiag = (sim.sum() - torch.diagonal(sim).sum()) / (n * (n - 1))

    return {
        "std_mean": float(std.mean()),
        "std_min": float(std.min()),
        "effective_rank": effective_rank,
        "cosine_offdiag_mean": float(offdiag),
    }


def compute_ema_drift(
    online_params: Iterable[torch.Tensor],
    target_params: Iterable[torch.Tensor],
) -> float:
    """L2 distance between online and EMA-target parameter sets.

    Approaching 0 means the target encoder has stopped moving — a corroborating
    collapse signal in EMA-based JEPA training.
    """
    total = 0.0
    for p, q in zip(online_params, target_params):
        diff = p.detach().float() - q.detach().float()
        total += float(torch.sum(diff * diff))
    return float(total**0.5)
