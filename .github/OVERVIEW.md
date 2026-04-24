> **[English](OVERVIEW.md)** | **[Italiano](OVERVIEW_IT.md)** | **[Portugues](OVERVIEW_PT.md)**

# .github — CI/CD Pipeline and GitHub Configuration

> **Authority:** Rule 7 (CI/CD & Release Engineering), Rule 5 (Security)

This directory contains the GitHub Actions CI/CD pipeline and related configuration. The pipeline ensures code quality, security, and cross-platform compatibility on every push.

## File Inventory

| File | Purpose |
|------|---------|
| `workflows/build.yml` | Main CI/CD pipeline definition |
| `ABOUT_CICD.md` | Pipeline overview (English) |
| `ABOUT_CICD_IT.md` | Pipeline overview (Italian) |
| `ABOUT_CICD_PT.md` | Pipeline overview (Portuguese) |
| `CICD_GUIDE.md` | Detailed technical guide |
| `PIPELINE.md` | Pipeline architecture documentation |
| `dependabot.yml` | Dependabot configuration for dependency updates |
| `pull_request_template.md` | PR template |
| `ISSUE_TEMPLATE/bug_report.md` | Bug report issue template |
| `ISSUE_TEMPLATE/feature_request.md` | Feature request issue template |

## Pipeline Architecture

```
Push / PR
    |
    +-- Stage 1: LINT (Ubuntu, ~1 min)
    |       +-- pre-commit run --all-files
    |
    +-- Stage 2: TEST (matrix Ubuntu + Windows, ~3 min)
    |       +-- pytest --cov-fail-under=33
    |
    +-- Stage 3: INTEGRATION (matrix Ubuntu + Windows, ~5 min)
    |       +-- headless_validator.py (313 checks, 24 phases)
    |       +-- Cross-module consistency (METADATA_DIM == INPUT_DIM)
    |       +-- Portability tests
    |       +-- Integrity manifest verification
    |
    +-- Stage 4a: SECURITY (Ubuntu, ~2 min)
    |       +-- Bandit (SAST, severity MEDIUM+)
    |       +-- detect-secrets
    |       +-- pip-audit (CVE scan)
    |
    +-- Stage 4b: TYPE-CHECK (Ubuntu, non-blocking)
    |       +-- mypy --ignore-missing-imports
    |
    +-- Stage 5: BUILD-DISTRIBUTION (Windows, main branch only, ~15 min)
            +-- Critical data file validation
            +-- PyInstaller build
            +-- Post-build audit (audit_binaries.py)
            +-- Artifact upload (30-day retention)
```

### Job Dependencies

```
lint --+-- test --+-- integration --+-- build-distribution (main only)
       |          |                 |
       +-- security ----------------+
       |
       +-- type-check (non-blocking, informational)
```

## Triggers

| Trigger | Branches | Ignored Paths |
|---------|----------|---------------|
| Push | `main`, `develop`, `feature/**`, `fix/**` | `*.md`, `docs/`, `.github/`, `LICENSE`, `.gitignore` |
| Pull Request | `main`, `develop` | Same as above |

**Concurrency:** One pipeline per branch. New pushes cancel in-progress runs.

## Cross-Platform Strategy

| Platform | Dependencies | PyTorch |
|----------|-------------|---------|
| Ubuntu | `requirements.txt` + SDL2 libraries | CPU-only (pip index) |
| Windows | `requirements-ci.txt` (lock file) | CPU-only (pip index) |

## Security Measures

All GitHub Actions are **pinned by SHA** (not referenced by tag) to prevent supply-chain attacks.

**Permissions:** Least privilege (`contents: read`), overridden per-job when necessary.

## Local Validation

Before pushing, run these commands locally to catch issues early:

```bash
# 1. Pre-commit hooks (like Stage 1)
pre-commit run --all-files

# 2. Tests (like Stage 2)
pytest Programma_CS2_RENAN/tests/ tests/ --cov=Programma_CS2_RENAN --cov-fail-under=33 -v

# 3. Headless validator (like Stage 3)
python tools/headless_validator.py

# 4. Portability tests
python tools/portability_test.py
```

## Development Notes

- Do NOT reference Actions by tag — always use full SHA for supply-chain security
- The `type-check` job has `continue-on-error: true` — informational, not blocking
- `build-distribution` only runs on pushes to the `main` branch
- Python version is pinned to 3.10 across all jobs
