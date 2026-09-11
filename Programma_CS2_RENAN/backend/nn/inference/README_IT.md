# `backend/nn/inference/` -- Utilita neurali sola-inferenza

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** `Programma_CS2_RENAN/backend/nn/inference/`
> **Skill:** `/ml-check`

## Scopo

Questo pacchetto contiene componenti di rete neurale usati **esclusivamente in inferenza** -- consumano checkpoint gia addestrati, non eseguono mai loop di training, e non possiedono mai stato lato training (optimizer, scheduler, EMA shadow, ecc.).

L'intento e tenere i percorsi di training e inferenza fisicamente separati nell'albero sorgente cosi che:

- Un deployment pure-inference (senza optimizer PyTorch, senza DataLoader) importa una superficie piu piccola.
- Invarianti solo-training (flusso del gradiente, cloning EMA, freezing del target encoder) non possano fluire in percorsi di inferenza.
- I test sul comportamento di inferenza possano essere scritti senza mettere in piedi un trainer.

## Inventario File

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto. |
| `ghost_engine.py` | `GhostEngine` -- proietta le posizioni predette dei giocatori sulla mappa tattica per l'overlay "ghost AI" nel Tactical Viewer. Gated dietro `USE_RAP_MODEL` (default `False`); carica il checkpoint `rap_coach` ed esegue inferenza forward-only per tick. |

## Riassunto di `GhostEngine`

- Controlla prima `USE_RAP_MODEL` (default `False`) -- quando non impostato, nessun modello viene caricato e le predizioni restano disabilitate.
- Carica il modello RAP tramite `ModelFactory.get_model(TYPE_RAP)` + `load_nn(ModelFactory.get_checkpoint_name(TYPE_RAP), ...)` (nome checkpoint `"rap_coach"`), poi `.eval()`; l'inferenza gira sotto `torch.no_grad()`.
- `predict_tick()` accetta un singolo tick (dict o dataclass) piu un `game_state` dict opzionale, costruisce tensori di view / map / motion tramite `TensorFactory` e il vettore metadata a 25 dimensioni tramite `FeatureExtractor`, e restituisce `(ghost_x, ghost_y)` coordinate mondo (posizione corrente + delta x `RAP_POSITION_SCALE`).
- I tensori provengono da un `TensorFactory` istanziato con `TrainingTensorConfig()` (risoluzione 64x64 per tutti i canali), corrispondente alla risoluzione di training (F-0026 chiuso).
- La modalita tensori player-POV e opt-in tramite `USE_POV_TENSORS` (default `False`); altrimenti si usano i tensori legacy.
- Restituisce `None` in caso di fallimento -- modello disabilitato, checkpoint mancante, `map_name` mancante o errore di inferenza. (R4: il vecchio sentinella `(0.0, 0.0)` era una coordinata mondo valida vicino al centro mappa ed e stato rimosso.)

## Punti di integrazione

| Consumer | Uso |
|----------|-----|
| `apps/qt_app/screens/tactical_viewer_screen.py` | Renderizza le proiezioni ghost sull'overlay della mappa tattica |
| `apps/qt_app/viewmodels/tactical_vm.py` (`TacticalGhostVM`) | Carica l'engine in modo lazy on demand per evitare costo di startup |

## Note di sviluppo

- **Nessun import lato training.** I moduli qui non devono importare da `training_orchestrator.py`, trainer, helper EMA, o assemblaggi DataLoader.
- **Nessuna mutazione di file.** Le utilita di inferenza non scrivono mai checkpoint. Il salvataggio appartiene a `nn/persistence.py:save_nn()` invocato dai percorsi di training.
- **Determinismo.** L'inferenza viene invocata da thread UI -- proteggi qualsiasi operazione tensoriale non idempotente (es. dropout) con `model.eval()`.
- **Degradazione graziosa.** Checkpoint mancante o inferenza fallita -> restituisce `None`, log a `WARNING`. Mai sollevare nel thread UI.

## Correlati

- Checkpoint addestrati: `Programma_CS2_RENAN/models/global/`
- Helper di persistenza: `backend/nn/persistence.py`
- Consumer con caricamento lazy: `apps/qt_app/viewmodels/tactical_vm.py` (`TacticalGhostVM`)
- Tactical viewer (consumer): `apps/qt_app/screens/tactical_viewer_screen.py`
