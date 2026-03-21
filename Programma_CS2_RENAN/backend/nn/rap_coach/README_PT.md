> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# RAP Coach — Arquitetura Neural Pedagogica com Recuperacao Aumentada

**Autoridade:** `Programma_CS2_RENAN/backend/nn/rap_coach/`
**Localizacao canonica:** `backend/nn/experimental/rap_coach/` (este pacote e um shim de compatibilidade desde a migracao P9-01)
**Feature flag:** `USE_RAP_MODEL=True` (padrao: `False`)

## Introducao

RAP (Retrieval-Augmented Pedagogical) Coach e o modelo neural de coaching de alta
fidelidade do Macena CS2 Analyzer. Implementa uma arquitetura de 7 camadas que percebe
o estado do jogo atraves de streams CNN, mantem memoria temporal via neuronios
Liquid Time-Constant (LTC), toma decisoes atraves de uma camada estrategica
Mixture-of-Experts, e gera feedback de coaching legivel por humanos, calibrado para
o nivel de habilidade do jogador.

O modelo consome o vetor canonico de 25 dimensoes (`METADATA_DIM=25`) produzido pelo
`FeatureExtractor` junto com frames visuais sintetizados (cone de visao, contexto do
mapa, diferenca de movimento). Produz probabilidades de conselho, estimativas de estado
de crenca, funcoes de valor, deltas de posicionamento otimo e pontuacoes de atribuicao
causal.

## Inventario de Arquivos

| Arquivo | Classes / Exportacoes | Proposito |
|---------|----------------------|-----------|
| `__init__.py` | -- | Shim de compatibilidade (P9-01). Redireciona para `experimental/rap_coach/`. |
| `model.py` | `RAPCoachModel`, `RAP_POSITION_SCALE` | Shim que re-exporta o orquestrador completo do modelo. |
| `memory.py` | `RAPMemory` | Shim que re-exporta a camada de memoria LTC-Hopfield. |
| `trainer.py` | `RAPTrainer` | Shim que re-exporta o orquestrador de treinamento. |
| `perception.py` | `RAPPerception`, `ResNetBlock` | Shim que re-exporta a camada de percepcao CNN. |
| `strategy.py` | `RAPStrategy`, `ContextualAttention` | Shim que re-exporta a camada estrategica MoE. |
| `pedagogy.py` | `RAPPedagogy`, `CausalAttributor` | Shim que re-exporta a camada de feedback causal. |
| `communication.py` | `RAPCommunication` | Shim que re-exporta o gerador de conselhos em linguagem natural. |
| `chronovisor_scanner.py` | `ChronovisorScanner`, `CriticalMoment`, `ScanResult`, `ScaleConfig`, `ANALYSIS_SCALES` | Shim que re-exporta a deteccao multi-escala de momentos criticos. |
| `skill_model.py` | `SkillAxes`, `SkillLatentModel` | Shim que re-exporta os eixos de habilidade do jogador (estilo VAE). Localizacao canonica: `backend/processing/skill_assessment`. |

## Arquitetura: O Pipeline RAP de 7 Camadas

O modelo RAP processa o estado do jogo atraves de sete camadas distintas, cada uma com
uma responsabilidade pedagogica especifica. O diagrama ASCII abaixo mostra o fluxo de
dados completo:

