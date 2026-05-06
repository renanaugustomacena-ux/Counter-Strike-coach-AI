# `apps/qt_app/web/tactical-viewer/` — Tactical viewer embarcado (TypeScript / Vite)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Propósito

Tactical viewer interativo renderizado dentro da aplicação Qt via `QWebEngineView`. Implementa a visão 2D do mapa com renderização de alta qualidade em canvas / WebGL para posições de jogadores, trilhas de granadas, cones de FoV e overlays de destaque do chronovisor.

Este é um projeto **Vite + TypeScript**. Ele não roda standalone no browser — espera que a ponte `qt.webChannelTransport` esteja presente (veja `web/README.md` para o protocolo da ponte).

## Inventário de arquivos

| Arquivo | Propósito |
|------|---------|
| `index.html` | HTML de entrada do Vite. O `QWebEngineView` do Qt carrega ou a URL do dev-server, ou o `dist/index.html` buildado. |
| `package.json` | Manifest do package do workspace: scripts `dev`, `build`, `lint`; dependências de runtime. |
| `tsconfig.json` | Config local do TypeScript (estende `web/tsconfig.base.json`). |
| `tsconfig.tsbuildinfo` | Cache de build incremental (gitignored na prática). |
| `vite.config.ts` | Config dos plugins do Vite — integração com a ponte Qt, configurações de HMR, saída de build para `dist/`. |

## Build & dev

### Instalação

A partir da raiz do workspace, uma única vez:

```bash
cd Programma_CS2_RENAN/apps/qt_app/web
pnpm install
```

### Dev (live reload)

```bash
cd Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer
pnpm dev
```

O Vite serve na porta configurada. Dentro do app Qt, defina a URL de dev pelo toggle de desenvolvedor em `Settings → Developer → Tactical Viewer URL` (ou via variável de ambiente).

### Build de produção

```bash
pnpm build
```

A saída são assets estáticos em `tactical-viewer/dist/`. O spec do PyInstaller em `packaging/cs2_analyzer_*.spec` inclui esse diretório no bundle congelado.

## Contrato de runtime

O viewer espera um objeto `bridge` exposto via `QWebChannel` com estes signals / slots (fornecidos por `apps/qt_app/core/web_bridge.py`):

| Direção | Nome | Payload | Notas |
|-----------|------|---------|-------|
| Python → JS | `tickReceived(dict)` | `{tick, players, nades, events}` | Estado por tick durante o playback |
| Python → JS | `mapChanged(str)` | nome do mapa (por exemplo, `de_inferno`) | Dispara recarregamento da textura |
| Python → JS | `chronovisorMarker(dict)` | `{tick, severity, label}` | Renderiza um marcador de destaque |
| JS → Python | `request_tick(int)` | número do tick | Usuário moveu a timeline |
| JS → Python | `request_seek(int)` | número do tick | Pula para um tick específico |
| JS → Python | `select_player(str)` | nome do jogador | Usuário clicou em um ponto |

O contrato está documentado dentro de `web_bridge.py`; mantenha as duas pontas sincronizadas ao alterá-lo.

## Por que TypeScript + Vite (e não apenas QPainter)

| Aspecto | Qt nativo | Camada web |
|---------|-----------|-----------|
| Primitivos de pan / zoom / scrub | Construir do zero em `QGraphicsView` | Ecossistema maduro (libs canvas / WebGL) |
| Shaders de trilha de nade | Caminhos manuais em `QPainter` | Fragment shaders ficam visualmente melhores |
| Velocidade de iteração | Reiniciar o app Qt a cada mudança | HMR do Vite — atualização sub-segundo |
| Reuso entre máquinas | Atrelado ao build de PySide6 | Reutilizável em um futuro viewer somente-browser |

O fallback nativo em `apps/qt_app/widgets/tactical/map_widget.py` é mantido para ambientes em que `QWebEngineView` não está disponível (alguns builds empacotados, testes headless).

## Não faça

- Não assuma que o runtime JS pode acessar a rede. O viewer é offline-only e precisa funcionar sem acesso à internet.
- Não passe por cima da ponte — falar diretamente com o sistema de arquivos do Python ou com o DB a partir do JS é proibido.
- Não commite `node_modules/`, `dist/` ou `tsconfig.tsbuildinfo` (já estão no gitignore em `web/.gitignore`).

## Relacionados

- Raiz do workspace: `apps/qt_app/web/README.md`
- Implementação da ponte: `apps/qt_app/core/web_bridge.py`
- Widget de fallback nativo: `apps/qt_app/widgets/tactical/map_widget.py`
- Empacotamento do build congelado: `packaging/cs2_analyzer_win.spec`
