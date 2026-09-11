# `apps/qt_app/screens/` — Modulos de tela da UI Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Este pacote contem todas as telas top-level do frontend Qt. Cada modulo define uma subclasse de `QWidget` que detem o layout, o wiring de signals e os hooks de ciclo de vida por tela para uma rota no grafo de navegacao da aplicacao. ViewModels (em `apps/qt_app/viewmodels/`) detem os dados e a logica de negocio; telas detem a composicao visual.

## Inventario de arquivos

| Arquivo | Tela | Finalidade |
|---------|------|------------|
| `__init__.py` | — | Marcador de pacote. |
| `home_screen.py` | Home | Pagina inicial: par hero ultima partida + foco semanal, faixa de partidas recentes, launchers de analise de demo / ingestao pro, hub de navegacao. |
| `coach_screen.py` | Coach | Dashboard RAP Coach: anel de confianca de belief-state, linhas de insight recentes, mais um dock `ChatPanel` embutido (alternado pelo botao Chat) suportado por `CoachingDialogueEngine` (via `CoachingChatViewModel`). |
| `match_history_screen.py` | Match History | Lista agrupada (Hoje / Esta Semana / Anteriores) de demos analisadas com filtros de fonte (Todos / Pessoal / Pro) e mapa; rating por partida em relacao ao baseline pessoal. |
| `match_detail_screen.py` | Match Detail | Drilldown por partida em abas: visao geral, rounds, economia, highlights (momentum + coaching insights). |
| `performance_screen.py` | Performance | Dashboard agregado: tendencia de rating, stats por mapa, forcas / fraquezas, breakdown de utility. |
| `pro_comparison_screen.py` | Pro Comparison | Comparacao Pro vs Pro ou Eu vs Pro: radar de habilidades + metricas head-to-head; Eu vs Pro e bloqueado ate que partidas pessoais suficientes sejam analisadas. |
| `pro_player_detail_screen.py` | Pro Player Detail | Perfil do pro com card de stat HLTV, partidas recentes, classificacao de role. |
| `tactical_viewer_screen.py` | Tactical Viewer | Replay 2D do mapa com controles de playback, overlay de ghost AI, highlights de chronovisor. |
| `profile_screen.py` | Profile | Editor do nome in-game do jogador; persiste `CS2_PLAYER_NAME` e garante a linha DB `PlayerProfile` via um `Worker` em background. |
| `user_profile_screen.py` | User Profile | Exibicao e edicao do perfil do usuario (bio, role) via `UserProfileViewModel`. |
| `settings_screen.py` | Settings | Em abas (Aparencia - Caminhos & Dados - Geral): tema, fonte, idioma, caminhos de dados, modo de ingestao, toggles de UI. |
| `steam_config_screen.py` | Steam Config | Entrada de SteamID64 / API key com validacao. |
| `faceit_config_screen.py` | FaceIT Config | Entrada de API key da FaceIT. |
| `wizard_screen.py` | First-Run Wizard | Setup de 5 passos: intro -> nome -> caminho do brain -> caminho dos demos -> lancamento. |
| `help_screen.py` | Help | Help in-app suportado por `backend/knowledge_base/help_system.py` (topicos de `Programma_CS2_RENAN/data/docs/*.md`). |
| `placeholder.py` | (utilitario) | Stub legado `PlaceholderScreen` (titulo centralizado); nao mais registrado — toda rota tem uma tela real. |

## Padrao de arquitetura

Cada tela segue o mesmo template:

```
class FooScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = FooViewModel(self)   # a tela e dona do seu ViewModel
        self._build_ui()                # composicao de widgets
        self._vm.data_changed.connect(self._on_data)   # wiring de signals

    def on_enter(self):                 # chamado por MainWindow.switch_screen()
        self._vm.load()

    def on_leave(self):                 # opcional — implementado onde necessario
        self._vm.cancel()
```

ViewModels fazem todo o carregamento de dados; telas marshall os resultados de volta para os widgets. Trabalho em background usa `core/worker.Worker` (um `QRunnable` no `QThreadPool`) para que a thread da UI permaneca responsiva.

## Invariantes-chave

- **`on_enter()` e chamado por `MainWindow.switch_screen()`** quando uma tela se torna visivel — use-o para atualizar dados.
- **Implemente `on_leave()` quando a tela possui trabalho em andamento** (coach, match history, performance e tactical viewer o fazem) e cancele carregamentos ViewModel pendentes.
- **Sem acesso ao DB na thread da GUI.** Telas com ViewModel persistem atraves dele; os poucos toques diretos no DB (upsert de `PlayerProfile` em profile / wizard, lookup de match-id no tactical viewer) usam um `Worker` off-thread (F-0038).
- **Sem strings hard-coded.** Texto visivel para o usuario passa por `core/i18n_bridge.QtLocalizationManager.get_text()`.

## Integracao

```
qt_app/app.py (registro de telas) --> MainWindow.switch_screen() (router)
    +-- HomeScreen        --> MatchHistoryViewModel + FocusInsightViewModel
    +-- CoachScreen       --> CoachViewModel + CoachingChatViewModel --> CoachingDialogueEngine
    +-- MatchDetailScreen --> MatchDetailViewModel --> backend storage
    +-- PerformanceScreen --> PerformanceViewModel
    +-- TacticalViewer    --> TacticalPlaybackVM / TacticalGhostVM / TacticalChronovisorVM
                              --> core/playback_engine + GhostEngine
    ... (uma rota por tela)
```

## Relacionados

- ViewModels: `apps/qt_app/viewmodels/README.md`
- Widgets customizados: `apps/qt_app/widgets/README.md`
- Core da aplicacao: `apps/qt_app/core/README.md`
- Pai: `apps/qt_app/README.md`
