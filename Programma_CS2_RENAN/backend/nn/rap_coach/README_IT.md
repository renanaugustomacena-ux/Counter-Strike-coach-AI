> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# RAP Coach — Architettura Neurale Pedagogica con Recupero Aumentato

**Autorita:** `Programma_CS2_RENAN/backend/nn/rap_coach/`
**Posizione canonica:** `backend/nn/experimental/rap_coach/` (questo pacchetto e uno shim di compatibilita dalla migrazione P9-01)
**Feature flag:** `USE_RAP_MODEL=True` (default: `False`)

## Introduzione

RAP (Retrieval-Augmented Pedagogical) Coach e il modello neurale di coaching ad alta
fedelta del Macena CS2 Analyzer. Implementa un'architettura a 7 livelli che percepisce
lo stato di gioco attraverso stream CNN, mantiene la memoria temporale tramite neuroni
Liquid Time-Constant (LTC), prende decisioni attraverso uno strato strategico
Mixture-of-Experts, e genera feedback di coaching leggibile dall'uomo, calibrato sul
livello di abilita del giocatore.

Il modello consuma il vettore canonico a 25 dimensioni (`METADATA_DIM=25`) prodotto da
`FeatureExtractor` insieme a frame visivi sintetizzati (cono visivo, contesto mappa,
differenza di movimento). Produce probabilita di consiglio, stime dello stato di credenza,
funzioni di valore, delta di posizionamento ottimale e punteggi di attribuzione causale.

## Inventario dei File

| File | Classi / Esportazioni | Scopo |
|------|----------------------|-------|
| `__init__.py` | -- | Shim di compatibilita (P9-01). Reindirizza a `experimental/rap_coach/`. |
| `model.py` | `RAPCoachModel`, `RAP_POSITION_SCALE` | Shim che ri-esporta l'orchestratore completo del modello. |
| `memory.py` | `RAPMemory` | Shim che ri-esporta il livello di memoria LTC-Hopfield. |
| `trainer.py` | `RAPTrainer` | Shim che ri-esporta l'orchestratore di addestramento. |
| `perception.py` | `RAPPerception`, `ResNetBlock` | Shim che ri-esporta il livello di percezione CNN. |
| `strategy.py` | `RAPStrategy`, `ContextualAttention` | Shim che ri-esporta il livello strategico MoE. |
| `pedagogy.py` | `RAPPedagogy`, `CausalAttributor` | Shim che ri-esporta il livello di feedback causale. |
| `communication.py` | `RAPCommunication` | Shim che ri-esporta il generatore di consigli in linguaggio naturale. |
| `chronovisor_scanner.py` | `ChronovisorScanner`, `CriticalMoment`, `ScanResult`, `ScaleConfig`, `ANALYSIS_SCALES` | Shim che ri-esporta il rilevamento multi-scala dei momenti critici. |
| `skill_model.py` | `SkillAxes`, `SkillLatentModel` | Shim che ri-esporta gli assi di abilita del giocatore (stile VAE). Posizione canonica: `backend/processing/skill_assessment`. |

## Architettura: La Pipeline RAP a 7 Livelli

Il modello RAP elabora lo stato di gioco attraverso sette livelli distinti, ciascuno con
una responsabilita pedagogica specifica. Il diagramma ASCII sottostante mostra il flusso
dati completo:

```
                         RAP Coach — Architettura a 7 Livelli
  ========================================================================

  TENSORI DI INPUT
  +------------------+  +------------------+  +------------------+
  | view_frame       |  | map_frame        |  | motion_diff      |
  | [B, 3, 64, 64]  |  | [B, 3, 64, 64]  |  | [B, 3, 64, 64]  |
  +--------+---------+  +--------+---------+  +--------+---------+
           |                     |                     |
  =========|=====================|=====================|===============
  LIVELLO 1: PERCEZIONE (RAPPerception)
           |                     |                     |
     +-----v------+       +-----v------+       +------v-----+
     | ResNet      |       | ResNet     |       | MotionConv |
     | [1,2,2,1]   |       | [2,2]     |       | 3->16->32  |
     | -> 64-dim   |       | -> 32-dim |       | -> 32-dim  |
     +-----+------+       +-----+------+       +------+-----+
           |                     |                     |
           +----------+----------+----------+----------+
                      |
                z_spatial [B, 128]
                      |
  ====================|================================================
  LIVELLO 2: MEMORIA (RAPMemory)
                      |
            +---------v-----------+        +---------+  metadata
            | Concatenazione      |<-------+ [B,T,25]|  (vettore 25-dim)
            | [B, T, 128+25=153] |        +---------+
            +---------+-----------+
                      |
            +---------v-----------+
            |  LTC (Liquid Time-  |   Cablaggio AutoNCP
            |  Constant) neuroni  |   ncp_units=512
            |  hidden_dim=256     |   seed=42
            +---------+-----------+
                      |
            +---------v-----------+
            | Memoria Associativa |   4 teste di attenzione
            | Hopfield (512 slot) |   NN-MEM-01: bypassata
            | + Addizione Residua |   fino a >=2 passaggi fwd
            +---------+-----------+
                      |
               combined_state [B, T, 256]
                      |
            +---------v-----------+
            | Belief Head         |   256 -> 256 -> 64
            | (attivazione SiLU)  |   belief_dim=64
            +---------+-----------+
                      |
               belief [B, T, 64]
                      |
  ====================|================================================
  LIVELLO 3: STRATEGIA (RAPStrategy)
                      |
            +---------v-----------+
            | Mixture of Experts  |   4 esperti
            | + Superposition     |   context = metadata[:,-1,:]
            | + Context Gate      |   regolarizzazione L1
            +---------+-----------+
                      |
               advice_probs [B, OUTPUT_DIM=10]
               gate_weights [B, 4]
                      |
  ====================|================================================
  LIVELLO 4: PEDAGOGIA (RAPPedagogy + CausalAttributor)
                      |
            +---------v-----------+
            | Critic Head V(s)    |   256 -> 64 -> 1
            | + Skill Adapter     |   skill_vec [B, 10]
            +---------+-----------+
                      |
               value_estimate [B, 1]
                      |
            +---------v-----------+
            | CausalAttributor    |   5 concetti:
            | Fusione Neurale +   |   Positioning, Crosshair,
            | Euristica           |   Aggression, Utility,
            +---------+-----------+   Rotation
                      |
               attribution [B, 5]
                      |
  ====================|================================================
  LIVELLO 5: COMUNICAZIONE (RAPCommunication)
                      |
            +---------v-----------+
            | Motore Template     |   Livelli: low (1-3),
            | Condizionato per    |   mid (4-7), high (8-10)
            | Abilita + Risolutore|   Soglia confidenza: 0.7
            | Angolo              |
            +---------+-----------+
                      |
               consiglio di coaching in linguaggio naturale
                      |
  ====================|================================================
  LIVELLO 6: ANALISI TEMPORALE (ChronovisorScanner)
                      |
            +---------v-----------+
            | Elaborazione Segnale|   micro:  64 tick (~1s)
            | Multi-Scala         |   standard: 192 tick (~3s)
            | + Dedup Cross-Scale |   macro: 640 tick (~10s)
            +---------+-----------+
                      |
               CriticalMoment[]
                      |
  ====================|================================================
  LIVELLO 7: POSITION HEAD (in RAPCoachModel)
                      |
            +---------v-----------+
            | Linear(256, 3)      |   Predice il delta di
            | dx, dy, dz delta    |   posizione ottimale
            +---------+-----------+   RAP_POSITION_SCALE=500.0
                      |
               optimal_pos [B, 3]

  ========================================================================
```

## Costanti Chiave

| Costante | Valore | Sorgente |
|----------|--------|----------|
| `hidden_dim` | 256 | `model.py:45` |
| `perception_dim` | 128 | `model.py:42` (64 + 32 + 32) |
| `ncp_units` | 512 | `memory.py:50` (hidden_dim x 2) |
| `belief_dim` | 64 | `memory.py:92` |
| `OUTPUT_DIM` | 10 | `nn/config.py:123` |
| `METADATA_DIM` | 25 | `vectorizer.py:32` |
| `RAP_POSITION_SCALE` | 500.0 | `nn/config.py:155` |
| `num_experts` | 4 | `strategy.py:42` |
| `hopfield_heads` | 4 | `memory.py:83` |
| `Z_AXIS_PENALTY_WEIGHT` | 2.0 | `trainer.py:26` |

## Invarianti Critiche

