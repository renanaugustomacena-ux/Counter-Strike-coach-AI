# Demo Ingestion Pipelines

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Demo ingestion infrastructure for professional and user CS2 demos with Steam integration, integrity validation, and round-level statistical enrichment.

## Directory Structure

```
ingestion/
├── __init__.py
├── demo_loader.py          # Main demo loading orchestrator
├── integrity.py            # Demo file integrity validation
├── steam_locator.py        # Steam installation discovery
├── cache/                  # Parsed demo cache (.mcn files)
├── pipelines/              # Ingestion pipeline implementations
│   ├── user_ingest.py      # User demo ingestion pipeline
│   └── json_tournament_ingestor.py  # Tournament JSON batch import
└── registry/               # Demo file tracking and lifecycle
    ├── lifecycle.py         # Demo lifecycle state machine
    ├── registry.py          # Demo file registry
    └── schema.sql           # Registry database schema
```

## Core Components

### Main Orchestrators

**`demo_loader.py`** — Main demo loading orchestrator
- Coordinates demo file parsing with demoparser2
- Integrity validation via `integrity.py`
- Delegates to pipeline implementations based on demo source
- Progress tracking and error recovery

**`steam_locator.py`** — Steam installation discovery
- Multi-platform CS2 installation detection (Windows, Linux, macOS)
- Registry parsing (Windows) and filesystem scanning
- Demo folder auto-detection

**`integrity.py`** — Demo file integrity validation
- File format verification (PBDEMS2 magic bytes)
- Header parsing and size validation
- Corruption detection

## Sub-Packages

### `pipelines/`

**`user_ingest.py`** — User demo ingestion pipeline
- Parses user demos via demoparser2
- Extracts round statistics with `round_stats_builder.py`
- Enriches with `enrich_from_demo()` (noscope/blind kills, flash assists, utility usage)
- Persists to RoundStats + PlayerMatchStats tables

**`json_tournament_ingestor.py`** — Tournament JSON batch ingestion
- Bulk import from tournament data exports
- Schema validation
- Conflict resolution

### `registry/`

Demo file registry and lifecycle management.

**`registry.py`** — Demo file tracking
- Tracks demo processing state (pending, processing, completed, failed)
- Duplicate detection via file hash
- Query interface for demo status

**`lifecycle.py`** — Demo lifecycle state machine
- State transitions for demo processing
- Retention policy enforcement
- Cleanup automation

**`schema.sql`** — Registry database schema definition

### `cache/`

Parsed demo cache directory. Stores `.mcn` intermediate files to avoid re-parsing previously processed demos.

## Important Notes

- **HLTV scraping** lives in `backend/data_sources/hltv/`, NOT in this package
- The main ingestion orchestrator function `_ingest_single_demo()` lives in `run_ingestion.py` at the package root
- Pro demo ingestion uses the same core pipeline as user demos, with additional statistical enrichment
- Demo discovery and batch processing is handled by `batch_ingest.py` at the project root
