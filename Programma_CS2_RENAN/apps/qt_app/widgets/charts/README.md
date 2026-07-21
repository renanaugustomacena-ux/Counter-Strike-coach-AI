# `apps/qt_app/widgets/charts/` — Dashboard chart widgets

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

QtCharts and QPainter-based chart widgets used across the dashboard, performance, and match-detail screens. Each widget wraps either a `QChartView` (for `QChart`-based charts) or a custom `QWidget` with `paintEvent` (for QPainter-based sparklines), and exposes a small Pythonic API for the calling ViewModel.

## File inventory

| File | Widget | Used By |
|------|--------|---------|
| `__init__.py` | (re-exports) | — |
| `economy_chart.py` | `EconomyChart` | Match Detail (per-round equipment value bars) |
| `mini_sparkline.py` | `MiniSparkline` | Hero stats strip, dashboards (compact trend line) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (cumulative kill-death delta with green/red fill) |

## Conventions

### Color palette

All charts read colors from `core/design_tokens.py`:

- **CT side:** `#5C9EE8` (canonical blue)
- **T side:** `#E8C95C` (canonical gold)
- **Positive trend / strength:** green family
- **Negative trend / weakness:** red family
- **Reference / baseline:** muted gray with dashed stroke

Hard-coding hex values is a code smell — open a token first.

### Widget lifecycle

Each chart widget handles data updates via a `set_*()` / `update()` API.
`QChartView`-based widgets replace the `QChart` series on update;
QPainter-based widgets call `update()` to trigger a repaint.

### Theme awareness

Charts subscribe to `theme_engine.themeChanged` and re-render with theme-appropriate styling. Background, text, grid, and reference-line colors all flip per theme.

### Accessibility

- Charts that encode information by colour also include text labels (axis ticks, legend, value annotations).
- `setAccessibleDescription()` provides a one-paragraph summary for screen-reader users (P4-07 in the project's accessibility checklist).
- Color contrast meets WCAG 2.0 AA against the active theme background.

## Adding a chart

1. For QtCharts-based: subclass `QChartView`, build a `QChart` in `__init__`, replace series in `update_data()`.
   For QPainter-based: subclass `QWidget`, store data in `set_values()`, call `self.update()`, draw in `paintEvent()`.
2. Accept a typed ViewModel object or a typed list — never raw DataFrames.
3. Pull colors from `core/design_tokens`.
4. Add a screen-reader description via `setAccessibleDescription()`.
5. Subscribe to `theme_engine.themeChanged` and re-render on theme switch.
6. Add the widget to the inventory table above.

## Do not

- Do not commit colour choices that are not in `design_tokens.py`.

## Related

- Backend data: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
