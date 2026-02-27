# Macena CS2 Analyzer — Engineering Constitution for Claude Code

> **Authority:** This file synthesizes `.agent/rules/` (rules 1-5), Gemini antigravity `global_workflows/` (rule-6, rule-7, audit, backend, database, devsecops). Full source documents take precedence for ambiguous cases.

## Non-Negotiable Engineering Principles

### Correctness & Reality (Rule 1)
- **Correctness is supreme** — fast/scalable/elegant but incorrect = invalid
- **No silent failures** — errors surface immediately, explicitly, observably
- **Deterministic by default** — randomness must be seeded, isolated, documented
- **Reproducible** — builds, tests, deployments, environments must be reproducible
- **No hidden side effects** — every effect has a traceable cause
- **Explicit trade-offs** — document what was chosen, what was rejected, and why

### Backend & API Sovereignty (Rule 2)
- **Each service owns its data, invariants, and failure modes**
- **Schema-first API design** — contracts, not functions
- **Zero trust at all boundaries** — validate inputs at edge AND domain layer
- **Separation of concerns** — transport / application / domain / infrastructure layers
- **Idempotent operations** — all externally-visible ops idempotent or documented as non-idempotent
- **Bounded retries** with backoff — no retry storms, no indefinite blocking

### Frontend & UX (Rule 3)
- **Frontend is safety-critical** — UI mistakes are system failures
- **Cognitive load is a constraint** — minimize, predict, be intentional
- **Immediate feedback** — users always know system state
- **Error prevention > error handling** — disable impossible actions, warn before destructive ones
- **WCAG 2.1 AA minimum** for accessibility

### Data & Persistence (Rule 4)
- **Data outlives code** — models must be conservative, explicit, interpretable
- **Single authoritative owner** per data concept
- **ACID/BASE declared explicitly** — no implicit consistency assumptions
- **Backups are mandatory and tested** — untested backups = no backups
- **Validate at ingress** — garbage in is unacceptable
- **Audit trails** — all mutations logged, attributable, immutable

### Security (Rule 5)
- **Assume hostile world** — active adversaries, insider threats, supply chain compromise
- **Never invent cryptography** — only vetted algorithms, standardized protocols, proven libraries
- **Least privilege everywhere** — minimal permissions, scoped, time-bound, revocable
- **No hard-coded secrets** — never logged, never plaintext where encryption is feasible
- **PII protection** — classify data, encrypt at rest and in transit

### Version Control & Change Governance (Rule 6)
- **Atomic commits** — each commit is a single logical change
- **Protected branches** — no direct commits to main/production
- **Meaningful commit messages** — semantic, attributable, traceable
- **AI-generated code must be labeled and reviewed**

### CI/CD & Release Engineering (Rule 7)
- **Deterministic, reproducible, idempotent builds**
- **Test pyramid enforced** — unit > integration > e2e
- **Security gates in pipeline** — SAST, dependency scanning, secrets detection
- **Immutable, versioned, traceable artifacts**
- **Zero-downtime deployments** with rollback capability

## Project Architecture

### Technology Stack
- **Language:** Python 3.10+
- **UI Framework:** Kivy + KivyMD (desktop app)
- **ML:** PyTorch, ncps (LTC), hflayers (Hopfield)
- **Database:** SQLite (WAL mode) — monolith `database.db` + per-match SQLite files
- **Migration:** Alembic
- **Scraping:** Playwright (sync)

### Key Directory Structure
```
Programma_CS2_RENAN/
├── apps/desktop_app/       # Kivy UI (MVVM: ViewModels, widgets)
├── backend/
│   ├── analysis/           # Game theory, belief models, momentum
│   ├── data_sources/       # Demo parser, HLTV metadata
│   ├── nn/                 # Neural networks (RAP Coach, JEPA)
│   │   ├── rap_coach/      # RAP model, memory (LTC-Hopfield), trainer
│   │   └── jepa_model.py   # JEPA encoder
│   ├── processing/         # Feature engineering, heatmaps, validation
│   ├── knowledge/          # RAG knowledge, experience bank
│   ├── services/           # Coaching service
│   └── storage/            # DB models, database, backup, match data
├── core/                   # Asset manager, map manager, spatial data, session engine
├── ingestion/              # Steam locator, integrity checks
├── observability/          # RASP, telemetry
└── reporting/              # Visualizer, PDF generators
```

### Critical Patterns
- **FeatureExtractor** (`backend/processing/feature_engineering/vectorizer.py`) — unified 25-dim vector for training and inference (METADATA_DIM=25)
- **MapManager** for UI asset loading (not AssetAuthority directly)
- **Tri-Daemon Engine** (`core/session_engine.py`) — Hunter, Digester, Teacher
- **COPER Coaching** — Experience Bank + RAG + Pro References (default coaching mode)
- **SQLite WAL mode** for concurrent access across all databases

### Workflows Applied
- **DevSecOps** (`.agent/workflows/devsecops.md`) — shift-left security in all phases
- **Audit** — risk-oriented, STRIDE methodology, automated scanning
- **Backend** — DDD, microservices readiness, resilience patterns
- **Database** — data-centric design, lifecycle management, migration discipline

## Development Rules

1. **Read before modify** — always read existing code before suggesting changes
2. **Backward compatibility** — new features must not break existing behavior
3. **Zero-regression guarantee** — test suite must pass before and after changes
4. **No magic numbers** — extract to named constants or config dataclasses
5. **Structured logging** via `get_logger("cs2analyzer.<module>")`
6. **Type hints** on all public interfaces
7. **Docstrings** only where logic is non-obvious — no boilerplate docs
8. **Every tick is sacred** — tick decimation is STRICTLY FORBIDDEN (project-specific invariant)
9. **Post-task headless validation** — after completing any development task, run `python tools/headless_validator.py` and verify exit code 0. If it fails, fix the regression before reporting the task as complete.
10. **Pre-commit hooks enforced** — run `pre-commit install` after cloning. All hooks must pass before commits reach the repo.

## Post-Task Validation Protocol

After every development task (feature, fix, refactor), Claude Code **MUST** run:

```bash
python tools/headless_validator.py
```

**Rules:**
- The command MUST exit with code 0 before the task is considered complete
- If any check fails, fix the regression immediately
- The script MUST complete in under 20 seconds
- Do NOT skip this step even for "trivial" changes
- This script does NOT validate UI/Kivy code — that requires manual testing

## Detailed Rule Reference

The full 150 numbered rules, deep audit protocol, and domain-specific workflow guides are available in `~/.claude/reference/`. Core principles are auto-loaded via `~/.claude/rules/CLAUDE.md`. Consult the reference files on demand when tasks require specific depth (infrastructure, security audits, deployment, etc.).
