> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Root-Level Project Tools

> **Authority:** Rule 3 (Zero-Regression), Rule 6 (Change Governance)
> **Skill:** `/validate`, `/pre-commit`

Root-level project tools for validation, diagnostics, build orchestration, and maintenance of the Macena CS2 Analyzer. The most critical tool is `headless_validator.py`, which is the mandatory pre-commit regression gate.

## File Inventory

The directory holds **49 Python tools** plus the `fuzz/` harness ([README](fuzz/README.md)) and `hltv_stealth_init.js` (browser stealth snippet for HLTV fetching). The most important ones:

| File | Purpose | Category |
|------|---------|----------|
| `headless_validator.py` | Regression gate with 42 distinct check phases | Validation |
| `dead_code_detector.py` | Orphan modules, duplicate definitions, stale imports | Validation |
| `verify_all_safe.py` | Safety verification across all modules | Validation |
| `portability_test.py` | Cross-platform portability checks | Validation |
| `Feature_Audit.py` | Feature alignment audit (parser vs ML pipeline) | Validation |
| `run_console_boot.py` | Console boot verification | Validation |
| `verify_main_boot.py` | Main application boot verification | Validation |
| `build_pipeline.py` | Build pipeline orchestration (5 stages) | Build |
| `audit_binaries.py` | Post-build binary integrity (SHA-256) | Build |
| `db_health_diagnostic.py` | Database health diagnostic (10 sections) | Database |
| `migrate_db.py` | DEPRECATED pre-Alembic patcher (use `alembic upgrade head`) | Database |
| `reset_pro_data.py` | Reset professional player data (idempotent) | Database |
| `dev_health.py` | Development health orchestrator | Maintenance |
| `Sanitize_Project.py` | Project sanitization (remove local data) | Maintenance |
| `observe_training_cycle.py` | Training metrics monitoring | Observability |
| `test_rap_lite.py` | RAP model lite testing | Testing |
| `test_tactical_pipeline.py` | Tactical inference pipeline testing | Testing |
| `validate_coaching_pipeline.py` | End-to-end coaching pipeline validation | Testing |

## `headless_validator.py` --- The Regression Gate

This is the single most important tool in the project (~2,900 lines). It runs **42 distinct check phases** (banner phases numbered 1–26 — Phase 19 is unused — plus lettered sub-phases 3b–3l and 6b–6f and a table-driven Contract phase) and must exit with code 0 before any commit. It is also wired as a pre-commit hook.

### Validation Phases

| Phase | What It Checks |
|-------|---------------|
| 1. Environment | Project root and critical directories exist |
| 2. Core Imports | Core modules import without errors |
| 3, 3b–3l. Backend Imports | Per-package import health: storage, processing, NN, analysis, coaching, services, knowledge, control, data sources, ingestion & onboarding, ingestion pipelines, reporting & observability |
| 4. Database Schema | In-memory database schema matches SQLModel definitions |
| 5. Config & Data Files | `map_config.json` valid, `get_setting()` types, METADATA_DIM==25, feature alignment |
| 6. ML Smoke | Model instantiation and forward pass |
| 6b–6f. Smoke Sub-phases | Baselines, demo format adapter, GPU detection, training pipeline, coaching pipeline |
| 7. UI Components (Headless) | Qt/PySide6 components import headlessly |
| 8. Cross-Platform | OS-specific code paths resolve |
| 9. Cross-Module Contracts | Public API contracts match implementations |
| 10. Deep ML Invariants | METADATA_DIM=25, OUTPUT_DIM=10, layer shapes |
| 11. Database Model Integrity | Table registry, columns, indexes |
| 12. Code Quality Scanning | Anti-pattern detection (incl. stray `print()`) |
| 13. Package Structure & Config | `__init__.py` in all packages, config integrity |
| 14. Feature Pipeline Consistency | Vectorizer produces 25-dim vectors |
| 15. Dependency & Environment | Pinned dependencies importable |
| 16. RAP Coach & Perception | RAP model forward pass and pipeline |
| 17. Belief Model & Analysis Engines | Analysis engine contracts, probability ranges |
| 18. MLControlContext & Training Control | Pause/resume/stop plumbing |
| 20. Shared Utilities | Shared utility and missing-module imports |
| 21. Integrity & Security Scanning | SHA-256 manifest, no hardcoded secrets |
| 22. Configuration Consistency | Settings file schema matches expected keys |
| 23. Advanced Code Quality | Cyclomatic complexity, duplicate code detection |
| 24. Qt Frontend Imports | Qt app screens/viewmodels import |
| 25. Design Token Freshness | Generated design tokens up to date |
| 26. Web Marquee Scaffold Health | Web app scaffold integrity |