```
                         RAP Coach — Arquitetura de 7 Camadas
  ========================================================================

  TENSORES DE ENTRADA
  +------------------+  +------------------+  +------------------+
  | view_frame       |  | map_frame        |  | motion_diff      |
  | [B, 3, 64, 64]  |  | [B, 3, 64, 64]  |  | [B, 3, 64, 64]  |
  +--------+---------+  +--------+---------+  +--------+---------+
           |                     |                     |
  =========|=====================|=====================|===============
  CAMADA 1: PERCEPCAO (RAPPerception)
           |                     |                     |
     +-----v------+       +-----v------+       +------v-----+
     | ResNet      |       | ResNet     |       | MotionConv |
     | [1,2,2,1]   |       | [2,2]     |       | 3->16->32  |
     | -> 64-dim   |       | -> 32-dim |       | -> 32-dim  |
     +-----+------+       +-----+------+       +------+-----+
           |                     |                     |
           +----------+----------+----------+----------+
                      |
                z_spatial [B, 128]
                      |
  ====================|================================================
  CAMADA 2: MEMORIA (RAPMemory)
                      |
            +---------v-----------+        +---------+  metadata
            | Concatenacao        |<-------+ [B,T,25]|  (vetor 25-dim)
            | [B, T, 128+25=153] |        +---------+
            +---------+-----------+
                      |
            +---------v-----------+
            |  LTC (Liquid Time-  |   Fiacao AutoNCP
            |  Constant) neuronios|   ncp_units=512
            |  hidden_dim=256     |   seed=42
            +---------+-----------+
                      |
            +---------v-----------+
            | Memoria Associativa |   4 cabecas de atencao
            | Hopfield (512 slots)|   NN-MEM-01: bypassada
            | + Adicao Residual   |   ate >=2 passagens fwd
            +---------+-----------+
                      |
               combined_state [B, T, 256]
                      |
            +---------v-----------+
            | Belief Head         |   256 -> 256 -> 64
            | (ativacao SiLU)     |   belief_dim=64
            +---------+-----------+
                      |
               belief [B, T, 64]
                      |
  ====================|================================================
  CAMADA 3: ESTRATEGIA (RAPStrategy)
                      |
            +---------v-----------+
            | Mixture of Experts  |   4 especialistas
            | + Superposition     |   context = metadata[:,-1,:]
            | + Context Gate      |   regularizacao L1
            +---------+-----------+
                      |
               advice_probs [B, OUTPUT_DIM=10]
               gate_weights [B, 4]
                      |
  ====================|================================================
  CAMADA 4: PEDAGOGIA (RAPPedagogy + CausalAttributor)
                      |
            +---------v-----------+
            | Critic Head V(s)    |   256 -> 64 -> 1
            | + Skill Adapter     |   skill_vec [B, 10]
            +---------+-----------+
                      |
               value_estimate [B, 1]
                      |
            +---------v-----------+
            | CausalAttributor    |   5 conceitos:
            | Fusao Neural +      |   Positioning, Crosshair,
            | Heuristica          |   Aggression, Utility,
            +---------+-----------+   Rotation
                      |
               attribution [B, 5]
                      |
  ====================|================================================
  CAMADA 5: COMUNICACAO (RAPCommunication)
                      |
            +---------v-----------+
            | Motor de Templates  |   Niveis: low (1-3),
            | Condicionado por    |   mid (4-7), high (8-10)
            | Habilidade +        |   Limiar de confianca: 0.7
            | Resolvedor de Angulo|
            +---------+-----------+
                      |
               conselho de coaching em linguagem natural
                      |
  ====================|================================================
  CAMADA 6: ANALISE TEMPORAL (ChronovisorScanner)
                      |
            +---------v-----------+
            | Processamento de    |   micro:  64 ticks (~1s)
            | Sinal Multi-Escala  |   standard: 192 ticks (~3s)
            | + Dedup Cross-Scale |   macro: 640 ticks (~10s)
            +---------+-----------+
                      |
               CriticalMoment[]
                      |
  ====================|================================================
  CAMADA 7: POSITION HEAD (em RAPCoachModel)
                      |
            +---------v-----------+
            | Linear(256, 3)      |   Prediz o delta de
            | dx, dy, dz delta    |   posicao otima
            +---------+-----------+   RAP_POSITION_SCALE=500.0
                      |
               optimal_pos [B, 3]

  ========================================================================
```

## Constantes-Chave

| Constante | Valor | Fonte |
|-----------|-------|-------|
| `hidden_dim` | 256 | `model.py:45` |
| `perception_dim` | 128 | `model.py:42` (64 + 32 + 32) |
| `ncp_units` | 512 | `memory.py:50` (hidden_dim x 2) |
| `belief_dim` | 64 | `memory.py:92` |
| `OUTPUT_DIM` | 10 | `nn/config.py:123` |
| `METADATA_DIM` | 25 | `vectorizer.py:32` |
| `RAP_POSITION_SCALE` | 500.0 | `nn/config.py:155` |
| `num_experts` | 4 | `strategy.py:42` |
| `hopfield_heads` | 4 | `memory.py:83` |
| `Z_AXIS_PENALTY_WEIGHT` | 2.0 | `trainer.py:26` |

