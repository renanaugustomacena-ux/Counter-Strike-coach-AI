# `backend/storage/models/` — Reserved namespace

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/storage/models/`
> **Status:** Reserved — currently empty, kept as a Python package.

## Why this exists

Reserved namespace intended for **storage-layer-specific data classes**: things like row-mapping helpers, lightweight DTOs that mediate between SQLModel ORM rows and downstream consumers, or query-builder result types.

It is **not** the place for the SQLModel ORM table definitions — those live in `backend/storage/db_models.py`. Putting them here would create a confusing two-source-of-truth for the data model.

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker (empty). |

## When to add code here

Add a module here when:

- You have a storage-side DTO that doesn't map 1:1 to a database table (e.g. a flattened query result, a join projection).
- The DTO is consumed by multiple modules and deserves a single home.
- You are *not* defining a new ORM table — those go in `db_models.py`.

## Boundaries (keep clean)

| Concern | Lives in |
|---------|----------|
| ORM table classes (`SQLModel.table=True`) | `backend/storage/db_models.py` |
| Manager singletons (`get_db_manager()`, etc.) | `backend/storage/database.py` |
| Per-match SQLite engine pool | `backend/storage/match_data_manager.py` |
| Storage-side DTOs and result types | `backend/storage/models/` (this directory) |

## Do not

- Do not add new ORM table classes here. They must live in `db_models.py`.
- Do not import from this package eagerly — empty packages should not appear in the public API.
- Do not place machine-learning model checkpoints here. Those live in `Programma_CS2_RENAN/models/`.

## Related

- ORM definitions: `backend/storage/db_models.py`
- Storage layer overview: `backend/storage/README.md`
