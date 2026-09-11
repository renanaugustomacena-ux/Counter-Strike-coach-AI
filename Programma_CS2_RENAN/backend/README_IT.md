> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Backend -- Livello di Logica di Business Centrale

| Autorità | Livello di Competenza |
|----------|----------------------|
| Macena CS2 Analyzer | Domain-Driven Design, AI Coaching Pipeline |

---

## Panoramica

Il pacchetto `backend/` è il livello di logica di business centrale del Macena CS2 Analyzer.
È organizzato in **14 sotto-pacchetti** che seguono i principi del domain-driven design,
dove ogni sotto-pacchetto possiede il proprio dominio, invarianti dei dati e modalità di errore.

Il backend implementa l'**intera pipeline di coaching IA** end-to-end:

1. **Parsing demo grezzo** -- i file `.dem` vengono decodificati in dati strutturati tick/eventi.
2. **Feature engineering** -- i dati a livello di tick vengono proiettati in un vettore feature unificato a 25 dimensioni.
3. **Inferenza reti neurali** -- i modelli addestrati (JEPA, RAP Coach, AdvancedCoachNN) valutano e classificano il comportamento dei giocatori.
4. **Output di coaching** -- i risultati dell'analisi vengono trasformati in consigli di coaching azionabili in linguaggio naturale.

Nessuna logica UI risiede qui. Il backend espone le sue funzionalità attraverso un **livello di servizi**
(`services/`) consumato dall'interfaccia PySide6/Qt (`apps/qt_app/`).

---

## Inventario dei Sotto-Pacchetti

| # | Sotto-Pacchetto | File | Scopo | Punti di Ingresso Chiave |
|---|-----------------|------|-------|--------------------------|
| 1 | `analysis/` | 12 | Motori di teoria dei giochi: belief model, tracciamento momentum, win probability, analisi entropia, indice di inganno, rilevamento punti ciechi | `belief_model.py`, `win_probability.py`, `momentum.py` |
| 2 | `coaching/` | 9 | Pipeline di coaching a 4 modalità: COPER basato su esperienza, Hybrid (NN + regole), RAG retrieval-augmented, correzioni tradizionali | `hybrid_engine.py`, `correction_engine.py`, `pro_bridge.py` |
| 3 | `control/` | 5 | Gestione ciclo di vita daemon, governance coda di ingestion, controllo training ML, limiti risorse database | `ingest_manager.py`, `ml_controller.py`, `db_governor.py` |
| 4 | `data_sources/` | 16 | Integrazione dati esterni: demo parser (demoparser2), scraper statistiche pro HLTV (FlareSolverr/Docker), Steam API, FACEIT API | `demo_parser.py`, `hltv/`, `steam_api.py`, `faceit_api.py` |
| 5 | `ingestion/` | 5 | Monitoraggio file runtime per nuove demo, risoluzione date partita, migrazione CSV da formati legacy, governance risorse OS | `watcher.py`, `resource_manager.py`, `csv_migrator.py`, `match_date_resolver.py` |
| 6 | `knowledge/` | 8 | Knowledge base RAG con indice vettoriale FAISS, banca esperienze COPER, mining demo pro, grafo di conoscenza tattica | `rag_knowledge.py`, `experience_bank.py`, `vector_index.py` |
| 7 | `knowledge_base/` | 2 | Sistema di aiuto in-app: indicizzazione documenti Markdown e ricerca testuale per la schermata di aiuto dell'interfaccia | `help_system.py` |
| 8 | `nn/` | 53 | Architetture reti neurali (6 tipi di modello), pipeline di training, inferenza, EMA, early stopping, data quality, RAP Coach, JEPA | `jepa_model.py`, `rap_coach/`, `train.py`, `config.py` |
| 9 | `onboarding/` | 2 | Flusso di progressione nuovi utenti: staging basato sul conteggio demo e gating di prontezza del coach | `new_user_flow.py` |
| 10 | `processing/` | 30 | Feature engineering (vettore 25-dim), calcolo baseline, baseline pro, generazione heatmap, validazione, arricchimento tick | `feature_engineering/vectorizer.py`, `baselines/`, `validation/` |
| 11 | `progress/` | 3 | Tracciamento longitudinale delle prestazioni del giocatore: calcolo del trend per-feature (pendenza, volatilità, confidenza) | `longitudinal.py`, `trend_analysis.py` |
| 12 | `reporting/` | 2 | Livello query analitiche per schermate UI: statistiche partite aggregate, riassunti trend, breakdown prestazioni | `analytics.py` |
| 13 | `services/` | 12 | Livello orchestrazione servizi: coaching service, analysis orchestrator, dialogue engine, integrazione LLM, gestione profilo, telemetria | `coaching_service.py`, `analysis_orchestrator.py`, `llm_service.py` |
| 14 | `storage/` | 14 | Persistenza tri-database (SQLite WAL): database manager, ORM SQLModel, backup, match data manager, state manager, telemetria remota | `database.py`, `db_models.py`, `match_data_manager.py` |

