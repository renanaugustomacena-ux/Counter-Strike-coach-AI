# Qt Desktop Application (Primary)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

*Maintained by the Macena CS2 Analyzer team. Requires familiarity with PySide6, MVVM, and Qt Signal/Slot.*

## Overview

PySide6/Qt desktop application implementing Model-View-ViewModel (MVVM) architecture with Qt Signal/Slot for CS2 tactical analysis and AI coaching. This is the **primary frontend** (46 Python files), replacing the legacy Kivy/KivyMD app at [`desktop_app/`](../desktop_app/). The application features 13 screens, 7 ViewModels, 6 chart widgets, 3 tactical widgets, toast notifications, 3 QSS themes (CS2, CSGO, CS1.6), background wallpaper rendering, internationalization (English/Italian/Portuguese), and a graceful shutdown sequence.

## Entry Point

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

The `main()` function in `app.py` performs the following boot sequence:

1. Enables High-DPI scaling (`PassThrough` rounding policy)
2. Creates `QApplication` and resolves the package version
3. Connects the graceful shutdown handler (`aboutToQuit` signal)
4. Instantiates `ThemeEngine`, registers custom fonts, applies the active theme
5. Creates `MainWindow` and sets the initial wallpaper
6. Instantiates and registers all 13 screens (real implementations, not placeholders)
7. Wires inter-screen signals (match selection: history -> detail, wizard completion -> home)
8. First-run gate: shows WizardScreen if `SETUP_COMPLETED` is False, otherwise HomeScreen
9. Boots the backend console (DB audit, conditional FlareSolverr/Hunter) with error dialog fallback
10. Starts AppState background polling (10-second interval)

## Directory Structure

```
qt_app/
├── app.py                          # Entry point: QApplication bootstrap and screen registration
├── main_window.py                  # QMainWindow with sidebar navigation + QStackedWidget + toast layer
├── __init__.py
├── core/
│   ├── app_state.py                # AppState singleton: polls CoachState DB every 10s, emits Signals
│   ├── theme_engine.py             # ThemeEngine: QSS loading, QPalette, fonts, wallpaper management
│   ├── worker.py                   # Worker QRunnable + WorkerSignals for background tasks
│   ├── asset_bridge.py             # QtAssetBridge: loads map images as QPixmap (singleton)
│   ├── i18n_bridge.py              # QtLocalizationManager: JSON-based i18n with Signal on language change
│   ├── qt_playback_engine.py       # QtPlaybackEngine: QTimer-based demo playback at ~60 FPS
│   └── __init__.py
├── screens/
│   ├── home_screen.py              # Dashboard and overview
│   ├── coach_screen.py             # AI coaching interface with chat panel
│   ├── match_history_screen.py     # Match listing with color-coded HLTV 2.0 ratings
│   ├── match_detail_screen.py      # Multi-section match analysis (overview, rounds, economy, momentum)
│   ├── performance_screen.py       # Performance analytics (trends, per-map stats, Z-score comparisons)
│   ├── tactical_viewer_screen.py   # 2D map replay with pixel-accurate rendering and timeline
│   ├── user_profile_screen.py      # User profile display and editing
│   ├── profile_screen.py           # Profile management
│   ├── settings_screen.py          # Application settings (theme, font, language, paths)
│   ├── wizard_screen.py            # First-time setup wizard for Steam/Faceit integration
│   ├── help_screen.py              # User documentation and guides
│   ├── steam_config_screen.py      # Steam integration configuration
│   ├── faceit_config_screen.py     # Faceit integration configuration
│   ├── placeholder.py              # Placeholder factory for screens not yet ported
│   └── __init__.py
├── viewmodels/
│   ├── match_history_vm.py         # Match list data, filtering, and sorting
│   ├── match_detail_vm.py          # Per-match analysis data (rounds, economy, highlights)
│   ├── performance_vm.py           # Performance trends, per-map stats, strengths/weaknesses
│   ├── tactical_vm.py              # Playback control, ghost AI predictions, chronovisor scanning
│   ├── coach_vm.py                 # Coaching insight loading from DB
│   ├── coaching_chat_vm.py         # Interactive coaching dialogue via Ollama/LLM
│   ├── user_profile_vm.py          # User profile data loading and saving
│   └── __init__.py
├── widgets/
│   ├── toast.py                    # ToastWidget + ToastContainer: ephemeral notifications (4 severities)
│   ├── charts/
│   │   ├── radar_chart.py          # RadarChartWidget: multi-dimensional performance radar
│   │   ├── momentum_chart.py       # MomentumGraphWidget: team momentum evolution per round
│   │   ├── economy_chart.py        # EconomyGraphWidget: round-by-round economy timeline
│   │   ├── rating_sparkline.py     # RatingSparklineWidget: compact rating history sparkline
│   │   ├── trend_chart.py          # TrendGraphWidget: time-series trend visualization
│   │   ├── utility_bar_chart.py    # UtilityBarWidget: utility usage comparison (user vs pro baseline)
│   │   └── __init__.py
│   ├── tactical/
│   │   ├── map_widget.py           # MapWidget: pixel-accurate 2D tactical map rendering
│   │   ├── player_sidebar.py       # PlayerSidebar: real-time player state display (health, armor, weapons)
│   │   ├── timeline_widget.py      # TimelineWidget: demo playback navigation and scrubbing
│   │   └── __init__.py
│   └── __init__.py
└── themes/
    ├── cs2.qss                     # CS2 theme: dark gaming aesthetic with orange accent (#D96600)
    ├── csgo.qss                    # CSGO theme: slate-blue tones with steel accent
    └── cs16.qss                    # CS 1.6 theme: retro green terminal aesthetic
```

