> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Apps — Camada de Interface do Usuario

> **Autoridade:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Visao Geral

O diretorio `apps/` contem todo o codigo de interface do usuario do Macena CS2 Analyzer.
Dois frameworks de UI coexistem como parte de uma estrategia de migracao deliberada:

- **Fase 0 (Legacy):** `desktop_app/` foi o prototipo original construido com Kivy +
  KivyMD. Serviu como shell de prototipagem rapida durante o desenvolvimento inicial.
  Nenhuma funcionalidade nova e adicionada aqui; existe apenas como referencia e para
  componentes ainda nao portados.

- **Fase 2+ (Ativo):** `qt_app/` e a UI desktop de producao construida com PySide6
  (Qt6). Todas as novas telas, widgets e funcionalidades sao destinadas exclusivamente
  a este framework. Qt foi escolhido pelo seu visual nativo, modelo de threading
  maduro (QThreadPool/QRunnable), biblioteca de graficos integrada (QtCharts) e amplo
  suporte multiplataforma.

Ambos os frameworks compartilham os mesmos servicos backend (`backend/services/`),
camada de banco de dados (`backend/storage/`) e sistema de configuracao (`core/config.py`).
A camada de UI e estritamente um consumidor dos dados do backend — ela nunca escreve
diretamente no banco de dados.

## Estrutura do Diretorio