## Invariantes Criticas

| ID | Regra | Consequencia se Violada |
|----|-------|-------------------------|
| **NN-MEM-01** | A memoria Hopfield e bypassada ate que >=2 passagens forward de treinamento tenham ocorrido. A ativacao tambem ocorre no carregamento de checkpoint. | Prototipos aleatorios injetam ruido em vez de sinal no combined_state, corrompendo o treinamento inicial. |
| **NN-RM-01** | `skill_vec` deve ter forma `[B, 10]`. Formas incompativeis sao registradas e ignoradas. | Dados lixo silenciosos no adaptador pedagogico distorcem as estimativas de valor. |
| **NN-RM-03** | `gate_weights` deve ser passado explicitamente para `compute_sparsity_loss()` (thread-safety, F3-07). | Condicao de corrida no estado em cache durante inferencia multi-thread. |
| **P-X-02** | As assercoes de forma do input impoe `metadata.shape[-1] == METADATA_DIM`. | Erros cripticos de dimensao LSTM/CNN nas profundezas do passagem forward. |
| **NN-CV-03** | Verificacao de limites do indice peak_tick antes de acessar o array ticks no ChronovisorScanner. | Crash IndexError durante a deteccao de momentos criticos. |

## Integracao

O RAP Coach se integra com o Macena CS2 Analyzer mais amplo atraves de varios pontos de contato:

- **CoachTrainingManager** (`backend/nn/coach_manager.py`) -- controla o gate de maturidade para o ChronovisorScanner
- **FeatureExtractor** (`backend/processing/feature_engineering/vectorizer.py`) -- produz o vetor metadata de 25 dimensoes
- **RAPStateReconstructor** (`backend/processing/state_reconstructor.py`) -- converte dados brutos de tick em lotes de tensores prontos para o modelo
- **SuperpositionLayer** (`backend/nn/layers/superposition.py`) -- camada linear modulada por contexto usada pelos especialistas do RAPStrategy
- **Persistence** (`backend/nn/persistence.py`) -- `load_nn("rap_coach", model)` / `save_nn()` para gerenciamento de checkpoints
- **Structured Logging** -- todos os modulos usam `get_logger("cs2analyzer.nn.experimental.rap_coach.<modulo>")`

## Dependencias

| Pacote | Proposito | Opcional? |
|--------|-----------|-----------|
| `torch` | Operacoes tensoriais centrais, nn.Module | Obrigatorio |
| `ncps` | Neuronios LTC, fiacao AutoNCP | Opcional (protegido por `_RAP_DEPS_AVAILABLE`) |
| `hflayers` | Memoria associativa Hopfield | Opcional (protegido por `_RAP_DEPS_AVAILABLE`) |
| `numpy` | Processamento de sinal no ChronovisorScanner | Obrigatorio |
| `sqlmodel` | Consultas ao banco de dados no ChronovisorScanner | Obrigatorio (no momento da varredura) |

Quando `ncps` / `hflayers` nao estao instalados, `RAPMemoryLite` (fallback baseado em LSTM)
esta disponivel via `use_lite_memory=True` em `RAPCoachModel.__init__()`.

## Notas de Desenvolvimento

- Este pacote (`backend/nn/rap_coach/`) contem apenas **shims de compatibilidade**.
  Toda a implementacao canonica reside em `backend/nn/experimental/rap_coach/`.
- O feature flag `USE_RAP_MODEL` e `False` por padrao. O modelo primario em producao e o JEPA.
- Alterar `ncp_units` ou `hidden_dim` invalida checkpoints existentes. O carregamento com
  controle de versao em `load_nn()` detecta incompatibilidades arquiteturais via `StaleCheckpointError`.
- O estado RNG para a fiacao AutoNCP e explicitamente salvo e restaurado (`seed=42`) para
  garantir uma topologia de rede deterministica e portavel entre checkpoints (NN-45 + NN-MEM-02).
- O trainer usa uma loss de 4 componentes ponderadas: strategy (1.0), value (0.5), sparsity (1.0),
  position (1.0). Erros de posicao no eixo Z sao penalizados com peso 2x (NN-TR-02b).
- A camada de comunicacao suprime conselhos quando a confianca do modelo esta abaixo do limiar de 0.7.
