# R0 Baseline — captured 2026-08-14, branch chore/nuke-proof-audit @ f9ef694

Rule: no wave may later claim any red below as a "regression" — this is the pre-campaign truth.

## Environment

- Interpreter: `.venv\Scripts\python.exe` — Python 3.12.10, PySide6 6.11.0
- **pytest 9.1.1 in venv vs 8.3.4 pinned in requirements-dev.in** (drift, noted for B76/W4)
- pytest-cov OK · pytest-timeout OK · **hypothesis MISSING in venv** (declared in dev deps) · **ruff MISSING in venv** (declared in dev deps)
- Pre-commit hooks NOT installed in .git/hooks (local commits unguarded; CI lint leg runs pre-commit with SKIP=integrity-manifest-check,dev-health-quick)
- Windows symlink privilege NOT held (standard user, no Developer Mode) — see F-0003
- No python daemons running at baseline. database.db (123 MB) mtime churns when the default
  suite runs — default-gate tests open the production DB (WAL/shm churn; lens L3 candidate).
- DB safety snapshot taken to scratchpad db_backup_r0/ before integration tier.

## Gate results

### Default suite (full, Windows mirror of CI: `-p no:timeout` + cov)
`pytest Programma_CS2_RENAN/tests/ tests/ --tb=short -p no:timeout --cov=Programma_CS2_RENAN --cov-fail-under=33`

- **2 failed, 2500 passed, 48 skipped, 5 errors, 4 warnings — 77.3s — EXIT 1**
- Coverage **55.36%** (floor 33% passes; `coverage: platform win32`)
- FAILED `test_tick_rate_ssot.py::TestNoBareTickRateLiterals::test_production_code_has_no_bare_64` → **F-0002** (real defect: bare 64 in tactical_viewer_screen.py:416)
- FAILED+5 ERROR `test_match_data_dangling_symlink.py` (6 tests) → **F-0003** (WinError 1314, no symlink privilege; tests lack capability skipif)
- Warnings: `Unknown config option: timeout` (expected — plugin disabled by `-p no:timeout`), 3× SwigPy DeprecationWarning (opencv, cosmetic)
- test_ui_smoke.py: all 4 runtime-walk tests PASSED inside this run (screen walk, theme switching, language roundtrip, sidebar collapse/resize)

### Integrity manifest
`sync_integrity_manifest.py --verify-only` — **FAIL: 45 changed, 15 new, 0 removed** → **F-0001**
(root integrity_manifest.json also hashes phantom `Programma_CS2_RENAN/main.py`; two manifest files + .bak coexist)

### Headless validator
`tools/headless_validator.py` — **316/319 checks, 2 failed, 1 warning — VERDICT: FAIL — 10.3s — EXIT 1**
- [Structure] "No .qss theme files found in apps/qt_app/themes/" → **F-0005** (stale check: legacy .qss deliberately deleted in design mission; only base.qss.template is rendered now)
- [Integrity] manifest hash sampling: 3/10 mismatch (app.py, animation.py, app_state.py) → same root cause as **F-0001**
- Warning (non-blocking): optional dep `shap` not installed

### CI (GitHub)
- **ZERO workflow runs on feat/frontend-design-atlas** — build.yml triggers on
  `branches: [main, develop, 'feature/**', 'fix/**']` but the convention in use is `feat/*`
  (and now `chore/*`) → **F-0004** (P1). The 46-commit design branch was never CI-tested;
  `pull_request:` trigger would fire on PR creation (no PR exists yet).
- docs-only pushes are paths-ignored (`docs/**`) — audit-docs commits will not trigger CI even
  after the filter fix; that is correct behavior.

### Integration tier
`CS2_INTEGRATION_TESTS=1 pytest -m "integration and not slow" -q -p no:timeout`
- **3 failed, 35 passed, 1 skipped, 2516 deselected — 65.3s — EXIT 1** (DBs snapshotted to scratchpad db_backup_r0/ first)
- All 3 failures share ONE root cause → **F-0006**: a real demo under `get_pro_demo_base()`
  panics demoparser2 0.41.4 (`pyo3_runtime.PanicException: range end index 16 out of range
  for slice of length 12`, first_pass/parser.rs:82/92) and the panic BYPASSES the
  `except Exception` guard in run_ingestion._parse_demo_header_meta (:1108) despite its
  "never aborts" contract (:1099). Failing tests: test_ingestion_tickrate::test_real_overpass_demo_header_if_present,
  test_grenade_thrown_extraction::test_real_overpass_thrown_geq_detonated,
  tests/forensics/test_forensic_parser::test_extraction_pro_sample.

## Named UI evidence (per feedback memory)

From the default-suite run: test_qt_core, test_ui_smoke (4/4), test_ui_harness, test_charts,
test_detonation_overlays, test_tactical_frame_widgets all green inside the 2,500 passed.
Render matrix not refreshed at R0 (no UI change yet); current committed matrix is the
design-mission close state under docs/ux-audit/renders-atlas/.
