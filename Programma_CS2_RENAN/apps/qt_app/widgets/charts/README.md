# `apps/qt_app/widgets/charts/` — Dashboard chart widgets

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

QPainter chart widgets used across the home, performance, pro-comparison, and match-detail screens. Every widget is a custom `QWidget` with a `paintEvent`, exposing a small Pythonic API for the calling ViewModel. **QtCharts is not used anywhere** — it is GPLv3-or-commercial only and was removed for license compliance; `Programma_CS2_RENAN/tests/test_charts.py::TestQtChartsRetired` fails the suite if a `QtCharts`/`QChart` reference reappears under `apps/qt_app/`.

## File inventory

| File | Widget | Used By |
|------|--------|---------|
| `__init__.py` | `token_color()` helper + re-exports (`EconomyChart`, `MomentumChart`, `RadarChart`) | `token_color()` parses `#RRGGBB` / `rgb()` / `rgba()` design-token strings into `QColor` |
| `economy_chart.py` | `EconomyChart` | Match Detail (per-round equipment value bars, side coloring, $ ladder, `set_half_marker()` divider) |
| `mini_sparkline.py` | `MiniSparkline` | Last-match hero card on the home screen (chrome-less trend line, via `components/last_match_hero.py`) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (per-round K-D swing bars around a zero axis, side-colored, HALF divider) |
| `radar_chart.py` | `RadarChart` | Pro Comparison (N-axis skill radar, N >= 3 — the screen uses 8 axes; dual-series user-vs-pro overlay) |
| `rating_sparkline.py` | `RatingSparkline` | Performance (rating trend with HLTV reference lines at 0.90 / 1.00 / 1.10) |
| `utility_bar_chart.py` | `UtilityBarChart` | Performance (grouped you-vs-pro bars via `set_rows()`, or single-series via `set_single()`) |

## Conventions

### Color palette

All charts resolve colors from `core/design_tokens.py` via `get_tokens()`:

- **Chart background:** `tokens.chart_bg`
- **Primary / secondary series (CT / T):** `tokens.chart_line_primary` / `tokens.chart_line_secondary`
- **Text and axes:** `tokens.text_primary` / `tokens.text_secondary`

Hard-coding hex values is a code smell — add a token first.

### Widget lifecycle

`EconomyChart` and `MomentumChart` store their round data in `plot(rounds)` and repaint;
the other charts store data in their `set_*` methods. All drawing happens in `paintEvent()`.

### Theme awareness

Charts resolve every color from the active token set (`get_tokens()`) inside `paintEvent()`, so a theme switch restyles them on the next repaint — they hold no hard-coded palette.

### Accessibility

- Charts that encode information by colour also include text labels (axis ticks, legend, value annotations).
- Add a `setAccessibleDescription()` summary for screen-reader users when introducing a new chart.
- Keep color contrast at WCAG 2.0 AA against the active theme background.

## Adding a chart

1. Subclass `QWidget`, store data in a `set_*`/`plot()` method, call `self.update()`, draw in `paintEvent()`. (Never QtCharts — see the license note above.)
2. Accept a typed ViewModel object or a typed list — never raw DataFrames.
3. Pull colors from `core/design_tokens` via `get_tokens()`.
4. Add a screen-reader description via `setAccessibleDescription()`.
5. Resolve all colors inside `paintEvent()` so a theme switch restyles on the next repaint.
6. Add the widget to the inventory table above.

## Do not

- Do not commit colour choices that are not in `design_tokens.py`.

## Related

- Backend data: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
