# Industry Standards Audit — Macena CS2 Analyzer

**Repository:** `https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI`
**Audit date:** 2026-03-20
**Auditor:** Claude (automated, full-codebase scan)
**Project version:** 1.0.0 (`pyproject.toml:12`)
**Python requirement:** `>=3.10` (`pyproject.toml:14`)
**License:** Dual — Proprietary (default) / Apache 2.0 (opt-in)

---

## Executive Summary

The repository demonstrates **professional-grade engineering** with an excellent CI/CD
pipeline, 78 test files, 46 documentation files in 3 languages, and robust security
scanning. However, **14 governance and community files** expected by industry standards
are missing. None of the gaps affect runtime quality — they affect **discoverability,
contributor experience, and enterprise readiness**.

| Area | Score | Notes |
|------|-------|-------|
| CI/CD | A+ | 6-stage, SHA-pinned, cross-platform (Ubuntu + Windows), security-hardened |
| Testing | A | 78 files, 6 pytest markers, `--strict-markers`, 30 s global timeout, 33% coverage gate |
| Documentation | A+ | 46 files, 6.8 MB, EN/IT/PT, 3-volume technical book, 16 research studies |
| Code quality | A | Black 24.1.1 + isort 5.13.2 (100-char), mypy 3.10, 14 pre-commit hooks |
| Security | A | Bandit MEDIUM+, detect-secrets, pip-audit `--strict`, SHA-pinned Actions |
| Package management | A | pyproject.toml (PEP 621), 3 lock files, 2 Alembic migrations, 63 dependencies |
| Governance & community | D | Missing CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, templates |
| Release management | C | No version tags, no CHANGELOG, no branch protection rules |
| Containerisation | C | docker-compose for FlareSolverr only; no Dockerfile for the app itself |

---

## 1. What Already Exists (strengths)

### 1.1 CI/CD Pipeline — `.github/workflows/build.yml` (393 lines)

**Workflow name:** `Macena CI Pipeline`

**Triggers:**
- Push to `main`, `develop`, `feature/**`, `fix/**`
- PR targeting `main` or `develop`
- Path ignores: `**.md`, `docs/**`, `.github/*.md`, `LICENSE`, `.gitignore`

**Global settings:**
- Permissions: `contents: read` (least-privilege)
- Concurrency: `ci-${{ github.ref }}`, `cancel-in-progress: true`
- Env: `PYTHON_VERSION: '3.10'`

**Stage dependency graph:**
```
lint (5 min) ──┬── test [ubuntu, windows] (15 min) ── integration [ubuntu, windows] (10 min) ──┐
               ├── security (10 min) ────────────────────────────────────────────────────────────┼── build-distribution (20 min, main only)
               └── type-check (10 min, non-blocking) ───────────────────────────────────────────┘
```

| Stage | Job name | Runner(s) | Timeout | Blocking | Key steps |
|-------|----------|-----------|---------|----------|-----------|
| 1. Lint | `lint` | ubuntu-latest | 5 min | Yes | pre-commit (SKIP: integrity-manifest-check, dev-health-quick) |
| 2. Test | `test` | ubuntu + windows | 15 min | Yes | pytest `--cov-fail-under=33 -x`, coverage.xml upload |
| 3. Integration | `integration` | ubuntu + windows | 10 min | Yes | headless-validator (23 phases, 2 min timeout), cross-module dim check (METADATA_DIM == INPUT_DIM), portability tests, integrity manifest |
| 4. Security | `security` | ubuntu-latest | 10 min | Yes | Bandit SAST (MEDIUM+, JSON report), detect-secrets, pip-audit `--strict` |
| 4b. Type-check | `type-check` | ubuntu-latest | 10 min | No | mypy `--ignore-missing-imports` (`continue-on-error: true`) |
| 5. Build | `build-distribution` | windows-latest | 20 min | — | PyInstaller → `packaging/cs2_analyzer_win.spec`, post-build `audit_binaries.py` |

**Artifacts (all 30-day retention):**
- `coverage-report-{Linux,Windows}` — coverage.xml
- `build-health-report-{Linux,Windows}` — Build_Health_Report.json
- `security-reports` — bandit-report.json, pip-audit-report.txt
- `cs2-analyzer-windows` — dist/ (main branch only)

**Supply-chain hardening:** Every GitHub Action is pinned to full commit SHA:
- `actions/checkout@34e114876b…` (v4)
- `actions/setup-python@a26af69be…` (v5)
- `actions/upload-artifact@ea165f839…` (v4)
- `actions/cache@5a3ec84eff…` (v4)

