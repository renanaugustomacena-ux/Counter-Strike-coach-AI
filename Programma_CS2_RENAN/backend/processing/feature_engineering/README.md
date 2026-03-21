# Feature Engineering -- Unified Feature Extraction

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/backend/processing/feature_engineering/`

## Introduction

This package is the **single source of truth** for the 25-dimensional feature
vector (`METADATA_DIM = 25`) consumed by every neural network in the project
(RAP Coach, JEPA, AdvancedCoachNN).  All feature extraction, normalization,
and encoding logic lives here -- no other module is permitted to construct
feature vectors independently.

The core contract: training and inference MUST produce identical feature
vectors for identical input data.  Any divergence causes silent model
corruption known as *Inference-Training Skew*.

## File Inventory

| File | Purpose | Key Exports |
|------|---------|-------------|
| `vectorizer.py` | 25-dim feature vector extraction and validation | `FeatureExtractor`, `FEATURE_NAMES`, `METADATA_DIM`, `DataQualityError`, `WEAPON_CLASS_MAP` |
| `base_features.py` | Configurable heuristic thresholds + match-level aggregation | `HeuristicConfig`, `extract_match_stats()`, `load_learned_heuristics()`, `save_heuristic_config()` |
| `rating.py` | Unified HLTV 2.0 rating formula (component + regression) | `compute_hltv2_rating()`, `compute_impact_rating()`, `compute_survival_rating()`, `compute_hltv2_rating_regression()` |
| `kast.py` | KAST (Kill/Assist/Survive/Trade) calculation | `calculate_kast_for_round()`, `calculate_kast_percentage()`, `estimate_kast_from_stats()` |
| `role_features.py` | Role-specific features and classification | `classify_role()`, `extract_role_features()`, `get_role_coaching_focus()`, `get_adaptive_signatures()`, `ROLE_SIGNATURES`, `PlayerRole` |
| `__init__.py` | Lazy-import dispatcher (prevents import-lock deadlocks) | Re-exports all public names from submodules |

## The 25-Dimensional Feature Vector

Every tick of every player is encoded into exactly 25 float32 values.  The
order is fixed and enforced by the compile-time assertion
`len(FEATURE_NAMES) == METADATA_DIM` (invariant `P-X-01`).

| Idx | Name | Normalization | Range | Category |
|-----|------|---------------|-------|----------|
| 0 | `health` | /100 | [0, 1] | Vitals |
| 1 | `armor` | /100 | [0, 1] | Vitals |
| 2 | `has_helmet` | binary | {0, 1} | Vitals |
| 3 | `has_defuser` | binary | {0, 1} | Vitals |
| 4 | `equipment_value` | /10000 | [0, 1] | Economy |
| 5 | `is_crouching` | binary | {0, 1} | Stance |
| 6 | `is_scoped` | binary | {0, 1} | Stance |
| 7 | `is_blinded` | binary | {0, 1} | Stance |
| 8 | `enemies_visible` | /5, clamped | [0, 1] | Awareness |
| 9 | `pos_x` | /4096, clipped | [-1, 1] | Position |
| 10 | `pos_y` | /4096, clipped | [-1, 1] | Position |
| 11 | `pos_z` | /1024, clipped | [-1, 1] | Position |
| 12 | `view_yaw_sin` | sin(yaw_rad) | [-1, 1] | View Angle |
| 13 | `view_yaw_cos` | cos(yaw_rad) | [-1, 1] | View Angle |
| 14 | `view_pitch` | /90 | [-1, 1] | View Angle |
| 15 | `z_penalty` | `compute_z_penalty()` | [0, 1] | Spatial |
| 16 | `kast_estimate` | KAST ratio | [0, 1] | Performance |
| 17 | `map_id` | md5 hash -> [0, 1] | [0, 1] | Context |
| 18 | `round_phase` | 0/0.33/0.66/1.0 | [0, 1] | Economy |
| 19 | `weapon_class` | categorical 0-1 | [0, 1] | Equipment |
| 20 | `time_in_round` | /115, clamped | [0, 1] | Context |
| 21 | `bomb_planted` | binary | {0, 1} | Context |
| 22 | `teammates_alive` | /4 | [0, 1] | Context |
| 23 | `enemies_alive` | /5 | [0, 1] | Context |
| 24 | `team_economy` | /16000 | [0, 1] | Economy |

### Design Decisions

- **Yaw angle uses sin/cos encoding** (indices 12-13) to avoid the +/-180
  degree discontinuity that would confuse gradient-based models.
- **Map identity uses `hashlib.md5`** (index 17), not Python `hash()`, for
  deterministic reproducibility across sessions (PYTHONHASHSEED randomization).
- **Context features 20-24** are read from `tick_data` first (enriched during
  ingestion), with fallback to a `context` dict (DemoFrame at inference),
  eliminating training/inference skew.
- **Weapon class** (index 19) maps ~70 CS2 weapon names (internal +
  demoparser2 display names) to 6 categories via `WEAPON_CLASS_MAP`.

## Architecture & Concepts

### FeatureExtractor (`vectorizer.py`)

The primary interface.  Class-level configuration via `HeuristicConfig`
enables runtime hot-swap of normalization bounds (Task 6.3).

Key methods:
- `extract(tick_data, map_name, context, _config_override)` -- single tick.
- `extract_batch(tick_data_list, map_name, contexts)` -- batch with config
  snapshot (`R4-14-03`) for thread-safe consistency.
- `validate_feature_parity(vec, label)` -- asserts last dimension equals
  `METADATA_DIM` at both training and inference boundaries (`P-SR-01`).
- `get_feature_names()` -- delegates to `FEATURE_NAMES` tuple.

Safety mechanisms:
- `P-VEC-01`: Warning on missing `map_name` (z_penalty defaults to 0.0).
- `P-VEC-02`: NaN/Inf detection with ERROR logging and clamp to defaults.
- `P-VEC-03`: `_config_override` parameter for batch consistency.
- `P3-A`: Batch quality gate -- `DataQualityError` raised when >5% of
  vectors in a batch contained NaN/Inf before clamping.
- `H-12`: Unknown weapons logged at WARNING on first occurrence, then DEBUG.

### HeuristicConfig (`base_features.py`)

A `@dataclass` encapsulating all normalization bounds and threshold constants.
Serializable to/from JSON via `to_dict()` / `from_dict()`.  Unknown keys are
silently ignored for forward compatibility.

`extract_match_stats()` aggregates per-round DataFrames into match-level
statistics, computing the unified HLTV 2.0 rating through `rating.py`
functions to prevent Inference-Training Skew.

### HLTV 2.0 Rating (`rating.py`)

Two implementations coexist by design (`F2-40`):

1. **`compute_hltv2_rating()`** -- per-component average, each term
   independently interpretable.  Used for coaching deviation analysis.
2. **`compute_hltv2_rating_regression()`** -- regression coefficients
   matching HLTV published values (R^2=0.995).  Used for UI display
   validation.  Includes a runtime guard against kast ratio/percentage
   confusion.

The two functions deliberately diverge -- do NOT reconcile them.

### KAST Calculation (`kast.py`)

Three granularities:
- `calculate_kast_for_round()` -- per-round event-level (K/A/S/T check with
  configurable trade window and tick rate).
- `calculate_kast_percentage()` -- multi-round aggregate.
- `estimate_kast_from_stats()` -- statistical approximation when round-level
  events are unavailable (uses 0.8 assist overlap heuristic and 30% trade
  probability estimate).

### Role Features (`role_features.py`)

- `ROLE_SIGNATURES` -- static centroid profiles for Entry, AWPer, Support,
  Lurker, and IGL based on top-20 HLTV player analysis.
- `classify_role()` -- delegates to `RoleClassifier` (learned thresholds +
  neural consensus), falls back to Euclidean-distance heuristic on cold start.
- `get_adaptive_signatures()` -- widens tolerance bands via
  `MetaDriftEngine.get_meta_confidence_adjustment()` when meta drift > 0.3.
- `get_role_coaching_focus()` -- returns priority stat keys per role.

### Lazy Imports (`__init__.py`)

Uses `__getattr__` to defer submodule imports until first attribute access.
This prevents `_ModuleLock` deadlocks when daemon threads (ingestion workers)
import submodules while the Kivy UI thread holds the import lock.

## Integration Points

| Consumer | Usage |
|----------|-------|
| `backend/nn/rap_coach/trainer.py` | `FeatureExtractor.extract_batch()` for training data |
| `backend/nn/jepa_trainer.py` | `FeatureExtractor.extract_batch()` with `validate_feature_parity()` |
| `backend/services/coaching_service.py` | `FeatureExtractor.extract()` for live inference |
| `backend/services/analysis_orchestrator.py` | `extract_match_stats()` for match-level analysis |
| `backend/processing/baselines/role_thresholds.py` | `classify_role()` for threshold validation |
| `core/session_engine.py` | `FeatureExtractor.configure()` at startup |

## Development Notes

- **Never add a feature** without updating `FEATURE_NAMES`, `METADATA_DIM`,
  the `extract()` docstring, and all model `input_dim` assertions.
- **Never include `round_won`** as a training feature -- it is an outcome
  label (invariant `P-RSB-03`).
- **Always call `extract()` with `map_name`** during training -- z_penalty
  breaks without it (`P-VEC-01`).
- Use `_config_override` in `extract()` for batch processing (`P-VEC-03`).
- Structured logging uses `get_logger("cs2analyzer.vectorizer")`.
- Dependencies: NumPy, Pandas, hashlib (stdlib), math (stdlib).
