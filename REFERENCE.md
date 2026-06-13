# REFERENCE.md — Macena CS2 Analyzer

Static reference for architecture, invariants, constants, contracts, skills,
tests, and configs. Companion to `CLAUDE.md` (rules, principles), `AUDIT.md`
(findings/history), and `TASKS.md` (backlog).

> **Rule of update:** any change that touches a constant, invariant, or
> contract enumerated below requires a `migration_manifest_<ts>.md` document
> at the repo root describing the retraining or schema-migration plan, AND a
> simultaneous update to this file. The ContractGuard tests in
> `Programma_CS2_RENAN/tests/test_metadata_dim_contract.py` will fail CI on
> drift without these.

---

## 1. Architecture Overview

**Stack:** Python 3.10+ · PyTorch · PySide6/Qt · SQLite-WAL · Alembic ·
demoparser2 · BS4 + FlareSolverr (HLTV scraper).

**Package root:** `Programma_CS2_RENAN/`. Eight logical AI subsystems:

```
Programma_CS2_RENAN/
├── apps/qt_app/                   # Qt GUI (launch.sh entry point)
├── backend/
│   ├── coaching/                  # longitudinal engine, narratives
│   ├── nn/                        # JEPA, AdvancedCoachNN, RAP, EMA, Hopfield
│   │   ├── jepa_model.py          # JEPA + VL-JEPA architecture
│   │   ├── jepa_trainer.py        # EMA schedule, concept loss, P9-02 hard-stop
│   │   ├── jepa_train.py          # pretraining entry; seeded RNG; worker_init_fn
│   │   ├── model.py               # AdvancedCoachNN (LSTM + 3-expert top-2 MoE)
│   │   ├── ema.py                 # EMA shadow params (NN-16 .clone() invariant)
│   │   ├── early_stopping.py      # EarlyStopping + EmbeddingCollapseDetector
│   │   ├── maturity_observatory.py# 5-state maturity gate + concept-temp alarm
│   │   └── experimental/rap_coach/# 7-component RAP (Reasoning/Adaptation/Pedagogy)
│   ├── processing/
│   │   ├── feature_engineering/
│   │   │   └── vectorizer.py      # SOLE source of METADATA_DIM=25 + FEATURE_NAMES
│   │   └── validation/drift.py    # DriftMonitor (z=2.5; calibrated only at N≥260)
│   └── storage/
│       ├── database.py            # monolith + match_data manager
│       ├── db_models.py           # SQLModel tables (canonical schema)
│       ├── match_data_manager.py  # per-match shard DBs
│       └── alembic migrations     # see alembic/versions/
├── core/
│   ├── config.py                  # SETTINGS_PATH, CORE_DB_DIR, get_setting/set_setting
│   └── integrity_manifest.json    # generated; covered by pre-commit hook
├── observability/
│   ├── logger_setup.py            # CS2_LOG_LEVEL env override; propagate=False
│   ├── label_source_monitor.py    # G-01 label_source telemetry (PRE-2)
│   ├── exceptions.py
│   └── error_codes.py
└── tests/                         # pytest target; in-tree; ContractGuard etc.
```

Top-level helpers: `console.py` (CLI), `goliath.py` (super-tool), `batch_ingest.py`
(parallel pro-demo ingest), `run_full_training_cycle.py`, `tools/headless_validator.py`
(MANDATORY post-task), `tools/wipe_for_reingest_v4.py` (one-shot DB rebuild).

---

## 2. The 25-Dim Metadata Contract (P-X-01) — Source of Truth

**File:** `Programma_CS2_RENAN/backend/processing/feature_engineering/vectorizer.py`
**Constants:**
- `METADATA_DIM = 25` (line 32)
- `FEATURE_NAMES: tuple` (lines 151-177) — the canonical 25-position naming
- Built-in import-time `assert len(FEATURE_NAMES) == METADATA_DIM` (line 178)

**Index map (load-bearing — re-ordering breaks every checkpoint):**

| idx | name             | idx | name              |
|-----|------------------|-----|-------------------|
| 0   | health           | 13  | view_yaw_cos      |
| 1   | armor            | 14  | view_pitch        |
| 2   | has_helmet       | 15  | z_penalty         |
| 3   | has_defuser      | 16  | kast_estimate     |
| 4   | equipment_value  | **17**  | **map_id**    |
| 5   | is_crouching     | 18  | round_phase       |
| 6   | is_scoped        | 19  | weapon_class      |
| 7   | is_blinded       | 20  | time_in_round     |
| 8   | enemies_visible  | 21  | bomb_planted      |
| 9   | pos_x            | 22  | teammates_alive   |
| 10  | pos_y            | 23  | enemies_alive     |
| 11  | pos_z            | 24  | team_economy      |
| 12  | view_yaw_sin     |     |                   |

