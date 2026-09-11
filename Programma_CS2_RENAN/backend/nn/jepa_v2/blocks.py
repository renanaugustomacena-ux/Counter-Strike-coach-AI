"""Transformer building blocks for JEPA v2.

RMSNorm, SwiGLU FFN, RoPE, QK-norm causal self-attention, pre-norm
TransformerBlock, and FiLM conditioning (CORREZIONE_NUCLEO_NEURALE
Parte II section 10, Parte III section 4.3).
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class RMSNorm(nn.Module):
    """Root-mean-square layer normalisation (Parte II section 10.1)."""

    def __init__(self, d: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        rms = x.float().square().mean(dim=-1, keepdim=True).add(self.eps).rsqrt()
        return (x.float() * rms).to(x.dtype) * self.weight


class SwiGLU(nn.Module):
    """SwiGLU feed-forward: W2(SiLU(xW1) * xV) (Parte II section 10.2).

    ``d_ff`` should already be the rounded value (see ``JepaV2Config.d_ff``).
    """

    def __init__(self, d: int, d_ff: int):
        super().__init__()
        self.w1 = nn.Linear(d, d_ff, bias=False)
        self.v = nn.Linear(d, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w2(F.silu(self.w1(x)) * self.v(x))


def _build_rope_cache(
    seq_len: int, d_head: int, theta: float, device: torch.device
) -> torch.Tensor:
    """Precompute complex-exponential RoPE frequencies for ``seq_len`` positions."""
    pos = torch.arange(seq_len, device=device, dtype=torch.float32)
    dim_pairs = d_head // 2
    freqs = 1.0 / (
        theta ** (torch.arange(0, d_head, 2, device=device, dtype=torch.float32) / d_head)
    )
    angles = pos.unsqueeze(1) * freqs.unsqueeze(0)  # (T, dim_pairs)
    return torch.polar(torch.ones_like(angles), angles)  # (T, dim_pairs)


def _apply_rope(x: torch.Tensor, freqs: torch.Tensor) -> torch.Tensor:
    """Rotate query/key by precomputed frequencies.

    ``x``: (B, H, T, d_head).  ``freqs``: (T, d_head//2).
    """
    # pair consecutive dims as complex
    x_complex = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
    out = torch.view_as_real(x_complex * freqs.unsqueeze(0).unsqueeze(0))
    return out.reshape(x.shape).to(x.dtype)


class CausalSelfAttention(nn.Module):
    """Multi-head causal self-attention with QK-norm and RoPE.

    Parte II section 10.3-10.5, Parte III section 4.3.
    """

    def __init__(self, d: int, n_heads: int, rope_theta: float = 10_000.0, dropout: float = 0.0):
        super().__init__()
        assert d % n_heads == 0
        self.n_heads = n_heads
        self.d_head = d // n_heads
        self.rope_theta = rope_theta
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.q_norm = nn.LayerNorm(self.d_head)
        self.k_norm = nn.LayerNorm(self.d_head)
        self.out_proj = nn.Linear(d, d, bias=False)
        self.dropout = dropout

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t, d = x.shape
        qkv = self.qkv(x).reshape(b, t, 3, self.n_heads, self.d_head)
        q, k, v = qkv.unbind(dim=2)  # each (B, T, H, d_head)
        q = q.transpose(1, 2)  # (B, H, T, d_head)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)
        q = self.q_norm(q)
        k = self.k_norm(k)
        freqs = _build_rope_cache(t, self.d_head, self.rope_theta, x.device)
        q = _apply_rope(q, freqs)
        k = _apply_rope(k, freqs)
        drop = self.dropout if self.training else 0.0
        out = F.scaled_dot_product_attention(q, k, v, is_causal=True, dropout_p=drop)
        out = out.transpose(1, 2).reshape(b, t, d)
        return self.out_proj(out)


class TransformerBlock(nn.Module):
    """Pre-norm causal Transformer block: Attn + SwiGLU (Parte III section 4.3)."""

    def __init__(
        self, d: int, n_heads: int, d_ff: int, rope_theta: float = 10_000.0, dropout: float = 0.0
    ):
        super().__init__()
        self.norm1 = RMSNorm(d)
        self.attn = CausalSelfAttention(d, n_heads, rope_theta, dropout)
        self.norm2 = RMSNorm(d)
        self.ffn = SwiGLU(d, d_ff)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x))
        x = x + self.ffn(self.norm2(x))
        return x


class FiLM(nn.Module):
    """Feature-wise Linear Modulation with zero-initialised final weights.

    ``y = (1 + gamma) * x + beta`` starts as identity when weights are zero
    (adaLN-Zero style).  Parte III section 4.3, Parte II section 10.7.
    """

    def __init__(self, cond_dim: int, d: int):
        super().__init__()
        self.proj = nn.Linear(cond_dim, 2 * d)
        nn.init.zeros_(self.proj.weight)
        nn.init.zeros_(self.proj.bias)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        """``x``: (B, T, d).  ``cond``: (B, cond_dim) or broadcastable."""
        gamma_beta = self.proj(cond)
        if gamma_beta.dim() == 2:
            gamma_beta = gamma_beta.unsqueeze(1)  # (B, 1, 2d)
        d = x.size(-1)
        gamma = gamma_beta[..., :d]
        beta = gamma_beta[..., d:]
        return (1.0 + gamma) * x + beta
