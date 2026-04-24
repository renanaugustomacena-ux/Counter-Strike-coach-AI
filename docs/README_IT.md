# Macena CS2 Analyzer — Indice della Documentazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

## Documento Principale

**[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Il riferimento tecnico unificato per l'intero progetto. Contiene: architettura del sistema, audit dello stato attuale, findings aperti, piano di esecuzione (interventi a fasi), roadmap del prodotto, guida al troubleshooting e tutte le appendici (codici errore, variabili d'ambiente, spec del vettore feature, schema database). **Inizia da qui.**

## Struttura della Directory

```
docs/
├── ENGINEERING_HANDOFF.md          # Riferimento tecnico unificato (inizia qui)
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

1. **[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Riferimento tecnico, piano di esecuzione, stato attuale
2. **[QUICKSTART.md](QUICKSTART.md)** — Fai partire l'app in 5 minuti
3. **[guides/USER_GUIDE_IT.md](guides/USER_GUIDE_IT.md)** — Walkthrough completo per l'utente
4. **[books/](books/)** — Libri di visione (1A -> 1B -> 2 -> 3) per la visione completa del prodotto
5. **[Studies/](Studies/)** — Papers di ricerca approfonditi sui fondamenti teorici

## Riferimento Rapido

| Necessita | Dove andare |
|-----------|-------------|
| Cos'e questo progetto? | ENGINEERING_HANDOFF, Sezione 1 |
| Cosa funziona oggi? | ENGINEERING_HANDOFF, Parte II |
| Cosa deve essere corretto? | ENGINEERING_HANDOFF, Parte III (Open Findings Registry) |
| Come correggerlo (passi ordinati)? | ENGINEERING_HANDOFF, Parte IV (Execution Plan) |
| Codici errore | ENGINEERING_HANDOFF, Appendice A |
| Variabili d'ambiente | ENGINEERING_HANDOFF, Appendice C |
| Vettore feature (25-dim) | ENGINEERING_HANDOFF, Appendice E |
| Schema database | ENGINEERING_HANDOFF, Appendice F |
| Troubleshooting | ENGINEERING_HANDOFF, Appendice G |
| Roadmap prodotto | ENGINEERING_HANDOFF, Parte V |

## Note

- La directory `archive/` contiene i documenti originali individuali che sono stati consolidati in ENGINEERING_HANDOFF.md. Sono preservati per riferimento storico.
- I Libri di Visione (books/) descrivono la visione aspirazionale del prodotto. Saranno aggiornati per allinearsi al codebase quando il programma sara stabile.
- Tutta la documentazione e in formato Markdown. I PDF sono generati con i tool in `tooling/`.
- Il file `CLAUDE.md` nella root del progetto contiene le direttive ingegneristiche e le regole di sviluppo.
