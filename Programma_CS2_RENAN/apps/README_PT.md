> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Apps — Camada de Interface do Usuario

> **Autoridade:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Visao Geral

O diretório `apps/` contém todo o código de interface do usuário do Macena CS2 Analyzer.
O único framework de UI ativo é `qt_app/` — uma aplicação desktop de produção construída com
PySide6 (Qt6), escolhida pelo seu visual nativo, modelo de threading maduro (QThreadPool/QRunnable),
biblioteca de gráficos integrada (QtCharts) e amplo suporte multiplataforma.

`qt_app/` é uma camada estritamente consumidora: compartilha os mesmos serviços backend
(`backend/services/`), camada de banco de dados (`backend/storage/`) e sistema de configuração
(`core/config.py`), mas nunca escreve diretamente no banco de dados.

> **Nota histórica:** Um protótipo Kivy + KivyMD (`legacy_kivy/`) serviu como shell de
> desenvolvimento inicial. Foi substituído pelo frontend Qt e removido em março de 2026
> (commit `4f04f06`).

## Estrutura do Diretorio

```
apps/
├── __init__.py
├── README.md                    # Versao em ingles
├── README_IT.md                 # Traducao italiana
├── README_PT.md                 # Este arquivo
│
└── qt_app/                      # Ativo PySide6 / Qt6
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
    │   ├── animation.py         # Utilitários de animação compartilhados
    │   ├── easing.py            # Curvas de easing personalizadas
    │   ├── typography.py        # Escala tipográfica e helpers de fonte
    │   ├── icons.py             # Registro de ícones e carregador de assets SVG
    │   ├── svg_icon_provider.py # QIconEngine baseado em recursos SVG
    │   ├── i18n_bridge.py       # Localização (en, pt, it) via JSON + fallback
    │   ├── sound.py             # Helpers de reprodução de efeitos sonoros
    │   ├── match_utils.py       # Funções utilitárias de nível de partida para a camada UI
    │   ├── widgets_helpers.py   # Funções helper genéricas para widgets Qt
    │   ├── web_bridge.py        # Bridge Python↔JavaScript para as web views integradas
    │   └── qt_playback_engine.py # Playback de demo baseado em QTimer
    │
    ├── screens/                 # Um QWidget por tela (camada View) — 15 telas
    │   ├── home_screen.py           # Dashboard — status do serviço, contagem de partidas, training
    │   ├── coach_screen.py          # AI Coach — interface de chat, coaching insights
    │   ├── match_history_screen.py  # Lista de partidas com busca e filtros
    │   ├── match_detail_screen.py   # Análise de partida individual (rounds, economia, eventos)
    │   ├── performance_screen.py    # Estatísticas do jogador e tendências
    │   ├── tactical_viewer_screen.py # Visualizador de mapa 2D com controles de playback
    │   ├── pro_comparison_screen.py # Análise comparativa usuário vs jogador pro
    │   ├── pro_player_detail_screen.py # Vista de perfil do jogador pro
    │   ├── wizard_screen.py         # Configuração inicial (caminho Steam, nome do jogador)
    │   ├── settings_screen.py       # Configurações do app (tema, fonte, idioma, caminhos)
    │   ├── user_profile_screen.py   # Editor de perfil do usuário
    │   ├── profile_screen.py        # Visão geral do perfil do jogador
    │   ├── steam_config_screen.py   # Configurações de integração Steam
    │   ├── faceit_config_screen.py  # Configurações de integração FACEIT
    │   ├── help_screen.py           # Visualizador de documentação de ajuda
    │   └── placeholder.py           # Factory para telas stub
    │
    ├── viewmodels/              # Camada ViewModel (subclasses QObject)
    │   ├── coach_vm.py              # CoachViewModel — orquestra consultas de coaching
    │   ├── coaching_chat_vm.py      # Histórico de chat e gerenciamento de mensagens
    │   ├── focus_insight_vm.py      # ViewModel de detalhe de coaching insight focalizado
    │   ├── match_history_vm.py      # Busca de dados e filtragem da lista de partidas
    │   ├── match_detail_vm.py       # Carregamento de dados de partida individual
    │   ├── performance_vm.py        # Agregação de estatísticas do jogador
    │   ├── pro_comparison_vm.py     # Dados e pontuação de comparação pro
    │   ├── pro_player_detail_vm.py  # Carregamento de dados do perfil do jogador pro
    │   ├── tactical_vm.py           # Dados táticos e estado de playback
    │   └── user_profile_vm.py       # Operações CRUD do perfil do usuário
    │
    ├── widgets/                 # Biblioteca de widgets reutilizaveis
    │   ├── toast.py             # Overlay de notificacoes toast
    │   ├── skeleton.py          # Widgets placeholder de carregamento skeleton
    │   ├── charts/              # Visualizações QtCharts / QPainter
    │   │   ├── economy_chart.py     # Economia round a round (gráfico de barras QtCharts)
    │   │   ├── mini_sparkline.py    # Sparkline compacta (QPainter, sem eixos)
    │   │   └── momentum_chart.py    # Delta K-D momentum (gráfico de área QtCharts)
    │   ├── coaching/            # Namespace de widgets de coaching (reservado; widgets removidos PR #32)
    │   ├── components/          # Componentes de UI reutilizáveis (design system)
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
    ├── web/                     # Sub-apps TypeScript (integradas via QWebEngineView)
    │   ├── coach-chat/          # App React de chat de coaching
    │   ├── match-detail/        # App React de detalhe de partida
    │   ├── tactical-viewer/     # App React de visualizador tático
    │   └── shared/              # Utilitários TypeScript compartilhados
    │
    └── themes/                  # Folhas de estilo QSS
        ├── cs2.qss              # Tema CS2 (destaque laranja, superficie escura)
        ├── csgo.qss             # Tema CS:GO (destaque azul aco)
        └── cs16.qss             # Tema CS 1.6 (destaque verde, retro)
```

