# Models — Neural Network Checkpoint Storage

> **Authority:** Rule 4 (Data Persistence)

This directory stores trained neural network checkpoints (`.pt` files) used by the Ghost Engine for inference and by the coaching pipeline for ML-augmented advice.

## Directory Structure

```
models/
└── global/                   # Shared baseline models (not user-specific)
    └── README.txt           # Placeholder (empty in repository)
```

## Checkpoint Types

| Checkpoint | Model | Created By | Size |
|-----------|-------|-----------|------|
| `jepa_brain.pt` | JEPACoachingModel | `backend/nn/jepa_trainer.py` | ~3.6 MB |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/experimental/rap_coach/trainer.py` | Variable |
| `coach_brain.pt` | AdvancedCoachNN (legacy) | `backend/nn/train.py` | ~1 MB |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` | ~100 KB |
| `role_head.pt` | NeuralRoleHead | Role classification training | ~50 KB |

## Storage Hierarchy

```
models/
├── global/              # Shared baseline (from pro demo training)
│   ├── jepa_brain.pt   # JEPA pre-trained on pro matches
│   └── ...
└── {user_id}/           # Per-user fine-tuned models (future)
    └── global/
        └── ...
```

The `persistence.py` module (`backend/nn/persistence.py`) manages checkpoint I/O:
- **Atomic writes:** Uses temp files to prevent corruption on crash
- **Multi-fallback loading:** User model → Global model → Bundled factory model
- **Dimension validation:** Raises `StaleCheckpointError` if architecture changed

## Critical Warning

- `WinProbabilityNN` (production, 12 features) and `WinProbabilityTrainerNN` (offline, 9 features) use **different architectures**. Never cross-load their checkpoints.
- After architecture changes (e.g., modifying METADATA_DIM), old checkpoints become invalid. The system detects this via strict dimension checking.

## In Production

The PyInstaller bundle includes `models/global/` as bundled data:
```python
# In cs2_analyzer_win.spec
datas += [('models/global', 'models/global')]
```

## Development Notes

- **Do NOT commit `.pt` files** to the repository — they are large binary artifacts
- The `global/` directory must exist (use `.gitkeep` or `README.txt`)
- Checkpoints are versioned implicitly by their architecture — stale detection is automatic
- Training logs go to `backend/nn/training_monitor.py` (JSON format), not this directory
- EMA shadow weights are stored inside the checkpoint dict, not as separate files
