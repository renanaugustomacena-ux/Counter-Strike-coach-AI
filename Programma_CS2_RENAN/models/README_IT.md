> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Archiviazione Checkpoint Reti Neurali

> **Autorità:** Regola 4 (Persistenza Dati)

Questa directory archivia i checkpoint delle reti neurali addestrate (file `.pt`)
utilizzati dal Ghost Engine per l'inferenza in tempo reale e dalla pipeline di
coaching per la generazione di suggerimenti potenziati da ML. I checkpoint sono
serializzazioni binarie `state_dict` di PyTorch gestite tramite il modulo
`persistence.py`, che impone scritture atomiche, caricamento multi-fallback e
validazione dimensionale rigorosa.

Nessun file `.pt` viene committato nel repository. Questa directory esiste nel
version control per preservare la sua struttura (tramite `global/README.txt`),
per ospitare il registro hash CTF-1 dei checkpoint (`checkpoint_hashes.json`) e
per servire come destinazione di scrittura predefinita quando `BRAIN_DATA_ROOT`
non è configurato. I checkpoint addestrati sono artefatti runtime locali
(gitignored); consultare `docs/OPEN_ISSUES.md` §2 per le attività di
addestramento e dati in sospeso.

## Struttura della Directory

```
models/
├── global/                   # Modelli baseline condivisi (non specifici per utente)
│   ├── archive_pre_rebuild_2026-09-01/  # Pesi archiviati pre-rebuild (file .pt gitignored)
│   └── README.txt           # Segnaposto per preservare la directory in git
├── checkpoint_hashes.json    # Registro hash SHA-256 CTF-1 per i checkpoint
├── README.md                 # Questo file (Inglese)
├── README_IT.md              # Traduzione Italiana
└── README_PT.md              # Traduzione Portoghese
```

Dopo il rebuild del 2026-09-01, `models/` non contiene file `.pt` di produzione.
I pesi pre-rebuild sono stati archiviati sotto
`global/archive_pre_rebuild_2026-09-01/` (gitignored).

A runtime, i modelli personalizzati per utente vengono archiviati in sottodirectory per utente:

```
models/
├── global/                  # Baseline condivisa (da addestramento demo professionali)
│   ├── latest.pt           # Modello coach predefinito (AdvancedCoachNN)
│   ├── jepa_brain.pt       # JEPA pre-addestrato su match professionali (miglior val loss)
│   ├── jepa_brain_latest.pt # Salvataggio rolling per epoca della stessa run
│   └── rap_coach.pt        # Checkpoint modello RAP
├── nn/versions/             # Snapshot con timestamp (ModelManager.save_version)
│   └── brain_{timestamp}.pt
└── {user_id}/               # Modelli personalizzati per utente
    └── latest.pt           # Checkpoint adattato all'utente
```

Il `TrainingOrchestrator` scrive due file per run: il nome di versione grezzo su
una nuova miglior validation loss, e `{version}_latest.pt` dopo ogni epoca. Ogni
checkpoint salvato tramite `save_nn()` è accompagnato da un file sidecar
`.pt.meta.json` (GAP-07) che registra `schema_version`, `metadata_dim` e la
lista dei nomi delle feature al momento del salvataggio.

## Inventario dei Checkpoint

Le stringhe di versione mappano ai tipi di modello di `ModelFactory`:

| Checkpoint | Classe Modello | Creato Da | Input Dim |
|-----------|---------------|-----------|-----------|
| `latest.pt` | AdvancedCoachNN (predefinito) | `backend/nn/train.py`, `coach_manager.py` | 25 (METADATA_DIM) |
| `jepa_brain.pt` | Modello coaching JEPA | `backend/nn/training_orchestrator.py` (ciclo epoche: `jepa_trainer.py`) | 25 (METADATA_DIM) |
| `vl_jepa_brain.pt` | VL-JEPA (concept head) | `backend/nn/training_orchestrator.py` | 25 (METADATA_DIM) |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/training_orchestrator.py` (ciclo epoche: `experimental/rap_coach/trainer.py`; condizionato da `USE_RAP_MODEL`) | 25 (METADATA_DIM) |
| `rap_lite_coach.pt` | RAP-Lite (memoria LSTM) | Addestramento RAP con `use_lite_memory` (stringa versione da `factory.py`) | 25 (METADATA_DIM) |
| `role_head.pt` | NeuralRoleHead | `backend/nn/role_head.py` | 5 |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` (utility offline, attualmente nessun chiamante in produzione) | 9 (sottoinsieme offline) |