```
apps/
├── __init__.py
├── README.md                    # Versao em ingles
├── README_IT.md                 # Traducao italiana
├── README_PT.md                 # Este arquivo
├── spatial_debugger.py          # Ferramenta standalone Kivy para validacao de coordenadas do mapa
│
├── desktop_app/                 # Legacy Kivy + KivyMD (Fase 0)
│   ├── __init__.py
│   ├── layout.kv                # Layout root KV (60 KB, 13 telas)
│   ├── theme.py                 # Constantes de paleta Kivy e cores de rating
│   ├── ghost_pixel.py           # Widget overlay de mira
│   ├── player_sidebar.py        # Barra lateral info jogador (Kivy)
│   ├── timeline.py              # Scrubber timeline de rounds (Kivy)
│   ├── widgets.py               # Widgets Kivy compartilhados (cards, botoes)
│   ├── wizard_screen.py         # Wizard de configuracao inicial
│   ├── help_screen.py           # Tela de ajuda / sobre
│   ├── match_history_screen.py  # Navegador de lista de partidas
│   ├── match_detail_screen.py   # Detalhamento de partida individual
│   ├── performance_screen.py    # Dashboard de estatisticas do jogador
│   ├── tactical_map.py          # Renderizador de mapa tatico 2D
│   ├── tactical_viewer_screen.py # Tela de analise tatica
│   ├── coaching_chat_vm.py      # ViewModel do chat de coaching
│   ├── tactical_viewmodels.py   # ViewModels de analise tatica
│   └── data_viewmodels.py       # ViewModels de busca de dados
│
└── qt_app/                      # Ativo PySide6 / Qt6 (Fase 2+)
    ├── __init__.py
    ├── app.py                   # Ponto de entrada da aplicacao
    ├── main_window.py           # QMainWindow com navegacao sidebar
    │
    ├── core/                    # Infraestrutura compartilhada
    │   ├── app_state.py         # Singleton AppState — poll de CoachState a cada 10s
    │   ├── worker.py            # Pattern Worker (QRunnable) em background
    │   ├── theme_engine.py      # Temas QSS (CS2, CSGO, CS1.6), paletas, fontes
    │   ├── design_tokens.py     # Definicoes de design tokens para o sistema de componentes Qt
    │   ├── qss_generator.py     # Geracao programatica de QSS a partir dos design tokens
    │   ├── animation.py         # Utilitarios de animacao compartilhados e helpers de easing
    │   ├── icons.py             # Registro de icones e carregador de assets SVG/icones
    │   ├── i18n_bridge.py       # Localizacao (en, pt, it) via JSON + fallback
    │   ├── asset_bridge.py      # Carregador de imagens de mapa (QPixmap), texturas fallback
    │   └── qt_playback_engine.py # Playback de demo baseado em QTimer (substitui Kivy Clock)
    │
    ├── screens/                 # Um QWidget por tela (camada View)
    │   ├── home_screen.py       # Dashboard — status do servico, contagem de partidas, training
    │   ├── coach_screen.py      # AI Coach — interface de chat, coaching insights
    │   ├── match_history_screen.py  # Lista de partidas com busca e filtros
    │   ├── match_detail_screen.py   # Analise de partida individual (rounds, economia, eventos)
    │   ├── performance_screen.py    # Estatisticas do jogador e tendencias
    │   ├── tactical_viewer_screen.py # Visualizador de mapa 2D com controles de playback
    │   ├── wizard_screen.py     # Configuracao inicial (caminho Steam, nome do jogador)
    │   ├── settings_screen.py   # Configuracoes do app (tema, fonte, idioma, caminhos)
    │   ├── user_profile_screen.py   # Editor de perfil do usuario
    │   ├── profile_screen.py    # Visao geral do perfil do jogador
    │   ├── steam_config_screen.py   # Configuracoes de integracao Steam
    │   ├── faceit_config_screen.py  # Configuracoes de integracao FACEIT
    │   ├── help_screen.py       # Visualizador de documentacao de ajuda
    │   └── placeholder.py       # Factory de placeholder para telas nao portadas
    │
    ├── viewmodels/              # Camada ViewModel (subclasses QObject)
    │   ├── coach_vm.py          # CoachViewModel — orquestra consultas de coaching
    │   ├── coaching_chat_vm.py  # Historico de chat e gerenciamento de mensagens
    │   ├── match_history_vm.py  # Busca de dados e filtragem da lista de partidas
    │   ├── match_detail_vm.py   # Carregamento de dados de partida individual
    │   ├── performance_vm.py    # Agregacao de estatisticas do jogador
    │   ├── tactical_vm.py       # Dados taticos e estado de playback
    │   └── user_profile_vm.py   # Operacoes CRUD do perfil do usuario
    │
    ├── widgets/                 # Biblioteca de widgets reutilizaveis
    │   ├── toast.py             # Overlay de notificacoes toast
    │   ├── skeleton.py          # Widgets placeholder de carregamento skeleton
    │   ├── charts/              # Visualizacoes baseadas em QtCharts
    │   │   ├── radar_chart.py       # Radar de habilidades (grafico spider 6 eixos)
    │   │   ├── economy_chart.py     # Grafico de economia round a round
    │   │   ├── momentum_chart.py    # Timeline de momentum da equipe
    │   │   ├── rating_sparkline.py  # Mini-grafico de rating inline
    │   │   ├── trend_chart.py       # Linhas de tendencia multi-partida
    │   │   └── utility_bar_chart.py # Grafico de barras de uso de utilitarios
    │   ├── components/          # Componentes de UI reutilizaveis (design system)
    │   │   ├── __init__.py          # Exports dos componentes
    │   │   ├── card.py              # Widget container de card
    │   │   ├── stat_badge.py        # Badge de estatistica com label e valor
    │   │   ├── empty_state.py       # Placeholder de estado vazio com icone e mensagem
    │   │   ├── section_header.py    # Cabecalho de secao com titulo e acao opcional
    │   │   ├── progress_ring.py     # Indicador de anel de progresso circular
    │   │   ├── icon_widget.py       # Widget de exibicao de icone (SVG/pixmap)
    │   │   └── nav_sidebar.py       # Componente de barra lateral de navegacao
    │   └── tactical/            # Componentes do visualizador tatico
    │       ├── map_widget.py        # Renderizador de mapa 2D (QGraphicsView)
    │       ├── player_sidebar.py    # Painel de info do jogador
    │       └── timeline_widget.py   # Scrubber de timeline de rounds
    │
    └── themes/                  # Folhas de estilo QSS
        ├── cs2.qss              # Tema CS2 (destaque laranja, superficie escura)
        ├── csgo.qss             # Tema CS:GO (destaque azul aco)
        └── cs16.qss             # Tema CS 1.6 (destaque verde, retro)
```

## Comparacao entre Frameworks

| Aspecto | `desktop_app/` (Kivy) | `qt_app/` (PySide6) |
|---------|----------------------|----------------------|
| **Status** | Legacy (Fase 0) — congelado | **Ativo** (Fase 2+) |
| **Layout** | Linguagem KV (`layout.kv`) | Codigo Python (QLayouts) |
| **Threading** | `threading.Thread` + `Clock.schedule_once` | `Worker` (QRunnable) + Signals |
| **Graficos** | matplotlib (pesado) | QtCharts (nativo, leve) |
| **Temas** | `theme.py` (propriedades Kivy) | `ThemeEngine` + folhas de estilo QSS |
| **i18n** | `LocalizationManager` (Kivy EventDispatcher) | `QtLocalizationManager` (QObject + Signal) |
| **Assets** | `AssetAuthority` (Kivy Texture) | `QtAssetBridge` (QPixmap) |
| **Playback** | `PlaybackEngine` + Kivy Clock | `QtPlaybackEngine` + QTimer |
| **Telas** | 13 (em `layout.kv`) | 14 (arquivos `.py` individuais) |
| **Arquivos Python** | 16 | 56 |

