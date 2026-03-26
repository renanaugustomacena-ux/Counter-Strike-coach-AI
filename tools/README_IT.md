> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Strumenti di Progetto a Livello Root

> **Autorita:** Regola 3 (Zero-Regressione), Regola 6 (Governance delle Modifiche)
> **Skill:** `/validate`, `/pre-commit`

Strumenti di progetto a livello root per validazione, diagnostica, orchestrazione di build e manutenzione del Macena CS2 Analyzer. Lo strumento piu critico e `headless_validator.py`, che costituisce il gate di regressione obbligatorio pre-commit.

## Inventario dei File

| File | Scopo | Categoria |
|------|-------|-----------|
| `headless_validator.py` | 319 controlli di regressione in 24 fasi | Validazione |
| `dead_code_detector.py` | Moduli orfani, definizioni duplicate, import obsoleti | Validazione |
| `verify_all_safe.py` | Verifica di sicurezza su tutti i moduli | Validazione |
| `portability_test.py` | Controlli di portabilita cross-platform | Validazione |
| `Feature_Audit.py` | Audit allineamento feature (parser vs pipeline ML) | Validazione |
| `run_console_boot.py` | Verifica di boot da console | Validazione |
| `verify_main_boot.py` | Verifica di boot dell'applicazione principale | Validazione |
| `build_pipeline.py` | Orchestrazione pipeline di build (5 stadi) | Build |
| `audit_binaries.py` | Integrita binari post-build (SHA-256) | Build |
| `db_health_diagnostic.py` | Diagnostica salute database (10 sezioni) | Database |
| `migrate_db.py` | Migrazione database con backward compatibility | Database |
| `reset_pro_data.py` | Reset dati giocatori professionisti (idempotente) | Database |
| `dev_health.py` | Orchestratore salute sviluppo | Manutenzione |
| `Sanitize_Project.py` | Sanitizzazione progetto (rimozione dati locali) | Manutenzione |
| `observe_training_cycle.py` | Monitoraggio metriche di addestramento | Osservabilita |
| `test_rap_lite.py` | Test lite del modello RAP | Test |
| `test_tactical_pipeline.py` | Test pipeline di inferenza tattica | Test |
| `validate_coaching_pipeline.py` | Validazione pipeline di coaching end-to-end | Test |

## `headless_validator.py` --- Il Gate di Regressione

Questo e lo strumento piu importante dell'intero progetto. Esegue **319 controlli automatizzati in 24 fasi** e deve terminare con codice di uscita 0 prima di qualsiasi commit. E inoltre collegato come hook pre-commit.

### Fasi di Validazione

| Fase | Cosa Controlla |
|------|---------------|
| 1. Import Health | Tutti i moduli di produzione si importano senza errori |
| 2. Schema Integrity | Lo schema del database in memoria corrisponde alle definizioni SQLModel |
| 3. Config Loading | `get_setting()` e `get_credential()` risolvono correttamente |
| 4. ML Smoke Test | Istanziazione e forward pass per tutti i 6 tipi di modello |
| 5. UI Framework | PySide6 e Kivy si importano con successo |
| 6. Platform Compat | I percorsi di codice specifici per OS risolvono correttamente |
| 7. Contract Validation | I contratti delle API pubbliche corrispondono alle implementazioni |
| 8. ML Invariants | METADATA_DIM=25, INPUT_DIM=25, OUTPUT_DIM=10 |
| 9. DB Integrity | Conteggio tabelle, chiavi esterne, esistenza indici |
| 10. Code Quality | Formattazione Black, ordinamento isort |
| 11. Package Structure | `__init__.py` in tutti i pacchetti, nessun import circolare |
| 12. Feature Pipeline | FeatureExtractor produce vettori a 25 dimensioni |
| 13. RAP Forward Pass | Il forward pass del modello RAP Coach ha successo |
| 14. Belief Contracts | Le probabilita del modello belief nell'intervallo [0, 1] |
| 15. Circuit Breakers | Le soglie di errore si attivano correttamente |
| 16. Integrity Manifest | Gli hash SHA-256 corrispondono a `core/integrity_manifest.json` |
| 17. Security Scan | Nessun segreto o credenziale hardcoded |
| 18. Config Consistency | Lo schema del file di impostazioni corrisponde alle chiavi attese |
| 19. Advanced Quality | Complessita ciclomatica, rilevamento codice duplicato |
| 20-23. | Controlli specializzati aggiuntivi |

