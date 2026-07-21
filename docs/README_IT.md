# Macena CS2 Analyzer — Indice della Documentazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Riferimenti Principali (root del progetto)

| Documento | Scopo |
|-----------|-------|
| **[REFERENCE.md](../REFERENCE.md)** | Architettura, contratto dimensionale, costanti, skill, test, configurazioni |
| **[AUDIT.md](../AUDIT.md)** | Findings, diagnostica, stato della build |
| **[TASKS.md](../TASKS.md)** | Backlog, errori, stato di esecuzione |

## Struttura della Directory

```
docs/
├── QUICKSTART.md                   # Guida rapida di 5 minuti
├── README.md / _IT.md / _PT.md    # Questo indice (3 lingue)
│
├── books/                          # Libri di visione (visione e architettura del progetto)
│   ├── Book-Coach-1A.md / .pdf     # Nucleo neurale: JEPA, VL-JEPA, AdvancedCoachNN
│   ├── Book-Coach-1B.md / .pdf     # RAP Coach, sorgenti dati (demo, HLTV, Steam)
│   ├── Book-Coach-2.md / .pdf      # Servizi, motori di analisi, COPER, database
│   └── Book-Coach-3.md / .pdf      # Logica del programma, UI Qt, ingestione, tools, build
│
├── guides/                         # Documentazione rivolta all'utente
│   ├── USER_GUIDE.md               # Guida utente completa (Inglese)
│   ├── USER_GUIDE_IT.md            # Guida utente (Italiano)
│   └── USER_GUIDE_PT.md            # Guia do usuario (Portugues)
│
├── Studies/                        # 17 papers di ricerca (fondamenti teorici)
│   ├── README.md / _IT.md / _PT.md # Indice degli studi
│   ├── Fondamenti-Epistemici.md    # Epistemologia e verita
│   ├── Architettura-JEPA.md        # Architettura JEPA
│   └── ... (15 altri)              # Vedi Studies/README.md
│
├── archive/                        # Documenti superati (conservati per riferimento)
│   ├── AI_ARCHITECTURE_ANALYSIS.md # Sostituito da ENGINEERING_HANDOFF
│   ├── PROJECT_SURGERY_PLAN.md     # Sostituito da ENGINEERING_HANDOFF
│   ├── PRODUCT_VIABILITY_ASSESSMENT.md
│   ├── INDUSTRY_STANDARDS_AUDIT.md
│   ├── logging-and-plan.md
│   ├── MISSION_RULES.md
│   ├── cybersecurity.md
│   ├── ERROR_CODES.md
│   ├── EXIT_CODES.md
│   └── prompt.md
│
└── tooling/                        # Utility per la generazione di PDF
    ├── generate_zh_pdfs.py         # Generatore di PDF in cinese
    ├── md2pdf.mjs                  # Markdown -> PDF (Node.js)
    └── package.json                # Dipendenze npm
```

## Ordine di Lettura

1. **[../REFERENCE.md](../REFERENCE.md)** — Architettura, invarianti, riferimento tecnico
2. **[QUICKSTART.md](QUICKSTART.md)** — Fai partire l'app in 5 minuti
3. **[guides/USER_GUIDE_IT.md](guides/USER_GUIDE_IT.md)** — Walkthrough completo per l'utente
4. **[books/](books/)** — Libri di visione (1A -> 1B -> 2 -> 3) per la visione completa del prodotto
5. **[Studies/](Studies/)** — Papers di ricerca approfonditi sui fondamenti teorici

## Riferimento Rapido

| Necessita | Dove andare |
|-----------|-------------|
| Cos'e questo progetto? | `../README.md` |
| Architettura e invarianti | `../REFERENCE.md` |
| Findings e diagnostica attuali | `../AUDIT.md` |
| Backlog e piano di esecuzione | `../TASKS.md` |
| Vettore feature (25-dim) | `../REFERENCE.md` §3 |
| Schema database | `../REFERENCE.md` §4 |
| Troubleshooting | `guides/USER_GUIDE_IT.md` — sezione Troubleshooting |
| Aiuto rivolto all'utente | `data/docs/troubleshooting.md` |

## Note

- La directory `archive/` contiene documenti superati preservati per riferimento storico.
- I Libri di Visione (books/) descrivono la visione aspirazionale del prodotto. Saranno aggiornati per allinearsi al codebase quando il programma sara stabile.
- Tutta la documentazione e in formato Markdown. I PDF sono generati con i tool in `tooling/`.
- Il file `CLAUDE.md` nella root del progetto contiene le direttive ingegneristiche e le regole di sviluppo.
