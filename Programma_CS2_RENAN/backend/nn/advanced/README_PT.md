> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Advanced — Stub Vazio Intencional

> **Autoridade:** `Programma_CS2_RENAN/backend/nn/advanced/`
> **Status:** Pacote vazio. Todos os módulos removidos na remediação G-06.

## O Que Aconteceu

Este pacote originalmente continha três módulos experimentais:

| Arquivo Removido | Propósito Original |
|------------------|--------------------|
| `superposition_net.py` | Wrapper experimental de SuperpositionLayer com fusão de modos brain |
| `brain_bridge.py` | Ponte de orquestração entre caminhos de coaching padrão e avançado |
| `feature_engineering.py` | Lógica duplicada de extração de features (cópia shadow do vectorizer canônico) |

Durante a fase de remediação G-06, uma auditoria de código morto revelou que **todos os três módulos tinham zero chamadores** em todo o codebase. Suas funcionalidades já haviam sido absorvidas nas localizações canônicas através de trabalhos de refatoração anteriores, tornando esses arquivos código morto inalcançável. Foram removidos para reduzir a carga de manutenção e eliminar confusão sobre qual implementação era autoritativa.

## Onde a Funcionalidade Reside Agora

As funcionalidades sobreviventes migraram para suas localizações canônicas antes da G-06:

- **SuperpositionLayer** -- `backend/nn/layers/superposition.py`. A camada linear canônica com gating contextual, regularização L1 de esparsidade, hooks de observabilidade dos gates (`get_gate_statistics()`, `get_gate_activations()`) e controles de rastreamento. Usada pela camada Strategy do RAP Coach.
- **Orquestração BrainBridge** -- Absorvida em `backend/nn/rap_coach/model.py` (`RAPCoachModel`). O próprio modelo gerencia a coordenação entre as camadas perception, memory, strategy, pedagogy e communication.
- **Feature engineering** -- `backend/processing/feature_engineering/vectorizer.py` (`FeatureExtractor`). Esta é a única fonte de verdade para o vetor de features de 25 dimensões (`METADATA_DIM = 25`). Nunca deve existir uma segunda implementação.

## Por Que o Namespace é Preservado

O diretório `advanced/` é mantido como pacote Python válido (com `__init__.py`) por três razões:

1. **Segurança de importações.** Código existente ou ferramentas de terceiros que escaneiam a árvore do pacote `nn/` não quebrarão por um subpacote ausente.
2. **Reserva de namespace.** Arquiteturas avançadas ou experimentais futuras que se graduarem além do sandbox `experimental/` poderão ser colocadas aqui.
3. **Trilha de auditoria.** O comentário no `__init__.py` documenta o que foi removido e por quê, preservando a memória institucional.

## Conteúdo do Pacote

| Arquivo | Propósito |
|---------|-----------|
| `__init__.py` | Stub do pacote com comentário histórico da remoção G-06 (5 linhas) |
| `README.md` | Versão em inglês |
| `README_IT.md` | Tradução italiana |
| `README_PT.md` | Este arquivo |

## Contexto da Remediação G-06

A remediação G-06 foi uma limpeza de código morto em todo o codebase que teve como alvo módulos com zero referências de importação. A auditoria foi realizada escaneando todos os arquivos Python em busca de padrões `from ... advanced` e `import ... advanced`. Os três arquivos neste pacote eram os únicos módulos em toda a árvore `nn/` que não tinham nenhum chamador. Sua remoção foi uma decisão deliberada para aplicar o princípio da "única fonte de verdade": cada conceito no sistema deve ter exatamente uma implementação autoritativa.

O risco-chave que a G-06 abordou foram as **implementações shadow** -- código duplicado que diverge silenciosamente da versão canônica. O arquivo `feature_engineering.py` neste pacote era um exemplo particularmente perigoso: continha uma cópia da lógica de extração de features que poderia ter sido acidentalmente importada no lugar do canônico `vectorizer.py`, produzindo vetores de features sutilmente diferentes e corrompendo o treinamento do modelo.

## Notas de Desenvolvimento

- **Não adicione módulos aqui sem justificativa.** Trabalho experimental novo deve ir primeiro para `backend/nn/experimental/` e só se graduar para `advanced/` após demonstrar estabilidade.
- **O SuperpositionLayer canônico está em `layers/superposition.py`.** Não o recrie aqui.
- **O FeatureExtractor canônico está em `processing/feature_engineering/vectorizer.py`.** Não duplique lógica de extração de features em nenhuma parte de `nn/`.
- **Se adicionar um módulo aqui**, atualize este README, o comentário no `__init__.py` e a tabela de subpacotes no `nn/README.md` principal.
