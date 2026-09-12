# `reports/` — Artefatti generati di audit e valutazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Store di artefatti generati (read-only per convenzione)

## Cosa vive qui

Questa directory raccoglie i report JSON generati automaticamente dagli strumenti di valutazione, audit e diagnostica del progetto. I file qui sono **output** dell'esecuzione di script, non documenti sorgente. La directory viene distribuita vuota (solo i README sono tracciati — `reports/*` e gitignored); i report si accumulano localmente man mano che si eseguono gli strumenti.

```
reports/
├── assets/                               # Grafici PNG MatchVisualizer (nomi fissi, sovrascritti)
├── audit/                                # Output JSON di audit_scanner.py (via --output)
├── coach_answer_eval_<UTC-timestamp>.json  # Esecuzioni di tools/coach_answer_eval.py (groundedness)
├── eval_<UTC-timestamp>.json             # Esecuzioni di tools/eval_harness.py (coaching-eval)
└── hltv_seed_<timestamp>/                # Report esecuzioni seed_hltv_top_n.py (pending_vision.json, ...)
```

## Categorie di file

| Pattern | Sorgente | Scopo |
|---------|----------|-------|
| `eval_*.json` | `tools/eval_harness.py` | Esecuzioni di valutazione coaching (con timestamp) |
| `coach_answer_eval_*.json` | `tools/coach_answer_eval.py` | Esecuzioni eval groundedness risposte LLM (con timestamp) |
| `audit/*.json` | `tools/audit_scanner.py --output reports/audit/<nome>.json` | Audit mirati di sottosistemi |
| `hltv_seed_*/` | `tools/seed_hltv_top_n.py` (consumato da `seed_hltv_apply_vision.py`) | Artefatti di esecuzioni seeding HLTV |
| `assets/*.png` | `Programma_CS2_RENAN/reporting/visualizer.py` (`MatchVisualizer`, dir default relativa a cwd) | Grafici heatmap / analisi round |

(Il benchmark `cs2_coach_bench` scrive le proprie risposte JSONL in `evals/cs2_coach_bench/reports/`, non qui.)

## Convenzioni

- **I nomi dei file dei report JSON sono con timestamp** (`UTC` o locale) cosi i report non si sovrascrivono mai. Eccezione: i PNG in `assets/` usano nomi fissi per mappa/grafico e vengono sovrascritti alla ri-generazione.
- **I report sono immutabili.** Rieseguire uno script produce un nuovo file — mai modificare in place.
- **I report sono solo locali.** `reports/*` e gitignored; conserva quelli vecchi finche la pressione sullo storage non ne giustifica la potatura. Il diff tra report consecutivi rivela regressioni.
- **Niente PII.** I report contengono nomi demo e alias di giocatori ma mai credenziali raw, token Steam o chiavi API HLTV.

## Correlati

- Harness del benchmark: `evals/README.md`
- Operatore Goliath: `goliath.py` alla radice del repo
- Output del validator (stream separato): vedere `tools/headless_validator.py` (scrive su stdout, non qui)

## Pulizia

Quando la directory cresce oltre qualche centinaio di file, pota per eta con:

```bash
find reports -name "eval_*.json" -mtime +90 -delete
```

Aggiusta le soglie alla tua preferenza di retention. Non c'e pulizia automatica.
