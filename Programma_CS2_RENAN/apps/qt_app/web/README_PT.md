# `apps/qt_app/web/` — Frontend embarcado em TypeScript / Vite

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Proposito

Este diretorio hospeda o **frontend web embarcado** que roda dentro da aplicacao Qt via `QWebEngineView`. A camada web renderiza visualizacoes interativas que sao mais faceis de escrever em TypeScript + canvas / WebGL do que em widgets Qt nativos. E um **pnpm monorepo** com tres apps workspace **React 18 + TypeScript + Vite** — `coach-chat`, `match-detail` e `tactical-viewer`. O tactical viewer e atualmente o unico embarcado por uma tela Qt (`screens/tactical_viewer_screen.py`); os outros dois sao membros do workspace em preparacao.

Uma ponte do lado Qt (`apps/qt_app/core/web_bridge.py`, classe `MarqueeBridge`) faz o marshalling de signals e slots entre o event loop do Python e o runtime JS via `QWebChannel`; o mirror tipado em TypeScript vive em `shared/qwebchannel.ts` e cada app o adapta em seu proprio `src/bridge.ts`.

## Layout

```
web/
├── .gitignore
├── package.json                 # Raiz do workspace — tooling ESLint compartilhado
├── pnpm-workspace.yaml          # Declaracao do workspace (3 membros)
├── pnpm-lock.yaml               # Versoes de dependencias travadas
├── tsconfig.base.json           # Config compartilhada do compilador TS
├── eslint.config.mjs            # Config ESLint flat para todos os workspaces
├── shared/
│   ├── qwebchannel.ts           # Interface tipada MarqueeBridge + connectBridge()
│   └── tokens.ts                # Design tokens (gerados por tools/gen_design_tokens.py --web)
├── coach-chat/                  # App React do chat de coaching
├── match-detail/                # App React do detalhe de partida
└── tactical-viewer/             # App React do tactical viewer — veja tactical-viewer/README.md
```

## Inventario de arquivos

| Arquivo | Proposito |
|---------|-----------|
| `.gitignore` | Exclui `node_modules/`, `dist/`, `.pnpm-store/`, logs do controle de versao. |
| `package.json` | Package raiz do workspace — dependencias dev ESLint/typescript-eslint compartilhadas. |
| `pnpm-workspace.yaml` | Declara membros (`tactical-viewer`, `match-detail`, `coach-chat`) mais configuracoes de `nodeLinker` / copy import para o repo montado em WSL. |
| `pnpm-lock.yaml` | Arvore de dependencias fixada — commitada para garantir builds reproduziveis. |
| `tsconfig.base.json` | Opcoes compartilhadas do compilador TypeScript herdadas por cada workspace. |
| `eslint.config.mjs` | Config ESLint flat compartilhada por todas as apps do workspace. |
| `shared/qwebchannel.ts` | Interface tipada `MarqueeBridge` espelhando `core/web_bridge.py` + helper de handshake `connectBridge()`. |
| `shared/tokens.ts` | Design tokens gerados (`tools/gen_design_tokens.py --web` de `design/tokens/design-tokens.json`) — nao edite manualmente. |

## Build & desenvolvimento

### Setup unico

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Build de desenvolvimento

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer   # ou coach-chat / match-detail
pnpm dev
```

O dev server do Vite serve apenas para iteracao no browser. O app Qt em si sempre carrega o `dist/index.html` **buildado** via `QUrl.fromLocalFile` — nunca aponta para o dev server.

### Build de producao

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm build            # ou execute tools/build_web.py a partir da raiz do repositorio
```

A saida vai para `<app>/dist/`. A tela tactical viewer do Qt usa o bundle buildado somente quando o toggle `use_webengine_marquee` esta habilitado **e** `tactical-viewer/dist/index.html` existe; caso contrario, recorre ao widget nativo `TacticalMapWidget`.

## Ponte com o lado Python

`apps/qt_app/core/web_bridge.py` expoe `MarqueeBridge`, um `QObject` registrado no canal com o nome `bridge`. Seus signals e slots sao espelhados pela interface tipada `MarqueeBridge` em `shared/qwebchannel.ts`:

```python
# Lado Python (core/web_bridge.py)
class MarqueeBridge(QObject):
    tick_changed = Signal(int)          # Python -> JS
    frame_ready = Signal(str)           # Python -> JS (payload JSON)

    @Slot(int)
    def seek_to_tick(self, tick: int):  # JS -> Python
        ...
```

```ts
// Lado TypeScript (src/bridge.ts de qualquer app)
import { connectBridge } from "@shared/qwebchannel";

const bridge = await connectBridge("bridge");
bridge.frame_ready.connect((payload) => render(JSON.parse(payload)));
bridge.seek_to_tick(currentTick);
```

## Por que ter uma camada web

Tres razoes pelas quais o tactical viewer prefere TypeScript + canvas / WebGL em vez de widgets Qt nativos:

1. **Primitivos de interatividade.** Pan / zoom / scrub sao maduros no ecossistema JS; reconstrui-los em `QGraphicsView` e caro.
2. **Qualidade de renderizacao.** Shaders WebGL para trilhas de nade, cones de FoV e efeitos de particulas superam `QPainter` para este estilo visual.
3. **Velocidade de iteracao.** O HMR do Vite e mais rapido do que reiniciar o app Qt a cada ajuste visual.

## Nao faca

- Nao passe por cima do `web_bridge.py`. Toda comunicacao Python ↔ JS passa pelo `QWebChannel`.
- Nao commite `node_modules/` ou `dist/` (ja estao no gitignore).
- Nao adicione um membro de workspace sem atualizar `pnpm-workspace.yaml` e o tooling de build (`tools/build_web.py`).

## Relacionados

- Workspace do tactical viewer: `web/tactical-viewer/README.md`
- Ponte do lado Python: `apps/qt_app/core/web_bridge.py`
- Fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py` (`TacticalMapWidget`, usado quando a web view esta desabilitada ou nao buildada)
- App pai: `apps/qt_app/README.md`
