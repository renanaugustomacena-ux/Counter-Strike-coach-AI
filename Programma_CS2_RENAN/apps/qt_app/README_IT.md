# Applicazione Desktop Qt (Primaria)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

*Mantenuta dal team Macena CS2 Analyzer. Richiede familiarita con PySide6, MVVM e Qt Signal/Slot.*

## Panoramica

Applicazione desktop PySide6/Qt che implementa l'architettura Model-View-ViewModel (MVVM) con Qt Signal/Slot per l'analisi tattica CS2 e il coaching AI. Questo e il **frontend primario** (91 file Python). L'applicazione include 15 schermate, 10 ViewModel, 6 widget grafici QPainter (QtCharts e stato rimosso per conformita di licenza), 3 widget tattici, una libreria di componenti del design system (26 moduli) piu una ChatPanel di coaching integrata, notifiche toast, 3 temi guidati dai token (CS2, CSGO, CS1.6), wallpaper di sfondo opzionale (default: piatto), internazionalizzazione (Inglese/Italiano/Portoghese, ~565 chiavi per lingua) e una sequenza di spegnimento controllato.

## Punto di Ingresso

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

La funzione `main()` in `app.py` esegue la seguente sequenza di avvio:

1. Abilita lo scaling High-DPI (policy di arrotondamento `PassThrough`)
2. Crea `QApplication` e risolve la versione del pacchetto
3. Connette il gestore di spegnimento controllato (signal `aboutToQuit`)
4. Istanzia `ThemeEngine`, registra i font personalizzati, applica il tema attivo
5. Crea `MainWindow` e imposta il wallpaper iniziale
6. Istanzia e registra tutte le 15 schermate (implementazioni reali, non placeholder)
7. Collega i signal inter-schermata (selezione partita: history -> detail, completamento wizard -> home)
8. Gate primo avvio: mostra WizardScreen se `SETUP_COMPLETED` e False, altrimenti HomeScreen
9. Avvia la console backend (audit DB, FlareSolverr/Hunter condizionale) con finestra di errore di fallback
10. Avvia il polling in background di AppState (intervallo di 10 secondi)

## Struttura Directory

