# Knowledge Transfer: utile_cs2 → Counter-Strike Coach AI

**Generated:** 2026-04-11 (v2 — rewritten against verified project state)
**Source directory:** `/media/admin/usb-ssd/PROIECT/utile_cs2/`
**Target project:** `Programma_CS2_RENAN/` inside `/media/admin/usb-ssd/Counter-Strike-coach-AI/Counter-Strike-coach-AI-main/`
**Purpose:** Deep cross-reference of available research, code, and data against the coaching project's *verified current state* and *confirmed* gaps.

---

## How to Read This Document

Each section follows a four-part structure:

1. **CURRENT STATE** — what the project actually implements right now (verified by code read, not assumed)
2. **PAPER DEPTH** — the full academic content from the source material, including equations, theorems, and design decisions that matter
3. **THE GAP** — what specifically is missing, confirmed absent via grep/read
4. **RECOMMENDATIONS** — concrete changes that respect project invariants (METADATA_DIM=25, tick decimation forbidden, feature flag system, etc.)

Sections are ordered from highest direct impact to lowest. Each recommendation specifies which feature flag, daemon, or module it affects.

---

## PROJECT CONTEXT

This section did not exist in v1. It is mandatory for anyone working on the project to understand before applying any recommendation.

### Architecture Overview

The project is a production-grade desktop application (`Programma_CS2_RENAN/`) with ~95K LOC across 397 Python files. It uses a **quad-daemon session engine** (`core/session_engine.py`) coordinating four background threads:

| Daemon | Role | Cycle |
|--------|------|-------|
| **Scanner** | HLTV pro stats scraping via FlareSolverr/Docker | 6 hours |
| **Digester** | Demo file parsing, feature extraction, DB storage | On event |
| **Teacher** | ML training (JEPA/RAP), drift detection, checkpointing | On data |
| **Pulse** | Health monitoring, backup, garbage collection | 60 seconds |

### Coaching Fallback Chain (4 levels)

The coaching pipeline has a cascading fallback with feature flags:

```
COPER (USE_COPER_COACHING=True)  ← DEFAULT, ACTIVE
  → Hybrid (USE_HYBRID_COACHING=False)
    → RAG (USE_RAG_COACHING=False)
      → Base (game theory engines — always available)
```

The COPER path uses: Experience Bank + RAG Knowledge + Pro References.
Game theory engines (9 implementations) are always available regardless of flags.

### Module Status Map

| Module | Status | Feature Flag | LOC |
|--------|--------|-------------|-----|
| JEPA (JEPACoachingModel + VLJEPACoachingModel) | Code-complete, **partially trained (not converged)** | `USE_JEPA_MODEL=False` | 1,102 |
| RAP Coach (LTC + Hopfield) | Experimental, **deferred to v0.5** | `USE_RAP_MODEL=False` | ~600 |
| Experience Bank | Production, active | (part of COPER) | 1,062 |
| Game Theory Engines (9 modules) | Production, active | Always on | ~3,500 |
| Win Probability NN | Production | Always on | 318 |
| Neural Role Head | Production | Always on | 326 |
| RAG Knowledge (SBERT + FAISS) | Production | (part of COPER) | 693 |
| Pro Bridge / Pro Baseline | Production | Always on | ~750 |

### Key Invariants

These are **non-negotiable constraints** that any recommendation must respect:

1. **METADATA_DIM = 25** — enforced by compile-time assertion in `vectorizer.py`. Both training (`StateReconstructor`) and inference (`GhostEngine`) share this single vectorizer. Expanding the vector dimension requires updating every consumer project-wide.
2. **Tick decimation STRICTLY FORBIDDEN** — all 128 ticks/sec are preserved.
3. **No `round_won` in training features** — outcome label isolation (P-RSB-03 leakage prevention).
4. **EMA target encoder `requires_grad=False`** — invariant NN-JM-04, enforced with RuntimeError.
5. **Hopfield bypass until >= 2 training forward passes** — invariant NN-MEM-01 + RAP-M-04.
6. **WAL mode enforced** on all three databases via `@event.listens_for`.
7. **Deterministic by default** — `GLOBAL_SEED=42` before all training.

### Current Blockers (from OPEN_PROBLEMS.md)

| ID | Problem | Impact |
|----|---------|--------|
| CI-01 | JEPA partially trained (not converged), needs full 50-100 epoch run | Blocks all JEPA-dependent coaching |
| CI-04 | Coach Book at 151 entries, target 1,500 | Limits RAG coaching depth |
| DP-04 | HLTV scraping CSS selectors drifted — only 3 pro players scraped | Blocks pro baseline expansion |
| CI-02 | No CS2 eval benchmark — can't measure coaching quality | Blocks quality assessment |

### Tri-Database Architecture

| Database | Purpose | Size |
|----------|---------|------|
| `database.db` (monolith) | Training data, player stats, 17.3M tick rows | 40 GB |
| `hltv_metadata.db` | Pro player stat cards from HLTV | Small |
| `match_data/<id>.db` (564 files) | Raw tick + event time-series per match | Varies |

---

## TIER 1 — Gaps Where Research Directly Fixes a Known Problem

---

### 1.1 · COPER Framework — Complete the Experience Bank

**Source:** `COPER_Agentic_Context.pdf` (ICLR 2026 under review)
**Target:** `Programma_CS2_RENAN/backend/knowledge/experience_bank.py` (1,062 lines)

#### Current State (Verified)

The Experience Bank is production-active as the core of the COPER coaching path. It implements:

- **`ExperienceContext`** dataclass with structured context matching (map, phase, side, position, health, equipment, teammates_alive, enemies_alive)
- **`compute_hash()`** — SHA-256 deterministic hash on `map:side:round_phase:position_area` for O(1) lookups
- **`add_experience()`** — stores with SBERT embedding (all-MiniLM-L6-v2), FAISS index signaling (AC-36-02)
- **`retrieve_similar()`** — FAISS vector search + cosine similarity fallback, min confidence threshold 0.3
- **`SynthesizedAdvice`** — narrative synthesis combining experiences + pro references
- **EMA effectiveness scoring** — `_MIN_EFFECTIVENESS_TRIALS = 5` (C-2 FIX), each observation shifts running average by 30%
- **Embedding serialization** — base64-encoded float32 (AC-32-01), 4x smaller than JSON, backward-compatible with legacy JSON format

What it does NOT have (confirmed absent via grep): TrueSkill uncertainty tracking, Update/Discard CRUD semantics, prioritized replay sampling, opponent-pool evaluation.

#### Paper Depth — The Full COPER Framework

The paper presents COPER as a weight-tuning-free framework with three synergistic mechanisms. The project currently implements only the Experience storage/retrieval part. The full framework is substantially richer:

**1. Context Optimization Loop (Section 3.1):**

COPER maintains a population of context candidates `C_g` (size N) at each generation `g`. Each candidate is evaluated via self-play against a fixed baseline using the *same base model* with different prompts. Bayesian skill estimates `(mu_c, sigma_c)` are maintained via TrueSkill (Herbrich et al., 2006). Selection uses a conservative lower-confidence bound:

```
S(c) = mu_c - kappa * sigma_c      (Eq. 1, kappa = 1 by default)
```

The next-generation population `C_{g+1}` is formed from an updated persistent candidate pool `CP` using **three proposal operators** (Section 3.1, page 5):

1. **Random proposals** — sample a playstyle from a fixed catalog, apply small length-bounded edits to the base context while preserving legality and interface constraints
2. **Crossover** — recombine high-scoring parents (by `S(c)`) at section- or sentence-level to propagate useful structure
3. **Experience-guided updates** — incorporate insights distilled from trajectory reflections into targeted prompt edits

This is a **genetic algorithm over prompt space**, not just a ranking system. The project's experience bank stores experiences but does not evolve the coaching prompt using them.

**Critical finding (Figure 1b):** Kendall's `tau_b` between prompt variants drops to **-0.504** (ranking reversals). Five nearly-equivalent prompts still flip pairwise outcomes. This quantifies why static prompts are unreliable — the project currently uses a fixed coaching prompt template.

