# Aplicacao Desktop Qt (Primaria)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

*Mantido pela equipe Macena CS2 Analyzer. Requer familiaridade com PySide6, MVVM e Qt Signal/Slot.*

## Visao Geral

Aplicacao desktop PySide6/Qt implementando arquitetura Model-View-ViewModel (MVVM) com Qt Signal/Slot para analise tatica CS2 e coaching de IA. Este e o **frontend primario** (91 arquivos Python). A aplicacao conta com 15 telas, 10 ViewModels, 6 widgets de graficos QPainter (QtCharts foi removido por conformidade de licenca), 3 widgets taticos, uma biblioteca de componentes do design system (26 modulos) mais um ChatPanel de coaching integrado, notificacoes toast, 3 temas guiados por tokens (CS2, CSGO, CS1.6), wallpaper de fundo opcional (padrao: plano), internacionalizacao (Ingles/Italiano/Portugues, ~565 chaves por idioma) e uma sequencia de encerramento controlado.

## Ponto de Entrada

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

A funcao `main()` em `app.py` executa a seguinte sequencia de inicializacao:

1. Habilita escalonamento High-DPI (politica de arredondamento `PassThrough`)
2. Cria `QApplication` e resolve a versao do pacote
3. Conecta o handler de encerramento controlado (signal `aboutToQuit`)
4. Instancia `ThemeEngine`, registra fontes customizadas, aplica o tema ativo
5. Cria `MainWindow` e define o wallpaper inicial
6. Instancia e registra todas as 15 telas (implementacoes reais, nao placeholders)
7. Conecta signals entre telas (selecao de partida: history -> detail, conclusao wizard -> home)
8. Gate de primeiro uso: mostra WizardScreen se `SETUP_COMPLETED` e False, caso contrario HomeScreen
9. Inicializa a console backend (audit DB, FlareSolverr/Hunter condicional) com dialogo de erro como fallback
10. Inicia o polling em background do AppState (intervalo de 10 segundos)

## Estrutura de Diretorios

