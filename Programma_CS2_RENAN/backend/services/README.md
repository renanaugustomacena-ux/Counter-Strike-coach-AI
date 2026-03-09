# Application Service Layer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Overview

High-level service orchestration layer providing coaching, analysis, visualization, and LLM integration. Services coordinate multiple backend modules and provide business logic for the desktop application.

## Key Services

### `coaching_service.py`
- **`CoachingService`** — Main coaching engine with 4 modes: COPER (default), Hybrid, RAG, Neural Network
- Temporal baseline enrichment via `_get_temporal_baseline()` and `_baseline_context_note()`
- Experience Bank integration for historical insight retrieval
- Pro reference comparison and tactical knowledge RAG

### `analysis_orchestrator.py`
- **`AnalysisOrchestrator`** — Coordinates all analysis engines (game theory, belief models, momentum, spatial, role classification)
- Factory pattern for engine instantiation

### `analysis_service.py`
- **`AnalysisService`** — Performance analysis, feature drift detection, pro comparison
- `check_for_drift()` now wired to real `detect_feature_drift()` using last 50 matches from DB

### `coaching_dialogue.py`
- **`CoachingDialogueEngine`** — Interactive multi-turn coaching conversations with context tracking

### `lesson_generator.py`
- **`LessonGenerator`** — Structured lesson generation with drills and practice recommendations

### `ollama_writer.py`
- **`OllamaCoachWriter`** — Ollama LLM integration for natural language polishing of coaching insights
- Transforms structured insights into conversational coaching text

### `llm_service.py`
- **`LLMService`** — Abstract LLM provider wrapper with retry logic and timeout handling

### `visualization_service.py`
- **`VisualizationService`** — Orchestrates heatmap, engagement map, and momentum chart generation

## Integration Pattern

Services are instantiated in `main.py` and used by UI screens. All services use dependency injection for database manager and config.
