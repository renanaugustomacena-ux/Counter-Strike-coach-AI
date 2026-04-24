> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Processing -- Data Pipeline, Feature Engineering & Tensor Generation

> **Authority:** Rule 1 (Correctness), Rule 5 (Data Outlives Code),
> Dimensional Contract (`METADATA_DIM = 25`)

The `processing` package is the central data-transformation layer of
the CS2 Coach AI. It sits between raw demo data (produced by
`backend/data_sources/`) and the neural network models (consumed by
`backend/nn/`). Every module in this package converts, enriches, or
validates data -- none of them store or train anything.

## File Inventory

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 1 | Package marker | -- |
| `bombsite_encoding.py` | ~192 | Bombsite centroid encoding and A/B site classification | `encode_bombsite_context()` |
| `connect_map_context.py` | ~112 | Z-aware spatial features relative to map objectives | `distance_with_z_penalty()`, `calculate_map_context_features()` |
| `data_pipeline.py` | ~408 | Data cleaning, scaling, temporal splitting, player decontamination | `ProDataPipeline` |
| `demo_prioritizer.py` | ~344 | Pro-demo prioritization queue scoring (recency, map, rating) | `DemoPrioritizer` |
| `demo_quality.py` | ~408 | Demo quality gates (tick completeness, corruption, coverage) | `DemoQualityAssessor` |
| `external_analytics.py` | ~201 | Z-score comparison against elite CSV reference datasets | `EliteAnalytics` |
| `heatmap_engine.py` | ~300 | Gaussian occupancy maps and differential user-vs-pro heatmaps | `HeatmapEngine`, `HeatmapData`, `DifferentialHeatmapData` |
| `player_knowledge.py` | ~625 | Player-POV perception system (NO-WALLHACK sensorial model) | `PlayerKnowledge`, `PlayerKnowledgeBuilder` |
| `rating.py` | ~230 | Cross-module HLTV rating glue (match-level aggregation) | `compute_match_rating()` |
| `round_reconstructor.py` | ~575 | Per-round state reconstruction from raw tick streams | `RoundReconstructor` |
| `round_stats_builder.py` | ~742 | Per-round, per-player statistics from demo events | `build_round_stats()`, `aggregate_round_stats_to_match()`, `enrich_from_demo()` |
| `skill_assessment.py` | ~161 | 5-axis skill decomposition and curriculum level projection | `SkillLatentModel`, `SkillAxes` |
| `state_reconstructor.py` | ~130 | Tick-to-tensor conversion for RAP-Coach training and inference | `RAPStateReconstructor` |
| `tensor_factory.py` | ~747 | Player-POV perception tensors (map, view, motion) | `TensorFactory`, `TensorConfig`, `TrainingTensorConfig`, `get_tensor_factory()` |
| `tick_enrichment.py` | ~350 | Cross-player contextual features for METADATA_DIM indices 20-24 | `enrich_tick_data()` |

## Sub-Packages

| Sub-Package | Files | Purpose |
|-------------|-------|---------|
| `feature_engineering/` | `vectorizer.py`, `base_features.py`, `role_features.py`, `rating.py`, `kast.py` | Unified 25-dim feature extraction (`FeatureExtractor`), HLTV 2.0 rating, KAST calculation, role-specific features |
| `baselines/` | `pro_baseline.py`, `role_thresholds.py`, `meta_drift.py`, `nickname_resolver.py` | Professional baselines, role thresholds, temporal decay, meta-drift detection, nickname resolution |
| `validation/` | `dem_validator.py`, `schema.py`, `sanity.py`, `drift.py` | Demo file validation, schema compliance, sanity checks, feature drift detection |

## Architecture & Concepts

### Data Flow

```
.dem file
  --> data_sources/ (demoparser2)
    --> tick_enrichment.py (cross-player features)
      --> round_stats_builder.py (per-round aggregation)
        --> data_pipeline.py (cleaning, scaling, splitting)
          --> feature_engineering/vectorizer.py (25-dim vector)
            --> tensor_factory.py (3-channel perception tensors)
              --> nn/ (RAP Coach, JEPA)
```

