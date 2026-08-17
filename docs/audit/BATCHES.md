# Nuke-Proof Audit — Frozen Batch Table (B01–B76)

Frozen 2026-08-14 at campaign start. Numbering is FROZEN — batches may be re-scoped only by
an explicit note in the ledger `notes` column, never renumbered. `LEDGER.csv`'s `batch`
column is the file-granular authority and must reconcile to this table.

Study-module interleave rule: the module is read immediately BEFORE the flagged batch;
its STUDY_LOG.md entry lands in the same commit as that batch's dossier.
Study source root: `C:\Users\Renan Macena\Desktop\WORK\personal-resources-main\personal-resources-main\04-PROGRAMMAZIONE-PYTHON`

All paths below are relative to the repo root; unprefixed package dirs live under
`Programma_CS2_RENAN/`.

## R0 — Setup (audit infra only, exempt from diagnose-before-fix)

- SU-1: branch `chore/nuke-proof-audit`; `docs/audit/` skeleton.
- SU-2: sweep S1 generates `LEDGER.csv` (authoritative 579-file enumeration + LOC + batch
  assignment; reconciles any file this table groups as "remaining") plus dead-import/dead-code
  candidate list.
- SU-3: `BASELINE.md` — run every gate once and record state; log F-0001 (stale integrity
  manifest incl. phantom `Programma_CS2_RENAN/main.py`). No wave may later claim a
  pre-existing red as a regression.

## Pass 1 batch table

