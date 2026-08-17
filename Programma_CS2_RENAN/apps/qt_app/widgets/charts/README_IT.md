# `apps/qt_app/widgets/charts/` -- Widget grafici per la dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Widget grafici QPainter usati nelle schermate dashboard, performance, confronto pro e match-detail. Ogni widget e un `QWidget` personalizzato con `paintEvent`, che espone una piccola API Pythonic al ViewModel chiamante. **QtCharts non e usato da nessuna parte** -- e disponibile solo con licenza GPLv3 o commerciale ed e stato rimosso per conformita di licenza; `tests/test_charts.py::TestQtChartsRetired` fa fallire la suite se un riferimento `QtCharts`/`QChart` ricompare sotto `apps/qt_app/`.

## Inventario File

| File | Widget | Usato Da |
|------|--------|----------|
| `__init__.py` | (ri-esporti) | -- |
| `economy_chart.py` | `EconomyChart` | Match Detail (barre valore equipaggiamento per round, colorazione per lato, scala $K) |
| `mini_sparkline.py` | `MiniSparkline` | Card hero dell'ultima partita nella home (linea di trend compatta) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (delta cumulativo kill-death con riempimento verde/rosso) |
| `radar_chart.py` | `RadarChart` | Confronto Pro (radar pentagonale delle skill, overlay utente-vs-pro) |
| `rating_sparkline.py` | `RatingSparkline` | Match Detail / Prestazioni (tendenza rating con baseline 1.0) |
| `utility_bar_chart.py` | `UtilityBarChart` | Match Detail / Prestazioni (barre uso utility) |

## Convenzioni

### Palette di colori

Tutti i grafici risolvono i colori da `core/design_tokens.py` tramite `get_tokens()`:

- **Sfondo grafico:** `tokens.chart_bg`
- **Serie primaria / secondaria (CT / T):** `tokens.chart_line_primary` / `tokens.chart_line_secondary`
- **Testo e assi:** `tokens.text_primary` / `tokens.text_secondary`

Hard-codare valori esadecimali e un code smell -- aggiungi prima un token.

### Ciclo di vita del widget

`EconomyChart` e `MomentumChart` memorizzano i dati dei round in `plot(rounds)` e ridisegnano;
gli altri grafici memorizzano i dati nei loro metodi `set_*`. Tutto il disegno avviene in `paintEvent()`.

### Theme awareness

I grafici risolvono ogni colore dal set di token attivo (`get_tokens()`) quando vengono costruiti o ri-plottati, quindi un cambio di tema li ristilizza al plot successivo -- non contengono alcuna palette hard-coded.

### Accessibilita

- I grafici che codificano informazione tramite colore includono anche label testuali (tick degli assi, legenda, annotazioni di valore).
- Aggiungi un riassunto `setAccessibleDescription()` per gli utenti screen-reader quando introduci un nuovo grafico.
- Mantieni il contrasto colore a WCAG 2.0 AA contro lo sfondo del tema attivo.

## Aggiungere un grafico

1. Sottoclassa `QWidget`, memorizza i dati in un metodo `set_*`/`plot()`, chiama `self.update()`, disegna in `paintEvent()`. (Mai QtCharts -- vedi la nota di licenza sopra.)
2. Accetta un oggetto ViewModel tipizzato o una lista tipizzata -- mai DataFrame grezzi.
3. Prendi i colori da `core/design_tokens` tramite `get_tokens()`.
4. Aggiungi una descrizione screen-reader tramite `setAccessibleDescription()`.
5. Risolvi tutti i colori al momento del plot cosi un cambio tema ristilizza al plot successivo.
6. Aggiungi il widget alla tabella di inventario sopra.

## Da non fare

- Non committare scelte di colore che non sono in `design_tokens.py`.

## Correlati

- Dati backend: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design token: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
