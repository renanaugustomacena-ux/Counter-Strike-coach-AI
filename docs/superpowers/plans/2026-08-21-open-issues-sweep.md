# Open-Issues Sweep Implementation Plan (2026-08-21)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every issue in docs/OPEN_ISSUES.md that is fixable on the Windows dev box, so only owner-gated training (R8+) and Linux data-box work remain.

**Architecture:** Grouped TDD fixes on branch `fix/open-issues-sweep` (already carries the docs-sanitation commit). Each task = failing test → minimal fix → green → commit with explicit paths (NEVER `git add -A`; the tree holds ~210 foreign README edits that must not be committed). One PR at the end.

**Tech Stack:** Python 3.12 (`venv_win/Scripts/python.exe`), pytest (`-m "not slow and not integration"`), black/isort, SQLModel/SQLite, PyTorch CPU, PySide6.

**Spec:** docs/OPEN_ISSUES.md (consolidated register) + docs/audit/FINDINGS.md (F-numbers) + TASKS.md rows. Owner decisions 2026-08-21: F-0020 → *recreate the CSVs* (honestly: generator tool + graceful per-component degradation; generation itself runs on the Linux data box — both local DBs here are empty); F-0028 → *remove dead inference*; #67/R10 stay deferred; one branch/one PR.

## Global Constraints

- Suite baseline on this box: **0 failed / 2617 passed / 18 skipped** (after installing pytest, tensorboard, ncps, hopfield-layers into venv_win). Every task ends ≥ this bar.
- Gate command: `venv_win/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/ tests/ -m "not slow and not integration" -q --timeout=120`
- Invariants (SESSION_HANDOFF conventions): no tick decimation; GLOBAL_SEED=42; METADATA_DIM=25; rating_* RAW; KAST ratio [0,1]; tick rate per-demo, never bare 64 (AST guard test); no fabricated data — honest sentinel over plausible zero.
- Package files touched → run `venv_win/Scripts/python.exe Programma_CS2_RENAN/tools/sync_integrity_manifest.py` before commit; format with black/isort on touched files.
- Commits: explicit paths only. Trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- `hltv_metadata.db` on this box: schema present, **0 rows** in all 7 tables. `Programma_CS2_RENAN/backend/storage/database.db` absent. All DB tests use tmp fixture DBs.

---

### Task 1: OI-1 — data_quality per-item completeness enumeration

**Files:**
- Modify: `Programma_CS2_RENAN/backend/nn/data_quality.py:115-130`
- Test: `Programma_CS2_RENAN/tests/test_data_quality.py` (find existing; else create)

The loop `for mid in match_ids: meta = mdm.get_metadata(mid)` sits inside one try; first failing shard aborts enumeration at iteration 0, `except Exception: logger.debug` hides it, report prints `Complete matches: 0, Incomplete: 0` and still PASSes.

- [ ] Test: monkeypatch `get_match_data_manager` → manager whose `list_available_matches` returns [m1, m2, m3] and `get_metadata` raises for m1, returns complete-meta for m2, incomplete for m3. Assert `report.complete_matches == 1`, `report.incomplete_matches == 2` (failed item counted incomplete), and a `logger.warning` fired (caplog).
- [ ] Fix: keep outer try for the import/manager acquisition; move per-item body into inner `try/except Exception` that logs `warning` with the match id and counts the item incomplete. Raise outer log from debug→warning.
- [ ] Gate + commit `fix(nn): OI-1 per-item match-completeness enumeration in data_quality`.

### Task 2: F-0018 — baseline fusion layers return only empirical keys

**Files:**
- Modify: `Programma_CS2_RENAN/backend/processing/baselines/pro_baseline.py:275-279` (delete demo-layer HARD merge), `:321-324` (delete CSV-layer HARD merge), `:138` (bonus: `c.player_id if c.player_id else c.name` → drop `.name` fallback, skip card with warning — ProPlayerStatCard has no `name`)
- Test: `Programma_CS2_RENAN/tests/test_baselines.py` (add `TestFusionLayerPriority`)

