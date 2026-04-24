> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge — RAG Retrieval & COPER Experience Bank

> **Authority:** COPER Coaching Framework (Context Optimized with Prompt, Experience, and Replay)

The `backend/knowledge/` module is the semantic memory layer of the CS2 coaching
system. It implements Retrieval-Augmented Generation (RAG) for tactical knowledge,
a COPER Experience Bank for learning from past gameplay, a FAISS vector index for
sub-linear nearest-neighbor search, a Knowledge Graph for multi-hop relational
reasoning, and a pro-stats mining pipeline that converts HLTV professional player
statistics into coaching knowledge entries. Together, these components allow the
coaching engine to deliver context-aware, experience-grounded advice that improves
over time as more demos are analyzed and more feedback is collected.

---

## File Inventory

| File | Purpose | Key Classes / Functions |
|------|---------|------------------------|
| `experience_bank.py` | COPER Experience Bank: store, retrieve, and synthesize gameplay experiences | `ExperienceBank`, `ExperienceContext`, `SynthesizedAdvice`, `get_experience_bank()` |
| `rag_knowledge.py` | RAG knowledge retrieval with Sentence-BERT embeddings | `KnowledgeEmbedder`, `KnowledgeRetriever`, `KnowledgePopulator`, `generate_rag_coaching_insight()`, `generate_unified_coaching_insight()` |
| `vector_index.py` | FAISS-backed vector index for sub-linear ANN search | `VectorIndexManager`, `get_vector_index_manager()` |
| `graph.py` | Knowledge Graph with entity-relation storage and BFS subgraph queries | `KnowledgeGraphManager`, `get_knowledge_graph()` |
| `pro_demo_miner.py` | Mine coaching knowledge from HLTV pro player stat cards | `ProStatsMiner` (`ProDemoMiner` alias), `auto_populate_from_pro_demos()` |
| `init_knowledge_base.py` | One-shot initialization: loads JSON, mines pro stats, builds FAISS indexes | `initialize_knowledge_base()` |
| `round_utils.py` | Shared round-phase inference from equipment value | `infer_round_phase()` |
| `tactical_knowledge.json` | Seed data: 15 hand-authored tactical knowledge entries covering 7 maps | (JSON data) |
| `__init__.py` | Package exports | `KnowledgeGraphManager`, `get_knowledge_graph` |

---

## Architecture

The module is organized around four retrieval strategies that feed into the
coaching engine through `generate_unified_coaching_insight()`:

```
                     +---------------------+
                     | coaching_service.py  |
                     |  (COPER / Hybrid)    |
                     +----------+----------+
                                |
                 generate_unified_coaching_insight()
                                |
              +-----------------+-----------------+
              |                                   |
   +----------v----------+          +-------------v-----------+
   | KnowledgeRetriever   |          | ExperienceBank          |
   |  (RAG tactical)      |          |  (COPER experiences)    |
   +---------+------------+          +------------+------------+
             |                                    |
     +-------v-------+                   +--------v--------+
     | VectorIndex    |                   | VectorIndex     |
     | "knowledge"    |                   | "experience"    |
     | (FAISS / brute)|                   | (FAISS / brute) |
     +-------+--------+                   +--------+--------+
             |                                     |
     +-------v--------+                   +--------v---------+
     | TacticalKnowledge|                  | CoachingExperience|
     | (database.db)    |                  | (database.db)     |
     +------------------+                  +-------------------+
```

### Embedding Pipeline

All text is embedded using Sentence-BERT (`all-MiniLM-L6-v2`, 384 dimensions).
When the `sentence-transformers` package is not installed, a deterministic
hash-projection fallback produces 100-dimensional vectors with degraded but
functional semantic similarity. The `KnowledgeEmbedder` class manages model
loading, caching, version tracking (`CURRENT_VERSION = "v3"`), and automatic
re-embedding when the model changes dimension.

### FAISS Vector Index

`VectorIndexManager` maintains two named FAISS `IndexFlatIP` indexes:

- **`knowledge`** -- indexes `TacticalKnowledge.embedding` rows
- **`experience`** -- indexes `CoachingExperience.embedding` rows

Vectors are L2-normalized before indexing so that inner product equals cosine
similarity. Indexes are persisted to disk (`<STORAGE_ROOT>/indexes/`) and
rebuilt lazily when marked dirty via `mark_dirty()`. Over-fetch multipliers
(`OVERFETCH_KNOWLEDGE=10`, `OVERFETCH_EXPERIENCE=20`) compensate for
post-filtering by map, category, confidence, and outcome. When FAISS is not
installed, all searches fall back to brute-force cosine similarity.

### Experience Bank Scoring

The `ExperienceBank` uses a composite scoring formula for retrieval:

```
score = (similarity + hash_bonus + effectiveness_bonus) * confidence
```

