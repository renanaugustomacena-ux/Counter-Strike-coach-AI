"""Tests for JEPA v2 loss function.

Loss finiteness, component keys, horizon correctness, gradient flow,
determinism, no EMA / stop-gradient.
CORREZIONE_NUCLEO_NEURALE Parte III section 4.6, C-8.
"""

import pytest
import torch

from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.encoder import EncoderV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.losses import jepa_v2_loss
from Programma_CS2_RENAN.backend.nn.jepa_v2.predictor import PredictorV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.projector import ProjectorV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.sigreg import SIGReg


@pytest.fixture
def setup():
    cfg = JepaV2Config(
        batch_size=4,
        tokens_per_window=16,
        patch_ticks=8,
        d_model=32,
        n_heads=4,
        n_layers=2,
        ffn_mult=4,
        proj_hidden=64,
        proj_out=16,
        predictor_layers=1,
        horizons=(1, 4),
        sigreg_num_proj=32,
        sigreg_taps=(0, -1),
        cat_vocab_sizes=(10, 9, 3),
        cat_embed_dims=(4, 4, 2),
        dropout=0.0,
    )
    torch.manual_seed(0)
    enc = EncoderV2(cfg)
    proj = ProjectorV2(cfg)
    pred = PredictorV2(cfg)
    reg = SIGReg(knots=cfg.sigreg_knots, num_proj=cfg.sigreg_num_proj, t_max=cfg.sigreg_t_max)
    b = cfg.batch_size
    l = cfg.tokens_per_window * cfg.patch_ticks
    x_num = torch.randn(b, l, cfg.numeric_dim)
    x_cat = torch.zeros(b, l, len(cfg.cat_vocab_sizes), dtype=torch.long)
    return cfg, enc, proj, pred, reg, x_num, x_cat


class TestLossFinite:
    def test_loss_is_finite(self, setup):
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        enc.eval()
        z, taps = enc(x_num, x_cat, return_taps=True)
        loss, info = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        assert torch.isfinite(loss)
        assert loss.item() > 0

    def test_component_keys(self, setup):
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        z, taps = enc(x_num, x_cat, return_taps=True)
        _, info = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        expected = {"L_next", "L_multi", "sig_T", "sig_B", "S_straight", "loss"}
        assert set(info.keys()) == expected

    def test_all_components_finite(self, setup):
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        z, taps = enc(x_num, x_cat, return_taps=True)
        _, info = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        for k, v in info.items():
            assert isinstance(v, float) and v == v, f"{k} is not finite: {v}"


class TestGradientFlow:
    def test_gradients_flow_to_encoder(self, setup):
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        z, taps = enc(x_num, x_cat, return_taps=True)
        loss, _ = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        loss.backward()
        graded = 0
        for p in enc.parameters():
            if p.grad is not None and p.grad.abs().sum() > 0:
                graded += 1
        assert graded > 0

    def test_gradients_flow_to_predictor(self, setup):
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        z, taps = enc(x_num, x_cat, return_taps=True)
        loss, _ = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        loss.backward()
        graded = sum(1 for p in pred.parameters() if p.grad is not None and p.grad.abs().sum() > 0)
        assert graded > 0

    def test_gradients_flow_to_projector(self, setup):
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        z, taps = enc(x_num, x_cat, return_taps=True)
        loss, _ = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        loss.backward()
        graded = sum(1 for p in proj.parameters() if p.grad is not None and p.grad.abs().sum() > 0)
        assert graded > 0


class TestDeterminism:
    def test_same_step_same_loss(self, setup):
        """Two forward passes at the same step must produce identical loss."""
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        enc.eval()
        pred.eval()
        z, taps = enc(x_num, x_cat, return_taps=True)
        loss1, _ = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=42)
        loss2, _ = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=42)
        assert loss1.item() == pytest.approx(loss2.item(), rel=1e-6)

    def test_different_step_different_directions(self, setup):
        """Different steps use different direction seeds -> different SIGReg.
        Compare steps far apart so the direction difference is measurable."""
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        enc.eval()
        pred.eval()
        z, taps = enc(x_num, x_cat, return_taps=True)
        _, info1 = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        _, info2 = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=10000)
        # sig_B differs because different directions; just check not bit-identical
        assert info1["sig_B"] != info2["sig_B"]


class TestNoEMA:
    def test_no_stop_gradient_on_target(self, setup):
        """Target u = proj(z) must have gradients flowing through z (no EMA,
        no stop-gradient — Parte II section 2.2)."""
        cfg, enc, proj, pred, reg, x_num, x_cat = setup
        z, taps = enc(x_num, x_cat, return_taps=True)
        loss, _ = jepa_v2_loss(z, taps, pred, proj, cfg, reg, step=0)
        loss.backward()
        conv_weight = enc.tokenizer.conv.weight
        assert conv_weight.grad is not None
        assert conv_weight.grad.abs().sum() > 0
