> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets — Static Resources

> **Authority:** Rule 3 (Frontend & UX)

This directory contains static resources consumed by the application at runtime.
Paths are resolved through `core/config.py:get_resource_path()`, which abstracts
the difference between development source trees and frozen executables (the
`i18n/` translations and `map_zones/` overlays are bundled into the PyInstaller
distribution). Nothing in this directory is generated at runtime; every file is
committed to version control and treated as immutable after release.

## Directory Structure

```
assets/
├── fonts/                    # Display fonts (auto-scanned by the theme engine)
│   ├── Inter-*.ttf          # Inter v4.1 static builds (4 weights)
│   ├── JetBrainsMono-*.ttf  # JetBrains Mono v2.304 (3 weights)
│   ├── SpaceGrotesk-*.ttf   # Space Grotesk 2.0.0 (3 weights)
│   └── README.txt           # Sources, licenses (OFL-1.1), role mapping
├── i18n/                     # Internationalization (translations)
│   ├── en.json              # English (572 keys) — primary/fallback
│   ├── pt.json              # Brazilian Portuguese
│   └── it.json              # Italian
├── map_zones/                # Tactical viewer named-zone overlays
│   └── de_mirage.json       # Zone rects (normalized 0-1) for Mirage
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
| `fonts/*.ttf` | TTF font | 10 files | Design-atlas type stack (Inter, Space Grotesk, JetBrains Mono static builds, all OFL-1.1); the theme engine auto-scans any `.ttf`/`.otf` here at startup |
| `fonts/README.txt` | Text | 1 file | Font sources, versions, licenses, and role mapping (UI body: Inter; display: Space Grotesk; mono: JetBrains Mono) |
| `i18n/en.json` | JSON | 572 keys | English UI strings (primary and fallback language) |
| `i18n/pt.json` | JSON | 572 keys | Brazilian Portuguese UI strings |
| `i18n/it.json` | JSON | 572 keys | Italian UI strings |
| `map_zones/de_mirage.json` | JSON | 1 file | Named-zone rects for the Qt tactical viewer overlay (Mirage only so far) |
| `maps/de_*_radar.dds` | DDS image | 10 files | Radar overhead images (1024x1024) for CS2 competitive maps |

## `i18n/` — Localization Files

JSON files containing every user-visible string in the application. The key schema
is identical across all language files: when a key exists in `en.json`, it must also
exist in `pt.json` and `it.json`. If a translation is missing, the English fallback
is used automatically by the `QtLocalizationManager`.

### Key Categories (572 keys total)

| Category | Example Keys | Purpose |
|----------|-------------|---------|
| Navigation | `dashboard`, `coaching`, `settings`, `profile` | Sidebar labels |
| Coaching | `coach_status`, `recent_insights`, `ask_your_coach`, `coach_thinking` | Coach screen text |
| Settings | `visual_theme`, `language`, `font_size`, `ingestion_mode` | Settings screen |
| Profile | `ingame_name`, `bio`, `pro_profile` | User profile fields |
| Tactical | `tactical_analyzer`, `tactical.tick`, `tactical.bomb_planted` | Tactical viewer screen and HUD (dotted `tactical.*` keys) |
| Match Detail | `md_title`, `md_tab_overview`, `md_tab_economy` | Match detail screen (`md_*` prefix) |
| Dialogs | `dialog_edit_profile`, `dialog_save`, `dialog_close` | Dialog messages |
| Steam/FaceIT | `steam_integration`, `steam_key_hint`, `faceit_hint` | Integration screens |
| Help | `help_center`, `search_placeholder`, `select_topic` | Help center screen |
| Wizard | `wizard_intro_title`, `wizard_step1_title`, `wizard_finish_text` | First-run setup wizard |
| Charts | `chart_caption_you`, `chart_economy_title`, `chart_round_axis` | Chart captions and axis labels |

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
2. Translate all 572 values (keep keys unchanged)
3. Register the new language code in `apps/qt_app/core/i18n_bridge.py` (`_load_json_translations`)
4. Add language toggle button in `apps/qt_app/screens/settings_screen.py`
5. Update `core/localization.py` if the legacy hardcoded fallback dicts (`TRANSLATIONS`) need the new language

### Adding a New Key

1. Add the key-value pair to **all three** JSON files (`en.json`, `pt.json`, `it.json`)
2. Reference in code via `i18n.get_text("your_new_key")`
3. If the key is critical for navigation, also add it to `_HARDCODED_EN` in `i18n_bridge.py`

## `maps/` — Radar Images

DDS (DirectDraw Surface) format radar images (1024x1024) for CS2 competitive maps.
They are referenced by the `image_file` field in `data/map_tensors.json` and
consumed by the reporting visualizer for overhead heatmap/overlay rendering.
(The Qt tactical viewer renders from the `PHOTO_GUI/maps/` PNG overviews instead.)

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
  (pixels-per-unit, typically 4.0 to 7.0), and `z_cutoff`/`levels` for multi-level maps;
  used by `core/spatial_data.py` for coordinate transformations
- **`data/map_tensors.json`** — Bombsite and spawn coordinates as tensors for the
  spatial analysis engine, plus the `image_file` radar reference per map
- **`core/map_callouts.py`** — `NamedPosition` registry (161 positions across 9 maps,
  e.g., "A Site", "Mid Doors") for human-readable coaching output; re-exported through
  `backend/analysis/engagement_range.py`

### Adding a New Map

1. Place `de_{mapname}_radar.dds` in `assets/maps/`
2. Add spatial config to `data/map_config.json` (`pos_x`, `pos_y`, `scale`, `landmarks`)
3. Add tensor definitions to `data/map_tensors.json` (bombsite/spawn coordinates, `image_file`)
4. Add named positions to `core/map_callouts.py`
5. For multi-level maps, add a `_lower_radar.dds` variant and set `z_cutoff` in config
6. Optionally add a named-zone overlay file to `assets/map_zones/` (see below)

## `map_zones/` — Tactical Viewer Zone Overlays

JSON files with named-zone rectangles for the Qt tactical viewer. Each file holds
a `zones` list of rects normalized 0-1 within the map pane (`name`, `x`, `y`, `w`,
`h`, `label`, optional `major` flag for the prominent A/B/MID labels).

- Currently one file: `de_mirage.json` (9 zones)
- Loaded by `apps/qt_app/widgets/tactical/map_widget.py` (`load_map_zones()`),
  which accepts both short (`mirage`) and long (`de_mirage`) map names and
  degrades to no overlay (`[]`) for maps without a zone file
- Resolved through `get_resource_path()` and bundled into the frozen build

## Bundling (PyInstaller)

The translations and zone overlays are included in the frozen executable via
`packaging/cs2_analyzer_win.spec` (at the repository root):

```python
(str(APP_DIR / "assets" / "i18n"), "Programma_CS2_RENAN/assets/i18n"),
(str(APP_DIR / "assets" / "map_zones"), "Programma_CS2_RENAN/assets/map_zones"),
```

The `assets/maps/` radar images and `assets/fonts/` TTFs are not currently listed
in the spec `datas` (the frozen tactical viewer uses the `PHOTO_GUI/maps/` PNG
overviews, and `PHOTO_GUI/` fonts, which are bundled). At runtime, paths are
resolved through `get_resource_path()`, which checks `sys._MEIPASS` (frozen)
before falling back to the source tree path.

## Integration Points

| Consumer | Asset | Access Pattern |
|----------|-------|---------------|
| `apps/qt_app/core/i18n_bridge.py` | `i18n/*.json` | `get_resource_path("assets/i18n")` at import |
| `apps/qt_app/core/theme_engine.py` | `fonts/*.ttf` / `*.otf` | Auto-scanned and registered at `register_fonts()` (after the `PHOTO_GUI/` legacy fonts) |
| `apps/qt_app/widgets/tactical/map_widget.py` | `map_zones/*.json` | `load_map_zones()` via `get_resource_path()` per map |
| `reporting/visualizer.py` | `maps/*` | Loads the map image referenced by `data/map_tensors.json` (`image_file`) for heatmap and overlay rendering |

## Development Notes

- DDS files should not exceed 4 MB each (2048x2048 maximum resolution)
- JSON files must be valid UTF-8 with no BOM (byte-order mark)
- The `i18n_bridge.py` `_HARDCODED_EN` fallback dict contains only critical navigation
  keys; keep it in sync when renaming or removing keys from the JSON files
- Map coordinate values originate from CS2 game files (`resource/overviews/*.txt`)
- Pre-commit hook `check-json` validates JSON syntax on every commit
- All 572 keys must be present in every language file; missing keys degrade gracefully
  to English but indicate an incomplete translation
- Fonts are static builds under the SIL Open Font License 1.1; sources and versions
  are documented in `fonts/README.txt` (`JetBrainsMono-Regular.ttf` ships separately
  under `PHOTO_GUI/`)