L'orchestratore scrive inoltre un checkpoint rolling `{version}_latest.pt` per
epoca, e la pipeline standalone a due stadi `backend/nn/jepa_train.py`
(CLI pretrain/finetune sul database monolite) scrive
`jepa_model.pt` / `jepa_model_finetuned.pt` nel proprio formato dizionario
wrappato.

## Formato dei Checkpoint

Ogni file `.pt` scritto tramite `save_nn()` è un dizionario `state_dict` di
PyTorch salvato via `torch.save()`. Le chiavi corrispondono ai parametri nominati
della classe del modello. (La pipeline standalone `jepa_train.py` invece wrappa
lo state dict in un dizionario checkpoint con `model_state_dict`, contatori EMA
e metadati di addestramento.) Struttura di esempio per `jepa_brain.pt`:

```python
{
    "online_encoder.layer1.weight": Tensor(...),
    "online_encoder.layer1.bias": Tensor(...),
    "coaching_head.fc1.weight": Tensor(...),
    "coaching_head.fc1.bias": Tensor(...),
    # ... tutti i parametri nominati
}
```

Per i modelli che utilizzano EMA (Exponential Moving Average), i pesi shadow sono
archiviati **all'interno** dello stesso dizionario del checkpoint, non come file
separati. Il modulo EMA clona i tensori shadow durante `apply_shadow()` per
preservare gli originali (invariante NN-16).

## Architettura di Persistenza

Il modulo `backend/nn/persistence.py` è l'interfaccia canonica per l'I/O dei
checkpoint sui percorsi di caricamento/salvataggio in produzione; il nuovo codice
non deve chiamare `torch.save()` / `torch.load()` direttamente. Eccezioni
offline note che lo bypassano: la pipeline standalone `jepa_train.py` (proprio
formato checkpoint wrappato atomico), l'utility dormiente
`win_probability_trainer.py` (`state_dict` grezzo su un percorso fornito dal
chiamante), e `ModelManager.save_version()` in `model.py` (snapshot con
timestamp sotto `models/nn/versions/`).

### Protocollo di Scrittura Atomica

```
save_nn(model, version, user_id=None, extra_meta=None)
  1. Risolvere il percorso destinazione: models/{user_id o "global"}/{version}.pt
  2. Scrivere pesi e sidecar .pt.meta.json su file temporanei
  3. Sostituzione atomica: tmp_path.replace(path)  # prima i pesi, poi il sidecar
  4. Registrare SHA-256 in checkpoint_hashes.json (CTF-1)
  5. In caso di errore: eliminare file tmp, ri-sollevare eccezione
```

Questo previene la corruzione quando l'applicazione crasha durante la scrittura o
quando il sistema perde alimentazione durante l'addestramento.

### Catena di Caricamento Multi-Fallback

```
load_nn(version, model, user_id=None)
  1. Tentare: models/{user_id}/{version}.pt         (modello appreso specifico utente)
  2. Tentare: models/global/{version}.pt            (baseline condivisa)
  3. Tentare: factory incluso/{user_id}/{version}.pt (incluso PyInstaller, utente)
  4. Tentare: factory incluso/global/{version}.pt   (incluso PyInstaller, globale)
  5. Fallire: sollevare FileNotFoundError            (mai pesi random silenziosi)
```

Prima che i pesi tocchino il modello, il file risolto viene verificato contro il
registro hash CTF-1, e il suo sidecar `.pt.meta.json` (se presente) viene
validato per `schema_version`, `metadata_dim` e drift dei nomi delle feature --
qualsiasi discrepanza solleva `StaleCheckpointError`. I checkpoint legacy senza
sidecar vengono caricati con un avviso.

### Validazione Dimensionale

Durante il caricamento, viene utilizzato `model.load_state_dict(state_dict, strict=True)`.
Se il checkpoint è stato prodotto da un modello con architettura diversa (es. dopo
che `METADATA_DIM` è cambiato da 25 a 26), il caricamento fallisce con un
`RuntimeError`. Il modulo di persistenza lo cattura e solleva
`StaleCheckpointError`, che segnala ai chiamanti che è necessario un ri-addestramento.

## Avvisi Critici

| ID | Regola | Conseguenza della Violazione |
|----|--------|------------------------------|
| NN-14 | Mai restituire silenziosamente un modello con pesi random | Output di coaching spazzatura, fiducia utente distrutta |
| NN-16 | EMA `apply_shadow()` deve `.clone()` i tensori shadow | Corruzione addestramento, non recuperabile |
| NN-MEM-01 | Memoria Hopfield bypassata fino a `notify_optimizer_step()` | Propagazione NaN nella memoria RAP |
| — | `WinProbabilityNN` (12 feature) vs `WinProbabilityTrainerNN` (9 feature) | Crash da cross-loading o corruzione silenziosa |

