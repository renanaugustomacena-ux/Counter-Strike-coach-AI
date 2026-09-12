> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Apps — Livello Interfaccia Utente

> **Autorità:** Rule 3 (Frontend & UX) | **Skill:** `/frontend-ux-review`

## Panoramica

La directory `apps/` contiene tutto il codice dell'interfaccia utente del Macena CS2 Analyzer.
L'unico framework UI attivo è `qt_app/` — un'applicazione desktop di produzione costruita con PySide6
(Qt6). È stata scelta per il suo aspetto nativo, il modello di threading maturo (QThreadPool/QRunnable),
il potente painting di widget custom (QPainter) e l'ampio supporto multipiattaforma.

`qt_app/` è un livello strettamente consumatore: condivide gli stessi servizi backend (`backend/services/`),
il livello database (`backend/storage/`) e il sistema di configurazione (`core/config.py`), e limita le
scritture nel database ai record di proprietà dell'utente (profilo, impostazioni, flag di lettura notifiche).

> **Nota storica:** Un prototipo Kivy + KivyMD (`legacy_kivy/`) è servito come shell di
> sviluppo iniziale. È stato sostituito dal frontend Qt e rimosso nel giugno 2026
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
    ├── app.py                   # Punto di ingresso dell'applicazione
    ├── main_window.py           # QMainWindow con navigazione sidebar
    │
    ├── core/                    # Infrastruttura condivisa
    │   ├── app_state.py         # Singleton AppState — poll CoachState ogni 10s
    │   ├── worker.py            # Pattern Worker (QRunnable) in background
    │   ├── theme_engine.py      # Theming guidato da token (CS2, CSGO, CS1.6): render QSS, QPalette, font, wallpaper
    │   ├── design_tokens.py     # Definizioni design token per il sistema componenti Qt
    │   ├── qss_generator.py     # Render di themes/base.qss.template con sostituzione token
    │   ├── animation.py         # Utilità di animazione condivise
    │   ├── easing.py            # Curve di easing personalizzate
    │   ├── typography.py        # Scala tipografica e helper font
    │   ├── icons.py             # Facade IconProvider — sprite SVG, fallback QPainterPath
    │   ├── svg_icon_provider.py # QIconEngine basato su risorse SVG
    │   ├── i18n_bridge.py       # Localizzazione (en, pt, it) tramite JSON + fallback
    │   ├── sound.py             # Helper riproduzione effetti sonori
    │   ├── match_utils.py       # Funzioni utility a livello partita per il livello UI
    │   ├── widgets_helpers.py   # Funzioni helper Qt widget generiche
    │   ├── web_bridge.py        # Bridge Python↔JavaScript per le web view integrate
    │   ├── qt_playback_engine.py # Playback demo basato su QTimer
    │   └── tray.py              # Icona system tray + menu (chiudi-nel-tray, scorciatoia AI Coach)
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
    │   └── placeholder.py           # Factory placeholder (tutte le voci sostituite da schermate reali)
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
    │   ├── charts/              # Visualizzazioni QPainter (QtCharts rimosso — solo GPL)
    │   │   ├── economy_chart.py     # Barre economia round per round (QPainter)
    │   │   ├── mini_sparkline.py    # Sparkline compatta (QPainter, senza assi)
    │   │   ├── momentum_chart.py    # Grafico ad area delta K-D momentum (QPainter)
    │   │   ├── radar_chart.py       # Radar delle skill a N assi (QPainter)
    │   │   ├── rating_sparkline.py  # Tendenza rating con baseline (QPainter)
    │   │   └── utility_bar_chart.py # Barre uso utility (QPainter)
    │   ├── coaching/            # Widget coaching (ChatPanel integrata in CoachScreen)
    │   ├── components/          # Componenti UI riutilizzabili (design system) — 26 moduli
    │   │   ├── __init__.py          # Export dei componenti
    │   │   ├── card.py              # Widget contenitore card (5 varianti di profondità)
    │   │   ├── db_record_card.py    # Eco mono della riga DB (tabella · colonna · valore)
    │   │   ├── delta_chip.py        # Pillola delta relativa al benchmark
    │   │   ├── drivers_list.py      # Righe di contributo con segno (cosa ha mosso una statistica)
    │   │   ├── empty_state.py       # Placeholder stato vuoto con icona e messaggio
    │   │   ├── filter_chip.py       # Pillola filtro attivabile
    │   │   ├── focus_insight.py     # Card focus insight (home screen)
    │   │   ├── hero_stats_strip.py  # Striscia orizzontale di metriche hero
    │   │   ├── icon_widget.py       # Widget visualizzazione icone (SVG/pixmap)
    │   │   ├── last_match_hero.py   # Card hero ultima partita (home screen)
    │   │   ├── map_tile.py          # Tile statistiche per mappa con accento win-rate
    │   │   ├── match_mini_card.py   # Card riassunto partita compatta
    │   │   ├── match_row_card.py    # Card riga partita estesa
    │   │   ├── metric_bar_row.py    # Etichetta + barra metrica orizzontale + valore
    │   │   ├── mini_link_card.py    # Piccola card di navigazione a link correlati
    │   │   ├── mono_footer.py       # Riga footer mono di provenienza/stato
    │   │   ├── nav_sidebar.py       # Componente barra laterale di navigazione comprimibile
    │   │   ├── numbered_step.py     # Riga passo 01/02/03 in mono accentato
    │   │   ├── pro_badge.py         # Pillola PRO/tier per le superfici dei giocatori pro
    │   │   ├── progress_ring.py     # Indicatore anello di progresso circolare
    │   │   ├── section_header.py    # Intestazione sezione con titolo e azione opzionale
    │   │   ├── stat_badge.py        # Badge statistiche con etichetta e valore
    │   │   ├── status_chip.py       # Pillola di stato colorata con etichetta di testo
    │   │   ├── stepper.py           # Indicatore di avanzamento a passi
    │   │   ├── tip_box.py           # Box suggerimento con bordo accentato
    │   │   └── toggle_switch.py     # Interruttore booleano animato
    │   └── tactical/            # Componenti visualizzatore tattico
    │       ├── _paint_utils.py      # Helper QPainter condivisi (mappa + timeline)
    │       ├── map_widget.py        # Renderer mappa 2D (QPainter, TacticalMapWidget)
    │       ├── player_sidebar.py    # Pannello info giocatore
    │       └── timeline_widget.py   # Scrubber timeline round
    │
    ├── web/                     # Sub-app TypeScript (integrate via QWebEngineView)
    │   ├── coach-chat/          # App React chat coaching
    │   ├── match-detail/        # App React dettaglio partita
    │   ├── tactical-viewer/     # App React visualizzatore tattico
    │   └── shared/              # Utilità TypeScript condivise
    │
    └── themes/                  # Sorgente QSS
        └── base.qss.template    # Foglio di stile a sostituzione token — unica sorgente QSS
                                 # (renderizzato per tema da core/qss_generator.py)
