# Demo File Registry and Lifecycle Management

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/ingestion/registry/`

## Introduction

This package provides demo file tracking and lifecycle management for the
ingestion subsystem.  Its central responsibility is answering a single
question: "has this demo already been ingested?"  The `DemoRegistry` class
maintains a persistent JSON file that records the set of processed demo names.
The `DemoLifecycleManager` handles post-ingestion housekeeping, specifically
the time-based cleanup of old archived demo files.

Together these components ensure that no demo is ingested twice (deduplication)
and that disk space is reclaimed automatically after a configurable retention
period.

## File Inventory

| File | Purpose | Key Public API |
|------|---------|----------------|
| `__init__.py` | Package marker (empty) | -- |
| `registry.py` | Persistent demo deduplication registry | `DemoRegistry(registry_path)` |
| `lifecycle.py` | Time-based demo file cleanup | `DemoLifecycleManager(raw_dir, processed_dir)` |
| `schema.sql` | Reserved for future SQL-based registry | -- |
| `README.md` | Documentation (English) | -- |
| `README_IT.md` | Documentation (Italian) | -- |
| `README_PT.md` | Documentation (Portuguese) | -- |

## Architecture and Concepts

### `DemoRegistry` -- Deduplication Engine

The `DemoRegistry` class is the single source of truth for which demos have
already been processed.  It persists its state as a JSON file on disk and
provides thread-safe, cross-process-safe access.

**Constructor:** `DemoRegistry(registry_path: Path)`

**Internal data structure:** A Python `set` of demo name strings
(`self._processed`).  The set is serialised to JSON as a list under the key
`"processed_demos"` and deserialised back to a set on load (F6-20) for O(1)
membership checks.

**Public methods:**

| Method | Description |
|--------|-------------|
| `is_processed(demo_name: str) -> bool` | Returns `True` if the demo has already been ingested. O(1) set lookup. |
| `mark_processed(demo_name: str)` | Adds the demo to the processed set and persists to disk. No-op if already present. |

**Concurrency model (R3-08):**

The registry uses a two-layer locking strategy:

1. **Thread lock** (`threading.Lock`) -- protects the in-memory `_processed`
   set from concurrent access within the same process.
2. **File lock** (`filelock.FileLock`) -- protects the JSON file from
   concurrent access across processes.  The lock file is created at
   `<registry_path>.lock`.

Lock acquisition order is always thread lock first, then file lock.  This
consistent ordering prevents deadlocks.

**Atomic write pattern (R3-H04):**

Writes use a write-ahead strategy to prevent corruption:

1. Create a backup of the existing registry (`.json.backup`).
2. Write the new state to a temporary file (`tempfile.mkstemp()`).
3. Atomically replace the original file via `os.replace()`.
4. If any step fails, the temporary file is cleaned up and the exception
   propagates.

**Backup recovery:**

If the primary registry file is corrupted (JSON decode error), the loader
`_execute_registry_load()` attempts to restore from the `.json.backup` file.
The backup is validated for structural integrity before being trusted (must be
a dict with a `"processed_demos"` list).  Only if both primary and backup are
unavailable does the registry reset to empty -- this is logged at CRITICAL
level since it means all ingestion history is lost.

### `DemoLifecycleManager` -- Disk Cleanup

The `DemoLifecycleManager` handles the retention policy for archived demo
files.  After a demo is successfully ingested, the pipeline moves it to the
`processed_dir`.  Over time, these archived files accumulate and consume disk
space.

**Constructor:** `DemoLifecycleManager(raw_dir: Path, processed_dir: Path)`

**Public methods:**

| Method | Description |
|--------|-------------|
| `cleanup_old_demos(days: int = 30)` | Deletes `.dem` files in `processed_dir` older than `days` days. |

The cleanup logic (`_purge_expired_demos()`) iterates over all `*.dem` files in
the target directory, checks each file's `st_mtime`, and unlinks files that
exceed the retention threshold.  Each deletion is logged at INFO level.

### `schema.sql` -- Reserved

The `schema.sql` file is reserved for a future migration from JSON-based
registry to SQL-based registry.  Currently empty.  When implemented, it will
define a `demo_file_records` table with columns for file path, hash, size,
source type, lifecycle state, error code, retry count, and timestamps.

## Integration

### Upstream Consumers

| Consumer | Usage |
|----------|-------|
| `ingestion/pipelines/user_ingest.py` | Calls `is_processed()` before ingesting, `mark_processed()` after success |
| `ingestion/pipelines/json_tournament_ingestor.py` | Batch processing with registry checks |
| `run_ingestion.py` | Orchestrator-level registry management |
| `core/session_engine.py` (IngestionWatcher) | Daemon thread that triggers pipelines and consults registry |

### Dependencies

| Dependency | Purpose |
|------------|---------|
| `filelock` | Cross-process file locking (third-party) |
| `observability/logger_setup.get_logger()` | Structured logging |

## Lifecycle State Diagram

```
  [New File]
      |
      v
  is_processed()?
      |
  +---+---+
  |       |
  No      Yes --> skip
  |
  v
  Pipeline runs
      |
  +---+---+
  |       |
  OK    FAIL --> stays in source_dir for retry
  |
  v
  mark_processed()
      |
  v
  Archived to processed_dir
      |
      v  (after retention period)
  cleanup_old_demos() --> unlinked
```

## Development Notes

- **F6-20 (set conversion):** The JSON format stores `processed_demos` as a
  list for serialisation compatibility.  On load, the list is immediately
  converted to a `set` for O(1) membership checks.  This is important because
  the registry may contain thousands of entries and is checked on every
  ingestion attempt.
- **R3-08 (thread safety):** The `_lock` (threading.Lock) and `_file_lock`
  (FileLock) are always acquired in the same order to prevent deadlocks.  The
  thread lock is acquired first, then the file lock.
- **R3-H04 (atomic writes):** The `_save_inner()` method uses
  `tempfile.mkstemp()` + `os.replace()` to guarantee that the registry file is
  never left in a half-written state.  This is critical because a crash during
  write would otherwise corrupt the entire ingestion history.
- **Backup safety:** Before every write, a copy of the current registry is
  created at `<path>.json.backup`.  The backup is validated on recovery to
  prevent restoring from a corrupted backup.
- **Retention default:** The default retention period of 30 days is a
  conservative balance between disk space and the ability to re-analyse recent
  demos.  It can be overridden via the `days` parameter.
- **No database dependency:** The registry intentionally uses a flat JSON file
  rather than SQLite.  This avoids coupling to the tri-database system and
  keeps the registry self-contained and portable.
