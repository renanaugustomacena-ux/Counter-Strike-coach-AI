> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Control — Orchestrazione Applicazione & Gestione Daemon

> **Autorità:** Rule 2 (Sovranità Backend), Rule 6 (Governance dei Cambiamenti)
> **Skill:** `/state-audit`, `/resilience-check`

Questo modulo contiene il piano di controllo centrale del Macena CS2 Analyzer. Gestisce il ciclo di vita di tutti i daemon in background, lo stato di salute del database, le code di ingestion e il coordinamento dell'addestramento ML.

## Inventario File

| File | Scopo | Classi Principali |
|------|-------|-------------------|
| `console.py` | Console di controllo unificata — orchestratore singleton | `Console`, `ServiceSupervisor`, `SystemState`, `ServiceStatus` |
| `db_governor.py` | Audit dello stato di salute del database + auto-recovery | `DatabaseGovernor` |
| `ingest_manager.py` | Controller coda di ingestion (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | Ciclo di vita addestramento ML con lock di sicurezza cross-processo | `MLControlContext`, `TrainingStopRequested` |

## Stati del Sistema

```
IDLE ──> BOOTING ──> BUSY ──> IDLE
                       │
                       ├──> MAINTENANCE
                       └──> ERROR
                             │
                             └──> SHUTTING_DOWN
```

## Sequenza di Avvio

Il singleton `Console` orchestra la fase di avvio:

```
1. DatabaseGovernor.audit_storage()
   ├── Verifica Tier 1/2 (DB monolitico + WAL)
   ├── Verifica Tier 3 (DB per-partita)
   └── Auto-recovery del DB HLTV da .bak se mancante
2. Inizializzazione StateManager
3. Avvio ServiceSupervisor
   └── Avvio daemon Hunter (sincronizzazione HLTV)
4. Avvio IngestionManager
   └── Inizio scansione demo
5. Pronto per MLController (addestramento su richiesta)
```

## Sequenza di Arresto

```
1. Arresto IngestionManager (svuotamento coda)
2. Arresto MLController (salvataggio checkpoint)
3. Arresto ServiceSupervisor
   └── terminate() con timeout 5s → kill()
4. Salvataggio stato
```

## Architettura Tri-Daemon

La `Console` gestisce tre tipi di daemon:

| Daemon | Controller | Scopo |
|--------|-----------|-------|
| **Hunter** | `ServiceSupervisor` | Scraping statistiche professionali HLTV (sottoprocesso) |
| **Digester** | `IngestionManager` | Parsing demo + estrazione feature (thread) |
| **Teacher** | `MLController` | Addestramento rete neurale (thread con file lock) |

### ServiceSupervisor (Hunter)

- Avvia Hunter come sottoprocesso con configurazione `PYTHONPATH`
- Auto-restart: massimo 3 tentativi con backoff esponenziale
- Finestra di reset tentativi: 3600s (resetta il contatore se nessun crash in 1 ora)
- Thread di monitoraggio che osserva l'output del sottoprocesso con timeout di 3600s
- Cancella i timer di restart in sospeso all'arresto (previene spawn duplicati)

### IngestionManager (Digester)

Tre modalità operative:
- **SINGLE**: Elabora una demo, poi si ferma
- **CONTINUOUS**: Elabora tutte le demo, poi attende e riscansiona
- **TIMED**: Riscansiona ogni N minuti (default 30)

Thread-safe con `threading.Event` per arresto graduale. Riporta lo stato: conteggi in coda/in elaborazione/falliti.

### MLController (Teacher)

- `MLControlContext`: Token di controllo passato ai loop di addestramento
  - `check_state()`: Chiamato per ogni batch — lancia `TrainingStopRequested` all'arresto
  - Supporto pausa con `Event.wait()` (nessuna attesa attiva)
  - Fattore di throttle: 0.0 (massima velocità) a 1.0 (ritardo massimo)
- **File lock cross-processo** (`training.lock`): Impedisce addestramento concorrente
  - Utilizza `fcntl` (Unix) / `msvcrt` (Windows)
  - Non-bloccante: lancia `RuntimeError` se il lock è mantenuto
  - Tracciamento basato su PID per il debugging

## Ordine dei Lock (Critico)

```
Console._lock  >  ServiceSupervisor._lock
```

Console non acquisisce mai il lock di ServiceSupervisor mentre detiene il proprio, e viceversa. Violare questo ordine rischia un deadlock.

## Note di Sviluppo

- `Console` è un singleton — sicuro da chiamare da qualsiasi thread
- Tutti i metodi pubblici di `Console` sono thread-safe
- `DatabaseGovernor.audit_storage()` restituisce una lista di anomalie per il logging
- L'enum `IngestMode` previene stringhe di modalità non valide
- L'eccezione `TrainingStopRequested` fornisce un meccanismo di interruzione pulita per addestramenti lunghi
- Il throttling delle risorse è in `ingestion/resource_manager.py`, non qui