### Utilizzo

```bash
# Validazione standard (obbligatoria prima di ogni commit)
python tools/headless_validator.py

# Codice di uscita: 0 = tutti i controlli superati, non-zero = errori rilevati
echo $?
```

## Pipeline di Build

### `build_pipeline.py` --- Orchestrazione Build in 5 Stadi

```
Stadio 1: Sanitize  ->  Stadio 2: Test  ->  Stadio 3: Manifest  ->  Stadio 4: Compile  ->  Stadio 5: Audit
(pulisci artefatti)     (esegui test)      (genera hash)          (PyInstaller)         (verifica binario)
```

### `audit_binaries.py` --- Integrita Post-Build

Calcola gli hash SHA-256 di tutti i file nell'output di build e li confronta con i valori attesi. Rileva manomissioni o build incomplete.

## Strumenti Database

### `db_health_diagnostic.py` --- Diagnostica in 10 Sezioni

| Sezione | Cosa Controlla |
|---------|---------------|
| 1 | Verifica modalita WAL su tutti e 3 i database |
| 2 | Esistenza tabelle e conteggio righe |
| 3 | Integrita vincoli di chiave esterna |
| 4 | Copertura indici sulle colonne interrogate frequentemente |
| 5 | Metriche qualita dati (tassi NaN, valori anomali) |
| 6 | Stato migrazione Alembic |
| 7 | Consistenza database per-match |
| 8 | Completezza metadati HLTV |
| 9 | Utilizzo storage e dimensioni file |
| 10 | Salute del connection pool |

### `migrate_db.py` --- Migrazione Sicura

Avvolge le migrazioni Alembic con controlli di backward compatibility. Piu sicuro dell'esecuzione diretta di `alembic upgrade head`.

### `reset_pro_data.py` --- Reset Dati Professionisti

Reset multi-fase e idempotente dei dati dei giocatori professionisti. Sicuro da eseguire piu volte. Fasi: backup -> svuota tabelle -> reset stato sincronizzazione -> verifica.

## Manutenzione del Progetto

### `dev_health.py` --- Orchestratore di Salute

Esegue piu strumenti in sequenza e produce un report di salute unificato:
1. Headless validator
2. Dead code detector
3. Portability test
4. Feature audit

### `Sanitize_Project.py` --- Pulizia Stato Locale

Rimuove tutti i file specifici dell'utente e locali per una distribuzione pulita:
- `user_settings.json`
- `database.db` e file WAL/SHM
- Directory `logs/`
- Directory `__pycache__/`

## Utilizzo

```bash
# Attivare l'ambiente virtuale
source /home/renan/.venvs/cs2analyzer/bin/activate

# Validazione headless (eseguire prima di ogni commit)
python tools/headless_validator.py

# Controllo salute sviluppo
python tools/dev_health.py

# Controllo salute database
python tools/db_health_diagnostic.py

# Controllo portabilita
python tools/portability_test.py

# Rilevamento codice morto
python tools/dead_code_detector.py

# Audit allineamento feature
python tools/Feature_Audit.py

# Pipeline di build
python tools/build_pipeline.py

# Sanitizzazione progetto (ATTENZIONE: rimuove dati locali)
python tools/Sanitize_Project.py
```

## Note di Sviluppo

- Tutti gli strumenti devono essere eseguiti dalla directory root del progetto
- Il headless validator e il gate di regressione non negoziabile --- se fallisce, il commit viene bloccato
- Gli strumenti database sono sicuri da eseguire su dati di produzione (usano query in sola lettura se non esplicitamente indicato)
- `Sanitize_Project.py` e distruttivo --- rimuove database locali e impostazioni. Usare con cautela.
- Gli strumenti terminano con codice 0 in caso di successo, non-zero in caso di errore
- L'orchestratore `dev_health.py` fornisce il controllo di salute piu completo con un singolo comando
