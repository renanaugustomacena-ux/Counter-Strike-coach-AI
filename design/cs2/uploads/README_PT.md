# Macena CS2 Coach AI — Atlas de Design

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Sistema de design vetorial para a aplicação de coaching de CS2. Todos os arquivos são SVG + HTML + JSON — zero binários, totalmente portátil.

## Mapa de arquivos

```
design/
├── index.html                  ← canvas master (abrir no browser)
├── README.md
├── tokens/
│   └── design-tokens.json      ← formato W3C DTCG, 3 temas
├── frames/                     ← 41 frames SVG, 1440×900 cada
│   ├── 01_cover.svg            Marketing (01–04)
│   ├── 02_landing_hero.svg
│   ├── 03_feature_showcase.svg
│   ├── 04_pitch_slide.svg
│   ├── 05_home.svg             Telas do app (05–20)
│   ├── ...
│   ├── 21_system_map.svg       Diagramas de arquitetura (21–30)
│   ├── ...
│   ├── 31_token_system.svg     Design System (31–36)
│   ├── 36_typography_specimen.svg
│   ├── 37_rap_7_layer_pipeline.svg          RAP Deep-Dive (37–41)
│   ├── 38_rap_perception_cnn.svg
│   ├── 39_rap_memory_ltc_hopfield.svg
│   ├── 40_rap_chronovisor_multiscale.svg
│   └── 41_rap_self_correction_loop.svg
├── architecture/               ← SVGs de deep-dive standalone
│   ├── system_map.svg          1920×1200 pipeline completa
│   ├── jepa_model.svg          1440×1080 diagrama completo de camadas
│   └── data_pipeline.svg       1440×900  ciclo de vida do vetor de 25 dim
└── assets/
    ├── icons/sprite.svg        Sprite de ícones SVG
    └── wallpapers/             cs2.svg · csgo.svg · cs16.svg
```

## Como usar

### Browser (Claude Design / preview local)

```bash
# abre o canvas master
open design/index.html
# ou
firefox design/index.html
```

Funciona como `file://` — sem necessidade de servidor. Carregue `index.html` como artifact do Claude para uso interativo.

### Figma

1. Abra qualquer frame SVG num editor de texto e copie todo o conteúdo.
2. No Figma: **Edit → Paste in place** — o SVG é colado como um frame vetorial flat.
3. Para tokens: instale o plugin **Figma Tokens** e carregue `tokens/design-tokens.json`.
4. SVGs de arquitetura (`architecture/`) são colados em resolução total — as camadas ficam legíveis.

### After Effects

1. **File → Import → File** — selecione qualquer `.svg` de `frames/` ou `architecture/`.
2. O AE importa o SVG como **vector shape layers** — totalmente animáveis.
3. Use os arquivos de `architecture/` em seções de vídeo explicativo (viewBox maior = mais espaço).
4. Os SVGs de arquitetura com setas são bons candidatos para animações de **motion path**.

### Rive / Lottie

1. Importe um frame SVG no canvas do Rive.
2. Atribua animações de timeline aos grupos de shape (cada seção é um `<g>` nomeado).
3. Exporte `.riv` para embed no app, ou `.json` para Lottie/bodymovin.

### Framer

1. Arraste qualquer SVG diretamente para um canvas do Framer.
2. Mapeie os tokens de cor: valores de `tokens/design-tokens.json` → variáveis do Framer.
3. Responsivo: os SVGs usam `viewBox` — escalam sem pixelar.

### Gamma / Keynote / Google Slides

SVGs escalam sem perdas em qualquer resolução. Para uso em slides:

```bash
# exporta qualquer frame para PNG em 2×, 3× ou 4× usando Chrome headless
chromium --headless --screenshot=frame.png \
  --window-size=2880,1800 frames/01_cover.svg
```

Ou abra no browser, dê zoom em 200% e tire um screenshot.

### Landing Page (Tailwind)

Mapeie os tokens para `tailwind.config.js`:

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

Insira os frames como hero `<img src="frames/01_cover.svg">` — renderização SVG nativa do browser.

### Posts sociais (crop 1080×1080)

```bash
# crop headless de qualquer frame para quadrado
chromium --headless --screenshot=post.png \
  --window-size=1080,1080 frames/03_feature_showcase.svg
```

