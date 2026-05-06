# `backend/` (top-level) — area di staging dello storage

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Layout del filesystem a livello repo
> **Stato:** Area di staging; il pacchetto backend vero e proprio si trova in `Programma_CS2_RENAN/backend/`.

## Perché esiste questa directory

`./backend/` (questa directory, alla radice del repo) **non** è il pacchetto backend dell'applicazione. È una piccola area di staging del filesystem che contiene file che devono vivere fuori dall'albero del pacchetto Python ma logicamente appartengono al dominio backend — tipicamente shard SQLite per-match e altri artefatti generati di grandi dimensioni che non dovrebbero essere committati sotto `Programma_CS2_RENAN/`.

Il codebase backend vero e proprio — servizi, training NN, ingestione, gestori di storage, base di conoscenza, pipeline di processing — vive in:

> `Programma_CS2_RENAN/backend/` ([README](../Programma_CS2_RENAN/backend/README.md))

Quel sotto-pacchetto contiene 14 moduli di dominio (`analysis/`, `coaching/`, `control/`, `data_sources/`, `ingestion/`, `knowledge/`, `knowledge_base/`, `nn/`, `onboarding/`, `processing/`, `progress/`, `reporting/`, `services/`, `storage/`).

## Cosa vive qui

```
backend/
└── storage/          # Artefatti runtime generati (SQLite per-match, backup)
```

`backend/storage/` è la radice dei dati runtime usata da `MatchDataManager` quando `PRO_DEMO_PATH` non è configurato o non disponibile. I file `match_{id}.db` per-match atterrano qui e si accumulano nel tempo. La pulizia è gestita da `Programma_CS2_RENAN/backend/storage/maintenance.py` e dalla retention policy del `BackupManager`.

## Da non fare

- **Non** aggiungere file sorgente Python qui. Il nuovo codice backend va in `Programma_CS2_RENAN/backend/<dominio>/`.
- **Non** trattare questo come path di import. `from backend.foo import ...` non si risolverà — la radice del pacchetto è `Programma_CS2_RENAN`.
- **Non** committare il contenuto di `backend/storage/`. I file `*.db` generati sono in gitignore.

## Documentazione correlata

- Pacchetto backend dell'applicazione: `Programma_CS2_RENAN/backend/README.md`
- Specifiche dello storage layer: `Programma_CS2_RENAN/backend/storage/README.md`
- Architettura tri-database: `CLAUDE.md` e `REFERENCE.md`
