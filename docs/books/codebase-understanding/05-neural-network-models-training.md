# Chapter 5: Neural Network Models and Training

This chapter provides an exhaustive reference to every class, function, constant, and design mechanism found in the `Programma_CS2_RENAN/backend/nn/` package and the root-level training entry point `run_full_training_cycle.py`. The neural network subsystem implements the AI coaching brain of the CS2 Analyzer: it learns from professional and user demo data, predicts optimal player behavior, classifies tactical roles, and provides real-time ghost-position inference.

---

## Table of Contents

1. [Package Layout](#1-package-layout)
2. [Configuration (`config.py`)](#2-configuration-configpy)
3. [Core Model (`model.py`)](#3-core-model-modelpy)
4. [Model Factory (`factory.py`)](#4-model-factory-factorypy)
5. [Datasets (`dataset.py`)](#5-datasets-datasetpy)
6. [Data Quality (`data_quality.py`)](#6-data-quality-data_qualitypy)
7. [Exponential Moving Average (`ema.py`)](#7-exponential-moving-average-emapy)
8. [Early Stopping (`early_stopping.py`)](#8-early-stopping-early_stoppingpy)
9. [Embedding Projector (`embedding_projector.py`)](#9-embedding-projector-embedding_projectorpy)
10. [Evaluation (`evaluate.py`)](#10-evaluation-evaluatepy)
11. [Persistence (`persistence.py`)](#11-persistence-persistencepy)
12. [Role Head (`role_head.py`)](#12-role-head-role_headpy)
13. [TensorBoard Callback (`tensorboard_callback.py`)](#13-tensorboard-callback-tensorboard_callbackpy)
14. [Layers (`layers/`)](#14-layers)
15. [Advanced (`advanced/`)](#15-advanced)
16. [Training Loop (`train.py`)](#16-training-loop-trainpy)
17. [Training Configuration (`training_config.py`)](#17-training-configuration-training_configpy)
18. [Training Callbacks (`training_callbacks.py`)](#18-training-callbacks-training_callbackspy)
19. [Training Controller (`training_controller.py`)](#19-training-controller-training_controllerpy)
20. [Training Monitor (`training_monitor.py`)](#20-training-monitor-training_monitorpy)
21. [Training Orchestrator (`training_orchestrator.py`)](#21-training-orchestrator-training_orchestratorpy)
22. [Maturity Observatory (`maturity_observatory.py`)](#22-maturity-observatory-maturity_observatorypy)
23. [Win Probability Trainer (`win_probability_trainer.py`)](#23-win-probability-trainer-win_probability_trainerpy)
24. [Coach Manager (`coach_manager.py`)](#24-coach-manager-coach_managerpy)
25. [JEPA Model (`jepa_model.py`)](#25-jepa-model-jepa_modelpy)
26. [JEPA Training Pipeline (`jepa_train.py`)](#26-jepa-training-pipeline-jepa_trainpy)
27. [JEPA Trainer (`jepa_trainer.py`)](#27-jepa-trainer-jepa_trainerpy)
28. [Inference / Ghost Engine (`inference/ghost_engine.py`)](#28-inference--ghost-engine)
29. [Root Training Entry Point (`run_full_training_cycle.py`)](#29-root-training-entry-point-run_full_training_cyclepy)
30. [Cross-Cutting Design Decisions](#30-cross-cutting-design-decisions)

---

## 1. Package Layout

```
backend/nn/
  __init__.py              # Empty (1 line)
  config.py                # Seeds, device, hyperparameters
  model.py                 # AdvancedCoachNN (MoE LSTM), ModelManager
  factory.py               # ModelFactory (registry of model types)
  dataset.py               # ProPerformanceDataset, SelfSupervisedDataset
  data_quality.py          # Pre-training quality checks
  ema.py                   # EMA shadow weights
  early_stopping.py        # EarlyStopping + EmbeddingCollapseDetector
  embedding_projector.py   # UMAP/TensorBoard embedding visualization
  evaluate.py              # SHAP-based evaluation
  persistence.py           # save_nn / load_nn with sidecar validation
  role_head.py             # NeuralRoleHead (5->5 classifier)
  tensorboard_callback.py  # TensorBoard training callback
  train.py                 # Supervised + JEPA training entry
  training_config.py       # TrainingConfig / JEPATrainingConfig dataclasses
  training_callbacks.py    # TrainingCallback ABC + CallbackRegistry
  training_controller.py   # Demo diversity gating
  training_monitor.py      # JSON-persisted progress monitor
  training_orchestrator.py # Unified epoch-loop orchestrator
  maturity_observatory.py  # 5-state maturity classifier
  win_probability_trainer.py # Win probability model
  coach_manager.py         # CoachTrainingManager (full cycle coordinator)
  jepa_model.py            # JEPACoachingModel, VLJEPACoachingModel
  jepa_train.py            # Standalone JEPA pretrain/finetune pipeline
  jepa_trainer.py          # JEPATrainer (AMP, drift, concept alignment)
  layers/
    __init__.py            # Empty
    superposition.py       # FiLM-conditioned SuperpositionLayer
  advanced/
    __init__.py            # Stub (dead code removed per G-06)
  inference/
    __init__.py            # Empty
    ghost_engine.py        # GhostEngine real-time inference

run_full_training_cycle.py # CLI entry point for training
```

---

## 2. Configuration (`config.py`)

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `GLOBAL_SEED` | `42` | Universal reproducibility seed |
| `BATCH_SIZE` | `32` | Default DataLoader batch size |
| `INPUT_DIM` | `METADATA_DIM` (25) | Canonical feature vector dimensionality, imported from `feature_engineering` |
| `OUTPUT_DIM` | `10` | Strategy layer output dimensionality (first 10 core features) |
| `HIDDEN_DIM` | `128` | Hidden layer size for AdvancedCoachNN / TeacherRefinementNN |
| `LEARNING_RATE` | `0.001` | Default learning rate |
| `EPOCHS` | `50` | Default epoch count |
| `WEIGHT_CLAMP` | `0.5` | Maximum adjustment factor for evaluation |
| `RAP_POSITION_SCALE` | `500.0` | Scale factor converting normalized model outputs [-1,1] to CS2 world-unit displacements. Must be consistent between GhostEngine and overlay code (F3-05) |
| `_INTEGRATED_GPU_KEYWORDS` | Tuple of 6 strings | GPU name substrings used to identify and deprioritize integrated GPUs |

### Module-Level State

- `_device_logged: bool` -- one-shot flag to prevent repeated device log messages.
- `_cached_device: Optional[torch.device]` -- cached result of `get_device()`.

### Functions

#### `set_global_seed(seed: int = GLOBAL_SEED)`

Sets all random seeds for reproducibility (AR-6, P1-02, DET-02):
- `random.seed(seed)`
- `np.random.seed(seed)`
- `torch.manual_seed(seed)`
- `torch.cuda.manual_seed_all(seed)`
- `torch.backends.cudnn.deterministic = True`
- `torch.backends.cudnn.benchmark = False`
- Calls `torch.use_deterministic_algorithms(True, warn_only=True)` unless `CS2_NONDETERMINISTIC=1` is set in the environment. Degrades gracefully on older PyTorch versions.

#### `seeded_generator(seed: int = GLOBAL_SEED) -> torch.Generator`

Returns a `torch.Generator` seeded from `seed`. Designed for `DataLoader(..., generator=seeded_generator())` to ensure worker-level RNG reproducibility (DET-01).

#### `_select_best_cuda_device() -> torch.device`

Enumerates CUDA devices. On multi-GPU systems, selects the device with the most total memory, penalizing integrated GPUs (score = 0 if name matches any integrated keyword).

#### `get_device() -> torch.device`

Detects the best available hardware with caching. Priority:
1. User override via `CUDA_DEVICE` setting (`"auto"`, `"cpu"`, `"cuda:0"`, etc.)
2. Discrete NVIDIA GPU (via `_select_best_cuda_device()`)
3. CPU fallback (emits a `StateManager` notification via WR-09)

#### `get_throttling_delay() -> float`

Returns the sleep delay (seconds) between training batches based on `ML_INTENSITY` setting:
- `"High"` -> `0.0`
- `"Medium"` -> `0.05`
- `"Low"` -> `0.2`

#### `get_intensity_batch_size() -> int`

Adjusts batch size based on `ML_INTENSITY` setting:
- `"High"` -> `128`
- `"Medium"` -> `32`
- `"Low"` -> `8`

---

## 3. Core Model (`model.py`)

### `CoachNNConfig` (dataclass)

Configuration dataclass for `AdvancedCoachNN`:

| Field | Default | Description |
|-------|---------|-------------|
| `input_dim` | `METADATA_DIM` (25) | Input feature dimensionality |
| `output_dim` | `OUTPUT_DIM` (10) | Coaching output dimensionality |
| `hidden_dim` | `128` | LSTM hidden size |
| `num_experts` | `3` | Number of MoE experts |
| `num_lstm_layers` | `2` | LSTM depth |
| `dropout` | `0.2` | Dropout rate |
| `use_layer_norm` | `True` | Whether to apply LayerNorm after LSTM |

### `AdvancedCoachNN(nn.Module)`

The primary supervised coaching neural network. Architecture:
1. Multi-layer LSTM for sequence learning
2. LayerNorm for gradient stability
3. Mixture of Experts (MoE) with top-K sparse gating (GAP-10)
4. SHAP-compatible forward pass

**Constructor** `__init__(input_dim, output_dim, hidden_dim, num_experts, config)`:
- Supports both legacy positional args and new `CoachNNConfig`-based initialization.
- Stores architecture config attributes (`input_dim`, `output_dim`, `hidden_dim`, `num_experts`, `num_lstm_layers`) for checkpoint serialization (P1-12).
- Creates an `nn.LSTM` with `batch_first=True`.
- Creates `nn.LayerNorm(hidden_dim)` or `nn.Identity()` based on `use_layer_norm`.
- Creates `nn.ModuleList` of `num_experts` expert networks via `_create_expert()`.
- Creates `nn.Linear(hidden_dim, num_experts)` gate that emits raw logits (GAP-10 / MOE-02). Previous dense softmax caused expert collapse. State dict key changed from `gate.0.weight` to `gate.weight`.
- Sets `gate_top_k = min(2, num_experts)`.

**`_create_expert(h_dim, o_dim)`**: Returns `nn.Sequential(Linear, LayerNorm, ReLU, Linear)`.

**`forward(x, role_id=None)`**:
1. Validates input dimensionality via `_validate_input_dim()`.
2. Passes through LSTM, takes last hidden state.
3. Applies LayerNorm.
4. Computes top-K sparse gate weights via `_topk_sparse_gate()`.
5. Optionally applies role bias via `_apply_role_bias()`.
6. Computes final output via `_compute_nn_output()`.

**`_validate_input_dim(x)`**: Raises `ValueError` if `x.dim() < 2`. Unsqueezes 2D input to 3D `[batch, 1, features]`.

**`_apply_role_bias(gate_weights, role_id)`**: Adds a one-hot bias vector scaled by 0.5 to gate weights for the specified expert. Clamps `role_id` to `[0, num_experts-1]` with a warning.

### Free Functions

#### `_topk_sparse_gate(logits: Tensor, k: int) -> Tensor`

GAP-10 implementation: converts dense gate logits `[B, E]` into a top-K sparse weight vector. Only the top-K positions are populated (softmax-normalized among those K logits), rest are zero. When `k = num_experts`, collapses to the legacy dense softmax.

#### `_compute_nn_output(experts, last_hidden, gate_weights)`

Stacks expert outputs `[B, E, output_dim]`, multiplies by gate weights (broadcasted), sums across experts, and applies `tanh` activation.

### Aliases

- `TeacherRefinementNN = AdvancedCoachNN` -- NN-L-01 deprecated alias.

### `ModelManager`

MLOps versioning. Constructor accepts optional `model_dir` (defaults to `MODELS_DIR/nn/versions`).

**`save_version(model, metrics: dict)`**: Saves model state dict with a timestamped name `brain_YYYYMMDD_HHMMSS.pt` plus a JSON metadata sidecar containing version, timestamp, metrics, and architecture config (P1-12).

### Optional Imports

- Attempts to import `RAPCoachModel` and `RAPCommunication` from `.experimental.rap_coach`. Sets `RAP_COACH_AVAILABLE = True/False`.
- Notes that `JEPACoachingModel` is importable from `jepa_model.py`.

---

## 4. Model Factory (`factory.py`)

### `_require_int(kwargs, key, default) -> int`

Coerces `kwargs[key]` to `int`, defaulting when absent or `None`. Prevents silent propagation of `None/str` into model constructor dimension args.

### `ModelFactory`

Static factory with type constants:

| Constant | Value | Model |
|----------|-------|-------|
| `TYPE_LEGACY` | `"default"` | `AdvancedCoachNN` (alias `TeacherRefinementNN`) |
| `TYPE_JEPA` | `"jepa"` | `JEPACoachingModel` |
| `TYPE_VL_JEPA` | `"vl-jepa"` | `VLJEPACoachingModel` |
| `TYPE_RAP` | `"rap"` | `RAPCoachModel` |
| `TYPE_RAP_LITE` | `"rap-lite"` | `RAPCoachModel(use_lite_memory=True)` |
| `TYPE_ROLE_HEAD` | `"role_head"` | `NeuralRoleHead` |

**`get_model(model_type, **kwargs) -> nn.Module`**: Instantiates the correct model class using `_require_int()` for dimension parameters. Each type uses lazy imports to avoid circular dependencies.

**`get_checkpoint_name(model_type) -> str`**: Returns the canonical checkpoint filename:
- `"jepa"` -> `"jepa_brain"`
- `"vl-jepa"` -> `"vl_jepa_brain"`
- `"rap"` -> `"rap_coach"`
- `"rap-lite"` -> `"rap_lite_coach"`
- `"role_head"` -> `"role_head"`
- `"default"` -> `"latest"`

---

## 5. Datasets (`dataset.py`)

### `ProPerformanceDataset(Dataset)`

Standard PyTorch dataset for supervised training.

**`__init__(X, y)`**: Converts inputs to float32 tensors. Handles both `torch.Tensor` and numpy/list inputs. Uses `.clone().detach().requires_grad_(False)` to avoid double wrapping.

**`__len__`**: Returns `len(self.X)`.

**`__getitem__(idx)`**: Returns `(self.X[idx], self.y[idx])`.

### `SelfSupervisedDataset(Dataset)`

Sliding-window dataset for JEPA self-supervised learning.

**`__init__(X, context_len=10, prediction_len=5)`**: Stores context and prediction window lengths. Computes `num_samples = len(X) - context_len - prediction_len`. Raises `ValueError` if data is too short.

**`__len__`**: Returns `max(0, self.num_samples)` (F3-34 guard against edge-case negatives).

**`__getitem__(idx)`**: Returns `(context, target)` where:
- `context = X[idx : idx + context_len]`
- `target = X[idx + context_len : idx + context_len + prediction_len]`

---

## 6. Data Quality (`data_quality.py`)

### `DataQualityReport` (dataclass)

Pre-training data quality summary:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `total_tick_rows` | `int` | `0` | Total PlayerTickState rows |
| `train_rows` | `int` | `0` | Rows in TRAIN split |
| `val_rows` | `int` | `0` | Rows in VAL split |
| `test_rows` | `int` | `0` | Rows in TEST split |
| `zero_position_rate` | `float` | `0.0` | Fraction of ticks with (0,0,0) position |
| `nan_rate` | `float` | `0.0` | Fraction of ticks with NaN |
| `round_outcome_distribution` | `Dict[str,int]` | `{}` | Class balance |
| `complete_matches` | `int` | `0` | Matches marked complete |
| `incomplete_matches` | `int` | `0` | Matches not complete |
| `issues` | `List[str]` | `[]` | Issues found |
| `passed` | `bool` | `True` | Overall verdict |

**`summary() -> str`**: Returns a multi-line string report.

### `run_pre_training_quality_check(min_samples=1000, max_zero_position_rate=0.10) -> DataQualityReport`

Performs five checks:
1. Total tick row count from `PlayerTickState`.
2. Counts by `DatasetSplit` (TRAIN/VAL/TEST) from `PlayerMatchStats`.
3. Zero-position rate (samples up to 10K ticks for efficiency).
4. Match completeness via `MatchDataManager`.
5. Verdict: fails if `total_tick_rows < min_samples`, `zero_position_rate > threshold`, or `train_rows == 0`.

---

## 7. Exponential Moving Average (`ema.py`)

### `EMA`

Maintains exponential moving average of model parameters for more stable behavior.

**`__init__(model, decay=0.999)`**: Stores model reference and decay rate. Calls `_register()` to clone initial parameter data into `self.shadow`.

**`_register()`**: Stores cloned `param.data` for all parameters with `requires_grad=True`.

**`update()`**: For each trainable parameter: `shadow = decay * shadow + (1 - decay) * param.data`. Creates shadow entries for newly added parameters.

**`apply_shadow()`**: Backs up current params to `self.backup`, then copies shadow weights into model params. NN-16 critical invariant: clones shadows before assignment to avoid shared reference.

**`restore()`**: Restores training weights from backup. Clones before assigning.

**`state_dict()`**: Returns cloned shadow tensors (F3-30 prevents external corruption).

**`load_state_dict(state_dict)`**: Loads shadow weights from checkpoint, cloning each tensor.

---

## 8. Early Stopping (`early_stopping.py`)

### `EmbeddingCollapseError(RuntimeError)`

Custom exception raised when JEPA encoder collapses to a degenerate representation.

### `EmbeddingCollapseDetector`

Hard-stop guard for the P9-02 embedding collapse failure mode. Modernization report Section 9 requirement: abort training after two consecutive validation epochs of collapse.

**`__init__(threshold=0.01, patience=2)`**: Sets threshold and patience. Initializes `consecutive_collapsed=0` and `last_variance=NaN`.

**`update(epoch_mean_variance: float)`**: Increments collapse counter if variance is below threshold, NaN, or negative. Resets on healthy epoch. Raises `EmbeddingCollapseError` when counter reaches patience. Error message includes diagnostic suggestions: (a) InfoNCE temperature, (b) EMA momentum, (c) data diversity, (d) VICReg term.

**`reset()`**: Resets counter and last_variance.

### `EarlyStopping`

Standard validation-loss-based early stopping.

**`__init__(patience=10, min_delta=1e-4)`**: Sets patience, min_delta, and initializes counter/best_loss/should_stop.

**`__call__(val_loss) -> bool`**: Returns `True` if training should stop. Tracks best loss with minimum improvement threshold.

**`reset()`**: Resets all state.

---

## 9. Embedding Projector (`embedding_projector.py`)

Layer 4 of the Coach Introspection Observatory.

### Constants

- `_CONCEPT_NAMES`: List of 16 coaching concept names (e.g., `"pos_aggressive"`, `"util_effective"`, `"aggression_calibrated"`).
- `_UMAP_AVAILABLE`: Boolean, True if `umap` importable.
- `_MPL_AVAILABLE`: Boolean, True if `matplotlib` importable.

### `EmbeddingProjector(TrainingCallback)`

Captures and projects high-dimensional embeddings at periodic intervals.

**`__init__(tb_writer=None, interval=5)`**: Stores TensorBoard writer and projection interval. Logs UMAP availability.

**`on_epoch_end(epoch, train_loss, val_loss, model, **kwargs)`**: At every `interval` epochs, calls `_project_belief_vectors()` and `_project_concept_embeddings()`.

**`_project_belief_vectors(model, epoch)`**: Reads `model._last_belief_batch`, exports to TensorBoard Embedding Projector, generates UMAP 2D projection image (requires >= 5 samples).

**`_project_concept_embeddings(model, epoch)`**: Reads `model.concept_embeddings.weight`, exports with metadata labels, generates UMAP concept map.

**`_generate_umap_figure(embeddings, title, tag, epoch, labels=None)`**: Creates UMAP 2D scatter plot, logs as TensorBoard figure. Uses `random_state=42`, adaptive `n_neighbors`.

**`_generate_concept_umap(embeddings, labels, epoch)`**: Creates labeled UMAP projection of concept prototypes.

---

## 10. Evaluation (`evaluate.py`)

### `evaluate_adjustments(model, X_sample, role_id=None) -> dict`

Evaluates model adjustments with SHAP explanations.

1. Prepares input tensor, ensures 2D.
2. Runs inference with `role_id` for MoE gating.
3. If `shap` is available, uses `KernelExplainer` with sample mean baseline (NN-EV-01 fix: avoids zero-vector bias).
4. Builds adjustment dict: `{feature_name}_weight = adj[i] * WEIGHT_CLAMP` for each of the 25 `MATCH_AGGREGATE_FEATURES`.
5. Attaches `explanations` key with SHAP values.

---

## 11. Persistence (`persistence.py`)

### Constants

- `BASE_NN_DIR`: `Path(MODELS_DIR)` -- base directory for model checkpoints.
- `_META_SCHEMA_VERSION`: `"v1"` -- sidecar schema version (GAP-07).

### `StaleCheckpointError(RuntimeError)`

Raised when a checkpoint has incompatible dimensions or feature schema. Must be handled explicitly.

### Path Resolution Functions

**`get_model_path(version, user_id=None) -> Path`**: Returns `BASE_NN_DIR / {user_id or "global"} / {version}.pt`.

**`get_factory_model_path(version, user_id=None) -> Path`**: Returns the path to the read-only model bundled with the executable (via `get_resource_path()`).

### Checkpoint Integrity (CTF-1)

**`_hash_registry_path() -> Path`**: Returns `BASE_NN_DIR / "checkpoint_hashes.json"`.

**`_compute_file_hash(path) -> str`**: SHA-256 hash of file contents (64KB chunks).

**`_register_checkpoint_hash(path)`**: Stores hash in registry JSON after saving.

**`_verify_checkpoint_hash(path) -> bool`**: Verifies checkpoint against registry. Returns `True` if valid or unregistered. Logs error on mismatch.

### Sidecar Metadata (GAP-07)

**`_sidecar_path(checkpoint_path) -> Path`**: Returns `.pt.meta.json` sibling path.

**`_build_current_meta() -> dict`**: Snapshots current `METADATA_DIM`, `FEATURE_NAMES`, and `heuristic_config` at save time. Lazy imports to avoid circular dependencies.

**`_validate_loaded_meta(meta, checkpoint_path)`**: Validates schema_version, metadata_dim, and feature_names against current code. Raises `StaleCheckpointError` on any drift. Heuristic config is presence-checked only.

### `save_nn(model, version, user_id=None, extra_meta=None)`

Saves model checkpoint with atomic write:
1. Writes state dict to `.pt.tmp`.
2. Builds sidecar metadata (feature schema + heuristic config + optional extra_meta).
3. Writes sidecar to `.json.tmp`.
4. Atomically promotes both files via `replace()`.
5. Registers checkpoint hash (CTF-1).
6. Cleans up temp files on failure.

### `load_nn(version, model, user_id=None)`

Loads model checkpoint with 4-location fallback:
1. User-specific local path.
2. Global local path.
3. User-specific factory-bundled path.
4. Global factory-bundled path.

Before loading:
- Verifies checkpoint hash integrity (CTF-1).
- Validates sidecar metadata (GAP-07). Missing sidecar on legacy checkpoints issues a warning.
- Uses `strict=True` for `load_state_dict()`.
- Catches `RuntimeError` on architecture mismatch and raises `StaleCheckpointError`.
- NN-14: Raises `FileNotFoundError` if no checkpoint found at any location (never silently returns random weights).

---

## 12. Role Head (`role_head.py`)

Neural Role Classification Head (Proposal 10).

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `ROLE_OUTPUT_ORDER` | `[LURKER, ENTRY, SUPPORT, AWPER, IGL]` | Index-to-role mapping. `role_anchor` merged into SUPPORT |
| `FLEX_CONFIDENCE_THRESHOLD` | `0.35` | Below this, classify as FLEX |
| `MIN_TRAINING_SAMPLES` | `20` | Minimum samples to train |
| `LABEL_SMOOTHING_EPS` | `0.02` | Epsilon to avoid `log(0)` in KL-divergence |

### `NeuralRoleHead(nn.Module)`

Architecture: `Linear(5,32) -> LayerNorm -> ReLU -> Linear(32,16) -> ReLU -> Linear(16,5)` (~750 parameters).

Class constants: `ROLE_INPUT_DIM = 5`, `ROLE_OUTPUT_DIM = 5`.

**`forward(x)`**: Returns `softmax(net(x), dim=-1)`.

**`forward_log_softmax(x)`**: Returns `log_softmax(net(x), dim=-1)` for KL-divergence training.

### Data Preparation

**`prepare_role_training_data() -> Optional[Tuple[Tensor, Tensor, Dict]]`**:
- Loads `Ext_PlayerPlaystyle` records from DB.
- Returns `None` if fewer than `MIN_TRAINING_SAMPLES`.
- Features: `[tapd, oap, podt, rating_impact, aggression_score]`.
- Labels: `[role_lurker, role_entry, role_support+role_anchor, role_awper, role_igl]`.
- Applies label smoothing: `y = y * (1 - eps) + eps/K`, then re-normalizes rows.
- Computes normalization stats (mean, std).

### Training

**`train_role_head(max_epochs=200, patience=15, lr=1e-3) -> Optional[NeuralRoleHead]`**:
- Normalizes features by mean/std.
- 80/20 train/val split with seeded permutation (F3-32).
- Uses `AdamW(lr, weight_decay=1e-4)` and `KLDivLoss(reduction="batchmean")`.
- Manual early stopping with patience tracking.
- Saves model via `save_nn("role_head")` and normalization stats to `role_head_norm.json`.

### Loading

**`load_role_head() -> Optional[Tuple[NeuralRoleHead, Dict]]`**: Loads model and normalization stats. Returns `None` if either is unavailable.

### Inference Helpers

**`extract_role_features_from_stats(player_stats: Dict) -> Optional[Tensor]`**: Converts player stats dict to 5-dim feature vector: `[tapd, oap, podt, rating_impact, aggression]`. Returns `None` if `rounds_played <= 0`.

---

## 13. TensorBoard Callback (`tensorboard_callback.py`)

Layer 2 of the Coach Introspection Observatory.

### `TensorBoardCallback(TrainingCallback)`

Logs training signals to TensorBoard. Becomes a no-op if `tensorboard` is not installed.

**`__init__(log_dir=None, model_type="")`**: Defaults `log_dir` to `RUNS_DIR/coach_training`. Creates `SummaryWriter`.

**Lifecycle Hooks**:

- **`on_train_start(model, config)`**: Stores model type, creates custom scalar layout.
- **`on_epoch_start(epoch)`**: Records epoch number.
- **`on_batch_end(batch_idx, loss, outputs)`**: Logs per-batch scalars:
  - `loss/batch`
  - RAP: `rap/sparsity_ratio`, `rap/z_axis_error`, `rap/loss_position`
  - Gates: `gates/mean_activation`, `gates/sparsity`, `gates/active_ratio`
  - JEPA: `jepa/infonce_loss`, `jepa/concept_loss`, `jepa/diversity_loss`
- **`on_epoch_end(epoch, train_loss, val_loss, model, **kwargs)`**: Logs epoch scalars (`loss/train`, `loss/val`, `loss/gap`), learning rate per param group, and histograms (parameters, gradients, beliefs, gates, concepts).
- **`on_train_end(model, final_metrics)`**: Logs final metrics.
- **`close()`**: Closes writer.

**Histogram Helpers**: `_log_parameter_histograms`, `_log_belief_histogram`, `_log_gate_histograms`, `_log_concept_histograms`.

**`_create_custom_layout()`**: Defines organized TensorBoard dashboard with sections: "Coach Vital Signs", "RAP Coach Internals", "JEPA Self-Supervised", "Superposition Gates".

---

## 14. Layers

### `layers/__init__.py`

Empty file.

### `layers/superposition.py`

#### `SuperpositionLayer(nn.Module)`

FiLM-conditioned Superposition Layer (Perez et al., AAAI 2018). Applies Feature-wise Linear Modulation:

```
y = gamma(context) * (W*x + b) + beta(context)
```

RAP-AUDIT-06: Previous multiplicative-only gating (`y = gate * out`) could only suppress features, never inject new ones. The additive `beta` term allows context-driven feature injection. Beta weights initialized to zero for backward compatibility.

**`__init__(in_features, out_features, context_dim=METADATA_DIM)`**:
- Weight initialized with Kaiming uniform (P1-09).
- Bias initialized to zeros.
- `context_gate`: `nn.Linear(context_dim, out_features)` -- gamma (multiplicative).
- `context_beta`: `nn.Linear(context_dim, out_features)` -- beta (additive), initialized to zero weights and bias.
- Observable state: `_last_gate_activations`, `_last_gate_live`, forward counter, log interval.

**`forward(x, context)`**:
1. `gamma = sigmoid(context_gate(context))`.
2. `beta = context_beta(context)`.
3. Stores live gate tensor for sparsity loss (NN-24 fix: retains grad).
4. Stores detached copy for observability.
5. Periodic gate statistics logging during training.
6. Returns `gamma * F.linear(x, weight, bias) + beta`.

**`get_gate_activations()`**: Returns last gate activations tensor.

**`get_gate_statistics() -> Dict[str, float]`**: Returns dict with `mean_activation`, `std_activation`, `sparsity`, `active_ratio`, `top_3_dims`, `bottom_3_dims`.

**`gate_sparsity_loss() -> Tensor`**: L1 regularization on live gate activations.

**`enable_tracing(interval=1)`** / **`disable_tracing()`**: Controls verbose logging interval.

---

## 15. Advanced

### `advanced/__init__.py`

Legacy experimental modules removed (G-06): `superposition_net.py`, `brain_bridge.py`, `feature_engineering.py` were dead code. Canonical `SuperpositionLayer` lives in `layers/superposition.py`.

---

## 16. Training Loop (`train.py`)

### Constants

- `MIN_TRAINING_SAMPLES = 20` -- P1-04 / AR-6 minimum for train/val split.

### `train_nn(X, y, X_val=None, y_val=None, model=None, config_name="default", context=None)`

ML-Audited Training Entry Point:
1. Calls `set_global_seed()` (P1-02).
2. Gets device via `get_device()`.
3. If `config_name == "jepa"`, delegates to `_train_jepa_self_supervised()`.
4. Otherwise, runs supervised training:
   - Prepares splits via `_prepare_splits()`.
   - Creates `ProPerformanceDataset` for train/val.
   - Creates `DataLoader` with intensity-adjusted batch size.
   - Uses `ModelFactory.get_model()` if no model provided.
   - Optimizer: `AdamW(lr=LEARNING_RATE, weight_decay=1e-2)`.
   - Loss: `MSELoss`.
   - Runs `_execute_validated_loop()`.
   - Returns model on CPU.

### `_train_jepa_self_supervised(X, device, context=None)`

Stage 1 JEPA Pre-training:
1. Creates `SelfSupervisedDataset(X, context_len=10, prediction_len=5)`.
2. Gets model via `ModelFactory.get_model(TYPE_JEPA)`.
3. Optimizer: `AdamW(lr=1e-4, weight_decay=1e-2)`.
4. Runs 5 epochs (prototype) with contrastive loss.
5. NN-61: Vectorized negative sampling via `torch.randperm`.
6. Gradient clipping at `max_norm=1.0` (P1-06).
7. EMA target encoder update after each batch.
8. Early stopping on training loss (P1-01).

### `_prepare_splits(X, y, X_val, y_val)`

If validation data not provided:
- Returns `None` tuple if `len(X) < MIN_TRAINING_SAMPLES` (P1-04).
- Uses `train_test_split(test_size=0.2, random_state=42)`.

### `_execute_validated_loop(model, train_loader, val_loader, optimizer, loss_fn, device, context=None)`

Standard epoch loop with:
- Throttling delay between batches.
- Early stopping (patience=10, min_delta=1e-4) on validation loss (P1-01).
- Periodic logging every 10 epochs.

### `_run_training_epoch(model, loader, optimizer, loss_fn, delay, device, context=None)`

Per-batch: forward, loss, backward, gradient clipping (max_norm=1.0, P1-06), optimizer step, optional sleep delay.

### `_run_validation_pass(model, loader, loss_fn, device)`

No-grad validation pass, returns total loss.

### `run_training()`

Standalone entry: uses `CoachTrainingManager` to fetch pro data, prepare tensors, train, and save as `"latest"`.

---

## 17. Training Configuration (`training_config.py`)

### `TrainingConfig` (dataclass)

| Field | Default | Description |
|-------|---------|-------------|
| `base_lr` | `1e-4` | Base learning rate |
| `warmup_steps` | `1000` | Warmup step count |
| `lr_schedule` | `"cosine"` | Schedule type (`"cosine"`, `"linear"`, `"constant"`) |
| `min_lr` | `1e-6` | Minimum LR for scheduler |
| `max_epochs` | `100` | Maximum epoch count |
| `batch_size` | `1` | Batch size (RAP processes 1 match at a time) |
| `gradient_clip` | `1.0` | Max gradient norm |
| `val_every_n_steps` | `50` | Validation frequency |
| `val_batch_size` | `1` | Validation batch size |
| `patience` | `10` | Early stopping patience |
| `min_delta` | `1e-4` | Minimum improvement threshold |
| `ema_decay` | `0.999` | EMA decay rate |
| `use_ema` | `True` | Whether to use EMA |
| `save_every_n_epochs` | `5` | Checkpoint frequency |
| `keep_n_checkpoints` | `3` | Maximum checkpoints to retain |
| `checkpoint_dir` | `"models/checkpoints"` | Checkpoint directory |
| `log_every_n_steps` | `10` | Logging frequency |
| `progress_file` | `"training_progress.json"` | Progress file path |
| `device` | `"auto"` | Device selection |

### `JEPATrainingConfig(TrainingConfig)` (dataclass)

Additional JEPA-specific fields:

| Field | Default | Description |
|-------|---------|-------------|
| `latent_dim` | `256` | Latent space dimensionality |
| `context_window` | `10` | Context window size |
| `prediction_window` | `10` | Prediction window size |
| `contrastive_temperature` | `0.07` | InfoNCE temperature |
| `momentum_target` | `0.996` | EMA decay for target encoder |
| `pretraining_epochs` | `50` | Pre-training epoch count |
| `finetuning_epochs` | `50` | Fine-tuning epoch count |

### `DEFAULT_CONFIG = TrainingConfig()`

---

## 18. Training Callbacks (`training_callbacks.py`)

Layer 1 of the Coach Introspection Observatory.

### `TrainingCallback(ABC)`

Abstract base class for training instrumentation. All methods are no-ops by default (F3-31: opt-in pattern, no `@abstractmethod`).

**Hooks**:
- `on_train_start(model, config: Dict)`: Before first epoch.
- `on_epoch_start(epoch: int)`: Beginning of each epoch.
- `on_batch_end(batch_idx: int, loss: float, outputs: Dict)`: After each batch.
- `on_epoch_end(epoch, train_loss, val_loss, model, **kwargs)`: End of epoch.
- `on_validation_end(epoch, val_loss, model)`: After validation pass.
- `on_train_end(model, final_metrics: Dict)`: After training completes.
- `close()`: Release resources.

### `CallbackRegistry`

Manages a collection of `TrainingCallback` instances.

**`__init__(callbacks=None)`**: Stores list of callbacks.

**`add(callback)`**: Adds callback, preventing duplicates (NN-L-13).

**`fire(event, **kwargs)`**: Dispatches event to all callbacks. Catches and logs exceptions from individual callbacks -- they never crash training.

**`close_all()`**: Calls `close()` on all registered callbacks.

---

## 19. Training Controller (`training_controller.py`)

### `TrainingDecision` (dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `should_train` | `bool` | -- | Whether to proceed |
| `reason` | `str` | -- | Human-readable reason |
| `diversity_score` | `float` | `0.0` | Diversity metric |

### `TrainingController`

Controls when the Coach trains. Manages demo deduplication, diversity checks, and monthly quotas.

**`__init__()`**: Gets DB manager. Reads `MAX_DEMOS_PER_MONTH` from settings (default: 10, NN-M-13).

Class constant: `MIN_DIVERSITY_SCORE = 0.3`.

**`should_train_on_demo(demo_path, match_stats) -> TrainingDecision`**:
1. Checks monthly limit via `_get_monthly_training_count()`.
2. Calculates diversity via `_calculate_diversity_score()`.
3. Returns decision with reason.

**`_get_monthly_training_count() -> int`**: Counts `PlayerMatchStats` with `processed_at >= 30_days_ago`.

**`_calculate_diversity_score(new_stats) -> float`**: Computes `1 - avg_cosine_similarity` against last 5 matches. Returns 1.0 for first match.

**`_extract_features(stats) -> np.ndarray`**: Extracts 6-dim feature vector with approximate z-scaling: kills, deaths, ADR, HS, utility blind time, opening duel win pct.

**`_cosine_similarity(a, b) -> float`**: Standard cosine similarity with zero-norm guard.

**`get_training_controller() -> TrainingController`**: Factory function.

---

## 20. Training Monitor (`training_monitor.py`)

### `_coerce_json_safe(value) -> Any`

Replaces `NaN`/`Inf` with `None` for valid RFC 8259 JSON (fix #27).

### `TrainingMonitor`

Logs and persists training metrics to JSON.

**`__init__(log_file="training_progress.json")`**: Initializes metrics dict with `started_at`, empty arrays for epochs/losses/LRs, `best_val_loss`, `early_stopped`. Loads existing progress if file exists.

**`log_epoch(epoch, train_loss, val_loss=None, lr=None)`**: Appends metrics and saves.

**`mark_early_stop()`**: Sets `early_stopped=True` and `stopped_at`.

**`mark_complete()`**: Sets `completed_at`.

**`_save()`**: Atomic write via `tempfile.mkstemp()` + `os.replace()` (NN-L-12). Coerces non-finite values and sets `allow_nan=False`.

**`get_summary() -> str`**: Returns human-readable status with epoch count, best val loss, and training status.

---

## 21. Training Orchestrator (`training_orchestrator.py`)

The unified orchestrator managing the entire training lifecycle.

### `_flush_all_loggers()`

Force-flushes all logging handlers to prevent silent loss on process kill.

### `TrainingOrchestrator`

Supports model types: `"jepa"`, `"vl-jepa"`, `"rap"`.

#### Constructor

```python
def __init__(self, manager, model_type="jepa", max_epochs=100,
             patience=10, batch_size=32, callbacks=None,
             accumulation_steps=4, train_samples=None,
             val_samples=None, dry_run=False):
```

Key initialization:
- `_DEFAULT_TRAIN_SAMPLES = 50_000`, `_DEFAULT_VAL_SAMPLES = 10_000`.
- `dry_run` flag (B4): suppresses all `save_nn` calls, ensuring non-destructive pipeline probes.
- `_neg_rng`: Deterministic numpy RNG for JEPA negative sampling (F3-02, seeded at 42).
- `_neg_pool`: Cross-match negative pool for contrastive learning (NN-H-03, max 500).
- `_total_samples` / `_total_fallbacks`: Aggregate zero-tensor fallback counters (F3-11).
- `_ltc_curriculum_epochs = 5`: LTC curriculum learning warmup.
- Sets `TrainerClass` and `model_name` based on `model_type`.
- RAP model requires `USE_RAP_MODEL=True` setting.

#### Core Methods

**`_warn_no_gpu()`**: Logs warning and adds StateManager notification when no GPU detected.

**`_load_or_init_model()`**: Creates model via `ModelFactory`, attempts checkpoint load with `load_nn()`. Handles `FileNotFoundError`, `StaleCheckpointError`, and generic exceptions. Restores `best_val_loss` from sidecar (B3.2).

**`_restore_best_val_from_sidecar()`**: Reads `extra.best_val_loss` from checkpoint sidecar JSON. Without this, resume always overwrites prior checkpoint on first epoch.

**`run_training(context=None)`**: Full training pipeline:
1. Pre-flight data quality check (`run_pre_training_quality_check()`).
2. Model load/init.
3. Trainer construction with appropriate kwargs.
4. Data availability verification (B1 preflight probe).
5. Minimum sample validation (100 samples required).
6. Fires `on_train_start` callback.
7. Sets total steps for EMA schedule if trainer supports it.
8. Runs `_run_epoch_loop()`.
9. Calls `_finalize_training()`.

**`_run_epoch_loop(trainer, model, val_data, context)`**: B1: Train data re-fetched each epoch with `seed = GLOBAL_SEED + epoch` for data rotation. Val data stays fixed. Per epoch:
1. Fires `on_epoch_start`.
2. Fetches fresh train data.
3. Runs train epoch and val epoch.
4. Steps LR scheduler.
5. Reports progress.
6. Fires `on_epoch_end`.
7. Best-model checkpointing (suppressed in dry-run mode).
8. Latest-model checkpointing (suppressed in dry-run mode).
9. Early stopping check.

**`_finalize_training(model, final_epoch)`**: Post-loop validation of zero-tensor fallback rate (P3-C: abort if > 30%, warn if > 10%). Fires `on_train_end` callback.

#### Data Fetching

**`_fetch_batches(is_train, epoch=0)`**: Fetches data and creates batches. JEPA uses `_fetch_jepa_ticks()` with per-epoch seed rotation (B1). RAP uses `_fetch_rap_windows()`.

#### Tensor Batch Preparation

**`_prepare_tensor_batch(raw_items)`**: Converts DB objects to tensor dictionaries using `FeatureExtractor.extract_batch()`.

For JEPA/VL-JEPA:
- Requires `context_len + 1 = 11` minimum ticks (J-5 + V-1 fix).
- Context: first 10 ticks, unsqueezed to `(1, 10, METADATA_DIM)`.
- Target: tick immediately after context (V-1 fix: correct next-step prediction).
- Negatives from cross-match pool (NN-H-03), falling back to in-batch sampling during warmup.
- For VL-JEPA: fetches `RoundStats` for outcome-based concept labels (G-01).

For RAP (delegated to `_prepare_rap_batch()`):
- Builds per-tick view/map/motion tensors.
- Computes advantage function (LEAK-01 guard: masks samples without POV data).
- Classifies tactical roles (10 classes).
- Segments into temporal windows of `RAP_SEQ_LEN=32` (with curriculum learning).

**RAP Batch Preparation Phases** (split into helper methods):

1. **`_rap_collect_per_tick()`**: Phase 1 -- resolves match DB, builds PlayerKnowledge, generates per-tick view/map/motion tensors, computes value+mask (LEAK-01), classifies tactical role.
2. **`_rap_compute_target_pos()`**: Phase 2 -- per-tick next-position deltas (RAP-AUDIT-02).
3. **`_rap_compute_timespans()`**: Phase 2b -- inter-tick timespans for LTC ODE solver (RAP-AUDIT-05).
4. **`_rap_segment_windows()`**: Phase 3 -- segments per-tick lists into windows, drops sparse-POV ones (T-2 fix: requires >= 50% POV density).

**`_rap_prefetch_caches(raw_items, match_mgr, caches)`**: Bulk pre-fetches match data for entire window: 2 queries instead of 288 per batch.

#### Training Step Dispatch

**`_train_step_dispatch(trainer, tensor_batch, do_step)`**: Routes to correct model-type path (JEPA, VL-JEPA, or RAP). Returns `(loss, result_dict)`.

**`_eval_step_dispatch(trainer, tensor_batch)`**: No-grad validation step dispatch.

**`_eval_step_jepa(trainer, tensor_batch)`**: JEPA validation with contrastive loss.

**`_eval_step_rap(trainer, tensor_batch)`**: RAP validation with value estimate loss and optional val_mask.

#### Training Target Computation

Advantage function weights: `_ADV_W_ALIVE=0.4`, `_ADV_W_HP=0.2`, `_ADV_W_EQUIP=0.2`, `_ADV_W_BOMB=0.2`.

**`_compute_advantage(all_players_at_tick, player_team, bomb_planted) -> float`**: Continuous advantage value [0,1] from game state: `0.4*alive_diff + 0.2*hp_ratio + 0.2*equip_ratio + 0.2*bomb_factor`. Replaces binary win/lose (G-04).

**`_classify_tactical_role(item, knowledge, all_players) -> int`**: Returns 0-9 index for tactical roles: site_take, rotation, entry_frag, support, anchor, lurk, retake, save, aggressive_push, passive_hold.

Tactical role thresholds: `_SAVE_EQUIP_THRESHOLD=1500`, `_LURK_DISTANCE_THRESHOLD=1500.0`, `_ENTRY_DISTANCE_THRESHOLD=800.0`, `_SUPPORT_DISTANCE_THRESHOLD=500.0`.

**`_curriculum_seq_len() -> int`**: Phase 5A: Ramps RAP window length during early epochs (8 -> 32 over 5 epochs).

---

## 22. Maturity Observatory (`maturity_observatory.py`)

Layer 3 of the Coach Introspection Observatory. Translates raw neural signals into human-interpretable maturity states.

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DOUBT_THRESHOLD` | `0.3` | Conviction below this = doubt |
| `LEARNING_UPPER` | `0.6` | Upper bound for learning state |
| `CONVICTION_THRESHOLD` | `0.6` | Conviction above this = conviction (if stable) |
| `CONVICTION_STABILITY` | `0.05` | Std over 10 epochs for stability |
| `MATURE_THRESHOLD` | `0.75` | Conviction above this = mature (with conditions) |
| `MATURE_EPOCHS` | `20` | Required stable epochs for mature state |
| `CRISIS_DROP_PCT` | `0.20` | 20% drop from rolling max = crisis |
| `CONCEPT_TEMP_LOWER_BOUND` | `0.01` | Concept temperature clamp lower |
| `CONCEPT_TEMP_UPPER_BOUND` | `1.0` | Concept temperature clamp upper |
| `CONCEPT_TEMP_SATURATION_FRACTION` | `0.05` | 5% of range = "near boundary" |
| `CONCEPT_TEMP_SATURATION_PATIENCE` | `10` | Consecutive saturated epochs before alarm |

### `MaturitySnapshot` (dataclass)

Point-in-time maturity assessment with fields: `epoch`, `timestamp`, individual signals (`belief_entropy`, `gate_specialization`, `concept_focus`, `value_accuracy`, `role_stability`), composite scores (`conviction_index`, `maturity_score`), `state`, concept temperature monitoring fields.

### `MaturityObservatory(TrainingCallback)`

Conviction index component weights: `belief_entropy=0.25`, `gate_specialization=0.25`, `concept_focus=0.20`, `value_accuracy=0.20`, `role_stability=0.10`. EMA smoothing alpha: `0.3`.

**Signal Extraction**:

1. **`_compute_belief_entropy(belief)`**: Shannon entropy of belief vector, normalized to [0,1]. Uses softmax over batch-averaged belief vector.

2. **`_compute_gate_specialization(model)`**: `1 - mean_gate_activation` from `model.strategy.superposition.get_gate_statistics()`.

3. **`_compute_concept_focus(model)`**: `1 - normalized_entropy` of concept embedding norms.

4. **`_compute_value_accuracy(val_loss)`**: Normalized improvement from initial val loss.

5. **`_compute_role_stability()`**: `1 - std*5` of conviction index over last 10 epochs.

**`_update_concept_temperature_saturation(snap, model)`**: PRE-6 hygiene. Tracks concept_temperature proximity to clamp boundaries. After 10 consecutive saturated epochs, logs an error alarm (one-shot latch). Re-arms on healthy epoch.

**State Machine** (`_classify_state()`):

Five states:
- **DOUBT**: conviction < 0.3, no improvement trend.
- **CRISIS**: conviction drops > 20% from rolling max within 5 epochs.
- **LEARNING**: conviction 0.3-0.6 with increasing trend.
- **CONVICTION**: conviction > 0.6 and std < 0.05 over 10 epochs.
- **MATURE**: conviction > 0.75, stable for 20+ epochs, value_accuracy > 0.7, gate_specialization > 0.5.

**Public API**: `current_state`, `current_conviction`, `get_timeline()`.

---

## 23. Win Probability Trainer (`win_probability_trainer.py`)

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `WIN_PROB_EPOCHS` | `100` | Training epochs |
| `WIN_PROB_MIN_SAMPLES` | `20` | AR-6 minimum |
| `WIN_PROB_TRAINER_INPUT_DIM` | `9` | Input features |

### `WinProbabilityTrainerNN(nn.Module)`

Lightweight win probability model for offline training. Architecture: `Linear(9,32) -> ReLU -> Linear(32,16) -> ReLU -> Linear(16,1) -> Sigmoid`.

NOTE: This is separate from `WinProbabilityNN` in `backend/analysis/win_probability.py` (12 features, 64/32 hidden dims). Do NOT cross-load checkpoints.

### `train_win_prob_model(data_df, model_path) -> Optional[model]`

Trains on match snapshots with:
- Features: `ct_alive, t_alive, ct_health, t_health, ct_armor, t_armor, ct_eqp, t_eqp, bomb_planted`.
- `BCELoss` with `Adam(lr=0.001)`.
- 80/20 train/val split (`random_state=42`).
- Early stopping (patience=10, min_delta=1e-4).
- Saves state dict to `model_path`.

### `predict_win_prob(model, state_dict) -> float`

Predicts CT win probability from a state dictionary.

---

## 24. Coach Manager (`coach_manager.py`)

### Constants

**`_MATCH_STATS_DEMO_SUFFIX_RE`**: Regex `r"\.dem_.*$"` to strip legacy demo_name suffix (WR-76).

**`TRAINING_FEATURES`**: 25-element list of tick-level feature names aligned with `FeatureExtractor` (METADATA_DIM=25). Includes core vitals, movement/stance, awareness, position, view angles, spatial/contextual, and tactical features. Runtime assertion ensures length matches `METADATA_DIM`.

**`MATCH_AGGREGATE_FEATURES`**: 25-element list of match-aggregate feature names from `PlayerMatchStats` columns. Includes core performance, variance/ratios, accuracy/economy, duel/clutch, utility/playstyle, HLTV 2.0 components, utility breakdown, and kill enrichment. Runtime assertion ensures length matches `METADATA_DIM`.

**`TARGET_INDICES`**: `list(range(OUTPUT_DIM))` -- first 10 core features targeted by NN adjustments.

**Maturity Tiers** (Task 2.11.1 Soft Gate):

| Tier | Demo Range | Confidence |
|------|------------|------------|
| `CALIBRATING` | 0-49 | 0.5 (50%) |
| `LEARNING` | 50-199 | 0.8 (80%) |
| `MATURE` | 200+ | 1.0 (100%) |

### `CoachTrainingManager`

Orchestrates the "Global wisdom + Local Adaptation" training cycle.

**`__init__()`**: Gets DB manager, creates `ProDataPipeline`, stores feature/target names.

**`check_prerequisites() -> tuple[bool, str]`**: Enforces the 10/10 Rule and Account Connection:
- >= 10 pro demos: Ready.
- < 10 pro demos: Checks if user has Steam+FACEIT connected and sufficient user demos.
- Updates `StateManager` status at each stage.

**`increment_maturity_counter()`**: Increments `CoachState.total_matches_processed` in the knowledge DB.

**`check_maturity_gate() -> tuple[bool, int]`**: Returns `(is_mature, current_count)` with `MATURITY_THRESHOLD=50`.

**`get_maturity_tier() -> str`**: Returns `"CALIBRATING"`, `"LEARNING"`, or `"MATURE"`.

**`get_confidence_multiplier() -> float`**: Returns 0.5, 0.8, or 1.0 based on tier.

**`run_full_cycle(context=None)`**: Main entry point:
1. Checks prerequisites.
2. Initializes database.
3. Assigns dataset splits.
4. Executes training phases.

**`assign_dataset_splits()`**: Chronological 70/15/15 split. Splits pro and user matches independently. Uses `match_date` as sort column. Re-assigns ALL matches each cycle.

**`_build_callbacks() -> CallbackRegistry`**: Builds TensorBoard callback for Console-driven training.

**`_execute_training_phases(context=None)`**: Five phases:
1. **Phase 1**: JEPA Cognitive Pre-training via `run_jepa_pretraining()`.
2. **Phase 2**: Professional Baseline via `_train_phase(is_pro=True)`.
3. **Phase 3**: User Playstyle Tailoring via `_train_phase(is_pro=False, base_model=global_m)`.
4. **Phase 4**: RAP Behavioral Optimization via `run_rap_cycle()`.
5. **Phase 5**: Role Classification Head via `_train_role_head()`.

**`run_jepa_pretraining(context, callbacks)`**: Creates `TrainingOrchestrator(model_type="jepa")` and runs training.

**`run_rap_cycle(context, callbacks)`**: Creates `TrainingOrchestrator(model_type="rap")` and runs training.

**`_train_role_head(context)`**: Calls `train_role_head()` from `role_head.py`.

**`_fetch_jepa_ticks(is_pro, split, seed=42, sample_size=5000)`**: B1 mechanism for JEPA tick fetching with seeded subsampling:
- Only uses demos with `match_complete=True` (P4-A).
- Strips WR-76 legacy suffix.
- Fetches all matching tick IDs (lightweight), then subsamples in Python with seeded RNG.
- Chunked SQLite fetches (_CHUNK=500).

**`_fetch_rap_windows(is_pro, split, window_size=96, max_demos=None)`**: Fetches windowed tick data for RAP:
- Only completed matches.
- Loads ticks grouped by match.
- Segments into non-overlapping contiguous windows.
- V-5 fix: Skips demos shorter than `window_size`.
- Per-demo tick cap: 10,000.

**`_get_completed_demo_names() -> Optional[set]`**: P4-A filter for completed demos via `MatchDataManager`.

**`_train_phase(is_pro, base_model=None, context=None)`**: Fetches training/validation data, prepares tensors, calls `train_nn()`.

**`_prepare_tensors(raw_data) -> (X_t, y_t)`**: Builds 25-dim vectors from `MATCH_AGGREGATE_FEATURES`, computes deltas against pro baseline.

**`_calculate_deltas(vec, pro_vec)`**: Z-score normalized deltas with feature-specific scale factors, clipped to [-1, 1].

**`_get_pro_baseline_vector()`**: Builds baseline from `get_pro_baseline()` with hardcoded fallback defaults for all 25 features.

**`get_skill_radar_data() -> dict`**: Generates skill delta comparison for UI radar visualization (6 skill categories: ADR, Impact, KAST, Accuracy, Rating, Economy).

**`get_interactive_overlay_data(match_id) -> dict`**: Generates tick-by-tick advantage and ghost position data for 2D viewer using RAP model inference.

### Legacy Helper Functions

- `_fetch_rap_ticks(db)`: Fetches ticks for current player.
- `_train_on_windows(trainer, windows, reconstructor, device)`: Processes RAP windows.
- `_process_single_rap_window(trainer, w, recon, device)`: Single window processing.
- `_apply_dynamic_window_targets(batch, window_ticks)`: Sets target_val and target_strat (F3-28: implicit label smoothing).
- `_calculate_pro_mean(pro_raw, feature_names)`: Averages feature vectors.
- `_extract_feature_vector(p, feature_names)`: Extracts feature dict values.

---

## 25. JEPA Model (`jepa_model.py`)

Joint-Embedding Predictive Architecture for CS2 coaching. ADDITIVE feature that coexists with `AdvancedCoachNN`.

### `JEPAEncoder(nn.Module)`

Vision Transformer-style encoder:
```
Linear(input_dim, 512) -> LayerNorm(512) -> GELU -> Dropout(0.1) ->
Linear(512, latent_dim) -> LayerNorm(latent_dim)
```

**`forward(x)`**: Encodes `[batch, seq_len, input_dim]` -> `[batch, seq_len, latent_dim]`.

### `JEPAPredictor(nn.Module)`

Predicts target embeddings from context embeddings:
```
Linear(latent_dim, latent_dim*2) -> LayerNorm(latent_dim*2) -> GELU ->
Dropout(0.1) -> Linear(latent_dim*2, latent_dim)
```

**`forward(context_embedding)`**: `[batch, latent_dim]` -> `[batch, latent_dim]`.

### `JEPACoachingModel(nn.Module)`

Hybrid JEPA-LSTM model. Training pipeline: Pre-train JEPA (self-supervised) -> Freeze encoders -> Fine-tune LSTM (supervised).

**Constructor** `__init__(input_dim, output_dim, latent_dim=256, hidden_dim=128, num_experts=3)`:
- `context_encoder`: JEPAEncoder
- `target_encoder`: JEPAEncoder (EMA-updated, never gradient-trained)
- `predictor`: JEPAPredictor
- `lstm`: LSTM(latent_dim, hidden_dim, num_layers=2, dropout=0.15) -- Supplement_N260 Section P2-4
- `experts`: ModuleList of 3 expert networks
- `gate`: Linear(hidden_dim, num_experts) -- J-3 raw logits for top-2 sparse routing
- `log_temperature`: Learned InfoNCE temperature (Phase 2B, initialized to `log(0.07)`)
- `moco_queue`: MoCo v3 momentum contrast queue, size 4096 (Phase 2A)
- `moco_queue_ptr`: Queue pointer buffer
- `_moe_aux_loss`: Switch Transformer auxiliary loss (Phase 3A)
- `_expert_counts`: Expert utilization tracking

**`forward(x, role_id=None)`**: Delegates to `forward_coaching()`.

**`forward_jepa_pretrain(x_context, x_target)`**: JEPA pre-training forward pass:
1. Context encoding via `context_encoder`.
2. Target encoding via `target_encoder` (with `torch.no_grad()`, P1-07).
3. Average pooling over sequence.
4. Prediction via `predictor`.
5. Returns `(s_target_pred, s_target_pooled)`.

**`enqueue(embeddings)`**: MoCo FIFO queue enqueue (Phase 2A). L2-normalizes and wraps around queue.

**`_sparse_moe(last_hidden, role_id=None)`**: Top-2 sparse MoE routing with load-balancing auxiliary loss (J-3 + Phase 3A). Computes Switch Transformer-style aux loss: `0.01 * num_experts * sum(f_i * P_i)`.

**`forward_coaching(x, role_id=None)`**: Full coaching inference:
1. Context encoder (frozen or unfrozen based on `is_pretrained`).
2. LSTM processing, take last hidden.
3. Sparse MoE routing.
4. WR-52: `sigmoid` output for [0,1] targets (not `tanh`).

**`forward_selective(x, prev_embedding=None, threshold=0.05, role_id=None)`**: VL-JEPA selective decoding optimization. Computes cosine distance between current and previous embedding. Only decodes if distance exceeds threshold. Returns `(prediction_or_None, current_embedding, did_decode)`.

**`_apply_role_bias(gate_logits, role_id)`**: Adds `+2.0` logit bias to specified expert.

**`freeze_encoders()`**: Sets `requires_grad=False` on both encoders, sets `is_pretrained=True`.

**`unfreeze_encoders()`**: Reverses `freeze_encoders()`.

**`update_target_encoder(momentum=0.996)`**: EMA update for target encoder (I-JEPA/BYOL style). NN-JM-04: Raises `RuntimeError` if target encoder has `requires_grad=True`. Formula: `target = momentum * target + (1 - momentum) * context`.

### `jepa_contrastive_loss(pred, target, negatives, temperature=0.07)`

InfoNCE contrastive loss. L2-normalizes all inputs. Computes positive and negative cosine similarities scaled by temperature. Returns cross-entropy loss.

### `vicreg_regularization(embeddings, lambda_var=25.0, lambda_cov=1.0)`

Phase 2E: VICReg variance + covariance regularization (Bardes et al. 2022). Prevents embedding collapse (low variance) and dimension correlation.

### Coaching Concepts

**`NUM_COACHING_CONCEPTS = 16`**

**`CoachingConcept`** (frozen dataclass): `id`, `name`, `dimension`, `description`.

**`COACHING_CONCEPTS`**: 16 concepts across 5 dimensions:
- Positioning (0-2): aggressive, passive, exposed
- Utility (3-4): effective, wasteful
- Decision (5-6, 11-12): economy efficient/wasteful, rotation fast, information gathered
- Engagement (7-10): favorable, unfavorable, trade responsive, trade isolated
- Psychology (13-15): momentum leveraged, clutch composed, aggression calibrated

**`CONCEPT_NAMES`**: List of concept name strings.

### `ConceptLabeler`

Generates soft coaching concept labels for VL-JEPA training.

Feature index constants: `_HP=0`, `_ARMOR=1`, `_HELMET=2`, `_EQUIP=4`, `_CROUCHING=5`, `_SCOPED=6`, `_BLINDED=7`, `_ENEMIES_VIS=8`, `_KAST=16`, `_ROUND_PHASE=18`, `_WEAPON_CLASS=19`, `_TIME_IN_ROUND=20`, `_BOMB_PLANTED=21`, `_TEAMMATES_ALIVE=22`, `_ENEMIES_ALIVE=23`, `_TEAM_ECONOMY=24`.

**`label_tick(features)`**: NN-JM-03 WARNING: label leakage risk. Derives labels from input features (heuristic). Delegates to four static helper methods:
- `_tick_positioning(labels, hp, crouching, scoped, enemies_vis, bomb_planted)`
- `_tick_utility_economy(labels, equip, blinded, enemies_vis, kast, round_phase, team_econ)`
- `_tick_engagement(labels, hp, armor, blinded, enemies_vis, teammates, enemies, kast)`
- `_tick_tactical(labels, crouching, scoped, enemies_vis, kast, round_phase, weapon_class, time_in_round, hp, bomb_planted)`

**`label_from_round_stats(round_stats)`**: G-01 fix. Derives labels from round OUTCOMES, eliminating label leakage. Uses kills, deaths, assists, damage, trades, opening kills/deaths, utility stats, equipment value, round_won, rating. Delegates to five static helpers:
- `_label_rs_positioning`
- `_label_rs_utility`
- `_label_rs_economy`
- `_label_rs_engagement`
- `_label_rs_tactical`

**`label_batch(features_batch)`**: Batch labeling with warning about heuristic label leakage. Handles both 2D and 3D input (averages over sequence for 3D).

### `VLJEPACoachingModel(JEPACoachingModel)`

Vision-Language aligned JEPA with coaching concept grounding.

Additional components:
- `concept_embeddings`: `nn.Embedding(num_concepts, latent_dim)` -- learnable concept prototypes.
- `concept_projector`: `Linear(latent_dim, latent_dim) -> GELU -> Linear(latent_dim, latent_dim)`.
- `concept_temperature`: Learned scalar, initialized to 0.10 (Supplement_N260 Section P2-4).

**`forward_vl(x, role_id=None) -> Dict`**: Full VL-JEPA forward:
1. Encode to latent space.
2. Mean-pool over sequence.
3. Project into concept-aligned space + L2-normalize.
4. Cosine similarity against concept embeddings.
5. Scale by learned temperature (clamped [0.01, 1.0]).
6. Softmax for concept probabilities.
7. Standard coaching output via parent.
8. Decode top concepts.
Returns dict with `concept_probs`, `concept_logits`, `top_concepts`, `coaching_output`, `latent`.

**`_decode_top_concepts(probs, k=3)`**: Returns top-k `(concept_name, probability)` tuples for batch[0]. NN-JM-01: Guards against empty batch.

**`get_concept_activations(x)`**: Lightweight concept-only forward (no coaching head, no LSTM). NN-JM-02: Ensures eval mode during inference.

### `vl_jepa_concept_loss(concept_logits, concept_labels, concept_embeddings, alpha=0.5, beta=0.1)`

VL-JEPA concept alignment loss:
1. Multi-label BCE on concept logits vs labels.
2. VICReg-inspired diversity loss: `-mean(std_per_dim)` of normalized concept embeddings.
3. Total = `alpha * concept_loss + beta * diversity_loss`.
4. NN-JM-05: Aligns all tensors to `concept_logits.device`.

---

## 26. JEPA Training Pipeline (`jepa_train.py`)

Standalone JEPA pre-training and fine-tuning pipeline.

### Constants

- `_MIN_TICKS_FOR_SEQUENCE = 20`: Minimum ticks for one training sample (J-1 fix).
- `_MAX_TICKS_PER_SEQUENCE = 500`: Memory bound per player-demo.
- `_PROJECT_ROOT` / `_DB_PATH`: Project root and database path.

### `_open_db(row_factory=False) -> sqlite3.Connection`

Opens monolith DB with WAL mode and 30s busy timeout.

### `JEPAPretrainDataset(Dataset)`

**`__init__(match_sequences, context_len=10, target_len=10, seed=42)`**: M2 fix: asserts `_MIN_TICKS_FOR_SEQUENCE >= context_len + target_len`. DET-01: per-dataset numpy Generator for bit-reproducibility.

**`__getitem__(idx)`**: Samples random starting point. Returns `{"context": FloatTensor, "target": FloatTensor}`.

### Data Loading Functions

**`_load_tick_sequence(demo_name, player_name, max_ticks=500) -> np.ndarray`**: J-1 fix: Uses `FeatureExtractor.extract_batch()` for canonical 25-dim tick-level vectors. Raw sqlite3 for performance. DATA-01 fix: does NOT inject `avg_kast` per-tick. V-4 fix: catches `DataQualityError`.

**`load_pro_demo_sequences(limit=100) -> List[np.ndarray]`**: J-1 fix: queries PlayerTickState (tick-level) instead of RoundStats (round-aggregate). Excludes ghost players (`sample_weight=0.0`).

**`load_user_match_sequences(limit=200) -> tuple`**: Loads user tick sequences. WR-53: Repeat-pads last tick instead of zero-padding (zero vectors encode impossible game states).

### Negative Sampling

**`_jepa_negative_indices(batch_size_actual, num_negatives, device)`**: P1-05 + NN-35: O(B) negative-index sampling via shifted randperm. Each sample excludes itself.

### Pre-training Pipeline

**`_jepa_pretrain_load_data(batch_size, worker_init_fn)`**: Loads pro sequences, builds seeded DataLoader.

**`_jepa_pretrain_setup_training(model, learning_rate, num_epochs, dataloader)`**: NN-JM-04: Freezes target encoder. Creates AdamW optimizer with separate param groups. Cosine LR scheduler (NN-L-15). Returns `(optimizer, scheduler, device, ema_state)`.

**`_jepa_pretrain_process_batch(model, batch, device, ...)`**: Single batch: forward -> loss -> backward -> clip (max_norm=1.0) -> optimizer step -> EMA update with J-6 cosine momentum schedule.

**`train_jepa_pretrain(model, num_epochs=50, batch_size=16, learning_rate=1e-4, num_negatives=8, log_dir=...)`**: Full pre-training:
1. Sets global seed.
2. Creates TensorBoard callback.
3. Loads data.
4. Sets up training (optimizer, scheduler, device, EMA state).
5. Epoch loop with early stopping (patience=10, min_delta=1e-5).
6. Fires callbacks.
7. Finalizes via `_jepa_pretrain_finalize()`.

**`_jepa_pretrain_finalize(model, loss_history, ...)`**: Fires `on_train_end`, freezes encoders, attaches training metadata and REPR-01 EMA counters to model.

### Fine-tuning Pipeline

**`train_jepa_finetune(model, X_train, y_train, num_epochs=30, batch_size=16, learning_rate=1e-3)`**: Supervised fine-tuning of LSTM + MoE:
- Freezes encoders.
- Optimizes only `lstm`, `experts`, `gate` parameters.
- MSELoss.
- Gradient clipping (NN-H-01).
- DET-01: Seeded generator.

### Checkpoint Management

**`save_jepa_model(model, path, optimizer=None, trainer=None)`**: Saves checkpoint with full metadata:
- `model_state_dict`, `is_pretrained`, `input_dim`, `output_dim`, `param_count`, `save_timestamp`.
- Optional: `optimizer_state_dict`.
- REPR-01: `ema_step`, `ema_total_steps` from trainer or model.
- `training_metadata` if available.
- M3 fix: Atomic write via tempfile + `os.replace()`.

**`load_jepa_model(path, input_dim, output_dim) -> JEPACoachingModel`**: Loads checkpoint, restores `is_pretrained` flag, training metadata, and REPR-01 EMA counters.

### CLI Entry Point

Supports `--mode pretrain` and `--mode finetune` with configurable `--model-path`.

---

## 27. JEPA Trainer (`jepa_trainer.py`)

### `_resolve_concept_labels(round_stats, concept_logits, device)`

Helper: resolves concept labels from round stats, filtering to valid indices. Returns `(labels_or_None, filtered_concept_logits)`.

### `JEPATrainer`

Trainer for JEPA with drift-triggered retraining (Task 2.19.3).

**Constructor** `__init__(model, lr=1e-4, weight_decay=1e-2, drift_threshold=2.5, t_max=100)`:
- NN-36: Excludes target encoder from gradient.
- KT-05: Separate concept parameters with 0.05x LR multiplier.
- Creates AdamW with parameter groups.
- Phase 4B: Sequential LR (linear warmup 5% -> cosine decay).
- Phase 4A: AMP with GradScaler.
- Phase 4C+D: Gradient accumulation (4 steps) and clipping (max_norm=1.0).
- J-6: EMA cosine momentum schedule. REPR-01: rehydrates from model's saved counters.
- `DriftMonitor` for feature drift detection.
- P9-02: `EmbeddingCollapseDetector(threshold=0.01, patience=2)`.
- G-01: `LabelSourceMonitor` for concept-label routing telemetry.

**`set_total_steps(epochs, batches_per_epoch)`**: Sets `_ema_total_steps` for cosine schedule (NN-04b).

**`_scheduled_ema_momentum() -> float`**: J-6 cosine schedule: `tau(t) = 1 - (1 - tau_base) * (cos(pi*t/T) + 1) / 2`. Starts at 0.996 (fast tracking) -> 1.0 (frozen target). Increments step counter.

**`encode_raw_negatives(negatives, seq_len) -> Tensor`**: NN-H-02: Shared encoding for raw feature negatives. Expands each negative to full sequence, encodes via target encoder, mean-pools.

**`train_step(x_context, x_target, negatives, step_optimizer=True) -> dict`**: Single self-supervised step with AMP + gradient accumulation:
1. NN-TR-03: Validates 3D input shapes and batch size match.
2. NN-JT-03: Moves tensors to model device.
3. Phase 2D: Tabular augmentation on context.
4. AMP autocast for forward + loss.
5. Encodes raw negatives if needed.
6. Phase 2A: Augments with MoCo queue.
7. Phase 2B: Learned CLIP-style temperature.
8. InfoNCE loss + Phase 2E VICReg regularization.
9. Phase 2A: Enqueues target embeddings.
10. Phase 4C: Scales loss for accumulation.
11. Optimizer step (if `step_optimizer`).
12. Returns dict: `loss`, `embedding_variance`, `grad_norm`, `temperature`, `vicreg`.

**`_tabular_augment(x, mask_ratio=0.3, noise_std=0.03)`**: Phase 2D TabNet-style feature masking + Gaussian noise.

**`_augment_with_moco_queue(negatives, pred_embedding)`**: Phase 2A: Samples up to 64 entries from MoCo queue, concatenates with batch negatives.

**`_optimizer_step() -> float`**: Unscale -> clip -> step -> scaler update -> zero_grad -> EMA target encoder update.

**`_log_embedding_diversity(embeddings) -> float`**: P9-02 monitoring. Returns mean variance across latent dimensions. Warns if below 0.01.

**`train_epoch(dataloader, device) -> float`**: One full epoch:
- In-batch negatives with NN-35 self-exclusion.
- NN-JT-01: Skips batches with size < 2.
- Gradient accumulation every 4 batches.
- Flushes remaining gradients at epoch end.
- NN-TR-02: Warns if 0 batches processed.
- P9-02: Feeds epoch mean variance to `EmbeddingCollapseDetector.update()`.

**`check_val_drift(val_df, reference_stats=None)`**: Checks validation set for feature drift via `DriftMonitor`. Flags `_needs_full_retrain` when `should_retrain()` returns True.

**`retrain_if_needed(full_dataloader, device, epochs=10) -> bool`**: Conditionally retrains:
- Resets LR scheduler with warmup.
- V-3 fix: Resets EMA cosine schedule.
- P9-02: Resets collapse detector.
- Clears drift flag and history after successful retraining.

**`train_step_vl(x_context, x_target, negatives, concept_alpha=0.5, concept_beta=0.1, round_stats=None, step_optimizer=True) -> dict`**: VL-JEPA training step:
1. Requires `VLJEPACoachingModel`.
2. Phase 2D augmentation + AMP autocast.
3. Forward JEPA pretrain + VL forward.
4. InfoNCE loss + VICReg.
5. Resolves concept labels from round stats.
6. If no labels: uses InfoNCE alone (J-2 skip, no leakage risk).
7. If labels available: adds concept alignment loss + diversity loss.
8. Records label source to `LabelSourceMonitor`.
9. Returns dict: `total_loss`, `infonce_loss`, `concept_loss`, `diversity_loss`, `label_source`.

---

## 28. Inference / Ghost Engine

### `inference/__init__.py`

Empty file.

### `GhostEngine`

Real-time Inference Engine for the RAP Coach ("The Ghost").

**`__init__(device=None)`**: Auto-detects device. Calls `_load_brain()`.

**`_load_brain()`**:
- Checks `USE_RAP_MODEL` setting (disabled by default).
- Creates model via `ModelFactory.get_model(TYPE_RAP)`.
- Loads checkpoint via `load_nn()`.
- Sets `is_trained = True` on success.
- Gracefully handles all failure modes (sets model to None).

**`predict_tick(tick_data, game_state=None) -> Tuple[float, float]`**:

Returns `(ghost_x, ghost_y)` world coordinates. Steps:

1. **Tensor Preparation** via `TensorFactory`:
   - A. Map Frame -- tactical overlay with optional PlayerKnowledge.
   - B. View Frame -- FOV + visible entities + utility zones.
   - C. Motion -- trajectory + velocity + crosshair.
   - D. Metadata -- via unified `FeatureExtractor.extract()` with context dict. Validates feature parity at inference boundary (P-SR-01).

2. **Inference**: `model(view_frame, map_frame, motion_diff, metadata)` under `torch.no_grad()`.

3. **Output Decoding**: `ghost_pos = current_pos + optimal_delta * RAP_POSITION_SCALE`.

Handles dict or dataclass tick_data via `SimpleNamespace` promotion. POV tensor mode toggled via `USE_POV_TENSORS` setting (R4-04-01 channel semantics warning).

**`_build_knowledge_from_game_state(tick_data, game_state)`**: Static method. Builds `PlayerKnowledge` from game_state dict using `PlayerKnowledgeBuilder`. Returns None on failure (falls back to legacy tensors).

---

## 29. Root Training Entry Point (`run_full_training_cycle.py`)

CLI entry point for the training pipeline.

### Environment Setup

Sets `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` for CUDA memory management.

### `_build_callbacks(args) -> CallbackRegistry`

Builds callback registry:
1. `TensorBoardCallback` (unless `--no-tensorboard`).
2. `MaturityObservatory` (PRE-11 wiring) -- shares the SummaryWriter for co-located TensorBoard events.

### `main()`

CLI arguments:

| Argument | Default | Description |
|----------|---------|-------------|
| `--dry-run` | False | Single epoch, no production saves |
| `--resume` | False | Resume from latest checkpoint |
| `--epochs` | 100 | Max epochs |
| `--model-type` | `"all"` | `"all"`, `"jepa"`, or `"rap"` |
| `--tb-logdir` | `RUNS_DIR` | TensorBoard log directory |
| `--no-tensorboard` | False | Disable TensorBoard |
| `--patience` | None | Early-stop patience (default: 10 smoke / 25-30 full) |
| `--train-samples` | None | Per-epoch train subsample |
| `--val-samples` | None | Validation subsample |

Execution flow:
1. `set_global_seed()` (DET-01).
2. Initializes `CoachTrainingManager`.
3. Builds callbacks.
4. Overrides epochs/patience for dry run.
5. Assigns dataset splits.
6. Phase 1: JEPA Pre-Training (if `--model-type` is `"all"` or `"jepa"`).
7. GPU memory reclamation between phases (`gc.collect()`, `torch.cuda.empty_cache()`, `torch.cuda.synchronize()`).
8. Phase 2: RAP Coach Training (if `--model-type` is `"all"` or `"rap"`).
9. Finally: closes all callbacks.

---

## 30. Cross-Cutting Design Decisions

### Reproducibility (DET Series)

- **DET-01**: Every DataLoader uses `seeded_generator()`. Per-dataset numpy Generators use `SeedSequence`-derived seeds.
- **DET-02**: `torch.use_deterministic_algorithms(True, warn_only=True)` surfaces non-deterministic kernels as warnings.
- **GLOBAL_SEED=42** used everywhere. `set_global_seed()` must be called before any training.

### Safety Invariants

- **P-RSB-03**: `round_won` excluded from training features (label leak).
- **NN-MEM-01**: Hopfield bypassed until >= 2 forward passes.
- **NN-16**: EMA `apply_shadow()` clones shadows before assignment.
- **NN-JM-04**: Target encoder `requires_grad=False` during EMA updates.
- **DS-12**: `MIN_DEMO_SIZE=10MB` for demo validation.
- **P-VEC-02/P3-A**: NaN/Inf clamp + >5% batch triggers `DataQualityError`.
- **METADATA_DIM=25**: Single source of truth from `vectorizer.py`.

### Checkpoint Integrity

- **CTF-1**: SHA-256 hash registry for checkpoint files.
- **GAP-07**: Sidecar `.pt.meta.json` with feature schema, validated on load.
- **Atomic writes**: All saves use tmpfile + `os.replace()`.
- **StaleCheckpointError**: Raised on dimension or schema mismatch, never silently ignored.

### Label Leak Prevention

- **LEAK-01**: Value head uses advantage function, not `round_outcome` (future information).
- **G-01**: VL-JEPA concept labels derived from `RoundStats` (orthogonal to input features).
- **NN-JM-03**: Heuristic `label_tick()` is explicitly marked as having label leakage risk.
- **J-2**: VL-JEPA falls back to InfoNCE-only when no RoundStats available.

### Embedding Collapse Prevention

- **P9-02**: `EmbeddingCollapseDetector` hard-stops training after 2 consecutive collapsed epochs.
- **Phase 2E**: VICReg variance + covariance regularization.
- **Phase 2A**: MoCo v3 momentum contrast queue for richer negatives.
- **Phase 2B**: Learned CLIP-style temperature.

### Training Pipeline Architecture

The training pipeline follows a hierarchical design:
1. **`run_full_training_cycle.py`**: CLI entry point, creates orchestrators.
2. **`CoachTrainingManager`**: Coordinates full 5-phase cycle (JEPA -> Pro baseline -> User tailoring -> RAP -> Role head).
3. **`TrainingOrchestrator`**: Unified epoch loop with data fetching, batch preparation, step dispatch, checkpointing, and early stopping.
4. **`JEPATrainer` / RAPTrainer**: Model-specific training logic (AMP, gradient accumulation, drift monitoring).
5. **`CallbackRegistry`**: Plugin-based instrumentation (TensorBoard, Maturity Observatory, Embedding Projector).

### Maturity System

Two complementary maturity systems:
1. **Demo-count maturity** (coach_manager.py): 3 tiers (CALIBRATING/LEARNING/MATURE) with confidence multipliers (0.5/0.8/1.0).
2. **Neural maturity** (maturity_observatory.py): 5 states (doubt/crisis/learning/conviction/mature) derived from conviction index (weighted composite of 5 neural signals).

### Model Architecture Summary

| Model | Input | Output | Architecture | Use Case |
|-------|-------|--------|--------------|----------|
| `AdvancedCoachNN` | 25-dim features | 10-dim adjustments | LSTM + MoE (top-2 sparse gate) | Supervised coaching |
| `JEPACoachingModel` | 25-dim sequences | 10-dim adjustments | JEPA Encoder + LSTM + MoE | Self-supervised pretrain + supervised finetune |
| `VLJEPACoachingModel` | 25-dim sequences | 10-dim + 16 concepts | JEPA + Concept alignment head | Concept-grounded coaching |
| `RAPCoachModel` | View/Map/Motion/Metadata | Strategy/Value/Position | CNN + LTC + Superposition | Behavioral optimization |
| `NeuralRoleHead` | 5-dim playstyle | 5-dim role probs | MLP (750 params) | Role classification |
| `WinProbabilityTrainerNN` | 9-dim game state | Win probability | MLP (sigmoid) | Win prediction |