```
qt_app/
├── app.py                          # Punto di ingresso: bootstrap QApplication e registrazione schermate
├── main_window.py                  # QMainWindow con navigazione sidebar + QStackedWidget + livello toast
├── __init__.py
├── core/
│   ├── app_state.py                # Singleton AppState: interroga CoachState DB ogni 10s, emette Signals
│   ├── theme_engine.py             # ThemeEngine: caricamento QSS, QPalette, font, gestione wallpaper
│   ├── design_tokens.py            # Definizioni design token per il sistema componenti Qt
│   ├── qss_generator.py            # Generazione QSS programmatica dai design token
│   ├── animation.py                # Utilita di animazione condivise e helper di easing
│   ├── easing.py                   # Curve di easing personalizzate
│   ├── typography.py               # Scala tipografica e helper font
│   ├── icons.py                    # Registro icone e caricatore asset SVG/icone
│   ├── svg_icon_provider.py        # QIconEngine basato su risorse SVG
│   ├── sound.py                    # Helper riproduzione effetti sonori
│   ├── match_utils.py              # Funzioni utility a livello partita per il livello UI
│   ├── widgets_helpers.py          # Funzioni helper Qt widget generiche
│   ├── web_bridge.py               # Bridge Python↔JavaScript per le web view integrate
│   ├── worker.py                   # Worker QRunnable + WorkerSignals per task in background
│   ├── i18n_bridge.py              # QtLocalizationManager: i18n basato su JSON con Signal al cambio lingua
│   ├── qt_playback_engine.py       # QtPlaybackEngine: riproduzione demo basata su QTimer a ~60 FPS
│   └── __init__.py
├── screens/
│   ├── home_screen.py              # Dashboard e panoramica
│   ├── coach_screen.py             # Schermata coaching AI con ChatPanel integrata (dock rimosso)
│   ├── match_history_screen.py     # Lista partite con rating HLTV 2.0 codificato per colore
│   ├── match_detail_screen.py      # Analisi partita a 4 tab (Panoramica · Round · Economia · Highlights)
│   ├── performance_screen.py       # Analisi prestazioni (tendenze, statistiche per mappa, confronti Z-score)
│   ├── tactical_viewer_screen.py   # Replay mappa 2D con rendering pixel-accurate e timeline
│   ├── user_profile_screen.py      # Visualizzazione e modifica profilo utente
│   ├── profile_screen.py           # Gestione profilo
│   ├── settings_screen.py          # Impostazioni applicazione (tema, font, lingua, percorsi)
│   ├── wizard_screen.py            # Procedura guidata primo avvio per integrazione Steam/Faceit
│   ├── help_screen.py              # Documentazione e guide utente
│   ├── steam_config_screen.py      # Configurazione integrazione Steam
│   ├── faceit_config_screen.py     # Configurazione integrazione Faceit
│   ├── pro_comparison_screen.py    # Analisi comparativa utente vs giocatore pro
│   ├── pro_player_detail_screen.py # Vista profilo giocatore pro
│   ├── placeholder.py              # Factory placeholder per schermate non ancora portate
│   └── __init__.py
├── viewmodels/
│   ├── match_history_vm.py         # Dati lista partite, filtraggio e ordinamento
│   ├── match_detail_vm.py          # Dati analisi per partita (round, economia, highlights)
│   ├── performance_vm.py           # Tendenze prestazioni, statistiche per mappa, forze/debolezze
│   ├── tactical_vm.py              # Controllo playback, predizioni ghost AI, scansione chronovisor
│   ├── coach_vm.py                 # Caricamento insight di coaching dal DB
│   ├── coaching_chat_vm.py         # Dialogo coaching interattivo via Ollama/LLM
│   ├── focus_insight_vm.py         # ViewModel dettaglio insight coaching focalizzato
│   ├── pro_comparison_vm.py        # Dati e punteggio comparativo pro
│   ├── pro_player_detail_vm.py     # Caricamento dati profilo giocatore pro
│   ├── user_profile_vm.py          # Caricamento e salvataggio dati profilo utente
│   └── __init__.py
├── widgets/
│   ├── toast.py                    # ToastWidget + ToastContainer: notifiche effimere (4 livelli di gravita)
│   ├── skeleton.py                 # Widget placeholder di caricamento skeleton
│   ├── charts/                     # Tutti QPainter — QtCharts rimosso (solo GPL)
│   │   ├── economy_chart.py        # EconomyChart: barre economia round per round (QPainter)
│   │   ├── mini_sparkline.py       # MiniSparkline: sparkline compatta con QPainter, senza assi
│   │   ├── momentum_chart.py       # MomentumChart: grafico ad area del momentum squadra (QPainter)
│   │   ├── radar_chart.py          # RadarChart: radar pentagonale delle skill (overlay utente vs pro)
│   │   ├── rating_sparkline.py     # RatingSparkline: tendenza rating con linea di base
│   │   ├── utility_bar_chart.py    # UtilityBarChart: barre orizzontali uso utility
│   │   └── __init__.py
│   ├── coaching/
│   │   ├── chat_panel.py           # ChatPanel: chat coach integrata (bolle, riga meta, riga input)
│   │   └── __init__.py
│   ├── components/                 # Componenti UI riutilizzabili (design system) — 26 moduli
│   │   ├── __init__.py             # Export dei componenti
│   │   ├── card.py                 # Widget contenitore card (5 varianti di profondita)
│   │   ├── db_record_card.py       # DbRecordCard: eco mono della riga DB (tabella · colonna · valore)
│   │   ├── delta_chip.py           # DeltaChip: pillola delta ▲/▼ relativa al benchmark
│   │   ├── drivers_list.py         # DriversList: righe di contributo con segno (cosa ha mosso una statistica)
│   │   ├── empty_state.py          # Placeholder stato vuoto con icona e messaggio
│   │   ├── filter_chip.py          # Pillola filtro attivabile
│   │   ├── focus_insight.py        # FocusInsightCard: card focus insight della home
│   │   ├── hero_stats_strip.py     # Striscia orizzontale di metriche hero
│   │   ├── icon_widget.py          # Widget visualizzazione icone (SVG/pixmap)
│   │   ├── last_match_hero.py      # LastMatchHeroCard: card hero ultima partita della home
│   │   ├── map_tile.py             # MapTile: tile statistiche per mappa con accento win-rate
│   │   ├── match_mini_card.py      # Card riassunto partita compatta
│   │   ├── match_row_card.py       # Card riga partita estesa con anteprima statistiche
│   │   ├── metric_bar_row.py       # MetricBarRow: etichetta + barra metrica orizzontale + valore
│   │   ├── mini_link_card.py       # MiniLinkCard: piccola card di navigazione a link correlati
│   │   ├── mono_footer.py          # MonoFooter: riga footer mono di provenienza/stato
│   │   ├── nav_sidebar.py          # Componente barra laterale di navigazione comprimibile
│   │   ├── numbered_step.py        # NumberedStep: riga passo 01/02/03 in mono accentato
│   │   ├── pro_badge.py            # ProBadge: pillola PRO/tier per le superfici dei giocatori pro
│   │   ├── progress_ring.py        # Indicatore anello di progresso circolare
│   │   ├── section_header.py       # Intestazione sezione con titolo e azione opzionale
│   │   ├── stat_badge.py           # Badge statistiche con etichetta e valore
│   │   ├── status_chip.py          # Pillola di stato colorata con etichetta di testo
│   │   ├── stepper.py              # Indicatore di avanzamento a passi etichettati (usato dal wizard)
│   │   ├── tip_box.py              # TipBox: box suggerimento con bordo accentato
│   │   └── toggle_switch.py        # Interruttore booleano animato
│   ├── tactical/
│   │   ├── map_widget.py           # TacticalMapWidget: rendering mappa 2D + overlay zone (assets/map_zones/) + scie di movimento
│   │   ├── player_sidebar.py       # PlayerSidebar: stato giocatore in tempo reale (salute, armatura, armi)
│   │   ├── timeline_widget.py      # TimelineWidget: scrubbing, divisori round, glifi momenti ★/◆/●
│   │   └── __init__.py
│   └── __init__.py
├── web/                            # Sub-app TypeScript (integrate via QWebEngineView)
│   ├── coach-chat/
│   ├── match-detail/
│   ├── tactical-viewer/
│   └── shared/
└── themes/
    └── base.qss.template           # Foglio di stile a token — unica fonte QSS
                                    # (renderizzato per tema da core/qss_generator.py)
```

