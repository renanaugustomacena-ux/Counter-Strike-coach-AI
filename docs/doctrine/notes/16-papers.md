# Phase 2 — Research papers mapped onto the codebase

All 7 papers in `docs/research/` read in full (X-Ego via its LaTeX source; the rest via
extracted PDF text). Every mapping below terminates in code personally read during Phase 1
(cluster notes 01–15), never in repo prose. Buckets per paper: **(a) already implemented**,
**(b) deliberate divergence**, **(c) roadmap candidates**.

## 1. X-Ego / CECL (2510.19150) — Cross-Egocentric Contrastive Learning, AAMAS'26 sub

124 h of pro CS2 (45 FACEIT matches, all de_mirage, 64 t/s), synchronized all-player POV video +
trajectories. CECL: sigmoid contrastive loss (SigLIP-style) aligning TEAMMATES' egocentric
embeddings at the same time segment; learnable temperature t=log 10 and bias b=−3 initialized to
the prior log-odds of the positive ratio (imbalance-aware); 3-level negative hierarchy. Probes:
Teammate/Enemy Location Nowcast — 23-callout multi-label occupancy from one POV. Mini-map masked
to prevent location leakage. CECL helps most at 1–2 POVs; V-JEPA2 0.3B saw no gain.

- (a) **Implemented**: learnable-temperature contrastive objective (jepa_model InfoNCE + learnable
  temperature, F-0023 concept temperature with PRE-6 saturation alarms — note 07a); their mini-map
  masking is a poorer cousin of the NO-WALLHACK sensorial contract (TensorFactory FOV gating,
  memory decay, POV-only 25-dim contract — notes 06/07a); their 23-callout vocabulary ≈ the
  map_callouts SSOT (WR-77); their 70:15:15 round-based split ≈ the chronological match-level
  split doctrine (P4-A/eligibility gates, note 07b — ours is stricter: whole-match, never-straddle).
- (b) **Divergence**: they train on recorded video; the codebase renders state-derived POV tensors
  (view/map/motion) from demo truth — cheaper, resolution-controlled (F-0026 parity), and leak-proof
  by construction. They hardcode 64 t/s; our 26-NORM-01 forbids that (their choice would break on
  128-tick demos).
- (c) **Roadmap**: (1) a CECL-style auxiliary objective — align the 5 teammates' POV-tensor
  embeddings at the same tick (multi-positive, imbalance-aware bias init) to give a single-POV
  embedding team-level situational awareness; directly serves the belief/blind-spot engines.
  (2) TLN/ELN-style callout-occupancy probes as EVAL tasks for JEPA embeddings (linear probe
  over map_callouts occupancy) — an objective measure of "does the latent know where people are",
  strictly NO-WALLHACK-compatible since labels come from the demo, inputs from one POV.

## 2. JEPA generalization theory (2606.27014) — PKU

JEPA pretraining ≡ low-rank factorization of an action-conditioned co-occurrence matrix; planning
regret ≤ 2c·√(pretraining risk), T-step regret scales ×T; approximation-vs-sample-error trade-off
in latent dim k (optimal spectrum tail Σ_{i>k}σ²); latent prediction provably beats input-level
reconstruction under observation noise and long horizons.

- (a) **Implemented**: the codebase's core bet — predict in latent space, decode selectively
  (jepa_model selective decoding, note 07a) — is exactly the regime the theory favors: CS2 tick
  streams are noisy (aim jitter, unpredictable micro-motion) and coaching judgments are
  long-horizon. RankMe/collapse_metrics telemetry (notes 07a/07b) is the empirical dual of
  Theorem 4.3: effective rank measures how many singular components of the co-occurrence structure
  the latent retains.
- (b) **Divergence**: none — the theory validates the architecture choice.
- (c) **Roadmap**: (1) T-step error accumulation (Thm 4.2) argues for keeping ghost_engine and
  game-tree rollouts SHORT and leaf-corrected (which game_tree already does, note 08) — doctrine
  should state the principle: never trust long latent rollouts more than linearly-degraded.
  (2) The predictor g(z,a) is ACTION-conditioned in the theory; our JEPA predictor is
  state-only. An action/intent-conditioned predictor would unlock counterfactual coaching
  ("what if you had rotated?") with a provable regret link to pretraining loss.
  (3) The latent-dim trade-off gives a principled frame for HIDDEN_DIM=128 tuning: watch RankMe
  vs val-loss jointly (approximation ↓ vs sample error ↑), not val-loss alone.

## 3. Zero-label surprise via JEPA (2606.28383) — nuPlan

Minimal JEPA on structured agent states; latent prediction error at inference = zero-label
"surprise"/complexity score. Ablations: EMA α=0.996 is THE load-bearing mechanism (no-EMA
collapse: score spread ÷44); random encoder ρ≈0; constant-velocity baselines actively misrank
(low kinematic error during pre-event approach). Collapse detected as latent variance <0.002 +
cosine sim >0.998. Auxiliary position-decoder head λ=0.1.

