> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Test di Verifica e Forensi a Livello Root

> **Autorità:** Regola 3 (Zero-Regressione)
> **Skill:** `/correctness-check`

Test di verifica e forensi a livello root per componenti critici del sistema Macena CS2 Analyzer. Questi test complementano la suite di test principale in `Programma_CS2_RENAN/tests/` con verifiche di livello superiore orientate all'integrazione che operano su dati reali simili a quelli di produzione.

## Struttura della Directory

```
tests/
├── conftest.py                     # Configurazione pytest a livello root e fixture
├── verify_chronovisor_logic.py     # Verifica logica Chronovisor
├── verify_chronovisor_real.py      # Chronovisor con dati demo reali
├── verify_csv_ingestion.py         # Verifica pipeline ingestion CSV
├── verify_map_integration.py       # Integrazione mappe e dati spaziali
├── verify_reporting.py             # Pipeline reporting (PDF, grafici)
├── verify_superposition.py         # Verifica rete superposition
├── setup_golden_data.py            # Configurazione dati golden per test
└── forensics/                      # Script di debug e diagnostica
    ├── check_db_status.py          # Diagnostica connettività database
    ├── check_failed_tasks.py       # Analisi fallimenti task di ingestion
    ├── debug_env.py                # Debug variabili d'ambiente
    ├── debug_nade_cols.py          # Debug colonne granate
    ├── debug_parser_fields.py      # Validazione campi demo parser
    ├── forensic_parser_test.py     # Investigazione comportamento parser
    ├── probe_missing_tables.py     # Verifica completezza schema
    ├── test_skill_logic.py         # Validazione sistema skill
    ├── verify_map_dimensions.py    # Verifica limiti mappe
    └── verify_spatial_integrity.py # Consistenza dati spaziali
```

## Categorie di Test

### Test di Verifica (Principali)

Questi test verificano il comportamento critico del sistema utilizzando dati reali:

| File di Test | Cosa Verifica | Dati Necessari |
|-----------|-----------------|---------------|
| `verify_chronovisor_logic.py` | Rilevamento scala temporale, deduplicazione tick, interpolazione replay | Nessuno (livello unit) |
| `verify_chronovisor_real.py` | Pipeline Chronovisor completa con file `.dem` reali | File demo reali |
| `verify_csv_ingestion.py` | Pipeline importazione CSV (statistiche esterne → database) | File CSV in `data/external/` |
| `verify_map_integration.py` | Trasformazioni coordinate mappa, gestione Z-cutoff, risoluzione landmark | `data/map_config.json` |
| `verify_reporting.py` | Generazione PDF, rendering heatmap, grafici momentum | Database con dati match |
| `verify_superposition.py` | Forward pass SuperpositionLayer, flusso gradienti | Nessuno (tensori sintetici) |
| `setup_golden_data.py` | Crea snapshot di dati di riferimento per test di regressione | Database con dati match |

### Script Forensi

La subdirectory `forensics/` contiene script diagnostici per investigare problemi specifici:

| Script | Scopo |
|--------|---------|
| `check_db_status.py` | Testa connettività database, modalità WAL, esistenza tabelle |
| `check_failed_tasks.py` | Interroga la tabella `IngestionTask` per task falliti con dettagli errore |
| `debug_env.py` | Stampa le variabili d'ambiente rilevanti per l'applicazione |
| `debug_nade_cols.py` | Verifica le colonne relative alle granate nelle tabelle dati tick |
| `debug_parser_fields.py` | Valida i nomi dei campi demoparser2 rispetto allo schema atteso |
| `forensic_parser_test.py` | Investigazione approfondita del comportamento del parser su file demo specifici |
| `probe_missing_tables.py` | Confronta le definizioni SQLModel con lo schema effettivo del database |
| `test_skill_logic.py` | Valida la logica di selezione e ponderazione delle skill di coaching |
| `verify_map_dimensions.py` | Controlla limiti mappa, fattori di scala e intervalli coordinate |
| `verify_spatial_integrity.py` | Validazione incrociata dati spaziali tra `map_config.json` e `spatial_data.py` |

## `conftest.py` — Configurazione Root

Il `conftest.py` a livello root fornisce:

- **Configurazione percorsi** — inserisce la root del progetto in `sys.path` affinché tutte le importazioni vengano risolte correttamente
- **Fixture root progetto** — percorso `PROJECT_ROOT` disponibile per tutti i test
- **Isolamento ambiente** — garantisce che i test non modifichino accidentalmente i dati di produzione

```python
# conftest.py semplificato
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

## Filosofia di Test

1. **Approccio forense** — i test investigano percorsi dati reali e comportamento effettivo del sistema, non mock sintetici
2. **Nessun dato sintetico** — tutti i test usano file demo reali o dati equivalenti a produzione dove possibile
3. **Skip se non disponibile** — i test saltano correttamente (tramite `pytest.skip()`) quando i dati richiesti mancano
4. **Copertura end-to-end** — focus su punti di integrazione e workflow cross-modulo
5. **Non distruttivo** — i test non modificano mai database di produzione o file di configurazione

## Relazione con la Suite di Test Principale

| Aspetto | `tests/` (root) | `Programma_CS2_RENAN/tests/` (principale) |
|--------|-----------------|--------------------------------------|
| Focus | Integrazione, E2E, forensi | Test unitari, test di modulo |
| Numero test | ~18 script | 1.515+ test in 79 file |
| Dati | Demo reali, DB di produzione | DB in memoria, mock, fixture |
| Framework | pytest + script standalone | pytest con ricco ecosistema fixture |
| Frequenza esecuzione | Su richiesta, debugging | Ogni commit (hook pre-commit) |

## Esecuzione dei Test

```bash
# Attiva l'ambiente virtuale
source /home/renan/.venvs/cs2analyzer/bin/activate

# Esegui tutti i test di verifica tramite pytest
python -m pytest tests/ -v

# Esegui uno script di verifica specifico direttamente
python tests/verify_chronovisor_real.py

# Esegui diagnostica forense
python tests/forensics/check_db_status.py

# Configura dati golden per test di regressione
python tests/setup_golden_data.py
```

## Note di Sviluppo

- Questi test NON fanno parte del gate pre-commit — richiedono dati reali che potrebbero non essere disponibili in CI
- Gli snapshot dei dati golden dovrebbero essere rigenerati dopo modifiche significative alla pipeline di ingestion
- Gli script forensi sono pensati per il debugging interattivo, non per test automatizzati
- Quando si aggiunge un nuovo test di verifica, seguire la convenzione di denominazione `verify_*.py`
- Tutti gli script forensi escono con codice 0 in caso di successo, diverso da zero in caso di errore
- La suite di test principale (`Programma_CS2_RENAN/tests/`) rappresenta il gate di regressione primario