## Arquitetura MVVM

Ambas as UIs seguem o padrao **Model-View-ViewModel**. A implementacao Qt e a
referencia canonica:

```
┌─────────────────────────────────────────────────────────────────┐
│                        View (Screen)                            │
│  - Subclasse QWidget, puro layout e exibicao                    │
│  - Conecta-se aos sinais do ViewModel em on_enter()             │
│  - NUNCA importa modulos backend ou modelos de banco de dados   │
│  - Chama metodos do ViewModel para disparar operacoes de dados  │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Qt Signals (result, error, finished)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ViewModel (QObject)                          │
│  - Possui logica de negocio e estado para uma tela              │
│  - Inicia Worker (QRunnable) para consultas ao banco            │
│  - Emite Signals tipados com resultados (auto-marshal para UI)  │
│  - Pode ler sinais do AppState para dados backend em tempo real │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Worker (thread em background)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Model (SQLModel / DB)                         │
│  - backend/storage/database.py (singleton get_db_manager)       │
│  - backend/storage/db_models.py (classes ORM SQLModel)          │
│  - Somente leitura da perspectiva da UI                         │
└─────────────────────────────────────────────────────────────────┘
```

**Contrato chave:** as Views nunca chamam `get_db_manager()` e nao importam nada de
`backend/storage/`. Todos os dados fluem atraves dos ViewModels.

## Pontos de Entrada

### Primario (Qt)

```bash
# A partir da raiz do projeto, com venv ativado:
python -m Programma_CS2_RENAN.apps.qt_app.app
```

A sequencia de inicializacao em `app.py`:
1. Escala High-DPI configurada
2. `QApplication` criada, versao lida dos metadados do pacote
3. Handler de shutdown conectado (`aboutToQuit`)
4. `ThemeEngine` inicializado — fontes personalizadas registradas, tema aplicado
5. `MainWindow` criada com navegacao sidebar
6. Todas as 14 telas instanciadas e registradas no `QStackedWidget`
7. Gate de primeira execucao: mostra `WizardScreen` se setup nao completado, senao `HomeScreen`
8. Console backend inicializado (`get_console().boot()`)
9. Polling do `AppState` iniciado (intervalo de 10 segundos)

### Bundle PyInstaller

A aplicacao tambem pode ser iniciada a partir de um executavel construido com PyInstaller.
Consulte o diretorio `packaging/` para o arquivo `.spec` e instrucoes de build.

### Ferramentas Standalone

- **`spatial_debugger.py`** — Widget de debug baseado em Kivy para validar as
  transformacoes de coordenadas do mapa. Exibe uma imagem do mapa com overlays de
  pontos de referencia e leitura de coordenadas cursor-mundo. Util durante a
  calibracao dos dados espaciais.

## Padroes Compartilhados

### Padrao Worker (`core/worker.py`)

Todas as operacoes em background usam a classe `Worker`, que encapsula um callable
em um `QRunnable` e emite resultados via Signals:

```python
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from PySide6.QtCore import QThreadPool

worker = Worker(some_db_query, arg1, arg2)
worker.signals.result.connect(self._on_data_loaded)
worker.signals.error.connect(self._on_error)
QThreadPool.globalInstance().start(worker)
```

Isso substitui o padrao Kivy de `Thread(target=fn).start()` seguido por
`Clock.schedule_once(callback)`.

### AppState (`core/app_state.py`)

O singleton `AppState` consulta a linha do banco de dados `CoachState` a cada 10
segundos e emite sinais somente-em-mudanca. As telas se conectam a estes no seu
metodo `on_enter()`:

- `service_active_changed(bool)` — heartbeat do daemon backend
- `coach_status_changed(str)` — texto de status de ingestao/treinamento
- `parsing_progress_changed(float)` — progresso do parsing de demo (0.0-1.0)
- `belief_confidence_changed(float)` — nivel de confianca do modelo
- `total_matches_changed(int)` — total de partidas ingeridas
- `training_changed(dict)` — bundle de epoca, loss, ETA
- `notification_received(str, str)` — severidade + mensagem para exibicao de toast

