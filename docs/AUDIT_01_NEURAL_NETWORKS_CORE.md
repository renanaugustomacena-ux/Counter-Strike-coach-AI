# Audit Report 01 — Neural Networks Core

**Scope:** `backend/nn/` (excl. `rap_coach/`) — 31 files, ~7,420 lines | **Date:** 2026-03-10
**Open findings:** 0 HIGH | 22 MEDIUM | 18 LOW

---

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| NN-M-01 | model.py | Auto-unsqueeze masks batch dimension errors — `_validate_input_dim()` silently reshapes 1D to 3D |
| NN-M-02 | jepa_model.py | 1034 lines — exceeds 500-line guideline by 2x |
| NN-M-03 | jepa_model.py:379 | Mid-file import of `METADATA_DIM` breaks convention |
| NN-M-04 | jepa_model.py | Hardcoded cosine distance threshold 0.3 in `forward_selective()` |
| NN-M-05 | jepa_model.py | `label_tick()` leakage risk — `label_batch()` still calls `label_tick()` as primary path |
| NN-M-06 | train.py vs jepa_train.py | Duplicated negative sampling logic (DRY violation) |
| NN-M-07 | factory.py | RAP output_dim=10 differs from METADATA_DIM=25 |
| NN-M-08 | coach_manager.py | 920 lines — god-class mixing training + presentation |
| NN-M-09 | coach_manager.py | Dual feature lists (TRAINING_FEATURES, MATCH_AGGREGATE_FEATURES) require manual sync |
| NN-M-10 | coach_manager.py | `datetime.now()` without timezone in dataset splitting |
| NN-M-11 | training_orchestrator.py | 890 lines — RAP batch prep has nested loops hard to unit test |
| NN-M-12 | training_orchestrator.py | Continuous [0,1] advantage — 0.5 boundary undocumented |
| NN-M-13 | training_controller.py | `MAX_DEMOS_PER_MONTH = 10` not configurable |
| NN-M-14 | train_pipeline.py | Deprecated pipeline still importable without module-level warning |
| NN-M-15 | jepa_train.py | 9 of 25 features always zero-padded — 36% input wasted in pretraining |
| NN-M-16 | embedding_projector.py | UMAP failure silent — effectively disables visualization |
| NN-M-17 | maturity_observatory.py | Uncalibrated maturity thresholds and EMA alpha |
| NN-M-18 | win_probability_trainer.py | WIN_PROB_FEATURES maintained separately from schema |
| NN-M-19 | ghost_engine.py | `predict_tick()` returns (0.0, 0.0) for all failure modes — indistinguishable |
| NN-M-20 | ghost_engine.py | No runtime validation that loaded model matches POV/legacy tensor mode |
| NN-M-21 | evaluate.py | SHAP KernelExplainer recreated per call |
| NN-M-22 | superposition.py | `_forward_count += 1` non-atomic increment |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| NN-L-01 | model.py | `TeacherRefinementNN = AdvancedCoachNN` alias may confuse maintainers |
| NN-L-02 | config.py | ML_INTENSITY string comparison without validation |
| NN-L-03 | jepa_model.py | COACHING_CONCEPTS as list — could be Enum |
| NN-L-04 | jepa_trainer.py | Hardcoded drift threshold 0.01 |
| NN-L-05 | train.py | `MIN_TRAINING_SAMPLES = 20` should be in training_config.py |
| NN-L-06 | factory.py | Lazy imports add first-call latency |
| NN-L-07 | role_head.py | ROLE_OUTPUT_ORDER defined in multiple places |
| NN-L-08 | role_head.py | FLEX_CONFIDENCE_THRESHOLD and LABEL_SMOOTHING_EPS undocumented |
| NN-L-09 | coach_manager.py | Maturity tier thresholds (0/50/200) are magic numbers |
| NN-L-10 | training_orchestrator.py | Tactical role thresholds hardcoded inline |
| NN-L-11 | training_controller.py | MIN_DIVERSITY_SCORE = 0.3 undocumented |
| NN-L-12 | training_monitor.py | JSON metrics file write not atomic |
| NN-L-13 | training_callbacks.py | Callback registry has no deduplication |
| NN-L-14 | train_pipeline.py | Legacy 12-feature extraction incompatible with current 25-dim |
| NN-L-15 | jepa_train.py | No LR scheduler in standalone pretrain |
| NN-L-16 | embedding_projector.py | TensorBoard metadata format hardcoded |
| NN-L-17 | tensorboard_callback.py | SummaryWriter resource leak (no close/del) |
| NN-L-18 | ghost_engine.py | Three separate `isinstance(tick_data, dict)` branches |

## Cross-Cutting

1. **Feature Dimension Fragmentation** — evaluate.py uses 4/25, jepa_train uses 16/25, RAP output=10, win_prob uses 9. No model uses full 25-dim at both input and output.
2. **Magic Number Proliferation** — 15+ hardcoded thresholds scattered across files.
3. **Code Size Violations** — jepa_model.py (1034), coach_manager.py (920), training_orchestrator.py (890) all exceed 500-line guideline.
