# `evals/` — Harness de Avaliação e Benchmarking

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Garantia de qualidade do coaching
> **Status:** Ativo — toda mudança na pipeline de coaching deve executar o bench antes do merge.

## Propósito

Este diretório hospeda o framework automatizado para medir e validar o desempenho do coach de IA do Counter-Strike. Ele fornece uma maneira sistemática de testar a pipeline de coaching e seus Modelos de Linguagem de Grande Escala (LLM) subjacentes contra cenários táticos selecionados por especialistas, produzindo relatórios quantificáveis sobre regressões, alucinações e drift de cobertura.

## Visão Geral Técnica

O sistema de avaliação opera como um harness de benchmarking de ciclo fechado. Ele simula solicitações de coaching usando um conjunto padronizado de perguntas e compara as respostas da IA com uma rubrica estritamente definida. Esse processo permite o acompanhamento quantificável de melhorias no modelo, detecção de regressão e validação de precisão em diferentes cenários de mapas e complexidades estratégicas.

## Componentes Principais

### CS2 Coach Bench
Localizado em **`cs2_coach_bench/`**, este é o conjunto de dados primário para avaliação:
- **`questions.jsonl`**: Uma coleção de 200 perguntas táticas (40 por categoria em 5 categorias) cobrindo táticas de mapa, economia, jogo mid-round, conhecimento sobre pros e mecânicas.
- **`rubric.md`**: Os critérios de pontuação "padrão-ouro" — 5 dimensões com pontuação 0-3 cada (máximo 15 por pergunta) — usados para avaliar a qualidade, precisão e relevância profissional dos conselhos do coach.
- **`run_eval.py`**: O motor de execução que envia as perguntas para um backend de modelo (`coach` para a pipeline completa ou `ollama:<model>`) e coleta as respostas brutas mais a latência.
- **`score_responses.py`**: A CLI de scoring (subcomandos `score` / `summary` / `compare`) que aplica a rubrica às respostas coletadas e compara os modelos.
- **`reports/`**: Arquivos de resposta JSONL por execução (gitignored, criados na primeira execução).

## Estrutura do Diretório

```text
evals/
├── cs2_coach_bench/        # Suíte de benchmarking primária
│   ├── questions.jsonl     # Perguntas de avaliação padronizadas
│   ├── rubric.md           # Critérios de pontuação definidos por especialistas
│   ├── run_eval.py         # Script de execução
│   ├── score_responses.py  # CLI de scoring e comparação
│   └── reports/            # Arquivos de resposta por execução (gitignored, gerados)
├── README.md               # Versão em inglês
├── README_IT.md            # Versão em italiano
└── README_PT.md            # Esta documentação
```

## Uso

### 1. Executar a Avaliação
Execute o benchmark contra a implementação atual do coach (pipeline completa ou um modelo Ollama bruto):
```bash
# Pipeline de coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach

# Smoke rápido (10 perguntas) contra um modelo Ollama baseline bruto
python evals/cs2_coach_bench/run_eval.py --model ollama:gemma4:e2b --limit 10
```
As respostas são salvas em `cs2_coach_bench/reports/<date>_<model>.jsonl` por padrão (`--output` sobrescreve; `--category` filtra por uma única categoria).

### 2. Pontuar os Resultados
Pontue as respostas coletadas com a rubrica, depois obtenha o sumário:
```bash
python evals/cs2_coach_bench/score_responses.py score --input evals/cs2_coach_bench/reports/<date>_coach.jsonl
python evals/cs2_coach_bench/score_responses.py summary --input evals/cs2_coach_bench/reports/<date>_coach.scored.jsonl
```

### 3. Analisar Métricas
O sumário fornece um detalhamento por categoria e por dimensão das pontuações da rubrica (5 dimensões, 0-3 cada), e `score_responses.py compare a.scored.jsonl b.scored.jsonl` compara dois modelos. Essas métricas controlam as mudanças na pipeline de coaching e guiam os esforços de ajuste fino do modelo (o bench em si roda localmente; treinamento e ajuste fino em escala completa rodam na máquina Linux de treinamento dedicada, não nesta estação de trabalho).

## Quando avaliar

Execute o benchmark completo antes de fazer merge de qualquer mudança que toque:
- `Programma_CS2_RENAN/backend/coaching/`
- `Programma_CS2_RENAN/backend/services/coaching_service.py`
- `Programma_CS2_RENAN/backend/knowledge/` (Experience Bank, RAG)
- `Programma_CS2_RENAN/backend/services/llm_service.py`
- Baselines de jogadores pro ou stat cards usados pelo coach Hybrid

## Relacionados

- Pacote de coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Camada de serviços: `Programma_CS2_RENAN/backend/services/README.md`
- Validador de qualidade (gate de regressão): `tools/headless_validator.py`
- Harness de métricas offline pré-retrain (feature drift, RAG recall@k, kNN purity): `tools/eval_harness.py`
- Eval de respostas do coach através do motor de diálogo real com o DB: `tools/coach_answer_eval.py`
