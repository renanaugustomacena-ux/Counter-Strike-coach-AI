# Ingestion Pipeline Implementations

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/ingestion/pipelines/`

## Introduction

This package contains the concrete ingestion pipelines that transform raw data
sources into structured database rows.  Each pipeline targets a specific input
format -- `.dem` replay files from user matches, `.dem` files from professional
matches, and structured JSON exports from tournament databases.  The pipelines
share a common seven-step flow (discovery, validation, parsing, enrichment,
persistence, registration, archival) but diverge in enrichment logic and
destination tables.

## File Inventory

| File | Purpose | Key Public API |
|------|---------|----------------|
| `__init__.py` | Package marker (empty) | -- |
| `user_ingest.py` | User demo ingestion pipeline | `ingest_user_demos(source_dir, processed_dir)` |
| `json_tournament_ingestor.py` | Tournament JSON batch processor | `process_tournament_jsons(json_dir, output_csv)` |
| `README.md` | Documentation (English) | -- |
| `README_IT.md` | Documentation (Italian) | -- |
| `README_PT.md` | Documentation (Portuguese) | -- |

## Architecture and Concepts

### The Seven-Step Ingestion Flow

Every pipeline follows this canonical sequence.  Steps may be implicit in
simpler pipelines but the logical order is always preserved:

1. **Discovery** -- scan the source directory for unprocessed files (`.dem` or
   `.json`).  The `DemoRegistry` from `ingestion/registry/` is consulted to
   skip already-ingested files.
2. **Validation** -- verify file integrity.  For `.dem` files this means
   checking the minimum file size (`MIN_DEMO_SIZE = 10 MB`, invariant DS-12).
   For JSON files the `_validate_tournament_json()` helper asserts required
   top-level keys (`id`, `slug`, `match_maps`) and per-map keys.
3. **Parsing** -- extract structured data.  Demo files are parsed by
   `backend/data_sources/demo_parser.parse_demo()` (backed by `demoparser2`).
   JSON files are loaded directly with Python `json.load()`.
4. **Enrichment** -- compute derived statistics.  User pipelines call
   `extract_match_stats()` from `base_features.py`.  Tournament pipelines
   compute per-round accuracy and economy rating inline.
5. **Persistence** -- write results to the database.  User pipelines upsert
   `PlayerMatchStats` rows via `DatabaseManager`.  Tournament pipelines write
   to CSV for downstream processing.
6. **Registration** -- mark the file as processed in the `DemoRegistry` so
   future runs skip it.
7. **Archival** -- move successfully ingested files to the `processed_dir`
   directory to keep the source directory clean.

### `user_ingest.py` in Detail

The user ingestion pipeline handles `.dem` files recorded from the local
player's CS2 matches.  It is the primary pipeline for personal coaching.

**Entry point:** `ingest_user_demos(source_dir: Path, processed_dir: Path)`

Internal flow:

1. Glob `source_dir` for `*.dem` files.
2. For each file, call `_process_single_user_demo()` which wraps the full
   pipeline in a try/except so one bad file does not abort the batch.
3. `parse_demo()` returns a `DataFrame` of round-level data.
4. `extract_match_stats()` aggregates into a flat stats dictionary.
5. A `PlayerMatchStats` ORM object is created with `is_pro=False` and the
   player name read from `get_setting("CS2_PLAYER_NAME")`.
6. `db_manager.upsert()` persists the row (insert or update on conflict).
7. `_trigger_ml_pipeline()` lazily imports `run_ml_pipeline` from
   `run_ingestion.py` to avoid circular imports, then executes the ML
   enrichment step (feature vectorisation, model inference).
8. `_archive_user_demo()` moves the file to `processed_dir` only after all
   previous steps succeeded (invariant R3-H03).

**Important limitation (F6-19):** This pipeline stores basic
`PlayerMatchStats` only.  `RoundStats`, events, and tick-level data require
the full enrichment path in `run_ingestion.py` (`enrich_from_demo()` and
`_extract_and_store_events()`).

### `json_tournament_ingestor.py` in Detail

The tournament JSON ingestor processes structured JSON exports that contain
match/map/round/team hierarchy.

**Entry point:** `process_tournament_jsons(json_dir: str, output_csv: str)`

Internal flow:

1. Glob `json_dir` for `*.json` files.
2. Each file is validated by `_validate_tournament_json()`.
3. The nested structure is flattened through a chain of extractors:
   `_extract_match_stats()` -> `_extract_map_stats()` ->
   `_extract_game_stats()` -> `_extract_round_stats()` ->
   `_build_flat_stat()`.
4. Numeric fields pass through `_safe_int()` (invariant DS-04) to handle
   None, strings, and other non-numeric JSON values.
5. Derived metrics are computed inline: `accuracy = hits / shots`,
   `econ_rating = damage / money_spent`.
6. The full list of flat stats is written to CSV via `pandas.DataFrame`.
7. Progress is logged every 100 files.

This pipeline is standalone: it can be run as `__main__` with hardcoded paths
pointing to `new_datasets/csgo_tournament_data/` and outputting to
`data/external/tournament_advanced_stats.csv`.

## Integration

### Upstream Dependencies

| Dependency | Module |
|------------|--------|
| Demo parser | `backend/data_sources/demo_parser.parse_demo()` |
| Feature extraction | `backend/processing/feature_engineering/base_features.extract_match_stats()` |
| Database singleton | `backend/storage/database.get_db_manager()` |
| ORM models | `backend/storage/db_models.PlayerMatchStats` |
| Configuration | `core/config.get_setting()` |
| Structured logging | `observability/logger_setup.get_logger()` |

### Downstream Consumers

- **`run_ingestion.py`** -- the orchestrator that calls `run_ml_pipeline()`
  after user demo ingestion.
- **`ingestion/registry/`** -- pipelines consult and update the demo registry.
- **`backend/nn/`** -- ML models consume the `PlayerMatchStats` rows produced
  by these pipelines.

## Development Notes

- **Error isolation:** Each file is processed inside its own try/except block.
  A corrupt demo does not abort the entire batch.
- **Lazy imports:** `_trigger_ml_pipeline()` uses a function-level import to
  break the circular dependency between `user_ingest` and `run_ingestion`.
- **Archival safety (R3-H03):** Files are moved to `processed_dir` only after
  all pipeline steps succeed.  If any step raises an exception, the file
  remains in the source directory for retry on the next run.
- **Thread safety:** The pipelines themselves are not thread-safe.  They are
  designed to be called from a single thread (the IngestionWatcher daemon).
  Cross-process safety is delegated to `DemoRegistry` via `FileLock`.
- **Structured logging:** All pipelines log via `get_logger("cs2analyzer.*")`
  with JSON format and correlation IDs for observability.
- **Invariant DS-04:** The `_safe_int()` helper in the tournament ingestor
  coerces all numeric fields safely, returning a default of `0` on failure.
- **Invariant DS-12:** Demo files smaller than `MIN_DEMO_SIZE` (10 MB) are
  rejected during validation.  Real CS2 demos are typically 50+ MB.
