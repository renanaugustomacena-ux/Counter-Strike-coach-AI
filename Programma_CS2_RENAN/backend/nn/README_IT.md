> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sottosistema Reti Neurali — Architetture dei Modelli & Infrastruttura di Addestramento

> **Autorità:** `Programma_CS2_RENAN/backend/nn/`
> **Dipende da:** `backend/processing/feature_engineering/` (vettore di feature a 25 dimensioni), `backend/storage/` (SQLite WAL), `core/config.py` (impostazioni)
> **Consumato da:** `backend/services/` (servizio di coaching), `backend/coaching/` (motore ibrido), `apps/qt_app/` (UI)

## Introduzione

Questo pacchetto costituisce il nucleo di machine learning del sistema di coaching CS2. Contiene sei architetture di reti neurali distinte, un orchestratore di addestramento unificato con strumentazione basata su callback a plugin, e un motore di inferenza in tempo reale (GhostEngine). Ogni modello consuma il vettore canonico di feature a 25 dimensioni prodotto da `FeatureExtractor` in `backend/processing/feature_engineering/vectorizer.py`. Tutta l'aleatorietà è seminata tramite `GLOBAL_SEED = 42` per esecuzioni di addestramento deterministiche e riproducibili.

La ricostruzione del 2026-09-01 ha azzerato tutti i pesi di produzione; i checkpoint pre-ricostruzione sono archiviati in `models/global/archive_pre_rebuild_2026-09-01/`.

## Inventario dei File

