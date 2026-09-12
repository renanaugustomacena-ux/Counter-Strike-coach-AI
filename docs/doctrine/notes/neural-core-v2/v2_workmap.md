# WORK MAP — CORREZIONE NUCLEO NEURALE, MILESTONE 1 (steps 0, 1, 1b, 2-3, 4)

Verification basis: tree at HEAD `50031cb` (branch `docs/refresh-2026-09-04`), 2026-09-11.
`git diff --stat 62cd2f1..HEAD` touches only README/docs files and root `tools/*.py` (four new `measure_*.py` +
`verify_math_claims.py`); `Programma_CS2_RENAN/backend`, `core`, `run_ingestion.py` and `run_full_training_cycle.py`
are byte-identical to 62cd2f1, so Parte III's line citations were checked against live code (drifts noted per entry).
Documents read in full: CORREZIONE_NUCLEO_NEURALE_PARTE_III.md (all 592 lines); CORREZIONE_NUCLEO_NEURALE.md
§6-§9 + App. A.1/A.2/A.5/A.8/E/G.

```
================================================================================
WORK MAP — CORREZIONE NUCLEO NEURALE, MILESTONE 1 (steps 0, 1, 1b, 2-3, 4)
Basis: HEAD 50031cb; docs read in full: PARTE_III (all), PARTE_I §6-§9 + App. A.1/A.2/A.5/A.8/E/G
Repo root R = /media/renan/WORK_RECOVERED1/PROIECT/Counter-Strike-coach-AI
Package  P = R/Programma_CS2_RENAN
================================================================================

LAYOUT / ENVIRONMENT FACTS THAT OVERRIDE THE DOCS' PATH CONVENTION
- Parte III says paths are relative to Programma_CS2_RENAN/ "salvo dove indicato", but:
  * tools/verify_math_claims.py (the model for every read-only tool) is R/tools/verify_math_claims.py (root),
    not P/tools/. P/tools/ exists too (db_inspector.py, Ultimate_ML_Coach_Debugger.py, ...). All four new
    owner tools (measure_*.py) are in R/tools/ and import `from tools.verify_math_claims import ...`.
  * run_full_training_cycle.py is R/run_full_training_cycle.py (root). run_ingestion.py is P/run_ingestion.py.
  * Tests live in P/tests/ (185 entries). R/tests/ holds only conftest.py + forensics/. pytest.ini testpaths =
    "tests Programma_CS2_RENAN/tests"; CI runs `python -m pytest Programma_CS2_RENAN/tests/ tests/`.
    pytest.ini sets a GLOBAL per-test timeout of 30 s (pytest-timeout) and markers slow/integration/unit.
  * Neither R/configs/ nor P/configs/ exists. P/tests/fixtures/ does not exist (P/tests/data/ exists, empty).
  * R/docs/benchmarks/ does not exist. R/docs/research/ holds the five 2026-09-05 JSON measurements.
  * $DATA is not defined anywhere in the repo (grep over *.py/*.sh/*.md). core/config.py has
    DATA_DIR = <USER_DATA_ROOT>/data (P/core/config.py:388; USER_DATA_ROOT = BRAIN_DATA_ROOT | CUSTOM_STORAGE_PATH | BASE_DIR, :365-369).
- Venv: R/.venv (P/.venv absent). torch 2.13.0+rocm10.0.0, numpy 2.4.3, pandas 2.3.3, scipy 1.17.1,
  scikit-learn 1.8.0, tensorboard 2.21.0, safetensors 0.8.0, faiss-cpu 1.13.2.
  safetensors is only a TRANSITIVE pin (R/requirements-lock.txt:111); absent from requirements.in / requirements.txt.
- Monolith: P/backend/storage/database.db -> /media/renan/New Volume7/AI/database.db (readlink -f). Read-only
  access pattern already in place: R/tools/verify_math_claims.py:109-114 open_ro() (os.path.realpath + ?mode=ro + PRAGMA query_only=1).
- Checkpoints: P/models/global/{jepa_brain.pt, jepa_brain_latest.pt, rap_coach.pt, rap_coach_latest.pt} (+ .meta.json) and
  P/models/global/archive_pre_rebuild_2026-09-01/ (jepa_brain.pt used as ARCHIVE by verify_math_claims.py:76).
- OPERATIONAL WARNING (from the owner's memory note 2026-09-11, not from the docs): a full legacy JEPA+RAP run
  (`./train.sh --patience 30`, PID 1481729) was started 2026-09-11 04:17 local and is expected to run for days.
  P/user_settings.json has USE_RAP_MODEL: true. Step 0's acceptance ("no new jepa_brain*.pt / rap_coach*.pt
  until step 4 passes") is being violated by that run; nothing in this map touches it — see Ambiguity A-1.

--------------------------------------------------------------------------------
0. PRE-FLIGHT (no code)
--------------------------------------------------------------------------------
0.1  Decide the fate of PID 1481729 (legacy run) before merging Step 0 — the freeze (entry 1) does not stop a
     process already past __init__; it only blocks new constructions. Do not kill without the owner's word.
0.2  Branch: Parte III §0.1 wants feat/neural-core-v2 from main AFTER docs/refresh-2026-09-04 is merged.
     Today's branch still has uncommitted work (CORREZIONE_*.md, tools/measure_*.py, README_IT/PT edits).
0.3  Re-verify D9 read-only before entry 3/10: `SELECT dataset_split, COUNT(*) FROM playermatchstats GROUP BY 1`
     via open_ro(). The 2026-09-05 fact (1031 rows UNASSIGNED) may be stale: run_full_training_cycle.py:217 calls
     manager.assign_dataset_splits() unconditionally and the 2026-09-11 run went through it.
0.4  Corpus today = 226 matches / 428.6 M ticks (memory 2026-09-11) vs 147.5 M ticks assumed in Parte III §3 —
     every size estimate in §3 is ~2.9x low (Ambiguity A-33).

--------------------------------------------------------------------------------
1. STEP 0 · §1.1  Freeze legacy training in TrainingOrchestrator.__init__
--------------------------------------------------------------------------------
Targets (all exist):
  P/backend/nn/training_orchestrator.py — class TrainingOrchestrator :24; __init__ :47-140 (doc cites 47-140: exact).
    model_type validation is the if/elif/else at :117-140: "jepa"/"vl-jepa" :117-123, "rap" :125-137 (gated by
    get_setting("USE_RAP_MODEL") at :128 -> ValueError), else ValueError("Unknown model type") :140.
    get_setting is imported function-locally (:74 and :126: `from Programma_CS2_RENAN.core.config import get_setting`).
  P/core/config.py — defaults dict inside load_user_settings() :183-245; "USE_JEPA_MODEL": False at :236 (exact);
    "USE_RAP_MODEL": False at :240; get_setting(key, default) :407-410. user_settings.json overrides defaults
    (SETTINGS_PATH :89). _SETTING_NAME_TO_GLOBAL (:529) is only for keys mirrored as module globals — not needed.
Change:
  (a) config.py: add "ALLOW_LEGACY_NEURAL_TRAINING": False next to :236.
  (b) training_orchestrator.py: after the :117-140 branch (or immediately before :117 — the doc says "dopo la
      validazione di model_type"; placing it AFTER :140 lets the rap branch's USE_RAP_MODEL ValueError keep
      precedence), insert the _LEGACY_TRAIN_TYPES = {"jepa","vl-jepa","rap","rap-lite"} check raising RuntimeError
      with the doc's message (verbatim in Parte III §1.1 lines 46-54).
      Note: "rap-lite" is never accepted by __init__ (only ModelFactory knows TYPE_RAP_LITE, factory.py:40), and
      "pov-rap" appears only in _checkpoint_extra_meta :470 — see A-4.
Tests required:
  - P/tests/test_training_orchestrator_logic.py::test_legacy_training_frozen_by_default (§1.1) — file exists
    (17 tests), test does not. Pattern to copy: :24-34 (patch get_device) and :48-65 (patch
    "Programma_CS2_RENAN.core.config.get_setting" with a side_effect lambda).
  - P/tests/test_legacy_frozen.py (§10 "Aggiungere", §11 row 0 command) — does not exist. The doc names BOTH
    locations for the same behaviour (A-3).
Blast radius (not mentioned by the doc): 19 existing constructions of TrainingOrchestrator(...) in
  test_training_orchestrator_logic.py (10), test_rap_training_dry_run.py (4), test_jepa_collapse_feed.py,
  test_probe_batch_wiring.py, test_training_abort_signal.py, test_training_loop_honesty.py,
  test_training_orchestrator_flows.py (1 each) will raise RuntimeError unless ALLOW_LEGACY_NEURAL_TRAINING is
  patched True; plus test_dry_run_checkpoint_integrity.py / test_tensorboard_integration.py go through
  run_full_training_cycle. Add an explicit override in those tests (or an autouse fixture in P/tests/conftest.py
  next to isolated_settings :416-444). Also coach_manager.run_jepa_pretraining :588-602 and run_rap_cycle :604-616
  catch ValueError -> warning and Exception -> app_logger.error (no re-raise): the console path will log
  "JEPA Training Failed" and continue — loud but not fatal (A-2).
Acceptance (§11 row 0): `pytest tests/test_legacy_frozen.py -q` green; construction with model_type="jepa" raises
  RuntimeError by default and does not raise with the setting True.
Depends on: nothing.

--------------------------------------------------------------------------------
2. STEP 0 · §1.2  run_full_training_cycle.py: no implicit default
--------------------------------------------------------------------------------
Targets (exist): R/run_full_training_cycle.py (289 lines). _build_parser :92-178; --model-type at :116-121
  (choices ["all","jepa","rap"], default "all"); main :181; manager.assign_dataset_splits() at :217; Phase-1 JEPA
  block :227-249; the `del orchestrator_jepa; gc.collect(); torch.cuda.empty_cache(); synchronize; mem_get_info`
  block is :242-249 (doc cites 242-247); Phase-2 RAP :251-264; exit(3) on aborted phases :269-274.
  R/train.sh passes `--model-type "$MODEL_TYPE"` (MODEL_TYPE default "all") and `--epochs "$EPOCHS"`.
Change: --model-type required=True, choices {"jepa_v2","coach_v2","jepa","rap","all"}; "all" = jepa_v2 -> coach_v2;
  remove :242-249; free GPU with model.cpu() after the checkpoint is saved.
  Constraints found: run_training() (training_orchestrator.py:524) returns bool, not the model, so "model.cpu()"
  needs a new handle (A-6); the jepa_v2/coach_v2 choices point at types that do not exist until entries 12-13 /
  step 6, and ModelFactory.get_model raises ValueError for them (factory.py:96-107) — selecting them must fail
  loudly until then (A-5); train.sh's "all" default will change meaning (its header §6.4 is step 5).
Tests required: none named by the doc. Existing coverage of the parser: P/tests/test_dry_run_checkpoint_integrity.py,
  P/tests/test_tensorboard_integration.py (both reference run_full_training_cycle / _build_parser) — re-run.
Acceptance: parser rejects a missing --model-type; "all" no longer schedules "rap".
Depends on: entry 1 (the setting) for the legacy choices to be usable at all; entries 12-13 for jepa_v2 to run.

--------------------------------------------------------------------------------
3. STEP 0 · §1.3  Splits assigned before any training; fail (not warn) on train_rows == 0
--------------------------------------------------------------------------------
Targets (exist): P/backend/nn/coach_manager.py — run_full_cycle :293 (doc: exact) with self.assign_dataset_splits()
  at :320 (exact); run_jepa_pretraining :588-602 (doc: exact) — constructs TrainingOrchestrator directly, no
  assign call, swallows exceptions; assign_dataset_splits :397-~510 (doc 397-510: exact; temporal_assign :433-464,
  eligibility gates from _build_eligibility_gates :343-396, OI-2 warning :470-490).
  P/backend/nn/data_quality.py — run_pre_training_quality_check :57-168; "No demos assigned to 'train' split"
  issue + passed=False at :159-161. Called from training_orchestrator.run_training :529-537, which already
  RETURNS False (F-0043) on a failed report; run_full_training_cycle.py then exits 3 (:269-274).
  `run_jepa_v2_pretraining` does not exist anywhere.
Change: call assign_dataset_splits() at the top of run_jepa_pretraining (and in the future v2 entry point); make a
  failed quality gate fatal on the coach_manager path (today run_jepa_pretraining ignores the bool; the CLI path
  already exits 3). Note the CLI already assigns at run_full_training_cycle.py:217 — the doc's §1.3 gap exists
  only on the console/coach_manager path (A-7).
  Operational: assign_dataset_splits WRITES the monolith (session.commit :468) — run only with ingestion idle.
Tests required: none named. Existing: P/tests/test_coach_manager_flows.py (exists).
Acceptance: after assignment, train_rows > 0 or training aborts with non-zero status on both paths.
Depends on: entry 0.3 (state check); nothing in code.

--------------------------------------------------------------------------------
4. STEP 1 · §2.1  Typed schema cs2_v2
--------------------------------------------------------------------------------
Target: NEW P/backend/processing/feature_engineering/schema_v2.py (directory exists: base_features.py,
  vectorizer.py, kast.py, rating.py, role_features.py, __init__.py — __init__ uses a lazy __getattr__ with
  __all__ = FEATURE_NAMES/METADATA_DIM/...; import the new module by full path).
Change: the dataclasses Kind / Field / FeatureSchema and the CS2_V2 constant exactly as Parte III §2.1 lines 77-138
  (24 fields: 21 numeric, 3 categorical; fingerprint = sha256 of canonical JSON of fields).
  Source columns verified on PlayerTickState (P/backend/storage/db_models.py:161-218): health :193, armor :194,
  is_crouching :195, is_scoped :196, has_helmet :197, has_defuser :198, active_weapon :199, equipment_value :200,
  enemies_visible :202, is_blinded :203, pos_x/y/z :187-189, view_x/view_y :190-191, round_number :212,
  time_in_round :213, bomb_planted :214, teammates_alive :215, enemies_alive :216, team_economy :217, map_name :218,
  tick :183, player_name :184, demo_name :185, steamid :209. `side` is NOT a tick column: roundstats.side
  (db_models.py:806, default "unknown"; measured 24,285 T / 24,285 CT, 0 null, constant per (demo,round,player)).
  Map vocab (9 + "other") matches core/spatial_data.py's known maps (de_mirage, inferno, dust2, overpass, ancient,
  anubis, train, nuke, vertigo; :82-98, :129-137). Weapon vocab: see A-10.
  Rule (e): v1 divisors live in HeuristicConfig (base_features.py:34-45: health_max 100, armor_max 100,
  equipment_value_max 10000, enemies_visible_max 5, pos_xy_extent 4096, pos_z_extent 1024, pitch_max 90) and as
  literals in _fill_context_features (vectorizer.py:417-452: /115.0 :430, /4.0 :440, /5.0 :445, /16000.0 :450 —
  doc cites 409-441; drift +8..+11).
Tests required: P/tests/test_schema_v2.py (§10) — does not exist: fingerprint stable; extract_v2 in range;
  remap without loss on 100 k ticks; vocab fallback logged.
Acceptance (§11 row 1): `pytest tests/test_schema_v2.py tests/test_naming.py -q`.
Depends on: nothing. Blocks: 5, 6, 7, 10, 12.
Ambiguities: A-8 (configs/schema_cs2_v2.json + nn/feature_schema.py in Parte I vs schema_v2.py in Parte III),
  A-9 (no clip/valid_range in Field although v1 clips), A-10 (weapon vocab), A-11 (map vocab), A-12 (`Field` name).

--------------------------------------------------------------------------------
5. STEP 1 · §2.5  D4 / D5 / D6 residuals
--------------------------------------------------------------------------------
D4 — P/backend/processing/feature_engineering/base_features.py HeuristicConfig :18-58 (doc: exact). Add
  time_in_round_max=115.0, teammates_alive_max=4.0, enemies_alive_max=5.0, team_economy_max=16000.0 and make
  _fill_context_features (vectorizer.py:417-452) read them (it currently takes no cfg argument — signature change:
  `_fill_context_features(vec, get_val, context)` -> needs cfg). The sidecar already records
  asdict(load_learned_heuristics()) (persistence.py:141), so the four new fields land in v1 sidecars automatically.
  Test: extend P/tests/test_metadata_dim_contract.py (:64-114, 5 tests) per Parte I step 2.
D5 — coach_manager.py: TRAINING_FEATURES :55-92 and MATCH_AGGREGATE_FEATURES :98-131 both assert len == METADATA_DIM
  (:91-92, :133-137). Add MATCH_AGGREGATE_DIM = len(MATCH_AGGREGATE_FEATURES) and drop the METADATA_DIM coupling for
  the aggregate list. factory.get_model :44-113 passes METADATA_DIM as input_dim/metadata_dim for jepa/vl-jepa/rap/
  rap-lite/default; the jepa_v2 branch (entry 13) reads dims from CS2_V2. nn/config.py INPUT_DIM = METADATA_DIM (:183-185).
D6 — vectorizer.py global state: _z_penalty_warned :31, _batch_clamp_local = threading.local() :153,
  _single_clamp_window deque :184, _reset_quality_gate_state_for_tests :188, class-level configure() :595 /
  update_heuristics() :606, _finalize_vector's clamp counters :453-~550. v2 path = FeatureExtractorV2(schema,
  quality_policy) instance with its own stats; v1 untouched.
Tests: none named beyond test_metadata_dim_contract extension.
Depends on: 4.

--------------------------------------------------------------------------------
6. STEP 1 · §2.2  extract_v2 / extract_batch_v2 / remap_v1_to_v2
--------------------------------------------------------------------------------
Target (exists): P/backend/processing/feature_engineering/vectorizer.py (778 lines). extract :615-677
  (signature (tick_data, map_name=None, context=None, _config_override=None); auto-resolves map_name from
  tick_data :660-665; fillers called :668-675); extract_batch :679-750 (config snapshot R4-14-03 at :700;
  _batch_clamp_local bookkeeping :720-737). Fillers: _fill_vitals_movement :280-305, _fill_awareness_position_view
  :308-333 (min(...,1.0) on enemies_visible, np.clip on pos), _fill_z_penalty :336-353 (core.spatial_data.compute_z_penalty),
  _fill_round_metadata :356-382 (stays v1-only), _fill_weapon_class :384-414, _fill_context_features :417-452.
  FEATURE_NAMES :240-266 — v1 indices for the 21 numerics are [0..15, 20..24] (16 kast_estimate, 17 map_id,
  18 round_phase, 19 weapon_class): the doc's remap indices are correct.
Change: add extract_v2(tick_data, map_name=None, side=None, schema=CS2_V2) -> (x_num f32[21], x_cat i64[3]),
  extract_batch_v2 (vectorised, config snapshot like :700), remap_v1_to_v2(x25, map_name, active_weapon, side).
  Categorical fallbacks other/none/unknown must be LOGGED (never silent). Do not touch extract/extract_batch
  (legacy checkpoints + R/tools/verify_math_claims.py:198 depend on them).
Tests: test_schema_v2.py: `extract_v2(...)[0] == remap_v1_to_v2(extract(...))[0]` within 1e-6 on 100,000 real
  ticks — needs DB or an exported fixture (A-13).
Depends on: 4, 5 (cfg-driven divisors).

--------------------------------------------------------------------------------
7. STEP 1 · §2.3  Sidecar v2 + SchemaMismatchError
--------------------------------------------------------------------------------
Target (exists): P/backend/nn/persistence.py (309 lines). _META_SCHEMA_VERSION = "v1" at :21 (doc: 22);
  StaleCheckpointError(RuntimeError) :24; _sidecar_path :118; _build_current_meta :123-142 (writes schema_version,
  metadata_dim, feature_names, heuristic_config); _validate_loaded_meta :145-182 (doc 146-182: exact) — today it
  REJECTS any schema_version != "v1" (:158-163) and then checks metadata_dim == 25 (:164-168) and feature_names
  (:170-181); save_nn(model, version, user_id=None, extra_meta=None) :184-222 puts extra_meta under meta["extra"]
  (:207-208); load_nn(version, model, user_id=None) :224-309 validates the sidecar then load_state_dict(strict=True).
  get_model_path -> MODELS_DIR/global/<version>.pt (:32-39) — "jepa_v2_encoder" fits.
Change: add SchemaMismatchError(StaleCheckpointError); branch _validate_loaded_meta on schema_version: "v1" ->
  current checks; "v2" -> compare schema_fingerprint with CS2_V2.fingerprint() (mismatch -> SchemaMismatchError),
  numeric_dim == 21, categorical_vocab_sizes == [10, 8, 3]; v2 save path writes {"schema_version":"v2",
  "schema_id":"cs2_v2","schema_fingerprint":...,"numeric_dim":21,"categorical_vocab_sizes":[10,8,3]}.
  Where these keys live (top-level vs meta["extra"]) is ambiguous (A-14). Parte I step 2 additionally wants
  recipe, git_sha, created_utc.
Tests: P/tests/test_persistence_stale_checkpoint.py exists (fixtures model_dir/small_model/large_model :24-41;
  10 tests) — add test_v2_fingerprint_mismatch_raises (§2.3, §10 "Modificare").
Acceptance (Parte I step 2): a checkpoint with a different fingerprint is refused with the named error.
Depends on: 4.

--------------------------------------------------------------------------------
8. STEP 1 · §2.4  D8 — normalize_player_name and the joins
--------------------------------------------------------------------------------
Targets:
  NEW P/backend/storage/naming.py (does not exist; P/backend/storage/ has database.py, db_models.py, models/, ...).
  P/run_ingestion.py (1738 lines): (b1) PlayerTickState write — _build_legacy_tick_dataframe :1451-~1530 passes the
    raw name at :1469 (`"player_name": df_legacy_source["player_name"]`), bulk to_sql("playertickstate") at :1700
    (doc: 1701). (b2) PlayerMatchStats write — _save_player_stats :542, p_name = row["player_name"] :544,
    PlayerMatchStats(player_name=p_name, ...) :588-594, db_manager.upsert :595. The doc's ":120" is the TRANSIENT
    PlayerMatchStats built in run_ml_pipeline :108-120 for skill scoring — not a DB write (A-16).
    :797 (`_df_state["_pname"] = ...str.strip().str.lower()`) is the event-state index inside the ingestion class,
    not the roundstats write; roundstats names are lowercased in P/backend/processing/round_stats_builder.py
    (:278-282, :389-390, :413, :444-445, :480-481, :614-615, :652-653, :901); RoundStats insert at :1005 (doc: exact),
    PMS enrichment join uses func.lower(PlayerMatchStats.player_name) == player_key at :1012 (lower, no trim).
  Joins (c): training_orchestrator._fetch_round_stats_for_batch :1537-1606 — exact equality
    `RoundStats.player_name == player` at :1567. coach_manager._fetch_round_stats_for_batch DOES NOT EXIST (only
    RoundStats use in coach_manager is the round-count gate :331-341) (A-17). R/tools/verify_math_claims.py
    fetch_ticks :154-163 already resolves the stored spelling via resolve_stored_name :141-151 (casefold match on
    `SELECT DISTINCT player_name ... WHERE demo_name=?`) so the tick query keeps using ix_pts_player_demo
    (db_models.py:164-166, columns (player_name, demo_name)); a `lower(trim(player_name)) = ?` predicate in SQL
    cannot use that index (A-18). Same-source joins PTS<->PMS by raw name exist in coach_manager._fetch_jepa_windows
    :873 and _fetch_rap_windows :989 — a migration that normalizes only one table breaks them (A-19).
Measured (R/docs/research/name_join_coverage_2026-09-05.json, all 225 demos, 2,250 (demo,player) pairs): exact
  match coverage 0.538 (1,211/2,250); strip().lower() coverage 1.000 of roundstats names / 0.9991 of PMS names,
  every demo fully covered; NFKC+casefold identical to strip().lower() (0 names differ; lower_ne_casefold = 0);
  67 PMS names change under strip().lower(). So the §2.4 / §10 "≥ 95 %" threshold is satisfiable.
Change: normalize_player_name(s) = s.strip().casefold() in naming.py; use it at (b1) :1469 and (b2) :544/:588 for
  new ingestions; use it in every label<->tick join (entry 10's export, :1567, verify_math_claims.fetch_ticks).
Migration (approval-gated, ingestion idle, backup): the two UPDATE statements of §2.4; size first with
  `SELECT count(*) FROM playertickstate WHERE player_name <> lower(trim(player_name))` (full scan; SQLite lower() is
  ASCII-only — A-15).
Tests: P/tests/test_naming.py (does not exist): idempotence, spaces, case, Unicode casefold; integration test
  "every roundstats.player_name has ≥ 1 playertickstate row after normalization" — no test DB with real names
  exists; the in-memory sqlite fixture pattern is P/tests/test_jepa_window_fetcher.py:38-66 (seeded_db).
  §10 "Modificare": P/tests/test_jepa_window_fetcher.py and P/tests/test_rap_window_fetcher.py (both exist) must
  use normalized names.
Depends on: nothing (blocks 10).

--------------------------------------------------------------------------------
9. STEP 1 · §2.4  D8 data migration on the monolith (OPTIONAL for milestone 1; approval required)
--------------------------------------------------------------------------------
§11 row 1 says the migration is optional because the export can normalize at the join. If executed: both UPDATEs
in one transaction (A-19), with the DB otherwise idle, after a backup, then re-run
R/tools/measure_name_join_coverage.py (exists, read-only) as the acceptance probe. Requires a paused/finished
PID 1481729 run (it writes PMS via assign_dataset_splits).

--------------------------------------------------------------------------------
10. STEP 1b · §3  tools/export_episodes.py
--------------------------------------------------------------------------------
Target: NEW R/tools/export_episodes.py (by analogy with R/tools/verify_math_claims.py — A-20).
Reuse (all exist, read-only): open_ro() (verify_math_claims.py:109-114), PTS_COLS :78-102 (23 columns: tick,
  round_number, time_in_round + all 21 numeric sources + map_name + active_weapon), resolve_stored_name :141-151,
  fetch_ticks :154-163 (`... ORDER BY tick LIMIT ?`), select_pairs :116; measure_episode_lengths.py:
  select_demo_players :86-107, fetch_thr :109-129, dedupe_ticks :131-139, split_episodes(tick, rnd, tol) :192-201
  (tol=1 strict / tol=7 bridged), _git_sha :342; measure_event_horizons.py: round_labels_for_pair :153-167
  (round_won, opening_death, opening_kill, kast per round), split_episodes :111, episode_tokens :127.
Query: per demo (from roundstats), per normalized player: `SELECT <PTS_COLS> FROM playertickstate WHERE demo_name=?
  AND player_name=? ORDER BY tick` with the stored spelling resolved first (index ix_pts_player_demo); segment in
  Python on round_number and tick[i+1]-tick[i]==1; keep episodes ≥ 64 ticks.
Labels: roundstats columns verified (db_models.py:779-840): round_won :835 (bool), kills :809, deaths :810,
  kast :837 (bool), round_rating :840 (Optional[float] — may be NULL, A-25), opening_kill :822, opening_death :823,
  side :806. Index ix_rs_demo_player (demo_name, player_name) :790.
Split: replicate assign_dataset_splits exactly — group PMS rows by _normalize_demo_name (coach_manager.py:50;
  WR-76: PMS.demo_name may carry the legacy "stem.dem_Player" suffix, :945), keep only rows passing the three
  eligibility gates (:343-396: shard complete via _get_completed_demo_names, ≥ MIN_COMPLETE_MAP_ROUNDS distinct
  rounds in roundstats, nonzero avg_kills/avg_adr), sort demos by (min match_date, demo key), cut at int(0.70·n)
  / int(0.85·n), pro and user separately (is_pro = 1 for all rows today -> user branch empty). Read
  PMS.dataset_split (db_models.py:77) if not UNASSIGNED; otherwise compute and write ONLY into the manifest.
  match_date_source (db_models.py:73; CHRONOLOGICAL_SOURCES = {filename_date, filename_year, hltv_event_date},
  P/backend/ingestion/match_date_resolver.py:41) -> OI-2 warning in the manifest.
Layout: one safetensors shard per demo at $DATA/cs2_v2/<split>/<demo_name>.safetensors with the tensors of the
  constants sheet (C-14); manifest.json per split (C-15). Profiles full / medium (default) / sample_2k (C-16).
  Actions per C-13.
Tests: P/tests/test_export_episodes.py (does not exist): episodes never cross a round; ticks consecutive;
  episode_offsets monotone; actions reconstruct raw_pos_view; labels present for ≥ 95 % of episodes; safetensors
  round-trip. Needs either the DB (mark integration/slow) or synthetic arrays + a tmp shard (A-28).
Acceptance (§11 row 1b): `PYTHONPATH=. .venv/bin/python tools/export_episodes.py --profile medium --out "$DATA/cs2_v2"`
  then `pytest tests/test_export_episodes.py -q`; manifest valid; labels ≥ 95 %; Parte I adds: counts consistent
  with the DB, no demo in two splits, remap test green, sample_2k in tests/fixtures/.
Depends on: 4, 6 (extract_v2), 8 (naming), 0.3 (split state). Add safetensors as a DIRECT pin in requirements.in /
  requirements.txt (A-34).
Ambiguities: A-20 ($DATA, tool location), A-21 (strict vs tolerance-7 episodes — measured: 80 % of strict episode
  breaks are 2-5-tick gaps), A-22 (round_number semantics, warm-up round 1, dead ticks), A-23 (x_cat i64 vs i32),
  A-24 (player table / hashed ids), A-25 (nullable round_rating), A-26 (actions per tick /8 vs per token /32),
  A-27 (sample_2k arithmetic), A-33 (sizes).

--------------------------------------------------------------------------------
11. STEP 1b · sample_2k fixture for CI
--------------------------------------------------------------------------------
Produce with `--profile sample_2k`, commit under P/tests/fixtures/ (directory to create; A-20 for root vs package
tests dir). CI runs both test trees on Linux and Windows; keep the fixture small enough for the repo and mark
DB-backed tests `integration`/`slow`. Depends on: 10.

--------------------------------------------------------------------------------
12. STEPS 2-3 · §4  Package P/backend/nn/jepa_v2/ (all new; no import of jepa_model.py)
--------------------------------------------------------------------------------
Directory does not exist. Build in this order (each module's tests before the next):
12.1 config.py — JepaV2Config frozen dataclass, values verbatim in C-1..C-9. (Parte I wants JSON-validated config
     with unknown-key errors — A-29.)
12.2 sigreg.py — SIGReg(knots=17, num_proj=1024, t_max=3.0), sigreg_batch(u) = reg(u.transpose(0,1)),
     sigreg_temporal(u) = reg(u) exactly as Parte III §4.2 (Parte I A.1 identical except `dtype=proj.dtype` in
     randn — A-30). Reference implementation for the parity test is already in the repo:
     R/tools/verify_math_claims.py sigreg_epps_pulley :334 and R/tools/measure_sigreg_sample_size.py
     sigreg_reference :116 / ep_stat :111 (their mutual parity is exact: 1.0117133855819702 both).
     Test P/tests/test_sigreg.py (new): parity rel 1e-5 on z ~ (8,64,32) with a fixed generator; N(0,I) ≈ 1
     (measured H0 mean 1.050 ± 0.093 at N=16, 1.053 at N=48 pooled; gaussian 256-d 1.054); constant ≫ 1 (measured
     16.8 at N=16, 4237 at N=4096 for constant + 1e-3 noise); finite bounded gradient, Thm 4 |∂/∂z_i| ≤ 4/(N s²)
     numerically; gradcheck float64 N=16, D=4, M=8 (Parte I); temporal vs batch on constructed tensors.
12.3 blocks.py — RMSNorm(d, eps=1e-6); SwiGLU(d, d_ff) with d_ff = int(2/3·ffn_mult·d) rounded to a multiple of 8
     (= 344 for d=128; Parte I says 352 — A-31); rope(q,k,positions) θ_i = 10000^(-2(i-1)/d_head), relative
     positions; CausalSelfAttention(d, n_heads, qk_norm=True) with Linear(d,3d,bias=False), LN on q and k, RoPE,
     scaled_dot_product_attention(is_causal=True), out-proj without bias; TransformerBlock pre-norm; FiLM(cond_dim,d)
     y = (1+γ)⊙x+β with the final Linear zero-initialised. Existing SuperpositionLayer
     (P/backend/nn/layers/superposition.py:14: sigmoid γ, zero-init β, context_dim=METADATA_DIM) is NOT this form —
     reuse optional (Parte I §9 says keep FiLM/Superposition as the mechanism).
     Test P/tests/test_jepa_v2_blocks.py (new): causality (perturb token t leaves outputs < t unchanged); RoPE depends
     only on relative positions; RMSNorm == LayerNorm on zero-mean input; SwiGLU shape; permutation test of the
     encoder (Parte I J3).
12.4 tokenizer.py — x_num (B, L=T·P, 21), x_cat (B, L, 3); Conv1d(21, d_num, kernel=P, stride=P) on x_num.transpose(1,2)
     -> (B,T,d_num); Embedding(V_i, e_i) per tick, mean over the P ticks; concat (B,T,d_num+10) -> Linear(·, d_model);
     no absolute positions. d_num is not specified (A-32).
12.5 encoder.py — EncoderV2.forward(x_num, x_cat, return_taps=False): taps = [h0, h1..h4]; final RMSNorm only for
     the heads, never for SIGReg; served representation taps[k], default k = n_layers // 2 = 2.
12.6 projector.py — 128 -> 256 -> 64, GELU, no final norm (Parte I inserts LayerNorm after the first Linear — A-31).
12.7 predictor.py — PredictorV2(z, horizon_idx): 2 causal blocks + FiLM on the horizon embedding.
12.8 losses.py — jepa_v2_loss verbatim §4.6 (generator seed cfg.seed·1_000_003 + step; L_next without stop-gradient;
     L_multi over horizons[1:] normalised by len-1; L_sig_T on proj(taps[k]) for k in sigreg_taps; L_sig_B on u;
     weights w_next, w_multi, λ_T, λ_B). No EMA, stop-grad, negatives, queue. Projector shared.
12.9 sampler.py — from safetensors shards (entry 10): per epoch, per episode ≥ 384 ticks, uniform offsets (seed per
     epoch), windows (x_num[384,21], x_cat[384,3]); B=128; validation offsets fixed (seed 0); never pad (J-5); episodes
     < 384 ticks skipped and counted. Census: strict episodes ≥ 384 ticks are 30 % of episodes but hold 99.2 % of
     ticks (frac_ticks_in_episodes_ge_L = 0.9919 for L=384).
12.10 telemetry.py — every probe_every steps on a fixed probe batch of 4,096 validation windows (Parte I: 2,048 —
     A-31): compute_collapse_metrics (P/backend/nn/collapse_metrics.py:41-82; keys std_mean, std_min,
     effective_rank, cosine_offdiag_mean — the doc's `effective_rank` and `std_min` exist verbatim) on
     taps[k].mean(1) and on u; SIGReg batch/temporal; S_straight (Parte II §6.3); probe AUROC (entry 14).
     metrics.csv + TensorBoard via the existing TensorBoardCallback (P/backend/nn/tensorboard_callback.py:90;
     build_run_dir :65; hooks on_train_start/on_epoch_start/on_batch_end/on_epoch_end/on_train_end/close
     :140-249) and CallbackRegistry (training_callbacks.py:67, fire :85). Abort (exit ≠ 0, checkpoint marked
     "aborted") if effective_rank < 8.0 or std_min < 1e-3 for two consecutive readings. Parte III §4.8 says NO
     EmbeddingCollapseDetector; Parte I §7.6 says keep it as the gate (P/backend/nn/early_stopping.py:39,
     threshold 0.01, patience 2) — A-31.
12.11 trainer.py — AdamW(lr_max, betas, weight_decay); per-STEP schedule lr(step) = lr_min + 0.5(lr_max-lr_min)
     (1+cos(π(step-warmup)/(steps-warmup))) after linear warmup; scheduler.step() inside the optimizer step
     (legacy: training_orchestrator._run_epoch_loop steps per epoch at :385-400, step call :394; jepa_trainer.py
     SequentialLR :114-127); autocast bf16 = existing amp_autocast() (P/backend/nn/config.py:165-176), no GradScaler
     (legacy jepa_trainer.py:131-132 uses GradScaler with default fp16 autocast :255 — J13); clip_grad_norm_(1.0);
     set_global_seed (nn/config.py:16, GLOBAL_SEED=42 :13, seeded_generator :42); cudnn stays disabled on HIP
     (get_device :89, :132). Checkpoint every probe_every: encoder-only state_dict -> "jepa_v2_encoder.pt" plus
     "jepa_v2_full.pt" for resume; sidecar v2 (entry 7) with extra = {step, best_probe_auroc, rankme, sigreg, lr,
     seed, git_sha}. Parte I adds optional gradient accumulation and full RNG resume.
     Test P/tests/test_jepa_v2_training_smoke.py (new): 200 steps on sample_2k, < 60 s CPU (Parte I: < 2 min —
     A-31): loss decreases, RankMe grows vs step 0, no NaN, valid checkpoint + sidecar, two runs same seed ->
     identical weights (determinism on ROCm SDPA — A-35). pytest.ini global timeout 30 s -> needs
     `pytestmark = pytest.mark.timeout(...)` (pattern: test_training_orchestrator_logic.py:18) and the `slow` marker.
12.12 P/tests/test_collapse_metrics.py (exists, 8 tests) — add "isotropic gaussian -> RankMe ≈ D" (measured 255.4/256).
Acceptance (§11 row 2-3): `pytest tests/test_sigreg.py tests/test_jepa_v2_blocks.py tests/test_jepa_v2_training_smoke.py -q`:
  SIGReg parity, smoke green, determinism.
Depends on: 4, 7 (sidecar), 10/11 (shards + sample_2k).

--------------------------------------------------------------------------------
13. PULLED FORWARD FROM STEP 5 (§6.1/§6.2 jepa_v2 branches only) — required by the step-4 command
--------------------------------------------------------------------------------
§11 row 4 runs `run_full_training_cycle.py --model-type jepa_v2`, which needs: ModelFactory.TYPE_JEPA_V2 = "jepa_v2"
(P/backend/nn/factory.py constants :36-41; get_model :44-113 builds EncoderV2(CS2_V2, JepaV2Config()) reading
dims from the schema; get_checkpoint_name("jepa_v2") == "jepa_v2_encoder", :115-124), and a TrainingOrchestrator
branch for "jepa_v2" (constructor :117-140; ModelFactory.get_model(self.model_type) at :176) that does not use
_fetch_batches :625-660 / _prepare_tensor_batch :820-935 (one window per batch, context features[:10], target
[10:11], 5 negatives + pool) but delegates to jepa_v2.sampler + jepa_v2.trainer.train_step, uses _run_epoch_loop
only for callbacks / early stopping on probe AUROC, skips the per-epoch scheduler.step() (:385-400) and the D-13
collapse block (:344-377), and writes head_trained=False + probes_calibrated in _checkpoint_extra_meta (:456-476).
Legacy types keep working but emit DeprecationWarning. The doc files this under step 5 (A-36). Depends on: 12.

--------------------------------------------------------------------------------
14. STEP 4 · §5.1  jepa_v2/probes.py
--------------------------------------------------------------------------------
Target: NEW P/backend/nn/jepa_v2/probes.py. fit_linear_probe(Z_train, y_train, Z_val, y_val, groups_train) ->
  ProbeResult: StandardScaler + LogisticRegression(C=1, class_weight="balanced", max_iter=3000); AUROC on val;
  temperature T fitted by NLL on val (Guo 2017); ECE with 15 bins. Reference code exists: verify_math_claims.py
  probes :352-388 (GroupKFold(5), identical LR params, no calibration) and measure_event_horizons.py
  ece_equal_width :180 / ece_equal_mass :190 / bootstrap_ece :200 / calibration_experiment :232.
  Labels per window, external (from export labels/manifest, never from the input): round_won (round of last token),
  death_within_2s (health -> 0 in the 128 ticks after the last token; measured positive rate 1.18 % per token at
  H=16 tokens on 298,354 tokens, tokens require health > 0 at end), enemy_visible_within_2s (measured "any" 70.3 %
  per window in verify_math; "new contact" 18.0 % per token — A-38), opening_death (episode), side. GroupKFold(5)
  by demo.
Tests: P/tests/test_probes.py (new): LeakageGuard (source columns ∩ schema = ∅; permutation -> AUROC ≈ 0.5);
  ECE ≈ 0 on a perfectly calibrated classifier; temperature scaling does not change the argmax. `side` is both a
  schema input and a probe label, and enemy_visible_* derives from the schema column enemies_visible — the guard
  as written fails by construction (A-39; the Field.derived_from_future flag hints at the intended rule).
Depends on: 12.10 (telemetry consumes it), 10 (labels).

--------------------------------------------------------------------------------
15. STEP 4 · §5.2  tools/benchmark_jepa_v2_vs_legacy.py + docs/benchmarks/
--------------------------------------------------------------------------------
Target: NEW R/tools/benchmark_jepa_v2_vs_legacy.py; NEW R/docs/benchmarks/jepa_v2_vs_legacy.md (dir absent).
Contenders on the SAME window lists (manifest, seed 0; 40 k train / 8 k val / 8 k test):
  A = legacy production recipe at B=128 from the existing classes — JEPAEncoder (P/backend/nn/jepa_model.py:33-66:
      Linear(25,512) -> LN -> GELU -> Dropout(0.1) -> Linear(512,256) -> LN, applied per tick) + mean, JEPAPredictor
      (:68-97: 256 -> 512 -> LN -> GELU -> Dropout -> 256), EMA target encoder with cosine momentum base 0.996
      (jepa_trainer.py:138-191) initialised as a COPY (J6), InfoNCE jepa_contrastive_loss (:408-426) with learned τ
      (log_temperature init log 0.07 at :151, clamped [0.01, 1.0] at trainer :266) and MoCo queue 4096 (:153-158,
      64 sampled :317), VICReg 0.01 × vicreg_regularization(λ_var=25, λ_cov=1) (:433-450, trainer :274-275),
      AdamW lr 1e-4 wd 1e-2 (trainer :79-113). Requires ALLOW_LEGACY_NEURAL_TRAINING=True only if built through
      TrainingOrchestrator (A-40). Parte I names this tools/baseline_legacy_infonce.py and, elsewhere, an
      `objective="legacy_infonce"` mode of the v2 trainer — three homes for A (A-40).
  B = jepa_v2 with JepaV2Config().
  R = raw features, window mean (Parte II §12.5 used the 25-d v1 vector; v2 numeric is 21-d — A-41).
Metrics on the frozen encoder (test split): RankMe on 8 k windows; probe AUROC/ECE (entry 14); kNN-20; R² of
  Δpos at 0.5 s and 2 s. Pass: B ≥ A and B ≥ R on every AUROC; RankMe(B) ≥ 2·RankMe(A); mean ± std over 3 seeds.
  Report includes the "legacy archiviato" row from R/docs/research/verify_math_claims_2026-09-05.json (C-19).
Tests: Parte I App. E: "benchmark §7.7 as a slow-marked test".
Depends on: 12, 13, 14, 10 (medium export).

--------------------------------------------------------------------------------
16. STEP 4 · §5.3  The 20 k-step run and the exit criterion
--------------------------------------------------------------------------------
Command (§11 row 4): `PYTHONPATH=. .venv/bin/python run_full_training_cycle.py --model-type jepa_v2` (20 k steps,
  ≈ 1-2 h on the RX 9070 XT per Parte III; Parte I §7.11 says minutes) then R/tools/benchmark_jepa_v2_vs_legacy.py,
  3 seeds each for A and B.
Exit: round_won AUROC(B) > 0.760 and death_within_2s AUROC(B) > 0.838 with a confidence interval excluding the raw
  baseline; RankMe(B) ≥ 64 (RankMe/d ≥ 0.5 at d=128). Note the conflict with "RankMe(B) ≥ 2·RankMe(A)" (A-42) and
  that 0.838 is the raw LAST-TICK value while R is defined as the window MEAN (0.829) (A-43).
Outputs consumed downstream: sidecar extra probes_calibrated = True when ECE < 0.05 on VAL and AUROC > raw baseline
  (§9.1) — written by the trainer or by _checkpoint_extra_meta (A-44). If the criterion fails: repeat step 4 with
  the λ_T sweep {1, 2.5, 5, 20} (Parte I: {1, 2.5, 5, 10, 20}) before anything else (Parte I step 4).
Depends on: 15; GPU.

--------------------------------------------------------------------------------
17. TEST BOOKKEEPING for steps 0-4 (Parte III §10)
--------------------------------------------------------------------------------
Add (none exist): test_schema_v2.py, test_naming.py, test_export_episodes.py, test_sigreg.py, test_jepa_v2_blocks.py,
  test_jepa_v2_training_smoke.py, test_probes.py, test_legacy_frozen.py (+ the §1.1 test inside
  test_training_orchestrator_logic.py).
Modify (exist): test_jepa_window_fetcher.py / test_rap_window_fetcher.py (normalized names);
  test_persistence_stale_checkpoint.py (fingerprint case); test_training_orchestrator_logic.py ("remove the
  per-epoch scheduler.step() expectations for jepa_v2" — no such expectation exists in the file today: its 17 tests
  cover init/patience/batch/RNG/tick-rate/round-stats; nothing to remove — A-45); test_collapse_metrics.py (+ gaussian
  -> RankMe ≈ D). Blast radius of entry 1 across seven more test files (see entry 1).
Retire (step 5, not now): the App. E list — leave in place during milestone 1.

================================================================================
CONSTANTS SHEET (verbatim where the documents give them; source in brackets)
================================================================================
C-1  Token: patch_ticks P = 8 ticks = 125 ms at 64 tick/s [III §4.1; I §7.3: P = round(tick_rate/8) -> 16 at 128 Hz,
     duration invariant]. Measured tick rate 64.0 Hz; R²_id(8) = 0.974 [I App. G; III §4.1 comment].
C-2  Window: tokens_per_window = 48 tokens = 384 ticks = 6 s [III §4.1, §4.7; I §7.3]. Batch B = 128 windows
     [III §4.1 batch_size; I §7.3: tensors (128, 48, 31) in, (128, 48, d) out]. steps = 20 000 (≈ 2.5 M windows seen).
C-3  Horizons: (1, 4, 16) tokens = 0.125 / 0.5 / 2 s; w_next = 1.0, w_multi (β) = 0.5 [III §4.1, §4.6; I §7.5].
C-4  SIGReg: knots 17 on [0, t_max = 3.0]; num_proj M = 1024 directions resampled every step with a generator
     seeded by the global step (III losses.py: cfg.seed·1_000_003 + step; I §7.5: seed = global_step);
     λ_T (lambda_sigreg_temporal) = 2.5, sweep {1, 2.5, 5, 20} [III] / {1, 2.5, 5, 10, 20} [I]; λ_B
     (lambda_sigreg_batch) = 0.1; sigreg_taps = (0, -1) [III §4.1] vs L_T = {0, 2} with taps exposed at {0, 2, 4}
     [I §7.4-7.5]; proj = projector output only, never a LayerNorm [III §4.2; II §2.3.3].
     Reference values: H0 gaussian ≈ 1.05 (1.050 ± 0.093 at N=16; 1.054 at 256-d N=4096); archived encoder 660.6
     (standardised 76.3); random init 2026.2; constant+1e-3 noise 4237.0 [verify_math_claims JSON T7;
     sigreg_sample_size JSON].
C-5  Encoder (EncoderV2): d_model 128, n_layers 4, n_heads 4, ffn_mult 4 with SwiGLU d_ff = int(2/3·4·d) rounded to a
     multiple of 8 (= 344; I §7.4 writes 128→352→128), RMSNorm eps 1e-6, QK-norm, RoPE θ_i = 10000^(-2(i-1)/d_head)
     on relative positions, causal SDPA, pre-norm residual blocks, dropout 0.1 [I §7.4 only]; tokenizer
     Conv1d(21, d_num, k=P, s=P) + per-tick Embedding(V_i, e_i) averaged over P + Linear(d_num+10, d_model);
     cat_embed_dims (4, 4, 2) for (map_id, weapon_class, side) -> 21 + 10 = 31 inputs per tick; no absolute
     positions; final RMSNorm for heads only; served representation taps[k], k = n_layers // 2 = 2 by default;
     ≈ 1.3 M parameters total (tokenizer ≈ 32 k, blocks ≈ 0.8 M, projector ≈ 50 k, predictor ≈ 0.4 M) [I §7.4].
C-6  Projector: 128 -> 256 -> 64 (proj_hidden 256, proj_out 64), GELU, no final norm ("Guillotine") [III §4.5];
     Linear(128,256) -> LayerNorm -> GELU -> Linear(256,64) [I §7.4].
C-7  Predictor (PredictorV2): 2 causal TransformerBlocks on z_{≤t} + FiLM conditioning on the horizon embedding,
     FiLM y = (1+γ)⊙x + β with zero-initialised final weights (adaLN-Zero style) [III §4.3, §4.5; I §7.4].
C-8  Loss: L = w_next·L_next + w_multi·L_multi + λ_T·L_sig_T + λ_B·L_sig_B, all MSE terms in projector space,
     shared projector, no EMA / stop-gradient / negatives / queue / learned temperature [III §4.6; I §7.5].
C-9  Optimiser/schedule: AdamW, betas (0.9, 0.99), weight_decay 0.05, lr_max 1e-4 -> lr_min 1e-6 cosine PER STEP
     after 1 000 linear warm-up steps, grad_clip 1.0, bf16 autocast without GradScaler, seed 0, cudnn/MIOpen
     disabled on HIP [III §4.1, §4.8; I §7.5]. dtype "bf16".
C-10 Telemetry/abort: probe_every 500 steps on a fixed probe batch of 4 096 validation windows [III] (2 048 [I]);
     signals: RankMe (effective_rank) on taps[k].mean(1) and on u, std_min, SIGReg batch/temporal, S_straight,
     probe AUROC (+ I: mse_next/h4/h16, dpos_r2_h4/h16, rankme_tokens/rankme_pooled); abort if
     effective_rank < abort_rankme_below = 8.0 or std_min < abort_std_min_below = 1e-3 for two consecutive
     readings (exit ≠ 0, checkpoint marked "aborted"); best checkpoint = max mean probe AUROC, early-stopping
     patience 10 evaluations [I §7.6 only]. Logs: metrics.csv + TensorBoard.
C-11 Checkpoints: "jepa_v2_encoder.pt" (encoder state_dict only) + "jepa_v2_full.pt" (resume), every probe_every
     steps, under MODELS_DIR/global/ (persistence.get_model_path). Sidecar v2: {"schema_version": "v2",
     "schema_id": "cs2_v2", "schema_fingerprint": CS2_V2.fingerprint(), "numeric_dim": 21,
     "categorical_vocab_sizes": [10, 8, 3]} + extra {step, best_probe_auroc, rankme, sigreg, lr, seed, git_sha}
     (+ probes_calibrated after step 4; I adds recipe, git_sha, created_utc); mismatch ->
     SchemaMismatchError(StaleCheckpointError) [III §2.3, §4.8; I §7.2, step 2].
C-12 Schema cs2_v2 (version 1): 21 numeric fields in order — health/100, armor/100, has_helmet, has_defuser,
     equipment_value/10000, is_crouching, is_scoped, is_blinded, enemies_visible/5 (COUNT), pos_x/4096, pos_y/4096,
     pos_z/1024, view_yaw_sin, view_yaw_cos (ANGULAR from view_x), view_pitch/90 (from view_y), z_penalty
     (pos_z+map_name), time_in_round/115, bomb_planted, teammates_alive/4 (COUNT), enemies_alive/5 (COUNT),
     team_economy/16000; 3 categoricals — map_id vocab ("de_ancient","de_anubis","de_dust2","de_inferno","de_mirage",
     "de_nuke","de_overpass","de_train","de_vertigo","other") [10], weapon_class ("none","knife","pistol","smg",
     "rifle","sniper","heavy","grenade") [8], side ("CT","T","unknown") [3]; removed: kast_estimate (identically 0),
     round_phase (function of equipment_value); fingerprint = sha256 of json.dumps(fields, sort_keys) [III §2.1].
     v1 -> v2 numeric remap indices: [0..15, 20..24].
C-13 Actions: a_t = [(Δx, Δy, Δz)/8, Δyaw/180 with Δyaw wrapped to (-180, 180], Δpitch/90] toward the NEXT tick;
     last tick of an episode = 0 with mask; |Δx| ≤ 3.9 u/tick at 250 u/s [III §3]. (I §7.2: per token over 8 ticks,
     Δpos/32 clipped to [-1, 1].)
C-14 Export tensors per demo shard: x_num [N,21] f32; x_cat [N,3] i64 (I: i32); raw_pos_view [N,5] f32
     (pos_x, pos_y, pos_z, yaw°, pitch°); actions [N,5] f32; health [N] f32; enemies_visible [N] f32;
     episode_offsets [E+1] i64 (CSR); episode_meta [E,4] i64 (round_number, tick_start, tick_end, player_idx);
     labels_round [E,8] f32 (round_won, kills, deaths, kast, round_rating, opening_kill, opening_death,
     side_is_ct) from roundstats via the normalized join [III §3]. Path $DATA/cs2_v2/<split>/<demo_name>.safetensors.
     Per-tick byte cost 21·4 + 3·8 + 5·4 + 5·4 + 2·4 = 156 B.
C-15 manifest.json per split: schema fingerprint, demo list, match_date + match_date_source (OI-2 warning when the
     source is the ingestion clock), counts, demoparser version, sha256 of every shard, seed, UTC date [III §3];
     I step 1 adds git SHA, torch/numpy versions, tick_rate, per-episode tables with hashed player_id.
C-16 Profiles: full (all episodes; I: cap 4 096 ticks/episode ≈ 8-10 GB; III: ≈ 22 GB at 147.5 M ticks), medium
     (≤ 8 episodes per player-match, ≈ 3 GB, default), sample_2k (III: 2 000 episodes ≈ 6 MB; I: 2 000 windows
     ≈ 6 MB, committed under tests/fixtures/ for CI).
C-17 Split rules: per demo, chronological 70/15/15 on match_date with the same eligibility gates and pro/user
     separation as assign_dataset_splits; no demo in two splits (shard = demo); no episode crosses a round
     (episode = contiguous ticks of (demo, player, round_number), tick strictly consecutive); minimum episode
     length 64 ticks (1 s); windows need ≥ 384 ticks; validation windows at fixed offsets (seed 0); export reads
     PMS.dataset_split when assigned, else computes and writes the split only into the manifest [III §3; I §7.3, §8].
C-18 Probe set and calibration: round_won (round of the last token), death_within_2s (health -> 0 within 128 ticks
     after the last token), enemy_visible_within_2s, opening_death (episode), side; LogisticRegression(C=1,
     class_weight="balanced", max_iter=3000) on StandardScaler; GroupKFold(5) with group = demo; temperature T by
     NLL on VAL; ECE with 15 bins; accept ECE < 0.05; confidence shown = max_k softmax(ℓ/T) [III §5.1; I App. A.8].
     I §7.6/§7.8 online variant: Linear(128,k) or Linear→GELU→Linear on detached latents, lr 1e-3, wd 1e-4, 200 epochs.
C-19 Benchmark (I §7.7 / III §5.2-5.3): same window lists, seed 0, 40 k train / 8 k val / 8 k test; contenders
     A (legacy at B=128), B (jepa_v2), R (raw window mean); metrics on the frozen encoder: RankMe on 8 k test
     windows, probe AUROC/ECE, kNN-20 accuracy, R² Δpos at 0.5 s and 2 s; pass = B ≥ A and B ≥ R on all AUROCs and
     RankMe(B) ≥ 2·RankMe(A), mean ± std over 3 seeds; exit criterion round_won AUROC(B) > 0.760, death_within_2s
     AUROC(B) > 0.838 (CI excluding raw), RankMe(B) ≥ 64 (RankMe/d ≥ 0.5); report docs/benchmarks/jepa_v2_vs_legacy.md.
     Measured legacy row (verify_math_claims_2026-09-05.json, n = 14 255 windows, 5-fold GroupKFold):
       round_won (pos. rate 0.564): raw window-mean 0.7602 ± 0.047 | raw last-tick 0.7601 | archived 0.6770 ± 0.054 | random 0.6809
       death_within_128_ticks (pos. rate 0.0095): raw window-mean 0.8291 ± 0.052 | raw last-tick 0.8380 ± 0.049 | archived 0.7364 ± 0.018 | random 0.7039
       enemy_visible_within_128_ticks (pos. rate 0.703): raw 0.9494 | archived 0.9420 | random 0.9420
       RankMe (256-d): archived context 66.11, archived target 66.89, random init 60.83, raw 25-d 16.02, gaussian 255.42
       τ learned 0.0481; EMA drift context-vs-target 0.1347 (random 22.81); predictor MSE 0.383 vs identity 0.011.
C-20 Legacy freeze: _LEGACY_TRAIN_TYPES = {"jepa", "vl-jepa", "rap", "rap-lite"}; setting
     ALLOW_LEGACY_NEURAL_TRAINING: False; run_full_training_cycle --model-type required, choices
     {"jepa_v2","coach_v2","jepa","rap","all"}, "all" = jepa_v2 -> coach_v2 [III §1.1-1.2].
C-21 Legacy baseline-A recipe constants (from code): per-tick MLP 25→512→256 with LayerNorm/GELU/Dropout 0.1;
     predictor 256→512→256; context 10 ticks, target 1 tick (window 11); 5 negatives + cross-match pool of 500;
     τ init 0.07 clamped [0.01, 1.0]; MoCo queue 4 096 (64 sampled); EMA base momentum 0.996 cosine; VICReg
     λ_var 25, λ_cov 1, weight 0.01; AdamW lr 1e-4, wd 1e-2; warm-up 5 % of epochs then cosine per epoch; fp16
     autocast + GradScaler.

================================================================================
AMBIGUITIES / CONTRADICTIONS (not resolved; numbered for reference above)
================================================================================
Operational
A-1  A legacy JEPA+RAP run (PID 1481729, `./train.sh --patience 30`, started 2026-09-11 04:17) is producing exactly
     the checkpoints Step 0 forbids. The freeze cannot stop it; who decides, and whether P/models/global/jepa_brain*.pt
     written by it must be archived like the 2026-09-01 set, is not covered by the docs.
A-2  §1.3 "fail, don't warn": coach_manager.run_jepa_pretraining :588-602 catches ValueError -> warning and
     Exception -> error without re-raise, and ignores run_training()'s False; the CLI path already exits 3 on a
     failed quality gate (:529-537 + run_full_training_cycle.py:269-274). The doc does not say which path to fix.
A-3  The freeze test is named twice: test_training_orchestrator_logic.py::test_legacy_training_frozen_by_default
     (§1.1) and tests/test_legacy_frozen.py (§10, §11 row 0).
A-4  _LEGACY_TRAIN_TYPES lists "rap-lite", which TrainingOrchestrator.__init__ never accepts (only ModelFactory does);
     "pov-rap" is referenced in _checkpoint_extra_meta :470 but is not constructible either.
A-5  §1.2 registers --model-type choices jepa_v2 / coach_v2 (and makes "all" mean jepa_v2 -> coach_v2) before those
     types exist in ModelFactory / TrainingOrchestrator (factory.py:96-107 raises ValueError). train.sh's default
     MODEL_TYPE=all would then pick a non-existent pipeline until entries 12-13 and step 6 land.
A-6  §1.2 replaces `del orchestrator_jepa` with "model.cpu() after saving" but run_training() returns bool
     (training_orchestrator.py:524-...) — no model handle reaches run_full_training_cycle.py; also "coach v2 receives
     the encoder as an argument" (§7.7 last row) has no API yet.
A-7  §1.3 says to add assign_dataset_splits() in run_jepa_pretraining; the CLI already calls it at
     run_full_training_cycle.py:217, and the D9 evidence (all rows UNASSIGNED on 2026-09-05) may already be stale
     because of the 2026-09-11 run. The doc also assumes assignment cannot run "while ingestion is in progress (22
     tasks queued)" — the memory note says ingestion finished; re-verify.
Schema / extraction
A-8  Schema artefact: Parte I §7.2 and step 2 want configs/schema_cs2_v2.json + nn/feature_schema.py (FeatureSchema,
     Field, normalizers as data, fields with name/kind/unit/normalizer/valid_range/nullable); Parte III §2.1 wants a
     Python constant CS2_V2 in backend/processing/feature_engineering/schema_v2.py with name/kind/unit/scale/vocab/
     source_column/derived_from_future. Neither configs/ nor nn/feature_schema.py exists.
A-9  Parte III's Field has only `scale`; v1 fillers also CLIP (enemies_visible min(·,1.0), pos np.clip ±1, the four
     context features min(·,1.0); view_pitch unclipped) and apply fallbacks (has_helmet := armor>0 when None,
     is_blinded from flash_duration when present). The lossless-remap test forces v2 to reproduce these, which
     contradicts "every divisor is data, not code" unless clip/valid_range becomes a schema attribute.
A-10 Weapon vocab: Parte III ("none","knife","pistol","smg","rifle","sniper","heavy","grenade") vs Parte I (knife,
     pistol, smg, rifle, sniper, heavy, utility/other, unknown); WEAPON_CLASS_MAP (vectorizer.py:40-142) also has
     taser/zeus/c4 at 0.05 and unknown default 0.5 — their class is unspecified.
A-11 Map vocab: Parte III fixes 9 maps + "other"; Parte I says "map names seen in training + unknown".
A-12 `Field` collides with sqlmodel.Field (used throughout db_models.py) and dataclasses.field — naming only.
A-13 The remap test on "100 000 real ticks" needs the monolith (read-only) or a fixture; Parte I step 1 says the
     export should emit the first 100 k ticks in both representations — so test_schema_v2 depends on 1b, contrary
     to §11's order (1 before 1b).
A-14 §2.3 says v2 keys are written "via extra_meta" (=> meta["extra"]) but _validate_loaded_meta compares TOP-LEVEL
     schema_version (:158) and today rejects anything but "v1" before any fingerprint could be checked; metadata_dim
     (25) and feature_names checks (:164-181) also fail for v2 unless branched.
Naming / D8
A-15 normalize_player_name = strip().casefold() (Python, Unicode) vs ingestion's .strip().lower() vs the migration's
     SQLite lower(trim()) (ASCII-only fold). Measured: identical on today's names (0 differences), not guaranteed.
A-16 Doc line refs: run_ingestion.py:120 is a transient PlayerMatchStats (run_ml_pipeline), the persistent write is
     _save_player_stats :544/:588-595; the tick bulk insert is :1700 with the raw name assembled at :1469;
     round_stats_builder.py:1005 is the RoundStats insert (names already lowercased upstream), :1012 the PMS join.
A-17 coach_manager._fetch_round_stats_for_batch (§2.4 c) does not exist; only training_orchestrator has it (:1537).
A-18 `lower(trim(player_name)) = ?` in SQL defeats ix_pts_player_demo; verify_math_claims already sidesteps this with
     resolve_stored_name (per-demo DISTINCT + Python casefold). The doc prescribes the SQL form.
A-19 A migration of playertickstate and playermatchstats must be atomic across both tables: coach_manager
     _fetch_jepa_windows :873 and _fetch_rap_windows :989 join PTS to PMS/anchors by raw equality.
A-20 Locations: `tools/export_episodes.py` — R/tools/ (where verify_math_claims.py lives) or P/tools/?; `tests/…` —
     P/tests/ (all tests) or R/tests/ (conftest only)?; `tests/fixtures/` absent, P/tests/data/ exists empty;
     `$DATA` undefined (DATA_DIR exists in core/config.py; external disks documented in the memory note).
Export / episodes
A-21 Episode definition "tick strictly consecutive": the 2026-09-05 census (14.4 M rows, 40 demos) shows 7 098
     within-round gaps of 2-5 ticks (max gap 5; 0.05 % of diffs) that create 80 % of strict episode breaks; strict
     episodes: median 10 ticks, 65 % shorter than 64 ticks (0.33 % of ticks), 30 % ≥ 384 ticks holding 99.2 % of
     ticks; tolerance-7 episodes: all ≥ 1 271 ticks. The doc's ≥ 64 filter discards fragments but the strict rule
     still splits rounds at gaps; the census tool measured both variants and the doc picks strict without citing it.
A-22 round_number is anchored on round_freeze_end (rows of a round include post-round + next freeze time), round 1 is
     warm-up-contaminated, and some episodes are > 50 % dead ticks (health ≤ 0). The export/probe definitions do not
     say whether to drop round 1, cut at death, or mask dead ticks (measure_event_horizons keeps tokens only while
     health > 0 at the token end).
A-23 x_cat dtype: i64 (Parte III table) vs i32 (Parte I step 1).
A-24 episode_meta carries player_idx but Parte III's manifest has no player table; Parte I wants hashed player_id.
A-25 labels_round is f32 but round_rating is Optional (NULL) and kast/round_won are bools — NaN/mask policy unspecified.
A-26 Actions: per tick (Δpos/8, unbounded) in Parte III vs per token over 8 ticks (Δpos/32, clip [-1,1]) in Parte I §7.2.
A-27 sample_2k "≈ 6 MB": 2 000 episodes (III) or windows (I) of ≥ 384 ticks at 156 B/tick is ≈ 120 MB; 6 MB holds
     ≈ 38 k ticks (≈ 100 windows).
A-28 test_export_episodes and the "labels ≥ 95 %" check need real data; CI (Linux+Windows, 30 s timeout) cannot open
     the monolith — the split between unit (synthetic) and integration (DB) tests is not specified.
jepa_v2 package
A-29 Module set differs: Parte I step 3 (objectives.py with SIGReg/PredictionMSE/VICReg(B≥2)/InfoNCE-legacy,
     sampler with TransitionSampler, config.py as validated JSON) vs Parte III §4 (sigreg.py, losses.py, config.py
     frozen dataclass, blocks.py, probes.py). Parte I also wants the trainer to be "the only trainer" with an
     objective="legacy_infonce" mode.
A-30 SIGReg reference code: Parte III passes dtype=proj.dtype to randn (bf16 directions under autocast), Parte I A.1
     does not (fp32). Parity tolerance 1e-5 is stated against a float64/fp32 reference.
A-31 Numeric/architectural disagreements Parte I vs III: taps (0, -1) vs {0, 2}; projector without any norm vs
     Linear→LayerNorm→GELU→Linear; d_ff 344 (rule) vs 352 (text); dropout 0.1 (I only); probe batch 4 096 vs 2 048;
     early stopping patience 10 (I) vs none (III); EmbeddingCollapseDetector kept as gate (I) vs removed (III);
     smoke < 60 s (III) vs < 2 min (I); online torch probes (I §7.6) vs sklearn GroupKFold probes (III §5.1).
A-32 Tokenizer d_num (Conv1d output width) is unspecified (d_model − 10? independent?); cat embedding "mean over P
     ticks" assumes categoricals constant within a token — true for map/side, not for weapon_class.
A-33 Sizes: corpus is 428.6 M ticks (2026-09-11), not 147.5 M — full export ≈ 67 GB at 156 B/tick; Parte I's "full
     ≈ 8-10 GB with a 4 096-tick cap" and Parte III's "≈ 22 GB" are both stale.
A-34 safetensors is a transitive pin only (requirements-lock.txt); the owner's rules require a direct, pinned
     dependency with license/CVE check before export_episodes.py imports it.
A-35 "Two runs with the same seed -> identical weights" is not guaranteed on ROCm with SDPA (flash/mem-efficient
     kernels) unless the math backend is forced; the doc does not specify torch.use_deterministic_algorithms.
Step 4
A-36 §11 row 4's command (`run_full_training_cycle.py --model-type jepa_v2`) needs the factory/orchestrator jepa_v2
     branches that Parte III files under step 5 (§6.1-6.2); the dependency order is inverted.
A-37 Parte I numbers its steps differently (1 = export, 2 = schema) from Parte III (1 = schema+names, 1b = export).
A-38 `enemy_visible_within_2s`: verify_math_claims measured "any enemy visible within 128 ticks" (70 % positives);
     measure_event_horizons distinguishes contact_new (18 %) from contact_any — the doc does not say which.
A-39 LeakageGuard ("source columns of every label ∩ schema fields = ∅") fails by construction: `side` is both a
     schema categorical and a probe label; enemy_visible_within_2s derives from the schema column enemies_visible
     (future values). Field.derived_from_future exists but its role in the guard is undefined.
A-40 Baseline A has three homes: tools/benchmark_jepa_v2_vs_legacy.py (III §5.2), tools/baseline_legacy_infonce.py
     (I step 4), trainer objective="legacy_infonce" (I §7.5). ALLOW_LEGACY_NEURAL_TRAINING gates only
     TrainingOrchestrator constructions — a standalone benchmark built from JEPAEncoder/JEPAPredictor is not gated.
A-41 R (raw baseline) was measured on the 25-d v1 vector; v2's numeric vector is 21-d — which R enters the benchmark
     is not stated (the 0.760 / 0.838 thresholds come from the 25-d measurement).
A-42 "RankMe(B) ≥ 2·RankMe(A)" (I §7.7, III §5.2) conflicts with d = 128: if A (re-run at B=128) keeps RankMe ≈ 66
     as the archived encoder, 2·66 = 132 > 128 is unattainable; §5.3 replaces it with RankMe(B) ≥ 64.
A-43 §5.3's death threshold 0.838 is the raw LAST-TICK AUROC; R is defined as the window MEAN (0.829). round_won is
     the same for both (0.760).
A-44 probes_calibrated (sidecar extra, gate for step 8 per §9.1) is "written by step 4" — by the v2 trainer (§4.8
     extra list omits it) or by training_orchestrator._checkpoint_extra_meta (§6.2)? Unspecified.
A-45 §10 "remove the per-epoch scheduler.step() expectations for jepa_v2 in test_training_orchestrator_logic.py":
     no such expectation exists in that file today.
```

Key findings to weigh first: (1) the live legacy training run started 2026-09-11 collides with Step 0 and with any
D8 migration; (2) the step-4 verification command depends on factory/orchestrator work the doc schedules for step 5;
(3) the strict-consecutive episode rule fragments rounds at 2–5-tick gaps according to the owner's own census;
(4) `RankMe(B) ≥ 2·RankMe(A)` is arithmetically unreachable at d=128 if A behaves like the archived encoder;
(5) `coach_manager._fetch_round_stats_for_batch` and `$DATA` do not exist, and `safetensors` is not a direct pin.
