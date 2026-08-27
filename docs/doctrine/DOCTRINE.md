# The AI Architecture Doctrine

Derived 2026-08-28 from a complete read of the codebase (every script; ~635 files across 16
cluster notes in `docs/doctrine/notes/`, clusters 01–15) followed by a study of the 7 research
papers in `docs/research/` mapped onto that code (note 16). Nothing below is cited from README
files, books, or other prose — every invariant terminates in code that was read, with the note
that carries the file-level evidence.

## 0. The Fundamentals (verbatim, standing at all times)

1. "the current codebase is the only focus, books and readme files are to be ignored until all
   work is done."
2. "i downloaded some pdf files to study for this purpose of enhancing the AI architecture. i got
   them from arxiv.org and you too can download some documents from that website if you need."
3. "write down small documents with your observations and thoughts as you go through your first
   codebase read, and read all the codebase before starting. all of it. dont skip even one
   script... the codebase is massive so writing down small documents will help you keep track of
   everything without hallucinating in the middle of the work."
4. "this is a highly advanced AI architecture, don't take anything for granted... to make an AI
   coach better than any other in the world, in his specific goal of learning from files
   containing information from professional or casual players matches."
5. "don't exaggerate with sub-agents, never use more than 5 sub-agents."
6. Workflow: work autonomously; commit and push at every step; short, clean commit messages, no
   AI mentions, author "Renan Macena"; the real project always stays with ONE branch — extra
   branches mean work in progress and must be merged back.

**The mission**: an AI coach better than any other in the world at learning from match files —
visual learning from data, decoding to recreate, evaluating like a real coach watching, hearing
and judging. The architecture is different from any other in the world; treat its idioms as
deliberate until the code proves otherwise.

---

## 1. The Laws (verified invariants)

Each law was observed enforced in code, usually with an incident ID naming the failure it
prevents. The codebase is its own incident database (F-xxxx, R4, GAP-xx, LEAK-xx, 26-*, P#-#,
CHAT-xx, WR-xx, DP-xx, BE-xx…); new work must extend that register, never bypass it.

### I. Truth and provenance

- **The demo file is the source of truth.** Every stored value must audit back to the replay
  (three-tier storage, DL-1 lineage, provenance flags — notes 04/05). EgoCS-400K states the same
  principle verbatim; the field has converged on our doctrine (note 16 §5).
- **Absent beats fabricated** (stated in `pro_bridge`, note 09). Honest NULLs; metrics go dark
  with a named reason rather than emit degenerate values (deception 0.0-with-reason, "n/a" over
  fake zeros, suppressed placeholder stat blocks CHAT-06 — notes 08/09/10). Repairs must never
  launder fabricated values into truth (P2-10 default-rate sentinel vs header-derived — note 12).
- **Comments and names must tell the truth.** Stale prose is a defect class: DA-03 renamed a
  module to admit it does arithmetic; F-0027 removed a phantom lock from a comment; F-0028
  renamed "ML confidence" to baseline math; "DORMANT BY DESIGN" and "NOT WIRED" are declared in
  place (notes 08/09/11). Every dormant feature carries its reason and activation plan.
- **Every hand-tuned constant is labeled as such with a validation plan** (P8-0x blocks — note
  08). Three tiers: empirically calibrated / hand-tuned pending validation / theoretical estimate.

### II. Anti-leakage (the flagship axiom)

- **NO-WALLHACK sensorial contract**: models consume only what the player could observe — FOV
  gating, memory decay in per-demo ticks, POV tensors, the 25-dim POV-derived feature contract
  (notes 06/07a/07c). The single JEPA→coaching seam re-asserts it (F1.3, note 09).
- **No future information in features**: DATA-01 (match aggregates never injected per-tick),
  LEAK-01 (value target masked — not substituted — when knowledge is missing), outcome-based
  concept labels only (G-01), VAL-features never become training negatives (NN-H-03) — notes
  07a/07b.
