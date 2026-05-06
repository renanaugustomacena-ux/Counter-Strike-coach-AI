# `evals/` — Harnesses de avaliação

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Garantia de qualidade do coaching
> **Status:** Ativo — toda mudança na pipeline de coaching deve executar o bench antes do merge.

## Propósito

Este diretório hospeda os harnesses de avaliação offline para as saídas de coaching do Macena CS2 Analyzer. As avaliações rodam independentemente da aplicação ao vivo e produzem relatórios JSON que quantificam regressões, alucinações e drift de cobertura entre versões do motor de coaching.

## Layout

```
evals/
└── cs2_coach_bench/      # Benchmark de coaching com 200 perguntas
    ├── README.md
    ├── run_eval.py       # Entry point CLI
    ├── questions.jsonl   # Conjunto de perguntas curado
    ├── rubric.py         # Critérios de scoring
    └── reports/          # Relatórios JSON gerados por execução
```

## Executando uma avaliação

```bash
# Pipeline de coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 200

# Smoke rápido (10 perguntas)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 10
```

Os relatórios são escritos em `reports/eval_<timestamp>.json` na raiz do repo e foram feitos para serem diferenciados entre execuções.

## Quando avaliar

Execute o benchmark completo antes de fazer merge de qualquer mudança que toque:

- `Programma_CS2_RENAN/backend/coaching/`
- `Programma_CS2_RENAN/backend/services/coaching_service.py`
- `Programma_CS2_RENAN/backend/knowledge/` (Experience Bank, RAG)
- `Programma_CS2_RENAN/backend/services/llm_service.py`
- Baselines de jogadores pro ou stat cards usados pelo coach Hybrid

Para o protocolo completo do benchmark, a rubrica de scoring e o formato de um relatório de exemplo, consulte `cs2_coach_bench/README.md`.

## Relacionados

- Pacote de coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Camada de serviços: `Programma_CS2_RENAN/backend/services/README.md`
- Validador de qualidade (gate de regressão): `tools/headless_validator.py`
