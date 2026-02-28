> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Feature Engineering — Unified Feature Extraction

Unified feature extraction pipeline for training and inference with HLTV 2.0 rating calculation and role-specific features.

## Core Modules

### Unified Feature Vector
- **vectorizer.py** — `FeatureExtractor` — Unified 25-dimensional feature vector (METADATA_DIM=25) for all ML models. Ensures consistent feature representation across training and inference. Extracts per-tick features: position (x, y, z), velocity, health, armor, weapon stats, utility counts, economy state, round context.

### HLTV 2.0 Rating
- **rating.py** — `compute_hltv2_rating()`, `compute_impact_rating()`, `compute_survival_rating()` — Full HLTV 2.0 rating implementation with three components:
  - Impact Rating: Kills/deaths/assists weighted by multi-kill multipliers
  - Survival Rating: Deaths per round inverse with penalties
  - KAST Integration: Kill/Assist/Survive/Trade percentage contribution

### KAST Calculation
- **kast.py** — `estimate_kast_from_stats()` — KAST percentage calculation from round statistics. KAST = percentage of rounds with Kill OR Assist OR Survived OR Traded.

### Base Features
- **base_features.py** — `HeuristicConfig`, `extract_match_stats()`, `load_learned_heuristics()` — Heuristic feature extraction with learned parameter loading from training. Configurable feature weights and thresholds.

### Role-Specific Features
- **role_features.py** — Role-specific feature extraction for Entry Fragger, Lurker, Support, AWPer, and IGL roles. Extracts role-relevant metrics (first kills, backstabs, utility assists, AWP kills, decision outcomes).

## Integration

FeatureExtractor used by:
- RAP Coach training (`backend/nn/rap_coach/trainer.py`)
- JEPA training (`backend/nn/jepa_trainer.py`)
- Coaching service (`backend/services/coaching_service.py`)
- Analysis orchestrator (`backend/services/analysis_service.py`)

## Feature Vector Components (25-dim)
Position (3), velocity (3), health/armor (2), weapon (5), utility (4), economy (3), round context (5).

## Dependencies
NumPy, Pandas, SQLModel.
