# `apps/qt_app/widgets/charts/` — Widgets de graficos do dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Widgets de grafico QPainter usados nas telas de home, performance, comparacao pro e match-detail. Cada widget e um `QWidget` personalizado com `paintEvent`, expondo uma pequena API Pythonic para a ViewModel chamadora. **QtCharts nao e usado em lugar nenhum** — esta disponivel apenas sob licenca GPLv3 ou comercial e foi removido por conformidade de licenca; `Programma_CS2_RENAN/tests/test_charts.py::TestQtChartsRetired` falha a suite se uma referencia `QtCharts`/`QChart` reaparecer sob `apps/qt_app/`.

## Inventario de arquivos

| Arquivo | Widget | Usado por |
|---------|--------|-----------|
| `__init__.py` | helper `token_color()`, painter compartilhado `paint_chart_empty()` para estado vazio, reexportacoes (`EconomyChart`, `MomentumChart`, `RadarChart`) | `token_color()` parseia strings `#RRGGBB` / `rgb()` / `rgba()` de design tokens em `QColor`; `paint_chart_empty()` desenha um estado de repouso circulo-e-tick usado por `EconomyChart` e `MomentumChart` |
| `economy_chart.py` | `EconomyChart` | Match Detail (barras de valor de equipamento por round, coloracao por lado, escala $, divisor `set_half_marker()`) |
| `mini_sparkline.py` | `MiniSparkline` | Card hero da ultima partida na home (linha de tendencia compacta, via `components/last_match_hero.py`) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (barras de swing K-D por round em torno de um eixo zero, coloridas por lado, divisor HALF) |
| `radar_chart.py` | `RadarChart` | Comparacao Pro (radar de skill com N eixos, N >= 3 — a tela usa 8 eixos; overlay de serie dupla usuario-vs-pro) |
| `rating_sparkline.py` | `RatingSparkline` | Performance (tendencia de rating com linhas de referencia HLTV em 0.90 / 1.00 / 1.10) |
| `utility_bar_chart.py` | `UtilityBarChart` | Performance (barras agrupadas voce-vs-pro via `set_rows()`, ou serie unica via `set_single()`) |

## Convencoes

### Paleta de cores

Todos os graficos resolvem cores de `core/design_tokens.py` via `get_tokens()`:

- **Fundo do grafico:** `tokens.chart_bg`
- **Coloracao por lado (CT / T):** `tokens.chart_line_primary` (CT) / `tokens.chart_line_secondary` (T) — usada por `EconomyChart` e `MomentumChart` para distincao por lado nos rounds
- **Serie do jogador:** `tokens.accent_primary` (os dados do jogador falam o acento do tema)
- **Serie de comparacao / pro:** info cyan (`tokens.info`) — a voz de benchmark pro em `RadarChart` e `UtilityBarChart`, deliberadamente distinta da coloracao por lado CT / T
- **Texto e eixos:** `tokens.text_primary` / `tokens.text_secondary`

Hard-codar valores hexadecimais e um code smell — adicione um token primeiro.

### Ciclo de vida do widget

`EconomyChart` e `MomentumChart` armazenam os dados dos rounds em `plot(rounds)` e repintam;
os demais graficos armazenam dados em seus metodos `set_*`. Todo o desenho acontece em `paintEvent()`.

### Consciencia de tema

Os graficos resolvem cada cor do conjunto de tokens ativo (`get_tokens()`) dentro de `paintEvent()`, entao uma troca de tema os reestiliza no proximo repaint — nao guardam nenhuma paleta hard-coded.

### Acessibilidade

- Graficos que codificam informacao por cor tambem incluem labels de texto (ticks de eixo, legenda, anotacoes de valor).
- Adicione um resumo `setAccessibleDescription()` para usuarios de leitores de tela ao introduzir um novo grafico.
- Mantenha o contraste de cor em WCAG 2.0 AA contra o fundo do tema ativo.

## Adicionando um grafico

1. Subclasse `QWidget`, armazene dados em um metodo `set_*`/`plot()`, chame `self.update()`, desenhe em `paintEvent()`. (Nunca QtCharts — veja a nota de licenca acima.)
2. Aceite um objeto ViewModel tipado ou uma lista tipada — nunca DataFrames crus.
3. Puxe as cores de `core/design_tokens` via `get_tokens()`.
4. Adicione uma descricao para leitores de tela via `setAccessibleDescription()`.
5. Resolva todas as cores dentro de `paintEvent()` para que uma troca de tema reestilize no proximo repaint.
6. Adicione o widget a tabela de inventario acima.

## Nao fazer

- Nao commitar escolhas de cor que nao estejam em `design_tokens.py`.

## Relacionados

- Dados backend: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