Where:
- `similarity` -- cosine similarity from FAISS or brute-force (0.0 to 1.0)
- `hash_bonus` -- 0.2 if `context_hash` matches exactly (same map + side + phase + area)
- `effectiveness_bonus` -- `effectiveness_score * 0.4` for validated experiences
- `confidence` -- per-experience reliability weight (0.1 to 1.0)

### Feedback Loop

The Experience Bank implements a closed-loop learning cycle:

1. Coaching advice is delivered (experience `usage_count` incremented)
2. Next match is analyzed (`collect_feedback_from_match()`)
3. Feedback is recorded with an EMA-updated `effectiveness_score`
4. Confidence is adjusted (+/- 5% per feedback event, clamped to [0.1, 1.0])
5. Stale unvalidated experiences decay 10% confidence after 90 days

### Knowledge Graph

`KnowledgeGraphManager` provides a SQLite-backed entity-relation graph for
structured tactical reasoning. Entities (e.g., "Mirage/Window", type "Spot")
carry JSON observation lists. Relations are directed edges (e.g.,
`"Mirage/Window" --[CONNECTS_TO]--> "Mirage/Mid"`). BFS subgraph queries
support multi-hop traversal up to depth 5.

---

## Integration

### Consumers

| Consumer | Usage |
|----------|-------|
| `backend/services/coaching_service.py` | Calls `generate_unified_coaching_insight()` in COPER and Hybrid modes |
| `backend/coaching/hybrid_engine.py` | Merges RAG knowledge context with ML predictions |
| `backend/coaching/correction_engine.py` | Retrieves pro examples for correction suggestions |
| `core/session_engine.py` (Teacher daemon) | Triggers experience extraction after demo ingestion |

### Data Sources

| Source | Target |
|--------|--------|
| `tactical_knowledge.json` | `TacticalKnowledge` table via `KnowledgePopulator.populate_from_json()` |
| HLTV `ProPlayerStatCard` | `TacticalKnowledge` table via `ProStatsMiner.mine_all_pro_stats()` |
| Parsed demo tick data + events | `CoachingExperience` table via `ExperienceBank.extract_experiences_from_demo()` |

### Singleton Access

All major components use thread-safe singleton factories:

- `get_experience_bank()` -- double-checked locking with `threading.Lock`
- `get_vector_index_manager()` -- returns `None` if FAISS is unavailable
- `get_knowledge_graph()` -- lazy initialization
- `_get_retriever()` -- cached `KnowledgeRetriever` to avoid reloading SBERT

---

## Development Notes

### Dependencies

| Package | Purpose | Fallback |
|---------|---------|----------|
| `sentence-transformers` | Sentence-BERT embeddings (`all-MiniLM-L6-v2`, 384-dim) | Hash-projection (100-dim) |
| `faiss-cpu` | Sub-linear ANN search (`IndexFlatIP`) | Brute-force cosine similarity |
| `numpy` | Vector operations | Required |
| `sqlmodel` / `sqlalchemy` | Database ORM and atomic updates | Required |

### Embedding Serialization

Experience embeddings use base64-encoded `float32` bytes (AC-32-01), which is
approximately 4x smaller than JSON serialization. The deserializer
(`_deserialize_embedding`) auto-detects legacy JSON format (starts with `[`)
for backward compatibility.

### Key Constants

| Constant | Value | Location |
|----------|-------|----------|
| `MIN_RETRIEVAL_CONFIDENCE` | 0.3 | `experience_bank.py:42` |
| `PRO_EXPERIENCE_CONFIDENCE` | 0.7 | `experience_bank.py:43` |
| `AMATEUR_EXPERIENCE_CONFIDENCE` | 0.5 | `experience_bank.py:44` |
| `OVERFETCH_KNOWLEDGE` | 10 | `vector_index.py:48` |
| `OVERFETCH_EXPERIENCE` | 20 | `vector_index.py:49` |
| `KnowledgeEmbedder.CURRENT_VERSION` | `"v3"` | `rag_knowledge.py:51` |
| `KnowledgeEmbedder.embedding_dim` | 384 (SBERT) / 100 (fallback) | `rag_knowledge.py:53,67` |

### Pro-Stats Mining Archetype Thresholds

| Archetype | Condition |
|-----------|-----------|
| Star Fragger | `impact >= 1.15` and `rating_2_0 >= 1.10` |
| AWP Specialist | `headshot_pct < 0.35` and `impact >= 1.05` |
| Support Anchor | `kast >= 0.72` and `impact < 1.05` |
| Entry Fragger | `opening_duel_win_pct >= 0.52` |
| Versatile | (default) |

### Initialization

Run `init_knowledge_base.py` once to bootstrap the knowledge system:

```bash
python -m Programma_CS2_RENAN.backend.knowledge.init_knowledge_base
```

This loads `tactical_knowledge.json` (15 entries), mines pro stat cards from
`hltv_metadata.db`, and builds both FAISS indexes.
