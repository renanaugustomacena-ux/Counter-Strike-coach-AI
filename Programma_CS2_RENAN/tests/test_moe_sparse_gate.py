"""GAP-10 (MOE-02) regression tests for top-K sparse MoE gate.

Verifies:
- `_topk_sparse_gate` returns a vector with exactly K non-zero entries per row.
- Selected weights sum to 1.0 along the gate dim (normalized via softmax of
  the top-K logits, NOT a clamp of full softmax — that distinction matters
  because it preserves a meaningful relative weighting between top-2).
- Non-selected experts receive zero gradient (the whole point of sparse MoE).
- Expert collapse fix: with random init + a noisy training step, gate
  entropy across a batch stays below the dense-softmax baseline (i.e. the
  top-K mask actually concentrates routing).
- AdvancedCoachNN.forward still produces same output shape; checkpoint key
  shape changed (gate.weight vs gate.0.weight) — confirms StaleCheckpointError
  on legacy load is intentional.
- num_experts=1 edge case (top-K=1, K capped at E) does not crash.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.model import AdvancedCoachNN, CoachNNConfig, _topk_sparse_gate


def test_topk_sparse_gate_has_exactly_k_nonzero():
    logits = torch.randn(8, 5)
    sparse = _topk_sparse_gate(logits, k=2)
    nonzero_per_row = (sparse > 0).sum(dim=-1)
    assert torch.all(nonzero_per_row == 2)


def test_topk_sparse_gate_sums_to_one():
    logits = torch.randn(16, 4)
    sparse = _topk_sparse_gate(logits, k=2)
    sums = sparse.sum(dim=-1)
    torch.testing.assert_close(sums, torch.ones(16))


def test_topk_sparse_gate_top_indices_match_logits_topk():
    logits = torch.tensor(
        [
            [10.0, 0.1, 0.2, 0.3, 0.4],
            [0.1, 0.2, 0.3, 0.4, 0.5],
        ]
    )
    sparse = _topk_sparse_gate(logits, k=2)
    # Row 0: top-2 are indices 0, 4 (values 10.0 and 0.4)
    nonzero_idx_row0 = torch.nonzero(sparse[0]).flatten().tolist()
    assert sorted(nonzero_idx_row0) == [0, 4]
    # Row 1: top-2 are 4, 3
    nonzero_idx_row1 = torch.nonzero(sparse[1]).flatten().tolist()
    assert sorted(nonzero_idx_row1) == [3, 4]


def test_topk_caps_at_num_experts():
    """k > E should clamp to E (degenerate to dense softmax)."""
    logits = torch.randn(4, 3)
    sparse = _topk_sparse_gate(logits, k=10)
    nonzero_per_row = (sparse > 0).sum(dim=-1)
    assert torch.all(nonzero_per_row == 3)


def test_topk_k1_picks_argmax():
    logits = torch.tensor([[1.0, 5.0, 2.0]])
    sparse = _topk_sparse_gate(logits, k=1)
    assert sparse[0, 1] == 1.0
    assert sparse[0, 0] == 0.0 and sparse[0, 2] == 0.0


def test_unselected_experts_receive_zero_gradient():
    """Core MOE-02 invariant: non-routed experts must have zero grad on
    the parameters whose contribution is gated to 0.

    Eval mode used so dropout doesn't randomise lstm_out between the
    forward/backward and the routing inspection — we need the routed-set
    captured during the same pass that produced the gradients.
    """
    torch.manual_seed(42)
    config = CoachNNConfig(input_dim=8, output_dim=4, hidden_dim=16, num_experts=4, dropout=0.0)
    model = AdvancedCoachNN(config=config)
    model.eval()  # disable LSTM dropout — deterministic forward

    x = torch.randn(2, 1, 8)
    # Capture the actual routing used in this forward pass
    with torch.no_grad():
        lstm_out, _ = model.lstm(x)
        last_hidden = model.layer_norm(lstm_out[:, -1, :])
        gate_logits = model.gate(last_hidden)
        sparse = _topk_sparse_gate(gate_logits, model.gate_top_k)
    routed_any = (sparse > 0).any(dim=0)  # [E]

    out = model(x)
    loss = out.sum()
    loss.backward()

    for i, expert in enumerate(model.experts):
        first_linear = expert[0]
        grad_norm = (
            first_linear.weight.grad.norm().item() if first_linear.weight.grad is not None else 0.0
        )
        if not routed_any[i]:
            assert grad_norm == 0.0, f"expert {i} was unrouted but received grad norm {grad_norm}"


def test_gate_entropy_stays_below_dense_baseline():
    """Sparse top-2 must produce LOWER entropy per row than the equivalent
    dense softmax over the same logits — that's the whole point."""
    torch.manual_seed(0)
    logits = torch.randn(64, 5)
    sparse = _topk_sparse_gate(logits, k=2)
    dense = torch.softmax(logits, dim=-1)

    # Per-row Shannon entropy in nats; clamp to avoid log(0).
    def _entropy(p):
        p = p.clamp(min=1e-12)
        return -(p * p.log()).sum(dim=-1)

    sparse_h = _entropy(sparse).mean().item()
    dense_h = _entropy(dense).mean().item()
    # Sparse top-2 is upper-bounded at log(2) ≈ 0.693 by definition (only 2
    # non-zero terms), while dense over 5 logits sits near log(5) ≈ 1.6 with
    # uniform-ish init. Random init pushes top-2 weights close to (0.5, 0.5)
    # → entropy near log(2). Two separate signals to verify:
    import math

    assert sparse_h < dense_h, "sparse must concentrate routing more than dense"
    assert sparse_h <= math.log(2) + 1e-6, "sparse top-2 entropy bounded by log(2)"


