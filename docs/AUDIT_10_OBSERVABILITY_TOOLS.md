# Audit Report 10 — Observability, Reporting & Tools

**Scope:** Observability, reporting, inner tools, root tools — 41 files, ~14,501 lines | **Date:** 2026-03-10
**Open findings:** 1 HIGH (arch debt) | 19 MEDIUM | 8 LOW

---

## HIGH — Acknowledged Debt

| ID | File | Finding |
|---|---|---|
| T10-H5 | Goliath_Hospital.py | 2894 lines, single class, 11 departments. Works correctly; size is maintainability concern. Tracked as architecture debt. |

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| — | sentry_setup.py | Sentry DSN empty-string vs None — init may be called with invalid DSN |
| — | visualizer.py | matplotlib.use("Agg") may conflict with other backends |
| — | visualizer.py | Plotting methods catch broad Exception without re-raise |
| — | analytics.py | AnalyticsEngine singleton not explicitly thread-safe |
| — | analytics.py | HLTV 2.0 rating weights may not match current formula |
| — | _infra.py | Severity enum duplicated in 3 places (Goliath, portability_test) |
| — | backend_validator.py | Import smoke tests overlap with headless_validator — cached imports mask failures |
| — | db_inspector.py | f-string SQL for table names (from introspection, not user input) |
| — | demo_inspector.py | Auto-discovers .dem files — symlink/network path resolution may fail |
| — | Goliath_Hospital.py | Timeout exception swallowed into generic "Timed out" message |
| — | Goliath_Hospital.py | _ONCOLOGY_LENGTH_EXCLUSIONS whitelist manually maintained |
| — | Goliath_Hospital.py | JSON report write not atomic (no temp+rename) |
| — | headless_validator.py (root) | CRITICAL_DIRS list (27) manually maintained |
| — | headless_validator.py (root) | Import lists (~130 modules) manually maintained |
| — | headless_validator.py (root) | Oversized function check capped at 3 violations — rest silently pass |
| — | seed_hltv_top20.py | Own path stabilization instead of _infra.py; hardcoded player stats will go stale |
| — | user_tools.py | Heartbeat PID check via `os.kill(pid, 0)` fails on Windows |
| — | portability_test.py | Triple-quote counting heuristic produces false positives/negatives |
| — | Sanitize_Project.py | Deletes database.db without backup |
| — | run_console_boot.py | `time.sleep(5)` hardcoded — should poll for readiness |
| — | verify_all_safe.py | 120s timeout per tool — worst case 30 minutes for 15 tools |
| — | observe_training_cycle.py + reset_pro_data.py + verify_main_boot.py | Missing venv guard |
| — | 6 root tools | Duplicated Rich boilerplate (~800 lines total) |
| — | Feature_Audit.py | Hardcoded parser column set can drift |
| — | dead_code_detector.py (root) | 150+ COMMON_NAMES entries manually maintained |
| — | db_health_diagnostic.py | Raw sqlite3 bypasses ORM WAL/timeout config |
| — | migrate_db.py | f-string SQL with hardcoded table names |
| — | Ultimate_ML_Coach_Debugger.py | Belief stability threshold 0.5 undocumented |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| — | project_snapshot.py | f-string SQL with KEY_TABLES constant |
| — | portability_test.py | 70+ SAFE_IMPORT_PATTERNS manually maintained |
| — | portability_test.py | Regex pattern recompilation per line per file |
| — | reset_pro_data.py | No venv guard |
| — | context_gatherer.py | O(n*m) AST walking — acceptable for current scale |
| — | audit_binaries.py + build_pipeline.py | Rich dependency not shared |
| — | verify_main_boot.py | No explicit venv guard |
| — | console.py + goliath.py | Logger names don't follow cs2analyzer.<module> convention |

## Cross-Cutting

1. **Duplicated Severity Enum** — 3 copies with different semantics (HIGH/MEDIUM/LOW vs CRITICAL/WARNING/INFO).
2. **Root Tools Lack Shared Framework** — 15 root tools each implement own venv guard, path stabilization, Rich imports (~800 lines duplication).
3. **Oversized Files** — Goliath_Hospital.py (2894 lines) and headless_validator.py (2733 lines) would benefit from decomposition.
