# Implementazioni Pipeline di Ingestion

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorevolezza:** `Programma_CS2_RENAN/ingestion/pipelines/`

## Introduzione

Questo pacchetto contiene le pipeline di ingestion concrete che trasformano le
fonti dati grezze in righe strutturate nel database.  Ogni pipeline gestisce un
formato di input specifico -- file replay `.dem` dalle partite dell'utente,
file `.dem` da partite professionali, e export JSON strutturati da database di
tornei.  Le pipeline condividono un flusso comune a sette fasi (discovery,
validation, parsing, enrichment, persistence, registration, archival) ma
divergono nella logica di arricchimento e nelle tabelle di destinazione.

## Inventario File

| File | Scopo | API Pubblica Principale |
|------|-------|-------------------------|
| `__init__.py` | Marker pacchetto (vuoto) | -- |
| `user_ingest.py` | Pipeline ingestion demo utente | `ingest_user_demos(source_dir, processed_dir)` |
| `json_tournament_ingestor.py` | Processore batch JSON tornei | `process_tournament_jsons(json_dir, output_csv)` |
| `README.md` | Documentazione (Inglese) | -- |
| `README_IT.md` | Documentazione (Italiano) | -- |
| `README_PT.md` | Documentazione (Portoghese) | -- |

## Architettura e Concetti

### Il Flusso di Ingestion a Sette Fasi

Ogni pipeline segue questa sequenza canonica.  Le fasi possono essere implicite
nelle pipeline piu' semplici ma l'ordine logico e' sempre preservato:

1. **Discovery** -- scansione della directory sorgente per file non elaborati
   (`.dem` o `.json`).  Il `DemoRegistry` da `ingestion/registry/` viene
   consultato per saltare i file gia' ingeriti.
2. **Validation** -- verifica dell'integrita' del file.  Per i file `.dem`
   questo significa controllare la dimensione minima
   (`MIN_DEMO_SIZE = 10 MB`, invariante DS-12).  Per i file JSON l'helper
   `_validate_tournament_json()` verifica le chiavi top-level richieste
   (`id`, `slug`, `match_maps`) e le chiavi per-map.
3. **Parsing** -- estrazione di dati strutturati.  I file demo sono analizzati
   da `backend/data_sources/demo_parser.parse_demo()` (supportato da
   `demoparser2`).  I file JSON sono caricati direttamente con `json.load()`.
4. **Enrichment** -- calcolo di statistiche derivate.  Le pipeline utente
   chiamano `extract_match_stats()` da `base_features.py`.  Le pipeline torneo
   calcolano accuratezza e rating economico per-round inline.
5. **Persistence** -- scrittura dei risultati nel database.  Le pipeline utente
   eseguono upsert di righe `PlayerMatchStats` via `DatabaseManager`.  Le
   pipeline torneo scrivono su CSV per elaborazione downstream.
6. **Registration** -- marcatura del file come elaborato nel `DemoRegistry`
   cosi' che le esecuzioni future lo saltino.
7. **Archival** -- spostamento dei file ingeriti con successo nella directory
   `processed_dir` per mantenere pulita la directory sorgente.

### `user_ingest.py` in Dettaglio

La pipeline di ingestion utente gestisce file `.dem` registrati dalle partite
CS2 del giocatore locale.  E' la pipeline primaria per il coaching personale.

**Punto di ingresso:** `ingest_user_demos(source_dir: Path, processed_dir: Path)`

Flusso interno:

1. Glob di `source_dir` per file `*.dem`.
2. Per ogni file, chiama `_process_single_user_demo()` che racchiude l'intera
   pipeline in un try/except cosi' che un file corrotto non interrompa il batch.
3. `parse_demo()` restituisce un `DataFrame` di dati a livello round.
4. `extract_match_stats()` aggrega in un dizionario statistiche piatto.
5. Un oggetto ORM `PlayerMatchStats` viene creato con `is_pro=False` e il nome
   giocatore letto da `get_setting("CS2_PLAYER_NAME")`.
6. `db_manager.upsert()` persiste la riga (insert o update on conflict).
7. `_trigger_ml_pipeline()` importa lazily `run_ml_pipeline` da
   `run_ingestion.py` per evitare import circolari, poi esegue il passo di
   arricchimento ML (vettorizzazione feature, inferenza modello).
