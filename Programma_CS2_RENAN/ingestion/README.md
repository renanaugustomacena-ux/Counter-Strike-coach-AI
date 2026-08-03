# Demo Ingestion Pipelines

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Demo ingestion infrastructure for professional and user CS2 demos with Steam integration, integrity validation, and round-level statistical enrichment.

## Directory Structure

```
ingestion/
├── __init__.py
├── demo_loader.py          # Three-pass demo parser with signed cache
├── integrity.py            # Demo file integrity validation
├── steam_locator.py        # Steam installation discovery
├── pipelines/              # Ingestion pipeline implementations
│   ├── user_ingest.py      # User demo ingestion pipeline
│   └── json_tournament_ingestor.py  # Tournament JSON batch import
└── registry/               # Demo file tracking and lifecycle
    ├── lifecycle.py         # Demo retention cleanup
    ├── registry.py          # Demo file registry
    └── schema.sql           # Reserved for a future SQL registry (currently empty)
```

## Core Components

### Main Orchestrators

**`demo_loader.py`** — `DemoLoader`, the three-pass demo parser
- Pass 1: player positions per tick; Pass 2: grenade events/trajectories; Pass 3: tick DataFrame → `DemoFrame` objects
- Parses via demoparser2; also extracts round starts, bomb events, and kill events
- Caches parsed results as HMAC-SHA256-signed pickle files (`.mcn`) in a `demo_cache/`
  directory (falls back to `ingestion/cache/`), created at runtime; loads use a
  restricted unpickler (DS-01) and verify the signature before deserializing

**`steam_locator.py`** — Steam installation discovery
- Multi-platform CS2 installation detection (Windows, Linux, macOS)
- Registry parsing (Windows) and filesystem scanning
- Demo folder auto-detection

**`integrity.py`** — Demo file integrity validation
- `validate_dem_file()` delegates to `backend/data_sources/demo_format_adapter`
  (PBDEMS2 magic bytes, size bounds; legacy CS:GO demos rejected)
- `compute_sha256()` helper for file hashing
- Legacy 50 KB / 900 MB size constants kept for backward compatibility only

## Sub-Packages

### `pipelines/`

**`user_ingest.py`** — User demo ingestion pipeline
- Parses user demos via demoparser2
- Persists PlayerMatchStats, then RoundStats + enrichment via
  `round_stats_builder.persist_round_stats_and_enrichment()`
- Triggers the ML pipeline (`run_ml_pipeline` from `run_ingestion.py`) and
  archives the demo only after all steps succeed

**`json_tournament_ingestor.py`** — Tournament JSON batch ingestion
- Bulk import from tournament data exports
- Schema validation (`_validate_tournament_json`)
- Flattens the match/map/round hierarchy to a CSV of per-round team stats

### `registry/`

Demo file registry and lifecycle management.

**`registry.py`** — `DemoRegistry`, JSON-backed processed-demo set
- `is_processed()` / `mark_processed()` with thread + file locking
- Atomic writes with automatic backup recovery

**`lifecycle.py`** — `DemoLifecycleManager`
- `cleanup_old_demos(days=30)` deletes archived `.dem` files past retention

**`schema.sql`** — Reserved for a future SQL-based registry (currently empty)

## Important Notes

- **HLTV scraping** lives in `backend/data_sources/hltv/`, NOT in this package
- The main ingestion orchestrator function `_ingest_single_demo()` lives in `run_ingestion.py` at the package root
- Pro demo ingestion uses the same core pipeline as user demos, with additional statistical enrichment
- Demo discovery and batch processing is handled by `batch_ingest.py` at the project root
