> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Neural Network Subsystem — Arquiteturas de Modelos & Infraestrutura de Treinamento

> **Autoridade:** `Programma_CS2_RENAN/backend/nn/`
> **Depende de:** `backend/processing/feature_engineering/` (vetor de features de 25 dimensões), `backend/storage/` (SQLite WAL), `core/config.py` (configurações)
> **Consumido por:** `backend/services/` (serviço de coaching), `backend/coaching/` (motor híbrido), `apps/qt_app/` (UI)

## Introdução

Este pacote é o núcleo de machine learning do sistema de coaching CS2. Contém seis arquiteturas de redes neurais distintas, um orquestrador de treinamento unificado com instrumentação baseada em callbacks de plugin, e um motor de inferência em tempo real (GhostEngine). Todo modelo consome o vetor canônico de features de 25 dimensões produzido por `FeatureExtractor` em `backend/processing/feature_engineering/vectorizer.py`. Toda aleatoriedade é semeada via `GLOBAL_SEED = 42` para execuções de treinamento determinísticas e reproduzíveis.

O pipeline de treinamento foi validado de ponta a ponta em 12 de março de 2026: 11 demos profissionais ingeridas (17.3M linhas de tick, banco de dados de 6.4 GB), dry-run do JEPA completado produzindo `jepa_brain.pt` (3.6 MB).

## Inventário de Arquivos

| Arquivo | Propósito |
|---------|-----------|
| `config.py` | Constantes centrais (`INPUT_DIM=25`, `OUTPUT_DIM=10`, `HIDDEN_DIM=128`, `GLOBAL_SEED=42`, `RAP_POSITION_SCALE=500.0`), `set_global_seed()`, `get_device()` com seleção de GPU discreta |
| `model.py` | `AdvancedCoachNN` (LSTM + Mixture of Experts), dataclass `CoachNNConfig`, `ModelManager` para salvamento de checkpoint versionado |
| `jepa_model.py` | `JEPAEncoder`, `JEPACoachingModel`, `VLJEPACoachingModel` -- JEPA auto-supervisionado com loss contrastivo InfoNCE e dicionário de conceitos |
| `jepa_train.py` | Script de treinamento JEPA em duas fases (pré-treinamento + fine-tuning), `_MIN_ROUNDS_FOR_SEQUENCE = 6` |
| `jepa_trainer.py` | Loop de treinamento JEPA de baixo nível com atualização EMA do encoder alvo |
| `ema.py` | Classe `EMA` -- média móvel exponencial para gerenciamento de pesos shadow (invariante NN-16: `.clone()` em `apply_shadow()`) |
| `role_head.py` | `NeuralRoleHead` (entrada 5-dim, saída softmax 5-dim, ~750 parâmetros), helpers de treinamento e inferência para classificação de papel do jogador |
| `win_probability_trainer.py` | `WinProbabilityTrainerNN` -- modelo leve de 9 features para probabilidade de vitória offline em DataFrames de partidas pro |
| `dataset.py` | `ProPerformanceDataset` (supervisionado) e `SelfSupervisedDataset` (pares contexto/alvo JEPA com janela deslizante) |
| `factory.py` | `ModelFactory` -- fábrica estática para instanciação unificada de todos os tipos de modelo (`default`, `jepa`, `vl-jepa`, `rap`, `rap-lite`, `role_head`) |
| `persistence.py` | `save_nn()`, `load_nn()`, `get_model_path()` com escrita atômica (`tmp + os.replace`), `StaleCheckpointError` |
| `early_stopping.py` | `EarlyStopping` com limiares configuráveis de paciência e delta mínimo |
| `training_config.py` | Dataclasses `TrainingConfig` e `JEPATrainingConfig` centralizando todos os hiperparâmetros |
| `training_orchestrator.py` | `TrainingOrchestrator` -- loop unificado por época com validação, early stopping, checkpointing, agendamento de LR e despacho de callbacks |
| `training_controller.py` | `TrainingController` -- deduplicação de demos, verificações de diversidade, gerenciamento de cota mensal, lógica start-stop |
| `coach_manager.py` | `CoachTrainingManager` -- orquestração de alto nível com portão de maturidade de 3 estágios (doubt / learning / conviction) |
| `train.py` | `train_nn()` -- ponto de entrada legado para treinamento do `AdvancedCoachNN` |
| `train_pipeline.py` | Pipeline de treinamento end-to-end legado (depreciado, mantido para compatibilidade) |
| `training_callbacks.py` | `TrainingCallback` (ABC, hooks opt-in) e `CallbackRegistry` (despachante de eventos com isolamento de erros) |
| `tensorboard_callback.py` | `TensorBoardCallback` -- registra 9+ sinais escalares, histogramas de parâmetros/gradientes, layouts escalares personalizados |
| `maturity_observatory.py` | `MaturityObservatory` -- índice de convicção de 5 sinais (belief entropy, gate specialization, concept focus, value accuracy, role stability), máquina de 5 estados (doubt / crisis / learning / conviction / mature) |
| `embedding_projector.py` | `EmbeddingProjector` -- projeções UMAP 2D e exportação de embeddings TensorBoard para visualização do espaço belief/concept |
| `training_monitor.py` | `TrainingMonitor` -- métricas por época persistidas em JSON com escrita atômica para monitoramento de progresso em tempo real |
| `evaluate.py` | `evaluate_adjustments()` -- avaliação compatível com SHAP dos ajustes de peso do modelo por feature |
| `data_quality.py` | `DataQualityReport` -- verificações de qualidade de dados pré-treinamento (taxa de NaN, taxa de posição zero, balanceamento de classes) |

