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
| `mini_sparkline.py` | `MiniSparkline` | Last-match hero card on the home screen (compact trend line) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (cumulative kill-death delta with green/red fill) |

## Conventions

### Color palette

All charts resolve colors from `core/design_tokens.py` via `get_tokens()`:

- **Chart background:** `tokens.chart_bg`
- **Primary / secondary series (CT / T):** `tokens.chart_line_primary` / `tokens.chart_line_secondary`
- **Text and axes:** `tokens.text_primary` / `tokens.text_secondary`

Hard-coding hex values is a code smell — add a token first.

### Widget lifecycle

`EconomyChart` and `MomentumChart` rebuild their `QChart` series in `plot(rounds)`;
`MiniSparkline` stores data in `set_values()` and repaints in `paintEvent()`.

### Theme awareness

Charts resolve every color from the active token set (`get_tokens()`) when they are built or replotted, so a theme switch restyles them on the next plot — they hold no hard-coded palette.

### Accessibility

- Charts that encode information by colour also include text labels (axis ticks, legend, value annotations).
- Add a `setAccessibleDescription()` summary for screen-reader users when introducing a new chart.
- Keep color contrast at WCAG 2.0 AA against the active theme background.

## Adding a chart

1. For QtCharts-based: subclass `QChartView`, build a `QChart` in `__init__`, replace series in `plot()`.
   For QPainter-based: subclass `QWidget`, store data in `set_values()`, call `self.update()`, draw in `paintEvent()`.
2. Accept a typed ViewModel object or a typed list — never raw DataFrames.
3. Pull colors from `core/design_tokens` via `get_tokens()`.
4. Add a screen-reader description via `setAccessibleDescription()`.
5. Resolve all colors at plot time so a theme switch restyles on the next plot.
6. Add the widget to the inventory table above.

## Do not

- Do not commit colour choices that are not in `design_tokens.py`.

## Related

- Backend data: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
