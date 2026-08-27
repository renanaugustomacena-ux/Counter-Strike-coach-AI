# Cluster 15 — tools (root + Programma)

Scope: all scripts under `tools/` (repo root, incl. `fuzz/` and the `.js` file), all scripts under `Programma_CS2_RENAN/tools/`, plus `docs/tooling/generate_zh_pdfs.py`. Read 2026-08-28.

## Files read

- [x] tools/headless_validator.py
- [x] Programma_CS2_RENAN/tools/backend_validator.py
- [x] tools/verify_all_safe.py
- [x] tools/eval_harness.py
- [x] Programma_CS2_RENAN/tools/Goliath_Hospital.py
- [x] Programma_CS2_RENAN/tools/_infra.py
- [x] tools/mine_shard_strategies.py
- [x] tools/mine_coaching_experience.py
- [x] tools/ingest_pro_demos.py
- [x] tools/seed_hltv_top_n.py
- [x] tools/seed_hltv_apply_vision.py
- [x] tools/hltv_stealth_init.js
- [x] Programma_CS2_RENAN/tools/seed_hltv_top20.py
- [x] tools/repair_equipment_value.py
- [x] tools/repair_kast.py
- [x] tools/repair_ratings.py
- [x] tools/repair_tick_features.py
- [x] tools/flag_ghost_players.py
- [x] tools/purge_default_stats_rag.py
- [x] tools/rebuild_monolith.py
- [x] tools/wipe_for_reingest_safe.py
- [x] tools/reset_pro_data.py
- [x] tools/Feature_Audit.py
- [x] tools/Sanitize_Project.py
- [x] tools/audit_binaries.py
- [x] tools/dev_health.py
- [x] tools/audit_scanner.py
- [x] tools/backfill_match_dates.py
- [x] tools/build_elite_csvs.py
- [x] tools/build_pipeline.py
- [x] tools/build_web.py
- [x] tools/coach_answer_eval.py
- [x] tools/d3_recover_shard_metadata.py
- [x] tools/d4_disk_hygiene_audit.py
- [x] tools/db_health_diagnostic.py
- [x] tools/dead_code_detector.py
- [x] tools/drift_detector.py
- [x] tools/gen_design_tokens.py
- [x] tools/merge_demo_pool.py
- [x] tools/migrate_db.py
- [x] tools/observe_training_cycle.py
- [x] tools/policy_runner.py
- [x] tools/populate_match_results.py
- [x] tools/populate_round_stats.py

- [x] tools/refresh_compose_digests.py
- [x] tools/refresh_model_pins.py
- [x] tools/rescrape_placeholder_pros.py
- [x] tools/run_console_boot.py
- [x] tools/sbom_generator.py
- [x] tools/sync_pro_players.py
- [x] tools/test_rap_lite.py
- [x] tools/test_tactical_pipeline.py
- [x] tools/tick_census.py
- [x] tools/ui_fixtures.py
- [x] tools/ui_gallery.py
- [x] tools/ui_screenshot.py
- [x] tools/validate_coaching_pipeline.py
- [x] tools/verify_lock_hashes.py
- [x] tools/verify_main_boot.py
- [x] tools/portability_test.py
- [x] tools/README.md / README_IT.md / README_PT.md
- [x] tools/fuzz/fuzz_demo_parser.py
- [x] tools/fuzz/__init__.py
- [x] tools/fuzz/README.md / README_IT.md / README_PT.md
- [x] Programma_CS2_RENAN/tools/Ultimate_ML_Coach_Debugger.py
- [x] Programma_CS2_RENAN/tools/aggregate_match_stats_sql.py
- [x] Programma_CS2_RENAN/tools/build_tools.py
- [x] Programma_CS2_RENAN/tools/context_gatherer.py
- [x] Programma_CS2_RENAN/tools/db_inspector.py
- [x] Programma_CS2_RENAN/tools/demo_inspector.py
- [x] Programma_CS2_RENAN/tools/migrate_hltv_schema_2026_05.py
- [x] Programma_CS2_RENAN/tools/project_snapshot.py
- [x] Programma_CS2_RENAN/tools/register_orphan_matches.py
- [x] Programma_CS2_RENAN/tools/repair_rating_scale.py
- [x] Programma_CS2_RENAN/tools/sync_integrity_manifest.py
- [x] Programma_CS2_RENAN/tools/ui_diagnostic.py
- [x] Programma_CS2_RENAN/tools/user_tools.py
- [x] Programma_CS2_RENAN/tools/__init__.py (empty)
- [x] Programma_CS2_RENAN/tools/README.md / README_IT.md / README_PT.md
- [x] docs/tooling/generate_zh_pdfs.py

## Tool inventory

### tools/headless_validator.py (2914 lines)

Read-only regression gate (~15-20s, no GUI). Imports ~290 production modules across 26 banner phases (42 distinct check phases incl. sub-phases), exit 0 PASS / 1 FAIL (warnings allowed). Not importable — raises ImportError unless `__main__` (headless_validator.py:69-72). Detects optional deps (kivy, ncps+hflayers for RAP) and downgrades those checks to warnings (:50-54, :2049). Enforces: METADATA_DIM==25, INPUT_DIM==METADATA_DIM, OUTPUT_DIM==10, NUM_COACHING_CONCEPTS==16, HIDDEN_DIM==128, RAP_POSITION_SCALE==500.0; 19 expected DB tables; checkpoint-name map (jepa→jepa_brain etc. :1315-1330); TRAINING_FEATURES == FeatureExtractor.get_feature_names(); integrity-manifest hash sampling with CRLF→LF normalization (:2268); security scans (torch.load must pass weights_only=True :2289, no subprocess shell=True, no eval/exec, no bare except, no hardcoded secrets); design-token freshness via subprocess `gen_design_tokens.py --check` and `--web --check` (:2777-2821). Cites R4 MED (a formerly no-op drive-letter check, fixed :993-999) and F-0005 (qss template contract :1743-1749). Phase 19 does not exist — numbering jumps 18→20 (:2194).

### Programma_CS2_RENAN/tools/backend_validator.py (606 lines)

Runtime backend gate v3.0, merges/supersedes Clinical_Integration_Validator (MCIV v2.0) + system_audit_suite (Deep Audit v4.0) (backend_validator.py:2-13). Uses shared `_infra.BaseValidator`. 7 sections against the LIVE DB (calls `init_database()` :117 — creates tables if absent, so not purely read-only): env deps (psutil/sklearn/demoparser2/sqlmodel), SELECT 1 + `PRAGMA journal_mode`==wal, 6 required tables, CoachState query smoke, backup recency <7d (warn), model zoo forward passes (default 25→4, jepa, vl-jepa 16 concepts, role_head softmax sums to 1), analysis modules by "Prop" number (Prop 5-12: chronovisor, belief calibrator, engagement range, dialogue, temporal decay, format adapter), coaching pipeline (CoachingService COPER, ExperienceBank, KnowledgeRetriever), resource integrity (PHOTO_GUI, models dir, settings, map_config, manifest freshness <168h warn, checkpoint freshness <30d warn), service health (hltv_sync.pid liveness via psutil, Windows Run-key `MacenaCS2Analyzer_HLTV` auto-start registration :559-583, sqlmodel>=0.0.14). F8-16 comment: model-zoo checks are load/run smoke with torch.randn, not correctness (:216).

### tools/verify_all_safe.py (164 lines)

Meta-gate: dynamically discovers every `tools/**/*.py` and executes each as a subprocess (120s timeout, `--test-only` injected for build_pipeline.py), skipping "unsafe" tools by filename convention. F-0039 doctrine (:68-92): the original six unsafe prefixes (fix_/reset_/migrate_/patch_/cleanup_/force_) missed 13 tools whose bare invocation mutates live data — worst case rebuild_monolith, whose delete-first/bulk-insert-last phase left pro stats EMPTY when the 120s timeout killed it mid-run. Now also skips repair_/flag_/purge_/mine_/populate_/rebuild_/observe_/ingest_/wipe_ prefixes plus run_console_boot.py, sanitize_project.py (confirm-prompt blocks non-interactive), fuzz_demo_parser.py (30-min budget guarantees timeout-fail). Tools that are dry-run-by-default (rescrape_/sync_/merge_/seed_/d3_/d4_) stay scheduled. Venv guard exits 2 unless in venv or CI env var set (:8-10). Exit 0 all green / 1 any failure.

### tools/eval_harness.py (742 lines)

GAP-04 offline pre-retrain measurement. Writes timestamped append-only JSON to `reports/` (no overwrite :696-699); `--dry-run` prints report shape and skips ALL heavy sections (B6.2 fix — dry-run is a shape probe, uniform skip rule :648-690). Sections, each independently degrading to NOT_AVAILABLE/ERROR: (1) feature drift — TickFeatureDriftMonitor fit on first 20% of a demo's playertickstate ticks (needs ≥500, cap 50k), z-threshold 2.5; (2) RAG recall@{1,5,10} self-retrieval + kNN purity k=5 over coachingexperience embeddings (reuses ExperienceBank._deserialize_embedding to handle legacy JSON + base64 float32, AC-32-01 :168-169; GAP-09: SELECTs only 3 columns to survive pre-migration DBs :183-189); (3) win-prob Brier + ECE (Naeini 2015) gated on `--win-prob-ckpt`, needs ≥50 RoundStats; (4) LLM A/B stub NOT_IMPLEMENTED (GAP-15 deferred); (5) Phase 7D embedding quality — silhouette (sklearn or hand-rolled cosine fallback) + per-dim std <0.1 collapse detection (VICReg target); (6) Phase 7B strategy label coverage, target ≥200 distinct labels; (7) Phase 7C MoE expert utilization — loads jepa_brain, counts routing on random input, balanced iff max<0.6 and min>0.1. Exit 0 report written / 2 only for pre-report failures. Read-only w.r.t. the DB.

### Programma_CS2_RENAN/tools/Goliath_Hospital.py (1127 lines)

