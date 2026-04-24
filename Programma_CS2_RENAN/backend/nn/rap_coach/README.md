> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# RAP Coach — Retrieval-Augmented Pedagogical Neural Architecture

**Authority:** `Programma_CS2_RENAN/backend/nn/rap_coach/`
**Canonical location:** `backend/nn/experimental/rap_coach/` (this package is a backward-compatibility shim since P9-01)
**Feature flag:** `USE_RAP_MODEL=True` (default: `False`)

## Introduction

RAP (Retrieval-Augmented Pedagogical) Coach is the high-fidelity neural coaching model
within the Macena CS2 Analyzer. It implements a 7-layer architecture that perceives game
state through CNN streams, maintains temporal memory via Liquid Time-Constant (LTC)
neurons, makes decisions through a Mixture-of-Experts strategy layer, and generates
human-readable coaching feedback calibrated to the player's skill level.

The model consumes the canonical 25-dimensional feature vector (`METADATA_DIM=25`)
produced by `FeatureExtractor` alongside synthesized visual frames (view cone, map
context, motion difference). It produces coaching advice probabilities, belief state
estimates, value functions, optimal positioning deltas, and causal attribution scores.

## File Inventory

| File | Classes / Exports | Purpose |
|------|-------------------|---------|
| `__init__.py` | -- | Backward-compatibility shim (P9-01). Redirects to `experimental/rap_coach/`. |
| `model.py` | `RAPCoachModel`, `RAP_POSITION_SCALE` | Shim re-exporting the full model orchestrator. |
| `memory.py` | `RAPMemory` | Shim re-exporting LTC-Hopfield memory layer. |
| `trainer.py` | `RAPTrainer` | Shim re-exporting training orchestrator. |
| `perception.py` | `RAPPerception`, `ResNetBlock` | Shim re-exporting CNN perception layer. |
| `strategy.py` | `RAPStrategy`, `ContextualAttention` | Shim re-exporting MoE strategy layer. |
| `pedagogy.py` | `RAPPedagogy`, `CausalAttributor` | Shim re-exporting causal feedback layer. |
| `communication.py` | `RAPCommunication` | Shim re-exporting natural-language advice generator. |
| `chronovisor_scanner.py` | `ChronovisorScanner`, `CriticalMoment`, `ScanResult`, `ScaleConfig`, `ANALYSIS_SCALES` | Shim re-exporting multi-scale critical moment detection. |
| `skill_model.py` | `SkillAxes`, `SkillLatentModel` | Shim re-exporting player skill axes (VAE-style). Canonical location: `backend/processing/skill_assessment`. |

## Architecture: The 7-Layer RAP Pipeline

The RAP model processes game state through seven distinct layers, each with a specific
pedagogical responsibility. The ASCII diagram below shows the full data flow:

