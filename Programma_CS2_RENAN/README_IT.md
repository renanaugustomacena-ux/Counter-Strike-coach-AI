> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Programma_CS2_RENAN — Pacchetto Applicativo Principale

> **Autorita:** Tutte le Regole (Root del Pacchetto)

Pacchetto applicativo principale del Macena CS2 Analyzer — un coach tattico basato su intelligenza artificiale per Counter-Strike 2. Questo pacchetto contiene l'intero codice dell'applicazione organizzato in un'architettura a livelli.

## La Pipeline GUARDA > IMPARA > PENSA > PARLA

L'intero sistema segue una pipeline a quattro fasi che trasforma i dati grezzi delle demo in consigli tattici attuabili:

```
GUARDA (Ingestione) →  IMPARA (Addestramento) →  PENSA (Inferenza) →  PARLA (Dialogo)
    Daemon Hunter         Daemon Teacher             Pipeline COPER       Template + Ollama
    Parsing demo          Maturita a 3 stadi         Conoscenza RAG       Attribuzione causale
    Estrazione feature    Training multi-modello      Teoria dei giochi    Confronti con i pro
```

### Fase 1: GUARDA (Ingestione)
- Il **daemon Hunter** raccoglie statistiche dei giocatori professionisti da hltv.org
- Il **daemon Digester** analizza i file `.dem` tramite demoparser2 ed estrae il vettore di feature a 25 dimensioni
- I dati grezzi dei tick vengono salvati in database SQLite per singola partita

### Fase 2: IMPARA (Addestramento)
- Il **daemon Teacher** addestra i modelli neurali sui dati ingeriti
- Controllo di maturita a 3 stadi: CALIBRATING (0-49 demo) → LEARNING (50-199) → MATURE (200+)
- Modelli: JEPA (auto-supervisionato), RAP Coach (pedagogico a 7 livelli), NeuralRoleHead, Win Probability

### Fase 3: PENSA (Inferenza)
- Pipeline di coaching COPER: Context + Observation + Pro Reference + Experience + Reasoning
- Motori di teoria dei giochi: modelli di credenza, tracciamento del momentum, ottimizzazione dell'economia
- Recupero conoscenza RAG da documenti di coaching tattico

### Fase 4: PARLA (Dialogo)
- Coaching basato su template con attribuzione causale
- Rifinitura LLM opzionale tramite Ollama per output in linguaggio naturale
- Confronti con giocatori professionisti e monitoraggio longitudinale dei progressi

## Struttura del Pacchetto

```
Programma_CS2_RENAN/
├── apps/                       # Livello interfaccia utente
│   ├── qt_app/                 # UI desktop PySide6/Qt (primaria, MVVM)
│   └── desktop_app/            # UI desktop Kivy/KivyMD (legacy fallback)
├── backend/                    # Livello logica di business
│   ├── analysis/               # Teoria dei giochi, modelli di credenza, momentum (11 motori)
│   ├── coaching/               # Pipeline di coaching (COPER, Ibrido, RAG, Neurale)
│   ├── control/                # Ciclo di vita dei daemon, coda di ingestione, controllo ML
│   ├── data_sources/           # Parser demo, statistiche pro HLTV, Steam, API Faceit
│   ├── ingestion/              # Monitoraggio file in tempo reale, governance risorse
│   ├── knowledge/              # Base di conoscenza RAG, banca esperienze COPER
│   ├── knowledge_base/         # Sistema di aiuto in-app
│   ├── nn/                     # Reti neurali (6 architetture di modello)
│   ├── onboarding/             # Tracciamento progressione nuovi utenti
│   ├── processing/             # Feature engineering (vettore 25-dim), baseline
│   ├── progress/               # Tracciamento progresso addestramento
│   ├── reporting/              # Query analitiche per la UI
│   ├── services/               # Livello di orchestrazione servizi (6 servizi)
│   └── storage/                # Persistenza SQLite, modelli, backup
├── core/                       # Fondamenta runtime
│   ├── session_engine.py       # Motore Quad-Daemon (Hunter, Digester, Teacher, Pulse)
│   ├── config.py               # Sistema di configurazione (risoluzione a 3 livelli)
│   ├── spatial_data.py         # Intelligenza spaziale mappe (9 mappe competitive)
│   ├── map_manager.py          # Gestione asset delle mappe
│   └── lifecycle.py            # Avvio/arresto controllato
├── ingestion/                  # Orchestrazione ingestione demo
│   ├── pipelines/              # Pipeline demo utente e pro
│   ├── registry/               # Tracciamento e ciclo di vita file demo
│   └── hltv/                   # Sottosistema scraper HLTV
├── observability/              # Protezione e monitoraggio runtime
│   ├── rasp.py                 # Guardia di integrita RASP
│   ├── logger_setup.py         # Logging strutturato JSON
│   └── sentry_setup.py         # Tracciamento errori Sentry
├── reporting/                  # Visualizzazione e report
│   ├── visualizer.py           # Heatmap, mappe di ingaggio, grafici momentum
│   └── report_generator.py     # Report PDF multi-pagina
├── assets/                     # Asset statici (i18n, mappe)
├── data/                       # Dati runtime (demo, conoscenza, configurazioni)
├── models/                     # Checkpoint dei modelli addestrati
├── tests/                      # Suite di test (1,515+ test in 87 file)
├── tools/                      # Strumenti di validazione a livello pacchetto
├── __init__.py                 # Init del pacchetto (__version__ = "1.0.0")
├── run_ingestion.py            # Punto di ingresso ingestione demo
├── fetch_hltv_stats.py         # Punto di ingresso scraping statistiche HLTV
└── hltv_sync_service.py        # Daemon di sincronizzazione HLTV in background
```

