# Database Storage Layer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Overview

SQLite-based persistence layer with WAL mode, SQLModel ORM, backup management, and dual-storage architecture (monolith `database.db` + per-match SQLite files).

## Key Components

### `db_models.py`
61+ SQLModel classes defining the complete data model:
- **Player Stats**: `PlayerMatchStats`, `PlayerTickState`, `RoundStats`
- **Coaching**: `CoachState`, `CoachingInsight`, `CoachingExperience`
- **Knowledge**: `TacticalKnowledge`, `ExperienceRecord`
- **Pro Data**: `ProPlayer`, `MatchResult`, `TeamComposition`
- **Analysis**: `MomentumState`, `BeliefSnapshot`, `RoleThresholdRecord`
- **System**: `DemoFileRecord`, `TrainingMetrics`, `IntegrityManifest`

### `database.py`
- **`DatabaseManager`** — SQLite connection manager with WAL mode
- **`get_db_manager()`** — Singleton factory pattern
- **`init_database()`** — Schema initialization and migration

### `match_data_manager.py`
- **`MatchDataManager`** — Per-match SQLite database management
- **`get_match_data_manager()`** — Singleton factory with config integration
- **`migrate_match_data()`** — One-time migration to external storage path
- Match DBs stored at `config.MATCH_DATA_PATH` (default: `PRO_DEMO_PATH/match_data/`)

### `backup_manager.py`
- **`BackupManager`** — Orchestrates backup of monolith DB and all match DBs
- Rotation policy, integrity verification

### Supporting Modules
- **`db_backup.py`** — Backup utilities with path resolution from config
- **`db_migrate.py`** — Alembic migration utilities
- **`maintenance.py`** — VACUUM, ANALYZE, integrity checks
- **`state_manager.py`** — CoachState persistence
- **`stat_aggregator.py`** — RoundStats → PlayerMatchStats aggregation

## Critical Patterns

- **Always use WAL mode** — `PRAGMA journal_mode=WAL` for concurrent access
- **Never hardcode match_data path** — Use `config.MATCH_DATA_PATH` or `get_match_data_manager()`
- **Call `reset_match_data_manager()` after path changes** — Invalidates singleton cache

## Migration

Match data relocation implemented in 2026-02-22 session. Old location: `backend/storage/match_data/`. New location: `PRO_DEMO_PATH/match_data/` (external drive).
