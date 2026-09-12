> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sistema di Migrazione Database (Alembic)

> **Autorità:** Regola 4 (Persistenza Dati), Regola 6 (Governance dei Cambiamenti)
> **Skill:** `/db-review`

Sistema di migrazione database utilizzando Alembic per gestire l'evoluzione dello schema SQLite nel Macena CS2 Analyzer. Tutti i cambiamenti di schema al database monolite (`database.db`) devono passare attraverso migrazioni Alembic — nessun DDL manuale in produzione.

## Struttura Directory

```
alembic/
├── env.py                  # Configurazione ambiente Alembic
├── script.py.mako          # Template script migrazione
└── versions/               # Storico migrazioni (sequenziale, immutabile)
    ├── f769fbe67229_...    # Completamento campi profilo (root)
    ├── 7a30a0ea024e_...    # Sincronizzazione schema
    ├── 89850b6e0a49_...    # Statistiche giocatori professionisti
    ├── 8a93567a2798_...    # Collegamento fisica pro
    ├── c8a2308770e5_...    # Trigger riaddestramento
    ├── 8c443d3d9523_...    # Supporto triplo daemon
    ├── 609fed4b4dce_...    # Tracciamento task ingestione
    ├── e3013f662fd4_...    # Sincronizzazione stato coaching
    ├── 57a72f0df21e_...    # Heartbeat nullable
    ├── da7a6be5c0c7_...    # Notifiche servizio
    ├── 19fcff36ea0a_...    # Telemetria heartbeat
    ├── 3c6ecb5fe20e_...    # Colonne piano fusion
    ├── a1b2c3d4e5f6_...    # Metriche qualità dati
    ├── b2c3d4e5f6a7_...    # Arricchimento tick giocatore
    ├── c3d4e5f6a7b8_...    # Etichetta strategia esperienza coaching
    ├── d4e5f6a7b8c9_...    # Colonne SteamID
    ├── e5f6a7b8c9d0_...    # Indice stream POV
    ├── f6a7b8c9d0e1_...    # Rimozione connect_state
    └── a7b8c9d0e1f2_...    # Fonte data partita (head)
```

## Storico Migrazioni (19 Revisioni)

Catena lineare singola, dalla più vecchia. Head corrente: `a7b8c9d0e1f2`.

| Revisione | Descrizione | Tabelle Interessate |
|-----------|-------------|---------------------|
| `f769fbe67229` | Aggiunta campi profilo mancanti (root) | `PlayerProfile`, `IngestionTask` (nuova) |
| `7a30a0ea024e` | Sincronizzazione tabelle mancanti | `CalibrationSnapshot` (nuova), `RoleThresholdRecord` (nuova) |
| `89850b6e0a49` | Aggiunta statistiche giocatori professionisti | `ProTeam` (nuova), `ProPlayer` (nuova), `ProPlayerStatCard` (nuova) |
| `8a93567a2798` | Collegamento fisica pro a statistiche | `PlayerMatchStats` (FK a `ProPlayer`) |
| `c8a2308770e5` | Supporto trigger riaddestramento | `CoachState` |
| `8c443d3d9523` | Supporto triplo daemon (Hunter/Digester/Teacher) | `CoachState` |
| `609fed4b4dce` | Aggiunta last_tick_processed a IngestionTask | `IngestionTask` |
| `e3013f662fd4` | Aggiunta sync e intervallo a CoachState | `CoachState` |
| `57a72f0df21e` | Aggiunta heartbeat nullable a CoachState | `CoachState` |
| `da7a6be5c0c7` | Aggiunta tabella notifiche servizio | `ServiceNotification` (nuova) |
| `19fcff36ea0a` | Aggiunta telemetria heartbeat a CoachState | `CoachState` |
| `3c6ecb5fe20e` | Colonne piano fusion (trade kills, suddivisione utility, feedback COPER) | `PlayerMatchStats`, `CoachingExperience` |
| `a1b2c3d4e5f6` | Aggiunta qualità dati a PlayerMatchStats | `PlayerMatchStats` |
| `b2c3d4e5f6a7` | Aggiunta colonne arricchimento a PlayerTickState | `PlayerTickState` |
| `c3d4e5f6a7b8` | Aggiunta strategy_label a CoachingExperience | `CoachingExperience` |
| `d4e5f6a7b8c9` | Aggiunta steamid a tick e match stats | `PlayerTickState`, `PlayerMatchStats` |
| `e5f6a7b8c9d0` | Aggiunta indice stream POV a PlayerTickState | `PlayerTickState` (solo indice) |
| `f6a7b8c9d0e1` | Rimozione connect_state da Ext_PlayerPlaystyle | `Ext_PlayerPlaystyle` |
| `a7b8c9d0e1f2` | Aggiunta marcatore provenienza match_date_source (head) | `PlayerMatchStats` |

