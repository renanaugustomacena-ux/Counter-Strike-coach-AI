> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Apps — User Interface Layer

> **Authority:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Overview

The `apps/` directory contains all user-facing interface code for the Macena CS2 Analyzer.
The sole active UI framework is `qt_app/` — a production desktop application built with PySide6
(Qt6). It was chosen for its native look-and-feel, mature threading model (QThreadPool/QRunnable),
powerful custom-widget painting (QPainter), and broad cross-platform support.

`qt_app/` is a strictly consumer layer: it shares the same backend services (`backend/services/`),
database layer (`backend/storage/`), and configuration system (`core/config.py`), and limits its
database writes to user-owned records (profile, settings, notification read flags).

> **Historical note:** A Kivy + KivyMD prototype (`legacy_kivy/`) served as the early-development
> shell. It was replaced by the Qt frontend and removed in June 2026 (commit `4f04f06`).

## Directory Structure

```
apps/
├── __init__.py
├── README.md                    # This file
├── README_IT.md                 # Italian translation
├── README_PT.md                 # Portuguese translation
│
└── qt_app/                      # Active PySide6 / Qt6
    ├── __init__.py
    ├── app.py                   # Application entry point
    ├── main_window.py           # QMainWindow with sidebar navigation
    │
    ├── core/                    # Shared infrastructure
    │   ├── app_state.py         # AppState singleton — polls CoachState every 10s
    │   ├── worker.py            # Background Worker (QRunnable) pattern
    │   ├── theme_engine.py      # Token-driven theming (CS2, CSGO, CS1.6): QSS render, QPalette, fonts, wallpapers
    │   ├── design_tokens.py     # Design token definitions for the Qt component system
    │   ├── qss_generator.py     # Renders themes/base.qss.template with token substitution
    │   ├── animation.py         # Shared animation utilities
    │   ├── easing.py            # Custom easing curves
    │   ├── typography.py        # Typography scale and font helpers
    │   ├── icons.py             # IconProvider facade — SVG sprite, QPainterPath fallback
    │   ├── svg_icon_provider.py # QIconEngine backed by SVG resources
    │   ├── i18n_bridge.py       # Localization (en, pt, it) via JSON + fallback
    │   ├── sound.py             # Sound effect playback helpers
    │   ├── match_utils.py       # Match-level utility functions for the UI layer
    │   ├── widgets_helpers.py   # Generic Qt widget helper functions
    │   ├── web_bridge.py        # Python↔JavaScript bridge for embedded web views
    │   └── qt_playback_engine.py # QTimer-based demo playback
    │
    ├── screens/                 # One QWidget per screen (View layer) — 15 screens
    │   ├── home_screen.py           # Dashboard — service status, match count, training
    │   ├── coach_screen.py          # AI Coach — chat interface, coaching insights
    │   ├── match_history_screen.py  # Match list with search and filters
    │   ├── match_detail_screen.py   # Single match analysis (rounds, economy, events)
    │   ├── performance_screen.py    # Player statistics and trends
    │   ├── tactical_viewer_screen.py # 2D map viewer with playback controls
    │   ├── pro_comparison_screen.py # Side-by-side user vs pro player analysis
    │   ├── pro_player_detail_screen.py # Pro player profile view
    │   ├── wizard_screen.py         # First-run setup (Steam path, player name)
    │   ├── settings_screen.py       # App settings (theme, font, language, paths)
    │   ├── user_profile_screen.py   # User profile editor
    │   ├── profile_screen.py        # Player profile overview
    │   ├── steam_config_screen.py   # Steam integration settings
    │   ├── faceit_config_screen.py  # FACEIT integration settings
    │   ├── help_screen.py           # Help documentation viewer
    │   └── placeholder.py           # Placeholder factory (all entries overridden by real screens)
    │
    ├── viewmodels/              # ViewModel layer (QObject subclasses)
    │   ├── coach_vm.py              # CoachViewModel — orchestrates coaching queries
    │   ├── coaching_chat_vm.py      # Chat history and message handling
    │   ├── focus_insight_vm.py      # Focused coaching insight detail ViewModel
    │   ├── match_history_vm.py      # Match list data fetching and filtering
    │   ├── match_detail_vm.py       # Single match data loading
    │   ├── performance_vm.py        # Player stats aggregation
    │   ├── pro_comparison_vm.py     # Pro comparison data and scoring
    │   ├── pro_player_detail_vm.py  # Pro player profile data loading
    │   ├── tactical_vm.py           # Tactical data and playback state
    │   └── user_profile_vm.py       # User profile CRUD operations
    │
    ├── widgets/                 # Reusable widget library
    │   ├── toast.py             # Toast notification overlay
    │   ├── skeleton.py          # Skeleton loading placeholder widgets
    │   ├── charts/              # QPainter visualizations (QtCharts removed — GPL-only)
    │   │   ├── economy_chart.py     # Round-by-round economy bars (QPainter)
    │   │   ├── mini_sparkline.py    # Compact sparkline (QPainter, no axes)
    │   │   ├── momentum_chart.py    # K-D delta momentum area chart (QPainter)
    │   │   ├── radar_chart.py       # N-axis skill radar (QPainter)
    │   │   ├── rating_sparkline.py  # Rating trend with baseline (QPainter)
    │   │   └── utility_bar_chart.py # Utility usage bars (QPainter)
    │   ├── coaching/            # Coaching widgets (ChatPanel embedded in CoachScreen)
    │   ├── components/          # Reusable UI components (design system) — 26 modules
    │   │   ├── __init__.py          # Component exports
    │   │   ├── card.py              # Card container widget (5 depth variants)
    │   │   ├── db_record_card.py    # Mono DB row echo (table · column · value)
    │   │   ├── delta_chip.py        # Benchmark-relative delta pill
    │   │   ├── drivers_list.py      # Signed contribution rows (what moved a stat)
    │   │   ├── empty_state.py       # Empty state placeholder with icon and message
    │   │   ├── filter_chip.py       # Toggleable filter pill
    │   │   ├── focus_insight.py     # Focus insight card (home screen)
    │   │   ├── hero_stats_strip.py  # Horizontal strip of hero metrics
    │   │   ├── icon_widget.py       # Icon display widget (SVG/pixmap)
    │   │   ├── last_match_hero.py   # Last-match hero card (home screen)
    │   │   ├── map_tile.py          # Per-map stat tile with win-rate accent
    │   │   ├── match_mini_card.py   # Compact match summary card
    │   │   ├── match_row_card.py    # Expanded match row card
    │   │   ├── metric_bar_row.py    # Label + horizontal metric bar + value
    │   │   ├── mini_link_card.py    # Small related-link navigation card
    │   │   ├── mono_footer.py       # Mono provenance/status footer line
    │   │   ├── nav_sidebar.py       # Collapsible navigation sidebar component
    │   │   ├── numbered_step.py     # 01/02/03 accent-mono step row
    │   │   ├── pro_badge.py         # PRO/tier pill for pro-player surfaces
    │   │   ├── progress_ring.py     # Circular progress ring indicator
    │   │   ├── section_header.py    # Section header with title and optional action
    │   │   ├── stat_badge.py        # Stat badge with label and value
    │   │   ├── status_chip.py       # Colored status pill with text label
    │   │   ├── stepper.py           # Step progress indicator
    │   │   ├── tip_box.py           # Accent-bordered tip/callout box
    │   │   └── toggle_switch.py     # Animated boolean switch
    │   └── tactical/            # Tactical viewer components
    │       ├── _paint_utils.py      # Shared QPainter helpers (map + timeline)
    │       ├── map_widget.py        # 2D map renderer (QPainter, TacticalMapWidget)
    │       ├── player_sidebar.py    # Player info panel
    │       └── timeline_widget.py   # Round timeline scrubber
    │
    ├── web/                     # TypeScript web sub-apps (embedded via QWebEngineView)
    │   ├── coach-chat/          # Coach chat React app
    │   ├── match-detail/        # Match detail React app
    │   ├── tactical-viewer/     # Tactical viewer React app
    │   └── shared/              # Shared TypeScript utilities
    │
    └── themes/                  # QSS source
        └── base.qss.template    # Token-substituted stylesheet — sole QSS source
                                 # (rendered per theme by core/qss_generator.py)
```

