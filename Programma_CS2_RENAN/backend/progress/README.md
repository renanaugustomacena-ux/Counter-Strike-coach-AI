# Progress — Longitudinal Performance Tracking

> **Authority:** Rule 1 (Correctness), Rule 4 (Data Persistence)

This module provides temporal analysis of player performance trends across multiple sessions. It answers the question: "Is this player improving, declining, or stable in each metric?"

## File Inventory

| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|----------------------|
| `longitudinal.py` | 9 | Trend data structure | `FeatureTrend` (dataclass) |
| `trend_analysis.py` | 19 | Compute statistical trends | `compute_trend(values)` |

## `FeatureTrend` — Data Structure

```python
@dataclass
class FeatureTrend:
    feature: str        # e.g., "avg_adr", "kd_ratio"
    slope: float        # Linear regression slope (positive = improving)
    volatility: float   # Standard deviation (consistency measure)
    confidence: float   # min(1.0, sample_count / 30)
```

## `compute_trend()` — Statistical Computation

```python
def compute_trend(values: List[float]) -> Tuple[float, float, float]:
    """Returns (slope, volatility, confidence)."""
```

- **Slope:** Linear regression over the value series (numpy `polyfit` degree 1)
- **Volatility:** Standard deviation of the values (consistency measure)
- **Confidence:** `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)` where threshold = 30 samples
- **Guard:** Returns `(0.0, 0.0, 0.0)` if fewer than 2 values (AC-39-01)

### Confidence Scale

| Samples | Confidence | Interpretation |
|---------|------------|----------------|
| < 2 | 0.0 | No trend (insufficient data) |
| 2-9 | 0.07-0.30 | Very early, unreliable |
| 10-19 | 0.33-0.63 | Emerging trend |
| 20-29 | 0.67-0.97 | Reliable trend |
| 30+ | 1.0 | Full confidence |

## Integration

```
PlayerMatchStats (historical records)
        │
        └── coaching_service.py calls compute_trend() per feature
                │
                ├── slope < 0 + confidence >= 0.6 → "Regression" insight
                ├── slope > 0 + confidence >= 0.6 → "Improvement" insight
                └── confidence < 0.6 → Suppressed (not enough data)
                        │
                        └── coaching/longitudinal_engine.py generates coaching text
```

## Downstream Consumers

- `services/coaching_service.py` — generates longitudinal coaching from trends
- `coaching/longitudinal_engine.py` — produces trend-based coaching narratives
- `reporting/analytics.py` — feeds dashboard trend graphs

## Development Notes

- Pure mathematical utility — no state, no side effects, no database access
- The `TREND_CONFIDENCE_SAMPLE_SIZE = 30` constant matches bootstrap CI requirements (sample ≤ 8% error)
- Slope units depend on the input feature units (e.g., ADR per match, K/D ratio per match)
- Volatility is absolute (not coefficient of variation) — compare within the same feature only
