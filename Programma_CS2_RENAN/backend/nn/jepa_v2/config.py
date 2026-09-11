"""JepaV2Config — frozen dataclass holding all architectural and training
hyperparameters for the JEPA v2 encoder (CORREZIONE_NUCLEO_NEURALE Parte III
section 4.1, constants C-1..C-9).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class JepaV2Config:
    # --- schema ---
    schema_id: str = "cs2_v2"
    numeric_dim: int = 21
    cat_vocab_sizes: tuple[int, ...] = (10, 9, 3)
    cat_embed_dims: tuple[int, ...] = (4, 4, 2)

    # --- tokeniser / window ---
    patch_ticks: int = 8
    tokens_per_window: int = 48
    d_model: int = 128
    n_layers: int = 4
    n_heads: int = 4
    ffn_mult: int = 4
    dropout: float = 0.1
    rope_theta: float = 10_000.0

    # --- projector / predictor ---
    proj_hidden: int = 256
    proj_out: int = 64
    predictor_layers: int = 2

    # --- loss ---
    horizons: tuple[int, ...] = (1, 4, 16)
    w_next: float = 1.0
    w_multi: float = 0.5
    lambda_sigreg_temporal: float = 2.5
    lambda_sigreg_batch: float = 0.1
    sigreg_num_proj: int = 1024
    sigreg_knots: int = 17
    sigreg_t_max: float = 3.0
    sigreg_taps: tuple[int, ...] = (0, -1)
    served_tap: int = 2

    # --- training ---
    batch_size: int = 128
    steps: int = 20_000
    warmup_steps: int = 1000
    lr_max: float = 1e-4
    lr_min: float = 1e-6
    weight_decay: float = 0.05
    betas: tuple[float, float] = (0.9, 0.99)
    grad_clip: float = 1.0
    dtype: str = "bf16"
    seed: int = 0

    # --- telemetry / abort ---
    probe_every: int = 500
    probe_windows: int = 4096
    abort_rankme_below: float = 8.0
    abort_std_min_below: float = 1e-3
    warn_rankme_ratio_below: float = 0.25

    # --- computed properties ---
    @property
    def d_ff(self) -> int:
        """SwiGLU hidden dim: int(2/3 * ffn_mult * d_model) rounded up to
        a multiple of 8 (Parte III section 4.3, D-15)."""
        raw = int(2 / 3 * self.ffn_mult * self.d_model)
        return math.ceil(raw / 8) * 8

    @property
    def d_num(self) -> int:
        """Conv1d output channels = d_model minus total categorical embedding
        width (D-15)."""
        return self.d_model - sum(self.cat_embed_dims)

    @property
    def window_ticks(self) -> int:
        return self.tokens_per_window * self.patch_ticks

    @property
    def d_head(self) -> int:
        return self.d_model // self.n_heads

    def validate(self) -> None:
        """Check internal consistency; raises ValueError on failure."""
        if self.d_model % self.n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads")
        if len(self.cat_vocab_sizes) != len(self.cat_embed_dims):
            raise ValueError("cat_vocab_sizes and cat_embed_dims must match in length")
        if self.d_num <= 0:
            raise ValueError(f"d_num must be positive, got {self.d_num}")
        if not self.horizons:
            raise ValueError("horizons must be non-empty")
        if self.patch_ticks <= 0:
            raise ValueError("patch_ticks must be positive")
        if not 0 <= self.served_tap <= self.n_layers:
            raise ValueError(f"served_tap must be in [0, n_layers], got {self.served_tap}")
        for k in self.sigreg_taps:
            if not -(self.n_layers + 1) <= k <= self.n_layers:
                raise ValueError(
                    f"sigreg tap {k} outside the taps list of length {self.n_layers + 1}"
                )
        if self.horizons[0] != 1:
            raise ValueError("horizons[0] must be 1: L_next is the one-token prediction")
        if max(self.horizons) >= self.tokens_per_window:
            raise ValueError("every horizon must be shorter than the window")
        if self.tokens_per_window < 16 or self.batch_size < 32:
            raise ValueError(
                "SIGReg needs T >= 16 tokens and B >= 32 windows (Parte II section 2.3.3)"
            )
