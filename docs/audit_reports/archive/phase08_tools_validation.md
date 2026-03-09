# Deep Audit Report — Phase 8: Tools + Validation Infrastructure

> **STATUS: HISTORICAL — All FIXED items removed (2026-03-08)**
> Cross-referenced against DEFERRALS.md. Only ACCEPTED design decisions and MONITORING items retained.

**Date:** 2026-02-27
**Files Audited:** 34 / 34
**Original Issues:** 38 (3 CRITICAL, 7 HIGH, 14 MEDIUM, 14 LOW)
**Remaining:** 12 (10 ACCEPTED + 2 MONITORING)

---

## Accepted Design Decisions (10)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F8-05 | `Goliath_Hospital.py:2012` | LOW | Health rating thresholds (>3 errors = ERROR, >10 warnings = WARNING) are heuristic. Adjust if project error/warning baseline changes |
| F8-07 | `headless_validator.py` | LOW | Schema validation uses in-memory SQLite for speed. Doesn't test WAL mode or concurrent access — tested separately |
| F8-12 | `db_inspector.py:315` | MEDIUM | `table_name` from SQLAlchemy introspection (not user input) — injection risk minimal. Bracket-quoting is SQLite-specific |
| F8-16 | `backend_validator.py` | LOW | Model Zoo uses `torch.randn()` inputs — smoke tests only, not accuracy tests |
| F8-18 | `dead_code_detector.py:22` | LOW | `apps/` excluded from dead-code analysis (KivyMD screens loaded dynamically via `MDScreenManager`) |
| F8-19 | `Goliath_Hospital.py` | LOW | Goliath Hospital uses `print()` for console output rather than structured logging. Acceptable for diagnostic tool |
| F8-20 | `Ultimate_ML_Coach_Debugger.py:100` | MEDIUM | Variance threshold 0.5 for neural belief stability is heuristic upper bound without empirical justification |
| F8-28 | `Ultimate_ML_Coach_Debugger.py` | LOW | Neural belief state and decision logic falsification tool |
| F8-29 | `Goliath_Hospital.py:1674` | LOW | `hflayers` is root-level custom implementation, not pip-installed; exempt from Pharmacy dependency checks |
| F8-33 | `Goliath_Hospital.py:2112` | LOW | `argparse` imported inside `main()` as lazy import — acceptable since module also imported by `goliath.py` orchestrator |

## Monitoring Items (2)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F8-06 | `Goliath_Hospital.py:1374` | LOW | Regex-based import scan matches "import" in comments and strings. Unlike `dead_code_detector.py` which uses AST parsing, Goliath's Oncology department relies on fragile regex. Provides heuristic estimate only |
| F8-11 | `context_gatherer.py:290` | LOW | Substring matching creates false reverse deps from comments/strings. Use `dead_code_detector.py` for accurate AST-based import analysis |
