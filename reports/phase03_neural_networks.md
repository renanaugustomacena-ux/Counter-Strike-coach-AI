# Deep Audit Report — Phase 3: Neural Network Architecture

**Total Files Audited: 41 / 41**
**Issues Found: 38**
**CRITICAL: 4 | HIGH: 6 | MEDIUM: 19 | LOW: 9**
**Author: Renan Augusto Macena**
**Date: 2026-02-27**
**Skills Applied: deep-audit, ml-check, jepa-audit, correctness-check, state-audit, observability-audit**

---

## Scope

This phase covers the entire `backend/nn/` directory: model definitions, training loops, inference engine, observatory framework, and supporting layers.

### Files Audited

| # | File | LOC | Status |
|---|---|---:|---|
| 1 | `backend/nn/training_orchestrator.py` | 733 | **MODIFIED (+432)** |
| 2 | `backend/nn/jepa_model.py` | 849 | HIGH |
| 3 | `backend/nn/coach_manager.py` | 878 | HIGH |
| 4 | `backend/nn/rap_coach/chronovisor_scanner.py` | 378 | HIGH |
| 5 | `backend/nn/maturity_observatory.py` | 329 | NORMAL |
| 6 | `backend/nn/role_head.py` | 322 | NORMAL |
| 7 | `backend/nn/jepa_train.py` | 311 | NORMAL |
| 8 | `backend/nn/jepa_trainer.py` | 265 | NORMAL |
| 9 | `backend/nn/train.py` | 232 | NORMAL |
| 10 | `backend/nn/embedding_projector.py` | 230 | NORMAL |
| 11 | `backend/nn/tensorboard_callback.py` | 226 | NORMAL |
| 12 | `backend/nn/inference/ghost_engine.py` | 205 | **MODIFIED** |
| 13 | `backend/nn/model.py` | 169 | NORMAL |
| 14 | `backend/nn/training_controller.py` | 160 | NORMAL |
| 15 | `backend/nn/config.py` | 130 | NORMAL |
| 16 | `backend/nn/rap_coach/skill_model.py` | 132 | NORMAL |
| 17 | `backend/nn/ema.py` | 119 | NORMAL |
| 18 | `backend/nn/training_monitor.py` | 122 | NORMAL |
| 19 | `backend/nn/training_callbacks.py` | 104 | NORMAL |
| 20 | `backend/nn/train_pipeline.py` | 104 | NORMAL |
| 21 | `backend/nn/rap_coach/model.py` | 103 | HIGH |
| 22 | `backend/nn/factory.py` | 98 | HIGH |
| 23 | `backend/nn/rap_coach/trainer.py` | 97 | NORMAL |
| 24 | `backend/nn/rap_coach/pedagogy.py` | 95 | NORMAL |
| 25 | `backend/nn/rap_coach/perception.py` | 88 | NORMAL |
| 26 | `backend/nn/win_probability.py` | 86 | NORMAL |
| 27 | `backend/nn/early_stopping.py` | 84 | LOW |
| 28 | `backend/nn/rap_coach/strategy.py` | 78 | NORMAL |
| 29 | `backend/nn/persistence.py` | 75 | NORMAL |
| 30 | `backend/nn/rap_coach/memory.py` | 72 | HIGH |
| 31 | `backend/nn/advanced/brain_bridge.py` | 71 | LOW |
| 32 | `backend/nn/training_config.py` | 70 | LOW |
| 33 | `backend/nn/rap_coach/communication.py` | 70 | LOW |
| 34 | `backend/nn/dataset.py` | 61 | LOW |
| 35 | `backend/nn/rap_coach/test_arch.py` | 48 | LOW |
| 36 | `backend/nn/evaluate.py` | 46 | NORMAL |
| 37 | `backend/nn/advanced/superposition_net.py` | 39 | LOW |
| 38 | `backend/nn/advanced/feature_engineering.py` | 32 | LOW |
| 39 | `backend/nn/layers/superposition.py` | 102 | NORMAL |
| 40 | `backend/nn/advanced/__init__.py` | ~5 | RAPID |
| 41 | `backend/nn/rap_coach/__init__.py` | ~5 | RAPID |

