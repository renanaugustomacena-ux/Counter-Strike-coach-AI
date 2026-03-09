# Desktop Application, User Interface, Visualization, and Reporting
# Macena CS2 Analyzer — Technical Audit Report 7/8

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| Report ID | AUDIT-2026-07 |
| Date | 2026-03-08 |
| Version | 1.0 |
| Classification | Internal — Engineering Review |
| Auditor | Engineering Audit Protocol v3 |
| Scope | 35 Python/KV files across desktop app, entry points, reporting, observability, and onboarding |
| Total LOC Audited | ~11,877 |
| Audit Standard | ISO/IEC 25010, ISO/IEC 27001, OWASP Top 10, IEEE 730, CLAUDE.md Constitution, WCAG 2.1 AA |
| Previous Audit | N/A (baseline audit) |

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Audit Methodology](#2-audit-methodology)
3. [Desktop Application UI](#3-desktop-application-ui)
4. [Application Entry Points](#4-application-entry-points)
5. [Reporting & Visualization](#5-reporting--visualization)
6. [Observability Infrastructure](#6-observability-infrastructure)
7. [Onboarding & Knowledge Base](#7-onboarding--knowledge-base)
8. [Consolidated Findings Matrix](#8-consolidated-findings-matrix)
9. [Recommendations](#9-recommendations)
10. [Appendix A: File Inventory](#appendix-a-complete-file-inventory)
11. [Appendix B: Glossary](#appendix-b-glossary)
12. [Appendix C: Data Flow Diagrams](#appendix-c-data-flow-diagrams)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Domain Health Assessment

**Overall Rating: SOUND**

The desktop application layer demonstrates a mature MVVM architecture built on Kivy/KivyMD with consistent design patterns across 12 screens. The codebase exhibits three tiers of rendering optimization — layer separation, widget pooling, and texture caching — that together enable smooth real-time tactical map playback. The entry point ecosystem (7 scripts + unified console) provides comprehensive operational control, and the observability infrastructure (RASP, Sentry, structured logging) represents the cleanest subsystem in the entire project.

Key strengths include: correct Kivy threading model (all UI updates via `Clock.schedule_once`), proper lifecycle management with `on_enter`/`on_leave` symmetry, WCAG 2.1 AA accessibility considerations (P4-07 rating labels), and pervasive internationalization via `i18n.get_text()`.

The domain earns "SOUND" rather than "EXEMPLARY" due to: API key fields lacking password masking (security), a high-severity onboarding query bug (counts all players instead of specific user), MD5-based match ID generation with collision risk in `run_ingestion.py`, stale PID file handling in `hltv_sync_service.py`, and several entry point scripts with fragile path assumptions.

### 1.2 Critical Findings Summary

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| DA-03-01 | HIGH | `run_ingestion.py` MD5 match_id truncated — collision risk | EVOLVED (reduced severity) |

*Resolved since audit:* DA-16-01 (HIGH), DA-06-01 (HIGH), DA-08-01 (HIGH), DA-KV-01 (MED), DA-01-03 (MED)

### 1.3 Quantitative Overview

| Metric | Value |
|--------|-------|
| Files Audited | 35 |
| Total Lines of Code | ~11,877 |
| Classes Analyzed | 38 |
| Functions/Methods Analyzed | ~310 |
| Findings: CRITICAL | 0 |
| Findings: HIGH | 1 (3 fixed) |
| Findings: MEDIUM | 12 (9 fixed) |
| Findings: LOW | 64 (1 fixed) |
| Findings: INFO/GOOD | 12 |
| Remediation Items Previously Fixed | 12 (F7-14, F7-18, F7-21, F7-22, F7-25, F7-27, F7-29, F7-31, F7-33, F7-36, F7-39, P4-07) |
| Remaining Deferred Items | 0 |

### 1.4 Risk Heatmap

```
              Impact
         Low    Med    High
    ┌────────┬────────┬────────┐
Hi  │        │        │ DA-03  │
    │        │        │(evolved)│
    ├────────┼────────┼────────┤
Med │  LOW   │        │        │
    │ issues │        │        │
    ├────────┼────────┼────────┤
Lo  │        │        │        │
    └────────┴────────┴────────┘
         Likelihood
```

---

## 2. AUDIT METHODOLOGY

### 2.1 Standards Applied

- **ISO/IEC 25010** — Software product quality model
- **WCAG 2.1 AA** — Web Content Accessibility Guidelines (applied to desktop UI)
- **ISO/IEC 27001** — Information security management
- **CLAUDE.md Constitution** — Project engineering rules (Rules 1–7, emphasis on Rule 3: Frontend/UX)
- **STRIDE** — Threat modeling

### 2.2 Severity Classification

| Severity | Definition | SLA |
|----------|------------|-----|
| CRITICAL | System failure, data loss, security breach | Immediate fix |
| HIGH | Significant functional impact, exploitable security weakness | Current sprint |
| MEDIUM | Moderate impact on reliability, performance, or maintainability | Next 2 sprints |
| LOW | Minor code quality, style, documentation | Next refactoring |
| INFO | Observations, positive findings | No SLA |

---

## 3. DESKTOP APPLICATION UI

### 3.1 `apps/desktop_app/__init__.py` — Package Marker

**File Metrics:** 1 LOC

Empty package marker. No issues.

---

### 3.2 `apps/desktop_app/coaching_chat_vm.py` — Coaching Chat ViewModel

**File Metrics:** 138 LOC | 1 class (`CoachingChatViewModel`) | 8 methods

**Architecture:** MVVM ViewModel using Kivy `EventDispatcher` with `ListProperty` for messages. Background thread for Ollama calls with `Clock.schedule_once` for UI-thread marshalling. Defensive `_lock` (threading.Lock) currently a no-op in single-threaded usage.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-CC-01 | LOW | `_lock` is defensive programming — correct for future multi-threading but adds code noise in current single-threaded usage | Keep as-is for future safety |
| DA-CC-02 | LOW | `send_message` spawns a daemon thread per message. Rapid sends could queue many threads | Add debounce or queue mechanism |

**Positive Observations:** Clean ViewModel pattern with proper UI-thread marshalling.

---

### 3.3 `apps/desktop_app/data_viewmodels.py` — Data ViewModels

**File Metrics:** 275 LOC | 3 classes | 14 methods

**Architecture:** Three ViewModels for match history, match detail, and performance screens. Background thread data loading with `Clock.schedule_once` for UI updates.

**Correctness Analysis:**

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-DV-01 | MEDIUM | `MatchHistoryViewModel.load()` lacks guard against concurrent loads — two rapid `on_enter` calls could spawn duplicate threads | Add `_is_loading` flag |
| DA-DV-02 | LOW | `PerformanceViewModel` loads all match history into memory for DataFrame operations | Cap at reasonable limit |
| DA-DV-03 | LOW | SQLAlchemy session scoping correct — data extracted within session before closing | Positive observation |

---

### 3.4 `apps/desktop_app/ghost_pixel.py` — Debug Overlay Widget

**File Metrics:** 140 LOC | 1 class | 6 methods

**Architecture:** Debug-only widget that renders ghost predictions as transparent overlays on the tactical map.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-GP-01 | LOW | No debug-mode gate — widget is always importable and instantiable. Should be gated behind `DEBUG_MODE` config flag | Add config guard |
| DA-GP-02 | LOW | `setattr(self, "ghost_" + key, ...)` dynamically creates attributes, bypassing type checking | Define attributes explicitly |

---

### 3.5 `apps/desktop_app/help_screen.py` — Help Screen

**File Metrics:** 79 LOC | 1 class | 5 methods

Clean screen with good error handling at every external call site. No significant issues.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-HS-01 | LOW | Topics reloaded on every `on_enter`. Could cache, but help content is small | Acceptable |

---

### 3.6 `apps/desktop_app/match_detail_screen.py` — Match Detail Screen

**File Metrics:** 451 LOC | 1 class | 16 methods

**Architecture:** MVVM screen with programmatic widget construction for match sections (score, economy, rounds, highlights).

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-MD-01 | MEDIUM | `app.selected_demo` accessed as attribute. If never set, raises `AttributeError`. The `if not demo:` check handles `None` but not missing attribute | Use `getattr(app, 'selected_demo', None)` |
| DA-MD-02 | LOW | `stats.get("rating", 1.0) or 1.0` — double fallback treats `0.0` as invalid rating | Check explicitly for None |
| DA-MD-03 | LOW | `from kivymd.uix.label import MDIcon` imported inside loop body. Python caches imports, so negligible cost | Move to top of file |
| DA-MD-04 | LOW | Dynamic height binding `content.bind(height=lambda inst, h: setattr(card, 'height', h + dp(24)))` could cause layout thrashing on rapid height changes | Acceptable for current usage |

**Performance:** For 30+ round matches, `_build_rounds_section` creates ~90+ widgets. Consider virtualization if performance degrades.

**Positive Observations:** HLTV 2.0 breakdown visualization with per-component color coding. P4-07 accessibility compliance for color-blind users.

---

### 3.7 `apps/desktop_app/match_history_screen.py` — Match History Screen

**File Metrics:** 162 LOC | 1 class | 8 methods

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-MH-01 | MEDIUM | `_on_matches_loaded` silently returns on empty list. UI stays in "Loading..." state forever. Should check `if matches is not None` and handle empty list with "No matches found" message | Handle empty list explicitly |
| DA-MH-02 | LOW | Map name extraction regex `r"(de_\w+|cs_\w+|ar_\w+)"` duplicated with match_detail_screen | Extract to shared utility |
| DA-MH-03 | LOW | Same `rating or 1.0` double fallback pattern | Check for None explicitly |

---

### 3.8 `apps/desktop_app/performance_screen.py` — Performance Dashboard

**File Metrics:** 320 LOC | 1 class | 12 methods

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-PS-01 | MEDIUM | Same issue as match_history: `_on_vm_data_changed` returns silently on empty data, leaving screen in loading state | Handle empty data explicitly |
| DA-PS-02 | LOW | `for name, z in sw.get("strengths", [])` assumes 2-tuple elements. If shape changes, crashes with ValueError | Add defensive unpacking |
| DA-PS-03 | LOW | `Clock.schedule_once(lambda dt: graph.plot(...), 0.1)` — 100ms delay for widget tree attachment. Fragile on slow systems | Increase to 200ms with retry |

**Positive Observations:** Strengths/weaknesses comparison against pro baselines with sigma notation (`+1.5σ`) is a strong UX feature. `_section_card` helper cleanly extracted and reused.

---

### 3.9 `apps/desktop_app/player_sidebar.py` — Real-Time Player List

**File Metrics:** 362 LOC | 2 classes | 16 methods

**Architecture:** Object pooling pattern for player list items. `LivePlayerCard` is detailed stats card with HP/armor bars. Widgets cached by `player_id` and reused across frames.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-PB-01 | MEDIUM | `setattr(self, bar_attr, bar)` dynamically creates `hp_bar`/`armor_bar` attributes, bypassing type checking | Define in `__init__` explicitly |
| DA-PB-02 | LOW | Health bar color threshold `hp > 50` hardcoded. Same value in `tactical_map.py` | Extract to shared constant |
| DA-PB-03 | LOW | `"CT" in str(p.team).upper()` — loose string match. "ACTOR" or "CTICA" would match | Use exact equality or enum comparison |
| DA-PB-04 | LOW | `sorted(players, key=lambda x: (not x.is_alive, x.player_id))` — clever but could confuse readers | Add comment explaining the sort |

**Positive Observations:** Widget pooling (lines 263-335) is a significant optimization, avoiding widget creation churn. `clear_all` properly cleans up pool on match switch (F7-14 verified).

---

### 3.10 `apps/desktop_app/tactical_map.py` — Tactical Map Renderer

**File Metrics:** 561 LOC | 1 class | 22 methods

**Architecture:** Layer-based rendering with `InstructionGroup` for map, heatmap, and dynamic elements. Static layers drawn once; dynamic layer redrawn every tick. Async map texture loading and background heatmap generation.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-TM-01 | MEDIUM | `nade.ending_tick + (5 * 64)` hardcodes tick rate as 64. CS2 uses 64 or 128 tick | Derive from demo metadata or use constant |
| DA-TM-02 | MEDIUM | `pulse = 0.5 + 0.15 * math.sin(time.time() * 8)` uses wall-clock time. Molotov pulses when paused and doesn't scale with playback speed | Use game tick time instead of wall clock |
| DA-TM-03 | LOW | `_ghosts` not initialized in `__init__` — first `_redraw` from `_on_size` would fail without `hasattr` guard | Initialize `self._ghosts = []` in `__init__` |
| DA-TM-04 | LOW | `NadeType` imported both at file top and inside `_draw_trajectory` — redundant inner import | Remove inner import |
| DA-TM-05 | LOW | Name texture cache with 64-entry LRU via `next(iter(...))` FIFO eviction — correct for Python 3.7+ dict ordering (F7-21 verified) | Correct |

**Positive Observations:**
- Layer separation correctly avoids re-uploading static textures to GPU every frame
- `_world_to_screen` and `_screen_to_world` correctly handle non-square widgets with uniform scaling (F7-22 verified)
- Detonation overlay system correctly converts game-unit radii to pixel radii via spatial engine

**Concurrency:** `update_heatmap_async` spawns background thread for generation. Multiple rapid calls could race, but last-one-wins behavior is acceptable.

---

### 3.11 `apps/desktop_app/tactical_viewer_screen.py` — Tactical Viewer Coordinator

**File Metrics:** 293 LOC | 1 class | 18 methods

**Architecture:** Thin UI coordinator between Playback, Ghost, and Chronovisor ViewModels. MVVM with proper binding/unbinding in lifecycle methods.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-TV-01 | MEDIUM | Binding on `on_enter` without checking for duplicate — if `on_enter` called twice without `on_leave`, creates duplicate binding | Guard with `_bindings_active` flag |
| DA-TV-02 | LOW | `self.ids.tactical_map._redraw()` calls private method directly | Expose public API |
| DA-TV-03 | LOW | `self.last_frame = frame` stores frame without `__init__` initialization — accessed via `hasattr` check | Initialize in `__init__` |
| DA-TV-04 | LOW | F7-27 guard against stale callback after screen navigation — correctly implemented | Verified remediation |

**Positive Observations:** Proper `on_enter`/`on_leave` symmetry with cleanup. `_tick_event` guard prevents multiple concurrent interval timers.

---

### 3.12 `apps/desktop_app/tactical_viewmodels.py` — Tactical ViewModels

**File Metrics:** 346 LOC | 3 classes | 18 methods

**Architecture:** Three specialized ViewModels extracted from former "God Object" screen: `TacticalPlaybackViewModel`, `TacticalGhostViewModel`, `TacticalChronovisorViewModel`.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-TVM-01 | MEDIUM | `replace(p, x=gx, y=gy, is_ghost=True)` assumes `InterpolatedPlayerState` has `is_ghost` field. If not, `replace` raises TypeError. `tactical_map.py` accesses via `getattr(..., "is_ghost", False)` suggesting it may not be a formal field | Add `is_ghost` to dataclass definition or use dict merge |
| DA-TVM-02 | LOW | `self.current_tick = tick` in `seek_to_tick` — could desync if engine clamps tick to bounds | Read back from engine after seek |
| DA-TVM-03 | LOW | `_scan_cancel` only checked at scan start — cannot interrupt mid-scan for long-running analyses | Add check inside scanner iteration |

**Positive Observations:** Clean God Object decomposition. F7-25 cooperative cancellation correctly implemented. Each ViewModel has clear responsibility boundaries.

---

### 3.13 `apps/desktop_app/timeline.py` — Timeline Scrubber

**File Metrics:** 113 LOC | 1 class | 6 methods

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-TL-01 | MEDIUM | All game events redrawn every `_redraw` call. For matches with thousands of events, this could be expensive | Cache event marker positions |
| DA-TL-02 | LOW | `progress_ratio = self.current_tick / self.max_tick` — could exceed 1.0 if `current_tick > max_tick` | Clamp to [0.0, 1.0] |
| DA-TL-03 | LOW | `self.metadata_textures = {}` initialized but never used — dead code | Remove |
| DA-TL-04 | LOW | F7-33 touch position clamped to `[0.0, 1.0]` — correct | Verified remediation |

---

### 3.14 `apps/desktop_app/widgets.py` — Matplotlib Bridge Widgets

**File Metrics:** 273 LOC | 7 classes | 14 methods

**Architecture:** `MatplotlibWidget` base class renders Matplotlib figures to Kivy textures via PNG buffer. Six specialized chart widgets.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-WG-01 | MEDIUM | `matplotlib.use("Agg")` must be called before `import matplotlib.pyplot`. If another module imports pyplot first, this fails. Fragile import order dependency | Move to earliest application import (main.py) |
| DA-WG-02 | LOW | PNG encode/decode overhead for figure→texture conversion. Acceptable for static charts | No action |
| DA-WG-03 | LOW | Radar chart guard for minimum 3 attributes (F7-36) prevents degenerate rendering | Verified remediation |

**Positive Observations:** Dark theme styling consistently applied. `plt.close(fig)` properly releases memory. `UtilityBarWidget` provides clean "You vs Pro" comparison.

---

### 3.15 `apps/desktop_app/wizard_screen.py` — Setup Wizard

**File Metrics:** 390 LOC | 1 class | 18 methods

**Architecture:** Step-based wizard (intro → brain_path → demo_path → finish) with `MDFileManager` for folder selection and platform-specific drive detection.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-WZ-01 | MEDIUM | `os.makedirs(self.demo_path, exist_ok=True)` creates directories from unsanitized user text field input. Path not validated before `validate_demo_step` | Add path sanitization (reject paths outside user home) |
| DA-WZ-02 | MEDIUM | `if "Permission" in str(e) or "Access" in str(e)` — locale-dependent string matching on exception messages | Use `isinstance(e, PermissionError)` |
| DA-WZ-03 | LOW | `self.app = None` set in `__init__`, populated in `on_enter`. Safe since UI interactions only happen after screen entry | Acceptable |
| DA-WZ-04 | LOW | Dead imports at lines 373-374: `import subprocess; import sys` never used | Remove |
| DA-WZ-05 | LOW | Redundant `from ... import i18n` inside `build_demo_path` — already imported at top | Remove redundant import |

**Security:** User-provided path input lacks validation against path traversal. A confused user could enter `/etc/` or create directories in sensitive locations.

---

### 3.16 `apps/desktop_app/theme.py` — Theme Constants

**File Metrics:** 32 LOC | 2 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-TH-01 | LOW | `rating_label` has finer granularity (5 tiers) than `rating_color` (4 tiers). "Excellent" and "Good" both map to green. Intentional | No action — label provides finer distinction |

**Positive Observations:** P4-07 WCAG 1.4.1 compliance — text labels alongside colors for color-blind accessibility.

---

### 3.17 `apps/desktop_app/layout.kv` — KV Layout Definition

**File Metrics:** 1,582 LOC | 6 reusable components | 12 screens

**Architecture:** Declarative Kivy layout with glassmorphism effects, `FadingBackground` wallpaper crossfade, and comprehensive i18n support.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-KV-01 | MEDIUM | Steam API Key input (line 985-988) and FaceIT API Key input (line 1028-1031) displayed in plain `MDTextField` without password masking. API keys visible on screen | Add `password=True` or equivalent masking |
| DA-KV-02 | MEDIUM | All 12 screens instantiated at startup via `MDScreenManager`. Impacts startup time | Consider lazy screen creation |
| DA-KV-03 | LOW | Hardcoded English text: "A Steam Web API Key allows the app..." (line 974) and "Ingestion Mode:" (line 1205) | Add to i18n system |
| DA-KV-04 | LOW | F7-39 documented: two `FitImage` textures for crossfade consume ~64MB GPU on 4K | Documented and accepted |
| DA-KV-05 | LOW | Training progress expression `current_epoch / total_epochs * 100` — ternary guard prevents division by zero | Correctly handled |

**Security:** API keys displayed in plaintext. Users' Steam and FaceIT API keys are visible to anyone who can see the screen.

---

### 3.18 `apps/spatial_debugger.py` — Coordinate Debug Tool

**File Metrics:** 153 LOC | 1 class | 8 methods

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-SD-01 | LOW | `AssetAuthority.get_map_asset()` dual-path (texture vs source) could lead to stale textures | Handle fallback transition |
| DA-SD-02 | LOW | `self.canvas.after.clear()` on every mouse move — expensive for complex canvases, acceptable for debug tool | Acceptable |
| DA-SD-03 | LOW | Division by zero guarded at line 85 for `<= 0`, but float precision edge case possible | Use epsilon guard |

---

## 4. APPLICATION ENTRY POINTS

### 4.1 `main.py` — Primary GUI Entry Point

**File Metrics:** 1,938 LOC | 1 class (`CS2AnalyzerApp`) | 68 methods

**Architecture:** Primary GUI entry point implementing MVVM with Kivy/KivyMD. Features lazy-loading for heavy dependencies, threaded DB operations, progressive polling backoff for daemon status, and RASP integrity audit at startup.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-01-01 | LOW | `_last_completed_tasks = []` class-level mutable default shared across instances. Only one instance created in practice | No action |
| DA-01-02 | LOW | `ServiceNotification.is_read == False` uses Python equality instead of SQLAlchemy `.is_(False)` | Use `.is_(False)` |
| DA-01-03 | MEDIUM | `json.loads(p["pc_specs_json"])` at line 330 — no try/except for malformed JSON. Corrupt data causes entire profile load to fail | Add inner try/except for JSON parsing |
| DA-01-04 | MEDIUM | `self.ids.insights_list` accessed without guard — KV layout failure raises AttributeError | Use `self.ids.get("insights_list")` |
| DA-01-05 | LOW | `atexit.register(lambda: os.path.exists(out_path) and os.unlink(out_path))` accumulates handlers on repeated dialog opens | Register cleanup once or use tempfile context manager |
| DA-01-06 | LOW | `_ml_status_running` flag without lock protection — race condition on check+set. Consequence is at most a duplicate thread spawn (benign) | Acceptable |
| DA-01-07 | LOW | `self.service_active = not self.service_active` not atomic — only called from UI thread, so safe in practice | Acceptable |

**Security:** Venv guard at line 13 prevents execution outside virtualenv. RASP integrity audit at lines 24-37 before heavy imports. Steam API keys stored in plaintext `settings.json` (accepted until keyring migration).

**Positive Observations:** Extensive use of daemon threads with correct `Clock.schedule_once` marshalling. Progressive backoff prevents wasteful polling. BFS widget refresh with max depth 50 prevents stack overflow. `multiprocessing.freeze_support()` correctly placed for PyInstaller.

---

### 4.2 `run_build.py` — Android Build Script

**File Metrics:** 33 LOC

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-02-01 | MEDIUM | `os.environ["JAVA_HOME"]` hardcoded to `tools/jdk17` — silently overwrites existing JAVA_HOME | Check before overwriting |
| DA-02-02 | MEDIUM | `cwd = "Programma_CS2_RENAN/apps/android_app"` is relative path — fails if script invoked from different directory | Use `Path(__file__).parent` |
| DA-02-03 | MEDIUM | Hardcoded venv path uses forward slashes — fails on Windows | Use `pathlib.Path` |

---

### 4.3 `run_ingestion.py` — Demo Ingestion Pipeline

**File Metrics:** 1,181 LOC | 12 functions

**Architecture:** Procedural pipeline with bulk insert optimization via `pandas.to_sql()` (762s → 97s, 8x speedup). Incremental ingestion via `start_tick` for resumable parsing.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-03-01 | HIGH | `match_id = int(hashlib.md5(demo_name.encode()).hexdigest(), 16) % (10**9)` — MD5 collision probability is non-trivial at 10^9 space (~50% at ~31,623 demos via birthday paradox). Different demos could collide, causing data overwrite | Use SHA-256 truncated to 64-bit or monotonic DB sequence |
| DA-03-02 | MEDIUM | State lookup cap at 50,000 evicts first half of keys (FIFO). Could evict entries needed for later lookups | Use LRU eviction instead of FIFO |
| DA-03-03 | MEDIUM | `monolith_engine = db_manager.engine` accesses engine directly, bypassing session context manager. Write is not transactional with session | Document intentional non-transactional design |
| DA-03-04 | LOW | `PlayerMatchStats.is_pro == False` uses Python equality instead of SQLAlchemy `.is_(False)` | Use `.is_(False)` |
| DA-03-05 | LOW | Circular interpolation for yaw/pitch (lines 496-527) correctly avoids angle discontinuities | Positive observation |

**Performance:** Bulk insert via `to_sql()` is the dominant optimization. `BATCH_SIZE` is 10,000 in HP mode, 2,000 otherwise.

---

### 4.4 `run_worker.py` — Background Ingestion Worker

**File Metrics:** 149 LOC | 3 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-04-01 | MEDIUM | `_should_skip_pro_task` silently delays pro demo processing until 10 are queued. No user notification | Add logging when pro tasks are deferred |
| DA-04-02 | MEDIUM | Stop signal file `hltv_sync.stop` shared with `hltv_sync_service.py`. Stopping HLTV sync also stops ingestion worker | Use independent signal files |
| DA-04-03 | LOW | `return time.sleep(5)` — `time.sleep()` returns None, so this works but is semantically confusing | Use explicit `time.sleep(5); return` |

---

### 4.5 `Train_ML_Cycle.py` — Simple Training Wrapper

**File Metrics:** 23 LOC

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-05-01 | LOW | `import numpy as np`, `import torch`, `from sqlmodel import select` imported but never used | Remove dead imports |
| DA-05-02 | LOW | Simplified alternative to `run_full_training_cycle.py` with no CLI args, no TensorBoard | Consider deprecating one |

---

### 4.6 `hltv_sync_service.py` — HLTV Background Daemon

**File Metrics:** 180 LOC | 4 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-06-01 | HIGH | `start_detached()` checks `PID_FILE.exists()` but does not verify the PID is still alive. Stale PID file from crashed process permanently prevents restart | Check if PID is alive via `os.kill(pid, 0)` |
| DA-06-02 | MEDIUM | On Linux, process launched without `setsid()` or double-fork — not truly detached, receives parent terminal signals | Use `os.setsid` in preexec_fn or double-fork |
| DA-06-03 | LOW | `PID_FILE.write_text(str(process.pid))` — no file locking. Two concurrent calls could race | Use atomic write or flock |

---

### 4.7 `console.py` — Unified Console (TUI + CLI)

**File Metrics:** 1,649 LOC | 4 classes | 42 methods

**Architecture:** Dual-mode operation: Rich Live TUI dashboard and argparse CLI. Command Registry with categories. StatusPoller using background thread with lock-protected cache. Platform-aware input (Windows `msvcrt` vs Unix `tty`/`select`).

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-07-01 | MEDIUM | `DATABASE_URL.replace("sqlite:///", "")` — fragile string manipulation. `sqlite:////absolute/path` would incorrectly strip 3 slashes | Use `urlparse` or handle both `///` and `////` |
| DA-07-02 | MEDIUM | `shutil.rmtree(os.path.join(root, d))` modifies directory tree during `os.walk()`. Can cause skipped directories or errors | Collect paths first, then delete |
| DA-07-03 | LOW | `stderr_file = open(spawn_log, "w", ...)` — file handle intentionally leaked (documented). Better pattern would be single expression | Accept with comment |
| DA-07-04 | LOW | Status change detection via `hash(str(...))` XOR — weak hash, collisions cause missed updates | Use deterministic serialization |

**Security:** API keys collected via `getpass.getpass()` — not visible in process list. Error messages sanitized to redact API keys. `_ALLOWED_CONFIG_KEYS` whitelist prevents arbitrary setting injection.

**Positive Observations:** Terminal state restoration in `finally` block prevents corrupted terminal on crash. TUI refresh throttled to 8 FPS. StatusPoller properly uses `threading.Lock`.

---

### 4.8 `run_full_training_cycle.py` — Full Training Entry Point

**File Metrics:** 116 LOC | 2 functions

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-08-01 | HIGH | `from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator` — git status shows this file as `training_orchestrator.py.backup`. If renamed, import fails at runtime | Verify file exists; update import if renamed |
| DA-08-02 | MEDIUM | `manager._assign_dataset_splits()` accesses private method — breaks if internal API changes | Add public wrapper method |
| DA-08-03 | LOW | f-string in logger calls — should use lazy `%s` formatting | Convert to `%s` |
| DA-08-04 | LOW | `callbacks.close_all()` in finally block ensures TensorBoard writers flushed on error | Positive observation |

---

## 5. REPORTING & VISUALIZATION

### 5.1 `reporting/report_generator.py` — Match Report Generation

**File Metrics:** 87 LOC | 1 class | 4 methods

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-RG-01 | MEDIUM | `self.output_dir = Path("reports")` — relative path depends on working directory | Use absolute path from config |
| DA-RG-02 | MEDIUM | `f"![Heatmap]({Path(heatmap_path).resolve()})"` — absolute path in markdown makes report non-portable | Use relative path |
| DA-RG-03 | LOW | `if p.health == 0` used as death proxy — misses deaths where health data is unavailable | Use explicit death event |
| DA-RG-04 | LOW | Positions appended per-frame per-player — O(n×m) memory for large demos | Stream or sample positions |

---

### 5.2 `reporting/visualizer.py` — Map Visualization Engine

**File Metrics:** 358 LOC | 1 class | 8 methods

**Architecture:** Matplotlib-based visualization with differential heatmaps (pro vs user), critical moments annotation, and map background overlays.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-VZ-01 | MEDIUM | `plt.figure(...)` without `try/finally: plt.close()` — figure leaks memory if `savefig` throws | Add try/finally block |
| DA-VZ-02 | MEDIUM | `self._setup_map_plot()` uses stateful `plt.xlim/plt.ylim` API while methods use OO `ax` API — mixing can cause issues with multiple figures | Use only OO API |
| DA-VZ-03 | LOW | `_get_bounds()` hardcodes map bounds for 6 maps. New maps fall back to (-4000, 4000) | Load from config or map_config.json |
| DA-VZ-04 | LOW | `plt.savefig(str(path))` without `dpi` specification — inconsistent with `dpi=150` used elsewhere | Standardize DPI |

---

## 6. OBSERVABILITY INFRASTRUCTURE

### 6.1 `observability/__init__.py` — Package Marker

**File Metrics:** 1 LOC. No issues.

---

### 6.2 `observability/logger_setup.py` — Centralized Logging Factory

**File Metrics:** 88 LOC | 1 factory function

**Architecture:** `get_logger(name)` factory with RotatingFileHandler (5MB, 3 backups), circular dependency break via `configure_log_dir()` callback, and handler deduplication.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-LS-01 | LOW | If `configure_log_dir()` called after loggers created, existing loggers still point to old directory | Document: call before creating loggers |

**Positive Observations:** `logger.propagate = False` prevents duplicate messages. Console handler filtered to WARNING+. RotatingFileHandler prevents unbounded log growth.

---

### 6.3 `observability/rasp.py` — Runtime Application Self-Protection

**File Metrics:** 138 LOC | 3 functions

**Architecture:** SHA-256 manifest verification with dual-mode (strict in production/PyInstaller, permissive in development).

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-RS-01 | LOW | Development mode returns `(True, [])` if manifest doesn't exist — developers never see integrity warnings | Acceptable by design |

**Security:** SHA-256 appropriate for integrity. Manifest itself is not signed — attacker who modifies files can also modify manifest. `check_frozen_binary()` checks extension, not code signing.

---

### 6.4 `observability/sentry_setup.py` — Error Tracking

**File Metrics:** 153 LOC | 2 functions

**Architecture:** Double opt-in (enabled flag + DSN) for Sentry telemetry. PII scrubbing via `_before_send` hook. Pytest detection gate prevents telemetry during tests.

**Correctness Analysis:** No issues found. This is one of the cleanest files in the entire project.

**Positive Observations:** `send_default_pii=False`, PII scrubbing covers server_name/stacktraces/breadcrumbs, 10% trace sample rate appropriate for production.

---

## 7. ONBOARDING & KNOWLEDGE BASE

### 7.1 `backend/onboarding/new_user_flow.py` — User Onboarding

**File Metrics:** 131 LOC | 3 classes | 6 methods

**Architecture:** State machine: `AWAITING_FIRST_DEMO` → `BUILDING_BASELINE` → `COACH_READY`. TTL-based in-memory cache (60s) for demo counts.

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-16-01 | HIGH | `session.exec(select(func.count(PlayerMatchStats.id))).one()` counts ALL rows regardless of `user_id` parameter. Pro demo imports inflate the counter, potentially declaring coach "ready" before user uploads personal demos | Add `WHERE player_name = user_id` filter |
| DA-16-02 | MEDIUM | `get_onboarding_manager()` creates new instance per call, defeating the purpose of the in-memory cache (each instance has empty cache) | Return singleton or use class-level cache |

---

### 7.2 `backend/knowledge_base/__init__.py` — Package Marker

**File Metrics:** 1 LOC. Single docstring. No issues.

---

### 7.3 `backend/knowledge_base/help_system.py` — In-App Documentation

**File Metrics:** 72 LOC | 1 class | 4 methods

**Architecture:** File-based documentation system reading markdown from `data/docs/`. Simple text search with weighted scoring (title=10, content=1).

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| DA-18-01 | MEDIUM | `help_system = HelpSystem()` global singleton at module import. If `get_resource_path()` not configured during test imports, constructor fails | Guard with lazy initialization |
| DA-18-02 | LOW | `print(f"Error reading doc {filename}: {e}")` uses `print` instead of structured logging | Use `get_logger()` |

---

## 8. CONSOLIDATED FINDINGS MATRIX

### Findings by Severity

#### CRITICAL Findings

None.

#### HIGH Findings

| ID | File | Category | Finding | Impact | Recommendation | Status |
|----|------|----------|---------|--------|----------------|--------|
| DA-03-01 | run_ingestion.py | Data Integrity | MD5 match_id in 10^9 space — birthday paradox collision at ~31K demos | Data overwrite on collision | Use SHA-256/64-bit or DB sequence | EVOLVED (reduced severity) |

*Resolved:* DA-16-01 (user_id filter fixed), DA-06-01 (PID liveness check added), DA-08-01 (import path fixed)

#### MEDIUM Findings

| ID | File | Category | Finding | Recommendation |
|----|------|----------|---------|----------------|
| DA-01-04 | main.py | Correctness | `self.ids.insights_list` unguarded access | Use `self.ids.get()` |
| DA-PB-01 | player_sidebar.py | Maintainability | Dynamic `setattr` for bar attributes | Define in `__init__` |
| DA-TM-01 | tactical_map.py | Correctness | Hardcoded tick rate 64 | Derive from metadata |
| DA-TM-02 | tactical_map.py | Correctness | Wall-clock time for molotov pulse | Use game tick time |
| DA-TL-01 | timeline.py | Performance | All events redrawn every tick | Cache positions |
| DA-WG-01 | widgets.py | Architecture | Fragile matplotlib.use("Agg") import order | Move to earliest import |
| DA-WZ-01 | wizard_screen.py | Security | Unsanitized path from text field used in makedirs | Validate path boundaries (EVOLVED — partial fix) |
| DA-WZ-02 | wizard_screen.py | Correctness | Locale-dependent exception string matching | Use isinstance() |
| DA-02-01 | run_build.py | Correctness | Hardcoded JAVA_HOME overwrite | Check before overwriting |
| DA-04-02 | run_worker.py | Architecture | Shared stop signal with HLTV service | Use independent files |
| DA-07-01 | console.py | Correctness | Fragile sqlite:/// string manipulation | Use urlparse |
| DA-16-02 | new_user_flow.py | Architecture | Factory creates new instance, defeating cache | Use singleton |

*Resolved:* DA-KV-01, DA-01-03, DA-DV-01, DA-MD-01, DA-MH-01, DA-PS-01, DA-TV-01, DA-TVM-01, DA-03-02 (now LRU)

#### LOW Findings

65 LOW findings across all files (see per-file analysis above).

### Findings by Category

| Category | CRIT | HIGH | MED | LOW | INFO | Total |
|----------|------|------|-----|-----|------|-------|
| Correctness | 0 | 1 | 10 | 22 | 0 | 33 |
| Security | 0 | 0 | 2 | 3 | 0 | 5 |
| Performance | 0 | 0 | 1 | 5 | 0 | 6 |
| Architecture | 0 | 0 | 3 | 8 | 0 | 11 |
| Reliability | 0 | 2 | 0 | 2 | 0 | 4 |
| Data Integrity | 0 | 1 | 1 | 1 | 0 | 3 |
| UX | 0 | 0 | 2 | 5 | 0 | 7 |
| Concurrency | 0 | 0 | 1 | 4 | 0 | 5 |
| Maintainability | 0 | 0 | 1 | 15 | 0 | 16 |
| **Total** | **0** | **4** | **21** | **65** | **12** | **102** |

### Findings Trend (vs Prior Audits)

| Phase | Items Fixed | Items Still Open |
|-------|-----------|------------------|
| Phase 7 (Desktop App+Entry Points) | 42 | 0 |
| F7-14 (widget pool cleanup) | 1 | 0 (verified) |
| F7-18 (i18n match history title) | 1 | 0 (verified) |
| F7-21 (name texture cache) | 1 | 0 (verified) |
| F7-22 (world-to-screen scaling) | 1 | 0 (verified) |
| F7-25 (scan cancellation) | 1 | 0 (verified) |
| F7-27 (stale callback guard) | 1 | 0 (verified) |
| F7-29 (child process cleanup) | 1 | 0 (verified) |
| F7-33 (touch position clamp) | 1 | 0 (verified) |
| F7-36 (radar chart guard) | 1 | 0 (verified) |
| F7-39 (crossfade GPU budget) | 1 | 0 (documented) |
| P4-07 (accessibility) | 1 | 0 (verified) |
| **New findings this audit** | — | **4 HIGH, 21 MEDIUM, 65 LOW** |

---

## 9. RECOMMENDATIONS

### Immediate Actions (HIGH severity)

1. **Fix onboarding query in `new_user_flow.py`** — Add `WHERE player_name = user_id` to count only the user's demos, not all PlayerMatchStats. (Complexity: LOW)

2. **Fix match ID generation in `run_ingestion.py`** — Replace MD5-based truncation with SHA-256 to 64-bit space or use a monotonic database sequence. (Complexity: MEDIUM)

3. **Fix stale PID handling in `hltv_sync_service.py`** — Before rejecting start, check if PID is alive via `os.kill(pid, 0)`. Delete stale PID files. (Complexity: LOW)

4. **Verify training_orchestrator.py exists** — Confirm whether `training_orchestrator.py.backup` is the intended import target. Update import path if needed. (Complexity: LOW)

### Short-Term Actions (MEDIUM severity)

5. **Add password masking to API key fields in `layout.kv`** — Use `password=True` on Steam and FaceIT key text fields. (Complexity: LOW)

6. **Handle empty data states in screens** — `match_history_screen.py` and `performance_screen.py` should show "No data" message instead of staying in loading state. (Complexity: LOW)

7. **Decouple stop signal files** — `run_worker.py` and `hltv_sync_service.py` should use independent stop signal files. (Complexity: LOW)

8. **Fix exception type checking in `wizard_screen.py`** — Replace string matching with `isinstance(e, PermissionError)`. (Complexity: LOW)

9. **Fix wall-clock molotov animation in `tactical_map.py`** — Use game tick time instead of `time.time()` for playback-speed-aware animation. (Complexity: MEDIUM)

10. **Add `is_ghost` field to `InterpolatedPlayerState` dataclass** — Eliminates runtime TypeError risk in tactical viewmodels. (Complexity: LOW)

### Long-Term Actions (Strategic)

11. **Lazy screen loading** — Replace eager instantiation of all 12 screens with on-demand creation. Improves startup time. (Complexity: HIGH)

12. **Extract shared utilities** — Map name extraction regex, section card builder, health threshold constants — currently duplicated across files. (Complexity: MEDIUM)

13. **Unify entry points** — Deprecate `Train_ML_Cycle.py` in favor of `run_full_training_cycle.py`. Consider merging all entry points into console subcommands. (Complexity: MEDIUM)

---

## APPENDIX A: COMPLETE FILE INVENTORY

| # | File Path | LOC | Classes | Functions | Findings (H/M/L) |
|---|-----------|-----|---------|-----------|-------------------|
| 1 | apps/desktop_app/__init__.py | 1 | 0 | 0 | 0/0/0 |
| 2 | apps/desktop_app/coaching_chat_vm.py | 138 | 1 | 8 | 0/0/2 |
| 3 | apps/desktop_app/data_viewmodels.py | 275 | 3 | 14 | 0/1/2 |
| 4 | apps/desktop_app/ghost_pixel.py | 140 | 1 | 6 | 0/0/2 |
| 5 | apps/desktop_app/help_screen.py | 79 | 1 | 5 | 0/0/1 |
| 6 | apps/desktop_app/match_detail_screen.py | 451 | 1 | 16 | 0/1/3 |
| 7 | apps/desktop_app/match_history_screen.py | 162 | 1 | 8 | 0/1/2 |
| 8 | apps/desktop_app/performance_screen.py | 320 | 1 | 12 | 0/1/2 |
| 9 | apps/desktop_app/player_sidebar.py | 362 | 2 | 16 | 0/1/3 |
| 10 | apps/desktop_app/tactical_map.py | 561 | 1 | 22 | 0/2/3 |
| 11 | apps/desktop_app/tactical_viewer_screen.py | 293 | 1 | 18 | 0/1/3 |
| 12 | apps/desktop_app/tactical_viewmodels.py | 346 | 3 | 18 | 0/1/3 |
| 13 | apps/desktop_app/timeline.py | 113 | 1 | 6 | 0/1/3 |
| 14 | apps/desktop_app/widgets.py | 273 | 7 | 14 | 0/1/2 |
| 15 | apps/desktop_app/wizard_screen.py | 390 | 1 | 18 | 0/2/4 |
| 16 | apps/desktop_app/theme.py | 32 | 0 | 2 | 0/0/1 |
| 17 | apps/desktop_app/layout.kv | 1,582 | 6 | — | 0/2/3 |
| 18 | apps/spatial_debugger.py | 153 | 1 | 8 | 0/0/3 |
| 19 | main.py | 1,938 | 1 | 68 | 0/2/5 |
| 20 | run_build.py | 33 | 0 | 1 | 0/3/0 |
| 21 | run_ingestion.py | 1,181 | 0 | 12 | 1/2/2 |
| 22 | run_worker.py | 149 | 0 | 3 | 0/2/1 |
| 23 | Train_ML_Cycle.py | 23 | 0 | 1 | 0/0/2 |
| 24 | hltv_sync_service.py | 180 | 0 | 4 | 1/1/1 |
| 25 | console.py | 1,649 | 4 | 42 | 0/2/2 |
| 26 | run_full_training_cycle.py | 116 | 0 | 2 | 1/1/2 |
| 27 | reporting/report_generator.py | 87 | 1 | 4 | 0/2/2 |
| 28 | reporting/visualizer.py | 358 | 1 | 8 | 0/2/2 |
| 29 | observability/__init__.py | 1 | 0 | 0 | 0/0/0 |
| 30 | observability/logger_setup.py | 88 | 0 | 2 | 0/0/1 |
| 31 | observability/rasp.py | 138 | 0 | 3 | 0/0/1 |
| 32 | observability/sentry_setup.py | 153 | 0 | 2 | 0/0/0 |
| 33 | backend/onboarding/new_user_flow.py | 131 | 3 | 6 | 1/1/0 |
| 34 | backend/knowledge_base/__init__.py | 1 | 0 | 0 | 0/0/0 |
| 35 | backend/knowledge_base/help_system.py | 72 | 1 | 4 | 0/1/1 |
| | **TOTALS** | **~11,877** | **38** | **~310** | **4/21/65** |

---

## APPENDIX B: GLOSSARY

| Term | Definition |
|------|-----------|
| MVVM | Model-View-ViewModel — architectural pattern separating UI from business logic |
| KV | Kivy Language — declarative UI definition format for Kivy framework |
| TUI | Text User Interface — Rich-based terminal dashboard in console.py |
| RASP | Runtime Application Self-Protection — integrity verification at startup |
| PID | Process Identifier — used for daemon lifecycle management |
| WCAG | Web Content Accessibility Guidelines — accessibility standard applied to desktop UI |
| SBERT | Sentence-BERT — embedding model used in knowledge retrieval |
| Glassmorphism | UI design trend using glass-like transparency effects (layout.kv coaching cards) |
| Widget Pooling | Optimization pattern reusing Kivy widgets across frames (player_sidebar.py) |
| Layer Separation | Rendering optimization separating static and dynamic canvas instructions |

---

## APPENDIX C: DATA FLOW DIAGRAMS

### Application Startup Flow

```
main.py __main__
    │
    ├── multiprocessing.freeze_support() (PyInstaller)
    ├── RASP integrity audit (rasp.py)
    ├── Console boot (console.py singleton)
    │       ├── DB migration check
    │       └── Daemon status poll
    ├── CS2AnalyzerApp().run()
    │       ├── load_kv("layout.kv")
    │       ├── Screen instantiation (12 screens)
    │       ├── Theme application
    │       ├── Wizard check (new_user_flow.py)
    │       └── Main loop (Kivy event loop)
    └── [Optional] --hltv-service → hltv_sync_service.py
```

### Tactical Viewer Data Flow

```
PlaybackEngine (tick-by-tick)
    │
    ├── TacticalPlaybackViewModel
    │       ├── current_tick property
    │       └── seek_to_tick()
    │
    ├── TacticalMap._redraw()
    │       ├── Static layer: map texture (drawn once)
    │       ├── Static layer: heatmap (async, drawn once)
    │       └── Dynamic layer: players, nades, ghosts (per tick)
    │               ├── Player dots (alive/dead color)
    │               ├── Name textures (cached, 64-entry LRU)
    │               ├── Nade trajectories (BezierCurve/Line)
    │               ├── Detonation overlays (circle radius)
    │               └── Ghost predictions (purple dots)
    │
    ├── PlayerSidebar.update_players()
    │       └── Widget pool: reuse LivePlayerCard by player_id
    │
    ├── TimelineScrubber._redraw()
    │       └── Event markers: kills (red), plants (yellow), defuses (blue)
    │
    └── TacticalGhostViewModel
            └── ghost_engine.predict_position() per alive player
```

### Entry Point Ecosystem

```
┌─────────────────────────────────────────────────┐
│                   console.py                     │
│  (Unified TUI/CLI — subsumes all below)          │
│  Commands: ml start, ingest start, hltv start    │
└──────────────────────┬──────────────────────────┘
                       │ delegates to
    ┌──────────────────┼──────────────────────┐
    │                  │                      │
    ▼                  ▼                      ▼
main.py          run_ingestion.py      hltv_sync_service.py
(GUI app)        (demo ingestion)      (HLTV scraper daemon)
                       │
                       ▼
                 run_worker.py
                 (background worker)
    ┌──────────────────┐
    │                  │
    ▼                  ▼
Train_ML_Cycle.py   run_full_training_cycle.py
(minimal wrapper)   (full training with TensorBoard)
```

---

*End of Report 7/8*
