# `apps/qt_app/widgets/tactical/` — Widget del Tactical Viewer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Widget custom esclusivi della schermata **Tactical Viewer**. Renderizzano il replay 2D della mappa, la sidebar live dei giocatori e lo scrubber della timeline. Nessuno di questi è riutilizzabile altrove — sono fortemente accoppiati allo stato del playback, alle proiezioni della Ghost AI e agli highlight del chronovisor.

## Inventario dei file

| File | Widget | Scopo |
|------|--------|---------|
| `__init__.py` | — | Marker di package. |
| `map_widget.py` | `MapWidget` | La "Living Map" — renderer 2D accelerato in GPU per posizioni dei giocatori, traiettorie delle granate, marker delle kill, proiezioni della Ghost AI. Si abbona a `TacticalPlaybackViewModel.tickAdvanced`. |
| `player_sidebar.py` | `PlayerSidebar` | Roster dei giocatori a due squadre con visualizzazione live di HP / armatura / arma / economia. Usa il pooling dei widget (riuso degli oggetti) così il refresh per tick non alloca. |
| `timeline_widget.py` | `TimelineWidget` | Scrubber interattivo con marker degli eventi codificati a colori (kill, plant, defuse, transizioni di round). Click e drag per posizionare il cursore. |

## Architettura

```
TacticalViewerScreen
    |
    +-- MapWidget         <-- TacticalPlaybackViewModel.tickAdvanced
    |   +-- TacticalGhostViewModel.predictionReady       (overlay Ghost AI)
    |   +-- TacticalChronovisorViewModel.criticalMoment  (marker di highlight)
    |
    +-- PlayerSidebar     <-- TacticalPlaybackViewModel.playersUpdated
    |
    +-- TimelineWidget    <-- TacticalPlaybackViewModel.timelineReady
                          --> TacticalPlaybackViewModel.seekRequested
```

## Considerazioni di performance

### MapWidget

La mappa viene renderizzata **a ogni tick** durante il playback (64 tick al secondo). Eventuali colli di bottiglia bloccherebbero l'intero thread UI. Mitigazioni:

- La texture della mappa viene caricata **una sola volta** per cambio mappa, non per tick.
- Le posizioni dei giocatori sono raggruppate in una singola chiamata `QPainter.drawPoints()`.
- Le traiettorie delle granate vengono pre-calcolate al momento del lancio e mantenute in cache fino alla detonazione.
- I marker delle kill svaniscono tramite un `QTimer` invece di essere ridisegnati per tick.

### PlayerSidebar

- 10 card giocatore (5 per squadra) riutilizzano istanze del widget `PlayerCard` invece di crearle / distruggerle a ogni tick (pooling dei widget — stesso pattern dell'app legacy in Kivy).
- Le barre di salute / armatura usano il disegno diretto con `QPainter` dentro un `paintEvent` invece di widget `QProgressBar` annidati, per evitare il churn di layout.

### TimelineWidget

- I marker degli eventi vengono renderizzati in una cache `QPixmap` offscreen una sola volta per partita e poi blitted al widget in `paintEvent`.
- Il cursore (tick corrente) è disegnato separatamente, sopra, così il movimento del cursore non invalida la cache dei marker.

## Accessibilità

- Le card giocatore includono riepiloghi screen-reader-friendly (`setAccessibleName("Giocatore 'Renan' — CT — 100 HP — 4750 di equip")`).
- I marker di evento della timeline portano descrizioni testuali, così uno screen reader annuncia "kill alle 1:23 nel round 12" invece di una semplice posizione di icona.
- Gli eventi codificati a colori (kill = rosso, plant = giallo, defuse = blu) sono abbinati a differenze di forma / posizione (kill a metà altezza, plant / defuse a piena altezza) così gli utenti daltonici possono comunque leggere lo stato (WCAG 1.4.1).

## Integrazione

```
TacticalViewerScreen (apps/qt_app/screens/tactical_viewer_screen.py)
    +-- MapWidget
    +-- PlayerSidebar
    +-- TimelineWidget
            |
            +-- ViewModel in apps/qt_app/viewmodels/tactical_vm.py
                    |
                    +-- core/playback_engine.PlaybackEngine
                    +-- core/qt_playback_engine.QtPlaybackEngine (timer Qt)
                    +-- backend/nn/inference/ghost_engine.GhostEngine
```

## Da non fare

- Non importare questi widget da schermate non tattiche — assumono un contesto di playback che non esiste altrove.
- Non allocare `QPixmap` / `QImage` dentro `paintEvent` — pre-allocare e mettere in cache.
- Non abbonarsi a segnali ad alta frequenza dal thread UI senza batching — 64 tick/s × N subscriber bloccano l'app.

## Correlati

- Cluster di ViewModel tattici: `apps/qt_app/viewmodels/tactical_vm.py`
- Playback engine: `Programma_CS2_RENAN/core/playback_engine.py`
- Inferenza Ghost AI: `Programma_CS2_RENAN/backend/nn/inference/ghost_engine.py`
- Asset delle mappe: `Programma_CS2_RENAN/assets/maps/`
- Parent: `apps/qt_app/widgets/README.md`