- **Splits cut between matches on real chronology** (P4-A shard completeness, MIN 13 complete
  rounds, nonzero aggregates, player-level decontamination, OI-2 date provenance ladder; a match
  never straddles train/val/test) — note 07b. Each eligibility gate is individually skippable
  when its signal is absent: a missing input must not silently empty the training pool.

### III. Single sources of truth

- **Tick rate is per-demo, resolved through one ladder** (column → MatchMetadata → canonical
  default with WARN; 26-NORM-01/26-TICK-02); tick decimation is FORBIDDEN; all windows are
  expressed in seconds and converted per demo. Every external CS dataset examined hardcodes
  64 t/s (notes 16 §§1,5) — our stance is stricter than the field's; hold it.
- **The 25-dim METADATA contract (P-X-01)** — METADATA_DIM == INPUT_DIM == 25, FEATURE_NAMES
  order pinned, map_id at 17, z_penalty at 15; changes require a migration manifest in the same
  commit (notes 06/13a/13b).
- Named registries: known_maps, map_callouts (WR-77), team_codes (F-0016/F-0025), rating
  components (RAW HLTV scale), ENRICHMENT_TO_PLAYERMATCHSTATS. Ratio-vs-percent is a named
  defect class with a 1.0-boundary discriminator (C-3/V-2 — note 09).

### IV. Learning discipline

- **Predict in latent space; learn from observations, not aggregates** (note 07a). The theory
  paper (note 16 §2) proves this is the right regime for noisy observations and long horizons,
  and bounds planning regret by pretraining risk. Corollary: never trust long latent rollouts
  more than linearly-degraded — keep rollouts short and leaf-corrected (game_tree already does).
- **JEPA batches are one contiguous single-player window** (context 10 + target 1; drop, never
  zero-pad — "zero vectors encode impossible game states"; R4 CRIT/V-1/J-5).
- **EMA target discipline**: frozen before update, cosine momentum 0.996→1.0 (J-6) — the exact
  mechanism two independent papers prove load-bearing (note 16 §§3,7).
- **Collapse is a first-class failure mode with three layers by intent**: variance telemetry →
  advisory warnings → EmbeddingCollapseDetector hard abort (P9-02); RankMe et al. as standing
  telemetry. Any future stacked/hierarchical JEPA multiplies collapse risk and must carry a
  per-level detector plus an early-epoch loss-statistics gate (note 16 §7).
- **Determinism**: GLOBAL_SEED=42; train seed 42+epoch, val pinned; seeded negative sampling and
  replay (DET-01 reaches even the experience bank). Loss accounting is honest (skipped batches
  out of denominators; schedulers skip zero-batch epochs).
- **Dry-run is non-destructive by contract** (B4); operator stop propagates through every phase
  (F-0032/TrainingStopRequested); training exclusivity is enforced twice (thread mutex + file
  lock, NN-02).

### V. Serving discipline

- **Random weights are never served** (NN-14 FileNotFoundError; W-02 loud degrade; strict
  loads); **checkpoints are self-describing and refused on drift** (GAP-07 sidecars,
  StaleCheckpointError, CTF-1 hash registry); **pretrain-only heads are refused at the seam**
  (F-0029 head_trained marker) — notes 07b/09.
- **Neural output reaches advice through exactly one gated seam** (JEPAInsightAdapter:
  setting-flag × trained-load × head_trained). Dead inference paths are deleted, not left
  running (F-0028). The legacy `_get_ml_predictions` caller in `coaching_dialogue` violates this
  and is registered as defect D-02 below.
- **Silence is a valid action** at every level: explainability threshold, JEPA noise gate,
  RAP confidence-gated advice suppression, Hopfield bypass, ghost lobotomy — "the system prefers
  no output to fabricated output" (notes 07c/08/09).
- **The coach's boldness scales with the model's maturity**: observatory states → hedged
  observations → plain speech; maturity multipliers scale confidence; conservative mapping until
  the observatory state is persisted (notes 07b/09/10). One maturity SSOT is owed (defect D-05).
