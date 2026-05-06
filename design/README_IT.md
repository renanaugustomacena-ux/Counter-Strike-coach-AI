# Macena CS2 Coach AI — Design Atlas

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Design system vettoriale per l'applicazione di coaching CS2. Tutti i file sono SVG + HTML + JSON — zero binari, completamente portabile.

## Mappa dei file

```
design/
├── index.html                  ← canvas master (aprire nel browser)
├── README.md
├── tokens/
│   └── design-tokens.json      ← formato W3C DTCG, 3 temi
├── frames/                     ← 41 frame SVG, 1440×900 ciascuno
│   ├── 01_cover.svg            Marketing (01–04)
│   ├── 02_landing_hero.svg
│   ├── 03_feature_showcase.svg
│   ├── 04_pitch_slide.svg
│   ├── 05_home.svg             Schermate dell'app (05–20)
│   ├── ...
│   ├── 21_system_map.svg       Diagrammi di architettura (21–30)
│   ├── ...
│   ├── 31_token_system.svg     Design system (31–36)
│   ├── 36_typography_specimen.svg
│   ├── 37_rap_7_layer_pipeline.svg          RAP Deep-Dive (37–41)
│   ├── 38_rap_perception_cnn.svg
│   ├── 39_rap_memory_ltc_hopfield.svg
│   ├── 40_rap_chronovisor_multiscale.svg
│   └── 41_rap_self_correction_loop.svg
├── architecture/               ← SVG di approfondimento standalone
│   ├── system_map.svg          1920×1200 pipeline completa
│   ├── jepa_model.svg          1440×1080 diagramma layer completo
│   └── data_pipeline.svg       1440×900  ciclo di vita del vettore 25-dim
└── assets/
    ├── icons/sprite.svg        sprite di icone SVG
    └── wallpapers/             cs2.svg · csgo.svg · cs16.svg
```

## Come si usa

### Browser (Claude Design / preview locale)

```bash
# apri il canvas master
open design/index.html
# oppure
firefox design/index.html
```

Funziona come `file://` — nessun server necessario. Caricare `index.html` come artifact Claude per uso interattivo.

### Figma

1. Aprire qualsiasi frame SVG in un editor di testo, copiare tutto il contenuto.
2. In Figma: **Edit → Paste in place** — l'SVG arriva come frame vettoriale piatto.
3. Per i token: installare il plugin **Figma Tokens**, caricare `tokens/design-tokens.json`.
4. Gli SVG di architettura (`architecture/`) si incollano a piena risoluzione — i layer sono leggibili.

### After Effects

1. **File → Import → File** — selezionare qualsiasi `.svg` da `frames/` o `architecture/`.
2. AE importa l'SVG come **vector shape layer** — completamente animabile.
3. Usare i file in `architecture/` per le sezioni di explainer video (viewBox più ampio = più spazio).
4. Gli SVG di architettura con frecce sono buoni candidati per animazioni di **motion path**.

### Rive / Lottie

1. Importare il frame SVG nel canvas Rive.
2. Assegnare animazioni timeline ai gruppi di shape (ogni sezione è un `<g>` nominato).
3. Esportare `.riv` per l'embed in app o `.json` per Lottie/bodymovin.

### Framer

1. Trascinare qualsiasi SVG direttamente su un canvas Framer.
2. Mappare i token di colore: valori in `tokens/design-tokens.json` → variabili Framer.
3. Responsive: gli SVG usano `viewBox` — scalano senza pixelatura.

### Gamma / Keynote / Google Slides

Gli SVG scalano lossless a qualsiasi risoluzione. Per uso in slide:

```bash
# esporta qualsiasi frame in PNG a 2×, 3× o 4× usando Chrome headless
chromium --headless --screenshot=frame.png \
  --window-size=2880,1800 frames/01_cover.svg
```

Oppure aprire nel browser, zoomare al 200%, fare screenshot.

### Landing Page (Tailwind)

Mappare i token in `tailwind.config.js`:

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

Inserire i frame come hero `<img src="frames/01_cover.svg">` — rendering SVG nativo del browser.

### Post per i social (crop 1080×1080)

```bash
# crop headless di un frame in formato quadrato
chromium --headless --screenshot=post.png \
  --window-size=1080,1080 frames/03_feature_showcase.svg
```

