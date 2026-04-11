> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching -- Multi-Mode Coaching Pipeline

> **Authority:** `backend/coaching/`
> **Skill:** `/ml-check`, `/api-contract-review`
> **Owner module:** `backend/services/coaching_service.py`

## Overview

The coaching package is the intelligence layer that transforms raw analysis data into
actionable player feedback. It implements a **four-mode coaching pipeline** where each
mode offers a different trade-off between knowledge-driven advice and neural-network
predictions. The default mode is **COPER** (Contextual Observation Pattern Experience
Retrieval), which combines an Experience Bank, RAG knowledge retrieval, and professional
player reference data to produce coaching output grounded in real match evidence.

All coaching modes are consumed by a single entry point --
`backend/services/coaching_service.py` -- which selects the active mode based on the
feature flags `USE_COPER_COACHING`, `USE_HYBRID_COACHING`, `USE_RAG_COACHING`, and
`USE_JEPA_MODEL` / `USE_RAP_MODEL` in `core/config.py`.

## The Four Coaching Modes

| # | Mode | Flag | Description |
|---|------|------|-------------|
| 1 | **COPER** | `USE_COPER_COACHING=True` (default) | Experience Bank semantic retrieval + RAG knowledge + Pro References. No ML model required. |
| 2 | **Hybrid** | `USE_HYBRID_COACHING=True` | Neural network predictions synthesized with RAG context for blended output. |
| 3 | **RAG** | `USE_RAG_COACHING=True` | Pure knowledge retrieval from indexed pro demo patterns. No ML inference. |
| 4 | **Neural** | `USE_JEPA_MODEL=True` or `USE_RAP_MODEL=True` | Pure ML predictions without knowledge augmentation. Requires a trained model checkpoint. |

### Coaching Fallback Flow

When a higher-fidelity mode is unavailable (missing model, empty knowledge base, etc.),
the pipeline degrades gracefully through the following chain:

```
Neural (pure ML)
   |  [model checkpoint missing or inference error]
   v
Hybrid (ML + RAG)
   |  [RAG index empty or ML unavailable]
   v
COPER (Experience Bank + RAG + Pro)
   |  [experience bank empty]
   v
RAG (knowledge retrieval only)
   |  [knowledge index empty]
   v
Heuristic corrections (correction_engine.py fallback)
```

Each transition is logged at WARNING level with a structured JSON message containing
the reason for degradation, so the operator always knows which mode is active.

## File Inventory

| File | Primary Export | Purpose |
|------|---------------|---------|
| `__init__.py` | Package API | Re-exports `HybridCoachingEngine`, `generate_corrections`, `ExplanationGenerator`, `PlayerCardAssimilator`, `get_pro_baseline_for_coach` |
| `hybrid_engine.py` | `HybridCoachingEngine` | Central orchestrator that synthesizes ML predictions with RAG knowledge retrieval for balanced coaching insights |
| `correction_engine.py` | `generate_corrections()` | Generates tactical corrections by comparing player performance deviations against professional baselines |
| `nn_refinement.py` | `apply_nn_refinement()` | Correction weight scaling — multiplies Z-score deviations by feature-specific weights. Does NOT perform NN inference (historical name) |
| `longitudinal_engine.py` | `generate_longitudinal_coaching()` | Tracks performance trends over time using temporal baseline decay integration for long-term improvement advice |
| `explainability.py` | `ExplanationGenerator` | Converts opaque ML prediction tensors into human-readable explanations with causal attribution chains |
| `pro_bridge.py` | `PlayerCardAssimilator` | Links professional player stat cards to coaching insights via role-based comparison (entry fragger, AWPer, etc.) |
| `token_resolver.py` | `PlayerTokenResolver` | Canonicalizes player names using fuzzy matching, leet-speak normalization, and alias resolution |

## Module Descriptions

### hybrid_engine.py -- HybridCoachingEngine

The `HybridCoachingEngine` is the primary orchestrator for the Hybrid coaching mode.
It accepts a 25-dimensional feature vector (see `METADATA_DIM` in `nn/config.py`),
runs ML inference through the active model (JEPA or RAP), retrieves relevant knowledge
from the RAG index, and merges both signals into a unified coaching response. The
engine applies a confidence-weighted blending strategy: high-confidence ML predictions
dominate, while low-confidence ones defer to RAG knowledge.

### correction_engine.py -- generate_corrections()

