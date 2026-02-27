# Deep Audit Report — Phase 5: Services + Knowledge + Orchestration

**Total Files Audited: 20 / 20**
**Issues Found: 38**
**CRITICAL: 3 | HIGH: 5 | MEDIUM: 20 | LOW: 10**
**Author: Renan Augusto Macena**
**Date: 2026-02-27**
**Auditor: Claude Code (Deep Audit Protocol)**

---

## Scope

Phase 5 covers the service layer (coaching, analysis, dialogue, lessons, LLM, profile, telemetry, visualization), the knowledge management layer (experience bank, RAG, knowledge graph, pro demo miner, KB initialization), the control plane (console, ML controller, DB governor, ingestion manager), and the reporting analytics engine.

### Files Audited

| # | File | LOC | Status |
|---|---|---:|---|
| 1 | `backend/knowledge/experience_bank.py` | 751 | Audited |
| 2 | `backend/services/coaching_service.py` | 585 | Audited |
| 3 | `backend/services/analysis_orchestrator.py` | 518 | Audited |
| 4 | `backend/knowledge/rag_knowledge.py` | 481 | Audited |
| 5 | `backend/control/console.py` | 441 | Audited |
| 6 | `backend/services/lesson_generator.py` | 372 | Audited |
| 7 | `backend/services/coaching_dialogue.py` | 368 | Audited |
| 8 | `backend/reporting/analytics.py` | 359 | Audited |
| 9 | `backend/knowledge/pro_demo_miner.py` | 275 | Audited |
| 10 | `backend/services/llm_service.py` | 253 | Audited |
| 11 | `backend/control/ingest_manager.py` | 232 | Audited |
| 12 | `backend/services/profile_service.py` | 121 | Audited |
| 13 | `backend/control/ml_controller.py` | 111 | Audited |
| 14 | `backend/control/db_governor.py` | 108 | Audited |
| 15 | `backend/services/visualization_service.py` | 106 | Audited |
| 16 | `backend/services/ollama_writer.py` | 106 | Audited |
| 17 | `backend/knowledge/init_knowledge_base.py` | 106 | Audited |
| 18 | `backend/knowledge/graph.py` | 202 | Audited |
| 19 | `backend/services/telemetry_client.py` | 50 | Audited |
| 20 | `backend/services/analysis_service.py` | 92 | Audited |

**Total LOC: ~5,636**

---

## Architecture Summary

### Services Layer (`backend/services/`)

The service layer orchestrates coaching, analysis, and external integrations:

1. **CoachingService** (`coaching_service.py`, 585 LOC) — 4-mode coaching pipeline with priority cascade: COPER (context-aware with experience bank) -> Hybrid (ML + RAG) -> Traditional+RAG -> Basic corrections. Each mode produces `CoachingInsight` records persisted to DB. Phase 6 advanced analysis runs as non-blocking post-processing. Temporal baseline integration (Proposal 11) provides pro comparison context. Ollama polishing via `OllamaCoachWriter` adds natural language enhancement.

2. **AnalysisOrchestrator** (`analysis_orchestrator.py`, 518 LOC) — Coordinates 7 Phase 6 analysis modules (momentum, deception, entropy, game tree, blind spots, engagement range, belief estimation). Produces `MatchAnalysis` aggregating round-level and match-level `CoachingInsight` objects. Each module runs in its own try/except — failure is logged but never crashes the pipeline.

3. **CoachingDialogueEngine** (`coaching_dialogue.py`, 368 LOC) — Multi-turn interactive coaching via Ollama's `/api/chat`. Intent classification (positioning/utility/economy/aim) routes to RAG + Experience Bank retrieval. Sliding context window (`MAX_CONTEXT_TURNS=6`). Graceful offline fallback with template-based responses.

4. **LessonGenerator** (`lesson_generator.py`, 372 LOC) — Generates structured coaching lessons from demo analysis. Sections: overview, strengths, improvements, pro tips, narrative (LLM-enhanced). Map-specific pro tips for 5 maps. Lazy-loaded DB connection.

