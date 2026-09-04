# `reports/` — Generated audit & evaluation artefacts

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Generated artefact store (read-only by convention)

## What lives here

This directory collects machine-generated JSON reports produced by the project's evaluation, audit, and diagnostic tools. Files here are **outputs** of running scripts, not source documents. The directory ships empty (only the READMEs are tracked — `reports/*` is gitignored); reports accumulate locally as you run the tools.

```
reports/
├── assets/                               # MatchVisualizer PNG charts (fixed names, overwritten)
├── audit/                                # audit_scanner.py JSON outputs (via --output)
├── coach_answer_eval_<UTC-timestamp>.json  # tools/coach_answer_eval.py groundedness runs
├── eval_<UTC-timestamp>.json             # tools/eval_harness.py coaching-eval runs
└── hltv_seed_<timestamp>/                # seed_hltv_top_n.py run reports (pending_vision.json, …)
```

## File categories

| Pattern | Source | Purpose |
|---------|--------|---------|
| `eval_*.json` | `tools/eval_harness.py` | Coaching evaluation runs (timestamped) |
| `coach_answer_eval_*.json` | `tools/coach_answer_eval.py` | LLM answer-groundedness eval runs (timestamped) |
| `audit/*.json` | `tools/audit_scanner.py --output reports/audit/<name>.json` | Targeted subsystem audits |
| `hltv_seed_*/` | `tools/seed_hltv_top_n.py` (consumed by `seed_hltv_apply_vision.py`) | HLTV seeding run artefacts |
| `assets/*.png` | `Programma_CS2_RENAN/reporting/visualizer.py` (`MatchVisualizer`, cwd-relative default dir) | Heatmap / round-analysis charts |

(The `cs2_coach_bench` benchmark writes its own JSONL responses to `evals/cs2_coach_bench/reports/`, not here.)

## Conventions

- **JSON report filenames are timestamped** (`UTC` or local) so reports never overwrite each other. Exception: `assets/` PNGs use fixed names per map/plot and are overwritten on re-generation.
- **Reports are immutable.** Re-running a script produces a new file — never edit in place.
- **Reports are local-only.** `reports/*` is gitignored; keep old ones until storage pressure justifies pruning. Diff between consecutive reports reveals regressions.
- **No PII.** Reports contain demo names and player aliases but never raw credentials, Steam tokens, or HLTV API keys.

## Related

- Benchmark harness: `evals/README.md`
- Goliath operator: `goliath.py` at the repo root
- Validator output (separate stream): see `tools/headless_validator.py` (writes to stdout, not here)

## Cleanup

When the directory grows past a few hundred files, prune by age with:

```bash
find reports -name "eval_*.json" -mtime +90 -delete
```

Adjust thresholds to your retention preference. There is no automatic cleanup.
