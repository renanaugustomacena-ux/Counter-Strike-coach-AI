# `apps/qt_app/widgets/charts/` — Widgets de gráficos do dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Widgets de gráfico baseados em Matplotlib, usados nas telas de dashboard, performance e match-detail. Cada widget renderiza uma figura Matplotlib em um canvas compatível com Qt (`FigureCanvasQTAgg`) e expõe uma pequena API Pythonic para a ViewModel chamadora — a superfície da API do Matplotlib não vaza para o resto da UI.

## Inventário de arquivos

| Arquivo | Widget | Usado por |
|---------|--------|-----------|
| `__init__.py` | (re-exports) | — |
| `economy_chart.py` | `EconomyChart` | Match Detail (barras de valor de equipamento por round) |
| `mini_sparkline.py` | `MiniSparkline` | Hero stats strip, dashboards (linha de tendência compacta) |
| `momentum_chart.py` | `MomentumChart` | Match Detail (delta cumulativo kill-death com fill verde/vermelho) |
| `radar_chart.py` | `RadarChart` | Performance (radar de skill com 5 eixos), Pro Comparison |
| `rating_sparkline.py` | `RatingSparkline` | Performance (progressão de rating com linhas de referência em 1.0 / 1.1 / 0.9) |
| `round_heatmap.py` | `RoundHeatmap` | Match Detail (grade de resultado por round colorida por win/loss + estado da economia) |
| `trend_chart.py` | `TrendChart` | Performance (eixo duplo: rating à esquerda, ADR à direita, últimas 20 partidas) |
| `utility_bar_chart.py` | `UtilityBarChart` | Performance (barras horizontais agrupadas: usuário vs média do pro) |

## Convenções

### Paleta de cores

Todos os gráficos leem cores de `core/design_tokens.py`:

- **Lado CT:** `#5C9EE8` (azul canônico)
- **Lado T:** `#E8C95C` (dourado canônico)
- **Tendência positiva / força:** família verde
- **Tendência negativa / fraqueza:** família vermelha
- **Referência / baseline:** cinza neutro com traço pontilhado

Hard-coding de valores hex é code smell — abra um token primeiro.

### Higiene de memória

Figuras Matplotlib são pesadas. Cada widget de gráfico:

1. Chama `plt.close(fig)` após renderização para liberar a figura.
2. Mantém o canvas, não a figura, como a referência de longa vida.
3. Implementa `clear()` para liberar memória da figura entre refreshes de dados.

### Consciência de tema

Gráficos se inscrevem em `theme_engine.themeChanged` e re-renderizam com estilização apropriada ao tema. Cores de fundo, texto, grade e linhas de referência todas trocam por tema.

### Acessibilidade

- Gráficos que codificam informação por cor também incluem labels de texto (ticks de eixo, legenda, anotações de valor).
- `setAccessibleDescription()` fornece um resumo de um parágrafo para usuários de leitor de tela (P4-07 no checklist de acessibilidade do projeto).
- O contraste de cor atende WCAG 2.0 AA contra o background do tema ativo.

## Adicionando um gráfico

1. Faça subclasse de `MatplotlibWidget` (definido em `apps/qt_app/widgets/charts/__init__.py` — fornece o canvas + a disciplina de `plt.close()`).
2. Implemente `render(data)` — aceite um objeto tipado da ViewModel, nunca DataFrames brutos.
3. Puxe cores de `core/design_tokens`.
4. Adicione uma descrição para leitor de tela via `setAccessibleDescription()`.
5. Inscreva-se em `theme_engine.themeChanged` e re-renderize ao trocar de tema.
6. Adicione o widget à tabela de inventário acima.

## Não faça

- Não importe `matplotlib.pyplot` diretamente em uma tela — passe por um widget de gráfico.
- Não mute a figura após `render()` retornar; crie uma nova figura no refresh de dados.
- Não comite escolhas de cor que não estejam em `design_tokens.py`.

## Relacionados

- Dados do backend: `Programma_CS2_RENAN/backend/reporting/analytics.py` (`AnalyticsEngine`)
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Theme engine: `apps/qt_app/core/theme_engine.py`
- Pai: `apps/qt_app/widgets/README.md`
