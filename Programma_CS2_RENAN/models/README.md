> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Neural Network Checkpoint Storage

> **Authority:** Rule 4 (Data Persistence)

This directory stores trained neural network checkpoints (`.pt` files) used by the
Ghost Engine for real-time inference and by the coaching pipeline for ML-augmented
advice generation. Checkpoints are binary PyTorch `state_dict` serializations
managed exclusively through the `persistence.py` module, which enforces atomic
writes, multi-fallback loading, and strict dimension validation.

No `.pt` files are committed to the repository. This directory exists in version
control solely to preserve its structure (via `global/README.txt`) and to serve as
the default write target when `BRAIN_DATA_ROOT` is not configured.

## Directory Structure

```
models/
├── global/                   # Shared baseline models (not user-specific)
│   └── README.txt           # Placeholder to preserve directory in git
├── README.md                 # This file (English)
├── README_IT.md              # Italian translation
└── README_PT.md              # Portuguese translation
```

At runtime, user-specific fine-tuned models are stored in per-user subdirectories:

```
models/
├── global/                  # Shared baseline (from pro demo training)
│   ├── jepa_brain.pt       # JEPA pre-trained on pro matches
│   ├── rap_coach.pt        # RAP model checkpoint
│   └── win_prob.pt         # Win probability model
└── {user_id}/               # Per-user fine-tuned models (future)
    └── jepa_brain.pt       # User-adapted JEPA checkpoint
```

## Checkpoint Inventory

| Checkpoint | Model Class | Created By | Typical Size | Input Dim |
|-----------|-------------|-----------|--------------|-----------|
| `jepa_brain.pt` | JEPACoachingModel | `backend/nn/jepa_trainer.py` | ~3.6 MB | 25 (METADATA_DIM) |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/experimental/rap_coach/trainer.py` | Variable | 25 (METADATA_DIM) |
| `coach_brain.pt` | AdvancedCoachNN (legacy) | `backend/nn/train.py` | ~1 MB | 25 (METADATA_DIM) |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` | ~100 KB | 9 (offline subset) |
| `role_head.pt` | NeuralRoleHead | Role classification training | ~50 KB | Variable |

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
save_nn(model, version, user_id=None)
  1. Resolve target path: models/{user_id or "global"}/{version}.pt
  2. Write to temporary file: {version}.pt.tmp
  3. Atomic replace: tmp_path.replace(path)  # POSIX atomic
  4. On failure: unlink tmp, re-raise
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
| NN-MEM-01 | Hopfield bypassed until >=2 training forward passes | NaN propagation in RAP memory |
| — | `WinProbabilityNN` (12 features) vs `WinProbabilityTrainerNN` (9 features) | Cross-loading crashes or silent corruption |

The `WinProbabilityNN` (production, 12 features) and `WinProbabilityTrainerNN`
(offline training, 9 features) use **different architectures**. Their checkpoints
are not interchangeable. Never cross-load between them.

After any architecture change (modifying `METADATA_DIM`, `HIDDEN_DIM`, `OUTPUT_DIM`,
or layer structure), all existing checkpoints become invalid. The system detects
this automatically via `strict=True` loading and raises `StaleCheckpointError`.

## Model Versioning

Checkpoints are versioned implicitly by their file name (`version` parameter in
`save_nn` / `load_nn`). There is no explicit version number embedded in the
checkpoint. Compatibility is enforced structurally: if the `state_dict` keys or
tensor shapes do not match the current model class, loading fails deterministically.

| Version String | Model | Training Source |
|---------------|-------|-----------------|
| `jepa_brain` | JEPACoachingModel | Pro demo dataset (JEPA two-stage training) |
| `rap_coach` | RAPCoachModel | Pro demo dataset (RAP LTC-Hopfield training) |
| `coach_brain` | AdvancedCoachNN | Legacy training pipeline |
| `win_prob` | WinProbabilityTrainerNN | Round outcome dataset |
| `role_head` | NeuralRoleHead | Role classification dataset |

## Bundling (PyInstaller)

The `global/` subdirectory is included in the frozen executable:

```python
# In cs2_analyzer_win.spec
datas += [('models/global', 'models/global')]
```

At runtime, `get_factory_model_path()` resolves bundled checkpoints through
`get_resource_path()`, which checks `sys._MEIPASS` for the frozen environment.

## Integration Points

| Consumer | Checkpoint | Operation |
|----------|-----------|-----------|
| `backend/nn/jepa_trainer.py` | `jepa_brain.pt` | Write after training epoch |
| `backend/nn/coach_manager.py` | `jepa_brain.pt`, `coach_brain.pt` | Load for inference |
| `backend/nn/training_orchestrator.py` | All | Load/save with `StaleCheckpointError` handling |
| `backend/nn/experimental/rap_coach/trainer.py` | `rap_coach.pt` | Write after RAP training |
| `backend/nn/win_probability_trainer.py` | `win_prob.pt` | Write after win-prob training |

## Development Notes

- **Do NOT commit `.pt` files** to the repository — they are large binary artifacts
- The `global/` directory must exist in the repo (preserved by `README.txt`)
- Training logs are written by `backend/nn/training_monitor.py` (JSON format), not stored here
- The `MODELS_DIR` path is resolved from `core/config.py` and defaults to this directory
- When `BRAIN_DATA_ROOT` is set, models are written to `{BRAIN_DATA_ROOT}/models/` instead
- Always use `save_nn()` / `load_nn()` from `persistence.py` — never call `torch.save()` directly
- After changing model architecture, delete stale checkpoints and retrain from scratch
