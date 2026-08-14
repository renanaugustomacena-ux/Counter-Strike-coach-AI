# Wave Log — gate evidence per wave / phase boundary

Every entry records: scope (F-ids or batch range), commits, gate evidence (named pytest
counts incl. test_ui_smoke, coverage %, headless_validator phases, manifest verify,
PNGs eyeballed by name for UI waves), CI status both legs.

(entries appended chronologically; R0 baseline lives in BASELINE.md)

## Phase N boundary — 2026-08-14 (batches B19–B25, 52 files / ~11,300 LOC read)

- Scope: entire backend/nn — foundations, JEPA/VL-JEPA model + both trainers,
  training orchestrator (solo), support/observatory, coach_manager + ghost
  inference + superposition, both rap_coach trees. Study module
  33-profiling-memoria-gc (STUDY_LOG row; leak-catalog lens applied — all
  training paths CLEAN on .item()/detach/bounded-cache discipline).
- Commits: dea0d2a (B19), 97dd1c2 (B20), f714e36 (B21), 2067e67 (B22),
  ec9bf6b (B23), 9fb4117 (B24), 5e12991 (B25). All pushed.
- Findings: F-0023..F-0026 registered (4× P2, all ML-correctness): VL-JEPA
  BCE-on-raw-cosine miscalibration (labels unfittable, train/readout
  divergence); P9-02 collapse hard-stop bypassed on the production
  orchestrator path; RAP labels computed under a team attribute the monolith
  rows don't have (EMPIRICAL: no `team` column → every sample CT-perspective);
  RAP train/serve tensor-resolution skew (64² training vs 128/224 at all
  THREE inference sites — P-SR-02 injection exists, unused). Three of four
  gated behind USE_RAP_MODEL=False. F-0016/F-0020 blast radii widened
  (concept labels; neural role head starved by missing CSV).
