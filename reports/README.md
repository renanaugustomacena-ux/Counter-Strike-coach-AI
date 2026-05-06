# `reports/` — Generated audit & evaluation artefacts

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Generated artefact store (read-only by convention)

## What lives here

This directory collects machine-generated JSON reports produced by the project's evaluation, audit, and diagnostic tools. Files here are **outputs** of running scripts, not source documents — they are kept under version control as historical evidence.

```
reports/
├── audit/                                # Goliath audit JSON outputs
├── eval_<UTC-timestamp>.json             # cs2_coach_bench benchmark runs
└── goliath_hospital_<timestamp>.json     # Goliath hospital-mode (DB recovery) runs
```

## File categories

| Pattern | Source | Purpose |
|---------|--------|---------|
| `eval_*.json` | `evals/cs2_coach_bench/run_eval.py` | Coaching benchmark scoring |
| `goliath_hospital_*.json` | `goliath.py audit --hospital` | Database integrity scan |
| `audit/*.json` | `goliath.py audit` | Targeted module audits |

## Conventions

- **Filenames are timestamped** (`UTC` or local) so reports never overwrite each other.
- **Reports are immutable.** Re-running a script produces a new file — never edit in place.
- **Old reports are kept** until storage pressure justifies pruning. Diff between consecutive reports reveals regressions.
- **No PII.** Reports contain demo names and player aliases but never raw credentials, Steam tokens, or HLTV API keys.

## Related

- Benchmark harness: `evals/README.md`
- Goliath operator: `goliath.py` at the repo root
- Validator output (separate stream): see `tools/headless_validator.py` (writes to stdout, not here)

## Cleanup

When the directory grows past a few hundred files, prune by month with:

```bash
find reports -name "eval_*.json" -mtime +90 -delete
find reports -name "goliath_hospital_*.json" -mtime +60 -delete
```

Adjust thresholds to your retention preference. There is no automatic cleanup.
