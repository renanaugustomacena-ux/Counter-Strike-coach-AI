> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Root-Level Verification and Forensic Tests

> **Authority:** Rule 3 (Zero-Regression)
> **Skill:** `/correctness-check`

Root-level verification and forensic tests for critical system components of the Macena CS2 Analyzer. These tests complement the main test suite in `Programma_CS2_RENAN/tests/` with higher-level, integration-focused verification that operates on real production-like data.

## Directory Structure

```
tests/
├── conftest.py                        # Root-level pytest path setup
├── test_d3_rederive.py                # d3_recover_shard_metadata --rederive-v1 tests
├── test_eval_harness.py               # eval_harness helpers + CLI tests
├── test_lock_files.py                 # core.lock_files acquire/release/reclaim tests
├── test_rescrape_placeholder_pros.py  # rescrape_placeholder_pros tool tests
├── test_sync_pro_players.py           # sync_pro_players stale-count/purge tests
├── verify_chronovisor_logic.py        # Chronovisor logic verification
├── verify_chronovisor_real.py         # Chronovisor with real demo data
├── verify_csv_ingestion.py            # CSV ingestion pipeline verification
├── verify_map_integration.py          # Map integration and spatial data
├── verify_reporting.py                # Reporting pipeline (PDF, charts)
├── verify_superposition.py            # Superposition network verification
├── setup_golden_data.py               # Golden test data setup
└── forensics/                         # Debug and diagnostic scripts
    ├── check_db_status.py             # Database connectivity diagnostics
    ├── check_failed_tasks.py          # Ingestion task failure analysis
    ├── debug_env.py                   # Environment variable debugging
    ├── debug_nade_cols.py             # Grenade column debugging
    ├── debug_parser_fields.py         # Demo parser field validation
    ├── test_forensic_parser.py        # Parser behavior investigation
    ├── probe_missing_tables.py        # Schema completeness check
    ├── test_skill_logic.py            # Skill system validation
    ├── verify_map_dimensions.py       # Map bounds verification
    └── verify_spatial_integrity.py    # Spatial data consistency
```

## Test Categories

### Pytest Suites (`test_*.py`)

Conventional pytest suites for the root-level tools and core utilities:

| Test File | What It Tests |
|-----------|---------------|
| `test_d3_rederive.py` | `tools/d3_recover_shard_metadata.py --rederive-v1` tick-rate re-derivation |
| `test_eval_harness.py` | `tools/eval_harness.py` pure helpers + CLI entrypoint (live-DB smoke behind `CS2_INTEGRATION_TESTS=1`) |
| `test_lock_files.py` | `core.lock_files` acquire / release / dead-PID reclaim / signal handling |
| `test_rescrape_placeholder_pros.py` | `tools/rescrape_placeholder_pros.py` listing, URLs, dry-run (stubbed fetcher, no network) |
| `test_sync_pro_players.py` | `tools/sync_pro_players.py` stale-count and purge logic (in-memory SQLite) |

### Verification Tests

These tests verify critical system behavior using real data:

| Test File | What It Verifies | Data Required |
|-----------|-----------------|---------------|
| `verify_chronovisor_logic.py` | Temporal scale detection, tick deduplication, replay interpolation | None (unit-level) |
| `verify_chronovisor_real.py` | Full Chronovisor pipeline with actual `.dem` files | Real demo files |
| `verify_csv_ingestion.py` | CSV import pipeline (external stats → database) | CSV files in `data/external/` |
| `verify_map_integration.py` | Map coordinate transforms, Z-cutoff handling, landmark resolution | `data/map_config.json` |
| `verify_reporting.py` | PDF generation, heatmap rendering, momentum charts | Database with match data |
| `verify_superposition.py` | SuperpositionLayer forward pass, gradient flow | None (synthetic tensors) |
| `setup_golden_data.py` | Creates reference data snapshots for regression testing | Database with match data |

### Forensic Scripts

The `forensics/` subdirectory contains diagnostic scripts for investigating specific issues:

| Script | Purpose |
|--------|---------|
| `check_db_status.py` | Tests database connectivity, WAL mode, table existence |
| `check_failed_tasks.py` | Queries `IngestionTask` table for failed tasks with error details |
| `debug_env.py` | Dumps environment variables relevant to the application |
| `debug_nade_cols.py` | Verifies grenade-related columns in tick data tables |
| `debug_parser_fields.py` | Validates demoparser2 field names against expected schema |
| `test_forensic_parser.py` | Deep investigation of parser behavior on specific demo files |
| `probe_missing_tables.py` | Compares SQLModel definitions against actual database schema |
| `test_skill_logic.py` | Validates coaching skill selection and weighting logic |
| `verify_map_dimensions.py` | Checks map bounds, scale factors, and coordinate ranges |
| `verify_spatial_integrity.py` | Cross-validates spatial data between `map_config.json` and `spatial_data.py` |

## `conftest.py` — Root Configuration

The root-level `conftest.py` is minimal — it injects the project root into `sys.path` so all imports resolve correctly:

```python
# Essentially the whole conftest.py
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))
```

## Test Philosophy

1. **Forensic approach** — tests investigate real data paths and actual system behavior, not synthetic mocks
2. **No synthetic data** — all tests use real demo files or production-equivalent data wherever possible
3. **Skip if unavailable** — tests skip gracefully (via `pytest.skip()`) when required data is missing
4. **End-to-end coverage** — focus on integration points and cross-module workflows
5. **Non-destructive** — tests never modify production databases or configuration files

## Relationship with Main Test Suite

| Aspect | `tests/` (root) | `Programma_CS2_RENAN/tests/` (main) |
|--------|-----------------|--------------------------------------|
| Focus | Tool tests, integration, forensics | Unit tests, module tests |
| Test count | 22 scripts (5 test + 6 verify + setup + 10 forensics) | 130 `test_*.py` files |
| Data | Real demos, production DB (verify/forensics); mocks (test_*) | In-memory DB, mocks, fixtures |
| Framework | pytest + standalone scripts | pytest with rich fixture ecosystem |
| Run frequency | On demand, debugging | Every commit (pre-commit hooks) |

## Running Tests

```bash
# Activate virtual environment
source /home/renan/.venvs/cs2analyzer/bin/activate

# Run all verification tests via pytest
python -m pytest tests/ -v

# Run a specific verification script directly
python tests/verify_chronovisor_real.py

# Run forensic diagnostics
python tests/forensics/check_db_status.py

# Setup golden data for regression testing
python tests/setup_golden_data.py
```

## Development Notes

- These tests are NOT part of the pre-commit gate — they require real data that may not be available in CI
- Golden data snapshots should be regenerated after major ingestion pipeline changes
- Forensic scripts are meant for interactive debugging, not automated testing
- When adding a new verification test, follow the `verify_*.py` naming convention
- All forensic scripts exit with code 0 on success, non-zero on failure
- The main test suite (`Programma_CS2_RENAN/tests/`) is the primary regression gate
