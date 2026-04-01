> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Test Suite

**Authority:** `Programma_CS2_RENAN/tests/` -- Comprehensive regression and correctness suite for the Macena CS2 Analyzer.

The test suite contains 1,794+ tests distributed across 89 files, following the test pyramid
(unit > integration > e2e). Every subsystem -- from the 25-dim feature vector through the
neural networks, coaching engine, database layer, and UI screens -- is covered by deterministic,
reproducible assertions. Tests run under pytest with a mandatory virtual-environment guard and
optional integration-test gating via the `CS2_INTEGRATION_TESTS` environment variable.

## Key Principles

- **No mock data for domain logic** -- Real DB data or `pytest.skip`
- **Mocks only at I/O boundaries** -- Network, filesystem, external APIs
- **Zero tolerance for synthetic data** -- Every value must originate from real sources
- **Test hierarchy** -- Unit (>70%) > Integration (>20%) > E2E (~10%)
- **Deterministic seeding** -- `GLOBAL_SEED=42` everywhere, `torch.manual_seed(42)` in fixtures

## File Inventory

| File | Domain | Description |
|------|--------|-------------|
| `conftest.py` | Infrastructure | Shared fixtures, venv guard, path stabilization, markers |
| `test_analysis_engines.py` | Analysis | Core analysis engine contracts |
| `test_analysis_engines_extended.py` | Analysis | Extended analysis coverage (belief models, momentum) |
| `test_analysis_gaps.py` | Analysis | Gap analysis and missing-coverage detection |
| `test_analysis_orchestrator.py` | Services | `AnalysisOrchestrator` pipeline tests |
| `test_auto_enqueue.py` | Ingestion | Auto-enqueue watcher for new demos |
| `test_baselines.py` | Analysis | Baseline computation and decay |
| `test_chronovisor_highlights.py` | Analysis | `ChronovisorScanner` highlight extraction |
| `test_chronovisor_scanner.py` | Analysis | Scanner tick-level sweep tests |
| `test_coaching_dialogue.py` | Coaching | Dialogue engine conversation flow |
| `test_coaching_engines.py` | Coaching | COPER, hybrid, and correction engines |
| `test_coaching_service_contracts.py` | Services | `CoachingService` API contract assertions |
| `test_coaching_service_fallback.py` | Services | Graceful degradation when backends unavailable |
| `test_coaching_service_flows.py` | Services | End-to-end coaching service workflows |
| `test_coach_manager_flows.py` | Core | `CoachManager` session lifecycle |
| `test_coach_manager_tensors.py` | Core | Tensor shape validation in coach pipeline |
| `test_config_extended.py` | Core | `config.py` resolution, overrides, thread safety |
| `test_config_resolution.py` | Core | Config resolution hierarchy tests |
| `test_coper_pathway.py` | Coaching | COPER coaching pathway end-to-end chain |
| `test_database_layer.py` | Storage | ORM models, migrations, WAL enforcement |
| `test_database_wal_enforcement.py` | Storage | WAL mode enforcement tests |
| `test_data_pipeline_contracts.py` | Processing | Feature pipeline input/output contracts |
| `test_db_backup.py` | Storage | Database backup and restore logic |
| `test_db_governor_integration.py` | Storage | Database governor concurrency tests |
| `test_debug_ingestion.py` | Ingestion | Ingestion debug trace validation |
| `test_demo_format_adapter.py` | Ingestion | Demo format adapter (MIN_DEMO_SIZE enforcement) |
| `test_demo_parser.py` | Ingestion | `demoparser2` integration and tick extraction |
| `test_dem_validator.py` | Ingestion | `.dem` file header and integrity checks |
| `test_deployment_readiness.py` | Build | Pre-deployment readiness gate |
| `test_detonation_overlays.py` | Reporting | Grenade detonation overlay rendering |
| `test_dimension_chain_integration.py` | NN | `METADATA_DIM=25` propagation across all models |
| `test_drift_and_heuristics.py` | Analysis | Statistical drift detection and heuristic rules |
| `test_experience_bank_db.py` | Knowledge | Experience bank database persistence |
| `test_experience_bank_logic.py` | Knowledge | Experience bank retrieval and ranking |
| `test_feature_extractor_contracts.py` | Processing | `FeatureExtractor.extract()` contract tests |
| `test_feature_kast_roles.py` | Processing | KAST estimation and role-based features |
| `test_features.py` | Processing | 25-dim feature vector correctness |
| `test_game_theory.py` | Analysis | Game-theoretic models (Nash, minimax) |
| `test_game_tree.py` | Analysis | Game tree construction and traversal |
| `test_hybrid_engine.py` | Coaching | Hybrid coaching engine fusion logic |
| `test_ingestion_pipeline.py` | Ingestion | Ingestion pipeline integration tests |
| `test_integration.py` | Integration | Cross-module integration with real DB |
| `test_jepa_model.py` | NN | JEPA encoder, coaching head, EMA target encoder |
| `test_jepa_training_pipeline.py` | NN | JEPA training pipeline tests |
| `test_knowledge_graph.py` | Knowledge | RAG knowledge graph queries |
| `test_lifecycle.py` | Core | Application lifecycle (boot, shutdown, recovery) |
| `test_map_manager.py` | Core | Map geometry, callout resolution, spatial queries |
| `test_model_factory_contracts.py` | NN | `ModelFactory` instantiation contracts |
| `test_models.py` | Storage | SQLModel ORM model validation |
| `test_nn_config_reproducibility.py` | NN | Neural network config reproducibility tests |
| `test_nn_extensions.py` | NN | LTC neurons, Hopfield memory extensions |
| `test_nn_infrastructure.py` | NN | Training infrastructure (DataLoader, checkpoints) |
| `test_nn_training.py` | NN | Training loop, loss convergence, gradient checks |
| `test_observability.py` | Observability | Structured logging, correlation IDs, telemetry |
| `test_onboarding.py` | UI | Onboarding wizard flow |
| `test_onboarding_training.py` | UI | Training-mode onboarding |
| `test_persistence_stale_checkpoint.py` | NN | Stale checkpoint detection and recovery |
| `test_phase0_3_regressions.py` | Regression | Phase 0-3 regression suite |
| `test_playback_engine.py` | Core | Tick playback engine |
| `test_pro_demo_miner.py` | Ingestion | Pro demo discovery and metadata |
| `test_profile_service.py` | Services | Player profile CRUD |
| `test_qt_core.py` | UI | PySide6/Qt core widget tests |
| `test_rag_knowledge.py` | Knowledge | RAG retrieval and FAISS index |
| `test_rap_coach.py` | NN | RAP model forward pass, memory, belief states |
| `test_round_stats_enrichment.py` | Processing | Round stats enrichment pipeline |
| `test_round_utils.py` | Processing | Round utility functions |
| `test_security.py` | Security | Shell injection, `.env` protection, secret detection |
| `test_services.py` | Services | `CoachingService`, `AnalysisService`, `DialogueEngine` |
| `test_session_engine.py` | Core | Quad-Daemon session engine lifecycle |
| `test_skill_assessment.py` | NN | Skill assessment module tests |
| `test_skill_model.py` | NN | Skill model forward pass and output shape |
| `test_spatial_and_baseline.py` | Analysis | Spatial engine + baseline integration |
| `test_spatial_engine.py` | Analysis | Spatial engine coordinate transforms |
| `test_state_reconstructor.py` | Processing | RAP state reconstruction from ticks |
| `test_tactical_features.py` | Processing | Tactical feature extraction |
| `test_temporal_baseline.py` | Analysis | 20 temporal baseline decay tests |
| `test_tensor_factory.py` | NN | `TensorFactory` shape and dtype contracts |
| `test_trade_kill_detector.py` | Analysis | Trade kill detection logic |
| `test_training_callbacks.py` | NN | Training callback registry tests |
| `test_training_orchestrator_flows.py` | Services | Training orchestrator end-to-end flows |
| `test_training_orchestrator_logic.py` | Services | Training orchestrator decision logic |
| `test_v1_blockers.py` | Regression | V1 production readiness blocker fixes |
| `test_z_penalty.py` | Processing | `compute_z_penalty()` edge cases |
| `automated_suite/` | Infrastructure | Automated test runner (smoke, unit, functional, e2e, regression) |
| `data/` | Infrastructure | Test data fixtures and sample files |

