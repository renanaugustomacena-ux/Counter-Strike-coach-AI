# Audit Report 05 — Coaching & Services

**Scope:** `backend/services/`, `backend/knowledge/`, `backend/coaching/` — 28 files, ~6,842 lines | **Date:** 2026-03-10
**Open findings:** 0 HIGH | 15 MEDIUM | 12 LOW

---

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| C-01 | analysis_orchestrator.py | GIL-dependent double-checked locking singleton (PEP-703 risk) |
| C-02 | analysis_orchestrator.py | No log suppression for repeated module failures |
| C-07 | coaching_dialogue.py | RAG retrieval context injected into LLM prompt without sanitization |
| C-08 | coaching_dialogue.py | Hardcoded T-side full_buy defaults when game state unknown |
| C-10 | coaching_service.py | Fallback chain drops NN refinement (nn_adjustments not passed) |
| C-11 | coaching_service.py | Millions of tick rows converted to in-memory DataFrame synchronously |
| C-14 | lesson_generator.py | Hardcoded pro player tips (s1mple, ropz) — stale over time |
| C-16 | llm_service.py | LLM prompt concatenates unvalidated user input (low risk for local Ollama) |
| C-18 | profile_service.py | `_fetch_cs2_hours()` no retry logic or timeout handling |
| C-20 | telemetry_client.py | HTTP telemetry in production (no HTTPS enforcement for non-localhost) |
| C-22 | visualization_service.py | Module-level singleton instantiated at import time — matplotlib crash on import |
| C-25 | experience_bank.py | Brute-force similarity limit(100) caps searchable experiences |
| C-26 | experience_bank.py | `usage_count += 1` race condition (last-write-wins) |
| C-29 | graph.py | Per-operation SQLite connections (no pooling) |
| C-32 | pro_demo_miner.py | KAST/HS normalization boundary fragile at exactly 1.0 |
| C-34 | rag_knowledge.py | Fallback bag-of-words embeddings low quality — negation not captured |
| C-36 | vector_index.py | Base64 vs JSON embedding deserialization mismatch (FAISS path) |
| C-40 | explainability.py | Template defaults use fabricated values, not wired to real data |
| C-42 | hybrid_engine.py | MetaDriftEngine crash propagates to confidence calculation |
| C-45 | pro_bridge.py | `avg_kills`/`avg_deaths` are actually KPR/DPR — naming mismatch |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| C-03 | analysis_orchestrator.py | `[:-1]` slice is a no-op bug in `_build_chat_messages()` |
| C-04 | analysis_service.py | `analyze_latest_performance()` returns only single most recent match |
| C-05 | analysis_service.py | `check_for_drift()` re-queries same data each call (no cache) |
| C-09 | coaching_dialogue.py | Misleading comment about user message append timing |
| C-12 | coaching_service.py | `KnowledgeRetriever()` instantiated per call (loads Sentence-BERT each time) |
| C-13 | coaching_service.py | Sentry breadcrumb `except ImportError` doesn't catch non-ImportError |
| C-17 | llm_service.py | Silent model substitution when configured model not found |
| C-19 | profile_service.py | App ID 730 comment missing (CS2 replaced CS:GO in-place) |
| C-21 | telemetry_client.py | No retry logic for telemetry submission |
| C-23 | visualization_service.py | `plt.close(fig)` not in finally block after `savefig()` |
| C-24 | knowledge/__init__.py | Eager import triggers SQLite DB init on package import |
| C-31 | init_knowledge_base.py | Missing `tactical_knowledge.json` only logged as warning |
| C-33 | pro_demo_miner.py | Archetype classification thresholds hardcoded |
| C-35 | rag_knowledge.py | `_brute_force_retrieve()` loads up to 500 full records into memory |
| C-37 | vector_index.py | `_load_knowledge_vectors()` loads ALL entries without limit |
| C-38 | coaching/__init__.py | Eager HybridCoachingEngine import triggers PyTorch load |
| C-39 | correction_engine.py | No actionable corrections until ~30 rounds played |
| C-43 | hybrid_engine.py | `__main__` block uses hardcoded synthetic stats |
| C-44 | longitudinal_engine.py | Regression insight always "Refocus on fundamentals" |
| C-46 | pro_bridge.py | Default values (HS 0.45, entry_rate 0.25) hardcoded |
| C-47 | token_resolver.py | Uses raw deltas instead of Z-scores for comparison |

## Cross-Cutting

1. **Stale Baselines** — Multiple modules contain hardcoded pro player references and statistical baselines that drift over time.
2. **Embedding Serialization Mismatch** — ExperienceBank uses base64, vector_index uses json.loads. FAISS rebuilds will fail for new entries.
3. **RAG Retriever Instantiation Cost** — `KnowledgeRetriever()` loads Sentence-BERT on init, instantiated without caching in multiple places.
