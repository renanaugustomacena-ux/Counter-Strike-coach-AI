# `apps/qt_app/widgets/coaching/` — Componentes visuais específicos de coaching

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Propósito

Componentes visuais que existem especificamente para expressar o estado de coaching — gauges de belief / threat, sparklines de momentum, contadores animados e labels com underglow. Eles vivem separados dos widgets genéricos de gráficos porque seu vocabulário visual é opinativo e voltado para feedback de coaching, não para analytics gerais.

## Inventário de arquivos

| Arquivo | Widget | Propósito |
|------|--------|---------|
| `__init__.py` | — | Marcador de pacote. |
| `animated_counter.py` | `AnimatedCounter` | Valor numérico que faz tween suave entre atualizações. Usado para kills, headshots, rating, etc., para que mudanças se registrem de forma subliminar, sem saltos bruscos. |
| `belief_threat_gauge.py` | `BeliefThreatGauge` | Gauge de dois eixos: barra vertical para **belief** (confiança do RAP coach na decisão atual), barra horizontal para **threat** (nível de ameaça atual). Alimenta o overlay ao vivo do coach durante replays táticos. |
| `momentum_sparkline.py` | `MomentumSparkline` | Spark de momentum round a round (delta cumulativo K-D) com preenchimento verde-acima / vermelho-abaixo. Variante compacta de `widgets/charts/momentum_chart.py` para exibição inline em cards de coaching. |
| `underglow_label.py` | `UnderglowLabel` | Label com um glow sutil na parte inferior cuja cor codifica severidade (info / warning / critical). Os insights de coaching usam isto para a manchete. |

## Por que estes não estão em `widgets/charts/`

`charts/` contém primitivos de analytics que leem DataFrames e produzem visualizações neutras. Os widgets de coaching aqui são **opinativos** — eles apostam na ressonância emocional (transições animadas, metáforas de gauge, sinalização por underglow) porque o modo coaching foi feito para ser *sentido*, não apenas lido. Misturá-los com primitivos de analytics neutros borra o vocabulário visual.

## Convenções

### Timing de animação

Tudo que se move usa os presets de easing de `core/animation.py` — nunca `QPropertyAnimation` com curvas feitas à mão. Isso mantém o timing consistente em todo o app.

### Cores de severidade

`UnderglowLabel` lê as cores de severidade de `core/design_tokens.py`:

| Severidade | Token | Tom |
|----------|-------|------|
| `info` | `accent.info` | Azul / ciano calmo |
| `warning` | `accent.warning` | Âmbar |
| `critical` | `accent.critical` | Vermelho, com leve pulso ao aparecer |

### Acessibilidade

- O gauge de belief / threat é pareado com valores em texto para que usuários com percepção reduzida de cores ainda consigam interpretar o estado.
- Contadores animados respeitam `prefers-reduced-motion` — quando o usuário desabilita movimento nas configurações do SO, as transições saltam em vez de fazer tween.
- `setAccessibleName()` é definido em todo widget para que screen readers possam anunciar os valores do gauge.

## Integração

```
apps/qt_app/screens/coach_screen.py
    +-- BeliefThreatGauge (overlay ao vivo do coach)
    +-- AnimatedCounter   (placar do round)
    +-- UnderglowLabel    (manchete do insight)

apps/qt_app/screens/match_detail_screen.py
    +-- MomentumSparkline (faixa de momentum por round)
    +-- AnimatedCounter   (atualizações de stat em nível de partida)
```

## Não faça

- Não coloque gráficos genéricos e neutros em relação ao tema aqui. Eles vão em `widgets/charts/`.
- Não embuta cores de severidade no código do widget. Puxe de `design_tokens.py`.
- Não anime sem checar `prefers-reduced-motion` (consulte via `core/animation.py:reduced_motion()`).

## Relacionados

- Gráficos genéricos: `apps/qt_app/widgets/charts/README.md`
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Núcleo de animação: `apps/qt_app/core/animation.py`
- Backend de coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Pacote pai: `apps/qt_app/widgets/README.md`
