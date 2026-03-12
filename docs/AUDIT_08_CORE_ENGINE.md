# Audit Report 08 — Core Engine & App Entry

**Scope:** `core/`, `backend/control/`, `main.py`, `run_ingestion.py` — 29 files, ~7,484 lines | **Date:** 2026-03-10
**Open findings:** 1 HIGH (arch debt) | 1 HIGH (bug) | 17 MEDIUM | 14 LOW

---

## HIGH Findings

| ID | File | Finding |
|---|---|---|
| Core-11 | main.py | **ACKNOWLEDGED DEBT**: God module — 1945 lines, 6 screen classes + full CS2AnalyzerApp. High-effort refactor deferred. |
| Core-22 | run_ingestion.py | Private method access `match_manager._get_or_create_engine(match_id)` — breaks on refactor |
| Core-45 | ml_controller.py | Wrong import: `from core.constants import DATA_DIR` — DATA_DIR is in config.py, will raise ImportError |

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| Core-02 | config.py | STORAGE_ROOT dual-assignment — import-order dependency |
| Core-03 | config.py | "PROTECTED_BY_WINDOWS_VAULT" sentinel leaks as literal API key value |
| Core-06 | session_engine.py | sys.path manipulation at module level (documented tech debt) |
| Core-07 | session_engine.py | FileHandler not cleaned up on failure; created unconditionally on import |
| Core-08 | session_engine.py | `is_pro == True` should use `.is_(True)` for SQLAlchemy correctness |
| Core-12 | main.py | Mutable class-level `_last_completed_tasks = []` shared across instances |
| Core-13 | main.py | Mutable class-level `_nav_stack: list = []` shared across instances |
| Core-14 | main.py | Broken atexit cleanup — accumulates handlers on each `show_skill_radar()` |
| Core-15 | main.py | `queue.pop(0)` in BFS — O(n), should use deque |
| Core-16 | main.py | 9+ daemon threads perform DB writes — killed mid-transaction on exit |
| Core-17 | main.py | `self.ids.name_label.text` — no guard for missing KV widget |
| Core-18 | main.py | Bare `except Exception: pass` for Sentry init |
| Core-23 | run_ingestion.py | `_save_sequential_data()` is ~280 lines — single untestable function |
| Core-24 | run_ingestion.py | state_lookup FIFO eviction — later events get wrong defaults |
| Core-25 | run_ingestion.py | `iterrows()` for state_lookup on 2.4M+ rows — extremely slow |
| Core-26 | run_ingestion.py | `is_pro == False` — same SQLAlchemy boolean issue |
| Core-29 | localization.py | Import-time f-string path evaluation in translation strings |
| Core-35 | lifecycle.py | Log file handles stored on `self` — leak if `shutdown()` never called |
| Core-39 | console.py | Italian log message in application logs |
| Core-40 | console.py | Console singleton reset on init failure |
| Core-47 | resource_manager.py | Priority management Windows-only — Linux runs at normal priority |
| Core-48 | resource_manager.py | Unused loop variable in `for f, arg in enumerate(cmd)` |
| Core-50 | watcher.py | Import-time path values — stale after user changes settings |
| Core-54 | demo_loader.py | O(ticks) per-grenade nade lookup — could use interval-based |
| Core-55 | demo_loader.py | Two full-match DataFrame passes held in memory simultaneously |
| Core-57 | hltv_sync_service.py | Hardcoded Italian strings in notifications |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| Core-04 | config.py | `globals()[key]` dynamic mutation — hard to trace |
| Core-05 | config.py | Russian word in comment |
| Core-09 | session_engine.py | Teacher daemon 5-min sleep as 300x1s loop |
| Core-10 | session_engine.py | `pass` in nested except — notification failure silently swallowed |
| Core-19 | main.py | Unusual tuple unpacking for Kivy StringProperty declarations |
| Core-20 | main.py | Duplicate `from kivy.core.window import Window` import |
| Core-21 | main.py | `import copy` inside method |
| Core-27 | run_ingestion.py | `import math` inside function |
| Core-28 | run_ingestion.py | Logger name mismatch vs module path |
| Core-30 | localization.py | Only 3 languages supported |
| Core-31 | localization.py | `_HOME_DIR` assigned but never used |
| Core-32 | spatial_data.py | `reload()` not thread-safe |
| Core-33 | spatial_data.py | Ambiguous partial match returns first candidate |
| Core-36 | lifecycle.py | `Global\\` mutex prefix meaningless on Linux |
| Core-37 | demo_frame.py | `object.__setattr__` on non-frozen dataclass |
| Core-38 | demo_frame.py | Mutable `list` trajectory on frozen dataclass |
| Core-41 | console.py | Shutdown uses sleep polling instead of Event |
| Core-42 | ingest_manager.py | Missing explicit commit after `_queue_files()` |
| Core-43 | ingest_manager.py | Hardcoded `_MAX_RETRIES` and `_STALE_THRESHOLD` |
| Core-46 | trend_analysis.py | Confidence denominator 30 but history limit is 10 |
| Core-49 | resource_manager.py | `psutil.process_iter()` iterates ALL processes |
| Core-51 | watcher.py | `os.makedirs()` silently creates directories |
| Core-52 | steam_locator.py | Duplicate Steam path discovery |
| Core-53 | steam_locator.py | Recursive glob may follow symlinks |
| Core-56 | demo_loader.py | CACHE_DIR computed relative to `__file__` |
| Core-58 | hltv_sync_service.py | PID/stop files stored in source directory |
| Core-59 | hltv_sync_service.py | Fixed 60s backoff on sync error |
| Core-60 | db_migrate.py | `alembic.ini` searched relative to wrong BASE_DIR |

## Cross-Cutting

1. **Daemon Thread Safety** — 12+ daemon threads killed on exit without cleanup; in-progress SQLite transactions rolled back by WAL.
2. **Italian Log Messages** — console.py and hltv_sync_service.py break English logging convention.
3. **Platform Gaps** — resource_manager.py priority is Windows-only; Linux runs unrestricted.
