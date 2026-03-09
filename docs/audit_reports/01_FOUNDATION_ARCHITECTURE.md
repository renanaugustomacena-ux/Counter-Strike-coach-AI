# Foundation Architecture, Configuration Governance, and Platform Infrastructure
# Macena CS2 Analyzer — Technical Audit Report 1/8

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| Report ID | AUDIT-2026-01 |
| Date | 2026-03-08 |
| Version | 1.0 |
| Classification | Internal — Engineering Review |
| Auditor | Engineering Audit Protocol v3 |
| Scope | 77 files across core framework, observability, CI/CD, build/packaging, and configuration governance |
| Total LOC Audited | 6,570 (3,440 Python + 3,130 config/build/docs) |
| Audit Standard | ISO/IEC 25010 (Software Quality), ISO/IEC 27001 (Security), OWASP Top 10, IEEE 730 (SQA), CLAUDE.md Engineering Constitution |
| Previous Audit | N/A (baseline audit) |

---

## TABLE OF CONTENTS

- [1. Executive Summary](#1-executive-summary)
  - [1.1 Domain Health Assessment](#11-domain-health-assessment)
  - [1.2 Critical Findings Summary](#12-critical-findings-summary)
  - [1.3 Quantitative Overview](#13-quantitative-overview)
  - [1.4 Risk Heatmap](#14-risk-heatmap)
- [2. Audit Methodology](#2-audit-methodology)
  - [2.1 Standards Applied](#21-standards-applied)
  - [2.2 Analysis Techniques](#22-analysis-techniques)
  - [2.3 Severity Classification](#23-severity-classification)
  - [2.4 Cross-Reference Protocol](#24-cross-reference-protocol)
- [3. Core Framework Analysis](#3-core-framework-analysis)
  - [3.1 Package Initialization and Version Management](#31-package-initialization-and-version-management)
  - [3.2 Configuration Hierarchy](#32-configuration-hierarchy)
  - [3.3 Type System and Domain Primitives](#33-type-system-and-domain-primitives)
  - [3.4 Tri-Daemon Architecture](#34-tri-daemon-architecture)
  - [3.5 Application Lifecycle Management](#35-application-lifecycle-management)
  - [3.6 Spatial Coordinate System](#36-spatial-coordinate-system)
  - [3.7 Game State Data Models](#37-game-state-data-models)
  - [3.8 Playback State Machine](#38-playback-state-machine)
  - [3.9 Asset Management System](#39-asset-management-system)
  - [3.10 Screen Registry](#310-screen-registry)
  - [3.11 Internationalization System](#311-internationalization-system)
  - [3.12 Platform Utilities](#312-platform-utilities)
  - [3.13 PyInstaller Frozen Hook](#313-pyinstaller-frozen-hook)
  - [3.14 Deprecated Logger Shim](#314-deprecated-logger-shim)
  - [3.15 Hopfield Network Layer](#315-hopfield-network-layer)
- [4. Observability Infrastructure](#4-observability-infrastructure)
  - [4.1 Logging Infrastructure](#41-logging-infrastructure)
  - [4.2 Runtime Application Self-Protection](#42-runtime-application-self-protection)
  - [4.3 Sentry Error Reporting](#43-sentry-error-reporting)
- [5. Configuration and Dependency Management](#5-configuration-and-dependency-management)
  - [5.1 Python Packaging Configuration](#51-python-packaging-configuration)
  - [5.2 Dependency Management Strategy](#52-dependency-management-strategy)
  - [5.3 Test Configuration](#53-test-configuration)
  - [5.4 Pre-Commit Hook Infrastructure](#54-pre-commit-hook-infrastructure)
  - [5.5 Application Settings Files](#55-application-settings-files)
  - [5.6 Integrity Manifest System](#56-integrity-manifest-system)
- [6. CI/CD Pipeline Architecture](#6-cicd-pipeline-architecture)
  - [6.1 Core Build Pipeline](#61-core-build-pipeline)
  - [6.2 Gemini AI Integration Workflows](#62-gemini-ai-integration-workflows)
- [7. Build and Packaging Infrastructure](#7-build-and-packaging-infrastructure)
  - [7.1 Build Automation Scripts](#71-build-automation-scripts)
  - [7.2 Windows Installer Configuration](#72-windows-installer-configuration)
  - [7.3 Docker Composition](#73-docker-composition)
- [8. Internationalization Data Files](#8-internationalization-data-files)
- [9. Version Control Configuration](#9-version-control-configuration)
- [10. Consolidated Findings Matrix](#10-consolidated-findings-matrix)
- [11. Recommendations](#11-recommendations)
- [Appendix A: Complete File Inventory](#appendix-a-complete-file-inventory)
- [Appendix B: Glossary](#appendix-b-glossary)
- [Appendix C: Cross-Reference Index](#appendix-c-cross-reference-index)
- [Appendix D: Dependency Graph](#appendix-d-dependency-graph)
- [Appendix E: Data Flow Diagrams](#appendix-e-data-flow-diagrams)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Domain Health Assessment

**Overall Rating: SOUND**

The foundation architecture of the Macena CS2 Analyzer demonstrates mature engineering across configuration management, coordinate systems, and daemon lifecycle. The codebase has undergone 12 remediation phases (368 issues fixed) and reflects careful architectural thinking — the Tri-Daemon engine, spatial coordinate pipeline, and configuration hierarchy are well-separated, thread-aware, and follow dependency inversion.

Key strengths include the breakage of circular dependencies between config and logging modules, deterministic spatial transformations with a documented Y-flip contract, and a comprehensive CI/CD pipeline with security gates. The RASP integrity guard and Sentry PII scrubbing demonstrate defense-in-depth security thinking.

Areas requiring attention include version string inconsistency across three definition sites, a Team enum defined in two incompatible formats across different modules, the lock file referencing `master.zip` for KivyMD (contradicting the pinned requirements.txt), and several config/build files referencing missing tools (`generate_manifest.py`).

### 1.2 Critical Findings Summary

| ID | Severity | File | Finding |
|----|----------|------|---------|
| ~~R1-01~~ | ~~HIGH~~ | | ~~RESOLVED — all three files now pin KivyMD to commit `d668d8b`~~ |
| R1-02 | HIGH | `demo_frame.py` / `app_types.py` | Team enum defined in two incompatible formats (string vs integer). Documented in `app_types.py` docstring but not unified. |
| R1-03 | LOW | `windows_installer.iss` | Version inconsistency: `__init__.py` and `pyproject.toml` now both say `1.0.0`, but `windows_installer.iss` still says `0.9.0`. |
| R1-04 | MEDIUM | `scripts/build_production.bat` | References `tools/generate_manifest.py` which does not exist |
| ~~R1-05~~ | ~~MEDIUM~~ | | ~~RESOLVED — now configurable via `get_setting("ZOMBIE_TASK_THRESHOLD_SECONDS")`~~ |
| R1-06 | LOW | `hflayers.py` | Extracted to named constant `HOPFIELD_MEMORY_SLOTS = 512` with comment. No longer a magic number. Could still be a constructor parameter. |
| R1-07 | LOW | `Programma_CS2_RENAN/requirements.txt` | `master.zip` and PDF packages fixed. Minor sync issues remain (tensorboard still listed, missing some root deps). |

### 1.3 Quantitative Overview

| Metric | Value |
|--------|-------|
| Files Audited | 77 |
| Total Lines of Code | 6,570 |
| Python LOC | 3,440 |
| Config/Build/Docs LOC | 3,130 |
| Classes Analyzed | 18 |
| Functions/Methods Analyzed | 89 |
| Findings: CRITICAL | 0 |
| Findings: HIGH | 1 (was 2; R1-01 resolved) |
| Findings: MEDIUM | 3 (was 9; R1-05 resolved, R1-03/R1-06/R1-07 downgraded to LOW) |
| Findings: LOW | 11 (was 8; +3 downgraded, R1-08 resolved) |
| Findings: INFO | 7 |
| Remediation Items Previously Fixed | 42 (Phases 6, 7, 8, 10) |
| Remaining Deferred Items | 0 |

### 1.4 Risk Heatmap

```
                    IMPACT
              Low    Medium    High    Critical
         ┌─────────┬─────────┬─────────┬─────────┐
  High   │         │         │         │         │
L        │         │         │         │         │
I  Med   │  R1-10  │  R1-04  │  R1-02  │         │
K        │  R1-14  │  R1-11  │         │         │
E  Low   │  R1-09  │  R1-03  │         │         │
L        │  R1-13  │  R1-06  │         │         │
I  VLow  │ INFO x7 │  R1-07  │  R1-12  │         │
H        │         │         │         │         │
         └─────────┴─────────┴─────────┴─────────┘
  3 findings resolved: R1-01, R1-05, R1-08
```

---

## 2. AUDIT METHODOLOGY

### 2.1 Standards Applied

- **ISO/IEC 25010** — Software product quality model: functionality, reliability, usability, efficiency, maintainability, portability, security, compatibility
- **ISO/IEC 27001** — Information security management: access controls, cryptographic controls, operational security
- **OWASP Top 10 2021** — Web/application security risks: injection, broken access control, security misconfiguration, vulnerable components
- **IEEE 730** — Software quality assurance: configuration management, verification, validation
- **CLAUDE.md Constitution** — Project-specific engineering rules (Rules 1-7, Dev Rules 1-11)
- **STRIDE** — Threat modeling methodology: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege

### 2.2 Analysis Techniques

- **Static Analysis**: Line-by-line code review of all 24 Python source files and 53 configuration files
- **Architectural Analysis**: Import graph construction, component coupling assessment, dependency direction verification
- **Data Flow Analysis**: Configuration propagation from `settings.json` → `config.py` → consumers
- **Control Flow Analysis**: Daemon state machines, playback engine state transitions, lifecycle management
- **Concurrency Analysis**: Thread safety of `_settings_lock`, daemon shutdown events, registry access patterns
- **Security Analysis**: STRIDE threat model against RASP guard, Sentry PII scrubbing, secret management via keyring
- **Performance Analysis**: Spatial computation complexity, asset loading patterns, i18n key lookup
- **Correctness Analysis**: Coordinate transform invariants (world ↔ radar ↔ pixel), version consistency, enum compatibility

### 2.3 Severity Classification

| Severity | Definition | SLA |
|----------|------------|-----|
| CRITICAL | System failure, data loss, security breach, or correctness violation affecting core functionality. Production blocking. | Immediate fix required |
| HIGH | Significant functional impact, performance degradation >50%, security weakness exploitable under realistic conditions, or maintainability debt creating cascading risk. | Fix within current sprint |
| MEDIUM | Moderate impact on reliability, performance, or maintainability. Does not block core functionality but degrades system quality. | Fix within next 2 sprints |
| LOW | Minor code quality issues, style inconsistencies, documentation gaps, or optimization opportunities with <10% impact. | Fix during next refactoring cycle |
| INFO | Observations, positive findings, architectural notes, or suggestions for future consideration. No action required. | No SLA — informational |

### 2.4 Cross-Reference Protocol

Findings are cross-referenced to:
- **Remediation phases**: F-codes (F1-01 through F12-18), G-codes (G-01 through G-09)
- **Pipeline audit**: C-codes (C-01 through C-09) from `PIPELINE_AUDIT_REPORT.md`
- **CLAUDE.md rules**: Rules 1-7, Dev Rules 1-11
- **Prior audit report**: Top 30 findings from `AUDIT_REPORT.md`

---

## 3. CORE FRAMEWORK ANALYSIS

### 3.1 `Programma_CS2_RENAN/__init__.py` — Package version declaration

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 2 |
| Classes | 0 |
| Functions/Methods | 0 |
| Import Count | 0 |

**Architecture & Design:**
Single-line package initializer declaring `__version__ = "1.0.0"`. This serves as the canonical Python-importable version, consumed by Sentry setup (`sentry_setup.py` line 101) and potentially by build tools.

**Correctness Analysis:**
The version `1.0.0` contradicts `pyproject.toml` (`0.9.0`) and `windows_installer.iss` (`0.9.0`). Only one site should be authoritative.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-03 | LOW | Configuration | `__init__.py` and `pyproject.toml` now both declare `1.0.0`. Only `windows_installer.iss` still says `0.9.0`. | Update `windows_installer.iss` to `1.0.0`. |

**Positive Observations:**
- Minimal init file — no side effects at import time.

---

### 3.2 `core/config.py` — Central configuration hierarchy

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 356 |
| Classes | 0 |
| Functions/Methods | 15 |
| Cyclomatic Complexity (max) | 6 (`_resolve_brain_data_root`) |
| Import Count | 11 |

**Architecture & Design:**
Central configuration module establishing the project's entire path hierarchy. Implements a layered configuration strategy:
1. **Environment detection**: PyInstaller frozen vs development mode
2. **Path stabilization**: `SOURCE_ROOT`, `PROJECT_ROOT`, `BRAIN_DATA_ROOT`
3. **Database URL construction**: Three separate database paths (core, HLTV, knowledge)
4. **Settings management**: JSON-based user settings with thread-safe RLock
5. **Secret management**: Keyring-based credential storage with graceful degradation

The circular dependency with `logger_setup.py` is cleanly broken: config imports `get_logger` from observability, then calls `configure_log_dir(LOG_DIR)` to feed the resolved log directory back.

**Correctness Analysis:**
- `_resolve_brain_data_root()` correctly handles the critical path architecture: core DB stays in project folder, only regeneratable data goes to `BRAIN_DATA_ROOT`.
- Thread safety via `_settings_lock = threading.RLock()` protects `load_user_settings()` and `save_user_setting()`.
- `get_secret()` / `set_secret()` use keyring with fallback to environment variables and finally None — graceful degradation chain.
- Default `DATABASE_URL` construction uses `sqlite:///` prefix with path joining — correct for SQLAlchemy.

**Security Analysis:**
- Secrets stored via `keyring` — OS-level credential storage (Windows Credential Manager, macOS Keychain, Linux Secret Service). This is best practice.
- No secrets are logged. `get_secret()` returns `Optional[str]` without logging the value.
- `SENTRY_DSN` retrieval uses the double-opt-in pattern (must be explicitly enabled).

**Concurrency & Thread Safety:**
- `_settings_lock = threading.RLock()` — reentrant lock allows nested calls within same thread. Correct choice for settings that might be read during a write callback.
- Settings file I/O is atomic: reads and writes are protected by the lock.

**Performance & Efficiency:**
- Settings loaded from JSON on every `load_user_settings()` call — no caching layer. For the current usage pattern (UI-triggered reads), this is acceptable.
- Path resolution at module import time — one-time cost, no runtime overhead.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| ~~R1-08~~ | ~~LOW~~ | ~~Maintainability~~ | ~~RESOLVED: `_resolve_brain_data_root()` was refactored into inline logic with clear comments documenting the BRAIN_DATA_ROOT → CUSTOM_STORAGE_PATH → BASE_DIR resolution chain.~~ | ~~Done~~ |

**Positive Observations:**
- Excellent circular dependency resolution with `configure_log_dir()`.
- Critical path architecture well-documented in comments: "Core DB stays in project folder."
- Thread-safe settings with RLock.
- Keyring-based secret management is industry best practice.
- Clean separation: no UI code, no ML code, no database queries.

---

### 3.3 `core/constants.py` — Game constants and temporal parameters

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 34 |
| Classes | 0 |
| Functions/Methods | 0 |
| Import Count | 0 |

**Architecture & Design:**
Pure constants module with zero dependencies. Defines CS2 game constants as named values:
- `TICK_RATE = 64` — CS2 server tick rate
- `FOV_DEGREES = 90.0` — Player field-of-view
- `Z_FLOOR_THRESHOLD = 200.0` — Map level discrimination
- Temporal constants in seconds with derived tick values computed at module load: `SMOKE_DURATION_S = 18.0`, `MOLOTOV_DURATION_S = 7.0`, `TRADE_WINDOW_S = 3.0`, `MEMORY_DECAY_TAU_S = 2.5`

**Correctness Analysis:**
- All game constants match official CS2 values (verified against Valve documentation).
- Derived tick values computed from seconds × `TICK_RATE` — correct dimensional analysis.
- `TRADE_WINDOW_S = 3.0` is a tunable parameter that could reasonably vary between 2-5 seconds; current value aligns with community consensus.

**Compliance with CLAUDE.md:**
- Dev Rule 4: No magic numbers — all values are named constants. Exemplary compliance.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-15 | INFO | Architecture | Constants module has zero dependencies — pure leaf node in import graph. This is ideal. | None — exemplary design. |

**Positive Observations:**
- Zero imports — absolute leaf node in the dependency graph.
- All temporal constants maintain dual representation (seconds + ticks) ensuring dimensional consistency.
- Dev Rule 4 fully satisfied: no magic numbers anywhere in this module.

---

### 3.4 `core/app_types.py` — Type system and domain primitives

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 77 |
| Classes | 4 (Team, PlayerRole, IngestionStatus enums + 2 TypedDicts) |
| Functions/Methods | 0 |
| Import Count | 4 |

**Architecture & Design:**
Defines the project's core type vocabulary:
- **NewType aliases**: `MatchID = NewType("MatchID", str)`, `Tick = NewType("Tick", int)`, `PlayerID = NewType("PlayerID", int)`
- **Team enum**: `SPECTATOR = 0`, `T = 1`, `CT = 2` (integer-valued)
- **PlayerRole enum**: 7 string-valued roles (ENTRY_FRAGGER, AWP, LURKER, IGL, SUPPORT, ANCHOR, FLEX)
- **IngestionStatus enum**: 4 states (PENDING, PROCESSING, COMPLETED, FAILED)
- **TypedDicts**: `DemoMetadata`, `PlayerStats`

**Correctness Analysis:**
The `Team` enum uses integer values (0, 1, 2), but `demo_frame.py` defines a separate `Team` type with string values ("ct", "t"). This dual representation creates a mapping hazard at boundaries where both modules interact.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-02 | HIGH | Correctness | `Team` enum in `app_types.py` uses integer values (0, 1, 2) while `demo_frame.py` uses string values ("ct", "t"). Consumers must know which `Team` they're handling. Cross-boundary misuse would cause silent incorrect comparisons. | Unify to a single canonical `Team` definition. If both representations are needed, add explicit conversion methods. |

**Positive Observations:**
- `NewType` aliases provide type-level distinction between MatchID (str), Tick (int), and PlayerID (int) — prevents accidental argument swapping.
- `PlayerRole` as a `str` enum enables both comparison and serialization naturally.
- Clean separation of concerns — no business logic, pure type definitions.

---

### 3.5 `core/session_engine.py` — Tri-Daemon architecture

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 464 |
| Classes | 0 (module-level functions) |
| Functions/Methods | 12 |
| Cyclomatic Complexity (max) | 8 (`_scanner_daemon_loop`) |
| Import Count | 16 |

**Architecture & Design:**
The crown jewel of the backend orchestration. Implements the Tri-Daemon Engine as four daemon threads coordinated through `threading.Event` objects:

1. **Scanner (Hunter)**: `_scanner_daemon_loop()` — Discovers new demo files, validates, creates ingestion tasks
2. **Digester**: `_digester_daemon_loop()` — Processes ingestion queue, runs demo parser, stores results
3. **Teacher**: `_teacher_daemon_loop()` — Triggers ML training cycles, belief calibration (G-07 fix)
4. **Pulse**: `_pulse_daemon_loop()` — Heartbeat monitoring, zombie task cleanup, meta-shift detection

**Concurrency & Thread Safety:**
- `_shutdown_event = threading.Event()` — clean shutdown signaling across all daemons
- `_work_available_event = threading.Event()` — efficient wake-up mechanism (no busy-waiting)
- Zombie task cleanup with `_ZOMBIE_THRESHOLD_SECONDS = 300` — correctly resets stale PROCESSING tasks
- Parent death detection via stdin pipe closure — robust cross-process lifecycle management
- All database access through SQLAlchemy sessions (one per daemon loop iteration) — no shared session state

**Correctness Analysis:**
- G-07 fix verified: Teacher daemon calls `belief_model.auto_calibrate()` after each retraining cycle
- Meta-shift detection (Proposal 11) uses `TemporalBaselineDecay` — statistically sound approach
- Each daemon loop has proper exception handling with `continue` to prevent single-error cascade
- `time.sleep()` intervals are reasonable: Scanner 30s, Digester 10s, Teacher 60s, Pulse 120s

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| ~~R1-05~~ | ~~MEDIUM~~ | ~~Maintainability~~ | ~~RESOLVED: Now configurable via `get_setting("ZOMBIE_TASK_THRESHOLD_SECONDS", default=300)` at line 192.~~ | ~~Done~~ |
| R1-16 | INFO | Architecture | The Tri-Daemon + Pulse pattern is an elegant event-driven architecture that avoids complex locking by giving each daemon its own session scope. | None — exemplary design pattern. |

**Positive Observations:**
- Event-driven coordination avoids busy-waiting and complex lock hierarchies.
- Each daemon owns its own DB session — no cross-thread session sharing.
- Parent death detection via stdin pipe is a robust IPC pattern.
- G-07 belief calibration correctly wired into Teacher daemon.
- Clean shutdown: `_shutdown_event.set()` propagates to all daemons simultaneously.

---

### 3.6 `core/lifecycle.py` — Application lifecycle management

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 145 |
| Classes | 1 (AppLifecycleManager) |
| Functions/Methods | 8 |
| Import Count | 9 |

**Architecture & Design:**
Manages single-instance enforcement and daemon subprocess lifecycle:
- **Single-instance**: Windows Named Mutex via ctypes (non-blocking trylock)
- **Daemon management**: Launches `session_engine` as subprocess with stdin pipe for IPC
- **Cleanup**: Proper resource release (file handles, mutex, process termination with timeout)

**Correctness Analysis:**
- Named Mutex uses `CreateMutexW` with `ERROR_ALREADY_EXISTS` check — correct Win32 API usage.
- Process termination follows escalation: `terminate()` → `wait(timeout=5)` → `kill()` — robust.
- F7-29 fix verified: `atexit` handler and signal handler registered for cleanup.

**Security Analysis:**
- Mutex name `Macena_CS2_Analyzer_Instance` is application-specific — no risk of collision.
- No elevation of privilege concerns — mutex operates at user level.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-09 | LOW | Portability | Single-instance enforcement uses Windows Named Mutex. On Linux/macOS, falls back to no enforcement. | Consider file-based locking (fcntl.flock) for cross-platform single-instance support if Linux deployment is planned. |

**Positive Observations:**
- Process termination escalation pattern (terminate → wait → kill) is production-grade.
- Clean `atexit` registration ensures cleanup even on unexpected exits.
- Stdin pipe IPC for parent-death detection is elegant and reliable.

---

### 3.7 `core/spatial_data.py` — Map metadata and spatial configuration

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 387 |
| Classes | 2 (MapMetadata frozen dataclass, SpatialConfigLoader singleton) |
| Functions/Methods | 14 |
| Import Count | 8 |

**Architecture & Design:**
Manages spatial coordinate metadata for all CS2 competitive maps. Key components:
- `MapMetadata` frozen dataclass: `pos_x`, `pos_y`, `scale`, `z_cutoff`, `level`
- `SpatialConfigLoader` singleton with **double-checked locking** for thread-safe initialization
- Multi-level map support: Nuke (`z_cutoff=-495`), Vertigo (`z_cutoff=11700`)
- `world_to_radar()` / `radar_to_world()` coordinate transforms
- `compute_z_penalty()` for neural network supervision — penalizes predictions on wrong map level

**Correctness Analysis:**
- Y-flip contract documented: Y-flip handled at rendering layer (`TacticalMap`), not in engine — this avoids the C-03 double Y-flip bug.
- `world_to_radar()` formula: `(world_x - pos_x) / scale` — mathematically correct for CS2's coordinate system.
- `compute_z_penalty()` returns smooth penalty via `tanh` — differentiable for gradient-based training.
- C-07 fix verified: position values clamped to valid map bounds.

**Concurrency & Thread Safety:**
- Double-checked locking on `SpatialConfigLoader._instance` with `threading.Lock()` — correct singleton pattern for multi-threaded environments.
- Module-level `__getattr__` provides lazy loading of `SPATIAL_REGISTRY`, `LANDMARKS`, `COMPETITIVE_MAPS` — thread-safe because Python's import lock serializes first access.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-17 | INFO | Architecture | `__getattr__` lazy loading at module level is an advanced Python pattern that works correctly but may surprise developers unfamiliar with module-level attribute access hooks. | Add a brief comment explaining the lazy-loading mechanism. |

**Positive Observations:**
- Frozen dataclass for `MapMetadata` — immutable after construction, thread-safe by design.
- Double-checked locking is textbook-correct singleton initialization.
- `compute_z_penalty()` smooth penalty function is differentiable — correct for gradient-based optimization.
- Y-flip contract clearly documented and correctly delegated to rendering layer.

---

### 3.8 `core/spatial_engine.py` — Coordinate transformations

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 92 |
| Classes | 1 (SpatialEngine) |
| Functions/Methods | 6 |
| Import Count | 2 |

**Architecture & Design:**
Provides bidirectional coordinate transformations:
- `world_to_normalized()` → `normalized_to_pixel()` → pixel coordinates
- `pixel_to_normalized()` → `normalized_to_world()` → world coordinates
- Y-flip documented: handled at rendering layer, not here

**Correctness Analysis:**
- All transforms are pure functions (no side effects, no state mutation).
- Inverse transforms verified: `world_to_normalized` → `normalized_to_world` produces identity within floating-point precision.
- Division-by-zero protection: `scale` parameter comes from `MapMetadata` which is validated at load time.

**Positive Observations:**
- Pure functions with no side effects — mathematically verifiable.
- Separation from rendering concerns (Y-flip handled elsewhere) prevents C-03 double-flip.

---

### 3.9 `core/demo_frame.py` — Game state data models

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 151 |
| Classes | 7 (DemoFrame, PlayerState, GhostState, NadeState, BombState, KillEvent, GameEvent) |
| Functions/Methods | 0 |
| Import Count | 3 |

**Architecture & Design:**
Defines tick-level game state as a hierarchy of dataclasses:
- `DemoFrame`: Top-level container (tick, map_name, players, grenades, bomb, kills, events)
- `PlayerState`: Position (x, y, z), angles (yaw, pitch), health, armor, team, weapons
- `NadeState`: **Frozen** dataclass — immutable after creation (correct, grenades don't change mid-flight)
- `GhostState`: AI-predicted player position for visualization

**Correctness Analysis:**
- `NadeState` is correctly frozen — grenades are immutable events.
- `Team` in this module uses string values ("ct", "t") — conflicts with `app_types.Team` (integer values).

**Findings:**

Referenced in R1-02 (HIGH) — Team enum dual definition.

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-10 | LOW | Maintainability | `DemoFrame` contains 8 fields with complex nested types. No `__slots__` optimization despite high instantiation rate (one per tick). | Consider `__slots__` for memory optimization if profiling shows allocation pressure. |

**Positive Observations:**
- `NadeState` as frozen dataclass is the correct choice — grenades are events, not mutable state.
- Clean dataclass hierarchy with no business logic — pure data containers.

---

### 3.10 `core/playback_engine.py` / `core/playback.py` — Playback state machine

**File Metrics (combined):**
| Metric | Value |
|--------|-------|
| Lines of Code | 361 (246 + 115) |
| Classes | 2 (PlaybackEngine, TimelineController) |
| Functions/Methods | 22 |
| Import Count | 7 |

**Architecture & Design:**
Two-layer playback system:
- `PlaybackEngine`: Low-level tick management, frame interpolation, binary search seek (`bisect.bisect_left`)
- `TimelineController(EventDispatcher)`: Kivy-aware controller with observable properties (`current_tick`, `is_playing`, `playback_speed`)

**Correctness Analysis:**
- `_interpolate_angle()` correctly handles 360° wraparound using delta normalization to [-180, 180].
- Binary search via `bisect_left` for seek — O(log n) complexity, correct for sorted frame lists.
- Kivy `Clock.schedule_interval` at 60 FPS for smooth playback — appropriate for desktop rendering.
- `playback_speed` range clamped to [0.25, 4.0] — prevents degenerate cases.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-18 | INFO | Performance | Binary search seek via `bisect_left` is O(log n) — optimal for sorted frame data. | None — correct algorithm choice. |

**Positive Observations:**
- Angle interpolation correctly handles the 360° boundary — a common source of subtle bugs.
- Speed clamping prevents degenerate playback rates.
- Clean MVC separation: PlaybackEngine (model) vs TimelineController (controller).

---

### 3.11 `core/asset_manager.py` / `core/map_manager.py` — Asset management system

**File Metrics (combined):**
| Metric | Value |
|--------|-------|
| Lines of Code | 341 (254 + 87) |
| Classes | 4 (AssetAuthority, SmartAsset, MapAssetManager deprecated shim, MapManager) |
| Functions/Methods | 18 |
| Import Count | 9 |

**Architecture & Design:**
Two-tier asset system:
- `AssetAuthority` (singleton): Unified source of truth for map visual assets. Implements lazy-loaded `SmartAsset` dataclass with Kivy texture creation. Provides checkered magenta/black 64×64 fallback texture for missing assets — debug-visible pattern.
- `MapManager`: High-level interface wrapping `AssetAuthority` with Kivy async loading via `Loader.image()`.
- `MapAssetManager`: Deprecated backward-compatibility shim (emits `DeprecationWarning`).

**Correctness Analysis:**
- Fallback texture (magenta/black checkerboard) is intentionally ugly — makes missing assets immediately visible during development. Good UX engineering.
- Theme variant support (regular, dark, light) with automatic fallback to unthemed variant.
- `load_map_async()` correctly uses Kivy's `Loader` for non-blocking texture loading — prevents UI freeze.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-19 | INFO | Architecture | Deprecated `MapAssetManager` shim exists for backward compatibility. | Track usage and remove when no consumers remain. |

**Positive Observations:**
- Magenta/black checkerboard fallback texture is an excellent debugging aid — makes missing assets impossible to miss.
- Async texture loading prevents UI freeze on map selection.
- Clean deprecation path with `DeprecationWarning`.

---

### 3.12 `core/registry.py` — Screen registry

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 42 |
| Classes | 1 (ScreenRegistry) |
| Functions/Methods | 3 |
| Import Count | 1 |

**Architecture & Design:**
KivyMD screen registration via decorator pattern. Provides `@ScreenRegistry.register("name")` for declarative screen registration.

**Correctness Analysis:**
- Registry is a module-level singleton (class with class methods) — thread-safe for registration during import.
- This is the **UI screen** registry, distinct from the ingestion registry (`ingestion/registry/registry.py`).

**Positive Observations:**
- Decorator pattern for screen registration is clean and declarative.
- Minimal code — does exactly one thing well.

---

### 3.13 `core/localization.py` — Internationalization system

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 422 |
| Classes | 0 |
| Functions/Methods | 5 |
| Import Count | 5 |

**Architecture & Design:**
Tri-lingual i18n system (English, Portuguese, Italian) with dual-source architecture:
1. **JSON files** (`assets/i18n/{en,pt,it}.json`) — priority source, user-editable
2. **Hardcoded `TRANSLATIONS` dict** — fallback for missing keys or corrupted JSON

Features `{home_dir}` placeholder expansion and graceful fallback: JSON → hardcoded → key itself.

**Correctness Analysis:**
- All three JSON files verified to have identical key sets (112 keys each) — no orphan translations.
- Fallback chain is robust: JSON parse error → hardcoded dict → raw key name.
- Thread safety: `_current_lang` is module-level but only changed during initialization — effectively immutable at runtime.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-11 | MEDIUM | Maintainability | Hardcoded `TRANSLATIONS` dict (90+ entries × 3 languages = ~270 lines) duplicates JSON files. Changes must be synchronized in two places. | Consider generating the hardcoded fallback from JSON files during build, or removing the fallback in favor of always loading from JSON. |

**Positive Observations:**
- Complete parity across all three language files — no missing translations.
- Placeholder expansion (`{home_dir}`) enables context-aware strings.
- Graceful fallback chain ensures the UI never shows raw exception text.

---

### 3.14 `core/platform_utils.py` — Platform detection

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 43 |
| Classes | 0 |
| Functions/Methods | 1 |
| Import Count | 4 |

**Architecture & Design:**
Single function `get_available_drives()` for Windows drive detection. Uses `ctypes.windll.kernel32.GetLogicalDrives()` bitmask with `psutil` fallback.

**Correctness Analysis:**
- Bitmask iteration `(1 << i)` for bits 0-25 (drives A: through Z:) — correct Win32 API usage.
- `psutil` fallback for non-Windows or ctypes failure — correct graceful degradation.
- On Linux, `psutil.disk_partitions()` returns mount points — different semantics but acceptable for the wizard's drive selection dialog.

**Positive Observations:**
- Dual-path implementation with fallback — robust cross-platform support.

---

### 3.15 `core/frozen_hook.py` — PyInstaller frozen environment hook

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 17 |
| Classes | 0 |
| Functions/Methods | 1 |
| Import Count | 3 |

**Architecture & Design:**
Called at startup when running as frozen PyInstaller binary. Performs:
1. `multiprocessing.freeze_support()` — Required for Windows multiprocessing in frozen builds
2. `os.chdir(sys._MEIPASS)` — Sets working directory to PyInstaller temp extraction folder

**Correctness Analysis:**
- Both operations are necessary and correctly ordered.
- `sys._MEIPASS` only exists in frozen context — the function is guarded by `getattr(sys, "frozen", False)`.

**Positive Observations:**
- Minimal, correct frozen-environment bootstrap.

---

### 3.16 `core/logger.py` — Deprecated logger shim

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 13 |
| Classes | 0 |
| Functions/Methods | 0 |
| Import Count | 2 |

**Architecture & Design:**
Deprecated shim that re-exports `get_logger` and `app_logger` from `observability.logger_setup`. Emits `DeprecationWarning` on import. Provides legacy alias `setup_logger = get_logger`.

**Correctness Analysis:**
- `stacklevel=2` on the warning ensures the caller's location is reported, not this module's line.
- Re-export via `from ... import ... # noqa: F401, E402` — correct suppression of linter warnings.

**Positive Observations:**
- Clean deprecation with warning and backward-compatible re-exports.

---

### 3.17 `hflayers.py` — Hopfield Network layer (first-principles implementation)

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 116 |
| Classes | 1 (Hopfield) |
| Functions/Methods | 2 |
| Import Count | 4 |

**Architecture & Design:**
First-principles implementation of the Continuous Hopfield Network (Ramsauer et al., 2020), replacing the unavailable `hflayers` library. Uses attention mechanism with learnable memory bank:
- Query projection: `nn.Linear(input_size, stored_pattern_size * num_heads)`
- Memory bank: 512 learnable key-value pairs as `nn.Parameter`
- Scaled dot-product attention with softmax
- Multi-head support via `num_heads` parameter

**Correctness Analysis:**
- Scaling factor `1.0 / sqrt(stored_pattern_size)` — correct for attention mechanisms.
- Parameter initialization `torch.randn(...) * 0.02` — small random init prevents saturation.
- 3D/2D input handling via `unsqueeze(1)` / `squeeze(1)` — correct batch dimension management.
- `einsum("bshd,bmhd->bshm", q, k)` — correct batch-multi-head attention score computation.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-06 | LOW | Configuration | `memory_slots` extracted to named constant `HOPFIELD_MEMORY_SLOTS = 512` with explanatory comment. No longer a magic number. Could still benefit from being a constructor parameter for task-specific tuning. | Consider making it a constructor parameter with 512 as default. |

**Positive Observations:**
- Mathematically sound implementation of modern Hopfield networks.
- Supports both 2D (single-step) and 3D (sequence) inputs.
- Multi-head attention follows the standard Transformer formulation.

---

## 4. OBSERVABILITY INFRASTRUCTURE

### 4.1 `observability/logger_setup.py` — Logging infrastructure

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 87 |
| Classes | 0 |
| Functions/Methods | 4 |
| Import Count | 3 |

**Architecture & Design:**
Centralized logging factory with two handlers per logger:
1. **RotatingFileHandler**: 5 MB rotation, 3 backups, UTF-8 encoding
2. **StreamHandler**: WARNING level to console

Format: `%(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s` — includes thread name for Tri-Daemon debugging.

**Correctness Analysis:**
- `configure_log_dir()` breaks circular dependency with `config.py` — config calls this function after resolving `LOG_DIR`.
- `_create_file_handler()` falls back to plain `FileHandler` on `PermissionError` — handles Windows daemon subprocess handle conflicts.
- `configure_log_level()` iterates `logging.Logger.manager.loggerDict` filtering by `cs2analyzer` prefix — correct for runtime log level changes.
- `logger.propagate = False` — prevents duplicate log entries from root logger.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-20 | INFO | Architecture | Thread name in log format (`[%(threadName)s]`) is essential for debugging Tri-Daemon issues. | None — correct design decision. |

**Positive Observations:**
- RotatingFileHandler prevents unbounded disk growth (5 MB × 4 files = 20 MB max).
- PermissionError fallback handles Windows daemon file locking gracefully.
- Thread name in format string enables Tri-Daemon debugging.
- Circular dependency cleanly resolved.

---

### 4.2 `observability/rasp.py` — Runtime Application Self-Protection

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 138 |
| Classes | 2 (IntegrityError, RASPGuard) |
| Functions/Methods | 5 |
| Import Count | 6 |

**Architecture & Design:**
SHA-256 integrity verification against a manifest of critical files. Handles both development and frozen (PyInstaller) environments with separate path resolution strategies.

**Security Analysis:**
- **Tampering (STRIDE T)**: Detects file modification via SHA-256 comparison against manifest.
- **Limitations**: The manifest itself is not signed — an attacker who can modify files can also modify the manifest. This is acceptable for the current threat model (protecting against accidental corruption, not APT-level adversaries).
- In development mode, missing manifest is treated as pass — correct for dev workflow.
- Frozen mode checks multiple candidate paths for manifest — handles different PyInstaller packaging strategies.

**Correctness Analysis:**
- SHA-256 computed in 4096-byte blocks — correct for large files.
- `check_frozen_binary()` verifies `.exe` extension on Windows — basic sanity check, not security-critical.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-12 | MEDIUM | Security | Integrity manifest is not cryptographically signed. An attacker with file write access could modify both target files and manifest simultaneously. | For production releases, consider signing the manifest with a private key and verifying the signature. Current implementation is appropriate for corruption detection. |

**Positive Observations:**
- Multi-environment path resolution handles dev, standard frozen, and flattened frozen builds.
- Clean separation between integrity check and environment check.
- 4096-byte block reads prevent memory issues on large files.

---

### 4.3 `observability/sentry_setup.py` — Sentry error reporting

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 152 |
| Classes | 0 |
| Functions/Methods | 4 |
| Import Count | 7 |

**Architecture & Design:**
Double opt-in Sentry integration:
1. Gate 1: pytest detection — disabled during tests
2. Gate 2: `enabled=True` required
3. Gate 3: Valid DSN required

PII scrubbing via `_before_send()`:
- Server name → "redacted"
- Home directory paths → `<user_home>`
- Breadcrumb data scrubbed

**Security Analysis:**
- **PII Protection (STRIDE I)**: Home paths, server names scrubbed before transmission. Complies with GDPR data minimization principle.
- `send_default_pii=False` — Sentry SDK default PII collection disabled.
- `traces_sample_rate=0.1` — 10% sampling reduces data exposure surface.
- DSN is `strip()`-ed before use — prevents whitespace-based configuration errors.

**Correctness Analysis:**
- `_initialized` flag prevents double initialization — correct idempotency.
- `add_breadcrumb()` is a no-op when `_initialized is False` — correct guard.
- Exception caught in `init_sentry()` and logged — initialization failure is non-fatal.
- `_ = e` in `add_breadcrumb()` exception handler — intentionally suppressed, documented with comment.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-21 | INFO | Security | PII scrubbing implementation is thorough — covers stacktraces, breadcrumbs, and server names. | None — exemplary privacy engineering. |

**Positive Observations:**
- Triple gate (pytest detection, enabled flag, valid DSN) is defense-in-depth.
- PII scrubbing covers all three Sentry data channels (events, breadcrumbs, server metadata).
- Non-fatal initialization — Sentry failure never crashes the application.
- `_before_send` hook is the correct Sentry pattern for pre-transmission filtering.

---

## 5. CONFIGURATION AND DEPENDENCY MANAGEMENT

### 5.1 `pyproject.toml` — Python packaging configuration

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 70 |

**Analysis:**
Well-structured packaging configuration with tool-specific sections for Black, isort, mypy, and coverage.

Key settings:
- `version = "0.9.0"` — contradicts `__init__.py` (`1.0.0`)
- `requires-python = ">=3.10"` — correct minimum for match-case, `X | Y` type hints
- `line-length = 100` aligned between Black and isort
- Coverage `fail_under = 30` with incremental roadmap documented in comments
- mypy `ignore_missing_imports = true` — pragmatic for a project with optional dependencies

**Findings:**

Referenced in R1-03 (MEDIUM) — version inconsistency.

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-13 | LOW | Configuration | mypy excludes `tests/` directory entirely. Type errors in test code go undetected. | Consider removing the `tests/` exclusion to catch type errors in test fixtures and mocks. |

**Positive Observations:**
- Coverage roadmap documented directly in config comments — transparent quality trajectory.
- Black and isort aligned on `line_length = 100` — no formatting conflicts.

---

### 5.2 Dependency Management Strategy

**Files analyzed**: `requirements.txt`, `requirements-ci.txt`, `requirements-lock.txt`, `Programma_CS2_RENAN/requirements.txt`, `bindep.txt`

**Architecture:**
Four-tier dependency strategy:
1. **`requirements.txt`** (root): Ranged pins (`>=x.y.z,<x+1.0`) for core dependencies — 18 packages
2. **`requirements-lock.txt`**: Exact pins (`==`) for reproducible builds — 157 packages, generated from Windows venv
3. **`requirements-ci.txt`**: CI overlay forcing CPU-only PyTorch via `--extra-index-url`
4. **`Programma_CS2_RENAN/requirements.txt`**: Inner requirements for the package itself — 116 lines
5. **`bindep.txt`**: Binary/system dependencies (demoparser2, ffmpeg, playwright, npm)

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| ~~R1-01~~ | ~~HIGH~~ | ~~Dependency~~ | ~~RESOLVED: All three files now pin KivyMD to commit `d668d8b`. Lock file line 69 and inner requirements line 103 both match root requirements.txt.~~ | ~~Done~~ |
| R1-07 | LOW | Dependency | `master.zip` and PDF packages fixed. `hopfield-layers` commented out with note. Minor sync issues remain: `tensorboard` still listed, missing `sentry-sdk`, `watchdog`, `faiss-cpu` from root. This inner file appears to be a legacy copy. | Determine if this inner requirements file is still needed. If so, synchronize with root. If not, remove it. |
| R1-14 | LOW | Dependency | `requirements-lock.txt` includes PDF-related packages (pdfminer, pdfplumber, pypdf, PyMuPDF) that were explicitly removed in P5-03. Lock file was generated before the cleanup. | Regenerate lock file from clean venv using only `requirements.txt`. |

**Positive Observations:**
- CI overlay for CPU-only PyTorch is elegant — single `--extra-index-url` line.
- Root `requirements.txt` uses ranged pins — balances reproducibility and flexibility.
- Binary dependencies documented in `bindep.txt`.

---

### 5.3 `pytest.ini` — Test configuration

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 46 |

**Analysis:**
Well-configured test discovery and execution:
- Dual test paths: `tests/` and `Programma_CS2_RENAN/tests/`
- `--strict-markers` — prevents typos in marker names
- Global `timeout = 30` — prevents indefinite hangs (F9-12 fix)
- 6 custom markers: `slow`, `integration`, `unit`, `portability`, `known_fail`, `flaky`
- `norecursedirs` includes `D:*` — prevents scanning external data drives (Windows)

**Positive Observations:**
- 30-second global timeout prevents CI hangs — production-grade test configuration.
- `--strict-markers` catches marker typos at test collection time.
- `D:*` exclusion is a smart portability consideration.

---

### 5.4 `.pre-commit-config.yaml` — Pre-commit hook infrastructure

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 97 |

**Analysis:**
13 hooks across 4 repositories:
- **Local hooks**: headless-validator (pre-push), dead-code-detector (pre-push), integrity-manifest-check (commit), dev-health-quick (commit)
- **Standard hooks**: trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-added-large-files (1MB), check-merge-conflict, detect-private-key
- **Python quality**: Black (line-length=100), isort (profile=black)

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-22 | INFO | CI/CD | `check-added-large-files` at 1MB threshold excludes PHOTO_GUI images and external CSVs via regex — correct for binary assets. | None — well-configured exclusion. |

**Positive Observations:**
- `detect-private-key` hook provides shift-left secret detection.
- Stage separation (commit vs pre-push) balances speed with thoroughness.
- Large file exclusion patterns are precise and well-documented.

---

### 5.5 Application Settings Files

**Files analyzed**: `settings.json`

**Analysis:**
Default settings with theme configuration and demo path:
- `theme_style: "Dark"`, `primary_palette: "BlueGray"`, `accent_palette: "Amber"`
- `DEFAULT_DEMO_PATH` points to a Windows-specific absolute path

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-23 | LOW | Portability | `DEFAULT_DEMO_PATH` in `settings.json` contains a Windows-specific absolute path (`c:\Users\Renan\Desktop\...`). This is the checked-in default. | This is acceptable as a development default since `user_settings.json` (gitignored) overrides it at runtime. Document this in the settings loading code. |

---

### 5.6 `integrity_manifest.json` — Integrity manifest system

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 23 |

**Analysis:**
Tracks SHA-256 hashes of 17 critical files:
- Core: `config.py`, `localization.py`, `registry.py`, `spatial_data.py`
- Storage: `database.py`, `db_models.py`, `match_data_manager.py`
- NN: `model.py`, `coach_manager.py`, `ghost_engine.py`
- Processing: `tensor_factory.py`, `state_reconstructor.py`, `vectorizer.py`, `dem_validator.py`
- Observability: `rasp.py`
- Entry: `main.py`, `hltv_sync_service.py`

Manifest version 2.0 with generation timestamp.

**Findings:**

Referenced by validator baseline: 296/298 PASS, with integrity manifest hash mismatch as one of the 2 non-blocking warnings.

**Positive Observations:**
- Critical file selection covers the most security-sensitive and correctness-critical modules.
- Version field enables manifest format evolution.

---

## 6. CI/CD PIPELINE ARCHITECTURE

### 6.1 `build.yml` — Core build pipeline

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 270 |

**Architecture:**
Six-stage pipeline with dependency graph:
```
lint ──→ unit-test ──→ integration ──→ build-distribution (main only)
  │
  ├──→ security (parallel with unit-test)
  └──→ type-check (parallel, informational, non-blocking)
```

Key design decisions:
- `concurrency.cancel-in-progress: true` — prevents queue buildup on rapid pushes
- Security stage runs **parallel** to unit tests — faster overall pipeline
- Type check is `continue-on-error: true` — informational only, non-blocking
- Build distribution only on `main` branch — protected release path
- `METADATA_DIM == INPUT_DIM` cross-module assertion in integration stage — ensures dimensional invariant

**Correctness Analysis:**
- Dependency chain ensures broken code cannot merge: lint → test → integration → build
- Cross-module consistency check (`METADATA_DIM == INPUT_DIM`) catches the most critical dimensional invariant at CI level
- `timeout-minutes: 2` on headless validator prevents CI hang
- `--cov-fail-under=30` enforces minimum coverage threshold

**Security Analysis:**
- Bandit security linter runs against production code (excludes tests)
- Hardcoded secret grep with `|| true` — scan is informational, not blocking
- No secrets in workflow file — all via `secrets.*` references
- `actions/checkout@v4` — pinned to major version (acceptable for GitHub-maintained actions)

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-24 | LOW | CI/CD | Bandit runs with `|| true` — security findings never block the pipeline. | Consider making Bandit blocking at `--severity-level high` to catch critical security issues. |
| R1-25 | LOW | CI/CD | Secret detection grep uses basic pattern matching. May miss encoded or obfuscated secrets. | Consider adding `trufflehog` or `gitleaks` as a more thorough secret scanner. |

**Positive Observations:**
- `METADATA_DIM == INPUT_DIM` CI check is a dimensional invariant gate — excellent engineering practice.
- Parallel security/type-check stages reduce total pipeline time.
- Build distribution gated to main branch only.

---

### 6.2 Gemini AI Integration Workflows

**Files analyzed**: `gemini-dispatch.yml`, `gemini-invoke.yml`, `gemini-review.yml`, `gemini-scheduled-triage.yml`, `gemini-triage.yml`, `gemini-invoke.toml`, `gemini-review.toml`, `gemini-scheduled-triage.toml`, `gemini-triage.toml`

**Architecture:**
Five-workflow Gemini integration for automated:
1. **Dispatch**: Event router — PR opened → review, issue opened → triage, `@gemini-cli` → invoke
2. **Review**: Automated code review on PRs with severity-rated comments
3. **Invoke**: General-purpose AI assistant with Plan → Approve → Execute → Report workflow
4. **Triage**: Issue classification and labeling
5. **Scheduled Triage**: Daily batch triage of unlabeled issues (08:00 UTC cron)

**Security Analysis:**
- **Prompt injection protection**: Triage workflows explicitly strip auth tokens (`GITHUB_TOKEN: ''`) when processing untrusted issue content — excellent security practice.
- **Label validation**: Applied labels are filtered against `availableLabels` — prevents injection of arbitrary labels.
- **Fork protection**: PR dispatch checks `head.repo.fork == false` — prevents fork-based privilege escalation.
- **Author verification**: `@gemini-cli` commands require `OWNER`, `MEMBER`, or `COLLABORATOR` association.
- Command substitution explicitly forbidden in TOML prompts — defense against shell injection.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-26 | INFO | CI/CD | Gemini integration includes comprehensive prompt injection defenses (token stripping, label validation, fork protection, author checks). | None — exemplary security posture for AI-integrated workflows. |

**Positive Observations:**
- Token stripping for untrusted input processing is defense-in-depth.
- Label injection prevention via allowlist filtering.
- Approval-gated execution workflow prevents autonomous destructive actions.
- 7-minute timeout on all Gemini workflow jobs prevents runaway AI sessions.

---

## 7. BUILD AND PACKAGING INFRASTRUCTURE

### 7.1 Build Automation Scripts

**Files analyzed**: `export_env.bat`, `setup_new_pc.bat`, `scripts/build_exe.bat`, `scripts/build_production.bat`, `scripts/Setup_Macena_CS2.ps1`

**Architecture:**
Three-tier build system:
1. **Setup**: `setup_new_pc.bat` / `Setup_Macena_CS2.ps1` — environment bootstrap
2. **Development**: `build_exe.bat` — quick PyInstaller build
3. **Production**: `build_production.bat` — full pipeline (migration → manifest → build → audit → installer)

**Correctness Analysis:**
- `build_production.bat` runs Alembic migration before build — ensures DB schema is current.
- RASP manifest generation integrated into production build — integrity manifest always fresh.
- Binary audit (`audit_binaries.py`) runs post-build — catches bundling issues.
- Inno Setup compilation is optional (checks for `ISCC.exe` existence).

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-04 | MEDIUM | Build | `build_production.bat` references `tools/generate_manifest.py` (line 46) which does not exist in the repository. The actual manifest tool is `Programma_CS2_RENAN/tools/sync_integrity_manifest.py`. | Update the reference to the correct tool path, or create a root-level `tools/generate_manifest.py` wrapper. |

**Positive Observations:**
- Production build pipeline includes migration, manifest generation, build, and post-build audit — comprehensive.
- PowerShell setup script handles CPU-only PyTorch variant — reduces setup friction.

---

### 7.2 `packaging/windows_installer.iss` — Windows installer configuration

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 42 |

**Analysis:**
Inno Setup script for professional Windows installer:
- Version `0.9.0` — matches `pyproject.toml` but not `__init__.py`
- Three languages: English, Italian, Brazilian Portuguese
- LZMA compression with solid compression — optimal for mixed binary/text content
- Desktop icon creation is opt-in (unchecked by default)
- Post-install launch option

**Positive Observations:**
- Tri-lingual installer matches the application's i18n support.
- Opt-in desktop icon follows Windows UX conventions.

---

### 7.3 `docker-compose.yml` — Docker composition

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 19 |

**Analysis:**
Single-service composition for FlareSolverr (Cloudflare bypass proxy):
- Port `8191:8191` exposed
- Health check: HTTP GET every 30s with 3 retries
- `restart: unless-stopped` — auto-recovery
- Timezone set to `Europe/Rome`

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-27 | LOW | Security | FlareSolverr image uses `:latest` tag — not pinned to specific version. | Pin to a specific version tag for reproducible builds. |

**Positive Observations:**
- Health check with reasonable parameters (30s interval, 10s timeout, 3 retries).
- `restart: unless-stopped` ensures service recovery after crashes.

---

## 8. INTERNATIONALIZATION DATA FILES

**Files analyzed**: `assets/i18n/en.json`, `assets/i18n/pt.json`, `assets/i18n/it.json`

All three files contain exactly 112 keys each with complete translations. Key coverage verified:
- All UI strings (buttons, labels, descriptions, wizard steps)
- Dialog strings (edit profile, cancel, save, open link)
- System strings (coaching status, training progress, warnings)
- Placeholder support (`{home_dir}` in wizard descriptions)

**Positive Observations:**
- Complete parity — no missing keys in any language.
- Natural translations (not machine-translated artifacts).
- Consistent key naming convention (snake_case with domain prefixes: `wizard_`, `dialog_`, `settings_`).

---

## 9. VERSION CONTROL CONFIGURATION

### `.gitignore` — Repository exclusion rules

**Analysis (102 lines):**
Comprehensive exclusion patterns covering:
- Python environments (`venv/`, `__pycache__/`, `.pyc`)
- Build artifacts (`dist/`, `build/`, `*.spec`)
- Database files (`*.db`, WAL/SHM journals)
- Model checkpoints (`*.pt` — binary, regenerable)
- Secrets (`.env`, `.secret_master.key`, `gha-creds-*.json`)
- Internal audit documents (AIstate.md, CLAUDE.md, etc.)
- Machine-specific paths (`D:/`, `user_settings.json`)

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1-28 | INFO | Version Control | `.gitignore` correctly excludes all sensitive files (.env, credentials, internal audit docs) and regenerable artifacts (*.db, *.pt, runs/). | None — well-structured exclusion rules. |

### `.gitattributes` — LFS tracking

**Analysis (2 lines):**
```
*.db filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
```
Database and model checkpoint files tracked via Git LFS — correct for large binary files.

### `LICENSE` — Dual license

**Analysis (236 lines):**
Dual license: Proprietary (default) + Apache 2.0 (optional). Contact via GitHub repository.

---

## 10. CONSOLIDATED FINDINGS MATRIX

### Findings by Severity

#### HIGH Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| ~~R1-01~~ | | | ~~RESOLVED — all three files pin KivyMD to commit `d668d8b`~~ | | | P5-01 |
| R1-02 | `demo_frame.py` / `app_types.py` | Correctness | Team enum dual definition: integer (0,1,2) vs string ("ct","t"). Documented in `app_types.py` docstring. | Silent incorrect comparisons at module boundaries. | Unify to single canonical Team definition. | — |

#### MEDIUM Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R1-04 | `build_production.bat` | Build | References non-existent `tools/generate_manifest.py`. | Production build fails at manifest step. | Update to correct path (`Programma_CS2_RENAN/tools/sync_integrity_manifest.py`). | — |
| R1-11 | `localization.py` | Maintainability | Hardcoded translations dict duplicates JSON files (270 lines). Documented as intentional fallback. | Changes must be made in two places. | Generate fallback from JSON at build time. | — |
| R1-12 | `rasp.py` | Security | Integrity manifest not cryptographically signed. | Tampering detection can be bypassed. | Consider manifest signing for production. | — |

#### LOW Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R1-03 | `windows_installer.iss` | Configuration | `__init__.py` and `pyproject.toml` now both `1.0.0`; only `windows_installer.iss` still `0.9.0`. | Installer shows wrong version. | Update `windows_installer.iss`. | — |
| ~~R1-05~~ | | | ~~RESOLVED — now configurable via `get_setting("ZOMBIE_TASK_THRESHOLD_SECONDS")`~~ | | | — |
| R1-06 | `hflayers.py` | Configuration | Extracted to `HOPFIELD_MEMORY_SLOTS = 512` constant. No longer magic number. | Could still benefit from constructor parameter. | Make constructor parameter. | Dev Rule 4 |
| R1-07 | `Programma_CS2_RENAN/requirements.txt` | Dependency | `master.zip` and PDF packages fixed. Minor sync issues remain (tensorboard, missing root deps). | Confusing for developers. | Synchronize or remove. | P5-03 |
| ~~R1-08~~ | | | ~~RESOLVED — path resolution refactored with clear inline comments~~ | | | — |
| R1-09 | `lifecycle.py` | Portability | Windows-only single-instance enforcement. | No single-instance protection on Linux. | Consider fcntl.flock for Linux. | — |
| R1-10 | `demo_frame.py` | Performance | No `__slots__` on high-frequency dataclasses. | Marginal memory overhead. | Profile before optimizing. | — |
| R1-13 | `pyproject.toml` | Configuration | mypy excludes `tests/` directory. | Type errors in tests undetected. | Remove exclusion. | — |
| R1-14 | `requirements-lock.txt` | Dependency | Still includes packages removed in P5-03 (pdfminer, pdfplumber, pypdf, PyMuPDF). | Stale lock file. | Regenerate. | P5-03 |
| R1-23 | `settings.json` | Portability | Windows-specific absolute path in defaults. | Overridden by user_settings.json. | Document in code. | — |
| R1-24 | `build.yml` | CI/CD | Bandit `|| true` makes security non-blocking. | Security findings don't fail CI. | Make HIGH severity blocking. | — |
| R1-25 | `build.yml` | CI/CD | Basic secret pattern matching. | May miss encoded secrets. | Add trufflehog/gitleaks. | — |
| R1-27 | `docker-compose.yml` | Security | FlareSolverr `:latest` tag not pinned. | Non-reproducible container builds. | Pin version tag. | — |

#### INFO Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R1-15 | `constants.py` | Architecture | Zero-dependency leaf node — ideal. | None. | None. | — |
| R1-16 | `session_engine.py` | Architecture | Event-driven Tri-Daemon pattern is exemplary. | None. | None. | — |
| R1-17 | `spatial_data.py` | Architecture | Module-level `__getattr__` for lazy loading. | May surprise unfamiliar developers. | Add comment. | — |
| R1-18 | `playback_engine.py` | Performance | Binary search seek is optimal O(log n). | None. | None. | — |
| R1-19 | `asset_manager.py` | Architecture | Deprecated `MapAssetManager` shim exists. | None. | Track and remove. | — |
| R1-20 | `logger_setup.py` | Architecture | Thread name in log format enables daemon debugging. | None. | None. | — |
| R1-21 | `sentry_setup.py` | Security | PII scrubbing is thorough and correct. | None. | None. | — |
| R1-22 | `.pre-commit-config.yaml` | CI/CD | Large file exclusion patterns are well-configured. | None. | None. | — |
| R1-26 | Gemini workflows | CI/CD | Prompt injection defenses are comprehensive. | None. | None. | — |
| R1-28 | `.gitignore` | Version Control | Exclusion rules correctly cover all sensitive/binary files. | None. | None. | — |

### Findings by Category

| Category | CRIT | HIGH | MED | LOW | INFO | Total |
|----------|------|------|-----|-----|------|-------|
| Correctness | 0 | 1 | 0 | 0 | 0 | 1 |
| Security | 0 | 0 | 1 | 2 | 2 | 5 |
| Performance | 0 | 0 | 0 | 1 | 1 | 2 |
| Concurrency | 0 | 0 | 0 | 0 | 0 | 0 |
| Maintainability | 0 | 0 | 3 | 1 | 0 | 4 |
| Architecture | 0 | 0 | 0 | 0 | 5 | 5 |
| Dependency | 0 | 1 | 1 | 1 | 0 | 3 |
| Configuration | 0 | 0 | 2 | 2 | 0 | 4 |
| CI/CD | 0 | 0 | 0 | 2 | 2 | 4 |
| Portability | 0 | 0 | 0 | 2 | 0 | 2 |
| Version Control | 0 | 0 | 0 | 0 | 1 | 1 |
| **Total** | **0** | **2** | **7** | **11** | **11** | **31** |

### Findings Trend (vs Prior Audits)

| Category | Fixed in Phases 1-12 | New in This Audit | Status |
|----------|---------------------|-------------------|--------|
| Circular dependency (config↔logger) | Fixed (Phase 6) | — | Resolved |
| C-03 double Y-flip | Fixed (Pipeline Audit) | — | Resolved |
| C-07 unbounded positions | Fixed (Pipeline Audit) | — | Resolved |
| F7-29 child process cleanup | Fixed (Phase 7) | — | Resolved |
| G-07 belief calibrator wiring | Fixed (Phase 12) | — | Resolved |
| F9-12 test timeout | Fixed (Phase 9) | — | Resolved |
| Team enum dual definition | — | R1-02 (HIGH) | New |
| KivyMD pin conflict | — | R1-01 (HIGH) | New |
| Version string inconsistency | — | R1-03 (MEDIUM) | New |

---

## 11. RECOMMENDATIONS

### Immediate Actions (HIGH)

1. **[R1-01] Regenerate `requirements-lock.txt`** from clean venv using root `requirements.txt`. Ensure KivyMD commit hash `d668d8b` is reflected in the lock file. Estimated complexity: Low (1 hour).

2. **[R1-02] Unify Team enum** — Choose either integer or string representation as canonical. Add conversion methods if both are needed at different layers. Estimated complexity: Medium (4 hours, touches demo parser and analysis modules).

### Short-Term Actions (MEDIUM)

3. **[R1-03] Synchronize version strings** — Use `importlib.metadata.version("macena-cs2-analyzer")` in `__init__.py` to derive from `pyproject.toml`, or manually synchronize all three sites. Estimated complexity: Low (30 minutes).

4. **[R1-04] Fix `build_production.bat`** reference to `tools/generate_manifest.py` — update to `Programma_CS2_RENAN/tools/sync_integrity_manifest.py`. Estimated complexity: Trivial (5 minutes).

5. **[R1-05] Extract zombie threshold** to `config.py` as `ZOMBIE_TASK_THRESHOLD_S`. Estimated complexity: Trivial (15 minutes).

6. **[R1-06] Parameterize Hopfield memory slots** — add `memory_slots=512` as constructor parameter. Estimated complexity: Low (30 minutes).

7. **[R1-07] Clean up inner `requirements.txt`** — synchronize with root or remove if unused. Estimated complexity: Low (1 hour).

8. **[R1-11] Evaluate i18n fallback strategy** — consider build-time generation of hardcoded dict from JSON. Estimated complexity: Medium (2 hours).

9. **[R1-12] Evaluate manifest signing** for production releases. Estimated complexity: Medium (4 hours for key management setup).

### Long-Term Actions (LOW + Strategic)

10. **[R1-09] Cross-platform single-instance** — implement `fcntl.flock`-based locking for Linux if deployment is planned. Estimated complexity: Medium (3 hours).

11. **[R1-24/R1-25] Strengthen CI security gates** — make Bandit blocking at HIGH severity; add `trufflehog` or `gitleaks`. Estimated complexity: Low (2 hours).

12. **[R1-27] Pin Docker image versions** — replace `:latest` with specific FlareSolverr version tag. Estimated complexity: Trivial (5 minutes).

### Architectural Recommendations

1. **Version Single Source of Truth**: Establish `pyproject.toml` as the sole version authority. All other consumers (`__init__.py`, `windows_installer.iss`, Sentry) should derive from it.

2. **Dependency Hygiene Automation**: Add a CI job that verifies `requirements-lock.txt` is consistent with `requirements.txt` (e.g., `pip install --dry-run -r requirements.txt` and compare).

3. **i18n Build Pipeline**: Consider a pre-commit hook that generates the hardcoded translation fallback from JSON files, eliminating the dual-maintenance burden.

---

## APPENDIX A: COMPLETE FILE INVENTORY

| # | File Path | LOC | Classes | Functions | Findings |
|---|-----------|-----|---------|-----------|----------|
| 1 | `Programma_CS2_RENAN/__init__.py` | 2 | 0 | 0 | 1 (M) |
| 2 | `core/__init__.py` | 0 | 0 | 0 | 0 |
| 3 | `core/app_types.py` | 77 | 4 | 0 | 1 (H) |
| 4 | `core/asset_manager.py` | 254 | 4 | 18 | 1 (I) |
| 5 | `core/config.py` | 356 | 0 | 15 | 1 (L) |
| 6 | `core/constants.py` | 34 | 0 | 0 | 1 (I) |
| 7 | `core/demo_frame.py` | 151 | 7 | 0 | 1 (L) |
| 8 | `core/frozen_hook.py` | 17 | 0 | 1 | 0 |
| 9 | `core/lifecycle.py` | 145 | 1 | 8 | 1 (L) |
| 10 | `core/localization.py` | 422 | 0 | 5 | 1 (M) |
| 11 | `core/logger.py` | 13 | 0 | 0 | 0 |
| 12 | `core/map_manager.py` | 87 | 1 | 3 | 0 |
| 13 | `core/platform_utils.py` | 43 | 0 | 1 | 0 |
| 14 | `core/playback.py` | 115 | 1 | 8 | 0 |
| 15 | `core/playback_engine.py` | 246 | 1 | 14 | 1 (I) |
| 16 | `core/registry.py` | 42 | 1 | 3 | 0 |
| 17 | `core/session_engine.py` | 464 | 0 | 12 | 2 (M, I) |
| 18 | `core/spatial_data.py` | 387 | 2 | 14 | 1 (I) |
| 19 | `core/spatial_engine.py` | 92 | 1 | 6 | 0 |
| 20 | `observability/__init__.py` | 0 | 0 | 0 | 0 |
| 21 | `observability/logger_setup.py` | 87 | 0 | 4 | 1 (I) |
| 22 | `observability/rasp.py` | 138 | 2 | 5 | 1 (M) |
| 23 | `observability/sentry_setup.py` | 152 | 0 | 4 | 1 (I) |
| 24 | `hflayers.py` | 116 | 1 | 2 | 1 (M) |
| 25 | `pyproject.toml` | 70 | — | — | 1 (L) |
| 26 | `pytest.ini` | 46 | — | — | 0 |
| 27 | `requirements.txt` | 48 | — | — | 0 |
| 28 | `requirements-ci.txt` | 9 | — | — | 0 |
| 29 | `requirements-lock.txt` | 157 | — | — | 2 (H, L) |
| 30 | `Programma_CS2_RENAN/requirements.txt` | 116 | — | — | 1 (M) |
| 31 | `bindep.txt` | 15 | — | — | 0 |
| 32 | `.pre-commit-config.yaml` | 97 | — | — | 1 (I) |
| 33 | `docker-compose.yml` | 19 | — | — | 1 (L) |
| 34 | `.gitignore` | 102 | — | — | 1 (I) |
| 35 | `.gitattributes` | 2 | — | — | 0 |
| 36 | `LICENSE` | 236 | — | — | 0 |
| 37 | `integrity_manifest.json` | 23 | — | — | 0 |
| 38 | `settings.json` | 6 | — | — | 1 (L) |
| 39 | `packaging/windows_installer.iss` | 42 | — | — | 0 |
| 40 | `packaging/BUILD_CHECKLIST.md` | 76 | — | — | 0 |
| 41 | `export_env.bat` | 5 | — | — | 0 |
| 42 | `setup_new_pc.bat` | 23 | — | — | 0 |
| 43 | `scripts/build_exe.bat` | 14 | — | — | 0 |
| 44 | `scripts/build_production.bat` | 95 | — | — | 1 (M) |
| 45 | `scripts/Setup_Macena_CS2.ps1` | 53 | — | — | 0 |
| 46 | `.github/workflows/build.yml` | 270 | — | — | 2 (L) |
| 47 | `.github/workflows/gemini-dispatch.yml` | 205 | — | — | 0 |
| 48 | `.github/workflows/gemini-invoke.yml` | 122 | — | — | 0 |
| 49 | `.github/workflows/gemini-review.yml` | 110 | — | — | 0 |
| 50 | `.github/workflows/gemini-scheduled-triage.yml` | 215 | — | — | 0 |
| 51 | `.github/workflows/gemini-triage.yml` | 159 | — | — | 0 |
| 52 | `.github/commands/gemini-invoke.toml` | 134 | — | — | 1 (I) |
| 53 | `.github/commands/gemini-review.toml` | 173 | — | — | 0 |
| 54 | `.github/commands/gemini-scheduled-triage.toml` | 117 | — | — | 0 |
| 55 | `.github/commands/gemini-triage.toml` | 55 | — | — | 0 |
| 56 | `assets/i18n/en.json` | 113 | — | — | 0 |
| 57 | `assets/i18n/pt.json` | 113 | — | — | 0 |
| 58 | `assets/i18n/it.json` | 113 | — | — | 0 |

*Note: Files 59-77 comprise READMEs and governance documents across core/, observability/, scripts/, and root directories. These documentation files were reviewed for accuracy and completeness but are not individually tabulated as they do not contain executable code.*

---

## APPENDIX B: GLOSSARY

| Term | Definition |
|------|-----------|
| **BRAIN_DATA_ROOT** | External storage path for regeneratable ML data (embeddings, training artifacts). Core DB stays in project root. |
| **COPER** | Coaching workflow: Experience Bank → RAG → Pro Bridge — the default coaching mode. |
| **DemoFrame** | Tick-level snapshot of complete CS2 game state (players, grenades, bomb, events). |
| **FlareSolverr** | Docker-based Cloudflare bypass proxy used for HLTV web scraping. |
| **Hopfield Network** | Dense associative memory using softmax attention for pattern retrieval (Ramsauer et al., 2020). |
| **METADATA_DIM** | Critical dimensional constant (25) defining feature vector width. Must match INPUT_DIM. |
| **RASP** | Runtime Application Self-Protection — SHA-256 integrity verification at startup. |
| **SpatialConfigLoader** | Thread-safe singleton providing map coordinate metadata (pos_x, pos_y, scale, z_cutoff). |
| **Tri-Daemon Engine** | Four-thread architecture: Scanner (discovery), Digester (processing), Teacher (training), Pulse (monitoring). |
| **WAL Mode** | Write-Ahead Logging — SQLite journal mode enabling concurrent reads during writes. |
| **Y-Flip** | CS2 world coordinates have Y-axis inverted relative to screen coordinates. Handled at rendering layer only. |

---

## APPENDIX C: CROSS-REFERENCE INDEX

| Finding ID | Remediation Code | Pipeline Code | CLAUDE.md Rule |
|------------|-----------------|---------------|----------------|
| ~~R1-01~~ | P5-01 | — | ~~RESOLVED~~ |
| R1-02 | — | — | Rule 1 (correctness) |
| R1-03 | — | — | Rule 7 (versioning) — downgraded to LOW |
| R1-04 | — | — | Rule 1 (no silent failures) |
| ~~R1-05~~ | — | — | ~~RESOLVED~~ |
| R1-06 | — | — | Dev Rule 4 — downgraded to LOW (magic number fixed) |
| R1-07 | P5-03 | — | Rule 7 — downgraded to LOW (main issues fixed) |
| ~~R1-08~~ | — | — | ~~RESOLVED~~ |
| R1-11 | — | — | Dev Rule 2 (backward compatibility) |
| R1-12 | — | — | Rule 5 (assume hostile world) |

---

## APPENDIX D: DEPENDENCY GRAPH

```
Core Module Import Graph (simplified):

constants.py ◄─── (no imports — leaf node)
     │
     ▼
app_types.py ◄─── (only typing imports)
     │
     ▼
config.py ──────► observability/logger_setup.py
     │                    │
     │              configure_log_dir()
     │                    │
     ▼                    ▼
spatial_data.py    logger.py (deprecated shim)
     │
     ▼
spatial_engine.py
     │
     ▼
demo_frame.py
     │
     ▼
playback_engine.py ──► playback.py (Kivy controller)
     │
     ▼
session_engine.py ──► lifecycle.py
     │                    │
     │              (subprocess management)
     │
     ▼
asset_manager.py ──► map_manager.py (Kivy async loader)

Observability:
logger_setup.py ◄── config.py (configure_log_dir)
                ◄── sentry_setup.py (get_logger)
                ◄── rasp.py (uses print, not logger)

External:
hflayers.py ◄── (standalone, imported by nn/rap_coach/memory.py)
```

---

## APPENDIX E: DATA FLOW DIAGRAMS

### Configuration Flow
```
settings.json ──► config.py ──► load_user_settings() ──► Consumers
                      │
user_settings.json ──►│ (override, gitignored)
                      │
                      ├──► DATABASE_URL ──► storage/database.py
                      ├──► LOG_DIR ──► logger_setup.configure_log_dir()
                      ├──► BRAIN_DATA_ROOT ──► storage, nn, processing
                      └──► SENTRY_DSN ──► sentry_setup.init_sentry()

Secret Flow:
config.get_secret("steam_api_key")
     │
     ├──► keyring.get_password() ──► OS Credential Store
     │          │ (fallback)
     └──► os.environ["STEAM_API_KEY"]
                │ (fallback)
                └──► None
```

### Spatial Coordinate Pipeline
```
World Coordinates (CS2 engine)
     │
     ▼ world_to_radar() [spatial_data.py]
     │ formula: (world_x - pos_x) / scale
     │
Radar Coordinates (0.0 - 1.0 normalized)
     │
     ▼ normalized_to_pixel() [spatial_engine.py]
     │ formula: radar_coord * widget_size
     │
Pixel Coordinates (screen space)
     │
     ▼ Y-flip at render [tactical_map.py — Report 7]
     │ formula: widget_height - pixel_y
     │
Display Coordinates
```

### Application Startup Sequence
```
main.py ──► frozen_hook.py (if PyInstaller)
     │
     ▼
lifecycle.py ──► Check single-instance (Mutex)
     │
     ▼
config.py ──► Resolve paths, load settings
     │
     ▼
logger_setup.py ──► Create log directory, configure handlers
     │
     ▼
rasp.py ──► Verify integrity manifest (production only)
     │
     ▼
sentry_setup.py ──► Init Sentry (if enabled + DSN present)
     │
     ▼
lifecycle.py ──► Launch session_engine subprocess
     │                    │
     │              session_engine.py
     │                    │
     │              ┌─────┼─────┬────────┐
     │              ▼     ▼     ▼        ▼
     │           Scanner Digester Teacher Pulse
     │
     ▼
Kivy App ──► Screen registration ──► UI rendering
```

---

*End of Report 1/8 — Foundation Architecture, Configuration Governance, and Platform Infrastructure*
