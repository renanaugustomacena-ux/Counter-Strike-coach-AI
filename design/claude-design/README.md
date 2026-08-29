# Claude Design bundle — Macena CS2

A sync-ready component library for **claude.ai/design** (the web design tool),
generated 2026-08-29 from the assets this folder already owned:

- values: `design/tokens/design-tokens.json` (the SSOT the app is generated from)
- vocabulary: frames 31–36 (token board, theme grid, component library,
  chart library, icon grid, typography specimen)
- assets: `design/assets/icons/sprite.svg` (22 icons, inlined),
  `motifs/tactical-grid.svg`, `wallpapers/*.svg`

## Cards (12)

| Group | Cards |
|---|---|
| Colors | CS2 palette · three-themes contract |
| Type | scale specimen (Inter / Space Grotesk / JetBrains Mono) |
| Spacing | spacing 4→48 + radius ladder |
| Components | buttons · inputs+selection · tags/StatBadge/ProgressRing · toasts · empty state |
| Charts | voice rules (Q3) · sparkline · utility bars · radar axes · per-map grid |
| Brand | icon set · frost/motif/wallpapers |

Each preview is a self-contained HTML file whose first line carries the
`<!-- @dsCard group="…" -->` marker the Design System pane indexes.

## How to sync

Run **`/design-sync`** in Claude Code (the sync command is user-triggered by
design). Point it at this directory; pick or create the "Macena CS2" design
system project when it asks. Re-run after any regeneration — it diffs and
uploads incrementally.

## Regenerating

The bundle is generated; edit the tokens JSON or the frames, then rebuild —
never hand-edit a preview to change a color (Law III: the JSON is the SSOT).