**Total LOC audited: ~7,380**

---

## AIstate.md Cross-Reference

| AIstate ID | Finding | Phase 3 Status |
|---|---|---|
| G-01 | JEPA ConceptLabeler label leakage | **Confirmed + extended**: F3-01 (19-dim stale comment), label leakage documented in jepa_trainer.py L225-228 |
| G-02 | Hopfield uniform attention | **Confirmed**: memory.py L33-37 documented — needs training data |
| G-03 | TensorFactory danger channel | Phase 2 finding (F2-07) |
| G-05 | Game theory / belief model | Phase 4 scope |
| G-06 | METADATA_DIM mismatch | **Confirmed**: F3-01, F3-09, F3-10 — three separate stale "19-dim" references |
| G-07 | Teacher daemon belief calibration | **Extended**: belief_calibrator.py does NOT exist at expected path |

---

## CRITICAL Findings

### F3-01: ConceptLabeler Feature Index Mismatch (CRITICAL)
**File:** `backend/nn/jepa_model.py:465-477`
**Skill:** jepa-audit, ml-check
**AIstate:** G-06

The `ConceptLabeler` class docstring says "19-dim feature vector" and uses hardcoded feature indices that map to the original 19-dim layout. However, `METADATA_DIM` was upgraded from 19 to 25 in a prior session. Features at indices 19-24 (`weapon_class`, `fov_coverage`, `has_armor`, `time_in_round_norm`, `team_economy_norm`) are **never consumed** by the labeler.

**Impact:** VL-JEPA concept alignment training ignores 6 input features (24% of the vector). Concept labels are computed from only 19/25 features, creating a systematic blind spot for weapon context, temporal state, and economic state.

**Evidence:**
```python
# jepa_model.py L465 (stale docstring)
"""Generates heuristic concept labels from a 19-dim feature vector."""
# Indices 0-18 are used for labels; 19-24 are never referenced
```

**Recommendation:** Update ConceptLabeler to handle all 25 features, or explicitly document which features are intentionally excluded and why.

---

### F3-02: Non-Deterministic JEPA Negative Sampling (CRITICAL)
**File:** `backend/nn/training_orchestrator.py:342`
**Skill:** ml-check, correctness-check
**Rule:** Deterministic by default — randomness must be seeded

```python
neg_indices = np.random.choice(pool_size, size=num_neg, replace=False)
```

`np.random.choice` uses the global random state without a seed. This makes JEPA training **non-reproducible** — identical data will produce different models across runs.

**Impact:** Violates CLAUDE.md core principle "Deterministic by default". Training runs cannot be compared for regression analysis.

**Recommendation:** Use `np.random.default_rng(seed)` or set `np.random.seed()` at training start.

---

### F3-03: Wrong RAPCoachModel Import in Coach Manager Overlay (CRITICAL)
**File:** `backend/nn/coach_manager.py:760-761`
**Skill:** correctness-check

```python
from Programma_CS2_RENAN.backend.nn.model import RAPCoachModel
```

This imports from `backend.nn.model` which defines `AdvancedCoachNN` and `TeacherRefinementNN`. There is **no `RAPCoachModel` in that module**. The correct import is `backend.nn.rap_coach.model`. This line will raise `ImportError` at runtime when `get_interactive_overlay_data()` is called.

Additionally, L776 uses `RAPStateReconstructor` which calls the legacy TensorFactory API without `knowledge` parameter (see Phase 2 F2-49), creating a training/inference skew.

**Impact:** Interactive overlay feature is completely broken at runtime for mature coaches.

---

### F3-04: NameError in train_pipeline.py (CRITICAL)
**File:** `backend/nn/train_pipeline.py:26`
**Skill:** correctness-check