## Punti di Ingresso Principali

| File | Scopo | Come Eseguire |
|------|-------|---------------|
| `apps/qt_app/app.py` | Applicazione desktop (GUI Qt) | `python -m Programma_CS2_RENAN.apps.qt_app.app` |
| `apps/desktop_app/main.py` | Applicazione desktop (GUI Kivy) | `python -m Programma_CS2_RENAN.apps.desktop_app.main` |
| `run_ingestion.py` | Pipeline di ingestione demo | `python -m Programma_CS2_RENAN.run_ingestion` |
| `fetch_hltv_stats.py` | Scraping statistiche pro HLTV | `python -m Programma_CS2_RENAN.fetch_hltv_stats` |
| `hltv_sync_service.py` | Sincronizzazione HLTV in background | Avviato dal daemon Hunter |

## Stack Tecnologico

| Livello | Tecnologia |
|---------|-----------|
| UI Primaria | PySide6/Qt (pattern MVVM, 13 schermate, 7 ViewModel) |
| UI Legacy | Kivy + KivyMD (pattern MVVM, 6 schermate) |
| Framework ML | PyTorch, ncps (neuroni Liquid Time-Constant), hflayers (Hopfield) |
| Database | SQLite (modalita WAL) via SQLModel/SQLAlchemy |
| Parsing Demo | demoparser2 (basato su Rust, alte prestazioni) |
| Statistiche Pro | BeautifulSoup4 + FlareSolverr/Docker (scraping HLTV) |
| Conoscenza | Sentence-BERT (384-dim) + FAISS (ricerca per similarita) |
| Osservabilita | TensorBoard, Sentry, logging strutturato JSON |
| Rifinitura LLM | Ollama (opzionale, inferenza locale) |

## Costanti Critiche

| Costante | Valore | Sorgente |
|----------|--------|----------|
| `METADATA_DIM` | 25 | `backend/processing/feature_engineering/vectorizer.py` |
| `INPUT_DIM` | 25 | `backend/nn/config.py` |
| `OUTPUT_DIM` | 10 | `backend/nn/config.py` |
| `HIDDEN_DIM` | 128 | `backend/nn/config.py` |
| `GLOBAL_SEED` | 42 | `backend/nn/config.py` |
| `BATCH_SIZE` | 32 | `backend/nn/config.py` |

## Note di Sviluppo

- Pattern di importazione: `from Programma_CS2_RENAN.backend.nn.config import ...`
- Il pacchetto utilizza importazioni lazy per evitare dipendenze circolari (specialmente config↔logger)
- Le dipendenze ML opzionali (ncps, hflayers) usano try/except all'importazione con controlli a runtime
- La `__version__` in `__init__.py` deve corrispondere a `pyproject.toml` e `windows_installer.iss`
- Eseguire `python tools/headless_validator.py` dalla root del progetto dopo ogni modifica
- Tutto il logging utilizza `get_logger("cs2analyzer.<modulo>")` per output JSON strutturato
