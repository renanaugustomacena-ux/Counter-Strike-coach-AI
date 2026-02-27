# Visualization & Report Generation

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Overview

Matplotlib-based visualization engine and PDF report generation. Produces heatmaps, engagement maps, momentum charts, utility breakdowns, and multi-section performance reports.

## Key Components

### `visualizer.py`
- **`MatchVisualizer`** — Main visualization class for match analysis
- **Heatmap generation** — Death locations, engagement zones, utility usage overlaid on map layouts
- **Engagement maps** — Player positioning during critical moments with scale-aware markers (micro/standard/macro)
- **Momentum charts** — Round-by-round momentum timeline with win/loss annotations
- **Scale legend** — Visual indicator for critical moment scale (micro=100px, standard=200px, macro=350px)
- Matplotlib figure management with DPI control for high-quality output

### `report_generator.py`
- **PDF report generation** — Multi-page reports with sections: Overview, Round Breakdown, Economy Timeline, Highlights
- **HLTV 2.0 rating visualization** — Bar charts comparing user vs pro baseline
- **Utility breakdown** — Bar charts for HE, molotov, smokes, flashes, unused utility
- **Per-map performance cards** — Rating, K/D, ADR, KAST% by map
- **Strengths/Weaknesses** — Z-score comparison against professional baseline

### `backend/reporting/analytics.py`
- **`get_rating_history()`** — Rating trend over time for sparkline rendering
- **`get_per_map_stats()`** — Aggregated performance statistics grouped by map
- **`get_strength_weakness()`** — Identifies top 3 strengths and weaknesses via Z-score
- **`get_utility_breakdown()`** — User vs pro utility usage comparison with effectiveness metrics
- **`get_hltv2_breakdown()`** — HLTV 2.0 rating component breakdown (K, S, KAST)

## Visualization Patterns

All visualizations use:
- **Map-aware coordinate projection** — Tick coordinates → pixel coordinates via `SpatialData`
- **Z-cutoff handling** — Multi-level maps (Nuke, Vertigo) with vertical plane separation
- **Color consistency** — Team colors (CT=blue, T=orange), severity colors (critical=red, warning=yellow)
- **High-DPI output** — 300 DPI for PDF embedding, 150 DPI for UI preview

## Critical Moment Rendering

- **Micro scale** (1-3 ticks): 100px marker, orange outline
- **Standard scale** (4-10 ticks): 200px marker, red outline
- **Macro scale** (>10 ticks): 350px marker, dark red fill

## Integration

Used by `VisualizationService` for orchestration and UI screens (`PerformanceScreen`, `MatchDetailScreen`) for inline chart rendering.

## Output Formats

- PNG for UI display
- PDF for report export
- SVG for web embedding (future)
