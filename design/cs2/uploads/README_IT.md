# Macena CS2 Coach AI — Design Atlas (Upload Bundle)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Bundle di upload appiattito del design atlas per l'applicazione di coaching CS2 — una copia autocontenuta dei 41 frame SVG più i design token, disposti in modo piatto per un facile drag-and-drop negli strumenti di design. Tutti i file sono SVG + HTML + JSON — zero binari, completamente portabile. L'atlas canonico e strutturato risiede in `design/` (radice del repository); vedi `design/README.md`.

## Mappa dei file

```
design/cs2/uploads/
├── index.html                  ← copia del canvas dell'atlas (vedi nota Browser qui sotto)
├── README.md
├── README-8252c0ae.md          ← copia caricata del README radice del progetto
├── design-tokens.json          ← formato W3C DTCG, 3 temi — copia identica
│                                 del SSOT dei token (design/tokens/design-tokens.json)
├── 01_cover.svg                Marketing (01–04)
├── 02_landing_hero.svg
├── 03_feature_showcase.svg
├── 04_pitch_slide.svg
├── 05_home.svg                 Schermate dell'app (05–20)
├── ...
├── 21_system_map.svg           Diagrammi di architettura (21–30)
├── ...
├── 31_token_system.svg         Design System (31–36)
├── 36_typography_specimen.svg
├── 37_rap_7_layer_pipeline.svg          RAP Deep-Dive (37–41)
├── 38_rap_perception_cnn.svg
├── 39_rap_memory_ltc_hopfield.svg
├── 40_rap_chronovisor_multiscale.svg
└── 41_rap_self_correction_loop.svg
```

Tutti i 41 frame sono 1440×900. I file SVG standalone di architettura più grandi (`system_map.svg`, `jepa_model.svg`, `data_pipeline.svg`) **non** fanno parte di questo bundle — risiedono in `design/architecture/`.

## Come si usa

### Browser (Claude Design / preview locale)

Il file `index.html` qui presente è una copia verbatim del canvas dell'atlas: fa riferimento agli SVG tramite percorsi relativi `frames/…` e `architecture/…`, che non si risolvono rispetto a questa cartella piatta. Aprire invece il canvas canonico:

```bash
# apri il canvas master (atlas strutturato)
open design/index.html
# oppure
firefox design/index.html
```

Funziona come `file://` — nessun server necessario. Caricare `design/index.html` come artifact Claude per uso interattivo; i singoli SVG in questa cartella si aprono direttamente in qualsiasi browser.

### Figma

1. Aprire qualsiasi frame SVG in un editor di testo, copiare tutto il contenuto.
2. In Figma: **Edit → Paste in place** — l'SVG arriva come frame vettoriale piatto.
3. Per i token: installare il plugin **Figma Tokens**, caricare `design-tokens.json`.
4. I frame di architettura (`21`–`30`) si incollano a piena risoluzione — i layer sono leggibili.

### After Effects

1. **File → Import → File** — selezionare qualsiasi `.svg` numerato da questa cartella.
2. AE importa l'SVG come **vector shape layer** — completamente animabile.
3. Usare gli SVG più grandi in `design/architecture/` per le sezioni di explainer video (viewBox più ampio = più spazio).
4. Gli SVG con frecce nei diagrammi sono buoni candidati per animazioni di **motion path**.

### Rive / Lottie

1. Importare il frame SVG nel canvas Rive.
2. Assegnare animazioni timeline ai gruppi di shape (ogni sezione è un `<g>` nominato).
3. Esportare `.riv` per l'embed in app o `.json` per Lottie/bodymovin.

### Framer

1. Trascinare qualsiasi SVG direttamente su un canvas Framer.
2. Mappare i token di colore: valori in `design-tokens.json` → variabili Framer.
3. Responsive: gli SVG usano `viewBox` — scalano senza pixelatura.

### Gamma / Keynote / Google Slides

Gli SVG scalano lossless a qualsiasi risoluzione. Per uso in slide:

```bash
# esporta qualsiasi frame in PNG a 2×, 3× o 4× usando Chrome headless
chromium --headless --screenshot=frame.png \
  --window-size=2880,1800 01_cover.svg
```