- **Degradation is a ladder with named, user-visible levels and guaranteed non-zero output**
  (P9-03 COPER→Hybrid→Traditional+RAG→Traditional; C-01; C-41 baseline ladder with staleness
  ages; degraded-baseline tags on messages) — notes 09/10.
- **Zero-trust at the LLM boundary, both directions** (DP-03/BE-03): model-supplied arguments
  validated against DB-known values; attacker-influenceable text sanitized before prompts;
  anti-hallucination enforced structurally (VERIFIED-DATA blocks, match-inventory injection,
  disambiguate-don't-guess, tutor-mode 3rd-person rewrite) with prompt rules (WR-78/79) as the
  last layer, not the only one — note 10. EgoCS-400K's prior-constrained captioning validates
  the design (note 16 §5).

### VI. Operations

- **$HOME is never a data root** (F-0008/OI-8); storage access only via the managers (raw
  sqlite3 on a guessed path silently created empty DBs — note 09); path confinement at every
  filesystem seam (RG-01, VZ-02).
- **Destructive tools**: dry-run default, explicit `--execute`/`--confirm`, backups, audit
  logs (`wipe_for_reingest_safe` is the gold standard); remediation verifies its own effect on
  the data, not the action (rescrape `_still_default`) — notes 12/15. Convention-based safety
  (F-0039 prefix list) is acknowledged fragile — see D-11.
- **Health is computed, never cached** (D3); recovery is bounded and biased safe; integrity
  checks never block the app (DG-02); failure telemetry itself must fail loudly (26-ORCH-01);
  failure counters reset per unit of work (O-01) — note 11.
- **Mutual exclusion is tested adversarially** (TOCTOU contention, foreign-lock protection,
  dead-PID reclaim — note 12); library bugs are patched locally with written justification
  (parse_guard F-0006, RAP-LTC-FIX) — notes 05/07c.

## 2. Decision rules (how to change this system)

1. **Name the failure.** Every fix carries an incident ID and a comment naming the failure it
   prevents. A change that cannot articulate its failure mode is not ready.
2. **Replace, don't delete.** Phantom references get repointed to the real entry point;
   deprecated modules become one-line re-export shims or tombstones naming what died and why
   (P9-01, G-06).
3. **Contracts fail loudly.** Undefined supervision contracts raise (26-RANGE-01); schema drift
   refuses to load; a missing signal degrades to a named legacy behavior, never to silence.
4. **Every cross-process seam gets a round-trip test.** The telemetry client/server pair shipped
   with success unreachable end-to-end (R4, note 10) — that class of defect is caught only by
   integration tests on the contract.
5. **Duplicates converge on an SSOT or carry a lockstep warning pointing at the contract test.**
   New parallel implementations of an existing concept are defects by default (see D-05..D-07).
6. **Probabilistic reasoning over deterministic heuristics — but boundary truths first**
   (0 alive ⇒ 0.0 before any model output; note 08).
7. **Prefer entity (callout) vocabularies over coordinate grids** wherever spatial reasoning
   surfaces to a human (paper-backed; note 16 §6).
8. **Synthetic data boundary**: pure-math signal tests may generate inputs and must say so;
   anything touching the product pipeline uses real data or skips (the chronovisor twins wrote
   the boundary down — note 12).
9. **Upgrade convention to structure when a convention is load-bearing** (D-11): a filename
   prefix that prevents data loss is a bug that hasn't fired yet.
10. **When adopting anything from the papers, the invariants win.** Every roadmap item below was
    filtered against Laws I–V; e.g. CECL joins as an auxiliary objective (its full-information
    regression is documented), a surprise channel is gated like F-0029.

## 3. Defect register (adjudicated from the full read; fix before or alongside new AI work)

Confirmed contradictions and drift, with the owning note:

- **D-01 Zombie-threshold schism** (notes 02/13b): config.py default 300 s vs run_worker's P4-B
  30-min SSOT; session_engine requeues ≤10-min-old processing tasks that run_worker deliberately
  protects. Two daemons hold different staleness doctrines for the same table — the exact
  duplicate-processing bug P4-B was raised to prevent. Decide one SSOT constant, cite P4-B.
- **D-02 F-0028 caller drift** (note 10): `coaching_dialogue._get_ml_analysis_for_players`
  still calls the deleted `engine._get_ml_predictions` and the old `_synthesize_insights`
  signature — dies in a broad except, so "LIVE NEURAL NETWORK ANALYSIS" and the F3 session-ML
  injection never render, invisibly. Repair against the JEPA-adapter seam or retire with a
  tombstone.
- **D-03 LLM_COACH_MODEL staleness** (notes 10/14): LLMService is a process singleton whose
  model resolves once; the CoachScreen selector takes effect only after restart, and
  `is_available()` may silently family-fallback. Re-resolve on setting change or notify the
  singleton.
- **D-04 Tick-rate SSOT bypasses** (notes 03/05/13b): inline `header.get("tick_rate", 64.0)`
  in demo_loader (viewer path), demo_parser `_compute_event_kast`, trade_kill_detector — and the
  AST sweep in test_tick_rate_ssot cannot see positional `.get` defaults, so the ban is escaped
  structurally. Route through `resolve_tick_rate`; extend the sweep.
- **D-05 Three parallel maturity ladders** (note 11): console boot belief-confidence tiers,
  coach_manager maturity tiers, coaching_service JEPA ladder — same idea, three encodings.
  Define one maturity SSOT.
- **D-06 Duplicated model trees** (note 13b): two RAP trees (canonical: `experimental.rap_coach`,
  pinned by RAP-LTC-FIX) and two SkillLatentModels (R4 "0.0-is-real" fix only on the rap_coach
  copy); the legacy trees keep passing suites that mask canonicity. Also duplicated
  `_health_to_range`, two Steam locators (F6-11), rating-formula copies (acknowledged).
- **D-07 Coach Book v3 gaps** (note 09): `trigger_reembedding` checks dimension only, not
  CURRENT_VERSION (v2→v3 refresh with the same model never re-embeds); hybrid
  `_feature_matches_category` lacks the v3 categories (mid_round, retakes_post_plant,
  aim_and_duels).
- **D-08 UI-thread inference** (note 14): GhostEngine constructed and `predict_ghosts` run on
  the GUI thread (per-frame at up to 60 fps); Ollama model discovery on the main thread.
  Route through Workers like every other backend-heavy call.
- **D-09 Untrained WinProbabilityNN cascade (R9)** (notes 08/09/10): game-tree leaves ride
  heuristics+clamps, COPER stores delta_win_prob=0.0, insights carry the heuristic note.
  Dormancy is honest and documented everywhere — but training this model unlocks three systems
  at once; it is the highest-leverage single training task.
- **D-10 Stale artifacts** (notes 12/15/01): tools IT/PT READMEs describe fictional structures;
  ui_diagnostic checks retired `.qss` files (contradicts F-0005); db_health_diagnostic queries
  `playertickstate` in shards that use `matchtickstate`; migrate_db's second `__main__` is
  unreachable; debug_env probes Kivy; build_production.bat prefights kivymd; two build pipelines
  coexist (F-0041 marks build_tools canonical); score_responses advertises an unimplemented
  judge mode; headless_validator Phase 19 does not exist (numbering trap).
- **D-11 Convention-based destruction safety** (note 15): repair_* tools mutate the live DB
  with no dry-run; verify_all_safe's protection is a filename-prefix list; Sanitize_Project
  deletes the HLTV DB with no backup. Apply the W3 retrofit pattern (dry-run default +
  `--execute` + backup) across the family.
- **D-12 Watchlist** (notes 04/06/09/14): maintenance.prune_old_metadata deletes 30-day-old
  ticks the JEPA trainer may still want (verify callers before any schedule); geometric
  `enemies_visible` (no occlusion) both feeds feature 8 and gates PlayerKnowledge; experience
  extraction's thin `_infer_action`/thirds-grid position areas (move to callouts, rule 7);
  AppState write-path exceptions in the UI; the dormant telemetry client/server pair needs a
  contract test if ever wired (rule 4).

## 4. The AI roadmap (paper-grounded, invariant-filtered)

Ordered by leverage; each item names its paper evidence (note 16) and its guards.

- **R1 — Surprise channel at inference** (§3): serve the JEPA's latent prediction error as a
  zero-label "critical moment"/complexity signal — a second channel for ChronovisorScanner,
  surprise-ranked data curation, and honest "this round was unusual" observations. Gate like
  F-0029 (trained weights only); it is the model's own uncertainty, so it is anti-fabrication
  by construction.
- **R2 — Team-level representation** (§§1,7): players-as-channels. Either CECL-style
  multi-positive alignment of the 5 teammates' concurrent POV-tensor embeddings (sigmoid loss,
  imbalance-aware bias init; auxiliary, never primary) or an H-JEPA channel level chained into
  the existing temporal JEPA. Directly serves team-tactical awareness under NO-WALLHACK (inputs
  stay per-player POV). Mandatory: per-level collapse detectors + early-epoch loss gate.
