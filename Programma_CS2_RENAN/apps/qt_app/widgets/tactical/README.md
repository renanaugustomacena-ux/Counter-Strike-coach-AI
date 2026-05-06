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
| `map_widget.py` | `MapWidget` | The "Living Map" — GPU-accelerated 2D map renderer for player positions, grenade trajectories, kill markers, ghost AI projections. Subscribes to `TacticalPlaybackViewModel.tickAdvanced`. |
| `player_sidebar.py` | `PlayerSidebar` | Two-team player roster with live HP / armor / weapon / economy display. Uses widget pooling (object reuse) so per-tick refresh does not allocate. |
| `timeline_widget.py` | `TimelineWidget` | Interactive scrubber with colour-coded event markers (kills, plants, defuses, round transitions). Click and drag to seek. |

## Architecture

```
TacticalViewerScreen
    |
    +-- MapWidget         <-- TacticalPlaybackViewModel.tickAdvanced
    |   +-- TacticalGhostViewModel.predictionReady       (ghost AI overlay)
    |   +-- TacticalChronovisorViewModel.criticalMoment  (highlight markers)
    |
    +-- PlayerSidebar     <-- TacticalPlaybackViewModel.playersUpdated
    |
    +-- TimelineWidget    <-- TacticalPlaybackViewModel.timelineReady
                          --> TacticalPlaybackViewModel.seekRequested
```

## Performance considerations

### MapWidget

The map renders **every tick** during playback (64 ticks per second). Bottlenecks would freeze the entire UI thread. Mitigations:

- Map texture is uploaded **once** per map switch, not per tick.
- Player positions are batched into a single `QPainter.drawPoints()` call.
- Grenade trajectories are pre-computed when a nade is thrown and cached until detonation.
- Kill markers fade out on a `QTimer` rather than being redrawn per tick.

### PlayerSidebar

- 10 player cards (5 per team) reuse `PlayerCard` widget instances rather than creating / destroying per tick (widget pooling — same pattern as the legacy Kivy app).
- Health / armor bars use `QPainter` direct draw inside a `paintEvent` rather than nested `QProgressBar` widgets to avoid layout churn.

### TimelineWidget

- Event markers are rendered into an offscreen `QPixmap` cache once per match and blitted to the widget on `paintEvent`.
- The cursor (current tick) is drawn separately, on top, so cursor movement does not invalidate the marker cache.

## Accessibility

- Player cards include screen-reader-friendly summaries (`setAccessibleName("Player 'Renan' — CT — 100 HP — 4750 equipment")`).
- Timeline event markers carry text descriptions, so a screen reader announces "kill at 1:23 in round 12" rather than just an icon position.
- Color-coded events (kill = red, plant = yellow, defuse = blue) are paired with shape / position differences (kill at half height, plant / defuse at full height) so colour-blind users can still parse the state (WCAG 1.4.1).

## Integration

```
TacticalViewerScreen (apps/qt_app/screens/tactical_viewer_screen.py)
    +-- MapWidget
    +-- PlayerSidebar
    +-- TimelineWidget
            |
            +-- ViewModels in apps/qt_app/viewmodels/tactical_vm.py
                    |
                    +-- core/playback_engine.PlaybackEngine
                    +-- core/qt_playback_engine.QtPlaybackEngine (Qt timer)
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
- Map assets: `Programma_CS2_RENAN/assets/maps/`
- Parent: `apps/qt_app/widgets/README.md`
