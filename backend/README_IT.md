# `backend/` (top-level) — area di staging dello storage

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Layout del filesystem a livello repo
> **Stato:** Area di staging; il pacchetto backend vero e proprio si trova in `Programma_CS2_RENAN/backend/`.

## Perché esiste questa directory

`./backend/` (questa directory, alla radice del repo) **non** è il pacchetto backend dell'applicazione. È una piccola area di staging del filesystem che rispecchia il layout del dominio backend al di fuori dell'albero del pacchetto Python — oggi contiene solo uno scaffold Alembic legacy sotto `storage/`.

Il codebase backend vero e proprio — servizi, training NN, ingestione, gestori di storage, base di conoscenza, pipeline di processing — vive in:

> `Programma_CS2_RENAN/backend/` ([README](../Programma_CS2_RENAN/backend/README.md))

Quel sotto-pacchetto contiene 14 moduli di dominio (`analysis/`, `coaching/`, `control/`, `data_sources/`, `ingestion/`, `knowledge/`, `knowledge_base/`, `nn/`, `onboarding/`, `processing/`, `progress/`, `reporting/`, `services/`, `storage/`).

## Cosa vive qui

```
backend/
└── storage/
    └── migrations/   # Scaffold Alembic legacy (2 revisioni iniziali) — NON la catena attiva
```

`backend/storage/` contiene solo uno scaffold Alembic vestigiale ([README](storage/README.md)). La catena di migrazioni **attiva** vive nella directory `alembic/` alla radice del repo (19 revisioni), configurata dal file `alembic.ini` alla radice. I database di runtime **non** vivono qui: il monolite `database.db` e `hltv_metadata.db` vengono creati sotto `Programma_CS2_RENAN/backend/storage/`, e gli shard per-match vanno in `PRO_DEMO_PATH/match_data/` (con fallback su `Programma_CS2_RENAN/backend/storage/match_data/`).

## Da non fare

- **Non** aggiungere file sorgente Python qui. Il nuovo codice backend va in `Programma_CS2_RENAN/backend/<dominio>/`.
- **Non** trattare questo come path di import. `from backend.foo import ...` non si risolverà — la radice del pacchetto è `Programma_CS2_RENAN`.
- **Non** aggiungere nuove migrazioni qui. Le nuove modifiche allo schema passano attraverso la catena `alembic/versions/` alla radice.

## Documentazione correlata

- Pacchetto backend dell'applicazione: `Programma_CS2_RENAN/backend/README.md`
- Specifiche dello storage layer: `Programma_CS2_RENAN/backend/storage/README.md`
- Catena di migrazioni attiva: `alembic/README.md` (radice del repo)
- Architettura tri-database: `REFERENCE.md`
