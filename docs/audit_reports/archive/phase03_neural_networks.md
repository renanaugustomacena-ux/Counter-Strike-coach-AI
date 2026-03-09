# Deep Audit Report — Phase 3: Neural Network Architecture

> **STATUS: HISTORICAL — All FIXED items removed (2026-03-08)**
> Cross-referenced against DEFERRALS.md. Only ACCEPTED design decisions and MONITORING items retained.

**Date:** 2026-02-27
**Files Audited:** 41 / 41
**Original Issues:** 38 (4 CRITICAL, 6 HIGH, 19 MEDIUM, 9 LOW)
**Remaining:** 6 (5 ACCEPTED + 1 MONITORING)

---

## Accepted Design Decisions (5)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F3-28 | `coach_manager.py:857` | LOW | Mean of round_outcome across temporal window creates a smoothed signal; label smoothing artifact ~0.5 at round boundaries is expected |
| F3-30 | `ema.py:86` | LOW | EMA `state_dict()` returns shallow copy — tensors not cloned. Accepted as low-risk if callers don't mutate returned dict |
| F3-31 | `training_callbacks.py:29` | LOW | `TrainingCallback` extends ABC without `@abstractmethod`; callbacks are opt-in by design, not mandatory |
| F3-35 | `tensorboard_callback.py:198` | LOW | `lr/group_0` hardcoded — models with multiple param groups would need extension |
| F3-38 | `rap_coach/test_arch.py:20` | LOW | Hardcodes 224x224 test inputs but training uses 64x64; acceptable test-only discrepancy per TrainingTensorConfig |

## Monitoring Items (1)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F3-18 | `evaluate.py:40` | MEDIUM | Zero-vector SHAP baseline biases attributions toward features with large absolute values. Replace `np.zeros` with mean of representative training sample for calibrated explanations |
