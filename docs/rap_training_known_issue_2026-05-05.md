# RAP Training: LTC timespans broadcast — RESOLVED (fix active in code)

> **Status: FIXED 2026-05-06** (commit `f5b822e`), verified by standalone forward pass
> the same day and end-to-end by the Phase B closure (B4 dry-run accepted exit-0,
> 2026-07-02). The fix is a **permanent monkey-patch that is still active** in
> `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/memory.py` (search `RAP-LTC-FIX`);
> this file is kept as its rationale. Referenced from `memory.py` (`_ode_solver` wrapper).

## The bug

`run_full_training_cycle.py --model-type rap` crashed in ncps's LTC ODE solver:

```text
RuntimeError: The size of tensor a (512) must match the size of tensor b (10)
at non-singleton dimension 0
```

## Root cause (confirmed by reading `ncps/torch/ltc.py:178`)

```python
ts = 1.0 if timespans is None else timespans[:, t].squeeze()
```

For `timespans` of shape `(B, T)`, the slice `[:, t]` yields `(B,)` and `.squeeze()`
is a no-op. Then `_ode_solver` computes `cm_t = cm / (elapsed_time / ode_unfolds)`
where `cm` has shape `(state_size,) = (ncp_units,) = (512,)`. Division of `(512,)` by
`(B,)` does not broadcast unless `state_size == B`.

This is an **intrinsic ncps bug** for any RNN config where `ncp_units != batch_size`.
It reproduces identically on ncps 1.0.1 and 0.0.7, ruling out a version regression.

## The fix

Monkey-patch `LTCCell._ode_solver` on the `self.ltc.rnn_cell` instance inside
`RAPMemory.__init__`. The patch unsqueezes any 1-D `elapsed_time` to `(B, 1)` before
delegating to the original solver, so `cm` `(state_size,)` broadcasts to
`(B, state_size)` as the ODE math requires.

## Verification

Standalone CPU forward pass (2026-05-06):

```python
mem = RAPMemory(perception_dim=128, metadata_dim=25, hidden_dim=256)
x = torch.randn(8, 10, 153)             # (B=8, T=10, F=153)
timespans = torch.full((8, 10), 1/64)   # (B, T) at 64-tick rate
ltc_out, belief, hidden = mem(x, hidden=None, timespans=timespans)
# ltc_out: (8, 10, 256) · belief: (8, 10, 64) · hidden: (8, 512) — no shape error
```

End-to-end: RAP dry-run accepted exit-0 as part of the Phase B closure
(B4, 2026-07-02 — see TASKS.md Phase B notes).
