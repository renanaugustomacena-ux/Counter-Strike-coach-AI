# `evals/` — Harness de Avaliação e Benchmarking

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Garantia de qualidade do coaching
> **Status:** Ativo — toda mudança na pipeline de coaching deve executar o bench antes do merge.

## Propósito

Este diretório hospeda o framework automatizado para medir e validar o desempenho do coach de IA do Counter-Strike. Ele fornece uma maneira sistemática de testar os Modelos de Linguagem de Grande Escala (LLM) e Modelos de Visão-Linguagem (VLM) contra cenários táticos selecionados por especialistas, produzindo relatórios quantificáveis sobre regressões, alucinações e drift de cobertura.

## Visão Geral Técnica

O sistema de avaliação opera como um harness de benchmarking de ciclo fechado. Ele simula solicitações de coaching usando um conjunto padronizado de perguntas e compara as respostas da IA com uma rubrica estritamente definida. Esse processo permite o acompanhamento quantificável de melhorias no modelo, detecção de regressão e validação de precisão em diferentes cenários de mapas e complexidades estratégicas.

## Componentes Principais

### CS2 Coach Bench
Localizado em **`cs2_coach_bench/`**, este é o conjunto de dados primário para avaliação:
- **`questions.jsonl`**: Uma coleção de mais de 200 perguntas táticas diversas cobrindo uso de utilitários, posicionamento e análise de estado de rodada.
- **`rubric.md`**: Os critérios de pontuação "padrão-ouro" usados para avaliar a qualidade, precisão e relevância profissional dos conselhos do coach.
- **`run_eval.py`**: O motor de execução que envia as perguntas para a API do coach e coleta as respostas brutas do modelo.
- **`score_responses.py`**: O script de validação que compara as saídas do modelo com a rubrica e gera métricas finais de desempenho (ex: Precisão, F1-score, Solidez Tática).
- **`reports/`**: Relatórios JSON gerados por execução para rastreamento histórico.

## Estrutura do Diretório

```text
evals/
├── cs2_coach_bench/        # Suíte de benchmarking primária
│   ├── questions.jsonl     # Perguntas de avaliação padronizadas
│   ├── rubric.md           # Critérios de pontuação definidos por especialistas
│   ├── run_eval.py         # Script de execução
│   ├── score_responses.py  # Script de pontuação e validação
│   └── reports/            # Relatórios por partida
├── README.md               # Versão em inglês
├── README_IT.md            # Versão em italiano
└── README_PT.md            # Esta documentação
```

## Uso

### 1. Executar a Avaliação
Execute o benchmark contra a implementação atual do coach (ex: pipeline completa ou modelo específico):
```bash
# Pipeline de coaching completa (RAG + Experience Bank + LLM)
python evals/cs2_coach_bench/run_eval.py --model coach --limit 200

# Smoke rápido (10 perguntas) contra um modelo específico
python evals/cs2_coach_bench/run_eval.py --model gpt-4o --limit 10 --output results.json
```

### 2. Pontuar os Resultados
Gere um relatório de desempenho pontuando as respostas coletadas:
```bash
python evals/cs2_coach_bench/score_responses.py --input results.json --rubric evals/cs2_coach_bench/rubric.md
```

### 3. Analisar Métricas
O sistema emitirá um detalhamento das métricas por categoria (ex: "Conhecimento de Smoke: 85%", "Conselhos Econômicos: 92%"). Essas métricas são usadas para autorizar implantações em produção e guiar os esforços de ajuste fino do modelo.

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