| File | Scopo |
|------|-------|
| `config.py` | Costanti centrali (`INPUT_DIM=25`, `OUTPUT_DIM=10`, `HIDDEN_DIM=128`, `GLOBAL_SEED=42`, `RAP_POSITION_SCALE=500.0`), `set_global_seed()`, `get_device()` con selezione GPU discreta |
| `model.py` | `AdvancedCoachNN` (LSTM + Mixture of Experts), dataclass `CoachNNConfig`, `ModelManager` per salvataggio checkpoint versionato |
| `jepa_model.py` | `JEPAEncoder`, `JEPACoachingModel`, `VLJEPACoachingModel`, `ConceptLabeler` -- JEPA auto-supervisionato con loss contrastivo InfoNCE, regolarizzazione VICReg e contrasto momentum MoCo |
| `jepa_train.py` | Script di addestramento JEPA a due fasi (pre-training + fine-tuning) su sequenze tick-level `PlayerTickState` con windowing seminato (J-1), `_MIN_TICKS_FOR_SEQUENCE = 20`, `_MAX_TICKS_PER_SEQUENCE = 500` |
| `jepa_trainer.py` | Loop di addestramento JEPA a basso livello con aggiornamento EMA dell'encoder target |
| `ema.py` | Classe `EMA` -- media mobile esponenziale per gestione pesi shadow (invariante NN-16: `.clone()` su `apply_shadow()`) |
| `role_head.py` | `NeuralRoleHead` (input 5-dim, output softmax 5-dim, ~870 parametri), helper di addestramento e inferenza per classificazione del ruolo del giocatore |
| `win_probability_trainer.py` | `WinProbabilityTrainerNN` -- modello leggero a 9 feature per probabilità di vittoria offline su DataFrame di partite pro |
| `dataset.py` | `ProPerformanceDataset` (supervisionato) e `SelfSupervisedDataset` (coppie contesto/target JEPA a finestra scorrevole) |
| `factory.py` | `ModelFactory` -- factory statica per istanziazione unificata di tutti i tipi di modello (`default`, `jepa`, `vl-jepa`, `rap`, `rap-lite`, `role_head`) |
| `persistence.py` | `save_nn()`, `load_nn()`, `get_model_path()` con scrittura atomica (`tmp + os.replace`), sidecar `.pt.meta.json` per lo schema delle feature, registro hash SHA-256 dei checkpoint (CTF-1), fallback di caricamento a 4 livelli (AppData utente -> AppData globale -> factory-bundled utente -> factory-bundled globale; un miss totale solleva `FileNotFoundError`, mai un modello silenzioso con pesi random, NN-14), `StaleCheckpointError` |
| `early_stopping.py` | `EarlyStopping` con soglie configurabili di pazienza e delta minimo; `EmbeddingCollapseDetector` / `EmbeddingCollapseError` -- gate di controllo del flusso che interrompe l'addestramento dopo `patience` epoche consecutive con collasso (P9-02) |
| `training_config.py` | Dataclass `TrainingConfig` e `JEPATrainingConfig` che centralizzano tutti gli iperparametri |
| `training_orchestrator.py` | `TrainingOrchestrator` -- loop unificato per epoca con validazione, early stopping, checkpointing, scheduling LR e dispatch dei callback; `run_training()` restituisce un esito esplicito successo/fallimento che la CLI espone (F-0043) e fornisce il `probe_batch` fisso per la telemetria di collasso |
| `training_controller.py` | `TrainingController` -- deduplicazione demo, controlli di diversità, gestione quota mensile, logica start-stop |
| `coach_manager.py` | `CoachTrainingManager` -- orchestrazione ad alto livello delle 5 fasi di addestramento (pre-training JEPA, baseline pro, adattamento utente, RAP, role head) con soft gate di maturità a 3 livelli (CALIBRATING 0-49 / LEARNING 50-199 / MATURE 200+); costruisce i gate di eleggibilità demo prima dello split temporale 70/15/15; la propagazione dello STOP operatore avviene tramite `TrainingStopRequested` (F-0032) |
| `train.py` | `train_nn()` -- punto d'ingresso legacy per addestramento di `AdvancedCoachNN` |
| `training_callbacks.py` | `TrainingCallback` (ABC, hook opt-in) e `CallbackRegistry` (dispatcher eventi con isolamento errori) |
| `tensorboard_callback.py` | `TensorBoardCallback` -- scalari per batch e per epoca (loss, LR, segnali RAP/JEPA/gate), istogrammi parametri/gradienti, layout scalari personalizzati e telemetria di collasso JEPA (`embed/*`) misurata su un probe batch fisso; `build_run_dir()` assegna a ogni run la propria log dir `RUNS_DIR/<model_type>/<timestamp UTC>-<tag dispositivo>`; degrada a un warning no-op senza `tensorboard` a meno che `CS2_TB_STRICT=1` |
| `collapse_metrics.py` | Telemetria pure-tensor del collasso delle rappresentazioni per embedding JEPA: `compute_collapse_metrics()` (std_mean, std_min, RankMe `effective_rank`, cosine_offdiag_mean su embedding L2-normalizzati) e `compute_ema_drift()`; consumato da `TensorBoardCallback`, non altera mai il flusso di controllo |
| `maturity_observatory.py` | `MaturityObservatory` -- indice di convinzione a 5 segnali (belief entropy, gate specialization, concept focus, value accuracy, role stability), macchina a 5 stati (doubt / crisis / learning / conviction / mature) |
| `embedding_projector.py` | `EmbeddingProjector` -- proiezioni UMAP 2D e esportazione embedding TensorBoard per visualizzazione dello spazio belief/concept |
| `training_monitor.py` | `TrainingMonitor` -- metriche per epoca persistite in JSON con scrittura atomica per monitoraggio progresso in tempo reale |
| `evaluate.py` | `evaluate_adjustments()` -- valutazione compatibile SHAP degli aggiustamenti di peso del modello per feature |
| `data_quality.py` | `DataQualityReport` -- controlli di qualità dati pre-addestramento (tasso NaN, tasso posizione zero, bilanciamento classi, completezza match) eseguiti tramite `run_pre_training_quality_check()`. I contatori di completezza match ora enumerano i risultati per elemento (OI-1 chiuso). |

## Sotto-pacchetti