```python
model = TeacherRefinementNN(INPUT_DIM, OUTPUT_DIM, HIDDEN_LAYERS)
```

`OUTPUT_DIM` is imported from `config.py` (value 4), but `HIDDEN_LAYERS` is **never defined or imported** anywhere in the file or its imports. This will raise `NameError` at runtime.

**Evidence:** Searching the entire file — only imports are `BATCH_SIZE, EPOCHS, INPUT_DIM, LEARNING_RATE` from config.

**Impact:** `run_training()` in train_pipeline.py is dead code — will crash on any invocation.

---

## HIGH Findings

### F3-05: Inconsistent Position Scale Factor (HIGH)
**File:** `ghost_engine.py:153` vs `coach_manager.py:814`
**Skill:** correctness-check

GhostEngine uses `SCALE_FACTOR = 500.0` to convert model delta to world coordinates. Coach manager's overlay uses `1000` for the same purpose:

```python
# ghost_engine.py L153
SCALE_FACTOR = 500.0
ghost_x = current_x + (optimal_delta[0] * SCALE_FACTOR)

# coach_manager.py L814
ghost_x = tick.pos_x + (optimal_pos[0] * 1000)
```

**Impact:** Same model output produces different ghost positions depending on which code path is used. GhostEngine positions are 2x closer to the player than overlay positions.

**Recommendation:** Extract to a single named constant in config or the RAP model module.

---

### F3-06: Position Key Name Mismatch at Inference (HIGH)
**File:** `ghost_engine.py:156-160`
**Skill:** correctness-check

```python
current_x = float(
    tick_data.get("X", 0) if isinstance(tick_data, dict) else getattr(tick_data, "x", 0)
)
```

Uses uppercase `"X"` for dict access and lowercase `"x"` for attribute access. However, the `FeatureExtractor` (vectorizer.py) uses `get_val("pos_x", ...)` and `PlayerTickState` uses `pos_x`. If `tick_data` comes from the DB model, neither `"X"` nor `"x"` will match — falls back to `0`.

**Impact:** Ghost position calculation starts from (0, 0) instead of player's actual position when using DB models, producing wildly incorrect ghost coordinates.

---

### F3-07: Thread-Unsafe Gate Weight Caching (HIGH)
**File:** `backend/nn/rap_coach/model.py:80`
**Skill:** state-audit

```python
self.last_gate_weights = gate_weights  # Instance attribute mutated during forward()
```

During `forward()`, the model writes gate weights to an instance attribute. If multiple threads call `forward()` concurrently (e.g., multiple GhostEngine instances or parallel overlay computation), gate weights from one inference will overwrite another's.

**Impact:** Incorrect sparsity loss computation and corrupted TensorBoard logging during concurrent inference.

---

### F3-08: JEPA Pre-training on Identical Frames (HIGH)
**File:** `backend/nn/jepa_train.py:106`
**Skill:** jepa-audit, ml-check

```python
# TODO: np.tile creates identical frames — JEPA sees no temporal variation.
sequence = np.tile(features, (20, 1))  # 20 pseudo-rounds (no temporal contrast)
```

The `load_pro_demo_sequences()` function creates "sequences" by tiling a single match-aggregate vector 20 times. JEPA is designed to learn temporal prediction — but with identical frames, the context-target prediction is trivially solved (copy the input). The model learns nothing meaningful.

**Impact:** The standalone `jepa_train.py` training pipeline is functionally a no-op for representation learning. The model converges to an identity mapping rather than learning temporal dynamics. NOTE: The `TrainingOrchestrator` uses real per-tick data, so this only affects the standalone script.

---

### F3-09: Stale METADATA_DIM=19 Comment in coach_manager.py (HIGH)
**File:** `backend/nn/coach_manager.py:22`
**Skill:** ml-check
**AIstate:** G-06

```python
# Canonical feature vector names (tick-level, matches METADATA_DIM=19).
```

