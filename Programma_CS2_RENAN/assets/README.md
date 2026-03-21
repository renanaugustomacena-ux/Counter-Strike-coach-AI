> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets — Static Resources

> **Authority:** Rule 3 (Frontend & UX)

This directory contains all static resources consumed by the application at runtime.
Files here are bundled into the PyInstaller distribution and resolved through
`core/config.py:get_resource_path()`, which abstracts the difference between
development source trees and frozen executables. Nothing in this directory is
generated at runtime; every file is committed to version control and treated as
immutable after release.

## Directory Structure

```
assets/
├── i18n/                     # Internationalization (translations)
│   ├── en.json              # English (137 keys) — primary/fallback
│   ├── pt.json              # Brazilian Portuguese
│   └── it.json              # Italian
├── maps/                     # CS2 map radar images
│   ├── de_ancient_radar.dds
│   ├── de_cache_radar.dds
│   ├── de_dust2_radar.dds
│   ├── de_inferno_radar.dds
│   ├── de_mirage_radar.dds
│   ├── de_nuke_lower_radar.dds
│   ├── de_nuke_radar.dds
│   ├── de_overpass_radar.dds
│   ├── de_train_radar.dds
│   ├── de_vertigo_lower_radar.dds
│   └── de_vertigo_radar.dds
├── README.md                 # This file (English)
├── README_IT.md              # Italian translation
└── README_PT.md              # Portuguese translation
```

## File Inventory

| File / Directory | Type | Count | Purpose |
|------------------|------|-------|---------|
| `i18n/en.json` | JSON | 137 keys | English UI strings (primary and fallback language) |
| `i18n/pt.json` | JSON | 137 keys | Brazilian Portuguese UI strings |
| `i18n/it.json` | JSON | 137 keys | Italian UI strings |
| `maps/de_*_radar.dds` | DDS image | 11 files | Radar overhead images for CS2 competitive maps |

## `i18n/` — Localization Files

JSON files containing every user-visible string in the application. The key schema
is identical across all language files: when a key exists in `en.json`, it must also
exist in `pt.json` and `it.json`. If a translation is missing, the English fallback
is used automatically by the `QtLocalizationManager`.

### Key Categories (137 keys total)

| Category | Example Keys | Purpose |
|----------|-------------|---------|
| Navigation | `dashboard`, `coach`, `match_history`, `performance` | Sidebar labels |
| Coaching | `coaching_insights`, `severity_high`, `focus_positioning` | Coach screen text |
| Settings | `theme`, `language`, `demo_path`, `ingestion_mode` | Settings screen |
| Profile | `player_name`, `bio`, `role` | User profile fields |
| Tactical | `tactical_viewer`, `playback_speed`, `timeline` | Tactical viewer screen |
| Dialogs | `confirm_delete`, `save_success`, `error_occurred` | Dialog messages |
| Steam/FaceIT | `steam_id`, `faceit_key`, `sync_profile` | Integration screens |
| Help | `help_center`, `getting_started`, `troubleshooting` | Help center screen |
| Wizard | `wizard_intro_title`, `wizard_step1_title`, `wizard_finish_text` | First-run setup wizard |

### Localization Resolution Chain

The `QtLocalizationManager` in `apps/qt_app/core/i18n_bridge.py` resolves a key
through four priority levels:

1. **JSON file for current language** (`_JSON_TRANSLATIONS[lang][key]`)
2. **Hardcoded dict for current language** (`_FULL_TRANSLATIONS[lang][key]`)
3. **English fallback** (`_FULL_TRANSLATIONS["en"][key]`)
4. **Raw key** (the key string itself, as last resort)

The JSON files are loaded once at import time. Dynamic placeholder substitution
(e.g., `{home_dir}`) is applied during loading.

### Adding a New Language

1. Copy `en.json` to `{language_code}.json` (e.g., `fr.json`)
2. Translate all 137 values (keep keys unchanged)
3. Register the new language code in `apps/qt_app/core/i18n_bridge.py` (`_load_json_translations`)
4. Add language toggle button in `apps/qt_app/screens/settings_screen.py`
5. Update `core/localization.py` if Kivy fallback dicts need the new language