5. **LLMService** (`llm_service.py`, 253 LOC) — Ollama integration with availability caching (60s TTL). Single-shot `/api/generate` and multi-turn `/api/chat` endpoints. Configurable model via `OLLAMA_MODEL` env var. All failures return `[LLM ...]` error markers for upstream detection.

6. **OllamaCoachWriter** (`ollama_writer.py`, 106 LOC) — Natural language polishing for coaching insights. Disabled by default (`USE_OLLAMA_COACHING`). Falls back gracefully to raw template text.

7. **ProfileService** (`profile_service.py`, 121 LOC) — Steam + FaceIT external API integration with 10s timeouts. CS2 hours extraction via app ID 730. Profile persistence with upsert pattern.

8. **AnalysisService** (`analysis_service.py`, 92 LOC) — Lightweight service wrapping `EliteAnalytics` and `detect_feature_drift()`. Latest performance retrieval, pro comparison, drift detection.

9. **VisualizationService** (`visualization_service.py`, 106 LOC) — Matplotlib radar charts for user-vs-pro comparison. Two modes: file output and BytesIO buffer.

10. **TelemetryClient** (`telemetry_client.py`, 50 LOC) — Sends match stats to central ML Coach server via HTTP POST. Currently configured for localhost only.

### Knowledge Layer (`backend/knowledge/`)

1. **ExperienceBank** (`experience_bank.py`, 751 LOC) — COPER Experience component. SHA256 context hashing for fast exact-match lookups + cosine similarity over sentence-transformer embeddings for semantic search. Feedback loop with EMA (0.7/0.3) effectiveness tracking. Stale experience decay (90-day max, 10% confidence reduction). Singleton via `get_experience_bank()`.

2. **KnowledgeRetriever/KnowledgePopulator/KnowledgeEmbedder** (`rag_knowledge.py`, 481 LOC) — RAG pipeline. Sentence-BERT embeddings (`all-MiniLM-L6-v2`) with SHA256 hash fallback. Embedding version tracking (`v2`) for automatic re-embedding on model change. Cosine similarity ranking with usage count tracking. JSON-based population from knowledge files.

3. **KnowledgeGraphManager** (`graph.py`, 202 LOC) — SQLite-backed entity-relation graph. Entities with observations, directed relations with metadata. Currently supports 1-hop subgraph queries only. WAL mode enabled.

4. **ProDemoMiner** (`pro_demo_miner.py`, 275 LOC) — Extracts tactical knowledge from HLTV downloads. Generates positioning and utility knowledge per map, economy knowledge per event. `AdvancedProDemoMiner` subclass has two `NotImplementedError` placeholder methods.

5. **init_knowledge_base.py** (106 LOC) — KB initialization script. Loads manual knowledge from JSON + auto-populates from pro demos.

### Control Plane (`backend/control/`)

1. **Console** (`console.py`, 441 LOC) — Singleton control authority. `ServiceSupervisor` manages background processes with auto-restart (max 3 retries/hour). Domain managers: `IngestionManager`, `DatabaseGovernor`, `MLController`. Baseline and training data caches with TTL. Boot/shutdown sequences. Safe error isolation in `get_system_status()`.

2. **MLController** (`ml_controller.py`, 111 LOC) — Training lifecycle supervisor. `MLControlContext` token with stop/pause/resume/throttle. Training runs in daemon thread via `CoachTrainingManager.run_full_cycle()`.

3. **DatabaseGovernor** (`db_governor.py`, 108 LOC) — Storage audit (Tier 1/2 monolith + Tier 3 match DBs). Integrity verification (lightweight SELECT 1 or full PRAGMA quick_check). Index rebuild via REINDEX.

4. **IngestionManager** (`ingest_manager.py`, 232 LOC) — Three modes: SINGLE, CONTINUOUS, TIMED. Sequential file processing with progress tracking via `StateManager`. Discovery -> Processing -> Mode-dependent loop control.

### Reporting (`backend/reporting/`)

1. **AnalyticsEngine** (`analytics.py`, 359 LOC) — Dashboard analytics: player trends (DataFrame), skill radar (5 axes), training metrics, rating history, per-map stats, strength/weakness (Z-score vs pro baseline), utility breakdown (user vs pro with DB query or fallback), HLTV 2.0 breakdown (5 rating components).

