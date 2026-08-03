> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets — Static Resources

> **Authority:** Rule 3 (Frontend & UX)

This directory contains static resources consumed by the application at runtime.
Paths are resolved through `core/config.py:get_resource_path()`, which abstracts
the difference between development source trees and frozen executables (the
`i18n/` translations are bundled into the PyInstaller distribution). Nothing in this directory is
generated at runtime; every file is committed to version control and treated as
immutable after release.

## Directory Structure

```
assets/
├── fonts/                    # Optional display fonts (auto-scanned by the theme engine)
│   └── README.txt           # Sources for Space Grotesk / Inter variable fonts
├── i18n/                     # Internationalization (translations)
│   ├── en.json              # English (141 keys) — primary/fallback
│   ├── pt.json              # Brazilian Portuguese
│   └── it.json              # Italian
├── maps/                     # CS2 map radar images
│   ├── de_ancient_radar.dds
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
| `fonts/README.txt` | Text | 1 file | Instructions for optional variable fonts (Space Grotesk, Inter); the theme engine auto-scans any `.ttf`/`.otf` dropped here at startup |
| `i18n/en.json` | JSON | 141 keys | English UI strings (primary and fallback language) |
| `i18n/pt.json` | JSON | 141 keys | Brazilian Portuguese UI strings |
| `i18n/it.json` | JSON | 141 keys | Italian UI strings |
| `maps/de_*_radar.dds` | DDS image | 10 files | Radar overhead images for CS2 competitive maps |

## `i18n/` — Localization Files

JSON files containing every user-visible string in the application. The key schema
is identical across all language files: when a key exists in `en.json`, it must also
exist in `pt.json` and `it.json`. If a translation is missing, the English fallback
is used automatically by the `QtLocalizationManager`.

### Key Categories (141 keys total)

| Category | Example Keys | Purpose |
|----------|-------------|---------|
| Navigation | `dashboard`, `coaching`, `settings`, `profile` | Sidebar labels |
| Coaching | `coach_status`, `recent_insights`, `ask_your_coach`, `coach_thinking` | Coach screen text |
| Settings | `visual_theme`, `language`, `font_size`, `ingestion_mode` | Settings screen |
| Profile | `ingame_name`, `bio`, `pro_profile` | User profile fields |
| Tactical | `tactical_analyzer`, `select_map`, `select_round`, `launch_viewer` | Tactical viewer screen |
| Dialogs | `dialog_edit_profile`, `dialog_save`, `dialog_close` | Dialog messages |
| Steam/FaceIT | `steam_integration`, `steam_key_hint`, `faceit_hint` | Integration screens |
| Help | `help_center`, `search_placeholder`, `select_topic` | Help center screen |
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
2. Translate all 141 values (keep keys unchanged)
3. Register the new language code in `apps/qt_app/core/i18n_bridge.py` (`_load_json_translations`)
4. Add language toggle button in `apps/qt_app/screens/settings_screen.py`
5. Update `core/localization.py` if the legacy hardcoded fallback dicts (`TRANSLATIONS`) need the new language

### Adding a New Key

1. Add the key-value pair to **all three** JSON files (`en.json`, `pt.json`, `it.json`)
2. Reference in code via `i18n.get_text("your_new_key")`
3. If the key is critical for navigation, also add it to `_HARDCODED_EN` in `i18n_bridge.py`

## `maps/` — Radar Images

DDS (DirectDraw Surface) format radar images for CS2 competitive maps. They are
paired with the spatial configuration in `data/map_config.json` and consumed by
the reporting visualizer for overhead heatmap/overlay rendering. (The Qt tactical
viewer renders from the `PHOTO_GUI/maps/` PNG overviews instead.)

### Coverage

10 radar images covering the competitive pool maps:

| Map | File(s) | Multi-level |
|-----|---------|-------------|
| Ancient | `de_ancient_radar.dds` | No |
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
- **`core/map_callouts.py`** — `NamedPosition` registry (161 positions across 9 maps,
  e.g., "A Site", "Mid Doors") for human-readable coaching output; re-exported through
  `backend/analysis/engagement_range.py`

### Adding a New Map

1. Place `de_{mapname}_radar.dds` in `assets/maps/`
2. Add spatial config to `data/map_config.json` (`pos_x`, `pos_y`, `scale`, `landmarks`)
3. Add tensor definitions to `data/map_tensors.json` (bombsite/spawn coordinates)
4. Add named positions to `core/map_callouts.py`
5. For multi-level maps, add a `_lower_radar.dds` variant and set `z_cutoff` in config

## Bundling (PyInstaller)

The translations are included in the frozen executable via
`packaging/cs2_analyzer_win.spec` (at the repository root):

```python
(str(APP_DIR / "assets" / "i18n"), "Programma_CS2_RENAN/assets/i18n"),
```

The `assets/maps/` radar images are not currently listed in the spec `datas`
(the frozen tactical viewer uses the `PHOTO_GUI/maps/` PNG overviews, which
are bundled). At runtime, paths are resolved through `get_resource_path()`,
which checks `sys._MEIPASS` (frozen) before falling back to the source tree path.

## Integration Points

| Consumer | Asset | Access Pattern |
|----------|-------|---------------|
| `apps/qt_app/core/i18n_bridge.py` | `i18n/*.json` | `get_resource_path("assets/i18n")` at import |
| `apps/qt_app/core/theme_engine.py` | `fonts/*.ttf` / `*.otf` | Auto-scanned and registered at startup (optional display fonts) |
| `reporting/visualizer.py` | `maps/*` | Loads the map image referenced by `data/map_config.json` (`image_file`) for heatmap and overlay rendering |

## Development Notes

- DDS files should not exceed 4 MB each (2048x2048 maximum resolution)
- JSON files must be valid UTF-8 with no BOM (byte-order mark)
- The `i18n_bridge.py` `_HARDCODED_EN` fallback dict contains only critical navigation
  keys; keep it in sync when renaming or removing keys from the JSON files
- Map coordinate values originate from CS2 game files (`resource/overviews/*.txt`)
- Pre-commit hook `check-json` validates JSON syntax on every commit
- All 141 keys must be present in every language file; missing keys degrade gracefully
  to English but indicate an incomplete translation