| Pacchetto | Scopo |
|-----------|-------|
| `rap_coach/` | **Shim di compatibilità deprecati (P9-01).** Ogni modulo ri-esporta da `experimental/rap_coach/`; `skill_model.py` ri-esporta da `backend/processing/skill_assessment.py`. Vedere `rap_coach/README.md`. |
| `advanced/` | **Stub vuoto intenzionale.** Moduli originali rimossi nella remediazione G-06. Namespace riservato per esperimenti futuri. Vedere `advanced/README.md`. |
| `inference/` | `GhostEngine` -- motore di previsione in tempo reale che traduce lo stato di gioco tick-level in suggerimenti di coaching tramite `RAP_POSITION_SCALE`. |
| `layers/` | `SuperpositionLayer` -- layer lineare condizionato FiLM (`y = gamma(context)*(Wx+b) + beta(context)`) con hook di loss per sparsità L1 del gate e hook di osservabilità del gate. |
| `jepa_v2/` | **Encoder JEPA v2.** Architettura basata su Transformer con CausalSelfAttention, RMSNorm, SwiGLU, condizionamento FiLM, regolarizzazione SIGReg e predizione multi-orizzonte. Config: `d_model=128`, 4 livelli, 4 teste, orizzonti (1, 4, 16), addestramento bf16. |
| `experimental/` | Sede canonica dell'implementazione RAP Coach (`experimental/rap_coach/`): Perception, Memory, Strategy, Pedagogy, Communication, ChronovisorScanner. Gated dietro `USE_RAP_MODEL`. |

## Architetture dei Modelli

### 1. JEPA (`jepa_model.py`) -- Percorso di Addestramento Primario