## Fixture Architecture

All shared fixtures live in `conftest.py`. The hierarchy is:

```
in_memory_db          -- Empty schema via SQLModel.metadata.create_all()
  seeded_db_session   -- Pre-populated with 6 PlayerMatchStats, 12 RoundStats, 1 PlayerProfile
    seeded_player_stats  -- First PlayerMatchStats from seeded DB
    seeded_round_stats   -- First RoundStats from seeded DB

real_db_session       -- Opens production database.db (skips if absent)
  real_player_stats   -- First real PlayerMatchStats (skips if empty)
  real_round_stats    -- First real RoundStats (skips if empty)

mock_db_manager       -- In-memory DatabaseManager replacement with get_session() / upsert()
isolated_settings     -- Redirects user_settings.json to tmp_path, restores at teardown
torch_no_grad         -- Wraps test body in torch.no_grad() context
rap_model             -- Deterministic RAPCoachModel (CPU, seed=42, eval mode)
rap_inputs            -- Deterministic input tensors matching TrainingTensorConfig shapes
```

## Integration Test Gating

Tests marked `@pytest.mark.integration` are skipped by default. They read from the production
`database.db` and require real ingested demo data. To enable them:

```bash
CS2_INTEGRATION_TESTS=1 python -m pytest Programma_CS2_RENAN/tests/ -x -q
```

The `pytest_collection_modifyitems` hook in `conftest.py` applies the skip marker automatically
when the environment variable is unset.

## Virtual Environment Guard

The `conftest.py` venv guard prevents running tests outside the `cs2analyzer` virtual environment.
If `sys.prefix == sys.base_prefix` and neither `CI` nor `GITHUB_ACTIONS` is set, pytest exits
immediately with return code 2. This avoids confusing import failures when tests are accidentally
run with system Python.

## Running Tests

```bash
# Activate the virtual environment first
source ~/.venvs/cs2analyzer/bin/activate

# Run all tests (stop on first failure)
python -m pytest Programma_CS2_RENAN/tests/ -x -q

# Run a specific test file
python -m pytest Programma_CS2_RENAN/tests/test_features.py -v

# Run only integration tests
CS2_INTEGRATION_TESTS=1 python -m pytest Programma_CS2_RENAN/tests/ -m integration -v

# Run the automated suite
python -m pytest Programma_CS2_RENAN/tests/automated_suite/ -v
```

## Development Notes

- The `seeded_db_session` fixture provides CI-portable data that works on any machine without
  requiring `database.db`. Prefer it over `real_db_session` for new unit tests.
- Neural network tests use `torch_no_grad` and `rap_model` fixtures to ensure deterministic,
  gradient-free evaluation on CPU.
- The `isolated_settings` fixture snapshots and restores the in-memory `_settings` dict so
  tests that mutate configuration do not pollute subsequent tests in the same process.
- Test file naming follows `test_<module>.py`; test class naming follows `Test<Feature>`;
  individual test naming follows `test_<behavior>`.