The comment says `METADATA_DIM=19` but the actual constant is 25. While the code logic is correct (assertion at L58-59 verifies 25 entries), the stale comment misleads maintainers.

---

### F3-10: Stale "19-dim" Reference in CoachNNConfig (HIGH)
**File:** `backend/nn/model.py:18`
**Skill:** ml-check
**AIstate:** G-06

```python
input_dim: int = INPUT_DIM  # 19-dim canonical feature vector
```

Comment says "19-dim" but `INPUT_DIM` is `METADATA_DIM = 25`. Same issue as F3-09 — code is correct, comment is stale.

---

## MEDIUM Findings

### F3-11: Silent Fallback to Zero Tensors in Training (MEDIUM)
**File:** `backend/nn/training_orchestrator.py:420-445`
**Skill:** ml-check, correctness-check

When per-match SQLite databases are unavailable, `_prepare_rap_batch()` falls back to zero tensors for map/view/motion frames. The fallback is logged at WARNING level but the training step proceeds with semantically meaningless input.

**Impact:** Model trains on garbage data without an explicit signal to callers. Should either skip the batch entirely or track fallback rate as a metric.

---

### F3-12: `datetime.utcnow()` Deprecated (MEDIUM)
**File:** `backend/nn/maturity_observatory.py:53`
**Skill:** correctness-check

```python
timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
```

`datetime.utcnow()` is deprecated since Python 3.12. Use `datetime.now(datetime.UTC)` instead.

### F3-13: `datetime.utcnow()` Deprecated (MEDIUM)
**File:** `backend/nn/training_controller.py:86`

Same pattern: `now = datetime.utcnow()`.

### F3-14: `datetime.utcnow()` Deprecated (MEDIUM)
**File:** `backend/nn/training_monitor.py:27`

Same pattern: `"started_at": datetime.utcnow().isoformat()`.

---

### F3-15: `print()` in EMA `__main__` Block (MEDIUM)
**File:** `backend/nn/ema.py:96-119`
**Skill:** observability-audit
**Rule:** No `print()` debugging — use structured logging

The `__main__` block uses `print()` and an emoji (`✅`) instead of structured logging.

### F3-16: `print()` in Early Stopping `__main__` Block (MEDIUM)
**File:** `backend/nn/early_stopping.py:69-83`

Same issue: `print()` with emoji.

### F3-17: `print()` in Training Monitor `__main__` Block (MEDIUM)
**File:** `backend/nn/training_monitor.py:108-122`

Same issue: `print()` with emoji.

---

### F3-18: SHAP Zero-Vector Baseline (MEDIUM)
**File:** `backend/nn/evaluate.py:36`
**Skill:** ml-check

```python
explainer = shap.KernelExplainer(model_wrapper, np.zeros((1, X_tensor.shape[1])))
```

Using a zero vector as SHAP baseline biases attributions toward features with non-zero values. The TODO is already documented but the impact is real — SHAP explanations may be misleading.

---

### F3-19: Win Probability Training Without Validation (MEDIUM)
**File:** `backend/nn/win_probability.py:52-62`
**Skill:** ml-check

```python
for epoch in range(100):
    optimizer.zero_grad()
    outputs = model(X)
    loss = criterion(outputs, y)
```

Trains for a fixed 100 epochs on the entire dataset with no train/val split, no early stopping, and no overfitting detection.

**Impact:** Model may overfit to training data, producing overconfident win probability estimates.

---

### F3-20: Hardcoded `context_dim=5` in Advanced Superposition (MEDIUM)
**File:** `backend/nn/advanced/superposition_net.py:12`
**Skill:** ml-check

```python
# TODO: context_dim=5 is hardcoded
self.context_gate = nn.Linear(5, out_features)
```

The canonical `layers/superposition.py` uses `METADATA_DIM` (25), but the advanced version hardcodes 5. If this module is activated, a dimension mismatch will crash at runtime.

---

