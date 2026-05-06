# `backend/nn/experimental/rap_coach/` — RAP Coach (sperimentale)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/`
> **Skill:** `/ml-check`, `/jepa-audit`
> **Stato:** Sperimentale — gated dietro `USE_RAP_MODEL=True`. Non caricato dalla pipeline di coaching di default.

## Scopo

RAP Coach (**R**easoning + **A**cting + **P**edagogy) è una rete policy multi-head che consuma l'embedding del world-model JEPA più lo stato per tick e produce:

- Una label di **strategy** a 10 dimensioni (one-hot sui ruoli tattici canonici).
- Una stima scalare di **value** della probabilità di vincere il round.
- Un forecast di delta di **position** a 3 dimensioni per il giocatore.
- Un segnale scalare di **sparsity** che pilota la regolarizzazione L1 sui gate di strategy.

Architetturalmente è una pipeline a 7 stadi — perception → memory → strategy → pedagogy → communication — costruita sopra le celle Liquid Time-Constant (LTC) di `ncps` per il ragionamento temporale lungo la finestra di 32 tick (`RAP_SEQ_LEN`).

## Inventario dei file

| File | Componente | Scopo |
|------|-----------|---------|
| `__init__.py` | — | Marker di package. |
| `perception.py` | `RAPPerception` | Aggregatore di feature visive / spaziali. Consuma view per tick, mini-mappa e tensori di motion e proietta verso un embedding di percezione unificato. |
| `memory.py` | `RAPMemory` | Memoria temporale basata su LTC sulla finestra di 32 tick. **Contiene il monkey-patch RAP-LTC-FIX** su `ncps.LTCCell._ode_solver` (righe 70–93) — patcha un mismatch di shape 1-D / 2-D in `cm / (elapsed_time / ode_unfolds)`. |
| `strategy.py` | `RAPStrategy` | Head di strategy: layer di sovrapposizione + softmax a 10 classi sui ruoli tattici. |
| `pedagogy.py` | `RAPPedagogy` | Head di pedagogy: explanation prior — produce una rappresentazione a bassa dimensione a valle della decisione di strategy, usata per l'explainability. |
| `communication.py` | `RAPCommunication` | Head di communication: piccola MLP su cui lo strato RAG / coaching può condizionarsi per la generazione di prosa policy-aware. |
| `chronovisor_scanner.py` | `ChronovisorScanner` | Identifica "momenti" temporalmente critici in un replay usando le head di strategy + value. Fornisce marker al Tactical Viewer. |
| `model.py` | `RAPCoachModel` | Compone i 7 stadi. Caricato via `ModelFactory.get_model('rap')`. Dimensioni inizializzate: `metadata_dim=25`, `output_dim=10`, `hidden=256`, `perception=128`. |
| `trainer.py` | `RAPTrainer` | Driver di training: loss composita (strategy + value + sparsity + position), penalità sull'asse Z, AMP, scheduler. Costruito da `TrainingOrchestrator(model_type='rap')`. |
| `conftest.py` | — | Fixture pytest locali a questo package (es. fixture RAP minuscola per i test di architettura). |
| `test_arch.py` | — | Test che verificano shape del forward-pass e flusso dei gradienti su una piccola batch sintetica. Gira in CI senza demo reali. |

## Attivazione

```python
# Default in core/config.py
"USE_RAP_MODEL": False,    # default

# Abilita per una sessione tramite il dict _settings (nessuna scrittura su disco):
from Programma_CS2_RENAN.core import config
with config._settings_lock:
    config._settings["USE_RAP_MODEL"] = True

# Oppure persisti tramite:
from Programma_CS2_RENAN.core.config import save_user_setting
save_user_setting("USE_RAP_MODEL", True)
```

`TrainingOrchestrator.__init__` solleva `ValueError` se `model_type='rap'` viene richiesto mentre il flag è `False`. Protegge da run di training non intenzionali.

## Training

Entry point: `run_full_training_cycle.py --dry-run --model-type rap --epochs 1`

Oppure programmaticamente:

```python
from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager

manager = CoachTrainingManager()
manager.assign_dataset_splits()
orch = TrainingOrchestrator(manager, model_type="rap", max_epochs=1, patience=1)
orch.run_training()
```

## Invarianti critiche

| ID | File / riga | Invariante |
|----|-------------|-----------|
| RAP-LTC-FIX | `memory.py:70-93` | Patch di shape su `_ode_solver` — deve restare in posizione; futuri upgrade di ncps potrebbero renderla ridondante ma non devono romperla in silenzio. |
| RAP-AUDIT-01 | `trainer.py`, `training_orchestrator.py:496` | `RAP_SEQ_LEN = 32` — finestra temporale per il processing di sequenze LTC. Deve coincidere con il default di `state_reconstructor.py`. |
| RAP-AUDIT-02 | `training_orchestrator.py:_rap_compute_target_pos` | Delta di posizione per tick richiesti per il training della head di position. |
| RAP-AUDIT-05 | `training_orchestrator.py:_rap_compute_timespans` | `dt` inter-tick richiesto per l'integrazione ODE della LTC. Costante 1/64 s nei replay canonici ma mantenuto tensoriale per supportare in futuro tick variabili. |
| LEAK-01 | `training_orchestrator.py:686-693` | `val_mask=False` quando la knowledge non è disponibile, così la head di value non si allena mai sull'esito del round leakato. |
| NN-TR-02b | `trainer.py:43-100` | Penalità sull'asse Z imposta nella loss di position per prevenire drift verticale su mappe multi-livello. |
| POV-RAP-FIX-2 | `training_orchestrator.py:632-637` | Fallback di `match_id` da `demo_name_to_match_id` quando la FK del DB è `None`. |
| T-2 FIX | `training_orchestrator.py:756-780` | Gate ≥ 50% di densità POV per finestra temporale. |

I test per queste invarianti vivono in `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py` e `Programma_CS2_RENAN/tests/test_rap_coach.py`.

## Confini

- **Non importare moduli RAP da codice di coaching in produzione.** `coaching_service.py` seleziona il backend RAP tramite `ModelFactory.get_model('rap')`, che solleva eccezione se il flag non è impostato. Gli import diretti aggirano il gate.
- **Non modificare `RAP_SEQ_LEN` senza ri-allenare tutti i checkpoint RAP.** Fa parte del contratto di architettura.
- **Non rimuovere il monkey-patch `RAP-LTC-FIX`.** Il bug di shape in upstream ncps si applica ancora a HEAD. Il test CI in `test_rap_training_dry_run.py` asserisce che il marker della fix sia presente.

## Correlati

- Parent della sandbox sperimentale: `backend/nn/experimental/README.md`
- Sotto-package NN di produzione: `backend/nn/README.md`
- Training orchestrator: `backend/nn/training_orchestrator.py`
- Smoke test / regressione: `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py`
- ncps upstream: <https://github.com/mlech26l/ncps>
- Documenti originali sull'architettura: `docs/Studies/` (volumi RAP)
