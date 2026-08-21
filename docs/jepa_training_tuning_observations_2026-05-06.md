# JEPA Training — Tuning Observations & Retrain Ladder

> **Sanitized 2026-08-21.** The May 2026 plateau analysis that used to open this file
> (val loss stuck ~1.90 because every epoch resampled the same 5,024 ticks with a fixed
> seed) is resolved: all three levers landed 2026-06-19 as B1 per-epoch seed rotation
> (`dd31e39`), B2 `--train-samples`/`--val-samples` (`330e28f`), B3 `--patience`
> (`4fb2f87`), plus the B1-XL id-space rejection sampler (`0cd6aa9`) for the full
> monolith. What remains below is the **operational content still in force**: the
> sanctioned retrain ladder (R8/G5) and the Phase B determinism probe record.

Historical anchor: the plateau checkpoint sat at val ≈ 1.8977, maturity `doubt`
(runs of 2026-05-05/06, resumed from the 1.9914 baseline).

---

## Retrain ladder (B7 — appended 2026-07-02)

Sampling levers B1–B3 landed 2026-06-19 (`dd31e39`, `330e28f`, `4fb2f87`);
`--eval-baseline` pre/post snapshots landed 2026-07-02 (`cfbf2e1`). The
ladder below is the sanctioned path from the plateau checkpoint to a
promoted model. Execution itself is owner-gated Phase G5 (GPU wall-clock).
Resume is AUTOMATIC whenever a checkpoint exists — the `--resume` flag is a
compatibility no-op.

| Rung | Command | Gate to next rung |
|---|---|---|
| Smoke | `./.venv/bin/python run_full_training_cycle.py --model-type jepa --epochs 5 --train-samples 50000 --val-samples 10000 --patience 10` | completes; P9-02 collapse detector quiet; val < starting val |
| Mid | `./.venv/bin/python run_full_training_cycle.py --model-type jepa --epochs 25 --patience 10` | val < 1.75 OR maturity leaves `doubt` (conviction > 0.2) |
| Full | `./.venv/bin/python run_full_training_cycle.py --model-type jepa --epochs 100 --patience 30` | val < 1.50 (target above); eval non-regression |

**Promotion protocol (B7.2):** the new `jepa_brain.pt` replaces production
only when BOTH hold — (a) the post-run eval is non-regressive vs the
pre-run eval on kNN purity@5 (floor 0.979) and RAG recall@10 (floor
0.6475); (b) the rung's val gate is met. The displaced checkpoint is
archived together with its `.pt.meta.json` sidecar (Law 17), and the CTF-1
checkpoint-hash registry is updated. Collapse/saturation telemetry (P9-02
detector, concept-temperature alarm) must be observed live on the smoke
rung before any longer rung starts (B7.3).

**Wall-clock note:** at 50k train subsamples expect roughly 10× the ~70s
epochs observed at 5k in the 2026-05-06 runs — budget the full rung in GPU
sessions, not minutes. The validation subsample stays fixed within a run
(DR-01c) so early stopping compares like with like across epochs.

---

## B5 determinism probe — PASSED (appended 2026-07-02)

Three seeded dry-runs (`--dry-run --model-type jepa --train-samples 5000
--val-samples 2000 --seed {42,43,44} --no-tensorboard`), executed against
the full monolith (348,236,706 eligible train ticks, sampled via the
B1-XL id-space rejection path landed the same day in `0cd6aa9` after the
probe itself exposed the original B1 id fetch OOMing at ~9 minutes).

| Seed | Train | Val | Val/Train |
|------|-------|-----|-----------|
| 42 | 3.6475 | 1.9688 | 0.5398 |
| 43 | 3.6967 | 1.9684 | 0.5325 |
| 44 | 3.6591 | 1.9688 | 0.5381 |

**Ratio variance = 0.000010 — gate (< 0.05, REFERENCE §8) passed by four
orders of magnitude.** Val losses are near-identical across seeds because
the val subsample is anchored at GLOBAL_SEED (B1.3) and the corpus is
fixed; residual train-side spread comes from model-init variation only.
DET-01 + B1 rotation semantics verified end-to-end on real data.

Operational notes from the probe campaign: each seed costs ~46 min at
5k/2k samples, dominated by the two corpus-scale COUNT queries (~25 min
each split) — cached per run since `04543be`, so multi-epoch rungs pay
the price once. Probe runs must be launched detached (`setsid --fork`);
the assistant-harness background executor SIGTERMs at ~10 minutes.

**Phase B exit state: B1–B7 all green (B4 accepted exit-0 the same day).
The retrain ladder above is unblocked — execution remains owner-gated
Phase G5.**