- (a) **Implemented**: EMA target encoder at 0.996 (J-6 cosine 0.996→1.0, note 07a — ours adds a
  schedule); their collapse thresholds are near-twins of EmbeddingCollapseDetector (variance <0.01
  for 2 epochs ⇒ hard abort, P9-02) — independent validation that the codebase watches exactly the
  right signals; auxiliary position head ≈ RAP position head / RAP-AUDIT-02 next-position deltas
  (note 07c).
- (b) **Divergence**: none material.
- (c) **Roadmap (high value)**: the codebase computes JEPA prediction error in training but never
  serves it. A **surprise channel** at inference would give: (1) a second, label-free signal for
  ChronovisorScanner (which today scans RAP value estimates only — note 07c) to find critical
  moments; (2) data curation — rank rounds/demos by surprise to prioritize coaching attention and
  training sampling (their AP 0.512 vs 0.436 chance is modest but real, and our structured-state
  setting matches theirs exactly); (3) a "this round was unusual" coach observation that is honest
  by construction (model's own uncertainty, no fabricated labels). Gate it exactly like F-0029:
  only from a checkpoint with trained weights.

## 4. ScaleAware-JEPA (2606.29723) — multiscale physical fields

Principle: **the representation and the predictive task must be organized by the same scale
hierarchy**. CDD decomposes the field into pixel-registered scale components; masks are sized by
each component's physical scale. Diagnostics — target effective rank + spread-hinge ratio — are
used ACTIVELY to select masking strategy (avoid context starvation and hinge saturation). VICReg-
style std-hinge spread regularizer. Inference produces a dense back-mappable latent atlas
(UMAP/PCA neighborhoods traced back to field locations) for label-free structure discovery.

- (a) **Implemented**: the spread hinge ≈ the VICReg variance term in the JEPA trainer (note 07a);
  UMAP atlases ≈ EmbeddingProjector Layer 4 ("clusters forming = conviction", note 07b).
- (b) **Divergence**: theirs is a masking JEPA over space; ours is a temporal-prediction JEPA over
  ticks. Both are legitimate JEPA instantiations; no conflict.
- (c) **Roadmap**: (1) CS2 tactics are hierarchical in TIME (tick → engagement → phase → round →
  half → match); the current JEPA predicts one fixed horizon (context 10 → next tick). Multi-
  horizon/multi-scale prediction targets (next tick, next engagement, next phase) would apply their
  principle to our axis. (2) Promote RankMe from passive telemetry to an ACTIVE design input when
  tuning window sizes/masking (their Fig. 2 workflow). (3) Extend EmbeddingProjector from
  diagnostic to coaching instrument: back-map latent neighborhoods to game situations ("this
  cluster = broken retakes") — a label-free tactical atlas for the knowledge pipeline.

## 5. EgoCS-400K (2606.18180) — CS replay-grounded dataset for world models

400K+ POV videos / 10K+ h from >1,000 pro CS/CS2 matches, 13 maps. Design principle stated
verbatim: **"the demo file is the source of truth"** — every annotation audits back to the replay
timeline. Multi-grained hierarchy: per-tick traces → rule-based atomic action spans (with
confidence, end-reason, source signal) → cut-protected action chains → DP-planned segments
(min 2 s/target 4 s/max 6.5 s, 0.5 s pre-context) → prior-constrained VLM captions (priors are
CONSTRAINTS; noEffect actions filtered; strict JSON with confidence + flags).

- (a) **Implemented**: replay-as-truth = the codebase's entire provenance doctrine (three-tier
  storage, honest NULLs, DL-1 lineage, anti-fabrication — notes 04/05/06); their prior-constrained
  captioning with anti-hallucination filtering is WR-78's data-honesty prompt rules + the
  round_reconstructor's grounded `format_for_llm` timelines (notes 06/10), independently arrived
  at; their strict-JSON-with-flags ≈ RFC-8259-honest JSON (note 07b).
- (b) **Divergence**: they render video for generative world models; we stay in structured state.
  They assume 64 t/s CS2; we resolve per demo (26-NORM-01).
- (c) **Roadmap**: (1) **atomic action spans** — rule-based detectors turning tick signals into
  temporally bounded actions (weapon switch, reload, grenade prepare/flight/effect as linked
  sub-events, each with confidence + source) would enrich round_reconstructor timelines and give
  RAP/JEPA an action vocabulary the 25-dim contract lacks; the codebase already synthesizes CS2
  blind events from joint evidence (note 06) — same technique, generalized. (2) **Cut-protected
  windowing**: JEPA windows currently cut at arbitrary ticks; never splitting a mid-action chain
  (their DP segmentation with pre-context) is a data-quality refinement for both JEPA and RAP
  batches.

## 6. HEE (2607.00816) — hierarchical entity exploration for HR perception

Training-free tree search for high-res VQA: entity-driven decomposition (frozen detector +
K-means over semantic embeddings) instead of geometric grids; dual scoring (semantic similarity +
model confidence, λ=0.5, τ=0.5); expand only the best node; confidence-guided backtracking over
the stored ranking. Key finding: cropping's gain comes from BACKGROUND REMOVAL, not resolution.

- (a) **Implemented (analog)**: search-with-budget-and-memory ≈ game_tree's expectiminimax with
  node budget + transposition table (note 08); entity-first spatial vocabulary ≈ the callout SSOT
  used by engagement_range/movement_quality coaching (notes 08/10).
- (b) **Divergence**: HEE is an MLLM-inference technique; the coach's perception is state-based.
- (c) **Roadmap**: (1) prefer ENTITY (callout) representations over coordinate grids wherever
  spatial reasoning surfaces — the entropy analyzer's grids are fine for information math, but
  experience_bank's `_infer_position_area` thirds-grid (flagged note 09) should move to the
  map_callouts SSOT: "entity-centric beats geometric" is now paper-backed. (2) If a VLM ever
  watches renders/heatmaps (the mission's "watching like a real coach"), HEE's recipe —
  entity decomposition, dual scoring, backtracking, τ-gated stopping — is the template; note the
  dialogue engine's tool phase (DP-03, note 10) already has the bones (bounded rounds, whitelists)
  but no scoring/backtracking.

## 7. ER-JEPA / H-JEPA (2607.01145) — hierarchical JEPA for multivariate time series (ECG)

Two chained JEPAs mirroring the expert's diagnostic workflow: a CHANNEL JEPA attends over
concurrent per-channel patches of one interval (sequence length N_ch, not N_ch×N_t), an
aggregation layer summarizes each interval, then a TEMPORAL JEPA treats interval summaries as a
univariate sequence. EMA momentum 0.996→1 linear. Stacked JEPAs AMPLIFY collapse risk (early
loss-drop-and-recover; ~1% anomalous runs detectable from epoch-2 loss stats; dropout materially
helps). Domain-guided masking (weighted channel sampling; block-vs-random context). SOTA on
ST-MEM benchmark at 3–6 GB VRAM.

- (a) **Implemented**: EMA 0.996→1.0 is exactly J-6 (note 07a); their early-anomaly detection from
  loss statistics is the same philosophy as the MaturityObservatory/PRE-6/P9-02 stack — watch the
  training dynamics, abort/flag early (note 07b).
- (b) **Divergence**: the codebase's 25-dim vector is one fused channel; no per-channel attention.
  That is a deliberate simplicity choice at 25 dims — H-JEPA's efficiency argument targets larger
  channel counts.
- (c) **Roadmap (architectural)**: the natural CS2 instantiation of H-JEPA is **players-as-
  channels**: a team-level JEPA attending over the 5 teammates' concurrent per-tick embeddings
  (this is where X-Ego's CECL and H-JEPA meet — contrastive alignment or channel-JEPA prediction
  over teammate embeddings), aggregated per tick, chained into the existing temporal JEPA. Serves
  the mission's team-tactical awareness directly. Doctrine caveat FROM THE PAPER: stacked JEPAs
  multiply collapse risk — any hierarchy must carry a per-level P9-02 detector and an epoch-2
  loss-statistics gate; their dropout finding transfers.

## Cross-paper synthesis (feeds DOCTRINE.md)

1. **The codebase's guards are independently validated**: EMA 0.996 (papers 3, 7 = J-6), variance
   collapse thresholds (paper 3 ≈ P9-02), effective-rank telemetry (papers 2, 4 ≈ RankMe),
   replay-as-truth + constrained-LLM honesty (paper 5 ≈ anti-fabrication + WR-78), chronological
   splits (paper 1). Nothing in the papers contradicts a single standing invariant.
2. **Latent-space prediction is the right bet** (paper 2's theory; paper 3's CV-baseline failure)
   — and its failure mode (long-rollout error accumulation) is already handled by leaf correction.
3. **Highest-leverage additions, in order**: surprise channel at inference (3); teammate-alignment
   /H-JEPA team level (1+7); action-conditioned predictor (2); callout-occupancy eval probes (1);
   atomic action spans + cut-protected windows (5); multi-horizon targets + latent atlas (4);
   entity-over-grid spatial vocabulary (6).
4. **New risks the papers name for our roadmap**: stacked-JEPA collapse amplification (7);
   contrastive compression hurting full-information settings (1's full-POV regression — keep CECL
   auxiliary, not primary); hardcoded tick rates in EVERY external CS dataset (1, 5) — our
   26-NORM-01 stance is stricter than the field's.