## MVVM Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MainWindow                                  │
│  ┌──────────┐  ┌─────────────────────────────────────────────────┐  │
│  │ Sidebar   │  │ QStackedWidget (13 screens)                    │  │
│  │ (5 nav    │  │  ┌───────────────────────────────────────────┐ │  │
│  │  buttons) │  │  │  Screen (QWidget)                         │ │  │
│  │           │  │  │   │                                       │ │  │
│  │  Home     │  │  │   │ connects to                           │ │  │
│  │  Coach    │  │  │   ▼                                       │ │  │
│  │  History  │  │  │  ViewModel (QObject)                      │ │  │
│  │  Stats    │  │  │   │ Signal ──────> Screen updates UI      │ │  │
│  │  Tactical │  │  │   │                                       │ │  │
│  │           │  │  │   │ Worker (QRunnable)                    │ │  │
│  │           │  │  │   │ └──> background DB/compute            │ │  │
│  │           │  │  │   │      └──> Signal.result ──> ViewModel │ │  │
│  │           │  │  └───────────────────────────────────────────┘ │  │
│  └──────────┘  └─────────────────────────────────────────────────┘  │
│                ┌─────────────────────────────────────────────────┐  │
│                │ _BackgroundWidget (wallpaper, 25% opacity)      │  │
│                │ ToastContainer (top-right notification overlay) │  │
│                └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              AppState (singleton, polls CoachState DB every 10s)
              └──> service_active_changed, coach_status_changed,
                   parsing_progress_changed, belief_confidence_changed,
                   total_matches_changed, training_changed,
                   notification_received
