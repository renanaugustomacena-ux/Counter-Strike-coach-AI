# Chapter 6: RAP Coach, Knowledge Layer, and Coaching Engine

This chapter provides an exhaustive reference for three tightly coupled subsystems of the Macena CS2 Analyzer: the **RAP Coach** neural architecture (both the deprecated shim layer and the canonical experimental implementation), the **Knowledge** layer (experience banking, knowledge graph, RAG retrieval, vector indexing, pro demo mining), and the **Coaching** layer (correction engine, explainability, hybrid engine, longitudinal analysis, NN refinement, pro bridge, token resolver). Every class, function, constant, and design mechanism is documented.

---

## Table of Contents

1. [RAP Coach -- Main Shim Layer](#1-rap-coach----main-shim-layer)
2. [RAP Coach -- Experimental (Canonical Implementations)](#2-rap-coach----experimental-canonical-implementations)
   - 2.1 [Package Init](#21-package-init)
   - 2.2 [Perception (`perception.py`)](#22-perception-perceptionpy)
   - 2.3 [Memory (`memory.py`)](#23-memory-memorypy)
   - 2.4 [Strategy (`strategy.py`)](#24-strategy-strategypy)
   - 2.5 [Model (`model.py`)](#25-model-modelpy)
   - 2.6 [Pedagogy (`pedagogy.py`)](#26-pedagogy-pedagogypy)
   - 2.7 [Communication (`communication.py`)](#27-communication-communicationpy)
   - 2.8 [Chronovisor Scanner (`chronovisor_scanner.py`)](#28-chronovisor-scanner-chronovisor_scannerpy)
   - 2.9 [Trainer (`trainer.py`)](#29-trainer-trainerpy)
   - 2.10 [Test Infrastructure](#210-test-infrastructure)
3. [Knowledge Layer](#3-knowledge-layer)
   - 3.1 [Package Init](#31-package-init)
   - 3.2 [Experience Bank (`experience_bank.py`)](#32-experience-bank-experience_bankpy)
   - 3.3 [Knowledge Graph (`graph.py`)](#33-knowledge-graph-graphpy)
   - 3.4 [RAG Knowledge (`rag_knowledge.py`)](#34-rag-knowledge-rag_knowledgepy)
   - 3.5 [Vector Index (`vector_index.py`)](#35-vector-index-vector_indexpy)
   - 3.6 [Pro Demo Miner (`pro_demo_miner.py`)](#36-pro-demo-miner-pro_demo_minerpy)
   - 3.7 [Round Utilities (`round_utils.py`)](#37-round-utilities-round_utilspy)
   - 3.8 [Init Knowledge Base (`init_knowledge_base.py`)](#38-init-knowledge-base-init_knowledge_basepy)
4. [Knowledge Base (Help System)](#4-knowledge-base-help-system)
5. [Coaching Layer](#5-coaching-layer)
   - 5.1 [Package Init](#51-package-init)
   - 5.2 [Correction Engine (`correction_engine.py`)](#52-correction-engine-correction_enginepy)
   - 5.3 [Explainability (`explainability.py`)](#53-explainability-explainabilitypy)
   - 5.4 [Hybrid Engine (`hybrid_engine.py`)](#54-hybrid-engine-hybrid_enginepy)
   - 5.5 [Longitudinal Engine (`longitudinal_engine.py`)](#55-longitudinal-engine-longitudinal_enginepy)
   - 5.6 [NN Refinement (`nn_refinement.py`)](#56-nn-refinement-nn_refinementpy)
   - 5.7 [Pro Bridge (`pro_bridge.py`)](#57-pro-bridge-pro_bridgepy)
   - 5.8 [Token Resolver (`token_resolver.py`)](#58-token-resolver-token_resolverpy)
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)

---

## 1. RAP Coach -- Main Shim Layer

**Location:** `Programma_CS2_RENAN/backend/nn/rap_coach/`

The entire main `rap_coach/` package is a **backward-compatibility shim layer** established during the P9-01 consolidation. Every module re-exports symbols from the canonical implementation under `backend/nn/experimental/rap_coach/`. This design allows existing import paths to continue working while the canonical code lives in the experimental namespace.

### 1.1 `__init__.py`

- **Purpose:** Backward-compatibility shim (P9-01).
- **Mechanism:** Re-exports nothing directly; serves as the package marker. Docstring directs readers to `experimental/rap_coach/` for the canonical implementations.
- **Design note:** This shim exists so that code written before P9-01 that imports from `backend.nn.rap_coach` continues to resolve without modification.

### 1.2 `chronovisor_scanner.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.chronovisor_scanner`:
  - `ChronovisorScanner` -- multi-scale critical moment detector
  - `CriticalMoment` -- dataclass for a detected moment
  - `ScanResult` -- dataclass for scan success/failure plus results
  - `ScaleConfig` -- dataclass for temporal scale parameters
  - `ANALYSIS_SCALES` -- list of three predefined scale configurations

### 1.3 `communication.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.communication`:
  - `RAPCommunication` -- pedagogical feedback generator

### 1.4 `memory.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.memory`:
  - `RAPMemory` -- LTC + Hopfield recurrent belief state module
  - (Also transitively makes `RAPMemoryLite` accessible from the experimental module)

### 1.5 `model.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.model`:
  - `RAPCoachModel` -- the complete RAP Coach neural network
  - `RAP_POSITION_SCALE` -- position normalization constant

### 1.6 `pedagogy.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.pedagogy`:
  - `RAPPedagogy` -- value critic and skill adaptation module
  - `CausalAttributor` -- 5-concept causal attribution head

### 1.7 `perception.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.perception`:
  - `RAPPerception` -- multi-stream visual encoder (view, map, motion)
  - `ResNetBlock` -- residual convolution block used by perception

### 1.8 `skill_model.py`

- **EXCEPTION to P9-01 pattern.** This shim does NOT point to `experimental/rap_coach/`. Instead it re-exports from `backend.processing.skill_assessment`:
  - `SkillAxes` -- enum of 5 skill dimensions
  - `SkillLatentModel` -- latent skill representation model
- **Design note:** `SkillAxes` and `SkillLatentModel` are general-purpose processing constructs, not RAP-specific. Their placement in the `rap_coach` shim is purely for import convenience.

### 1.9 `strategy.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.strategy`:
  - `RAPStrategy` -- Mixture-of-Experts strategy module

### 1.10 `trainer.py`

- **Re-exports from** `backend.nn.experimental.rap_coach.trainer`:
  - `RAPTrainer` -- multi-loss training orchestrator

---

## 2. RAP Coach -- Experimental (Canonical Implementations)

**Location:** `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/`

This is the canonical, research-grade implementation of the RAP (Recurrent Attentive Pedagogy) Coach model. It implements a full neural coaching pipeline: visual perception (ResNet CNN) -> temporal memory (LTC + Hopfield) -> strategic decision-making (Mixture-of-Experts) -> pedagogical output (value critic + causal attribution) -> human communication (template-based feedback).

### 2.1 Package Init

**File:** `backend/nn/experimental/__init__.py`

- Package docstring: "Contains research-grade models. Enable via `USE_RAP_MODEL=True`."
- No exports. The experimental namespace is opt-in.

**File:** `backend/nn/experimental/rap_coach/__init__.py`

- Documents the P9-01 migration from `backend/nn/rap_coach/`.
- Module-level `__all__` list (if present) controls the public API surface.

### 2.2 Perception (`perception.py`)

**File:** `backend/nn/experimental/rap_coach/perception.py`

The perception layer is a multi-stream CNN that encodes three visual input modalities into a unified 128-dimensional spatial feature vector.

#### Class: `ResNetBlock(nn.Module)`

A standard pre-activation residual block.

**Constructor Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `in_channels` | int | Input channel count |
| `out_channels` | int | Output channel count |

**Architecture:**
- `conv1`: Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
- `bn1`: BatchNorm2d(out_channels)
- `conv2`: Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
- `bn2`: BatchNorm2d(out_channels)
- `shortcut`: Identity if in_channels == out_channels, otherwise Conv2d(in_channels, out_channels, 1) + BatchNorm2d

**Method: `forward(x)`**
- Computes: identity + F(x) where F = bn2(conv2(relu(bn1(conv1(x)))))
- Applies ReLU after residual addition.

#### Class: `RAPPerception(nn.Module)`

Three parallel CNN backbones process different visual modalities.

**Constructor Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `view_channels` | int | 3 | Channels in first-person view |
| `map_channels` | int | 3 | Channels in minimap overlay |
| `motion_channels` | int | 3 | Channels in motion/optical-flow map |

**Architecture:**

1. **View backbone** (`view_backbone`): Sequential with block counts [1, 2, 2, 1]:
   - Conv2d(3, 64, 3, padding=1) -> BatchNorm2d(64) -> ReLU
   - 1x ResNetBlock(64, 64) -> MaxPool2d(2)
   - 2x ResNetBlock(64, 64) -> MaxPool2d(2)
   - 2x ResNetBlock(64, 64) -> MaxPool2d(2)
   - 1x ResNetBlock(64, 64)
   - Output: 64 channels
   - `view_pool`: AdaptiveAvgPool2d(1, 1) -> 64-dim vector

2. **Map backbone** (`map_backbone`): Sequential with block counts [2, 2]:
   - Conv2d(3, 32, 3, padding=1) -> BatchNorm2d(32) -> ReLU
   - 2x ResNetBlock(32, 32) -> MaxPool2d(2)
   - 2x ResNetBlock(32, 32)
   - Output: 32 channels
   - `map_pool`: AdaptiveAvgPool2d(1, 1) -> 32-dim vector

3. **Motion convolutions** (`motion_conv`): Sequential:
   - Conv2d(3, 16, 3, padding=1) -> ReLU -> MaxPool2d(2)
   - Conv2d(16, 32, 3, padding=1) -> ReLU -> MaxPool2d(2)
   - Output: 32 channels, global average pooled

**Method: `forward(view, minimap, motion)`**
- Input shapes: each is (B, C, H, W) where H and W are arbitrary (pools handle it).
- Returns: `torch.cat([z_view, z_map, z_motion], dim=-1)` of shape (B, 128).
  - z_view: 64-dim
  - z_map: 32-dim
  - z_motion: 32-dim
- Total perception output dimension: **128**.

### 2.3 Memory (`memory.py`)

**File:** `backend/nn/experimental/rap_coach/memory.py`

The memory layer resolves POMDP (Partially Observable Markov Decision Process) partial observability via Bayesian filtering in latent space, combining Liquid Time-Constant (LTC) neurons for continuous-time dynamics with Hopfield Associative Memory for long-term pattern recall.

#### Module-Level Flag

```python
_RAP_DEPS_AVAILABLE: bool
```
- `True` if both `ncps` and `hflayers` packages are importable.
- `False` triggers graceful degradation (use `RAPMemoryLite` instead).
- When `False`, the sentinel values `LTC = None`, `AutoNCP = None`, `HopfieldLayer = None` are set.

#### Class: `RAPMemory(nn.Module)`

**Docstring:** "Recurrent Belief State Module (Generation 2: Liquid Mind)."

**Constructor Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `perception_dim` | int | -- | Dimension of perception output (128) |
| `metadata_dim` | int | -- | Dimension of metadata features (25) |
| `hidden_dim` | int | 256 | Hidden state dimension |

**Guard:** Raises `ImportError` if `_RAP_DEPS_AVAILABLE` is `False`.

**Architecture:**

1. **LTC Layer (Liquid Time-Constant Neurons):**
   - `input_dim = perception_dim + metadata_dim` (128 + 25 = 153)
   - `ncp_units = hidden_dim * 2 = 512` total neurons
   - `ncp_output = int(ncp_units * 0.3) = 154` motor neurons (RAP-AUDIT-07)
   - **Neuron distribution** (per Lechner et al. 2020 recommendation):
     - Motor: 154 (30%) -- outputs
     - Command: ~143 (28%) -- processing
     - Inter: ~215 (42%) -- interneurons
   - Previous 0.5 ratio was suboptimal: too many motor neurons, too few inter/command.
   - **Deterministic wiring** (NN-45 + NN-MEM-02): Both numpy and torch RNG states are saved, seeded to 42, then restored after `AutoNCP` construction. This ensures checkpoint-portable, reproducible NCP connectivity graphs.
   - `self.wiring = AutoNCP(units=512, output_size=154)`
   - `self.ltc = LTC(input_dim=153, wiring, batch_first=True)`

2. **LTC ODE Monkey-Patch** (RAP-LTC-FIX, 2026-05-06):
   - **Bug:** In `ncps` library (both v1.0.1 and v0.0.7), `LTCCell._ode_solver` performs `cm / (elapsed_time / ode_unfolds)` where `cm` has shape `(state_size,) = (512,)` and `elapsed_time` (after `.squeeze()`) has shape `(B,)`. Division of `(512,)` by `(B,)` fails unless `state_size == B`.
   - **Fix:** Wraps `_original_ode_solver` with `_patched_ode_solver` that unsqueezes 1-D `elapsed_time` from `(B,)` to `(B, 1)`, enabling proper broadcasting to `(B, state_size)`.
   - This is a critical correctness fix -- without it, variable batch sizes crash at runtime.

3. **LTC Projection:**
   - `self.ltc_projection = nn.Linear(ncp_output=154, hidden_dim=256)` (RAP-AUDIT-07)
   - Bridges the NCP output dimension back to the 256-dim contract expected by all downstream layers.

4. **Hopfield Layer (Associative Memory):**
   - Uses `HopfieldLayer` (NOT `Hopfield`) for learnable prototype storage (RAP-AUDIT-03).
   - `HopfieldLayer` has persistent `nn.Parameter` lookup_weights (the "Prototype Rounds").
   - Configuration: `input_size=256`, `output_size=256`, `num_heads=4`, `quantity=32` (32 learnable prototypes), `trainable=True`.
   - Parameter count: 32 prototypes x 256-dim = 8,192 parameters.
   - Storage capacity: O(exp(d)) per Ramsauer et al. (ICLR 2021).
   - **Activation guard** (NN-MEM-01 + RAP-M-04):
     - `_hopfield_trained: bool = False` -- tracks whether prototypes are meaningful.
     - `_training_forward_count: int = 0` -- counts training-mode forward passes.
     - Hopfield activates only after >= 2 training forward passes, ensuring at least one backward+step has shaped the stored patterns.
     - Before activation, `forward()` substitutes `torch.zeros_like(ltc_out)` for Hopfield output.

5. **Belief Head (State Reconstruction):**
   - `self.belief_head = nn.Sequential(Linear(256, 256), SiLU(), Linear(256, 64))`
   - Outputs a 64-dimensional belief vector representing latent game state properties (enemy strategy, rotation phase, etc.).
   - SiLU activation chosen for better gradient flow than ReLU.

**Method: `forward(x, hidden=None, timespans=None)`**

| Parameter | Shape | Description |
|-----------|-------|-------------|
| `x` | (B, T, input_dim) | Sequential observation features |
| `hidden` | optional | Previous hidden state for continuity |
| `timespans` | (B, T) optional | Inter-tick time intervals in seconds |

- **Step 1:** LTC processes temporal sequence with optional real-time intervals -> `ltc_out` (B, T, 154), then projected to (B, T, 256).
- **Step 2:** Hopfield recall (if trained) or zero tensor.
- **Step 3:** Residual combination: `combined_state = ltc_out + mem_out`.
- **Step 4:** Belief extraction: `belief = belief_head(combined_state)` -> (B, T, 64).
- **Step 5:** Training-mode activation counting for Hopfield gate.
- **Returns:** `(combined_state[B,T,256], belief[B,T,64], hidden)`.

**RAP-AUDIT-05 note:** Without timespans, LTC treats every tick interval as 1.0s, losing the continuous-time advantage over LSTM. With real timespans, the ODE solver adapts membrane capacitance: `cm_t = cm / (elapsed_time / ode_unfolds)`.

**Method: `initialize_prototypes(embeddings: torch.Tensor) -> None`**

Phase 5B initialization. K-means clustering (K=32, 10 iterations) of collected LTC output embeddings, then copies centroids into the Hopfield prototype parameters. Reduces warmup time from random initialization.

- Guards: Returns early if N < K (fewer embeddings than prototypes).
- Finds the Hopfield parameter matching centroid shape and copies data.
- Sets `_hopfield_trained = True` on success.
- Decorated with `@torch.no_grad()`.

**Method: `load_state_dict(state_dict, strict=True, assign=False)`**

Override that additionally sets `_hopfield_trained = True` after loading, since checkpoint prototypes are pre-shaped by training.

#### Class: `RAPMemoryLite(nn.Module)`

Lightweight LSTM-based drop-in replacement for `RAPMemory` when `ncps`/`hflayers` are unavailable.

**Constructor Parameters:**
Same as `RAPMemory`: `perception_dim`, `metadata_dim`, `hidden_dim=256`.

**Architecture:**
- `self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)` where input_dim = perception_dim + metadata_dim = 153.
- `self.belief_head = nn.Sequential(Linear(256, 256), SiLU(), Linear(256, 64))` -- identical structure to `RAPMemory`.

**Method: `forward(x, hidden=None, timespans=None)`**
- `timespans` is accepted but **ignored** (LSTM has no continuous-time dynamics).
- Returns: `(lstm_out[B,T,256], belief[B,T,64], hidden)`.
- Same output contract as `RAPMemory`.

### 2.4 Strategy (`strategy.py`)

**File:** `backend/nn/experimental/rap_coach/strategy.py`

Implements a **Top-2 Sparse Mixture-of-Experts** routing layer (Shazeer/Fedus architecture) where each expert is a FiLM-conditioned `SuperpositionLayer` for context-adaptive feature processing.

#### Class: `RAPStrategy(nn.Module)`

**Class Constants:**
```python
TOP_K = 2          # Number of experts selected per input (Top-2 routing)
```

**Constructor Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hidden_dim` | int | -- | Input feature dimension (256) |
| `output_dim` | int | -- | Strategy output dimension |
| `context_dim` | int | -- | Context vector dimension for FiLM conditioning (89) |
| `num_experts` | int | 4 | Number of expert networks |

**Architecture:**

1. **Expert networks** (`self.experts`): `nn.ModuleList` of 4 experts, each:
   - `SuperpositionLayer(hidden_dim, hidden_dim // 2, context_dim)` -> ReLU -> `Linear(hidden_dim // 2, output_dim)`
   - FiLM conditioning allows each expert to be context-adaptive, modulating its behavior based on the metadata+belief context vector.

2. **Gate network** (`self.gate`):
   - `Linear(hidden_dim, num_experts)` -- produces 4 logits.
   - Full softmax over all experts produces `gate_probs` (for loss computation).
   - Top-2 selection extracts the two highest-probability experts.
   - Selected weights are **renormalized** to sum to 1.0.

**Method: `forward(x, context)`**

| Parameter | Shape | Description |
|-----------|-------|-------------|
| `x` | (B, hidden_dim) | Input features from memory |
| `context` | (B, context_dim) | Fused metadata + belief context (89-dim) |

**Routing mechanism:**
1. Compute `gate_logits = self.gate(x)` -> (B, 4).
2. `gate_probs = softmax(gate_logits)` -- full distribution for sparsity loss.
3. `top2_indices = topk(gate_logits, k=2)` -- select two experts.
4. Renormalize the two selected weights to sum to 1.0.
5. For each selected expert `i`:
   - Create batch mask `mask_i = (indices contain i)`.
   - If any samples route to expert `i`, compute `expert_i(x[mask], context[mask])`.
   - Accumulate: `output[mask] += weight_i * expert_output`.
6. **Returns:** `(final_output[B, output_dim], gate_probs[B, 4])`.

**Design notes:**
- Only 2 of 4 experts execute per sample (computational efficiency).
- Batch masking avoids wasted computation on unselected experts.
- The full `gate_probs` tensor is returned for entropy-based sparsity regularization in the trainer.

### 2.5 Model (`model.py`)

**File:** `backend/nn/experimental/rap_coach/model.py`

The top-level model that composes perception, memory, strategy, and pedagogy into a single forward pass.

#### Module-Level Constants

```python
RAP_POSITION_SCALE  # Position normalization constant (exported)
```

#### Class: `RAPCoachModel(nn.Module)`

**Constructor Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `metadata_dim` | int | METADATA_DIM (25) | Metadata feature count |
| `output_dim` | int | OUTPUT_DIM | Strategy output dimension |
| `context_gate_l1_weight` | float | from HeuristicConfig or 1e-4 | L1 regularization weight for context gate |

**Architecture (submodule composition):**

1. `self.perception = RAPPerception()` -- outputs 128-dim spatial features (perception_dim=128).
2. `self.memory` = `RAPMemory(128, metadata_dim)` or `RAPMemoryLite(128, metadata_dim)` -- selected based on `_RAP_DEPS_AVAILABLE`. Hidden_dim=256.
3. `self.strategy = RAPStrategy(hidden_dim=256, output_dim, context_dim=metadata_dim + belief_dim = 25 + 64 = 89)`.
4. `self.pedagogy = RAPPedagogy(hidden_dim=256)`.
5. `self.causal = CausalAttributor(hidden_dim=256)`.
6. `self.position_head = nn.Linear(256, 3)` -- predicts optimal (dx, dy, dz) position delta.

**Method: `forward(view, minimap, motion, metadata, timespans=None, skill_vec=None)`**

Supports two input modes:
- **4D input** `[B, C, H, W]`: Single-frame mode. Processes one visual frame per batch item.
- **5D input** `[B, T, C, H, W]`: Temporal sequence mode (NN-39). Iterates over T timesteps, each through perception, then processes the temporal sequence through memory.

**Forward pass steps:**
1. **Shape assertions** (P-X-02): Validates input tensor dimensions.
2. **Perception:** For each timestep, `perception(view_t, map_t, motion_t)` -> 128-dim spatial features.
3. **Concatenation:** `spatial_features ++ metadata` -> (B, T, 153).
4. **Memory:** `memory(concatenated, hidden, timespans)` -> combined_state (B, T, 256), belief (B, T, 64), hidden.
5. **Context fusion** (RAP-AUDIT-09): `context = cat(metadata, belief[:, -1, :])` -> 89-dim context vector.
6. **Strategy:** `strategy(combined_state[:, -1, :], context)` -> advice_probs, gate_weights.
7. **Pedagogy:** `pedagogy(combined_state[:, -1, :], skill_vec)` -> value_estimate. Optional skill_vec validation (NN-RM-01).
8. **Position head:** `position_head(combined_state[:, -1, :])` -> optimal_pos (B, 3).
9. **Causal attribution:** `causal.diagnose(combined_state[:, -1, :])` -> concept_weights.

**Returns:** Dictionary with 7 keys:
```python
{
    "advice_probs":    Tensor[B, output_dim],   # Strategy output
    "value_estimate":  Tensor[B, 1],            # Value critic estimate
    "gate_weights":    Tensor[B, 4],            # MoE gate probabilities
    "optimal_pos":     Tensor[B, 3],            # Position delta [dx, dy, dz]
    "belief":          Tensor[B, T, 64],        # Full belief sequence
    "concept_weights": Tensor[B, 5],            # Causal attribution per concept
    "hidden":          hidden_state,            # Memory hidden state for next call
}
```

**Method: `compute_sparsity_loss(gate_weights) -> Tensor`**

Entropy-based sparsity regularization for MoE gate specialization (RAP-AUDIT-04).

- Formula: `H(p) = -sum(p * log(p + eps))` where p = gate_weights (softmaxed).
- Range: [0, log(num_experts)] = [0, log(4)] = [0, 1.386].
- Higher entropy = more uniform routing = penalized.
- Returns 0.0 if gate_weights is None.

### 2.6 Pedagogy (`pedagogy.py`)

**File:** `backend/nn/experimental/rap_coach/pedagogy.py`

Implements the value critic and causal attribution heads that assess game state value and attribute coaching insights to specific tactical concepts.

#### Class: `RAPPedagogy(nn.Module)`

**Constructor Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hidden_dim` | int | 256 | Input feature dimension |

**Architecture:**
1. **Critic head** (`self.critic`): `Sequential(Linear(256, 64), ReLU(), Linear(64, 1))`
   - Outputs a scalar value estimate for the current game state.
2. **Skill adapter** (`self.skill_adapter`): `Linear(10, 256)`
   - Projects a 10-dimensional skill vector into the 256-dim hidden space.
   - Used as an additive bias: `hidden = hidden + skill_adapter(skill_vec)`.

**Method: `calculate_advantage_gap(actual_outcome, value_pred) -> Tensor`**
- Returns `actual_outcome - value_pred` (temporal-difference error).

**Method: `forward(hidden, skill_vec=None) -> Tensor`**
- If `skill_vec` is provided and has the correct shape, adds skill bias to hidden features.
- Returns: `self.critic(hidden)` -> scalar value estimate (B, 1).

#### Class: `CausalAttributor(nn.Module)`

Maps hidden features to a 5-concept attribution vector, identifying which tactical domain is most relevant to the current situation.

**Class Constants:**
```python
concepts = ["positioning", "crosshair_placement", "utility_usage", "timing", "economy"]
```

**Constructor Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hidden_dim` | int | 256 | Input feature dimension |

**Architecture:**
- `self.relevance_head = Sequential(Linear(256, 32), ReLU(), Linear(32, 5), Sigmoid())`
- Output range: [0, 1] per concept (sigmoid activation).

**Method: `diagnose(hidden, context_weights=None, mechanical_errors=None) -> Tensor`**
- Base attribution: `self.relevance_head(hidden)` -> (B, 5).
- If `context_weights` is provided: `attribution = context_weights * mechanical_errors` (element-wise fusion of contextual relevance with observed errors).
- Returns: 5-dim attribution vector.

**Method: `_detect_utility_need(hidden) -> Tensor`**
- Returns `sigmoid(hidden.mean(dim=-1))` -- a scalar heuristic for whether utility usage coaching is needed.
- Used as a quick check without full attribution.

### 2.7 Communication (`communication.py`)

**File:** `backend/nn/experimental/rap_coach/communication.py`

Converts model outputs into natural-language coaching feedback, stratified by player skill level.

#### Module-Level Constants

```python
_ANGLE_SECTORS = [
    (0, 45, "ahead"),
    (45, 135, "to the right"),
    (135, 225, "behind"),
    (225, 315, "to the left"),
    (315, 360, "ahead"),
]
```
Five directional sectors mapping angle ranges (degrees) to human-readable spatial descriptions.

#### Module-Level Function: `_compute_relative_direction(player_angle, threat_position, player_position)`

Computes the relative direction from player to threat based on the player's facing angle.

- **Returns:** A string from `_ANGLE_SECTORS` (e.g., "to the right", "behind").
- Used to provide spatially-aware coaching feedback.

#### Class: `RAPCommunication`

**Constructor:** No parameters. Initializes the `templates` dictionary.

**Instance Attribute: `templates`**

A nested dictionary organized as `templates[skill_tier][topic]` where:
- **Skill tiers:** `"low"` (skill level 1-3), `"mid"` (skill level 4-7), `"high"` (skill level 8-10).
- **Topics:** `"positioning"`, `"mechanics"`, `"strategy"`.
- Each entry is a template string containing `{angle}` placeholders for spatial context injection.

**Template examples:**
- Low/positioning: Basic "move to cover {angle}" advice.
- High/strategy: Advanced rotational timing and read-based play suggestions.

**Method: `generate_advice(model_output, game_context=None, skill_level=5) -> str`**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_output` | dict | Forward pass output from RAPCoachModel |
| `game_context` | dict optional | Live game state (player positions, angles) |
| `skill_level` | int | Player skill level (1-10) |

- **Confidence gate:** If max advice probability < 0.7, returns generic "continue current approach" message.
- **Skill tier mapping:** 1-3 = "low", 4-7 = "mid", 8-10 = "high".
- **Signal extraction:** `argmax(advice_probs)` determines dominant signal, mapped to topic via modulo or predefined mapping.
- **Spatial context:** Resolves `{angle}` placeholder via `_resolve_angle()` using game_context.
- **Returns:** Formatted template string with spatial directions injected.

**Static Method: `_resolve_angle(game_context) -> str`**
- Extracts player position, threat position, and player angle from game_context.
- Delegates to `_compute_relative_direction()`.
- Returns a spatial direction string or "ahead" as default.

### 2.8 Chronovisor Scanner (`chronovisor_scanner.py`)

**File:** `backend/nn/experimental/rap_coach/chronovisor_scanner.py`

Multi-scale critical moment detection system that identifies mistakes and plays across different temporal granularities (micro, standard, macro).

#### Dataclass: `ScanResult`

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Whether the scan completed without error |
| `critical_moments` | list[CriticalMoment] | Detected critical moments |
| `ticks_analyzed` | int | Total ticks processed |
| `error` | str or None | Error message if scan failed |

#### Dataclass: `ScaleConfig`

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Scale name ("micro", "standard", "macro") |
| `window_ticks` | int | Analysis window size in ticks |
| `lag` | int | Lookback lag for delta computation |
| `threshold` | float | Minimum delta magnitude to trigger a moment |
| `description` | str | Human-readable scale description |

#### Dataclass: `CriticalMoment`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `match_id` | str | -- | Match identifier |
| `start_tick` | int | -- | Moment start tick |
| `peak_tick` | int | -- | Tick of maximum signal intensity |
| `end_tick` | int | -- | Moment end tick |
| `severity` | float | -- | Severity score [0.0, 1.0] |
| `type` | str | -- | Either "mistake" or "play" |
| `scale` | str | -- | Which temporal scale detected it |
| `context_ticks` | int | 128 | Number of surrounding ticks for context |

#### Module-Level Constant: `ANALYSIS_SCALES`

```python
ANALYSIS_SCALES = [
    ScaleConfig("micro",    window_ticks=64,  lag=16,  threshold=0.10, description="Mechanical errors, reaction failures"),
    ScaleConfig("standard", window_ticks=192, lag=64,  threshold=0.15, description="Tactical mistakes, positioning errors"),
    ScaleConfig("macro",    window_ticks=640, lag=128, threshold=0.20, description="Strategic failures, rotation timing"),
]
```

Scale philosophy:
- **Micro** (64 ticks, ~1s at 64 tick): Rapid mechanical events -- missed flicks, late reactions.
- **Standard** (192 ticks, ~3s): Mid-level tactical events -- bad peeks, utility timing.
- **Macro** (640 ticks, ~10s): Strategic events -- wrong rotations, economy mismanagement.
- Higher thresholds at larger scales prevent noise from triggering at coarse granularity.
- **Priority order** for deduplication: micro > standard > macro (finer scale wins).

#### Class: `ChronovisorScanner`

**Constructor:** Initializes the logger and model reference.

**Method: `_load_model()`**
- Loads the RAP Coach model with maturity gate check.
- Model must pass a maturity threshold before scanning is permitted.

**Class Constant:**
```python
_MAX_TICKS_PER_SCAN = 50000
```
Safety limit to prevent OOM on very long demos.

**Method: `scan_match(match_id, tick_data) -> ScanResult`**
- Entry point for critical moment detection.
- Truncates tick_data to `_MAX_TICKS_PER_SCAN` if necessary.
- Delegates to `_analyze_signal()` for multi-scale processing.
- Returns `ScanResult` with success/failure status.

**Method: `_analyze_signal(signal, match_id) -> list[CriticalMoment]`**
- Iterates over `ANALYSIS_SCALES`, calling `_analyze_signal_at_scale()` for each.
- Aggregates all moments, then deduplicates via `_deduplicate_across_scales()`.

**Method: `_analyze_signal_at_scale(signal, scale, match_id) -> list[CriticalMoment]`**
- Computes deltas: `delta = signal[t] - signal[t - lag]` within sliding windows.
- Peaks above `scale.threshold` become `CriticalMoment` entries.
- Classifies direction: negative delta = "mistake", positive = "play".
- Assigns severity normalized to [0, 1].

**Method: `_deduplicate_across_scales(moments) -> list[CriticalMoment]`**

**Constants used:**
```python
MIN_GAP_TICKS = 64
```

- Sorts moments by priority (micro > standard > macro).
- Two moments within `MIN_GAP_TICKS` of each other: the finer-scale moment wins.
- Prevents reporting the same event at multiple temporal resolutions.

### 2.9 Trainer (`trainer.py`)

**File:** `backend/nn/experimental/rap_coach/trainer.py`

Multi-loss training orchestrator with mixed-precision support, gradient accumulation, and per-axis position loss weighting.

#### Class: `RAPTrainer`

**Class Constants:**
```python
LOSS_WEIGHT_STRATEGY  = 1.0   # NN-58: Strategy loss multiplier
LOSS_WEIGHT_VALUE     = 0.5   # NN-58: Value critic loss multiplier
LOSS_WEIGHT_SPARSITY  = 1.0   # NN-58: MoE sparsity loss multiplier
LOSS_WEIGHT_POSITION  = 1.0   # NN-58: Position loss multiplier
Z_AXIS_PENALTY_WEIGHT = 2.0   # NN-TR-02b: Z-axis penalty (verticality in CS2)
```

**Design rationale for Z_AXIS_PENALTY_WEIGHT:** Verticality errors in CS2 are disproportionately impactful -- being on the wrong floor is nearly always fatal. Z-axis MSE is penalized 2x relative to X/Y.

**Constructor Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | RAPCoachModel | -- | The model to train |
| `lr` | float | 1e-4 | Learning rate |
| `t_max` | int | 100 | Cosine annealing period |
| `accumulation_steps` | int | 4 | Gradient accumulation steps |

**Optimizer and Scheduler:**
- `AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)`
- `CosineAnnealingLR(T_max=100, eta_min=1e-6)` -- learning rate decays from 1e-4 to 1e-6 over 100 epochs.
- `GradScaler("cuda", enabled=self._use_amp)` -- mixed-precision training on CUDA only.

**Loss Functions:**
- `criterion_strat = nn.MSELoss()` -- strategy prediction loss.
- `criterion_val = nn.MSELoss()` -- value estimate loss.
- `criterion_pos = nn.MSELoss()` -- per-axis position loss (custom weighting applied).

**Method: `train_step(batch, *, step_optimizer=True) -> dict`**

| Parameter | Type | Description |
|-----------|------|-------------|
| `batch` | dict | Tensor dict from orchestrator with keys: view, map, motion, metadata, target_strat, target_val, val_mask, target_pos, timespans |
| `step_optimizer` | bool | If False, accumulates gradients without stepping (for gradient accumulation) |

**Forward pass under AMP autocast:**
1. `model.forward(batch["view"], batch["map"], batch["motion"], batch["metadata"], timespans=batch.get("timespans"))`.
2. **Strategy loss:** `MSE(outputs["advice_probs"], batch["target_strat"])`.
3. **Value loss:** `MSE(outputs["value_estimate"], batch["target_val"])` with optional `val_mask`:
   - If mask exists and is partial: apply masked loss.
   - If mask exists and all-False: zero loss (no valid targets).
   - Otherwise: full-batch loss.
4. **Sparsity loss:** `model.compute_sparsity_loss(outputs["gate_weights"])`.
5. **Position loss:** If `target_pos` in batch: `compute_position_loss(outputs["optimal_pos"], batch["target_pos"])`.
6. **Total loss:** Weighted sum of all four losses using class constants.

**Gradient mechanics:**
- Loss divided by `_accumulation_steps` before `.backward()`.
- If `step_optimizer=True`:
  - `scaler.unscale_(optimizer)`
  - `clip_grad_norm_(model.parameters(), max_norm=1.0)`
  - `scaler.step(optimizer)` + `scaler.update()`
  - `optimizer.zero_grad()`

**Sparsity ratio logging:** Fraction of gate weights with absolute value < 0.01 (dead expert detection).

**Returns:**
```python
{"loss": float, "sparsity_ratio": float, "loss_pos": float, "z_error": float}
```

**Method: `compute_position_loss(pred_delta, target_delta) -> (Tensor, float)`**

- Separates X, Y, Z components.
- `weighted_loss = mse_x + mse_y + (z_axis_penalty_weight * mse_z)`.
- Returns `(weighted_loss, mse_z.item())` for logging.

**Method: `_optimizer_step()`**
- Flush accumulated gradients at epoch end.
- Same unscale/clip/step/update/zero_grad sequence as `train_step`.

### 2.10 Test Infrastructure

**File:** `backend/nn/experimental/rap_coach/conftest.py`

```python
collect_ignore = ["test_arch.py"]
```
Prevents pytest from collecting `test_arch.py` (which is a standalone script, not a pytest test).

**File:** `backend/nn/experimental/rap_coach/test_arch.py`

Standalone architecture verification script (not a pytest test).

- **Import guard:** Raises `ImportError` if `pytest` is detected in `sys.modules` (prevents accidental pytest collection).
- **Test parameters:** `batch_size=2`, `seq_len=5`, visual inputs `64x64` resolution.
- **Verification:** Creates a `RAPCoachModel`, runs a forward pass, and asserts output shapes match expected dimensions.
- **Usage:** Run directly with `python test_arch.py` to verify architecture integrity after modifications.

---

## 3. Knowledge Layer

**Location:** `Programma_CS2_RENAN/backend/knowledge/`

The knowledge layer implements COPER (Context Optimized with Prompt, Experience, and Replay) -- a framework that combines experience banking, knowledge retrieval (RAG), knowledge graphs, and vector indexing to provide context-aware coaching grounded in real pro player data.

### 3.1 Package Init

**File:** `backend/knowledge/__init__.py`

Empty file (package marker only, 1 line).

### 3.2 Experience Bank (`experience_bank.py`)

**File:** `backend/knowledge/experience_bank.py`

Implements the COPER Experience Bank -- a persistent store of coaching experiences with CRUD lifecycle management, semantic similarity retrieval, TrueSkill-inspired confidence tracking, and prioritized replay sampling.

#### Module-Level Constants

```python
_MIN_EFFECTIVENESS_TRIALS    = 5     # Minimum trials before effectiveness is meaningful
MIN_RETRIEVAL_CONFIDENCE     = 0.3   # Floor for retrieval confidence filtering
PRO_EXPERIENCE_CONFIDENCE    = 0.7   # Default confidence for pro-sourced experiences
AMATEUR_EXPERIENCE_CONFIDENCE= 0.5   # Default confidence for amateur-sourced experiences
DUPLICATE_SIMILARITY_THRESHOLD = 0.9 # Cosine similarity threshold for dedup
CRUD_EMA_FACTOR              = 0.3   # EMA smoothing factor for effectiveness updates
REPLAY_ALPHA                 = 0.6   # Priority exponent for replay sampling
REPLAY_GATE                  = 0.4   # Minimum priority to be eligible for replay
```

#### Dataclass: `ExperienceContext`

Captures the full tactical context of a coaching experience.

| Field | Type | Description |
|-------|------|-------------|
| `map_name` | str | Map identifier (e.g., "de_dust2") |
| `round_phase` | str | Phase of the round ("pistol", "eco", "force", "full_buy") |
| `side` | str | Team side ("ct" or "t") |
| `position_area` | str | Map area/callout |
| `health_range` | str | Health bracket |
| `equipment_tier` | str | Equipment value bracket |
| `teammates_alive` | int | Count of alive teammates |
| `enemies_alive` | int | Count of alive enemies |

**Method: `to_query_string() -> str`**
- Concatenates all fields into a space-separated string for semantic embedding.

**Method: `compute_hash() -> str`**
- Deterministic hash of the context (for deduplication and CRUD matching).

#### Dataclass: `SynthesizedAdvice`

Output of advice synthesis from multiple experiences.

| Field | Type | Description |
|-------|------|-------------|
| `narrative` | str | Human-readable coaching narrative |
| `pro_references` | list[str] | Pro player examples cited |
| `confidence` | float | Overall confidence score |
| `focus_area` | str | Primary coaching focus |
| `experiences_used` | int | Number of experiences synthesized |

#### Module-Level Function: `_dedup_experiences(experiences) -> list`

**Tag:** CHAT-07.

Deduplicates a list of experience records by checking context hash and action similarity. Uses `DUPLICATE_SIMILARITY_THRESHOLD` (0.9) for cosine similarity comparison of embeddings.

This is a **module-level function**, not an `ExperienceBank` method. It is called by retrieval methods before returning results.

#### Class: `ExperienceBank`

**Embedding Serialization:**

**Static Method: `_serialize_embedding(embedding) -> str`**
- Converts numpy array to base64-encoded string for SQLite storage.

**Static Method: `_deserialize_embedding(data) -> np.ndarray`**
- Supports two formats:
  - **Base64:** Modern format (post-v2).
  - **JSON:** Legacy format (pre-v2 migration path).

**Method: `add_experience(context, action, outcome, embedding, source="amateur") -> str`**

CRUD lifecycle management for new experiences:
1. **Duplicate detection:** Searches existing experiences with same context hash.
2. **UPDATE path:** If existing experience has same context AND same action -> EMA update of effectiveness score.
3. **DISCARD path:** If existing experience has same context AND different action but existing is better -> new experience discarded, existing created.
4. **CREATE path:** Otherwise, inserts new experience with appropriate confidence (`PRO_EXPERIENCE_CONFIDENCE` or `AMATEUR_EXPERIENCE_CONFIDENCE`).

**Method: `update_experience(experience_id, outcome) -> None`**
- EMA update: `new_effectiveness = CRUD_EMA_FACTOR * outcome + (1 - CRUD_EMA_FACTOR) * old_effectiveness`.
- TrueSkill-inspired confidence update: adjusts confidence based on outcome consistency with historical performance.

**Method: `discard_experience(experience_id) -> None`**
- Soft-delete: sets `confidence = 0.0` (does not remove the row).
- Experiences with zero confidence are filtered from retrieval.

**Method: `retrieve_similar(query_embedding, context=None, k=5) -> list`**
- **FAISS path:** If vector index is available, uses `IndexFlatIP` for approximate nearest neighbor.
- **Brute-force path:** Falls back to manual cosine similarity computation.
- **Composite scoring:** Combines embedding similarity with context hash matching.
- Filters by `MIN_RETRIEVAL_CONFIDENCE` (0.3).
- Applies `_dedup_experiences()` before returning.

**Method: `retrieve_by_text(query_text, k=5) -> list`**
- Embeds query text via SBERT, then delegates to `retrieve_similar()`.
- Semantic-only retrieval (no context hash matching).

**Method: `retrieve_pro_examples(context=None, k=3) -> list`**
- Retrieves experiences where `source = "pro"`.
- Optional context filtering.

**Method: `synthesize_advice(context, k=10) -> SynthesizedAdvice`**
- Retrieves top-k similar experiences.
- Separates into success and failure patterns.
- Builds a narrative from patterns: what works, what doesn't, pro player references.
- Returns `SynthesizedAdvice` dataclass.

**Method: `extract_experiences_from_demo(demo_data) -> list[str]`**
- Parses demo replay data to extract actionable coaching experiences.
- Creates `ExperienceContext` from round metadata.
- Returns list of created experience IDs.

**Method: `sample_for_replay(batch_size=32) -> list`**
- **Prioritized sampling** (Schaul et al., 2016):
  - Priority = effectiveness^REPLAY_ALPHA (0.6).
  - Gate: Only experiences with priority >= REPLAY_GATE (0.4) are eligible.
  - Sampling probability proportional to priority (priority skew).

**Method: `record_feedback(experience_id, feedback_score) -> None`**
- Atomic SQL `UPDATE` of feedback score for human-in-the-loop refinement.

**Method: `collect_feedback_from_match(match_id) -> list`**
- Aggregates all experiences from a match and their feedback scores.

**Method: `decay_stale_experiences(max_age_days=90, decay_rate=0.1) -> int`**
- Decays confidence by `decay_rate` (10%) for experiences older than `max_age_days` (90 days).
- Returns count of decayed experiences.

#### Singleton Factory: `get_experience_bank() -> ExperienceBank`

Thread-safe singleton. Uses module-level `_instance` with lock protection.

### 3.3 Knowledge Graph (`graph.py`)

**File:** `backend/knowledge/graph.py`

SQLite-backed knowledge graph with entity-relation storage and BFS subgraph queries.

#### Class: `KnowledgeGraphManager`

**Class Constants:**
```python
DB_PATH = USER_DATA_ROOT / "knowledge_graph.db"
```

**Database Schema (two tables):**

**`entities` table:**
| Column | Type | Constraint |
|--------|------|------------|
| `name` | TEXT | PRIMARY KEY |
| `type` | TEXT | Entity category |
| `observations` | TEXT (JSON) | Serialized observation data |

**`relations` table:**
| Column | Type | Constraint |
|--------|------|------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `from_entity` | TEXT | FOREIGN KEY -> entities.name |
| `to_entity` | TEXT | FOREIGN KEY -> entities.name |
| `relation_type` | TEXT | Relation label |
| `metadata` | TEXT (JSON) | Additional relation data |
| UNIQUE | | (from_entity, to_entity, relation_type) |

**Method: `_connect() -> sqlite3.Connection`**
- Opens SQLite connection with:
  - `journal_mode = WAL` (Write-Ahead Logging for concurrency)
  - `synchronous = NORMAL` (balanced durability/performance)
  - `busy_timeout = 30000` ms (30-second wait on lock contention)

**Method: `add_entity(name, entity_type, observations=None) -> None`**
- `INSERT OR REPLACE` (UPSERT semantics).
- Observations serialized as JSON.

**Method: `add_relation(from_entity, to_entity, relation_type, metadata=None) -> None`**
- `INSERT OR IGNORE` (prevents duplicate relations).
- Metadata serialized as JSON.

**Method: `query_subgraph(root_entity, max_depth=3) -> dict`**
- **BFS traversal** starting from `root_entity`.
- Depth cap: `min(max_depth, 5)` -- hard limit of 5 to prevent runaway queries.
- Returns: `{"entities": [...], "relations": [...]}` for the reachable subgraph.
- Each hop follows outgoing relations to discover connected entities.

**Method: `close() -> None`**
- Closes the database connection.

#### Singleton Factory: `get_knowledge_graph() -> KnowledgeGraphManager`

Module-level singleton with no explicit locking (relies on SQLite WAL for concurrent access safety).

### 3.4 RAG Knowledge (`rag_knowledge.py`)

**File:** `backend/knowledge/rag_knowledge.py`

Retrieval-Augmented Generation (RAG) system with SBERT embeddings, FAISS indexing, and fallback hash-projection for environments without the sentence-transformers library.

#### Class: `KnowledgeEmbedder`

Manages embedding generation and versioning.

**Class Constants:**
```python
CURRENT_VERSION = "v3"  # Embedding version -- triggers re-embedding on mismatch
```

**Model:** `all-MiniLM-L6-v2` via sentence-transformers library (384-dimensional embeddings).

**Method: `_is_model_cached() -> bool`**
- Checks if the SBERT model is already downloaded to the local cache.
- Prevents unnecessary network calls.

**Method: `_notify_download_start() / _notify_download_complete()`**
- UI notification hooks for model download progress.
- Called before/after first-time model download.

**Method: `embed(texts: list[str]) -> np.ndarray`**
- Primary embedding method using SBERT.
- Returns: array of shape (N, 384).
- Falls back to `_fallback_embed()` if sentence-transformers unavailable.

**Method: `_fallback_embed(texts: list[str]) -> np.ndarray`**
- **Bag-of-words hash-projection** producing 100-dimensional embeddings.
- Each word is hashed (deterministic), and its hash maps to a fixed dimension.
- Significantly lower quality than SBERT but ensures the system never crashes.
- Returns: array of shape (N, 100).

**Method: `check_embedding_compatibility() -> bool`**
- Compares stored embedding version against `CURRENT_VERSION`.
- Returns `False` if re-embedding is needed (version mismatch).

**Method: `trigger_reembedding()`**
- Batch re-embeds all knowledge entries when version changes.
- **Constant:** `MAX_REEMBED_BATCH = 5000` -- processes at most 5000 entries per call.
- Updates stored version to `CURRENT_VERSION`.

#### Class: `KnowledgeRetriever`

Retrieves knowledge entries by semantic similarity.

**Method: `retrieve(query_text, k=5, min_score=0.3) -> list[dict]`**
- Embeds query via `KnowledgeEmbedder`.
- Attempts FAISS search first, falls back to brute-force.
- Filters by `min_score` threshold.
- Updates usage counts for retrieved entries.

**Method: `_fetch_and_filter(ids, scores, min_score) -> list[dict]`**
- Fetches full entries from SQLite by ID.
- Applies score threshold filtering.

**Method: `_brute_force_retrieve(query_embedding, k, min_score) -> list[dict]`**
- Loads all embeddings from DB, computes cosine similarity manually.
- Used when FAISS index is unavailable or corrupted.

**Method: `_update_usage_counts(entry_ids) -> None`**
- Increments `usage_count` column for retrieved entries.
- Tracks which knowledge entries are most useful.

#### Class: `KnowledgePopulator`

Populates the knowledge database from JSON files.

**Class Constants:**
```python
_ALLOWED_ENTRY_KEYS = frozenset({...})  # Whitelist of valid knowledge entry fields
```

**Method: `add_knowledge(entry: dict) -> str`**
- Validates entry keys against `_ALLOWED_ENTRY_KEYS`.
- Embeds the entry text.
- Inserts into SQLite with embedding and version metadata.
- Returns the entry ID.

**Method: `populate_from_json(json_path) -> int`**
- Handles two JSON formats:
  - **Coach Book index:** A manifest file listing individual knowledge files.
  - **Legacy format:** A single JSON file with all entries.
- Delegates to `_populate_single_file()` for each file.
- Returns count of entries added.

**Method: `_populate_single_file(file_path) -> int`**
- Reads and validates a single JSON knowledge file.
- Calls `add_knowledge()` for each entry.

#### Module-Level Functions

**`ensure_seed_knowledge_loaded() -> None`**
- Idempotent initialization: loads seed knowledge if not already present.
- Called during application startup.

**`_get_retriever() -> KnowledgeRetriever`**
- Cached singleton factory for the retriever.
- Lazy initialization on first call.

**`generate_rag_coaching_insight(query, context=None) -> dict`**
- High-level API: generates a single coaching insight via RAG retrieval.
- Embeds the query, retrieves relevant knowledge, formats response.

**`generate_unified_coaching_insight(query, context=None, include_experiences=True) -> dict`**
- Unified API combining knowledge retrieval with experience bank.
- Merges RAG knowledge with relevant experiences for richer insights.

### 3.5 Vector Index (`vector_index.py`)

**File:** `backend/knowledge/vector_index.py`

FAISS-based dual vector index for knowledge and experience retrieval.

#### Module-Level Flag

```python
FAISS_AVAILABLE: bool  # True if faiss library is importable
```

#### Module-Level Constants

```python
OVERFETCH_KNOWLEDGE  = 10   # Overfetch multiplier for knowledge queries
OVERFETCH_EXPERIENCE = 20   # Overfetch multiplier for experience queries
```

Overfetching retrieves more candidates than requested, then post-filters for quality. Experience index uses a higher multiplier because experience entries have more variable quality.

#### Module-Level Function: `_deserialize_embedding(data) -> np.ndarray`

Supports both base64 and JSON serialization formats (same dual-format logic as in `experience_bank.py`).

#### Function: `_default_index_dir() -> Path`

Returns `STORAGE_ROOT / "vector_indexes"` as the default persistence directory.

#### Class: `VectorIndexManager`

Manages two separate FAISS indexes: one for knowledge entries, one for experience entries.

**Threading:** `threading.Lock` protects all index operations.

**Instance Attributes:**
- `_knowledge_index`: FAISS IndexFlatIP for knowledge vectors.
- `_experience_index`: FAISS IndexFlatIP for experience vectors.
- `_knowledge_dirty: bool` -- flag for lazy rebuild.
- `_experience_dirty: bool` -- flag for lazy rebuild.
- `_knowledge_id_map: list[int]` -- maps FAISS internal IDs to database IDs.
- `_experience_id_map: list[int]` -- maps FAISS internal IDs to database IDs.

**Method: `mark_dirty(index_type: str) -> None`**
- Sets the dirty flag for "knowledge" or "experience" index.
- Triggers rebuild on next search.

**Method: `search(query_embedding, index_type="knowledge", k=5) -> list[tuple[int, float]]`**
- L2-normalizes the query embedding.
- Searches the specified index using inner product (cosine similarity after normalization).
- Returns list of (database_id, score) tuples.
- Auto-rebuilds if dirty flag is set.

**Method: `rebuild_from_db(index_type="knowledge") -> None`**
- Rebuilds the specified index from database contents.
- Delegates to `_load_knowledge_vectors()` or `_load_experience_vectors()`.
- Thread-safe (acquires lock).

**Method: `_build_index(vectors: np.ndarray) -> faiss.IndexFlatIP`**
- Creates a new `IndexFlatIP` (Inner Product) index.
- L2-normalizes all vectors before adding.

**Method: `_save(index_type) / _load_persisted(index_type)`**
- Disk persistence for indexes using FAISS native I/O.
- Saves both the index and the ID map.

**Method: `_load_knowledge_vectors() -> tuple[np.ndarray, list[int]]`**
- Batch loads knowledge embeddings from SQLite.
- **Batch size:** `BATCH_SIZE = 5000` rows per query.
- Deserializes embeddings, stacks into numpy array.

**Method: `_load_experience_vectors() -> tuple[np.ndarray, list[int]]`**
- Same batch loading pattern for experience embeddings.
- **Batch size:** `BATCH_SIZE = 5000` rows per query.

#### Singleton Factory: `get_vector_index_manager() -> VectorIndexManager`

Thread-safe singleton with double-checked locking pattern.

### 3.6 Pro Demo Miner (`pro_demo_miner.py`)

**File:** `backend/knowledge/pro_demo_miner.py`

Mines professional player statistics to generate coaching knowledge. Works with HLTV stat cards (NOT demo files -- HLTV is for pro stats scraping only).

#### Module-Level Constants

```python
_STAR_FRAGGER_IMPACT     = 1.15   # Impact rating threshold for Star Fragger
_SNIPER_HS_THRESHOLD     = 0.35   # HS% below this suggests AWP specialist
_SUPPORT_KAST_THRESHOLD  = 0.72   # KAST above this suggests Support Anchor
_ENTRY_OPENING_THRESHOLD = 0.52   # Opening kill rate for Entry Fragger

_KNOWN_MAPS = {"de_dust2", "de_mirage", "de_inferno", "de_nuke",
               "de_overpass", "de_ancient", "de_vertigo", "de_anubis"}

_MIN_MAP_ROUNDS = 10   # Minimum rounds on a map for statistical significance

_DEFAULT_STATS_SENTINEL = (...)  # Tuple of sentinel values for empty stat cards
```

#### Module-Level Function: `_is_default_stats_card(card) -> bool`

**Tag:** CHAT-06.

Detects whether a `ProPlayerStatCard` contains sentinel/placeholder values rather than real statistics. Prevents the system from generating coaching advice from empty data.

#### Class: `ProStatsMiner` (alias: `ProDemoMiner`)

**Method: `mine_all_pro_stats(stat_cards: list) -> list[dict]`**
- Iterates over `ProPlayerStatCard` records.
- Skips sentinel cards via `_is_default_stats_card()`.
- Calls `_generate_player_knowledge()` for each valid card.
- Returns list of knowledge entries.

**Method: `_generate_player_knowledge(card) -> list[dict]`**
- Creates three types of knowledge entries per player:
  1. **`pro_baseline`:** Overall performance metrics (KPR, DPR, KAST, rating).
  2. **`opening_duels`:** First-kill statistics and tendencies.
  3. **`clutch_performance`:** Clutch round win rates and patterns.

**Method: `mine_map_specific_knowledge(round_stats: list) -> list[dict]`**
- Aggregates `RoundStats` records by `(map, player, side)`.
- Requires minimum `_MIN_MAP_ROUNDS` for statistical significance.
- Generates map-specific, side-specific coaching insights.

**Method: `_classify_archetype(card) -> str`**

Classification logic (evaluated in priority order):
1. `Impact >= _STAR_FRAGGER_IMPACT` (1.15) -> "Star Fragger"
2. `HS% < _SNIPER_HS_THRESHOLD` (0.35) -> "AWP Specialist"
3. `KAST >= _SUPPORT_KAST_THRESHOLD` (0.72) -> "Support Anchor"
4. `Opening kill rate >= _ENTRY_OPENING_THRESHOLD` (0.52) -> "Entry Fragger"
5. Default -> "Versatile"

#### Module-Level Function: `auto_populate_from_pro_demos(limit=10) -> int`

Convenience function that chains miner initialization, stat card loading, and knowledge population. The `limit` parameter caps the number of pro players processed.

### 3.7 Round Utilities (`round_utils.py`)

**File:** `backend/knowledge/round_utils.py`

Classifies CS2 round phases based on equipment value.

#### Module-Level Constants

```python
_PISTOL_MAX_EQUIP = 1500    # Equipment value ceiling for pistol rounds
_ECO_MAX_EQUIP    = 3000    # Equipment value ceiling for eco rounds
_FORCE_MAX_EQUIP  = 4000    # Equipment value ceiling for force-buy rounds
```

#### Function: `infer_round_phase(equipment_value: int) -> str`

Classification logic:
- `equipment_value <= _PISTOL_MAX_EQUIP` -> `"pistol"`
- `equipment_value <= _ECO_MAX_EQUIP` -> `"eco"`
- `equipment_value <= _FORCE_MAX_EQUIP` -> `"force"`
- Otherwise -> `"full_buy"`

### 3.8 Init Knowledge Base (`init_knowledge_base.py`)

**File:** `backend/knowledge/init_knowledge_base.py`

Orchestrates the complete knowledge base initialization pipeline.

#### Function: `initialize_knowledge_base() -> None`

Five-step initialization:
1. **Initialize database:** Creates/migrates knowledge tables.
2. **Load Coach Book:** Populates from the structured Coach Book JSON index, or falls back to legacy JSON format.
3. **Mine pro demos:** Processes up to `limit=10` professional player stat cards.
4. **Report stats:** Runs aggregation queries (entry counts, category distribution, embedding version stats) and logs the results.
5. **Build FAISS indexes:** Triggers `VectorIndexManager.rebuild_from_db()` for both knowledge and experience indexes.

---

## 4. Knowledge Base (Help System)

**Location:** `Programma_CS2_RENAN/backend/knowledge_base/`

A separate, simpler knowledge base for in-app help documentation.

### 4.1 Package Init

**File:** `backend/knowledge_base/__init__.py`

Docstring only -- no exports. Serves as package marker.

### 4.2 Help System (`help_system.py`)

**File:** `backend/knowledge_base/help_system.py`

In-application help system that reads markdown documentation from the `data/docs/` directory.

#### Class: `HelpSystem`

**Method: `refresh_index() -> None`**
- Scans `data/docs/` for markdown files.
- Builds an in-memory index of topics from file headers and content.

**Method: `get_topic(topic_name: str) -> str or None`**
- Returns the full content of a specific help topic.
- Case-insensitive matching.

**Method: `get_all_topics() -> list[str]`**
- Returns a sorted list of all available topic names.

**Method: `search_topics(query: str) -> list[tuple[str, float]]`**
- Simple text search with scoring.
- Matches query terms against topic titles and content.
- Returns list of (topic_name, relevance_score) tuples, sorted by score.

#### Singleton Factory: `get_help_system() -> HelpSystem`

Lazy singleton -- initializes on first call, calls `refresh_index()`.

---

## 5. Coaching Layer

**Location:** `Programma_CS2_RENAN/backend/coaching/`

The coaching layer is the output-facing pipeline that transforms ML predictions and knowledge retrieval into actionable player feedback. It bridges the neural network outputs (from RAP Coach or AdvancedCoachNN) with human-readable coaching insights.

### 5.1 Package Init

**File:** `backend/coaching/__init__.py`

**Exports:**
- `HybridCoachingEngine` -- the primary coaching engine
- `generate_corrections` -- Z-score correction generator
- `ExplanationGenerator` -- narrative explanation generator
- `PlayerCardAssimilator` -- pro player stat card translator
- `get_pro_baseline_for_coach` -- factory for pro baseline retrieval

### 5.2 Correction Engine (`correction_engine.py`)

**File:** `backend/coaching/correction_engine.py`

Generates statistical corrections by comparing player performance to baseline metrics using Z-scores.

#### Module-Level Constants

```python
DEFAULT_IMPORTANCE = {
    "kpr":              1.0,    # Kills per round
    "dpr":              0.8,    # Deaths per round
    "kast":             0.9,    # KAST percentage
    "adr":              0.85,   # Average damage per round
    "hs_percentage":    0.7,    # Headshot percentage
    "first_kills":      0.75,   # First kill rate
    "clutch_win_rate":  0.65,   # Clutch win rate
}

CONFIDENCE_ROUNDS_CEILING = 300  # Rounds needed for maximum confidence
```

#### Function: `get_feature_importance() -> dict`

Returns `DEFAULT_IMPORTANCE` merged with any user-configured overrides from settings.

#### Function: `generate_corrections(player_stats, baseline, rounds_played) -> list[dict]`

1. For each feature in `DEFAULT_IMPORTANCE`:
   - Computes Z-score: `(player_value - baseline_value) / baseline_std`.
   - Applies importance weighting: `weighted_z = z_score * importance`.
2. Computes confidence: `min(1.0, rounds_played / CONFIDENCE_ROUNDS_CEILING)`.
   - 300 rounds = full confidence.
3. Sorts by `|weighted_z| * importance` descending.
4. Returns **top 3** corrections, each containing:
   - Feature name, raw Z-score, weighted Z-score, importance, direction ("improve"/"maintain"), confidence.

### 5.3 Explainability (`explainability.py`)

**File:** `backend/coaching/explainability.py`

Generates human-readable narrative explanations from statistical coaching insights.

#### Class: `ExplanationGenerator`

**Class Constants:**
```python
SILENCE_THRESHOLD       = 0.2   # |Z-score| below this: insight suppressed (not significant)
SEVERITY_HIGH_BOUNDARY  = 1.5   # |Z-score| above this: HIGH severity
SEVERITY_MEDIUM_BOUNDARY= 0.8   # |Z-score| above this: MEDIUM severity
                                 # Below MEDIUM boundary: LOW severity
```

**Class Constant: `TEMPLATES`**

Dictionary keyed by `SkillAxes` enum values:
```python
TEMPLATES = {
    SkillAxes.MECHANICS:   {"negative": "...", "positive": "...", "action": "..."},
    SkillAxes.POSITIONING: {"negative": "...", "positive": "...", "action": "..."},
    SkillAxes.UTILITY:     {"negative": "...", "positive": "...", "action": "..."},
    SkillAxes.TIMING:      {"negative": "...", "positive": "...", "action": "..."},
    SkillAxes.DECISION:    {"negative": "...", "positive": "...", "action": "..."},
}
```

Each skill axis has three template slots:
- **negative:** Used when Z-score is negative (underperformance).
- **positive:** Used when Z-score is positive (outperformance).
- **action:** Concrete recommended action.

**Static Method: `generate_narrative(corrections, skill_level=5) -> list[str]`**

1. Filters corrections by `SILENCE_THRESHOLD` (suppresses insignificant insights).
2. **Skill-level verbosity filter:**
   - Low skill (1-3): Only HIGH severity insights (avoid overwhelming).
   - Mid skill (4-7): HIGH and MEDIUM severity.
   - High skill (8-10): All insights including LOW severity.
3. Maps each correction to the appropriate template based on feature -> SkillAxes mapping and Z-score direction.
4. Returns list of narrative strings.

**Static Method: `classify_insight_severity(z_score) -> str`**
- `|z_score| >= SEVERITY_HIGH_BOUNDARY` (1.5) -> `"high"`
- `|z_score| >= SEVERITY_MEDIUM_BOUNDARY` (0.8) -> `"medium"`
- Otherwise -> `"low"`

### 5.4 Hybrid Engine (`hybrid_engine.py`)

**File:** `backend/coaching/hybrid_engine.py`

The central coaching engine that fuses ML predictions with RAG knowledge retrieval to produce unified coaching insights. This is the primary output-facing component.

#### Enum: `InsightPriority`

```python
class InsightPriority(Enum):
    CRITICAL = "critical"   # Z-score and confidence thresholds for each level
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
```

Each priority level has associated Z-score and confidence thresholds that determine when an insight qualifies.

#### Dataclass: `HybridInsight`

| Field | Type | Description |
|-------|------|-------------|
| `title` | str | Short insight title |
| `message` | str | Full coaching message |
| `priority` | InsightPriority | Severity level |
| `confidence` | float | [0.0, 1.0] confidence score |
| `feature` | str | Which performance feature triggered it |
| `ml_z_score` | float | ML-derived Z-score deviation |
| `knowledge_refs` | list[dict] | RAG knowledge entries cited |
| `pro_examples` | list[dict] | Pro player examples cited |
| `tick_range` | tuple or None | (start_tick, end_tick) for temporal context |
| `demo_name` | str or None | Associated demo file |

#### Module-Level Constants

```python
_FALLBACK_BASELINE = {
    "kpr": 0.65, "dpr": 0.62, "kast": 0.70, "adr": 75.0,
    "hs_percentage": 0.45, "first_kills": 0.10, "clutch_win_rate": 0.10,
    "flash_assists": 0.15, "utility_damage": 5.0, "entry_rate": 0.08,
    "trade_rate": 0.12, "survival_rate": 0.35,
}
```
Hard-coded fallback baseline for when no dynamic or pro baseline is available. Contains 12 features with conservative average values.

#### Class: `HybridCoachingEngine`

**Lazy SBERT loading** (AC-15-01): The sentence-transformers model is loaded only on first access via the `retriever` property, avoiding startup latency when coaching is not used.

**Method: `_load_model() -> nn.Module`**
- Attempts to load JEPA model first (if USE_JEPA=True).
- Falls back to `AdvancedCoachNN`.
- Returns the loaded model in eval mode.

**Method: `_load_pro_baseline() -> dict`**
- Triple fallback chain:
  1. **Dynamic baseline:** From `pro_baseline` module (live HLTV data).
  2. **HARD_DEFAULT:** Module-level constant baseline.
  3. **Local `_FALLBACK_BASELINE`:** The 12-feature fallback above.
- **TTL refresh:** Baseline is refreshed every 3600 seconds (1 hour) to pick up new pro stats.

**Method: `generate_insights(player_stats, demo_data=None, match_context=None) -> list[HybridInsight]`**

Main entry point. Orchestrates the full coaching pipeline:

1. **Resolve contextual pro baseline:** Adjusts baseline for map/side/role if available.
2. **Calculate deviations:** Delegates to `pro_baseline` module for Z-score computation.
3. **ML predictions:** Runs the loaded model for pattern-based insights.
4. **Knowledge retrieval:** Queries the RAG system for contextually relevant coaching content.
5. **Synthesize insights:** Merges ML deviations with knowledge context.
6. **Tag degraded baseline:** If using fallback baseline, marks insights as degraded-confidence.

**Method: `_calculate_deviations(player_stats, baseline) -> dict`**
- Delegates to `pro_baseline` module's deviation calculation.
- Returns feature -> Z-score mapping.

**Method: `_calculate_confidence(ml_confidence, knowledge_score) -> float`**
- Blends ML and knowledge confidence: `0.6 * ml_confidence + 0.4 * knowledge_score`.
- Optionally adjusted by `MetaDriftEngine` if drift is detected.

**Method: `_synthesize_insights(deviations, knowledge_entries, pro_examples, ml_output=None) -> list[HybridInsight]`**
- For each significant deviation (above priority thresholds):
  - Creates a `HybridInsight` with the deviation, matched knowledge references, and pro examples.
  - Supports **Reference Clip** attachment (TASK 2.7.1) -- links specific demo tick ranges to insights.
- Sorts by priority (CRITICAL first) and returns.

**Method: `save_insights_to_db(insights, player_id, match_id) -> None`**
- Persists generated insights to the SQLite database for historical tracking.

#### Singleton Factory: `get_hybrid_engine() -> HybridCoachingEngine`

Factory function with lazy initialization.

### 5.5 Longitudinal Engine (`longitudinal_engine.py`)

**File:** `backend/coaching/longitudinal_engine.py`

Analyzes player performance trends over time to generate long-term coaching insights.

#### Function: `generate_longitudinal_coaching(trends: list[dict]) -> list[HybridInsight]`

1. Filters trends by `confidence >= 0.6`.
2. For each qualifying trend, calls `_process_trend()`.
3. Returns at most **3 insights** (prevents information overload).

#### Function: `_process_trend(trend: dict) -> HybridInsight or None`

- **Regression detection:** If trend slope is significantly negative, generates a regression warning insight.
- **Improvement detection:** If trend slope is significantly positive, generates an improvement acknowledgment insight.
- Maps trend features to `InsightPriority` levels.
- Returns `None` for insignificant trends.

### 5.6 NN Refinement (`nn_refinement.py`)

**File:** `backend/coaching/nn_refinement.py`

A simple scaling layer that adjusts correction weights based on neural network output.

#### Function: `apply_nn_refinement(corrections, nn_adjustments) -> list[dict]`

- For each correction, multiplies `weighted_z` by `(1 + nn_adjustments[feature_weight])`.
- **No actual NN inference** happens in this module despite the name -- it merely applies pre-computed adjustment factors.
- Acts as a post-processing step after corrections are generated and NN predictions are available.

### 5.7 Pro Bridge (`pro_bridge.py`)

**File:** `backend/coaching/pro_bridge.py`

Translates professional player stat cards into the coaching engine's baseline format. Bridges the HLTV data model with the coaching data model.

#### Module-Level Constants

```python
ESTIMATED_ROUNDS_PER_MATCH = 24.0  # Average rounds per CS2 match (used for per-round normalization)
```

#### Class: `PlayerCardAssimilator`

Translates `ProPlayerStatCard` (HLTV format) to the coaching engine's baseline dictionary format.

**Method: `get_coach_baseline(card) -> dict`**
- **P3-02 fix:** Uses KPR and DPR directly from the stat card (no longer divides by rounds).
- **V-2 defensive normalization:** KAST and HS% are normalized from percentage (0-100) to ratio (0-1) if they appear to be in percentage format (value > 1.0).
- Returns a baseline dict compatible with `generate_corrections()`.

**Method: `_extract_hs_ratio(card) -> float`**
- Extracts headshot ratio with V-2 normalization.
- Guards against None values.

**Method: `_map_detailed_metrics(card) -> dict`**
- Extracts `entry_rate` (opening kills per round) and `utility_damage` (average utility damage per round) from detailed stat card fields.
- Uses `ESTIMATED_ROUNDS_PER_MATCH` for normalization when per-round values are not directly available.

**Method: `get_player_archetype(card) -> str`**

Classification logic (same thresholds as `ProStatsMiner._classify_archetype` but in the coaching context):
- "Star Fragger" -- high impact rating
- "Support Anchor" -- high KAST
- "Sniper Specialist" -- low HS% (implies AWP usage)
- "All-Rounder" -- default

#### Module-Level Function: `get_pro_baseline_for_coach(player_name=None) -> dict`

Factory function that:
1. Loads a `ProPlayerStatCard` for the given player (or the default reference player).
2. Passes it through `PlayerCardAssimilator.get_coach_baseline()`.
3. Returns the formatted baseline dict.

### 5.8 Token Resolver (`token_resolver.py`)

**File:** `backend/coaching/token_resolver.py`

Resolves a player's identity and performance into a complete "Token" -- a structured snapshot used for detailed comparison and coaching.

#### Class: `PlayerTokenResolver`

**Method: `get_player_token(player_id, match_context=None) -> dict`**

Returns a comprehensive Token dictionary with five sections:
```python
{
    "identity": {
        "player_id": str,
        "display_name": str,
        "steam_id": str,
    },
    "core_metrics": {
        "kpr": float, "dpr": float, "kast": float, "adr": float,
        "hs_percentage": float, "rating": float,
    },
    "tactical_baselines": {
        "entry_rate": float, "trade_rate": float,
        "clutch_win_rate": float, "flash_assists": float,
    },
    "granular_data": {
        "per_map": dict,     # Map-specific performance breakdowns
        "per_weapon": dict,  # Weapon-specific accuracy/kill stats
        "trend": dict,       # Historical performance trend data
    },
    "metadata": {
        "total_rounds": int,
        "matches_analyzed": int,
        "last_updated": str,
        "confidence": float,
    },
}
```

**Method: `compare_performance_to_token(player_stats, pro_token) -> dict`**

Returns a Correction Delta dictionary:
```python
{
    "deltas": {
        "kpr": float,           # player_value - pro_value
        "dpr": float,
        "kast": float,
        ...
    },
    "is_underperforming": bool,  # True if player rating < 85% of pro rating
    "underperformance_areas": list[str],  # Features with significant negative deltas
}
```

The 85% threshold is used as the underperformance gate -- a player is flagged only if their overall rating drops below 85% of the reference pro player's rating.

---

## 6. Cross-Cutting Concerns

### 6.1 Singleton and Factory Patterns

| Factory Function | Module | Threading Model |
|-----------------|--------|-----------------|
| `get_experience_bank()` | experience_bank.py | Module-level lock |
| `get_knowledge_graph()` | graph.py | No explicit lock (SQLite WAL) |
| `get_vector_index_manager()` | vector_index.py | Double-checked locking |
| `get_help_system()` | help_system.py | Lazy init, no lock |
| `get_hybrid_engine()` | hybrid_engine.py | Lazy init |
| `_get_retriever()` | rag_knowledge.py | Cached singleton |

### 6.2 Dimensional Contracts

The following dimensions flow through the pipeline and must remain consistent:

| Dimension | Value | Source |
|-----------|-------|--------|
| Perception output | 128 | RAPPerception (64 + 32 + 32) |
| Metadata dim | 25 | METADATA_DIM constant |
| Memory input | 153 | 128 + 25 |
| LTC neurons | 512 | hidden_dim * 2 |
| NCP motor output | 154 | 512 * 0.3 |
| Hidden dim | 256 | Memory output (projected from 154) |
| Belief dim | 64 | Belief head output |
| Context dim | 89 | 25 + 64 (metadata + belief) |
| MoE experts | 4 | RAPStrategy.num_experts |
| MoE top-k | 2 | RAPStrategy.TOP_K |
| Hopfield prototypes | 32 | Quantity parameter |
| Causal concepts | 5 | CausalAttributor.concepts |
| Position output | 3 | (dx, dy, dz) |
| Skill vector | 10 | RAPPedagogy.skill_adapter input |
| SBERT embedding | 384 | all-MiniLM-L6-v2 |
| Fallback embedding | 100 | Hash-projection |

### 6.3 Critical Invariants

| ID | Rule | Location |
|----|------|----------|
| NN-MEM-01 | Hopfield bypassed until >= 2 training forward passes | memory.py:161-177 |
| RAP-AUDIT-03 | Use HopfieldLayer (NOT Hopfield) for persistent prototypes | memory.py:115-121 |
| RAP-AUDIT-04 | Entropy-based sparsity loss for MoE gate | model.py:compute_sparsity_loss |
| RAP-AUDIT-05 | Without timespans, LTC loses continuous-time advantage | memory.py:forward docstring |
| RAP-AUDIT-07 | NCP output ratio 0.3 (not 0.5), with projection layer | memory.py:48-97 |
| RAP-AUDIT-09 | Context = metadata + belief (not metadata alone) | model.py:forward |
| RAP-LTC-FIX | ODE solver monkey-patch for ncps shape bug | memory.py:86-93 |
| NN-39 | Support both 4D and 5D visual input | model.py:forward |
| NN-45 | Deterministic NCP wiring via numpy+torch seed save/restore | memory.py:57-67 |
| NN-TR-02b | Z-axis penalty 2x for position loss | trainer.py:28 |
| P-X-02 | Shape assertions on model input | model.py:forward |
| NN-RM-01 | Skill vector validation before pedagogy | model.py:forward |
| P9-01 | Main rap_coach/ is shim layer to experimental/ | rap_coach/__init__.py |
| AC-15-01 | Lazy SBERT loading in HybridCoachingEngine | hybrid_engine.py |
| P3-02 | KPR/DPR used directly (not divided by rounds) | pro_bridge.py |
| V-2 | Defensive normalization for KAST/HS% (>1.0 -> ratio) | pro_bridge.py |
| CHAT-06 | Sentinel detection for empty stat cards | pro_demo_miner.py |
| CHAT-07 | Dedup experiences before retrieval | experience_bank.py |

### 6.4 Data Flow Summary

```
Demo File
  |
  v
[Perception: ResNet CNN]  --view(64) + map(32) + motion(32)--> 128-dim spatial
  |
  + metadata(25) --> 153-dim
  |
  v
[Memory: LTC + Hopfield]  --temporal processing--> combined_state(256), belief(64)
  |
  + context = metadata(25) + belief(64) = 89-dim
  |
  v
[Strategy: MoE Top-2]  --FiLM-conditioned experts--> advice_probs, gate_weights
  |
  v
[Pedagogy: Value Critic + Causal]  --> value_estimate(1), concept_weights(5)
  |
  v
[Communication: Template Engine]  --> human-readable coaching text
  |
  + [Knowledge: RAG + Experience Bank + Knowledge Graph]  --> contextual references
  |
  v
[Hybrid Engine]  --fuses ML + Knowledge--> HybridInsight list
  |
  v
[Correction Engine + Explainability]  --> prioritized, narrated coaching output
```

### 6.5 External Dependencies

| Dependency | Used By | Optional? | Fallback |
|-----------|---------|-----------|----------|
| `ncps` | RAPMemory (LTC neurons) | Yes | RAPMemoryLite (LSTM) |
| `hflayers` | RAPMemory (Hopfield) | Yes | RAPMemoryLite (no associative memory) |
| `sentence-transformers` | KnowledgeEmbedder | Yes | Hash-projection (100-dim) |
| `faiss` | VectorIndexManager | Yes | Brute-force cosine similarity |
| `torch` | All neural modules | No | -- |
