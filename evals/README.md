# `evals/` — Evaluation harnesses

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Coaching quality assurance
> **Status:** Active — every coaching pipeline change must run the bench before merge.

## Purpose

This directory holds offline evaluation harnesses for the Macena CS2 Analyzer's coaching outputs. Evaluations run independently of the live application and produce JSON reports that quantify regressions, hallucinations, and coverage drift between coaching engine versions.

## Layout

```
evals/
└── cs2_coach_bench/      # 200-question coaching benchmark
    ├── README.md
    ├── run_eval.py       # CLI entry point
    ├── questions.jsonl   # Curated question set
    ├── rubric.py         # Scoring criteria
    └── reports/          # Generated per-run JSON reports
```

## Running an evaluation

```bash
# Full coaching pipeline (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 200

# Quick smoke (10 questions)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 10
```

Reports are written to `reports/eval_<timestamp>.json` at the repo root and are intended to be diffed across runs.

## When to evaluate

Run the full benchmark before merging any change that touches:

- `Programma_CS2_RENAN/backend/coaching/`
- `Programma_CS2_RENAN/backend/services/coaching_service.py`
- `Programma_CS2_RENAN/backend/knowledge/` (Experience Bank, RAG)
- `Programma_CS2_RENAN/backend/services/llm_service.py`
- Pro player baselines or stat cards used by the Hybrid coach

For the full benchmark protocol, scoring rubric, and sample report shape see `cs2_coach_bench/README.md`.

## Related

- Coaching package: `Programma_CS2_RENAN/backend/coaching/README.md`
- Services layer: `Programma_CS2_RENAN/backend/services/README.md`
- Quality validator (regression gate): `tools/headless_validator.py`
