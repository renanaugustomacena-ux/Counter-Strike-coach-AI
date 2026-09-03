# `apps/qt_app/widgets/components/` — Generic UI primitives

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Generic, reusable UI primitives consumed by multiple screens. Each component does one thing, is theme-aware (reads from `core/design_tokens.py`), and interactive components expose their state via `Signal`s.

## File inventory

| File | Component | Purpose |
|------|-----------|---------|
| `__init__.py` | — | Package marker; re-exports a subset of the public components. |
| `card.py` | `Card` | Base elevated-surface container with optional title + body slots. Five depth variants (`flat`, `raised`, `highlighted`, `floating`, `frosted`); `frosted` uses a semi-transparent fill approximating backdrop blur. |
| `db_record_card.py` | `DbRecordCard` | Raised card showing a database record: bold title + mono SQL caption + key/value mono grid. A value may carry a semantic token name (`success`, `info`, …) to tint it. |
| `delta_chip.py` | `DeltaChip` | Benchmark-relative delta annotation (`▲ +0.09 vs 47-match avg`). Starts hidden; a zero or unknown delta never renders. |
| `drivers_list.py` | `DriversList` | Vertical list of (severity, text) driver rows — 8px semantic-colored square + body text. Severity ∈ {`success`, `warning`, `error`, `info`}. |
| `empty_state.py` | `EmptyState` | Friendly placeholder shown when a list / table / chart has no data. Icon or illustration, title, optional CTAs plus ghost link row; also has a loading-skeleton mode. |
| `filter_chip.py` | `FilterChip` | Selectable filter pill — click to toggle, emits `toggled(bool)`; optional trailing count badge. Used by match history and pro comparison. |
| `focus_insight.py` | `FocusInsightCard` | Home-page pair card to `LastMatchHeroCard` — surfaces one coachable focus area with a ghost CTA (`open_clicked(str)`); has an empty state. |
| `hero_stats_strip.py` | `HeroStatsStrip` | Horizontal strip of large-format stat blocks (display number + caption, sentiment-colored). |
| `icon_widget.py` | `IconWidget` | QPainterPath icon container with theme-aware coloring. Wraps `core/icons.py` (`IconProvider`). |
| `last_match_hero.py` | `LastMatchHeroCard` | Home-page hero card summarising the most recent match, with a rating-trend `MiniSparkline`; the empty state carries an analyze CTA. |
| `map_tile.py` | `MapTile` | Per-map performance tile: map name, rating line (color + accessibility label), ADR / K/D line, match count, bottom rating-fill bar. Fully QPainter-drawn. |
| `match_mini_card.py` | `MatchMiniCard` | Compact clickable match preview card (home screen "Recent Matches" strip). Emits `clicked(demo_name)`. |
| `match_row_card.py` | `MatchRowCard` | Wide match row with stat preview (match history rows); pro rows swap in player + event line. Emits `clicked(demo_name)`. |
| `metric_bar_row.py` | `MetricBarRow` | Labeled metric with a proportional colored fill bar (Match Detail HLTV 2.0 grid rows). |
| `mini_link_card.py` | `MiniLinkCard` | Small clickable navigation card — bold "Title →" + one-line caption. Emits `clicked`. |
| `mono_footer.py` | `MonoFooter` | Bottom-of-screen mono tertiary annotation line naming the data source. |
| `nav_sidebar.py` | `NavSidebar` | Left navigation sidebar with route icons + labels. Emits `nav_clicked(str)`; collapsible 220px ↔ 60px. |
| `numbered_step.py` | `NumberedStep` | Numbered step row (Getting Started): filled accent circle with the step number + bold title + description. |
| `pro_badge.py` | `ProBadge` | Pill-shaped mono badge ("PRO" by default) with optional CT / T side recoloring via `set_side()`. |
| `progress_ring.py` | `ProgressRing` | Circular progress indicator with optional centered percentage text; size presets `SMALL` / `DEFAULT` / `COACH` / `HERO`. |
| `section_header.py` | `SectionHeader` | Standardised section-title row (title + optional subtitle + optional action widget). |
| `stat_badge.py` | `StatBadge` | Prominent stat value with a label underneath (scope.gg pattern); semantic coloring + optional trend arrow. |
| `status_chip.py` | `StatusChip` | Coloured status pill (`online`, `offline`, `warning`, `neutral`). Includes both colour and label, never colour-only. |
| `stepper.py` | `Stepper` | Horizontal step indicator (dots + connector bars, optional labels) for the first-run wizard. Emits `step_changed(int)`. |
| `tip_box.py` | `TipBox` | Dashed info-outline callout: bold info-colored title + secondary body. |
| `toggle_switch.py` | `ToggleSwitch` | Animated iOS-style boolean switch widget. |

## Design system

All components consume tokens from `core/design_tokens.py` (generated from `design/tokens/design-tokens.json`). Colors, spacing, radii, and typography are referenced by name — never hard-coded. Theming works as follows:

- Three token sets (`CS2`, `CSGO`, `CS1.6`) share one structural contract; `theme_engine.apply_theme()` swaps the active set.
- The single stylesheet source is `themes/base.qss.template`, rendered per theme by `core/qss_generator.py` — there are no per-theme QSS files.
- The `QPalette` is derived from the same tokens, so widgets that bypass QSS still match.
- Theme switches (`theme_changed` signal) re-style all components consistently.

## Conventions

| Convention | Rationale |
|------------|-----------|
| One component per file | Easy to find; small files; safe to extract. |
| Public API via `Signal`s, not callbacks | Decouples widget from screen; testable via `QSignalSpy`. |
| Status colour always paired with text or icon | Never colour-only; helps colour-blind users (WCAG 1.4.1). |
| Hover / focus / active states explicit | Avoid the "default Tailwind look" — make state visible. |

## Adding a component

1. Place the file here with a single class definition.
2. Inherit from the smallest applicable Qt class (`QWidget`, `QFrame`, `QLabel`).
3. Pull colors / spacing / typography from `core/design_tokens`.
4. Expose state via `Signal`s.
5. Add an entry to the inventory table above.
6. If the component is theme-aware, resolve colors from the active token set (`get_tokens()`) or connect to `theme_engine.theme_changed`.

## Related

- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme switching: `apps/qt_app/core/theme_engine.py`
- QSS template: `apps/qt_app/themes/base.qss.template` (rendered by `core/qss_generator.py`)
- Domain-specific widgets: `widgets/charts/`, `widgets/coaching/`, `widgets/tactical/`
- Parent: `apps/qt_app/widgets/README.md`
