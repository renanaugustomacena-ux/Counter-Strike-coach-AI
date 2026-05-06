# `apps/qt_app/screens/` — Módulos de tela da UI Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Este pacote contém todas as telas top-level do frontend Qt. Cada módulo define uma subclasse de `QWidget` (ou `QStackedWidget`) que detém o layout, o wiring de signals e os hooks de ciclo de vida por tela para uma rota no grafo de navegação da aplicação. ViewModels (em `apps/qt_app/viewmodels/`) detêm os dados e a lógica de negócio; telas detêm a composição visual.

## Inventário de arquivos

| Arquivo | Tela | Finalidade |
|---------|------|------------|
| `__init__.py` | — | Marcador de pacote. |
| `home_screen.py` | Home | Página inicial: resumo da última partida, focus insight, hub de navegação. |
| `coach_screen.py` | Coach | Chat com coach AI: diálogo com `CoachingDialogueEngine`, respostas augmentadas por RAG, seletor de modelo. |
| `match_history_screen.py` | Match History | Lista filtrável de partidas do usuário com ratings HLTV 2.0. |
| `match_detail_screen.py` | Match Detail | Drilldown por partida: rounds, economia, highlights, momentum. |
| `performance_screen.py` | Performance | Dashboard agregado: tendência de rating, stats por mapa, forças / fraquezas, breakdown de utility. |
| `pro_comparison_screen.py` | Pro Comparison | Comparação lado a lado de stats entre o usuário e um pro selecionado. |
| `pro_player_detail_screen.py` | Pro Player Detail | Perfil do pro com card de stat HLTV, partidas recentes, classificação de role. |
| `tactical_viewer_screen.py` | Tactical Viewer | Replay 2D do mapa com controles de playback, overlay de ghost AI, highlights de chronovisor. |
| `profile_screen.py` | Profile | Editor de perfil do usuário (nome de exibição, preferência de role). |
| `user_profile_screen.py` | User Profile | Perfil autenticado com status de integração Steam / FaceIT. |
| `settings_screen.py` | Settings | Tema, idioma, paths, modo de ingestão, seletor de modelo, toggle de telemetria. |
| `steam_config_screen.py` | Steam Config | Entrada de Steam ID / API key com validação. |
| `faceit_config_screen.py` | FaceIT Config | Entrada de API key da FaceIT com validação. |
| `wizard_screen.py` | First-Run Wizard | Setup de 4 passos: intro → caminho do brain → caminho dos demos → finish. |
| `help_screen.py` | Help | Help in-app suportado por `backend/knowledge_base/help_system.py`. |
| `placeholder.py` | (utilitário) | Stub `EmptyPlaceholderScreen` exibido quando uma rota ainda não está implementada. |

## Padrão de arquitetura

Cada tela segue o mesmo template:

```
class FooScreen(QWidget):
    def __init__(self, app_state, viewmodel: FooViewModel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._build_ui()             # composição de widgets
        self._wire_signals()         # liga self._vm.* signals a self._on_*
        self._apply_theme()          # inscreve em theme_engine.themeChanged

    def on_enter(self):              # chamado pelo router de navegação ao receber foco
        self._vm.refresh()

    def on_leave(self):              # chamado quando o usuário navega para fora
        self._vm.cancel_loads()
```

ViewModels fazem todo o carregamento de dados; telas marshall os resultados de volta para os widgets. Trabalho em background usa `core/worker.QThread` para que a thread da UI permaneça responsiva.

## Invariantes-chave

- **`on_enter` / `on_leave` são obrigatórios.** O router de navegação os chama; implementações ausentes vazam threads ou subscriptions stale.
- **Signals devem ser desconectados em `on_leave`.** Use `core/widgets_helpers.disconnect_all()` para evitar disparo duplo após reentrada.
- **Sem acesso direto ao DB de uma tela.** Toda persistência passa pela ViewModel.
- **Sem strings hard-coded.** Texto visível para o usuário passa por `core/i18n_bridge.QtLocalizationManager.get_text()`.

## Integração

```
qt_app/app.py (router)
    +-- HomeScreen        --> HomeViewModel        --> backend/services/*
    +-- CoachScreen       --> CoachViewModel       --> CoachingDialogueEngine + LLMService
    +-- MatchDetailScreen --> MatchDetailViewModel --> AnalyticsEngine + storage
    +-- PerformanceScreen --> PerformanceViewModel --> reporting/analytics.py
    +-- TacticalViewer    --> TacticalPlaybackVM   --> core/playback_engine + GhostEngine
    ... (uma rota por tela)
```

## Relacionados

- ViewModels: `apps/qt_app/viewmodels/README.md`
- Widgets customizados: `apps/qt_app/widgets/README.md`
- Core da aplicação: `apps/qt_app/core/README.md`
- Pai: `apps/qt_app/README.md`
