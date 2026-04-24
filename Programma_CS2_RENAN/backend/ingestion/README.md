# Backend Ingestion — File Watching, Resource Governance & CSV Migration

> **Authority:** Rule 2 (Backend Sovereignty), Rule 4 (Data Persistence)
> **Skill:** `/resilience-check`, `/data-lifecycle-review`

This module handles the runtime ingestion layer: watching for new demo files on disk, governing system resources during background processing, and migrating external CSV datasets into the database.

**Note:** This is distinct from the top-level `Programma_CS2_RENAN/ingestion/` directory, which handles the multi-stage pipeline orchestration. This module provides the low-level building blocks.

## File Inventory

| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|----------------------|
| `watcher.py` | ~239 | Filesystem monitor for `.dem` files | `DemoFileHandler(FileSystemEventHandler)`, `IngestionWatcher` |
| `resource_manager.py` | ~201 | CPU/RAM throttling for background tasks | `ResourceManager` |
| `csv_migrator.py` | ~208 | External CSV import into SQLModel tables | `CSVMigrator` |

## `watcher.py` — Demo File Monitor

Uses [watchdog](https://github.com/gorakhargosh/watchdog) to observe configured directories for new `.dem` files.

### How It Works

```
New .dem file detected (on_created / on_moved)
        │
        ├── Schedule stability check (1s interval)
        │       │
        │       ├── File size unchanged for 2 consecutive checks? ──> Stable
        │       │       │
        │       │       └── Enqueue as IngestionTask in database
        │       │
        │       └── Still changing? ──> Re-check (max 120 attempts / ~30s)
        │
        └── Validate minimum size (MIN_DEMO_SIZE from demo_format_adapter.py)
```

- **Stability debouncing:** Prevents reading partially-written files (Steam writes demos progressively)
- **Duplicate prevention:** Checks if file already exists in `IngestionTask` table before enqueuing
- **Pro/User distinction:** Watches both user demo folders (`is_pro_folder=False`) and pro demo folders (`is_pro_folder=True`)

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
- **Override:** Set `HP_MODE=1` environment variable to disable throttling (Turbo mode)
- **Thread-safe:** Separate locks for CPU samples and throttle state

## `csv_migrator.py` — External Data Import

Migrates external statistical CSV files into SQLModel database tables for coaching analytics.

### Data Sources

| CSV File | Target Table | Content |
|----------|-------------|---------|
| `data/external/cs2_playstyle_roles_2024.csv` | `Ext_PlayerPlaystyle` | Role probabilities per player |
| Tournament stats CSVs | `Ext_TeamRoundStats` | Tournament-level round statistics |

- **Idempotent:** Safe to re-run (checks for existing data)
- **Encoding:** UTF-8 with BOM handling
- **Safe parsing:** `_safe_float()` and `_safe_int()` prevent NaN propagation

## Integration

```
                    watcher.py
                        │
                        ├── Enqueues IngestionTask to database
                        │
                        └── control/ingest_manager.py picks up tasks
                                │
                                ├── resource_manager.should_throttle()?
                                │       YES → sleep before next batch
                                │       NO  → process immediately
                                │
                                └── data_sources/demo_parser.py parses the .dem file
```

## Development Notes

- `watcher.py` requires `watchdog` package (`pip install watchdog`)
- `ResourceManager` is a static utility class — no instantiation needed
- `CSVMigrator` extends `DatabaseManager` for session access
- The `HP_MODE` env var is for development/benchmarking only — not for production use
- File stability checking uses `os.path.getsize()` polling, not filesystem locks
