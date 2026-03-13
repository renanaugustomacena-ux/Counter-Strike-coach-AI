# GitHub Actions - CI/CD Configuration

> **[English](ABOUT_CICD.md)** | **[Italiano](ABOUT_CICD_IT.md)** | **[Português](ABOUT_CICD_PT.md)**

This directory contains the GitHub Actions CI/CD pipeline for the Macena CS2 Analyzer project.

## Pipeline Overview

The pipeline runs on **every push and pull request**, validating code quality across both Linux and Windows platforms. The final distribution build targets Windows (where CS2 players are).

**Workflow file:** [`.github/workflows/build.yml`](workflows/build.yml)

## Pipeline Stages

```
lint ──┬── test (Ubuntu + Windows) ── integration (Ubuntu + Windows) ──┐
       │                                                                ├── build-distribution (Windows, main only)
       ├── security ───────────────────────────────────────────────────┘
       └── type-check (informational, non-blocking)
```

### Stage 1: Lint & Format Check
- **Runner:** Ubuntu
- Pre-commit hooks, Black formatting, isort import ordering

### Stage 2: Unit Tests + Coverage
- **Runner:** Ubuntu + Windows (matrix)
- pytest with coverage tracking (30% threshold)
- Coverage reports uploaded as artifacts

### Stage 3: Integration
- **Runner:** Ubuntu + Windows (matrix)
- Headless validator (23-phase gate)
- Cross-module consistency checks (METADATA_DIM, PlayerRole)
- Portability tests
- Integrity manifest verification

### Stage 4: Security Scan
- **Runner:** Ubuntu (parallel with tests)
- Bandit security linter (MEDIUM+ severity)
- detect-secrets for hardcoded credentials

### Stage 4b: Type Check
- **Runner:** Ubuntu (informational, non-blocking)
- mypy static type analysis

### Stage 5: Build Distribution
- **Runner:** Windows (main branch only, after all gates pass)
- PyInstaller executable build
- Post-build integrity audit
- Artifact upload (30-day retention)

## Supply Chain Security

All GitHub Actions are **SHA-pinned** (not tag-referenced) to prevent supply chain attacks:
- `actions/checkout` — pinned to v4 SHA
- `actions/setup-python` — pinned to v5 SHA
- `actions/upload-artifact` — pinned to v4 SHA

## Cross-Platform Strategy

| Platform | Dependencies | Purpose |
|----------|-------------|---------|
| Linux | `requirements.txt` + CPU PyTorch index | Development + CI validation |
| Windows | `requirements-ci.txt` (lock file) | Reproducible builds + distribution |

## Documentation

- **[CICD_GUIDE.md](CICD_GUIDE.md)** — Detailed pipeline guide with local testing, troubleshooting, and workflow triggers
