> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Apps — Livello Interfaccia Utente

> **Autorita:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Panoramica

La directory `apps/` contiene tutto il codice dell'interfaccia utente del Macena CS2
Analyzer. L'unico framework UI attivo è `qt_app/` — un'applicazione desktop di produzione
costruita con PySide6 (Qt6), scelta per il suo aspetto nativo, il modello di threading
maturo (QThreadPool/QRunnable), la libreria grafica integrata (QtCharts) e l'ampio
supporto multipiattaforma.

`qt_app/` è un livello esclusivamente consumatore: condivide gli stessi servizi backend
(`backend/services/`), il livello database (`backend/storage/`) e il sistema di
configurazione (`core/config.py`), ma non scrive mai direttamente nel database.

> **Nota storica:** Un prototipo Kivy + KivyMD (`legacy_kivy/`) è servito come shell di
> sviluppo iniziale. È stato sostituito dal frontend Qt e rimosso nel marzo 2026
> (commit `4f04f06`).

## Struttura della Directory

```
apps/
├── __init__.py
├── README.md                    # Versione inglese
├── README_IT.md                 # Questo file
├── README_PT.md                 # Traduzione portoghese
│
└── qt_app/                      # Attivo PySide6 / Qt6
    ├── __init__.py
    ├── app.py                   # Punto di ingresso applicazione
    ├── main_window.py           # QMainWindow con navigazione sidebar
    │
    ├── core/                    # Infrastruttura condivisa
    │   ├── app_state.py         # Singleton AppState — poll CoachState ogni 10s
    │   ├── worker.py            # Pattern Worker (QRunnable) in background
    │   ├── theme_engine.py      # Temi QSS (CS2, CSGO, CS1.6), palette, font
    │   ├── design_tokens.py     # Definizioni design token per il sistema componenti Qt
    │   ├── qss_generator.py     # Generazione QSS programmatica dai design token
    │   ├── animation.py         # Utilità di animazione condivise
    │   ├── easing.py            # Curve di easing personalizzate
    │   ├── typography.py        # Scala tipografica e helper font
    │   ├── icons.py             # Registro icone e caricatore asset SVG
    │   ├── svg_icon_provider.py # QIconEngine basato su risorse SVG
    │   ├── i18n_bridge.py       # Localizzazione (en, pt, it) tramite JSON + fallback
    │   ├── sound.py             # Helper riproduzione effetti sonori
    │   ├── match_utils.py       # Funzioni utility a livello partita per il livello UI
    │   ├── widgets_helpers.py   # Funzioni helper Qt widget generiche
    │   ├── web_bridge.py        # Bridge Python↔JavaScript per le web view integrate
    │   └── qt_playback_engine.py # Playback demo basato su QTimer
    │
    ├── screens/                 # Un QWidget per schermata (livello View) — 15 schermate
    │   ├── home_screen.py           # Dashboard — stato servizio, conteggio partite, training
    │   ├── coach_screen.py          # AI Coach — interfaccia chat, coaching insights
    │   ├── match_history_screen.py  # Lista partite con ricerca e filtri
    │   ├── match_detail_screen.py   # Analisi singola partita (round, economia, eventi)
    │   ├── performance_screen.py    # Statistiche giocatore e tendenze
    │   ├── tactical_viewer_screen.py # Visualizzatore mappa 2D con controlli playback
    │   ├── pro_comparison_screen.py # Analisi comparativa utente vs giocatore pro
    │   ├── pro_player_detail_screen.py # Vista profilo giocatore pro
    │   ├── wizard_screen.py         # Configurazione iniziale (percorso Steam, nome giocatore)
    │   ├── settings_screen.py       # Impostazioni app (tema, font, lingua, percorsi)
    │   ├── user_profile_screen.py   # Editor profilo utente
    │   ├── profile_screen.py        # Panoramica profilo giocatore
    │   ├── steam_config_screen.py   # Impostazioni integrazione Steam
    │   ├── faceit_config_screen.py  # Impostazioni integrazione FACEIT
    │   ├── help_screen.py           # Visualizzatore documentazione aiuto
    │   └── placeholder.py           # Factory per schermate stub
    │
    ├── viewmodels/              # Livello ViewModel (sottoclassi QObject)
    │   ├── coach_vm.py              # CoachViewModel — orchestra le query di coaching
    │   ├── coaching_chat_vm.py      # Cronologia chat e gestione messaggi
    │   ├── focus_insight_vm.py      # ViewModel dettaglio insight coaching focalizzato
    │   ├── match_history_vm.py      # Recupero dati e filtraggio lista partite
    │   ├── match_detail_vm.py       # Caricamento dati singola partita
    │   ├── performance_vm.py        # Aggregazione statistiche giocatore
    │   ├── pro_comparison_vm.py     # Dati e punteggio comparativo pro
    │   ├── pro_player_detail_vm.py  # Caricamento dati profilo giocatore pro
    │   ├── tactical_vm.py           # Dati tattici e stato playback
    │   └── user_profile_vm.py       # Operazioni CRUD profilo utente
    │
    ├── widgets/                 # Libreria widget riutilizzabili
    │   ├── toast.py             # Overlay notifiche toast
    │   ├── skeleton.py          # Widget placeholder di caricamento skeleton
    │   ├── charts/              # Visualizzazioni QtCharts / QPainter
    │   │   ├── economy_chart.py     # Economia round per round (grafico a barre QtCharts)
    │   │   ├── mini_sparkline.py    # Sparkline compatta (QPainter, senza assi)
    │   │   └── momentum_chart.py    # Delta K-D momentum (grafico area QtCharts)
    │   ├── coaching/            # Namespace widget coaching (riservato; widget rimossi PR #32)
    │   ├── components/          # Componenti UI riutilizzabili (design system)
    │   │   ├── __init__.py          # Export dei componenti
    │   │   ├── card.py              # Widget contenitore card
    │   │   ├── stat_badge.py        # Badge statistiche con etichetta e valore
    │   │   ├── empty_state.py       # Placeholder stato vuoto con icona e messaggio
    │   │   ├── section_header.py    # Intestazione sezione con titolo e azione opzionale
    │   │   ├── progress_ring.py     # Indicatore anello di progresso circolare
    │   │   ├── icon_widget.py       # Widget visualizzazione icone (SVG/pixmap)
    │   │   └── nav_sidebar.py       # Componente barra laterale di navigazione
    │   └── tactical/            # Componenti visualizzatore tattico
    │       ├── map_widget.py        # Renderer mappa 2D (QGraphicsView)
    │       ├── player_sidebar.py    # Pannello info giocatore
    │       └── timeline_widget.py   # Scrubber timeline round
    │
    ├── web/                     # Sub-app TypeScript (integrate via QWebEngineView)
    │   ├── coach-chat/          # App React chat coaching
    │   ├── match-detail/        # App React dettaglio partita
    │   ├── tactical-viewer/     # App React visualizzatore tattico
    │   └── shared/              # Utilità TypeScript condivise
    │
    └── themes/                  # Fogli di stile QSS
        ├── cs2.qss              # Tema CS2 (accento arancione, superficie scura)
        ├── csgo.qss             # Tema CS:GO (accento blu acciaio)
        └── cs16.qss             # Tema CS 1.6 (accento verde, retro)
```

