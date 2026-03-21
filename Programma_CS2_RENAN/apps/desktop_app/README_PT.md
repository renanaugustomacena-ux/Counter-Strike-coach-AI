# Aplicacao Desktop (Legacy Kivy/KivyMD)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Dominio:** Desktop UI / Frontend Kivy
> **Nivel:** Intermediario -- requer familiaridade com o ciclo de vida dos widgets Kivy, componentes Material do KivyMD e o padrao MVVM.

> **Nota:** Este e o frontend **legacy** Kivy/KivyMD. Ainda esta funcional e mantido como fallback. O frontend primario e PySide6/Qt -- veja [`qt_app/`](../qt_app/).

---

## Visao Geral

Aplicacao desktop Kivy/KivyMD implementando a arquitetura **Model-View-ViewModel (MVVM)** para analise tatica de CS2 e coaching de IA. O modulo fornece 6 telas dedicadas (definidas neste diretorio) alem de 7 telas adicionais definidas no ponto de entrada da aplicacao principal. Todo o layout visual e declarado em um unico arquivo `layout.kv` (~60 KB, 1621 linhas) utilizando a biblioteca de componentes Material Design do KivyMD.

A aplicacao renderiza replays de partidas em um mapa tatico 2D pixel-accurate, exibe o estado dos jogadores em tempo real nas sidebars, gera graficos de economia e momentum via graficos Matplotlib incorporados, e fornece uma interface de chat de coaching de IA sustentada pelo motor de coaching COPER.

---

## Inventario de Arquivos

| Arquivo | Linhas | Proposito |
|---------|--------|-----------|
| `__init__.py` | 1 | Marcador de pacote (vazio). |
| `wizard_screen.py` | 418 | Assistente de configuracao inicial -- caminho Steam, brain data root, pasta de demos. |
| `tactical_viewer_screen.py` | 295 | Replay de mapa 2D com controles de reproducao, ghost AI, navegacao chronovisor. |
| `match_history_screen.py` | 162 | Lista de partidas rolavel com rating HLTV 2.0 codificado por cor. |
| `match_detail_screen.py` | 454 | Analise detalhada de uma unica partida: visao geral, rounds, grafico de economia, destaques. |
| `performance_screen.py` | 331 | Dashboard agregado: tendencia de rating, estatisticas por mapa, forcas/fraquezas, utility. |
| `help_screen.py` | 80 | Central de ajuda com busca, suportada pelo modulo opcional `help_system`. |
| `widgets.py` | 275 | 7 widgets graficos baseados em Matplotlib (tendencia, radar, economia, momentum, sparkline, utility, base). |
| `tactical_map.py` | 607 | O widget "Living Map" -- rendering otimizado por GPU com InstructionGroup para jogadores, granadas, heatmaps. |
| `player_sidebar.py` | 362 | LivePlayerCard + PlayerSidebar com pooling de widgets para estado do jogador em tempo real. |
| `timeline.py` | 129 | TimelineScrubber interativo com marcadores de eventos (kills, plants, defuses). |
| `ghost_pixel.py` | 140 | Overlay de debug GhostPixelValidator para calibracao de coordenadas. |
| `tactical_viewmodels.py` | 345 | 3 ViewModels: TacticalPlaybackViewModel, TacticalGhostViewModel, TacticalChronovisorViewModel. |
| `coaching_chat_vm.py` | 140 | CoachingChatViewModel -- gerenciamento de sessao de dialogo de IA com thread safety. |
| `data_viewmodels.py` | 316 | 3 ViewModels: MatchHistoryViewModel, MatchDetailViewModel, PerformanceViewModel. |
| `theme.py` | 74 | Constantes de cor compartilhadas, registro de paletas (CS2/CSGO/CS1.6), helpers de rating. |
| `layout.kv` | 1621 | Definicoes de layout KivyMD para todas as telas (~60 KB). Componentes Material Design. |

**Total: 16 arquivos Python + 1 arquivo de layout KV.**

