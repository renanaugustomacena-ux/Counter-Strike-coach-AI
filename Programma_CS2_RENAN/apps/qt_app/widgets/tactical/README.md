# `apps/qt_app/widgets/tactical/` — Tactical viewer widgets

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Custom widgets exclusive to the **Tactical Viewer** screen. They render the 2D map replay, live player sidebar, and timeline scrubber. None of these are reusable elsewhere — they are tightly coupled to playback state, ghost AI projections, and chronovisor highlights.

## File inventory

| File | Widget | Purpose |
|------|--------|---------|
| `__init__.py` | — | Package marker. |
| `_paint_utils.py` | — | Shared QPainter helpers for the tactical widgets (`with_alpha()` — copy a `QColor` with a given alpha). |
| `map_widget.py` | `TacticalMapWidget` | The "Living Map" — QPainter-based 2D map renderer (loads `PHOTO_GUI/maps/*.png` overviews) for player positions and trails, zone callouts, C4/bomb state, grenade trajectories and detonation overlays, ghost AI projections, the score box, and the frame-14 Ghost Mode overlay (dual you-vs-ghost paths, divergence points, legend — `set_ghost_overlay()`). Driven per frame via `TacticalPlaybackVM.frame_updated`; emits `selected_player_changed`. |
| `player_sidebar.py` | `PlayerSidebar` | Single-team roster column (the screen instantiates two — CT and T): team header with alive count and team money over frame-13 roster cards carrying HP / armor / weapon / economy / utility inline. Reuses per-player row widgets so per-tick refresh does not allocate. |
| `timeline_widget.py` | `TimelineWidget` | Interactive scrubber with colour-coded event markers (kills, plants, defuses), round dividers, a mono `t={tick}` caption strip, and kind-differentiated chronovisor moment glyphs (star = critical/mistake, diamond = clutch, circle = play; clicking a glyph seeks to the moment's start tick). Click and drag to seek. |

## Architecture

```
TacticalViewerScreen
    |
    +-- TacticalMapWidget  <-- TacticalPlaybackVM.frame_updated (via the screen)
    |   +-- ghost projections from TacticalGhostVM.predict_ghosts (via the screen)
    |
    +-- PlayerSidebar x2 (CT / T)  <-- TacticalPlaybackVM.frame_updated (via the screen)
    |
    +-- TimelineWidget     <-- TacticalPlaybackVM.current_tick_changed / total_ticks_changed
                           <-- TacticalChronovisorVM.scan_complete  (moment glyphs, via the screen)
                           <-- TacticalChronovisorVM.navigate_to    (seek, via the screen)
                           --> seeks through TacticalPlaybackVM
```

## Performance considerations

### TacticalMapWidget

The map repaints **every frame** during playback, so per-frame work must stay minimal:

- The scaled map pixmap is cached and recomputed only on resize or map change — per-frame paints reuse it.
- When no map overview is found, `paintEvent` draws a dark fallback rect instead of failing.

### PlayerSidebar

- Player rows reuse per-player widget instances (updated in place, stale entries evicted) rather than being created / destroyed per tick.

### TimelineWidget

- Markers and the cursor are drawn in `paintEvent`; keep per-frame allocations out of the paint path.

## Accessibility

- Follow the project convention: pair every colour-coded state (kill / plant / defuse markers, HP bars) with text or shape differences so colour-blind users can still parse it (WCAG 1.4.1).

## Integration

```
TacticalViewerScreen (apps/qt_app/screens/tactical_viewer_screen.py)
    +-- TacticalMapWidget
    +-- PlayerSidebar (x2)
    +-- TimelineWidget
            |
            +-- ViewModels in apps/qt_app/viewmodels/tactical_vm.py
                    |
                    +-- Programma_CS2_RENAN/core/playback_engine.PlaybackEngine
                    +-- apps/qt_app/core/qt_playback_engine.QtPlaybackEngine (Qt timer, held by the screen)
                    +-- backend/nn/inference/ghost_engine.GhostEngine
```

## Do not

- Do not import these widgets from non-tactical screens — they assume playback context that does not exist elsewhere.
- Do not allocate `QPixmap` / `QImage` inside `paintEvent` — pre-allocate and cache.
- Do not subscribe to high-frequency signals from the UI thread without batching — 64 ticks/s × N subscribers freezes the app.

## Related

- Tactical ViewModel cluster: `apps/qt_app/viewmodels/tactical_vm.py`
- Playback engine: `Programma_CS2_RENAN/core/playback_engine.py`
- Ghost AI inference: `Programma_CS2_RENAN/backend/nn/inference/ghost_engine.py`
- Map overview images: `Programma_CS2_RENAN/PHOTO_GUI/maps/`
- Parent: `apps/qt_app/widgets/README.md`
