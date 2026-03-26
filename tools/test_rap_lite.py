"""RAP-Lite integration test — verifies dimensional contracts end-to-end."""

import os
import sys

# --- Venv Guard ---
if sys.prefix == sys.base_prefix and not os.environ.get("CI"):
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import torch

from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM


def test_rap_lite():
    # 1. Instantiate via factory
    model = ModelFactory.get_model("rap-lite")
    model.eval()
    print(f"[OK] rap-lite instantiated via ModelFactory")

    # 2. Verify memory is the lite variant (not the full LTC+Hopfield)
    from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.memory import RAPMemoryLite

    assert isinstance(
        model.memory, RAPMemoryLite
    ), f"Expected RAPMemoryLite, got {type(model.memory).__name__}"
    print(f"[OK] Memory layer is RAPMemoryLite (LSTM-based)")

    # 3. Dimensional contracts
    B, T = 1, 10
    view = torch.randn(B, 3, 64, 64)
    map_t = torch.randn(B, 3, 64, 64)
    motion = torch.randn(B, 3, 64, 64)
    meta = torch.randn(B, T, METADATA_DIM)

    with torch.no_grad():
        out = model(view, map_t, motion, meta)

    # 4. Verify output contract (7 keys)
    assert "advice_probs" in out and out["advice_probs"].shape == (B, 10)
    assert "belief_state" in out and out["belief_state"].shape == (B, T, 64)
    assert "value_estimate" in out and out["value_estimate"].shape[-1] == 1
    assert "gate_weights" in out and out["gate_weights"].shape == (B, 4)
    assert "optimal_pos" in out and out["optimal_pos"].shape == (B, 3)
    assert "attribution" in out and out["attribution"].shape == (B, 5)
    assert "hidden_state" in out
    print(f"[OK] 7-key output dict with correct shapes")

    # 5. Ghost-compatible: optimal_pos is finite
    assert torch.isfinite(out["optimal_pos"]).all(), "Position delta must be finite"
    print(f"[OK] optimal_pos is finite (GhostEngine-compatible)")

    # 6. Chronovisor-compatible: value_estimate is finite
    assert torch.isfinite(out["value_estimate"]).all(), "Value estimate must be finite"
    print(f"[OK] value_estimate is finite (ChronovisorScanner-compatible)")

    # 7. Checkpoint name registered
    assert ModelFactory.get_checkpoint_name("rap-lite") == "rap_lite_coach"
    print(f"[OK] Checkpoint name: rap_lite_coach")

    # 8. JEPA pipeline unaffected
    jepa = ModelFactory.get_model("jepa")
    assert type(jepa).__name__ == "JEPACoachingModel"
    print(f"[OK] JEPA pipeline unaffected")

    # 9. Summary
    params = sum(p.numel() for p in model.parameters())
    print()
    print("=" * 50)
    print("ALL RAP-LITE CHECKS PASSED")
    print(f"  Model params:    {params:,}")
    print(f"  METADATA_DIM:    {METADATA_DIM}")
    print(f"  advice_probs:    {out['advice_probs'].shape}")
    print(f"  belief_state:    {out['belief_state'].shape}")
    print(f"  value_estimate:  {out['value_estimate'].shape}")
    print(f"  optimal_pos:     {out['optimal_pos'].shape}")
    print(f"  attribution:     {out['attribution'].shape}")
    print(f"  gate_weights:    {out['gate_weights'].shape}")
    print("=" * 50)


if __name__ == "__main__":
    test_rap_lite()