```

## Architettura MVVM

L'app Qt segue il pattern **Model-View-ViewModel**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        View (Screen)                            │
│  - Sottoclasse QWidget, puro layout e visualizzazione           │
│  - Si connette ai segnali del ViewModel in on_enter()           │
│  - NON importa MAI moduli backend o modelli database            │
│  - Chiama metodi del ViewModel per avviare operazioni sui dati  │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Qt Signals (result, error, finished)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ViewModel (QObject)                          │
│  - Possiede logica business e stato per uno screen              │
│  - Avvia Worker (QRunnable) per query database                  │
│  - Emette Signals tipizzati con risultati (auto-marshal verso UI)│
│  - Può leggere segnali AppState per dati backend live           │
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

# Oppure tramite lo script launcher alla root del repository (usa .venv, pulisce bytecode obsoleto):
./launch.sh
```

La sequenza di avvio in `app.py`:
1. Scaling High-DPI configurato
2. `QApplication` creata, versione letta dai metadati del pacchetto
3. Guardia a istanza singola (`lifecycle.ensure_single_instance()`) — mostra un dialogo di avviso ed esce se un'altra istanza è già in esecuzione
4. `ThemeEngine` creato e font personalizzati registrati; viene mostrata una splash screen tematizzata (colori dai design token del tema attivo)
5. Handler di shutdown controllato connesso (`aboutToQuit`)
6. Tema e impostazioni font persistite applicati
7. `MainWindow` creata con navigazione sidebar
8. Tutte le 15 schermate istanziate e registrate nel `QStackedWidget`; segnali inter-schermata collegati (selezione partita → dettaglio, wizard → home, momenti salienti → visualizzatore tattico, confronto pro → dettaglio pro)
9. Gate primo avvio: mostra `WizardScreen` se il setup non è completato, altrimenti `HomeScreen`
10. Console backend avviata (`get_console().boot()`) e demone Session Engine lanciato
11. Modello linguistico SBERT verificato (download al primo avvio, con progresso nella splash)
12. System tray costruita (`build_tray`); se disponibile, `setQuitOnLastWindowClosed(False)` abilita il comportamento chiudi-nel-tray
13. Polling `AppState` avviato (intervallo 10 secondi)

### Bundle PyInstaller

L'applicazione può essere lanciata anche da un eseguibile costruito con PyInstaller.
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
emette segnali solo-su-cambio. Le schermate si connettono a questi nel loro metodo
`on_enter()`:

- `service_active_changed(bool)` — heartbeat demone backend
- `coach_status_changed(str)` — testo stato ingestione/training
- `parsing_progress_changed(float)` — progresso parsing demo (0.0-1.0)
- `belief_confidence_changed(float)` — livello confidenza modello
- `total_matches_changed(int)` — partite totali ingerite
- `training_changed(dict)` — bundle epoca, loss, ETA
- `notification_received(str, str)` — severità + messaggio per display toast