`WinProbabilityNN` (produzione, 12 feature) e `WinProbabilityTrainerNN`
(addestramento offline, 9 feature) utilizzano **architetture diverse**. I loro
checkpoint non sono intercambiabili. Mai incrociare il caricamento tra di essi.

Dopo qualsiasi modifica architetturale (modifica di `METADATA_DIM`, `HIDDEN_DIM`,
`OUTPUT_DIM` o struttura dei layer), tutti i checkpoint esistenti diventano invalidi.
Il sistema rileva questo automaticamente tramite caricamento `strict=True` e solleva
`StaleCheckpointError`.

## Versionamento dei Modelli

I checkpoint sono versionati dal loro nome file (parametro `version` in
`save_nn` / `load_nn`); il sidecar `.pt.meta.json` incorpora inoltre una
`schema_version` (GAP-07). La compatibilità è imposta sia dal controllo del
sidecar che strutturalmente: se le chiavi del `state_dict` o le forme dei tensori
non corrispondono alla classe del modello corrente, il caricamento fallisce
deterministicamente.

| Stringa Versione | Modello | Fonte di Addestramento |
|-----------------|---------|------------------------|
| `latest` | AdvancedCoachNN | Pipeline di addestramento predefinita (`train.py`, `coach_manager.py`) |
| `jepa_brain` | Modello coaching JEPA | Dataset demo professionali (addestramento JEPA a due stadi) |
| `vl_jepa_brain` | VL-JEPA | Dataset demo professionali (addestramento concept-head) |
| `rap_coach` | RAPCoachModel | Dataset demo professionali (addestramento RAP LTC-Hopfield) |
| `rap_lite_coach` | RAP-Lite | Addestramento RAP con memoria LSTM di fallback |
| `role_head` | NeuralRoleHead | Dataset classificazione ruoli |
| `win_prob` | WinProbabilityTrainerNN | Dataset esiti dei round (utility offline; nessun chiamante in produzione -- il predittore resta euristico fino al ri-addestramento a 12 dim) |

Le run complete richiedono il database di addestramento monolite; consultare
`docs/OPEN_ISSUES.md` §2 per le attività di dati e addestramento in sospeso.

## Bundling (PyInstaller)

La catena di caricamento supporta checkpoint inclusi nella factory:
`get_factory_model_path()` li risolve tramite `get_resource_path()`, che
controlla `sys._MEIPASS` nell'ambiente congelato. Si noti che l'attuale
`packaging/cs2_analyzer_win.spec` **non** include una voce `models/` nella sua
lista `datas`, quindi i livelli factory si risolvono solo quando un build
include esplicitamente i checkpoint.

## Punti di Integrazione

| Consumatore | Checkpoint | Operazione |
|-------------|-----------|------------|
| `backend/nn/training_orchestrator.py` | `jepa_brain.pt`, `vl_jepa_brain.pt`, `rap_coach.pt` (+ varianti `_latest`) | Caricamento/salvataggio con gestione `StaleCheckpointError`; unico scrittore per gli addestramenti orchestrati |
| `backend/nn/coach_manager.py` | `latest.pt` | Salvataggio modelli globali/utente; caricamento per inferenza |
| `backend/nn/role_head.py` | `role_head.pt` | Salvataggio/caricamento tramite `save_nn()` / `load_nn()` |
| `backend/nn/jepa_train.py` | `jepa_model.pt`, `jepa_model_finetuned.pt` | Pipeline standalone a due stadi (proprio formato checkpoint) |
| `backend/nn/win_probability_trainer.py` | percorso fornito dal chiamante | Utility offline (`torch.save` grezzo, attualmente non chiamata) |

## Note di Sviluppo

- **NON committare file `.pt`** nel repository -- sono artefatti binari di grandi dimensioni
- La directory `global/` deve esistere nel repo (preservata da `README.txt`)
- I log di addestramento sono scritti da `backend/nn/training_monitor.py` (formato JSON), non archiviati qui
- Il percorso `MODELS_DIR` viene risolto da `core/config.py` e predefinito a questa directory
- Quando `BRAIN_DATA_ROOT` (o, come fallback, `CUSTOM_STORAGE_PATH`) è impostato ed esiste,
  i modelli vengono scritti in `{BRAIN_DATA_ROOT}/models/`
- `checkpoint_hashes.json` è indicizzato per percorso assoluto del checkpoint; le voci sono
  state registrate durante le run di addestramento su vari volumi di storage locali
- Usare sempre `save_nn()` / `load_nn()` da `persistence.py` -- mai chiamare `torch.save()` direttamente
- Dopo modifiche all'architettura del modello, eliminare i checkpoint obsoleti e ri-addestrare da zero