## Arquitetura MVVM

O app Qt segue o padrão **Model-View-ViewModel**:

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
6. Todas as 15 telas instanciadas e registradas no `QStackedWidget`
7. Gate de primeira execucao: mostra `WizardScreen` se setup nao completado, senao `HomeScreen`
8. Console backend inicializado (`get_console().boot()`)
9. Polling do `AppState` iniciado (intervalo de 10 segundos)

### Bundle PyInstaller

A aplicacao tambem pode ser iniciada a partir de um executavel construido com PyInstaller.
Consulte o diretorio `packaging/` para o arquivo `.spec` e instrucoes de build.

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

Este padrão garante que todo trabalho pesado seja executado fora da thread principal sem bloquear o loop de eventos Qt.

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

1. **Threading em background é obrigatório** — nunca bloqueie a thread principal com
   consultas ao banco, chamadas de rede ou I/O de arquivo. Use `Worker` de `core/worker.py`.
2. **Conecte-se aos sinais do `AppState` em `on_enter()`** — este é o barramento de
   dados ao vivo do backend. Não consulte o banco de dados a partir das telas.
3. **Gráficos usam QtCharts** (não matplotlib) — mais leves, integração nativa Qt,
   temas consistentes via QSS.
4. **Localização** — todas as strings visíveis ao usuário devem passar por
   `i18n_bridge.get_text(key)`. Nunca insira texto hardcoded no código das telas.
5. **Temas** — use `ThemeEngine.get_color(slot)` para cores e nunca use valores hex
   hardcoded. Todas as constantes visuais residem em `theme_engine.py` ou nos arquivos QSS.
6. **As telas não importam umas as outras** — a navegação é gerenciada por
   `MainWindow.switch_screen()`. A comunicação entre telas acontece via sinais ou
   `AppState`.
7. **Toda tela deve implementar `on_enter()`** — chamado por `MainWindow` quando a
   tela se torna visível. Use para atualizar dados e conectar sinais.
8. **Implemente `retranslate()`** — chamado quando o usuário troca de idioma.
   Atualize todos os labels visíveis ao usuário a partir de `i18n_bridge`.

## Notas de Desenvolvimento

- O app Qt requer **PySide6 >= 6.5** e **Python 3.10+**.
- As folhas de estilo QSS estao em `qt_app/themes/` — um arquivo por tema. Edite
  estes para mudancas visuais; nao insira estilos inline no codigo Python.
- A factory `placeholder.py` gera telas stub que exibem uma mensagem "Coming Soon" para telas em desenvolvimento.
- `MainWindow` usa um `QStackedLayout` com tres camadas: papel de parede de fundo
  (inferior), pilha de telas (central) e notificacoes toast (superior).
- O console backend (`get_console().boot()`) pode falhar sem quebrar a UI. Uma
  caixa de dialogo de aviso e exibida e a aplicacao continua em modo degradado.

## Contagem de Arquivos

- `qt_app/`: 78 arquivos Python em `core/`, `screens/`, `viewmodels/`, `widgets/` + 3 temas QSS + 3 sub-apps web integradas
