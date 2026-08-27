# Cluster 07c — RAP Coach, superposition, ghost engine, chronovisor

Files read: experimental/rap_coach/{model, perception, memory, strategy, pedagogy,
communication, trainer, chronovisor_scanner, test_arch, conftest, __init__},
layers/superposition, inference/ghost_engine, rap_coach/* shims, experimental/__init__,
advanced/__init__.

## RAPCoachModel — the "grand vision" architecture (experimental, USE_RAP_MODEL gate)

Six layers, biologically framed:

1. **Perception** (`perception.py`): dual-stream CNN — ventral (view, ResNet stack [1,2,2,1] calibrated for 64×64 training inputs, F3-29) + dorsal (map, [2,2]) + motion conv → concat 64+32+32 = 128-dim. AdaptiveAvgPool makes it resolution-agnostic (but grid-unit statistics still demand training-resolution parity — F-0026).
2. **Memory** (`memory.py`): **LTC (Liquid Time-Constant, ncps AutoNCP wiring 512 units, 0.3 output ratio per Lechner et al.) + HopfieldLayer (32 learnable prototype rounds, Ramsauer et al.)** → belief head (64-dim belief vector). Continuous-time: real inter-tick `timespans` drive the ODE solver (without them "the LTC treats every tick as 1.0s and loses its continuous-time advantage"). RAP-LTC-FIX: a documented monkey-patch fixes an upstream ncps broadcast bug (elapsed_time (B,) vs cm (512,)), with trace in docs/rap_training_known_issue. **NN-MEM-01 invariant: Hopfield recall is BYPASSED (zeros) until real optimizer steps have shaped the prototypes** — activation is step-driven via `notify_optimizer_step()` (forward-count gating fired before any weight update under grad accumulation, R4); checkpoint load asserts trained ONLY when Hopfield weights actually loaded ("a partial load must NOT bless random prototypes"). Phase 5B K-means prototype init exists (fixed to target hflayers' (1, K, D) shape). RAPMemoryLite: LSTM drop-in with identical contract for dependency-free installs.
3. **Strategy** (`strategy.py`): top-2 sparse MoE (4 experts), each expert = **SuperpositionLayer (FiLM: γ(context)·(Wx+b)+β(context)**, RAP-AUDIT-06: multiplicative-only gating "could only suppress features, never inject"; β zero-init preserves prior behavior) with context = metadata 25 + belief 64 = 89 (RAP-AUDIT-09: belief head was computed but never consumed). Full gate softmax returned for **entropy sparsity loss** (RAP-AUDIT-04: L1 on softmax outputs was "mathematically constant... zero useful gradient").
4. **Pedagogy** (`pedagogy.py`): critic value head V(s) + skill-conditioned bias (10 skill buckets shift the hidden state) — advantage gap = actual − estimated = "the coaching gap".
5. **Position head**: optimal-shadow deltas [dx,dy,dz]; trainer applies **2× Z-axis penalty** ("wrong floor = instant death").
6. **CausalAttributor + RAPCommunication**: relevance head over 5 human concepts (Positioning/Crosshair/Aggression/Utility/Rotation) fused with mechanical deltas → attribution scores; communication renders **skill-tiered templates** (low=direct/concrete, mid=pattern, high=strategic/abstract) with real spatial angle resolution (threat direction relative to view), **advice suppressed below 0.7 confidence** ("Silence is a Valid Action" again).

`RAPTrainer`: weighted multi-task loss (strategy MSE 1.0 + value 0.5 masked by val_mask + entropy sparsity 1.0 + position 1.0), AMP + accumulation, notifies memory on real steps.

## GhostEngine (inference/ghost_engine.py)

- Loads RAP checkpoint via factory/persistence ladder; **no checkpoint ⇒ "Lobotomy" — predictions disabled, never random weights**. USE_RAP_MODEL off ⇒ inert.
- Serve-time parity: TrainingTensorConfig (64×64) factory (F-0026 — the default 128/224 "silently skews grid-unit statistics"); unified FeatureExtractor + validate_feature_parity(label="inference"); context features from live game state.
- **POV-mode channel-semantics guard** (R4-04-01): POV tensors have different channel meanings than legacy training tensors — POV inference only via explicit USE_POV_TENSORS, "only valid if model was trained with POV tensors".
- Failure returns None, not (0,0) — "a VALID world coordinate near map center; callers could not tell ghost-at-origin from inference-failed".

## ChronovisorScanner

- Match timeline → per-window value estimates → **multi-scale gradient detection** (micro 64t / standard 192t / macro 640t with per-scale thresholds 0.10/0.15/0.20) → CriticalMoments ("mistake"=advantage loss, "play"=gain) with cross-scale dedup (finer scale wins). Entry stride computed from actual window spacing (lag in ticks ÷ real stride — pre-R4 the timeline silently collapsed one entry per window keyed to the wrong tick).
- Returns a structured ScanResult that distinguishes empty-success from failure ("never silently empty"); truncation at 50K ticks warned; maturity gate advisory-but-loud for backend callers.

## Hygiene

- P9-01 consolidation: rap_coach/* are deprecated one-line re-export shims (replace-not-delete); advanced/ tombstone names the deleted dead modules (G-06); test_arch.py is a standalone architecture check that actively refuses pytest collection.

## Doctrine candidates

- The RAP layer stack mirrors a coach's cognition: perceive (dual-stream vision) → remember (continuous-time belief + associative round prototypes) → decide (context-modulated experts) → evaluate (value/advantage) → explain (causal attribution) → communicate (skill-tiered language, confidence-gated silence).
- Untrained components must be inert, not noisy: Hopfield bypass, ghost lobotomy, advice suppression — the system prefers "no output" to fabricated output at every level.
- Upstream library bugs are patched locally with full written justification and a docs trace, not forked or ignored.
- Train/serve parity is enforced at tensor resolution, feature schema, channel semantics, and scale factor — four separate guards.
