# `evals/` — Harness di valutazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Quality assurance del coaching
> **Stato:** Attivo — ogni modifica alla pipeline di coaching deve eseguire il bench prima del merge.

## Scopo

Questa directory ospita gli harness di valutazione offline per gli output del coaching del Macena CS2 Analyzer. Le valutazioni vengono eseguite indipendentemente dall'applicazione live e producono report JSON che quantificano regressioni, allucinazioni e drift di copertura tra versioni del motore di coaching.

## Layout

```
evals/
└── cs2_coach_bench/      # Benchmark di coaching da 200 domande
    ├── README.md
    ├── run_eval.py       # Entry point CLI
    ├── questions.jsonl   # Set di domande curate
    ├── rubric.py         # Criteri di scoring
    └── reports/          # Report JSON generati per esecuzione
```

## Eseguire una valutazione

```bash
# Pipeline di coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 200

# Smoke veloce (10 domande)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 10
```

I report vengono scritti in `reports/eval_<timestamp>.json` alla radice del repo e sono pensati per essere confrontati tra esecuzioni successive.

## Quando valutare

Esegui il benchmark completo prima di mergeare qualunque modifica che tocchi:

- `Programma_CS2_RENAN/backend/coaching/`
- `Programma_CS2_RENAN/backend/services/coaching_service.py`
- `Programma_CS2_RENAN/backend/knowledge/` (Experience Bank, RAG)
- `Programma_CS2_RENAN/backend/services/llm_service.py`
- Baseline di giocatori pro o stat card usate dal coach Hybrid

Per il protocollo completo del benchmark, la rubrica di scoring e la forma di un report di esempio vedere `cs2_coach_bench/README.md`.

## Correlati

- Pacchetto coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Strato dei servizi: `Programma_CS2_RENAN/backend/services/README.md`
- Validatore di qualità (gate di regressione): `tools/headless_validator.py`
