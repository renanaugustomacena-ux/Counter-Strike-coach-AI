# AIstate.md — Rapporto di Verita sullo Stato AI del Macena CS2 Analyzer

> **Autore**: Audit automatizzato (Claude Code)
> **Data**: 2026-02-26
> **Scope**: Sottosistema AI e impatto end-to-end su servizi, storage, e GUI
> **Trigger**: `part1_review.md` contiene 13+ affermazioni "Not Implemented" contraddette dal codebase
> **Regola fondamentale**: Questo documento e SOLO documentazione. Nessuna modifica al codice sorgente.

---

## Indice

1. [Meta-Analisi: Cosa la Review ha Sbagliato](#1-meta-analisi--cosa-la-review-ha-sbagliato)
2. [Catene di Dipendenza Critiche: Da AI a GUI](#2-catene-di-dipendenza-critiche--da-ai-a-gui)
3. [Issue Genuine con Blast Radius Analysis](#3-issue-genuine-con-blast-radius-analysis)
4. [Classificazione Sicurezza dei Fix](#4-classificazione-sicurezza-dei-fix)
5. [Valutazione di Affidabilita del Sistema](#5-valutazione-di-affidabilita-del-sistema)
6. [Roadmap di Remediation con Ordine di Dipendenza](#6-roadmap-di-remediation-con-ordine-di-dipendenza)
7. [Verifica Fondamenti Matematici](#7-verifica-fondamenti-matematici)
8. [DB Schema Consumer Map](#8-db-schema-consumer-map)
9. [Appendici](#9-appendici)

---

## 1. Meta-Analisi — Cosa la Review ha Sbagliato

La Sezione 3 di `part1_review.md` ("Repository-Paper Alignment Report") afferma che 13 componenti AI sono "Not Implemented" o "Partially Implemented". Un audit completo del codebase rivela che **tutti e 13 sono pienamente implementati**. La review e stata condotta su uno snapshot incompleto (5-6 file analizzati su 100+).

### Tabella delle 13 Correzioni

| # | Componente | Claim della Review | Realta nel Codebase | File:Riga | LOC |
|---|---|---|---|---|---|
| 1 | JEPA Encoder | "Not Implemented" | JEPAEncoder completo: ViT-style projection, LayerNorm, GELU, Dropout, residual connections | `backend/nn/jepa_model.py:24-56` | 33 |
| 2 | VL-JEPA | "Not Implemented" | VLJEPACoachingModel completo: 16 coaching concepts, concept embeddings, concept projector, BCE+VICReg diversity loss, learned temperature | `backend/nn/jepa_model.py:619-795` | 177 |
| 3 | LSTM+MoE | "Not Implemented" | AdvancedCoachNN: LSTM(2-layer)+LayerNorm+MoE(3 experts)+role_bias gating. Anche in JEPACoachingModel (lines 119-126) | `backend/nn/model.py:27-125` | 98 |
| 4 | NeuralRoleHead | "Not Implemented" | MLP 5->32->16->5, softmax output, KL-divergence training, FLEX threshold=0.35, label smoothing eps=0.02, consensus con heuristic classifier | `backend/nn/role_head.py:1-322` | 322 |
| 5 | Ghost Engine | "Not Implemented" | GhostEngine: 4-modality tensor fusion (view+map+motion+metadata), ModelFactory integration, 4-tier checkpoint loading, graceful degradation (is_trained flag), SCALE_FACTOR=500.0 | `backend/nn/inference/ghost_engine.py:14-50` | ~200 |
| 6 | RAP Coach | "3-layer prototype" | 7 layer completi: Perception(70-conv budget)+Memory(LTC+Hopfield)+Strategy(MoE)+Pedagogy+CausalAttributor+PositionHead+Sparsity regularization. metadata_dim=25, hidden_dim=256, output_dim=10 | `backend/nn/rap_coach/model.py:11-46` | ~300 |
| 7 | LTC-Hopfield | "Not present" | RAPMemory: `ncps.torch.LTC` con `AutoNCP` wiring (units=288, output=256) + `hflayers.Hopfield` (4 heads, stored_pattern_size=256). Belief head 256->SiLU->64 | `backend/nn/rap_coach/memory.py:1-60` | ~80 |
| 8 | Training Pipeline | "Not Provided" | 2-phase: Phase 1 JEPA pretrain (InfoNCE, EMA target encoder m=0.996), Phase 2 RAP supervised (strategy+value loss). Early stopping, validation split 0.2, callbacks, progress reporting | `run_full_training_cycle.py` + `backend/nn/training_orchestrator.py` | ~450 |
| 9 | 64-tick Delta | "Not Found" | Chronovisor multi-scala: micro(64 tick, lag=16, threshold=0.10), standard(192 tick, lag=64, threshold=0.15), macro(640 tick, lag=128, threshold=0.20). Cross-scale dedup, context_ticks, suggested_review | `backend/nn/rap_coach/chronovisor_scanner.py:54-103` | ~350 |
| 10 | 4-Level Fallback | "Documentation only" | CoachingService implementa COPER->Hybrid->RAG+Trad->Trad con ExperienceBank, Ollama NL polishing, baseline context. **Gap nel fallback** (vedi G-08) ma la struttura e completa | `backend/services/coaching_service.py:56-202` | ~150 |
| 11 | Training Observatory | "Not present" | 4 file: TrainingCallback ABC + CallbackRegistry (plugin), TensorBoardCallback (9+ scalari, istogrammi param/grad, gate/belief/concept), MaturityObservatory (5 segnali, conviction_index, state machine), EmbeddingProjector (UMAP projections) | `backend/nn/training_callbacks.py` + 3 file | ~400 |
| 12 | Quad-Daemon | "Only 3 documented" | 4 daemon: Scanner(:167), Digester(:218), Teacher(:265), Pulse(:303). Ciascuno con shutdown_event, error handling, state_manager integration | `core/session_engine.py:167-312` | ~145 |
| 13 | Model Persistence | "Partially" | 4-tier fallback: user_dir->global_dir->factory_bundle->factory_global. Usa `torch.save/load` con state_dict. ModelFactory per istanziazione (5 tipi: default, jepa, vl-jepa, rap, role_head) | `backend/nn/persistence.py:1-60` + `factory.py` | ~120 |

### Causa dell'Errore nella Review

La review ha analizzato un subset di file (probabilmente solo `model.py`, `jepa_model.py` parziale, e alcuni import) senza attraversare la struttura completa:

```
backend/nn/
  ├── rap_coach/          ← 4 file (model, memory, perception, strategy, pedagogy) — NON esaminati
  │   ├── model.py
  │   ├── memory.py       ← LTC-Hopfield qui
  │   ├── perception.py
  │   ├── strategy.py
  │   └── chronovisor_scanner.py
  ├── inference/
  │   └── ghost_engine.py ← NON esaminato
  ├── role_head.py        ← NON esaminato
  ├── training_callbacks.py
  ├── tensorboard_callback.py
  ├── maturity_observatory.py
  └── embedding_projector.py
```

Le sezioni 1 (Literature Review) e 2 (Coaching Services) di `part1_review.md` sono tecnicamente valide e ben documentate. Solo la Sezione 3 e affetta da incompletezza del dataset di input.

---

## 2. Catene di Dipendenza Critiche — Da AI a GUI

Ogni modifica al sottosistema AI si propaga attraverso servizi, storage, e GUI. Questa sezione mappa le 6 catene critiche per prevenire regressioni a cascata.

### Catena 1: RAPCoachModel -> GhostEngine -> TacticalViewerScreen

```
RAPCoachModel(metadata_dim=25, view=(3,224,224), map=(3,128,128))
  |
  v
GhostEngine.predict_tick()              [ghost_engine.py:54+]
  | Richiede: view(3,224,224), map(3,128,128), motion(3,224,224), metadata(25-dim)
  | Produce: (delta_x, delta_y) * SCALE_FACTOR=500.0
  v
TacticalGhostViewModel.predict_ghosts() [tactical_viewmodels.py]
  | Consuma: (dx, dy) coordinate predette
  | Produce: Lista di GhostPosition per overlay rendering
  v
TacticalViewerScreen                    [tactical_viewer_screen.py]
  | Disegna: overlay ghost su mappa tattica
```

**Contratto dimensionale:**
- `METADATA_DIM = 25` (vectorizer.py:20) -> `INPUT_DIM = METADATA_DIM` (config.py:104) -> `RAPCoachModel(metadata_dim=METADATA_DIM)` (model.py:17)
- View: `(3, 224, 224)` -> `RAPPerception.view_backbone(Conv2d(in_channels=3))`
- Map: `(3, 128, 128)` -> `RAPPerception.map_backbone(Conv2d(in_channels=3))`
- Motion: `(3, 224, 224)` -> `RAPPerception.motion_conv(Conv2d(in_channels=3))`

**Punto di rottura:** Se METADATA_DIM cambia (25->26): `RuntimeError: mat1 and mat2 shapes cannot be multiplied` in ogni layer che consuma metadata. GhostEngine cattura l'eccezione e ritorna `(0, 0)`. L'utente vede la mappa tattica senza ghost — degradazione graceful ma silenziosamente inutile.

**Degradazione:** Graceful. GhostEngine ha try/except globale (linea 49-52). La UI non crasha ma l'utente perde tutta l'inferenza RAP.

---

### Catena 2: CoachingService -> CoachingInsight DB -> MatchDetailScreen

```
CoachingService.generate_new_insights()   [coaching_service.py:43]
  | Mode selection: COPER / Hybrid / RAG+Trad / Traditional
  v
_generate_coper_insights()                [coaching_service.py:133+]
  | Usa: ExperienceBank, OllamaCoachWriter, TemporalBaselineDecay
  | Produce: CoachingInsight(title, severity, message, focus_area)
  v
DB commit -> CoachingInsight table        [db_models.py]
  |
  +---> MatchDetailScreen._load_detail()  [match_detail_screen.py:102-107]
  |       | Legge: CoachingInsight per demo_name
  |       | Renderizza: CoachingCard widget (colore per severity)
  |       v
  |     layout.kv CoachingCard template
  |
  +---> Coaching chat ViewModel           [viewmodels]
  +---> HomeScreen quick summary
```

**Contratto dati:** CoachingInsight DEVE avere: `title(str)`, `severity("Info"|"Medium"|"High"|"Critical")`, `message(str)`, `focus_area(str)`. Il template KV in `layout.kv` usa severity per selezionare l'icona e il colore — un severity non standard non causa crash ma mostra icona di default.

**Punto di rottura:** Se un campo e `None` o mancante, la CoachingCard Kivy potrebbe mostrare "None" come testo. Non e un crash ma e un difetto visivo direttamente visibile all'utente.

---

### Catena 3: FeatureExtractor(25-dim) -> Tutti i Modelli -> Training + Inference

```
FeatureExtractor.extract()               [vectorizer.py]
  | Produce: 25-dim numpy array [hp, armor, helmet, defuser, equip, crouch, scope,
  |          blind, enemies_vis, pos_x/y/z, yaw_sin/cos, pitch, z_penalty,
  |          kast, map_id, round_phase, weapon_class, time_in_round,
  |          bomb_planted, teammates_alive, enemies_alive, team_economy]
  |
  +---> Training: StateReconstructor._vectorize_ticks()
  |       -> TrainingOrchestrator._build_batch()
  |         -> features_tensor (b, METADATA_DIM)
  |
  +---> Inference: GhostEngine.predict_tick()
  |       -> RAPCoachModel.forward(metadata=(b, seq, 25))
  |
  +---> Strategy: MoEStrategy(context_dim=METADATA_DIM=25)
  |
  +---> Analysis: belief_model, deception_index, game_tree
  |       -> Consumano feature vector direttamente o indirettamente
```

**Contratto:** `METADATA_DIM = 25` in `vectorizer.py:20` e il singolo punto di verita. Propagato a:
- `backend/nn/config.py:104` come `INPUT_DIM`
- `backend/nn/rap_coach/model.py:17` come parametro di default
- `backend/nn/model.py:18` tramite `CoachNNConfig.input_dim`
- `backend/nn/jepa_model.py:103` tramite parametro `input_dim`

**CLASSIFICAZIONE: FORBIDDEN** — Non cambiare `METADATA_DIM` senza un piano completo di:
1. Migrazione di TUTTI i checkpoint esistenti (incompatibili)
2. Retraining di TUTTI i modelli (default, jepa, vl-jepa, rap, role_head)
3. Aggiornamento di TUTTI i test che verificano dimensionalita
4. Verifica che GhostEngine/TensorFactory producano output coerenti

---

### Catena 4: PlayerMatchStats/RoundStats -> AnalyticsEngine -> 3 Screen

```
PlayerMatchStats (avg_kills, avg_deaths, avg_adr, rating, kd_ratio...)
RoundStats (kills, deaths, damage_dealt, round_won, round_rating...)
  |
  +---> analytics.py
  |       get_rating_history()      -> PerformanceScreen (sparkline)
  |       get_per_map_stats()       -> PerformanceScreen (per-map cards)
  |       get_strength_weakness()   -> PerformanceScreen (strengths/weaknesses)
  |       get_utility_breakdown()   -> PerformanceScreen (utility panel)
  |       get_round_breakdown()     -> MatchDetailScreen (round-by-round)
  |       get_round_economy_timeline() -> MatchDetailScreen (economy graph)
  |
  +---> MatchHistoryScreen          -> Lista match con rating, kills
  +---> MatchDetailScreen           -> Overview + HLTV 2.0 breakdown
  +---> PerformanceScreen           -> Dashboard aggregato
  +---> Training pipeline           -> Legge stats per feature engineering
  +---> 15+ test file               -> Verificano field names e valori
```

**Contratto field names (INVIOLABILE):**
- `PlayerMatchStats.avg_kills` — **NON** `kills`
- `PlayerMatchStats.avg_deaths` — **NON** `deaths`
- `PlayerMatchStats.avg_kast` — **NON** `kast_pct`
- `RoundStats.damage_dealt` — **NON** `damage`
- `MomentumState.current_multiplier` — **NON** `multiplier`

**CLASSIFICAZIONE: FORBIDDEN** — Rinominare un campo DB rompe 3 screen + analytics + training + 15+ test simultaneamente.

---

### Catena 5: TensorFactory Shapes -> RAPCoachModel CNN Layers

```
TensorFactory.generate_map_tensor()     -> (3, 128, 128) -> RAPPerception.map_backbone
TensorFactory.generate_view_tensor()    -> (3, 224, 224) -> RAPPerception.view_backbone
TensorFactory.generate_motion_tensor()  -> (3, 224, 224) -> RAPPerception.motion_conv
  |
  +---> GhostEngine.predict_tick()      -> Crea tensori per inferenza
  +---> TrainingOrchestrator._build_batch() -> Crea tensori per training
```

**Contratto:**
- Canali = 3 (hardcoded in Conv2d layers di RAPPerception)
- Map resolution = 128 (da `TensorFactoryConfig.map_resolution`)
- View resolution = 224 (da `TensorFactoryConfig.view_resolution`)
- dtype = `torch.float32`

**Punto di rottura:** Se canali 3->4, `Conv2d(in_channels=3)` crashera con `RuntimeError`. Richiede modifica architettura + retraining completo.

**NOTA CRITICA:** C'e un mismatch di risoluzione tra training (64x64, orchestrator.py:357-358) e inference (128x128 map / 224x224 view, tensor_factory.py). Questo non e un bug attuale perche il training non usa TensorFactory reale (vedi G-04), ma diventerebb un problema quando G-04 fase 2 sara implementato. Il Conv2d accetta input di qualsiasi risoluzione (convoluzioni non dipendono dalla dimensione spaziale) ma le feature map risultanti avranno dimensioni diverse, potenzialmente causando mismatch nel linear layer finale se presente.

---

### Catena 6: TrainingOrchestrator -> Callbacks -> TensorBoard/MaturityObservatory

```
TrainingOrchestrator.train()             [training_orchestrator.py]
  | Fire points: on_train_start, on_epoch_start, on_batch_end, on_epoch_end, on_train_end
  v
CallbackRegistry.fire()                  [training_callbacks.py]
  |
  +---> TensorBoardCallback              [tensorboard_callback.py]
  |       -> runs/ directory (scalari, istogrammi, layout personalizzato)
  |
  +---> MaturityObservatory              [maturity_observatory.py]
  |       -> conviction_index, maturity_state (doubt/crisis/learning/conviction/mature)
  |
  +---> EmbeddingProjector              [embedding_projector.py]
        -> UMAP projections (graceful if umap-learn not installed)
```

**Contratto:** Zero-impact design. Ogni callback e wrappato in try/except individuale:
```python
# training_callbacks.py — CallbackRegistry.fire()
for cb in self.callbacks:
    try:
        method = getattr(cb, event_name, None)
        if method:
            method(**kwargs)
    except Exception as e:
        logger.warning("Callback %s failed on %s: %s", cb.__class__.__name__, event_name, e)
```

**CLASSIFICAZIONE: SAFE** — Errori nei callback MAI crashano il training. Nessuna propagazione verso UI o DB. Questo e il pattern ideale per estensioni future.

---

## 3. Issue Genuine con Blast Radius Analysis

L'audit ha identificato **9 issue genuine** invisibili alla review originale. Per ciascuna: severita, blast radius, classificazione fix, catene impattate.

---

### G-01 [MEDIUM]: ConceptLabeler Label Leakage

**File:** `backend/nn/jepa_model.py:463-616`

**Problema:** `ConceptLabeler.label_tick()` deriva soft label (16 coaching concepts) dagli stessi 19 feature usati come input al modello VL-JEPA. Il modello impara a ricostruire pattern nei propri input anziche concetti tattici indipendenti.

**Meccanismo della leakage:**
```
Input features [hp, armor, helmet, equip, ...]
  |
  +---> VL-JEPA encoder -> concept_probs
  |
  +---> ConceptLabeler.label_tick() -> concept_labels  (derivati dagli stessi feature!)
  |
  v
Loss = BCE(concept_probs, concept_labels)
  = Il modello impara a ricostruire f(input) anziche apprendere concetti tattici
```

Esempio concreto: il concetto "POSITIONING_RISK" (feature index 463-475) e attivato quando `enemies_vis > 0.4` e `health < 0.4` — entrambi direttamente presenti nel feature vector di input.

**Blast Radius:** CONTAINED
- Tocca SOLO `jepa_model.py` (ConceptLabeler class) e `jepa_trainer.py`
- VL-JEPA NON e nel path di inferenza di GhostEngine (che usa RAP)
- Nessuna catena UI impattata
- Nessun campo DB coinvolto

**Fix SAFE:**
- Sostituire `label_tick()` con label derivati da `RoundStats` (kill/death/bomb/utility events per round)
- RoundStats gia contiene: `opening_kill`, `round_won`, `flashes_thrown`, `damage_dealt`, `round_rating`
- NON cambia dimensioni input/output, NON cambia architettura, NON invalida checkpoint JEPA base
- File da modificare: SOLO `jepa_model.py` (ConceptLabeler class)

**Rischio residuo:** I nuovi label da RoundStats potrebbero non allinearsi perfettamente con i 16 concept fissi — serve un mapping esplicito concept->field_combinazione.

---

### G-02 [HIGH]: TensorFactory Danger Zone Placeholder

**File:** `backend/processing/tensor_factory.py:162-167`

**Problema:** Il view tensor ha 3 canali ma solo Channel 0 (FOV mask) e informativo:
```python
# tensor_factory.py:162-167
danger_zone = np.zeros((resolution, resolution), dtype=np.float32)  # Ch1: SEMPRE ZERO
safe_zone = np.clip(1.0 - fov_mask - danger_zone, 0, 1)            # Ch2: = 1 - Ch0 (ridondante)
view_tensor = np.stack([fov_mask, danger_zone, safe_zone], axis=0)
```

Channel 1 (danger zone) e permanentemente zero. Channel 2 (safe zone) e `1.0 - fov_mask` — algebricamente ridondante con Channel 0.

**Impatto:** Il CNN view backbone di RAPPerception (che consuma ~60% dei parametri del modello RAP) riceve 1/3 dell'informazione utile prevista dall'architettura. I neuroni responsabili di Channel 1 apprendono pesi near-zero (nessun gradient da input zero). I neuroni di Channel 2 apprendono una trasformazione lineare di Channel 0.

**Blast Radius:** CONTAINED ma DELICATO
- Tocca SOLO `tensor_factory.py` (metodo `generate_view_tensor`)
- Shape NON cambia: resta `(3, 224, 224)`
- Catene impattate: Catena 1 (RAP->Ghost->UI) e Catena 5 (TensorFactory->RAP CNN)

**Fix SAFE se:** i canali restano 3 e la risoluzione resta 224x224. La modifica e DENTRO i canali esistenti.
- Channel 1 = sightline projection da posizioni+view_angles dei nemici
- Channel 2 = composite (cover overlay + threat intersection)
- `generate_view_tensor()` gia riceve `ticks` con `pos_x/y, view_x/y` per tutti i player — i dati ci sono

**Prerequisiti:** Checkpoint RAP addestrati su zeros impareranno pattern diversi -> **richiede retraining RAP** dopo il fix.

**File da modificare:** SOLO `tensor_factory.py`

---

### G-03 [HIGH]: RAP Training Targets Triviali

**File:** `backend/nn/training_orchestrator.py:371-385`

**Problema:** I target di training del modello RAP non codificano decisioni tattiche:
```python
# training_orchestrator.py:371-385
target_val[i, 0] = float(outcome)           # Value: 0 (perso) o 1 (vinto) — binario
equip = getattr(item, "equipment_value", 0)  # Strategy: bin economico 0-9
strat_idx = min(9, int(equip / 1000))
target_strat[i, strat_idx] = 1.0            # One-hot del bin economico
```

- **Value target** `(b, 1)`: Il modello impara "round vinto = bene" — zero informazione sulla qualita del gioco
- **Strategy target** `(b, 10)`: Il modello impara "giocatore ricco = bin alto" — zero intelligenza tattica

Un modello con questi target sara al massimo un classificatore economico, non un coach tattico.

**Blast Radius:** CONTAINED
- Tocca SOLO `_build_batch()` in `training_orchestrator.py`
- Nessun cambio di shape: `target_val` resta `(b, 1)`, `target_strat` resta `(b, 10)`
- Catena 1 impattata indirettamente (qualita del modello RAP)

**Fix SAFE:**
- `target_val (b,1)`: Sostituire con advantage function = f(alive_diff, hp_ratio, equip_diff, bomb_state) in [0,1]
- `target_strat (b,10)`: Sostituire con tactical action labels (site_take, rotation, entry, support, anchor, lurk, retake, save, eco, force_buy)
- `raw_items` nel batch gia contengono `round_outcome`, `equipment_value`, e accesso a RoundStats

**Rischio BASSO:** Checkpoint vecchi addestrati su target sbagliati diventano meno utili ma non crashano. L'architettura e identica.

**File da modificare:** SOLO `training_orchestrator.py`

---

### G-04 [HIGH]: RAP Visual Inputs Zero-Initialized in Training

**File:** `backend/nn/training_orchestrator.py:354-366`

**Problema:** Durante il training, view e map tensor sono quasi-zero:
```python
# training_orchestrator.py:354-358
view = torch.zeros(b, 3, 64, 64).to(self.device)
map_tensor = torch.zeros(b, 3, 64, 64).to(self.device)
# Solo un singolo pixel settato per posizione:
map_tensor[i, 0, py, px] = 1.0  # Un punto su 64*64 = 4096 pixel
```

Il backbone visivo (~60% parametri RAP) si addestra su segnale essenzialmente nullo. In inferenza, GhostEngine usa TensorFactory reale (mappe a 128x128 con tutti i player, FOV mask a 224x224) — il modello vede dati completamente diversi da quelli su cui e stato addestrato.

**Blast Radius:** RISKY (dipende dalla fase)

**Fase 1 (CONTAINED):** Popolare map/view tensor con piu informazione dalle feature gia disponibili nel batch — NON richiede nuove query DB. Singolo file.

**Fase 2 (RISKY):** Integrare TensorFactory reale nel training loop:
- Richiede query DB per tutti i player di un tick (non solo il player target)
- Impatto performance training (query addizionali per tick_number+demo_name)
- Mismatch risoluzione: training 64x64 vs inference 128x128/224x224

**File fase 1:** SOLO `training_orchestrator.py`
**File fase 2:** `training_orchestrator.py` + `coach_manager.py` + nuova query in `database.py`

---

### G-05 [MEDIUM]: Parametri Euristici Non Validati

**File:** `belief_model.py`, `deception_index.py`, `game_tree.py`

**Problema:** Tutti i parametri numerici sono hand-tuned senza calibrazione su dati reali:

| File | Parametro | Valore | Nota |
|---|---|---|---|
| `belief_model.py:23-27` | Prior per HP bracket | full=0.35, damaged=0.55, critical=0.80 | Plausibili ma non calibrati |
| `belief_model.py:30+` | Weapon lethality multipliers | AWP>rifle>pistol | Direzione corretta, magnitudine non validata |
| `deception_index.py` | Pesi componenti | 0.25/0.40/0.35 | Arbitrari |
| `game_tree.py` | Prior strategici | 0.30/0.40/0.20/0.10 | Arbitrari |

**Blast Radius:** SAFE per ogni singolo file
- Sono costanti locali senza propagazione
- Catena 2 impattata indirettamente (qualita coaching COPER/Advanced)
- Nessun cambio di interfaccia

**Fix SAFE:** Modificare SOLO le costanti nei rispettivi file.
**Rischio:** Nuovi valori potrebbero essere peggiori dei vecchi se non validati empiricamente. Approccio consigliato:
1. Documentare valori correnti come baseline
2. Creare script di validazione che confronta output con dati pro annotati
3. Solo dopo validazione, aggiornare le costanti

---

### G-06 [LOW]: SuperpositionNet Legacy context_dim=5

**File:** `backend/nn/advanced/superposition_net.py:12`

```python
# superposition_net.py:12
self.context_gate = nn.Linear(5, out_features)  # Hardcoded, dovrebbe essere METADATA_DIM
```

**Blast Radius:** ZERO
- Il file legacy NON e nel path di import attivo
- La versione corretta e in `backend/nn/layers/superposition.py`
- Nessun import lo referenzia in produzione

**Fix SAFE:** Aggiungere deprecation comment o eliminare il file.

---

### G-07 [MEDIUM]: Belief Calibrator Non Collegato al Teacher Daemon

**File:** `core/session_engine.py:265-300`

**Problema:** Il Teacher daemon chiama `CoachTrainingManager().run_full_cycle()` (riga 281) e `_check_meta_shift()` (riga 287), ma **MAI** `AdaptiveBeliefCalibrator.auto_calibrate()`.

**Codice attuale (riga 274-292):**
```python
while not _shutdown_event.is_set():
    try:
        trigger_count = _check_retraining_trigger()
        if trigger_count > 0:
            state_manager.update_status("teacher", "Learning")
            CoachTrainingManager().run_full_cycle()
            _commit_trained_sample_count(trigger_count)
            _last_baseline = _check_meta_shift(_last_baseline)
            # ^^^ Nessuna chiamata a belief calibration qui
    except Exception as e:
        logger.error("Teacher Error: %s", e)
```

**NOTA:** Il `MEMORY.md` del progetto afferma erroneamente che `_run_belief_calibration()` e stato aggiunto al Teacher daemon. Grep conferma che questa funzione NON esiste nel file.

**Blast Radius:** CONTAINED
- Aggiunge 5-10 righe al Teacher daemon loop
- Non modifica interfacce esistenti
- `AdaptiveBeliefCalibrator` in `belief_model.py` ha gia `extract_death_events_from_db()` e `auto_calibrate()` implementati
- Pattern: stesso pattern non-fatale del meta_shift check (try/except con logging)

**Fix SAFE:**
```python
# Dopo riga 287:
try:
    from backend.analysis.belief_model import AdaptiveBeliefCalibrator
    calibrator = AdaptiveBeliefCalibrator()
    calibrator.auto_calibrate(db_manager)
    logger.info("Belief calibration completed after retraining")
except Exception as cal_err:
    logger.warning("Belief calibration non-fatal: %s", cal_err)
```

**File da modificare:** SOLO `session_engine.py`

---

### G-08 [MEDIUM]: Fallback Coaching Incompleto

**File:** `backend/services/coaching_service.py:190-202`

**Problema:** Se COPER fallisce E (`use_hybrid` e False OPPURE `player_stats` e None), il sistema logga un warning e genera ZERO coaching:

```python
# coaching_service.py:196-202
if self.use_hybrid and player_stats:
    self._generate_hybrid_insights(player_name, demo_name, player_stats, map_name)
else:
    logger.warning(
        f"COPER fallback: no hybrid available and no deviations -- "
        f"no coaching generated for {player_name} on {demo_name}"
    )
    # ^^^ Fine. Nessun coaching prodotto. Catena 2 interrotta qui.
```

L'utente che guarda la MatchDetailScreen vedra ZERO CoachingCard per quella demo — senza alcuna spiegazione del perche.

**Blast Radius:** CONTAINED
- Modifica 3-5 righe nel blocco else
- Catena 2 (coaching->DB->UI): corregge il caso dove la catena si interrompe

**Fix SAFE:** Nel blocco else, aggiungere chiamata a `generate_corrections()` + `_save_corrections_as_insights()` (gia importati e usati a riga 92-95).

**Rischio ZERO:** Aggiunge un fallback dove prima non c'era nulla. Impossibile peggiorare la situazione.

**File da modificare:** SOLO `coaching_service.py`

---

### G-09 [MEDIUM]: Test Failures Pre-Esistenti

**File:** 8+ file test con failures noti

| Test File | Causa | Tipo |
|---|---|---|
| `test_game_theory.py` (7 test) | `DeathProbabilityEstimator` mancante in `analysis/__init__.py` | Import |
| `test_analysis_orchestrator.py` | Stesso import mancante | Import |
| `test_demo_format_adapter.py` | `validate_demo_file` non nel parser source | API mismatch |
| `test_security.py` | `.env` non in `.gitignore` | Config |
| `test_hybrid_engine.py` | baseline string indices error | Logic |
| `test_integration.py` | untrained model degenerate output | Precondition |
| `test_onboarding_training.py` (2 test) | baseline deviations | Tolerance |
| `test_pro_demo_miner.py` (2 test) | knowledge records persistence | DB fixture |
| `test_spatial_engine.py` | pixel_mapping values | Formula |

**Blast Radius:** VARIABILE per test — nessuna catena di produzione impattata. Solo quality gate.

---

## 4. Classificazione Sicurezza dei Fix

| Issue | Classificazione | File Toccati | Cambio Shape? | Cambio DB? | Cambio UI? | Retraining? |
|-------|----------------|-------------|:---:|:---:|:---:|:---:|
| G-01 | **SAFE** | jepa_model.py | NO | NO (legge RoundStats) | NO | Solo VL-JEPA |
| G-02 | **CONTAINED** | tensor_factory.py | NO (3,224,224) | NO | NO | RAP dopo fix |
| G-03 | **CONTAINED** | training_orchestrator.py | NO (b,1) e (b,10) | NO | NO | RAP dopo fix |
| G-04 fase 1 | **CONTAINED** | training_orchestrator.py | NO (b,3,64,64) | NO | NO | RAP dopo fix |
| G-04 fase 2 | **RISKY** | orchestrator + manager + DB | NO | LEGGE PlayerTickState | NO | RAP dopo fix |
| G-05 | **SAFE** | 3 file isolati | NO | NO | NO | NO |
| G-06 | **SAFE (ZERO)** | superposition_net.py | NO | NO | NO | NO |
| G-07 | **CONTAINED** | session_engine.py | NO | LEGGE CalibrationSnapshot | NO | NO |
| G-08 | **SAFE** | coaching_service.py | NO | SCRIVE CoachingInsight | NO | NO |
| G-09 | **VARIABILE** | 8+ test file | NO | NO | NO | NO |

### Regole di Sicurezza INVIOLABILI

Queste regole derivano dall'analisi delle catene di dipendenza. Violarle causa regressioni a cascata non recuperabili senza retraining o migrazione dati.

1. **MAI cambiare `METADATA_DIM` (25)** senza migration plan completo — invalida tutti i checkpoint, tutti i modelli, tutti i test dimensionali (Catena 3)
2. **MAI rinominare campi DB** (`avg_kills`, `damage_dealt`, `current_multiplier`) — rompe 3 screen + analytics + training + 15+ test (Catena 4)
3. **MAI cambiare shape dei tensor** (3 canali, 128/224 risoluzioni) — RuntimeError in Conv2d (Catena 5)
4. **MAI cambiare signature di `ModelFactory.get_model()`** — usata in 6+ consumatori (factory.py)
5. **MAI cambiare `CoachingInsight` fields** (title, severity, message, focus_area) — rompe UI e coaching chat (Catena 2)
6. **Ogni fix DEVE passare `headless_validator` (79/79)** PRIMA di essere considerato completo

---

## 5. Valutazione di Affidabilita del Sistema

### Domanda 1: Modelli non addestrati possono corrompere output?

**Verdetto: NO.** Il sistema ha 3 livelli di protezione:

1. **GhostEngine `is_trained` flag** (ghost_engine.py:25): Se nessun checkpoint -> `self.model = None`, `self.is_trained = False`. `predict_tick()` ritorna `(0.0, 0.0)`.

2. **Maturity gating** (coach_manager.py): 3 tier che scalano confidence:
   - CALIBRATING (0-49 demo): 0.5x confidence
   - LEARNING (50-199 demo): 0.8x confidence
   - MATURE (200+ demo): 1.0x confidence

3. **COPER non usa modello neurale**: Il coaching mode di default usa ExperienceBank (pattern matching su esperienze passate) + RAG knowledge + pro references + Ollama NL polishing. Nessuna dipendenza da checkpoint.

### Domanda 2: Il fallback a 4 livelli degrada gracefully?

**Verdetto: PARZIALMENTE.**

- COPER -> Hybrid: **Funziona** (coaching_service.py:196-197)
- Hybrid/COPER entrambi falliscono: **ROTTO** (G-08) — solo warning, zero coaching generato
- Traditional mode (generate_corrections): **Funziona** autonomamente
- La catena si interrompe nel caso specifico dove COPER fallisce E hybrid non e disponibile E player_stats e None

Fix richiesto: 3 righe (G-08). Rischio zero.

### Domanda 3: Le euristiche hand-tuned sono pericolose?

**Verdetto: RISCHIO MODERATO, NON PERICOLOSO.**

I parametri sono direzionalmente corretti:
- AWP > rifle > pistol (belief_model.py) — vero in CS2
- Damaged player ha piu chance di morire — vero
- I pesi del deception_index prioritizzano informazione nascosta — sensato

Rischio: magnitudine sbagliate -> coaching plausibile ma impreciso. NON pericoloso (non crashera nulla, non dara consigli dannosi), ma potrebbe dare consigli subottimali. Un coach umano con 10 anni di esperienza potrebbe calibrare meglio questi parametri.

### Domanda 4: Il placeholder danger channel corrompe l'inferenza?

**Verdetto: NON CORROMPE, MA LIMITA.**

CNN impara a ignorare Channel 1 (zero gradient su input zero). Channel 2 e algebricamente ridondante con Channel 0. Il modello funziona ma e "cieco" alle minacce spaziali — spreca ~60% della capacita visiva del backbone.

In pratica: il ghost predice posizioni basandosi su mappa e metadata, ma non considera le sightlines nemiche. E come un coach che analizza la posizione del giocatore sulla mappa ma non vede dove guardano gli avversari.

### Domanda 5: Il sistema puo produrre risultati di coaching attendibili ORA?

**SI per coaching COPER** (mode di default):
- Basato su ExperienceBank (pattern matching su esperienze passate reali)
- RAG knowledge retrieval da base di conoscenza CS2
- Pro references per confronto con giocatori professionisti
- Ollama NL polishing per leggibilita
- Confidence score comunicato all'utente
- NON dipende da modelli neurali

**NO per coaching basato su RAP/JEPA:**
- Richiede 200+ demo per raggiungere MATURE tier
- I training target sono triviali (G-03) — il modello impara correlazioni economiche, non tattiche
- Il visual backbone e addestrato su segnale nullo (G-04) — il modello e "cieco"
- Fix G-02/G-03/G-04 necessari PRIMA che il training produca un modello utile
- Dopo i fix, retraining obbligatorio

**PARZIALMENTE per analisi avanzata:**
- Momentum tracker: funziona con euristiche plausibili
- Deception index: funziona ma con parametri non calibrati
- Game tree (expectiminimax): funziona ma con prior arbitrari
- Chronovisor: richiede modello RAP trainato per operare (maturity check)

---

## 6. Roadmap di Remediation con Ordine di Dipendenza

L'ordine conta: alcune fix dipendono da altre, e il retraining deve avvenire DOPO tutti i fix di training quality.

```
FASE 0 (IMMEDIATE, < 1 giorno, SAFE — nessun retraining):
  G-08: Coaching fallback gap           -> 3 righe, rischio zero
  G-07: Belief calibrator wiring        -> 5-10 righe, rischio zero
  G-06: Legacy SuperpositionNet         -> 1 riga commento o delete file

FASE 1 (TRAINING QUALITY, 3-5 giorni, CONTAINED — retraining RAP alla fine):
  G-03: RAP training targets            -> prerequisito per G-02/G-04
  G-02: Danger zone implementation      -> dipende da G-03 (train dopo)
  G-04 fase 1: Popolare map tensor      -> dipende da G-03 (train dopo)
  >>> RETRAINING RAP dopo tutti e 3 <<<

FASE 2 (CONCEPT QUALITY, 2-3 giorni, SAFE — retraining VL-JEPA):
  G-01: ConceptLabeler fix              -> indipendente da Fase 1
  >>> RETRAINING VL-JEPA dopo <<<

FASE 3 (VALIDATION, 3-5 giorni, SAFE):
  G-05: Heuristic validation            -> richiede dataset pro annotato
  G-09: Test failures                   -> ciascuno indipendente

FASE 4 (FUTURE, RISKY):
  G-04 fase 2: TensorFactory reale      -> richiede redesign data loading
```

### Grafo delle Dipendenze

```
G-08 ──(indipendente)──> DONE
G-07 ──(indipendente)──> DONE
G-06 ──(indipendente)──> DONE

G-03 ──> G-02 ──┐
           |     ├──> RETRAINING RAP ──> Inference quality migliora
G-03 ──> G-04f1─┘

G-01 ──(indipendente)──> RETRAINING VL-JEPA ──> Concept quality migliora

G-05 ──(indipendente, richiede dati pro)──> Parametri calibrati
G-09 ──(ciascuno indipendente)──> Quality gate pulita
```

### Perche G-03 prima di G-02 e G-04?

Se si implementano G-02 (danger zone) e G-04 (map tensor) prima di G-03 (target), il modello vedrebbe dati visivi ricchi ma imparerebbe target triviali (binario win/lose + bin economici). I neuroni visivi verrebbero addestrati a predire l'economia del giocatore dalla mappa — inutile. Implementando G-03 prima, i target diventano tattici, e i neuroni visivi possono imparare correlazioni spaziali significative.

---

## 7. Verifica Fondamenti Matematici

Tutte le formule matematiche critiche sono state verificate per correttezza.

| Formula | File | Verifica | Status |
|---|---|---|---|
| **JEPA InfoNCE** | jepa_model.py | L2-norm, cosine similarity, temperature=0.07, -log(exp(sim)/sum(exp)), contrastive corretto | OK |
| **EMA Target Encoder** | jepa_model.py | theta_k = m*theta_k + (1-m)*theta_q, m=0.996 — update rule standard BYOL/DINO | OK |
| **Bayesian Death Prob** | belief_model.py | Log-odds update: logit(p) += sum(evidence_i). Conversione logit<->prob corretta. Prior da calibrare (G-05) | OK (parametri da calibrare) |
| **Conviction Index** | maturity_observatory.py | sum(w_i * signal_i), w=[0.25, 0.25, 0.20, 0.20, 0.10], sum=1.0. Weighted average corretto | OK |
| **Superposition Gating** | layers/superposition.py | out = F.linear(x, W, b) * sigmoid(gate(context)) + L1 sparsity. Feature selection differenziabile | OK |
| **Temporal Decay** | pro_baseline.py | w = exp(-0.693 * age_days / 90), min=0.1. Half-life=90 giorni (exp(-0.693)=0.5). Corretto | OK |
| **Momentum** | momentum.py | Multiplier in [0.7, 1.4], decay lambda=0.15, half-switch reset a round 13. Clamped, bounded | OK |
| **HLTV 2.0 Rating** | round_stats_builder.py | Composite: KAST%, ADR/151, kills/rounds, survival_rate, multi-kill bonus. Pesi standard | OK |
| **KL-Divergence Role** | role_head.py | KL(target || pred) con label smoothing eps=0.02. Numericamente stabile con smoothing | OK |
| **VICReg Diversity** | jepa_model.py:786-790 | std(embeddings, dim=0).mean() — penalizza collasso. Corretto per prevenire mode collapse | OK |

---

## 8. DB Schema Consumer Map

I 5 modelli DB piu critici con tutti i loro consumatori:

### PlayerMatchStats

| Aspetto | Dettaglio |
|---|---|
| **Writers** | `user_ingest.py`, `pro_ingest.py`, `round_stats_builder.py` (aggregate) |
| **Readers** | `analytics.py` (3 metodi), `PerformanceScreen`, `MatchHistoryScreen`, `MatchDetailScreen`, `training_orchestrator.py`, `coaching_service.py`, 15+ test |
| **Critical Fields** | `avg_kills`, `avg_deaths`, `avg_adr`, `rating`, `kd_ratio`, `avg_kast` |
| **Change Risk** | **FORBIDDEN rename** — 20+ consumatori simultanei |

### RoundStats

| Aspetto | Dettaglio |
|---|---|
| **Writers** | `round_stats_builder.py`, `user_ingest.py`, `pro_ingest.py` |
| **Readers** | `momentum.py`, `MatchDetailScreen`, `coaching_service.py`, `analytics.py`, `belief_model.py` (calibrator), ConceptLabeler (proposto G-01) |
| **Critical Fields** | `damage_dealt`, `round_won`, `kills`, `deaths`, `round_rating`, `opening_kill` |
| **Change Risk** | **FORBIDDEN rename** — catena coaching + UI + training |

### CoachingInsight

| Aspetto | Dettaglio |
|---|---|
| **Writers** | `coaching_service.py`, `analysis_orchestrator.py` |
| **Readers** | `MatchDetailScreen`, coaching chat ViewModel, `HomeScreen` (quick summary) |
| **Critical Fields** | `title`, `severity`, `message`, `focus_area` |
| **Change Risk** | **FORBIDDEN rename** — UI template in layout.kv dipende da questi nomi |

### PlayerTickState

| Aspetto | Dettaglio |
|---|---|
| **Writers** | `run_ingestion.py` (dual-write MatchTickState + PlayerTickState) |
| **Readers** | `tensor_factory.py`, `vectorizer.py`, `state_reconstructor.py`, `chronovisor_scanner.py`, `meta_drift.py`, `ghost_engine.py` (via TensorFactory) |
| **Critical Fields** | `pos_x`, `pos_y`, `pos_z`, `health`, `armor`, `view_x`, `view_y` |
| **Change Risk** | **FORBIDDEN rename** — ogni modifica spacca training + inference + analysis |

### CoachingExperience

| Aspetto | Dettaglio |
|---|---|
| **Writers** | `experience_bank.py` |
| **Readers** | `experience_bank.py`, `coaching_service.py` (COPER mode) |
| **Critical Fields** | `context_hash`, `embedding`, `effectiveness_score` |
| **Change Risk** | **CONTAINED** — solo ExperienceBank e COPER ne dipendono |

---

## 9. Appendici

### A. Inventario TODO/KNOWN LIMITATION nel Codice

| File:Riga | Tipo | Contenuto | Issue Correlata |
|---|---|---|---|
| `tensor_factory.py:162` | TODO | "Danger zone channel is currently a placeholder" | G-02 |
| `training_orchestrator.py:354` | KNOWN LIMITATION | "Visual inputs are zero-initialized" | G-04 |
| `training_orchestrator.py:368` | KNOWN LIMITATION | "Value targets are binary win/lose" | G-03 (value) |
| `training_orchestrator.py:372` | KNOWN LIMITATION | "Strategy targets are equipment-value bins" | G-03 (strategy) |
| `superposition_net.py:11` | TODO | "context_dim=5 is hardcoded" | G-06 |
| `memory.py:34-37` | NOTE | "Stored patterns start as random [...] attention will be near-uniform" | Architetturale (atteso) |
| `jepa_model.py:465-468` | Implicito | ConceptLabeler usa stessi feature dell'input | G-01 |

### B. Correzioni Necessarie al MEMORY.md

Il file `MEMORY.md` del progetto contiene un'affermazione errata:

> "Proposal 6 (Belief Calibration) Completed: [...] Teacher daemon (session_engine.py): `_run_belief_calibration()` called after retraining"

**Realta verificata**: La funzione `_run_belief_calibration()` NON esiste in `session_engine.py`. Grep conferma zero occorrenze di `belief.*calibrat` nel file. Questa entry in MEMORY.md va corretta per riflettere lo stato reale (G-07).

### C. Configurazioni Runtime e Loro Impatto

| Config | Default | Effetto | Impatto se Cambiato |
|---|---|---|---|
| `USE_COPER` | True | Abilita ExperienceBank coaching | Se False: niente COPER, ricade su Hybrid/Traditional |
| `use_hybrid` | True | Abilita coaching ibrido (neurale+euristico) | Se False: COPER-only o Traditional-only |
| `USE_RAG` | True | Abilita knowledge retrieval | Se False: coaching senza contesto knowledge base |
| `USE_OLLAMA` | True | Abilita NL polishing via Ollama | Se False: coaching in formato raw (meno leggibile) |
| `METADATA_DIM` | 25 | Dimensione feature vector | **FORBIDDEN** — vedi Catena 3 |
| `view_resolution` | 224 | Risoluzione view tensor | Richiede retraining se cambiato |
| `map_resolution` | 128 | Risoluzione map tensor | Richiede retraining se cambiato |

### D. Checkpoint Compatibility Matrix

| Fix | Checkpoint RAP | Checkpoint JEPA | Checkpoint VL-JEPA | Checkpoint Default | Checkpoint RoleHead |
|---|:---:|:---:|:---:|:---:|:---:|
| G-01 | - | - | **INVALIDO** | - | - |
| G-02 | **Subottimale** | - | - | - | - |
| G-03 | **Subottimale** | - | - | - | - |
| G-04 fase 1 | **Subottimale** | - | - | - | - |
| G-04 fase 2 | **INVALIDO** | - | - | - | - |
| G-05 | - | - | - | - | - |
| G-06 | - | - | - | - | - |
| G-07 | - | - | - | - | - |
| G-08 | - | - | - | - | - |

Legenda:
- `-`: Nessun impatto
- `Subottimale`: Funziona ma addestrato su dati inferiori — retraining consigliato
- `INVALIDO`: Incompatibile — retraining obbligatorio

### E. Stato Globale del Sottosistema AI

```
                    +-----------------------+
                    |   AI Subsystem State  |
                    +-----------------------+
                    |                       |
    +-----------+   |   +---------------+   |   +------------------+
    | COPER     |   |   | RAP Coach     |   |   | VL-JEPA          |
    | Coaching  |   |   | (7-layer)     |   |   | (16 concepts)    |
    |-----------|   |   |---------------|   |   |------------------|
    | OPERATIVO |   |   | LIMITATO      |   |   | LIMITATO         |
    | Score: 8/10|  |   | Score: 3/10   |   |   | Score: 2/10      |
    +-----------+   |   +---------------+   |   +------------------+
                    |                       |
    +-----------+   |   +---------------+   |   +------------------+
    | Analytics |   |   | JEPA Base     |   |   | NeuralRoleHead   |
    | Engine    |   |   | (InfoNCE)     |   |   | (5-role MLP)     |
    |-----------|   |   |---------------|   |   |------------------|
    | OPERATIVO |   |   | OPERATIVO     |   |   | OPERATIVO        |
    | Score: 6/10|  |   | Score: 7/10   |   |   | Score: 7/10      |
    +-----------+   |   +---------------+   |   +------------------+
                    |                       |
                    +-----------------------+

    OPERATIVO = Produce output affidabili nel suo dominio
    LIMITATO  = Architettura corretta, training inadeguato (G-02/G-03/G-04)
```

---

*Fine del documento. Ultimo aggiornamento: 2026-02-26.*
*Prossima revisione consigliata: dopo completamento Fase 0 della roadmap.*
