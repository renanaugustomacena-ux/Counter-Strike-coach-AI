# `evals/` — Framework di Valutazione e Benchmarking

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Quality assurance del coaching
> **Stato:** Attivo — ogni modifica alla pipeline di coaching deve eseguire il bench prima del merge.

## Scopo

Questa directory ospita il framework automatizzato per misurare e convalidare le prestazioni del coach IA di Counter-Strike. Fornisce un modo sistematico per confrontare la pipeline di coaching e i Large Language Models (LLM) sottostanti con scenari tattici curati da esperti, producendo report quantificabili su regressioni, allucinazioni e drift di copertura.

## Panoramica Tecnica

Il sistema di valutazione opera come un harness di benchmarking a ciclo chiuso. Simula richieste di coaching utilizzando un set standardizzato di domande e confronta le risposte dell'IA con una rubrica rigorosamente definita. Questo processo consente il monitoraggio quantificabile dei miglioramenti del modello, il rilevamento di regressioni e la convalida dell'accuratezza in diversi scenari di mappa e complessità strategiche.

## Componenti Chiave

### CS2 Coach Bench
Situato in **`cs2_coach_bench/`**, questo è il dataset primario per la valutazione:
- **`questions.jsonl`**: Una raccolta di 200 domande tattiche (40 per categoria su 5 categorie) che coprono tattiche di mappa, economia, gioco mid-round, conoscenza dei pro e meccaniche.
- **`rubric.md`**: I criteri di punteggio "gold-standard" — 5 dimensioni con punteggio 0-3 ciascuna (massimo 15 per domanda) — usati per valutare la qualità, l'accuratezza e la rilevanza professionale dei consigli del coach.
- **`run_eval.py`**: Il motore di esecuzione che invia le domande a un backend di modello (`coach` per la pipeline completa oppure `ollama:<model>`) e raccoglie le risposte raw più la latenza.
- **`score_responses.py`**: La CLI di scoring (sotto-comandi `score` / `summary` / `compare`) che applica la rubrica alle risposte raccolte e confronta i modelli.
- **`reports/`**: File di risposta JSONL per ogni esecuzione (gitignored, creati alla prima esecuzione).

## Struttura della Directory

```text
evals/
├── cs2_coach_bench/        # Suite di benchmarking primaria
│   ├── questions.jsonl     # Domande di valutazione standardizzate
│   ├── rubric.md           # Criteri di punteggio definiti da esperti
│   ├── run_eval.py         # Script di esecuzione
│   ├── score_responses.py  # CLI di scoring e confronto
│   └── reports/            # File di risposta per esecuzione (gitignored, generati)
├── README.md               # Versione inglese
├── README_IT.md            # Questa documentazione
└── README_PT.md            # Versione portoghese
```

## Utilizzo

### 1. Eseguire la Valutazione
Esegui il benchmark sulla attuale implementazione del coach (pipeline completa o un modello Ollama grezzo):
```bash
# Pipeline di coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach

# Smoke veloce (10 domande) contro un modello Ollama baseline grezzo
python evals/cs2_coach_bench/run_eval.py --model ollama:gemma4:e2b --limit 10
```
Le risposte vengono salvate in `cs2_coach_bench/reports/<date>_<model>.jsonl` per default (`--output` sovrascrive; `--category` filtra per una singola categoria).

### 2. Punteggio dei Risultati
Assegna il punteggio alle risposte raccolte con la rubrica, poi ottieni il sommario:
```bash
python evals/cs2_coach_bench/score_responses.py score --input evals/cs2_coach_bench/reports/<date>_coach.jsonl
python evals/cs2_coach_bench/score_responses.py summary --input evals/cs2_coach_bench/reports/<date>_coach.scored.jsonl
```

### 3. Analisi delle Metriche
Il sommario fornisce una suddivisione per categoria e per dimensione dei punteggi della rubrica (5 dimensioni, 0-3 ciascuna), e `score_responses.py compare a.scored.jsonl b.scored.jsonl` confronta due modelli. Queste metriche controllano i cambiamenti alla pipeline di coaching e guidano gli sforzi di fine-tuning del modello (il bench stesso gira localmente; l'addestramento e il fine-tuning completi girano sulla macchina Linux di training dedicata, non questa workstation).

## Quando valutare

Esegui il benchmark completo prima di mergeare qualunque modifica che tocchi:
- `Programma_CS2_RENAN/backend/coaching/`
- `Programma_CS2_RENAN/backend/services/coaching_service.py`
- `Programma_CS2_RENAN/backend/knowledge/` (Experience Bank, RAG)
- `Programma_CS2_RENAN/backend/services/llm_service.py`
- Baseline di giocatori pro o stat card usate dal coach Hybrid

## Correlati

- Pacchetto coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Strato dei servizi: `Programma_CS2_RENAN/backend/services/README.md`
- Validatore di qualità (gate di regressione): `tools/headless_validator.py`
- Harness di metriche offline pre-retrain (feature drift, RAG recall@k, kNN purity): `tools/eval_harness.py`
- Eval delle risposte del coach attraverso il motore di dialogo reale con il DB: `tools/coach_answer_eval.py`