**2. Experience Bank CRUD Semantics (Section 3.2, Eq. 3):**

The paper maintains a **permanent memory** `M` that persists across all generations. At the end of each generation `g`, completed trajectories `tau` together with final outcomes `r(tau)` and sampled intermediate states are collected. The LLM extracts **structured reflections** into typed insights (up to `kappa` per trajectory). Memory is updated via CRUD (Martin, 1983):

```
M <- (M \ D^{(g)}) ∪ U^{(g)} ∪ C^{(g)}      (Eq. 3)
```

Where:
- `D^{(g)}` = entries to **discard** (outdated or conflicting with new evidence)
- `U^{(g)}` = entries to **update** (matched by semantic similarity, effectiveness improved)
- `C^{(g)}` = entries to **create** (novel insights from unmatched items in working set `W^{(g)}`)

The matching for `U^{(g)}` requires a semantic similarity threshold (cosine > 0.9 in the embedding space). The project's FAISS index already supports this operation.

**Critical insight not in v1:** Retrieved memories are **injected into the operative prompt dynamically** at inference time. This is not "fetch similar entries and display them" — it is "edit the coaching system prompt to include relevant experience before generating advice." The coaching context `C = (q, M)` where `q` is the instruction prompt and `M` is the experience-derived knowledge.

**3. Prioritized Replay (Section 3.3, Eqs. 4–5):**

```
priority(tau) = 1 / N(tau)                                    (Eq. 4)
p_i = (priority(tau_i))^alpha / sum_j (priority(tau_j))^alpha  (Eq. 5)
```

Where `N(tau)` is the occurrence count, `alpha = 0.6` controls sharpness. Buffer capacity `B = 100,000`, replay gate `beta = 0.4` (fraction of games initialized from replay buffer). The buffer operates as a **sliding window** of capacity `B`, continuously refreshing with new data while retaining a diverse set of past plays.

**Empirical results (Table 2, GPT-4o-mini ablation):**

| Setting | TwoDollar | KuhnPoker | Briscola | Mean Win Rate |
|---------|-----------|-----------|----------|---------------|
| Baseline | 32.2% | 39.1% | 0.3% | 23.8% |
| + Prompt Optimization | 24.7% | 54.7% | 2.0% | 27.1% |
| + Experience | 48.7% | 57.2% | 38.4% | 48.1% |
| + Replay | 52.4% | 55.6% | 42.7% | **50.2%** |

The experience bank is the **core contributor** (+21 pp mean win rate). Prompt optimization alone is unreliable (+3.3 pp). Replay adds a further +2.1 pp by revisiting rare informative states.

**4. Full-Context Evaluation and Opponent Pool (Section 2, page 3):**

Each round consists of two games with **swapped first-move order** to remove first-move bias. The evaluated agent's win rate in game `g` under context `C_r` is averaged over all opponents in pool `E` and `k` rounds. This opponent-pool evaluation prevents overfitting to a single opponent style — the project's experience bank currently treats all coaching advice as opponent-agnostic.

**5. Cross-Game Transfer (Section 5, Table 3):**

Protocol-level skills (turn management, action formatting, short-horizon planning) transfer effectively across game families. But transfer is **directionally asymmetric** — negotiation strategies from TwoDollar improve SimpleNegotiation (+5.6%), but the reverse is negligible (-0.2%). This implies that coaching strategies learned from one map or game mode may not automatically transfer to another.

**6. Computational Efficiency (Table 5):**

COPER uses only **91K output tokens** (one-quarter of MIPRO's 354K, 20% fewer than GEPA's 113K). This matters for the project because Ollama inference on llama3.1:8b has measurable latency.

#### The Gap

1. **No uncertainty tracking per experience** — no `sigma` tracking, so the system cannot distinguish between a highly-validated experience (used 50 times, always good) and a fresh untested one
2. **No CRUD semantics** — the bank only adds entries via `add_experience()`. There is no `update_experience()` for matched items or `discard_experience()` for contradicted ones. Over time, stale advice accumulates.
3. **No prioritized replay** — all experiences are scored by composite similarity, not biased toward infrequently-visited coaching scenarios
4. **No opponent modeling** — experiences don't track which opponent style they were effective against
5. **No prompt evolution** — the coaching prompt template is static, not evolved via the genetic algorithm
6. **No Kendall's tau stability measurement** — no way to quantify whether the coaching system is producing stable recommendations across prompt variants

#### Concrete Recommendations

**A. Add TrueSkill uncertainty to `CoachingExperience` (db_models.py):**

```python
# Add to CoachingExperience table in backend/storage/db_models.py:
mu_skill: float = Field(default=0.5)          # TrueSkill posterior mean
sigma_skill: float = Field(default=0.5)       # TrueSkill posterior std
times_retrieved: int = Field(default=0)
times_validated: int = Field(default=0)       # user confirmed good advice

def confidence_score(self, kappa: float = 1.0) -> float:
    """TrueSkill lower-confidence bound (Eq. 1) — prefer high-certainty experiences."""
    return self.mu_skill - kappa * self.sigma_skill
```

**B. Implement CRUD on the experience bank (experience_bank.py):**

When inserting a new experience:
1. Query FAISS index for cosine similarity > 0.9 matches (semantic duplicate detection)
2. If match found: Update via `U^{(g)}` — exponential moving average on `effectiveness_score`, increment `times_retrieved`, adjust `mu_skill`/`sigma_skill`
3. If contradiction found (same `context_hash`, different `action_taken`, new entry has higher `delta_win_prob`): Discard via `D^{(g)}` — mark old entry's confidence to 0.0, insert new with merged uncertainty
4. If no match: Create via `C^{(g)}` — standard `add_experience()` path

**C. Implement replay priority sampling (experience_bank.py):**

```python
REPLAY_ALPHA = 0.6   # sharpness (paper: alpha=0.6, Eq. 5)
REPLAY_GATE = 0.4    # fraction of coaching queries that draw from replay (paper: beta=0.4)

def sample_for_replay(self, k: int = 5) -> List[CoachingExperience]:
    """Sample k experiences biased toward infrequently-retrieved ones (Eq. 4-5)."""
    all_exp = self._get_all_experiences()
    priorities = np.array([1.0 / max(e.times_retrieved, 1) for e in all_exp])
    probs = (priorities ** REPLAY_ALPHA) / (priorities ** REPLAY_ALPHA).sum()
    indices = np.random.choice(len(all_exp), size=min(k, len(all_exp)), replace=False, p=probs)
    return [all_exp[i] for i in indices]
```

**D. Add active prompt editing with retrieved experiences (coaching_dialogue.py):**

When the coaching service generates advice, inject the top-k retrieved experiences directly into the LLM system prompt. This is the "agentic context" the paper's title refers to — the prompt is edited *per-query* based on what the experience bank retrieves.

**NOTE:** This affects the COPER coaching path (currently active, `USE_COPER_COACHING=True`). No feature flag changes needed. Database migration required for new columns.

---

### 1.2 · LTC+MHN Additive Coupling — Replace Binary Hopfield Bypass

**Source:** `Additive_Coupling_of_Liquid_NN_and_MHL.pdf` (ICLR 2026 submission)
**Target:** `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/memory.py` (201 lines)

**STATUS NOTE:** RAP Coach is **deferred to v0.5** (`USE_RAP_MODEL=False`). These recommendations should be implemented when RAP is reactivated. The reactivation criteria are documented in ENGINEERING_HANDOFF.md section 31.

#### Current State (Verified)

`RAPMemory` (memory.py) implements:

- **LTC layer** via `ncps` library with `AutoNCP` wiring — brain-like sparse connectivity
- **0.3 output ratio** (RAP-AUDIT-07): 154 motor neurons (30%), 143 command (28%), 215 inter (42%) — down from 0.5 ratio
- **Deterministic NCP wiring** via numpy seed 42 + torch seed 42 (NN-45 + NN-MEM-02)
- **LTC projection** (154-dim NCP output → 256-dim hidden) via `nn.Linear`
- **HopfieldLayer** (Ramsauer et al., ICLR 2021): 32 learnable prototypes x 256-dim = 8,192 parameters, 4 heads, trainable
- **Binary bypass** (NN-MEM-01 + RAP-M-04): Hopfield output is `torch.zeros_like(ltc_out)` until `_training_forward_count >= 2`. Then `combined_state = ltc_out + mem_out` (simple residual addition)
- **Belief head**: Linear(256) → SiLU → Linear(64) — produces 64-dim belief state vector
- **RAPMemoryLite**: LSTM fallback when `ncps`/`hflayers` unavailable — same interface contract

