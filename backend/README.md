# `backend/` (top-level) — storage staging

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Repo-level filesystem layout
> **Status:** Staging area; the package backend lives at `Programma_CS2_RENAN/backend/`.

## Why this directory exists

`./backend/` (this directory, at the repo root) is **not** the application backend package. It is a small filesystem staging area that holds files which need to live outside the Python package tree but logically belong to the backend domain — typically per-match SQLite shards and other large generated artefacts that should not be committed under `Programma_CS2_RENAN/`.

The actual backend codebase — services, NN training, ingestion, storage managers, knowledge base, processing pipelines — lives at:

> `Programma_CS2_RENAN/backend/` ([README](../Programma_CS2_RENAN/backend/README.md))

That sub-package owns 14 domain modules (`analysis/`, `coaching/`, `control/`, `data_sources/`, `ingestion/`, `knowledge/`, `knowledge_base/`, `nn/`, `onboarding/`, `processing/`, `progress/`, `reporting/`, `services/`, `storage/`).

## What lives here

```
backend/
└── storage/          # Generated runtime artefacts (per-match SQLite, backups)
```

`backend/storage/` is the runtime data root used by `MatchDataManager` when `PRO_DEMO_PATH` is unconfigured or unavailable. Per-match `match_{id}.db` files land here and accumulate over time. Cleanup is handled by `Programma_CS2_RENAN/backend/storage/maintenance.py` and `BackupManager`'s retention policy.

## Do not

- **Do not** add Python source files here. New backend code goes into `Programma_CS2_RENAN/backend/<domain>/`.
- **Do not** treat this as the import path. `from backend.foo import ...` will not resolve — the package root is `Programma_CS2_RENAN`.
- **Do not** commit the contents of `backend/storage/`. Generated `*.db` files are gitignored.

## Related documentation

- Application backend package: `Programma_CS2_RENAN/backend/README.md`
- Storage layer specifics: `Programma_CS2_RENAN/backend/storage/README.md`
- Tri-database architecture: `CLAUDE.md` and `REFERENCE.md`
