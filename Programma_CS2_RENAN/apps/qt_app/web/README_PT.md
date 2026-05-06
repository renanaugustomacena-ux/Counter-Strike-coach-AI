# `apps/qt_app/web/` — Frontend embarcado em TypeScript / Vite

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Propósito

Este diretório hospeda o **frontend web embarcado** que roda dentro da aplicação Qt via `QWebEngineView`. A camada web renderiza visualizações interativas que são mais fáceis de escrever em TypeScript + canvas / WebGL do que em widgets Qt nativos — atualmente o tactical viewer é o único consumidor.

O build é um **pnpm monorepo** com um workspace por app embarcado. Uma ponte do lado Qt (`apps/qt_app/core/web_bridge.py`) faz o marshalling de signals e slots entre o event loop do Python e o runtime JS via `QWebChannel`.

## Layout

```
web/
├── .gitignore
├── pnpm-workspace.yaml          # Declaração do workspace
├── pnpm-lock.yaml               # Versões de dependências travadas
├── tsconfig.base.json           # Config compartilhada do compilador TS
└── tactical-viewer/             # Membro do workspace — veja tactical-viewer/README.md
```

## Inventário de arquivos

| Arquivo | Propósito |
|------|---------|
| `.gitignore` | Exclui `node_modules`, `dist` e outputs de build do controle de versão. |
| `pnpm-workspace.yaml` | Declara membros do workspace (atualmente `tactical-viewer`). |
| `pnpm-lock.yaml` | Árvore de dependências fixada — commitada para garantir builds reproduzíveis. |
| `tsconfig.base.json` | Opções compartilhadas do compilador TypeScript herdadas por cada workspace. |

## Build & desenvolvimento

### Setup único

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Build de desenvolvimento

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

O dev server do Vite roda numa porta configurada; o `QWebEngineView` do app Qt pode apontar para ela e ter live-reload durante o desenvolvimento.

### Build de produção

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm build
```

A saída vai para `tactical-viewer/dist/`. O spec do PyInstaller inclui esse diretório no bundle congelado.

## Ponte com o lado Python

`apps/qt_app/core/web_bridge.py` expõe um `QObject` cujos slots e signals são mapeados para o objeto JavaScript `qt.webChannelTransport`. Padrão típico:

```python
# Lado Python
class WebBridge(QObject):
    tickReceived = Signal(dict)         # Python -> JS

    @Slot(int)
    def request_tick(self, tick: int):  # JS -> Python
        ...
```

```ts
// Lado TypeScript
new QWebChannel(qt.webChannelTransport, (channel) => {
    const bridge = channel.objects.bridge;
    bridge.tickReceived.connect((payload) => render(payload));
    bridge.request_tick(currentTick);
});
```

## Por que ter uma camada web

Três razões pelas quais o tactical viewer prefere TypeScript + canvas / WebGL em vez de widgets Qt nativos:

1. **Primitivos de interatividade.** Pan / zoom / scrub são maduros no ecossistema JS; reconstruí-los em `QGraphicsView` é caro.
2. **Qualidade de renderização.** Shaders WebGL para trilhas de nade, cones de FoV e efeitos de partículas superam `QPainter` para este estilo visual.
3. **Velocidade de iteração.** O HMR do Vite é mais rápido do que reiniciar o app Qt a cada ajuste visual.

## Não faça

- Não passe por cima do `web_bridge.py`. Toda comunicação Python ↔ JS passa pelo `QWebChannel`.
- Não commite `node_modules/` (já está no gitignore).
- Não adicione um membro de workspace sem atualizar `pnpm-workspace.yaml` e o spec do PyInstaller.

## Relacionados

- Workspace do tactical viewer: `web/tactical-viewer/README.md`
- Ponte do lado Python: `apps/qt_app/core/web_bridge.py`
- Fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py` (usado quando a web view está desabilitada)
- App pai: `apps/qt_app/README.md`