The combination is `ltc_out + mem_out` — a **fixed equal-weight residual**, not learnable additive coupling.

#### Paper Depth — Full LTC+MHN Architecture

**LTC ODE (Section 3.1, Eq. 1):**

```
dx(t)/dt = -(1/tau + f_theta(x(t), I(t))) * x(t) + f_theta(x(t), I(t)) * A
```

Where `tau in R^n` is a learnable base time constant, `A in R^n` is a saturation vector, `f_theta` is a shared MLP. The paper explicitly states: "For stable and accurate integration, we discretize Eq. 1 using a **fourth-order Runge-Kutta solver**" (page 4, line 172). The `ncps` library's default LTC implementation uses an ODE solver, but the specific integration order depends on the `ode_unfolds` parameter. The paper found Euler integration causes instability with stiff time constants.

**Lemma 1 (Boundedness of LTC states, page 4):** If `x(0)` is bounded and `f_theta` is Lipschitz-continuous with bounded range, then `x(t)` remains bounded for all `t >= 0`. Proof sketch: the system can be written as `x_dot = g(x, I)` where `g` is Lipschitz and coercive. Standard ODE stability results imply forward completeness.

**MHN Query and Retrieval (Section 3.2, Eqs. 2–3):**

```
q(t) = W_q * x(t),   W_q in R^{M x n}                              (Eq. 2)
r(t) = sum_i softmax_i(beta * q(t)^T * xi_i) * xi_i                 (Eq. 3)
```

Where `beta > 0` is inverse temperature controlling retrieval sharpness.

**Lemma 2 (Contraction property of MHN, page 4):** Suppose `||q(t)|| <= R` and `||xi_i|| <= S` for all `i`. Then the mapping `q -> r` defined in Eq. 3 is Lipschitz with constant `L < 1`, making it a contraction. **Proof sketch:** The retrieval can be viewed as a softmax-weighted convex combination of bounded vectors. Differentiating with respect to `q` yields Jacobian entries bounded by `beta * R * S` under softmax normalization. For sufficiently small `beta` or bounded `R * S`, `L < 1` holds, guaranteeing contraction. **Full proof in Appendix B.**

This is the **mathematical stability condition** the project needs: with `beta = 0.25` and bounded prototype norms, contraction is guaranteed. If `beta` is set too high or prototypes grow unbounded, the retrieval becomes unstable.

**Additive Coupling (Section 3.3, Eq. 4):**

```
z(t) = alpha * x(t) + delta * r(t)                                  (Eq. 4)
```

Where `alpha, delta >= 0` are **learnable scalars** (not fixed weights, not a gating matrix). This is the core design choice — simpler than gated controllers, avoids destructive interference from high-dimensional gating matrices.

**Lemma 3 (Boundedness of coupled state):** If `x(t)` and `r(t)` are bounded, then `z(t)` is bounded for all `t`. Directly from Eq. 4: `||z(t)|| <= alpha * ||x(t)|| + delta * ||r(t)||`.

**Lemma 4 (Gradient smoothing, page 5):** Let `L` be a differentiable loss. Then the gradient through `z(t)` decomposes as:

```
nabla_x L = alpha * nabla_x L + delta * nabla_r L
```

Coupling acts as a **convex combination of gradient flows**, reducing variance and aiding convergence. This is WHY additive coupling helps with cold-start instability — it doesn't eliminate the problem (delta starts small), but it provides a smooth gradient path through both the LTC dynamics and the memory retrieval.

**Proposition (Stability of the coupled system, page 5):** By Lemmas 1-3, the coupled system admits bounded hidden states under bounded inputs. By Lemma 2, retrieval is contractive, and by Lemma 4, gradients are smoothed. Together, these ensure stable forward dynamics and more regular optimization landscapes.

**Training Hyperparameters (Section 4.1):**

| Parameter | Paper Value | Project Current |
|-----------|------------|-----------------|
| Optimizer | Adam | — (RAP not trained yet) |
| Learning rate | 0.001 | — |
| Batch size | **256** | 32 (general `BATCH_SIZE` in nn/config.py) |
| Hopfield size M | 16 prototypes | 32 prototypes |
| Scaling factor beta | **0.25** | Not explicitly set (hflayers default) |
| Number of heads | 4 | 4 (matches) |
| Validation split | 10% | — |
| LTC integration | **4th-order Runge-Kutta** | ncps default |

**Ablation results (Table 2, 34 CTR23 datasets):**

- **No-MHN** (vanilla LTC): baseline RMSE
- **Zero beta** (uniform retrieval): moderate improvement on stable datasets, fails on high-variance data
- **Matched LNN** (same parameter count, no memory): no improvement — gains are from *memory*, not parameter count
- **Full additive coupling**: best on 29/34 datasets, mean RMSE gain +10.42%, median +5.37%

**Critical limitation (Section 5.3):** Memory staleness. In dynamic or non-stationary settings (opponents adapting, map meta changing), stored prototypes become outdated, diminishing corrective utility. Paper recommends **online replacement or episodic refresh strategies**.

**Loss landscape analysis (Section 5.1):** On California Housing, Brazilian Houses, and Diamonds, baseline LTC produced jagged profiles with sharp walls, fragmented basins and sharp spikes. The proposed model displays smoother bowls of wider curvature, consistent with flatter minima and more stable optimization.

#### The Gap

1. **Binary bypass instead of learnable additive coupling** — `combined_state = ltc_out + mem_out` is an equal-weight residual. The paper's learnable `alpha, delta` scalars allow the system to naturally transition from pure LTC (delta near 0) to coupled mode as prototypes become meaningful. This elegantly solves the cold-start problem that NN-MEM-01 addresses with a hard binary gate.
2. **No explicit RK4 integration specification** — the `ncps` LTC uses an ODE solver, but whether it's RK4 or Euler depends on the `ode_unfolds` parameter. The paper shows Euler causes instability with stiff time constants.
3. **No episodic prototype refresh** — when the Pulse daemon detects drift, there is no mechanism to refresh the Hopfield prototypes
4. **Batch size mismatch** — the project's general `BATCH_SIZE=32` is insufficient for LTC+MHN. The paper used 256.

#### Concrete Recommendations

**A. Replace binary bypass with additive coupling (memory.py):**

```python
# Replace NN-MEM-01 binary bypass with learnable coupling
self.alpha = nn.Parameter(torch.tensor(1.0))   # start at pure LTC
self.delta = nn.Parameter(torch.tensor(0.01))  # start near-zero for cold start

def forward(self, x, hidden=None, timespans=None):
    ltc_out, hidden = self.ltc(x, hidden, timespans=timespans)
    ltc_out = self.ltc_projection(ltc_out)
    mem_out = self.hopfield(ltc_out)
    # Learnable additive coupling (Eq. 4) — no binary bypass needed
    alpha = F.softplus(self.alpha)  # ensure alpha >= 0
    delta = F.softplus(self.delta)  # ensure delta >= 0
    combined_state = alpha * ltc_out + delta * mem_out
    belief = self.belief_head(combined_state)
    return combined_state, belief, hidden
```

This eliminates the `_hopfield_trained` flag, `_training_forward_count`, and the `torch.zeros_like(ltc_out)` bypass entirely. The `softplus` constraint ensures non-negativity (Eq. 4 requires `alpha, delta >= 0`).

**B. Set beta = 0.25 explicitly in HopfieldLayer:**

```python
self.hopfield = HopfieldLayer(
    input_size=hidden_dim,
    output_size=hidden_dim,
    num_heads=4,
    quantity=32,
    trainable=True,
    scaling=0.25,  # Paper's beta = 0.25, conservative for contraction guarantee
)
```

