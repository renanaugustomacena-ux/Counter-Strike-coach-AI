# CS2 Coach Bench

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Benchmark de avaliação com 200 perguntas para a qualidade da AI de coaching de CS2.

## Quick Start

```bash
# Roda contra a pipeline de coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 10

# Roda contra Ollama bruto (sem RAG, isola o conhecimento do modelo)
python evals/cs2_coach_bench/run_eval.py --model ollama:llama3.1:8b --limit 10

# Pontua respostas manualmente
python evals/cs2_coach_bench/score_responses.py score --input reports/2026-04-12_coach.jsonl

# Imprime o resumo do scoring
python evals/cs2_coach_bench/score_responses.py summary --input reports/2026-04-12_coach.scored.jsonl

# Compara dois modelos
python evals/cs2_coach_bench/score_responses.py compare reports/model_a.scored.jsonl reports/model_b.scored.jsonl
```

## Estrutura

- `questions.jsonl` — 200 perguntas (40 por categoria)
- `rubric.md` — rubrica de scoring de 5 dimensões (0-3 cada, máximo de 15/pergunta)
- `run_eval.py` — Roda as perguntas em um modelo, salva respostas + latência
- `score_responses.py` — CLI de scoring manual + ferramentas de comparação
- `reports/` — Arquivos de resposta gerados (gitignored)

## Categorias

| Categoria | Quantidade | Testa |
|----------|-------|-------|
| map_tactics | 40 | Site executes, defaults, retakes, rotações |
| economy | 40 | Decisões de force/save, loss bonus, disciplina de eco |
| mid_round | 40 | Reads, rotações, vantagem numérica, timing |
| pro_knowledge | 40 | Comparações de jogadores, estratégias de times, análise de papéis |
| mechanics | 40 | Sub-tick, movement, timing de utility, spray |

## Dimensões de scoring

Veja `rubric.md` para descrições completas. Cada dimensão é 0-3:

1. **Tactical correctness** — o conselho está correto?
2. **CS2-currentness** — é CS2, não CSGO?
3. **Specificity** — genérico ou concreto?
4. **Pro grounding** — referencia pros reais?
5. **Actionability** — diz o que fazer?

## Critério de Ship (do COACH_QUALITY_ROADMAP)

`cs2coach` precisa superar o Llama 3.1 8B vanilla em >25% no score total E superar o GPT-4 em >5% nas dimensões CS2-currentness e pro-grounding.
