> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Database Migration System (Alembic)

> **Authority:** Rule 5 (Data Persistence), Rule 6 (Change Governance)
> **Skill:** `/db-review`

Database migration system using Alembic for managing SQLite schema evolution in the Macena CS2 Analyzer. All schema changes to the monolith database (`database.db`) must go through Alembic migrations — no manual DDL in production.

## Directory Structure

```
alembic/
├── env.py                  # Alembic environment configuration
├── script.py.mako          # Migration script template
└── versions/               # Migration history (sequential, immutable)
    ├── 19fcff36ea0a_...    # Heartbeat telemetry
    ├── 3c6ecb5fe20e_...    # Fusion plan columns
    ├── 57a72f0df21e_...    # Nullable heartbeat
    ├── 609fed4b4dce_...    # Ingestion task tracking
    ├── 7a30a0ea024e_...    # Schema synchronization
    ├── 89850b6e0a49_...    # Professional player statistics
    ├── 8a93567a2798_...    # Pro player physics linking
    ├── 8c443d3d9523_...    # Triple daemon support
    ├── a1b2c3d4e5f6_...    # Data quality metrics
    ├── b2c3d4e5f6a7_...    # Player tick enrichment
    ├── c8a2308770e5_...    # Retraining triggers
    ├── da7a6be5c0c7_...    # Service notifications
    ├── e3013f662fd4_...    # Coaching state sync
    └── f769fbe67229_...    # Profile field completeness
```

## Migration History (14 Revisions)

| Revision | Description | Tables Affected |
|----------|-------------|-----------------|
| `f769fbe67229` | Add missing profile fields | `UserProfile` |
| `e3013f662fd4` | Add sync and interval to CoachState | `CoachState` |
| `da7a6be5c0c7` | Add service notification table | `ServiceNotification` (new) |
| `c8a2308770e5` | Add retraining trigger support | `TrainingState` |
| `b2c3d4e5f6a7` | Add enrichment columns to PlayerTickState | `PlayerTickState` |
| `a1b2c3d4e5f6` | Add data quality to PlayerMatchStats | `PlayerMatchStats` |
| `8c443d3d9523` | Triple daemon support (Hunter/Digester/Teacher) | `DaemonState` (new) |
| `8a93567a2798` | Link pro physics to stats | `ProPlayer`, `ProPlayerStatCard` |
| `89850b6e0a49` | Add professional player statistics | `ProPlayer` (new), `ProPlayerStatCard` (new) |
| `7a30a0ea024e` | Sync missing tables | Multiple |
| `609fed4b4dce` | Add last_tick_processed to IngestionTask | `IngestionTask` |
| `57a72f0df21e` | Add nullable heartbeat to CoachState | `CoachState` |
| `3c6ecb5fe20e` | Fusion plan columns (temporal baseline, role thresholds) | `CoachState` |
| `19fcff36ea0a` | Add heartbeat telemetry to CoachState | `CoachState` |

## `env.py` — Environment Configuration

The environment script handles both offline and online migration modes:

- **Path stabilization** via `core.config.stabilize_paths()` — ensures correct `CORE_DB_DIR` resolution
- **Model import** — imports all SQLModel classes from `backend/storage/db_models.py` for autogenerate
- **WAL mode enforcement** — every connection sets `PRAGMA journal_mode=WAL` before running migrations
- **Database URL** — resolved from `core.config.DATABASE_URL` (always points to monolith `database.db`)

```python
# Connection setup (simplified)
connectable = create_engine(config.DATABASE_URL)
with connectable.connect() as connection:
    connection.execute(text("PRAGMA journal_mode=WAL"))
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

## Scope and Boundaries

Alembic manages **only** the monolith database (`database.db`). The other two databases in the tri-database architecture are managed separately:

| Database | Manager | Migration Strategy |
|----------|---------|-------------------|
| `database.db` (monolith) | Alembic | Sequential versioned migrations |
| `hltv_metadata.db` | `HLTVDatabaseManager` | Schema created at first use |
| `match_data/<id>.db` (per-match) | `MatchDataManager` | Schema created per demo ingestion |

## Usage

```bash
# Activate virtual environment first
source /home/renan/.venvs/cs2analyzer/bin/activate

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

1. **Idempotent** — migrations use `batch_alter_table` for SQLite compatibility and can be re-run safely
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
- The `DatabaseGovernor` in `backend/control/db_governor.py` audits migration state on every boot
- All 61+ SQLModel classes in `db_models.py` are imported by `env.py` for autogenerate detection

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "Target database is not up to date" | Pending migrations | Run `alembic upgrade head` |
| "Can't locate revision" | Corrupted `alembic_version` table | Check `alembic current`, manually fix if needed |
| "No changes detected" | Model changes not imported | Ensure `db_models.py` imports in `env.py` |
| Batch mode errors | Missing `render_as_batch=True` | Add to `context.configure()` in `env.py` |
