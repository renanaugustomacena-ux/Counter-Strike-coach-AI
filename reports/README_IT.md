# `reports/` — Artefatti generati di audit e valutazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Store di artefatti generati (read-only per convenzione)

## Cosa vive qui

Questa directory raccoglie i report JSON generati automaticamente dagli strumenti di valutazione, audit e diagnostica del progetto. I file qui sono **output** dell'esecuzione di script, non documenti sorgente — vengono mantenuti sotto controllo di versione come evidenza storica.

```
reports/
├── audit/                                # Output JSON degli audit Goliath
├── eval_<UTC-timestamp>.json             # Esecuzioni del benchmark cs2_coach_bench
└── goliath_hospital_<timestamp>.json     # Esecuzioni Goliath in modalità hospital (recovery DB)
```

## Categorie di file

| Pattern | Sorgente | Scopo |
|---------|----------|-------|
| `eval_*.json` | `evals/cs2_coach_bench/run_eval.py` | Scoring del benchmark di coaching |
| `goliath_hospital_*.json` | `goliath.py audit --hospital` | Scan di integrità del database |
| `audit/*.json` | `goliath.py audit` | Audit mirati di moduli |

## Convenzioni

- **I nomi dei file sono timestampati** (`UTC` o locale) così i report non si sovrascrivono mai.
- **I report sono immutabili.** Rieseguire uno script produce un nuovo file — mai modificare in place.
- **I vecchi report sono conservati** finché la pressione sullo storage non ne giustifica la potatura. Il diff tra report consecutivi rivela regressioni.
- **Niente PII.** I report contengono nomi demo e alias di giocatori ma mai credenziali raw, token Steam o chiavi API HLTV.

## Correlati

- Harness del benchmark: `evals/README.md`
- Operatore Goliath: `goliath.py` alla radice del repo
- Output del validator (stream separato): vedere `tools/headless_validator.py` (scrive su stdout, non qui)

## Pulizia

Quando la directory cresce oltre qualche centinaio di file, pota per mese con:

```bash
find reports -name "eval_*.json" -mtime +90 -delete
find reports -name "goliath_hospital_*.json" -mtime +60 -delete
```

Aggiusta le soglie alla tua preferenza di retention. Non c'è pulizia automatica.