**`map_id` at index 17** is consumed by Pillar III's per-axis position loss
(`σ_z(map_id) · MSE(Δz)` per `CS2_Coach_Modernization_Report.pdf §5.3, §8.4`)
and by per-map specialization (`Supplement_N260 §3.1b`). Moving it is a
structural break.

**ContractGuard:** `Programma_CS2_RENAN/tests/test_metadata_dim_contract.py`
fails CI on any drift in the value, length, or order. A deliberate change
requires updating EXPECTED_FEATURE_NAMES in that file plus a migration
manifest. **This is the binding contract** between the feature pipeline and
every neural network input layer.

---

## 3. Critical Invariants

Violation of any of these is silent corruption — verify on every change to
the cited file.

| ID | Invariant | File:Line | Action on change |
|---|---|---|---|
| **P-X-01** | `METADATA_DIM=25`; `FEATURE_NAMES` length and order | `vectorizer.py:32, 151-177` | Migration manifest + retraining + ContractGuard update |
| **P-RSB-03** | `round_won` excluded from training features (label leakage) | `vectorizer.py` (FEATURE_NAMES — `round_won` is NOT present) | Re-derive feature schema before adding |
| **NN-MEM-01** | Hopfield bypass until ≥2 forward passes | `experimental/rap_coach/memory.py:111` (counter `_training_forward_count`), gated at `:175-180` | Coordinate with Pillar II self-correction loop (Refinement passes do NOT count today) |
| **NN-16** | EMA `apply_shadow()` must `.clone()` shadows; `restore()` must `.clone()` backups | `ema.py:79, 90` (verified 2026-06-13) | Any aliasing reintroduces the 2026-03 silent-share regression |
| **NN-JM-04** | Target encoder `requires_grad=False` during EMA | `jepa_trainer.py:51-52` (loop sets `p.requires_grad=False` for `target_encoder.*`) | Reverting causes target/context divergence |
| **DS-12** | `MIN_DEMO_SIZE = 10 MB` | `demo_format_adapter.py:49` | Increase only with empirical evidence on demo distribution |
| **P-VEC-02 / P3-A** | NaN/Inf clamp + `>5%` batch fail → `DataQualityError` | `vectorizer.py` (`_nan_inf_clamp_count` at :145, threading lock at :146) | Tightening threshold requires re-baselining batch-quality dashboard |
| **P9-02** | Embedding variance < 0.01 over 2 consecutive validation epochs aborts training | `early_stopping.py:EmbeddingCollapseDetector`; wired in `jepa_trainer.py:train_epoch` | Threshold/patience changes require re-validation of "healthy" baseline |
| **G-01** | Concept labels via RoundStats outcomes only; heuristic fallback hard-gated | `jepa_trainer.py:335-416` | `LabelSourceMonitor` alarms above 1% SKIPPED rate |
| **DET-01** | `set_global_seed(42)` before every training entry | `backend/nn/config.py:16-39`; called in `jepa_train.py:290`, `:298`, `:542-544`; `train.py:28, 79`; `win_probability_trainer.py:53` | Adding a new entry point requires a seed call before any RNG draw |
| **REPR-01** | EMA cosine schedule rehydrates `_ema_step` / `_ema_total_steps` from saved checkpoint | `jepa_trainer.py:106-107` (load from model attrs) | Skipping rehydration restarts τ at 0.996, breaks fine-tuning |

---

## 4. Phase 0 Hygiene Gates (April 2026)

Per `CS2_Coach_Modernization_Report.pdf §9` and `CS2_Coach_Supplement_N260.pdf §5.1`,
the following are blocking for the modernization roadmap. All landed
2026-04-25:

