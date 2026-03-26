# Applicazione Desktop Qt (Primaria)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

*Mantenuta dal team Macena CS2 Analyzer. Richiede familiarita con PySide6, MVVM e Qt Signal/Slot.*

## Panoramica

Applicazione desktop PySide6/Qt che implementa l'architettura Model-View-ViewModel (MVVM) con Qt Signal/Slot per l'analisi tattica CS2 e il coaching AI. Questo e il **frontend primario** (56 file Python), che sostituisce l'app legacy Kivy/KivyMD in [`desktop_app/`](../desktop_app/). L'applicazione include 13 schermate, 7 ViewModel, 6 widget grafici, 3 widget tattici, notifiche toast, 3 temi QSS (CS2, CSGO, CS1.6), rendering wallpaper di sfondo, internazionalizzazione (Inglese/Italiano/Portoghese) e una sequenza di spegnimento controllato.

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
6. Istanzia e registra tutte le 13 schermate (implementazioni reali, non placeholder)
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
│   ├── icons.py                    # Registro icone e caricatore asset SVG/icone
│   ├── worker.py                   # Worker QRunnable + WorkerSignals per task in background
│   ├── asset_bridge.py             # QtAssetBridge: carica immagini mappa come QPixmap (singleton)
│   ├── i18n_bridge.py              # QtLocalizationManager: i18n basato su JSON con Signal al cambio lingua
│   ├── qt_playback_engine.py       # QtPlaybackEngine: riproduzione demo basata su QTimer a ~60 FPS
│   └── __init__.py
├── screens/
│   ├── home_screen.py              # Dashboard e panoramica
│   ├── coach_screen.py             # Interfaccia coaching AI con pannello chat
│   ├── match_history_screen.py     # Lista partite con rating HLTV 2.0 codificato per colore
│   ├── match_detail_screen.py      # Analisi partita multi-sezione (panoramica, round, economia, momentum)
│   ├── performance_screen.py       # Analisi prestazioni (tendenze, statistiche per mappa, confronti Z-score)
│   ├── tactical_viewer_screen.py   # Replay mappa 2D con rendering pixel-accurate e timeline
│   ├── user_profile_screen.py      # Visualizzazione e modifica profilo utente
│   ├── profile_screen.py           # Gestione profilo
│   ├── settings_screen.py          # Impostazioni applicazione (tema, font, lingua, percorsi)
│   ├── wizard_screen.py            # Procedura guidata primo avvio per integrazione Steam/Faceit
│   ├── help_screen.py              # Documentazione e guide utente
│   ├── steam_config_screen.py      # Configurazione integrazione Steam
│   ├── faceit_config_screen.py     # Configurazione integrazione Faceit
│   ├── placeholder.py              # Factory placeholder per schermate non ancora portate
│   └── __init__.py
├── viewmodels/
│   ├── match_history_vm.py         # Dati lista partite, filtraggio e ordinamento
│   ├── match_detail_vm.py          # Dati analisi per partita (round, economia, highlights)
│   ├── performance_vm.py           # Tendenze prestazioni, statistiche per mappa, forze/debolezze
│   ├── tactical_vm.py              # Controllo playback, predizioni ghost AI, scansione chronovisor
│   ├── coach_vm.py                 # Caricamento insight di coaching dal DB
│   ├── coaching_chat_vm.py         # Dialogo coaching interattivo via Ollama/LLM
│   ├── user_profile_vm.py          # Caricamento e salvataggio dati profilo utente
│   └── __init__.py
├── widgets/
│   ├── toast.py                    # ToastWidget + ToastContainer: notifiche effimere (4 livelli di gravita)
│   ├── skeleton.py                 # Widget placeholder di caricamento skeleton
│   ├── charts/
│   │   ├── radar_chart.py          # RadarChartWidget: radar prestazioni multidimensionale
│   │   ├── momentum_chart.py       # MomentumGraphWidget: evoluzione momentum squadra per round
│   │   ├── economy_chart.py        # EconomyGraphWidget: timeline economia round-by-round
│   │   ├── rating_sparkline.py     # RatingSparklineWidget: sparkline compatto storico rating
│   │   ├── trend_chart.py          # TrendGraphWidget: visualizzazione tendenze serie temporali
│   │   ├── utility_bar_chart.py    # UtilityBarWidget: confronto utilizzo utility (utente vs baseline pro)
│   │   └── __init__.py
│   ├── components/                 # Componenti UI riutilizzabili (design system)
│   │   ├── __init__.py             # Export dei componenti
│   │   ├── card.py                 # Widget contenitore card
│   │   ├── stat_badge.py           # Badge statistiche con etichetta e valore
│   │   ├── empty_state.py          # Placeholder stato vuoto con icona e messaggio
│   │   ├── section_header.py       # Intestazione sezione con titolo e azione opzionale
│   │   ├── progress_ring.py        # Indicatore anello di progresso circolare
│   │   ├── icon_widget.py          # Widget visualizzazione icone (SVG/pixmap)
│   │   └── nav_sidebar.py          # Componente barra laterale di navigazione
│   ├── tactical/
│   │   ├── map_widget.py           # MapWidget: rendering mappa tattica 2D pixel-accurate
│   │   ├── player_sidebar.py       # PlayerSidebar: stato giocatore in tempo reale (salute, armatura, armi)
│   │   ├── timeline_widget.py      # TimelineWidget: navigazione e scrubbing playback demo
│   │   └── __init__.py
│   └── __init__.py
└── themes/
    ├── cs2.qss                     # Tema CS2: estetica gaming scura con accento arancione (#D96600)
    ├── csgo.qss                    # Tema CSGO: toni blu-ardesia con accento acciaio
    └── cs16.qss                    # Tema CS 1.6: estetica retro terminale verde
