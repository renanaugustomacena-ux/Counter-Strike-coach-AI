# Backend Ingestion — File Watching, Resource Governance, Match Date Resolution & CSV Migration

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 2 (Backend Sovereignty), Rule 4 (Data Persistence)
> **Skill:** `/resilience-check`, `/data-lifecycle-review`

This module handles the runtime ingestion layer: watching for new demo files on disk, governing system resources during background processing, resolving real match dates for chronological dataset splits, and migrating external CSV datasets into the database.

**Note:** This is distinct from the top-level `Programma_CS2_RENAN/ingestion/` directory, which handles the multi-stage pipeline orchestration. This module provides the low-level building blocks.

## File Inventory

| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|----------------------|
| `watcher.py` | ~238 | Filesystem monitor for `.dem` files | `DemoFileHandler(FileSystemEventHandler)`, `IngestionWatcher` |
| `resource_manager.py` | ~201 | CPU/RAM throttling for background tasks | `ResourceManager` |
| `csv_migrator.py` | ~213 | External CSV import into SQLModel tables | `CSVMigrator` |
| `match_date_resolver.py` | ~93 | Resolve real match dates with provenance markers | `resolve_match_date()`, `CHRONOLOGICAL_SOURCES` |

## `watcher.py` — Demo File Monitor

Uses [watchdog](https://github.com/gorakhargosh/watchdog) to observe configured directories for new `.dem` files.

### How It Works

```
New .dem file detected (on_created / on_moved)
        │
        └── Schedule stability check (1s interval)
                │
                ├── Still changing? ──> Re-check (max 120 attempts)
                │
                └── File size unchanged for 2 consecutive checks? ──> Stable
                        │
                        ├── Size < MIN_DEMO_SIZE (10 MB, from demo_format_adapter.py)? ──> Skip
                        │
                        └── File openable (not locked)? ──> Enqueue as IngestionTask in database
```

- **Stability debouncing:** Prevents reading partially-written files (Steam writes demos progressively)
- **Duplicate prevention:** Checks if file already exists in `IngestionTask` table before enqueuing
- **Pro/User distinction:** Watches both the user demo folder (`DEFAULT_DEMO_PATH`, `is_pro_folder=False`) and the pro demo folder (`PRO_DEMO_PATH`, `is_pro_folder=True`), both read via `get_setting()` at start time
- **Event-driven wake-up:** After enqueuing, calls `core/session_engine.signal_work_available()` so the queue is drained without polling

## `resource_manager.py` — System Load Throttling

Prevents the Digester daemon from consuming too many system resources during background parsing.

### Hysteresis Thresholds

```
CPU Usage (10-second moving average of 10 samples):

  100% ┬───────────────────────────────────
       │        THROTTLE ACTIVE
   85% ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← Start throttling
       │
   70% ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← Stop throttling
       │        NORMAL OPERATION
    0% ┴───────────────────────────────────
```

- **Hysteresis** prevents rapid on/off toggling near threshold
- **Smoothing:** 10 CPU samples at 1-second intervals → moving average
- **RAM guard:** RAM above 90% throttles immediately (no hysteresis)
- **Override:** Set `HP_MODE=1` environment variable to disable throttling (Turbo mode)
- **Thread-safe:** Separate locks for CPU samples and throttle state

## `csv_migrator.py` — External Data Import

Migrates external statistical CSV files into SQLModel database tables for coaching analytics.

### Data Sources

| CSV File | Target Table | Content |
|----------|-------------|---------|
| `data/external/cs2_playstyle_roles_2024.csv` | `Ext_PlayerPlaystyle` | Role probabilities per player |
| `data/external/tournament_advanced_stats.csv` | `Ext_TeamRoundStats` | Tournament-level round statistics (batch commit every 1000 rows) |

- **Idempotent:** Safe to re-run (checks for existing data before each insert)
- **Encoding:** UTF-8
- **Safe parsing:** `_safe_float()` and `_safe_int()` prevent NaN propagation
- **Standalone entry point:** Can be run directly via `python -m Programma_CS2_RENAN.backend.ingestion.csv_migrator` (uses the `get_db_manager()` singleton)

## `match_date_resolver.py` — Real Match Dates

Resolves a demo's true match date instead of using the ingestion timestamp, so that chronological dataset splits reflect real match order rather than ingestion order.

### Resolution Ladder (best first)

| Rung | Source | Signal |
|------|--------|--------|
| 1 | `filename_date` | 8-digit `YYYYMMDD` token in the demo name (e.g. `demo_mirage_20240615`) |
| 2 | `filename_year` | Leading `YYYY-` HLTV-archive prefix (coarse: January 1 of that year) |
| 3 | `file_mtime` | File modification time (weakest real signal — destroyed by copies/moves) |
| 4 | `ingested_at` | `datetime.now()` — NOT a match date; splits treat these rows as ingestion-ordered |

An `hltv_event_date` rung (joining `ProEvent.start_date`) exists only in `tools/backfill_match_dates.py`, which requires the populated `hltv_metadata.db`.

- **Sanity bounds:** parsed dates must fall between 2012 and 2035
- **Provenance markers:** each returned date carries its source string so downstream consumers (`assign_dataset_splits`) can distinguish real chronology from ingestion order
- **`CHRONOLOGICAL_SOURCES`:** the frozenset `{filename_date, filename_year, hltv_event_date}` — only rows with one of these sources count as truly chronological for the training split

## Integration

```
core/session_engine.py
        │
        ├── starts watcher.py (IngestionWatcher)
        │       │
        │       ├── Enqueues IngestionTask to database
        │       └── signal_work_available() (event-driven wake-up)
        │
        └── control/ingest_manager.py drains the queue (FIFO)
                │
                ├── ResourceManager.set_high_priority() (user-requested)
                │   or set_low_priority() (background)
                │
                └── run_ingestion._ingest_single_demo()
                        │
                        └── data_sources/demo_parser.py parses the .dem file
```

## Development Notes

- `watcher.py` requires `watchdog` package (`pip install watchdog`)
- `ResourceManager` is a static utility class — no instantiation needed
- `ResourceManager.should_throttle()` and `get_optimal_worker_count()` currently have no callers outside this module — `control/ingest_manager.py` uses only the priority helpers (`set_high_priority()` / `set_low_priority()`)
- `CSVMigrator` takes a `DatabaseManager` in its constructor for session access
- The `HP_MODE` env var is for development/benchmarking only — not for production use
- File stability checking uses `os.path.getsize()` polling plus a read-only `open()` probe to confirm the file is not locked — no filesystem locks are taken