```
qt_app/
├── app.py                          # Ponto de entrada: bootstrap QApplication e registro de telas
├── main_window.py                  # QMainWindow com navegacao sidebar + QStackedWidget + camada toast
├── __init__.py
├── core/
│   ├── app_state.py                # Singleton AppState: consulta CoachState DB a cada 10s, emite Signals
│   ├── theme_engine.py             # ThemeEngine: carregamento QSS, QPalette, fontes, gerenciamento wallpaper
│   ├── design_tokens.py            # Definicoes de design tokens para o sistema de componentes Qt
│   ├── qss_generator.py            # Geracao programatica de QSS a partir dos design tokens
│   ├── animation.py                # Utilitarios de animacao compartilhados e helpers de easing
│   ├── easing.py                   # Curvas de easing personalizadas
│   ├── typography.py               # Escala tipografica e helpers de fonte
│   ├── icons.py                    # Registro de icones e carregador de assets SVG/icones
│   ├── svg_icon_provider.py        # QIconEngine baseado em recursos SVG
│   ├── sound.py                    # Helpers de reproducao de efeitos sonoros
│   ├── match_utils.py              # Funcoes utilitarias a nivel de partida para a camada UI
│   ├── widgets_helpers.py          # Funcoes helper Qt widget genericas
│   ├── web_bridge.py               # Bridge Python↔JavaScript para web views integradas
│   ├── worker.py                   # Worker QRunnable + WorkerSignals para tarefas em background
│   ├── i18n_bridge.py              # QtLocalizationManager: i18n baseado em JSON com Signal na troca de idioma
│   ├── qt_playback_engine.py       # QtPlaybackEngine: reproducao de demo baseada em QTimer a ~60 FPS
│   └── __init__.py
├── screens/
│   ├── home_screen.py              # Dashboard e visao geral
│   ├── coach_screen.py             # Tela de coaching IA com ChatPanel integrado (dock removido)
│   ├── match_history_screen.py     # Lista de partidas com rating HLTV 2.0 codificado por cor
│   ├── match_detail_screen.py      # Analise de partida em 4 abas (Visao geral · Rounds · Economia · Highlights)
│   ├── performance_screen.py       # Analise de desempenho (tendencias, stats por mapa, comparacoes Z-score)
│   ├── tactical_viewer_screen.py   # Replay de mapa 2D com renderizacao pixel-accurate e timeline
│   ├── user_profile_screen.py      # Exibicao e edicao do perfil do usuario
│   ├── profile_screen.py           # Gerenciamento de perfil
│   ├── settings_screen.py          # Configuracoes da aplicacao (tema, fonte, idioma, caminhos)
│   ├── wizard_screen.py            # Assistente de primeiro uso para integracao Steam/Faceit
│   ├── help_screen.py              # Documentacao e guias do usuario
│   ├── steam_config_screen.py      # Configuracao de integracao Steam
│   ├── faceit_config_screen.py     # Configuracao de integracao Faceit
│   ├── pro_comparison_screen.py    # Analise comparativa usuario vs jogador pro
│   ├── pro_player_detail_screen.py # Vista de perfil do jogador pro
│   ├── placeholder.py              # Factory de placeholder para telas ainda nao portadas
│   └── __init__.py
├── viewmodels/
│   ├── match_history_vm.py         # Dados da lista de partidas, filtragem e ordenacao
│   ├── match_detail_vm.py          # Dados de analise por partida (rounds, economia, highlights)
│   ├── performance_vm.py           # Tendencias de desempenho, stats por mapa, forcas/fraquezas
│   ├── tactical_vm.py              # Controle de playback, predicoes ghost AI, varredura chronovisor
│   ├── coach_vm.py                 # Carregamento de insights de coaching do DB
│   ├── coaching_chat_vm.py         # Dialogo de coaching interativo via Ollama/LLM
│   ├── focus_insight_vm.py         # ViewModel de detalhe de insight de coaching focalizado
│   ├── pro_comparison_vm.py        # Dados e pontuacao de comparacao pro
│   ├── pro_player_detail_vm.py     # Carregamento de dados do perfil do jogador pro
│   ├── user_profile_vm.py          # Carregamento e salvamento de dados do perfil do usuario
│   └── __init__.py
├── widgets/
│   ├── toast.py                    # ToastWidget + ToastContainer: notificacoes efemeras (4 severidades)
│   ├── skeleton.py                 # Widgets placeholder de carregamento skeleton
│   ├── charts/                     # Todos QPainter — QtCharts removido (somente GPL)
│   │   ├── economy_chart.py        # EconomyChart: barras de economia round a round (QPainter)
│   │   ├── mini_sparkline.py       # MiniSparkline: sparkline compacta com QPainter, sem eixos
│   │   ├── momentum_chart.py       # MomentumChart: grafico de area do momentum da equipe (QPainter)
│   │   ├── radar_chart.py          # RadarChart: radar pentagonal de skills (overlay usuario vs pro)
│   │   ├── rating_sparkline.py     # RatingSparkline: tendencia de rating com linha de base
│   │   ├── utility_bar_chart.py    # UtilityBarChart: barras horizontais de uso de utilitarios
│   │   └── __init__.py
│   ├── coaching/
│   │   ├── chat_panel.py           # ChatPanel: chat do coach integrado (baloes, linha meta, linha de input)
│   │   └── __init__.py
│   ├── components/                 # Componentes de UI reutilizaveis (design system) — 26 modulos
│   │   ├── __init__.py             # Exports dos componentes
│   │   ├── card.py                 # Widget container de card (5 variantes de profundidade)
│   │   ├── db_record_card.py       # DbRecordCard: eco mono da linha do DB (tabela · coluna · valor)
│   │   ├── delta_chip.py           # DeltaChip: pilula de delta ▲/▼ relativa ao benchmark
│   │   ├── drivers_list.py         # DriversList: linhas de contribuicao com sinal (o que moveu uma estatistica)
│   │   ├── empty_state.py          # Placeholder de estado vazio com icone e mensagem
│   │   ├── filter_chip.py          # Pilula de filtro alternavel
│   │   ├── focus_insight.py        # FocusInsightCard: card de foco de insight da home
│   │   ├── hero_stats_strip.py     # Faixa horizontal de metricas hero
│   │   ├── icon_widget.py          # Widget de exibicao de icone (SVG/pixmap)
│   │   ├── last_match_hero.py      # LastMatchHeroCard: card hero da ultima partida na home
│   │   ├── map_tile.py             # MapTile: tile de estatisticas por mapa com destaque de win-rate
│   │   ├── match_mini_card.py      # Card compacto de resumo de partida
│   │   ├── match_row_card.py       # Card de linha de partida expandido com previa de estatisticas
│   │   ├── metric_bar_row.py       # MetricBarRow: label + barra de metrica horizontal + valor
│   │   ├── mini_link_card.py       # MiniLinkCard: pequeno card de navegacao de links relacionados
│   │   ├── mono_footer.py          # MonoFooter: linha de rodape mono de proveniencia/status
│   │   ├── nav_sidebar.py          # Componente de barra lateral de navegacao recolhivel
│   │   ├── numbered_step.py        # NumberedStep: linha de passo 01/02/03 em mono acentuado
│   │   ├── pro_badge.py            # ProBadge: pilula PRO/tier para superficies de jogadores pro
│   │   ├── progress_ring.py        # Indicador de anel de progresso circular
│   │   ├── section_header.py       # Cabecalho de secao com titulo e acao opcional
│   │   ├── stat_badge.py           # Badge de estatistica com label e valor
│   │   ├── status_chip.py          # Pilula de status colorida com label de texto
│   │   ├── stepper.py              # Indicador de progresso em passos rotulados (usado pelo wizard)
│   │   ├── tip_box.py              # TipBox: caixa de dica com borda em destaque
│   │   └── toggle_switch.py        # Interruptor booleano animado
│   ├── tactical/
│   │   ├── map_widget.py           # TacticalMapWidget: renderizacao de mapa 2D + overlays de zonas (assets/map_zones/) + trilhas de movimento
│   │   ├── player_sidebar.py       # PlayerSidebar: estado do jogador em tempo real (vida, armadura, armas)
│   │   ├── timeline_widget.py      # TimelineWidget: scrubbing, divisores de round, glifos de momentos ★/◆/●
│   │   └── __init__.py
│   └── __init__.py
├── web/                            # Sub-apps TypeScript (integradas via QWebEngineView)
│   ├── coach-chat/
│   ├── match-detail/
│   ├── tactical-viewer/
│   └── shared/
└── themes/
    └── base.qss.template           # Folha de estilo com tokens — unica fonte QSS
                                    # (renderizada por tema por core/qss_generator.py)
```