Ou faça o crop no Figma após o paste.

## Temas

Três temas disponíveis em `tokens/design-tokens.json`:

| Tema | Accent | Background | Caráter |
|-------|--------|------------|-----------|
| **CS2** | `#d96600` laranja | `#14141e` deep navy | Moderno · escuro · tático |
| **CSGO** | `#617d8c` aço | `#1a1c21` ardósia escura | Militar · esmaecido |
| **CS1.6** | `#4db04f` verde | `#0d1a0d` terminal | Retrô · hacker |

## RAP Deep-Dive (37–41)

Frames dedicados ao carro-chefe **Reflexive Auto-correcting Pedagogue** — a arquitetura alcança confiabilidade pela auto-correção, não pela escala.

| Frame | Assunto | O que mostra |
|-------|---------|---------------|
| `37_rap_7_layer_pipeline.svg` | Stack completa | Perception → Memory → Strategy → Pedagogy → Position → Chronovisor → Communication com dimensões reais e âncoras file:line |
| `38_rap_perception_cnn.svg` | Perception | 3 streams CNN paralelos (ventral view / dorsal map / temporal motion) → concat [B, 128] |
| `39_rap_memory_ltc_hopfield.svg` | Memory | AutoNCP LTC(units=512, out=154) + HopfieldLayer(32 prototypes × 4 heads) + gate de maturidade NN-MEM-01 |
| `40_rap_chronovisor_multiscale.svg` | Auto-crítica | Scans Micro (64t) + Standard (192t) + Macro (640t) sobre a timeline de V(s) + dedup cross-scale |
| `41_rap_self_correction_loop.svg` | A grande ideia | Loop circular de 6 estágios · Humility gate (conf < 0.7 = silêncio) · prototypes reformatados · especialização de experts · LLM-like via gradiente |

## SVGs de arquitetura — Notas técnicas

Os três arquivos em `architecture/` são documentos técnicos standalone, maiores que os frames numerados:

| Arquivo | ViewBox | Conteúdo |
|------|---------|---------|
| `system_map.svg` | 1920×1200 | Pipeline completa: Ingestion → Features → Storage → Training → Inference. Todas as 7 invariantes críticas sinalizadas. |
| `jepa_model.svg` | 1440×1080 | Caminho de pré-treino JEPA + caminho de fine-tune LSTM + MoE + Hopfield. Shapes das camadas, âncoras file:line. |
| `data_pipeline.svg` | 1440×900 | Grid de features de 25 dim (todas as dimensões rotuladas) + montagem de batch downstream + nota de paridade train/infer. |

## Invariantes (não viole)

Estas estão hardcoded nos diagramas de arquitetura como referência:

| Código | Regra |
|------|------|
| `P-RSB-03` | `round_won` excluído de todas as 25 dimensões de feature (label leak) |
| `NN-MEM-01` | Memória Hopfield bypassada até ≥2 forward passes |
| `NN-16` | EMA `apply_shadow()` deve fazer `.clone()` dos shadows |
| `NN-JM-04` | `target_encoder` requires_grad=False durante o EMA |
| `DS-12` | MIN_DEMO_SIZE = 10 MB |
| `P-VEC-02` | Clamp de NaN/Inf + >5% por batch → DataQualityError |
| `METADATA_DIM=25` | Fonte única: `vectorizer.py:32` |

## Matriz de compatibilidade

| Ferramenta | Como |
|------|-----|
| Claude Design (web) | Carregue `index.html` como artifact; cole SVGs individuais |
| Figma | Cole o SVG; carregue tokens via plugin Figma Tokens |
| After Effects | File → Import SVG (vector shape layers) |
| Rive | Importe SVG → anime na timeline → exporte .riv |
| Lottie / bodymovin | Via export do Rive ou AE + plugin bodymovin |
| Framer | Arraste o SVG; mapeie os tokens para variáveis |
| Tailwind | Mapeie os valores de `design-tokens.json` para a config |
| Gamma | Cole o SVG ou importe a exportação como imagem |
| Keynote / Slides | Arraste o SVG (escala nativamente) |
| Social / vídeo | Chrome headless → PNG em qualquer resolução |
