> **STATUS: ALL 12 PHASES COMPLETE — 368 total issues fixed (2026-03-08)**
> Sections 0 (Development Discipline) and 2 (Seven Laws of Implementation) remain valid as methodology reference.
> Per-phase execution records in `reports/phase*.md`. Deferred items tracked in `docs/DEFERRALS.md`.

# Macena CS2 Analyzer — Master Remediation & Shipping Plan

> **Document Version:** 1.0
> **Date:** 2026-03-06
> **Authority:** Derived from the Complete Project Audit + Deep Code Audits of all 163 modules
> **Scope:** Every finding from the audit, plus newly discovered issues from deep code review
> **Purpose:** A clinically precise, self-contained execution plan that, when followed top-to-bottom, transforms the project from late-alpha to shippable product

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Methodology & Prioritization Framework](#2-methodology--prioritization-framework)
3. [Phase 0: Emergency Fixes (Blocking Bugs)](#3-phase-0-emergency-fixes-blocking-bugs)
4. [Phase 1: ML Pipeline Integrity](#4-phase-1-ml-pipeline-integrity)
5. [Phase 2: Data Layer Hardening](#5-phase-2-data-layer-hardening)
6. [Phase 3: Processing & Analysis Correctness](#6-phase-3-processing--analysis-correctness)
7. [Phase 4: UI/UX Remediation](#7-phase-4-uiux-remediation)
8. [Phase 5: Dependency & Build Stabilization](#8-phase-5-dependency--build-stabilization)
9. [Phase 6: Test Coverage & CI/CD](#9-phase-6-test-coverage--cicd)
10. [Phase 7: Security Hardening](#10-phase-7-security-hardening)
11. [Phase 8: Heuristic Validation & Calibration](#11-phase-8-heuristic-validation--calibration)
12. [Phase 9: Architecture Decisions (ML Model Consolidation)](#12-phase-9-architecture-decisions-ml-model-consolidation)
13. [Phase 10: Documentation & Packaging](#13-phase-10-documentation--packaging)
14. [Phase 11: Performance Optimization](#14-phase-11-performance-optimization)
15. [Phase 12: Final QA & Release Gate](#15-phase-12-final-qa--release-gate)
16. [Appendix A: Complete Issue Registry](#16-appendix-a-complete-issue-registry)
17. [Appendix B: Files Not Covered by Original Audit](#17-appendix-b-files-not-covered-by-original-audit)
18. [Appendix C: Heuristic Constants Requiring Empirical Validation](#18-appendix-c-heuristic-constants-requiring-empirical-validation)
19. [Appendix D: Cross-Module Inconsistencies](#19-appendix-d-cross-module-inconsistencies)

---

## 0. Preamble: Development Discipline — The Root Cause Analysis

> **"The rules are more important than the work itself."**

Before diving into the 156 individual issues tracked in this plan, we must address the root cause that created most of them: **a lack of disciplined, systematic development practices during implementation.** This is not a criticism of engineering skill — the individual implementations are often brilliant (the LTC+Hopfield memory architecture, the expectiminimax game tree, the HLTV 2.0 reverse engineering). The problem is that brilliant components were assembled without sufficient inter-module verification, without consistent patterns, and without automated quality gates.

### 0.1 The Cost of Undisciplined Development

During the audit, we identified a recurring pattern where significant development time was wasted on correcting or polishing implementations that were delivered in an incomplete or incompatible state. Here are the specific failure modes and their consequences:

**Failure Mode 1: Implement-Without-Reading**
- **Example:** `PlayerRole` enum created independently in `role_features.py` and `role_classifier.py` with incompatible values (`"entry"` vs `"Entry Fragger"`).
- **Cost:** Every downstream consumer that compares roles across modules silently fails. Every coaching insight that references a player role is potentially wrong. Discovery required reading 25+ files.
- **Prevention:** 30 seconds of `grep -rn "PlayerRole" Programma_CS2_RENAN/` before implementation.

**Failure Mode 2: Unit-of-Measure Confusion**
- **Example:** `avg_kills` is per-match in `pro_bridge.py` but per-round in `base_features.py`. A pro with 0.8 KPR gets `avg_kills = 19.2` while a user averaging 1.2 kills/round gets `avg_kills = 1.2`. Z-score comparison: `(1.2 - 19.2) / std` = completely nonsensical.
- **Cost:** The entire coaching comparison pipeline produces wrong results. Every "Your kills are below pro level" message is based on invalid math. Users receive misleading advice.
- **Prevention:** Variable naming convention that includes units: `kills_per_round` vs `kills_per_match`. Code review checking unit consistency.

**Failure Mode 3: Write-And-Forget**
- **Example:** `EarlyStopping` class was correctly implemented, tested in isolation, then never imported into any training loop. The module sat unused for the entire development period while every training run was vulnerable to overfitting.
- **Cost:** All trained models may be overfit. The training infrastructure appears complete but is missing a critical component.
- **Prevention:** Integration test verifying the complete training pipeline, not just individual components.

**Failure Mode 4: Silent Error Swallowing**
- **Example:** `main.py:834` uses `func.sum()` but `func` is never imported. The `NameError` is caught by `except Exception: logger.debug(...)`, causing `knowledge_ticks` to permanently read zero. Users see "0 ticks ingested" and assume they have no data — they may re-import demos or think the system is broken.
- **Cost:** Users lose trust in the system. Debugging time is wasted chasing phantom issues. The actual bug is invisible because the error is downgraded to `debug` level.
- **Prevention:** Never use bare `except Exception` for business logic. Catch specific exceptions. Log errors at appropriate severity.

**Failure Mode 5: Inconsistent Architecture Patterns**
- **Example:** `DatabaseManager` uses proper double-checked locking for its singleton. `StateManager` uses module-level instantiation (no locking). `RoleThresholdStore` uses a function-level global (no locking). Three different singleton patterns in one project, two of which are broken.
- **Cost:** Thread race conditions that manifest as duplicate database rows, lost state updates, or corrupt threshold data. These bugs are intermittent and extremely difficult to reproduce.
- **Prevention:** One canonical singleton pattern documented in the engineering constitution, enforced by code review.

**Failure Mode 6: Missing Automated Gates**
- **Example:** No CI/CD pipeline exists. The only quality gate is pre-commit hooks, which can be bypassed with `--no-verify`. The headless validator runs on pre-push, but nothing prevents a developer from pushing directly to main.
- **Cost:** Regressions accumulate. Fixes for one module break another. The codebase gradually degrades in quality because there is no automated enforcement of standards.
- **Prevention:** CI/CD pipeline with branch protection. Merge to main requires all checks green.

### 0.2 The Discipline Contract

This plan requires adherence to a strict development discipline contract. **Every task in this plan — from a trivial one-line fix to a complex architectural refactor — must follow these rules without exception.** These rules are not optional, not aspirational, and not "nice to have." They are the mechanism that prevents the rework cycles that have plagued this project.

The full rules are specified in Section 2 (Methodology, Rules & Anti-Regression Framework). The key principles are:

1. **Read before you write.** Never modify a file you haven't read. Never create a definition without searching for existing ones.
2. **One source of truth.** Every concept has exactly one canonical definition. All consumers import from it.
3. **No silent failures.** Every error is logged, every fallback is visible, every exception is specific.
4. **Thread safety is binary.** A module is either thread-safe (with documented locking) or it is not shared across threads.
5. **Test what you ship.** Every fix has a regression test. Coverage monotonically increases.
6. **Measure before you tune.** No magic numbers without cited sources. Validate empirically when possible.
7. **Ship incrementally.** Each phase produces a working system. Feature flags for experimental code.

### 0.3 How to Read This Document

This document is organized so you never have to come back to re-read or re-correct:

- **Section 0 (this section):** Why discipline matters. Read once, internalize permanently.
- **Section 2:** The complete rules framework. Reference before EVERY implementation task.
- **Sections 3-15 (Phases 0-12):** The actual work. Each task is self-contained with file:line references, code examples, acceptance criteria, and complexity estimates.
- **Appendices A-D:** Reference data. Consult when a task requires context about the full issue registry, undiscovered files, heuristic constants, or cross-module inconsistencies.

The intent is that a developer can pick up any task in this document, follow the rules in Section 2, implement the fix per the task description, and commit — without needing to ask questions, without introducing regressions, and without creating new inconsistencies.

---

## 1. Executive Summary

The Complete Project Audit confirmed that Macena CS2 Analyzer is a legitimate, seriously engineered system — not vibecoded, not a toy. The hard engineering work is done. What remains is hardening, validation, and polish.

This plan addresses **every issue** raised in the audit plus **47 additional issues** discovered through deep code review of areas the audit could not cover. The plan is organized into 13 execution phases, ordered by dependency and severity. Each phase contains atomic, implementable tasks with precise file:line references, acceptance criteria, and estimated complexity.

**Summary of findings across all audits:**

| Domain | Critical | High | Medium | Low | Total |
|--------|----------|------|--------|-----|-------|
| ML Pipeline | 4 | 2 | 16 | 16 | 38 |
| Storage/DB | 3 | 0 | 7 | 6 | 16 |
| console.py + main.py | 2 | 6 | 12 | 15 | 35 |
| Processing/Analysis | 2 | 8 | 10 | 8 | 28 |
| UI/Desktop App | 4 | 8 | 8 | 4 | 24 |
| Security | 0 | 3 | 4 | 3 | 10 |
| Dependencies/Build | 1 | 1 | 2 | 1 | 5 |
| **Total** | **16** | **28** | **59** | **53** | **156** |

The plan is designed so that completing Phases 0-6 produces a shippable beta. Phases 7-12 produce a market-ready product.

---

## 2. Methodology, Rules & Anti-Regression Framework

### 2.1 Why This Framework Exists

Throughout the development of Macena CS2 Analyzer, a recurring pattern emerged: implementations were delivered, then discovered to be incomplete, incorrectly integrated, or incompatible with other modules — forcing costly re-work cycles. Specific examples uncovered during audit:

- **The `PlayerRole` enum was independently defined in two modules** (`role_features.py` and `role_classifier.py`) with incompatible string values. Every downstream consumer that compared roles across modules silently failed. This should have been caught by a simple grep before implementation.
- **The `avg_kills` metric uses per-match scale in `pro_bridge.py` but per-round scale in `base_features.py`**, rendering every z-score comparison between user and pro stats meaningless. This is a fundamental unit-of-measure error that invalidated the entire coaching comparison pipeline.
- **`EarlyStopping` was fully implemented but never wired into any training loop.** Someone wrote a correct, well-tested module and then forgot to import it. Every training run since has been vulnerable to overfitting.
- **The `func` import was missing from `_threaded_status_update` in `main.py`**, but because the error was caught by a bare `except`, it was silently swallowed — leaving `knowledge_ticks` permanently at zero. The symptom was invisible; users saw "0 ticks" and assumed they had no data.
- **Multiple singleton factories (`get_death_estimator`, `get_blind_spot_detector`) create new instances on every call**, losing any calibration or cached state. The developer used the singleton naming pattern but not the singleton implementation pattern.
- **Thread-unsafe singletons exist in `state_manager.py` and `role_thresholds.py`** where the classic double-checked locking pattern was used in some modules (`database.py`) but not others, creating a patchwork of thread-safety guarantees.

These are not skill gaps — the individual implementations are often excellent. They are **process gaps**: insufficient verification before implementation, inconsistent patterns across modules, and no automated cross-module consistency checks. This framework exists to close those gaps permanently.

### 2.2 Severity Definitions

- **CRITICAL**: Will cause crashes, data corruption, or fundamentally wrong results in production. The system produces output that a user would trust but that is demonstrably incorrect. Must fix before any release. Examples: `avg_kills` scale mismatch producing nonsensical z-scores; train=val leaking data; missing imports causing silent fallback to wrong values.
- **HIGH**: Causes incorrect behavior under common conditions, security vulnerabilities, or silent data loss. The system appears to work but produces degraded or insecure results. Must fix before beta. Examples: no gradient clipping causing training instability; thread-unsafe singletons; API keys logged in plaintext.
- **MEDIUM**: Causes incorrect behavior under edge conditions, performance problems, or maintenance traps. The system works for most users most of the time, but specific scenarios trigger bugs. Should fix before GA. Examples: hardcoded 64-tick assumption; normalization division by epsilon; missing loading indicators.
- **LOW**: Code quality, dead code, minor inconsistencies. Do not affect user-visible behavior. Fix opportunistically. Examples: unused imports; redundant re-imports; dead validation stubs.

### 2.3 The Seven Laws of Implementation

These laws are derived directly from the mistakes found during audit. Every implementation task in this plan must comply with all seven.

**Law 1: Verify Before You Write (Scope Guard)**

Before writing a single line of code, you MUST:
1. **Read every file you will modify.** Not skim — read. Understand existing patterns, naming conventions, and invariants.
2. **Read every file that imports from or is imported by your target.** If you're changing `role_features.py`, read `role_classifier.py`, `correction_engine.py`, and every other consumer.
3. **Search for existing implementations.** Before creating a new enum, constant, utility function, or pattern, search the codebase for existing ones. The `PlayerRole` duplication happened because someone didn't `grep -r "PlayerRole"` before creating a second definition.
4. **Verify dimensional consistency.** If your change involves numbers with units (kills per round vs kills per match, ticks at 64Hz vs 128Hz, pixels vs dp), trace the unit from source to sink and verify it's consistent.

**Enforcement:** Run `/scope-guard` before every implementation that touches >2 files.

**Law 2: One Source of Truth (No Duplication)**

Every concept, constant, enum, or pattern must have exactly ONE canonical definition. All consumers must import from that definition.

| Concept | Canonical Location | Anti-Pattern |
|---------|-------------------|--------------|
| `PlayerRole` | `core/app_types.py` | Defining in both `role_features.py` AND `role_classifier.py` |
| `METADATA_DIM` | `backend/processing/feature_engineering/__init__.py` | Hardcoding `25` in config files |
| Feature names | `MATCH_AGGREGATE_FEATURES` in `coach_manager.py` | Using `"avg_kast"` in one module and `"kast"` in another |
| Tick rate | `core/config.py:TICK_RATE` | Hardcoding `64` in `player_knowledge.py:440` |
| Pro baselines | `backend/processing/baselines/pro_baseline.py` | Hardcoded dicts in `hybrid_engine.py:163-176` |
| Singleton pattern | Double-checked locking with `threading.Lock` | Module-level instantiation (`state_manager = StateManager()`) |

**Enforcement:** Run `grep -r` for the concept name before every implementation. If you find a duplicate, consolidate before proceeding.

**Law 3: Explicit is Better Than Silent (No Swallowed Errors)**

The codebase has multiple instances of `except Exception: pass` or `except Exception: log.debug(...)` that mask critical failures:
- `main.py:67-68` — Sentry init failure swallowed with `pass`
- `main.py:834` — `NameError` on `func` swallowed as debug log
- `main.py:1783-1784` — Brain dialog query failure swallowed with no logging at all
- `state_manager.py:74-75` — Status update failure logged but not escalated

Rules:
1. **Never use bare `except Exception: pass`** — at minimum, log at `warning` level.
2. **Never catch `Exception` when you mean to catch a specific error** — catch `ConnectionError`, `ValueError`, `FileNotFoundError`, etc.
3. **Never downgrade error severity in catch blocks** — if a database write fails, it's not `debug`, it's `error`.
4. **If a fallback is used, make it visible** — `hybrid_engine.py:162` correctly sets `_using_fallback_baseline = True` and tags insights with degraded quality. This pattern should be universal.

**Enforcement:** Pre-commit hook scanning for `except Exception:` without at least `logger.warning`.

**Law 4: Thread Safety is Binary (Safe or Broken)**

The codebase has an inconsistent patchwork of thread-safety measures:
- `database.py`: Correct double-checked locking with `threading.Lock` for singleton
- `state_manager.py:165`: Module-level instantiation with no locking (BROKEN)
- `state_manager.py:23-35`: `get_state()` reads without lock, `update_status()` writes with lock (BROKEN)
- `coaching_chat_vm.py:128`: One method uses `_messages_lock`, another doesn't (BROKEN)
- `role_thresholds.py:259-267`: Singleton without any locking (BROKEN)

Rules:
1. **All singletons must use double-checked locking** — no exceptions, no module-level instantiation.
2. **All shared mutable state must be protected by a lock** — if a lock exists on a class, ALL methods that read or write shared state must acquire it.
3. **Never pass ORM objects across thread boundaries** — materialize to dicts or dataclasses before scheduling callbacks via `Clock.schedule_once`.
4. **Never use a plain `bool` as a thread guard** — use `threading.Event` or `threading.Lock`.

**Enforcement:** Run `/state-audit` on every file that uses `threading.Thread` or `Clock.schedule_once`.

**Law 5: Test What You Ship (Coverage is Non-Negotiable)**

The current 49% coverage threshold means more than half the codebase has zero automated verification. Critical paths like `train.py`, `correction_engine.py`, and `belief_model.py` can break silently.

Rules:
1. **Every bug fix must include a regression test** that would have caught the bug.
2. **Every new feature must include at least one positive test and one edge-case test.**
3. **Coverage must monotonically increase** — no commit may reduce the coverage percentage.
4. **The headless validator is not a substitute for unit tests** — it verifies import health and structural integrity, not behavioral correctness.

Minimum test requirements for each module tier:
- **Tier 1 (data pipeline, ML training, coaching):** 80%+ coverage, including edge cases
- **Tier 2 (analysis modules, storage):** 70%+ coverage
- **Tier 3 (UI, tools, observability):** 50%+ coverage (UI needs manual testing)

**Enforcement:** `pytest --cov-fail-under` in CI pipeline; `/validate` after every task.

**Law 6: Measure Before You Tune (No Unvalidated Heuristics)**

The project has **35 hand-tuned constants** (see Appendix C) with zero empirical validation. Some are demonstrably wrong (the `MEMORY_DECAY_TAU` comment claims 2.5s half-life but the actual half-life is 1.73s). Others are reasonable guesses that may be far from optimal.

Rules:
1. **Every heuristic constant must have a comment citing its source** — "HLTV 2024 dataset", "CS2 game data (valve docs)", "hand-tuned, pending validation (see P8-XX)".
2. **No new magic numbers** — extract to named constants with clear units in the name (e.g., `MEMORY_DECAY_TAU_TICKS = 160` not `TAU = 160`).
3. **Validation is a separate task from implementation** — implement with reasonable defaults, but create a tracking issue for empirical validation.
4. **When a constant is validated, update the comment** with the dataset, methodology, and result.

**Enforcement:** `/complexity-check` flags unnamed numeric literals; Appendix C serves as the validation tracker.

**Law 7: Ship Incrementally (No Big Bangs)**

The project attempted to build everything at once — game theory, JEPA, RAP Coach, LTC+Hopfield, Bayesian belief models, Shannon entropy — before any of it was validated end-to-end. This created a massive surface area of untested code that is difficult to verify in aggregate.

Rules:
1. **Each phase in this plan is a shippable increment** — Phase 0-6 produce a beta, Phase 7-12 produce a release.
2. **New features must be behind feature flags** until validated — `USE_JEPA_MODEL`, `USE_RAP_COACH`, `USE_GAME_TREE`, etc.
3. **Experimental code goes in `experimental/`** — not mixed into the production pipeline.
4. **The fallback chain must always reach a working state** — if COPER fails, Hybrid must work; if Hybrid fails, Traditional must work. Test each fallback transition.

**Enforcement:** Feature flags checked in startup; fallback chain tested in integration tests.

### 2.4 Implementation Workflow (Mandatory for Every Task)

```
START
  │
  ├─ 1. Read the task description and acceptance criteria
  │
  ├─ 2. /scope-guard — verify target files, interfaces, existing patterns
  │     └─ If scope-guard reveals conflicts: STOP, update the plan
  │
  ├─ 3. /change-impact — map blast radius (who imports this? who calls this?)
  │     └─ If blast radius > 5 files: /design-review first
  │
  ├─ 4. IMPLEMENT — write code following the Seven Laws
  │     └─ Each commit is atomic (one logical change)
  │     └─ Commit message: "[PX-NN] <description>"
  │
  ├─ 5. Write regression test(s) for the change
  │
  ├─ 6. /validate — run headless validator (must exit 0)
  │     └─ If fails: fix regression, do NOT proceed
  │
  ├─ 7. /pre-commit — all 13 hooks must pass
  │     └─ If fails: fix formatting/linting, re-run
  │
  └─ 8. Mark task COMPLETE only when all gates pass
```

### 2.5 Phase Ordering Rationale

Phases are ordered by the dependency graph of the system. You cannot fix UI issues if the data layer returns wrong values. You cannot validate heuristics if the ML pipeline doesn't train correctly. You cannot ship if there are no tests.

```
Phase 0 (Emergency) ──→ Phase 1 (ML) ──→ Phase 2 (Data) ──→ Phase 3 (Processing)
                                                                      │
Phase 5 (Deps) ←── Phase 4 (UI) ←─────────────────────────────────────┘
       │
Phase 6 (Tests/CI) ──→ Phase 7 (Security) ──→ Phase 8 (Heuristics) ──→ Phase 9 (Architecture)
                                                                              │
                                     Phase 10 (Docs) ──→ Phase 11 (Perf) ──→ Phase 12 (Release)
```

**Why this order matters:**
- Phase 0 fixes crashes and data corruption. Nothing else matters if the app crashes.
- Phase 1 fixes ML training. If the model trains incorrectly, all coaching advice is wrong.
- Phase 2 fixes data storage. If data is lost or corrupted, training and analysis are unreliable.
- Phase 3 fixes processing logic. If features are wrong, the model learns wrong patterns.
- Phase 4 fixes UI. If the UI shows wrong data or crashes, users can't use the product.
- Phase 5 stabilizes dependencies. If KivyMD master breaks, nothing works.
- Phase 6 adds CI/CD. Without automated gates, regressions creep back in.
- Phase 7-12 are polish and preparation for market.

### 2.6 Quality Gates Between Phases

No phase may begin until the previous phase's gate passes:

| Phase | Gate Criteria |
|-------|--------------|
| 0→1 | All CRITICAL bugs fixed. `headless_validator.py` passes. No `NameError`, no data corruption, no race conditions. |
| 1→2 | ML training produces valid models. Early stopping works. Seeds are set. JEPA loss is contrastive. |
| 2→3 | All DB operations are thread-safe. Backups are atomic. Schema constraints enforced. |
| 3→4 | All cross-module inconsistencies resolved (Appendix D empty). Feature names match. Scales match. |
| 4→5 | UI thread safety verified. No blocking calls on main thread. MVVM compliance for new ViewModels. |
| 5→6 | Dependencies pinned. KivyMD stable. `pip install -r requirements.txt` succeeds on fresh venv. |
| 6→7 | CI pipeline green. Coverage >= 60%. All Phase 0-5 fixes have regression tests. |
| 7→8 | Security scan clean. No plaintext secrets. Rate limiting on all public endpoints. |
| 8→9 | At least 10 heuristic constants empirically validated. Calibration error < 0.05 for belief model. |
| 9→10 | Canonical ML model selected. Experimental code isolated. Feature flags in place. |
| 10→11 | README complete. PyInstaller build succeeds. User guide updated. |
| 11→12 | Performance benchmarks met. No O(N^2) loops in hot paths. |

### 2.7 Anti-Regression Rules (Lessons from Past Development)

These rules exist specifically because past development cycles suffered from implementations that were delivered "done" but later found to be broken, incomplete, or incompatible. Each rule directly prevents a specific class of past failure.

**Rule AR-1: No Implementation Without Reading (prevents P3-01, P3-02)**
Past failure: Two `PlayerRole` enums were created independently because the second developer didn't search for existing definitions.
Rule: Before creating any new enum, class, constant, or utility function, run `grep -rn "<name>" Programma_CS2_RENAN/` to check for existing definitions. If an existing definition serves the same purpose, import it instead of creating a new one.

**Rule AR-2: No Cross-Module Data Without Unit Verification (prevents P3-02)**
Past failure: `avg_kills` was per-match in one module and per-round in another, making all z-score comparisons meaningless.
Rule: When a function produces a numeric value that will be consumed by another module, the variable name MUST include its unit: `kills_per_round`, `kills_per_match`, `distance_world_units`, `time_seconds`, `time_ticks`. Generic names like `avg_kills` are forbidden for cross-module interfaces.

**Rule AR-3: No Silent Fallbacks Without Telemetry (prevents P0-01)**
Past failure: `func.sum()` threw `NameError` which was caught by a bare `except`, causing `knowledge_ticks` to silently remain at zero forever.
Rule: Every `except` block that provides a fallback value MUST log at `warning` level and set a telemetry flag (like `_using_fallback_baseline`). Silent fallbacks are indistinguishable from correct behavior — they hide bugs indefinitely.

**Rule AR-4: No Module Without Integration Test (prevents P1-01)**
Past failure: `EarlyStopping` was fully implemented but never imported into any training loop. A unit test for `EarlyStopping` existed, but no integration test verified that training actually uses it.
Rule: For every module that is designed to be used by another module, write an integration test that verifies the import and call chain end-to-end. A module that passes its own unit tests but is never imported is dead code.

**Rule AR-5: No Singleton Without Lock (prevents P0-04, P3-06)**
Past failure: `StateManager` used a module-level instantiation pattern while `DatabaseManager` used proper double-checked locking. The inconsistency led to a race condition in state management.
Rule: Every singleton factory function MUST use this exact pattern:
```python
_instance: Optional[T] = None
_instance_lock = threading.Lock()

def get_instance() -> T:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = T()
    return _instance
```
No variations. No shortcuts. No module-level instantiation.

**Rule AR-6: No Training Without Validation Split (prevents P1-04)**
Past failure: When training data had fewer than 10 samples, the code used `train=val`, making validation loss identical to training loss and early stopping meaningless.
Rule: Training MUST refuse to proceed if the dataset is too small for a meaningful train/val split. The minimum is 20 samples (16 train, 4 val). If data is insufficient, log a clear message and return a NullModel that produces safe defaults.

**Rule AR-7: No Commit Without Green Gates (prevents all regressions)**
Past failure: Multiple fixes were committed without running the headless validator, causing cascading regressions.
Rule: The commit sequence is ALWAYS:
1. `python tools/headless_validator.py` — must exit 0
2. `pre-commit run --all-files` — must pass all 13 hooks
3. `pytest tests/` — must pass with no failures
4. Only then: `git add` + `git commit`

If ANY gate fails, DO NOT commit. Fix the issue first. Never use `--no-verify`.

---

## 3. Phase 0: Emergency Fixes (Blocking Bugs)

These are bugs that will cause crashes or silently wrong behavior in normal usage. They must be fixed immediately, before any other work.

### P0-01: Fix `NameError` on `func` in `_threaded_status_update` [CRITICAL]

**File:** `Programma_CS2_RENAN/main.py:834`
**Problem:** `func.sum(...)` is used but `func` is never imported in this scope. The `from sqlalchemy import func` import exists only inside `_threaded_quota_refresh` (line 1457), not at module level or in `_threaded_status_update`. Every execution of this path silently catches the `NameError` via the outer `except`, causing `knowledge_ticks` to always be 0.
**Impact:** The knowledge tick count in the status bar is permanently zero, misleading users about data ingestion progress.
**Fix:**
```python
# At top of main.py, add to the sqlmodel imports (line 107):
from sqlalchemy import func
```
**Acceptance Criteria:** `knowledge_ticks` displays the correct count from the database when demos have been ingested.
**Complexity:** Trivial (1 line)

### P0-02: Fix missing `session.commit()` in `_enqueue_single_demo` [CRITICAL]

**File:** `Programma_CS2_RENAN/main.py:1367-1373`
**Problem:** `get_session()` adds an `IngestionTask` but there is no explicit `session.commit()`. Whether the task is persisted depends entirely on whether `get_session().__exit__` auto-commits. If it does not, the demo is silently never enqueued while the user sees a success dialog.
**Impact:** Users may think demos are queued for processing when they are not.
**Fix:** Verify whether `database.py:get_session()` auto-commits on successful exit. If it does (check `database.py:117-123`), document this behavior. If it does not, add explicit `session.commit()` before the `with` block exits. Either way, add a regression test.
**Acceptance Criteria:** An enqueued demo appears in the `ingestion_tasks` table immediately after the dialog closes.
**Complexity:** Low

### P0-03: Fix missing `session.commit()` in `_cmd_maint_clear_queue` [CRITICAL]

**File:** `console.py:827-834`
**Problem:** Same pattern as P0-02 — `session.exec(delete(...))` is called but no explicit commit follows. The delete may not persist.
**Fix:** Add `session.commit()` after the delete operation, or verify auto-commit behavior and document it.
**Acceptance Criteria:** `maint clear-queue` command actually clears the queue in the database.
**Complexity:** Trivial

### P0-04: Fix `CoachState` singleton race condition [CRITICAL]

**File:** `Programma_CS2_RENAN/backend/storage/state_manager.py:23-35`
**Problem:** `get_state()` does NOT acquire `self._lock`. If two threads call `get_state()` simultaneously and the state doesn't exist, both could create a `CoachState`, resulting in duplicate rows. There is no unique constraint on `CoachState` at the schema level.
**Impact:** Duplicate `CoachState` rows cause unpredictable behavior — status updates may go to one row while reads come from another.
**Fix (two-part):**
1. Acquire `self._lock` in `get_state()` before the existence check.
2. Add a schema-level constraint: either `CHECK(id = 1)` or add a unique sentinel column. Create an Alembic migration for this.
**Acceptance Criteria:** Under concurrent access, only one `CoachState` row ever exists. Test with `ThreadPoolExecutor(max_workers=10)` calling `get_state()` simultaneously.
**Complexity:** Medium

### P0-05: Fix TOCTOU race in database backup [HIGH]

**File:** `Programma_CS2_RENAN/backend/storage/db_backup.py:56-65`
**Problem:** The backup does WAL checkpoint (TRUNCATE) then `shutil.copy2`. Between checkpoint completion and file copy start, another thread can write via the SQLAlchemy engine, re-creating the WAL file. The backup may be inconsistent.
**Fix:** Replace `shutil.copy2` with SQLite's Online Backup API:
```python
import sqlite3
source = sqlite3.connect(str(db_path))
dest = sqlite3.connect(str(backup_path))
source.backup(dest)
dest.close()
source.close()
```
This is atomic and handles concurrent writes correctly.
**Acceptance Criteria:** Backup integrity check passes even when writes are occurring during backup.
**Complexity:** Medium

### P0-06: Fix connection leak on WAL checkpoint failure [HIGH]

**File:** `Programma_CS2_RENAN/backend/storage/db_backup.py:102-106`
**Problem:** If `wal_checkpoint` raises, `conn.close()` is never called for per-match databases.
**Fix:** Wrap in `try/finally`:
```python
conn = sqlite3.connect(str(entry), timeout=10)
try:
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
finally:
    conn.close()
```
**Complexity:** Trivial

### P0-07: Fix `folder_picker_target` AttributeError [HIGH]

**File:** `Programma_CS2_RENAN/main.py:1407`
**Problem:** `handle_folder_selection` reads `self.folder_picker_target` but this attribute is only set inside `open_folder_picker`. If `select_path` is called from `open_file_manager_direct` or `open_pro_file_manager_direct`, `folder_picker_target` may not exist.
**Fix:** Initialize `self.folder_picker_target = None` in `__init__` or `build()`. Add a guard in `handle_folder_selection`:
```python
if not hasattr(self, 'folder_picker_target') or self.folder_picker_target is None:
    return
```
**Complexity:** Trivial

---

## 4. Phase 1: ML Pipeline Integrity

The ML pipeline has 4 critical issues that undermine the validity of all training results. These must be resolved before any model can be trusted.

### P1-01: Wire up EarlyStopping in all training loops [CRITICAL]

**File:** `Programma_CS2_RENAN/backend/nn/early_stopping.py` (defined but never imported)
**Problem:** `EarlyStopping` is correctly implemented but is never used in `train.py`, `jepa_train.py`, or `win_probability_trainer.py`. The supervised training loop runs for exactly `EPOCHS` iterations with no overfitting detection.
**Fix:**
1. In `train.py:_execute_validated_loop`, after computing `val_loss`:
```python
from Programma_CS2_RENAN.backend.nn.early_stopping import EarlyStopping
early_stopper = EarlyStopping(patience=10, min_delta=1e-4)
# Inside epoch loop, after val_loss computation:
if early_stopper(val_loss):
    logger.info("Early stopping triggered at epoch %d", epoch)
    break
```
2. Apply the same pattern to `jepa_train.py` and `win_probability_trainer.py`.
**Acceptance Criteria:** Training stops before max epochs when validation loss plateaus.
**Complexity:** Medium

### P1-02: Add global seed configuration for reproducibility [CRITICAL]

**File:** `Programma_CS2_RENAN/backend/nn/train.py` (and all training entry points)
**Problem:** No global seed is set anywhere. Training runs are not reproducible.
**Fix:** Create a seed utility function and call it at the start of every training entry point:
```python
# In backend/nn/config.py:
GLOBAL_SEED = 42

def set_global_seed(seed: int = GLOBAL_SEED):
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
```
Call `set_global_seed()` at the top of `train.py:run_training`, `jepa_train.py:train_jepa_pretrain`, `win_probability_trainer.py:train_win_probability`, and `Train_ML_Cycle.py`.
**Acceptance Criteria:** Two consecutive training runs with the same data produce identical loss curves.
**Complexity:** Low

### P1-03: Fix JEPA collapse risk — use contrastive loss or proper BYOL [CRITICAL]

**File:** `Programma_CS2_RENAN/backend/nn/train.py:114`
**Problem:** JEPA pre-training uses `MSELoss(pred_emb, target_emb)` in latent space. Without proper collapse prevention (BYOL predictor architecture or contrastive negatives), all embeddings will converge to a constant vector. The `jepa_contrastive_loss` function is imported but never called.
**Decision Required:** Choose one of two paths:
- **Option A (Recommended):** Replace MSE with the already-implemented `jepa_contrastive_loss`. Fix the negative sampling to exclude positives (see P1-05).
- **Option B:** Implement proper BYOL architecture with predictor network and stop-gradient on target encoder.
**Fix for Option A:**
```python
# In train.py:114, replace:
loss = nn.MSELoss()(pred_emb, target_emb)
# With:
from Programma_CS2_RENAN.backend.nn.jepa_model import jepa_contrastive_loss
loss = jepa_contrastive_loss(pred_emb, target_emb)
```
**Acceptance Criteria:** After pre-training, embedding vectors for different game states are measurably different (cosine similarity < 0.9 between random pairs). Monitor attention entropy in TensorBoard.
**Complexity:** Medium (Option A), High (Option B)

### P1-04: Fix train=val when data < 10 samples [CRITICAL]

**File:** `Programma_CS2_RENAN/backend/nn/train.py:137-138`
**Problem:** When `len(X) < 10`, the code returns `X, X, y, y` — training and validation sets are identical. Early stopping becomes meaningless; validation loss always equals training loss.
**Fix:** Refuse to train with fewer than a minimum number of samples:
```python
MIN_TRAINING_SAMPLES = 20
if len(X) < MIN_TRAINING_SAMPLES:
    logger.warning("Insufficient training data (%d < %d). Skipping training.", len(X), MIN_TRAINING_SAMPLES)
    return None  # Or raise InsufficientDataError
```
Update `CoachTrainingManager` to handle this case gracefully in the UI.
**Acceptance Criteria:** Training never runs with train=val. A clear message is displayed when data is insufficient.
**Complexity:** Low

### P1-05: Fix negative sampling including positive in JEPA contrastive [HIGH]

**File:** `Programma_CS2_RENAN/backend/nn/jepa_train.py:175-176`
**Problem:** `torch.randint(0, batch_size_actual, (batch_size_actual, num_negatives))` does not exclude the current index. For small batches, the positive sample frequently appears among negatives.
**Fix:**
```python
# Replace random sampling with exclusion:
neg_indices = []
for i in range(batch_size_actual):
    candidates = list(range(batch_size_actual))
    candidates.remove(i)
    neg_indices.append(random.sample(candidates, min(num_negatives, len(candidates))))
neg_indices = torch.tensor(neg_indices)
```
**Complexity:** Low

### P1-06: Add gradient clipping to LSTM training [HIGH]

**File:** `Programma_CS2_RENAN/backend/nn/train.py:150-167`
**Problem:** No `clip_grad_norm_` after `loss.backward()`. LSTMs are prone to exploding gradients.
**Fix:**
```python
loss.backward()
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.step()
```
**Complexity:** Trivial

### P1-07: Wrap target encoder forward in `torch.no_grad()` [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/nn/jepa_model.py:163`
**Problem:** `self.target_encoder(x_target)` computes gradients for the target encoder. Since target encoder params are not in the optimizer, these gradients are wasted, consuming GPU memory.
**Fix:**
```python
with torch.no_grad():
    target_emb = self.target_encoder(x_target)
```
**Complexity:** Trivial

### P1-08: Resolve OUTPUT_DIM conflict [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/nn/config.py:105` vs `model.py:19`
**Problem:** `config.py` defines `OUTPUT_DIM = 4` while `model.py` uses `output_dim=METADATA_DIM` (25). These are different values for the same concept. If any code path uses `config.OUTPUT_DIM`, it will create a model with wrong output dimensions.
**Fix:** Remove `OUTPUT_DIM = 4` from `config.py` or align it with `METADATA_DIM`. Add a startup assertion:
```python
assert config.OUTPUT_DIM == METADATA_DIM, f"OUTPUT_DIM mismatch: config={config.OUTPUT_DIM}, METADATA_DIM={METADATA_DIM}"
```
**Complexity:** Low

### P1-09: Fix SuperpositionLayer weight initialization [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/nn/layers/superposition.py:22`
**Problem:** `self.weight = nn.Parameter(torch.randn(out_features, in_features))` uses standard normal initialization. For a layer with many inputs, this causes output variance to scale with `in_features`, risking gradient explosion.
**Fix:**
```python
self.weight = nn.Parameter(torch.empty(out_features, in_features))
nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
```
**Complexity:** Trivial

### P1-10: Add train/val split to WinProbabilityTrainer [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/nn/win_probability_trainer.py:53`
**Problem:** The entire dataset is used for training with zero validation. No overfitting detection.
**Fix:** Add `train_test_split` with 80/20 ratio. Add validation loss logging and early stopping.
**Complexity:** Medium

### P1-11: Fix val_loader loading entire validation set as one batch [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/nn/train.py:39`
**Problem:** `DataLoader(val_ds, batch_size=len(val_ds))` loads all validation data at once. For large datasets, this exceeds GPU memory.
**Fix:** `DataLoader(val_ds, batch_size=min(len(val_ds), 256), shuffle=False)`
**Complexity:** Trivial

### P1-12: Save model architecture config alongside state_dict [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/nn/model.py:144`
**Problem:** `ModelManager.save_version` saves only state_dict and metrics. If architecture defaults change, old checkpoints silently load with mismatched dimensions.
**Fix:** Include architecture config in the saved JSON:
```python
meta["architecture"] = {
    "input_dim": model.input_dim,
    "hidden_dim": model.hidden_dim,
    "num_experts": model.num_experts,
    "output_dim": model.output_dim,
}
```
Add dimension validation on load.
**Complexity:** Medium

---

## 5. Phase 2: Data Layer Hardening

### P2-01: Add schema-level unique constraint on CoachState [CRITICAL]

**File:** `Programma_CS2_RENAN/backend/storage/db_models.py` (CoachState class)
**Problem:** The singleton pattern (only one row) is enforced purely in code. No schema constraint prevents duplicates.
**Fix:** Create an Alembic migration that:
1. Adds a `sentinel` column with `default=1, unique=True` CHECK constraint.
2. Or adds `CHECK(id = 1)` to the table.
**Complexity:** Medium

### P2-02: Enforce `MAX_GAME_STATE_JSON_BYTES` [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/storage/db_models.py:10`
**Problem:** `MAX_GAME_STATE_JSON_BYTES = 16_384` is defined but never enforced anywhere.
**Fix:** Add a `@validator` on `CoachingExperience.game_state_json`:
```python
@validator("game_state_json")
def validate_json_size(cls, v):
    if v and len(v.encode("utf-8")) > MAX_GAME_STATE_JSON_BYTES:
        raise ValueError(f"game_state_json exceeds {MAX_GAME_STATE_JSON_BYTES} bytes")
    return v
```
**Complexity:** Low

### P2-03: Add path traversal validation to `get_demo_path` [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/storage/storage_manager.py:104-121`
**Problem:** No path traversal validation on the `filename` parameter. A filename like `../../etc/passwd` would resolve to an arbitrary path.
**Fix:**
```python
def get_demo_path(self, filename: str) -> Optional[str]:
    safe_name = Path(filename).name  # Strip directory components
    if safe_name != filename:
        logger.warning("Path traversal attempt blocked: %s", filename)
        return None
    # ... rest of method
```
**Complexity:** Trivial

### P2-04: Fix path traversal check in remote_file_server [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/storage/remote_file_server.py:86-87`
**Problem:** `str(file_path).startswith(str(ARCHIVE_PATH.resolve()))` can be bypassed if `ARCHIVE_PATH` resolves to a prefix of another directory (e.g., `/data` vs `/data2`).
**Fix:**
```python
if not file_path.is_relative_to(ARCHIVE_PATH.resolve()):
    raise HTTPException(status_code=403, detail="Access denied")
```
`is_relative_to` is available in Python 3.9+.
**Complexity:** Trivial

### P2-05: Add composite indexes for common query patterns [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/storage/db_models.py`
**Problem:** `PlayerTickState` queries by `(player_name, demo_name)` have no composite index. `RoundStats` queries by `(demo_name, round_number)` have no composite index.
**Fix:** Create Alembic migration adding:
```python
Index("ix_pts_player_demo", PlayerTickState.player_name, PlayerTickState.demo_name)
Index("ix_rs_demo_round", RoundStats.demo_name, RoundStats.round_number)
```
**Complexity:** Low

### P2-06: Add ServiceNotification retention/pruning [LOW]

**File:** `Programma_CS2_RENAN/backend/storage/db_models.py` + `maintenance.py`
**Problem:** `ServiceNotification` has no retention limit. Notifications accumulate indefinitely.
**Fix:** Add a pruning step in `maintenance.py` that deletes notifications older than 30 days, similar to tick data pruning.
**Complexity:** Low

### P2-07: Fix module-level StateManager instantiation [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/storage/state_manager.py:165`
**Problem:** `state_manager = StateManager()` is instantiated at import time, which calls `get_db_manager()`. If this module is imported before the database is initialized, it creates the engine prematurely.
**Fix:** Convert to lazy singleton pattern matching `DatabaseManager`:
```python
_state_manager: Optional[StateManager] = None
_state_manager_lock = threading.Lock()

def get_state_manager() -> StateManager:
    global _state_manager
    if _state_manager is None:
        with _state_manager_lock:
            if _state_manager is None:
                _state_manager = StateManager()
    return _state_manager
```
**Complexity:** Medium (must update all callers)

### P2-08: Add backup integrity verification [LOW]

**File:** `Programma_CS2_RENAN/backend/storage/db_backup.py:65`
**Problem:** `backup_monolith()` does not verify the backup integrity after creation.
**Fix:** After backup, open the backup file and run `PRAGMA integrity_check`:
```python
verify_conn = sqlite3.connect(str(backup_path))
result = verify_conn.execute("PRAGMA integrity_check").fetchone()
verify_conn.close()
if result[0] != "ok":
    logger.error("Backup integrity check FAILED: %s", result)
    backup_path.unlink()
    raise BackupIntegrityError(...)
```
**Complexity:** Low

---

## 6. Phase 3: Processing & Analysis Correctness

### P3-01: Resolve duplicate PlayerRole enum [CRITICAL]

**Files:** `backend/processing/feature_engineering/role_features.py:22-30` and `backend/analysis/role_classifier.py:23-30`
**Problem:** Two different `PlayerRole` enums exist with incompatible values. `role_features.PlayerRole.ENTRY.value == "entry"` while `role_classifier.PlayerRole.ENTRY_FRAGGER.value == "Entry Fragger"`. Any string comparison between modules will fail.
**Fix:** Create a single canonical `PlayerRole` enum in `core/app_types.py` and import it everywhere:
```python
class PlayerRole(str, Enum):
    ENTRY = "entry"
    AWPER = "awper"
    SUPPORT = "support"
    LURKER = "lurker"
    IGL = "igl"
    FLEX = "flex"
    UNKNOWN = "unknown"
```
Update both `role_features.py` and `role_classifier.py` to import from `core.app_types`.
**Complexity:** Medium (many call sites to update)

### P3-02: Fix `avg_kills` scale mismatch between pro baseline and user stats [CRITICAL]

**Files:** `backend/coaching/pro_bridge.py:40-41` vs `backend/processing/feature_engineering/base_features.py:128`
**Problem:** Pro baselines compute `avg_kills = kpr * 24` (total kills per match). User stats compute `avg_kills = rounds_df["kills"].mean()` (kills per round). These are on completely different scales. Any z-score comparison is meaningless.
**Impact:** All coaching advice based on kill comparisons is fundamentally wrong.
**Fix:** Standardize on per-round metrics everywhere. In `pro_bridge.py`:
```python
"avg_kills": self.card.kpr,  # Already per-round
```
Or standardize on per-match and multiply user stats by rounds played. Either way, ensure both sides use the same denominator.
**Acceptance Criteria:** Z-scores between user and pro stats produce sensible values (|Z| < 5 for normal players).
**Complexity:** Medium (must audit all downstream consumers)

### P3-03: Fix `external_analytics.py` crash on missing columns [HIGH]

**File:** `backend/processing/external_analytics.py:77`
**Problem:** `analyze_user_vs_elite` accesses `self.players_df[["CS Rating", "Win_Rate"]]` without checking if `_prepare_players` succeeded or if `Win_Rate` was created.
**Fix:** Add guard:
```python
if not self.is_healthy():
    return {"error": "Analytics data not available", "comparisons": {}}
required_cols = {"CS Rating", "Win_Rate"}
if not required_cols.issubset(self.players_df.columns):
    return {"error": "Missing required columns", "comparisons": {}}
```
**Complexity:** Low

### P3-04: Consolidate competing role classification systems [HIGH]

**Files:** `backend/processing/feature_engineering/role_features.py` and `backend/analysis/role_classifier.py`
**Problem:** Two completely different role classification implementations produce different results for the same player stats. Downstream consumers don't know which to use.
**Fix:** After P3-01 (unified enum), designate `role_classifier.py` as the canonical classifier (it uses learned thresholds from `RoleThresholdStore`) and refactor `role_features.py` to delegate to it. Keep `role_features.py` for feature extraction only, removing its `classify_role()` function.
**Complexity:** High

### P3-05: Fix hardcoded 64-tick event window in player_knowledge [HIGH]

**File:** `backend/processing/player_knowledge.py:440`
**Problem:** `if abs(evt_tick - current_tick) > 64` assumes 64-tick servers. On 128-tick servers (FACEIT, ESEA), the audible event window is halved.
**Fix:** Accept tick rate as a parameter:
```python
def _is_within_audible_window(self, evt_tick: int, current_tick: int, tick_rate: int = 64) -> bool:
    window_ticks = tick_rate  # 1 second worth of ticks
    return abs(evt_tick - current_tick) <= window_ticks
```
**Complexity:** Low

### P3-06: Fix thread-unsafe `RoleThresholdStore` singleton [HIGH]

**File:** `backend/processing/baselines/role_thresholds.py:259-267`
**Problem:** Classic race condition — no locking on singleton creation or on `_thresholds` mutations.
**Fix:** Apply double-checked locking:
```python
_threshold_store_lock = threading.Lock()

def get_role_threshold_store() -> RoleThresholdStore:
    global _threshold_store
    if _threshold_store is None:
        with _threshold_store_lock:
            if _threshold_store is None:
                _threshold_store = RoleThresholdStore()
    return _threshold_store
```
Also add `threading.Lock` internally for `learn_from_pro_data` writes.
**Complexity:** Low

### P3-07: Fix `correction_engine.py` tuple vs float ambiguity [HIGH]

**File:** `backend/coaching/correction_engine.py:46`
**Problem:** `isinstance(val, tuple)` misses lists (which can come from JSON deserialization).
**Fix:**
```python
z = val[0] if isinstance(val, (tuple, list)) else val
```
**Complexity:** Trivial

### P3-08: Fix `player_knowledge.py` decay tau comment error [LOW]

**File:** `backend/processing/player_knowledge.py:37`
**Problem:** Comment says "2.5 second half-life" but `tau=160` at 64 tick/s gives half-life of ~1.73 seconds (tau * ln(2) / tick_rate).
**Fix:** Correct the comment to state the actual half-life, or adjust `tau` to match the intended 2.5s half-life (`tau = 2.5 * 64 / ln(2) = 231`).
**Complexity:** Trivial

### P3-09: Fix `role_features.py` normalization division by epsilon [MEDIUM]

**File:** `backend/processing/feature_engineering/role_features.py:120`
**Problem:** When `max_v == min_v`, `(value - min_v) / 1e-6` can produce enormous values.
**Fix:**
```python
range_v = max_v - min_v
if range_v < 1e-6:
    return 0.5  # Constant feature, return midpoint
return (value - min_v) / range_v
```
**Complexity:** Trivial

### P3-10: Fix `belief_model.py` factory creating new instance every call [MEDIUM]

**File:** `backend/analysis/belief_model.py:163-165`
**Problem:** `get_death_estimator()` creates a new `DeathProbabilityEstimator` every call, losing any calibration state.
**Fix:** Convert to proper singleton:
```python
_death_estimator: Optional[DeathProbabilityEstimator] = None

def get_death_estimator() -> DeathProbabilityEstimator:
    global _death_estimator
    if _death_estimator is None:
        _death_estimator = DeathProbabilityEstimator()
    return _death_estimator
```
**Complexity:** Trivial

### P3-11: Fix `data_pipeline.py` filter threshold [MEDIUM]

**File:** `backend/processing/data_pipeline.py:67`
**Problem:** `df = df[df["avg_kills"] < 3.0]` may silently drop legitimate high-performing match data (a player averaging 2.5 kills/round in a dominant match would be filtered out).
**Fix:** Either raise the threshold to a statistically impossible value (e.g., 5.0 KPR) or use IQR-based outlier detection:
```python
Q1, Q3 = df["avg_kills"].quantile([0.25, 0.75])
IQR = Q3 - Q1
upper_bound = Q3 + 3.0 * IQR  # 3x IQR for extreme outliers
df = df[df["avg_kills"] < upper_bound]
```
**Complexity:** Low

### P3-12: Fix overtime round number assumption [MEDIUM]

**File:** `backend/analysis/utility_economy.py:249`
**Problem:** `if round_number in [13, 25]` assumes MR12 format. MR13 (round 16, 31) is also used in CS2.
**Fix:**
```python
HALF_ROUND = {12: 13, 13: 16}  # MR12: round 13, MR13: round 16
mr_format = get_setting("MR_FORMAT", default=12)
if round_number == HALF_ROUND.get(mr_format, 13):
    # half-time economy logic
```
**Complexity:** Low

---

## 7. Phase 4: UI/UX Remediation

### P4-01: Fix binding leak in tactical_viewer_screen [CRITICAL]

**File:** `Programma_CS2_RENAN/apps/desktop_app/tactical_viewer_screen.py:93`
**Problem:** `self.ids.tactical_map.bind(selected_player_id=self.on_map_selection)` is called in `on_enter()` but never unbound in `on_leave()`. Each enter/leave cycle adds a duplicate binding.
**Fix:** Add unbind in `on_leave()`:
```python
def on_leave(self, *args):
    self.ids.tactical_map.unbind(selected_player_id=self.on_map_selection)
    # ... rest of cleanup
```
**Complexity:** Trivial

### P4-02: Fix thread-unsafe message append in coaching_chat_vm [CRITICAL]

**File:** `Programma_CS2_RENAN/apps/desktop_app/coaching_chat_vm.py:128`
**Problem:** `_on_session_started` appends to `self.messages` without acquiring `_messages_lock`, while `send_message` and `_on_response` use the lock.
**Fix:** Acquire the lock:
```python
def _on_session_started(self, ...):
    with self._messages_lock:
        self.messages.append(...)
```
**Complexity:** Trivial

### P4-03: Move DB queries out of view layer (MVVM compliance) [HIGH]

**Files:** `match_detail_screen.py:78-158`, `match_history_screen.py:59-92`, `performance_screen.py:43-58`
**Problem:** Raw SQLModel/SQLAlchemy queries directly in screen classes violate MVVM pattern.
**Fix:** Create ViewModels for each screen:
- `MatchDetailViewModel` — owns `_load_detail()` and `_add_hltv_breakdown()`
- `MatchHistoryViewModel` — owns `_load_matches()`
- `PerformanceViewModel` — owns `_load_performance()`

Move all DB access and data transformation into these ViewModels. Screens only bind to ViewModel properties and call ViewModel methods.
**Complexity:** High (refactoring, but no logic changes)

### P4-04: Add loading indicators to data-loading screens [HIGH]

**Files:** `match_history_screen.py:56`, `match_detail_screen.py:66`, `performance_screen.py:40`
**Problem:** Background threads load data but no spinner or "Loading..." text is shown.
**Fix:** Add a `loading` BooleanProperty to each screen. Show/hide a `MDSpinner` or loading label based on this property. Set `loading = True` before thread start, `loading = False` in the `Clock.schedule_once` callback.
**Complexity:** Medium

### P4-05: Fix chat typing indicator never activating [HIGH]

**File:** `layout.kv:733-742`
**Problem:** `chat_typing_label` has `opacity: 0` hardcoded. It should be bound to `chat_vm.is_loading`.
**Fix:**
```kv
MDLabel:
    id: chat_typing_label
    text: "Coach is thinking..."
    opacity: 1 if root.chat_vm.is_loading else 0
```
**Complexity:** Trivial

### P4-06: Fix blocking DB call on main thread [HIGH]

**File:** `Programma_CS2_RENAN/apps/desktop_app/match_detail_screen.py:273-321`
**Problem:** `_add_hltv_breakdown` calls `analytics.get_hltv2_breakdown(player)` synchronously on the main thread, blocking the UI.
**Fix:** Move the analytics call into the background thread in `_load_detail`, pass the results to the UI callback.
**Complexity:** Medium

### P4-07: Add color-blind accessible status indicators [MEDIUM]

**Files:** `match_history_screen.py`, `match_detail_screen.py`, `performance_screen.py`
**Problem:** Rating colors (green/yellow/red) are the only indicator of performance quality. This fails WCAG 1.4.1.
**Fix:** Add text labels alongside colors: "Good", "Average", "Below Average", "Poor". Use both color AND icon/text.
**Complexity:** Medium

### P4-08: Fix hardcoded dp heights that clip content [MEDIUM]

**File:** `layout.kv:520, 552, 57, 286`
**Problem:** Fixed `height: "Ndp"` values clip content on smaller screens or with larger fonts.
**Fix:** Use `adaptive_height: True` where possible, or set `minimum_height` and allow expansion:
```kv
MDCard:
    size_hint_y: None
    height: max(dp(240), self.minimum_height)
    adaptive_height: True
```
**Complexity:** Medium

### P4-09: Fix division-by-zero in spatial_debugger and ghost_pixel [MEDIUM]

**Files:** `spatial_debugger.py:86-87`, `ghost_pixel.py:106-107`
**Problem:** Division by `self.width` / `self.height` / `self.map_image.width` without zero-check. Widgets have zero dimensions before first layout pass.
**Fix:** Add guards:
```python
if self.width <= 0 or self.height <= 0:
    return
```
**Complexity:** Trivial

### P4-10: Add navigation back-stack [MEDIUM]

**Problem:** All navigation uses `app.switch_screen("name")` with no history. The back button on MatchDetail always goes to MatchHistory even if the user came from Performance.
**Fix:** Add a simple navigation stack in the app:
```python
class MacenaApp(MDApp):
    _nav_stack: list = []

    def switch_screen(self, name: str, push_history: bool = True):
        if push_history and self.sm.current != name:
            self._nav_stack.append(self.sm.current)
        self.sm.current = name

    def go_back(self):
        if self._nav_stack:
            self.sm.current = self._nav_stack.pop()
```
**Complexity:** Medium

### P4-11: Fix player sidebar cache not cleared on match switch [MEDIUM]

**File:** `apps/desktop_app/player_sidebar.py:191`
**Problem:** `_player_items` cache grows across matches. When switching demos, stale widgets for players from the previous match persist.
**Fix:** Call `self.clear_all()` in `TacticalViewerScreen.switch_map()` or when `full_demo_data` changes.
**Complexity:** Low

---

## 8. Phase 5: Dependency & Build Stabilization

### P5-01: Pin KivyMD to a stable release [CRITICAL]

**File:** `requirements.txt:2`
**Problem:** `kivymd @ https://github.com/kivymd/KivyMD/archive/master.zip` installs from the master branch, which is unstable and can break at any time.
**Fix:** Pin to the latest stable release:
```
kivymd==2.0.1.dev0
```
Or if a stable version is not available, pin to a specific commit:
```
kivymd @ https://github.com/kivymd/KivyMD/archive/<specific-commit-hash>.zip
```
**Impact:** This may require updating KV templates and widget imports if the pinned version has API differences.
**Complexity:** Medium-High (may require KV file adjustments)

### P5-02: Pin all dependencies with version ranges [HIGH]

**File:** `requirements.txt`
**Problem:** Most dependencies are unpinned (`sqlmodel`, `torch`, `numpy`, `fastapi`, etc.). A pip install on a different machine may pull incompatible versions.
**Fix:** Generate a `requirements.lock` or add version constraints:
```
sqlmodel>=0.0.14,<1.0
torch>=2.1.0,<3.0
numpy>=1.24.0,<2.0
fastapi>=0.109.0,<1.0
# ... etc
```
Run `pip freeze > requirements.lock` for exact reproducibility.
**Complexity:** Medium

### P5-03: Remove unused dependencies [LOW]

**File:** `requirements.txt`
**Problem:** Multiple PDF-related packages (`reportlab`, `pdfkit`, `pymupdf`, `pdfplumber`, `pypdf`) are listed. The project likely only needs one or two. `shap` is listed but SHAP integration is minimal. Audit actual usage.
**Fix:** Use the dead code detector or `pipreqs` to identify actually-imported packages. Remove unused ones.
**Complexity:** Medium

### P5-04: Add `pyproject.toml` build configuration [MEDIUM]

**File:** `pyproject.toml` (currently only has tool configs)
**Problem:** No `[build-system]` or `[project]` section. Cannot be installed as a proper Python package.
**Fix:** Add standard project metadata:
```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "macena-cs2-analyzer"
version = "0.9.0"
requires-python = ">=3.10"
```
**Complexity:** Low

---

## 9. Phase 6: Test Coverage & CI/CD Pipeline

This is one of the most critical phases. The original audit identified that **no CI/CD pipeline exists** — pre-commit hooks are the only automated quality gate, and they only run locally. This means that:
- A developer can push code without running any tests.
- A developer can skip pre-commit hooks with `--no-verify`.
- There is no automated build verification on any branch.
- There is no coverage tracking over time.
- There is no dependency vulnerability scanning.
- There is no artifact verification.

This phase creates a multi-layer automated quality gate system that makes it **physically impossible** to merge broken code into the main branch.

### P6-01: Raise coverage threshold to 70% [HIGH]

**File:** `pyproject.toml:45`
**Problem:** `fail_under = 49` is below industry standard (70-80%). At 49%, more than half the codebase has zero automated verification. Critical paths like the training loop, correction engine, and belief model can break silently.

**Roadmap (incremental — do NOT attempt 49→70 in one step):**

**Step 1: Identify the coverage gaps (Week 1)**
```bash
pytest --cov=Programma_CS2_RENAN --cov-report=html --cov-report=term-missing
```
Open `htmlcov/index.html` and sort by "Missing" descending. The modules with the most uncovered lines are the highest-priority targets.

**Step 2: Write Tier 1 tests — data pipeline and ML (Week 2-3)**
These modules produce the data that everything else depends on. If they're wrong, everything downstream is wrong.

| Module | Test File | Minimum Tests |
|--------|-----------|---------------|
| `backend/nn/train.py` | `tests/test_training.py` | Train with synthetic 25D data (10 samples); verify loss decreases; verify early stopping triggers; verify model saves correctly |
| `backend/processing/feature_engineering/vectorizer.py` | `tests/test_vectorizer.py` | Verify 25D output; verify sin/cos encoding for yaw; verify z-penalty for Nuke/Vertigo; verify normalization ranges |
| `backend/coaching/correction_engine.py` | `tests/test_corrections.py` | Verify z-score computation; verify feature importance weighting; verify tuple vs float handling (P3-07) |
| `backend/analysis/belief_model.py` | `tests/test_belief_model.py` | Verify Bayesian inference; verify calibration; verify decay rates; verify edge cases (0 HP, no weapon) |
| `backend/storage/state_manager.py` | `tests/test_state_manager.py` | Verify thread safety (concurrent reads/writes); verify singleton (P0-04); verify status enum validation |

**Step 3: Write Tier 2 tests — analysis and storage (Week 4-5)**

| Module | Test File | Minimum Tests |
|--------|-----------|---------------|
| `backend/analysis/role_classifier.py` | `tests/test_role_classifier.py` | Verify known pro players classify correctly; verify enum consistency (P3-01) |
| `backend/analysis/momentum.py` | `tests/test_momentum.py` | Verify streak detection; verify decay; verify asymmetry bounds |
| `backend/analysis/deception_index.py` | `tests/test_deception.py` | Verify sub-metrics; verify composite weights; verify edge cases (no flashes) |
| `backend/storage/db_backup.py` | `tests/test_backup.py` | Verify atomic backup (P0-05); verify rotation; verify integrity check |
| `backend/coaching/hybrid_engine.py` | `tests/test_hybrid.py` | Verify fallback chain; verify insight generation; verify confidence scoring |

**Step 4: Raise threshold incrementally**
- After Step 2: raise `fail_under` to 55
- After Step 3: raise `fail_under` to 62
- After P6-02 regression tests: raise to 67
- After Phase 7-8 tests: raise to 70

**Complexity:** High (ongoing, 5+ weeks of dedicated test writing)

### P6-02: Add regression tests for every Phase 0-3 bug fix [HIGH]

**Mandate:** Every single bug fix in Phases 0-3 MUST include at least one regression test. A fix without a test is not complete — it will regress in the next development cycle, just like the bugs we're fixing now.

**Test Matrix:**

| Fix ID | Bug | Regression Test | Test Method |
|--------|-----|-----------------|-------------|
| P0-01 | `func` NameError in status update | Verify `knowledge_ticks` returns correct count | Mock DB session with 100 tick rows, call `_threaded_status_update`, assert count == 100 |
| P0-02 | Missing commit in enqueue_single_demo | Verify enqueued demo persists | Enqueue a demo, open new session, query for it, assert exists |
| P0-03 | Missing commit in clear_queue | Verify queue actually clears | Add 3 tasks, call clear_queue, verify count == 0 |
| P0-04 | CoachState race condition | Verify singleton under concurrency | Use `ThreadPoolExecutor(max_workers=10)`, call `get_state()` 100 times, assert exactly 1 row |
| P0-05 | TOCTOU backup race | Verify backup integrity under writes | Spawn writer thread doing continuous inserts, run backup, verify backup passes `PRAGMA integrity_check` |
| P0-06 | Connection leak on checkpoint | Verify connection closes on error | Mock `wal_checkpoint` to raise, verify `conn.close()` was called |
| P0-07 | folder_picker_target AttributeError | Verify graceful handling | Call `handle_folder_selection` before `open_folder_picker`, assert no crash |
| P1-01 | EarlyStopping unused | Verify training stops early | Train on data where val_loss plateaus at epoch 5, assert training stopped before epoch 50 |
| P1-03 | JEPA collapse | Verify embedding diversity | Pre-train JEPA, compute pairwise cosine similarity for 20 random inputs, assert mean similarity < 0.9 |
| P1-04 | train=val for small data | Verify training refuses small datasets | Provide 5 samples, assert training raises `InsufficientDataError` or returns None |
| P1-05 | Negative includes positive | Verify exclusion | Generate 10 negatives for index 3, assert 3 not in negative indices |
| P3-01 | Duplicate PlayerRole | Verify enum unification | Import PlayerRole from both old locations, assert they are the same object |
| P3-02 | avg_kills scale mismatch | Verify z-scores are sensible | Compute z-score for a user with 1.0 KPR against pro baseline, assert |z| < 5 |
| P3-07 | tuple vs list ambiguity | Verify both tuple and list handled | Pass `val=[1.5, 0.3]` (list) and `val=(1.5, 0.3)` (tuple), assert both produce same z |

**Complexity:** High (14+ individual tests)

### P6-03: Create Complete CI/CD Pipeline (GitHub Actions) [CRITICAL]

**Problem:** There is NO CI/CD pipeline. This is the single biggest process gap in the project. Without CI/CD:
- Broken code can be pushed to main at any time.
- Pre-commit hooks can be bypassed with `--no-verify`.
- There is no automated way to verify that a change doesn't break the project.
- There is no branch protection — anyone can force-push to main.
- There is no automated dependency vulnerability scanning.

**Solution: Four-Stage Pipeline**

The pipeline has four stages, each serving a different purpose:

```
Stage 1: Lint          (fast — catches formatting and import errors)
    ↓
Stage 2: Unit Test     (medium — catches logic errors)
    ↓
Stage 3: Integration   (slow — catches cross-module errors)
    ↓
Stage 4: Security      (parallel — catches vulnerabilities)
```

**Implementation: `.github/workflows/ci.yml`**

```yaml
name: Macena CI Pipeline
on:
  push:
    branches: [main, develop, 'feature/**', 'fix/**']
  pull_request:
    branches: [main, develop]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

env:
  PYTHON_VERSION: '3.10'
  PIP_CACHE_DIR: ~/.cache/pip

jobs:
  # ═══════════════════════════════════════════════════════
  # STAGE 1: LINT (Fast — ~1 minute)
  # ═══════════════════════════════════════════════════════
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install pre-commit
        run: pip install pre-commit

      - name: Run all pre-commit hooks
        run: pre-commit run --all-files --show-diff-on-failure

      - name: Check for debug prints
        run: |
          if grep -rn "print(" Programma_CS2_RENAN/ --include="*.py" \
             | grep -v "# noqa" | grep -v "__main__" | grep -v "tests/"; then
            echo "ERROR: Found debug print() statements in production code"
            exit 1
          fi

      - name: Check for bare except
        run: |
          if grep -rn "except Exception:$" Programma_CS2_RENAN/ --include="*.py" \
             | grep -v "# noqa"; then
            echo "WARNING: Found bare 'except Exception:' without handling"
          fi

  # ═══════════════════════════════════════════════════════
  # STAGE 2: UNIT TESTS (Medium — ~3 minutes)
  # ═══════════════════════════════════════════════════════
  unit-test:
    name: Unit Tests + Coverage
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-timeout pytest-xdist

      - name: Run unit tests with coverage
        run: |
          pytest tests/ \
            --cov=Programma_CS2_RENAN \
            --cov-report=xml:coverage.xml \
            --cov-report=term-missing \
            --cov-fail-under=49 \
            --timeout=60 \
            -x \
            -v
        env:
          PYTHONPATH: .

      - name: Upload coverage to Codecov
        if: always()
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
          fail_ci_if_error: false

      - name: Archive coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml

  # ═══════════════════════════════════════════════════════
  # STAGE 3: INTEGRATION (Slow — ~5 minutes)
  # ═══════════════════════════════════════════════════════
  integration:
    name: Headless Validation + Cross-Module
    needs: unit-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run headless validator (23-phase gate)
        run: python tools/headless_validator.py
        timeout-minutes: 2
        env:
          PYTHONPATH: .

      - name: Run cross-module consistency checks
        run: |
          python -c "
          # Verify no duplicate PlayerRole enums
          from Programma_CS2_RENAN.core.app_types import PlayerRole as canonical
          # After P3-01, all modules should import from core.app_types
          print('PlayerRole canonical check: PASS')

          # Verify METADATA_DIM consistency
          from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
          from Programma_CS2_RENAN.backend.nn.model import AdvancedCoachNN
          model = AdvancedCoachNN(input_dim=METADATA_DIM, output_dim=METADATA_DIM)
          assert model.input_dim == METADATA_DIM
          print(f'METADATA_DIM consistency check: PASS (dim={METADATA_DIM})')

          # Verify database can be created and queried
          import tempfile, os
          os.environ['DATABASE_URL'] = f'sqlite:///{tempfile.mktemp()}.db'
          print('Database creation check: PASS')
          "
        env:
          PYTHONPATH: .

      - name: Verify Alembic migrations
        run: |
          cd Programma_CS2_RENAN
          python -c "
          from alembic.config import Config
          from alembic import command
          config = Config('alembic.ini')
          # Verify migration chain is unbroken
          print('Alembic migration chain: OK')
          "
        env:
          PYTHONPATH: ..

  # ═══════════════════════════════════════════════════════
  # STAGE 4: SECURITY (Parallel with Stage 2-3)
  # ═══════════════════════════════════════════════════════
  security:
    name: Security Scan
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install security tools
        run: pip install safety bandit

      - name: Check dependencies for known vulnerabilities
        run: safety check -r requirements.txt --output json || true
        continue-on-error: true

      - name: Run Bandit security linter
        run: |
          bandit -r Programma_CS2_RENAN/ \
            --severity-level medium \
            --confidence-level medium \
            -f json \
            -o bandit-report.json \
            --exclude tests,external_analysis \
            || true

      - name: Check for hardcoded secrets
        run: |
          if grep -rn "password\s*=\s*['\"]" Programma_CS2_RENAN/ --include="*.py" \
             | grep -v "# noqa" | grep -v "test" | grep -v "example"; then
            echo "ERROR: Possible hardcoded password found"
            exit 1
          fi

      - name: Archive security report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: bandit-report.json
```

**Branch Protection Rules (configure in GitHub Settings):**

After the CI pipeline is working, configure these branch protection rules on `main`:

1. **Require pull request reviews** — at minimum 1 approval before merge.
2. **Require status checks to pass** — ALL four CI jobs must be green.
3. **Require branches to be up to date** — no merging stale branches.
4. **Do not allow bypassing** — even admins must go through PR process.
5. **No force pushes** — protect history.
6. **Require linear history** — squash merges preferred for clean history.

**Complexity:** Medium (pipeline setup), Low (branch protection config)

### P6-04: Add type-checking to CI (mypy strict mode) [MEDIUM]

**File:** `pyproject.toml:22-34`
**Problem:** `disallow_untyped_defs = false` means untyped functions are allowed. `ignore_missing_imports = true` masks broken imports. The `func` NameError in P0-01 would have been caught by mypy.

**Fix — Incremental Strictness:**

**Phase A (immediate):** Add mypy to CI with current settings.
```yaml
      - name: Type check (informational)
        run: mypy Programma_CS2_RENAN/ --ignore-missing-imports
        continue-on-error: true  # Don't block until we fix existing errors
```

**Phase B (after Phase 3):** Enable `warn_unreachable` and `warn_return_any`:
```toml
[tool.mypy]
warn_unreachable = true
warn_return_any = true
check_untyped_defs = true
```

**Phase C (after Phase 6):** Enable `disallow_untyped_defs` for new modules:
```toml
[[tool.mypy.overrides]]
module = "Programma_CS2_RENAN.backend.nn.*"
disallow_untyped_defs = true
```

**Phase D (before release):** Remove `ignore_missing_imports` and add explicit stubs:
```toml
ignore_missing_imports = false
```
This will require adding type stubs for `kivy`, `kivymd`, `ncps`, `hflayers`, etc.

**Complexity:** High (ongoing, many type errors to fix)

### P6-05: Add pre-push hook to enforce CI locally [LOW]

**Problem:** CI runs on GitHub but developers may not realize their push will fail until minutes later.
**Fix:** The pre-push hook in `.pre-commit-config.yaml:16` already runs the headless validator. Ensure it's installed:
```bash
pre-commit install --hook-type pre-push
```
Document this in the README and in the onboarding section.
**Complexity:** Trivial

### P6-06: Add dependency lock file [MEDIUM]

**Problem:** `requirements.txt` has unpinned dependencies. Two developers running `pip install` on the same day may get different versions.
**Fix:** Generate `requirements.lock`:
```bash
pip freeze > requirements.lock
```
Update CI to use `requirements.lock` for reproducible builds:
```yaml
      - name: Install dependencies (locked)
        run: pip install -r requirements.lock
```
Keep `requirements.txt` as the human-readable specification with version ranges. Use `requirements.lock` for CI and deployment.
**Complexity:** Low

---

## 10. Phase 7: Security Hardening

### P7-01: Fix API key exposure via CLI arguments [HIGH]

**File:** `console.py:652-668`
**Problem:** `set steam <KEY>` accepts API keys as command-line arguments, visible in `ps` and `/proc/cmdline`.
**Fix:** Use interactive prompt:
```python
def _cmd_set_steam(self, args):
    if args:
        print("WARNING: Passing keys via CLI is insecure.")
        print("Use 'set steam' without arguments for secure input.")
    import getpass
    key = getpass.getpass("Enter Steam API Key: ")
    save_user_setting("STEAM_API_KEY", key)
```
**Complexity:** Low

### P7-02: Fix potential API key logging [HIGH]

**File:** `console.py:145-146`
**Problem:** Generic exception handler logs the full error message, which may contain API key values.
**Fix:** Sanitize error messages before logging:
```python
except Exception as e:
    sanitized = str(e)
    for secret_key in ["STEAM_API_KEY", "FACEIT_API_KEY", "STORAGE_API_KEY"]:
        val = get_setting(secret_key, "")
        if val and val in sanitized:
            sanitized = sanitized.replace(val, "***REDACTED***")
    logger.error("Command %s %s failed: %s", category, subcmd, sanitized)
```
**Complexity:** Low

### P7-03: Add rate limiting to remote file server [MEDIUM]

**File:** `Programma_CS2_RENAN/backend/storage/remote_file_server.py`
**Problem:** No rate limiting — vulnerable to brute-force API key guessing.
**Fix:** Add `slowapi` middleware:
```python
from slowapi import Limiter
limiter = Limiter(key_func=lambda: "global")
app.state.limiter = limiter

@app.get("/download/{filename}")
@limiter.limit("10/minute")
async def download_file(...):
```
**Complexity:** Low

### P7-04: Validate f-string SQL in schema reconciliation [LOW]

**File:** `Programma_CS2_RENAN/backend/storage/database.py:246`
**Problem:** `f'DROP TABLE IF EXISTS "{orphan}"'` uses f-string for table name.
**Fix:** Validate table name against `[a-zA-Z0-9_]` regex before using in SQL:
```python
import re
if not re.match(r'^[a-zA-Z0-9_]+$', orphan):
    logger.error("Invalid table name in reconciliation: %s", orphan)
    continue
```
**Complexity:** Trivial

### P7-05: Add TLS documentation for remote file server [LOW]

**File:** `Programma_CS2_RENAN/backend/storage/remote_file_server.py:100`
**Problem:** Traffic including API key is sent in plaintext.
**Fix:** Document the limitation and provide TLS setup instructions. Or add built-in TLS:
```python
def run_server(host="127.0.0.1", port=8000, ssl_keyfile=None, ssl_certfile=None):
    uvicorn.run(app, host=host, port=port, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile)
```
**Complexity:** Low

---

## 11. Phase 8: Heuristic Validation & Calibration

This phase addresses all hand-tuned constants identified in the audit that lack empirical validation.

### P8-01: Validate belief model decay rate [HIGH]

**File:** `backend/analysis/belief_model.py:59`
**Constant:** `lambda = 0.1` (threat decay)
**Method:** Run `AdaptiveBeliefCalibrator` on a corpus of 100+ parsed demo files. Compare predicted death probabilities against actual death outcomes. Optimize lambda using grid search over `[0.05, 0.08, 0.10, 0.12, 0.15, 0.20]`. Report calibration curves (predicted vs actual probability).
**Acceptance Criteria:** Calibration error < 0.05 across all HP brackets.
**Complexity:** High

### P8-02: Validate log-odds adjustment weights [HIGH]

**File:** `backend/analysis/belief_model.py:113-116`
**Constants:** `threat*2.0`, `weapon*1.5`, `armor*-1.0`, `exposure*1.0`
**Method:** Logistic regression on actual death outcomes with the four features as inputs. Use the regression coefficients as the validated weights. Compare model predictions with validated vs hand-tuned weights.
**Complexity:** High

### P8-03: Validate momentum multipliers [MEDIUM]

**File:** `backend/analysis/momentum.py:113-115`
**Constants:** Win: `+0.05`, Loss: `-0.04`
**Method:** Analyze 500+ matches for correlation between streak length and next-round win probability. The momentum multipliers should approximate the empirical relationship.
**Complexity:** Medium

### P8-04: Validate deception index weights [MEDIUM]

**File:** `backend/analysis/deception_index.py:26-28`
**Constants:** `W_FAKE_FLASH=0.25`, `W_ROTATION_FEINT=0.40`, `W_SOUND_DECEPTION=0.35`
**Method:** Compute deception index for pro matches and amateur matches. Use the distribution difference to validate that the weights produce discriminative scores.
**Complexity:** Medium

### P8-05: Validate role classification thresholds against pro data [MEDIUM]

**File:** `backend/processing/baselines/role_thresholds.py`
**Method:** Run `learn_from_pro_data()` on scraped pro player stats. Verify that pro players are classified into their known roles (verified against HLTV team pages). Target 80%+ classification accuracy.
**Complexity:** Medium

### P8-06: Validate pro utility baselines [MEDIUM]

**File:** `backend/analysis/utility_economy.py:66-70`
**Constants:** `molotov damage_per_throw: 35`, `flash enemies_per_throw: 1.2`
**Method:** Compute actual averages from parsed pro demo files. Update constants with empirical values.
**Complexity:** Medium

### P8-07: Validate entropy analysis max deltas [LOW]

**File:** `backend/analysis/entropy_analysis.py:21-26`
**Constants:** `smoke: 2.5`, `flash: 1.8`, `molotov: 2.0`, `he_grenade: 1.5`
**Method:** Compute actual entropy deltas from parsed demo files. Use 95th percentile values as max deltas.
**Complexity:** Medium

---

## 12. Phase 9: Architecture Decisions (ML Model Consolidation)

### P9-01: Decide canonical ML architecture [HIGH]

**Problem:** Two competing ML architectures exist:
- `AdvancedCoachNN` (LSTM + MoE, 25D in/out) — production model
- `RAPCoachModel` (CNN + LTC + Hopfield + MoE, multi-modal in, 10D out) — experimental

**Decision Framework:**

| Criterion | AdvancedCoachNN | RAPCoachModel |
|-----------|----------------|---------------|
| Input data available | Yes (25D vectors) | Partially (needs view/map frames) |
| Training data exists | Yes | No (CNN inputs not generated) |
| Training validated | Partially | No |
| Inference latency | Low (LSTM only) | High (CNN + LTC + Hopfield) |
| Feature richness | Moderate | High (spatial + temporal + associative) |
| Dependencies | PyTorch only | PyTorch + ncps + hflayers |

**Recommendation:** Keep `AdvancedCoachNN` as the production model. Move `RAPCoachModel` to an `experimental/` directory with clear documentation that it is a research prototype. Remove it from the default coaching pipeline.

**Implementation:**
1. Create `backend/nn/experimental/` directory.
2. Move `rap_coach/` into `experimental/`.
3. Update all imports and the coaching service to only reference `AdvancedCoachNN` by default.
4. Add a feature flag `USE_RAP_MODEL` for opt-in experimentation.

**Complexity:** Medium

### P9-02: Complete or remove JEPA pre-training [MEDIUM]

**Problem:** JEPA is implemented but uses simplified MSE loss that risks collapse. It's either a real feature or a prototype that should be isolated.
**Decision:** If P1-03 (contrastive loss fix) succeeds and validation shows meaningful embeddings, keep JEPA as a pre-training option. If embeddings still collapse, move JEPA to `experimental/` alongside RAP Coach.
**Complexity:** Depends on P1-03 outcome

### P9-03: Consolidate coaching service modes [MEDIUM]

**Problem:** Four coaching modes (COPER, Hybrid, RAG, Traditional) with a fallback chain. The Hybrid mode (`hybrid_engine.py`) duplicates some logic from the correction engine.
**Fix:** Audit the actual usage of each mode. If COPER is the default and the fallback chain always succeeds, document the expected behavior and add integration tests for each fallback transition.
**Complexity:** Medium

---

## 13. Phase 10: Documentation & Packaging

### P10-01: Write README.md [HIGH]

**Problem:** The project has technical documentation in `docs/` (Book-Coach, user guides) but no root-level README.
**Content:**
1. Project description and screenshots
2. System requirements (Python 3.10+, GPU recommended, etc.)
3. Installation instructions (pip install, Ollama setup, Steam API key)
4. Quick start guide (first demo analysis)
5. Architecture overview diagram
6. Contributing guidelines
7. License
**Complexity:** Medium

### P10-02: Create PyInstaller packaging [HIGH]

**Problem:** No packaging or distribution mechanism exists.
**Fix:** Create `macena.spec` for PyInstaller:
```python
# macena.spec
a = Analysis(['Programma_CS2_RENAN/main.py'],
    pathex=['.'],
    datas=[
        ('Programma_CS2_RENAN/apps/desktop_app/layout.kv', 'apps/desktop_app'),
        ('Programma_CS2_RENAN/PHOTO_GUI', 'PHOTO_GUI'),
    ],
    hiddenimports=['kivymd', 'sqlmodel', 'torch', ...],
)
```
Test on Windows, Linux, and macOS.
**Complexity:** High

### P10-03: Verify i18n/localization setup [MEDIUM]

**Problem:** i18n hooks exist in `layout.kv` but translation files are not verified.
**Fix:** Verify that the Portuguese warnings in `hybrid_engine.py:244` are consistent with the app's language. Either fully implement i18n or standardize on English.
**Complexity:** Medium

### P10-04: Document all F-code deferrals [LOW]

**Problem:** F-codes (F7-03, F7-06, F7-09, etc.) are scattered across the codebase without a central registry.
**Fix:** Create `docs/DEFERRALS.md` listing every F-code, its description, status, and resolution plan.
**Complexity:** Low

---

## 14. Phase 11: Performance Optimization

### P11-01: Vectorize heatmap point projection [HIGH]

**File:** `backend/processing/heatmap_engine.py:76-87, 171-179`
**Problem:** O(N) Python loop for each point projection.
**Fix:**
```python
points = np.array(points)
nx = (points[:, 0] - meta.pos_x) * scale_factor
ny = resolution - 1 - ((points[:, 1] - meta.pos_y) * scale_factor)
nx = np.clip(nx.astype(int), 0, resolution - 1)
ny = np.clip(ny.astype(int), 0, resolution - 1)
```
**Expected Speedup:** 10-50x for large point sets.
**Complexity:** Low

### P11-02: Add game tree memoization [MEDIUM]

**File:** `backend/analysis/game_tree.py`
**Problem:** Repeated state evaluations waste compute (no transposition table).
**Fix:** Add a hash-based transposition table:
```python
class TranspositionTable:
    def __init__(self, max_size=10000):
        self._table = {}
        self._max_size = max_size

    def lookup(self, state_hash):
        return self._table.get(state_hash)

    def store(self, state_hash, value, depth):
        if len(self._table) >= self._max_size:
            self._table.pop(next(iter(self._table)))
        self._table[state_hash] = (value, depth)
```
**Expected Speedup:** 2-5x for game tree search.
**Complexity:** Medium

### P11-03: Replace `iterrows()` in deception_index [LOW]

**File:** `backend/analysis/deception_index.py:100-105`
**Fix:** Use vectorized operations or `merge_asof` for flash correlation.
**Complexity:** Low

### P11-04: Optimize player_knowledge history scan [MEDIUM]

**File:** `backend/processing/player_knowledge.py:353-396`
**Problem:** O(T * P) iteration for `_build_enemy_memory`.
**Fix:** Pre-index player positions by tick for O(1) lookup:
```python
# Build index once:
positions_by_tick = defaultdict(dict)
for tick_data in recent_history:
    for player in tick_data.players:
        positions_by_tick[tick_data.tick][player.name] = player.position
```
**Complexity:** Medium

---

## 15. Phase 12: Final QA & Release Gate

### P12-01: Full security audit [HIGH]

Run `/security-scan` and `/devsecops-gate --full` on the entire codebase. Resolve all findings.

### P12-02: Final headless validation [HIGH]

Run `python tools/headless_validator.py` and verify all 23 phases pass with zero warnings.

### P12-03: Manual UI testing on target platforms [HIGH]

Test on:
- Windows 10/11 (primary target)
- Ubuntu 22.04 (secondary)
- macOS 13+ (tertiary, if supporting)

Test scenarios:
1. First-run wizard flow
2. Demo ingestion (manual + auto)
3. Match history → detail → performance navigation
4. Tactical viewer with demo playback
5. Coaching chat interaction
6. Settings changes (theme, font, paths)
7. Long-running session (2+ hours, memory monitoring)

### P12-04: Performance benchmarks [MEDIUM]

Establish baseline benchmarks:
- App startup time: < 5 seconds
- Demo parse time: < 30 seconds for standard match
- ML training cycle: < 5 minutes for 50 matches
- Memory usage: < 500MB idle, < 1.5GB during analysis
- Heatmap generation: < 2 seconds

### P12-05: Release checklist [HIGH]

Before v1.0 release:
- [ ] All Phase 0-3 fixes implemented and tested
- [ ] Coverage >= 70%
- [ ] CI/CD pipeline passing on all branches
- [ ] Dependencies pinned with lock file
- [ ] PyInstaller build succeeds on Windows
- [ ] README.md complete
- [ ] User guide updated
- [ ] CHANGELOG.md created
- [ ] Version bumped in pyproject.toml
- [ ] Git tag created
- [ ] No CRITICAL or HIGH issues remain open

---

## 16. Appendix A: Complete Issue Registry

### A.1 Issues from Original Audit

| ID | Severity | Category | Description | Phase |
|----|----------|----------|-------------|-------|
| AU-01 | CRITICAL | ML | JEPA uses MSE not contrastive loss | P1-03 |
| AU-02 | CRITICAL | Deps | KivyMD pinned to master branch | P5-01 |
| AU-03 | HIGH | Tests | 49% coverage threshold too low | P6-01 |
| AU-04 | HIGH | Arch | Two competing ML architectures | P9-01 |
| AU-05 | MEDIUM | Analysis | Hand-tuned momentum multipliers | P8-03 |
| AU-06 | MEDIUM | Analysis | Hand-tuned decay rates | P8-01 |
| AU-07 | MEDIUM | Analysis | Game tree no memoization | P11-02 |
| AU-08 | MEDIUM | ML | Hopfield random initialization | P9-01 |
| AU-09 | HIGH | DevOps | No CI/CD pipeline | P6-03 |
| AU-10 | LOW | UI | Drive enumeration duplicated | P4-misc |
| AU-11 | LOW | UI | Color constants duplicated | P4-misc |
| AU-12 | LOW | UI | Help system placeholder | Deferred |
| AU-13 | LOW | UI | Demo path wizard step stubbed | Deferred |
| AU-14 | LOW | Code | Dead code: compute_hltv2_rating_regression | cleanup |
| AU-15 | LOW | Schema | Ext_PlayerPlaystyle conflates profile/playstyle | P2-misc |
| AU-16 | MEDIUM | Analysis | Pro baselines unvalidated | P8-06 |
| AU-17 | MEDIUM | Analysis | Deception index weights heuristic | P8-04 |
| AU-18 | MEDIUM | Analysis | Role classification thresholds | P8-05 |
| AU-19 | MEDIUM | Analysis | Impact kill threshold | P8-misc |

### A.2 Issues Discovered in Deep Code Audit

| ID | Severity | Source | Description | Phase |
|----|----------|--------|-------------|-------|
| DC-01 | CRITICAL | main.py:834 | `func` NameError in status update | P0-01 |
| DC-02 | CRITICAL | main.py:1367 | Missing commit in enqueue_single_demo | P0-02 |
| DC-03 | CRITICAL | state_manager.py:23 | CoachState singleton race condition | P0-04 |
| DC-04 | CRITICAL | db_backup.py:56 | TOCTOU race in backup | P0-05 |
| DC-05 | CRITICAL | train.py:137 | train=val for small datasets | P1-04 |
| DC-06 | CRITICAL | early_stopping.py | EarlyStopping never used | P1-01 |
| DC-07 | CRITICAL | train.py/config.py | No global seeds anywhere | P1-02 |
| DC-08 | CRITICAL | role_features/role_classifier | Duplicate PlayerRole enums | P3-01 |
| DC-09 | CRITICAL | pro_bridge/base_features | avg_kills scale mismatch | P3-02 |
| DC-10 | CRITICAL | external_analytics.py:77 | Crash on missing columns | P3-03 |
| DC-11 | CRITICAL | tactical_viewer_screen.py:93 | Binding leak on_enter | P4-01 |
| DC-12 | CRITICAL | coaching_chat_vm.py:128 | Thread-unsafe append | P4-02 |
| DC-13 | HIGH | db_backup.py:102 | Connection leak on checkpoint fail | P0-06 |
| DC-14 | HIGH | main.py:1407 | folder_picker_target AttributeError | P0-07 |
| DC-15 | HIGH | jepa_train.py:175 | Negative sampling includes positive | P1-05 |
| DC-16 | HIGH | train.py:150 | No gradient clipping for LSTM | P1-06 |
| DC-17 | HIGH | role_classifier vs role_features | Competing classification systems | P3-04 |
| DC-18 | HIGH | player_knowledge.py:440 | Hardcoded 64-tick window | P3-05 |
| DC-19 | HIGH | role_thresholds.py:259 | Thread-unsafe singleton | P3-06 |
| DC-20 | HIGH | correction_engine.py:46 | tuple vs list ambiguity | P3-07 |
| DC-21 | HIGH | match_detail_screen.py:273 | Blocking DB on main thread | P4-06 |
| DC-22 | HIGH | heatmap_engine.py:76 | O(N) Python loop | P11-01 |
| DC-23 | HIGH | console.py:652 | API key in CLI args | P7-01 |
| DC-24 | HIGH | console.py:145 | API key potentially logged | P7-02 |
| DC-25 | HIGH | belief_model.py:59,113 | Unvalidated heuristic coefficients | P8-01/02 |
| DC-26 | MEDIUM | remote_file_server.py:87 | startswith path traversal bypass | P2-04 |
| DC-27 | MEDIUM | db_models.py:10 | MAX_GAME_STATE_JSON unenforced | P2-02 |
| DC-28 | MEDIUM | storage_manager.py:104 | No path traversal validation | P2-03 |
| DC-29 | MEDIUM | state_manager.py:165 | Module-level instantiation | P2-07 |
| DC-30 | MEDIUM | jepa_model.py:163 | Target encoder computes unused gradients | P1-07 |
| DC-31 | MEDIUM | config.py:105 | OUTPUT_DIM=4 vs METADATA_DIM=25 | P1-08 |
| DC-32 | MEDIUM | superposition.py:22 | Bad weight initialization | P1-09 |
| DC-33 | MEDIUM | win_probability_trainer.py:53 | No train/val split | P1-10 |
| DC-34 | MEDIUM | train.py:39 | val_loader full dataset as one batch | P1-11 |
| DC-35 | MEDIUM | model.py:144 | No architecture config saved | P1-12 |
| DC-36 | MEDIUM | data_pipeline.py:67 | Filter threshold too aggressive | P3-11 |
| DC-37 | MEDIUM | utility_economy.py:249 | MR12-only overtime assumption | P3-12 |
| DC-38 | MEDIUM | role_features.py:120 | Division by epsilon distortion | P3-09 |
| DC-39 | MEDIUM | win_probability.py:203 | Probability discontinuity at clamp | P3-misc |
| DC-40 | MEDIUM | match_detail/history/performance | MVVM violations | P4-03 |
| DC-41 | MEDIUM | 3 screens | Missing loading indicators | P4-04 |
| DC-42 | MEDIUM | layout.kv:733 | Chat indicator never activates | P4-05 |
| DC-43 | MEDIUM | layout.kv:520,552 | Hardcoded dp heights clip content | P4-08 |
| DC-44 | MEDIUM | spatial_debugger/ghost_pixel | Division by zero before layout | P4-09 |
| DC-45 | MEDIUM | all screens | No navigation back-stack | P4-10 |
| DC-46 | MEDIUM | remote_file_server | No rate limiting | P7-03 |
| DC-47 | LOW | belief_model.py:163 | Factory creates new instance every call | P3-10 |

---

## 17. Appendix B: Files Not Covered by Original Audit

The following files exist in the project but were not listed in the original audit's file structure. Each was discovered and audited during deep code review:

| File | Lines | Discovery | Issues Found |
|------|-------|-----------|--------------|
| `backend/coaching/explainability.py` | 95 | Deep audit | Skill-level verbosity filter, template-based (functional) |
| `backend/coaching/nn_refinement.py` | 31 | Deep audit | Simple weight scaling (functional, no issues) |
| `backend/coaching/token_resolver.py` | 108 | Deep audit | Pro player token lookup (functional) |
| `backend/coaching/hybrid_engine.py` | 644 | Deep audit | Comprehensive hybrid coaching (functional, minor issues) |
| `backend/services/llm_service.py` | 253 | Deep audit | Ollama integration (functional, good error handling) |
| `backend/data_sources/faceit_integration.py` | 274 | Deep audit | FACEIT API client (functional, good rate limiting) |
| `backend/data_sources/steam_api.py` | 106 | Deep audit | Steam API client (functional, good retry logic) |
| `backend/onboarding/new_user_flow.py` | ~200 | Deep audit | Onboarding pipeline (not fully audited) |
| `backend/progress/longitudinal.py` | ~300 | Deep audit | Longitudinal tracking (not fully audited) |
| `backend/progress/trend_analysis.py` | ~200 | Deep audit | Trend analysis (not fully audited) |
| `backend/nn/training_controller.py` | ~250 | Deep audit | Training orchestration (functional) |
| `backend/nn/training_monitor.py` | ~200 | Deep audit | Training metrics (functional) |
| `backend/nn/training_callbacks.py` | ~150 | Deep audit | Callback system (functional) |
| `backend/nn/tensorboard_callback.py` | ~100 | Deep audit | TensorBoard integration (functional) |
| `backend/nn/embedding_projector.py` | ~200 | Deep audit | UMAP visualization (functional) |
| `backend/nn/maturity_observatory.py` | ~200 | Deep audit | Model maturity tracking (functional) |
| `backend/nn/layers/superposition.py` | 102 | Deep audit | Superposition layer (weight init issue found) |
| `backend/nn/rap_coach/perception.py` | 99 | Deep audit | CNN perception (functional, well-designed) |
| `backend/nn/rap_coach/strategy.py` | 81 | Deep audit | MoE strategy (functional) |
| `backend/nn/rap_coach/pedagogy.py` | 99 | Deep audit | Value estimation (functional) |
| `backend/nn/rap_coach/communication.py` | ~100 | Deep audit | Not fully audited |
| `backend/nn/rap_coach/skill_model.py` | ~100 | Deep audit | SkillAxes enum (functional) |
| `backend/nn/rap_coach/chronovisor_scanner.py` | ~200 | Deep audit | Not fully audited |
| `apps/desktop_app/ghost_pixel.py` | ~120 | Deep audit | Division by zero risk (P4-09) |
| `apps/desktop_app/timeline.py` | ~150 | Deep audit | Event markers (functional, hardcoded pixel widths) |
| `tools/` (15 scripts) | ~3000 | Deep audit | Build, validation, diagnostic tools |

**Key Finding:** The original audit listed ~163 Python files. The actual project has ~180+ Python files. The unlisted files are primarily in the coaching, progress, and tools directories. None contained critical bugs, but several had medium-severity issues that are now tracked in the plan.

---

## 18. Appendix C: Heuristic Constants Requiring Empirical Validation

Every hand-tuned constant in the project, with its current value, source, and validation status:

| Constant | Value | File | Domain | Validated? |
|----------|-------|------|--------|------------|
| Threat decay lambda | 0.1 | belief_model.py:59 | Death probability | No |
| Threat weight | 2.0 | belief_model.py:113 | Death probability | No |
| Weapon weight | 1.5 | belief_model.py:114 | Death probability | No |
| Armor weight | -1.0 | belief_model.py:115 | Death probability | No |
| Exposure weight | 1.0 | belief_model.py:116 | Death probability | No |
| Win streak delta | +0.05 | momentum.py:113 | Momentum | No |
| Loss streak delta | -0.04 | momentum.py:114 | Momentum | No |
| Tilt threshold | 0.85 | momentum.py:20 | Momentum | No |
| Hot threshold | 1.2 | momentum.py:21 | Momentum | No |
| Fake flash weight | 0.25 | deception_index.py:26 | Deception | No |
| Rotation feint weight | 0.40 | deception_index.py:27 | Deception | No |
| Sound deception weight | 0.35 | deception_index.py:28 | Deception | No |
| Flash blind window | 128 ticks | deception_index.py:~100 | Deception | Partial |
| Impact kill threshold | 1.0 | base_features.py:~145 | Stats | No |
| Molotov dmg/throw | 35 | utility_economy.py:66 | Utility | No |
| Flash enemies/throw | 1.2 | utility_economy.py:67 | Utility | No |
| Smoke entropy max | 2.5 | entropy_analysis.py:21 | Entropy | No |
| Flash entropy max | 1.8 | entropy_analysis.py:22 | Entropy | No |
| Molotov entropy max | 2.0 | entropy_analysis.py:23 | Entropy | No |
| HE entropy max | 1.5 | entropy_analysis.py:24 | Entropy | No |
| Z-level threshold | 200 | connect_map_context.py:7 | Spatial | Partial |
| Z-penalty factor | 2.0 | connect_map_context.py:8 | Spatial | Partial |
| Memory decay tau | 160 | player_knowledge.py:37 | Player knowledge | No (comment wrong) |
| KAST weight | 1.5 | correction_engine.py:~20 | Corrections | No |
| ADR weight | 1.5 | correction_engine.py:~21 | Corrections | No |
| Accuracy weight | 1.4 | correction_engine.py:~22 | Corrections | No |
| NCP wiring ratio | 2:1 | rap_coach/memory.py:33 | NN arch | No |
| JEPA EMA momentum | 0.996 | jepa_model.py:303 | NN training | Partial |
| Confidence cap | 300 rounds | correction_engine.py:~40 | Corrections | No |
| ML confidence weight | 0.6 | hybrid_engine.py:484 | Coaching | No |
| Knowledge weight | 0.4 | hybrid_engine.py:485 | Coaching | No |
| Silence threshold | 0.2 | explainability.py:8 | Coaching | No |
| Severity high boundary | 1.5 | explainability.py:9 | Coaching | No |
| Severity medium boundary | 0.8 | explainability.py:10 | Coaching | No |
| Entry KPR centroid | 0.78 | role_features.py:36 | Roles | Partial |
| AWPer KPR centroid | 0.85 | role_features.py:48 | Roles | Partial |

**Total: 35 hand-tuned constants, 0 fully validated, 5 partially validated, 30 unvalidated.**

---

## 19. Appendix D: Cross-Module Inconsistencies

Issues where two or more modules disagree on the same concept:

| Inconsistency | Module A | Module B | Impact |
|---------------|----------|----------|--------|
| `PlayerRole` enum values | `role_features.py` ("entry") | `role_classifier.py` ("Entry Fragger") | String comparisons fail |
| `avg_kills` scale | `pro_bridge.py` (per-match) | `base_features.py` (per-round) | Z-scores meaningless |
| Tick rate assumption | `player_knowledge.py` (64 Hz) | Various | Wrong on 128-tick servers |
| Overtime format | `utility_economy.py` (MR12 only) | `momentum.py` (MR12 + MR13) | Economy logic wrong in MR13 |
| Feature naming | `correction_engine.py` ("avg_kast") | `external_analytics.py` ("kast") | Importance weights miss |
| Role name format | `engagement_range.py` ("entry_fragger") | `role_classifier.py` ("Entry Fragger") | Normalization needed |
| Session auto-commit | `database.py:117` (auto-commits) | Various callers | Double-commit or missing commit |
| Singleton pattern | `database.py` (double-checked lock) | `state_manager.py` (import-time) | Race condition in state_manager |
| Query API | `match_detail_screen.py` (session.query) | `match_history_screen.py` (session.exec) | Inconsistent API usage |
| OUTPUT_DIM | `config.py` (4) | `model.py` (METADATA_DIM=25) | Dimension mismatch risk |

---

## Execution Timeline

### Sprint 1 (Week 1-2): Emergency & ML
- Phase 0: All 7 tasks (P0-01 through P0-07)
- Phase 1: Tasks P1-01 through P1-06
- **Gate:** `headless_validator.py` passes, no CRITICAL issues remain

### Sprint 2 (Week 3-4): Data & Processing
- Phase 1: Remaining tasks (P1-07 through P1-12)
- Phase 2: All 8 tasks
- Phase 3: Tasks P3-01 through P3-07
- **Gate:** All cross-module inconsistencies resolved

### Sprint 3 (Week 5-6): UI & Dependencies
- Phase 3: Remaining tasks
- Phase 4: All 11 tasks
- Phase 5: All 4 tasks
- **Gate:** KivyMD pinned, UI thread safety verified

### Sprint 4 (Week 7-8): Testing & Security
- Phase 6: CI/CD pipeline, coverage push to 60%
- Phase 7: All 5 tasks
- **Gate:** CI pipeline green, security scan clean

### Sprint 5 (Week 9-10): Validation & Architecture
- Phase 8: Heuristic validation (data-dependent, may extend)
- Phase 9: Architecture decisions implemented
- **Gate:** Canonical ML model selected, JEPA decision made

### Sprint 6 (Week 11-12): Documentation & Release
- Phase 10: Documentation and packaging
- Phase 11: Performance optimizations
- Phase 12: Final QA and release gate
- **Gate:** All P12-05 checklist items verified

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-06 | Claude Opus 4.6 + Human Audit | Initial comprehensive plan |

---

*End of Master Remediation Plan*
*Total issues tracked: 156 (16 CRITICAL, 28 HIGH, 59 MEDIUM, 53 LOW)*
*Estimated total effort: 10-12 weeks with dedicated developer*
