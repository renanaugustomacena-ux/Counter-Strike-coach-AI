# `backend/processing/validation/` — Gate di integrità dei dati

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 1 (Correctness), Rule 4 (Data Persistence)
> **Skill:** `/correctness-check`, `/data-lifecycle-review`

## Scopo

Questo package possiede i gate di validazione che proteggono ogni consumer a valle (training, inferenza, dashboard) da input malformati. I file qui girano ai confini di ingestione, ai confini di batch del training e all'avvio. Sono il punto in cui dati corrotti o non sicuri devono fallire forte e presto — la degradazione silenziosa è una linea rossa del progetto (Rule 1).

## Inventario dei file

| File | Modulo | Scopo | Export chiave |
|------|--------|---------|-------------|
| `__init__.py` | — | Re-export pubblici per il package validation. | — |
| `dem_validator.py` | DemValidator | Valida la struttura del file `.dem` prima del parse. Impone `MIN_DEMO_SIZE = 10 MB` (invariante `DS-12`), controlla i magic byte, rifiuta file troncati. | `DemValidator`, `validate_dem_file()` |
| `drift.py` | Drift detection | Rilevamento statistico del drift tra distribuzioni di feature dei giocatori. Confronta la distribuzione rolling delle ultime N partite con la baseline storica; segnala quando il p-value del test KS supera una soglia. | `detect_feature_drift()`, `DriftReport` |
| `sanity.py` | Sanity check | Asserzioni runtime leggere sullo stato a livello di tick (giocatori vivi hanno HP > 0, giocatori morti hanno HP = 0, valore equipaggiamento non negativo, ...). | `assert_tick_sanity()` |
| `schema.py` | Schema | Validatori JSON schema per l'ingestione di sorgenti tournament. | `TOURNAMENT_JSON_SCHEMA`, `validate_tournament_json()` |

## Dove gira ogni validatore

```
File .dem arriva nella cartella di ingest
    +-- DemValidator.validate_dem_file()           [dem_validator.py]
    |     - rifiuta file < MIN_DEMO_SIZE
    |     - rifiuta file con magic byte errati
    |     - rifiuta file troncati
    |
    +-- la pipeline parsa il demo (demoparser2)
    |
    +-- per tick: assert_tick_sanity()              [sanity.py]
    |     - bound HP / armor / equipment_value
    |     - coerenza stato vivo vs morto
    |
    +-- righe per tick persistite in SQLite per match

Feed JSON di tournament
    +-- validate_tournament_json(payload)          [schema.py]
    |     - chiavi richieste presenti
    |     - chiavi per mappa presenti
    |     - coercizione safe-int (DS-04)

Confine della batch di training
    +-- detect_feature_drift(...)                  [drift.py]
    |     - test KS sulla distribuzione rolling
    |     - segnala feature dei giocatori sospette prima del training
```

## Invarianti critiche

| ID | File / riga | Invariante |
|----|-------------|-----------|
| `DS-12` | `dem_validator.py` | `MIN_DEMO_SIZE = 10 MB`. File più piccoli vengono rifiutati (i demo CS2 reali sono tipicamente ≥ 50 MB). |
| `DS-04` | `schema.py` | `_safe_int()` coerce valori JSON non numerici a `0` invece di sollevare eccezione. |
| `P-VEC-02` / `P3-A` | `vectorizer.py` upstream | Clamp NaN / Inf + > 5 % per batch → `DataQualityError`. La validazione qui assicura che il gate upstream non possa essere aggirato. |

## Convenzioni

- **Fallire forte.** I validatori sollevano eccezioni tipizzate (`DemValidationError`, `SchemaValidationError`, `DataQualityError`) — mai un `None` silenzioso.
- **Funzioni pure dove possibile.** I validatori prendono input e restituiscono un verdetto; non scrivono su disco né sul database.
- **Logging strutturato.** Tutti i fallimenti loggano via `get_logger("cs2analyzer.validation.<module>")` con un codice di errore stabile così le dashboard possono aggregare.
- **Controlli economici per primi.** Ordinare le asserzioni dal più economico (size, magic byte) al più costoso (test statistici) così un file rotto fallisce prima che girino i percorsi costosi.

## Aggiungere un nuovo validatore

1. Inserirlo in questo package, un file per concern.
2. Definire una classe di eccezione tipizzata (`<Domain>ValidationError`) e usarla per tutte le modalità di fallimento — mai sollevare `RuntimeError`.
3. Aggiungere una riga alla tabella inventario qui sopra con uno scopo in una riga.
4. Cablarlo nella pipeline al **primo** confine in cui il dato sbagliato potrebbe arrivare.
5. Fornire un unit test in `Programma_CS2_RENAN/tests/test_<domain>_validation.py`.

## Da non fare

- Non coercere silenziosamente input malformati in valori "best-effort" senza registrare la deviazione in `DataLineage` / `DataQualityMetric`. La coercizione silenziosa viola Rule 1.
- Non duplicare `MIN_DEMO_SIZE`. La costante vive qui; tutti gli altri lo importano.
- Non usare i validatori per controlli speculativi a tempo di inferenza ("se il dato sembra strano, salta"). I validatori decidono; il codice a valle rispetta la decisione.

## Correlati

- Demo parser: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Feature engineering: `Programma_CS2_RENAN/backend/processing/feature_engineering/README.md`
- Modulo data quality (lato training): `Programma_CS2_RENAN/backend/nn/data_quality.py`
- Lineage & metriche: `backend/storage/db_models.DataLineage`, `DataQualityMetric`
- Package parent: `Programma_CS2_RENAN/backend/processing/README.md`
