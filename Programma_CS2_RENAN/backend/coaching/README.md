> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching — Multi-Mode Coaching Pipeline

Coaching pipeline orchestration with four operational modes: COPER (Experience Bank + RAG + Pro References), Hybrid (ML + RAG synthesis), RAG (knowledge retrieval only), and Neural Network (pure ML).

## Core Engines

### Primary Orchestration
- **hybrid_engine.py** — `HybridCoachingEngine` — Synthesizes machine learning predictions with RAG knowledge retrieval for balanced coaching insights

### Correction & Refinement
- **correction_engine.py** — `generate_corrections()` — Generates tactical corrections from performance deviations against pro baselines
- **nn_refinement.py** — `apply_nn_refinement()` — Neural network refinement layer for heuristic corrections with confidence scoring

### Longitudinal Analysis
- **longitudinal_engine.py** — `generate_longitudinal_coaching()` — Tracks performance trends over time with temporal baseline decay integration

### Explainability & Integration
- **explainability.py** — `ExplanationGenerator` — Converts ML predictions into human-readable explanations with causal attribution
- **pro_bridge.py** — `PlayerCardAssimilator` — Links professional player data to coaching insights via role-based comparison
- **token_resolver.py** — `PlayerTokenResolver` — Player name canonicalization with fuzzy matching and leet-speak normalization

## Coaching Modes

1. **COPER** (Default) — Experience Bank semantic retrieval + RAG knowledge + Pro References
2. **Hybrid** — ML predictions synthesized with RAG context
3. **RAG** — Pure knowledge retrieval from pro demo patterns
4. **Neural** — Pure ML predictions without knowledge augmentation

## Integration
Used by `backend/services/coaching_service.py` with temporal baseline context from `backend/processing/baselines/temporal_decay.py`.

## Dependencies
PyTorch, sentence-transformers (embeddings), SQLModel (experience persistence).
