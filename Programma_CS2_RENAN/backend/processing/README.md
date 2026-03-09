> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Processing — Data Pipeline & Feature Engineering

Data processing pipeline orchestrating feature extraction, baseline management, validation, and tensor generation for ML models.

## Top-Level Modules

### Round Statistics
- **round_stats_builder.py** — `build_round_stats()`, `compute_round_rating()`, `aggregate_round_stats_to_match()`, `enrich_from_demo()` — Per-round HLTV 2.0 rating calculation, aggregation to match-level stats, and demo enrichment with noscope/blind kills, flash assists, utility usage.

### Visual Tensors
- **tensor_factory.py** — `TensorFactory` — Generates 5-channel visual tensors for RAP Coach perception layer: Ch0 (view cone), Ch1 (danger zones - placeholder), Ch2 (map context), Ch3 (motion vectors), Ch4 (teammate positions).

### Heatmaps & Visualization
- **heatmap_engine.py** — `HeatmapEngine` — 2D position heatmap generation with Gaussian kernel smoothing for death locations, engagement zones, and utility usage.

### State Reconstruction
- **state_reconstructor.py** — `RAPStateReconstructor` — Full game state reconstruction from tick data for RAP Coach training. Integrates spatial awareness, economy tracking, and momentum state.

### Map Context
- **connect_map_context.py** — Map-aware spatial feature extraction with Z-axis penalty for multi-level maps (Nuke, Vertigo). Integrates with `core/spatial_data.py` for Z-cutoff logic.

## Sub-Packages

### feature_engineering/
Unified feature extraction: `FeatureExtractor` (25-dim vector), HLTV 2.0 rating components, KAST calculation, role-specific features.

### baselines/
Professional baselines, role thresholds, temporal decay, feature drift detection.

### validation/
Demo file validation, schema compliance, drift detection.

## Dependencies
NumPy, Pandas, PyTorch, OpenCV (heatmaps), SQLModel.
