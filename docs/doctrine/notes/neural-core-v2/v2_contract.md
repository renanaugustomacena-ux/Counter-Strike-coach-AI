# JEPA v2 — MILESTONE 1 ENGINEERING CONTRACT (binding for every coding agent)

Repo R = /media/renan/WORK_RECOVERED1/PROIECT/Counter-Strike-coach-AI ; package P = R/Programma_CS2_RENAN.
Branch: feat/neural-core-v2 (already checked out). Python 3.12, venv R/.venv, torch 2.13.0+rocm10.0.0.
Always run python as `HIP_VISIBLE_DEVICES=0 R/.venv/bin/python` (never -1). Tests: `HIP_VISIBLE_DEVICES=0 R/.venv/bin/pytest -q -o addopts="" -p no:cacheprovider <files>`.
Reference documents (read the parts your task cites): scratchpad/v2_workmap.md (entries 0-17, C-1..C-21, A-1..A-45),
scratchpad/v2_inventory.md (existing code, interfaces to respect, dead paths), scratchpad/v2_decisions.md (measured
numbers). The owner's plan: R/CORREZIONE_NUCLEO_NEURALE_PARTE_III.md (Italian) and R/CORREZIONE_NUCLEO_NEURALE.md §7-§9.

## Rules for every agent
1. Touch ONLY the files assigned to you. Never edit files owned by another wave-1 agent (ownership list below).
2. NO git commands that change state (no add/commit/stash/checkout/reset). Read-only git (diff/log/status) is fine.
   The coordinator reviews and commits.
3. Never open the production monolith for writing. Read-only access = `open_ro()` pattern from R/tools/verify_math_claims.py:109
   (`file:<realpath>?mode=ro` + `PRAGMA query_only=1`). Do not run the training entry points. Do not start long jobs.
4. Code style: ruff (line length 100, target py311), black 100, isort profile black. Run
   `R/.venv/bin/pre-commit run --files <your files>` at the end and fix what it reports (it may reformat; re-run).
   Typed, explicit code; functions < 50 lines where practical; files < 800 lines; no new dependencies except
   `safetensors==0.8.0` (already installed; the export agent adds the direct pin). No AI attribution anywhere.
5. Tests live in P/tests/ (pytest.ini: testpaths `tests Programma_CS2_RENAN/tests`, global 30 s per-test timeout;
   use `pytestmark = pytest.mark.timeout(120)` + `@pytest.mark.slow` for slower tests; markers slow/integration/unit
   are registered). Tests must not need the monolith unless marked `integration` and skipped without
   CS2_INTEGRATION_TESTS=1.
6. Legacy behaviour stays intact: FEATURE_NAMES/METADATA_DIM=25, extract/extract_batch, legacy checkpoints, sidecar v1,
   ModelFactory names, orchestrator contracts listed in v2_inventory.md "Interfaces v2 must respect".
7. Every deviation from the owner's documents must be one of the DECISIONS below; if you hit a new ambiguity, pick the
   simplest option, implement it, and list it in your final report under "Decisions taken".
8. Final report: files created/modified (paths), tests added + the exact pytest command and its result, pre-commit
   result, decisions taken, anything left undone.