## MVVM Architecture

The Qt app follows the **Model-View-ViewModel** pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                        View (Screen)                            │
│  - QWidget subclass, pure layout and display                    │
│  - Connects to ViewModel signals in on_enter()                  │
│  - NEVER imports backend modules or database models              │
│  - Calls ViewModel methods to trigger data operations            │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Qt Signals (result, error, finished)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ViewModel (QObject)                          │
│  - Owns business logic and state for one screen                 │
│  - Spawns Worker (QRunnable) for database queries               │
│  - Emits typed Signals with results (auto-marshaled to UI)      │
│  - May read AppState signals for live backend data              │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Worker (background thread)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Model (SQLModel / DB)                         │
│  - backend/storage/database.py (get_db_manager singleton)       │
│  - backend/storage/db_models.py (SQLModel ORM classes)          │
│  - Read-only from the UI perspective                            │
└─────────────────────────────────────────────────────────────────┘
```

**Key contract:** Views never call `get_db_manager()` or import anything from
`backend/storage/`. All data flows through ViewModels.

## Entry Points

### Primary (Qt)

```bash
# From project root, with venv activated:
python -m Programma_CS2_RENAN.apps.qt_app.app

# Or via the launcher script at the repository root (uses .venv, clears stale bytecode):
./launch.sh
```

The boot sequence in `app.py`:
1. High-DPI scaling configured
2. `QApplication` created, version read from package metadata
3. `ThemeEngine` created and custom fonts registered; a themed splash screen (colors from the active theme's design tokens) is shown
4. Graceful shutdown handler connected (`aboutToQuit`)
5. Persisted theme and font settings applied
6. `MainWindow` created with sidebar navigation
7. All 15 screens instantiated and registered in the `QStackedWidget`; cross-screen signals wired (match selection → detail, wizard → home, highlight moments → tactical viewer, pro comparison → pro detail)
8. First-run gate: shows `WizardScreen` if setup not completed, else `HomeScreen`
9. Backend console booted (`get_console().boot()`) and the Session Engine daemon launched
10. SBERT language model checked (downloaded on first run, with splash progress)
11. `AppState` polling started (10-second interval)

### PyInstaller Bundle

The application can also be launched from a PyInstaller-built executable. See the
`packaging/` directory for the `.spec` file and build instructions.

## Shared Patterns

### Worker Pattern (`core/worker.py`)

All background operations use the `Worker` class, which wraps a callable in a
`QRunnable` and emits results via Signals:

```python
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from PySide6.QtCore import QThreadPool