- **R3 — Action/intent-conditioned predictor** (§2): extend g(z)→g(z,a) to unlock counterfactual
  coaching ("what if you had rotated?") with the theory's regret link. Actions come from the
  demo (real inputs), so no fabrication surface.
- **R4 — Callout-occupancy probes as evals** (§1): linear TLN/ELN-style probes over
  map_callouts occupancy from single-POV embeddings — an objective, leak-free measure of
  spatial awareness for every checkpoint; wire into eval_harness (which already has honest
  NOT_IMPLEMENTED slots).
- **R5 — Atomic action spans + cut-protected windows** (§5): rule-based detectors turning tick
  signals into bounded action spans (confidence, source, end-reason; grenade
  prepare/flight/effect as linked sub-events) enriching round_reconstructor and the model's
  action vocabulary; JEPA/RAP windows stop cutting mid-action (DP segmentation with
  pre-context). The codebase already synthesizes CS2 blind events from joint evidence — same
  technique, generalized.
- **R6 — Multi-horizon targets + latent atlas** (§4): apply "representation and predictive task
  share one scale hierarchy" to time (tick → engagement → phase); promote RankMe from passive
  telemetry to an active design input; extend EmbeddingProjector into a back-mappable tactical
  atlas (latent neighborhoods → named game situations) feeding the knowledge pipeline.
