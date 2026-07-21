# `apps/qt_app/widgets/coaching/` — Componentes visuais específicos de coaching

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Propósito

Pacote de namespace reservado para widgets visuais específicos de coaching. Os quatro
widgets especializados que antes viviam aqui — `AnimatedCounter`, `BeliefThreatGauge`,
`MomentumSparkline` e `UnderglowLabel` — foram removidos na PR #32 (commit `697bac7`)
como parte da limpeza de módulos órfãos. O feedback de coaching agora é renderizado
diretamente em `screens/coach_screen.py` via widgets Qt padrão e
`widgets/charts/momentum_chart.py`.

## Inventário de arquivos

| Arquivo | Propósito |
|---------|-----------|
| `__init__.py` | Marcador de pacote (vazio). |

## Nota histórica

Os widgets removidos eram componentes opinativos do modo coaching, projetados para
criar ressonância emocional: tweens numéricos animados, um gauge de dois eixos
belief/threat, um spark de momentum K-D inline e uma label com underglow colorido
por severidade. Foram eliminados porque dependiam de APIs internas que foram
consolidadas, e sua funcionalidade foi absorvida pela tela de coaching e pelo
pacote compartilhado de gráficos.

Se no futuro forem necessários novos widgets visuais específicos de coaching, este
diretório é o local correto para eles. Siga estas convenções do design original:

- Puxar todas as cores de `core/design_tokens.py` — sem valores hex hardcoded.
- Usar os presets de easing de `core/animation.py` para todo movimento.
- Respeitar `prefers-reduced-motion` via `core/animation.py:reduced_motion()`.
- Parear cada codificação visual com um valor textual para acessibilidade.
- Definir `setAccessibleName()` em todo widget.

## Relacionados

- Gráficos genéricos: `apps/qt_app/widgets/charts/README.md`
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Núcleo de animação: `apps/qt_app/core/animation.py`
- Backend de coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Pacote pai: `apps/qt_app/widgets/README.md`
