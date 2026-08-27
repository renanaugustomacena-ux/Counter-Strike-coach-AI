# Cluster 08 — `backend/analysis/` (tactical analysis engines)

Files read (all 12): belief_model, win_probability, game_tree, role_classifier,
movement_quality, utility_economy, momentum, deception_index, engagement_range,
blind_spots, entropy_analysis, __init__.

## Engine map

| Engine | What it models | Key mechanism |
|---|---|---|
| `belief_model` | P(death \| information asymmetry) | Bayesian log-odds over HP-bracket priors × threat (visible + decayed inferred enemies) × weapon lethality × armor × exposure; **MC-dropout uncertainty** (mean/std/90% CI); AdaptiveBeliefCalibrator learns priors/lethality/decay-λ from real death events with safety bounds and DB snapshots (CalibrationSnapshot), wired to the Teacher daemon (G-07). R4 HIGH: THREAT_DECAY_LAMBDA must be ClassVar — as a dataclass field the calibrator's update was "a silent no-op for all future BeliefStates". R4 MED in extract: economy tier is NOT health — eco rounds were fabricating hp=30/60 and "P(death\|critical) was silently calibrated to ECO-ROUND death rates"; eco/force rows are now DROPPED, not invented. |
| `win_probability` | Round win prob | 12-feature NN (64/32, sigmoid) + deterministic boundary rules first (0 alive ⇒ 0.0) + heuristic clamps; **PlattScaler** post-hoc calibration (26-WINPROB-03 fixed a negated Hessian that made Newton diverge); **Elo with recency half-life** as a blendable prior (α=0.15). W-02: no checkpoint ⇒ ERROR-level "predictions use random weights" and callers can gate on `_checkpoint_loaded`. Explicit "DORMANT BY DESIGN" comment: Platt/Elo wiring deferred until a trained checkpoint exists — "enabling it before... would be a placebo on random weights" (deliberate dormancy documented in place, not deleted as dead code). Trainer (9-dim) and predictor (12-dim) checkpoints cross-load-guarded (A-12). |
| `game_tree` | Round strategy | Expectiminimax (max/chance alternation) with node budget 1000, transposition table (node_type in the hash — R4: max and chance nodes sharing a slot returned wrong values; depth-direction reuse rule fixed R4 MED), **adaptive OpponentModel** (economy-tier priors, side/advantage/time adjustments, EMA-blended learned per-map profiles ≥10 rounds), leaf evaluation via WinProbabilityPredictor; symmetric push modeling documented as a deliberate simplification corrected at the leaves. Natural-language `suggest_strategy` reports confidence + opponent-model provenance. |
| `role_classifier` | Player roles | Heuristic affinity scores against LEARNED thresholds (Anti-Mock: cold start ⇒ FLEX@0%) + **neural second opinion with consensus rules** (agree ⇒ boost; neural wins only with >0.1 margin; heuristic breaks ties); **F-0030 vocabulary guard**: a stats dict with none of the role-signal keys is REFUSED — normalization used to fabricate "IGL (100%)" from a single feature. Coaching tips retrieved from RAG with static fallback; team classification enforces composition constraints (max 1 AWPer) and `audit_team_balance` emits structural-weakness insights. |
| `movement_quality` | 4 positioning mistakes (MLMove/SIGGRAPH 2024) | high-ground abandonment (combat-justified descents excluded), premature position abandonment (no-new-info test), over-aggressive trading (solo push post-teammate-death), over-passive support (not capitalizing on openings, man-disadvantage excluded); aggregate map-coverage/high-ground/stability metrics. All windows in SECONDS via one `_seconds_to_ticks` conversion point (26-TICK-02: hardcoded 128 "doubled every real-time window on 64-tick demos"). ADDITIVE — does not touch METADATA_DIM. |
| `utility_economy` | Utility efficiency + buy decisions | Per-type effectiveness vs PRO_BASELINES (documented as hand-estimated pending empirical validation P8-06); EconomyOptimizer with MR-format-aware half-round detection — R4 HIGH: half-switch is the second PISTOL round; the old code recommended "an impossible full-buy with 0.95 confidence in every match reaching halftime". |
| `momentum` | Psychological momentum | Streak-based multiplier [0.7, 1.4] with round-type weights (eco upset wins weigh 1.4×; full-buy losses 1.2×), exponential gap decay, tilt detection <0.85, half-switch reset derived from MR format (R4 HIGH: dual 13-and-16 resets wiped mid-half momentum in every MR12 match). |
| `deception_index` | Tactical deception | Composite of flash-bait rate (F-0021: CS2 has no player_blind events — blind signal resolution ladder; **"honestly dark (0.0)" when no signal exists** vs the old degenerate all-bait 1.0), rotation feints (angular reversal >108°, map-extent-normalized displacement), sound deception (crouch-ratio proxy); weights documented as hand-tuned with a validation plan. |
| `engagement_range` | Kill-distance profiles | close/medium/long/extreme distribution vs per-role baselines (F-0022: key normalized to canonical enum "entry" — "entry_fragger" was unreachable); callout-annotated kills; ≥5 kills before observations. |
| `blind_spots` | Recurring strategic errors | Compares player actions vs game-tree optimal per round; clusters mismatches by situation ("1vN clutch", "post-plant advantage"...); priority = frequency × impact; skip-ratio >5% warned ("an empty result indistinguishable from 'no blind spots'"); generates a training plan. |
| `entropy_analysis` | Information value of utility | Shannon entropy of enemy-position grid before/after each throw; effectiveness = delta / per-type theoretical max (hand-estimated, validation plan documented); per-map grid resolutions; lock-protected shared buffer. |

## Invariants observed (doctrine candidates)

- **Probabilistic reasoning over deterministic heuristics** (stated governance) — but deterministic boundary truths (0 alive ⇒ 0.0) are applied BEFORE any model output.
- **Every hand-tuned constant is labeled as such with a validation plan** (P8-0x block comments) — the code distinguishes "empirically calibrated", "hand-tuned pending validation", and "theoretical estimate" explicitly.
- **Calibration is learned, bounded, snapshotted, and atomic**: safety bounds on every learned parameter; snapshots to DB for rollback; atomic global swap for concurrent readers.
- **Metrics go dark rather than degenerate**: no blind signal ⇒ 0.0 with a named reason, never a saturated garbage value; no vocabulary ⇒ refuse to classify; cold start ⇒ FLEX@0%.
- **Dormant-by-design vs dead code is an explicit distinction** — deferred features carry the reason and the activation plan in place.
- Factory functions honestly document instance semantics (singleton vs new-per-call) after R4 caught stateful callers relying on a false singleton claim.

## Risks / open questions carried forward

- WinProbabilityNN has no trained production checkpoint yet (W-02 path) — game_tree leaf evaluations currently ride heuristics + random-weight NN outputs clamped by rules; acceptable but doctrine should note the R9 retrain dependency.
- deception sound_deception is a crouch-ratio proxy only (thin signal); utility_economy PRO_BASELINES and entropy _MAX_DELTA remain hand-estimated.
- game_tree state transitions are coarse (fixed deltas); documented as leaf-corrected.
