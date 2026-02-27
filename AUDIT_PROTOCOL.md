# AUDIT PROTOCOL: TEST & TOOL INTEGRITY VERIFICATION

## 1. CORE MANDATE: THE ANTI-PLACEBO STANDARD

The primary objective is the identification and documentation of **mocks, false positives, and false negatives** across the entire test suite and all tool/validation scripts — including the console command systems.

This extends the original "Placebo Logic" mandate. The audit targets code that:

* **Appears to validate** but actually asserts on meaningless conditions (false positive).
* **Appears to test real behavior** but substitutes synthetic/mocked data where empirical data from the database is required (mock contamination).
* **Appears to catch problems** but silently skips, swallows, or misclassifies real failures (false negative).
* **Reports "OK" or "PASS"** without verifying the underlying operation actually succeeded (tool false positive).

The three primary detection targets are defined precisely:

1. **Mock Contamination:** Usage of `MagicMock`, `@patch`, synthetic `DataFrame` construction, `torch.randn` as model input, or any fabricated data structure where real DB records from `database.db` or per-match Tier 3 SQLite files should be used. The ONLY acceptable mock targets are external HTTP boundaries (Steam API, Ollama, HLTV) and controlled scalar inputs for pure math/formula unit tests.

2. **False Positives:** Tests that PASS but do not validate what they claim. Indicators include: `assert True`, assertions on the return type only (e.g., `assert isinstance(result, dict)`) without checking content, `try/except` that catches the assertion error itself, tool checks that `return True` unconditionally or inside a bare `except`, and subprocess calls whose exit codes are never inspected.

3. **False Negatives / Phantom SKIPs:** Tests that FAIL or SKIP on valid conditions (e.g., `pytest.skip("no data")` when data exists in the DB), tool checks that miss real problems because the check logic is incomplete or the error is swallowed before reaching the reporting layer, and `except Exception: pass` blocks that hide diagnostic failures.

---

## 2. OPERATIONAL GUARDRAILS

* **READ-ONLY ANALYSIS:** Under no circumstances shall any project script be modified, moved, deleted, or "fixed" during the audit phase. The audit produces a report, not a patch.
* **SINGLE-FILE FOCUS:** Audits must proceed one file at a time. No jumping between multiple files unless tracing a specific data contamination path or verifying a cross-file delegation (e.g., `console.py` → `backend/control/console.py`).
* **LINE-BY-LINE SCRUTINY:** Every assertion, `pytest.skip` gate, exception handler, subprocess call, and tool check verdict must be individually examined. No function is "probably fine."
* **NO SUMMARIZATION:** Avoid high-level marketing-style summaries. Findings must be reported with exact file paths, line numbers, and verbatim code snippets as "receipts." A finding without a line number is not a finding.
* **ZERO-MODIFICATION POLICY:** The only files permitted for writing are `AUDIT_PROTOCOL.md` (this file) and the output report `tool_reporting.md`. No other file in the project may be touched.

---

## 3. SCOPE — FILES UNDER AUDIT

Every file listed below MUST receive its own numbered section in `tool_reporting.md`, even if the verdict is PASS. No file is exempt.

### 3.1 Console Systems (PRIORITY — audit these first)

These are the highest-priority targets. Every command must be individually verified.

| # | File | Description |
|---|------|-------------|
| 1 | `console.py` | Root CLI — ~44 commands across 10 categories (ml, ingest, build, test, sys, set, svc, maint, tool, help) |
| 2 | `Programma_CS2_RENAN/backend/control/console.py` | Backend singleton — ServiceSupervisor, MLController, IngestionManager, DatabaseGovernor |

**Per-command audit checklist** (apply to every registered command):

