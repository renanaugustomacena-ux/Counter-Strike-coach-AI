# RAP Training: Tensor Shape Mismatch — Blocker (2026-05-05)

## Summary

`run_full_training_cycle.py --model-type rap` fails after ~50 minutes of
preparation with a `RuntimeError` deep in ncps's LTC ODE solver:

```
RuntimeError: The size of tensor a (512) must match the size of tensor b (10)
at non-singleton dimension 0
```

The error originates in `ncps.torch.ltc_cell._ode_solver` while computing
`cm_t = cm / elapsed_time`. `cm` is the LTC's per-feature time-constant
parameter (shape `(512,)` = ncp_units). `elapsed_time` arrives shape `(10,)`
(= per-window timesteps).

## Reproduction

1. `./.venv/bin/python -m pip install ncps "git+https://github.com/ml-jku/hopfield-layers.git"`
2. `./.venv/bin/python run_full_training_cycle.py --dry-run --model-type rap`
3. Crash at `RAPTrainer.train_step` → `RAPCoachModel.forward` →
   `RAPMemory.forward` (line 128) → `ncps.torch.ltc.forward` (line 185) →
   `ncps.torch.ltc_cell.forward` (line 282) → `_ode_solver` (line 223)

## What was tried, what didn't help

| Attempt | Result |
|---------|--------|
| `ncps==1.0.1` (latest)     | crash at `cm_t / elapsed_time` shape mismatch |
| `ncps==0.0.7` (last pre-1.0) | same crash, identical traceback                |

The shape mismatch is identical between ncps 1.0.1 and 0.0.7, ruling out an
ncps API change as the cause. The bug is in our integration: the timespans
tensor shape does not match what `ncps.LTCCell._ode_solver` expects to
broadcast against `cm`.

## Where to look

- `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/memory.py:128` —
  `self.ltc(x, hidden, timespans=timespans)` is the call site.
- `Programma_CS2_RENAN/backend/nn/training_orchestrator.py:583` — where
  `timespans` is built via `torch.stack(windows["timespans"])` with comment
  asserting shape `(B, T)`.
- `Programma_CS2_RENAN/backend/nn/training_orchestrator.py:786` —
  `window_timespans.append(torch.tensor(per_tick["dt"][start:end], dtype=torch.float32))`
  appends per-window 1-D tensors of length `(end - start)`. After
  `torch.stack` the batch dim is added.

## Hypotheses worth testing in a follow-up session

1. The `(512,)` is the LTC cell hidden dim (ncp_units); the `(10,)` is the
   sequence length T (10 ticks per window). The ode_solver expects
   `elapsed_time` per-step (`(B,)` only, not `(B, T)`). The LTC layer's
   internal loop iterates over T steps internally, slicing `(B, T)` to
   `(B,)` per step. Broadcasting against `cm` shape `(ncp_units,)` requires
   `elapsed_time` to be `(B, 1)` so it broadcasts to `(B, ncp_units)`.
   At some intermediate step a reshape may be missing.
2. Alternatively: the `cm` parameter shape may be wrong relative to the LTC
   cell's hidden dim. Check `RAPMemory.__init__` for the LTC instantiation
   and the `wiring`/`output_size` arguments that determine `cm`'s shape.
3. Try passing `timespans=None` from `RAPMemory.forward` as a workaround;
   loses the continuous-time advantage but should let RAP train. Validates
   that the bug is specifically in the timespans-broadcast path.

## Decision

Train JEPA-only for now. JEPA passed its dry-run cleanly (1h 40min, 1 epoch
over the full data, 0 errors). JEPA produces the world-model checkpoint
that the production coaching pipeline depends on. RAP is the experimental
add-on per `Programma_CS2_RENAN/backend/coaching/README.md`; it can be
re-enabled in a focused follow-up session that tackles only the
timespans/cm broadcast bug.

## Acceptance for the follow-up

`./.venv/bin/python run_full_training_cycle.py --dry-run --model-type rap`
exits 0. A single epoch completes without raising in `_ode_solver`.

## Fix staged (2026-05-06) — pending verification

Root cause confirmed by reading `ncps/torch/ltc.py:178`:

```python
ts = 1.0 if timespans is None else timespans[:, t].squeeze()
```

For `timespans` of shape `(B, T)`, the slice `[:, t]` yields `(B,)` and
`.squeeze()` is a no-op. Then `_ode_solver` (line 224) computes
`cm_t = cm / (elapsed_time / ode_unfolds)` where `cm` has shape
`(state_size,) = (ncp_units,) = (512,)`. Division of `(512,)` by `(B,)`
does not broadcast unless `state_size == B`.

This is an intrinsic ncps bug for any RNN config where `ncp_units != batch_size`.
Reproduces identically on ncps 1.0.1 and 0.0.7, ruling out a version
regression.

**Fix:** monkey-patch `LTCCell._ode_solver` on the `self.ltc.rnn_cell`
instance inside `RAPMemory.__init__`. The patch unsqueezes any 1-D
`elapsed_time` to `(B, 1)` before delegating to the original solver, so
`cm` (state_size,) broadcasts to `(B, state_size)` as the ODE math
requires.

Code: `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/memory.py`,
inside the RAPMemory `__init__` after `self.ltc = LTC(...)`. Search for
`RAP-LTC-FIX` in the source.

Verification status: **VERIFIED via standalone CPU forward pass (2026-05-06).**

Standalone check (no full training pipeline, no GPU, doesn't compete with
the JEPA training currently running):

```python
mem = RAPMemory(perception_dim=128, metadata_dim=25, hidden_dim=256)
x = torch.randn(8, 10, 153)             # (B=8, T=10, F=153)
timespans = torch.full((8, 10), 1/64)   # (B, T) at 64-tick rate
ltc_out, belief, hidden = mem(x, hidden=None, timespans=timespans)
# Forward OK:
#   ltc_out: (8, 10, 256)
#   belief:  (8, 10, 64)
#   hidden:  (8, 512)   ← matches ncp_units, no shape error
```

The previously-crashing path `cm (512,) / elapsed_time (B,)` now succeeds
because `elapsed_time` is reshaped to `(B, 1)` before the division, so it
broadcasts to `(B, state_size) = (B, 512)` cleanly.

End-to-end follow-up (in a future session, after JEPA training completes):
`./.venv/bin/python run_full_training_cycle.py --dry-run --model-type rap`
should now exit 0.