### Usage

```bash
# Standard validation (mandatory before every commit)
python tools/headless_validator.py

# Exit code: 0 = all checks pass, non-zero = failures detected
echo $?
```

## Build Pipeline

### `build_pipeline.py` --- 5-Stage Build Orchestration

```
Stage 1: Sanitize  ->  Stage 2: Test  ->  Stage 3: Manifest  ->  Stage 4: Compile  ->  Stage 5: Audit
(clean artifacts)     (run test suite)   (generate hashes)    (PyInstaller)        (verify binary)
```

### `audit_binaries.py` --- Post-Build Integrity

Computes SHA-256 hashes of all files in the build output and compares against expected values. Detects tampering or incomplete builds.

## Database Tools

### `db_health_diagnostic.py` --- 10-Section Diagnostic

| Section | What It Checks |
|---------|---------------|
| 1 | Structural health — schema & constraints |
| 2 | Integrity check — corruption detection (`PRAGMA integrity_check`) |
| 3 | WAL & journal mode verification |
| 4 | Data consistency & logical stability (duplicates, orphans, impossible values) |
| 5 | Ingestion pipeline health (task status, stuck tasks, cross-DB) |
| 6 | Performance health — index coverage & query-plan full-scan check |
| 7 | Observability — diagnostic metadata coverage |
| 8 | HLTV pro statistics database |
| 9 | ML pipeline readiness — CoachState |
| 10 | Storage summary |

### `migrate_db.py` --- DEPRECATED

Retained only as a historical archive (R2-11). It patches pre-Alembic databases by adding 5 columns to `CoachState`; that schema is now managed by Alembic revisions `8c443d3d9523` and `3c6ecb5fe20e`. Use `alembic upgrade head` for all schema migrations.

### `reset_pro_data.py` --- Pro Data Reset

Multi-phase, idempotent reset for a fresh ingestion & training run. Clears `database.db` data tables + CoachState, `hltv_metadata.db` (skippable with `--preserve-hltv`), `knowledge_graph.db`, caches, model checkpoints, per-match shards, and sync state.

## Project Maintenance

### `dev_health.py` --- Health Orchestrator

Runs multiple tools in sequence and produces a unified health report:
1. Headless validator (always; `--quick` runs only this)
2. Dead code detector (`--strict`)
3. Feature alignment audit
4. Portability test

### `Sanitize_Project.py` --- Clean Local State

Removes all user-specific and local-only data for clean distribution:
- `Programma_CS2_RENAN/backend/storage/database.db` (main local database)
- `Programma_CS2_RENAN/backend/storage/hltv_metadata.db`
- `Programma_CS2_RENAN/backend/storage/match_data/` (per-match SQLite shards)
- `models/` (ML checkpoints)
- `logs/` directory
- stale `hltv_sync.pid`

## Usage

```bash
# Activate virtual environment
source /home/renan/.venvs/cs2analyzer/bin/activate

# Headless validation (run before every commit)
python tools/headless_validator.py

# Development health check
python tools/dev_health.py

# Database health check
python tools/db_health_diagnostic.py

# Portability check
python tools/portability_test.py

# Dead code detection
python tools/dead_code_detector.py

# Feature alignment audit
python tools/Feature_Audit.py

# Build pipeline
python tools/build_pipeline.py

# Project sanitization (WARNING: removes local data)
python tools/Sanitize_Project.py
```

## Development Notes

- All tools must be run from the project root directory
- The headless validator is the non-negotiable regression gate --- if it fails, the commit is blocked
- Database tools are safe to run on production data (they use read-only queries unless explicitly stated)
- `Sanitize_Project.py` is destructive --- it removes local databases and settings. Use with care.
- Tools exit with code 0 on success, non-zero on failure
- The `dev_health.py` orchestrator provides the most comprehensive single-command health check
