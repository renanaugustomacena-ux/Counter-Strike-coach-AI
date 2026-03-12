# Audit Report 11 — Tests

**Scope:** 96 test files, ~19,345 lines | **Date:** 2026-03-10
**Open findings:** 4 HIGH | 86 MEDIUM | 153 LOW

---

## HIGH Findings

| ID | File | Finding |
|---|---|---|
| — | test_hybrid_engine.py:163 | `test_save_insights_to_db` writes to production DB via `get_db_manager()` |
| — | test_services.py | Almost entirely smoke tests — no functional logic exercised |
| — | test_training_orchestrator_logic.py:76 | Tautological: manually implements early stopping logic inline instead of testing production code |
| — | test_e2e.py + test_functional.py | Operate on production DB/config (mitigated via `isolated_settings` but still risky) |
| — | backend/nn/experimental/rap_coach/test_arch.py | Test file inside production source tree — packaged with prod code |
| — | tests/forensics/check_db_status.py | Not a test — queries prod DB at module-load time |
| — | tests/verify_chronovisor_real.py | Depends on real matches in production DB — always skips in CI |
| — | tests/verify_reporting.py | Connects to prod DB, writes files on disk, `shutil.rmtree` risk |

## Systemic MEDIUM Patterns (86 total)

### `__new__()` Constructor Bypass (12 files)
ExperienceBank, CoachingDialogueEngine, KnowledgeGraph, CoachingService, ChronovisorScanner, CoachTrainingManager, StateManager, DatabaseGovernor, TrainingController, ProfileService, ExperienceBank (round_utils), RAPStateReconstructor — all use `ClassName.__new__()` bypassing `__init__`, creating partially initialized objects that mask initialization bugs.

### Source Code Reading Anti-Pattern (6 files)
test_chronovisor_highlights.py, test_db_backup.py, test_demo_format_adapter.py, test_detonation_overlays.py — read raw .py source and do string matching instead of testing behavior.

### Production DB Access (5 remaining files)
test_system_regression.py (module-level), test_onboarding.py, test_rag_knowledge.py, test_auto_enqueue.py, test_onboarding_training.py — use `init_database()` or `get_db_manager()` touching production DB.

### Weak/Tautological Assertions
- `assert conf >= 0 or True` (always passes) — test_analysis_engines_extended.py
- `assert not ({})` tests Python semantics, not app code — test_coaching_service_contracts.py
- Conditional assertions `if SkillAxes.X in vec` — test_skill_model.py
- `isinstance(moments, list)` only — test_chronovisor_scanner.py
- `status != "INVALID"` weak negative — test_phase0_3_regressions.py

### Flaky Patterns
- `time.sleep(0.01)` for ordering — test_auto_enqueue.py
- Wall-clock latency tests — test_deployment_readiness.py
- 100 threads via ThreadPoolExecutor — test_phase0_3_regressions.py
- `datetime.now(UTC)` float rounding — test_temporal_baseline.py
- Non-deterministic embeddings — test_rag_knowledge.py
- `torch.randn()` without seed — test_arch.py

### Other MEDIUM
- Disjunctive assertion `"kills" in result or "below" in result` — test_coaching_engines.py
- Catches AttributeError but swallows all other exceptions — test_coaching_service_contracts.py
- `sys.modules` patching to make imports fail — test_coaching_service_fallback.py
- MagicMock without `spec=` (multiple files)
- `tempfile.mkstemp` with manual cleanup instead of `tmp_path` — test_demo_format_adapter.py
- Loss decrease fragility — test_rap_coach.py
- Only 5 tests for PlaybackEngine — test_playback_engine.py
- `mine_all_pro_stats` processes ALL pro players — test_pro_demo_miner.py
- Mixed unittest.TestCase + pytest — verify_chronovisor_logic.py, verify_chronovisor_real.py
- Diagnostic scripts masquerading as tests (9 files in tests/forensics/)

## Systemic LOW Patterns (153 total)

### Unused `import sys` (68 files)
Remnant of per-file sys.path manipulation centralized to conftest.py. Trivial cleanup.

### Coverage Gaps (~30 files)
Missing edge cases, boundary tests, NaN/negative inputs, concurrent access tests, multi-model tests across many files.

### Other LOW
- Duplicate test implementations (health range classification, mode selection, factory tests, dimension chain)
- Hardcoded feature indices instead of named constants
- Weak tolerance values in approx assertions
- Always-skipped CI tests (7 files depend on real data)
- Dead code in test files

## Cross-Cutting

1. **Production DB in Tests** — 5+ files still touch production database. Standardize on `mock_db_manager` or `seeded_db_session` fixtures.
2. **`__new__()` Bypass** — 12 files bypass constructors, masking `__init__` bugs. Replace with DI or `patch.__init__`.
3. **68 Unused `import sys`** — Trivial batch cleanup with high hygiene value.
4. **Scripts in Test Tree** — 9 diagnostic scripts in tests/forensics/ are not pytest-compatible. Move to tools/ or add ImportError guards.
