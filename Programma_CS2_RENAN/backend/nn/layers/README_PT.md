# `backend/nn/layers/` — Blocos neurais reutilizáveis

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/layers/`
> **Skill:** `/ml-check`

## Finalidade

Este pacote possui as definições canônicas dos building blocks `nn.Module` compartilhados. Foi criado durante a remediação G-06 para consolidar implementações duplicadas em uma única localização autoritativa. Atualmente seu único ocupante, `SuperpositionLayer`, é consumido pela camada Strategy do RAP Coach.

## Inventário de arquivos

| Arquivo | Finalidade | Exports principais |
|---------|------------|--------------------|
| `__init__.py` | Marcador de pacote. | — |
| `superposition.py` | `SuperpositionLayer` — camada linear com condicionamento FiLM (`y = γ(context)·(Wx+b) + β(context)`, RAP-AUDIT-06) com hook de loss para esparsidade L1 do gate (`gate_sparsity_loss()`), hooks de observabilidade do gate (`get_gate_statistics()`, `get_gate_activations()`) e controles de tracing. | `SuperpositionLayer` |

## `SuperpositionLayer` em um parágrafo

Uma projeção linear padrão modulada por Feature-wise Linear Modulation (FiLM): um gate sigmoide `γ(context)` escala a projeção e um shift aditivo inicializado em zero `β(context)` injeta features orientadas pelo contexto (RAP-AUDIT-06 — o gate anterior, apenas multiplicativo, podia suprimir features mas nunca adicioná-las). Cada especialista na camada Strategy do RAP Coach usa um como sua primeira camada adaptável ao contexto. Fornece um hook de loss para esparsidade L1 do gate (`gate_sparsity_loss()`) e hooks de observabilidade para que o trainer possa logar a esparsidade do gate por passo.

## Por que este diretório existe

Antes da limpeza G-06, o projeto teve brevemente duas implementações paralelas do mecanismo de superposição (uma em `backend/nn/advanced/superposition_net.py`, outra inline no modelo RAP). Ambas divergiram. A G-06 consolidou a implementação canônica aqui. Deve permanecer exatamente uma definição de `SuperpositionLayer` em todo o codebase — veja o aviso em `backend/nn/advanced/README.md`.

## Adicionando uma nova camada

Um bloco pertence aqui quando ele é:

1. **A única definição canônica** de um building block que não deve ser duplicado em outro lugar (princípio G-06).
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
