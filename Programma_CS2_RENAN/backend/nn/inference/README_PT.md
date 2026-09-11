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
| `ghost_engine.py` | `GhostEngine` — projeta posições previstas de jogadores no mapa tático para o overlay de "ghost AI" no Tactical Viewer. Atrás do feature flag `USE_RAP_MODEL` (padrão `False`); carrega o checkpoint `rap_coach` e roda inferência forward-only por tick. |

## Resumo do `GhostEngine`

- Verifica `USE_RAP_MODEL` primeiro (padrão `False`) — quando não definido, nenhum modelo é carregado e as predições permanecem desabilitadas.
- Carrega o modelo RAP via `ModelFactory.get_model(TYPE_RAP)` + `load_nn(ModelFactory.get_checkpoint_name(TYPE_RAP), ...)` (nome do checkpoint `"rap_coach"`), então `.eval()`; inferência roda sob `torch.no_grad()`.
- `predict_tick()` aceita um único tick (dict ou dataclass) mais um `game_state` dict opcional, constrói tensores de view / map / motion via `TensorFactory` e o vetor metadata de 25 dimensões via `FeatureExtractor`, e retorna `(ghost_x, ghost_y)` coordenadas mundo (posição atual + delta x `RAP_POSITION_SCALE`).
- Os tensores vêm de um `TensorFactory` instanciado com `TrainingTensorConfig()` (resolução 64x64 para todos os canais), correspondendo à resolução de treinamento (F-0026 fechado).
- O modo de tensores player-POV é opt-in via `USE_POV_TENSORS` (padrão `False`); tensores legado são usados caso contrário.
- Retorna `None` em caso de falha — modelo desabilitado, checkpoint ausente, `map_name` ausente ou erro de inferência. (R4: o antigo sentinel `(0.0, 0.0)` era uma coordenada mundo válida perto do centro do mapa e foi removido.)

## Pontos de integração

| Consumidor | Uso |
|------------|-----|
| `apps/qt_app/screens/tactical_viewer_screen.py` | Renderiza projeções de ghost no overlay do mapa tático |
| `apps/qt_app/viewmodels/tactical_vm.py` (`TacticalGhostVM`) | Carrega o engine sob demanda (lazy) para evitar custo de startup |

## Notas de desenvolvimento

- **Sem imports do lado de treinamento.** Módulos aqui não devem importar de `training_orchestrator.py`, trainers, helpers de EMA ou montagens de DataLoader.
- **Sem mutação de arquivo.** Utilitários de inferência nunca escrevem checkpoints. Salvar é responsabilidade de `nn/persistence.py:save_nn()` invocado a partir dos caminhos de treinamento.
- **Determinismo.** Inferência é invocada a partir das threads de UI — proteja qualquer operação de tensor que não seja idempotente (por exemplo, dropout) com `model.eval()`.
- **Degradação graciosa.** Checkpoint ausente ou inferência falha → retorna `None`, log em `WARNING`. Nunca levante exceção para a thread da UI.

## Relacionados

- Checkpoints treinados: `Programma_CS2_RENAN/models/global/`
- Helpers de persistência: `backend/nn/persistence.py`
- Consumidor com carregamento lazy: `apps/qt_app/viewmodels/tactical_vm.py` (`TacticalGhostVM`)
- Tactical viewer (consumidor): `apps/qt_app/screens/tactical_viewer_screen.py`
