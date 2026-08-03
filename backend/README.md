# `backend/` (top-level) — storage staging

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Repo-level filesystem layout
> **Status:** Staging area; the package backend lives at `Programma_CS2_RENAN/backend/`.

## Why this directory exists

`./backend/` (this directory, at the repo root) is **not** the application backend package. It is a small filesystem staging area that mirrors the backend domain's layout outside the Python package tree — today it holds only a legacy Alembic migration scaffold under `storage/`.

The actual backend codebase — services, NN training, ingestion, storage managers, knowledge base, processing pipelines — lives at:

> `Programma_CS2_RENAN/backend/` ([README](../Programma_CS2_RENAN/backend/README.md))

That sub-package owns 14 domain modules (`analysis/`, `coaching/`, `control/`, `data_sources/`, `ingestion/`, `knowledge/`, `knowledge_base/`, `nn/`, `onboarding/`, `processing/`, `progress/`, `reporting/`, `services/`, `storage/`).

## What lives here

```
backend/
└── storage/
    └── migrations/   # Legacy Alembic scaffold (2 early revisions) — NOT the active chain
```

`backend/storage/` contains only a vestigial Alembic scaffold ([README](storage/README.md)). The **active** migration chain lives at the repo-root `alembic/` directory (18 revisions), configured by the root `alembic.ini`. Runtime databases do **not** live here: the monolith `database.db` and `hltv_metadata.db` are created under `Programma_CS2_RENAN/backend/storage/`, and per-match shards go to `PRO_DEMO_PATH/match_data/` (falling back to `Programma_CS2_RENAN/backend/storage/match_data/`).

## Do not

- **Do not** add Python source files here. New backend code goes into `Programma_CS2_RENAN/backend/<domain>/`.
- **Do not** treat this as the import path. `from backend.foo import ...` will not resolve — the package root is `Programma_CS2_RENAN`.
- **Do not** add new migrations here. New schema changes go through the root `alembic/versions/` chain.

## Related documentation

- Application backend package: `Programma_CS2_RENAN/backend/README.md`
- Storage layer specifics: `Programma_CS2_RENAN/backend/storage/README.md`
- Active migration chain: `alembic/README.md` (repo root)
- Tri-database architecture: `REFERENCE.md`
