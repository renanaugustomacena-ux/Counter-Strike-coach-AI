# Qt Desktop Application (Primary)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

*Maintained by the Macena CS2 Analyzer team. Requires familiarity with PySide6, MVVM, and Qt Signal/Slot.*

## Overview

PySide6/Qt desktop application implementing Model-View-ViewModel (MVVM) architecture with Qt Signal/Slot for CS2 tactical analysis and AI coaching. This is the **primary frontend** (92 Python files). The application features 15 screens, 10 ViewModels, 6 QPainter chart widgets (QtCharts was removed for license compliance), 3 tactical widgets, a design-system component library (26 modules) plus an embedded coaching ChatPanel, toast notifications, 3 token-driven themes (CS2, CSGO, CS1.6), optional background wallpaper (default: flat), an optional frameless window mode with a custom title bar, internationalization (English/Italian/Portuguese, 572 keys per language), and a graceful shutdown sequence.

## Entry Point

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

The `main()` function in `app.py` performs the following boot sequence:

1. Enables High-DPI scaling (`PassThrough` rounding policy)
2. Creates `QApplication` and resolves the package version
3. Instantiates `ThemeEngine`, registers custom fonts, shows a themed splash screen (gradient + branding rendered from the saved theme's design tokens)
4. Connects the graceful shutdown handler (`aboutToQuit` signal)
5. Applies the active theme with the persisted font family/size settings
6. Creates `MainWindow` and sets the initial wallpaper
7. Instantiates and registers all 15 screens (real implementations override the placeholder registry)
8. Wires inter-screen signals (match selection: history/home -> detail, wizard completion -> home, highlight moments -> tactical viewer, pro comparison -> pro detail)
9. First-run gate: shows WizardScreen if `SETUP_COMPLETED` is False, otherwise HomeScreen
10. Boots the backend console (conditional FlareSolverr/Hunter, database schema initialization) and launches the Session Engine daemon, with error dialog fallback
11. Ensures the SBERT language model is present (~90 MB download on first run, splash progress)
12. Starts AppState background polling (10-second interval) and installs a Qt-aware excepthook

## Directory Structure

```
qt_app/
├── app.py                          # Entry point: QApplication bootstrap and screen registration
├── main_window.py                  # QMainWindow with sidebar navigation + QStackedWidget + toast layer
├── __init__.py
├── core/
│   ├── app_state.py                # AppState singleton: polls CoachState DB every 10s, emits Signals
│   ├── theme_engine.py             # ThemeEngine: token QSS render, QPalette, fonts, wallpaper management
│   ├── design_tokens.py            # Design token definitions for the Qt component system
│   ├── qss_generator.py            # Renders themes/base.qss.template with token substitution
│   ├── animation.py                # Shared animation utilities
│   ├── easing.py                   # Custom easing curves
│   ├── typography.py               # Typography scale and font helpers
│   ├── icons.py                    # IconProvider facade: SVG sprite with QPainterPath fallback
│   ├── svg_icon_provider.py        # SvgIconProvider: sprite-backed QIcon factory
│   ├── sound.py                    # Sound effect playback helpers
│   ├── match_utils.py              # Match-level utility functions for the UI layer
│   ├── widgets_helpers.py          # Generic Qt widget helper functions
│   ├── web_bridge.py               # Python↔JavaScript bridge for embedded web views
│   ├── worker.py                   # Worker QRunnable + WorkerSignals for background tasks
│   ├── i18n_bridge.py              # QtLocalizationManager: JSON-based i18n with Signal on language change
│   ├── qt_playback_engine.py       # QtPlaybackEngine: QTimer-based demo playback at ~60 FPS
│   └── __init__.py
├── screens/
│   ├── home_screen.py              # Dashboard and overview
│   ├── coach_screen.py             # AI coaching screen with embedded ChatPanel (dock removed)
│   ├── match_history_screen.py     # Match listing with color-coded HLTV 2.0 ratings
│   ├── match_detail_screen.py      # 4-tab match analysis (Overview · Rounds · Economy · Highlights)
│   ├── performance_screen.py       # Performance analytics (trends, per-map stats, Z-score comparisons)
│   ├── tactical_viewer_screen.py   # 2D map replay with pixel-accurate rendering and timeline
│   ├── user_profile_screen.py      # User profile display and editing
│   ├── profile_screen.py           # Profile management
│   ├── settings_screen.py          # Application settings (theme, font, language, paths)
│   ├── wizard_screen.py            # First-time setup wizard for Steam/Faceit integration
│   ├── help_screen.py              # User documentation and guides
│   ├── steam_config_screen.py      # Steam integration configuration
│   ├── faceit_config_screen.py     # Faceit integration configuration
│   ├── pro_comparison_screen.py    # Side-by-side user vs pro player analysis
│   ├── pro_player_detail_screen.py # Pro player profile view
│   ├── placeholder.py              # Placeholder factory (all entries overridden by real screens)
│   └── __init__.py
├── viewmodels/
│   ├── match_history_vm.py         # Match list data, filtering, and sorting
│   ├── match_detail_vm.py          # Per-match analysis data (rounds, economy, highlights)
│   ├── performance_vm.py           # Performance trends, per-map stats, strengths/weaknesses
│   ├── tactical_vm.py              # Playback control, ghost AI predictions, chronovisor scanning
│   ├── coach_vm.py                 # Coaching insight loading from DB
│   ├── coaching_chat_vm.py         # Interactive coaching dialogue via Ollama/LLM
│   ├── focus_insight_vm.py         # Focused coaching insight detail ViewModel
│   ├── pro_comparison_vm.py        # Pro comparison data and scoring
│   ├── pro_player_detail_vm.py     # Pro player profile data loading
│   ├── user_profile_vm.py          # User profile data loading and saving
│   └── __init__.py
├── widgets/
│   ├── toast.py                    # ToastWidget + ToastContainer: ephemeral notifications (4 severities)
│   ├── skeleton.py                 # Skeleton loading placeholder widgets
│   ├── charts/                     # All QPainter — QtCharts removed (GPL-only)
│   │   ├── economy_chart.py        # EconomyChart: round-by-round economy bars (QPainter)
│   │   ├── mini_sparkline.py       # MiniSparkline: compact QPainter sparkline, no axes
│   │   ├── momentum_chart.py       # MomentumChart: team momentum area chart (QPainter)
│   │   ├── radar_chart.py          # RadarChart: N-axis skill radar (user vs pro overlay)
│   │   ├── rating_sparkline.py     # RatingSparkline: rating trend with baseline
│   │   ├── utility_bar_chart.py    # UtilityBarChart: utility usage horizontal bars
│   │   └── __init__.py
│   ├── coaching/
│   │   ├── chat_panel.py           # ChatPanel: embedded coach chat (bubbles, meta line, input row)
│   │   └── __init__.py
│   ├── components/                 # Reusable UI components (design system) — 26 modules
│   │   ├── __init__.py             # Component exports
│   │   ├── card.py                 # Card container widget (5 depth variants)
│   │   ├── db_record_card.py       # DbRecordCard: mono DB row echo (table · column · value)
│   │   ├── delta_chip.py           # DeltaChip: ▲/▼ benchmark-relative delta pill
│   │   ├── drivers_list.py         # DriversList: signed contribution rows (what moved a stat)
│   │   ├── empty_state.py          # Empty state placeholder with icon and message
│   │   ├── filter_chip.py          # Toggleable filter pill
│   │   ├── focus_insight.py        # FocusInsightCard: home-page focus insight card
│   │   ├── hero_stats_strip.py     # Horizontal strip of hero metrics
│   │   ├── icon_widget.py          # Icon display widget (SVG/pixmap)
│   │   ├── last_match_hero.py      # LastMatchHeroCard: home-page last-match hero card
│   │   ├── map_tile.py             # MapTile: per-map stat tile with win-rate accent
│   │   ├── match_mini_card.py      # Compact match summary card
│   │   ├── match_row_card.py       # Expanded match row card with stat preview
│   │   ├── metric_bar_row.py       # MetricBarRow: label + horizontal metric bar + value
│   │   ├── mini_link_card.py       # MiniLinkCard: small related-link navigation card
│   │   ├── mono_footer.py          # MonoFooter: mono provenance/status footer line
│   │   ├── nav_sidebar.py          # Collapsible navigation sidebar component
│   │   ├── numbered_step.py        # NumberedStep: 01/02/03 accent-mono step row
│   │   ├── pro_badge.py            # ProBadge: PRO/tier pill for pro-player surfaces
│   │   ├── progress_ring.py        # Circular progress ring indicator
│   │   ├── section_header.py       # Section header with title and optional action
│   │   ├── stat_badge.py           # Stat badge with label and value
│   │   ├── status_chip.py          # Colored status pill with text label
│   │   ├── stepper.py              # Labeled step progress indicator (used by the wizard)
│   │   ├── tip_box.py              # TipBox: accent-bordered tip/callout box
│   │   └── toggle_switch.py        # Animated boolean switch
│   ├── tactical/
│   │   ├── _paint_utils.py         # Shared QPainter helpers for the tactical widgets
│   │   ├── map_widget.py           # TacticalMapWidget: 2D map rendering + zone overlays (assets/map_zones/) + movement trails
│   │   ├── player_sidebar.py       # PlayerSidebar: real-time player state display (health, armor, weapons)
│   │   ├── timeline_widget.py      # TimelineWidget: scrubbing, round dividers, ★/◆/● moment glyphs
│   │   └── __init__.py
│   └── __init__.py
├── web/                            # TypeScript web sub-apps (embedded via QWebEngineView)
│   ├── coach-chat/
│   ├── match-detail/
│   ├── tactical-viewer/
│   └── shared/
└── themes/
    └── base.qss.template           # Token-substituted stylesheet — sole QSS source
                                    # (rendered per theme by core/qss_generator.py)
```

## MVVM Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MainWindow                                  │
│  ┌──────────┐  ┌─────────────────────────────────────────────────┐  │
│  │ Sidebar   │  │ QStackedWidget (15 screens)                    │  │
│  │ (7 nav    │  │  ┌───────────────────────────────────────────┐ │  │
│  │  buttons) │  │  │  Screen (QWidget)                         │ │  │
│  │           │  │  │   │                                       │ │  │
│  │  Home     │  │  │   │ connects to                           │ │  │
│  │  Coach    │  │  │   ▼                                       │ │  │
│  │  History  │  │  │  ViewModel (QObject)                      │ │  │
│  │  Stats    │  │  │   │ Signal ──────> Screen updates UI      │ │  │
│  │  Tactical │  │  │   │                                       │ │  │
│  │  Settings │  │  │   │ Worker (QRunnable)                    │ │  │
│  │  Help     │  │  │   │ └──> background DB/compute            │ │  │
│  │           │  │  │   │      └──> Signal.result ──> ViewModel │ │  │
│  │           │  │  └───────────────────────────────────────────┘ │  │
│  └──────────┘  └─────────────────────────────────────────────────┘  │
│                ┌─────────────────────────────────────────────────┐  │
│                │ _BackgroundWidget (wallpaper, 15% opacity)      │  │
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

## Screens (15)

| # | Screen | File | Description |
|---|--------|------|-------------|
| 1 | HomeScreen | `home_screen.py` | Dashboard with service status, match count, training progress, parsing progress |
| 2 | CoachScreen | `coach_screen.py` | AI coaching **stacked screen** with belief ring, top-3 ranked insights, and an embedded ChatPanel (Ollama) — the old QDockWidget chat dock was removed |
| 3 | MatchHistoryScreen | `match_history_screen.py` | Match listing with color-coded HLTV 2.0 ratings, emits `match_selected` Signal |
| 4 | MatchDetailScreen | `match_detail_screen.py` | 4-tab match analysis: Overview · Rounds · Economy · Highlights (underline tabs, frame 09) |
| 5 | PerformanceScreen | `performance_screen.py` | Performance analytics: rating trends, per-map stats, strength/weakness, utility breakdown |
| 6 | TacticalViewerScreen | `tactical_viewer_screen.py` | 2D map replay with zone overlays, movement trails, glyph timeline (★ critical · ◆ clutch · ● play), chronovisor scanning, and Ghost Mode (dual progress + divergence panel) |
| 7 | UserProfileScreen | `user_profile_screen.py` | User profile display with bio and role editing |
| 8 | ProfileScreen | `profile_screen.py` | In-game name editor (frame 17): case-sensitivity caption, DbRecordCard echo, related-link cards, stored-locally note |
| 9 | SettingsScreen | `settings_screen.py` | Application settings: clickable theme preview cards, font type/size, live preview, language, data paths |
| 10 | WizardScreen | `wizard_screen.py` | First-time setup wizard with labeled stepper (Intro · Name · Brain Path · Demo Path · Launch) and "What happens next" calibration copy; emits `setup_completed` |
| 11 | HelpScreen | `help_screen.py` | Structured help article: numbered getting-started steps, topic cards, keyboard hints, docs provenance |
| 12 | SteamConfigScreen | `steam_config_screen.py` | Steam integration: path configuration, demo folder detection |
| 13 | FaceitConfigScreen | `faceit_config_screen.py` | Faceit integration: API key, player ID configuration |
| 14 | ProComparisonScreen | `pro_comparison_screen.py` | Side-by-side statistical comparison of user vs selected pro player |
| 15 | ProPlayerDetailScreen | `pro_player_detail_screen.py` | Full pro player profile: career stats, heatmaps, signature plays |

## ViewModels (10)

| ViewModel | File | Key Signals | Description |
|-----------|------|-------------|-------------|
| `MatchHistoryViewModel` | `match_history_vm.py` | `matches_changed(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads match list from `PlayerMatchStats` with cancellation support |
| `MatchDetailViewModel` | `match_detail_vm.py` | `data_changed(dict, list, list, dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads match stats, round data, coaching insights, HLTV breakdown |
| `PerformanceViewModel` | `performance_vm.py` | `data_changed(list, dict, dict, dict, bool)`, `context_changed(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads rating history, per-map stats, strength/weakness, utility data, plus pro-cohort percentile context |
| `TacticalPlaybackVM` | `tactical_vm.py` | `frame_updated(object)`, `current_tick_changed(int)`, `is_playing_changed(bool)` | Playback control: play/pause, speed, seek, tick tracking via PlaybackEngine |
| `TacticalGhostVM` | `tactical_vm.py` | `ghost_active_changed(bool)`, `is_loaded_changed(bool)` | Ghost AI position predictions via lazy-loaded GhostEngine |
| `TacticalChronovisorVM` | `tactical_vm.py` | `scan_complete(list, int)`, `navigate_to(int, str)`, `is_scanning_changed(bool)` | Critical moment scanning and jump-to navigation via ChronovisorScanner |
| `CoachViewModel` | `coach_vm.py` | `insights_loaded(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads latest `CoachingInsight` rows for the active player |
| `CoachingChatViewModel` | `coaching_chat_vm.py` | `messages_changed(list)`, `session_active_changed(bool)`, `is_available_changed(bool)`, `streaming_changed(str)` | Interactive coaching chat via CoachingDialogueEngine (Ollama backend) |
| `FocusInsightViewModel` | `focus_insight_vm.py` | `insight_changed(dict)`, `has_data_changed(bool)` | Loads and manages the detail view for a single focused coaching insight |
| `ProComparisonViewModel` | `pro_comparison_vm.py` | `players_loaded(list)`, `comparison_ready(dict, dict, str, str)`, `error_changed(str)` | Fetches and scores user-vs-pro statistical comparison |
| `ProPlayerDetailViewModel` | `pro_player_detail_vm.py` | `profile_loaded(dict)`, `error_changed(str)` | Loads pro player profile and career statistics |
| `UserProfileViewModel` | `user_profile_vm.py` | `profile_loaded(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Loads/saves `PlayerProfile` (bio, role) with background DB access |

*Note: The Tactical module contains 3 ViewModels in a single file (`tactical_vm.py`) for cohesion.*

## Widgets

### Chart Widgets (`widgets/charts/`) — all QPainter

> **QtCharts was removed** from the app: Qt Charts is GPLv3-or-commercial only (unlike LGPL base Qt), incompatible with this proprietary repo. Every chart is now a custom `QWidget.paintEvent` implementation; a license-gate test (`test_charts.py::TestQtChartsRetired`) fails the suite if any `QtCharts`/`QChart` reference reappears under `apps/qt_app/`.

| Widget | File | Description |
|--------|------|-------------|
| `EconomyChart` | `economy_chart.py` | Round-by-round economy bars with side coloring, half divider, and $K ladder |
| `MiniSparkline` | `mini_sparkline.py` | Compact sparkline with no axes, used in the last-match hero card |
| `MomentumChart` | `momentum_chart.py` | Team momentum evolution per round, dual-color CT/T area overlay |
| `RadarChart` | `radar_chart.py` | N-axis skill radar (N >= 3) with user-vs-pro polygon overlay (8 axes in pro comparison) |
| `RatingSparkline` | `rating_sparkline.py` | Rating trend line with 1.0 baseline (match detail / performance) |
| `UtilityBarChart` | `utility_bar_chart.py` | Horizontal utility-usage bars (flash/smoke/HE/molly) |

### Coaching Widgets (`widgets/coaching/`)

| Widget | File | Description |
|--------|------|-------------|
| `ChatPanel` | `chat_panel.py` | Embedded coach chat: message bubbles, mono provenance meta line, availability states, input row — hosted by CoachScreen (replaces the removed chat dock) |

### Component Primitives added in the design-atlas rebuild (`widgets/components/`)

| Widget | File | Description |
|--------|------|-------------|
| `ProBadge` | `pro_badge.py` | PRO/tier pill for pro-player surfaces |
| `DeltaChip` | `delta_chip.py` | ▲/▼ benchmark-relative delta pill (vs 30-day avg / pro baseline) |
| `DriversList` | `drivers_list.py` | Signed contribution rows explaining what moved a headline stat |
| `TipBox` | `tip_box.py` | Accent-bordered tip/callout box (wizard, help) |
| `NumberedStep` | `numbered_step.py` | 01/02/03 accent-mono step row (wizard launch page, help) |
| `DbRecordCard` | `db_record_card.py` | Mono DB row echo (`table · column · value`, frame 17) |
| `MonoFooter` | `mono_footer.py` | Mono provenance/status footer line (screen-bottom captions) |
| `MiniLinkCard` | `mini_link_card.py` | Small related-link navigation card |
| `MapTile` | `map_tile.py` | Per-map stat tile with win-rate accent |
| `MetricBarRow` | `metric_bar_row.py` | Label + horizontal metric bar + value row |

### Tactical Widgets (`widgets/tactical/`)

| Widget | File | Description |
|--------|------|-------------|
| `TacticalMapWidget` | `map_widget.py` | 2D tactical map rendering with player dots, named zone overlays (`assets/map_zones/*.json`), movement trails, ghost overlays, and event markers |
| `PlayerSidebar` | `player_sidebar.py` | Real-time player state display: health, armor, weapon, money, alive/dead status |
| `TimelineWidget` | `timeline_widget.py` | Demo playback scrubbing with round dividers, event markers, and kind-differentiated critical-moment glyphs (★ critical / ◆ clutch / ● play, star fallback) |

### Toast Notifications (`widgets/toast.py`)

| Severity | Icon | Auto-dismiss |
|----------|------|--------------|
| INFO | (i) | 5 seconds |
| WARNING | (!) | 8 seconds |
| ERROR | (X) | 12 seconds |
| CRITICAL | (skull) | Manual only |

Maximum 3 visible toasts at once. Oldest toast is removed when the limit is exceeded. The `ToastContainer` is a floating top-right child of the content area (not part of the `QStackedLayout`), repositioned via an event filter and hidden when empty so it never blocks events.

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

AppState is **read-only toward `CoachState`** — only the backend session engine writes it. One sanctioned write exists: delivered `ServiceNotification` rows are marked `is_read=True` so notifications are shown once. AppState also persists four UI toggles (`sounds_enabled`, `use_frameless_window`, `use_pyqtgraph_heatmap`, `use_webengine_marquee`), each with its own `*_changed` Signal.

## ThemeEngine

`ThemeEngine` (`core/theme_engine.py`) manages the visual identity of the application:

- **3 themes:** CS2 (deep navy + tactical orange), CSGO (slate-blue + steel accent), CS 1.6 (retro green terminal)
- **Design tokens are the single source of truth:** per-theme token sets (`core/design_tokens.py`) feed **both** the QSS render (`themes/base.qss.template` via `core/qss_generator.py`, with dynamic font-family/size injection) and the `QPalette` configuration for widgets that do not honor QSS — no hand-maintained color values outside the token tables
- **Fonts:** legacy `PHOTO_GUI/` faces (Roboto, JetBrains Mono, New Hope, CS Regular, YUPIX) plus the bundled OFL display stack auto-scanned from `assets/fonts/` (Space Grotesk, Inter, JetBrains Mono weights — see `assets/fonts/README.txt` for sources/licenses)
- **Wallpaper:** default is **no wallpaper** — a flat `surface_base` background per the design atlas. A persisted user choice can select a per-theme wallpaper file, rendered at 15% opacity via `_BackgroundWidget`, which also tiles a barely-perceptible tactical-grid motif (5% opacity) behind all content
- **HLTV rating colors:** green (> 1.10), yellow (0.90-1.10), red (< 0.90) with WCAG 1.4.1 text labels
- **Live restyle:** theme switches emit `theme_changed` on the engine **and** on a module-level relay (`get_theme_relay()`), so chip-style widgets restyle without a restart

## Worker Pattern

The `Worker` class (`core/worker.py`) is a `QRunnable` that wraps any callable for execution on `QThreadPool.globalInstance()`. It emits three always-available signals via `WorkerSignals` (plus an opt-in `progress` signal — constructing with `wants_progress=True` injects a `progress_callback` into the wrapped callable for streaming partial results):

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
| `QtLocalizationManager` | `core/i18n_bridge.py` | Singleton (`i18n`) providing `get_text(key)` with JSON priority, hardcoded fallback, and `language_changed` Signal |
| `QtPlaybackEngine` | `core/qt_playback_engine.py` | Subclass of `PlaybackEngine` using `QTimer` at 16ms interval (~60 FPS) |
| `DesignTokens` | `core/design_tokens.py` | Per-theme design tokens (colors, spacing, radius, typography) — GENERATED from `design/tokens/design-tokens.json` |
| `render_qss` | `core/qss_generator.py` | Renders `themes/base.qss.template` with token substitution, cached per theme |
| `Animator` | `core/animation.py` | Shared animation helpers (fade, slide, pulse, stagger, count-up, ring-sweep) with a `MACENA_UI_ANIMATIONS=0` kill-switch |
| `IconProvider` | `core/icons.py` | Icon facade: SVG-sprite primary path with a `QPainterPath` fallback (`USE_SVG_ICONS` flag) |
| `Easing` | `core/easing.py` | Named `QEasingCurve` aliases (Remotion port) plus `cubic_bezier()` |
| `Typography` | `core/typography.py` | Typography role scale and font helpers (sizes read from `get_tokens()`) |
| `SvgIconProvider` | `core/svg_icon_provider.py` | Sprite-backed QIcon factory (`design/assets/icons/sprite.svg`), swapped in via `USE_SVG_ICONS` in `core/icons.py` |
| `SoundManager` | `core/sound.py` | Four preloaded `QSoundEffect` WAVs (click, success, error, notification), gated by `AppState.sounds_enabled` |
| `match_utils` | `core/match_utils.py` | Match helpers: `extract_map_name`, `map_short_name`, `count_personal_and_pro` |
| `widgets_helpers` | `core/widgets_helpers.py` | Widget factories built on the QSS template: `make_button`, `navigate_to` |
| `MarqueeBridge` | `core/web_bridge.py` | `QWebChannel` Python↔JavaScript bridge for the embedded web views |

## Testing

The UI suite (under `Programma_CS2_RENAN/tests/`) runs fully offscreen (`QT_QPA_PLATFORM=offscreen`) with animations disabled (`MACENA_UI_ANIMATIONS=0`):

| File | Covers |
|------|--------|
| `tests/test_qt_core.py` | Core modules (tokens, QSS generation, i18n bridge, workers) — includes a **subprocess-isolated** live-animation test so the animations-enabled path is exercised without polluting the offscreen run |
| `tests/test_ui_smoke.py` | **Runtime walk**: boots the real MainWindow, visits every screen, switches all 3 themes live, round-trips languages (retranslate), collapses/expands the sidebar |
| `tests/test_ui_harness.py` | **i18n key parity** across en/it/pt (`test_i18n_key_parity_across_languages`) + runs the screenshot harness end-to-end as a subprocess |
| `tests/test_charts.py` | QPainter chart widgets + the QtCharts license gate (`TestQtChartsRetired`) |
| `tests/test_tactical_frame_widgets.py` | Map-zone loader, timeline glyph-kind mapping + star hit-test, ghost divergence-row adapter |
| `tests/test_detonation_overlays.py` | Grenade/bomb detonation overlay painting |

Screenshot tooling: `tools/ui_screenshot.py` (offscreen harness — real screens + fixture data from `tools/ui_fixtures.py`, per-theme PNGs) and `tools/ui_gallery.py` (component gallery sheet).

## Development Notes

- **Window size:** opens at 1440x900 (the design-atlas canvas); minimum 1280x720 pixels
- **Sidebar:** collapsible 220px ↔ 60px, with 7 navigation buttons (Home, Coach, Match History, Performance, Tactical Viewer, Settings, Help), each with a keyboard shortcut (Ctrl+1..Ctrl+5, Ctrl+,, F1) driven by the shared `NAV_ITEMS` table
- **Frameless mode:** an AppState toggle (`use_frameless_window`) strips the native frame and adds a custom draggable title bar; read once at construction, so flipping it requires a restart
- **Screen lifecycle:** `MainWindow.switch_screen()` calls `on_leave()` on the outgoing screen and `on_enter()` on the incoming one; `retranslate()` is called on language change
- **Thread safety:** All DB access goes through Worker/QThreadPool. Never access SQLModel sessions on the main thread.
- **i18n:** 3 languages (en, pt, it) loaded from `assets/i18n/*.json`. The `language_changed` Signal triggers `retranslate()` on all registered screens.
- **Graceful shutdown:** `app.aboutToQuit` stops AppState polling, shuts down the Session Engine daemon (`lifecycle.shutdown()`), and shuts down the backend console
- **First-run gate:** If `SETUP_COMPLETED` setting is False, the app starts on WizardScreen instead of HomeScreen
- **Backend boot failure:** If the backend console fails to boot, a `QMessageBox` warning is shown but the app continues running in degraded mode
