"""Tests for the SIGReg Epps-Pulley distributional regulariser.

Parity with tools/verify_math_claims.py:sigreg_epps_pulley and
tools/measure_sigreg_sample_size.py:sigreg_reference at rel-tolerance 1e-5.
Measured H0 values from docs/research/sigreg_sample_size_2026-09-05.json.
CORREZIONE_NUCLEO_NEURALE Parte III section 4.2.
"""

import torch

from Programma_CS2_RENAN.backend.nn.jepa_v2.sigreg import SIGReg, sigreg_batch, sigreg_temporal


def _reference_sigreg(proj: torch.Tensor, seed: int = 0) -> float:
    """Reference implementation from tools/verify_math_claims.py:334-349."""
    g = torch.Generator().manual_seed(seed)
    knots, t_max, num_proj = 17, 3.0, 1024
    t = torch.linspace(0, t_max, knots)
    dt = t_max / (knots - 1)
    weights = torch.full((knots,), 2 * dt)
    weights[[0, -1]] = dt
    phi = torch.exp(-t.square() / 2.0)
    weights = weights * phi
    a = torch.randn(proj.size(-1), num_proj, generator=g)
    a = a / a.norm(p=2, dim=0, keepdim=True)
    x_t = (proj @ a).unsqueeze(-1) * t
    err = (x_t.cos().mean(-3) - phi).square() + x_t.sin().mean(-3).square()
    return float(((err @ weights) * proj.size(-2)).mean())


class TestSIGRegParity:
    """SIGReg must match the reference implementations numerically."""

    def test_parity_with_reference(self):
        torch.manual_seed(42)
        z = torch.randn(8, 64, 32)
        seed = 0
        ref = _reference_sigreg(z.reshape(-1, 32), seed)
        reg = SIGReg(knots=17, num_proj=1024, t_max=3.0)
        g = torch.Generator().manual_seed(seed)
        val = float(reg(z.reshape(-1, 32).unsqueeze(0).squeeze(0), g))
        assert abs(val - ref) / max(abs(ref), 1e-12) < 1e-5, f"got {val}, ref {ref}"

    def test_parity_batched_shape(self):
        torch.manual_seed(7)
        z = torch.randn(16, 32)
        seed = 99
        ref = _reference_sigreg(z, seed)
        reg = SIGReg()
        g = torch.Generator().manual_seed(seed)
        val = float(reg(z, g))
        assert abs(val - ref) / max(abs(ref), 1e-12) < 1e-5


class TestSIGRegDistributions:
    """Statistical properties of the Epps-Pulley statistic."""

    def test_gaussian_near_one(self):
        """Isotropic Gaussian -> H0 ~ 1.05 (measured 1.050 +/- 0.093 at N=16)."""
        reg = SIGReg()
        vals = []
        for i in range(50):
            g_data = torch.Generator().manual_seed(1000 + i)
            z = torch.randn(48, 64, generator=g_data)
            g_dir = torch.Generator().manual_seed(i)
            vals.append(float(reg(z, g_dir)))
        mean_val = sum(vals) / len(vals)
        assert 0.85 < mean_val < 1.25, f"Gaussian mean = {mean_val}"

    def test_constant_much_larger(self):
        """Collapsed distribution -> statistic >> 1 (measured 16.8 at N=16)."""
        reg = SIGReg()
        z = torch.ones(48, 64) * 3.0 + 1e-3 * torch.randn(48, 64)
        g = torch.Generator().manual_seed(0)
        val = float(reg(z, g))
        assert val > 5.0, f"Collapsed stat should be >> 1, got {val}"


class TestSIGRegGradients:
    """Gradient properties of the SIGReg statistic."""

    def test_finite_bounded_gradient(self):
        """Gradient entries must be finite and bounded (Thm 4: |dEP/dz_i| <= 4/(N*s^2))."""
        torch.manual_seed(0)
        z = torch.randn(16, 8, requires_grad=True)
        reg = SIGReg(knots=17, num_proj=64, t_max=3.0)
        g = torch.Generator().manual_seed(0)
        val = reg(z, g)
        val.backward()
        assert z.grad is not None
        assert torch.isfinite(z.grad).all()
        max_grad = z.grad.abs().max().item()
        n = z.size(-2)
        bound = 4.0 / (n * 1.0)
        assert max_grad < bound * 10, f"max_grad={max_grad}, loose bound={bound * 10}"

    def test_gradcheck_float64(self):
        """Numerical gradient check at float64 (Parte I App. A.1)."""
        reg = SIGReg(knots=17, num_proj=8, t_max=3.0)
        reg = reg.double()
        torch.manual_seed(99)
        z = torch.randn(16, 4, dtype=torch.float64, requires_grad=True) * 0.5
        g_factory = lambda: torch.Generator().manual_seed(42)  # noqa: E731

        def func(x: torch.Tensor) -> torch.Tensor:
            return reg(x, g_factory())

        assert torch.autograd.gradcheck(func, (z,), eps=1e-5, atol=1e-3, rtol=1e-3)


class TestSIGRegBatchVsTemporal:
    """sigreg_batch and sigreg_temporal compute different things."""

    def test_batch_vs_temporal_differ(self):
        """Batch and temporal SIGReg compute different axes; on structured
        data with temporal correlation they should diverge measurably."""
        torch.manual_seed(0)
        # AR(1) temporal structure: batch axis is i.i.d., temporal is correlated
        b, t, d = 8, 48, 32
        u = torch.zeros(b, t, d)
        for bi in range(b):
            z = torch.randn(d)
            for ti in range(t):
                z = 0.9 * z + 0.1 * torch.randn(d)
                u[bi, ti] = z
        reg = SIGReg(knots=17, num_proj=128, t_max=3.0)
        g1 = torch.Generator().manual_seed(0)
        g2 = torch.Generator().manual_seed(0)
        v_batch = float(sigreg_batch(u, reg, g1))
        v_temp = float(sigreg_temporal(u, reg, g2))
        # temporal SIGReg on AR(1) should be much larger than batch on i.i.d.
        assert (
            v_temp > v_batch * 1.5
        ), f"temporal={v_temp} should be > 1.5x batch={v_batch} on AR(1) data"

    def test_temporal_per_window_not_pooled(self):
        """Temporal SIGReg must NOT pool tokens across windows (A-12)."""
        torch.manual_seed(0)
        reg = SIGReg(knots=17, num_proj=64, t_max=3.0)
        u_single = torch.randn(1, 48, 32)
        g1 = torch.Generator().manual_seed(0)
        val_single = float(sigreg_temporal(u_single, reg, g1))
        u_dup = u_single.repeat(4, 1, 1)
        g2 = torch.Generator().manual_seed(0)
        val_dup = float(sigreg_temporal(u_dup, reg, g2))
        assert abs(val_single - val_dup) / max(abs(val_single), 1e-12) < 1e-4


class TestSIGRegFloat32Directions:
    """D-15: directions must be drawn in float32 even with bf16 input."""

    def test_bf16_input_float32_directions(self):
        reg = SIGReg()
        z = torch.randn(16, 32).bfloat16()
        g = torch.Generator().manual_seed(0)
        val = reg(z, g)
        assert torch.isfinite(val)
        assert val.dtype == torch.float32