Fusion base already starts from `dict(HARD_DEFAULT_BASELINE)` (line 68), so layer-internal merges only clobber earlier empirical layers (e.g. hard `rating_impact` 1.10 overwrites CSV's empirical Impact whenever demo layer is active).

- [ ] Test A: monkeypatch `_load_pro_from_csv` → `{"rating_impact": {"mean": 1.4, "std": 0.2}}`, `_load_pro_from_demo_stats` → `{"rating": {"mean": 1.0, "std": 0.1}}` (no rating_impact), `_load_pro_from_db` → None. Assert fused `rating_impact.mean == 1.4` (CSV survives demo layer).
- [ ] Test B (unit on real loader): fixture in-memory DB with ≥10 PlayerMatchStats pro rows lacking utility fields → `_load_pro_from_demo_stats()` result contains NO `utility_blind_time`/`rating_impact` keys (only its 7-8 empirical keys).
- [ ] Fix: delete both internal merges; `_provenance` unchanged; log lines updated (counts). Bonus `:138` guard.
- [ ] Gate + commit `fix(baselines): F-0018 fusion layers emit empirical keys only`.

### Task 3: F-0019 — percent→ratio normalization + sanity band

**Files:**
- Modify: `pro_baseline.py:296-335` (`_load_pro_from_csv`: divide percent columns by 100), `Programma_CS2_RENAN/backend/processing/validation/sanity.py:22-29` (LIMITS headshot_pct → (0.0, 1.0)) and `:75-83` (extend P-SAN-01 self-heal to headshot_pct, mirror kast branch)
- Test: `Programma_CS2_RENAN/tests/test_spatial_and_baseline.py` (extend), `test_baselines.py`

CSV percent columns: `KAST`, `Headshot %` (HLTV publishes percent; baseline keys avg_kast/avg_hs are ratio). Mirror stat_fetcher.py:588-593 pattern (`/100.0`). Values already ≤1.5 in a column → treat as ratio (per-column max>1.5 heuristic → percent), so a hand-made ratio CSV isn't double-divided; log the interpretation.

- [ ] Test A: `_load_pro_from_csv` on tmp CSV with `KAST=71.2, Headshot % = 46.3` rows → `avg_kast.mean ≈ 0.712`, `avg_hs.mean ≈ 0.463`.
- [ ] Test B: ratio-styled CSV (KAST=0.71) → unchanged (no double division).
- [ ] Test C: sanity strict mode flags `headshot_pct=37.0` as out-of-band; trim/self-heal converts `>1.0` headshot_pct to ratio with warning (caplog), mirroring P-SAN-01.
- [ ] Gate + commit `fix(baselines): F-0019 percent/ratio coherence in CSV layer and sanity band`.

### Task 4: OI-7 — thin-baseline minimum

**Files:**
- Modify: `pro_baseline.py:220-221` (bare `10` → named constant `MIN_DEMO_BASELINE_ROWS = 30`, module top, with comment: 10 rows = one 5v5 match → std collapse/z inflation; 30 ≈ three matches minimum)
- Test: `test_baselines.py`

- [ ] Test: fixture DB with 10 pro rows → `_load_pro_from_demo_stats()` returns None; with ≥30 rows → returns dict.
- [ ] Gate + commit `fix(baselines): OI-7 raise thin-baseline activation floor to 30 rows`.

### Task 5: F-0020 — elite CSV recreation path (owner: "recreate the CSVs")

**Files:**
- Create: `tools/build_elite_csvs.py` (generator; dry-run default, `--apply` writes)
- Modify: `Programma_CS2_RENAN/backend/processing/external_analytics.py` (drop dead `maps_statistics.csv`/`weapons_statistics.csv` loads — zero consumers repo-wide; make `analyze_user_vs_elite` degrade per-component instead of all-or-nothing on players_df columns)
- Create: `Programma_CS2_RENAN/data/external/README.md` (what each CSV is, which source regenerates it, exact command)
- Test: `Programma_CS2_RENAN/tests/test_elite_csv_builder.py`

Reality (recon): all 7 CSVs absent and gitignored; hltv_metadata.db here has 0 rows (populated copy lives on the Linux box: ~161 stat cards). Honest regenerability: `all_Time_best_Players_Stats.csv` + `top_100_players.csv` from ProPlayerStatCard (Name←nickname via ProPlayer join, Rating1.0←rating_2_0, K/D←kpr/dpr, ADR←adr, Headshot %←headshot_pct×100, KAST←kast×100, Impact←impact; top-100 = rating-sorted head with `CS Rating`←rating_2_0 — no Wins/Total_Matches fabrication, so consumer must not require Win_Rate); `match_players.csv` + `tournament_advanced_stats.csv` from monolith pro PlayerMatchStats (adr/deaths/kills/rating/hs per match; accuracy/econ_rating aggregates; utility_value←unused-utility-derived if present else omitted); `cs2_playstyle_roles_2024.csv` NOT regenerable (no role source) → generator skips it loudly, `get_player_role` already degrades to "Unknown".

- [ ] Generator: reads both DBs read-only (`mode=ro&immutable=1`), writes only with `--apply`, per-file skip-with-reason when source empty; percent-styled columns written ×100 (the Task-3 loader normalizes back — document this pairing in both files).
- [ ] `analyze_user_vs_elite` re-shape: compute `z_scores` (match_players_df) and `tournament_z_scores` (tournament_df) independently; `elite_rating_avg` from players_df `CS Rating` alone when present; `Win_Rate` optional (only derived if Wins/Total_Matches both exist).
- [ ] Tests: builder against tmp fixture DBs (2 stat cards, 12 match rows) → CSVs written with exact expected headers; EliteAnalytics loads them → is_healthy True, z-scores non-empty; missing-source → skip + warning; per-component degradation asserted.
- [ ] Add row to docs/OPEN_ISSUES.md §3: run `tools/build_elite_csvs.py --apply` on the Linux data box.
- [ ] Gate + commit `feat(analytics): F-0020 elite CSV builder + per-component elite degradation`.

---

### Task 6: F-0017 — heatmap dead Kivy surface + C-03 single-flip alignment

**Files:**
- Modify: `Programma_CS2_RENAN/backend/processing/heatmap_engine.py`
- Test: `Programma_CS2_RENAN/tests/test_heatmap_projection.py` (new; existing coverage is import-smoke only in `test_drift_and_heuristics.py:236-251`)

Recon facts: forward projection double-flips Y (line 79 `meta.pos_y - y` + line 81 `(1.0 - ny)`), in BOTH `generate_heatmap_data` and `_positions_to_grid` (:176-189). The reverse projection in `_extract_hotspots` (:259-264) is symmetric, so hotspot world coords are currently correct — flipping forward without reverse moves every hotspot. Dead surface (zero consumers repo-wide): `HeatmapData`, `generate_heatmap_data`, `create_texture_from_data`, `generate_heatmap_texture`, `DifferentialHeatmapData.rgba_bytes` + `diff_matrix` + the whole RGBA colorize block (:200-219). Sole production consumer: `coaching_service.py:889` → `.hotspots` only. C-03 doctrine: `backend/processing/tensor_factory.py:634-648` `_world_to_grid` (single flip: `ny = (meta.pos_y - y) * scale; gy = ny * res`).

- [ ] Delete dead: `HeatmapData` dataclass, `generate_heatmap_data`, `create_texture_from_data`, `generate_heatmap_texture`, RGBA build; `DifferentialHeatmapData` keeps only `resolution` + `hotspots`.
- [ ] Align `_positions_to_grid` to C-03: `gy = (ny * resolution)` (drop `1.0 -`), and `_extract_hotspots` reverse to `ny = gy / resolution; wy = meta.pos_y - ny * inv_scale` (drop `1.0 -`), keeping round-trip identity.
- [ ] Tests: (a) grid/tensor-factory convention parity — a world point with y > pos_y-center maps to the same row band as `TensorFactory._world_to_grid`; (b) hotspot round-trip: inject a hot cluster at a known world coord, assert extracted hotspot within one cell of it (this passes before AND after — proves the flip alignment kept world coords); (c) removed names no longer importable.
- [ ] Update the 3 observability/README mentions ONLY if they reference deleted names (grep `generate_heatmap_texture` in Programma_CS2_RENAN READMEs — EN only; IT/PT are R10).
- [ ] Gate + commit `refactor(processing): F-0017 heatmap C-03 single-flip + dead Kivy surface removal`.

### Task 7: F-0021 — deception flash-baits: honest input contract

**Files:**
- Modify: `Programma_CS2_RENAN/backend/analysis/deception_index.py:101-134`
- Test: `Programma_CS2_RENAN/tests/test_game_theory.py` (extend; R4 pins at :1044/:1091 must stay green)

Recon reframe: production `tick_data` rows are PlayerTickState-shaped — NO `event_type` column, so `_detect_flash_baits` already returns 0.0 always; the `player_blind`-keyed path can only ever fire on synthetic test data, where CS2 demos would yield the degenerate 1.0. Fix = honest contract, not full event rewiring (event-stream plumbing is the R9 Phase-6 wiring decision):
- [ ] `_detect_flash_baits`: when `event_type` column absent → return 0.0 AND log debug once ("no event stream — flash-bait dark"). When present: replace dead `player_blind` key with the real signal available in tick rows — count a flash effective when any enemy row within `FLASH_BLIND_WINDOW_SECONDS` has `is_blinded == True` (column exists, db_models.py:198); keep `flashbang_throw` filter for event-shaped input; delete the all-bait `return 1.0` branch (no blinds ⇒ all thrown flashes ineffective is only claimable when a blind signal EXISTS in the frame — otherwise 0.0 honest-dark).
- [ ] Tests: event-shaped frame with is_blinded transitions → bait rate in (0,1); frame with flashes and zero blind signal columns → 0.0 not 1.0; PlayerTickState-shaped frame → 0.0.
- [ ] Gate + commit `fix(analysis): F-0021 flash-bait detection keys on real blind signal, honest-dark otherwise`.

### Task 8: F-0028 — hybrid engine dead inference removal

**Files:**
- Modify: `Programma_CS2_RENAN/backend/coaching/hybrid_engine.py` (delete `_get_ml_predictions` :411-447, the `ml_predictions` threading at :324/:332/:494/:550/:641, honest module+class docstrings: RAG + baseline-Z engine; JEPA contributes via JEPAInsightAdapter 26-HYB-01)
- Test: `Programma_CS2_RENAN/tests/test_hybrid_engine.py` (update any test touching `_get_ml_predictions`)

Owner decision 2026-08-21: remove dead inference. Zero behavior change (outputs never consumed); saves a full model forward per insight call.
- [ ] Delete + docstrings + `_calculate_confidence` doc line ("ML confidence" → "|z| signal").
- [ ] Gate + commit `refactor(coaching): F-0028 remove dead ML inference from hybrid engine, honest docs`.

### Task 9: F-0031 — utility analysis fed from RoundStats

**Files:**
- Modify: `Programma_CS2_RENAN/backend/services/analysis_orchestrator.py:739-758` (derive utility keys before the gate)
- Test: `Programma_CS2_RENAN/tests/test_analysis_orchestrator.py` (extend)

Recon: `player_stats` never carries `*_thrown` in production; RoundStats DOES have per-round `flashes_thrown`/`smokes_thrown` (+ `he_damage`/`molotov_damage`) populated by round_stats_builder. `_analyze_utility` gains a fallback: when the 4 `*_thrown` keys absent, aggregate from RoundStats for (player, demo): `flash_thrown=Σflashes_thrown`, `smoke_thrown=Σsmokes_thrown`, `flash_damage/smoke_damage` absent→0, `he_grenade_damage=Σhe_damage`, `molotov_damage=Σmolotov_damage`; he/molotov thrown-counts genuinely unavailable → leave 0 (honest absence — utility analyzer already handles per-type zero). `rounds_played=count(RoundStats)`. Keep existing dict path first (tests feed it).
- [ ] Tests: seeded tmp-DB RoundStats rows → `_analyze_utility` emits flash/smoke effectiveness insight; empty RoundStats + bare stats → [] as today.
- [ ] Note in OPEN_ISSUES→R9: full Phase-6 wiring (game_states producer, tick_rows producer) remains a product decision post-retrain; `_analyze_strategy`/`_analyze_win_probability`/`_analyze_economy` stay dark pending it (no producer writes `game_states` anywhere today).
- [ ] Gate + commit `fix(services): F-0031 utility analysis derives throw counts from RoundStats`.

### Task 10: F-0011 — logging: one handler per process, per-role file

**Files:**
- Modify: `Programma_CS2_RENAN/observability/logger_setup.py:175-210`, `Programma_CS2_RENAN/core/lifecycle.py:launch_daemon` (env `CS2_LOG_ROLE=daemon`), `Programma_CS2_RENAN/run_worker.py` + `Programma_CS2_RENAN/hltv_sync_service.py` (set role at entry)
- Test: `Programma_CS2_RENAN/tests/test_observability.py` (extend; keep TestGetLoggerIdempotent green)

Design: handlers attach ONCE to the shared parent logger `cs2analyzer`; `get_logger(name)` returns child with `propagate=True` and NO own handlers (non-`cs2analyzer.*` names get the same treatment via a module-level `_ensure_root_handlers()`); filename = `cs2_analyzer.log` for the app process, `cs2_analyzer_<role>.log` when env `CS2_LOG_ROLE` set (daemon/worker/hltv_sync) → each process owns its rotating file exclusively; LS-01 fallback retained.
- [ ] Tests: two `get_logger` names → exactly one RotatingFileHandler total (on parent); `CS2_LOG_ROLE=daemon` (monkeypatch env + reset module state) → file name `cs2_analyzer_daemon.log`; records from child propagate into the file.
- [ ] `lifecycle.launch_daemon`: `env["CS2_LOG_ROLE"] = "daemon"`; worker/hltv entries: `os.environ.setdefault("CS2_LOG_ROLE", "worker"/"hltv_sync")` before first `get_logger`.
- [ ] Gate + commit `fix(observability): F-0011 single-handler logging with per-process log files`.

### Task 11: OI-8 — demo archive out of $HOME

**Files:**
- Modify: `Programma_CS2_RENAN/backend/storage/storage_manager.py:26-62` (+`archive_demo`)
- Test: `Programma_CS2_RENAN/tests/test_storage_manager_archive.py` (extend), `test_config_resolution.py` guards stay green

Recon: `DEFAULT_DEMO_PATH` defaults to `~` → `~/ingested/` archive + `rglob` over the whole home tree (the F-0008 anti-pattern; StorageManager bypasses `get_pro_demo_base`'s never-$HOME rule). `DEMO_ARCHIVE_PATH` config key exists but is unused.
- [ ] Fix: when `DEFAULT_DEMO_PATH` is unset/`~`-equivalent or configured path missing → `self.local_path = Path(DATA_DIR) / "demos"` (managed, created), never bare `~`; honor `DEMO_ARCHIVE_PATH` in `archive_demo` when set (falls back to `<ingest>/ingested` so the rglob-exclusion contract at :203-210 still holds — when DEMO_ARCHIVE_PATH points elsewhere the exclusion is unnecessary).
- [ ] Tests: unset settings → local_path under DATA_DIR, not home; DEMO_ARCHIVE_PATH set → archive lands there; default → `ingested/` sibling as before (existing test).
- [ ] Gate + commit `fix(storage): OI-8 archive/ingest default under managed DATA_DIR, honor DEMO_ARCHIVE_PATH`.

### Task 12: #28.2 + #28.4 — final broad-except narrowing (#28.3 closes as already-done)

**Files:**
- Modify: `Programma_CS2_RENAN/core/session_engine.py:54` (`(OSError, ValueError)`), `:341` (stays broad + comment: demoparser2 boundary, F-0006 class — narrowing would re-open PanicException hole), `Programma_CS2_RENAN/core/lifecycle.py:56` + `:191` (`(ImportError, OSError)`)
- Test: `Programma_CS2_RENAN/tests/test_session_engine.py`, `test_lifecycle.py` (add: stdin-monitor ValueError path sets shutdown event; POSIX lock branch fail-closed on OSError — the currently-untested branches)
- Modify: `TASKS.md` #28 queue rows (28.2 → DONE with the 6-site disposition; 28.3 → DONE "already satisfied by F-0006 — demoparser2 exports no typed exceptions, guard is BaseException+is_parse_error by design"; 28.4 → DONE)

Recon: daemon top-levels (B/D/E/F) must stay broad (crash-contain); heartbeat/state-writes already narrowed in prior campaigns; TASKS counts were stale (6 remain, not 20).
- [ ] Gate + commit `fix(core): #28 broad-except closeout — narrow stdin monitor + POSIX lock paths, document daemon boundaries`.

### Task 13: OI-2 — match_date provenance (code + migration + backfill tool)

**Files:**
- Create: `alembic/versions/a7b8c9d0e1f2_add_match_date_source.py` (down_revision `f6a7b8c9d0e1`; additive nullable `match_date_source: str` on `playermatchstats`, server_default `'ingested_at'`; pattern-copy `a1b2c3d4e5f6_add_data_quality_to_playermatchstats.py`)
- Create: `Programma_CS2_RENAN/backend/ingestion/match_date_resolver.py` — `resolve_match_date(demo_name: str, dem_path: Path|None) -> tuple[datetime, str]`, ladder: filename `YYYYMMDD` token (conftest convention `<name>_<map>_<YYYYMMDD>`) → filename year prefix `^(\d{4})-` (populate_match_results convention, day=Jan 1 coarse) → dem file mtime → now(utc); source strings: `filename_date | filename_year | file_mtime | ingested_at`. (HLTV event-date rung is data-box-only — the backfill tool adds it where ProEvent rows exist.)
- Modify: `Programma_CS2_RENAN/backend/storage/db_models.py` (field `match_date_source: Optional[str] = Field(default="ingested_at")`), `Programma_CS2_RENAN/run_ingestion.py:555-561` (+`match_date=resolved, match_date_source=src`) and `:1513-1521` (`MatchMetadata.match_date=resolved`), `Programma_CS2_RENAN/ingestion/pipelines/user_ingest.py:42` (same), `Programma_CS2_RENAN/backend/nn/coach_manager.py:assign_dataset_splits` (after ordering: log WARNING with % of rows whose source is `ingested_at`/`file_mtime` — "chronological split is ingestion-ordered for these")
- Create: `tools/backfill_match_dates.py` (dry-run default, `--apply`; monolith backfill via resolver + optional HLTV `ProEvent.start_date` join on event-token; reports per-source counts; Linux data box)
- Test: `Programma_CS2_RENAN/tests/test_match_date_resolver.py` (ladder cases), extend `test_ingestion_pipeline.py` (persisted row carries filename-derived date+source), `test_coach_manager_flows.py` split-warning case

- [ ] TDD each piece; migration verified via `CS2_ALEMBIC_URL` throwaway DB upgrade+downgrade.
- [ ] OPEN_ISSUES §3: add "run tools/backfill_match_dates.py --apply on the data box, then re-run split assignment".
- [ ] Gate + commit `feat(ingestion): OI-2 true match-date resolution with provenance marker + backfill tool`.

### Task 14: #47 hardening — non-destructive HLTV schema reconciliation

**Files:**
- Modify: `Programma_CS2_RENAN/backend/storage/database.py:455-493` (`_reconcile_stale_schema`)
- Test: `Programma_CS2_RENAN/tests/test_hltv_table_registry.py` (extend)

Recon: current logic DROPS any HLTV table missing a model column — silent data wipe on additive model evolution (the class of loss that killed Phase-H1 tables). Full alembic adoption stays G7 (owner-sequenced); this closes the data-loss hazard now:
- [ ] Additive-only mismatch (model has extra columns; all existing columns still in model) → `ALTER TABLE ADD COLUMN` per missing column (SQLite-safe: nullable, no default expr) instead of drop; log info. Non-additive (typed/renamed/removed columns) → `ALTER TABLE x RENAME TO x_stale_<yyyymmddHHMMSS>` (preserve data) + recreate; orphan-purge loop skips `*_stale_*` names; loud warning naming the preserved table.
- [ ] Tests (tmp sqlite): additive add keeps rows; non-additive renames + preserves rows + recreates fresh; orphan purge still drops true orphans but never `_stale_` snapshots.
- [ ] TASKS #47 row: note hazard closed, alembic adoption remains G7.
- [ ] Gate + commit `fix(storage): #47 non-destructive HLTV schema reconciliation (add columns, preserve on mismatch)`.

### Task 15 — NN cluster (F-0023, F-0024, F-0025, F-0026, F-0029, #64 mechanical)

**15a F-0023** — `jepa_model.py:forward_vl` (:969-991) computes `concept_logits_scaled = concept_logits / temp` but keeps it LOCAL; `train_step_vl` (jepa_trainer.py:595-604) feeds the UN-scaled cosine logits to `vl_jepa_concept_loss` BCE → sigmoid confined to [0.269,0.731], τ gets zero gradient. Fix: return `"concept_logits_scaled"` from forward_vl; `train_step_vl` + `_resolve_concept_labels` operate on the scaled tensor. Tests: sigmoid(scaled logit at cosine=±1, τ=0.10) reaches ≥0.99/≤0.01 (covers label range); after one train_step_vl backward, `model.concept_temperature.grad is not None`. Keep `test_concept_loss_computation` green.

**15b F-0024** — `_run_epoch` (training_orchestrator.py:636-692) forwards `result` only to callbacks. Fix: accumulate `result.get("embedding_variance")` during train epochs; after the train `_run_epoch` call in `_run_epoch_loop` (:331), `if hasattr(trainer, "embedding_collapse_detector") and variances: trainer.embedding_collapse_detector.update(mean)` — `EmbeddingCollapseError` propagates (no catch in run_training). ALSO: `train_step_vl` return dict (jepa_trainer.py:610-616) lacks `embedding_variance` — add it (same `_log_embedding_diversity` on pred embeddings) or the default VL path stays unguarded. Regression: fake trainer emitting variance 0.0 → run_training raises EmbeddingCollapseError within 2 epochs; healthy variance → completes.

**15c F-0025** — `PlayerTickState` has NO team column → `getattr(item, "team", "CT")` at :1082-1099 (advantage) and :1552-1568 (role) is a constant "CT"; shard rows carry `team` ('CT'/'TERRORIST') and `knowledge.own_team` holds it (player_knowledge.py:328) at both call sites. Fix: promote `round_stats_builder._normalize_winner` (:63-79) to shared `core/team_codes.py:normalize_team` (round_stats_builder keeps an alias); orchestrator resolves side via `normalize_team(knowledge.own_team) or "CT"` and normalizes `p_team` inside `_compute_advantage`. Trap: shard supplies 'TERRORIST', code compares == "T"/"CT" — normalize BOTH sides. Tests: TERRORIST-teamed shard fakes → advantage < 0.5 when CTs dominate; `_classify_tactical_role` returns SITE_TAKE for a TERRORIST entry item; existing TestComputeAdvantage/TestClassifyTacticalRole stay green.

**15d F-0026** — training builds `TensorFactory(TrainingTensorConfig())` (64²) per batch (:835-841); inference: ghost_engine.py:92-94 `get_tensor_factory()` (128/224) and coach_manager.py:1296 `RAPStateReconstructor()` (None → singleton); the `tensor_config` hook (state_reconstructor.py:49-52, P-SR-02) has zero callers. Fix: pass `TrainingTensorConfig()` at both sites; orchestrator `save_nn` best+_latest branches add `extra_meta` keys `map_resolution`/`view_resolution` (additive — `_validate_loaded_meta` ignores `extra`). Tests: reconstructor built by coach_manager path has 64/64 config; ghost_engine factory config == TrainingTensorConfig; sidecar carries resolutions after save.

**15e F-0029** — adapter (`jepa_insight_adapter.py:load_jepa_for_insights`) arms on any loadable `jepa_brain` checkpoint; orchestrator pretrain saves have untrained coaching heads. Fix: orchestrator `save_nn` calls stamp `extra_meta={"head_trained": False, ...}` for jepa/vl-jepa (pretrain path never trains the head; True is written only by a future finetune promotion — no such path exists today, correct). Adapter: after `load_nn` succeeds, read sidecar `(meta.get("extra") or {}).get("head_trained")` (template: `_restore_best_val_from_sidecar`, training_orchestrator.py:190-213); not True → warn "F-0029: pretrain-only checkpoint (coaching head untrained) — insight adapter disabled" and cache None. Missing sidecar (legacy) → same refusal. Tests: sidecar head_trained False/absent → None + warning; True → armed. Existing test_jepa_insight_adapter mocks adjust.

**15f #64 mechanical** — the loud ValueError guard already ships (jepa_train.py:592-607); remaining semantic target design stays R9 (owner). Sweep closes the mechanical residue: (1) `test_jepa_training_pipeline.py` fixtures at :59-67 build `output_dim=metadata_dim` (25) models that cannot exist in production (CLI always OUTPUT_DIM=10) — repoint fixtures to `output_dim=10` and invert `test_matching_dims_pass_the_guard` (currently green-lights the wrong 25-target contract; a 10-dim y should pass the guard, 25-dim must raise); (2) contract test pinning `jepa_insight_adapter._TARGET_FEATURES == vectorizer.FEATURE_NAMES[:10]` — resolves the documented conflict with `MATCH_AGGREGATE_FEATURES[0:10]` (that list feeds AdvancedCoachNN via `_calculate_deltas`, a different model; document at both sites); (3) TASKS#64 row → note guard shipped + fixtures fixed + design decision = the only residue (R9).

- [ ] TDD per sub-task; each its own commit (`fix(nn): F-00xx …`).

### Git-flow closeout (owner order 2026-08-21)

When Task 16 gates are green: push branch → `gh pr create` (Problem/Solution/Verification/Risk body) → wait CI green (poll `gh pr checks`) → `gh pr merge --rebase --delete-branch` → `git checkout main && git fetch --prune && git reset --hard origin/main` → delete local branch. Repo returns to exactly one branch. The ~210 foreign IT/PT README working-tree edits stay uncommitted and untouched.

### Task 16: Ledger + docs closeout

- [ ] TASKS.md: #38 → DONE (2026-08-03 rescrape applied, acceptance passed), #65 → DONE (PR #46 hflayers pin), #28 queue statuses (Task 12), #47 note (Task 14). No other row edits.
- [ ] docs/OPEN_ISSUES.md: rewrite — §1 fixed (OI-1/OI-2 code side), §2 fixed rows annotated `fixed@<sha>` or moved to a "closed by sweep" list, §3 Linux data-box checklist (OI-3..6, OI-9 + backfill + build_elite_csvs runs), §4 pointers refreshed, R9/R10/#67/G7 deferrals stated.
- [ ] Full gates: suite ≥ baseline, `tools/headless_validator.py` exit 0, black/isort touched files, `sync_integrity_manifest.py` (package files changed), dead_code_detector clean.
- [ ] Push branch, open PR (body: Problem/Solution/Verification/Risk; list of finding IDs closed), report PR URL + the Linux-box run list.