| Gate | Status | Implementation | Test |
|---|---|---|---|
| **F3-25** non-seeded NumPy RNG | FIXED (pre-existing) | `np.random.default_rng(seed)` + `worker_init_fn` in `jepa_train.py:64-100, 297-298, 325-326` | `tests/test_jepa_training_pipeline.py` |
| **F3-08** `np.tile` identity-op fallback | NEVER PRESENT (false alarm) | `_load_tick_sequence` returns empty array on undersize; `extract_batch` is the real path | n/a |
| **G-01** RoundStats outcome labelling | FIXED + telemetry added (PRE-2) | `jepa_trainer.py:335-416` hard-gate; `LabelSourceMonitor` sliding-window alarm at 1%/5min | `tests/test_label_source_monitor.py` |
| **P9-02** embedding-variance hard-stop | FIXED (PRE-3) | `EmbeddingCollapseDetector` (threshold=0.01, patience=2 consecutive epochs) | `tests/test_embedding_collapse_detector.py` |
| **§8.3** concept_temperature saturation alarm | FIXED (PRE-6) | `MaturityObservatory._update_concept_temperature_saturation` (5% band, 10-epoch patience) | `tests/test_concept_temperature_saturation.py` |
| **METADATA_DIM=25 ContractGuard** | FIXED (PRE-5) | `tests/test_metadata_dim_contract.py` pins value, length, order, and map_id index | self |

---

## 5. Storage Architecture

**Two-tier storage. Three databases.**

