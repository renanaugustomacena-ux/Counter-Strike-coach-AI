# `backend/processing/validation/` — Data integrity gates

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 1 (Correctness), Rule 4 (Data Persistence)
> **Skill:** `/correctness-check`, `/data-lifecycle-review`

## Purpose

This package owns the validation gates that protect every downstream consumer (training, inference, dashboard) from malformed input. Files here run at ingestion boundaries, training-batch boundaries, and at startup. They are the place where corrupt or unsafe data is supposed to fail loudly and early — silent degradation is a project red line (Rule 1).

## File inventory

| File | Module | Purpose | Key Exports |
|------|--------|---------|-------------|
| `__init__.py` | — | Public re-exports for the validation package. | — |
| `dem_validator.py` | DemValidator | Validates `.dem` file structure pre-parse. Enforces `MIN_DEMO_SIZE = 10 MB` (invariant `DS-12`), checks magic bytes, rejects truncated files. | `DemValidator`, `validate_dem_file()` |
| `drift.py` | Drift detection | Statistical drift detection across player feature distributions. Compares last-N-match rolling distribution against the historical baseline; flags when KS-test p-value crosses a threshold. | `detect_feature_drift()`, `DriftReport` |
| `sanity.py` | Sanity checks | Lightweight runtime assertions on tick-level state (alive players have HP > 0, dead players have HP = 0, equipment value is non-negative, ...). | `assert_tick_sanity()` |
| `schema.py` | Schema | JSON schema validators for tournament-source ingestion. | `TOURNAMENT_JSON_SCHEMA`, `validate_tournament_json()` |

## Where each validator runs

```
.dem file lands in the ingest folder
    +-- DemValidator.validate_dem_file()           [dem_validator.py]
    |     - rejects files < MIN_DEMO_SIZE
    |     - rejects files with bad magic bytes
    |     - rejects truncated files
    |
    +-- pipeline parses the demo (demoparser2)
    |
    +-- per tick: assert_tick_sanity()              [sanity.py]
    |     - HP / armor / equipment_value bounds
    |     - alive vs dead state coherence
    |
    +-- tick rows persisted to per-match SQLite

JSON tournament feed
    +-- validate_tournament_json(payload)          [schema.py]
    |     - required keys present
    |     - per-map keys present
    |     - safe-int coercion (DS-04)

Training batch boundary
    +-- detect_feature_drift(...)                  [drift.py]
    |     - rolling distribution KS-test
    |     - flags suspect player features before training
```

## Critical invariants

| ID | File / Line | Invariant |
|----|-------------|-----------|
| `DS-12` | `dem_validator.py` | `MIN_DEMO_SIZE = 10 MB`. Smaller files are rejected (real CS2 demos are typically ≥ 50 MB). |
| `DS-04` | `schema.py` | `_safe_int()` coerces non-numeric JSON values to `0` rather than raising. |
| `P-VEC-02` / `P3-A` | upstream `vectorizer.py` | NaN / Inf clamp + > 5 % per-batch → `DataQualityError`. Validation here ensures the upstream gate cannot be bypassed. |

## Conventions

- **Fail loudly.** Validators raise typed exceptions (`DemValidationError`, `SchemaValidationError`, `DataQualityError`) — never return silent `None`.
- **Pure functions where possible.** Validators take inputs and return a verdict; they do not write to disk or the database.
- **Structured logging.** All failures log via `get_logger("cs2analyzer.validation.<module>")` with a stable error code so dashboards can aggregate.
- **Cheap checks first.** Order assertions from cheapest (size, magic bytes) to most expensive (statistical tests) so a broken file fails before the expensive paths run.

## Adding a new validator

1. Place it in this package, one file per concern.
2. Define a typed exception class (`<Domain>ValidationError`) and use it for all failure modes — never raise `RuntimeError`.
3. Add an entry to the inventory table above with a one-line purpose.
4. Wire it into the pipeline at the **earliest** boundary where the bad data could arrive.
5. Provide a unit test in `Programma_CS2_RENAN/tests/test_<domain>_validation.py`.

## Do not

- Do not silently coerce malformed input into "best-effort" values without recording the deviation in `DataLineage` / `DataQualityMetric`. Silent coercion violates Rule 1.
- Do not duplicate `MIN_DEMO_SIZE`. The constant lives here; everywhere else imports it.
- Do not use validators for inference-time speculative checks ("if data looks weird, skip"). Validators decide; downstream code respects the decision.

## Related

- Demo parser: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Feature engineering: `Programma_CS2_RENAN/backend/processing/feature_engineering/README.md`
- Data quality module (training-side): `Programma_CS2_RENAN/backend/nn/data_quality.py`
- Lineage & metrics: `backend/storage/db_models.DataLineage`, `DataQualityMetric`
- Parent package: `Programma_CS2_RENAN/backend/processing/README.md`