---

## Findings

### F5-01: Anti-Fabrication Violation in analytics.py (CRITICAL)

**File:** `backend/reporting/analytics.py:293-302`
**Severity:** CRITICAL
**Skill:** data-lifecycle-review, deep-audit

The `get_utility_breakdown()` method has hardcoded fallback pro baseline values when no pro data exists in DB:

```python
pro = {
    "he_damage": 4.5,
    "molotov_damage": 6.2,
    "smokes_per_round": 1.1,
    "flash_blind_time": 12.0,
    "flash_assists": 0.8,
    "unused_utility": 0.3,
    "_provenance": "fallback",
}
```

**Violation:** CLAUDE.md Anti-Fabrication Rule: "No mock data, synthetic data, or fabricated outputs." These are invented numbers without documented provenance.

**Mitigation:** The `_provenance: "fallback"` tag provides transparency, but the values themselves are synthetic. Should either return empty dict or query `TemporalBaselineDecay.get_temporal_baseline()` for real pro data.

---

### F5-02: Anti-Fabrication Violation in telemetry_client.py (CRITICAL)

**File:** `backend/services/telemetry_client.py:46-49`
**Severity:** CRITICAL
**Skill:** deep-audit, security-scan

The `__main__` block contains synthetic dummy data:

```python
if __name__ == "__main__":
    dummy_stats = {"kills": 24, "deaths": 12, "headshot_pct": 45.5, "map": "de_mirage"}
    send_match_telemetry("User_Test_001", "match_display_123", dummy_stats)
```

**Violation:** CLAUDE.md Anti-Fabrication Rule. Fabricated test data in a module that sends data to an external server. Additionally, the field names (`kills`, `deaths`) don't match the project's canonical field names (`avg_kills`, `avg_deaths`).

---

### F5-03: Unbounded DB Query in rag_knowledge.py (CRITICAL)

**File:** `backend/knowledge/rag_knowledge.py:120`
**Severity:** CRITICAL
**Skill:** db-review, deep-audit

`trigger_reembedding()` loads all TacticalKnowledge records into memory without LIMIT:

```python
entries = session.exec(select(TacticalKnowledge)).all()
```

With a growing knowledge base, this will cause unbounded memory consumption. Same pattern appears in `init_knowledge_base.py:76`:

```python
total = session.exec(select(TacticalKnowledge)).all()
```

**Impact:** OOM risk on large knowledge bases. Both should use batched processing or `func.count()` for statistics.

---

### F5-04: Non-Singleton ExperienceBank Creation in coaching_service.py (HIGH)

**File:** `backend/services/coaching_service.py:125`
**Severity:** HIGH
**Skill:** api-contract-review, state-audit

`_generate_coper_insights()` creates `ExperienceBank()` directly instead of using the `get_experience_bank()` singleton factory:

```python
bank = ExperienceBank()
```

Each call creates a new instance, re-initializing `init_database()` and `KnowledgeEmbedder()` (which loads the Sentence-BERT model). This wastes memory and slows down COPER coaching. Same pattern appears in `coaching_dialogue.py:271`:

```python
bank = ExperienceBank()
```

And in `rag_knowledge.py:440`:

```python
bank = ExperienceBank()
```

**Fix:** Replace all with `get_experience_bank()`.

---

### F5-05: NotImplementedError in Public API (HIGH)

**File:** `backend/knowledge/pro_demo_miner.py:241,252`
**Severity:** HIGH
**Skill:** api-contract-review

`AdvancedProDemoMiner` has two public methods that raise `NotImplementedError`:

```python
def parse_demo_file(self, demo_path: Path) -> Dict:
    raise NotImplementedError("Demo file parsing not yet implemented")

def detect_successful_executes(self, rounds: List[Dict]) -> List[Dict]:
    raise NotImplementedError("Execute detection not yet implemented")
```

**Impact:** Any caller using `AdvancedProDemoMiner` will crash at runtime. The class should either be marked as abstract (ABC) or the methods should return sentinel values.

