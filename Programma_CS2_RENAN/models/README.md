> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Neural Network Checkpoint Storage

> **Authority:** Rule 4 (Data Persistence)

This directory stores trained neural network checkpoints (`.pt` files) used by the
Ghost Engine for real-time inference and by the coaching pipeline for ML-augmented
advice generation. Checkpoints are binary PyTorch `state_dict` serializations
managed exclusively through the `persistence.py` module, which enforces atomic
writes, multi-fallback loading, and strict dimension validation.

No `.pt` files are committed to the repository. This directory exists in version
control to preserve its structure (via `global/README.txt`), to hold the CTF-1
checkpoint hash registry (`checkpoint_hashes.json`), and to serve as the default
write target when `BRAIN_DATA_ROOT` is not configured.

## Directory Structure

```
models/
├── global/                   # Shared baseline models (not user-specific)
│   └── README.txt           # Placeholder to preserve directory in git
├── checkpoint_hashes.json    # CTF-1 SHA-256 hash registry for checkpoints
├── README.md                 # This file (English)
├── README_IT.md              # Italian translation
└── README_PT.md              # Portuguese translation
```

At runtime, user-specific fine-tuned models are stored in per-user subdirectories:

```
models/
├── global/                  # Shared baseline (from pro demo training)
│   ├── latest.pt           # Default coach model (AdvancedCoachNN)
│   ├── jepa_brain.pt       # JEPA pre-trained on pro matches
│   └── rap_coach.pt        # RAP model checkpoint
└── {user_id}/               # Per-user fine-tuned models
    └── latest.pt           # User-adapted checkpoint
```

Each checkpoint is accompanied by a `.pt.meta.json` sidecar (GAP-07) recording
`schema_version`, `metadata_dim`, and the feature-name list at save time.

## Checkpoint Inventory

Version strings map to `ModelFactory` model types:

| Checkpoint | Model Class | Created By | Input Dim |
|-----------|-------------|-----------|-----------|
| `latest.pt` | AdvancedCoachNN (default) | `backend/nn/train.py`, `coach_manager.py` | 25 (METADATA_DIM) |
| `jepa_brain.pt` | JEPA coaching model | `backend/nn/jepa_trainer.py` | 25 (METADATA_DIM) |
| `vl_jepa_brain.pt` | VL-JEPA (concept head) | `backend/nn/training_orchestrator.py` | 25 (METADATA_DIM) |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/experimental/rap_coach/trainer.py` | 25 (METADATA_DIM) |
| `rap_lite_coach.pt` | RAP-Lite (LSTM memory) | RAP training with `use_lite_memory` | 25 (METADATA_DIM) |
| `role_head.pt` | NeuralRoleHead | Role classification training | 5 |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` (offline utility) | 9 (offline subset) |

## Checkpoint Format

Every `.pt` file is a PyTorch `state_dict` dictionary saved via `torch.save()`.
The keys correspond to the named parameters of the model class. Example structure
for `jepa_brain.pt`:

```python
{
    "online_encoder.layer1.weight": Tensor(...),
    "online_encoder.layer1.bias": Tensor(...),
    "coaching_head.fc1.weight": Tensor(...),
    "coaching_head.fc1.bias": Tensor(...),
    # ... all named parameters
}
```

For models that use EMA (Exponential Moving Average), the shadow weights are stored
**inside** the same checkpoint dictionary, not as separate files. The EMA module
clones shadow tensors during `apply_shadow()` to preserve originals (invariant NN-16).

## Persistence Architecture

The `backend/nn/persistence.py` module is the **sole** interface for checkpoint I/O.
Direct `torch.save()` / `torch.load()` calls from other modules are forbidden.

### Atomic Write Protocol

```
save_nn(model, version, user_id=None, extra_meta=None)
  1. Resolve target path: models/{user_id or "global"}/{version}.pt
  2. Write weights and .pt.meta.json sidecar to temporary files
  3. Atomic replace: tmp_path.replace(path)  # weights first, then sidecar
  4. Record SHA-256 in checkpoint_hashes.json (CTF-1)
  5. On failure: unlink tmp files, re-raise
```

This prevents corruption when the application crashes mid-write or when the system
loses power during training.

### Multi-Fallback Load Chain

```
load_nn(version, model, user_id=None)
  1. Try: models/{user_id}/{version}.pt         (user-specific learned model)
  2. Try: models/global/{version}.pt            (shared baseline)
  3. Try: bundled factory/{user_id}/{version}.pt (PyInstaller bundled, user)
  4. Try: bundled factory/global/{version}.pt   (PyInstaller bundled, global)
  5. Fail: raise FileNotFoundError              (no silent random weights)
```