* Does the handler function exist and match the registered name?
* Does the handler do what the help text claims it does?
* Are there `except Exception` blocks that return `"[success]"` or `"[error]"` without logging the actual exception to structured logs?
* For subprocess-based commands (`build run`, `test all`, `tool demo`, etc.): is the subprocess exit code checked? Does a non-zero exit code propagate as a failure to the user?
* For DB-mutating commands (`maint clear-queue`, `maint prune`, `sys vacuum`): is there transaction safety? Is the result verified after mutation?
* For status-reporting commands (`ml status`, `ingest status`, `sys status`): are the reported values sourced from real state, or do any fall back to hardcoded defaults on exception?
* Does the TUI dashboard `get_system_status()` call handle failures transparently, or does it return `{}` silently?

### 3.2 Test Suite (38 files)

| # | File |
|---|------|
| 1 | `Programma_CS2_RENAN/tests/conftest.py` |
| 2 | `Programma_CS2_RENAN/tests/test_analysis_engines.py` |
| 3 | `Programma_CS2_RENAN/tests/test_analysis_orchestrator.py` |
| 4 | `Programma_CS2_RENAN/tests/test_auto_enqueue.py` |
| 5 | `Programma_CS2_RENAN/tests/test_chronovisor_highlights.py` |
| 6 | `Programma_CS2_RENAN/tests/test_db_backup.py` |
| 7 | `Programma_CS2_RENAN/tests/test_debug_ingestion.py` |
| 8 | `Programma_CS2_RENAN/tests/test_dem_validator.py` |
| 9 | `Programma_CS2_RENAN/tests/test_demo_format_adapter.py` |
| 10 | `Programma_CS2_RENAN/tests/test_demo_parser.py` |
| 11 | `Programma_CS2_RENAN/tests/test_detonation_overlays.py` |
| 12 | `Programma_CS2_RENAN/tests/test_drift_and_heuristics.py` |
| 13 | `Programma_CS2_RENAN/tests/test_features.py` |
| 14 | `Programma_CS2_RENAN/tests/test_game_theory.py` |
| 15 | `Programma_CS2_RENAN/tests/test_hybrid_engine.py` |
| 16 | `Programma_CS2_RENAN/tests/test_integration.py` |
| 17 | `Programma_CS2_RENAN/tests/test_jepa_model.py` |
| 18 | `Programma_CS2_RENAN/tests/test_map_manager.py` |
| 19 | `Programma_CS2_RENAN/tests/test_models.py` |
| 20 | `Programma_CS2_RENAN/tests/test_onboarding.py` |
| 21 | `Programma_CS2_RENAN/tests/test_onboarding_training.py` |
| 22 | `Programma_CS2_RENAN/tests/test_phase1_improvements.py` |
| 23 | `Programma_CS2_RENAN/tests/test_playback_engine.py` |
| 24 | `Programma_CS2_RENAN/tests/test_pro_demo_miner.py` |
| 25 | `Programma_CS2_RENAN/tests/test_rag_knowledge.py` |
| 26 | `Programma_CS2_RENAN/tests/test_round_stats_enrichment.py` |
| 27 | `Programma_CS2_RENAN/tests/test_security.py` |
| 28 | `Programma_CS2_RENAN/tests/test_services.py` |
| 29 | `Programma_CS2_RENAN/tests/test_skill_model.py` |
| 30 | `Programma_CS2_RENAN/tests/test_spatial_and_baseline.py` |
| 31 | `Programma_CS2_RENAN/tests/test_spatial_engine.py` |
| 32 | `Programma_CS2_RENAN/tests/test_storage_cloud.py` |
| 33 | `Programma_CS2_RENAN/tests/test_tactical_features.py` |
| 34 | `Programma_CS2_RENAN/tests/test_temporal_baseline.py` |
| 35 | `Programma_CS2_RENAN/tests/test_visualization.py` |
| 36 | `Programma_CS2_RENAN/tests/test_z_penalty.py` |

Additionally, the following automated suite files if they exist under `tests/automated_suite/`:

| # | File |
|---|------|
| 37 | `Programma_CS2_RENAN/tests/automated_suite/test_functional.py` |
| 38 | `Programma_CS2_RENAN/tests/automated_suite/test_e2e.py` |
| 39 | `Programma_CS2_RENAN/tests/automated_suite/test_smoke.py` |
| 40 | `Programma_CS2_RENAN/tests/automated_suite/test_unit.py` |
| 41 | `Programma_CS2_RENAN/tests/automated_suite/test_system_regression.py` |