## Subpacotes

| Pacote | Propósito |
|--------|-----------|
| `rap_coach/` | Modelo RAP Coach: arquitetura pedagógica de 7 camadas (Perception, Memory, Strategy, Pedagogy, Communication, ChronovisorScanner, SkillModel). Requer `ncps` + `hflayers` para memória LTC-Hopfield. |
| `advanced/` | **Stub vazio intencional.** Módulos originais removidos na remediação G-06. Namespace reservado para experimentos futuros. Consulte `advanced/README.md`. |
| `inference/` | `GhostEngine` -- motor de previsão em tempo real que traduz estado de jogo em nível de tick em sugestões de coaching via `RAP_POSITION_SCALE`. |
| `layers/` | `SuperpositionLayer` -- camada linear com gating contextual que habilita fusão dinâmica de modos com regularização L1 de esparsidade e hooks de observabilidade. |
| `experimental/` | Variante experimental do RAP Coach com módulos separados de Perception, Strategy, Pedagogy, Communication, Memory e harness de teste. |

## Arquiteturas de Modelos

### 1. JEPA (`jepa_model.py`) -- Caminho de Treinamento Primário

Arquitetura Joint-Embedding Predictive auto-supervisionada. Protocolo de duas fases: (1) pré-treinamento em demos profissionais com loss contrastivo InfoNCE + dicionário de conceitos para alinhamento semântico, (2) fine-tuning LSTM em dados do usuário. Usa encoder alvo EMA (`requires_grad=False` durante atualização, invariante NN-JM-04). Dim latente: 256, dim oculta LSTM: 128.

### 2. RAP Coach (`rap_coach/`) -- Arquitetura da Grande Visão

Modelo pedagógico de 7 camadas: Perception baseada em ResNet, Memory LTC-Hopfield (512 slots associativos, `ncp_units=512`, `belief_dim=64`), Strategy com SuperpositionLayer e gating contextual, Pedagogy causal para atribuição de erros, Communication em linguagem natural, ChronovisorScanner para análise temporal multi-escala, e SkillModel para estimativa de habilidade do jogador. Hopfield é contornado até 2+ forward passes de treinamento (invariante NN-MEM-01).

### 3. AdvancedCoachNN (`model.py`) -- Modelo Supervisionado Legado

Encoder de sequência LSTM + Mixture of Experts (3 especialistas por padrão) com LayerNorm, gating com viés de papel e clamping de saída com `tanh`. Alias como `TeacherRefinementNN` para compatibilidade.

### 4. NeuralRoleHead (`role_head.py`) -- Classificação de Papéis

MLP leve (5 -> 32 -> 16 -> 5, ~750 parâmetros) que prevê probabilidades de papel do jogador a partir de métricas de estilo de jogo (TAPD, OAP, PODT, rating impact, aggression). Loss KL-divergence com label smoothing. Funciona como opinião secundária junto ao classificador heurístico `RoleClassifier`.

### 5. WinProbabilityTrainerNN (`win_probability_trainer.py`) -- Predição de Vitória Offline

Modelo de 9 features (vivos, saúde, armadura, equipamento, estado da bomba) para treinamento offline em DataFrames de partidas pro. Separado do preditor em tempo real `WinProbabilityNN` em `backend/analysis/` (12 features, dims ocultas 64/32). Os checkpoints NÃO são intercambiáveis.

