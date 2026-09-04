# CS2 Coach Bench

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

200-question evaluation benchmark for CS2 coaching AI quality.

## Quick Start

```bash
# Run against the full coaching pipeline (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 10

# Run against raw Ollama (no RAG, isolates model knowledge)
python evals/cs2_coach_bench/run_eval.py --model ollama:llama3.1:8b --limit 10

# Score responses manually
python evals/cs2_coach_bench/score_responses.py score --input evals/cs2_coach_bench/reports/2026-04-12_coach.jsonl

# Print scoring summary
python evals/cs2_coach_bench/score_responses.py summary --input evals/cs2_coach_bench/reports/2026-04-12_coach.scored.jsonl

# Compare two models
python evals/cs2_coach_bench/score_responses.py compare evals/cs2_coach_bench/reports/model_a.scored.jsonl evals/cs2_coach_bench/reports/model_b.scored.jsonl
```

## Structure

- `questions.jsonl` — 200 questions (40 per category)
- `rubric.md` — 5-dimension scoring rubric (0-3 each, max 15/question)
- `run_eval.py` — Runs questions through a model, saves responses + latency
- `score_responses.py` — Manual scoring CLI (`score` / `summary` / `compare` subcommands)
- `reports/` — Generated response files (gitignored, created on first run)

## Categories

| Category | Count | Tests |
|----------|-------|-------|
| map_tactics | 40 | Site executes, defaults, retakes, rotations |
| economy | 40 | Force/save decisions, loss bonus, eco discipline |
| mid_round | 40 | Reads, rotations, number advantage, timing |
| pro_knowledge | 40 | Player comparisons, team strats, role analysis |
| mechanics | 40 | Sub-tick, movement, utility timing, spray |

## Scoring Dimensions

See `rubric.md` for full descriptions. Each 0-3:

1. **Tactical correctness** — is the advice right?
2. **CS2-currentness** — CS2, not CSGO?
3. **Specificity** — generic or concrete?
4. **Pro grounding** — references real pros?
5. **Actionability** — tells you what to do?

## Ship Criterion

`cs2coach` (the planned fine-tuned coach model) must beat vanilla Llama 3.1 8B by >25% on total score AND beat GPT-4 by >5% on CS2-currentness and pro-grounding dimensions.

Notes: the criterion originated in the retired `COACH_QUALITY_ROADMAP` doc (consolidated away on 2026-05-03, see `docs/DIAGNOSIS_2026-05.md`) — this README now carries it. Fine-tuning runs on the dedicated Linux training machine, not this workstation. `run_eval.py` only wires the `coach` and `ollama:<model>` backends, so the GPT-4 baseline must be collected externally and scored with the same rubric.
