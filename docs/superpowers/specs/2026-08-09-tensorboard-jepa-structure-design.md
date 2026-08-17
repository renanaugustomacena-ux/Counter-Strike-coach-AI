# TensorBoard as a Real Instrument: Detecting JEPA Representation Collapse

**Date:** 2026-08-09
**Status:** Approved design, pending implementation plan

## Problem

The project has a well-built TensorBoard layer that has never run. `TensorBoardCallback`
(`Programma_CS2_RENAN/backend/nn/tensorboard_callback.py`) logs scalars, parameter and
gradient histograms, gate activations, and custom scalar layouts — but `tensorboard` is
listed only in `requirements-dev.in:62`, not in the runtime lock. So the import guard at
line 27-33 sets `_TB_AVAILABLE = False`, every hook returns early, and the feature is a
silent no-op. `Programma_CS2_RENAN/tests/test_training_callbacks.py:200` actively asserts
this silence.

The question the instrument needs to answer is whether JEPA is learning real structure.
The failure mode is **representation collapse**: the encoder emits near-constant
embeddings, the predictor trivially satisfies its objective, and the loss curve looks
healthy while the model has learned nothing. None of the currently logged signals
(`jepa/infonce_loss`, `jepa/concept_loss`, `jepa/diversity_loss`) distinguish collapse
from success — all three can look fine during collapse.

## Goals

- Detect JEPA representation collapse quantitatively, per epoch, cheaply enough to leave on.
- Make the embedding space explorable so "what did it organize?" is answerable, not just "did it collapse?".
- Behave identically on Windows (CPU smoke runs) and Linux/ROCm (real training).
- Stop failing silently.

## Non-Goals

- Experiment comparison across runs (hparams dashboards, run-naming discipline). Deferred:
  it is experiment management, not structure detection, and there are no runs worth
  comparing yet.
- Replacing or refactoring the existing scalar/histogram logging, which is sound.
- Any change to training *dynamics* — no change to the loss, optimizer, schedule, or model
  architecture. Observation only. Note this does require **wiring** edits to
  `jepa_train.py` (registering the projector, supplying the probe batch); those are
  in scope, and they must not alter what the model computes.
- GPU/ROCm enablement. Heavy training runs on the Linux side of the dual-boot; this spec
  assumes that and does not attempt a Windows GPU path.

## Current State

Three findings from the 2026-08-09 audit:

1. **`TensorBoardCallback` is inert.** `tensorboard` is not installed in the runtime
   environment, so all logging is skipped without error.
2. **`EmbeddingProjector` is orphaned and doubly inert.**
   `Programma_CS2_RENAN/backend/nn/embedding_projector.py:79-82` sets
   `self._active = tb_writer is not None`, so constructing it without a writer makes it a
   silent no-op — and nothing in the codebase constructs it at all. It is already a
   `TrainingCallback` (line 69) whose constructor accepts an external writer, so it is
   designed to share one.
3. **Event-file fragmentation.** The prior run logs recovered from the ext4 drive
   (`runs/jepa_pretrain`) contain **8 event files written by a single process** (same PID,
   spanning 4 seconds). Leading hypothesis: more than one `SummaryWriter` was opened
   against the same `log_dir`. A dashboard split across 8 files is unreadable.

`jepa_train.py:455` constructs `TensorBoardCallback` and registers it via
`CallbackRegistry([tb_callback])`. `jepa_train.py` maintains an `ema_state`, so EMA target
drift is measurable.

## Design

### Component 1 — `backend/nn/collapse_metrics.py` (new)

Pure functions, no TensorBoard import and no model coupling:

```
compute_collapse_metrics(embeddings: Tensor) -> dict[str, float]
compute_ema_drift(online_params, ema_params) -> float
```

`embeddings` is a 2-D `[N, D]` tensor. Isolating this as pure functions makes the metrics
unit-testable without TensorBoard, a training loop, or a GPU, and reusable from anywhere
(CLI diagnostics, notebooks) later.

### Component 2 — Metrics

Computed each epoch and logged as scalars:

| Scalar | Definition | Collapse signature |
|---|---|---|
| `embed/std_mean` | mean over dims of per-dimension std of L2-normalized embeddings | → 0 |
| `embed/std_min` | min over dims of the same | → 0 (catches partial collapse first) |
| `embed/effective_rank` | participation ratio of covariance eigenvalues: `(Σλ)² / Σλ²` | → 1 |
| `embed/cosine_offdiag_mean` | mean pairwise cosine similarity, diagonal excluded | → 1 |
| `embed/ema_drift` | L2 distance between online and EMA target encoder parameters | → 0 |

L2-normalization before the std and cosine metrics makes them scale-invariant, so a model
that merely shrinks its output magnitude is not mistaken for one that has collapsed in
direction.

`embed/ema_drift` is logged only when the trainer supplies EMA state; it is skipped
without error otherwise (the RAP path has no EMA target).

### Component 3 — Fixed probe batch

At `on_train_start`, sample one batch and retain it for the lifetime of the run. Every
epoch's metrics are computed from a no-grad forward pass over that same batch.

Rationale: metrics computed over varying batches conflate *change in the model* with
*change in the input*, making the epoch-over-epoch trend — the entire signal we care about
— uninterpretable. A fixed probe makes the curve mean exactly one thing.

