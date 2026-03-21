# Services -- Application Service Orchestration Layer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Authority:** Rule 1 (Correctness), Rule 2 (Backend Sovereignty)
> **Skills:** `/api-contract-review`, `/state-audit`, `/correctness-check`

## Introduction

This is the top-level service layer that coordinates between backend analysis modules
and the UI. Services in this directory are the primary entry points for the desktop
application -- they orchestrate coaching generation, analysis pipelines, LLM
integration, player profile management, visualization rendering, and telemetry
dispatch. Each service encapsulates a distinct business capability while depending on
lower-level modules (storage, processing, analysis, knowledge) for data and
computation.

All services use dependency injection for `DatabaseManager` access (via
`get_db_manager()` singleton) and structured logging (via
`get_logger("cs2analyzer.<module>")`).

## File Inventory

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 0 | Package marker | -- |
| `coaching_service.py` | ~950 | Main coaching orchestrator (4 modes) | `CoachingService` |
| `analysis_orchestrator.py` | ~830 | Phase 6 analysis coordination (9 engines) | `AnalysisOrchestrator`, `MatchAnalysis`, `RoundAnalysis` |
| `analysis_service.py` | 92 | Performance analysis and drift detection | `AnalysisService`, `get_analysis_service()` |
| `coaching_dialogue.py` | 391 | Interactive multi-turn coaching chat | `CoachingDialogueEngine`, `get_dialogue_engine()` |
| `lesson_generator.py` | 382 | Structured lesson generation from demos | `LessonGenerator`, `check_lesson_system_status()` |
| `llm_service.py` | 253 | Ollama LLM provider wrapper | `LLMService`, `get_llm_service()`, `check_ollama_status()` |
| `ollama_writer.py` | 110 | Natural language polishing for insights | `OllamaCoachWriter`, `get_ollama_writer()` |
| `profile_service.py` | 167 | Steam/FaceIT profile integration | `ProfileService` |
| `telemetry_client.py` | 60 | Match telemetry dispatch to ML server | `send_match_telemetry()` |
| `visualization_service.py` | 131 | Radar charts and comparison plots | `VisualizationService`, `get_visualization_service()` |

## Architecture and Concepts

### `CoachingService` -- Main Coaching Orchestrator

The central coaching engine with a prioritized 4-mode fallback chain (P9-03):

1. **COPER** (default, `USE_COPER_COACHING=True`): Context-aware coaching using
   Experience Bank + RAG + Pro References. Requires `map_name` and `tick_data`.
2. **Hybrid** (`USE_HYBRID_COACHING=True`): ML predictions synthesized with RAG
   knowledge retrieval. Requires `player_stats`.
3. **Traditional + RAG** (`USE_RAG_COACHING=True`): Correction engine enhanced with
   tactical knowledge retrieval.
4. **Traditional** (always available): Pure deviation-based correction engine. Lowest
   fidelity, zero external dependencies. Ultimate fallback.

Fallback transitions: COPER failure -> Hybrid (if enabled) -> Traditional.

Post-coaching pipelines (non-blocking):
- Phase 6 Advanced Analysis (momentum, deception, entropy, game theory)
- Longitudinal Trend Coaching (regression/improvement detection via `compute_trend()`)
- Ollama natural language polishing (via `OllamaCoachWriter`)
- Explainability narratives (via `ExplanationGenerator`)

Key method: `generate_new_insights(player_name, demo_name, deviations,
rounds_played, map_name, player_stats, tick_data)`.

Timeout protection: All coaching generation runs through `_run_with_timeout()` with
a 30-second default (`_COACHING_TIMEOUT`) to prevent UI hangs when SBERT download,
FAISS search, or Ollama polishing stalls.

### `AnalysisOrchestrator` -- Phase 6 Analysis Coordination

Coordinates 9 analysis engines and produces `CoachingInsight` objects for database
storage:

| Step | Engine | Input Required | Focus Area |
|------|--------|----------------|------------|
| 1 | Momentum Tracker | `round_outcomes` | Tilt/hot-streak detection |
| 2 | Deception Analyzer | `tick_data` | Fake play identification |
| 3 | Entropy Analyzer | `tick_data` | Utility usage predictability |
| 4 | Game Tree + Blind Spots | `game_states` | Strategic decision alternatives |
| 5 | Engagement Range | `tick_data` | Optimal fight distances |
| 6 | Win Probability | `game_states` | Round win prediction accuracy |
| 7 | Role Classifier | `player_stats` | Player role identification |
| 8 | Utility Analyzer | `player_stats` | Utility usage efficiency |
| 9 | Economy Optimizer | `game_states` | Buy/save decision analysis |

Data structures: `RoundAnalysis` (per-round insights) and `MatchAnalysis`
(aggregated match insights with `all_insights` property).

Module failure tracking: Uses `_module_failure_counts` with log suppression
(first 3, then every 10th) to prevent log flooding from persistent engine failures.

### `AnalysisService` -- Performance Analysis

Lightweight service for performance retrieval and drift detection:

- `analyze_latest_performance(player_name)`: Fetches latest `PlayerMatchStats`
- `get_pro_comparison(player_name, pro_name)`: Side-by-side user vs pro stats
- `check_for_drift(player_name)`: Detects feature drift using the last 100 matches
  via `detect_feature_drift()` from the validation module

### `CoachingDialogueEngine` -- Interactive Coaching Chat