### 3.3 Backend Tool Scripts (9 files)

| # | File | Purpose |
|---|------|---------|
| 1 | `Programma_CS2_RENAN/tools/_infra.py` | Shared infrastructure for tool scripts |
| 2 | `Programma_CS2_RENAN/tools/backend_validator.py` | Build-level validation (40 checks) |
| 3 | `Programma_CS2_RENAN/tools/brain_verify.py` | 118-rule AI intelligence verification |
| 4 | `Programma_CS2_RENAN/tools/build_tools.py` | Build orchestration utilities |
| 5 | `Programma_CS2_RENAN/tools/demo_inspector.py` | Demo file inspection |
| 6 | `Programma_CS2_RENAN/tools/Goliath_Hospital.py` | 10-department comprehensive diagnostic |
| 7 | `Programma_CS2_RENAN/tools/ui_diagnostic.py` | UI/KV integrity checks |
| 8 | `Programma_CS2_RENAN/tools/Ultimate_ML_Coach_Debugger.py` | ML debugging tool |
| 9 | `Programma_CS2_RENAN/tools/user_tools.py` | User-facing tool utilities |

### 3.4 Root Tool Scripts (11 files)

| # | File | Purpose |
|---|------|---------|
| 1 | `tools/audit_binaries.py` | Binary file audit |
| 2 | `tools/build_pipeline.py` | Build pipeline orchestration |
| 3 | `tools/dead_code_detector.py` | Dead code analysis |
| 4 | `tools/dev_health.py` | Developer environment health |
| 5 | `tools/Feature_Audit.py` | Feature engineering audit |
| 6 | `tools/generate_manifest.py` | Integrity manifest generator |
| 7 | `tools/headless_validator.py` | Gate-level regression validator (79 checks) |
| 8 | `tools/migrate_db.py` | Database migration runner |
| 9 | `tools/portability_test.py` | Cross-platform portability test |
| 10 | `tools/Sanitize_Project.py` | Project cleanup tool |
| 11 | `tools/verify_all_safe.py` | Security surface check |

### 3.5 Brain Verification Suite (18 files)

| # | File |
|---|------|
| 1 | `Programma_CS2_RENAN/tools/brain_verification/_common.py` |
| 2-17 | `Programma_CS2_RENAN/tools/brain_verification/sec01_foundational_intelligence.py` through `sec16_decision_framework.py` |

---

## 4. DETECTION CATEGORIES

Audits must specifically search for and flag:

### Original Categories (retained)

* **Hardcoded Placebos:** Static values (e.g., `std=0.0`, `rating=1.0`) injected where empirical data is missing. In tool scripts, this includes checks that compare against hardcoded thresholds without documenting the source of truth.
* **Circular Brain Logic:** AI models trained on labels generated by the programmer's own hardcoded heuristics (e.g., `ConceptLabeler`). In tests, this includes assertions where the expected value was copy-pasted from the implementation itself.
* **Silent Fail Networks:** `except` blocks that swallow critical errors and return "safe" but meaningless defaults (e.g., `return (0.0, 0.0)` or `pass`). In tools, this includes `except Exception: pass` in diagnostic checks that should report failures.
* **Validation Blindness:** Test scripts that use `torch.randn` or random noise to validate "success" instead of using real-world data from the partitioned databases. In tool checks, this includes assertions on model `.forward()` with random inputs instead of representative feature vectors.
* **Redundant Bloat:** Double-writing logic, duplicate test coverage that creates maintenance burden, or tool checks that test the same condition from multiple entry points without added value.

### New Categories (added)

* **Mock Contamination:** Usage of `MagicMock`, `unittest.mock.patch`, `@patch`, synthetic `pd.DataFrame()` construction, or any fabricated data structure where real DB records should be used. The ONLY acceptable mock targets are: (a) external HTTP services (Steam, Ollama, HLTV, Faceit), (b) controlled scalar inputs for pure math/formula functions. Everything else must use real data from `database.db` or Tier 3 per-match SQLite files, with `pytest.skip` gates when data is unavailable.