---

## Telas (6 neste diretorio)

### 1. WizardScreen (`wizard_screen.py`)
Assistente de configuracao inicial com fluxo de 4 etapas: `intro` -> `brain_path` -> `demo_path` -> `finish`. Utiliza `MDFileManager` para selecao de pastas com suporte a multiplos discos no Windows. Valida caminhos, cria a estrutura de subdiretorios `knowledge/`, `models/`, `datasets/` sob `BRAIN_DATA_ROOT`, e persiste configuracoes via `save_user_setting()`. Inclui normalizacao de caminho contra traversal (WZ-01) e logica de fallback para permissao negada.

### 2. TacticalViewerScreen (`tactical_viewer_screen.py`)
Tela central de replay que coordena tres ViewModels. Carrega dados de demo analisados no `PlaybackEngine`, renderiza frames no `TacticalMap`, e atualiza os widgets `PlayerSidebar` por equipe. Suporta play/pause, velocidade variavel, seek por tick, salto entre segmentos de round, overlay ghost AI, e navegacao de momentos criticos do chronovisor. O timer de UI dos ticks funciona apenas enquanto a tela esta ativa (iniciado no `on_enter`, cancelado no `on_leave`).

### 3. MatchHistoryScreen (`match_history_screen.py`)
Exibe a lista de partidas do usuario ordenada por data. Cada card de partida mostra o rating HLTV 2.0 com codificacao por cor e etiquetas de texto para acessibilidade (P4-07), nome do mapa extraido via regex, razao K/D, ADR, kills e mortes. Tocar em um card navega para `MatchDetailScreen`. O carregamento de dados e delegado ao `MatchHistoryViewModel`.

### 4. MatchDetailScreen (`match_detail_screen.py`)
Analise detalhada em 4 secoes para uma unica partida:
- **Visao Geral:** Rating HLTV 2.0 com barras de decomposicao dos componentes (KPR, DPR, impacto, etc.)
- **Timeline de Rounds:** Estatisticas por round com cor por lado (CT azul / T dourado), vitoria/derrota, K/D, dano, economia, opening kill
- **Economia:** Grafico de barras `EconomyGraphWidget` do valor de equipamento por round
- **Destaques e Momentum:** Insights de coaching com icones de severidade + grafico `MomentumGraphWidget` do delta K-D acumulado

### 5. PerformanceScreen (`performance_screen.py`)
Dashboard agregado em 4 paineis:
- **Tendencia de Rating:** `RatingSparklineWidget` com linhas de referencia em 1.0, 1.1, 0.9
- **Estatisticas por Mapa:** Scroll horizontal de cards de mapa com rating, ADR, K/D, quantidade de partidas
- **Forcas/Fraquezas:** Comparacao Z-score contra baseline profissional (colunas verde/vermelho)
- **Eficacia de Utility:** `UtilityBarWidget` barras horizontais agrupadas (usuario vs media pro)

### 6. HelpScreen (`help_screen.py`)
Lista de topicos na sidebar com painel de conteudo. Utiliza o modulo opcional `help_system` (degradacao graciosa via try/except). Suporta filtragem por busca de topicos. Carrega o primeiro topico por padrao ao entrar.

### Telas Adicionais (definidas em `main.py`)
HomeScreen, CoachScreen, UserProfileScreen, SettingsScreen, ProfileScreen, SteamConfigScreen, FaceitConfigScreen.

---

## Widgets Personalizados

### Widgets Graficos (`widgets.py`)

Todos os widgets graficos estendem `MatplotlibWidget`, que renderiza figuras Matplotlib em texturas Kivy via um buffer PNG em memoria. As figuras sao fechadas imediatamente apos o rendering (WG-01) para prevenir vazamento de memoria.