## Architettura MVVM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MainWindow                                  │
│  ┌──────────┐  ┌─────────────────────────────────────────────────┐  │
│  │ Sidebar   │  │ QStackedWidget (15 schermate)                  │  │
│  │ (7 pul-   │  │  ┌───────────────────────────────────────────┐ │  │
│  │  santi)   │  │  │  Screen (QWidget)                         │ │  │
│  │           │  │  │   │                                       │ │  │
│  │  Home     │  │  │   │ si connette a                         │ │  │
│  │  Coach    │  │  │   ▼                                       │ │  │
│  │  History  │  │  │  ViewModel (QObject)                      │ │  │
│  │  Stats    │  │  │   │ Signal ──────> Screen aggiorna la UI  │ │  │
│  │  Tactical │  │  │   │                                       │ │  │
│  │           │  │  │   │ Worker (QRunnable)                    │ │  │
│  │           │  │  │   │ └──> DB/calcolo in background         │ │  │
│  │           │  │  │   │      └──> Signal.result ──> ViewModel │ │  │
│  │           │  │  └───────────────────────────────────────────┘ │  │
│  └──────────┘  └─────────────────────────────────────────────────┘  │
│                ┌─────────────────────────────────────────────────┐  │
│                │ _BackgroundWidget (wallpaper, opacita 15%)      │  │
│                │ ToastContainer (overlay notifiche in alto-dx)   │  │
│                └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              AppState (singleton, interroga CoachState DB ogni 10s)
              └──> service_active_changed, coach_status_changed,
                   parsing_progress_changed, belief_confidence_changed,
                   total_matches_changed, training_changed,
                   notification_received
