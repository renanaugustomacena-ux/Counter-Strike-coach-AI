> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Strumenti di Progetto a Livello Root

> **Autorità:** Regola 3 (Zero-Regressione), Regola 6 (Governance delle Modifiche)
> **Skill:** `/validate`, `/pre-commit`

Strumenti di progetto a livello root per validazione, diagnostica, orchestrazione di build e manutenzione del Macena CS2 Analyzer. Lo strumento più critico è `headless_validator.py`, che costituisce il gate di regressione obbligatorio pre-commit.

## Inventario dei File

La directory contiene **55 strumenti Python** più l'harness `fuzz/` ([README](fuzz/README.md)) e `hltv_stealth_init.js` (snippet di stealth browser per il fetching da HLTV). I più importanti:

| File | Scopo | Categoria |
|------|-------|-----------|
| `headless_validator.py` | Gate di regressione con 41 fasi di controllo distinte | Validazione |
| `dead_code_detector.py` | Moduli orfani, definizioni duplicate, import obsoleti | Validazione |
| `audit_scanner.py` | Audit meccanico dei sottosistemi (LOC, import, complessità, TODO) | Validazione |
| `verify_all_safe.py` | Scopre ed esegue tutti gli strumenti sicuri (sola lettura), saltando quelli non sicuri/interattivi | Validazione |
| `portability_test.py` | Controlli di portabilità cross-platform | Validazione |
| `Feature_Audit.py` | Audit di allineamento delle feature (parser vs pipeline ML) | Validazione |
| `run_console_boot.py` | Verifica di boot da console | Validazione |
| `verify_main_boot.py` | Verifica di boot dell'applicazione principale | Validazione |
| `build_pipeline.py` | Orchestrazione pipeline di build (5 stadi) | Build |
| `audit_binaries.py` | Integrità binari post-build (SHA-256) | Build |
| `db_health_diagnostic.py` | Diagnostica salute database (10 sezioni) | Database |
| `migrate_db.py` | DEPRECATO — patcher pre-Alembic (usare `alembic upgrade head`) | Database |
| `reset_pro_data.py` | Reset dati giocatori professionisti (idempotente) | Database |
| `dev_health.py` | Orchestratore salute sviluppo | Manutenzione |
| `Sanitize_Project.py` | Sanitizzazione progetto (rimozione dati locali) | Manutenzione |
| `observe_training_cycle.py` | Diagnostica end-to-end del ciclo di addestramento (acquisizione → conoscenza) | Osservabilità |
| `ui_screenshot.py` | Harness di screenshot offscreen per schermate reali (dati fixture) | UI |
| `ui_gallery.py` | Renderer offscreen della galleria componenti (uno scatto per tema) | UI |
| `ui_fixtures.py` | Payload di fixture frame-realistici per l'harness UI | UI |
| `test_rap_lite.py` | Test di integrazione RAP-Lite (contratti dimensionali) | Test |
| `test_tactical_pipeline.py` | Test end-to-end della pipeline tactical viewer su un .dem reale | Test |
| `validate_coaching_pipeline.py` | Validazione end-to-end della pipeline di coaching | Test |

Il resto copre l'ingestione di demo professionali (`ingest_pro_demos.py`), la riparazione dati del monolite (`repair_*.py`, `tick_census.py`), il recupero shard e la ricostruzione del monolite (`d3_recover_shard_metadata.py`, `rebuild_monolith.py`), audit di disco in sola lettura (`d4_disk_hygiene_audit.py`), mining di esperienze/strategie (`mine_coaching_experience.py`, `mine_shard_strategies.py`), seeding metadati HLTV (`seed_hltv_top_n.py`, `seed_hltv_apply_vision.py`), backfill di date partite e statistiche round (`backfill_match_dates.py`, `populate_match_results.py`, `populate_round_stats.py`), export CSV elite (`build_elite_csvs.py`), segnalazione ghost-player (`flag_ghost_players.py`), manutenzione giocatori pro (`rescrape_placeholder_pros.py`, `sync_pro_players.py`), unione demo-pool (`merge_demo_pool.py`), wipe sicuro per re-ingestione (`wipe_for_reingest_safe.py`), generazione design-token (`gen_design_tokens.py`), build web (`build_web.py`), purge dati RAG di default (`purge_default_stats_rag.py`), pinning della supply-chain (`sbom_generator.py`, `verify_lock_hashes.py`, `refresh_model_pins.py`, `refresh_compose_digests.py`), scansione di policy di sicurezza e drift (`policy_runner.py`, `drift_detector.py`), e valutazioni offline (`eval_harness.py`, `coach_answer_eval.py`).

## `headless_validator.py` --- Il Gate di Regressione

Questo è lo strumento più importante dell'intero progetto (~2.900 righe). Esegue **41 fasi di controllo distinte** (fasi con banner numerate 1–26 — la Fase 19 è inutilizzata — più sotto-fasi con lettera 3b–3l e 6b–6f; la Fase 9 è la validazione tabellare dei contratti cross-modulo) e deve terminare con codice di uscita 0 prima di qualsiasi commit. È inoltre collegato a `.pre-commit-config.yaml` come hook pre-push.

### Fasi di Validazione

