# Aesthetic round 1 — workbench decisions executed (2026-08-29)

Mission: the operator answered the design workbench's six open questions
(claude.ai artifact, comment loop) plus a font-bug report and a tray/slideshow
feature request. Method: one 5-reader parallel deep-study (fonts, slideshow+
tray, charts+empty states, ML architecture, repaint scope), then six PRs, each
through the full gate. Final state: **2719 passed / 0 failed** on merged main.

## Decisions as recorded

| Q | Decision | Outcome |
|---|---|---|
| Q1 frost rollout | RESERVED — keep meaning | no code change, recorded |
| Q2 accent discipline | keep loose | no code change, recorded |
| Q3 chart voice | accent-led | PR #92 |
| Q4 empty states | more character | PR #93 |
| Q5 design frames | repaint to live palette | PR #96 (supersedes D-30 option B) |
| Q6 fonts/slideshow/tray | fix + build | PRs #91, #94, #95 |

## D-31 — the font system lied three ways (FIXED, PR #91)

The report "only one font actually works" had three verified causes:

1. **Picker saved labels, not family names**: "New Hope"/"CS Regular" match no
   registered family (real embedded names: `NewHope`, `Counter-Strike`) — Qt
   silently walked the fallback chain to Segoe UI, so both picks rendered
   identically. Fixed at the picker + a legacy-alias normalizer for persisted
   configs.
2. **Impostor font file**: `PHOTO_GUI/JetBrainsMono-Regular.ttf`'s name table
   said `DejaVu Sans Mono` (byte-verified). Replaced with the genuine
   JetBrains Mono v2.304 Regular (official release, OFL-1.1, same source as
   the other bundled weights) in both PHOTO_GUI and assets/fonts.
3. **Dist shipped no design fonts**: `cs2_analyzer_win.spec` never bundled
   `assets/fonts` — packaged apps fell back to Consolas/Roboto everywhere;
   only YUPIX (pixel font) looked different. Added to datas.

Lockstep tests pin all three (name-table impostor detector included).
Registered, NOT yet fixed (part of D-32): the FONT_TYPE setting only reaches
the generic QWidget rule — hardcoded QSS families and QPainter text ignore
it; the appended font-size rule overrides Typography point sizes app-wide.

## D-32 — the Windows packaging gap (REGISTERED, fonts part fixed)

From the ML-architecture read: `cs2_analyzer_win.spec` ships **no .pt
checkpoints, no hltv_metadata.db, no FAISS index, no coach-book dir** — the
factory-bundle fallback in `persistence.load_nn` points at bundle paths that
never exist, so ALL neural features silently no-op on a fresh install.
`database.db` is a monolith mixing pro training rows with user tables, so
"ship without the training DB" concretely means shipping a pruned monolith
(an `.empty_backup` exists but nothing wires it). Decision needed at
packaging time — registered, not unilaterally changed.

## D-33 — the coaching chain is unwired end-to-end (REGISTERED; extends D-26)

Beyond D-26's `generate_new_insights` orphan, the read confirmed the WHOLE
insight-producing chain has no production caller: `run_ml_pipeline` (only
caller: `ingest_user_demos`, itself uncalled), `CoachingService` (
`get_coaching_service()` never invoked), `ExperienceBank
.extract_experiences_from_demo` (CoachingExperience stays empty),
`RoleThresholdStore.learn_from_pro_data`/`persist_to_db` (role classifier in
permanent cold start → the role insight never fires), CSVMigrator seeding
(`__main__`-only → role head Phase 5 always skips). Also: the maturity
ladder counts TRAINING CYCLES, not demos (`total_matches_processed`
increments once per full cycle — it can effectively never reach the
MATURE=200 tier). The Qt coach screen reads `CoachingInsight` rows nothing
currently writes. This is THE wiring campaign to run before/with Linux
training (replace-not-delete: re-point ingestion or a UI action at
CoachingService).

## Architecture answers recorded (operator's shipping questions)

- **What .pt files carry**: model weights + (CLI format) EMA counters and
  training metadata; app-format checkpoints are bare state_dicts with
  `.meta.json` sidecars + SHA-256 registry (ship them together — load
  validates). Inference needs NO pro tick data: checkpoints (~40 MB),
  `hltv_metadata.db` (112 KB pro cards), FAISS index + coach book (~1 MB),
  baseline CSVs. The heavy pro rows (123 MB monolith share + 584 MB shards)
  are training-only.
- **User demos today**: ingest → stats/rounds/ticks stored; analysis/training
  do NOT auto-run (see D-33). Manual trigger exists (console `ml start` /
  POST /api/training/start): Phase 3 trains a user-specific NN on the user's
  aggregates (models/user/latest.pt); the tick-level JEPA finetune is
  CLI-only and currently blocked by the undefined 10-dim coaching-target
  contract (26-RANGE-01).
- **Noob-to-pro profile**: pieces exist (per-match history + trends,
  SkillLatentModel 5-axis skill vector + curriculum level, maturity ladder,
  THREE disconnected role systems, pro z-score comparisons) but no persisted
  skill history, no role write-back, no role-conditioned curriculum, no
  user-role→pro-archetype matching. The six-gap list in the ML read is the
  build plan for the "role-based coaching path" the operator wants.

## Shipped features (Q3/Q4/Q6 details)

- **Charts speak accent** (#92): player series lead with the theme accent
  (sparklines, home hero, utility you-bars, avg-rating stat); pro baseline
  moved to info-cyan; endpoint "now" dots to text-primary. CT/T side-identity
  tokens deliberately untouched (a token-value swap would have recolored
  team semantics — the scoping read caught this). Splash status text was the
  last old-palette literal in the app — now token-driven.
- **Empty states** (#93): EmptyState paints a tactical motif (faint grid +
  scope-ring crosshair on the icon well, pure QPainter, Linux
  QGraphicsEffect ban holds); economy/momentum charts paint a resting state
  instead of blank panels (new i18n key ×3).
- **Wallpaper slideshow** (#94): `BACKGROUND_IMAGE="::slideshow::"` sentinel
  rotates the active theme's wallpaper folder every 2 min with a 900 ms
  crossfade; dashed Settings card; MACENA_UI_ANIMATIONS=0 hard-cuts; one
  `apply_wallpaper_state` seam replaced three ad-hoc push sites. The dead
  ENABLE_SLIDESHOW config key (read by nothing) was replaced.
- **System tray** (#95): painted tray icon (no binary asset), menu
  Open/AI Coach/CLI Console/Quit, close-to-tray (default on, Settings
  toggle, balloon-once). "Chatbot only" deliberately opens the SAME instance
  on the coach screen — and `lifecycle.ensure_single_instance` finally has a
  production caller (it was test-only dead code; two GUI processes = two
  session-engine daemons on one SQLite).
- **Atlas repaint** (#96): 126 SVGs + galleries + wallpaper + stale uploads
  tokens copy; 4-phase mechanical plan with the frame-32 CSGO/CS16 carve-out
  and the dual-role #3a3a5a attribute split; zero old literals survive the
  acceptance grep; eyeballed 32/31/01. D-30 fully resolved.

## Render atlas

`docs/ux-audit/renders-atlas` regenerated in lockstep with this note — 17
screens changed (genuine JetBrains Mono alone re-renders every mono caption;
plus accent charts, motif empty states, slideshow card).
