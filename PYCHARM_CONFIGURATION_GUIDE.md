# Guida Completa alla Configurazione di PyCharm per Macena CS2 Analyzer

Questa guida descrive, sezione per sezione e campo per campo, ogni impostazione di PyCharm
ottimizzata per lo sviluppo del progetto CS2 Analyzer. Il progetto e un analizzatore AI per
Counter-Strike 2 composto da un package Python monolitico (`Programma_CS2_RENAN/`), con UI
Kivy+KivyMD (legacy) e PySide6/Qt (nuova), backend ML con PyTorch, database SQLite (WAL mode),
migrazioni Alembic, e un sistema di coaching AI basato su JEPA + RAP Coach. L'interprete di
riferimento e Python 3.12 nel virtualenv `/mnt/usb/.venvs/cs2analyzer/`.

> **Nota**: La versione Python testata in CI e **3.10**. Python 3.12 e supportato e funziona
> correttamente, ma le build automatiche in GitHub Actions usano 3.10 come versione di riferimento.

Le impostazioni si aprono da **File > Settings** (oppure `Ctrl+Alt+S`).

---

## PARTE 1 — SEZIONE "PYTHON"

### 1.1 Python > Interpreter

**Percorso nel menu:** `Settings > Python > Interpreter`

**Stato attuale:** Potresti avere configurato Python 3.10 o 3.12 di sistema con molti pacchetti
visibili. Questo NON e l'interprete corretto per il progetto.

**Cosa cambiare:**

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Python Interpreter | `/mnt/usb/.venvs/cs2analyzer/bin/python3` (Python 3.12) | Il virtualenv `cs2analyzer` contiene gia tutti i pacchetti necessari: pytest 9.0.2, pre-commit 4.5.1, torch 2.10.0+cpu, numpy 2.3.5, demoparser2 0.41.1, sqlmodel 0.37, pydantic 2.12.5, Kivy 2.3.1, sentence-transformers 5.3.0, ecc. L'interprete di sistema potrebbe non avere i pacchetti del progetto. |

**Step-by-step:**

1. Clicca l'icona ingranaggio accanto al dropdown dell'interprete attuale
2. Seleziona **"Add Interpreter..."** > **"Existing"**
3. Nel campo "Interpreter path" inserisci: `/mnt/usb/.venvs/cs2analyzer/bin/python3`
4. Clicca **OK** per confermare
5. Verifica che nella lista pacchetti compaiano `pytest`, `torch`, `demoparser2`, `sqlmodel`, `pydantic`, `numpy`, `Kivy`
6. Se l'interprete precedente (sistema) appare ancora, puoi rimuoverlo cliccando l'ingranaggio > **"Show All..."** e poi il pulsante **"-"**

**IMPORTANTE:** Questo e il passo piu critico di tutta la configurazione. Tutti gli altri
strumenti (Black, isort, mypy, pytest, debugger) dipendono dall'interprete corretto.
Senza questo cambio, PyCharm non risolvera gli import dei moduli del progetto e mostrera
errori falsi ovunque.

**Pacchetti da installare dopo la configurazione dell'interprete** (se mancanti):
```bash
source /mnt/usb/.venvs/cs2analyzer/bin/activate
pip install black isort mypy PySide6
```
Questi sono necessari per il linting, la formattazione e il type checking ma potrebbero
non essere installati nel venv attuale.

---

### 1.2 Python > Debugger

**Percorso nel menu:** `Settings > Python > Debugger`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Attach to subprocess automatically while debugging | **ON** | Il progetto usa thread multipli per il Tri-Daemon Engine (Hunter, Digester, Teacher in `core/session_engine.py`) e worker thread nel Qt frontend. Necessario per seguire i worker figli. |
| Collect run-time types information for code insight | **ON** | Raccoglie informazioni sui tipi a runtime, migliora l'autocompletamento per il codice con dict, tensori PyTorch, DataFrame pandas e oggetti SQLModel usati massivamente nel backend. Dopo la prima sessione di debug, i type hints inline saranno molto piu precisi. |
| Gevent compatible | **OFF** | Non usiamo gevent. Il progetto usa threading nativo e asyncio per alcune parti. |
| Drop into debugger on failed tests | **ON** | Con 50+ test nel progetto, questo velocizza enormemente il debug. Quando un test pytest fallisce, il debugger si apre automaticamente sul punto di errore. |
| PyQt compatible | **Auto** | Necessario per il debugging della UI PySide6/Qt. L'impostazione "Auto" rileva automaticamente PySide6. |
| Debugger evaluation response timeout (ms) | **120000** | 120 secondi. Le operazioni PyTorch (inference, feature extraction) e le query SQLite su tabelle con milioni di righe (PlayerTickState) possono essere lente in debug. |

