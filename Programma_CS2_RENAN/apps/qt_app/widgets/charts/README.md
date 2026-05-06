# `apps/qt_app/widgets/charts/` — Dashboard chart widgets

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Matplotlib-backed chart widgets used across the dashboard, performance, and match-detail screens. Each widget renders a Matplotlib figure to a Qt-compatible canvas (`FigureCanvasQTAgg`) and exposes a small Pythonic API for the calling ViewModel — no Matplotlib API surface leaks into the rest of the UI.

## File inventory

| File | Widget | Used By |
|------|--------|---------|
| `__init__.py` | (re-exports) | — |
| `economy_chart.py` | `EconomyChart` | Match Detail (per-round equipment value bars) |
| `mini_sparkline.py` | `MiniSparkline` | Hero stats strip, dashboards (compact trend line) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (cumulative kill-death delta with green/red fill) |
| `radar_chart.py` | `RadarChart` | Performance (skill radar with 5 axes), Pro Comparison |
| `rating_sparkline.py` | `RatingSparkline` | Performance (rating progression with reference lines at 1.0 / 1.1 / 0.9) |
| `round_heatmap.py` | `RoundHeatmap` | Match Detail (per-round outcome grid coloured by win/loss + economy state) |
| `trend_chart.py` | `TrendChart` | Performance (dual-axis: rating left, ADR right, last 20 matches) |
| `utility_bar_chart.py` | `UtilityBarChart` | Performance (grouped horizontal bars: user vs pro average) |

## Conventions

### Color palette

All charts read colors from `core/design_tokens.py`:

- **CT side:** `#5C9EE8` (canonical blue)
- **T side:** `#E8C95C` (canonical gold)
- **Positive trend / strength:** green family
- **Negative trend / weakness:** red family
- **Reference / baseline:** muted gray with dashed stroke

Hard-coding hex values is a code smell — open a token first.

### Memory hygiene

Matplotlib figures are heavy. Every chart widget:

1. Calls `plt.close(fig)` after rendering to free the figure.
2. Holds the canvas, not the figure, as the long-lived reference.
3. Implements `clear()` to release figure memory between data refreshes.

### Theme awareness

Charts subscribe to `theme_engine.themeChanged` and re-render with theme-appropriate styling. Background, text, grid, and reference-line colors all flip per theme.

### Accessibility

- Charts that encode information by colour also include text labels (axis ticks, legend, value annotations).
- `setAccessibleDescription()` provides a one-paragraph summary for screen-reader users (P4-07 in the project's accessibility checklist).
- Color contrast meets WCAG 2.0 AA against the active theme background.

## Adding a chart

1. Subclass `MatplotlibWidget` (defined in `apps/qt_app/widgets/charts/__init__.py` — provides the canvas + `plt.close()` discipline).
2. Implement `render(data)` — accept a typed ViewModel object, never raw DataFrames.
3. Pull colors from `core/design_tokens`.
4. Add a screen-reader description via `setAccessibleDescription()`.
5. Subscribe to `theme_engine.themeChanged` and re-render on theme switch.
6. Add the widget to the inventory table above.

## Do not

- Do not import `matplotlib.pyplot` directly into a screen — go through a chart widget.
- Do not mutate the figure after `render()` returns; create a new figure on data refresh.
- Do not commit colour choices that are not in `design_tokens.py`.

## Related

- Backend data: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
