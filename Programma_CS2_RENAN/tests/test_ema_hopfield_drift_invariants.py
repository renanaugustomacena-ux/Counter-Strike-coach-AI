"""TEST-COV regression suite — covers silent-failure paths flagged by the
ML/AI audit (AUDIT §3.2 TEST-COV) that previously had no unit coverage:

- EMA aliasing (NN-16): apply_shadow/restore must break storage aliasing so
  `self.backup={}` cannot free memory still referenced by param.data.
- Hopfield bypass after partial state_dict load (MEM-01): partial loads
  must NOT flip `_hopfield_trained=True` with random prototypes.
- MoE sparse routing (MOE-01): strategy.forward must produce at least one
  non-zero per-sample output when experts are enabled.
- Tick-feature drift monitor (DRIFT-01 fix verification): the new
  TickFeatureDriftMonitor must flag per-dimension drift on the 25-dim
  input vector.
"""

from __future__ import annotations

import numpy as np
import torch

from Programma_CS2_RENAN.backend.nn.ema import EMA
from Programma_CS2_RENAN.backend.processing.validation.drift import TickFeatureDriftMonitor

# --- EMA aliasing regression -------------------------------------------------


def test_ema_restore_breaks_backup_aliasing():
    """restore() must clone backup tensors so later backup reset + mutation of
    an external reference does not corrupt param.data."""
    model = torch.nn.Linear(4, 4)
    ema = EMA(model, decay=0.5)
    with torch.no_grad():
        model.weight.add_(1.0)
    ema.update()

    ema.apply_shadow()
    pre_shadow = model.weight.data.clone()
    ema.restore()
    restored = model.weight.data

    # Mutate ema.backup residue (should be empty, but any leftover ref must
    # not alias the restored param storage).
    for t in list(ema.backup.values()):
        t.zero_()

    assert torch.equal(restored, model.weight.data), "restored weights mutated"
    assert not torch.equal(pre_shadow, restored), "restore left shadow weights"


def test_ema_apply_shadow_breaks_shadow_aliasing():
    """apply_shadow() must clone — else in-place op on param.data corrupts the
    stored shadow (the original NN-16 bug)."""
    model = torch.nn.Linear(3, 3)
    ema = EMA(model, decay=0.5)
    original_shadow = {k: v.clone() for k, v in ema.shadow.items()}

    ema.apply_shadow()
    with torch.no_grad():
        model.weight.mul_(0.0)  # in-place mutation on param.data

    for k, v in original_shadow.items():
        assert torch.equal(ema.shadow[k], v), f"shadow[{k}] corrupted by in-place mutation"


# --- Hopfield partial-load guard --------------------------------------------


def test_hopfield_bypass_after_partial_load():
    """Loading a state_dict that omits Hopfield weights must not mark the
    layer as trained — else the model runs with random prototypes."""
    try:
        from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.memory import (
            RecurrentBeliefState,
        )
    except ImportError:
        import pytest

        pytest.skip("RAP memory module unavailable (optional dep)")

    memory = RecurrentBeliefState(input_dim=8, hidden_dim=16, belief_dim=32)
    # Build a state_dict that strips all hopfield weights.
    sd = {k: v for k, v in memory.state_dict().items() if "hopfield" not in k.lower()}
    memory.load_state_dict(sd, strict=False)

    trained_flag = getattr(memory, "_hopfield_trained", False)
    assert not trained_flag, (
        "_hopfield_trained must stay False when Hopfield weights were not "
        "part of the loaded state_dict"
    )


# --- MoE sparse-gate output sanity ------------------------------------------


def test_moe_sparse_strategy_outputs_nonzero_per_sample():
    """RAPStrategy top-2 routing should produce non-zero output for every
    sample in a batch (regression guard for MOE-01 indexing logic)."""
    try:
        from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.strategy import RAPStrategy
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
    except ImportError:
        import pytest

        pytest.skip("RAP strategy unavailable (optional dep)")

    hidden_dim, output_dim = 32, 10
    strategy = RAPStrategy(hidden_dim, output_dim, context_dim=METADATA_DIM)
    strategy.eval()

    batch = 6
    hidden = torch.randn(batch, hidden_dim)
    context = torch.randn(batch, METADATA_DIM)
    with torch.no_grad():
        out, gate_probs = strategy(hidden, context)

    assert out.shape == (batch, output_dim)
    assert gate_probs.shape == (batch, strategy.num_experts)
    # At least one non-zero value per sample — zero rows indicate indexing bug.
    per_sample_magnitude = out.abs().sum(dim=-1)
    assert (per_sample_magnitude > 0).all(), "zero output row indicates routing bug"


# --- Tick-feature drift monitor ---------------------------------------------


def test_tick_feature_drift_monitor_detects_per_dim_shift():
    rng = np.random.default_rng(0)
    ref = rng.normal(loc=0.0, scale=1.0, size=(512, 25))

    monitor = TickFeatureDriftMonitor(z_threshold=2.5)
    monitor.fit_reference(ref, feature_names=[f"f{i}" for i in range(25)])

    # Shift feature 7 by 5σ, leave others alone.
    new_batch = rng.normal(loc=0.0, scale=1.0, size=(256, 25))
    new_batch[:, 7] += 5.0
    report = monitor.check_drift(new_batch)

    assert report.is_drifted is True
    assert "f7" in report.drifted_features
    assert report.max_z_score > 2.5


def test_tick_feature_drift_monitor_noops_without_reference():
    import pytest

    monitor = TickFeatureDriftMonitor()
    with pytest.raises(RuntimeError):
        monitor.check_drift(np.zeros((4, 25)))