* **False Positive Tests:** Tests that PASS but do not actually validate correctness. Indicators:
  - `assert True` or `assert result is not None` as the only assertion
  - `isinstance()` checks without content validation
  - `try: <operation>; except: pytest.skip()` patterns that hide real import/runtime errors
  - Assertions on `.shape` or `.dtype` only, without verifying tensor values are meaningful
  - Tool checks that `return True` inside a `try/except` without verifying the operation's output

* **False Negative / Phantom SKIPs:** Tests that FAIL or SKIP when they should PASS, or tool checks that miss real problems. Indicators:
  - `pytest.skip("no data")` when `database.db` contains qualifying records
  - `except ImportError: skip` for modules that ARE installed in the environment
  - Tool checks that catch errors and report "WARNING" instead of "FAIL" for critical conditions
  - Brain verification rules that return `SKIP` instead of `FAIL` when required models/data are absent

---

## 5. WORKFLOW STEPS

1. **Select:** Identify the next file in the audit scope (Section 3). Console systems (3.1) are audited FIRST, then test suite (3.2), then tool scripts (3.3–3.5).
2. **Read:** Perform a full read of the script. For files exceeding 500 lines, read in sequential chunks — never skip sections.
3. **Audit:** Trace every assertion, skip gate, exception handler, subprocess call, and return value. For console commands, verify each handler against its registered help text.
4. **Document:** Add findings to `tool_reporting.md` with line-level evidence, following the reporting format specified in Section 6.
5. **Halt:** Stop and wait for explicit user instruction before proceeding to the next file. Never batch multiple files into a single audit pass.

---

## 6. REPORTING FORMAT — `tool_reporting.md`

All findings must be written to `tool_reporting.md` following the exact format used in `DETAILED_REMEDIATION_PLAN.md`:

### Document Header

```markdown
# Tool & Test Integrity Report — Macena CS2 Analyzer
## Mock / False Positive / False Negative Audit (YYYY-MM-DD)

**Total Files Audited: X / Y**
**Issues Found: N**
**CRITICAL: A | HIGH: B | MEDIUM: C | LOW: D**
```

### Per-File Section Format

```markdown
---

## [N]. [File Name]

### Status: [PASS | WARNING | FAIL | CRITICAL]
**File:** `[full/relative/path.py]`

### Findings

* **Line [X]** — `[exact code snippet]`
  **Classification:** [Mock Contamination | False Positive | False Negative | Silent Fail | ...]
  **Severity:** [CRITICAL | HIGH | MEDIUM | LOW]
  **Evidence:** [Explanation of WHY this is a problem, with the specific expected behavior vs actual behavior]

* **Line [Y]-[Z]** — `[exact code snippet]`
  ...

### Action
* [Concrete remediation step 1]
* [Concrete remediation step 2]
```

### Severity Definitions

* **CRITICAL:** The finding causes the test/tool to report a fundamentally incorrect result (false PASS on broken logic, false FAIL on correct logic, or complete diagnostic blindness).
* **HIGH:** The finding undermines confidence in the test/tool result but doesn't fully invert it (e.g., partial mock contamination, incomplete assertion coverage).
* **MEDIUM:** The finding is a code quality issue that could become HIGH under changed conditions (e.g., fragile skip gates, hardcoded thresholds without documentation).
* **LOW:** The finding is a maintainability concern that doesn't affect current correctness (e.g., redundant assertions, dead test code).

---

## 7. CONSOLE AUDIT CHECKLIST

This section defines the per-command audit procedure for the console systems. Apply this checklist to **every registered command** in `console.py` and every public method in `backend/control/console.py`.

### Root Console (`console.py`) — Command Categories

