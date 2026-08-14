# Changelog

All notable changes to the Macena CS2 Analyzer are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Audited (2026-08 nuke-proof campaign)
- Full two-pass audit of all 618 files (~155k LOC) with per-file dossiers, a
  44-finding register (all resolved: 31 fixed + 13 explicitly deferred), ten
  cross-cutting contract lenses, and per-wave gate evidence — see `docs/audit/`
- Default test gate now FULLY GREEN (2574 passed, 0 failed, 0 errors) with the
  coverage floor raised 33% → 50%; `headless_validator` PASS; integrity
  manifest verify GREEN; CI green on Ubuntu + Windows

### Fixed (campaign highlights)
- Operator STOP now actually stops training; training aborts exit non-zero
- Ingestion: atomic task claim (no more double-parsed demos across runners);
  parse guards absorb Rust panics and demoparser2's own error class; the parse
  timeout no longer joins a hung worker
- Safety tooling: `verify_all_safe` gates every bare-invocation mutating tool;
  `build_pipeline --test-only` never wipes data; `reset_pro_data` is dry-run by
  default with a pre-delete backup; `build_tools` builds the real packaging spec
  with argv lists (last `shell=True` removed)
- Three screens moved GUI-thread DB work onto Workers (with a permanent
  doctrine test); chips restyle live on theme switch; toast timers can no
  longer fire on destroyed widgets; the animations kill-switch is honored by
  every helper
- Known-maps single source of truth (`core/known_maps.py`) replaces seven
  divergent lists; round-winner dtype normalized (int team_num demos no longer
  record every round as lost)
- HLTV daemon spawns its real module entry point and retries after dormancy;
  POSIX single-instance enforcement; lock release honours ownership; secrets
  saving degrades gracefully without a keyring; `$HOME` can never again become
  a data directory
- CI: branch filter covers `feat/**`/`chore/**` (the pipeline now actually
  runs); ruff joins pre-commit; `pip check` dependency gate


### Added
- Design-atlas frontend rebuild: all 15 Qt screens rebuilt against the 41-frame design atlas (app frames 05-20), driven by the pre-existing design-token pipeline (per-theme tokens remain the single source for both QSS and QPalette)
- QPainter chart suite: `EconomyChart`, `MomentumChart`, `RadarChart`, `RatingSparkline`, `UtilityBarChart` (plus the existing `MiniSparkline`)
- Bundled OFL display fonts in `assets/fonts/` (Space Grotesk, Inter, JetBrains Mono weights)
- Offscreen UI screenshot harness (`tools/ui_screenshot.py`) with deterministic fixtures (`tools/ui_fixtures.py`) and component gallery (`tools/ui_gallery.py`)
- Runtime UI smoke suite (boots the real MainWindow: screen walk, live theme switching, language roundtrip, sidebar collapse) and an i18n key-parity guard across en/it/pt
- Competitive-research-informed surfaces: benchmark-relative delta chips on headline stats, mono provenance lines on AI advice, top-3 ranked coach focus areas, wizard "what happens next" calibration copy, kind-differentiated critical-moment glyphs on the tactical timeline (★ critical / ◆ clutch / ● play, with legend)
- Trilingual i18n completion: ~565 keys per language (en/it/pt), properly translated

### Changed
- Coach chat moved from a QDockWidget dock to a stacked CoachScreen with an embedded `ChatPanel` (belief ring, ranked insights, chat in one screen)
- Match Detail reorganized into 4 underline tabs (Overview · Rounds · Economy · Highlights)
- Tactical viewer upgraded: named zone overlays (`assets/map_zones/`), movement trails, glyph timeline, and Ghost Mode (dual YOU/GHOST progress + divergence panel)
- Default background is now flat `surface_base` (no wallpaper); per-theme wallpapers remain available as a persisted user opt-in

### Removed
- QtCharts dependency — Qt Charts is GPLv3-or-commercial only, incompatible with this proprietary codebase; all charts are custom QPainter widgets and a license-gate test fails the suite if a `QtCharts`/`QChart` reference reappears under `apps/qt_app/`

## [1.0.0] - 2026-03-20

### Added
- End-to-end coaching pipeline: WATCH > LEARN > THINK > SPEAK
- JEPA self-supervised pre-training with InfoNCE contrastive loss and EMA target encoder
- RAP Coach architecture (LTC-Hopfield memory, Mixture-of-Experts strategy layer)
- COPER coaching pipeline with 4-level fallback chain (COPER > Hybrid > RAG > Base)
- Experience Bank with EMA effectiveness scoring and context-similarity retrieval
- PySide6/Qt desktop frontend (13 screens, MVVM, 3 visual themes)
- Legacy Kivy/KivyMD frontend (maintained as fallback)
- 4-daemon session engine (Scanner, Digester, Teacher, Pulse)
- 3-stage maturity gating (Calibrating > Learning > Mature)
- HLTV 2.0 rating calculation per match
- Tick-level demo parsing via demoparser2 (zero decimation)
- 25-dimensional canonical feature vector (FeatureExtractor)
- Game-theory analysis (expectiminimax, Bayesian death probability, deception index)
- Neural role classification (5 roles: entry, support, lurk, AWP, anchor)
- Bayesian belief models for opponent mental state tracking
- HLTV pro stats scraping via FlareSolverr/Docker
- Ollama integration for natural-language coaching refinement
- 2D tactical viewer with real-time demo replay
- Temporal baseline decay for skill evolution tracking
- Conviction Index (5-signal composite model confidence)
- RASP integrity checking and integrity manifest
- Cross-platform CI/CD pipeline (GitHub Actions, 6 stages)
- 1500+ automated tests with headless validator
- SQLite WAL mode with auto-migration (Alembic)
- Automated backup strategy with safety gates
- Multi-language support (English, Italian, Portuguese)
- PyInstaller distribution build for Windows

### Security
- SHA-pinned GitHub Actions for supply chain security
- Bandit SAST + detect-secrets + pip-audit in CI
- OS keyring integration for credential storage
- Input validation with Pydantic models at all boundaries
