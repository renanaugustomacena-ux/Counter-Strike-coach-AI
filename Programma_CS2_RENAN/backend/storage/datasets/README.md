# `backend/storage/datasets/` — Reserved namespace

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/storage/datasets/`
> **Status:** Reserved — currently empty, kept as a Python package.

## Why this exists

This package is a reserved namespace for **dataset wrappers** that present multiple per-match SQLite databases as a unified, iterator-friendly interface for ML training. As of HEAD it contains only `__init__.py` — the wrappers have not landed yet.

The current data-access path for training goes directly through:

- `backend/storage/match_data_manager.py` — `MatchDataManager` (per-match DB files)
- `backend/storage/database.py` — `DatabaseManager` (monolith `database.db`)

Future dataset abstractions (e.g. a `RAPTickDataset` that wraps `MatchTickState` queries with batching, sharding, and caching for `torch.utils.data.DataLoader`) will live here.

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker (empty). |

## When to add code here

Add a module here when:

- You need a `Dataset` / `IterableDataset` wrapper around per-match SQLite shards.
- The wrapper is large enough to deserve its own file (don't grow `match_data_manager.py` indefinitely).
- The abstraction is generic across multiple consumers (training, evaluation, drift detection).

Keep storage-manager logic — engine pools, connection PRAGMAs, schema migrations — in `match_data_manager.py` itself.

## Do not

- Do not place ML model weights here (those go under `Programma_CS2_RENAN/models/`).
- Do not duplicate query helpers from `match_data_manager.py`.
- Do not break the package contract — `__init__.py` must remain importable even when empty.

## Related

- Match data manager: `backend/storage/match_data_manager.py`
- Storage layer overview: `backend/storage/README.md`
- Training data fetching: `backend/nn/training_orchestrator.py:_fetch_batches()`
