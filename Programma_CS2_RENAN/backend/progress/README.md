# Progress -- Longitudinal Performance Tracking

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Authority:** Rule 1 (Correctness), Rule 4 (Data Persistence)

## Introduction

This module provides temporal analysis of player performance trends across multiple
sessions. It answers the fundamental coaching question: "Is this player improving,
declining, or stable in each metric over time?" The module is intentionally minimal --
two files, one dataclass, one function -- because trend computation must remain a pure
mathematical utility with zero side effects, zero state, and zero database access.

The output of this module feeds directly into the coaching pipeline: when a trend
reaches sufficient confidence, `CoachingService` can emit "Improvement" or
"Regression" insights to the player, turning raw numbers into actionable guidance.

## File Inventory

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 0 | Package marker | -- |
| `longitudinal.py` | 9 | Trend data structure | `FeatureTrend` (dataclass) |
| `trend_analysis.py` | 19 | Statistical trend computation | `compute_trend(values)`, `TREND_CONFIDENCE_SAMPLE_SIZE` |

## Architecture and Concepts

### `FeatureTrend` -- Data Structure

```python
@dataclass
class FeatureTrend:
    feature: str        # e.g., "avg_adr", "kd_ratio"
    slope: float        # Linear regression slope (positive = improving)
    volatility: float   # Standard deviation (consistency measure)
    confidence: float   # min(1.0, sample_count / 30)
```

Each field has a precise interpretation:

- **feature**: The name of the performance metric being tracked. Must match keys
  from `PlayerMatchStats` (e.g., `avg_adr`, `kd_ratio`, `avg_hs`).
- **slope**: The linear regression coefficient computed by `numpy.polyfit(x, y, 1)`.
  A positive slope indicates improvement; negative indicates regression. Units depend
  on the input feature (e.g., ADR per match, K/D ratio per match).
- **volatility**: The standard deviation of the value series. Measures consistency --
  a player with high slope but high volatility is improving erratically.
- **confidence**: A normalized score from 0.0 to 1.0 representing how reliable the
  trend is, computed as `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)`.

### `compute_trend()` -- Statistical Computation

```python
def compute_trend(values: List[float]) -> Tuple[float, float, float]:
    """Returns (slope, volatility, confidence)."""
```

- **Slope**: Linear regression over the value series using `numpy.polyfit` with
  degree 1. The x-axis is simply the index (0, 1, 2, ...), representing sequential
  matches.
- **Volatility**: Standard deviation of the values via `numpy.ndarray.std()`.
- **Confidence**: `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)` where the
  threshold constant is 30 samples.
- **Guard (AC-39-01)**: Returns `(0.0, 0.0, 0.0)` when fewer than 2 data points
  are provided. This prevents `numpy.polyfit` from raising a `LinAlgError` on
  degenerate inputs.

### Confidence Scale

| Samples | Confidence | Interpretation |
|---------|------------|----------------|
| < 2 | 0.0 | No trend (insufficient data) |
| 2--9 | 0.07--0.30 | Very early, unreliable |
| 10--19 | 0.33--0.63 | Emerging trend |
| 20--29 | 0.67--0.97 | Reliable trend |
| 30+ | 1.0 | Full confidence |

The threshold of 30 matches the classical bootstrap confidence interval requirement,
yielding sample error under 8% at the 95% confidence level.

## Integration

```
PlayerMatchStats (historical records in database.db)
        |
        +-- coaching_service.py calls compute_trend() per feature
                |
                +-- slope < 0 + confidence >= 0.6 --> "Regression" insight
                +-- slope > 0 + confidence >= 0.6 --> "Improvement" insight
                +-- confidence < 0.6 --> Suppressed (not enough data)
                        |
                        +-- coaching/longitudinal_engine.py generates coaching text
```

### Downstream Consumers

| Consumer | Module | How It Uses Trends |
|----------|--------|--------------------|
| Coaching Service | `services/coaching_service.py` | Generates longitudinal coaching insights from slope/confidence |
| Longitudinal Engine | `coaching/longitudinal_engine.py` | Produces trend-based coaching narratives |
| Analytics Engine | `reporting/analytics.py` | Feeds dashboard trend graphs |
| Explanation Generator | `coaching/explainability.py` | Includes trend data in coaching explanations |

### Data Flow

1. Demo ingestion populates `PlayerMatchStats` rows in `database.db`.
2. `CoachingService.generate_new_insights()` fetches the player's match history.
3. For each tracked feature, `compute_trend(values)` is called with the historical
   series.
4. The returned `(slope, volatility, confidence)` triple is wrapped in a
   `FeatureTrend` dataclass.
5. Trends with `confidence >= 0.6` are passed to `generate_longitudinal_coaching()`
   to produce human-readable coaching insights.
6. Those insights are persisted as `CoachingInsight` rows in the database.

## Development Notes

- **Pure mathematical utility**: No state, no side effects, no database access, no
  logging. This is intentional -- the module is a leaf dependency.
- **TREND_CONFIDENCE_SAMPLE_SIZE = 30**: This constant is defined in
  `trend_analysis.py` and should not be changed without re-evaluating the statistical
  basis for confidence thresholds.
- **Slope units**: Units depend on the input feature. For ADR, the slope is "ADR
  points per match." For K/D ratio, it is "K/D per match." Comparisons across
  features require normalization (not done here -- handled by the coaching layer).
- **Volatility is absolute**: Standard deviation, not coefficient of variation.
  Compare within the same feature only. A volatility of 5.0 for ADR means something
  very different than 5.0 for K/D.
- **No caching**: Results are computed fresh each time. The coaching service decides
  when to call and how to cache.
- **Thread safety**: Both `FeatureTrend` (immutable dataclass) and `compute_trend()`
  (pure function) are inherently thread-safe.
