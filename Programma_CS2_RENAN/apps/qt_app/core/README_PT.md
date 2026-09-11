# `apps/qt_app/core/` — Utilitarios core da aplicacao Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Utilitarios de fundacao para o frontend PySide6/Qt (`apps/qt_app/`). Este pacote agrupa tudo o que **nao** e uma tela, ViewModel ou widget mas e necessario para eles: motores de animacao, plumbing de estado da aplicacao, ponte de assets, design tokens, theming, cola de internacionalizacao e worker threads.

Modulos aqui sao framework-aware (eles importam de `PySide6`) mas sao agnosticos em relacao a qualquer tela especifica.

## Inventario de arquivos

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote. |
| `animation.py` | Helpers de animacao Qt reutilizaveis baseados em `QPropertyAnimation` (fade, slide, pulse, stagger-reveal, collapse-width, count-up, ring-sweep; padrao 200 ms). Kill-switch global: `animations_enabled()` retorna False quando `MACENA_UI_ANIMATIONS=0`. |
| `app_state.py` | Singleton `AppState` — consulta a linha DB `CoachState` a cada 10 s em um Worker em background e emite Signals change-only (status do servico, training, notificacoes); tambem persiste configuracoes toggle da UI (sons, janela frameless, backends de heatmap/marquee). |
| `design_tokens.py` | Design tokens tematizados (dataclasses frozen CS2 / CSGO / CS1.6) consumidos por `qss_generator.py` — GERADOS a partir de `design/tokens/design-tokens.json` por `tools/gen_design_tokens.py`. |
| `easing.py` | Classe `Easing` — aliases `QEasingCurve` nomeados (`Easing.OutCubic`, `Easing.OutBack`, ...) portando o conjunto de easing do Remotion, mais `Easing.cubic_bezier(x1, y1, x2, y2)`. |
| `i18n_bridge.py` | `QtLocalizationManager` — tupla de idiomas `("en", "pt", "it")` (linha 49), carregamento JSON de `assets/i18n/`, hot-swap em troca de idioma. |
| `icons.py` | `IconProvider` — caminho primario SVG-sprite (`design/assets/icons/sprite.svg`) com fallback `QPainterPath` desenhado a mao; flag `USE_SVG_ICONS` forca o fallback para debug. |
| `match_utils.py` | Helpers de match: `extract_map_name` / `map_short_name` de nomes de arquivo de demo (mapas conhecidos SSOT em `core/known_maps.py`) e `count_personal_and_pro`. |
| `qss_generator.py` | Renderiza `themes/base.qss.template` com substituicao de tokens de `design_tokens.py` — uma stylesheet em cache por tema. |
| `qt_playback_engine.py` | Driver de playback nativo Qt envolvendo `core/playback_engine.PlaybackEngine` com avanco de tick orientado por `QTimer`. |
| `sound.py` | `SoundManager` — quatro `QSoundEffect` WAV pre-carregados (click, success, error, notification) de `PHOTO_GUI/sounds/`, controlados por `AppState.sounds_enabled` (padrao off); arquivos ausentes avisam uma vez. |
| `svg_icon_provider.py` | `SvgIconProvider` — factory de `QIcon` baseada em sprite, intercambiavel com o provider `QPainterPath` via `USE_SVG_ICONS` em `icons.py`. |
| `theme_engine.py` | Alterna entre temas CS2 / CSGO / CS1.6, emite `theme_changed` (signal de instancia + relay em nivel de modulo); registra fontes e resolve wallpapers (incluindo uma sentinela `WALLPAPER_SLIDESHOW` para rotacao crossfade de 2 minutos via `_BackgroundWidget`); `rating_color()` / `rating_label()` e helpers de severidade (WCAG 1.4.1). |
| `tray.py` | Integracao com system-tray: `build_tray()` cria o icone de tray (pintado em runtime a partir dos design tokens) com tres acoes sempre presentes (Open Macena, AI Coach, Quit) mais uma entrada condicional CLI Console (apenas layout fonte Windows); retorna `None` quando o system tray nao esta disponivel. |
| `typography.py` | Escala de papeis tipograficos e helpers por papel (sans: Roboto, display: Space Grotesk, mono: JetBrains Mono); tamanhos lidos de `get_tokens()`. |
| `web_bridge.py` | `MarqueeBridge` (QObject) — bridge `QWebChannel` bidirecional entre Qt e os web apps embutidos (`web/`). |
| `widgets_helpers.py` | Pequenos helpers de conveniencia Qt baseados no template QSS (`make_button`, `navigate_to`). |
| `worker.py` | `Worker` (`QRunnable`) + `WorkerSignals` (result / error / finished, mais progress opt-in via `wants_progress=True`) executados no `QThreadPool` — usado pelos ViewModels para carregamento em background. |

## Conceitos-chave

### Singleton de estado da aplicacao (`app_state.py`)

`AppState` (via `get_app_state()`) consulta a linha de banco de dados `CoachState` a cada 10 segundos em um `Worker` em background e emite Signals tipados e change-only (status do servico, progresso de parsing, training, notificacoes). Telas se conectam em `on_enter()` em vez de consultar o banco de dados diretamente.

### Tupla de localizacao (`i18n_bridge.py:49`)

A lista de idiomas e `("en", "pt", "it")` — a **unica fonte da verdade** sobre quais idiomas a aplicacao suporta. Adicionar um quarto idioma exige edicoes aqui, em `assets/i18n/`, e no seletor de idioma da tela de configuracoes (veja `assets/README.md` para o procedimento completo).

### Theme engine (`theme_engine.py`)

Tres temas (CS2 / CSGO / CS1.6). Alternar emite `theme_changed`; a stylesheet e regenerada a partir de `themes/base.qss.template` via substituicao de tokens de `qss_generator.py` e reaplicada em toda a aplicacao sem reinicializacao.

## Integracao

```
qt_app/screens/*  -->  qt_app/core/app_state         (broadcast de estado)
qt_app/screens/*  -->  qt_app/core/animation          (transicoes)
qt_app/screens/*  -->  qt_app/core/i18n_bridge        (lookup de traducao)
qt_app/widgets/*  -->  qt_app/core/design_tokens      (estilizacao consistente)
qt_app/viewmodels/* -->  qt_app/core/worker          (carregamento em background)
```

## Nao faca

- Nao importe de `qt_app/screens/` aqui — `core/` e uma dependencia folha.
- Nao coloque helpers especificos de tela neste diretorio. Esses pertencem ao proprio modulo da tela.
- Nao duplique a tupla de idiomas de `i18n_bridge.py`. Leia-a a partir dali se precisar dela em outro lugar.

## Relacionados

- App pai: `apps/qt_app/README.md`
- Arquivos JSON de i18n: `Programma_CS2_RENAN/assets/i18n/`
- Core de playback (nao-Qt): `core/playback_engine.py`
