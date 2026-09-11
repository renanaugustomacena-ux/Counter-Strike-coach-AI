# Correzione del nucleo neurale — diagnosi matematica e piano di ricostruzione

> **Documento di lavoro** · Versione 1.1 (2026-09-05, sera) · prima stesura 2026-09-05
> **Trilogia**: questa è la **Parte I** (diagnosi e piano). La **Parte II** (`CORREZIONE_NUCLEO_NEURALE_PARTE_II.md`) contiene la matematica completa con le dimostrazioni e le **verifiche empiriche sui dati veri** (`tools/verify_math_claims.py` → `docs/research/verify_math_claims_2026-09-05.json`); la **Parte III** (`CORREZIONE_NUCLEO_NEURALE_PARTE_III.md`) contiene le istruzioni tecniche per file e funzione. La versione 1.1 estende la copertura a **tutte** le reti e i motori di analisi del progetto (§6b) e corregge la dichiarazione di copertura (§0.2).
> Repo: `Counter-Strike-coach-AI` · HEAD `62cd2f1` · branch `docs/refresh-2026-09-04`
> Autore del progetto: Renan Augusto Macena
> Stato della macchina al momento della scrittura: ingestion pro-demo in corso (`tools/ingest_pro_demos.py --no-train`, log `logs/ingest_2026-09-05.out`), 81+ demo pro nel monolite, ~147 M tick.
>
> Questo documento è il seguito onesto di `jepa.md` (2026-02-21). Quello descriveva l'architettura *così com'era intesa*; questo descrive *cosa fa davvero la matematica*, dove è sbagliata, perché, e come si corregge senza buttare via i pezzi che valgono.

---

## Indice

