# `apps/qt_app/web/tactical-viewer/` — Tactical viewer embarcado (TypeScript / Vite)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Proposito

Tactical viewer interativo renderizado dentro da aplicacao Qt via `QWebEngineView`. O stack de componentes em `src/components/` implementa a visao 2D do mapa — imagem de radar mais camadas SVG / canvas para pontos de jogador com cones de yaw, trilhas de movimento, heatmap de posicao e overlay da Ghost AI. O root `App.tsx` atualmente apresenta um painel de status MVP que prova o handshake do bridge e a propagacao dos design tokens; compor o stack de mapa nele e a proxima iteracao planejada (plano P4.0).

Este e um projeto **Vite + TypeScript**. Ele nao roda standalone no browser — espera que a ponte `qt.webChannelTransport` esteja presente (veja `web/README.md` para o protocolo da ponte).

## Inventario de arquivos

| Arquivo | Proposito |
|---------|-----------|
| `index.html` | HTML de entrada do Vite — carrega `qrc:///qtwebchannel/qwebchannel.js`. O `QWebEngineView` do Qt carrega o `dist/index.html` buildado via `file://`. |
| `package.json` | Manifest do package do workspace: scripts `dev`, `build`, `preview`, `lint`; dependencias react 18, react-dom, d3, three (d3 / three sao declarados e pre-chunked mas ainda nao importados por `src/`). |
| `tsconfig.json` | Config local do TypeScript (estende `web/tsconfig.base.json`; inclui `../shared`). |
| `tsconfig.tsbuildinfo` | Cache de build incremental (regenerado por `tsc -b`). |
| `vite.config.ts` | Config do Vite — plugin React, `base: "./"` relativo para carregamento `file://`, alias `@shared`, chunks manuais para three/d3, saida de build em `dist/`. |
| `src/main.tsx` | Entry React — monta o componente root. |
| `src/App.tsx` | Componente root — painel de status MVP que prova conexao do bridge + propagacao de tokens; os componentes de mapa abaixo ainda nao estao montados aqui. |
| `src/bridge.ts` | Hook React `useMarqueeBridge()` — conecta via `connectBridge("bridge")` e parseia os payloads JSON do bridge em estado tipado. |
| `src/types.ts` | Tipos TypeScript compartilhados (frames, jogadores, eventos). |
| `src/components/MapCanvas.tsx` | Canvas raiz do mapa — carrega a imagem de radar e compoe as camadas de jogadores / ghost / trilhas / heatmap (coordenadas normalizadas 0..1). |
| `src/components/PlayerLayer.tsx` | Pontos de jogador com cone de yaw, label de nome, anel de HP. |
| `src/components/GhostLayer.tsx` | Overlay de predicao da Ghost AI. |
| `src/components/HeatmapLayer.tsx` | Overlay de heatmap de posicao (40x40 bins de canvas). |
| `src/components/TrailsLayer.tsx` | Overlay de trilhas de movimento — polylines SVG em fade (ultimos ~20 ticks). |
| `src/components/RoundTimeline.tsx` | Timeline de rounds — limites de round + marcadores de evento; clique para fazer scrub via `seek_to_tick`. |
| `src/components/ControlBar.tsx` | Barra de controle superior — status de conexao, indicador de mapa / tick, toggles de heatmap e ghost. |

## Build & dev

### Instalacao

A partir da raiz do workspace, uma unica vez:

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Dev (live reload)

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

O dev server do Vite serve apenas para iteracao no browser — o app Qt nunca aponta para ele. O Qt carrega o `dist/index.html` **buildado** quando o toggle `use_webengine_marquee` esta ativo e o bundle existe; caso contrario, a tela recorre ao widget nativo `TacticalMapWidget`.

### Build de producao

```bash
pnpm build            # ou execute tools/build_web.py a partir da raiz do repositorio
```

A saida sao assets estaticos em `tactical-viewer/dist/` com `base: "./"` relativo para que o Qt possa carrega-los via `QUrl.fromLocalFile`.

## Contrato de runtime

O viewer espera um objeto `bridge` exposto via `QWebChannel` — `MarqueeBridge` de `apps/qt_app/core/web_bridge.py`:

| Direcao | Nome | Payload | Notas |
|---------|------|---------|-------|
| Python → JS | `tick_changed(int)` | tick atual | Emitido durante o playback |
| Python → JS | `frame_ready(str)` | payload JSON do frame | Estado jogadores/nade por tick |
| Python → JS | `coach_state_changed(str)` | estado do coach JSON | |
| Python → JS | `ready_changed(bool)` | prontidao do bridge | |
| Python → JS | `map_name_changed(str)` | nome do mapa (por exemplo, `de_inferno`) | Dispara recarregamento da textura |
| Python → JS | `segments_ready(str)` | JSON `{round_name: start_tick}` | Segmentos de round para a timeline |
| Python → JS | `events_ready(str)` | lista de eventos JSON | Marcadores de kill / plant / defuse |
| Python → JS | `ghost_ready(str)` | JSON `[{x, y, team, name}]` | Posicoes do overlay Ghost AI |
| JS → Python | `seek_to_tick(int)` | numero do tick | Usuario fez scrub na timeline |
| JS → Python | `select_player(int)` | id do jogador | Usuario clicou em um ponto |
| JS → Python | `request_ghost(int)` | numero do tick | Pedido de predicao ghost |
| JS → Python | `log(str, str)` | nivel + mensagem | Log do lado JS no log do Qt |

O mirror tipado desse contrato e a interface `MarqueeBridge` em `web/shared/qwebchannel.ts`; mantenha-a sincronizada com `web_bridge.py` ao alterar qualquer uma das pontas.

## Por que TypeScript + Vite (e nao apenas QPainter)

| Aspecto | Qt nativo | Camada web |
|---------|-----------|-----------|
| Primitivos de pan / zoom / scrub | Construir do zero em `QGraphicsView` | Ecossistema maduro (libs canvas / WebGL) |
| Shaders de trilha de nade | Caminhos manuais em `QPainter` | Fragment shaders ficam visualmente melhores |
| Velocidade de iteracao | Reiniciar o app Qt a cada mudanca | HMR do Vite — atualizacao sub-segundo |
| Reuso entre maquinas | Atrelado ao build de PySide6 | Reutilizavel em um futuro viewer somente-browser |

O fallback nativo em `apps/qt_app/widgets/tactical/map_widget.py` e mantido para ambientes em que `QWebEngineView` nao esta disponivel (alguns builds empacotados, testes headless).

## Nao faca

- Nao assuma que o runtime JS pode acessar a rede. O viewer e offline-only e precisa funcionar sem acesso a internet.
- Nao passe por cima da ponte — falar diretamente com o sistema de arquivos do Python ou com o DB a partir do JS e proibido.
- Nao commite `node_modules/` ou `dist/` (ja estao no gitignore em `web/.gitignore`).

## Relacionados

- Raiz do workspace: `apps/qt_app/web/README.md`
- Implementacao da ponte: `apps/qt_app/core/web_bridge.py`
- Widget de fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py`
- Empacotamento do build congelado: `packaging/cs2_analyzer_win.spec`
