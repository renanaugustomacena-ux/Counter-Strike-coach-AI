> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sistema di Migrazione Database (Alembic)

> **Autorità:** Regola 5 (Persistenza Dati), Regola 6 (Governance dei Cambiamenti)
> **Skill:** `/db-review`

Sistema di migrazione database utilizzando Alembic per gestire l'evoluzione dello schema SQLite nel Macena CS2 Analyzer. Tutti i cambiamenti di schema al database monolite (`database.db`) devono passare attraverso migrazioni Alembic — nessun DDL manuale in produzione.

## Struttura Directory

```
alembic/
├── env.py                  # Configurazione ambiente Alembic
├── script.py.mako          # Template script migrazione
└── versions/               # Storico migrazioni (sequenziale, immutabile)
    ├── 19fcff36ea0a_...    # Telemetria heartbeat
    ├── 3c6ecb5fe20e_...    # Colonne piano fusion
    ├── 57a72f0df21e_...    # Heartbeat nullable
    ├── 609fed4b4dce_...    # Tracciamento task ingestione
    ├── 7a30a0ea024e_...    # Sincronizzazione schema
    ├── 89850b6e0a49_...    # Statistiche giocatori professionisti
    ├── 8a93567a2798_...    # Collegamento fisica pro
    ├── 8c443d3d9523_...    # Supporto triplo daemon
    ├── a1b2c3d4e5f6_...    # Metriche qualità dati
    ├── b2c3d4e5f6a7_...    # Arricchimento tick giocatore
    ├── c8a2308770e5_...    # Trigger riaddestramento
    ├── da7a6be5c0c7_...    # Notifiche servizio
    ├── e3013f662fd4_...    # Sincronizzazione stato coaching
    └── f769fbe67229_...    # Completamento campi profilo
```

## Storico Migrazioni (14 Revisioni)

| Revisione | Descrizione | Tabelle Interessate |
|-----------|-------------|---------------------|
| `f769fbe67229` | Aggiunta campi profilo mancanti | `UserProfile` |
| `e3013f662fd4` | Aggiunta sync e intervallo a CoachState | `CoachState` |
| `da7a6be5c0c7` | Aggiunta tabella notifiche servizio | `ServiceNotification` (nuova) |
| `c8a2308770e5` | Supporto trigger riaddestramento | `TrainingState` |
| `b2c3d4e5f6a7` | Colonne arricchimento in PlayerTickState | `PlayerTickState` |
| `a1b2c3d4e5f6` | Qualità dati in PlayerMatchStats | `PlayerMatchStats` |
| `8c443d3d9523` | Supporto triplo daemon (Hunter/Digester/Teacher) | `DaemonState` (nuova) |
| `8a93567a2798` | Collegamento fisica pro a statistiche | `ProPlayer`, `ProPlayerStatCard` |
| `89850b6e0a49` | Aggiunta statistiche giocatori professionisti | `ProPlayer` (nuova), `ProPlayerStatCard` (nuova) |
| `7a30a0ea024e` | Sincronizzazione tabelle mancanti | Multiple |
| `609fed4b4dce` | Aggiunta last_tick_processed a IngestionTask | `IngestionTask` |
| `57a72f0df21e` | Aggiunta heartbeat nullable a CoachState | `CoachState` |
| `3c6ecb5fe20e` | Colonne piano fusion (baseline temporale, soglie ruolo) | `CoachState` |
| `19fcff36ea0a` | Aggiunta telemetria heartbeat a CoachState | `CoachState` |

## `env.py` — Configurazione Ambiente

Lo script ambiente gestisce sia la modalità migrazione offline che online:

- **Stabilizzazione percorsi** via `core.config.stabilize_paths()` — garantisce la corretta risoluzione di `CORE_DB_DIR`
- **Import modelli** — importa tutte le classi SQLModel da `backend/storage/db_models.py` per autogenerate
- **Imposizione WAL mode** — ogni connessione imposta `PRAGMA journal_mode=WAL` prima di eseguire le migrazioni
- **URL Database** — risolto da `core.config.DATABASE_URL` (punta sempre al monolite `database.db`)

```python
# Configurazione connessione (semplificata)
connectable = create_engine(config.DATABASE_URL)
with connectable.connect() as connection:
    connection.execute(text("PRAGMA journal_mode=WAL"))
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

## Ambito e Confini

Alembic gestisce **solo** il database monolite (`database.db`). Gli altri due database nell'architettura tri-database sono gestiti separatamente:

| Database | Gestore | Strategia Migrazione |
|----------|---------|---------------------|
| `database.db` (monolite) | Alembic | Migrazioni versionali sequenziali |
| `hltv_metadata.db` | `HLTVDatabaseManager` | Schema creato al primo utilizzo |
| `match_data/<id>.db` (per-match) | `MatchDataManager` | Schema creato per ogni demo ingerita |

## Utilizzo

```bash
# Attivare prima l'ambiente virtuale
source /home/renan/.venvs/cs2analyzer/bin/activate

# Controllare stato migrazione corrente
alembic current

# Aggiornare all'ultima versione
alembic upgrade head

# Downgrade di una revisione
alembic downgrade -1

# Generare nuova migrazione (dopo aver modificato db_models.py)
alembic revision --autogenerate -m "descrizione_del_cambiamento"

# Visualizzare storico migrazioni
alembic history --verbose
```

## Principi di Migrazione

1. **Idempotenti** — le migrazioni usano `batch_alter_table` per compatibilità SQLite e possono essere rieseguite
2. **Reversibili** — ogni migrazione ha entrambe le funzioni `upgrade()` e `downgrade()`
3. **Versionati** — le migrazioni sono committate su git e mai modificate dopo il merge
4. **Testati** — eseguire `python tools/headless_validator.py` dopo ogni cambio di schema
5. **Atomici** — ogni migrazione è un singolo cambiamento logico di schema
6. **SQLite-aware** — usare `op.batch_alter_table()` per operazioni ALTER TABLE (limitazione SQLite)

## Note di Sviluppo

- Eseguire sempre `alembic upgrade head` dopo aver scaricato nuove modifiche che includono migrazioni
- Mai eliminare o riordinare i file di migrazione in `versions/`
- Il file `alembic.ini` nella root del progetto configura l'URL del database e il logging
- SQLite non supporta nativamente tutte le operazioni ALTER TABLE — la modalità batch di Alembic gestisce questo
- Dopo aver creato una nuova migrazione, verificarla con `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
- Il `DatabaseGovernor` in `backend/control/db_governor.py` verifica lo stato delle migrazioni ad ogni avvio
- Tutte le 61+ classi SQLModel in `db_models.py` sono importate da `env.py` per il rilevamento autogenerate

## Problemi Comuni

| Problema | Causa | Soluzione |
|----------|-------|----------|
| "Target database is not up to date" | Migrazioni in sospeso | Eseguire `alembic upgrade head` |
| "Can't locate revision" | Tabella `alembic_version` corrotta | Controllare `alembic current`, correggere manualmente |
| "No changes detected" | Cambiamenti modello non importati | Verificare import di `db_models.py` in `env.py` |
| Errori batch mode | Mancanza di `render_as_batch=True` | Aggiungere a `context.configure()` in `env.py` |