## Decisions on the open points (coordinator, 2026-09-11)
D-01 Freeze gate: `ALLOW_LEGACY_NEURAL_TRAINING` (default False in core/config.py defaults next to USE_JEPA_MODEL);
     TrainingOrchestrator.__init__ raises RuntimeError for model_type in {"jepa","vl-jepa","rap","rap-lite"} unless
     the setting is True, placed AFTER the existing model_type validation (rap's USE_RAP_MODEL ValueError keeps precedence).
     Single test file P/tests/test_legacy_frozen.py. Existing tests that construct TrainingOrchestrator get the
     setting via an autouse fixture in P/tests/conftest.py that patches get_setting("ALLOW_LEGACY_NEURAL_TRAINING")
     to True for every module EXCEPT test_legacy_frozen.py (the fixture reads request.module.__name__).
D-02 run_full_training_cycle.py: --model-type required, choices {jepa_v2, coach_v2, jepa, rap, all}; "all" =
     jepa_v2 then coach_v2; coach_v2 raises NotImplementedError("coach_v2 arrives with step 6") until it exists;
     legacy jepa/rap phases keep the current code (incl. the GPU-reclaim block) and only run when the gate allows.
     jepa_v2 phase = call `Programma_CS2_RENAN.backend.nn.jepa_v2.cli.run_jepa_v2(args)` (wave-2 module; wave-1
     agent writes the dispatch behind a lazy import and a clear error if the module is missing).
D-03 coach_manager.run_jepa_pretraining: call self.assign_dataset_splits() first; if run_training() returns False
     raise RuntimeError("JEPA pre-training aborted: <reason>") instead of warning; keep TrainingStopRequested re-raise.
D-04 Schema: Python constant `CS2_V2` in P/backend/processing/feature_engineering/schema_v2.py (no configs/*.json;
     `FeatureSchema.to_json()` exists for docs). Dataclass named `SchemaField` (not Field). Fields carry
     name, kind, source_column, unit, scale, clip (optional (lo,hi)), vocab (categorical), derived_from_future=False,
     description. fingerprint() = sha256 of json.dumps(fields as dicts, sort_keys=True, separators=(",",":")).
D-05 Numeric fields (21, this exact order = v1 indices [0..15, 20..24]): health, armor, has_helmet, has_defuser,
     equipment_value, is_crouching, is_scoped, is_blinded, enemies_visible, pos_x, pos_y, pos_z, view_yaw_sin,
     view_yaw_cos, view_pitch, z_penalty, time_in_round, bomb_planted, teammates_alive, enemies_alive, team_economy.
     Scales/clips reproduce v1 EXACTLY (lossless remap): health/100, armor/100, equipment_value/10000 (NO clip, as v1),
     enemies_visible/5 clipped to ≤1, pos_x,pos_y /4096 clipped [-1,1], pos_z /1024 clipped [-1,1], yaw sin/cos of
     radians(view_x), view_pitch = view_y/90 (no clip), z_penalty = core.spatial_data.compute_z_penalty(pos_z, map_name)
     (0.0 when map unknown), time_in_round/115 clipped ≤1, bomb_planted 0/1, teammates_alive/4 clipped ≤1,
     enemies_alive/5 clipped ≤1, team_economy/16000 clipped ≤1. Fallbacks as v1: has_helmet None -> armor>0;
     NaN -> 0, +inf -> 1, -inf -> -1. Categorical (3): map_id vocab (10) = de_ancient, de_anubis, de_dust2,
     de_inferno, de_mirage, de_nuke, de_overpass, de_train, de_vertigo, other; weapon_class vocab (9) = none, knife,
     pistol, smg, rifle, sniper, heavy, grenade, other (none = NULL/empty/"nan" active_weapon; other = taser/zeus/c4
     or any string not in vectorizer.WEAPON_CLASS_MAP); side vocab (3) = CT, T, unknown. categorical_vocab_sizes =
     [10, 9, 3]; embedding dims (4, 4, 2). Vocab fallbacks (other/none/unknown) are logged at WARNING, throttled.
D-06 vectorizer.py gains: `extract_v2(tick_data, map_name=None, side=None) -> (np.float32[21], np.int64[3])`,
     `extract_frame_v2(df: pandas.DataFrame, map_name: str|None, side: str|None) -> (np.float32[N,21], np.int64[N,3])`
     (VECTORISED, used by the export; df columns = PlayerTickState column names), and
     `remap_v1_to_v2(x25, map_name, active_weapon, side) -> (np.float32[21], np.int64[3])`. v1 extract/extract_batch untouched.
D-07 HeuristicConfig (base_features.py) gains time_in_round_max=115.0, teammates_alive_max=4.0, enemies_alive_max=5.0,
     team_economy_max=16000.0; v1 `_fill_context_features` reads them (same numbers -> no behaviour change);
     `MATCH_AGGREGATE_DIM = len(MATCH_AGGREGATE_FEATURES)` in coach_manager.py replaces the METADATA_DIM assert for
     the aggregate list (D5) — owned by the step-0 agent because it owns coach_manager.py.
D-08 Names: P/backend/storage/naming.py with `normalize_player_name(s) -> str` = str(s).strip().casefold() and
     `resolve_stored_names(conn, demo_name) -> dict[str,str]` (normalized -> stored spelling) built from
     playermatchstats.player_name for that demo (fallback: DISTINCT player_name from playertickstate, LIMIT-bounded).
     Joins in new code normalise in Python; NO monolith migration and NO change to run_ingestion.py in milestone 1.
D-09 Sidecar v2 (persistence.py): `save_nn(model, version, user_id=None, extra_meta=None, schema_meta=None)`;
     when schema_meta is given the sidecar's TOP-LEVEL keys are {"schema_version":"v2","schema_id","schema_fingerprint",
     "numeric_dim","categorical_vocab_sizes","extra"}; `_validate_loaded_meta` branches on schema_version:
     "v1" -> current checks; "v2" -> fingerprint/numeric_dim/vocab-sizes must equal the running CS2_V2 (import lazily),
     mismatch -> `SchemaMismatchError(StaleCheckpointError)`. `load_nn` unchanged otherwise. git_sha/created_utc go
     under extra when provided by the caller.
D-10 Episodes (export): per (demo, normalized player), rows ordered by tick; segment on round_number change and on
     tick gaps; gaps of 2..7 ticks are BRIDGED by forward-filling the previous row (the census shows 80 % of strict
     breaks are 2-5-tick parser gaps) and marked in a `filled` tensor; gaps > 7 split the episode. Each episode is
     CUT at the first tick with health <= 0, keeping that death tick as its last tick (post-death spectating excluded).
     Round-1 ticks with time_in_round == 0 (warm-up) are dropped. Keep episodes with >= 64 ticks.
D-11 Export layout: `--out DIR` required (no $DATA; recommended /data/PROIECT/cs2_v2 — NVMe). One safetensors shard
     per demo at DIR/<split>/<demo_name>.safetensors with tensors: x_num[N,21] f32, x_cat[N,3] i64,
     raw_pos_view[N,5] f32 (pos_x,pos_y,pos_z,view_x deg,view_y deg), actions[N,5] f32 (Δx,Δy,Δz)/8, Δyaw/180 wrapped
     to (-180,180], Δpitch/90 toward the NEXT tick, 0 at episode end), health[N] f32, enemies_visible[N] f32,
     tick[N] i64, filled[N] u8, episode_offsets[E+1] i64 (CSR), episode_meta[E,4] i64 (round_number, tick_start,
     tick_end, player_idx), labels_round[E,8] f32 (round_won, kills, deaths, kast, round_rating, opening_kill,
     opening_death, side_is_ct) with NaN where the roundstats row/column is missing and labels_mask[E,8] u8.
     safetensors metadata (all str): demo_name, map_name, tick_rate, players (json list, index = player_idx),
     schema_fingerprint, split, match_date, match_date_source, export_version="1", git_sha, created_utc.
     manifest.json per split: schema_fingerprint, export_version, git_sha, created_utc, demoparser version, seed,
     demos [{demo_name, file, sha256, match_date, match_date_source, n_ticks, n_episodes, players}], totals,
     warnings (OI-2 when match_date_source is not chronological).
D-12 Split: read playermatchstats.dataset_split (stored as the enum NAME, e.g. "TRAIN"); a demo's split = the split
     of its rows (all equal); UNASSIGNED demos are skipped and counted. No recomputation in the export.
D-13 Profiles: full (all episodes), medium (default: at most 8 episodes per (demo, player), the longest ones),
     sample (fixture: 16 demos spread over the three splits, 2 episodes per demo, each truncated to 448 ticks, all
     players, target <= 3 MB total; written to P/tests/fixtures/cs2_v2_sample/ by the coordinator, never auto-committed).
D-14 jepa_v2 package P/backend/nn/jepa_v2/ (new, never imports jepa_model.py): config.py (frozen dataclass
     JepaV2Config with the C-1..C-10 values: numeric_dim=21, cat_vocab_sizes=(10,9,3), cat_embed_dims=(4,4,2),
     patch_ticks=8, tokens_per_window=48, d_model=128, n_layers=4, n_heads=4, ffn_mult=4, dropout=0.1,
     rope_theta=10000.0, proj_hidden=256, proj_out=64, predictor_layers=2, horizons=(1,4,16), w_next=1.0,
     w_multi=0.5, lambda_sigreg_temporal=2.5, lambda_sigreg_batch=0.1, sigreg_num_proj=1024, sigreg_knots=17,
     sigreg_t_max=3.0, sigreg_taps=(0,-1), served_tap=2, batch_size=128, steps=20000, warmup_steps=1000,
     lr_max=1e-4, lr_min=1e-6, weight_decay=0.05, betas=(0.9,0.99), grad_clip=1.0, dtype="bf16", seed=0,
     probe_every=500, probe_windows=4096, abort_rankme_below=8.0, abort_std_min_below=1e-3,
     warn_rankme_ratio_below=0.25), sigreg.py, blocks.py, tokenizer.py, encoder.py, projector.py, predictor.py,
     losses.py (wave 1); sampler.py, telemetry.py, trainer.py, probes.py, cli.py (wave 2).
D-15 Architecture constants: d_ff = int(2/3 * ffn_mult * d_model) rounded UP to a multiple of 8 (= 344); tokenizer
     d_num = d_model - sum(cat_embed_dims) = 118, Conv1d(21, 118, kernel=8, stride=8) on x_num, categorical
     embeddings per tick averaged over the 8 ticks, concat -> Linear(128,128); no absolute positions; projector
     Linear(128,256)-GELU-Linear(256,64) with NO normalisation; SIGReg statistic computed in float32 with directions
     drawn in float32 from a torch.Generator seeded cfg.seed*1_000_003+step; temporal SIGReg taps (0,-1) on the
     projector of the tap outputs; served representation = taps[2] WITHOUT a final norm (a separate RMSNorm exists
     for heads); no EmbeddingCollapseDetector; abort on effective_rank < 8 or std_min < 1e-3 twice in a row;
     WARNING when effective_rank/d_model < 0.25.
D-16 Tensor conventions: x_num (B, L=384, 21) float32, x_cat (B, 384, 3) int64, tokens T=48; taps list
     [h0(tokenizer out), h1..h4]; encoder.forward(x_num, x_cat, return_taps=False) -> z (B,48,128) or (z, taps).
D-17 Labels for probes/heads are derived at sampling time from the shard tensors: round_won / opening_death / side
     from labels_round of the window's episode; death_within_2s = a tick with health <= 0 within the 128 ticks after
     the window's last tick inside the same episode; contact_new_within_2s = enemies_visible == 0 at the last tick
     and > 0 at some tick within the next 128 ticks of the episode. "enemy_visible_within_2s (any)" is reported but
     excluded from pass/fail (near-leaky).
D-18 Benchmark exit (step 4): round_won AUROC(B) > raw-features AUROC on the SAME windows and > 0.760;
     death_within_2s AUROC(B) > raw last-tick AUROC on the same windows and > 0.838; RankMe(B) >= 64 on the 128-d
     served representation (replaces the 2×RankMe(A) rule). Raw = the 21-d v2 numeric vector (window mean and last
     tick both reported). Mean ± std over 3 seeds; probes = sklearn LogisticRegression(C=1, class_weight="balanced",
     max_iter=3000) on StandardScaler, GroupKFold(5) by demo; ECE 15 equal-width bins after temperature scaling.
D-19 Loss weights as documented (w_next 1.0, w_multi 0.5, λ_T 2.5, λ_B 0.1) for the first run; per-horizon losses
     logged; sweep {1, 2.5, 5, 20} only if the exit criterion fails.
D-20 Determinism test: two 200-step smoke runs with the same seed on CPU must give identical weights; on GPU a
     tolerance of 1e-4 is accepted.

## File ownership, wave 1 (parallel)
- Agent W1-A (step 0): P/backend/nn/training_orchestrator.py, P/core/config.py, P/backend/nn/coach_manager.py,
  R/run_full_training_cycle.py, R/train.sh (header/comments only if needed), P/tests/conftest.py (autouse fixture),
  P/tests/test_legacy_frozen.py (new), P/tests/test_coach_manager_flows.py (only if a test must change).
- Agent W1-B (schema): P/backend/processing/feature_engineering/schema_v2.py (new), vectorizer.py (additions only),
  base_features.py (D-07 fields), P/tests/test_schema_v2.py (new), P/tests/test_metadata_dim_contract.py (extend).
- Agent W1-C (naming + sidecar): P/backend/storage/naming.py (new), P/tests/test_naming.py (new),
  P/backend/nn/persistence.py, P/tests/test_persistence_stale_checkpoint.py (extend).
- Agent W1-D (jepa_v2 core): P/backend/nn/jepa_v2/{__init__,config,sigreg,blocks,tokenizer,encoder,projector,
  predictor,losses}.py (new), P/tests/test_sigreg.py, P/tests/test_jepa_v2_blocks.py, P/tests/test_jepa_v2_losses.py (new),
  P/tests/test_collapse_metrics.py (add the gaussian RankMe test).
- Agent W1-E (probes): P/backend/nn/jepa_v2/probes.py (new; self-contained, sklearn + numpy), P/tests/test_probes.py (new).
Wave 2 (after review): export tool, sampler/telemetry/trainer/cli, factory dispatch, fixture, benchmark tool, run.
