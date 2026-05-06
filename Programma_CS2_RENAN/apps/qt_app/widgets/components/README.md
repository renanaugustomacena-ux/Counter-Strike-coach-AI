# `apps/qt_app/widgets/components/` — Generic UI primitives

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Generic, reusable UI primitives consumed by multiple screens. Each component does one thing, is theme-aware (reads from `core/design_tokens.py`), and exposes its state via `Signal`s.

## File inventory

| File | Component | Purpose |
|------|-----------|---------|
| `__init__.py` | — | Package marker; re-exports public components. |
| `card.py` | `Card` | Base elevated-surface container with optional title + body slots. Backed by frosted-glass effect on macOS / Windows 11 with a flat fallback. |
| `empty_state.py` | `EmptyState` | Friendly placeholder shown when a list / table / chart has no data. Includes icon, title, optional CTA. |
| `filter_chip.py` | `FilterChip` | Selectable filter pill — click to toggle, emits `toggled(bool)`. Used by match history and pro comparison. |
| `focus_insight.py` | `FocusInsight` | Card variant for the home page's focus insight (one prominent coaching insight with severity icon). |
| `hero_stats_strip.py` | `HeroStatsStrip` | Horizontal strip of large-format metrics (rating, K/D, ADR, KAST). |
| `icon_widget.py` | `IconWidget` | SVG icon container with theme-aware coloring. Wraps `core/svg_icon_provider.py`. |
| `last_match_hero.py` | `LastMatchHero` | Home-page hero card summarising the most recent match. |
| `match_mini_card.py` | `MatchMiniCard` | Compact match summary card (one row in match history). |
| `match_row_card.py` | `MatchRowCard` | Expanded match card with stat preview (used in match history hero list). |
| `nav_sidebar.py` | `NavSidebar` | Left navigation sidebar with route icons + labels. Subscribes to `app_state.routeChanged`. |
| `progress_ring.py` | `ProgressRing` | Circular progress indicator with optional center label. |
| `section_header.py` | `SectionHeader` | Standardised section-title row (title + optional subtitle + optional action button). |
| `stat_badge.py` | `StatBadge` | Small label + value pill (e.g. `K/D 1.18`, `ADR 78`). |
| `status_chip.py` | `StatusChip` | Coloured status pill (`success`, `warning`, `error`, `info`). Includes both colour and label, never colour-only. |
| `stepper.py` | `Stepper` | Numeric stepper input (`-` / value / `+`). |
| `toggle_switch.py` | `ToggleSwitch` | Animated boolean switch widget. |

## Design system

All components consume tokens from `core/design_tokens.py`. Colors, spacing, radii, and typography are referenced by name — never hard-coded. This guarantees:

- Theme switches (`themeChanged` signal) re-render all components consistently.
- Typography scale changes propagate without per-widget edits.
- Light / dark mode (when added) requires changes only in the token file.

## Conventions

| Convention | Rationale |
|------------|-----------|
| One component per file | Easy to find; small files; safe to extract. |
| Public API via `Signal`s, not callbacks | Decouples widget from screen; testable via `QSignalSpy`. |
| `setAccessibleName()` on every interactive component | WCAG compliance + screen-reader support. |
| Status colour always paired with text or icon | Never colour-only; helps colour-blind users (WCAG 1.4.1). |
| Hover / focus / active states explicit | Avoid the "default Tailwind look" — make state visible. |

## Adding a component

1. Place the file here with a single class definition.
2. Inherit from the smallest applicable Qt class (`QWidget`, `QFrame`, `QLabel`).
3. Pull colors / spacing / typography from `core/design_tokens`.
4. Expose state via `Signal`s.
5. Add an entry to the inventory table above.
6. If the component is theme-aware, subscribe to `theme_engine.themeChanged`.

## Related

- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme switching: `apps/qt_app/core/theme_engine.py`
- Domain-specific widgets: `widgets/charts/`, `widgets/coaching/`, `widgets/tactical/`
- Parent: `apps/qt_app/widgets/README.md`
