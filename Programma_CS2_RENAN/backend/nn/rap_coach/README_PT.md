> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# RAP Coach — Arquitetura Neural Reasoning, Adaptation, Pedagogy

**Autoridade:** `Programma_CS2_RENAN/backend/nn/rap_coach/`
**Localizacao canonica:** `backend/nn/experimental/rap_coach/` (este pacote e um shim de compatibilidade desde a migracao P9-01)
**Feature flag:** `USE_RAP_MODEL=True` (padrao: `False`)

## Introducao

RAP (Reasoning, Adaptation, Pedagogy) Coach e o modelo neural de coaching de alta
fidelidade do Macena CS2 Analyzer. Acopla seis componentes aprendiveis dentro de
`RAPCoachModel` -- percepcao CNN, memoria temporal Liquid Time-Constant (LTC) + Hopfield,
uma camada estrategica sparse Mixture-of-Experts com roteamento top-2, uma value head
pedagogica, atribuicao causal e uma position head -- com uma camada de comunicacao
externa baseada em templates que gera feedback de coaching legivel por humanos, calibrado
para o nivel de habilidade do jogador.

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
| `strategy.py` | `RAPStrategy` | Shim que re-exporta a camada estrategica MoE. |
| `pedagogy.py` | `RAPPedagogy`, `CausalAttributor` | Shim que re-exporta a camada de feedback causal. |
| `communication.py` | `RAPCommunication` | Shim que re-exporta o gerador de conselhos em linguagem natural. |
| `chronovisor_scanner.py` | `ChronovisorScanner`, `CriticalMoment`, `ScanResult`, `ScaleConfig`, `ANALYSIS_SCALES` | Shim que re-exporta a deteccao multi-escala de momentos criticos. |
| `skill_model.py` | `SkillAxes`, `SkillLatentModel` | Shim que re-exporta os eixos de habilidade do jogador (decomposicao estatistica de 5 eixos projetada num nivel curricular de 1-10). Localizacao canonica: `backend/processing/skill_assessment.py`. |

## Arquitetura: O Pipeline RAP de 7 Camadas

O diagrama abaixo organiza a pilha RAP em sete estagios de processamento, cada um com
uma responsabilidade pedagogica especifica. Os estagios 1-4 e 7 sao componentes aprendiveis
dentro de `RAPCoachModel`; o estagio 5 (`RAPCommunication`) e o estagio 6 (`ChronovisorScanner`)
residem fora do grafo `nn.Module` (veja a nota apos o diagrama):

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
            |  output 153 -> 256  |   seed=42
            |  (ltc_projection)   |
            +---------+-----------+
                      |
            +---------v-----------+
            | HopfieldLayer       |   4 cabecas de atencao
            | (32 prototipos)     |   NN-MEM-01: bypassada
            | + Adicao Residual   |   ate o 1o step do otimiz.
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
            | Mixture of Experts  |   4 especialistas, routing top-2
            | + Superposition     |   context = metadata+belief
            | (FiLM) + Gate       |   (89-dim); entropy sparsity
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
  CAMADA 5: COMUNICACAO (RAPCommunication — fora do grafo nn.Module)
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
  CAMADA 6: ANALISE TEMPORAL (ChronovisorScanner — utilitario offline separado)
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

> **Nota -- staging vs. grafo forward literal.** O fluxo vertical acima e um staging
> pedagogico, nao o grafo exato de `RAPCoachModel.forward`: as heads de strategy,
> pedagogy e position consomem o estado oculto da memoria **em paralelo**;
> `CausalAttributor` consome adicionalmente o delta de posicao; `RAPCommunication`
> pos-processa os outputs retornados; e `ChronovisorScanner` e um scanner offline
> separado que conduz o modelo treinado pelas timelines dos matches.
>
> **Nota -- resolucao de input.** As formas de input `[B, 3, 64, 64]` refletem a
> configuracao de treinamento (`TrainingTensorConfig`, 64x64). `GhostEngine` usa
> `TrainingTensorConfig` para corresponder a resolucao de treinamento (F-0026 fechado).
> `ChronovisorScanner` usa o `TensorConfig` padrao (128/224) via
> `RAPStateReconstructor`; o `AdaptiveAvgPool2d` de `RAPPerception` acomoda a
> discrepancia.

## Constantes-Chave

> Os anchors de linha abaixo apontam para a implementacao canonica em
> `backend/nn/experimental/rap_coach/` -- os arquivos neste pacote sao shims
> de re-exportacao de poucas linhas.

| Constante | Valor | Fonte |
|-----------|-------|-------|
| `hidden_dim` | 256 | `experimental/rap_coach/model.py:45` |
| `perception_dim` | 128 | `experimental/rap_coach/model.py:42` (64 + 32 + 32) |
| `ncp_units` | 512 | `experimental/rap_coach/memory.py:52` (hidden_dim x 2) |
| `belief_dim` | 64 | `experimental/rap_coach/model.py:61` |
| strategy `context_dim` | 89 (25 metadata + 64 belief) | `experimental/rap_coach/model.py:62` |
| `OUTPUT_DIM` | 10 | `nn/config.py:186` |
| `METADATA_DIM` | 25 | `vectorizer.py:34` |
| `RAP_POSITION_SCALE` | 500.0 | `nn/config.py:218` |
| `num_experts` | 4 | `experimental/rap_coach/strategy.py:32` |
| `TOP_K` (especialistas roteados) | 2 | `experimental/rap_coach/strategy.py:30` |
| `hopfield_heads` | 4 | `experimental/rap_coach/memory.py:118` |
| prototipos hopfield (`quantity`) | 32 | `experimental/rap_coach/memory.py:119` |
| `Z_AXIS_PENALTY_WEIGHT` | 2.0 | `experimental/rap_coach/trainer.py:28` |