Before the weights touch the model, the resolved file is verified against the
CTF-1 hash registry, and its `.pt.meta.json` sidecar (if present) is validated
for `schema_version`, `metadata_dim`, and feature-name drift -- any mismatch
raises `StaleCheckpointError`. Legacy checkpoints without a sidecar load with
a warning.

### Dimension Validation

When loading, `model.load_state_dict(state_dict, strict=True)` is used. If the
checkpoint was produced by a model with different architecture (e.g., after
`METADATA_DIM` changed from 25 to 26), the load fails with a `RuntimeError`.
The persistence module catches this and raises `StaleCheckpointError`, which
signals to callers that re-training is required.

## Critical Warnings

| ID | Rule | Consequence of Violation |
|----|------|------------------------|
| NN-14 | Never silently return a model with random weights | Garbage coaching output, user trust destroyed |
| NN-16 | EMA `apply_shadow()` must `.clone()` shadow tensors | Training corruption, non-recoverable |
| NN-MEM-01 | Hopfield memory bypassed until `notify_optimizer_step()` fires | NaN propagation in RAP memory |
| — | `WinProbabilityNN` (12 features) vs `WinProbabilityTrainerNN` (9 features) | Cross-loading crashes or silent corruption |

The `WinProbabilityNN` (production, 12 features) and `WinProbabilityTrainerNN`
(offline training, 9 features) use **different architectures**. Their checkpoints
are not interchangeable. Never cross-load between them.

After any architecture change (modifying `METADATA_DIM`, `HIDDEN_DIM`, `OUTPUT_DIM`,
or layer structure), all existing checkpoints become invalid. The system detects
this automatically via `strict=True` loading and raises `StaleCheckpointError`.

## Model Versioning

Checkpoints are versioned by their file name (`version` parameter in
`save_nn` / `load_nn`); the `.pt.meta.json` sidecar additionally embeds a
`schema_version` (GAP-07). Compatibility is enforced both by the sidecar check
and structurally: if the `state_dict` keys or tensor shapes do not match the
current model class, loading fails deterministically.

| Version String | Model | Training Source |
|---------------|-------|-----------------|
| `latest` | AdvancedCoachNN | Default training pipeline (`train.py`, `coach_manager.py`) |
| `jepa_brain` | JEPA coaching model | Pro demo dataset (JEPA two-stage training) |
| `vl_jepa_brain` | VL-JEPA | Pro demo dataset (concept-head training) |
| `rap_coach` | RAPCoachModel | Pro demo dataset (RAP LTC-Hopfield training) |
| `rap_lite_coach` | RAP-Lite | RAP training with LSTM fallback memory |
| `role_head` | NeuralRoleHead | Role classification dataset |
| `win_prob` | WinProbabilityTrainerNN | Round outcome dataset (offline utility) |

## Bundling (PyInstaller)

The load chain supports factory-bundled checkpoints: `get_factory_model_path()`
resolves them through `get_resource_path()`, which checks `sys._MEIPASS` in the
frozen environment. Note that the current `packaging/cs2_analyzer_win.spec`
does **not** include a `models/` entry in its `datas` list, so the factory
tiers only resolve when a build explicitly bundles checkpoints.

## Integration Points

| Consumer | Checkpoint | Operation |
|----------|-----------|-----------|
| `backend/nn/jepa_trainer.py` | `jepa_brain.pt` | Write after training |
| `backend/nn/coach_manager.py` | `latest.pt` | Save global/user models; load for inference |
| `backend/nn/training_orchestrator.py` | `jepa_brain.pt`, `vl_jepa_brain.pt` | Load/save with `StaleCheckpointError` handling |
| `backend/nn/experimental/rap_coach/trainer.py` | `rap_coach.pt` | Write after RAP training |
| `backend/nn/win_probability_trainer.py` | `win_prob.pt` | Write after win-prob training (offline) |

## Development Notes

- **Do NOT commit `.pt` files** to the repository — they are large binary artifacts
- The `global/` directory must exist in the repo (preserved by `README.txt`)
- Training logs are written by `backend/nn/training_monitor.py` (JSON format), not stored here
- The `MODELS_DIR` path is resolved from `core/config.py` and defaults to this directory
- When `BRAIN_DATA_ROOT` is set, models are written to `{BRAIN_DATA_ROOT}/models/` instead
- Always use `save_nn()` / `load_nn()` from `persistence.py` — never call `torch.save()` directly
- After changing model architecture, delete stale checkpoints and retrain from scratch
