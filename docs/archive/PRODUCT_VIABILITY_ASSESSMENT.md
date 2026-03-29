# CS2 Coach AI — Product Viability Assessment

> **Date:** March 17, 2026
> **Scope:** Full-stack audit — backend, frontend, packaging, distribution, commercial viability
> **Purpose:** Honest, zero-sugar assessment of whether this can become an actual product for sale
> **Companion document:** [AI_ARCHITECTURE_ANALYSIS.md](AI_ARCHITECTURE_ANALYSIS.md) (AI/ML layer audit)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Numbers](#2-the-numbers)
3. [What Ships Today (Windows)](#3-what-ships-today)
4. [Backend: What Works, What Doesn't](#4-backend)
5. [Frontend: Product or Prototype?](#5-frontend)
6. [Dependency Reality](#6-dependencies)
7. [What Breaks for Real Users](#7-what-breaks)
8. [Cross-Platform Reality](#8-cross-platform)
9. [Competitive Landscape](#9-competition)
10. [Monetization Paths (Honest)](#10-monetization)
11. [The Roadmap to v1.0](#11-roadmap)
12. [Final Verdict](#12-verdict)

---

## 1. Executive Summary

This is a **technically sophisticated research project** built by a solo developer who started coding three months ago. The engineering quality in specific areas (database architecture, ML pipeline, game theory engines) rivals mid-career professional work. But it is **not a shippable product today**.

| Dimension | Readiness | Score |
|-----------|-----------|-------|
| Backend infrastructure | Production-grade in core, fragile at edges | **7/10** |
| Frontend UX | 5 screens polished, 8 are empty stubs | **4/10** |
| Packaging & distribution | Windows installer exists, nothing else | **3/10** |
| Commercial viability | Strong differentiation, weak completeness | **4/10** |
| Portfolio value | Exceptional for a self-taught developer | **9/10** |

**The honest answer:** It can become a product. It is not one yet. The gap is 6-10 weeks of focused work, not 6 months.

---

## 2. The Numbers

| Metric | Value |
|--------|-------|
| Python source files | 372 |
| Lines of code (application) | 84,497 |
| Test files | 18 |
| Lines of test code | 1,309 |
| Test coverage | ~30% (CI gate: `fail_under=30`) |
| Dependencies (direct) | 51 packages in requirements.txt |
| Bundle size (CPU-only) | ~1.6 GB |
| Bundle size (CUDA default) | ~2.5 GB |
| Qt screens (functional) | 5 of 13 |
| Qt screens (stub) | 8 of 13 |
| Custom chart widgets | 6 (all hand-rolled QPainter) |
| Languages supported | 3 (English, Portuguese, Italian) |
| Theme variants | 3 (CS2, CSGO, CS 1.6) |
| Game theory engines | 6 (all functional, zero training data needed) |
| ML models | 4 (JEPA, VL-JEPA, RAP Coach, Legacy) |
| Database tables (monolith) | 18 |
| Pro demos available | ~200 |
| Pro demos ingested | 11 (17.3M tick rows) |

---

## 3. What Ships Today

### Windows Distribution

**Exists:** PyInstaller spec (`packaging/cs2_analyzer_win.spec`) + Inno Setup installer (`packaging/windows_installer.iss`). Builds a `Macena_CS2_Installer.exe` with localized install (EN, IT, PT).

**What the user gets after install:**

| Screen | Status | What They See |
|--------|--------|---------------|
| Home Dashboard | **FUNCTIONAL** | 5 cards: demo path, pro ingestion status, connectivity, tactical viewer link, training status. Live polling every 10s. |
| AI Coach | **FUNCTIONAL** | Coaching insights, belief state card, recent insights list, collapsible chat panel, quick action buttons. |
| Match History | **FUNCTIONAL** | Scrollable match list with color-coded HLTV 2.0 rating badges (green/yellow/red), K/D, ADR, dates. |
| Your Stats | **FUNCTIONAL** | Rating trend sparkline, per-map stats table, strengths/weaknesses radar chart, utility usage comparison. |
| Tactical Analyzer | **FUNCTIONAL** | 2D pixel-accurate map playback with real-time player positions, timeline scrubbing, ghost player mode overlay. |
| Match Detail | **STUB** | Empty label: "Match Detail — Coming Soon" |
| Settings | **STUB** | Empty label. No way to change theme, language, or paths from UI. |
| Setup Wizard | **STUB** | Empty label. No first-time onboarding. |
| Player Profile | **STUB** | Empty label. |
| Edit Profile | **STUB** | Empty label. |
| Steam Integration | **STUB** | Empty label. |
| FaceIT Integration | **STUB** | Empty label. |
| Help | **STUB** | Empty label. No documentation, no FAQ. |

**The core loop closes:** Upload demo → parse → analyze → see insights + tactical replay. A user can get value from the 5 functional screens.

**The problem:** The 8 stubs are **visible in the sidebar**. A user who clicks "Settings" sees a blank screen with a placeholder label. This screams "unfinished software" regardless of how good the 5 working screens are.

### What's NOT in the Windows Installer

- No code signing → Windows SmartScreen warns "Unknown publisher"
- No GPU detection → user won't know if training is 50x slower than expected
- No Docker → HLTV pro stats sync fails silently
- No SentenceTransformer models → ~400 MB auto-download on first Experience Bank use, no progress indicator
- Playwright excluded → HLTV scraper can't run from frozen build anyway

---

## 4. Backend: What Works, What Doesn't

### What's Genuinely Solid

**1. Tri-Database WAL Architecture**
(`backend/storage/database.py`, `backend/storage/match_data_manager.py`)

- Monolith `database.db` for aggregate stats + coaching state
- Separate `hltv_metadata.db` to eliminate write lock contention with HLTV scraper
- Per-match SQLite files (`match_data/match_*.db`) to prevent monolith from growing to 10+ GB
- WAL mode enforced on every connection: `PRAGMA journal_mode=WAL`, `busy_timeout=30000`
- Atomic upserts via `INSERT ... ON CONFLICT DO UPDATE` — no TOCTOU races
- LRU engine cache (max 50 per-match connections, OrderedDict eviction)

This is better database design than most mid-size startups ship.

**2. 4-Level Coaching Fallback Chain**
(`backend/services/coaching_service.py`)

```
Level 1: COPER (Experience Bank + RAG + Pro References) — highest fidelity
Level 2: HYBRID (ML predictions + RAG synthesis)
Level 3: TRADITIONAL + RAG (statistical deviations + knowledge base)
Level 4: TRADITIONAL (pure statistics) — always produces output
```

System NEVER outputs zero coaching. Even on total failure, a generic insight is saved. This is how production systems should work.

**3. Game Theory Engines — Work TODAY With Zero Training Data**
(`backend/analysis/`)

These don't need ML. They use math and rules:

| Engine | What It Does | Status |
|--------|-------------|--------|
| Bayesian Death Probability | Log-odds update with auto-calibration from match data | Fully functional |
| Expectiminimax Game Tree | 4-action recursive search with stochastic opponent modeling | Fully functional |
| Momentum Tracker | Psychological momentum multiplier (0.7 tilt → 1.4 hot) | Fully functional |
| Entropy Analysis | Utility effectiveness in bits (Shannon entropy on 32×32 grid) | Fully functional |
| Win Probability NN | 12-feature neural network for real-time round win prediction | Fully functional |
| Blind Spot Detection | Compares player actions to game-tree optimal | Fully functional |
| Engagement Range | Kill distance buckets vs. pro baselines per role | Fully functional |

**These are the project's hidden gem.** They produce useful coaching output right now, with no training whatsoever. A user's flash effectiveness vs. pro baseline, their positioning blind spots, their economy decisions — all computed from match data and published CS2 knowledge.

**4. Data Pipeline After Hardening**

The pipeline overhaul (Phases 0-7) addressed 40 structural issues:
- Atomic writes for cache and checkpoints (crash-safe)
- Round-aware position interpolation (no cross-death teleportation)
- NaN/Inf quality gates in vectorizer
- Pre-training data quality report
- `match_complete` flag for Teacher/Digester coordination
- Cascading match deletion + orphan detection
- Data lineage tracking (audit trail)

### What's Fragile

**1. Silent Failure Philosophy**

The entire backend follows a pattern of "log the error, don't crash." This is good for uptime but **terrible for user experience**:

```python
# coaching_service.py — typical pattern
try:
    insights = generate_coper_coaching(...)
except Exception as e:
    _coaching_logger.warning("COPER failed: %s", e)
    # Falls back to Hybrid silently — user sees nothing
```

The user sees "Generating coaching..." for 10 seconds, then gets degraded output. No popup, no toast, no indication that the system fell back from Level 1 to Level 3 coaching. **The user thinks they're getting the best analysis when they're getting the simplest.**

**2. Backup Failure Halts Everything**

```python
# session_engine.py
_backup_failed = False  # Module-level flag

# If BackupManager crashes (disk full, permission denied):
_backup_failed = True

# Teacher daemon checks:
if _backup_failed:
    logger.warning("Teacher: training skipped — backup failed at startup.")
    # Training halts FOREVER. No recovery path. No user notification.
```

**3. No Timeouts on Critical Operations**

- Coaching generation has no timeout. If RAG knowledge retrieval hangs, the UI locks.
- Ollama (local LLM) calls have no timeout. If Ollama is slow, the app blocks indefinitely.
- Demo parsing has no overall timeout. A corrupted 2 GB .dem file blocks the Digester indefinitely.

**4. No Rate Limiting on Ingestion**

If a user drops 100 .dem files at once, the watcher spawns threads for all of them. Each thread polls file stability. On a laptop with 8 GB RAM, this can OOM. There's no queue, no concurrency cap, no backpressure.

### What's Missing

| Feature | Impact | Difficulty |
|---------|--------|------------|
| GPU detection + warning | Users don't know training is 50x slower on CPU | Easy (1 day) |
| Coaching timeout (30s) | Prevents UI lockup | Easy (1 day) |
| Ingestion rate limiting | Prevents OOM on batch imports | Medium (2-3 days) |
| Storage quota warning | Users don't know when disk is filling | Easy (1 day) |
| Error toasts in UI | Users know when coaching degrades | Medium (3-5 days) |
| Ollama health check | App checks if local LLM is available before calling it | Easy (1 day) |

---

## 5. Frontend: Product or Prototype?

### Architecture Quality: High

**Pattern:** MVVM (Model-View-ViewModel) with PySide6/Qt6

- **Views:** Screen widgets with QSS stylesheet theming
- **ViewModels:** QObject subclasses with typed signals, background Worker threads
- **State:** Singleton `AppState` polls `CoachState` DB row every 10 seconds, marshals to main thread via signals

No UI blocking. Proper async discipline. Signal-based updates. This is correct Qt architecture.

### Theme System: Professional

**ThemeEngine** (`apps/qt_app/core/theme_engine.py`):
- 3 palettes: CS2 (orange), CSGO (blue-grey), CS 1.6 (green retro)
- QSS stylesheets with hover states, focus states, border-radius, scrollbar styling
- Wallpaper system with opacity blending
- Custom font registration (Roboto, JetBrains Mono, CS Regular, YUPIX)

### Custom Charts: No Library Dependencies

All 6 chart widgets are hand-rolled with QPainter — no matplotlib, no QtCharts:

| Widget | Purpose | LOC |
|--------|---------|-----|
| RadarChart | Performance spider/skill chart | 117 |
| RatingSparkline | Compact rating history | 96 |
| TrendChart | Time-series evolution | 91 |
| MomentumChart | Team momentum visualization | 107 |
| EconomyChart | Round-by-round economy | 82 |
| UtilityBarChart | Utility usage comparison | 75 |

Why custom? QtCharts doesn't match gaming aesthetics. These give precise control over colors, layouts, and CS2-specific visuals.

### i18n: Complete for 3 Languages

- English, Portuguese, Italian — 136 translation keys each
- `QtLocalizationManager` with dynamic language switching via `retranslate()` on all screens
- Fallback chain: JSON (current lang) → hardcoded (current) → hardcoded (English) → raw key

### Tactical Viewer: The Flagship Feature

The tactical analyzer (`apps/qt_app/screens/tactical_viewer_screen.py`) is the most impressive screen:
- 2D pixel-accurate map rendering with DDS textures
- Real-time player position dots with team colors
- Timeline scrubber for round/tick navigation
- Ghost player overlay (shows where AI thinks you should stand)
- Player sidebar with health, equipment, role indicators
- Multi-level map support (Nuke lower, Vertigo lower)

This alone could be a selling point. **No competing product offers offline, privacy-first tactical replay with AI ghost positioning.**

### The Stub Problem

`apps/qt_app/screens/placeholder.py` (77 lines) defines a generic `PlaceholderScreen` class that shows a centered label with the screen name + "Coming Soon." Eight screens use this. They're all **visible in the sidebar navigation** with real icons and labels. A user can click them and land on an empty screen.

**This is the single biggest barrier to shipping.** The solution is simple: hide or disable stub screens in the sidebar until they're implemented. Ship 5 screens, call it "Early Access."

### Honest UX Verdict

| Aspect | Assessment |
|--------|-----------|
| Visual quality | Professional dark gaming aesthetic — competitive with paid tools |
| Architecture | Clean MVVM, proper async, no anti-patterns |
| Feature completeness | 38% (5/13 screens) — not shippable without hiding stubs |
| Performance | No UI blocking, proper worker threads |
| Accessibility | WCAG 1.4.1 color contrast via text labels alongside color coding |
| Stability | No obvious crashes in implemented code paths |

---

## 6. Dependency Reality

### Bundle Size

| Component | Size | Notes |
|-----------|------|-------|
| Python + PySide6 (Qt6) | ~150 MB | Cross-platform UI framework |
| PyTorch (CPU-only) | ~1.2 GB | ML inference and training |
| PyTorch (CUDA 12.1) | ~2.3 GB | GPU variant — **current default, too large** |
| NumPy + SciPy + scikit-learn | ~200 MB | Scientific computing |
| OpenCV | ~150 MB | Image processing for tensors |
| Matplotlib | ~30 MB | Legacy visualization (still required by some widgets) |
| Application code + assets | ~25 MB | Source, fonts, map textures, themes |
| **Total (CPU-only)** | **~1.6 GB** | Recommended for distribution |
| **Total (CUDA)** | **~2.5 GB** | Current default — must change |

**Problem #1:** The default build bundles CUDA PyTorch (2.3 GB). For a desktop app targeting gamers, a 2.5 GB installer is painful. Solution: default to CPU-only for distribution, document GPU setup for power users.

**Problem #2:** SentenceTransformer (SBERT) auto-downloads ~400 MB of model weights on first use. No progress bar. No warning. The user's first coaching request triggers a 400 MB download with no indication of what's happening.

### Critical Dependency Issues

| Issue | Severity | Impact |
|-------|----------|--------|
| `requirements-lock.txt` contains Windows-only packages (`kivy-deps.angle`, `pywin32`) without platform markers | High | Linux/macOS installs crash |
| Phantom PDF deps still pinned (`pdfminer`, `pdfplumber`, `PyMuPDF`, `pypdf`) — code removed but deps remain | Medium | ~50 MB wasted in bundle |
| `demoparser2` license not verified | High | Legal risk for commercial distribution |
| Playwright excluded from frozen build but HLTV scraper imports it | Medium | HLTV sync crashes in packaged build |
| `hflayers` (Hopfield) and `ncps` (LTC) are niche academic libraries | Low | May become unmaintained |

### License Compatibility

| Package | License | Safe for Proprietary? |
|---------|---------|----------------------|
| PySide6 | LGPL v3 | Yes (dynamic linking, unmodified) |
| PyTorch | BSD | Yes |
| SQLAlchemy | MIT | Yes |
| OpenCV | Apache 2.0 + BSD | Yes (needs attribution) |
| FastAPI | MIT | Yes |
| Sentry SDK | BSD | Yes (opt-in telemetry) |
| demoparser2 | **UNKNOWN** | **Must verify before commercial release** |

**Verdict:** All major dependencies are safe for proprietary distribution. The only blocker is verifying `demoparser2`'s license.

---

## 7. What Breaks for Real Users

### Scenario 1: Windows User Without Docker

**User** downloads installer, installs, opens app. Everything works for local demo analysis. User sees "HLTV Sync" in settings and enables it.

**What happens:**
1. App calls `ensure_flaresolverr()` → `docker info` fails
2. Error logged: `"Docker unavailable. Install Docker Desktop..."`
3. User has no idea what Docker is
4. HLTV sync never works
5. Pro baseline stale or missing

**Impact:** Coaching degrades from "your flash effectiveness is 0.31 vs pro 0.68" to generic statistical deviations. The user never knows what they're missing. **Workaround:** Pre-compute and bundle pro baseline CSV (already partially done).

### Scenario 2: 100 Demos Dropped at Once

**User** copies their entire demo folder (100 .dem files) to the watch directory.

**What happens:**
1. Watcher detects 100 new files simultaneously
2. Spawns monitoring threads for each — all polling file stability
3. System RAM climbs (each thread + file handle + buffer)
4. On a laptop with 8 GB RAM: potential `MemoryError`

**Impact:** App crashes. User thinks data is lost (it isn't, but they don't know). **Fix needed:** Queue with max 10 concurrent processing slots.

### Scenario 3: No Dedicated GPU

**User** has a laptop with integrated Intel graphics. Starts training.

**What happens:**
1. `torch.cuda.is_available()` returns `False`
2. Training silently falls back to CPU
3. What should take 10 minutes takes 8+ hours
4. No warning, no estimated time, no indication of degraded performance

**Impact:** User leaves laptop running for days thinking training is progressing normally. **Fix needed:** Print clear message: "No GPU detected. Training will be significantly slower. Consider using a machine with an NVIDIA GPU."

### Scenario 4: Disk Full During Backup

**User's** SSD has 1 GB free. Background backup triggers.

**What happens:**
1. `BackupManager.create_checkpoint()` → `VACUUM INTO` fails with `OSError: No space left`
2. `_backup_failed = True` flag set at module level
3. Teacher daemon checks flag → skips training forever
4. No error popup, no log visible to user
5. Training silently stops — never resumes until app restart with more disk space

**Impact:** Complete training halt with zero user feedback. **Fix needed:** Make backup failure non-fatal for training; warn user about low disk space.

### Scenario 5: External SSD Disconnects

**User** has 200 pro demos on external SSD. Demo #150 is being parsed when USB cable disconnects.

**What happens:**
1. Match data manager tries to write to `[external]/match_data/match_150.db`
2. Path is invalid (drive offline)
3. Falls back to in-project path silently
4. File written to internal storage instead
5. Future accesses are split across two storage locations

**Impact:** Data scattered across drives. Performance degrades. User has no idea why. **Fix needed:** Detect storage path change and warn user.

### Scenario 6: HLTV Rate Limiting

**User** enables HLTV sync. Scraper runs for 1 hour, successfully pulls 50 player profiles.

**What happens:**
1. HLTV/Cloudflare starts returning HTTP 429 (Too Many Requests)
2. FlareSolverr retries 2-3 times
3. Code logs warning, pauses scraper
4. User sees "HLTV Sync: Active" in dashboard but no new data arrives

**Impact:** Pro baseline stuck at 50 profiles. User thinks sync is working but it's stalled. **Fix needed:** Surface rate-limit status in UI with estimated resume time.

---

## 8. Cross-Platform Reality

### Current State

| Platform | Binary | Installer | Tested in CI | Package Format |
|----------|--------|-----------|-------------|---------------|
| Windows 10/11 | Yes (PyInstaller) | Yes (Inno Setup) | Yes | `.exe` |
| Ubuntu Linux | No | No | Tests only | Source install |
| macOS | No | No | No | Nothing |

### What Would Be Needed

**Linux (2-4 weeks):**
- AppImage or .deb packaging script
- FHS-compliant paths (`~/.local/share/MacenaCS2Analyzer/`)
- Desktop entry file for app launcher
- Update CI to build Linux binary
- Test on Ubuntu 22.04+ (majority of Linux gamers)

**macOS (2+ months):**
- Apple Developer account ($99/year)
- Code signing + notarization (Apple requirements — mandatory since Catalina)
- Universal binary (Intel + Apple Silicon)
- `.dmg` or `.pkg` installer
- Add macOS to CI matrix

**Reality check:** Linux gaming is ~2-4% of Steam users. macOS is ~3%. Windows is 93%. For a solo developer, **Windows-only is a defensible launch strategy.** Linux can follow. macOS is a luxury.

### Cross-Platform Code Issues

- `core/platform_utils.py` imports from Kivy (`from kivy.utils import platform`) — tight coupling to Kivy even in Qt build
- `os.getuid()` used in HMAC key derivation — doesn't exist on Windows (falls back to `"win"` string, meaning all Windows machines share same HMAC key)
- Windows single-instance mutex via `ctypes.windll.kernel32` — no equivalent on Linux (multiple instances can corrupt database)
- Path handling assumes Windows-first (`LOCALAPPDATA`, registry access)

---

## 9. Competitive Landscape

### Existing CS2 Coaching Tools

| Product | Model | Price | Strengths | Weaknesses |
|---------|-------|-------|-----------|------------|
| **Leetify** | Cloud SaaS | Free + $5/mo premium | Auto-sync, web dashboard, team features, mobile app | Cloud-only, privacy concerns, generic advice |
| **Scope.gg** | Cloud SaaS | Free + premium | Beautiful UI, heatmaps, 3D replay | Subscription, limited free tier |
| **Refrag** | Cloud SaaS | Free + $10/mo | AI suggestions, practice routines | Expensive, requires upload |
| **CSGO Demos Manager** | Desktop (free) | Free | Robust demo browser, stats | No coaching, no AI, abandoned |
| **This project** | Desktop (offline) | TBD | AI ghost player, game theory, privacy-first, no subscription | Solo dev, incomplete UI, no cloud |

### This Project's Competitive Edge

1. **Fully offline.** No cloud upload. No subscription. Privacy-first. For players who don't want their demos on someone else's server.
2. **Game theory engines.** Bayesian death probability, expectiminimax game trees, entropy analysis — no competitor does this. These work TODAY with zero ML training.
3. **Ghost player overlay.** No competitor offers an AI-predicted "where you should stand" overlay on the tactical map.
4. **One-time purchase model.** In a market of monthly subscriptions, a $30 perpetual license is differentiated.
5. **Deep personalization.** Not generic advice — analysis of YOUR specific replays, YOUR specific habits, compared against pro baselines from YOUR rank range.

### This Project's Competitive Disadvantage

1. **Solo developer** vs. funded teams with designers, backend engineers, QA, marketing.
2. **No cloud infrastructure.** No auto-sync with Steam. No web dashboard. No mobile app.
3. **Incomplete UI.** 5 of 13 screens functional. Competitors have polished, complete products.
4. **Training data scarcity.** 11 demos ingested, ~200 available. Competitors have millions of matches.
5. **No community.** No Discord, no subreddit, no YouTube tutorials, no word-of-mouth.

### The Fundamental Question

**Can offline + privacy + deeper AI beat cloud + team + polish?**

Only if the coaching output is **demonstrably better** for the user's specific situation. Generic "position better on B site" advice loses to Leetify. But "in YOUR last 50 rounds on Mirage B site, you overpeek apartments 73% of the time, and your Bayesian death probability spikes to 0.82 when you do — pros hold from van with 0.35 death probability" — that wins.

The game theory engines can deliver this today. The ML layer will amplify it later. **Lead with game theory. Prove value. Then scale with ML.**

---

## 10. Monetization Paths (Honest)

### Path 1: Direct Sale ($30-50 one-time)

**Viable IF** feature completeness reaches ~70% and coaching output visibly beats free alternatives like Leetify's free tier.

**Pros:** Simple model, no recurring costs, attractive to gamers tired of subscriptions.
**Cons:** Requires high upfront polish. No recurring revenue. Updates must be funded by new sales.

**Realistic revenue:** At $30 with 1% conversion of CS2's ~1M daily active players who watch tutorials... that's aspirational. A more honest target: 500-2,000 sales in year 1 if the product genuinely helps players rank up. That's $15K-$60K.

### Path 2: Early Access ($15-20)

**Viable NOW** with honest scope communication.

**Pros:** Revenue starts immediately. User expectations managed ("Early Access — 5 screens, more coming"). Community feedback drives development priorities.
**Cons:** Risk of negative reviews if early users hit stub screens. Must deliver updates consistently.

**Platforms:** itch.io (no approval process, 10% cut), Gumroad (same), Steam (30% cut, requires Steamworks approval, but massive audience).

### Path 3: Open-Core (free base + paid pro)

**Best risk/reward for a solo developer.**

**Free tier:** Game theory analysis (Bayesian death probability, blind spots, economy optimization, utility effectiveness). These work today, need zero ML, and already beat generic LLM advice for specific situations.

**Paid tier ($20-30):** ML-powered coaching (JEPA patterns, ghost player positioning, VL-JEPA concept explanations), tactical replay viewer, longitudinal trend tracking.

**Pros:** Builds community. Free tier proves value. Paid tier monetizes power features. Word-of-mouth from free users drives paid conversions.
**Cons:** Must clearly separate free/paid features. Risk of "everything important is free" if boundary is wrong.

### Path 4: SDK/API Licensing

**Premature.** Requires proven value and demand from third-party developers. Could become viable after establishing user base. The game theory engines as a library (Bayesian death probability, game tree search for CS2) could interest other esports analytics companies.

### Path 5: Portfolio Piece

**Already valuable.** This project demonstrates:
- Self-taught Python in 3 months
- ML pipeline (JEPA, contrastive learning, RAP architecture)
- Systems engineering (tri-database, daemon coordination, atomic writes)
- Game theory (Bayesian inference, expectiminimax, Shannon entropy)
- UI development (Qt6, MVVM, custom chart rendering)
- Data engineering (demo parsing, feature extraction, 17.3M row database)

For job applications, freelance opportunities, or investor conversations, this is compelling evidence of engineering capability.

---

## 11. The Roadmap to v1.0

### Phase A: Ship-Blocking Fixes (2-3 weeks)

These must be done before any public release:

| # | Task | Files | Days |
|---|------|-------|------|
| A1 | Hide/disable 8 stub screens in sidebar (show only functional 5) | `main_window.py` | 1 |
| A2 | GPU detection + user warning on training start | `training_orchestrator.py`, `coach_manager.py` | 1 |
| A3 | Default to CPU-only PyTorch for distribution builds | `requirements-ci.txt`, `packaging/` | 1 |
| A4 | Fix `requirements-lock.txt` (remove phantom PDF deps, add platform markers) | `requirements-lock.txt` | 1 |
| A5 | Add error toasts when coaching degrades (silent fallback → visible notification) | `coaching_service.py`, Qt notification widget | 3 |
| A6 | Add LICENSE file + verify demoparser2 license | Project root | 1 |
| A7 | Code-sign Windows executable | `packaging/`, CI workflow | 2 |
| A8 | Add SBERT model download progress indicator | `experience_bank.py` | 2 |

### Phase B: Early Access Quality (2-4 weeks)

Minimum for a paid Early Access release:

| # | Task | Days |
|---|------|------|
| B1 | Settings screen (theme, language, demo paths — replace stub) | 3 |
| B2 | Setup wizard (first-time Steam path + demo folder config) | 3 |
| B3 | Match Detail screen wired to backend data | 5 |
| B4 | Rate-limit ingestion (max 10 concurrent demos) | 2 |
| B5 | Storage quota warning (>50 GB) | 1 |
| B6 | Coaching generation timeout (30s max, fallback notification) | 1 |
| B7 | Make backup failure non-fatal for training | 1 |
| B8 | Linux single-instance mutex (fcntl flock) | 1 |

### Phase C: Competitive Parity (1-2 months)

Full v1.0 release:

| # | Task | Days |
|---|------|------|
| C1 | Complete remaining 5 screens (Profile, Steam, FaceIT, Help, Edit Profile) | 10 |
| C2 | Linux packaging (AppImage) | 5 |
| C3 | Test coverage to 50%+ | 10 |
| C4 | Deployment documentation (install guide, troubleshooting) | 3 |
| C5 | Train on 200 pro demos — validate coaching output quality | 5 |
| C6 | User feedback telemetry (opt-in via Sentry) | 2 |
| C7 | Remove Kivy coupling from `platform_utils.py` | 1 |
| C8 | Docker setup documentation (HLTV sync) | 2 |

### What NOT To Build Yet

- macOS support (2% of target audience, 2+ months work)
- Mobile app (different framework entirely)
- Cloud/web dashboard (different architecture entirely)
- Multi-player team features (need user base first)
- Replay recording/streaming (scope creep)

---

## 12. Final Verdict

**Can this become an actual product?** Yes. The engineering foundation — database architecture, ML pipeline, game theory engines, data pipeline — is production-grade in the areas that matter most. The gap is not engineering quality; it's **feature completeness and user-facing polish**.

**The fastest path to revenue** is an Early Access release on itch.io or Gumroad: hide the 8 stub screens, ship the 5 functional ones, lead with the game theory engines (which work today with zero training data), price at $15-20, and iterate based on user feedback. This could be ready in 2-3 weeks.

**The honest risk:** The CS2 coaching market has funded competitors with teams of 10-20 engineers. A solo developer cannot compete on breadth. The only viable strategy is **depth** — make the game theory analysis and personalized coaching so specific to each player's replays that generic cloud tools can't match it. That's where this project's architecture was designed to win, and with 200 pro demos ready for training, the data to prove it is already on the SSD.
