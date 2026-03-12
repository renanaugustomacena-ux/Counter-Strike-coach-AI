# Audit Report 02 — RAP Coach & Training

**Scope:** `backend/nn/rap_coach/`, `experimental/rap_coach/`, RAP processing — 25 files, ~3,024 lines | **Date:** 2026-03-10
**Open findings:** 0 HIGH | 12 MEDIUM | 11 LOW

---

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| RAP-M-01 | model.py / ghost_engine.py | Position head outputs 3D but inference only uses 2D — Z-axis trained but discarded |
| RAP-M-02 | communication.py | Feedback templates use fabricated values from confidence scalar, not real game metrics |
| RAP-M-03 | pedagogy.py | `_detect_utility_need()` uses `sigmoid(hidden.mean())` — proxy may not correlate with utility need |
| RAP-M-04 | memory.py | Hopfield activated on first forward pass before any gradient update |
| RAP-M-05 | trainer.py | No gradient clipping in RAPTrainer (unlike train.py which uses `clip_grad_norm_`) |
| RAP-M-06 | trainer.py | Silent position training skip when `target_pos` absent — no logging |
| RAP-M-07 | test_arch.py | Uses assert instead of test framework — stripped with `-O` flag |
| RAP-M-08 | tensor_factory.py | Channel semantics (legacy vs POV) not tracked on generated tensors |
| RAP-M-09 | tensor_factory.py | `int()` truncation vs `math.floor()` in world-to-grid conversion |
| RAP-M-10 | player_knowledge.py | `_build_enemy_memory()` O(N*E) with no hard cap on history size |
| RAP-M-11 | player_knowledge.py | Flash radius uses SMOKE_RADIUS (200) instead of actual ~400 units |
| RAP-M-12 | skill_assessment.py | Skill vector attribute access without getattr guards |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| RAP-L-01 | rap_coach/ | 11 deprecated shims not cleaned up |
| RAP-L-02 | perception.py | No output dimension assertion on forward() |
| RAP-L-03 | strategy.py | Forward returns bare tuple instead of NamedTuple |
| RAP-L-04 | communication.py | Confidence threshold 0.7 hardcoded |
| RAP-L-05 | pedagogy.py | Coaching concepts hardcoded as list |
| RAP-L-06 | chronovisor_scanner.py | Maturity gate not enforced in backend |
| RAP-L-07 | chronovisor_scanner.py | `if model:` after `RAPCoachModel()` — always truthy |
| RAP-L-08 | test_arch.py | Only tests shapes, not gradient flow or NaN propagation |
| RAP-L-09 | skill_assessment.py | Fallback 0.5 undocumented |
| RAP-L-10 | player_knowledge.py | Unused constant `HEARING_RANGE_FOOTSTEP` |
| RAP-L-11 | perception.py | `num_blocks=[1,2,2,1]` group structure misleading |

## Cross-Cutting

1. **Training/Inference Skew** — Position dims (3D vs 2D), channel order (legacy vs POV), tensor resolution (64 vs 128/224).
2. **Heuristic Attribution Quality** — 2 of 5 concepts (Aggression, Rotation) are derived from same signal with different scaling.
3. **Fabricated Feedback Values** — Player-facing advice uses confidence-derived fake measurements.
