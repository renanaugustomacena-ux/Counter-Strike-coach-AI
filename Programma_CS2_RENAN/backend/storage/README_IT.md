# Livello Storage Database

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Panoramica

Livello di persistenza basato su SQLite con modalità WAL, ORM SQLModel, gestione backup e architettura dual-storage (monolite `database.db` + file SQLite per-match).

## Componenti Chiave

### `db_models.py`
61+ classi SQLModel che definiscono il modello dati completo:
- **Statistiche Giocatore**: `PlayerMatchStats`, `PlayerTickState`, `RoundStats`
- **Coaching**: `CoachState`, `CoachingInsight`, `CoachingExperience`
- **Conoscenza**: `TacticalKnowledge`, `ExperienceRecord`
- **Dati Pro**: `ProPlayer`, `MatchResult`, `TeamComposition`
- **Analisi**: `MomentumState`, `BeliefSnapshot`, `RoleThresholdRecord`
- **Sistema**: `DemoFileRecord`, `TrainingMetrics`, `IntegrityManifest`

### `database.py`
- **`DatabaseManager`** — Gestore connessioni SQLite con modalità WAL
- **`get_db_manager()`** — Pattern factory singleton
- **`init_database()`** — Inizializzazione schema e migrazione

### `match_data_manager.py`
- **`MatchDataManager`** — Gestione database SQLite per-match
- **`get_match_data_manager()`** — Factory singleton con integrazione config
- **`migrate_match_data()`** — Migrazione una-tantum a percorso storage esterno
- DB match memorizzati in `config.MATCH_DATA_PATH` (default: `PRO_DEMO_PATH/match_data/`)

### `backup_manager.py`
- **`BackupManager`** — Orchestra backup di DB monolite e tutti i DB match
- Policy rotazione, verifica integrità

### Moduli di Supporto
- **`db_backup.py`** — Utility backup con risoluzione path da config
- **`db_migrate.py`** — Utility migrazione Alembic
- **`maintenance.py`** — VACUUM, ANALYZE, controlli integrità
- **`state_manager.py`** — Persistenza CoachState
- **`stat_aggregator.py`** — Aggregazione RoundStats → PlayerMatchStats

## Pattern Critici

- **Usa sempre modalità WAL** — `PRAGMA journal_mode=WAL` per accesso concorrente
- **Mai hardcodare path match_data** — Usa `config.MATCH_DATA_PATH` o `get_match_data_manager()`
- **Chiama `reset_match_data_manager()` dopo cambio path** — Invalida cache singleton

## Migrazione

Rilocalizzazione match data implementata nella sessione 2026-02-22. Vecchia posizione: `backend/storage/match_data/`. Nuova posizione: `PRO_DEMO_PATH/match_data/` (disco esterno).
