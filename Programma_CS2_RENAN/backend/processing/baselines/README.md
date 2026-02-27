# Professional Baselines & Meta Drift Detection

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Overview

This module provides professional player baselines, role classification thresholds, meta-game drift detection, and fuzzy nickname resolution. It enables temporal decay modeling of professional statistics and learned role thresholds persisted to the database.

## Key Components

### `pro_baseline.py`
- **`get_pro_baseline()`** — Retrieves professional player statistics with temporal decay weighting
- **`calculate_deviations()`** — Computes user performance deviations from pro baseline
- **`TemporalBaselineDecay`** — Exponential decay model for aging professional stats (default λ=0.0001/day)

### `role_thresholds.py`
- **`RoleThresholdStore`** — In-memory storage for learned role classification thresholds
- **`LearnedThreshold`** — Dataclass for per-role statistical thresholds (entry, support, lurk, AWP, IGL)
- **`persist_to_db()` / `load_from_db()`** — Database persistence for learned thresholds

### `meta_drift.py`
- **`MetaDriftEngine`** — Detects shifts in professional meta-game patterns (weapon usage, utility meta, map control trends)

### `nickname_resolver.py`
- **`NicknameResolver`** — Fuzzy matching for professional player nicknames (handles leet-speak, abbreviations, aliases)

## Integration

Used by `CoachingService` for temporal baseline enrichment, `Teacher` daemon for meta-shift detection after retraining, and `NeuralRoleHead` for role classification threshold learning.

## Data Sources

Professional baselines sourced from `ProPlayer` and `MatchResult` tables via HLTV scraping pipeline.