worker = Worker(some_db_query, arg1, arg2)
worker.signals.result.connect(self._on_data_loaded)
worker.signals.error.connect(self._on_error)
QThreadPool.globalInstance().start(worker)
```

This pattern ensures all heavy work runs off the main thread without blocking the Qt event loop.

### AppState (`core/app_state.py`)

The `AppState` singleton polls the `CoachState` database row every 10 seconds and
emits change-only signals. Screens connect to these in their `on_enter()` method:

- `service_active_changed(bool)` — backend daemon heartbeat
- `coach_status_changed(str)` — ingestion/training status text
- `parsing_progress_changed(float)` — demo parsing progress (0.0-1.0)
- `belief_confidence_changed(float)` — model confidence level
- `total_matches_changed(int)` — total ingested matches
- `training_changed(dict)` — epoch, loss, ETA bundle
- `notification_received(str, str)` — severity + message for toast display

### Theming (`core/theme_engine.py`)

Three built-in themes mirror the Counter-Strike franchise eras:

| Theme | Accent Color | Surface |
|-------|-------------|---------|
| CS2 | Tactical orange (`#FF6A00`) | Deep navy (`#0B1628`) |
| CSGO | Steel blue (`#617D8C`) | Dark slate (`#1A1C21`) |
| CS 1.6 | Green (`#4DB04F`) | Dark green (`#121A12`) |