| Fase | Cosa Controlla |
|------|---------------|
| 1. Environment | La root del progetto e le directory critiche esistono |
| 2. Core Imports | I moduli core si importano senza errori |
| 3, 3b–3l. Backend Imports | Salute degli import per pacchetto: storage, processing, NN, analysis, coaching, services, knowledge, control, data sources, ingestion & onboarding, ingestion pipelines, reporting & observability |
| 4. Database Schema | Lo schema del database in memoria corrisponde alle definizioni SQLModel |
| 5. Config & Data Files | `map_config.json` valido, tipi di `get_setting()`, METADATA_DIM==25, allineamento feature |
| 6. ML Smoke | Istanziazione del modello e forward pass |
| 6b–6f. Smoke Sub-phases | Baselines, adattatore formato demo, rilevamento GPU, pipeline di training, pipeline di coaching |
| 7. UI Components (Headless) | I componenti Qt/PySide6 si importano in modalità headless |
| 8. Cross-Platform | I percorsi di codice specifici per OS risolvono correttamente |
| 9. Cross-Module Contracts | I contratti delle API pubbliche corrispondono alle implementazioni |
| 10. Deep ML Invariants | METADATA_DIM=25, OUTPUT_DIM=10, forme dei layer |
| 11. Database Model Integrity | Registro delle tabelle, colonne, indici |
| 12. Code Quality Scanning | Rilevamento di anti-pattern (inclusi `print()` spurie) |
| 13. Package Structure & Config | `__init__.py` in tutti i pacchetti, integrità della configurazione |
| 14. Feature Pipeline Consistency | Il Vectorizer produce vettori a 25 dimensioni |
| 15. Dependency & Environment | Le dipendenze fissate sono importabili |
| 16. RAP Coach & Perception | Forward pass del modello RAP e pipeline |
| 17. Belief Model & Analysis Engines | Contratti dei motori di analisi, intervalli di probabilità |
| 18. MLControlContext & Training Control | Cablaggio pause/resume/stop |
| 20. Shared Utilities | Import di utilità condivise e moduli mancanti |
| 21. Integrity & Security Scanning | Manifest SHA-256, nessun segreto hardcoded |
| 22. Configuration Consistency | Lo schema del file di impostazioni corrisponde alle chiavi attese |
| 23. Advanced Code Quality | Complessità ciclomatica, rilevamento codice duplicato |
| 24. Qt Frontend Imports | Import di schermate/viewmodel dell'app Qt |
| 25. Design Token Freshness | I design token generati sono aggiornati |
| 26. Web Marquee Scaffold Health | Integrità dello scaffold dell'app web |

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

### `audit_binaries.py` --- Integrità Post-Build

Calcola gli hash SHA-256 di tutti i file nell'output di build e li confronta con i valori attesi. Rileva manomissioni o build incomplete.

## Strumenti Database

### `db_health_diagnostic.py` --- Diagnostica in 10 Sezioni

| Sezione | Cosa Controlla |
|---------|---------------|
| 1 | Salute strutturale — schema e vincoli |
| 2 | Controllo integrità — rilevamento corruzione (`PRAGMA integrity_check`) |
| 3 | Verifica modalità WAL e journal |
| 4 | Consistenza dei dati e stabilità logica (duplicati, orfani, valori impossibili) |
| 5 | Salute pipeline di ingestione (stato dei task, task bloccati, cross-DB) |
| 6 | Salute delle prestazioni — copertura indici e verifica full-scan nel piano di query |
| 7 | Osservabilità — copertura dei metadati diagnostici |
| 8 | Database statistiche pro HLTV |
| 9 | Prontezza pipeline ML — CoachState |
| 10 | Riepilogo storage |

### `migrate_db.py` --- DEPRECATO

Mantenuto solo come archivio storico (R2-11). Patcha database pre-Alembic aggiungendo 5 colonne a `CoachState`; quello schema è ora gestito dalle revisioni Alembic `8c443d3d9523` e `3c6ecb5fe20e`. Usare `alembic upgrade head` per tutte le migrazioni di schema.

### `reset_pro_data.py` --- Reset Dati Professionisti

Reset multi-fase e idempotente per un nuovo ciclo di ingestione e addestramento. Svuota le tabelle dati di `database.db` + CoachState, `hltv_metadata.db` (saltabile con `--preserve-hltv`), `knowledge_graph.db`, cache, checkpoint dei modelli, shard per-match e stato di sincronizzazione.

## Manutenzione del Progetto

### `dev_health.py` --- Orchestratore di Salute

Esegue più strumenti in sequenza e produce un report di salute unificato:
1. Headless validator (sempre; `--quick` esegue solo questo)
2. Dead code detector (`--strict`)
3. Audit di allineamento feature
4. Test di portabilità (solo con `--full`)

### `Sanitize_Project.py` --- Pulizia Stato Locale

Rimuove tutti i dati specifici dell'utente e locali per una distribuzione pulita:
- `Programma_CS2_RENAN/backend/storage/database.db` (database locale principale)
- `Programma_CS2_RENAN/backend/storage/hltv_metadata.db`
- `Programma_CS2_RENAN/backend/storage/match_data/` (shard SQLite per-match)
- `models/` (checkpoint ML)
- directory `logs/`
- `hltv_sync.pid` obsoleto

## Utilizzo

```bash
# Attivare l'ambiente virtuale
source .venv/bin/activate

# Validazione headless (eseguire prima di ogni commit)
python tools/headless_validator.py

# Controllo salute sviluppo
python tools/dev_health.py

# Controllo salute database
python tools/db_health_diagnostic.py

# Controllo portabilità
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
- Il headless validator è il gate di regressione non negoziabile --- se fallisce, il commit viene bloccato
- Gli strumenti database sono sicuri da eseguire su dati di produzione (usano query in sola lettura se non esplicitamente indicato)
- `Sanitize_Project.py` è distruttivo --- rimuove database locali e impostazioni. Usare con cautela.
- Gli strumenti terminano con codice 0 in caso di successo, non-zero in caso di errore
- L'orchestratore `dev_health.py` fornisce il controllo di salute più completo con un singolo comando
