# Cross-Cutting Contracts & Invariants (Pass 2 evidence)

Filled during pass 2 (L1–L10). One section per lens; tables are the evidence format:
producer → shape/units → consumer; thread ownership; session lifecycle; config keys;
formula → implementation.

## L1 — Tick / coordinate / tensor-dimension contracts
Assembled 2026-08-14 from D-B01..B76 cross-refs; spot verifications noted. Test-net column names the pinning suite.

### Tick-rate SSOT (26-NORM-01, owner decision 2026-07-17)
| Producer/consumer | Contract | Test net |
|---|---|---|
| core/tick_rate.py | THE SSOT: DEFAULT_TICK_RATE=64 ("the one sanctioned literal"), resolve ladder metadata→header→None sentinel, valid [32,256] (DS-07) | test_tick_rate_ssot (AST bare-64 hunter + seeded-violation meta-test) |
| run_ingestion._parse_demo_header_meta | per-demo rate PERSISTED to match_metadata (GAP-01), loud warn out-of-range | test_ingestion_tickrate |
| training_orchestrator._resolve_tick_rate | data-carried provenance, 26-ORCH-02 loud fallback | test_training_orchestrator_logic, test_tick_rate_propagation |
| D2A aggregate + trade_kill_detector | trade windows = seconds × per-demo rate (R4 HIGH 26-TICK); TRADE_WINDOW_TICKS export retired | test_trade_kill_detector, test_tools_regressions |
| movement_quality._seconds_to_ticks | the LONE conversion point; RATE-EQUIVARIANCE property (64 vs 128 identical real-time detection) | test_movement_quality_tickrate |
| deception FLASH_BLIND_WINDOW_SECONDS=2.0 | seconds-based (old TICKS=128 baked 64 t/s) | test_game_theory, test_analysis_gaps |
| tactical_viewer_screen | resolved per demo via header meta; :416 init placeholder = F-0002's ONE offender (W2 one-liner) | RED by design until W2 |
| KNOWN GAP | mine_shard_strategies bare `<=32` HE / `<=128` double-util windows (B51) — UNpinned, unconverted | none (register carries it) |

