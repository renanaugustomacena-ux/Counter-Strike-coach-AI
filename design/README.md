# Macena CS2 Coach AI — Design Atlas

Vector design system for the CS2 coaching application. All files are SVG + HTML + JSON — zero binaries, fully portable.

## File Map

```
design/
├── index.html                  ← master canvas (open in browser)
├── README.md
├── tokens/
│   └── design-tokens.json      ← W3C DTCG format, 3 themes
├── frames/                     ← 41 SVG frames, 1440×900 each
│   ├── 01_cover.svg            Marketing (01–04)
│   ├── 02_landing_hero.svg
│   ├── 03_feature_showcase.svg
│   ├── 04_pitch_slide.svg
│   ├── 05_home.svg             App Screens (05–20)
│   ├── ...
│   ├── 21_system_map.svg       Architecture Diagrams (21–30)
│   ├── ...
│   ├── 31_token_system.svg     Design System (31–36)
│   ├── 36_typography_specimen.svg
│   ├── 37_rap_7_layer_pipeline.svg          RAP Deep-Dive (37–41)
│   ├── 38_rap_perception_cnn.svg
│   ├── 39_rap_memory_ltc_hopfield.svg
│   ├── 40_rap_chronovisor_multiscale.svg
│   └── 41_rap_self_correction_loop.svg
├── architecture/               ← standalone deep-dive SVGs
│   ├── system_map.svg          1920×1200 full pipeline
│   ├── jepa_model.svg          1440×1080 full layer diagram
│   └── data_pipeline.svg       1440×900  25-dim vector lifecycle
└── assets/
    ├── icons/sprite.svg        SVG icon sprite
    └── wallpapers/             cs2.svg · csgo.svg · cs16.svg
```

## How to Use

### Browser (Claude Design / local preview)

```bash
# open the master canvas
open design/index.html
# or
firefox design/index.html
```

Works as `file://` — no server needed. Load `index.html` as a Claude artifact for interactive use.

### Figma

1. Open any SVG frame in a text editor, copy all content.
2. In Figma: **Edit → Paste in place** — SVG lands as a flat vector frame.
3. For tokens: install the **Figma Tokens** plugin, load `tokens/design-tokens.json`.
4. Architecture SVGs (`architecture/`) paste at full resolution — layers are readable.

### After Effects

1. **File → Import → File** — select any `.svg` from `frames/` or `architecture/`.
2. AE imports SVG as **vector shape layers** — fully animatable.
3. Use `architecture/` files for explainer video sections (larger viewBox = more room).
4. Architecture SVGs with arrows are good candidates for **motion path** animations.

### Rive / Lottie

1. Import SVG frame into Rive canvas.
2. Assign timeline animations to shape groups (each section is a named `<g>`).
3. Export `.riv` for app embed or `.json` for Lottie/bodymovin.

### Framer

1. Drag any SVG directly onto a Framer canvas.
2. Map color tokens: `tokens/design-tokens.json` values → Framer variables.
3. Responsive: SVGs use `viewBox` — scale without pixelation.

### Gamma / Keynote / Google Slides

SVGs scale losslessly at any resolution. For slide use:

```bash
# export any frame to PNG at 2×, 3×, or 4× using Chrome headless
chromium --headless --screenshot=frame.png \
  --window-size=2880,1800 frames/01_cover.svg
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

Drop frames as hero `<img src="frames/01_cover.svg">` — native browser SVG rendering.

### Social Posts (1080×1080 crop)

```bash
# headless crop of any frame to square
chromium --headless --screenshot=post.png \
  --window-size=1080,1080 frames/03_feature_showcase.svg
```

Or crop in Figma after paste.

## Themes

Three themes available in `tokens/design-tokens.json`:

| Theme | Accent | Background | Character |
|-------|--------|------------|-----------|
| **CS2** | `#d96600` orange | `#14141e` deep navy | Modern · dark · tactical |
| **CSGO** | `#617d8c` steel | `#1a1c21` dark slate | Military · muted |
| **CS1.6** | `#4db04f` green | `#0d1a0d` terminal | Retro · hacker |

## RAP Deep-Dive (37–41)

Dedicated frames for the flagship **Reflexive Auto-correcting Pedagogue** — the architecture reaches reliability through self-correction, not through scale.

| Frame | Subject | What it shows |
|-------|---------|---------------|
| `37_rap_7_layer_pipeline.svg` | Full stack | Perception → Memory → Strategy → Pedagogy → Position → Chronovisor → Communication with real dims and file:line anchors |
| `38_rap_perception_cnn.svg` | Perception | 3 parallel CNN streams (ventral view / dorsal map / temporal motion) → concat [B, 128] |
| `39_rap_memory_ltc_hopfield.svg` | Memory | AutoNCP LTC(units=512, out=154) + HopfieldLayer(32 prototypes × 4 heads) + NN-MEM-01 maturity gate |
| `40_rap_chronovisor_multiscale.svg` | Self-critique | Micro (64t) + Standard (192t) + Macro (640t) scans over V(s) timeline + cross-scale dedup |
| `41_rap_self_correction_loop.svg` | The big idea | 6-stage circular loop · Humility gate (conf < 0.7 = silence) · reshaped prototypes · expert specialization · LLM-like via gradient |

## Architecture SVGs — Technical Notes

The three files in `architecture/` are standalone technical documents, larger than the numbered frames:

| File | ViewBox | Content |
|------|---------|---------|
| `system_map.svg` | 1920×1200 | Full pipeline: Ingestion → Features → Storage → Training → Inference. All 7 critical invariants flagged. |
| `jepa_model.svg` | 1440×1080 | JEPA pre-training path + LSTM fine-tune path + MoE + Hopfield. Layer shapes, file:line anchors. |
| `data_pipeline.svg` | 1440×900 | 25-dim feature grid (all dims labeled) + downstream batch assembly + train/infer parity note. |

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
| `METADATA_DIM=25` | Sole source: `vectorizer.py:32` |

## Compatibility Matrix

| Tool | How |
|------|-----|
| Claude Design (web) | Load `index.html` as artifact; paste individual SVGs |
| Figma | Paste SVG; load tokens via Figma Tokens plugin |
| After Effects | File → Import SVG (vector shape layers) |
| Rive | Import SVG → timeline animate → export .riv |
| Lottie / bodymovin | Via Rive export or AE + bodymovin plugin |
| Framer | Drag SVG; map tokens to variables |
| Tailwind | Map `design-tokens.json` values to config |
| Gamma | Paste SVG or import image export |
| Keynote / Slides | Drag SVG (scales natively) |
| Social / video | Chrome headless → PNG at any resolution |
