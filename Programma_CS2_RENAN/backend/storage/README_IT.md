# Livello di Storage del Database

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorità:** `Programma_CS2_RENAN/backend/storage/`
Livello di persistenza tri-database che alimenta ogni operazione dati in Macena CS2 Analyzer.

## Introduzione

Questo pacchetto implementa l'intero livello di persistenza dati utilizzando SQLite in
modalità WAL, ORM SQLModel/SQLAlchemy e un'architettura di storage a tre livelli. Ogni
tick del giocatore, statistica della partita, insight di coaching e profilo di giocatore
professionista passa attraverso questi moduli prima di raggiungere la pipeline di
addestramento della rete neurale o l'interfaccia utente. Il design privilegia la durabilità
dei dati, l'accesso concorrente dai daemon e la portabilità tra macchine.

## Inventario File

| File | Scopo |
|------|-------|
| `db_models.py` | 21 classi tabella SQLModel che coprono l'intero modello dati |
| `database.py` | `DatabaseManager` (monolite) + `HLTVDatabaseManager` + singleton |
| `match_data_manager.py` | Partizioni SQLite per-partita (Tier 3) con cache engine LRU |
| `backup_manager.py` | Backup a caldo via SQLite Online Backup API, ritenzione (ultimo + 7 giornalieri + 4 settimanali) |
| `db_backup.py` | Wrapper SQLite Online Backup API + archiviazione tar.gz per dati partita |
| `db_migrate.py` | Esecutore migrazioni Alembic per aggiornamenti schema automatici all'avvio |
| `maintenance.py` | Pulizia metadati: rimuove vecchi dati tick preservando le statistiche aggregate |
| `state_manager.py` | `StateManager` DAO per la riga singleton `CoachState` |
| `stat_aggregator.py` | `StatCardAggregator`: output dello spider verso `ProPlayer`/`ProPlayerStatCard` |
| `storage_manager.py` | `StorageManager`: percorsi file demo, gestione quota, deduplicazione |
| `remote_file_server.py` | Server cloud personale FastAPI per accesso demo tra macchine |

## Architettura Tri-Database

Il sistema suddivide i dati in tre database SQLite distinti per eliminare la contesa
dei lock di scrittura tra daemon e mantenere bassa la profondità B-tree per partita.

```
+-------------------------------+
|      database.db (Monolite)   |
|  18 tabelle: dati training,   |
|  statistiche giocatore, tick, |
|  stato coaching, conoscenza   |
+---------------+---------------+
                |
                |  Processo separato / nessun link FK
                v
+-------------------------------+
|    hltv_metadata.db (HLTV)    |
|  3 tabelle: ProTeam,          |
|  ProPlayer, ProPlayerStatCard |
+-------------------------------+

+-------------------------------+
|  match_data/{id}.db (Tier 3)  |
|  Telemetria per-partita:      |
|  MatchTickState,              |
|  MatchEventState,             |
|  MatchMetadata                |
+-------------------------------+
   Un file per partita (~1.7M righe ciascuno)
```

### PRAGMA di Connessione (applicate ad ogni checkout)

```sql
PRAGMA journal_mode     = WAL;
PRAGMA synchronous      = NORMAL;
PRAGMA busy_timeout     = 30000;
PRAGMA foreign_keys     = ON;      -- DB-06: FK sono decorative senza questo
PRAGMA wal_autocheckpoint = 512;   -- DB-07: cadenza di checkpoint ~2 MB
```

Pool engine: `pool_size=1, max_overflow=4` per la sicurezza single-writer di SQLite.

## Classi Principali

### DatabaseManager (`database.py`)

Gestisce il monolite `database.db`. Fornisce:

- `create_db_and_tables()` -- inizializzazione schema (filtrato a `_MONOLITH_TABLES`)
- `get_session()` -- context manager con auto-commit/rollback e `expire_all()` in caso di errore
- `upsert()` -- upsert atomico; usa `INSERT ... ON CONFLICT` di SQLite per `PlayerMatchStats`
- `delete_match_cascade()` -- ordine di eliminazione FK-safe (figli prima, poi genitore)
- `detect_orphans()` -- trova file DB per-partita senza un `MatchResult` corrispondente

Accesso singleton: **sempre** usare `get_db_manager()` (double-checked locking).

### HLTVDatabaseManager (`database.py`)

Manager dedicato per `hltv_metadata.db`, isolato per evitare contesa WAL con i daemon
del session engine. Include `_reconcile_stale_schema()` che elimina e ricrea le tabelle
le cui colonne si sono disallineate dalla definizione del modello.

Accesso singleton: `get_hltv_db_manager()`.