---

### 1.3 Python > Debugger > Type Renderers

**Percorso nel menu:** `Settings > Python > Debugger > Type Renderers`

**Cosa aggiungere:** Per ora puoi lasciare vuoto. I Type Renderers Python sono utili
solo se hai classi custom con rappresentazioni complesse. Il progetto usa principalmente
dict, tensori PyTorch e dataclass SQLModel che il debugger gestisce bene di default.

**Opzionale per il futuro:** Se dovessi avere difficolta a leggere i tensori PyTorch
nel debugger (che a volte appaiono come oggetti lunghi), potresti aggiungere un renderer
custom per `torch.Tensor` con expression `f"Tensor({self.shape}, {self.dtype})"`.

---

### 1.4 Python > Console

**Percorso nel menu:** `Settings > Python > Console`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Always show Debug Console | **ON** | Mostra sempre la console debug. |
| Use IPython if available | **ON** | IPython offre autocompletamento, syntax highlighting e magic commands. Se non e installato nel venv, esegui: `pip install ipython` nel cs2analyzer venv. |
| Show console variables by default | **ON** | Mostra le variabili nella console interattiva. |
| Use existing console for "Run with Python Console" | **OFF** | Meglio avere console separate per run diversi, cosi non si mischiano output della console CLI, del Qt frontend e dei test. |
| Code completion | **Runtime** | Essendo un progetto con molti dict dinamici, tipi da demoparser2 e risposte JSON da HLTV/Steam/FACEIT, il completamento runtime sara molto piu preciso perche interroga l'interprete in tempo reale. |

---

### 1.5 Python > Console > Python Console

**Percorso nel menu:** `Settings > Python > Console > Python Console`

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Python interpreter | `/mnt/usb/.venvs/cs2analyzer/bin/python3` | Si aggiornera automaticamente dopo aver cambiato l'interprete globale (sezione 1.1). Verifica che punti al venv e non a `/usr/bin/python3`. |
| Working directory | `/mnt/usb/Counter-Strike-coach-AI/Counter-Strike-coach-AI-main` | Imposta la directory root del progetto come working directory, cosi gli import `from Programma_CS2_RENAN.…` funzionano correttamente nella console interattiva. |
| Add content roots to PYTHONPATH | **ON** | Necessario perche PyCharm aggiunga le source roots al path. |
| Add source roots to PYTHONPATH | **ON** | Necessario per risolvere gli import di `Programma_CS2_RENAN.*`. |

---

### 1.6 Python > Tools

Questa pagina e un indice dei sotto-tool. Vediamo ognuno.

---

### 1.6.1 Python > Tools > Ruff

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **OFF** (lasciare disabilitato) | Il progetto **NON usa Ruff**. Il formatter ufficiale e **Black** (line-length=100) con **isort** (profile=black). Il pre-commit hook usa `black` e `isort`, NON ruff. Attivare Ruff causerebbe conflitti di formattazione. |

---

### 1.6.2 Python > Tools > Black

**CRITICO — Black e il formatter principale del progetto** (usato nel pre-commit hook).

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **ON** (attivare) | Black e il formatter ufficiale del progetto (`pyproject.toml`: line-length=100, target-version py310). |
| Execution mode | **Interpreter** | Usa l'interprete del progetto (cs2analyzer venv). Se black non e installato, esegui `pip install black` nel venv. |
| Use Black formatter > On code reformat | **ON** | Formatta con Black quando premi `Ctrl+Alt+L`. |
| Use Black formatter > On save | **ON** | Formatta automaticamente al salvataggio. Previene commit con formattazione sbagliata. |

**Configurazione da `pyproject.toml`** (auto-rilevata da PyCharm):
```toml
[tool.black]
line-length = 100
target-version = ["py310"]
exclude = 'external_analysis|dist|\.venv|venv.*'
```

---

### 1.6.3 Python > Tools > Pyright

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **OFF** (lasciare disabilitato) | Il progetto usa **mypy** come type checker (definito in `pyproject.toml`). Pyright e un type checker alternativo — averli entrambi attivi genera confusione con segnalazioni duplicate e potenzialmente contrastanti. Mypy e gia configurato con flag specifici (`--ignore-missing-imports`, `--allow-untyped-defs`) che Pyright non rispetta. |

---