```

## Architettura MVVM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MainWindow                                  │
│  ┌──────────┐  ┌─────────────────────────────────────────────────┐  │
│  │ Sidebar   │  │ QStackedWidget (13 schermate)                  │  │
│  │ (5 pul-   │  │  ┌───────────────────────────────────────────┐ │  │
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
│                │ _BackgroundWidget (wallpaper, opacita 25%)      │  │
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

## Schermate (13)

| # | Schermata | File | Descrizione |
|---|-----------|------|-------------|
| 1 | HomeScreen | `home_screen.py` | Dashboard con stato servizio, conteggio partite, progresso training, progresso parsing |
| 2 | CoachScreen | `coach_screen.py` | Interfaccia coaching AI con schede insight e pannello chat interattivo (Ollama) |
| 3 | MatchHistoryScreen | `match_history_screen.py` | Lista partite con rating HLTV 2.0 codificato per colore, emette Signal `match_selected` |
| 4 | MatchDetailScreen | `match_detail_screen.py` | Analisi partita multi-sezione: statistiche, round-by-round, grafico economia, momentum |
| 5 | PerformanceScreen | `performance_screen.py` | Analisi prestazioni: tendenze rating, statistiche per mappa, forze/debolezze, utilizzo utility |
| 6 | TacticalViewerScreen | `tactical_viewer_screen.py` | Replay mappa 2D con rendering pixel-accurate, overlay ghost AI, scansione chronovisor |
| 7 | UserProfileScreen | `user_profile_screen.py` | Visualizzazione profilo utente con modifica bio e ruolo |
| 8 | ProfileScreen | `profile_screen.py` | Gestione e configurazione profilo |
| 9 | SettingsScreen | `settings_screen.py` | Impostazioni applicazione: selezione tema, tipo/dimensione font, lingua, percorsi dati |
| 10 | WizardScreen | `wizard_screen.py` | Procedura guidata primo avvio per percorso Steam, nome giocatore, config Faceit; emette `setup_completed` |
| 11 | HelpScreen | `help_screen.py` | Documentazione utente, guide e FAQ |
| 12 | SteamConfigScreen | `steam_config_screen.py` | Integrazione Steam: configurazione percorso, rilevamento cartella demo |
| 13 | FaceitConfigScreen | `faceit_config_screen.py` | Integrazione Faceit: configurazione API key, ID giocatore |

## ViewModel (7)

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
| `UserProfileViewModel` | `user_profile_vm.py` | `profile_loaded(dict)`, `is_loading_changed(bool)`, `error_changed(str)` | Carica/salva `PlayerProfile` (bio, ruolo) con accesso DB in background |

*Nota: Il modulo Tactical contiene 3 ViewModel in un singolo file (`tactical_vm.py`) per coesione.*

## Widget

### Widget Grafici (`widgets/charts/`)

| Widget | File | Descrizione |
|--------|------|-------------|
| `RadarChartWidget` | `radar_chart.py` | Radar prestazioni multidimensionale con rendering QPainter personalizzato |
| `MomentumGraphWidget` | `momentum_chart.py` | Evoluzione momentum squadra per round, overlay duale CT/T |
| `EconomyGraphWidget` | `economy_chart.py` | Timeline economia round-by-round che mostra i livelli di acquisto |
| `RatingSparklineWidget` | `rating_sparkline.py` | Sparkline compatto inline dello storico rating con indicatore tendenza |
| `TrendGraphWidget` | `trend_chart.py` | Visualizzazione tendenze serie temporali per qualsiasi metrica tra partite |
| `UtilityBarWidget` | `utility_bar_chart.py` | Barre orizzontali di confronto utilizzo utility (utente vs baseline pro) |

### Widget Tattici (`widgets/tactical/`)

| Widget | File | Descrizione |
|--------|------|-------------|
| `MapWidget` | `map_widget.py` | Rendering mappa tattica 2D pixel-accurate con punti giocatore, overlay ghost e marcatori evento |
| `PlayerSidebar` | `player_sidebar.py` | Stato giocatore in tempo reale: salute, armatura, arma, denaro, stato vivo/morto |
| `TimelineWidget` | `timeline_widget.py` | Navigazione playback demo con scrubbing, marcatori round e indicatori momenti critici |

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
- **Fogli di stile QSS** caricati da `themes/*.qss`, con iniezione dinamica font-family/size
- **Configurazione QPalette** per widget che non rispettano QSS
- **5 font personalizzati:** Roboto, JetBrains Mono, New Hope, CS Regular, YUPIX
- **Gestione wallpaper:** cartelle wallpaper per tema, preferenza immagini verticali, renderizzati al 25% di opacita tramite `_BackgroundWidget`
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
| `QtAssetBridge` | `core/asset_bridge.py` | Singleton che carica immagini mappa come `QPixmap` con cache e fallback a scacchiera magenta/nero |
| `QtLocalizationManager` | `core/i18n_bridge.py` | Singleton (`i18n`) che fornisce `get_text(key)` con priorita JSON, fallback hardcoded, e Signal `language_changed` |
| `QtPlaybackEngine` | `core/qt_playback_engine.py` | Sottoclasse di `PlaybackEngine` che usa `QTimer` a intervallo 16ms (~60 FPS) al posto di Kivy Clock |
| `DesignTokens` | `core/design_tokens.py` | Definizioni design token (spaziatura, raggio, elevazione) per il sistema componenti Qt |
| `QSSGenerator` | `core/qss_generator.py` | Generazione programmatica di fogli di stile QSS dai design token |
| `Animation` | `core/animation.py` | Utilita di animazione condivise e helper di easing per transizioni widget |
| `Icons` | `core/icons.py` | Registro icone e caricatore asset SVG/icone per il sistema componenti |

## Note di Sviluppo

- **Dimensione minima finestra:** 1280x720 pixel
- **Larghezza sidebar:** 220px fissa, con 5 pulsanti di navigazione (Home, Coach, History, Stats, Tactical)
- **Ciclo di vita schermata:** `on_enter()` viene chiamato automaticamente quando una schermata diventa visibile; `retranslate()` viene chiamato al cambio lingua
- **Thread safety:** Tutti gli accessi DB passano attraverso Worker/QThreadPool. Non accedere mai alle sessioni SQLModel sul thread principale.
- **i18n:** 3 lingue (en, pt, it) caricate da `assets/i18n/*.json`. Il Signal `language_changed` attiva `retranslate()` su tutte le schermate registrate.
- **Spegnimento controllato:** `app.aboutToQuit` ferma il polling di AppState e spegne la console backend
- **Gate primo avvio:** Se l'impostazione `SETUP_COMPLETED` e False, l'app parte su WizardScreen invece di HomeScreen
- **Fallimento avvio backend:** Se la console backend non riesce ad avviarsi, viene mostrato un avviso `QMessageBox` ma l'app continua in modalita degradata
