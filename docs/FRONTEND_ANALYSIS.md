# Macena CS2 Analyzer — Frontend Analysis

> **Date:** 2026-03-30
> **Audience:** Engineers working on the Qt/PySide6 frontend
> **Rule:** Every claim verified against code. Every issue has evidence.

---

## 1. Boot Chain (Exact Execution Order)

When the user runs `./launch.sh`:

```
launch.sh
  → Activates venv Python 3.10
  → Clears stale __pycache__
  → python -m Programma_CS2_RENAN.apps.qt_app.app

app.py:main()
  1. QApplication created (high-DPI, version from package metadata)
  2. Splash screen shown (gradient, CS2 branding)
  3. Shutdown handler registered (app.aboutToQuit → stop polling + shutdown console)
  4. ThemeEngine created, fonts registered, theme applied
  5. MainWindow created (sidebar + QStackedWidget + toast container)
  6. Placeholder screens created
  7. 13 real screens instantiated and registered
  8. Wizard ↔ Home first-run gate checked (SETUP_COMPLETED setting)
  9. get_console().boot() — BACKEND BOOT (see below)
  10. Window shown, splash closed
  11. AppState.start_polling() — 10-second DB polling loop starts
  12. Qt event loop (app.exec())
```

### Backend Boot (`console.py:boot()`)

```
Console.__new__() → singleton creation under lock
Console._do_init() → ServiceSupervisor, DatabaseGovernor, IngestionManager, MLController
Console.boot():
  1. Set correlation ID
  2. init_database() → create_db_and_tables() + _add_missing_columns()
  3. Hunter service start (if ENABLE_HLTV_SYNC and Docker available)
  4. _audit_databases() → verify monolith + HLTV integrity
  5. configure_retention() → purge old log files
  6. Compute belief confidence from match count → persist to CoachState
  7. Status: "Running"
```

**Critical:** `init_database()` is called during boot. This triggers schema reconciliation
(`_add_missing_columns()`) which adds any columns present in the ORM models but missing
from the database. Without this, old databases cause `no such column` errors.

---

## 2. Database Configuration

| Database | URL | File |
|----------|-----|------|
| Monolith | `sqlite:///{CORE_DB_DIR}/database.db` | `Programma_CS2_RENAN/backend/storage/database.db` |
| HLTV | `sqlite:///{CORE_DB_DIR}/hltv_metadata.db` | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` |
| Per-match | `match_data/match_{id}.db` | Symlinked to SSD |

`CORE_DB_DIR` = `{BASE_DIR}/backend/storage` (always in project folder).

### Singleton Access Pattern

```python
get_db_manager()        # Monolith — lazy singleton, double-checked locking
get_hltv_db_manager()   # HLTV — lazy singleton
get_match_data_manager() # Per-match — lazy singleton with LRU engine cache
```

### WAL Mode Enforcement

All three databases enforce WAL mode via SQLAlchemy `@event.listens_for(engine, "connect")`.

---

## 3. AppState Polling (DB → UI Bridge)

`AppState` is a singleton QObject that polls `CoachState` (row id=1) every 10 seconds.

```
QTimer(10s) → Worker thread → _bg_read() → DB session → CoachState row
  → _apply() on main thread → emit typed signals only on value change
