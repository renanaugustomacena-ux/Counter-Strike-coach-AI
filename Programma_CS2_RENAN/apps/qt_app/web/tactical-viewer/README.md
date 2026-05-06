# `apps/qt_app/web/tactical-viewer/` — Embedded tactical-viewer (TypeScript / Vite)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Interactive tactical viewer rendered inside the Qt application via `QWebEngineView`. Implements the 2D map view with high-quality canvas / WebGL rendering for player positions, grenade trails, FoV cones, and chronovisor highlight overlays.

This is a **Vite + TypeScript** project. It does not run standalone in the browser — it expects the `qt.webChannelTransport` bridge to be present (see `web/README.md` for the bridge protocol).

## File inventory

| File | Purpose |
|------|---------|
| `index.html` | Vite entry HTML. The Qt `QWebEngineView` loads either the dev-server URL or the built `dist/index.html`. |
| `package.json` | Workspace package manifest: `dev`, `build`, `lint` scripts; runtime dependencies. |
| `tsconfig.json` | Local TypeScript config (extends `web/tsconfig.base.json`). |
| `tsconfig.tsbuildinfo` | Incremental build cache (gitignored in practice). |
| `vite.config.ts` | Vite plugin config — Qt-bridge integration, HMR settings, build output to `dist/`. |

## Build & dev

### Install

From the workspace root once:

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Dev (live reload)

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

Vite serves on its configured port. Inside the Qt app, set the dev URL via the developer toggle in `Settings → Developer → Tactical Viewer URL` (or via env var).

### Production build

```bash
pnpm build
```

Outputs static assets to `tactical-viewer/dist/`. The PyInstaller spec at `packaging/cs2_analyzer_*.spec` includes that directory in the frozen bundle.

## Runtime contract

The viewer expects a `QWebChannel`-exposed `bridge` object with these signals / slots (provided by `apps/qt_app/core/web_bridge.py`):

| Direction | Name | Payload | Notes |
|-----------|------|---------|-------|
| Python → JS | `tickReceived(dict)` | `{tick, players, nades, events}` | Per-tick state during playback |
| Python → JS | `mapChanged(str)` | map name (e.g. `de_inferno`) | Triggers texture reload |
| Python → JS | `chronovisorMarker(dict)` | `{tick, severity, label}` | Renders a highlight marker |
| JS → Python | `request_tick(int)` | tick number | User scrubbed the timeline |
| JS → Python | `request_seek(int)` | tick number | Jump to specific tick |
| JS → Python | `select_player(str)` | player name | User clicked a dot |

The contract is documented inside `web_bridge.py`; keep both ends in sync when changing it.

## Why TypeScript + Vite (not just QPainter)

| Concern | Native Qt | Web layer |
|---------|-----------|-----------|
| Pan / zoom / scrub primitives | Build from scratch on `QGraphicsView` | Mature ecosystem (canvas / WebGL libs) |
| Nade trail shaders | Manual `QPainter` paths | Fragment shaders give better look |
| Iteration speed | Restart the Qt app on every change | Vite HMR — sub-second update |
| Cross-machine reuse | Tied to PySide6 build | Reusable in a future browser-only viewer |

The native fallback at `apps/qt_app/widgets/tactical/map_widget.py` is retained for environments where `QWebEngineView` is unavailable (some packaged builds, headless tests).

## Do not

- Do not assume the JS runtime can reach the network. The viewer is offline-only and must work without internet access.
- Do not bypass the bridge — talking directly to the Python file system or DB from JS is forbidden.
- Do not commit `node_modules/`, `dist/`, or `tsconfig.tsbuildinfo` (already gitignored in `web/.gitignore`).

## Related

- Workspace root: `apps/qt_app/web/README.md`
- Bridge implementation: `apps/qt_app/core/web_bridge.py`
- Native fallback widget: `apps/qt_app/widgets/tactical/map_widget.py`
- Frozen-build packaging: `packaging/cs2_analyzer_win.spec`