### Adding a New Key

1. Add the key-value pair to **all three** JSON files (`en.json`, `pt.json`, `it.json`)
2. Reference in code via `i18n.get_text("your_new_key")`
3. If the key is critical for navigation, also add it to `_HARDCODED_EN` in `i18n_bridge.py`

## `maps/` — Radar Images

DDS (DirectDraw Surface) format radar images for CS2 competitive maps. These are
used by the Tactical Viewer for 2D overhead rendering of player positions, grenade
trajectories, and round replays.

### Coverage

11 radar images covering all current competitive pool maps:

| Map | File(s) | Multi-level |
|-----|---------|-------------|
| Ancient | `de_ancient_radar.dds` | No |
| Cache | `de_cache_radar.dds` | No |
| Dust2 | `de_dust2_radar.dds` | No |
| Inferno | `de_inferno_radar.dds` | No |
| Mirage | `de_mirage_radar.dds` | No |
| Nuke | `de_nuke_radar.dds`, `de_nuke_lower_radar.dds` | Yes |
| Overpass | `de_overpass_radar.dds` | No |
| Train | `de_train_radar.dds` | No |
| Vertigo | `de_vertigo_radar.dds`, `de_vertigo_lower_radar.dds` | Yes |

### Map Coordinate System

Radar images are paired with spatial configuration files elsewhere in the project:

- **`data/map_config.json`** — `pos_x`, `pos_y` (Valve coordinate-system origin), `scale`
  (pixels-per-unit, typically 4.0 to 7.0), and optional `z_cutoff` for multi-level maps
- **`data/map_tensors.json`** — Bombsite and spawn coordinates as tensors for the
  spatial analysis engine
- **`backend/analysis/engagement_range.py`** — Named positions (e.g., "A Site",
  "Mid Doors") for human-readable coaching output

### Adding a New Map

1. Place `de_{mapname}_radar.dds` in `assets/maps/`
2. Add spatial config to `data/map_config.json` (`pos_x`, `pos_y`, `scale`, `landmarks`)
3. Add tensor definitions to `data/map_tensors.json` (bombsite/spawn coordinates)
4. Add named positions to `backend/analysis/engagement_range.py`
5. For multi-level maps, add a `_lower_radar.dds` variant and set `z_cutoff` in config

## Bundling (PyInstaller)

All files in this directory are included in the frozen executable via
`packaging/cs2_analyzer_win.spec`:

```python
datas += [('Programma_CS2_RENAN/assets/i18n', 'assets/i18n')]
datas += [('Programma_CS2_RENAN/assets/maps', 'assets/maps')]
```

At runtime, paths are resolved through `get_resource_path()`, which checks
`sys._MEIPASS` (frozen) before falling back to the source tree path.

## Integration Points

| Consumer | Asset | Access Pattern |
|----------|-------|---------------|
| `apps/qt_app/core/i18n_bridge.py` | `i18n/*.json` | `get_resource_path("assets/i18n")` at import |
| `apps/qt_app/screens/tactical_screen.py` | `maps/*.dds` | `get_resource_path("assets/maps")` on demand |
| `core/map_manager.py` | `maps/*.dds` | Coordinate transformation with `map_config.json` |
| `reporting/visualizer.py` | `maps/*.dds` | Heatmap and PDF overlay rendering |

## Development Notes

- DDS files should not exceed 4 MB each (2048x2048 maximum resolution)
- JSON files must be valid UTF-8 with no BOM (byte-order mark)
- The `i18n_bridge.py` `_HARDCODED_EN` fallback dict contains only critical navigation
  keys; keep it in sync when renaming or removing keys from the JSON files
- Map coordinate values originate from CS2 game files (`resource/overviews/*.txt`)
- Pre-commit hook `check-json` validates JSON syntax on every commit
- All 137 keys must be present in every language file; missing keys degrade gracefully
  to English but indicate an incomplete translation
