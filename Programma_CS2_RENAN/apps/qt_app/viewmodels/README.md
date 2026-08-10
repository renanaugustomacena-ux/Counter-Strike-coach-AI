# `apps/qt_app/viewmodels/` — MVVM ViewModels

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX), Rule 1 (Correctness)
> **Skill:** `/frontend-ux-review`, `/state-audit`

## Purpose

ViewModels in the Model-View-ViewModel (MVVM) pattern. Every screen has at least one ViewModel that owns:

1. **Data loading** from the backend (services, analytics, storage).
2. **Background work** (long-running queries, ML inference) via `core/worker.Worker` (a `QRunnable` on `QThreadPool`).
3. **State broadcast** to the screen via PySide6 `Signal`.
4. **Cancellation** semantics so the user never waits on stale work after navigation.

Screens stay thin and visual; ViewModels stay thick and headless. Tests for business logic happen at the ViewModel level — no Qt event loop required (we use Qt's `QSignalSpy` or plain mocks).

## File inventory

| File | ViewModel | Backed Screen | Responsibility |
|------|-----------|---------------|----------------|
| `__init__.py` | — | — | Package marker. |
| `coach_vm.py` | `CoachViewModel` | Coach | Loads the latest `CoachingInsight` rows for the active player (`insights_loaded` / `is_loading_changed` / `error_changed`). |
| `coaching_chat_vm.py` | `CoachingChatViewModel` | Coach (chat panel) | Multi-turn dialogue with `CoachingDialogueEngine`. Thread-safe message list. |
| `focus_insight_vm.py` | `FocusInsightViewModel` | Home (focus card) | Single-insight carousel for the home page focus card. |
| `match_detail_vm.py` | `MatchDetailViewModel` | Match Detail | Loads `PlayerMatchStats`, `RoundStats`, coaching insights, HLTV 2.0 breakdown. |
| `match_history_vm.py` | `MatchHistoryViewModel` | Match History | Filterable list of user matches. Cancellation on filter change. |
| `performance_vm.py` | `PerformanceViewModel` | Performance | Rating trend, per-map stats, strengths / weaknesses, utility breakdown. |
| `pro_comparison_vm.py` | `ProComparisonViewModel` | Pro Comparison | User-vs-pro stat comparison with role-aware baselines. |
| `pro_player_detail_vm.py` | `ProPlayerDetailViewModel` | Pro Player Detail | Pro player profile data, recent matches, percentile context. |
| `tactical_vm.py` | `TacticalPlaybackVM`, `TacticalGhostVM`, `TacticalChronovisorVM` | Tactical Viewer | Three coordinated VMs: playback, ghost AI overlay, chronovisor highlights. |
| `user_profile_vm.py` | `UserProfileViewModel` | User Profile | Loads and saves `PlayerProfile` fields (bio, role). |

## Conventions

### Threading

All I/O happens off the UI thread. ViewModels use `core/worker.Worker` on the global `QThreadPool`:

```python
def load_matches(self):
    self._cancel.clear()                  # threading.Event
    self.is_loading_changed.emit(True)
    worker = Worker(self._bg_load)
    worker.signals.result.connect(self._on_loaded)
    worker.signals.error.connect(self._on_error)
    QThreadPool.globalInstance().start(worker)

def cancel(self):
    self._cancel.set()
```

`cancel()` (called from the screen's `on_leave`) sets the `threading.Event` so the background load bails out cleanly without touching widgets that may have been destroyed.

### Signals

Public state is exposed via `Signal` (PySide6) — never mutable attributes. Screens subscribe; ViewModels emit:

```python
matches_changed = Signal(list)        # payload: list of match rows
error_changed = Signal(str)           # payload: human-readable reason
is_loading_changed = Signal(bool)     # payload: True while a fetch is in flight
```

### Singleton policy

ViewModels are **per-screen-instance**, not singletons. Each screen constructs its own ViewModel(s) when it is created at app startup (screens live in the `QStackedWidget` for the application's lifetime). Singletons would leak state across screens.

### No Qt widgets in this layer

Importing from `PySide6.QtWidgets` here is a code smell — ViewModels should be testable without an active QApplication. Imports limited to `PySide6.QtCore` (signals, QObject, QThreadPool).

## Common pitfalls

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Fetching synchronously in `__init__` | Blocks UI thread on screen entry | Defer to first `refresh()` call |
| Forgetting `cancel()` | Stale fetch finishes on a destroyed screen → segfault | Implement `cancel()` on every VM with workers |
| Sharing a single `DatabaseManager` session across threads | SQLite WAL contention | Use `get_db_manager().get_session()` per worker |
| Emitting signals from worker threads to non-thread-safe slots | Crash on cross-thread call | Use queued connections (Qt's default for `Signal` across threads) |

## Integration

```
Screen (apps/qt_app/screens/*)
    +-- ViewModel (this package)
            +-- backend/services/*           (business logic)
            +-- backend/reporting/analytics  (dashboard math)
            +-- backend/storage/database     (persistence singletons)
            +-- core/worker.Worker           (background execution)
```

## Related

- Screens: `apps/qt_app/screens/README.md`
- Worker / threading: `apps/qt_app/core/worker.py`
- Backend services: `Programma_CS2_RENAN/backend/services/README.md`
- Parent app: `apps/qt_app/README.md`