### Temas (`core/theme_engine.py`)

Tres temas integrados refletem as eras da franquia Counter-Strike:

| Tema | Cor de Destaque | Superficie |
|------|----------------|------------|
| CS2 | Laranja (`#D96600`) | Carvao escuro |
| CSGO | Azul aco (`#617D8C`) | Cinza ardosia |
| CS 1.6 | Verde (`#4DB050`) | Oliva escuro |

Os temas sao aplicados via folhas de estilo QSS (`themes/*.qss`) mais uma `QPalette`
para widgets nao estilizados. Fontes personalizadas (Roboto, JetBrains Mono, CS Regular,
YUPIX, New Hope) sao registradas na inicializacao.

### Localizacao (`core/i18n_bridge.py`)

Tres idiomas sao suportados: Ingles, Portugues, Italiano. Ordem de resolucao de strings:
1. Arquivo de traducao JSON (`assets/i18n/{lang}.json`)
2. Dicionario de traducao hardcoded (idioma atual)
3. Fallback para ingles
4. Chave bruta (se nenhuma correspondencia)

Mudancas de idioma emitem um sinal `language_changed`. As telas implementam
`retranslate()` para atualizar seus labels dinamicamente.

## Diretrizes de Desenvolvimento

1. **Todo novo trabalho de UI vai em `qt_app/`** — nao adicione funcionalidades em `desktop_app/`
2. **Nenhum import Kivy no codigo Qt** — `asset_bridge.py`, `i18n_bridge.py`,
   `theme_engine.py` usam apenas Qt e stdlib. Imports cross-framework sao proibidos.
3. **Threading em background e obrigatorio** — nunca bloqueie a thread principal com
   consultas ao banco, chamadas de rede ou I/O de arquivo. Use `Worker` de `core/worker.py`.
4. **Conecte-se aos sinais do `AppState` em `on_enter()`** — este e o barramento de
   dados ao vivo do backend. Nao consulte o banco de dados a partir das telas.
5. **Graficos usam QtCharts** (nao matplotlib) — mais leves, integracao nativa Qt,
   temas consistentes via QSS.
6. **Localizacao** — todas as strings visiveis ao usuario devem passar por
   `i18n_bridge.get_text(key)`. Nunca insira texto de exibicao hardcoded no codigo
   das telas.
7. **Temas** — use `ThemeEngine.get_color(slot)` para cores e nunca use valores hex
   hardcoded. Todas as constantes visuais residem em `theme_engine.py` ou nos arquivos QSS.
8. **As telas nao importam umas as outras** — a navegacao e gerenciada por
   `MainWindow.switch_screen()`. A comunicacao entre telas acontece via sinais ou
   `AppState`.
9. **Toda tela deve implementar `on_enter()`** — chamado por `MainWindow` quando a
   tela se torna visivel. Use para atualizar dados e conectar sinais.
10. **Implemente `retranslate()`** — chamado quando o usuario troca de idioma.
    Atualize todos os labels visiveis ao usuario a partir de `i18n_bridge`.

## Notas de Desenvolvimento

- O app Qt requer **PySide6 >= 6.5** e **Python 3.10+**.
- As folhas de estilo QSS estao em `qt_app/themes/` — um arquivo por tema. Edite
  estes para mudancas visuais; nao insira estilos inline no codigo Python.
- A factory `placeholder.py` gera telas stub para paginas ainda nao portadas do Kivy.
  Estas exibem uma mensagem "Coming Soon" e sao progressivamente substituidas.
- `MainWindow` usa um `QStackedLayout` com tres camadas: papel de parede de fundo
  (inferior), pilha de telas (central) e notificacoes toast (superior).
- O console backend (`get_console().boot()`) pode falhar sem quebrar a UI. Uma
  caixa de dialogo de aviso e exibida e a aplicacao continua em modo degradado.
- `spatial_debugger.py` e o unico arquivo em `apps/` que importa Kivy diretamente.
  E uma ferramenta de debug standalone e nao e carregada pela aplicacao Qt.

## Contagem de Arquivos

- `desktop_app/`: 16 arquivos Python + 1 layout KV (legacy, congelado)
- `qt_app/`: 56 arquivos Python distribuidos em `core/`, `screens/`, `viewmodels/`, `widgets/` + 3 temas QSS
- Raiz `apps/`: 1 ferramenta standalone (`spatial_debugger.py`)
