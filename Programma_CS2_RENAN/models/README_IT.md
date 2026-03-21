> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Archiviazione Checkpoint Reti Neurali

> **Autorità:** Regola 4 (Persistenza Dati)

Questa directory archivia i checkpoint delle reti neurali addestrate (file `.pt`)
utilizzati dal Ghost Engine per l'inferenza in tempo reale e dalla pipeline di
coaching per la generazione di suggerimenti potenziati da ML. I checkpoint sono
serializzazioni binarie `state_dict` di PyTorch gestite esclusivamente tramite il
modulo `persistence.py`, che impone scritture atomiche, caricamento multi-fallback
e validazione dimensionale rigorosa.

Nessun file `.pt` viene committato nel repository. Questa directory esiste nel
version control unicamente per preservare la sua struttura (tramite
`global/README.txt`) e per servire come destinazione di scrittura predefinita
quando `BRAIN_DATA_ROOT` non è configurato.

## Struttura della Directory

```
models/
├── global/                   # Modelli baseline condivisi (non specifici per utente)
│   └── README.txt           # Segnaposto per preservare la directory in git
├── README.md                 # Questo file (Inglese)
├── README_IT.md              # Traduzione Italiana
└── README_PT.md              # Traduzione Portoghese
```

A runtime, i modelli personalizzati per utente vengono archiviati in sottodirectory per utente:

```
models/
├── global/                  # Baseline condivisa (da addestramento demo professionali)
│   ├── jepa_brain.pt       # JEPA pre-addestrato su match professionali
│   ├── rap_coach.pt        # Checkpoint modello RAP
│   └── win_prob.pt         # Modello probabilità di vittoria
└── {user_id}/               # Modelli personalizzati per utente (futuro)
    └── jepa_brain.pt       # Checkpoint JEPA adattato all'utente
```

## Inventario dei Checkpoint

| Checkpoint | Classe Modello | Creato Da | Dimensione Tipica | Input Dim |
|-----------|---------------|-----------|-------------------|-----------|
| `jepa_brain.pt` | JEPACoachingModel | `backend/nn/jepa_trainer.py` | ~3.6 MB | 25 (METADATA_DIM) |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/experimental/rap_coach/trainer.py` | Variabile | 25 (METADATA_DIM) |
| `coach_brain.pt` | AdvancedCoachNN (legacy) | `backend/nn/train.py` | ~1 MB | 25 (METADATA_DIM) |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` | ~100 KB | 9 (sottoinsieme offline) |
| `role_head.pt` | NeuralRoleHead | Addestramento classificazione ruoli | ~50 KB | Variabile |

## Formato dei Checkpoint

Ogni file `.pt` è un dizionario `state_dict` di PyTorch salvato tramite `torch.save()`.
Le chiavi corrispondono ai parametri nominati della classe del modello. Struttura di
esempio per `jepa_brain.pt`:

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

Il modulo `backend/nn/persistence.py` è l'**unica** interfaccia per l'I/O dei
checkpoint. Chiamate dirette a `torch.save()` / `torch.load()` da altri moduli
sono proibite.

### Protocollo di Scrittura Atomica

```
save_nn(model, version, user_id=None)
  1. Risolvere il percorso destinazione: models/{user_id o "global"}/{version}.pt
  2. Scrivere su file temporaneo: {version}.pt.tmp
  3. Sostituzione atomica: tmp_path.replace(path)  # atomico su POSIX
  4. In caso di errore: eliminare tmp, ri-sollevare eccezione
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
| NN-MEM-01 | Hopfield bypassato fino a >=2 forward pass di addestramento | Propagazione NaN nella memoria RAP |
| — | `WinProbabilityNN` (12 feature) vs `WinProbabilityTrainerNN` (9 feature) | Crash da cross-loading o corruzione silenziosa |

`WinProbabilityNN` (produzione, 12 feature) e `WinProbabilityTrainerNN`
(addestramento offline, 9 feature) utilizzano **architetture diverse**. I loro
checkpoint non sono intercambiabili. Mai incrociare il caricamento tra di essi.

Dopo qualsiasi modifica architetturale (modifica di `METADATA_DIM`, `HIDDEN_DIM`,
`OUTPUT_DIM` o struttura dei layer), tutti i checkpoint esistenti diventano invalidi.
Il sistema rileva questo automaticamente tramite caricamento `strict=True` e solleva
`StaleCheckpointError`.

## Versionamento dei Modelli

I checkpoint sono versionati implicitamente dal loro nome file (parametro `version`
in `save_nn` / `load_nn`). Non esiste un numero di versione esplicito incorporato
nel checkpoint. La compatibilità è imposta strutturalmente: se le chiavi del
`state_dict` o le forme dei tensori non corrispondono alla classe del modello
corrente, il caricamento fallisce deterministicamente.

| Stringa Versione | Modello | Fonte di Addestramento |
|-----------------|---------|------------------------|
| `jepa_brain` | JEPACoachingModel | Dataset demo professionali (addestramento JEPA a due stadi) |
| `rap_coach` | RAPCoachModel | Dataset demo professionali (addestramento RAP LTC-Hopfield) |
| `coach_brain` | AdvancedCoachNN | Pipeline di addestramento legacy |
| `win_prob` | WinProbabilityTrainerNN | Dataset esiti dei round |
| `role_head` | NeuralRoleHead | Dataset classificazione ruoli |

## Bundling (PyInstaller)

La sottodirectory `global/` è inclusa nell'eseguibile congelato:

```python
# In cs2_analyzer_win.spec
datas += [('models/global', 'models/global')]
```

A runtime, `get_factory_model_path()` risolve i checkpoint inclusi tramite
`get_resource_path()`, che controlla `sys._MEIPASS` per l'ambiente congelato.

## Punti di Integrazione

| Consumatore | Checkpoint | Operazione |
|-------------|-----------|------------|
| `backend/nn/jepa_trainer.py` | `jepa_brain.pt` | Scrittura dopo epoca di addestramento |
| `backend/nn/coach_manager.py` | `jepa_brain.pt`, `coach_brain.pt` | Caricamento per inferenza |
| `backend/nn/training_orchestrator.py` | Tutti | Caricamento/salvataggio con gestione `StaleCheckpointError` |
| `backend/nn/experimental/rap_coach/trainer.py` | `rap_coach.pt` | Scrittura dopo addestramento RAP |
| `backend/nn/win_probability_trainer.py` | `win_prob.pt` | Scrittura dopo addestramento win-prob |

## Note di Sviluppo

- **NON committare file `.pt`** nel repository — sono artefatti binari di grandi dimensioni
- La directory `global/` deve esistere nel repo (preservata da `README.txt`)
- I log di addestramento sono scritti da `backend/nn/training_monitor.py` (formato JSON), non archiviati qui
- Il percorso `MODELS_DIR` viene risolto da `core/config.py` e predefinito a questa directory
- Quando `BRAIN_DATA_ROOT` è impostato, i modelli vengono scritti in `{BRAIN_DATA_ROOT}/models/`
- Usare sempre `save_nn()` / `load_nn()` da `persistence.py` — mai chiamare `torch.save()` direttamente
- Dopo modifiche all'architettura del modello, eliminare i checkpoint obsoleti e ri-addestrare da zero