### F3-21: Unbounded Tick Query in Chronovisor (MEDIUM)
**File:** `backend/nn/rap_coach/chronovisor_scanner.py:183-187`
**Skill:** db-review

```python
ticks = s.exec(
    select(PlayerTickState)
    .where(PlayerTickState.match_id == match_id)
    .order_by(PlayerTickState.tick)
).all()
```

No `LIMIT` clause. A match with 250K+ ticks (standard for a 30-round game) could consume hundreds of MB.

---

### F3-22: Unbounded Match Query for Split Assignment (MEDIUM)
**File:** `backend/nn/coach_manager.py:323-325`
**Skill:** db-review

```python
all_matches = session.exec(
    select(PlayerMatchStats).order_by(PlayerMatchStats.match_date)
).all()
```

Loads **all** PlayerMatchStats records into memory for temporal split assignment. With hundreds of matches, this is acceptable, but there is no upper bound check.

---

### F3-23: Stale Checkpoint Flag Never Checked (MEDIUM)
**File:** `backend/nn/persistence.py:66`
**Skill:** correctness-check

```python
model._stale_checkpoint = True
```

When a size mismatch is detected, `load_nn()` sets `_stale_checkpoint = True` on the model but no caller ever checks this flag. The model silently runs with random weights after an architecture upgrade.

**Impact:** Inference produces random predictions without any warning to users.

---

### F3-24: RAP Trainer Uses Adam Instead of AdamW (MEDIUM)
**File:** `backend/nn/rap_coach/trainer.py:15`
**Skill:** ml-check

```python
self.optimizer = optim.Adam(model.parameters(), lr=lr)
```

All other training loops use `AdamW` with weight decay. The RAP trainer uses plain `Adam` without weight decay, creating inconsistent regularization behavior.

---

### F3-25: Non-Deterministic Random Sampling in JEPA Pre-training (MEDIUM)
**File:** `backend/nn/jepa_train.py:59`
**Skill:** ml-check

```python
start = np.random.randint(0, max_start)
```

Uses unseeded global random state for sequence windowing. Combined with F3-02, multiple sources of non-determinism exist in the JEPA training pipeline.

---

### F3-26: Synthetic Test Data in `__main__` Block (MEDIUM)
**File:** `backend/nn/jepa_train.py:306-307`
**Skill:** ml-check
**Rule:** No synthetic/fabricated data

```python
X_train = np.random.randn(100, 15, METADATA_DIM)
y_train = np.random.randn(100, METADATA_DIM)
```

The `__main__` block generates random synthetic data for fine-tuning. While this is a development-only path, it violates the project's no-synthetic-data principle.

---

### F3-27: Magic Numbers in Advantage Function (MEDIUM)
**File:** `backend/nn/training_orchestrator.py:620-630`
**Skill:** correctness-check
**Rule:** No magic numbers

```python
advantage = (
    0.4 * alive_diff +
    0.2 * hp_ratio +
    0.2 * equip_ratio +
    0.2 * bomb_factor
)
```

Weights 0.4/0.2/0.2/0.2 are not extracted to named constants or a config dataclass. Their rationale is undocumented.

---

### F3-28: Label Smoothing Artifact in Dynamic Window Targets (MEDIUM)
**File:** `backend/nn/coach_manager.py:857-858`
**Skill:** ml-check

```python
outcomes = [t.round_outcome for t in window_ticks if t.round_outcome is not None]
val = np.mean(outcomes) if outcomes else 0.5
```

Taking the mean of round outcomes across a temporal window creates an implicit label smoothing effect. If a window spans a round boundary where the outcome changes (loss→win), the target becomes ~0.5, which is uninformative.

---

### F3-29: Oversized ResNet Stack for 64x64 Inputs (MEDIUM)
**File:** `backend/nn/rap_coach/perception.py:51,71`
**Skill:** ml-check

```python
self.view_backbone = self._make_resnet_stack(3, 64, [3, 4, 6, 3])
# L71: sum(num_blocks) - 1 = 15 ResNet blocks
```

