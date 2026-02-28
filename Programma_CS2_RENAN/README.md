> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Programma_CS2_RENAN

Main application package for the Macena CS2 Analyzer — an AI-powered tactical coach for Counter-Strike 2.

## Overview

This package contains the complete application codebase organized into a layered architecture following the **WATCH > LEARN > THINK > SPEAK** pipeline:

```
WATCH (Ingestion)  →  LEARN (Training)  →  THINK (Inference)  →  SPEAK (Dialogue)
    Hunter daemon        Teacher daemon       COPER pipeline       Template + Ollama
    Demo parsing         3-stage maturity     RAG knowledge        Causal attribution
    Feature extraction   Multi-model train    Game theory          Pro comparisons
```

## Structure

```
Programma_CS2_RENAN/
├── apps/desktop_app/       Kivy/KivyMD desktop UI (MVVM pattern)
├── backend/                Business logic layer
│   ├── analysis/           Game theory, belief models, momentum
│   ├── coaching/           Coaching pipeline (COPER, Hybrid, RAG)
│   ├── data_sources/       Demo parser, HLTV, Steam, Faceit APIs
│   ├── knowledge/          RAG knowledge base, COPER experience bank
│   ├── nn/                 Neural networks (6 model types)
│   ├── processing/         Feature engineering, baselines, validation
│   ├── services/           Service layer (Coaching, Analysis, Ollama)
│   └── storage/            SQLite database, models, backup
├── core/                   Session engine, asset management, spatial data
├── ingestion/              Demo ingestion pipelines (HLTV, Steam)
├── observability/          RASP integrity, telemetry, Sentry
├── reporting/              Visualization, PDF generation
├── tests/                  Test suite (390+ tests)
└── tools/                  Validation and diagnostic tools
```

## Key Entry Points

| File | Purpose |
|------|---------|
| `apps/desktop_app/main.py` | Desktop application (Kivy GUI) |
| `run_ingestion.py` | Demo ingestion pipeline |
| `fetch_hltv_stats.py` | HLTV professional metadata scraping |
| `hltv_sync_service.py` | Background HLTV sync daemon |

## Technology Stack

- **UI**: Kivy + KivyMD
- **ML**: PyTorch, ncps (LTC), Hopfield networks
- **Database**: SQLite (WAL mode) via SQLModel
- **Scraping**: Playwright (sync)
- **Observability**: TensorBoard, Sentry
