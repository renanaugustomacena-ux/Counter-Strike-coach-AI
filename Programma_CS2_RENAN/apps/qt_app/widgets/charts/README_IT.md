# `apps/qt_app/widgets/charts/` — Widget grafici per la dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Widget grafici QPainter usati nelle schermate home, performance, confronto pro e match-detail. Ogni widget e un `QWidget` personalizzato con `paintEvent`, che espone una piccola API Pythonic al ViewModel chiamante. **QtCharts non e usato da nessuna parte** — e disponibile solo con licenza GPLv3 o commerciale ed e stato rimosso per conformita di licenza; `Programma_CS2_RENAN/tests/test_charts.py::TestQtChartsRetired` fa fallire la suite se un riferimento `QtCharts`/`QChart` ricompare sotto `apps/qt_app/`.

## Inventario dei file

| File | Widget | Usato Da |
|------|--------|----------|
| `__init__.py` | helper `token_color()`, painter condiviso `paint_chart_empty()` per lo stato vuoto, ri-esportazioni (`EconomyChart`, `MomentumChart`, `RadarChart`) | `token_color()` parsa stringhe `#RRGGBB` / `rgb()` / `rgba()` dei design token in `QColor`; `paint_chart_empty()` disegna uno stato a riposo cerchio-e-tick usato da `EconomyChart` e `MomentumChart` |
| `economy_chart.py` | `EconomyChart` | Match Detail (barre valore equipaggiamento per round, colorazione per lato, scala $, divisore `set_half_marker()`) |
| `mini_sparkline.py` | `MiniSparkline` | Card hero dell'ultima partita nella home (linea di trend compatta, tramite `components/last_match_hero.py`) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (barre swing K-D per round attorno a un asse zero, colorate per lato, divisore HALF) |
| `radar_chart.py` | `RadarChart` | Confronto Pro (radar skill a N assi, N >= 3 — la schermata usa 8 assi; overlay doppia serie utente-vs-pro) |
| `rating_sparkline.py` | `RatingSparkline` | Performance (tendenza rating con linee di riferimento HLTV a 0.90 / 1.00 / 1.10) |
| `utility_bar_chart.py` | `UtilityBarChart` | Performance (barre raggruppate tu-vs-pro tramite `set_rows()`, o serie singola tramite `set_single()`) |

## Convenzioni

### Palette di colori

Tutti i grafici risolvono i colori da `core/design_tokens.py` tramite `get_tokens()`:

- **Sfondo grafico:** `tokens.chart_bg`
- **Colorazione per lato (CT / T):** `tokens.chart_line_primary` (CT) / `tokens.chart_line_secondary` (T) — usata da `EconomyChart` e `MomentumChart` per la distinzione per lato nei round
- **Serie giocatore:** `tokens.accent_primary` (i dati del giocatore parlano l'accento del tema)
- **Serie confronto / pro:** info cyan (`tokens.info`) — la voce benchmark pro in `RadarChart` e `UtilityBarChart`, deliberatamente distinta dalla colorazione per lato CT / T
- **Testo e assi:** `tokens.text_primary` / `tokens.text_secondary`

Hard-codare valori esadecimali e un code smell — aggiungi prima un token.

### Ciclo di vita del widget

`EconomyChart` e `MomentumChart` memorizzano i dati dei round in `plot(rounds)` e ridisegnano;
gli altri grafici memorizzano i dati nei loro metodi `set_*`. Tutto il disegno avviene in `paintEvent()`.

### Theme awareness

I grafici risolvono ogni colore dal set di token attivo (`get_tokens()`) dentro `paintEvent()`, quindi un cambio di tema li ristilizza al repaint successivo — non contengono alcuna palette hard-coded.

### Accessibilita

- I grafici che codificano informazione tramite colore includono anche label testuali (tick degli assi, legenda, annotazioni di valore).
- Aggiungi un riassunto `setAccessibleDescription()` per gli utenti screen-reader quando introduci un nuovo grafico.
- Mantieni il contrasto colore a WCAG 2.0 AA contro lo sfondo del tema attivo.

## Aggiungere un grafico

1. Sottoclassa `QWidget`, memorizza i dati in un metodo `set_*`/`plot()`, chiama `self.update()`, disegna in `paintEvent()`. (Mai QtCharts — vedi la nota di licenza sopra.)
2. Accetta un oggetto ViewModel tipizzato o una lista tipizzata — mai DataFrame grezzi.
3. Prendi i colori da `core/design_tokens` tramite `get_tokens()`.
4. Aggiungi una descrizione screen-reader tramite `setAccessibleDescription()`.
5. Risolvi tutti i colori dentro `paintEvent()` cosi un cambio tema ristilizza al repaint successivo.
6. Aggiungi il widget alla tabella di inventario sopra.

## Da non fare

- Non committare scelte di colore che non sono in `design_tokens.py`.

## Correlati

- Dati backend: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design token: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
