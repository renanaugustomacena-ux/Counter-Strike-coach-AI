> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Apps — Camada de Interface do Usuario

> **Autoridade:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Visao Geral

O diretorio `apps/` contem todo o codigo de interface do usuario do Macena CS2 Analyzer.
O unico framework de UI ativo e `qt_app/` — uma aplicacao desktop de producao construida com
PySide6 (Qt6). Foi escolhida pelo seu visual nativo, modelo de threading maduro (QThreadPool/QRunnable),
painting poderoso de widgets customizados (QPainter) e amplo suporte multiplataforma.

`qt_app/` e uma camada estritamente consumidora: compartilha os mesmos servicos backend
(`backend/services/`), camada de banco de dados (`backend/storage/`) e sistema de configuracao
(`core/config.py`), e limita suas escritas no banco de dados a registros do usuario (perfil,
configuracoes, flags de leitura de notificacoes).

> **Nota historica:** Um prototipo Kivy + KivyMD (`legacy_kivy/`) serviu como shell de
> desenvolvimento inicial. Foi substituido pelo frontend Qt e removido em junho de 2026
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
    │   ├── theme_engine.py      # Tematizacao guiada por tokens (CS2, CSGO, CS1.6): render QSS, QPalette, fontes, wallpapers
    │   ├── design_tokens.py     # Definicoes de design tokens para o sistema de componentes Qt
    │   ├── qss_generator.py     # Renderiza themes/base.qss.template com substituicao de tokens
    │   ├── animation.py         # Utilitarios de animacao compartilhados
    │   ├── easing.py            # Curvas de easing personalizadas
    │   ├── typography.py        # Escala tipografica e helpers de fonte
    │   ├── icons.py             # Fachada IconProvider — SVG sprite, fallback QPainterPath
    │   ├── svg_icon_provider.py # QIconEngine baseado em recursos SVG
    │   ├── i18n_bridge.py       # Localizacao (en, pt, it) via JSON + fallback
    │   ├── sound.py             # Helpers de reproducao de efeitos sonoros
    │   ├── match_utils.py       # Funcoes utilitarias a nivel de partida para a camada UI
    │   ├── widgets_helpers.py   # Funcoes helper genericas para widgets Qt
    │   ├── web_bridge.py        # Bridge Python↔JavaScript para as web views integradas
    │   ├── qt_playback_engine.py # Playback de demo baseado em QTimer
    │   └── tray.py              # Icone na bandeja do sistema + menu (fechar-para-bandeja, atalho AI Coach)
    │
    ├── screens/                 # Um QWidget por tela (camada View) — 15 telas
    │   ├── home_screen.py           # Dashboard — status do servico, contagem de partidas, training
    │   ├── coach_screen.py          # AI Coach — interface de chat, coaching insights
    │   ├── match_history_screen.py  # Lista de partidas com busca e filtros
    │   ├── match_detail_screen.py   # Analise de partida individual (rounds, economia, eventos)
    │   ├── performance_screen.py    # Estatisticas do jogador e tendencias
    │   ├── tactical_viewer_screen.py # Visualizador de mapa 2D com controles de playback
    │   ├── pro_comparison_screen.py # Analise comparativa usuario vs jogador pro
    │   ├── pro_player_detail_screen.py # Vista de perfil do jogador pro
    │   ├── wizard_screen.py         # Configuracao inicial (caminho Steam, nome do jogador)
    │   ├── settings_screen.py       # Configuracoes do app (tema, fonte, idioma, caminhos)
    │   ├── user_profile_screen.py   # Editor de perfil do usuario
    │   ├── profile_screen.py        # Visao geral do perfil do jogador
    │   ├── steam_config_screen.py   # Configuracoes de integracao Steam
    │   ├── faceit_config_screen.py  # Configuracoes de integracao FACEIT
    │   ├── help_screen.py           # Visualizador de documentacao de ajuda
    │   └── placeholder.py           # Factory de placeholder (todas as entradas substituidas por telas reais)
    │
    ├── viewmodels/              # Camada ViewModel (subclasses QObject)
    │   ├── coach_vm.py              # CoachViewModel — orquestra consultas de coaching
    │   ├── coaching_chat_vm.py      # Historico de chat e gerenciamento de mensagens
    │   ├── focus_insight_vm.py      # ViewModel de detalhe de coaching insight focalizado
    │   ├── match_history_vm.py      # Busca de dados e filtragem da lista de partidas
    │   ├── match_detail_vm.py       # Carregamento de dados de partida individual
    │   ├── performance_vm.py        # Agregacao de estatisticas do jogador
    │   ├── pro_comparison_vm.py     # Dados e pontuacao de comparacao pro
    │   ├── pro_player_detail_vm.py  # Carregamento de dados do perfil do jogador pro
    │   ├── tactical_vm.py           # Dados taticos e estado de playback
    │   └── user_profile_vm.py       # Operacoes CRUD do perfil do usuario
    │
    ├── widgets/                 # Biblioteca de widgets reutilizaveis
    │   ├── toast.py             # Overlay de notificacoes toast
    │   ├── skeleton.py          # Widgets placeholder de carregamento skeleton
    │   ├── charts/              # Visualizacoes QPainter (QtCharts removido — somente GPL)
    │   │   ├── economy_chart.py     # Barras de economia round a round (QPainter)
    │   │   ├── mini_sparkline.py    # Sparkline compacta (QPainter, sem eixos)
    │   │   ├── momentum_chart.py    # Grafico de area delta K-D momentum (QPainter)
    │   │   ├── radar_chart.py       # Radar de N eixos de skills (QPainter)
    │   │   ├── rating_sparkline.py  # Tendencia de rating com baseline (QPainter)
    │   │   └── utility_bar_chart.py # Barras de uso de utilitarios (QPainter)
    │   ├── coaching/            # Widgets de coaching (ChatPanel integrado na CoachScreen)
    │   ├── components/          # Componentes de UI reutilizaveis (design system) — 26 modulos
    │   │   ├── __init__.py          # Exports dos componentes
    │   │   ├── card.py              # Widget container de card (5 variantes de profundidade)
    │   │   ├── db_record_card.py    # Eco mono de linha do DB (tabela · coluna · valor)
    │   │   ├── delta_chip.py        # Pilula de delta relativa ao benchmark
    │   │   ├── drivers_list.py      # Linhas de contribuicao com sinal (o que moveu uma estatistica)
    │   │   ├── empty_state.py       # Placeholder de estado vazio com icone e mensagem
    │   │   ├── filter_chip.py       # Pilula de filtro alternavel
    │   │   ├── focus_insight.py     # Card de foco de insight (tela home)
    │   │   ├── hero_stats_strip.py  # Faixa horizontal de metricas hero
    │   │   ├── icon_widget.py       # Widget de exibicao de icone (SVG/pixmap)
    │   │   ├── last_match_hero.py   # Card hero da ultima partida (tela home)
    │   │   ├── map_tile.py          # Tile de estatisticas por mapa com destaque de win-rate
    │   │   ├── match_mini_card.py   # Card compacto de resumo de partida
    │   │   ├── match_row_card.py    # Card de linha de partida expandido
    │   │   ├── metric_bar_row.py    # Label + barra de metrica horizontal + valor
    │   │   ├── mini_link_card.py    # Pequeno card de navegacao de links relacionados
    │   │   ├── mono_footer.py       # Linha de rodape mono de proveniencia/status
    │   │   ├── nav_sidebar.py       # Componente de barra lateral de navegacao recolhivel
    │   │   ├── numbered_step.py     # Linha de passo 01/02/03 em mono acentuado
    │   │   ├── pro_badge.py         # Pilula PRO/tier para superficies de jogadores pro
    │   │   ├── progress_ring.py     # Indicador de anel de progresso circular
    │   │   ├── section_header.py    # Cabecalho de secao com titulo e acao opcional
    │   │   ├── stat_badge.py        # Badge de estatistica com label e valor
    │   │   ├── status_chip.py       # Pilula de status colorida com label de texto
    │   │   ├── stepper.py           # Indicador de progresso em passos
    │   │   ├── tip_box.py           # Caixa de dica com borda em destaque
    │   │   └── toggle_switch.py     # Interruptor booleano animado
    │   └── tactical/            # Componentes do visualizador tatico
    │       ├── _paint_utils.py      # Helpers QPainter compartilhados (mapa + timeline)
    │       ├── map_widget.py        # Renderizador de mapa 2D (QPainter, TacticalMapWidget)
    │       ├── player_sidebar.py    # Painel de info do jogador
    │       └── timeline_widget.py   # Scrubber de timeline de rounds
    │
    ├── web/                     # Sub-apps TypeScript (integradas via QWebEngineView)
    │   ├── coach-chat/          # App React de chat de coaching
    │   ├── match-detail/        # App React de detalhe de partida
    │   ├── tactical-viewer/     # App React de visualizador tatico
    │   └── shared/              # Utilitarios TypeScript compartilhados
    │
    └── themes/                  # Fonte QSS
        └── base.qss.template    # Folha de estilo com substituicao de tokens — unica fonte QSS
                                 # (renderizada por tema por core/qss_generator.py)
