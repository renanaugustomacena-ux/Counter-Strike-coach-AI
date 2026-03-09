> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Processing — Pipeline de Dados e Engenharia de Características

Pipeline de processamento de dados orquestrando extração de características, gerenciamento de linhas de base, validação e geração de tensores para modelos ML.

## Módulos de Nível Superior

### Estatísticas de Round
- **round_stats_builder.py** — `build_round_stats()`, `compute_round_rating()`, `aggregate_round_stats_to_match()`, `enrich_from_demo()` — Cálculo de rating HLTV 2.0 por round, agregação a estatísticas de nível de partida, enriquecimento de demo com noscope/blind kills, flash assists, uso de utilitários.

### Tensores Visuais
- **tensor_factory.py** — `TensorFactory` — Gera tensores visuais de 5 canais para camada de percepção do RAP Coach: Ch0 (cone de visão), Ch1 (zonas de perigo - placeholder), Ch2 (contexto do mapa), Ch3 (vetores de movimento), Ch4 (posições de companheiros).

### Heatmaps e Visualização
- **heatmap_engine.py** — `HeatmapEngine` — Geração de heatmap de posição 2D com suavização de kernel Gaussiano para locais de morte, zonas de engajamento e uso de utilitários.

### Reconstrução de Estado
- **state_reconstructor.py** — `RAPStateReconstructor` — Reconstrução completa de estado do jogo a partir de dados de tick para treinamento do RAP Coach. Integra consciência espacial, rastreamento de economia e estado de momentum.

### Contexto do Mapa
- **connect_map_context.py** — Extração de características espaciais consciente do mapa com penalidade de eixo Z para mapas de vários níveis (Nuke, Vertigo). Integrado com `core/spatial_data.py` para lógica de Z-cutoff.

## Sub-Pacotes

### feature_engineering/
Extração de características unificada: `FeatureExtractor` (vetor 25-dim), componentes de rating HLTV 2.0, cálculo KAST, características específicas de função.

### baselines/
Linhas de base profissionais, limites de função, decaimento temporal, detecção de drift de características.

### validation/
Validação de arquivo de demo, conformidade de esquema, detecção de drift.

## Dependências
NumPy, Pandas, PyTorch, OpenCV (heatmaps), SQLModel.