### 1.2 Pre-commit Hooks — `.pre-commit-config.yaml` (97 lines)

**14 hooks total** (4 custom local + 10 standard):

| Hook | Source | Stage | What it does |
|------|--------|-------|-------------|
| `headless-validator` | local → `tools/headless_validator.py` | pre-push | 23-phase system validation gate |
| `dead-code-detector` | local → `tools/dead_code_detector.py` | pre-push | Orphaned module / dead import finder |
| `integrity-manifest-check` | local → `Programma_CS2_RENAN/tools/sync_integrity_manifest.py --verify-only` | pre-commit | Verifies `integrity_manifest.json` hash consistency |
| `dev-health-quick` | local → `tools/dev_health.py --quick` | pre-commit | Fast health checks (critical paths) |
| `trailing-whitespace` | pre-commit/pre-commit-hooks v4.5.0 | pre-commit | Strips trailing whitespace |
| `end-of-file-fixer` | pre-commit/pre-commit-hooks v4.5.0 | pre-commit | Ensures single newline at EOF |
| `check-yaml` | pre-commit/pre-commit-hooks v4.5.0 | pre-commit | YAML syntax validation |
| `check-json` | pre-commit/pre-commit-hooks v4.5.0 | pre-commit | JSON syntax validation |
| `check-added-large-files` | pre-commit/pre-commit-hooks v4.5.0 | pre-commit | Blocks files > 1000 KB (excludes PHOTO_GUI images, CSVs) |
| `check-merge-conflict` | pre-commit/pre-commit-hooks v4.5.0 | pre-commit | Detects `<<<<<<<` markers |
| `detect-private-key` | pre-commit/pre-commit-hooks v4.5.0 | pre-commit | Finds hardcoded private keys |
| `black` | psf/black-pre-commit-mirror 24.1.1 | pre-commit | Code formatting (line-length=100, py310, excludes: external_analysis, dist, venv) |
| `isort` | pycqa/isort 5.13.2 | pre-commit | Import sorting (black profile, line_length=100) |

### 1.3 Testing Infrastructure

**Configuration:** `pytest.ini` (45 lines)

| Setting | Value |
|---------|-------|
| Test paths | `tests`, `Programma_CS2_RENAN/tests` |
| Discovery | `test_*.py` → `Test*` → `test_*` |
| Global timeout | 30 s (`pytest-timeout`) |
| Strict markers | Yes (`--strict-markers`) |
| Traceback | `--tb=short` |

**Registered markers:**
1. `slow` — deselect with `-m "not slow"`
2. `integration` — integration tests
3. `unit` — unit tests
4. `portability` — cross-platform tests
5. `known_fail` — documented failures pending fix
6. `flaky` — non-deterministic / environment-dependent

**Test files:** 78 in `Programma_CS2_RENAN/tests/` + automated suite (`tests/automated_suite/`):
- `test_smoke.py`, `test_unit.py`, `test_functional.py`, `test_e2e.py`, `test_system_regression.py`

**Coverage configuration** (`pyproject.toml:51-69`):
```toml
[tool.coverage.run]
source = ["Programma_CS2_RENAN"]
omit = ["*/tests/*", "*/.venv/*", "*/external_analysis/*"]

[tool.coverage.report]
fail_under = 33          # roadmap: 33 → 35 → 40 → 50 → 60 → 70
show_missing = true
exclude_lines = ["pragma: no cover", "if __name__ == .__main__.", "if TYPE_CHECKING:"]
```

### 1.4 Code Quality Tooling

**Formatter / linter configuration** (`pyproject.toml`):

| Tool | Config section | Key settings |
|------|---------------|--------------|
| Black | `[tool.black]` | `line-length = 100`, `target-version = ["py310"]` |
| isort | `[tool.isort]` | `profile = "black"`, `line_length = 100` |
| mypy | `[tool.mypy]` | `python_version = "3.10"`, `warn_return_any = true`, `check_untyped_defs = true`, `disallow_untyped_defs = false` |

mypy excludes: `external_analysis/`, `dist/`, `.venv/`, `tests/`

### 1.5 Package Management

**Build system:** setuptools >= 68.0 (`pyproject.toml:1-2`)

**Dependencies (requirements.txt — 63 packages):**