Both the QSS (rendered from `themes/base.qss.template` by `core/qss_generator.py`)
and the `QPalette` for non-styled widgets derive from the same per-theme design
tokens (`core/design_tokens.py`, generated from `design/tokens/design-tokens.json`).
Custom fonts (Roboto, JetBrains Mono, CS Regular, YUPIX, New Hope) are registered
at startup, plus a display stack auto-scanned from `assets/fonts/` (Space Grotesk, Inter).

### Localization (`core/i18n_bridge.py`)

Three languages are supported: English, Portuguese, Italian. String resolution order:
1. JSON translation file (`assets/i18n/{lang}.json`)
2. Hardcoded translation dict (current language)
3. English fallback
4. Caller-supplied default (if provided)
5. Raw key (if nothing matched)

Language changes emit a `language_changed` signal. Screens implement `retranslate()`
to update their labels dynamically.

## Development Guidelines

1. **Background threading is mandatory** — never block the main thread with DB queries,
   network calls, or file I/O. Use `Worker` from `core/worker.py`.
2. **Connect to `AppState` signals in `on_enter()`** — this is the live data bus
   from the backend. Do not poll the database from screens.
3. **Charts are custom QPainter widgets** (not matplotlib, and not QtCharts — the latter
   is GPL-only and was removed for license compliance) — lightweight, token-themed,
   guarded by a license-gate test in `tests/test_charts.py`.
4. **Localization** — all user-visible strings must go through `i18n_bridge.get_text(key)`.
   Never hardcode display text in screen code.
5. **Themes** — use `design_tokens.get_tokens()` fields for colors and never hardcode
   hex values. Tokens are generated from `design/tokens/design-tokens.json`; the QSS
   template and the QPalette both derive from the same `DesignTokens` instance.
6. **Screens don't import each other** — navigation is handled by `MainWindow.switch_screen()`.
   Inter-screen communication goes through signals or `AppState`.
7. **Every screen must implement `on_enter()`** — called by `MainWindow` when the screen
   becomes visible. Use it to refresh data and connect signals.
8. **Implement `retranslate()`** — called when the user switches language. Update all
    user-visible labels from `i18n_bridge`.

## Development Notes

- The Qt app requires **PySide6 6.11.0** (pinned in `requirements.txt`) and **Python 3.10+**.
- The sole QSS source is `qt_app/themes/base.qss.template`; the legacy per-theme
  `.qss` files were removed (commits `73ec5ed`, `5ce891b`). Visual changes go through
  design tokens and the template; do not inline styles in Python code.
- The `placeholder.py` factory creates simple named placeholder screens (centered title + description). At boot every placeholder entry is overridden by a real screen implementation; the factory remains as a registration safety net.
- `MainWindow` layers the content area with a `QStackedLayout` (`StackAll` mode):
  background (optional wallpaper at 15% opacity plus a subtle tactical-grid motif)
  beneath the transparent screen stack. Toast notifications float as a separate
  top-right child overlay, outside the stacked layout.
- The backend console (`get_console().boot()`) may fail without breaking the UI.
  A warning dialog is shown, and the application continues in degraded mode.

## File Count

- `qt_app/`: 92 Python files (`app.py`, `main_window.py`, `core/`, `screens/`, `viewmodels/`, `widgets/`) + 1 QSS template (`themes/base.qss.template`) + 3 embedded web sub-apps
