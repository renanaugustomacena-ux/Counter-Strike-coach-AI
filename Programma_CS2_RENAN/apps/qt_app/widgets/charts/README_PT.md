# `apps/qt_app/widgets/charts/` — Widgets de gráficos do dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Widgets de gráfico QPainter usados nas telas de dashboard, performance, comparação pro e match-detail. Cada widget é um `QWidget` personalizado com `paintEvent`, expondo uma pequena API Pythonic para a ViewModel chamadora. **QtCharts não é usado em lugar nenhum** — está disponível apenas sob licença GPLv3 ou comercial e foi removido por conformidade de licença; `tests/test_charts.py::TestQtChartsRetired` falha a suite se uma referência `QtCharts`/`QChart` reaparecer sob `apps/qt_app/`.

## Inventário de arquivos

| Arquivo | Widget | Usado por |
|---------|--------|-----------|
| `__init__.py` | (re-exports) | — |
| `economy_chart.py` | `EconomyChart` | Match Detail (barras de valor de equipamento por round, coloração por lado, escala $K) |
| `mini_sparkline.py` | `MiniSparkline` | Card hero da última partida na home (linha de tendência compacta) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (delta cumulativo kill-death com fill verde/vermelho) |
| `radar_chart.py` | `RadarChart` | Comparação Pro (radar pentagonal de skills, overlay usuário-vs-pro) |
| `rating_sparkline.py` | `RatingSparkline` | Match Detail / Desempenho (tendência de rating com baseline 1.0) |
| `utility_bar_chart.py` | `UtilityBarChart` | Match Detail / Desempenho (barras de uso de utilitários) |

## Convenções

### Paleta de cores

Todos os gráficos resolvem cores de `core/design_tokens.py` via `get_tokens()`:

- **Fundo do gráfico:** `tokens.chart_bg`
- **Série primária / secundária (CT / T):** `tokens.chart_line_primary` / `tokens.chart_line_secondary`
- **Texto e eixos:** `tokens.text_primary` / `tokens.text_secondary`

Hard-codar valores hexadecimais é um code smell — adicione um token primeiro.

### Ciclo de vida do widget

`EconomyChart` e `MomentumChart` armazenam os dados dos rounds em `plot(rounds)` e repintam;
os demais gráficos armazenam dados em seus métodos `set_*`. Todo o desenho acontece em `paintEvent()`.

### Consciência de tema

Os gráficos resolvem cada cor do conjunto de tokens ativo (`get_tokens()`) quando são construídos ou re-plotados, então uma troca de tema os reestiliza no próximo plot — não guardam nenhuma paleta hard-coded.

### Acessibilidade

- Gráficos que codificam informação por cor também incluem labels de texto (ticks de eixo, legenda, anotações de valor).
- Adicione um resumo `setAccessibleDescription()` para usuários de leitores de tela ao introduzir um novo gráfico.
- Mantenha o contraste de cor em WCAG 2.0 AA contra o fundo do tema ativo.

## Adicionando um gráfico

1. Subclasse `QWidget`, armazene dados em um método `set_*`/`plot()`, chame `self.update()`, desenhe em `paintEvent()`. (Nunca QtCharts — veja a nota de licença acima.)
2. Aceite um objeto ViewModel tipado ou uma lista tipada — nunca DataFrames crus.
3. Puxe as cores de `core/design_tokens` via `get_tokens()`.
4. Adicione uma descrição para leitores de tela via `setAccessibleDescription()`.
5. Resolva todas as cores no momento do plot para que uma troca de tema reestilize no próximo plot.
6. Adicione o widget à tabela de inventário acima.

## Não fazer

- Não commitar escolhas de cor que não estejam em `design_tokens.py`.

## Relacionados

- Dados backend: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Parent: `apps/qt_app/widgets/README.md`
