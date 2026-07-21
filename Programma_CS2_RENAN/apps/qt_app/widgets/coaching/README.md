# `apps/qt_app/widgets/coaching/` — Coaching-specific visual components

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Namespace package reserved for coaching-specific visual widgets. The four specialized
widgets that previously lived here — `AnimatedCounter`, `BeliefThreatGauge`,
`MomentumSparkline`, and `UnderglowLabel` — were removed in PR #32 (commit `697bac7`)
as part of the orphan-module cleanup. Coaching feedback is now rendered directly in
`screens/coach_screen.py` via standard Qt widgets and `widgets/charts/momentum_chart.py`.

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker (empty). |

## Historical note

The removed widgets were opinionated coaching-mode components designed for emotional
resonance: animated numeric tweens, a two-axis belief/threat gauge, an inline K-D
momentum spark, and a severity-colored underglow label. They were eliminated because
they depended on internal APIs that were consolidated, and their functionality was
absorbed into the coaching screen and the shared charts package.

If coaching-specific visual widgets are needed again, this directory is the correct
home for them. Follow these conventions from the original design:

- Pull all colors from `core/design_tokens.py` — no hardcoded hex values.
- Use `core/animation.py` easing presets for all motion.
- Respect `prefers-reduced-motion` via `core/animation.py:reduced_motion()`.
- Pair every visual encoding with a text value for accessibility.
- Set `setAccessibleName()` on every widget.

## Related

- Generic charts: `apps/qt_app/widgets/charts/README.md`
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Animation core: `apps/qt_app/core/animation.py`
- Coaching backend: `Programma_CS2_RENAN/backend/coaching/README.md`
- Parent: `apps/qt_app/widgets/README.md`