I conteggi file sono file `.py` ricorsivi (inclusi `__init__.py`), escluso `__pycache__`.

**Modulo di primo livello:** oltre ai sotto-pacchetti, la radice del pacchetto contiene `server.py` --
un **server FastAPI di utilità standalone** (endpoint di ingestion telemetria con rate limiting,
proxy Ollama). Come indicato nella sua docstring, **NON è collegato** al ciclo di vita dell'app: non è
importato né avviato da `main.py`, `session_engine.py` o `lifecycle.py`. Per utilizzarlo, eseguire
`uvicorn Programma_CS2_RENAN.backend.server:app` manualmente.

---

## Diagramma del Flusso Dati

Il backend elabora i dati attraverso quattro fasi concettuali, corrispondenti al
Quad-Daemon Engine (`core/session_engine.py`):

```
 WATCH          LEARN           THINK            SPEAK
 (Ingestione)   (Elaborazione)  (Analisi)        (Coaching)

 File .dem       Dati tick       Teoria dei giochi  Linguaggio naturale
 Statistiche     Vettore 25-dim  Inferenza NN       Output coaching
 HLTV            Baseline        Belief model       Consigli correttivi
 Steam API       Validazione     Win probability    Confronti pro

 data_sources/   processing/     analysis/        coaching/
 ingestion/      knowledge/      nn/              services/
 control/        storage/        progress/        reporting/
```

**Flusso dettagliato:**

```
[File Demo (.dem)]
       |
       v
  data_sources/demo_parser.py       -- Parsing demo binario grezzo
       |
       v
  processing/feature_engineering/   -- Estrazione vettore feature 25-dim
       |
       v
  storage/match_data_manager.py     -- Persistenza in database SQLite per partita
       |
       v
  nn/ (JEPA / RAP Coach)            -- Inferenza rete neurale
       |
       v
  analysis/ (11 moduli teoria giochi)-- Scoring pattern, rilevamento punti ciechi
       |
       v
  coaching/ (fallback a 4 livelli)  -- Generazione consigli di coaching
       |
       v
  services/coaching_service.py      -- Esposizione al livello UI
```

---

## Pattern Architetturali Chiave

### Fallback Coaching a 4 Livelli

La pipeline di coaching prova strategie progressivamente più semplici fino al successo:

| Priorità | Modalità | Sorgente | Condizione |
|----------|----------|----------|------------|
| 1 | **COPER** | Experience Bank + RAG + Riferimenti Pro | `USE_COPER_COACHING` (default True) + nome mappa + dati tick |
| 2 | **Hybrid** | Predizioni NN + knowledge retrieval | `USE_HYBRID_COACHING` (default False) + statistiche giocatore |
| 3 | **Traditional + RAG** | Correction engine + knowledge retrieval | `USE_RAG_COACHING` (default False) |
| 4 | **Traditional** | Correction engine puro basato su deviazioni | Sempre disponibile (fallback) |

### Gating Maturità a 3 Stadi

I modelli e la qualità del coaching evolvono attraverso tre stadi:

| Stadio | Nome | Comportamento |
|--------|------|---------------|
| 0 | **CALIBRATING** (0-49 demo) | Coaching prudente, moltiplicatore di confidenza 0.5 |
| 1 | **LEARNING** (50-199 demo) | Coaching base, moltiplicatore di confidenza 0.8 |
| 2 | **MATURE** (200+ demo) | Coaching completo, moltiplicatore di confidenza 1.0 |

### Decadimento Temporale Baseline

Le baseline delle abilità dei giocatori usano ponderazione a decadimento esponenziale
in modo che le prestazioni recenti contino più di quelle passate. Implementato da
`TemporalBaselineDecay` in `baselines/pro_baseline.py` (emivita 90 giorni, peso minimo 0.1).

### Vettore Feature Unificato a 25 Dimensioni

