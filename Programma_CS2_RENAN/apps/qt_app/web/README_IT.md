# `apps/qt_app/web/` — Frontend embedded TypeScript / Vite

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Questa directory ospita il **frontend web embedded** che gira dentro l'applicazione Qt tramite `QWebEngineView`. Lo strato web renderizza visualizzazioni interattive che e piu semplice scrivere in TypeScript + canvas / WebGL piuttosto che con widget Qt nativi. E un **monorepo pnpm** con tre app workspace **React 18 + TypeScript + Vite** — `coach-chat`, `match-detail` e `tactical-viewer`. Il tactical viewer e attualmente l'unico embedded da una schermata Qt (`screens/tactical_viewer_screen.py`); gli altri due sono membri del workspace in preparazione.

Un bridge lato Qt (`apps/qt_app/core/web_bridge.py`, classe `MarqueeBridge`) fa da marshall per segnali e slot tra l'event loop Python e la runtime JS via `QWebChannel`; il mirror tipizzato in TypeScript vive in `shared/qwebchannel.ts` e ogni app lo adatta nel proprio `src/bridge.ts`.

## Layout

```
web/
├── .gitignore
├── package.json                 # Root del workspace — tooling ESLint condiviso
├── pnpm-workspace.yaml          # Dichiarazione del workspace (3 membri)
├── pnpm-lock.yaml               # Versioni delle dipendenze bloccate
├── tsconfig.base.json           # Config compilatore TS condivisa
├── eslint.config.mjs            # Config ESLint flat per tutti i workspace
├── shared/
│   ├── qwebchannel.ts           # Interfaccia tipizzata MarqueeBridge + connectBridge()
│   └── tokens.ts                # Design token (generati da tools/gen_design_tokens.py --web)
├── coach-chat/                  # App React per la chat coaching
├── match-detail/                # App React per il dettaglio partita
└── tactical-viewer/             # App React per il tactical viewer — vedere tactical-viewer/README.md
```

## Inventario dei file

| File | Scopo |
|------|-------|
| `.gitignore` | Esclude `node_modules/`, `dist/`, `.pnpm-store/`, log dal version control. |
| `package.json` | Package root del workspace — dipendenze dev ESLint/typescript-eslint condivise. |
| `pnpm-workspace.yaml` | Dichiara i membri (`tactical-viewer`, `match-detail`, `coach-chat`) piu le impostazioni `nodeLinker` / copy import per il repo montato su WSL. |
| `pnpm-lock.yaml` | Albero delle dipendenze pinnato — committato per garantire build riproducibili. |
| `tsconfig.base.json` | Opzioni del compilatore TypeScript condivise ereditate da ciascun workspace. |
| `eslint.config.mjs` | Config ESLint flat condivisa da tutte le app del workspace. |
| `shared/qwebchannel.ts` | Interfaccia tipizzata `MarqueeBridge` che rispecchia `core/web_bridge.py` + helper di handshake `connectBridge()`. |
| `shared/tokens.ts` | Design token generati (`tools/gen_design_tokens.py --web` da `design/tokens/design-tokens.json`) — non modificare a mano. |

## Build & sviluppo

### Setup iniziale

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Build di sviluppo

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer   # o coach-chat / match-detail
pnpm dev
```

Il dev server di Vite serve solo per iterazione lato browser. L'app Qt stessa carica sempre il `dist/index.html` **buildato** tramite `QUrl.fromLocalFile` — non punta mai al dev server.

### Build di produzione

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm build            # oppure esegui tools/build_web.py dalla root del repository
```

Produce l'output in `<app>/dist/`. La schermata tactical viewer di Qt usa il bundle buildato solo quando il toggle `use_webengine_marquee` e abilitato **e** `tactical-viewer/dist/index.html` esiste; altrimenti ricade sul widget nativo `TacticalMapWidget`.

## Bridge con il lato Python

`apps/qt_app/core/web_bridge.py` espone `MarqueeBridge`, un `QObject` registrato sul canale con il nome `bridge`. I suoi segnali e slot sono rispecchiati dall'interfaccia tipizzata `MarqueeBridge` in `shared/qwebchannel.ts`:

```python
# Lato Python (core/web_bridge.py)
class MarqueeBridge(QObject):
    tick_changed = Signal(int)          # Python -> JS
    frame_ready = Signal(str)           # Python -> JS (payload JSON)

    @Slot(int)
    def seek_to_tick(self, tick: int):  # JS -> Python
        ...
```

```ts
// Lato TypeScript (src/bridge.ts di qualsiasi app)
import { connectBridge } from "@shared/qwebchannel";

const bridge = await connectBridge("bridge");
bridge.frame_ready.connect((payload) => render(JSON.parse(payload)));
bridge.seek_to_tick(currentTick);
```

## Perche uno strato web

Tre ragioni per cui il tactical viewer preferisce TypeScript + canvas / WebGL ai widget Qt nativi:

1. **Primitive di interattivita.** Pan / zoom / scrub sono mature nell'ecosistema JS; ricostruirle su `QGraphicsView` e costoso.
2. **Qualita del rendering.** Gli shader WebGL per scie di granate, coni di FoV ed effetti particellari superano `QPainter` per questo stile visivo.
3. **Velocita di iterazione.** L'HMR di Vite e piu rapido del riavvio dell'app Qt a ogni modifica visiva.

## Da non fare

- Non aggirare `web_bridge.py`. Tutta la comunicazione Python ↔ JS passa per `QWebChannel`.
- Non committare `node_modules/` o `dist/` (gia nel gitignore).
- Non aggiungere un membro del workspace senza aggiornare `pnpm-workspace.yaml` e il tooling di build (`tools/build_web.py`).

## Correlati

- Workspace del tactical viewer: `web/tactical-viewer/README.md`
- Bridge lato Python: `apps/qt_app/core/web_bridge.py`
- Fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py` (`TacticalMapWidget`, usato quando la web view e disabilitata o non buildata)
- App parent: `apps/qt_app/README.md`
