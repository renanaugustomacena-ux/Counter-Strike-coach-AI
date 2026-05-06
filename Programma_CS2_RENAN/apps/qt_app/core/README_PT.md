# `apps/qt_app/core/` — Utilitários core da aplicação Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Utilitários de fundação para o frontend PySide6/Qt (`apps/qt_app/`). Este pacote agrupa tudo o que **não** é uma tela, ViewModel ou widget mas é necessário para eles: motores de animação, plumbing de estado da aplicação, ponte de assets, design tokens, theming, cola de internacionalização e worker threads.

Módulos aqui são framework-aware (eles importam de `PySide6`) mas são agnósticos em relação a qualquer tela específica.

## Inventário de arquivos

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote. |
| `animation.py` | Primitivas de animação Qt reutilizáveis (wrappers de `QPropertyAnimation`, presets de easing, helpers parallel/sequence). |
| `app_state.py` | Singleton de estado a nível de aplicação — tela atual, tema, idioma, hub de signals para broadcasts entre telas. |
| `asset_bridge.py` | Resolve caminhos de assets via `core/config.get_resource_path()` e os expõe como `QUrl` / `QPixmap`. |
| `design_tokens.py` | Design tokens com tema CS2 (cores, espaçamento, tamanhos de tipografia) consumidos por `qss_generator.py`. |
| `easing.py` | Curvas de easing nomeadas (`ease_out_cubic`, `ease_in_out_quart`, etc.) que dão suporte ao `animation.py`. |
| `i18n_bridge.py` | `QtLocalizationManager` — tupla de idiomas `("en", "pt", "it")` (linha 49), carregamento JSON de `assets/i18n/`, hot-swap em troca de idioma. |
| `icons.py` | Registro de ícones SVG com overrides de cor cientes do tema. |
| `match_utils.py` | Helpers puros para formatação de metadados de partida (data, nome de mapa, placar). |
| `qss_generator.py` | Gera Qt Style Sheets a partir de `design_tokens.py` + o tema ativo. |
| `qt_playback_engine.py` | Driver de playback nativo Qt envolvendo `core/playback_engine.PlaybackEngine` com avanço de tick orientado por `QTimer`. |
| `sound.py` | Áudio de notificação (toasts, conquistas). Carregado lazy; degrada silenciosamente se o backend de áudio não estiver disponível. |
| `svg_icon_provider.py` | `QQmlImageProvider` para ícones SVG — usado pela web view embutida. |
| `theme_engine.py` | Alterna entre temas CS2 / CSGO / CS1.6, emite signal `themeChanged`. |
| `typography.py` | Registro de fontes (Roboto, fallback monoespaçado), escala de tamanho de fonte vinculada à configuração `FONT_SIZE`. |
| `web_bridge.py` | Ponte bidirecional entre Qt e o `web/tactical-viewer/` (TypeScript) embutido — slots e signals de `QWebChannel`. |
| `widgets_helpers.py` | Pequenos helpers de conveniência Qt (centred-on-screen, find-ancestor, signal-disconnect-all). |
| `worker.py` | Padrão de worker `QThread` com suporte a cancelamento — usado por ViewModels para carregamento em background. |

## Conceitos-chave

### Singleton de estado da aplicação (`app_state.py`)

Centraliza broadcasts entre telas. ViewModels emitem através de `app_state.bus`, telas se inscrevem. Evita a alternativa de cada tela ser ligada diretamente a todas as outras.

### Tupla de localização (`i18n_bridge.py:49`)

A lista de idiomas é `("en", "pt", "it")` — a **única fonte da verdade** sobre quais idiomas a aplicação suporta. Adicionar um quarto idioma exige edições aqui, em `assets/i18n/`, e no seletor de idioma da tela de configurações (veja `assets/README.md` para o procedimento completo).

### Theme engine (`theme_engine.py`)

Três temas (CS2 / CSGO / CS1.6). Alternar emite `themeChanged`; `qss_generator.py` regenera o style sheet; cada widget inscrito em `setStyleSheet()` apanha a mudança sem reinicialização.

## Integração

```
qt_app/screens/*  -->  qt_app/core/app_state         (broadcast de estado)
qt_app/screens/*  -->  qt_app/core/animation          (transições)
qt_app/screens/*  -->  qt_app/core/i18n_bridge        (lookup de tradução)
qt_app/widgets/*  -->  qt_app/core/design_tokens      (estilização consistente)
qt_app/viewmodels/* -->  qt_app/core/worker          (carregamento em background)
```

## Não faça

- Não importe de `qt_app/screens/` aqui — `core/` é uma dependência folha.
- Não coloque helpers específicos de tela neste diretório. Esses pertencem ao próprio módulo da tela.
- Não duplique a tupla de idiomas de `i18n_bridge.py`. Leia-a a partir dali se precisar dela em outro lugar.

## Relacionados

- App pai: `apps/qt_app/README.md`
- Arquivos JSON de i18n: `Programma_CS2_RENAN/assets/i18n/`
- Core de playback (não-Qt): `core/playback_engine.py`
