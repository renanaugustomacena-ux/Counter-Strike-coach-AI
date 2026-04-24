> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Programma_CS2_RENAN — Main Application Package

> **Authority:** All Rules (Package Root)

Main application package for the Macena CS2 Analyzer — an AI-powered tactical coach for Counter-Strike 2. This package contains the complete application codebase organized into a layered architecture.

## The WATCH > LEARN > THINK > SPEAK Pipeline

The entire system follows a four-stage pipeline that transforms raw demo data into actionable coaching advice:

```
WATCH (Ingestion)  →  LEARN (Training)  →  THINK (Inference)  →  SPEAK (Dialogue)
    Hunter daemon        Teacher daemon       COPER pipeline       Template + Ollama
    Demo parsing         3-stage maturity     RAG knowledge        Causal attribution
    Feature extraction   Multi-model train    Game theory          Pro comparisons
```

### Stage 1: WATCH (Ingestion)
- The **Hunter daemon** scrapes professional player statistics from hltv.org
- The **Digester daemon** parses `.dem` files via demoparser2 and extracts the 25-dimensional feature vector
- Raw tick data is stored in per-match SQLite databases

### Stage 2: LEARN (Training)
- The **Teacher daemon** trains neural models on ingested data
- 3-stage maturity gating: CALIBRATING (0-49 demos) → LEARNING (50-199) → MATURE (200+)
- Models: JEPA (self-supervised), RAP Coach (7-layer pedagogical), NeuralRoleHead, Win Probability

### Stage 3: THINK (Inference)
- COPER coaching pipeline: Context + Observation + Pro Reference + Experience + Reasoning
- Game theory engines: belief models, momentum tracking, economy optimization
- RAG knowledge retrieval from tactical coaching documents

### Stage 4: SPEAK (Dialogue)
- Template-based coaching with causal attribution
- Optional LLM polishing via Ollama for natural language output
- Pro player comparisons and longitudinal progress tracking

## Package Structure

```
Programma_CS2_RENAN/
├── apps/                       # User interface layer
│   ├── qt_app/                 # PySide6/Qt desktop UI (primary, MVVM)
│   └── desktop_app/            # Kivy/KivyMD desktop UI (legacy fallback)
├── backend/                    # Business logic layer
│   ├── analysis/               # Game theory, belief models, momentum (11 engines)
│   ├── coaching/               # Coaching pipeline (COPER, Hybrid, RAG, Neural)
│   ├── control/                # Daemon lifecycle, ingestion queue, ML control
│   ├── data_sources/           # Demo parser, HLTV pro stats, Steam, Faceit APIs
│   ├── ingestion/              # Runtime file watching, resource governance
│   ├── knowledge/              # RAG knowledge base, COPER experience bank
│   ├── knowledge_base/         # In-app help system
│   ├── nn/                     # Neural networks (6 model architectures)
│   ├── onboarding/             # New user progression tracking
│   ├── processing/             # Feature engineering (25-dim vector), baselines
│   ├── progress/               # Training progress tracking
│   ├── reporting/              # Analytics queries for UI
│   ├── services/               # Service orchestration layer (6 services)
│   └── storage/                # SQLite persistence, models, backup
├── core/                       # Runtime foundation
│   ├── session_engine.py       # Quad-Daemon Engine (Hunter, Digester, Teacher, Pulse)
│   ├── config.py               # Configuration system (3-level resolution)
│   ├── spatial_data.py         # Map spatial intelligence (9 competitive maps)
│   ├── map_manager.py          # Map asset management
│   └── lifecycle.py            # Graceful startup/shutdown
├── ingestion/                  # Demo ingestion orchestration
│   ├── pipelines/              # User and pro demo pipelines
│   ├── registry/               # Demo file tracking and lifecycle
│   └── hltv/                   # HLTV scraper subsystem
├── observability/              # Runtime protection and monitoring
│   ├── rasp.py                 # RASP integrity guard
│   ├── logger_setup.py         # Structured JSON logging
│   └── sentry_setup.py         # Sentry error tracking
├── reporting/                  # Visualization and reports
│   ├── visualizer.py           # Heatmaps, engagement maps, momentum charts
│   └── report_generator.py     # Multi-page PDF reports
├── assets/                     # Static assets (i18n, maps)
├── data/                       # Runtime data (demos, knowledge, configs)
├── models/                     # Trained model checkpoints
├── tests/                      # Test suite (1,794+ tests in 89 files)
├── tools/                      # Package-level validation tools
├── __init__.py                 # Package init (__version__ = "1.0.0")
├── main.py                     # Legacy Kivy/KivyMD desktop entry (RASP-gated)
├── run_ingestion.py            # Demo ingestion entry point
├── run_worker.py               # Background ingestion worker (stale-task recovery)
└── hltv_sync_service.py        # Background HLTV sync daemon
```

## Key Entry Points

| File | Purpose | How to Run |
|------|---------|-----------|
| `apps/qt_app/app.py` | Desktop application (Qt GUI, primary) | `python -m Programma_CS2_RENAN.apps.qt_app.app` |
| `main.py` | Desktop application (Kivy/KivyMD GUI, legacy fallback) | `python -m Programma_CS2_RENAN.main` |
| `run_ingestion.py` | Demo ingestion pipeline | `python -m Programma_CS2_RENAN.run_ingestion` |
| `run_worker.py` | Background ingestion worker (stale task recovery) | `python -m Programma_CS2_RENAN.run_worker` |
| `hltv_sync_service.py` | HLTV background sync | Started by Hunter daemon |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Primary UI | PySide6/Qt (MVVM pattern, 13 screens, 7 ViewModels) |
| Legacy UI | Kivy + KivyMD (MVVM pattern, 6 screens) |
| ML Framework | PyTorch, ncps (Liquid Time-Constant neurons), hflayers (Hopfield) |
| Database | SQLite (WAL mode) via SQLModel/SQLAlchemy |
| Demo Parsing | demoparser2 (Rust-based, high performance) |
| Pro Stats | BeautifulSoup4 + FlareSolverr/Docker (HLTV scraping) |
| Knowledge | Sentence-BERT (384-dim) + FAISS (similarity search) |
| Observability | TensorBoard, Sentry, structured JSON logging |
| LLM Polish | Ollama (optional, local inference) |

## Critical Constants

| Constant | Value | Source |
|----------|-------|--------|
| `METADATA_DIM` | 25 | `backend/processing/feature_engineering/vectorizer.py` |
| `INPUT_DIM` | 25 | `backend/nn/config.py` |
| `OUTPUT_DIM` | 10 | `backend/nn/config.py` |
| `HIDDEN_DIM` | 128 | `backend/nn/config.py` |
| `GLOBAL_SEED` | 42 | `backend/nn/config.py` |
| `BATCH_SIZE` | 32 | `backend/nn/config.py` |

## Development Notes

- Import pattern: `from Programma_CS2_RENAN.backend.nn.config import ...`
- The package uses lazy imports to avoid circular dependencies (especially config↔logger)
- Optional ML dependencies (ncps, hflayers) use try/except at import with runtime checks
- The `__version__` in `__init__.py` must match `pyproject.toml` and `windows_installer.iss`
- Run `python tools/headless_validator.py` from the project root after any changes
- All logging uses `get_logger("cs2analyzer.<module>")` for structured JSON output