## Architettura MVVM

L'app Qt segue il pattern **Model-View-ViewModel**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        View (Screen)                            │
│  - Sottoclasse QWidget, puro layout e visualizzazione           │
│  - Si connette ai segnali del ViewModel in on_enter()           │
│  - NON importa MAI moduli backend o modelli database            │
│  - Chiama metodi del ViewModel per avviare operazioni dati      │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Qt Signals (result, error, finished)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ViewModel (QObject)                          │
│  - Possiede logica business e stato per uno screen              │
│  - Avvia Worker (QRunnable) per query database                  │
│  - Emette Signals tipizzati con risultati (auto-marshal verso UI)│
│  - Puo leggere segnali AppState per dati backend live           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Worker (thread in background)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Model (SQLModel / DB)                         │
│  - backend/storage/database.py (singleton get_db_manager)       │
│  - backend/storage/db_models.py (classi ORM SQLModel)           │
│  - Sola lettura dalla prospettiva UI                            │
└─────────────────────────────────────────────────────────────────┘
```

**Contratto chiave:** le View non chiamano mai `get_db_manager()` e non importano
nulla da `backend/storage/`. Tutti i dati fluiscono attraverso i ViewModel.

## Punti di Ingresso

### Primario (Qt)

```bash
# Dalla root del progetto, con venv attivato:
python -m Programma_CS2_RENAN.apps.qt_app.app
```

La sequenza di avvio in `app.py`:
1. Scaling High-DPI configurato
2. `QApplication` creata, versione letta dai metadati del pacchetto
3. Handler di shutdown connesso (`aboutToQuit`)
4. `ThemeEngine` inizializzato — font personalizzati registrati, tema applicato
5. `MainWindow` creata con navigazione sidebar
6. Tutti i 15 screen istanziati e registrati nel `QStackedWidget`
7. Gate prima esecuzione: mostra `WizardScreen` se setup non completato, altrimenti `HomeScreen`
8. Console backend avviata (`get_console().boot()`)
9. Polling `AppState` avviato (intervallo 10 secondi)

### Bundle PyInstaller

L'applicazione puo essere lanciata anche da un eseguibile costruito con PyInstaller.
Vedere la directory `packaging/` per il file `.spec` e le istruzioni di build.

## Pattern Condivisi

### Pattern Worker (`core/worker.py`)

Tutte le operazioni in background usano la classe `Worker`, che incapsula un callable
in un `QRunnable` ed emette risultati tramite Signals:

```python
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from PySide6.QtCore import QThreadPool

