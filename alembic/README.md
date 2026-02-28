> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Database Migration System (Alembic)

Database migration system using Alembic for managing SQLite schema evolution.

## Overview

This directory contains Alembic migrations for the Macena CS2 Analyzer database (`database.db`). All schema changes must go through migrations — no manual DDL in production.

## Migration Files

The `versions/` directory contains 13 migration files covering:

- Profile fields and user preferences
- Schema alignment with models
- Professional player statistics
- Daemon support (Hunter, Digester, Teacher)
- Telemetry and observability
- Fusion plan columns (temporal baseline, role thresholds, coaching state)

## Key Files

- `env.py` — Alembic environment configuration (connects to SQLite WAL mode database)
- `alembic.ini` — Alembic configuration (database URL, logging)
- `versions/` — Migration history (sequential, immutable)

## Migration Principles

- **Idempotent** — Migrations can be run multiple times safely
- **Reversible** — All migrations have upgrade and downgrade paths
- **Version-controlled** — Migrations are committed to git
- **Tested** — Migrations tested on production-like data before deployment

## Usage

```bash
# Check current migration status
alembic current

# Upgrade to latest version
alembic upgrade head

# Downgrade by one revision
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "description"
```

## Notes

- Database uses SQLite WAL mode for concurrent access
- All migrations must pass headless validation before commit
- Never skip migrations or force-apply schema changes
