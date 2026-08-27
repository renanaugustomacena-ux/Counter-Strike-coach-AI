# Cluster 07b — `backend/nn/` training orchestration

Files read: training_orchestrator, coach_manager, persistence, train, training_callbacks,
training_config, training_controller, training_monitor, evaluate, win_probability_trainer,
maturity_observatory, tensorboard_callback, embedding_projector, role_head.

## TrainingOrchestrator (the production loop)

- Pipeline: pre-training data-quality gate (P3-D, abort on fail) → model via factory + checkpoint resume (best_val restored from sidecar B3.2 — without it every resume "improved" on +inf and clobbered the best checkpoint) → per-epoch loop with rotating train subsample (B1: seed=GLOBAL_SEED+epoch; val FIXED at GLOBAL_SEED for stable early stopping) → per-epoch collapse-detector feed (F-0024: the hard-stop was wired only in the never-called JEPATrainer.train_epoch — production loop now feeds it) → checkpoint best + latest with sidecar metadata.
- **JEPA batches are ONE contiguous single-player window** (context 10 + next-step target 1): R4 CRIT — the old flat-tick feed trained "next-step prediction" on unrelated random rows ("a plausible cause of the ~1.90 val-loss plateau"). `_fetch_jepa_windows` reuses the seeded anchor machinery then expands to contiguous (demo, player) streams.
- **Cross-match negative pool** (NN-H-03): negatives come from other matches, not the same temporal sequence; TRAIN batches only feed the pool (R4: val features must never become training negatives — split hygiene inside the contrastive objective); warmup→pool transition logged once.
- Loss accounting integrity (R4 HIGH): skipped batches excluded from denominators — epochs with different skip fractions had non-comparable val losses "corrupting best-checkpoint and early-stopping decisions". Scheduler not stepped on zero-batch epochs (TASKS#59).
- **Dry-run is non-destructive by contract** (B4): tracks best/patience identically but never writes checkpoints (a --dry-run once overwrote production weights — "Law 7 violation").
- `_checkpoint_extra_meta`: **head_trained=False on all orchestrated jepa runs** (F-0029) — pretrain-only runs have a randomly-initialized coaching head and the insight adapter refuses them; only a future supervised finetune-promotion writes True. RAP checkpoints record training tensor resolutions (F-0026) for serve-time parity checks.
- RAP batch prep: per-tick PlayerKnowledge from shards (bulk prefetch: 2 queries instead of 288 per window), per-demo tick-rate-aware builders (C1.2), **LEAK-01 guard: value target masked (not substituted) when knowledge/context missing — round_outcome is a future-leak label**; advantage function = 0.4·alive + 0.2·hp + 0.2·equip + 0.2·bomb ∈ [0,1] (G-04: continuous advantage over binary win/lose); side resolved via team_codes (F-0025 — "the old getattr made every production sample CT"); next-position deltas (RAP-AUDIT-02, position head had zero loss without them); real inter-tick timespans for the LTC ODE (RAP-AUDIT-05, per-demo rate); **windows require ≥50% POV density** (T-2: zero-POV windows "taught the model that vision data is uninformative"); aggregate zero-tensor fallback >30% ⇒ training ABORTED (P3-C); map fallback to de_mirage warns once per demo (C-1).
- W2.5/DR-17 opt-in train-vs-val drift telemetry in 25-dim model-input space (rotating train window vs fixed-val reference); escalates once per run; never kills training.

## CoachTrainingManager (the curriculum)

- 5-phase cycle: JEPA pretrain → pro baseline (supervised, `train_nn`) → user adaptation (fine-tune from pro base) → RAP → role head. "Global wisdom + Local Adaptation."
- **Split assignment doctrine** (`assign_dataset_splits`): chronological 70/15/15, pros/users split independently; **eligibility gates** — P4-A shard completeness ("did the tick data land?"), MIN_COMPLETE_MAP_ROUNDS=13 ("is this a whole map?" — MR12 floor; fragments of 2-9 rounds observed in TRAIN), nonzero aggregates ("are the labels real?"); each gate skipped (not failed-universal) when its signal is unavailable — "a missing input must not silently empty the training pool". **Slices on MATCHES, never rows** (a row-index cut put one player in TRAIN and nine in VAL of the same demo). OI-2 warning names the share of rows whose "chronology" is really ingestion order. Ineligible rows demoted to UNASSIGNED.
- `_get_completed_demo_names` (P4-A): per-shard failure counted as incomplete, only total signal absence returns None — "that distinction is load-bearing" (one unreadable shard used to readmit 259 permanently-incomplete demos).
- **B1-XL**: corpora >2M eligible ticks sampled by seeded id-space rejection (uniform over id RANGE, documented bias tradeoff) — exact materialization OOMed at 429M rows (earlyoom SIGTERM); COUNT/min/max cached per corpus per process (~25min saved per epoch on the full monolith).
- Maturity: soft gate at 50 demos (UI "Calibrating"), tiers CALIBRATING/LEARNING/MATURE with confidence multipliers 0.5/0.8/1.0 — **coaching confidence is explicitly scaled by data maturity**.
- Operator stop: TrainingStopRequested propagates through every phase (F-0032: the old StopIteration guards matched nothing and "training marched on").
- Legacy dead RAP path DELETED with a tombstone comment naming its latent LEAK-01 defect.

## Persistence (persistence.py) — checkpoint doctrine

- `save_nn`: atomic (tmp+replace, checkpoint before sidecar "so consumers never see a sidecar without weights"); **GAP-07 sidecar** records schema_version + METADATA_DIM + FEATURE_NAMES + heuristic config; `load_nn` validates it and raises **StaleCheckpointError on any drift** ("refuse to load a checkpoint whose feature-schema cannot be verified"); missing sidecar = legacy warn. CTF-1 SHA-256 hash registry (corrupted registry preserved as .corrupt, never silently rebuilt). Load ladder: user → global → factory-bundled. **NN-14: no checkpoint ⇒ FileNotFoundError — "never silently return a model with random weights."** strict=True load; size mismatch ⇒ StaleCheckpointError ("prevents the 'placebo' effect").

## Observability stack (the Coach Introspection Observatory)

- Layer 1 callbacks (registry with error isolation), Layer 2 TensorBoardCallback (loss/gap, LR, param/grad histograms, gate stats, belief histograms, concept norms, **collapse metrics on a FIXED probe batch** — "so embed/* trends reflect the model changing rather than the input changing"; unconsumable probe disables once, loudly; run dirs stamped with UTC + device tag so "a Windows CPU smoke run isn't mistaken for a real ROCm run"), Layer 3 **MaturityObservatory** — 5-state machine doubt/crisis/learning/conviction/mature from belief entropy, gate specialization, concept focus, value accuracy, role stability; conviction index weighted composite; **PRE-6 concept-temperature saturation alarm** (10 consecutive epochs within 5% of either clamp edge ⇒ "binary collapse" or "uniform/non-discriminative" error), Layer 4 EmbeddingProjector (TB projector + UMAP images of belief/concept spaces: "clusters forming = conviction, scattered = doubt").
- training_monitor.py: RFC-8259-honest JSON (NaN→null, allow_nan=False so regressions fail loudly), atomic writes.

## Others

- train.py: legacy supervised loop (refuses <20 samples P1-04) + prototype JEPA self-supervised branch; MoE aux loss consumed in finetune (R4: it "was never added to ANY objective — the claimed expert-collapse protection was inert").
- training_controller.py: monthly quota + diversity score (cosine vs last 5 matches) — fail-safe: don't train on error.
- role_head.py: 5→32→16→5 MLP on Ext_PlayerPlaystyle labels (KL loss, label smoothing, normalization stats persisted beside checkpoint); FLEX below 0.35 confidence; consensus with heuristic classifier.
- evaluate.py: SHAP explanations with sample-mean baseline (NN-EV-01).
- win_probability_trainer.py: 9-dim offline trainer explicitly separated from the 12-dim real-time WinProbabilityNN ("Do NOT cross-load checkpoints"); compat alias deliberately removed (A-12).

## Doctrine candidates

- Data eligibility is a stack of orthogonal, individually-skippable gates; splits cut between matches on real chronology; sampled data stays deterministic per (seed, corpus).
- Checkpoints are self-describing, integrity-hashed, schema-validated; stale ⇒ refuse + retrain; random weights are never silently served; pretrain-only heads are marked untrainable-for-inference.
- The model's maturation is *observed* (5-state machine, conviction index, saturation alarms, UMAP) — introspection is a standing subsystem, not debug code.
- Every "fix" in this cluster names the failure it prevents — the code is its own incident database (F-/R4/B/LEAK IDs).
