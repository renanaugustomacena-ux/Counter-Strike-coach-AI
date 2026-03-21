# Registro File Demo e Gestione Lifecycle

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorevolezza:** `Programma_CS2_RENAN/ingestion/registry/`

## Introduzione

Questo pacchetto fornisce il tracking dei file demo e la gestione del lifecycle
per il sottosistema di ingestion.  La sua responsabilita' centrale e' rispondere
a una singola domanda: "questa demo e' gia' stata ingerita?"  La classe
`DemoRegistry` mantiene un file JSON persistente che registra l'insieme dei nomi
demo elaborati.  Il `DemoLifecycleManager` gestisce le operazioni post-ingestion,
specificamente la pulizia basata sul tempo dei file demo archiviati.

Insieme questi componenti assicurano che nessuna demo venga ingerita due volte
(deduplicazione) e che lo spazio disco venga recuperato automaticamente dopo un
periodo di retention configurabile.

## Inventario File

| File | Scopo | API Pubblica Principale |
|------|-------|-------------------------|
| `__init__.py` | Marker pacchetto (vuoto) | -- |
| `registry.py` | Registro persistente di deduplicazione demo | `DemoRegistry(registry_path)` |
| `lifecycle.py` | Pulizia file demo basata sul tempo | `DemoLifecycleManager(raw_dir, processed_dir)` |
| `schema.sql` | Riservato per futuro registro basato su SQL | -- |
| `README.md` | Documentazione (Inglese) | -- |
| `README_IT.md` | Documentazione (Italiano) | -- |
| `README_PT.md` | Documentazione (Portoghese) | -- |

## Architettura e Concetti

### `DemoRegistry` -- Motore di Deduplicazione

La classe `DemoRegistry` e' la singola fonte di verita' per quali demo sono
state gia' elaborate.  Persiste il suo stato come file JSON su disco e
fornisce accesso thread-safe e cross-process-safe.

**Costruttore:** `DemoRegistry(registry_path: Path)`

**Struttura dati interna:** Un `set` Python di stringhe nomi demo
(`self._processed`).  Il set viene serializzato in JSON come lista sotto la
chiave `"processed_demos"` e deserializzato nuovamente in set al caricamento
(F6-20) per lookup di appartenenza O(1).

**Metodi pubblici:**

| Metodo | Descrizione |
|--------|-------------|
| `is_processed(demo_name: str) -> bool` | Restituisce `True` se la demo e' gia' stata ingerita. Lookup set O(1). |
| `mark_processed(demo_name: str)` | Aggiunge la demo al set elaborati e persiste su disco. Nessuna operazione se gia' presente. |

**Modello di concorrenza (R3-08):**

Il registro usa una strategia di locking a due livelli:

1. **Thread lock** (`threading.Lock`) -- protegge il set in-memory
   `_processed` dall'accesso concorrente all'interno dello stesso processo.
2. **File lock** (`filelock.FileLock`) -- protegge il file JSON dall'accesso
   concorrente tra processi.  Il file di lock viene creato a
   `<registry_path>.lock`.

L'ordine di acquisizione dei lock e' sempre thread lock prima, poi file lock.
Questo ordine consistente previene i deadlock.

**Pattern scrittura atomica (R3-H04):**

Le scritture usano una strategia write-ahead per prevenire la corruzione:

1. Crea un backup del registro esistente (`.json.backup`).
2. Scrive il nuovo stato in un file temporaneo (`tempfile.mkstemp()`).
3. Sostituisce atomicamente il file originale tramite `os.replace()`.
4. Se un passo fallisce, il file temporaneo viene pulito e l'eccezione si
   propaga.

**Recovery da backup:**

Se il file registro primario e' corrotto (errore JSON decode), il loader
`_execute_registry_load()` tenta di ripristinare dal file `.json.backup`.  Il
backup viene validato per integrita' strutturale prima di essere utilizzato
(deve essere un dict con una lista `"processed_demos"`).  Solo se sia il
primario che il backup non sono disponibili il registro viene resettato a
vuoto -- questo viene loggato a livello CRITICAL poiche' significa che tutta
la storia di ingestion e' persa.

