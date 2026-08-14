# Wave Log — gate evidence per wave / phase boundary

Every entry records: scope (F-ids or batch range), commits, gate evidence (named pytest
counts incl. test_ui_smoke, coverage %, headless_validator phases, manifest verify,
PNGs eyeballed by name for UI waves), CI status both legs.

(entries appended chronologically; R0 baseline lives in BASELINE.md)

## Pass 2 boundary — 2026-08-14 (lenses L1–L10 + L-COV + sweeps S-4/S-6/S-7) — **DIAGNOSIS COMPLETE, CP0 PRESENTED**

- Scope: all ten cross-cutting lenses assembled into CONTRACTS.md (one commit
  each or grouped), every one of the 618 ledger rows now carries ≥1 lens tag
  (L-COV rule satisfied, 0 untagged). Sweeps closed: S-6 delegated censuses
  (verified counts), S-4 redo (satisfied via L3/L9 assembly), S-7 (performed
  through Phase-T dossiers; asymmetries recorded).
- S-6 headline results: the 22 core→backend layering edges are ALL in
  session_engine (composition root — W3 shrinks to an ADR paragraph); ZERO
  real bare-excepts (validator enforces the ban); ZERO `raise e`; prints
  ~all in __main__ debug blocks; 17 naive-datetime hits with NO cross-boundary
  arithmetic hazard; seed discipline exemplary (P1-02 SSOT).
- Register FINAL for CP0: **F-0001..F-0044 — 0 P0 / 12 P1 / 32 P2.**
  CP0.md written: severity table, 7 decision clusters, wave scopes.
- Gate (Pass-2 boundary): **2 failed, 2500 passed, 48 skipped, 5 errors —
  74.4s — IDENTICAL to R0 baseline**; coverage 55.40% ≥ 33%;
  test_ui_smoke.py named run **4/4 in 7.71s**. Campaign has touched zero
  production code, as designed.
- NEXT: CP0 user checkpoint — NO fixes until approval.

## Phase I boundary — 2026-08-14 (batch B76, 39 files / ~3,090 LOC read) — **PASS 1 COMPLETE: 618/618 ledger rows (100%)**

- Scope: ALL infra/config — 4 CI workflows (build.yml 471 read in full), root +
  SHADOW pytest.ini, pyproject, pre-commit, alembic.ini, .gitignore/.gitattributes/
  .env.example, 8-file requirements family, docker-compose, packaging specs +
  installer, 9 shell/batch scripts, launch.sh, both integrity manifests, SECURITY/
  governance set (skim per plan). Study module 30-troubleshooting read first.