15 ResNet blocks for a 64x64 input (training resolution per `TrainingTensorConfig`) is excessive. After multiple stride-2 downsampling, feature maps become 1x1 or smaller well before block 15. Significant wasted compute.

---

## LOW Findings

### F3-30: EMA `state_dict()` Shallow Copy (LOW)
**File:** `backend/nn/ema.py:86`

```python
return self.shadow.copy()  # dict.copy() — tensors are NOT cloned
```

If the returned dict is modified externally, the EMA shadow weights are corrupted.

---

### F3-31: TrainingCallback ABC Without @abstractmethod (LOW)
**File:** `backend/nn/training_callbacks.py:29`

`TrainingCallback` extends `ABC` but no methods are decorated with `@abstractmethod`. This means any class can extend it without implementing any hooks, which is intentional (opt-in pattern), but inconsistent with traditional ABC usage.

---

### F3-32: role_head.py Non-Reproducible Train/Val Split (LOW)
**File:** `backend/nn/role_head.py:190`

```python
perm = torch.randperm(n)
```

No seed for `torch.randperm`, making the 80/20 split non-reproducible across runs.

---

### F3-33: Deprecated `_resolve_pro_baseline` Still Present (LOW)
**File:** `backend/nn/coach_manager.py:658-660`

Dead method that just delegates to `_get_pro_baseline_vector()`. Should be removed.

---

### F3-34: SelfSupervisedDataset `__len__` Can Return 0 (LOW)
**File:** `backend/nn/dataset.py:50-51`

```python
def __len__(self):
    return max(0, self.num_samples)
```

The constructor raises `ValueError` for negative `num_samples`, but `max(0, ...)` implies it could handle 0 length. A zero-length dataset passed to DataLoader will silently produce no batches.

---

### F3-35: TensorBoard Custom Layout Hardcodes lr/group_0 (LOW)
**File:** `backend/nn/tensorboard_callback.py:198`

The custom layout references `"lr/group_0"` but models with multiple param groups would have `lr/group_1`, etc.

---

### F3-36: Win Probability Fixed 100 Epochs, No Early Stopping (LOW)
**File:** `backend/nn/win_probability.py:53`

Redundant with F3-19 but specifically: no checkpointing, no learning rate scheduling, no gradient clipping.

---

### F3-37: Communication Templates Use Static Placeholders (LOW)
**File:** `backend/nn/rap_coach/communication.py:63-69`

```python
return template.format(
    angle="the flank",  # Always "the flank"
    recommendation="conservative" if confidence > 0.8 else "aggressive",
)
```

The `{angle}` placeholder always resolves to `"the flank"` regardless of actual game context. The advice appears dynamic but is actually templated with static values.

---

### F3-38: test_arch.py Hardcodes Input Resolutions (LOW)
**File:** `backend/nn/rap_coach/test_arch.py:20-22`

```python
view_frame = torch.randn(batch_size, 3, 224, 224)
map_frame = torch.randn(batch_size, 3, 128, 128)
```

Hardcodes 224x224 and 128x128, but training uses 64x64 (`TrainingTensorConfig`). The test verifies a resolution the production training pipeline doesn't use.

---

## Tensor Shape Contract Verification