---

### F5-06: LLM Fallback Lacks Recursion Guard (HIGH)

**File:** `backend/services/coaching_dialogue.py:127-158`
**Severity:** HIGH
**Skill:** correctness-check, resilience-check

In `respond()`, if the LLM returns an error marker, `_fallback_response()` is called which invokes `_retrieve_context()`, which creates a new `ExperienceBank()` (F5-04). If experience retrieval also fails, the error is caught silently. While not recursive per se, the fallback path creates expensive objects and makes multiple DB calls without circuit-breaking.

More concerning: if `_llm.chat()` throws an exception (not just returns error marker), the exception propagates unhandled and the history becomes inconsistent (user message was already appended at L145 before the LLM call at L150).

---

### F5-07: rglob on Potentially Large/Network Drives (HIGH)

**File:** `backend/control/console.py:394,400`
**Severity:** HIGH
**Skill:** resilience-check

`_get_training_data_progress()` uses `rglob("*.dem")` on user-configured demo paths:

```python
pro_dem_available = sum(1 for _ in pro_dir.rglob("*.dem"))
user_dem_available = sum(1 for _ in user_dir.rglob("*.dem"))
```

**Impact:** If these paths point to a network drive or a directory with deep nested structures, rglob can hang for minutes, blocking the status endpoint. The 120s cache TTL mitigates repeat calls but not the initial hang.

**Mitigation exists:** Cache TTL reduces frequency, but no timeout/circuit-breaker on the rglob itself.

---

### F5-08: Hardcoded DB Path in KnowledgeGraphManager (HIGH)

**File:** `backend/knowledge/graph.py:29-35`
**Severity:** HIGH
**Skill:** db-review, correctness-check

```python
DB_PATH = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
    "data",
    "knowledge_graph.db",
)
```

This constructs the path from `__file__` traversals, which is fragile across different installation layouts. The path should use `config.py` constants like `DB_DIR` or `CORE_DB_DIR`.

Additionally, raw `sqlite3.connect()` is used instead of SQLModel/SQLAlchemy, creating a parallel database management path outside the project's ORM architecture.

---

### F5-09: datetime.utcnow() Deprecated (MEDIUM)

**File:** `backend/knowledge/experience_bank.py:557,644`
**Severity:** MEDIUM
**Skill:** correctness-check

`datetime.utcnow()` is deprecated in Python 3.12+ in favor of `datetime.now(timezone.utc)`. Appears in:

- `experience_bank.py:557` — `last_feedback_at = datetime.utcnow()`
- `experience_bank.py:644` — `cutoff = datetime.utcnow() - timedelta(days=max_age_days)`
- `profile_service.py:43` — `last_updated=datetime.datetime.utcnow()`
- `lesson_generator.py:63` — `datetime.utcnow().isoformat()`
- `console.py:87,137,290` — Multiple occurrences

---

### F5-10: Unbounded Query in experience_bank.py decay (MEDIUM)

**File:** `backend/knowledge/experience_bank.py:647-652`
**Severity:** MEDIUM
**Skill:** db-review

`decay_stale_experiences()` fetches all stale experiences without LIMIT:

```python
stale = session.exec(stmt).all()
```

Should add `.limit(1000)` or batch processing to prevent memory pressure on large experience banks.

---

### F5-11: Emojis in Backend Logic (MEDIUM)

**File:** `backend/knowledge/rag_knowledge.py:356-358`
**Severity:** MEDIUM
**Skill:** deep-audit

```python
insight_parts.append(f"\U0001f4a1 {k.title}: {k.description}")
insight_parts.append(f"   \U0001f4ca Pro example: {k.pro_example}")
```

Emojis in backend data violate separation of concerns. Rendering decisions belong in the UI layer.

---

### F5-12: print() Statements Instead of Logger (MEDIUM)

**File:** `backend/knowledge/init_knowledge_base.py:87-101`
**Severity:** MEDIUM
**Skill:** observability-audit

`initialize_knowledge_base()` uses `print()` for statistics output:

