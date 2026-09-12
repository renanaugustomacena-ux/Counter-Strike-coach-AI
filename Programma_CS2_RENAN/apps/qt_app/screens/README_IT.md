# `apps/qt_app/screens/` -- Moduli schermata UI Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Questo pacchetto contiene ogni schermata di primo livello nel frontend Qt. Ogni modulo definisce una sottoclasse di `QWidget` che possiede il layout, il wiring dei segnali e gli hook di lifecycle per-schermata per una rotta nel grafo di navigazione dell'applicazione. I ViewModel (in `apps/qt_app/viewmodels/`) possiedono i dati e la logica di business; le schermate possiedono la composizione visuale.

## Inventario File

| File | Schermata | Scopo |
|------|-----------|-------|
| `__init__.py` | -- | Marcatore di pacchetto. |
| `home_screen.py` | Home | Landing page: coppia hero ultimo match + focus settimanale, strip match recenti, launcher analisi demo / ingestione pro, hub di navigazione. |
| `coach_screen.py` | Coach | Dashboard RAP Coach: anello di confidenza belief-state, righe di insight recenti, piu un dock `ChatPanel` embedded (attivato dal pulsante Chat) supportato da `CoachingDialogueEngine` (via `CoachingChatViewModel`). |
| `match_history_screen.py` | Match History | Lista raggruppata (Oggi / Questa Settimana / Precedenti) delle demo analizzate con filtri sorgente (Tutti / Personali / Pro) e mappa; rating per-match rispetto alla baseline personale. |
| `match_detail_screen.py` | Match Detail | Drilldown per-match a schede: panoramica, round, economia, highlight (momentum + coaching insight). |
| `performance_screen.py` | Performance | Dashboard aggregata: trend di rating, statistiche per-mappa, punti di forza / debolezza, breakdown utility. |
| `pro_comparison_screen.py` | Pro Comparison | Confronto Pro vs Pro o Me vs Pro: radar di abilita + metriche head-to-head; Me vs Pro e bloccato finche non sono analizzati abbastanza match personali. |
| `pro_player_detail_screen.py` | Pro Player Detail | Profilo pro player con stat card HLTV, match recenti, classificazione di ruolo. |
| `tactical_viewer_screen.py` | Tactical Viewer | Replay 2D della mappa con controlli di playback, overlay ghost AI, highlight chronovisor. |
| `profile_screen.py` | Profile | Editor del nome in-game del giocatore; persiste `CS2_PLAYER_NAME` e assicura la riga DB `PlayerProfile` tramite un `Worker` in background. |
| `user_profile_screen.py` | User Profile | Visualizzazione e modifica del profilo utente (bio, ruolo) tramite `UserProfileViewModel`. |
| `settings_screen.py` | Settings | A schede (Aspetto - Percorsi & Dati - Generale): tema, font, lingua, percorsi dati, modalita di ingestione, toggle UI. |
| `steam_config_screen.py` | Steam Config | Inserimento SteamID64 / API key con validazione. |
| `faceit_config_screen.py` | FaceIT Config | Inserimento FaceIT API key. |
| `wizard_screen.py` | First-Run Wizard | Setup in 5 step: intro -> nome -> percorso brain -> percorso demo -> avvio. |
| `help_screen.py` | Help | Help in-app supportato da `backend/knowledge_base/help_system.py` (argomenti da `Programma_CS2_RENAN/data/docs/*.md`). |
| `placeholder.py` | (utilita) | Stub legacy `PlaceholderScreen` (titolo centrato); non piu registrato -- ogni rotta ha una schermata reale. |

## Pattern architetturale

Ogni schermata segue lo stesso template:

```
class FooScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = FooViewModel(self)   # la schermata possiede il suo ViewModel
        self._build_ui()                # composizione widget
        self._vm.data_changed.connect(self._on_data)   # wiring segnali

    def on_enter(self):                 # chiamato da MainWindow.switch_screen()
        self._vm.load()

    def on_leave(self):                 # opzionale -- implementato dove necessario
        self._vm.cancel()
```

I ViewModel fanno tutto il caricamento dati; le schermate marshallano i risultati nei widget. Il lavoro di background usa `core/worker.Worker` (un `QRunnable` su `QThreadPool`) cosi il thread UI resta reattivo.

## Invarianti chiave

- **`on_enter()` e chiamato da `MainWindow.switch_screen()`** quando una schermata diventa visibile -- usalo per aggiornare i dati.
- **Implementa `on_leave()` quando la schermata ha lavoro in corso** (coach, match history, performance e tactical viewer lo fanno) e annulla i caricamenti ViewModel pendenti.
- **Nessun accesso DB sul thread GUI.** Le schermate con un ViewModel persistono attraverso di esso; i pochi tocchi DB diretti (upsert `PlayerProfile` in profile / wizard, lookup match-id nel tactical viewer) usano un `Worker` off-thread (F-0038).
- **Nessuna stringa hard-coded.** Il testo visibile all'utente passa attraverso `core/i18n_bridge.QtLocalizationManager.get_text()`.

## Integrazione

```
qt_app/app.py (registro schermate) --> MainWindow.switch_screen() (router)
    +-- HomeScreen        --> MatchHistoryViewModel + FocusInsightViewModel
    +-- CoachScreen       --> CoachViewModel + CoachingChatViewModel --> CoachingDialogueEngine
    +-- MatchDetailScreen --> MatchDetailViewModel --> backend storage
    +-- PerformanceScreen --> PerformanceViewModel
    +-- TacticalViewer    --> TacticalPlaybackVM / TacticalGhostVM / TacticalChronovisorVM
                              --> core/playback_engine + GhostEngine
    ... (una rotta per schermata)
```

## Correlati

- ViewModel: `apps/qt_app/viewmodels/README.md`
- Widget custom: `apps/qt_app/widgets/README.md`
- Core applicativo: `apps/qt_app/core/README.md`
- Parent: `apps/qt_app/README.md`
