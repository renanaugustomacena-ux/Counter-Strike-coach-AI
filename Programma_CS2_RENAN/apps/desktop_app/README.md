# Desktop Application (Legacy Kivy/KivyMD)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Authority:** Desktop UI / Kivy frontend
> **Skill level:** Intermediate -- requires familiarity with Kivy widget lifecycle, KivyMD Material components, and the MVVM pattern.

> **Note:** This is the **legacy** Kivy/KivyMD frontend. It is still functional and maintained as a fallback. The primary frontend is PySide6/Qt -- see [`qt_app/`](../qt_app/).

---

## Overview

Kivy/KivyMD desktop application implementing the **Model-View-ViewModel (MVVM)** architecture for CS2 tactical analysis and AI coaching. The module provides 6 dedicated screens (defined in this directory) plus 7 additional screens defined in the main application entry point. All visual layout is declared in a single `layout.kv` file (~60 KB, 1621 lines) using the KivyMD Material Design component library.

The application renders match replays on a pixel-accurate 2D tactical map, displays real-time player state in sidebars, graphs economy and momentum data via embedded Matplotlib charts, and provides an AI coaching chat interface backed by the COPER coaching engine.

---

## File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package marker (empty). |
| `wizard_screen.py` | 418 | First-time setup wizard -- Steam path, brain data root, demo folder. |
| `tactical_viewer_screen.py` | 295 | 2D map replay with playback controls, ghost AI, chronovisor navigation. |
| `match_history_screen.py` | 162 | Scrollable match list with color-coded HLTV 2.0 ratings. |
| `match_detail_screen.py` | 454 | Single-match drill-down: overview, rounds, economy chart, highlights. |
| `performance_screen.py` | 331 | Aggregate dashboard: rating trend, per-map stats, strengths/weaknesses, utility. |
| `help_screen.py` | 80 | Searchable help center backed by optional `help_system` module. |
| `widgets.py` | 275 | 7 Matplotlib-based chart widgets (trend, radar, economy, momentum, sparkline, utility, base). |
| `tactical_map.py` | 607 | The "Living Map" widget -- GPU-optimized InstructionGroup rendering of players, nades, heatmaps. |
| `player_sidebar.py` | 362 | LivePlayerCard + PlayerSidebar with widget pooling for real-time player state. |
| `timeline.py` | 129 | Interactive TimelineScrubber with event markers (kills, plants, defuses). |
| `ghost_pixel.py` | 140 | GhostPixelValidator debug overlay for coordinate calibration. |
| `tactical_viewmodels.py` | 345 | 3 ViewModels: TacticalPlaybackViewModel, TacticalGhostViewModel, TacticalChronovisorViewModel. |
| `coaching_chat_vm.py` | 140 | CoachingChatViewModel -- AI dialogue session management with thread safety. |
| `data_viewmodels.py` | 316 | 3 ViewModels: MatchHistoryViewModel, MatchDetailViewModel, PerformanceViewModel. |
| `theme.py` | 74 | Shared color constants, palette registry (CS2/CSGO/CS1.6), rating helpers. |
| `layout.kv` | 1621 | KivyMD layout definitions for all screens (~60 KB). Material Design components. |

**Total: 16 Python files + 1 KV layout file.**

---

## Screens (6 in this directory)

### 1. WizardScreen (`wizard_screen.py`)
First-time setup wizard with a 4-step flow: `intro` -> `brain_path` -> `demo_path` -> `finish`. Uses `MDFileManager` for folder selection with Windows multi-drive support. Validates paths, creates the `knowledge/`, `models/`, `datasets/` subdirectory structure under `BRAIN_DATA_ROOT`, and persists settings via `save_user_setting()`. Includes path traversal normalization (WZ-01) and permission-denied fallback logic.

### 2. TacticalViewerScreen (`tactical_viewer_screen.py`)
Central replay screen coordinating three ViewModels. Loads parsed demo data into `PlaybackEngine`, renders frames on `TacticalMap`, and updates `PlayerSidebar` widgets per team. Supports play/pause, variable speed, tick seeking, round segment jumping, ghost AI overlay, and chronovisor critical moment navigation. The tick UI timer runs only while the screen is active (started on `on_enter`, cancelled on `on_leave`).

