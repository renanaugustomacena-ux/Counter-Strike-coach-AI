# `backend/processing/validation/` — Data integrity gates

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 1 (Correctness), Rule 4 (Data Persistence)
> **Skill:** `/correctness-check`, `/data-lifecycle-review`

## Purpose

This package owns the validation gates that protect every downstream consumer (training, inference, dashboard) from malformed input. Files here run at ingestion boundaries, training-batch boundaries, and at startup. They are the place where corrupt or unsafe data is supposed to fail loudly and early — silent degradation is a project red line (Rule 1).

## File inventory

| File | Module | Purpose | Key Exports |
|------|--------|---------|-------------|
| `__init__.py` | — | Empty package marker. | — |
| `dem_validator.py` | DEMValidator | Validates `.dem` file structure pre-parse: format pre-screen size bounds 100 KB – 800 MB, magic bytes (`PBDEMS2` CS2 / `HL2DEMO` CSGO), truncation check. Deliberately looser than the `DS-12` ingestion floor (`MIN_DEMO_SIZE = 10 MB`, enforced in `data_sources/demo_format_adapter.py`). | `DEMValidator`, `DEMValidationError`, `validate_dem_file()` |
| `drift.py` | Drift detection | Statistical drift detection across player feature distributions. Compares a recent rolling window (default 10) against past history and flags features whose z-score exceeds a threshold (default 2.5). | `detect_feature_drift()`, `DriftReport`, `DriftMonitor`, `TickFeatureDriftMonitor`, `should_retrain()` |
| `sanity.py` | Sanity checks | Range checks on parsed demo DataFrames against the `LIMITS` bounds table (HP, armor, equipment value, ...). Strict mode raises `ValueError`; non-strict mode clamps outliers. | `validate_demo_sanity()`, `validate_and_trim()` |
| `schema.py` | Schema | Versioned structural validation of demo parser output (`SCHEMA_VERSION = 2`: v1 core stats + `accuracy`). | `get_active_schema()`, `validate_demo_schema()` |

## Where each validator runs

```
.dem file lands in the ingest folder
    +-- validate_dem_file()                        [dem_validator.py]
    |     - rejects files outside 100 KB - 800 MB
    |     - rejects files with bad magic bytes
    |     - rejects truncated files
    |
    +-- pipeline parses the demo (demoparser2)
    |
    +-- parsed DataFrame: validate_demo_schema()   [schema.py]
    |     - required columns + types per SCHEMA_VERSION
    |
    +-- validate_demo_sanity() / validate_and_trim() [sanity.py]
    |     - HP / armor / equipment_value bounds (LIMITS)
    |     - strict: raise, non-strict: clamp outliers
    |
    +-- tick rows persisted to per-match SQLite

Training batch boundary
    +-- detect_feature_drift(...)                  [drift.py]
    |     - rolling-window z-score comparison
    |     - flags suspect player features before training
```

## Critical invariants

| ID | File / Line | Invariant |
|----|-------------|-----------|
| `DS-12` | `data_sources/demo_format_adapter.py` | `MIN_DEMO_SIZE = 10 MB` ingestion-acceptance floor. `dem_validator.py` is a deliberately looser format pre-screen (100 KB – 800 MB). |
| `P-VEC-02` / `P3-A` | upstream `vectorizer.py` | NaN / Inf clamp + > 5 % per-batch → `DataQualityError`. Validation here ensures the upstream gate cannot be bypassed. |

## Conventions

- **Fail loudly.** Validators raise typed exceptions (`DEMValidationError`) or `ValueError` with an explicit message — never degrade silently.
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
- Do not duplicate `MIN_DEMO_SIZE`. The constant lives in `data_sources/demo_format_adapter.py`; everywhere else imports it.
- Do not use validators for inference-time speculative checks ("if data looks weird, skip"). Validators decide; downstream code respects the decision.

## Related

- Demo parser: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Feature engineering: `Programma_CS2_RENAN/backend/processing/feature_engineering/README.md`
- Data quality module (training-side): `Programma_CS2_RENAN/backend/nn/data_quality.py`
- Lineage & metrics: `backend/storage/db_models.DataLineage`, `DataQualityMetric`
- Parent package: `Programma_CS2_RENAN/backend/processing/README.md`
