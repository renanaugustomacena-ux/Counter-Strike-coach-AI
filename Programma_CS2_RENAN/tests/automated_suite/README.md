# `tests/automated_suite/` — Layered automated test suite

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 5 (Testability)
> **Skill:** `/test-coverage`

## Purpose

Layered automated test suite that exercises the full Macena CS2 Analyzer stack at several levels of granularity. Tests in this directory complement the topic-organised pytest modules at the package root (`Programma_CS2_RENAN/tests/test_*.py`) — those tests are unit-oriented and grouped by domain; the tests in this sub-package are organised by **test type**.

The split exists so that CI can run a fast smoke-only stage, then gate slower stages on its success.

## File inventory

| File | Layer | Purpose |
|------|-------|---------|
| `__init__.py` | — | Package marker. |
| `test_smoke.py` | Smoke | Fastest gate — instantiates core managers, opens DB, loads config. Should run in seconds. Failure here means the build is fundamentally broken. |
| `test_unit.py` | Unit | Targeted unit tests across core utility functions that are not topic-specific (e.g. cross-cutting helpers, type coercions). |
| `test_functional.py` | Functional | Functional tests for end-to-end pipelines with mocked external dependencies — pipelines run in-memory, no real demos / network. |
| `test_e2e.py` | End-to-end | Real-or-fixture demo files run through the full ingestion → vectorisation → inference path. Heavier; gated behind `CS2_INTEGRATION_TESTS=1`. |
| `test_system_regression.py` | Regression | System-level regression checks: known-bad inputs, historical bug reproductions, golden-file comparisons. |

## Running

```bash
# Smoke only (fast)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py -v

# Smoke + unit (default CI fast lane)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py \
                   Programma_CS2_RENAN/tests/automated_suite/test_unit.py -v

# Functional (in-memory pipelines)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_functional.py -v

# Full suite including E2E (slow, requires demos)
CS2_INTEGRATION_TESTS=1 ./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/ -v

# Regression
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_system_regression.py -v
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
