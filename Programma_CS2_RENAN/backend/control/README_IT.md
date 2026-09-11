> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Control — Orchestrazione Applicazione & Gestione Daemon

> **Autorita:** Rule 2 (Sovranita Backend), Rule 6 (Governance dei Cambiamenti)
> **Skill:** `/state-audit`, `/resilience-check`

Questo modulo contiene il piano di controllo centrale del Macena CS2 Analyzer. Gestisce il ciclo di vita di tutti i daemon in background, lo stato di salute del database, le code di ingestion e il coordinamento dell'addestramento ML.

## Inventario File

| File | Scopo | Classi Principali |
|------|-------|-------------------|
| `console.py` | Console di controllo unificata — orchestratore singleton | `Console`, `ServiceSupervisor`, `SystemState`, `ServiceStatus` |
| `db_governor.py` | Audit dello stato di salute del database + auto-recovery | `DatabaseGovernor` |
| `ingest_manager.py` | Controller coda di ingestion (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | Ciclo di vita addestramento ML con lock di sicurezza | `MLController`, `MLControlContext`, `TrainingStopRequested` |

## Stati del Sistema

`_compute_state()` valuta una cascata di priorita — la prima condizione
corrispondente vince:

1. **SHUTTING_DOWN** — flag `_shutting_down` impostato
2. **BOOTING** — flag `_booting` impostato
3. **ERROR** — fallimento integrita DB, un servizio supervisionato e crashato,
   o un daemon CoachState ha status `"Error"`
4. **BUSY** — addestramento ML o ingestion attivamente in corso
5. **IDLE** — default di fallthrough

MAINTENANCE e definito nell'enum `SystemState` ma attualmente non viene mai
assegnato da `_compute_state()`.

## Sequenza di Avvio

Il singleton `Console` orchestra la fase di avvio (`boot()`):

```
1. Avvio daemon Hunter (solo se ENABLE_HLTV_SYNC=true)
   |-- docker_manager.ensure_flaresolverr()
   +-- ServiceSupervisor.start_service("hunter")
       (saltato con notifica utente se Docker non e disponibile)
2. init_database() — crea tabelle/colonne mancanti
3. Audit DatabaseGovernor
   |-- audit_storage(): Tier 1/2 (DB monolitico + WAL), Tier 3 (DB per-partita)
   |-- Auto-restore hltv_metadata.db da .bak se mancante
   +-- verify_integrity() — imposta stato ERROR su fallimento monolite
4. Applicazione retention log (OBS-06)
5. Confidence belief calcolata dal conteggio PlayerMatchStats
   (IngestionManager e MLController avviati su richiesta, non al boot)
```

## Sequenza di Arresto

```
1. Arresto MLController (richiesta stop addestramento)
2. Arresto IngestionManager (segnale evento stop)
3. Arresto Hunter tramite ServiceSupervisor
   +-- terminate() con timeout 5s -> kill()
4. Arresto container FlareSolverr (docker stop)
5. Attesa drain: fino a 5s per ML/ingestion per riportare lo stato stopped
6. Stato impostato su Offline (idempotente — sicuro chiamare due volte)
```

## Architettura Tri-Daemon

La `Console` gestisce tre tipi di daemon:

| Daemon | Controller | Scopo |
|--------|-----------|-------|
| **Hunter** | `ServiceSupervisor` | Scraping statistiche professionali HLTV (sottoprocesso) |
| **Digester** | `IngestionManager` | Parsing demo + estrazione feature (thread) |
| **Teacher** | `MLController` | Addestramento rete neurale (thread con lock in-process) |

### ServiceSupervisor (Hunter)

- Avvia Hunter come sottoprocesso con configurazione `PYTHONPATH`
- Auto-restart: massimo 3 tentativi con ritardo fisso di 5s per il restart
- Finestra di reset tentativi: 3600s (resetta il contatore se nessun crash in 1 ora)
- Thread di monitoraggio che osserva l'output del sottoprocesso con timeout di 3600s
- Cancella i timer di restart in sospeso all'arresto (previene spawn duplicati)

### IngestionManager (Digester)

Tre modalita operative:
- **SINGLE**: Elabora una demo, poi si ferma
- **CONTINUOUS**: Elabora tutte le demo, poi attende e riscansiona
- **TIMED**: Riscansiona ogni N minuti (default 30)

Thread-safe con `threading.Event` per arresto graduale. Elabora al massimo 10 demo per ciclo (WR-07, `_MAX_BATCH_SIZE`) per prevenire utilizzo eccessivo della CPU. Riporta lo stato: conteggi in coda/in elaborazione/falliti.

### MLController (Teacher)

- `MLControlContext`: Token di controllo passato ai loop di addestramento
  - `check_state()`: Chiamato per ogni batch — lancia `TrainingStopRequested` all'arresto
  - Supporto pausa con `Event.wait()` (nessuna attesa attiva)
  - Fattore di throttle: 0.0 (massima velocita) a 1.0 (ritardo massimo)
- **Lock threading in-process** (`_TRAINING_LOCK`): `MLController.start_training()`
  acquisisce questo `threading.Lock` a livello di modulo per prevenire addestramento
  concorrente all'interno dello stesso processo. Non-bloccante: restituisce immediatamente
  se il lock e mantenuto.
- **File lock cross-processo** (`training_file_lock()`): Context manager esportato
  che blocca `DATA_DIR/training.lock` tramite `fcntl`/`msvcrt` per sicurezza
  cross-processo. Attualmente non chiamato da `MLController` stesso — disponibile per
  chiamanti esterni che necessitano di coordinamento tra processi.

## Ordine dei Lock (Critico)

```
Console._lock  >  ServiceSupervisor._lock
```

Console non acquisisce mai il lock di ServiceSupervisor mentre detiene il proprio, e viceversa. Violare questo ordine rischia un deadlock.

## Note di Sviluppo

- `Console` e un singleton — sicuro da chiamare da qualsiasi thread
- Tutti i metodi pubblici di `Console` sono thread-safe
- `DatabaseGovernor.audit_storage()` restituisce una lista di anomalie per il logging
- L'enum `IngestMode` previene stringhe di modalita non valide
- L'eccezione `TrainingStopRequested` fornisce un meccanismo di interruzione pulita per addestramenti lunghi
- Il throttling delle risorse e in `backend/ingestion/resource_manager.py`, non qui
