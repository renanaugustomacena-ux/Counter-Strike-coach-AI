# `apps/qt_app/core/` -- Utilita core dell'applicazione Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Utilita di base per il frontend PySide6/Qt (`apps/qt_app/`). Questo pacchetto raccoglie tutto cio che **non** e una schermata, ViewModel o widget ma di cui hanno bisogno: motori di animazione, plumbing dello stato applicativo, bridging degli asset, design token, theming, glue di internazionalizzazione e thread worker.

I moduli qui sono framework-aware (importano da `PySide6`) ma sono agnostici rispetto a qualsiasi schermata specifica.

## Inventario File

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto. |
| `animation.py` | Helper di animazione Qt riutilizzabili basati su `QPropertyAnimation` (fade, slide, pulse, stagger-reveal, collapse-width, count-up, ring-sweep; default 200 ms). Kill-switch globale: `animations_enabled()` restituisce False quando `MACENA_UI_ANIMATIONS=0`. |
| `app_state.py` | Singleton `AppState` -- interroga la riga DB `CoachState` ogni 10 s su un Worker in background e emette Signal change-only (stato del servizio, training, notifiche); inoltre persiste le impostazioni toggle dell'UI (suoni, finestra frameless, backend heatmap/marquee). |
| `design_tokens.py` | Design token tematizzati (dataclass frozen CS2 / CSGO / CS1.6) consumati da `qss_generator.py` -- GENERATI da `design/tokens/design-tokens.json` tramite `tools/gen_design_tokens.py`. |
| `easing.py` | Classe `Easing` -- alias `QEasingCurve` nominati (`Easing.OutCubic`, `Easing.OutBack`, ...) che portano il set di easing Remotion, piu `Easing.cubic_bezier(x1, y1, x2, y2)`. |
| `i18n_bridge.py` | `QtLocalizationManager` -- tupla di lingue `("en", "pt", "it")` (riga 49), caricamento JSON da `assets/i18n/`, hot-swap al cambio di lingua. |
| `icons.py` | `IconProvider` -- percorso primario SVG-sprite (`design/assets/icons/sprite.svg`) con fallback `QPainterPath` disegnato a mano; il flag `USE_SVG_ICONS` forza il fallback per il debug. |
| `match_utils.py` | Helper per i match: `extract_map_name` / `map_short_name` da nomi di file demo (mappe note SSOT in `core/known_maps.py`) e `count_personal_and_pro`. |
| `qss_generator.py` | Renderizza `themes/base.qss.template` con sostituzione di token da `design_tokens.py` -- un foglio di stile in cache per tema. |
| `qt_playback_engine.py` | Driver di playback Qt-nativo che incapsula `core/playback_engine.PlaybackEngine` con avanzamento tick guidato da `QTimer`. |
| `sound.py` | `SoundManager` -- quattro `QSoundEffect` WAV precaricati (click, success, error, notification) da `PHOTO_GUI/sounds/`, controllati da `AppState.sounds_enabled` (default off); file mancanti avvisano una volta. |
| `svg_icon_provider.py` | `SvgIconProvider` -- factory di `QIcon` basata su sprite, scambiabile con il provider `QPainterPath` tramite `USE_SVG_ICONS` in `icons.py`. |
| `theme_engine.py` | Commuta tra i temi CS2 / CSGO / CS1.6, emette `theme_changed` (signal di istanza + relay a livello di modulo); registra font e risolve wallpaper (inclusa una sentinella `WALLPAPER_SLIDESHOW` per la rotazione crossfade di 2 minuti tramite `_BackgroundWidget`); `rating_color()` / `rating_label()` e helper di severita (WCAG 1.4.1). |
| `tray.py` | Integrazione system-tray: `build_tray()` crea l'icona tray (dipinta a runtime dai design token) con tre azioni sempre presenti (Open Macena, AI Coach, Quit) piu una voce condizionale CLI Console (solo layout sorgente Windows); restituisce `None` quando il system tray non e disponibile. |
| `typography.py` | Scala di ruoli tipografici e helper per-ruolo (sans: Roboto, display: Space Grotesk, mono: JetBrains Mono); le dimensioni vengono lette da `get_tokens()`. |
| `web_bridge.py` | `MarqueeBridge` (QObject) -- bridge `QWebChannel` bidirezionale tra Qt e le web app embedded (`web/`). |
| `widgets_helpers.py` | Piccoli helper di convenienza Qt basati sul template QSS (`make_button`, `navigate_to`). |
| `worker.py` | `Worker` (`QRunnable`) + `WorkerSignals` (result / error / finished, piu progress opt-in tramite `wants_progress=True`) eseguiti su `QThreadPool` -- usato dai ViewModel per il caricamento in background. |

## Concetti chiave

### Singleton di stato applicativo (`app_state.py`)

`AppState` (tramite `get_app_state()`) interroga la riga di database `CoachState` ogni 10 secondi su un `Worker` in background e emette Signal tipizzati e change-only (stato del servizio, avanzamento parsing, training, notifiche). Le schermate si connettono in `on_enter()` invece di interrogare il database direttamente.

### Tupla di localizzazione (`i18n_bridge.py:49`)

La lista delle lingue e `("en", "pt", "it")` -- la **singola sorgente di verita** per quali lingue l'applicazione supporta. Aggiungere una quarta lingua richiede modifiche qui, in `assets/i18n/`, e nel selettore di lingua della schermata Settings (vedi `assets/README.md` per la procedura completa).

### Theme engine (`theme_engine.py`)

Tre temi (CS2 / CSGO / CS1.6). Lo switch emette `theme_changed`; il foglio di stile viene rigenerato da `themes/base.qss.template` tramite sostituzione token di `qss_generator.py` e riapplicato a livello applicativo senza riavvio.

## Integrazione

```
qt_app/screens/*  -->  qt_app/core/app_state         (broadcast di stato)
qt_app/screens/*  -->  qt_app/core/animation          (transizioni)
qt_app/screens/*  -->  qt_app/core/i18n_bridge        (lookup di traduzione)
qt_app/widgets/*  -->  qt_app/core/design_tokens      (styling consistente)
qt_app/viewmodels/* -->  qt_app/core/worker          (caricamento in background)
```

## Da non fare

- Non importare da `qt_app/screens/` qui -- `core/` e una dipendenza foglia.
- Non mettere helper screen-specific in questa directory. Quelli appartengono al modulo della schermata stessa.
- Non duplicare la tupla di lingue di `i18n_bridge.py`. Leggila da li se ti serve altrove.

## Correlati

- App parent: `apps/qt_app/README.md`
- File JSON i18n: `Programma_CS2_RENAN/assets/i18n/`
- Core di playback (non-Qt): `core/playback_engine.py`