```python
print(f"\n{'='*50}")
print(f"Total Knowledge Entries: {len(total)}")
```

Also in `rag_knowledge.py:391-398`:

```python
print(f"Found {len(results)} results:\n")
```

And `pro_demo_miner.py:274`:

```python
print(f"Mined {count} knowledge entries from pro demos")
```

CLAUDE.md requires structured logging via `get_logger()`.

---

### F5-13: Hardcoded Ollama URL (MEDIUM)

**File:** `backend/services/llm_service.py:24`
**Severity:** MEDIUM
**Skill:** resilience-check

```python
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
```

Env var provides configurability, but `http://` is plaintext. For production deployments, should consider HTTPS. Similarly, `telemetry_client.py:12`:

```python
DEV_SERVER_URL = "http://127.0.0.1:8000"
```

Hardcoded with no env var override.

---

### F5-14: Silent Exception Handlers in analysis_orchestrator.py (MEDIUM)

**File:** `backend/services/analysis_orchestrator.py:199,248,344,400,509`
**Severity:** MEDIUM
**Skill:** correctness-check, observability-audit

Five analysis methods catch all exceptions with `logger.error()` but return empty lists, effectively hiding failures:

```python
except Exception as e:
    logger.error("Momentum analysis failed: %s", e)
return insights  # Always returns empty list on failure
```

While this is intentional (non-blocking analysis), it means a persistently failing module will silently produce zero insights with no alerting mechanism. Consider adding a failure counter or metric.

---

### F5-15: Busy-Wait Loop in MLControlContext (MEDIUM)

**File:** `backend/control/ml_controller.py:24-25`
**Severity:** MEDIUM
**Skill:** correctness-check, resilience-check

```python
def check_state(self):
    while self._pause_requested:
        time.sleep(1)
```

Busy-wait with 1s polling. Should use `threading.Event` for cleaner signaling:

```python
self._resume_event = threading.Event()
self._resume_event.wait()  # Blocks until set, no CPU waste
```

---

### F5-16: StopIteration Used for Control Flow (MEDIUM)

**File:** `backend/control/ml_controller.py:28`
**Severity:** MEDIUM
**Skill:** correctness-check

```python
raise StopIteration("ML Operator requested termination.")
```

`StopIteration` is reserved for iterator protocol (PEP 479). Using it for control flow can cause confusing behavior if caught by generator frames. Should use a custom exception (e.g., `TrainingStopRequested`).

---

### F5-17: f-string in Logger Call (MEDIUM)

**File:** `backend/knowledge/experience_bank.py:567-568`
**Severity:** MEDIUM
**Skill:** observability-audit

```python
logger.info(
    f"Feedback recorded for experience {experience_id}: "
    f"effectiveness={effectiveness:.2f}"
)
```

Should use lazy formatting: `logger.info("Feedback recorded for experience %s: effectiveness=%.2f", experience_id, effectiveness)`.

---

### F5-18: Hardcoded Thresholds in lesson_generator.py (MEDIUM)

**File:** `backend/services/lesson_generator.py:121,132,198,211`
**Severity:** MEDIUM
**Skill:** ml-check

Multiple magic numbers for performance thresholds:

- `adr > 75` (L121) — strength threshold
- `hs > 0.4` (L132) — HS% strength
- `adr < 60` (L186) — improvement threshold
- `hs < 0.35` (L198) — HS% improvement
- `deaths > kills * 1.5 and deaths > 15` (L211) — death ratio

Should be extracted to named constants or config.

---

### F5-19: No Error Handling in VisualizationService (MEDIUM)

**File:** `backend/services/visualization_service.py:10-57`
**Severity:** MEDIUM
**Skill:** resilience-check

`generate_performance_radar()` and `plot_comparison_v2()` have no try/except. If `user_stats` or `pro_stats` are empty or have mismatched keys, matplotlib will throw with an unhelpful error.

---

### F5-20: Duplicate _infer_round_phase Logic (MEDIUM)

**File:** `backend/services/coaching_service.py:262-271`, `backend/knowledge/experience_bank.py:675-684`, `backend/knowledge/rag_knowledge.py:471-480`
**Severity:** MEDIUM
**Skill:** correctness-check

