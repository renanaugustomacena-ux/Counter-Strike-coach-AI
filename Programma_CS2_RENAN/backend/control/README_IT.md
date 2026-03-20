> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Control — Orchestrazione Applicazione & Gestione Daemon

> **Autorità:** Regola 2 (Sovranità Backend), Regola 6 (Governance dei Cambiamenti)

Questo modulo contiene il piano di controllo centrale del Macena CS2 Analyzer. Gestisce il ciclo di vita di tutti i daemon in background, lo stato di salute del database, le code di ingestion e il coordinamento dell'addestramento ML.

## File

| File | Scopo | Classi Principali |
|------|-------|-------------------|
| `console.py` | Console di controllo unificata — orchestratore singleton | `Console`, `ServiceSupervisor`, `SystemState` |
| `db_governor.py` | Audit dello stato di salute del database + auto-recovery | `DatabaseGovernor` |
| `ingest_manager.py` | Controller coda di ingestion (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | Ciclo di vita addestramento ML con lock di sicurezza cross-processo | `MLControlContext`, `TrainingStopRequested` |

## Stati del Sistema

IDLE ──> BOOTING ──> BUSY ──> IDLE
                       │
                       ├──> MAINTENANCE
                       └──> ERROR → SHUTTING_DOWN

## Architettura Tri-Daemon

| Daemon | Controller | Scopo |
|--------|-----------|-------|
| Hunter | ServiceSupervisor | Scraping statistiche professionali HLTV (sottoprocesso) |
| Digester | IngestionManager | Parsing demo + estrazione feature (thread) |
| Teacher | MLController | Addestramento rete neurale (thread con file lock) |

## Funzionalità Chiave

- Console singleton: thread-safe, gestisce le sequenze di avvio/arresto
- DatabaseGovernor: audita storage Tier 1/2/3, auto-recovery del DB HLTV da backup
- IngestionManager: 3 modalità (SINGLE, CONTINUOUS, TIMED), thread-safe con arresto graduale
- MLController: file lock cross-processo (training.lock), supporto pausa/ripresa/throttle
- Ordine dei lock: Console._lock > ServiceSupervisor._lock (previene deadlock)

## Note di Sviluppo

- Console è un singleton — sicuro da chiamare da qualsiasi thread
- L'eccezione TrainingStopRequested fornisce un'interruzione pulita per addestramenti lunghi
- Il throttling delle risorse è in ingestion/resource_manager.py, non qui