### 3. MatchHistoryScreen (`match_history_screen.py`)
Displays the user's match list ordered by date. Each match card shows the HLTV 2.0 rating with color coding and accessibility text labels (P4-07), map name extracted via regex, K/D ratio, ADR, kills, and deaths. Tapping a card navigates to `MatchDetailScreen`. Data loading is delegated to `MatchHistoryViewModel`.

### 4. MatchDetailScreen (`match_detail_screen.py`)
4-section drill-down for a single match:
- **Overview:** HLTV 2.0 rating with component breakdown bars (KPR, DPR, impact, etc.)
- **Round Timeline:** Per-round stats with side color (CT blue / T gold), win/loss, K/D, damage, economy, opening kills
- **Economy:** `EconomyGraphWidget` bar chart of equipment value per round
- **Highlights & Momentum:** Coaching insights with severity icons + `MomentumGraphWidget` cumulative K-D delta

### 5. PerformanceScreen (`performance_screen.py`)
4-panel aggregate dashboard:
- **Rating Trend:** `RatingSparklineWidget` with reference lines at 1.0, 1.1, 0.9
- **Per-Map Stats:** Horizontal scroll of map cards showing rating, ADR, K/D, match count
- **Strengths/Weaknesses:** Z-score comparison against professional baseline (green/red columns)
- **Utility Effectiveness:** `UtilityBarWidget` grouped horizontal bars (user vs pro average)

### 6. HelpScreen (`help_screen.py`)
Sidebar topic list with content panel. Uses optional `help_system` module (graceful degradation via try/except). Supports topic search filtering. Loads the first topic by default on entry.

### Additional Screens (defined in `main.py`)
HomeScreen, CoachScreen, UserProfileScreen, SettingsScreen, ProfileScreen, SteamConfigScreen, FaceitConfigScreen.

---

## Custom Widgets

### Chart Widgets (`widgets.py`)

All chart widgets extend `MatplotlibWidget`, which renders Matplotlib figures to Kivy textures via an in-memory PNG buffer. Figures are closed immediately after rendering (WG-01) to prevent memory leaks.

