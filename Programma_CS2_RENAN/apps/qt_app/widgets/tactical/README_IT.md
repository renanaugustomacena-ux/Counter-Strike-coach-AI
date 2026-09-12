# `apps/qt_app/widgets/tactical/` — Widget del Tactical Viewer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Widget custom esclusivi della schermata **Tactical Viewer**. Renderizzano il replay 2D della mappa, la sidebar live dei giocatori e lo scrubber della timeline. Nessuno di questi e riutilizzabile altrove — sono fortemente accoppiati allo stato del playback, alle proiezioni della Ghost AI e agli highlight del chronovisor.

## Inventario dei file

| File | Widget | Scopo |
|------|--------|-------|
| `__init__.py` | — | Marker di package. |
| `_paint_utils.py` | — | Helper QPainter condivisi per i widget tattici (`with_alpha()` — copia un `QColor` con un dato alpha). |
| `map_widget.py` | `TacticalMapWidget` | La "Living Map" — renderer 2D della mappa basato su QPainter (carica overview `PHOTO_GUI/maps/*.png`) per posizioni dei giocatori e scie, callout delle zone, stato C4/bomba, traiettorie delle granate e overlay di detonazione, proiezioni della Ghost AI, il riquadro punteggio e l'overlay Ghost Mode frame-14 (percorsi doppi tu-vs-ghost, punti di divergenza, legenda — `set_ghost_overlay()`). Guidato per frame da `TacticalPlaybackVM.frame_updated`; emette `selected_player_changed`. |
| `player_sidebar.py` | `PlayerSidebar` | Colonna roster singola squadra (la schermata ne istanzia due — CT e T): intestazione squadra con conteggio vivi e denaro squadra, sopra card roster frame-13 con HP / armatura / arma / economia / utility inline. Riusa widget per-giocatore cosi il refresh per tick non alloca. |
| `timeline_widget.py` | `TimelineWidget` | Scrubber interattivo con marker degli eventi codificati a colore (kill, plant, defuse), divisori dei round, striscia caption mono `t={tick}`, e glifi momento del chronovisor differenziati per tipo (stella = critico/errore, diamante = clutch, cerchio = giocata; click su un glifo cerca al tick di inizio del momento). Click e drag per fare seek. |

## Architettura

```
TacticalViewerScreen
    |
    +-- TacticalMapWidget  <-- TacticalPlaybackVM.frame_updated (tramite la schermata)
    |   +-- proiezioni ghost da TacticalGhostVM.predict_ghosts (tramite la schermata)
    |
    +-- PlayerSidebar x2 (CT / T)  <-- TacticalPlaybackVM.frame_updated (tramite la schermata)
    |
    +-- TimelineWidget     <-- TacticalPlaybackVM.current_tick_changed / total_ticks_changed
                           <-- TacticalChronovisorVM.scan_complete  (glifi momento, tramite la schermata)
                           <-- TacticalChronovisorVM.navigate_to    (seek, tramite la schermata)
                           --> seek tramite TacticalPlaybackVM
```

## Considerazioni di performance

### TacticalMapWidget

La mappa ridisegna **ogni frame** durante il playback, quindi il lavoro per-frame deve restare minimale:

- Il pixmap della mappa scalato e in cache e ricalcolato solo su ridimensionamento o cambio mappa — i repaint per-frame lo riutilizzano.
- Quando nessuna overview della mappa viene trovata, `paintEvent` disegna un rettangolo scuro di fallback invece di fallire.

### PlayerSidebar

- Le righe giocatore riutilizzano istanze widget per-giocatore (aggiornate in-place, entry obsolete rimosse) invece di crearle / distruggerle per tick.

### TimelineWidget

- I marker e il cursore sono disegnati in `paintEvent`; mantieni le allocazioni per-frame fuori dal percorso di disegno.

## Accessibilita

- Segui la convenzione del progetto: accoppia ogni stato codificato a colore (marker kill / plant / defuse, barre HP) con differenze di testo o forma cosi gli utenti daltonici possano comunque leggerlo (WCAG 1.4.1).

## Integrazione

```
TacticalViewerScreen (apps/qt_app/screens/tactical_viewer_screen.py)
    +-- TacticalMapWidget
    +-- PlayerSidebar (x2)
    +-- TimelineWidget
            |
            +-- ViewModel in apps/qt_app/viewmodels/tactical_vm.py
                    |
                    +-- Programma_CS2_RENAN/core/playback_engine.PlaybackEngine
                    +-- apps/qt_app/core/qt_playback_engine.QtPlaybackEngine (timer Qt, tenuto dalla schermata)
                    +-- backend/nn/inference/ghost_engine.GhostEngine
```

## Da non fare

- Non importare questi widget da schermate non tattiche — assumono un contesto di playback che non esiste altrove.
- Non allocare `QPixmap` / `QImage` dentro `paintEvent` — pre-allocare e mettere in cache.
- Non abbonarsi a segnali ad alta frequenza dal thread UI senza batching — 64 tick/s x N subscriber bloccano l'app.

## Correlati

- Cluster di ViewModel tattici: `apps/qt_app/viewmodels/tactical_vm.py`
- Playback engine: `Programma_CS2_RENAN/core/playback_engine.py`
- Inferenza Ghost AI: `Programma_CS2_RENAN/backend/nn/inference/ghost_engine.py`
- Immagini overview mappa: `Programma_CS2_RENAN/PHOTO_GUI/maps/`
- Parent: `apps/qt_app/widgets/README.md`
