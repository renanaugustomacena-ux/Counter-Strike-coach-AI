# Reporting — Dashboard Analytics Engine

> **Authority:** Rule 1 (Correctness), Rule 2 (Backend Sovereignty)
> **Skill:** `/correctness-check`

This module provides the math and data aggregation layer for the dashboard UI. It computes player trends, skill radar data, and pro baselines — all read-only queries with no mutations.

**Note:** This is distinct from the top-level `Programma_CS2_RENAN/reporting/` directory, which handles PDF generation and visualization output. This module focuses on data computation.

## File Inventory

| File | Lines | Purpose | Key Classes |
|------|-------|---------|-------------|
| `analytics.py` | 351 | Dashboard math engine | `AnalyticsEngine` |

## `AnalyticsEngine` — Key Methods

### `get_player_trends(player_name, limit=20)` → DataFrame

Fetches historical performance metrics for trend graphs:
- Queries `PlayerMatchStats` where `player_name` matches and `is_pro == False`
- Orders by `processed_at DESC`, limits to 20 records
- Returns DataFrame in chronological order (reversed)

### `get_skill_radar(player_name)` → Dict

Computes normalized skill attributes (0-100) vs. professional baseline:

| Skill Axis | Formula |
|-----------|---------|
| **Aim** | `(accuracy * 0.5) + (HS% * 0.5)` |
| **Utility** | `(blind_enemies / 2.0 * 100 * 0.6) + (flash_assists / 1.0 * 100 * 0.4)` |
| **Positioning** | `min(100, (KAST / 0.75) * 100)` |
| (additional axes) | See full implementation |

Returns empty dict `{}` if insufficient data.

### `compute_pro_baselines()` → Dict

Aggregates professional player statistics from `PlayerMatchStats` where `is_pro == True` for calibration against user performance.

### `get_coach_state(player_name)` → CoachState

Fetches the latest `CoachState` record for status display.

## Integration

```
UI Dashboard (Qt)
    │
    ├── PerformanceViewModel
    │       └── AnalyticsEngine.get_player_trends() → trend_chart data
    │       └── AnalyticsEngine.get_skill_radar() → radar_chart data
    │
    └── HomeScreen
            └── AnalyticsEngine.get_coach_state() → status indicators
```

## Design Patterns

- **Single responsibility:** Math and aggregation only — no mutations, no side effects
- **Defensive null-checking:** All methods return safe defaults if data is insufficient
- **Read-only queries:** Uses `get_db_manager().get_session()` for atomic reads
- **Logging:** `get_logger("cs2analyzer.analytics")`

## Development Notes

- All queries use SQLModel ORM, not raw SQL
- Radar chart normalization is heuristic-based (not ML) — adjust weights in the method
- Pro baselines are computed from the same `PlayerMatchStats` table, filtered by `is_pro == True`
- The 20-match limit for trends prevents excessive DB reads while providing meaningful trend lines
- Never cache results in this class — let the ViewModel handle caching/invalidation
