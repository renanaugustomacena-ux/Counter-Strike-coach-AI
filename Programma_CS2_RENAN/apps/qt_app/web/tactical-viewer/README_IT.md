# `apps/qt_app/web/tactical-viewer/` — Tactical viewer embedded (TypeScript / Vite)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Tactical viewer interattivo renderizzato dentro l'applicazione Qt tramite `QWebEngineView`. Lo stack di componenti in `src/components/` implementa la vista 2D della mappa — immagine radar piu layer SVG / canvas per puntini giocatore con coni di yaw, scie di movimento, heatmap di posizione e overlay della Ghost AI. Il root `App.tsx` attualmente presenta un pannello di stato MVP che dimostra l'handshake del bridge e la propagazione dei design token; comporre lo stack mappa al suo interno e l'iterazione pianificata successiva (piano P4.0).

Questo e un progetto **Vite + TypeScript**. Non gira standalone nel browser — si aspetta che il bridge `qt.webChannelTransport` sia presente (vedere `web/README.md` per il protocollo del bridge).

## Inventario dei file

| File | Scopo |
|------|-------|
| `index.html` | HTML di ingresso di Vite — carica `qrc:///qtwebchannel/qwebchannel.js`. Il `QWebEngineView` di Qt carica il `dist/index.html` buildato via `file://`. |
| `package.json` | Manifest del package del workspace: script `dev`, `build`, `preview`, `lint`; dipendenze react 18, react-dom, d3, three (d3 / three sono dichiarati e pre-chunked ma non ancora importati da `src/`). |
| `tsconfig.json` | Config TypeScript locale (estende `web/tsconfig.base.json`; include `../shared`). |
| `tsconfig.tsbuildinfo` | Cache di build incrementale (rigenerato da `tsc -b`). |
| `vite.config.ts` | Config di Vite — plugin React, `base: "./"` relativo per caricamento `file://`, alias `@shared`, chunk manuali per three/d3, output di build in `dist/`. |
| `src/main.tsx` | Entry React — monta il componente root. |
| `src/App.tsx` | Componente root — pannello di stato MVP che dimostra la connessione del bridge + propagazione dei token; i componenti mappa qui sotto non sono ancora montati qui. |
| `src/bridge.ts` | Hook React `useMarqueeBridge()` — si connette via `connectBridge("bridge")` e parsa i payload JSON del bridge in stato tipizzato. |
| `src/types.ts` | Tipi TypeScript condivisi (frame, giocatori, eventi). |
| `src/components/MapCanvas.tsx` | Canvas mappa root — carica l'immagine radar e compone i layer giocatori / ghost / scie / heatmap (coordinate normalizzate 0..1). |
| `src/components/PlayerLayer.tsx` | Puntini giocatore con cono di yaw, label nome, anello HP. |
| `src/components/GhostLayer.tsx` | Overlay di predizione Ghost AI. |
| `src/components/HeatmapLayer.tsx` | Overlay heatmap di posizione (40x40 bin canvas). |
| `src/components/TrailsLayer.tsx` | Overlay scie di movimento — polyline SVG in dissolvenza (ultimi ~20 tick). |
| `src/components/RoundTimeline.tsx` | Timeline round — confini round + marker eventi; click per fare scrub via `seek_to_tick`. |
| `src/components/ControlBar.tsx` | Barra di controllo superiore — stato connessione, indicatore mappa / tick, toggle heatmap e ghost. |

## Build & dev

### Install

Dalla root del workspace una sola volta:

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Dev (live reload)

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

Il dev server di Vite serve solo per iterazione lato browser — l'app Qt non punta mai a esso. Qt carica il `dist/index.html` **buildato** quando il toggle `use_webengine_marquee` e attivo e il bundle esiste; altrimenti la schermata ricade sul widget nativo `TacticalMapWidget`.

### Build di produzione

```bash
pnpm build            # oppure esegui tools/build_web.py dalla root del repository
```

Produce asset statici in `tactical-viewer/dist/` con un `base: "./"` relativo cosi Qt puo caricarli via `QUrl.fromLocalFile`.

## Contratto runtime

Il viewer si aspetta un oggetto `bridge` esposto via `QWebChannel` — `MarqueeBridge` da `apps/qt_app/core/web_bridge.py`:

| Direzione | Nome | Payload | Note |
|-----------|------|---------|------|
| Python → JS | `tick_changed(int)` | tick corrente | Emesso durante il playback |
| Python → JS | `frame_ready(str)` | payload JSON del frame | Stato giocatori/nade per tick |
| Python → JS | `coach_state_changed(str)` | stato coach JSON | |
| Python → JS | `ready_changed(bool)` | prontezza del bridge | |
| Python → JS | `map_name_changed(str)` | nome mappa (es. `de_inferno`) | Innesca il reload della texture |
| Python → JS | `segments_ready(str)` | JSON `{round_name: start_tick}` | Segmenti round per la timeline |
| Python → JS | `events_ready(str)` | lista eventi JSON | Marker kill / plant / defuse |
| Python → JS | `ghost_ready(str)` | JSON `[{x, y, team, name}]` | Posizioni overlay Ghost AI |
| JS → Python | `seek_to_tick(int)` | numero del tick | L'utente ha fatto scrub sulla timeline |
| JS → Python | `select_player(int)` | id giocatore | L'utente ha cliccato su un puntino |
| JS → Python | `request_ghost(int)` | numero del tick | Richiesta di predizione ghost |
| JS → Python | `log(str, str)` | livello + messaggio | Log lato JS nel log Qt |

Il mirror tipizzato di questo contratto e l'interfaccia `MarqueeBridge` in `web/shared/qwebchannel.ts`; mantenerla sincronizzata con `web_bridge.py` quando si modifica una delle due estremita.

## Perche TypeScript + Vite (e non solo QPainter)

| Aspetto | Qt nativo | Strato web |
|---------|-----------|-----------|
| Primitive di pan / zoom / scrub | Da costruire da zero su `QGraphicsView` | Ecosistema maturo (librerie canvas / WebGL) |
| Shader per scie di granate | Path manuali con `QPainter` | I fragment shader producono un risultato migliore |
| Velocita di iterazione | Riavviare l'app Qt a ogni modifica | HMR di Vite — aggiornamento in meno di un secondo |
| Riuso cross-machine | Legato alla build PySide6 | Riutilizzabile in un futuro viewer browser-only |

Il fallback nativo in `apps/qt_app/widgets/tactical/map_widget.py` e mantenuto per ambienti dove `QWebEngineView` non e disponibile (alcune build packagizzate, test headless).

## Da non fare

- Non assumere che la runtime JS possa raggiungere la rete. Il viewer e solo offline e deve funzionare senza accesso a internet.
- Non aggirare il bridge — parlare direttamente al filesystem Python o al DB dal JS e vietato.
- Non committare `node_modules/` o `dist/` (gia nel gitignore di `web/.gitignore`).

## Correlati

- Root del workspace: `apps/qt_app/web/README.md`
- Implementazione del bridge: `apps/qt_app/core/web_bridge.py`
- Widget di fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py`
- Packaging della build frozen: `packaging/cs2_analyzer_win.spec`
