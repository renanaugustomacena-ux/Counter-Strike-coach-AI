> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Apps — Livello Interfaccia Utente

> **Autorita:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Panoramica

La directory `apps/` contiene tutto il codice dell'interfaccia utente del Macena CS2
Analyzer. Due framework UI coesistono come parte di una strategia di migrazione deliberata:

- **Fase 0 (Legacy):** `desktop_app/` era il prototipo originale costruito con Kivy +
  KivyMD. Ha servito come shell di prototipazione rapida durante lo sviluppo iniziale.
  Non vengono aggiunte nuove funzionalita qui; esiste solo come riferimento e per i
  componenti non ancora portati.

- **Fase 2+ (Attivo):** `qt_app/` e l'UI desktop di produzione costruita con PySide6
  (Qt6). Tutti i nuovi screen, widget e funzionalita sono destinati esclusivamente a
  questo framework. Qt e stato scelto per il suo aspetto nativo, il modello di
  threading maturo (QThreadPool/QRunnable), la libreria di grafici integrata (QtCharts)
  e l'ampio supporto multipiattaforma.

Entrambi i framework condividono gli stessi servizi backend (`backend/services/`), il
livello database (`backend/storage/`) e il sistema di configurazione (`core/config.py`).
Il livello UI e strettamente un consumatore dei dati backend — non scrive mai
direttamente nel database.

## Struttura della Directory

```
apps/
├── __init__.py
├── README.md                    # Versione inglese
├── README_IT.md                 # Questo file
├── README_PT.md                 # Traduzione portoghese
├── spatial_debugger.py          # Strumento standalone Kivy per validazione coordinate mappa
│
├── desktop_app/                 # Legacy Kivy + KivyMD (Fase 0)
│   ├── __init__.py
│   ├── layout.kv                # Layout root KV (60 KB, 13 screen)
│   ├── theme.py                 # Costanti palette Kivy e colori rating
│   ├── ghost_pixel.py           # Widget overlay mirino
│   ├── player_sidebar.py        # Barra laterale info giocatore (Kivy)
│   ├── timeline.py              # Scrubber timeline round (Kivy)
│   ├── widgets.py               # Widget Kivy condivisi (card, pulsanti)
│   ├── wizard_screen.py         # Wizard configurazione iniziale
│   ├── help_screen.py           # Schermata aiuto / informazioni
│   ├── match_history_screen.py  # Browser lista partite
│   ├── match_detail_screen.py   # Dettaglio singola partita
│   ├── performance_screen.py    # Dashboard statistiche giocatore
│   ├── tactical_map.py          # Renderer mappa tattica 2D
│   ├── tactical_viewer_screen.py # Schermata analisi tattica
│   ├── coaching_chat_vm.py      # ViewModel chat coaching
│   ├── tactical_viewmodels.py   # ViewModel analisi tattica
│   └── data_viewmodels.py       # ViewModel recupero dati
│
└── qt_app/                      # Attivo PySide6 / Qt6 (Fase 2+)
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
    │   ├── animation.py         # Utilita di animazione condivise e helper di easing
    │   ├── icons.py             # Registro icone e caricatore asset SVG/icone
    │   ├── i18n_bridge.py       # Localizzazione (en, pt, it) tramite JSON + fallback
    │   ├── asset_bridge.py      # Caricatore immagini mappa (QPixmap), texture fallback
    │   └── qt_playback_engine.py # Playback demo basato su QTimer (sostituisce Kivy Clock)
    │
    ├── screens/                 # Un QWidget per schermata (livello View)
    │   ├── home_screen.py       # Dashboard — stato servizio, conteggio partite, training
    │   ├── coach_screen.py      # AI Coach — interfaccia chat, coaching insights
    │   ├── match_history_screen.py  # Lista partite con ricerca e filtri
    │   ├── match_detail_screen.py   # Analisi singola partita (round, economia, eventi)
    │   ├── performance_screen.py    # Statistiche giocatore e tendenze
    │   ├── tactical_viewer_screen.py # Visualizzatore mappa 2D con controlli playback
    │   ├── wizard_screen.py     # Configurazione iniziale (percorso Steam, nome giocatore)
    │   ├── settings_screen.py   # Impostazioni app (tema, font, lingua, percorsi)
    │   ├── user_profile_screen.py   # Editor profilo utente
    │   ├── profile_screen.py    # Panoramica profilo giocatore
    │   ├── steam_config_screen.py   # Impostazioni integrazione Steam
    │   ├── faceit_config_screen.py  # Impostazioni integrazione FACEIT
    │   ├── help_screen.py       # Visualizzatore documentazione aiuto
    │   └── placeholder.py       # Factory placeholder per screen non portati
    │
    ├── viewmodels/              # Livello ViewModel (sottoclassi QObject)
    │   ├── coach_vm.py          # CoachViewModel — orchestra le query di coaching
    │   ├── coaching_chat_vm.py  # Cronologia chat e gestione messaggi
    │   ├── match_history_vm.py  # Recupero dati e filtraggio lista partite
    │   ├── match_detail_vm.py   # Caricamento dati singola partita
    │   ├── performance_vm.py    # Aggregazione statistiche giocatore
    │   ├── tactical_vm.py       # Dati tattici e stato playback
    │   └── user_profile_vm.py   # Operazioni CRUD profilo utente
    │
    ├── widgets/                 # Libreria widget riutilizzabili
    │   ├── toast.py             # Overlay notifiche toast
    │   ├── skeleton.py          # Widget placeholder di caricamento skeleton
    │   ├── charts/              # Visualizzazioni basate su QtCharts
    │   │   ├── radar_chart.py       # Radar abilita (grafico spider 6 assi)
    │   │   ├── economy_chart.py     # Grafico economia round per round
    │   │   ├── momentum_chart.py    # Timeline momentum squadra
    │   │   ├── rating_sparkline.py  # Mini-grafico rating inline
    │   │   ├── trend_chart.py       # Linee di tendenza multi-partita
    │   │   └── utility_bar_chart.py # Grafico a barre uso utility
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
    └── themes/                  # Fogli di stile QSS
        ├── cs2.qss              # Tema CS2 (accento arancione, superficie scura)
        ├── csgo.qss             # Tema CS:GO (accento blu acciaio)
        └── cs16.qss             # Tema CS 1.6 (accento verde, retro)
```