| ID | Regola | Conseguenza se Violata |
|----|--------|------------------------|
| **NN-MEM-01** | La memoria Hopfield viene bypassata fino a quando non si sono verificati >=2 passaggi forward di addestramento. L'attivazione avviene anche al caricamento di un checkpoint. | I prototipi casuali iniettano rumore invece di segnale nel combined_state, corrompendo l'addestramento iniziale. |
| **NN-RM-01** | `skill_vec` deve avere forma `[B, 10]`. Le forme non corrispondenti vengono registrate e ignorate. | Dati spazzatura silenziosi nell'adattatore pedagogico distorcono le stime di valore. |
| **NN-RM-03** | `gate_weights` deve essere passato esplicitamente a `compute_sparsity_loss()` (thread-safety, F3-07). | Condizione di competizione sullo stato memorizzato nella cache in inferenza multi-thread. |
| **P-X-02** | Le asserzioni sulla forma dell'input impongono `metadata.shape[-1] == METADATA_DIM`. | Errori criptici di dimensione LSTM/CNN in profondita nel passaggio forward. |
| **NN-CV-03** | Controllo dei limiti dell'indice peak_tick prima di accedere all'array ticks in ChronovisorScanner. | Crash IndexError durante il rilevamento dei momenti critici. |

## Integrazione

RAP Coach si integra con il Macena CS2 Analyzer piu ampio attraverso diversi punti di contatto:

- **CoachTrainingManager** (`backend/nn/coach_manager.py`) -- controlla il gate di maturita per ChronovisorScanner
- **FeatureExtractor** (`backend/processing/feature_engineering/vectorizer.py`) -- produce il vettore metadata a 25 dimensioni
- **RAPStateReconstructor** (`backend/processing/state_reconstructor.py`) -- converte i dati tick grezzi in batch di tensori pronti per il modello
- **SuperpositionLayer** (`backend/nn/layers/superposition.py`) -- livello lineare modulato dal contesto usato dagli esperti di RAPStrategy
- **Persistence** (`backend/nn/persistence.py`) -- `load_nn("rap_coach", model)` / `save_nn()` per la gestione dei checkpoint
- **Structured Logging** -- tutti i moduli usano `get_logger("cs2analyzer.nn.experimental.rap_coach.<modulo>")`

## Dipendenze

| Pacchetto | Scopo | Opzionale? |
|-----------|-------|------------|
| `torch` | Operazioni tensoriali core, nn.Module | Obbligatorio |
| `ncps` | Neuroni LTC, cablaggio AutoNCP | Opzionale (protetto da `_RAP_DEPS_AVAILABLE`) |
| `hflayers` | Memoria associativa Hopfield | Opzionale (protetto da `_RAP_DEPS_AVAILABLE`) |
| `numpy` | Elaborazione segnale in ChronovisorScanner | Obbligatorio |
| `sqlmodel` | Query database in ChronovisorScanner | Obbligatorio (al momento della scansione) |

Quando `ncps` / `hflayers` non sono installati, `RAPMemoryLite` (fallback basato su LSTM) e
disponibile tramite `use_lite_memory=True` in `RAPCoachModel.__init__()`.

## Note di Sviluppo

- Questo pacchetto (`backend/nn/rap_coach/`) contiene solo **shim di compatibilita**.
  Tutta l'implementazione canonica risiede in `backend/nn/experimental/rap_coach/`.
- Il feature flag `USE_RAP_MODEL` e impostato su `False` per default. Il modello primario in produzione e JEPA.
- Modificare `ncp_units` o `hidden_dim` invalida i checkpoint esistenti. Il caricamento
  con controllo di versione in `load_nn()` rileva le discrepanze architetturali tramite `StaleCheckpointError`.
- Lo stato RNG per il cablaggio AutoNCP viene esplicitamente salvato e ripristinato (`seed=42`)
  per garantire una topologia di rete deterministica e portabile tra checkpoint (NN-45 + NN-MEM-02).
- Il trainer usa una loss a 4 componenti pesate: strategy (1.0), value (0.5), sparsity (1.0),
  position (1.0). Gli errori di posizione sull'asse Z sono penalizzati con peso 2x (NN-TR-02b).
- Il livello di comunicazione sopprime i consigli quando la confidenza del modello e sotto la soglia di 0.7.
