> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Session Runs & Dados de Execução

Este diretório é o local de saída padrão para logs de eventos TensorBoard gerados durante o treinamento de modelos pelo coach de IA do Counter-Strike. Não contém código; apenas dados de telemetria de treinamento regeneráveis são escritos aqui em tempo de execução.

## Visão Geral Técnica

O caminho é resolvido como `RUNS_DIR = USER_DATA_ROOT/runs` em `core/config.py` (criado automaticamente no import). Quando `BRAIN_DATA_ROOT` está configurado, as runs são escritas sob essa raiz em vez do diretório no repositório. O `TensorBoardCallback` (`backend/nn/tensorboard_callback.py`) — Layer 2 do Coach Introspection Observatory — mantém `RUNS_DIR/coach_training` como valor padrão do construtor, mas o ponto de entrada do treinamento (`run_full_training_cycle.py`) delimita cada run via `build_run_dir(model_type)`, que retorna `RUNS_DIR/<model_type>/<timestamp UTC>-<tag de dispositivo>` (ex. `runs/jepa/20260817T142530Z-cpu`). O tag de dispositivo vem de `resolve_device_tag()` (`cpu` / `cuda` / `rocm`), de modo que uma smoke run Windows em CPU nunca é confundida com uma run Linux ROCm real no dashboard.

## Componentes Principais

- **Arquivos de Evento TensorBoard**: Escalares (loss, learning rate, esparsidade), histogramas e layouts de escalares personalizados registrados por época durante o treinamento.
- **Escalares MaturityObservatory**: O observatory compartilha o mesmo `SummaryWriter`, então seus sinais de conviction/maturidade são registrados no mesmo logdir.
- **Subdiretórios Por-Run**: Cada invocação de treinamento recebe seu próprio diretório `<model_type>/<timestamp UTC>-<tag de dispositivo>`, mantendo os experimentos separáveis na UI do TensorBoard em vez de acumulá-los em uma única pasta.

## Uso

1. **Treinamento**: `python run_full_training_cycle.py` registra o callback TensorBoard por padrão; `--tb-logdir` sobrescreve o destino (o padrão `None` indica um diretório com escopo da run via `build_run_dir()`; um caminho explícito desabilita o escopo da run e escreve diretamente lá) e `--no-tensorboard` desabilita o logging. O tag de dispositivo (`-cpu`, `-cuda`, `-rocm`) torna as runs de diferentes configurações de hardware imediatamente distinguíveis no dashboard.
2. **Visualização**: Iniciar `tensorboard --logdir Programma_CS2_RENAN/runs` e abrir a URL impressa para inspecionar as curvas de treinamento.
3. **Limpeza**: Arquivos de evento são artefatos voláteis e regeneráveis — diretórios de runs antigos podem ser excluídos livremente para economizar espaço em disco.
