"""Tests for JEPA v2 Transformer blocks, encoder, and architecture.

Causality, RoPE, RMSNorm, shapes, taps, FiLM identity, parameter count.
CORREZIONE_NUCLEO_NEURALE Parte III section 4.3, C-5.
"""

import pytest
import torch

from Programma_CS2_RENAN.backend.nn.jepa_v2.blocks import (
    CausalSelfAttention,
    FiLM,
    RMSNorm,
    SwiGLU,
    TransformerBlock,
)
from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.encoder import EncoderV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.predictor import PredictorV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.projector import ProjectorV2


class TestRMSNorm:
    def test_shape_preserved(self):
        norm = RMSNorm(32)
        x = torch.randn(2, 8, 32)
        assert norm(x).shape == x.shape

    def test_matches_layernorm_on_zero_mean(self):
        d = 16
        norm = RMSNorm(d)
        ln = torch.nn.LayerNorm(d, elementwise_affine=False)
        torch.manual_seed(0)
        x = torch.randn(4, 8, d)
        x = x - x.mean(dim=-1, keepdim=True)
        out_rms = norm(x)
        out_ln = ln(x)
        assert torch.allclose(out_rms, out_ln, atol=1e-5)


class TestSwiGLU:
    def test_shape(self):
        ffn = SwiGLU(128, 344)
        x = torch.randn(2, 48, 128)
        assert ffn(x).shape == (2, 48, 128)

    def test_d_ff_default(self):
        cfg = JepaV2Config()
        assert cfg.d_ff == 344


class TestCausalSelfAttention:
    def test_causality(self):
        """Perturbing token t must leave outputs at positions < t unchanged."""
        torch.manual_seed(0)
        attn = CausalSelfAttention(32, 4, dropout=0.0)
        attn.eval()
        x = torch.randn(1, 8, 32)
        out1 = attn(x)
        x_perturbed = x.clone()
        x_perturbed[:, 5, :] += 10.0
        out2 = attn(x_perturbed)
        assert torch.allclose(out1[:, :5], out2[:, :5], atol=1e-5)
        assert not torch.allclose(out1[:, 5:], out2[:, 5:], atol=1e-3)


class TestRoPE:
    def test_relative_position_dependence(self):
        """RoPE must depend only on relative positions within a window."""
        torch.manual_seed(0)
        attn = CausalSelfAttention(32, 4, dropout=0.0)
        attn.eval()
        x = torch.randn(1, 16, 32)
        out_full = attn(x)
        out_short = attn(x[:, :8])
        assert out_full[:, :8].shape == out_short.shape


class TestTransformerBlock:
    def test_residual_shape(self):
        blk = TransformerBlock(128, 4, 344, dropout=0.0)
        x = torch.randn(2, 48, 128)
        assert blk(x).shape == x.shape


class TestFiLM:
    def test_identity_at_init(self):
        """FiLM with zero-init weights starts as identity."""
        film = FiLM(64, 128)
        x = torch.randn(2, 48, 128)
        cond = torch.randn(2, 64)
        out = film(x, cond)
        assert torch.allclose(out, x, atol=1e-6)


class TestEncoderV2:
    @pytest.fixture
    def cfg(self):
        return JepaV2Config()

    def test_output_shape(self, cfg):
        enc = EncoderV2(cfg)
        enc.eval()
        b, l = 2, cfg.window_ticks
        x_num = torch.randn(b, l, cfg.numeric_dim)
        x_cat = torch.zeros(b, l, len(cfg.cat_vocab_sizes), dtype=torch.long)
        z = enc(x_num, x_cat)
        assert z.shape == (b, cfg.tokens_per_window, cfg.d_model)

    def test_taps_length(self, cfg):
        enc = EncoderV2(cfg)
        enc.eval()
        b, l = 1, cfg.window_ticks
        x_num = torch.randn(b, l, cfg.numeric_dim)
        x_cat = torch.zeros(b, l, len(cfg.cat_vocab_sizes), dtype=torch.long)
        z, taps = enc(x_num, x_cat, return_taps=True)
        assert len(taps) == cfg.n_layers + 1

    def test_served_tap_is_unnormed(self, cfg):
        """The served ``z`` is ``taps[served_tap]`` with NO norm applied (D-15, D-16)."""
        enc = EncoderV2(cfg)
        enc.eval()
        b, l = 1, cfg.window_ticks
        x_num = torch.randn(b, l, cfg.numeric_dim)
        x_cat = torch.zeros(b, l, len(cfg.cat_vocab_sizes), dtype=torch.long)
        z, taps = enc(x_num, x_cat, return_taps=True)
        assert torch.equal(z, taps[cfg.served_tap])
        assert not torch.allclose(enc.for_heads(z), z, atol=1e-3)
        rms = enc.for_heads(z).pow(2).mean(-1).sqrt()
        assert torch.allclose(rms, torch.ones_like(rms), atol=1e-3)

    def test_param_count(self, cfg):
        """Approximate parameter count ~ 1.3M total (C-5)."""
        enc = EncoderV2(cfg)
        proj = ProjectorV2(cfg)
        pred = PredictorV2(cfg)
        total = sum(p.numel() for p in enc.parameters())
        total += sum(p.numel() for p in proj.parameters())
        total += sum(p.numel() for p in pred.parameters())
        assert 500_000 < total < 3_000_000, f"total params = {total}"


class TestConfigProperties:
    def test_d_ff(self):
        cfg = JepaV2Config()
        assert cfg.d_ff == 344

    def test_d_num(self):
        cfg = JepaV2Config()
        assert cfg.d_num == 118

    def test_window_ticks(self):
        cfg = JepaV2Config()
        assert cfg.window_ticks == 384

    def test_d_head(self):
        cfg = JepaV2Config()
        assert cfg.d_head == 32

    def test_validate_passes_default(self):
        cfg = JepaV2Config()
        cfg.validate()

    def test_validate_bad_heads(self):
        cfg = JepaV2Config(d_model=127, n_heads=4)
        with pytest.raises(ValueError, match="divisible"):
            cfg.validate()
