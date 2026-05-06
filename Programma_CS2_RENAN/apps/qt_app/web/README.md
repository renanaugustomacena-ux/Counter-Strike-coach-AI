# `apps/qt_app/web/` — Embedded TypeScript / Vite frontend

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

This directory hosts the **embedded web frontend** that runs inside the Qt application via `QWebEngineView`. The web layer renders interactive visualisations that are easier to author in TypeScript + canvas / WebGL than in native Qt widgets — currently the tactical viewer is the sole consumer.

The build is a **pnpm monorepo** with one workspace per embedded app. A Qt-side bridge (`apps/qt_app/core/web_bridge.py`) marshals signals and slots between the Python event loop and the JS runtime via `QWebChannel`.

## Layout

```
web/
├── .gitignore
├── pnpm-workspace.yaml          # Workspace declaration
├── pnpm-lock.yaml               # Locked dependency versions
├── tsconfig.base.json           # Shared TS compiler config
└── tactical-viewer/             # Workspace member — see tactical-viewer/README.md
```

## File inventory

| File | Purpose |
|------|---------|
| `.gitignore` | Excludes `node_modules`, `dist`, build outputs from version control. |
| `pnpm-workspace.yaml` | Declares workspace members (currently `tactical-viewer`). |
| `pnpm-lock.yaml` | Pinned dependency tree — committed to ensure reproducible builds. |
| `tsconfig.base.json` | Shared TypeScript compiler options inherited by each workspace. |

## Build & development

### One-time setup

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Development build

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

The Vite dev server runs on a configured port; the Qt app's `QWebEngineView` can point at it for live-reload during development.

### Production build

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm build
```

Outputs to `tactical-viewer/dist/`. The PyInstaller spec includes that directory in the frozen bundle.

## Bridge with the Python side

`apps/qt_app/core/web_bridge.py` exposes a `QObject` whose slots and signals are mapped into the JavaScript `qt.webChannelTransport` object. Typical pattern:

```python
# Python side
class WebBridge(QObject):
    tickReceived = Signal(dict)         # Python -> JS

    @Slot(int)
    def request_tick(self, tick: int):  # JS -> Python
        ...
```

```ts
// TypeScript side
new QWebChannel(qt.webChannelTransport, (channel) => {
    const bridge = channel.objects.bridge;
    bridge.tickReceived.connect((payload) => render(payload));
    bridge.request_tick(currentTick);
});
```

## Why a web layer at all

Three reasons the tactical viewer prefers TypeScript + canvas / WebGL over native Qt widgets:

1. **Interactivity primitives.** Pan / zoom / scrub are mature in the JS ecosystem; rebuilding them on `QGraphicsView` is expensive.
2. **Rendering quality.** WebGL shaders for nade trails, FoV cones, and particle effects out-perform `QPainter` for this visual style.
3. **Iteration speed.** Vite's HMR is faster than restarting the Qt app on every visual tweak.

## Do not

- Do not bypass `web_bridge.py`. All Python ↔ JS communication goes through `QWebChannel`.
- Do not commit `node_modules/` (already gitignored).
- Do not add a workspace member without updating `pnpm-workspace.yaml` and the PyInstaller spec.

## Related

- Tactical viewer workspace: `web/tactical-viewer/README.md`
- Python-side bridge: `apps/qt_app/core/web_bridge.py`
- Native fallback: `apps/qt_app/widgets/tactical/map_widget.py` (used when the web view is disabled)
- Parent app: `apps/qt_app/README.md`