| Category | Commands | Count |
|----------|----------|-------|
| `ml` | start, stop, pause, resume, throttle, status | 6 |
| `ingest` | start, stop, mode, status | 4 |
| `build` | run, verify, manifest | 3 |
| `test` | all, headless, backend, ui, hospital, suite | 6 |
| `sys` | status, audit, baseline, db, vacuum, resources | 6 |
| `set` | steam, faceit, config, view | 4 |
| `svc` | restart, kill-all, spawn, status | 4 |
| `maint` | clear-cache, clear-queue, sanitize, dead-code, prune | 5 |
| `tool` | demo, user, logs, list | 4 |
| `help/exit` | help, exit | 2 |
| **Total** | | **44** |

### Per-Command Verification Criteria

For each of the 44 commands, the audit must answer:

1. **Handler Exists?** — Is the registered handler function defined and reachable?
2. **Help Text Accurate?** — Does the help string describe what the handler actually does?
3. **Exception Handling Sound?** — Are exceptions logged with structured logging (`get_logger`)? Are they surfaced to the user, or swallowed?
4. **Success Verification?** — When the command reports success (`[success]`), was the underlying operation's result actually checked?
5. **Subprocess Exit Codes?** — For commands that spawn subprocesses, is `returncode` inspected? Is a non-zero exit code reported as failure?
6. **State Mutation Safety?** — For commands that mutate DB or filesystem state, is there transaction safety? Is the result verified post-mutation?
7. **Fallback Defaults?** — On exception, does the command fall back to hardcoded defaults that could mislead the user (e.g., returning `{}` for status)?

### Backend Console (`backend/control/console.py`)

Verify the following for the singleton:

* **Initialization:** Does `__init__` create all four subsystems (Supervisor, Ingestion, DB Governor, ML Controller) with real dependencies, not stubs?
* **boot():** Does it verify services are actually running after starting them?
* **shutdown():** Does it confirm all services stopped, or does it fire-and-forget?
* **get_system_status():** Are all status fields sourced from live queries, or do any use cached/stale data?
* **_audit_databases():** Does `PRAGMA integrity_check` result actually influence the reported health, or is it discarded?
* **ML delegations:** Do `start_training()`, `stop_training()`, `pause_training()`, `resume_training()` verify the operation took effect?

---

## 8. TECHNICAL PRECISION MANDATE

This section is non-negotiable. Every finding recorded in `tool_reporting.md` MUST satisfy ALL of the following:

1. **File Path:** Full relative path from project root (e.g., `Programma_CS2_RENAN/tests/test_models.py`).
2. **Line Number(s):** Exact line or line range where the issue occurs. A finding without a line number is rejected.
3. **Code Snippet:** Verbatim copy of the offending code, sufficient to locate it unambiguously. Minimum 1 line, maximum 10 lines.
4. **Classification:** Exactly one of the detection categories from Section 4.
5. **Severity:** Exactly one of CRITICAL / HIGH / MEDIUM / LOW per the definitions in Section 6.
6. **Evidence:** A technical explanation of WHY this is a problem. Must describe: (a) what the code claims to do, (b) what it actually does, and (c) the concrete consequence of the gap.

### Explicitly Forbidden

* **No "this area looks fine"** — either provide specific passing evidence (e.g., "Line 45: assertion checks `result.rating` against DB value — CORRECT") or document a specific failure.
* **No "generally good quality"** — every function/test/check gets its own verdict.
* **No severity inflation** — do not mark something CRITICAL just to appear thorough. Apply the definitions strictly.
* **No severity deflation** — do not mark something LOW to avoid uncomfortable findings. A false positive in a gate validator is CRITICAL by definition.
* **Exhaustive coverage** — every file in Section 3 receives a section in `tool_reporting.md`. Files with no issues get a brief PASS section with evidence of what was checked.

---

## 9. REJECTION OF SPEED

Speed is recognized as an indicator of "Inaptitude" and "Laziness." The protocol requires a deliberate, slow pace to ensure no mock, no false positive, and no false negative is missed. Rushing through a file to "get to the next one" is a violation of this contract. A single file audited thoroughly is worth more than ten files skimmed.