| Category | Packages |
|----------|----------|
| UI | PySide6 >= 6.6.0 |
| Demo parsing | demoparser2 >= 0.40.0 |
| ORM | SQLAlchemy 2.0+, SQLModel, Alembic, Pydantic 2.0+ |
| ML | torch >= 2.1.0, numpy, scipy, scikit-learn |
| Web | FastAPI, uvicorn, requests, httpx |
| Scraping | Playwright, BeautifulSoup4 |
| NLP | sentence-transformers (optional) |
| Vector | faiss-cpu (optional) |
| Monitoring | psutil, watchdog, sentry-sdk |
| Dev | pre-commit >= 3.5.0 |

**Lock files:**
- `requirements-lock.txt` — full pins (generated 2026-02-15, Python 3.10.11, Windows 10)
- `requirements-lock-cpu.txt` — CPU-only PyTorch variant (torch 2.5.1+cpu)
- `requirements-ci.txt` — CI overlay (CPU torch via `--extra-index-url`)

**Key locked versions:** torch 2.5.1+cu121, playwright 1.57.0, numpy 2.2.6, fastapi 0.128.0, cryptography 46.0.3, requests 2.32.5

**Alembic migrations** (2 in `backend/storage/migrations/versions/`):
1. `b609a11e13cc_baseline_schema.py` — baseline 21-table schema
2. `5d5764ef9f26_add_rating_components.py` — rating component columns

### 1.6 Docker

**File:** `docker-compose.yml` (17 lines) — single service:

| Setting | Value |
|---------|-------|
| Service | `flaresolverr` |
| Image | `ghcr.io/flaresolverr/flaresolverr:v3.4.6` |
| Ports | `8191:8191` |
| Env | `LOG_LEVEL: info`, `TZ: America/Sao_Paulo` |
| Restart | `unless-stopped` |
| Healthcheck | `curl -f http://localhost:8191/` (30s interval, 10s timeout, 3 retries, 15s start) |

Purpose: Cloudflare bypass proxy for HLTV match-data scraping.

### 1.7 Documentation

46 files across `docs/`, root, and sub-packages:

| Category | Files | Highlights |
|----------|-------|------------|
| Technical books | 5 (1A, 1B, 2, 3 .md + 3 .pdf) | Italian, 579 KB+ each, exhaustive architecture coverage |
| Architecture | 3 (EN, IT, PT) | `AI_ARCHITECTURE_ANALYSIS` — 51–58 KB |
| User guides | 3 (EN, IT, PT) | 19–24 KB each |
| Cybersecurity | 1 | 31 KB assessment |
| Product viability | 1 | 30 KB analysis |
| Research studies | 16 | Algebra, RL, JEPA, GNN, ethics, hardware optimisation, etc. |
| CI/CD guides | 5 | README + CICD_GUIDE + ABOUT_CICD (EN, IT, PT) |
| Error/exit codes | 2 | ERROR_CODES.md, EXIT_CODES.md |
| Logging strategy | 1 | logging-and-plan.md (42 KB) |
| IDE setup | 2 | PYCHARM_CONFIGURATION_GUIDE + reference (36 KB) |

### 1.8 Security

| Mechanism | Location | Details |
|-----------|----------|---------|
| Bandit SAST | CI security stage | `--severity-level medium --confidence-level medium`, blocks on findings |
| detect-secrets | CI + pre-commit | Scans for hardcoded credentials |
| pip-audit | CI security stage | `--strict` mode — CVE scanning |
| SHA-pinned Actions | build.yml | All 4 Actions pinned to commit SHA, not tag |
| .gitignore secrets | `.gitignore` | `.env`, `.env.*`, `.secret_master.key`, `gha-creds-*.json` |
| RASP audit | `Programma_CS2_RENAN/main.py` | Runtime Application Self-Protection on boot |
| HMAC manifest | `CS2_MANIFEST_KEY` env var | Integrity verification of critical files |
| Large-file guard | pre-commit | Blocks files > 1000 KB (prevents accidental binary commits) |

### 1.9 Entry Points

The application has 6 runnable entry points but **no formal `[project.scripts]`** in `pyproject.toml`:

| Entry point | File | Purpose | Shebang |
|-------------|------|---------|---------|
| Qt UI (primary) | `Programma_CS2_RENAN/main.py` | Full application: venv guard → RASP audit → Qt launch | No |
| Batch ingestion | `batch_ingest.py` | Headless demo processing | `#!/usr/bin/env python3` |
| Console shell | `console.py` (66 KB) | Interactive REPL for testing/debugging | `#!/usr/bin/env python3` |
| Training cycle | `run_full_training_cycle.py` | ML model training orchestration | No |
| Schema inspector | `schema.py` | Database schema inspection tool | No |
| Goliath | `goliath.py` (13 KB) | Reference architecture utility | `#!/usr/bin/env python3` |

### 1.10 Environment Variables

