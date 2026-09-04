# `tests/automated_suite/` — Layered automated test suite

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 5 (Testability)
> **Skill:** `/test-coverage`

## Purpose

Layered automated test suite that exercises the full Macena CS2 Analyzer stack at several levels of granularity. Tests in this directory complement the topic-organised pytest modules at the package root (`Programma_CS2_RENAN/tests/test_*.py`) — those tests are unit-oriented and grouped by domain; the tests in this sub-package are organised by **test type**.

The split keeps a fast smoke lane available and lets the slow suites be deselected with markers: `test_e2e.py` and `test_system_regression.py` are `slow`-marked, and the CI integration tier (`.github/workflows/build.yml`) runs `-m "integration and not slow"` to keep the monolith-scale runs out of its time budget.

## File inventory

| File | Layer | Purpose |
|------|-------|---------|
| `__init__.py` | — | Package marker. |
| `test_smoke.py` | Smoke | Fastest gate — imports core modules, initializes the DB, checks config (`METADATA_DIM=25`) and `ModelFactory` types. Should run in seconds. Failure here means the build is fundamentally broken. |
| `test_unit.py` | Unit | Targeted unit tests for cross-cutting helpers: `extract_match_stats()` aggregation logic and `LocalizationManager` language switching / fallback. |
| `test_functional.py` | Functional | User-settings persistence round-trip through the config layer, redirected to a temp file via the `isolated_settings` fixture — never touches the real `user_settings.json`. |
| `test_e2e.py` | End-to-end | Full lifecycle on real DB data: init, config, then a complete `CoachTrainingManager` training cycle. Marked `slow` + `integration`; gated behind `CS2_INTEGRATION_TESTS=1` and skip-gated on 5+ real `PlayerMatchStats`. |
| `test_system_regression.py` | Regression | `PlayerMatchStats` schema regression (pure model check, e.g. `dataset_split`) plus an `integration`-gated query against real data. Module marked `slow`. |

## Running

```bash
# Activate the virtual environment first (venv_win on Windows, venv_linux on Linux)

# Smoke only (fast)
python -m pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py -v

# Smoke + unit (fast lane)
python -m pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py \
                 Programma_CS2_RENAN/tests/automated_suite/test_unit.py -v

# Functional (in-memory, isolated settings)
python -m pytest Programma_CS2_RENAN/tests/automated_suite/test_functional.py -v

# Full suite including E2E (slow, requires real ingested data)
CS2_INTEGRATION_TESTS=1 python -m pytest Programma_CS2_RENAN/tests/automated_suite/ -v

# Regression
python -m pytest Programma_CS2_RENAN/tests/automated_suite/test_system_regression.py -v
```

## CI staging recommendation

Stage tests so a failing smoke aborts the run cheaply:

```
1. Smoke           (seconds)     -> blocks all later stages on failure
2. Unit            (~1 min)      -> blocks functional / e2e on failure
3. Functional      (~5 min)      -> blocks e2e on failure
4. Regression      (~5 min)      -> independent of e2e
5. E2E             (~30+ min)    -> only on staged / nightly runs
```

## Conventions

- **Smoke is for sanity, not coverage.** Prefer ten 50 ms tests over one 5 s test — fast feedback is more valuable than thorough validation at this layer.
- **Functional tests must mock external systems.** No network, no real demo files, no Ollama, no Steam API. Use the fixtures in `Programma_CS2_RENAN/tests/conftest.py`.
- **E2E tests gate behind `CS2_INTEGRATION_TESTS=1`.** This is the standard project-wide flag for slow, real-data tests.
- **Regression tests freeze prior bugs as fixtures.** When a bug is fixed, add the failing input as a regression case so it cannot silently come back.

## Where to put a new test

| Question | Answer |
|----------|--------|
| Is it about a single function or class? | `Programma_CS2_RENAN/tests/test_<topic>.py` (the topic-organised root) |
| Is it a sub-second sanity check that the build is alive? | `automated_suite/test_smoke.py` |
| Is it a cross-module pipeline test with mocks? | `automated_suite/test_functional.py` |
| Does it require real demos / external systems? | `automated_suite/test_e2e.py` (gated) |
| Is it a "this bug must never come back" lock-in? | `automated_suite/test_system_regression.py` |

## Related

- Topic-organised tests (root): `Programma_CS2_RENAN/tests/README.md`
- Shared fixtures: `Programma_CS2_RENAN/tests/conftest.py`
- Validator (separate gate): `tools/headless_validator.py` — run after pytest, not in place of it.
- RAP smoke (added in Phase 0): `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py`
