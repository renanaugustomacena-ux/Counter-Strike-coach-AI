> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Processing -- Pipeline de Dados, Engenharia de Características e Geração de Tensores

> **Autoridade:** Regra 1 (Corretude), Regra 5 (Dados Sobrevivem ao Código),
> Contrato Dimensional (`METADATA_DIM = 25`)

O pacote `processing` é a camada central de transformação de dados do
CS2 Coach AI. Ele fica entre os dados brutos das demos (produzidos por
`backend/data_sources/`) e os modelos de rede neural (consumidos por
`backend/nn/`). Cada módulo neste pacote converte, enriquece ou valida
dados -- nenhum deles armazena ou treina nada.

## Inventário de Arquivos

| Arquivo | Linhas | Propósito | Exports Principais |
|---------|--------|-----------|-------------------|
| `__init__.py` | 1 | Marcador de pacote | -- |
| `bombsite_encoding.py` | ~192 | Codificacao de centroide de bombsite e classificacao A/B | `encode_bombsite_context()` |
| `connect_map_context.py` | ~112 | Caracteristicas espaciais Z-aware relativas aos objetivos do mapa | `distance_with_z_penalty()`, `calculate_map_context_features()` |
| `data_pipeline.py` | ~408 | Limpeza de dados, scaling, split temporal, descontaminacao de jogadores | `ProDataPipeline` |
| `demo_prioritizer.py` | ~344 | Priorizacao de fila de demos pro (recencia, mapa, rating) | `DemoPrioritizer` |
| `demo_quality.py` | ~408 | Quality gates de demos (completude de tick, corrupcao, cobertura) | `DemoQualityAssessor` |
| `external_analytics.py` | ~201 | Comparacao z-score com datasets CSV de referencia elite | `EliteAnalytics` |
| `heatmap_engine.py` | ~300 | Mapas de ocupacao Gaussiana e heatmaps diferenciais usuario-vs-pro | `HeatmapEngine`, `HeatmapData`, `DifferentialHeatmapData` |
| `player_knowledge.py` | ~625 | Sistema de percepcao Player-POV (modelo sensorial NO-WALLHACK) | `PlayerKnowledge`, `PlayerKnowledgeBuilder` |
| `rating.py` | ~230 | Glue HLTV rating cross-modulo (agregacao nivel de partida) | `compute_match_rating()` |
| `round_reconstructor.py` | ~575 | Reconstrucao de estado por round a partir de streams de ticks brutos | `RoundReconstructor` |
| `round_stats_builder.py` | ~742 | Estatisticas por round e por jogador a partir de eventos de demo | `build_round_stats()`, `aggregate_round_stats_to_match()`, `enrich_from_demo()` |
| `skill_assessment.py` | ~161 | Decomposicao de habilidade em 5 eixos e projecao de nivel curricular | `SkillLatentModel`, `SkillAxes` |
| `state_reconstructor.py` | ~130 | Conversao tick-para-tensor para treinamento e inferencia do RAP-Coach | `RAPStateReconstructor` |
| `tensor_factory.py` | ~747 | Tensores de percepcao Player-POV (map, view, motion) | `TensorFactory`, `TensorConfig`, `TrainingTensorConfig`, `get_tensor_factory()` |
| `tick_enrichment.py` | ~350 | Caracteristicas contextuais cross-jogador para indices METADATA_DIM 20-24 | `enrich_tick_data()` |

## Sub-Pacotes

| Sub-Pacote | Arquivos | Propósito |
|------------|----------|-----------|
| `feature_engineering/` | `vectorizer.py`, `base_features.py`, `role_features.py`, `rating.py`, `kast.py` | Extração unificada de características 25-dim (`FeatureExtractor`), rating HLTV 2.0, cálculo KAST, características específicas de função |
| `baselines/` | `pro_baseline.py`, `role_thresholds.py`, `meta_drift.py`, `nickname_resolver.py` | Baselines profissionais, limites de função, decaimento temporal, detecção de meta-drift, resolução de nicknames |
| `validation/` | `dem_validator.py`, `schema.py`, `sanity.py`, `drift.py` | Validação de arquivo de demo, conformidade de esquema, verificações de sanidade, detecção de drift de características |

## Arquitetura e Conceitos

### Fluxo de Dados

```
arquivo .dem
  --> data_sources/ (demoparser2)
    --> tick_enrichment.py (características cross-jogador)
      --> round_stats_builder.py (agregação por round)
        --> data_pipeline.py (limpeza, scaling, split)
          --> feature_engineering/vectorizer.py (vetor 25-dim)
            --> tensor_factory.py (tensores de percepção de 3 canais)
              --> nn/ (RAP Coach, JEPA)
```

