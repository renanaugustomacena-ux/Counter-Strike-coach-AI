# CS2 Coach Bench

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Benchmark di valutazione da 200 domande per la qualità del coaching AI di CS2.

## Quick Start

```bash
# Esegui contro la pipeline di coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 10

# Esegui contro Ollama puro (senza RAG, isola la conoscenza del modello)
python evals/cs2_coach_bench/run_eval.py --model ollama:llama3.1:8b --limit 10

# Assegna manualmente i punteggi alle risposte
python evals/cs2_coach_bench/score_responses.py score --input reports/2026-04-12_coach.jsonl

# Stampa il riepilogo dello scoring
python evals/cs2_coach_bench/score_responses.py summary --input reports/2026-04-12_coach.scored.jsonl

# Confronta due modelli
python evals/cs2_coach_bench/score_responses.py compare reports/model_a.scored.jsonl reports/model_b.scored.jsonl
```

## Struttura

- `questions.jsonl` — 200 domande (40 per categoria)
- `rubric.md` — rubrica di scoring a 5 dimensioni (0-3 ciascuna, max 15/domanda)
- `run_eval.py` — Esegue le domande attraverso un modello, salva risposte + latenza
- `score_responses.py` — CLI di scoring manuale + tool di confronto
- `reports/` — File di risposte generati (gitignored)

## Categorie

| Categoria | Numero | Cosa testa |
|----------|-------|-------|
| map_tactics | 40 | Site execute, default, retake, rotazioni |
| economy | 40 | Decisioni force/save, bonus su perdita, disciplina eco |
| mid_round | 40 | Lettura del round, rotazioni, vantaggio numerico, timing |
| pro_knowledge | 40 | Confronti tra giocatori, strategie di team, analisi dei ruoli |
| mechanics | 40 | Sub-tick, movimento, timing delle utility, spray |

## Dimensioni di scoring

Vedere `rubric.md` per le descrizioni complete. Ogni dimensione 0-3:

1. **Correttezza tattica** — il consiglio è giusto?
2. **Aderenza a CS2** — CS2, non CSGO?
3. **Specificità** — generico o concreto?
4. **Grounding sui pro** — fa riferimento a pro reali?
5. **Azionabilità** — ti dice cosa fare?

## Criterio di ship (da COACH_QUALITY_ROADMAP)

`cs2coach` deve battere Llama 3.1 8B vanilla di >25% sul punteggio totale E battere GPT-4 di >5% sulle dimensioni di aderenza a CS2 e di grounding sui pro.
