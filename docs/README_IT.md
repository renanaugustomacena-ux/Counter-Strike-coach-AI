# Macena CS2 Analyzer — Indice Documentazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorità:** Regola 8 (Governance della Documentazione)

Questa directory contiene la documentazione completa per il progetto Macena CS2 Analyzer — un'applicazione sofisticata di analisi tattica e coaching AI per Counter-Strike 2. La documentazione è organizzata in guide utente, specifiche tecniche, articoli di ricerca e script di utilità.

## Struttura della Directory

```
docs/
├── USER_GUIDE.md                       # Guida utente completa (Inglese)
├── USER_GUIDE_IT.md                    # Guida utente completa (Italiano)
├── USER_GUIDE_PT.md                    # Guia do usuário completo (Portoghese)
├── Progetto-Renan-Cs2-AI-Coach.md      # Specifica completa dell'architettura
├── AI_ARCHITECTURE_ANALYSIS.md         # Analisi approfondita architettura AI (Inglese)
├── AI_ARCHITECTURE_ANALYSIS_IT.md      # Analisi approfondita architettura AI (Italiano)
├── AI_ARCHITECTURE_ANALYSIS_PT.md      # Análise da arquitetura AI (Portoghese)
├── ERROR_CODES.md                      # Riferimento codici di errore
├── EXIT_CODES.md                       # Riferimento codici di uscita
├── HLTV_SYNC_SERVICE_SPEC.md           # Specifica del servizio di sincronizzazione HLTV
├── INDUSTRY_STANDARDS_AUDIT.md         # Audit di conformità agli standard industriali
├── prompt.md                           # Guida ai prompt per assistenti AI
├── generate_manual_pdf_it.py           # Utilità per generazione manuale PDF
├── logging-and-plan.md                 # Documentazione architettura di logging
├── Studies/                            # 17 articoli di ricerca (approfondimenti)
├── Book-Coach-1A*.md/pdf               # Libro visione parte 1A
├── Book-Coach-1B*.md/pdf               # Libro visione parte 1B
├── Book-Coach-2*.md/pdf                # Libro visione parte 2
├── Book-Coach-3*.md/pdf                # Libro visione parte 3
└── package.json                        # Strumenti docs (markdownlint, ecc.)
```

## Documentazione Utente

### Guide Utente (3 Lingue)

Le guide utente coprono installazione, configurazione, procedure guidate delle funzionalità, risoluzione dei problemi e best practice:

- **[USER_GUIDE.md](USER_GUIDE.md)** — Guida utente completa (Inglese)
- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia do usuário completo (Portoghese)

Ogni guida copre:
1. Installazione e configurazione dell'ambiente
2. Prima ingestione demo (la regola 10/10)
3. Panoramica della schermata di coaching
4. Cronologia partite e analisi delle prestazioni
5. Impostazioni e configurazione
6. Risoluzione dei problemi comuni

## Documentazione Tecnica

### Specifiche dell'Architettura

- **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** — Specifica completa dell'architettura in 12 sezioni (Italiano)
  - Architettura del sistema e diagrammi di flusso dei dati (Mermaid)
  - Modelli di reti neurali (RAP Coach, JEPA, NeuralRoleHead)
  - Sistemi di memoria (ibrido LTC-Hopfield)
  - Pipeline di coaching (modalità COPER)
  - Schema del database e architettura dello storage
  - Pattern di progettazione UI/UX (MVVM)

- **Analisi dell'Architettura AI** — Approfondimento sul sottosistema AI
  - [Inglese](AI_ARCHITECTURE_ANALYSIS.md) | [Italiano](AI_ARCHITECTURE_ANALYSIS_IT.md) | [Portoghese](AI_ARCHITECTURE_ANALYSIS_PT.md)

### Documenti di Riferimento

| Documento | Scopo |
|-----------|-------|
| [ERROR_CODES.md](ERROR_CODES.md) | Tutti i codici di errore con cause e rimedi |
| [EXIT_CODES.md](EXIT_CODES.md) | Codici di uscita per script e daemon |
| [HLTV_SYNC_SERVICE_SPEC.md](HLTV_SYNC_SERVICE_SPEC.md) | Specifica dello scraper di statistiche pro HLTV |
| [INDUSTRY_STANDARDS_AUDIT.md](INDUSTRY_STANDARDS_AUDIT.md) | Audit di conformità agli standard industriali |
| [logging-and-plan.md](logging-and-plan.md) | Architettura di logging strutturato e roadmap |

### Integrazione con Assistenti AI

- **[prompt.md](prompt.md)** — Prompt strutturati e workflow per sviluppo assistito da AI, revisione del codice e manutenzione del sistema

### Libri sulla Visione

I "Coach Books" descrivono la visione completa del prodotto, l'architettura tecnica e la strategia di business:

| Libro | Focus |
|-------|-------|
| Book-Coach-1A | Fondamenta: definizione del problema, analisi di mercato, visione del prodotto |
| Book-Coach-1B | Tecnico: architetture neurali, pipeline di training, modello dati |
| Book-Coach-2 | Implementazione: modalità di coaching, UI/UX, punti di integrazione |
| Book-Coach-3 | Strategia: monetizzazione, licenza SDK, modello open-core |

Disponibili in formato Markdown e PDF, in inglese, italiano e portoghese.

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

### `generate_manual_pdf_it.py`

Converte la guida utente italiana (`USER_GUIDE_IT.md`) in un manuale PDF formattato utilizzando la conversione markdown-to-PDF. Eseguire dalla root del progetto:

```bash
python docs/generate_manual_pdf_it.py
```

### `package.json`

Configurazione degli strumenti per i documenti, incluso markdownlint e altri controlli di qualità del Markdown. Installare con:

```bash
cd docs && npm install
```

## Per Iniziare

1. Inizia con **[USER_GUIDE.md](USER_GUIDE.md)** per installazione e configurazione
2. Consulta **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** per l'architettura del sistema
3. Esplora **[Studies/](Studies/)** per una comprensione tecnica approfondita
4. Consulta **[ERROR_CODES.md](ERROR_CODES.md)** per la risoluzione dei problemi

## Note di Sviluppo

- Tutta la documentazione è in formato Markdown per la massima portabilità
- I termini tecnici, i nomi delle classi e i riferimenti al codice rimangono in inglese in tutte le traduzioni
- I diagrammi Mermaid sono utilizzati per la visualizzazione dell'architettura e del flusso dei dati
- La generazione dei PDF richiede i pacchetti Python `markdown` e `weasyprint`
- Il file `CLAUDE.md` nella root del progetto contiene i principi ingegneristici e le linee guida di sviluppo