### 1.6.4 Python > Tools > Pyrefly

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **OFF** (lasciare disabilitato) | Pyrefly (Meta's type checker) e sperimentale e non compatibile con la configurazione mypy del progetto. Non serve. |

---

### 1.6.5 Python > Tools > ty

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable | **OFF** (lasciare disabilitato) | `ty` (di Astral, stessi creatori di Ruff) e ancora in fase alpha. Non e pronto per un progetto in produzione. |

---

### 1.6.6 Python > Tools > Integrated Tools

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Default test runner | **pytest** | Il progetto usa pytest con i plugin pytest-cov 7.0.0, pytest-mock 3.15.1. |
| Docstring format | **Google** | Il codice del progetto usa docstring con stile descrittivo che si allinea meglio al formato Google (parametri inline, returns, description). Questo migliora i tooltip e la generazione automatica di docstring template. |
| Analyze Python code in docstrings | **ON** | Evidenzia errori di sintassi negli esempi nelle docstring. |

**NOTA:** Se appare il warning "No pytest runner found", scomparira dopo aver cambiato l'interprete
al cs2analyzer venv (sezione 1.1), dove pytest 9.0.2 e gia installato.

---

### 1.7 Python > Tables

**Percorso nel menu:** `Settings > Python > Tables`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Default column statistics mode | **Off** | Le statistiche colonna consumano risorse. Per tabelle con dati tick-by-tick (PlayerTickState) con milioni di righe, meglio calcolarle on-demand. |
| Automatically display 'Compact' statistics | **ON** | Va bene per tabelle piccole. |
| Display NumPy, PyTorch, TensorFlow as table | **ON** | Essenziale. Il progetto usa numpy per feature vectors (`vectorizer.py` produce vettori METADATA_DIM dimensioni) e PyTorch per il training JEPA/RAP Coach. Visualizzare i tensori come tabella e fondamentale per il debug ML. |
| Limit the number of rendered columns | **ON**, valore **1200** | I nostri feature vector hanno dimensioni variabili, 1200 e piu che sufficiente. |
| Run data quality checks after table creation | **ON** | Utile per individuare NaN, duplicati e missing values nei DataFrame di tick data e match statistics. |
| Enable local filters by default in Data View | **ON** | Con tabelle di dati tick filtrate per round/player/team, i filtri locali permettono di restringere la vista senza modificare la query. |

---

### 1.8 Python > Django

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Enable Django Support | **OFF** (lasciare disabilitato) | Il progetto NON usa Django. Il backend API usa FastAPI (`fastapi 0.135.1`). Non attivare il supporto Django. |

---

### 1.9 Python > Flask

| Campo | Valore da impostare | Motivazione |
|-------|---------------------|-------------|
| Flask integration | **OFF** (disattivare) | Il progetto NON usa Flask. Il backend API usa FastAPI con Uvicorn. Avere Flask attivo puo interferire con il riconoscimento delle routes FastAPI e spreca risorse dell'IDE. Disattivalo. |

---

### 1.10 Python > External Documentation

**Cosa aggiungere** — clicca il pulsante **"+"** per aggiungere queste entry rilevanti per il progetto:

| Module Name | URL Pattern |
|-------------|-------------|
| `torch` | `https://pytorch.org/docs/stable/generated/{element.qname}.html` |
| `numpy` | `https://numpy.org/doc/stable/reference/generated/{element.qname}.html` |
| `fastapi` | `https://fastapi.tiangolo.com/reference/{module.basename}/` |
| `pydantic` | `https://docs.pydantic.dev/latest/api/{module.basename}/` |
| `sqlmodel` | `https://sqlmodel.tiangolo.com/` |
| `sqlalchemy` | `https://docs.sqlalchemy.org/en/20/` |
| `PySide6` | `https://doc.qt.io/qtforpython-6/` |

**Cosa rimuovere** (non rilevanti per il progetto):
- `wx`, `gtk`, `pyramid`, `PyQt5`, `PyQt4`, `flask` — nessuno di questi e usato.
  Seleziona ciascuno e clicca il pulsante **"-"** per rimuoverli. Meno entry = lookup piu veloce.

Mantieni: `matplotlib`, `pandas` (per analisi dati e grafici).

---

### 1.11 Project Structure

**Percorso nel menu:** `Settings > Project Structure`

Questa e una configurazione **critica** per la risoluzione degli import. Ecco cosa fare:

**Content Root:**
`/mnt/usb/Counter-Strike-coach-AI/Counter-Strike-coach-AI-main`

**IMPORTANTE: La project root e la source root.** NON marcare `Programma_CS2_RENAN/` come Sources Root.
Tutti gli import nel progetto partono dalla root:
```python
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.core.config import get_config
from Programma_CS2_RENAN.backend.nn.jepa_model import JEPA
```
Se marchi `Programma_CS2_RENAN/` come Sources, PyCharm risolvera gli import come
`from backend.storage...` che e SBAGLIATO.

**Directories da marcare come "Tests"** (clicca la cartella poi il pulsante verde **"Tests"**):

| Directory | Tipo |
|-----------|------|
| `tests/` | **Tests** |
| `Programma_CS2_RENAN/tests/` | **Tests** |

**Directories da marcare come "Excluded"** (clicca poi il pulsante rosso **"Excluded"**):

| Directory | Motivazione |
|-----------|-------------|
| `.idea` | File di configurazione IDE, non codice |
| `.claude` | Configurazione Claude Code, non codice |
| `.git` | Repository git |
| `.git_corrupted` | Artefatti git corrotti residui |
| `external_analysis` | Analisi esterne, non codice del progetto |
| `dist`, `build` | Artefatti di build PyInstaller |
| `__pycache__` | Bytecode Python compilato |
| `runs` | TensorBoard run data |
| `reports` | Report generati |
| `.venv`, `venv*` | Virtual environment (se presente in root) |

**Exclude files** (campo in basso): Inserisci questo pattern:
```
*.pyc;*.pyo;__pycache__;*.egg-info;.mypy_cache;.pytest_cache;.ruff_cache;*.dem;*.db;*.db-wal;*.db-shm;*.pt
```

Questo esclude dall'indicizzazione i file generati, i demo files (possono essere GB),
i database SQLite e i checkpoint del modello, velocizzando la ricerca e la navigazione.

---

## PARTE 2 — SEZIONE "BUILD, EXECUTION, DEPLOYMENT"

### 2.1 Build Tools

**Percorso:** `Settings > Build, Execution, Deployment > Build Tools`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Sync project after changes in the build scripts | **ON** | |
| Any changes / External changes | **Any changes** | Nel nostro workflow, Claude Code modifica file continuamente dall'esterno E dal terminale integrato. Con "Any changes", PyCharm risincronizza l'albero del progetto dopo ogni modifica, incluse quelle fatte nella console PyCharm stessa. Evita stati stantii. |

---

### 2.2 Coverage

**Percorso:** `Settings > Build, Execution, Deployment > Coverage`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| When New Coverage Is Gathered | **Replace active suites with the new one** | Non avere popup ogni volta che esegui i test con coverage. La sostituzione automatica e piu pratica nel workflow quotidiano. |
| Activate Coverage View | **ON** | Mostra il pannello con la percentuale di copertura per file. Target attuale: **35%** (roadmap: 35→40→50→60→70). |
| Show coverage in the project view | **ON** | Colora i file nel Project tree in base alla copertura. |
| Use bundled coverage.py | **OFF** | Il progetto usa `coverage` e `pytest-cov 7.0.0` gia installati nel venv. La versione bundled potrebbe essere vecchia. |
| Branch coverage | **ON** | La branch coverage misura se entrambi i rami di ogni `if` sono stati testati. Fondamentale per codice con molte condizioni come `match_data_manager.py` (validazione dati, dedup) e `session_engine.py` (gestione stati daemon). |

**Configurazione da `pyproject.toml`** (auto-rilevata):
```toml
[tool.coverage.run]
source = ["Programma_CS2_RENAN"]
omit = ["*/tests/*", "*/.venv/*", "*/external_analysis/*"]

[tool.coverage.report]
fail_under = 35
show_missing = true
```

---

### 2.3 Debugger (Build, Execution, Deployment)

**Percorso:** `Settings > Build, Execution, Deployment > Debugger`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Show debug window on breakpoint | **ON** | |
| Focus application on breakpoint | **ON** | |
| Hide debug window on process termination | **OFF** | Meglio mantenere la finestra aperta dopo il termine per esaminare l'ultimo stato. |
| Scroll execution point to center | **ON** | Quando il debugger si ferma su un breakpoint, la riga viene centrata nell'editor. Con file lunghi come `console.py` (2000+ righe), `match_data_manager.py` (31K) o `db_models.py` (27K), questo ti risparmia lo scroll manuale. |
| Click line number to perform run to cursor | **ON** | Comodo. |
| Confirm removal of conditional or logging breakpoints | **ON** | Previene la cancellazione accidentale di breakpoint con condizioni complesse configurati per il debug di specifici round, player o tick. |

---

### 2.3.1 Debugger > Data Views

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Sort values alphabetically | **OFF** | L'ordine di inserimento e piu utile per i dict Python che usiamo (i risultati demoparser2 hanno campi in ordine logico). |
| Enable auto expressions in Variables view | **ON** | |
| Show values inline | **ON** | Fondamentale: mostra i valori delle variabili direttamente accanto al codice. |
| Show value tooltip | **ON** | |
| Value tooltip delay (ms) | **500** | Riduci a 500ms per feedback piu rapido quando passi il mouse sulle variabili durante il debug. |
| Show value tooltip on code selection | **ON** | Quando selezioni un'espressione come `tick_data["player_position"]` o `features.shape`, appare un tooltip con il valore valutato. Utile con le espressioni composite del progetto. |

---

### 2.3.2 Debugger > Stepping

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Python > Always do smart step into | **ON** | Con chiamate annidate come `vectorizer.extract_features(tick_data)`, lo smart step ti permette di scegliere in quale funzione entrare. |
| Python > Do not step into library scripts | **ON** | Evita di entrare nel codice di torch, numpy, sqlmodel, kivy, PySide6 e altre librerie esterne durante il debug. Vuoi debuggare il TUO codice, non il codice di terze parti. Questo velocizza enormemente il debug. |

---

### 2.4 Deployment

**Percorso:** `Settings > Build, Execution, Deployment > Deployment`

**Per ora non serve configurare un server di deployment** in PyCharm. Il progetto usa
GitHub Actions per CI/CD e PyInstaller per la build Windows. Se in futuro avrai un
server di staging dove vuoi fare deploy diretto via SFTP, potrai configurarlo qui.

---

### 2.4.1 Deployment > Options

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Exclude items by name | `.svn;.cvs;.idea;.DS_Store;.git;.hg;*.hprof;*.pyc;*.env;__pycache__;.mypy_cache;.pytest_cache;*.dem;*.db;*.pt` | Aggiungi `*.env` (previene caricamento accidentale di credenziali), `*.dem` (demo files da GB), `*.db` (database), `*.pt` (checkpoint modello). |
| Upload changed files automatically | **Never** | Non fare upload automatico. Il deployment avviene via git push e CI/CD. |

---

### 2.5 Docker

**Percorso:** `Settings > Build, Execution, Deployment > Docker`

**NON rilevante per questo progetto.** Il CS2 Analyzer e un'applicazione desktop monolitica
che usa SQLite, non un ecosistema di microservizi con Docker. Non serve configurare Docker.

Se in futuro il progetto dovesse adottare un servizio esterno (es. un server di inferenza
separato), questa sezione potra essere configurata.

---

## PARTE 3 — SEZIONE "TOOLS" (Database)

### 3.1 Tools > Database > Query Execution

**Percorso:** `Settings > Tools > Database > Query Execution`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Shortcut | `Ctrl+Enter` | Standard e comodo. |
| When caret inside statement execute | **Ask what to execute** | Sicuro: chiede conferma prima di eseguire. Con database di match data che contengono milioni di righe di tick data, vuoi sempre sapere cosa stai per eseguire. |
| When caret outside statement execute | **Nothing** | Previene esecuzioni accidentali. |
| Open results in new tab | **ON** | Quando esegui query successive (es. prima `SELECT * FROM playertickstate` poi `SELECT * FROM playermatchstats`), ogni risultato si apre in un tab separato. Puoi confrontarli affiancati. |
| Show warning before running potentially unsafe queries | **ON** | Critico: avvisa prima di UPDATE, DELETE, DROP. Con dati di match analizzati per ore, non vuoi cancellare accidentalmente la tabella `playertickstate`. |

---

### 3.2 Tools > Database > Query Execution > Output and Results

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Show timestamp for query output | **ON** | Utile per correlare i risultati delle query con il timing delle partite analizzate. |
| Create title for results from comment before query | **ON** | Un commento come `-- Kill positions round 15` diventa il titolo del tab risultati. |
| Focus on Services tool window in window mode | **ON** | Quando esegui una query, il focus passa automaticamente alla finestra risultati. |

---

### 3.3 Tools > Database > Data Editor and Viewer

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Data Sorting > Sort via ORDER BY | **ON** | Il sorting avviene lato database. Con tabelle di milioni di righe (PlayerTickState), il sort client-side sarebbe impossibile. |
| Sort tables by numeric primary key | **ON, Descending** | Le tabelle time-series hanno dati ordinati per tick. Con "Descending" vedi prima i dati piu recenti. |
| Data Modification > Submit changes immediately | **OFF** | **NON attivare.** Vuoi rivedere le modifiche prima di salvarle. Una modifica accidentale potrebbe corrompere i dati di analisi. |
| Show DML preview before submitting changes | **ON** | Critico: mostra il SQL che verra eseguito prima di salvare. |

---

### 3.4 Configurazione della Connessione al Database (Pannello Database)

Questa sezione NON e nelle Settings ma nel pannello **Database** (View > Tool Windows > Database).

**Step-by-step per creare le connessioni:**

1. Apri il pannello **Database** (icona nella barra laterale destra o `View > Tool Windows > Database`)
2. Clicca **"+" > Data Source > SQLite**

**Connessione 1 — Main Database:**

| Campo | Valore | Note |
|-------|--------|------|
| Name | `CS2 Main DB` | Nome descrittivo |
| File | `Programma_CS2_RENAN/backend/storage/database.db` | Database principale (creato al primo avvio) |

**Connessione 2 — HLTV Metadata:**

| Campo | Valore | Note |
|-------|--------|------|
| Name | `HLTV Metadata` | Nome descrittivo |
| File | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Dati pro player, match results, map vetos |

3. Clicca **"Test Connection"** per verificare entrambe
4. Clicca **"OK"**

**Tabelle principali nel Main DB:**
- `playertickstate` — stato di ogni player ad ogni tick (tabella piu grande, milioni di righe)
- `playermatchstats` — statistiche aggregate per player per match
- `ingestiontask` — stato delle task di ingestion dei demo file
- `alembic_version` — versione corrente dello schema

**Tabelle nell'HLTV Metadata DB:**
- `proplayer` — giocatori professionisti (ID HLTV, nickname)
- `proteam` — team professionistici
- `proplayerstatcard` — statistiche dettagliate pro player
- `matchresult` — risultati match HLTV
- `mapveto` — ban/pick delle mappe per match

---

### 3.5 Tools > Database > Other

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| SQL Resolution > Default resolve mode | **Script** | In modalita Script, ogni console SQL e un file persistente che puoi salvare e riutilizzare. In Playground, il contenuto si perde alla chiusura. Per query ricorrenti come l'analisi dei tick data o il check delle ingestion task, vuoi poterle salvare. |

---

## PARTE 4 — SEZIONE "TOOLS" (MCP Server)

### 4.1 Tools > MCP Server

**Percorso:** `Settings > Tools > MCP Server`

| Campo | Valore consigliato | Motivazione |
|-------|---------------------|-------------|
| Enable MCP Server | **ON** | Il Model Context Protocol permette a Claude Code di interagire direttamente con PyCharm — leggere file aperti, eseguire refactoring, navigare il codice, eseguire run configuration. Essenziale per il nostro workflow. |
| Claude Code > Auto-Configure | **Configured** | Claude Code viene configurato come client MCP. Questo significa che quando usi Claude Code nel terminale, puo accedere alle funzionalita di PyCharm (search, refactor, build, run). |
| Command execution > Run shell commands without confirmation (brave mode) | **OFF** | **NON attivare.** La modalita "brave" permette l'esecuzione di comandi shell senza conferma. Il progetto manipola database con dati analizzati per ore — vuoi sempre confermare prima di eseguire comandi potenzialmente distruttivi. |

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

- [ ] L'interprete mostra `Python 3.12 (cs2analyzer)` in basso a destra nella status bar
- [ ] Aprendo `Programma_CS2_RENAN/backend/storage/database.py`, nessun import e sottolineato in rosso
- [ ] `from Programma_CS2_RENAN.backend.storage.database import get_db_manager` si risolve correttamente (Ctrl+Click naviga al file)
- [ ] Il pannello "Python Packages" mostra i pacchetti del cs2analyzer venv (pytest, torch, numpy, ecc.)
- [ ] Black e attivo: aprendo un file .py, la formattazione on-save funziona
- [ ] Il pannello Database mostra le tabelle SQLite (se le connessioni sono configurate)
- [ ] Eseguendo un test (tasto destro su un file test > "Run pytest"), i test vengono trovati e eseguiti
- [ ] La console `python console.py` si avvia senza errori

### 5.3 Run/Debug Configuration Consigliate

Crea queste Run Configuration per il lavoro quotidiano (Run > Edit Configurations > "+"):

**1. CS2 Console (TUI + CLI):**
- Type: Python
- Script path: `console.py`
- Working directory: Project root
- Environment variables: `PYTHONPATH=.`
- Interpreter: cs2analyzer venv

**2. Qt Frontend (PySide6):**
- Type: Python
- Module name: `Programma_CS2_RENAN.apps.qt_app.app`
- Working directory: Project root
- Environment variables: `PYTHONPATH=.`

**3. Kivy Frontend (Legacy):**
- Type: Python
- Script path: `Programma_CS2_RENAN/main.py`
- Working directory: Project root
- Environment variables: `PYTHONPATH=.;KIVY_NO_ARGS=1`

**4. Headless Validator (Post-Task Gate):**
- Type: Python
- Script path: `tools/headless_validator.py`
- Working directory: Project root
- Environment variables: `PYTHONPATH=.`
- **OBBLIGATORIO:** Eseguire dopo ogni modifica al codice. Deve uscire con codice 0.

**5. All Tests:**
- Type: pytest
- Target: Project root
- Additional arguments: `-v --tb=short`
- Environment variables: `PYTHONPATH=.`

**6. Tests with Coverage:**
- Type: pytest
- Target: Project root
- Additional arguments: `--cov=Programma_CS2_RENAN --cov-report=term-missing --cov-fail-under=35`

**7. Alembic Migration:**
- Type: Python
- Module name: `alembic`
- Parameters: `upgrade head`
- Working directory: Project root

---

## PARTE 6 — CONSIGLI AVANZATI PER IL WORKFLOW QUOTIDIANO

### 6.1 File Watchers per Black + isort

Se vuoi che Black e isort formattino automaticamente ogni volta che salvi un file:

1. Vai in `Settings > Tools > File Watchers`
2. Clicca **"+"** > **"Custom"**

**File Watcher 1 — Black Format on Save:**
- Name: `Black Format on Save`
- File type: `Python`
- Scope: `Project Files`
- Program: `/mnt/usb/.venvs/cs2analyzer/bin/black`
- Arguments: `--line-length 100 $FilePath$`
- Output paths to refresh: `$FilePath$`
- Working directory: `$ProjectFileDir$`

**File Watcher 2 — isort on Save:**
- Name: `isort on Save`
- File type: `Python`
- Scope: `Project Files`
- Program: `/mnt/usb/.venvs/cs2analyzer/bin/isort`
- Arguments: `--profile black --line-length 100 $FilePath$`
- Output paths to refresh: `$FilePath$`
- Working directory: `$ProjectFileDir$`

In "Advanced Options": deseleziona "Auto-save edited files to trigger the watcher" per entrambi.

### 6.2 Scorciatoie da Tastiera Consigliate

Per velocizzare il lavoro con il progetto CS2 Analyzer:

- `Ctrl+Shift+F10` — Esegui il file/test corrente
- `Shift+F9` — Debug del file/test corrente
- `Ctrl+Shift+T` — Naviga tra test e implementazione
- `Alt+Enter` — Quick fix (applica suggerimenti Black/mypy)
- `Ctrl+E` — File recenti (utile con tanti moduli backend)
- `Ctrl+Shift+F` — Cerca in tutto il progetto
- `Double Shift` — Cerca ovunque (file, classi, simboli)
- `Ctrl+B` — Vai alla definizione (fondamentale per navigare tra backend, core, storage)
- `Ctrl+Alt+L` — Riformatta file (usa Black)
- `Ctrl+Alt+O` — Ottimizza import (usa isort)
- `Ctrl+F2` — Ferma l'esecuzione corrente

### 6.3 Live Templates per SQL CS2 Analyzer

Per velocizzare le query ricorrenti nel pannello Database, crea dei Live Templates
(`Settings > Editor > Live Templates > SQL`):

**Template "csticks"** — Query tick data di un player:
```sql
SELECT tick, player_name, x, y, z, health, armor, active_weapon
FROM playertickstate
WHERE match_id = '$MATCH_ID$' AND player_name = '$PLAYER$'
ORDER BY tick
LIMIT $LIMIT$;
```

**Template "csstats"** — Statistiche player per match:
```sql
SELECT player_name, kills, deaths, assists, adr, rating, headshot_pct
FROM playermatchstats
WHERE match_id = '$MATCH_ID$'
ORDER BY rating DESC;
```

**Template "csingest"** — Stato ingestion task:
```sql
SELECT id, demo_path, status, error_message, created_at, completed_at
FROM ingestiontask
ORDER BY created_at DESC
LIMIT $LIMIT$;
```

**Template "cshltvpro"** — Pro player da HLTV:
```sql
SELECT p.nickname, p.country, t.name as team, s.rating_2_0, s.adr, s.kpr
FROM proplayer p
LEFT JOIN proteam t ON p.team_id = t.id
LEFT JOIN proplayerstatcard s ON s.player_id = p.id
ORDER BY s.rating_2_0 DESC;
```

---

### 6.4 Debugging del Training ML

Per debuggare il training JEPA o RAP Coach:

1. Imposta breakpoint in `backend/nn/jepa_trainer.py` o `backend/nn/rap_coach/trainer.py`
2. Nella Run Configuration, aggiungi environment variable: `PYTORCH_ENABLE_MPS_FALLBACK=1`
3. **GPU Note:** Attualmente il training gira su CPU (PyTorch 2.10.0+cpu). La GPU AMD RX 9070 XT
   (gfx1201/RDNA 4) richiede PyTorch con ROCm 7.2+ che non e ancora disponibile in stable.
   `HSA_OVERRIDE_GFX_VERSION=12.0.0` causa bus error — **NON usarlo**.
4. Per sessioni di debug ML lunghe, aumenta il timeout del debugger a **300000** ms (5 minuti)
   in `Settings > Python > Debugger > Debugger evaluation response timeout`

### 6.5 Pre-Commit Hooks

Installa una volta dal terminale:
```bash
source /mnt/usb/.venvs/cs2analyzer/bin/activate
pre-commit install
pre-commit install --hook-type pre-push
```

**13 hooks attivi:**

| Hook | Stage | Scopo |
|------|-------|-------|
| trailing-whitespace | pre-commit | Rimuove spazi trailing (markdown-aware) |
| end-of-file-fixer | pre-commit | Assicura newline a fine file |
| check-yaml | pre-commit | Validazione sintassi YAML |
| check-json | pre-commit | Validazione sintassi JSON |
| check-added-large-files | pre-commit | Blocca file >1MB (esclude immagini/CSV) |
| check-merge-conflict | pre-commit | Rileva marcatori di conflitto |
| detect-private-key | pre-commit | Blocca commit accidentali di chiavi private |
| black | pre-commit | Formattazione codice (100 caratteri) |
| isort | pre-commit | Ordinamento import (profilo black) |
| integrity-manifest-check | pre-commit | Verifica file critici del progetto |
| dev-health-quick | pre-commit | Controlli di salute rapidi |
| headless-validator | **pre-push** | Gate di regressione completo a 23 fasi |
| dead-code-detector | **pre-push** | Rilevamento moduli orfani |

### 6.6 Riprodurre CI Localmente

```bash
source /mnt/usb/.venvs/cs2analyzer/bin/activate

# Lint (pre-commit hooks)
pre-commit run --all-files

# Unit Tests con coverage
pytest --cov=Programma_CS2_RENAN --cov-fail-under=30 -q

# Integration (headless validator — OBBLIGATORIO)
python tools/headless_validator.py

# Portability test
python tools/portability_test.py

# Type check (informativo, non bloccante)
mypy Programma_CS2_RENAN/ --ignore-missing-imports --allow-untyped-defs

# Security scan
bandit -r Programma_CS2_RENAN/ -ll
```

### 6.7 Strumenti di Sviluppo

| Tool | Percorso | Scopo | Quando usarlo |
|------|----------|-------|---------------|
| `tools/headless_validator.py` | 23 fasi di regressione | **OBBLIGATORIO** dopo ogni modifica |
| `tools/dead_code_detector.py` | Moduli orfani | Periodicamente |
| `tools/portability_test.py` | Validazione cross-platform | Prima dei commit |
| `tools/db_health_diagnostic.py` | Integrita database | Dopo operazioni DB |
| `tools/dev_health.py` | Health check rapido | Controllo veloce |
| `tools/verify_main_boot.py` | Verifica boot | Dopo cambiamenti strutturali |
| `tools/Sanitize_Project.py` | Pulizia progetto | Prima dei rilasci |
| `tools/test_tactical_pipeline.py` | Pipeline tattica | Dopo cambiamenti a tactical viewer |

---

## RIEPILOGO DELLE MODIFICHE CRITICHE

In ordine di priorita, le modifiche piu importanti da fare:

1. **INTERPRETE** (1.1): Cambia dall'interprete di sistema al cs2analyzer venv Python 3.12
2. **PROJECT STRUCTURE** (1.11): NON marcare Programma_CS2_RENAN/ come Sources. Root = source root
3. **BLACK** (1.6.2): Attiva come formatter principale (line-length=100, on save)
4. **RUFF OFF** (1.6.1): NON attivare Ruff (il progetto usa Black+isort)
5. **FLASK OFF** (1.9): Disattiva l'integrazione Flask (non usata)
6. **DEBUGGER** (1.2): Attiva "Drop into debugger on failed tests" e "Collect runtime types"
7. **STEPPING** (2.3.2): Attiva "Do not step into library scripts"
8. **BUILD TOOLS** (2.1): Cambia sync a "Any changes"
9. **COVERAGE** (2.2): Attiva Branch coverage, target 35%
10. **DATABASE** (3.4): Configura le connessioni SQLite (Main DB + HLTV Metadata)
11. **EXTERNAL DOCS** (1.10): Aggiungi torch, numpy, PySide6, sqlmodel; rimuovi wx, gtk, flask
12. **EXCLUDE FILES** (1.11): Aggiungi pattern di esclusione per *.dem, *.db, *.pt, __pycache__
13. **INSTALL MISSING PACKAGES**: `pip install black isort mypy PySide6` nel venv
