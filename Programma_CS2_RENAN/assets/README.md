# Assets — Static Resources

> **Authority:** Rule 3 (Frontend & UX)

This directory contains static resources used by the application at runtime. These files are bundled into the PyInstaller distribution.

## Directory Structure

```
assets/
├── i18n/                     # Internationalization (translations)
│   ├── en.json              # English (137 keys) — primary/fallback
│   ├── pt.json              # Brazilian Portuguese
│   └── it.json              # Italian
└── maps/                     # CS2 map radar images
    ├── de_ancient_radar.dds
    ├── de_cache_radar.dds
    ├── de_dust2_radar.dds
    ├── de_inferno_radar.dds
    ├── de_mirage_radar.dds
    ├── de_nuke_lower_radar.dds
    ├── de_nuke_radar.dds
    ├── de_overpass_radar.dds
    ├── de_train_radar.dds
    ├── de_vertigo_lower_radar.dds
    └── de_vertigo_radar.dds
```

## `i18n/` — Localization Files

JSON files containing all user-visible UI strings. The key schema is shared across all languages.

### Key Categories (137 keys total)

| Category | Example Keys | Purpose |
|----------|-------------|---------|
| Navigation | `dashboard`, `coach`, `match_history`, `performance` | Sidebar labels |
| Coaching | `coaching_insights`, `severity_high`, `focus_positioning` | Coach screen text |
| Settings | `theme`, `language`, `demo_path`, `ingestion_mode` | Settings screen |
| Profile | `player_name`, `bio`, `role` | User profile fields |
| Tactical | `tactical_viewer`, `playback_speed`, `timeline` | Tactical screen |
| Dialogs | `confirm_delete`, `save_success`, `error_occurred` | Dialog messages |
| Steam/FaceIT | `steam_id`, `faceit_key`, `sync_profile` | Integration screens |
| Help | `help_center`, `getting_started`, `troubleshooting` | Help screen |

### Adding a New Language

1. Copy `en.json` to `{language_code}.json` (e.g., `fr.json`)
2. Translate all values (keep keys unchanged)
3. Register in `apps/qt_app/core/i18n_bridge.py`
4. Add language toggle button in `apps/qt_app/screens/settings_screen.py`

### Adding a New Key

1. Add the key to **all** JSON files (en, pt, it)
2. Use in code: `i18n.get_text("your_new_key")`
3. If a key is missing from a translation file, the English fallback is used

## `maps/` — Radar Images

DDS (DirectDraw Surface) format radar images for CS2 competitive maps. Used by the tactical viewer for 2D map rendering.

### Coverage

11 radar images covering all current competitive pool maps:
- Standard maps: Ancient, Cache, Dust2, Inferno, Mirage, Overpass, Train
- Multi-level maps: Nuke (upper + lower), Vertigo (upper + lower)

### Map Coordinate System

Map images are paired with spatial configuration in `data/map_config.json`:
- `pos_x`, `pos_y` — Valve coordinate system origin
- `scale` — Pixels-per-unit scale factor (4.0 to 7.0)
- Multi-level maps have `z_cutoff` boundaries for upper/lower discrimination

### Adding a New Map

1. Place `de_{mapname}_radar.dds` in this directory
2. Add spatial config to `data/map_config.json` (pos_x, pos_y, scale, landmarks)
3. Add tensor definitions to `data/map_tensors.json` (bombsite/spawn coordinates)
4. Add named positions to `backend/analysis/engagement_range.py`

## Bundling

All files in this directory are included in the PyInstaller build via `packaging/cs2_analyzer_win.spec`:
```python
datas += [('Programma_CS2_RENAN/assets/i18n', 'assets/i18n')]
```

## Development Notes

- DDS files should not exceed 4MB each (2048x2048 max resolution)
- JSON files must be valid UTF-8 with no BOM
- The `i18n_bridge.py` fallback hardcodes English strings for critical keys — keep this in sync
- Map coordinate values come from CS2 game files (`resource/overviews/*.txt`)
