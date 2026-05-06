# `apps/qt_app/screens/` -- Moduli schermata UI Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Questo pacchetto contiene ogni schermata di primo livello nel frontend Qt. Ogni modulo definisce una sottoclasse di `QWidget` (o `QStackedWidget`) che possiede il layout, il wiring dei segnali e gli hook di lifecycle per-schermata di una rotta nel grafo di navigazione dell'applicazione. I ViewModel (in `apps/qt_app/viewmodels/`) possiedono i dati e la logica di business; le schermate possiedono la composizione visuale.

## Inventario File

| File | Schermata | Scopo |
|------|-----------|-------|
| `__init__.py` | -- | Marcatore di pacchetto. |
| `home_screen.py` | Home | Landing page: riassunto ultimo match, focus insight, hub di navigazione. |
| `coach_screen.py` | Coach | Chat con AI coach: dialogo con `CoachingDialogueEngine`, risposte aumentate via RAG, model picker. |
| `match_history_screen.py` | Match History | Lista filtrabile dei match utente con rating HLTV 2.0. |
| `match_detail_screen.py` | Match Detail | Drilldown per-match: round, economy, highlight, momentum. |
| `performance_screen.py` | Performance | Dashboard aggregata: trend di rating, statistiche per-mappa, punti di forza / debolezza, breakdown utility. |
| `pro_comparison_screen.py` | Pro Comparison | Confronto fianco a fianco delle statistiche utente vs pro selezionato. |
| `pro_player_detail_screen.py` | Pro Player Detail | Profilo pro player con stat card HLTV, match recenti, classificazione di ruolo. |
| `tactical_viewer_screen.py` | Tactical Viewer | Replay 2D della mappa con controlli di playback, overlay ghost AI, highlight chronovisor. |
| `profile_screen.py` | Profile | Editor profilo utente (display name, preferenza ruolo). |
| `user_profile_screen.py` | User Profile | Profilo autenticato con stato di integrazione Steam / FaceIT. |
| `settings_screen.py` | Settings | Tema, lingua, path, modalita di ingestione, model picker, toggle telemetria. |
| `steam_config_screen.py` | Steam Config | Inserimento Steam ID / API key con validazione. |
| `faceit_config_screen.py` | FaceIT Config | Inserimento FaceIT API key con validazione. |
| `wizard_screen.py` | First-Run Wizard | Setup in 4 step: intro -> path brain -> path demo -> finish. |
| `help_screen.py` | Help | Help in-app supportato da `backend/knowledge_base/help_system.py`. |
| `placeholder.py` | (utilita) | Stub `EmptyPlaceholderScreen` mostrato quando una rotta non e ancora implementata. |

## Pattern architetturale

Ogni schermata segue lo stesso template:

```
class FooScreen(QWidget):
    def __init__(self, app_state, viewmodel: FooViewModel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._build_ui()             # composizione widget
        self._wire_signals()         # collega self._vm.* a self._on_*
        self._apply_theme()          # sottoscrivi a theme_engine.themeChanged

    def on_enter(self):              # chiamato dal navigation router al focus
        self._vm.refresh()

    def on_leave(self):              # chiamato quando l'utente naviga via
        self._vm.cancel_loads()
```

I ViewModel fanno tutto il caricamento dati; le schermate marshallano i risultati nei widget. Il lavoro di background usa `core/worker.QThread` cosi il thread UI resta reattivo.

## Invarianti chiave

- **`on_enter` / `on_leave` sono obbligatori.** Il navigation router li chiama; implementazioni mancanti causano leak di thread o sottoscrizioni stantie.
- **I segnali devono essere disconnessi su `on_leave`.** Usa `core/widgets_helpers.disconnect_all()` per evitare double-firing al re-entry.
- **Nessun accesso DB diretto da una schermata.** Tutta la persistenza passa attraverso il ViewModel.
- **Nessuna stringa hard-coded.** Il testo visibile all'utente passa attraverso `core/i18n_bridge.QtLocalizationManager.get_text()`.

## Integrazione

```
qt_app/app.py (router)
    +-- HomeScreen        --> HomeViewModel        --> backend/services/*
    +-- CoachScreen       --> CoachViewModel       --> CoachingDialogueEngine + LLMService
    +-- MatchDetailScreen --> MatchDetailViewModel --> AnalyticsEngine + storage
    +-- PerformanceScreen --> PerformanceViewModel --> reporting/analytics.py
    +-- TacticalViewer    --> TacticalPlaybackVM   --> core/playback_engine + GhostEngine
    ... (una rotta per schermata)
```

## Correlati

- ViewModel: `apps/qt_app/viewmodels/README.md`
- Widget custom: `apps/qt_app/widgets/README.md`
- Core applicativo: `apps/qt_app/core/README.md`
- Parent: `apps/qt_app/README.md`
