> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Root-Level Project Tools

> **Authority:** Rule 3 (Zero-Regression), Rule 6 (Change Governance)
> **Skill:** `/validate`, `/pre-commit`

Root-level project tools for validation, diagnostics, build orchestration, and maintenance of the Macena CS2 Analyzer. The most critical tool is `headless_validator.py`, which is the mandatory pre-commit regression gate.

## File Inventory

| File | Purpose | Category |
|------|---------|----------|
| `headless_validator.py` | 291+ regression checks across 23 phases | Validation |
| `dead_code_detector.py` | Orphan modules, duplicate definitions, stale imports | Validation |
| `verify_all_safe.py` | Safety verification across all modules | Validation |
| `portability_test.py` | Cross-platform portability checks | Validation |
| `Feature_Audit.py` | Feature alignment audit (parser vs ML pipeline) | Validation |
| `run_console_boot.py` | Console boot verification | Validation |
| `verify_main_boot.py` | Main application boot verification | Validation |
| `build_pipeline.py` | Build pipeline orchestration (5 stages) | Build |
| `audit_binaries.py` | Post-build binary integrity (SHA-256) | Build |
| `db_health_diagnostic.py` | Database health diagnostic (10 sections) | Database |
| `migrate_db.py` | Database migration with backward compatibility | Database |
| `reset_pro_data.py` | Reset professional player data (idempotent) | Database |
| `dev_health.py` | Development health orchestrator | Maintenance |
| `Sanitize_Project.py` | Project sanitization (remove local data) | Maintenance |
| `observe_training_cycle.py` | Training metrics monitoring | Observability |
| `test_rap_lite.py` | RAP model lite testing | Testing |
| `test_tactical_pipeline.py` | Tactical inference pipeline testing | Testing |

## `headless_validator.py` --- The Regression Gate

This is the single most important tool in the project. It runs **291+ automated checks across 23 phases** and must exit with code 0 before any commit. It is also wired as a pre-commit hook.

### Validation Phases

| Phase | What It Checks |
|-------|---------------|
| 1. Import Health | All production modules import without errors |
| 2. Schema Integrity | In-memory database schema matches SQLModel definitions |
| 3. Config Loading | `get_setting()` and `get_credential()` resolve correctly |
| 4. ML Smoke Test | Model instantiation and forward pass for all 6 model types |
| 5. UI Framework | PySide6 and Kivy import successfully |
| 6. Platform Compat | OS-specific code paths resolve |
| 7. Contract Validation | Public API contracts match implementations |
| 8. ML Invariants | METADATA_DIM=25, INPUT_DIM=25, OUTPUT_DIM=10 |
| 9. DB Integrity | Table counts, foreign keys, index existence |
| 10. Code Quality | Black formatting, isort ordering |
| 11. Package Structure | `__init__.py` in all packages, no circular imports |
| 12. Feature Pipeline | FeatureExtractor produces 25-dim vectors |
| 13. RAP Forward Pass | RAP Coach model forward pass succeeds |
| 14. Belief Contracts | Belief model probability ranges [0, 1] |
| 15. Circuit Breakers | Error thresholds trigger correctly |
| 16. Integrity Manifest | SHA-256 hashes match `core/integrity_manifest.json` |
| 17. Security Scan | No hardcoded secrets or credentials |
| 18. Config Consistency | Settings file schema matches expected keys |
| 19. Advanced Quality | Cyclomatic complexity, duplicate code detection |
| 20-23. | Additional specialized checks |

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
| 1 | WAL mode verification on all 3 databases |
| 2 | Table existence and row counts |
| 3 | Foreign key constraint integrity |
| 4 | Index coverage on frequently queried columns |
| 5 | Data quality metrics (NaN rates, outliers) |
| 6 | Alembic migration state |
| 7 | Per-match database consistency |
| 8 | HLTV metadata completeness |
| 9 | Storage usage and file sizes |
| 10 | Connection pool health |

### `migrate_db.py` --- Safe Migration

Wraps Alembic migrations with backward compatibility checks. Safer than running `alembic upgrade head` directly.

### `reset_pro_data.py` --- Pro Data Reset

Multi-phase, idempotent reset of professional player data. Safe to run multiple times. Phases: backup -> clear tables -> reset sync state -> verify.

## Project Maintenance

### `dev_health.py` --- Health Orchestrator

Runs multiple tools in sequence and produces a unified health report:
1. Headless validator
2. Dead code detector
3. Portability test
4. Feature audit

### `Sanitize_Project.py` --- Clean Local State

Removes all user-specific and local-only files for clean distribution:
- `user_settings.json`
- `database.db` and WAL/SHM files
- `logs/` directory
- `__pycache__/` directories

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
