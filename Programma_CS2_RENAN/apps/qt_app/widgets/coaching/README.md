# `apps/qt_app/widgets/coaching/` — Coaching-specific visual components

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Coaching-specific visual widgets. The package hosts `ChatPanel`, the embedded coach
chat introduced by the design-atlas rebuild (frames 06/07): message bubbles, a mono
provenance meta line, availability states, and the input row. It is hosted by
`screens/coach_screen.py` — the old QDockWidget chat dock was removed with the
frames-06/07 redesign. (An earlier generation of widgets — `AnimatedCounter`,
`BeliefThreatGauge`, `MomentumSparkline`, `UnderglowLabel` — was removed in PR #32,
commit `697bac7`; see the historical note below.)

## File inventory

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports (`ChatPanel`). |
| `chat_panel.py` | `ChatPanel` — embedded coach chat panel hosted by CoachScreen. |

## Historical note

The removed widgets were opinionated coaching-mode components designed for emotional
resonance: animated numeric tweens, a two-axis belief/threat gauge, an inline K-D
momentum spark, and a severity-colored underglow label. They were eliminated because
they depended on internal APIs that were consolidated, and their functionality was
absorbed into the coaching screen and the shared charts package.

If coaching-specific visual widgets are needed again, this directory is the correct
home for them. Follow these conventions from the original design:

- Pull all colors from `core/design_tokens.py` — no hardcoded hex values.
- Use `core/animation.py` / `core/easing.py` presets for all motion.
- Pair every visual encoding with a text value for accessibility.
- Set `setAccessibleName()` on every widget.

## Related

- Generic charts: `apps/qt_app/widgets/charts/README.md`
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Animation core: `apps/qt_app/core/animation.py`
- Coaching backend: `Programma_CS2_RENAN/backend/coaching/README.md`
- Parent: `apps/qt_app/widgets/README.md`
