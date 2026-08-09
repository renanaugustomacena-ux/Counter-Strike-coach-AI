"""Unit tests for JEPA representation-collapse metrics.

Deterministic, CPU-only, no TensorBoard required. Collapse is the failure
where the encoder emits near-constant embeddings: the predictor then satisfies
its objective trivially while the loss curve still looks healthy.
"""

import torch

from Programma_CS2_RENAN.backend.nn.collapse_metrics import (
    compute_collapse_metrics,
    compute_ema_drift,
)


def _collapsed(n=64, d=16):
    """All rows point in essentially the same direction."""
    torch.manual_seed(0)
    base = torch.randn(1, d)
    return base.repeat(n, 1) + 1e-6 * torch.randn(n, d)


def _healthy(n=64, d=16):
    """Rows spread across many directions."""
    torch.manual_seed(0)
    return torch.randn(n, d)


class TestCollapseMetrics:
    """Metric surface and directional behaviour under collapse."""

    def test_returns_expected_keys(self):
        m = compute_collapse_metrics(_healthy())
        assert set(m) == {
            "std_mean",
            "std_min",
            "effective_rank",
            "cosine_offdiag_mean",
        }
        assert all(isinstance(v, float) for v in m.values())

    def test_collapsed_embeddings_flagged(self):
        m = compute_collapse_metrics(_collapsed())
        assert m["std_mean"] < 0.01
        assert m["std_min"] < 0.01
        assert m["cosine_offdiag_mean"] > 0.99
        assert m["effective_rank"] < 1.5

    def test_healthy_embeddings_not_flagged(self):
        m = compute_collapse_metrics(_healthy(n=64, d=16))
        assert m["std_mean"] > 0.05
        assert abs(m["cosine_offdiag_mean"]) < 0.3
        assert m["effective_rank"] > 8.0

    def test_scale_invariance(self):
        e = _healthy()
        a = compute_collapse_metrics(e)
        b = compute_collapse_metrics(e * 37.0)
        for k in a:
            assert abs(a[k] - b[k]) < 1e-4

    def test_flattens_higher_rank_input(self):
        e = torch.randn(8, 5, 16)  # [B, T, D]
        m = compute_collapse_metrics(e)
        assert m["effective_rank"] > 1.0

    def test_degenerate_input_is_safe(self):
        m = compute_collapse_metrics(torch.randn(1, 16))
        assert m["std_mean"] == 0.0
        assert m["effective_rank"] == 0.0


class TestEmaDrift:
    """Online-vs-target parameter distance."""

    def test_identical_params_zero_drift(self):
        p = [torch.ones(4, 4), torch.zeros(3)]
        q = [torch.ones(4, 4), torch.zeros(3)]
        assert compute_ema_drift(p, q) == 0.0

    def test_drift_grows_with_divergence(self):
        p = [torch.zeros(4, 4)]
        near = compute_ema_drift(p, [torch.full((4, 4), 0.1)])
        far = compute_ema_drift(p, [torch.full((4, 4), 1.0)])
        assert far > near > 0.0