### Player-POV Perception (NO-WALLHACK)

A core design principle is that the AI coach sees only what the player
legitimately knows at each tick. This is enforced by `player_knowledge.py`
and consumed by `tensor_factory.py`:

- **Own state:** Full access (position, yaw, health, armor, weapon).
- **Teammates:** Always known (radar/comms).
- **Visible enemies:** Only when `enemies_visible > 0` AND within the
  FOV cone. Multi-level maps (Nuke, Vertigo) use a Z-floor threshold.
- **Last-known enemies:** Memory with exponential decay
  (`half-life = MEMORY_DECAY_TAU_TICKS`).
- **Sound inference:** `weapon_fire` events within `HEARING_RANGE_GUNFIRE`.
- **Utility zones:** Active smokes, molotovs, and recent flashes.
- **Bomb state:** Known to all players.

### Tensor Channels

`TensorFactory` produces three 3-channel tensors per tick sequence:

| Tensor | Channel 0 | Channel 1 | Channel 2 |
|--------|-----------|-----------|-----------|
| **map** | Teammate positions | Enemy positions (visible + last-known with decay) | Utility zones + bomb |
| **view** | FOV mask (geometric cone) | Visible entities (distance-weighted) | Active utility zones |
| **motion** | Trajectory trail (last 32 ticks) | Velocity radial gradient | Crosshair yaw-delta encoding |

### Data Pipeline Safeguards

`ProDataPipeline` enforces several data-integrity rules:

- **P-DP-01:** Outlier thresholds derived from training set only
  (prevents data leakage).
- **P-DP-02:** Player decontamination assigns each player to their
  **earliest** temporal split, dropping later-split rows.
- **P-DP-03:** IQR outlier multiplier is a named constant (3.0x).
- **P-DP-04:** Idempotency guard prevents double-scaling.
- **P-DP-05:** Scaler sklearn version check (major.minor comparison).

### Skill Assessment

`SkillLatentModel` decomposes player statistics into five axes:

| Axis | Metrics |
|------|---------|
| Mechanics | `accuracy`, `avg_hs` |
| Positioning | `rating_survival`, `rating_kast` |
| Utility | `utility_blind_time`, `utility_enemies_blinded` |
| Timing | `opening_duel_win_pct`, `positional_aggression_score` |
| Decision | `clutch_win_pct`, `rating_impact` |

The average skill score is projected onto a 1-10 curriculum level via
Gaussian CDF approximation (`sigmoid(1.702 * z)`).

## Integration

- **Ingestion Pipeline:** `tick_enrichment.enrich_tick_data()` is called
  during demo ingestion to compute features 20-24 of the 25-dim vector.
  `round_stats_builder.enrich_from_demo()` produces match-level enrichment.
- **Neural Networks:** `state_reconstructor.RAPStateReconstructor` and
  `tensor_factory.TensorFactory` produce the tensors consumed by
  RAP-Coach and JEPA models.
- **Coaching Engine:** `skill_assessment.SkillLatentModel` feeds the
  curriculum layer. `external_analytics.EliteAnalytics` provides z-score
  comparisons for the correction engine.
- **UI / Visualization:** `heatmap_engine.HeatmapEngine` generates
  RGBA data for position heatmaps and differential overlays.

## Development Notes

- All spatial distance calculations on multi-level maps must use
  `distance_with_z_penalty()` from `connect_map_context.py`, not raw
  Euclidean distance.
- `HeatmapEngine.generate_heatmap_data()` and
  `generate_differential_heatmap_data()` are thread-safe.
- `ProDataPipeline` limits in-memory rows to `_MAX_PIPELINE_ROWS`
  (50,000) to prevent OOM on large deployments.
- `player_knowledge.py` caps tracked enemies at `MAX_TRACKED_ENEMIES`
  (10) and history traversal at `MAX_HISTORY_TICKS` (512).
- The module uses structured logging via
  `get_logger("cs2analyzer.<module>")` with correlation IDs.
- All feature changes must update `FEATURE_NAMES`, `METADATA_DIM`,
  `extract()` docstring, and model `input_dim` assertions.
