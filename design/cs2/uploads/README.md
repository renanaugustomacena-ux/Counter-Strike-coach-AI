# Macena CS2 Coach AI — Design Atlas (Upload Bundle)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Flattened upload bundle of the design atlas for the CS2 coaching application — a self-contained copy of the 41 SVG frames plus an earlier snapshot of the design tokens, laid out flat for easy drag-and-drop into design tools. All files are SVG + HTML + JSON — zero binaries, fully portable. The canonical, structured atlas lives at `design/` (repo root); see `design/README.md`.

## File Map

```
design/cs2/uploads/
├── index.html                  ← copy of the atlas canvas (see Browser note below)
├── README.md
├── README-8252c0ae.md          ← uploaded copy of the project root README
├── design-tokens.json          ← W3C DTCG format, 3 themes — older snapshot; the
│                                 token SSOT is design/tokens/design-tokens.json
├── 01_cover.svg                Marketing (01–04)
├── 02_landing_hero.svg
├── 03_feature_showcase.svg
├── 04_pitch_slide.svg
├── 05_home.svg                 App Screens (05–20)
├── ...
├── 21_system_map.svg           Architecture Diagrams (21–30)
├── ...
├── 31_token_system.svg         Design System (31–36)
├── 36_typography_specimen.svg
├── 37_rap_7_layer_pipeline.svg          RAP Deep-Dive (37–41)
├── 38_rap_perception_cnn.svg
├── 39_rap_memory_ltc_hopfield.svg
├── 40_rap_chronovisor_multiscale.svg
└── 41_rap_self_correction_loop.svg
```

All 41 frames are 1440×900. The larger standalone architecture SVGs (`system_map.svg`, `jepa_model.svg`, `data_pipeline.svg`) are **not** part of this bundle — they live in `design/architecture/`.

## How to Use

### Browser (Claude Design / local preview)

The `index.html` here is a verbatim copy of the atlas canvas: it references the SVGs via `frames/…` and `architecture/…` relative paths, which do not resolve against this flat folder. Open the canonical canvas instead:

```bash
# open the master canvas (structured atlas)
open design/index.html
# or
firefox design/index.html
```

Works as `file://` — no server needed. Load `design/index.html` as a Claude artifact for interactive use; the individual SVGs in this folder open directly in any browser.

### Figma

1. Open any SVG frame in a text editor, copy all content.
2. In Figma: **Edit → Paste in place** — SVG lands as a flat vector frame.
3. For tokens: install the **Figma Tokens** plugin, load `design-tokens.json`.
4. Architecture frames (`21`–`30`) paste at full resolution — layers are readable.

### After Effects

1. **File → Import → File** — select any numbered `.svg` from this folder.
2. AE imports SVG as **vector shape layers** — fully animatable.
3. Use the larger SVGs in `design/architecture/` for explainer video sections (larger viewBox = more room).
4. Diagram SVGs with arrows are good candidates for **motion path** animations.

### Rive / Lottie

1. Import SVG frame into Rive canvas.
2. Assign timeline animations to shape groups (each section is a named `<g>`).
3. Export `.riv` for app embed or `.json` for Lottie/bodymovin.

### Framer

1. Drag any SVG directly onto a Framer canvas.
2. Map color tokens: `design-tokens.json` values → Framer variables.
3. Responsive: SVGs use `viewBox` — scale without pixelation.

### Gamma / Keynote / Google Slides

SVGs scale losslessly at any resolution. For slide use:

```bash
# export any frame to PNG at 2×, 3×, or 4× using Chrome headless
chromium --headless --screenshot=frame.png \
  --window-size=2880,1800 01_cover.svg
```

Or open in browser, zoom to 200%, screenshot.

### Landing Page (Tailwind)

Map tokens to `tailwind.config.js`:

```js
theme: {
  extend: {
    colors: {
      surface: { base: '#14141e', raised: '#1a1a2e', sunken: '#0f0f2e' },
      accent:  { DEFAULT: '#d96600', hover: '#e67a1a', pressed: '#b85500' },
      text:    { primary: '#dcdcdc', secondary: '#a0a0b0' },
      ok:      '#4caf50',
      warn:    '#ffaa00',
      err:     '#ff4444',
      info:    '#4a9eff',
    },
    fontFamily: {
      sans: ['Roboto', 'Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
    },
    spacing: { '4': '4px', '8': '8px', '12': '12px', '16': '16px', '24': '24px', '32': '32px' },
    borderRadius: { sm: '4px', md: '8px', lg: '16px', xl: '24px' },
  },
}
```