Oppure aprire nel browser, zoomare al 200%, fare screenshot.

### Landing Page (Tailwind)

Mappare i token in `tailwind.config.js`:

```js
theme: {
  extend: {
    colors: {
      surface: { base: '#0B1628', raised: '#121E2E', sunken: '#07101C' },
      accent:  { DEFAULT: '#FF6A00', hover: '#FF8533', pressed: '#CC5500' },
      text:    { primary: '#F5F7FA', secondary: '#8B94A5' },
      ok:      '#4caf50',
      warn:    '#ffaa00',
      err:     '#ff4444',
      info:    '#00D9FF',
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

Inserire i frame come hero `<img src="01_cover.svg">` — rendering SVG nativo del browser.

### Post per i social (crop 1080×1080)

```bash
# crop headless di un frame in formato quadrato
chromium --headless --screenshot=post.png \
  --window-size=1080,1080 03_feature_showcase.svg
```

Oppure ritagliare in Figma dopo il paste.

## Temi

Tre temi disponibili in `design-tokens.json`:

| Tema | Accent | Sfondo | Carattere |
|-------|--------|------------|-----------|
| **CS2** | `#FF6A00` arancione | `#0B1628` blu navy profondo | Moderno · scuro · tattico |
| **CSGO** | `#617d8c` acciaio | `#1a1c21` ardesia scuro | Militare · attenuato |
| **CS1.6** | `#4db04f` verde | `#121a12` terminale | Retro · hacker |

Nota: i token e i frame di questo bundle corrispondono al SSOT corrente (`design/tokens/design-tokens.json`): `#FF6A00` su `#0B1628`.

## RAP Deep-Dive (37–41)

Frame dedicati al fiore all'occhiello **Reflexive Auto-correcting Pedagogue** — l'architettura raggiunge l'affidabilità tramite auto-correzione, non tramite scala.

| Frame | Soggetto | Cosa mostra |
|-------|---------|---------------|
| `37_rap_7_layer_pipeline.svg` | Stack completo | Perception → Memory → Strategy → Pedagogy → Position → Chronovisor → Communication con dim reali e ancore file:line |
| `38_rap_perception_cnn.svg` | Perception | 3 stream CNN paralleli (vista ventrale / mappa dorsale / motion temporale) → concat [B, 128] |
| `39_rap_memory_ltc_hopfield.svg` | Memory | AutoNCP LTC(units=512, out=154) + HopfieldLayer(32 prototipi × 4 head) + gate di maturità NN-MEM-01 |
| `40_rap_chronovisor_multiscale.svg` | Self-critique | Scansioni Micro (64t) + Standard (192t) + Macro (640t) sulla timeline di V(s) + dedup cross-scale |
| `41_rap_self_correction_loop.svg` | L'idea grande | Loop circolare a 6 stadi · Humility gate (conf < 0.7 = silenzio) · prototipi rimodellati · specializzazione expert · LLM-like via gradiente |

## SVG di architettura — Dove risiedono

I tre documenti tecnici standalone (`system_map.svg` 1920×1200, `jepa_model.svg` 1440×1080, `data_pipeline.svg` 1440×900) **non** sono in questo bundle — risiedono in `design/architecture/` alla radice del repository. La copertura architettonica di questo bundle consiste nei frame numerati `21`–`30` (più i deep-dive RAP `37`–`41`).

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
| `METADATA_DIM=25` | Sorgente unica: `vectorizer.py` |

## Matrice di compatibilità

| Tool | Come |
|------|-----|
| Claude Design (web) | Caricare `design/index.html` come artifact; incollare singoli SVG |
| Figma | Incollare l'SVG; caricare i token via plugin Figma Tokens |
| After Effects | File → Import SVG (vector shape layer) |
| Rive | Importare SVG → animare timeline → esportare .riv |
| Lottie / bodymovin | Tramite export Rive o AE + plugin bodymovin |
| Framer | Trascinare l'SVG; mappare i token in variabili |
| Tailwind | Mappare i valori di `design-tokens.json` nella config |
| Gamma | Incollare l'SVG o importare un export immagine |
| Keynote / Slides | Trascinare l'SVG (scala nativamente) |
| Social / video | Chrome headless → PNG a qualsiasi risoluzione |
