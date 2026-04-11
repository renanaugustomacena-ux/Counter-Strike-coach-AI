> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Neural Network Subsystem — Architetture dei Modelli & Infrastruttura di Addestramento

> **Autorita:** `Programma_CS2_RENAN/backend/nn/`
> **Dipende da:** `backend/processing/feature_engineering/` (vettore di feature a 25 dimensioni), `backend/storage/` (SQLite WAL), `core/config.py` (impostazioni)
> **Consumato da:** `backend/services/` (servizio di coaching), `backend/coaching/` (motore ibrido), `apps/qt_app/` (UI)

## Introduzione

Questo pacchetto costituisce il nucleo di machine learning del sistema di coaching CS2. Contiene sei architetture di reti neurali distinte, un orchestratore di addestramento unificato con strumentazione basata su callback a plugin, e un motore di inferenza in tempo reale (GhostEngine). Ogni modello consuma il vettore canonico di feature a 25 dimensioni prodotto da `FeatureExtractor` in `backend/processing/feature_engineering/vectorizer.py`. Tutta l'aleatorietà è seminata tramite `GLOBAL_SEED = 42` per esecuzioni di addestramento deterministiche e riproducibili.

La pipeline di addestramento è stata validata end-to-end il 12 marzo 2026: 11 demo professionali ingerite (17.3M righe tick, database da 6.4 GB), dry-run JEPA completato producendo `jepa_brain.pt` (3.6 MB).

## Inventario dei File

| File | Scopo |
|------|-------|
| `config.py` | Costanti centrali (`INPUT_DIM=25`, `OUTPUT_DIM=10`, `HIDDEN_DIM=128`, `GLOBAL_SEED=42`, `RAP_POSITION_SCALE=500.0`), `set_global_seed()`, `get_device()` con selezione GPU discreta |
| `model.py` | `AdvancedCoachNN` (LSTM + Mixture of Experts), dataclass `CoachNNConfig`, `ModelManager` per salvataggio checkpoint versionato |
| `jepa_model.py` | `JEPAEncoder`, `JEPACoachingModel`, `VLJEPACoachingModel` -- JEPA auto-supervisionato con loss contrastivo InfoNCE e dizionario di concetti |
| `jepa_train.py` | Script di addestramento JEPA a due fasi (pre-training + fine-tuning), `_MIN_ROUNDS_FOR_SEQUENCE = 6` |
| `jepa_trainer.py` | Loop di addestramento JEPA a basso livello con aggiornamento EMA dell'encoder target |
| `ema.py` | Classe `EMA` -- media mobile esponenziale per gestione pesi shadow (invariante NN-16: `.clone()` su `apply_shadow()`) |
| `role_head.py` | `NeuralRoleHead` (input 5-dim, output softmax 5-dim, ~750 parametri), helper di addestramento e inferenza per classificazione del ruolo del giocatore |
| `win_probability_trainer.py` | `WinProbabilityTrainerNN` -- modello leggero a 9 feature per probabilità di vittoria offline su DataFrame di partite pro |
| `dataset.py` | `ProPerformanceDataset` (supervisionato) e `SelfSupervisedDataset` (coppie contesto/target JEPA a finestra scorrevole) |
| `factory.py` | `ModelFactory` -- factory statica per istanziazione unificata di tutti i tipi di modello (`default`, `jepa`, `vl-jepa`, `rap`, `rap-lite`, `role_head`) |
| `persistence.py` | `save_nn()`, `load_nn()`, `get_model_path()` con scrittura atomica (`tmp + os.replace`), `StaleCheckpointError` |
| `early_stopping.py` | `EarlyStopping` con soglie configurabili di pazienza e delta minimo |
| `training_config.py` | Dataclass `TrainingConfig` e `JEPATrainingConfig` che centralizzano tutti gli iperparametri |
| `training_orchestrator.py` | `TrainingOrchestrator` -- loop unificato per epoca con validazione, early stopping, checkpointing, scheduling LR e dispatch dei callback |
| `training_controller.py` | `TrainingController` -- deduplicazione demo, controlli di diversità, gestione quota mensile, logica start-stop |
| `coach_manager.py` | `CoachTrainingManager` -- orchestrazione ad alto livello con gate di maturità a 3 fasi (doubt / learning / conviction) |
| `train.py` | `train_nn()` -- punto d'ingresso legacy per addestramento di `AdvancedCoachNN` |
| `training_callbacks.py` | `TrainingCallback` (ABC, hook opt-in) e `CallbackRegistry` (dispatcher eventi con isolamento errori) |
| `tensorboard_callback.py` | `TensorBoardCallback` -- registra 9+ segnali scalari, istogrammi parametri/gradienti, layout scalari personalizzati |
| `maturity_observatory.py` | `MaturityObservatory` -- indice di convinzione a 5 segnali (belief entropy, gate specialization, concept focus, value accuracy, role stability), macchina a 5 stati (doubt / crisis / learning / conviction / mature) |
| `embedding_projector.py` | `EmbeddingProjector` -- proiezioni UMAP 2D e esportazione embedding TensorBoard per visualizzazione dello spazio belief/concept |
| `training_monitor.py` | `TrainingMonitor` -- metriche per epoca persistite in JSON con scrittura atomica per monitoraggio progresso in tempo reale |
| `evaluate.py` | `evaluate_adjustments()` -- valutazione compatibile SHAP degli aggiustamenti di peso del modello per feature |
| `data_quality.py` | `DataQualityReport` -- controlli di qualità dati pre-addestramento (tasso NaN, tasso posizione zero, bilanciamento classi) |

