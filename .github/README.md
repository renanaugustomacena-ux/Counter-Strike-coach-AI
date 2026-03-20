# .github — CI/CD Pipeline & GitHub Configuration

> **Authority:** Rule 7 (CI/CD & Release Engineering), Rule 5 (Security)

This directory contains the GitHub Actions CI/CD pipeline and its documentation. The pipeline enforces code quality, security, and cross-platform compatibility on every push.

## File Inventory

| File | Purpose |
|------|---------|
| `workflows/build.yml` | Main CI/CD pipeline definition (383 lines) |
| `ABOUT_CICD.md` | Pipeline overview (English) |
| `ABOUT_CICD_IT.md` | Pipeline overview (Italian) |
| `ABOUT_CICD_PT.md` | Pipeline overview (Portuguese) |
| `CICD_GUIDE.md` | Detailed technical guide |

## Pipeline Architecture

```
Push / PR
    │
    ├── Stage 1: LINT (Ubuntu, ~1 min)
    │       └── pre-commit run --all-files
    │
    ├── Stage 2: TEST (Ubuntu + Windows matrix, ~3 min)
    │       └── pytest --cov-fail-under=30
    │
    ├── Stage 3: INTEGRATION (Ubuntu + Windows matrix, ~5 min)
    │       ├── headless_validator.py (23-phase gate)
    │       ├── Cross-module consistency (METADATA_DIM == INPUT_DIM)
    │       ├── Portability tests
    │       └── Integrity manifest verification
    │
    ├── Stage 4a: SECURITY (Ubuntu, ~2 min)
    │       ├── Bandit (SAST, MEDIUM+ severity)
    │       ├── detect-secrets
    │       └── pip-audit (CVE scanning)
    │
    ├── Stage 4b: TYPE-CHECK (Ubuntu, non-blocking)
    │       └── mypy --ignore-missing-imports
    │
    └── Stage 5: BUILD-DISTRIBUTION (Windows, main branch only, ~15 min)
            ├── Validate critical data files
            ├── PyInstaller build
            ├── Post-build audit (audit_binaries.py)
            └── Upload artifact (30-day retention)
```

### Job Dependencies

```
lint ──┬── test ──┬── integration ──┬── build-distribution (main only)
       │          │                 │
       └── security ────────────────┘
       │
       └── type-check (non-blocking, informational)
```

## Triggers

| Trigger | Branches | Paths Ignored |
|---------|----------|---------------|
| Push | `main`, `develop`, `feature/**`, `fix/**` | `*.md`, `docs/`, `.github/`, `LICENSE`, `.gitignore` |
| Pull Request | `main`, `develop` | Same as above |

**Concurrency:** One pipeline per branch. New pushes cancel in-progress runs.

## Cross-Platform Strategy

| Platform | Dependencies | PyTorch |
|----------|-------------|---------|
| Ubuntu | `requirements.txt` + SDL2 libs | CPU-only (pip index) |
| Windows | `requirements-ci.txt` (lock file) | CPU-only (pip index) |

## Security Measures

All GitHub Actions are **SHA-pinned** (not tag-referenced) to prevent supply-chain attacks:

```yaml
actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5     # v4
actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5
actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4
actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830         # v4
```

**Permissions:** Least-privilege (`contents: read`), overridden per job as needed.

## Integration Tests

The integration stage runs critical cross-module consistency checks:

```python
# Verify METADATA_DIM == INPUT_DIM (prevents training/inference skew)
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.backend.nn.config import INPUT_DIM
assert METADATA_DIM == INPUT_DIM

# Verify PlayerRole canonical enum is consistent
from Programma_CS2_RENAN.core.app_types import PlayerRole as canonical
```

## Artifacts Produced

| Artifact | Stage | Retention | Content |
|----------|-------|-----------|---------|
| Coverage report | test | 30 days | `coverage.xml` |
| Build Health Report | integration | 30 days | `Build_Health_Report.json` |
| Bandit report | security | 30 days | `bandit-report.json` |
| pip-audit report | security | 30 days | `pip-audit-report.txt` |
| Windows distribution | build | 30 days | `dist/Macena_CS2_Analyzer/` |

## Local Validation

Before pushing, run these locally to catch issues early:

```bash
# 1. Pre-commit hooks (same as Stage 1)
pre-commit run --all-files

# 2. Tests (same as Stage 2)
pytest Programma_CS2_RENAN/tests/ tests/ --cov=Programma_CS2_RENAN --cov-fail-under=30 -v

# 3. Headless validator (same as Stage 3)
python tools/headless_validator.py

# 4. Portability test
python tools/portability_test.py
```

## Development Notes

- **Do NOT reference Actions by tag** (e.g., `@v4`) — always use full SHA for supply-chain security
- The `type-check` job has `continue-on-error: true` — it's informational, not blocking
- `build-distribution` only runs on `main` branch pushes (not PRs or feature branches)
- Environment variables set in all jobs: `CI=true`, `VIRTUAL_ENV=ci`, `KIVY_NO_ARGS=1`
- Python version is pinned to 3.10 across all jobs
- Windows tests use a reproducible lock file (`requirements-ci.txt`) for deterministic builds