| Database | Path | Purpose | Schema source |
|---|---|---|---|
| **Monolith** | `Programma_CS2_RENAN/backend/storage/database.db` | tick states, match stats, round stats, ingestion tasks, coaching insights, user state | `db_models.py` + Alembic migrations |
| **HLTV metadata** | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | scraped HLTV teams, players, ratings | `SQLModel.metadata.create_all()` (TASKS#47 — bring under alembic) |
| **Per-match shards** | `<PRO_DEMO_PATH>/match_data/match_{id}.db` | tick-level rich features per match (Tier 3) | `match_data_manager.py:_MATCH_DB_MIGRATIONS` |

**Singletons (mandatory):** `get_db_manager()`, `get_hltv_db_manager()`,
`match_manager.get_engine(match_id)`. **Never instantiate `DatabaseManager` /
`HLTVDatabaseManager` directly.**

**Settings file:** `Programma_CS2_RENAN/user_settings.json` (gitignored).
Read via `get_setting(key, default)`; write via `save_user_setting(key, value)`
(atomic temp+rename, threading lock).

---

## 6. Global Constants & Defaults

| Constant | Value | File:Line | Notes |
|---|---|---|---|
| `GLOBAL_SEED` | 42 | `backend/nn/config.py` (set_global_seed default) | `set_global_seed(42)` before every training entry |
| `METADATA_DIM` | 25 | `vectorizer.py:32` | sole source of truth — see §2 |
| `MIN_DEMO_SIZE` | 10 MB | `demo_format_adapter.py:49` | ingestion rejects undersized demos (DS-12) |
| `EMA τ_base` | 0.996 | `jepa_trainer.py:102` (`self._ema_base_momentum`) | cosine schedule to 1.0 over `_ema_total_steps` |
| `InfoNCE τ` | **learnable**; init `log(0.07)` | `jepa_model.py:151` (`nn.Parameter`); clamped `[0.01, 1.0]` at `jepa_trainer.py:218, :488` | Radford et al. 2021 (CLIP); P2-4 init adjustment deferred |
| `Embedding-collapse threshold` | 0.01 / 2 consecutive epochs | `early_stopping.py: EmbeddingCollapseDetector` | P9-02 |
| `concept_temperature` | clamped to [0.01, 1.0] | `jepa_model.py:151` (same param); `jepa_trainer.py:218, :488` (clamp sites) | saturation alarm at 5%/10 epochs (PRE-6) |
| `label_source alarm` | 1% / 5-min sliding window | `observability/label_source_monitor.py` | G-01 telemetry (PRE-2) |
| `BATCH_SIZE` (JEPA) | 16 | `jepa_train.py:383` (default arg) | RAP uses batch_size=1 (`training_config.py:22`) |
| `latent_dim` | 256 | `jepa_model.py:43, :75` (encoder + predictor defaults) | reverts to 256 at N≥260 (was 128 at N=11) per Supplement |
| `MoCo queue size` | 4096 | `jepa_model.py:154` (`_MOCO_QUEUE_SIZE`) | 64 sampled per batch (`:266`) |
| `VICReg λ_var / λ_cov / weight` | 25.0 / 1.0 / 0.01 | `jepa_trainer.py:222-223` | regularization on pred embeddings |
| `MoE load-balance aux` | 0.01 × num_experts | `jepa_model.py:243` | penalizes unbalanced routing |
| `_MIN_TRAINING_SAMPLES` | 100 | `training_orchestrator.py:174` | hard gate; fewer → abort |
| `P3-C fallback-rate gates` | 10% warn / 30% abort | `training_orchestrator.py:269-274` | aggregate zero-tensor fallback rate |

---

## 7. Skills — When to Trigger (`.claude/skills/`)

**Mandatory:**
- `/validate` — post-task headless regression check. Equivalent to `python tools/headless_validator.py`. Required after every code-modification turn.
- `/pre-commit` — runs all pre-commit hooks with detailed pass/fail.

**Path-triggered (auto-recommend on touch):**

| Path | Skill |
|---|---|
| `backend/storage/`, `alembic/` | `/db-review` |
| `backend/nn/`, training entries | `/ml-check` |
| `backend/nn/jepa_*` | `/jepa-audit` |
| `backend/coaching/longitudinal_engine.py`, `session_engine.py` | `/state-audit` |
| `apps/qt_app/`, kivy code | `/frontend-ux-review` |
| External I/O (HLTV, FlareSolverr) | `/resilience-check` |
| Auth, secrets, keyring code | `/security-scan` |
| Service boundaries, REST | `/api-contract-review` |

**Multi-file:** `/scope-guard`, `/change-impact`, `/design-review`,
`/complexity-check`, `/correctness-check`, `/observability-audit`,
`/data-lifecycle-review`, `/dependency-audit`, `/devsecops-gate`,
`/deep-audit`.

---

## 8. Tests — Where to Look

| Path | Coverage |
|---|---|
| `tests/test_metadata_dim_contract.py` | METADATA_DIM=25 ContractGuard (PRE-5) |
| `tests/test_embedding_collapse_detector.py` | P9-02 hard-stop logic (PRE-3) |
| `tests/test_label_source_monitor.py` | G-01 telemetry sliding window (PRE-2) |
| `tests/test_concept_temperature_saturation.py` | concept_temperature alarm (PRE-6) |
| `tests/test_jepa_model.py` | JEPA architecture, forward passes, sparse MoE |
| `tests/test_jepa_training_pipeline.py` | dataset reproducibility, EMA schedule, finetune |
| `tests/test_ema_hopfield_drift_invariants.py` | NN-16 backup aliasing, NN-MEM-01 bypass, drift |
| `tests/test_data_pipeline_contracts.py` | feature pipeline shape contracts |

**Run patterns:**
- All scoped: `pytest Programma_CS2_RENAN/tests/ tests/ -m "not slow" --tb=short`
- Single: `pytest path/to/file.py::Class::test_name`
- Integration (touches DB): `CS2_INTEGRATION_TESTS=1 pytest -m integration`
- CI-bypass venv-guard: `CI=1 pytest ...`

**Determinism probe** (any change to training): three seeds, val/train ratio
variance < 0.05.

---

## 9. Configs / Env Vars

| Variable | Effect | Default |
|---|---|---|
| `CS2_LOG_LEVEL` | logger root level (`DEBUG / INFO / WARNING / ERROR`) | INFO |
| `CS2_INTEGRATION_TESTS` | enable `@pytest.mark.integration` (DB required) | unset → skipped |
| `CS2_NONDETERMINISTIC` | bypass `torch.use_deterministic_algorithms(True)` | unset → strict |
| `CI` | bypass venv-guard checks in some entrypoints | unset |
| `KIVY_NO_ARGS`, `KIVY_LOG_LEVEL` | suppress Kivy noise during ingest | set by `batch_ingest.py:19-20` |
| `QT_QUICK_BACKEND=software` | force software rendering for Qt charts (Linux GPU drivers segfault) | set by `launch.sh:26` |

---

## 10. Open Documentation Debt

- `hltv_metadata.db` not yet under Alembic (TASKS#47 — GAP-14).
- This file (`REFERENCE.md`) was missing prior to 2026-04-25; tracked as
  TASKS#46 (GAP-13). Created during PRE-5/P0-5 work.
- Per-match shard archival strategy not yet documented; planned via SQLite
  ATTACH consolidation before the per-match DB count crosses ~1000 instances
  (Supplement §3.2 Risk C).
- 14 arxiv JEPA/VL-JEPA papers in `docs/research/arxiv/` (added 2026-06-13);
  indexed by research dossier in the programme plan. Phase E8 links from README.

---

## 11. Cross-references

- **Principles & rules:** `CLAUDE.md` (project + user globals)
- **Audit trail / findings:** `AUDIT.md`
- **Backlog:** `TASKS.md`
- **Completion programme:** `~/.claude/plans/cs2-completion-2026-06-13/` (15 files; supersedes all earlier plan files)
- **Modernization reports:** `CS2_Coach_Modernization_Report.pdf`,
  `CS2_Coach_Supplement_N260.pdf` (gitignored — author's reference docs)