worker = Worker(some_db_query, arg1, arg2)
worker.signals.result.connect(self._on_data_loaded)
worker.signals.error.connect(self._on_error)
QThreadPool.globalInstance().start(worker)
```

Questo pattern garantisce che tutto il lavoro pesante venga eseguito fuori dal thread principale senza bloccare il loop di eventi Qt.

### AppState (`core/app_state.py`)

Il singleton `AppState` interroga la riga database `CoachState` ogni 10 secondi ed
emette segnali solo-su-cambio. Gli screen si connettono a questi nel loro metodo
`on_enter()`:

- `service_active_changed(bool)` — heartbeat daemon backend
- `coach_status_changed(str)` — testo stato ingestione/training
- `parsing_progress_changed(float)` — progresso parsing demo (0.0-1.0)
- `belief_confidence_changed(float)` — livello confidenza modello
- `total_matches_changed(int)` — partite totali ingerite
- `training_changed(dict)` — bundle epoca, loss, ETA
- `notification_received(str, str)` — severita + messaggio per display toast

### Temi (`core/theme_engine.py`)

Tre temi integrati rispecchiano le ere del franchise Counter-Strike:

| Tema | Colore Accento | Superficie |
|------|---------------|------------|
| CS2 | Arancione (`#D96600`) | Carbone scuro |
| CSGO | Blu acciaio (`#617D8C`) | Grigio ardesia |
| CS 1.6 | Verde (`#4DB050`) | Oliva scuro |

I temi vengono applicati tramite fogli di stile QSS (`themes/*.qss`) piu una `QPalette`
per i widget non stilizzati. Font personalizzati (Roboto, JetBrains Mono, CS Regular,
YUPIX, New Hope) vengono registrati all'avvio.

### Localizzazione (`core/i18n_bridge.py`)

Tre lingue sono supportate: Inglese, Portoghese, Italiano. Ordine di risoluzione stringhe:
1. File di traduzione JSON (`assets/i18n/{lang}.json`)
2. Dizionario di traduzione hardcoded (lingua corrente)
3. Fallback inglese
4. Chiave grezza (se nessuna corrispondenza)

I cambi di lingua emettono un segnale `language_changed`. Gli screen implementano
`retranslate()` per aggiornare le loro etichette dinamicamente.

## Linee Guida per lo Sviluppo

1. **Il threading in background è obbligatorio** — non bloccare mai il thread principale
   con query DB, chiamate di rete o I/O file. Usare `Worker` da `core/worker.py`.
2. **Connettersi ai segnali `AppState` in `on_enter()`** — questo è il bus dati live
   dal backend. Non interrogare il database dagli screen.
3. **I grafici usano QtCharts** (non matplotlib) — più leggeri, integrazione Qt nativa,
   temi consistenti tramite QSS.
4. **Localizzazione** — tutte le stringhe visibili all'utente devono passare per
   `i18n_bridge.get_text(key)`. Non inserire mai testo hardcoded nel codice degli screen.
5. **Temi** — usare `ThemeEngine.get_color(slot)` per i colori e non usare mai valori
   hex hardcoded. Tutte le costanti visive risiedono in `theme_engine.py` o nei file QSS.
6. **Gli screen non si importano tra loro** — la navigazione è gestita da
   `MainWindow.switch_screen()`. La comunicazione inter-screen avviene tramite
   segnali o `AppState`.
7. **Ogni screen deve implementare `on_enter()`** — chiamato da `MainWindow` quando
   lo screen diventa visibile. Usarlo per aggiornare i dati e connettere i segnali.
8. **Implementare `retranslate()`** — chiamato quando l'utente cambia lingua.
   Aggiornare tutte le etichette visibili dall'utente da `i18n_bridge`.

## Note di Sviluppo

- L'app Qt richiede **PySide6 >= 6.5** e **Python 3.10+**.
- I fogli di stile QSS sono in `qt_app/themes/` — un file per tema. Modificare questi
  per cambiamenti visivi; non inserire stili inline nel codice Python.
- La factory `placeholder.py` genera schermate stub che mostrano un messaggio "Coming Soon" per le schermate in sviluppo.
- `MainWindow` usa un `QStackedLayout` con tre livelli: sfondo wallpaper (inferiore),
  stack screen (centrale) e notifiche toast (superiore).
- La console backend (`get_console().boot()`) puo fallire senza rompere l'UI.
  Viene mostrata una finestra di avviso e l'applicazione continua in modalita degradata.

## Conteggio File

- `qt_app/`: 78 file Python in `core/`, `screens/`, `viewmodels/`, `widgets/` + 3 temi QSS + 3 sub-app web incorporate
