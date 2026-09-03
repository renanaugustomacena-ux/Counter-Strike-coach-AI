# `apps/qt_app/screens/` — Qt UI screen modules

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

This package contains every top-level screen in the Qt frontend. Each module defines a `QWidget` subclass that owns the layout, signal wiring, and per-screen lifecycle hooks for one route in the application's navigation graph. ViewModels (in `apps/qt_app/viewmodels/`) own the data and business logic; screens own the visual composition.

## File inventory

| File | Screen | Purpose |
|------|--------|---------|
| `__init__.py` | — | Package marker. |
| `home_screen.py` | Home | Landing page: last match + weekly focus hero pair, recent matches strip, demo analysis / pro ingestion launchers, navigation hub. |
| `coach_screen.py` | Coach | RAP Coach dashboard: belief-state confidence ring, recent insight rows, plus an embedded `ChatPanel` dock (toggled by the Chat button) backed by `CoachingDialogueEngine` (via `CoachingChatViewModel`). |
| `match_history_screen.py` | Match History | Grouped (Today / This Week / Earlier) list of analyzed demos with source (All / Personal / Pro) and map filters; per-match rating vs. the personal baseline. |
| `match_detail_screen.py` | Match Detail | Tabbed per-match drilldown: overview, rounds, economy, highlights (momentum + coaching insights). |
| `performance_screen.py` | Performance | Aggregate dashboard: rating trend, per-map stats, strengths / weaknesses, utility breakdown. |
| `pro_comparison_screen.py` | Pro Comparison | Pro vs Pro or Me vs Pro comparison: skill radar + head-to-head metrics; Me vs Pro is gated until enough personal matches are analyzed. |
| `pro_player_detail_screen.py` | Pro Player Detail | Pro player profile with HLTV stat card, recent matches, role classification. |
| `tactical_viewer_screen.py` | Tactical Viewer | 2D map replay with playback controls, ghost AI overlay, chronovisor highlights. |
| `profile_screen.py` | Profile | In-game player name editor; persists `CS2_PLAYER_NAME` and ensures the `PlayerProfile` DB row via a background `Worker`. |
| `user_profile_screen.py` | User Profile | User profile display and editing (bio, role) via `UserProfileViewModel`. |
| `settings_screen.py` | Settings | Tabbed (Appearance · Paths & Data · General): theme, font, language, data paths, ingestion mode, UI toggles. |
| `steam_config_screen.py` | Steam Config | SteamID64 / API key entry with validation. |
| `faceit_config_screen.py` | FaceIT Config | FaceIT API key entry. |
| `wizard_screen.py` | First-Run Wizard | 5-step setup: intro → name → brain path → demo path → launch. |
| `help_screen.py` | Help | In-app help backed by `backend/knowledge_base/help_system.py` (topics from `Programma_CS2_RENAN/data/docs/*.md`). |
| `placeholder.py` | (utility) | Legacy stub `PlaceholderScreen` (centered title); no longer registered — every route has a real screen. |

## Architecture pattern

Each screen follows the same template:

```
class FooScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = FooViewModel(self)   # screen owns its ViewModel
        self._build_ui()                # widget composition
        self._vm.data_changed.connect(self._on_data)   # signal wiring

    def on_enter(self):                 # called by MainWindow.switch_screen()
        self._vm.load()

    def on_leave(self):                 # optional — implemented where needed
        self._vm.cancel()
```

ViewModels do all data loading; screens marshal results back into widgets. Background work uses `core/worker.Worker` (a `QRunnable` on `QThreadPool`) so the UI thread stays responsive.

## Key invariants

- **`on_enter()` is called by `MainWindow.switch_screen()`** when a screen becomes visible — use it to refresh data.
- **Implement `on_leave()` when the screen holds in-flight work** (coach, match history, performance, and tactical viewer do) and cancel pending ViewModel loads there.
- **No DB access on the GUI thread.** Screens with a ViewModel persist through it; the few direct DB touches (`PlayerProfile` upsert in profile / wizard, match-id lookup in the tactical viewer) ride a `Worker` off-thread (F-0038).
- **No hard-coded strings.** User-visible text routes through `core/i18n_bridge.QtLocalizationManager.get_text()`.

## Integration

```
qt_app/app.py (screen registry) --> MainWindow.switch_screen() (router)
    +-- HomeScreen        --> MatchHistoryViewModel + FocusInsightViewModel
    +-- CoachScreen       --> CoachViewModel + CoachingChatViewModel --> CoachingDialogueEngine
    +-- MatchDetailScreen --> MatchDetailViewModel --> backend storage
    +-- PerformanceScreen --> PerformanceViewModel
    +-- TacticalViewer    --> TacticalPlaybackVM / TacticalGhostVM / TacticalChronovisorVM
                              --> core/playback_engine + GhostEngine
    ... (one route per screen)
```

## Related

- ViewModels: `apps/qt_app/viewmodels/README.md`
- Custom widgets: `apps/qt_app/widgets/README.md`
- Application core: `apps/qt_app/core/README.md`
- Parent: `apps/qt_app/README.md`
