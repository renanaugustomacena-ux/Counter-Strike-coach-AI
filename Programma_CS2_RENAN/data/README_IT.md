> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Data — Dati Applicazione e Configurazione

> **Autorita:** Rule 4 (Data Persistence)

Questa directory contiene dati runtime, file di configurazione, conoscenza per il coaching, dataset statistici esterni e l'area di staging per l'ingestione delle demo.

## Struttura della Directory

data/
├── demos/pro_ingest/         # Demo di partite professionistiche per il training
├── docs/                     # Documentazione di aiuto in-app
├── external/                 # Dataset statistici di terze parti (CSV)
├── knowledge/                # Base di conoscenza RAG per il coaching
├── dataset.csv               # Dataset di training
├── map_config.json           # Configurazione spaziale delle mappe
├── map_tensors.json          # Definizioni coordinate tensore 3D
├── pro_baseline.csv          # Statistiche baseline professionistiche
└── hltv_sync_state.json      # Stato di sincronizzazione scraper HLTV

## File di Configurazione Principali

### map_config.json
Definizioni spaziali per tutte le mappe competitive di CS2 (pos_x, pos_y, scale, landmarks, z_cutoff per mappe multi-livello).

### map_tensors.json
Coordinate tensore 3D per il training ML (posizioni bombsite, posizioni spawn, zone di controllo mid).

## external/ — Dataset Statistici
Dati CSV di terze parti usati per analisi di riferimento e calibrazione del coaching (top 100 giocatori, ruoli di playstyle, statistiche mappe, statistiche armi, esiti round, ecc.)

## knowledge/ — Base di Conoscenza RAG
Testi di coaching per mappa (8 mappe x 2 versioni), base di conoscenza JSON strutturata, utilizzati dal framework COPER tramite embedding SBERT e indicizzazione FAISS.

## Note di Sviluppo

- NON committare file demo (.dem) — sono da 50-200MB ciascuno
- I CSV esterni sono dati di riferimento statici
- I file di conoscenza sono la base intellettuale del coaching — modificare con cura
