# Visualization & Report Generation

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/reporting/`
**Owner:** Macena CS2 Analyzer presentation layer

## Introduction

This package transforms raw match analysis data into human-readable visual artifacts
and structured reports. It sits at the outermost layer of the architecture, consuming
outputs from the processing, analysis, and coaching pipelines and producing heatmaps,
differential overlays, critical-moment annotations, and multi-section Markdown reports.
All rendering is backed by Matplotlib with deterministic figure lifecycle management
to prevent memory leaks.

## File Inventory

| File | Purpose | Key Exports |
|------|---------|-------------|
| `visualizer.py` | Matplotlib-based map visualisation engine | `MatchVisualizer`, `generate_highlight_report()` |
| `report_generator.py` | Multi-section match report builder | `MatchReportGenerator` |
| `__init__.py` | Package marker | -- |

## Architecture & Concepts

### Map Visualisation Engine (`visualizer.py`)

`MatchVisualizer` is the central rendering class. It produces three categories of
visual output:

1. **Position Heatmaps** (`generate_heatmap`) -- 2D histogram of player positions
   overlaid on the map background. Uses a 64-bin grid with the `"magma"` colourmap
   and a minimum count threshold (`cmin=1`) to suppress empty bins.

2. **Differential Overlays** (`render_differential_overlay`) -- diverging heatmap
   comparing user positioning against professional baselines. The algorithm:
   - Converts each position set to a density grid at configurable `resolution`
     (default 128).
   - Applies Gaussian blur (`sigma=5.0`) via `scipy.ndimage.gaussian_filter`.
   - Normalises each density independently, then computes the difference.
   - Masks regions with negligible activity (`< 0.02` threshold).
   - Renders with `RdBu_r` diverging colourmap and `TwoSlopeNorm` centred at zero.
   - Blue regions indicate user-heavy positioning; red regions indicate pro-heavy.

3. **Critical Moment Maps** (`render_critical_moments`) -- annotated scatter plot of
   key events identified by `ChronovisorScanner`. Each moment is rendered as a
   severity-coloured, type-shaped, scale-sized marker:

   | Severity | Colour | Type | Marker | Scale | Pixel Size |
   |----------|--------|------|--------|-------|------------|
   | critical | red | play | `^` (up triangle) | macro | 350 |
   | critical | red | mistake | `v` (down triangle) | standard | 200 |
   | significant | orange | play/mistake | `^` / `v` | standard | 200 |
   | notable | gold | play/mistake | `o` (circle) | micro | 100 |

4. **Round Error Plots** (`plot_round_errors`) -- scatter plot marking death locations
   (red `x`) and coach-flagged bad decisions (orange `P`) for a single round.

All rendering methods follow the **try/finally** pattern (`DA-VZ-01`), guaranteeing
`plt.close(fig)` even when `savefig` raises. This prevents Matplotlib figure leaks
under error conditions.

#### Map Background & Bounds

Background images are loaded from `assets/maps/` using paths defined in
`data/map_tensors.json`. A path traversal guard (`VZ-02`) validates that the resolved
image path stays within `assets_dir` before loading. Six maps have hardcoded bounds in
`_get_bounds()`: `de_mirage`, `de_inferno`, `de_dust2`, `de_nuke`, `de_overpass`, and
`de_ancient`. Unknown maps fall back to a `(-4000, 4000, -4000, 4000)` bounding box.

### Report Generator (`report_generator.py`)

`MatchReportGenerator` orchestrates the full report pipeline:

1. **Parse** -- loads the demo file via `DemoLoader`.
2. **Extract** -- iterates parsed frames to collect player positions and death events.
3. **Visualise** -- calls `MatchVisualizer.generate_heatmap()` to produce the
   positioning heatmap.
4. **Write** -- produces a timestamped Markdown report file containing:
   - Map name and generation date.
   - Embedded heatmap image (relative path, `RG-02`).
   - Fundamental error analysis section.

Output directory is anchored to `USER_DATA_ROOT/reports` with a path-escape guard
(`RG-01`) ensuring the report stays under the user data root.

#### Security Annotations

| Code | Guard |
|------|-------|
| `DA-VZ-01` | `try/finally` figure closure to prevent memory leaks |
| `VZ-02` | Path traversal prevention for map background images |
| `DA-RG-01` | Absolute path anchoring for report output directory |
| `RG-01` | Path-escape validation ensuring output stays under `USER_DATA_ROOT` |
| `RG-02` | Relative path in Markdown to avoid exposing filesystem structure |

### Highlight Report Integration (`generate_highlight_report`)

The module-level `generate_highlight_report(match_id, map_name)` function bridges
the RAP Coach model with the visualisation engine. It:

1. Checks whether the RAP model is enabled via `get_setting("USE_RAP_MODEL")`.
2. Instantiates `ChronovisorScanner` and scans the match for critical moments.
3. Converts each `CriticalMoment` to a highlight annotation dict.
4. Renders the annotated map image via `render_critical_moments()`.

This function is guarded by a broad `try/except` with error logging, ensuring that
visualisation failures never crash the calling pipeline.

## Integration

| Consumer | Usage |
|----------|-------|
| `apps/qt_app/screens/` | Inline chart rendering in `PerformanceScreen`, `MatchDetailScreen` |
| `backend/services/analysis_orchestrator.py` | Calls `generate_highlight_report()` during post-analysis |
| `backend/nn/rap_coach/chronovisor_scanner.py` | Supplies `CriticalMoment` objects for rendering |
| `ingestion/demo_loader.py` | Provides parsed frames consumed by `MatchReportGenerator` |
| `core/config.py` | `USER_DATA_ROOT` for report output path anchoring |

## Output Formats

| Format | DPI | Use Case |
|--------|-----|----------|
| PNG | 150 | UI display, inline previews |
| PNG (high-res) | 300 | PDF embedding, archival |
| Markdown | -- | Structured text reports with embedded image references |

## Development Notes

- **Figure lifecycle**: every Matplotlib figure must be created and closed within the
  same method scope. Never store figure references as instance attributes.
- **Deterministic output**: file names include map name and timestamp to prevent
  collisions. Heatmap bins and colourmap are fixed for reproducibility.
- **Dependency isolation**: `scipy.ndimage.gaussian_filter` is the only SciPy import;
  `numpy` is used for grid computation. Both are mandatory dependencies.
- **Testing**: visualiser tests use `matplotlib.use("Agg")` to avoid GUI backend
  requirements. Report generator tests mock `DemoLoader` and verify file output.
