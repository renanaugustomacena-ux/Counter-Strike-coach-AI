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
| `animation.py` | Primitive di animazione Qt riutilizzabili (wrapper `QPropertyAnimation`, preset di easing, helper parallel/sequence). |
| `app_state.py` | Singleton di stato a livello applicativo -- schermata corrente, tema, lingua, hub di segnali per broadcast cross-screen. |
| `design_tokens.py` | Design token tematizzati CS2 (colori, spaziature, dimensioni tipografiche) consumati da `qss_generator.py`. |
| `easing.py` | Curve di easing nominate (`ease_out_cubic`, `ease_in_out_quart`, ecc.) che supportano `animation.py`. |
| `i18n_bridge.py` | `QtLocalizationManager` -- tupla di lingue `("en", "pt", "it")` (riga 49), caricamento JSON da `assets/i18n/`, hot-swap al cambio di lingua. |
| `icons.py` | Registro di icone SVG con override di colore theme-aware. |
| `match_utils.py` | Helper puri per la formattazione dei metadati di match (data, nome mappa, punteggio). |
| `qss_generator.py` | Genera Qt Style Sheet a partire da `design_tokens.py` + il tema attivo. |
| `qt_playback_engine.py` | Driver di playback Qt-nativo che incapsula `core/playback_engine.PlaybackEngine` con avanzamento tick guidato da `QTimer`. |
| `sound.py` | Audio di notifica (toast, achievement). Caricamento lazy; degrada silenziosamente se il backend audio non e disponibile. |
| `svg_icon_provider.py` | `QQmlImageProvider` per icone SVG -- usato dalla web view embedded. |
| `theme_engine.py` | Commuta tra i temi CS2 / CSGO / CS1.6, emette il segnale `themeChanged`. |
| `typography.py` | Registrazione font (Roboto, fallback monospaziato), scala dimensione font legata al setting `FONT_SIZE`. |
| `web_bridge.py` | Bridge bidirezionale tra Qt e la `web/tactical-viewer/` embedded (TypeScript) -- slot e segnali `QWebChannel`. |
| `widgets_helpers.py` | Piccoli helper di convenienza Qt (centred-on-screen, find-ancestor, signal-disconnect-all). |
| `worker.py` | Pattern worker `QThread` con supporto per cancellazione -- usato dai ViewModel per il caricamento in background. |

## Concetti chiave

### Singleton di stato applicativo (`app_state.py`)

Centralizza i broadcast cross-screen. I ViewModel emettono attraverso `app_state.bus`, le schermate sottoscrivono. Evita l'alternativa di cablare ogni schermata direttamente a ogni altra schermata.

### Tupla di localizzazione (`i18n_bridge.py:49`)

La lista delle lingue e `("en", "pt", "it")` -- la **singola sorgente di verita** per quali lingue l'applicazione supporta. Aggiungere una quarta lingua richiede modifiche qui, in `assets/i18n/`, e nel selettore di lingua della schermata Settings (vedi `assets/README.md` per la procedura completa).

### Theme engine (`theme_engine.py`)

Tre temi (CS2 / CSGO / CS1.6). Lo switch emette `themeChanged`; `qss_generator.py` rigenera lo style sheet; ogni widget sottoscritto a `setStyleSheet()` raccoglie il cambiamento senza riavvio.

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