0. [Perché questo documento e come leggerlo](#0-perché-questo-documento-e-come-leggerlo)
1. [Il verdetto in una pagina](#1-il-verdetto-in-una-pagina)
2. [Il flusso reale oggi: dal file .dem all'utente](#2-il-flusso-reale-oggi-dal-file-dem-allutente)
3. [Fondamenti matematici necessari per capire le correzioni](#3-fondamenti-matematici-necessari-per-capire-le-correzioni)
4. [Diagnosi della JEPA, errore per errore](#4-diagnosi-della-jepa-errore-per-errore)
5. [Diagnosi del RAP coach, errore per errore](#5-diagnosi-del-rap-coach-errore-per-errore)
6. [Diagnosi del contratto dati e della pipeline](#6-diagnosi-del-contratto-dati-e-della-pipeline)
6b. [Le altre reti e i motori di analisi — sintesi](#6b-le-altre-reti-e-i-motori-di-analisi--sintesi)
7. [L'architettura corretta: Macena Coach v2](#7-larchitettura-corretta-macena-coach-v2)
8. [Piano di correzione incrementale](#8-piano-di-correzione-incrementale)
9. [Cosa tenere esattamente com'è](#9-cosa-tenere-esattamente-comè)
10. [Appendici](#10-appendici)

---

## 0. Perché questo documento e come leggerlo

### 0.1 Scopo

Il progetto ha una pipeline dati seria e un'intuizione architetturale giusta, ma il **nucleo neurale** — la parte che dovrebbe imparare — contiene errori matematici che rendono inutile l'allenamento: il modello attuale, anche portato a convergenza, non impara nulla che un allenatore possa usare. Questo documento:

1. dimostra ogni errore con la riga di codice esatta e con la matematica che lo rende un errore;
2. spiega la scienza necessaria per capire perché la correzione è quella e non un'altra;
3. definisce l'architettura corretta (v2) tenendo insieme i pezzi esistenti dove hanno senso;
4. dà un piano di correzione a passi, ognuno con criteri di accettazione verificabili.

### 0.2 Cosa ho letto per scriverlo (dichiarazione di copertura)

Letti integralmente, riga per riga, in questa sessione (nessun sub-agente ha scritto o riassunto per me il contenuto di questo documento):

- `Programma_CS2_RENAN/backend/nn/`: `jepa_model.py`, `jepa_trainer.py`, `jepa_train.py`, `training_orchestrator.py` (1779 righe), `collapse_metrics.py`, `early_stopping.py`, `ema.py`, `config.py`, `factory.py`, `training_config.py`, `dataset.py`, `layers/superposition.py`, `maturity_observatory.py`, `inference/ghost_engine.py`, `coach_manager.py` (sezioni: vocabolari feature, gate di maturità, gate di eleggibilità e split, fasi, fetcher JEPA/RAP, overlay).
- `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/`: `model.py`, `memory.py`, `perception.py`, `strategy.py`, `pedagogy.py`, `communication.py`, `chronovisor_scanner.py`, `trainer.py`.
- `Programma_CS2_RENAN/backend/processing/`: `feature_engineering/vectorizer.py`, `feature_engineering/base_features.py`, `tensor_factory.py`, `state_reconstructor.py`, `skill_assessment.py`, `player_knowledge.py` (testa), `core/spatial_data.py::compute_z_penalty`.
- `run_full_training_cycle.py`, `backend/coaching/jepa_insight_adapter.py` (testa e gate), `backend/nn/data_quality.py` (soglie).
- Documentazione: `jepa.md`, `docs/research/INDEX.md`, `docs/doctrine/notes/07a-nn-jepa.md`, `07c-nn-rap.md`, `16-papers.md`, `docs/jepa_training_tuning_observations_2026-05-06.md`, `docs/OPEN_ISSUES.md`, sezioni JEPA/RAP di `TASKS.md`, elenco dei test in `Programma_CS2_RENAN/tests/test_jepa_*.py`, `test_rap_coach.py`, `test_jepa_insight_adapter.py`, sidecar dei checkpoint archiviati.

Letti integralmente in questa sessione (versione 1.1), per coprire ogni componente AI del progetto e non solo JEPA/RAP: `backend/nn/model.py` (AdvancedCoachNN, alias `TeacherRefinementNN`, ModelManager), `backend/nn/train.py`, `backend/nn/role_head.py`, `backend/nn/win_probability_trainer.py`, `backend/nn/evaluate.py`, `backend/nn/persistence.py`, `backend/nn/data_quality.py`, `backend/nn/training_callbacks.py`, `backend/nn/training_controller.py`, `backend/nn/training_monitor.py`, `backend/analysis/win_probability.py`, `backend/analysis/belief_model.py`, `backend/analysis/game_tree.py`, `backend/analysis/entropy_analysis.py`, `backend/analysis/role_classifier.py`, `backend/analysis/momentum.py`, `backend/analysis/blind_spots.py` (rilevatore), `backend/analysis/deception_index.py` (pesi), `backend/coaching/hybrid_engine.py`, `backend/coaching/nn_refinement.py`, `backend/coaching/jepa_insight_adapter.py` (intero), `backend/processing/baselines/pro_baseline.py` (baseline e z-score), `backend/processing/validation/drift.py`, `backend/knowledge/experience_bank.py` (costanti, aggiornamento "TrueSkill", sintesi, replay, feedback). Letti per struttura con lettura mirata dei punti matematici: `backend/knowledge/rag_knowledge.py`, `backend/knowledge/vector_index.py`, `backend/services/coaching_service.py`, `backend/services/llm_service.py`, `backend/services/coaching_dialogue.py`, `backend/processing/data_pipeline.py`, `backend/analysis/{movement_quality,utility_economy,engagement_range}.py`, `observability/label_source_monitor.py`, `tools/eval_harness.py`, `evals/cs2_coach_bench/run_eval.py`. L'analisi matematica di ciascuno è nella **Parte II §11**; la sintesi in §6b qui sotto.

Letti in una fase precedente tramite tre agenti di esplorazione (report con riferimenti `file:riga`, poi verificati a campione sui sorgenti): `run_ingestion.py` (shard builder), `db_models.py`, `match_data_manager.py`, `server.py`, `lifecycle.py`/`session_engine.py`, `lesson_generator.py`, `REFERENCE.md`, `AUDIT.md`.

Non letti: scraper HLTV, viewmodel Qt, la parte demoparser di `run_ingestion.py`, `tools/` diversi da `eval_harness.py`, `ingest_pro_demos.py`, `observe_training_cycle.py`. Nessuna affermazione di questo documento dipende da quei file.

**Dati letti in sola lettura** (2026-09-05, ingestione in corso): monolite `database.db` (`playertickstate`, `roundstats`, `playermatchstats`, `ingestiontask`), checkpoint archiviati con sidecar. Le misure sono nella Parte II §12.

### 0.3 Letteratura consultata

Ricerca arXiv del 2026-09-05 via API: 442 paper con "JEPA" nel titolo/abstract, di cui 109 su serie temporali/sensori/tabulare, 110 su regolarizzazione anti-collasso, 189 su world model/planning. **Nella versione 1.1 i paper primari sono stati letti in testo integrale** (PDF scaricati e convertiti, equazioni e dimostrazioni comprese, senza riassunti intermedi): LeJEPA (2511.08544, §2–7 e appendici A–B con le dimostrazioni), LeNEPA (2607.00958), LeWorldModel (2603.19312 con appendici), "JEPAs focus on slow features" (2211.10831), Tian–Chen–Ganguli sulle dinamiche non contrastive (2102.06810), Jing et al. sul collasso dimensionale (2110.09348), RankMe (2210.02885), la teoria di generalizzazione per world model JEPA (2606.27014), HEPA (2605.11130), "Surprise as a signal" (2606.31495), la complessità di scenario zero-label via JEPA (2606.28383), Switch Transformers (2101.03961 §2.2), VICReg (2105.04906 §4.1), Guo et al. sulla calibrazione (1706.04599), CPC (1807.03748 §2), BYOL (2006.07733 §3.1), I-JEPA (2301.08243 §3), T-JEPA (2410.05016 §3), CF-JEPA (2606.07031 §3), RoPE (2104.09864), GLU/SwiGLU (2002.05202), RMSNorm (1910.07467), ViT-22B/QK-norm (2302.05442), DiT/adaLN-Zero (2212.09748). Codice ufficiale: `galilai-group/lejepa/MINIMAL.md`, `lucas-maes/le-wm/module.py`. L'elenco con le parti lette è nella Parte II §0.2 e App. B. La biblioteca del progetto (`docs/research/INDEX.md`) marcava già LeJEPA come **"Critico"** il 2026-07 e `TASKS.md` C9 registra "drop EMA-teacher via SIGReg" come enhancement non eseguito: questo documento porta a compimento quella intuizione.

### 0.4 Convenzioni

- Abbreviazioni di percorso: `nn/` = `Programma_CS2_RENAN/backend/nn/`; `rap/` = `nn/experimental/rap_coach/`; `proc/` = `Programma_CS2_RENAN/backend/processing/`; `coach/` = `Programma_CS2_RENAN/backend/coaching/`.
- Ogni errore è presentato con lo stesso schema: **Evidenza** (righe di codice) → **Perché è sbagliato** (matematica) → **Conseguenza** (cosa succede davvero al modello) → **Correzione** (cosa cambiare, precisamente) → **Test** (quali test cambiano).
- Gravità: **BLOCCANTE** = con questo errore il modello non può imparare nulla di utile; **GRAVE** = impara la cosa sbagliata o fallisce in silenzio; **MEDIO** = spreca dati/compute o rende i numeri non interpretabili; **MINORE** = pulizia.
- Le sezioni "In parole semplici" sono scritte per chi non legge codice. Le sezioni "Nel dettaglio" sono per chi implementa.

---

## 1. Il verdetto in una pagina

**In parole semplici.** Il progetto ha costruito tre cose: (1) una fabbrica di dati eccellente (parsing dei demo, database, controlli di qualità, split anti-imbroglio); (2) una rete "JEPA" che dovrebbe imparare a rappresentare lo stato di gioco; (3) un "RAP coach" che dovrebbe ragionare e dare consigli. La fabbrica di dati funziona. La JEPA è configurata in modo tale che il compito che le viene dato è quasi banale (indovinare il prossimo quindicesimo di secondo partendo dal presente) e quindi impara pochissimo; in più parti della sua "difesa anti-collasso" sono spente senza che nessuno se ne accorga. Il RAP non ha mai completato un allenamento, non usa la JEPA, e le sue funzioni di perdita (le formule che dicono alla rete cosa è giusto) hanno errori di segno e di tipo. Infine, il consiglio che arriva all'utente non passa da nessuna di queste reti: arriva da statistiche aggregate e dall'LLM. **Quindi oggi il prodotto "coach AI" non è un prodotto AI: è un analizzatore statistico con un LLM davanti.** Questo si corregge, e la maggior parte del lavoro fatto si riusa.

### 1.1 Tabella riassuntiva

| # | Componente | Cosa fa davvero oggi | Gravità | Azione |
|---|---|---|---|---|
| J1 | Batch JEPA | Una sola finestra per batch (`B=1`); ogni statistica di batch è indefinita | BLOCCANTE | Batch ≥128 finestre |
| J2 | Orizzonte di predizione | Predice il tick successivo (~15,6 ms): il bersaglio è quasi identico al contesto | BLOCCANTE | Token da 8 tick, orizzonti 0,125–2 s |
| J3 | Encoder | MLP per singolo tick + media: ignora l'ordine temporale | GRAVE | Encoder temporale (Transformer causale) |
| J4 | Obiettivo InfoNCE | 5 negativi grezzi + 64 da una coda inizializzata a caso; τ appreso | GRAVE | Predizione latente + SIGReg (niente negativi) |
| J5 | VICReg | Ritorna sempre 0.0 con `B=1`: inerte, nessun avviso | GRAVE (silenzioso) | Sostituito da SIGReg; asserire `B≥2` |
| J6 | Target encoder EMA | Inizializzato indipendentemente dal context encoder; contatori di resume solo sul path che non gira | MEDIO | Rimosso (SIGReg non ne ha bisogno); se tenuto, copia iniziale |
| J7 | Path di training | Tre implementazioni divergenti (CLI, `train_epoch` morto, orchestratore) | GRAVE (processo) | Un solo trainer |
| J8 | Testa di coaching | LSTM+MoE mai allenati, serializzati in ogni checkpoint; l'adapter verso il coach non si arma mai | GRAVE | Sostituita da probe su latenti + world model |
| J9 | VL-JEPA concetti | Label derivate dalle stesse feature in input (leakage); residuo di leakage anche nel path "outcome" via `equipment_value` | GRAVE | Probe con label esterne; tassonomia come output, non come input |
| J10 | Rilevatore di collasso | Soglia 0.01 tarata per varianza intra-batch, applicata a varianza tra finestre | MEDIO | RankMe + std su probe batch, soglie ricalibrate |
| J11 | Loss di validazione | Non confrontabile col training (5 vs 69 negativi); il valore ~0.004 registrato è coerente con un bersaglio quasi-identità | MEDIO | Metriche di utilità (probe, RankMe) al posto della loss |
| J12–J14 | Codice morto / no-op | `forward_selective`, `train_epoch`, drift-retrain, `JEPATrainingConfig` mai importata, espansione ×10 dei negativi | MINORE | Rimozione |
| R1 | RAP ↔ JEPA | Nessun legame: RAP parte da pixel sintetici + 25 feature grezze | GRAVE | Teste RAP sopra i latenti JEPA |
| R2 | Training RAP | Mai completato un run validato; flag `USE_RAP_MODEL=False`; dipendenze non-PyPI | BLOCCANTE (prodotto) | Riprogettato come "Coach v2" |
| R3 | Testa strategia | MSE su one-hot (non cross-entropy); classe `ROLE_ROTATION` irraggiungibile | GRAVE | Cross-entropy; label riviste |
| R4 | Loss MoE | Minimizza l'entropia del gate: premia il collasso su un esperto | GRAVE | Switch load-balancing (segno corretto) |
| R5 | Valore (critic) | Bersaglio = formula euristica dello stato: impara la formula, non l'esito | MEDIO | Doppio bersaglio: euristico ausiliario + esito reale scontato |
| R6 | Memoria | LTC (dipendenza fragile) + Hopfield che scrive solo via backprop | MEDIO | Memoria episodica gated dalla sorpresa |
| R7 | Percezione | "ResNet" a larghezza costante; fallback legacy con canali ridondanti | MEDIO | Rimandata dopo la v2 tabulare |
| R8 | Attribuzione | 3 concetti su 5 collineari, 1 sempre zero; `skill_vec` mai passato | GRAVE | Controfattuali + gradienti delle probe |
| R9 | Comunicazione | `confidence=0.85` costante; topic = `argmax % 3` | GRAVE (onestà) | Confidenza calibrata; topic da attribuzione |
| R10 | Chronovisor | Algoritmo corretto; scale in tick, nessun lisciamento | MINORE | Secondi, Savitzky–Golay, ingresso "sorpresa" |
| R11 | Regimi di finestra | Train 5D per-timestep, Chronovisor 1 frame ×32, Ghost T=1; overlay copia 1 output su 32 tick | MEDIO | Un solo regime |
| R12 | Observatory | Legge attributi che non esistono (`_last_belief_batch`, `strategy.superposition`) | MEDIO | Segnali registrati esplicitamente |
| R13 | Batch RAP | `_fetch_rap_windows(window_size=96)` con `seq_len=32` → 3 finestre per batch: BatchNorm e statistiche su 3 campioni (coefficiente di variazione 100%, Parte II Prop. 5) | GRAVE | Batch ≥ 32 o norme senza statistiche di batch |
| D1–D7 | Contratto dati | Feature 16 sempre 0; `map_id` = hash; `round_phase` ridondante; normalizzatori hardcoded; due vocabolari da 25; stato globale nell'estrattore; 5 entry point | MEDIO | Schema tipizzato v2 |
| D8 | Nomi giocatore | `roundstats` normalizza (`lower/strip`), `playertickstate`/`playermatchstats` no: 47/105 nomi senza corrispondenza esatta, 18/48 coppie senza tick nel campione | MEDIO | Normalizzazione unica + migrazione (Parte III §2.4) |
| D9 | Split | Tutte le 1.031 righe di `playermatchstats` sono `UNASSIGNED`: nessun training può leggere `TRAIN` | BLOCCANTE (operativo) | `assign_dataset_splits` prima di ogni training |
| A1 | AdvancedCoachNN | Bersaglio = `clip((pro−cur)/scale)` funzione dell'input: leakage totale; LSTM su sequenza di lunghezza 1 | GRAVE | Ritirare; il delta è uno z-score (Parte II §11.1) |
| A2 | NeuralRoleHead | KL su etichette soft esterne, normalizzazione salvata: **corretto** | — | Tenere; verificare semantica feature; calibrare |
| A3 | WinProbabilityTrainerNN | BCE su 9 feature grezze non normalizzate; mai addestrato | MEDIO | Eliminare / unificare |
| A4 | WinProbabilityNN + euristiche | Rete mai addestrata (pesi casuali, W-02) + clamp a mano; Platt dormiente; usata come funzione di valutazione dell'albero | GRAVE | Sonda `round_won` su latenti + Platt (Parte II §11.4) |
| A5 | DeathProbabilityEstimator | Logit a coefficienti a mano; "MC dropout" che perturba gli input | MEDIO | Regressione logistica o sonda evento (Parte II §11.5) |
| A6 | Expectiminimax + BlindSpots | Ricorsione corretta su transizioni inventate e foglie valutate da A4 | GRAVE | Ritirare; il world model è il modello |
| A7 | EntropyAnalyzer | Entropia su griglia ridefinita per chiamata: non misura ciò che dice; $\Delta H_{max}$ irraggiungibili | MEDIO | Griglia fissa / Δ-sorpresa |
| A8 | ExperienceBank | EMA chiamata "TrueSkill"; σ decresce di 0,95 a prescindere dall'evidenza | MEDIO | Beta-binomiale (Parte III §8.1) |
| A9 | Momentum, Deception, Hybrid confidence | Punteggi a mano o indici ordinali presentati come confidenze | MINORE/MEDIO | Stimare o etichettare; "priorità" non "confidenza" |

### 1.2 Le tre frasi che contano

1. **Nessun output neurale raggiunge oggi l'utente.** La JEPA produce un checkpoint marcato `head_trained=False` (`nn/training_orchestrator.py:467-469`) che l'adapter verso il coach rifiuta per costruzione (`coach/jepa_insight_adapter.py:180-228`); il RAP non ha un checkpoint validato e il `GhostEngine` è disabilitato da `USE_RAP_MODEL=False`; l'LLM riceve statistiche aggregate, non tensori.
2. **Il compito dato alla JEPA è quasi banale.** Con orizzonte di un tick e finestre contigue, il bersaglio differisce dal contesto per meno dello 0,1% del range delle feature: un predittore identità ottiene loss quasi zero. La loss di validazione registrata nel checkpoint archiviato (`best_val_loss` ≈ 0.004) è coerente con questo, non con un modello che ha capito il gioco.
3. **Le misure sui dati veri confermano il verdetto** (Parte II §12): a un tick l'identità spiega il 99,78% della varianza del bersaglio; una rete a pesi casuali con predittore identità risolve InfoNCE al 97%; il checkpoint archiviato usa 66 dimensioni su 256 (rete casuale: 61) ed è **peggiore delle feature grezze** e uguale a una rete casuale sulle sonde "round vinto" (AUROC 0,68 vs 0,76) e "morte entro 2 s" (0,74 vs 0,84).
4. **La correzione non richiede di buttare via il progetto.** La pipeline dati, lo split, il contratto delle feature, i controlli di qualità, `collapse_metrics.py`, `PlayerKnowledge`, l'algoritmo del Chronovisor, il layer FiLM e la disciplina di osservabilità restano. Cambiano: l'obiettivo di training, la forma delle finestre, l'encoder, e il modo in cui le teste del coach si collegano all'encoder.

---

## 2. Il flusso reale oggi: dal file .dem all'utente

**In parole semplici.** Immagina una catena di montaggio. I primi reparti (leggere i demo, metterli in ordine, controllare che i dati siano sani) funzionano. Il reparto "cervello" lavora su un problema sbagliato e il suo prodotto finisce in un magazzino che nessuno apre. Il reparto "allenatore" non ha mai acceso le macchine. Alla fine della catena, il consiglio che esce viene da un altro reparto (statistiche + LLM) che non ha mai visto il cervello.

### 2.1 La catena, reparto per reparto

```
[1] file .dem
      │  demoparser2 → run_ingestion.py (shard per partita + monolite SQLite WAL)
      ▼
[2] PlayerTickState (monolite) + matchtickstate (shard)   ← ~147 M righe, 81+ demo pro
      │  FeatureExtractor.extract_batch()  (proc/feature_engineering/vectorizer.py)
      ▼
[3] vettore 25-dim per tick (25 float; 1 sempre 0; 1 hash)
      │  coach_manager._fetch_jepa_windows(): finestre contigue di 11 tick, stesso giocatore, stesso round
      ▼
[4] TrainingOrchestrator._prepare_tensor_batch()  → context (1,10,25) · target (1,1,25) · negatives (1,5,25)
      │  JEPATrainer.train_step(): InfoNCE + 0.01·VICReg(=0) ; EMA target
      ▼
[5] checkpoint jepa_brain.pt + sidecar {head_trained: False}
      │
      ├─► coach/jepa_insight_adapter.py  → rifiuta: head_trained ≠ True  (F-0029)      ✖ STOP
      │
[6] RAPCoachModel  (pixel sintetici 64×64 + 25 feature)  → nessun run validato          ✖ STOP
      │  GhostEngine: USE_RAP_MODEL=False → "lobotomized", predict_tick → None
      ▼
[7] CoachingService (COPER: RAG + esperienze + riferimenti pro) + LLMService (Ollama)
      │  lesson_generator._generate_narrative(): 8 scalari da PlayerMatchStats          ← nessun tensore
      ▼
[8] UI Qt: card di coaching, overlay disabilitato ("calibrating"/"disabled")
```

### 2.2 I tre punti di rottura

1. **[4]→[5]: il cervello impara la cosa sbagliata.** Dettagli in §4 (J1–J5).
2. **[5]→[7]: il prodotto del cervello non viene mai consumato.** L'adapter (`coach/jepa_insight_adapter.py`) è progettato per leggere la *testa di coaching* (LSTM+MoE, 10 output) via `model.forward_coaching(x)` (riga 276), ma quella testa non è mai stata allenata su nessun path raggiungibile: l'orchestratore fa solo pre-training (`_checkpoint_extra_meta` scrive `head_trained=False`), e il fine-tuning CLI solleva `ValueError` per contratto (`nn/jepa_train.py:634-641`). Il gate F-0029 fa la cosa giusta rifiutando il checkpoint; il risultato netto è che l'adapter non si arma mai.
3. **[6]: il RAP è un ramo secco.** Costruttore protetto da `USE_RAP_MODEL` (`nn/training_orchestrator.py:128-132`), dipendenze `ncps`/`hflayers` (la seconda non è su PyPI), un solo checkpoint smoke del 3 agosto 2026 senza `best_val_loss` nel sidecar, mai un run con early stopping.

### 2.3 Cosa succede alla riga 242 di `run_full_training_cycle.py`

Le "Phase 1: JEPA" e "Phase 2: RAP" del ciclo completo non sono una consegna di conoscenza ma due processi sequenziali indipendenti: tra le due, `del orchestrator_jepa; gc.collect(); torch.cuda.empty_cache()` (righe 242-247) distrugge l'oggetto JEPA. Il RAP non riceve né pesi né embedding. È la prova strutturale di R1.


---

## 3. Fondamenti matematici necessari per capire le correzioni

Questa sezione non è un corso: contiene solo la matematica che serve a giudicare gli errori del §4–§6 e a capire perché le correzioni del §7 sono quelle e non altre. Ogni sottosezione parte da un'analogia e arriva alle formule.

### 3.1 Rappresentazioni e spazio latente

**In parole semplici.** Un *encoder* è una funzione che comprime una situazione di gioco (decine di numeri per tick, per molti tick) in un vettore di poche centinaia di numeri: le "coordinate" di quella situazione in uno *spazio delle situazioni*. Se l'encoder è buono, situazioni simili finiscono vicine e situazioni diverse lontane, e informazioni utili (chi vincerà il round, se il giocatore morirà tra due secondi, che ruolo sta giocando) si possono leggere con una regola semplice, quasi una riga retta, dentro quello spazio. Un coach AI ha bisogno esattamente di questo: uno spazio dove "dove ti trovi" dica qualcosa di vero sulla partita.

**Nel dettaglio.** Sia $x \in \mathbb{R}^{T \times D}$ una finestra di $T$ tick con $D$ feature per tick e $f_\theta: \mathbb{R}^{T\times D} \to \mathbb{R}^{d}$ l'encoder. Le proprietà misurabili che ci interessano:

1. **Informatività**: quante direzioni indipendenti usa lo spazio (rango effettivo, §3.7). Se tutte le finestre finiscono nello stesso punto, l'encoder ha "collassato".
2. **Linearità delle letture**: quanto bene una *probe lineare* $w^\top z + b$ predice un fatto esterno $y$ (esito del round, morte entro $k$ secondi). È la misura standard di qualità di una rappresentazione auto-supervisionata (I-JEPA, V-JEPA, LeJEPA la usano tutti).
3. **Prevedibilità della dinamica**: quanto $z_{t+h}$ è predicibile da $z_{\le t}$ per orizzonti $h$ che contano per il coaching (frazioni di secondo → secondi).

### 3.2 JEPA come modello ad energia

**In parole semplici.** Una JEPA impara *predicendo nello spazio delle coordinate, non nello spazio dei pixel*: dato il presente (contesto) deve indovinare le coordinate del futuro (bersaglio). Il trucco è che non deve ricostruire ogni dettaglio del futuro, solo la sua "posizione" nello spazio delle situazioni. Il pericolo è altrettanto semplice: se l'encoder mappa tutto nello stesso punto, la predizione è perfetta e inutile. Tutta la ricerca su JEPA dal 2022 al 2026 è, in fondo, la storia di come evitare quel punto.

**Nel dettaglio.** Con encoder di contesto $f_\theta$, encoder di bersaglio $\bar f$ e predittore $g_\phi$, la JEPA minimizza un'energia

$$E_{\theta,\phi}(x, y) = \left\lVert g_\phi\!\left(f_\theta(x)\right) - \bar f(y) \right\rVert^2 ,$$

dove $x$ è il contesto e $y$ il bersaglio (LeCun 2022; I-JEPA, Assran et al. 2023). Il minimizzatore banale è $f_\theta \equiv \bar f \equiv c$ costante: energia zero per ogni coppia. La teoria (2606.27014) mostra che, sotto rumore di osservazione e orizzonti lunghi, la predizione latente batte la ricostruzione dell'input: è il motivo per cui la scelta "JEPA" del progetto è giusta. Il problema del progetto non è l'idea, è come sono stati scelti $x$, $y$ e la difesa contro il minimizzatore banale.

### 3.3 Il collasso e le tre famiglie di rimedi

**In parole semplici.** Ci sono tre modi noti per impedire all'encoder di "mettere tutto nello stesso punto": (a) mostrargli esempi *negativi* e chiedergli di tenerli lontani; (b) rendere il bersaglio un po' diverso dal contesto con trucchi (un secondo encoder che si aggiorna lentamente, niente gradiente sul bersaglio); (c) imporre direttamente che la nuvola di punti abbia una forma sana (varianza, decorrelazione, forma gaussiana). Il progetto usa (a) e (b) insieme più un pezzo di (c) che però è spento. La ricerca del 2025–2026 dice che (c), fatto bene, rende (a) e (b) inutili.

**(a) Contrastivo — InfoNCE** (CPC 2018, SimCLR, MoCo). Con predizione $p$, bersaglio positivo $t^+$, negativi $t^-_j$ ($j=1..N$), similarità coseno $s(\cdot,\cdot)$ e temperatura $\tau$:

$$\mathcal{L}_{\text{InfoNCE}} = -\log \frac{e^{s(p,t^+)/\tau}}{e^{s(p,t^+)/\tau} + \sum_{j=1}^{N} e^{s(p,t^-_j)/\tau}} .$$

Proprietà che contano qui: (i) il valore "a caso" della loss è $\log(N{+}1)$ (con $N=5$: $1.79$; con $N=69$: $4.25$); (ii) la qualità dipende dal fatto che i negativi siano *difficili ma veri* — negativi troppo facili (partite diverse) portano la loss a zero senza insegnare nulla, negativi "falsi" (stati quasi uguali al positivo) confondono; (iii) servono molti negativi e batch grandi (SimCLR 4096, MoCo coda 65536); (iv) è un lower bound dell'informazione mutua, limitato da $\log(N{+}1)$.

**(b) Asimmetria — EMA target + stop-gradient** (BYOL 2020, I-JEPA 2023, V-JEPA 2024). Il bersaglio è prodotto da una copia lenta dell'encoder:

$$\bar\theta \leftarrow m\,\bar\theta + (1-m)\,\theta, \qquad m \in [0.996, 1.0],$$

senza gradiente attraverso $\bar f$. Funziona empiricamente ma è una collezione di euristiche (momentum, schedule, predittore stretto, inizializzazione $\bar\theta_0=\theta_0$) la cui stabilità non è garantita: LeJEPA (2511.08544) le chiama esplicitamente "heuristics" e le rimuove.

**(c) Regolarizzazione distribuzionale.**

*VICReg* (2105.04906) su una matrice di embedding $Z \in \mathbb{R}^{N\times d}$:

$$v(Z) = \frac{1}{d}\sum_{j=1}^{d} \max\!\left(0,\ \gamma - \sqrt{\operatorname{Var}(Z_{:,j}) + \epsilon}\right), \qquad c(Z) = \frac{1}{d}\sum_{i\ne j} C(Z)_{ij}^2 ,$$

con $C(Z)$ covarianza campionaria. Nel codice del progetto (`nn/jepa_model.py:433-449`) c'è esattamente questo, con $\gamma=1$, pesi $25$ e $1$, e **`if embeddings.shape[0] < 2: return 0.0`**: la varianza campionaria di un solo punto non esiste (denominatore $N-1=0$), quindi con $N=1$ il termine è per definizione indefinito e il codice lo azzera.

*SIGReg* (LeJEPA, §3.4): impone che $Z$ sia distribuito come una gaussiana isotropa $\mathcal N(0, I_d)$, il che implica automaticamente varianza unitaria e decorrelazione in ogni direzione.

### 3.4 SIGReg: la regolarizzazione che sostituisce cinque meccanismi

**In parole semplici.** Invece di dire "tieni lontani i negativi" e "aggiorna lentamente una copia", SIGReg dice all'encoder: "la nuvola delle tue coordinate deve avere la forma di una palla gaussiana, in ogni direzione". LeJEPA dimostra che quella forma è la migliore possibile quando *non sai ancora* quali domande farai allo spazio (esattamente il caso del coaching: mille domande diverse). Per controllare la forma usa un trucco classico di statistica: proietta la nuvola su tante rette casuali e verifica che ogni ombra unidimensionale sia una gaussiana standard. Un solo iperparametro, niente negativi, niente copia lenta, niente stop-gradient — e la loss di training diventa *informativa*: più bassa, meglio va nei compiti a valle (correlazione di Spearman ≈ 0.94 nel paper), il che permette di scegliere il modello senza etichette.

**Nel dettaglio.**

*Perché la gaussiana isotropa.* LeJEPA (2511.08544, §3): per probe lineari, se la covarianza dell'embedding ha autovalori $\lambda_1 > \dots > \lambda_d$ con $\lambda_d < \lambda_1$, esiste sempre un compito a valle con bias più alto (Lemma 1), e la varianza totale dello stimatore è minima per covarianza isotropa (Lemma 2); per probe non lineari (kNN, kernel) la gaussiana isotropa è l'unico minimizzatore del bias quadratico integrato tra le distribuzioni con vincolo scalare sulla covarianza (Teorema 1).

*Come si verifica la forma.* Cramér–Wold: $Z \sim \mathcal N(0, I_d)$ se e solo se per ogni direzione unitaria $a \in S^{d-1}$ la proiezione $a^\top Z \sim \mathcal N(0,1)$. Si campionano $M$ direzioni e per ciascuna si usa la statistica di normalità di Epps–Pulley basata sulla funzione caratteristica:

$$\mathrm{EP}(u_1,\dots,u_N) = N \int_{-\infty}^{+\infty} \left| \hat\varphi_N(t) - e^{-t^2/2} \right|^2 w(t)\, dt, \qquad \hat\varphi_N(t) = \frac1N \sum_{n=1}^{N} e^{\,i t u_n},$$

con $w(t) = e^{-t^2/2}$. Separando parte reale e immaginaria:

$$\left| \hat\varphi_N(t) - e^{-t^2/2} \right|^2 = \Big(\tfrac1N\sum_n \cos(t u_n) - e^{-t^2/2}\Big)^2 + \Big(\tfrac1N\sum_n \sin(t u_n)\Big)^2 .$$

L'integrale si calcola con la regola dei trapezi su $K=17$ nodi in $t\in[0,3]$ (simmetria della funzione caratteristica: si integra su metà dominio e si raddoppia), pesi $w_k$ = trapezio × finestra $e^{-t_k^2/2}$. Il valore finale è la media su $M$ direzioni ricampionate a ogni passo. Implementazione esatta (LeWorldModel, `lucas-maes/le-wm/module.py`), 15 righe:

```python
class SIGReg(torch.nn.Module):
    def __init__(self, knots=17, num_proj=1024):
        super().__init__()
        t = torch.linspace(0, 3, knots)                 # nodi di quadratura
        dt = 3 / (knots - 1)
        weights = torch.full((knots,), 2 * dt); weights[[0, -1]] = dt   # trapezi
        window = torch.exp(-t.square() / 2.0)           # finestra w(t) = phi(t) della N(0,1)
        self.register_buffer("t", t); self.register_buffer("phi", window)
        self.register_buffer("weights", weights * window); self.num_proj = num_proj
    def forward(self, proj):                            # proj: (T, B, D) — N = B campioni per tempo
        A = torch.randn(proj.size(-1), self.num_proj, device=proj.device)
        A = A.div_(A.norm(p=2, dim=0))                  # M direzioni unitarie casuali
        x_t = (proj @ A).unsqueeze(-1) * self.t         # proiezioni × nodi
        err = (x_t.cos().mean(-3) - self.phi).square() + x_t.sin().mean(-3).square()
        statistic = (err @ self.weights) * proj.size(-2)   # Epps–Pulley × N
        return statistic.mean()                          # media su direzioni e tempo
```

Costo $O(N \cdot M \cdot K)$: trascurabile.

*Come si combina con la predizione.* Tre ricette pubblicate, tutte senza EMA, senza stop-gradient, senza negativi:

| Ricetta | Loss | Iperparametri | Fonte |
|---|---|---|---|
| LeJEPA (immagini, multi-vista) | $\lambda\,\mathrm{SIGReg} + (1-\lambda)\,\lVert \mu - z_v\rVert^2$ | $\lambda = 0.05$, $M=1024$, $B\ge128$ | 2511.08544 |
| LeWorldModel (video + azioni) | $\lVert \hat z_{t+1} - z_{t+1}\rVert^2 + \lambda\,\mathrm{SIGReg}(Z)$ | $\lambda = 0.1$, $M=1024$ | 2603.19312 |
| LeNEPA (serie temporali) | $\lVert h(\hat z_t) - h(z_{t+1})\rVert^2 + \lambda_T\,\mathrm{SIGReg}_{\text{temporale}}$ | $\lambda_T \in [2.5, 20]$, proiettore $h$ a 64 dim | 2607.00958 |

LeNEPA è la ricetta più vicina al nostro caso (flussi campionati nel tempo, senza augmentation): SIGReg è applicato **per campione lungo il tempo** (i $T$ token di una finestra devono distribuirsi come una gaussiana), non solo lungo il batch; la loss di predizione è calcolata nello spazio di un *proiettore* $h$ (MLP) che viene poi scartato, perché "calcolare la loss nello spazio proiettato impedisce all'encoder di specializzarsi sul compito di predizione"; le probe migliori si leggono ai layer intermedi.

*Cosa sostituisce nel nostro codice.* InfoNCE + τ apprendibile + coda MoCo + VICReg + EMA target con schedule coseno (cinque meccanismi, otto iperparametri) → un termine, un iperparametro.

### 3.5 Quanta informazione c'è nel bersaglio? Il problema dell'orizzonte

**In parole semplici.** Se ti chiedo "dove sarai tra un centesimo di secondo?", la risposta giusta è "esattamente dove sono adesso": non serve capire nulla del gioco. Se ti chiedo "dove sarai tra due secondi?", devi capire dove stai andando, cosa vedi, cosa sta succedendo. La JEPA attuale fa la prima domanda (un tick = 15,6 ms) e quindi impara la risposta banale.

**Nel dettaglio.** Sia $x_{t+h} = x_t + \Delta_h$. Se $f$ è $L$-Lipschitz, il predittore identità $g = \mathrm{id}$ ottiene

$$\lVert f(x_{t+h}) - f(x_t) \rVert \le L\,\lVert \Delta_h \rVert ,$$

quindi con $\Delta_h \to 0$ la loss va a zero *senza alcun apprendimento*, per qualunque encoder liscio. L'unica pressione residua sull'encoder è ridurre $L$ lungo le traiettorie (rendere le feature "lente"): utile in astratto (2211.10831, nella biblioteca del progetto), ma con $h$ di un tick *tutto* è lento, quindi non c'è selezione di cosa conservare.

Numeri per CS2 a 64 tick/s ($\Delta t = 15{,}6$ ms), con le normalizzazioni di `vectorizer.py`:

| Feature | Variazione massima in un tick | Normalizzata |
|---|---|---|
| `pos_x`, `pos_y` (velocità max ≈ 250 u/s → ≈ 3,9 u/tick) | 3,9 u | $3{,}9/4096 \approx 0{,}00095$ |
| `pos_z` | 3,9 u | $3{,}9/1024 \approx 0{,}0038$ |
| `view_pitch` | tipicamente < 2°/tick | $< 0{,}02$ |
| `view_yaw_sin/cos` | tipicamente < 5°/tick (flick esclusi) | $< 0{,}09$ |
| `health`, `armor`, `equipment_value` | 0 nella maggioranza dei tick | 0 |
| flag binari (`is_crouching`, `bomb_planted`, …) | cambiano in una frazione ≪ 1% dei tick | 0 quasi sempre |
| contatori (`time_in_round`) | 1/115 s per tick | 0,00014 |

**Misura (Parte II §12.2, 1,2 M tick pro, 64,0 tick/s):** media di $|\Delta_1|$ per componente $7{,}9\cdot10^{-4}$; $R^2$ dell'identità 0,9978 a 1 tick, 0,974 a 125 ms, 0,911 a 0,5 s, 0,768 a 2 s, 0,444 a 10 s; 19 feature su 25 costanti in oltre il 93% delle finestre di 11 tick; salute/armatura/equipaggiamento cambiano in meno dello 0,2% dei tick. La tabella sopra (stime a priori) è confermata e superata dalle misure. Nella grande maggioranza dei tick $\lVert \Delta_1 \rVert_\infty \lesssim 10^{-3}$. Con InfoNCE la similarità positiva vale ≈ 1 per costruzione e i negativi (tick di *altre partite*, `nn/training_orchestrator.py:868-882`) sono banalmente lontani: la loss precipita verso zero. È esattamente ciò che è successo: prima della correzione R4 (finestre casuali non contigue) la validazione stava a ≈ 1.97, vicino al livello "a caso" $\log 6 = 1.79$ dei 5 negativi (`docs/jepa_training_tuning_observations_2026-05-06.md`); dopo la correzione R4 (finestre contigue, bersaglio = tick successivo) il checkpoint archiviato registra `best_val_loss = 0.004024` (`Programma_CS2_RENAN/models/global/archive_pre_rebuild_2026-09-01/jepa_brain.pt.meta.json`). Il passaggio da "a caso" a "quasi perfetto" non è la firma di un modello che ha capito il gioco: è la firma di un compito diventato risolvibile dall'identità.

*Correzione.* Scegliere $h$ dove l'informazione predittiva $I(z_t; z_{t+h})$ non è né quasi tutta (banale) né quasi nulla (imprevedibile). Per le decisioni che un coach commenta — peek, rotazioni, ingaggi, uso di utility — la scala è 0,1–2 s. Ricetta v2 (§7): token = 8 tick (125 ms) tramite conv1d a passo 8 (nessuna decimazione: tutti i tick entrano nel token), predizione del token successivo (LeNEPA) più orizzonti a +4 e +16 token (0,5 s e 2 s, stile CF-JEPA multi-orizzonte).

### 3.6 Statistiche di batch: cosa richiede $B \ge 2$ e cosa richiede $B \gg d$

Con $N$ campioni: la varianza campionaria richiede $N \ge 2$; la covarianza $d\times d$ ha rango $\le N-1$ (con $d=256$ e $N=128$ è singolare: va bene come regolarizzatore, non come stima); il rango effettivo (RankMe) su $N$ vettori è al più $\min(N, d)$; SIGReg ha senso a partire da qualche decina di campioni per direzione (LeJEPA stabile da $B=128$). Con $B=1$ **nessuna** di queste quantità esiste: la difesa (c) è matematicamente impossibile, non solo spenta.

### 3.7 RankMe: il rango effettivo

Per una matrice di embedding $Z \in \mathbb R^{N\times d}$ con valori singolari $\sigma_1,\dots,\sigma_{\min(N,d)}$, $p_i = \sigma_i / \sum_j \sigma_j$:

$$\mathrm{RankMe}(Z) = \exp\!\Big(-\sum_i p_i \log p_i\Big) \in [1, \min(N,d)] .$$

Vale 1 se tutti i punti sono allineati su una retta (collasso) e $\min(N,d)$ se le direzioni sono usate uniformemente. `nn/collapse_metrics.py:41-82` lo implementa correttamente, su embedding L2-normalizzati e **non centrati** — scelta giusta e ben motivata nel docstring (centrare sottrarrebbe la direzione media che il collasso produce).

### 3.8 Leakage: quando l'etichetta è una funzione dell'input

**In parole semplici.** Se chiedo a uno studente di indovinare un numero e la risposta è scritta sul foglio della domanda, lo studente imparerà a leggere il foglio, non la materia. Un test superato così non dice nulla.

**Nel dettaglio.** Se $y = h(x)$ è una funzione deterministica dell'input, il predittore Bayes-ottimo è $h$ stesso e un modello allenato su coppie $(x, h(x))$ impara a *re-implementare* $h$: l'accuratezza sul test è alta e non misura alcuna comprensione. `ConceptLabeler.label_tick` (`nn/jepa_model.py:601-733`) costruisce 16 etichette "soft" da soglie sulle stesse 25 feature date all'encoder: la testa dei concetti impara le soglie. Il path "outcome-based" `label_from_round_stats` (righe 735-861) usa esiti del round (kill, morti, trade, `round_won`) che *non* sono nell'input — corretto — ma inserisce `equipment_value` nelle etichette 5, 6 e 15 (righe 809-821, 856-858) mentre `equipment_value` è la feature 4 dell'input: leakage residuo su tre concetti su sedici. Inoltre le etichette sono costanti per tutto il round (una `RoundStats` per finestra, D-14): il massimo che la testa può imparare è l'esito del round dalla finestra, che è una *probe*, non un "concetto di coaching".

Test di leakage da adottare: (i) *permutazione*: allenare la probe con etichette prese da un altro round dello stesso giocatore — l'accuratezza deve crollare a caso; (ii) *ablazione dell'input*: rimuovere la feature 4 — la predicibilità delle etichette 5/6/15 non deve cambiare se non c'è leakage.

### 3.9 Mixture of Experts: bilanciamento vs entropia

Con $E$ esperti, $p_i$ probabilità di routing e, sul batch, $f_i$ = frazione di campioni instradati all'esperto $i$ e $P_i$ = media delle $p_i$, la loss ausiliaria di Switch Transformer (2101.03961) è

$$\mathcal L_{\text{aux}} = \alpha\, E \sum_{i=1}^{E} f_i P_i ,$$

minima ($=\alpha$) quando l'uso è **uniforme** sul batch: impedisce che un esperto assorba tutto. L'entropia $H(p) = -\sum_i p_i \log p_i$ misura invece la *confidenza per campione*. Aggiungere $+c\,H(p)$ alla loss con $c > 0$ (`rap/model.py:201-205`, peso 1.0 in `rap/trainer.py:92`) **minimizza** l'entropia: spinge ogni $p$ verso un one-hot, e nulla impedisce che sia lo *stesso* one-hot per tutti i campioni. Con routing top-2 il secondo esperto riceve peso ≈ 0 e smette di ricevere gradiente: il MoE degenera a un solo esperto. Il docstring ("one expert dominates (desired)") confonde due cose distinte: la *specializzazione* richiede confidenza per campione **e** bilanciamento sul batch; la seconda manca del tutto. Nella JEPA il termine di Switch è calcolato correttamente (`nn/jepa_model.py:236-243`: `0.01 * E * (f_i * P_i).sum()`) ma consumato solo nel path di fine-tuning che non può girare (`nn/jepa_train.py:705-707`).

### 3.10 Bersagli categoriali: MSE su one-hot vs cross-entropy

Per un bersaglio a $K$ classi, il modello corretto emette logit $\ell \in \mathbb R^K$ e minimizza $-\log \mathrm{softmax}(\ell)_y$ (cross-entropy): è una *proper scoring rule*, produce probabilità calibrate, e il gradiente non si annulla per le classi rare. `rap/trainer.py:67` minimizza invece $\lVert \ell - e_y\rVert^2$ con $\ell$ lineare senza softmax ("least-squares classification"): consistente in teoria ma non calibrato, dominato dai nove zeri del one-hot, e chiamato `advice_probs` pur non essendo una distribuzione. Aggravante: la classe 1 (`ROLE_ROTATION`) non è mai prodotta dal labeler (`nn/training_orchestrator.py:1711-1773`: nessun `return self.ROLE_ROTATION`), quindi una delle dieci uscite è morta per costruzione; e il labeler stesso è un albero di decisione su `equipment_value`, distanze e visibilità (§3.8 di nuovo): la testa "strategia" impara a replicare `_classify_tactical_role`.

### 3.11 EMA: inizializzazione e ripresa

BYOL e I-JEPA inizializzano $\bar\theta_0 = \theta_0$. Il progetto istanzia due `JEPAEncoder` indipendenti (`nn/jepa_model.py:126-127`) e non copia mai i pesi. Dopo $k$ passi di ottimizzazione, $\bar\theta_k = m^k \bar\theta_0 + (1-m^k)\cdot(\text{media pesata dei } \theta)$: con $m = 0.996$ il residuo casuale si dimezza ogni ≈ 173 passi e vale ancora 1,8% dopo 1000 passi. Non è fatale, ma le prime centinaia di passi predicono rumore. Sul path di produzione, inoltre, `persistence.save_nn` salva solo `state_dict()` e non i contatori `_ema_step`/`_ema_total_steps` (REPR-01, documentato in `nn/training_orchestrator.py:163-169`): ogni ripresa riparte da $m=0.996$ ("riscaldamento" del target). Se si adotta SIGReg (§3.4) il target encoder e tutti questi problemi scompaiono.

### 3.12 Scheduler, precisione mista, accumulo

Lo scheduler è avanzato **per epoca** (`nn/training_orchestrator.py:388-400`) con `T_max = max_epochs` e warmup del 5% delle epoche: coerente ma grossolano. La precisione mista ha due politiche: `JEPATrainer` usa autocast **fp16 + GradScaler** quando c'è CUDA (`nn/jepa_trainer.py:130-132`), mentre `config.amp_autocast()` usa **bf16 senza scaler** e documenta bf16 come l'unico path veloce sul wheel ROCm gfx1201 (`nn/config.py:165-176`); il CLI usa bf16. Non è un errore matematico ma una doppia politica da unificare (bf16).

---

## 4. Diagnosi della JEPA, errore per errore

Ordine: prima i due errori che da soli rendono inutile l'allenamento (J1, J2), poi quelli che fanno imparare la cosa sbagliata o falliscono in silenzio, poi le pulizie.

### J1 · Batch di una sola finestra — BLOCCANTE

**Evidenza.**
- `nn/training_orchestrator.py:859-866`: `context = features_tensor[:10].unsqueeze(0)` → forma `(1, 10, 25)`; `target = features_tensor[10:11].unsqueeze(0)` → `(1, 1, 25)`.
- `nn/training_orchestrator.py:644-652`: `window_len = 11`, `n_windows = sample_size // 11` (con `TRAIN_SAMPLES=50000` → 4545 finestre); ogni finestra è un elemento della lista `batches` iterata da `_run_epoch` (`:772-781`) → **un forward per finestra**.
- `nn/jepa_trainer.py:271-275`, commento del codice: *"at the production batch shape (B=1 …) vicreg_regularization returns 0.0, so the anti-collapse term is INERT on the orchestrated path"*.
- `nn/jepa_trainer.py:351-352`: `_log_embedding_diversity` ritorna `None` per `B<2`.

**Perché è sbagliato.** §3.6: con $N=1$ varianza, covarianza, rango effettivo e ogni regolarizzatore distribuzionale sono indefiniti. Non è una scelta di iperparametro: è l'assenza della quantità matematica su cui si basa tutta la difesa (c) contro il collasso.

**Conseguenza.** (i) VICReg vale 0 su ogni passo; (ii) il rilevatore di collasso ripiega su una quantità diversa (J10); (iii) niente negativi in-batch; (iv) la GPU esegue 4545 forward di tensori `(1,10,25)` per epoca: tempo dominato dal loop Python e dal fetch SQLite, non dal calcolo. Il progetto stesso ha già documentato la diagnosi ("Phase B: windows stacked into true (N, ctx, feat) batches") senza mai eseguirla.

**Correzione.** Un `Dataset`/collate che impila le finestre in tensori `(B, T, D)` con `B = 128` (LeJEPA: stabile da 128; il nostro modello è piccolo, 256 è fattibile in bf16 sulla RX 9070 XT). Rimuovere il loop "una finestra per batch". Da qui in avanti tutte le statistiche di batch esistono.

**Test.** `tests/test_jepa_collapse_feed.py::test_single_window_batch_is_unmeasurable_not_collapsed` e `::test_within_batch_variance_still_takes_precedence` diventano obsoleti (il caso B=1 deve alzare un errore, non essere "non misurabile"); `test_training_orchestrator_flows.py` — i test sulle forme `(1,10,25)` vanno riscritti su `(B,T,D)`.

### J2 · Orizzonte di un tick: il bersaglio è quasi l'identità — BLOCCANTE

**Evidenza.**
- `nn/training_orchestrator.py:45`: `_JEPA_CONTEXT_LEN = 10`; `:864-866`: il bersaglio è il tick immediatamente successivo al contesto (commento V-1: *"target is the tick immediately AFTER the context window"*).
- `docs/doctrine/notes/16-papers.md:94-96` (nota dell'autore): *"the current JEPA predicts one fixed horizon (context 10 → next tick)"*.
- Loss registrate: validazione ≈ 1.90–1.97 con finestre casuali non contigue (`docs/jepa_training_tuning_observations_2026-05-06.md`), poi `best_val_loss = 0.004024` dopo la correzione R4 delle finestre contigue (`models/global/archive_pre_rebuild_2026-09-01/jepa_brain.pt.meta.json`).

**Perché è sbagliato.** §3.5: a 64 tick/s il bersaglio differisce dal contesto per $\lesssim 10^{-3}$ nella norma delle feature normalizzate; il predittore identità azzera la loss per qualsiasi encoder liscio. Con InfoNCE il positivo è banalmente vicino e i negativi (altre partite) banalmente lontani.

**Conseguenza.** L'encoder è premiato solo per la *levigatezza* (feature lente), non per la struttura tattica; il salto della loss da "a caso" a "quasi zero" dopo R4 è la firma di un compito diventato banale. Nessuna metrica di utilità (probe, RankMe) è mai stata misurata su questi checkpoint, quindi non c'è alcuna prova che rappresentino qualcosa.

**Correzione.** Token da 8 tick (125 ms a 64 Hz; `P = round(tick_rate/8)` così il token dura 125 ms anche a 128 Hz, in linea con 26-NORM-01), costruiti con una conv1d a passo 8 (tutti i tick entrano nel token: nessuna decimazione, l'invariante "no tick decimation" resta rispettato). Finestre di 48 token (384 tick = 6 s). Obiettivo: predizione del token successivo per ogni posizione (LeNEPA, $T-1$ predizioni per finestra) più due orizzonti lunghi (+4 token = 0,5 s, +16 token = 2 s) con un predittore condizionato all'orizzonte (CF-JEPA/HEPA). Le finestre non attraversano mai il round (D-22 già in vigore).

**Test.** Nuovi test sul campionatore (orizzonti, nessun attraversamento di round, durata token invariante rispetto al tick rate); i test che asseriscono "target = tick 11" vanno rimossi.

### J3 · Encoder senza mixing temporale, poi media — GRAVE

**Evidenza.**
- `nn/jepa_model.py:46-53`: `nn.Sequential(Linear(25,512), LayerNorm, GELU, Dropout(0.1), Linear(512,256), LayerNorm)` applicato a `[B, T, 25]`: ogni tick è codificato indipendentemente dagli altri.
- `nn/jepa_model.py:201-202`: `s_context.mean(dim=1)` — media sui tick.
- `nn/jepa_model.py:35`: docstring *"Vision Transformer-style encoder"* — non c'è né attenzione né posizione.

**Perché è sbagliato.** Sia $\phi$ la mappa per-tick e $z = \frac1T\sum_t \phi(x_t)$: $z$ è una funzione *simmetrica* dei tick, quindi $f(x_{\pi(1)},\dots,x_{\pi(T)}) = f(x_1,\dots,x_T)$ per ogni permutazione $\pi$. L'encoder non può rappresentare ordine, verso del movimento, accelerazione, sequenza di eventi: vede un *sacchetto* di dieci stati.

**Conseguenza.** Anche con orizzonte corretto, la dinamica non è osservabile dal contesto. L'unico modulo sequenziale del modello (LSTM) sta nella testa mai allenata (J8).

**Correzione.** `TabularTokenizer` per tick (25 numerici + embedding delle categoriali → $d$) → conv1d a passo $P$ (token) → Transformer **causale** ($d=128$, 4 layer, 4 head, RMSNorm, SwiGLU, RoPE; ≈1 M parametri; LeNEPA XS usa $d=192$, 8 layer). Niente LSTM/GRU: su ROCm il progetto disabilita cuDNN/MIOpen (`nn/config.py:132`) e le RNN girano su kernel lenti, mentre il Transformer è solo matmul (veloce in bf16).

**Test.** Test di permutazione: mescolare l'ordine dei token deve cambiare l'output (oggi non lo cambia).

### J4 · InfoNCE con negativi banali e coda casuale — GRAVE

**Evidenza.**
- `nn/training_orchestrator.py:868-893`: 5 negativi (`_n_contrastive_negatives = 5`, `:97`) campionati da un pool di vettori **grezzi** a 25 dimensioni di altre finestre/partite (`_neg_pool`, ultimi 200); warm-up in-batch quando il pool è vuoto.
- `nn/jepa_trainer.py:207-212`: i negativi grezzi vengono codificati dal target encoder dopo espansione a `seq_len` copie identiche (no-op, J14).
- `nn/jepa_model.py:155-157`: coda MoCo di 4096 vettori **inizializzati casualmente** (`F.normalize(torch.randn(...))`); `nn/jepa_trainer.py:314-322`: 64 campionati a ogni passo → 69 negativi totali.
- `nn/jepa_trainer.py:266`: $\tau = \exp(\log\tau)$ appreso, clamp $[0.01, 1]$.
- Path CLI: `nn/jepa_train.py:449` chiama `jepa_contrastive_loss(pred, target, negatives)` senza $\tau$ → $\tau = 0.07$ fisso; negativi = altri bersagli del batch (`:445-446`); mai `enqueue` → la coda nei checkpoint CLI resta casuale.

**Perché è sbagliato.** §3.3(a): InfoNCE insegna solo se i negativi sono *difficili e veri*. Tick di partite diverse differiscono per `map_id`, posizione, economia: separarli è banale. Per il primo ~un'epoca (4096 finestre) 64 dei 69 negativi sono rumore gaussiano normalizzato. Con negativi facili, $\tau$ appreso tende ad affilare i logit e la loss precipita.

**Conseguenza.** Combinato con J2: loss ≈ 0 senza struttura. Inoltre l'apprendimento contrastivo ha bisogno di batch ≥ 256 per funzionare (SimCLR, MoCo): con B=1 non è un regime contrastivo in nessun senso pratico.

**Correzione.** Abbandonare InfoNCE come obiettivo di default. Obiettivo v2: MSE latente nello spazio del proiettore + SIGReg (§3.4). Tenere `jepa_contrastive_loss` solo per il baseline A/B (`JEPA_OBJECTIVE=legacy_infonce`).

**Test.** `tests/test_jepa_model.py::test_contrastive_loss` resta valido per il legacy; nuovi test di parità SIGReg (Appendice A.1) e di monotonia (gaussiana isotropa → statistica ≈ 0; nuvola collassata → statistica grande).

### J5 · VICReg inerte per costruzione — GRAVE (silenzioso)

**Evidenza.** `nn/jepa_model.py:440-441`: `if embeddings.shape[0] < 2: return torch.tensor(0.0)`; chiamato con peso `0.01` in `nn/jepa_trainer.py:274-275` e `:591`; commento del codice `:271-275` che ammette l'inerzia.

**Perché è sbagliato.** Non l'implementazione (corretta), ma il fatto che un termine anti-collasso possa valere 0 senza fermare il training: un guardrail che si disattiva in silenzio è peggio di nessun guardrail, perché il log dice "VICReg attivo".

**Conseguenza.** Il commento *"The contrastive loss fix (P1-03) resolved embedding collapse risk"* (`nn/jepa_model.py:8`) è falso sul path di produzione: la sola difesa reale è l'asimmetria EMA.

**Correzione.** Un regolarizzatore che riceve $N<2$ deve **alzare** `ValueError`, mai ritornare 0. Con la v2 il termine è SIGReg su $B\ge128$; VICReg può restare come opzione di confronto con l'asserzione.

**Test.** Nuovo test: `vicreg_regularization(x[:1])` deve alzare.

### J6 · Target encoder EMA: inizializzazione indipendente e ripresa impossibile — MEDIO

**Evidenza.** `nn/jepa_model.py:126-127` (due istanze indipendenti, nessuna copia dei pesi); `:401-405` (aggiornamento); `nn/jepa_trainer.py:179-191` (schedule coseno 0.996→1); `nn/training_orchestrator.py:163-169` (docstring: il path di produzione salva solo `state_dict`, i contatori REPR-01 esistono solo nel formato del CLI); `nn/jepa_trainer.py:147-153` (warning "REPR-01 … restarts at τ_base").

**Perché è sbagliato.** §3.11.

**Conseguenza.** Prime centinaia di passi con bersagli casuali; ogni ripresa "riscalda" il target. Non fatale, ma inutile e fonte di risultati non riproducibili tra run singolo e run ripreso.

**Correzione.** Con SIGReg il target encoder non serve: si rimuove (meno parametri, meno stato, nessun contatore da persistere). Se si volesse mantenere un baseline EMA: `target_encoder.load_state_dict(context_encoder.state_dict())` nel costruttore e contatori nel sidecar.

### J7 · Tre implementazioni divergenti dello stesso training — GRAVE (processo)

**Evidenza.**

| | CLI `nn/jepa_train.py` | `JEPATrainer.train_epoch` | Orchestratore (produzione) |
|---|---|---|---|
| Raggiungibile | sì (`--mode pretrain`) | **no** (`retrain_if_needed` `:520` è l'unico chiamante e non ha chiamanti) | sì |
| contesto / bersaglio | 10 / **10** tick (`:335`) | dal dataloader | 10 / **1** tick |
| batch | 16 finestre (`:474`) | richiede B≥2 (`:389-393`) | **1** finestra |
| negativi | 8 dai bersagli del batch (`:445`) | B−1 in-batch + 64 coda | 5 grezzi cross-match + 64 coda |
| τ | **0.07 fisso** (`:449`) | appreso | appreso |
| VICReg | assente | attivo | presente, = 0 |
| coda MoCo | mai riempita | sì | sì |
| ottimizzatore | solo `context_encoder` + `predictor` (`:361-365`) | tutti i parametri con grad | idem |
| precisione | bf16 (`amp_autocast`) | fp16 + GradScaler | fp16 + GradScaler |
| scheduler | `CosineAnnealingLR(T_max=epochs)` (`:371`) | warmup 5% → coseno | warmup 5% → coseno |
| early stopping | su **loss di training** (`:513, :579`) | — | su val loss |
| checkpoint | `save_jepa_model` (dict ricco, `:727-792`) | — | `save_nn` (solo `state_dict` + sidecar) |

Aggiunte: `JEPATrainingConfig` (`nn/training_config.py:50-65`) dichiara `context_window=10, prediction_window=10, contrastive_temperature=0.07, momentum_target=0.996` e **non è importata da nessun modulo JEPA**; `SelfSupervisedDataset` (`nn/dataset.py:25-63`) definisce un terzo schema di finestra (`prediction_len=5`) usato solo dal legacy `train.py`.

**Perché è sbagliato.** Un esperimento con tre definizioni della loss non è riproducibile né confrontabile; i test verdi su un path non dicono nulla degli altri.

**Correzione.** Un solo `Trainer`, una sola definizione di batch, configurazione come dati (JSON validato), un solo entry point (`run_full_training_cycle.py`). Il CLI di `jepa_train.py` viene ridotto a un wrapper sottile o rimosso.

### J8 · La testa di coaching non è mai stata allenata, ma è in ogni checkpoint — GRAVE

**Evidenza.**
- `nn/jepa_model.py:133-143`: `nn.LSTM(256,128, 2 layer)`, 3 esperti `Linear(128,128)→ReLU→Linear(128,10)`, gate `Linear(128,3)`; `:177-179` il commento dice "same as AdvancedCoachNN" ma manca il `LayerNorm` presente in `nn/model.py`.
- `nn/training_orchestrator.py:467-469`: `meta["head_trained"] = False` per ogni checkpoint jepa/vl-jepa (i run orchestrati sono solo pre-training).
- `nn/jepa_train.py:634-641`: `train_jepa_finetune` alza `ValueError` perché il contratto dei 10 bersagli non è definito (26-RANGE-01, TASKS#64).
- `coach/jepa_insight_adapter.py:180-228`: rifiuta checkpoint senza `head_trained=True`; `:276` legge `model.forward_coaching(x)` (la testa).
- `nn/jepa_model.py:236-243`: la loss ausiliaria Switch del MoE è calcolata a ogni forward ma consumata solo in `nn/jepa_train.py:705-707` (path che alza).

**Perché è sbagliato.** Parametri casuali (~100 k) serializzati come se fossero conoscenza; un adapter costruito attorno a un output che non esiste; una loss ausiliaria corretta collegata a niente.

**Conseguenza.** È il punto di rottura n. 2 del §2: il prodotto neurale non arriva mai al coach, e il gate F-0029 (giusto) lo garantisce.

**Correzione.** Separare la rappresentazione (encoder JEPA) dalle letture (teste). Le teste v2 sono *probe* (lineari o MLP a un layer) allenate su etichette esterne con l'encoder congelato (§7.7) e un *world model* (§7.8). L'adapter v2 consuma probe, sorpresa e momenti critici, non un vettore "di aggiustamento" a 10 dimensioni mai definito.

### J9 · VL-JEPA: etichette che leggono l'input e una loss incoerente con l'inferenza — GRAVE

**Evidenza.**
- `nn/jepa_model.py:601-733` `label_tick`: 16 etichette da soglie sulle stesse 25 feature (es. riga 662: `if crouching <= 0.5 and scoped <= 0.5 and enemies_vis > 0.4: labels[0] = ...`); warning NN-JM-03 nel docstring.
- `:735-861` `label_from_round_stats`: usa esiti del round, ma `equip` entra nelle etichette 5, 6 (`:809-821`) e 15 (`:856-858`) mentre `equipment_value` è la feature 4 in input.
- `:1085` loss BCE multi-label sui logit scalati; `:980` in inferenza `softmax(logits/τ)` — sedici sigmoidi indipendenti in training, una distribuzione che somma a 1 in inferenza.
- `nn/training_orchestrator.py:911-924`: una `RoundStats` per finestra (etichette costanti su tutto il round).

**Perché è sbagliato.** §3.8 (leakage totale per `label_tick`, parziale per il path outcome) e incoerenza train/serve: BCE tratta i concetti come indipendenti (più concetti attivi insieme, target che possono sommare a 3), il softmax li mette in competizione.

**Conseguenza.** La testa concetti è, nel caso migliore, una probe dell'esito del round; nel caso peggiore una copia di `label_tick`. I "top concepts" mostrati sono probabilità di una distribuzione che il training non ha mai ottimizzato.

**Correzione.** Rimuovere `ConceptLabeler.label_tick` dal training; la tassonomia dei 16 concetti resta come *nomi di probe* allenate su etichette esterne (RoundStats, eventi, annotazioni) con `LeakageGuard` (nessuna feature d'input tra le sorgenti delle etichette; test di permutazione e ablazione §3.8); scoperta non supervisionata dei "tipi di situazione" via k-means sui latenti come complemento onesto.

**Test.** `tests/test_jepa_model.py::test_positioning_exposed`, `::test_economy_wasteful_pistol_round`, `::test_trade_isolated_low_kast`, `::test_label_batch_*` codificano il leakage: vanno rimossi o spostati in un test "legacy". Nuovi: permutation test, ablation test.

### J10 · Rilevatore di collasso su una grandezza diversa da quella tarata — MEDIO

**Evidenza.** `nn/training_orchestrator.py:340-377`: quando nessun batch può misurare la varianza (sempre, con B=1), si usa la varianza **tra finestre** dei `pred_embedding_pooled`; il commento `:350-353` ammette: *"the 0.01 threshold was tuned for within-batch variance; cross-window variance is a different unit — re-validate"*. `nn/early_stopping.py:57-97`: soglia 0.01, pazienza 2.

**Perché è sbagliato.** La varianza di embedding non normalizzati dipende dalla scala d'uscita del predittore (ultimo `Linear` senza normalizzazione, `nn/jepa_model.py:83`): un fattore di scala cambia il verdetto senza cambiare la geometria.

**Correzione.** Usare `collapse_metrics.py` (già corretto: L2-normalizzazione, RankMe non centrato) su un probe batch fisso di ≥1024 finestre, con soglie di abort: `effective_rank < 8` oppure `std_min < 1e-3` per 2 epoche consecutive; più il valore di SIGReg (che misura la forma della distribuzione direttamente). `EmbeddingCollapseDetector` resta come gate, alimentato da queste quantità.

### J11 · Loss di validazione non confrontabile e, in ogni caso, non informativa — MEDIO

**Evidenza.** `nn/training_orchestrator.py:704-725`: la validazione usa i 5 negativi grezzi (senza coda) e $\tau$ appreso (D-18); il training usa 69 negativi. Il commento chiama l'asimmetria "acceptable". Early stopping e scelta del best checkpoint (`:418-436`) si basano su questa loss.

**Perché è sbagliato.** Due InfoNCE con $N$ diversi hanno livelli "a caso" diversi ($\log 6$ vs $\log 70$); e per J2 entrambe tendono a zero indipendentemente dalla qualità. Un checkpoint selezionato su questa loss è selezionato a caso.

**Correzione.** Selezione del modello su metriche di utilità: RankMe, probe lineari su etichette esterne (AUROC di `round_won` a livello di episodio, di "morte entro 2 s", di "nemico visibile entro 2 s"), $R^2$ della previsione di Δpos; la loss SIGReg+MSE resta come segnale secondario (LeJEPA: correlata alla probe).

### J12 · Codice morto e configurazione fantasma — MINORE

`forward_selective` (`nn/jepa_model.py:291-350`, nessun chiamante di produzione); `JEPATrainer.train_epoch`, `check_val_drift`, `retrain_if_needed` (`nn/jepa_trainer.py:362-528`, nessun chiamante); `JEPATrainingConfig` (mai importata); `SelfSupervisedDataset` (solo legacy `train.py`); `_jepa_negative_indices` (solo CLI). Da rimuovere o spostare in `legacy/` con un test che verifichi che non siano importati da nessun path attivo.

### J13 · Due politiche di precisione mista — MINORE

§3.12: fp16+GradScaler (`nn/jepa_trainer.py:130-132`) contro bf16 senza scaler (`nn/config.py:165-176`, usato dal CLI). Unificare su bf16 (documentato come unico path veloce sul wheel gfx1201; esponente fp32, niente scaler).

### J14 · Espansione ×10 dei negativi: un no-op costoso — MINORE

`nn/jepa_trainer.py:207-212`: `negatives.reshape(b*n,1,d).expand(-1, seq_len, -1)` poi `target_encoder(...).mean(dim=1)`. Poiché l'encoder è position-wise (J3), codificare dieci copie identiche e mediarle equivale a codificare il vettore una volta. Irrilevante dopo J4.

### J15 · Augmentation tabulare: rumore, non vista — MINORE

`nn/jepa_trainer.py:301-308`: `x * Bernoulli(0.7) + N(0, 0.03²)` sul contesto. Le componenti "mascherate" non vengono azzerate ma sostituite da rumore gaussiano; su feature binarie e su un orizzonte di un tick, questa è l'unica cosa che rende il compito non banale, ma è rumore casuale, non una vista semanticamente coerente. La ricetta v2 (LeNEPA) non usa augmentation.

---

## 5. Diagnosi del RAP coach, errore per errore

Premessa di lettura: `nn/rap_coach/` contiene dieci file che sono soltanto re-export di `nn/experimental/rap_coach/` (P9-01); tutto il codice vero sta in `rap/`. Il nome "RAP" è espanso in due modi diversi nei documenti ("Reasoning, Attention, Planning" in `jepa.md`; "Reasoning/Adaptation/Pedagogy" in `REFERENCE.md`): nel codice non c'è nulla che ragioni o pianifichi, quindi il nome va inteso come etichetta dello stack, non come descrizione.

### R1 · Il RAP non consuma la JEPA — GRAVE (architetturale)

**Evidenza.** `rap/model.py:81-90`: `forward(view_frame, map_frame, motion_diff, metadata, ...)` — pixel sintetici e i 25 numeri grezzi, nessun embedding in ingresso; nessun `import` da `jepa_model`. `run_full_training_cycle.py:242-247`: l'oggetto JEPA è distrutto prima della fase RAP. `nn/factory.py:52-83`: costruttori indipendenti; `nn/training_orchestrator.py:117-140`: due rami mutuamente esclusivi.

**Perché è sbagliato.** L'intera premessa del progetto (`jepa.md` §1.2) è che la JEPA fornisca la rappresentazione e il coach la usi. Il RAP reimpara una rappresentazione da zero, da input peggiori (raster 64×64 costruiti a mano), con meno dati e più parametri.

**Correzione.** Le teste del coach (strategia, valore, memoria, attribuzione) si montano **sopra i latenti JEPA** (§7.8). È così che i pezzi restano insieme: la JEPA diventa il "reparto percezione" del RAP.

### R2 · Mai completato un run validato — BLOCCANTE per il prodotto

**Evidenza.** `core/config.py:240`: `"USE_RAP_MODEL": False`; `nn/training_orchestrator.py:128-132`: il costruttore alza `ValueError` se il flag è falso; `nn/inference/ghost_engine.py:43-47`: motore disabilitato; `nn/coach_manager.py` overlay: `status: "disabled"`. Dipendenze: `rap/memory.py:11-21, 34-38` (`ncps`, `hflayers` obbligatori, altrimenti `ImportError`); `requirements-rap.in`: `hopfield-layers @ git+https://github.com/ml-jku/hopfield-layers.git@f56f929c…` (non su PyPI). Checkpoint: `models/global/archive_pre_rebuild_2026-09-01/rap_coach.pt` e `rap_coach_latest.pt` entrambi del 2026-08-03 20:42 (una sola scrittura), sidecar **senza** `extra.best_val_loss` (a differenza di `jepa_brain.pt.meta.json`). `TASKS.md` e la memoria di sessione confermano: la "Phase 2 RAP" non ha mai attraversato un ciclo con early stopping.

**Conseguenza.** Tutto ciò che dipende dal RAP — Ghost, overlay, Chronovisor — è inattivo. Non è una questione di bug singolo: è un ramo intero mai esercitato end-to-end.

### R3 · Testa "strategia": MSE su one-hot, una classe irraggiungibile, etichette euristiche — GRAVE

**Evidenza.** `rap/trainer.py:33` `criterion_strat = nn.MSELoss()`, `:67` applicata a `advice_probs` vs `target_strat`; `nn/training_orchestrator.py:1247-1250`: one-hot a 10 classi da `_classify_tactical_role`; `:1711-1773`: l'albero di decisione non restituisce mai `ROLE_ROTATION` (indice 1; `grep` conferma: l'unico riferimento al di fuori della costante è in un test); `rap/strategy.py:94`: uscita lineare senza softmax, ma chiamata `advice_probs` in `rap/model.py:167`; `rap/communication.py:109-112`: `argmax` su quell'uscita.

**Perché è sbagliato.** §3.10. Inoltre le etichette sono funzione dello stato (`equipment_value < 1500 → SAVE`, distanze, visibilità): la testa impara a replicare il labeler (§3.8).

**Correzione.** Cross-entropy sui logit; classi con almeno un esempio (definire "rotazione" da uno spostamento verso l'altro sito, oppure rimuovere la classe); e, onestamente, trattare questa testa come *probe di replica dell'euristica* (utile per verificare che il latente contenga l'informazione), non come "strategia appresa". La strategia appresa vera viene dal world model (§7.8).

### R4 · Loss del MoE con il segno sbagliato — GRAVE

**Evidenza.** `rap/model.py:201-205`: `entropy = -(p log p).sum().mean(); return weight * entropy` (minimizzata); `rap/trainer.py:80, 92`: peso `LOSS_WEIGHT_SPARSITY = 1.0`; docstring `:184-187`: *"Low entropy (peaked) -> small loss -> one expert dominates (desired)"*.

**Perché è sbagliato.** §3.9: minimizzare l'entropia spinge tutti i campioni verso lo *stesso* esperto; il bilanciamento (Switch) manca. Il commento RAP-AUDIT-04 corregge giustamente il precedente L1 costante, ma sostituisce un termine inutile con uno dannoso.

**Correzione.** Rimuovere il termine di entropia; aggiungere $\mathcal L_{\text{aux}} = \alpha E \sum_i f_i P_i$ con $\alpha = 0.01$ (già implementato correttamente in `nn/jepa_model.py:236-243`: riusarlo).

### R5 · Valore (critic) allenato su una formula dello stato — MEDIO

**Evidenza.** `nn/training_orchestrator.py:1651-1709` `_compute_advantage`: $0.4\cdot\text{alive} + 0.2\cdot\text{hp} + 0.2\cdot\text{equip} + 0.2\cdot\text{bomb}$ dai giocatori vivi al tick; `rap/trainer.py:69-77`: MSE mascherata (`val_mask`, LEAK-01: giusto non usare `round_outcome` per tick).

**Perché è sbagliato.** Il bersaglio è una funzione deterministica dello stato completo del tick; il modello vede (parzialmente) lo stesso stato: impara la formula, non il valore atteso dell'esito. Un "critic" in senso RL stima $\mathbb E[\text{ritorno}\mid s]$: qui il ritorno non c'è.

**Correzione.** Due bersagli: (a) tenere l'euristica come ausiliario esplicitamente etichettato "advantage-heuristic"; (b) aggiungere il valore da esito reale: $V(s_t) = \mathbb E[\,\gamma^{T_{\text{end}}-t}\cdot \mathbb 1[\text{round\_won}]\,]$ con sconto sul tempo residuo, calcolato **solo** dopo la fine del round (nessun leakage: è il target di regressione classico del value learning, e la maschera LEAK-01 resta per i tick senza informazione di squadra). Il "gap di coaching" $A_t = \text{esito} - V(s_t)$ ha senso solo con (b).

### R6 · Memoria: Hopfield che non scrive, LTC fragile, Lite che ignora il tempo — MEDIO

**Evidenza.** `rap/memory.py:115-121`: `HopfieldLayer(quantity=32, trainable=True)` — 32 prototipi aggiornati **solo** da backprop; nessuna scrittura a runtime; `:161-164` bypass fino al primo passo di ottimizzazione; `:196-242` `initialize_prototypes` (k-means) senza chiamanti (ammesso dal commento `:176`); `:244-265` `_hopfield_trained` è un booleano Python non nel `state_dict`, ricostruito con un'euristica al caricamento; `:52-93` LTC via `ncps` con monkey-patch di un bug upstream (`_ode_solver` broadcast) e wiring `AutoNCP` seedato (non riproducibile fuori da Python); `:300` `RAPMemoryLite` ignora `timespans` pur dichiarandosi drop-in.

**Perché è sbagliato.** Una "memoria" che non può ricordare nulla di ciò che vede a inferenza non è una memoria episodica: è uno strato di attenzione su 32 pesi. L'idea (prototipi di round, recupero associativo) è buona; l'oggetto sbagliato.

**Correzione.** Memoria episodica esplicita (§7.8): coppie (latente, contesto, esito) scritte a runtime quando la *sorpresa* del world model supera una soglia; recupero kNN; i 32 "prototipi" possono restare come centroidi k-means dei latenti (l'idea di `initialize_prototypes`, finalmente chiamata) in sola lettura.

### R7 · Percezione: uno stack che non è un ResNet e fallback che il codice stesso sconsiglia — MEDIO

**Evidenza.** `rap/perception.py:78-84` `_make_resnet_stack`: un blocco a passo 2 seguito da `sum(num_blocks)-1` blocchi identici a larghezza costante (per `[1,2,2,1]`: 6 blocchi a 64 canali, il commento `:55` dice 5); niente raddoppio dei canali, niente stadi. `BatchNorm2d` (`:20, :25`) con batch piccoli. `proc/tensor_factory.py:173-224`: in modalità legacy il canale "nemici" è strutturalmente vuoto perché le righe del monolite non hanno `team` (warning `:178-191`); `:605-630` il motion legacy è tre scalari replicati su tutta la griglia (solo quando manca la metadata mappa).

Nota di correttezza verso `jepa.md` §5.2: l'affermazione che il canale "danger" sia *sempre zero* è **superata** — oggi la modalità legacy calcola la zona di pericolo dal FOV accumulato (`:273-284`) e la modalità POV ha canali reali (entità visibili, utility). Il problema attuale non è il vuoto, è che il ramo CNN duplica il lavoro della JEPA (R1) su un input più povero.

**Correzione.** Rinviare la percezione visiva a dopo la v2 tabulare. Quando servirà (es. per la lettura della mappa), entrerà come **secondo flusso di token** nel Transformer, non come rete separata. `PlayerKnowledge` (modello di osservabilità parziale) resta: è la parte di valore.

### R8 · Attribuzione: tre concetti collineari, uno sempre zero, uno spurio — GRAVE per la pedagogia

**Evidenza.** `rap/pedagogy.py:78-82`: `[Positioning, Aim, Aggression, Utility, Rotation] = [‖Δpos‖, ‖Δview‖, 0.5·‖Δpos‖, σ(mean(h)), 0.8·‖Δpos‖]`; `rap/model.py:164`: `diagnose(last_hidden, optimal_pos)` senza `optimal_view_delta` → `aim_delta = 0` sempre (`:70-72`); `skill_vec` non è mai passato da nessun chiamante (`rap/trainer.py:56-62`, `ghost_engine.py:189-191`, `chronovisor_scanner.py:240-245`, overlay) → `skill_adapter = Linear(10,256)` non riceve mai gradiente; `_detect_utility_need = sigmoid(mean(hidden))` (`:88-98`, il docstring lo definisce un segnaposto).

**Perché è sbagliato.** Tre delle cinque uscite sono la stessa quantità moltiplicata per costanti (informazione identica), una è identicamente nulla, la quinta è una funzione arbitraria del latente. Moltiplicare per `relevance_head` (sigmoide) non aggiunge informazione indipendente sulle prime tre.

**Correzione.** Attribuzione controfattuale (§7.8): perturbare un campo o un'azione, ricodificare/rollout, misurare il Δ della probe o del valore; e gradienti delle probe rispetto ai campi via lo schema. I cinque nomi restano come tassonomia di uscita.

### R9 · Comunicazione: confidenza costante e mappa dei topic arbitraria — GRAVE (onestà del prodotto)

**Evidenza.** `Programma_CS2_RENAN/run_ingestion.py:225`: `comm.generate_advice(out["advice_probs"], confidence=0.85, skill_level=skill_level)` — l'unico chiamante di produzione passa una **costante**; `rap/communication.py:86`: soglia 0.7 (sempre superata); `:121-123`: `{score} = 85%`, `recommendation = "conservative"` (0.85 > 0.8) sempre; `:109-112`: `topic = ["positioning","mechanics","strategy"][argmax % 3]` — un indice di *ruolo tattico* (10 classi) mappato per modulo su 3 argomenti (ruolo 0 site_take → positioning, 1 rotation → mechanics, 2 entry_frag → strategy, 3 support → positioning…).

**Perché è sbagliato.** Ogni numero mostrato come "confidenza" è inventato; l'argomento del consiglio non ha relazione semantica con l'uscita del modello.

**Correzione.** Confidenza = probabilità calibrata di una probe (temperature scaling su un set di validazione; Appendice A.8); topic = argmax dell'attribuzione (§R8) su una tassonomia vera; il gate "silenzio sotto soglia" resta (è un'idea giusta) ma su una confidenza reale.

### R10 · Chronovisor: algoritmo sano, unità sbagliate, lisciamento mancante — MINORE

**Evidenza.** `rap/chronovisor_scanner.py:68-90`: scale in tick (64/192/640) con lag 16/64/128 — a 128 Hz durano la metà; `:15` promette Savitzky–Golay o media mobile, nessuno implementato; `:310-398` differenze a lag, raggruppamento a segno costante, picco; `:400-440` dedup tra scale; `:269-279` un valore per finestra keyed all'ultimo tick (corretto dopo R4).

**Correzione.** Scale in secondi convertite via tick rate; lisciamento Savitzky–Golay (finestra 5–9 punti, grado 2) prima delle differenze; soglie in unità di z-score calibrate sul train; **secondo segnale d'ingresso: la sorpresa del world model** (§7.8), oltre al valore. L'algoritmo resta.

### R11 · Tre regimi di finestra e un overlay che copia — MEDIO

**Evidenza.** Training: tensori 5D per-timestep `(B,32,3,64,64)` (`nn/training_orchestrator.py:1023-1041`). Chronovisor e overlay: `RAPStateReconstructor.reconstruct_belief_tensors` restituisce visivi 4D `(1,3,H,W)` + metadata `(1,32,25)` (`proc/state_reconstructor.py:103-119`) → `rap/model.py:115-118` espande **un frame** su 32 passi. Ghost: `T=1` (`ghost_engine.py:180-185`). `nn/coach_manager.py` overlay (`for tick in window:` con `outputs[...][0]` invariato): lo stesso `value`/`ghost_pos` assegnato a tutti i 32 tick della finestra.

**Correzione.** Un solo regime: token della JEPA v2 (§7.3), output per token.

### R12 · Observatory che legge attributi inesistenti — MEDIO

**Evidenza.** `nn/maturity_observatory.py:155`: `getattr(model, "_last_belief_batch", None)` — nessun modulo lo assegna (`grep` sull'intero pacchetto: zero scrittori); `:211`: `getattr(strategy, "superposition", None)` — `RAPStrategy` espone `experts[i]["super"]`, non `.superposition`; `:225`: `concept_embeddings` esiste solo su VL-JEPA. Il "conviction index" per un run RAP vale quindi $0.25(1-1.0) + 0 + 0 + 0.2\,\text{value\_acc} + 0.1\,\text{role\_stability}$: dominato dal miglioramento della val loss.

**Correzione.** I segnali si *registrano* esplicitamente (il modello espone `telemetry()` → dict), l'Observatory legge solo chiavi dichiarate e fallisce rumorosamente su chiavi assenti.

### R13 · Batch effettivo del RAP: tre finestre — GRAVE

**Evidenza.** `nn/coach_manager.py::_fetch_rap_windows` (riga 909) con `window_size=96` e `seq_len=32` produce tre finestre per batch; `rap/perception.py` usa `BatchNorm2d`.

**Perché è sbagliato.** Ogni statistica di batch (media, varianza della BatchNorm; VICReg) è stimata su $n=3$: la varianza campionaria ha coefficiente di variazione $\sqrt{2/(n-1)} = 1$ (Parte II Prop. 5 e App. A.4), cioè oscilla del 100% da batch a batch; le statistiche correnti della BatchNorm registrate per l'inferenza sono rumore.

**Correzione.** Nel coach v2 le norme sono RMSNorm/GroupNorm (nessuna statistica di batch); se il RAP resta allenabile per confronto, `n_windows ≥ 32` (Parte III §7.7).

---

## 6. Diagnosi del contratto dati e della pipeline

**In parole semplici.** Qui gli errori sono meno gravi e in parte già noti al progetto. Il tema comune: il numero **25** viene usato come se fosse un *tipo*. Due liste diverse di 25 nomi sono legate dallo stesso intero; una categoria (la mappa) è schiacciata in un numero senza significato; una colonna è sempre zero; alcune costanti del gioco sono scolpite nel codice invece che nella configurazione.

### D1 · Feature 16 (`kast_estimate`) è costante zero — MINORE

`proc/feature_engineering/vectorizer.py:360-363`: `get_val("kast", get_val("avg_kast", None))` — `PlayerTickState` non ha né `kast` né `avg_kast`, e DATA-01 (`nn/jepa_train.py:152-157`) ha giustamente vietato l'iniezione dell'aggregato di partita (leakage del futuro). Risultato: una dimensione su 25 non porta informazione. La rimozione è corretta; un'eventuale KAST per-round a posteriori è un'*etichetta*, non una feature.

### D2 · `map_id` = hash MD5 schiacciato in un ordinale — MEDIO

`vectorizer.py:366-369`: `(md5(map_name) % 10000) / 10000`. Un hash distrugge ogni struttura metrica: `de_dust2` e `de_mirage` finiscono a distanza arbitraria, e un MLP deve "memorizzare" quale valore corrisponde a quale mappa. Correzione: `map_id` come **indice categoriale** → `nn.Embedding(n_maps, 4)` nel tokenizer. Lo stesso per `weapon_class` (`:386-414`: ordinale 0/0.2/…/1.0 che impone un ordine knife<pistol<SMG<rifle<sniper<heavy privo di senso metrico) → embedding su 7 classi. `REFERENCE.md` dichiara l'indice 17 "immovabile" (Pillar III): la v2 versiona lo schema (§7.2) invece di congelare posizioni.

### D3 · `round_phase` è una funzione di `equipment_value` — MINORE

`vectorizer.py:371-381`: soglie 1500/3000/4000 su `equip_val` (feature 4). Ridondanza deterministica: nessuna informazione aggiunta, una dimensione sprecata. Rimuovere (o tenerla solo come etichetta di probe).

### D4 · Normalizzatori fuori da `HeuristicConfig` — MINORE

`vectorizer.py:430, 440, 445, 450`: `/115.0`, `/4.0`, `/5.0`, `/16000.0` come letterali, mentre le feature 0–14 leggono da `HeuristicConfig` (`base_features.py:34-45`). Portare tutto nello schema (§7.2) così il sidecar del checkpoint descrive **completamente** la normalizzazione.

### D5 · Due vocabolari da 25 legati dallo stesso intero — MEDIO

`nn/coach_manager.py` (righe 98-138 del file): `MATCH_AGGREGATE_FEATURES` (25 aggregati per partita: `avg_kills`, `rating`, …) con `if len(...) != METADATA_DIM: raise` — un vocabolario per-partita semanticamente estraneo al vettore per-tick, ma pinnato alla stessa dimensione; `nn/factory.py:44-100` passa `input_dim=METADATA_DIM` a modelli di entrambi i lati. È la radice del contratto indefinito di TASKS#64. Correzione: `FeatureSchema{id, version, fields}` con impronta (hash) nel sidecar; il vocabolario aggregato diventa uno schema separato.

### D6 · Stato globale mutabile nell'estrattore — MINORE (ma blocca il parallelismo)

`vectorizer.py:144-185`: contatori, `deque`, `threading.local`, flag "warned" a livello di modulo; `FeatureExtractor.configure()` di classe. Corretto per un singolo processo; impossibile da usare in `DataLoader` multi-worker senza sorprese e da portare altrove. Correzione: un oggetto `Extractor(schema, policy)` con stato proprio.

### D7 · Cinque entry point, due sequenze di fasi, documenti che contraddicono il codice — MEDIO

`run_full_training_cycle.py` (2 fasi) vs `coach_manager._execute_training_phases` (5 fasi); `train.sh` (header su gate di maturità che il suo path non chiama); `services/llm_service.py:4` e `services/lesson_generator.py:5` affermano che il RAP alimenta l'LLM — `lesson_generator.py:314-325` passa otto scalari da `PlayerMatchStats`. Correzione: un entry point, docstring corretti (fanno parte del passo 5 del piano).

### D8 · Nomi giocatore normalizzati in una tabella sola — MEDIO

**Evidenza (sola lettura, 2026-09-05).** `run_ingestion.py:797` normalizza `player_name` con `strip().lower()` per `roundstats`; il bulk insert di `playertickstate` (riga 1701) e `PlayerMatchStats` (riga 120) conservano la grafia originale (es. `' saffee'`, `Art`). 47 dei 105 nomi di `roundstats` non hanno corrispondenza esatta in `playermatchstats`; 18 delle 48 coppie campionate dalla verifica empirica non hanno restituito tick.

**Conseguenza.** Ogni join etichetta↔tick per uguaglianza esatta perde quasi metà dei giocatori: le sonde e le teste "evento" vedono metà dei dati.

**Correzione.** Una sola funzione di normalizzazione usata in scrittura e in ogni join; migrazione delle righe esistenti a ingestione ferma (Parte III §2.4).

### D9 · Nessuna riga in `TRAIN` — BLOCCANTE (operativo)

**Evidenza.** `SELECT dataset_split, COUNT(*) FROM playermatchstats GROUP BY 1` → `UNASSIGNED: 1031`. `assign_dataset_splits` (coach_manager.py:397) non è stata eseguita dopo la ri-ingestione del 2026-09-01.

**Correzione.** Eseguirla (a ingestione ferma) prima di qualunque training; far fallire il training se `train_rows == 0` (già rilevato da `data_quality.run_pre_training_quality_check`, che oggi restituirebbe FAIL).

### 6.1 Cosa nella pipeline dati è **giusto** e va tenuto

- **Split cronologico 70/15/15 tagliato tra demo, mai dentro** (`nn/coach_manager.py`, `temporal_assign`): corretto, con il bug del 2026-07-26 documentato e risolto; l'avviso OI-2 sull'`ingested_at` come data è onesto.
- **Finestre che non attraversano il round** (D-22, `_fetch_jepa_windows`): giusto; nella v2 diventa strutturale (episodio = round).
- **Contratto delle feature con assert a import, sidecar con `feature_names` e `StaleCheckpointError`**: da estendere con l'impronta dello schema, non da rimuovere.
- **Gate di qualità pre-training** (`nn/data_quality.py`: ≥1000 tick, ≤10% posizioni (0,0,0), split non vuoti) e **gate di eleggibilità** (shard completo, round minimi, aggregati non nulli).
- **`collapse_metrics.py`**: il modulo più pulito del pacchetto; si riusa così com'è.
- **`PlayerKnowledge`** (`proc/player_knowledge.py`): il modello di osservabilità parziale (FOV, udito, decadimento della memoria, occlusori) è l'idea più trasferibile del repo; nella v2 diventa la sorgente di feature/token aggiuntivi.
- **Shard per partita con id deterministico e migrazioni**; **scritture atomiche**; **registro hash dei checkpoint**.
- **Disciplina anti-leakage** (P-RSB-03, LEAK-01, DATA-01): giusta; la v2 la rende una regola verificata da test (`LeakageGuard`).

---

## 6b. Le altre reti e i motori di analisi — sintesi

**In parole semplici.** Oltre a JEPA e RAP, il progetto contiene quattro reti più piccole e una decina di "motori" statistici che producono numeri mostrati come probabilità o confidenze. Alcuni sono corretti (la testa dei ruoli, gli z-score rispetto ai pro, i monitor di drift). Altri hanno la forma di un modello ma non i contenuti: coefficienti scelti a mano, reti mai addestrate che girano con pesi casuali, alberi di ricerca su regole inventate, una "TrueSkill" che non è TrueSkill. La regola per distinguere è una sola: **un numero è una probabilità solo se è stato stimato dai dati e calibrato su un insieme di validazione**; tutto il resto è un punteggio, e va chiamato così.

**Nel dettaglio** (analisi completa, formula per formula, nella **Parte II §11**):

| Componente | Matematica implementata | Verdetto | Destino nella v2 |
|---|---|---|---|
| `AdvancedCoachNN` (`nn/model.py`, `train.py`) | MSE su bersaglio `clip((pro−cur)/scale)` = funzione dell'input | Leakage totale; LSTM su sequenza di lunghezza 1 | Ritirare; il delta è `calculate_deviations` (z-score) |
| `NeuralRoleHead` (`nn/role_head.py`) | KL su etichette soft esterne, statistiche di normalizzazione salvate | **Corretto** | Tenere; test di semantica delle feature; calibrare |
| `WinProbabilityTrainerNN` | BCE, 9 feature grezze non normalizzate | Mai addestrato, mal condizionato | Eliminare o unificare |
| `WinProbabilityNN` + euristiche + `PlattScaler` + Elo (`analysis/win_probability.py`) | sigmoide **casuale** (W-02) + clamp a mano; Platt dormiente; Elo standard | Non probabilistico | Sonda `round_won` sui latenti + Platt su VAL |
| `DeathProbabilityEstimator` (`analysis/belief_model.py`) | logit con coefficienti a mano (2; 1,5; −1; 1) | Non stimato; "MC dropout" improprio | Regressione logistica o sonda "morte entro Δt" |
| `ExpectiminimaxSearch`, `OpponentModel`, `BlindSpotDetector` | ricorsione corretta; transizioni a tabella; foglie da `WinProbabilityNN` | Argmax di rumore; azioni del giocatore non osservate | Ritirare dal coaching; world model + CEM |
| `EntropyAnalyzer` | Shannon su griglia adattata al bounding box | Non misura l'incertezza posizionale; $\Delta H_{max}$ > $\log_2 5$ | Griglia fissa per mappa o Δ-sorpresa |
| `MomentumTracker` | moltiplicatore a mano con decadimento | Non validato | Stimare su `roundstats` o etichettare "narrativo" |
| `DeceptionAnalyzer` | somma pesata 0,25/0,40/0,35 | Punteggio, non modello | Etichettare; validare pro vs amateur |
| `RoleClassifier` euristico | affinità normalizzate + consenso col neurale | Coerente; confidenze su scale diverse | Tenere |
| `HybridCoachingEngine` | z-score coorte pro; "confidenza" = 0,6·min(\|z\|/3,1)+0,4·uso | Statistica corretta; "confidenza" ordinale | Tenere; rinominare "priorità" |
| `ExperienceBank` (COPER) | coseno FAISS; EMA di efficacia; "TrueSkill" = μ EMA, σ·0,95 | Retrieval corretto; nomi fuorvianti | Beta-binomiale; memoria episodica su latenti |
| LLM (`llm_service.py`) | — | Nessun numero generato dall'LLM è affidabile | Renderer di strutture calcolate; modello pinnato |
| Drift, quality gate, `eval_harness` | z sulla differenza di medie; soglie; ECE, Brier | Corretti | Tenere ed estendere alla v2 |

---

## 7. L'architettura corretta: Macena Coach v2

**In parole semplici.** La v2 tiene la fabbrica di dati e cambia il cervello in quattro mosse: (1) gli dà un compito che richiede di capire il gioco (predire il futuro a mezzo secondo e a due secondi, non a quindici millesimi); (2) gli dà un modo matematicamente pulito per non collassare (SIGReg) al posto di cinque trucchi sovrapposti; (3) gli dà un encoder che vede l'ordine del tempo; (4) collega le "teste" del coach — strategia, valore, memoria, spiegazioni, consigli — **sopra** la rappresentazione appresa, così JEPA e RAP diventano un solo sistema. Il consiglio all'utente nasce da tre segnali del modello: quanto una situazione *sorprende* un modello allenato sui professionisti, cosa facevano i professionisti da situazioni simili, e cosa dicono le letture (probabilità di morire entro due secondi, di vincere il round…). L'LLM riceve questi fatti e li racconta.

### 7.1 Sette principi di progetto

1. **Predizione nello spazio latente + SIGReg.** Un termine di regolarizzazione, un iperparametro; niente target encoder EMA, niente negativi, niente stop-gradient, niente coda, niente temperatura appresa.
2. **Statistiche che esistono.** Batch ≥ 128 finestre; orizzonti in secondi; token da 125 ms.
3. **Encoder temporale causale.** L'ordine dei tick è informazione, non rumore da mediare.
4. **Rappresentazione e letture separate.** Encoder auto-supervisionato (senza etichette) + probe su etichette esterne (mai derivate dall'input) + world model condizionato alle azioni. La "testa di coaching" mai definita sparisce.
5. **La sorpresa come segnale unificante.** L'errore di predizione del world model allenato sui pro alimenta memoria episodica, momenti critici e stima di abilità.
6. **Schema dati tipizzato e versionato.** Un intero non è un tipo: campi con nome, tipo, unità, normalizzatore; impronta SHA-256 nel sidecar; categoriali come embedding.
7. **Fallire rumorosamente, misurare l'utilità.** Un solo trainer; nessun termine che ritorna 0 in silenzio; selezione del modello su RankMe e probe, non sulla loss.

### 7.2 Schema dati v2 (`cs2_v2`)

Dai 25 campi attuali: si tolgono `kast_estimate` (D1, sempre 0) e `round_phase` (D3, ridondante); `map_id` e `weapon_class` passano da ordinali a **categoriali**; si aggiunge `side` (CT/T) quando disponibile dallo shard/`PlayerKnowledge` (oggi non è nel vettore: F-0025 ha mostrato che `PlayerTickState` non ha la colonna `team`). Le normalizzazioni restano numericamente identiche a oggi ma vivono nello schema, non nel codice.

| Gruppo | Campi (21 numerici) | Normalizzatore (dati dello schema) |
|---|---|---|
| Vitali | `health`, `armor` | affine /100 |
| Equipaggiamento | `has_helmet`, `has_defuser`, `equipment_value` | binario; affine /10000 |
| Postura | `is_crouching`, `is_scoped`, `is_blinded` | binario |
| Consapevolezza | `enemies_visible` | affine /5, clip [0,1] |
| Posizione | `pos_x`, `pos_y`, `pos_z` | affine /4096, /4096, /1024, clip [−1,1] |
| Vista | `view_yaw_sin`, `view_yaw_cos`, `view_pitch` | ciclico (gradi); affine /90 |
| Spaziale | `z_penalty` | fornito dall'adapter (`compute_z_penalty`: distanza dal piano di taglio /500, mappe multilivello) |
| Round | `time_in_round`, `bomb_planted`, `teammates_alive`, `enemies_alive`, `team_economy` | /115, binario, /4, /5, /16000 |

| Categoriali (3) | Vocabolario | Embedding |
|---|---|---|
| `map_id` | nomi mappa visti in training + `unknown` | 4 dim |
| `weapon_class` | knife, pistol, smg, rifle, sniper, heavy, utility/other, unknown | 4 dim |
| `side` | CT, T, unknown | 2 dim |

Ingresso per tick al tokenizer: $21 + 4 + 4 + 2 = 31$ numeri. Lo schema è un JSON (`configs/schema_cs2_v2.json`) con `schema_id`, `version`, lista ordinata dei campi (`name, kind, unit, normalizer, valid_range, nullable`), e la sua impronta SHA-256 finisce nel sidecar di ogni checkpoint: caricare un checkpoint su uno schema diverso deve alzare `SchemaMismatchError` (evoluzione dello `StaleCheckpointError` attuale).

**Azioni** (per il world model; per token, aggregate sugli 8 tick): `Δpos_x, Δpos_y, Δpos_z` (unità di gioco / 32, clip [−1,1]: 8 tick × 3,9 u/tick ≈ 31 u massimi), `Δyaw` (gradi avvolti /180), `Δpitch` (/90). Sono le decisioni di movimento e mira del giocatore: esattamente ciò che un coach commenta. (Estensione futura: azioni discrete da eventi — sparo, lancio utility.)

**Etichette esterne** (per le probe; mai in input): per episodio `round_won`, `survived`, `kills`, `deaths`, `opening_kill`, `opening_death`, `kast` (binario per round), `round_rating`; per token `death_within_2s`, `enemy_visible_within_2s`, `damage_taken_within_2s`; euristiche di ruolo (`_classify_tactical_role`) tenute **solo** come etichette di probe, dichiarate tali.

### 7.3 Episodi, token, finestre, batch

- **Episodio** = tick contigui di `(demo, player, round)`, ≥ 64 tick; nessuna finestra attraversa un episodio (D-22 diventa strutturale).
- **Token** = $P$ tick con $P = \mathrm{round}(\text{tick\_rate}/8)$ (8 a 64 Hz, 16 a 128 Hz): durata 125 ms invariante rispetto al server (26-NORM-01). Costruito con `Conv1d(31, d, kernel=P, stride=P)`: ogni tick entra nel token, nessuna decimazione.
- **Finestra** = 48 token (6 s); inizio campionato a caso nell'episodio; per la validazione finestre fisse (seed fisso).
- **Batch** = 128 finestre → tensori `(128, 48, 31)` in ingresso, `(128, 48, d)` latenti.
- **Sorgente dati** = shard `safetensors` esportati una volta per split (passo 1 del piano), non query SQLite a ogni epoca: le COUNT sull'intero monolite costano ~25 minuti (`docs/jepa_training_tuning_observations_2026-05-06.md`) e il training documentato era I/O-bound.

### 7.4 Il modello JEPA v2

```
x  (B, 48·P, 31)  per-tick (numerici normalizzati ⊕ embedding categoriali)
 │  Tokenizer: Conv1d(31 → d=128, k=P, s=P)  →  (B, 48, 128)  + RoPE
 ▼
Encoder f_θ: 4 × TransformerBlock causale
   [RMSNorm → MHA(4 head, QK-norm, causale) → residuo → RMSNorm → SwiGLU(128→352→128) → residuo], dropout 0.1
   uscite: token z_t (B,48,128) ; tap ai layer {0, 2, 4} per SIGReg temporale e probe
 │
 ├─► Proiettore h_ψ: Linear(128,256) → LayerNorm → GELU → Linear(256,64)      (solo per la loss; scartato a inferenza)
 │
 └─► Predittore g_φ: 2 × TransformerBlock causale sui token z_{≤t}
         + condizionamento all'orizzonte h ∈ {1, 4, 16} via FiLM: z ← γ_h ⊙ z + β_h   (idea "Superposition" riusata)
         → ẑ_{t+h}  → h_ψ(ẑ_{t+h})
```

Parametri: tokenizer ≈ 32 k; 4 blocchi ≈ 0,8 M; proiettore ≈ 50 k; predittore ≈ 0,4 M → **≈ 1,3 M** (contro ~300 k della JEPA attuale e ~11 M del RAP). Niente LSTM/GRU (ROCm senza MIOpen), niente BatchNorm (statistiche di batch a inferenza = skew train/serve, già costato un run RAP).

### 7.5 L'obiettivo di training

$$\mathcal L = \underbrace{\frac{1}{B(T-1)}\sum_{b,t}\big\lVert h_\psi(\hat z^{(1)}_{b,t+1}) - h_\psi(z_{b,t+1})\big\rVert^2}_{\mathcal L_{\text{next}}}
\;+\; \beta \underbrace{\sum_{h\in\{4,16\}} \frac{1}{|\mathcal V_h|}\sum_{(b,t)\in\mathcal V_h}\big\lVert h_\psi(\hat z^{(h)}_{b,t+h}) - h_\psi(z_{b,t+h})\big\rVert^2}_{\mathcal L_{\text{multi}}}
\;+\; \lambda_T \underbrace{\frac{1}{B|\mathcal L_T|}\sum_{\ell\in\mathcal L_T}\sum_b \mathrm{SIGReg}\big(\{u^{(\ell)}_{b,t}\}_{t=1}^{T}\big)}_{\mathcal L_{\text{SIGReg, temporale}}}
\;+\; \lambda_B\, \mathrm{SIGReg}\big(\{h_\psi(z_{b,t})\}_{b=1}^{B}\big)_{\text{media su } t}$$

- Nessuno stop-gradient sui bersagli $z_{t+h}$ (LeNEPA, LeWM): la stabilità viene da SIGReg.
- $\mathcal L_T = \{0, 2\}$ (tap dopo il tokenizer e a metà encoder; LeNEPA usa {0, ultimo}); $\lambda_T = 2.5$ di default, sweep $\{1, 2.5, 5, 10, 20\}$; $\lambda_B = 0.1$ (LeWM) sulle proiezioni lungo il batch; $\beta = 0.5$.
- SIGReg: $M = 1024$ direzioni ricampionate a ogni passo con seme = `global_step` (riproducibile), 17 nodi su $[0,3]$ (Appendice A.1).
- Ottimizzatore: AdamW $(\beta_1,\beta_2)=(0.9, 0.99)$, lr $10^{-4} \to 10^{-6}$ coseno **per passo**, warmup 1000 passi, weight decay 0.05, clip della norma del gradiente 1.0, autocast **bf16** senza scaler, 20 000 passi (≈ 2,5 M finestre viste; a 128 finestre/passo il compute per passo è dell'ordine dei millisecondi: il collo di bottiglia è solo il caricamento dati).
- Modalità legacy per il confronto: `objective = "legacy_infonce"` riproduce J4 (InfoNCE + EMA + coda + VICReg) **con B = 128** — con B = 1 la ricetta attuale non è nemmeno definita.

### 7.6 Telemetria, selezione del modello, arresto

Ogni 500 passi, su un insieme fisso di 2048 finestre di validazione:

| Segnale | Definizione | Uso |
|---|---|---|
| `rankme_tokens`, `rankme_pooled` | RankMe (`collapse_metrics.py`) sui token del layer 2 e sulla media per finestra | collasso, ricchezza |
| `std_min` | deviazione standard minima per dimensione (L2-normalizzati) | collasso dimensionale |
| `sigreg_val` | statistica SIGReg sul set fisso | forma della distribuzione |
| `mse_next`, `mse_h4`, `mse_h16` | errori di predizione nello spazio del proiettore | apprendimento della dinamica |
| `probe_auroc_*` | probe lineari online (ingresso `detach()`, lr $10^{-3}$) su `round_won` (per episodio), `death_within_2s`, `enemy_visible_within_2s` (per token) | **utilità** — criterio primario |
| `dpos_r2_h4`, `dpos_r2_h16` | $R^2$ di una probe lineare che predice Δpos da $z_t$ | dinamica leggibile |

Regole: best checkpoint = massima media delle AUROC delle probe (la loss SIGReg+MSE è il criterio secondario; LeJEPA mostra che è correlata); early stopping con pazienza 10 valutazioni; **abort** se `rankme_pooled < 8` oppure `std_min < 10^{-3}` per 2 valutazioni consecutive (l'attuale `EmbeddingCollapseDetector` resta come gate, alimentato da queste quantità). Log in CSV/JSONL nel run dir; TensorBoard opzionale (l'infrastruttura di callback esistente si riusa).

### 7.7 Protocollo "battere il baseline" (definizione di successo del passo 4)

Stesse finestre per tutti (liste salvate: 40 k train / 8 k val / 8 k test, seme 0). Contendenti: **A** = ricetta di produzione riprodotta fedelmente in PyTorch ma con B = 128 (MLP position-wise + media, MLP predittore, EMA coseno, InfoNCE con τ appreso e coda, VICReg 0.01); **B** = ricetta v2. Metriche su encoder congelato: RankMe su 8 k finestre di test; AUROC delle probe lineari (`round_won`, `death_within_2s`, `enemy_visible_within_2s`); accuratezza kNN-20 sulle stesse etichette; $R^2$ Δpos a 0,5 s e 2 s. Terzo contendente obbligatorio, **R** = feature grezze (media di finestra, 25-d): la Parte II §12.5 misura che l'encoder archiviato è *sotto* R (AUROC 0,68 vs 0,76 su `round_won`; 0,74 vs 0,84 su morte entro 2 s). Superamento: **B ≥ A e B ≥ R su tutte le AUROC, e RankMe(B) ≥ 2·RankMe(A)**, media ± deviazione su 3 semi. Il rapporto va in `docs/benchmarks/jepa_v2_vs_legacy.md`.

### 7.8 Le letture: probe e tassonomia (sostituiscono la testa VL-JEPA e la testa "strategia" a MSE)

- **Probe** = `Linear(128, k)` o `Linear→GELU→Linear` su latenti congelati (token o media), allenate con cross-entropy/BCE su etichette esterne (§7.2), weight decay $10^{-4}$, 200 epoche.
- **`LeakageGuard`** (test automatico): l'insieme delle colonne sorgente di ogni etichetta ∩ l'insieme dei campi dello schema deve essere vuoto; test di permutazione (etichette di un altro round → AUROC ≈ 0.5) e di ablazione (§3.8) nel CI.
- **I 16 concetti** restano come *nomi*: quelli con un'etichetta esterna disponibile (`trade_responsive` ← `trade_kills`; `positioning_exposed` ← `opening_death`/morte entro 2 s; `economy_*` ← `round_won` × classe di spesa; …) diventano probe; gli altri si scoprono senza supervisione con k-means ($k=32$) sui latenti — il ruolo che `initialize_prototypes` avrebbe voluto avere.
- **Calibrazione**: temperature scaling per ogni probe sul set di validazione (Appendice A.8) → la "confidenza" mostrata all'utente è una probabilità calibrata, mai una costante.

### 7.9 Il coach v2 sopra i latenti (il RAP rinato)

```
                 ┌──────────────────────────── latenti JEPA z_t (congelati, o fine-tune a lr×0.1) ────────────────────────────┐
                 │                                                                                                              │
   (a) World model  g_a(z_≤t, a_≤t)  → ẑ_{t+1..t+k}      (b) Sorpresa  ε_t = ‖h(ẑ_t) − h(z_t)‖² → z-score       (c) Probe calibrate
        │  AdaLN-zero su embedding azione ⊕ Δt                  │                                                     │
        ▼                                                       ▼                                                     ▼
   (d) Ghost = planner CEM sulle azioni       (e) Memoria episodica (kNN)      (f) Chronovisor v2 (valore + sorpresa)   (g) Valore: euristico + esito scontato
        │  costo = ‖ẑ_H − z_goal‖²,                 scrive se ε_t > τ_w,               secondi, Savitzky–Golay, z-soglie
        │  z_goal da (e): situazioni pro simili     legge i riferimenti pro
        ▼
   (h) Attribuzione controfattuale  (campo/azione → Δ probe, Δ valore, Δ sorpresa)
        ▼
   (i) Comunicazione: template per livello di abilità · confidenza = probe calibrata · topic = attribuzione · JSON strutturato → LLM (Ollama)
```

(a) **World model.** Stesso predittore di §7.4 con condizionamento **AdaLN-zero** (LeWorldModel: `c = MLP(a_emb ⊕ Δt)` → shift/scale/gate per blocco, ultimo `Linear` inizializzato a zero) sulle azioni $a_t$ a 5 dimensioni. Loss: $\mathcal L_{\text{next}} + 0.1\cdot\mathrm{SIGReg}$ su transizioni campionate (`TransitionSampler`), rollout di $k = 8$ token (1 s) durante il training con loss su ogni passo. È la testa "posizione ottimale" del RAP fatta bene: predice la *dinamica* dato ciò che il giocatore fa, non uno spostamento fisso ×500.

(b) **Sorpresa.** $\varepsilon_t$ z-scorato con statistiche running (Welford) per flusso; calcolato con il world model **allenato sui pro**: alta sorpresa = "un modello del gioco professionistico non si aspettava questa evoluzione" = candidato momento didattico o anomalia (paper 2606.28383, già nella biblioteca del progetto: la "surprise channel" è anche nella roadmap di `16-papers.md`).

(c) **Probe** di §7.8.

(d) **Ghost.** Cross-Entropy Method (LeWM): 300 sequenze di azioni campionate, 10 iterazioni (30 nei casi difficili), 30 élite, orizzonte 8 token; costo terminale $\lVert \hat z_H - z_{\text{goal}}\rVert^2$; $z_{\text{goal}}$ = latente a $+H$ delle situazioni pro più simili (recuperate da (e)). La traiettoria fantasma = integrazione delle azioni pianificate (Δpos → posizioni): sostituisce `optimal_pos × 500` con una quantità fisica.

(e) **Memoria episodica.** Indice dei latenti pro (token ogni 4 = 0,5 s; ≈ 4,6 M vettori per 147 M tick → 1,2 GB in bf16; con FAISS IVF-PQ, già dipendenza del repo per la RAG, molto meno), con metadati (episodio, tick, esiti, azioni successive). Lettura kNN (cosine) → "cosa hanno fatto i pro da qui". Scrittura a runtime delle situazioni dell'utente con $\varepsilon_t > \tau_w$ (personalizzazione). I 32 prototipi Hopfield → centroidi k-means in sola lettura (facoltativi).

(f) **Chronovisor v2.** L'algoritmo attuale (differenze a lag, raggruppamento, dedup tra scale) con: scale in secondi (1 s / 3 s / 10 s; lag 0,25 / 1 / 2 s) convertite via tick rate; lisciamento Savitzky–Golay (finestra 7, grado 2); soglie in z-score calibrate sul train; **due segnali**: valore (g) e sorpresa (b). Uscita `CriticalMoment{t_peak, t_start, t_end, severità, polarità, scala, segnale}`.

(g) **Valore.** Due teste lineari su $z_t$: `advantage_heuristic` (l'attuale formula, come ausiliario dichiarato) e `value_outcome` = $\gamma^{(T_{\text{end}}-t)/\text{rate}}\cdot\mathbb 1[\text{round\_won}]$ con $\gamma$ per secondo = 0,97, calcolato a fine round (nessun leakage nel *training*: è un target di regressione classico); maschera LEAK-01 mantenuta dove manca l'informazione di squadra.

(h) **Attribuzione controfattuale.** Per ogni campo $f$: sostituirlo con la mediana dell'episodio nella finestra, ricodificare, misurare Δ delle probe/della sorpresa; per le azioni: sostituire quella del giocatore con quella del planner, misurare Δ del valore predetto. La classifica dei Δ è il "perché" — indipendente per costruzione, a differenza delle tre copie scalate di ‖Δpos‖.

(i) **Comunicazione.** `TemplateRenderer` per livello di abilità (i tre livelli attuali e `SkillLatentModel` si tengono), `confidence` = probabilità calibrata della probe che sostiene il consiglio, `topic` = campo/azione in testa all'attribuzione, silenzio sotto soglia (idea giusta, finalmente su un numero vero). L'LLM (Ollama, modello pinnato) riceve un JSON strutturato: momenti critici, attribuzione, ghost, Δ delle probe rispetto ai pro, riferimenti pro recuperati — con nomi giocatore hashati. È la prima volta che il testo del coach discende da un output neurale.

(j) **Observatory v2.** Il modello espone `telemetry()` (dict con chiavi dichiarate: RankMe, SIGReg, AUROC probe, statistiche di sorpresa, dimensione memoria); l'Observatory legge solo quelle chiavi e fallisce su chiavi assenti. Il "conviction index" si ridefinisce su segnali che esistono.

**Cosa del RAP resta come idea:** FiLM/Superposition (nel predittore, §7.4), esperti top-2 con la loss di bilanciamento **corretta** (opzionali, come `TopKMoE` sulle probe di strategia), belief/valore, curriculum sulla lunghezza, `timespans` come condizionamento (Δt nell'AdaLN), Chronovisor, `ScanResult`, finestre a 50% di overlap per la scansione, LEAK-01. **Cosa si sostituisce:** LTC/`ncps`, `HopfieldLayer`, CNN su raster (rinviata), loss a entropia, MSE su one-hot, `confidence=0.85`, `argmax % 3`, attribuzione collineare, `skill_adapter` mai alimentato.

### 7.10 Il ciclo di prodotto: come "il coach confronta"

La visione originale — allenare una volta sui professionisti, distribuire un coach già esperto, far caricare agli utenti i propri `.dem`, aggiornare periodicamente — è realizzabile e diventa concreta così:

1. **Pre-training sui pro** (demo pro → §7.5) → congelamento → pacchetto rilasciato = `{encoder, world model, probe calibrate, indice memoria pro, schema_fingerprint, versione}`.
2. **L'utente carica un `.dem`** → ingestion esistente → episodi → codifica con l'encoder congelato. *Nessun fine-tuning sui dati dell'utente per la parte "riferimento"*: farlo insegnerebbe al coach gli errori dell'utente. La personalizzazione passa da memoria episodica e livello di abilità.
3. **Il confronto** produce quattro cose misurabili: (i) il **profilo di sorpresa** (dove il tuo gioco diverge da ciò che un modello dei pro si aspetta); (ii) i **riferimenti pro** (cosa hanno fatto i pro da situazioni simili, con la traiettoria fantasma); (iii) i **Δ delle probe** ("da qui, la tua probabilità di morire entro 2 s è 0,41; per i pro nella stessa situazione 0,18"); (iv) i **momenti critici** con attribuzione. Il livello di abilità (`SkillLatentModel`, esistente) sceglie il registro linguistico.
4. **Aggiornamento**: nuovi demo pro → nuovo pre-training → nuova versione; compatibilità verificata dall'impronta dello schema; promozione solo se il benchmark §7.7 non regredisce (l'attuale protocollo B7.2 con kNN purity e RAG recall resta valido e si estende alle probe).

### 7.11 Budget di calcolo sulla macchina attuale

RX 9070 XT (gfx1201), `torch 2.13.0+rocm10.0.0` nel `.venv` (CUDA disponibile = sì), bf16 ≈ 118 TFLOPS dichiarati nel codice. Modello 1,3 M parametri, 6144 token per passo → ≈ 50 GFLOP per passo (forward + backward) → ordine del **millisecondo**. 20 000 passi = minuti di GPU. Il vero costo è nei dati: esportare una volta le finestre in `safetensors` (passo 1) elimina le query SQLite per epoca. Indice memoria pro: 1,2 GB in bf16 se si tiene un token ogni 4, oppure IVF-PQ con FAISS. Le probe e le valutazioni costano secondi. **Il progetto non ha un problema di hardware; ha avuto un problema di obiettivo.**

---

## 8. Piano di correzione incrementale

**In parole semplici.** Nove passi, ciascuno piccolo abbastanza da essere finito e verificato in pochi giorni di lavoro a coppia, ciascuno con un criterio oggettivo di "fatto". Si lavora **in questo repo, in Python**: è la strada più corta verso un coach che funziona davvero. Il porting in C++ (piano `latentis`) può seguire lo stesso disegno dopo, se e quando servirà.

Stima complessiva: **18–22 giorni di sessioni a coppia** (un "giorno" ≈ 3–5 ore focalizzate). Il percorso critico è 0 → 1 → 2 → 3 → 4; i passi 5 e 6 si possono sovrapporre al 4.

### Passo 0 · Congelare il training attuale (subito, 0 giorni)

- Non lanciare `train.sh` / `run_full_training_cycle.py` con l'obiettivo attuale: ogni ora di GPU spesa produce checkpoint che il §4 dimostra non informativi. L'ingestion in corso **continua** (i dati servono).
- Archiviare i checkpoint attuali (già fatto il 2026-09-01 in `models/global/archive_pre_rebuild_2026-09-01/`).
- **Accettazione**: nessun nuovo checkpoint `jepa_brain*.pt`/`rap_coach*.pt` scritto finché il passo 4 non è superato.

### Passo 1 · Esportare gli episodi in `safetensors` (2–3 giorni)

- Nuovo `tools/export_episodes.py` (gira col `.venv`, legge il monolite in sola lettura con `mode=ro`, mai `immutable=1`; controlla `readlink -f` del symlink e `lsblk` per il mount drift documentato).
- Per split (TRAIN/VAL/TEST dai `dataset_split` esistenti, dopo `assign_dataset_splits`): episodi `(demo, player, round)` ≥ 64 tick, in formato CSR: `x_num [N_tick, 21] f32`, `x_cat [N_tick, 3] i32`, `actions [N_tick, 5] f32`, `episode_offsets [E+1] i64`, tabelle per episodio (`labels`, `demo_id`, `player_id` hashato, `round`, `tick_rate`, `match_date`, `match_date_source`), `manifest.json` (schema `cs2_v2`, impronta, conteggi, git SHA, UTC, versioni torch/numpy, SHA-256 degli shard).
- Riusa `FeatureExtractor.extract_batch()` per produrre i 25 valori attuali e rimappa a v2 (drop 16 e 18; 17 e 19 → indici categoriali): parità per costruzione. Esporta anche i primi 100 k tick con entrambe le rappresentazioni per un test di rimappatura senza perdita.
- Profili: `full` (tutti gli episodi, cap 4096 tick per episodio ≈ 8–10 GB), `medium` (≤ 8 episodi per player-match, ≈ 3 GB, default), `sample_2k` (2000 finestre, ≈ 6 MB, committato per i test).
- **Accettazione**: conteggi coerenti col DB; nessun episodio attraversa un round; nessun `demo` in due split; test di rimappatura verde; `sample_2k` in `tests/fixtures/`.

### Passo 2 · Schema v2 e contratto tipizzato (2 giorni)

- `configs/schema_cs2_v2.json` + `nn/feature_schema.py` (`FeatureSchema`, `Field`, normalizzatori come dati, `fingerprint()`), `Extractor(schema)` senza stato globale (l'attuale `vectorizer.py` resta per la pipeline di ingestione finché non viene migrato; il training v2 legge dagli shard).
- Sidecar dei checkpoint: aggiungere `schema_id`, `schema_version`, `schema_fingerprint`, `recipe`, `git_sha`, `created_utc`; `load_nn` alza `SchemaMismatchError` su impronta diversa.
- **Accettazione**: `test_metadata_dim_contract.py` esteso allo schema v2; un checkpoint con impronta diversa viene rifiutato con errore nominato.

### Passo 3 · Pacchetto `nn/jepa_v2/` (3–4 giorni)

- Moduli: `tokenizer.py` (Conv1d + embedding categoriali + RoPE), `encoder.py` (blocchi causali RMSNorm/SwiGLU/QK-norm), `projector.py`, `predictor.py` (AR + FiLM sull'orizzonte; variante AdaLN-zero per le azioni), `objectives.py` (`SIGReg` esatto, `PredictionMSE`, `VICReg` con asserzione `B≥2`, `InfoNCE` legacy), `sampler.py` (finestre da episodi CSR, orizzonti, `TransitionSampler`), `trainer.py` (**l'unico** trainer: AdamW, warmup+coseno per passo, bf16, clip, accumulo opzionale, checkpoint + sidecar, resume completo incluso RNG), `telemetry.py` (RankMe da `collapse_metrics.py`, probe online, CSV/JSONL), `config.py` (JSON validato, chiavi sconosciute = errore).
- Test: parità di `SIGReg` con l'implementazione di riferimento (copiata da `le-wm/module.py` nel test); proprietà (gaussiana isotropa → statistica ≈ 0; nuvola collassata → alta); test di permutazione dell'encoder (J3); forme; gradiente finito; determinismo con seme fisso (due run → stessi pesi).
- **Accettazione**: `pytest tests/test_jepa_v2_*.py` verde; smoke di 200 passi su `sample_2k` sotto 2 minuti su CPU.

### Passo 4 · Telemetria, probe, baseline: battere il legacy (2 giorni + tempo GPU)

- Probe online e offline (§7.6, §7.8), `LeakageGuard` con test di permutazione/ablazione, gate di collasso su RankMe/std.
- `tools/baseline_legacy_infonce.py`: la ricetta attuale con B = 128 sulle stesse finestre.
- Run: v2 e legacy su `medium`, 3 semi ciascuno; rapporto `docs/benchmarks/jepa_v2_vs_legacy.md` col protocollo §7.7.
- **Accettazione**: criteri §7.7 soddisfatti. Se **non** lo fossero, il passo 4 si ripete con lo sweep di $\lambda_T$ prima di procedere: è l'unico punto del piano in cui la matematica va dimostrata sui dati veri.

### Passo 5 · Un solo trainer, un solo entry point, documenti veri (1 giorno)

- Spostare in `nn/legacy/` (con test che verifica che nessun path attivo li importi): `jepa_train.py` (CLI), `JEPATrainer.train_epoch/check_val_drift/retrain_if_needed`, `JEPATrainingConfig`, `SelfSupervisedDataset`, `forward_selective`, la testa LSTM+MoE di `JEPACoachingModel`, `ConceptLabeler.label_tick`.
- `run_full_training_cycle.py` chiama il trainer v2; `train.sh` con header corretto; docstring di `llm_service.py:4` e `lesson_generator.py:5` corretti; `README` di `nn/` aggiornato (una sola verità su target, batch, loss).
- Test che codificavano i comportamenti errati (elenco in Appendice E) rimossi o spostati in `tests/legacy/`.
- **Accettazione**: `grep` di `from ...legacy` nei path attivi = 0; suite verde.

### Passo 6 · World model, sorpresa, ghost, Chronovisor v2 (3 giorni)

- `TransitionSampler` + predittore AdaLN-zero + training con $\mathcal L_{\text{next}} + 0.1\,\mathrm{SIGReg}$ e rollout a 8 token; `Surprise` (Welford per flusso); `CEMPlanner` (300/10/30/orizzonte 8); `GoalProvider` dai vicini pro; `chronovisor_v2.py` (secondi, Savitzky–Golay, z-soglie, due segnali) che riusa `_analyze_signal_at_scale` e `_deduplicate_across_scales` esistenti.
- Test: su `medium`, i momenti critici da sorpresa+valore devono avere precision@10 verso eventi di morte/kill ≥ 3× il caso; il planner deve ridurre la distanza latente al goal su episodi held-out; il ghost integrato deve restare dentro la mappa (bounds) nel 99% dei casi.
- **Accettazione**: i tre test sopra verdi; report in `docs/benchmarks/coach_v2_signals.md`.

### Passo 7 · Teste del coach sui latenti (3–4 giorni)

- `nn/coach_v2/`: `probes.py` (strategia CE + Switch aux se MoE; concetti con etichette esterne; calibrazione), `value.py` (euristico + esito scontato), `memory.py` (indice pro FAISS/kNN, scrittura gated), `attribution.py` (controfattuali), `communication.py` (template per livello, confidenza calibrata, topic da attribuzione, JSON per l'LLM), `telemetry()` per l'Observatory.
- `rap/` resta in `nn/legacy/experimental/` finché il coach v2 non supera le sue verifiche; `USE_RAP_MODEL` → `USE_COACH_V2`.
- **Accettazione**: nessuna confidenza costante nel codice (test che cerca letterali); attribuzione con rango pieno (nessuna coppia di uscite collineari sui dati di test, correlazione < 0.9); calibrazione ECE < 0.05 sulle probe usate per i consigli.

### Passo 8 · Collegare al CoachingService e alla UI (2 giorni)

- `coach/jepa_insight_adapter.py` v2: consuma probe/sorpresa/momenti/ghost (non la testa morta); il gate F-0029 diventa "il pacchetto contiene probe calibrate e indice memoria".
- `lesson_generator`/`llm_service`: il prompt riceve il JSON strutturato (§7.9 (i)); `GhostEngine` v2 legge il planner; overlay per token (un valore per 125 ms, non uno per 32 tick).
- **Accettazione**: un `.dem` dell'utente produce almeno un `CoachingInsight` marcato `source=neural` con confidenza calibrata e riferimento a un momento critico; test end-to-end su `sample_2k`.

### Passo 9 · Ciclo di prodotto (continuo)

- Script di rilascio: `tools/release_coach.py` (esporta pacchetto `{encoder, world model, probe, indice, schema, versione}` + `CHANGELOG` con date assolute); confronto pre/post con `tools/eval_harness.py` esteso alle probe; regola di promozione B7.2 estesa (§7.10).
- **Accettazione**: due versioni consecutive del pacchetto, la seconda promossa solo se il benchmark non regredisce.

### Tabella riassuntiva

| Passo | Giorni | Dipende da | Criterio di accettazione (sintesi) |
|---|---|---|---|
| 0 | 0 | — | nessun nuovo checkpoint con l'obiettivo attuale |
| 1 | 2–3 | ingestion finita | shard `safetensors` + manifest; rimappatura senza perdita |
| 2 | 2 | 1 | schema v2 con impronta; mismatch → errore |
| 3 | 3–4 | 2 | test v2 verdi; parità SIGReg; smoke < 2 min |
| 4 | 2 + GPU | 3 | **v2 batte legacy** (§7.7), 3 semi |
| 5 | 1 | 4 | zero import di `legacy` nei path attivi; docs veri |
| 6 | 3 | 4 | momenti critici ≥ 3× caso; planner riduce il costo |
| 7 | 3–4 | 6 | confidenze calibrate, attribuzione a rango pieno |
| 8 | 2 | 7 | insight `source=neural` end-to-end |
| 9 | continuo | 8 | promozione solo senza regressione |

---

## 9. Cosa tenere esattamente com'è

Perché nessuno confonda "correggere la matematica" con "rifare tutto":

- **Ingestion e storage**: parser, shard per partita con id deterministico e migrazioni, monolite WAL, `IngestionTask` con ripresa sicura, gate di qualità, atomicità delle scritture.
- **Split** cronologico tra demo (`temporal_assign`) e gate di eleggibilità; avviso OI-2 sulla provenienza delle date.
- **Finestre che non attraversano il round** (D-22) e il rifiuto del padding con zeri (J-5, WR-53).
- **Contratto delle feature** (nomi ordinati, assert a import, sidecar, `StaleCheckpointError`): si estende, non si rimuove.
- **`collapse_metrics.py`** intero; `EmbeddingCollapseDetector` come gate (con nuovi ingressi); `EarlyStopping`; `CallbackRegistry` con isolamento degli errori; `TensorBoardCallback`.
- **`PlayerKnowledge`** e il modello di osservabilità parziale; `TensorFactory` in modalità POV (per il futuro flusso visivo).
- **Algoritmo del Chronovisor** (differenze a lag multi-scala, raggruppamento, dedup) e la semantica di `ScanResult`.
- **FiLM/`SuperpositionLayer`** come meccanismo di condizionamento (riusato nel predittore).
- **`SkillLatentModel`** (z-score → percentile, livelli 1–10) e i tre registri linguistici della comunicazione.
- **`persistence.save_nn/load_nn`** con registro SHA-256 e scrittura atomica; `set_global_seed`, `seeded_generator`, `get_device` con il workaround ROCm.
- **La disciplina di annotazione** (ID dei finding nel codice, docstring che dichiarano i limiti): è ciò che ha reso possibile questa diagnosi.

---

## 10. Appendici

### A. Formule e pseudocodice di riferimento

#### A.1 SIGReg (implementazione esatta e test di parità)

Riferimento: `lucas-maes/le-wm/module.py` (LeWorldModel), identica in spirito a `galilai-group/lejepa/MINIMAL.md` (che usa 256 direzioni). Ingresso `proj` di forma `(T, B, D)`: la statistica è calcolata su $N = B$ campioni per ogni tempo (modalità *batch*). Per la modalità *temporale* (LeNEPA) si passa `(B, T, D)` trasposto in modo che $N = T$.

```python
class SIGReg(torch.nn.Module):
    def __init__(self, knots: int = 17, num_proj: int = 1024, t_max: float = 3.0):
        super().__init__()
        t = torch.linspace(0, t_max, knots)
        dt = t_max / (knots - 1)
        weights = torch.full((knots,), 2 * dt); weights[[0, -1]] = dt          # trapezi (dominio simmetrico → ×2)
        window = torch.exp(-t.square() / 2.0)                                     # phi(t) della N(0,1) = finestra w(t)
        self.register_buffer("t", t); self.register_buffer("phi", window)
        self.register_buffer("weights", weights * window)
        self.num_proj = num_proj

    def forward(self, proj: torch.Tensor, generator: torch.Generator | None = None) -> torch.Tensor:
        # proj: (..., N, D). Direzioni ricampionate a ogni passo; `generator` seedato con global_step per riproducibilità.
        A = torch.randn(proj.size(-1), self.num_proj, device=proj.device, generator=generator)
        A = A / A.norm(p=2, dim=0, keepdim=True)                                  # colonne unitarie
        x_t = (proj @ A).unsqueeze(-1) * self.t                                   # (..., N, M, K)
        err = (x_t.cos().mean(-3) - self.phi).square() + x_t.sin().mean(-3).square()   # media su N
        statistic = (err @ self.weights) * proj.size(-2)                          # Epps–Pulley × N, per direzione
        return statistic.mean()                                                   # media su M direzioni (e su ...)
```

Test di parità: fissare `A` (passare un generator seedato) e confrontare con una copia letterale della funzione di riferimento su input `z ~ (8, 64, 32)`: tolleranza relativa $10^{-5}$. Test di proprietà: `z = torch.randn(1, 4096, 64)` → statistica $\approx$ piccola e stabile al variare del seme; `z = costante + 1e-3·rumore` → statistica grande (ordine $N$). Test del gradiente: `torch.autograd.gradcheck` in float64 su $N=16$, $D=4$, $M=8$.

#### A.2 Ricette pubblicate (numeri da riprodurre)

| | LeJEPA (2511.08544) | LeWorldModel (2603.19312) | LeNEPA (2607.00958) |
|---|---|---|---|
| Dati | immagini, 2 viste globali + 8 locali | pixel 64×64 + azioni | serie temporali multicanale, patch conv1d |
| Encoder | qualsiasi (ViT/ResNet), proiettore MLP+BN | ViT-Tiny (5 M) + MLP+BN → latente | Transformer causale 8L, d 192/256, 4 head, RMSNorm/SwiGLU/RoPE, QK-norm |
| Predittore | nessuno (media delle viste) | Transformer 6L, AdaLN-zero sulle azioni | proiettore MLP+BN+ReLU → 64 dim |
| Loss | $\lambda\,\mathrm{SIGReg} + (1-\lambda)\lVert\mu - z_v\rVert^2$ | $\lVert\hat z_{t+1}-z_{t+1}\rVert^2 + \lambda\,\mathrm{SIGReg}$ | $\lVert h(\hat z_t) - h(z_{t+1})\rVert^2 + \lambda_T\,\mathrm{SIGReg}_{\text{temp}}$ |
| Iperparametri | $\lambda = 0.05$, $M = 1024$, $B \ge 128$ | $\lambda = 0.1$, $M = 1024$, $B = 128$, 4 frame | $\lambda_T$ 2.5–20, $B = 256$, 20 k passi, lr $10^{-4}\to10^{-6}$, warmup 1000, wd 0.01→0.1, bf16 |
| EMA / stop-grad / negativi | no / no / no | no / no / no | no / no / no |
| Planning | — | CEM 300 campioni, 10–30 iter, 30 élite, orizzonte 5, costo terminale | — |

#### A.3 VICReg (per confronto)

$$\mathcal L_{\text{VICReg}} = \lambda\, s(Z,Z') + \mu\, [v(Z) + v(Z')] + \nu\, [c(Z) + c(Z')],\quad \lambda=\mu=25,\ \nu=1,$$

con $s$ = MSE tra viste, $v$ = hinge sulla deviazione standard, $c$ = somma dei quadrati delle covarianze fuori diagonale. Nel repo manca il termine $s$ (sostituito da InfoNCE) e $v,c$ pesano 25 e 1 con fattore globale 0.01. Con SIGReg non serve.

#### A.4 InfoNCE (modalità legacy)

$$\mathcal L = -\log \frac{\exp(\hat s^+/\tau)}{\exp(\hat s^+/\tau) + \sum_{j=1}^N \exp(\hat s^-_j/\tau)},\qquad \hat s = \text{coseno}.$$

Valore "a caso": $\log(N+1)$. Con $B=128$ e negativi in-batch ($N = 127$) diventa una baseline ragionevole per il confronto §7.7.

#### A.5 RankMe

$$\mathrm{RankMe}(Z) = \exp\Big(-\sum_i p_i\log p_i\Big),\quad p_i = \frac{\sigma_i(Z)}{\sum_j \sigma_j(Z)},$$

su $Z$ L2-normalizzato per riga, **non centrato** (`nn/collapse_metrics.py:63-72`).

#### A.6 Blocco AdaLN-zero (condizionamento alle azioni, LeWorldModel)

```python
class AdaLNZeroBlock(nn.Module):
    def __init__(self, d, heads, mlp_dim, dropout=0.0):
        self.attn = CausalAttention(d, heads, dropout); self.mlp = SwiGLU(d, mlp_dim, dropout)
        self.norm1 = RMSNorm(d, affine=False); self.norm2 = RMSNorm(d, affine=False)
        self.mod = nn.Sequential(nn.SiLU(), nn.Linear(d, 6 * d))
        nn.init.zeros_(self.mod[-1].weight); nn.init.zeros_(self.mod[-1].bias)      # "zero": il blocco parte come identità
    def forward(self, x, c):                       # x: (B,T,d) latenti; c: (B,T,d) = MLP(azione ⊕ Δt ⊕ orizzonte)
        s1, sc1, g1, s2, sc2, g2 = self.mod(c).chunk(6, dim=-1)
        x = x + g1 * self.attn(self.norm1(x) * (1 + sc1) + s1)
        x = x + g2 * self.mlp(self.norm2(x) * (1 + sc2) + s2)
        return x
```

Il FiLM del repo ($y = \gamma \odot (Wx+b) + \beta$) è la stessa famiglia: AdaLN-zero è FiLM applicato dopo la normalizzazione, con un gate residuale inizializzato a zero.

#### A.7 Planner CEM (il "ghost")

```
input: z_0 (latente attuale), storia a_{≤0}, z_goal, world model g_a, orizzonte H, S campioni, K iter, E élite, bounds
μ ← 0, σ ← σ_0 (per dimensione dell'azione, entro bounds)
ripeti K volte:
    campiona S sequenze A_s ∈ R^{H×5} ~ N(μ, σ²), clip ai bounds
    per ogni s: ẑ_H = rollout(g_a, z_0, A_s)  ;  costo_s = ‖ẑ_H − z_goal‖²  (+ eventuali costi intermedi)
    élite = le E sequenze a costo minimo ; μ, σ ← media, dev.std delle élite
ritorna A* = μ ; ghost = integra Δpos di A* a partire dalla posizione attuale
```

Numeri di partenza (LeWM): $S=300$, $K=10$ (30 nei casi difficili), $E=30$, $H=5$–$8$ token.

#### A.8 Calibrazione della confidenza (temperature scaling)

Per una probe con logit $\ell$, trovare $T>0$ che minimizza la NLL su un set di validazione della probabilità $\mathrm{softmax}(\ell/T)$ (o $\sigma(\ell/T)$); misurare l'ECE (expected calibration error) su 15 bin; accettare se ECE < 0.05. La confidenza mostrata all'utente è $\max_k \mathrm{softmax}(\ell/T)_k$.

#### A.9 Loss ausiliaria di bilanciamento (Switch)

$$\mathcal L_{\text{aux}} = \alpha\, E \sum_{i=1}^{E} f_i\, P_i,\qquad f_i = \tfrac{1}{B}\sum_b \mathbb 1[\arg\max_j p_{b,j} = i],\quad P_i = \tfrac1B\sum_b p_{b,i},\quad \alpha = 0.01.$$

Già implementata in `nn/jepa_model.py:236-243`.

#### A.10 Sorpresa con statistiche running (Welford)

Per ogni flusso (giocatore), mantenere $n, \bar\varepsilon, M_2$; a ogni token: $n{+}{=}1$; $\delta = \varepsilon_t - \bar\varepsilon$; $\bar\varepsilon {+}{=} \delta/n$; $M_2 {+}{=} \delta(\varepsilon_t - \bar\varepsilon)$; $z_t = (\varepsilon_t - \bar\varepsilon)/\sqrt{M_2/(n-1)}$. Scrittura in memoria se $z_t > \tau_w$ (partire da $\tau_w = 2.5$). Per l'inizializzazione usare le statistiche della popolazione pro.

#### A.11 Valore da esito scontato

Con $t$ il token corrente, $T_{\text{end}}$ il token di fine round, rate $r$ token/s, $\gamma_s = 0.97$ per secondo:

$$V^{\text{target}}_t = \gamma_s^{(T_{\text{end}} - t)/r}\cdot \mathbb 1[\text{round\_won}].$$

Calcolato a fine round e usato solo come **target** di regressione (nessun leakage nell'input).

### B. Letteratura usata e cosa prendere da ciascun lavoro

| arXiv | Titolo | Cosa prendiamo |
|---|---|---|
| 2306.02572 | LeCun — latent-variable EBM / H-JEPA | il principio: predire nello spazio latente |
| 2511.08544 | LeJEPA: provable and scalable SSL without the heuristics | SIGReg, teoria della gaussiana isotropa, loss informativa, niente EMA/stop-grad |
| 2603.19312 | LeWorldModel: stable end-to-end JEPA from pixels | ricetta world model + AdaLN-zero + CEM; implementazione SIGReg |
| 2607.00958 | LeNEPA: no-augmentation next-latent prediction for time series | tokenizer conv1d, Transformer causale RMSNorm/SwiGLU/RoPE, proiettore, SIGReg temporale, probe ai layer intermedi |
| 2606.07031 | CF-JEPA | predizione multi-orizzonte senza masking |
| 2410.05016 | T-JEPA (tabulare, ICLR 2025) | tokenizzazione numerici/categoriali, variante a sottoinsiemi di campi |
| 2509.25449 | TS-JEPA | riferimento per masking uniforme 70% su patch (alternativa) |
| 2605.11130 | HEPA | predittore condizionato all'orizzonte; testa a CDF di sopravvivenza per "eventi entro $h$" (estensione futura) |
| 2602.04643 | SC-JEPA | predizione di anomalie/precursori multi-risoluzione (per i momenti critici) |
| 2606.31495 | Surprise as a signal for plasticity and metacognition | errore di predizione → gate della memoria episodica |
| 2606.12979 | EPM-JEPA | modulazione del predittore dall'esperienza |
| 2606.28383 | Zero-label driving complexity via JEPA | il "canale di sorpresa" (già nella roadmap del repo) |
| 2606.27014 | Generalization theory for JEPA world models | latente > ricostruzione; regret di planning ∝ radice della loss; tenere i rollout corti |
| 2105.04906 · 2211.10831 · 2110.09348 | VICReg · JEPA = slow features · dimensional collapse | perché la sola levigatezza non basta; metriche di collasso |
| 2101.03961 · 1701.06538 | Switch Transformer · Sparsely-gated MoE | loss di bilanciamento (segno corretto) |
| 2602.03604 | EB-JEPA (Meta FAIR, libreria) | organizzazione del codice image/video/action-conditioned + planning |

### C. Glossario minimo

- **Encoder / latente / embedding**: la funzione che comprime una finestra di gioco in un vettore; il vettore stesso.
- **Collasso**: tutti i latenti diventano (quasi) uguali; la predizione è perfetta e inutile.
- **SIGReg**: regolarizzatore che obbliga i latenti ad avere la forma di una gaussiana isotropa, verificata su proiezioni casuali (statistica di Epps–Pulley).
- **Probe**: piccolo modello (spesso lineare) che legge un fatto esterno dai latenti congelati; misura quanto la rappresentazione è utile.
- **World model**: predittore del futuro latente **date le azioni**; permette di simulare "cosa succede se…".
- **Ghost**: traiettoria pianificata dal world model verso una situazione-obiettivo (ciò che i pro avrebbero fatto).
- **Sorpresa**: errore di predizione del world model, normalizzato; alto = comportamento inatteso per un modello dei pro.
- **Momento critico**: variazione rapida di valore o sorpresa, trovata dal Chronovisor.
- **Leakage**: l'etichetta è (in parte) una funzione dell'input; il modello impara a leggere il foglio, non la materia.
- **RankMe**: quante direzioni indipendenti usa lo spazio latente (1 = collasso).
- **Token**: gruppo di 8 tick (125 ms) compresso in un vettore prima dell'encoder.

### D. Indice delle evidenze (percorsi relativi a `Programma_CS2_RENAN/`)

| Voce | File:righe |
|---|---|
| J1 | `backend/nn/training_orchestrator.py:644-652, 772-781, 859-866`; `backend/nn/jepa_trainer.py:271-275, 351-352` |
| J2 | `backend/nn/training_orchestrator.py:45, 861-866`; `docs/doctrine/notes/16-papers.md:94-96`; `models/global/archive_pre_rebuild_2026-09-01/jepa_brain.pt.meta.json` |
| J3 | `backend/nn/jepa_model.py:35, 46-53, 201-202` |
| J4 | `backend/nn/training_orchestrator.py:97, 868-905`; `backend/nn/jepa_trainer.py:193-212, 266, 314-322`; `backend/nn/jepa_model.py:155-157, 210-223`; `backend/nn/jepa_train.py:445-449` |
| J5 | `backend/nn/jepa_model.py:440-441`; `backend/nn/jepa_trainer.py:271-275, 591` |
| J6 | `backend/nn/jepa_model.py:126-127, 401-405`; `backend/nn/jepa_trainer.py:147-191`; `backend/nn/training_orchestrator.py:163-169` |
| J7 | `backend/nn/jepa_train.py:335, 361-365, 371, 445-449, 474, 513, 579, 727-792`; `backend/nn/jepa_trainer.py:362-528`; `backend/nn/training_config.py:50-65`; `backend/nn/dataset.py:25-63` |
| J8 | `backend/nn/jepa_model.py:133-143, 177-179, 236-243`; `backend/nn/training_orchestrator.py:467-469`; `backend/nn/jepa_train.py:634-641, 705-707`; `backend/coaching/jepa_insight_adapter.py:180-228, 262, 276` |
| J9 | `backend/nn/jepa_model.py:601-733, 735-861 (809-821, 856-858), 980, 1085`; `backend/nn/training_orchestrator.py:911-924` |
| J10 | `backend/nn/training_orchestrator.py:340-377`; `backend/nn/early_stopping.py:57-97` |
| J11 | `backend/nn/training_orchestrator.py:418-436, 704-725` |
| J12–J15 | `backend/nn/jepa_model.py:291-350`; `backend/nn/jepa_trainer.py:130-132, 207-212, 301-308, 362-528`; `backend/nn/config.py:165-176` |
| R1 | `backend/nn/experimental/rap_coach/model.py:81-90`; `run_full_training_cycle.py:242-247`; `backend/nn/factory.py:52-83`; `backend/nn/training_orchestrator.py:117-140` |
| R2 | `core/config.py:236-240`; `backend/nn/training_orchestrator.py:128-132`; `backend/nn/inference/ghost_engine.py:43-47`; `backend/nn/experimental/rap_coach/memory.py:11-21, 34-38`; `requirements-rap.in`; `models/global/archive_pre_rebuild_2026-09-01/rap_coach*.pt(.meta.json)` |
| R3 | `backend/nn/experimental/rap_coach/trainer.py:33, 67`; `backend/nn/training_orchestrator.py:1247-1250, 1622-1632, 1711-1773`; `backend/nn/experimental/rap_coach/strategy.py:94`; `backend/nn/experimental/rap_coach/model.py:167` |
| R4 | `backend/nn/experimental/rap_coach/model.py:176-205`; `backend/nn/experimental/rap_coach/trainer.py:80, 92` |
| R5 | `backend/nn/training_orchestrator.py:1224-1244, 1651-1709`; `backend/nn/experimental/rap_coach/trainer.py:69-77` |
| R6 | `backend/nn/experimental/rap_coach/memory.py:52-93, 115-121, 161-164, 176, 185-194, 196-242, 244-265, 300` |
| R7 | `backend/nn/experimental/rap_coach/perception.py:20, 25, 55, 78-84`; `backend/processing/tensor_factory.py:173-224, 273-284, 605-630` |
| R8 | `backend/nn/experimental/rap_coach/pedagogy.py:22, 70-72, 78-82, 88-98`; `backend/nn/experimental/rap_coach/model.py:164`; `backend/nn/experimental/rap_coach/trainer.py:56-62` |
| R9 | `run_ingestion.py:222-225`; `backend/nn/experimental/rap_coach/communication.py:86, 109-112, 121-123` |
| R10 | `backend/nn/experimental/rap_coach/chronovisor_scanner.py:15, 68-90, 269-279, 310-398, 400-440` |
| R11 | `backend/nn/training_orchestrator.py:1023-1041`; `backend/processing/state_reconstructor.py:103-119`; `backend/nn/experimental/rap_coach/model.py:115-118`; `backend/nn/inference/ghost_engine.py:180-185`; `backend/nn/coach_manager.py` (`get_interactive_overlay_data`, ciclo `for tick in window`) |
| R12 | `backend/nn/maturity_observatory.py:155, 211, 225` |
| D1–D6 | `backend/processing/feature_engineering/vectorizer.py:144-185, 338-341, 360-363, 366-369, 371-381, 386-414, 430-450`; `backend/processing/feature_engineering/base_features.py:34-45`; `backend/nn/coach_manager.py` (`MATCH_AGGREGATE_FEATURES` e assert); `backend/nn/factory.py:44-100` |
| D7 | `run_full_training_cycle.py`; `backend/nn/coach_manager.py` (`_execute_training_phases`); `train.sh`; `backend/services/llm_service.py:4`; `backend/services/lesson_generator.py:5, 314-325` |
| Dati positivi | `backend/nn/coach_manager.py` (`temporal_assign`, `_fetch_jepa_windows` D-22); `backend/nn/data_quality.py:58-59`; `backend/nn/collapse_metrics.py`; `backend/processing/player_knowledge.py` |

### E. Test da rimuovere, spostare o aggiungere

**Codificano comportamenti che il piano elimina (→ `tests/legacy/` al passo 5):**
- `tests/test_jepa_collapse_feed.py::test_single_window_batch_is_unmeasurable_not_collapsed`, `::test_within_batch_variance_still_takes_precedence` (B=1 deve alzare).
- `tests/test_jepa_model.py::test_positioning_exposed`, `::test_economy_wasteful_pistol_round`, `::test_trade_isolated_low_kast`, `::test_label_batch_2d`, `::test_label_batch_3d` (leakage di `label_tick`).
- `tests/test_jepa_model.py::test_jepa_coaching_forward`, `::test_jepa_coaching_with_role`, `::test_forward_vl_output_shape`, `::test_concept_probs_sum_to_one` (testa mai allenata; softmax incoerente con BCE).
- `tests/test_jepa_training_pipeline.py::test_finetune_*`, `::test_target_is_last_tick`, `::test_context_target_no_overlap` (path CLI e orizzonte 1 tick).
- `tests/test_rap_coach.py::test_advantage_gap`, `::test_with_skill_vec`, `::test_diagnose_shape` (funzioni mai chiamate in produzione / attribuzione collineare) — restano solo se il modulo va in `legacy/`.

**Restano validi (eventualmente adattati):** `test_contrastive_loss` (legacy A/B), `test_freeze_unfreeze_encoders`, `test_model_save_load`, `test_jepa_window_fetcher.py` (contiguità, determinismo), `test_metadata_dim_contract.py` (esteso allo schema v2), tutti i test di `collapse_metrics`.

**Da aggiungere:** parità e proprietà di SIGReg (A.1); permutazione dell'encoder (J3); `vicreg_regularization` alza con $N<2$; `LeakageGuard` (permutazione e ablazione, §3.8); determinismo run-to-run (due run con lo stesso seme → pesi identici); rimappatura senza perdita 25→v2 (passo 1); `SchemaMismatchError` (passo 2); smoke 200 passi su `sample_2k`; benchmark §7.7 come test lento marcato; precision@10 dei momenti critici, riduzione del costo del planner, ghost dentro i bounds (passo 6); nessuna confidenza letterale, attribuzione a rango pieno, ECE < 0.05 (passo 7); insight `source=neural` end-to-end (passo 8).

### G. Verifiche empiriche (sintesi; dettaglio in Parte II §12)

`tools/verify_math_claims.py` (sola lettura, CPU, 488 s; JSON in `docs/research/verify_math_claims_2026-09-05.json`), 1.200.000 tick pro su 30 demo, 14.255 finestre di produzione (10 tick + bersaglio):

| misura | valore | cosa dimostra |
|---|---|---|
| frequenza di tick | 64,0 tick/s (15,625 ms) | unità per orizzonti e Chronovisor |
| $R^2$ dell'identità a 1 / 8 / 32 / 128 / 640 tick | 0,9978 / 0,9742 / 0,9106 / 0,7683 / 0,4442 | J2: il bersaglio a 1 tick è il presente |
| media $\|\Delta_1\|$ per componente | $7{,}9\cdot10^{-4}$ (< σ dell'augmentation $10^{-2}$) | il rumore iniettato supera il segnale |
| feature costanti in > 93% delle finestre di 11 tick | 19 su 25 | feature lente (Sobal) |
| τ appreso nel checkpoint | 0,0481 (da 0,07) | dinamica della temperatura con positivi facili |
| $\|\theta_{ctx}-\theta_{tgt}\|$ | 0,135 (casuale: 22,8) | EMA convergiuta: modello finale ≈ SimSiam a B=1 |
| RankMe encoder archiviato / rete casuale / gaussiana | 66,1 / 60,8 / 255,4 (su 256) | collasso dimensionale |
| MSE predittore vs identità (h=1) | 0,383 vs 0,011 | il predittore è peggiore dell'identità |
| InfoNCE top-1, rete **casuale** + identità (h=1) | 97,0% | J4: i negativi sono banali senza apprendimento |
| AUROC `round_won`: grezze / archiviato / casuale | 0,760 / 0,677 / 0,681 | l'encoder distrugge informazione |
| AUROC morte entro 2 s: grezze / archiviato / casuale | 0,838 / 0,736 / 0,704 | idem |
| SIGReg: gaussiana / archiviato / casuale / collassato | 1,05 / 661 / 2.026 / 4.237 | scala per l'abort e per il benchmark |

### F. Rapporto con il piano `latentis` (C++)

Il piano del 2026-09-05 per la libreria C++ `latentis` (file `/home/renan/.claude/plans/ciao-amico-mio-questo-greedy-ripple.md`) descrive **la stessa architettura v2** (schema tipizzato, token, SIGReg, world model, sorpresa, probe) come framework domain-agnostic con motore proprio. La sequenza raccomandata è: prima correggere la matematica **qui, in Python** (passi 0–8: settimane, con PyTorch e la GPU già funzionante), dimostrare con il benchmark §7.7 che il coach impara, e solo poi decidere se e cosa portare in C++. Un porting fedele di un nucleo sbagliato avrebbe replicato gli errori del §4 in un altro linguaggio.

---

> **Chiusura.** La diagnosi è dura ma circoscritta: due errori bloccanti (batch di una finestra, orizzonte di un tick), una manciata di errori gravi tutti dello stesso tipo (difese spente in silenzio, etichette che leggono l'input, segni sbagliati nelle loss, output mai collegati), e una pipeline dati che regge. La correzione ha una forma nota nella letteratura del 2025–2026 (LeJEPA, LeWorldModel, LeNEPA), un piano a passi con criteri oggettivi, e riusa quasi tutto ciò che il progetto ha costruito in un anno. Il primo numero da guardare non è più una loss: è l'AUROC di una probe che legge, dai latenti, se il giocatore morirà nei prossimi due secondi — e se quel numero batte il baseline, il coach ha cominciato a capire il gioco. Oggi quel numero è 0,736 per l'encoder archiviato contro 0,838 per le feature grezze (Parte II §12.5): la soglia da superare è misurata, non stimata.