```
                         RAP Coach — 7-Layer Architecture
  ========================================================================

  INPUT TENSORS
  +------------------+  +------------------+  +------------------+
  | view_frame       |  | map_frame        |  | motion_diff      |
  | [B, 3, 64, 64]  |  | [B, 3, 64, 64]  |  | [B, 3, 64, 64]  |
  +--------+---------+  +--------+---------+  +--------+---------+
           |                     |                     |
  =========|=====================|=====================|===============
  LAYER 1: PERCEPTION (RAPPerception)
           |                     |                     |
     +-----v------+       +-----v------+       +------v-----+
     | ResNet      |       | ResNet     |       | MotionConv |
     | [1,2,2,1]   |       | [2,2]     |       | 3->16->32  |
     | -> 64-dim   |       | -> 32-dim |       | -> 32-dim  |
     +-----+------+       +-----+------+       +------+-----+
           |                     |                     |
           +----------+----------+----------+----------+
                      |
                z_spatial [B, 128]
                      |
  ====================|================================================
  LAYER 2: MEMORY (RAPMemory)
                      |
            +---------v-----------+        +---------+  metadata
            | Concatenate         |<-------+ [B,T,25]|  (25-dim vector)
            | [B, T, 128+25=153] |        +---------+
            +---------+-----------+
                      |
            +---------v-----------+
            |  LTC (Liquid Time-  |   AutoNCP wiring
            |  Constant) neurons  |   ncp_units=512
            |  hidden_dim=256     |   seed=42
            +---------+-----------+
                      |
            +---------v-----------+
            | Hopfield Associative|   4 attention heads
            | Memory (512 slots)  |   NN-MEM-01: bypassed
            | + Residual Addition |   until >=2 fwd passes
            +---------+-----------+
                      |
               combined_state [B, T, 256]
                      |
            +---------v-----------+
            | Belief Head         |   256 -> 256 -> 64
            | (SiLU activation)   |   belief_dim=64
            +---------+-----------+
                      |
               belief [B, T, 64]
                      |
  ====================|================================================
  LAYER 3: STRATEGY (RAPStrategy)
                      |
            +---------v-----------+
            | Mixture of Experts  |   4 experts
            | + Superposition     |   context = metadata[:,-1,:]
            | + Context Gate      |   L1 sparsity regularization
            +---------+-----------+
                      |
               advice_probs [B, OUTPUT_DIM=10]
               gate_weights [B, 4]
                      |
  ====================|================================================
  LAYER 4: PEDAGOGY (RAPPedagogy + CausalAttributor)
                      |
            +---------v-----------+
            | Critic Head V(s)    |   256 -> 64 -> 1
            | + Skill Adapter     |   skill_vec [B, 10]
            +---------+-----------+
                      |
               value_estimate [B, 1]
                      |
            +---------v-----------+
            | CausalAttributor    |   5 concepts:
            | Neural + Heuristic  |   Positioning, Crosshair,
            | Fusion              |   Aggression, Utility,
            +---------+-----------+   Rotation
                      |
               attribution [B, 5]
                      |
  ====================|================================================
  LAYER 5: COMMUNICATION (RAPCommunication)
                      |
            +---------v-----------+
            | Skill-Conditioned   |   Tiers: low (1-3),
            | Template Engine     |   mid (4-7), high (8-10)
            | + Angle Resolver    |   Confidence gate: 0.7
            +---------+-----------+
                      |
               natural-language coaching advice
                      |
  ====================|================================================
  LAYER 6: TEMPORAL ANALYSIS (ChronovisorScanner)
                      |
            +---------v-----------+
            | Multi-Scale Signal  |   micro:  64 ticks (~1s)
            | Processing          |   standard: 192 ticks (~3s)
            | + Cross-Scale Dedup |   macro: 640 ticks (~10s)
            +---------+-----------+
                      |
               CriticalMoment[]
                      |
  ====================|================================================
  LAYER 7: POSITION HEAD (in RAPCoachModel)
                      |
            +---------v-----------+
            | Linear(256, 3)      |   Predicts optimal
            | dx, dy, dz delta    |   position delta
            +---------+-----------+   RAP_POSITION_SCALE=500.0
                      |
               optimal_pos [B, 3]

  ========================================================================
```

## Key Constants

> Line anchors below point to the canonical implementation under
> `backend/nn/experimental/rap_coach/` -- the files in this package are 4-5 line
> re-export shims.

| Constant | Value | Source |
|----------|-------|--------|
| `hidden_dim` | 256 | `experimental/rap_coach/model.py:45` |
| `perception_dim` | 128 | `experimental/rap_coach/model.py:42` (64 + 32 + 32) |
| `ncp_units` | 512 | `experimental/rap_coach/memory.py:52` (hidden_dim x 2) |
| `belief_dim` | 64 | `experimental/rap_coach/model.py:61` |
| `OUTPUT_DIM` | 10 | `nn/config.py:162` |
| `METADATA_DIM` | 25 | `vectorizer.py:32` |
| `RAP_POSITION_SCALE` | 500.0 | `nn/config.py:194` |
| `num_experts` | 4 | `experimental/rap_coach/strategy.py:32` |
| `hopfield_heads` | 4 | `experimental/rap_coach/memory.py:92` |
| `Z_AXIS_PENALTY_WEIGHT` | 2.0 | `experimental/rap_coach/trainer.py:27` |