```

## Arquitetura MVVM

O app Qt segue o padrao **Model-View-ViewModel**:

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

# Ou via o script de lancamento na raiz do repositorio (usa .venv, limpa bytecode obsoleto):
./launch.sh
```

A sequencia de inicializacao em `app.py` (`main(argv)`):

1. Despacho dos argumentos antes de qualquer trabalho Qt: `--daemon` executa o Session Engine neste processo (e assim que a GUI o lanca — `python -m Programma_CS2_RENAN.core.session_engine` a partir do codigo-fonte, `<exe> --daemon` no build congelado), `--selftest` executa a sonda de runtime sem GUI (`core/selftest.py`, relatorio JSON, codigo de saida); `core/frozen_hook` e importado aqui (suporte a freeze do multiprocessing)
2. Escala High-DPI configurada, `QApplication` criada, versao lida dos metadados do pacote
3. Guarda de instancia unica (`lifecycle.ensure_single_instance()`) — um segundo lancamento pede a instancia em execucao que traga sua janela para frente por um socket local (`core/instance_guard.py`) e encerra em silencio; o dialogo de aviso fica apenas como recurso quando ninguem responde
4. `ThemeEngine` criado e fontes customizadas registradas; handler de encerramento controlado conectado (`aboutToQuit`); com o setup ja concluido o esquema do banco e inicializado (`init_database`) para que nenhuma tela consulte uma tabela inexistente
5. `_boot_ui`: a tela de splash tematizada fica visivel APENAS enquanto a UI e composta — tema aplicado, `MainWindow` criada, todas as 15 telas instanciadas e registradas no `QStackedWidget`, signals entre telas conectados (selecao de partida → detalhe, momentos de destaque → visualizador tatico, comparacao pro → detalhe pro), gate de primeiro uso (`WizardScreen` se o setup nao foi concluido, senao `HomeScreen`), janela exibida. O splash e fechado em um `finally`, portanto nenhum erro de inicializacao pode deixa-lo na tela; uma linha INFO por fase ("boot phase …") registra a cronologia
6. A guarda de instancia comeca a escutar; bandeja do sistema construida (`build_tray`); se uma bandeja esta disponivel, `setQuitOnLastWindowClosed(False)` habilita o comportamento de fechar-para-bandeja
7. Inicializacao do backend no thread pool DEPOIS que a janela esta visivel: `get_console().boot()` + daemon do Session Engine (`lifecycle.launch_daemon()`, lancado com console oculto), depois verificacao/download do modelo de linguagem SBERT em segundo plano (toasts, nunca bloqueante). No primeiro uso este passo inteiro aguarda o `setup_completed` do wizard e entao chega a `HomeScreen`
8. Polling do `AppState` iniciado (intervalo de 10 segundos)

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