`_infer_round_phase()` is duplicated in three separate files with identical logic (equipment thresholds: 1500/3000/4000). Should be extracted to a shared utility function.

---

### F5-21: Missing Commit in profile_service.py (MEDIUM)

**File:** `backend/services/profile_service.py:101-106`
**Severity:** MEDIUM
**Skill:** db-review

`_persist_profile_update()` modifies the profile but never calls `session.commit()`:

```python
def _persist_profile_update(profile):
    db = get_db_manager()
    with db.get_session() as session:
        stmt = select(PlayerProfile).where(PlayerProfile.player_name == CS2_PLAYER_NAME)
        existing = session.exec(stmt).first()
        _update_or_add_profile(session, existing, profile)
```

The `with db.get_session()` context manager likely auto-commits on exit, but this is an implicit dependency rather than an explicit commit.

---

### F5-22: Secrets in Config Import (MEDIUM)

**File:** `backend/services/profile_service.py:10`
**Severity:** MEDIUM
**Skill:** security-scan

```python
from Programma_CS2_RENAN.core.config import CS2_PLAYER_NAME, FACEIT_API_KEY, STEAM_API_KEY
```

API keys are imported as module-level constants. If `config.py` loads them from env vars, this is acceptable. But the direct import pattern means the keys are in memory for the entire process lifetime and could appear in tracebacks/dumps. Verify they originate from env vars or a secrets manager.

---

### F5-23: init_database() Side Effect in Constructors (MEDIUM)

**File:** `backend/knowledge/experience_bank.py:103`, `backend/knowledge/rag_knowledge.py:152,241`
**Severity:** MEDIUM
**Skill:** state-audit

Multiple constructors call `init_database()` as a side effect:

- `ExperienceBank.__init__()` (L103)
- `KnowledgeRetriever.__init__()` (L152)
- `KnowledgePopulator.__init__()` (L241)

`init_database()` should be called once at application startup, not in every service constructor. While it's likely idempotent, it adds unnecessary overhead and creates implicit coupling.

---

### F5-24: Hardcoded System Prompt in ollama_writer.py (MEDIUM)

**File:** `backend/services/ollama_writer.py:20-24`
**Severity:** MEDIUM
**Skill:** ml-check

```python
COACH_SYSTEM_PROMPT = (
    "You are a CS2 tactical coach. Based on the analysis data provided, "
    ...
)
```

System prompts should be configurable (config file or DB) to allow tuning without code changes. Same applies to `coaching_dialogue.py:77-91` and `llm_service.py:167-170`.

---

### F5-25: Hardcoded Retry/TTL Constants in Console (MEDIUM)

**File:** `backend/control/console.py:133-139,211-218`
**Severity:** MEDIUM
**Skill:** correctness-check

Multiple magic numbers: auto-restart max retries (3), retry window (3600s/1h), baseline cache TTL (60s), training data cache TTL (120s). Should be class-level named constants.

---

### F5-26: `== False` in SQLModel Queries (LOW)

**File:** Multiple files
**Severity:** LOW
**Skill:** correctness-check

PEP 8 violation using `== False` instead of `is False` or `.is_(False)`:

- `experience_bank.py:593,648` — `CoachingExperience.outcome_validated == False`
- `analytics.py:32,123,147,253,278,330` — `PlayerMatchStats.is_pro == False`
- `lesson_generator.py:328` — `PlayerMatchStats.is_pro == False`
- `analytics.py:277,374` — `PlayerMatchStats.is_pro == True`

**Note:** In SQLModel/SQLAlchemy, `== False` is actually correct syntax for generating SQL `WHERE col = 0`. The `noqa: E712` comments confirm awareness. This is a stylistic issue only.

---

### F5-27: rag_knowledge.py __main__ Block (LOW)

**File:** `backend/knowledge/rag_knowledge.py:363-399`
**Severity:** LOW
**Skill:** deep-audit

The `__main__` block creates sample knowledge entries and runs retrieval tests. While useful for development, it should be in a separate test script. The hardcoded test data (`"Team Liquid vs NAVI - IEM Katowice 2024"`) is not real production data.