**C. Add RAP-specific batch size constant (nn/config.py):**

```python
RAP_BATCH_SIZE = 256   # From LTC+MHN paper Section 4.1 (vs general BATCH_SIZE=32)
```

**D. Implement episodic prototype refresh in the Pulse daemon:**

When drift is detected, compute the centroid of the most recent N JEPA embeddings and reset `self.hopfield.lookup_weights` to these centroids. This addresses the memory staleness limitation (Section 5.3).

**NOTE:** RAP Coach is `USE_RAP_MODEL=False`. Apply these changes when reactivating per ENGINEERING_HANDOFF.md section 31 criteria.

---

### 1.3 · MLMove — New Movement Quality Coaching Dimension

**Source:** `Learning_to_Move_Like_Professional_Counter_Strike_Players.pdf` (SIGGRAPH 2024, Stanford/Activision/NVIDIA)
**Target:** No existing module — this is a **new coaching dimension** not currently covered.

#### Current State (Verified)

The project has analysis modules for strategic weaknesses (`blind_spots.py`, 219 lines), combat distance analysis (`engagement_range.py`, 441 lines), entropy analysis (`entropy_analysis.py`, 182 lines), and momentum tracking (`momentum.py`, 217 lines). None of these evaluate **how a player moves** — they evaluate what happened (kills, deaths, positions) but not the movement quality that led there.

The 25-dim feature vector includes position (`pos_x`, `pos_y`, `pos_z` at indices 9-11) and velocity-related features (`is_crouching` at index 5), but does not include movement direction, speed category, or position transition metrics.

Movement quality is **confirmed absent** via grep: no `movement_quality`, `MovementMetrics`, `map_coverage`, `high_ground`, or `over_aggression` exist in the codebase.

#### Paper Depth — Full MLMove Architecture and Findings

**Dataset: CSKnow (Section 5):**

123 hours of CS:GO professional gameplay at **16 Hz (62.5ms intervals)**, from HLTV logs of de_dust2 between April 2021 and November 2022. Filtered to CS:GO Retakes mode only:
- 2,292 unique players
- 513K shots, 29K eliminations
- 1,430 rounds across competitive maps
- Retakes-specific: bomb already planted, 40-second explosion timer, 3 defense vs 4 offense

**Why Retakes specifically (Section 3, page 3):** The paper restricts to Retakes to control complexity. Full competitive CS:GO has 15-round halves with economy, utility purchases, and complex macro-strategy. Retakes starts with the bomb planted, fixed equipment, and a 40-second window — making the decision space tractable for a learned movement model while still requiring team coordination.

**Critical philosophical distinction (Section 7, page 7):** "The objective of playing like an expert human in a team setting is NOT the same as playing to win." The paper explicitly states this. For a coaching system, this is fundamental — you want to teach team coordination patterns, not superhuman strategies that work only for bots. Human evaluators rated MLMove bots as more human-like (TrueSkill ~40) than rule-based bots (TrueSkill ~25), matching actual human play.

**Model Architecture (Section 4.1, Figure 2):**

1. **Input:** 10 player tokens (1 per player), each containing: position (x, y, z), velocity (vx, vy, vz), view direction (yaw, pitch), alive state, team side
2. **Per-Player Embedding:** Each token → 3 embedded tokens via 3-layer MLP (Linear → LeakyReLU → Linear → LeakyReLU → Linear) + sinusoidal position encoding + temporal position encoding. **This 1→3 token expansion is critical** — it gives the attention mechanism more "slots" to reason about each player.
3. **Scene Transformer Encoder:** Standard transformer with **masked attention** — masks applied for eliminated players. Without masking, the model fails to learn inter-player relationships (Table 3: NoATTN Kill Locations EMD = 10.3 vs MLMove 6.7).
4. **Output:** 30 tokens (3 movement command tokens per player) → softmax → **discrete movement distribution**

**Discrete Action Space (Section 4.1, page 5):** Movement commands are discretized into **48 tokens**: 16 angular directions x 3 speed categories (walk/run/jump) + fire command. This is fundamentally different from predicting continuous movement vectors — the model outputs a probability distribution over discrete actions, which naturally captures uncertainty (a player might go left or right with different probabilities).

**Integration with Game (Section 4.2, Figure 3):** MLMove outputs movement commands every 125ms (8 game ticks). A rule-based execution module converts movement commands to keyboard actions for aiming and firing. The aiming module uses a probabilistic occupancy map for target prediction when no enemy is visible.

**Performance (Table 1):**

| EMD Type | MLMove | RuleMove | GameBot |
|----------|--------|----------|---------|
| Map Occupancy | **8.2 +/- 0.5** | 14.7 +/- 1.7 | 15.2 +/- 0.3 |
| Kill Locations | **6.7 +/- 0.1** | 15.4 +/- 0.7 | 16.4 +/- 0.7 |
| Lifetimes | **4.9 +/- 0.4** | 7.8 +/- 0.0 | 1.1 +/- 0.0 |
| Shots Per Kill | **2.1 +/- 0.1** | 5.6 +/- 0.0 | 4.9 +/- 0.2 |

**Training (Section 4.1, page 5):** 5.4M parameters, trained for 20 epochs, batch size 1024, initial LR 4e-5, Adam optimizer, weight decay 0, betas (0.9, 0.999), eps 1e-08. Training takes 1.5 hours on Intel i7-12700K + NVIDIA RTX 4090. Inference: **< 0.5ms per game step** on single CPU core (0.6ms IQR on Xeon 8375C).

**Four Ground-Truth Coaching Mistakes (Section 6.3.2, Figure 6, page 9):**

Human evaluators identified these common positioning mistakes:

1. **Leaving high ground unnecessarily** — defensive mistake, quantified in Figure 6 (MLMove: ~80 rounds, Human: ~80, RuleMove: ~140, GameBot: ~150)
2. **Leaving established positions prematurely** — similar pattern (MLMove: ~80, Human: ~90, RuleMove: ~120, GameBot: ~140)
3. **Being overly aggressive when trading** — two teammates must be in the right place for a trade kill; overly aggressive players push without support
4. **Being overly passive when supporting** — failing to push when a teammate creates an opening

These are **directly actionable coaching feedback categories** that the project's `blind_spots.py` could detect.

**Key Ablation (Table 3):**

| EMD Type | MLMove | NoATTN | HISTORY |
|----------|--------|--------|---------|
| Map Occupancy | **8.2 +/- 0.5** | 10.3 | 11.8 |
| Kill Locations | **6.7 +/- 0.1** | 8.2 | 7.4 |
| Shots Per Kill | **2.1 +/- 0.1** | 2.2 | 1.2 |

- **NoATTN**: Removing attention degrades map occupancy (+2.1 EMD) and kill locations (+1.5 EMD) — attention is critical for team-wide movement coordination
- **HISTORY**: Adding prior states causes the inertia problem — players repeat prior actions rather than responding to dynamic changes. Current-state-only attention beats history.

#### The Gap

The project knows WHERE a player was (features 9-11: pos_x, pos_y, pos_z) but cannot evaluate HOW they moved. A player can visit the right areas inconsistently or avoid key areas entirely — the project currently cannot distinguish these patterns. The four coaching mistakes identified by human evaluators (leaving high ground, leaving positions, over-aggressive trading, over-passive supporting) are exactly the kind of feedback a CS2 coaching AI should provide.

#### Concrete Recommendations

**A. Create a new movement quality analysis module (backend/analysis/movement_quality.py):**

```python
@dataclass
class MovementMetrics:
    map_coverage_score: float        # fraction of key positions visited
    high_ground_utilization: float   # time in elevated positions / total time
    position_transitions: int        # number of position changes per round
    passive_time_ratio: float        # seconds stationary / round length
    position_abandonment_rate: float # leaving established positions prematurely
    trade_positioning_score: float   # proximity to teammates during engagements

# Reference EMDs from MLMove paper Table 1 for comparison:
PROFESSIONAL_BENCHMARKS = {
    "map_occupancy_emd": 8.2,    # lower = more human-like
    "kill_location_emd": 6.7,
    "shots_per_kill": 2.1,
    "lifetime_emd": 4.9,
}
```

