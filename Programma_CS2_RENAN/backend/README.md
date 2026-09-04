> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Backend -- Core Business Logic Layer

| Authority | Skill Level |
|-----------|-------------|
| Macena CS2 Analyzer | Domain-Driven Design, AI Coaching Pipeline |

---

## Overview

The `backend/` package is the central business logic layer of the Macena CS2 Analyzer.
It is organized into **14 sub-packages** following domain-driven design principles,
where each sub-package owns its domain, data invariants, and failure modes.

The backend implements the **full AI coaching pipeline** end-to-end:

1. **Raw demo parsing** -- `.dem` files are decoded into structured tick/event data.
2. **Feature engineering** -- tick-level data is projected into a unified 25-dimensional feature vector.
3. **Neural network inference** -- trained models (JEPA, RAP Coach, AdvancedCoachNN) score and classify player behavior.
4. **Coaching output** -- analysis results are transformed into actionable, natural language coaching advice.

No UI logic lives here. The backend exposes its capabilities through a **service layer**
(`services/`) that is consumed by the PySide6/Qt UI (`apps/qt_app/`).

---

## Sub-Package Inventory

| # | Sub-Package | Files | Purpose | Key Entry Points |
|---|-------------|-------|---------|------------------|
| 1 | `analysis/` | 12 | Game theory engines: belief models, momentum tracking, win probability, entropy analysis, deception index, blind spot detection | `belief_model.py`, `win_probability.py`, `momentum.py` |
| 2 | `coaching/` | 9 | 4-mode coaching pipeline: COPER experience-based, Hybrid (NN + rules), RAG retrieval-augmented, traditional corrections | `hybrid_engine.py`, `correction_engine.py`, `pro_bridge.py` |
| 3 | `control/` | 5 | Daemon lifecycle management, ingestion queue governance, ML training control, database resource limits | `ingest_manager.py`, `ml_controller.py`, `db_governor.py` |
| 4 | `data_sources/` | 16 | External data integration: demo parser (demoparser2), HLTV pro statistics scraper (FlareSolverr/Docker), Steam API, FACEIT API | `demo_parser.py`, `hltv/`, `steam_api.py`, `faceit_api.py` |
| 5 | `ingestion/` | 4 | Runtime file watching for new demos, CSV migration from legacy formats, OS resource governance | `watcher.py`, `resource_manager.py`, `csv_migrator.py` |
| 6 | `knowledge/` | 8 | RAG knowledge base with FAISS vector index, COPER experience bank, pro demo mining, tactical knowledge graph | `rag_knowledge.py`, `experience_bank.py`, `vector_index.py` |
| 7 | `knowledge_base/` | 2 | In-app help system: Markdown doc indexing and text search for the UI help screen | `help_system.py` |
| 8 | `nn/` | 53 | Neural network architectures (6 model types), training pipeline, inference, EMA, early stopping, data quality, RAP Coach, JEPA | `jepa_model.py`, `rap_coach/`, `train.py`, `config.py` |
| 9 | `onboarding/` | 2 | New user progression flow: demo-count staging and coach readiness gating | `new_user_flow.py` |
| 10 | `processing/` | 30 | Feature engineering (25-dim vector), baseline computation, pro baselines, heatmap generation, validation, tick enrichment | `feature_engineering/vectorizer.py`, `baselines/`, `validation/` |
| 11 | `progress/` | 3 | Longitudinal player performance tracking: per-feature trend computation (slope, volatility, confidence) | `longitudinal.py`, `trend_analysis.py` |
| 12 | `reporting/` | 2 | Analytics query layer for UI screens: aggregated match stats, trend summaries, performance breakdowns | `analytics.py` |
| 13 | `services/` | 12 | Service orchestration layer: coaching service, analysis orchestrator, dialogue engine, LLM integration, profile management, telemetry | `coaching_service.py`, `analysis_orchestrator.py`, `llm_service.py` |
| 14 | `storage/` | 14 | Tri-database persistence (SQLite WAL): database manager, SQLModel ORM, backup, match data manager, state manager, remote telemetry | `database.py`, `db_models.py`, `match_data_manager.py` |

File counts are recursive `.py` files (including `__init__.py`), excluding `__pycache__`.

**Top-level module:** besides the sub-packages, the package root contains `server.py` --
a **standalone FastAPI utility server** (telemetry ingestion endpoint with rate limiting,
Ollama proxy). Per its docstring it is **NOT wired** into the app lifecycle: it is not
imported or launched by `main.py`, `session_engine.py`, or `lifecycle.py`. To use it, run
`uvicorn Programma_CS2_RENAN.backend.server:app` manually.

---

## Data Flow Diagram

The backend processes data through four conceptual stages, mapping to the
Quad-Daemon Engine (`core/session_engine.py`):

```
 WATCH          LEARN           THINK            SPEAK
 (Ingest)       (Process)       (Analyze)        (Coach)

 .dem files      Tick data       Game theory      Natural language
 HLTV stats      25-dim vector   NN inference     coaching output
 Steam API       Baselines       Belief models    Correction advice
                 Validation      Win probability  Pro comparisons

 data_sources/   processing/     analysis/        coaching/
 ingestion/      knowledge/      nn/              services/
 control/        storage/        progress/        reporting/
```

**Detailed flow:**

```
[Demo File (.dem)]
       |
       v
  data_sources/demo_parser.py       -- Parse raw binary demo
       |
       v
  processing/feature_engineering/   -- Extract 25-dim feature vector
       |
       v
  storage/match_data_manager.py     -- Persist to per-match SQLite DB
       |
       v
  nn/ (JEPA / RAP Coach)            -- Neural network inference
       |
       v
  analysis/ (11 game theory modules)-- Score patterns, detect blind spots
       |
       v
  coaching/ (4-level fallback)      -- Generate coaching advice
       |
       v
  services/coaching_service.py      -- Expose to UI layer
```

