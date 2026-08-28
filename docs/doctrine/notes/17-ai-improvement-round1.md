# AI-architecture improvement — round 1 (2026-08-28)

Following DOCTRINE.md Phase A. Method: a 4-agent deep re-study of the AI architecture only
(JEPA core / training orchestration / serving seams / SSOT+duplication — within the standing
5-sub-agent cap), findings verified against code (two dynamically, in the venv), then fixes
landed one PR at a time, each with regression tests exercising the real seams.

## Register verification results

- **CONFIRMED**: D-02, D-03, D-04 (with additions), D-05 (sharpened: the console counts
  PlayerMatchStats ROWS incl. pros — same 50/200 thresholds applied to a ~10× different unit
  than the other two sites; plus a FOURTH ladder encoding in jepa_insight_adapter), D-07
  (sharpened: "aim" does not exist in book v3 at all — only ~28% of the 466 book entries are
  feature-matchable), D-09 (all four legs verified: no dataset builder, zero callers, 9-dim
  trainer incompatible with the served 12-dim net, promotion path has no sidecar/hash).
- **REFUTED**: D-06's SkillLatentModel duplication — `nn/rap_coach/skill_model.py` is a 9-line
  P9 shim; ONE implementation exists (processing/skill_assessment.py) and it carries the R4
  0.0-is-real fix. Note 13b #4 is stale.
- **PARTIAL**: D-06's RAP trees — the legacy tree is 100% deprecated one-line shims (P9-01
  complete); residue is 3 production files importing via the shim path (visualizer.py:346,
  tactical_vm.py:191, backend_validator.py:372). D-04's trade_kill_detector literal claim was
  stale (it already used DEFAULT_TICK_RATE); the real residue was the missing validity window
  (now fixed).
- **Stale note prose (Law I)**: note 03's claim that demo_loader's parser boundaries use the
  F-0006 `is_parse_error` idiom is wrong — they are `except Exception`, and `parse_header` at
  the load path was entirely unguarded. Note 13b #10 (two RAP trees under test) is resolved by
  P9-01; #11's sweep blind spot had a FOURTH escaped site (round_stats_builder:236).

## New defects found (now registered as D-13..D-26)

Verified this round; asterisks = fixed this round:

- *D-13 (P0)*: P9-02 collapse detector false-fired at epoch 2 of EVERY orchestrated run —
  production batches are one window (B=1), `_log_embedding_diversity` returned a constant 0.0
  ("unmeasurable" conflated with "collapsed"). Dynamically verified. VICReg also inert at B=1.
- *D-14 (P0)*: VL-JEPA passed one RoundStats per CONTEXT TICK — (10,16) labels vs (1,16)
  logits crashed BCE on the first labeled batch (dynamically verified); k=1 silently mispaired.
- *D-15 (P1)*: the CLI pretrain loaders ignored `dataset_split` (trained on val/test matches,
  Law II) with engine-dependent row order (DET-01 gap).
