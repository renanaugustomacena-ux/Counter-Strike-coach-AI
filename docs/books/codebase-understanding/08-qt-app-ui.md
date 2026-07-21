# Chapter 8 -- Qt App UI Layer

> **Scope:** Every class, function, constant, and mechanism in
> `Programma_CS2_RENAN/apps/qt_app/` -- the PySide6 (Qt) frontend.
>
> **File inventory:** 80+ source files across `qt_app/` (core, screens,
> viewmodels, widgets).

---

## Table of Contents

1. [Package Root and Init Files](#1-package-root-and-init-files)
2. [Qt App Entry Point (`app.py`)](#2-qt-app-entry-point)
3. [Main Window (`main_window.py`)](#3-main-window)
4. [Core Infrastructure (`core/`)](#4-core-infrastructure)
   - 4.1 [Animation Framework](#41-animation-framework)
   - 4.2 [Application State Singleton](#42-application-state-singleton)
   - 4.4 [Design Tokens](#44-design-tokens)
   - 4.5 [Easing Curves](#45-easing-curves)
   - 4.6 [Internationalization Bridge](#46-internationalization-bridge)
   - 4.7 [Icon System](#47-icon-system)
   - 4.8 [Match Utilities](#48-match-utilities)
   - 4.9 [QSS Generator](#49-qss-generator)
   - 4.10 [Playback Engine](#410-playback-engine)
   - 4.11 [Sound Manager](#411-sound-manager)
   - 4.12 [SVG Icon Provider](#412-svg-icon-provider)
   - 4.13 [Theme Engine](#413-theme-engine)
   - 4.14 [Typography](#414-typography)
   - 4.15 [Web Bridge](#415-web-bridge)
   - 4.16 [Widget Helpers](#416-widget-helpers)
   - 4.17 [Worker](#417-worker)
5. [Screens (`screens/`)](#5-screens)
   - 5.1 [Placeholder Factory](#51-placeholder-factory)
   - 5.2 [Home Screen (Dashboard)](#52-home-screen)
   - 5.3 [Coach Screen](#53-coach-screen)
   - 5.4 [Match History Screen](#54-match-history-screen)
   - 5.5 [Match Detail Screen](#55-match-detail-screen)
   - 5.6 [Performance Screen](#56-performance-screen)
   - 5.7 [Tactical Viewer Screen](#57-tactical-viewer-screen)
   - 5.8 [Settings Screen](#58-settings-screen)
   - 5.9 [Help Screen](#59-help-screen)
   - 5.10 [Profile Screen](#510-profile-screen)
   - 5.11 [User Profile Screen](#511-user-profile-screen)
   - 5.12 [Steam Config Screen](#512-steam-config-screen)
   - 5.13 [FaceIT Config Screen](#513-faceit-config-screen)
   - 5.14 [Wizard Screen](#514-wizard-screen)
   - 5.15 [Pro Comparison Screen](#515-pro-comparison-screen)
   - 5.16 [Pro Player Detail Screen](#516-pro-player-detail-screen)
6. [ViewModels (`viewmodels/`)](#6-viewmodels)
   - 6.1 [Coach ViewModel](#61-coach-viewmodel)
   - 6.2 [Coaching Chat ViewModel](#62-coaching-chat-viewmodel)
   - 6.3 [Focus Insight ViewModel](#63-focus-insight-viewmodel)
   - 6.4 [Match Detail ViewModel](#64-match-detail-viewmodel)
   - 6.5 [Match History ViewModel](#65-match-history-viewmodel)
   - 6.6 [Performance ViewModel](#66-performance-viewmodel)
   - 6.7 [Pro Comparison ViewModel](#67-pro-comparison-viewmodel)
   - 6.8 [Pro Player Detail ViewModel](#68-pro-player-detail-viewmodel)
   - 6.9 [Tactical ViewModel](#69-tactical-viewmodel)
   - 6.10 [User Profile ViewModel](#610-user-profile-viewmodel)
7. [Widgets (`widgets/`)](#7-widgets)
   - 7.1 [Skeleton Loader](#71-skeleton-loader)
   - 7.2 [Toast Notifications](#72-toast-notifications)
   - 7.3 [Charts](#73-charts)
   - 7.5 [Design System Components](#75-design-system-components)
   - 7.6 [Tactical Widgets](#76-tactical-widgets)
9. [Architecture and Design Decisions](#9-architecture-and-design-decisions)

---

## 1. Package Root and Init Files

### `apps/__init__.py`

Empty file. Marks `Programma_CS2_RENAN.apps` as a Python package. Contains no code, no docstring.

### `apps/qt_app/__init__.py`

Single-line docstring:

```python
"""PySide6 (Qt) frontend for Macena CS2 Analyzer."""
```

### `apps/qt_app/core/__init__.py`

Single-line docstring:

```python
"""Qt app core utilities -- threading, theming, i18n, assets."""
```

### `apps/qt_app/screens/__init__.py`

Single-line docstring:

```python
"""Qt screen widgets -- one per app page, registered with MainWindow."""
```

### `apps/qt_app/viewmodels/__init__.py`

Single-line docstring. Marks the viewmodel package.

### `apps/qt_app/widgets/__init__.py`, `widgets/charts/__init__.py`, `widgets/coaching/__init__.py`, `widgets/components/__init__.py`, `widgets/tactical/__init__.py`

Init files for each widget subpackage. Typically contain only docstrings or are empty.

---

## 2. Qt App Entry Point

**File:** `apps/qt_app/app.py`

The application bootstrap module. Launched via `python -m Programma_CS2_RENAN.apps.qt_app.app`.

### Functions

#### `_create_splash(app_version: str) -> QSplashScreen`

Creates a branded splash screen (520x320 pixels) with:
- Dark gradient background (`#14141e` to `#0a0a14`)
- CS2-orange accent bar at top (`#d96600`, 4px)
- Title "MACENA CS2 ANALYZER" in Roboto 22pt Bold
- Subtitle "AI-Powered Coaching Platform" in Roboto 11pt
- Version string in JetBrains Mono 9pt
- Orange divider line and bottom border
- Window flags: `SplashScreen | FramelessWindowHint | WindowStaysOnTopHint`

#### `_splash_status(splash: QSplashScreen, message: str) -> None`

Updates the splash status message (bottom-left, `#a0a0b0` color) and calls `QApplication.processEvents()` to keep the splash responsive.

#### `_resolve_app_version() -> str`

Reads the installed package version via `importlib.metadata.version("macena-cs2-analyzer")`. Falls back to `"1.0.0"` on `PackageNotFoundError`.

#### `_install_quit_handler(app: QApplication) -> None`

Wires `app.aboutToQuit` to a shutdown sequence:
1. `get_app_state().stop_polling()` -- stops the 10s CoachState poll timer
2. `lifecycle.shutdown()` -- halts the Session Engine subprocess (Scanner/Digester/Teacher/Pulse)
3. `get_console().shutdown()` -- closes Console database connections

Ordering is critical: polling stops first, then daemon, then Console DB handles.

#### `_apply_theme(app: QApplication, splash: QSplashScreen) -> ThemeEngine`

Registers custom fonts via `ThemeEngine.register_fonts()`. Reads user preferences:
- `FONT_TYPE` (default `"Roboto"`)
- `FONT_SIZE` (default `"Medium"` = 13pt; Small=11, Large=16)
- `ACTIVE_THEME` (default `"CS2"`)

Applies the theme stylesheet and palette to the QApplication.

#### `_create_screens(theme: ThemeEngine) -> dict`

Deferred import of all 16 screen classes to keep module-level import cheap. Returns a dict mapping screen names to widget instances:

| Key | Class |
|---|---|
| `"match_history"` | `MatchHistoryScreen` |
| `"match_detail"` | `MatchDetailScreen` |
| `"performance"` | `PerformanceScreen` |
| `"settings"` | `SettingsScreen(theme_engine=theme)` |
| `"wizard"` | `WizardScreen` |
| `"user_profile"` | `UserProfileScreen` |
| `"profile"` | `ProfileScreen` |
| `"home"` | `HomeScreen` |
| `"coach"` | `CoachScreen` |
| `"steam_config"` | `SteamConfigScreen` |
| `"faceit_config"` | `FaceitConfigScreen` |
| `"help"` | `HelpScreen` |
| `"tactical_viewer"` | `TacticalViewerScreen` |
| `"pro_comparison"` | `ProComparisonScreen` |
| `"pro_player_detail"` | `ProPlayerDetailScreen` |

#### `_wire_screen_signals(window: MainWindow, screens: dict) -> None`

Cross-screen routing:
- `match_history.match_selected` and `home.match_selected` -> loads demo in `match_detail`, then switches to it
- `wizard.setup_completed` -> switches to `"home"`
- `pro_comparison.pro_detail_requested(hltv_id)` -> loads pro in `pro_player_detail`, switches to it
- `pro_player_detail.back_requested` -> switches back to `"pro_comparison"`

#### `_boot_backend_services(splash: QSplashScreen) -> None`

Boots the Console (`get_console().boot()`) and launches the Session Engine daemon (`lifecycle.launch_daemon()`). Errors are logged but never raised -- the app remains usable even if the backend fails.

#### `_ensure_sbert_model(splash: QSplashScreen) -> None`

WR-10 feature: pre-downloads the SBERT RAG model (~90 MB) on first run. Uses a background thread with a polling loop that calls `QApplication.processEvents()` to keep the splash responsive. Failure is silently caught -- the coach falls back to dense similarity.

#### `_install_qt_excepthook() -> None`

Installs `sys.excepthook` to log uncaught exceptions from Qt signal/slot dispatch. Preserves the original excepthook and chains to it.

#### `_show_boot_failure_warning_if_needed(window: MainWindow) -> None`

Shows a `QMessageBox.warning` if `get_console()` raises. The modal requires the main window as parent so it appears after the window is shown.

#### `main()`

The complete boot sequence:
1. Enable High-DPI: `PassThrough` rounding policy
2. Create `QApplication`
3. Resolve version, set app name/version
4. Show splash
5. Install quit handler
6. Apply theme
7. Create `MainWindow`
8. Set wallpaper from theme
9. Create placeholder screens, then real screens
10. Wire cross-screen signals
11. Register all screens with the window
12. Check `SETUP_COMPLETED` -- route to `"home"` or `"wizard"`
13. Store theme engine reference on window
14. Boot backend services
15. Pre-download SBERT model
16. Show window, finish splash
17. Show boot failure warning if needed
18. Start AppState 10s polling
19. Install Qt excepthook
20. `sys.exit(app.exec())`

---

## 3. Main Window

**File:** `apps/qt_app/main_window.py`

### Class: `_CustomTitleBar(QFrame)`

Hand-rolled frameless titlebar (36px height) with:
- Title label (`QLabel`)
- Three buttons: Minimize (`-`), Maximize/Restore (`[]`), Close (`x`)
- Drag-to-move: tracks press offset so window moves 1:1 with cursor
- Double-click title bar toggles maximize
- Only instantiated when `AppState.use_frameless_window` is True
- Caveat: no native snap-to-edge (OS window manager feature)

**Methods:**
- `__init__(parent: QMainWindow)` -- builds the 3-button + title layout
- `_toggle_maximize()` -- switches between `showNormal()` and `showMaximized()`
- `mousePressEvent(event)` -- records drag offset on left click (non-maximized)
- `mouseMoveEvent(event)` -- moves window by cursor delta
- `mouseReleaseEvent(event)` -- clears drag offset
- `mouseDoubleClickEvent(event)` -- toggles maximize

### Class: `_BackgroundWidget(QWidget)`

Paints two composited layers behind all screen content:

1. **Wallpaper pixmap** -- center-cropped, scaled via `KeepAspectRatioByExpanding`, at opacity 0.25. Cached as `_scaled_cache` (invalidated on resize).
2. **Tactical-grid motif** -- SVG from `design/assets/motifs/tactical-grid.svg`, rendered once into a 64x64 `QPixmap` tile, painted via `drawTiledPixmap` at opacity 0.05.

**Constants:**
- `_MOTIF_PATH` -- path to the tactical-grid SVG

**Methods:**
- `_render_motif_tile(cls)` -- classmethod, renders SVG into 64x64 pixmap via `QSvgRenderer`
- `set_image(path: str)` -- loads a wallpaper image file
- `resizeEvent(event)` -- invalidates scaled cache
- `paintEvent(event)` -- composites both layers

### Class: `MainWindow(QMainWindow)`

Root application window. Contains the collapsible sidebar, content stack, toast overlay, and coach dock.

**Signal:**
- `screen_changed(str)` -- emitted after navigating to a new screen

**Construction:**
- Minimum size: 1280x720
- Title: `"Macena CS2 Analyzer v{version}"`
- Frameless mode: reads `AppState.use_frameless_window` at construction (runtime flip requires restart)
- Layout structure:
  - If frameless: `QVBoxLayout(central)` -> `_CustomTitleBar` + body
  - If framed: `QHBoxLayout(central)` directly
  - Left: `NavSidebar` (collapsible)
  - Right: `QStackedLayout` in `StackAll` mode:
    - Layer 0: `_BackgroundWidget` (wallpaper)
    - Layer 1: `QStackedWidget` (screen stack, transparent bg)
  - Toast container: floating child of `content_wrapper`, not in the stacked layout

**Keyboard shortcuts:**

| Shortcut | Screen |
|---|---|
| `Ctrl+1` | home |
| `Ctrl+2` | coach |
| `Ctrl+3` | match_history |
| `Ctrl+4` | performance |
| `Ctrl+5` | tactical_viewer |
| `Ctrl+,` | settings |
| `F1` | help |

**Methods:**
- `set_wallpaper(path: str)` -- delegates to `_BackgroundWidget.set_image()`
- `register_screen(name: str, widget: QWidget)` -- adds to stack; special-cases `"coach"` as a `QDockWidget`
- `_register_coach_dock(widget)` -- wraps CoachScreen in a `QDockWidget` pinned to `RightDockWidgetArea` or `BottomDockWidgetArea`. Persists dock area, floating, and visibility state in `user_settings.json`.
- `switch_screen(name: str)` -- navigates to a named screen:
  - `"coach"` toggles the dock visibility instead of switching the stack
  - Calls `on_leave()` on old widget, `on_enter()` on new widget
  - Updates sidebar active state
  - Emits `screen_changed` signal
  - Fade animation is disabled (QPainter errors on Linux)
- `_show_toast(severity: str, message: str)` -- delegates to `ToastContainer.add_toast()`
- `_refresh_nav_labels(_lang: str)` -- called on i18n language change; retranslates sidebar and all screens
- `eventFilter(obj, event)` -- repositions toast overlay on content area resize

---

## 4. Core Infrastructure

### 4.1 Animation Framework

**File:** `apps/qt_app/core/animation.py`

#### Function: `_ensure_opacity_effect(widget) -> QGraphicsOpacityEffect`

Attaches a `QGraphicsOpacityEffect` if not already present. Returns the effect.

#### Class: `Animator`

Static method collection for reusable animations.

**Methods:**

| Method | Description | Default Duration |
|---|---|---|
| `fade_in(widget, duration=200)` | Opacity 0->1, `OutCubic` easing | 200ms |
| `fade_out(widget, duration=150, hide_on_finish=False)` | Opacity current->0, `InCubic` easing | 150ms |
| `pulse(widget, low=0.3, high=0.8, duration=1200)` | Infinite breathing loop for skeletons. Returns `QSequentialAnimationGroup` for caller to `stop()`. | 1200ms/cycle |
| `cross_fade(old_widget, new_widget, duration=200)` | Fades out old, then fades in new. | 200ms total |
| `slide_in(widget, direction="right", distance_px=24, duration=220, easing=None)` | Slides from offset to resting position. Animates `geometry` (safe on mid-repaint). | 220ms |
| `slide_out(widget, direction="right", distance_px=24, duration=180, easing=None, hide_on_finish=True)` | Slides away from resting position. | 180ms |
| `reveal_stagger(widgets, delay_ms=40, duration=220, distance_px=16, direction="up")` | Staggered slide-in for card lists/bento grids. Uses `QTimer.singleShot` per widget. | 220ms per item, 40ms stagger |
| `collapse_width(widget, to_width, duration=200, easing=None)` | Animates geometry to target width. Used for sidebar collapse/expand. | 200ms |

**Safety note:** `slide_in`, `slide_out`, `reveal_stagger`, `collapse_width` animate `geometry`, not opacity, making them safe on widgets that may repaint concurrently. Prefer them over `fade_in`/`fade_out` during screen transitions.

### 4.2 Application State Singleton

**File:** `apps/qt_app/core/app_state.py`

#### Function: `get_app_state() -> AppState`

Returns the global singleton. Created on first call.

#### Class: `AppState(QObject)`

Polls the `CoachState` database row (id=1) every 10 seconds. Read-only -- the Qt app never writes to CoachState.

**Signals:**

| Signal | Type | Description |
|---|---|---|
| `service_active_changed` | `bool` | True if heartbeat delta < 300s |
| `coach_status_changed` | `str` | Ingest status from CoachState |
| `parsing_progress_changed` | `float` | 0-100 parsing progress |
| `belief_confidence_changed` | `float` | Model belief confidence |
| `total_matches_changed` | `int` | Distinct demo count from PlayerMatchStats |
| `training_changed` | `dict` | Bundle of epoch/loss/ETA fields |
| `notification_received` | `(str, str)` | (severity, message) from ServiceNotification |
| `sounds_enabled_changed` | `bool` | P3 toggle |
| `use_frameless_window_changed` | `bool` | P3 toggle |
| `use_pyqtgraph_heatmap_changed` | `bool` | P3 toggle |
| `use_webengine_marquee_changed` | `bool` | P4 toggle |

**Properties (persisted via user settings):**
- `sounds_enabled` -- micro-interaction sound effects
- `use_frameless_window` -- hand-rolled titlebar chrome
- `use_pyqtgraph_heatmap` -- match_detail pyqtgraph heatmap preference
- `use_webengine_marquee` -- React+D3 web views for marquee screens
- `cached_state` -- last-polled state snapshot dict

**Methods:**
- `start_polling()` -- starts 10s QTimer; calls `_poll()` immediately on first invocation
- `stop_polling()` -- stops the timer
- `_poll()` -- launches a `Worker` that calls `_bg_read()` in the thread pool
- `_bg_read()` -- static method; opens a DB session, reads CoachState, queries unread ServiceNotifications (marks them read), counts distinct demos in PlayerMatchStats
- `_apply(data)` -- compares new data against `_prev`, emits changed signals
- `_on_error(msg)` -- logs warning
- `_read_toggle(key)` / `_write_toggle(key, value)` -- reads/writes boolean toggles from `core.config`

### 4.4 Design Tokens

**File:** `apps/qt_app/core/design_tokens.py`

Auto-generated from `design/tokens/design-tokens.json` via `tools/gen_design_tokens.py`.

#### Class: `DesignTokens` (frozen dataclass)

Single source of truth for every visual constant. 80+ fields organized in categories:

**Theme identity:** `theme_name`, `surface_base`

**Surfaces (4-layer depth system):**
- `surface_raised` -- cards, panels (1 layer up)
- `surface_overlay` -- tooltips, dropdowns (2 layers up)
- `surface_sunken` -- inputs, wells (1 layer down)
- `surface_sidebar` -- navigation sidebar
- `surface_raised_rgba` -- card bg with alpha channel

**Borders:** `surface_card_hover_border`, `border_subtle`, `border_default`, `border_accent_muted`

**Text hierarchy (5 levels):** `text_primary`, `text_secondary`, `text_tertiary`, `text_inverse`, `text_disabled`

**Accent (theme-specific):** `accent_primary`, `accent_hover`, `accent_pressed`, `accent_muted_15`, `accent_muted_25`, `accent_muted_30`

**Semantic colors:** `success`, `warning`, `error`, `info`

**Toast backgrounds/borders:** `toast_info_bg/border`, `toast_warning_bg/border`, `toast_error_bg/border`, `toast_critical_bg/border`, `toast_dismiss`

**Chart palette:** `chart_bg`, `chart_grid`, `chart_axis`, `chart_line_primary`, `chart_line_secondary`, `chart_fill_positive`, `chart_fill_negative`

**Frost/glass (Phase 7):** `frost_bg`, `frost_bg_hover`, `frost_border`, `frost_glow`, `frost_blur_radius` (12), `frost_elevation_blur` (24), `frost_elevation_offset` (6)

**Spacing scale (4px grid):** `spacing_xs=4`, `spacing_sm=8`, `spacing_md=12`, `spacing_lg=16`, `spacing_xl=24`, `spacing_xxl=32`, `spacing_xxxl=48`

**Typography scale:** `font_size_caption=11`, `font_size_body=13`, `font_size_subtitle=14`, `font_size_title=18`, `font_size_h1=24`, `font_size_stat=28`, `font_size_display=32`

**Border radius:** `radius_sm=4`, `radius_md=8`, `radius_lg=16`, `radius_xl=24`

#### Pre-built Theme Instances

| Instance | Accent | Surface Base |
|---|---|---|
| `CS2_TOKENS` | `#FF6A00` (orange) | `#0B1628` (deep navy) |
| `CSGO_TOKENS` | `#617d8c` (steel blue) | `#1a1c21` (dark slate) |
| `CS16_TOKENS` | `#4db04f` (green) | `#121a12` (dark forest) |

#### Functions

- `get_tokens(theme_name=None) -> DesignTokens` -- returns tokens for a theme (defaults to active theme)
- `set_active_theme(name: str) -> None` -- updates the module-level `_active_theme` variable

### 4.5 Easing Curves

**File:** `apps/qt_app/core/easing.py`

#### Class: `Easing`

Named `QEasingCurve` aliases for the Remotion library curves used in design assets.

**Static attributes:** `Linear`, `InCubic`, `OutCubic`, `InOutCubic`, `InExpo`, `OutExpo`, `InOutExpo`, `InBack`, `OutBack`, `InOutBack`, `InSine`, `OutSine`, `InOutSine`

**Static method:** `cubic_bezier(x1, y1, x2, y2) -> QEasingCurve` -- creates a CSS-style cubic bezier via `QEasingCurve.BezierSpline` + `addCubicBezierSegment`.

### 4.6 Internationalization Bridge

**File:** `apps/qt_app/core/i18n_bridge.py`

Qt-native localization that reuses the core translation system without Kivy dependencies.

#### Constants

`_HARDCODED_EN` -- minimal fallback dict with 12 keys (app_name, dashboard, coaching, settings, profile, match_history_title, tactical_analysis, tactical_analyzer, rap_coach_dashboard, advanced_analytics, knowledge_engine, training_progress, help).

#### Functions

- `_get_home_dir() -> str` -- returns `os.path.expanduser("~")`
- `_load_json_translations() -> dict` -- loads `en.json`, `pt.json`, `it.json` from `assets/i18n/`. Substitutes `{home_dir}` placeholders.

#### Class: `QtLocalizationManager(QObject)`

**Signal:** `language_changed(str)` -- emitted when `set_language()` changes the active language

**Methods:**
- `get_text(key, default=None) -> str` -- lookup priority: JSON (current lang) > hardcoded (current lang) > hardcoded English > caller default > raw key
- `set_language(lang_code: str)` -- validates against available translations, emits `language_changed`

**Singleton:** `i18n = QtLocalizationManager()`

### 4.7 Icon System

**File:** `apps/qt_app/core/icons.py`

Dual-provider icon system with an SVG sprite primary path and QPainterPath fallback.

#### Constant: `USE_SVG_ICONS = True`

Flip to `False` to force the QPainterPath fallback.

#### Function: `_render(path, size, color, stroke=1.5) -> QPixmap`

Renders a `QPainterPath` into a `QPixmap`. Scales from 24x24 design space. Uses antialiased, round-capped, round-joined strokes.

#### Class: `_QPainterPathIconProvider`

Fallback icon factory. All methods are `@staticmethod`, return `QIcon`, take `size=24` and `color="#ffffff"`.

Icons: `home` (house), `brain` (circle with partitions), `list_icon` (three lines with bullets), `chart` (ascending bars), `crosshair` (target), `gear` (cog with 8 teeth), `help_circle` (question mark in circle).

#### Module-level selection

```python
IconProvider = SvgIconProvider if USE_SVG_ICONS and sprite_is_available() else _QPainterPathIconProvider
```

### 4.8 Match Utilities

**File:** `apps/qt_app/core/match_utils.py`

#### Constants

- `_MAP_PATTERN` -- regex matching `de_*/cs_*/ar_*` map prefixes (stops at second underscore)
- `_KNOWN_MAPS` -- frozenset of 11 bare map names: mirage, inferno, dust2, overpass, ancient, anubis, nuke, vertigo, train, cache, office

#### Functions

- `extract_map_name(demo_name: str) -> str` -- extracts `de_mirage` style map id from demo filenames. Falls back to bare name matching against `_KNOWN_MAPS`. Returns `"Unknown Map"` on failure.
- `map_short_name(demo_name: str) -> str` -- returns the bare map name with prefix stripped (e.g., `"mirage"`). Returns `"--"` on unknown.

### 4.9 QSS Generator

**File:** `apps/qt_app/core/qss_generator.py`

Template-based QSS stylesheet generator. Replaces three duplicate QSS files with one `base.qss.template` file where `$token_name` variables are substituted at runtime.

**Constants:**
- `_TEMPLATE_PATH` -- path to `themes/base.qss.template`
- `_cache` -- dict of `theme_name -> rendered QSS string`

**Functions:**
- `render_qss(tokens: DesignTokens) -> str` -- renders template with `string.Template.safe_substitute(asdict(tokens))`. Caches per theme name.
- `invalidate_cache(theme_name=None)` -- clears cache for one or all themes

### 4.10 Playback Engine

**File:** `apps/qt_app/core/qt_playback_engine.py`

#### Class: `QtPlaybackEngine(PlaybackEngine)`

Subclass of the base `PlaybackEngine` that uses `QTimer` instead of Kivy's `Clock`.

- Timer interval: 16ms (~60 FPS)
- `play()` -- starts timer if frames exist; resets to frame 0 if at end
- `pause()` -- stops timer
- `_qt_tick()` -- computes delta time via `time.monotonic()`, calls `_tick(dt)`
- `_clock_event = None` -- prevents parent from using Kivy Clock

### 4.11 Sound Manager

**File:** `apps/qt_app/core/sound.py`

#### Type: `SoundName = Literal["click", "success", "error", "notification"]`

#### Constants

- `_SOUND_DIR = "PHOTO_GUI/sounds"`
- `_FILES` -- dict mapping `SoundName` to WAV filenames

#### Class: `SoundManager(QObject)`

Preloads four `QSoundEffect` instances at volume 0.6. Gated behind `AppState.sounds_enabled` (default False).

**Methods:**
- `__init__(app_state, parent=None)` -- loads effects from `PHOTO_GUI/sounds/`
- `_load_effects()` -- creates `QSoundEffect` for each WAV
- `play(name: SoundName)` -- no-op if sounds disabled or file missing. Warns exactly once per missing file per session.

### 4.12 SVG Icon Provider

**File:** `apps/qt_app/core/svg_icon_provider.py`

Primary icon factory that renders from `design/assets/icons/sprite.svg`.

#### Module-level processing

1. `_sprite_raw()` -- reads sprite SVG text, warns if missing
2. `_SYMBOL_RE` -- regex extracting `<symbol id="..." viewBox="...">...</symbol>`
3. `_build_symbol_svgs(raw)` -- wraps each symbol as a standalone SVG document
4. `_SYMBOL_SVGS` -- dict of `symbol_id -> standalone SVG text`

#### Function: `_render_symbol(symbol_id, size, color) -> QPixmap`

Substitutes `currentColor` with the requested color, renders via `QSvgRenderer` at 2x supersampling, then downscales for HiDPI clarity.

#### Class: `SvgIconProvider`

**Class cache:** `_cache: dict[tuple[str, int, str], QIcon]` -- permanent per-session

**Nav/chrome icons:** `home`, `brain`, `list_icon`, `chart`, `crosshair`, `gear`, `help_circle`, `user`

**Game icons (SVG-only):** `bomb`, `defuser`, `smoke`, `flash`, `molotov`, `he`, `rifle`, `awp`, `pistol`, `knife`

**Status glyphs:** `check`, `warn`, `bolt`, `db`

Each maps to a sprite symbol id like `i-home`, `i-brain`, etc.

#### Function: `sprite_is_available() -> bool`

True if the sprite loaded and parsed successfully.

### 4.13 Theme Engine

**File:** `apps/qt_app/core/theme_engine.py`

#### Constants

| Constant | Value | Description |
|---|---|---|
| `COLOR_GREEN` | `(0.30, 0.69, 0.31, 1)` | RGBA green |
| `COLOR_YELLOW` | `(1.0, 0.60, 0.0, 1)` | RGBA yellow |
| `COLOR_RED` | `(0.96, 0.26, 0.21, 1)` | RGBA red |
| `COLOR_CARD_BG` | `(0.12, 0.12, 0.14, 1)` | RGBA card bg |
| `RATING_GOOD` | `1.10` | Threshold for good rating |
| `RATING_BAD` | `0.90` | Threshold for bad rating |
| `PALETTES` | dict | Three theme palettes (CS2/CSGO/CS1.6) with surface, surface_alt, accent_primary, chart_bg |

Directory constants:
- `_THEMES_DIR` -- `qt_app/themes/`
- `_ASSETS_DIR` -- `PHOTO_GUI/`
- `_DISPLAY_FONTS_DIR` -- `assets/fonts/` (P4 Neo-tactical noir display fonts)
- `_THEME_WALLPAPER_FOLDER` -- maps theme name to subfolder
- `_FONT_FILES` -- maps 5 font names to filenames

#### Functions

- `rgba_to_qcolor(rgba: list[float]) -> QColor` -- converts `[r,g,b,a]` (0-1 floats) to QColor
- `rating_color(rating: float) -> QColor` -- green/yellow/red based on thresholds
- `rating_label(rating: float) -> str` -- "Excellent"/"Good"/"Average"/"Below Avg" (WCAG color-blind accessible)

#### Class: `ThemeEngine(QObject)`

**Signal:** `theme_changed(str)` -- emitted after a theme switch

**Properties:** `active_theme`, `tokens`, `chart_bg`, `wallpaper_path`

**Methods:**
- `get_color(slot: str) -> QColor` -- returns QColor for a palette slot
- `apply_theme(name: str, app=None)` -- renders QSS from template, appends font rule, sets QPalette with 15+ color roles, updates wallpaper, emits `theme_changed`
- `set_font(family, size_pt)` -- invalidates QSS cache, re-applies theme
- `register_fonts()` -- registers fonts from `PHOTO_GUI/` (5 fonts) and `assets/fonts/` (auto-scan for `.ttf`/`.otf`). Called once.
- `_update_wallpaper(theme_name)` -- picks wallpaper from theme folder (prefers "vertical" images)
- `get_available_wallpapers(theme_name=None) -> list[str]` -- lists wallpaper filenames
- `set_wallpaper(filename: str)` -- sets a specific wallpaper

### 4.14 Typography

**File:** `apps/qt_app/core/typography.py`

#### Constants

- `_SANS = "Roboto"`, `_DISPLAY = "Space Grotesk"`, `_MONO = "JetBrains Mono"`
- `_QSS_ROLES` -- frozenset of roles handled by QSS: `display`, `h1`, `caption`, `mono`, `accent`

#### Class: `Typography`

Static helper (never instantiated).

**Methods:**
- `apply(widget, role)` -- for QSS-backed roles, sets `variant` property and re-polishes; otherwise calls `setFont()`
- `font(role) -> QFont` -- returns a configured QFont for the role

**Role definitions:**

| Role | Family | Size (token) | Weight | Extra |
|---|---|---|---|---|
| `display` | Space Grotesk | `font_size_display` (32) | Black | Letter spacing -1.0 |
| `h1` | Space Grotesk | `font_size_h1` (24) | Bold | Letter spacing -0.5 |
| `title` | Roboto | `font_size_title` (18) | DemiBold | |
| `subtitle` | Roboto | `font_size_subtitle` (14) | Bold | |
| `body` | Roboto | `font_size_body` (13) | Normal | |
| `caption` | Roboto | `font_size_caption` (11) | DemiBold | Uppercase, letter spacing 1.5 |
| `mono` | JetBrains Mono | `font_size_body` (13) | Normal | |
| `stat` | Space Grotesk | `font_size_stat` (28) | Bold | |

### 4.15 Web Bridge

**File:** `apps/qt_app/core/web_bridge.py`

Python-to-JS bridge for marquee web apps (React+D3/Three.js in `QWebEngineView`).

#### Class: `MarqueeBridge(QObject)`

**Signals (Python -> JS):**
- `tick_changed(int)`, `frame_ready(str)`, `coach_state_changed(str)`, `ready_changed(bool)`
- `map_name_changed(str)`, `segments_ready(str)`, `events_ready(str)`, `ghost_ready(str)`

**Signals (JS -> Python):**
- `seek_requested(int)`, `player_selected(int)`, `ghost_requested(int)`

**Q_PROPERTIES (observable from JS):**
- `current_tick` (int), `frame_payload` (str), `coach_state` (str), `ready` (bool)
- `map_name` (str), `segments` (str), `events` (str), `ghost` (str)

**Python-side publish methods:**
- `publish_tick(tick)`, `publish_frame(frame_dict)`, `publish_coach_state(coach_dict)`
- `publish_map(map_name)`, `publish_segments(segments_dict)`, `publish_events(events_list)`, `publish_ghost(ghosts_list)`

All publish methods serialize to compact JSON (`separators=(",",":")`) with `default=str` for non-serializable types.

**JS-invocable slots:**
- `seek_to_tick(tick)` -- emits `seek_requested`
- `select_player(player_id)` -- emits `player_selected`
- `request_ghost(tick)` -- emits `ghost_requested`
- `log(level, message)` -- routes web-side console logs to Python logger

### 4.16 Widget Helpers

**File:** `apps/qt_app/core/widgets_helpers.py`

#### Type: `ButtonVariant = Literal["primary", "secondary", "ghost", "danger"]`

#### Function: `make_button(text, variant="secondary", fixed_width=None, parent=None) -> QPushButton`

Factory for themed buttons. Sets the `variant` property (consumed by `QPushButton[variant="..."]` rules in `base.qss.template`), pointing-hand cursor, optional fixed width, and re-polishes.

### 4.17 Worker

**File:** `apps/qt_app/core/worker.py`

Drop-in replacement for Kivy's Thread + Clock pattern.

#### Class: `WorkerSignals(QObject)`

- `finished` -- Signal()
- `error` -- Signal(str)
- `result` -- Signal(object)

All signals auto-marshal to the main thread via Qt's signal/slot mechanism.

#### Class: `Worker(QRunnable)`

Generic background worker.

- `__init__(fn, *args, **kwargs)` -- stores callable and arguments; sets `autoDelete=True`
- `run()` -- calls `fn(*args, **kwargs)`, emits `result` on success, `error` on exception, `finished` always. Catches `RuntimeError` on signal emission (receiver may be GC'd).

Usage pattern:
```python
worker = Worker(some_function, arg1, arg2)
worker.signals.result.connect(on_success)
worker.signals.error.connect(on_error)
QThreadPool.globalInstance().start(worker)
```

---

## 5. Screens

### 5.1 Placeholder Factory

**File:** `apps/qt_app/screens/placeholder.py`

Function `create_placeholder_screens()` returns a dict of lightweight placeholder `QWidget` instances for all screen slots. These are created before the real screens and then replaced by `placeholders.update(real_screens)` in `app.py`. This ensures every screen slot has a valid widget even if a real screen fails to import.

### 5.2 Home Screen (Dashboard)

**File:** `apps/qt_app/screens/home_screen.py`

#### Class: `HomeScreen(QWidget)`

The dashboard / landing page. Composition:
- Title rail with "Dashboard" title and two status chips (service status, match count)
- Hero section (stacked layout): Page A = hero pair + recent strip, Page B = onboarding card
- Utility row (3-column): Ingest card, Training card (hidden when idle), Tactical card

**Signal:** `match_selected(str)` -- demo_name, wired to MatchDetailScreen

**ViewModels used:** `MatchHistoryViewModel`, `FocusInsightViewModel`

**Key methods:**
- `on_enter()` -- refreshes path display, connects AppState signals (once), kicks off async loads
- `_build_ui()` -- constructs the entire layout tree
- `_build_recent_strip()` -- horizontal scrollable row of `MatchMiniCard` widgets
- `_build_onboarding_card()` -- `EmptyState` widget for cold start, with CTA to pick demo folder
- `_build_ingest_card()` -- personal and pro demo analysis rows with path labels, Change/Analyze buttons, progress bar
- `_build_training_card()` -- epoch/loss/ETA display, hidden until training is active
- `_build_tactical_card()` -- "Open viewer" and "Compare pros" buttons
- `_on_matches_changed(matches)` -- filters user vs pro matches, populates hero card and recent strip, updates dual-count chip
- `_on_start_analysis()` / `_on_start_pro_analysis()` -- background `Worker` calling `process_new_demos()`
- `_on_training(data)` -- shows/hides training card, rebalances utility row stretch factors
- `_on_total_matches(count)` -- fallback if `_on_matches_changed` hasn't populated the chip yet

### 5.3 Coach Screen

**File:** `apps/qt_app/screens/coach_screen.py`

#### Constants

- `_QUICK_ACTION_KEYS` -- 3 preset coaching questions (positioning, utility, focus)
- `_MAP_RE` -- regex for extracting map names from demo filenames

#### Helper functions

- `_map_from_demo(demo_name)` -- extracts title-cased map name
- `_severity_color(severity, tokens)` -- maps high/medium/low to error/warning/success tokens

#### Class: `CoachScreen(QWidget)`

AI coaching surface with insights and collapsible chat composer.

**ViewModels:** `CoachViewModel`, `CoachingChatViewModel`

**Layout:**
- Scrollable main surface with title rail (title + chat status chip + toggle button)
- Belief confidence card (ProgressRing + numeric label)
- Insights card (dynamic list of insight cards with severity-colored left border)
- LLM Coach settings card (Ollama model picker with QComboBox + Refresh button)
- Chat panel (fixed-height 420px, hidden by default):
  - Header with status chip, Clear button, Collapse button
  - Message scroll area with chat bubbles (user right-aligned, assistant left-aligned, system error-styled)
  - Typing indicator
  - Quick action chips row
  - Composer: QLineEdit + Send button

**Key methods:**
- `on_enter()` -- connects belief signal, loads insights, checks chat availability, lazy-loads LLM models
- `_toggle_chat()` -- shows/hides the chat panel, starts chat session
- `_refresh_llm_models()` -- queries Ollama `/api/tags`, populates combobox (gemma family sorted first)
- `_on_llm_model_picked(_label)` -- persists model selection to `LLM_COACH_MODEL`
- `_on_insights(insights)` -- clears and rebuilds insight cards
- `_render_messages(messages)` -- clears and rebuilds chat bubbles with role-specific styling
- `_on_chat_availability(available)` -- updates status chips ("Online"/"Offline")

### 5.4 Match History Screen

**File:** `apps/qt_app/screens/match_history_screen.py`

#### Constants

- `_SOURCE_ALL`, `_SOURCE_PERSONAL`, `_SOURCE_PRO` -- source filter keys
- `_MAP_ALL = "__all__"` -- map filter key
- `_BUCKET_ORDER = ("TODAY", "THIS WEEK", "EARLIER")` -- time grouping order

#### Helper functions

- `_to_aware(dt)` -- converts to timezone-aware datetime
- `_bucket(match_date, now)` -- groups matches into TODAY/THIS WEEK/EARLIER based on elapsed time (24h/7d thresholds)

#### Class: `MatchHistoryScreen(QWidget)`

**Signal:** `match_selected(str)` -- demo_name

**ViewModel:** `MatchHistoryViewModel`

**Layout:**
- Title rail with count chip
- Source filter chips (All/Personal/Pro, mutually exclusive)
- Map filter chips (dynamic, top 8 maps by count)
- Pro-only banner (visible when no personal matches)
- Body stack: skeleton | empty | filter_empty | match_list (grouped by time buckets)

**Key methods:**
- `on_enter()` -- shows loading skeleton, kicks off `load_matches()`
- `_on_matches_loaded(matches)` -- refreshes source/map chip counts, renders filtered+grouped rows
- `_render_filtered()` -- applies source and map filters, groups by time bucket, creates `MatchRowCard` widgets with stagger animation
- `_rebuild_map_chips()` -- dynamically generates `FilterChip` widgets for maps in the current source scope
- `_on_source_chip(key)` / `_on_map_chip(key)` -- single-select filter handlers
- `_reset_filters()` -- clears both filter dimensions

### 5.5 Match Detail Screen

**File:** `apps/qt_app/screens/match_detail_screen.py`

#### Helper functions

- `_format_match_date(value)` -- formats datetime or string to `YYYY-MM-DD HH:MM`
- `_kd_sentiment(value)`, `_adr_sentiment(value)`, `_kast_sentiment(value)`, `_rating_sentiment(value)` -- return "positive"/"negative"/"neutral" based on thresholds

#### Class: `MatchDetailScreen(QWidget)`

Tabbed drill-down for one analyzed demo.

**ViewModel:** `MatchDetailViewModel`

**Layout:**
- Header rail: Back button, title (map name), subtitle (map + date), rating chip
- Empty/loading state (EmptyState widget)
- Tabs (pill-styled QTabWidget): Overview, Rounds, Economy, Highlights

**Key methods:**
- `load_demo(demo_name)` -- called externally; sets loading state, delegates to VM
- `_on_data(stats, rounds, insights, hltv)` -- populates all tabs:
  - Overview: HeroStatsStrip (Rating, K/D, ADR, KAST, Headshot), round outcome strip, HLTV 2.0 component breakdown with colored bars
  - Rounds: monospaced table with round number, W/L, side, kills, deaths, damage, equipment value, first-kill marker
  - Economy: `EconomyChart` widget
  - Highlights: coaching insights with severity-colored left borders, `MomentumChart`

### 5.6 Performance Screen

**File:** `apps/qt_app/screens/performance_screen.py`

#### Class: `PerformanceScreen(QWidget)`

Aggregate analytics dashboard.

**ViewModel:** `PerformanceViewModel`

**Layout:**
- Title rail with count chip
- Pro-overview banner (visible when no personal data)
- Body stack: skeleton | empty | scrollable content

**Sections (built dynamically from data):**
1. **Hero strip** -- HeroStatsStrip: avg rating, matches, K/D, ADR, KAST
2. **Context strip** (Cluster F) -- percentile rank vs pro cohort (Rating, K/D, ADR, KAST as Nth %)
3. **Rating trend** -- text-based trend summary: average, range, last N, trend direction (up/down/stable arrow + color)
4. **Per-map grid** -- 3-column grid of map tiles with rating (color-coded), K/D, ADR, match count
5. **Strengths/weaknesses** -- two-column display with sigma deviations from pro baseline
6. **Utility effectiveness** -- per-metric comparison vs pro (HE damage, molotov damage, smokes/round, flash blind time, flash assists, unused utility) with percentage delta arrows

### 5.7 Tactical Viewer Screen

**File:** `apps/qt_app/screens/tactical_viewer_screen.py`

2D demo replay viewer with:
- Map widget showing player positions on the radar image
- Player sidebar listing CT/T teams with per-player stats
- Timeline widget for scrubbing through ticks
- Playback controls (play/pause, speed, step)
- Demo selector dropdown

Uses `QtPlaybackEngine` for tick-based playback at ~60 FPS.

The screen checks `AppState.use_webengine_marquee` -- if True and the web dist exists, it loads a QWebEngineView with the React+D3 tactical viewer instead of the Qt-native widgets. Falls back silently if the dist is missing.

### 5.8 Settings Screen

**File:** `apps/qt_app/screens/settings_screen.py`

Application settings panel. Takes `theme_engine: ThemeEngine` as constructor parameter.

**Settings rows (Cards):**
- **Theme selector** -- CS2/CSGO/CS1.6 radio buttons; applies immediately via `theme_engine.apply_theme()`
- **Wallpaper picker** -- lists available wallpapers for the current theme
- **Font settings** -- family dropdown (Roboto, JetBrains Mono, New Hope, CS Regular, YUPIX) + size dropdown (Small/Medium/Large)
- **Language** -- English/Portuguese/Italian selector
- **Demo paths** -- personal and pro demo folder paths with file dialogs
- **Player identity** -- CS2 player name and SteamID64 fields
- **P3 toggles:**
  - Sounds enabled (ToggleSwitch)
  - Frameless window mode (ToggleSwitch, requires restart)
  - PyQtGraph heatmap preference (ToggleSwitch)
- **P4 toggle:**
  - WebEngine marquee mode (ToggleSwitch)
- **Advanced** -- database reset, cache clear

### 5.9 Help Screen

**File:** `apps/qt_app/screens/help_screen.py`

Two-panel help browser.

**Fallback topics (6 entries):** Getting Started, Demo Analysis, AI Coach, Steam Integration, Navigation, Troubleshooting.

**Layout:**
- Title + search input
- Left panel: `QListWidget` of topic titles (240px wide)
- Right panel: `QScrollArea` with topic content label

**Data source:** Tries to load from `backend/knowledge_base/help_system`. Falls back to `_FALLBACK_TOPICS` on import or runtime failure.

**Search:** Client-side filter by title or content substring.

### 5.10 Profile Screen

**File:** `apps/qt_app/screens/profile_screen.py`

Player profile display showing Steam identity configuration and aggregate stats. Contains links to Steam Config and FaceIT Config screens.

### 5.11 User Profile Screen

**File:** `apps/qt_app/screens/user_profile_screen.py`

Extended user profile view with editable player name, SteamID, and profile preferences. Persists changes via `save_user_setting()`.

### 5.12 Steam Config Screen

**File:** `apps/qt_app/screens/steam_config_screen.py`

Steam integration configuration:
- SteamID64 input
- Steam API Key input (password-masked)
- Link to Steam API key registration
- Save button with success feedback
- Keyring availability warning (falls back to plaintext if `keyring` package unavailable)

### 5.13 FaceIT Config Screen

**File:** `apps/qt_app/screens/faceit_config_screen.py`

#### Class: `FaceitConfigScreen(QWidget)`

**Layout:**
- Back button + title "FaceIT Competitive Stats"
- Keyring warning (if `keyring` package unavailable)
- API Key card: description, link to developers.faceit.com, password-masked input
- Save button with 3-second "Saved!" feedback

**Methods:**
- `on_enter()` -- pre-fills API key from saved config
- `_on_save()` -- persists API key via `save_user_setting("FACEIT_API_KEY", ...)`

### 5.14 Wizard Screen

**File:** `apps/qt_app/screens/wizard_screen.py`

First-run setup wizard. Uses a `Stepper` component for step progression.

**Signal:** `setup_completed` -- emitted when wizard finishes, wired to switch to home screen

**Steps:**
1. Welcome / introduction
2. Player name and SteamID configuration
3. Demo folder path selection
4. (Optional) Pro demo folder path
5. Completion confirmation

Persists `SETUP_COMPLETED = True` on finish.

### 5.15 Pro Comparison Screen

**File:** `apps/qt_app/screens/pro_comparison_screen.py`

Side-by-side comparison of the user's stats against pro player baselines.

**Signal:** `pro_detail_requested(int)` -- HLTV player ID, wired to ProPlayerDetailScreen

**ViewModel:** `ProComparisonViewModel`

**Layout:**
- Radar chart comparing user vs pro averages across multiple axes
- Per-player comparison cards with "Details" buttons

### 5.16 Pro Player Detail Screen

**File:** `apps/qt_app/screens/pro_player_detail_screen.py`

Drill-down into a single pro player's stats from HLTV.

**Signal:** `back_requested` -- wired to navigate back to pro_comparison

**ViewModel:** `ProPlayerDetailViewModel`

**Methods:**
- `load_pro(hltv_id: int)` -- fetches pro player data via ViewModel

---

## 6. ViewModels

All ViewModels follow the MVVM pattern. They are `QObject` subclasses that use `Worker`/`QThreadPool` for background data access and emit typed signals consumed by their corresponding screens. No ViewModel directly manipulates UI widgets.

### 6.1 Coach ViewModel

**File:** `apps/qt_app/viewmodels/coach_vm.py`

#### Class: `CoachViewModel(QObject)`

**Signal:** `insights_loaded(list)` -- list of insight dicts

**Method:** `load_insights()` -- background query via `Worker` that fetches recent coaching insights from the database (typically from `CoachingInsight` model). Emits results on the main thread.

### 6.2 Coaching Chat ViewModel

**File:** `apps/qt_app/viewmodels/coaching_chat_vm.py`

#### Class: `CoachingChatViewModel(QObject)`

Manages the interactive coaching chat session.

**Signals:**
- `messages_changed(list)` -- list of message dicts with `role` and `content`
- `is_loading_changed(bool)` -- typing indicator state
- `is_available_changed(bool)` -- whether the LLM coach is reachable

**Methods:**
- `check_availability()` -- probes the LLM service endpoint
- `check_and_start(player_name)` -- starts a new session with player context
- `send_message(text)` -- sends user message, triggers background LLM call, appends response
- `clear_session()` -- resets the conversation history

### 6.3 Focus Insight ViewModel

**File:** `apps/qt_app/viewmodels/focus_insight_vm.py`

#### Class: `FocusInsightViewModel(QObject)`

**Signal:** `insight_changed(dict)` -- payload with `area`, `body`, `navigate_to` keys

**Method:** `load()` -- background query that identifies the user's current "focus this week" area based on recent performance patterns.

### 6.4 Match Detail ViewModel

**File:** `apps/qt_app/viewmodels/match_detail_vm.py`

#### Class: `MatchDetailViewModel(QObject)`

**Signals:**
- `data_changed(dict, list, list, dict)` -- (stats, rounds, insights, hltv_components)
- `error_changed(str)` -- error message

**Method:** `load_detail(demo_name)` -- background query fetching:
- Player match stats (rating, K/D, ADR, KAST, HS%)
- Per-round data (round number, side, W/L, kills, deaths, damage, equipment value, opening kill)
- Coaching insights for the match
- HLTV 2.0 component breakdown

### 6.5 Match History ViewModel

**File:** `apps/qt_app/viewmodels/match_history_vm.py`

#### Class: `MatchHistoryViewModel(QObject)`

**Signals:**
- `matches_changed(list)` -- list of match dicts with demo_name, rating, match_date, is_pro, etc.
- `error_changed(str)` -- error message
- `is_loading_changed(bool)` -- loading state

**Methods:**
- `load_matches()` -- background query fetching all analyzed matches from `PlayerMatchStats`
- `cancel()` -- sets a cancellation flag (best-effort)

### 6.6 Performance ViewModel

**File:** `apps/qt_app/viewmodels/performance_vm.py`

#### Class: `PerformanceViewModel(QObject)`

**Signals:**
- `data_changed(list, dict, dict, dict, bool)` -- (history, map_stats, strengths_weaknesses, utility, is_pro_overview)
- `context_changed(dict)` -- Cluster F: percentile rank vs pro cohort
- `error_changed(str)` -- error message
- `is_loading_changed(bool)` -- loading state

**Method:** `load_performance()` -- background computation that:
1. Loads all user match stats (falls back to pro data if no personal matches)
2. Aggregates per-map statistics
3. Computes strengths/weaknesses vs pro baseline (z-score analysis)
4. Computes utility effectiveness metrics
5. Computes percentile rankings against the pro cohort

### 6.7 Pro Comparison ViewModel

**File:** `apps/qt_app/viewmodels/pro_comparison_vm.py`

#### Class: `ProComparisonViewModel(QObject)`

**Signal:** `comparison_loaded(list)` -- list of pro player comparison dicts

**Method:** `load_comparison()` -- background query fetching pro player stats from HLTV database for radar chart and comparison cards.

### 6.8 Pro Player Detail ViewModel

**File:** `apps/qt_app/viewmodels/pro_player_detail_vm.py`

#### Class: `ProPlayerDetailViewModel(QObject)`

**Signal:** `detail_loaded(dict)` -- pro player detail with stats, career history, etc.

**Method:** `load_detail(hltv_id: int)` -- background query for a single pro player's data.

### 6.9 Tactical ViewModel

**File:** `apps/qt_app/viewmodels/tactical_vm.py`

#### Class: `TacticalViewModel(QObject)`

Manages demo loading, frame iteration, and player selection for the tactical viewer.

**Signals:**
- Frame data, player lists, map name changes
- Playback state changes

**Methods:**
- `load_demo(demo_path_or_name)` -- loads parsed demo data
- `seek_to_tick(tick)` -- jumps to a specific tick
- `set_speed(multiplier)` -- adjusts playback speed
- `select_player(player_id)` -- highlights a player

### 6.10 User Profile ViewModel

**File:** `apps/qt_app/viewmodels/user_profile_vm.py`

#### Class: `UserProfileViewModel(QObject)`

**Signal:** `profile_loaded(dict)` -- user profile data including name, SteamID, stats summary

**Method:** `load_profile()` -- background query assembling user profile from config and database.

---

## 7. Widgets

### 7.1 Skeleton Loader

**File:** `apps/qt_app/widgets/skeleton.py`

#### Class: `SkeletonTable(QWidget)`

Generates a placeholder loading animation with `row_count` skeleton rows. Each row is a rounded `QFrame` with a pulsing opacity animation via `Animator.pulse()`. Used during data loading in MatchHistory, Performance, and other screens.

### 7.2 Toast Notifications

**File:** `apps/qt_app/widgets/toast.py`

#### Class: `ToastContainer(QWidget)`

Floating notification container anchored to the top-right of the content area.

**Methods:**
- `add_toast(severity, message)` -- creates a toast widget, slides it in from the right, auto-dismisses after a timeout
- `refit()` -- repositions the container when the parent resizes

#### Class: `Toast(QFrame)` (or similar internal widget)

Individual toast notification with:
- Severity-colored left border and background from design tokens
- Dismiss button
- Auto-hide timer (typically 5-8 seconds)
- Slide-out animation on dismiss

### 7.3 Charts

#### `charts/economy_chart.py` -- `EconomyChart(QWidget)`

QPainter-based chart showing equipment value per round. Draws a line graph with filled area, grid lines, and round number labels. Colors from design tokens.

#### `charts/mini_sparkline.py` -- `MiniSparkline(QWidget)`

Compact inline sparkline for embedding in cards. Renders a small line chart with optional fill, configurable color and size.

#### `charts/momentum_chart.py` -- `MomentumChart(QWidget)`

QPainter-based chart showing round-by-round momentum (cumulative round differential). Draws positive area in green, negative in red.

### 7.5 Design System Components

#### `components/card.py` -- `Card(QFrame)`

Base card component with:
- Title label (optional, with `caption` typography)
- Optional subtitle
- `content_layout` (QVBoxLayout) for child content
- Depth levels: `"raised"`, `"flat"`, `"overlay"`
- Styling from design tokens (background, border, radius)

**Methods:**
- `set_title(text)`, `set_subtitle(text)`
- `content_layout` property for adding child widgets

#### `components/empty_state.py` -- `EmptyState(QWidget)`

Centered empty-state placeholder with:
- Large icon text (emoji/symbol)
- Title label
- Description label
- Optional primary CTA button
- Optional secondary CTA button

**Signals:** `action_clicked`, `secondary_action_clicked`

**Methods:** `set_title(text)`, `set_description(text)`, `set_cta_text(text)`

#### `components/filter_chip.py` -- `FilterChip(QFrame)`

Toggle chip for filter bars. Shows label text and optional count badge.

**Signal:** `toggled(bool)`

**Methods:**
- `set_checked(checked)` -- sets visual state without emitting signal
- `set_count(count)` -- updates the count badge

#### `components/focus_insight.py` -- `FocusInsightCard(Card)`

Dashboard card for "Focus This Week" display. Shows the current focus area, body text, and "Open" button.

**Signal:** `open_clicked(str)` -- screen name to navigate to

**Methods:** `set_insight(area, body, navigate_to)`, `set_empty()`

#### `components/hero_stats_strip.py`

**Dataclass:** `HeroStat(value: str, label: str, sentiment: str)` -- where sentiment is "positive"/"negative"/"neutral"

**Class:** `HeroStatsStrip(QWidget)` -- horizontal row of stat blocks with large value numbers and caption labels. Values colored by sentiment.

#### `components/icon_widget.py` -- `IconWidget(QLabel)`

Wraps the `IconProvider` to display icons as QLabel pixmaps. Provides a unified interface regardless of whether SVG or QPainterPath provider is active.

#### `components/last_match_hero.py` -- `LastMatchHeroCard(Card)`

Dashboard hero card showing last match summary: map name, rating (color-coded), K/D, and a mini sparkline of recent ratings.

**Signals:** `analyze_clicked`, `detail_clicked(str)` (demo_name)

**Method:** `set_state(match_data, history_ratings)`

#### `components/match_mini_card.py` -- `MatchMiniCard(QFrame)`

Compact card for the dashboard recent matches strip. Shows map thumbnail/name, rating badge, and date. Fixed size for horizontal scrolling.

**Signal:** `clicked(str)` -- demo_name

#### `components/match_row_card.py` -- `MatchRowCard(QFrame)`

Full-width card for the match history list. Shows map name, date, rating, K/D, ADR in a horizontal layout. Hover effects from QSS.

**Signal:** `clicked(str)` -- demo_name

#### `components/nav_sidebar.py` -- `NavSidebar(QFrame)`

Collapsible navigation sidebar.

**Signal:** `nav_clicked(str)` -- screen name

**Nav items:** Home, Coach, Match History, Performance, Tactical Viewer, Settings, Help (defined as a list of dicts with icon method name, label, screen key)

**Methods:**
- `set_active(screen_name)` -- highlights the active nav item
- `retranslate()` -- updates labels from i18n

Each nav item is a `QPushButton` with an icon from `IconProvider` and a label.

#### `components/progress_ring.py` -- `ProgressRing(QWidget)`

Circular progress indicator. QPainter-drawn arc with configurable size, thickness, and value (0.0-1.0). Uses accent colors from design tokens.

**Method:** `set_value(value: float)` -- updates the displayed value

#### `components/section_header.py` -- `SectionHeader(QWidget)`

Section divider with a caption-styled label and optional right-side widget.

#### `components/stat_badge.py` -- `StatBadge(QFrame)`

Compact badge displaying a single stat value and label, with sentiment coloring.

#### `components/status_chip.py` -- `StatusChip(QFrame)`

Small status indicator chip with colored dot and text label.

**Severity levels:** `"online"` (green dot), `"offline"` (red dot), `"warning"` (yellow dot), `"neutral"` (gray dot)

**Methods:** `set_label(text)`, `set_severity(severity)`

#### `components/stepper.py` -- `Stepper(QWidget)`

Multi-step wizard stepper component. Shows numbered circles connected by lines, with the current step highlighted.

#### `components/toggle_switch.py` -- `ToggleSwitch(QWidget)`

iOS-style toggle switch with animated knob movement. QPainter-drawn with accent/surface colors from design tokens.

**Signal:** `toggled(bool)`

**Methods:** `isChecked() -> bool`, `setChecked(checked: bool)`

### 7.6 Tactical Widgets

#### `tactical/map_widget.py` -- `MapWidget(QWidget)`

2D radar map display. Renders player positions, utility throws, and event markers on top of a map image loaded from `PHOTO_GUI/maps/`.

**Features:**
- Pan and zoom (mouse wheel + drag)
- Player dots with team colors (CT blue, T yellow/orange)
- Name labels
- Ghost-AI overlay positions
- Coordinate system mapping (game coordinates to pixel coordinates)

#### `tactical/player_sidebar.py` -- `PlayerSidebar(QFrame)`

Sidebar showing player lists for both teams (CT and T). Each player row shows name, health, armor, weapon, and alive/dead state.

**Signal:** `player_selected(int)` -- player index/ID

#### `tactical/timeline_widget.py` -- `TimelineWidget(QWidget)`

Horizontal timeline scrubber for demo playback. Shows tick positions, round boundaries, and event markers (kills, plants, defuses).

**Signals:**
- `tick_changed(int)` -- user dragged the scrubber
- `round_selected(int)` -- user clicked a round marker

---

## 8. Legacy Kivy Frontend

> **Historical note:** The Kivy/KivyMD-based frontend (`apps/legacy_kivy/`) was the
> original UI layer, replaced by the Qt frontend in March 2026. The `legacy_kivy/`
> directory has been removed from the codebase. All active development targets the
> Qt frontend documented in sections 1–7 above.
---

## 9. Architecture and Design Decisions

### MVVM Pattern

The Qt app strictly follows Model-View-ViewModel:
- **Views** (screens, widgets) -- declarative layout, connect to VM signals, never access the database directly
- **ViewModels** -- `QObject` subclasses that encapsulate business logic, use `Worker`/`QThreadPool` for background I/O, emit typed signals
- **Models** -- existing backend storage layer (`PlayerMatchStats`, `CoachState`, etc.)

### Threading Model

All database and network access runs in `QThreadPool` via the `Worker` class. Signal/slot auto-marshaling ensures results arrive on the main thread. The legacy Kivy frontend used `Thread` + `Clock.schedule_once`; the Qt layer uses Signal/slot auto-marshaling instead.

### Theming Architecture

1. **Design tokens** (`design-tokens.json`) are the single source of truth
2. `tools/gen_design_tokens.py` generates `design_tokens.py` (frozen dataclasses)
3. `base.qss.template` uses `$token_name` variables
4. `qss_generator.py` renders the template with token values at runtime
5. `ThemeEngine` applies QSS + QPalette + font rules to QApplication

Three themes share the same QSS template; only the token values differ.

### Screen Lifecycle

Screens implement optional lifecycle hooks:
- `on_enter()` -- called when switching to this screen (connect signals, refresh data)
- `on_leave()` -- called when switching away (cleanup, cancel pending work)
- `retranslate()` -- called when the UI language changes

### Navigation

`MainWindow.switch_screen(name)` manages all navigation:
- Regular screens use `QStackedWidget` index switching
- Coach screen uses `QDockWidget` visibility toggle
- Keyboard shortcuts provide direct access to key screens

### Asset Management

- Map images: loaded from `PHOTO_GUI/maps/` with canonical map name normalization and a checkered QPainter fallback
- Icons: dual-provider system (SVG sprite preferred, QPainterPath fallback)
- Fonts: registered at startup from `PHOTO_GUI/` and `assets/fonts/`
- Wallpapers: per-theme selection from `cs2theme/`, `csgotheme/`, `cs16theme/`

### Phase Evolution

| Phase | Key Features |
|---|---|
| P1 | Basic Qt window, screen stack, wallpaper background |
| P2 | Real screens, navigation sidebar, theme engine |
| P3 | Frameless window, sounds, pyqtgraph heatmap toggles |
| P4 | WebEngine marquee, web bridge, tactical-grid motif |
| P7 | Frost/glass effects (design tokens defined, rendering TBD) |
