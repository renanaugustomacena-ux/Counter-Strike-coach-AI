# `tools/fuzz/` — Demo parser fuzz harness

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Robustness testing for the demo ingestion pipeline
> **Skill:** `/security-scan`, `/correctness-check`

## Purpose

This directory holds a fuzz-testing harness for the `demoparser2`-backed demo parser. Its job is to exercise the parser with malformed, truncated, and adversarial `.dem` files and confirm that:

1. The parser does **not** segfault, panic, or hang on bad input.
2. Failures surface as Python exceptions (catchable, recoverable).
3. The pre-validation gate (`MIN_DEMO_SIZE = 10 MB`, magic-byte check) rejects junk before the parser sees it.

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `fuzz_demo_parser.py` | Main fuzzer. Generates corrupted demo bytes and feeds them to `backend/data_sources/demo_parser.parse_demo()`. |

## Running the fuzzer

```bash
# Single iteration (smoke)
./.venv/bin/python tools/fuzz/fuzz_demo_parser.py --iterations 1

# Sustained fuzzing (CI / overnight runs)
./.venv/bin/python tools/fuzz/fuzz_demo_parser.py --iterations 10000 \
    --seed 42 --report /tmp/fuzz_report.json
```

The harness reports every failure mode it observes, with byte-offset of the corruption and the resulting exception class.

## Failure modes the fuzzer protects against

- Truncated headers (parser must abort cleanly).
- Inconsistent message length fields (parser must not over-read).
- Invalid string-table indices (parser must not crash on out-of-range lookups).
- Pathological tick density (parser must respect memory bounds).
- Files smaller than `MIN_DEMO_SIZE` (must be rejected before parsing — invariant `DS-12`).

## Related

- Demo parser: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Validation gate: `Programma_CS2_RENAN/backend/processing/validation/dem_validator.py`
- Ingestion pipeline: `Programma_CS2_RENAN/ingestion/pipelines/README.md`
- Structured logging: failures are emitted via `get_logger("cs2analyzer.fuzz")` and end up in `Programma_CS2_RENAN/logs/cs2_analyzer.log`.

## Do not

- Do **not** feed real user demos to the fuzzer — the corruption pass would destroy them. The harness generates its own scratch input.
- Do **not** disable the `MIN_DEMO_SIZE` guard to "speed up" fuzzing. The guard is part of the surface under test.
- Do **not** commit failure-case demo files to the repo. Capture the byte sequence (or seed) into the report and reproduce on demand.
