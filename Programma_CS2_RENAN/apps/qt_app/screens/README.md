# `apps/qt_app/screens/` — Qt UI screen modules

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

This package contains every top-level screen in the Qt frontend. Each module defines a `QWidget` (or `QStackedWidget`) subclass that owns the layout, signal wiring, and per-screen lifecycle hooks for one route in the application's navigation graph. ViewModels (in `apps/qt_app/viewmodels/`) own the data and business logic; screens own the visual composition.

## File inventory

| File | Screen | Purpose |
|------|--------|---------|
| `__init__.py` | — | Package marker. |
| `home_screen.py` | Home | Landing page: last match summary, focus insight, navigation hub. |
| `coach_screen.py` | Coach | AI coach surface: insight cards plus a collapsible chat composer backed by `CoachingDialogueEngine` (via `CoachingChatViewModel`). |
| `match_history_screen.py` | Match History | Filterable list of user matches with HLTV 2.0 ratings. |
| `match_detail_screen.py` | Match Detail | Per-match drilldown: rounds, economy, highlights, momentum. |
| `performance_screen.py` | Performance | Aggregate dashboard: rating trend, per-map stats, strengths / weaknesses, utility breakdown. |
| `pro_comparison_screen.py` | Pro Comparison | User vs. selected pro side-by-side stat comparison. |
| `pro_player_detail_screen.py` | Pro Player Detail | Pro player profile with HLTV stat card, recent matches, role classification. |
| `tactical_viewer_screen.py` | Tactical Viewer | 2D map replay with playback controls, ghost AI overlay, chronovisor highlights. |
| `profile_screen.py` | Profile | User profile editor (display name, role preference). |
| `user_profile_screen.py` | User Profile | User profile display and editing (bio, role) via `UserProfileViewModel`. |
| `settings_screen.py` | Settings | Theme, font, language, data paths, ingestion mode, UI toggles. |
| `steam_config_screen.py` | Steam Config | Steam ID / API key entry with validation. |
| `faceit_config_screen.py` | FaceIT Config | FaceIT API key entry with validation. |
| `wizard_screen.py` | First-Run Wizard | 5-step setup: intro → player name → brain path → demo path → finish. |
| `help_screen.py` | Help | In-app help backed by `backend/knowledge_base/help_system.py`. |
| `placeholder.py` | (utility) | Stub `EmptyPlaceholderScreen` shown when a route is not yet implemented. |

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
- **No direct DB access from a screen.** All persistence goes through the ViewModel.
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