- *D-16 (P1)*: the TensorBoard collapse-telemetry probe received raw ORM rows it could not
  consume — embed/* (RankMe, effective rank, EMA drift) silently dead on every production run.
  With D-13: all three collapse layers were defective at once on the production path.
- D-17 (P2, registered): eval_harness `_expert_utilization` reads `model.encoder` which never
  existed — the MoE-routing section ERRORs the moment a checkpoint lands; also measures only
  the last forward and does not label its synthetic input.
- *D-18 (P1)*: validation scored with the default temperature 0.07 while training optimized a
  learned tau — best-checkpoint/early-stopping ranking off-objective.
- *D-19 (P0)*: the P3-C "Training ABORTED" gate returned success (F-0043 broken in the same
  function that cites it); checkpoints from the aborted run stayed promoted.
- *D-20 (P0)*: `_fetch_jepa_ticks`'s legacy LIMIT fallback dropped split/is_pro/completeness
  filters — TRAIN and VAL received identical monolith rows when it fired (Law II).
- *D-21 (P1)*: sample gate counted windows×batch_size (~3× fiction both ways).
- *D-22 (P2)*: ~0.1–0.2% of JEPA windows spanned the round reset — next-step prediction
  trained on spawn teleports. R5-lite guard landed (drop, never pad); full R5 stays roadmap.
- D-23 (P0-when-armed, registered): RAP training path — event-window literals 320/64 halve
  event memory on 128-tick demos; the terminal sub-window of every batch carries a fabricated
  [0,0,0] stand-still position label (mask, don't substitute — LEAK-01 pattern); fully-masked
  val batches counted as 0.0 in the denominator; `_fetch_rap_windows` reads only the FIRST
  ~1000 rows per player (warmup/pistol bias). All dormant while USE_RAP_MODEL=False.
- D-24 (P1, registered): the MoCo queue reintroduces same-stream near-duplicate negatives in
  latent space (NN-H-03's failure, one level up) — queue entries carry no (demo, player)
  identity to mask against.
- D-25 (P1, registered): the orchestrator's save path never persists the J-6 EMA schedule
  counters or `is_pretrained` (only jepa_train's separate format does) — every orchestrator
  resume silently restarts the momentum schedule; `set_total_steps` mixes old counters with
  new totals. Also: val negatives churn with the train pool + shared RNG (val data pinned,
  objective not).
- D-26 (adjudicate, registered): `CoachingService.generate_new_insights` appears to have NO
  production caller (grep: tests + validators only) — run_ingestion has its own parallel
  implementation. If confirmed at the entrypoint level, the P9-03 chain, C-01 guarantees and
  the F1.2 JEPA write seam are production-dead and must be wired or tombstoned (rule 2).

## Fixes landed this round (all merged to main)

| PR | Fix | Tests |
|---|---|---|
| #75 | D-03: `refresh_model()` re-runs the resolution ladder; caption shows the effective model | 5 new + ui_smoke |
| #76 | D-02: repaired the dead per-player analysis block against the real hybrid API; truthful provenance relabels (module docstring, system prompt, block headers); F3 gate un-inverted; stale stream-cancel cleared; heatmap_engine phantom ref fixed | real-seam regression on in-memory DB; 70 dialogue tests |
| #77 | D-04: demo_parser KAST window, trade_kill validation, round_stats flash window, demo_loader viewer path through `resolve_tick_rate`; ACTIVE 30*64 nade window + 32-tick scan fixed; run_ingestion de-aliased; AST sweep extended (wrapped assigns + positional `.get`) in lockstep | sweep 8 + 79 affected |
| #78 | D-13: None-for-unmeasurable + cross-window variance feed; hard-stop stays alive for true collapse | 6 new + 199 adjacent |
| #79 | D-14: one RoundStats per window (last context tick); loud one-label-per-sample contract | end-to-end trainer tests |
| #80 | D-15: `dataset_split='train'` + deterministic ORDER BY in both CLI loaders; NULL split ineligible, excluded count logged | real-SQL tests |
| #81 | D-16: prepared tensor probe (RNG state restored — negative stream untouched); unconsumable probe warns loudly | 112 incl. new |
| #82 | D-18..D-22: learned-tau val loss; F-0043 verdict threading; split-blind fallback → named refusal; real-row sample gate; R5-lite round-boundary window guard | 7 new + 172 adjacent |

## Next queue (in order)

1. D-05 maturity SSOT (design agreed: one module, CoachState.total_matches_processed basis,
   console row-count named as the failure; three delegating shims + lockstep test; absorb the
   adapter's 4th ladder).
2. D-07: category map extension to book-v3 vocabulary + lockstep index contract test; then the
   `embedding_version` column (alembic, GAP-09 pattern) wiring `trigger_reembedding` for real.
3. F-0006 parse-guard idiom for trade_kill_detector's four boundaries (+ demo_loader's), whose
   escape path breaks two written never-raises contracts.
4. D-17 eval-harness repair; D-23 RAP batch (before any USE_RAP_MODEL enablement); D-24 queue
   identity masking; D-25 EMA sidecar persistence + pinned val negatives.
5. D-26 adjudication (entrypoint-level caller trace for generate_new_insights); D-01 zombie
   SSOT (cross-daemon semantics — needs its own careful round).
6. Then Phase B: R9 win-prob (12-dim trainer per the verified spec: MatchTickState snapshots,
   match-level splits, sidecar; explicit owner decision on the two sourceless features),
   supervised finetune promotion (head_trained=True), R1 surprise channel (gate:
   pretrain_epochs_completed marker — analogous to, not identical to, F-0029), R4 probes.

Paper-grounded improvements (16-papers.md §4) remain gated behind Phase A/B exits per the
doctrine's phase plan.
