# CS2 Coach AI — Complete Architecture Analysis

> **Date:** March 17, 2026
> **Scope:** Full AI/ML architecture audit — neural networks, game theory, coaching pipeline, training orchestration, data pipeline, database schema, tensor generation, inference engine
> **Purpose:** Comprehensive reference document for understanding every component of the AI system

---

## Table of Contents

1. [The Feature Vector (METADATA_DIM = 25)](#1-the-feature-vector)
2. [Data Pipeline: Demo to Features](#2-data-pipeline)
3. [Database Schema](#3-database-schema)
4. [JEPA — Self-Supervised Pre-training](#4-jepa)
5. [VL-JEPA — Interpretable Coaching Concepts](#5-vl-jepa)
6. [RAP Coach — The Ghost Player Brain](#6-rap-coach)
7. [Legacy Coach (AdvancedCoachNN)](#7-legacy-coach)
8. [Tensor Factory — Visual Inputs](#8-tensor-factory)
9. [Game Theory Engines](#9-game-theory-engines)
10. [COPER Coaching Pipeline](#10-coper-coaching-pipeline)
11. [Analysis Orchestrator (Phase 6)](#11-analysis-orchestrator)
12. [Training Orchestration (5 Phases)](#12-training-orchestration)
13. [Model Factory & Checkpoint Loading](#13-model-factory)
14. [GhostEngine Inference](#14-ghost-engine)
15. [Selective Decoding & Stateful Inference](#15-selective-decoding)
16. [Tri-Daemon Session Engine](#16-session-engine)
17. [Key Dimensional Constants](#17-key-constants)
18. [Honest Engineering Assessment](#18-honest-assessment)

---

## 1. The Feature Vector

**File:** `backend/processing/feature_engineering/vectorizer.py`

Every tick of every demo is compressed into a 25-number vector. This is the universal language all models speak.

| Index | Feature | Range | Normalization |
|-------|---------|-------|---------------|
| 0 | health | 0-1 | / 100 |
| 1 | armor | 0-1 | / 100 |
| 2 | has_helmet | 0/1 | binary |
| 3 | has_defuser | 0/1 | binary |
| 4 | equipment_value | 0-1 | / 10,000 |
| 5 | is_crouching | 0/1 | binary |
| 6 | is_scoped | 0/1 | binary |
| 7 | is_blinded | 0/1 | binary |
| 8 | enemies_visible | 0-1 | count / 5 |
| 9 | pos_x | -1 to 1 | / 4,096 |
| 10 | pos_y | -1 to 1 | / 4,096 |
| 11 | pos_z | -1 to 1 | / 1,024 |
| 12 | view_yaw_sin | -1 to 1 | sin(yaw) — cyclic encoding avoids 359-to-0 discontinuity |
| 13 | view_yaw_cos | -1 to 1 | cos(yaw) — paired with sin for smooth rotation |
| 14 | view_pitch | -1 to 1 | / 90 |
| 15 | z_penalty | 0-1 | vertical level distinctiveness |
| 16 | kast_estimate | 0-1 | Kill/Assist/Survive/Trade ratio |
| 17 | map_id | 0-1 | MD5 hash % 10000 / 10000 (deterministic per map) |
| 18 | round_phase | 0/0.33/0.66/1 | pistol/eco/force/full buy |
| 19 | weapon_class | 0-1 | knife=0, pistol=0.2, SMG=0.4, rifle=0.6, sniper=0.8, heavy=1.0 |
| 20 | time_in_round | 0-1 | elapsed / 115 seconds |
| 21 | bomb_planted | 0/1 | binary |
| 22 | teammates_alive | 0-1 | count / 4 |
| 23 | enemies_alive | 0-1 | count / 5 |
| 24 | team_economy | 0-1 | team avg money / 16,000 |

**Round phase thresholds** (from `base_features.py`):
- Eco: team money < $1,500
- Force: $1,500 - $3,000
- Force-buy: $3,000 - $4,000
- Full buy: > $4,000

---

## 2. Data Pipeline

**File:** `ingestion/demo_loader.py`

### 3-Pass Demo Parsing

Each `.dem` file goes through three sequential passes using the `demoparser2` library:

**Pass 1 — Position Extraction:**
- Extracts player positions at every tick
- Builds `pos_by_tick[tick] = {steamid: (x, y, z)}`
- Lightweight — just coordinates

**Pass 2 — Grenade Linking:**
- Processes grenade start/end events
- Matches throw data to trajectory and impact
- Tracks: `base_id`, `nade_type`, `x/y/z`, `starting_tick`, `ending_tick`, `throw_tick`, `trajectory`, `thrower_id`
- Heuristic ceiling: grenades missing end events capped at 20 × tick_rate (`is_duration_estimated = True` flag)
- Fade window: 5 × tick_rate

**Pass 3 — Full State Extraction:**
- Builds complete 25-field PlayerState objects per tick
- Multi-map segmentation (detects map changes within a single demo)
- Uses `round_freeze_end` events to detect round boundaries
- Money resolution: coalesces across field variants (`balance`, `cash`, `money`, `m_iAccount`)
- Team resolution: vectorized string matching (CT/TER/SPEC)

### Cache System
- Cache version: `v21_vectorized_parse` (pre-vectorized columns for 10x speedup)
- HMAC-signed with atomic write (prevents corruption)
- Safe unpickler restricts to `demo_frame` module classes only (security)
- Cache invalidation: file size + version string mismatch

### Tick Enrichment (Features 20-24)
After parsing, each tick is enriched with contextual features:
- `time_in_round`: computed from round start tick
- `bomb_planted`: from game events
- `teammates_alive` / `enemies_alive`: from tick-level player state
- `team_economy`: averaged across team members

### Data Splitting Strategy
- **Chronological 70/15/15** split by match date (prevents temporal leakage)
- **Player decontamination**: each player appears in ONE split only
- **Outlier removal**: IQR 3.0x (Tukey's outer fence)
- **StandardScaler**: fitted on train split only, applied to val/test

---

## 3. Database Schema

**File:** `backend/storage/db_models.py`

All databases use SQLite in WAL (Write-Ahead Logging) mode for concurrent access.

### PlayerMatchStats (match-level aggregates)
25 statistical fields per player per match:
- **Core:** kills, deaths, ADR, headshot%, KAST
- **Variance:** kill_std, adr_std, K/D ratio
- **Duels:** opening_duel_win_pct, clutch_win_pct, trade_kill_ratio
- **Utility:** flash_assists, HE damage/round, molotov damage/round, smokes/round
- **HLTV 2.0 ratings:** impact, survival, KAST, KPR, ADR
- **Flags:** `is_pro` (boolean), `dataset_split` (train/val/test), `data_quality` (string)

### PlayerTickState (per-tick state, ~17.3M rows for 11 demos)
19 fields per tick per player:
- Position (x, y, z), view angles (sin/cos encoded), health, armor
- Crouching, scoped, blinded, active weapon, equipment value
- Enemies visible, round number, time in round, bomb planted
- Teammates alive, enemies alive, team economy, map name

### RoundStats (per-round per-player)
- Kills, deaths, assists, damage dealt, headshot kills
- Trade kills, was traded, opening kill/death
- Utility: HE damage, molotov damage, flashes thrown, smokes thrown
- Equipment value, round won, MVP, round rating

### CoachingExperience (Experience Bank for COPER)
- Context: map, round phase, side, position area
- Game state: JSON snapshot (max 16KB)
- Action/outcome: what was done, result (kill/death/trade/objective/survived)
- Pro reference: player name + match ID
- Embedding: 384-dim vector (JSON-encoded)
- Feedback loop: effectiveness score, times followed

### CoachState (singleton, id=1)
- Training status (Paused/Training/Idle/Error)
- Current epoch, total epochs, train/val loss, ETA
- Heartbeat, system CPU/memory load
- Maturity: total_matches_processed

### ProPlayerStatCard (HLTV statistics)
- Rating 2.0, DPR, KAST, impact, ADR, KPR, headshot%
- Opening kill ratio, clutch wins, multikill rounds
- Time span: all_time / last_3_months / 2024

### TacticalKnowledge (RAG knowledge base)
- Title, description, category (positioning/economy/utility/aim)
- Map, situation context, pro example
- Embedding: 384-dim vector for similarity search

### DataLineage (audit trail)
- Append-only: traces every entity back to source demo, tick, pipeline version

---

## 4. JEPA

**File:** `backend/nn/jepa_model.py`
**What it stands for:** Joint-Embedding Predictive Architecture (from Yann LeCun / Meta AI)

### Purpose
Learn representations of game states without labels. Watches pro demos and learns what "normal good play" looks like in a compressed 256-dimensional latent space.

### How It Works (Conceptual)
Given a window of game ticks (the "context"), predict what the NEXT window (the "target") will look like — but in compressed 256-dim representation, not raw 25-dim features. This forces the model to understand cause-and-effect in CS2: "If a player is here with this weapon and sees two enemies, what happens next?"

### Architecture

```
JEPACoachingModel
├── Context Encoder (JEPAEncoder) — trained by gradient
│   └── Linear(25→512) + LayerNorm + GELU + Dropout(0.1)
│       Linear(512→256) + LayerNorm
│       Output: [B, seq_len, 256]
│
├── Target Encoder (same architecture) — EMA-only, NO gradients
│   └── Updated: target = 0.996 × target + 0.004 × context
│       Never receives gradient. Only copies slowly from context encoder.
│
├── Predictor (JEPAPredictor) — maps context to predicted target
│   └── Linear(256→512) + LayerNorm + GELU + Dropout(0.1)
│       Linear(512→256)
│       Input: mean-pooled context [B, 256]
│       Output: predicted target [B, 256]
│
├── LSTM Coaching Head (2 layers, hidden=128, dropout=0.2)
│   └── Input: [B, seq_len, 256] from context encoder
│       Output: [B, seq_len, 128] temporal processing
│
├── Mixture of Experts (3 experts) — specialized coaching
│   └── Gate: Linear(128→3) + Softmax → "which expert to trust?"
│       Expert 1: Linear(128→128) + ReLU + Linear(128→10)
│       Expert 2: same architecture
│       Expert 3: same architecture
│       Weighted sum of expert outputs
│
└── Output: tanh([B, 10]) → coaching vector in [-1, 1]
```

### Two-Stage Training Protocol

**Stage 1 — JEPA Pre-training (self-supervised, no labels needed):**

```
Pro demo tick sequences
    │
    ├── Context window [B, context_len, 25]
    │         │
    │         ▼
    │   Context Encoder → [B, context_len, 256]
    │         │
    │         ▼
    │   Mean Pool → [B, 256]
    │         │
    │         ▼
    │   Predictor → predicted_target [B, 256]
    │
    └── Target window [B, target_len, 25]
              │
              ▼
        Target Encoder (no_grad) → [B, target_len, 256]
              │
              ▼
        Mean Pool → real_target [B, 256]

Loss: "Is predicted_target closer to real_target
       than to random other targets?"
       → InfoNCE contrastive loss
```

**Stage 2 — Fine-tuning (supervised, needs coaching labels):**
- Freeze both encoders (`requires_grad = False`)
- Train only LSTM + MoE experts on coaching targets with MSE loss
- Encoders become fixed feature extractors

### InfoNCE Loss (Step by Step)

```
1. Normalize everything to unit sphere (L2 norm):
   pred    = normalize(pred)        → unit vectors [B, 256]
   target  = normalize(target)      → unit vectors [B, 256]
   negs    = normalize(negatives)   → unit vectors [B, K, 256]

2. Positive similarity (how close is prediction to REAL target?):
   pos_sim = dot_product(pred, target) / 0.07
   Division by temperature=0.07 sharpens the distribution

3. Negative similarities (how close is prediction to WRONG targets?):
   neg_sim = dot_product(pred, each_negative) / 0.07
   [B, K] — one score per negative per sample

4. Stack into classification logits:
   logits = [pos_sim, neg_sim₁, neg_sim₂, ..., neg_simₖ]
   [B, K+1] — position 0 is the correct answer

5. Cross-entropy loss:
   labels = [0, 0, 0, ...] (correct class always index 0)
   loss = -log(exp(pos_sim) / (exp(pos_sim) + Σexp(neg_sim)))
```

### In-Batch Negatives (O(B²) — No Extra Memory Needed)

```
For batch of size B, encode all B target windows:
  all_encoded = target_encoder(x_target).mean(dim=1)  → [B, 256]

For sample i, negatives = all OTHER samples:
  negatives[i] = all_encoded[j] for all j ≠ i   → [B-1, 256]

Result: [B, B-1, 256] — each sample has B-1 negatives for free
Skip batches where B < 2 (need at least 2 samples for contrast)
```

### EMA Update (Anti-Collapse Mechanism)

After every training step:
```
target_weights = 0.996 × target_weights + 0.004 × context_weights
```

**Why?** Without this, the model can "collapse" — output the same embedding for everything (trivially perfect similarity = zero loss, but useless). The target encoder LAGS behind the context encoder by ~250 steps (1/0.004), creating a moving target that prevents collapse.

**Safety check (NN-JM-04):** Before every EMA update, verifies `target_encoder.requires_grad == False`. If violated → `RuntimeError` immediately.

### Embedding Health Monitor (P9-02)
```
variance = embeddings.var(dim=0).mean()
if variance < 0.01 → WARNING: collapse risk (all embeddings converging)
if variance ≥ 0.01 → healthy (embeddings are spread out in space)
```

### Drift Detection & Auto-Retraining
- Monitors validation data Z-scores vs training reference stats
- Z-score > 2.5 → drift detected (game meta changed)
- 5 consecutive drift checks → triggers full retraining (10 epochs)
- Resets learning rate scheduler and drift history after retraining

---

## 5. VL-JEPA

**File:** `backend/nn/jepa_model.py` (class `VLJEPACoachingModel`, extends `JEPACoachingModel`)

### Purpose
Extends JEPA with 16 interpretable coaching concepts so the model can explain WHY it gives specific advice. Instead of just a 10-number coaching vector, you get: "This tick is 80% positioning_exposed, 60% engagement_unfavorable."

### 16 Coaching Concepts

| ID | Concept | Category | What it means |
|----|---------|----------|---------------|
| 0 | positioning_aggressive | Positioning | Pushing angles, close-range fights |
| 1 | positioning_passive | Positioning | Holding long angles, avoiding contact |
| 2 | positioning_exposed | Positioning | Vulnerable position, high death risk |
| 3 | utility_effective | Utility | Grenades creating real advantage |
| 4 | utility_wasteful | Utility | Dying with unused utility, low impact |
| 5 | economy_efficient | Decision | Equipment matches round expectations |
| 6 | economy_wasteful | Decision | Force-buying into bad rounds |
| 7 | engagement_favorable | Engagement | Taking fights with HP/position/numbers advantage |
| 8 | engagement_unfavorable | Engagement | Outnumbered, low HP, bad angles |
| 9 | trade_responsive | Engagement | Quick teammate trades, good coordination |
| 10 | trade_isolated | Engagement | Dying without trades, too far from team |
| 11 | rotation_fast | Decision | Quick positional rotation after intel |
| 12 | information_gathered | Decision | Good recon, multiple enemies spotted |
| 13 | momentum_leveraged | Psychology | Capitalizing on hot streaks |
| 14 | clutch_composed | Psychology | Calm decisions in 1vN situations |
| 15 | aggression_calibrated | Psychology | Right aggression level for the situation |

### How Concepts Work

```
Game state [B, seq_len, 25]
  │
  ▼
Context Encoder → [B, seq_len, 256]
  │
  ▼
Mean Pool → [B, 256]
  │
  ▼
Concept Projector: Linear(256→256) + GELU + Linear(256→256) + L2 normalize
  │
  ▼
projected [B, 256] (unit vector on sphere)

Compare with 16 learnable Concept Embeddings [16, 256]:
  cosine_similarity = projected × concept_embeddings.T  → [B, 16]

Temperature scaling (learnable, initialized 0.07, clamped [0.01, 1.0]):
  logits_scaled = cosine_similarity / temperature

Softmax → [B, 16] probability distribution over concepts
```

### Two Ways to Generate Concept Labels

**Outcome-based (preferred, no data leakage):** Uses RoundStats data — kills, deaths, damage, round won/lost, trade kills, utility usage. Examples:
- Got opening kill + survived → `positioning_aggressive = 0.8`
- Died first with < 40 damage → `positioning_exposed = 0.6`
- Won eco round with < $2000 gear → `economy_efficient = 0.9`
- Trade kills > 0 → `trade_responsive = 0.6 + 0.2 per kill`

**Heuristic fallback (label leakage risk):** Derives labels from the same 25-dim input features. The model can "cheat" by reconstructing input→label mapping. A warning is logged when this path is used.

### VL-JEPA Loss Function
```
total_loss = InfoNCE + α × concept_BCE + β × diversity_loss

Where:
  concept_loss = Binary Cross-Entropy(logits, soft_labels)
    Each concept is an independent binary classification (multi-label, not one-hot)

  diversity_loss = -mean(std_per_dimension(concept_embeddings))
    Penalizes all 16 concepts clustering in the same spot
    Inspired by VICReg (Variance-Invariance-Covariance Regularization)

Default weights: α=0.5, β=0.1
```

---

## 6. RAP Coach

**Files:** `backend/nn/experimental/rap_coach/`
**What it stands for:** Recurrent Attention-based Pedagogy

### Purpose
A 7-layer "ghost player" brain that takes visual tensors (map, view, motion) + metadata, and outputs: where you should stand, what you should do, how good your situation is, and why you're making mistakes.

### Layer 1: PERCEPTION (perception.py)

Three visual processing streams inspired by neuroscience (ventral "what" / dorsal "where" pathways):

```
View Frame [B, 3, H, W]  (what do I see?)
  → ResNet backbone: Conv2d(3→64, stride=2) + BatchNorm + ReLU
    + 4 residual blocks (64→64), each: conv3×3→BN→ReLU→conv3×3→BN + shortcut
  → AdaptiveAvgPool2d(1,1) → [B, 64]

Map Frame [B, 3, H, W]  (where am I on the map?)
  → ResNet backbone: Conv2d(3→32, stride=2) + BatchNorm + ReLU
    + 3 residual blocks (32→32)
  → AdaptiveAvgPool2d(1,1) → [B, 32]

Motion Frame [B, 3, H, W]  (what's moving?)
  → Conv2d(3→16, 3×3) + ReLU + MaxPool2d(2)
  → Conv2d(16→32, 3×3) + ReLU
  → AdaptiveAvgPool2d(1,1) → [B, 32]

Concatenate all three: [64 + 32 + 32] = [B, 128] perception vector
```

### Layer 2: MEMORY (memory.py)

**Liquid Time-Constant (LTC) Network:**
- Brain-inspired neurons with ADAPTIVE time constants — they respond differently to fast vs slow changes
- Uses `AutoNCP(units=512, output_size=256)` — sparse, biologically-plausible Neural Circuit Policy wiring
- Input: [B, T, 153] (128 perception + 25 metadata concatenated)
- Key property: naturally handles variable frame rates (CS2 demos aren't always 64 ticks/s)
- RNG seeded deterministically: `np.random.seed(42)` + `torch.manual_seed(42)`

**Hopfield Associative Memory:**
- 4 attention heads, pattern dimension 256
- Think of it as: stores "prototype situations" (perfect tactical plays)
- Patterns initialized randomly (randn × 0.02), shaped only by gradient descent during training
- **Safety guard:** Stays OFF for first 2 training forward passes (random patterns would add noise)
- After 2 passes → `_hopfield_trained = True` → Hopfield activates
- Combined with LTC via residual connection: `output = ltc_output + hopfield_output`

**Belief Head (internal situation understanding):**
```
Linear(256→256) → SiLU → Linear(256→64)
Output: [B, T, 64] — the model's compressed "understanding" of the current situation
```

### Layer 3: STRATEGY (strategy.py)

4 Mixture-of-Experts with context-gated Superposition Layers:

```
For each of 4 experts:
  SuperpositionLayer(256→128, context=25) → ReLU → Linear(128→10)

Gate: Linear(256→4) → Softmax → [B, 4] expert weights

Final = Σ(expert_output × gate_weight) → [B, 10] strategy vector
```

**Superposition Layer** (the gating mechanism):
```python
out = F.linear(x, weight, bias)         # Standard linear: [B, 128]
gate = sigmoid(context_gate(metadata))   # Context determines relevance: [B, 128]
return out * gate                        # Element-wise: irrelevant neurons suppressed
```

### Layer 4: EVALUATION (pedagogy.py)

**Critic (value function):**
```
Linear(256→64) → ReLU → Linear(64→1) → V(s)
"How good is this game state?" (single scalar)
```

**Skill Adapter:**
```
Linear(10→256)
If skill_vec provided: hidden = hidden + skill_adapter(skill_vec)
Shifts the model's expectations based on player skill level (1-10 scale)
```

### Layer 5: POSITIONING

```
Linear(256→3) → [dx, dy, dz]
At inference, scaled by RAP_POSITION_SCALE = 500.0 game units
ghost_x = current_x + dx × 500.0
ghost_y = current_y + dy × 500.0
```

**Z-axis gets 2x penalty** during training because being on the wrong floor in CS2 = instant death.

### Layer 6: ATTRIBUTION

5-channel error explanation: **Positioning, Aim, Aggression, Utility, Rotation**

```
Relevance Head: Linear(256→32) → ReLU → Linear(32→5) → Sigmoid → [B, 5]

Combines neural relevance weights with mechanical error measurements:
  attribution[0] = relevance[0] × ||position_delta||     (Positioning)
  attribution[1] = relevance[1] × ||aim_delta||           (Aim)
  attribution[2] = relevance[2] × ||pos_delta|| × 0.5     (Aggression)
  attribution[3] = relevance[3] × sigmoid(hidden.mean())  (Utility — neural-only)
  attribution[4] = relevance[4] × ||pos_delta|| × 0.8     (Rotation)
```

### RAP Training Loss

```
total = 1.0 × MSE(strategy_pred, strategy_target)
      + 0.5 × MSE(value_pred, value_target)       (with masking for missing data)
      + 1.0 × L1(gate_weights) × 1e-4             (sparsity regularization)
      + 1.0 × weighted_MSE(position_pred, position_target)
              where Z-axis weight = 2.0

Gradient clipping: max_norm = 1.0
Optimizer: AdamW(lr=5e-5, weight_decay=1e-4)
```

### Full RAP Output Dictionary
```python
{
    "advice_probs":    [B, 10],    # Strategy recommendations (10 tactical roles)
    "belief_state":    [B, T, 64], # Internal situation understanding
    "value_estimate":  [B, 1],     # How good is this state? (scalar)
    "gate_weights":    [B, 4],     # Which expert dominated the decision?
    "optimal_pos":     [B, 3],     # Where you SHOULD be standing (delta)
    "attribution":     [B, 5],     # Why you're losing (5 channels)
    "hidden_state":    (tuple),    # Persistent LSTM memory for next tick
}
```

---

## 7. Legacy Coach

**File:** `backend/nn/model.py`

The simpler fallback model (AdvancedCoachNN / TeacherRefinementNN):

```
Input [B, seq, 25]
  │
  ▼
LSTM(25→128, 2 layers, dropout=0.2)
  │
  ▼
LayerNorm(128)
  │
  ▼
3 MoE Experts:
  Each: Linear(128→128) + LayerNorm + ReLU + Linear(128→10)
  Gate: Linear(128→3) + Softmax
  │
  ▼
tanh → [B, 10] coaching output
```

**Role biasing:** When a role_id (0, 1, or 2) is provided:
```
role_bias = [0, 0, 0] with role_bias[role_id] = 1.0
new_weights = (gate_weights + role_bias) / 2.0
→ Preferred expert gets boosted from ~33% to ~65%
```

---

## 8. Tensor Factory

**File:** `backend/processing/tensor_factory.py`

Generates 3 visual tensor inputs (map, view, motion) for the RAP Coach model.

### Resolutions
- **Training:** 64×64 (smaller for speed)
- **Inference:** map=128×128, view=224×224

### Map Tensor — Tactical Overview (3 channels)

| Channel | Player-POV Mode | Legacy Mode |
|---------|----------------|-------------|
| Ch0 | Teammate positions (heatmap) | Enemy positions |
| Ch1 | Enemy positions (visible + last-known with decay) | Teammate positions |
| Ch2 | Utility zones + bomb marker (50 unit radius) | Player position |

### View Tensor — Player's Perspective (3 channels)

| Channel | Player-POV Mode | Legacy Mode |
|---------|----------------|-------------|
| Ch0 | FOV mask (90° cone, cos-weighted, Gaussian blurred) | FOV mask |
| Ch1 | Visible entities (distance-dimmed heatmap) | Danger zones |
| Ch2 | Active utility zones | Safe zones |

**FOV mask:** Cone from player yaw ± 45°, with Gaussian blur (sigma=3.0). View distance = 2000 game units.

### Motion Tensor — Movement Context (3 channels)

| Channel | Content |
|---------|---------|
| Ch0 | Trajectory trail (last 32 ticks, recency gradient) |
| Ch1 | Velocity radial gradient (max 4.0 units/tick at 64Hz) |
| Ch2 | Crosshair movement (yaw delta, max 45° per tick) |

### Normalization (P-TF-01)
When max value < 1.0, divides by 1.0 (not max) to avoid noise amplification. Preserves relative magnitude of weak signals.

---

## 9. Game Theory Engines

### 9.1 Bayesian Death Probability

**File:** `backend/analysis/belief_model.py`

Estimates "how likely is this player to die right now?" using Bayesian reasoning.

**Priors by HP bracket:**
- Full (80-100 HP): 35% base death rate
- Damaged (40-79 HP): 55% base death rate
- Critical (1-39 HP): 80% base death rate

**Weapon lethality multipliers:** rifle=1.0, AWP=1.4, SMG=0.75, pistol=0.6, shotgun=0.85, knife=0.3

**Threat level computation:**
```
threat = (visible_enemies + inferred_enemies × e^(-0.1 × info_age_seconds) × 0.5) / 5.0
```
Inferred enemies lose relevance over time (exponential decay with λ=0.1/s).

**Log-odds update (Bayesian posterior):**
```
log_odds = ln(prior / (1-prior))
  + threat × 2.0                        [more enemies = more danger]
  + (weapon_mult - 1.0) × 1.5           [AWP = +0.6, pistol = -0.6]
  + (armor_factor - 1.0) × -1.0         [armor reduces death rate]
  + (exposure_factor - 0.5) × 1.0       [position-dependent]

P(death) = 1 / (1 + e^(-log_odds))      [sigmoid conversion]
```

**Auto-calibration** from real match data (minimum 30 total samples, 10 per bracket):
- Recalibrates HP bracket priors from observed death rates
- Fits weapon lethality per class from actual kill counts
- Fits threat decay λ via least-squares on info_age → outcome
- All parameters bounded: priors [0.05, 0.95], lethality [0.1, 3.0], decay [0.01, 1.0]
- Saves CalibrationSnapshot to database (observability)

### 9.2 Expectiminimax Game Tree

**File:** `backend/analysis/game_tree.py`

Recursive minimax search with stochastic opponent modeling — the same algorithm family used in chess AI and poker bots.

**4 Available Actions:** push, hold, rotate, use_utility

**Tree structure:**
```
Root (MAX — our team picks best action)
  ├── PUSH → Chance Node (opponent responds probabilistically)
  │            ├── opponent PUSH (p=0.30) → evaluate leaf
  │            ├── opponent HOLD (p=0.40) → evaluate leaf
  │            ├── opponent ROTATE (p=0.20) → evaluate leaf
  │            └── opponent UTILITY (p=0.10) → evaluate leaf
  ├── HOLD → Chance Node ...
  ├── ROTATE → Chance Node ...
  └── USE_UTILITY → Chance Node ...
```

**Opponent probability adjustments by context:**

| Condition | Push | Hold | Rotate | Utility |
|-----------|------|------|--------|---------|
| Eco round (<$2000) | +25% | -25% | — | +15% |
| Full buy (>$4000) | -5% | +10% | +5% | — |
| T-side opponent | +5% | -5% | — | — |
| Outnumbered | -5% | +10% | — | -10% |
| Time < 30 seconds | +15% | -10% | — | +5% |
| Learned profile (≥10 rounds) | blend up to 70% learned | 30% base | | |

**State transitions per action:**
- PUSH: -1 alive each side, +0.15 map control
- HOLD: -15 seconds time
- ROTATE: -10s time, ±0.1 map control
- USE_UTILITY: -1 utility item, +0.05 map control

**Budget:** 1,000 nodes max (prevents OOM). Transposition table: 10,000 entries with FIFO eviction.

**Output:** Best action + estimated win probability for current state.

### 9.3 Momentum Tracker

**File:** `backend/analysis/momentum.py`

Tracks psychological momentum as a multiplier between 0.7 (tilted) and 1.4 (on fire):

```
Win streak of N:  multiplier = 1.0 + 0.05 × N × e^(-0.15 × round_gap)
Loss streak of N: multiplier = 1.0 - 0.04 × N × e^(-0.15 × round_gap)

Bounds: [0.7 (max tilt), 1.4 (max hot)]
Tilt threshold: < 0.85 (~3 losses in a row)
Hot threshold: > 1.2 (~4 wins in a row)
Resets at halftime (round 13 for MR12, round 16 for MR13)
```

### 9.4 Entropy Analysis

**File:** `backend/analysis/entropy_analysis.py`

Measures utility effectiveness in **bits of information** using Shannon entropy:

```
1. Discretize map into 32×32 grid (1,024 cells)
2. Count enemy positions per cell BEFORE utility
3. H_before = -Σ(pᵢ × log₂(pᵢ)) for occupied cells
4. Count positions AFTER utility lands
5. H_after = same formula
6. delta = H_before - H_after (positive = information gained)
7. effectiveness = delta / max_delta
```

**Max deltas by utility type:**
- Smoke: 2.5 bits (blocks line of sight for ~18s)
- Molotov: 2.0 bits (area denial for ~7s)
- Flash: 1.8 bits (3s blind window)
- HE: 1.5 bits (momentary position reveal)

### 9.5 Deception Index

**File:** `backend/analysis/deception_index.py`

```
composite = 0.25 × flash_bait_rate + 0.40 × rotation_feint_rate + 0.35 × sound_deception_score
```

- **Flash baits (25%):** % of flashes not blinding anyone within 128 ticks (~2 seconds)
- **Rotation feints (40%):** Direction changes > 108° relative to map extent (heaviest weight — positional deception matters most)
- **Sound deception (35%):** Inverse of crouch ratio (less crouching = more noise = potential info warfare)

### 9.6 Win Probability

**File:** `backend/analysis/win_probability.py`

Small neural network for real-time round win prediction:

```
12 features → Linear(64) + ReLU + Dropout(0.2)
           → Linear(32) + ReLU + Dropout(0.1)
           → Linear(1) + Sigmoid → [0, 1]
```

**The 12 input features:**
0. team_economy / 16,000
1. enemy_economy / 16,000
2. economy difference / 16,000
3. alive_players / 5
4. enemy_alive / 5
5. alive difference / 5
6. utility_remaining / 5
7. map_control_pct
8. time_remaining / 115
9. bomb_planted (0/1)
10. is_ct (0/1)
11. equipment ratio (clamped: min(team/enemy, 2) / 2)

**Deterministic safety boundaries:**
- 0 alive → 0.0% immediately
- 0 enemies → 100.0% immediately
- ±3 player advantage → force min 85% / max 15%
- Bomb planted → ±10% by side
- Economy diff > $8,000 → force min 65% / max 35%

### 9.7 Blind Spot Detection

**File:** `backend/analysis/blind_spots.py`

Compares player's actual actions to game-tree optimal actions:
- Classifies each situation (eco rush, post-plant, 1vN clutch, retake, etc.)
- Tracks mismatch frequency × impact (win probability delta)
- Top 3 by priority become coaching focus areas

### 9.8 Engagement Range Analysis

**File:** `backend/analysis/engagement_range.py`

Kill distance buckets with pro baselines per role:

| Range | Distance | AWPer | Entry | Support |
|-------|----------|-------|-------|---------|
| Close | < 500 units | 10% | 40% | 25% |
| Medium | 500-1500 | 30% | 40% | 45% |
| Long | 1500-3000 | 45% | 15% | 25% |
| Extreme | > 3000 | 15% | 5% | 5% |

Flags coaching observations when player deviates > 15% from role baseline.

### 9.9 Utility & Economy Analyzers

**File:** `backend/analysis/utility_economy.py`

**UtilityAnalyzer — Pro baselines:**
- Molotov: 35 damage/throw, 70% usage rate
- HE: 25 damage/throw, 50% usage rate
- Flash: 1.2 enemies blinded/flash, 80% usage rate
- Smoke: 0.9 strategic value, 90% usage rate

Effectiveness = player metric / pro baseline. Recommendations generated when score < 0.5.

**EconomyOptimizer — Buy round logic:**

| Money | Decision | Confidence |
|-------|----------|------------|
| ≥ $4,000 | Full buy | High |
| $2,000 - $3,999 | Force buy | Medium |
| $1,200 - $1,999 | Half buy (SMG) | Medium |
| < $1,200 | Eco | High |

Special round detection: pistol (round 1), halftime (MR12→round 13, MR13→round 16).

Output includes: action, confidence, recommended weapons, natural language reasoning.

---

## 10. COPER Coaching Pipeline

**File:** `backend/services/coaching_service.py`
**COPER = Context Optimized with Prompt, Experience, Replay**

### 4-Level Priority Fallback

```
Level 1: COPER (full pipeline — highest fidelity)
  Uses: Experience Bank + RAG Knowledge + Pro References
  Requires: map_name + tick_data
  Pipeline:
    1. Build ExperienceContext from tick_data
    2. Query Experience Bank for similar past situations
    3. Synthesize advice narrative
    4. Retrieve temporal baseline (pro comparison)
    5. Polish via Ollama Writer (local LLM)
    6. Collect feedback for future learning
    7. Persist CoachingInsight to database
  │
  ▼ fallback (if data missing)
Level 2: HYBRID (ML + RAG synthesis)
  Uses: HybridCoachingEngine merging ML predictions + knowledge
  Requires: player_stats
  │
  ▼ fallback
Level 3: TRADITIONAL + RAG (deviations + knowledge enhancement)
  Always available (only needs statistical deviations)
  Uses: Z-score formatted deviations + tactical knowledge entries
  │
  ▼ fallback
Level 4: TRADITIONAL (pure statistical deviations)
  Terminal fallback — always produces output
  Parses deviations, maps to focus areas, generates corrections
```

**Absolute rule:** System NEVER outputs zero coaching. Even on total failure, a generic insight is saved (C-01).

### Experience Bank
- Stores gameplay experiences with 384-dim vector embeddings
- Semantic similarity search (Sentence-BERT all-MiniLM-L6-v2, fallback to hash-based)
- FAISS vector index for O(log n) lookups
- Pro experiences weighted at 0.7 confidence, user at 0.5
- Output: SynthesizedAdvice with narrative, pro references, confidence, focus area

### RAG Knowledge Base
- Fed by HLTV pro player statistics (scraped from hltv.org — NOT demo files)
- ProStatsMiner creates TacticalKnowledge entries with archetypes:
  - STAR_FRAGGER (rating ≥ 1.15)
  - SNIPER (HS% ≥ 35%)
  - SUPPORT (KAST ≥ 72%)
  - ENTRY (opening duel win% ≥ 52%)
  - LURKER (clutch wins or multikill rate)
- Stores tactical knowledge with 384-dim embeddings for similarity search

### Post-Coaching Analysis (Non-Blocking)
After main coaching, these run in background:
1. **Phase 6 Analysis** via AnalysisOrchestrator (momentum, deception, entropy, game tree, engagement range)
2. **Longitudinal Trends** on last 10 matches (regression/improvement/volatility detection)
3. **Differential Heatmap** (on-demand from UI — user positions vs pro baselines)

---

## 11. Analysis Orchestrator

**File:** `backend/services/analysis_orchestrator.py`

Coordinates all Phase 6 analysis modules for a single match:

```
AnalysisOrchestrator.analyze_match(player, demo, rounds, ticks, states)
  │
  ├── _analyze_momentum()       → tilt zones, hot streaks
  ├── _analyze_deception()      → composite deception index
  ├── _analyze_utility_entropy() → utility impact in bits
  ├── _analyze_strategy()       → blind spots + game tree recommendations
  └── _analyze_engagement_range() → kill distance patterns
```

**Failure handling (F5-14):** Per-module failure counters. Log first 3 failures, then every 10th. Non-blocking — failures don't stop the main coaching pipeline.

**Output:** MatchAnalysis with per-round insights + match-level insights, all persisted to CoachingInsight table.

---

## 12. Training Orchestration

### Trigger: When Does Training Start?

Teacher daemon checks every 5 minutes:
```
pro_count = count(PlayerMatchStats WHERE is_pro=True)
last_count = CoachState.last_trained_sample_count

if pro_count ≥ last_count × 1.10:     → RETRAIN (10% growth threshold)
elif last_count == 0 AND pro_count ≥ 10: → FIRST TRAINING
else: sleep 300 seconds
```

### Thread Safety
Module-level `_TRAINING_LOCK` prevents concurrent training between daemon and UI.

### 5-Phase Training Cycle

**Phase 1: JEPA Pre-training (self-supervised)**
- Data: PlayerTickState rows (pro only, train split)
- Context windows padded to 10 ticks, target = 1 tick (next-step prediction)
- 5 cross-match negatives from pool of 500 cached samples
- Loss: InfoNCE contrastive
- Optimizer: AdamW(lr=1e-4, weight_decay=1e-4)
- Scheduler: CosineAnnealingLR(T_max=100)
- Early stopping: patience=10 on validation loss
- Checkpoint: `jepa_brain.pt`

**Phase 2: Professional Baseline (supervised)**
- Data: PlayerMatchStats (is_pro=True, train/val splits)
- 25 match-aggregate features → improvement deltas (Z-score normalized)
- Model: AdvancedCoachNN (legacy)
- Checkpoint: `latest.pt` (global directory)

**Phase 3: User Personalization (transfer learning)**
- Base: Phase 2 global model (warm start)
- Data: PlayerMatchStats (is_pro=False)
- Fine-tunes pro baseline on user's specific playstyle
- Checkpoint: `latest.pt` (user directory)

**Phase 4: RAP Behavioral Optimization (conditional)**
- Only runs if `USE_RAP_MODEL=True`
- Data: 320-tick contiguous windows from per-match databases
- Builds full map/view/motion tensors at 64×64 (training resolution)
- Computes advantage targets per tick:
  ```
  advantage = 0.4 × alive_diff + 0.2 × hp_ratio + 0.2 × equip_ratio + 0.2 × bomb_factor
  alive_diff = (team_alive - enemy_alive + 5) / 10  → [0, 1]
  bomb_factor = 0.7 (T planted) / 0.3 (CT planted) / 0.5 (no bomb)
  ```
- Classifies tactical role (10 classes):
  0=site_take, 1=rotation, 2=entry_frag, 3=support, 4=anchor,
  5=lurk, 6=retake, 7=save, 8=aggressive_push, 9=passive_hold
- Multi-task loss with Z-axis 2× penalty
- Optimizer: AdamW(lr=5e-5, weight_decay=1e-4)
- **Safety gate:** Aborts if zero-tensor fallback rate > 30%
- Checkpoint: `rap_coach.pt`

**Phase 5: Role Classification Head**
- Lightweight classifier for predicting player tactical role
- Non-fatal on failure
- Checkpoint: `role_head.pt`

### Maturity Gating
| Tier | Demos Processed | Coaching Confidence |
|------|----------------|-------------------|
| CALIBRATING | 0-49 | 50% (UI shows "Calibrating" overlay) |
| LEARNING | 50-199 | 80% |
| MATURE | 200+ | 100% (professional corrections unlocked) |

### Post-Training Steps
1. Increment maturity counter
2. Commit trained sample count (only AFTER success — prevents false triggers on crash)
3. Check meta-shift (compare pro stats before/after training — detects game meta changes)
4. Auto-calibrate belief model (Bayesian priors from real match outcomes)
5. Release `_TRAINING_LOCK`

---

## 13. Model Factory

**File:** `backend/nn/factory.py`

### Model Types
```
"default"   → TeacherRefinementNN (legacy)
"jepa"      → JEPACoachingModel
"vl-jepa"   → VLJEPACoachingModel
"rap"       → RAPCoachModel
"role_head" → NeuralRoleHead
```

### Checkpoint Names
- `"jepa"` → `jepa_brain.pt`
- `"vl-jepa"` → `vl_jepa_brain.pt`
- `"rap"` → `rap_coach.pt`
- `"role_head"` → `role_head.pt`
- `"default"` → `latest.pt`

### Checkpoint Loading Hierarchy
When loading a model, the system searches in order:
1. **User local:** `MODELS_DIR/user_id/version.pt`
2. **Global local:** `MODELS_DIR/global/version.pt`
3. **Bundled factory (user):** `get_resource_path(models/user_id/version.pt)`
4. **Bundled factory (global):** `get_resource_path(models/global/version.pt)`

**If NONE found → FileNotFoundError** (never silently uses random weights).
**If dimensions mismatch → StaleCheckpointError** (forces retraining).

**Atomic write protocol:**
1. Write to `.pt.tmp`
2. `fsync` (flush to disk)
3. `os.replace` (atomic on POSIX — no corruption on power loss)
4. Cleanup `.pt.tmp` on exception

---

## 14. GhostEngine Inference

**File:** `backend/nn/inference/ghost_engine.py`

The production inference engine that creates the "ghost" overlay on the tactical map.

### Per-Tick Inference Flow

```
Tick data (player state dict)
  │
  ▼
1. Check model loaded (if not → return (0, 0))
  │
  ▼
2. Build tensors via TensorFactory:
   map_t:    [1, 3, 128, 128]  tactical overview
   view_t:   [1, 3, 224, 224]  player's perspective
   motion_t: [1, 3, 224, 224]  movement context
   meta_t:   [1, 1, 25]        feature vector
  │
  ▼
3. Forward pass (no_grad):
   out = model(view=view_t, map=map_t, motion=motion_t, metadata=meta_t)
  │
  ▼
4. Decode position:
   optimal_delta = out["optimal_pos"]  → [1, 3] (dx, dy, dz)
   ghost_x = current_x + dx × 500.0
   ghost_y = current_y + dy × 500.0
   (Z-axis unused — CS2 maps are 2D-navigable)
  │
  ▼
5. Return (ghost_x, ghost_y) as world coordinates
```

**Error handling:** RuntimeError or any exception → log + return (0.0, 0.0). No exceptions reach UI.

**UI integration** (from `tactical_vm.py`): Lazy-loads GhostEngine only when user activates ghost mode. Loops through alive players, calls `predict_tick()` per player, replaces position with ghost coordinates.

### Current Limitations
- **No selective decoding:** Full forward pass every tick (see Section 15)
- **No stateful inference:** LSTM hidden state resets every tick
- **No batching:** batch_size=1 per player prediction
- **No embedding caching:** No reuse across sequential ticks

---

## 15. Selective Decoding

**File:** `backend/nn/jepa_model.py` (method `forward_selective`)

### Status: EXISTS but NOT USED by GhostEngine

The method is fully implemented but GhostEngine does full decoding every tick.

### How It Would Work

```
Tick N arrives → [B, seq_len, 25]
  │
  ▼
Context Encoder (ALWAYS runs — cheap, ~100k params)
  → curr_embedding [B, seq_len, 256]
  │
  ├── Mean Pool → curr_pooled [B, 256]
  │
  ├── Compare with prev_pooled from last tick:
  │     cosine_distance = 1.0 - cosine_similarity(curr, prev)
  │
  │     distance < 0.05? ─── YES ──► SKIP: return None, reuse last prediction
  │         │
  │        NO (state changed meaningfully)
  │         │
  ▼         ▼
LSTM (2 layers, 256→128)    ← EXPENSIVE (~500k params)
MoE gate (3 experts)         ← EXPENSIVE
tanh → prediction [B, 10]
  │
  ▼
Return: (prediction, curr_embedding, True)
Cache curr_embedding for next tick's comparison
```

**Savings potential:** During quiet moments (player holding an angle), could skip 60-80% of computation.

### Also Not Used: Stateful Inference (NN-40)

RAP model supports LSTM hidden state persistence across ticks:
```python
# What the model supports:
out = model(view, map, motion, metadata, hidden_state=cached_state)
# What GhostEngine actually does:
out = model(view, map, motion, metadata)  # No hidden_state → resets every tick
```

Enabling this would let the LSTM "remember" recent ticks, reducing jitter.

---

## 16. Tri-Daemon Session Engine

**File:** `core/session_engine.py`

Four background threads orchestrate all asynchronous work:

```
┌──────────────────────────────────────────────────────────┐
│                    SESSION ENGINE                         │
│                 (Main Keep-Alive Loop)                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  DAEMON A: SCANNER (Hunter)              Cycle: 10s     │
│  ├─ Watches filesystem for new .dem files                │
│  ├─ Two scans per cycle: is_pro=True, is_pro=False       │
│  ├─ Queues IngestionTask rows in database                │
│  └─ Signals _work_available_event                        │
│                                                          │
│  DAEMON B: DIGESTER                      Cycle: event   │
│  ├─ Consumes IngestionTask queue (1 per cycle)           │
│  ├─ 3-pass demo parsing → feature extraction             │
│  ├─ Validates data integrity                             │
│  ├─ Persists PlayerMatchStats, RoundStats, MatchTickState│
│  ├─ Zombie recovery: tasks stuck >5 min reset to queued  │
│  └─ Blocks on event when queue empty (no polling)        │
│                                                          │
│  DAEMON C: TEACHER                       Cycle: 300s    │
│  ├─ Monitors pro sample count growth (10% threshold)     │
│  ├─ Acquires _TRAINING_LOCK                              │
│  ├─ Runs full 5-phase training cycle                     │
│  ├─ Meta-shift detection + belief calibration            │
│  └─ Persists model checkpoints                           │
│                                                          │
│  DAEMON D: PULSE                         Cycle: 5s      │
│  ├─ Heartbeat timestamp for UI                           │
│  └─ Enables stall detection                              │
│                                                          │
│  SHUTDOWN: Parent writes "STOP" to stdin → all daemons   │
│  exit gracefully (5s join timeout)                        │
│                                                          │
│  STARTUP: Automated daily backup via BackupManager       │
│  + one-time knowledge base initialization                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Data ownership (no cross-daemon mutations):**
- Scanner owns IngestionTask creation
- Digester owns PlayerMatchStats/RoundStats/PlayerTickState creation
- Teacher owns model checkpoint creation + CalibrationSnapshot
- CoachingService owns CoachingInsight/CoachingExperience creation

---

## 17. Key Constants

| Constant | Value | Usage |
|----------|-------|-------|
| METADATA_DIM | 25 | Every model's input dimension |
| OUTPUT_DIM | 10 | Strategy/coaching output |
| JEPA latent_dim | 256 | Encoder/predictor/target latent space |
| RAP hidden_dim | 256 | Memory + strategy hidden dimension |
| RAP perception_dim | 128 | View(64) + Map(32) + Motion(32) |
| NUM_COACHING_CONCEPTS | 16 | VL-JEPA interpretability |
| LTC NCP units | 512 | 2× hidden for sparse wiring |
| Hopfield heads | 4 | Associative memory attention |
| MoE experts (RAP) | 4 | Strategy layer specialization |
| MoE experts (JEPA) | 3 | Coaching head specialization |
| RAP_POSITION_SCALE | 500.0 | Delta → world coordinate units |
| InfoNCE temperature | 0.07 | Contrastive distribution sharpness |
| EMA momentum | 0.996 | Target encoder lag (~250 steps) |
| GLOBAL_SEED | 42 | Reproducibility everywhere |
| BATCH_SIZE | 32 | Default training batch |
| RAP learning rate | 5e-5 | RAP optimizer |
| JEPA learning rate | 1e-4 | JEPA optimizer |
| Sequence length (RAP) | 320 | Training window in ticks (~5s at 64Hz) |
| Sequence length (JEPA) | 10 | Context window in ticks |
| Negative pool max | 500 | Cross-match negative cache |
| Map tensor (training) | 64×64 | Reduced for speed |
| Map tensor (inference) | 128×128 | Full resolution |
| View tensor (training) | 64×64 | Reduced for speed |
| View tensor (inference) | 224×224 | Full resolution |
| Experience embedding | 384-dim | Sentence-BERT output |
| Knowledge embedding | 384-dim | Sentence-BERT output |
| Win prob features | 12 | WinProbabilityNN input |
| Early stopping patience | 10 | Epochs without improvement |
| Drift Z-threshold | 2.5 | Feature distribution shift |
| Training lock timeout | ∞ | Non-blocking acquire only |
| Daemon heartbeat | 5 seconds | Pulse interval |
| Scanner cycle | 10 seconds | File system check |
| Teacher cycle | 300 seconds | Retraining check |
| Zombie task timeout | 5 minutes | Stuck task recovery |

---

## 18. Honest Engineering Assessment

### What's Genuinely Sound

1. **JEPA is real, published research** from Yann LeCun's team at Meta AI. The InfoNCE contrastive loss implementation is correct. The EMA target encoder anti-collapse mechanism works as intended.
2. **The 25-dim feature vector** captures essential game state with sensible normalizations: cyclic yaw encoding (sin/cos avoids the 359°→0° jump), bounded ranges, separate tactical context (features 20-24).
3. **Bayesian death probability** uses textbook log-odds updates with auto-calibration from real match data. The math is sound.
4. **Expectiminimax game tree** is a real algorithm from game AI research (chess, poker). Applying it to CS2 round decisions with adaptive opponent modeling is creative and defensible.
5. **COPER fallback chain** is solid production software engineering. "Never output zero coaching" with 4 levels of degradation is how production systems should work.
6. **Data pipeline** is well-built: 3-pass parsing, HMAC-signed caching, vectorized 10× speedup, temporal train/val/test splits, player decontamination, outlier removal.
7. **Atomic checkpoint writes** (write to .tmp → fsync → os.replace) prevent corruption on power loss.
8. **Tri-daemon architecture** with event-driven coordination is a reasonable design for this type of application.

### What's Overengineered

1. **RAP Coach is too complex for 11 demos.** ResNet perception + LTC neurons + Hopfield memory + Superposition gating + 4 MoE experts + Attribution + Position head + Value function = hundreds of thousands of parameters. You need 10,000× more data.
2. **Hopfield "prototypes" learn noise with this data scale.** Randomly initialized patterns + gradient descent with 11 demos = memorization, not generalization.
3. **LTC neurons** are designed for robotics/continuous-time control. Not clearly better than standard LSTM for discrete game ticks.
4. **"Superposition Layer"** is a standard gated linear layer. `linear(x) * sigmoid(gate(context))` — simple gating mechanism with an impressive name.
5. **CausalAttributor** uses crude proxies (`aggression = pos_delta × 0.5`) — not genuine causal reasoning.
6. **Sound deception metric** is just inverse crouch ratio — doesn't actually measure sound deception.
7. **Features built but not connected:** selective decoding, stateful inference, POV tensors all implemented but unused in production.

### Can It Beat Asking an LLM for CS2 Tips?

**Right now: No.** A language model trained on millions of CS2 discussions gives better general advice.

**The potential is fundamentally different:** Personalized, data-driven coaching based on YOUR actual replays is something a general LLM cannot do.

| Scenario | General LLM | This System (when trained) |
|----------|------------|--------------------------|
| "How to play B site?" | Generic best practices | "In YOUR last 50 rounds, you overpeek apartments 73% of the time and die. Pros hold from van." |
| "Am I good at utility?" | General utility tips | "Your flash effectiveness is 0.31. Pros average 0.68. You throw 40% of flashes without blinding anyone." |
| "Where should I be?" | Map callout guide | Ghost overlay showing exactly where you SHOULD stand at this tick |

### Path Forward

1. **Start simpler.** Prove a basic model (2-layer MLP or standard LSTM) can distinguish good from bad rounds before adding RAP complexity.
2. **Get more data.** 11→200 demos is a start, but complex architectures need thousands.
3. **Prove value incrementally.** Can the model predict round outcomes? Distinguish eco from full buy? If not, fix the foundation before adding layers.
4. **Game theory engines may be more valuable right now** — they work with rules and math, not training data, and could provide useful coaching TODAY.
