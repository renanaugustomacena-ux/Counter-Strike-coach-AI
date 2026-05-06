# JEPA Training — Tuning Observations (2026-05-06)

## What just happened

Two consecutive JEPA training runs against the new D1+D2A+D2C data state:

| Run | Date    | Epochs ran | Best val | Maturity | Wall |
|-----|---------|-----------|----------|----------|------|
| 1   | 05-05   | 5/5 (cap) | 1.9167   | doubt    | ~50 min |
| 2   | 05-06   | 13/100 (early-stop) | 1.8977 | doubt | ~16 min |

Both runs **resumed** from the prior checkpoint and shaved a small slice off
val loss (1.9914 baseline → 1.9167 → 1.8977, total -0.094 across two
sessions). The model never left the `doubt` maturity state; conviction
plateaus around 0.08, val_acc stays at 0.000.

## Pattern: val loss bounces, doesn't converge

Run 2 epoch-by-epoch trajectory:

```
ep  train  val
 1  1.39   1.96   ← session-best (resume reset the tracker)
 2  1.41   1.96
 3  1.43   1.90   ← session-best (saved as new jepa_brain.pt)
 4  1.48   1.96
 5  1.52   1.94
 6  1.48   2.02
 7  1.48   1.97
 8  1.48   2.04
 9  1.47   1.98
10  1.47   1.99
11  1.47   1.96
12  1.45   2.00
13  1.47   2.03   ← early-stop (10 non-improving epochs since ep3)
```

Train loss creeps up (1.39 → 1.47), val loss bounces in a narrow band
(1.90–2.04). Classic "model isn't learning, just oscillating in noise"
shape.

## Most likely cause

Looking at `Programma_CS2_RENAN/backend/nn/training_orchestrator.py`:

- **Subsample size: 5024 ticks per epoch** (cf. logs: "Loaded 5000 ticks for
  train split").
- **Sampling seed: fixed via `set_global_seed(42)` at script entry**
  (`run_full_training_cycle.py:87`).
- Result: every epoch sees the **same 5024 ticks**. The model isn't
  discovering new patterns — it's just shuffling weights against a fixed
  micro-dataset.

5024 ticks out of 392M is a 0.0013% sample. Even if the seed rotated, the
sample would barely cover the distribution. With a fixed seed, the
information per epoch is exactly zero new tokens.

## Three tuning levers for the next session

### 1. Larger train/val subsamples per epoch

`backend/nn/training_orchestrator.py` configures the dataset loader to
draw N samples per split. Bump from 5024 to ~50000 train + 10000 val
(same fraction of full data, but enough variance per epoch for stable
gradients). Trade-off: per-epoch wall time increases ~10×.

### 2. Rotate the per-epoch sampling seed

Currently `set_global_seed(42)` runs once at script start. The dataloader
should reseed per epoch (e.g., `seed = 42 + epoch`) so the 5024-tick
window slides across the dataset across epochs. Trivial change in the
DataLoader's `worker_init_fn` or by using PyTorch's `RandomSampler` with
a generator that re-seeds.

### 3. Longer early-stop patience

Default `patience=10` early-stops the run before the model has seen
enough data. With levers 1 and 2 in place, val loss should actually
improve epoch-over-epoch — but if it doesn't, longer patience (e.g.,
25-30) lets the model push through plateaus before triggering early
stop.

## Recommended next session ordering

1. Audit `training_orchestrator.py` for the 5024-sample cap. Find where
   the dataloader is constructed and check if `num_samples` is hardcoded
   or pulled from config.
2. Make subsample size configurable via CLI (`--train-samples N
   --val-samples M`) and add per-epoch seed rotation.
3. Run a fresh training cycle with the new sampler, longer patience.
   Expect val loss to drop below 1.5 if the data is genuinely informative.

## What is NOT broken

- Pipeline runs end-to-end: PASS
- GPU acceleration (GTX 1650 + CUDA 13.0): PASS
- Data Quality Report (PASS, 392M ticks, 0.19% zero-pos rate): PASS
- METADATA_DIM=25 contract: PASS
- Checkpoint save/load + resume: PASS
- Model improves session-over-session: PASS (small but consistent)

The plateau is a curriculum/sampling tuning issue, not a data layer or
model construction issue. The hard work (D1/D2A/D2C) is paying off — the
training pipeline reads the new data cleanly. The next gain comes from
showing the model more of that data per epoch.