```

**Data flow:** Screen <-> ViewModel (QObject + Signals) <-> Database (SQLModel) via Worker threads. All database access runs on `QThreadPool`; results are auto-marshaled back to the main thread via Signal connections.

## Screens (13)

| # | Screen | File | Description |
|---|--------|------|-------------|
| 1 | HomeScreen | `home_screen.py` | Dashboard with service status, match count, training progress, parsing progress |
| 2 | CoachScreen | `coach_screen.py` | AI coaching interface with insight cards and interactive chat panel (Ollama) |
| 3 | MatchHistoryScreen | `match_history_screen.py` | Match listing with color-coded HLTV 2.0 ratings, emits `match_selected` Signal |
| 4 | MatchDetailScreen | `match_detail_screen.py` | Multi-section match analysis: overview stats, round-by-round, economy chart, momentum |
| 5 | PerformanceScreen | `performance_screen.py` | Performance analytics: rating trends, per-map stats, strength/weakness, utility breakdown |
| 6 | TacticalViewerScreen | `tactical_viewer_screen.py` | 2D map replay with pixel-accurate rendering, ghost AI overlay, chronovisor scanning |
| 7 | UserProfileScreen | `user_profile_screen.py` | User profile display with bio and role editing |
| 8 | ProfileScreen | `profile_screen.py` | Profile management and configuration |
| 9 | SettingsScreen | `settings_screen.py` | Application settings: theme selection, font type/size, language, data paths |
| 10 | WizardScreen | `wizard_screen.py` | First-time setup wizard for Steam path, player name, Faceit config; emits `setup_completed` |
| 11 | HelpScreen | `help_screen.py` | User documentation, guides, and FAQ |
| 12 | SteamConfigScreen | `steam_config_screen.py` | Steam integration: path configuration, demo folder detection |
| 13 | FaceitConfigScreen | `faceit_config_screen.py` | Faceit integration: API key, player ID configuration |

## ViewModels (7)

| ViewModel | File | Key Signals | Description |
|-----------|------|-------------|-------------|
| `MatchHistoryViewModel` | `match_history_vm.py` | `matches_changed(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads match list from `PlayerMatchStats` with cancellation support |
| `MatchDetailViewModel` | `match_detail_vm.py` | `data_changed(dict, list, list, dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads match stats, round data, coaching insights, HLTV breakdown |
| `PerformanceViewModel` | `performance_vm.py` | `data_changed(list, dict, dict, dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads rating history, per-map stats, strength/weakness, utility data |
| `TacticalPlaybackVM` | `tactical_vm.py` | `frame_updated(object)`, `current_tick_changed(int)`, `is_playing_changed(bool)` | Playback control: play/pause, speed, seek, tick tracking via PlaybackEngine |
| `TacticalGhostVM` | `tactical_vm.py` | `ghost_active_changed(bool)`, `is_loaded_changed(bool)` | Ghost AI position predictions via lazy-loaded GhostEngine |
| `TacticalChronovisorVM` | `tactical_vm.py` | `scan_complete(list, int)`, `navigate_to(int, str)`, `is_scanning_changed(bool)` | Critical moment scanning and jump-to navigation via ChronovisorScanner |
| `CoachViewModel` | `coach_vm.py` | `insights_loaded(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads latest `CoachingInsight` rows for the active player |
| `CoachingChatViewModel` | `coaching_chat_vm.py` | `messages_changed(list)`, `session_active_changed(bool)`, `is_available_changed(bool)` | Interactive coaching chat via CoachingDialogueEngine (Ollama backend) |
| `UserProfileViewModel` | `user_profile_vm.py` | `profile_loaded(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads/saves `PlayerProfile` (bio, role) with background DB access |

*Note: The Tactical module contains 3 ViewModels in a single file (`tactical_vm.py`) for cohesion.*

## Widgets

### Chart Widgets (`widgets/charts/`)

| Widget | File | Description |
|--------|------|-------------|
| `RadarChartWidget` | `radar_chart.py` | Multi-dimensional performance radar with custom QPainter rendering |
| `MomentumGraphWidget` | `momentum_chart.py` | Team momentum evolution per round, dual-color CT/T overlay |
| `EconomyGraphWidget` | `economy_chart.py` | Round-by-round economy timeline showing buy levels |
| `RatingSparklineWidget` | `rating_sparkline.py` | Compact inline rating history sparkline with trend indicator |
| `TrendGraphWidget` | `trend_chart.py` | Time-series trend visualization for any metric over matches |
| `UtilityBarWidget` | `utility_bar_chart.py` | Horizontal bar comparison of utility usage (user vs pro baseline) |

### Tactical Widgets (`widgets/tactical/`)

| Widget | File | Description |
|--------|------|-------------|
| `MapWidget` | `map_widget.py` | Pixel-accurate 2D tactical map rendering with player dots, ghost overlays, and event markers |
| `PlayerSidebar` | `player_sidebar.py` | Real-time player state display: health, armor, weapon, money, alive/dead status |
| `TimelineWidget` | `timeline_widget.py` | Demo playback navigation with scrubbing, round markers, and critical moment indicators |

### Toast Notifications (`widgets/toast.py`)

| Severity | Icon | Auto-dismiss |
|----------|------|--------------|
| INFO | (i) | 5 seconds |
| WARNING | (!) | 8 seconds |
| ERROR | (X) | 12 seconds |
| CRITICAL | (skull) | Manual only |

Maximum 3 visible toasts at once. Oldest toast is removed when the limit is exceeded. The `ToastContainer` is rendered as a top-right overlay above all screen content via `QStackedLayout.StackAll`.

## AppState Singleton

`AppState` (`core/app_state.py`) is a `QObject` singleton obtained via `get_app_state()`. It polls the `CoachState` database row (id=1) every 10 seconds using a `QTimer` + `Worker` pattern, and emits typed signals only when values actually change (delta-based emission):

| Signal | Type | Trigger |
|--------|------|---------|
| `service_active_changed` | `bool` | Heartbeat delta > 300 seconds = inactive |
| `coach_status_changed` | `str` | Ingest status text changed |
| `parsing_progress_changed` | `float` | Demo parsing progress updated |
| `belief_confidence_changed` | `float` | Model belief confidence updated |
| `total_matches_changed` | `int` | Total processed matches changed |
| `training_changed` | `dict` | Any of: current_epoch, total_epochs, train_loss, val_loss, eta_seconds |
| `notification_received` | `(str, str)` | Unread `ServiceNotification` rows (severity + message) |

AppState is **read-only** from the Qt side. Only the backend session engine writes to `CoachState`.

## ThemeEngine

`ThemeEngine` (`core/theme_engine.py`) manages the visual identity of the application:

- **3 themes:** CS2 (dark + orange accent), CSGO (slate-blue + steel accent), CS 1.6 (retro green terminal)
- **QSS stylesheets** loaded from `themes/*.qss`, with dynamic font-family/size injection
- **QPalette** configuration for widgets that do not honor QSS
- **5 custom fonts:** Roboto, JetBrains Mono, New Hope, CS Regular, YUPIX
- **Wallpaper management:** per-theme wallpaper folders, vertical image preference, rendered at 25% opacity via `_BackgroundWidget`
- **HLTV rating colors:** green (> 1.10), yellow (0.90-1.10), red (< 0.90) with WCAG 1.4.1 text labels

## Worker Pattern

The `Worker` class (`core/worker.py`) is a `QRunnable` that wraps any callable for execution on `QThreadPool.globalInstance()`. It emits three signals via `WorkerSignals`:

```python
worker = Worker(some_function, arg1, arg2)
worker.signals.result.connect(on_success)   # auto-marshals to main thread
worker.signals.error.connect(on_error)       # receives str(exception)
worker.signals.finished.connect(on_done)     # always emitted
QThreadPool.globalInstance().start(worker)
```

All signal emissions are wrapped in `try/except RuntimeError` to handle the case where the receiver is garbage-collected before the worker completes. Workers are auto-deleted after execution (`setAutoDelete(True)`).

## Additional Core Modules

| Module | File | Description |
|--------|------|-------------|
| `QtAssetBridge` | `core/asset_bridge.py` | Singleton that loads map images as `QPixmap` with caching and magenta/black checkerboard fallback |
| `QtLocalizationManager` | `core/i18n_bridge.py` | Singleton (`i18n`) providing `get_text(key)` with JSON priority, hardcoded fallback, and `language_changed` Signal |
| `QtPlaybackEngine` | `core/qt_playback_engine.py` | Subclass of `PlaybackEngine` using `QTimer` at 16ms interval (~60 FPS) instead of Kivy Clock |

## Development Notes

- **Minimum window size:** 1280x720 pixels
- **Sidebar width:** 220px fixed, with 5 navigation buttons (Home, Coach, History, Stats, Tactical)
- **Screen lifecycle:** `on_enter()` is called automatically when a screen becomes visible; `retranslate()` is called on language change
- **Thread safety:** All DB access goes through Worker/QThreadPool. Never access SQLModel sessions on the main thread.
- **i18n:** 3 languages (en, pt, it) loaded from `assets/i18n/*.json`. The `language_changed` Signal triggers `retranslate()` on all registered screens.
- **Graceful shutdown:** `app.aboutToQuit` stops AppState polling and shuts down the backend console
- **First-run gate:** If `SETUP_COMPLETED` setting is False, the app starts on WizardScreen instead of HomeScreen
- **Backend boot failure:** If the backend console fails to boot, a `QMessageBox` warning is shown but the app continues running in degraded mode
