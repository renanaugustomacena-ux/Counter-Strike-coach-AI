# Pipeline di Ingestion Demo

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Infrastruttura di ingestion demo per demo CS2 professionali e utente con integrazione Steam, validazione di integrità e arricchimento statistico a livello di round.

## Struttura Directory

```
ingestion/
├── __init__.py
├── demo_loader.py          # Orchestratore principale caricamento demo
├── integrity.py            # Validazione integrità file demo
├── steam_locator.py        # Rilevamento installazione Steam
├── cache/                  # Cache demo parsate (file .mcn)
├── pipelines/              # Implementazioni pipeline di ingestion
│   ├── user_ingest.py      # Pipeline ingestion demo utente
│   └── json_tournament_ingestor.py  # Importazione batch JSON torneo
└── registry/               # Tracciamento e ciclo di vita file demo
    ├── lifecycle.py         # Macchina a stati ciclo di vita demo
    ├── registry.py          # Registry file demo
    └── schema.sql           # Schema database registry
```

## Componenti Principali

### Orchestratori Principali

**`demo_loader.py`** — Orchestratore principale caricamento demo
- Coordina parsing file demo con demoparser2
- Validazione integrità via `integrity.py`
- Delega alle implementazioni pipeline in base alla sorgente demo
- Tracciamento progresso e recupero errori

**`steam_locator.py`** — Rilevamento installazione Steam
- Rilevamento installazione CS2 multi-piattaforma (Windows, Linux, macOS)
- Parsing registry (Windows) e scansione filesystem
- Auto-rilevamento cartella demo

**`integrity.py`** — Validazione integrità file demo
- Verifica formato file (magic bytes PBDEMS2)
- Parsing header e validazione dimensioni
- Rilevamento corruzione

## Sub-Package

### `pipelines/`

**`user_ingest.py`** — Pipeline ingestion demo utente
- Parsing demo utente via demoparser2
- Estrazione statistiche round con `round_stats_builder.py`
- Arricchimento con `enrich_from_demo()` (kill noscope/blind, flash assist, utilizzo utility)
- Persistenza su tabelle RoundStats + PlayerMatchStats

**`json_tournament_ingestor.py`** — Ingestion batch JSON torneo
- Importazione massiva da export dati torneo
- Validazione schema
- Risoluzione conflitti

### `registry/`

Registry file demo e gestione ciclo di vita.

**`registry.py`** — Tracciamento file demo
- Traccia stato processing demo (pending, processing, completed, failed)
- Rilevamento duplicati via hash file
- Interfaccia query per stato demo

**`lifecycle.py`** — Macchina a stati ciclo di vita demo
- Transizioni di stato per processing demo
- Applicazione politiche retention
- Automazione pulizia

**`schema.sql`** — Definizione schema database registry

### `cache/`

Directory cache demo parsate. Archivia file intermedi `.mcn` per evitare ri-parsing di demo precedentemente processate.

## Note Importanti

- Lo **scraping HLTV** risiede in `backend/data_sources/hltv/`, NON in questo package
- La funzione principale di orchestrazione ingestion `_ingest_single_demo()` risiede in `run_ingestion.py` alla root del package
- L'ingestion demo pro utilizza la stessa pipeline core delle demo utente, con arricchimento statistico aggiuntivo
- La scoperta demo e il processing batch sono gestiti da `batch_ingest.py` alla root del progetto