**B. Implement the 4 coaching mistake detectors (extend blind_spots.py):**

Each of the four MLMove-identified mistakes can be detected from existing tick data:

1. **High ground abandonment**: Track `pos_z` changes — flag when a player moves from elevated to lower position without enemy contact
2. **Premature position abandonment**: Track position stability — flag when a player leaves a position they held for >3 seconds without new information
3. **Over-aggressive trading**: Detect when a player pushes within 5 seconds of teammate death without another teammate nearby
4. **Over-passive supporting**: Detect when a player is within audio range of teammate engagement but doesn't advance

**C. Discrete action tokenization for movement comparison:**

The paper's 48-token action space (16 directions x 3 speeds) can be used to bucket observed player movement from tick data. The vectorizer's `view_yaw_sin` (index 12) and `view_yaw_cos` (index 13) can be converted to angular direction, and velocity (derivable from position deltas) can be bucketed into walk/run/jump. This creates a **movement action distribution** per player that can be compared against professional distributions.

**NOTE:** This does NOT modify METADATA_DIM=25. Movement metrics are computed as **derived features** from existing tick data, stored in a separate analysis result, not added to the feature vector.

---

### 1.4 · Growing-Window Temporal Validation — Correctness Fix

**Source:** `Counter_Strike_ML.pdf` (Ondrej Svec, CTU Prague, January 2022)
**Target:** `Programma_CS2_RENAN/tests/` (87 test files), `Programma_CS2_RENAN/backend/nn/dataset.py`

#### Current State (Verified)

No growing-window temporal validation is enforced. The `DatasetSplit` enum in `db_models.py` has `TRAIN`, `VAL`, `TEST`, `UNASSIGNED` — but there is no mechanism enforcing temporal ordering of splits. Standard random splits on temporally-ordered demo data leak future information into training.

#### Paper Depth

The thesis tests three sample representations (player features, roster features, match history) and finds that **Elo/TrueSkill-based features are the most important predictors** (Section 6.4), achieving 64% accuracy with Elo rating difference alone.

**Growing-window validation (Section 5.1.4):**

```
Training: matches from [t_0, t_train]
Validation: matches from [t_train, t_val]
Test: matches from [t_val, t_end]
```

The window grows forward in time. This prevents data leakage from future matches into training.

**Minimum match count filter:** Players with fewer than 50 matches are excluded to prevent overfitting to low-activity players.

**1D Convolution for recency (Section 5.2.3):** Using 1D convolutions over the sequence of recent matches implicitly captures form (recent performance trajectory) better than simple aggregation. This is a feature engineering insight — treating the last N matches as a time series rather than averaging them.

#### Concrete Recommendations

**A. Add growing-window validation to the dataset split logic (backend/nn/dataset.py):**

```python
def assign_temporal_splits(demos: List, train_ratio=0.7, val_ratio=0.15):
    """Growing-window: never train on future data."""
    sorted_demos = sorted(demos, key=lambda d: d.match_date)
    n = len(sorted_demos)
    for d in sorted_demos[:int(n * train_ratio)]:
        d.dataset_split = DatasetSplit.TRAIN
    for d in sorted_demos[int(n * train_ratio):int(n * (train_ratio + val_ratio))]:
        d.dataset_split = DatasetSplit.VAL
    for d in sorted_demos[int(n * (train_ratio + val_ratio)):]:
        d.dataset_split = DatasetSplit.TEST
```

**B. Add minimum match count filter:** Exclude players with fewer than 10 demos from training to prevent overfitting to low-activity players.

**NOTE:** This is a correctness fix, not a feature. All temporal models in the project should use growing-window validation.

---

## TIER 2 — Enhancements to Already-Implemented Modules

---

### 2.1 · VL-JEPA — What's Done vs. What the Paper Still Adds

**Source:** `VL_jepa.pdf` (Meta FAIR, December 2025)
**Target:** `Programma_CS2_RENAN/backend/nn/jepa_model.py` (1,102 lines), `backend/nn/jepa_trainer.py` (403 lines)

#### Current State (Verified — THIS IS NOT "LIMITED 2/10")

The project's JEPA implementation is **1,102 lines of production code** with:

- **`JEPAEncoder`**: Linear(input_dim, 512) → LayerNorm → GELU → Dropout(0.1) → Linear(512, latent_dim=256) → LayerNorm
- **`JEPAPredictor`**: Linear(256, 512) → LayerNorm → GELU → Dropout(0.1) → Linear(512, 256) — predicts in latent space
- **`JEPACoachingModel`**: Hybrid JEPA + 2-layer LSTM(256→128) + Top-2 Sparse MoE (J-3 FIX, Shazeer et al. 2017, Fedus et al. 2021) + sigmoid output (WR-52 fix)
- **`forward_jepa_pretrain()`**: Context encoder + target encoder (no_grad, P1-07) → average pool → predictor
- **`forward_selective()`**: **Already implemented** — cosine distance thresholding for selective decoding. If `distance.mean() < threshold`, skip decoding. Handles batch mode.
- **`update_target_encoder()`**: EMA update with NN-JM-04 RuntimeError guard on `requires_grad`
- **`jepa_contrastive_loss()`**: InfoNCE with normalized embeddings, temperature 0.07, in-batch negatives
- **`VLJEPACoachingModel`**: Extends JEPA with 16 coaching concepts:
  - Learnable concept embeddings (`nn.Embedding(16, 256)`)
  - Concept projector (Linear → GELU → Linear)
  - Learned temperature parameter (`nn.Parameter(0.07)`)
  - `forward_vl()` returning concept_probs, concept_logits, top_concepts, coaching_output, latent
  - `get_concept_activations()` — lightweight inference path (no LSTM/MoE)
- **`vl_jepa_concept_loss()`**: Multi-label BCE + **VICReg-inspired diversity regularization** (penalizes concept embedding collapse via std across concepts)
- **`ConceptLabeler`**: Two modes:
  - `label_from_round_stats()` — outcome-based (kills, deaths, utility usage, round_won), **no label leakage** (G-01 fix)
  - `label_tick()` — heuristic fallback from 25-dim features, **explicitly warned for label leakage** (NN-JM-03)
  - J-2 FIX: Hard-gates heuristic fallback out when RoundStats unavailable
- **Training (jepa_trainer.py)**: AdamW + cosine annealing + J-6 EMA cosine momentum schedule + drift monitoring + gradient clipping

**CRITICAL STATUS:** The JEPA checkpoint (`jepa_brain.pt`, 3.7 MB, 945,614 params) is **partially trained** — Deep Audit weight forensics show 10-50 epochs across multiple restarts since January 2026, but the model has not converged. The 17.3M available tick rows have been partially used. **The bottleneck is sustained training to convergence, not implementation.**

#### What the Paper Adds Beyond Current Implementation

The VL-JEPA paper (Meta FAIR) describes an architecture that differs from the project's implementation in several important ways:

**1. Frozen Pretrained Vision Backbone (Section 3.1, critical):**

The X-Encoder is a **frozen V-JEPA 2 ViT-L/16** (Assran et al., 2025) at 256x256 resolution, compressing visual input into 336 visual tokens. The key word is *frozen* — it is not trained from scratch. **Ablation (Table 5):** Without pretraining, classification drops from 79.1% to **27.3%**. This is the single most important finding for the project's VL-JEPA path.

The project's `JEPAEncoder` is a 2-layer MLP trained from scratch. For CS2 tick data (not images), a pretrained vision backbone is not directly applicable, but the principle is: **the encoder needs sufficient pretraining before the concept alignment head can learn meaningful concepts.** This is exactly what CI-01 (run JEPA pretraining) addresses.

**2. Y-Encoder is EmbeddingGemma-300M (Section 3.1, page 3):**

The target text embedding is produced by `EmbeddingGemma-300M` (Vera et al., 2025) — a 300M parameter model from Google, not a standard `nn.Embedding` layer. This provides rich textual representations for the training targets. The project uses outcome-based labels (float vectors), not text targets, so this is architecturally different.

**3. Learning Rate Multiplier 0.05x for Text Encoder (Section 4.6, Table 5):**

