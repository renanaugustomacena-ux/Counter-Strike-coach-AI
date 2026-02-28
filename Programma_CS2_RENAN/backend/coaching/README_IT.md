> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching — Pipeline di Coaching Multi-Modalità

Orchestrazione pipeline di coaching con quattro modalità operative: COPER (Experience Bank + RAG + Riferimenti Pro), Hybrid (sintesi ML + RAG), RAG (solo recupero conoscenza) e Neural Network (ML puro).

## Motori Principali

### Orchestrazione Primaria
- **hybrid_engine.py** — `HybridCoachingEngine` — Sintetizza predizioni machine learning con recupero conoscenza RAG per insights di coaching bilanciati

### Correzione e Raffinamento
- **correction_engine.py** — `generate_corrections()` — Genera correzioni tattiche da deviazioni di performance rispetto a baseline pro
- **nn_refinement.py** — `apply_nn_refinement()` — Livello di raffinamento rete neurale per correzioni euristiche con scoring di confidenza

### Analisi Longitudinale
- **longitudinal_engine.py** — `generate_longitudinal_coaching()` — Traccia trend di performance nel tempo con integrazione decay baseline temporale

### Spiegabilità e Integrazione
- **explainability.py** — `ExplanationGenerator` — Converte predizioni ML in spiegazioni leggibili dall'uomo con attribuzione causale
- **pro_bridge.py** — `PlayerCardAssimilator` — Collega dati giocatori professionisti a insights di coaching via comparazione basata su ruolo
- **token_resolver.py** — `PlayerTokenResolver` — Canonicalizzazione nomi giocatori con fuzzy matching e normalizzazione leet-speak

## Modalità Coaching

1. **COPER** (Default) — Recupero semantico Experience Bank + conoscenza RAG + Riferimenti Pro
2. **Hybrid** — Predizioni ML sintetizzate con contesto RAG
3. **RAG** — Recupero puro di conoscenza da pattern demo pro
4. **Neural** — Predizioni ML pure senza augmentazione conoscenza

## Integrazione
Usato da `backend/services/coaching_service.py` con contesto baseline temporale da `backend/processing/baselines/temporal_decay.py`.

## Dipendenze
PyTorch, sentence-transformers (embeddings), SQLModel (persistenza esperienza).
