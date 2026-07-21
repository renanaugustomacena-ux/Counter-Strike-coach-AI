> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Apps — User Interface Layer

> **Authority:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Overview

The `apps/` directory contains all user-facing interface code for the Macena CS2 Analyzer.
The sole active UI framework is `qt_app/` — a production desktop application built with PySide6
(Qt6). It was chosen for its native look-and-feel, mature threading model (QThreadPool/QRunnable),
built-in chart library (QtCharts), and broad cross-platform support.

`qt_app/` is a strictly consumer layer: it shares the same backend services (`backend/services/`),
database layer (`backend/storage/`), and configuration system (`core/config.py`), but never writes
to the database directly.

> **Historical note:** A Kivy + KivyMD prototype (`legacy_kivy/`) served as the early-development
> shell. It was replaced by the Qt frontend and removed in March 2026 (commit `4f04f06`).

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
    │   ├── theme_engine.py      # QSS themes (CS2, CSGO, CS1.6), palettes, fonts
    │   ├── design_tokens.py     # Design token definitions for the Qt component system
    │   ├── qss_generator.py     # Programmatic QSS generation from design tokens
    │   ├── animation.py         # Shared animation utilities
    │   ├── easing.py            # Custom easing curves
    │   ├── typography.py        # Typography scale and font helpers
    │   ├── icons.py             # Icon registry and SVG/icon asset loader
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
    │   └── placeholder.py           # Placeholder factory for stub screens
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
    │   ├── charts/              # QtCharts / QPainter-based visualizations
    │   │   ├── economy_chart.py     # Round-by-round economy (QtCharts bar chart)
    │   │   ├── mini_sparkline.py    # Compact sparkline (QPainter, no axes)
    │   │   └── momentum_chart.py    # K-D delta momentum (QtCharts area chart)
    │   ├── coaching/            # Coaching widget namespace (reserved; all widgets removed PR #32)
    │   ├── components/          # Reusable UI components (design system)
    │   │   ├── __init__.py          # Component exports
    │   │   ├── card.py              # Card container widget
    │   │   ├── stat_badge.py        # Stat badge with label and value
    │   │   ├── empty_state.py       # Empty state placeholder with icon and message
    │   │   ├── section_header.py    # Section header with title and optional action
    │   │   ├── progress_ring.py     # Circular progress ring indicator
    │   │   ├── icon_widget.py       # Icon display widget (SVG/pixmap)
    │   │   └── nav_sidebar.py       # Navigation sidebar component
    │   └── tactical/            # Tactical viewer components
    │       ├── map_widget.py        # 2D map renderer (QGraphicsView)
    │       ├── player_sidebar.py    # Player info panel
    │       └── timeline_widget.py   # Round timeline scrubber
    │
    ├── web/                     # TypeScript web sub-apps (embedded via QWebEngineView)
    │   ├── coach-chat/          # Coach chat React app
    │   ├── match-detail/        # Match detail React app
    │   ├── tactical-viewer/     # Tactical viewer React app
    │   └── shared/              # Shared TypeScript utilities
    │
    └── themes/                  # QSS stylesheets
        ├── cs2.qss              # CS2 theme (orange accent, dark surface)
        ├── csgo.qss             # CS:GO theme (steel blue accent)
        └── cs16.qss             # CS 1.6 theme (green accent, retro)
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
```

The boot sequence in `app.py`:
1. High-DPI scaling configured
2. `QApplication` created, version read from package metadata
3. Graceful shutdown handler connected (`aboutToQuit`)
4. `ThemeEngine` initialized — custom fonts registered, theme applied
5. `MainWindow` created with sidebar navigation
6. All 15 screens instantiated and registered in the `QStackedWidget`
7. First-run gate: shows `WizardScreen` if setup not completed, else `HomeScreen`
8. Backend console booted (`get_console().boot()`)
9. `AppState` polling started (10-second interval)

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
| CS2 | Orange (`#D96600`) | Dark charcoal |
| CSGO | Steel blue (`#617D8C`) | Slate gray |
| CS 1.6 | Green (`#4DB050`) | Dark olive |

Themes are applied via QSS stylesheets (`themes/*.qss`) plus a `QPalette` for
non-styled widgets. Custom fonts (Roboto, JetBrains Mono, CS Regular, YUPIX,
New Hope) are registered at startup.

### Localization (`core/i18n_bridge.py`)

Three languages are supported: English, Portuguese, Italian. String resolution order:
1. JSON translation file (`assets/i18n/{lang}.json`)
2. Hardcoded translation dict (current language)
3. English fallback
4. Raw key (if nothing matched)

Language changes emit a `language_changed` signal. Screens implement `retranslate()`
to update their labels dynamically.

## Development Guidelines

1. **Background threading is mandatory** — never block the main thread with DB queries,
   network calls, or file I/O. Use `Worker` from `core/worker.py`.
2. **Connect to `AppState` signals in `on_enter()`** — this is the live data bus
   from the backend. Do not poll the database from screens.
3. **Charts use QtCharts** (not matplotlib) — lighter weight, native Qt integration,
   consistent theming via QSS.
4. **Localization** — all user-visible strings must go through `i18n_bridge.get_text(key)`.
   Never hardcode display text in screen code.
5. **Themes** — use `ThemeEngine.get_color(slot)` for colors and never hardcode hex values.
   All visual constants live in `theme_engine.py` or QSS files.
6. **Screens don't import each other** — navigation is handled by `MainWindow.switch_screen()`.
   Inter-screen communication goes through signals or `AppState`.
7. **Every screen must implement `on_enter()`** — called by `MainWindow` when the screen
   becomes visible. Use it to refresh data and connect signals.
8. **Implement `retranslate()`** — called when the user switches language. Update all
    user-visible labels from `i18n_bridge`.

## Development Notes

- The Qt app requires **PySide6 >= 6.5** and **Python 3.10+**.
- QSS stylesheets are in `qt_app/themes/` — one file per theme. Edit these for
  visual changes; do not inline styles in Python code.
- The `placeholder.py` factory generates stub screens that display a "Coming Soon" message for screens under development.
- `MainWindow` uses a `QStackedLayout` with three layers: background wallpaper
  (bottom), screen stack (middle), and toast notifications (top).
- The backend console (`get_console().boot()`) may fail without breaking the UI.
  A warning dialog is shown, and the application continues in degraded mode.

## File Count

- `qt_app/`: 78 Python files across `core/`, `screens/`, `viewmodels/`, `widgets/` + 3 QSS themes + 3 embedded web sub-apps