The codebase reads **25 environment variables** across all modules:

| Variable | Default | Module(s) | Purpose |
|----------|---------|-----------|---------|
| `STEAM_API_KEY` | — | steam_api.py | Steam Web API authentication |
| `STEAM_ID` | — | steam_api.py | Target Steam64 ID for demo lookup |
| `OLLAMA_URL` | `http://localhost:11434` | llm_service.py | Local LLM API endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | llm_service.py | LLM model name |
| `CS2_LOG_LEVEL` | `""` | logger_setup.py | Override application log level |
| `CS2_MANIFEST_KEY` | `""` | rasp.py | HMAC key for integrity checks |
| `CS2_TELEMETRY_URL` | `http://127.0.0.1:8000` | telemetry_client.py | Telemetry server endpoint |
| `CS2_TELEMETRY_PATH` | — | server.py | Telemetry data directory |
| `CS2_INTEGRATION_TESTS` | — | conftest.py | Set `"1"` to enable integration tests |
| `CS2_LATENCY_MULTIPLIER` | `"3.0"` | test_deployment_readiness.py | CI latency tolerance factor |
| `HP_MODE` | `"0"` | resource_manager.py, run_ingestion.py | High-performance mode toggle |
| `FLARESOLVERR_URL` | `http://localhost:8191/v1` | docker_manager.py | FlareSolverr proxy endpoint |
| `SENTRY_DSN` | — | logger_setup.py | Sentry error tracking DSN |
| `CI` | — | conftest.py, tools | CI environment indicator |
| `GITHUB_ACTIONS` | — | conftest.py | GitHub Actions environment indicator |
| `VIRTUAL_ENV` | — | build.yml | Virtual environment name (CI) |
| `KIVY_NO_ARGS` | `"1"` (set) | main.py, batch_ingest.py, conftest.py | Disable Kivy argument parsing |
| `KIVY_LOG_LEVEL` | `"warning"` | batch_ingest.py | Kivy logging suppression |
| `NO_COLOR` | — | _infra.py | Disable ANSI colour output |
| `TERM` | — | _infra.py | Terminal type detection |
| `WT_SESSION` | — | _infra.py | Windows Terminal detection |
| `LOCALAPPDATA` | `~` | config.py | Windows app data path |
| `JAVA_HOME` | `tools/jdk17` | run_build.py | Java home for build tooling |
| `MMDC_PATH` | `mmdc` | generate_zh_pdfs.py | Mermaid CLI path (docs build) |
| `DOCS_DIR` | `__file__` parent | generate_zh_pdfs.py | Documentation directory (docs build) |

### 1.11 License Structure

**File:** `LICENSE` (236 lines) — dual license:

**Section A (default) — Proprietary:**
- Copyright 2025–2026 Renan Augusto Macena
- No copying, modification, distribution without written permission
- No reverse engineering / decompilation
- No commercial use without commercial license
- Viewing for educational purposes permitted
- Fork-for-PR permitted; accepted contributions become author's property

**Section B (opt-in) — Apache License 2.0:**
- Full Apache 2.0 terms (lines 54–228)
- Available when explicitly chosen

---

## 2. What Is Missing

### Priority 1 — High (professional baseline)

| # | File | Purpose | Why it matters |
|---|------|---------|----------------|
| 1 | `CONTRIBUTING.md` | How to fork, branch, test, and submit PRs | First thing a new contributor looks for; its absence signals "closed project" |
| 2 | `CODE_OF_CONDUCT.md` | Expected behaviour in issues, PRs, discussions | Required by most open-source foundations and enterprise compliance checks |
| 3 | `SECURITY.md` | How to report vulnerabilities privately | GitHub displays a warning banner in the Security tab when this is missing; critical for responsible disclosure |
| 4 | `CHANGELOG.md` | Structured version history (Keep a Changelog format) | Users and integrators need to know what changed between releases without reading git log |
| 5 | `.env.example` | Template listing every env var the app reads | Prevents "works on my machine" onboarding failures; 25 env vars documented nowhere |

### Priority 2 — Medium (GitHub best practices)

| # | File | Purpose | Why it matters |
|---|------|---------|----------------|
| 6 | `.github/ISSUE_TEMPLATE/bug_report.yml` | Structured bug report form (YAML, not Markdown) | Enforces required fields, auto-labels; reduces low-quality reports |
| 7 | `.github/ISSUE_TEMPLATE/feature_request.yml` | Feature request form | Captures motivation, alternatives, and acceptance criteria |
| 8 | `.github/PULL_REQUEST_TEMPLATE.md` | PR checklist | Ensures tests pass, docs updated, screenshots attached |
| 9 | `.github/CODEOWNERS` | Auto-assign reviewers by path | Guarantees the right person reviews each PR |
| 10 | `.github/dependabot.yml` | Automated dependency update PRs | Catches CVEs and outdated packages before they accumulate; monitors both pip and github-actions ecosystems |