| Widget | Type | Description |
|--------|------|-------------|
| `MatplotlibWidget` | Base | Buffer-to-texture conversion with `BytesIO` context manager (WG-02). |
| `TrendGraphWidget` | Line | Dual-axis chart: Rating (left, cyan) and ADR (right, amber). Last 20 matches. |
| `RadarChartWidget` | Polar | Spider/radar chart for skill attributes. Requires minimum 3 data points (F7-36). |
| `EconomyGraphWidget` | Bar | Per-round equipment value. CT bars in blue (#5C9EE8), T bars in gold (#E8C95C). |
| `MomentumGraphWidget` | Line+Fill | Cumulative kill-death delta. Green fill above zero, red fill below. |
| `RatingSparklineWidget` | Line+Fill | Rating progression with reference lines at 1.0 (neutral), 1.1 (good), 0.9 (bad). |
| `UtilityBarWidget` | H-Bar | Grouped horizontal bars comparing user utility stats vs professional average. |

### Tactical Widgets

| Widget | File | Description |
|--------|------|-------------|
| `TacticalMap` | `tactical_map.py` | GPU-optimized 2D map with 3 InstructionGroup layers (static map, heatmap, dynamic players/nades). Supports async map loading, LRU name texture cache (64 entries), grenade trajectory rendering with 3D height visualization, detonation radius overlays (HE/Molotov/Smoke/Flash), player FoV cones, selection highlight, and click-to-select with enlarged hitboxes. |
| `LivePlayerCard` | `player_sidebar.py` | Real-time stat card: HP/armor progress bars, economy, KDA, weapon. Death state dims opacity. |
| `PlayerSidebar` | `player_sidebar.py` | Scrollable player list with widget pooling (object reuse instead of create/destroy per frame). Includes `LivePlayerCard` for selected player detail. |
| `TimelineScrubber` | `timeline.py` | Interactive progress bar with color-coded event markers. Kill markers at half height (red), bomb plant (yellow) and defuse (blue) at full height. Supports click and drag seeking. |
| `GhostPixelValidator` | `ghost_pixel.py` | Debug overlay showing normalized and world coordinates at touch position. Renders landmark reference points and a magenta crosshair. Active only when `debug_mode=True`. |

---

## MVVM Architecture

### ViewModels

The application follows the **Model-View-ViewModel** pattern. Views (Screen classes + `layout.kv`) handle rendering and user interaction. ViewModels own business logic and data loading. All ViewModels extend Kivy's `EventDispatcher` with observable properties, use daemon threads for I/O, and marshal results back to the UI thread via `Clock.schedule_once`.

| ViewModel | File | Responsibility |
|-----------|------|----------------|
| `TacticalPlaybackViewModel` | `tactical_viewmodels.py` | Play/pause, speed, seeking, tick tracking via `PlaybackEngine`. |
| `TacticalGhostViewModel` | `tactical_viewmodels.py` | Lazy-loaded `GhostEngine` for AI position predictions. |
| `TacticalChronovisorViewModel` | `tactical_viewmodels.py` | Background scanning for critical moments, next/prev navigation with tick buffer. |
| `CoachingChatViewModel` | `coaching_chat_vm.py` | AI dialogue session: availability check, session start, message send/receive. Thread-safe message list (F7-24). |
| `MatchHistoryViewModel` | `data_viewmodels.py` | Background loading of match list from `PlayerMatchStats` table. Cancellation support (DV-01). |
| `MatchDetailViewModel` | `data_viewmodels.py` | Background loading of match stats, rounds, coaching insights, HLTV 2.0 breakdown. |
| `PerformanceViewModel` | `data_viewmodels.py` | Background loading of rating history, per-map stats, strengths/weaknesses, utility data. |

---

## Entry Point

This module is **not** self-contained. The application entry point is `main.py` at the project root, which:
1. Creates the `MDApp` subclass
2. Loads `layout.kv` via `Builder.load_file()`
3. Registers all screens with the `ScreenManager`
4. Starts the Kivy event loop

Screens in this directory are imported by `main.py` and registered via the `@registry.register()` decorator.

---

## Layout File (`layout.kv`)

The `layout.kv` file (1621 lines, ~60 KB) defines the declarative UI for all screens using KivyMD's Material Design components. It includes:

- Screen layouts with `MDNavigationLayout`, `MDTopAppBar`, `MDNavigationDrawer`
- Widget trees for each screen with `id` references used by Python code
- Style rules for cards, labels, buttons, and custom widgets
- Responsive sizing with `dp()` and `sp()` units
- Theme bindings for the palette registry in `theme.py`

All `self.ids.<widget_id>` references in Python code correspond to `id: <widget_id>` declarations in this file.

---

## Theme System (`theme.py`)

Provides a shared color palette with three selectable themes:

| Theme | Surface Color | Accent | Chart Background |
|-------|--------------|--------|-----------------|
| **CS2** (default) | Dark purple-black | Orange | `#1a1a1a` |
| **CSGO** | Dark gray | Blue-gray | `#1c1e20` |
| **CS1.6** | Dark green | Green | `#181e18` |

Rating color coding follows standard HLTV thresholds: green (>1.10), yellow (0.90-1.10), red (<0.90). Text labels ("Excellent", "Good", "Average", "Below Avg") provide WCAG 1.4.1 color-blind accessibility (P4-07).

---

## Development Notes

### Legacy Status
This frontend is the **original** UI built during initial development. It remains functional and is maintained as a fallback, but **all new feature development targets the PySide6/Qt frontend** in `qt_app/`. Bug fixes and critical patches are still applied here.

### Key Design Decisions
- **InstructionGroup layers** in `TacticalMap` avoid re-uploading the map texture to the GPU every frame. Static layers redraw only on resize or map change.
- **Widget pooling** in `PlayerSidebar` reuses `MDListItem` widgets instead of creating/destroying them each frame, reducing GC pressure.
- **Lazy imports** for heavy dependencies (`torch`, `GhostEngine`, `ChronovisorScanner`) prevent startup freezes.
- **Thread safety** enforced via `threading.Lock` on shared message lists and `threading.Event` for cancellation.

### Known Limitations
- `HelpScreen` depends on an optional `help_system` module that may not be implemented yet (F7-09)
- `GhostEngine` requires a trained model checkpoint to function
- Matplotlib charts are rendered as static PNG textures (no interactivity)
- The `layout.kv` file is large and monolithic; splitting it is a future refactoring target
