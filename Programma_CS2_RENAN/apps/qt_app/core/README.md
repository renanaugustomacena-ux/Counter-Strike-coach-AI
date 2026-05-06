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
| `app_state.py` | Application-level state singleton — current screen, theme, language, signal hub for cross-screen broadcasts. |
| `asset_bridge.py` | Resolves asset paths through `core/config.get_resource_path()` and exposes them as `QUrl` / `QPixmap`. |
| `design_tokens.py` | CS2-themed design tokens (colors, spacing, typography sizes) consumed by `qss_generator.py`. |
| `easing.py` | Named easing curves (`ease_out_cubic`, `ease_in_out_quart`, etc.) backing `animation.py`. |
| `i18n_bridge.py` | `QtLocalizationManager` — language tuple `("en", "pt", "it")` (line 49), JSON loading from `assets/i18n/`, hot-swap on language change. |
| `icons.py` | SVG icon registry with theme-aware colour overrides. |
| `match_utils.py` | Pure helpers for match metadata formatting (date, map name, score). |
| `qss_generator.py` | Generates Qt Style Sheets from `design_tokens.py` + the active theme. |
| `qt_playback_engine.py` | Qt-native playback driver wrapping `core/playback_engine.PlaybackEngine` with `QTimer`-driven tick advancement. |
| `sound.py` | Notification audio (toasts, achievements). Lazy-loaded; degrades silently if the audio backend is unavailable. |
| `svg_icon_provider.py` | `QQmlImageProvider` for SVG icons — used by the embedded web view. |
| `theme_engine.py` | Switches between CS2 / CSGO / CS1.6 themes, emits `themeChanged` signal. |
| `typography.py` | Font registration (Roboto, monospace fallback), font-size scale tied to `FONT_SIZE` setting. |
| `web_bridge.py` | Bidirectional bridge between Qt and the embedded `web/tactical-viewer/` (TypeScript) — `QWebChannel` slots and signals. |
| `widgets_helpers.py` | Small Qt convenience helpers (centred-on-screen, find-ancestor, signal-disconnect-all). |
| `worker.py` | `QThread` worker pattern with cancellation support — used by ViewModels for background loading. |

## Key concepts

### Application state singleton (`app_state.py`)

Centralises cross-screen broadcasts. ViewModels emit through `app_state.bus`, screens subscribe. Avoids the alternative of every screen wiring directly to every other screen.

### Localization tuple (`i18n_bridge.py:49`)

The language list is `("en", "pt", "it")` — the **single source of truth** for which languages the application supports. Adding a fourth language requires edits here, in `assets/i18n/`, and in the settings screen language picker (see `assets/README.md` for the full procedure).

### Theme engine (`theme_engine.py`)

Three themes (CS2 / CSGO / CS1.6). Switching emits `themeChanged`; `qss_generator.py` regenerates the style sheet; every widget subscribed to `setStyleSheet()` picks up the change without restart.

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