"Setting a learning rate multiplier of ×0.05 to all text encoder parameters improves performance." Without this, text embedding quality degrades early in training. The project should apply a similar reduced learning rate to the concept embedding parameters:

```python
# In jepa_trainer.py, when creating optimizer:
concept_params = [p for n, p in model.named_parameters() if 'concept' in n]
other_params = [p for n, p in model.named_parameters() if 'concept' not in n]
optimizer = AdamW([
    {'params': other_params},
    {'params': concept_params, 'lr': base_lr * 0.05},  # VL-JEPA paper Section 4.6
])
```

**4. Selective Decoding with Agglomerative Clustering (Section 4.5):**

The project implements selective decoding via cosine distance thresholding (`forward_selective()`). The paper uses a more sophisticated approach: **agglomerative clustering with Ward distance** on the embedding stream to partition into N segments of high intra-segment monosemanticity (Section 3.3, 4.5). The clustering approach reduces decoding by **2.85x** while maintaining CIDEr performance. The project's thresholding approach is simpler but functional.

**5. Predictor is 9-11 Llama-3 Layers (Section 3.1):**

The Predictor processes visual tokens + textual query tokens using the last 8 Transformer layers of Llama-3-2-1B, initialized from the pretrained Llama weights. The project uses a 2-layer MLP predictor. For CS2 tick data this is appropriate — the Llama predictor is designed for vision-language fusion, not tabular time-series.

#### Concrete Recommendations

**A. Execute CI-01 first.** Before any VL-JEPA refinements, run JEPA pretraining on the 17.3M available ticks. The paper shows pretraining is not optional (27.3% without → 79.1% with).

**B. Add 0.05x learning rate for concept parameters** when training VL-JEPA (code above).

**C. Monitor embedding diversity during training** — the VICReg diversity loss is already implemented. Track `std_per_dim` in TensorBoard to detect concept collapse early.

---

### 2.2 · Player Rating — PlusMinus and Role-Specific Bayesian Priors

**Source:** `Rating_csgo_players.pdf` (University of New South Wales, 2024)
**Target:** `Programma_CS2_RENAN/backend/coaching/pro_bridge.py`, `backend/processing/baselines/pro_baseline.py` (651 lines)

#### Current State (Verified)

`pro_bridge.py` maps HLTV 2.0 metrics (KPR, DPR, ADR, HS ratio, KAST, KD ratio, impact, rating_2_0) via `PlayerCardAssimilator`. Uses per-round rates directly (P3-02 FIX). `pro_baseline.py` has per-role baselines (AWPer, Entry, Support, IGL, Lurker), per-map baselines (7 competitive maps), and per-side baselines (T/CT).

No PlusMinus metric exists. No hierarchical Bayesian model. (Confirmed absent via grep.)

#### Paper Depth

**PlusMinus Metric (Section II):**

The PlusMinus value of a player is the **average point difference** between their team and the opponent's team over all matches the player participated in. Design matrix `X` has `x_{i,j} = 1` if player `j` played for Team 1 in match `i`, `x_{i,j} = -1` if for Team 2, 0 if not playing. The coefficient vector `beta` captures each player's contribution to team point differences.

This captures **team contribution** independent of individual box score (kills, deaths). A player with high kills who is always alive when their team loses rounds will score negative PlusMinus.

**Key finding:** IGL (in-game leader) impact is **severely underrated by Rating2.0** because IGL contributions manifest in team positioning and coordination, not individual kills. The Bayesian model corrects this.

**Hierarchical Bayesian Model (Section III.B):**

```
y | beta ~ N(X*beta, sigma^2 * I)
beta | eta ~ N(eta * sRating2.0, tau^2 * I)
eta ~ N(0, I)
```

Where `eta` is a hyperparameter vector allowing different adjustment strength per player position/role, and `sRating2.0` is standardized Rating2.0. The Hadamard product `eta * sRating2.0` differentiates the impact of the prior distribution for different players. Fitted via MCMC using **Stan** (probabilistic programming language).

**Minimum match filter:** Players with fewer than **50 matches** excluded to avoid overfitting (Section IV).

**Results (Tables III-IV):** The Bayesian model and elastic logistic regression produce rankings that are highly correlated with true PlusMinus values on test data. The p-values (Table II) confirm strong correlation between predicted and actual PlusMinus.

#### Concrete Recommendations

**A. Add PlusMinus computation to per-match stats:**

```python
# In backend/processing/ or backend/analysis/
def compute_plus_minus(player_name: str, rounds_data: pd.DataFrame) -> float:
    """PlusMinus: team point differential when player was alive."""
    player_rounds = rounds_data[rounds_data['player_name'] == player_name]
    alive_rounds = player_rounds[player_rounds['is_alive']]
    return alive_rounds['team_score_delta'].mean()  # [-1, +1] scale
```

**B. Add role-specific prior adjustments to pro_bridge.py:**

```python
ROLE_PRIOR_ADJUSTMENTS = {
    PlayerRole.ENTRY: 1.2,    # entry fraggers expected to have high individual rating
    PlayerRole.SUPPORT: 0.8,  # supports contribute via PlusMinus, not rating
    PlayerRole.LURKER: 0.95,
    PlayerRole.AWPER: 1.1,
    PlayerRole.IGL: 0.75,     # IGLs most underrated by Rating2.0 (paper finding)
}
```

---

### 2.3 · Win Probability — Elo Features + Recency

**Source:** `Counter_Strike_ML.pdf`
**Target:** `Programma_CS2_RENAN/backend/analysis/win_probability.py` (318 lines)

#### Current State (Verified)

`WinProbabilityNN`: 12 normalized game-state features → 64 → 32 hidden (ReLU + Dropout) → sigmoid. Xavier initialization. Target accuracy 72%+ (Phase 1B Roadmap). Separate training model (`WinProbabilityTrainerNN`, 9 raw features, 32/16 hidden) — **DO NOT cross-load checkpoints**.

#### Paper Depth

The thesis finds Elo rating difference alone achieves **64% accuracy**. Adding economy difference, historical map win rates, and equipment value difference improves to ~66%. Neural networks performed worse (59-61%) — the simple Elo feature is more predictive than complex architectures without it.

**1D Convolution insight (Section 5.2.3):** Using 1D convolutions over the last 5 matches captures recency better than simple aggregation. Recent form (winning or losing streak) is more predictive than long-term average.

#### Concrete Recommendations

**A. Add Elo/FaceIT rating difference as a first-class feature.** The project already has FaceIT integration (`faceit_api.py`, `faceit_integration.py`). Compute team Elo delta and add it to the 12-feature win probability input.

**B. Consider 1D convolution over recent match history** for longitudinal coaching (`longitudinal_engine.py`). This captures form trajectory better than the current EMA smoothing.

---

## TIER 3 — Architectural Improvements (Medium-Term Value)

---

### 3.1 · GOEI State Reduction — Compress the Game Tree

**Source:** `Goal_oriented_state_reduction_of_unknown_game_dynamics.pdf` (ICLR 2026 submission)
**Target:** `Programma_CS2_RENAN/backend/analysis/game_tree.py` (516 lines)

#### Current State (Verified)

`ExpectiminimaxSearch` with full minimax + chance nodes for POMDP solving. `OpponentModel` with economy-based priors, side adjustments, EMA blending. Transposition table (`_TT_MAX_SIZE = 10,000`), node budget (`DEFAULT_NODE_BUDGET = 1,000`). Action space: push, hold, rotate, use_utility.

#### Paper Depth

GOEI achieves near-optimal Nash equilibrium performance using only **452 core states (2.9%)** out of 15,542 possible observations in "Hol's der Geier."

**Critical methodological detail the v1 doc oversimplified:** The number of core states K is **learned via Dirichlet Process clustering**, not set as a hyperparameter. The DP prior (Eq. 8) has:

```
q_{t,o}^S(Theta_{s,o}^S) = DP(Theta_{s,o}^S | a, a_{t,o}^{(i)})
```