## Arquitetura MVVM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MainWindow                                  │
│  ┌──────────┐  ┌─────────────────────────────────────────────────┐  │
│  │ Sidebar   │  │ QStackedWidget (15 telas)                      │  │
│  │ (7 bo-    │  │  ┌───────────────────────────────────────────┐ │  │
│  │  toes)    │  │  │  Screen (QWidget)                         │ │  │
│  │           │  │  │   │                                       │ │  │
│  │  Home     │  │  │   │ conecta-se a                          │ │  │
│  │  Coach    │  │  │   ▼                                       │ │  │
│  │  History  │  │  │  ViewModel (QObject)                      │ │  │
│  │  Stats    │  │  │   │ Signal ──────> Screen atualiza a UI   │ │  │
│  │  Tactical │  │  │   │                                       │ │  │
│  │           │  │  │   │ Worker (QRunnable)                    │ │  │
│  │           │  │  │   │ └──> DB/calculo em background         │ │  │
│  │           │  │  │   │      └──> Signal.result ──> ViewModel │ │  │
│  │           │  │  └───────────────────────────────────────────┘ │  │
│  └──────────┘  └─────────────────────────────────────────────────┘  │
│                ┌─────────────────────────────────────────────────┐  │
│                │ _BackgroundWidget (wallpaper, opacidade 15%)    │  │
│                │ ToastContainer (overlay de notificacoes sup-dx) │  │
│                └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              AppState (singleton, consulta CoachState DB a cada 10s)
              └──> service_active_changed, coach_status_changed,
                   parsing_progress_changed, belief_confidence_changed,
                   total_matches_changed, training_changed,
                   notification_received