### `DemoLifecycleManager` -- Pulizia Disco

Il `DemoLifecycleManager` gestisce la policy di retention per i file demo
archiviati.  Dopo che una demo viene ingerita con successo, la pipeline la
sposta nella `processed_dir`.  Col tempo, questi file archiviati si accumulano
e consumano spazio disco.

**Costruttore:** `DemoLifecycleManager(raw_dir: Path, processed_dir: Path)`

**Metodi pubblici:**

| Metodo | Descrizione |
|--------|-------------|
| `cleanup_old_demos(days: int = 30)` | Elimina file `.dem` in `processed_dir` piu' vecchi di `days` giorni. |

La logica di pulizia (`_purge_expired_demos()`) itera su tutti i file `*.dem`
nella directory target, controlla il `st_mtime` di ogni file, e rimuove i file
che superano la soglia di retention.  Ogni eliminazione viene loggata a livello
INFO.

### `schema.sql` -- Riservato

Il file `schema.sql` e' riservato per una futura migrazione dal registro basato
su JSON al registro basato su SQL.  Attualmente vuoto.  Quando implementato,
definira' una tabella `demo_file_records` con colonne per percorso file, hash,
dimensione, tipo sorgente, stato lifecycle, codice errore, contatore retry e
timestamp.

## Integrazione

### Consumatori Upstream

| Consumatore | Utilizzo |
|-------------|----------|
| `ingestion/pipelines/user_ingest.py` | Chiama `is_processed()` prima dell'ingestion, `mark_processed()` dopo il successo |
| `ingestion/pipelines/json_tournament_ingestor.py` | Elaborazione batch con controlli registro |
| `run_ingestion.py` | Gestione registro a livello orchestratore |
| `core/session_engine.py` (IngestionWatcher) | Thread daemon che attiva pipeline e consulta il registro |

### Dipendenze

| Dipendenza | Scopo |
|------------|-------|
| `filelock` | Locking file cross-process (terze parti) |
| `observability/logger_setup.get_logger()` | Logging strutturato |

## Diagramma degli Stati Lifecycle

```
  [Nuovo File]
      |
      v
  is_processed()?
      |
  +---+---+
  |       |
  No      Si --> salta
  |
  v
  Pipeline esegue
      |
  +---+---+
  |       |
  OK    FAIL --> rimane in source_dir per retry
  |
  v
  mark_processed()
      |
  v
  Archiviato in processed_dir
      |
      v  (dopo periodo retention)
  cleanup_old_demos() --> rimosso
```

## Note di Sviluppo

- **F6-20 (conversione set):** Il formato JSON salva `processed_demos` come
  lista per compatibilita' di serializzazione.  Al caricamento, la lista viene
  immediatamente convertita in un `set` per lookup di appartenenza O(1).
  Questo e' importante perche' il registro puo' contenere migliaia di voci e
  viene controllato ad ogni tentativo di ingestion.
- **R3-08 (thread safety):** Il `_lock` (threading.Lock) e il `_file_lock`
  (FileLock) vengono sempre acquisiti nello stesso ordine per prevenire
  deadlock.  Il thread lock viene acquisito per primo, poi il file lock.
- **R3-H04 (scritture atomiche):** Il metodo `_save_inner()` usa
  `tempfile.mkstemp()` + `os.replace()` per garantire che il file registro non
  venga mai lasciato in uno stato di scrittura parziale.  Questo e' critico
  perche' un crash durante la scrittura corromprebbe altrimenti l'intera
  storia di ingestion.
- **Sicurezza backup:** Prima di ogni scrittura, una copia del registro
  corrente viene creata a `<path>.json.backup`.  Il backup viene validato al
  recovery per prevenire il ripristino da un backup corrotto.
- **Retention default:** Il periodo di retention di 30 giorni e' un
  compromesso conservativo tra spazio disco e la possibilita' di rianalizzare
  demo recenti.  Puo' essere sovrascritto tramite il parametro `days`.
- **Nessuna dipendenza database:** Il registro usa intenzionalmente un file
  JSON piatto anziche' SQLite.  Questo evita l'accoppiamento al sistema
  tri-database e mantiene il registro autocontenuto e portabile.
