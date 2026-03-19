# Guida Completa alla Configurazione di PyCharm per GOLIATH Trading Ecosystem

Questa guida descrive, sezione per sezione e campo per campo, ogni impostazione di PyCharm
ottimizzata per lo sviluppo del progetto GOLIATH. Il progetto e un ecosistema di trading
algoritmico composto da microservizi Python (ai-brain, mt5-bridge, console, dashboard,
ml-training, external-data), un servizio Go (data-ingestion), un database TimescaleDB/PostgreSQL, Redis,
e infrastruttura Docker. L'interprete di riferimento e Python 3.12 nel virtualenv
`/home/a-cupsa/goliath-venv/`.

> **Nota**: La versione Python testata in CI e **3.11**. Python 3.12 e supportato e funziona
> correttamente, ma le build automatiche in GitHub Actions usano 3.11 come versione di riferimento.

Le impostazioni si aprono da **File > Settings** (oppure `Ctrl+Alt+S`).

---

## PARTE 1 — SEZIONE "PYTHON"

### 1.1 Python > Interpreter

**Percorso nel menu:** `Settings > Python > Interpreter`

**Stato attuale:** Hai configurato Python 3.10 di sistema con molti pacchetti visibili.
Questo NON e l'interprete corretto per il progetto.

**Cosa cambiare:**

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Python Interpreter | `/home/a-cupsa/goliath-venv/bin/python3` (Python 3.12) | Il virtualenv `goliath-venv` contiene gia tutti i pacchetti necessari: ruff 0.15.6, mypy 1.19.1, pytest 8.4.2, black 25.12.0, coverage 7.13.4, fastapi, httpx, ecc. L'interprete di sistema (3.10) e obsoleto e non ha i pacchetti del progetto. |

**Step-by-step:**

1. Clicca l'icona ingranaggio accanto al dropdown dell'interprete attuale
2. Seleziona **"Add Interpreter..."** > **"Existing"**
3. Nel campo "Interpreter path" inserisci: `/home/a-cupsa/goliath-venv/bin/python3`
4. Clicca **OK** per confermare
5. Verifica che nella lista pacchetti compaiano `ruff`, `mypy`, `pytest`, `black`, `fastapi`, `structlog`, `prometheus-client`
6. Se l'interprete precedente (Python 3.10) appare ancora, puoi rimuoverlo cliccando l'ingranaggio > **"Show All..."** e poi il pulsante **"-"**

**IMPORTANTE:** Questo e il passo piu critico di tutta la configurazione. Tutti gli altri
strumenti (Ruff, Black, mypy, pytest, debugger) dipendono dall'interprete corretto.
Senza questo cambio, PyCharm non risolvera gli import dei moduli del progetto e mostrera
errori falsi ovunque.

---

### 1.2 Python > Debugger

**Percorso nel menu:** `Settings > Python > Debugger`

**Stato attuale:** Abbastanza buono. PyQt compatible e attivo, timeout a 60000ms.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Attach to subprocess automatically while debugging | **ON** (gia attivo) | Il progetto usa asyncio e subprocess per alcuni servizi. Necessario per seguire i worker figli. |
| Collect run-time types information for code insight | **ON** (cambiare) | Attualmente OFF. Attivalo: raccoglie informazioni sui tipi a runtime, migliora l'autocompletamento per il codice con Decimal, dict[str, Any] e pydantic BaseSettings usati massivamente in connector.py e order_manager.py. Dopo la prima sessione di debug, i type hints inline saranno molto piu precisi. |
| Gevent compatible | **OFF** (lasciare) | Non usiamo gevent. Il progetto usa asyncio nativo. |
| Drop into debugger on failed tests | **ON** (cambiare) | Attualmente OFF. Attivalo: quando un test pytest fallisce, il debugger si apre automaticamente sul punto di errore. Con 916+ test nel progetto, questo velocizza enormemente il debug. |
| PyQt compatible | **Auto** (lasciare) | OK cosi com'e. |
| Attach To Process - filter | `python` (lasciare) | Corretto. Filtra i processi Python per "Attach to Process". |
| Debugger evaluation response timeout (ms) | **60000** (lasciare) | 60 secondi e corretto. Alcune operazioni ML/NumPy possono essere lente in debug. Se dovessi debuggare il training orchestrator, potresti anche alzarlo a 120000. |

---

### 1.3 Python > Debugger > Type Renderers

**Percorso nel menu:** `Settings > Python > Debugger > Type Renderers`

**Stato attuale:** Vuoto ("No renderers").

**Cosa aggiungere:** Per ora puoi lasciare vuoto. I Type Renderers Python sono utili
solo se hai classi custom con rappresentazioni complesse. Il progetto usa principalmente
dict, Decimal e dataclass standard che il debugger gestisce bene di default.

**Opzionale per il futuro:** Se dovessi avere difficolta a leggere gli oggetti `Decimal`
nel debugger (che a volte appaiono come oggetti lunghi), potresti aggiungere un renderer
custom per `decimal.Decimal` con expression `str(self)`. Ma per ora non serve.

---

### 1.4 Python > Console

**Percorso nel menu:** `Settings > Python > Console`

**Stato attuale:** Buona configurazione di base.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Always show Debug Console | **ON** (gia attivo) | Bene, mostra sempre la console debug. |
| Use IPython if available | **ON** (gia attivo) | IPython offre autocompletamento, syntax highlighting e magic commands. Se non e installato nel venv, esegui: `pip install ipython` nel goliath-venv. |
| Show console variables by default | **ON** (gia attivo) | Mostra le variabili nella console interattiva. |
| Use existing console for "Run with Python Console" | **OFF** (lasciare) | Meglio avere console separate per run diversi, cosi non si mischiano gli output dei vari servizi. |
| Command queue for Python Console | **OFF** (lasciare) | Non necessario. |
| Code completion | **Runtime** (cambiare) | Attualmente impostato su "Static". Cambia a **"Runtime"**: essendo un progetto con molti dict dinamici, tipi Any da rpyc e risposte JSON, il completamento runtime sara molto piu preciso perche interroga l'interprete in tempo reale. |

