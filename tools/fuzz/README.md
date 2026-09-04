# `tools/fuzz/` — Demo parser fuzz harness

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Robustness testing for the demo ingestion pipeline
> **Skill:** `/security-scan`, `/correctness-check`

## Purpose

This directory holds a fuzz-testing harness for the `demoparser2` library itself (maps to control C-SBX-02). Its job is to exercise the parser with malformed, truncated, and adversarial demo bytes and confirm that:

1. The parser does **not** segfault, panic, or hang on bad input.
2. Failures surface as Python exceptions (catchable, recoverable).

It deliberately bypasses the app's pre-validation gates (`MIN_DEMO_SIZE = 10 MB`, magic-byte check) and calls `demoparser2.DemoParser(...)` directly — the library's own robustness is the surface under test.

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `fuzz_demo_parser.py` | Main fuzzer. Generates random demo bytes (70% carrying the `PBDEMS2\0` magic prefix, up to 64 KiB) and feeds them to `demoparser2.DemoParser` + `parse_event("round_start")`. |

## Running the fuzzer

```bash
# Default run (30-minute time budget)
python tools/fuzz/fuzz_demo_parser.py

# Short run
python tools/fuzz/fuzz_demo_parser.py --time-budget 600 --seed 42

# Replay a single crash input (exit 1 if it reproduces)
python tools/fuzz/fuzz_demo_parser.py --reproduce .fuzz/crashes/<hash>-<size>.dem
```

When [Atheris](https://github.com/google/atheris) is installed, the run is coverage-guided; otherwise it falls back to a deterministic random-input loop (`--force-fallback` skips Atheris explicitly). Crash inputs are written to `--crash-dir` (default `.fuzz/crashes/`) as `<sha256-prefix>-<size>.dem` (first 16 hex chars of the SHA-256) plus a `.meta` sidecar recording the exception class and message.

## Failure modes the fuzzer protects against

- Truncated headers (parser must abort cleanly).
- Inconsistent message length fields (parser must not over-read).
- Invalid string-table indices (parser must not crash on out-of-range lookups).
- Random garbage with and without the `PBDEMS2\0` magic prefix.

In the application itself, junk this small never reaches the parser: the ingestion pre-validation gates (`MIN_DEMO_SIZE = 10 MB`, magic-byte check — invariant `DS-12`) reject it first. The fuzzer exists to harden the layer *behind* those gates.

## Related

- Demo parser wrapper: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Validation gate: `Programma_CS2_RENAN/backend/processing/validation/dem_validator.py`
- Ingestion pipeline: `Programma_CS2_RENAN/ingestion/pipelines/README.md`
- CI: nightly runs via `.github/workflows/fuzz-nightly.yml`; the harness logs to stdout/stderr (`logging.basicConfig`, logger `fuzz_demo_parser`).

## Do not

- Do **not** feed real user demos to the fuzzer — it generates its own scratch input; keep real demos out of `.fuzz/`.
- Do **not** disable the ingestion `MIN_DEMO_SIZE` guard because "the fuzzer passes" — the guard is the first line of defense in production.
- Do **not** commit failure-case demo files to the repo. `.fuzz/crashes/` stays local; capture the seed (or the `.meta` sidecar contents) and reproduce with `--reproduce` on demand.
