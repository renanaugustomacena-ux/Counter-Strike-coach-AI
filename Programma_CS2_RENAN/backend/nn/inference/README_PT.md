# `backend/nn/inference/` — Utilitários neurais somente de inferência

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/inference/`
> **Skill:** `/ml-check`

## Finalidade

Este pacote contém componentes de redes neurais que são usados **somente em tempo de inferência** — eles consomem checkpoints já treinados, nunca rodam loops de treinamento, e nunca possuem estado do lado de treinamento (optimizer, scheduler, EMA shadow, etc.).

A intenção é manter os caminhos de treinamento e inferência fisicamente separados na árvore de fontes para que:

- Um deployment de inferência pura (sem optimizer do PyTorch, sem DataLoader) importe uma superfície menor.
- Invariantes exclusivos do treinamento (fluxo de gradiente, clonagem de EMA, congelamento do target encoder) não vazem para os caminhos de inferência.
- Testes para comportamento de inferência possam ser escritos sem subir um trainer.

## Inventário de arquivos

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote. |
| `ghost_engine.py` | `GhostEngine` — projeta posições previstas de jogadores no mapa tático para o overlay de "ghost AI" no Tactical Viewer. Carrega o checkpoint JEPA / RAP ativo e roda inferência forward-only em batches de tick. |

## Resumo do `GhostEngine`

- Carrega o modelo via `ModelFactory.get_model(model_type).eval()` e desabilita gradientes com `torch.no_grad()`.
- Aceita uma sliding window de features de tick recentes (25-dim `METADATA_DIM`) e emite deltas de posição projetados.
- Faz cache do handle do modelo para que chamadas repetidas reutilizem os mesmos parâmetros; reset via o helper público `reset()` após troca de checkpoint.
- Cai num caminho de zero-prediction quando não há checkpoint, para que a UI permaneça utilizável numa instalação fresca.

## Pontos de integração

| Consumidor | Uso |
|------------|-----|
| `apps/qt_app/screens/tactical_viewer_screen.py` | Renderiza projeções de ghost no overlay do mapa tático |
| `apps/legacy_kivy/tactical_viewmodels.py` (`TacticalGhostViewModel`) | Carrega o engine sob demanda (lazy) para evitar custo de startup |

## Notas de desenvolvimento

- **Sem imports do lado de treinamento.** Módulos aqui não devem importar de `training_orchestrator.py`, trainers, helpers de EMA ou montagens de DataLoader.
- **Sem mutação de arquivo.** Utilitários de inferência nunca escrevem checkpoints. Salvar é responsabilidade de `nn/persistence.py:save_nn()` invocado a partir dos caminhos de treinamento.
- **Determinismo.** Inferência é invocada a partir das threads de UI — proteja qualquer operação de tensor que não seja idempotente (por exemplo, dropout) com `model.eval()`.
- **Degradação graciosa.** Checkpoint ausente → fallback de zero-prediction, log em `WARNING`. Nunca levante exceção para a thread da UI.

## Relacionados

- Checkpoints treinados: `Programma_CS2_RENAN/models/global/`
- Helpers de persistência: `backend/nn/persistence.py`
- Orquestração de inferência: `backend/services/coaching_service.py`
- Tactical viewer (consumidor): `apps/qt_app/screens/tactical_viewer_screen.py`
