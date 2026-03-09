# Visualização & Geração de Relatórios

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Visão Geral

Motor de visualização baseado em Matplotlib e geração de relatórios PDF. Produz heatmaps, mapas de engajamento, gráficos de momentum, detalhamentos de utilitários e relatórios de desempenho multi-seção.

## Componentes Principais

### `visualizer.py`
- **`MatchVisualizer`** — Classe de visualização principal para análise de partida
- **Geração de heatmap** — Localizações de morte, zonas de engajamento, uso de utilitários sobrepostos em layouts de mapa
- **Mapas de engajamento** — Posicionamento de jogadores durante momentos críticos com marcadores scale-aware (micro/standard/macro)
- **Gráficos de momentum** — Linha do tempo de momentum round-por-round com anotações de vitória/derrota
- **Legenda de escala** — Indicador visual para escala de momento crítico (micro=100px, standard=200px, macro=350px)
- Gerenciamento de figuras Matplotlib com controle de DPI para saída de alta qualidade

### `report_generator.py`
- **Geração de relatórios PDF** — Relatórios multi-página com seções: Overview, Round Breakdown, Economy Timeline, Highlights
- **Visualização de rating HLTV 2.0** — Gráficos de barras comparando usuário vs baseline pro
- **Detalhamento de utilitários** — Gráficos de barras para HE, molotov, smokes, flashes, utilitários não usados
- **Cards de desempenho por-mapa** — Rating, K/D, ADR, KAST% por mapa
- **Forças/Fraquezas** — Comparação de Z-score contra baseline profissional

### `backend/reporting/analytics.py`
- **`get_rating_history()`** — Tendência de rating ao longo do tempo para renderização de sparkline
- **`get_per_map_stats()`** — Estatísticas de desempenho agregadas agrupadas por mapa
- **`get_strength_weakness()`** — Identifica top 3 forças e fraquezas via Z-score
- **`get_utility_breakdown()`** — Comparação de uso de utilitários usuário vs pro com métricas de eficácia
- **`get_hltv2_breakdown()`** — Detalhamento de componentes de rating HLTV 2.0 (K, S, KAST)

## Padrões de Visualização

Todas as visualizações usam:
- **Projeção de coordenadas map-aware** — Coordenadas de tick → coordenadas de pixel via `SpatialData`
- **Tratamento de Z-cutoff** — Mapas multi-nível (Nuke, Vertigo) com separação de planos verticais
- **Consistência de cores** — Cores de time (CT=azul, T=laranja), cores de severidade (crítico=vermelho, warning=amarelo)
- **Saída de alta DPI** — 300 DPI para incorporação em PDF, 150 DPI para preview de UI

## Renderização de Momentos Críticos

- **Escala micro** (1-3 ticks): marcador 100px, contorno laranja
- **Escala padrão** (4-10 ticks): marcador 200px, contorno vermelho
- **Escala macro** (>10 ticks): marcador 350px, preenchimento vermelho escuro

## Integração

Usado por `VisualizationService` para orquestração e telas de UI (`PerformanceScreen`, `MatchDetailScreen`) para renderização de gráficos inline.

## Formatos de Saída

- PNG para exibição em UI
- PDF para exportação de relatórios
- SVG para incorporação web (futuro)
