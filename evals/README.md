# `evals/` — Evaluation Harness & Benchmarking

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Coaching quality assurance
> **Status:** Active — every coaching pipeline change must run the bench before merge.

## Purpose

This directory serves as the automated framework for measuring and validating the performance of the Counter-Strike AI coach. It provides a systematic way to benchmark the Large Language Models (LLM) and Vision-Language Models (VLM) against expert-curated tactical scenarios, producing quantifiable reports on regressions, hallucinations, and coverage drift.

## Technical Overview

The evaluation system operates as a closed-loop benchmarking harness. It simulates coaching requests using a standardized set of questions and compares the AI's responses against a strictly defined rubric. This process allows for quantifiable tracking of model improvements, regression detection, and accuracy validation across different map scenarios and strategic complexities.

## Key Components

### CS2 Coach Bench
Located in **`cs2_coach_bench/`**, this is the primary dataset for evaluation:
- **`questions.jsonl`**: A collection of 200+ diverse tactical questions covering utility usage, positioning, and round-state analysis.
- **`rubric.py` / `rubric.md`**: The gold-standard scoring criteria used to evaluate the quality, accuracy, and professional relevance of the coach's advice.
- **`run_eval.py`**: The execution engine that feeds the questions into the coach API and collects the raw model responses.
- **`score_responses.py`**: The validation script that compares model outputs against the rubric and generates final performance metrics (e.g., Accuracy, F1-score, Tactical Soundness).
- **`reports/`**: Generated per-run JSON reports for historical tracking.

## Directory Structure

```text
evals/
├── cs2_coach_bench/        # Primary benchmarking suite
│   ├── questions.jsonl     # Standardized evaluation questions
│   ├── rubric.md           # Expert-defined scoring criteria
│   ├── run_eval.py         # Execution script
│   ├── score_responses.py  # Scoring and validation script
│   └── reports/            # Per-match reports
├── README.md               # This documentation
├── README_IT.md            # Italian version
└── README_PT.md            # Portuguese version
```

## Usage

### 1. Run the Evaluation
Execute the benchmark against the current coach implementation (e.g., full pipeline or specific model):
```bash
# Full coaching pipeline (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 200

# Quick smoke (10 questions) against a specific model
python evals/cs2_coach_bench/run_eval.py --model gpt-4o --limit 10 --output results.json
```

### 2. Score the Results
Generate a performance report by scoring the collected responses:
```bash
python evals/cs2_coach_bench/score_responses.py --input results.json --rubric evals/cs2_coach_bench/rubric.md
```

### 3. Analyze Metrics
The system will output a detailed breakdown of performance by category (e.g., "Smoke Knowledge: 85%", "Economic Advice: 92%"). These metrics are used to gate production deployments and guide model fine-tuning efforts.

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