### Priority 3 — Low (polish and enterprise extras)

| # | File | Purpose | Why it matters |
|---|------|---------|----------------|
| 11 | `.editorconfig` | Cross-editor indentation/encoding rules | Prevents mixed tabs/spaces from editors that ignore pyproject.toml (VSCode, Vim, Sublime) |
| 12 | `Dockerfile` | Container image for the main application | Required for cloud deployment, reproducible environments, Kubernetes |
| 13 | `.dockerignore` | Exclude tests/docs/models from image | Smaller image, faster builds, no secrets leaked into layers |
| 14 | Git version tags (`v1.0.0`) | Semantic versioning anchored to commits | Enables `git describe`, GitHub Releases page, and downstream dependency pinning |

### Priority 4 — Structural (not missing files, but missing practices)

| # | Practice | Current state | Industry expectation |
|---|----------|---------------|---------------------|
| 15 | `[project.scripts]` in pyproject.toml | 6 entry points, none registered | `macena = "Programma_CS2_RENAN.main:main"` enables `pip install -e .` + CLI |
| 16 | Branch protection rules | CI enforces via job deps, but no GitHub-level protection | Require PR, require CI pass, require 1 review on `main` |
| 17 | GitHub Releases | None | Attach PyInstaller artifact to tagged releases |
| 18 | SBOM (Software Bill of Materials) | pip-audit runs, but no exported SBOM | `pip-audit --format=cyclonedx-json` or `syft` for supply-chain transparency |

---

## 3. Detailed Recommendations (ready-to-use content)

### 3.1 CONTRIBUTING.md

Should cover these sections, mapped to your existing tooling:

| Section | Content (derived from codebase) |
|---------|--------------------------------|
| Prerequisites | Python >= 3.10, PySide6 >= 6.6.0, pre-commit >= 3.5.0 |
| Setup | `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pre-commit install` |
| Branch naming | `feature/*`, `fix/*` (already in CI triggers: `build.yml:8-10`) |
| Running tests | `pytest` (30 s timeout, `--strict-markers`), `pytest -m "not slow"` for fast feedback |
| Headless validator | `python tools/headless_validator.py` (23-phase gate, same as CI) |
| Code style | Black 24.1.1 (line-length 100), isort 5.13.2 (black profile) — enforced by pre-commit |
| Type checking | `mypy Programma_CS2_RENAN/ --ignore-missing-imports` (informational, not blocking) |
| Commit format | Imperative mood, 72-char subject, body explains "why" not "what" |
| PR process | Target `main`, all CI stages must pass, 1 review required |
| Licensing | Contributions accepted under Section A of LICENSE (become author's property) |

### 3.2 CODE_OF_CONDUCT.md

Adopt [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)
— the de-facto standard used by Linux, Kubernetes, .NET, and 100k+ projects. Customise
the enforcement contact email.

### 3.3 SECURITY.md

```markdown
# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

## Reporting a Vulnerability

**Do NOT open a public issue.**

Use [GitHub Security Advisories](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/security/advisories/new)
to report vulnerabilities privately.

Expected response time: 72 hours for acknowledgement, 30 days for fix or mitigation.

## Scope

The following are in scope:
- SQL injection, XSS, or command injection in any user-facing input path
- Authentication/authorisation bypass in Steam API or HLTV scraping flows
- Credential leakage (API keys, session tokens) via logs, error messages, or artifacts
- Dependency vulnerabilities not yet caught by pip-audit

Out of scope:
- Denial-of-service via demo file size (we assume trusted local input)
- Issues in third-party services (Steam, HLTV, FlareSolverr)

## Security Scanning Already in Place

- **Bandit** SAST (MEDIUM+ severity blocking) — CI security stage
- **detect-secrets** — hardcoded credential scanning
- **pip-audit** — CVE scanning in strict mode
- **RASP** — runtime integrity check on application boot
- **HMAC manifest** — critical file integrity verification
```

### 3.4 CHANGELOG.md

Use [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-20

### Added
- Qt/PySide6 as primary desktop UI (13 screens, MVVM, Qt Signals/Slots)
- 3 visual themes: CS2 (orange #FF6600), CSGO (blue-grey #4A90D9), CS1.6 (green #33CC33)
- i18n support: EN, IT, PT via QtLocalizationManager + JSON files
- DataLineage table (append-only data provenance tracking)
- DataQualityMetric table (append-only pipeline quality metrics)
- 1,506 tests across 78 files
- 291+ headless validator checks across 24+ phases
- 6-stage CI/CD pipeline (lint, test, integration, security, type-check, build)
- Bandit SAST, detect-secrets, pip-audit in CI security gate

### Fixed
- Zero-norm vector rejection in RAG search (M-07)
- Settings file validation rejects non-dict payloads (M-08)
- Bootstrap NameError when logger not yet initialised (C-09)
- DB handle leak in backup integrity check — uses try/finally + PRAGMA quick_check (H-02)
- Silent batch swallowing removed from RAP train/val loops (H-03)

### Changed
- Database schema: 19 → 21 tables (DataLineage, DataQualityMetric)
- Win probability: two separate architectures clearly distinguished
  - 12-feature WinProbabilityNN (real-time, analysis/win_probability.py)
  - 9-feature WinProbabilityTrainerNN (offline, nn/win_probability_trainer.py)
- Utility normalisation: /10 → /5 (CS2 max: 2 smokes + 2 flashes + 1 HE)
- Bomb heuristics: multiplicative (T: x1.2, CT: x0.85) → additive (T: +0.10, CT: -0.10)
- Kivy/KivyMD desktop app relabelled as legacy fallback
```

### 3.5 .env.example

Complete template derived from the 25 env vars found in the codebase:

```bash
# ─── Required ────────────────────────────────────────────────────────

# Steam Web API key (https://steamcommunity.com/dev/apikey)
STEAM_API_KEY=your_steam_api_key_here

# Your Steam64 ID (find at https://steamid.io)
STEAM_ID=your_steam64_id_here

# ─── LLM Backend (optional — coaching dialogue) ─────────────────────

# Ollama local LLM endpoint
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# ─── HLTV Scraping (optional — requires docker-compose up) ──────────

# FlareSolverr Cloudflare bypass proxy
FLARESOLVERR_URL=http://localhost:8191/v1

# ─── Observability (optional) ────────────────────────────────────────

# Sentry DSN for error tracking (leave empty to disable)
SENTRY_DSN=

# Application log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
CS2_LOG_LEVEL=

# Telemetry server endpoint
CS2_TELEMETRY_URL=http://127.0.0.1:8000

# ─── Security (optional) ─────────────────────────────────────────────

# HMAC key for integrity manifest verification (leave empty to skip)
CS2_MANIFEST_KEY=

# ─── Performance (optional) ──────────────────────────────────────────

# High-performance mode: set to "1" to enable aggressive resource usage
HP_MODE=0

# ─── Testing (CI only) ───────────────────────────────────────────────

# CI=true                     # Set automatically by GitHub Actions
# GITHUB_ACTIONS=true          # Set automatically by GitHub Actions
# CS2_INTEGRATION_TESTS=1      # Enable integration test suite
# CS2_LATENCY_MULTIPLIER=3.0   # CI latency tolerance factor
```

### 3.6 GitHub Issue Templates

**`.github/ISSUE_TEMPLATE/bug_report.yml`:**

```yaml
name: Bug Report
description: Report a bug in Macena CS2 Analyzer
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: Thank you for reporting a bug. Please fill in the details below.

  - type: textarea
    id: description
    attributes:
      label: Bug description
      description: Clear description of the unexpected behaviour
    validations:
      required: true

  - type: textarea
    id: reproduce
    attributes:
      label: Steps to reproduce
      description: Minimal steps to trigger the bug
      placeholder: |
        1. Launch the application with `python Programma_CS2_RENAN/main.py`
        2. Navigate to ...
        3. Click ...
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected behaviour
    validations:
      required: true

  - type: dropdown
    id: component
    attributes:
      label: Component
      options:
        - Qt UI
        - Console
        - Demo parser / Ingestion
        - Coaching engine
        - Neural networks (JEPA, RAP, Win Probability)
        - Database / Storage
        - HLTV scraping
        - CI / Build
        - Other
    validations:
      required: true

  - type: input
    id: os
    attributes:
      label: Operating system
      placeholder: "Windows 11 / Ubuntu 24.04 / macOS 15"
    validations:
      required: true

  - type: input
    id: python
    attributes:
      label: Python version
      placeholder: "3.10.11"
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: Log output
      description: Paste relevant log output or traceback
      render: shell
```

**`.github/ISSUE_TEMPLATE/feature_request.yml`:**

```yaml
name: Feature Request
description: Suggest a new feature or enhancement
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem statement
      description: What problem does this feature solve?
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Proposed solution
      description: How would you like this to work?
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
      description: Any workarounds or alternative approaches you considered?

  - type: dropdown
    id: component
    attributes:
      label: Component
      options:
        - Qt UI
        - Console
        - Demo parser / Ingestion
        - Coaching engine
        - Neural networks
        - Database / Storage
        - HLTV scraping
        - Documentation
        - Other
```

**`.github/ISSUE_TEMPLATE/config.yml`:**

```yaml
blank_issues_enabled: false
contact_links:
  - name: Question / Discussion
    url: https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/discussions
    about: Use Discussions for general questions
```

### 3.7 Pull Request Template

**`.github/PULL_REQUEST_TEMPLATE.md`:**

```markdown
## What this PR does
<!-- Brief description of the change and why it's needed -->

## Type of change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactor / tech debt

## How to test
<!-- Steps to verify the change works correctly -->

## Checklist
- [ ] `pytest` passes locally
- [ ] `python tools/headless_validator.py` passes (23 phases)
- [ ] Code formatted with Black + isort (`pre-commit run --all-files`)
- [ ] Updated relevant docs (if applicable)
- [ ] No new secrets or credentials in committed files

## Screenshots (if UI change)
```

### 3.8 CODEOWNERS

**`.github/CODEOWNERS`:**

```
# Default — all files require owner review
* @renanaugustomacena-ux

# Qt UI (primary interface)
Programma_CS2_RENAN/apps/qt_app/ @renanaugustomacena-ux

# Legacy Kivy UI
Programma_CS2_RENAN/apps/desktop_app/ @renanaugustomacena-ux

# Neural networks (JEPA, RAP, Win Probability)
Programma_CS2_RENAN/backend/nn/ @renanaugustomacena-ux

# Database schema and migrations
Programma_CS2_RENAN/backend/storage/ @renanaugustomacena-ux
backend/storage/migrations/ @renanaugustomacena-ux
alembic/ @renanaugustomacena-ux

# CI/CD pipeline
.github/ @renanaugustomacena-ux

# Security-sensitive files
Programma_CS2_RENAN/observability/rasp.py @renanaugustomacena-ux
Programma_CS2_RENAN/core/integrity_manifest.json @renanaugustomacena-ux
```

### 3.9 Dependabot

**`.github/dependabot.yml`:**

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 5
    labels:
      - dependencies
      - automated
    ignore:
      # Major version bumps require manual review
      - dependency-name: "torch"
        update-types: ["version-update:semver-major"]
      - dependency-name: "PySide6"
        update-types: ["version-update:semver-major"]
      - dependency-name: "sqlalchemy"
        update-types: ["version-update:semver-major"]

  # GitHub Actions versions
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    labels:
      - ci
      - automated
```

### 3.10 .editorconfig

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yml,yaml,json}]
indent_size = 2

[*.md]
# Markdown uses trailing spaces for line breaks
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

### 3.11 Dockerfile + .dockerignore

A minimal Dockerfile for the session engine / headless validator demonstrates
cloud-readiness. Not strictly required if the project remains desktop-only, but
expected by enterprise evaluators and enables:
- Reproducible CI environments without matrix complexity
- Cloud deployment of the coaching API (FastAPI + uvicorn)
- Containerised training pipelines

**Suggested `Dockerfile`:**

```dockerfile
FROM python:3.10-slim AS base

WORKDIR /app

# System deps for PySide6 headless + SDL2 (Kivy legacy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: headless validator (CI mode)
ENV CI=true KIVY_NO_ARGS=1
CMD ["python", "tools/headless_validator.py"]
```

**Suggested `.dockerignore`:**

```
.git
.github
.venv
venv
dist
build
*.egg-info
__pycache__
*.pyc
*.pyo
.env
.env.*
.secret_master.key
*.db
*.pt
*.dem
*.mcn
docs/
PHOTO_GUI/
runs/
reports/
```

### 3.12 Version Tags and GitHub Releases

```bash
# Tag the current state
git tag -a v1.0.0 -m "v1.0.0: Qt UI primary, 21 tables, 1506 tests, 6-stage CI"
git push origin v1.0.0
```

Then create a GitHub Release from the tag:
- Title: `v1.0.0 — Qt Desktop UI & Full CI Pipeline`
- Body: link to CHANGELOG.md
- Attach: PyInstaller Windows build from CI artifact (`cs2-analyzer-windows`)

### 3.13 pyproject.toml Entry Points

Add to `pyproject.toml` to enable `pip install -e .` and CLI access:

```toml
[project.scripts]
macena = "Programma_CS2_RENAN.main:main"
macena-ingest = "batch_ingest:main"
macena-console = "console:main"
```

This requires each script to expose a `main()` function (currently they use
`if __name__ == "__main__"` guards — a minor refactor).

---

## 4. Release Management Recommendation

Currently the repository has no formal release process. A lightweight approach:

1. **Version tags** on `main` for each release (`v1.0.0`, `v1.1.0`, etc.)
2. **CHANGELOG.md** updated before each tag (see Section 3.4)
3. **GitHub Release** created from each tag (auto-generated notes + manual summary)
4. **Branch protection** on `main`:
   - Require pull request before merge
   - Require status checks: `lint`, `test`, `integration`, `security`
   - Require 1 approving review
   - Dismiss stale reviews on new pushes
5. Optional: `develop` branch for integration (CI already supports it via `build.yml:8`)

**Recommended GitHub Settings → Branches → Branch protection rule for `main`:**

| Setting | Value |
|---------|-------|
| Require a pull request before merging | Yes |
| Required approving reviews | 1 |
| Dismiss stale pull request approvals | Yes |
| Require status checks to pass before merging | Yes |
| Status checks: | `lint`, `test`, `integration`, `security` |
| Require branches to be up to date | Yes |
| Restrict who can push to matching branches | Owner only |

---

## 5. Coverage Threshold Roadmap

Current: `fail_under = 33` (`pyproject.toml:63`, enforced by CI at `build.yml:133`)

| Phase | Target | Focus area | Rationale |
|-------|--------|------------|-----------|
| Current | 33% | — | Baseline established |
| Next | 50% | `backend/nn/`, `backend/processing/` | Neural network and feature engineering are highest-risk modules |
| Mid-term | 70% | `backend/coaching/`, `backend/services/` | Coaching pipeline and service layer affect user-facing quality |
| Long-term | 80%+ | `apps/qt_app/viewmodels/`, `core/session_engine.py` | UI viewmodels and session orchestration for full confidence |

**Suggested exclusions to keep (already configured):**
- `*/tests/*` — test code itself
- `*/external_analysis/*` — third-party analysis scripts
- `*/.venv/*` — virtual environment
- `pragma: no cover` — explicit opt-outs
- `if __name__ == "__main__"` — script entry guards
- `if TYPE_CHECKING:` — type-only imports

---

## 6. Compliance Checklist

Quick reference for implementation on another machine. Check each box as you create the file:

```
Priority 1 — Professional Baseline
  [ ] CONTRIBUTING.md                              (Section 3.1)
  [ ] CODE_OF_CONDUCT.md                           (Section 3.2)
  [ ] SECURITY.md                                  (Section 3.3)
  [ ] CHANGELOG.md                                 (Section 3.4)
  [ ] .env.example                                 (Section 3.5)

Priority 2 — GitHub Best Practices
  [ ] .github/ISSUE_TEMPLATE/bug_report.yml        (Section 3.6)
  [ ] .github/ISSUE_TEMPLATE/feature_request.yml   (Section 3.6)
  [ ] .github/ISSUE_TEMPLATE/config.yml            (Section 3.6)
  [ ] .github/PULL_REQUEST_TEMPLATE.md             (Section 3.7)
  [ ] .github/CODEOWNERS                           (Section 3.8)
  [ ] .github/dependabot.yml                       (Section 3.9)

Priority 3 — Polish
  [ ] .editorconfig                                (Section 3.10)
  [ ] Dockerfile                                   (Section 3.11)
  [ ] .dockerignore                                (Section 3.11)
  [ ] git tag v1.0.0                               (Section 3.12)
  [ ] GitHub Release from v1.0.0 tag               (Section 3.12)

Priority 4 — Structural
  [ ] [project.scripts] in pyproject.toml          (Section 3.13)
  [ ] Branch protection rules on main              (Section 4)
  [ ] SBOM export (pip-audit --format=cyclonedx-json)
```

---

## Conclusion

The repository is **technically excellent** — the CI/CD pipeline, security scanning,
testing infrastructure, and documentation are above average for projects of this
complexity. The gaps are all in **governance and community files** that take 2–3 hours
to add but significantly improve the project's professional appearance, contributor
experience, and enterprise readiness.

**Recommended action:** Create all Priority 1 + Priority 2 files in a single PR (content
provided above is ready to copy-paste). Then tag `v1.0.0` and configure branch protection
on `main`. This closes every visible gap with minimal effort.