Drop frames as hero `<img src="01_cover.svg">` — native browser SVG rendering.

### Social Posts (1080×1080 crop)

```bash
# headless crop of any frame to square
chromium --headless --screenshot=post.png \
  --window-size=1080,1080 03_feature_showcase.svg
```

Or crop in Figma after paste.

## Themes

Three themes available in `design-tokens.json`:

| Theme | Accent | Background | Character |
|-------|--------|------------|-----------|
| **CS2** | `#d96600` orange | `#14141e` deep navy | Modern · dark · tactical |
| **CSGO** | `#617d8c` steel | `#1a1c21` dark slate | Military · muted |
| **CS1.6** | `#4db04f` green | `#121a12` terminal | Retro · hacker |

Note: this bundle's tokens and frames use the earlier CS2 palette; the current token SSOT (`design/tokens/design-tokens.json`) uses `#FF6A00` on `#0B1628`.

## RAP Deep-Dive (37–41)

Dedicated frames for the flagship **Reflexive Auto-correcting Pedagogue** — the architecture reaches reliability through self-correction, not through scale.

| Frame | Subject | What it shows |
|-------|---------|---------------|
| `37_rap_7_layer_pipeline.svg` | Full stack | Perception → Memory → Strategy → Pedagogy → Position → Chronovisor → Communication with real dims and file:line anchors |
| `38_rap_perception_cnn.svg` | Perception | 3 parallel CNN streams (ventral view / dorsal map / temporal motion) → concat [B, 128] |
| `39_rap_memory_ltc_hopfield.svg` | Memory | AutoNCP LTC(units=512, out=154) + HopfieldLayer(32 prototypes × 4 heads) + NN-MEM-01 maturity gate |
| `40_rap_chronovisor_multiscale.svg` | Self-critique | Micro (64t) + Standard (192t) + Macro (640t) scans over V(s) timeline + cross-scale dedup |
| `41_rap_self_correction_loop.svg` | The big idea | 6-stage circular loop · Humility gate (conf < 0.7 = silence) · reshaped prototypes · expert specialization · LLM-like via gradient |

## Architecture SVGs — Where They Live

The three standalone technical documents (`system_map.svg` 1920×1200, `jepa_model.svg` 1440×1080, `data_pipeline.svg` 1440×900) are **not** in this bundle — they live in `design/architecture/` at the repo root. This bundle's architecture coverage is the numbered frames `21`–`30` (plus RAP deep-dives `37`–`41`).

## Invariants (do not violate)

These are hardcoded in the architecture diagrams for reference:

| Code | Rule |
|------|------|
| `P-RSB-03` | `round_won` excluded from all 25 feature dims (label leak) |
| `NN-MEM-01` | Hopfield memory bypassed until ≥2 forward passes |
| `NN-16` | EMA `apply_shadow()` must `.clone()` shadows |
| `NN-JM-04` | `target_encoder` requires_grad=False during EMA |
| `DS-12` | MIN_DEMO_SIZE = 10 MB |
| `P-VEC-02` | NaN/Inf clamp + >5% batch → DataQualityError |
| `METADATA_DIM=25` | Sole source: `vectorizer.py` |

## Compatibility Matrix

| Tool | How |
|------|-----|
| Claude Design (web) | Load `design/index.html` as artifact; paste individual SVGs |
| Figma | Paste SVG; load tokens via Figma Tokens plugin |
| After Effects | File → Import SVG (vector shape layers) |
| Rive | Import SVG → timeline animate → export .riv |
| Lottie / bodymovin | Via Rive export or AE + bodymovin plugin |
| Framer | Drag SVG; map tokens to variables |
| Tailwind | Map `design-tokens.json` values to config |
| Gamma | Paste SVG or import image export |
| Keynote / Slides | Drag SVG (scales natively) |
| Social / video | Chrome headless → PNG at any resolution |
