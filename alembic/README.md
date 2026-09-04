> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Database Migration System (Alembic)

> **Authority:** Rule 4 (Data Persistence), Rule 6 (Change Governance)
> **Skill:** `/db-review`

Database migration system using Alembic for managing SQLite schema evolution in the Macena CS2 Analyzer. All schema changes to the monolith database (`database.db`) must go through Alembic migrations — no manual DDL in production.

## Directory Structure

```
alembic/
├── env.py                  # Alembic environment configuration
├── script.py.mako          # Migration script template
└── versions/               # Migration history (sequential, immutable)
    ├── f769fbe67229_...    # Profile field completeness (root)
    ├── 7a30a0ea024e_...    # Schema synchronization
    ├── 89850b6e0a49_...    # Professional player statistics
    ├── 8a93567a2798_...    # Pro player physics linking
    ├── c8a2308770e5_...    # Retraining triggers
    ├── 8c443d3d9523_...    # Triple daemon support
    ├── 609fed4b4dce_...    # Ingestion task tracking
    ├── e3013f662fd4_...    # Coaching state sync
    ├── 57a72f0df21e_...    # Nullable heartbeat
    ├── da7a6be5c0c7_...    # Service notifications
    ├── 19fcff36ea0a_...    # Heartbeat telemetry
    ├── 3c6ecb5fe20e_...    # Fusion plan columns
    ├── a1b2c3d4e5f6_...    # Data quality metrics
    ├── b2c3d4e5f6a7_...    # Player tick enrichment
    ├── c3d4e5f6a7b8_...    # Coaching experience strategy label
    ├── d4e5f6a7b8c9_...    # SteamID columns
    ├── e5f6a7b8c9d0_...    # POV stream index
    └── f6a7b8c9d0e1_...    # Drop connect_state (head)
```

## Migration History (18 Revisions)

Single linear chain, oldest first. Current head: `f6a7b8c9d0e1`.

| Revision | Description | Tables Affected |
|----------|-------------|-----------------|
| `f769fbe67229` | Add missing profile fields (root) | `PlayerProfile`, `IngestionTask` (new) |
| `7a30a0ea024e` | Sync missing tables | `CalibrationSnapshot` (new), `RoleThresholdRecord` (new) |
| `89850b6e0a49` | Add professional player statistics | `ProTeam` (new), `ProPlayer` (new), `ProPlayerStatCard` (new) |
| `8a93567a2798` | Link pro physics to stats | `PlayerMatchStats` (FK to `ProPlayer`) |
| `c8a2308770e5` | Add retraining trigger support | `CoachState` |
| `8c443d3d9523` | Triple daemon support (Hunter/Digester/Teacher) | `CoachState` |
| `609fed4b4dce` | Add last_tick_processed to IngestionTask | `IngestionTask` |
| `e3013f662fd4` | Add sync and interval to CoachState | `CoachState` |
| `57a72f0df21e` | Add nullable heartbeat to CoachState | `CoachState` |
| `da7a6be5c0c7` | Add service notification table | `ServiceNotification` (new) |
| `19fcff36ea0a` | Add heartbeat telemetry to CoachState | `CoachState` |
| `3c6ecb5fe20e` | Fusion plan columns (trade kills, utility breakdown, COPER feedback) | `PlayerMatchStats`, `CoachingExperience` |
| `a1b2c3d4e5f6` | Add data quality to PlayerMatchStats | `PlayerMatchStats` |
| `b2c3d4e5f6a7` | Add enrichment columns to PlayerTickState | `PlayerTickState` |
| `c3d4e5f6a7b8` | Add strategy_label to CoachingExperience | `CoachingExperience` |
| `d4e5f6a7b8c9` | Add steamid to tick and match stats | `PlayerTickState`, `PlayerMatchStats` |
| `e5f6a7b8c9d0` | Add POV stream index to PlayerTickState | `PlayerTickState` (index only) |
| `f6a7b8c9d0e1` | Drop connect_state from Ext_PlayerPlaystyle (head) | `Ext_PlayerPlaystyle` |

## `env.py` — Environment Configuration

The environment script handles both offline and online migration modes:

- **Path stabilization** via `core.config.stabilize_paths()` — ensures correct `CORE_DB_DIR` resolution
- **Model import** — explicitly imports 19 SQLModel classes from `Programma_CS2_RENAN/backend/storage/db_models.py` so autogenerate diffs against `SQLModel.metadata`
- **Pre-migration backup** — online mode calls `db_backup.backup_monolith()` before running migrations (non-fatal if it fails)
- **Database URL** — `CS2_ALEMBIC_URL` (env var, for throwaway verification DBs) wins over `core.config.DATABASE_URL` (the monolith `database.db`)

```python
# URL resolution + online run (simplified)
config.set_main_option("sqlalchemy.url", os.environ.get("CS2_ALEMBIC_URL", DATABASE_URL))
_pre_migration_backup()  # backup_monolith(), non-fatal
connectable = engine_from_config(..., poolclass=pool.NullPool)
with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

## Scope and Boundaries

Alembic manages **only** the monolith database (`database.db`). The other two databases in the tri-database architecture are managed separately:

| Database | Manager | Migration Strategy |
|----------|---------|-------------------|
| `database.db` (monolith) | Alembic | Sequential versioned migrations |
| `hltv_metadata.db` | `HLTVDatabaseManager` | Schema via `SQLModel.metadata.create_all()` at first use |
| `match_data/<id>.db` (per-match) | `MatchDataManager` | Schema created per demo ingestion |

Bringing `hltv_metadata.db` under Alembic is **open backlog work** (TASKS.md #47, Programme Phase G7) — today its schema still evolves outside Alembic.

## Usage

```bash
# Activate the project virtualenv first (see "Manual Setup" in the root README.md)

# Check current migration status
alembic current

# Upgrade to latest version
alembic upgrade head

# Downgrade by one revision
alembic downgrade -1

# Generate new migration (after modifying db_models.py)
alembic revision --autogenerate -m "description_of_change"

# View migration history
alembic history --verbose
```

## Migration Principles

1. **Sequential** — one linear chain, no branches (current head: `f6a7b8c9d0e1`)
2. **Reversible** — every migration has both `upgrade()` and `downgrade()` functions
3. **Version-controlled** — migrations are committed to git and never modified after merge
4. **Tested** — run `python tools/headless_validator.py` after any schema change
5. **Atomic** — each migration is a single logical schema change
6. **SQLite-aware** — use `op.batch_alter_table()` for ALTER TABLE operations (SQLite limitation)

## Development Notes

- Always run `alembic upgrade head` after pulling new changes that include migrations
- Never delete or reorder migration files in `versions/`
- The `alembic.ini` file at the project root configures the database URL and logging
- SQLite does not support all ALTER TABLE operations natively — Alembic's batch mode handles this
- After creating a new migration, verify it with `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
- The `DatabaseGovernor` in `Programma_CS2_RENAN/backend/control/db_governor.py` runs periodic integrity audits (`PRAGMA quick_check`) on the live databases
- `env.py` explicitly imports 19 SQLModel classes from `db_models.py` (which defines 25 `table=True` models) for autogenerate detection — adding a table means adding its import there

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "Target database is not up to date" | Pending migrations | Run `alembic upgrade head` |
| "Can't locate revision" | Corrupted `alembic_version` table | Check `alembic current`, manually fix if needed |
| "No changes detected" | Model changes not imported | Ensure `db_models.py` imports in `env.py` |
| Batch mode errors | Missing `render_as_batch=True` | Add to `context.configure()` in `env.py` |
