# Macena CS2 Analyzer — Indice Documentazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorità:** Regola 8 (Governance della Documentazione)

Questa directory contiene la documentazione completa per il progetto Macena CS2 Analyzer — un'applicazione sofisticata di analisi tattica e coaching AI per Counter-Strike 2. La documentazione è organizzata in guide utente, specifiche tecniche, articoli di ricerca, libri sulla visione e script di utilità.

## Struttura della Directory

```
docs/
├── USER_GUIDE.md                       # Guida utente completa (Inglese)
├── USER_GUIDE_IT.md                    # Guida utente completa (Italiano)
├── USER_GUIDE_PT.md                    # Guia do usuário completo (Portoghese)
├── QUICKSTART.md                       # Guida rapida all'avvio
├── AI_ARCHITECTURE_ANALYSIS.md         # Analisi approfondita architettura AI (Inglese)
├── AI_ARCHITECTURE_ANALYSIS_IT.md      # Analisi approfondita architettura AI (Italiano)
├── AI_ARCHITECTURE_ANALYSIS_PT.md      # Análise da arquitetura AI (Portoghese)
├── ERROR_CODES.md                      # Riferimento codici di errore
├── EXIT_CODES.md                       # Riferimento codici di uscita
├── INDUSTRY_STANDARDS_AUDIT.md         # Audit di conformità agli standard industriali
├── MISSION_RULES.md                    # Missione del progetto e regole
├── PRODUCT_VIABILITY_ASSESSMENT.md     # Analisi di fattibilità del prodotto
├── PROJECT_SURGERY_PLAN.md             # Piano di chirurgia dell'architettura
├── cybersecurity.md                    # Valutazione di cybersicurezza
├── prompt.md                           # Guida ai prompt per assistenti AI
├── logging-and-plan.md                 # Documentazione architettura di logging
├── Book-Coach-1A.md/pdf               # Libro visione parte 1A — Nucleo neurale
├── Book-Coach-1B.md/pdf               # Libro visione parte 1B — RAP Coach e sorgenti dati
├── Book-Coach-2.md/pdf                # Libro visione parte 2 — Servizi e infrastruttura
├── Book-Coach-3.md/pdf                # Libro visione parte 3 — Logica del programma e UI
├── Studies/                            # 17 articoli di ricerca (approfondimenti)
├── generate_zh_pdfs.py                 # Utilità per generazione PDF in cinese
├── md2pdf.mjs                          # Convertitore da Markdown a PDF (Node.js)
└── package.json                        # Strumenti docs (markdownlint, ecc.)
```

## Documentazione Utente

### Guide Utente (3 Lingue)

Le guide utente coprono installazione, configurazione, procedure guidate delle funzionalità, risoluzione dei problemi e best practice:

- **[USER_GUIDE.md](USER_GUIDE.md)** — Guida utente completa (Inglese)
- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia do usuário completo (Portoghese)
- **[QUICKSTART.md](QUICKSTART.md)** — Guida rapida per essere operativi velocemente

Ogni guida copre:
1. Installazione e configurazione dell'ambiente
2. Prima ingestione demo (la regola 10/10)
3. Panoramica della schermata di coaching
4. Cronologia partite e analisi delle prestazioni
5. Impostazioni e configurazione
6. Risoluzione dei problemi comuni

## Documentazione Tecnica

### Specifiche dell'Architettura

- **Analisi dell'Architettura AI** — Approfondimento sul sottosistema AI
  - [Inglese](AI_ARCHITECTURE_ANALYSIS.md) | [Italiano](AI_ARCHITECTURE_ANALYSIS_IT.md) | [Portoghese](AI_ARCHITECTURE_ANALYSIS_PT.md)

### Documenti di Riferimento

