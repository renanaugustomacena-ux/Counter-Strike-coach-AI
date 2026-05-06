# `backend/nn/experimental/rap_coach/` — RAP Coach (experimental)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/`
> **Skill:** `/ml-check`, `/jepa-audit`
> **Status:** Experimental — gated behind `USE_RAP_MODEL=True`. Not loaded by the default coaching pipeline.

## Purpose

RAP Coach (**R**easoning + **A**cting + **P**edagogy) is a multi-head policy network that consumes the JEPA world-model embedding plus per-tick state and produces:

- A 10-dimensional **strategy** label (one-hot over the canonical tactical roles).
- A scalar **value** estimate of round-win probability.
- A 3-dimensional **position** delta forecast for the player.
- A scalar **sparsity** signal that drives L1 regularisation on the strategy gates.

Architecturally it is a 7-stage pipeline — perception → memory → strategy → pedagogy → communication — built on top of `ncps` Liquid Time-Constant (LTC) cells for temporal reasoning across the 32-tick window (`RAP_SEQ_LEN`).

## File inventory

| File | Component | Purpose |
|------|-----------|---------|
| `__init__.py` | — | Package marker. |
| `perception.py` | `RAPPerception` | Visual / spatial feature aggregator. Consumes per-tick views, mini-map, and motion tensors and projects to a unified perception embedding. |
| `memory.py` | `RAPMemory` | LTC-based temporal memory over the 32-tick window. **Contains the RAP-LTC-FIX** monkey-patch on `ncps.LTCCell._ode_solver` (lines 70–93) — patches a 1-D / 2-D shape mismatch in `cm / (elapsed_time / ode_unfolds)`. |
| `strategy.py` | `RAPStrategy` | Strategy head: superposition layer + 10-class softmax over tactical roles. |
| `pedagogy.py` | `RAPPedagogy` | Pedagogy head: explanation prior — produces a low-dim representation downstream of the strategy decision used for explainability. |
| `communication.py` | `RAPCommunication` | Communication head: small MLP that the RAG / coaching layer can condition on for policy-aware prose generation. |
| `chronovisor_scanner.py` | `ChronovisorScanner` | Identifies temporally critical "moments" in a replay using the strategy + value heads. Supplies markers to the Tactical Viewer. |
| `model.py` | `RAPCoachModel` | Composes the 7 stages. Loaded via `ModelFactory.get_model('rap')`. Initialised dimensions: `metadata_dim=25`, `output_dim=10`, `hidden=256`, `perception=128`. |
| `trainer.py` | `RAPTrainer` | Training driver: composite loss (strategy + value + sparsity + position), Z-axis penalty, AMP, scheduler. Constructed by `TrainingOrchestrator(model_type='rap')`. |
| `conftest.py` | — | Pytest fixtures local to this package (e.g. tiny RAP fixture for arch tests). |
| `test_arch.py` | — | Tests that verify forward-pass shapes and gradient flow on a tiny synthetic batch. Runs in CI without real demos. |

## Activation

```python
# core/config.py defaults
"USE_RAP_MODEL": False,    # default

# Enable for a session via _settings dict (no disk write):
from Programma_CS2_RENAN.core import config
with config._settings_lock:
    config._settings["USE_RAP_MODEL"] = True

# Or persist via:
from Programma_CS2_RENAN.core.config import save_user_setting
save_user_setting("USE_RAP_MODEL", True)
```

`TrainingOrchestrator.__init__` raises `ValueError` if `model_type='rap'` is requested while the flag is `False`. This protects unintended training runs.

## Training

Entry point: `run_full_training_cycle.py --dry-run --model-type rap --epochs 1`

Or programmatically:

```python
from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager

manager = CoachTrainingManager()
manager.assign_dataset_splits()
orch = TrainingOrchestrator(manager, model_type="rap", max_epochs=1, patience=1)
orch.run_training()
```

## Critical invariants

| ID | File / line | Invariant |
|----|-------------|-----------|
| RAP-LTC-FIX | `memory.py:70-93` | `_ode_solver` shape patch — must remain in place; future ncps upgrades may make it redundant but should not break it silently. |
| RAP-AUDIT-01 | `trainer.py`, `training_orchestrator.py:496` | `RAP_SEQ_LEN = 32` — temporal window for LTC sequence processing. Must match `state_reconstructor.py` default. |
| RAP-AUDIT-02 | `training_orchestrator.py:_rap_compute_target_pos` | Per-tick position deltas required for position-head training. |
| RAP-AUDIT-05 | `training_orchestrator.py:_rap_compute_timespans` | Inter-tick `dt` required for LTC ODE integration. Constant 1/64 s in canonical replays but kept tensorial for future variable-tick support. |
| LEAK-01 | `training_orchestrator.py:686-693` | `val_mask=False` when knowledge unavailable, so the value head never trains on the leaked round outcome. |
| NN-TR-02b | `trainer.py:43-100` | Z-axis penalty enforced in the position loss to prevent vertical drift on multi-level maps. |
| POV-RAP-FIX-2 | `training_orchestrator.py:632-637` | `match_id` fallback from `demo_name_to_match_id` when DB FK is `None`. |
| T-2 FIX | `training_orchestrator.py:756-780` | ≥ 50% POV density gate per temporal window. |

Tests for these invariants live in `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py` and `Programma_CS2_RENAN/tests/test_rap_coach.py`.

## Boundaries

- **Do not import RAP modules from production coaching code.** `coaching_service.py` selects the RAP backend through `ModelFactory.get_model('rap')`, which raises if the flag is unset. Direct imports bypass the gate.
- **Do not modify `RAP_SEQ_LEN` without re-training all RAP checkpoints.** It is part of the architecture contract.
- **Do not strip the `RAP-LTC-FIX` monkey-patch.** The shape bug in upstream ncps still applies as of HEAD. The CI test in `test_rap_training_dry_run.py` asserts the fix marker is present.

## Related

- Experimental sandbox parent: `backend/nn/experimental/README.md`
- Production NN sub-packages: `backend/nn/README.md`
- Training orchestrator: `backend/nn/training_orchestrator.py`
- Smoke / regression test: `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py`
- ncps upstream: <https://github.com/mlech26l/ncps>
- Original architecture docs: `docs/Studies/` (RAP volumes)
