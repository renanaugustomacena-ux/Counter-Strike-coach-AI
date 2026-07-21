# `apps/qt_app/widgets/charts/` -- Widget grafici per la dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Widget grafici basati su QtCharts e QPainter usati nelle schermate dashboard, performance e match-detail. Ogni widget racchiude un `QChartView` (per grafici basati su `QChart`) o un `QWidget` personalizzato con `paintEvent` (per sparkline QPainter), esponendo una piccola API Pythonic al ViewModel chiamante.

## Inventario File

| File | Widget | Usato Da |
|------|--------|----------|
| `__init__.py` | (ri-esporti) | -- |
| `economy_chart.py` | `EconomyChart` | Match Detail (barre del valore equipaggiamento per round) |
| `mini_sparkline.py` | `MiniSparkline` | Hero stats strip, dashboard (linea di trend compatta) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (delta cumulativo kill-death con riempimento verde/rosso) |

## Convenzioni

### Palette di colori

Tutti i grafici leggono i colori da `core/design_tokens.py`:

- **Lato CT:** `#5C9EE8` (blu canonico)
- **Lato T:** `#E8C95C` (oro canonico)
- **Trend positivo / forza:** famiglia verde
- **Trend negativo / debolezza:** famiglia rossa
- **Riferimento / baseline:** grigio attenuato con tratteggio

Hard-codare valori esadecimali e un code smell -- apri prima un token.

### Igiene di memoria

Le figure Matplotlib sono pesanti. Ogni widget grafico:

1. Chiama `plt.close(fig)` dopo il rendering per liberare la figura.
2. Tiene il canvas, non la figura, come riferimento di lunga durata.
3. Implementa `clear()` per rilasciare la memoria della figura tra refresh dei dati.

### Theme awareness

I grafici sottoscrivono a `theme_engine.themeChanged` e si ri-renderizzano con styling theme-appropriate. Sfondo, testo, griglia e colori delle linee di riferimento si ribaltano tutti per tema.

### Accessibilita

- I grafici che codificano informazione tramite colore includono anche label testuali (tick degli assi, legenda, annotazioni di valore).
- `setAccessibleDescription()` fornisce un riassunto di un paragrafo per gli utenti screen-reader (P4-07 nella checklist di accessibilita del progetto).
- Il contrasto colore rispetta WCAG 2.0 AA contro lo sfondo del tema attivo.

## Aggiungere un grafico

1. Sottoclassi `MatplotlibWidget` (definito in `apps/qt_app/widgets/charts/__init__.py` -- fornisce il canvas + la disciplina `plt.close()`).
2. Implementa `render(data)` -- accetta un oggetto ViewModel tipizzato, mai DataFrame grezzi.
3. Prendi i colori da `core/design_tokens`.
4. Aggiungi una descrizione screen-reader tramite `setAccessibleDescription()`.
5. Sottoscrivi a `theme_engine.themeChanged` e ri-renderizza al cambio di tema.
6. Aggiungi il widget alla tabella di inventario sopra.

## Da non fare

- Non importare `matplotlib.pyplot` direttamente in una schermata -- passa attraverso un widget grafico.
- Non mutare la figura dopo il return di `render()`; crea una nuova figura al refresh dati.
- Non committare scelte di colore che non sono in `design_tokens.py`.

## Correlati

- Dati backend: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design token: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