```

### Signals Emitted

| Signal | Type | Source Field | Consumer |
|--------|------|-------------|----------|
| `service_active_changed` | `bool` | heartbeat staleness < 300s | HomeScreen status dot |
| `coach_status_changed` | `str` | `ingest_status` | HomeScreen coach label |
| `parsing_progress_changed` | `float` | `parsing_progress` | HomeScreen progress bar |
| `belief_confidence_changed` | `float` | `belief_confidence` | CoachScreen progress ring |
| `total_matches_changed` | `int` | `total_matches_processed` | HomeScreen match count |
| `training_changed` | `dict` | epoch/loss/eta | HomeScreen training card |
| `notification_received` | `str,str` | ServiceNotification rows | MainWindow toast |

---

## 4. Screen Registry (13 Screens)

| Screen | File | on_enter() | Key Data | Known Issues |
|--------|------|-----------|----------|--------------|
| Home | `home_screen.py` | Refresh paths, connect signals | Config paths, AppState | Pro ingestion buttons disabled |
| Coach | `coach_screen.py` | Load insights, connect belief signal | CoachingInsight, CoachState | 0% confidence if boot didn't run |
| Match History | `match_history_screen.py` | Show loading, load matches | PlayerMatchStats | Empty if schema stale |
| Match Detail | `match_detail_screen.py` | Load demo if set | Stats + Rounds + Insights | HLTV breakdown optional |
| Performance | `performance_screen.py` | Load analytics | Analytics module (optional) | Silently empty if no module |
| Tactical Viewer | `tactical_viewer_screen.py` | Start tick timer | DemoLoader + PlaybackEngine | Parsing slow, no cancel |
| Settings | `settings_screen.py` | Refresh toggles | Config, ThemeEngine | No validation feedback |
| Wizard | `wizard_screen.py` | Reset to page 1 | Config writes | No back button |
| Profile | `profile_screen.py` | Load name | Config | Minimal |
| User Profile | `user_profile_screen.py` | Load profile | PlayerProfile | Sync disabled |
| Steam Config | `steam_config_screen.py` | Load credentials | Keyring / config | No validation |
| FaceIT Config | `faceit_config_screen.py` | Load API key | Keyring / config | Minimal |
| Help | `help_screen.py` | Load topics | Hardcoded fallback | help_system not implemented |

---

## 5. ViewModels (8 Total)

| ViewModel | File | Key Query | Signals |
|-----------|------|-----------|---------|
| MatchHistoryVM | `match_history_vm.py` | `PlayerMatchStats` (pro + user, limit 50) | `matches_changed`, `error_changed` |
| MatchDetailVM | `match_detail_vm.py` | Stats + Rounds + Insights by demo | `data_changed`, `error_changed` |
| PerformanceVM | `performance_vm.py` | Analytics module calls | `data_changed`, `error_changed` |
| CoachVM | `coach_vm.py` | `CoachingInsight` (limit 10) | `insights_loaded`, `error_changed` |
| UserProfileVM | `user_profile_vm.py` | `PlayerProfile` by name | `profile_loaded`, `error_changed` |
| CoachingChatVM | `coaching_chat_vm.py` | Ollama HTTP API | `messages_changed`, `is_available_changed` |
| TacticalPlaybackVM | `tactical_vm.py` | Frame list from DemoLoader | `frame_updated`, `is_playing_changed` |
| TacticalGhostVM | `tactical_vm.py` | GhostEngine predictions | `ghost_active_changed` |

All ViewModels use the `Worker` QRunnable pattern for background operations.

---

## 6. Root Causes Found (2026-03-30)

### RC-1: Stale Python 3.12 Bytecode (CRITICAL)

**216 stale `.cpython-312.pyc` files** existed alongside fresh `.cpython-310.pyc` files.
System has Python 3.12 at `/usr/bin/python3.12`. If anything triggered it, old compiled
code would be loaded instead of our edits.

**Fix:** `launch.sh` now clears all `__pycache__` before every launch and explicitly
uses the venv Python 3.10.

### RC-2: Qt App Never Called init_database()

`console.py boot()` did NOT call `create_db_and_tables()`. The monolith schema was
assumed to already exist. When the recovered database (from Feb) was missing 14 columns,
the ORM queries crashed with `no such column`.

**Fix:** `boot()` now calls `init_database()` before `_audit_databases()`.

### RC-3: Dead .venv Directory

Project root has `.venv/` with Windows-style paths (`C:\Users\Renan\...`).
Real venv is at `/home/renan/.venvs/cs2analyzer/`. Not causing bugs but confusing.

---

## 7. Current Data State

| Table | Rows | Status |
|-------|------|--------|
| PlayerMatchStats | 22 (all pro) | Working after schema fix |
| PlayerTickState | 10,000 | Working |
| CoachingInsight | 0 | Empty — no coaching has run |
| CoachingExperience | 0 | Empty — new table |
| TacticalKnowledge | 0 | Empty — new table |
| ProPlayer (HLTV) | 0 | Schema changed, needs re-scrape |
| Per-match databases | 156 | Symlinked from SSD |

**dataset_split enum:** Fixed from lowercase 'train' → 'TRAIN' (22 rows).

---

## 8. Open Frontend Issues (Priority Order)

| ID | Screen | Issue | Severity |
|----|--------|-------|----------|
| FE-01 | Coach | 0% confidence until boot computes it | HIGH — fixed |
| FE-02 | Match History | `no such column` crash | HIGH — fixed (schema reconciliation) |
| FE-03 | Match History | Only showed user matches (all 22 are pro) | HIGH — fixed |
| FE-04 | Coach | Chat requires Ollama running + 400MB SBERT download | MEDIUM |
| FE-05 | Coach | No coaching insights exist (never ran coaching pipeline) | MEDIUM |
| FE-06 | Home | Pro ingestion speed buttons disabled (Phase 3) | LOW |
| FE-07 | Performance | Analytics module optional, silently returns empty | MEDIUM |
| FE-08 | Tactical | Demo parsing slow with no progress indicator | MEDIUM |
| FE-09 | Settings | No validation feedback on interval input | LOW |
| FE-10 | Wizard | No back button, no step indicator | LOW |
| FE-11 | All | QPainter noise from QGraphicsOpacityEffect on first paint | LOW — mitigated |
| FE-12 | Help | help_system module not implemented, hardcoded fallback | LOW |

---

*Document generated 2026-03-30. Based on code analysis at commit `4265c32`.*
