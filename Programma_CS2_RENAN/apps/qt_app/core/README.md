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
| `animation.py` | Reusable Qt animation primitives (`QPropertyAnimation` wrappers, easing presets, parallel/sequence helpers). |
| `app_state.py` | `AppState` singleton — polls the `CoachState` DB row every 10 s on a background Worker and emits change-only Signals (service status, training, notifications); also persists UI toggle settings. |
| `design_tokens.py` | Theme design tokens (CS2 / CSGO / CS1.6 frozen dataclasses) consumed by `qss_generator.py` — GENERATED from `design/tokens/design-tokens.json` by `tools/gen_design_tokens.py`. |
| `easing.py` | Named easing curves (`ease_out_cubic`, `ease_in_out_quart`, etc.) backing `animation.py`. |
| `i18n_bridge.py` | `QtLocalizationManager` — language tuple `("en", "pt", "it")` (line 49), JSON loading from `assets/i18n/`, hot-swap on language change. |
| `icons.py` | SVG icon registry with theme-aware colour overrides. |
| `match_utils.py` | Pure helpers for match metadata formatting (date, map name, score). |
| `qss_generator.py` | Generates Qt Style Sheets from `design_tokens.py` + the active theme. |
| `qt_playback_engine.py` | Qt-native playback driver wrapping `core/playback_engine.PlaybackEngine` with `QTimer`-driven tick advancement. |
| `sound.py` | Notification audio (toasts, achievements). Lazy-loaded; degrades silently if the audio backend is unavailable. |
| `svg_icon_provider.py` | `SvgIconProvider` — sprite-backed `QIcon` factory, swappable with the `QPainterPath` provider via `USE_SVG_ICONS` in `icons.py`. |
| `theme_engine.py` | Switches between CS2 / CSGO / CS1.6 themes, emits `theme_changed` signal; registers fonts and wallpapers; `rating_color()` / `rating_label()` (WCAG 1.4.1). |
| `typography.py` | Typography role scale and per-role font helpers (base sans: Roboto). |
| `web_bridge.py` | `MarqueeBridge` (QObject) — bidirectional `QWebChannel` bridge between Qt and the embedded web apps (`web/`). |
| `widgets_helpers.py` | Small Qt convenience helpers built on the QSS template (e.g. `make_button`). |
| `worker.py` | `Worker` (`QRunnable`) + `WorkerSignals` (result / error / finished / progress) run on `QThreadPool` — used by ViewModels for background loading. |

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
