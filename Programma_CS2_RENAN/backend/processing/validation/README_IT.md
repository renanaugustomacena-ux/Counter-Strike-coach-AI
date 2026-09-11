# `backend/processing/validation/` -- Gate di integrita dei dati

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 1 (Correttezza), Regola 4 (Persistenza dei Dati)
> **Skill:** `/correctness-check`, `/data-lifecycle-review`

## Scopo

Questo package possiede i gate di validazione che proteggono ogni consumatore a valle (training, inferenza, dashboard) da input malformati. I file qui girano ai confini di ingestione, ai confini di batch del training e all'avvio. Sono il punto in cui dati corrotti o non sicuri devono fallire forte e presto -- la degradazione silenziosa e una linea rossa del progetto (Regola 1).

## Inventario dei file

| File | Modulo | Scopo | Export chiave |
|------|--------|-------|---------------|
| `__init__.py` | -- | Marcatore di pacchetto vuoto. | -- |
| `dem_validator.py` | DEMValidator | Valida la struttura del file `.dem` prima del parse: integrita del nome file (metacaratteri shell, `F2-26`), pre-screening formato limiti dimensione 100 KB -- 800 MB, magic byte (`PBDEMS2` CS2 / `HL2DEMO` CSGO), controllo troncamento. Deliberatamente piu permissivo del floor di ingestione `DS-12` (`MIN_DEMO_SIZE = 10 MB`, applicato in `data_sources/demo_format_adapter.py`). | `DEMValidator`, `DEMValidationError`, `validate_dem_file()` |
| `drift.py` | Rilevamento drift | Rilevamento statistico del drift tra distribuzioni di feature dei giocatori. Confronta una finestra rolling recente (default 10) contro la cronologia passata e segnala feature il cui z-score supera una soglia (default 2.5). `DRIFT_FEATURES` copre statistiche aggregate per partita; `TickFeatureDriftMonitor` copre il vettore di input del modello a 25-dim (`DRIFT-01`). | `detect_feature_drift()`, `DriftReport`, `DriftMonitor`, `TickFeatureDriftMonitor`, `should_retrain()` |
| `sanity.py` | Controlli di sanita | Controlli di intervallo su DataFrame demo parsati contro la tabella dei limiti `LIMITS` (kills, deaths, assists, ADR, headshot_pct, KAST). La modalita strict solleva `ValueError`; la modalita trim clamp gli outlier e auto-ripara KAST e headshot_pct in scala percentuale (`> 1.0` -> `/100`, `P-SAN-01`). | `validate_demo_sanity()`, `validate_and_trim()` |
| `schema.py` | Schema | Validazione strutturale versionata dell'output del demo parser (`SCHEMA_VERSION = 2`: statistiche core v1 + `accuracy`). | `get_active_schema()`, `validate_demo_schema()` |

## Dove gira ogni validatore

```
File .dem arriva nella cartella di ingest
    +-- validate_dem_file()                        [dem_validator.py]
    |     - rifiuta file fuori da 100 KB - 800 MB
    |     - rifiuta file con magic byte errati
    |     - rifiuta file troncati
    |
    +-- la pipeline parsa il demo (demoparser2)
    |
    +-- DataFrame parsato: validate_demo_schema()   [schema.py]
    |     - colonne richieste + tipi per SCHEMA_VERSION
    |
    +-- validate_demo_sanity() / validate_and_trim() [sanity.py]
    |     - limiti kills / deaths / assists / adr / headshot_pct / kast (LIMITS)
    |     - strict: solleva errore, non-strict: clamp outlier
    |
    +-- righe tick persistite in SQLite per-partita

Confine batch di training
    +-- detect_feature_drift(...)                  [drift.py]
    |     - confronto z-score su finestra rolling
    |     - segnala feature giocatore sospette prima del training
```

## Invarianti critiche

| ID | File / Riga | Invariante |
|----|-------------|-----------|
| `DS-12` | `data_sources/demo_format_adapter.py` | `MIN_DEMO_SIZE = 10 MB` floor di accettazione ingestione. `dem_validator.py` e un pre-screening formato deliberatamente piu permissivo (100 KB -- 800 MB). |
| `P-VEC-02` / `P3-A` | `vectorizer.py` upstream | Clamp NaN / Inf + > 5 % per batch -> `DataQualityError`. La validazione qui assicura che il gate upstream non possa essere aggirato. |
| `F-0019` (chiuso 2026-08-21) | `sanity.py` `LIMITS` | Sia `headshot_pct` che `kast` hanno bande in scala rapporto (0.0 -- 1.0) ed entrambi sono colonne auto-riparanti in `_RATIO_SELF_HEAL_COLUMNS` (`P-SAN-01`). Valori superiori a 1.0 vengono divisi per 100 e clamped. |

## Convenzioni

- **Fallire forte.** I validatori sollevano eccezioni tipizzate (`DEMValidationError`) o `ValueError` con un messaggio esplicito -- mai degradare silenziosamente.
- **Funzioni pure dove possibile.** I validatori prendono input e restituiscono un verdetto; non scrivono su disco ne sul database.
- **Logging strutturato.** `drift.py`, `sanity.py` e `schema.py` loggano via `get_logger("cs2analyzer.<modulo>")`; `dem_validator.py` non effettua logging e restituisce invece un verdetto esplicito `(is_valid, game_version, error_message)`.
- **Controlli economici per primi.** Ordinare le asserzioni dal piu economico (size, magic byte) al piu costoso (test statistici) cosi un file rotto fallisce prima che girino i percorsi costosi.

## Aggiungere un nuovo validatore

1. Inserirlo in questo package, un file per concern.
2. Definire una classe di eccezione tipizzata (`<Domain>ValidationError`) e usarla per tutte le modalita di fallimento -- mai sollevare `RuntimeError`.
3. Aggiungere una riga alla tabella inventario qui sopra con uno scopo in una riga.
4. Cablarlo nella pipeline al **primo** confine in cui il dato sbagliato potrebbe arrivare.
5. Fornire un unit test in `Programma_CS2_RENAN/tests/` (es. `test_dem_validator.py`, `test_drift_and_heuristics.py`).

## Da non fare

- Non coercere silenziosamente input malformati in valori "best-effort" senza registrare la deviazione in `DataLineage` / `DataQualityMetric`. La coercizione silenziosa viola Regola 1.
- Non duplicare `MIN_DEMO_SIZE`. La costante vive in `data_sources/demo_format_adapter.py`; tutti gli altri la importano.
- Non usare i validatori per controlli speculativi a tempo di inferenza ("se il dato sembra strano, salta"). I validatori decidono; il codice a valle rispetta la decisione.

## Correlati

- Demo parser: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Feature engineering: `Programma_CS2_RENAN/backend/processing/feature_engineering/README.md`
- Modulo data quality (lato training): `Programma_CS2_RENAN/backend/nn/data_quality.py`
- Lineage & metriche: `backend/storage/db_models.DataLineage`, `DataQualityMetric`
- Package parent: `Programma_CS2_RENAN/backend/processing/README.md`
