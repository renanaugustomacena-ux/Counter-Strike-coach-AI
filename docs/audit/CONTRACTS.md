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
Assembled 2026-08-14 (module 07 rubric; S-6 census evidence).

| Domain | Contract & state | Evidence |
|---|---|---|
| Bare except | ZERO in production; headless_validator ENFORCES the ban as a gate phase | S6-B |
| raise e (traceback destruction) | ZERO occurrences | S6-F |
| BaseException doctrine | the one violation class = pyo3 PanicException slipping past `except Exception` = **F-0006** (P1); module-07 fix shape locked (catch PanicException explicitly, never blanket BaseException) | register |
| Exception taxonomy | domain hierarchies + stable error codes (observability/error_codes) tested; narrowed-except DESIGN asserted in tests (OSError caught, RuntimeError propagates by design) | test_observability, test_coach_manager_flows |
| Logging | JSON formatter + correlation IDs (contextvars behavior pinned); logger.exception discipline spot-verified through Pass 1; mock-logger assertion idiom pins LOUD-fallback doctrine (26-ORCH-02, TASKS#59, REPR-01, DR-17, GAP-01) | test_observability + Phase T pins |
| Loud-fallback doctrine | fabricate-nothing + warn-with-doctrine-ID is the house pattern; alert-once escalation (drift CRITICAL once); never-raises telemetry guards | B63-B65 pins |
| print() residue | 24 hits: ~22 inside __main__ debug blocks (L10 debt list); 2 live-path (help_system, training_callbacks) = W3 one-liners | S6-C |
| Naive datetime | 17 hits, NO cross-boundary naive-vs-aware arithmetic found; W3 mechanical utc batch | S6-D |
| Swallow-and-wrong-shape (P0 class) | none found in either pass — every graceful degradation returns typed/documented fallbacks | Pass-1 dossiers |


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
Assembled 2026-08-14.

| Domain | Contract & state | Evidence |
|---|---|---|
| rating_* scale | RAW HLTV components in columns; normalization ONLY in `rating` aggregate; THREE writers pinned to compute_rating_components; **GAP: repair_rating_scale stdlib mirror NOT in the parity net** (W3: 4th parity class) | test_rating_components_contract, D-B61/B72 |
| KAST provenance ladder | estimate_kast_from_stats (closed-form, ~0.91 inflation documented) → event-accurate (repair_kast) by data_quality tier; tests pin BOUNDS not accuracy (correct given the ladder) | D-B53/59, test_feature_kast_roles |
| dataset_split ownership | FOUR writers enumerated: coach_manager.assign_dataset_splits (chronological 70/15/15, per-cohort), data_pipeline P-DP-02 (temporal + player decontamination, bulk chunked), D2A MD5 insert-time (provisional), register_orphan UNASSIGNED; pipeline re-derives each cycle → insert-time values provisional BY DESIGN; T-DIAG live-verified the boundary math (2 rows → TRAIN+TEST) | D-B59/B61/B63, T-DIAG |
| Percent-vs-ratio boundary | V-2 normalization (>1.0→÷100) at seed/vision writers; VM dual-scale display tolerance; **manual-entry hole = F-0042** (consumer confirmed unfiltered); conftest seeded_hltv_session encodes PRE-fix percent scale (W2 companion) | D-B58/61/62 |
| MR12 format awareness | half-switch at 13 (not 16), OT $10k, [13,36] round band (81% mis-flag war story) | test_game_theory, D-B59 |
| Determinism | GLOBAL_SEED=42; B1 per-epoch rotation (train=seed+epoch, val fixed); DET-01 window fetch reproducible; seeded probes in falsification tools | test_nn_config_reproducibility, test_training_orchestrator_flows, B60 |
| Calibration math | 26-WINPROB-03 Platt Newton-Raphson vs closed-form ground truth (Hessian-sign divergence pinned); ECE Naeini in eval_harness; anti-fabrication: eco rows DROPPED not mapped (belief), per-starting-side outcomes only (populate_match_results) | test_analysis_engines_extended, B52/55 |
| NaN/Inf discipline | vectorizer clamp gate (thread-local); _prepare_tensors None guard (Bug#4 FIXED — stale demo tests noted W3); Inf-yaw sanitize; NaN/Inf checkpoint scans | B63, test_playback_engine, ML debugger |


## L9 — Security & input boundaries
Assembled 2026-08-14.

| Boundary | Contract & state | Evidence |
|---|---|---|
| Secrets | OS keyring for 3 API keys (FE-04/FE-06, STORAGE gap war story fixed); no key fragments printed (F8-10/P7-02); repo-wide hardcode scans AS TESTS; detect-secrets + Bandit MEDIUM+ in CI; .env gitignored w/ example | B61 verify, test_security, build.yml |
| Demo ingest path | FE-03 realpath containment + .dem allowlist + MIN_DEMO_SIZE (DS-12); PanicException gap = **F-0006** (P1, all demoparser2 sites); fuzz harness Phase 1 + nightly (develop-only) | B42, register, B76 |
| LLM boundary | sanitize_llm_context prompt-injection tests; R3/R4 anti-fabrication doctrine; Ollama-absent honest exits | test_security_hardening, B55 |
| SQL | see L3 row (validators tested; nosec justified) | test_security_hardening |
| Network | DS-08 SSRF prevention TESTED (remote_file_server); FlareSolverr local-only compose; robots.txt preflights on scrapers; retry+backoff over fetch throttle | test_handoff_regressions, B56 |
| Supply chain | actions SHA-pinned (POL-CI-01 enforced BY policy file + practice); model pins C-MOD-01; compose digests C-DOCK-01 (compose still tag-pinned — W4/W5); SBOM CycloneDX; binary hash-lock post-build; pip-audit CI | B56/B76 |
| Shell | ONE shell=True total (F-0041, internal+broken); shlex+shell=False elsewhere; `svc spawn` path traversal P3 (B46) | S5, register |
| Wipe safety | wipe gold standard (HMAC snapshots, JSONL audit, dry-run default); the DANGEROUS family = F-0039/F-0040/F-0041/F-0043 cluster (CP0 headline) | B52, register |
| Governance | SECURITY/ full set + policy_runner (§54) + waivers w/ expiry + threat-model-gate on boundary files | B54/B76 |


## L10 — API-contract drift & dead code
Assembled 2026-08-14. Consolidated dead/drift ledger (W3 fuel).

| Item | Class | Source |
|---|---|---|
| SvgIconProvider: 15 zero-caller game-glyph methods | dead API | B35/B38 census |
| chronovisor cancel_scan never called | dead API | B42 |
| goliath.py CLI vs console dispatch duplication; Goliath_Hospital overlap | duplication | B47/B59 |
| dead_code_detector ENTRY_POINTS lists deleted main.py (masks orphans under it) | stale anchor (F-0014 x-ref) | B57 |
| scripts/build_exe.bat — Kivy corpse building deleted main.py | dead script (W3 delete) | B76 |
| Root integrity_manifest.json stale duplicate | dead config (W1 delete) | B76 (F-0001) |
| build_tools.py: phantom macena.spec + 2 schema-drift readers + no-op --force | drift cluster = **F-0041** | B61/B76 |
| db_inspector done/error status keys (sibling fixed) | drift (P3 W3) | B61 |
| mine_coaching_experience duplicates round_utils.infer_round_phase (untested copy) | duplication | B55, test_coper_pathway |
| repair_rating_scale constants mirror unpinned | accepted-w/-gap (W3 parity test) | B61/B72 |
| _infra.validate_tool_contract zero callers (candidate) | dead API (verify at W3) | B61 |
| verify_*.py root scripts not pytest-collected | tier labeling (S7/W3) | B75 |
| ~18 production __main__ debug blocks | debt list | S5 |
| fuzzer help text demoparser2==0.41.1 vs pinned 0.41.4 | doc drift (P3) | B76 |
| help_screen + 3 tooling sites: gemma3 vs gemma4 | stale strings (W3/W6) | B45/B50 |
| Stale Bug#4 demonstration tests (never call production) | test debt (W3) | B63 |