8. `_archive_user_demo()` sposta il file in `processed_dir` solo dopo che
   tutti i passi precedenti sono riusciti (invariante R3-H03).

**Limitazione importante (F6-19):** Questa pipeline salva solo
`PlayerMatchStats` di base.  `RoundStats`, eventi e dati tick-level
richiedono il percorso di arricchimento completo in `run_ingestion.py`
(`enrich_from_demo()` e `_extract_and_store_events()`).

### `json_tournament_ingestor.py` in Dettaglio

L'ingestor JSON tornei elabora export JSON strutturati che contengono la
gerarchia match/map/round/team.

**Punto di ingresso:** `process_tournament_jsons(json_dir: str, output_csv: str)`

Flusso interno:

1. Glob di `json_dir` per file `*.json`.
2. Ogni file viene validato da `_validate_tournament_json()`.
3. La struttura annidata viene appiattita attraverso una catena di estrattori:
   `_extract_match_stats()` -> `_extract_map_stats()` ->
   `_extract_game_stats()` -> `_extract_round_stats()` ->
   `_build_flat_stat()`.
4. I campi numerici passano attraverso `_safe_int()` (invariante DS-04) per
   gestire None, stringhe e altri valori JSON non numerici.
5. Le metriche derivate sono calcolate inline: `accuracy = hits / shots`,
   `econ_rating = damage / money_spent`.
6. La lista completa di statistiche piatte viene scritta in CSV tramite
   `pandas.DataFrame`.
7. Il progresso viene loggato ogni 100 file.

Questa pipeline e' standalone: puo' essere eseguita come `__main__` con
percorsi hardcoded che puntano a `new_datasets/csgo_tournament_data/` e
output su `data/external/tournament_advanced_stats.csv`.

## Integrazione

### Dipendenze Upstream

| Dipendenza | Modulo |
|------------|--------|
| Demo parser | `backend/data_sources/demo_parser.parse_demo()` |
| Estrazione feature | `backend/processing/feature_engineering/base_features.extract_match_stats()` |
| Singleton database | `backend/storage/database.get_db_manager()` |
| Modelli ORM | `backend/storage/db_models.PlayerMatchStats` |
| Configurazione | `core/config.get_setting()` |
| Logging strutturato | `observability/logger_setup.get_logger()` |

### Consumatori Downstream

- **`run_ingestion.py`** -- l'orchestratore che chiama `run_ml_pipeline()`
  dopo l'ingestion delle demo utente.
- **`ingestion/registry/`** -- le pipeline consultano e aggiornano il registro
  demo.
- **`backend/nn/`** -- i modelli ML consumano le righe `PlayerMatchStats`
  prodotte da queste pipeline.

## Note di Sviluppo

- **Isolamento errori:** Ogni file viene elaborato nel proprio blocco
  try/except.  Una demo corrotta non interrompe l'intero batch.
- **Import lazy:** `_trigger_ml_pipeline()` usa un import a livello funzione
  per spezzare la dipendenza circolare tra `user_ingest` e `run_ingestion`.
- **Sicurezza archivio (R3-H03):** I file vengono spostati in `processed_dir`
  solo dopo che tutti i passi della pipeline sono riusciti.  Se un passo lancia
  un'eccezione, il file rimane nella directory sorgente per il retry alla
  prossima esecuzione.
- **Thread safety:** Le pipeline stesse non sono thread-safe.  Sono progettate
  per essere chiamate da un singolo thread (il daemon IngestionWatcher).  La
  sicurezza cross-process e' delegata a `DemoRegistry` tramite `FileLock`.
- **Logging strutturato:** Tutte le pipeline loggano via
  `get_logger("cs2analyzer.*")` con formato JSON e ID correlazione per
  l'osservabilita'.
- **Invariante DS-04:** L'helper `_safe_int()` nell'ingestor tornei converte
  tutti i campi numerici in modo sicuro, restituendo un default di `0` in caso
  di fallimento.
- **Invariante DS-12:** File demo piu' piccoli di `MIN_DEMO_SIZE` (10 MB)
  vengono rifiutati durante la validazione.  Le demo CS2 reali sono tipicamente
  50+ MB.