### Temi (`core/theme_engine.py`)

Tre temi integrati rispecchiano le ere del franchise Counter-Strike:

| Tema | Colore Accento | Superficie |
|------|---------------|------------|
| CS2 | Arancione tattico (`#FF6A00`) | Blu navy scuro (`#0B1628`) |
| CSGO | Blu acciaio (`#617D8C`) | Ardesia scuro (`#1A1C21`) |
| CS 1.6 | Verde (`#4DB04F`) | Verde scuro (`#121A12`) |

Sia il QSS (renderizzato da `themes/base.qss.template` tramite `core/qss_generator.py`)
sia la `QPalette` per i widget non stilizzati derivano dagli stessi design token per tema
(`core/design_tokens.py`, generati da `design/tokens/design-tokens.json`).
I font personalizzati (Roboto, JetBrains Mono, CS Regular, YUPIX, New Hope) vengono
registrati all'avvio, più uno stack display auto-scansionato da `assets/fonts/` (Space Grotesk, Inter).

### Localizzazione (`core/i18n_bridge.py`)

Tre lingue sono supportate: Inglese, Portoghese, Italiano. Ordine di risoluzione stringhe:
1. File di traduzione JSON (`assets/i18n/{lang}.json`)
2. Dizionario di traduzione hardcoded (lingua corrente)
3. Fallback inglese
4. Default fornito dal chiamante (se specificato)
5. Chiave grezza (se nessuna corrispondenza)

I cambi di lingua emettono un segnale `language_changed`. Le schermate implementano
`retranslate()` per aggiornare le loro etichette dinamicamente.

## Linee Guida per lo Sviluppo

1. **Il threading in background è obbligatorio** — non bloccare mai il thread principale
   con query DB, chiamate di rete o I/O file. Usare `Worker` da `core/worker.py`.
2. **Connettersi ai segnali `AppState` in `on_enter()`** — questo è il bus dati live
   dal backend. Non interrogare il database dalle schermate.
3. **I grafici sono widget QPainter custom** (non matplotlib, e non QtCharts — quest'ultimo
   è solo GPL ed è stato rimosso per conformità di licenza) — leggeri, tematizzati via token,
   protetti da un test di guardia sulla licenza in `tests/test_charts.py`.
4. **Localizzazione** — tutte le stringhe visibili all'utente devono passare per
   `i18n_bridge.get_text(key)`. Non inserire mai testo hardcoded nel codice delle schermate.
5. **Temi** — usare i campi di `design_tokens.get_tokens()` per i colori e non usare mai
   valori hex hardcoded. I token sono generati da `design/tokens/design-tokens.json`;
   il template QSS e la QPalette derivano dalla stessa istanza `DesignTokens`.
6. **Le schermate non si importano tra loro** — la navigazione è gestita da
   `MainWindow.switch_screen()`. La comunicazione inter-schermata avviene tramite
   segnali o `AppState`.
7. **Ogni schermata deve implementare `on_enter()`** — chiamato da `MainWindow` quando
   la schermata diventa visibile. Usarlo per aggiornare i dati e connettere i segnali.
8. **Implementare `retranslate()`** — chiamato quando l'utente cambia lingua.
   Aggiornare tutte le etichette visibili dall'utente da `i18n_bridge`.

## Note di Sviluppo

- L'app Qt richiede **PySide6 6.11.0** (fissato in `requirements.txt`) e **Python 3.11+**.
- L'unica sorgente QSS è `qt_app/themes/base.qss.template`; i vecchi file `.qss` per tema
  sono stati rimossi (commit `73ec5ed`, `5ce891b`). Le modifiche visive passano attraverso
  i design token e il template; non usare stili inline nel codice Python.
- La factory `placeholder.py` crea semplici schermate placeholder con nome (titolo centrato + descrizione). All'avvio ogni voce placeholder è sovrascritta da un'implementazione reale; la factory rimane come rete di sicurezza per la registrazione.
- `MainWindow` stratifica l'area contenuto con un `QStackedLayout` (modalità `StackAll`):
  sfondo (wallpaper opzionale al 15% di opacità più un motivo griglia tattica sottile)
  sotto lo stack di schermate trasparenti. Le notifiche toast fluttuano come overlay
  figlio separato in alto a destra, fuori dallo stacked layout.
- La console backend (`get_console().boot()`) può fallire senza rompere la UI.
  Viene mostrata una finestra di avviso e l'applicazione continua in modalità degradata.

## Conteggio File

- `qt_app/`: 93 file Python (`app.py`, `main_window.py`, `core/`, `screens/`, `viewmodels/`, `widgets/`) + 1 template QSS (`themes/base.qss.template`) + 3 sub-app web integrate
