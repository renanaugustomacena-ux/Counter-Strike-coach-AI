# `backend/nn/experimental/rap_coach/` — RAP Coach (experimental)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/`
> **Skill:** `/ml-check`, `/jepa-audit`
> **Status:** Experimental — gated behind `USE_RAP_MODEL=True`. Not loaded by the default coaching pipeline.

## Purpose

RAP Coach (**R**easoning + **A**cting + **P**edagogy) is a multi-head policy network that consumes synthesized visual tensors (view / map / motion frames) plus the 25-dim per-tick metadata vector and produces:

- A 10-dimensional **strategy** output (trained against one-hot tactical-role targets).
- A scalar **value** estimate of round-win probability.
- A 3-dimensional **position** delta forecast for the player.
- Full strategy **gate probabilities**, fed to an entropy-based sparsity loss (RAP-AUDIT-04) that drives expert specialisation.
- A 64-dim **belief** state, a 5-concept causal **attribution**, and the recurrent **hidden state** (NN-40).

Architecturally it is a pipeline of perception → memory → strategy → pedagogy (value + causal attribution) → position head, with a template-based communication layer outside the `nn.Module` graph — built on top of `ncps` Liquid Time-Constant (LTC) cells for temporal reasoning across the 32-tick window (`RAP_SEQ_LEN`).

## File inventory

| File | Component | Purpose |
|------|-----------|---------|
| `__init__.py` | — | Package marker. |
| `perception.py` | `RAPPerception` | Visual / spatial feature aggregator. Consumes per-tick views, mini-map, and motion tensors and projects to a unified perception embedding. |
| `memory.py` | `RAPMemory`, `RAPMemoryLite` | Temporal memory over the 32-tick window: LTC with 512 NCP units (154 motor outputs projected to 256 via `ltc_projection`) + `HopfieldLayer` associative memory (4 heads, 32 trainable prototypes, bypassed until `notify_optimizer_step()`, NN-MEM-01) + belief head; `RAPMemoryLite` is the LSTM fallback. **Contains the RAP-LTC-FIX** monkey-patch on `ncps.LTCCell._ode_solver` (lines 70–93) — patches a 1-D / 2-D shape mismatch in `cm / (elapsed_time / ode_unfolds)`. |
| `strategy.py` | `RAPStrategy` | Strategy head: Top-2 sparse MoE routing (RAP-AUDIT-08) over 4 experts (SuperpositionLayer FiLM → ReLU → Linear). Gate emits raw logits; top-2 are softmax-renormalised, full gate softmax is returned for the entropy sparsity loss. Context = metadata + belief, 89-dim (RAP-AUDIT-09). |
| `pedagogy.py` | `RAPPedagogy`, `CausalAttributor` | `RAPPedagogy`: critic value head (256→64→1) with skill adapter (10→256). `CausalAttributor`: maps latent state + position delta to 5 concept attributions (Positioning, Crosshair Placement, Aggression, Utility, Rotation). |
| `communication.py` | `RAPCommunication` | Communication layer: skill-tiered template engine (plain class, not an `nn.Module`) that turns model outputs into templated advice; suppresses advice below the 0.7 confidence threshold. |
| `chronovisor_scanner.py` | `ChronovisorScanner` | Identifies temporally critical "moments" in a replay using the strategy + value heads. Supplies markers to the Tactical Viewer. |
| `model.py` | `RAPCoachModel` | Composes perception, memory, strategy, pedagogy, causal attribution, and the position head (`RAPCommunication` stays external). Forward returns 7 outputs incl. `hidden_state` (NN-40) and accepts per-timestep 5D or static 4D visual input (NN-39). Loaded via `ModelFactory.get_model('rap')`. Initialised dimensions: `metadata_dim=25`, `output_dim=10`, `hidden=256`, `perception=128`. |
| `trainer.py` | `RAPTrainer` | Training driver: composite loss (strategy + value + entropy sparsity + position), Z-axis penalty, AMP, scheduler. Constructed by `TrainingOrchestrator(model_type='rap')`. |
| `conftest.py` | — | Sets `collect_ignore = ["test_arch.py"]` — excludes the validation utility from pytest collection. |
| `test_arch.py` | — | Standalone architecture validation utility (forward-pass shapes on a tiny synthetic batch), used by `headless_validator.py` Phase 16; not collected by pytest. |

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
| RAP-AUDIT-01 | `training_orchestrator.py:793` | `RAP_SEQ_LEN = 32` — temporal window for LTC sequence processing. Must match `state_reconstructor.py` default. |
| RAP-AUDIT-02 | `training_orchestrator.py:_rap_compute_target_pos` | Per-tick position deltas required for position-head training. |
| RAP-AUDIT-05 | `training_orchestrator.py:_rap_compute_timespans` | Inter-tick `dt` required for LTC ODE integration. Constant 1/64 s in canonical replays but kept tensorial for future variable-tick support. |
| LEAK-01 | `training_orchestrator.py:_rap_collect_per_tick` | `val_mask=False` when the round outcome is unavailable, so the value head never trains on the leaked round outcome. |
| NN-TR-02b | `trainer.py:compute_position_loss` | Z-axis penalty enforced in the position loss to prevent vertical drift on multi-level maps. |
| POV-RAP-FIX-2 | `training_orchestrator.py:_rap_prefetch_caches` / `_rap_collect_per_tick` | `match_id` fallback from `demo_name_to_match_id` when DB FK is `None`. |
| T-2 FIX | `training_orchestrator.py:_rap_segment_windows` | ≥ 50% POV density gate per temporal window. |

Tests for these invariants live in `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py` and `Programma_CS2_RENAN/tests/test_rap_coach.py`.

## Boundaries

- **Do not import RAP modules from production coaching code.** The training gate lives in `TrainingOrchestrator.__init__` (raises `ValueError` when `USE_RAP_MODEL` is `False`); the inference entry point is `GhostEngine` (`backend/nn/inference/ghost_engine.py`), which checks the flag and stays disabled when it is unset. Direct imports bypass these gates.
- **Do not modify `RAP_SEQ_LEN` without re-training all RAP checkpoints.** It is part of the architecture contract.
- **Do not strip the `RAP-LTC-FIX` monkey-patch.** The shape bug in upstream ncps still applies as of HEAD. The CI test in `test_rap_training_dry_run.py` asserts the fix marker is present.

## Related

- Experimental sandbox parent: `backend/nn/experimental/README.md`
- Production NN sub-packages: `backend/nn/README.md`
- Training orchestrator: `backend/nn/training_orchestrator.py`
- Smoke / regression test: `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py`
- ncps upstream: <https://github.com/mlech26l/ncps>
- Original architecture docs: `docs/Studies/` (RAP volumes)
