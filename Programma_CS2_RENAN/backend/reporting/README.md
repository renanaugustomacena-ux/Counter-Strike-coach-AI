# Reporting -- Dashboard Analytics Engine

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Authority:** Rule 1 (Correctness), Rule 2 (Backend Sovereignty)
> **Skill:** `/correctness-check`

## Introduction

This module provides the math and data aggregation layer for the dashboard UI. It
computes player trends, skill radar data, training metrics, rating history, per-map
statistics, strength/weakness analysis, utility breakdowns, and HLTV 2.0 rating
component decomposition. All methods are read-only queries with no mutations.

**Important distinction:** This is `backend/reporting/`, which focuses on data
computation for the Qt dashboard. It is separate from the top-level
`Programma_CS2_RENAN/reporting/` directory, which handles PDF generation and
visualization output files.

## File Inventory

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 0 | Package marker | -- |
| `analytics.py` | 353 | Dashboard math engine | `AnalyticsEngine`, `analytics` (singleton) |

## Architecture and Concepts

### `AnalyticsEngine` -- Central Dashboard Data Provider

The `AnalyticsEngine` class is the single entry point for all dashboard data
aggregation. It owns a reference to the database manager (obtained via
`get_db_manager()`) and exposes seven public methods, each returning a specific
data shape for a UI widget.

#### `get_player_trends(player_name, limit=20)` -> DataFrame

Fetches historical performance metrics for the trend graph widget:

- Queries `PlayerMatchStats` where `player_name` matches and `is_pro == False`
- Orders by `processed_at DESC`, limits to `limit` records (default 20)
- Converts results to a pandas DataFrame in chronological order (reversed)
- Returns an empty DataFrame if no data exists

#### `get_skill_radar(player_name)` -> Dict

Computes normalized skill attributes (0--100) for the radar chart widget:

| Skill Axis | Formula | Ceiling |
|-----------|---------|---------|
| **Aim** | `(accuracy * 100 * 0.5) + (HS% * 100 * 0.5)` | 100 |
| **Utility** | `(blind_enemies / 2.0 * 100 * 0.6) + (flash_assists / 1.0 * 100 * 0.4)` | 100 |
| **Positioning** | `min(100, (KAST / 0.75) * 100)` | 100 |
| **Map Sense** | `min(100, (ADR / 100.0) * 100)` | 100 |
| **Clutch** | `min(100, clutch_win_pct * 100)` | 100 |

Returns empty dict `{}` if insufficient data.

#### `get_training_metrics()` -> Dict

Fetches the latest training telemetry from the `CoachState` table in the knowledge
session context. Returns epoch, total_epochs, train/val loss, and belief confidence.

#### `get_rating_history(player_name, limit=50)` -> List

Returns a chronologically ordered list of `{rating, match_date, demo_name}` dicts
for the rating timeline widget. Filters out pro matches (`is_pro == False`).

#### `get_per_map_stats(player_name)` -> Dict

Aggregates per-map performance into `{map_name: {rating, adr, kd, matches}}`:

- Extracts map names from `demo_name` using regex pattern `(de_\w+|cs_\w+|ar_\w+)`
- Groups matches by map and computes mean rating, ADR, and K/D per map
- Maps that cannot be identified are grouped under `"unknown"`

#### `get_strength_weakness(player_name)` -> Dict

Computes Z-score deviations versus the pro baseline for key metrics:

- Fetches player averages for rating, K/D, ADR, KAST, HS%, accuracy, clutch%,
  and opening duel%
- Calls `calculate_deviations()` from `pro_baseline.py` to get Z-scores
- Z-score > 0.5 qualifies as a strength; Z-score < -0.5 qualifies as a weakness
- Returns top 5 strengths and top 5 weaknesses, sorted by magnitude

#### `get_utility_breakdown(player_name)` -> Dict

Per-utility comparison between user and pro averages for 6 utility metrics:
`he_damage`, `molotov_damage`, `smokes_per_round`, `flash_blind_time`,
`flash_assists`, `unused_utility`. The pro baseline is queried from real DB data
(`is_pro == True`). If no pro data exists, the pro dict is returned empty
(Anti-Fabrication Rule).

#### `get_hltv2_breakdown(player_name)` -> Dict

Decomposes the player's HLTV 2.0 rating into its five components: Kill, Survival,
KAST, Impact, and Damage. Each component is normalized against the HLTV baseline
constants imported from `rating.py`.

### Module-Level Singleton

```python
analytics = AnalyticsEngine()
```

The module exposes a pre-constructed singleton `analytics` for direct import by
ViewModels. This avoids repeated `get_db_manager()` calls while keeping the class
testable via direct instantiation.

## Integration

```
UI Dashboard (Qt MVVM)
    |
    +-- PerformanceViewModel
    |       +-- analytics.get_player_trends()    --> trend chart
    |       +-- analytics.get_skill_radar()      --> radar chart
    |       +-- analytics.get_rating_history()   --> rating timeline
    |       +-- analytics.get_per_map_stats()    --> map breakdown
    |
    +-- StrengthWeaknessWidget
    |       +-- analytics.get_strength_weakness() --> Z-score cards
    |
    +-- UtilityWidget
    |       +-- analytics.get_utility_breakdown() --> user vs pro bars
    |
    +-- TrainingStatusWidget
            +-- analytics.get_training_metrics()  --> epoch/loss display
```

### Dependencies

| Dependency | Module | Purpose |
|------------|--------|---------|
| `get_db_manager()` | `backend/storage/database.py` | Database session access |
| `PlayerMatchStats` | `backend/storage/db_models.py` | ORM model for match data |
| `CoachState` | `backend/storage/db_models.py` | ORM model for training state |
| `get_pro_baseline()` | `backend/processing/baselines/pro_baseline.py` | Pro baseline for Z-scores |
| `calculate_deviations()` | `backend/processing/baselines/pro_baseline.py` | Z-score computation |
| HLTV 2.0 baselines | `backend/processing/feature_engineering/rating.py` | Rating decomposition |

## Development Notes

- **Read-only contract**: All methods use `get_db_manager().get_session()` for atomic
  reads. No method mutates the database. This is enforced by design, not by code
  guards.
- **Defensive null-checking**: Every method returns a safe default (empty dict, empty
  list, empty DataFrame) if the underlying data is missing or insufficient.
- **All queries use SQLModel ORM**: No raw SQL. This ensures type safety and
  compatibility with the SQLite WAL configuration.
- **Radar normalization is heuristic-based**: The weights (0.5/0.5 for Aim,
  0.6/0.4 for Utility, etc.) are tuning parameters, not ML outputs. Adjust them
  in the method body as the coaching model evolves.
- **Pro baselines from real data**: `get_utility_breakdown()` and
  `get_strength_weakness()` both use real pro data from the database. No fabricated
  values are used as fallback (Anti-Fabrication Rule).
- **No caching in this class**: ViewModels handle caching and invalidation. The
  `AnalyticsEngine` recomputes on every call.
- **Logging**: Uses `get_logger("cs2analyzer.analytics")` for structured error
  logging. All error paths log the exception and return safe defaults.
- **The 20-match default limit** for `get_player_trends()` prevents excessive DB
  reads while providing meaningful trend lines.