Architettura Joint-Embedding Predictive auto-supervisionata. Protocollo a due fasi: (1) pre-training su demo professionali con loss contrastivo InfoNCE, regolarizzazione VICReg e contrasto momentum MoCo v3 (dimensione coda 4096, temperatura appresa), (2) fine-tuning LSTM su dati utente. MoE sparso a 3 esperti top-2 con bias del ruolo e output sigmoide (WR-52). Utilizza encoder target EMA (`requires_grad=False` durante l'aggiornamento, invariante NN-JM-04). Dim latente: 256, dim nascosta LSTM: 128.

### 2. RAP Coach (`experimental/rap_coach/`) -- Architettura della Grande Visione

Modello pedagogico a 7 livelli: Perception basata su ResNet, Memory LTC-Hopfield (LTC con `ncp_units=512` e proiezione output 153->256, `HopfieldLayer` con 32 prototipi addestrabili, `belief_dim=64`), Strategy con routing sparso top-2 MoE su 4 esperti SuperpositionLayer (FiLM), Pedagogy causale per attribuzione errori, Communication in linguaggio naturale e ChronovisorScanner per analisi temporale multi-scala. Hopfield è bypassato finché il trainer non segnala il primo vero step dell'ottimizzatore tramite `notify_optimizer_step()` (invariante NN-MEM-01). La stima delle abilità risiede in `backend/processing/skill_assessment.py` (`rap_coach/skill_model.py` è uno shim).

### 3. AdvancedCoachNN (`model.py`) -- Modello Supervisionato Legacy

Encoder di sequenza LSTM + Mixture of Experts (3 esperti di default) con LayerNorm, routing gate sparso top-2 (`_topk_sparse_gate`, GAP-10) con bias del ruolo, e clamping dell'output con `tanh`. Alias come `TeacherRefinementNN` per compatibilità.

### 4. NeuralRoleHead (`role_head.py`) -- Classificazione dei Ruoli

MLP leggero (5 -> 32 -> 16 -> 5, ~870 parametri) che predice le probabilità dei ruoli del giocatore da metriche di stile di gioco (TAPD, OAP, PODT, rating impact, aggression). Loss KL-divergence con label smoothing. Funziona come opinione secondaria insieme al classificatore euristico `RoleClassifier`.

### 5. WinProbabilityTrainerNN (`win_probability_trainer.py`) -- Predizione Vittoria Offline

Modello a 9 feature (vivi, salute, armatura, equipaggiamento, stato bomba) per addestramento offline su DataFrame di partite pro. Separato dal `WinProbabilityNN` real-time in `backend/analysis/` (12 feature, dim nascoste 64/32). I checkpoint NON sono intercambiabili.

### 6. VL-JEPA (`jepa_model.py`) -- Estensione Vision-Language

Estende `JEPACoachingModel` con un `ConceptLabeler` (16 concetti di coaching), proiettore di concetti e temperatura dei concetti appresa per spiegazioni di coaching a livello di concetto.

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
| RAP `hidden_dim` | 256 | `experimental/rap_coach/model.py` |
| RAP `ncp_units` | 512 | `experimental/rap_coach/memory.py` |
| RAP `belief_dim` | 64 | `experimental/rap_coach/model.py` |
| JEPA `latent_dim` | 256 | `jepa_model.py` |
| JEPA LSTM `hidden_dim` | 128 | `jepa_model.py` |

## Coach Introspection Observatory

La pipeline di addestramento include uno stack di osservabilità a 4 livelli, implementato come plugin `TrainingCallback`:

1. **Livello 1 -- CallbackRegistry** (`training_callbacks.py`): Architettura a plugin con isolamento errori. I callback non causano mai crash dell'addestramento.
2. **Livello 2 -- TensorBoardCallback** (`tensorboard_callback.py`): Scalari (loss, LR, sparsità, dinamiche gate), istogrammi (parametri, gradienti, belief, concetti), layout dashboard personalizzati e telemetria di collasso delle rappresentazioni (scalari `embed/*` da `collapse_metrics.py`, calcolati ad ogni epoca su un probe batch fisso). Entrambi i punti d'ingresso dell'addestramento creano log dir per-run con tag dispositivo tramite `build_run_dir()`.
3. **Livello 3 -- MaturityObservatory** (`maturity_observatory.py`): Indice di convinzione a 5 segnali con smoothing EMA e macchina di classificazione a 5 stati (doubt / crisis / learning / conviction / mature).
4. **Livello 4 -- EmbeddingProjector** (`embedding_projector.py`): Proiezioni UMAP 2D dei vettori belief e degli embedding di concetti, esportati su TensorBoard.

Lo stack completo è integrato in entrambi i percorsi di addestramento: `jepa_train.py` collega `TensorBoardCallback` e `EmbeddingProjector` direttamente, mentre il percorso `TrainingOrchestrator` riceve la catena di callback da `run_full_training_cycle.py` (`_build_callbacks()`).

## Invarianti Critici

| ID | Regola |
|----|--------|
| P-RSB-03 | `round_won` ESCLUSO dalle feature di addestramento (fuga di etichetta) |
| NN-MEM-01 | Hopfield bypassato fino a quando `notify_optimizer_step()` segnala il primo vero step dell'ottimizzatore |
| NN-16 | EMA `apply_shadow()` deve usare `.clone()` sui tensori shadow |
| NN-JM-04 | Encoder target `requires_grad=False` durante aggiornamento EMA |
| P-X-01 | Asserzione compile-time `len(FEATURE_NAMES) == METADATA_DIM` |
| P-VEC-02 | NaN/Inf nelle feature attivano log ERROR + clamp |
| P3-A | >5% NaN/Inf nel batch solleva `DataQualityError` |

## Note di Sviluppo

- **Riproducibilità:** Chiamare sempre `set_global_seed(42)` prima delle esecuzioni di addestramento.
- **Selezione dispositivo:** `get_device()` seleziona automaticamente la GPU discreta per VRAM; sovrascrivibile tramite impostazione `CUDA_DEVICE`.
- **Allineamento feature:** Qualsiasi modifica al vettore a 25 dimensioni deve aggiornare simultaneamente `FEATURE_NAMES`, `METADATA_DIM`, docstring di `extract()` e tutte le asserzioni `input_dim` dei modelli.
- **Dipendenze opzionali:** RAP Coach richiede `ncps` e `hopfield-layers` (importato come `hflayers`; il nome del pacchetto di distribuzione differisce dal nome di importazione). Le importazioni sono protette con `try/except`; verificare `_RAP_DEPS_AVAILABLE` prima dell'istanziazione.
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
