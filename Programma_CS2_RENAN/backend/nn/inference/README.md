# `backend/nn/inference/` — Inference-only neural utilities

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/inference/`
> **Skill:** `/ml-check`

## Purpose

This package holds neural-network components that are used **only at inference time** — they consume already-trained checkpoints, never run training loops, and never own training-side state (optimizer, scheduler, EMA shadow, etc.).

The intent is to keep training and inference paths physically separated in the source tree so that:

- A pure-inference deployment (no PyTorch optimizer, no DataLoader) imports a smaller surface.
- Training-only invariants (gradient flow, EMA cloning, target-encoder freezing) cannot leak into inference paths.
- Tests for inference behaviour can be written without spinning up a trainer.

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `ghost_engine.py` | `GhostEngine` — projects predicted player positions into the tactical map for the "ghost AI" overlay in the Tactical Viewer. Loads the active JEPA / RAP checkpoint and runs forward-only inference on tick batches. |

## `GhostEngine` summary

- Loads model via `ModelFactory.get_model(model_type).eval()` and disables grad with `torch.no_grad()`.
- Accepts a sliding window of recent tick features (25-dim `METADATA_DIM`) and emits projected position deltas.
- Caches the model handle so repeated calls reuse the same parameters; reset via the public `reset()` helper after a checkpoint swap.
- Falls back to a zero-prediction path when no checkpoint exists, so the UI remains usable on a fresh installation.

## Integration points

| Consumer | Usage |
|----------|-------|
| `apps/qt_app/screens/tactical_viewer_screen.py` | Renders ghost projections on the tactical map overlay |
| `apps/legacy_kivy/tactical_viewmodels.py` (`TacticalGhostViewModel`) | Lazy-loads the engine on demand to avoid startup cost |

## Development notes

- **No training-side imports.** Modules here must not import from `training_orchestrator.py`, trainers, EMA helpers, or DataLoader assemblies.
- **No file mutation.** Inference utilities never write checkpoints. Saving belongs to `nn/persistence.py:save_nn()` invoked from training paths.
- **Determinism.** Inference is invoked from UI threads — guard any tensor operation that is not idempotent (e.g. dropout) with `model.eval()`.
- **Graceful degradation.** Missing checkpoint → zero-prediction fallback, log at `WARNING`. Never raise into the UI thread.

## Related

- Trained checkpoints: `Programma_CS2_RENAN/models/global/`
- Persistence helpers: `backend/nn/persistence.py`
- Inference orchestration: `backend/services/coaching_service.py`
- Tactical viewer (consumer): `apps/qt_app/screens/tactical_viewer_screen.py`
