# Design-atlas study — `design/` (2026-08-29)

Mission (user directive): study the `design/` folder. Method: every claim the
folder makes about the codebase checked against the code (Law I), every
duplication adjudicated (Law III), history pulled where direction mattered.
158 files, 2.6 MB, zero binaries.

## What the folder is

The vector design system for the app: `tokens/design-tokens.json` (W3C DTCG,
3 themes), 41 numbered SVG frames (marketing 01–04, app screens 05–20,
architecture diagrams 21–30, design system 31–36, RAP deep-dive 37–41), three
standalone architecture SVGs, an icon sprite + motifs + wallpapers, a master
`index.html` canvas, and `cs2/` — the marketing deck and promo-video sources
(HTML/JSX scenes) with their own flattened asset copies.

## Verified TRUE (the folder is fundamentally healthy)

- **One-way token flow intact and live**: `design/tokens/design-tokens.json`
  → `tools/gen_design_tokens.py` → `apps/qt_app/core/design_tokens.py`
  (GENERATED header confirms; L1 headless_validator checks the sync; the app
  really renders the JSON's palette).
- **`index.html` references all 41 frames** — coverage complete.
- **The triplication is structural, not accidental**: `Macena Deck.html`
  references `assets/*.svg` by relative path, so `cs2/assets/` must exist;
  `cs2/uploads/` is the declared flattened upload bundle. Byte-diffs between
  the copies are DOM re-serialization only (`<path/>` vs `<path></path>`) —
  no content drift found in sampled frames.
- **Frame 37 is honest about RAP dormancy**: "USE_RAP_MODEL=False default"
  is drawn on the diagram itself — the design does not oversell RAP.
- **IT/PT READMEs are structurally aligned** with EN (20 headings each) —
  not the D-10 fictional-structure failure; they share EN's palette staleness
  and nothing worse.
- **`ui_fixtures.py` mirrors the atlas frames' numbers** — the design atlas
  feeds the UI test harness fixtures (a real, live consumer).

## Findings (registered as D-30; asterisk = fixed this round)

- ***gemma3 staleness in the design source***: frames 07 (coach chat caption)
  and 19 (help FAQ) said `gemma3:e2b` — same defect class fixed in the app's
  i18n in round 2 (PR #86). Fixed in all three copies (6 files, text nodes
  only).
- **Palette drift — frames vs SSOT**: all 35 palette-bearing frames + all 3
  architecture SVGs are drawn in the pre-redesign palette (`#14141e` navy /
  `#d96600` orange); the tokens SSOT and the live app moved to `#0B1628` /
  `#FF6A00` at Phase 0 (git: frames frozen at their creation commit; tokens
  kept evolving). The atlas no longer looks like the product it documents.
- **README Themes table + Tailwind snippet document the OLD palette** while
  pointing at the tokens file that contradicts them two directories down —
  a live Law I violation in the atlas's front door (all three languages).
- **`cs2/uploads/design-tokens.json` is a stale pre-redesign snapshot that
  claims the REVERSED flow** ("Source: …/design_tokens.py") — someone editing
  it expecting effect would be editing a dead copy with a false provenance
  comment. The canonical file correctly says "edit JSON, then regenerate".
- **File:line anchors are stale as a class**: 12/12 sampled anchors no longer
  land on their claimed line; in ALL sampled cases the concept still holds
  elsewhere in the file (METADATA_DIM=25 at :34 not :32, FEATURE_NAMES at
  :240 not :151, forward_jepa_pretrain at :181 not :165, CoachState id=1
  CHECK at :394 not :365, …). Worst offenders: the five RAP-layer anchors
  point at `backend/nn/rap_coach/*` — the P9-01 **deprecated shim tombstones**
  (canonical: `experimental/rap_coach/`; e.g. HopfieldLayer quantity=32 lives
  at experimental/rap_coach/memory.py:119). `nav_sidebar.py` also moved to
  `widgets/components/`.
- **`cs2/uploads/README-8252c0ae.md`** is a stray copy of the project root
  README (CI badges and all) — an upload artifact, not a design doc.

## Decision handed to the operator (palette drift)

Three options, not executed unilaterally:

- **(A)** Regenerate all 41 frames + README tables to the current palette —
  big job, touches marketing assets, needs design judgment.
- **(B)** One-paragraph truth note in `design/README.md` (all three
  languages): the frames are a pre-Phase-0 historical snapshot; the tokens
  JSON and the app are current. Cheap, Law I-consistent. **Recommended.**
- **(C)** Register only (this note).

Same reasoning for the anchor re-pinning (~40 anchors across ~10 SVGs) and
the stale uploads tokens copy: bulk edits into marketing/vector sources are
design work, registered here, not snuck in.
