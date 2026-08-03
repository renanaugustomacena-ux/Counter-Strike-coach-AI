> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Validation and Diagnostic Tools

**Authority:** `Programma_CS2_RENAN/tools/` -- Package-level validation, diagnostic, and development utilities for the Macena CS2 Analyzer.

This directory contains internal tooling specific to the `Programma_CS2_RENAN` package. These
are distinct from the root-level `tools/` directory (which holds project-wide entry points like
`headless_validator.py` invoked by pre-commit hooks). Together with the root validator and the
pytest suite, the tools here form a 4-level validation hierarchy that ensures system health from
fast smoke checks through deep clinical diagnostics. The validators build on the shared
`BaseValidator` ABC defined in `_infra.py`, producing structured `ToolResult` / `ToolReport`
objects with severity levels.

## Validation Hierarchy

The four levels are designed to be run in order of increasing depth and time cost:

| Level | Tool | Checks | Purpose |
|-------|------|--------|---------|
| 1 | `tools/headless_validator.py` (project root) | 42 distinct check phases | Fast regression gate (mandatory before task completion) |
| 2 | pytest suite | 2,190+ tests in 130 files | Logic validation, contract assertions |
| 3 | `backend_validator.py` | 7 sections | Build health, model zoo, coaching pipeline |
| 4 | `Goliath_Hospital.py` | 11 departments | Comprehensive clinical diagnostic |

## File Inventory

| File | Category | Description |
|------|----------|-------------|
| `_infra.py` | Infrastructure | Shared infrastructure: path stabilization, `BaseValidator` ABC, `Console`, `ToolResult`, `ToolReport`, venv guard |
| `__init__.py` | Infrastructure | Package marker |
| `backend_validator.py` | Validation | Backend health gate with 7 sections (environment, database, model zoo, analysis, coaching, resource integrity, service health) |
| `Goliath_Hospital.py` | Diagnostics | Hospital-style diagnostic suite with 11 departments (ER, Radiology, Pathology, Cardiology, Neurology, Oncology, Pediatrics, ICU, Pharmacy, Tool Clinic, Endocrinology) |
| `ui_diagnostic.py` | Diagnostics | Headless UI validation (resources, localization, assets, KV validation, Qt frontend, spatial coordinates) |
| `Ultimate_ML_Coach_Debugger.py` | Diagnostics | Neural belief state and decision logic falsification tool; 9 audit phases (data fidelity, belief stability, insight traceability, model zoo, dimensions, data quality, weight health, convergence, maturity) |
| `aggregate_match_stats_sql.py` | Data | SQL-only PlayerMatchStats aggregator over `match_*.db` shards (no `.dem` required) |
| `build_tools.py` | Build | Consolidated build pipeline (lint, test, PyInstaller, hash verification, integrity manifest) |
| `context_gatherer.py` | Development | Relational context gatherer for a given file (imports, dependents, tests, API surface, git history) |
| `db_inspector.py` | Development | Database inspection CLI for full DB state without manual queries |
| `demo_inspector.py` | Development | Unified demo file inspection (events, fields, entity tracking); merges 7 legacy probe scripts |
| `migrate_hltv_schema_2026_05.py` | Data | Idempotent one-off migration extending the `hltv_metadata.db` schema (outside Alembic) |
| `project_snapshot.py` | Development | Compact project state snapshot (dependencies, git state, DB stats, environment) |
| `register_orphan_matches.py` | Data | Registration-only pass for orphan `match_*.db` files missing from `playermatchstats` |
| `repair_rating_scale.py` | Data | One-shot repair returning `rating_*` columns of `full_sql*` rows to RAW scale |
| `seed_hltv_top20.py` | Data | Seeds the HLTV metadata database with top-20 teams, players, and stat cards |
| `sync_integrity_manifest.py` | Pre-commit | Regenerates `core/integrity_manifest.json` from production `.py` file SHA-256 hashes |
| `user_tools.py` | User-facing | Consolidated interactive utilities (personalize, customize, manual-entry, weights, heartbeat) |

Note: `headless_validator.py`, `dev_health.py`, and `dead_code_detector.py` live in the
root-level `tools/` directory, not here.

## Shared Infrastructure (`_infra.py`)

All tools in this directory build on the shared infrastructure module `_infra.py`, which provides:

- **`path_stabilize()`** -- Canonical path setup; adds `PROJECT_ROOT` to `sys.path`, sets
  `KIVY_NO_ARGS=1`, configures UTF-8 encoding. Returns `(PROJECT_ROOT, SOURCE_ROOT)`.
- **`require_venv()`** -- Venv guard that exits if not in the `cs2analyzer` virtualenv
  (bypassed when `CI` is set).
- **`BaseValidator`** -- Abstract base class with `define_checks()`, `check()`, `run()`,
  `Console` integration, and JSON report generation.
- **`ToolResult`** / **`ToolReport`** -- Structured dataclasses for check results with
  `Severity` levels (CRITICAL, WARNING, INFO, OK).
- **`Console`** -- Rich-style terminal output with section headers, pass/fail indicators,
  and summary tables.

## Goliath Hospital Departments

The `Goliath_Hospital.py` diagnostic suite organizes checks into medical-themed departments:

| Department | Focus |
|------------|-------|
| Emergency Room (ER) | Syntax, forbidden patterns, namespace collisions |
| Radiology | Asset integrity (themes, map radars, models, layout) |
| Pathology | Data quality, mock vs real data detection |
| Cardiology | Core health (critical modules, DB, config, analysis engines) |
| Neurology | ML/AI system (delegates to `Ultimate_ML_Coach_Debugger`) |
| Oncology | Tech debt (deprecated patterns, commented code, long functions) |
| Pediatrics | Recently modified files |
| ICU | Integration (import chains, service instantiation) |
| Pharmacy | Dependency health and version checks |
| Tool Clinic | Validates all project tool scripts |
| Endocrinology | System integration (entry points, migrations, JSON configs) |

## Pre-commit Integration

One tool in this directory is invoked as a pre-commit hook:

1. **`sync_integrity_manifest.py --verify-only`** -- exits 1 if the on-disk RASP
   integrity manifest diverges from computed hashes (run without the flag to regenerate)

The other validation hooks (`headless_validator.py`, `dev_health.py --quick`,
`dead_code_detector.py`) run from the root-level `tools/` directory; the headless
validator is both a pre-commit hook and the mandatory post-task gate -- it must exit 0
before any development task is considered complete.

## Usage

```bash
# Activate the virtual environment first
source ~/.venvs/cs2analyzer/bin/activate

# Headless validation (mandatory post-task gate; lives in root tools/)
python tools/headless_validator.py

# Backend validation (model zoo, coaching pipeline, services)
python Programma_CS2_RENAN/tools/backend_validator.py

# Full Goliath Hospital diagnostic
python Programma_CS2_RENAN/tools/Goliath_Hospital.py

# Quick development health check (pre-commit; lives in root tools/)
python tools/dev_health.py --quick

# Full development health check
python tools/dev_health.py --full

# Database inspection
python Programma_CS2_RENAN/tools/db_inspector.py

# Demo file inspection
python Programma_CS2_RENAN/tools/demo_inspector.py all --demo path/to/file.dem

# Build pipeline
python Programma_CS2_RENAN/tools/build_tools.py build

# Project state snapshot
python Programma_CS2_RENAN/tools/project_snapshot.py

# Seed HLTV top-20 data
python -m Programma_CS2_RENAN.tools.seed_hltv_top20
```

## Development Notes

- All tools use `_infra.path_stabilize()` for consistent path resolution. Never manipulate
  `sys.path` directly in tool scripts.
- Exit codes are standardized: `0 = PASS`, `1 = FAIL`. Pre-commit hooks rely on this contract.
- The `BaseValidator` pattern ensures every tool produces human-readable console output
  and, with the `--json` flag, a machine-readable JSON report on stdout.
- `Goliath_Hospital.py` is a `BaseValidator` subclass (`GoliathHospital`); findings are
  captured as `ToolResult` entries with severity levels, and `--department` runs a single
  department in isolation.
- `demo_inspector.py` consolidates 7 legacy probe scripts (`probe_demo_data`, `probe_entity_track`,
  `probe_events_advanced`, `probe_inventory`, `probe_stats_fields`, `probe_trajectories`,
  `probe_inv_direct`) into a single unified tool.
- `user_tools.py` consolidates 7 legacy interactive tools (`Manual_Data_v2`, `Personalize_v2`,
  `GUI_Master_Customizer`, `ML_Coach_Control_Panel`, `manage_sync`, `Seed_Pro_Data`,
  `Heartbeat_Monitor`) into subcommands of a single entry point.