| # | Batch (dossier D-B##) | Contents | ~LOC | Study before |
|---|---|---|---|---|
| **Phase F — Foundations** | | | | **22-clean-code** before B01 (smells catalog + review checklist become the pass-1 per-file rubric) |
| B01 | core-config | core/config, constants, app_types, tick_rate, registry, frozen_hook, lifecycle, lock_files | 1.3k | 22 |
| B02 | core-runtime | session_engine, playback_engine, demo_frame, spatial_engine, map_manager, asset_manager, localization | 2.0k | — |
| B03 | core-spatial+obs | spatial_data, map_callouts + observability/ (7) | 2.0k | **07-error-handling** |
| **Phase D — Data** | | | | |
| B04 | storage-core | database, db_models, storage_manager | 1.8k | **09-type-hints** (ORM typing is peak type-risk; playbook re-consulted at W4) |
| B05 | storage-data | match_data_manager, stat_aggregator, state_manager, maintenance | 1.6k | — |
| B06 | storage-aux+migrations | backup_manager, db_backup, db_migrate, remote_file_server + ALL THREE alembic trees (alembic/, backend/storage/migrations/, Programma_CS2_RENAN/migrations/) | 2.6k | — |
| B07 | demo-parsing | demo_parser, demo_format_adapter, event_registry, round_context, trade_kill_detector | 1.9k | — |
| B08 | external-sources | data_sources/hltv/ (4), hltv_scraper, steam_api, steam_demo_finder, faceit_* | 2.1k | — |
| B09 | ingestion-pkgs | ingestion/ (10) + backend/ingestion/ (4: watcher, csv_migrator, resource_manager) | 2.0k | **10-async** (daemons/watchers) |
| B10 | ingestion-orchestration | run_ingestion.py, hltv_sync_service.py, run_worker.py | 2.1k | — |
| **Phase P — Processing** | | | | |
| B11 | pipeline-core | data_pipeline, tick_enrichment, round_reconstructor, state_reconstructor, connect_map_context | 1.6k | — |
| B12 | round-stats | round_stats_builder, rating, skill_assessment, external_analytics | 1.6k | — |
| B13 | tensors | tensor_factory, player_knowledge, heatmap_engine | 1.7k | — |
| B14 | feature-eng | feature_engineering/ (vectorizer, role_features, base_features, rating, kast) | 1.7k | — |
| B15 | baselines+validation | baselines/ (7) + validation/ (drift, dem_validator, sanity, schema) | 2.1k | — |
| **Phase A — Analysis** | | | | |
| B16 | analysis-1 | win_probability, momentum, entropy_analysis, engagement_range, blind_spots | 1.6k | — |
| B17 | analysis-2 | belief_model, game_tree, deception_index, __init__ (101 ln) | 1.4k | — |
| B18 | analysis-3 | movement_quality, role_classifier, utility_economy | 1.6k | — |
| **Phase N — NN/ML** | | | | **33-profiling-memoria-gc** before B19 (torch memory/GC) |
| B19 | nn-foundations | config, training_config, model, factory, dataset, data_quality, ema, early_stopping, persistence | 1.5k | 33 |
| B20 | jepa-model | jepa_model, role_head | 1.5k | — |
| B21 | jepa-training | jepa_train, jepa_trainer | 1.4k | — |
| B22 | training-orchestrator | training_orchestrator.py (solo) | 1.6k | — |
| B23 | training-support | train, training_monitor/controller/callbacks, tensorboard_callback, evaluate, win_probability_trainer, embedding_projector, maturity_observatory | 1.9k | — |
| B24 | coach-manager+inference | coach_manager, inference/ghost_engine, layers/superposition, advanced/ | 1.7k | — |
| B25 | rap-coach-both-trees | nn/rap_coach/ + nn/experimental/rap_coach/ (S2 diff cross-checked here) | 1.7k | — |
| **Phase K — Knowledge/Coaching/Services** | | | | |
| B26 | experience-bank | experience_bank, round_utils | 1.4k | — |
| B27 | knowledge-rag | rag_knowledge, vector_index, graph, pro_demo_miner, init_knowledge_base | 1.9k | — |
| B28 | coaching-engines | backend/coaching/ (9) + knowledge_base/ + progress/ + onboarding/ (zero-coverage pkgs flagged) | 1.8k | — |
| B29 | services-coaching | coaching_service, profile_service, analysis_service, visualization_service | 1.5k | — |
| B30 | coaching-dialogue | coaching_dialogue.py (solo) | 2.0k | — |
| B31 | services-orchestration | analysis_orchestrator, llm_service, ollama_writer, telemetry_client | 1.7k | — |
| B32 | services-rest+control | lesson_generator, player_lookup + control/ (console, ingest_manager, ml_controller, db_governor) | 2.3k | — |
| B33 | reporting | backend/reporting/analytics + reporting/ (visualizer, report_generator) | 0.9k | — (slack batch) |
| **Phase U — UI** | | | | **20-gui** before B34 |
| B34 | qt-foundations | app.py, main_window, core/app_state, core/worker, core/i18n_bridge | 1.3k | 20 |
| B35 | qt-core-visuals | design_tokens (generated — verify header/no hand edits), theme_engine, typography, qss_generator, icons, svg_icon_provider, animation, easing, sound, web_bridge, match_utils, widgets_helpers, qt_playback_engine | 2.0k | — |
| B36 | viewmodels | all 11 VMs | 1.6k | — |
| B37 | widgets-components-1 | card, match_row_card, nav_sidebar, empty_state, stepper, stat_badge, last_match_hero, toggle_switch, focus_insight, map_tile, match_mini_card, filter_chip | 2.1k | — |
| B38 | widgets-components-2+charts | remaining components + charts/ (7) | 2.0k | — |
| B39 | widgets-tactical+overlay | tactical/map_widget, player_sidebar, timeline_widget, _paint_utils, coaching/chat_panel, toast, skeleton | 2.2k | — |
| B40 | screens-home | home_screen, match_history_screen, placeholder | 1.5k | — |
| B41 | screens-detail | match_detail_screen, performance_screen | 2.1k | — |
| B42 | screens-tactical | tactical_viewer_screen.py (solo) | 1.7k | — |
| B43 | screens-coach | coach_screen, pro_comparison_screen, pro_player_detail_screen | 2.0k | — |
| B44 | screens-settings | settings_screen, steam_config, faceit_config, profile, user_profile | 2.0k | — |
| B45 | screens-wizard+help | wizard_screen, help_screen | 1.5k | — |
| **Phase C — CLIs/tools** | | | | |
| B46 | console | console.py root (solo) | 1.7k | — |
| B47 | root-clis | goliath, batch_ingest, schema, run_full_training_cycle, setup.py | 1.2k | — |
| B48 | headless-validator | tools/headless_validator.py (solo — it IS the gate) | 2.9k | — |
| B49 | portability+verify | portability_test, verify_lock_hashes, verify_main_boot, run_console_boot, verify_all_safe, dev_health | 2.4k | — |
| B50 | ui-tooling | ui_fixtures, ui_screenshot, ui_gallery, gen_design_tokens, build_web | 2.0k | — |
| B51 | shard-tools | mine_shard_strategies, d3_recover_shard_metadata | 2.0k | — |
| B52 | db-maintenance-tools | wipe_for_reingest_safe, reset_pro_data, db_health_diagnostic, populate_round_stats, populate_match_results | 2.3k | — |
| B53 | repair-tools | repair_* (4), merge_demo_pool, rescrape_placeholder_pros, flag_ghost_players, purge_default_stats_rag, sync_pro_players, migrate_db (deprecated), tick_census | 1.8k | — |
| B54 | pipeline-tools | rebuild_monolith, observe_training_cycle, policy_runner | 2.3k | — |
| B55 | eval-tools | eval_harness, coach_answer_eval, mine_coaching_experience, validate_coaching_pipeline, test_tactical_pipeline, test_rap_lite, drift_detector | 2.4k | — |
| B56 | seed+supplychain-tools | seed_hltv_top_n, seed_hltv_apply_vision, ingest_pro_demos, refresh_compose_digests, refresh_model_pins, sbom_generator, audit_binaries, audit_scanner | 2.5k | — |
| B57 | misc-tools | dead_code_detector, Feature_Audit, Sanitize_Project, d4_disk_hygiene_audit, build_pipeline + S1-reconciled leftovers | 1.7k | — |
| B58 | ptools-hltv | Programma_CS2_RENAN/tools/: seed_hltv_top20, migrate_hltv_schema_2026_05, sync_integrity_manifest | 1.8k | — |
| B59 | ptools-goliath | Goliath_Hospital, aggregate_match_stats_sql | 2.1k | — |
| B60 | ptools-inspectors | backend_validator, context_gatherer, Ultimate_ML_Coach_Debugger, db_inspector | 2.2k | — |
| B61 | ptools-rest | _infra, project_snapshot, register_orphan_matches, build_tools, demo_inspector, ui_diagnostic, user_tools, repair_rating_scale | 2.9k | — |
| **Phase T — Tests** | | | | **08-testing** before B62 |
| B62 | test-infra | both conftest.py, automated_suite/ (6), setup_golden_data, tests/ data helpers | 1.3k | 08 |
| **T-DIAG** | (scheduled step, not a batch) | ONE bounded local run each of automated_suite/test_e2e.py, test_system_regression.py, test_dry_run_checkpoint_integrity.py — explicit timeout, DB state backed up first, outcomes recorded as FINDINGS evidence. No activation work. | | |
| B63 | tests-nn-training | test_coach_manager_flows, test_training_orchestrator_flows/logic, test_jepa_model, test_jepa_training_pipeline | 3.8k | — |
| B64 | tests-rap-chronovisor | test_coper_pathway, test_rap_coach, test_rap_training_dry_run, test_chronovisor_*, test_nn_extensions/infrastructure | 3.5k | — |
| B65 | tests-analysis | test_game_theory, test_game_tree, test_analysis_gaps/engines/engines_extended, test_belief_model_extended | 3.4k | — |
| B66 | tests-processing | test_tensor_factory, test_feature_kast_roles, test_feature_extractor_contracts, test_round_stats_enrichment, test_skill_assessment | 2.8k | — |
| B67 | tests-storage | test_experience_bank_db, test_database_layer, test_db_backup, test_baselines, test_config_resolution | 2.2k | — |
| B68 | tests-coaching | test_coaching_service_* (3), test_coaching_engines, test_hybrid_engine, test_rag_knowledge | 2.5k | — |
| B69 | tests-ui | test_qt_core, test_ui_smoke, test_ui_harness, test_charts, test_detonation_overlays, test_tactical_frame_widgets, i18n key-parity test | 3.0k | — |
| B70 | tests-regression | test_phase0_3_regressions, test_v1_blockers, test_deployment_readiness, test_handoff_regressions, test_tools_regressions, test_security_hardening, test_observability | 2.8k | — |
| B71–B74 | tests-remaining | ~82 small files, module-mirror grouping fixed by S1: B71 core/session mirrors; B72 data-sources/ingestion mirrors; B73 nn/tools mirrors; B74 services/misc mirrors | ~2.8k each | — |
| B75 | tests-top-level+evals | tests/ (24 incl. forensics/) + evals/cs2_coach_bench (2) | 2.6k | — |
| **Phase I — Infra** | | | | **30-troubleshooting** before B76 |
| B76 | infra-config | .github/workflows (build.yml, fuzz-nightly.yml, notify-failure.yml, threat-model-gate.yml), pytest.ini, pyproject.toml, setup.py stub, requirements*, .pre-commit-config.yaml, docker-compose.yml, scripts/ (incl. stale build_exe.bat), launch.sh + shell/bat launchers, packaging/*.spec + .iss, alembic.ini, .gitignore, integrity_manifest.json | ~1.5k | 30 |

Per-batch commit: `docs(audit): B## <name> — dossier + ledger`.

## Gate cadence during pass 1

Batch commits are docs-only → full gate runs at R0 and at every phase boundary
(F, D, P, A, N, K, U, C, T, I) with named counts reported. Per-wave gates from CP0 onward.

## Mechanical sweeps (subagents — evidence-pointers only, NEVER auto-findings)

Every promoted candidate is re-verified by the main auditor at file:line during the owning
batch. Raw results in `docs/audit/sweeps/S-#.md` with per-candidate verified/rejected status.

- **S1** (R0): ledger generation + dead-import/dead-code candidates (`ruff check --select F401,F811,F841` + orphan-module pass) → reconciled continuously; feeds L10.
- **S2** (before B25): unified diff rap_coach vs experimental/rap_coach → cross-checked at B25.
- **S3** (before B34): i18n literal sweep (user-visible strings bypassing `i18n.get_text` in apps/qt_app), hex-color-literal sweep (colors bypassing design_tokens), QGraphicsOpacity/DropShadow usage sweep → cross-checked B34–B45 + L7.
- **S4** (before B04): raw-SQL f-string/`execute(` sweep, Session-creation callsite census → cross-checked B04–B06 + L3.
- **S5** (before B46): sys.path-manipulation sweep, `__main__` entry inventory, subprocess/shell usage sweep → cross-checked B46–B61.
- **S6** (before pass 2): core→backend import edge map (the 22 known), circular-import candidates, bare/broad-except census, print-in-library census, datetime.now/utcnow census, seed usage → feeds L4/L8/L10.
- **S7** (during Phase T): test-to-module cross-ref (modules with zero test imports) → feeds zero-coverage findings.