- Findings: **F-0044 (P2) shadow pytest.ini** (invocation-dependent test config;
  file was MISSED by S1 — ledger corrected to 618 rows); **F-0041 gained (e)**:
  build_tools targets a NONEXISTENT macena.spec; **F-0001 RESOLVED the
  authoritative-manifest question** (core/ authoritative; root copy = the stale
  phantom-main.py carrier, W1 deletes it); F-0014 evidence #4 (scripts/
  build_exe.bat pyinstalls deleted main.py with Kivy); F-0004's exact filter
  line confirmed (feature/** vs feat/**). Register: F-0001..F-0044
  (0 P0 / 12 P1 / 32 P2).
- Binding W-wave constraints discovered: line-ending policy in .gitattributes
  ("do NOT renormalize globally" — 478 CRLF / 623 LF historic mix); LFS
  attributes on *.db/*.pt; black pin drift (pre-commit 24.1.1 vs plan's W4a
  24.10.0 target); compose TAG-pinned (C-DOCK-01 --check would flag).
- Gate: **2 failed, 2500 passed, 48 skipped, 5 errors — 77.9s — IDENTICAL to
  R0 baseline**; coverage 55.40% ≥ 33%. test_ui_smoke.py (named): **4/4 in
  8.19s**. CI: not triggered (docs-only; F-0004).
- Pass-1 totals: 76 batches + R0, ~154.6k LOC read personally, 44 findings
  (0 P0 / 12 P1 / 32 P2), 76 dossiers, 7 study modules logged, T-DIAG executed
  with evidence. Next: Pass 2 (S6 sweeps → L1–L10 + L-COV).

## Phase T boundary — 2026-08-14 (batches B62–B75 + T-DIAG, 167 files / ~27,500 LOC read)

- Scope: EVERY test file in the repo — infra+conftest+automated_suite (B62), NN
  training (B63), COPER/RAP/chronovisor (B64), analysis (B65), feature/tensor
  (B66), storage/config (B67), coaching engines (B68), UI suites (B69),
  regression tiers (B70), extended suites (B71), data-layer + both known-reds
  (B72), NN support (B73), remaining Programma tests (B74), root tests +
  forensics + evals (B75). Study module 08-testing read before B62 (STUDY_LOG).
  Ledger: 579/617 rows read (93.8%). Commits: one per batch, all pushed.
- Findings: **F-0043 (P2) registered from T-DIAG** — run_full_training_cycle
  exits 0 on "Training Aborted" (automation-blinding; latent inverse-guard test
  misreads it as a save bug). F-0002 enumerated LIVE: exactly ONE offender
  (tactical_viewer_screen.py:416) — W2 is a one-line SSOT import. F-0003
  decoded: fixture needs SeCreateSymbolicLink (WinError 1314) — Linux-correct
  suite, W2 = skipif-unprivileged-Windows. Register: F-0001..F-0043
  (0 P0 / 12 P1 / 31 P2).
- **T-DIAG (bounded, backed up, evidence recorded)**: DB backed up via sqlite
  backup API + models/ copied + checkpoint SHA-256s taken FIRST.
  (1) test_e2e_user_journey → SKIPPED cleanly (2 < 5 PMS rows — gate honest).
  (2) test_system_regression → 2 passed, read-only. 2.13s.
  (3) test_dry_run_checkpoint_integrity → dry-run leg PASSED (Law-7 guard:
  exit 0, zero .pt in redirected root); real-run leg FAILED → root-caused to
  F-0043 (abort-as-success), NOT a save bug. After-state verified: the
  acknowledged dry-run split write landed (UNASSIGNED×2 → TRAIN 1 + TEST 1,
  matching the B63-pinned boundary math); CoachState unchanged; **all 5
  production checkpoints byte-identical** (BRAIN_DATA_ROOT redirect held).
  No latent-suite activation work done (per plan).
- Tests-lens results for CP0: stale Bug#4 demonstration suite (B63); EN-advice
  assertion landmine spans 4 suites (B64/B68 — i18n decision must budget test
  churn or keep advice EN deliberately); rating-constants lockstep gap
  (repair_rating_scale mirror unpinned, B72); `slow` mark unregistered
  (warning noise, W4 one-liner); doctrine-pin coverage otherwise EXCELLENT —
  the war-story catalogue from Phases F-C is comprehensively pinned, incl.
  three operational disasters ($HOME shard migration, backup free-space,
  dangling-symlink self-repair).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed,
  48 skipped, 5 errors — 74.8s — IDENTICAL to R0 baseline** (known reds
  F-0002/F-0003 only; T-DIAG's split-label write changed nothing). Coverage
  floor ≥33% passed. test_ui_smoke.py (named run): **4/4 green in 7.76s**.
- User directive logged mid-phase: END STATE = ONE BRANCH (merge audit →
  design-atlas → main after W6; memory + task #20).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged.

## Phase C boundary — 2026-08-14 (batches B46–B61, 80 files / ~33,000 LOC read)

- Scope: BOTH tools directories end-to-end — console.py solo + S5 sweeps (B46), root
  CLIs (B47), headless_validator solo (B48), verify/portability tools (B49), UI
  tooling (B50), shard/db-maintenance/repair/pipeline/eval/seed/supply-chain tools
  (B51–B56), misc+fuzz+docs tooling (B57), then Programma_CS2_RENAN/tools complete:
  hltv group (B58), goliath+D2A (B59), inspectors (B60), infra+consolidated
  utilities (B61). Ledger: 411/617 rows read (66.6%).
- Commits: 0c6f9fc f5cf0c7 6bbabd2 a55a148 fceba4c 76d88b3 02d8c00 227eba1 553601e
  677add1 319792d 86c3fe0 66e8a43 ddd67fd 2b563c3 7f6877e (+ this boundary commit).
  All pushed.
- Findings this phase: **F-0037 grown to five trigger surfaces; F-0038 three screens;
  F-0039 registered→P1, census CLOSED at 13 bare-invocation mutating members;
  F-0040 (P1) build_pipeline sanitizes BEFORE honoring --test-only (compounds
  F-0039 via the verify_all_safe special-case); F-0041 (P2) build_tools triple
  drift + space-unsafe interpolation (the repo's one shell=True, closed from S5);
  F-0042 (P2) manual-entry percent-into-ratio pro rows.** F-0014 evidence grew to
  3 tools (goliath entry-point + dead_code ENTRY_POINTS; manifest itself is clean).
  Register now F-0001..F-0042: 0× P0, 12× P1, 30× P2 (grep-verified vs the register).
- Cross-cutting closures: verify_all_safe scope precisely mapped (root tools/
  rglob — ptools entirely outside); MCIV lineage resolved (probe player named
  after the superseded Clinical_Integration_Validator); dataset_split ownership
  contract (insert-time provisional → data_pipeline temporal P-DP-02 owns);
  StatCard identity contract (player_id-only upsert, one-card invariant,
  (player_id,time_span) uniqueness deferred by H1); KAST provenance ladder
  (estimator → event-accurate by data_quality); DEFAULT_STATS sentinel origin
  found (seed_hltv_top20); F-0001 manifest re-verified LIVE: 45 changed / 15 new /
  0 removed, exit 1 — identical to R0 (campaign added zero drift).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500 passed,
  48 skipped, 5 errors — 75.1s — IDENTICAL to R0 baseline** (known reds
  F-0002/F-0003 only; no regression from audit commits). Coverage 55.40% ≥ 33%.
- test_ui_smoke.py (named run): **4/4 green in 8.02s** (screen walk, theme
  switching, language roundtrip, collapse/resize).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged (no UI
  edits).

## Phase U boundary — 2026-08-14 (batches B34–B45, ~90 files / ~19,900 LOC read)

- Scope: entire apps/qt_app — app shell + core bridges (B34), theme/tokens
  core (B35), all 11 viewmodels (B36), 44+ widgets across components/charts/
  tactical/overlay (B37–B39), all 17 screens (B40–B45). Study module 20-gui
  before B34 (STUDY_LOG row); S3 sweeps executed and CLOSED (sweeps/S-3.md).
- Commits: 079dfa1 (B34), ad311f5 (B35), d3e226e (B36), d0f65d9 (B37),
  375cc4f (B38), 50d544d (B39), ad95bac (B40), 8c99c47 (B41), 673ebea
  (B42), b2eee99 (B43), 157e494 (B44), 9a04ab9 (B45). All pushed.
- Findings: F-0033..F-0038 (2× P1, 4× P2). **P1s**: F-0037 ingestion
  concurrency (three trigger surfaces — daemon auto-cycle default ON, Home,
  Settings — share an exclusion-free pipeline; snapshot task claim +
  check-then-act dedupe → double parses and duplicate stats rows); F-0038
  three screens touch the DB on the GUI thread (profile save / chronovisor
  lookup / wizard finish) against the self-documented doctrine. P2s: F-0033
  AppState staticmethod-self NameError; F-0034 MACENA_UI_ANIMATIONS honored
  by only 2/10 helpers (README claim overbroad); F-0035 EmptyState CTA rows
  never reappear (match-detail no-data/error states lose "Back to Match
  History" — invisible to the render matrix); F-0036 toast auto-dismiss
  timers fire on destroyed widgets (eviction guarantees it).
- S3 sweeps CLOSED: effects doctrine settled repo-wide (context-scoped ban,
  consistently applied; card shadows static + single frosted site; NO
  violations — memory row refined); hex census = parameter defaults +
  sanctioned token SSOT; i18n setter-census CORRECTED (constructor-arg EN
  literals escaped the grep — full L7 ledger rebuilt per dossier for Pass 2).
- Verdicts: F-0002 tick-rate semantics settled (loud fallback only, real
  header resolution — NO upgrade); F-0016/F-0019 consumer surfaces
  confirmed coherent (ratio×100 displays, dual-scale formatter); icons
  fallback census CLOSED (zero unsafe callers); MVP purity PASS (no VM
  imports widgets); streaming chat wiring verified correct end-to-end.
- Cross-phase ledgers assembled for Pass 2: theme-switch instance-style
  staleness (FilterChip/StatusChip/roster/banners — systemic L2/L6),
  fade_in-during-layout tension (1 site), map-SSOT cluster grew to 7
  lists, L7 systemic evidence per-screen (match_detail/procomp/coach
  nearly clean vs pro_player_detail/faceit/wizard EN-heavy).
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500
  passed, 48 skipped, 5 errors — 73.7s — IDENTICAL to R0 baseline**
  (known reds F-0002/F-0003 only). Coverage 55.40% (floor 33%) ✓.
  test_ui_smoke.py: 4/4 green (named run, 7.6s).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged
  (no UI edits; committed design-close matrix stands).

## Phase K boundary — 2026-08-14 (batches B26–B33, 50 files / ~12,300 LOC read)

- Scope: knowledge (experience bank, RAG/FAISS/graph, pro miner), coaching
  engines (hybrid, JEPA adapter, satellites), services (coaching_service,
  coaching_dialogue solo, analysis_orchestrator, LLM stack), control plane
  (console/supervisor/ML/ingest/governor), server, reporting. No study
  module scheduled.
- Commits: 0c33788 (B26), 54b75cb (B27), ba9d106 (B28), 849f429 (B29),
  c282fa2 (B30), dac6558 (B31), b6e5567 (B32), eb9dedc (B33). All pushed.
- Findings: F-0027..F-0032 (2× P1, 4× P2). **P1s**: F-0030 live "IGL 100%
  confidence" fabrication (classifier fed a dict with zero of its
  vocabulary keys; kd-balance bonus is the only live signal); F-0032
  operator STOP broken (TrainingStopRequested swallowed per phase —
  training continues, status reports Error). P2s: F-0027 phantom conn
  lock in knowledge graph; F-0028 hybrid engine discards its ML
  predictions; F-0029 JEPA adapter arms on pretrain-only checkpoints
  (untrained head noise); F-0031 Phase-6 dark modules (utility *_thrown
  vocabulary has no producer; game_states pending T-DIAG). F-0015 widened
  (ingest_manager same 5-min threshold). F-0016 radius widened (chat
  drill-down WON/LOST + BEST WINNING ROUNDS + momentum + orchestrator).
- Census closures (the carried list): EliteAnalytics consumer =
  analysis_service (F-0020 exposure); TemporalBaselineDecay,
  calculate_deviations ×2, MetaDrift, detect_feature_drift,
  round_reconstructor.format_for_llm, WR-76 timelines, F-0021 caller
  (live), F-0022 exposure (live) — all FOUND. F-0017 scope SETTLED
  (overlay path orientation correct; dead rgba only). role-stat
  vocabulary suppliers resolved (F-0030). S2 shims have a LIVE consumer
  (visualizer highlight report — W3 must update import). L7 systemic
  evidence complete (EN insights persisted to DB; one localized fragment).
- Showcases: coaching_dialogue = anti-fabrication + prompt-injection
  defense at its most mature (DP-03 zero-trust tool phase, BE-03, CHAT-02,
  WR-78); console.py D1-D10 lifecycle discipline; experience bank KT-01
  CRUD; player_lookup CHAT-06 sentinel suppression. B26/B30/B33
  zero-new-findings batches.
- Gate (full suite + cov, Windows `-p no:timeout`): **2 failed, 2500
  passed, 48 skipped, 5 errors — 72.8s — IDENTICAL to R0 baseline**
  (known reds F-0002/F-0003 only). Coverage floor passed.
  test_ui_smoke.py: 4/4 green (named run, 7.5s).
- CI: not triggered (docs-only; F-0004 filter). Render matrix: unchanged.

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
