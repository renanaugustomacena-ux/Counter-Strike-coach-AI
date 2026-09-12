> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Scaffold di Migrazione Legacy

Questa directory contiene uno **scaffold Alembic legacy** da una prima iterazione del layer di persistenza dei dati. Viene mantenuta solo come riferimento storico — la catena di migrazioni **attiva** per l'applicazione vive nella directory `alembic/` alla radice del repo (19 revisioni, configurata dal file `alembic.ini` alla radice).

## Panoramica Tecnica

Lo scaffold utilizza SQLAlchemy/SQLModel come layer ORM e Alembic per l'evoluzione dello schema, rispecchiando l'approccio che il progetto utilizza ancora oggi. Contiene le prime due revisioni di schema mai scritte per il layer delle statistiche di match; lo sviluppo successivo ha riavviato la catena alla radice del repo, dove vivono tutte le revisioni successive.

## Componenti Chiave

### Migrazioni Alembic
La sottodirectory **`migrations/`** contiene lo scaffold:
- **`env.py`**: Il punto di ingresso dell'ambiente Alembic (importa tutti i modelli da `Programma_CS2_RENAN.backend.storage.db_models` e punta a `SQLModel.metadata`).
- **`script.py.mako`**: Un file template utilizzato da Alembic per generare nuovi script di migrazione.
- **`README`**: Un avviso di deprecazione (R2-01) che marca questa catena come legacy e rimanda alla directory `alembic/` alla radice.
- **`versions/`**: I due script di migrazione iniziali.
    - **`b609a11e13cc_baseline_schema.py`**: Stabilisce le tabelle iniziali (`matchresult`, `mapveto`) ed estende `proplayerstatcard`.
    - **`5d5764ef9f26_add_rating_components.py`**: Aggiunge le colonne dei componenti Rating 2.0 (kpr, dpr, ...) a `playermatchstats`.

## Struttura della Directory

```text
backend/storage/
├── migrations/             # Scaffold Alembic legacy
│   ├── env.py              # Configurazione dell'ambiente
│   ├── script.py.mako      # Template script di migrazione
│   ├── README              # Avviso di deprecazione R2-01
│   └── versions/           # Due revisioni di schema iniziali
├── README.md               # Documentazione in inglese
├── README_IT.md            # Questa documentazione
└── README_PT.md            # Versione portoghese
```

## Utilizzo

**Non** eseguire migrazioni da questa directory — qui non c'e un `alembic.ini`, e la catena e superata. Tutti i comandi di migrazione si eseguono dalla radice del progetto contro la directory `alembic/` alla radice:

### Applicazione delle Migrazioni
```bash
alembic upgrade head
```

### Creazione di una Nuova Migrazione
Quando le classi SQLModel in `Programma_CS2_RENAN/backend/storage/db_models.py` vengono aggiornate:
```bash
alembic revision --autogenerate -m "descrizione delle modifiche"
```

### Rollback
```bash
alembic downgrade -1
```

L'URL del database e impostato nel file `alembic.ini` alla radice (monolite SQLite `Programma_CS2_RENAN/backend/storage/database.db`); la variabile d'ambiente `CS2_ALEMBIC_URL` puo sovrascriverlo per database di verifica temporanei. Consulta `alembic/README.md` alla radice del repo per la cronologia completa delle migrazioni.
