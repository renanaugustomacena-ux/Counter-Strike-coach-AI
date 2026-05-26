# `evals/` — Framework di Valutazione e Benchmarking

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Quality assurance del coaching
> **Stato:** Attivo — ogni modifica alla pipeline di coaching deve eseguire il bench prima del merge.

## Scopo

Questa directory ospita il framework automatizzato per misurare e convalidare le prestazioni del coach IA di Counter-Strike. Fornisce un modo sistematico per confrontare i Large Language Models (LLM) e i Vision-Language Models (VLM) con scenari tattici curati da esperti, producendo report quantificabili su regressioni, allucinazioni e drift di copertura.

## Panoramica Tecnica

Il sistema di valutazione opera come un harness di benchmarking a ciclo chiuso. Simula richieste di coaching utilizzando un set standardizzato di domande e confronta le risposte dell'IA con una rubrica rigorosamente definita. Questo processo consente il monitoraggio quantificabile dei miglioramenti del modello, il rilevamento di regressioni e la convalida dell'accuratezza in diversi scenari di mappa e complessità strategiche.

## Componenti Chiave

### CS2 Coach Bench
Situato in **`cs2_coach_bench/`**, questo è il dataset primario per la valutazione:
- **`questions.jsonl`**: Una raccolta di oltre 200 domande tattiche diverse che coprono l'uso delle utility, il posizionamento e l'analisi dello stato del round.
- **`rubric.py` / `rubric.md`**: I criteri di punteggio "gold-standard" utilizzati per valutare la qualità, l'accuratezza e la rilevanza professionale dei consigli del coach.
- **`run_eval.py`**: Il motore di esecuzione che invia le domande all'API del coach e raccoglie le risposte raw del modello.
- **`score_responses.py`**: Lo script di convalida che confronta gli output del modello con la rubrica e genera le metriche finali di performance (es. Accuratezza, F1-score, Solidità Tattica).
- **`reports/`**: Report JSON generati per ogni esecuzione per il tracciamento storico.

## Struttura della Directory

```text
evals/
├── cs2_coach_bench/        # Suite di benchmarking primaria
│   ├── questions.jsonl     # Domande di valutazione standardizzate
│   ├── rubric.md           # Criteri di punteggio definiti da esperti
│   ├── run_eval.py         # Script di esecuzione
│   ├── score_responses.py  # Script di punteggio e convalida
│   └── reports/            # Report per match
├── README.md               # Versione inglese
├── README_IT.md            # Questa documentazione
└── README_PT.md            # Versione portoghese
```

## Utilizzo

### 1. Eseguire la Valutazione
Esegui il benchmark sulla attuale implementazione del coach (es. pipeline completa o modello specifico):
```bash
# Pipeline di coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 200

# Smoke veloce (10 domande) contro un modello specifico
python evals/cs2_coach_bench/run_eval.py --model gpt-4o --limit 10 --output results.json
```

### 2. Punteggio dei Risultati
Genera un report di performance valutando le risposte raccolte:
```bash
python evals/cs2_coach_bench/score_responses.py --input results.json --rubric evals/cs2_coach_bench/rubric.md
```

### 3. Analisi delle Metriche
Il sistema fornirà una suddivisione dettagliata delle prestazioni per categoria (es. "Conoscenza Smoke: 85%", "Consigli Economici: 92%"). Queste metriche vengono utilizzate per approvare i deployment in produzione e guidare gli sforzi di fine-tuning del modelo.

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