Multi-turn coaching dialogue with RAG and Experience Bank augmentation:

- **Session lifecycle**: `start_session()` -> `respond()` (repeated) -> `clear_session()`
- **Intent classification**: Keyword-based routing into 4 categories (positioning,
  utility, economy, aim) plus "general" fallback
- **RAG augmentation**: Each user message triggers `KnowledgeRetriever` and
  `ExperienceBank` retrieval, injected as context into the LLM prompt
- **Sliding context window**: Last `MAX_CONTEXT_TURNS * 2` messages (default 12)
- **Thread safety**: All mutable state protected by `_state_lock` (threading.Lock)
- **Offline fallback**: Template-based responses with RAG knowledge when Ollama is
  unavailable

Singleton: `get_dialogue_engine()` with double-checked locking.

### `LessonGenerator` -- Structured Demo Lessons

Generates educational coaching lessons from demo analysis:

- `generate_lesson(demo_name, focus_area)`: Produces a multi-section lesson with
  overview, strengths, improvements, pro tips, and optional LLM narrative
- Named thresholds: `_ADR_STRONG_THRESHOLD`, `_HS_WEAK_THRESHOLD`,
  `_DEATH_RATIO_WARNING`, etc. -- no magic numbers
- Map-specific pro tips for mirage, inferno, dust2, ancient, nuke
- `check_lesson_system_status()`: Diagnostic function returning LLM and DB health

### `LLMService` -- Ollama Integration

Wraps the Ollama REST API for local LLM inference:

- **Endpoints**: `/api/generate` (single-shot) and `/api/chat` (multi-turn)
- **Availability caching**: 60-second TTL on `is_available()` checks
- **Auto model selection**: If the configured model is not found, falls back to
  the first available model
- **Error markers**: All error responses start with `[LLM` prefix for easy
  downstream detection
- Specialized methods: `generate_lesson()`, `explain_round_decision()`,
  `generate_pro_tip()`

### `OllamaCoachWriter` -- Natural Language Polishing

Transforms structured coaching data into conversational advice via Ollama:

- `polish(title, message, focus_area, severity, map_name)`: Enhances a coaching
  message; returns original text unchanged if Ollama is disabled or unavailable
- Feature flag: `USE_OLLAMA_COACHING` setting controls enablement
- Lazy initialization of LLM service to avoid import-time HTTP calls

### `ProfileService` -- External Profile Integration

Manages Steam and FaceIT profile synchronization:

- `fetch_steam_stats(steam_id)`: Fetches player info and CS2 playtime hours
  with bounded retry (3 attempts, exponential backoff)
- `fetch_faceit_stats(nickname)`: Fetches FaceIT Elo and skill level
- `sync_all_external_data()`: Orchestrates both fetches and persists to
  `PlayerProfile` in the database
- Security: API keys loaded from keyring/env via `get_credential()`, never
  hard-coded (F5-22)
- Guard (AC-28-01): Skips profile save when both fetches fail

### `VisualizationService` -- Chart Rendering

Generates matplotlib-based visualizations:

- `generate_performance_radar(user_stats, pro_stats, output_path)`: Polar radar
  chart comparing user vs pro performance, saved to file
- `plot_comparison_v2(p1_name, p2_name, p1_stats, p2_stats)`: Comparison radar
  chart returned as `io.BytesIO` buffer for Qt embedding

### `telemetry_client` -- Match Telemetry Dispatch

Sends match statistics to a central ML Coach server via httpx:

- Optional dependency: `httpx` is try/except imported; degrades gracefully
- Endpoint: `POST /api/ingest/telemetry` at `CS2_TELEMETRY_URL`
- No fabricated test data (Anti-Fabrication Rule)

## Integration

```
Desktop App (Qt)
    |
    +-- Screens / ViewModels
            |
            +-- CoachingService.generate_new_insights()
            |       +-- correction_engine (traditional)
            |       +-- coper_engine (Experience Bank + RAG)
            |       +-- hybrid_engine (ML + RAG)
            |       +-- OllamaCoachWriter.polish()
            |       +-- AnalysisOrchestrator.analyze_match()
            |
            +-- CoachingDialogueEngine.respond()
            |       +-- LLMService.chat()
            |       +-- KnowledgeRetriever.retrieve()
            |       +-- ExperienceBank.retrieve_similar()
            |
            +-- LessonGenerator.generate_lesson()
            |       +-- LLMService.generate_lesson()
            |
            +-- ProfileService.sync_all_external_data()
            |       +-- Steam API / FaceIT API
            |
            +-- VisualizationService.generate_performance_radar()
```

## Development Notes

- **Singleton pattern**: Most services expose a `get_*()` factory function for
  thread-safe singleton access. Use these instead of direct construction.
- **Timeout protection**: `CoachingService` wraps expensive calls in
  `_run_with_timeout()` to prevent UI thread blocking.
- **Graceful degradation**: Every service degrades cleanly when external
  dependencies (Ollama, Steam API, FaceIT API) are unavailable.
- **No hard-coded secrets**: All API keys use `get_credential()` from
  `core/config.py`, loaded from OS keyring or environment variables.
- **Structured logging**: All services use `get_logger("cs2analyzer.<module>")`
  with structured JSON output and correlation IDs.
- **Thread safety**: `CoachingDialogueEngine` and `CoachingService` protect mutable
  state with explicit locks. Singletons use double-checked locking patterns.
