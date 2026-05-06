# `backend/storage/datasets/` -- Namespace riservato

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** `Programma_CS2_RENAN/backend/storage/datasets/`
> **Stato:** Riservato -- attualmente vuoto, mantenuto come pacchetto Python.

## Perche esiste

Questo pacchetto e un namespace riservato per **wrapper di dataset** che presentano piu database SQLite per-match come un'interfaccia unificata e iteratore-friendly per il training ML. Allo stato di HEAD contiene solo `__init__.py` -- i wrapper non sono ancora stati introdotti.

Il percorso attuale di accesso ai dati per il training passa direttamente attraverso:

- `backend/storage/match_data_manager.py` -- `MatchDataManager` (file DB per-match)
- `backend/storage/database.py` -- `DatabaseManager` (monolite `database.db`)

Le future astrazioni dataset (es. un `RAPTickDataset` che incapsula query `MatchTickState` con batching, sharding e cache per `torch.utils.data.DataLoader`) vivranno qui.

## Inventario File

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto (vuoto). |

## Quando aggiungere codice qui

Aggiungi un modulo qui quando:

- Hai bisogno di un wrapper `Dataset` / `IterableDataset` attorno agli shard SQLite per-match.
- Il wrapper e abbastanza grande da meritare un proprio file (non far crescere `match_data_manager.py` indefinitamente).
- L'astrazione e generica tra piu consumer (training, valutazione, rilevamento drift).

Mantieni la logica dello storage-manager -- pool di engine, PRAGMA di connessione, migrazioni di schema -- dentro `match_data_manager.py` stesso.

## Da non fare

- Non collocare qui i pesi dei modelli ML (vanno sotto `Programma_CS2_RENAN/models/`).
- Non duplicare query helper da `match_data_manager.py`.
- Non rompere il contratto di pacchetto -- `__init__.py` deve restare importabile anche se vuoto.

## Correlati

- Match data manager: `backend/storage/match_data_manager.py`
- Panoramica del livello di storage: `backend/storage/README.md`
- Fetching dati di training: `backend/nn/training_orchestrator.py:_fetch_batches()`
