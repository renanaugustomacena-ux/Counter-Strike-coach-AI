> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Validation and Diagnostic Tools

**Authority:** `Programma_CS2_RENAN/tools/` -- Package-level validation, diagnostic, and development utilities for the Macena CS2 Analyzer.

This directory contains internal tooling specific to the `Programma_CS2_RENAN` package. These
are distinct from the root-level `tools/` directory (which holds project-wide entry points like
`headless_validator.py` invoked by pre-commit hooks). The tools here form a 4-level validation
hierarchy that ensures system health from fast smoke checks through deep clinical diagnostics.
Every tool inherits from the shared `BaseValidator` ABC defined in `_infra.py`, producing
structured `ToolResult` / `ToolReport` objects with severity levels.

## Validation Hierarchy

The four levels are designed to be run in order of increasing depth and time cost:

| Level | Tool | Checks | Time | Purpose |
|-------|------|--------|------|---------|
| 1 | `headless_validator.py` | 319 across 24 phases | <20s | Fast regression gate (mandatory before task completion) |
| 2 | pytest suite | 1,515+ tests in 87 files | ~2min | Logic validation, contract assertions |
| 3 | `backend_validator.py` | 40 across 7 sections | ~30s | Build health, model zoo, coaching pipeline |
| 4 | `Goliath_Hospital.py` | 10 departments | ~60s | Comprehensive clinical diagnostic |

## File Inventory

| File | Category | Description |
|------|----------|-------------|
| `_infra.py` | Infrastructure | Shared infrastructure: path stabilization, `BaseValidator` ABC, `Console`, `ToolResult`, `ToolReport`, venv guard |
| `__init__.py` | Infrastructure | Package marker |
| `headless_validator.py` | Validation | Fast 7-phase regression gate (environment, core imports, backend imports, database schema, config loading, ML smoke, observability) |
| `backend_validator.py` | Validation | Backend health gate with 7 sections (environment, database, model zoo, analysis, coaching, resource integrity, service health) |
| `Goliath_Hospital.py` | Diagnostics | Hospital-style diagnostic suite with 10 departments (ER, Radiology, Pathology Lab, Cardiology, Neurology, Oncology, Pediatrics, ICU, Pharmacy, Tool Clinic) |
| `ui_diagnostic.py` | Diagnostics | Headless UI validation (resources, localization, assets, KV validation, spatial coordinates) |
| `Ultimate_ML_Coach_Debugger.py` | Diagnostics | Neural belief state and decision logic falsification tool; checks fidelity thresholds, stability probes, insight traceability |
| `build_tools.py` | Build | Consolidated build pipeline (lint, test, PyInstaller, hash verification, integrity manifest) |
| `context_gatherer.py` | Development | Relational context gatherer for a given file (imports, dependents, tests, API surface, git history) |
| `db_inspector.py` | Development | Database inspection CLI for full DB state without manual queries |
| `dead_code_detector.py` | Pre-commit | Orphan module detection, stale test import detection, empty package detection |
| `dev_health.py` | Pre-commit | Development health check with `--quick` (pre-commit, <10s) and `--full` (headless + backend) modes |
| `demo_inspector.py` | Development | Unified demo file inspection (events, fields, entity tracking); merges 7 legacy probe scripts |
| `project_snapshot.py` | Development | Compact project state snapshot (dependencies, git state, DB stats, environment) |
| `seed_hltv_top20.py` | Data | Seeds the HLTV metadata database with top-20 teams, players, and stat cards |
| `sync_integrity_manifest.py` | Pre-commit | Regenerates `core/integrity_manifest.json` from production `.py` file SHA-256 hashes |
| `user_tools.py` | User-facing | Consolidated interactive utilities (personalize, customize, manual-entry, weights, heartbeat) |
| `logs/` | Infrastructure | Tool execution logs |

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
| Emergency Room (ER) | Critical syntax and import issues |
| Radiology | Visual asset integrity scans |
| Pathology Lab | Data quality, mock vs real data detection |
| Cardiology | Core module health (DB, config, models) |
| Neurology | ML/AI system integrity |
| Oncology | Dead code, deprecated patterns, tech debt |
| Pediatrics | New and recently modified files |
| ICU | Integration tests, end-to-end flows |
| Pharmacy | Dependency health and version checks |
| Tool Clinic | Validates all project tool scripts |

## Pre-commit Integration

Three tools in this directory are invoked as pre-commit hooks:

1. **`dev_health.py --quick`** -- Import smoke test, DB alive check, config validation (<10s)
2. **`dead_code_detector.py`** -- Scans for orphan modules and stale test imports
3. **`sync_integrity_manifest.py`** -- Regenerates the RASP integrity manifest; exits 1 if
   the on-disk manifest diverges from computed hashes when run with `--verify-only`

The `headless_validator.py` is invoked post-task (not as a git hook) and must exit 0 before
any development task is considered complete.

## Usage

```bash
# Activate the virtual environment first
source ~/.venvs/cs2analyzer/bin/activate

# Headless validation (mandatory post-task gate)
python Programma_CS2_RENAN/tools/headless_validator.py

# Backend validation (model zoo, coaching pipeline, services)
python Programma_CS2_RENAN/tools/backend_validator.py

# Full Goliath Hospital diagnostic
python Programma_CS2_RENAN/tools/Goliath_Hospital.py

# Quick development health check (pre-commit)
python Programma_CS2_RENAN/tools/dev_health.py --quick

# Full development health check
python Programma_CS2_RENAN/tools/dev_health.py --full

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
- The `BaseValidator` pattern ensures every tool produces both human-readable console output
  and machine-readable JSON reports stored in `tools/logs/`.
- `Goliath_Hospital.py` uses `print()` for console output rather than structured logging. As
  a diagnostic tool (not a production service), this is acceptable -- all findings are captured
  in `DiagnosticFinding` objects with severity levels.
- `demo_inspector.py` consolidates 7 legacy probe scripts (`probe_demo_data`, `probe_entity_track`,
  `probe_events_advanced`, `probe_inventory`, `probe_stats_fields`, `probe_trajectories`,
  `probe_inv_direct`) into a single unified tool.
- `user_tools.py` consolidates 7 legacy interactive tools (`Manual_Data_v2`, `Personalize_v2`,
  `GUI_Master_Customizer`, `ML_Coach_Control_Panel`, `manage_sync`, `Seed_Pro_Data`,
  `Heartbeat_Monitor`) into subcommands of a single entry point.