### Percepção Player-POV (NO-WALLHACK)

Um princípio de design central é que o coach de IA vê apenas o que o
jogador legitimamente sabe em cada tick. Isso é aplicado por
`player_knowledge.py` e consumido por `tensor_factory.py`:

- **Estado próprio:** Acesso completo (posição, yaw, vida, colete, arma).
- **Companheiros:** Sempre conhecidos (radar/comunicação).
- **Inimigos visíveis:** Apenas quando `enemies_visible > 0` E dentro do
  cone FOV. Mapas multi-nível (Nuke, Vertigo) usam um limiar Z-floor.
- **Últimos inimigos conhecidos:** Memória com decaimento exponencial
  (`half-life = MEMORY_DECAY_TAU_TICKS`).
- **Inferência sonora:** Eventos `weapon_fire` dentro de `HEARING_RANGE_GUNFIRE`.
- **Zonas de utility:** Smokes e molotovs ativos e flashes recentes.
- **Estado da bomba:** Conhecido por todos os jogadores.

### Canais de Tensores

`TensorFactory` produz três tensores de 3 canais por sequência de ticks:

| Tensor | Canal 0 | Canal 1 | Canal 2 |
|--------|---------|---------|---------|
| **map** | Posições de companheiros | Posições de inimigos (visíveis + últimos conhecidos com decay) | Zonas de utility + bomba |
| **view** | Máscara FOV (cone geométrico) | Entidades visíveis (ponderadas por distância) | Zonas de utility ativas |
| **motion** | Trilha de trajetória (últimos 32 ticks) | Gradiente radial de velocidade | Codificação de yaw-delta da mira |

### Salvaguardas da Pipeline de Dados

`ProDataPipeline` aplica diversas regras de integridade de dados:

- **P-DP-01:** Limiares de outlier derivados apenas do conjunto de
  treinamento (previne data leakage).
- **P-DP-02:** A descontaminação de jogadores atribui cada jogador ao
  seu split temporal **mais antigo**, descartando linhas de splits
  posteriores.
- **P-DP-03:** O multiplicador IQR para outlier é uma constante nomeada (3.0x).
- **P-DP-04:** Guarda de idempotência previne duplo scaling.
- **P-DP-05:** Verificação de versão do sklearn do scaler (comparação major.minor).

### Avaliação de Habilidades

`SkillLatentModel` decompõe as estatísticas do jogador em cinco eixos:

| Eixo | Métricas |
|------|----------|
| Mechanics | `accuracy`, `avg_hs` |
| Positioning | `rating_survival`, `rating_kast` |
| Utility | `utility_blind_time`, `utility_enemies_blinded` |
| Timing | `opening_duel_win_pct`, `positional_aggression_score` |
| Decision | `clutch_win_pct`, `rating_impact` |

A pontuação média de habilidade é projetada em um nível curricular de
1-10 via aproximação CDF Gaussiana (`sigmoid(1.702 * z)`).

## Integração

- **Pipeline de Ingestão:** `tick_enrichment.enrich_tick_data()` é
  chamado durante a ingestão de demos para calcular as características
  20-24 do vetor 25-dim. `round_stats_builder.enrich_from_demo()` produz
  enriquecimento a nível de partida.
- **Redes Neurais:** `state_reconstructor.RAPStateReconstructor` e
  `tensor_factory.TensorFactory` produzem os tensores consumidos pelos
  modelos RAP-Coach e JEPA.
- **Motor de Coaching:** `skill_assessment.SkillLatentModel` alimenta a
  camada curricular. `external_analytics.EliteAnalytics` fornece
  comparações z-score para o motor de correção.
- **UI / Visualização:** `heatmap_engine.HeatmapEngine` gera dados RGBA
  para heatmaps de posição e overlays diferenciais.

## Notas de Desenvolvimento

- Todos os cálculos de distância espacial em mapas multi-nível devem
  usar `distance_with_z_penalty()` de `connect_map_context.py`, não a
  distância Euclidiana bruta.
- `HeatmapEngine.generate_heatmap_data()` e
  `generate_differential_heatmap_data()` são thread-safe.
- `ProDataPipeline` limita as linhas em memória a `_MAX_PIPELINE_ROWS`
  (50.000) para prevenir OOM em deployments grandes.
- `player_knowledge.py` limita inimigos rastreados a `MAX_TRACKED_ENEMIES`
  (10) e travessia de histórico a `MAX_HISTORY_TICKS` (512).
- O módulo usa logging estruturado via
  `get_logger("cs2analyzer.<module>")` com IDs de correlação.
- Todas as alterações de características devem atualizar `FEATURE_NAMES`,
  `METADATA_DIM`, docstring de `extract()` e asserções `input_dim`
  dos modelos.