"Hospital" diagnostic v3.0 on `_infra.BaseValidator`, 11 "departments" selectable via `--department`: ER (AST syntax on all source .py, forbidden patterns incl. hardcoded Desktop paths/passwords/api_keys, bare `from backend/core/ingestion` imports without Programma_CS2_RENAN prefix), Radiology (PHOTO_GUI themes cs2/csgo/cs16 with ≥5 assets, radar images for 7 required maps, .pt census), Pathology (mock-data indicator scan + live-DB count of player_name LIKE %test%/%mock%/%MCIV% — MCIV probes are treated as pollution), Cardiology (21 critical module files, DB SELECT 1, config, TemporalBaselineDecay weight range, 11 analysis factory callables — R4 LOW: factory failures now surfaced :618-619, ResourceManager stats, logger type, 4 control modules), Neurology (delegates: just instantiates UltimateMLDebugger), Oncology (deprecated patterns, 5+-line commented-out code blocks, >100-line functions with exclusion list; R4 MED: exclusion paths were POSIX so never matched on Windows until normalized :760-765), Pediatrics (files modified <1d/<7d — informational), ICU (24 import chains, CoachingService instantiation, FeatureExtractor+DB round-trip, all timeout-guarded daemon threads 10-20s), Pharmacy (critical + optional deps, requirements.txt), Tool Clinic (syntax + `__main__` guard + docstring on every tool in both tools/ dirs), Endocrinology (entry points — W3 replace-not-delete note: Kivy main.py is gone, Qt entry is apps/qt_app/app.py :1017-1018; alembic migration parseability; JSON configs; headless_validator parseability cross-ref). Read-only against the DB; runs live queries but writes nothing.

### Programma_CS2_RENAN/tools/_infra.py (442 lines)

Shared tool infrastructure: `require_venv()` exits 2 outside a venv unless CI env var (:30-43, venv named `cs2analyzer`); `path_stabilize()` — single canonical root resolution, inserts project root in sys.path, sets KIVY_NO_ARGS=1, reconfigures Windows stdout to UTF-8 (:51-81), executed at import time (:84); Severity enum (CRITICAL/ERROR/WARNING/INFO/HEALTHY); ToolResult/ToolReport — only CRITICAL/ERROR count as failures, WARNING/INFO are soft (:155-170); Console with ANSI color (R4 LOW: win32 color detection previously returned truthy str and leaked ANSI into CI logs, now requires TTY :250-256); BaseValidator ABC — standard args --verbose/--json/--quiet, define_checks() hook, exit 0/1, unhandled exceptions become a FATAL CRITICAL result (:363-368); `validate_tool_contract()` — every tool must have a `__main__` guard + parse cleanly.

### tools/mine_shard_strategies.py (1446 lines)

"Path B" strategy miner: reads ~270 per-match `match_*.db` shards (opened with `PRAGMA query_only=ON` :162), classifies every round into strategy labels across 5 families (economy/individual/setpiece/rotation/playbook — base + "Tier 1: 85 new labels" + Tier 2 cross-round/site/timing extensions), then bulk-inserts into monolith `coachingexperience` with strategy_label set. Key doctrine in comments: DP-06 SSOT — an earlier revision hardcoded the dead "New Volume" mount, turning the default run into a silent 0-shard no-op (:34-36); event round_number in shards is broken (always 1) so events map to rounds via tick bisection (:9-11, :253-257); 26-TICK — windows are SECONDS × per-shard match_metadata.tick_rate (validated to [32,256]), because old *_TICKS constants baked a 64-tick assumption halving windows on 128-tick shards (:47-55, :183-194), and one inline `64` had survived the sweep at the flash-assist window (:520-523). Winner inference heuristic: 5 CT dead→T, 5 T dead→CT, plant undefused→T, defused→CT, no plant→CT timeout (:294-307). Bomb sites classified by nearest K-means centroid (dust2/inferno/mirage only :59-63). Embeddings: SentenceTransformer all-MiniLM-L6-v2 (384-d) or hashed bag-of-words 100-d fallback (:1191-1237), serialized base64 float32. Rows carry confidence PRO_CONFIDENCE=0.7, mu_skill 25.0 / sigma 25/3 (TrueSkill prior). Safety rails: `--dry-run`, `--limit N`, dedup by md5 key; DESTRUCTIVE only under `--fresh`, which deletes `WHERE strategy_label IS NOT NULL` — comment records that a former blanket DELETE also destroyed mine_coaching_experience rows while claiming "miner rows" (:1424-1433).

### tools/mine_coaching_experience.py (237 lines)

"Path A" miner: scans monolith `roundstats` and emits CoachingExperience via ExperienceBank.add_experience() (embeddings/context-hash handled by the bank). Scenario rules with hardcoded delta_win_prob: opening_kill +0.15 / opening_death -0.15, ≥2 kills+win +0.25, traded death -0.05, eco (<2000, non-pistol) upset win +0.30, ≥50 nade damage + win +0.10 (:102-114). Idempotent by context_hash duplicate skip; `--dry-run` supported; confidence = PRO_EXPERIENCE_CONFIDENCE. DL-1: records lineage row (`batch_experience_mining`, processing_step=experience_mining) after insert (:224-232). Writes to the live DB (WAL, busy_timeout 30s).

### tools/ingest_pro_demos.py (231 lines)