| Widget | Tipo | Descricao |
|--------|------|-----------|
| `MatplotlibWidget` | Base | Conversao buffer-to-texture com context manager `BytesIO` (WG-02). |
| `TrendGraphWidget` | Linha | Grafico de eixo duplo: Rating (esquerdo, ciano) e ADR (direito, ambar). Ultimas 20 partidas. |
| `RadarChartWidget` | Polar | Grafico radar/spider para atributos de habilidade. Requer minimo de 3 pontos de dados (F7-36). |
| `EconomyGraphWidget` | Barras | Valor de equipamento por round. Barras CT em azul (#5C9EE8), barras T em dourado (#E8C95C). |
| `MomentumGraphWidget` | Linha+Preenchimento | Delta kill-death acumulado. Preenchimento verde acima do zero, vermelho abaixo. |
| `RatingSparklineWidget` | Linha+Preenchimento | Progressao de rating com linhas de referencia em 1.0 (neutro), 1.1 (bom), 0.9 (ruim). |
| `UtilityBarWidget` | Barras Horizontais | Barras horizontais agrupadas comparando estatisticas de utility do usuario vs media profissional. |

### Widgets Taticos

| Widget | Arquivo | Descricao |
|--------|---------|-----------|
| `TacticalMap` | `tactical_map.py` | Mapa 2D otimizado por GPU com 3 camadas InstructionGroup (mapa estatico, heatmap, jogadores/granadas dinamicos). Suporta carregamento assincrono do mapa, cache LRU para texturas de nomes (64 entradas), rendering de trajetorias de granadas com visualizacao de altura 3D, overlays de raio de detonacao (HE/Molotov/Smoke/Flash), cones de FoV dos jogadores, highlight de selecao, e click-to-select com hitboxes ampliadas. |
| `LivePlayerCard` | `player_sidebar.py` | Card de estatisticas em tempo real: barras de progresso HP/armadura, economia, KDA, arma. Estado de morte diminui a opacidade. |
| `PlayerSidebar` | `player_sidebar.py` | Lista de jogadores rolavel com pooling de widgets (reuso de objetos ao inves de criar/destruir a cada frame). Inclui `LivePlayerCard` para detalhe do jogador selecionado. |
| `TimelineScrubber` | `timeline.py` | Barra de progresso interativa com marcadores de eventos codificados por cor. Marcadores de kill na metade da altura (vermelho), plant (amarelo) e defuse (azul) em altura total. Suporta seek por click e arraste. |
| `GhostPixelValidator` | `ghost_pixel.py` | Overlay de debug mostrando coordenadas normalizadas e mundiais no ponto de toque. Renderiza pontos de referencia de landmarks e uma mira magenta. Ativo apenas quando `debug_mode=True`. |

---

## Arquitetura MVVM

### ViewModels

A aplicacao segue o padrao **Model-View-ViewModel**. As Views (classes Screen + `layout.kv`) lidam com rendering e interacao do usuario. Os ViewModels possuem a logica de negocio e o carregamento de dados. Todos os ViewModels estendem o `EventDispatcher` do Kivy com propriedades observaveis, usam daemon threads para I/O, e retornam resultados ao thread de UI via `Clock.schedule_once`.

| ViewModel | Arquivo | Responsabilidade |
|-----------|---------|------------------|
| `TacticalPlaybackViewModel` | `tactical_viewmodels.py` | Play/pause, velocidade, seeking, rastreamento de tick via `PlaybackEngine`. |
| `TacticalGhostViewModel` | `tactical_viewmodels.py` | `GhostEngine` carregado lazy para predicoes de posicao por IA. |
| `TacticalChronovisorViewModel` | `tactical_viewmodels.py` | Varredura em background para momentos criticos, navegacao proximo/anterior com buffer de tick. |
| `CoachingChatViewModel` | `coaching_chat_vm.py` | Sessao de dialogo de IA: verificacao de disponibilidade, inicio de sessao, envio/recebimento de mensagens. Lista de mensagens thread-safe (F7-24). |
| `MatchHistoryViewModel` | `data_viewmodels.py` | Carregamento em background da lista de partidas da tabela `PlayerMatchStats`. Suporte a cancelamento (DV-01). |
| `MatchDetailViewModel` | `data_viewmodels.py` | Carregamento em background de estatisticas da partida, rounds, insights de coaching, decomposicao HLTV 2.0. |
| `PerformanceViewModel` | `data_viewmodels.py` | Carregamento em background de historico de rating, estatisticas por mapa, forcas/fraquezas, dados de utility. |

---

## Ponto de Entrada

Este modulo **nao** e autonomo. O ponto de entrada da aplicacao e `main.py` na raiz do projeto, que:
1. Cria a subclasse `MDApp`
2. Carrega `layout.kv` via `Builder.load_file()`
3. Registra todas as telas com o `ScreenManager`
4. Inicia o loop de eventos do Kivy

As telas neste diretorio sao importadas pelo `main.py` e registradas pelo decorador `@registry.register()`.

---

## Arquivo de Layout (`layout.kv`)

O arquivo `layout.kv` (1621 linhas, ~60 KB) define a interface declarativa para todas as telas usando os componentes Material Design do KivyMD. Inclui:

- Layouts de tela com `MDNavigationLayout`, `MDTopAppBar`, `MDNavigationDrawer`
- Arvores de widgets para cada tela com referencias `id` usadas pelo codigo Python
- Regras de estilo para cards, labels, botoes e widgets personalizados
- Dimensionamento responsivo com unidades `dp()` e `sp()`
- Bindings de tema para o registro de paletas em `theme.py`

Todas as referencias `self.ids.<widget_id>` no codigo Python correspondem as declaracoes `id: <widget_id>` neste arquivo.

---

## Sistema de Temas (`theme.py`)

Fornece uma paleta de cores compartilhada com tres temas selecionaveis:

| Tema | Cor de Superficie | Destaque | Fundo dos Graficos |
|------|-------------------|----------|---------------------|
| **CS2** (padrao) | Preto-roxo escuro | Laranja | `#1a1a1a` |
| **CSGO** | Cinza escuro | Azul-acinzentado | `#1c1e20` |
| **CS1.6** | Verde escuro | Verde | `#181e18` |

A codificacao de cor do rating segue os limites padrao HLTV: verde (>1.10), amarelo (0.90-1.10), vermelho (<0.90). As etiquetas de texto ("Excellent", "Good", "Average", "Below Avg") garantem acessibilidade WCAG 1.4.1 para daltonismo (P4-07).

---

## Notas de Desenvolvimento

### Status Legacy
Este frontend e a interface **original** construida durante o desenvolvimento inicial. Permanece funcional e e mantido como fallback, mas **todo o desenvolvimento de novas funcionalidades e direcionado ao frontend PySide6/Qt** em `qt_app/`. Correcoes de bugs e patches criticos ainda sao aplicados aqui.

### Decisoes de Design Chave
- **Camadas InstructionGroup** no `TacticalMap` evitam recarregar a textura do mapa na GPU a cada frame. Camadas estaticas sao redesenhadas apenas no redimensionamento ou troca de mapa.
- **Pooling de widgets** no `PlayerSidebar` reutiliza widgets `MDListItem` ao inves de cria-los/destrui-los a cada frame, reduzindo a pressao no GC.
- **Imports lazy** para dependencias pesadas (`torch`, `GhostEngine`, `ChronovisorScanner`) previnem travamentos na inicializacao.
- **Thread safety** garantida via `threading.Lock` nas listas de mensagens compartilhadas e `threading.Event` para cancelamento.

### Limitacoes Conhecidas
- `HelpScreen` depende de um modulo opcional `help_system` que pode ainda nao estar implementado (F7-09)
- `GhostEngine` requer um checkpoint de modelo treinado para funcionar
- Os graficos Matplotlib sao renderizados como texturas PNG estaticas (sem interatividade)
- O arquivo `layout.kv` e grande e monolitico; sua divisao e um objetivo de refatoracao futuro