## Confronto tra Framework

| Aspetto | `desktop_app/` (Kivy) | `qt_app/` (PySide6) |
|---------|----------------------|----------------------|
| **Stato** | Legacy (Fase 0) — congelato | **Attivo** (Fase 2+) |
| **Layout** | Linguaggio KV (`layout.kv`) | Codice Python (QLayouts) |
| **Threading** | `threading.Thread` + `Clock.schedule_once` | `Worker` (QRunnable) + Signals |
| **Grafici** | matplotlib (pesante) | QtCharts (nativo, leggero) |
| **Temi** | `theme.py` (proprieta Kivy) | `ThemeEngine` + fogli di stile QSS |
| **i18n** | `LocalizationManager` (Kivy EventDispatcher) | `QtLocalizationManager` (QObject + Signal) |
| **Asset** | `AssetAuthority` (Kivy Texture) | `QtAssetBridge` (QPixmap) |
| **Playback** | `PlaybackEngine` + Kivy Clock | `QtPlaybackEngine` + QTimer |
| **Screen** | 13 (in `layout.kv`) | 14 (file `.py` individuali) |
| **File Python** | 16 | 56 |

## Architettura MVVM

Entrambe le UI seguono il pattern **Model-View-ViewModel**. L'implementazione Qt e il
riferimento canonico:

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
6. Tutti i 14 screen istanziati e registrati nel `QStackedWidget`
7. Gate prima esecuzione: mostra `WizardScreen` se setup non completato, altrimenti `HomeScreen`
8. Console backend avviata (`get_console().boot()`)
9. Polling `AppState` avviato (intervallo 10 secondi)

