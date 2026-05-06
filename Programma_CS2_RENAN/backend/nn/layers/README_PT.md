# `backend/nn/layers/` — Blocos neurais reutilizáveis

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/layers/`
> **Skill:** `/ml-check`

## Finalidade

Este pacote possui os pequenos blocos `nn.Module` reutilizáveis dos quais mais de um modelo no projeto depende. Qualquer coisa única a uma só arquitetura de modelo permanece dentro do pacote daquele modelo — apenas blocos com múltiplos consumidores são promovidos para cá.

## Inventário de arquivos

| Arquivo | Finalidade | Exports principais |
|---------|------------|--------------------|
| `__init__.py` | Marcador de pacote. | — |
| `superposition.py` | `SuperpositionLayer` — camada linear context-gated com regularização de esparsidade L1, hooks de observabilidade do gate (`get_gate_statistics()`, `get_gate_activations()`) e controles de tracing. | `SuperpositionLayer` |

## `SuperpositionLayer` em um parágrafo

Uma projeção linear padrão envolvida num gate aprendível e condicionado por contexto. A saída do gate é regularizada por L1 para que a camada aprenda a manter a maior parte da sua capacidade inativa para um dado input, "acendendo" apenas o subespaço relevante para o estado atual. Usada pela camada Strategy do RAP Coach para combinar múltiplas sub-políticas especialistas sob uma única parametrização compartilhada. Fornece hooks de observabilidade para que o trainer possa logar a esparsidade do gate por passo.

## Por que este diretório existe

Antes da limpeza G-06, o projeto teve brevemente duas implementações paralelas do mecanismo de superposição (uma em `backend/nn/advanced/superposition_net.py`, outra inline no modelo RAP). Ambas divergiram. A G-06 consolidou a implementação canônica aqui. Deve permanecer exatamente uma definição de `SuperpositionLayer` em todo o codebase — veja o aviso em `backend/nn/advanced/README.md`.

## Adicionando uma nova camada

Um bloco pertence aqui apenas quando ele é:

1. **Reutilizado por ≥ 2 modelos.** Um bloco usado por um único modelo vive no pacote daquele modelo.
2. **Stateless quanto ao modo de treinamento/inferência** além do switch padrão `model.eval()` — sem registries globais, sem estado mutável a nível de módulo.
3. **Documentado neste README.** Atualize a tabela de inventário de arquivos e adicione um resumo de um parágrafo.

## Não faça

- **Não** duplique o `SuperpositionLayer`. Existe uma única implementação canônica.
- **Não** adicione estado do lado de treinamento (optimizer, scheduler, EMA) a um módulo neste pacote.
- **Não** coloque lógica de feature engineering aqui. Extração de features é de responsabilidade de `backend/processing/feature_engineering/`.

## Relacionados

- Consumidor da camada Strategy do RAP Coach: `backend/nn/experimental/rap_coach/strategy.py`
- Histórico de stub vazio: `backend/nn/advanced/README.md` (notas de limpeza G-06)
- Dimensão de feature: `METADATA_DIM = 25` de `backend/processing/feature_engineering/vectorizer.py`