- **R7 — Entity-over-grid completion** (§6): finish the callout migration (experience bank
  position areas first), and keep HEE's dual-scoring/backtracking template on file for any
  future VLM-watches-renders capability.

## 5. Phase roadmap

- **Phase A — Stabilize (no new capability)**: burn down D-01..D-08 and D-10/D-11; add the
  missing contract tests (rule 4); unify SSOTs (D-05/D-06). Exit: defect register empty or
  explicitly deferred with reasons.
- **Phase B — Train & promote (existing architecture)**: R9 win-probability training (D-09),
  the supervised finetune that writes `head_trained=True` (TASKS#64 — arms the insight adapter),
  R1 surprise channel, R4 eval probes. Exit: no dormant-by-design component that a training run
  could awaken remains dormant without a decision.
- **Phase C — Extend (new architecture, one at a time)**: R2 team level, R3 action conditioning,
  R5 action spans/windows, R6 hierarchy+atlas — each behind a setting flag with byte-identical
  off behavior (the F1 pattern), each with its own collapse telemetry, each validated by R4
  probes before it may reach the coaching seam.

The fundamentals in §0 outrank everything in §§1–5. When a roadmap item and a Law conflict, the
Law wins; when the code and this document conflict, read the code, then fix whichever one is
lying — and log the incident ID.