---

### F5-28: Unused Import in visualization_service.py (LOW)

**File:** `backend/services/visualization_service.py:2`
**Severity:** LOW
**Skill:** correctness-check

```python
import os
```

`os` is imported but never used in the file.

---

### F5-29: Missing Type Hints in profile_service.py (LOW)

**File:** `backend/services/profile_service.py:50-58`
**Severity:** LOW
**Skill:** deep-audit

Helper functions `_execute_steam_fetch()`, `_parse_steam_response()`, `_fetch_cs2_hours()`, `_execute_faceit_fetch()` lack type annotations on parameters and return values.

---

### F5-30: graph.py add_entity Shadows Builtin (LOW)

**File:** `backend/knowledge/graph.py:75`
**Severity:** LOW
**Skill:** correctness-check

```python
def add_entity(self, name: str, type: str, observations: List[str] = None):
```

Parameter `type` shadows the Python builtin `type()`. Should use `entity_type` instead.

---

### F5-31: No Timeout on DB Integrity Check (LOW)

**File:** `backend/control/db_governor.py:86`
**Severity:** LOW
**Skill:** resilience-check

```python
res = session.execute(text("PRAGMA quick_check")).scalar()
```

`PRAGMA quick_check` on a 16+ GB monolith can take minutes. No timeout is configured. The docstring warns about this, but there's no programmatic guard.

---

### F5-32: Hardcoded 30-Minute Interval in ingest_manager.py (LOW)

**File:** `backend/control/ingest_manager.py:40`
**Severity:** LOW
**Skill:** correctness-check

```python
self._interval_minutes = 30
```

Hardcoded default. Should come from `config.py` or be configurable via `set_mode()`.

---

### F5-33: Missing Logger in profile_service.py (LOW)

**File:** `backend/services/profile_service.py`
**Severity:** LOW
**Skill:** observability-audit

No logger is initialized in this file. All error handling returns error dicts silently. Should use `get_logger("cs2analyzer.profile_service")` for structured error reporting.

---

### F5-34: Console shutdown Busy-Wait (MEDIUM)

**File:** `backend/control/console.py:251-256`
**Severity:** MEDIUM
**Skill:** resilience-check

```python
for _ in range(10):
    ml_status = self.ml_controller.get_status()
    ingest_status = self.ingest_manager.get_status()
    if not ml_status.get("is_running") and not ingest_status.get("is_running"):
        break
    time.sleep(0.5)
```

Polling loop with 5s max wait. Should use `threading.Event` or at minimum log if the timeout is hit without clean shutdown.

---

### F5-35: IngestionManager Busy-Wait Loops (MEDIUM)

**File:** `backend/control/ingest_manager.py:152-155,163-166`
**Severity:** MEDIUM
**Skill:** resilience-check

```python
for _ in range(self._interval_minutes * 60):
    if self._stop_requested:
        break
    time.sleep(1)
```

1-second polling for up to 30 minutes (1800 iterations). Should use `threading.Event.wait(timeout=self._interval_minutes * 60)` for immediate response to stop requests without polling overhead.

---

### F5-36: Knowledge Graph Depth=1 Only (LOW)

**File:** `backend/knowledge/graph.py:126-144`
**Severity:** LOW
**Skill:** api-contract-review

`query_subgraph()` accepts a `depth` parameter but only implements depth=1. The warning log is appropriate but the parameter creates a misleading API contract.

---

### F5-37: Non-Singleton AnalysisOrchestrator Factory (LOW)

**File:** `backend/services/analysis_orchestrator.py:515-517`
**Severity:** LOW
**Skill:** api-contract-review

```python
def get_analysis_orchestrator() -> AnalysisOrchestrator:
    return AnalysisOrchestrator()
```

Creates a new instance every call. The constructor imports and instantiates 7 analysis modules. Should use singleton pattern like other services.

---

### F5-38: CoachingService Non-Singleton Factory (LOW)

**File:** `backend/services/coaching_service.py:583-584`
**Severity:** LOW
**Skill:** api-contract-review

