# Pipeline di Ingestion Demo

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Infrastruttura di ingestion demo per demo CS2 professionali e utente con integrazione Steam, validazione di integrita' e arricchimento statistico a livello di round.

## Struttura Directory

```
ingestion/
├── __init__.py
├── .validated_cache.json   # Artefatto runtime legacy; resettato solo da tools/reset_pro_data.py (root repo), non scritto da questo package
├── demo_loader.py          # Parser demo a tre passate con cache firmata
├── integrity.py            # Validazione integrita' file demo
├── steam_locator.py        # Rilevamento installazione Steam
├── pipelines/              # Implementazioni pipeline di ingestion
│   ├── user_ingest.py      # Pipeline ingestion demo utente
│   └── json_tournament_ingestor.py  # Importazione batch JSON torneo
└── registry/               # Tracciamento e ciclo di vita file demo
    ├── lifecycle.py         # Pulizia retention demo
    ├── registry.py          # Registry file demo
    └── schema.sql           # Riservato per un futuro registry SQL (attualmente vuoto)
```

## Componenti Principali

### Orchestratori Principali

**`demo_loader.py`** -- `DemoLoader`, il parser demo a tre passate
- Passata 1: posizioni giocatore per tick; Passata 2: eventi/traiettorie granate; Passata 3: tick DataFrame -> oggetti `DemoFrame`
- Parsing tramite demoparser2; estrae anche round start, eventi bomba e kill
- Cache dei risultati parsati come file pickle firmati HMAC-SHA256 (`.mcn`) in una
  directory `demo_cache/` (ricade su `ingestion/cache/`), creata a runtime; il
  caricamento usa un unpickler ristretto (DS-01) e verifica la firma prima della
  deserializzazione

**`steam_locator.py`** -- Rilevamento installazione Steam
- Rilevamento installazione CS2 multi-piattaforma (Windows, Linux)
- Parsing registry (Windows) e scansione filesystem, con fallback a scansione drive
- Auto-rilevamento cartella demo
- `sync_steam_demos()` accoda ogni demo appena scoperta come riga `IngestionTask`

**`integrity.py`** -- Validazione integrita' file demo
- `validate_dem_file()` delega a `backend/data_sources/demo_format_adapter`
  (magic bytes PBDEMS2, limiti dimensione; demo CS:GO legacy rifiutate)
- Helper `compute_sha256()` per hashing file
- Costanti dimensione legacy 50 KB / 900 MB mantenute solo per retrocompatibilita'

## Sub-Package

### `pipelines/`

**`user_ingest.py`** -- Pipeline ingestion demo utente
- Parsing demo utente via demoparser2
- Persiste PlayerMatchStats, poi RoundStats + arricchimento via
  `round_stats_builder.persist_round_stats_and_enrichment()`
- Attiva la pipeline ML (`run_ml_pipeline` da `run_ingestion.py`) e
  archivia la demo solo dopo il successo di tutti i passi

**`json_tournament_ingestor.py`** -- Ingestion batch JSON torneo
- Importazione massiva da export dati torneo
- Validazione schema (`_validate_tournament_json`)
- Appiattimento della gerarchia match/map/round in un CSV di statistiche team per-round

### `registry/`

Registry file demo e gestione ciclo di vita.

**`registry.py`** -- `DemoRegistry`, set JSON-backed di demo elaborate
- `is_processed()` / `mark_processed()` con locking thread + file
- Scritture atomiche con recovery automatico da backup

**`lifecycle.py`** -- `DemoLifecycleManager`
- `cleanup_old_demos(days=30)` elimina file `.dem` archiviati oltre la retention

**`schema.sql`** -- Riservato per un futuro registry basato su SQL (attualmente vuoto)

## Note Importanti

- Lo **scraping HLTV** risiede in `backend/data_sources/hltv/`, NON in questo package
- La funzione principale di orchestrazione ingestion `_ingest_single_demo()` risiede in `run_ingestion.py` alla root del package
- L'orchestratore di produzione **non** importa questo package: `run_ingestion.py` parsa via
  `backend/data_sources/demo_parser` e usa `backend/ingestion/` (resource manager).
  I consumatori di questo package sono `Programma_CS2_RENAN/reporting/report_generator.py` e
  `apps/qt_app/screens/tactical_viewer_screen.py` (`DemoLoader`), `core/session_engine.py`
  (`steam_locator`), e la suite di test (`integrity`)
- L'ingestion demo pro utilizza la stessa pipeline core delle demo utente; le demo pro
  parsano tutti i giocatori (target `"ALL"`) mentre le demo utente puntano al
  `CS2_PLAYER_NAME` configurato
- La scoperta demo e il processing batch sono gestiti da `run_ingestion.py`
  (`StorageManager.list_new_demos()` + la coda `IngestionTask`) e dal worker
  long-running `run_worker.py`, entrambi alla root del package
