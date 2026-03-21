# Professional Baselines & Meta-Drift Detection

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/backend/processing/baselines/`

## Introduction

This package establishes the professional reference frame against which every
user performance metric is evaluated.  It answers the question *"how does this
player compare to the pros?"* by maintaining Gaussian baselines (mean + std)
derived from real HLTV statistics, detecting when the competitive meta shifts
enough to invalidate those baselines, resolving in-game demo nicknames to
canonical HLTV identities, and learning role-classification thresholds from
empirical data rather than hardcoded constants.

The package is deliberately **read-heavy / write-rare**: baselines and
thresholds are computed once (during HLTV sync or after demo ingestion) and
then consumed thousands of times by the coaching pipeline.

## File Inventory

| File | Purpose | Key Exports |
|------|---------|-------------|
| `pro_baseline.py` | Gaussian baselines from HLTV `ProPlayerStatCard` records | `get_pro_baseline()`, `calculate_deviations()`, `get_pro_positions()`, `TemporalBaselineDecay` |
| `role_thresholds.py` | Learned role-classification thresholds (cold-start aware) | `RoleThresholdStore`, `LearnedThreshold`, `get_role_threshold_store()` |
| `meta_drift.py` | Detects statistical and spatial drift in pro play patterns | `MetaDriftEngine` |
| `nickname_resolver.py` | Fuzzy resolution of demo player names to HLTV IDs | `NicknameResolver` |
| `__init__.py` | Empty package marker | -- |

## Architecture & Concepts

### Three-Tier Baseline Fallback (`pro_baseline.py`)

`get_pro_baseline()` resolves baselines through a strict priority chain:

1. **Database** -- Aggregates `ProPlayerStatCard` rows from `hltv_metadata.db`
   into per-player averages, then computes global mean/std.  Supports optional
   `map_name` filtering (Task 2.18.1) for map-specific coaching.
2. **CSV** -- Falls back to `data/external/all_Time_best_Players_Stats.csv`
   when the database is empty.  Dynamically maps CSV columns via
   `_CSV_COLUMN_MAP`.
3. **Hard defaults** -- `HARD_DEFAULT_BASELINE` provides 16 hand-tuned
   metric distributions so the coach can still function on a fresh install.
   A `_provenance` key marks the baseline as degraded.

Guard rails:
- `P-PB-01`: K/D ratio skipped when DPR < 0.01 (avoids inflated ratios).
- `P-PB-02`: Survival approximated as `max(0, min(1, 1 - dpr))` since HLTV
  does not expose a dedicated survival metric.
- `P-PB-03`: CSV column mapping is dynamic, not hardcoded to three columns.
- `std = 0.0` is allowed; downstream `calculate_deviations()` skips Z-score
  for that metric rather than dividing by zero.

### Temporal Baseline Decay (`TemporalBaselineDecay`)

Professional CS2 evolves: recent stats should carry more weight than data
from six months ago.  `TemporalBaselineDecay` wraps the legacy
`get_pro_baseline()` with exponential time-weighting:

- **Half-life:** 90 days (configurable via `HALF_LIFE_DAYS`).
- **Floor weight:** 0.1 (`MIN_WEIGHT`) -- old data is down-weighted, never
  discarded entirely.
- **Meta-shift detection:** `detect_meta_shift()` compares two baseline
  epochs and flags metrics that moved more than 5% (`META_SHIFT_THRESHOLD`).

The temporal baseline is merged with the legacy baseline to ensure no metric
is ever missing.

### Meta-Drift Surveillance (`meta_drift.py`)

`MetaDriftEngine` combines two drift signals:

| Signal | Weight | Source |
|--------|--------|--------|
| Statistical drift (Rating 2.0 average shift) | 0.4 | `hltv_metadata.db` via `ProPlayerStatCard` |
| Spatial drift (position centroid shift) | 0.6 | `database.db` via `PlayerTickState` |

- Spatial drift uses `P-MD-01`: actual map dimensions from `spatial_data`
  when available, falling back to observed data spread.
- Drift threshold: 10% of map extent or 500 world units, whichever is larger.
- Final coefficient in `[0.0, 1.0]` feeds `get_meta_confidence_adjustment()`
  which returns a coaching confidence multiplier in `[0.5, 1.0]`.

### Role Threshold Learning (`role_thresholds.py`)

`RoleThresholdStore` follows the **Anti-Mock Principle**: every threshold
starts as `None` and is populated exclusively from real data.

- **Cold-start detection:** `is_cold_start()` returns `True` until at least
  3 thresholds have `>= MIN_SAMPLES_FOR_VALIDITY` (30) unique players.
- **Consistency validation:** `validate_consistency()` checks range `[0, 1]`
  before any persistence (`P-RT-03`).
- **Percentile learning:** `learn_from_pro_data()` computes the 75th
  percentile for each role stat (`P-RT-01`), counting unique players not
  total data points (`P-RT-02`).
- **Thread-safe singleton:** `get_role_threshold_store()` uses double-checked
  locking (`P3-06`).
- **Database persistence:** `persist_to_db()` / `load_from_db()` use the
  `RoleThresholdRecord` model for recovery across restarts.

### Nickname Resolution (`nickname_resolver.py`)

Bridges demo player names (e.g. `"Spirit donk"`, `"s1mple-G2-"`) to HLTV
`ProPlayer.hltv_id` through a three-stage pipeline:

1. **Exact match** -- case-insensitive SQL query.
2. **Substring match** -- checks if any known nickname is contained in the
   cleaned demo name.
3. **Fuzzy match** -- `SequenceMatcher` with `FUZZY_THRESHOLD = 0.8`.

Complexity note (`F2-41`): substring + fuzzy lookup is `O(n)` per query,
acceptable for < 1000 registered pros.

## Integration Points

| Consumer | Usage |
|----------|-------|
| `CoachingService` | Calls `get_pro_baseline()` and `calculate_deviations()` to generate Z-score reports |
| `Teacher` daemon | Calls `MetaDriftEngine.calculate_drift_coefficient()` after retraining |
| `AnalysisOrchestrator` | Uses `TemporalBaselineDecay.get_temporal_baseline()` for recency-weighted comparisons |
| `RoleClassifier` | Reads `get_role_threshold_store()` for learned thresholds |
| `NicknameResolver` | Called during demo ingestion to tag pro players |
| `role_features.py` | Calls `MetaDriftEngine.get_meta_confidence_adjustment()` for adaptive signatures |

## Data Sources

- **`hltv_metadata.db`** -- `ProPlayer`, `ProPlayerStatCard`, `ProTeam`
  tables populated by the HLTV scraping pipeline.
- **`database.db`** -- `PlayerMatchStats`, `PlayerTickState` for spatial
  drift analysis and pro position retrieval.
- **Per-match databases** -- `match_data/<id>.db` for `get_pro_positions()`.
- **CSV fallback** -- `data/external/all_Time_best_Players_Stats.csv`.

## Development Notes

- All baseline functions are **pure readers** -- they never mutate the
  database.  Only `RoleThresholdStore.persist_to_db()` writes.
- Structured logging uses `get_logger("cs2analyzer.<module>")`.
- The `HARD_DEFAULT_BASELINE` dict is the last resort and should be updated
  periodically to reflect current pro averages.
- `get_pro_positions()` caps output via uniform sampling to bound memory.
- `R4-20-01`: Database queries use `.limit()` and `.yield_per(500)` to
  prevent unbounded memory consumption.
