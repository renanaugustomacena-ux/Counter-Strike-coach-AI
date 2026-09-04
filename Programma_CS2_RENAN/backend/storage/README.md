# Database Storage Layer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/backend/storage/`
Tri-database persistence layer powering every data operation in Macena CS2 Analyzer.

## Introduction

This package implements the entire data persistence tier using SQLite in WAL mode,
SQLModel/SQLAlchemy ORM, and a three-tier storage architecture. Every player tick,
match statistic, coaching insight, and professional player profile passes through
these modules before reaching the neural network training pipeline or the user
interface. The design prioritizes data durability, concurrent daemon access, and
portability across machines.

## File Inventory

| File | Purpose |
|------|---------|
| `db_models.py` | 25 SQLModel table classes spanning the full data model |
| `database.py` | `DatabaseManager` (monolith) + `HLTVDatabaseManager` + singletons |
| `match_data_manager.py` | Per-match SQLite partitions (Tier 3) with LRU engine cache |
| `backup_manager.py` | Hot backup via SQLite Online Backup API, retention (7 daily incl. the newest + 4 weekly) |
| `db_backup.py` | SQLite Online Backup API wrapper + tar.gz archival for match data; `rotate_backups()` keeps 5 |
| `db_migrate.py` | Alembic migration runner for automatic schema upgrades on startup |
| `maintenance.py` | Metadata pruning: removes old tick data while preserving aggregate stats |
| `state_manager.py` | `StateManager` DAO for the singleton `CoachState` row |
| `stat_aggregator.py` | `StatCardAggregator`: spider output to `ProPlayer`/`ProPlayerStatCard` |
| `storage_manager.py` | `StorageManager`: demo file paths, quota enforcement, deduplication |
| `remote_file_server.py` | FastAPI personal cloud server for cross-machine demo access |
| `datasets/`, `models/` | README-only placeholder packages (empty `__init__.py`, no code) |
| `remote_telemetry/` | Sample telemetry JSON only (no code) |

## Tri-Database Architecture

The system splits data across three distinct SQLite databases to eliminate
write-lock contention between daemons and to keep per-match B-tree depth shallow.

```
+-------------------------------+
|      database.db (Monolith)   |
|  18 tables: training data,    |
|  player stats, ticks,         |
|  coaching state, knowledge    |
+---------------+---------------+
                |
                |  Separate process / no FK link
                v
+-------------------------------+
|    hltv_metadata.db (HLTV)    |
|  7 tables: ProTeam, ProPlayer,|
|  ProPlayerStatCard, ProEvent, |
|  ProTournament, ProHead2Head, |
|  ProMapRecord                 |
+-------------------------------+

+--------------------------------------+
|  match_data/match_{id}.db (Tier 3)   |
|  Per-match telemetry:                |
|  MatchTickState,                     |
|  MatchEventState,                    |
|  MatchMetadata                       |
+--------------------------------------+
   One file per match
```

### Connection PRAGMAs (enforced on every checkout)

```sql
PRAGMA journal_mode     = WAL;
PRAGMA synchronous      = NORMAL;
PRAGMA busy_timeout     = 30000;
PRAGMA foreign_keys     = ON;      -- DB-06: FKs are decorative without this
PRAGMA wal_autocheckpoint = 512;   -- DB-07: ~2 MB checkpoint cadence
```

Engine pool: `pool_size=1, max_overflow=4` for single-writer SQLite safety.

## Key Classes

### DatabaseManager (`database.py`)

Manages the monolith `database.db`. Provides:

- `create_db_and_tables()` -- schema initialization (filtered to `_MONOLITH_TABLES`)
- `get_session()` -- context manager with auto-commit/rollback and `expire_all()` on failure
- `upsert()` -- atomic upsert; uses SQLite `INSERT ... ON CONFLICT` for `PlayerMatchStats`
- `delete_match_cascade()` -- FK-safe deletion order (children first, then parent)
- `detect_orphans()` -- finds per-match DB files without a corresponding `MatchResult`

Singleton access: **always** use `get_db_manager()` (double-checked locking).

### HLTVDatabaseManager (`database.py`)

Dedicated manager for `hltv_metadata.db`, isolated to avoid WAL contention with
the session engine daemons. Includes `_reconcile_stale_schema()` which drops and
recreates tables whose column set has drifted from the model definition. Note:
`hltv_metadata.db` is NOT under Alembic yet — its schema evolves only via
`create_all()` plus this drop/recreate reconciliation (backlog item #47 in
`TASKS.md` tracks bringing it under Alembic).

Singleton access: `get_hltv_db_manager()`.