### Bundle PyInstaller

L'applicazione puo essere lanciata anche da un eseguibile costruito con PyInstaller.
Vedere la directory `packaging/` per il file `.spec` e le istruzioni di build.

### Strumenti Standalone

- **`spatial_debugger.py`** — Widget debug basato su Kivy per validare le trasformazioni
  delle coordinate mappa. Mostra un'immagine mappa con overlay di punti di riferimento
  e lettura coordinate cursore-mondo. Utile durante la calibrazione dei dati spaziali.

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

Questo sostituisce il pattern Kivy di `Thread(target=fn).start()` seguito da
`Clock.schedule_once(callback)`.

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

1. **Tutto il nuovo lavoro UI va in `qt_app/`** — non aggiungere funzionalita a `desktop_app/`
2. **Nessun import Kivy nel codice Qt** — `asset_bridge.py`, `i18n_bridge.py`,
   `theme_engine.py` usano solo Qt e stdlib. Gli import cross-framework sono vietati.
3. **Il threading in background e obbligatorio** — non bloccare mai il thread principale
   con query DB, chiamate di rete o I/O file. Usare `Worker` da `core/worker.py`.
4. **Connettersi ai segnali `AppState` in `on_enter()`** — questo e il bus dati live
   dal backend. Non interrogare il database dagli screen.
5. **I grafici usano QtCharts** (non matplotlib) — piu leggeri, integrazione Qt nativa,
   temi consistenti tramite QSS.
6. **Localizzazione** — tutte le stringhe visibili all'utente devono passare per
   `i18n_bridge.get_text(key)`. Non inserire mai testo di visualizzazione hardcoded
   nel codice degli screen.
7. **Temi** — usare `ThemeEngine.get_color(slot)` per i colori e non usare mai valori
   hex hardcoded. Tutte le costanti visive risiedono in `theme_engine.py` o nei file QSS.
8. **Gli screen non si importano tra loro** — la navigazione e gestita da
   `MainWindow.switch_screen()`. La comunicazione inter-screen avviene tramite
   segnali o `AppState`.
9. **Ogni screen deve implementare `on_enter()`** — chiamato da `MainWindow` quando
   lo screen diventa visibile. Usarlo per aggiornare i dati e connettere i segnali.
10. **Implementare `retranslate()`** — chiamato quando l'utente cambia lingua.
    Aggiornare tutte le etichette visibili dall'utente da `i18n_bridge`.

## Note di Sviluppo

- L'app Qt richiede **PySide6 >= 6.5** e **Python 3.10+**.
- I fogli di stile QSS sono in `qt_app/themes/` — un file per tema. Modificare questi
  per cambiamenti visivi; non inserire stili inline nel codice Python.
- La factory `placeholder.py` genera screen stub per le pagine non ancora portate
  da Kivy. Questi mostrano un messaggio "Coming Soon" e vengono progressivamente sostituiti.
- `MainWindow` usa un `QStackedLayout` con tre livelli: sfondo wallpaper (inferiore),
  stack screen (centrale) e notifiche toast (superiore).
- La console backend (`get_console().boot()`) puo fallire senza rompere l'UI.
  Viene mostrata una finestra di avviso e l'applicazione continua in modalita degradata.
- `spatial_debugger.py` e l'unico file in `apps/` che importa Kivy direttamente.
  E uno strumento di debug standalone e non viene caricato dall'applicazione Qt.

## Conteggio File

- `desktop_app/`: 16 file Python + 1 layout KV (legacy, congelato)
- `qt_app/`: 56 file Python distribuiti in `core/`, `screens/`, `viewmodels/`, `widgets/` + 3 temi QSS
- Root `apps/`: 1 strumento standalone (`spatial_debugger.py`)