Oppure ritagliare in Figma dopo il paste.

## Temi

Tre temi disponibili in `tokens/design-tokens.json`:

| Tema | Accent | Sfondo | Carattere |
|-------|--------|------------|-----------|
| **CS2** | `#d96600` arancione | `#14141e` blu navy profondo | Moderno · scuro · tattico |
| **CSGO** | `#617d8c` acciaio | `#1a1c21` ardesia scuro | Militare · attenuato |
| **CS1.6** | `#4db04f` verde | `#0d1a0d` terminale | Retro · hacker |

## RAP Deep-Dive (37–41)

Frame dedicati al fiore all'occhiello **Reflexive Auto-correcting Pedagogue** — l'architettura raggiunge l'affidabilità tramite auto-correzione, non tramite scala.

| Frame | Soggetto | Cosa mostra |
|-------|---------|---------------|
| `37_rap_7_layer_pipeline.svg` | Stack completo | Perception → Memory → Strategy → Pedagogy → Position → Chronovisor → Communication con dim reali e ancore file:line |
| `38_rap_perception_cnn.svg` | Perception | 3 stream CNN paralleli (vista ventrale / mappa dorsale / motion temporale) → concat [B, 128] |
| `39_rap_memory_ltc_hopfield.svg` | Memory | AutoNCP LTC(units=512, out=154) + HopfieldLayer(32 prototipi × 4 head) + gate di maturità NN-MEM-01 |
| `40_rap_chronovisor_multiscale.svg` | Self-critique | Scansioni Micro (64t) + Standard (192t) + Macro (640t) sulla timeline di V(s) + dedup cross-scale |
| `41_rap_self_correction_loop.svg` | L'idea grande | Loop circolare a 6 stadi · Humility gate (conf < 0.7 = silenzio) · prototipi rimodellati · specializzazione expert · LLM-like via gradiente |

## SVG di architettura — Note tecniche

I tre file in `architecture/` sono documenti tecnici standalone, più grandi dei frame numerati:

| File | ViewBox | Contenuto |
|------|---------|---------|
| `system_map.svg` | 1920×1200 | Pipeline completa: Ingestione → Feature → Storage → Training → Inferenza. Tutte le 7 invarianti critiche evidenziate. |
| `jepa_model.svg` | 1440×1080 | Path di pre-training JEPA + path di fine-tune LSTM + MoE + Hopfield. Shape dei layer, ancore file:line. |
| `data_pipeline.svg` | 1440×900 | Griglia di feature 25-dim (tutte le dim etichettate) + assemblaggio batch a valle + nota di parità train/infer. |

## Invarianti (non violare)

Sono hardcoded nei diagrammi di architettura per riferimento:

| Codice | Regola |
|------|------|
| `P-RSB-03` | `round_won` escluso da tutte le 25 dim di feature (label leak) |
| `NN-MEM-01` | Memoria Hopfield bypassata fino a ≥2 forward pass |
| `NN-16` | EMA `apply_shadow()` deve fare `.clone()` delle shadow |
| `NN-JM-04` | `target_encoder` requires_grad=False durante l'EMA |
| `DS-12` | MIN_DEMO_SIZE = 10 MB |
| `P-VEC-02` | Clamp NaN/Inf + >5% batch → DataQualityError |
| `METADATA_DIM=25` | Sorgente unica: `vectorizer.py:32` |

## Matrice di compatibilità

| Tool | Come |
|------|-----|
| Claude Design (web) | Caricare `index.html` come artifact; incollare singoli SVG |
| Figma | Incollare l'SVG; caricare i token via plugin Figma Tokens |
| After Effects | File → Import SVG (vector shape layer) |
| Rive | Importare SVG → animare timeline → esportare .riv |
| Lottie / bodymovin | Tramite export Rive o AE + plugin bodymovin |
| Framer | Trascinare l'SVG; mappare i token in variabili |
| Tailwind | Mappare i valori di `design-tokens.json` nella config |
| Gamma | Incollare l'SVG o importare un export immagine |
| Keynote / Slides | Trascinare l'SVG (scala nativamente) |
| Social / video | Chrome headless → PNG a qualsiasi risoluzione |