Stateless function that takes a player's round performance snapshot and compares it
against the professional baseline (provided by `pro_bridge.py`). Deviations exceeding
configurable thresholds produce correction entries with severity (info/warning/critical),
a human-readable description, and the specific metric that triggered the correction.
This module is the final fallback when all higher-fidelity coaching modes are unavailable.

### nn_refinement.py -- apply_nn_refinement()

Correction weight scaling step (DA-03: historical name is misleading). Takes heuristic
corrections from `correction_engine.py` and multiplies each `weighted_z` by
`(1 + feature_weight)` from a provided adjustments dict. This is pure arithmetic — no
neural network is loaded, no model inference occurs, no confidence scoring is performed.
The adjustments dict *may* originate from an NN model's output upstream, but this module
itself is a scalar multiplication. Called conditionally by `correction_engine.py` only
when `nn_adjustments` is non-empty.

### longitudinal_engine.py -- generate_longitudinal_coaching()

Generates coaching advice based on performance trends across multiple matches or sessions.
Uses `TemporalBaselineDecay` from `backend/processing/baselines/pro_baseline.py` to
weight recent performance more heavily than older data. Produces trend direction indicators
(improving/declining/stable) for each tracked metric and tailors advice accordingly.

### explainability.py -- ExplanationGenerator

Implements model explainability by decomposing neural network predictions into
human-readable explanations. Uses feature attribution (which of the 25 input dimensions
contributed most to the prediction) and causal reasoning chains to explain *why* the
model recommends a particular action. Critical for building player trust in ML-driven
coaching advice.

### pro_bridge.py -- PlayerCardAssimilator

Bridges the gap between professional player statistics (from `hltv_metadata.db`) and
the coaching pipeline. The `PlayerCardAssimilator` loads pro player stat cards and
performs role-based comparison: if the user plays as an entry fragger, their stats are
compared against professional entry fraggers. The `get_pro_baseline_for_coach()` helper
provides a ready-to-use baseline dictionary for the correction engine.

### token_resolver.py -- PlayerTokenResolver

Resolves ambiguous player name references to canonical identities. Handles common
challenges in CS2 naming: leet-speak substitutions (e.g., "s1mple" vs "simple"),
clan tag prefixes, Unicode homoglyphs, and partial name matches. Uses fuzzy string
matching with configurable similarity thresholds. Essential for matching user-provided
names to entries in the professional player database.

## Integration with Services Layer

```
coaching_service.py
    |
    +-- selects coaching mode (COPER / Hybrid / RAG / Neural)
    |
    +-- calls hybrid_engine.py (Hybrid mode)
    |       |-- ML inference (JEPA or RAP model)
    |       +-- RAG retrieval (knowledge/)
    |
    +-- calls correction_engine.py (all modes)
    |       +-- pro_bridge.py (professional baseline)
    |
    +-- calls nn_refinement.py (if model available)
    |
    +-- calls longitudinal_engine.py (if historical data present)
    |
    +-- calls explainability.py (if ML predictions used)
    |
    +-- returns CoachingResponse to UI layer
```

The `coaching_service.py` orchestrator also injects temporal baseline context from
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`), ensuring that coaching advice accounts
for how the player's skill level has evolved over recent sessions.

## Development Notes

- **Feature flag discipline:** Never bypass feature flags. The coaching mode is selected
  exclusively through `core/config.py` flags. Hard-coding a mode causes test failures.
- **25-dim contract:** Any module that touches the feature vector must respect
  `METADATA_DIM=25`. See the Dimensional Contract table in the project root `CLAUDE.md`.
- **Structured logging:** All modules use `get_logger("cs2analyzer.coaching.<module>")`.
  Fallback transitions log at WARNING level with correlation IDs.
- **Thread safety:** The coaching pipeline may be invoked from the Quad-Daemon's Teacher
  thread. All shared state must be accessed through thread-safe accessors, never module-level
  globals.
- **Testing:** Tests live in `Programma_CS2_RENAN/tests/`. Use the `mock_db_manager` and
  `torch_no_grad` fixtures for coaching tests.

## Dependencies

- **PyTorch** -- Neural network inference for Hybrid and Neural modes
- **sentence-transformers** -- Embedding generation for RAG and Experience Bank retrieval
- **SQLModel** -- Experience Bank persistence
- **scikit-learn** -- Similarity metrics for token resolution (optional)