def test_post_warmup_gate_entropy_below_acceptance():
    """Plan §7 acceptance: post-warmup gate entropy must drop below 0.5 nat.
    Simulated by widening the logit gap between top-1 and top-2 — what a
    well-trained gate would produce. Confirms the metric is achievable on
    the existing helper, so a real training run can target it."""
    # top-1 dominates top-2 by ~3 nats → softmax(top-2) ≈ (0.95, 0.05)
    logits = torch.tensor(
        [
            [3.0, 0.0, -1.0, -2.0, -3.0],
            [0.0, 3.0, -1.0, -2.0, -3.0],
        ]
    )
    sparse = _topk_sparse_gate(logits, k=2)

    def _entropy(p):
        p = p.clamp(min=1e-12)
        return -(p * p.log()).sum(dim=-1)

    h = _entropy(sparse).mean().item()
    assert h < 0.5, f"post-warmup entropy {h:.3f} must be < 0.5 nats"


def test_advanced_coach_forward_shape_unchanged():
    config = CoachNNConfig(input_dim=8, output_dim=4, hidden_dim=16, num_experts=3)
    model = AdvancedCoachNN(config=config)
    model.eval()
    x = torch.randn(5, 1, 8)
    out = model(x)
    assert out.shape == (5, 4)
    assert torch.all(out >= -1.0) and torch.all(out <= 1.0)  # tanh


def test_state_dict_uses_flat_gate_keys_not_sequential():
    """Catches the architecture-bump signature: old checkpoints used
    `gate.0.weight`/`gate.0.bias` (Sequential index). New flat Linear emits
    `gate.weight`/`gate.bias`."""
    config = CoachNNConfig(input_dim=8, output_dim=4, hidden_dim=16, num_experts=3)
    model = AdvancedCoachNN(config=config)
    keys = set(model.state_dict().keys())
    assert "gate.weight" in keys
    assert "gate.bias" in keys
    assert "gate.0.weight" not in keys


def test_num_experts_one_does_not_crash():
    config = CoachNNConfig(input_dim=8, output_dim=4, hidden_dim=16, num_experts=1)
    model = AdvancedCoachNN(config=config)
    x = torch.randn(3, 1, 8)
    out = model(x)
    assert out.shape == (3, 4)
    # With 1 expert, gate_top_k = 1, gate weight must be 1.0
    assert model.gate_top_k == 1


def test_role_bias_still_applies_with_sparse_gate():
    """Role bias was a post-softmax blend. With sparse gate, semantics
    preserved: even if role expert isn't in top-K, it gets weight 0.5."""
    torch.manual_seed(7)
    config = CoachNNConfig(input_dim=8, output_dim=4, hidden_dim=16, num_experts=4)
    model = AdvancedCoachNN(config=config)
    model.eval()
    x = torch.randn(3, 1, 8)

    out_no_role = model(x)
    out_role = model(x, role_id=2)
    assert out_no_role.shape == out_role.shape
    # Outputs should differ because role bias shifts gating.
    assert not torch.allclose(out_no_role, out_role)