## Critical Invariants

| ID | Rule | Consequence if Violated |
|----|------|------------------------|
| **NN-MEM-01** | Hopfield memory is bypassed until >=2 training forward passes have occurred. Activation also triggers on checkpoint load. | Random prototypes inject noise instead of signal into combined_state, corrupting early training. |
| **NN-RM-01** | `skill_vec` must be shape `[B, 10]`. Mismatched shapes are logged and ignored. | Silent garbage in the pedagogy adapter biases value estimates. |
| **NN-RM-03** | `gate_weights` must be passed explicitly to `compute_sparsity_loss()` (thread-safety, F3-07). | Race condition on cached state in multi-threaded inference. |
| **P-X-02** | Input shape assertions enforce `metadata.shape[-1] == METADATA_DIM`. | Cryptic LSTM/CNN dimension errors deep in the forward pass. |
| **NN-CV-03** | Bounds-check peak_tick index before accessing ticks array in ChronovisorScanner. | IndexError crash during critical moment detection. |

## Integration

The RAP Coach integrates with the broader Macena CS2 Analyzer through several touchpoints:

- **CoachTrainingManager** (`backend/nn/coach_manager.py`) -- controls maturity gate for ChronovisorScanner
- **FeatureExtractor** (`backend/processing/feature_engineering/vectorizer.py`) -- produces the 25-dim metadata vector
- **RAPStateReconstructor** (`backend/processing/state_reconstructor.py`) -- converts raw tick data into model-ready tensor batches
- **SuperpositionLayer** (`backend/nn/layers/superposition.py`) -- context-modulated linear layer used by RAPStrategy experts
- **Persistence** (`backend/nn/persistence.py`) -- `load_nn("rap_coach", model)` / `save_nn()` for checkpoint management
- **Structured Logging** -- all modules use `get_logger("cs2analyzer.nn.experimental.rap_coach.<module>")`

## Dependencies

| Package | Purpose | Optional? |
|---------|---------|-----------|
| `torch` | Core tensor operations, nn.Module | Required |
| `ncps` | LTC neurons, AutoNCP wiring | Optional (guarded by `_RAP_DEPS_AVAILABLE`) |
| `hflayers` | Hopfield associative memory | Optional (guarded by `_RAP_DEPS_AVAILABLE`) |
| `numpy` | Signal processing in ChronovisorScanner | Required |
| `sqlmodel` | Database queries in ChronovisorScanner | Required (at scan time) |

When `ncps` / `hflayers` are not installed, `RAPMemoryLite` (LSTM-based fallback) is
available via `use_lite_memory=True` in `RAPCoachModel.__init__()`.

## Development Notes

- This package (`backend/nn/rap_coach/`) contains only **backward-compatibility shims**.
  All canonical implementation lives in `backend/nn/experimental/rap_coach/`.
- The feature flag `USE_RAP_MODEL` defaults to `False`. The primary production model is JEPA.
- Changing `ncp_units` or `hidden_dim` invalidates existing checkpoints. Version-gated
  loading in `load_nn()` detects architecture mismatches via `StaleCheckpointError`.
- The RNG state for AutoNCP wiring is explicitly saved and restored (`seed=42`) to ensure
  deterministic, checkpoint-portable network topology (NN-45 + NN-MEM-02).
- Trainer uses 4-component weighted loss: strategy (1.0), value (0.5), sparsity (1.0),
  position (1.0). Z-axis position errors are penalized at 2x weight (NN-TR-02b).
- Communication layer suppresses advice when model confidence is below 0.7 threshold.
