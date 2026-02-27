# Macena CS2 Analyzer - Indice Documentazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Questa directory contiene la documentazione completa per il progetto Macena CS2 Analyzer, un'applicazione sofisticata di analisi tattica e coaching AI per Counter-Strike 2.

## Documentazione Utente

### Guide Utente
- **[USER_GUIDE.md](USER_GUIDE.md)** — Guida utente completa (Inglese)
  Installazione, configurazione, procedure guidate delle funzionalità, risoluzione dei problemi e best practice

- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
  Traduzione italiana della guida utente completa

- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia do usuário completo (Português)
  Traduzione portoghese brasiliano della guida utente completa

## Documentazione Tecnica

### Architettura e Progettazione
- **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** — Specifica completa dell'architettura del progetto (Italiano)
  Specifica tecnica completa in 12 sezioni con diagrammi Mermaid che copre:
  - Architettura del sistema e flusso dei dati
  - Modelli di reti neurali (RAP Coach, JEPA, NeuralRoleHead)
  - Sistemi di memoria (LTC-Hopfield)
  - Pipeline di coaching (modalità COPER)
  - Schema del database e architettura dello storage
  - Patterns di progettazione UI/UX

### Integrazione Assistenti AI
- **[prompt.md](prompt.md)** — Guida ai prompt per assistenti AI
  Prompt strutturati e workflow per sviluppo assistito da AI, revisione del codice e manutenzione del sistema

### Utilità
- **[generate_manual_pdf_it.py](generate_manual_pdf_it.py)** — Generatore di manuale PDF
  Converte la guida utente italiana in un manuale PDF formattato

## Ricerca e Approfondimenti

### Directory Studies
La directory **[Studies/](Studies/)** contiene 17 documenti di ricerca tecnica approfondita che coprono le fondamenta teoriche e i dettagli implementativi del sistema:

- **Epistemologia e Teoria dei Giochi:** Reti bayesiane di belief, gioco avversariale razionale, stima della probabilità di morte
- **Architettura di Coaching:** Design RAP Coach, modalità COPER (Context + Observation + Pro Reference + Experience + Reasoning)
- **Intelligenza Spaziale:** Gestione Z-cutoff, mappe multi-livello, analisi dell'engagement range
- **Sistemi di Momentum:** Modellazione del momentum temporale, rilevamento dei momenti critici, decadimento della baseline
- **Architetture Neurali:** Allineamento vision-language VL-JEPA, integrazione memoria Hopfield, dinamiche LTC
- **Feature Engineering:** Vettore tattico unificato a 25 dimensioni, quantizzazione euristica
- **Pipeline di Analisi:** Statistiche a livello di round, rating HLTV 2.0, analisi dell'uso delle utility

## Per Iniziare

1. Inizia con **[USER_GUIDE.md](USER_GUIDE.md)** per installazione e configurazione
2. Consulta **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** per l'architettura del sistema
3. Esplora **[Studies/](Studies/)** per una comprensione tecnica approfondita

## Contribuire

Consulta il file `CLAUDE.md` nella root del progetto per i principi ingegneristici e le linee guida di sviluppo.
