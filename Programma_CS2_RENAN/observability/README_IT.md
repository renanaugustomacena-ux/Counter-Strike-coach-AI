# Observability & Protezione Runtime

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorità:** `Programma_CS2_RENAN/observability/`
**Proprietario:** infrastruttura core Macena CS2 Analyzer

## Introduzione

Questo pacchetto fornisce i tre pilastri dell'osservabilità runtime per il CS2 Analyzer:
logging strutturato, protezione dell'integrità e tracciamento remoto degli errori. Ogni
modulo del progetto instrada i propri diagnostici attraverso questo pacchetto, garantendo
una superficie di osservabilità unica e coerente. Il design privilegia il comportamento
deterministico, zero fallimenti silenti e rigoroso isolamento PII prima che qualsiasi
dato lasci il confine del processo.

## Inventario File

| File | Scopo | Export Principali |
|------|-------|-------------------|
| `logger_setup.py` | Logging strutturato JSON centralizzato con ID correlazione | `get_logger()`, `get_tool_logger()`, `set_correlation_id()`, `configure_log_dir()`, `configure_retention()` |
| `rasp.py` | Guardia integrità Runtime Application Self-Protection | `RASPGuard`, `run_rasp_audit()`, `IntegrityError` |
| `sentry_setup.py` | Integrazione SDK Sentry con doppio opt-in e scrubbing PII | `init_sentry()`, `add_breadcrumb()` |
| `error_codes.py` | Registro centralizzato codici errore con severità e rimedio | `ErrorCode`, `log_with_code()`, `get_all_codes()` |
| `exceptions.py` | Gerarchia eccezioni di dominio radicata in `CS2AnalyzerError` | `CS2AnalyzerError`, `ConfigurationError`, `DatabaseError`, `IngestionError`, `TrainingError`, `IntegrationError`, `UIError` |
| `__init__.py` | Marcatore pacchetto | -- |

## Architettura & Concetti

### Logging Strutturato (`logger_setup.py`)

Tutti i logger vengono creati tramite `get_logger("cs2analyzer.<modulo>")`. La factory
collega ogni logger a due handler:

1. **File handler** -- `RotatingFileHandler` che scrive righe JSON in `cs2_analyzer.log`
   (rotazione 5 MB, 3 backup). Ricade su `FileHandler` semplice quando si verifica un
   `PermissionError` (contesa lock Windows, annotato come `LS-01`).
2. **Console handler** -- formato leggibile a soglia `WARNING`, mantenendo stdout
   pulito durante il funzionamento normale.

Ogni record di log viene arricchito da `_CorrelationFilter`, che inietta il
`correlation_id` thread-local impostato tramite `set_correlation_id()`. Questo abilita
il tracing end-to-end di un singolo job di ingestione, ciclo di training o sessione
coaching attraverso tutti i moduli.

Il livello di log viene risolto al momento della creazione del logger dalla variabile
d'ambiente `CS2_LOG_LEVEL` (es. `CS2_LOG_LEVEL=DEBUG`), consentendo sessioni debug
zero-code senza modificare i file sorgente. La riconfigurazione runtime è possibile
anche tramite `configure_log_level(logging.DEBUG)`.

Gli script CLI standalone (validatori, diagnostica) usano `get_tool_logger(tool_name)`,
che scrive in un file dedicato `logs/tools/<tool_name>_<timestamp>.json` per evitare
di inquinare il log dell'applicazione principale.

`configure_retention(max_days=30)` applica una policy del ciclo di vita dei log
eliminando i file `.log` e `.json` più vecchi della finestra di retention.
Best-effort -- gli errori OS vengono ignorati silenziosamente per evitare crash
dell'applicazione per operazioni di pulizia.

### Guardia Integrità RASP (`rasp.py`)

`RASPGuard` verifica che nessun file sorgente Python sia stato manomesso dall'ultima
build o generazione del manifest. Legge `core/integrity_manifest.json`, che mappa
percorsi file relativi ai rispettivi hash SHA-256, e confronta ogni voce con il
filesystem corrente.

Comportamenti chiave:

- **Firma HMAC** (`R1-12`): il manifest stesso è firmato con una chiave HMAC-SHA256.
  Le build di produzione iniettano la chiave tramite `CS2_MANIFEST_KEY`; lo sviluppo
  ricade su una chiave statica con un warning loggato (`RP-01`).
- **Supporto binari frozen**: quando eseguito all'interno di un bundle PyInstaller, il
  manifest viene risolto da `sys._MEIPASS` con percorsi candidati multipli.
- **Entry point di convenienza**: `run_rasp_audit(project_root)` istanzia la guardia,
  esegue il controllo e logga tutte le violazioni a livello `CRITICAL`.

### Tracciamento Errori Sentry (`sentry_setup.py`)

Il reporting remoto degli errori segue un modello **doppio opt-in**: sia `enabled=True`
che una stringa `dsn` valida devono essere forniti. Questo previene leak accidentali
di telemetria.

I PII vengono rimossi nell'hook `_before_send` prima che qualsiasi evento lasci il
processo:

- `server_name` viene sostituito con `"redacted"`.
- I nomi file degli stack trace contenenti la directory home utente vengono ripuliti.
- I messaggi e dati dei breadcrumb vengono sanificati in modo identico.

L'SDK viene inizializzato con `send_default_pii=False` e un `traces_sample_rate` del
10% per un monitoraggio performance leggero. La `LoggingIntegration` cattura breadcrumb
a livello WARNING e scala i record a livello ERROR in eventi Sentry completi.

`add_breadcrumb()` è un no-op quando Sentry non è inizializzato, rendendolo sicuro da
chiamare incondizionatamente in tutto il codebase.

### Registro Codici Errore (`error_codes.py`)

Ogni codice errore annotato nel progetto (es. `LS-01`, `RP-01`, `SE-04`) è registrato
come membro enum `ErrorCode` con severità, modulo proprietario, descrizione e guida
al rimedio. `log_with_code(ErrorCode.LS_01, "messaggio")` prefissa il messaggio con il
codice formale per grepping machine-parseable dei log.

### Gerarchia Eccezioni (`exceptions.py`)

Tutte le eccezioni di dominio ereditano da `CS2AnalyzerError`, che accetta un parametro
opzionale `error_code` per il logging strutturato. I sottotipi includono
`ConfigurationError`, `DatabaseError`, `IngestionError`, `TrainingError`,
`IntegrationError` e `UIError`.

## Integrazione

| Consumatore | Utilizzo |
|-------------|----------|
| `core/session_engine.py` | `set_correlation_id()` all'inizio del ciclo daemon; `run_rasp_audit()` al boot |
| `core/config.py` | `configure_log_dir(LOG_DIR)` dopo risoluzione percorso per rompere import circolare |
| Pipeline `ingestion/` | `get_logger()` + ID correlazione per tracing per-demo |
| Training `backend/nn/` | `get_logger()` per logging epoch/loss; `add_breadcrumb()` ai checkpoint |
| `apps/qt_app/` | `init_sentry()` all'avvio applicazione con DSN consentito dall'utente |
| Script `tools/` | `get_tool_logger()` per diagnostica tool isolata |
| Hook pre-commit | `run_rasp_audit()` tramite `tools/headless_validator.py` |

## Note Sviluppo

- **Guardia import circolare**: `config.py` necessita `get_logger()` al momento
  dell'import, ma `get_logger()` non deve importare da `config`. La soluzione è
  `configure_log_dir()`, chiamata da `config.py` dopo che `LOG_DIR` è calcolato.
- **Thread safety**: `_correlation_local` usa `threading.local()`, quindi gli ID
  correlazione sono isolati per thread. I thread daemon nel Quad-Daemon engine
  impostano ciascuno il proprio ID all'inizio del ciclo.
- **Testing**: nelle suite di test, `CS2_LOG_LEVEL=DEBUG` e
  `configure_log_dir(tmp_path)` redirigono tutto l'output in una directory temporanea.
  Sentry viene automaticamente saltato quando `pytest` è rilevato in `sys.modules`.
- **Pre-commit**: l'hook `integrity-manifest` rigenera e firma il manifest;
  `headless_validator.py` esegue `run_rasp_audit()` per verificarlo.