## Sotto-pacchetti

| Pacchetto | Scopo |
|-----------|-------|
| `rap_coach/` | Modello RAP Coach: architettura pedagogica a 7 livelli (Perception, Memory, Strategy, Pedagogy, Communication, ChronovisorScanner, SkillModel). Richiede `ncps` + `hflayers` per la memoria LTC-Hopfield. |
| `advanced/` | **Stub vuoto intenzionale.** Moduli originali rimossi nella remediazione G-06. Namespace riservato per esperimenti futuri. Vedere `advanced/README.md`. |
| `inference/` | `GhostEngine` -- motore di previsione in tempo reale che traduce lo stato di gioco tick-level in suggerimenti di coaching tramite `RAP_POSITION_SCALE`. |
| `layers/` | `SuperpositionLayer` -- layer lineare con gating contestuale che abilita la fusione dinamica di modalità con regolarizzazione L1 di sparsità e hook di osservabilità. |
| `experimental/` | Variante sperimentale RAP Coach con moduli separati Perception, Strategy, Pedagogy, Communication, Memory e harness di test. |

## Architetture dei Modelli

### 1. JEPA (`jepa_model.py`) -- Percorso di Addestramento Primario

Architettura Joint-Embedding Predictive auto-supervisionata. Protocollo a due fasi: (1) pre-training su demo professionali con loss contrastivo InfoNCE + dizionario di concetti per allineamento semantico, (2) fine-tuning LSTM su dati utente. Utilizza encoder target EMA (`requires_grad=False` durante l'aggiornamento, invariante NN-JM-04). Dim latente: 256, dim nascosta LSTM: 128.

### 2. RAP Coach (`rap_coach/`) -- Architettura della Grande Visione

Modello pedagogico a 7 livelli: Perception basata su ResNet, Memory LTC-Hopfield (512 slot associativi, `ncp_units=512`, `belief_dim=64`), Strategy con SuperpositionLayer e gating contestuale, Pedagogy causale per attribuzione errori, Communication in linguaggio naturale, ChronovisorScanner per analisi temporale multi-scala, e SkillModel per stima delle abilità del giocatore. Hopfield è bypassato fino a 2+ forward pass di addestramento (invariante NN-MEM-01).

### 3. AdvancedCoachNN (`model.py`) -- Modello Supervisionato Legacy

Encoder di sequenza LSTM + Mixture of Experts (3 esperti di default) con LayerNorm, gating con bias del ruolo e clamping dell'output con `tanh`. Alias come `TeacherRefinementNN` per compatibilità.

### 4. NeuralRoleHead (`role_head.py`) -- Classificazione dei Ruoli

MLP leggero (5 -> 32 -> 16 -> 5, ~750 parametri) che predice le probabilità dei ruoli del giocatore da metriche di stile di gioco (TAPD, OAP, PODT, rating impact, aggression). Loss KL-divergence con label smoothing. Funziona come opinione secondaria insieme al classificatore euristico `RoleClassifier`.

### 5. WinProbabilityTrainerNN (`win_probability_trainer.py`) -- Predizione Vittoria Offline

Modello a 9 feature (vivi, salute, armatura, equipaggiamento, stato bomba) per addestramento offline su DataFrame di partite pro. Separato dal predittore real-time `WinProbabilityNN` in `backend/analysis/` (12 feature, dim nascoste 64/32). I checkpoint NON sono intercambiabili.

### 6. VL-JEPA (`jepa_model.py`) -- Estensione Vision-Language

Estende JEPA con comprensione tattica visivo-linguistica per spiegazioni di coaching a livello di concetto.

## Costanti Chiave

| Costante | Valore | Definita in |
|----------|--------|-------------|
| `INPUT_DIM` / `METADATA_DIM` | 25 | `config.py`, `vectorizer.py` |
| `OUTPUT_DIM` | 10 | `config.py` |
| `HIDDEN_DIM` | 128 | `config.py` |
| `GLOBAL_SEED` | 42 | `config.py` |
| `BATCH_SIZE` | 32 | `config.py` |
| `LEARNING_RATE` | 0.001 | `config.py` |
| `RAP_POSITION_SCALE` | 500.0 | `config.py` |
| `WEIGHT_CLAMP` | 0.5 | `config.py` |
| RAP `hidden_dim` | 256 | `rap_coach/model.py` |
| RAP `ncp_units` | 512 | `rap_coach/memory.py` |
| RAP `belief_dim` | 64 | `rap_coach/memory.py` |
| JEPA `latent_dim` | 256 | `jepa_model.py` |
| JEPA LSTM `hidden_dim` | 128 | `jepa_model.py` |

## Coach Introspection Observatory

La pipeline di addestramento include uno stack di osservabilità a 4 livelli, implementato come plugin `TrainingCallback`:

1. **Livello 1 -- CallbackRegistry** (`training_callbacks.py`): Architettura a plugin con isolamento errori. I callback non causano mai crash dell'addestramento.
2. **Livello 2 -- TensorBoardCallback** (`tensorboard_callback.py`): Scalari (loss, LR, sparsità, dinamiche gate), istogrammi (parametri, gradienti, belief, concetti), layout dashboard personalizzati.
3. **Livello 3 -- MaturityObservatory** (`maturity_observatory.py`): Indice di convinzione a 5 segnali con smoothing EMA e macchina di classificazione a 5 stati (doubt / crisis / learning / conviction / mature).
4. **Livello 4 -- EmbeddingProjector** (`embedding_projector.py`): Proiezioni UMAP 2D dei vettori belief e degli embedding di concetti, esportati su TensorBoard.

## Invarianti Critici

| ID | Regola |
|----|--------|
| P-RSB-03 | `round_won` ESCLUSO dalle feature di addestramento (fuga di etichetta) |
| NN-MEM-01 | Hopfield bypassato fino a 2+ forward pass di addestramento |
| NN-16 | EMA `apply_shadow()` deve usare `.clone()` sui tensori shadow |
| NN-JM-04 | Encoder target `requires_grad=False` durante aggiornamento EMA |
| P-X-01 | Asserzione compile-time `len(FEATURE_NAMES) == METADATA_DIM` |
| P-VEC-02 | NaN/Inf nelle feature attivano log ERROR + clamp |
| P3-A | >5% NaN/Inf nel batch solleva `DataQualityError` |

## Note di Sviluppo

- **Riproducibilità:** Chiamare sempre `set_global_seed(42)` prima delle esecuzioni di addestramento.
- **Selezione dispositivo:** `get_device()` seleziona automaticamente la GPU discreta per VRAM; sovrascrivibile tramite impostazione `CUDA_DEVICE`.
- **Allineamento feature:** Qualsiasi modifica al vettore a 25 dimensioni deve aggiornare simultaneamente `FEATURE_NAMES`, `METADATA_DIM`, docstring di `extract()` e tutte le asserzioni `input_dim` dei modelli.
- **Dipendenze opzionali:** RAP Coach richiede `ncps` e `hflayers`. Le importazioni sono protette con `try/except`; verificare `_RAP_DEPS_AVAILABLE` prima dell'istanziazione.
- **Scritture atomiche:** Tutti i salvataggi checkpoint e la persistenza JSON usano `tmp + os.replace()` per prevenire corruzione in caso di crash.
- **La decimazione dei tick è RIGOROSAMENTE VIETATA** -- tutti i dati tick-level devono essere preservati come ingeriti.

## Utilizzo

```python
from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
from Programma_CS2_RENAN.backend.nn.config import set_global_seed

set_global_seed(42)
model = ModelFactory.get_model("jepa")

from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
orchestrator = TrainingOrchestrator(manager, model_type="jepa", max_epochs=50)
```
