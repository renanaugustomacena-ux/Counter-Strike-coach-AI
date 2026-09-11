# Macena CS2 Analyzer — Indice della Documentazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Riferimenti Principali (root del progetto)

| Documento | Scopo |
|-----------|-------|
| **[REFERENCE.md](../REFERENCE.md)** | Architettura, contratto dimensionale, costanti, skill, test, configurazioni |
| **[TASKS.md](../TASKS.md)** | Backlog, errori, stato di esecuzione |
| **[CHANGELOG.md](../CHANGELOG.md)** | Storico delle modifiche |

## Struttura della Directory

```
docs/
├── QUICKSTART.md                   # Guida rapida di 5 minuti
├── README.md / _IT.md / _PT.md     # Questo indice (3 lingue)
│
├── OPEN_ISSUES.md                  # Problemi aperti consolidati (sweep documentale 2026-08-21)
├── RE_INGESTION_GUIDE.md           # Ops: pipeline completa di re-ingestione e training
├── concurrency_policy.md           # Ops: politica di lock DB per migrazioni a lunga esecuzione
├── rollback_procedure.md           # Ops: rollback DB alla baseline 2026-05-03
├── strategy_taxonomy.md            # Tassonomia coachingexperience.strategy_label
│
├── DIAGNOSIS_2026-05.md            # Diagnosi storica (stato superato da docs/audit)
├── SESSION_HANDOFF.md              # Convenzioni operative (stato storico rimosso)
├── jepa_training_tuning_observations_2026-05-06.md   # Scala retrain R8 + record probe B5
├── rap_training_known_issue_2026-05-05.md            # Risolto: motivazione per la patch LTC ncps live
├── restoration_baseline_2026-05-03.json              # Conteggi righe baseline per rollback
├── d3_rederive_report_2026-07-17.json                # Report ri-derivazione D3 tick-rate (shards)
│
├── audit/                          # Archivio Audit Nuke-Proof (chiuso 2026-08-14)
│   ├── FINAL_REPORT.md             # Chiusura campagna (inizia qui)
│   ├── FINDINGS.md                 # Registro 44 findings (13 differiti → OPEN_ISSUES.md)
│   └── ...                         # WAVES, CONTRACTS, dossier, sweep, ledger
│
├── books/                          # Libri di visione (visione e architettura del progetto)
│   ├── Book-Coach-1A .md/.pdf      # Nucleo neurale: JEPA, VL-JEPA, AdvancedCoachNN
│   ├── Book-Coach-1B .md/.pdf      # RAP Coach, sorgenti dati (demo, HLTV, Steam)
│   ├── Book-Coach-2  .md/.pdf      # Servizi, motori di analisi, COPER, database
│   ├── Book-Coach-3  .md/.pdf      # Logica del programma, UI Qt, ingestione, tools, build
│   │                               # (ciascuno con varianti -en / -pt)
│   ├── analogy-book .md/.pdf       # Companion per analogie (con varianti -en / -pt)
│   ├── codebase-understanding/     # Walkthrough codebase in 9 capitoli (01-09)
│   ├── REFACTOR_PLAN.md
│   └── TRANSLATION_GLOSSARY.md
│
├── doctrine/                       # Dottrina architetturale AI (derivata dal codice)
│   ├── DOCTRINE.md                 # Invarianti, contratti e motivazioni di design
│   └── notes/                      # Note di lettura per cluster + READING-MANIFEST.md
│
├── guides/                         # Documentazione rivolta all'utente
│   ├── USER_GUIDE.md               # Guida utente completa (Inglese)
│   ├── USER_GUIDE_IT.md            # Guida utente (Italiano)
│   ├── USER_GUIDE_PT.md            # Guia do usuario (Portugues)
│   └── PROJETO_EXPLICADO_PT.md     # Panoramica progetto in Portoghese (per sviluppatori da altri stack)
│
├── research/                       # Catalogo biblioteca di ricerca + design research
│   ├── INDEX.md                    # Indice bibliografico; i PDF stessi sono
│   │                               # git-ignorati e non presenti in un checkout fresco
│   └── cs_platforms.md / github_gems.md / global_startups.md   # Dossier redesign UI/UX
│
├── superpowers/                    # Piani di implementazione e specifiche di design (workflow skill)
│   ├── plans/
│   └── specs/
│
├── ux-audit/                       # Audit visivo UX + render schermo
│   ├── UX_VISUAL_AUDIT.md
│   ├── renders/                    # Screenshot CS16 / CS2 / CSGO
│   └── renders-atlas/              # Screenshot CS16 / CS2 / CSGO (pass design-atlas)
│
└── tooling/                        # Utility per la generazione di PDF
    ├── generate_zh_pdfs.py         # Generatore Mermaid → SVG + PDF tema scuro
    ├── md2pdf.mjs                  # Markdown -> PDF (Node.js)
    └── package.json / package-lock.json
```

## Ordine di Lettura

1. **[../REFERENCE.md](../REFERENCE.md)** — Architettura, invarianti, riferimento tecnico
2. **[doctrine/DOCTRINE.md](doctrine/DOCTRINE.md)** — Dottrina architetturale AI (invarianti e contratti derivati dal codice)
3. **[QUICKSTART.md](QUICKSTART.md)** — Fai partire l'app in 5 minuti
4. **[guides/USER_GUIDE_IT.md](guides/USER_GUIDE_IT.md)** — Walkthrough completo per l'utente
5. **[books/](books/)** — Libri di visione (1A → 1B → 2 → 3) per la visione completa del prodotto
6. **[research/INDEX.md](research/INDEX.md)** — Bibliografia dei paper di ricerca

## Riferimento Rapido

| Necessita | Dove andare |
|-----------|-------------|
| Cos'e questo progetto? | `../README.md` |
| Architettura e invarianti | `../REFERENCE.md` |
| Backlog e piano di esecuzione | `../TASKS.md` |
| Vettore feature (25-dim) | `../REFERENCE.md` §2 |
| Architettura storage / schema | `../REFERENCE.md` §5 |
| Pipeline re-ingestione / training | `RE_INGESTION_GUIDE.md` |
| Troubleshooting | `guides/USER_GUIDE_IT.md` — sezione Troubleshooting |
| Aiuto in-app | `../Programma_CS2_RENAN/data/docs/troubleshooting.md` |

## Note

- I file con date nel nome (`*_2026-*`) sono snapshot storici da precedenti run di
  restoration/training — descrivono lo stato a quella data, non lo stato attuale.
- I Libri di Visione (books/) descrivono la visione del prodotto e sono stati riallineati al codebase
  il 2026-08-17. La Dottrina (doctrine/) e l'autorita derivata dal codice per architettura e
  invarianti; quando i due discordano, la dottrina riflette l'implementazione attuale.
- Tutta la documentazione e in formato Markdown. I PDF sono generati con i tool in `tooling/`.
