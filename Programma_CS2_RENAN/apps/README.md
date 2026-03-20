# Apps — User Interface Layer

> **Authority:** Rule 3 (Frontend & UX), MVVM architecture pattern

The `apps/` directory contains all user-facing interface code for the Macena CS2 Analyzer. Two UI frameworks coexist during the migration period:

| Subdirectory | Framework | Status | Purpose |
|-------------|-----------|--------|---------|
| `desktop_app/` | Kivy + KivyMD | Legacy (Phase 0) | Original desktop UI, being replaced |
| `qt_app/` | PySide6 (Qt6) | **Active** (Phase 2+) | Production desktop UI |

## Architecture

Both UIs follow the **MVVM (Model-View-ViewModel)** pattern:

```
View (Screen/Widget) ──signals──> ViewModel (QObject) ──queries──> Model (SQLModel/DB)
     UI layout only                data + state logic              persistence layer
```

**Key principles:**
- Views never access the database directly
- ViewModels run database queries on background threads (Worker/QRunnable)
- Results are marshaled to the main thread via Qt Signals
- Screens don't import each other (loose coupling)

## Entry Point

The application launches from `qt_app/app.py`:

```bash
# From project root, with venv activated:
python -m Programma_CS2_RENAN.apps.qt_app.app
```

Or via the PyInstaller bundle (see `packaging/`).

## Standalone Tools

- `spatial_debugger.py` — Standalone spatial debugging tool for map coordinate verification

## Development Guidelines

1. **All new UI work goes in `qt_app/`** — do not add features to `desktop_app/`
2. **No Kivy imports in Qt code** — `asset_bridge.py`, `i18n_bridge.py`, `theme_engine.py` use only Qt/stdlib
3. **Background threading is mandatory** — never block the main thread with DB queries or network calls
4. **Use `Worker` from `qt_app/core/worker.py`** for all background operations
5. **Connect to `AppState` signals** in `on_enter()` — this is the live data bus from the backend
6. **Charts use QtCharts** (not matplotlib) — lighter, native integration
7. **Localization** — all user-visible strings must go through `i18n_bridge.get_text(key)`
8. **Themes** — use `ThemeEngine` for colors/fonts, never hardcode hex values in screens

## File Count

- `desktop_app/`: 13 Python files (legacy)
- `qt_app/`: 50+ Python files across `core/`, `viewmodels/`, `widgets/`, `screens/`
