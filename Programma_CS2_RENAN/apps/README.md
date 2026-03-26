> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Apps — User Interface Layer

> **Authority:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Overview

The `apps/` directory contains all user-facing interface code for the Macena CS2 Analyzer.
Two UI frameworks coexist as part of a deliberate migration strategy:

- **Phase 0 (Legacy):** `desktop_app/` was the original prototype built with Kivy + KivyMD.
  It served as the rapid-prototyping shell during early development. No new features are
  added here; it exists only as a reference and for components not yet ported.

- **Phase 2+ (Active):** `qt_app/` is the production desktop UI built with PySide6 (Qt6).
  All new screens, widgets, and features target this framework exclusively. Qt was chosen
  for its native look-and-feel, mature threading model (QThreadPool/QRunnable), built-in
  chart library (QtCharts), and broad cross-platform support.

Both frameworks share the same backend services (`backend/services/`), database layer
(`backend/storage/`), and configuration system (`core/config.py`). The UI layer is strictly
a consumer of backend data — it never writes to the database directly.

## Directory Structure

```
apps/
├── __init__.py
├── README.md                    # This file
├── README_IT.md                 # Italian translation
├── README_PT.md                 # Portuguese translation
├── spatial_debugger.py          # Standalone Kivy tool for map coordinate validation
│
├── desktop_app/                 # Legacy Kivy + KivyMD (Phase 0)
│   ├── __init__.py
│   ├── layout.kv                # Root KV layout (60 KB, 13 screens)
│   ├── theme.py                 # Kivy palette constants and rating colors
│   ├── ghost_pixel.py           # Crosshair overlay widget
│   ├── player_sidebar.py        # Player info sidebar (Kivy)
│   ├── timeline.py              # Round timeline scrubber (Kivy)
│   ├── widgets.py               # Shared Kivy widgets (cards, buttons)
│   ├── wizard_screen.py         # First-run setup wizard
│   ├── help_screen.py           # Help / about screen
│   ├── match_history_screen.py  # Match list browser
│   ├── match_detail_screen.py   # Single match breakdown
│   ├── performance_screen.py    # Player stats dashboard
│   ├── tactical_map.py          # 2D tactical map renderer
│   ├── tactical_viewer_screen.py # Tactical analysis screen
│   ├── coaching_chat_vm.py      # Coaching chat ViewModel
│   ├── tactical_viewmodels.py   # Tactical analysis ViewModels
│   └── data_viewmodels.py       # Data-fetching ViewModels
│
└── qt_app/                      # Active PySide6 / Qt6 (Phase 2+)
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
    │   ├── animation.py         # Shared animation utilities and easing helpers
    │   ├── icons.py             # Icon registry and SVG/icon asset loader
    │   ├── i18n_bridge.py       # Localization (en, pt, it) via JSON + fallback
    │   ├── asset_bridge.py      # Map image loader (QPixmap), fallback textures
    │   └── qt_playback_engine.py # QTimer-based demo playback (replaces Kivy Clock)
    │
    ├── screens/                 # One QWidget per screen (View layer)
    │   ├── home_screen.py       # Dashboard — service status, match count, training
    │   ├── coach_screen.py      # AI Coach — chat interface, coaching insights
    │   ├── match_history_screen.py  # Match list with search and filters
    │   ├── match_detail_screen.py   # Single match analysis (rounds, economy, events)
    │   ├── performance_screen.py    # Player statistics and trends
    │   ├── tactical_viewer_screen.py # 2D map viewer with playback controls
    │   ├── wizard_screen.py     # First-run setup (Steam path, player name)
    │   ├── settings_screen.py   # App settings (theme, font, language, paths)
    │   ├── user_profile_screen.py   # User profile editor
    │   ├── profile_screen.py    # Player profile overview
    │   ├── steam_config_screen.py   # Steam integration settings
    │   ├── faceit_config_screen.py  # FACEIT integration settings
    │   ├── help_screen.py       # Help documentation viewer
    │   └── placeholder.py       # Placeholder factory for unported screens
    │
    ├── viewmodels/              # ViewModel layer (QObject subclasses)
    │   ├── coach_vm.py          # CoachViewModel — orchestrates coaching queries
    │   ├── coaching_chat_vm.py  # Chat history and message handling
    │   ├── match_history_vm.py  # Match list data fetching and filtering
    │   ├── match_detail_vm.py   # Single match data loading
    │   ├── performance_vm.py    # Player stats aggregation
    │   ├── tactical_vm.py       # Tactical data and playback state
    │   └── user_profile_vm.py   # User profile CRUD operations
    │
    ├── widgets/                 # Reusable widget library
    │   ├── toast.py             # Toast notification overlay
    │   ├── skeleton.py          # Skeleton loading placeholder widgets
    │   ├── charts/              # QtCharts-based visualizations
    │   │   ├── radar_chart.py       # Skill radar (6-axis spider chart)
    │   │   ├── economy_chart.py     # Round-by-round economy graph
    │   │   ├── momentum_chart.py    # Team momentum timeline
    │   │   ├── rating_sparkline.py  # Inline rating mini-chart
    │   │   ├── trend_chart.py       # Multi-match trend lines
    │   │   └── utility_bar_chart.py # Utility usage bar chart
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
    └── themes/                  # QSS stylesheets
        ├── cs2.qss              # CS2 theme (orange accent, dark surface)
        ├── csgo.qss             # CS:GO theme (steel blue accent)
        └── cs16.qss             # CS 1.6 theme (green accent, retro)
```

