> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Database Storage & Migrations

This directory manages the persistent data layer of the Counter-Strike coach application. It leverages SQLAlchemy as the Object-Relational Mapper (ORM) and Alembic for robust database schema evolution and migration management.

## Technical Overview

The storage engine is designed to ensure data integrity and schema consistency across different deployment environments. By using Alembic, the system maintains a linear history of database changes, allowing for seamless upgrades and rollbacks. The schema is optimized for high-performance queries on match statistics, player performance metrics, and tactical metadata.

## Key Components

### Alembic Migrations
The **`migrations/`** subdirectory contains the logic for database evolution:
- **`env.py`**: The entry point for the Alembic environment, configuring the database connection and migration context.
- **`script.py.mako`**: A template file used by Alembic to generate new migration scripts.
- **`versions/`**: A collection of incremental migration scripts.
    - **`b609a11e13cc_baseline_schema.py`**: Establishes the initial tables (Players, Matches, Rounds, etc.).
    - **`5d5764ef9f26_add_rating_components.py`**: An example of an incremental update that adds complex rating calculation fields to the database.

## Directory Structure

```text
backend/storage/
├── migrations/             # Alembic migration engine
│   ├── env.py              # Environment configuration
│   ├── script.py.mako      # Migration script template
│   └── versions/           # Incremental schema versions
├── README.md               # This documentation
├── README_IT.md            # Italian version
└── README_PT.md            # Portuguese version
```

## Usage

### Applying Migrations
To bring the database to the latest version, run the following command from the project root:
```bash
alembic upgrade head
```

### Creating a New Migration
When the SQLAlchemy models in the backend are updated, generate a new migration script using:
```bash
alembic revision --autogenerate -m "description of changes"
```

### Rollbacks
To revert to a previous version:
```bash
alembic downgrade -1
```

The database connection parameters are typically loaded from environment variables or the central `settings.json` file.
