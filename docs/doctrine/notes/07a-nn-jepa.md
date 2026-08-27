# Cluster 07a — `backend/nn/` JEPA core

Files read: jepa_model, jepa_trainer, jepa_train, ema, collapse_metrics, early_stopping,
data_quality, config, model, factory, dataset.

## Architecture (jepa_model.py)

- **JEPACoachingModel**: context encoder + EMA-only target encoder (MLP-style JEPAEncoder: Linear 512 → latent 256, LayerNorm+GELU) + JEPAPredictor (latent→2·latent→latent). Prediction happens IN LATENT SPACE (the JEPA principle). Downstream: 2-layer LSTM (dropout 0.15 per Supplement_N260 §P2-4) → **top-2 sparse MoE** (3 experts, raw-logit gate J-3; dense softmax "causes all experts to converge to near-identical functions") with Switch-Transformer load-balancing aux loss (Phase 3A) → sigmoid output (WR-52: tanh systematically underpredicted near 1.0). OUTPUT_DIM=10.
- Contrastive machinery: **InfoNCE with learnable CLIP-style temperature** (log 0.07 init, clamped [0.01, 1.0]); **MoCo queue 4096** with FIFO enqueue of normalized target embeddings; **VICReg regularization** (λ_var=25, λ_cov=1, weighted 0.01) against collapse.
- **EMA target update** guarded by NN-JM-04: raises if target encoder has requires_grad=True ("EMA would corrupt gradient-based learning"). **J-6 cosine momentum schedule** τ: 0.996→1.0 (Assran et al. CVPR 2023 §3.2); REPR-01 persists/rehydrates the schedule counters through checkpoints (legacy checkpoints warn loudly).
- **Selective decoding** (forward_selective, VL-JEPA idea): re-decode only when pooled-embedding cosine distance > threshold; ANY-sample rule (max) — batch-mean averaging suppressed the one sample that needed decoding (R4).
- **VLJEPACoachingModel**: +16 learnable concept prototypes with taxonomy (`COACHING_CONCEPTS`: positioning/utility/decision/engagement/psychology dimensions — the interpretability bridge). Concept similarity scaled by learnable temperature (init 0.10 per N=266 supplement). **F-0023: the loss consumes temperature-SCALED logits** — raw cosine confined sigmoid to [0.269, 0.731] and gave τ zero gradient.
- **ConceptLabeler**: two modes with an explicit leakage hierarchy — `label_from_round_stats` (outcome-based, "the model must learn to predict outcomes from features instead of reconstructing known feature patterns", G-01) is preferred; `label_tick` (heuristic from the input features) carries a WARNING docstring (NN-JM-03 label leakage) and a one-shot runtime warning.

## Training (jepa_trainer.py + jepa_train.py)

- JEPATrainer: AdamW (weight decay 1e-2 per Loshchilov-Hutter), concept params at 0.05× LR (KT-05, VL-JEPA §4.6 anti-collapse), linear warmup 5% → cosine decay, AMP + grad accumulation ×4 + clip 1.0, MoCo queue negative augmentation (64 sampled), tabular augmentation on CONTEXT only (BYOL paradigm: "target stays clean"), in-batch negatives with self-exclusion (O(B²) NN-TR-01; vectorized variant in jepa_train).
- **Collapse defense in depth**: per-batch variance telemetry (`_log_embedding_diversity`, warn <0.01) → epoch-mean fed to **EmbeddingCollapseDetector (P9-02): 2 consecutive collapsed epochs ⇒ EmbeddingCollapseError raised, training ABORTED** ("silent collapse renders all subsequent metrics meaningless"); NaN treated as collapse. Complemented by telemetry-only `collapse_metrics.py`: RankMe effective rank (deliberately UNcentered — centering would hide collapse), off-diagonal cosine, EMA drift; explicitly separated from the control-flow gate ("do not feed one to the other").
- VL path records `label_source` per batch into LabelSourceMonitor (G-01 1%/5min alarm); skipped-concept batches fall back to InfoNCE-only, loudly, once.
- Drift: DriftMonitor + should_retrain(3-of-5) → `retrain_if_needed` resets LR schedule, EMA schedule (V-3: stale _ema_step froze the target encoder), and the collapse counter.
- jepa_train.py (standalone CLI path): tick-level sequences via the SAME FeatureExtractor (J-1: eliminated round-aggregate/tick-level "semantic collision" — I-JEPA operates on observations, not summaries). **DATA-01: avg_kast is NOT injected per-tick — "a post-hoc match aggregate broadcast to every tick leaks future information and creates train-serve skew"** (the repo's flagship leakage fix). WR-53 padding repeats last tick (zero vectors encode impossible states). 26-RANGE-01: finetune refuses 25-dim targets against the 10-dim head — "the supervised coaching-target contract is undefined; define it before running" (fail loudly over silently broadcasting). Checkpoint save is atomic with EMA counters; weights_only=True on load.

## Support

- config.py: GLOBAL_SEED=42, `set_global_seed` (deterministic algorithms warn_only, DET-02), seeded DataLoader generators (DET-01); device selection prefers discrete GPU by VRAM with integrated-GPU keyword penalty; **ROCm quirk: cudnn/MIOpen disabled on hip** (rocrand JIT failure on gfx1201); bf16 `amp_autocast` (no GradScaler needed; "the only fast matmul path on gfx1201 wheels"); ML_INTENSITY throttling (delay/batch size); RAP_POSITION_SCALE=500 canonical.
- model.py AdvancedCoachNN (legacy supervised): same LSTM+MoE shape, GAP-10 top-K sparse gate retrofitted (state_dict key change ⇒ StaleCheckpointError, retrain required — no silent compat shim); tanh output (legacy); ModelManager versioned saves with self-describing architecture metadata (P1-12).
- factory.py: single instantiation point for default/jepa/vl-jepa/rap/rap-lite/role_head + canonical checkpoint names; int-coercion guard on dims.
- data_quality.py: pre-training gate (min ticks, ≤10% zero-position rate, train split non-empty, per-item shard completeness OI-1) — orchestrator ABORTS on failure.
- early_stopping.py: standard patience-based + the P9-02 detector (see above).
- ema.py: generic shadow-weights EMA with clone-on-apply/restore (NN-16 aliasing).

## Doctrine candidates

- Predict in latent space; learn from observations, not aggregates.
- **Anti-leakage is a design axiom**: outcome-based labels over feature-derived labels; no future-known aggregates in per-tick features; undefined supervision contracts fail loudly rather than train on garbage.
- **Collapse is a first-class failure mode** with telemetry (RankMe et al.), advisory warnings, and a hard abort — three separate layers by intent.
- EMA target discipline: frozen, schedule-persisted, guard-railed.
- Interpretability is architectural (16 named concepts, taxonomy, temperature-monitored), not post-hoc.