### 6. VL-JEPA (`jepa_model.py`) -- Extensão Vision-Language

Estende o JEPA com compreensão tática visual-linguística para explicações de coaching em nível de conceito.

## Constantes-Chave

| Constante | Valor | Definida em |
|-----------|-------|-------------|
| `INPUT_DIM` / `METADATA_DIM` | 25 | `config.py`, `vectorizer.py` |
| `OUTPUT_DIM` | 10 | `config.py` |
| `HIDDEN_DIM` | 128 | `config.py` |
| `GLOBAL_SEED` | 42 | `config.py` |
| `BATCH_SIZE` | 32 | `config.py` |
| `LEARNING_RATE` | 0.001 | `config.py` |
| `RAP_POSITION_SCALE` | 500.0 | `config.py` |
| `WEIGHT_CLAMP` | 0.5 | `config.py` |
| RAP `hidden_dim` | 256 | `rap_coach/model.py` |
| RAP `ncp_units` | 512 | `rap_coach/memory.py` |
| RAP `belief_dim` | 64 | `rap_coach/memory.py` |
| JEPA `latent_dim` | 256 | `jepa_model.py` |
| JEPA LSTM `hidden_dim` | 128 | `jepa_model.py` |

## Coach Introspection Observatory

O pipeline de treinamento inclui uma pilha de observabilidade de 4 camadas, implementada como plugins `TrainingCallback`:

1. **Camada 1 -- CallbackRegistry** (`training_callbacks.py`): Arquitetura de plugins com isolamento de erros. Callbacks nunca causam crash no treinamento.
2. **Camada 2 -- TensorBoardCallback** (`tensorboard_callback.py`): Escalares (loss, LR, esparsidade, dinâmicas de gate), histogramas (parâmetros, gradientes, beliefs, conceitos), layouts de dashboard personalizados.
3. **Camada 3 -- MaturityObservatory** (`maturity_observatory.py`): Índice de convicção de 5 sinais com suavização EMA e máquina de classificação de 5 estados (doubt / crisis / learning / conviction / mature).
4. **Camada 4 -- EmbeddingProjector** (`embedding_projector.py`): Projeções UMAP 2D de vetores belief e embeddings de conceitos, exportados para TensorBoard.

## Invariantes Críticos

| ID | Regra |
|----|-------|
| P-RSB-03 | `round_won` EXCLUÍDO das features de treinamento (vazamento de rótulo) |
| NN-MEM-01 | Hopfield contornado até 2+ forward passes de treinamento |
| NN-16 | EMA `apply_shadow()` deve usar `.clone()` nos tensores shadow |
| NN-JM-04 | Encoder alvo `requires_grad=False` durante atualização EMA |
| P-X-01 | Asserção em tempo de compilação `len(FEATURE_NAMES) == METADATA_DIM` |
| P-VEC-02 | NaN/Inf nas features dispara log ERROR + clamp |
| P3-A | >5% NaN/Inf no batch levanta `DataQualityError` |

## Notas de Desenvolvimento

- **Reprodutibilidade:** Sempre chamar `set_global_seed(42)` antes das execuções de treinamento.
- **Seleção de dispositivo:** `get_device()` seleciona automaticamente a GPU discreta por VRAM; substituível via configuração `CUDA_DEVICE`.
- **Alinhamento de features:** Qualquer alteração no vetor de 25 dimensões deve atualizar simultaneamente `FEATURE_NAMES`, `METADATA_DIM`, docstring de `extract()` e todas as asserções `input_dim` dos modelos.
- **Dependências opcionais:** RAP Coach requer `ncps` e `hflayers`. Importações são protegidas com `try/except`; verificar `_RAP_DEPS_AVAILABLE` antes da instanciação.
- **Escritas atômicas:** Todos os salvamentos de checkpoint e persistência JSON usam `tmp + os.replace()` para prevenir corrupção em caso de crash.
- **A decimação de ticks é RIGOROSAMENTE PROIBIDA** -- todos os dados em nível de tick devem ser preservados como ingeridos.

## Uso

```python
from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
from Programma_CS2_RENAN.backend.nn.config import set_global_seed

set_global_seed(42)
model = ModelFactory.get_model("jepa")

from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
orchestrator = TrainingOrchestrator(manager, model_type="jepa", max_epochs=50)
```