### MatchDataManager (`match_data_manager.py`)

Crea e gestisce file SQLite individuali sotto `config.MATCH_DATA_PATH`.
Ogni partita ottiene `match_{id}.db` contenente `MatchTickState`, `MatchEventState`
e `MatchMetadata`. Funzionalità:

- Cache engine LRU (`OrderedDict`, max 50 voci) per prevenire esaurimento file handle
- Auto-migrazione via `_ensure_match_schema()` (passi incrementali `ALTER TABLE`)
- Filtro `tables=` su `create_all()` per impedire che tabelle monolite finiscano nei DB partita
- Utility di migrazione `migrate_match_data()` per rilocare dati su dischi esterni

### StateManager (`state_manager.py`)

DAO thread-safe per la riga singleton `CoachState` (vincolo CHECK `id = 1`).
Traccia lo stato dei daemon, il progresso dell'addestramento, l'heartbeat e i limiti
di risorse. Funzionalità:

- Enum `DaemonName` previene bug da errori di battitura negli aggiornamenti di stato
- Escalation della telemetria (SM-02): logga come WARNING fino a 5 fallimenti consecutivi, poi ERROR
- Auto-pulizia notifiche (SM-03): cap a 500, elimina voci più vecchie di 30 giorni

### BackupManager (`backup_manager.py`)

Backup a caldo usando l'Online Backup API di SQLite (`sqlite3.Connection.backup()` a
`backup_manager.py:81-89`), WAL-safe e non-bloccante. Politica di
ritenzione: mantiene l'ultimo + 7 giornalieri + 4 settimanali. Ogni backup è verificato
con `PRAGMA quick_check` prima dell'accettazione.

### StorageManager (`storage_manager.py`)

Manager del file system per i file demo. Gestisce percorsi demo utente e pro,
applicazione della quota, deduplicazione contro `IngestionTask` e `PlayerMatchStats`,
e protezione path-traversal (P2-03).

## Punti Salienti del Modello Dati (db_models.py)

Il modulo definisce 21 classi tabella SQLModel organizzate in gruppi logici:

- **Telemetria giocatore:** `PlayerMatchStats`, `PlayerTickState`, `RoundStats`, `PlayerProfile`
- **Framework di coaching:** `CoachState`, `CoachingInsight`, `CoachingExperience` (COPER)
- **Base di conoscenza:** `TacticalKnowledge` (RAG, embedding 384-dim)
- **Dati pro:** `ProTeam`, `ProPlayer`, `ProPlayerStatCard`
- **Struttura partita:** `MatchResult`, `MapVeto`
- **Dati esterni:** `Ext_TeamRoundStats`, `Ext_PlayerPlaystyle`
- **Controllo pipeline:** `IngestionTask`, `ServiceNotification`
- **Osservabilità:** `DataLineage`, `DataQualityMetric`, `CalibrationSnapshot`
- **Tuning ML:** `RoleThresholdRecord`

Le protezioni di dimensione dei campi JSON sono applicate tramite validatori Pydantic:
`MAX_GAME_STATE_JSON_BYTES = 16 KB`, `MAX_AUX_JSON_BYTES = 8 KB`.

## Punti di Integrazione

```
session_engine.py ──> get_db_manager()   ──> database.db
                  ──> get_state_manager() ──> CoachState (riga singleton)

hltv_sync_service ──> get_hltv_db_manager() ──> hltv_metadata.db

pipeline ingestion ──> get_match_data_manager() ──> match_data/{id}.db
                   ──> get_db_manager()          ──> PlayerMatchStats, RoundStats
```

## Note di Sviluppo

- **Mai istanziare i manager direttamente.** Usare i singleton `get_db_manager()`,
  `get_hltv_db_manager()`, `get_match_data_manager()` e `get_state_manager()`.
- **Chiamare `reset_match_data_manager()` dopo modifiche a `PRO_DEMO_PATH`** per invalidare
  il pool di engine in cache e utilizzare il nuovo percorso.
- **Il database HLTV NON ha NULLA a che fare con i file demo.** Effettua scraping delle
  statistiche dei giocatori professionisti da hltv.org. L'ingestion delle demo è una
  pipeline completamente separata.
- **Regole cascade FK:** `ON DELETE CASCADE` per dati dipendenti (stat card, map veto);
  `ON DELETE SET NULL` per dati che devono sopravvivere all'eliminazione del genitore (tick, esperienze).
- **Rilocalizzazione dati partita:** migrazione una tantum da `backend/storage/match_data/` a
  `PRO_DEMO_PATH/match_data/` eseguita automaticamente al primo avvio dopo il cambio percorso.