Tutti i modelli consumano lo stesso vettore a 25 elementi prodotto da `FeatureExtractor`
(`processing/feature_engineering/vectorizer.py`). Questa è la **singola fonte di verità**
per le definizioni delle feature. Disallineamenti dimensionali causano corruzione silenziosa del training.
L'asserzione a tempo di compilazione impone `len(FEATURE_NAMES) == METADATA_DIM == 25`.

### SQLite Modalità WAL

Tutti e tre i database (Monolith, HLTV, Per-match) applicano il Write-Ahead Logging
al checkout della connessione tramite `@event.listens_for` di SQLAlchemy. Questo permette
lettori concorrenti senza bloccare gli scrittori.

---

## Regole di Dipendenza tra Sotto-Pacchetti

```
Livello 0 (Fondazione):     storage/
Livello 1 (Dati):           data_sources/  ingestion/  knowledge/  knowledge_base/
Livello 2 (Elaborazione):   processing/  progress/
Livello 3 (Intelligenza):   analysis/  nn/
Livello 4 (Coaching):       coaching/  onboarding/
Livello 5 (Orchestrazione): services/  reporting/  control/
```

**Regole rigide:**

- I livelli inferiori NON importano MAI dai livelli superiori.
- `storage/` ha ZERO logica di dominio -- è pura persistenza.
- `services/` è il livello principale consumato dai pacchetti UI (`apps/`); il singleton
  di analytics `reporting/` (sola lettura) è anche importato direttamente dai ViewModel della dashboard.
- `nn/` può leggere da `processing/` e `storage/`, ma mai da `coaching/`.
- `coaching/` può invocare `nn/` per l'inferenza, ma non attiva mai il training.
- `control/` gestisce il ciclo di vita dei daemon e può toccare qualsiasi livello per l'orchestrazione.
- `data_sources/hltv/` effettua lo scraping SOLO di statistiche giocatori professionisti. NON recupera demo.

---

## Invarianti Critici

| ID | Regola | Conseguenza se Violata |
|----|--------|------------------------|
| P-X-01 | `len(FEATURE_NAMES) == METADATA_DIM == 25` | Corruzione silenziosa del modello |
| P-RSB-03 | `round_won` escluso dalle feature di training | La label leakage distrugge la validità del modello |
| NN-MEM-01 | Hopfield bypassato fino al primo vero passo dell'optimizer (o caricamento di checkpoint addestrato) | Esplosione NaN nella memoria RAP |
| P-VEC-02 | NaN/Inf nelle feature attiva ERROR + clamp | Propagazione di dati spazzatura nella pipeline |
| P3-A | > 5% NaN/Inf nel batch solleva `DataQualityError` | Il training run si interrompe in modo pulito |
| DS-12 | `MIN_DEMO_SIZE = 10 MB` | Rifiuta file demo corrotti/troncati |
| NN-16 | EMA `apply_shadow()` deve usare `.clone()` sui tensori | Il target encoder condivide silenziosamente i pesi |
| NN-JM-04 | Target encoder `requires_grad=False` durante EMA | Il gradient leakage corrompe JEPA |

---

## Note di Sviluppo

### Pattern di Import

- Le dipendenze opzionali (`ncps`, `hflayers`) usano `try/except` all'import e
  sollevano eccezioni all'istanziazione. Controllare `_RAP_DEPS_AVAILABLE` prima di usare RAP Coach.
- Guardie contro import circolari: `config` <-> `logger_setup` usa cablaggio post-import;
  `vectorizer.py` e `session_engine.py` usano import lazy/a livello di funzione.

### Configurazione

- Ordine di risoluzione: Default -> `user_settings.json` -> OS keyring/env.
- Nei thread daemon, usare `get_setting()` / `get_credential()` (thread-safe).
  Le variabili globali a livello di modulo sono snapshot-at-import e possono essere obsolete.

### Testing

- Framework: `pytest`, 182 file `test_*.py` in `Programma_CS2_RENAN/tests/` (+10 in `tests/` root).
- I test di integrazione richiedono `CS2_INTEGRATION_TESTS=1`.
- Fixture chiave: `in_memory_db`, `seeded_db_session`, `mock_db_manager`, `torch_no_grad`.

### Hook Pre-Commit

14 hook devono passare prima di ogni commit: headless-validator, dead-code-detector,
integrity-manifest, dev-health, trailing-whitespace, end-of-file-fixer,
check-yaml, check-json, large-files (1 MB), merge-conflict, detect-private-key,
ruff (--fix), black (100 colonne, py3.12), isort (profile=black).

### Validazione Post-Task

Dopo ogni modifica, eseguire:

```bash
python tools/headless_validator.py   # deve uscire con 0
```
