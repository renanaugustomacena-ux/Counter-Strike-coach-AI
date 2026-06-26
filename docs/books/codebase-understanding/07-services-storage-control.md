# Chapter 7 — Services, Storage, Control, Onboarding, and Top-Level Scripts

> Exhaustive reference covering every class, function, constant, dataclass, enum, singleton pattern, and design decision found in the Services layer, Storage layer, Control layer, Onboarding subsystem, and root-level CLI entry points of the Macena CS2 Analyzer.

---

## Table of Contents

1. [Services Layer](#1-services-layer)
   1. [Analysis Orchestrator](#11-analysis-orchestrator)
   2. [Analysis Service](#12-analysis-service)
   3. [Coaching Dialogue Engine](#13-coaching-dialogue-engine)
   4. [Coaching Service](#14-coaching-service)
   5. [Lesson Generator](#15-lesson-generator)
   6. [LLM Service](#16-llm-service)
   7. [Ollama Writer](#17-ollama-writer)
   8. [Player Lookup](#18-player-lookup)
   9. [Profile Service](#19-profile-service)
   10. [Telemetry Client](#110-telemetry-client)
   11. [Visualization Service](#111-visualization-service)
2. [Server](#2-server)
   1. [FastAPI Utility Server](#21-fastapi-utility-server)
3. [Storage Layer](#3-storage-layer)
   1. [Backup Manager](#31-backup-manager)
   2. [Database Manager](#32-database-manager)
   3. [DB Backup Utilities](#33-db-backup-utilities)
   4. [DB Migrate](#34-db-migrate)
   5. [DB Models](#35-db-models)
   6. [Maintenance](#36-maintenance)
   7. [Match Data Manager](#37-match-data-manager)
   8. [Remote File Server](#38-remote-file-server)
   9. [Stat Aggregator](#39-stat-aggregator)
   10. [State Manager](#310-state-manager)
   11. [Storage Manager](#311-storage-manager)
4. [Control Layer](#4-control-layer)
   1. [Console (Backend)](#41-console-backend)
   2. [Database Governor](#42-database-governor)
   3. [Ingestion Manager](#43-ingestion-manager)
   4. [ML Controller](#44-ml-controller)
5. [Onboarding](#5-onboarding)
   1. [New User Flow](#51-new-user-flow)
6. [Top-Level Scripts](#6-top-level-scripts)
   1. [console.py — Unified Console v3.0](#61-consolepy--unified-console-v30)
   2. [goliath.py — Master Authority Orchestrator](#62-goliathpy--master-authority-orchestrator)
7. [Cross-Cutting Patterns](#7-cross-cutting-patterns)

---

## 1. Services Layer

**Location:** `Programma_CS2_RENAN/backend/services/`

The services layer provides the application's business logic — coaching, analysis, LLM integration, player lookup, visualization, and external data synchronization. Every service follows the singleton pattern with double-checked locking via module-level `threading.Lock` objects.

### 1.1 Analysis Orchestrator

**File:** `services/analysis_orchestrator.py`

The Analysis Orchestrator is the central integration point for Phase 6 analysis. It coordinates 11 independent analysis modules that each examine a different facet of match performance.

#### Dataclasses

- **`RoundAnalysis`**: Holds `round_number: int` and `insights: List[CoachingInsight]`. Represents the analytical output for a single round.

- **`MatchAnalysis`**: Holds `player_name: str`, `demo_name: str`, `round_analyses: List[RoundAnalysis]`, and `match_insights: List[CoachingInsight]`. Provides a property `all_insights` that aggregates both round-level and match-level insights into a single flat list.

#### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `_LOG_SUPPRESSION_INITIAL` | `3` | Number of initial failures before log messages are suppressed for a module |
| `_LOG_SUPPRESSION_INTERVAL` | `10` | After initial suppression, log only every Nth failure |

#### Class: `AnalysisOrchestrator`

**Constructor (`__init__`)**: Lazily imports and instantiates 11 analysis modules from `backend/analysis/`:
1. `MomentumAnalyzer`
2. `DeceptionAnalyzer`
3. `UtilityEntropyAnalyzer`
4. `GameTreeAnalyzer` (for strategy/game tree analysis)
5. `BlindSpotDetector`
6. `EngagementRangeAnalyzer`
7. `WinProbabilityAnalyzer`
8. `RoleClassifier`
9. `UtilityAnalyzer`
10. `EconomyOptimizer`
11. `DeathProbabilityModel`
12. `MovementQualityAnalyzer`

Each module is wrapped in a try/except so that import failures for individual modules do not crash the entire orchestrator. A `_failure_counts` dictionary tracks per-module failure counts for log suppression.

**Methods:**

- **`analyze_match(demo_name, player_name, match_data, round_data_list)`**: Main entry point. Iterates over all rounds and runs each analysis module against each round. Collects `CoachingInsight` objects from each module. Returns a `MatchAnalysis` object. Each module runs in a try/except with failure recording.

- **`_record_module_failure(module_name, error)`**: Implements log suppression. For the first `_LOG_SUPPRESSION_INITIAL` failures of a module, logs at WARNING level. After that, logs only every `_LOG_SUPPRESSION_INTERVAL` failures. This prevents log flooding when a module consistently fails.

- **`_analyze_momentum(round_data)`**: Delegates to `MomentumAnalyzer.analyze()`. Returns a list of `CoachingInsight` for momentum shifts detected within the round.

- **`_analyze_deception(round_data)`**: Delegates to `DeceptionAnalyzer.analyze()`. Detects deceptive plays (fakes, feints).

- **`_analyze_utility_entropy(round_data)`**: Delegates to `UtilityEntropyAnalyzer.analyze()`. Measures randomness/predictability of utility usage.

- **`_analyze_strategy(round_data)`**: Delegates to `GameTreeAnalyzer.analyze()`. Evaluates strategic decision quality.

- **`_analyze_engagement_range(round_data)`**: Delegates to `EngagementRangeAnalyzer.analyze()`. Assesses whether engagements occur at optimal ranges for the player's weapons.

- **`_analyze_win_probability(round_data)`**: Delegates to `WinProbabilityAnalyzer.analyze()`. Calculates real-time win probability curves.

- **`_analyze_role(round_data)`**: Delegates to `RoleClassifier.classify()`. Determines the player's in-round role (entry fragger, support, AWPer, etc.).

- **`_analyze_utility(round_data)`**: Delegates to `UtilityAnalyzer.analyze()`. Evaluates utility efficiency (flashbang effectiveness, smoke placement, etc.).

- **`_analyze_economy(round_data)`**: Delegates to `EconomyOptimizer.analyze()`. Assesses economic decisions (buy/save/eco/force).

- **`_analyze_death_probability(round_data)`**: Delegates to `DeathProbabilityModel.analyze()`. Estimates survivability based on positioning and timing.

- **`_analyze_movement_quality(round_data)`**: Delegates to `MovementQualityAnalyzer.analyze()`. Evaluates movement patterns (counter-strafing, peek quality, jiggle peeks).

#### Singleton

- **`_orchestrator_lock`**: Module-level `threading.Lock`.
- **`get_analysis_orchestrator()`**: Thread-safe singleton factory using double-checked locking pattern. Returns the single `AnalysisOrchestrator` instance.

---

### 1.2 Analysis Service

**File:** `services/analysis_service.py`

A database-backed analysis facade that provides high-level performance analysis queries.

#### Class: `AnalysisService`

**Constructor**: Creates an `EliteAnalytics` instance and acquires the `DatabaseManager` via `get_db_manager()`.

**Methods:**

- **`analyze_latest_performance(player_name: str)`**: Queries the database for the player's most recent match stats and feeds them through `EliteAnalytics` for performance scoring and trend analysis. Returns a structured result with ratings, strengths, and improvement areas.

- **`get_pro_comparison(player_name: str, pro_name: str)`**: Fetches stats for both the player and a professional player from the database, then runs a comparative analysis. Returns a side-by-side comparison with skill deltas.

- **`check_for_drift(player_name: str)`**: Uses `detect_feature_drift()` to identify whether the player's recent performance has shifted significantly from their historical baseline. Returns drift indicators.

#### Factory

- **`get_analysis_service()`**: Simple factory function (not a full singleton) that creates and returns a new `AnalysisService` instance.

---

### 1.3 Coaching Dialogue Engine

**File:** `services/coaching_dialogue.py` (~1384 lines)

The coaching dialogue engine manages multi-turn conversational coaching sessions. It integrates LLM generation, RAG retrieval, intent classification, player entity detection, and context assembly into a coherent dialogue system.

#### Constants

| Constant | Value | Source | Purpose |
|----------|-------|--------|---------|
| `_DIALOGUE_TIMEOUT` | `180` | Env `CS2_DIALOGUE_TIMEOUT` | Maximum seconds for a dialogue response |
| `_OPENING_TIMEOUT` | `90` | Env `CS2_OPENING_TIMEOUT` | Maximum seconds for session opening generation |
| `_FALLBACK_RETRY_TIMEOUT` | `90` | Env `CS2_FALLBACK_TIMEOUT` | Timeout for fallback response generation |

#### Intent Classification

- **`INTENT_KEYWORDS`**: A dictionary mapping 7 intent categories to keyword lists:
  - `strategy`: keywords related to tactical play, rotations, site execution
  - `aim`: keywords for mechanical skill, crosshair placement, recoil control
  - `economy`: keywords for buy decisions, eco rounds, economy management
  - `utility`: keywords for grenades, smokes, flashes, molotovs
  - `positioning`: keywords for angles, map control, off-angles
  - `review`: keywords for match/round review, replay analysis
  - `general`: catch-all category

#### Pattern Constants

- **`_ROUND_PATTERN`**: Compiled regex for extracting round numbers from user messages (e.g., "round 5", "r5", "round five").
- **`_DEMO_PATTERN`**: Compiled regex for detecting demo file references in user messages.
- **`_CS2_MAP_NAMES`**: Frozenset of 9 official competitive CS2 map names: `{'mirage', 'inferno', 'dust2', 'overpass', 'nuke', 'ancient', 'anubis', 'vertigo', 'train'}`.

#### Pronoun Transformation

- **`_SECOND_TO_THIRD_PERSON`**: Tuple of 18 `(regex_pattern, replacement_string)` pairs used by `_to_third_person()` to convert second-person coaching insights ("you should") into third-person references ("s1mple should") when discussing pro players.

#### Text Safety

- **`_CONTROL_CHARS_RE`**: Compiled regex matching Unicode control characters (categories Cc and Cf). Used by `_sanitize_llm_context()` to strip potentially dangerous characters from text injected into LLM prompts (BE-03 security requirement).

- **`_sanitize_llm_context(text: str, max_len: int = 300) -> str`**: Strips control characters, collapses whitespace, and truncates to `max_len` characters. Prevents prompt injection through malformed data.

- **`_to_third_person(text: str, pro_name: str, attribute: bool = True) -> str`**: Converts second-person text to third-person by applying the `_SECOND_TO_THIRD_PERSON` regex pairs and optionally prefixing with the pro player's name.

#### System Prompt

- **`SYSTEM_PROMPT_TEMPLATE`**: A massive multi-paragraph template defining the coaching persona. Contains critical rules:
  - Factual accuracy requirements (never fabricate statistics)
  - Data provenance (cite source of every statistic)
  - Data honesty (WR-78): explicitly state when data is unavailable rather than inventing it
  - Format instructions for structured responses
  - Player context placeholders (`{player_context}`, `{system_context}`)
  - Brace escaping for injection prevention (BE-03)

#### Class: `CoachingDialogueEngine`

**Class Constants:**
- `MAX_CONTEXT_TURNS = 6`: Maximum number of conversation turns to include in LLM context window.
- `RETRIEVAL_TOP_K = 3`: Maximum number of RAG results to include per retrieval query.

**Constructor (`__init__`)**: Initializes:
- `LLMService` instance (via `get_llm_service()`)
- `CoachingService` instance (via `get_coaching_service()`)
- Optional RAG retriever (via `get_tactical_retriever()`, can be None)
- Session storage: `_sessions` dict mapping session IDs to conversation histories
- Session lock: `_session_lock` for thread-safe session access

**Session Lifecycle Methods:**

- **`start_session(player_name: str, demo_name: str = None) -> str`**: Creates a new session ID (UUID4), initializes the conversation history, builds player context, generates an opening message (LLM-generated or offline fallback), and returns the session ID.

- **`respond(session_id: str, user_message: str) -> str`**: Main response method. Classifies user intent, detects player mentions, retrieves relevant context (RAG, experience bank, round data, match overview, analytical data), builds the full prompt with conversation history, and calls the LLM with timeout. Falls back to `_fallback_response()` on failure.

- **`get_history(session_id: str) -> List[Dict]`**: Returns the conversation history for a session as a list of `{"role": "user"|"assistant", "content": "..."}` dictionaries.

- **`clear_session(session_id: str)`**: Removes a session from the `_sessions` dictionary, freeing memory.

**Internal Methods:**

- **`_chat_with_timeout(messages, system_prompt, timeout) -> str`**: Wraps the LLM chat call in a thread with a timeout. If the LLM does not respond within the timeout, raises `TimeoutError`. Uses `threading.Thread` with `join(timeout)`.

- **`_build_player_context(player_name: str, demo_name: str = None) -> str`**: Queries the database for the player's recent match statistics. If the player is found in the HLTV database (pro player), includes pro insights. Returns a formatted context string with verified data blocks.

- **`_build_system_prompt(player_context: str) -> str`**: Fills the `SYSTEM_PROMPT_TEMPLATE` with the player context. Escapes curly braces in the player context to prevent format string injection (BE-03).

- **`_classify_intent(message: str) -> Tuple[str, List[str]]`**: Two-phase intent classification:
  1. Keyword matching against `INTENT_KEYWORDS` dictionary
  2. Player entity detection using `PlayerLookupService.detect_player_mentions()`
  Returns `(intent_category, detected_player_names)`.

- **`_retrieve_context(intent, player_names, session) -> str`**: Assembles retrieval context from multiple sources:
  1. RAG retrieval (tactical knowledge base) if retriever is available
  2. Experience Bank retrieval for relevant coaching experiences
  3. Round drill-down data if a specific round is mentioned
  4. Match overview if the session has a demo loaded
  5. Analytical context from Phase 6 modules

- **`_retrieve_analytical_context(player_name, demo_name) -> str`**: Runs the `AnalysisOrchestrator` on the current match to generate live analytical insights.

- **`_retrieve_round_drill_down(session, round_number) -> str`**: Fetches detailed tick-by-tick data for a specific round from the `MatchDataManager`.

- **`_retrieve_match_overview(session) -> str`**: Generates a high-level summary of the entire match including scoreline, player performance, and round progression.

- **`_format_player_analytics(player_stats) -> str`** (static method): Formats raw player statistics into a human-readable block including:
  - Match statistics (kills, deaths, ADR, HLTV rating)
  - Best rounds (highest-impact rounds)
  - Round timeline (kill/death events per round)
  - ML-backed insights (if available)

- **`_get_ml_analysis_for_players(player_names) -> str`**: Runs the neural network model's prediction pipeline on-demand for the specified players. Returns formatted ML insights or an empty string on failure.

- **`_generate_opening(player_name, player_context) -> str`**: Generates the initial coaching greeting using the LLM. Includes player-specific data in the system prompt.

- **`_offline_opening(player_name) -> str`**: Returns a static opening message when the LLM is unavailable. Provides a template-based greeting.

- **`_fallback_response(user_message, intent) -> str`**: Generates a context-aware fallback response when the LLM fails or times out. Uses intent classification to provide relevant static advice.

#### Singleton

- **`_engine_lock`**: Module-level `threading.Lock`.
- **`get_dialogue_engine()`**: Thread-safe singleton factory with double-checked locking.

---

### 1.4 Coaching Service

**File:** `services/coaching_service.py` (~983 lines)

The coaching service is the unified orchestrator for all coaching insight generation. It implements a four-mode priority chain and integrates Phase 6 analysis, longitudinal tracking, and pro comparison.

#### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `_COACHING_TIMEOUT` | `30` | Timeout in seconds for individual coaching operations |

#### Helper Functions

- **`_run_with_timeout(func, args, kwargs, timeout) -> Any`**: Generic timeout wrapper. Runs `func(*args, **kwargs)` in a thread and raises `TimeoutError` if it exceeds `timeout` seconds.

#### Feature Mapping Dictionaries

- **`_FEATURE_TO_AXIS`**: Maps 16 internal feature names (e.g., `"avg_kills"`, `"avg_headshot_pct"`) to `SkillAxes` enum values for radar chart visualization. This bridges the gap between raw feature names and the UI's skill axis taxonomy.

- **`_FEATURE_HUMAN_NAMES`**: Maps the same 16 internal feature keys to human-readable labels (e.g., `"avg_kills"` -> `"Kills per Match"`, `"avg_headshot_pct"` -> `"Headshot %"`).

#### Class: `CoachingService`

**Constructor (`__init__`)**: Reads three boolean configuration flags that determine the coaching mode:
- `use_rag` (default: True) — Whether RAG-enhanced coaching is enabled
- `use_hybrid` (default: True) — Whether hybrid ML+RAG coaching is enabled
- `use_coper` (default: True) — Whether COPER framework coaching is enabled

These flags create the four-mode priority chain documented in the class docstring:
1. **COPER mode** (highest priority): Context-Oriented Player Experience Replay — uses the Experience Bank plus temporal baselines
2. **Hybrid mode**: Combines ML predictions with RAG tactical knowledge
3. **Traditional + RAG**: Uses pre-built coaching rules enhanced by RAG retrieval
4. **Traditional**: Pure rule-based coaching (lowest priority, always available)

**Methods:**

- **`_get_temporal_baseline(map_name: str) -> dict`**: Fetches the temporal baseline for a specific map using `TemporalBaselineDecay`. Falls back to the legacy static baseline if temporal data is unavailable.

- **`generate_new_insights(player_name, demo_name, match_data, focus_area=None) -> List[CoachingInsight]`**: Main entry point. Selects the coaching mode based on the priority chain and available infrastructure. Runs:
  1. Mode-specific insight generation
  2. Phase 6 advanced analysis (non-blocking)
  3. Longitudinal trend coaching
  Returns combined insights from all sources.

- **`_generate_coper_insights(player_name, demo_name, match_data, focus_area) -> List[CoachingInsight]`**: COPER mode implementation. Queries the `ExperienceBank` for similar past experiences, applies temporal baseline comparison, and generates context-rich coaching insights.

- **`_format_coper_message(experience, baseline_note) -> str`**: Formats a COPER experience into a human-readable coaching message with baseline context.

- **`_baseline_context_note(feature_name, player_value, baseline) -> str`**: Generates a contextual note comparing the player's current value to the pro baseline (e.g., "Your ADR of 65.2 is below the pro average of 78.1").

- **`_infer_round_phase(round_data) -> str`**: Determines the phase of a round (early, mid, late, post-plant) based on tick timing.

- **`_health_to_range(health) -> str`**: Converts a health value to a descriptive range label (critical/low/mid/high/full).

- **`_generate_advanced_insights(player_name, demo_name, match_data) -> List[CoachingInsight]`**: Runs Phase 6 analysis through the `AnalysisOrchestrator` in a non-blocking manner with timeout protection.

- **`_run_longitudinal_coaching(player_name, new_insights) -> List[CoachingInsight]`**: Trend-aware coaching. Compares current match insights against the player's historical coaching insights to detect recurring patterns and track improvement/regression.

- **`_find_best_match_pro(player_name, player_stats) -> Tuple[str, float]`**: Finds the closest-matching professional player by HLTV rating. Returns `(pro_name, rating_delta)`.

- **`_generate_hybrid_insights(player_name, demo_name, match_data, focus_area) -> List[CoachingInsight]`**: Hybrid mode. Runs ML model predictions and enhances results with RAG-retrieved tactical knowledge.

- **`_enhance_with_rag(insights, focus_area) -> List[CoachingInsight]`**: Takes existing insights and enriches them with relevant tactical knowledge from the RAG knowledge base.

- **`generate_differential_insights(player_name, match1_stats, match2_stats) -> List[CoachingInsight]`**: Generates insights based on the difference between two matches. Used for positional heatmap comparison.

- **`get_latest_insights(player_name: str, limit: int = 5) -> List[CoachingInsight]`**: Queries the database for the player's most recent coaching insights, ordered by creation date descending.

#### Helper Functions (Module Level)

- **`_save_corrections_as_insights(player_name, corrections) -> List[CoachingInsight]`**: Converts correction objects (from the COPER Experience Bank) into `CoachingInsight` database records.

- **`_create_insight_obj(player_name, title, message, focus_area, severity) -> CoachingInsight`**: Factory function for creating `CoachingInsight` ORM objects with consistent field population.

- **`_save_generic_insight(player_name, title, message, focus_area, severity) -> CoachingInsight`**: Creates and persists a generic coaching insight to the database.

#### Singleton

- **`_coaching_service_lock`**: Module-level `threading.Lock`.
- **`get_coaching_service()`**: Thread-safe singleton factory with double-checked locking.

---

### 1.5 Lesson Generator

**File:** `services/lesson_generator.py`

Generates structured coaching lessons from demo analysis data. Each lesson contains an overview, strengths, improvements, pro tips, and a narrative summary.

#### Threshold Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `_ADR_STRONG_THRESHOLD` | `75.0` | ADR above this is considered a strength |
| `_ADR_WEAK_THRESHOLD` | `60.0` | ADR below this triggers an improvement suggestion |
| `_HS_STRONG_THRESHOLD` | `0.40` | Headshot percentage above 40% is a strength |
| `_HS_WEAK_THRESHOLD` | `0.35` | Headshot percentage below 35% triggers improvement |
| `_RATING_ABOVE_AVG` | `1.0` | HLTV rating above 1.0 is above average |
| `_KAST_STRONG_THRESHOLD` | `0.70` | KAST above 70% is a strength |
| `_DEATH_RATIO_WARNING` | `1.5` | Deaths-to-kills ratio above 1.5 triggers a warning |
| `_MIN_DEATHS_FOR_WARNING` | `15` | Minimum deaths required before the death ratio warning applies |

#### Class: `LessonGenerator`

**Constructor**: Lazy-loads the database manager on first use to avoid import-time side effects.

**Methods:**

- **`generate_lesson(demo_name: str, focus_area: str = None) -> dict`**: Main entry point. Fetches match data from the database and generates a structured lesson with sections:
  - `overview`: Match summary (map, score, result)
  - `strengths`: List of identified strengths based on thresholds
  - `improvements`: List of areas needing improvement
  - `pro_tips`: Map-specific tactical tips
  - `narrative`: Natural language summary of the match

- **`_get_match_data(demo_name) -> dict`**: Queries `PlayerMatchStats` for the demo. Returns a dictionary of match statistics.

- **`_generate_overview(match_data) -> str`**: Builds a textual overview including map name, final score, and match duration.

- **`_generate_strengths(match_data) -> List[str]`**: Evaluates match statistics against the threshold constants and returns a list of strength descriptions.

- **`_generate_improvements(match_data) -> List[str]`**: Evaluates match statistics against the threshold constants and returns improvement suggestions.

- **`_generate_pro_tips(match_data) -> List[str]`**: Returns map-specific tactical tips. Has hardcoded tip lists for mirage, inferno, dust2, ancient, and nuke. Falls back to generic tips for other maps.

- **`_generate_narrative(match_data) -> str`**: Composes a natural-language paragraph summarizing the player's performance.

- **`get_available_demos(limit: int = 20) -> List[str]`**: Queries the database for recent demo names, limited to `limit` results.

#### Status Check

- **`check_lesson_system_status() -> dict`**: Diagnostic function that checks whether the lesson generation system is operational (database accessible, demos available).

---

### 1.6 LLM Service

**File:** `services/llm_service.py`

Wraps the Ollama local LLM API for text generation and chat.

#### Constants

- **`OLLAMA_URL`**: Read from environment variable `OLLAMA_URL`, defaults to `"http://localhost:11434"`.

#### Functions

- **`_resolve_default_model() -> str`**: Resolves the default LLM model with a three-tier priority:
  1. Environment variable `OLLAMA_MODEL`
  2. User setting `LLM_COACH_MODEL` from `settings.json`
  3. Hardcoded fallback: `"gemma4:e2b"`

#### Class: `LLMService`

**Constructor**: Initializes the Ollama URL, default model name, and an availability cache with a 60-second TTL.

**Methods:**

- **`list_models() -> List[dict]`**: Calls the Ollama `/api/tags` endpoint to list all locally available models. Returns the parsed JSON response.

- **`is_available() -> bool`**: Checks if Ollama is running and the configured model is available. Uses a 60-second cache to avoid repeated network calls. If the exact model is not found, attempts a model family fallback (e.g., if `"gemma4:e2b"` is not found, checks for any model in the `"gemma4"` family).

- **`generate(prompt: str, system_prompt: str = None) -> str`**: Calls the Ollama `/api/generate` endpoint with parameters:
  - `timeout=600` seconds
  - `temperature=0.7`
  - `top_p=0.9`
  - `num_ctx=32768` (context window)
  Returns the generated text response.

- **`chat(messages: List[dict], system_prompt: str = None) -> str`**: Calls the Ollama `/api/chat` endpoint for multi-turn conversation. Same timeout and parameter configuration as `generate()`.

- **`generate_lesson(insights: List) -> str`**: Convenience method that formats coaching insights into a prompt and calls `generate()` to produce a natural-language lesson.

- **`explain_round_decision(round_data: dict) -> str`**: Takes round data and generates an explanation of key decisions made during the round.

- **`generate_pro_tip(context: str) -> str`**: Generates a professional-level tactical tip based on the provided context.

#### Singleton

- **`get_llm_service()`**: Simple singleton factory (not double-checked locking — the LLM service is not performance-critical to instantiate).

#### Diagnostic

- **`check_ollama_status() -> dict`**: Returns a dictionary with the Ollama connection status, available models, and configured model name.

---

### 1.7 Ollama Writer

**File:** `services/ollama_writer.py`

A specialized LLM wrapper that "polishes" raw coaching insights into more natural, engaging coaching messages.

#### Constants

- **`COACH_SYSTEM_PROMPT`**: A system prompt constant that instructs the LLM to act as a CS2 coach, polish the given insight into a more engaging and actionable message, and maintain the original meaning.

#### Class: `OllamaCoachWriter`

**Constructor**: Lazy-loads the `LLMService` and checks whether LLM polishing is enabled in user settings.

**Methods:**

- **`polish(title: str, message: str, focus_area: str, severity: str, map_name: str = None) -> str`**: Takes raw coaching insight components and returns a polished version. If the LLM is unavailable or disabled, returns the original message unchanged. The prompt includes the title, severity, focus area, and optional map context.

#### Singleton

- **`get_ollama_writer()`**: Simple singleton factory returning the single `OllamaCoachWriter` instance.

---

### 1.8 Player Lookup

**File:** `services/player_lookup.py`

Provides player name detection within chat messages and cross-database profile assembly.

#### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `_STOP_WORDS` | frozenset (~100 words) | Common English words excluded from player name matching |
| `_CHAT_FUZZY_THRESHOLD` | `0.75` | Minimum fuzzy match ratio for player name detection in chat |

#### Dataclass: `ProPlayerProfile`

Fields:
- `name: str` — Player's display name
- `team: str` — Current team
- `country: str` — Nationality
- `hltv_stats: dict` — Statistics from HLTV database
- `demo_stats: dict` — Statistics derived from analyzed demo files
- `is_default_stats: bool` — Flag indicating whether the stats are placeholder/default values (for CHAT-06 handling)

#### Sentinel

- **`_DEFAULT_STATS_SENTINEL`**: A tuple of values that represents placeholder stat cards. Used by `_stat_card_is_default()` to detect when a player's stats are actually default values rather than real data.

- **`_stat_card_is_default(card) -> bool`**: Checks whether a `ProPlayerStatCard` ORM object contains only default/placeholder values by comparing key fields against the sentinel.

#### Class: `PlayerLookupService`

**Class Constants:**
- `_CACHE_TTL = 60.0`: Cache time-to-live in seconds for the player name lookup cache.

**Methods:**

- **`_ensure_cache()`**: Loads player names from both the HLTV database (`ProPlayer` table) and the main database (`PlayerMatchStats` table) into an in-memory cache. Uses TTL-based invalidation.

- **`detect_player_mentions(message: str) -> List[str]`**: Three-pass player name detection:
  1. **Exact match**: Checks if any known player name appears as a complete word in the message
  2. **N-gram match**: Generates bigrams and trigrams from the message and checks against known names
  3. **Fuzzy match**: Uses `difflib.SequenceMatcher` with `_CHAT_FUZZY_THRESHOLD` against remaining unmatched words (after filtering stop words)
  Returns a deduplicated list of detected player names.

- **`lookup_player(name: str) -> ProPlayerProfile`**: Cross-database profile assembly:
  1. Searches HLTV database for player identity (name, team, country)
  2. Fetches HLTV stat cards for the player
  3. Searches main database for demo-derived performance stats
  4. Assembles a `ProPlayerProfile` with the `is_default_stats` flag set based on `_stat_card_is_default()`

- **`format_player_context(profile: ProPlayerProfile) -> str`**: Formats a `ProPlayerProfile` into a `VERIFIED PLAYER DATA` text block suitable for injection into LLM prompts. Implements CHAT-06: if `is_default_stats` is True, the context block explicitly states that statistics are placeholder values and should not be cited as factual.

---

### 1.9 Profile Service

**File:** `services/profile_service.py`

Integrates external player profiles from Steam and FACEIT APIs.

#### Class: `ProfileService`

**Methods:**

- **`fetch_steam_stats(steam_id: str) -> dict`**: Fetches CS2 statistics from the Steam Web API for the given Steam ID. Delegates to `_execute_steam_fetch()`.

- **`fetch_faceit_stats(nickname: str) -> dict`**: Fetches competitive statistics from the FACEIT API for the given nickname. Delegates to `_execute_faceit_fetch()`.

- **`sync_all_external_data(steam_id: str, faceit_name: str) -> dict`**: Orchestrates fetching from both Steam and FACEIT, then persists the combined data to the database.

**Internal Methods:**

- **`_execute_steam_fetch(steam_id) -> dict`**: Makes the HTTP request to the Steam API with 3 retries and exponential backoff. Returns raw API response.

- **`_parse_steam_response(response) -> dict`**: Parses the Steam API JSON response, extracting CS2-specific statistics from the nested structure.

- **`_fetch_cs2_hours(steam_id) -> float`**: Fetches the player's total CS2 playtime hours from Steam.

- **`_execute_faceit_fetch(nickname) -> dict`**: Makes the HTTP request to the FACEIT API with URL encoding for special characters. Returns raw API response.

- **`_persist_profile_update(steam_data, faceit_data)`**: Writes the combined external profile data to the database.

- **`_update_or_add_profile(session, steam_data, faceit_data)`**: Upserts the profile record — updates if exists, creates if not.

- **`_apply_profile_fields(profile_obj, steam_data, faceit_data)`**: Applies individual field values from API responses to the ORM profile object.

---

### 1.10 Telemetry Client

**File:** `services/telemetry_client.py`

A minimal HTTP client for sending match telemetry to a remote server.

#### Constants

- **`DEV_SERVER_URL`**: Read from environment variable `CS2_TELEMETRY_URL`, defaults to `"http://127.0.0.1:8000"`.
- **`_HAS_HTTPX`**: Boolean flag indicating whether the `httpx` library is installed. If not, telemetry is silently disabled with a warning.

#### Functions

- **`send_match_telemetry(player_id: str, match_id: str, stats: dict) -> bool`**: Sends a POST request to `{DEV_SERVER_URL}/api/ingest/telemetry` with a JSON payload containing `player_id`, `match_id`, `stats`, and a `timestamp`. Returns `True` on success (HTTP 200), `False` on failure or if httpx is unavailable. Uses a 10-second timeout.

**Design Note:** The `__main__` block explicitly refuses to use synthetic test data, citing the Anti-Fabrication Rule. It only logs readiness.

---

### 1.11 Visualization Service

**File:** `services/visualization_service.py`

Generates Matplotlib-based charts for player performance visualization.

#### Class: `VisualizationService`

**Methods:**

- **`generate_performance_radar(user_stats: dict, pro_stats: dict, output_path: str)`**: Creates a radar/spider chart comparing the user's stats against a professional player's stats. Saves the chart to `output_path` as a PNG file. Uses Matplotlib's polar projection.

- **`plot_comparison_v2(p1_name: str, p2_name: str, p1_stats: dict, p2_stats: dict) -> BytesIO`**: Generates a side-by-side comparison chart of two players. Returns the chart as a `BytesIO` buffer (in-memory image) rather than writing to disk. This is used for embedding in the Qt UI.

#### Singleton

- **`get_visualization_service()`**: Simple singleton factory.

#### Module-Level Wrapper

- **`generate_performance_radar(...)`**: A module-level convenience function that delegates to `get_visualization_service().generate_performance_radar(...)`.

---

## 2. Server

### 2.1 FastAPI Utility Server

**File:** `backend/server.py`

A standalone FastAPI server providing REST endpoints for telemetry ingestion, insight retrieval, system health, and remote service control. This server is NOT wired into the main application flow — it is a standalone utility.

#### Rate Limiter

- **`RateLimiter` class**: Implements a sliding-window rate limiter.
  - `max_requests = 10` per `window_seconds = 60` per IP address.
  - `_requests` dictionary maps IP addresses to lists of `float` timestamps.
  - **`is_allowed(ip: str) -> bool`**: Checks if the IP has exceeded the rate limit within the current window. Prunes expired timestamps from the window.

#### Lifespan

The FastAPI app uses an async lifespan handler that initializes the database on startup via `init_database()`.

#### Pydantic Models

- **`InsightRead`**: Response model for coaching insights with fields: `id`, `player_name`, `title`, `message`, `focus_area`, `severity`, `created_at`.
- **`MatchTelemetry`**: Request model for telemetry ingestion with fields: `player_id`, `match_id`, `stats` (dict), `timestamp` (float).

#### Endpoints

| Method | Path | Rate Limited | Description |
|--------|------|-------------|-------------|
| `POST` | `/api/ingest/telemetry` | Yes | Ingests match telemetry data. Queues background disk write via `_write_telemetry_to_disk()`. |
| `GET` | `/api/insights` | No | Returns coaching insights for a player (query param: `player_name`). |
| `GET` | `/api/status` | No | Returns application status with version, uptime, and database state. |
| `GET` | `/api/console/health` | No | Returns service health check for monitoring. |
| `POST` | `/api/training/start` | No | Starts ML training via the backend Console. |
| `POST` | `/api/training/stop` | No | Stops ML training. |
| `POST` | `/api/training/pause` | No | Pauses ML training. |
| `POST` | `/api/training/resume` | No | Resumes ML training. |
| `POST` | `/api/services/hunter/start` | No | Starts the HLTV Hunter service. |
| `POST` | `/api/services/hunter/stop` | No | Stops the HLTV Hunter service. |
| `GET` | `/api/services/status` | No | Returns status of all managed services. |

#### Background Task

- **`_write_telemetry_to_disk(data: dict)`**: Writes telemetry data to a JSON file on disk. Uses sanitized filenames derived from `player_id` and `match_id` to prevent path traversal.

---

## 3. Storage Layer

**Location:** `Programma_CS2_RENAN/backend/storage/`

The storage layer implements a three-tier database architecture with SQLite, WAL-mode concurrency, per-match partitioning, backup management, and state tracking.

### 3.1 Backup Manager

**File:** `storage/backup_manager.py`

Production-grade backup solution for the monolithic SQLite database.

#### Constants

- **`_SAFE_BACKUP_LABEL_RE`**: Compiled regex `^[a-zA-Z0-9_\-]{1,64}$` for validating backup labels. Prevents injection into file paths (BE-01, DB-03, AUDIT section 9).

#### Class: `BackupManager`

**Constructor**: Sets up the backup directory at `{USER_DATA_ROOT}/backups` and locates the monolith database at `{CORE_DB_DIR}/database.db`.

**Methods:**

- **`create_checkpoint(label: str = "auto") -> bool`**: Creates a hot backup. Steps:
  1. Validates label against `_SAFE_BACKUP_LABEL_RE` (pre-validation, not post-hoc)
  2. Constructs filename: `backup_{label}_{YYYYMMDD_HHMMSS}.db`
  3. Validates target path is inside backup directory using `Path.resolve().relative_to()` (BE-06 defence-in-depth)
  4. Uses SQLite Online Backup API (`sqlite3.Connection.backup()`) — NOT `VACUUM INTO` — for WAL-safe, injection-free backups
  5. Verifies output file exists
  6. Runs integrity check on the backup (not the main DB)
  7. Deletes backup if integrity check fails
  8. Prunes old backups per retention policy
  Returns `True` on success, `False` on any failure. Cleans up partial files.

- **`_verify_integrity(db_path: str) -> bool`**: Runs `PRAGMA quick_check` on the specified database file. Uses `quick_check` instead of full `integrity_check` to avoid blocking for minutes on large databases (DG-01). Returns `True` if result is "ok".

- **`verify_backup(backup_path: str) -> bool`**: Public method for verifying a backup before restore. Includes path traversal guard using `Path.resolve().relative_to()` to ensure the backup path does not escape the backup directory (DG-03, BE-06). Delegates to `_verify_integrity()`.

- **`_prune_backups()`**: Enforces the retention policy:
  - Always keeps the absolute latest backup (safety)
  - Keeps the last 7 daily backups (one per day, most recent for each day)
  - Keeps the last 4 weekly backups (one per ISO week, for approximately one month of coverage)
  - Deletes all backups not in the keep list

  Parses backup filenames to extract timestamps using the format `backup_LABEL_YYYYMMDD_HHMMSS.db`. Skips malformed filenames gracefully.

- **`should_run_auto_backup() -> bool`**: Checks whether any backup exists with today's date. Returns `True` if no backup for today exists (triggering auto-backup). Fails safe: returns `True` on any error.

---

### 3.2 Database Manager

**File:** `storage/database.py` (~507 lines)

The core database management layer. Manages two separate SQLite databases: the monolith (`database.db`) and the HLTV metadata database (`hltv_metadata.db`).

#### Constants

- **`_SAFE_COL_TYPE_RE`**: Compiled regex for validating column type strings in dynamic schema operations (DB-04). Only allows safe SQL type keywords.

#### Table Lists

- **`_MONOLITH_TABLES`**: List of 17 SQLModel table objects that define the monolith database schema. Includes: `PlayerMatchStats`, `PlayerTickState`, `Ext_PlayerProfile`, `Ext_PlayerPlaystyle`, `CoachingInsight`, `IngestionTask`, `TacticalKnowledge`, `CoachState`, `Notification`, `RoundStats`, `CalibrationSnapshot`, `RoleThresholds`, `DataLineage`, `DataQualityMetrics`, and others.

- **`_HLTV_TABLES`**: List of 3 SQLModel table objects for the HLTV database: `ProPlayer`, `ProPlayerStatCard`, `ProTeam`.

#### Class: `DatabaseManager`

**Engine Configuration:**
- `check_same_thread=False` (allows cross-thread access in WAL mode)
- `timeout=30` seconds
- `pool_size=1`, `max_overflow=4` (conservative pooling for SQLite)

**Connection Pragmas (set on every new connection):**
- `journal_mode=WAL` (Write-Ahead Logging for concurrent reads)
- `synchronous=NORMAL` (balance of safety and speed)
- `busy_timeout=30000` (30 second busy timeout)
- `foreign_keys=ON` (enforce referential integrity)
- `wal_autocheckpoint=512` (checkpoint every 512 pages)

**Methods:**

- **`create_db_and_tables()`**: Creates all tables defined in `_MONOLITH_TABLES` using `SQLModel.metadata.create_all()`. Then calls `_add_missing_columns()` for forward-compatible schema evolution (adds columns that exist in models but not in the database).

- **`_add_missing_columns(engine)`**: Introspects the database schema via `PRAGMA table_info` and compares against the SQLModel definitions. For each missing column, executes `ALTER TABLE ADD COLUMN` with appropriate defaults. Validates column types against `_SAFE_COL_TYPE_RE` (DB-04).

- **`get_session()`**: Context manager that yields a `Session` object. Handles:
  - Automatic `session.commit()` on successful exit
  - `session.rollback()` on exception
  - `session.expire_all()` on exit to prevent stale data
  - Proper session cleanup

- **`upsert(obj)`**: General-purpose upsert. For `PlayerMatchStats` objects, delegates to `_upsert_player_stats()` which uses SQLite `INSERT ... ON CONFLICT DO UPDATE` syntax for atomic upserts on the `(demo_name, player_name)` unique constraint.

- **`get(model_class, **filters)`**: Generic query method that fetches a single record matching the given filters.

- **`record_lineage(match_id, source, operation, metadata_dict)`**: Creates a `DataLineage` record for data provenance tracking.

- **`delete_match_cascade(demo_name)`**: Deletes all data associated with a match, cascading through `PlayerMatchStats`, `PlayerTickState`, `CoachingInsight`, and `IngestionTask` tables.

- **`detect_orphans()`**: Identifies orphaned records — rows that reference non-existent parent records. Returns a list of orphan descriptions.

#### Class: `HLTVDatabaseManager`

Same engine configuration and pragmas as `DatabaseManager` but operates on `hltv_metadata.db`.

**Additional Method:**

- **`_reconcile_stale_schema(engine)`**: Drops and recreates HLTV tables if the existing schema does not match the SQLModel definitions. This is aggressive but acceptable for HLTV data since it can always be re-scraped.

#### Singletons

- **`get_db_manager()`**: Thread-safe singleton factory with double-checked locking (`_db_lock`). Returns the single `DatabaseManager` instance.

- **`get_hltv_db_manager()`**: Thread-safe singleton factory with double-checked locking (`_hltv_lock`). Returns the single `HLTVDatabaseManager` instance.

#### Security

- **`_restrict_db_permissions(db_path)`**: Sets file permissions to `0o600` (owner read/write only) on non-Windows systems.

#### Initialization

- **`init_database()`**: Creates both database managers, calls `create_db_and_tables()` on each, and restricts file permissions.

---

### 3.3 DB Backup Utilities

**File:** `storage/db_backup.py`

Lower-level backup utilities separate from the `BackupManager`. Provides atomic backup operations and archive management.

#### Functions

- **`backup_monolith() -> bool`**: Creates a backup of the monolith database using the SQLite Online Backup API. Verifies integrity of the backup after creation.

- **`backup_match_data() -> bool`**: Creates a tar.gz archive of all per-match SQLite databases. Uses `sqlite3.backup()` for each individual match database file to ensure consistency (atomic copy of each database within the archive).

- **`rotate_backups(keep_count: int = 5)`**: Deletes the oldest backups beyond the `keep_count` retention threshold. Sorts by modification time.

- **`restore_backup(backup_path: str, target_path: str) -> bool`**: Restores a backup to the target location. Steps:
  1. Creates a rollback copy of the current database
  2. Copies the backup to the target
  3. Cleans up WAL and SHM files from the restored database
  4. Runs integrity check on the restored database
  5. On failure, restores from the rollback copy

---

### 3.4 DB Migrate

**File:** `storage/db_migrate.py`

Alembic migration utility for managing database schema changes.

#### Functions

- **`ensure_database_current() -> bool`**: Checks whether the database is at the latest Alembic revision. If not, runs `alembic upgrade head` to bring it current. Called during application boot.

- **`get_current_revision() -> str`**: Returns the current Alembic revision hash of the database.

- **`get_head_revision() -> str`**: Returns the latest (head) Alembic revision hash from the migration scripts.

---

### 3.5 DB Models

**File:** `storage/db_models.py` (~883 lines)

All ORM models for both the monolith and HLTV databases. Uses SQLModel (which combines SQLAlchemy and Pydantic).

#### Size Guard Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_GAME_STATE_JSON_BYTES` | `16384` | Maximum size for game state JSON fields |
| `MAX_AUX_JSON_BYTES` | `8192` | Maximum size for auxiliary JSON fields |
| `MAX_STAT_JSON_BYTES` | `32768` | Maximum size for statistics JSON fields (S-07) |

#### Enums

- **`DatasetSplit`**: `train`, `val`, `test`, `unassigned` — Categorizes data records for ML training/validation/testing splits.
- **`CoachStatus`**: `Paused`, `Training`, `Idle`, `Error`, `Booting`, `Running`, `ShuttingDown`, `Offline` — Tracks the application's coaching daemon state.

#### Table Classes (24 total)

**Match & Player:**
1. **`PlayerMatchStats`**: Core match statistics per player per demo. Fields include kills, deaths, assists, ADR, headshot percentage, HLTV rating, map name, demo name, player name, and more. Has `UniqueConstraint` on `(demo_name, player_name)`.
2. **`PlayerTickState`**: Per-tick player state data for the monolith database (legacy).
3. **`RoundStats`**: Per-round aggregated statistics.

**External Profiles:**
4. **`Ext_PlayerProfile`**: External player profile data (Steam, FACEIT).
5. **`Ext_PlayerPlaystyle`**: Player playstyle analysis including upload counts.

**Coaching:**
6. **`CoachingInsight`**: Generated coaching insights with title, message, focus area, severity, player name, and creation timestamp.
7. **`CoachingExperience`**: COPER experience bank entries.

**Ingestion:**
8. **`IngestionTask`**: Tracks demo ingestion status (queued, processing, completed, failed) with retry count and error messages.

**Knowledge:**
9. **`TacticalKnowledge`**: RAG knowledge base entries for tactical coaching information.

**System State:**
10. **`CoachState`**: Singleton record tracking the application's overall state, daemon statuses, confidence scores, and heartbeat timestamps.
11. **`Notification`**: Application notifications with type, message, and timestamp.

**HLTV Pro Data:**
12. **`ProPlayer`**: Professional player identity (name, team, country, HLTV ID).
13. **`ProPlayerStatCard`**: Professional player statistics (rating, KD, ADR, KAST, headshot percentage, etc.) with temporal data (last_updated).
14. **`ProTeam`**: Professional team data.
15. **`ProEvent`**: HLTV tournament/event data.
16. **`ProTournament`**: Tournament metadata.
17. **`ProHeadToHead`**: Head-to-head player comparison records.
18. **`ProMapRecord`**: Per-map performance records for pro players.
19. **`MatchResult`**: Professional match results.
20. **`MapVeto`**: Map veto data from professional matches.

**ML/Calibration:**
21. **`CalibrationSnapshot`**: Point-in-time calibration data for ML models.
22. **`RoleThresholds`**: Thresholds for role classification.

**Data Governance:**
23. **`DataLineage`**: Data provenance tracking (source, operation, timestamp, metadata).
24. **`DataQualityMetrics`**: Quality metrics for ingested data (NaN rates, range violations, etc.).

#### Pydantic Validators

Several models include Pydantic validators (using SQLModel's `@validator` decorator):
- JSON size limit validators that check field lengths against `MAX_GAME_STATE_JSON_BYTES`, `MAX_AUX_JSON_BYTES`, and `MAX_STAT_JSON_BYTES`
- Data quality coercion validators that clamp numeric fields to valid ranges
- CHECK constraints defined in table metadata for database-level enforcement

#### Indexes and Constraints

- Composite indexes on frequently queried column combinations
- Foreign keys with `ON DELETE CASCADE` for child records and `ON DELETE SET NULL` for optional references
- Unique constraints for deduplication (e.g., `(demo_name, player_name)` on `PlayerMatchStats`)

---

### 3.6 Maintenance

**File:** `storage/maintenance.py`

Simple metadata pruning utility.

#### Functions

- **`prune_old_metadata(days_threshold: int = 30)`**: Deletes `PlayerTickState` records for demos older than `days_threshold` days. Processes deletions in 500-row chunks to avoid locking the database for extended periods.

---

### 3.7 Match Data Manager

**File:** `storage/match_data_manager.py` (~1053 lines)

Manages per-match SQLite partitions (Tier 3 storage). Each match gets its own SQLite database file, providing isolation and enabling independent lifecycle management.

#### Safety Functions

- **`_assert_safe_identifier(name: str)`**: Validates that a string is a safe SQL identifier (alphanumeric + underscores only). Raises `ValueError` on unsafe input.

- **`_assert_safe_col_type(col_type: str)`**: Validates column types against a safe list. Raises `ValueError` on unsafe input.

- **`_assert_safe_default_literal(value)`**: Validates default values for columns. Only allows None, integers, floats, and safe string literals.

#### Deterministic Match ID

- **`demo_name_to_match_id(demo_name: str) -> str`**: Derives a deterministic match ID from the demo filename using SHA-256 hashing. This ensures the same demo always maps to the same match database file.

#### Schema Versioning

- **`MATCH_DB_SCHEMA_VERSION = 3`**: Current schema version for per-match databases.

- **`_MATCH_DB_MIGRATIONS`**: Dictionary mapping source version to migration function:
  - `1 -> 2`: Adds new columns introduced in version 2
  - `2 -> 3`: Adds new columns introduced in version 3
  Migrations are applied incrementally (v1 -> v2 -> v3).

#### Models (Per-Match)

- **`MatchTickState`**: Per-tick player state within a match. Bound to legacy table name `matchtickstate`. Contains approximately 50 fields per tick including position (x, y, z), velocity, health, armor, weapon, team, alive status, and various game state flags.

- **`MatchEventState`**: Game events within a match. Tracks actor, victim, event type, tick number, round number, and entity tracking data.

- **`MatchMetadata`**: Match-level metadata including map name, team names, demo file info, processing timestamps, and schema version.

#### Class: `MatchDataManager`

**Engine Cache:**
- Uses an LRU cache with `_MAX_CACHED_ENGINES = 50` engines.
- Implemented via `collections.OrderedDict` for LRU eviction.
- When cache exceeds maximum, the least-recently-used engine is disposed.

**Storage Verification:**
- **WR-14**: Compares the device ID of the match data directory against expectations to detect when match files have been moved to a different storage device.

**Schema Migration:**
- **`_ensure_match_schema(engine, match_id)`**: Checks the `match_metadata` table for the current schema version and applies incremental migrations from `_MATCH_DB_MIGRATIONS` until the schema is current.

**Methods:**

- **`store_tick_batch(match_id, ticks: List[MatchTickState])`**: Bulk-inserts tick data for a match. Opens or reuses the cached engine for the match.

- **`store_metadata(match_id, metadata: MatchMetadata)`**: Stores or updates match metadata.

- **`get_ticks_for_round(match_id, round_number) -> List[MatchTickState]`**: Queries tick data filtered by round number.

- **`get_player_ticks(match_id, player_name) -> List[MatchTickState]`**: Queries all ticks for a specific player across all rounds.

- **`get_metadata(match_id) -> MatchMetadata`**: Retrieves match metadata.

- **`store_event_batch(match_id, events: List[MatchEventState])`**: Bulk-inserts game events.

- **`get_events_for_tick_range(match_id, start_tick, end_tick) -> List[MatchEventState]`**: Queries events within a tick range.

- **`get_active_utilities(match_id, tick) -> List[MatchEventState]`**: Queries active utility grenades at a specific tick.

- **`get_all_players_at_tick(match_id, tick) -> List[MatchTickState]`**: Gets the state of all players at a specific tick.

- **`get_player_tick_window(match_id, player_name, start_tick, end_tick) -> List[MatchTickState]`**: Queries a player's ticks within a tick range.

- **`get_all_players_tick_window(match_id, start_tick, end_tick) -> List[MatchTickState]`**: Queries all players' ticks within a tick range.

- **`list_available_matches() -> List[dict]`**: Scans the match data directory and returns metadata for all available match databases.

- **`delete_match(match_id)`**: Deletes a match database file and removes it from the engine cache.

- **`get_match_size_bytes(match_id) -> int`**: Returns the file size of a match database.

- **`get_total_storage_bytes() -> int`**: Returns the total size of all match databases combined.

- **`close_all()`**: Disposes all cached engines and clears the cache. Used during shutdown.

#### Singleton and Utilities

- **`get_match_data_manager()`**: Thread-safe singleton factory. On first call, also performs a one-time migration of match data from any old storage location.

- **`reset_match_data_manager()`**: Resets the singleton (for testing purposes).

- **`migrate_match_data(old_dir, new_dir)`**: Moves match database files from an old location to the current location.

---

### 3.8 Remote File Server

**File:** `storage/remote_file_server.py`

A personal cloud storage server built on FastAPI for remote access to application data.

#### Rate Limiting

- **`_RateLimiter` class**: Sliding window rate limiter, 10 requests per minute per IP.

- **`RateLimitMiddleware`**: ASGI middleware that applies rate limiting to all incoming requests. Returns HTTP 429 when limit is exceeded.

#### Security

- API key authentication using HMAC-safe comparison (`hmac.compare_digest`) to prevent timing attacks.
- Path traversal protection on all file access endpoints.
- **BE-07**: Refuses to serve on non-localhost addresses without TLS. If TLS certificate and key paths are provided, serves over HTTPS.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/list` | Lists available files (with API key auth) |
| `GET` | `/download/{filename}` | Downloads a specific file (with API key auth and path traversal protection) |
| `GET` | `/health` | Health check (no auth required) |

#### Server Runner

- **`run_server(host, port, cert_file, key_file)`**: Starts the FastAPI server via uvicorn. If `cert_file` and `key_file` are provided, runs with TLS. Otherwise, only binds to localhost (BE-07).

---

### 3.9 Stat Aggregator

**File:** `storage/stat_aggregator.py`

Persists HLTV-scraped data to the HLTV database.

#### Class: `StatCardAggregator`

**Methods:**

- **`persist_player_card(spider_data: dict)`**: Persists a player stat card from spider-scraped data. Performs:
  - KAST normalization (converts percentage string to decimal)
  - Headshot percentage normalization (converts percentage string to decimal)
  - JSON size guard (S-07): truncates serialized data that exceeds `MAX_STAT_JSON_BYTES`
  - Upserts into the `ProPlayerStatCard` table

- **`persist_team(team_data: dict)`**: Persists team data from spider-scraped data into the `ProTeam` table.

---

### 3.10 State Manager

**File:** `storage/state_manager.py`

Application state DAO (Data Access Object) that provides a clean interface for reading and updating the application's runtime state.

#### Enum: `DaemonName`

Values: `HUNTER`, `DIGESTER`, `TEACHER`, `GLOBAL` — identifies the four major system daemons/processes.

#### Class: `StateManager`

**Class Constants:**
- `_TELEMETRY_ESCALATION_THRESHOLD = 5`: Number of consecutive failures before escalating to error state.
- `_MAX_NOTIFICATIONS = 500`: Maximum stored notifications before auto-pruning.

**Methods:**

- **`get_state() -> CoachState`**: Retrieves the current `CoachState` singleton record. Creates it if it does not exist. Uses `session.expunge()` before returning to detach the object from the session (SM-01 requirement — prevents accidental modification of the persistent state).

- **`update_status(daemon: DaemonName, status: CoachStatus, detail: str = None)`**: Updates the status of a specific daemon. Validates transitions for the `GLOBAL` daemon (prevents invalid state transitions).

- **`update_belief_confidence(confidence: float)`**: Updates the belief confidence score (0.0 to 1.0) in the state.

- **`update_parsing_progress(progress: float, current_file: str = None)`**: Updates the parsing progress (0.0 to 100.0) and optionally the currently-processing filename.

- **`update_training_progress(epoch: int, total_epochs: int, loss: float)`**: Updates ML training progress metrics. If `loss` remains stagnant for `_TELEMETRY_ESCALATION_THRESHOLD` updates, escalates to warning state.

- **`heartbeat(daemon: DaemonName)`**: Updates the heartbeat timestamp for a daemon.

- **`set_error(daemon: DaemonName, error_msg: str)`**: Sets a daemon to error state with an error message.

- **`add_notification(notification_type: str, message: str)`**: Adds a notification to the database. Auto-prunes when count exceeds `_MAX_NOTIFICATIONS`.

- **`prune_old_notifications(max_age_days: int = 30)`**: Deletes notifications older than `max_age_days`.

- **`get_status(daemon: DaemonName) -> dict`**: Returns the current status dictionary for a specific daemon, including status, detail, last heartbeat, and error information.

#### Singleton

- **`get_state_manager()`**: Thread-safe singleton factory with double-checked locking.

---

### 3.11 Storage Manager

**File:** `storage/storage_manager.py`

Manages local demo file storage — ingest directories, archival, quota enforcement, and deduplication.

#### Class: `StorageManager`

**Constructor**: Configures storage paths:
- `local_path`: From user setting `DEFAULT_DEMO_PATH` (fallback: user home directory)
- `quota_gb`: From user setting `LOCAL_QUOTA_GB` (default: 10.0 GB)
- `brain_dir`: From user setting `BRAIN_DATA_ROOT` (fallback: `{PROJECT_ROOT}/data`)
- `archive_dir`: `{brain_dir}/datasets/user_archive`
- `pro_archive_dir`: `{brain_dir}/datasets/pro_archive`
- `ingest_dir`: Same as `local_path`
- `pro_ingest_dir`: From user setting `PRO_DEMO_PATH` (fallback: `{local_path}/pro_ingest`)

Falls back to the user's home directory if the configured path does not exist.

**Methods:**

- **`enforce_quota()`**: Checks current directory size against `quota_gb`. If over quota, calls `_archive_old_files()` with a target reduction of (current_usage - quota + 1.0 GB buffer).

- **`get_demo_path(filename: str) -> Optional[str]`**: Resolves a demo filename to an absolute path. **P2-03**: Strips directory components from the filename (`Path(filename).name`) to block path traversal attacks (e.g., `../../etc/passwd`). Searches `local_path`, `ingest_dir`, `pro_ingest_dir`, and `archive_path` in order.

- **`list_new_demos(is_pro: bool = False) -> List[Path]`**: Scans the appropriate ingest directory recursively (`.rglob("*.dem")`, excluding symlinks) and filters out demos already recorded in the database. Deduplication checks:
  1. Demo path against `IngestionTask.demo_path`
  2. Demo stem (filename without extension) against `PlayerMatchStats.demo_name`
  Uses a query limit of `_QUERY_LIMIT = 10,000` with warning if hit. **STOR-07**: Explicit `.dem` suffix removal for reliable matching.

- **`archive_demo(demo_path, is_pro=False)`**: Moves a processed demo to the `ingested/` subdirectory within its ingest folder.

- **`can_user_upload(is_pro: bool = False) -> bool`**: Checks upload quotas. Pro uploads are always allowed. For user uploads, checks `Ext_PlayerPlaystyle.monthly_upload_count` against `MAX_DEMOS_PER_MONTH` and `total_upload_count` against `MAX_TOTAL_DEMOS_PER_USER`.

**Private Methods:**

- **`_ensure_dirs()`**: Creates all managed directories. Skips `pro_ingest_dir` (user-managed, may have restricted permissions). Handles `OSError` for unavailable drives (Windows-specific).

- **`_archive_old_files(target_reduction_gb)`**: Moves the oldest `.dem` files to the archive until the freed bytes meet the target reduction. Excludes `pro_ingest_dir` from archival (M-27). Sorts by modification time.

- **`_get_dir_size_gb(path) -> float`**: Recursively calculates directory size in gigabytes. Handles deleted-during-walk and permission-denied errors gracefully.

- **`get_ingest_dir(is_pro) -> Path`**: Returns the appropriate ingest directory based on the `is_pro` flag.

---

## 4. Control Layer

**Location:** `Programma_CS2_RENAN/backend/control/`

The control layer orchestrates system-level operations: boot/shutdown sequences, service supervision, database governance, ingestion management, and ML training lifecycle.

### 4.1 Console (Backend)

**File:** `control/console.py` (~740 lines)

The backend system console that manages the application's lifecycle and provides a unified interface for all major subsystems.

#### Enums

- **`SystemState`**: `IDLE`, `BOOTING`, `BUSY`, `SHUTTING_DOWN`, `MAINTENANCE`, `ERROR` — Represents the overall system state.

- **`ServiceStatus`**: `STOPPED`, `RUNNING`, `CRASHED`, `STARTING` — Represents individual service states.

#### Class: `ServiceSupervisor`

Manages subprocess daemons with automatic restart on crash.

**Class Constants:**
- `_MAX_RETRIES = 3`: Maximum automatic restart attempts before marking as crashed
- `_RETRY_RESET_WINDOW_S = 3600`: Window (in seconds) after which the retry counter resets
- `_RESTART_DELAY_S = 5`: Delay between restart attempts
- `_MONITOR_TIMEOUT_S = 3600`: Maximum monitoring time for a single service instance

**Methods:**

- **`start_service(name: str)`**: Starts a named service as a subprocess. Launches a monitoring thread via `_monitor_process()`.

- **`stop_service(name: str)`**: Stops a named service. Cancels any pending restart timers. Sends SIGTERM and waits for graceful shutdown.

- **`_monitor_process(name)`**: Background thread that polls the subprocess. On unexpected exit (non-zero return code), triggers auto-restart with the retry mechanism. Resets the retry counter if the process has been running for longer than `_RETRY_RESET_WINDOW_S`.

- **`get_status() -> Dict[str, dict]`**: Returns a dictionary of all managed services with their current status, PID, and last restart time.

#### Class: `Console` (Singleton via `__new__`)

Uses Python's `__new__` method for singleton enforcement.

**Class Constants:**
- `_BASELINE_CACHE_TTL_S = 60`: Cache TTL for baseline status queries
- `_TRAINING_DATA_CACHE_TTL_S = 120`: Cache TTL for training data progress queries

**Initialization (`_do_init()`):** Creates instances of:
- `ServiceSupervisor` for managing the Hunter subprocess
- `IngestionManager` for controlling demo ingestion
- `DatabaseGovernor` for database integrity management
- `MLController` for ML training lifecycle

**Methods:**

- **`boot()`**: System boot sequence:
  1. Starts the HLTV Hunter service (if HLTV sync is enabled in config AND Docker is available)
  2. Initializes databases via `init_database()`
  3. Runs database integrity audit via `_audit_databases()`
  4. Applies log retention policies
  5. Calculates belief confidence score

- **`shutdown()`**: Ordered shutdown sequence:
  1. Stops ML training (if running)
  2. Stops ingestion (if running)
  3. Stops Hunter service
  4. Stops FlareSolverr container (if running)
  5. Waits up to 5 seconds for drain

- **`_audit_databases()`**: Runs database integrity checks and reports anomalies.

- **`get_system_status() -> dict`**: Returns comprehensive system status including:
  - System state (computed live, never cached)
  - Service statuses
  - Ingestion status
  - ML controller status
  - Storage metrics
  - Baseline status (cached 60s)
  - Training data progress (cached 120s)

- **`_compute_state() -> SystemState`**: Computes the current system state from service statuses and daemon states. Never caches — always computed fresh.

- **`_get_baseline_status() -> dict`**: Returns baseline statistics with 60-second caching.

- **`_get_training_data_progress() -> dict`**: Returns training data pipeline progress with 120-second caching.

**ML Wrappers:**
- **`start_training()`**: Delegates to `MLController.start_training()`
- **`stop_training()`**: Delegates to `MLController.stop_training()`
- **`pause_training()`**: Delegates to `MLController.pause_training()`
- **`resume_training()`**: Delegates to `MLController.resume_training()`

#### Singleton

- **`get_console()`**: Returns the `Console` singleton instance.

---

### 4.2 Database Governor

**File:** `control/db_governor.py`

Controls database-level operations: integrity verification, storage auditing, index rebuilding, and data pruning.

#### Class: `DatabaseGovernor`

**Methods:**

- **`audit_storage() -> dict`**: Comprehensive storage audit covering:
  - **Tier 1/2 (monolith)**: File existence, size, `PRAGMA quick_check`
  - **HLTV database**: File existence, integrity, auto-restore from backup if corrupt
  - **Tier 3 (match files)**: Lists all match databases, checks sizes, reports anomalies

- **`_run_pragma_quick_check(db_path) -> str`**: Internal blocking call that runs `PRAGMA quick_check` on a database file and returns the result.

- **`verify_integrity(full: bool = False) -> bool`**: Two modes:
  - `full=False` (default): Lightweight — runs `SELECT 1` to verify the database is accessible
  - `full=True`: Runs `PRAGMA quick_check` asynchronously via `verify_integrity_async()`

- **`verify_integrity_async(timeout_seconds: int = 120) -> bool`**: Runs integrity verification in a background thread with a timeout. Returns `True` if the check passes within the timeout.

- **`prune_match_data(match_id: int) -> bool`**: Deletes a specific match database from Tier 3 storage.

- **`rebuild_indexes()`**: Runs `REINDEX` on the monolith database to rebuild all indexes. Useful after large batch operations.

---

### 4.3 Ingestion Manager

**File:** `control/ingest_manager.py`

Controls the demo ingestion pipeline with multiple operational modes.

#### Enum: `IngestMode`

- `SINGLE`: Processes once and stops
- `CONTINUOUS`: Runs indefinitely, re-scanning at regular intervals
- `TIMED`: Runs on a fixed schedule (every N minutes)

#### Class: `IngestionManager`

**Class Constants:**
- `_MAX_BATCH_SIZE = 10`: Maximum demos to process per batch cycle

**Methods:**

- **`set_mode(mode: IngestMode, interval_minutes: int = 30)`**: Sets the operational mode and scan interval.

- **`scan_all(high_priority: bool = False)`**: Starts the ingestion cycle in a background thread. If `high_priority=True`, assigns resource priority to the ingestion thread.

- **`stop()`**: Signals the ingestion thread to stop using a `threading.Event`. Does not block — the thread checks the event between batches.

- **`get_status() -> dict`**: Returns current ingestion status combining:
  - Database counts (queued, processing, completed, failed tasks)
  - StateManager progress information
  - Current mode, interval, and phase information

- **`_run_unified_cycle()`**: Main ingestion loop:
  1. **Discovery**: Calls `StorageManager.list_new_demos()` for both user and pro demos
  2. **Queue**: Creates `IngestionTask` records for new demos
  3. **Processing**: Calls `_process_unified_queue()` to process queued tasks
  4. **Mode logic**: In `SINGLE` mode, exits after one cycle. In `TIMED` mode, sleeps for the configured interval. In `CONTINUOUS` mode, loops indefinitely with a short sleep.

- **`_recover_stuck_tasks()`**: Identifies tasks stuck in `processing` status for more than 5 minutes and resets them to `queued` status, up to a maximum of 3 retries per task.

- **`_process_unified_queue()`**: FIFO queue processor:
  1. Fetches queued tasks ordered by priority (pro demos first) then creation time
  2. Processes up to `_MAX_BATCH_SIZE` tasks per cycle
  3. Updates task status through `queued -> processing -> completed/failed`
  4. Records data lineage for successfully processed demos

---

### 4.4 ML Controller

**File:** `control/ml_controller.py`

Controls the ML training lifecycle with support for pause, resume, stop, and throttling.

#### Module-Level

- **`_TRAINING_LOCK`**: `threading.Lock` — Module-level lock for training coordination within the current process.

- **`training_file_lock()`**: Context manager for cross-process training coordination. Uses `fcntl.flock()` on Unix and `msvcrt.locking()` on Windows to create a file-based lock. This prevents multiple processes from training simultaneously.

#### Exception

- **`TrainingStopRequested`**: Custom exception raised when training is stopped externally. The training loop catches this to perform graceful cleanup.

#### Class: `MLControlContext`

Provides the control surface for training operations.

**Attributes:**
- `_stop_event`: `threading.Event` — Signals training to stop
- `_pause_event`: `threading.Event` — Signals training to pause
- `_resume_event`: `threading.Event` — Signals training to resume from pause
- `throttle_factor`: `float` — Value between 0.0 (no throttling) and 1.0 (maximum throttling). Introduces artificial delays between training steps.

**Methods:**
- `request_stop()`, `request_pause()`, `request_resume()`
- `set_throttle(factor: float)`
- `should_stop() -> bool`, `should_pause() -> bool`
- `wait_for_resume(timeout=None) -> bool`

#### Class: `MLController`

**Methods:**

- **`start_training()`**: Starts ML training in a background thread. Uses double locking:
  1. Module-level `_TRAINING_LOCK` for thread coordination
  2. `StateManager` status check to prevent concurrent training
  Delegates to `_run_wrapper()`.

- **`stop_training()`**: Requests training stop via `MLControlContext.request_stop()`.

- **`pause_training()`**: Requests training pause via `MLControlContext.request_pause()`.

- **`resume_training()`**: Requests training resume via `MLControlContext.request_resume()`.

- **`_run_wrapper()`**: Training execution wrapper:
  1. Updates StateManager to `Training` status
  2. Acquires the cross-process file lock
  3. Delegates to `CoachTrainingManager.run_full_cycle()`
  4. Handles `TrainingStopRequested` exception
  5. Updates StateManager on completion/failure

- **`get_status() -> dict`**: Returns `{"is_running": bool, "paused": bool, "stop_requested": bool}`.

---

## 5. Onboarding

**Location:** `Programma_CS2_RENAN/backend/onboarding/`

### 5.1 New User Flow

**File:** `backend/onboarding/new_user_flow.py`

Manages the new user experience through a staged onboarding process.

#### Class: `OnboardingStage` (Constants)

| Constant | Value | Meaning |
|----------|-------|---------|
| `AWAITING_FIRST_DEMO` | `"awaiting_first_demo"` | User has uploaded no demos |
| `BUILDING_BASELINE` | `"building_baseline"` | User has uploaded demos but fewer than recommended |
| `COACH_READY` | `"coach_ready"` | User has enough demos for full coaching |

#### Dataclass: `OnboardingStatus`

Fields:
- `stage: str` — Current onboarding stage
- `demos_uploaded: int` — Number of demos the user has uploaded
- `demos_required: int` — Minimum demos needed (1)
- `demos_recommended: int` — Recommended demos for stable baseline (3)
- `coach_ready: bool` — Whether the coach can function
- `baseline_stable: bool` — Whether the statistical baseline is reliable
- `message: str` — Human-readable status message

#### Class: `UserOnboardingManager`

**Class Constants:**
- `MIN_INITIAL_DEMOS = 1`: Minimum demos required to start coaching
- `RECOMMENDED_DEMOS = 3`: Demos recommended for a stable baseline
- `_CACHE_TTL_SECONDS = 60`: Cache TTL for demo count queries (TASK 2.16.1)

**Constructor**: Initializes the database manager and an in-memory demo count cache (`Dict[str, Tuple[int, float]]` mapping user_id to (count, timestamp)).

**Methods:**

- **`get_status(user_id: str = "default_user") -> OnboardingStatus`**: Returns the current onboarding status. Counts demos, determines stage, generates the appropriate message.

- **`_count_user_demos(user_id: str) -> int`**: Counts processed (non-pro) demos for the user. Uses TTL-based caching (TASK 2.16.1) to avoid repeated database queries during rapid UI refreshes. Filter: `player_name == user_id AND is_pro == False`.

- **`invalidate_cache(user_id: str = None)`**: Invalidates the demo count cache. If `user_id` is provided, clears only that user's cache entry. If `None`, clears the entire cache. Should be called after a new demo is uploaded.

- **`_determine_stage(count: int) -> str`**: Maps demo count to onboarding stage:
  - 0 demos: `AWAITING_FIRST_DEMO`
  - 1-2 demos: `BUILDING_BASELINE`
  - 3+ demos: `COACH_READY`

- **`_get_stage_message(stage: str, count: int) -> str`**: Returns a human-readable message for each stage.

#### Singleton

- **`get_onboarding_manager()`**: Simple singleton factory (not thread-safe with double-checked locking — acceptable for this low-contention use case).

---

## 6. Top-Level Scripts

### 6.1 console.py — Unified Console v3.0

**File:** `console.py` (project root, ~1674 lines)

The single entry point for the Macena CS2 Analyzer. Provides both an interactive TUI (Text User Interface) with a live dashboard and a non-interactive CLI mode.

#### Guards and Setup

- **Venv Guard**: Checks `sys.prefix == sys.base_prefix` and exits with an error if not in a virtual environment (bypassed by `CI=1` environment variable).
- **Path Stabilization**: Adds `PROJECT_ROOT` to `sys.path` (F7-12: acceptable for root-level CLI entry points).
- **Windows Encoding Fix**: Reconfigures stdout/stderr to UTF-8 on Windows.
- **Rich imports**: Requires the `rich` library. Exits with a clear error message if not installed.

#### Theme

- **`THEME`**: Rich `Theme` with semantic styles: `info` (cyan), `warning` (bold yellow), `error` (bold red), `success` (bold green), `brain` (bold magenta), `digester` (bold cyan), `archive` (bold yellow), `path` (underline blue), `dim` (dim white).

#### Console Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `TUI_REFRESH_PER_SECOND` | `8` | Target refresh rate for the TUI dashboard |
| `TUI_INPUT_POLL_INTERVAL_S` | `0.10` | Input polling interval in seconds |
| `OUTPUT_TRIM_MAX_LINES` | `80` | Maximum output lines displayed from subprocess |
| `SUBPROCESS_DEFAULT_TIMEOUT_S` | `120` | Default subprocess timeout |
| `SUBPROCESS_BUILD_TIMEOUT_S` | `600` | Build pipeline subprocess timeout |
| `DEAD_CODE_DETECTOR_TIMEOUT_S` | `220` | Dead code detector timeout |

#### Backend Lazy Loader

- **`_get_sys_console()`**: Lazily imports and returns the backend `Console` singleton from `control/console.py`. Avoids import-time side effects.

#### Subprocess Runners

- **`_run_tool(cmd, timeout=120) -> Tuple[int, str]`**: Runs a subprocess synchronously and returns `(exit_code, output_snippet)`. Trims output to `OUTPUT_TRIM_MAX_LINES` lines. Sets `PYTHONPATH` to include the project root.

- **`_run_tool_live(cmd, timeout=600) -> str`**: Runs a subprocess with live output streaming directly to the Rich console. Returns a PASS/FAIL string.

#### Command Registry System

- **`Command` class**: Slots-based class holding `handler` (Callable), `help_text` (str), and `category` (str).

- **`CommandRegistry` class**: Manages command registration and dispatch.
  - **`register(category, name, handler, help_text)`**: Registers a command under a category.
  - **`dispatch(category, subcmd, args) -> str`**: Dispatches to the registered handler. Includes P7-02 security: sanitizes error messages to prevent API key leakage in logs.
  - **`dispatch_interactive(cmd_line) -> str`**: Parses a raw command line string and dispatches. Handles single-word commands and subcmd routing.
  - **`get_help(category=None) -> str`**: Generates help text for a specific category or all categories.

#### Command Handlers (50+ handlers organized by category)

**ML Commands** (`ml`):
- `ml start` — Starts ML training
- `ml stop` — Graceful stop at next checkpoint
- `ml pause` — Pause training (resumable)
- `ml resume` — Resume from pause
- `ml throttle <0-1>` — Set training delay factor
- `ml status` — Detailed ML pipeline status

**Ingest Commands** (`ingest`):
- `ingest start [--priority]` — Start ingestion scan
- `ingest stop` — Stop ingestion
- `ingest mode <single|continuous|timed> [interval]` — Set operational mode
- `ingest status` — Show queue and processing status
- `ingest scan` — Dry-run scan for new demos

**Build Commands** (`build`):
- `build run [--test-only]` — Full build pipeline
- `build verify` — Post-build integrity verification
- `build manifest` — Generate integrity manifest

**Test Commands** (`test`):
- `test all` — Run full pytest suite
- `test headless` — Run headless validator
- `test backend` — Run backend validator
- `test ui` — Run UI diagnostic
- `test hospital [dept]` — Run Goliath Hospital diagnostic
- `test suite` — Run ALL validators sequentially (headless, pytest, backend, hospital)

**System Commands** (`sys`):
- `sys status` — Full system status dump
- `sys audit [--demo PATH]` — Feature audit
- `sys baseline` — Temporal baseline comparison (shows Legacy vs Temporal metrics with deltas)
- `sys db [-y]` — Database migration via Alembic
- `sys vacuum` — SQLite VACUUM on monolith
- `sys resources` — CPU/RAM/disk usage (via psutil)

**Settings Commands** (`set`):
- `set steam` — Set Steam API key (via `getpass` secure prompt, P7-01)
- `set faceit` — Set FACEIT API key (via `getpass` secure prompt)
- `set config <key> <value>` — Set a configuration key from `_ALLOWED_CONFIG_KEYS`
- `set view` — Show all settings (API keys masked to last 4 chars, F7-30)
- `set demo-path <path>` — Set user demo folder path
- `set pro-path <path>` — Set pro demo folder path

**`_ALLOWED_CONFIG_KEYS`** (16 keys): `PLAYER_NAME`, `STEAM_ID`, `STEAM_API_KEY`, `FACEIT_API_KEY`, `DEFAULT_DEMO_PATH`, `PRO_DEMO_PATH`, `ACTIVE_THEME`, `FONT_SIZE`, `FONT_TYPE`, `LANGUAGE`, `BACKGROUND_IMAGE`, `ENABLE_SLIDESHOW`, `BRAIN_DATA_ROOT`, `SETUP_COMPLETED`, `COACH_WEIGHT_OVERRIDES`, `CS2_PLAYER_NAME`.

**Service Commands** (`svc`):
- `svc restart <name>` — Restart a supervised service
- `svc kill-all` — Terminate all managed services
- `svc spawn <script>` — Spawn a tool as background process (with log capture)
- `svc status` — Show service supervisor status

**Maintenance Commands** (`maint`):
- `maint clear-cache` — Delete `__pycache__` and `.pytest_cache` directories (with PROJECT_ROOT safety check)
- `maint clear-queue` — Purge queued ingestion tasks
- `maint sanitize [-y]` — Run project sanitizer
- `maint dead-code` — Run dead code detector
- `maint prune <match_id>` — Delete a match database

**Tool Commands** (`tool`):
- `tool demo [events|fields|track|all]` — Demo inspector
- `tool user` — Show user profile info (read-only)
- `tool logs` — View recent log files (last 20 lines of latest JSON log)
- `tool list` — List all registered tools

**Meta Commands:**
- `help [category]` — Show command reference
- `exit` — Graceful shutdown (returns `__EXIT__` sentinel)

#### TUI Renderer

- **`TUIRenderer` class**: Generates the Rich Layout for the persistent TUI dashboard.

  **Layout Structure:**
  ```
  ┌─────────────────────────────────────────────┐
  │                   HEADER                     │ (4 rows)
  ├──────────────────────┬──────────────────────┤
  │     INGESTION        │     ML / BRAIN       │
  ├──────────────────────┤──────────────────────┤
  │     STORAGE          │     SYSTEM           │
  ├──────────────────────┴──────────────────────┤
  │                   FOOTER                     │ (16 rows)
  │   Last command result                        │
  │   MACENA> command input                      │
  │   Command reference                          │
  └─────────────────────────────────────────────┘
  ```

  **Dirty Flag Pattern:** Uses `_dirty` flag to avoid unnecessary re-renders. Only refreshes when state changes or user types.

  **Panels:**
  - `_header()`: Shows HLTV status, ingestion status, ML status with color coding
  - `_ingest_panel()`: Mode, phase, found demos, queue counts, progress bar, interval
  - `_ml_panel()`: State, teacher status, detail, stop requested flag
  - `_storage_panel()`: Monolith size, match count/size, anomaly count
  - `_system_panel()`: CPU usage, RAM usage (with 1-second psutil cache), baseline mode
  - `_footer()`: Last result, command input with blinking cursor, full command reference

#### Status Poller

- **`StatusPoller` class**: Background thread that caches system status at a fixed 2-second interval. The TUI render loop reads the cached dict (fast, non-blocking) instead of calling `get_system_status()` synchronously every frame.

  **Methods:**
  - `start()`: Starts the polling thread
  - `stop()`: Signals the thread to stop and joins
  - `get() -> dict`: Returns a copy of the cached status dict (thread-safe via lock)
  - `_poll()`: Polling loop that calls `get_system_status()` every `_STATUS_POLL_INTERVAL_S` (2 seconds)

#### TUI Input Handling

- **`_poll_tui_input(cmd_buffer, renderer, live) -> Tuple[str, bool]`**: Platform-aware input polling. Uses `msvcrt.kbhit()` on Windows and `select.select()` on Unix for non-blocking input detection.

- **`_handle_tui_keypress(ch, cmd_buffer, renderer, live) -> Tuple[str, bool]`**: Processes individual keystrokes:
  - `Ctrl+C` (0x03): Returns `should_exit=True`
  - Backspace/Delete: Removes last character from buffer
  - Enter: Dispatches the command, handles live-output commands specially (stops Live display, shows output, waits for Enter)
  - Printable characters: Appends to buffer

#### TUI Mode

- **`run_tui_mode()`**: Main TUI event loop:
  1. Boots the backend console
  2. Primes psutil CPU measurement
  3. Sets up SIGINT handler
  4. On Unix: saves terminal settings and enters cbreak mode
  5. Creates initial layout
  6. Starts StatusPoller
  7. Main loop: reads cached status, detects changes via hash, polls input, throttled refresh (8 FPS max), sleeps for `TUI_INPUT_POLL_INTERVAL_S`
  8. On exit: restores terminal settings, stops poller, shuts down console

#### CLI Mode

- **`build_cli_parser() -> argparse.ArgumentParser`**: Builds the argparse parser for non-interactive CLI mode. Mirrors the command registry structure with subparsers for each category.

- **`_CLI_ARG_EXTRACTORS`**: Dictionary mapping `(category, subcmd)` tuples to lambda functions that extract handler arguments from the parsed argparse namespace.

- **`_extract_cli_handler_args(args, subcmd) -> list`**: Looks up the arg extractor for the given command and returns the handler arguments.

- **`run_cli_mode(argv) -> int`**: Non-interactive command dispatch. Boots the backend console (ROOT-08), dispatches the command, and returns an exit code (0 for success, 1 if the result starts with `[error]`).

#### Entry Point

- **`main()`**: If command-line arguments are provided, runs CLI mode. Otherwise, runs TUI mode.

---

### 6.2 goliath.py — Master Authority Orchestrator

**File:** `goliath.py` (project root, ~304 lines)

A simpler CLI tool that delegates to specific subsystems without the TUI overhead. Used for build, sanitize, integrity, audit, database migration, hospital diagnostics, and baseline checks.

#### Setup

Same guards as `console.py`:
- Path stabilization (F7-12)
- Windows encoding fix
- Rich library requirement

#### Theme

- **`MTS_THEME`**: Rich `Theme` with `info`, `warning`, `error`, `success`, `command`, `path` styles.

#### Logging

- **`setup_logging(log_dir) -> logger`**: Creates a file-based JSON logger at `{PROJECT_ROOT}/logs/goliath_master_{YYYYMMDD}.json`. Appends to daily log files.

#### Class: `GoliathOrchestrator`

**Constructor**: Registers SIGINT and SIGTERM signal handlers and an `atexit` cleanup handler (F7-29).

**Process Management:**

- **`register_child(proc)`**: Tracks a subprocess for cleanup on signal.

- **`_cleanup_children()`**: Terminates all tracked child processes. First attempts `terminate()` with a 5-second wait, then escalates to `kill()` on failure (F7-29).

- **`_signal_handler(sig, frame)`**: Cleans up children and exits on SIGINT/SIGTERM.

**Subsystem Methods:**

- **`print_header()`**: Displays the Goliath header panel.

- **`run_build(test_only: bool)`**: Imports and executes `IndustrialBuildPipeline` from `tools/build_pipeline.py`.

- **`run_sanitize(force: bool)`**: Imports and executes `IndustrialSanitizer` from `tools/Sanitize_Project.py`.

- **`run_manifest()`**: Runs the integrity manifest generator as a subprocess.

- **`run_audit(demo_path: Optional[str])`**: Imports and executes `IndustrialFeatureAuditor` from `tools/Feature_Audit.py`.

- **`run_db(force: bool)`**: Imports and executes `ensure_database_current()` from the Alembic migration utility.

- **`run_baseline()`**: Displays temporal baseline status. Fetches stat card count from the database, generates temporal and legacy baselines, detects meta shifts, and prints results.

- **`run_hospital(department: Optional[str])`**: Runs the Goliath Hospital diagnostic as a subprocess. Optionally filters by department.

#### CLI Parser

Subcommands:
- `build [--test-only]`: Execute the Industrial Build Pipeline
- `sanitize [-y/--yes]`: Clean project for distribution
- `integrity`: Generate source code integrity manifest
- `audit [--demo PATH]`: Verify data and features
- `db [-y/--yes]`: Manage database schema
- `doctor [--dept/-d DEPT]`: Run clinical diagnostics
- `baseline`: Show temporal baseline decay status

#### Entry Point

- **`main()`**: Parses arguments, creates `GoliathOrchestrator`, dispatches to the appropriate subsystem method. Catches unhandled exceptions with Rich traceback and critical logging.

---

## 7. Cross-Cutting Patterns

### 7.1 Singleton Pattern

Nearly every service, manager, and controller uses the singleton pattern. Two variants appear:

1. **Double-Checked Locking** (thread-safe): Used for performance-critical singletons accessed from multiple threads. Pattern:
   ```python
   _instance = None
   _lock = threading.Lock()

   def get_instance():
       global _instance
       if _instance is None:
           with _lock:
               if _instance is None:
                   _instance = SomeClass()
       return _instance
   ```
   Used by: `DatabaseManager`, `HLTVDatabaseManager`, `StateManager`, `CoachingDialogueEngine`, `CoachingService`, `AnalysisOrchestrator`.

2. **Simple Singleton** (not thread-safe): Used for low-contention singletons. Pattern:
   ```python
   _instance = None

   def get_instance():
       global _instance
       if _instance is None:
           _instance = SomeClass()
       return _instance
   ```
   Used by: `LLMService`, `OllamaCoachWriter`, `VisualizationService`, `UserOnboardingManager`.

3. **`__new__` Singleton**: Used by `Console` in `control/console.py`.

### 7.2 Lazy Loading

Services and their dependencies are lazy-loaded to avoid import-time side effects and circular dependencies. The `_get_sys_console()` function in `console.py` is a notable example — the backend console is only imported when first needed.

### 7.3 Timeout Protection

All external calls (LLM, HTTP, subprocess) are wrapped in timeout mechanisms. Three approaches are used:
- `threading.Thread` with `join(timeout)` for LLM calls
- `subprocess.run(timeout=N)` for subprocess calls
- httpx `timeout` parameter for HTTP calls

### 7.4 Security Patterns

- **Path traversal protection**: `Path(filename).name` stripping and `Path.resolve().relative_to()` checks
- **SQL injection prevention**: `_SAFE_COL_TYPE_RE` regex, SQLite Online Backup API (no SQL strings), parameterized queries via ORM
- **Prompt injection prevention**: `_sanitize_llm_context()` and brace escaping in system prompts (BE-03)
- **API key protection**: `getpass` for input (P7-01), masking in display (F7-30), sanitization in error messages (P7-02)
- **HMAC-safe comparison**: `hmac.compare_digest` for API key authentication
- **TLS enforcement**: BE-07 refuses non-localhost without TLS

### 7.5 Cache Patterns

Multiple caching strategies are used:
- **TTL-based caches**: `PlayerLookupService._CACHE_TTL`, `UserOnboardingManager._CACHE_TTL_SECONDS`, `Console._BASELINE_CACHE_TTL_S`
- **LRU cache**: `MatchDataManager._MAX_CACHED_ENGINES` with `OrderedDict`
- **Availability cache**: `LLMService` caches Ollama availability for 60 seconds
- **Background polling cache**: `StatusPoller` caches system status at 2-second intervals

### 7.6 Graceful Degradation

The system degrades gracefully when optional components are unavailable:
- LLM unavailable: Falls back to static coaching messages
- RAG unavailable: Skips knowledge retrieval, uses rule-based coaching
- HLTV database corrupt: Auto-restores from backup
- Individual analysis modules failing: Log suppression prevents flooding, other modules continue
- httpx not installed: Telemetry silently disabled with warning

### 7.7 State Machine Architecture

The application uses a multi-daemon state model:
- **System State**: `IDLE -> BOOTING -> BUSY -> SHUTTING_DOWN` (with `ERROR` and `MAINTENANCE` as exceptional states)
- **Service State**: `STOPPED -> STARTING -> RUNNING -> CRASHED` (with auto-restart)
- **Training State**: `Idle -> Training -> Paused -> Idle` (with `stop_requested` flag)
- **Ingestion Mode**: `SINGLE`, `CONTINUOUS`, `TIMED` (independent of running state)
- **Onboarding Stage**: `AWAITING_FIRST_DEMO -> BUILDING_BASELINE -> COACH_READY` (progressive)

### 7.8 Data Integrity

Multiple layers protect data integrity:
- **WAL mode**: Concurrent reads without blocking writes
- **`PRAGMA quick_check`**: Fast B-tree integrity verification
- **Backup verification**: Every backup is integrity-checked before acceptance
- **Schema versioning**: Per-match databases track schema versions and migrate incrementally
- **Deduplication**: Ingestion checks both file paths and filenames against existing records
- **Size guards**: JSON field size limits prevent unbounded growth (S-07)
- **Orphan detection**: `detect_orphans()` identifies referential integrity violations
