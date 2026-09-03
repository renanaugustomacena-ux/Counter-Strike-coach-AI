> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Legacy Migration Scaffold

This directory holds a **legacy Alembic scaffold** from an early iteration of the persistent data layer. It is kept for historical reference only — the **active** migration chain for the application lives at the repo-root `alembic/` directory (18 revisions, configured by the root `alembic.ini`).

## Technical Overview

The scaffold uses SQLAlchemy/SQLModel as the ORM layer and Alembic for schema evolution, mirroring the approach the project still uses today. It contains the first two schema revisions ever written for the match-statistics layer; later development restarted the chain at the repo root, where all subsequent revisions live.

## Key Components

### Alembic Migrations
The **`migrations/`** subdirectory contains the scaffold:
- **`env.py`**: The Alembic environment entry point (imports all models from `Programma_CS2_RENAN.backend.storage.db_models` and targets `SQLModel.metadata`).
- **`script.py.mako`**: A template file used by Alembic to generate new migration scripts.
- **`README`**: A deprecation notice (R2-01) marking this chain as legacy and pointing at the root `alembic/` directory.
- **`versions/`**: The two early migration scripts.
    - **`b609a11e13cc_baseline_schema.py`**: Establishes the initial tables (`matchresult`, `mapveto`) and extends `proplayerstatcard`.
    - **`5d5764ef9f26_add_rating_components.py`**: Adds Rating 2.0 component columns (kpr, dpr, …) to `playermatchstats`.

## Directory Structure

```text
backend/storage/
├── migrations/             # Legacy Alembic scaffold
│   ├── env.py              # Environment configuration
│   ├── script.py.mako      # Migration script template
│   ├── README              # R2-01 deprecation notice
│   └── versions/           # Two early schema revisions
├── README.md               # This documentation
├── README_IT.md            # Italian version
└── README_PT.md            # Portuguese version
```

## Usage

Do **not** run migrations from this directory — there is no `alembic.ini` here, and the chain is superseded. All migration commands run from the project root against the root `alembic/` directory:

### Applying Migrations
```bash
alembic upgrade head
```

### Creating a New Migration
When the SQLModel classes in `Programma_CS2_RENAN/backend/storage/db_models.py` are updated:
```bash
alembic revision --autogenerate -m "description of changes"
```

### Rollbacks
```bash
alembic downgrade -1
```

The database URL is set in the root `alembic.ini` (SQLite monolith `Programma_CS2_RENAN/backend/storage/database.db`); the `CS2_ALEMBIC_URL` environment variable can override it for throwaway verification databases. See `alembic/README.md` at the repo root for the full migration history.