---

## Key Architectural Patterns

### 4-Level Coaching Fallback

The coaching pipeline tries progressively simpler strategies until one succeeds:

| Priority | Mode | Source | Condition |
|----------|------|--------|-----------|
| 1 | **COPER** | Experience Bank + RAG + Pro References | `USE_COPER_COACHING` (default True) + map name + tick data |
| 2 | **Hybrid** | NN predictions + knowledge retrieval | `USE_HYBRID_COACHING` (default False) + player stats |
| 3 | **Traditional + RAG** | Correction engine + knowledge retrieval | `USE_RAG_COACHING` (default False) |
| 4 | **Traditional** | Pure deviation-based correction engine | Always available (fallback) |

### 3-Stage Maturity Gating

Models and coaching quality evolve through three stages:

| Stage | Name | Behavior |
|-------|------|----------|
| 0 | **CALIBRATING** (0-49 demos) | Hedged coaching, confidence multiplier 0.5 |
| 1 | **LEARNING** (50-199 demos) | Basic coaching, confidence multiplier 0.8 |
| 2 | **MATURE** (200+ demos) | Full coaching, confidence multiplier 1.0 |

### Temporal Baseline Decay

Player skill baselines use exponential decay weighting so that recent performance
matters more than older data. Implemented by `TemporalBaselineDecay` in
`baselines/pro_baseline.py` (half-life 90 days, minimum weight 0.1).

### Unified 25-Dimensional Feature Vector

All models consume the same 25-element vector produced by `FeatureExtractor`
(`processing/feature_engineering/vectorizer.py`). This is the **single source of truth**
for feature definitions. Dimension mismatches cause silent training corruption.
Compile-time assertion enforces `len(FEATURE_NAMES) == METADATA_DIM == 25`.

### SQLite WAL Mode

All three databases (Monolith, HLTV, Per-match) enforce Write-Ahead Logging
at connection checkout via SQLAlchemy `@event.listens_for`. This enables
concurrent readers without blocking writers.

---

## Dependency Rules Between Sub-Packages

```
Layer 0 (Foundation):   storage/
Layer 1 (Data):         data_sources/  ingestion/  knowledge/  knowledge_base/
Layer 2 (Processing):   processing/  progress/
Layer 3 (Intelligence): analysis/  nn/
Layer 4 (Coaching):     coaching/  onboarding/
Layer 5 (Orchestration): services/  reporting/  control/
```

**Hard rules:**

- Lower layers NEVER import from higher layers.
- `storage/` has ZERO domain logic -- it is pure persistence.
- `services/` is the primary layer consumed by UI packages (`apps/`); the read-only
  `reporting/` analytics singleton is also imported directly by dashboard ViewModels.
- `nn/` may read from `processing/` and `storage/`, but never from `coaching/`.
- `coaching/` may invoke `nn/` for inference, but never triggers training.
- `control/` manages daemon lifecycle and may touch any layer for orchestration.
- `data_sources/hltv/` scrapes pro player statistics ONLY. It does NOT fetch demos.

---

## Critical Invariants

| ID | Rule | Consequence if Violated |
|----|------|------------------------|
| P-X-01 | `len(FEATURE_NAMES) == METADATA_DIM == 25` | Silent model corruption |
| P-RSB-03 | `round_won` excluded from training features | Label leakage destroys model validity |
| NN-MEM-01 | Hopfield bypassed until first real optimizer step (or trained-checkpoint load) | NaN explosion in RAP memory |
| P-VEC-02 | NaN/Inf in features triggers ERROR + clamp | Garbage propagation through pipeline |
| P3-A | > 5% NaN/Inf in batch raises `DataQualityError` | Training run aborts cleanly |
| DS-12 | `MIN_DEMO_SIZE = 10 MB` | Rejects corrupt/truncated demo files |
| NN-16 | EMA `apply_shadow()` must `.clone()` tensors | Target encoder silently shares weights |
| NN-JM-04 | Target encoder `requires_grad=False` during EMA | Gradient leakage corrupts JEPA |

---

## Development Notes

### Import Patterns

- Optional dependencies (`ncps`, `hflayers`) use `try/except` at import and raise
  at instantiation. Check `_RAP_DEPS_AVAILABLE` before using RAP Coach.
- Circular import guards: `config` <-> `logger_setup` uses post-import wiring;
  `vectorizer.py` and `session_engine.py` use lazy/function-level imports.

### Configuration

- Resolution order: Defaults -> `user_settings.json` -> OS keyring/env.
- In daemon threads, use `get_setting()` / `get_credential()` (thread-safe).
  Module-level globals are snapshot-at-import and may be stale.

### Testing

- Framework: `pytest`, 166 `test_*.py` files in `Programma_CS2_RENAN/tests/` (+10 in root `tests/`).
- Integration tests require `CS2_INTEGRATION_TESTS=1`.
- Key fixtures: `in_memory_db`, `seeded_db_session`, `mock_db_manager`, `torch_no_grad`.

### Pre-Commit Hooks

14 hooks must pass before any commit: headless-validator, dead-code-detector,
integrity-manifest, dev-health, trailing-whitespace, end-of-file-fixer,
check-yaml, check-json, large-files (1 MB), merge-conflict, detect-private-key,
ruff (--fix), black (100 cols, py3.12), isort (profile=black).

### Post-Task Validation

After every change, run:

```bash
python tools/headless_validator.py   # must exit 0
```
