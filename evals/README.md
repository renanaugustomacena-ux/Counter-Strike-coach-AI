# `evals/` — Evaluation Harness & Benchmarking

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Coaching quality assurance
> **Status:** Active — every coaching pipeline change must run the bench before merge.

## Purpose

This directory serves as the automated framework for measuring and validating the performance of the Counter-Strike AI coach. It provides a systematic way to benchmark the coaching pipeline and its underlying Large Language Models (LLM) against expert-curated tactical scenarios, producing quantifiable reports on regressions, hallucinations, and coverage drift.

## Technical Overview

The evaluation system operates as a closed-loop benchmarking harness. It simulates coaching requests using a standardized set of questions and compares the AI's responses against a strictly defined rubric. This process allows for quantifiable tracking of model improvements, regression detection, and accuracy validation across different map scenarios and strategic complexities.

## Key Components

### CS2 Coach Bench
Located in **`cs2_coach_bench/`**, this is the primary dataset for evaluation:
- **`questions.jsonl`**: A collection of 200 tactical questions (40 per category across 5 categories) covering map tactics, economy, mid-round play, pro knowledge, and mechanics.
- **`rubric.md`**: The gold-standard scoring criteria — 5 dimensions scored 0-3 each (max 15 per question) — used to evaluate the quality, accuracy, and professional relevance of the coach's advice.
- **`run_eval.py`**: The execution engine that feeds the questions into a model backend (`coach` full pipeline or `ollama:<model>`) and collects the raw responses plus latency.
- **`score_responses.py`**: The scoring CLI (`score` / `summary` / `compare` subcommands) that applies the rubric to collected responses and compares models.
- **`reports/`**: Generated per-run JSONL response files (gitignored, created at first run).

## Directory Structure

```text
evals/
├── cs2_coach_bench/        # Primary benchmarking suite
│   ├── questions.jsonl     # Standardized evaluation questions
│   ├── rubric.md           # Expert-defined scoring criteria
│   ├── run_eval.py         # Execution script
│   ├── score_responses.py  # Scoring and comparison CLI
│   └── reports/            # Per-run response files (gitignored, generated)
├── README.md               # This documentation
├── README_IT.md            # Italian version
└── README_PT.md            # Portuguese version
```

## Usage

### 1. Run the Evaluation
Execute the benchmark against the current coach implementation (full pipeline or a raw Ollama model):
```bash
# Full coaching pipeline (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach

# Quick smoke (10 questions) against a raw Ollama baseline
python evals/cs2_coach_bench/run_eval.py --model ollama:llama3.1:8b --limit 10
```
Responses land in `cs2_coach_bench/reports/<date>_<model>.jsonl` by default (`--output` overrides; `--category` filters to one category).

### 2. Score the Results
Score the collected responses against the rubric, then summarize:
```bash
python evals/cs2_coach_bench/score_responses.py score --input evals/cs2_coach_bench/reports/<date>_coach.jsonl
python evals/cs2_coach_bench/score_responses.py summary --input evals/cs2_coach_bench/reports/<date>_coach.scored.jsonl
```

### 3. Analyze Metrics
The summary gives a per-category and per-dimension breakdown of rubric scores (5 dimensions, 0-3 each), and `score_responses.py compare a.scored.jsonl b.scored.jsonl` diffs two models. These metrics gate coaching-pipeline changes and guide model fine-tuning efforts (the bench itself runs locally; full-scale training and fine-tuning run on the dedicated Linux training machine, not this workstation).

## When to evaluate

Run the full benchmark before merging any change that touches:
- `Programma_CS2_RENAN/backend/coaching/`
- `Programma_CS2_RENAN/backend/services/coaching_service.py`
- `Programma_CS2_RENAN/backend/knowledge/` (Experience Bank, RAG)
- `Programma_CS2_RENAN/backend/services/llm_service.py`
- Pro player baselines or stat cards used by the Hybrid coach

## Related

- Coaching package: `Programma_CS2_RENAN/backend/coaching/README.md`
- Services layer: `Programma_CS2_RENAN/backend/services/README.md`
- Quality validator (regression gate): `tools/headless_validator.py`
- Offline pre-retrain metrics harness (feature drift, RAG recall@k, kNN purity): `tools/eval_harness.py`
- DB-grounded answer eval through the real dialogue engine: `tools/coach_answer_eval.py`
