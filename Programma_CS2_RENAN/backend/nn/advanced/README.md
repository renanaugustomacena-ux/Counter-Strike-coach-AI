> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Advanced — Intentional Empty Stub

> **Authority:** `Programma_CS2_RENAN/backend/nn/advanced/`
> **Status:** Empty package. All modules removed in remediation G-06.

## What Happened

This package originally contained three experimental modules:

| Removed File | Original Purpose |
|--------------|------------------|
| `superposition_net.py` | Experimental SuperpositionLayer wrapper with brain-mode blending |
| `brain_bridge.py` | Orchestration bridge between standard and advanced coaching paths |
| `feature_engineering.py` | Duplicate feature extraction logic (shadow copy of the canonical vectorizer) |

During the G-06 remediation phase, a dead-code audit revealed that **all three modules had zero callers** across the entire codebase. Their functionality had already been absorbed into canonical locations through prior refactoring work, making these files unreachable dead code. They were removed to reduce maintenance burden and eliminate confusion about which implementation was authoritative.

## Where the Functionality Lives Now

The surviving functionality migrated to its canonical locations before G-06:

- **SuperpositionLayer** -- `backend/nn/layers/superposition.py`. The canonical context-gated linear layer with L1 sparsity regularization, gate observability hooks (`get_gate_statistics()`, `get_gate_activations()`), and tracing controls. Used by the RAP Coach Strategy layer.
- **BrainBridge orchestration** -- Absorbed into `backend/nn/rap_coach/model.py` (`RAPCoachModel`). The model itself handles the coordination between perception, memory, strategy, pedagogy, and communication layers.
- **Feature engineering** -- `backend/processing/feature_engineering/vectorizer.py` (`FeatureExtractor`). This is the single source of truth for the 25-dimensional feature vector (`METADATA_DIM = 25`). There must never be a second implementation.

## Why the Namespace is Preserved

The `advanced/` directory is kept as a valid Python package (with `__init__.py`) for three reasons:

1. **Import safety.** Existing code or third-party tools that scan the `nn/` package tree will not break on a missing sub-package.
2. **Namespace reservation.** Future advanced or experimental architectures that graduate beyond the `experimental/` sandbox may be placed here.
3. **Audit trail.** The `__init__.py` comment documents what was removed and why, preserving institutional memory.

## Package Contents

| File | Purpose |
|------|---------|
| `__init__.py` | Package stub with G-06 removal history comment (5 lines) |
| `README.md` | This file |
| `README_IT.md` | Italian translation |
| `README_PT.md` | Portuguese translation |

## G-06 Remediation Context

The G-06 remediation was a codebase-wide dead-code cleanup that targeted modules with zero import references. The audit was performed by scanning all Python files for `from ... advanced` and `import ... advanced` patterns. The three files in this package were the only modules in the entire `nn/` tree that had no callers whatsoever. Their removal was a deliberate decision to enforce the "single source of truth" principle: every concept in the system should have exactly one authoritative implementation.

The key risk that G-06 addressed was **shadow implementations** -- duplicate code that silently drifts out of sync with the canonical version. The `feature_engineering.py` file in this package was a particularly dangerous example: it contained a copy of the feature extraction logic that could have been accidentally imported instead of the canonical `vectorizer.py`, producing subtly different feature vectors and corrupting model training.

## Development Notes

- **Do not add modules here without justification.** New experimental work should go in `backend/nn/experimental/` first and only graduate to `advanced/` after proving stability.
- **The canonical SuperpositionLayer is in `layers/superposition.py`.** Do not recreate it here.
- **The canonical FeatureExtractor is in `processing/feature_engineering/vectorizer.py`.** Do not duplicate feature extraction logic anywhere in `nn/`.
- **If you add a module here**, update this README, the `__init__.py` comment, and the parent `nn/README.md` sub-packages table.