---

### 1.5 Python > Console > Python Console

**Percorso nel menu:** `Settings > Python > Console > Python Console`

**Stato attuale:** Interprete impostato su "Project Default (Python 3.12) /usr/bin/python3".
Questo punta all'interprete di sistema, NON al virtualenv.

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Environment variables | Clicca l'icona e aggiungi le variabili dal file `.env` | Per poter testare interattivamente il codice nella console, servono le variabili d'ambiente del progetto. Le piu importanti: `GOLIATH_DB_HOST=localhost`, `GOLIATH_DB_PORT=5432`, `GOLIATH_DB_NAME=goliath`, `GOLIATH_REDIS_HOST=localhost`, `GOLIATH_REDIS_PORT=6379`, `GOLIATH_ENV=development`. |
| Python interpreter | `/home/a-cupsa/goliath-venv/bin/python3` | Si aggiornera automaticamente dopo aver cambiato l'interprete globale (sezione 1.1). Verifica che punti al venv e non a `/usr/bin/python3`. |
| Interpreter options | (lasciare vuoto) | Non servono opzioni speciali. |
| Working directory | `/home/a-cupsa/Desktop/trading-ecosystem-main (1)/trading-ecosystem-main/program` | Imposta la directory `program/` come working directory, cosi gli import relativi dei servizi funzionano correttamente nella console interattiva. |
| Add content roots to PYTHONPATH | **ON** (gia attivo) | Necessario perche PyCharm aggiunga le source roots al path. |
| Add source roots to PYTHONPATH | **ON** (gia attivo) | Necessario per risolvere gli import di `goliath_common`, `ai_brain`, `mt5_bridge`, ecc. |

**Starting script** — lascia quello di default:
```python
import sys; print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend([WORKING_DIR_AND_PYTHON_PATHS])
```

---

### 1.6 Python > Tools

**Percorso nel menu:** `Settings > Python > Tools`

Questa pagina e un indice dei sotto-tool. Vediamo ognuno.

---

### 1.6.1 Python > Tools > Ruff

**Stato attuale:** Disabilitato. Ruff non installato nell'interprete corrente.

**CRITICO — Ruff e il linter/formatter principale del progetto** (usato nel pre-commit hook).

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **ON** (attivare) | Ruff e il linter ufficiale del progetto. Il pre-commit usa `ruff` e `ruff-format`. E gia installato nel goliath-venv (v0.15.6). |
| Features > Inspections | **ON** | Mostra gli errori di linting inline nell'editor. |
| Features > Formatting | **ON** | Usa ruff come formatter (sostituisce Black per la formattazione). |
| Features > Import optimizer | **ON** | Ruff gestisce anche l'ordinamento degli import (isort integrato). |
| Execution mode | **Interpreter** | Usa l'interprete del progetto (goliath-venv) che ha gia ruff installato. |
| Python interpreter | Verra auto-selezionato dal Project Default dopo il cambio in 1.1 | |

**Dopo aver cambiato l'interprete (1.1):** Il messaggio "Ruff package is not installed" scomparira
perche ruff 0.15.6 e gia nel goliath-venv.

---

### 1.6.2 Python > Tools > Black

**Stato attuale:** Disabilitato. Black non installato nell'interprete corrente.

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Execution mode | **Package** (lasciare) | |
| Python interpreter | Si aggiornera con il cambio interprete (1.1) | |
| Use Black formatter > On code reformat | **OFF** (lasciare OFF) | **NON attivare Black come formatter.** Il progetto usa **Ruff** come formatter primario (vedi pre-commit: `ruff-format`). Avere sia Black che Ruff attivi causa conflitti di formattazione. Black e installato nel venv come fallback ma Ruff ha la precedenza. |
| Use Black formatter > On save | **OFF** (lasciare OFF) | Stessa ragione: usa Ruff, non Black. |

**Nota importante:** Black e nel venv come dipendenza transitiva, ma il pre-commit hook
usa `ruff-format`. Non attivare Black on-save o on-reformat per evitare formattazioni
contrastanti.

---

### 1.6.3 Python > Tools > Pyright

**Stato attuale:** Disabilitato.

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **OFF** (lasciare disabilitato) | Il progetto usa **mypy** come type checker (definito nel pre-commit hook: `mirrors-mypy v1.10.0`). Pyright e un type checker alternativo — averli entrambi attivi genera confusione con segnalazioni duplicate e potenzialmente contrastanti. Mypy e gia configurato con flag specifici (`--ignore-missing-imports`, `--allow-untyped-defs`) che Pyright non rispetta. |

---

### 1.6.4 Python > Tools > Pyrefly

