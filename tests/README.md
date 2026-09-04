> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Root-Level Verification and Forensic Tests

> **Authority:** Rule 3 (Zero-Regression)
> **Skill:** `/correctness-check`

Root-level verification and forensic tests for critical system components of the Macena CS2 Analyzer. These tests complement the main test suite in `Programma_CS2_RENAN/tests/` with higher-level, integration-focused verification that operates on real production-like data.

## Directory Structure

```
tests/
├── conftest.py                        # Root-level pytest path setup
├── test_coach_answer_eval.py          # coach_answer_eval scoring-layer tests
├── test_d3_rederive.py                # d3_recover_shard_metadata --rederive-v1 tests
├── test_eval_harness.py               # eval_harness helpers + CLI tests
├── test_lock_files.py                 # core.lock_files acquire/release/reclaim tests
├── test_lock_release_ownership.py     # F-0009 foreign-lock release regression tests
├── test_rescrape_placeholder_pros.py  # rescrape_placeholder_pros tool tests
├── test_single_instance_posix.py      # F-0010 POSIX single-instance regression tests
├── test_sync_pro_players.py           # sync_pro_players stale-count/purge tests
├── verify_chronovisor_logic.py        # Chronovisor signal-processing verification
├── verify_chronovisor_real.py         # Chronovisor with real database data
├── verify_csv_ingestion.py            # CSV ingestion result verification
├── verify_map_integration.py          # State reconstruction and metadata features
├── verify_reporting.py                # Reporting pipeline (heatmaps, generator)
├── verify_superposition.py            # Superposition network verification
├── setup_golden_data.py               # Golden test data setup
└── forensics/                         # Debug and diagnostic scripts
    ├── check_db_status.py             # Database content and task-status counts
    ├── check_failed_tasks.py          # Ingestion task failure analysis
    ├── debug_env.py                   # Python environment debugging
    ├── debug_nade_cols.py             # Grenade event column debugging
    ├── debug_parser_fields.py         # Demo parser field validation
    ├── test_forensic_parser.py        # Real-demo parser integration test
    ├── probe_missing_tables.py        # Actual DB schema dump
    ├── test_skill_logic.py            # SkillLatentModel unit tests
    ├── verify_map_dimensions.py       # Radar image dimension check
    └── verify_spatial_integrity.py    # Spatial projection consistency
```

## Test Categories

### Pytest Suites (`test_*.py`)

Conventional pytest suites for the root-level tools and core utilities:

| Test File | What It Tests |
|-----------|---------------|
| `test_coach_answer_eval.py` | `tools/coach_answer_eval.py` pure scoring layer: Unicode normalization, token-coverage fact matching, all/any/cluster check modes (no DB, no LLM) |
| `test_d3_rederive.py` | `tools/d3_recover_shard_metadata.py --rederive-v1` tick-rate re-derivation |
| `test_eval_harness.py` | `tools/eval_harness.py` pure helpers + CLI entrypoint (live-DB smoke behind `CS2_INTEGRATION_TESTS=1`) |
| `test_lock_files.py` | `core.lock_files` acquire / release / dead-PID reclaim / signal handling |
| `test_lock_release_ownership.py` | F-0009 regression: `core.lock_files.release()` must never remove a foreign live lock (D-track / HLTV-track mutual exclusion) |
| `test_rescrape_placeholder_pros.py` | `tools/rescrape_placeholder_pros.py` listing, URLs, dry-run (stubbed fetcher, no network) |
| `test_single_instance_posix.py` | F-0010 regression: POSIX single-instance enforcement in `core.lifecycle` is real (no unconditional pass off-Windows) |
| `test_sync_pro_players.py` | `tools/sync_pro_players.py` stale-count and purge logic (in-memory SQLite) |

Two more pytest suites live in `forensics/` and are collected by the same `test_*.py` pattern: `test_forensic_parser.py` (integration-marked, gated behind `CS2_INTEGRATION_TESTS=1`) and `test_skill_logic.py`.

### Verification Tests

These tests verify critical system behavior using real data:

