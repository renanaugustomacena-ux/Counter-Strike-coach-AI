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
| `coach_screen.py` | Coach | AI coach chat: dialogue with `CoachingDialogueEngine`, RAG-augmented responses, model picker. |
| `match_history_screen.py` | Match History | Filterable list of user matches with HLTV 2.0 ratings. |
| `match_detail_screen.py` | Match Detail | Per-match drilldown: rounds, economy, highlights, momentum. |
| `performance_screen.py` | Performance | Aggregate dashboard: rating trend, per-map stats, strengths / weaknesses, utility breakdown. |
| `pro_comparison_screen.py` | Pro Comparison | User vs. selected pro side-by-side stat comparison. |
| `pro_player_detail_screen.py` | Pro Player Detail | Pro player profile with HLTV stat card, recent matches, role classification. |
| `tactical_viewer_screen.py` | Tactical Viewer | 2D map replay with playback controls, ghost AI overlay, chronovisor highlights. |
| `profile_screen.py` | Profile | User profile editor (display name, role preference). |
| `user_profile_screen.py` | User Profile | Authenticated profile with Steam / FaceIT integration status. |
| `settings_screen.py` | Settings | Theme, language, paths, ingestion mode, model picker, telemetry toggle. |
| `steam_config_screen.py` | Steam Config | Steam ID / API key entry with validation. |
| `faceit_config_screen.py` | FaceIT Config | FaceIT API key entry with validation. |
| `wizard_screen.py` | First-Run Wizard | 4-step setup: intro → brain path → demo path → finish. |
| `help_screen.py` | Help | In-app help backed by `backend/knowledge_base/help_system.py`. |
| `placeholder.py` | (utility) | Stub `EmptyPlaceholderScreen` shown when a route is not yet implemented. |

## Architecture pattern

Each screen follows the same template:

```
class FooScreen(QWidget):
    def __init__(self, app_state, viewmodel: FooViewModel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._build_ui()             # widget composition
        self._wire_signals()         # bind self._vm.* signals to self._on_*
        self._apply_theme()          # subscribe to theme_engine.themeChanged

    def on_enter(self):              # called by the navigation router on focus
        self._vm.refresh()

    def on_leave(self):              # called when the user navigates away
        self._vm.cancel_loads()
```

ViewModels do all data loading; screens marshal results back into widgets. Background work uses `core/worker.QThread` so the UI thread stays responsive.

## Key invariants

- **`on_enter` / `on_leave` are mandatory.** The navigation router calls them; missing implementations leak threads or stale subscriptions.
- **Signals must be disconnected on `on_leave`.** Use `core/widgets_helpers.disconnect_all()` to avoid double-firing after re-entry.
- **No direct DB access from a screen.** All persistence goes through the ViewModel.
- **No hard-coded strings.** User-visible text routes through `core/i18n_bridge.QtLocalizationManager.get_text()`.

## Integration

```
qt_app/app.py (router)
    +-- HomeScreen        --> HomeViewModel        --> backend/services/*
    +-- CoachScreen       --> CoachViewModel       --> CoachingDialogueEngine + LLMService
    +-- MatchDetailScreen --> MatchDetailViewModel --> AnalyticsEngine + storage
    +-- PerformanceScreen --> PerformanceViewModel --> reporting/analytics.py
    +-- TacticalViewer    --> TacticalPlaybackVM   --> core/playback_engine + GhostEngine
    ... (one route per screen)
```

## Related

- ViewModels: `apps/qt_app/viewmodels/README.md`
- Custom widgets: `apps/qt_app/widgets/README.md`
- Application core: `apps/qt_app/core/README.md`
- Parent: `apps/qt_app/README.md`
