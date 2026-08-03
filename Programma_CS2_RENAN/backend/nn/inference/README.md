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
| `ghost_engine.py` | `GhostEngine` — projects predicted player positions into the tactical map for the "ghost AI" overlay in the Tactical Viewer. Gated behind `USE_RAP_MODEL` (default `False`); loads the `rap_coach` checkpoint and runs forward-only inference per tick. |

## `GhostEngine` summary

- Checks `USE_RAP_MODEL` first (default `False`) — when unset, no model is loaded and predictions stay disabled.
- Loads the RAP model via `ModelFactory.get_model(TYPE_RAP)` + `load_nn("rap_coach", ...)`, then `.eval()`; inference runs under `torch.no_grad()`.
- `predict_tick()` accepts a single tick (dict or dataclass) plus an optional `game_state` dict, builds view / map / motion tensors via `TensorFactory` and the 25-dim metadata vector via `FeatureExtractor`, and returns `(ghost_x, ghost_y)` world coordinates (current position + delta × `RAP_POSITION_SCALE`).
- Player-POV tensor mode is opt-in via `USE_POV_TENSORS` (default `False`); legacy tensors are used otherwise.
- Returns `None` on any failure — model disabled, missing checkpoint, missing `map_name`, or inference error. (R4: the old `(0.0, 0.0)` sentinel was a valid world coordinate near map center and was removed.)

## Integration points

| Consumer | Usage |
|----------|-------|
| `apps/qt_app/screens/tactical_viewer_screen.py` | Renders ghost projections on the tactical map overlay |
| `apps/qt_app/viewmodels/tactical_vm.py` (`TacticalGhostVM`) | Lazy-loads the engine on demand to avoid startup cost |

## Development notes

- **No training-side imports.** Modules here must not import from `training_orchestrator.py`, trainers, EMA helpers, or DataLoader assemblies.
- **No file mutation.** Inference utilities never write checkpoints. Saving belongs to `nn/persistence.py:save_nn()` invoked from training paths.
- **Determinism.** Inference is invoked from UI threads — guard any tensor operation that is not idempotent (e.g. dropout) with `model.eval()`.
- **Graceful degradation.** Missing checkpoint or failed inference → `None` return, log at `WARNING`. Never raise into the UI thread.

## Related

- Trained checkpoints: `Programma_CS2_RENAN/models/global/`
- Persistence helpers: `backend/nn/persistence.py`
- Lazy-loading consumer: `apps/qt_app/viewmodels/tactical_vm.py` (`TacticalGhostVM`)
- Tactical viewer (consumer): `apps/qt_app/screens/tactical_viewer_screen.py`
