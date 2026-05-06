# `apps/qt_app/web/tactical-viewer/` — Tactical viewer embedded (TypeScript / Vite)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Tactical viewer interattivo renderizzato dentro l'applicazione Qt tramite `QWebEngineView`. Implementa la vista 2D della mappa con rendering canvas / WebGL ad alta qualità per posizioni dei giocatori, scie di granate, coni di FoV e overlay di highlight del chronovisor.

Questo è un progetto **Vite + TypeScript**. Non gira standalone nel browser — si aspetta che il bridge `qt.webChannelTransport` sia presente (vedere `web/README.md` per il protocollo del bridge).

## Inventario dei file

| File | Scopo |
|------|---------|
| `index.html` | HTML di ingresso di Vite. Il `QWebEngineView` di Qt carica o l'URL del dev-server o il `dist/index.html` buildato. |
| `package.json` | Manifest del package del workspace: script `dev`, `build`, `lint`; dipendenze runtime. |
| `tsconfig.json` | Config TypeScript locale (estende `web/tsconfig.base.json`). |
| `tsconfig.tsbuildinfo` | Cache di build incrementale (in pratica nel gitignore). |
| `vite.config.ts` | Config dei plugin di Vite — integrazione del bridge Qt, impostazioni HMR, output di build in `dist/`. |

## Build & dev

### Install

Una volta sola dalla root del workspace:

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Dev (live reload)

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

Vite serve sulla porta configurata. Dentro l'app Qt, impostare l'URL di dev tramite il toggle developer in `Impostazioni → Developer → Tactical Viewer URL` (o tramite variabile d'ambiente).

### Build di produzione

```bash
pnpm build
```

Produce asset statici in `tactical-viewer/dist/`. La spec di PyInstaller in `packaging/cs2_analyzer_*.spec` include quella directory nel bundle frozen.

## Contratto runtime

Il viewer si aspetta un oggetto `bridge` esposto via `QWebChannel` con questi segnali / slot (forniti da `apps/qt_app/core/web_bridge.py`):

| Direzione | Nome | Payload | Note |
|-----------|------|---------|-------|
| Python → JS | `tickReceived(dict)` | `{tick, players, nades, events}` | Stato per tick durante il playback |
| Python → JS | `mapChanged(str)` | nome della mappa (es. `de_inferno`) | Innesca il reload della texture |
| Python → JS | `chronovisorMarker(dict)` | `{tick, severity, label}` | Renderizza un marker di highlight |
| JS → Python | `request_tick(int)` | numero del tick | L'utente ha agito sulla timeline |
| JS → Python | `request_seek(int)` | numero del tick | Salta a un tick specifico |
| JS → Python | `select_player(str)` | nome del giocatore | L'utente ha cliccato su un puntino |

Il contratto è documentato dentro `web_bridge.py`; tenere allineate entrambe le estremità quando lo si modifica.

## Perché TypeScript + Vite (e non solo QPainter)

| Aspetto | Qt nativo | Strato web |
|---------|-----------|-----------|
| Primitive di pan / zoom / scrub | Da costruire da zero su `QGraphicsView` | Ecosistema maturo (librerie canvas / WebGL) |
| Shader per scie di granate | Path manuali con `QPainter` | I fragment shader producono un risultato migliore |
| Velocità di iterazione | Riavviare l'app Qt a ogni modifica | HMR di Vite — aggiornamento in meno di un secondo |
| Riuso cross-machine | Legato alla build PySide6 | Riutilizzabile in un futuro viewer browser-only |

Il fallback nativo in `apps/qt_app/widgets/tactical/map_widget.py` è mantenuto per ambienti dove `QWebEngineView` non è disponibile (alcune build packagizzate, test headless).

## Da non fare

- Non assumere che la runtime JS possa raggiungere la rete. Il viewer è solo offline e deve funzionare senza accesso a internet.
- Non aggirare il bridge — parlare direttamente al filesystem Python o al DB dal JS è vietato.
- Non committare `node_modules/`, `dist/`, o `tsconfig.tsbuildinfo` (già nel gitignore di `web/.gitignore`).

## Correlati

- Root del workspace: `apps/qt_app/web/README.md`
- Implementazione del bridge: `apps/qt_app/core/web_bridge.py`
- Widget di fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py`
- Packaging della build frozen: `packaging/cs2_analyzer_win.spec`