| Component | Expected Shape | Verified |
|---|---|---|
| FeatureExtractor output | (25,) | config.py L104: `INPUT_DIM = METADATA_DIM = 25` |
| Perception (view) input | (B, 3, H, W) | perception.py L51: Conv2d in_channels=3 |
| Perception (map) input | (B, 3, H, W) | perception.py L53: Conv2d in_channels=3 |
| Perception (motion) input | (B, 3, H, W) | perception.py L59: Conv2d in_channels=3 |
| Perception output | (B, 128) | view(64ch) + map(32ch) + motion(32ch) = 128 |
| Memory input | (B, seq, 128+25) | memory.py L21: perception_dim + metadata_dim |
| Memory belief output | (B, seq, 64) | memory.py L50: Linear(hidden, 64) |
| Strategy output | (B, output_dim) | strategy.py L75: MoE weighted sum |
| Pedagogy value | (B, 1) | pedagogy.py L15: Linear(64, 1) |
| Position Head | (B, 3) | rap_coach/model.py L75: Linear(hidden, 3) |
| JEPA encoder input | (B, seq, METADATA_DIM=25) | jepa_model.py L30: Linear(input_dim, ...) |
| JEPA latent | (B, 256) | jepa_model.py L31: encoder_dim=256 |
| Role Head input | (B, 5) | role_head.py L56: ROLE_INPUT_DIM=5 |
| Role Head output | (B, 5) | role_head.py L57: ROLE_OUTPUT_DIM=5 |
| Win Probability input | (B, 9) | win_probability.py L15: input_dim=9 |

**NOTE:** GhostEngine output uses `optimal_pos[0:2]` (dx, dy only), but the Position Head outputs 3 dimensions (dx, dy, dz). The Z component is silently discarded at inference.

---

## Architecture Quality Assessment

### Strengths
1. **Modular RAP Architecture**: Clean separation into Perception/Memory/Strategy/Pedagogy layers
2. **Observatory Framework**: Well-designed callback system (zero-impact, error-isolated)
3. **Player-POV Perception**: New sensorial model properly separates known from unknown information
4. **EMA for Target Encoder**: Correctly prevents JEPA collapse (BYOL-style asymmetry)
5. **Multi-Scale Chronovisor**: Elegant 3-scale temporal analysis with cross-scale dedup
6. **Maturity State Machine**: 5-state lifecycle (doubt→crisis→learning→conviction→mature) is well-conceived

### Weaknesses
1. **Stale Comments**: Three separate "19-dim" references (G-06) risk confusing contributors
2. **Non-Determinism**: At least 3 sources of unseeded randomness in training paths
3. **Dead Code**: train_pipeline.py is broken, _resolve_pro_baseline is deprecated
4. **Inconsistent Scale Factors**: 500 vs 1000 for position delta scaling
5. **Missing Validation**: Win probability and some standalone scripts lack train/val splits

---

## Remediation Priority Matrix

| Priority | ID | Effort | Blast Radius |
|---|---|---|---|
| **P0** | F3-03 | LOW | ImportError blocks overlay feature |
| **P0** | F3-04 | LOW | NameError blocks train_pipeline.py |
| **P1** | F3-01 | MEDIUM | VL-JEPA concept alignment ignores 24% of features |
| **P1** | F3-05 | LOW | Inconsistent ghost positioning |
| **P1** | F3-06 | LOW | Ghost starts from (0,0) with DB models |
| **P1** | F3-23 | LOW | Silent random predictions after arch upgrade |
| **P2** | F3-02 | LOW | Non-reproducible training |
| **P2** | F3-07 | MEDIUM | Concurrent inference corruption |
| **P2** | F3-08 | HIGH | Standalone JEPA training learns nothing |
| **P2** | F3-09, F3-10 | LOW | Misleading maintainer comments |
| **P3** | F3-11 to F3-29 | MEDIUM | Various medium-severity issues |
| **P4** | F3-30 to F3-38 | LOW | Low-severity issues |

---

## Cross-Phase References

| This Phase | Related To |
|---|---|
| F3-01 (ConceptLabeler 19-dim) | Phase 2 F2-01 (METADATA_DIM contract) |
| F3-06 (Key name mismatch) | Phase 2 F2-01 (vectorizer uses "pos_x") |
| F3-11 (zero tensor fallback) | Phase 2 F2-49 (state_reconstructor legacy API) |
| F3-21 (unbounded tick query) | Phase 1 F1-09 (unbounded queries pattern) |
| F3-23 (stale checkpoint) | Phase 1 F1-12 (persistence layer gaps) |
