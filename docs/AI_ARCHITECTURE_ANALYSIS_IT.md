# CS2 Coach AI — Analisi Completa dell'Architettura

> **Data:** 17 marzo 2026
> **Ambito:** Audit completo dell'architettura AI/ML — reti neurali, teoria dei giochi, pipeline di coaching, orchestrazione dell'addestramento, pipeline dati, schema del database, generazione dei tensori, motore di inferenza
> **Scopo:** Documento di riferimento completo per comprendere ogni componente del sistema AI

---

## Indice

1. [Il Vettore delle Feature (METADATA_DIM = 25)](#1-il-vettore-delle-feature)
2. [Pipeline Dati: Dalla Demo alle Feature](#2-pipeline-dati)
3. [Schema del Database](#3-schema-del-database)
4. [JEPA — Pre-addestramento Auto-Supervisionato](#4-jepa)
5. [VL-JEPA — Concetti di Coaching Interpretabili](#5-vl-jepa)
6. [RAP Coach — Il Cervello del Giocatore Fantasma](#6-rap-coach)
7. [Coach Legacy (AdvancedCoachNN)](#7-coach-legacy)
8. [Tensor Factory — Input Visivi](#8-tensor-factory)
9. [Motori di Teoria dei Giochi](#9-motori-di-teoria-dei-giochi)
10. [Pipeline di Coaching COPER](#10-pipeline-di-coaching-coper)
11. [Orchestratore di Analisi (Fase 6)](#11-orchestratore-di-analisi)
12. [Orchestrazione dell'Addestramento (5 Fasi)](#12-orchestrazione-delladdestramento)
13. [Model Factory e Caricamento dei Checkpoint](#13-model-factory)
14. [GhostEngine — Inferenza](#14-ghostengine)
15. [Decodifica Selettiva e Inferenza con Stato](#15-decodifica-selettiva)
16. [Motore di Sessione Tri-Daemon](#16-motore-di-sessione)
17. [Costanti Dimensionali Chiave](#17-costanti-chiave)
18. [Valutazione Ingegneristica Onesta](#18-valutazione-onesta)

---

## 1. Il Vettore delle Feature

**File:** `backend/processing/feature_engineering/vectorizer.py`

Ogni tick di ogni demo viene compresso in un vettore di 25 numeri. Questo è il linguaggio universale che tutti i modelli parlano.

| Indice | Feature | Intervallo | Normalizzazione |
|--------|---------|-----------|-----------------|
| 0 | health | 0-1 | / 100 |
| 1 | armor | 0-1 | / 100 |
| 2 | has_helmet | 0/1 | binario |
| 3 | has_defuser | 0/1 | binario |
| 4 | equipment_value | 0-1 | / 10.000 |
| 5 | is_crouching | 0/1 | binario |
| 6 | is_scoped | 0/1 | binario |
| 7 | is_blinded | 0/1 | binario |
| 8 | enemies_visible | 0-1 | conteggio / 5 |
| 9 | pos_x | da -1 a 1 | / 4.096 |
| 10 | pos_y | da -1 a 1 | / 4.096 |
| 11 | pos_z | da -1 a 1 | / 1.024 |
| 12 | view_yaw_sin | da -1 a 1 | sin(yaw) — codifica ciclica che evita la discontinuità 359-0 |
| 13 | view_yaw_cos | da -1 a 1 | cos(yaw) — accoppiato al sin per rotazione fluida |
| 14 | view_pitch | da -1 a 1 | / 90 |
| 15 | z_penalty | 0-1 | distinzione del livello verticale |
| 16 | kast_estimate | 0-1 | rapporto Kill/Assist/Survive/Trade |
| 17 | map_id | 0-1 | MD5 hash % 10000 / 10000 (deterministico per mappa) |
| 18 | round_phase | 0/0.33/0.66/1 | pistol/eco/force/full buy |
| 19 | weapon_class | 0-1 | knife=0, pistol=0.2, SMG=0.4, rifle=0.6, sniper=0.8, heavy=1.0 |
| 20 | time_in_round | 0-1 | tempo trascorso / 115 secondi |
| 21 | bomb_planted | 0/1 | binario |
| 22 | teammates_alive | 0-1 | conteggio / 4 |
| 23 | enemies_alive | 0-1 | conteggio / 5 |
| 24 | team_economy | 0-1 | denaro medio squadra / 16.000 |

**Soglie delle fasi di round** (da `base_features.py`):
- Eco: denaro squadra < $1.500
- Force: $1.500 - $3.000
- Force-buy: $3.000 - $4.000
- Full buy: > $4.000

---

## 2. Pipeline Dati

**File:** `ingestion/demo_loader.py`

### Parsing delle Demo in 3 Passate

Ogni file `.dem` viene processato attraverso tre passate sequenziali utilizzando la libreria `demoparser2`:

**Passata 1 — Estrazione delle Posizioni:**
- Estrae le posizioni dei giocatori ad ogni tick
- Costruisce `pos_by_tick[tick] = {steamid: (x, y, z)}`
- Leggera — solo coordinate

**Passata 2 — Collegamento delle Granate:**
- Processa gli eventi di inizio/fine delle granate
- Associa i dati di lancio alla traiettoria e all'impatto
- Traccia: `base_id`, `nade_type`, `x/y/z`, `starting_tick`, `ending_tick`, `throw_tick`, `trajectory`, `thrower_id`
- Limite euristico: le granate senza evento di fine vengono limitate a 20 × tick_rate (flag `is_duration_estimated = True`)
- Finestra di dissolvenza: 5 × tick_rate

**Passata 3 — Estrazione Completa dello Stato:**
- Costruisce oggetti PlayerState completi a 25 campi per tick
- Segmentazione multi-mappa (rileva cambi di mappa all'interno di una singola demo)
- Utilizza gli eventi `round_freeze_end` per rilevare i confini dei round
- Risoluzione del denaro: coalescenza tra varianti di campo (`balance`, `cash`, `money`, `m_iAccount`)
- Risoluzione della squadra: corrispondenza di stringhe vettorizzata (CT/TER/SPEC)

### Sistema di Cache
- Versione cache: `v21_vectorized_parse` (colonne pre-vettorizzate per velocità 10x)
- Firmata con HMAC e scrittura atomica (previene la corruzione)
- Unpickler sicuro limitato alle sole classi del modulo `demo_frame` (sicurezza)
- Invalidazione della cache: discrepanza dimensione file + stringa versione

### Arricchimento dei Tick (Feature 20-24)
Dopo il parsing, ogni tick viene arricchito con feature contestuali:
- `time_in_round`: calcolato dal tick di inizio round
- `bomb_planted`: dagli eventi di gioco
- `teammates_alive` / `enemies_alive`: dallo stato dei giocatori a livello di tick
- `team_economy`: media tra i membri della squadra

### Strategia di Suddivisione dei Dati
- Suddivisione **cronologica 70/15/15** per data della partita (previene la fuga temporale)
- **Decontaminazione dei giocatori**: ogni giocatore appare in UNA SOLA suddivisione
- **Rimozione degli outlier**: IQR 3.0x (recinzione esterna di Tukey)
- **StandardScaler**: adattato solo sulla suddivisione di addestramento, applicato a validazione/test

---

## 3. Schema del Database

**File:** `backend/storage/db_models.py`

Tutti i database utilizzano SQLite in modalità WAL (Write-Ahead Logging) per l'accesso concorrente.

### PlayerMatchStats (aggregati a livello di partita)
25 campi statistici per giocatore per partita:
- **Core:** kill, morti, ADR, percentuale headshot, KAST
- **Varianza:** kill_std, adr_std, rapporto K/D
- **Duelli:** opening_duel_win_pct, clutch_win_pct, trade_kill_ratio
- **Utility:** flash_assists, danni HE/round, danni molotov/round, smoke/round
- **Rating HLTV 2.0:** impatto, sopravvivenza, KAST, KPR, ADR
- **Flag:** `is_pro` (booleano), `dataset_split` (train/val/test), `data_quality` (stringa)

### PlayerTickState (stato per-tick, ~17,3M righe per 11 demo)
19 campi per tick per giocatore:
- Posizione (x, y, z), angoli di visuale (codifica sin/cos), salute, armatura
- Accovacciato, mirino, accecato, arma attiva, valore equipaggiamento
- Nemici visibili, numero round, tempo nel round, bomba piazzata
- Compagni vivi, nemici vivi, economia della squadra, nome mappa

### RoundStats (per-round per-giocatore)
- Kill, morti, assist, danno inflitto, kill con headshot
- Trade kill, è stato tradato, primo kill/prima morte
- Utility: danno HE, danno molotov, flash lanciate, smoke lanciati
- Valore equipaggiamento, round vinto, MVP, valutazione del round

### CoachingExperience (Banca dell'Esperienza per COPER)
- Contesto: mappa, fase del round, lato, area di posizione
- Stato di gioco: snapshot JSON (massimo 16KB)
- Azione/risultato: cosa è stato fatto, esito (kill/morte/trade/obiettivo/sopravvissuto)
- Riferimento pro: nome giocatore + ID partita
- Embedding: vettore 384-dim (codificato in JSON)
- Ciclo di feedback: punteggio di efficacia, volte seguito

### CoachState (singleton, id=1)
- Stato dell'addestramento (In pausa/In addestramento/Inattivo/Errore)
- Epoca corrente, epoche totali, loss di addestramento/validazione, tempo stimato
- Heartbeat, carico CPU/memoria del sistema
- Maturità: total_matches_processed

### ProPlayerStatCard (statistiche HLTV)
- Rating 2.0, DPR, KAST, impatto, ADR, KPR, percentuale headshot
- Rapporto opening kill, vittorie in clutch, round con multi-kill
- Periodo: all_time / last_3_months / 2024

### TacticalKnowledge (base di conoscenza RAG)
- Titolo, descrizione, categoria (positioning/economy/utility/aim)
- Mappa, contesto situazionale, esempio pro
- Embedding: vettore 384-dim per ricerca per similarità

### DataLineage (traccia di audit)
- Solo in aggiunta: traccia ogni entità fino alla demo sorgente, tick, versione della pipeline

---

## 4. JEPA

**File:** `backend/nn/jepa_model.py`
**Acronimo di:** Joint-Embedding Predictive Architecture (da Yann LeCun / Meta AI)

### Scopo
Apprendere rappresentazioni degli stati di gioco senza etichette. Osserva le demo dei professionisti e impara come appare il "gioco normale e competente" in uno spazio latente compresso a 256 dimensioni.

### Come Funziona (Concettuale)
Data una finestra di tick di gioco (il "contesto"), predice come apparirà la finestra SUCCESSIVA (il "bersaglio") — ma nella rappresentazione compressa a 256-dim, non nelle feature grezze a 25-dim. Questo costringe il modello a comprendere causa-effetto in CS2: "Se un giocatore è qui con quest'arma e vede due nemici, cosa succede dopo?"

### Architettura

```
JEPACoachingModel
├── Encoder del Contesto (JEPAEncoder) — addestrato tramite gradiente
│   └── Linear(25→512) + LayerNorm + GELU + Dropout(0.1)
│       Linear(512→256) + LayerNorm
│       Output: [B, seq_len, 256]
│
├── Encoder del Bersaglio (stessa architettura) — solo EMA, NESSUN gradiente
│   └── Aggiornato: target = 0.996 × target + 0.004 × context
│       Non riceve mai gradienti. Copia lentamente dall'encoder del contesto.
│
├── Predittore (JEPAPredictor) — mappa il contesto al bersaglio predetto
│   └── Linear(256→512) + LayerNorm + GELU + Dropout(0.1)
│       Linear(512→256)
│       Input: media pooling del contesto [B, 256]
│       Output: bersaglio predetto [B, 256]
│
├── Testa di Coaching LSTM (2 strati, hidden=128, dropout=0.2)
│   └── Input: [B, seq_len, 256] dall'encoder del contesto
│       Output: [B, seq_len, 128] elaborazione temporale
│
├── Miscela di Esperti (3 esperti) — coaching specializzato
│   └── Gate: Linear(128→3) + Softmax → "di quale esperto fidarsi?"
│       Esperto 1: Linear(128→128) + ReLU + Linear(128→10)
│       Esperto 2: stessa architettura
│       Esperto 3: stessa architettura
│       Somma pesata degli output degli esperti
│
└── Output: tanh([B, 10]) → vettore di coaching in [-1, 1]
```

### Protocollo di Addestramento in Due Stadi

**Stadio 1 — Pre-addestramento JEPA (auto-supervisionato, nessuna etichetta necessaria):**

```
Sequenze di tick da demo professionali
    │
    ├── Finestra di contesto [B, context_len, 25]
    │         │
    │         ▼
    │   Encoder del Contesto → [B, context_len, 256]
    │         │
    │         ▼
    │   Media Pooling → [B, 256]
    │         │
    │         ▼
    │   Predittore → predicted_target [B, 256]
    │
    └── Finestra bersaglio [B, target_len, 25]
              │
              ▼
        Encoder del Bersaglio (no_grad) → [B, target_len, 256]
              │
              ▼
        Media Pooling → real_target [B, 256]

Loss: "Il predicted_target è più vicino al real_target
       che a bersagli casuali?"
       → Loss contrastiva InfoNCE
```

**Stadio 2 — Fine-tuning (supervisionato, necessita etichette di coaching):**
- Congela entrambi gli encoder (`requires_grad = False`)
- Addestra solo LSTM + esperti MoE su obiettivi di coaching con loss MSE
- Gli encoder diventano estrattori di feature fissi

### Loss InfoNCE (Passo per Passo)

```
1. Normalizza tutto sulla sfera unitaria (norma L2):
   pred    = normalize(pred)        → vettori unitari [B, 256]
   target  = normalize(target)      → vettori unitari [B, 256]
   negs    = normalize(negatives)   → vettori unitari [B, K, 256]

2. Similarità positiva (quanto è vicina la predizione al bersaglio REALE?):
   pos_sim = dot_product(pred, target) / 0.07
   La divisione per temperatura=0.07 rende la distribuzione più netta

3. Similarità negative (quanto è vicina la predizione ai bersagli SBAGLIATI?):
   neg_sim = dot_product(pred, each_negative) / 0.07
   [B, K] — un punteggio per negativo per campione

4. Impila in logit di classificazione:
   logits = [pos_sim, neg_sim₁, neg_sim₂, ..., neg_simₖ]
   [B, K+1] — la posizione 0 è la risposta corretta

5. Loss cross-entropy:
   labels = [0, 0, 0, ...] (la classe corretta è sempre all'indice 0)
   loss = -log(exp(pos_sim) / (exp(pos_sim) + Σexp(neg_sim)))
```

### Negativi In-Batch (O(B²) — Nessuna Memoria Extra Necessaria)

```
Per un batch di dimensione B, codifica tutte le B finestre bersaglio:
  all_encoded = target_encoder(x_target).mean(dim=1)  → [B, 256]

Per il campione i, i negativi = tutti gli ALTRI campioni:
  negatives[i] = all_encoded[j] per ogni j ≠ i   → [B-1, 256]

Risultato: [B, B-1, 256] — ogni campione ha B-1 negativi gratuitamente
Salta i batch dove B < 2 (servono almeno 2 campioni per il contrasto)
```

### Aggiornamento EMA (Meccanismo Anti-Collasso)

Dopo ogni passo di addestramento:
```
target_weights = 0.996 × target_weights + 0.004 × context_weights
```

**Perché?** Senza questo meccanismo, il modello può "collassare" — produrre lo stesso embedding per tutto (similarità banalmente perfetta = loss zero, ma inutile). L'encoder del bersaglio RESTA INDIETRO rispetto all'encoder del contesto di circa 250 passi (1/0.004), creando un bersaglio mobile che impedisce il collasso.

**Controllo di sicurezza (NN-JM-04):** Prima di ogni aggiornamento EMA, verifica che `target_encoder.requires_grad == False`. Se violato → `RuntimeError` immediato.

### Monitor di Salute degli Embedding (P9-02)
```
variance = embeddings.var(dim=0).mean()
se variance < 0.01 → ATTENZIONE: rischio di collasso (tutti gli embedding convergono)
se variance ≥ 0.01 → sano (gli embedding sono distribuiti nello spazio)
```

### Rilevamento della Deriva e Ri-addestramento Automatico
- Monitora i punteggi Z dei dati di validazione rispetto alle statistiche di riferimento dell'addestramento
- Punteggio Z > 2.5 → deriva rilevata (il meta di gioco è cambiato)
- 5 controlli di deriva consecutivi → attiva il ri-addestramento completo (10 epoche)
- Resetta lo scheduler del learning rate e la cronologia delle derive dopo il ri-addestramento

---

## 5. VL-JEPA

**File:** `backend/nn/jepa_model.py` (classe `VLJEPACoachingModel`, estende `JEPACoachingModel`)

### Scopo
Estende JEPA con 16 concetti di coaching interpretabili affinché il modello possa spiegare PERCHÉ fornisce consigli specifici. Invece di un semplice vettore di coaching a 10 numeri, si ottiene: "Questo tick è 80% positioning_exposed, 60% engagement_unfavorable."

### 16 Concetti di Coaching

| ID | Concetto | Categoria | Significato |
|----|----------|-----------|-------------|
| 0 | positioning_aggressive | Posizionamento | Spingere gli angoli, combattimenti ravvicinati |
| 1 | positioning_passive | Posizionamento | Tenere angoli lunghi, evitare il contatto |
| 2 | positioning_exposed | Posizionamento | Posizione vulnerabile, alto rischio di morte |
| 3 | utility_effective | Utility | Granate che creano un vero vantaggio |
| 4 | utility_wasteful | Utility | Morire con utility inutilizzata, basso impatto |
| 5 | economy_efficient | Decisione | Equipaggiamento coerente con le aspettative del round |
| 6 | economy_wasteful | Decisione | Force-buy in round sfavorevoli |
| 7 | engagement_favorable | Ingaggio | Combattimenti con vantaggio di HP/posizione/numeri |
| 8 | engagement_unfavorable | Ingaggio | In inferiorità numerica, HP bassi, angoli sfavorevoli |
| 9 | trade_responsive | Ingaggio | Trade rapidi dei compagni, buon coordinamento |
| 10 | trade_isolated | Ingaggio | Morire senza trade, troppo lontano dalla squadra |
| 11 | rotation_fast | Decisione | Rotazione posizionale rapida dopo raccolta di informazioni |
| 12 | information_gathered | Decisione | Buona ricognizione, più nemici avvistati |
| 13 | momentum_leveraged | Psicologia | Capitalizzare sulle serie positive |
| 14 | clutch_composed | Psicologia | Decisioni calme nelle situazioni 1vN |
| 15 | aggression_calibrated | Psicologia | Livello di aggressività adeguato alla situazione |

### Come Funzionano i Concetti

```
Stato di gioco [B, seq_len, 25]
  │
  ▼
Encoder del Contesto → [B, seq_len, 256]
  │
  ▼
Media Pooling → [B, 256]
  │
  ▼
Proiettore dei Concetti: Linear(256→256) + GELU + Linear(256→256) + normalizzazione L2
  │
  ▼
proiettato [B, 256] (vettore unitario sulla sfera)

Confronto con 16 Embedding di Concetti apprendibili [16, 256]:
  cosine_similarity = proiettato × concept_embeddings.T  → [B, 16]

Scalatura della temperatura (apprendibile, inizializzata a 0.07, limitata [0.01, 1.0]):
  logits_scaled = cosine_similarity / temperature

Softmax → [B, 16] distribuzione di probabilità sui concetti
```

### Due Modi per Generare le Etichette dei Concetti

**Basato sui risultati (preferito, nessuna fuga di dati):** Utilizza i dati di RoundStats — kill, morti, danno, round vinto/perso, trade kill, utilizzo utility. Esempi:
- Opening kill ottenuto + sopravvissuto → `positioning_aggressive = 0.8`
- Morto per primo con < 40 di danno → `positioning_exposed = 0.6`
- Round eco vinto con < $2000 di equipaggiamento → `economy_efficient = 0.9`
- Trade kill > 0 → `trade_responsive = 0.6 + 0.2 per kill`

**Fallback euristico (rischio di fuga di etichette):** Deriva le etichette dalle stesse feature di input a 25-dim. Il modello può "barare" ricostruendo la mappatura input→etichetta. Un avviso viene registrato quando si utilizza questo percorso.

### Funzione di Loss di VL-JEPA
```
total_loss = InfoNCE + α × concept_BCE + β × diversity_loss

Dove:
  concept_loss = Binary Cross-Entropy(logits, soft_labels)
    Ogni concetto è una classificazione binaria indipendente (multi-etichetta, non one-hot)

  diversity_loss = -media(std_per_dimensione(concept_embeddings))
    Penalizza tutti i 16 concetti che si raggruppano nello stesso punto
    Ispirato da VICReg (Variance-Invariance-Covariance Regularization)

Pesi predefiniti: α=0.5, β=0.1
```

---

## 6. RAP Coach

**File:** `backend/nn/experimental/rap_coach/`
**Acronimo di:** Recurrent Attention-based Pedagogy (Pedagogia Basata sull'Attenzione Ricorrente)

### Scopo
Un "cervello da giocatore fantasma" a 7 strati che prende tensori visivi (mappa, visuale, movimento) + metadati, e produce: dove dovresti stare, cosa dovresti fare, quanto è buona la tua situazione, e perché stai commettendo errori.

### Strato 1: PERCEZIONE (perception.py)

Tre flussi di elaborazione visiva ispirati alle neuroscienze (percorso ventrale "cosa" / percorso dorsale "dove"):

```
Frame di Visuale [B, 3, H, W]  (cosa vedo?)
  → Backbone ResNet: Conv2d(3→64, stride=2) + BatchNorm + ReLU
    + 4 blocchi residuali (64→64), ciascuno: conv3×3→BN→ReLU→conv3×3→BN + scorciatoia
  → AdaptiveAvgPool2d(1,1) → [B, 64]

Frame della Mappa [B, 3, H, W]  (dove sono sulla mappa?)
  → Backbone ResNet: Conv2d(3→32, stride=2) + BatchNorm + ReLU
    + 3 blocchi residuali (32→32)
  → AdaptiveAvgPool2d(1,1) → [B, 32]

Frame di Movimento [B, 3, H, W]  (cosa si muove?)
  → Conv2d(3→16, 3×3) + ReLU + MaxPool2d(2)
  → Conv2d(16→32, 3×3) + ReLU
  → AdaptiveAvgPool2d(1,1) → [B, 32]

Concatenazione di tutti e tre: [64 + 32 + 32] = [B, 128] vettore di percezione
```

### Strato 2: MEMORIA (memory.py)

**Rete Liquid Time-Constant (LTC):**
- Neuroni ispirati al cervello con costanti temporali ADATTIVE — rispondono diversamente a cambiamenti rapidi e lenti
- Utilizza `AutoNCP(units=512, output_size=256)` — cablaggio di Neural Circuit Policy sparso e biologicamente plausibile
- Input: [B, T, 153] (128 percezione + 25 metadati concatenati)
- Proprietà chiave: gestisce naturalmente frame rate variabili (le demo di CS2 non sono sempre a 64 tick/s)
- RNG seminato deterministicamente: `np.random.seed(42)` + `torch.manual_seed(42)`

**Memoria Associativa di Hopfield:**
- 4 teste di attenzione, dimensione dei pattern 256
- Pensala come: memorizza "situazioni prototipo" (giocate tattiche perfette)
- Pattern inizializzati casualmente (randn × 0.02), modellati solo dalla discesa del gradiente durante l'addestramento
- **Guardia di sicurezza:** Resta DISATTIVATA per le prime 2 passate forward di addestramento (pattern casuali aggiungerebbero rumore)
- Dopo 2 passate → `_hopfield_trained = True` → Hopfield si attiva
- Combinata con LTC tramite connessione residua: `output = ltc_output + hopfield_output`

**Testa di Credenza (comprensione interna della situazione):**
```
Linear(256→256) → SiLU → Linear(256→64)
Output: [B, T, 64] — la comprensione compressa del modello della situazione corrente
```

### Strato 3: STRATEGIA (strategy.py)

4 Miscele di Esperti con Strati a Superposizione a gate contestuale:

```
Per ciascuno dei 4 esperti:
  SuperpositionLayer(256→128, context=25) → ReLU → Linear(128→10)

Gate: Linear(256→4) → Softmax → [B, 4] pesi degli esperti

Finale = Σ(output_esperto × peso_gate) → [B, 10] vettore strategico
```

**Strato a Superposizione** (il meccanismo di gating):
```python
out = F.linear(x, weight, bias)         # Lineare standard: [B, 128]
gate = sigmoid(context_gate(metadata))   # Il contesto determina la rilevanza: [B, 128]
return out * gate                        # Elemento per elemento: neuroni irrilevanti soppressi
```

### Strato 4: VALUTAZIONE (pedagogy.py)

**Critico (funzione di valore):**
```
Linear(256→64) → ReLU → Linear(64→1) → V(s)
"Quanto è buono questo stato di gioco?" (scalare singolo)
```

**Adattatore di Abilità:**
```
Linear(10→256)
Se skill_vec fornito: hidden = hidden + skill_adapter(skill_vec)
Sposta le aspettative del modello in base al livello di abilità del giocatore (scala 1-10)
```

### Strato 5: POSIZIONAMENTO

```
Linear(256→3) → [dx, dy, dz]
In inferenza, scalato per RAP_POSITION_SCALE = 500.0 unità di gioco
ghost_x = current_x + dx × 500.0
ghost_y = current_y + dy × 500.0
```

**L'asse Z riceve una penalità 2x** durante l'addestramento perché trovarsi sul piano sbagliato in CS2 = morte istantanea.

### Strato 6: ATTRIBUZIONE

Spiegazione dell'errore a 5 canali: **Posizionamento, Mira, Aggressività, Utility, Rotazione**

```
Testa di Rilevanza: Linear(256→32) → ReLU → Linear(32→5) → Sigmoid → [B, 5]

Combina pesi di rilevanza neurali con misurazioni meccaniche dell'errore:
  attribution[0] = relevance[0] × ||position_delta||     (Posizionamento)
  attribution[1] = relevance[1] × ||aim_delta||           (Mira)
  attribution[2] = relevance[2] × ||pos_delta|| × 0.5     (Aggressività)
  attribution[3] = relevance[3] × sigmoid(hidden.mean())  (Utility — solo neurale)
  attribution[4] = relevance[4] × ||pos_delta|| × 0.8     (Rotazione)
```

### Loss di Addestramento RAP

```
total = 1.0 × MSE(strategy_pred, strategy_target)
      + 0.5 × MSE(value_pred, value_target)       (con mascheramento per dati mancanti)
      + 1.0 × L1(gate_weights) × 1e-4             (regolarizzazione di sparsità)
      + 1.0 × weighted_MSE(position_pred, position_target)
              dove peso asse Z = 2.0

Clipping del gradiente: max_norm = 1.0
Ottimizzatore: AdamW(lr=5e-5, weight_decay=1e-4)
```

### Dizionario di Output Completo di RAP
```python
{
    "advice_probs":    [B, 10],    # Raccomandazioni strategiche (10 ruoli tattici)
    "belief_state":    [B, T, 64], # Comprensione interna della situazione
    "value_estimate":  [B, 1],     # Quanto è buono questo stato? (scalare)
    "gate_weights":    [B, 4],     # Quale esperto ha dominato la decisione?
    "optimal_pos":     [B, 3],     # Dove DOVRESTI stare (delta)
    "attribution":     [B, 5],     # Perché stai perdendo (5 canali)
    "hidden_state":    (tuple),    # Memoria LSTM persistente per il tick successivo
}
```

---

## 7. Coach Legacy

**File:** `backend/nn/model.py`

Il modello di ripiego più semplice (AdvancedCoachNN / TeacherRefinementNN):

```
Input [B, seq, 25]
  │
  ▼
LSTM(25→128, 2 strati, dropout=0.2)
  │
  ▼
LayerNorm(128)
  │
  ▼
3 Esperti MoE:
  Ciascuno: Linear(128→128) + LayerNorm + ReLU + Linear(128→10)
  Gate: Linear(128→3) + Softmax
  │
  ▼
tanh → [B, 10] output di coaching
```

**Biasing del ruolo:** Quando viene fornito un role_id (0, 1 o 2):
```
role_bias = [0, 0, 0] con role_bias[role_id] = 1.0
new_weights = (gate_weights + role_bias) / 2.0
→ L'esperto preferito viene potenziato da ~33% a ~65%
```

---

## 8. Tensor Factory

**File:** `backend/processing/tensor_factory.py`

Genera 3 input visivi sotto forma di tensori (mappa, visuale, movimento) per il modello RAP Coach.

### Risoluzioni
- **Addestramento:** 64×64 (ridotta per velocità)
- **Inferenza:** mappa=128×128, visuale=224×224

### Tensore Mappa — Panoramica Tattica (3 canali)

| Canale | Modalità POV Giocatore | Modalità Legacy |
|--------|------------------------|-----------------|
| Ch0 | Posizioni compagni (heatmap) | Posizioni nemici |
| Ch1 | Posizioni nemici (visibili + ultime note con decadimento) | Posizioni compagni |
| Ch2 | Zone utility + marcatore bomba (raggio 50 unità) | Posizione giocatore |

### Tensore Visuale — Prospettiva del Giocatore (3 canali)

| Canale | Modalità POV Giocatore | Modalità Legacy |
|--------|------------------------|-----------------|
| Ch0 | Maschera FOV (cono 90°, pesata per coseno, sfocatura gaussiana) | Maschera FOV |
| Ch1 | Entità visibili (heatmap attenuata dalla distanza) | Zone di pericolo |
| Ch2 | Zone utility attive | Zone sicure |

**Maschera FOV:** Cono dal yaw del giocatore ± 45°, con sfocatura gaussiana (sigma=3.0). Distanza di visione = 2000 unità di gioco.

### Tensore Movimento — Contesto di Movimento (3 canali)

| Canale | Contenuto |
|--------|-----------|
| Ch0 | Scia della traiettoria (ultimi 32 tick, gradiente di recenza) |
| Ch1 | Gradiente radiale della velocità (massimo 4.0 unità/tick a 64Hz) |
| Ch2 | Movimento del mirino (delta yaw, massimo 45° per tick) |

### Normalizzazione (P-TF-01)
Quando il valore massimo è < 1.0, divide per 1.0 (non per il massimo) per evitare l'amplificazione del rumore. Preserva la magnitudine relativa dei segnali deboli.

---

## 9. Motori di Teoria dei Giochi

### 9.1 Probabilità di Morte Bayesiana

**File:** `backend/analysis/belief_model.py`

Stima "quanto è probabile che questo giocatore muoia proprio adesso?" utilizzando il ragionamento bayesiano.

**Prior per fascia di HP:**
- Piena (80-100 HP): 35% tasso di morte base
- Danneggiato (40-79 HP): 55% tasso di morte base
- Critico (1-39 HP): 80% tasso di morte base

**Moltiplicatori di letalità delle armi:** rifle=1.0, AWP=1.4, SMG=0.75, pistol=0.6, shotgun=0.85, knife=0.3

**Calcolo del livello di minaccia:**
```
threat = (visible_enemies + inferred_enemies × e^(-0.1 × info_age_seconds) × 0.5) / 5.0
```
I nemici dedotti perdono rilevanza nel tempo (decadimento esponenziale con λ=0.1/s).

**Aggiornamento log-odds (posteriore bayesiano):**
```
log_odds = ln(prior / (1-prior))
  + threat × 2.0                        [più nemici = più pericolo]
  + (weapon_mult - 1.0) × 1.5           [AWP = +0.6, pistol = -0.6]
  + (armor_factor - 1.0) × -1.0         [l'armatura riduce il tasso di morte]
  + (exposure_factor - 0.5) × 1.0       [dipendente dalla posizione]

P(morte) = 1 / (1 + e^(-log_odds))      [conversione sigmoide]
```

**Auto-calibrazione** dai dati reali delle partite (minimo 30 campioni totali, 10 per fascia):
- Ricalibra i prior delle fasce di HP dai tassi di morte osservati
- Adatta la letalità per classe di arma dai conteggi di kill effettivi
- Adatta il decadimento della minaccia λ tramite minimi quadrati su info_age → esito
- Tutti i parametri limitati: prior [0.05, 0.95], letalità [0.1, 3.0], decadimento [0.01, 1.0]
- Salva CalibrationSnapshot nel database (osservabilità)

### 9.2 Albero di Gioco Expectiminimax

**File:** `backend/analysis/game_tree.py`

Ricerca minimax ricorsiva con modellazione stocastica dell'avversario — la stessa famiglia di algoritmi usata nell'AI per gli scacchi e nei bot per il poker.

**4 Azioni Disponibili:** push, hold, rotate, use_utility

**Struttura dell'albero:**
```
Radice (MAX — la nostra squadra sceglie l'azione migliore)
  ├── PUSH → Nodo Casuale (l'avversario risponde probabilisticamente)
  │            ├── avversario PUSH (p=0.30) → valuta foglia
  │            ├── avversario HOLD (p=0.40) → valuta foglia
  │            ├── avversario ROTATE (p=0.20) → valuta foglia
  │            └── avversario UTILITY (p=0.10) → valuta foglia
  ├── HOLD → Nodo Casuale ...
  ├── ROTATE → Nodo Casuale ...
  └── USE_UTILITY → Nodo Casuale ...
```

**Aggiustamenti delle probabilità dell'avversario per contesto:**

| Condizione | Push | Hold | Rotate | Utility |
|------------|------|------|--------|---------|
| Round eco (<$2000) | +25% | -25% | — | +15% |
| Full buy (>$4000) | -5% | +10% | +5% | — |
| Avversario T-side | +5% | -5% | — | — |
| In inferiorità numerica | -5% | +10% | — | -10% |
| Tempo < 30 secondi | +15% | -10% | — | +5% |
| Profilo appreso (≥10 round) | blend fino a 70% appreso | 30% base | | |

**Transizioni di stato per azione:**
- PUSH: -1 vivo per lato, +0.15 controllo mappa
- HOLD: -15 secondi di tempo
- ROTATE: -10s tempo, ±0.1 controllo mappa
- USE_UTILITY: -1 oggetto utility, +0.05 controllo mappa

**Budget:** Massimo 1.000 nodi (previene OOM). Tabella di trasposizione: 10.000 voci con evizione FIFO.

**Output:** Azione migliore + probabilità di vittoria stimata per lo stato corrente.

### 9.3 Tracker del Momentum

**File:** `backend/analysis/momentum.py`

Traccia il momentum psicologico come un moltiplicatore tra 0.7 (in tilt) e 1.4 (on fire, in serie positiva):

```
Serie di vittorie di N:  moltiplicatore = 1.0 + 0.05 × N × e^(-0.15 × round_gap)
Serie di sconfitte di N: moltiplicatore = 1.0 - 0.04 × N × e^(-0.15 × round_gap)

Limiti: [0.7 (tilt massimo), 1.4 (caldo massimo)]
Soglia di tilt: < 0.85 (~3 sconfitte consecutive)
Soglia caldo: > 1.2 (~4 vittorie consecutive)
Reset al cambio campo (round 13 per MR12, round 16 per MR13)
```

### 9.4 Analisi dell'Entropia

**File:** `backend/analysis/entropy_analysis.py`

Misura l'efficacia dell'utility in **bit di informazione** utilizzando l'entropia di Shannon:

```
1. Discretizza la mappa in una griglia 32×32 (1.024 celle)
2. Conta le posizioni dei nemici per cella PRIMA dell'utility
3. H_before = -Σ(pᵢ × log₂(pᵢ)) per le celle occupate
4. Conta le posizioni DOPO l'atterraggio dell'utility
5. H_after = stessa formula
6. delta = H_before - H_after (positivo = informazione guadagnata)
7. effectiveness = delta / max_delta
```

**Delta massimi per tipo di utility:**
- Smoke: 2.5 bit (blocca la linea di vista per ~18s)
- Molotov: 2.0 bit (negazione di area per ~7s)
- Flash: 1.8 bit (finestra di accecamento di 3s)
- HE: 1.5 bit (rivelazione momentanea della posizione)

### 9.5 Indice di Inganno

**File:** `backend/analysis/deception_index.py`

```
composite = 0.25 × flash_bait_rate + 0.40 × rotation_feint_rate + 0.35 × sound_deception_score
```

- **Flash esca (25%):** % di flash che non accecano nessuno entro 128 tick (~2 secondi)
- **Finte di rotazione (40%):** Cambi di direzione > 108° relativi all'estensione della mappa (peso maggiore — l'inganno posizionale è il più importante)
- **Inganno sonoro (35%):** Inverso del rapporto di accovacciamento (meno accovacciamento = più rumore = potenziale guerra informativa)

### 9.6 Probabilità di Vittoria

**File:** `backend/analysis/win_probability.py`

Piccola rete neurale per la predizione della vittoria del round in tempo reale:

```
12 feature → Linear(64) + ReLU + Dropout(0.2)
           → Linear(32) + ReLU + Dropout(0.1)
           → Linear(1) + Sigmoid → [0, 1]
```

**Le 12 feature di input:**
0. team_economy / 16.000
1. enemy_economy / 16.000
2. differenza di economia / 16.000
3. alive_players / 5
4. enemy_alive / 5
5. differenza giocatori vivi / 5
6. utility_remaining / 5
7. map_control_pct
8. time_remaining / 115
9. bomb_planted (0/1)
10. is_ct (0/1)
11. rapporto equipaggiamento (limitato: min(team/enemy, 2) / 2)

**Limiti di sicurezza deterministici:**
- 0 vivi → 0.0% immediatamente
- 0 nemici → 100.0% immediatamente
- Vantaggio di ±3 giocatori → forza minimo 85% / massimo 15%
- Bomba piazzata → ±10% per lato
- Differenza economia > $8.000 → forza minimo 65% / massimo 35%

### 9.7 Rilevamento dei Punti Ciechi

**File:** `backend/analysis/blind_spots.py`

Confronta le azioni effettive del giocatore con le azioni ottimali dell'albero di gioco:
- Classifica ogni situazione (eco rush, post-plant, 1vN clutch, retake, ecc.)
- Traccia la frequenza delle discrepanze × impatto (delta di probabilità di vittoria)
- Le prime 3 per priorità diventano aree di focus del coaching

### 9.8 Analisi della Distanza di Ingaggio

**File:** `backend/analysis/engagement_range.py`

Fasce di distanza dei kill con linee di base pro per ruolo:

| Fascia | Distanza | AWPer | Entry | Supporto |
|--------|----------|-------|-------|----------|
| Ravvicinata | < 500 unità | 10% | 40% | 25% |
| Media | 500-1500 | 30% | 40% | 45% |
| Lunga | 1500-3000 | 45% | 15% | 25% |
| Estrema | > 3000 | 15% | 5% | 5% |

Segnala osservazioni di coaching quando il giocatore devia > 15% dalla linea di base del ruolo.

### 9.9 Analizzatori di Utility ed Economia

**File:** `backend/analysis/utility_economy.py`

**UtilityAnalyzer — Linee di base pro:**
- Molotov: 35 danno/lancio, 70% tasso di utilizzo
- HE: 25 danno/lancio, 50% tasso di utilizzo
- Flash: 1.2 nemici accecati/flash, 80% tasso di utilizzo
- Smoke: 0.9 valore strategico, 90% tasso di utilizzo

Efficacia = metrica del giocatore / linea di base pro. Raccomandazioni generate quando il punteggio < 0.5.

**EconomyOptimizer — Logica dei round di acquisto:**

| Denaro | Decisione | Confidenza |
|--------|-----------|------------|
| ≥ $4.000 | Full buy | Alta |
| $2.000 - $3.999 | Force buy | Media |
| $1.200 - $1.999 | Half buy (SMG) | Media |
| < $1.200 | Eco | Alta |

Rilevamento round speciali: pistol (round 1), cambio campo (MR12→round 13, MR13→round 16).

Output include: azione, confidenza, armi raccomandate, ragionamento in linguaggio naturale.

---

## 10. Pipeline di Coaching COPER

**File:** `backend/services/coaching_service.py`
**COPER = Context Optimized with Prompt, Experience, Replay** (Ottimizzato per Contesto con Prompt, Esperienza, Replay)

### Catena di Fallback a 4 Livelli di Priorità

```
Livello 1: COPER (pipeline completa — massima fedeltà)
  Utilizza: Banca dell'Esperienza + Conoscenza RAG + Riferimenti Pro
  Richiede: map_name + tick_data
  Pipeline:
    1. Costruisce ExperienceContext dai tick_data
    2. Interroga la Banca dell'Esperienza per situazioni passate simili
    3. Sintetizza la narrativa di consiglio
    4. Recupera la linea di base temporale (confronto con i pro)
    5. Raffina tramite Ollama Writer (LLM locale)
    6. Raccoglie feedback per l'apprendimento futuro
    7. Persiste CoachingInsight nel database
  │
  ▼ fallback (se dati mancanti)
Livello 2: IBRIDO (sintesi ML + RAG)
  Utilizza: HybridCoachingEngine che unisce predizioni ML + conoscenza
  Richiede: player_stats
  │
  ▼ fallback
Livello 3: TRADIZIONALE + RAG (deviazioni + arricchimento da conoscenza)
  Sempre disponibile (necessita solo delle deviazioni statistiche)
  Utilizza: deviazioni formattate con Z-score + voci di conoscenza tattica
  │
  ▼ fallback
Livello 4: TRADIZIONALE (deviazioni puramente statistiche)
  Fallback terminale — produce sempre un output
  Analizza le deviazioni, le mappa alle aree di focus, genera correzioni
```

**Regola assoluta:** Il sistema NON produce MAI zero coaching. Anche in caso di fallimento totale, un insight generico viene salvato (C-01).

### Banca dell'Esperienza
- Memorizza esperienze di gameplay con embedding vettoriali a 384-dim
- Ricerca per similarità semantica (Sentence-BERT all-MiniLM-L6-v2, fallback basato su hash)
- Indice vettoriale FAISS per ricerche O(log n)
- Esperienze pro pesate a 0.7 di confidenza, utente a 0.5
- Output: SynthesizedAdvice con narrativa, riferimenti pro, confidenza, area di focus

### Base di Conoscenza RAG
- Alimentata dalle statistiche dei giocatori professionisti HLTV (raccolte da hltv.org — NON file demo)
- ProStatsMiner crea voci TacticalKnowledge con archetipi:
  - STAR_FRAGGER (rating ≥ 1.15)
  - SNIPER (HS% ≥ 35%)
  - SUPPORT (KAST ≥ 72%)
  - ENTRY (opening duel win% ≥ 52%)
  - LURKER (vittorie in clutch o tasso di multikill)
- Memorizza conoscenza tattica con embedding a 384-dim per ricerca per similarità

### Analisi Post-Coaching (Non Bloccante)
Dopo il coaching principale, queste operazioni vengono eseguite in background:
1. **Analisi Fase 6** tramite AnalysisOrchestrator (momentum, inganno, entropia, albero di gioco, distanza di ingaggio)
2. **Trend Longitudinali** sulle ultime 10 partite (rilevamento di regressione/miglioramento/volatilità)
3. **Heatmap Differenziale** (su richiesta dalla UI — posizioni dell'utente vs linee di base pro)

---

## 11. Orchestratore di Analisi

**File:** `backend/services/analysis_orchestrator.py`

Coordina tutti i moduli di analisi della Fase 6 per una singola partita:

```
AnalysisOrchestrator.analyze_match(player, demo, rounds, ticks, states)
  │
  ├── _analyze_momentum()       → zone di tilt, serie positive
  ├── _analyze_deception()      → indice di inganno composito
  ├── _analyze_utility_entropy() → impatto dell'utility in bit
  ├── _analyze_strategy()       → punti ciechi + raccomandazioni dell'albero di gioco
  └── _analyze_engagement_range() → pattern della distanza dei kill
```

**Gestione degli errori (F5-14):** Contatori di fallimento per modulo. Registra i primi 3 fallimenti, poi ogni 10-esimo. Non bloccante — i fallimenti non fermano la pipeline di coaching principale.

**Output:** MatchAnalysis con insight per-round + insight a livello di partita, tutti persistiti nella tabella CoachingInsight.

---

## 12. Orchestrazione dell'Addestramento

### Trigger: Quando Inizia l'Addestramento?

Il daemon Teacher controlla ogni 5 minuti:
```
pro_count = count(PlayerMatchStats WHERE is_pro=True)
last_count = CoachState.last_trained_sample_count

if pro_count ≥ last_count × 1.10:     → RI-ADDESTRAMENTO (soglia di crescita del 10%)
elif last_count == 0 AND pro_count ≥ 10: → PRIMO ADDESTRAMENTO
else: sleep 300 secondi
```

### Sicurezza dei Thread
`_TRAINING_LOCK` a livello di modulo impedisce l'addestramento concorrente tra daemon e UI.

### Ciclo di Addestramento in 5 Fasi

**Fase 1: Pre-addestramento JEPA (auto-supervisionato)**
- Dati: righe PlayerTickState (solo pro, suddivisione train)
- Finestre di contesto completate a 10 tick, bersaglio = 1 tick (predizione del passo successivo)
- 5 negativi cross-partita da un pool di 500 campioni in cache
- Loss: contrastiva InfoNCE
- Ottimizzatore: AdamW(lr=1e-4, weight_decay=1e-4)
- Scheduler: CosineAnnealingLR(T_max=100)
- Early stopping: pazienza=10 sulla loss di validazione
- Checkpoint: `jepa_brain.pt`

**Fase 2: Linea di Base Professionale (supervisionato)**
- Dati: PlayerMatchStats (is_pro=True, suddivisioni train/val)
- 25 feature aggregate per partita → delta di miglioramento (normalizzati con Z-score)
- Modello: AdvancedCoachNN (legacy)
- Checkpoint: `latest.pt` (directory globale)

**Fase 3: Personalizzazione Utente (transfer learning)**
- Base: modello globale della Fase 2 (avvio a caldo)
- Dati: PlayerMatchStats (is_pro=False)
- Affina la linea di base pro sullo stile di gioco specifico dell'utente
- Checkpoint: `latest.pt` (directory utente)

**Fase 4: Ottimizzazione Comportamentale RAP (condizionale)**
- Viene eseguita solo se `USE_RAP_MODEL=True`
- Dati: finestre contigue di 320 tick dai database per-partita
- Costruisce tensori completi mappa/visuale/movimento a 64×64 (risoluzione di addestramento)
- Calcola i target di vantaggio per tick:
  ```
  advantage = 0.4 × alive_diff + 0.2 × hp_ratio + 0.2 × equip_ratio + 0.2 × bomb_factor
  alive_diff = (team_alive - enemy_alive + 5) / 10  → [0, 1]
  bomb_factor = 0.7 (T piazzata) / 0.3 (CT piazzata) / 0.5 (nessuna bomba)
  ```
- Classifica il ruolo tattico (10 classi):
  0=site_take, 1=rotation, 2=entry_frag, 3=support, 4=anchor,
  5=lurk, 6=retake, 7=save, 8=aggressive_push, 9=passive_hold
- Loss multi-task con penalità 2× sull'asse Z
- Ottimizzatore: AdamW(lr=5e-5, weight_decay=1e-4)
- **Gate di sicurezza:** Si interrompe se il tasso di fallback su tensori zero > 30%
- Checkpoint: `rap_coach.pt`

**Fase 5: Testa di Classificazione dei Ruoli**
- Classificatore leggero per predire il ruolo tattico del giocatore
- Non fatale in caso di fallimento
- Checkpoint: `role_head.pt`

### Gating di Maturità
| Livello | Demo Processate | Confidenza del Coaching |
|---------|----------------|------------------------|
| IN CALIBRAZIONE | 0-49 | 50% (la UI mostra overlay "In calibrazione") |
| IN APPRENDIMENTO | 50-199 | 80% |
| MATURO | 200+ | 100% (correzioni a livello professionale sbloccate) |

### Passi Post-Addestramento
1. Incrementa il contatore di maturità
2. Registra il conteggio dei campioni addestrati (solo DOPO il successo — previene falsi trigger in caso di crash)
3. Controlla il cambio di meta (confronta le statistiche pro prima/dopo l'addestramento — rileva cambiamenti nel meta di gioco)
4. Auto-calibra il modello bayesiano (prior bayesiani dagli esiti reali delle partite)
5. Rilascia `_TRAINING_LOCK`

---

## 13. Model Factory

**File:** `backend/nn/factory.py`

### Tipi di Modello
```
"default"   → TeacherRefinementNN (legacy)
"jepa"      → JEPACoachingModel
"vl-jepa"   → VLJEPACoachingModel
"rap"       → RAPCoachModel
"role_head" → NeuralRoleHead
```

### Nomi dei Checkpoint
- `"jepa"` → `jepa_brain.pt`
- `"vl-jepa"` → `vl_jepa_brain.pt`
- `"rap"` → `rap_coach.pt`
- `"role_head"` → `role_head.pt`
- `"default"` → `latest.pt`

### Gerarchia di Caricamento dei Checkpoint
Quando carica un modello, il sistema cerca in ordine:
1. **Locale utente:** `MODELS_DIR/user_id/version.pt`
2. **Locale globale:** `MODELS_DIR/global/version.pt`
3. **Factory bundled (utente):** `get_resource_path(models/user_id/version.pt)`
4. **Factory bundled (globale):** `get_resource_path(models/global/version.pt)`

**Se NESSUNO trovato → FileNotFoundError** (non usa mai silenziosamente pesi casuali).
**Se le dimensioni non corrispondono → StaleCheckpointError** (forza il ri-addestramento).

**Protocollo di scrittura atomica:**
1. Scrive su `.pt.tmp`
2. `fsync` (flush su disco)
3. `os.replace` (atomico su POSIX — nessuna corruzione in caso di interruzione di corrente)
4. Pulizia di `.pt.tmp` in caso di eccezione

---

## 14. GhostEngine — Inferenza

**File:** `backend/nn/inference/ghost_engine.py`

Il motore di inferenza in produzione che crea l'overlay del "fantasma" sulla mappa tattica.

### Flusso di Inferenza Per-Tick

```
Dati del tick (dizionario dello stato del giocatore)
  │
  ▼
1. Verifica modello caricato (se no → ritorna (0, 0))
  │
  ▼
2. Costruisce i tensori tramite TensorFactory:
   map_t:    [1, 3, 128, 128]  panoramica tattica
   view_t:   [1, 3, 224, 224]  prospettiva del giocatore
   motion_t: [1, 3, 224, 224]  contesto di movimento
   meta_t:   [1, 1, 25]        vettore delle feature
  │
  ▼
3. Passata forward (no_grad):
   out = model(view=view_t, map=map_t, motion=motion_t, metadata=meta_t)
  │
  ▼
4. Decodifica della posizione:
   optimal_delta = out["optimal_pos"]  → [1, 3] (dx, dy, dz)
   ghost_x = current_x + dx × 500.0
   ghost_y = current_y + dy × 500.0
   (Asse Z non utilizzato — le mappe di CS2 sono navigabili in 2D)
  │
  ▼
5. Ritorna (ghost_x, ghost_y) come coordinate mondo
```

**Gestione degli errori:** RuntimeError o qualsiasi eccezione → log + ritorna (0.0, 0.0). Nessuna eccezione raggiunge la UI.

**Integrazione con la UI** (da `tactical_vm.py`): Carica GhostEngine in modo pigro (lazy) solo quando l'utente attiva la modalità fantasma. Itera sui giocatori vivi, chiama `predict_tick()` per giocatore, sostituisce la posizione con le coordinate fantasma.

### Limitazioni Attuali
- **Nessuna decodifica selettiva:** Passata forward completa ad ogni tick (vedi Sezione 15)
- **Nessuna inferenza con stato:** Lo stato nascosto LSTM si resetta ad ogni tick
- **Nessun batching:** batch_size=1 per predizione del giocatore
- **Nessuna cache degli embedding:** Nessun riutilizzo tra tick sequenziali

---

## 15. Decodifica Selettiva

**File:** `backend/nn/jepa_model.py` (metodo `forward_selective`)

### Stato: ESISTE ma NON UTILIZZATA da GhostEngine

Il metodo è completamente implementato ma GhostEngine esegue la decodifica completa ad ogni tick.

### Come Funzionerebbe

```
Arriva il Tick N → [B, seq_len, 25]
  │
  ▼
Encoder del Contesto (viene SEMPRE eseguito — economico, ~100k parametri)
  → curr_embedding [B, seq_len, 256]
  │
  ├── Media Pooling → curr_pooled [B, 256]
  │
  ├── Confronto con prev_pooled dal tick precedente:
  │     cosine_distance = 1.0 - cosine_similarity(curr, prev)
  │
  │     distance < 0.05? ─── SI ──► SALTA: ritorna None, riutilizza l'ultima predizione
  │         │
  │        NO (lo stato è cambiato in modo significativo)
  │         │
  ▼         ▼
LSTM (2 strati, 256→128)    ← COSTOSO (~500k parametri)
Gate MoE (3 esperti)         ← COSTOSO
tanh → predizione [B, 10]
  │
  ▼
Ritorna: (predizione, curr_embedding, True)
Mette in cache curr_embedding per il confronto del tick successivo
```

**Potenziale di risparmio:** Durante i momenti calmi (giocatore che tiene un angolo), potrebbe saltare il 60-80% del calcolo.

### Anche Non Utilizzata: Inferenza con Stato (NN-40)

Il modello RAP supporta la persistenza dello stato nascosto LSTM tra i tick:
```python
# Cosa supporta il modello:
out = model(view, map, motion, metadata, hidden_state=cached_state)
# Cosa fa effettivamente GhostEngine:
out = model(view, map, motion, metadata)  # Nessun hidden_state → si resetta ad ogni tick
```

Abilitare questa funzionalità permetterebbe all'LSTM di "ricordare" i tick recenti, riducendo il jitter (tremolii).

---

## 16. Motore di Sessione Tri-Daemon

**File:** `core/session_engine.py`

Quattro thread in background orchestrano tutto il lavoro asincrono:

```
┌──────────────────────────────────────────────────────────┐
│                   MOTORE DI SESSIONE                       │
│               (Loop Principale Keep-Alive)                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  DAEMON A: SCANNER (Hunter)              Ciclo: 10s     │
│  ├─ Monitora il filesystem per nuovi file .dem           │
│  ├─ Due scansioni per ciclo: is_pro=True, is_pro=False   │
│  ├─ Accoda righe IngestionTask nel database              │
│  └─ Segnala _work_available_event                        │
│                                                          │
│  DAEMON B: DIGESTORE                     Ciclo: evento   │
│  ├─ Consuma la coda IngestionTask (1 per ciclo)          │
│  ├─ Parsing demo a 3 passate → estrazione feature        │
│  ├─ Valida l'integrità dei dati                          │
│  ├─ Persiste PlayerMatchStats, RoundStats, MatchTickState│
│  ├─ Recupero zombie: task bloccati >5 min reset a queued │
│  └─ Si blocca sull'evento quando la coda è vuota        │
│                                                          │
│  DAEMON C: INSEGNANTE                    Ciclo: 300s    │
│  ├─ Monitora la crescita dei campioni pro (soglia 10%)   │
│  ├─ Acquisisce _TRAINING_LOCK                            │
│  ├─ Esegue il ciclo completo di addestramento a 5 fasi  │
│  ├─ Rilevamento cambio meta + calibrazione bayesiana     │
│  └─ Persiste i checkpoint del modello                    │
│                                                          │
│  DAEMON D: IMPULSO                       Ciclo: 5s      │
│  ├─ Timestamp di heartbeat per la UI                     │
│  └─ Permette il rilevamento di stallo                    │
│                                                          │
│  SPEGNIMENTO: Il processo padre scrive "STOP" su stdin   │
│  → tutti i daemon escono con grazia (timeout join 5s)    │
│                                                          │
│  AVVIO: Backup giornaliero automatico tramite            │
│  BackupManager + inizializzazione una tantum della       │
│  base di conoscenza                                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Proprietà dei dati (nessuna mutazione cross-daemon):**
- Lo Scanner possiede la creazione di IngestionTask
- Il Digestore possiede la creazione di PlayerMatchStats/RoundStats/PlayerTickState
- L'Insegnante possiede la creazione dei checkpoint del modello + CalibrationSnapshot
- Il CoachingService possiede la creazione di CoachingInsight/CoachingExperience

---

## 17. Costanti Chiave

| Costante | Valore | Utilizzo |
|----------|--------|----------|
| METADATA_DIM | 25 | Dimensione di input di ogni modello |
| OUTPUT_DIM | 10 | Output di strategia/coaching |
| JEPA latent_dim | 256 | Spazio latente encoder/predittore/bersaglio |
| RAP hidden_dim | 256 | Dimensione nascosta memoria + strategia |
| RAP perception_dim | 128 | View(64) + Map(32) + Motion(32) |
| NUM_COACHING_CONCEPTS | 16 | Interpretabilità di VL-JEPA |
| LTC NCP units | 512 | 2× hidden per cablaggio sparso |
| Hopfield heads | 4 | Attenzione della memoria associativa |
| Esperti MoE (RAP) | 4 | Specializzazione dello strato strategia |
| Esperti MoE (JEPA) | 3 | Specializzazione della testa di coaching |
| RAP_POSITION_SCALE | 500.0 | Delta → unità coordinate mondo |
| Temperatura InfoNCE | 0.07 | Nitidezza della distribuzione contrastiva |
| Momentum EMA | 0.996 | Ritardo dell'encoder bersaglio (~250 passi) |
| GLOBAL_SEED | 42 | Riproducibilità ovunque |
| BATCH_SIZE | 32 | Batch di addestramento predefinito |
| Learning rate RAP | 5e-5 | Ottimizzatore RAP |
| Learning rate JEPA | 1e-4 | Ottimizzatore JEPA |
| Lunghezza sequenza (RAP) | 320 | Finestra di addestramento in tick (~5s a 64Hz) |
| Lunghezza sequenza (JEPA) | 10 | Finestra di contesto in tick |
| Pool negativi max | 500 | Cache di negativi cross-partita |
| Tensore mappa (addestramento) | 64×64 | Ridotto per velocità |
| Tensore mappa (inferenza) | 128×128 | Risoluzione piena |
| Tensore visuale (addestramento) | 64×64 | Ridotto per velocità |
| Tensore visuale (inferenza) | 224×224 | Risoluzione piena |
| Embedding esperienza | 384-dim | Output Sentence-BERT |
| Embedding conoscenza | 384-dim | Output Sentence-BERT |
| Feature probabilità vittoria | 12 | Input di WinProbabilityNN |
| Pazienza early stopping | 10 | Epoche senza miglioramento |
| Soglia Z di deriva | 2.5 | Spostamento della distribuzione delle feature |
| Timeout lock addestramento | ∞ | Solo acquisizione non bloccante |
| Heartbeat daemon | 5 secondi | Intervallo di impulso |
| Ciclo scanner | 10 secondi | Controllo del file system |
| Ciclo insegnante | 300 secondi | Controllo ri-addestramento |
| Timeout task zombie | 5 minuti | Recupero task bloccati |

---

## 18. Valutazione Ingegneristica Onesta

### Cosa è Genuinamente Solido

1. **JEPA è vera ricerca pubblicata** dal team di Yann LeCun presso Meta AI. L'implementazione della loss contrastiva InfoNCE è corretta. Il meccanismo anti-collasso dell'encoder bersaglio tramite EMA funziona come previsto.
2. **Il vettore delle feature a 25-dim** cattura lo stato di gioco essenziale con normalizzazioni sensate: codifica ciclica del yaw (sin/cos evita il salto 359°→0°), intervalli limitati, contesto tattico separato (feature 20-24).
3. **La probabilità di morte bayesiana** utilizza aggiornamenti log-odds da manuale con auto-calibrazione dai dati reali delle partite. La matematica è corretta.
4. **L'albero di gioco expectiminimax** è un algoritmo reale dalla ricerca nell'AI dei giochi (scacchi, poker). Applicarlo alle decisioni di round in CS2 con modellazione adattiva dell'avversario è creativo e difendibile.
5. **La catena di fallback COPER** è solida ingegneria del software di produzione. "Non produrre mai zero coaching" con 4 livelli di degradazione è come dovrebbero funzionare i sistemi di produzione.
6. **La pipeline dati** è ben costruita: parsing a 3 passate, cache firmata con HMAC, velocizzazione 10× vettorizzata, suddivisioni temporali train/val/test, decontaminazione dei giocatori, rimozione degli outlier.
7. **Le scritture atomiche dei checkpoint** (scrittura su .tmp → fsync → os.replace) prevengono la corruzione in caso di interruzione di corrente.
8. **L'architettura tri-daemon** con coordinamento basato su eventi è un design ragionevole per questo tipo di applicazione.

### Cosa è Sovra-ingegnerizzato

1. **Il RAP Coach è troppo complesso per 11 demo.** Percezione ResNet + neuroni LTC + memoria di Hopfield + gating a Superposizione + 4 esperti MoE + Attribuzione + testa di Posizione + funzione di Valore = centinaia di migliaia di parametri. Servono 10.000× più dati.
2. **I "prototipi" di Hopfield apprendono rumore con questa scala di dati.** Pattern inizializzati casualmente + discesa del gradiente con 11 demo = memorizzazione, non generalizzazione.
3. **I neuroni LTC** sono progettati per robotica/controllo a tempo continuo. Non sono chiaramente superiori agli LSTM standard per tick di gioco discreti.
4. **Lo "Strato a Superposizione"** è uno strato lineare con gate standard. `linear(x) * sigmoid(gate(context))` — un semplice meccanismo di gating con un nome che fa colpo.
5. **Il CausalAttributor** utilizza proxy approssimativi (`aggressione = pos_delta × 0.5`) — non è un vero ragionamento causale.
6. **La metrica di inganno sonoro** è semplicemente l'inverso del rapporto di accovacciamento — non misura effettivamente l'inganno sonoro.
7. **Funzionalità costruite ma non connesse:** decodifica selettiva, inferenza con stato, tensori POV tutti implementati ma inutilizzati in produzione.

### Puo' Battere il Chiedere Consigli su CS2 a un LLM?

**Adesso: No.** Un modello linguistico addestrato su milioni di discussioni su CS2 fornisce consigli generali migliori.

**Il potenziale e' fondamentalmente diverso:** Coaching personalizzato e basato sui dati, fondato sulle TUE replay effettive, e' qualcosa che un LLM generico non puo' fare.

| Scenario | LLM Generico | Questo Sistema (una volta addestrato) |
|----------|------------|--------------------------------------|
| "Come giocare il sito B?" | Buone pratiche generiche | "Nei TUOI ultimi 50 round, fai overpeek verso gli apartments il 73% delle volte e muori. I pro tengono dal van." |
| "Sono bravo con l'utility?" | Consigli generici sull'utility | "La tua efficacia con le flash e' 0.31. La media dei pro e' 0.68. Lanci il 40% delle flash senza accecare nessuno." |
| "Dove dovrei stare?" | Guida ai callout della mappa | Overlay fantasma che mostra esattamente dove DOVRESTI stare in questo tick |

### Il Percorso da Seguire

1. **Iniziare piu' semplici.** Dimostrare che un modello base (MLP a 2 strati o LSTM standard) riesce a distinguere i round buoni da quelli cattivi prima di aggiungere la complessita' di RAP.
2. **Ottenere piu' dati.** Da 11 a 200 demo e' un inizio, ma le architetture complesse necessitano di migliaia.
3. **Dimostrare valore incrementalmente.** Il modello riesce a predire l'esito dei round? A distinguere un eco da un full buy? Se no, sistemare le fondamenta prima di aggiungere strati.
4. **I motori di teoria dei giochi potrebbero essere piu' preziosi adesso** — funzionano con regole e matematica, non con dati di addestramento, e potrebbero fornire coaching utile GIA' OGGI.