- S2 sweep DISSOLVED: rap_coach non-experimental tree = clean P9-01 shims,
  zero drift (sweeps/S-2.md). Three-training-paths question closed (all
  alive by design). B19/B23 zero-findings batches; persistence.py +
  vectorizer-grade quality (GAP-07 sidecars, CTF-1 hashes, atomic saves).
  CP0 status items: JEPA finetune deliberately disabled (26-RANGE-01/
  TASKS#64); win-prob predictor heuristic-only until R9 12-dim retrain;
  RAP-quality cluster (F-0025/F-0026 + concept→topic modulo scramble + EN
  advice) gates any future USE_RAP_MODEL enablement.
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed,
  48 skipped, 5 errors — 71.8s — IDENTICAL to R0 baseline** (known reds
  F-0002/F-0003 only). Coverage floor passed. test_ui_smoke.py: 4/4 green
  (named run, 7.6s).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged.

## Phase A boundary — 2026-08-14 (batches B16–B18, 12 files / 4,585 LOC read)

- Scope: backend/analysis complete — win probability + Elo, engagement range,
  momentum, blind spots, entropy, belief model, game tree, deception, movement
  quality, role classifier, utility/economy. No study module scheduled.
- Commits: f374198 (B16), 7cca008 (B17), e0c9dbe (B18). All pushed.
- Findings: F-0021, F-0022 registered (2× P2, both silent-degradation contract
  drift): deception flash-bait detection keyed to dead CS2 event vocabulary
  (player_blind never emitted → bait rate degenerates 1.0/0.0); engagement
  "entry_fragger" baseline key unreachable via canonical PlayerRole ("entry")
  → entry players never get range coaching. F-0016 blast radius widened to
  momentum.from_round_stats (eternal-loss-streak tilt spam if winner-dtype
  bug confirmed). Duplicate-PlayerRole-enum question resolved CLEAN (canonical
  core.app_types import everywhere). FOUR R4 war stories verified in place
  (ClassVar no-op calibration, TT node-type + depth-direction, halftime
  full-buy). Phase K carry-list: role-stat vocabulary caller census
  (awp_kills/entry_frags/solo_kills suppliers), game_tree learn_from_match
  event vocabulary, eager analysis/__init__ torch import from daemons,
  EN-only coaching strings (L7), entropy bounding-box degeneracy consumers.
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed,
  48 skipped, 5 errors — 72.2s — IDENTICAL to R0 baseline** (known reds
  F-0002/F-0003 only). Coverage 55.40% (floor 33%) ✓. test_ui_smoke.py: 4/4
  green (named run, 7.6s).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged.

## Phase P boundary — 2026-08-14 (batches B11–B15, 30 files / ~8,700 LOC read)

- Scope: pipeline core, round-stats, tensor factory + player knowledge + heatmap,
  feature engineering, baselines + validation. No study module scheduled this phase.
- Commits: a58869b (B11), 4bcaf54 (B12), b0e9a5e (B13), cfffdcb (B14),
  8b0445a (B15). All pushed.
- Findings: F-0016..F-0020 registered (5× P2). F-0016 winner-dtype contract conflict
  (T-DIAG probe scheduled — escalates P1 if demoparser2 emits int); F-0017 heatmap
  double-Y-flip Kivy residue (dead display surface); F-0018 baseline fusion
  layer-priority inversion; F-0019 metric-scale incoherence (CSV percent vs ratio +
  sanity headshot band 100× loose); F-0020 all elite-comparison CSVs absent
  (feature dark on fresh installs — CP0 decision). Two campaign highlights:
  vectorizer.py is the strongest file audited so far (P-X-01/P3-A/D1/D2 quality
  architecture); B14 closed the slot-16 KAST-scale risk as VERIFIED COHERENT.
  Empirical DB verification used R0 backups (ProPlayerStatCard=0 rows, pro
  demos=0, avg_hs/avg_kast confirmed ratio-scale).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed,
  48 skipped, 5 errors — 72.0s — IDENTICAL to R0 baseline** (known reds
  F-0002/F-0003 only; no regression from audit commits). Coverage 55.40%
  (floor 33%) ✓. test_ui_smoke.py: 4/4 green (named run, 7.5s).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged (no UI edits).

## Phase D boundary — 2026-08-14 (batches B04–B10, 69 files / ~13,900 LOC read)

- Scope: storage core/data/aux + 3 migration trees + demo parsing + external sources
  + ingestion packages + orchestration. Study modules 09 (full) + 10 (leverage sections).
- Commits: f2aa445 (B04), 638008a (B05), dc40411 (B06), 4475ff7 (B07), 6c62d68 (B08),
  f3e226f (B09), B10 in this commit. All pushed.
- Findings: F-0012..F-0015 registered this phase (2× P1 new: undefined-logger NameError
  in shard fallbacks; worker 5-min stale threshold = the documented P4-B bug + F-0014
  dead main.py launcher). F-0006 blast radius widened; remediation template identified
  (demo_loader's validate_demo_file wiring). Recon's three-migration-trees concern
  DISSOLVED (two proper tombstones, one canonical chain).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed, 48 skipped,
  5 errors — 71.8s — IDENTICAL to R0 baseline** (known reds F-0002/F-0003 only; no
  regression from audit commits). test_ui_smoke 4/4 green inside the run.
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged (no UI edits).

## Phase F boundary — 2026-08-14 (batches B01–B03, 26 files / 5,365 LOC read)

- Scope: R0 + pass-1 Phase F (core/ + observability/) + study modules 22, 07.
- Commits: 839c24b (R0), 9f2a453 (B01), 0f19ac4 (B02), B03 in this commit. All pushed.
- Findings register: F-0001..F-0011 (2× P1, 9× P2). No fixes applied (diagnose-first).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed, 48 skipped,
  5 errors — 73.7s — IDENTICAL to R0 baseline** (known reds F-0002 tick-rate SSOT,
  F-0003 symlink privilege; no regression from audit commits). Coverage floor passed.
- test_ui_smoke.py: 4/4 green inside the run (screen walk, theme switching, language
  roundtrip, collapse/resize).
- CI: not triggered (docs-only paths are ignored by design; branch filter issue = F-0004).
- Render matrix: unchanged (no UI edits; committed design-close matrix stands).