```python
def get_coaching_service() -> CoachingService:
    return CoachingService()
```

Creates a new instance every call. `CoachingService.__init__()` calls `get_db_manager()` and `get_setting()` — lightweight, but the non-singleton pattern is inconsistent with the rest of the codebase.

---

## Cross-Phase Verification

### Quality Gate: Coaching Fallback Chain (G-08)

The coaching fallback chain was verified:

1. **COPER mode** (`use_coper=True`, default): Requires `map_name` AND `tick_data`. Falls back to Hybrid on failure (L196-197).
2. **Hybrid mode** (`use_hybrid=True`): Requires `player_stats`. Falls back with warning on failure (L367-370). Note: fallback to Traditional requires `deviations` which may not be available — potential dead end.
3. **Traditional mode**: Runs `generate_corrections(deviations, rounds_played)`. Optionally enhanced with RAG if `use_rag=True`.

**Gap identified:** If COPER fails and Hybrid is not enabled, and no `deviations` dict was passed, no coaching is generated at all (L199-202 logs warning but produces nothing). This is a silent degradation path.

### Quality Gate: ExperienceBank Scoring

Scoring algorithm verified:
- `score = (similarity + hash_bonus + effectiveness_bonus) * confidence`
- Hash bonus: 0.2 for exact context match
- Effectiveness bonus: `effectiveness_score * 0.4` (only if validated)
- Candidates limited to 100 per query (L205)
- Feedback EMA: `0.7 * old + 0.3 * new` (L550-551)
- Confidence adjustment: `effectiveness * 0.05`, clamped [0.1, 1.0] (L560-561)

**Assessment:** Scoring is reasonable. The 0.4 effectiveness weight means validated experiences can significantly outrank high-similarity but unvalidated ones, which is desirable.

### Quality Gate: Service-UI Cross-Reference

Service outputs verified against Fase 7 UI contract expectations:
- `CoachingInsight` model used consistently across services (coaching_service, analysis_orchestrator)
- `PlayerMatchStats` field names correct: `avg_kills`, `avg_deaths`, `avg_adr`, `avg_kast`, `avg_hs`, `rating`, `kd_ratio`
- `AnalyticsEngine` methods produce dict/DataFrame outputs suitable for UI widgets

### AIstate.md Reconciliation

- **G-07 (Belief Calibration):** `coaching_service.py` does NOT call `_run_belief_calibration()` in session_engine.py. This confirms AIstate.md G-07 finding that Teacher daemon wiring is disconnected. ExperienceBank feedback loop operates independently.
- **G-08 (Coaching Fallback):** New finding documented above — COPER -> Hybrid fallback works, but Hybrid -> Traditional fallback requires `deviations` that may not exist.

---

## Summary Statistics

| Category | Count |
|---|---:|
| Anti-Fabrication Violations | 2 |
| Unbounded DB Queries | 2 |
| Singleton Pattern Violations | 4 |
| Busy-Wait Loops | 3 |
| Hardcoded Values | 7 |
| Missing Error Handling | 2 |
| Deprecated API Usage | 6 |
| Code Duplication | 1 |
| Security Concerns | 2 |
| Observability Gaps | 3 |

### Severity Distribution

| Severity | Count | % |
|---|---:|---:|
| CRITICAL | 3 | 7.9% |
| HIGH | 5 | 13.2% |
| MEDIUM | 20 | 52.6% |
| LOW | 10 | 26.3% |
| **TOTAL** | **38** | **100%** |

### Cross-Phase Issue Accumulation

| Phase | Files | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---:|---:|---:|---:|---:|---:|
| Phase 1 | 29 | 2 | 3 | 15 | 17 | 37 |
| Phase 2 | 25 | 4 | 5 | 18 | 15 | 42 |
| Phase 3 | 41 | 4 | 6 | 19 | 9 | 38 |
| Phase 4 | 19 | 1 | 3 | 14 | 6 | 24 |
| Phase 5 | 20 | 3 | 5 | 20 | 10 | 38 |
| **Cumulative** | **134** | **14** | **22** | **86** | **57** | **179** |
