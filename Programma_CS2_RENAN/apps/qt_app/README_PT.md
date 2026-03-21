# Aplicacao Desktop Qt (Primaria)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

*Mantido pela equipe Macena CS2 Analyzer. Requer familiaridade com PySide6, MVVM e Qt Signal/Slot.*

## Visao Geral

Aplicacao desktop PySide6/Qt implementando arquitetura Model-View-ViewModel (MVVM) com Qt Signal/Slot para analise tatica CS2 e coaching de IA. Este e o **frontend primario** (46 arquivos Python), substituindo o app legacy Kivy/KivyMD em [`desktop_app/`](../desktop_app/). A aplicacao conta com 13 telas, 7 ViewModels, 6 widgets de graficos, 3 widgets taticos, notificacoes toast, 3 temas QSS (CS2, CSGO, CS1.6), renderizacao de wallpaper de fundo, internacionalizacao (Ingles/Italiano/Portugues) e uma sequencia de encerramento controlado.

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
6. Instancia e registra todas as 13 telas (implementacoes reais, nao placeholders)
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
│   ├── worker.py                   # Worker QRunnable + WorkerSignals para tarefas em background
│   ├── asset_bridge.py             # QtAssetBridge: carrega imagens de mapa como QPixmap (singleton)
│   ├── i18n_bridge.py              # QtLocalizationManager: i18n baseado em JSON com Signal na troca de idioma
│   ├── qt_playback_engine.py       # QtPlaybackEngine: reproducao de demo baseada em QTimer a ~60 FPS
│   └── __init__.py
├── screens/
│   ├── home_screen.py              # Dashboard e visao geral
│   ├── coach_screen.py             # Interface de coaching IA com painel de chat
│   ├── match_history_screen.py     # Lista de partidas com rating HLTV 2.0 codificado por cor
│   ├── match_detail_screen.py      # Analise de partida multi-secao (visao geral, rounds, economia, momentum)
│   ├── performance_screen.py       # Analise de desempenho (tendencias, stats por mapa, comparacoes Z-score)
│   ├── tactical_viewer_screen.py   # Replay de mapa 2D com renderizacao pixel-accurate e timeline
│   ├── user_profile_screen.py      # Exibicao e edicao do perfil do usuario
│   ├── profile_screen.py           # Gerenciamento de perfil
│   ├── settings_screen.py          # Configuracoes da aplicacao (tema, fonte, idioma, caminhos)
│   ├── wizard_screen.py            # Assistente de primeiro uso para integracao Steam/Faceit
│   ├── help_screen.py              # Documentacao e guias do usuario
│   ├── steam_config_screen.py      # Configuracao de integracao Steam
│   ├── faceit_config_screen.py     # Configuracao de integracao Faceit
│   ├── placeholder.py              # Factory de placeholder para telas ainda nao portadas
│   └── __init__.py
├── viewmodels/
│   ├── match_history_vm.py         # Dados da lista de partidas, filtragem e ordenacao
│   ├── match_detail_vm.py          # Dados de analise por partida (rounds, economia, highlights)
│   ├── performance_vm.py           # Tendencias de desempenho, stats por mapa, forcas/fraquezas
│   ├── tactical_vm.py              # Controle de playback, predicoes ghost AI, varredura chronovisor
│   ├── coach_vm.py                 # Carregamento de insights de coaching do DB
│   ├── coaching_chat_vm.py         # Dialogo de coaching interativo via Ollama/LLM
│   ├── user_profile_vm.py          # Carregamento e salvamento de dados do perfil do usuario
│   └── __init__.py
├── widgets/
│   ├── toast.py                    # ToastWidget + ToastContainer: notificacoes efemeras (4 severidades)
│   ├── charts/
│   │   ├── radar_chart.py          # RadarChartWidget: radar de desempenho multidimensional
│   │   ├── momentum_chart.py       # MomentumGraphWidget: evolucao do momentum da equipe por round
│   │   ├── economy_chart.py        # EconomyGraphWidget: timeline de economia round-by-round
│   │   ├── rating_sparkline.py     # RatingSparklineWidget: sparkline compacto do historico de rating
│   │   ├── trend_chart.py          # TrendGraphWidget: visualizacao de tendencias de series temporais
│   │   ├── utility_bar_chart.py    # UtilityBarWidget: comparacao de uso de utilitarios (usuario vs baseline pro)
│   │   └── __init__.py
│   ├── tactical/
│   │   ├── map_widget.py           # MapWidget: renderizacao de mapa tatico 2D pixel-accurate
│   │   ├── player_sidebar.py       # PlayerSidebar: estado do jogador em tempo real (vida, armadura, armas)
│   │   ├── timeline_widget.py      # TimelineWidget: navegacao e scrubbing de playback de demo
│   │   └── __init__.py
│   └── __init__.py
└── themes/
    ├── cs2.qss                     # Tema CS2: estetica gaming escura com destaque laranja (#D96600)
    ├── csgo.qss                    # Tema CSGO: tons azul-ardosia com destaque aco
    └── cs16.qss                    # Tema CS 1.6: estetica retro terminal verde