### Dimension chain (25-dim)
| Link | Contract | Test net |
|---|---|---|
| FeatureExtractor (vectorizer) | 25 features, names==METADATA_DIM, no dupes, batch==individual, thread-local clamp gate 26-VEC-01 | test_feature_extractor_contracts, test_metadata_dim_contract |
| METADATA_DIM == INPUT_DIM == len(TRAINING_FEATURES) == len(MATCH_AGGREGATE_FEATURES) == 25 | quadruple equality; OUTPUT_DIM==10 | test_coach_manager_tensors, test_smoke (==25 pin), ML debugger phase 5, CI cross-module step |
| JEPA windows | contiguous single-player, window_len=11 (10 ctx + 1 tgt, V-1 no-overlap), J-5 skip-not-pad, R4-CRIT | test_jepa_window_fetcher, test_training_orchestrator_flows |
| RAP tensors | view/map/motion (B,3,64,64), metadata (B,5,25), skill_vec (B,10); WR-76 suffix strip | conftest rap_inputs, test_rap_coach, test_rap_window_fetcher |
| OPEN CONTRACT | finetune targets 25-dim vs coaching head OUT=10 — 26-RANGE-01 guard raises NAMED error; NOT resolved (TASKS#64, JEPA-readiness CP0 cluster) | test_jepa_training_pipeline (pins the guard) |

### Radar/world coordinate space
| Element | Contract | Test net |
|---|---|---|
| SPATIAL_REGISTRY + MapMetadata | world→radar via pos_x/pos_y/scale; corners→(0,0)/(1,1); NO Y-inversion doctrine; FoV rotate(90−yaw) | test_spatial_engine, test_tensor_factory (FovConeOrientation), ui_diagnostic §6 |
| Mirage constants | pos_x=-3230, pos_y=1713, scale=5.0 — IDENTICAL in tensor_factory tests + ui_fixtures inverse transform | test_tensor_factory, B50 verify |
| map-SSOT CLUSTER (CP0) | 12 divergent known-map lists (match_utils 11, coach _MAP_RE 9, rebuild_monolith 8, mine_* 8, populate_match_results, d3_recover, seed tools, REQUIRED_MAPS 7, spatial registry, map_config.json, headless EXPECTED, ui fixtures) — single-authority fix is a CP0 decision | none — the cluster IS the finding |

## L2 — Thread & Qt-signal safety
Assembled 2026-08-14. The MVVM doctrine (Worker(QRunnable)+Signals; screens never touch DB) held across all 17 screens at Pass 1 with THREE exceptions — all registered.

| Domain | Contract & state | Evidence/test net |
|---|---|---|
| Worker signal contract | result/error/finished-ALWAYS; VMs emit, screens slot | test_qt_core TestWorker; B36 all-11-VMs MVP-pure verify |
| Screens touching DB (auto ≥P1 rule) | THREE violations registered: profile_screen._save, tactical _start_chronovisor_scan, wizard._finish = **F-0038** (P1, 3 sites) | B44/B45 dossiers |
| Ingestion worker slots | home + settings + console share `_ingestion_worker` single-slot pattern; concurrency hazard = **F-0037** (P1, FIVE trigger surfaces: home, settings, console ingest, batch_ingest, ingest_pro_demos) | B40/B44/B46/B47/B56 |
| Timers | toast singleShot fire-on-corpse = **F-0036**; skeleton pulse stops in hideEvent ✓; playback QTimer main-thread ✓ (Inf-yaw hang pinned) | B39, test_playback_engine |
| Cross-thread delivery | Qt auto-queued connections validated as THE doctrine (module 20); chat streaming first-chunk/update_last split correct (B43) | test_chat_streaming, coach_screen verify |
| Daemon lifecycle | session_engine graceful shutdown (signal→flag→drain→join) ✓ course-validated; run_worker stale-threshold copy = **F-0015**; hltv_sync dead main.py launch = **F-0014** | test_session_engine, test_lock_files |
| Locks | lock_files: TOCTOU-hardened acquire, exactly-one-winner ATOMICITY test, dead-PID reclaim (Windows OpenProcess fix 26-WIN-02); release() ownership gap = **F-0009**; lock ordering: no nested cross-order acquire found in Pass 1 (d_track_running and hltv_schema_migration never nested) | test_lock_files |
| Singletons under threads | tensor-factory 10-thread same-instance test ✓; config._settings_lock thread test ✓; contextvars correlation-ID behavior pinned | test_tensor_factory, test_config_resolution, test_observability |
| Theme-switch staleness (SYSTEMIC, CP0) | instance-styled widgets (FilterChip/StatusChip/roster cards/banners) never re-styled on theme_changed — hosts don't call refresh_styling; register at CP0 as one cluster | B37-B45 ledger |
| GIL note | demoparser2 (Rust) releases GIL during parse — thread-based parse timeout sound in principle; wrong implementation = **F-0013** | module 10 study |

## L3 — DB session & transaction lifecycle
Assembled 2026-08-14.

| Domain | Contract & state | Evidence/test net |
|---|---|---|
| Session shape | `Session(engine, expire_on_commit=False)` everywhere (database.py:230/498; every test fake replicates it) | B36 verify; conftest mock_db_manager |
| DB separation principle | main database.db vs hltv_metadata.db — "conflating them = trust below zero"; _HLTV_TABLES registry is the SSOT (create_all `tables=` filter); leak guard in H1 migration (exit 3) | test_hltv_table_registry (R4 CRIT), migrate_hltv_schema |
| Migration-path plurality (RESOLVED map) | ONE canonical alembic tree (alembic.ini → alembic/, binds database.db ONLY) + hltv DB deliberately OUTSIDE alembic (idempotent one-off scripts, H1 pattern) + migrate_db.py = proper R2-11 tombstone + schema.py hot-patch (identifier-validated) — plurality is DESIGNED, not drift; W3 optional: one doc paragraph | B47/B53/B58/B76 |
| WAL discipline | journal_mode=WAL enforced + tested; wipe/restore clears stale WAL sidecars; backup via sqlite backup API; free-space guard (154GB war story) | test_database_wal_enforcement, test_db_backup, test_tools_regressions |
| Check-then-act inventory | run_ingestion `_is_demo_already_ingested` + queued-snapshot (**F-0037**); D2A existing-quality check-then-upsert (single-writer under lock — OK); register_orphan same (gated) | register |
| Ingestion claim semantics | ingest_manager statuses queued/processing/completed/failed; stale-recovery threshold: session_engine 30-min (P4-B) vs run_worker 5-min copy = **F-0015**; db_inspector displays done/error = stale vocabulary (P3, W3) | test_session_engine, D-B60/61 |
| SQL injection posture | whitelist+bracket table names (db_inspector/project_snapshot); schema.py safe_identifier/col_type/default validators TESTED; D2A nosec B608 justified (module constants) | test_security_hardening |
| StatCard identity | player_id-only upsert convention, ONE-card invariant, (player_id,time_span) uniqueness DEFERRED by H1 §11 — every writer must keep the convention or reads go nondeterministic | D-B58 contract |
| Session-per-row vs bulk | data_pipeline F2-22 chunked UPDATE (500/id-IN chunk under SQLITE_MAX_VARIABLE_NUMBER); rebuild_monolith bulk-PRAGMA pairs + checkpoint/resume | B11/B54 |

## L4 — Error-handling & logging consistency
(pending)

## L5 — Resource lifecycle
Assembled 2026-08-14 (module 33 rubric).

| Domain | Contract & state | Evidence |
|---|---|---|
| torch.load | weights_only=True at EVERY loader found (ML debugger, persistence, tests) | B60, test_nn_infrastructure |
| Checkpoint saves | persistence save_nn/load_nn + StaleCheckpointError + NN-14 FileNotFoundError; sidecar meta (best_val_loss B3.2); EMA counters rehydration REPR-01 | test_persistence_stale_checkpoint, B63 |
| EMA aliasing | NN-16: apply_shadow/restore break storage aliasing (memory-safety) | test_ema_hopfield_drift_invariants |
| Training-loop memory | losses via .item() discipline verified at B19-B25; epoch-loss denominator R4; zero-step scheduler guard TASKS#59 | B19-25 dossiers, test_training_orchestrator_flows |
| SQLite handles | ro-URI opens in tools (d4, D2A, tick_census); contextlib.closing in register_orphan; WAL sidecar hygiene at wipe/restore | B52-B61 |
| Tempfiles | correct delete=False+unlink (generate_zh_pdfs, jepa e2e ft-path); Windows-hostile delete=True in fuzzer (P3 B57); test_jepa_model leaks one tmp .pt (P3) | B57/B63 |
| Subprocesses | list-args+timeouts everywhere except the ONE shell=True (F-0041 build_tools, broken anyway); B47 F7-29 goliath child cleanup | S5, B76 |
| Qt objects | deleteLater discipline OK; toast timer fire-on-corpse F-0036; QPainter guards in charts (offscreen render tests pass) | B38-39, test_charts |
| Locks/PID files | lock_files reclaim+atomicity; hltv_sync.pid stale detection (F8-35) | test_lock_files, B61 |


## L6 — Config/settings & path portability
Assembled 2026-08-14.

| Domain | Contract & state | Evidence |
|---|---|---|
| Settings flow | get_setting/save_user_setting under _settings_lock; secrets (STEAM/FACEIT/STORAGE_API_KEY) route through OS keyring FE-04/FE-06 with PROTECTED sentinel on disk; set/get robustness asymmetry = F-0007 | test_config_resolution, B61 verify |
| $HOME family (the 2026-07-26 disasters) | THREE guards pinned: PRO_DEMO_PATH never defaults to HOME + explicit-HOME refused; NO implicit shard migration; dangling symlink fails LOUD (F-0003 suite, Linux) — get_pro_demo_base residual $HOME fallback = F-0008 | test_config_resolution, test_match_data_no_implicit_migration, test_match_data_dangling_symlink |
| Env overrides | 4 path keys env-overridable (BRAIN_DATA_ROOT verified live at T-DIAG); .env layering tested; .env.example honest | test_config_dotenv, B76 |
| Path bootstrap | path_stabilize SSOT (_infra) + per-file sys.path inserts (S5: 92 hits/83 files — convention, dual-import hazard documented); module 30 resolution-order grounding | S5, STUDY_LOG |
| Cross-OS | CRLF-normalized manifest hashing; .gitattributes line-ending POLICY (no global renormalize — BINDING); win32 UTF-8 reconfigure; POSIX-only os.kill fixed 26-WIN-02 | B58/B76 |
| Shadow config | pytest.ini duplicate = F-0044 (invocation-dependent) | B76 |
| Hardcoded personal paths | generate_zh_pdfs (env-overridable, personal docs tool P3); forbidden-pattern scans (Desktop paths) in goliath ER + CI | B57/B59 |


## L7 — i18n & user-facing text
Assembled 2026-08-14. THE SYSTEMIC REGISTER ENTRY (CP0 decision cluster).

| Domain | State | Evidence |
|---|---|---|
| Parity gates EXIST | en/it/pt key parity tested at THREE tiers: test_ui_harness (harness), ui_diagnostic §2 (validator, WARNING), test_unit localization (unit incl. LOC-02 fallback) | B69/B61/B62 |
| get_text coverage — screens | md_*/procomp/coach/tactical screens near-clean ✓; EN-heavy: pro_player_detail (near-zero i18n), faceit config, wizard; constructor-arg literals ESCAPED S3's setter grep (census corrected at B40): home "RECENT MATCHES"/"View all →", match_history bucket headers, steam "Sync Now" restore drift | L7 ledger (B34-B45) |
| EN advice cluster (DECISION NEEDED at CP0) | ALL coaching advice EN by construction (ExplanationGenerator, hybrid titles "Strong Deaths", COPER messages, rating_label); FOUR test suites hard-pin the EN strings (coper_pathway, coaching_engines, coaching_service_flows, hybrid_engine) — i18n-ifying advice = engine+4-suite coordinated wave; alternative = deliberate EN-advice product decision (zero churn) | D-B68 |
| READMEs | trilingual EN/IT/PT everywhere incl. SECURITY/ and logs/ exceptions; W6 ONLY | B76 |
| Known stale strings | help_screen gemma3:e2b vs llm_service gemma4:e2b (4 sites incl. ui_gallery/ui_fixtures); placeholder.py README naming drift (W6) | B45/B50 |


## L8 — Numerical & ML correctness
(pending)

## L9 — Security & input boundaries
(pending)

## L10 — API-contract drift & dead code
(pending)