### MatchDataManager (`match_data_manager.py`)

Creates and manages individual SQLite files under `config.MATCH_DATA_PATH`.
Each match gets `match_{id}.db` containing `MatchTickState`, `MatchEventState`,
and `MatchMetadata`. Features:

- LRU engine cache (`OrderedDict`, max 50 entries) to prevent file-handle exhaustion
- Auto-migration via `_ensure_match_schema()` (incremental `ALTER TABLE` steps)
- `tables=` filter on `create_all()` to prevent monolith tables leaking into match DBs
- Migration utility `migrate_match_data()` for relocating data to external drives
  (explicit call only — nothing invokes it implicitly)

### StateManager (`state_manager.py`)

Thread-safe DAO for the singleton `CoachState` row (CHECK constraint `id = 1`).
Tracks daemon status, training progress, heartbeat, and resource limits. Features:

- `DaemonName` enum prevents typo-driven status update bugs
- Telemetry escalation (SM-02): logs at WARNING until 5 consecutive failures, then ERROR
- Notification auto-pruning (SM-03): caps at 500, prunes entries older than 30 days

### BackupManager (`backup_manager.py`)

Hot backup using SQLite's Online Backup API (`sqlite3.Connection.backup()` at
`backup_manager.py:115-123`), WAL-safe and non-blocking. Retention policy:
keep 7 daily backups (the newest is always kept) + 4 weekly backups. Every
backup is verified with `PRAGMA quick_check` before acceptance. Size guard
(ST-BK-01, 2026-08-03): refuses to back up a database larger than 50 GiB
(override via `CS2_BACKUP_MAX_DB_BYTES`) or when free space is below 1.2x
the database size — the monolith can be hundreds of GB.

### StorageManager (`storage_manager.py`)

File-system manager for demo files. Handles user and pro demo paths, quota
enforcement, deduplication against `IngestionTask` and `PlayerMatchStats`, and
path-traversal protection (P2-03).

## Data Model Highlights (db_models.py)

The module defines 25 SQLModel table classes organized into logical groups:

- **Player telemetry:** `PlayerMatchStats`, `PlayerTickState`, `RoundStats`, `PlayerProfile`
- **Coaching framework:** `CoachState`, `CoachingInsight`, `CoachingExperience` (COPER)
- **Knowledge base:** `TacticalKnowledge` (RAG, 384-dim embeddings)
- **Pro data:** `ProTeam`, `ProPlayer`, `ProPlayerStatCard`, `ProEvent`, `ProTournament`, `ProHead2Head`, `ProMapRecord`
- **Match structure:** `MatchResult`, `MapVeto`
- **External data:** `Ext_TeamRoundStats`, `Ext_PlayerPlaystyle`
- **Pipeline control:** `IngestionTask`, `ServiceNotification`
- **Observability:** `DataLineage`, `DataQualityMetric`, `CalibrationSnapshot`
- **ML tuning:** `RoleThresholdRecord`

JSON field size guards are enforced via Pydantic validators:
`MAX_GAME_STATE_JSON_BYTES = 16 KB`, `MAX_AUX_JSON_BYTES = 8 KB`.

## Integration Points

```
session_engine.py ──> get_db_manager()   ──> database.db
                  ──> get_state_manager() ──> CoachState (singleton row)

hltv_sync_service ──> get_hltv_db_manager() ──> hltv_metadata.db

ingestion pipeline ──> get_match_data_manager() ──> match_data/match_{id}.db
                   ──> get_db_manager()          ──> PlayerMatchStats, RoundStats
```

## Development Notes

- **Never instantiate managers directly.** Use `get_db_manager()`, `get_hltv_db_manager()`,
  `get_match_data_manager()`, and `get_state_manager()` singletons.
- **Call `reset_match_data_manager()` after `PRO_DEMO_PATH` changes** to invalidate the
  cached engine pool and pick up the new path.
- **The HLTV database has NOTHING to do with demo files.** It scrapes professional player
  statistics from hltv.org. Demo ingestion is an entirely separate pipeline.
- **FK cascade rules:** `ON DELETE CASCADE` for dependent data (stat cards, map vetoes);
  `ON DELETE SET NULL` for data that should survive parent deletion (ticks, experiences).
- **Match data relocation is explicit-only.** Nothing relocates shards automatically:
  `warn_if_shards_in_legacy_location()` only logs a warning when shards remain in the
  legacy in-project directory. Call `migrate_match_data()` yourself when relocation is
  intended (the old implicit "one-time migration" was removed on 2026-07-26 after it
  moved the production shard corpus as a side effect of constructing the singleton).