Este padrao garante que todo trabalho pesado seja executado fora da thread principal sem bloquear o loop de eventos Qt.

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
| CS2 | Laranja tatico (`#FF6A00`) | Azul-marinho escuro (`#0B1628`) |
| CSGO | Azul aco (`#617D8C`) | Ardosia escuro (`#1A1C21`) |
| CS 1.6 | Verde (`#4DB04F`) | Verde escuro (`#121A12`) |

Tanto o QSS (renderizado a partir de `themes/base.qss.template` por `core/qss_generator.py`)
quanto a `QPalette` para widgets nao estilizados derivam dos mesmos design tokens por tema
(`core/design_tokens.py`, gerados a partir de `design/tokens/design-tokens.json`).
Fontes customizadas (Roboto, JetBrains Mono, CS Regular, YUPIX, New Hope) sao registradas
na inicializacao, mais um stack de fontes de display auto-escaneado de `assets/fonts/` (Space Grotesk, Inter).

### Localizacao (`core/i18n_bridge.py`)

Tres idiomas sao suportados: Ingles, Portugues, Italiano. Ordem de resolucao de strings:
1. Arquivo de traducao JSON (`assets/i18n/{lang}.json`)
2. Dicionario de traducao hardcoded (idioma atual)
3. Fallback para ingles
4. Default fornecido pelo chamador (se informado)
5. Chave bruta (se nenhuma correspondencia)

