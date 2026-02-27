> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge — RAG e Experience Bank

Base di conoscenza RAG (Retrieval-Augmented Generation) e COPER Experience Bank per coaching context-aware con recupero semantico.

## Moduli Principali

### COPER Experience Bank
- **experience_bank.py** — `ExperienceBank`, `ExperienceContext` — Memorizza esperienze di coaching con ricerca similarità semantica, ponderazione recency/effectiveness e pruning automatico (max 1000 esperienze). Integrato con `backend/storage/db_models.py::CoachingExperience` per persistenza.

### Recupero Conoscenza RAG
- **rag_knowledge.py** — `KnowledgeRetriever`, `KnowledgeEmbedder` — Recupero semantico di conoscenza tattica da pattern demo pro usando embeddings sentence-transformers. Supporta store conoscenza in-memory e database-backed.

### Mining Pattern Professionisti
- **pro_demo_miner.py** — `ProDemoMiner` — Estrae pattern tattici, setup e alberi decisionali da demo giocatori professionisti. Popola base conoscenza con esempi annotati per recupero RAG.

### Infrastruttura di Supporto
- **graph.py** — Strutture knowledge graph per rappresentazione conoscenza relazionale
- **init_knowledge_base.py** — Inizializzazione base conoscenza e seeding con concetti tattici CS2 fondamentali

## Integrazione

Usato da `backend/services/coaching_service.py` in modalità COPER e Hybrid:
- **Modalità COPER**: Experience Bank (semantico) + RAG (tattico) + Riferimenti Pro (basati su ruolo)
- **Modalità Hybrid**: Contesto conoscenza RAG sintetizzato con predizioni ML

## Strategia Recupero

Experience Bank usa similarità coseno su embeddings con decay recency (λ=0.1) e bonus effectiveness (0.4×rating). Recupero Top-K (default K=5) con deduplicazione semantica.

## Dipendenze
sentence-transformers (all-MiniLM-L6-v2), SQLModel (persistenza), NumPy.
