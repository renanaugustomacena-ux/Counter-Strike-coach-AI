# `apps/qt_app/viewmodels/` — MVVM ViewModels

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX), Rule 1 (Correctness)
> **Skill:** `/frontend-ux-review`, `/state-audit`

## Purpose

ViewModels in the Model-View-ViewModel (MVVM) pattern. Every screen has at least one ViewModel that owns:

1. **Data loading** from the backend (services, analytics, storage).
2. **Background work** (long-running queries, ML inference) via `core/worker.QThread`.
3. **State broadcast** to the screen via `pyqtSignal` / `Signal`.
4. **Cancellation** semantics so the user never waits on stale work after navigation.

Screens stay thin and visual; ViewModels stay thick and headless. Tests for business logic happen at the ViewModel level — no Qt event loop required (we use Qt's `QSignalSpy` or plain mocks).

## File inventory

| File | ViewModel | Backed Screen | Responsibility |
|------|-----------|---------------|----------------|
| `__init__.py` | — | — | Package marker. |
| `coach_vm.py` | `CoachViewModel` | Coach | Coach screen state — model picker, available LLMs (`Ollama /api/tags`), session lifecycle. |
| `coaching_chat_vm.py` | `CoachingChatViewModel` | Coach (chat panel) | Multi-turn dialogue with `CoachingDialogueEngine`. Thread-safe message list. |
| `focus_insight_vm.py` | `FocusInsightViewModel` | Home (focus card) | Single-insight carousel for the home page focus card. |
| `match_detail_vm.py` | `MatchDetailViewModel` | Match Detail | Loads `PlayerMatchStats`, `RoundStats`, coaching insights, HLTV 2.0 breakdown. |
| `match_history_vm.py` | `MatchHistoryViewModel` | Match History | Filterable list of user matches. Cancellation on filter change. |
| `performance_vm.py` | `PerformanceViewModel` | Performance | Rating trend, per-map stats, strengths / weaknesses, utility breakdown. |
| `pro_comparison_vm.py` | `ProComparisonViewModel` | Pro Comparison | User-vs-pro stat comparison with role-aware baselines. |
| `pro_player_detail_vm.py` | `ProPlayerDetailViewModel` | Pro Player Detail | Pro player profile data, recent matches, percentile context. |
| `tactical_vm.py` | `TacticalPlaybackViewModel`, `TacticalGhostViewModel`, `TacticalChronovisorViewModel` | Tactical Viewer | Three coordinated VMs: playback, ghost AI overlay, chronovisor highlights. |
| `user_profile_vm.py` | `UserProfileViewModel` | User Profile | Steam / FaceIT sync state, profile fields. |

## Conventions

### Threading

All I/O happens off the UI thread. ViewModels use `core/worker.QThread`:

```python
def refresh(self):
    self._cancel_token = CancelToken()
    self._worker = run_in_thread(
        self._fetch_match_history,
        cancel_token=self._cancel_token,
    )
    self._worker.finished.connect(self._on_loaded)
    self._worker.failed.connect(self._on_load_failed)
```

`cancel_loads()` (called from the screen's `on_leave`) flips the cancel token so the worker bails out cleanly without touching widgets that may have been destroyed.

### Signals

Public state is exposed via `Signal` (PySide6) — never mutable attributes. Screens subscribe; ViewModels emit:

```python
matches_loaded = Signal(list)         # payload: List[MatchSummary]
load_failed = Signal(str)             # payload: human-readable reason
loading_changed = Signal(bool)        # payload: True while a fetch is in flight
```

### Singleton policy

ViewModels are **per-screen-instance**, not singletons. The router constructs a fresh ViewModel each time a screen is instantiated. Singletons would leak state across navigations.

### No Qt widgets in this layer

Importing from `PySide6.QtWidgets` here is a code smell — ViewModels should be testable without an active QApplication. Imports limited to `PySide6.QtCore` (signals, QObject, QThread).

## Common pitfalls

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Fetching synchronously in `__init__` | Blocks UI thread on screen entry | Defer to first `refresh()` call |
| Forgetting `cancel_loads()` | Stale fetch finishes on a destroyed screen → segfault | Implement `cancel_loads()` on every VM with workers |
| Sharing a single `DatabaseManager` session across threads | SQLite WAL contention | Use `get_db_manager().get_session()` per worker |
| Emitting signals from worker threads to non-thread-safe slots | Crash on cross-thread call | Use queued connections (Qt's default for `Signal` across threads) |

## Integration

```
Screen (apps/qt_app/screens/*)
    +-- ViewModel (this package)
            +-- backend/services/*           (business logic)
            +-- backend/reporting/analytics  (dashboard math)
            +-- backend/storage/database     (persistence singletons)
            +-- core/worker.QThread          (background execution)
```

## Related

- Screens: `apps/qt_app/screens/README.md`
- Worker / threading: `apps/qt_app/core/worker.py`
- Backend services: `Programma_CS2_RENAN/backend/services/README.md`
- Parent app: `apps/qt_app/README.md`