The probe batch is captured via the existing `on_train_start(model, config)` hook; the
trainer passes it in `config` under key `probe_batch`. If absent, collapse metrics are
skipped with a single WARNING naming the consequence.

Cost: one forward pass per epoch, no gradients. Acceptable always-on in both environments.

### Component 4 — Single-writer ownership

`TensorBoardCallback` constructs and owns the only `SummaryWriter`. `EmbeddingProjector`
is constructed with that writer and registered in the same `CallbackRegistry`:

```
tb = TensorBoardCallback(log_dir=..., model_type="jepa_pretrain")
proj = EmbeddingProjector(tb_writer=tb.writer, interval=5)
callbacks = CallbackRegistry([tb, proj])
```

`CallbackRegistry.close_all()` already exists; only `TensorBoardCallback.close()` closes
the writer, so the projector must not close it. This is the fragmentation fix.

The projector keeps its existing `interval` (default 5 epochs) and writes `add_embedding`
for belief and concept vectors. UMAP figures remain optional: `umap-learn` is not a
dependency, and `add_embedding` provides PCA/t-SNE in the browser without it. When
`umap-learn` is absent the projector logs its existing warning and skips only the UMAP
figures.

### Component 5 — Loud failure

`tensorboard` moves from `requirements-dev.in` into the runtime lock files so the default
environment can log.

Failure behavior changes from silent to visible:

- If `tensorboard` is unavailable, emit **one** WARNING at `on_train_start` stating that no
  metrics will be recorded for this run.
- Honor `CS2_TB_STRICT=1` (env var): when set, an unavailable `tensorboard` raises at
  construction instead of degrading.

`test_training_callbacks.py:200-240` currently asserts the silent-no-op contract. Those
tests are updated to assert the new contract: degrade without raising by default, warn
exactly once, and raise under `CS2_TB_STRICT=1`.

### Component 6 — Environment parity

Log directory becomes `RUNS_DIR/<model_type>/<run_id>`, where `run_id` is
`<UTC timestamp>-<device tag>` (e.g. `20260809T124500Z-rocm`, `20260809T124500Z-cpu`).
`RUNS_DIR` already resolves per-platform via `Programma_CS2_RENAN/core/config.py:386`.

The device tag is derived as: `rocm` when `torch.version.hip` is set and a GPU is
available, `cuda` when `torch.version.cuda` is set and a GPU is available, otherwise
`cpu`. It describes the device training actually ran on, not the one requested.

Recording the device in the run id prevents a Windows CPU smoke run from being mistaken
for a Linux ROCm run in the dashboard — a real hazard given heavy training runs on Linux
while inspection may happen on Windows.

## Testing

**Unit (`Programma_CS2_RENAN/tests/test_collapse_metrics.py`, new)** — deterministic, no
TensorBoard, no GPU. NN tests live under `Programma_CS2_RENAN/tests/`; `pytest.ini` sets
`testpaths = tests Programma_CS2_RENAN/tests`:

- Collapsed input: `[N, D]` matrix of near-identical rows plus tiny noise. Assert
  `std_mean → ~0`, `effective_rank → ~1`, `cosine_offdiag_mean → ~1`.
- Healthy input: orthogonal-ish random rows. Assert `effective_rank` scales with `D`,
  `cosine_offdiag_mean → ~0`, `std_mean` bounded away from 0.
- Scale invariance: multiplying embeddings by a constant leaves all metrics unchanged.
- `compute_ema_drift` returns 0 for identical parameter sets and grows with divergence.

**Integration (`Programma_CS2_RENAN/tests/test_tensorboard_integration.py`, new)** —
requires `tensorboard`:

- A short run over a stub model produces **exactly one** event file in the run directory
  (locks in the fragmentation fix).
- That file contains the expected `embed/*` tags.

**Updated** — `tests/test_training_callbacks.py` for the loud-failure contract above.

## Dependencies

- `tensorboard==2.21.0` moves into `requirements-lock.txt` / `requirements-lock-cpu.txt`
  (already pinned at `requirements-dev.in:62`).
- `umap-learn` remains optional and unlisted; the projector degrades without it.

## Risks

- **Previously quiet runs will start warning.** Intended: that silence is the bug.
- **`add_embedding` disk cost** grows with embedding count × interval. Mitigated by the
  existing `interval` default of 5; revisit if run directories become unwieldy.
- **Fragmentation cause is a hypothesis.** Single-writer ownership is correct regardless,
  but the integration test is what actually proves the fix; if one event file is still not
  produced, the true cause must be found before closing the work.
- **Probe batch representativeness.** A single batch may be unrepresentative of the
  dataset. Accepted: the metric is a *trend* indicator, not an absolute measure, and a
  fixed batch is what makes the trend readable.

## Out of Scope

Recorded here because they were found during this audit and will otherwise be forgotten —
each needs its own decision, and none belong in this change:

- `run_ingestion.py` coaching path is orphaned (`ingest_user_demos` has no callers).
- `ExplanationGenerator` feeds z-scores into a percentage formatter, inverting positive feedback.
- `generate_advice` is called with a hardcoded `confidence=0.85`.
- `.dem.info` sidecars are never read, and archiving orphans them from their demos.