| Documento | Scopo |
|-----------|-------|
| [ERROR_CODES.md](ERROR_CODES.md) | Tutti i codici di errore con cause e rimedi |
| [EXIT_CODES.md](EXIT_CODES.md) | Codici di uscita per script e daemon |
| [INDUSTRY_STANDARDS_AUDIT.md](INDUSTRY_STANDARDS_AUDIT.md) | Audit di conformità agli standard industriali |
| [MISSION_RULES.md](MISSION_RULES.md) | Dichiarazione di missione del progetto e regole di sviluppo |
| [PRODUCT_VIABILITY_ASSESSMENT.md](PRODUCT_VIABILITY_ASSESSMENT.md) | Analisi di fattibilità e mercato del prodotto |
| [PROJECT_SURGERY_PLAN.md](PROJECT_SURGERY_PLAN.md) | Piano di chirurgia e refactoring dell'architettura |
| [cybersecurity.md](cybersecurity.md) | Valutazione di cybersicurezza e modello delle minacce |
| [logging-and-plan.md](logging-and-plan.md) | Architettura di logging strutturato e roadmap |

### Integrazione con Assistenti AI

- **[prompt.md](prompt.md)** — Prompt strutturati e workflow per sviluppo assistito da AI, revisione del codice e manutenzione del sistema

### Libri sulla Visione

I "Coach Books" descrivono la visione completa del prodotto, l'architettura tecnica e la strategia di business:

| Libro | Focus | Dimensione |
|-------|-------|------------|
| [Book-Coach-1A](Book-Coach-1A.md) | Nucleo neurale: JEPA, VL-JEPA, AdvancedCoachNN, MaturityObservatory | 1.315 righe |
| [Book-Coach-1B](Book-Coach-1B.md) | RAP Coach (7 componenti), sorgenti dati (demo, HLTV, Steam, FACEIT, FAISS) | 1.176 righe |
| [Book-Coach-2](Book-Coach-2.md) | Servizi, 10 motori di analisi, knowledge/RAG/COPER, database, pipeline di training | 2.492 righe |
| [Book-Coach-3](Book-Coach-3.md) | Logica completa del programma, Qt UI (13 schermate), ingestione, strumenti, test, build | 3.143 righe |

Disponibili in formato Markdown e PDF.

## Ricerca e Approfondimenti

### Directory Studies

La directory **[Studies/](Studies/)** contiene 17 articoli di ricerca tecnica approfondita che coprono le fondamenta teoriche e i dettagli implementativi:

- **Epistemologia e Teoria dei Giochi:** Reti bayesiane di belief, gioco avversariale razionale, stima della probabilità di morte
- **Architettura di Coaching:** Design del RAP Coach, modalità COPER (Context + Observation + Pro Reference + Experience + Reasoning)
- **Intelligenza Spaziale:** Gestione del Z-cutoff, mappe multi-livello (Nuke, Vertigo), analisi dell'engagement range
- **Sistemi di Momentum:** Modellazione del momentum temporale, rilevamento dei momenti critici, decadimento della baseline
- **Architetture Neurali:** Allineamento vision-language VL-JEPA, integrazione memoria Hopfield, dinamiche LTC
- **Feature Engineering:** Vettore tattico unificato a 25 dimensioni, quantizzazione euristica
- **Pipeline di Analisi:** Statistiche a livello di round, calcolo del rating HLTV 2.0, analisi dell'uso delle utility

## Utilità

### `generate_zh_pdfs.py`

Genera versioni PDF in cinese della documentazione. Eseguire dalla root del progetto:

```bash
python docs/generate_zh_pdfs.py
```

### `md2pdf.mjs`

Convertitore da Markdown a PDF basato su Node.js. Richiede le dipendenze npm:

```bash
cd docs && npm install && node md2pdf.mjs
```

### `package.json`

Configurazione degli strumenti per i documenti, incluso markdownlint e generazione PDF.

## Per Iniziare

1. Inizia con **[QUICKSTART.md](QUICKSTART.md)** o **[USER_GUIDE.md](USER_GUIDE.md)** per installazione e configurazione
2. Leggi i **Libri sulla Visione** (1A → 1B → 2 → 3) per l'architettura completa del sistema
3. Esplora **[Studies/](Studies/)** per una comprensione tecnica approfondita
4. Consulta **[ERROR_CODES.md](ERROR_CODES.md)** per la risoluzione dei problemi

## Note di Sviluppo

- Tutta la documentazione è in formato Markdown per la massima portabilità
- I termini tecnici, i nomi delle classi e i riferimenti al codice rimangono in inglese in tutte le traduzioni
- La generazione dei PDF richiede la toolchain Node.js o i pacchetti Python
- Il file `CLAUDE.md` nella root del progetto contiene i principi ingegneristici e le linee guida di sviluppo