```

**Flusso dati:** Screen <-> ViewModel (QObject + Signals) <-> Database (SQLModel) tramite Worker threads. Tutti gli accessi al database avvengono su `QThreadPool`; i risultati vengono automaticamente rimandati al thread principale tramite connessioni Signal.

## Schermate (15)

| # | Schermata | File | Descrizione |
|---|-----------|------|-------------|
| 1 | HomeScreen | `home_screen.py` | Dashboard con stato servizio, conteggio partite, progresso training, progresso parsing |
| 2 | CoachScreen | `coach_screen.py` | **Schermata impilata** di coaching AI con anello di belief, top-3 insight ordinati e ChatPanel integrata (Ollama) — il vecchio dock chat QDockWidget e stato rimosso |
| 3 | MatchHistoryScreen | `match_history_screen.py` | Lista partite con rating HLTV 2.0 codificato per colore, emette Signal `match_selected` |
| 4 | MatchDetailScreen | `match_detail_screen.py` | Analisi partita a 4 tab: Panoramica · Round · Economia · Highlights (tab a sottolineatura, frame 09) |
| 5 | PerformanceScreen | `performance_screen.py` | Analisi prestazioni: tendenze rating, statistiche per mappa, forze/debolezze, utilizzo utility |
| 6 | TacticalViewerScreen | `tactical_viewer_screen.py` | Replay mappa 2D con overlay zone, scie di movimento, timeline a glifi (★ critico · ◆ clutch · ● giocata), scansione chronovisor e Ghost Mode (doppio progresso + pannello divergenza) |
| 7 | UserProfileScreen | `user_profile_screen.py` | Visualizzazione profilo utente con modifica bio e ruolo |
| 8 | ProfileScreen | `profile_screen.py` | Editor nome in gioco (frame 17): nota maiuscole/minuscole, eco DbRecordCard, card link correlati, nota archiviazione locale |
| 9 | SettingsScreen | `settings_screen.py` | Impostazioni applicazione: card anteprima tema cliccabili, tipo/dimensione font, anteprima live, lingua, percorsi dati |
| 10 | WizardScreen | `wizard_screen.py` | Procedura guidata primo avvio con stepper etichettato (Intro · Nome · Percorso Brain · Percorso demo · Avvio) e testo di calibrazione "Cosa succede adesso"; emette `setup_completed` |
| 11 | HelpScreen | `help_screen.py` | Articolo di aiuto strutturato: passi numerati per iniziare, card argomenti, scorciatoie tastiera, provenienza documenti |
| 12 | SteamConfigScreen | `steam_config_screen.py` | Integrazione Steam: configurazione percorso, rilevamento cartella demo |
| 13 | FaceitConfigScreen | `faceit_config_screen.py` | Integrazione Faceit: configurazione API key, ID giocatore |
| 14 | ProComparisonScreen | `pro_comparison_screen.py` | Confronto statistico affiancato utente vs giocatore pro selezionato |
| 15 | ProPlayerDetailScreen | `pro_player_detail_screen.py` | Profilo completo giocatore pro: statistiche carriera, heatmap, giocate caratteristiche |

## ViewModel (10)

| ViewModel | File | Signals Principali | Descrizione |
|-----------|------|--------------------|-------------|
| `MatchHistoryViewModel` | `match_history_vm.py` | `matches_changed(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Carica lista partite da `PlayerMatchStats` con supporto cancellazione |
| `MatchDetailViewModel` | `match_detail_vm.py` | `data_changed(dict, list, list, dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carica statistiche partita, dati round, insight coaching, breakdown HLTV |
| `PerformanceViewModel` | `performance_vm.py` | `data_changed(list, dict, dict, dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carica storico rating, statistiche per mappa, forze/debolezze, dati utility |
| `TacticalPlaybackVM` | `tactical_vm.py` | `frame_updated(object)`, `current_tick_changed(int)`, `is_playing_changed(bool)` | Controllo playback: play/pause, velocita, seek, tracciamento tick via PlaybackEngine |
| `TacticalGhostVM` | `tactical_vm.py` | `ghost_active_changed(bool)`, `is_loaded_changed(bool)` | Predizioni posizione ghost AI tramite GhostEngine caricato lazily |
| `TacticalChronovisorVM` | `tactical_vm.py` | `scan_complete(list, int)`, `navigate_to(int, str)`, `is_scanning_changed(bool)` | Scansione momenti critici e navigazione jump-to tramite ChronovisorScanner |
| `CoachViewModel` | `coach_vm.py` | `insights_loaded(list)`, `is_loading_changed(bool)`, `error_changed(str)` | Carica le ultime righe `CoachingInsight` per il giocatore attivo |
| `CoachingChatViewModel` | `coaching_chat_vm.py` | `messages_changed(list)`, `session_active_changed(bool)`, `is_available_changed(bool)` | Chat coaching interattiva via CoachingDialogueEngine (backend Ollama) |
| `FocusInsightViewModel` | `focus_insight_vm.py` | `insight_changed(object)`, `is_loading_changed(bool)` | Carica e gestisce la vista dettaglio per un singolo insight coaching focalizzato |
| `ProComparisonViewModel` | `pro_comparison_vm.py` | `data_changed(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Recupera e calcola il punteggio del confronto statistico utente-vs-pro |
| `ProPlayerDetailViewModel` | `pro_player_detail_vm.py` | `profile_changed(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carica profilo giocatore pro e statistiche carriera |
| `UserProfileViewModel` | `user_profile_vm.py` | `profile_loaded(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carica/salva `PlayerProfile` (bio, ruolo) con accesso DB in background |

*Nota: Il modulo Tactical contiene 3 ViewModel in un singolo file (`tactical_vm.py`) per coesione.*

## Widget

### Widget Grafici (`widgets/charts/`) — tutti QPainter

> **QtCharts e stato rimosso** dall'app: Qt Charts e disponibile solo con licenza GPLv3 o commerciale (a differenza di Qt base, LGPL), incompatibile con questo repository proprietario. Ogni grafico e ora un'implementazione custom di `QWidget.paintEvent`; un test di guardia sulla licenza (`test_charts.py::TestQtChartsRetired`) fa fallire la suite se un riferimento `QtCharts`/`QChart` ricompare sotto `apps/qt_app/`.

| Widget | File | Descrizione |
|--------|------|-------------|
| `EconomyChart` | `economy_chart.py` | Barre economia round per round con colorazione per lato, divisore di meta partita e scala $K |
| `MiniSparkline` | `mini_sparkline.py` | Sparkline compatta senza assi, usata nella card hero dell'ultima partita |
| `MomentumChart` | `momentum_chart.py` | Evoluzione momentum squadra per round, overlay ad area duale CT/T |
| `RadarChart` | `radar_chart.py` | Radar pentagonale delle skill con overlay poligonale utente-vs-pro (confronto pro) |
| `RatingSparkline` | `rating_sparkline.py` | Linea di tendenza del rating con baseline 1.0 (dettaglio partita / prestazioni) |
| `UtilityBarChart` | `utility_bar_chart.py` | Barre orizzontali uso utility (flash/smoke/HE/molly) |

### Widget di Coaching (`widgets/coaching/`)

| Widget | File | Descrizione |
|--------|------|-------------|
| `ChatPanel` | `chat_panel.py` | Chat coach integrata: bolle messaggio, riga meta mono di provenienza, stati di disponibilita, riga input — ospitata da CoachScreen (sostituisce il dock chat rimosso) |

### Primitive componenti aggiunte nel rebuild design-atlas (`widgets/components/`)

| Widget | File | Descrizione |
|--------|------|-------------|
| `ProBadge` | `pro_badge.py` | Pillola PRO/tier per le superfici dei giocatori pro |
| `DeltaChip` | `delta_chip.py` | Pillola delta ▲/▼ relativa al benchmark (vs media 30 giorni / baseline pro) |
| `DriversList` | `drivers_list.py` | Righe di contributo con segno che spiegano cosa ha mosso una statistica |
| `TipBox` | `tip_box.py` | Box suggerimento con bordo accentato (wizard, aiuto) |
| `NumberedStep` | `numbered_step.py` | Riga passo 01/02/03 in mono accentato (pagina di avvio del wizard, aiuto) |
| `DbRecordCard` | `db_record_card.py` | Eco mono della riga DB (`tabella · colonna · valore`, frame 17) |
| `MonoFooter` | `mono_footer.py` | Riga footer mono di provenienza/stato (didascalie a fondo schermata) |
| `MiniLinkCard` | `mini_link_card.py` | Piccola card di navigazione a link correlati |
| `MapTile` | `map_tile.py` | Tile statistiche per mappa con accento win-rate |
| `MetricBarRow` | `metric_bar_row.py` | Riga etichetta + barra metrica orizzontale + valore |

### Widget Tattici (`widgets/tactical/`)

| Widget | File | Descrizione |
|--------|------|-------------|
| `TacticalMapWidget` | `map_widget.py` | Rendering mappa tattica 2D con punti giocatore, overlay di zone con nome (`assets/map_zones/*.json`), scie di movimento, overlay ghost e marcatori evento |
| `PlayerSidebar` | `player_sidebar.py` | Stato giocatore in tempo reale: salute, armatura, arma, denaro, stato vivo/morto |
| `TimelineWidget` | `timeline_widget.py` | Scrubbing playback demo con divisori round, marcatori evento e glifi dei momenti critici differenziati per tipo (★ critico / ◆ clutch / ● giocata, fallback stella) |

### Notifiche Toast (`widgets/toast.py`)

| Gravita | Icona | Auto-chiusura |
|---------|-------|---------------|
| INFO | (i) | 5 secondi |
| WARNING | (!) | 8 secondi |
| ERROR | (X) | 12 secondi |
| CRITICAL | (teschio) | Solo manuale |

Massimo 3 toast visibili contemporaneamente. Il toast piu vecchio viene rimosso quando il limite viene superato. Il `ToastContainer` viene renderizzato come overlay in alto a destra sopra tutto il contenuto delle schermate tramite `QStackedLayout.StackAll`.

## Singleton AppState

`AppState` (`core/app_state.py`) e un singleton `QObject` ottenuto tramite `get_app_state()`. Interroga la riga del database `CoachState` (id=1) ogni 10 secondi usando un pattern `QTimer` + `Worker`, e emette signal tipizzati solo quando i valori cambiano effettivamente (emissione basata su delta):

| Signal | Tipo | Attivazione |
|--------|------|-------------|
| `service_active_changed` | `bool` | Delta heartbeat > 300 secondi = inattivo |
| `coach_status_changed` | `str` | Testo stato ingestione cambiato |
| `parsing_progress_changed` | `float` | Progresso parsing demo aggiornato |
| `belief_confidence_changed` | `float` | Confidenza belief del modello aggiornata |
| `total_matches_changed` | `int` | Totale partite processate cambiato |
| `training_changed` | `dict` | Qualsiasi tra: current_epoch, total_epochs, train_loss, val_loss, eta_seconds |
| `notification_received` | `(str, str)` | Righe `ServiceNotification` non lette (gravita + messaggio) |

AppState e in **sola lettura** dal lato Qt. Solo il session engine del backend scrive su `CoachState`.

## ThemeEngine

`ThemeEngine` (`core/theme_engine.py`) gestisce l'identita visiva dell'applicazione:

- **3 temi:** CS2 (scuro + accento arancione), CSGO (blu-ardesia + accento acciaio), CS 1.6 (retro terminale verde)
- **I design token sono l'unica fonte di verita:** i set di token per tema (`core/design_tokens.py`) alimentano **sia** il rendering QSS (`themes/base.qss.template` via `core/qss_generator.py`, con iniezione dinamica font-family/size) **sia** la configurazione `QPalette` per i widget che non rispettano QSS — nessun valore colore mantenuto a mano fuori dalle tabelle dei token
- **Font:** i font legacy di `PHOTO_GUI/` (Roboto, JetBrains Mono, New Hope, CS Regular, YUPIX) piu lo stack display OFL incluso, auto-scansionato da `assets/fonts/` (Space Grotesk, Inter, pesi JetBrains Mono — vedi `assets/fonts/README.txt` per fonti/licenze)
- **Wallpaper:** il default e **nessun wallpaper** — sfondo piatto `surface_base` come da design atlas. Una scelta utente persistita puo selezionare un file wallpaper per tema, renderizzato al 15% di opacita tramite `_BackgroundWidget`
- **Colori rating HLTV:** verde (> 1.10), giallo (0.90-1.10), rosso (< 0.90) con etichette testo WCAG 1.4.1

## Pattern Worker

La classe `Worker` (`core/worker.py`) e un `QRunnable` che incapsula qualsiasi callable per l'esecuzione su `QThreadPool.globalInstance()`. Emette tre signal tramite `WorkerSignals`:

```python
worker = Worker(some_function, arg1, arg2)
worker.signals.result.connect(on_success)   # auto-marshal al thread principale
worker.signals.error.connect(on_error)       # riceve str(exception)
worker.signals.finished.connect(on_done)     # emesso sempre
QThreadPool.globalInstance().start(worker)
```

Tutte le emissioni di signal sono protette da `try/except RuntimeError` per gestire il caso in cui il ricevitore viene garbage-collected prima che il worker finisca. I worker vengono auto-eliminati dopo l'esecuzione (`setAutoDelete(True)`).

## Moduli Core Aggiuntivi

| Modulo | File | Descrizione |
|--------|------|-------------|
| `QtLocalizationManager` | `core/i18n_bridge.py` | Singleton (`i18n`) che fornisce `get_text(key)` con priorita JSON, fallback hardcoded, e Signal `language_changed` |
| `QtPlaybackEngine` | `core/qt_playback_engine.py` | Sottoclasse di `PlaybackEngine` che usa `QTimer` a intervallo 16ms (~60 FPS) |
| `DesignTokens` | `core/design_tokens.py` | Definizioni design token (spaziatura, raggio, elevazione) per il sistema componenti Qt |
| `QSSGenerator` | `core/qss_generator.py` | Generazione programmatica di fogli di stile QSS dai design token |
| `Animation` | `core/animation.py` | Utilita di animazione condivise e helper di easing per transizioni widget |
| `Icons` | `core/icons.py` | Registro icone e caricatore asset SVG/icone per il sistema componenti |
| `Easing` | `core/easing.py` | Curve di easing personalizzate per le animazioni widget |
| `Typography` | `core/typography.py` | Definizioni scala tipografica e helper font |
| `SVGIconProvider` | `core/svg_icon_provider.py` | Implementazione QIconEngine basata su risorse SVG |
| `Sound` | `core/sound.py` | Helper riproduzione effetti sonori per il feedback UI |
| `MatchUtils` | `core/match_utils.py` | Funzioni utility a livello partita per il livello UI |
| `WidgetsHelpers` | `core/widgets_helpers.py` | Funzioni helper Qt widget generiche |
| `WebBridge` | `core/web_bridge.py` | Bridge Python↔JavaScript per le web view integrate |

## Test

La suite UI gira interamente offscreen (`QT_QPA_PLATFORM=offscreen`) con le animazioni disabilitate (`MACENA_UI_ANIMATIONS=0`):

| File | Copertura |
|------|-----------|
| `tests/test_qt_core.py` | Moduli core (token, generazione QSS, bridge i18n, worker) — include un test di animazione live **isolato in un sottoprocesso** cosi il percorso con animazioni abilitate viene esercitato senza inquinare la run offscreen |
| `tests/test_ui_smoke.py` | **Walk a runtime**: avvia la MainWindow reale, visita ogni schermata, cambia live tutti e 3 i temi, fa il roundtrip delle lingue (retranslate), comprime/espande la sidebar |
| `tests/test_ui_harness.py` | **Parita delle chiavi i18n** tra en/it/pt (`test_i18n_key_parity_across_languages`) + esegue l'harness screenshot end-to-end come sottoprocesso |
| `tests/test_charts.py` | Widget grafici QPainter + il gate di licenza QtCharts (`TestQtChartsRetired`) |
| `tests/test_tactical_frame_widgets.py` | Loader zone mappa, mapping tipo→glifo della timeline + hit-test stelle, adapter righe divergenza ghost |
| `tests/test_detonation_overlays.py` | Painting overlay detonazioni granate/bomba |

Strumenti screenshot: `tools/ui_screenshot.py` (harness offscreen — schermate reali + dati fixture da `tools/ui_fixtures.py`, PNG per tema) e `tools/ui_gallery.py` (foglio galleria componenti).

## Note di Sviluppo

- **Dimensione minima finestra:** 1280x720 pixel
- **Sidebar:** comprimibile 220px ↔ 60px, con 7 pulsanti di navigazione (Home, Coach, Match History, Performance, Tactical Viewer, Settings, Help)
- **Ciclo di vita schermata:** `on_enter()` viene chiamato automaticamente quando una schermata diventa visibile; `retranslate()` viene chiamato al cambio lingua
- **Thread safety:** Tutti gli accessi DB passano attraverso Worker/QThreadPool. Non accedere mai alle sessioni SQLModel sul thread principale.
- **i18n:** 3 lingue (en, pt, it) caricate da `assets/i18n/*.json`. Il Signal `language_changed` attiva `retranslate()` su tutte le schermate registrate.
- **Spegnimento controllato:** `app.aboutToQuit` ferma il polling di AppState e spegne la console backend
- **Gate primo avvio:** Se l'impostazione `SETUP_COMPLETED` e False, l'app parte su WizardScreen invece di HomeScreen
- **Fallimento avvio backend:** Se la console backend non riesce ad avviarsi, viene mostrato un avviso `QMessageBox` ma l'app continua in modalita degradata