One-shot pro-demo pipeline: discover .dem under `get_pro_demo_base()` (rejecting download-duplicate "(1)" folders :93-95), queue via run_ingestion._queue_files(is_pro=True), process, then retrain coach via CoachTrainingManager.run_full_cycle(). DESTRUCTIVE under `--full`: deletes ALL IngestionTask rows, all pro PlayerMatchStats, PlayerTickState scoped BY demo_name (comment: a former blanket DELETE destroyed the USER's tick data which pro re-ingest never recreates :137-140), and per-match shard DBs computed as sha256(stem)%2^63 (:154-165). Comment records removal of the old module-level monkeypatch that disabled duplicate-checking for everything in the interpreter, user demos included (:166-169). Incremental mode only clears queued/failed tasks whose file no longer exists. `--retrain-only` skips ingestion. No dry-run flag.

### tools/seed_hltv_top_n.py (631 lines)

Phase-1 HLTV seeder. SCOPE guard in docstring: touches ONLY hltv_metadata.db, never database.db — the two are independent (cites a memory file `feedback_hltv_db_is_separate.md` :4-6). Flow: FlareSolverr fetch of /ranking/teams → top-N teams → team pages → `.bodyshot-team` active-roster anchors (verified 2026-04-29; unfiltered scan used to return ~36 players/team; fallback capped at 7 = CS2 active-roster ceiling :190-216) → per-player stat fetch with retry/backoff; failures land in `reports/hltv_seed_<ts>/pending_vision.json` for the Phase-2 vision pass. Requires exactly one of `--dry-run` (no DB writes) or `--apply`; `--apply` runs a robots.txt/settings preflight unless `--skip-preflight` (:422-427). Freshness cache `--refresh-days` (default 7); default-stats sentinel cards are always re-fetched. Backfills ProPlayer.team_id post-fetch — the stats page doesn't expose team; documented incident: jL/19206 landed at mouz with team_id=NULL and was unrouteable from the pro-baseline merger (:500-506). Doctrine §111/§112/§115/§116/§117/§121 explicitly cited (:34-43). Reports written atomically via tmp+os.replace. "Owner-authorized only: ~150 live HLTV calls, ~1-4h wall-time" (:30-32).

### tools/seed_hltv_apply_vision.py (325 lines)

Phase-2 vision-fallback writer, hltv_metadata.db only. Takes stats extracted out-of-band (vision LLM reading puppeteer-mcp screenshots — flow documented :28-38) either as single-player CLI (`--player-id --stats-json/--stats-file`) or `--batch` JSON list. Validates 8 required fields; rejects all-zero stats ("would recreate the default sentinel", §117 :107-112); normalizes KAST from percent to ratio; warns on rating outside [0.3, 2.0]. Idempotent upsert of ProTeam/ProPlayer/ProPlayerStatCard (§115). Batch continues past per-entry failures, exit 1 if any failed / 2 for a bad file.

### tools/hltv_stealth_init.js (135 lines)

Best-effort runtime stealth payload for puppeteer-mcp `puppeteer_evaluate` after navigation: masks navigator.webdriver/plugins/languages, fakes window.chrome, patches permissions.query and WebGL vendor/renderer, strips lingering Cloudflare challenge widgets. Honest limitations block: cannot defeat the FIRST-load Cloudflare challenge (real stealth needs evaluateOnNewDocument at launch time); useful mainly to make screenshots readable for the vision-LLM; fall back to FlareSolverr when "Just a moment..." persists (:24-46). Notes one-time `npx puppeteer browsers install chrome` prerequisite (verified missing 2026-04-29 :12-22).

### Programma_CS2_RENAN/tools/seed_hltv_top20.py (1455 lines)

Static (no-network) seeder for hltv_metadata.db: hardcodes the March-2026 top-20 team table (Vitality #1 ... Aurora #20), 100 players with hltv_id/real_name/country/team_id, and PLAYER_STATS for ~40 players "from HLTV top 20 articles & web sources", period 2025. Players without an entry get DEFAULT_STATS — an "average T2 pro" baseline rating 1.02 (:1267-1278), flagged `[est.]` in output; detailed_stats_json records source/period/rank provenance. V-2 FIX comment: KAST/HS%/opening-duel normalized from percent to ratio at write time (:1363-1377). Upserts (no deletes); no dry-run flag but idempotent; writes only the HLTV DB. Note: DEFAULT_STATS has opening_duel_win_pct already as ratio 0.49 while PLAYER_STATS uses percents — the >1.0 normalization handles both. Data is a hand-curated snapshot that will silently go stale; seed_hltv_top_n.py is the live-scrape successor. Its DEFAULT_STATS placeholder is the root cause of the CHAT-06 RAG-pollution incident (see purge_default_stats_rag.py).

### tools/repair_equipment_value.py (189 lines)

Destructive fixer for a specific incident: 8 hardcoded demos (falcons-vs-parivision, furia-vs-*) had equipment_value=0 in playertickstate ("from tick census" :25-35). Re-parses .dem via demoparser2 (current_equip_value), batch-UPDATEs by rowid where equipment_value=0, 50k-row chunks, 200MB SQLite cache. Only touches rows that are currently 0. Post-run verification prints %-non-zero per demo with OK/STILL BROKEN. DL-1 lineage recorded per demo. No dry-run.

### tools/repair_kast.py (133 lines)

Recomputes avg_kast in playermatchstats (pro rows) from roundstats binary K/A/S/T flags, replacing the inflated estimate_kast_from_stats() approximation (~0.91 avg → expected ~0.70-0.75 :5-8). Joins on LOWER(player_name). Prints before/after aggregate + bucket distribution. `--dry-run` supported; DL-1 lineage `batch_kast_repair`.

### tools/repair_ratings.py (100 lines)

Fixes PlayerMatchStats rows with rating=0.0 caused by NaN sanitized to 0.0 (:5-7). Recomputes via compute_rating_components() SSOT — docstring codifies the RAW-components contract: baseline normalization happens only inside the `rating` aggregate, never in `rating_*` columns (:9-11). Rating clamped [0,5]. Ghost players (all-zero stats) skipped; repaired rows demoted data_quality complete→partial (:79-80). DL-1 lineage. No dry-run.

### tools/repair_tick_features.py (198 lines)

Repairs 4 dead tick features mis-ingested from demoparser2: is_crouching (real field "ducking"), is_blinded (flash_duration>0), has_helmet/has_defuser (columns never written :5-9). Temp-table + UPDATE FROM per demo; never deletes rows (safe for roundstats/KAST linkage). Two doctrine comments: ANTI-FABRICATION — a field the parser did not return is excluded from the UPDATE, never defaulted, else a whole demo gets fabricated zeros (:121-123, :139-144); and the temp-table index is mandatory — without it the UPDATE FROM planned "SCAN r" = O(demo×temp), measured runaway >40min/days-scale on the 429M-row monolith (:164-167). Join is LOWER(TRIM()) because the monolith stores original-case names — an exact join silently skipped ~half the monolith (:48-51). DL-1 lineage per demo. No dry-run.

### tools/flag_ghost_players.py (67 lines)

Sets sample_weight=0.0 on pro PlayerMatchStats rows with avg_kills=avg_deaths=avg_adr=0 (coaches/spectators/standins). Doctrine: excluded from pro baseline, training selection and z-scores but NOT deleted — tick data retained for lineage (:9-14). Idempotent (filters sample_weight>0). Mutating, no dry-run.

### tools/purge_default_stats_rag.py (123 lines)

One-shot cleanup for the CHAT-06 incident (tracked TASKS#34, AUDIT §8.6): pro_demo_miner had embedded seed_hltv_top20 DEFAULT_STATS placeholder cards into `knowledgeentry`, so RAG retrieval returned 24 different pros with byte-identical stats (:1-9). Finds default-stats players via the `_is_default_stats_card` sentinel in the HLTV DB, deletes TacticalKnowledge rows whose title matches "Pro baseline: {nick}" / "Opening duels: {nick}" prefixes. `--dry-run` supported; idempotent; deletes from the main DB.

### tools/rebuild_monolith.py (1066 lines)

Rebuilds monolith playertickstate/playermatchstats from per-match shard DBs without re-parsing .dem files (except the match-stats phase). The F-0039 poster child (delete-first/bulk-insert-last). Phases via `--phase`: full (tick+stats+linker), tick-only (D1), match-stats-only, linker-only, enrich-only (D2B). `--source match-dbs` synthesizes demo paths from match_metadata.demo_name so matches without surviving .dem still migrate (D1 :195-226). Destructive behavior: `--full` DELETEs all playertickstate first (:339-345); the stats phase always deletes all pro PlayerMatchStats before re-parsing (:556-564). Bulk-write posture: synchronous=OFF, 2GB cache, 4GB mmap, index drop/recreate cycle (post-R4 indexes included in the cycle :132-141). D1 safety rails: JSON checkpoint file with completed/errors/in_progress for kill-resume (:246-288), disk-pressure abort default 50GB free (:229-243, sized for the ~414M-row migration), periodic `wal_checkpoint(TRUNCATE)`, `--match-id`/`--limit` slicing, and a MANDATORY `d_track_running` lock (blocks hltv_sync_service concurrent writes per docs/concurrency_policy.md) with `--no-lock` escape hatch (:927-942). steamid forwarded per migration d4e5f6a7b8c9 so identity survives nickname collisions (:43-45); legacy tables missing it get None not NaN (:468-472). D2B enrichment: 14 Class B fields from enrich_from_demo; failures tag data_quality full_sql_dem_unreadable/_partial rather than fake values; 4 fields knowingly left at defaults (accuracy, clutch_win_pct, positional_aggression_score, unused_utility_per_round :677-679). map-SSOT CP0 #2: the old 8-entry map copy missed train/cache/office (:143-144).

### tools/wipe_for_reingest_safe.py (541 lines)

The gold-standard destructive tool. Doctrine §57 Least Privilege, §60 Incident Response as Design Input; control C-WIPE-01, SOP SECURITY/WIPE_RUNBOOK.md (:4-6). Successor to deleted wipe_for_reingest_v1-v4. Safety generation: dry-run is DEFAULT; `--confirm-wipe` mandatory to mutate; refuses to wipe without `--snapshot` or an explicit `--no-snapshot` waiver (:469-475); HMAC-SHA256-sealed snapshot tarball (MACWIPEv1 format, key from CS2_WIPE_SNAPSHOT_KEY env/keyring; Fernet AEAD deferred to Phase 2 to avoid adding the cryptography dep mid-ingestion :154-175); JSONL audit log of every invoke/refuse/complete/fail in logs/wipe_audit_*.jsonl (operator = USER or USERNAME, else Windows operators would all log as "unknown" :232-234); DB-unlock preflight — on Windows via rename-onto-itself because psutil open_files handle enumeration hard-crashed the tool's own preflight with an uncatchable access violation (:73-99). Wipes 5 tables (playermatchstats, playertickstate, roundstats, coachinginsight, ingestiontask) + VACUUM; `--mode swap` raises NotImplementedError (v4 algorithm never ported :280-285). Restore path verifies HMAC, allowlists tar members, deletes current WAL/SHM sidecars before extract (else SQLite replays the post-snapshot WAL over the restored DB, silently mixing two states :330-334), extracts with filter="data".

### tools/reset_pro_data.py (713 lines)

The most destructive tool in the repo: clears database.db data tables (17-table FK-ordered list), resets the CoachState singleton to Paused/Idle, optionally wipes hltv_metadata.db (`--wipe-hltv`; `--preserve-hltv` is DEFAULT — HLTV data comes from scraping, not demos :227-228), clears knowledge_graph.db, hltv_cache.db, deletes ingestion/cache/*.mcn, .validated_cache.json, hltv_sync_state.json, PID/stop files, ALL match_data/*.db* shards, and ALL model checkpoints (*.pt in models/global|user|master_user), then VACUUMs and runs an 8-phase verification. PlayerProfile is never cleared ("belongs to the user, not pro data" :214). delete_rows() is gated by a frozen table allowlist (:83-112). W3 safety retrofit (CP0 #6): "this tool deletes MORE than wipe_for_reingest_safe yet had none of its safety generation" — dry-run now default, `--execute` required, sqlite-API backup of database.db taken first unless `--no-backup` (:636-650, :588-608). Venv guard; interactive y/N unless `--yes`.

### tools/Feature_Audit.py (208 lines)

"MTS-IS" feature-alignment auditor (rich-based). Compares ProDataPipeline.feature_cols (what the "ML Brain" expects) against parser output: static mode uses a hardcoded 23-column set claimed to mirror the real parser (:77-101 — a drift risk since it is not derived from code), live mode (`--demo path.dem`) parses a real demo and diffs actual DataFrame columns. Reports MISSING (required by brain, absent in output) as CRITICAL / SURPLUS / ALIGNED. Read-only. Venv guard.

### tools/Sanitize_Project.py (198 lines)

"Privacy prep / distribution" destroyer: DELETEs database.db, hltv_metadata.db, hltv_sync.pid; CLEARs match_data/, models/, logs/ (:64-96). Rich table plan + interactive Confirm unless `-y/--yes` — this confirm is why verify_all_safe skips it (F-0039). SIGINT handler for clean abort. No backup, no dry-run flag beyond declining the prompt. Note it deletes the HLTV DB that reset_pro_data deliberately preserves by default.

### tools/audit_binaries.py (218 lines)

Post-build binary integrity locker: SHA-256 hashes every .dll/.pyd/.exe under dist/Macena_CS2_Analyzer (or dist/cs2_analyzer fallback, or an explicit dir) and writes `binary_integrity.json` manifest beside them. Returns success (not failure) when no build exists — "don't fail the pipeline in dev mode" (:107-115). Only artifact write; no source/DB mutation.

### tools/dev_health.py (115 lines)

Developer health orchestrator: always runs headless_validator (critical, fast-fail); default adds dead_code_detector `--strict` (critical since the 2026-07-17 orphan sweep established a Clean baseline — any regression is new dead code :21-27) and Feature_Audit (non-critical); `--full` adds portability_test (critical). `--quick` = headless only. Pure subprocess runner, read-only.

### tools/audit_scanner.py (466 lines)

Mechanical per-subsystem audit engine (the instrument behind the docs/audit campaign): module inventory + LOC, public-API extraction, import graph, caller map (grep-style "who imports this"), regex pattern violations (bare/broad except, print, logging.basicConfig, traceback.print_exc, TODO/FIXME/HACK), AST cyclomatic complexity (>10 flagged), test-coverage map by filename convention, missing public docstrings. Emits JSON or markdown, optional `--output`. Read-only. Minor: the ast.With branch in complexity counting is a no-op by construction (:145-153).

### tools/backfill_match_dates.py (149 lines)

OI-2 fixer: every historical PlayerMatchStats.match_date was ingestion wall-clock (no writer ever set it), so the "chronological" split was really ingestion-ordered (:1-6). Resolves real dates per demo via the match_date_resolver ladder plus an HLTV ProEvent rung using exact unique slug containment only — "never a guess" (:76-83). Provenance discipline: only rows with source 'ingested_at'/NULL are upgraded; a real source is never overwritten by a weaker one (:44-47). Dry-run default; dry-run opens the DB `mode=ro&immutable=1` explicitly to avoid creating -wal/-shm side files on the monolith (:100-103). Aborts with pointer to alembic migration a7b8c9d0e1f2 if the column is missing. Docstring: after applying, re-run split assignment.

### tools/build_elite_csvs.py (220 lines)

F-0020: regenerates the gitignored `data/external/*.csv` elite-comparison reference files lost with the original datasets — "honestly: files whose source data does not exist are SKIPPED with a reason, never fabricated" (:5-7). Sources: hltv_metadata.db stat cards → all_Time_best_Players_Stats.csv + top_100_players.csv; monolith pro playermatchstats → match_players.csv + tournament_advanced_stats.csv; cs2_playstyle_roles_2024.csv NOT regenerated (no role data anywhere); maps/weapons statistics were dead loads removed from EliteAnalytics (:17-20). F-0019 pairing: Headshot%/KAST written percent-styled x100 (HLTV convention), loader normalizes back (:22-24). utility_value column omitted — "no honest source anywhere" (:189-190). Dry-run default, `--apply` to write; read-only immutable connections on both DBs; needs ≥2 rows per file (loader minimum).

### tools/build_pipeline.py (233 lines)

"Industrial Build Pipeline v2.0": stages = Sanitize_Project --yes → pytest → sync_integrity_manifest → clean dist/build → PyInstaller (cs2_analyzer_win.spec/cs2_analyzer.spec) → audit_binaries. Carries the F-0040 doctrine at :145-148: sanitization is DESTRUCTIVE and is NEVER run in `--test-only` mode — the old stage order wiped live data on --test-only, and verify_all_safe's special-cased `--test-only` run made that wipe deterministic on every sweep. So --test-only = tests + manifest only. shell=False with shlex splitting.

### tools/build_web.py (142 lines)

Builds the P4 web marquee sub-apps (tactical-viewer, match-detail, coach-chat) via pnpm workspace: install-once, `pnpm build` per app, idempotent freshness check (dist/index.html mtime vs src/). Copies PHOTO_GUI/maps radar PNGs into tactical-viewer/dist/maps (source of truth shared with the Qt-native viewer :61-70). Exit 2 = pnpm missing/workspace not scaffolded, 1 = build failure. Non-destructive.

### tools/coach_answer_eval.py (330 lines)

GAP-15 / TASKS#48 LLM answer-quality eval: builds fixture questions from LIVE DB ground truth (top-kill round drill-down, ambiguous team pairing that must surface multiple candidates, free-choice narration, player-stats grounding), asks them through the real CoachingDialogueEngine (full pipeline: tools, retrieval, disambiguation, prompt rules — not the LLM in isolation :7-9), scores groundedness = fraction of expected DB facts present. Anti-typography measures: Unicode dash folding (:183-190) and ≥80%-token fuzzy fact matching because LLMs paraphrase demo names (:196-216); free-choice scored by ROSTER CLUSTERS — ≥3 same-demo player names proves a real match was narrated (:131-134). Requires Ollama reachable (exit 2 otherwise); `--dry-run` builds/prints fixtures only. Writes reports/coach_answer_eval_UTC.json. Read-only on DB.

### tools/d3_recover_shard_metadata.py (546 lines)

D3 recovery for corrupted per-match shards (missing match_metadata). Embeds the §129 5-question doctrine check in the report header (:7-12, :482-488). Classification: SHA-256 forward map (demo stem → match_id) built from monolith + on-disk .dem names, intra-shard map-name validation, buckets RECOVERABLE_FULL / NAME_ONLY (deferred to M2 re-ingest) / UNRECOVERABLE (NO_SHA256_MATCH, MATCH_ID_INTEGRITY_FAIL, MAP_MISMATCH). Anti-fabrication rules: tick_rate read from the .dem header only, validated [32,256] per GAP-01/P-RSB-05 — "recovery must never fabricate a rate (26-NORM-01: a 64.0 written for a 128-tick demo silently halves every time window)" (:49-57); team names/scores get honest "unknown"/0 sentinels since inventing "Team 1"/"Team 2" is indistinguishable from data (:139-141); rows without a header rate get parser_version 'v2-d3-recovered-default-rate' so they stay findable/repairable (:125-128, :145-147). `--rederive-v1` fixes the 2026-05-06 run's HARDCODED 64.0 rows (:317-327). Dry-run default, `--apply` backs up shards first, INSERT-only (DELETE reverses), idempotent skip if metadata exists. DP-06 note again: earlier revision hardcoded the dead "New Volume" mount (:31-33). The one-shot inventory input was removed 2026-08-21; without it only --rederive-v1 remains operational (:460-469). Report notes record is_pro_match=0 as a known systemic misset (203-shard pattern, V-phase fix :495).

### tools/d4_disk_hygiene_audit.py (272 lines)

Read-only disk-hygiene inventory: (1) per shard, tick parity vs monolith → KEEP / RM_AFTER_BACKUP (only on exact tick parity + present in monolith) / INVESTIGATE (more ticks in source, or missing counterpart); (2) startup backups retention scoring — keep 3 most recent + 1 per calendar month for 6 months, older = PRUNE_PER_RETENTION_POLICY. "NO files are deleted. The owner runs any deletion themselves" (:14-16). Writes docs/match_db_audit_TS.json with per-file recommendations and reclaimable-bytes summary.

### tools/db_health_diagnostic.py (585 lines)

10-section DB health diagnostic, read-only. Anti-stale doctrine: table names, expected columns, valid statuses and rating bounds are DERIVED from the live SQLModel classes, never hardcoded (:1-51). Sections: schema census (cols/FKs/indexes/rows/PK), PRAGMA integrity_check on main+HLTV plus 5-shard spot check ("full check is very slow on external SSD" :197), WAL/journal/synchronous modes, consistency (duplicate (demo,player), orphan playertickstate vs matchresult, impossible values, model-vs-DB schema drift, dataset_split & is_pro distributions), ingestion pipeline (status distribution, stuck 'processing' tasks, cross-DB match-file vs MatchResult orphans both directions), index coverage + EXPLAIN QUERY PLAN full-scan detection on 3 critical queries, observability metadata coverage (timestamp/source columns per table), HLTV DB census, CoachState ML readiness dump, storage summary. Table-name identifier regex guard against SQL injection into PRAGMAs (:70-81). Note: the shard spot-check queries `playertickstate` inside shards (:205) but shards actually use `matchtickstate` — that tick count will read N/A.

### tools/dead_code_detector.py (582 lines)

Three-phase static hygiene gate wired into dev_health as critical: Phase A orphan modules (conservative substring usage scan; entry points and __init__.py exempt; `# no-dead-code` opt-out marker; rglob over tools/ because fuzz_demo_parser.py is launched by fuzz-nightly.yml and glob-only coverage flagged it as orphan :32-35; the vendored `caveman` plugin dir excluded — 125+ false positives on the 2026-07-02 baseline, TASKS#57 :77-80), Phase B duplicate class/function definitions (INFO only; huge COMMON_NAMES allowlist of dunders/lifecycle/interface names :91-266), Phase C stale imports (AST Name-usage vs imports; R4 MED — original `alias not in content` could never be True because the import line contains the alias, so Phase C reported nothing ever; now tests content minus import lines :484-491; honors `# noqa: F401` re-export markers; `import a.b` binds `a` per R4 MED :448-450). Orphans AND stale imports flip the verdict; `--strict` exits 1 (W3 note: Kivy main.py replaced by apps/qt_app/app.py in ENTRY_POINTS :24-27). Read-only.

### tools/drift_detector.py (272 lines)

Doctrine §63 Infrastructure as Security Primitive; control C-DRIFT-01. SHA-256 manifest of `Programma_CS2_RENAN/**` vs a baseline at SECURITY/drift_baseline.json; `--baseline` writes, default verifies; exit 1 on drift with pointer to SECURITY/INCIDENT_RESPONSE.md IR-02/IR-05. Excludes runtime/user artifacts (DBs, match_data, checkpoints — "tracked separately via integrity_manifest", logs, secrets.vault, .master_key.bin :39-57). Phase 1 skeleton: baseline does not ship yet; Phase 3 will have the installer ship a signed baseline and app startup re-verify as a RASP event (:8-11). Writes only the baseline file when asked.

### tools/gen_design_tokens.py (446 lines)

Design-token codegen: design/tokens/design-tokens.json (SSOT) → Python frozen dataclass (qt_app/core/design_tokens.py) and, with `--web`, a TypeScript mirror (web/shared/tokens.ts). Byte-identical output on unchanged input so pre-commit and headless_validator Phase 25 can diff regenerations (:4-7). Field mapping is explicit, no auto-derivation — a JSON key rename must consciously update the generator (:16-21). Modes: default write, `--check` (exit 1 if stale — the freshness gate), `--stdout`. Handles DTCG `$value` leaves. 46 per-theme fields x 3 themes (CS2/CSGO/CS1.6) + 21 global scale fields.

### tools/merge_demo_pool.py (192 lines)

Merges a secondary pro-demo pool into the primary: identity = Path.stem case-insensitive, same semantics as run_ingestion's canonical three-tier dedup (:3-6). Duplicates (stem in PlayerMatchStats OR target dir) are DELETED from source to reclaim drive space; unique files MOVED to target; files <10MB (DS-12) skipped. Dry-run by default, `--execute` to touch the filesystem; refuses source==target. Destructive on the source pool only under --execute.

### tools/migrate_db.py (255 lines)

DEPRECATED (R2-11) — superseded by `alembic upgrade head` (migrations 8c443d3d9523 + 3c6ecb5fe20e). Direct invocation prints the deprecation notice and exits 0 via an early `__main__` block at :30-35, making the entire migrator class below unreachable when run as a script (the trailing main() at :253 never executes). Retained as archive for pre-Alembic DBs: would add 5 CoachState columns with a VACUUM INTO backup first (NN-82 — consistent snapshot under WAL, :106-127).

### tools/observe_training_cycle.py (570 lines)

End-to-end observed training diagnostic mapped to the Book-Coach-1.md pipeline diagram (Acquisizione→Elaborazione→Addestramento→Osservatorio→Conoscenza :4-5). Phase 1 data discovery (tick counts per demo, split distribution, the critical check that TRAIN split demos actually HAVE tick data, flags UNASSIGNED pipeline gaps); Phase 2 FeatureExtractor.extract_batch on 100 real ticks (shape==METADATA_DIM, NaN/Inf, all-zero dead-feature columns); Phase 3 model-zoo instantiation; Phase 4 a REAL 1-epoch JEPA training run through TrainingOrchestrator with an observer callback capturing per-batch losses — this trains and checkpoints for real (why verify_all_safe skips the observe_ prefix); Phase 5 checkpoint + TensorBoard artifact census; Phase 6 knowledge-state counts (coachingexperience, tacticalknowledge, coachstate). Final gap analysis names the known failure mode "_fetch_jepa_ticks() returns empty" when TRAIN has no ticks (:556).

### tools/policy_runner.py (688 lines)

Doctrine §54 Policy as Code Law: "every rule is executable, waivers are time-bound" (:14). Discovers SECURITY/policies/*.yaml, evaluates rule kinds line_regex / text_regex / yaml_walker (minimal JSONPath subset) / file_compare (regex-extract equality across two files) / ast_walker (Phase 2 stub — emits an info "not yet implemented, needs libcst" violation :492-500). Waivers from SECURITY/waivers.yaml with schema validation, rule+path-glob+snippet matching; EXPIRED waivers fail the strict gate (:678-682). Inline waiver markers per policy. HARD_EXCLUDES defense-in-depth so a misconfigured policy can't walk .git/.venv (:53-69). Exit: 0 warn-mode; 1 strict with unwaived error-severity violations or expired waivers; 2 malformed policy/waiver. Read-only.

### tools/populate_match_results.py (259 lines)

Populates MatchResult from demo_name parsing + roundstats outcomes, one row per demo (event_name='demo:STEM'). ANTI-FABRICATION doctrine at :81-87: nothing in the DB links a starting side to the team NAMES parsed from the filename (that mapping lives only in the .dem scoreboard, which this tool does not open) — an earlier revision guessed winner=team_a whenever CT-start won, "a coin flip recorded as fact". Outcome is therefore reported per starting side only (CT_start/T_start/draw); team names stay in map_picks JSON strictly as filename metadata. Score = max round_won across each starting-side group ("a full-match player's round_won count IS the team score; substitutes undercount" :122-126). Idempotent by event_key; `--full` deletes and rebuilds only demo:% rows. Writes to matchresult.

### tools/populate_round_stats.py (287 lines)

Populates roundstats from .dem files via round_stats_builder.enrich_from_demo AND fixes Q1-02: the enrichment dict was previously discarded (`_, round_stats_dicts = ...`), leaving 11 playermatchstats enrichment columns 0.0 across all rows — now captured and UPDATEd per (demo, player) (:11-17, :234-260). Enrichment-key→column mapping imported from the builder module — single source of truth shared with ingestion (F6-19 :77-82). equipment_value backfilled from first tick per player/round via MIN(tick) GROUP BY trick (:90-107). Case-insensitive player match (builder lowercases, monolith stores raw case — exact match silently skipped every mixed-case player :251-253). INSERT OR IGNORE idempotent; `--full` deletes per-demo before re-insert. Deadlock doctrine: record_lineage uses a separate SQLAlchemy session, so the raw conn MUST be committed first or the two connections deadlock, especially on NTFS (:218-222).

### tools/refresh_compose_digests.py (229 lines)

Doctrine §53 Software Supply Chain Is the Core Asset; control C-DOCK-01. Rewrites docker-compose.yml `image: repo:tag` lines to `repo@sha256:digest` form, resolving via `docker manifest inspect --verbose` or skopeo. Modes: `--dry-run` default, `--apply`, `--check` (exit 1 while any tag pin remains). Phase 1 scaffold: today's compose still tag-pins flaresolverr v3.4.6; Phase 2 flips to digest pins (:11-14). Adds a `# was: repo:tag` traceability comment above each rewritten line. Only writes the compose file under --apply.

### tools/refresh_model_pins.py (194 lines)

Doctrine §53; control C-MOD-01. Pins HuggingFace model revisions + per-artifact SHA-256 (model.safetensors, config, 3 tokenizer files) into core/integrity_manifest.json `models` block; the app is meant to refuse to load a model whose artifact hashes mismatch (:14-16). Registry currently one model: sentence-transformers/all-MiniLM-L6-v2 (the RAG SBERT). `--check` exits 1 if any default model is unpinned; refresh path validates the revision is a 40-hex SHA and refuses to save incomplete pins (:176-181). Phase 1 scaffold — rag_knowledge.py enforcement lands Phase 2 (:17-21).

### tools/rescrape_placeholder_pros.py (192 lines)

GAP-06: re-scrapes the 24 DEFAULT_STATS placeholder ProPlayerStatCard rows written by seed_hltv_top20 fallback (RAG mining skips them since the CHAT-06 fix 2026-04-19, but coaching coverage suffers :5-10). Reuses HLTVStatFetcher.fetch_and_save_player (throttle lives in the fetcher, 2-7s jitter — no double-throttle :12-15). Safe-by-default: dry-run default, `--apply` = owner-authorized live calls with robots.txt preflight unless `--skip-preflight`, `--limit N` resume-friendly, idempotent upsert. Post-run verification re-reads each card and warns if it STILL matches the sentinel; acceptance gate per TASKS#38 = purge_default_stats_rag --dry-run reports 0 (:32-36). Exit 1 if any fail or still-default.

### tools/run_console_boot.py (166 lines)

Console boot-sequence validator: boots the Unified Console via get_console().boot(), waits 5s, validates get_system_status() structure — 9 required top-level keys, state value derived from the actual SystemState enum ("never hardcode" :26-28), per-service status against ServiceStatus enum + PID type, storage tier sizes, baseline block (mode in temporal/legacy/unavailable). Always attempts graceful console.shutdown() in finally. Skipped by verify_all_safe as interactive/long-running — boot has real side effects (services spawn).

### tools/sbom_generator.py (215 lines)

Doctrine §53; control C-SC-06. CycloneDX 1.6 SBOM: `--from-env` (importlib.metadata scan of the active env, transitives included) or `--from-lockfile` (name==version parse). Stamps project name/version from pyproject.toml, git commit as a property, purl per package. Falls back to a minimal-but-valid emitter without cyclonedx-bom. Phase 1 standalone; Phase 2 wires into `goliath.py sbom` + CI release step; verification pairing: `pip-audit --strict --vulnerability-service osv` (:27-28). Write-only to the output file.

### tools/sync_pro_players.py (145 lines)

GAP-05: purges stale ProPlayer/ProPlayerStatCard/ProTeam rows from the MAIN DB — the canonical pro reference lives ONLY in hltv_metadata.db; main DB links via PlayerMatchStats.pro_player_id → ProPlayer.hltv_id as a cross-DB logical reference with no FK (:3-10). Current known state: 2 stale seed rows (zywoo=11893, s1mple=7998) from early testing. Dry-run default; `--apply` takes a timestamped file-copy backup `database.db.pre_gap05_<ts>` first unless `--skip-backup` (AUDIT §8 CHAT-06 pattern); deletes ALL rows of the three tables in main DB, asserts 0 after. Idempotent no-op at 0 rows.

### tools/test_rap_lite.py (89 lines)

RAP-Lite integration smoke: ModelFactory 'rap-lite' must use RAPMemoryLite (LSTM) not the full LTC+Hopfield memory; full forward contract of 7 output keys with exact shapes (advice_probs (B,10), belief_state (B,T,64), gate_weights (B,4), optimal_pos (B,3) finite = GhostEngine-compatible, value_estimate finite = ChronovisorScanner-compatible, attribution (B,5), hidden_state); checkpoint name 'rap_lite_coach'; asserts the JEPA pipeline is unaffected. Read-only, no DB.

### tools/test_tactical_pipeline.py (444 lines)

Headless end-to-end test of the Qt tactical-viewer pipeline on a REAL .dem (arg or first found in DEMO_PRO_PLAYERS/): Stage 1-2 DemoLoader.load_demo + output-shape validation (dict of (frames, events, segments) tuples per map); Stages 3-5 DemoFrame/GameEvent/segments typing + exhaustive attribute-access probes for the 21 player fields and 9 nade fields the Qt map_widget reads (None weapon/name flagged); Stage 6 PlaybackEngine seek/emit + forced mid-frame interpolation (probes p.is_ghost); Stage 7 SpatialEngine world_to_normalized with [0,1] range check + MapMetadata lookup; Stage 8 radar PNG resolution in PHOTO_GUI/maps; Stage 9 Qt-free render simulation (rotation = 90 - yaw, Team/NadeType enums, 3-coord trajectory points). Collects ALL errors instead of dying on the first; exit 1 on any error. Read-only.

### tools/tick_census.py (239 lines)

Full-corpus tick-quality census over monolith playertickstate in 100k rowid chunks: per-demo and global zero-rate for 17 audited columns mapped to their indices in the 25-dim feature vector (comment: has_helmet/has_defuser exist since the D-4 indexes and were backfilled by repair_tick_features 2026-07-17 — "auditing them is the point" :29-32). Binary/low-frequency features (crouch/scope/blind/bomb/helmet/defuser) exempt from the >90%-zero CRITICAL "dead dimension" flag; statuses HEALTHY/WARN/DEGRADED/CRITICAL. Emits per-issue repair recommendations grouped by column — this census is what produced repair_equipment_value's 8-demo AFFECTED list. Read-only.

### tools/ui_fixtures.py (1319 lines)

Frame-realistic fixture payloads for the screenshot harness — numbers mirror the design atlas (design/frames/): 47 personal demos, belief 73%, last match de_mirage rating 1.34 etc. (:1-6). Injection philosophy: calls the screens' OWN signal-handler slots ("the same ones their ViewModels emit into — no DB, no backend, no monkeypatching" :6-8). Encodes the FIELD-GAP doctrine throughout: fixture keys that the real payloads lack (clutches_won, demo_size_mb, pro_teams, batch progress, ghost divergence fields per Locked Decision 8 :1183-1186, tactical scoreboard/bomb/death attribution) carry "the names the payload WOULD use" so defensive rendering paths get exercised. Deterministic math notes: 47-row performance history sums to avg exactly 1.08 with last-5 = 1.17 (:582-587); documents where the design frame itself is internally inconsistent (utility percentages 1 point off "the frame is internally inconsistent there" :626-630). Tactical fixture inverts MapMetadata.world_to_radar for de_mirage to convert frame pane px→world coords (:833-841); walks macena/niko along frame-13 trails through the real InterpolatedFrame path so trail deques fill correctly; ghost variant disconnects the Ghost checkbox from the VM so the harness flip stays torch-checkpoint-free (:1257-1266); pro_comparison unhooks VM signals so a late DB worker can't clobber injected state (:1302-1311); tactical injection nulls _loaded_demo_stem during load so no real chronovisor scan wipes the injected stars (:1284-1291). Read-only w.r.t. project data.

### tools/ui_gallery.py (289 lines)

Offscreen component-gallery renderer (QT_QPA_PLATFORM=offscreen): composes every shared UI primitive (buttons, StatusChip, StatBadge rating-color bands >1.10 green / 0.90-1.10 yellow / <0.90 red, ProBadge, 4-severity Toasts, EmptyState, ProgressRing 48-128px, SkeletonCard, ChatPanel per frame 07, DriversList, TipBox, NumberedStep, DbRecordCard, MonoFooter) with frame-realistic sample copy per theme, grabs to docs/ux-audit/renders-atlas/THEME/gallery{,_chat}.png. Reuses ui_screenshot's settle/wait helpers. Writes only PNGs.

### tools/ui_screenshot.py (198 lines)

Offscreen screenshot harness: boots ONLY the presentation layer (ThemeEngine + MainWindow + qt_app._create_screens) — "never starts backend services, the Session Engine daemon, SBERT downloads, or AppState polling — safe on any machine, including CI" (:3-6). MACENA_UI_ANIMATIONS=0 for deterministic end-states. 15 screens; `--themes`, `--no-fixtures` (natural cold-start state), `--collapse-nav`, `--md-tab` (per-tab suffixed grabs), `--variant` (inject_<screen>_<variant> lookup, e.g. tactical_viewer ghost), `--size`. _settle() drains QThreadPool worker signals BEFORE fixture injection so fixture state wins deterministically (:49-63); _wait() spins the loop so fade-ins finish before grab. Writes only PNGs. This is the render-eyeball instrument the "visible runtime testing" feedback memory requires.

### tools/validate_coaching_pipeline.py (253 lines)

"Proves the product works" end-to-end: .dem → parse_demo → ensure PlayerProfile (creates a temporary one so the _is_profile_ready coaching gate passes :10-12) → sanitize+clamp and UPSERT PlayerMatchStats (is_pro=False) → pro_baseline deviations → generate_corrections → ExplanationGenerator narratives with SkillAxes categorization. PASS requires ≥1 insight AND ≥10 total words, else exit 1 with the raw corrections dumped for triage (:203-214, :243-248). WRITES to the live DB (profile + match stats) — a validator with side effects.

### tools/verify_lock_hashes.py (249 lines)

Doctrine §53; control C-SC-03; policy POL-DEPS-01. Verifies every requirements-lock*.txt line is `name==version` exact-pinned AND paired with ≥1 `--hash=sha256:` continuation; permitted directives -r/-c/--index-url/--extra-index-url/--find-links. Phase 1: hashed lockfiles don't exist yet (`uv pip compile --generate-hashes` will produce them post-ingestion), so `--allow-empty` exists; Phase 2 makes it a CI gate (:18-22). Exit 0/1/2. Read-only.

### tools/verify_main_boot.py (177 lines)

Headless Qt-app structure dry-run (no display server): entry point qt_app.app.main callable; MainWindow public interface (register_screen/switch_screen/screen_changed/set_wallpaper); NAV_ITEMS 4-tuples with non-empty shortcuts (nav rework contract); screen modules AUTO-DISCOVERED from the filesystem, all must import; theme validation post-F-0005 — per-theme .qss files are gone, base.qss.template is the sole stylesheet source rendered via qss_generator per theme, rendered QSS must be ≥200 chars and contain real Q-selectors for all 3 themes (:129-161). Read-only.

### tools/fuzz/fuzz_demo_parser.py (268 lines)

Doctrine §64 Testability and Continuous Verification; control C-SBX-02. Coverage-guided Atheris fuzzer for demoparser2 with 70%-probability `PBDEMS2\x00` magic prefix inputs (≤64KiB); gracefully degrades to a deterministic seeded random-input loop when Atheris is absent (:16-21). Default budget 1800s (why verify_all_safe skips it — guaranteed 120s timeout). Crash inputs saved as `<sha256-16>-<size>.dem` + .meta under .fuzz/crashes for stable IDs; `--reproduce <path>` replays one input (exit 1 if it reproduces). Launched by fuzz-nightly.yml CI (per dead_code_detector comment). Writes only fuzz artifacts.

### tools/portability_test.py (1573 lines)

Self-styled "DOCTORATE-LEVEL / 1000% Portability Certification" suite, 10 tests: (1) hardcoded-path regexes (drive letters, /home, /Users, /tmp, /var...) with layered exemptions — comments/docstrings, ACCEPTABLE_PATTERNS (pathlib/os.path/get_setting), `# PORTABILITY_OK` marker, regex-literal skip, and a backwards-walking platform-guard detector for `if os.name == 'nt'` blocks (:433-449); (2) path-construction analysis — f-string paths without Path, with an elaborate false-positive filter (URLs, ANSI codes, logging, pathlib `/` operator, real-backslash-after-escape-stripping :364-431); (3) import safety — AST top-level Call detection outside functions/`__main__`, filtered by a ~150-entry SAFE_IMPORT_PATTERNS allowlist (:179-336 — an allowlist this large is itself a maintenance smell), plus unguarded win32/winreg/pwd/grp imports = CRITICAL; (4) config portability (DATABASE_URL hardcoded-path check, env-var usage); (5) required files; (6) critical-module imports; (7) env-var fallback + hardcoded-secret scan; (8) resource path construction (warn-only); (9) cross-platform (CRLF info, shell=True warn, unguarded windows commands); (10) requirements.txt (file:// refs CRITICAL, dev versions, unmarked platform deps). Certification = all tests passed (criticals only fail; warnings never do). `--save-report` writes portability_report.json. Read-only. Wired into dev_health --full as critical.

### tools/README.md + README_IT.md + README_PT.md

English README (updated 2026-08-03): inventory of 49 tools, names headless_validator the "mandatory pre-commit regression gate" (Rule 3 Zero-Regression, Rule 6 Change Governance), accurately describes 42 check phases with Phase 19 unused, the 5-stage build pipeline, migrate_db as DEPRECATED, and warns Sanitize_Project is destructive. IT/PT versions (last touched 2026-07-21) are STALE TRANSLATIONS describing a fictional structure: "26 fases" with a phase table that never matched the code (claims Black/isort formatting checks, circuit-breaker phase numbering), migrate_db described as an ACTIVE "safe wrapper around Alembic — safer than alembic upgrade head" (the opposite of deprecated), db_health sections invented (connection-pool health, Alembic status), Sanitize described as removing user_settings.json (it doesn't).

### tools/fuzz/README.md + README_IT.md + README_PT.md + __init__.py

English fuzz README matches the code: deliberately bypasses the app's DS-12 pre-validation gates to test the layer BEHIND them; crash artifacts stay local, nightly CI via fuzz-nightly.yml; "do not disable MIN_DEMO_SIZE because the fuzzer passes". IT/PT again stale: claim the fuzzer targets parse_demo() with `--iterations`/`--report` flags that do not exist (real flags: --time-budget/--seed/--reproduce), claim the pre-validation gate itself is part of the surface under test (English explicitly says the opposite). __init__.py: 3-line package marker citing C-SBX-02 / IR-02.

### Programma_CS2_RENAN/tools/Ultimate_ML_Coach_Debugger.py (530 lines)

9-phase "neural falsification tool" on BaseValidator (v2.0), delegated to by Goliath Neurology: (1) data fidelity row counts for a probe player (default MCIV_PROBE — the same sentinel Pathology flags as pollution); (2) belief stability — output variance under real ticks must stay < ML_BELIEF_VARIANCE_THRESHOLD (default 0.5), with R4 LOW fix: probe now runs on set_global_seed(42) because an unseeded random init made pass/fail flap between runs (:147-152); (3) decision traceability — ≥80% of CoachingInsight rows must link a demo_name; (4) model-zoo instantiation for all 6 types (RAP/RAP-Lite optional=warn) + legacy forward pass; (5) dimensional consistency (INPUT_DIM==METADATA_DIM, TRAINING_FEATURES length, OUTPUT_DIM==10); (6) data quality delegated to run_pre_training_quality_check in a daemon thread with 15s timeout; (7) weight health — NaN/Inf and dead neurons (<0.001 abs max) in saved checkpoints via weights_only=True load; (8) training convergence — overfitting = val_loss > train_loss*1.20 for 5 consecutive epochs, R4 MED fix: tracks the MAX streak, since the trailing streak reset on any non-divergent final epoch and mid-training divergence passed a guard labeled "max streak" (:446-459); (9) maturity — MaturityObservatory conviction state must not be "doubt"/"crisis". Read-only.

### Programma_CS2_RENAN/tools/aggregate_match_stats_sql.py (940 lines)

D2A: SQL-only PlayerMatchStats aggregator — computes the 25 Class-A fields from shards (matchtickstate + match_event_state) without .dem re-parse, UPSERTing rows tagged data_quality='full_sql'; the 11 Class-B fields stay 0.0 for D2B; Class-C is D2C/out-of-scope (§22.4). Rich doctrine: (a) deterministic 70/15/15 split via md5(demo_name)%100 — hashing on demo identity keeps a match's player rows in one split, no leakage (:111-123); (b) per-player totals MUST come from cumulative MAX(*_total) columns, NOT per-round counters, which undercount (measured: MAX(kills_total)=35 vs SUM(per-round)=17 on shard 910) — but per-round damage must come from damage_this_round since no damage_total exists (:206-213); (c) MR12 round-count sanity band [13,36]; the previous {16,24,30,36} CSGO-MR15 set mis-flagged 81% of CS2 demos as anomalous (2026-05-05 audit :59-68); (d) R4 HIGH 26-TICK: trade window derives from the per-demo GAP-01 tick_rate, not a hardcoded 64 that halved the real-time trade window on 128-tick demos (:354-364); (e) rating_* columns carry RAW components per the SSOT — a prior draft wrote baseline-normalized ratios and corrupted every downstream Z-score (:519-523); (f) impact_rounds = share of rounds with ≥1 kill, distinct from the HLTV rating_impact component ("conflating them was a bug" :536-539); (g) is_pro from path override because metadata.is_pro_match is unreliable (0 on a known Vitality pro match :558-561); (h) team names mapped from full 'TERRORIST'/'CT' strings — earlier draft compared two-letter codes that never appear (:331-334). Safety: dry-run DEFAULT, `--commit` requires the d_track_running lock, `--force` overwrites registered_only/partial (R4 MED: --force was previously a documented no-op — the write path never consulted it :899-908), `--really-force` overwrites 'complete' rows after a 5s countdown banner; `--reconcile` mode diffs fresh aggregates vs existing complete rows with 5% field tolerance and a 10%-of-rows halt threshold (§5 D2A.4), exit 2 on drift_detected. Noise filter for observer/caster/bot rows mirrors register_orphan_matches (R4 LOW: report used to hardcode rows_skipped_noise=0 :196-199).

### Programma_CS2_RENAN/tools/build_tools.py (405 lines)

Consolidated inner build pipeline v3.0 (merges build_pipeline, Build_Integrity_Verifier, Advanced_Build_Debugger). Subcommands: `build` (black --check + isort → pytest → alembic upgrade head → PyInstaller from packaging/cs2_analyzer_win.spec → multi-binary SHA-256 build_manifest.json), `verify` (forbidden-file scan of dist/ — *.db/*.dem/*.pt/user_settings.json/*.env/*.pem/*.key/*.log must NOT ship; manifest validity), `debug-build` (streams PyInstaller output through an error-pattern categorizer), `manifest` (delegates to sync_integrity_manifest). Carries the full F-0041 fix family in comments: (a) argv lists with shell=False — the old shell=True string broke on space-containing paths and was the repo's only B602; (b) verify's old single-binary manifest check could never pass after the multi-artifact fix; (c) the sync tool writes "hashes" not "files"; (d) --force now actually gates lint-failure continuation as its help text claims; (e) the real spec lives in packaging/ — "the old phantom spec name never existed after the packaging move; the tool could never build". R4 LOW: manifest was rewritten inside the loop so only the last artifact was attested (:148-150). Unlike root build_pipeline.py, this one does NOT run Sanitize first (non-destructive).

### Programma_CS2_RENAN/tools/context_gatherer.py (578 lines)

Developer context tool: for a file or dotted module, gathers file info, AST structure (classes/methods/functions), imports classified proj/std/ext, forward deps resolved to paths, reverse deps (substring scan with F8-11 honesty note: "substring matching creates false reverse deps from comments/strings — use dead_code_detector for accurate AST analysis" :289-291), related tests, last-5 git log (F8-34: list-args subprocess, timeout=10 :345-347), and public API signatures. Compact terminal format or --json. F8-25: unresolvable target returns exit 1 for calling scripts (:544). Read-only (runs `git log`).

### Programma_CS2_RENAN/tools/db_inspector.py (531 lines)

Compact DB diagnostics: connectivity + PRAGMAs, per-table row counts (whitelist-validated table names against injection :24-29), storage sizes (main/HLTV/match_data dir with min/max/avg shard size), ingestion status counts + oldest queued + last error, CoachState daemon panel — R4 MED: the real columns are hltv_status/ingest_status/ml_status (Hunter/Digester/Teacher); the old *_status keys never existed so every daemon displayed "?" (:213-219); R4 (W3): ingestion statuses are completed/failed — done/error never existed and permanently displayed 0, "project_snapshot had the fix" (:402-405); alembic version; dataset-split + pro/user distribution; `--table X` full schema detail (columns/PK/FK/indexes/rowcount). Calls init_database() (may create tables) but otherwise read-only. F8-23/F8-24: suppressed exceptions now logged.

### Programma_CS2_RENAN/tools/demo_inspector.py (346 lines)

Unified demo-probe tool, merges/supersedes 7 old probe_* scripts. Subcommands: `events` (list_game_events + probe player_death/bomb_planted/round_end/weapon_fire/player_hurt with sample rows + coordinate-column detection), `fields` (parse_ticks probes for stats/weapon-slot/inventory-blob fields), `track` (smoke detonation trajectory back-tracking by entityid, grenade_thrown census, entity-class listing at tick 1000), `all`. Demo auto-discovery ladder: explicit path → data/ → demos_to_process/ingestion cache → PRO_DEMO_PATH. Read-only.

### Programma_CS2_RENAN/tools/migrate_hltv_schema_2026_05.py (159 lines)

H1 one-off migration: hltv_metadata.db is intentionally OUTSIDE Alembic (alembic.ini binds only database.db); HLTV schema evolves via idempotent SQLModel create_all(checkfirst=True). Adds 4 tables (ProEvent, ProTournament, ProHead2Head, ProMapRecord) per v3 plan §11 H1; the time_span composite-uniqueness change is explicitly deferred (:19-22). CRITICAL comment: SQLModel.metadata is GLOBAL, so create_all MUST pass an explicit `tables=` filter or every main-DB table would be created inside hltv_metadata.db — "HLTV DB is SEPARATE — conflating them = trust below zero" (:73-80). Post-run verification asserts expected tables exist AND runs a forbidden-leak guard against an 18-table main-DB list (exit 3 on leak :127-152). Takes the `hltv_schema_migration` lock; deliberately NOT d_track_running (HLTV DB only, safe during tick migration).

### Programma_CS2_RENAN/tools/sync_integrity_manifest.py (172 lines)

Pre-commit manifest generator (v2.0): SHA-256 (CRLF→LF normalized) of all production .py under Programma_CS2_RENAN excluding tools/tests/caches/node_modules ("npm packages ship .py files — flatted — present locally, absent in CI → phantom removed drift" :28-30), written sorted with explicit newline="\n" — the manifest carries -text git attrs so git never renormalizes; without LF discipline every OS switch would rewrite all 300+ lines (26-ENV-01 anti-churn :73-75). `--verify-only` diffs changed/new/removed and exits 1 on drift (invoked by build_pipeline and cross-checked by headless_validator Phase 21).

### Programma_CS2_RENAN/tools/project_snapshot.py (439 lines)

Compact "<60 lines" project state: git branch/dirty/last-commit, runtime (python/torch/cuda), DB connectivity + key-table counts + ingest status (uses the CORRECT completed/failed keys — this was the reference for db_inspector's R4 W3 fix) + coach state, checkpoint census with age, integrity-manifest drift count, 7 critical dep versions, config essentials (METADATA_DIM, db path, player name, match_data size). All collectors wrapped in _safe(). Read-only (runs git commands; init_database may create tables).

### Programma_CS2_RENAN/tools/register_orphan_matches.py (424 lines)

Registration-only recovery for orphan shards: when ingestion died between the shard write and the monolith stats write (or shards were restored from backup), the dashboard sees no matches despite hundreds of parsed match files (:3-11). Emits a PlayerMatchStats row per (demo,player) directly from shard cumulative counters — NO .dem re-parse; ML-pipeline fields stay zero and rows are tagged data_quality='registered_only' so backfill jobs can find them (:16-19). R4 MED shared with D2A: MAX(*_total) is the truth, SUM(MAX(*_this_round)) undercounts (match 910: 35 vs 17); damage keeps the per-round SUM since no damage_total exists (:194-199). Path-based is_pro=True override even when metadata flagged 0 (:180-182). Safety: dry-run default, --commit to write, refuses to overwrite 'complete' rows without --force, UPSERT idempotent, shards opened mode=ro. logging.basicConfig(force=True) so parent handlers can't silently swallow warnings (:310-317). Exit 2 if any file failed.

### Programma_CS2_RENAN/tools/repair_rating_scale.py (227 lines)

One-shot data repair for the R4 MED rating-scale incident (2026-07-17): aggregate_match_stats_sql used to write baseline-NORMALIZED ratios into rating_* columns while demo_parser/base_features wrote RAW — every consumer assumes RAW; 1571 of 2501 full_sql* rows on the production monolith carried the wrong scale (:4-11). Deterministic recomputation from intact raw sources (kpr/dpr/avg_kast/avg_adr) — idempotent by construction. Deliberately STDLIB-ONLY: "the monolith lives on the SSD reachable from WSL where the project venv does not exist", so it duplicates the HLTV 2.0 formula with a keep-in-lockstep warning pointing at test_rating_components_contract.py (:20-23). Scope limited to full_sql/full_sql_round_count_anomaly ('complete' rows are already raw). Phase 2 also fixes impact_rounds on 'complete' rows where legacy demo_parser aliased the HLTV impact RATING into a [0,1]-share column (:168-171). Dry-run default (mode=ro connection); --commit takes a full-table CSV backup first, single transaction, then a post-repair verification pass — exit 1 if anything still diverges.

### Programma_CS2_RENAN/tools/ui_diagnostic.py (316 lines)

Headless UI validator v1.0 (merges gui_health_check, Omni_UI_Diagnostic, coordinate_audit, verify_setpos). 6 sections: Resources (PHOTO_GUI + DB SELECT 1), Localization (TRANSLATIONS languages + key parity warnings), Assets (3 themes, ≥3 map radars, fonts), KV Validation — retired with a non-failing INFO notice because the Kivy UI was migrated to Qt; kept only so the console `test ui` command and section count stay stable (:149-161), Qt Frontend (≥10 *_screen.py AST-parseable, ≥5 viewmodels, app.py; NOTE: still checks for *.qss theme files at :206-227, which the F-0005 design-atlas rebuild replaced with base.qss.template — this check contradicts headless_validator/verify_main_boot and will report 0 themes), Spatial Coordinates (world_to_radar corner normalization + landmark bounds on dust2/mirage/inferno). Read-only.

### Programma_CS2_RENAN/tools/user_tools.py (321 lines)

Consolidated interactive utilities (merges 7 legacy scripts): `personalize` (player name/SteamID/API keys — F8-10: prints *** instead of key fragments), `customize` (language en/pt/it, theme, font), `manual-entry` (interactive pro-baseline rows into PlayerMatchStats is_pro=True — F-0042/V-2: typed percents normalized /100, "typed percents used to land raw and poison pro baselines ~100x" :127-131; F8-08 tz-aware datetimes), `weights` (COACH_WEIGHT_OVERRIDES view/set/reset), `heartbeat` (queue counts with the correct completed/failed statuses, CoachState daemon panel, psutil resources, stale-PID detection F8-35). Interactive input() everywhere — cannot run under verify_all_safe (skipped as user_tools has no unsafe prefix but its bare run just prints help and exits 0, so it stays green).

### Programma_CS2_RENAN/tools/__init__.py + tools/__pycache__

Root tools/fuzz/__init__.py documents C-SBX-02; Programma tools/__init__.py is EMPTY (0 bytes) — package marker only.

### Programma_CS2_RENAN/tools/README.md + README_IT.md + README_PT.md

English README (2026-08-03): defines the 4-level validation hierarchy — L1 root headless_validator (42 phases), L2 pytest (2,190+ tests / 130 files), L3 backend_validator (7 sections), L4 Goliath_Hospital (11 departments) — and the pre-commit contract (sync_integrity_manifest --verify-only here; headless_validator + dev_health --quick + dead_code_detector from root tools/, headless as both hook and mandatory post-task gate). Accurate inventory. IT/PT (2026-07-21) again stale: 26 phases, 2,024 tests/118 files, 10 departments (no Endocrinology), claim headless_validator/dev_health/dead_code_detector live IN this directory as pre-commit hooks, list files that don't exist here, mention DiagnosticFinding objects and tools/logs/ JSON reports that don't exist.

### docs/tooling/generate_zh_pdfs.py (285 lines)

Renders the trilingual Book-Coach-{1,2,3}.md into dark-themed Chinese ("zh") PDFs: ```mermaid``` fences rendered to SVG via mmdc (puppeteer config hardcodes /usr/bin/google-chrome-stable --no-sandbox — Linux-only), failures degrade to a code-styled fallback div; markdown→HTML via python-markdown; PDF via weasyprint with an embedded dark CSS (Atkinson Hyperlegible from ~/.local/share/fonts + NotoSansCJK from /usr/share/fonts — hardcoded Linux paths). Output docs/tooling/pdf_zh_output/. Writes only artifacts. Sibling md2pdf.mjs + package.json in the same directory (outside this cluster's named scope) are its Node companion.

## The validation gate

The gate is layered as a 4-level hierarchy (Programma_CS2_RENAN/tools/README.md:15-24), plus two meta-runners:

1. **headless_validator.py (L1, root)** — the mandatory pre-commit AND post-task gate. 42 check phases (banner 1-26 with Phase 19 unused, plus 3b-3l and 6b-6f sub-phases). What must hold: every production module imports (~290 modules, Kivy/RAP deps degrade to warnings); the in-memory SQLModel schema materializes 19+ expected tables and CRUD round-trips (CoachState/PlayerMatchStats/PlayerTickState/RoundStats); the dimensional constitution — METADATA_DIM==25 == INPUT_DIM, OUTPUT_DIM==10, NUM_COACHING_CONCEPTS==16, HIDDEN_DIM==128, RAP_POSITION_SCALE==500.0, TRAINING_FEATURES exactly equals FeatureExtractor.get_feature_names(), TARGET_INDICES in bounds, checkpoint-name map fixed; live forward passes (JEPA shape/pretrain-latents, VL-JEPA concept head (2,16), role-head softmax=1, RAP full pass with 6-key output contract, EMA update/apply/restore round-trip, SelfSupervisedDataset windowing math); feature pipeline never emits NaN/Inf even on extreme inputs; 14 cross-module API contracts (Console, DatabaseManager, ModelFactory, ExperienceBank...); MLControlContext stop/pause/resume semantics incl. TrainingStopRequested NOT being KeyboardInterrupt; integrity-manifest hash sampling (10 files, CRLF-normalized); security invariants (torch.load weights_only=True everywhere, no shell=True, no eval/exec, no bare except, no hardcoded secrets, .gitignore covers .env and *.db); code quality budgets (print ≤30, asserts ≤50, functions >200 lines ≤7, no CRITICAL TODOs in core); Qt frontend imports (14 screens + 7 VMs), qss template contract (F-0005), design-token freshness via gen_design_tokens --check / --web --check; web marquee scaffold shape. Exit 1 on any hard failure.

2. **pytest suite (L2)** — 2,190+ tests, outside this cluster.

3. **backend_validator.py (L3)** — the same contracts probed against the LIVE runtime: real DB in WAL mode with required tables and recent backups, real model-zoo forward passes, the numbered "Prop" analysis modules instantiate, coaching stack (COPER insights, ExperienceBank, RAG retriever) callable, resources present and FRESH (manifest <7d, checkpoints <30d), service health (hltv_sync PID alive, Windows autostart Run key). Honest about its own limits: model-zoo checks are smoke, not correctness (F8-16).

4. **Goliath_Hospital.py (L4)** — the wide clinical sweep: full-source AST syntax, forbidden patterns (hardcoded home paths, credentials), bare-namespace imports, asset integrity (3 themes, 7 map radars), mock-data pollution in code AND in the live DB (player_name LIKE %MCIV%), 21 critical files, 11 analysis factories actually construct, 24 import chains, tech-debt census, tool-contract validation of every tool in both tools/ dirs (syntax + __main__ guard + docstring), entry points/migrations/JSON configs. Delegates ML depth to Ultimate_ML_Coach_Debugger (9 falsification phases: belief variance under seeded init, insight demo_name traceability ≥80%, checkpoint NaN/dead-neuron scan, overfitting max-streak guard, maturity conviction state).

5. **verify_all_safe.py (meta)** — executes every tools/**/*.py as a subprocess with a 120s timeout; exists to prove "a bare invocation of any scheduled tool is harmless". Its F-0039 skip-list IS the destructive-tool census: repair_/flag_/purge_/mine_/populate_/rebuild_/observe_/ingest_/wipe_/fix_/reset_/migrate_/patch_/cleanup_/force_ prefixes never run bare, and the doctrine comment preserves the incident where a timed-out rebuild_monolith left pro stats EMPTY. Its counterpart discipline lives in build_pipeline.py (F-0040: --test-only must never reach the destructive Sanitize stage).

6. **eval_harness.py (measurement, not pass/fail)** — the evidence-first pre-retrain baseline: append-only timestamped JSON reports with feature drift (z>2.5), RAG self-recall@k, kNN outcome purity, embedding silhouette + VICReg collapse detection, strategy-label coverage (target 200+), MoE expert balance, and win-prob Brier/ECE once a checkpoint exists. Graceful degradation is the design: NOT_AVAILABLE sections are never failures.

Supporting gates: dev_health.py orchestrates headless + dead_code_detector --strict + Feature_Audit (+ portability_test at --full); dead_code_detector holds the "orphans baseline is Clean since 2026-07-17" line; sync_integrity_manifest --verify-only is the pre-commit manifest hook; drift_detector / policy_runner / verify_lock_hashes / refresh_compose_digests / refresh_model_pins / sbom_generator form the §53/§54/§63/§64 supply-chain-and-policy wall (mostly Phase-1 scaffolds today); verify_main_boot + run_console_boot + ui_diagnostic + test_tactical_pipeline + observe_training_cycle + validate_coaching_pipeline + coach_answer_eval prove the vertical slices actually run; ui_screenshot / ui_gallery / ui_fixtures are the named-render-eyeball instrument.

## Knowledge-mining pipeline

Coaching knowledge is built along two demo-derived paths plus one scraped reference axis, all landing in two strictly separated stores (monolith database.db vs hltv_metadata.db — "conflating them = trust below zero", migrate_hltv_schema_2026_05.py:79).

Demo → experience (Path A): ingest_pro_demos.py queues .dem files through run_ingestion (per-demo shard DBs + monolith playertickstate/playermatchstats), populate_round_stats.py builds per-round roundstats from the .dem via round_stats_builder AND back-fills the 11 Q1-02 enrichment columns onto playermatchstats, populate_match_results.py derives per-starting-side outcomes (never guessing team-name↔side pairing), then mine_coaching_experience.py turns roundstats moments (entry frags ±0.15, multi-kill wins +0.25, eco upsets +0.30, nade-damage wins +0.10, traded deaths -0.05) into CoachingExperience rows via ExperienceBank with PRO confidence and DL-1 lineage.

Shard → strategy labels (Path B): mine_shard_strategies.py reads ~270 match shards read-only and classifies every round into ~200+ strategy labels across economy/individual/setpiece/rotation/playbook families (incl. cross-round Tier-2 context: loss streaks, economy collapse/recovery, comeback pressure, site-specific executes via K-means bomb-site centroids), embeds each labeled experience with SBERT MiniLM (or a hashed fallback), and bulk-inserts into coachingexperience with strategy_label set — the column eval_harness Phase-7B coverage and the GAP-09 migration-compatible SELECT both key on. The shard-side stats counterparts define an explicit data_quality ladder the miners and dashboards trust: register_orphan_matches → 'registered_only', D2A aggregate_match_stats_sql (25 Class-A fields, SQL-only) → 'full_sql', D2B rebuild_monolith --phase enrich-only (14 Class-B fields from the .dem) → 'complete'.

HLTV reference axis: seed_hltv_top20.py (static hand-curated snapshot with DEFAULT_STATS fallback) → seed_hltv_top_n.py (live FlareSolverr scrape of top-N rosters, freshness-cached, failures queued to pending_vision.json) → seed_hltv_apply_vision.py (vision-LLM-extracted stats writer) → rescrape_placeholder_pros.py (GAP-06 sentinel-card refresh) populate ProTeam/ProPlayer/ProPlayerStatCard in hltv_metadata.db ONLY; sync_pro_players.py (GAP-05) deletes the stale mirror rows from the main DB; purge_default_stats_rag.py removes RAG knowledge minted from placeholder cards (CHAT-06). pro_demo_miner (production code) then mines these cards into TacticalKnowledge/knowledgeentry for RAG retrieval, guarded by the _is_default_stats_card sentinel. build_elite_csvs.py regenerates the elite-comparison CSV baselines from both DBs without fabricating missing sources.

Quality loops closing the pipeline: tick_census → repair_equipment_value / repair_tick_features (dead tick dimensions), repair_kast / repair_ratings / repair_rating_scale (scale and NaN incidents), flag_ghost_players (sample_weight=0 for non-players), backfill_match_dates (OI-2 real chronology for splits), d3_recover_shard_metadata / d4_disk_hygiene_audit (shard corpus health), eval_harness + coach_answer_eval (does the mined knowledge actually ground the coach's answers).

## Suspicious findings

- **Stale trilingual READMEs**: tools/README_IT/PT and Programma tools/README_IT/PT (and fuzz IT/PT) describe fictional structures — migrate_db as an ACTIVE "safer than alembic" wrapper (it is deprecated and unreachable), 26 validator phases with Black/isort checks that don't exist, 10 Goliath departments (no Endocrinology), pre-commit hooks placed in the wrong directory, fuzzer flags --iterations/--report that don't exist. Commit 2f6b1f8 claimed "trilingual parity" for the books, but the tools READMEs (mtime 2026-07-21 vs EN 2026-08-03) were left behind.
- **ui_diagnostic.py checks retired artifacts**: its Qt section still validates themes/*.qss files (Programma_CS2_RENAN/tools/ui_diagnostic.py:206-227), which the F-0005 design-atlas rebuild replaced with base.qss.template — it will report 0 QSS themes while headless_validator/verify_main_boot validate the template. The KV section is an intentional retired stub kept only for section-count stability.
- **db_health_diagnostic.py shard probe queries the wrong table**: the per-match spot check counts `playertickstate` inside shards (tools/db_health_diagnostic.py:205) but shards use `matchtickstate` — tick counts always read N/A there.
- **migrate_db.py is a zombie**: an early `if __name__ == "__main__": sys.exit(0)` block (:30-35) makes everything below unreachable when executed; retained deliberately as an archive, but the second `main()` guard at :253 is dead code.
- **Dangerous defaults that still bite**: repair_equipment_value / repair_ratings / repair_tick_features / flag_ghost_players / ingest_pro_demos mutate the live DB with NO dry-run flag (they rely purely on the F-0039 prefix convention to stay unscheduled); Sanitize_Project deletes the HLTV DB that reset_pro_data deliberately preserves, with no backup; seed_hltv_top20's DEFAULT_STATS placeholder remains in-tree and is the documented root cause of the CHAT-06 RAG pollution.
- **Convention-based safety is fragile**: verify_all_safe's protection is filename-prefix matching — a new destructive tool with an unlisted prefix would be executed bare on every sweep (exactly how F-0039 happened the first time).
- **Feature_Audit static mode hardcodes the parser's 23-column set** (tools/Feature_Audit.py:77-101) rather than deriving it — the same "silently stale" pattern db_health_diagnostic explicitly designs against.
- **headless_validator Phase 19 does not exist** (numbering jumps 18→20); documented in the EN README, but an eternal trap for phase-count claims (the stale IT/PT docs already fell into it).
- **portability_test's SAFE_IMPORT_PATTERNS allowlist (~150 substring entries, tools/portability_test.py:179-336)** makes the import-side-effect check largely advisory — any call whose line contains e.g. `print(` or `float(` is exempt.
- **Duplicated formula copies by design**: repair_rating_scale duplicates the HLTV 2.0 constants (stdlib-only WSL constraint) with a keep-in-lockstep warning pointing at the SSOT contract test; the drift risk is acknowledged but real.
- **Two build pipelines coexist**: root tools/build_pipeline.py (destructive Sanitize stage, spec at repo root, venv_win pyinstaller path) vs Programma tools/build_tools.py (lint + alembic, spec under packaging/ per F-0041e). The F-0041 comments mark build_tools as the corrected one; root build_pipeline still references the old spec location.
- **External note**: while writing this file, docs/doctrine/notes/15-tools.md was repeatedly reverted on disk by something outside this session; the content was rebuilt from a scratchpad master copy each time.