```

**Fluxo de dados:** Screen <-> ViewModel (QObject + Signals) <-> Database (SQLModel) via Worker threads. Todos os acessos ao banco de dados ocorrem no `QThreadPool`; os resultados sao automaticamente encaminhados de volta ao thread principal via conexoes Signal.

## Telas (15)

| # | Tela | Arquivo | Descricao |
|---|------|---------|-----------|
| 1 | HomeScreen | `home_screen.py` | Dashboard com status do servico, contagem de partidas, progresso de treinamento, progresso de parsing |
| 2 | CoachScreen | `coach_screen.py` | **Tela empilhada** de coaching IA com anel de belief, top-3 insights ranqueados e ChatPanel integrado (Ollama) — o antigo dock de chat QDockWidget foi removido |
| 3 | MatchHistoryScreen | `match_history_screen.py` | Lista de partidas com rating HLTV 2.0 codificado por cor, emite Signal `match_selected` |
| 4 | MatchDetailScreen | `match_detail_screen.py` | Analise de partida em 4 abas: Visao geral · Rounds · Economia · Highlights (abas sublinhadas, frame 09) |
| 5 | PerformanceScreen | `performance_screen.py` | Analise de desempenho: tendencias de rating, stats por mapa, forcas/fraquezas, uso de utilitarios |
| 6 | TacticalViewerScreen | `tactical_viewer_screen.py` | Replay de mapa 2D com overlays de zonas, trilhas de movimento, timeline de glifos (★ critico · ◆ clutch · ● jogada), varredura chronovisor e Ghost Mode (progresso duplo + painel de divergencia) |
| 7 | UserProfileScreen | `user_profile_screen.py` | Exibicao de perfil do usuario com edicao de bio e funcao |
| 8 | ProfileScreen | `profile_screen.py` | Editor de nome no jogo (frame 17): nota de maiusculas/minusculas, eco DbRecordCard, cards de links relacionados, nota de armazenamento local |
| 9 | SettingsScreen | `settings_screen.py` | Configuracoes da aplicacao: cards de previa de tema clicaveis, tipo/tamanho de fonte, previa ao vivo, idioma, caminhos de dados |
| 10 | WizardScreen | `wizard_screen.py` | Assistente de primeiro uso com stepper rotulado (Intro · Nome · Pasta do Brain · Pasta de demos · Inicio) e texto de calibracao "O que acontece agora"; emite `setup_completed` |
| 11 | HelpScreen | `help_screen.py` | Artigo de ajuda estruturado: passos numerados para comecar, cards de topicos, dicas de teclado, proveniencia dos documentos |
| 12 | SteamConfigScreen | `steam_config_screen.py` | Integracao Steam: configuracao de caminho, deteccao de pasta de demos |
| 13 | FaceitConfigScreen | `faceit_config_screen.py` | Integracao Faceit: configuracao de API key, ID do jogador |
| 14 | ProComparisonScreen | `pro_comparison_screen.py` | Comparacao estatistica lado a lado usuario vs jogador pro selecionado |
| 15 | ProPlayerDetailScreen | `pro_player_detail_screen.py` | Perfil completo do jogador pro: estatisticas de carreira, heatmaps, jogadas caracteristicas |

## ViewModels (10)

| ViewModel | Arquivo | Signals Principais | Descricao |
|-----------|---------|---------------------|-----------|
| `MatchHistoryViewModel` | `match_history_vm.py` | `matches_changed(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Carrega lista de partidas de `PlayerMatchStats` com suporte a cancelamento |
| `MatchDetailViewModel` | `match_detail_vm.py` | `data_changed(dict, list, list, dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carrega estatisticas da partida, dados de rounds, insights de coaching, breakdown HLTV |
| `PerformanceViewModel` | `performance_vm.py` | `data_changed(list, dict, dict, dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carrega historico de rating, stats por mapa, forcas/fraquezas, dados de utility |
| `TacticalPlaybackVM` | `tactical_vm.py` | `frame_updated(object)`, `current_tick_changed(int)`, `is_playing_changed(bool)` | Controle de playback: play/pause, velocidade, seek, rastreamento de tick via PlaybackEngine |
| `TacticalGhostVM` | `tactical_vm.py` | `ghost_active_changed(bool)`, `is_loaded_changed(bool)` | Predicoes de posicao ghost AI via GhostEngine carregado lazily |
| `TacticalChronovisorVM` | `tactical_vm.py` | `scan_complete(list, int)`, `navigate_to(int, str)`, `is_scanning_changed(bool)` | Varredura de momentos criticos e navegacao jump-to via ChronovisorScanner |
| `CoachViewModel` | `coach_vm.py` | `insights_loaded(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Carrega as ultimas linhas de `CoachingInsight` para o jogador ativo |
| `CoachingChatViewModel` | `coaching_chat_vm.py` | `messages_changed(list)`, `session_active_changed(bool)`, `is_available_changed(bool)` | Chat de coaching interativo via CoachingDialogueEngine (backend Ollama) |
| `FocusInsightViewModel` | `focus_insight_vm.py` | `insight_changed(object)`, `is_loading_changed(bool)` | Carrega e gerencia a vista de detalhe para um unico insight de coaching focalizado |
| `ProComparisonViewModel` | `pro_comparison_vm.py` | `data_changed(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Busca e calcula a pontuacao da comparacao estatistica usuario-vs-pro |
| `ProPlayerDetailViewModel` | `pro_player_detail_vm.py` | `profile_changed(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carrega perfil do jogador pro e estatisticas de carreira |
| `UserProfileViewModel` | `user_profile_vm.py` | `profile_loaded(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carrega/salva `PlayerProfile` (bio, funcao) com acesso DB em background |

*Nota: O modulo Tactical contem 3 ViewModels em um unico arquivo (`tactical_vm.py`) por coesao.*

## Widgets

### Widgets de Graficos (`widgets/charts/`) — todos QPainter

> **QtCharts foi removido** do app: Qt Charts esta disponivel apenas sob licenca GPLv3 ou comercial (diferente do Qt base, LGPL), incompativel com este repositorio proprietario. Cada grafico agora e uma implementacao custom de `QWidget.paintEvent`; um teste de guarda de licenca (`test_charts.py::TestQtChartsRetired`) falha a suite se qualquer referencia `QtCharts`/`QChart` reaparecer sob `apps/qt_app/`.

| Widget | Arquivo | Descricao |
|--------|---------|-----------|
| `EconomyChart` | `economy_chart.py` | Barras de economia round a round com coloracao por lado, divisor de metade e escala $K |
| `MiniSparkline` | `mini_sparkline.py` | Sparkline compacta sem eixos, usada no card hero da ultima partida |
| `MomentumChart` | `momentum_chart.py` | Evolucao do momentum da equipe por round, overlay de area duplo CT/T |
| `RadarChart` | `radar_chart.py` | Radar pentagonal de skills com overlay poligonal usuario-vs-pro (comparacao pro) |
| `RatingSparkline` | `rating_sparkline.py` | Linha de tendencia de rating com baseline 1.0 (detalhe de partida / desempenho) |
| `UtilityBarChart` | `utility_bar_chart.py` | Barras horizontais de uso de utilitarios (flash/smoke/HE/molly) |

### Widgets de Coaching (`widgets/coaching/`)

| Widget | Arquivo | Descricao |
|--------|---------|-----------|
| `ChatPanel` | `chat_panel.py` | Chat do coach integrado: baloes de mensagem, linha meta mono de proveniencia, estados de disponibilidade, linha de input — hospedado pela CoachScreen (substitui o dock de chat removido) |

### Primitivas de componentes adicionadas no rebuild design-atlas (`widgets/components/`)

| Widget | Arquivo | Descricao |
|--------|---------|-----------|
| `ProBadge` | `pro_badge.py` | Pilula PRO/tier para superficies de jogadores pro |
| `DeltaChip` | `delta_chip.py` | Pilula de delta ▲/▼ relativa ao benchmark (vs media de 30 dias / baseline pro) |
| `DriversList` | `drivers_list.py` | Linhas de contribuicao com sinal explicando o que moveu uma estatistica |
| `TipBox` | `tip_box.py` | Caixa de dica com borda em destaque (wizard, ajuda) |
| `NumberedStep` | `numbered_step.py` | Linha de passo 01/02/03 em mono acentuado (pagina de inicio do wizard, ajuda) |
| `DbRecordCard` | `db_record_card.py` | Eco mono da linha do DB (`tabela · coluna · valor`, frame 17) |
| `MonoFooter` | `mono_footer.py` | Linha de rodape mono de proveniencia/status (legendas no pe das telas) |
| `MiniLinkCard` | `mini_link_card.py` | Pequeno card de navegacao de links relacionados |
| `MapTile` | `map_tile.py` | Tile de estatisticas por mapa com destaque de win-rate |
| `MetricBarRow` | `metric_bar_row.py` | Linha label + barra de metrica horizontal + valor |

### Widgets Taticos (`widgets/tactical/`)

| Widget | Arquivo | Descricao |
|--------|---------|-----------|
| `TacticalMapWidget` | `map_widget.py` | Renderizacao de mapa tatico 2D com pontos de jogador, overlays de zonas nomeadas (`assets/map_zones/*.json`), trilhas de movimento, overlays ghost e marcadores de evento |
| `PlayerSidebar` | `player_sidebar.py` | Estado do jogador em tempo real: vida, armadura, arma, dinheiro, status vivo/morto |
| `TimelineWidget` | `timeline_widget.py` | Scrubbing de playback de demo com divisores de round, marcadores de evento e glifos de momentos criticos diferenciados por tipo (★ critico / ◆ clutch / ● jogada, fallback estrela) |

### Notificacoes Toast (`widgets/toast.py`)

| Severidade | Icone | Auto-fechamento |
|------------|-------|-----------------|
| INFO | (i) | 5 segundos |
| WARNING | (!) | 8 segundos |
| ERROR | (X) | 12 segundos |
| CRITICAL | (caveira) | Somente manual |

Maximo de 3 toasts visiveis simultaneamente. O toast mais antigo e removido quando o limite e excedido. O `ToastContainer` e renderizado como overlay no canto superior direito acima de todo o conteudo das telas via `QStackedLayout.StackAll`.

## Singleton AppState

`AppState` (`core/app_state.py`) e um singleton `QObject` obtido via `get_app_state()`. Consulta a linha do banco de dados `CoachState` (id=1) a cada 10 segundos usando um pattern `QTimer` + `Worker`, e emite signals tipados apenas quando os valores realmente mudam (emissao baseada em delta):

| Signal | Tipo | Acionamento |
|--------|------|-------------|
| `service_active_changed` | `bool` | Delta heartbeat > 300 segundos = inativo |
| `coach_status_changed` | `str` | Texto de status de ingestao mudou |
| `parsing_progress_changed` | `float` | Progresso de parsing de demo atualizado |
| `belief_confidence_changed` | `float` | Confianca de belief do modelo atualizada |
| `total_matches_changed` | `int` | Total de partidas processadas mudou |
| `training_changed` | `dict` | Qualquer entre: current_epoch, total_epochs, train_loss, val_loss, eta_seconds |
| `notification_received` | `(str, str)` | Linhas `ServiceNotification` nao lidas (severidade + mensagem) |

AppState e **somente leitura** do lado Qt. Apenas o session engine do backend escreve em `CoachState`.

## ThemeEngine

`ThemeEngine` (`core/theme_engine.py`) gerencia a identidade visual da aplicacao:

- **3 temas:** CS2 (escuro + destaque laranja), CSGO (azul-ardosia + destaque aco), CS 1.6 (retro terminal verde)
- **Design tokens sao a unica fonte de verdade:** os conjuntos de tokens por tema (`core/design_tokens.py`) alimentam **tanto** o render QSS (`themes/base.qss.template` via `core/qss_generator.py`, com injecao dinamica de font-family/size) **quanto** a configuracao `QPalette` para widgets que nao respeitam QSS — nenhum valor de cor mantido a mao fora das tabelas de tokens
- **Fontes:** as fontes legadas de `PHOTO_GUI/` (Roboto, JetBrains Mono, New Hope, CS Regular, YUPIX) mais o stack display OFL embarcado, auto-escaneado de `assets/fonts/` (Space Grotesk, Inter, pesos JetBrains Mono — veja `assets/fonts/README.txt` para fontes/licencas)
- **Wallpaper:** o padrao e **sem wallpaper** — fundo plano `surface_base` conforme o design atlas. Uma escolha persistida do usuario pode selecionar um arquivo de wallpaper por tema, renderizado a 15% de opacidade via `_BackgroundWidget`
- **Cores de rating HLTV:** verde (> 1.10), amarelo (0.90-1.10), vermelho (< 0.90) com labels de texto WCAG 1.4.1

## Pattern Worker

A classe `Worker` (`core/worker.py`) e um `QRunnable` que encapsula qualquer callable para execucao no `QThreadPool.globalInstance()`. Emite tres signals via `WorkerSignals`:

```python
worker = Worker(some_function, arg1, arg2)
worker.signals.result.connect(on_success)   # auto-marshal para o thread principal
worker.signals.error.connect(on_error)       # recebe str(exception)
worker.signals.finished.connect(on_done)     # sempre emitido
QThreadPool.globalInstance().start(worker)
```

Todas as emissoes de signal sao protegidas por `try/except RuntimeError` para lidar com o caso em que o receptor e coletado pelo garbage collector antes do worker finalizar. Workers sao auto-deletados apos a execucao (`setAutoDelete(True)`).

## Modulos Core Adicionais

| Modulo | Arquivo | Descricao |
|--------|---------|-----------|
| `QtLocalizationManager` | `core/i18n_bridge.py` | Singleton (`i18n`) que fornece `get_text(key)` com prioridade JSON, fallback hardcoded, e Signal `language_changed` |
| `QtPlaybackEngine` | `core/qt_playback_engine.py` | Subclasse de `PlaybackEngine` usando `QTimer` com intervalo de 16ms (~60 FPS) |
| `DesignTokens` | `core/design_tokens.py` | Definicoes de design tokens (espacamento, raio, elevacao) para o sistema de componentes Qt |
| `QSSGenerator` | `core/qss_generator.py` | Geracao programatica de folhas de estilo QSS a partir dos design tokens |
| `Animation` | `core/animation.py` | Utilitarios de animacao compartilhados e helpers de easing para transicoes de widgets |
| `Icons` | `core/icons.py` | Registro de icones e carregador de assets SVG/icones para o sistema de componentes |
| `Easing` | `core/easing.py` | Curvas de easing personalizadas para animacoes de widgets |
| `Typography` | `core/typography.py` | Definicoes de escala tipografica e helpers de fonte |
| `SVGIconProvider` | `core/svg_icon_provider.py` | Implementacao QIconEngine baseada em recursos SVG |
| `Sound` | `core/sound.py` | Helpers de reproducao de efeitos sonoros para feedback UI |
| `MatchUtils` | `core/match_utils.py` | Funcoes utilitarias a nivel de partida para a camada UI |
| `WidgetsHelpers` | `core/widgets_helpers.py` | Funcoes helper Qt widget genericas |
| `WebBridge` | `core/web_bridge.py` | Bridge Python↔JavaScript para web views integradas |

## Testes

A suite de UI roda inteiramente offscreen (`QT_QPA_PLATFORM=offscreen`) com animacoes desabilitadas (`MACENA_UI_ANIMATIONS=0`):

| Arquivo | Cobertura |
|---------|-----------|
| `tests/test_qt_core.py` | Modulos core (tokens, geracao QSS, bridge i18n, workers) — inclui um teste de animacao ao vivo **isolado em subprocesso**, para exercitar o caminho com animacoes habilitadas sem poluir a execucao offscreen |
| `tests/test_ui_smoke.py` | **Walk em runtime**: inicializa a MainWindow real, visita cada tela, troca ao vivo os 3 temas, faz o roundtrip dos idiomas (retranslate), recolhe/expande a sidebar |
| `tests/test_ui_harness.py` | **Paridade de chaves i18n** entre en/it/pt (`test_i18n_key_parity_across_languages`) + executa o harness de screenshot ponta a ponta como subprocesso |
| `tests/test_charts.py` | Widgets de graficos QPainter + o gate de licenca QtCharts (`TestQtChartsRetired`) |
| `tests/test_tactical_frame_widgets.py` | Loader de zonas de mapa, mapeamento tipo→glifo da timeline + hit-test de estrelas, adapter de linhas de divergencia do ghost |
| `tests/test_detonation_overlays.py` | Painting de overlays de detonacao de granadas/bomba |

Ferramentas de screenshot: `tools/ui_screenshot.py` (harness offscreen — telas reais + dados de fixture de `tools/ui_fixtures.py`, PNGs por tema) e `tools/ui_gallery.py` (folha de galeria de componentes).

## Notas de Desenvolvimento

- **Tamanho minimo da janela:** 1280x720 pixels
- **Sidebar:** recolhivel 220px ↔ 60px, com 7 botoes de navegacao (Home, Coach, Match History, Performance, Tactical Viewer, Settings, Help)
- **Ciclo de vida da tela:** `on_enter()` e chamado automaticamente quando uma tela se torna visivel; `retranslate()` e chamado na troca de idioma
- **Thread safety:** Todos os acessos ao DB passam por Worker/QThreadPool. Nunca acesse sessoes SQLModel no thread principal.
- **i18n:** 3 idiomas (en, pt, it) carregados de `assets/i18n/*.json`. O Signal `language_changed` aciona `retranslate()` em todas as telas registradas.
- **Encerramento controlado:** `app.aboutToQuit` para o polling do AppState e encerra a console backend
- **Gate de primeiro uso:** Se a configuracao `SETUP_COMPLETED` e False, o app inicia na WizardScreen em vez da HomeScreen
- **Falha de inicializacao backend:** Se a console backend falhar ao iniciar, um aviso `QMessageBox` e exibido mas o app continua em modo degradado
