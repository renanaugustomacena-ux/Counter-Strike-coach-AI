"""Tests for the bf16 AMP autocast helper (GPU training fast-path).

On the ROCm gfx1201 wheels fp32 GEMM is untuned (~1.3 TFLOPS vs ~118 in
bf16), so GPU training must run under bf16 autocast to get hardware value.
bf16 keeps the fp32 exponent range, so no GradScaler is required — call
sites wrap forward+loss only, backward/step stay outside.
"""

import pytest
import torch

from Programma_CS2_RENAN.backend.nn.config import amp_autocast


def test_amp_autocast_returns_context_manager():
    ctx = amp_autocast()
    assert hasattr(ctx, "__enter__") and hasattr(ctx, "__exit__")


def test_amp_autocast_disabled_on_cpu_host():
    """On CPU-only hosts the context must be a transparent no-op."""
    with amp_autocast():
        x = torch.randn(4, 8)
        y = torch.nn.Linear(8, 2)(x)
    assert y.dtype == torch.float32


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs GPU")
def test_amp_autocast_casts_matmul_to_bf16_on_gpu():
    d = torch.device("cuda:0")
    net = torch.nn.Linear(32, 16).to(d)
    x = torch.randn(4, 32, device=d)
    with amp_autocast():
        y = net(x)
    assert y.dtype == torch.bfloat16


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs GPU")
def test_training_step_under_autocast_produces_finite_fp32_grads():
    d = torch.device("cuda:0")
    net = torch.nn.Sequential(torch.nn.Linear(16, 32), torch.nn.GELU(), torch.nn.Linear(32, 4)).to(
        d
    )
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
    x = torch.randn(8, 16, device=d)
    target = torch.randn(8, 4, device=d)

    with amp_autocast():
        loss = torch.nn.functional.mse_loss(net(x), target)
    loss.backward()
    opt.step()

    for p in net.parameters():
        assert p.grad is not None
        assert p.grad.dtype == torch.float32, "master grads must stay fp32"
        assert bool(torch.isfinite(p.grad).all())
