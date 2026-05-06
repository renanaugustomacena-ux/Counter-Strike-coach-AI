# `backend/storage/models/` -- Namespace riservato

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** `Programma_CS2_RENAN/backend/storage/models/`
> **Stato:** Riservato -- attualmente vuoto, mantenuto come pacchetto Python.

## Perche esiste

Namespace riservato destinato a **classi dati specifiche del livello di storage**: cose come helper di row-mapping, DTO leggeri che mediano tra righe ORM SQLModel e consumer downstream, o tipi di risultato dei query-builder.

**Non** e il posto per le definizioni di tabella ORM SQLModel -- quelle vivono in `backend/storage/db_models.py`. Metterle qui creerebbe una doppia sorgente di verita confusa per il modello dati.

## Inventario File

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto (vuoto). |

## Quando aggiungere codice qui

Aggiungi un modulo qui quando:

- Hai un DTO storage-side che non mappa 1:1 a una tabella del database (es. un risultato di query appiattito, una proiezione di join).
- Il DTO e consumato da piu moduli e merita una sede unica.
- *Non* stai definendo una nuova tabella ORM -- quelle vanno in `db_models.py`.

## Confini (mantenerli puliti)

| Area | Vive in |
|------|---------|
| Classi tabella ORM (`SQLModel.table=True`) | `backend/storage/db_models.py` |
| Manager singleton (`get_db_manager()`, ecc.) | `backend/storage/database.py` |
| Pool engine SQLite per-match | `backend/storage/match_data_manager.py` |
| DTO e tipi di risultato storage-side | `backend/storage/models/` (questa directory) |

## Da non fare

- Non aggiungere qui nuove classi tabella ORM. Devono vivere in `db_models.py`.
- Non importare da questo pacchetto in modo eager -- pacchetti vuoti non devono apparire nell'API pubblica.
- Non collocare qui checkpoint di modelli di machine-learning. Quelli vivono in `Programma_CS2_RENAN/models/`.

## Correlati

- Definizioni ORM: `backend/storage/db_models.py`
- Panoramica del livello di storage: `backend/storage/README.md`