## Invariantes Criticas

| ID | Regra | Consequencia se Violada |
|----|-------|-------------------------|
| **NN-MEM-01** | A memoria Hopfield e bypassada ate que o trainer sinalize o primeiro step real do otimizador via `notify_optimizer_step()`. O carregamento de checkpoint a ativa somente quando o checkpoint de fato carrega pesos Hopfield. | Prototipos aleatorios injetam ruido em vez de sinal no combined_state, corrompendo o treinamento inicial. |
| **NN-RM-01** | `skill_vec` deve ter forma `[B, 10]`. Formas incompativeis sao registradas e ignoradas. | Dados lixo silenciosos no adaptador pedagogico distorcem as estimativas de valor. |
| **NN-RM-03** | `gate_weights` deve ser passado explicitamente para `compute_sparsity_loss()` (thread-safety, F3-07). | Condicao de corrida no estado em cache durante inferencia multi-thread. |
| **P-X-02** | As assercoes de forma do input impoem `metadata.shape[-1] == METADATA_DIM`. | Erros cripticos de dimensao LSTM/CNN nas profundezas da passagem forward. |
| **NN-CV-03** | Verificacao de limites do indice peak_tick antes de acessar o array ticks no ChronovisorScanner. | Crash IndexError durante a deteccao de momentos criticos. |

## Integracao

O RAP Coach se integra com o Macena CS2 Analyzer mais amplo atraves de varios pontos de contato:

- **CoachTrainingManager** (`backend/nn/coach_manager.py`) -- gate consultivo de maturidade para ChronovisorScanner (varreduras com maturidade insuficiente procedem com um warning)
- **FeatureExtractor** (`backend/processing/feature_engineering/vectorizer.py`) -- produz o vetor metadata de 25 dimensoes
- **RAPStateReconstructor** (`backend/processing/state_reconstructor.py`) -- converte dados brutos de tick em lotes de tensores prontos para o modelo
- **SuperpositionLayer** (`backend/nn/layers/superposition.py`) -- camada linear modulada por contexto usada pelos especialistas do RAPStrategy
- **Persistence** (`backend/nn/persistence.py`) -- `load_nn("rap_coach", model)` / `save_nn()` para gerenciamento de checkpoints
- **Structured Logging** -- modulos neurais logam sob `cs2analyzer.nn.experimental.rap_coach.<modulo>`; `ChronovisorScanner` loga sob `cs2analyzer.nn.chronovisor`

## Dependencias

| Pacote | Proposito | Opcional? |
|--------|-----------|-----------|
| `torch` | Operacoes tensoriais centrais, nn.Module | Obrigatorio |
| `ncps` | Neuronios LTC, fiacao AutoNCP | Opcional (protegido por `_RAP_DEPS_AVAILABLE`) |
| `hopfield-layers` (importado como `hflayers`) | Memoria associativa Hopfield | Opcional (protegido por `_RAP_DEPS_AVAILABLE`) |
| `numpy` | Processamento de sinal no ChronovisorScanner | Obrigatorio |
| `sqlmodel` | Consultas ao banco de dados no ChronovisorScanner | Obrigatorio (no momento da varredura) |

Quando `ncps` / `hopfield-layers` nao estao instalados, `RAPMemoryLite` (fallback baseado em LSTM)
esta disponivel via `use_lite_memory=True` em `RAPCoachModel.__init__()`.

## Notas de Desenvolvimento

- Este pacote (`backend/nn/rap_coach/`) contem apenas **shims de compatibilidade**.
  Toda a implementacao canonica reside em `backend/nn/experimental/rap_coach/`.
- O feature flag `USE_RAP_MODEL` e `False` por padrao. O modelo primario em producao e o JEPA.
- Alterar `ncp_units` ou `hidden_dim` invalida checkpoints existentes. O carregamento com
  controle de versao em `load_nn()` detecta incompatibilidades arquiteturais via `StaleCheckpointError`.
- O estado RNG para a fiacao AutoNCP e explicitamente salvo e restaurado (`seed=42`) para
  garantir uma topologia de rede deterministica e portavel entre checkpoints (NN-45 + NN-MEM-02).
- O trainer usa uma loss de 4 componentes ponderadas: strategy (1.0), value (0.5), sparsity (1.0,
  baseada em entropia sobre as probabilidades do gate, RAP-AUDIT-04), position (1.0). Erros de
  posicao no eixo Z sao penalizados com peso 2x (NN-TR-02b).
- A camada de comunicacao suprime conselhos quando a confianca do modelo esta abaixo do limiar de 0.7.
- Os findings anteriormente abertos F-0025 (labels de time apenas CT) e F-0026 (skew de resolucao de tensor treinamento/inferencia) foram fechados na revisao de 2026-08-21. Veja `docs/OPEN_ISSUES.md` para detalhes.
