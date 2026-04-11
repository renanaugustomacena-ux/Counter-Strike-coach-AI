> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Neural Network Subsystem — Model Architectures & Training Infrastructure

> **Authority:** `Programma_CS2_RENAN/backend/nn/`
> **Depends on:** `backend/processing/feature_engineering/` (25-dim feature vector), `backend/storage/` (SQLite WAL), `core/config.py` (settings)
> **Consumed by:** `backend/services/` (coaching service), `backend/coaching/` (hybrid engine), `apps/qt_app/` (UI)

## Introduction

This package is the machine learning core of the CS2 coaching system. It contains six distinct neural network architectures, a unified training orchestrator with plugin-based callback instrumentation, and a real-time inference engine (GhostEngine). Every model consumes the canonical 25-dimensional feature vector produced by `FeatureExtractor` in `backend/processing/feature_engineering/vectorizer.py`. All randomness is seeded via `GLOBAL_SEED = 42` for deterministic, reproducible training runs.

The training pipeline was validated end-to-end on March 12, 2026: 11 pro demos ingested (17.3M tick rows, 6.4 GB database), JEPA dry-run completed producing `jepa_brain.pt` (3.6 MB).

## File Inventory

| File | Purpose |
|------|---------|
| `config.py` | Central constants (`INPUT_DIM=25`, `OUTPUT_DIM=10`, `HIDDEN_DIM=128`, `GLOBAL_SEED=42`, `RAP_POSITION_SCALE=500.0`), `set_global_seed()`, `get_device()` with discrete GPU selection |
| `model.py` | `AdvancedCoachNN` (LSTM + Mixture of Experts), `CoachNNConfig` dataclass, `ModelManager` for versioned checkpoint saving |
| `jepa_model.py` | `JEPAEncoder`, `JEPACoachingModel`, `VLJEPACoachingModel` -- self-supervised JEPA with InfoNCE contrastive loss and concept dictionary |
| `jepa_train.py` | JEPA two-stage training script (pre-training + fine-tuning), `_MIN_ROUNDS_FOR_SEQUENCE = 6` |
| `jepa_trainer.py` | Low-level JEPA training loop with EMA target encoder update |
| `ema.py` | `EMA` class -- exponential moving average for shadow weight management (invariant NN-16: `.clone()` on `apply_shadow()`) |
| `role_head.py` | `NeuralRoleHead` (5-dim input, 5-dim softmax output, ~750 params), training and inference helpers for player role classification |
| `win_probability_trainer.py` | `WinProbabilityTrainerNN` -- lightweight 9-feature model for offline win probability on pro match DataFrames |
| `dataset.py` | `ProPerformanceDataset` (supervised) and `SelfSupervisedDataset` (JEPA sliding-window context/target pairs) |
| `factory.py` | `ModelFactory` -- static factory for unified instantiation across all model types (`default`, `jepa`, `vl-jepa`, `rap`, `rap-lite`, `role_head`) |
| `persistence.py` | `save_nn()`, `load_nn()`, `get_model_path()` with atomic write (`tmp + os.replace`), `StaleCheckpointError` |
| `early_stopping.py` | `EarlyStopping` with configurable patience and min-delta thresholds |
| `training_config.py` | `TrainingConfig` and `JEPATrainingConfig` dataclasses centralizing all hyperparameters |
| `training_orchestrator.py` | `TrainingOrchestrator` -- unified epoch loop with validation, early stopping, checkpointing, LR scheduling, and callback dispatch |
| `training_controller.py` | `TrainingController` -- demo deduplication, diversity checks, monthly quota management, stop-start logic |
| `coach_manager.py` | `CoachTrainingManager` -- high-level orchestration with 3-stage maturity gate (doubt / learning / conviction) |
| `train.py` | `train_nn()` -- legacy training entry point for `AdvancedCoachNN` |
| `training_callbacks.py` | `TrainingCallback` (ABC, opt-in hooks) and `CallbackRegistry` (event dispatcher with error isolation) |
| `tensorboard_callback.py` | `TensorBoardCallback` -- logs 9+ scalar signals, parameter/gradient histograms, custom scalar layouts |
| `maturity_observatory.py` | `MaturityObservatory` -- 5-signal conviction index (belief entropy, gate specialization, concept focus, value accuracy, role stability), 5-state machine (doubt / crisis / learning / conviction / mature) |
| `embedding_projector.py` | `EmbeddingProjector` -- UMAP 2D projections and TensorBoard embedding export for belief/concept space visualization |
| `training_monitor.py` | `TrainingMonitor` -- JSON-persisted epoch metrics with atomic write for real-time progress tracking |
| `evaluate.py` | `evaluate_adjustments()` -- SHAP-compatible evaluation of model weight adjustments per feature |
| `data_quality.py` | `DataQualityReport` -- pre-training data quality checks (NaN rate, zero-position rate, class balance) |

## Sub-packages

| Package | Purpose |
|---------|---------|
| `rap_coach/` | RAP Coach model: 7-layer pedagogical architecture (Perception, Memory, Strategy, Pedagogy, Communication, ChronovisorScanner, SkillModel). Requires `ncps` + `hflayers` for LTC-Hopfield memory. |
| `advanced/` | **Intentional empty stub.** Original modules removed in remediation G-06. Namespace reserved for future experiments. See `advanced/README.md`. |
| `inference/` | `GhostEngine` -- real-time prediction engine translating tick-level game state into coaching suggestions via `RAP_POSITION_SCALE`. |
| `layers/` | `SuperpositionLayer` -- context-gated linear layer enabling dynamic mode blending with L1 sparsity regularization and observability hooks. |
| `experimental/` | Experimental RAP Coach variant with separate Perception, Strategy, Pedagogy, Communication, Memory modules and test harness. |

## Model Architectures

