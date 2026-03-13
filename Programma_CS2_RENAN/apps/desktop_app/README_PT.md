# Aplicacao Desktop (Legacy Kivy/KivyMD)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Nota:** Este e o frontend legacy Kivy/KivyMD. Ainda esta funcional e mantido como fallback. O frontend primario e PySide6/Qt -- veja [qt_app/](../qt_app/).

Aplicacao desktop Kivy/KivyMD implementando arquitetura MVVM para analise tatica CS2 e coaching de IA.

## Arquitetura

**Padrão:** Model-View-ViewModel (MVVM)
- **Views:** Classes Screen e widgets (definições layout.kv)
- **ViewModels:** Orquestradores de lógica de negócio (tactical_viewmodels.py, coaching_chat_vm.py)
- **Models:** Camada de dados backend (database.py, db_models.py)

## Telas (6)

1. **WizardScreen** (`wizard_screen.py`) — Assistente de configuração inicial para integração Steam e configuração de pastas
2. **TacticalViewerScreen** (`tactical_viewer_screen.py`) — Replay de mapa 2D com renderização pixel-accurate e navegação na linha do tempo
3. **MatchHistoryScreen** (`match_history_screen.py`) — Lista de partidas com rating HLTV 2.0 codificado por cor
4. **MatchDetailScreen** (`match_detail_screen.py`) — Análise em 4 seções:
   - Visão geral + estatísticas HLTV 2.0
   - Detalhamento por round
   - Linha do tempo de economia
   - Destaques + gráfico de Momentum
5. **PerformanceScreen** (`performance_screen.py`) — Análise de desempenho em 4 painéis:
   - Sparkline de tendência de rating
   - Cards de estatísticas por mapa
   - Forças/fraquezas vs baseline profissional (Z-score)
   - Painel de uso de utilitários (6 métricas)
6. **HelpScreen** (`help_screen.py`) — Documentação e guias do usuário

**Telas Adicionais (em main.py):**
- HomeScreen, CoachScreen, UserProfileScreen, SettingsScreen, ProfileScreen, SteamConfigScreen, FaceitConfigScreen

## Widgets Personalizados

**`widgets.py`** — 7 widgets personalizados:
- `MatplotlibWidget` — Canvas matplotlib incorporado para gráficos gerais
- `TrendGraphWidget` — Visualização de tendência de séries temporais
- `RadarChartWidget` — Radar de desempenho multidimensional
- `EconomyGraphWidget` — Linha do tempo de economia round-by-round
- `MomentumGraphWidget` — Evolução do momentum da equipe
- `RatingSparklineWidget` — Sparkline compacto de histórico de rating
- `UtilityBarWidget` — Barras de comparação de uso de utilitários (usuário vs baseline pro)

**`tactical_map.py`** — Widget `TacticalMap` com renderização 2D pixel-accurate de coordenadas spatial_data.py

**`player_sidebar.py`** — `LivePlayerCard`, `PlayerSidebar` para exibição de estado do jogador em tempo real

**`timeline.py`** — `TimelineScrubber` para navegação de reprodução de demo

**`ghost_pixel.py`** — `GhostPixelValidator` para debug do tactical viewer e verificação de coordenadas

## ViewModels (MVVM)

**`tactical_viewmodels.py`** — 3 ViewModels para Tactical Viewer:
- `TacticalPlaybackViewModel` — Controle de reprodução e gerenciamento de linha do tempo
- `TacticalGhostViewModel` — Renderização de ghost player para modo de comparação
- `TacticalChronovisorViewModel` — Detecção e visualização de momentos críticos (integração chronovisor)

**`coaching_chat_vm.py`** — `CoachingChatViewModel` para gerenciamento de diálogo de coaching de IA

## Definições de Layout

**`layout.kv`** (56 KB) — Definições de layout KivyMD para todas as telas com componentes Material Design
