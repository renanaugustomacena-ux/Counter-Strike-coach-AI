# `apps/qt_app/widgets/coaching/` — Coaching-specific visual components

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Purpose

Visual components that exist specifically to express coaching state — belief / threat gauges, momentum sparklines, animated counters, and underglow labels. They live separately from generic chart widgets because their visual vocabulary is opinionated for coaching feedback, not for general analytics.

## File inventory

| File | Widget | Purpose |
|------|--------|---------|
| `__init__.py` | — | Package marker. |
| `animated_counter.py` | `AnimatedCounter` | Numeric value that smoothly tweens between updates. Used for kills, headshots, rating, etc. so changes register subliminally without harsh jumps. |
| `belief_threat_gauge.py` | `BeliefThreatGauge` | Two-axis gauge: vertical bar for **belief** (RAP coach confidence in current decision), horizontal bar for **threat** (current threat level). Drives the live coach overlay during tactical replays. |
| `momentum_sparkline.py` | `MomentumSparkline` | Round-by-round momentum spark (cumulative K-D delta) with green-above / red-below fill. Compact variant of `widgets/charts/momentum_chart.py` for inline display in coaching cards. |
| `underglow_label.py` | `UnderglowLabel` | Label with a subtle bottom glow whose color encodes severity (info / warning / critical). Coaching insights use this for the headline. |

## Why these are not in `widgets/charts/`

`charts/` contains analytics primitives that read DataFrames and produce neutral visualisations. The coaching widgets here are **opinionated** — they lean into emotional resonance (animated transitions, gauge metaphors, underglow signalling) because the coaching mode is meant to be *felt*, not just read. Mixing them with neutral analytics primitives blurs the visual vocabulary.

## Conventions

### Animation timing

Everything that moves uses `core/animation.py` easing presets — never `QPropertyAnimation` with hand-rolled curves. Keeps timing consistent across the app.

### Severity colors

`UnderglowLabel` reads severity colors from `core/design_tokens.py`:

| Severity | Token | Tone |
|----------|-------|------|
| `info` | `accent.info` | Calm blue / cyan |
| `warning` | `accent.warning` | Amber |
| `critical` | `accent.critical` | Red, slight pulse on appearance |

### Accessibility

- The belief / threat gauge is paired with text values so users with reduced colour perception can still parse the state.
- Animated counters respect `prefers-reduced-motion` — when the user disables motion in OS settings, transitions snap instead of tweening.
- `setAccessibleName()` is set on every widget so screen readers can announce gauge values.

## Integration

```
apps/qt_app/screens/coach_screen.py
    +-- BeliefThreatGauge (live coach overlay)
    +-- AnimatedCounter   (round score)
    +-- UnderglowLabel    (insight headline)

apps/qt_app/screens/match_detail_screen.py
    +-- MomentumSparkline (per-round momentum strip)
    +-- AnimatedCounter   (match-level stat updates)
```

## Do not

- Do not place generic, theme-neutral charts here. They go in `widgets/charts/`.
- Do not bake severity colors into widget code. Pull from `design_tokens.py`.
- Do not animate without checking `prefers-reduced-motion` (query via `core/animation.py:reduced_motion()`).

## Related

- Generic charts: `apps/qt_app/widgets/charts/README.md`
- Design tokens: `apps/qt_app/core/design_tokens.py`
- Animation core: `apps/qt_app/core/animation.py`
- Coaching backend: `Programma_CS2_RENAN/backend/coaching/README.md`
- Parent: `apps/qt_app/widgets/README.md`