### 1. JEPA (`jepa_model.py`) -- Primary Training Path

Self-supervised Joint-Embedding Predictive Architecture. Two-stage protocol: (1) pre-training on pro demos with InfoNCE contrastive loss + concept dictionary for semantic alignment, (2) LSTM fine-tuning on user data. Uses EMA target encoder (`requires_grad=False` during update, invariant NN-JM-04). Latent dim: 256, LSTM hidden dim: 128.

### 2. RAP Coach (`rap_coach/`) -- Grand Vision Architecture

7-layer pedagogical model: ResNet-based Perception, LTC-Hopfield Memory (512 associative slots, `ncp_units=512`, `belief_dim=64`), SuperpositionLayer Strategy with context gating, Causal Pedagogy for mistake attribution, Natural Language Communication, ChronovisorScanner for multi-scale temporal analysis, and SkillModel for player skill estimation. Hopfield is bypassed until 2+ training forward passes (invariant NN-MEM-01).

### 3. AdvancedCoachNN (`model.py`) -- Legacy Supervised Model

LSTM sequence encoder + Mixture of Experts (3 experts by default) with LayerNorm, role-biased gating, and `tanh` output clamping. Aliased as `TeacherRefinementNN` for backward compatibility.

### 4. NeuralRoleHead (`role_head.py`) -- Role Classification

Lightweight MLP (5 -> 32 -> 16 -> 5, ~750 parameters) predicting player role probabilities from playstyle metrics (TAPD, OAP, PODT, rating impact, aggression). KL-divergence loss with label smoothing. Runs as secondary opinion alongside heuristic `RoleClassifier`.

### 5. WinProbabilityTrainerNN (`win_probability_trainer.py`) -- Offline Win Prediction

9-feature model (alive, health, armor, equipment, bomb state) for offline training on pro match DataFrames. Separate from the real-time `WinProbabilityNN` in `backend/analysis/` (12 features, 64/32 hidden dims). Checkpoints are NOT interchangeable.

### 6. VL-JEPA (`jepa_model.py`) -- Vision-Language Extension

Extends JEPA with visual-linguistic tactical understanding for concept-level coaching explanations.

## Key Constants

| Constant | Value | Defined in |
|----------|-------|------------|
| `INPUT_DIM` / `METADATA_DIM` | 25 | `config.py`, `vectorizer.py` |
| `OUTPUT_DIM` | 10 | `config.py` |
| `HIDDEN_DIM` | 128 | `config.py` |
| `GLOBAL_SEED` | 42 | `config.py` |
| `BATCH_SIZE` | 32 | `config.py` |
| `LEARNING_RATE` | 0.001 | `config.py` |
| `RAP_POSITION_SCALE` | 500.0 | `config.py` |
| `WEIGHT_CLAMP` | 0.5 | `config.py` |
| RAP `hidden_dim` | 256 | `rap_coach/model.py` |
| RAP `ncp_units` | 512 | `rap_coach/memory.py` |
| RAP `belief_dim` | 64 | `rap_coach/memory.py` |
| JEPA `latent_dim` | 256 | `jepa_model.py` |
| JEPA LSTM `hidden_dim` | 128 | `jepa_model.py` |

## Coach Introspection Observatory

The training pipeline includes a 4-layer observability stack, implemented as `TrainingCallback` plugins:

1. **Layer 1 -- CallbackRegistry** (`training_callbacks.py`): Plugin architecture with error isolation. Callbacks never crash training.
2. **Layer 2 -- TensorBoardCallback** (`tensorboard_callback.py`): Scalars (loss, LR, sparsity, gate dynamics), histograms (params, grads, beliefs, concepts), custom dashboard layouts.
3. **Layer 3 -- MaturityObservatory** (`maturity_observatory.py`): 5-signal conviction index with EMA smoothing and a 5-state classification machine (doubt / crisis / learning / conviction / mature).
4. **Layer 4 -- EmbeddingProjector** (`embedding_projector.py`): UMAP 2D projections of belief vectors and concept embeddings, exported to TensorBoard.

## Critical Invariants

| ID | Rule |
|----|------|
| P-RSB-03 | `round_won` EXCLUDED from training features (label leakage) |
| NN-MEM-01 | Hopfield bypassed until 2+ training forward passes |
| NN-16 | EMA `apply_shadow()` must `.clone()` shadow tensors |
| NN-JM-04 | Target encoder `requires_grad=False` during EMA update |
| P-X-01 | `len(FEATURE_NAMES) == METADATA_DIM` compile-time assertion |
| P-VEC-02 | NaN/Inf in features triggers ERROR log + clamp |
| P3-A | >5% NaN/Inf in batch raises `DataQualityError` |

## Development Notes

- **Reproducibility:** Always call `set_global_seed(42)` before training runs.
- **Device selection:** `get_device()` auto-selects discrete GPU by VRAM; override via `CUDA_DEVICE` setting.
- **Feature alignment:** Any change to the 25-dim vector must update `FEATURE_NAMES`, `METADATA_DIM`, `extract()` docstring, and all model `input_dim` assertions simultaneously.
- **Optional dependencies:** RAP Coach requires `ncps` and `hflayers`. Imports are guarded with `try/except`; check `_RAP_DEPS_AVAILABLE` before instantiation.
- **Atomic writes:** All checkpoint saves and JSON persistence use `tmp + os.replace()` to prevent corruption on crash.
- **Tick decimation is STRICTLY FORBIDDEN** -- all tick-level data must be preserved as ingested.

## Usage

```python
from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
from Programma_CS2_RENAN.backend.nn.config import set_global_seed

set_global_seed(42)
model = ModelFactory.get_model("jepa")

from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
orchestrator = TrainingOrchestrator(manager, model_type="jepa", max_epochs=50)
```
