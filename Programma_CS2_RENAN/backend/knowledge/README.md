> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge — RAG & Experience Bank

RAG (Retrieval-Augmented Generation) knowledge base and COPER Experience Bank for context-aware coaching with semantic retrieval.

## Core Modules

### COPER Experience Bank
- **experience_bank.py** — `ExperienceBank`, `ExperienceContext` — Stores coaching experiences with semantic similarity search, recency/effectiveness weighting, and automatic pruning (max 1000 experiences). Integrates with `backend/storage/db_models.py::CoachingExperience` for persistence.

### RAG Knowledge Retrieval
- **rag_knowledge.py** — `KnowledgeRetriever`, `KnowledgeEmbedder` — Semantic retrieval of tactical knowledge from pro demo patterns using sentence-transformers embeddings. Supports both in-memory and database-backed knowledge stores.

### Professional Pattern Mining
- **pro_demo_miner.py** — `ProDemoMiner` — Extracts tactical patterns, setups, and decision trees from professional player demos. Populates knowledge base with annotated examples for RAG retrieval.

### Supporting Infrastructure
- **graph.py** — Knowledge graph structures for relational knowledge representation
- **init_knowledge_base.py** — Knowledge base initialization and seeding with foundational CS2 tactical concepts

## Integration

Used by `backend/services/coaching_service.py` in COPER and Hybrid modes:
- **COPER Mode**: Experience Bank (semantic) + RAG (tactical) + Pro References (role-based)
- **Hybrid Mode**: RAG knowledge context synthesized with ML predictions

## Retrieval Strategy

Experience Bank uses cosine similarity on embeddings with recency decay (λ=0.1) and effectiveness bonus (0.4×rating). Top-K retrieval (default K=5) with semantic deduplication.

## Dependencies
sentence-transformers (all-MiniLM-L6-v2), SQLModel (persistence), NumPy.
