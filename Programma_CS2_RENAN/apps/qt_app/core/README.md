# `apps/qt_app/core/` — Qt application core utilities

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Foundation utilities for the PySide6/Qt frontend (`apps/qt_app/`). This package collects everything that is **not** a screen, ViewModel, or widget but is needed by them: animation engines, application state plumbing, asset bridging, design tokens, theming, internationalisation glue, and worker threads.

Modules here are framework-aware (they import from `PySide6`) but are agnostic of any specific screen.

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `animation.py` | Reusable Qt animation helpers on `QPropertyAnimation` (fade, slide, pulse, stagger-reveal, collapse-width, count-up, ring-sweep; default 200 ms). Global kill-switch: `animations_enabled()` returns False when `MACENA_UI_ANIMATIONS=0`. |
| `app_state.py` | `AppState` singleton — polls the `CoachState` DB row every 10 s on a background Worker and emits change-only Signals (service status, training, notifications); also persists UI toggle settings (sounds, frameless window, heatmap/marquee backends). |
| `design_tokens.py` | Theme design tokens (CS2 / CSGO / CS1.6 frozen dataclasses) consumed by `qss_generator.py` — GENERATED from `design/tokens/design-tokens.json` by `tools/gen_design_tokens.py`. |
| `easing.py` | `Easing` class — named `QEasingCurve` aliases (`Easing.OutCubic`, `Easing.OutBack`, ...) porting the Remotion easing set, plus `Easing.cubic_bezier(x1, y1, x2, y2)`. |
| `i18n_bridge.py` | `QtLocalizationManager` — language tuple `("en", "pt", "it")` (line 49), JSON loading from `assets/i18n/`, hot-swap on language change. |
| `icons.py` | `IconProvider` — SVG-sprite primary path (`design/assets/icons/sprite.svg`) with a hand-drawn `QPainterPath` fallback; `USE_SVG_ICONS` flag forces the fallback for debugging. |
| `match_utils.py` | Match helpers: `extract_map_name` / `map_short_name` from demo filenames (known-maps SSOT in `core/known_maps.py`) and `count_personal_and_pro`. |
| `qss_generator.py` | Renders `themes/base.qss.template` with token substitution from `design_tokens.py` — one cached stylesheet per theme. |
| `qt_playback_engine.py` | Qt-native playback driver wrapping `core/playback_engine.PlaybackEngine` with `QTimer`-driven tick advancement. |
| `sound.py` | `SoundManager` — four preloaded `QSoundEffect` WAVs (click, success, error, notification) from `PHOTO_GUI/sounds/`, gated by `AppState.sounds_enabled` (default off); missing files warn once. |
| `svg_icon_provider.py` | `SvgIconProvider` — sprite-backed `QIcon` factory, swappable with the `QPainterPath` provider via `USE_SVG_ICONS` in `icons.py`. |
| `theme_engine.py` | Switches between CS2 / CSGO / CS1.6 themes, emits `theme_changed` (instance signal + module-level relay); registers fonts and resolves wallpapers; `rating_color()` / `rating_label()` and severity helpers (WCAG 1.4.1). |
| `typography.py` | Typography role scale and per-role font helpers (sans: Roboto, display: Space Grotesk, mono: JetBrains Mono); sizes read from `get_tokens()`. |
| `web_bridge.py` | `MarqueeBridge` (QObject) — bidirectional `QWebChannel` bridge between Qt and the embedded web apps (`web/`). |
| `widgets_helpers.py` | Small Qt convenience helpers built on the QSS template (`make_button`, `navigate_to`). |
| `worker.py` | `Worker` (`QRunnable`) + `WorkerSignals` (result / error / finished, plus opt-in progress via `wants_progress=True`) run on `QThreadPool` — used by ViewModels for background loading. |

## Key concepts

### Application state singleton (`app_state.py`)

`AppState` (via `get_app_state()`) polls the `CoachState` database row every 10 seconds on a background `Worker` and emits typed, change-only Signals (service status, parsing progress, training, notifications). Screens connect in `on_enter()` instead of polling the database themselves.

### Localization tuple (`i18n_bridge.py:49`)

The language list is `("en", "pt", "it")` — the **single source of truth** for which languages the application supports. Adding a fourth language requires edits here, in `assets/i18n/`, and in the settings screen language picker (see `assets/README.md` for the full procedure).

### Theme engine (`theme_engine.py`)

Three themes (CS2 / CSGO / CS1.6). Switching emits `theme_changed`; the stylesheet is regenerated from `themes/base.qss.template` via `qss_generator.py` token substitution and re-applied application-wide without restart.

## Integration

```
qt_app/screens/*  -->  qt_app/core/app_state         (state broadcast)
qt_app/screens/*  -->  qt_app/core/animation          (transitions)
qt_app/screens/*  -->  qt_app/core/i18n_bridge        (translation lookup)
qt_app/widgets/*  -->  qt_app/core/design_tokens      (consistent styling)
qt_app/viewmodels/* -->  qt_app/core/worker          (background loading)
```

## Do not

- Do not import from `qt_app/screens/` here — `core/` is a leaf dependency.
- Do not put screen-specific helpers in this directory. Those belong inside the screen's own module.
- Do not duplicate `i18n_bridge.py`'s language tuple. Read it from there if you need it elsewhere.

## Related

- Parent app: `apps/qt_app/README.md`
- i18n JSON files: `Programma_CS2_RENAN/assets/i18n/`
- Playback core (non-Qt): `core/playback_engine.py`