```

## Arquitetura MVVM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MainWindow                                  │
│  ┌──────────┐  ┌─────────────────────────────────────────────────┐  │
│  │ Sidebar   │  │ QStackedWidget (13 telas)                      │  │
│  │ (5 bo-    │  │  ┌───────────────────────────────────────────┐ │  │
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
│                │ _BackgroundWidget (wallpaper, opacidade 25%)    │  │
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

## Telas (13)

| # | Tela | Arquivo | Descricao |
|---|------|---------|-----------|
| 1 | HomeScreen | `home_screen.py` | Dashboard com status do servico, contagem de partidas, progresso de treinamento, progresso de parsing |
| 2 | CoachScreen | `coach_screen.py` | Interface de coaching IA com cards de insight e painel de chat interativo (Ollama) |
| 3 | MatchHistoryScreen | `match_history_screen.py` | Lista de partidas com rating HLTV 2.0 codificado por cor, emite Signal `match_selected` |
| 4 | MatchDetailScreen | `match_detail_screen.py` | Analise de partida multi-secao: estatisticas, round-by-round, grafico de economia, momentum |
| 5 | PerformanceScreen | `performance_screen.py` | Analise de desempenho: tendencias de rating, stats por mapa, forcas/fraquezas, uso de utilitarios |
| 6 | TacticalViewerScreen | `tactical_viewer_screen.py` | Replay de mapa 2D com renderizacao pixel-accurate, overlay ghost AI, varredura chronovisor |
| 7 | UserProfileScreen | `user_profile_screen.py` | Exibicao de perfil do usuario com edicao de bio e funcao |
| 8 | ProfileScreen | `profile_screen.py` | Gerenciamento e configuracao de perfil |
| 9 | SettingsScreen | `settings_screen.py` | Configuracoes da aplicacao: selecao de tema, tipo/tamanho de fonte, idioma, caminhos de dados |
| 10 | WizardScreen | `wizard_screen.py` | Assistente de primeiro uso para caminho Steam, nome do jogador, config Faceit; emite `setup_completed` |
| 11 | HelpScreen | `help_screen.py` | Documentacao do usuario, guias e FAQ |
| 12 | SteamConfigScreen | `steam_config_screen.py` | Integracao Steam: configuracao de caminho, deteccao de pasta de demos |
| 13 | FaceitConfigScreen | `faceit_config_screen.py` | Integracao Faceit: configuracao de API key, ID do jogador |

## ViewModels (7)

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
| `UserProfileViewModel` | `user_profile_vm.py` | `profile_loaded(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carrega/salva `PlayerProfile` (bio, funcao) com acesso DB em background |

*Nota: O modulo Tactical contem 3 ViewModels em um unico arquivo (`tactical_vm.py`) por coesao.*

## Widgets

### Widgets de Graficos (`widgets/charts/`)

| Widget | Arquivo | Descricao |
|--------|---------|-----------|
| `RadarChartWidget` | `radar_chart.py` | Radar de desempenho multidimensional com renderizacao QPainter customizada |
| `MomentumGraphWidget` | `momentum_chart.py` | Evolucao do momentum da equipe por round, overlay duplo CT/T |
| `EconomyGraphWidget` | `economy_chart.py` | Timeline de economia round-by-round mostrando niveis de compra |
| `RatingSparklineWidget` | `rating_sparkline.py` | Sparkline compacto inline do historico de rating com indicador de tendencia |
| `TrendGraphWidget` | `trend_chart.py` | Visualizacao de tendencias de series temporais para qualquer metrica entre partidas |
| `UtilityBarWidget` | `utility_bar_chart.py` | Barras horizontais de comparacao de uso de utilitarios (usuario vs baseline pro) |

### Widgets Taticos (`widgets/tactical/`)

| Widget | Arquivo | Descricao |
|--------|---------|-----------|
| `MapWidget` | `map_widget.py` | Renderizacao de mapa tatico 2D pixel-accurate com pontos de jogador, overlays ghost e marcadores de evento |
| `PlayerSidebar` | `player_sidebar.py` | Estado do jogador em tempo real: vida, armadura, arma, dinheiro, status vivo/morto |
| `TimelineWidget` | `timeline_widget.py` | Navegacao de playback de demo com scrubbing, marcadores de round e indicadores de momentos criticos |

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
- **Folhas de estilo QSS** carregadas de `themes/*.qss`, com injecao dinamica de font-family/size
- **Configuracao QPalette** para widgets que nao respeitam QSS
- **5 fontes customizadas:** Roboto, JetBrains Mono, New Hope, CS Regular, YUPIX
- **Gerenciamento de wallpaper:** pastas de wallpaper por tema, preferencia por imagens verticais, renderizados a 25% de opacidade via `_BackgroundWidget`
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
| `QtAssetBridge` | `core/asset_bridge.py` | Singleton que carrega imagens de mapa como `QPixmap` com cache e fallback de tabuleiro xadrez magenta/preto |
| `QtLocalizationManager` | `core/i18n_bridge.py` | Singleton (`i18n`) que fornece `get_text(key)` com prioridade JSON, fallback hardcoded, e Signal `language_changed` |
| `QtPlaybackEngine` | `core/qt_playback_engine.py` | Subclasse de `PlaybackEngine` usando `QTimer` com intervalo de 16ms (~60 FPS) em vez de Kivy Clock |

## Notas de Desenvolvimento

- **Tamanho minimo da janela:** 1280x720 pixels
- **Largura da sidebar:** 220px fixa, com 5 botoes de navegacao (Home, Coach, History, Stats, Tactical)
- **Ciclo de vida da tela:** `on_enter()` e chamado automaticamente quando uma tela se torna visivel; `retranslate()` e chamado na troca de idioma
- **Thread safety:** Todos os acessos ao DB passam por Worker/QThreadPool. Nunca acesse sessoes SQLModel no thread principal.
- **i18n:** 3 idiomas (en, pt, it) carregados de `assets/i18n/*.json`. O Signal `language_changed` aciona `retranslate()` em todas as telas registradas.
- **Encerramento controlado:** `app.aboutToQuit` para o polling do AppState e encerra a console backend
- **Gate de primeiro uso:** Se a configuracao `SETUP_COMPLETED` e False, o app inicia na WizardScreen em vez da HomeScreen
- **Falha de inicializacao backend:** Se a console backend falhar ao iniciar, um aviso `QMessageBox` e exibido mas o app continua em modo degradado