Where `a` controls the probability of generating new states. A new state appears with probability `a / (sum a_j + a)`, while existing state `j` appears with probability `a_j / (sum a_j + a)`. This means models with fewer states automatically achieve higher ELBO — the complexity penalty is built into the inference, not hand-tuned.

**Best hyperparameters (Table 1):** `beta = 0.2`, `alpha = 25`. The parameter `beta` sets the Dirichlet prior for transition rules (beta=1 → uniform, beta→0 → sparse one-hot states). The parameter `alpha` controls clustering (larger alpha → more exploration, more states, potentially slower convergence).

**Evaluation metric (Eq. 10):**

```
H(S_t) = -sum_{s_t in S_t} P(s_t) * log P(s_t)
P(s_t) = sum_{o_t in O_t} p(s_t | o_t) * P(o_t)
```

The entropy of the representative state distribution. States with **high entropy** across observations are more "core" — they reduce more irrelevant information. This is different from information gain (which measures how much a feature reduces prediction uncertainty). GOEI measures how much the *state representation* compresses the observation space.

**Information content analysis (Section 4.2, Figure 3):** After state reduction, the information loss (conditional entropy) is low for most features, but **score difference (SD) preserves the most mutual information** across all rounds. This aligns with the project's finding that economy features are highly predictive.

#### Concrete Recommendations

**A. Identify core features via entropy-based selection (not mutual_info_classif):**

The v1 document recommended `sklearn.feature_selection.mutual_info_classif` — this is a simplification. GOEI uses DP clustering to discover that most of the 25 features are redundant for outcome prediction. A pragmatic approximation:

```python
# Rank features by mutual information with round outcome, then use DP-inspired
# automatic cutoff: select features until adding the next one increases effective
# state count by less than 5%
def find_core_features(tick_features, round_outcomes):
    mi = mutual_info_classif(tick_features, round_outcomes)
    sorted_idx = np.argsort(mi)[::-1]
    core = [sorted_idx[0]]
    prev_states = len(np.unique(tick_features[:, core], axis=0))
    for idx in sorted_idx[1:]:
        test_core = core + [idx]
        new_states = len(np.unique(tick_features[:, test_core], axis=0))
        if (new_states - prev_states) / prev_states < 0.05:
            break  # diminishing returns — DP would stop here
        core.append(idx)
        prev_states = new_states
    return core
```

**B. Prune game tree nodes** using core features only in the transposition table hash. States that differ only in non-core features can be merged, dramatically increasing effective search depth.

---

### 3.2 · NAIT Demo Prioritization — Capability-Directed Training

**Source:** `Neuron_Aware_Data_Selection.pdf` (ICLR 2026 submission)
**Target:** `Programma_CS2_RENAN/backend/ingestion/resource_manager.py` (201 lines), Teacher daemon in `core/session_engine.py`

#### Paper Depth — Corrected

The v1 document described NAIT's activation feature extraction incorrectly. The critical details:

**Stage A — Activation DELTAS, not raw activations (Section 3.2):**

```
A(t_k)^{(l)} = [a_j^{(k,l)}]_{j=1}^J       (activation vector at layer l, token t_k)
DELTA_A^{(l)}(t_k) = A^{(l)}(t_k) - A^{(l)}(t_1)  (shift FROM FIRST TOKEN)
v_l = PCA(DELTA_A^{(l)})                     (first principal component per layer)
```

The shift from the first token normalizes out the baseline activation pattern. This is not optional — using raw activations instead of deltas significantly reduces selection quality.

**Per-layer PCA:** A **separate** principal component `v_l` is computed for EACH layer `l`. The capability alignment score sums across all layers: `s_y = sum_{l=1}^L (A^{(l)}(t_k) . v_l)`.

**Key finding (Figure 3):** Data with **logical reasoning and programmatic content** has strong generalizability across tasks — a stable core subset consistently activates fundamental capabilities. Training LLaMA-2-7b on 10% of NAIT-selected data achieves **+3.24% average improvement** over training on 100% of data. For CS2 coaching: demos with explicit decision-making (economy reads, site rotations) are more valuable than aim-heavy demos for training the coaching model.

#### Concrete Recommendations

**A. Score demos by coaching-capability variance** (not raw feature variance):

```python
COACHING_CAPABILITIES = {
    "positioning": [9, 10, 11, 15],      # pos_x, pos_y, pos_z, z_penalty
    "utility": [4, 5, 6],                 # equip_value, is_crouching, is_scoped
    "economy": [4, 24],                   # equip_value, team_economy
    "engagement": [0, 8, 22, 23],         # health, enemies_visible, teammates, enemies
    "decision": [18, 20, 21],             # round_phase, time_in_round, bomb_planted
}

def score_demo_for_capability(demo_features: np.ndarray, capability: str) -> float:
    indices = COACHING_CAPABILITIES[capability]
    return demo_features[:, indices].var(axis=0).mean()
```

**B. Use WeightedRandomSampler** in the Teacher daemon's DataLoader, prioritizing demos that cover the player's weakest coaching capability (identified by `blind_spots.py`).

---

### 3.3 · Approximate Equivariance — Map-Agnostic Coordinates

**Source:** `Approximate_Equivariance.pdf` (ICLR 2026 submission)
**Target:** `Programma_CS2_RENAN/backend/processing/feature_engineering/vectorizer.py` (585 lines)

#### Current State (Verified)

`vectorizer.py` normalizes `pos_x / 4096` and `pos_y / 4096` — raw engine coordinates. These don't respect map symmetry. A model trained only on CT-side Inferno would not generalize to T-side.

#### Paper Depth — Corrected

CS2 maps have **discrete** symmetry groups (e.g., 180-degree rotation on Dust2), not continuous. The paper provides two algorithms:

**Algorithm 1 (finite groups, left side):** For discrete symmetry group G with representations `rho_in`, `rho_out`:

```python
def project_finite(W, group, rho_in, rho_out):
    W_proj = zeros_like(W)
    for g in group:
        W_proj += rho_out[g].conj().T @ W @ rho_in[g]
    return W_proj / len(group)
```

This is O(|G| * n^2) where |G| is the group size. For CS2's discrete symmetries (|G| = 2 for most maps), this is trivially cheap.

**For continuous groups (right side):** Projection via FFT in spectral domain — O(n log n) vs O(n^2). Not needed for CS2.

**Key insight:** The regularizer penalizes non-equivariance across the **full group orbit**, not point-wise. You don't need 1000 rotations of a demo — you penalize the operator's non-equivariance via projection.

#### Concrete Recommendations

**A. Replace raw coordinate normalization with bombsite-relative encoding** — this can be done WITHIN the existing METADATA_DIM=25, by modifying how `pos_x` and `pos_y` are computed in the vectorizer:

```python
def normalize_position_equivariant(pos_x, pos_y, map_id, team_side):
    bombsite_a, bombsite_b = MAP_BOMBSITE_CENTERS[map_id]
    dist_a = sqrt((pos_x - bombsite_a[0])**2 + (pos_y - bombsite_a[1])**2)
    dist_b = sqrt((pos_x - bombsite_b[0])**2 + (pos_y - bombsite_b[1])**2)
    normalized = (dist_a - dist_b) / MAP_DIAGONAL[map_id]
    return normalized if team_side == 'CT' else -normalized
```

This preserves METADATA_DIM=25 (same indices 9-10) but makes the encoding team-side-equivariant.

---

### 3.4 · Robust Feature Estimation — Demo Quality

**Source:** `Robust_Prediction_Powered_inference.pdf` (ICLR 2026 submission)
**Target:** `Programma_CS2_RENAN/ingestion/integrity.py`

#### Paper Depth

**Huber contamination model:** `P_X <- (1-epsilon) * P_X^clean + epsilon * P_X^corruption`. This handles distribution shift (e.g., 64-tick vs 128-tick server demos, network recording artifacts).

**Roica robust mean:** Weight vector `w_hat` found by minimizing covariance `||Sigma_w(theta)||` subject to `w in Delta_{N,epsilon}` where `Delta_{N,epsilon} = {w in R^N : ||w||_1 = 1, 0 <= w_i <= 1/(N(1-epsilon))}`.