## `env.py` — Configurazione Ambiente

Lo script ambiente gestisce sia la modalità migrazione offline che online:

- **Stabilizzazione percorsi** via `core.config.stabilize_paths()` — garantisce la corretta risoluzione di `CORE_DB_DIR`
- **Import modelli** — importa esplicitamente 19 classi SQLModel da `Programma_CS2_RENAN/backend/storage/db_models.py` per diff autogenerate rispetto a `SQLModel.metadata`
- **Backup pre-migrazione** — la modalità online chiama `db_backup.backup_monolith()` prima di eseguire le migrazioni (non fatale in caso di errore)
- **URL Database** — `CS2_ALEMBIC_URL` (variabile d'ambiente, per DB di verifica usa e getta) prevale su `core.config.DATABASE_URL` (il monolite `database.db`)

```python
# Risoluzione URL + esecuzione online (semplificata)
config.set_main_option("sqlalchemy.url", os.environ.get("CS2_ALEMBIC_URL", DATABASE_URL))
_pre_migration_backup()  # backup_monolith(), non fatale
connectable = engine_from_config(..., poolclass=pool.NullPool)
with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

## Ambito e Confini

Alembic gestisce **solo** il database monolite (`database.db`). Gli altri due database nell'architettura tri-database sono gestiti separatamente:

| Database | Gestore | Strategia Migrazione |
|----------|---------|---------------------|
| `database.db` (monolite) | Alembic | Migrazioni versionali sequenziali |
| `hltv_metadata.db` | `HLTVDatabaseManager` | Schema via `SQLModel.metadata.create_all()` al primo utilizzo |
| `match_data/<id>.db` (per-match) | `MatchDataManager` | Schema creato per ogni demo ingerita |

Portare `hltv_metadata.db` sotto Alembic è un **lavoro in backlog** (TASKS.md #47, Programme Phase G7) — oggi il suo schema evolve ancora al di fuori di Alembic.

## Utilizzo

```bash
# Attivare prima l'ambiente virtuale del progetto (vedi "Manual Setup" nel README.md principale)

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

1. **Sequenziale** — una catena lineare singola, nessun ramo (head corrente: `a7b8c9d0e1f2`)
2. **Reversibile** — ogni migrazione ha entrambe le funzioni `upgrade()` e `downgrade()`
3. **Versionato** — le migrazioni sono committate su git e mai modificate dopo il merge
4. **Testato** — eseguire `python tools/headless_validator.py` dopo ogni cambio di schema
5. **Atomico** — ogni migrazione è un singolo cambiamento logico di schema
6. **SQLite-aware** — usare `op.batch_alter_table()` per operazioni ALTER TABLE (limitazione SQLite)

## Note di Sviluppo

- Eseguire sempre `alembic upgrade head` dopo aver scaricato nuove modifiche che includono migrazioni
- Mai eliminare o riordinare i file di migrazione in `versions/`
- Il file `alembic.ini` nella root del progetto configura l'URL del database e il logging
- SQLite non supporta nativamente tutte le operazioni ALTER TABLE — la modalità batch di Alembic gestisce questo
- Dopo aver creato una nuova migrazione, verificarla con `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
- Il `DatabaseGovernor` in `Programma_CS2_RENAN/backend/control/db_governor.py` esegue audit periodici di integrità (`PRAGMA quick_check`) sui database attivi
- `env.py` importa esplicitamente 19 classi SQLModel da `db_models.py` (che definisce 25 modelli `table=True`) per il rilevamento autogenerate — aggiungere una tabella significa aggiungere il suo import lì

## Problemi Comuni

| Problema | Causa | Soluzione |
|----------|-------|----------|
| "Target database is not up to date" | Migrazioni in sospeso | Eseguire `alembic upgrade head` |
| "Can't locate revision" | Tabella `alembic_version` corrotta | Controllare `alembic current`, correggere manualmente |
| "No changes detected" | Cambiamenti modello non importati | Verificare import di `db_models.py` in `env.py` |
| Errori batch mode | Mancanza di `render_as_batch=True` | Aggiungere a `context.configure()` in `env.py` |
