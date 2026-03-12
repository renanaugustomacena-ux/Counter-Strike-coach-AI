# Audit Report 04 — Analysis & Game Theory

**Scope:** `backend/analysis/` — 11 files, ~3,672 lines | **Date:** 2026-03-10
**Open findings:** 0 HIGH | 11 MEDIUM | 9 LOW

---

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| A-02 | belief_model.py | Hand-tuned log-odds weights [2.0, 1.5, -1.0, 1.0] — no empirical validation |
| A-06 | game_tree.py | `_state_hash` uses randomized Python `hash()` — not safe for cross-process use |
| A-07 | game_tree.py | Transposition table uses FIFO eviction, not LRU |
| A-13 | win_probability.py | Without trained checkpoint, predictor is purely heuristic — undocumented |
| A-15 | role_classifier.py | AWPer dedup assigns FLEX without considering second-best role |
| A-16 | role_classifier.py | Neural FLEX can override heuristic non-FLEX via consensus mechanism |
| A-18 | entropy_analysis.py | `_MAX_DELTA` values hand-estimated, not empirically validated |
| A-20 | utility_economy.py | Flash cost hardcoded $200 — may be $250 in current CS2 |
| A-21 | utility_economy.py | PRO_BASELINES hand-estimated from VOD, not parsed demo data |
| A-23 | deception_index.py | Sound deception uses crouch ratio as sole proxy — conflates lack of stealth with active deception |
| A-24 | deception_index.py | Composite deception weights hand-tuned, unvalidated |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| A-01 | __init__.py | Eager imports trigger full module loading including PyTorch |
| A-03 | belief_model.py | HP range assertion missing in `estimate()` |
| A-04 | belief_model.py | Mid-file `import threading` |
| A-05 | belief_model.py | Per-bracket calibration minimum (10) vs global (30) |
| A-08 | game_tree.py | Chance node value temporarily holds probability |
| A-10 | momentum.py | Momentum multipliers hand-tuned, validation deferred |
| A-11 | momentum.py | `is_hot` threshold 1.2 not a named constant |
| A-14 | win_probability.py | Self-test block not reachable via test framework |
| A-17 | role_classifier.py | `KnowledgeRetriever()` re-instantiated per call |
| A-22 | utility_economy.py | `np.mean` on 4-element dict.values() — unnecessary numpy overhead |
| A-26 | engagement_range.py | Role range baselines hand-estimated |
| A-25 | engagement_range.py | 50+ named positions hardcoded as Python literals |

## Cross-Cutting

1. **Pervasive Hand-Tuned Parameters** — 8 of 11 files contain unvalidated constants. A single calibration pass using parsed pro demos would improve coaching accuracy.
2. **WinProbabilityPredictor as Shared Dependency** — Game tree, blind spot, and coaching all depend on it. Training the model cascades improvements through the entire stack.