**Cross-validation for epsilon (Eq. 8):** `epsilon_hat = argmin_{epsilon in E} sum_k sum_{(X,Y) in D_k} loss^{Roica(epsilon)}(X, Y)`. This automatically finds the optimal contamination level.

**Theoretical guarantee:** O(sqrt(epsilon)) bias rate — 10% corruption → ~0.316x bias.

#### Concrete Recommendations

**A. Add robust feature mean estimation in the vectorizer** for per-demo statistics (not per-tick — the tick data itself is preserved per invariant):

```python
def robust_feature_mean(features: np.ndarray, epsilon: float = 0.05) -> np.ndarray:
    n = len(features)
    max_weight = 1.0 / (n * (1 - epsilon))
    weights = np.ones(n) / n
    for _ in range(10):
        weighted_mean = (weights[:, None] * features).sum(axis=0)
        distances = np.linalg.norm(features - weighted_mean, axis=1)
        weights = np.clip(1.0 / (distances + 1e-8), 0, max_weight)
        weights /= weights.sum()
    return weighted_mean
```

**B. In the Pulse daemon,** when drift is detected, first estimate contamination level `epsilon` via CV. If `epsilon > 0.1` (>10% ticks suspicious), flag the demo as potentially corrupted.

---

## TIER 4 — Infrastructure and Code Assets (Direct Reuse)

---

### 4.1 · CSKnow Dataset — Expand Coach Book

**Source:** `csknow-master/` in utile_cs2
**Available:** 93 CSV files with professional player positioning data (G2 vs ENCE, NIP vs Gambit, Na'vi vs LDLC). `column_names.py` defines engagement/aim features beyond the project's 25-dim vector.

**CSKnow aim features not in the project's 25-dim vector:**
- `ideal_view_angle_x/y` — target angle for perfect aim
- `delta_relative_first_head_view_angle_x/y` — angular error from enemy head center
- `recoil_index` — which shot in the burst (critical for spray patterns)
- `ticks_since_last_fire` — firing cadence
- `attacker_vel_x/y/z` — velocity affecting spray accuracy

**Recommendation:** Extract position patterns from CSKnow CSVs to expand Coach Book from 151 → 500+ entries (addresses CI-04). Create a **separate aim quality sub-vector** (not expanding METADATA_DIM=25) for optional aim analysis.

### 4.2 · demoinfocs-golang — Grenade Trajectories

**Source:** `demoinfocs-golang-master/` in utile_cs2
**Exclusive capabilities:** Grenade projectile trajectory computation (full flight paths), 47 protobuf definitions for CS2 network protocol, live streaming parsing, **1 hour of gameplay per second** throughput with 8 concurrent demos.

**Recommendation:** Optional subprocess bridge for grenade trajectory analysis only. The project's `utility_economy.py` scores utility effectiveness but cannot trace smoke trajectories or flash angles — only throw/landing events from demoparser2.

### 4.3 · V-JEPA Reference Implementation

**Source:** `jepa-main/` in utile_cs2 (Meta AI official V-JEPA code)
**Key parameters to cross-reference during CI-01:** mask ratio 0.9 (90% of patches masked), predictor depth 6 transformer layers, InfoNCE temperature 0.1 (project uses 0.07), EMA momentum 0.996 (project matches).

---

## TIER 5 — Strategic Research Direction

---

### 5.1 · JEPA Gaming Vision (JEPA_gaming.txt)

A strategic vision document arguing that gaming provides the ideal laboratory for JEPA-based world models:
- **Multi-modal learning**: Games provide synchronized visual + audio + interaction streams — the project currently uses only tabular tick data
- **Temporal prediction scaling**: Current JEPA processes short tick sequences; gaming offers potential to predict minutes or hours ahead
- **Transfer learning**: Spatial reasoning from 3D games, resource optimization from strategy games, physics intuition from simulation games

This is a long-term research direction, not an implementation item.

### 5.2 · GOEI for LLM Coaching Context Compression

GOEI's finding that 2.9% of observations are sufficient for near-optimal play suggests the coaching LLM context could be dramatically compressed. Instead of feeding all tick data to the RAG system, identify the ~3% of game states that actually change the tactical situation (bomb plant moments, first pick, economy swing rounds). Use the GOEI entropy metric `H(S_t)` as a **round importance score** — only store/retrieve experiences from high-entropy-change rounds.

### 5.3 · Robust PPI for Semi-Supervised Knowledge Base Expansion

The project currently has 151 Coach Book entries (target: 1,500). Roica's semi-supervised framework could enable automatically expanding the knowledge base: use the 151 labeled entries to train a simple predictor, then apply Roica to robustly impute tactical knowledge for unlabeled demo states. This directly addresses CI-04 without requiring manual authoring.

---

## Summary Table

| Source | Target Module | Impact | Effort | Status in Project |
|--------|--------------|--------|--------|-------------------|
| COPER §3.1–3.3 | `experience_bank.py` | **HIGH** — TrueSkill + CRUD + replay | Medium | Partially implemented (add/retrieve only) |
| LTC+MHN §3.3 (Eq. 4) | `rap_coach/memory.py` | **HIGH** — fixes cold-start bypass | Medium | Binary bypass, deferred to v0.5 |
| MLMove §4–6 | New `movement_quality.py` | **HIGH** — new coaching dimension | Medium | Not implemented |
| CS:GO ML §5.1.4 | `dataset.py`, tests | **HIGH** — correctness fix | Low | Not implemented |
| VL-JEPA §3–4 | `jepa_model.py` | **MEDIUM** — refinements to working code | Low | Code-complete, partially trained |
| Rating paper §III | `pro_bridge.py` | **MEDIUM** — better pro comparison | Low | Individual metrics only |
| CS:GO ML §5–6 | `win_probability.py` | **MEDIUM** — Elo features | Low | 12 features, no Elo |
| GOEI §3 | `game_tree.py` | **MEDIUM** — state compression | High | Full minimax, no reduction |
| NAIT §3.2 | `resource_manager.py` | **MEDIUM** — demo prioritization | Low | Sequential processing |
| Approx. Equivariance §3 | `vectorizer.py` | **MEDIUM** — map generalization | Medium | Raw coordinates |
| Robust PPI §3 | `integrity.py` | **LOW-MEDIUM** — demo QC | Low | SHA256 + format only |
| CSKnow data | Coach Book expansion | **MEDIUM** — 151→500+ entries | Low | Not integrated |
| demoinfocs-golang | `demo_parser.py` | **LOW** — grenade trajectories | High | Not integrated |
| V-JEPA source | `jepa_trainer.py` | **LOW** — reference params | Low | Available for CI-01 |

---

## Priority Queue — Recommended Implementation Order

1. **Execute CI-01: JEPA pretraining to convergence** — data ready (17.3M ticks), trainer ready, partially trained but not converged. A sustained 50-100 epoch run is needed. This unblocks all JEPA-dependent coaching and is the single highest-impact action.

2. **COPER Experience Bank overhaul** — TrueSkill sigma tracking + CRUD semantics + prioritized replay + active prompt editing. Directly improves current coaching quality without requiring more data.

3. **Growing-window validation** — correctness fix for all temporal models. Must be implemented before trusting any model evaluation results.

4. **Movement quality module** — new coaching dimension from MLMove paper. Adds 4 concrete coaching mistake detectors not currently covered.

5. **CSKnow Coach Book expansion** — extract pro positioning patterns from 93 CSV files to expand Coach Book from 151 → 500+ entries (addresses CI-04).

6. **PlusMinus metric + role-specific priors** — improves fairness of coaching for support players and IGLs.

7. **VL-JEPA learning rate multiplier** — small change (0.05x for concept params) that the paper shows prevents concept embedding collapse.

8. **LTC+MHN additive coupling** — when RAP Coach is reactivated (v0.5), replace binary bypass with learnable alpha/delta scalars.

9. **Robust feature estimation** — Roica-style contamination detection in the Digester daemon.

10. **NAIT demo prioritization** — capability-directed training in the Teacher daemon.

11. **GOEI state reduction** — compress game tree search space using entropy-based feature selection.

12. **Equivariant coordinate normalization** — bombsite-relative encoding in vectorizer.py.
