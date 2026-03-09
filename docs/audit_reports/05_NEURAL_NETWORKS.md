# Neural Networks, Training Infrastructure, and ML Control Plane
# Macena CS2 Analyzer — Technical Audit Report 5/8

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| Report ID | AUDIT-2026-05 |
| Date | 2026-03-08 |
| Version | 1.0 |
| Classification | Internal — Engineering Review |
| Auditor | Engineering Audit Protocol v3 |
| Scope | 57 files across NN core, RAP Coach, JEPA, training infrastructure, and ML control plane |
| Total LOC Audited | ~8,200 (Python) + ~400 (READMEs/docs) |
| Audit Standard | ISO/IEC 25010 (Software Quality), ISO/IEC 27001 (Security), OWASP Top 10, IEEE 730 (SQA), CLAUDE.md Engineering Constitution |
| Previous Audit | N/A (baseline audit) |

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Audit Methodology](#2-audit-methodology)
3. [NN Core Architecture](#3-nn-core-architecture)
   - 3.1 `config.py`
   - 3.2 `model.py`
   - 3.3 `dataset.py`
   - 3.4 `factory.py`
   - 3.5 `evaluate.py`
   - 3.6 `persistence.py`
   - 3.7 `ema.py`
   - 3.8 `early_stopping.py`
   - 3.9 `role_head.py`
   - 3.10 `win_probability_trainer.py`
   - 3.11 `layers/superposition.py`
4. [JEPA Architecture](#4-jepa-architecture)
   - 4.1 `jepa_model.py`
   - 4.2 `jepa_train.py`
   - 4.3 `jepa_trainer.py`
5. [RAP Coach Architecture](#5-rap-coach-architecture)
   - 5.1 `rap_coach/model.py`
   - 5.2 `rap_coach/perception.py`
   - 5.3 `rap_coach/memory.py`
   - 5.4 `rap_coach/strategy.py`
   - 5.5 `rap_coach/pedagogy.py`
   - 5.6 `rap_coach/communication.py`
   - 5.7 `rap_coach/chronovisor_scanner.py`
   - 5.8 `rap_coach/trainer.py`
   - 5.9 `rap_coach/skill_model.py`
6. [Training Infrastructure](#6-training-infrastructure)
   - 6.1 `train.py`
   - 6.2 `train_pipeline.py` (deprecated)
   - 6.3 `training_config.py`
   - 6.4 `training_controller.py`
   - 6.5 `training_monitor.py`
   - 6.6 `training_callbacks.py`
   - 6.7 `tensorboard_callback.py`
   - 6.8 `embedding_projector.py`
   - 6.9 `maturity_observatory.py`
7. [ML Control Plane](#7-ml-control-plane)
   - 7.1 `control/ml_controller.py`
   - 7.2 `control/ingest_manager.py`
   - 7.3 `control/db_governor.py`
   - 7.4 `control/console.py`
   - 7.5 `session_engine.py`
   - 7.6 `training_orchestrator.py.backup`
8. [Documentation Assessment](#8-documentation-assessment)
9. [Consolidated Findings Matrix](#9-consolidated-findings-matrix)
10. [Recommendations](#10-recommendations)
11. [Appendices](#appendices)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Domain Health Assessment

**Overall Rating: SOUND WITH RESERVATIONS**

The Neural Networks domain encompasses the complete ML pipeline — from model architectures (JEPA, RAP Coach, Legacy MoE) through training infrastructure (callbacks, monitoring, observatory) to the operational control plane (Console, SessionEngine, MLController). This is the computational core of the coaching system: every tactical recommendation, skill assessment, and positional suggestion originates from these neural networks.

The domain demonstrates considerable architectural ambition and sophistication. The RAP Coach implements a neuroscience-inspired five-layer pipeline (Perception → Memory → Strategy → Pedagogy → Communication) that is cleanly modularized. The JEPA architecture implements VL-JEPA Selective Decoding for real-time inference optimization. The training Observatory (four layers: callbacks, TensorBoard, maturity classification, embedding projection) provides production-grade introspection. The ML control plane enables cooperative training cancellation, pause/resume, and intensity throttling.

However, several significant issues were identified:

**Critical Design Issues (3 originally, all 3 RESOLVED):**
1. ~~**SuperpositionLayer sparsity loss uses detached tensors** — the L1 regularization on gate activations cannot backpropagate, making the sparsity penalty a no-op during training.~~ **RESOLVED:** `_last_gate_live` now stores live (non-detached) tensor for loss computation.
2. ~~**RAP Perception temporal blindness** — the CNN processes a single frame and replicates it across all timesteps, preventing the model from perceiving visual changes over time.~~ **RESOLVED:** Model now supports per-timestep [B,T,C,H,W] visual input with per-frame CNN processing.
3. ~~**O(batch²) negative sampling in JEPATrainer** — quadratic encoder forward passes per batch instead of a single batched pass.~~ **RESOLVED:** All targets are now encoded in a single batched `target_encoder` forward pass.

**Important Design Issues (4, 2 RESOLVED):**
1. ~~**ModelFactory hidden_dim mismatch** — legacy model defaults to 64 via factory but 128 via config.py, causing checkpoint incompatibility.~~ **RESOLVED:** Factory now uses `HIDDEN_DIM` from config.py (128).
2. **Dual training invocation paths** — Console-controlled (with pause/stop) and SessionEngine daemon (without control) can run simultaneously with no mutual exclusion.
3. ~~**persistence.py silent random-weight return** — when no checkpoint exists at any fallback location, returns an untrained model without warning.~~ **RESOLVED:** Now raises `FileNotFoundError` with explicit message.
4. **Deterministic negative sampling in JEPA** — always picks lowest-index candidates, reducing contrastive learning diversity.

Across 39 Python source files audited (excluding READMEs, shims, and __init__ stubs), we identified 72 findings: 3 CRITICAL, 4 HIGH, 18 MEDIUM, 32 LOW, and 15 GOOD PRACTICE observations.

> **Post-Audit Resolution Status (2026-03-08):** 11 findings have been resolved or rendered obsolete: 3/3 CRITICAL (NN-24, NN-35, NN-39), 2/4 HIGH (NN-09, NN-14; NN-93 file deleted), 3/18 MEDIUM (NN-16, NN-36; NN-94 file deleted), 2/32 LOW (NN-25; NN-95 file deleted). Remaining: 0 CRITICAL, 2 HIGH, 15 MEDIUM, 30 LOW open.

### 1.2 Risk Profile

| Risk Category | Level | Justification |
|---------------|-------|---------------|
| **Training Correctness** | ~~HIGH~~ LOW | ~~SuperpositionLayer sparsity no-op, perception temporal blindness,~~ deterministic negatives in train.py (all 3 CRITICALs resolved) |
| **Checkpoint Integrity** | ~~MEDIUM~~ LOW | ~~Factory/config hidden_dim mismatch~~ (resolved), no architecture versioning in checkpoints |
| **Operational Safety** | MEDIUM | Dual training paths, uncoordinated shutdown, vestigial lock in MLController |
| **Security** | LOW | `weights_only=True` enforced, no user-facing input in ML pipeline |
| **Performance** | MEDIUM | O(batch²) JEPATrainer, Hopfield O(seq²), ConceptLabeler un-vectorized loops |
| **Observability** | LOW | Excellent 4-layer Observatory, comprehensive TensorBoard integration |

### 1.3 Key Metrics

| Metric | Value |
|--------|-------|
| Total Python Files | 39 source + 6 shims + 12 READMEs |
| Total LOC (Python) | ~8,200 |
| Model Architectures | 5 (AdvancedCoachNN, JEPA, VL-JEPA, RAP Coach, RoleHead + WinProb) |
| Training Pipelines | 3 active + 1 deprecated |
| Callback Types | 3 (TensorBoard, EmbeddingProjector, MaturityObservatory) |
| CRITICAL Findings | ~~3~~ 0 remaining (3 resolved) |
| HIGH Findings | ~~4~~ 2 remaining (2 resolved: NN-09, NN-14; NN-93 file deleted) |
| MEDIUM Findings | ~~18~~ 15 remaining (3 resolved: NN-16, NN-36, NN-94 file deleted) |
| LOW Findings | ~~32~~ 30 remaining (2 resolved: NN-25, NN-95 file deleted) |
| GOOD PRACTICE | 15 |

---

## 2. AUDIT METHODOLOGY

### 2.1 Approach
Each source file was subjected to exhaustive line-by-line analysis across six dimensions:
1. **Architecture/Design Patterns** — structural choices, modularity, coupling
2. **Correctness** — mathematical soundness, edge cases, silent failures, contract violations
3. **Security** — input validation, deserialization safety, secrets handling
4. **Concurrency** — thread safety, race conditions, lock discipline
5. **Performance** — algorithmic complexity, memory usage, scalability
6. **Notable Practices** — positive patterns worth preserving

### 2.2 Severity Classification

| Level | Definition |
|-------|-----------|
| **CRITICAL** | Directly corrupts training signal or model output; must fix before production |
| **HIGH** | Causes silent degradation, checkpoint incompatibility, or operational hazard |
| **MEDIUM** | Design weakness that could cause issues under specific conditions |
| **LOW** | Minor concern, documentation gap, or code quality issue |
| **GOOD** | Positive engineering practice worth highlighting |

---

## 3. NN CORE ARCHITECTURE

### 3.1 `config.py` (155 LOC)

**Purpose:** Central configuration for NN hyperparameters, device selection, reproducibility seeding, and ML intensity throttling.

**Key Constants:** `GLOBAL_SEED=42`, `BATCH_SIZE=32`, `INPUT_DIM=METADATA_DIM=25`, `OUTPUT_DIM=25`, `HIDDEN_DIM=128`, `LEARNING_RATE=1e-3`, `EPOCHS=50`, `RAP_POSITION_SCALE=500.0`

**Design Patterns:**
- Cached device detection with integrated GPU de-prioritization by keyword matching
- Four-source reproducibility seeding (Python, NumPy, PyTorch CPU, PyTorch CUDA)
- Intensity-based throttling (LOW/MEDIUM/HIGH) for production resource control

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-01 | LOW | `_cached_device` and `_device_logged` are module-level mutable globals without thread synchronization. Benign in practice (same result regardless of race), but not formally thread-safe. |
| NN-02 | GOOD | Excellent multi-GPU selection logic that de-prioritizes integrated GPUs. `cuDNN.deterministic = True` correctly prioritizes reproducibility over speed. |
| NN-03 | GOOD | `RAP_POSITION_SCALE = 500.0` clearly documented with cross-references (P9-01, F3-05). |

---

### 3.2 `model.py` (182 LOC)

**Purpose:** Core AdvancedCoachNN architecture — LSTM-based Mixture of Experts with gated expert blending.

**Architecture:**
```
Input [batch, seq_len, INPUT_DIM=25]
  -> LSTM (hidden_dim, 2 layers, dropout=0.2)
  -> last hidden state [batch, hidden_dim]
  -> 3 Expert Heads (Linear hidden -> output)
  -> Gating Network (Linear hidden -> 3) + Softmax
  -> Optional Role Bias ((gate + role_bias) / 2.0)
  -> Weighted Expert Sum -> tanh -> [batch, OUTPUT_DIM=25]
```

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-04 | LOW | `_validate_input_dim()` auto-unsqueezes 1D/2D inputs to 3D — honest comment acknowledges this "may mask batch dimension errors during training." |
| NN-05 | LOW | Role bias blending `(gate + bias) / 2.0` forces 50% minimum weight on the role-preferred expert. Limits gate expressiveness when role context is active. |
| NN-06 | GOOD | Dual initialization path (legacy positional args vs config dataclass) ensures backward compatibility. Architecture config stored in model attributes for checkpoint serialization. |
| NN-07 | GOOD | `TeacherRefinementNN = AdvancedCoachNN` alias preserves backward compatibility. Optional RAP/JEPA imports with graceful fallback (`RAP_COACH_AVAILABLE` flag). |

---

### 3.3 `dataset.py` (64 LOC)

**Purpose:** Minimal PyTorch Dataset implementations for supervised and self-supervised training.

**Classes:** `ProPerformanceDataset` (standard X,y), `SelfSupervisedDataset` (sliding-window context/target pairs for JEPA pretraining)

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-08 | GOOD | Clean, minimal implementation. Type coercion handles both tensor and non-tensor inputs. `SelfSupervisedDataset.__getitem__` uses slicing (zero-copy on contiguous tensors). |

---

### 3.4 `factory.py` (121 LOC)

**Purpose:** Static factory pattern for model instantiation. Supports 5 model types: Legacy, JEPA, VL-JEPA, RAP, RoleHead.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| ~~**NN-09**~~ | ~~**HIGH**~~ | ~~**Hidden dimension mismatch:** Legacy model defaults to `hidden_dim=64` via `kwargs.get("hidden_dim", 64)`.~~ **RESOLVED:** Factory now uses `kwargs.get("hidden_dim", HIDDEN_DIM)` importing `HIDDEN_DIM=128` from config.py. |
| NN-10 | LOW | RAP model defaults to `output_dim=10` while other models default to `OUTPUT_DIM=25`. Intentional for RAP architecture but should be documented in the docstring. |
| NN-11 | GOOD | Clear enumeration of valid model types with helpful error messages. Checkpoint naming convention centralized. |

---

### 3.5 `evaluate.py` (56 LOC)

**Purpose:** Inference-time evaluation with optional SHAP explainability.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| **NN-12** | **MEDIUM** | Only 4 of 25 output dimensions are used in the result dict (`adr_weight`, `kast_weight`, `hs_weight`, `impact_weight`). The remaining 21 dimensions are silently discarded. Legacy coupling from the original 4-output model. |
| NN-13 | LOW | Zero-vector SHAP baseline (self-documented as F3-18) biases attributions. SHAP KernelExplainer with 25 features could be computationally expensive. |

---

### 3.6 `persistence.py` (86 LOC)

**Purpose:** Model persistence with 4-level fallback chain (user-specific local → global local → user-specific bundled → global bundled).

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| ~~**NN-14**~~ | ~~**HIGH**~~ | ~~`load_nn` returns the model with random weights when no checkpoint exists.~~ **RESOLVED:** Now logs a warning and raises `FileNotFoundError` with explicit message (lines 87-97). |
| NN-15 | GOOD | `weights_only=True` on `torch.load` prevents arbitrary code execution via pickle deserialization. `StaleCheckpointError` with strict state dict loading prevents dimension mismatches. |

---

### 3.7 `ema.py` (128 LOC)

**Purpose:** Exponential Moving Average for model weight smoothing during training.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| ~~NN-16~~ | ~~MEDIUM~~ | ~~`apply_shadow` assigns shadow tensors directly to `param.data` instead of copying.~~ **RESOLVED:** Now uses `param.data = self.shadow[name].clone()` at line 79 with explicit NN-16 fix comment. |
| NN-17 | GOOD | `state_dict()` returns cloned tensors (F3-30 fix). `load_state_dict` uses `clone()` to isolate loaded state. Dynamic parameter registration handles late-added parameters. |

---

### 3.8 `early_stopping.py` (86 LOC)

**Purpose:** Standard early stopping with patience and minimum delta.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-18 | GOOD | Textbook-clean implementation. `should_stop` flag provides polling alternative to return-value checking. `reset()` enables reuse across training phases. |

---

### 3.9 `role_head.py` (327 LOC)

**Purpose:** Self-contained neural role classification pipeline — model architecture (3-layer MLP, ~750 parameters), data preparation, training with early stopping, persistence, and inference.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-19 | GOOD | Complete mini-pipeline in one file. Seeded `torch.Generator().manual_seed(42)` for local reproducibility without affecting global state (F3-32). Label smoothing correctly redistributes probability mass. |
| NN-20 | LOW | Full-batch training (no mini-batching) — acceptable for the expected data volume (~hundreds of player records) but not scalable. |
| NN-21 | GOOD | Role anchor merging (Anchor → Support) well-documented and domain-semantically correct. |

---

### 3.10 `win_probability_trainer.py` (124 LOC)

**Purpose:** Win probability prediction via 3-layer MLP (32→16→1 with Sigmoid).

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-22 | LOW | Uses `optim.Adam` instead of `AdamW` (inconsistent with rest of codebase). No GPU support, no gradient clipping — acceptable for this small model but inconsistent. |
| NN-23 | LOW | Feature list duplicated between `train_win_prob_model` and `predict_win_prob`. Should be a module-level constant. |

---

### 3.11 `layers/superposition.py` (105 LOC)

**Purpose:** Context-dependent gating layer for dynamic specialization of coaching modes. Sigmoid gate modulates linear layer output.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| ~~**NN-24**~~ | ~~**CRITICAL**~~ | ~~`gate_sparsity_loss()` uses detached gate activations.~~ **RESOLVED:** `_last_gate_live` now stores live (non-detached) tensor at line 47; `gate_sparsity_loss()` uses it at line 99. Detached copy kept separately for observability only. |
| ~~NN-25~~ | ~~LOW~~ | ~~`torch.tensor(0.0)` returned on line 95 when no activations exist — always on CPU regardless of model device.~~ **RESOLVED:** Now uses `torch.tensor(0.0, device=self.weight.device)` at line 98. |
| NN-26 | GOOD | Well-structured observability with `get_gate_statistics()` providing mean, std, min, max, and sparsity ratio. Tracing toggle for debugging without code changes. |

---

## 4. JEPA ARCHITECTURE

### 4.1 `jepa_model.py` (1000 LOC)

**Purpose:** Joint Embedding Predictive Architecture for CS2 coaching. Includes JEPAEncoder, JEPAPredictor, JEPACoachingModel (with MoE), ConceptLabeler (16 coaching concepts), and VL-JEPA extension with selective decoding.

**Architecture:**
```
Standard JEPA:
  Context Encoder [batch, seq_len, 25] -> [batch, seq_len, latent_dim=256]
  Target Encoder (EMA copy, no gradient)
  Predictor: context latent -> target latent prediction
  Loss: Contrastive (positive pair closeness, negative pair distance)

VL-JEPA Extension:
  + View encoder for visual input (3-channel, adaptive pooling)
  + Concept alignment loss (inter/intra-concept distance)
  + Selective Decoding: cosine-distance gating skips LSTM+MoE when state unchanged
```

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-27 | GOOD | `forward_selective` (VL-JEPA Selective Decoding) is a genuine computational optimization — cosine-distance gating avoids the expensive LSTM+MoE path when game state has not changed significantly. Well-designed inference shortcut. |
| NN-28 | MEDIUM | `label_tick()` uses `.item()` calls in a tight loop (lines 524-549). When called from `label_batch()` for 3D tensors, this creates O(batch × seq_len × 25) Python-level `.item()` calls, preventing vectorization. |
| NN-29 | GOOD | Two labeling modes exist (`label_tick` vs `label_from_round_stats`) to address G-01 label leakage. The outcome-based mode is architecturally correct. |
| NN-30 | GOOD | 16 coaching concepts as a frozen dataclass taxonomy. Comprehensive domain model (positioning, crosshair, utility, economy, timing, rotation, trade, info-gathering, anti-eco, post-plant, retake, peek, flash, smoke, lurk, communication). |

---

### 4.2 `jepa_train.py` (454 LOC)

**Purpose:** Two-stage JEPA training pipeline: pretrain (contrastive self-supervised) → finetune (concept-labeled supervised).

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-31 | MEDIUM | When `max_start <= 0` in `JEPAPretrainDataset.__getitem__` (lines 57-61), context/target slices are shorter than expected. DataLoader will fail when collating variable-length tensors across the batch. |
| NN-32 | MEDIUM | Fallback tiled sequences (line 155): `np.tile(features, (20, 1))` creates identical rows. The JEPA predictor learns trivially low contrastive loss. Warning logged but not prevented. |
| NN-33 | MEDIUM | `avg_loss = total_loss / len(dataloader)` (line 306) raises `ZeroDivisionError` if `load_pro_demo_sequences` returns empty. |
| NN-34 | GOOD | `torch.load(path, weights_only=True)` at line 417 — correctly prevents arbitrary code execution. |

---

### 4.3 `jepa_trainer.py` (295 LOC)

**Purpose:** Class-based JEPA trainer with drift monitoring, retraining triggers, and VL-JEPA concept training support.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| ~~**NN-35**~~ | ~~**CRITICAL**~~ | ~~`train_epoch` negative sampling loop: O(batch_size²) forward passes.~~ **RESOLVED:** All targets are now encoded in a single batched `target_encoder(x_target).mean(dim=1)` call (line 122), then indexed per-sample (lines 124-127). Comment references "NN-35 fix." |
| ~~NN-36~~ | ~~MEDIUM~~ | ~~`optim.AdamW(model.parameters(), ...)` optimizes ALL parameters including the target encoder.~~ **RESOLVED:** Now filters with `[p for n, p in model.named_parameters() if "target_encoder" not in n]` (line 38). Comment references "NN-36." |
| NN-37 | LOW | `CosineAnnealingLR(self.optimizer, T_max=100)` hardcoded (line 38). If training runs for fewer than 100 epochs, LR never reaches minimum. If more, it cycles. |
| NN-38 | LOW | `ConceptLabeler()` instantiated on every `train_step_vl` call (line 248). Should be cached on `self`. |

---

## 5. RAP COACH ARCHITECTURE

### 5.1 `rap_coach/model.py` (114 LOC)

**Purpose:** Five-layer RAP Coach neural pipeline — Perception → Memory → Strategy → Pedagogy → Positioning.

**Architecture:**
```
Visual Inputs:
  view_frame [B,3,H,W], map_frame [B,3,H,W], motion_diff [B,1,H,W]
    -> RAPPerception (ResNet CNN) -> z_spatial [B, 128]
    -> repeat(seq_len) -> [B, seq_len, 128]  ← TEMPORAL BLINDNESS

Metadata: [B, seq_len, METADATA_DIM=25]
    -> concat with z_spatial -> [B, seq_len, 153]
    -> RAPMemory (LTC + Hopfield) -> [B, seq_len, 256]
    -> RAPStrategy (SuperpositionLayer MoE, 4 experts) -> action [B, output_dim]
    -> RAPPedagogy (Critic V(s)) -> value estimate
    -> CausalAttributor -> 5 concept attribution scores
    -> Position Head -> [B, 3] optimal position delta
```

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| ~~**NN-39**~~ | ~~**CRITICAL**~~ | ~~**Temporal blindness in visual perception**: single frame replicated across all timesteps.~~ **RESOLVED:** Model now handles both per-timestep [B,T,C,H,W] (processed per-frame through CNN, lines 60-68) and static [B,C,H,W] (expanded with `.expand()`) visual inputs. Comment references "NN-39 fix." |
| NN-40 | MEDIUM | `self.memory(lstm_in)` receives concatenated input but `hidden` state defaults to None (line 69). Each forward call starts with fresh hidden state, losing temporal continuity across multiple inference calls. |
| NN-41 | LOW | `optimal_pos = self.position_head(last_hidden)` output is unbounded (no activation). Large deltas could suggest teleporting the player across the map. |
| NN-42 | GOOD | `compute_sparsity_loss` takes `gate_weights` as an explicit parameter (thread-safe, F3-07 fix). |

---

### 5.2 `rap_coach/perception.py` (99 LOC)

**Purpose:** Dual-stream CNN — ventral (view) and dorsal (map) pathways with residual blocks, inspired by neuroscience.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-43 | MEDIUM | `_make_resnet_stack` ignores the structure of `num_blocks` (e.g., `[1,2,2,1]`). It sums all values and creates that many blocks with the SAME channel count. A true ResNet uses per-stage block counts with increasing channels and stride-2 transitions. Produces a shallower feature hierarchy than intended. |
| NN-44 | LOW | Output dimension hardcoded at 64+32+32=128. Changing any backbone silently breaks RAPMemory's `perception_dim` input. No compile-time or static check for this invariant. |

---

### 5.3 `rap_coach/memory.py` (82 LOC)

**Purpose:** Hybrid memory — Liquid Time-Constant (LTC) network for continuous-time dynamics + Hopfield associative memory for tactical pattern recall, with residual connection.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-45 | MEDIUM | `AutoNCP(units=ncp_units, output_size=hidden_dim)` generates random connectivity at construction time (line 34). Two `RAPMemory` instances with identical parameters may have different wirings, making checkpoint sharing between model instances potentially incompatible. |
| NN-46 | MEDIUM | Hopfield attention is O(seq_len² × hidden_dim) (line 73). For long sequences (>256 timesteps), quadratic complexity becomes a bottleneck. |
| NN-47 | LOW | `ncp_units = hidden_dim * 2` ratio is hardcoded (line 33). Changing `hidden_dim` automatically changes NCP topology, silently invalidating existing checkpoints. |

---

### 5.4 `rap_coach/strategy.py` (81 LOC)

**Purpose:** Mixture of Experts with 4 experts, Softmax gating, and SuperpositionLayer context modulation.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-48 | LOW | `ContextualAttention` class defined but never used in the RAP pipeline. Dead code. |
| NN-49 | GOOD | `gate_weights` returned alongside `final_output`, enabling external sparsity loss computation. Clean API design. |

---

### 5.5 `rap_coach/pedagogy.py` (99 LOC)

**Purpose:** `RAPPedagogy` — value function V(s) for advantage estimation with skill conditioning. `CausalAttributor` — hybrid neural/mechanical attribution with 5 error concepts.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-50 | MEDIUM | `_detect_utility_need` uses `torch.sigmoid(hidden.mean(dim=-1))` (line 97). Taking the mean of the entire hidden state as a utility signal is poorly motivated — the hidden state contains mixed information (position, strategy, memory). Effectively a random learned projection. |
| NN-51 | LOW | `mechanical_errors[:, 0] = pos_delta.squeeze()` — if B=1, `.squeeze()` produces a scalar, broadcasting incorrectly. Should use `.squeeze(-1)`. |

---

### 5.6 `rap_coach/communication.py` (136 LOC)

**Purpose:** Template-based advice generation stratified by skill tier (low/mid/high) and topic (positioning/mechanics/strategy).

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-52 | MEDIUM | `scores.shape` (line 103) will raise `AttributeError` if `scores` is a Python list (from fallback at line 101). Should use `np.array([0.1])` for the fallback. |
| NN-53 | LOW | `topics[top_idx % len(topics)]` — with 3 topics and potentially 10+ output dimensions, the index-to-topic mapping cycles naively. |
| NN-54 | GOOD | Template injection impossible — templates are hardcoded strings with numeric/string-safe format values. |

---

### 5.7 `rap_coach/chronovisor_scanner.py` (382 LOC)

**Purpose:** Multi-scale temporal signal analysis for detecting critical moments in matches. Three scales (micro/standard/macro) with configurable lag, threshold, and context.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-55 | HIGH | `ChronovisorScanner.__init__` eagerly loads the model and creates a database manager (lines 142-146). Makes the class impossible to instantiate in test environments without a database or trained model. Should support lazy initialization or dependency injection. |
| NN-56 | LOW | `self.manager.db.get_session("default")` uses hardcoded session name (line 185). Other code uses `get_session()` without arguments. |
| NN-57 | LOW | `deltas = vals[scale.lag:] - vals[:-scale.lag]` (lines 282-283) propagates NaN from model output without checking, potentially suppressing all critical moment detection for a match. |

---

### 5.8 `rap_coach/trainer.py` (110 LOC)

**Purpose:** Multi-task training with four combined losses — strategy, value, sparsity, position — with Z-axis penalty.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-58 | MEDIUM | Loss weights hardcoded: `total_loss = loss_strat + 0.5 * loss_val + loss_sparsity + loss_pos` (line 71). No adaptive scaling. Relative magnitudes may differ by orders of magnitude, causing one loss to dominate. |
| NN-59 | LOW | `z_axis_penalty_weight = 2.0` hardcoded (line 23). Should be configurable as a hyperparameter. |

---

### 5.9 `rap_coach/skill_model.py` (10 LOC shim → `skill_assessment.py` 147 LOC)

**Purpose:** Z-score normalization of player stats against pro baselines, decomposed into 5 independent skill axes.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-60 | LOW | `if not val` (line 52-53) treats `0` and `0.0` as "no data." A player with exactly 0% accuracy would be treated as missing. Should use `if val is None`. |

---

## 6. TRAINING INFRASTRUCTURE

### 6.1 `train.py` (274 LOC)

**Purpose:** Main training entry point supporting supervised (Legacy) and self-supervised (JEPA) training with early stopping, gradient clipping, throttling, and cooperative cancellation.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-61 | MEDIUM | JEPA negative sampling (lines 121-127) is **deterministic** — always picks the first N candidates by index, not random samples. Reduces contrastive learning diversity and could bias the learned representations. |
| NN-62 | LOW | `MIN_TRAINING_SAMPLES = 20` duplicates the constant in `role_head.py`. Should be centralized. |
| NN-63 | LOW | `run_training` function (line 241) accesses private methods `manager._fetch_training_data` and `manager._prepare_tensors` — violates encapsulation. |
| NN-64 | GOOD | Comprehensive training pipeline supporting multiple model types, early stopping, throttling, and cooperative cancellation via `context.check_state()`. |

---

### 6.2 `train_pipeline.py` (115 LOC — DEPRECATED)

**Purpose:** Legacy training pipeline, properly marked with `DeprecationWarning`.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-65 | MEDIUM | If accidentally used: no validation split, no early stopping, no GPU support, no gradient clipping. Minimum sample threshold (5) inconsistent with rest of codebase (20). 52% of input features are padding zeros. Properly deprecated but still importable. |

---

### 6.3 `training_config.py` (70 LOC)

**Purpose:** Dataclass-based training hyperparameter configuration.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-66 | LOW | `batch_size: int = 1` with comment "RAP processes 1 match at a time" — this RAP-specific default becomes the general default for all model types. |
| NN-67 | LOW | `DEFAULT_CONFIG` is a singleton instance. If callers modify it, all subsequent users see the mutations. Should be `frozen=True` or replaced with a factory function. |

---

### 6.4 `training_controller.py` (160 LOC)

**Purpose:** Training governance — monthly quotas (10 demos/month), duplicate detection, diversity checks via cosine similarity.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-68 | LOW | `MAX_DEMOS_PER_MONTH = 10` is very conservative. With 3-5 matches/day, >90% of matches excluded from training. |
| NN-69 | LOW | Feature extraction uses hardcoded normalization baselines (kills=15, deaths=15, ADR=75) not derived from actual data statistics. |
| NN-70 | GOOD | Fail-safe on error (line 80) — refuses to train on exception, preventing garbage training data. |

---

### 6.5 `training_monitor.py` (123 LOC)

**Purpose:** JSON-based training metrics persistence — epoch-by-epoch loss, learning rate, and lifecycle events.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-71 | LOW | No atomic file writes — crash during `_save()` would corrupt the progress JSON. No error handling for corrupt JSON on resume. |

---

### 6.6 `training_callbacks.py` (110 LOC)

**Purpose:** Plugin architecture for training instrumentation — 7 lifecycle hooks with error isolation.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-72 | GOOD | Error isolation in `fire()` catches all exceptions per callback, preventing individual callback failures from crashing training. F3-31 note about intentionally not using `@abstractmethod` prevents breaking changes. |

---

### 6.7 `tensorboard_callback.py` (228 LOC)

**Purpose:** Layer 2 of the Observatory — comprehensive TensorBoard logging of scalars, histograms, beliefs, gates, and concepts.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-73 | GOOD | Comprehensive logging covering core metrics, RAP-specific signals, JEPA signals, and gate dynamics. Custom scalar layout provides organized dashboards. Graceful no-op when TensorBoard not installed. |

---

### 6.8 `embedding_projector.py` (230 LOC)

**Purpose:** Layer 4 of the Observatory — captures embeddings for TensorBoard and UMAP visualization.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-74 | GOOD | `n_neighbors` clamped to `min(15, max(2, N-1))` prevents UMAP crashes on small datasets. `plt.close(fig)` prevents matplotlib memory leaks. Graceful degradation when UMAP not installed. |

---

### 6.9 `maturity_observatory.py` (329 LOC)

**Purpose:** Layer 3 of the Observatory — tracks 5 neural maturity signals, computes conviction index, and classifies model into 5 states (DOUBT, CRISIS, LEARNING, CONVICTION, MATURE) via state machine.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-75 | GOOD | Rich, well-structured 5-state maturity classification. EMA smoothing on maturity score prevents noisy transitions. Full TensorBoard integration with scalar and text state logging. |
| NN-76 | LOW | Some maturity signals (gate_specialization, concept_focus) only work with RAP model. For legacy AdvancedCoachNN, these return 0.0, making conviction index undercount. |

---

## 7. ML CONTROL PLANE

### 7.1 `control/ml_controller.py` (121 LOC)

**Purpose:** Training lifecycle management — cooperative stop/pause/resume/throttle via `MLControlContext` token injected into training loops.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-77 | MEDIUM | `_lock` declared at line 24 but **never acquired** in any method. Vestigial. All flag mutations rely on CPython GIL for atomicity — not portable to free-threaded Python (PEP 703). |
| NN-78 | MEDIUM | `request_stop()` sets `_stop_requested = True` without clearing `_resume_event`. If training is paused when stop is requested, the thread blocks forever at `_resume_event.wait()` (line 32). Fix: `request_stop()` should also call `self._resume_event.set()`. |
| NN-79 | GOOD | `threading.Event` used for pause/resume instead of busy-wait polling (F5-15 fix). Cooperative cancellation pattern via `check_state()` at safe checkpoints. |

---

### 7.2 `control/ingest_manager.py` (258 LOC)

**Purpose:** Operator-governed ingestion controller — SINGLE/CONTINUOUS/TIMED modes, circuit breaker for stuck tasks (max 3 retries), FIFO queue processing.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-80 | MEDIUM | Event clear-after-wait race (lines 151-153): `_stop_event.clear()` called after checking `_stop_requested`. If `stop()` is called between these two lines, the event is cleared after the stop signal. Secondary guard at line 108 mitigates. |
| NN-81 | GOOD | Event-based stop signaling (F5-35), crash recovery for stuck tasks, proper session-per-call DB access. |

---

### 7.3 `control/db_governor.py` (125 LOC)

**Purpose:** Authoritative controller for database tiers with self-healing (auto-restore from .bak, empty DB creation).

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-82 | MEDIUM | `shutil.copy2()` on a live SQLite WAL-mode database (line 55) may produce a corrupt copy. Proper SQLite backup requires `sqlite3.backup()` or `VACUUM INTO`. |
| NN-83 | LOW | Orphan detection (line 80-82) planned but never implemented — dead code comment. |

---

### 7.4 `control/console.py` (494 LOC)

**Purpose:** Singleton unified control console — aggregates MLController, IngestionManager, DatabaseGovernor, ServiceSupervisor. Thread-safe singleton via `__new__` + class-level lock. Cache-aside pattern with TTL for status queries.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| NN-84 | MEDIUM | Partial initialization on failure (lines 210-216): if `MLController()` fails during init, `self.ingest_manager` exists but `self.ml_controller` does not. Subsequent calls to `start_training()` raise `AttributeError`. |
| NN-85 | MEDIUM | Auto-restart retry reset logic (lines 141-143): `retries` are reset only if the last start was >1 hour ago. If service crashes 3 times within seconds, retries are never reset because `last_start` keeps updating on each restart attempt. |
| NN-86 | LOW | `SystemState.ERROR` is a latched state with no mechanism to clear it. Once set, the system reports ERROR forever until process restart. |
| NN-87 | GOOD | Error isolation via `_safe_call()` wraps each subsystem status fetch — one subsystem failure doesn't crash the entire status report. Graceful shutdown with 5s timeout. |

---

### 7.5 `session_engine.py` (464 LOC)

**Purpose:** Tri-Daemon Architecture — Scanner (filesystem → DB queue), Digester (DB queue → match stats), Teacher (ML retraining trigger). Plus heartbeat and stdin parent-death detection.

**Findings:**

| ID | Severity | Description |
|----|----------|-------------|
| **NN-88** | **HIGH** | **Dual training invocation paths:** Session engine's teacher daemon calls `CoachTrainingManager().run_full_cycle()` without `context` parameter (line 327), while Console calls via `MLController` with context. The teacher daemon's training CANNOT be paused or stopped via the Console. Both paths can run simultaneously with no mutual exclusion. |
| NN-89 | MEDIUM | Lost-wakeup race in digester (lines 296-298): `_work_available_event.wait()` followed by `.clear()`. If `signal_work_available()` fires between these lines, the signal is lost. The 2-second timeout limits impact. |
| NN-90 | MEDIUM | Scanner daemon uses `time.sleep(1)` polling (line 254) instead of `_shutdown_event.wait(timeout=SCAN_INTERVAL)`. Teacher daemon uses `for _ in range(300): time.sleep(1)` instead of single `_shutdown_event.wait(timeout=300)`. Partially migrated from polling to event-based signaling. |
| NN-91 | LOW | `sys.path` manipulation at module load time (lines 11-13). Can cause import shadowing. |
| NN-92 | LOW | `FileHandler` added unconditionally at module load. If imported multiple times (e.g., in tests), duplicate handlers accumulate. |

---

### 7.6 ~~`training_orchestrator.py.backup` (246 LOC)~~ **FILE DELETED**

~~**Purpose:** DEPRECATED orchestrator — backup file with placeholder training methods.~~

**Status:** File has been deleted from the repository. All findings below are OBSOLETE.

| ID | Severity | Description |
|----|----------|-------------|
| ~~NN-93~~ | ~~HIGH~~ | ~~Fake decreasing loss in placeholders.~~ **OBSOLETE:** File deleted. |
| ~~NN-94~~ | ~~MEDIUM~~ | ~~Bare `except:` clause catches all exceptions.~~ **OBSOLETE:** File deleted. |
| ~~NN-95~~ | ~~LOW~~ | ~~Floating-point equality for best model detection.~~ **OBSOLETE:** File deleted. |

---

## 8. DOCUMENTATION ASSESSMENT

### 8.1 README Coverage

| Directory | README Files | Quality |
|-----------|-------------|---------|
| `backend/nn/` | EN, IT, PT | Good — covers architecture overview and model types |
| `backend/nn/advanced/` | EN, IT, PT | Good — documents experimental features |
| `backend/nn/rap_coach/` | EN, IT, PT | Good — explains RAP pipeline stages |

### 8.2 Inline Documentation Quality

| Aspect | Rating | Notes |
|--------|--------|-------|
| Design rationale | Good | F-code and P-code cross-references throughout |
| Mathematical formulas | Good | HLTV 2.0 coefficients, Z-score transforms documented |
| Known limitations | Excellent | Self-documented warnings (F3-18, F5-15, G-01, etc.) |
| Architecture diagrams | Missing | No visual diagrams of RAP pipeline or JEPA architecture |
| Hyperparameter justification | Poor | Many magic constants undocumented (1.702 sigmoid, 512 memory slots, 2.0 Z-penalty) |

---

## 9. CONSOLIDATED FINDINGS MATRIX

### 9.1 By Severity

| Severity | Count | Key Examples |
|----------|-------|-------------|
| CRITICAL | ~~3~~ 0 remaining | ~~NN-24 (SuperpositionLayer sparsity no-op), NN-35 (O(batch²) JEPATrainer), NN-39 (RAP perception temporal blindness)~~ — ALL RESOLVED |
| HIGH | ~~4~~ 2 remaining | ~~NN-09 (factory hidden_dim mismatch)~~, ~~NN-14 (silent random-weight return)~~, NN-88 (dual training paths), ~~NN-93 (fake loss in backup — file deleted)~~ |
| MEDIUM | ~~18~~ 15 remaining | NN-12, ~~NN-16~~, NN-28, NN-31-33, ~~NN-36~~, NN-40, NN-43, NN-45-46, NN-50, NN-52, NN-58, NN-61, NN-65, NN-77-78, NN-80, NN-82, NN-84-85, NN-89-90, ~~NN-94 (file deleted)~~ |
| LOW | ~~32~~ 30 remaining | Various documentation, consistency, and minor code quality issues (~~NN-25~~, ~~NN-95 (file deleted)~~ resolved) |
| GOOD | 15 | Observatory architecture, cooperative cancellation, SHAP safety, error isolation, EMA cloning |

### 9.2 By Category

| Category | CRIT | HIGH | MED | LOW | Total | Resolved |
|----------|------|------|-----|-----|-------|----------|
| Training Correctness | ~~2~~ 0 | ~~1~~ 0 | ~~5~~ 4 | 3 | ~~11~~ 7 | 4 (NN-24, NN-35, NN-36, NN-93) |
| Architecture Design | ~~1~~ 0 | ~~1~~ 0 | 5 | ~~6~~ 5 | ~~13~~ 10 | 3 (NN-39, NN-09, NN-25) |
| Checkpoint/Persistence | 0 | ~~1~~ 0 | ~~1~~ 0 | 2 | ~~4~~ 2 | 2 (NN-14, NN-16) |
| Operational Control | 0 | 1 | ~~5~~ 4 | ~~4~~ 3 | ~~10~~ 8 | 2 (NN-94, NN-95) |
| Performance | 0 | 0 | 2 | 2 | 4 | 0 |
| Code Quality | 0 | 0 | 0 | 15 | 15 | 0 |

### 9.3 Complete Finding Registry

| ID | File | Severity | Title |
|----|------|----------|-------|
| NN-01 | config.py | LOW | Global device cache not thread-safe |
| NN-02 | config.py | GOOD | Multi-GPU selection with integrated GPU de-prioritization |
| NN-03 | config.py | GOOD | RAP_POSITION_SCALE well-documented |
| NN-04 | model.py | LOW | Auto-unsqueeze masks batch dimension errors |
| NN-05 | model.py | LOW | Role bias limits gate expressiveness |
| NN-06 | model.py | GOOD | Dual initialization for backward compatibility |
| NN-07 | model.py | GOOD | Optional imports with graceful fallback |
| NN-08 | dataset.py | GOOD | Clean minimal Dataset implementation |
| ~~NN-09~~ | factory.py | ~~HIGH~~ | ~~Hidden_dim=64 default vs config HIDDEN_DIM=128~~ **RESOLVED** |
| NN-10 | factory.py | LOW | RAP output_dim=10 undocumented |
| NN-11 | factory.py | GOOD | Clear model type enumeration |
| NN-12 | evaluate.py | MEDIUM | Only 4/25 output dimensions used |
| NN-13 | evaluate.py | LOW | Zero-vector SHAP baseline |
| ~~NN-14~~ | persistence.py | ~~HIGH~~ | ~~Silent random-weight model return~~ **RESOLVED** |
| NN-15 | persistence.py | GOOD | weights_only=True + StaleCheckpointError |
| ~~NN-16~~ | ema.py | ~~MEDIUM~~ | ~~apply_shadow shares tensor references~~ **RESOLVED** |
| NN-17 | ema.py | GOOD | state_dict returns cloned tensors |
| NN-18 | early_stopping.py | GOOD | Textbook implementation |
| NN-19 | role_head.py | GOOD | Complete self-contained pipeline |
| NN-20 | role_head.py | LOW | Full-batch training not scalable |
| NN-21 | role_head.py | GOOD | Role anchor merging domain-correct |
| NN-22 | win_probability_trainer.py | LOW | Adam vs AdamW inconsistency |
| NN-23 | win_probability_trainer.py | LOW | Duplicated feature list |
| ~~NN-24~~ | superposition.py | ~~CRITICAL~~ | ~~Sparsity loss uses detached tensors (no-op)~~ **RESOLVED** |
| ~~NN-25~~ | superposition.py | ~~LOW~~ | ~~Device mismatch for zero tensor~~ **RESOLVED** |
| NN-26 | superposition.py | GOOD | Gate statistics observability |
| NN-27 | jepa_model.py | GOOD | VL-JEPA Selective Decoding optimization |
| NN-28 | jepa_model.py | MEDIUM | Un-vectorized label_tick loop |
| NN-29 | jepa_model.py | GOOD | Dual labeling modes for G-01 fix |
| NN-30 | jepa_model.py | GOOD | 16 frozen concept taxonomy |
| NN-31 | jepa_train.py | MEDIUM | Variable-length slices in Dataset |
| NN-32 | jepa_train.py | MEDIUM | Tiled sequences create trivial loss |
| NN-33 | jepa_train.py | MEDIUM | ZeroDivisionError on empty dataloader |
| NN-34 | jepa_train.py | GOOD | weights_only=True for safe loading |
| ~~NN-35~~ | jepa_trainer.py | ~~CRITICAL~~ | ~~O(batch²) negative sampling~~ **RESOLVED** |
| ~~NN-36~~ | jepa_trainer.py | ~~MEDIUM~~ | ~~Optimizer includes target encoder params~~ **RESOLVED** |
| NN-37 | jepa_trainer.py | LOW | Hardcoded CosineAnnealingLR T_max |
| NN-38 | jepa_trainer.py | LOW | ConceptLabeler re-instantiated per step |
| ~~NN-39~~ | rap_coach/model.py | ~~CRITICAL~~ | ~~Perception temporal blindness~~ **RESOLVED** |
| NN-40 | rap_coach/model.py | MEDIUM | Fresh hidden state loses temporal continuity |
| NN-41 | rap_coach/model.py | LOW | Unbounded position delta |
| NN-42 | rap_coach/model.py | GOOD | Explicit gate_weights param (thread-safe) |
| NN-43 | rap_coach/perception.py | MEDIUM | ResNet stack ignores block structure |
| NN-44 | rap_coach/perception.py | LOW | Hardcoded 128-dim output |
| NN-45 | rap_coach/memory.py | MEDIUM | AutoNCP random wiring breaks checkpoint portability |
| NN-46 | rap_coach/memory.py | MEDIUM | Hopfield O(seq²) complexity |
| NN-47 | rap_coach/memory.py | LOW | NCP units ratio hardcoded |
| NN-48 | rap_coach/strategy.py | LOW | ContextualAttention dead code |
| NN-49 | rap_coach/strategy.py | GOOD | gate_weights returned for external loss |
| NN-50 | rap_coach/pedagogy.py | MEDIUM | Utility need detection poorly motivated |
| NN-51 | rap_coach/pedagogy.py | LOW | squeeze() scalar broadcasting edge case |
| NN-52 | rap_coach/communication.py | MEDIUM | AttributeError on list fallback |
| NN-53 | rap_coach/communication.py | LOW | Naive index-to-topic cycling |
| NN-54 | rap_coach/communication.py | GOOD | Template injection impossible |
| NN-55 | chronovisor_scanner.py | HIGH | Eager initialization blocks testing |
| NN-56 | chronovisor_scanner.py | LOW | Hardcoded session name |
| NN-57 | chronovisor_scanner.py | LOW | NaN propagation in deltas |
| NN-58 | rap_coach/trainer.py | MEDIUM | Hardcoded loss weights |
| NN-59 | rap_coach/trainer.py | LOW | Hardcoded Z-penalty weight |
| NN-60 | skill_model.py | LOW | Falsy 0 treated as missing |
| NN-61 | train.py | MEDIUM | Deterministic negative sampling |
| NN-62 | train.py | LOW | Duplicated MIN_TRAINING_SAMPLES |
| NN-63 | train.py | LOW | Private method access violation |
| NN-64 | train.py | GOOD | Comprehensive multi-model training |
| NN-65 | train_pipeline.py | MEDIUM | Deprecated but still importable |
| NN-66 | training_config.py | LOW | RAP-specific default for all models |
| NN-67 | training_config.py | LOW | Mutable singleton config |
| NN-68 | training_controller.py | LOW | Conservative monthly quota |
| NN-69 | training_controller.py | LOW | Hardcoded normalization baselines |
| NN-70 | training_controller.py | GOOD | Fail-safe on error |
| NN-71 | training_monitor.py | LOW | Non-atomic file writes |
| NN-72 | training_callbacks.py | GOOD | Error isolation per callback |
| NN-73 | tensorboard_callback.py | GOOD | Comprehensive TensorBoard integration |
| NN-74 | embedding_projector.py | GOOD | UMAP crash prevention |
| NN-75 | maturity_observatory.py | GOOD | 5-state maturity classification |
| NN-76 | maturity_observatory.py | LOW | Maturity signals RAP-only |
| NN-77 | ml_controller.py | MEDIUM | Vestigial lock never acquired |
| NN-78 | ml_controller.py | MEDIUM | Stop doesn't unblock paused training |
| NN-79 | ml_controller.py | GOOD | Event-based pause/resume |
| NN-80 | ingest_manager.py | MEDIUM | Event clear-after-wait race |
| NN-81 | ingest_manager.py | GOOD | Crash recovery for stuck tasks |
| NN-82 | db_governor.py | MEDIUM | shutil.copy2 on live WAL database |
| NN-83 | db_governor.py | LOW | Orphan detection unimplemented |
| NN-84 | console.py | MEDIUM | Partial initialization on failure |
| NN-85 | console.py | MEDIUM | Auto-restart retry reset logic flawed |
| NN-86 | console.py | LOW | Latched ERROR state |
| NN-87 | console.py | GOOD | Error isolation via _safe_call |
| NN-88 | session_engine.py | HIGH | Dual training paths, no mutual exclusion |
| NN-89 | session_engine.py | MEDIUM | Lost-wakeup race in digester |
| NN-90 | session_engine.py | MEDIUM | Incomplete polling→event migration |
| NN-91 | session_engine.py | LOW | sys.path manipulation at load time |
| NN-92 | session_engine.py | LOW | FileHandler duplication on re-import |
| ~~NN-93~~ | ~~orchestrator.backup~~ | ~~HIGH~~ | ~~Fake decreasing loss in placeholders~~ **OBSOLETE: file deleted** |
| ~~NN-94~~ | ~~orchestrator.backup~~ | ~~MEDIUM~~ | ~~Bare except, print() instead of logging~~ **OBSOLETE: file deleted** |
| ~~NN-95~~ | ~~orchestrator.backup~~ | ~~LOW~~ | ~~Float equality for best model detection~~ **OBSOLETE: file deleted** |

---

## 10. RECOMMENDATIONS

### 10.1 Priority 1 — Critical (Fix Before Training) — ALL RESOLVED

| ID | Fix | Effort | Status |
|----|-----|--------|--------|
| ~~NN-24~~ | ~~Store live (non-detached) gate tensor for `gate_sparsity_loss()`.~~ | ~~30 min~~ | **RESOLVED** |
| ~~NN-35~~ | ~~Batch all negatives into a single forward pass.~~ | ~~1 hour~~ | **RESOLVED** |
| ~~NN-39~~ | ~~Process view frames per-timestep through the CNN.~~ | ~~2 hours~~ | **RESOLVED** |

### 10.2 Priority 2 — High (Fix Before Release) — 3/4 RESOLVED

| ID | Fix | Effort | Status |
|----|-----|--------|--------|
| ~~NN-09~~ | ~~Change factory.py default to `kwargs.get("hidden_dim", HIDDEN_DIM)`.~~ | ~~15 min~~ | **RESOLVED** |
| ~~NN-14~~ | ~~Raise `FileNotFoundError` when no checkpoint exists.~~ | ~~15 min~~ | **RESOLVED** |
| NN-88 | Add mutual exclusion between Console-initiated and SessionEngine-initiated training. Either pass `MLControlContext` to session engine's teacher, or use a global training lock. | 2 hours | OPEN |
| ~~NN-93~~ | ~~Delete `training_orchestrator.py.backup`.~~ | ~~5 min~~ | **RESOLVED (file deleted)** |

### 10.3 Priority 3 — Medium (Next Sprint) — 2/8 RESOLVED

| ID | Fix | Effort | Status |
|----|-----|--------|--------|
| ~~NN-16~~ | ~~Use `.clone()` instead of direct assignment in `apply_shadow()`.~~ | ~~15 min~~ | **RESOLVED** |
| ~~NN-36~~ | ~~Exclude target encoder parameters from optimizer.~~ | ~~30 min~~ | **RESOLVED** |
| NN-43 | Implement proper per-stage ResNet blocks with increasing channels and stride-2 transitions, or document that the flat architecture is intentional. | 2 hours | OPEN |
| NN-45 | Seed the AutoNCP wiring with `GLOBAL_SEED` for reproducibility across instances. | 30 min | OPEN |
| NN-55 | Add lazy initialization to `ChronovisorScanner` — defer model loading until `scan_match()` is first called. | 1 hour | OPEN |
| NN-61 | Use `random.sample(candidates, num_negatives)` instead of `candidates[:num_negatives]` for diverse negative sampling. | 15 min | OPEN |
| NN-78 | Add `self._resume_event.set()` to `request_stop()` so paused training unblocks on stop request. | 5 min | OPEN |
| NN-82 | Replace `shutil.copy2()` with `sqlite3.backup()` for safe WAL-mode database copies. | 30 min | OPEN |

### 10.4 Priority 4 — Low (Technical Debt)

| Focus Area | Actions |
|-----------|---------|
| Magic constants | Extract all undocumented constants to config.py or training_config.py with rationale comments |
| Dead code | Remove ContextualAttention (NN-48), ~~delete or archive training_orchestrator.py.backup (NN-93)~~ **(DONE)**, delete orphan detection comment (NN-83) |
| Consistency | Standardize on AdamW everywhere, centralize MIN_TRAINING_SAMPLES, unify session name strings |
| Checkpoint versioning | Add architecture version tag to checkpoint format (model type, hidden_dim, num_experts, etc.) |
| Testing | Add unit tests for SuperpositionLayer sparsity loss gradient flow, EMA apply/restore cycle, and factory-created model dimension compatibility |

---

## APPENDICES

### Appendix A: Model Architecture Comparison

| Feature | AdvancedCoachNN | JEPA | VL-JEPA | RAP Coach |
|---------|----------------|------|---------|-----------|
| Input | 25-dim metadata | 25-dim metadata | 25-dim + visual | Visual + metadata |
| Encoder | LSTM (2-layer) | Linear+LN+GELU | Linear+LN+GELU+CNN | ResNet CNN |
| Memory | None | LSTM (2-layer) | LSTM (2-layer) | LTC + Hopfield |
| Expert Count | 3 | 3 | 3 | 4 |
| Gating | Softmax + role bias | Softmax | Softmax + selective | SuperpositionLayer |
| Output | tanh 25-dim | tanh 25-dim | tanh 25-dim | 10-dim + 3D pos + value |
| Params (est.) | ~50K | ~200K | ~300K | ~500K |
| Training Mode | Supervised | Self-supervised → Supervised | Self-supervised → Concept | Multi-task (4 losses) |

### Appendix B: Training Infrastructure Layer Map

```
Layer 4: EmbeddingProjector (UMAP visualization)
Layer 3: MaturityObservatory (5-state classification)
Layer 2: TensorBoardCallback (scalars, histograms, gates)
Layer 1: TrainingCallbacks (7 lifecycle hooks, error isolation)
───────────────────────────────────────────────────────
train.py / jepa_trainer.py / rap_trainer.py
  ↕ MLControlContext (stop/pause/resume/throttle)
MLController → CoachTrainingManager.run_full_cycle()
Console → MLController (with context)
SessionEngine Teacher → CoachTrainingManager (WITHOUT context) ← NN-88
```

### Appendix C: Checkpoint Fallback Chain

```
1. ~/.cs2analyzer/models/{user_id}/{model}.pt     (user-specific local)
2. ~/.cs2analyzer/models/global/{model}.pt          (global local)
3. {install_dir}/models/{user_id}/{model}.pt        (user-specific bundled)
4. {install_dir}/models/global/{model}.pt           (global bundled)
5. Raise FileNotFoundError ← NN-14 RESOLVED        (was: silent failure)
```

---

*End of Report 5/8*
