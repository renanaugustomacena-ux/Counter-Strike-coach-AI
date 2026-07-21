# `apps/qt_app/widgets/` — Custom Qt widget library

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Reusable custom `QWidget` subclasses that compose into screens. Anything used by more than one screen, or anything large enough to deserve its own file, lives here. Pure single-screen visuals stay inside their owning screen module.

## Layout

```
widgets/
├── __init__.py
├── skeleton.py             # Loading skeletons (shimmer placeholders)
├── toast.py                # Transient notification toasts
├── components/             # Generic UI primitives (cards, badges, chips, ...)
├── charts/                 # QtCharts / QPainter-based charts
├── coaching/               # Coaching widget namespace (reserved; widgets removed PR #32)
└── tactical/               # Tactical-viewer specific widgets
```

| Sub-package | Purpose | README |
|-------------|---------|--------|
| `components/` | Generic UI primitives reused across screens | [components/README.md](components/README.md) |
| `charts/` | QtCharts / QPainter-based charts for the dashboard | [charts/README.md](charts/README.md) |
| `coaching/` | Reserved namespace; all widgets removed in PR #32 | [coaching/README.md](coaching/README.md) |
| `tactical/` | Tactical viewer widgets (map, sidebar, timeline) | [tactical/README.md](tactical/README.md) |

## Top-level files

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `skeleton.py` | `SkeletonLoader` — shimmer placeholder shown while ViewModel data loads. |
| `toast.py` | Transient toast notification with auto-dismiss + action button. Subscribed to `app_state.bus` for global toasts. |

## Conventions

### Composition over inheritance

Most widgets are `QWidget` containers that compose smaller pieces. Avoid deep inheritance trees — they collide with Qt's signal model and complicate theming.

### Theme-aware styling

Every widget reads colors / spacing / typography from `core/design_tokens.py` rather than hard-coding them. The QSS generator in `core/qss_generator.py` materialises tokens into a stylesheet that's applied app-wide.

### Signal-based API

Widgets expose state changes via `Signal` (e.g. `clicked`, `selectionChanged`). Avoid synchronous callbacks — they break MVVM separation.

### Accessibility

- Set `setAccessibleName()` and `setAccessibleDescription()` for any widget that renders semantic content (charts, status indicators).
- Color-coded status (rating, severity) must be paired with text or an icon — never colour-only (WCAG 1.4.1).

## Adding a new widget

1. Decide whether it belongs at `widgets/` (generic), `widgets/components/` (UI primitive), or in a domain sub-package.
2. Inherit from the smallest applicable Qt class (`QWidget`, `QFrame`, `QLabel`).
3. Read tokens via `core/design_tokens` — never hard-code colors.
4. Expose state via `Signal`s, not getters that mutate.
5. Add the widget to its sub-package's README inventory table.
6. If the widget is theme-aware, subscribe to `theme_engine.themeChanged`.

## Related

- Application core: `apps/qt_app/core/README.md`
- Screens (consumers): `apps/qt_app/screens/README.md`
- Parent app: `apps/qt_app/README.md`