| Test File | What It Verifies | Data Required |
|-----------|-----------------|---------------|
| `verify_chronovisor_logic.py` | `ChronovisorScanner` signal processing: spike detection, mistake (drop) detection, Gaussian-noise tolerance | None (synthetic signals) |
| `verify_chronovisor_real.py` | `ChronovisorScanner` on a real player timeline pulled from the match database | Database with ingested match ticks |
| `verify_csv_ingestion.py` | Presence of ingested external stats (`Ext_TeamRoundStats`, `Ext_PlayerPlaystyle`) in the database | Database populated by CSV ingestion |
| `verify_map_integration.py` | `RAPStateReconstructor` + FeatureExtractor: METADATA_DIM consistency, belief-tensor keys/shapes, metadata feature spot-checks | None (mock ticks) |
| `verify_reporting.py` | `MatchVisualizer` heatmap rendering from real match positions; `MatchReportGenerator` instantiation | Database with match data |
| `verify_superposition.py` | `SuperpositionLayer` forward pass and context adaptation; full `RAPCoachModel` forward (output heads and shapes) | None (synthetic tensors) |
| `setup_golden_data.py` | Creates the golden regression snapshot: parses ticks + events from a reference demo into `golden_data/golden.db` | Demo at `tests/golden_data/golden.dem` |

### Forensic Scripts

The `forensics/` subdirectory contains diagnostic scripts for investigating specific issues:

| Script | Purpose |
|--------|---------|
| `check_db_status.py` | Counts user vs pro `PlayerMatchStats` rows and `IngestionTask` statuses, samples failed tasks |
| `check_failed_tasks.py` | Queries `IngestionTask` table for failed tasks with error details (capped at 500) |
| `debug_env.py` | Dumps Python interpreter info and `sys.path`, probes legacy Kivy/KivyMD imports |
| `debug_nade_cols.py` | Prints the columns demoparser2 returns for grenade events (`smokegrenade_detonate`, `grenade_thrown`) on the first available pro demo |
| `debug_parser_fields.py` | Tests which demoparser2 tick fields parse successfully on a locally available demo |
| `test_forensic_parser.py` | Pytest integration test (`@pytest.mark.integration`, needs `CS2_INTEGRATION_TESTS=1`): extracts and aggregates player stats from a real pro demo |
| `probe_missing_tables.py` | Dumps actual database tables and columns via the SQLAlchemy inspector |
| `test_skill_logic.py` | Pytest unit tests for `SkillAxes` / `SkillLatentModel` (beginner vs pro levels, one-hot skill tensors) |
| `verify_map_dimensions.py` | Checks every `SPATIAL_REGISTRY` map has a 1024x1024 radar image in `PHOTO_GUI/maps/` |
| `verify_spatial_integrity.py` | Validates the `core.spatial_data` world-to-radar projection against hand-computed Mirage T-Spawn coordinates |

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
| Test count | 25 scripts (8 test + 6 verify + setup + 10 forensics) | 166 `test_*.py` files |
| Data | Real demos, production DB (verify/forensics); mocks (test_*) | In-memory DB, mocks, fixtures |
| Framework | pytest + standalone scripts | pytest with rich fixture ecosystem |
| Run frequency | CI on every push (`test_*.py`); on demand (verify/forensics) | CI on every push (`build.yml`) |

## Running Tests

```bash
# Activate virtual environment
source /home/renan/.venvs/cs2analyzer/bin/activate

# Run the pytest suites (test_*.py, including forensics/)
python -m pytest tests/ -v

# Include the live-DB / real-demo smoke tests
CS2_INTEGRATION_TESTS=1 python -m pytest tests/ -v

# Run a specific verification script directly
python tests/verify_chronovisor_real.py

# Run forensic diagnostics
python tests/forensics/check_db_status.py

# Setup golden data for regression testing
python tests/setup_golden_data.py
```

Note: pytest only collects `test_*.py` files (per `pytest.ini`) — the `verify_*` scripts and `setup_golden_data.py` must be run directly.

## Development Notes

- The `test_*.py` suites run in CI on every push (`build.yml` runs `pytest Programma_CS2_RENAN/tests/ tests/`); integration-marked tests run in a separate CI tier (`-m "integration and not slow"`)
- The `verify_*` and forensic scripts are NOT part of any automated gate — they require real data that may not be available in CI
- Golden data snapshots should be regenerated after major ingestion pipeline changes
- Forensic scripts are meant for interactive debugging, not automated testing — they report to stdout rather than enforcing a strict exit-code contract
- When adding a new verification test, follow the `verify_*.py` naming convention
- The main test suite (`Programma_CS2_RENAN/tests/`) is the primary regression gate