Mudancas de idioma emitem um sinal `language_changed`. As telas implementam
`retranslate()` para atualizar seus labels dinamicamente.

## Diretrizes de Desenvolvimento

1. **Threading em background e obrigatorio** — nunca bloqueie a thread principal com
   consultas ao banco, chamadas de rede ou I/O de arquivo. Use `Worker` de `core/worker.py`.
2. **Conecte-se aos sinais do `AppState` em `on_enter()`** — este e o barramento de
   dados ao vivo do backend. Nao consulte o banco de dados a partir das telas.
3. **Graficos sao widgets QPainter customizados** (nao matplotlib, e nao QtCharts — este
   ultimo e somente GPL e foi removido por conformidade de licenca) — leves, tematizados
   via tokens, protegidos por um teste de guarda de licenca em `tests/test_charts.py`.
4. **Localizacao** — todas as strings visiveis ao usuario devem passar por
   `i18n_bridge.get_text(key)`. Nunca insira texto hardcoded no codigo das telas.
5. **Temas** — use os campos de `design_tokens.get_tokens()` para cores e nunca use
   valores hex hardcoded. Os tokens sao gerados de `design/tokens/design-tokens.json`;
   o template QSS e a QPalette derivam da mesma instancia `DesignTokens`.
6. **As telas nao importam umas as outras** — a navegacao e gerenciada por
   `MainWindow.switch_screen()`. A comunicacao entre telas acontece via sinais ou
   `AppState`.
7. **Toda tela deve implementar `on_enter()`** — chamado por `MainWindow` quando a
   tela se torna visivel. Use para atualizar dados e conectar sinais.
8. **Implemente `retranslate()`** — chamado quando o usuario troca de idioma.
   Atualize todos os labels visiveis ao usuario a partir de `i18n_bridge`.

## Notas de Desenvolvimento

- O app Qt requer **PySide6 6.11.0** (fixado em `requirements.txt`) e **Python 3.11+**.
- A unica fonte QSS e `qt_app/themes/base.qss.template`; os arquivos `.qss` legados
  por tema foram removidos (commits `73ec5ed`, `5ce891b`). Mudancas visuais passam pelos
  design tokens e pelo template; nao insira estilos inline no codigo Python.
- A factory `placeholder.py` cria telas placeholder simples com nome (titulo centralizado + descricao). No boot, todas as entradas de placeholder sao substituidas por implementacoes reais de telas; a factory permanece como rede de seguranca de registro.
- `MainWindow` organiza a area de conteudo com um `QStackedLayout` (modo `StackAll`):
  fundo (wallpaper opcional a 15% de opacidade mais um motivo sutil de grade tatica)
  sob a pilha de telas transparentes. Notificacoes toast flutuam como um overlay filho
  separado no canto superior direito, fora do stacked layout.
- O console backend (`get_console().boot()`) pode falhar sem quebrar a UI. Uma caixa de
  dialogo de aviso e exibida e a aplicacao continua em modo degradado.

## Contagem de Arquivos

- `qt_app/`: 93 arquivos Python (`app.py`, `main_window.py`, `core/`, `screens/`, `viewmodels/`, `widgets/`) + 1 template QSS (`themes/base.qss.template`) + 3 sub-apps web integradas