**Stato attuale:** Disabilitato.

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **OFF** (lasciare disabilitato) | Pyrefly (Meta's type checker) e sperimentale e non compatibile con la configurazione mypy del progetto. Non serve. |

---

### 1.6.5 Python > Tools > ty

**Stato attuale:** Disabilitato.

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **OFF** (lasciare disabilitato) | `ty` (di Astral, stessi creatori di Ruff) e ancora in fase alpha. Quando sara stabile, potrebbe sostituire mypy, ma per ora non e pronto per un progetto in produzione. |

---

### 1.6.6 Python > Tools > Integrated Tools

**Stato attuale:** pytest selezionato, ma warning "No pytest runner found in the selected interpreter".

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Package requirements file for SDK | (lasciare vuoto) | Ogni servizio ha il proprio `pyproject.toml`. Non c'e un singolo requirements file globale. |
| Path to Pipenv executable | (lasciare vuoto) | Non usiamo Pipenv. |
| Default test runner | **pytest** (gia corretto) | Il progetto usa pytest con i plugin pytest-asyncio, pytest-cov, pytest-mock. |
| Detect tests in Jupyter Notebooks | **OFF** (lasciare) | Non usiamo Jupyter per i test. |
| Docstring format | **Google** (cambiare) | Attualmente "Plain". Cambia a **"Google"**: il codice del progetto usa docstring con stile descrittivo che si allinea meglio al formato Google (parametri inline, returns, description). Questo migliora i tooltip e la generazione automatica di docstring template. |
| Analyze Python code in docstrings | **ON** (gia attivo) | Corretto: evidenzia errori di sintassi negli esempi nelle docstring. |
| Render external documentation for stdlib | **OFF** (lasciare) | Non essenziale. |

**NOTA:** Il warning "No pytest runner found" scomparira dopo aver cambiato l'interprete
al goliath-venv (sezione 1.1), dove pytest 8.4.2 e gia installato.

---

### 1.7 Python > Tables

**Percorso nel menu:** `Settings > Python > Tables`

**Stato attuale:** Ben configurato.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Default column statistics mode | **Off** (lasciare) | Le statistiche colonna consumano risorse. Per tabelle con dati finanziari (OHLCV) con milioni di righe, meglio calcolarle on-demand. |
| Automatically display 'Compact' statistics | **ON** (gia attivo) | Va bene per tabelle piccole (50-600K righe). |
| Display NumPy, PyTorch, TensorFlow as table | **ON** (gia attivo) | Essenziale. Il progetto usa numpy per feature vectors (market_vectorizer.py produce vettori di 60+ dimensioni) e PyTorch per il training ML. Visualizzare i tensori come tabella e fondamentale per il debug. |
| Limit the number of rendered columns | **ON**, valore **1200** (lasciare) | OK. I nostri feature vector hanno max ~60 colonne, quindi 1200 e piu che sufficiente. |
| Run data quality checks after table creation | **ON** (gia attivo) | Utile per individuare NaN, duplicati e missing values nei DataFrame di market data. |
| Enable local filters by default in Data View | **ON** (cambiare) | Attualmente OFF. Attivalo: con tabelle di dati OHLCV filtrate per simbolo/timeframe, i filtri locali permettono di restringere la vista senza modificare la query. Comodo quando esplori le candele di un singolo simbolo. |

---

### 1.8 Python > Django

**Percorso nel menu:** `Settings > Python > Django`

**Stato attuale:** Vuoto, non configurato.

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable Django Support | **OFF** (lasciare disabilitato) | Il progetto NON usa Django. Il dashboard backend usa FastAPI (`program/services/dashboard/backend/main.py`). Non attivare il supporto Django. |

---

### 1.9 Python > Flask

**Percorso nel menu:** `Settings > Python > Flask`

**Stato attuale:** Flask integration attiva (toggle ON).

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Flask integration | **OFF** (disattivare) | Il progetto NON usa Flask. Il backend usa FastAPI con Uvicorn. Avere Flask attivo puo interferire con il riconoscimento delle routes FastAPI e spreca risorse dell'IDE. Disattivalo. |

---

### 1.10 Python > External Documentation

**Percorso nel menu:** `Settings > Python > External Documentation`

**Stato attuale:** URL di documentazione per matplotlib, pandas, wx, gtk, ecc.

**Cosa aggiungere** — clicca il pulsante **"+"** per aggiungere queste entry rilevanti per il progetto:

| Module Name | URL Pattern |
|-------------|-------------|
| `fastapi` | `https://fastapi.tiangolo.com/reference/{module.basename}/` |
| `pydantic` | `https://docs.pydantic.dev/latest/api/{module.basename}/` |
| `structlog` | `https://www.structlog.org/en/stable/api.html` |
| `asyncio` | `https://docs.python.org/3/library/asyncio-{module.basename}.html` |
| `grpc` | `https://grpc.github.io/grpc/python/grpc.html` |
| `prometheus_client` | `https://prometheus.github.io/client_python/` |
| `numpy` | `https://numpy.org/doc/stable/reference/generated/{element.qname}.html` |
| `torch` | `https://pytorch.org/docs/stable/generated/{element.qname}.html` |
| `rpyc` | `https://rpyc.readthedocs.io/en/latest/api/` |

**Cosa rimuovere** (non rilevanti per il progetto):
- `wx`, `gtk`, `pyramid`, `PySide`, `PyQt5`, `PyQt4`, `kivy` — nessuno di questi e usato.
  Seleziona ciascuno e clicca il pulsante **"-"** per rimuoverli. Meno entry = lookup piu veloce.

Mantieni: `matplotlib`, `pandas`, `flask` (per riferimento generico).

---

### 1.11 Project Structure

**Percorso nel menu:** `Settings > Project Structure`

**Stato attuale:** Una sola Content Root, nessuna directory marcata come Sources/Tests/Excluded.

Questa e una configurazione **critica** per la risoluzione degli import. Ecco cosa fare:

**Content Root** gia presente:
`/home/a-cupsa/Desktop/trading-ecosystem-main (1)/trading-ecosystem-main`

**Directories da marcare come "Sources"** (clicca la cartella poi il pulsante blu **"Sources"**):

| Directory | Tipo | Motivazione |
|-----------|------|-------------|
| `program/services/ai-brain/src` | **Sources** | Contiene il package `ai_brain` — il cervello del sistema |
| `program/services/mt5-bridge/src` | **Sources** | Contiene `mt5_bridge` — connettore MetaTrader 5 |
| `program/services/console/src` | **Sources** | Contiene `goliath_console` — TUI di gestione |
| `program/services/dashboard/backend` | **Sources** | Contiene il backend FastAPI del dashboard |
| `program/services/ml-training/src` | **Sources** | Contiene `ml_training` — orchestratore ML |
| `program/services/external-data/src` | **Sources** | Contiene `external_data` — dati macro |
| `program/shared/python-common/src` | **Sources** | Contiene `goliath_common` — libreria condivisa (logging, exceptions, decimal_utils) |

**Directories da marcare come "Tests"** (clicca la cartella poi il pulsante verde **"Tests"**):

| Directory | Tipo |
|-----------|------|
| `program/services/ai-brain/tests` | **Tests** |
| `program/services/mt5-bridge/tests` | **Tests** |
| `program/services/console/tests` | **Tests** |
| `program/services/ml-training/tests` | **Tests** |

**Directories da marcare come "Excluded"** (clicca poi il pulsante rosso **"Excluded"**):

| Directory | Motivazione |
|-----------|-------------|
| `.idea` | File di configurazione IDE, non codice |
| `.claude` | Configurazione Claude Code, non codice |
| `program/services/*/build` | Artefatti di build |
| `program/services/*/__pycache__` | Bytecode Python compilato |
| `AUDIT_REPORTS` | Report di audit, non codice |
| `GUIDE` | Guide testuali |
| `.git` | Repository git |
| `program/services/data-ingestion/vendor` | Dipendenze Go vendored (se presente) |

**Exclude files** (campo in basso): Inserisci questo pattern:
```
*.pyc;*.pyo;__pycache__;*.egg-info;.mypy_cache;.pytest_cache;.ruff_cache;node_modules;dist;build
```

Questo esclude dall'indicizzazione i file generati, velocizzando la ricerca e la navigazione.

---

## PARTE 2 — SEZIONE "BUILD, EXECUTION, DEPLOYMENT"

### 2.1 Build Tools

**Percorso:** `Settings > Build, Execution, Deployment > Build Tools`

**Stato attuale:** Sync project attivo con "External changes".

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Sync project after changes in the build scripts | **ON** (gia attivo) | |
| Any changes / External changes | **Any changes** (cambiare) | Attualmente su "External changes". Cambia a **"Any changes"**: nel nostro workflow, Claude Code modifica file continuamente dall'esterno E dal terminale integrato. Con "Any changes", PyCharm risincronizza l'albero del progetto dopo ogni modifica, incluse quelle fatte nella console PyCharm stessa. Evita stati stantii. |

---

### 2.2 Coverage

**Percorso:** `Settings > Build, Execution, Deployment > Coverage`

**Stato attuale:** "Show options before applying coverage", bundled coverage.py non attivo.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| When New Coverage Is Gathered | **Replace active suites with the new one** (cambiare) | Attualmente "Show options before applying". Cambia per non avere popup ogni volta che esegui i test con coverage. La sostituzione automatica e piu pratica nel workflow quotidiano. |
| Activate Coverage View | **ON** (gia attivo) | Mostra il pannello con la percentuale di copertura per file. |
| Show coverage in the project view | **ON** (gia attivo) | Colora i file nel Project tree in base alla copertura. |
| Use bundled coverage.py | **OFF** (lasciare OFF) | Il progetto usa `coverage 7.13.4` e `pytest-cov 5.0.0` gia installati nel venv. La versione bundled potrebbe essere vecchia. |
| Branch coverage | **ON** (cambiare) | Attualmente OFF. Attivalo: la branch coverage misura se entrambi i rami di ogni `if` sono stati testati. Fondamentale per codice con molte condizioni come `order_manager.py` (validazione margine, lot clamping, dedup) e `connector.py` (direct vs rpyc backend). |

---

### 2.3 Debugger (Build, Execution, Deployment)

**Percorso:** `Settings > Build, Execution, Deployment > Debugger`

**Stato attuale:** Buone impostazioni di base.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Show debug window on breakpoint | **ON** (gia attivo) | |
| Focus application on breakpoint | **ON** (gia attivo) | |
| Hide debug window on process termination | **OFF** (lasciare) | Meglio mantenere la finestra aperta dopo il termine per esaminare l'ultimo stato. |
| Scroll execution point to center | **ON** (cambiare) | Attualmente OFF. Attivalo: quando il debugger si ferma su un breakpoint, la riga viene centrata nell'editor. Con file lunghi come `main.py` (400+ righe) o `connector.py` (744 righe), questo ti risparmia lo scroll manuale. |
| Click line number to perform run to cursor | **ON** (gia attivo) | Comodo. |
| Remove breakpoint | **Click with left mouse button** (gia selezionato) | OK. |
| Confirm removal of conditional or logging breakpoints | **ON** (cambiare) | Attualmente OFF. Attivalo: previene la cancellazione accidentale di breakpoint con condizioni complesse che hai configurato per il debug di specifici simboli (es. `symbol == "XAUUSD"`). |

---

### 2.3.1 Debugger > Data Views

**Stato attuale:** Buone impostazioni.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Sort values alphabetically | **OFF** (lasciare) | L'ordine di inserimento e piu utile per i dict Python che usiamo (i risultati MT5 hanno campi in ordine logico). |
| Enable auto expressions in Variables view | **ON** (gia attivo) | |
| Show values inline | **ON** (gia attivo) | Fondamentale: mostra i valori delle variabili direttamente accanto al codice. |
| Show value tooltip | **ON** (gia attivo) | |
| Value tooltip delay (ms) | **500** (cambiare) | Attualmente 700ms. Riduci a 500ms per feedback piu rapido quando passi il mouse sulle variabili durante il debug. |
| Show value tooltip on code selection | **ON** (cambiare) | Attualmente OFF. Attivalo: quando selezioni un'espressione come `info["balance"]` o `to_decimal(pos["volume"])`, appare un tooltip con il valore valutato. Utile con le espressioni composite del progetto. |

---

### 2.3.2 Debugger > Stepping

**Stato attuale:** Smart step into attivo per Python e JavaScript.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Python > Always do smart step into | **ON** (gia attivo) | Corretto: con chiamate annidate come `to_decimal(info["balance"])`, lo smart step ti permette di scegliere in quale funzione entrare. |
| Python > Do not step into library scripts | **ON** (cambiare) | Attualmente OFF. **Attivalo**: evita di entrare nel codice di structlog, prometheus_client, rpyc, asyncio e altre librerie esterne durante il debug. Vuoi debuggare il TUO codice, non il codice di terze parti. Questo velocizza enormemente il debug. |
| Python > Do not step into scripts | (lasciare vuoto per ora) | Se trovi che il debugger entra in file specifici che non vuoi debuggare, puoi aggiungerli qui. |

---

### 2.3.3 Debugger > Data Views > JavaScript / Perl5 Type Renderers

Lasciare le impostazioni di default. Non sono rilevanti per il nostro progetto Python.
Il frontend React (dashboard) usa il debugger del browser, non quello di PyCharm.

---

### 2.4 Deployment

**Percorso:** `Settings > Build, Execution, Deployment > Deployment`

**Stato attuale:** Non configurato ("Not configured").

**Per ora non serve configurare un server di deployment** in PyCharm. Il progetto usa
Docker Compose per il deployment locale e git push per il deployment remoto.
Se in futuro avrai un server di staging Proxmox dove vuoi fare deploy diretto via SFTP,
potrai configurarlo qui.

---

### 2.4.1 Deployment > Options

**Stato attuale:** Configurazione di default.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Exclude items by name | `.svn;.cvs;.idea;.DS_Store;.git;.hg;*.hprof;*.pyc;*.env;__pycache__;.mypy_cache;.pytest_cache;.ruff_cache;node_modules` (aggiornare) | Aggiungi `*.env`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `node_modules` alla lista di esclusione. Critico: `*.env` previene il caricamento accidentale di file con credenziali. |
| Preserve file timestamps | **ON** (gia attivo) | |
| Confirm deleting remote files | **ON** (gia attivo) | |
| Prompt when overwriting or deleting local items | **ON** (gia attivo) | |
| Upload changed files automatically | **Never** (lasciare) | Non fare upload automatico. Il deployment avviene via Docker. |

---

### 2.5 Docker

**Percorso:** `Settings > Build, Execution, Deployment > Docker`

**Stato attuale:** Docker configurato, connessione via Unix socket riuscita ("Connection successful").

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Name | `Docker` (lasciare) | |
| Detect executable paths automatically | **ON** (gia attivo) | |
| Connect to Docker daemon with | **Unix socket** (gia selezionato) | Corretto per Linux. Il socket di default `unix:///var/run/docker.sock` funziona. |
| Connection successful | OK, tutto bene | La connessione Docker funziona. Potrai vedere i container GOLIATH (macena-postgres, macena-redis, macena-prometheus, ecc.) nel pannello Services di PyCharm. |

**Path Mappings** (sezione in basso "Virtual machine path / Local path"):
Per ora lascia vuoto. Se dovessi debuggare codice all'interno di un container Docker,
dovresti mappare i path del container ai path locali (es. `/app/src` -> `program/services/ai-brain/src`).

---

### 2.5.1 Docker > Console

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Fold previous sessions in the Log console | **ON** (gia attivo) | Mantiene la console Docker pulita piegando le sessioni precedenti. |

---

### 2.5.2 Docker > Docker Registry

**Stato attuale:** Docker Hub configurato ma senza credenziali ("Cannot connect: Username required").

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Name | `Docker Hub` (lasciare) | |
| Registry | `Docker Hub` (lasciare) | |
| Username | (inserisci il tuo username Docker Hub se ne hai uno) | Le immagini del progetto (timescaledb, redis, prometheus, grafana) sono tutte pubbliche, quindi le credenziali NON sono strettamente necessarie per il pull. Se non hai un account Docker Hub, puoi lasciare vuoto e ignorare il warning. |
| Password | (inserisci la tua password/token se hai un account) | |

**Nota:** Per il nostro progetto, non pushiamo immagini su Docker Hub, facciamo solo pull
di immagini pubbliche. Le credenziali servono solo per evitare rate limiting (100 pull/6h
per utenti anonimi, 200 pull/6h per utenti autenticati).

---

### 2.6 Perl5 Profiler

**Stato attuale:** Profiler NYTProf configurato.

**Non rilevante per il nostro progetto.** Non usiamo Perl. Puoi ignorare questa sezione.

---

### 2.7 Run Targets

**Percorso:** `Settings > Build, Execution, Deployment > Run Targets`

**Stato attuale:** Nessun target creato. Il menu mostra le opzioni SSH, Docker, Docker Compose.

**Consiglio: Crea un Run Target Docker Compose** per poter eseguire e debuggare i servizi Python
direttamente nei container Docker.

**Step-by-step per creare il target:**

1. Clicca **"+ Add new target..."**
2. Seleziona **"Docker Compose..."**
3. Nel campo **"Server"**: seleziona `Docker` (quello configurato in 2.5)
4. Nel campo **"Configuration files"**: seleziona il file
   `program/infra/docker/docker-compose.yml`
5. Nel campo **"Service"**: seleziona il servizio che vuoi debuggare (es. `ai-brain`)
6. Clicca **"Next"**, poi **"Create"**

Questo ti permettera di selezionare "Docker Compose: ai-brain" come target di esecuzione
nelle Run/Debug Configurations, eseguendo il codice direttamente nel container con tutte
le dipendenze (PostgreSQL, Redis) accessibili.

**Ripeti** per `mt5-bridge` e `dashboard` se vuoi debuggare anche quelli nei container.

---

## PARTE 3 — SEZIONE "TOOLS" (Database)

### 3.1 Tools > Database > Query Execution

**Percorso:** `Settings > Tools > Database > Query Execution`

**Stato attuale:** Configurazione ragionevole con opzioni di sicurezza attive.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Shortcut | `Ctrl+Enter` (lasciare) | Standard e comodo. |
| When caret inside statement execute | **Ask what to execute** (lasciare) | Sicuro: chiede conferma prima di eseguire. Con un database di trading in produzione, vuoi sempre sapere cosa stai per eseguire. |
| When caret outside statement execute | **Nothing** (lasciare) | Previene esecuzioni accidentali. |
| For selection execute | **Exactly as separate statements** (lasciare) | Corretto per eseguire piu statement selezionati singolarmente. |
| Open results in new tab | **ON** (cambiare) | Attualmente OFF. Attivalo: quando esegui query successive (es. prima `SELECT * FROM market_data_ohlcv` poi `SELECT * FROM trading_signals`), ogni risultato si apre in un tab separato. Puoi confrontarli affiancati. |
| Review parameters before execution | **ON** (gia attivo) | Sicurezza: mostra i parametri prima di eseguire query parametrizzate. |
| Show warning before running potentially unsafe queries | **ON** (gia attivo) | Critico: avvisa prima di UPDATE, DELETE, DROP. Con dati finanziari reali, non vuoi cancellare accidentalmente la tabella `market_data_ohlcv`. |

---

### 3.2 Tools > Database > Query Execution > Output and Results

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Show timestamp for query output | **ON** (cambiare) | Attualmente OFF. Attivalo: per le query su tabelle time-series come `market_data_ohlcv`, vedere il timestamp dell'esecuzione ti aiuta a correlare i risultati con l'orario di mercato. |
| Results > Show results in editor | **OFF** (lasciare) | I risultati nella Services tool window sono piu gestibili. |
| Create title for results from comment before query | **ON** (gia attivo) | Utile: un commento come `-- Ultimi segnali per XAUUSD` diventa il titolo del tab risultati. |
| Services Tool Window > Show for | **For all output** (lasciare) | |
| Focus on Services tool window in window mode | **ON** (cambiare) | Attualmente OFF. Attivalo: quando esegui una query, il focus passa automaticamente alla finestra risultati. |

---

### 3.3 Tools > Database > Query Execution > User Parameters

**Stato attuale:** Ben configurato con pattern per Python (`%(name)s`, `%name`), PostgreSQL (`:name`), ecc.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Enable in query consoles and SQL files | **ON** (gia attivo) | Corretto. |
| Enable in string literals with SQL injection | **ON** (gia attivo) | Importante: rileva parametri anche dentro stringhe Python che contengono SQL. |
| Substitute inside SQL strings | **OFF** (lasciare) | Prevenire sostituzioni indesiderate all'interno di stringhe. |
| Parameter patterns | (lasciare tutti quelli presenti) | I pattern coprono tutti i formati usati: Python `%(name)s`, PostgreSQL `$1` e `:name`, `${name}`. |

---

### 3.4 Tools > Database > Data Editor and Viewer

**Stato attuale:** Primo screenshot poco leggibile (troppo piccolo), secondo screenshot mostra date/time e sorting.

**Le impostazioni dalla seconda parte visibile:**

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Custom Date/Time Formats > Datetime/timestamp | **ON** (attivare), pattern: `yyyy-MM-dd HH:mm:ss` | Attualmente OFF. Attivalo: le tabelle GOLIATH usano timestamp per ogni candela, segnale e esecuzione. Visualizzarli in formato ISO standard e essenziale. |
| Custom Date/Time Formats > Time with time zone | **ON** (attivare), pattern: `HH:mm:ss Z` | I mercati Forex operano in UTC. Mostrare il fuso orario evita confusione. |
| Custom Date/Time Formats > Date | **ON** (attivare), pattern: `yyyy-MM-dd` | Formato ISO standard per le date. |
| Data Sorting > Sort via ORDER BY | **ON** (gia attivo) | Corretto: il sorting avviene lato server, non client. Con tabelle di milioni di righe (hypertable TimescaleDB), il sort client-side sarebbe impossibile. |
| Sort tables by numeric primary key | **ON** (cambiare) | Attualmente OFF. Attivalo con **Descending**: le tabelle time-series hanno dati ordinati per timestamp. Con "Descending" vedi prima i dati piu recenti, che e quasi sempre quello che vuoi (ultima candela, ultimo segnale). |
| Data Modification > Submit changes immediately | **OFF** (lasciare OFF) | **NON attivare.** Vuoi rivedere le modifiche prima di salvarle. Con dati finanziari reali, una modifica accidentale potrebbe corrompere i dati. |
| Enable editing for queries with JOIN clauses | **ON** (gia attivo) | |
| Show DML preview before submitting changes | **ON** (gia attivo) | Critico: mostra il SQL che verra eseguito prima di salvare. |

---

### 3.5 Tools > Database > Query Files

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Show data source name in code editor tab title | **ON** (gia attivo) | Utile: quando hai piu connessioni (dev, staging), il tab mostra a quale database sei connesso. |

---

### 3.6 Tools > Database > Other

**Stato attuale:** Configurazione mista con SQL Resolution in "Playground" mode.

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Modify Object > Confirm cancellation | **ON** (gia attivo) | Sicurezza. |
| Refactoring > Show preview of valid script | **ON** (gia attivo) | |
| DDL Mappings > Suggest dumping DDL | **ON** (gia attivo) | |
| Code Generation > Generate context templates | **Append to existing console** (lasciare) | |
| Database Explorer > Remember filter | **ON** (gia attivo) | |
| Virtual Foreign Keys | Pattern `(.*)_(?i)id` -> `$1\\.(?i)id` (gia presente) | Questo pattern riconosce automaticamente le relazioni FK virtuali (es. `signal_id` -> `signals.id`). Corretto per il nostro schema dove le tabelle `trading_signals`, `order_executions`, `market_data_ohlcv` usano questo naming convention. |
| SQL Resolution > Default resolve mode | **Script** (cambiare) | Attualmente "Playground". Cambia a **"Script"**: in modalita Script, ogni console SQL e un file persistente che puoi salvare e riutilizzare. In Playground, il contenuto si perde alla chiusura. Per query ricorrenti come l'analisi dei segnali o il check delle esecuzioni, vuoi poterle salvare. |
| Statement delimiter | `;` (lasciare vuoto/default) | PostgreSQL usa `;` come delimitatore. |

---

### 3.7 Configurazione della Connessione al Database (Pannello Database)

Questa sezione NON e nelle Settings ma nel pannello **Database** (View > Tool Windows > Database).
E fondamentale per connettere PyCharm al database TimescaleDB del progetto.

**Step-by-step per creare la connessione:**

1. Apri il pannello **Database** (icona nella barra laterale destra o `View > Tool Windows > Database`)
2. Clicca **"+" > Data Source > PostgreSQL**
3. Compila i campi:

| Campo | Valore | Note |
|-------|--------|------|
| Name | `GOLIATH Dev` | Nome descrittivo |
| Host | `localhost` | Come da `.env.example`: `GOLIATH_DB_HOST=localhost` |
| Port | `5432` | Come da `.env.example`: `GOLIATH_DB_PORT=5432` |
| Database | `goliath` | Come da `.env.example`: `GOLIATH_DB_NAME=goliath` |
| User | `goliath` | Come da `.env.example`: `GOLIATH_DB_USER=goliath` |
| Password | (la password che hai impostato nel tuo `.env`) | Spunta "Save" per salvarla |
| URL | `jdbc:postgresql://localhost:5432/goliath` | Si auto-compila |

4. Clicca **"Test Connection"** per verificare
5. Nella tab **"Schemas"**: seleziona `public` (lo schema principale del progetto)
6. Clicca **"OK"**

**IMPORTANTE:** Se i container Docker non sono in esecuzione, la connessione fallira.
Avvia prima lo stack con:
```bash
cd program && make up
```
oppure:
```bash
docker compose -f program/infra/docker/docker-compose.yml up -d
```

**Tabelle principali che vedrai:**
- `market_data_ohlcv` — candele OHLCV (hypertable TimescaleDB)
- `trading_signals` — segnali generati dal brain
- `order_executions` — ordini eseguiti su MT5
- `portfolio_snapshots` — stato del portafoglio nel tempo
- `kill_switch_events` — eventi di kill switch
- `audit_log` — log di audit

---

## PARTE 4 — SEZIONE "TOOLS" (MCP Server)

### 4.1 Tools > MCP Server

**Percorso:** `Settings > Tools > MCP Server`

**Stato attuale:** MCP Server abilitato su `http://127.0.0.1:64342/sse`.
Claude Code auto-configurato ("Configured").

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Enable MCP Server | **ON** (gia attivo) | Il Model Context Protocol permette a Claude Code di interagire direttamente con PyCharm — leggere file aperti, eseguire refactoring, navigare il codice, eseguire run configuration. Essenziale per il nostro workflow. |
| Claude Code > Auto-Configure | **Configured** (gia fatto) | Claude Code e gia configurato come client MCP. Questo significa che quando usi Claude Code nel terminale, puo accedere alle funzionalita di PyCharm (search, refactor, build, run). |
| Command execution > Run shell commands without confirmation (brave mode) | **OFF** (lasciare OFF) | **NON attivare.** La modalita "brave" permette l'esecuzione di comandi shell senza conferma. Con un progetto che gestisce trading reale e connessioni al broker, vuoi sempre confermare prima di eseguire comandi potenzialmente distruttivi. |

**Verifica che il MCP funzioni:**
1. Apri un terminale in PyCharm
2. L'URL MCP mostrato (`http://127.0.0.1:64342/sse`) deve essere raggiungibile
3. Se usi Claude Code dal terminale PyCharm, le funzionalita MCP (navigazione file,
   diagnostics, build) saranno automaticamente disponibili

---

## PARTE 5 — AZIONI POST-CONFIGURAZIONE

### 5.1 Invalidare Cache e Riavviare

Dopo tutte queste modifiche, e fondamentale:

1. **File > Invalidate Caches...**
2. Seleziona **tutte** le opzioni (Clear file system cache, Clear VCS Log caches, Clear downloaded shared indexes)
3. Clicca **"Invalidate and Restart"**

Questo forza PyCharm a ricostruire gli indici con il nuovo interprete e le nuove source roots.
La prima riapertura sara lenta (2-5 minuti per l'indicizzazione), ma dopo tutto sara fluido.

### 5.2 Verifica Post-Configurazione

Dopo il riavvio, verifica che:

- [ ] L'interprete mostra `Python 3.12 (goliath-venv)` in basso a destra nella status bar
- [ ] Aprendo `program/services/ai-brain/src/ai_brain/main.py`, nessun import e sottolineato in rosso
- [ ] `from goliath_common.logging import get_logger` si risolve correttamente (Ctrl+Click naviga al file)
- [ ] Il pannello "Python Packages" mostra i pacchetti del goliath-venv (ruff, mypy, pytest, ecc.)
- [ ] Ruff e attivo: aprendo un file .py, eventuali warning Ruff appaiono inline
- [ ] Il pannello Docker mostra i container del progetto (se lo stack e in esecuzione)
- [ ] Il pannello Database mostra le tabelle GOLIATH (se la connessione e configurata)
- [ ] Eseguendo un test (tasto destro su un file test > "Run pytest"), i test vengono trovati e eseguiti

### 5.3 Run/Debug Configuration Consigliate

Crea queste Run Configuration per il lavoro quotidiano (Run > Edit Configurations > "+"):

**1. AI Brain Service:**
- Type: Python
- Script path: `program/services/ai-brain/src/ai_brain/main.py`
- Working directory: `program/services/ai-brain`
- Environment variables: carica da `.env`
- Interpreter: goliath-venv

**2. MT5 Bridge Service:**
- Type: Python
- Script path: `program/services/mt5-bridge/src/mt5_bridge/main.py`
- Working directory: `program/services/mt5-bridge`
- Environment variables: carica da `.env`

**3. Dashboard Backend:**
- Type: Python
- Module name: `uvicorn`
- Parameters: `dashboard.backend.main:app --reload --port 8080`
- Working directory: `program/services/dashboard`

**4. All Tests:**
- Type: pytest
- Target: `program/`
- Additional arguments: `-v --tb=short`

**5. Docker Compose (Full Stack):**
- Type: Docker > Docker Compose
- Compose file: `program/infra/docker/docker-compose.yml`
- Services: (tutti)

---

## PARTE 6 — CONSIGLI AVANZATI PER IL WORKFLOW QUOTIDIANO

### 6.1 File Watchers per Ruff (Opzionale)

Se vuoi che Ruff formatti automaticamente ogni volta che salvi un file:

1. Vai in `Settings > Tools > File Watchers`
2. Clicca **"+"** > **"Custom"**
3. Configura:
   - Name: `Ruff Format on Save`
   - File type: `Python`
   - Scope: `Project Files`
   - Program: `/home/a-cupsa/goliath-venv/bin/ruff`
   - Arguments: `format $FilePath$`
   - Output paths to refresh: `$FilePath$`
   - Working directory: `$ProjectFileDir$`
4. In "Advanced Options": deseleziona "Auto-save edited files to trigger the watcher"

Questo e alternativo all'opzione "On save" di Ruff nelle impostazioni Python Tools, e offre
piu controllo granulare sul comportamento.

### 6.2 Scorciatoie da Tastiera Consigliate

Per velocizzare il lavoro con il progetto GOLIATH:

- `Ctrl+Shift+F10` — Esegui il file/test corrente
- `Shift+F9` — Debug del file/test corrente
- `Ctrl+Shift+T` — Naviga tra test e implementazione
- `Alt+Enter` — Quick fix (applica suggerimenti Ruff/mypy)
- `Ctrl+E` — File recenti (utile con tanti servizi)
- `Ctrl+Shift+F` — Cerca in tutto il progetto
- `Double Shift` — Cerca ovunque (file, classi, simboli)
- `Ctrl+B` — Vai alla definizione (fondamentale per navigare tra servizi)
- `Ctrl+Alt+L` — Riformatta file (usa Ruff se configurato)
- `Ctrl+F2` — Ferma l'esecuzione corrente

### 6.3 Live Templates per SQL GOLIATH

Per velocizzare le query ricorrenti nel pannello Database, crea dei Live Templates
(`Settings > Editor > Live Templates > SQL`):

**Template "gohlcv"** — Query candele recenti:
```sql
SELECT symbol, timeframe, bucket, open, high, low, close, volume
FROM market_data_ohlcv
WHERE symbol = '$SYMBOL$' AND timeframe = '$TIMEFRAME$'
ORDER BY bucket DESC
LIMIT $LIMIT$;
```

**Template "gosig"** — Ultimi segnali di trading:
```sql
SELECT symbol, direction, confidence, strategy, created_at
FROM trading_signals
WHERE created_at > NOW() - INTERVAL '$HOURS$ hours'
ORDER BY created_at DESC;
```

**Template "goexec"** — Esecuzioni recenti:
```sql
SELECT symbol, direction, lots, price, slippage_pips, status, executed_at
FROM order_executions
WHERE executed_at > NOW() - INTERVAL '$HOURS$ hours'
ORDER BY executed_at DESC;
```

---

## RIEPILOGO DELLE MODIFICHE CRITICHE

In ordine di priorita, le modifiche piu importanti da fare:

1. **INTERPRETE** (1.1): Cambia da Python 3.10 sistema a goliath-venv Python 3.12
2. **SOURCE ROOTS** (1.11): Marca 7 directory come Sources e 4 come Tests
3. **RUFF** (1.6.1): Attiva come linter/formatter principale
4. **FLASK OFF** (1.9): Disattiva l'integrazione Flask (non usata)
5. **BLACK OFF** (1.6.2): Non attivare Black (conflitto con Ruff)
6. **DEBUGGER** (1.2): Attiva "Drop into debugger on failed tests" e "Collect runtime types"
7. **STEPPING** (2.3.2): Attiva "Do not step into library scripts"
8. **BUILD TOOLS** (2.1): Cambia sync a "Any changes"
9. **COVERAGE** (2.2): Attiva Branch coverage
10. **DATABASE** (3.7): Configura la connessione a TimescaleDB
11. **EXTERNAL DOCS** (1.10): Aggiungi fastapi, pydantic, structlog; rimuovi wx, gtk, kivy
12. **EXCLUDE FILES** (1.11): Aggiungi pattern di esclusione per *.pyc, __pycache__, ecc.
