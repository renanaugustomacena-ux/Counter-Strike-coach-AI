# Desktop Application (Legacy Kivy/KivyMD)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Note:** This is the legacy Kivy/KivyMD frontend. It is still functional and maintained as a fallback. The primary frontend is PySide6/Qt -- see [qt_app/](../qt_app/).

Kivy/KivyMD desktop application implementing MVVM architecture for CS2 tactical analysis and AI coaching.

## Architecture

**Pattern:** Model-View-ViewModel (MVVM)
- **Views:** Screen classes and widgets (layout.kv definitions)
- **ViewModels:** Business logic orchestrators (tactical_viewmodels.py, coaching_chat_vm.py)
- **Models:** Backend data layer (database.py, db_models.py)

## Screens (6)

1. **WizardScreen** (`wizard_screen.py`) — First-time setup wizard for Steam integration and folder configuration
2. **TacticalViewerScreen** (`tactical_viewer_screen.py`) — 2D map replay with pixel-accurate rendering and timeline scrubbing
3. **MatchHistoryScreen** (`match_history_screen.py`) — Match listing with color-coded HLTV 2.0 ratings
4. **MatchDetailScreen** (`match_detail_screen.py`) — 4-section analysis:
   - Overview + HLTV 2.0 stats
   - Per-round breakdown
   - Economy timeline
   - Highlights + Momentum graph
5. **PerformanceScreen** (`performance_screen.py`) — 4-panel performance analytics:
   - Rating trend sparkline
   - Per-map statistics cards
   - Strengths/weaknesses vs professional baseline (Z-score)
   - Utility usage panel (6 metrics)
6. **HelpScreen** (`help_screen.py`) — User documentation and guides

**Additional Screens (in main.py):**
- HomeScreen, CoachScreen, UserProfileScreen, SettingsScreen, ProfileScreen, SteamConfigScreen, FaceitConfigScreen

## Custom Widgets

**`widgets.py`** — 7 custom widgets:
- `MatplotlibWidget` — Embedded matplotlib canvas for general charts
- `TrendGraphWidget` — Time-series trend visualization
- `RadarChartWidget` — Multi-dimensional performance radar
- `EconomyGraphWidget` — Round-by-round economy timeline
- `MomentumGraphWidget` — Team momentum evolution
- `RatingSparklineWidget` — Compact rating history sparkline
- `UtilityBarWidget` — Utility usage comparison bars (user vs pro baseline)

**`tactical_map.py`** — `TacticalMap` widget with pixel-accurate 2D rendering from spatial_data.py coordinates

**`player_sidebar.py`** — `LivePlayerCard`, `PlayerSidebar` for real-time player state display

**`timeline.py`** — `TimelineScrubber` for demo playback navigation

**`ghost_pixel.py`** — `GhostPixelValidator` for tactical viewer debugging and coordinate verification

## ViewModels (MVVM)

**`tactical_viewmodels.py`** — 3 ViewModels for Tactical Viewer:
- `TacticalPlaybackViewModel` — Playback control and timeline management
- `TacticalGhostViewModel` — Ghost player rendering for comparison mode
- `TacticalChronovisorViewModel` — Critical moment detection and visualization (chronovisor integration)

**`coaching_chat_vm.py`** — `CoachingChatViewModel` for AI coaching dialogue management

## Layout Definitions

**`layout.kv`** (56 KB) — KivyMD layout definitions for all screens with Material Design components
