# `apps/qt_app/web/` — Frontend embedded TypeScript / Vite

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Questa directory ospita il **frontend web embedded** che gira dentro l'applicazione Qt tramite `QWebEngineView`. Lo strato web renderizza visualizzazioni interattive che è più semplice scrivere in TypeScript + canvas / WebGL piuttosto che con widget Qt nativi — al momento il tactical viewer è l'unico consumer.

La build è un **monorepo pnpm** con un workspace per ogni app embedded. Un bridge lato Qt (`apps/qt_app/core/web_bridge.py`) fa da marshall per segnali e slot tra l'event loop Python e la runtime JS via `QWebChannel`.

## Layout

```
web/
├── .gitignore
├── pnpm-workspace.yaml          # Dichiarazione del workspace
├── pnpm-lock.yaml               # Versioni delle dipendenze bloccate
├── tsconfig.base.json           # Config compilatore TS condivisa
└── tactical-viewer/             # Membro del workspace — vedere tactical-viewer/README.md
```

## Inventario dei file

| File | Scopo |
|------|---------|
| `.gitignore` | Esclude `node_modules`, `dist`, output di build dal version control. |
| `pnpm-workspace.yaml` | Dichiara i membri del workspace (attualmente `tactical-viewer`). |
| `pnpm-lock.yaml` | Albero delle dipendenze pinnato — committato per garantire build riproducibili. |
| `tsconfig.base.json` | Opzioni del compilatore TypeScript condivise ed ereditate da ciascun workspace. |

## Build & sviluppo

### Setup iniziale

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Build di sviluppo

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

Il dev server di Vite gira su una porta configurata; il `QWebEngineView` dell'app Qt può puntare a esso per il live-reload durante lo sviluppo.

### Build di produzione

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm build
```

Produce l'output in `tactical-viewer/dist/`. La spec di PyInstaller include quella directory nel bundle frozen.

## Bridge con il lato Python

`apps/qt_app/core/web_bridge.py` espone un `QObject` i cui slot e segnali sono mappati nell'oggetto JavaScript `qt.webChannelTransport`. Pattern tipico:

```python
# Lato Python
class WebBridge(QObject):
    tickReceived = Signal(dict)         # Python -> JS

    @Slot(int)
    def request_tick(self, tick: int):  # JS -> Python
        ...
```

```ts
// Lato TypeScript
new QWebChannel(qt.webChannelTransport, (channel) => {
    const bridge = channel.objects.bridge;
    bridge.tickReceived.connect((payload) => render(payload));
    bridge.request_tick(currentTick);
});
```

## Perché uno strato web

Tre ragioni per cui il tactical viewer preferisce TypeScript + canvas / WebGL ai widget Qt nativi:

1. **Primitive di interattività.** Pan / zoom / scrub sono mature nell'ecosistema JS; ricostruirle su `QGraphicsView` è costoso.
2. **Qualità del rendering.** Gli shader WebGL per scie di granate, coni di FoV ed effetti particellari superano `QPainter` per questo stile visivo.
3. **Velocità di iterazione.** L'HMR di Vite è più rapido del riavvio dell'app Qt a ogni modifica visiva.

## Da non fare

- Non aggirare `web_bridge.py`. Tutta la comunicazione Python ↔ JS passa per `QWebChannel`.
- Non committare `node_modules/` (già nel gitignore).
- Non aggiungere un membro del workspace senza aggiornare `pnpm-workspace.yaml` e la spec di PyInstaller.

## Correlati

- Workspace del tactical viewer: `web/tactical-viewer/README.md`
- Bridge lato Python: `apps/qt_app/core/web_bridge.py`
- Fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py` (usato quando la web view è disabilitata)
- App parent: `apps/qt_app/README.md`
