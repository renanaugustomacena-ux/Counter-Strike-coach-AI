> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sistema di Migrazione Database (Alembic)

Sistema di migrazione database utilizzando Alembic per gestire l'evoluzione dello schema SQLite.

## Panoramica

Questa directory contiene migrazioni Alembic per il database Macena CS2 Analyzer (`database.db`). Tutti i cambiamenti di schema devono passare attraverso migrazioni — nessun DDL manuale in produzione.

## File di Migrazione

La directory `versions/` contiene 13 file di migrazione che coprono:

- Campi profilo e preferenze utente
- Allineamento schema con modelli
- Statistiche giocatori professionisti
- Supporto daemon (Hunter, Digester, Teacher)
- Telemetria e osservabilità
- Colonne piano fusion (temporal baseline, soglie ruolo, stato coaching)

## File Chiave

- `env.py` — Configurazione ambiente Alembic (connessione a database SQLite in modalità WAL)
- `alembic.ini` — Configurazione Alembic (URL database, logging)
- `versions/` — Storia migrazioni (sequenziale, immutabile)

## Principi di Migrazione

- **Idempotenti** — Le migrazioni possono essere eseguite più volte in sicurezza
- **Reversibili** — Tutte le migrazioni hanno percorsi upgrade e downgrade
- **Version-controlled** — Le migrazioni sono committed su git
- **Testate** — Migrazioni testate su dati simili a produzione prima del deployment

## Utilizzo

```bash
# Controlla stato migrazione corrente
alembic current

# Aggiorna all'ultima versione
alembic upgrade head

# Downgrade di una revisione
alembic downgrade -1

# Genera nuova migrazione
alembic revision --autogenerate -m "descrizione"
```

## Note

- Il database usa modalità SQLite WAL per accesso concorrente
- Tutte le migrazioni devono passare validazione headless prima del commit
- Mai saltare migrazioni o forzare cambiamenti schema