## Framework Comparison

| Aspect | `desktop_app/` (Kivy) | `qt_app/` (PySide6) |
|--------|----------------------|----------------------|
| **Status** | Legacy (Phase 0) — frozen | **Active** (Phase 2+) |
| **Layout** | KV language (`layout.kv`) | Python code (QLayouts) |
| **Threading** | `threading.Thread` + `Clock.schedule_once` | `Worker` (QRunnable) + Signals |
| **Charts** | matplotlib (heavyweight) | QtCharts (native, lightweight) |
| **Theming** | `theme.py` (Kivy properties) | `ThemeEngine` + QSS stylesheets |
| **i18n** | `LocalizationManager` (Kivy EventDispatcher) | `QtLocalizationManager` (QObject + Signal) |
| **Assets** | `AssetAuthority` (Kivy Texture) | `QtAssetBridge` (QPixmap) |
| **Playback** | `PlaybackEngine` + Kivy Clock | `QtPlaybackEngine` + QTimer |
| **Screens** | 13 (in `layout.kv`) | 14 (individual `.py` files) |
| **Python files** | 16 | 56 |

## MVVM Architecture

Both UIs follow the **Model-View-ViewModel** pattern. The Qt implementation is the
canonical reference:

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
6. All 14 screens instantiated and registered in the `QStackedWidget`
7. First-run gate: shows `WizardScreen` if setup not completed, else `HomeScreen`
8. Backend console booted (`get_console().boot()`)
9. `AppState` polling started (10-second interval)

### PyInstaller Bundle

The application can also be launched from a PyInstaller-built executable. See the
`packaging/` directory for the `.spec` file and build instructions.

### Standalone Tools

- **`spatial_debugger.py`** — Kivy-based debug widget for validating map coordinate
  transformations. Displays a map image with landmark overlays and a cursor-to-world
  coordinate readout. Useful during spatial data calibration.

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

This replaces the Kivy pattern of `Thread(target=fn).start()` followed by
`Clock.schedule_once(callback)`.

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

1. **All new UI work goes in `qt_app/`** — do not add features to `desktop_app/`
2. **No Kivy imports in Qt code** — `asset_bridge.py`, `i18n_bridge.py`, `theme_engine.py`
   use only Qt and stdlib. Cross-framework imports are forbidden.
3. **Background threading is mandatory** — never block the main thread with DB queries,
   network calls, or file I/O. Use `Worker` from `core/worker.py`.
4. **Connect to `AppState` signals in `on_enter()`** — this is the live data bus
   from the backend. Do not poll the database from screens.
5. **Charts use QtCharts** (not matplotlib) — lighter weight, native Qt integration,
   consistent theming via QSS.
6. **Localization** — all user-visible strings must go through `i18n_bridge.get_text(key)`.
   Never hardcode display text in screen code.
7. **Themes** — use `ThemeEngine.get_color(slot)` for colors and never hardcode hex values.
   All visual constants live in `theme_engine.py` or QSS files.
8. **Screens don't import each other** — navigation is handled by `MainWindow.switch_screen()`.
   Inter-screen communication goes through signals or `AppState`.
9. **Every screen must implement `on_enter()`** — called by `MainWindow` when the screen
   becomes visible. Use it to refresh data and connect signals.
10. **Implement `retranslate()`** — called when the user switches language. Update all
    user-visible labels from `i18n_bridge`.

## Development Notes

- The Qt app requires **PySide6 >= 6.5** and **Python 3.10+**.
- QSS stylesheets are in `qt_app/themes/` — one file per theme. Edit these for
  visual changes; do not inline styles in Python code.
- The `placeholder.py` factory generates stub screens for pages not yet ported
  from Kivy. These display a "Coming Soon" message and are progressively replaced.
- `MainWindow` uses a `QStackedLayout` with three layers: background wallpaper
  (bottom), screen stack (middle), and toast notifications (top).
- The backend console (`get_console().boot()`) may fail without breaking the UI.
  A warning dialog is shown, and the application continues in degraded mode.
- `spatial_debugger.py` is the only file in `apps/` that imports Kivy directly.
  It is a standalone debug tool and is not loaded by the Qt application.

## File Count

- `desktop_app/`: 16 Python files + 1 KV layout (legacy, frozen)
- `qt_app/`: 56 Python files across `core/`, `screens/`, `viewmodels/`, `widgets/` + 3 QSS themes
- `apps/` root: 1 standalone tool (`spatial_debugger.py`)
