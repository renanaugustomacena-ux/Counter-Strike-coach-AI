# Data Acquisition Pipeline: Ingestion, Parsing, and External Integration
# Macena CS2 Analyzer — Technical Audit Report 3/8

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| Report ID | AUDIT-2026-03 |
| Date | 2026-03-08 |
| Version | 1.0 |
| Classification | Internal — Engineering Review |
| Auditor | Engineering Audit Protocol v3 |
| Scope | 62 files across data acquisition, ingestion pipeline, HLTV scraping, external APIs, and backend control |
| Total LOC Audited | 7,871 Python + 0 SQL + 1,200 README = ~9,071 |
| Audit Standard | ISO/IEC 25010, ISO/IEC 27001, OWASP Top 10, IEEE 730, STRIDE, CLAUDE.md Constitution |
| Previous Audit | AUDIT-2026-02 (Data Persistence) |

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
   - 1.1 Domain Health Assessment
   - 1.2 Critical Findings Summary
   - 1.3 Quantitative Overview
   - 1.4 Risk Heatmap
2. [Audit Methodology](#2-audit-methodology)
3. [Demo Parsing & Format Adaptation](#3-demo-parsing--format-adaptation)
   - 3.1 demo_parser.py
   - 3.2 demo_format_adapter.py
   - 3.3 event_registry.py
   - 3.4 round_context.py
   - 3.5 trade_kill_detector.py
4. [External API Integrations](#4-external-api-integrations)
   - 4.1 steam_api.py
   - 4.2 steam_demo_finder.py
   - 4.3 faceit_api.py
   - 4.4 faceit_integration.py
5. [HLTV Scraping Subsystem](#5-hltv-scraping-subsystem)
   - 5.1 hltv_api_service.py
   - 5.2 stat_fetcher.py
   - 5.3 selectors.py
   - 5.4 rate_limit.py
   - 5.5 docker_manager.py
   - 5.6 flaresolverr_client.py
   - 5.7 browser/manager.py
   - 5.8 cache/proxy.py
   - 5.9 collectors/players.py
   - 5.10 hltv_scraper.py (entry point)
6. [Ingestion Pipeline](#6-ingestion-pipeline)
   - 6.1 demo_loader.py
   - 6.2 integrity.py
   - 6.3 steam_locator.py
   - 6.4 pipelines/json_tournament_ingestor.py
   - 6.5 pipelines/user_ingest.py
   - 6.6 registry/lifecycle.py
   - 6.7 registry/registry.py
   - 6.8 registry/schema.sql
7. [Backend Ingestion Layer](#7-backend-ingestion-layer)
   - 7.1 csv_migrator.py
   - 7.2 resource_manager.py
   - 7.3 watcher.py
8. [Backend Control Layer](#8-backend-control-layer)
   - 8.1 console.py
   - 8.2 db_governor.py
   - 8.3 ingest_manager.py
   - 8.4 ml_controller.py
9. [Entry Points & Service Daemons](#9-entry-points--service-daemons)
   - 9.1 run_ingestion.py
   - 9.2 run_worker.py
   - 9.3 hltv_sync_service.py
10. [Package & Module Init Files](#10-package--module-init-files)
11. [README Documentation Assessment](#11-readme-documentation-assessment)
12. [Consolidated Findings Matrix](#12-consolidated-findings-matrix)
13. [Recommendations](#13-recommendations)
14. [Appendix A: Complete File Inventory](#appendix-a-complete-file-inventory)
15. [Appendix B: Glossary](#appendix-b-glossary)
16. [Appendix C: Cross-Reference Index](#appendix-c-cross-reference-index)
17. [Appendix D: Dependency Graph](#appendix-d-dependency-graph)
18. [Appendix E: Data Flow Diagrams](#appendix-e-data-flow-diagrams)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Domain Health Assessment

**Overall Rating: ADEQUATE**

The Data Acquisition domain is the project's most externally-facing subsystem, interfacing with demo file parsing (demoparser2), Steam Web API, FaceIT API, and HLTV.org web scraping. At 7,871 Python LOC across 43 Python modules, it represents the primary data ingestion pathway that feeds the entire ML training pipeline and coaching system.

The domain demonstrates strong architectural separation: demo parsing, external APIs, HLTV scraping, ingestion orchestration, and backend control are cleanly separated into distinct sub-packages. The vectorized bulk insert in `run_ingestion.py` (achieving 8x speedup from 762s to 97s) is a standout engineering achievement. The HLTV subsystem's circuit breaker pattern, FlareSolverr Cloudflare bypass, and multi-tier caching show sophisticated resilience engineering.

However, significant concerns exist in three areas: (1) **silent data quality degradation** — multiple fallback chains silently substitute defaults (hardcoded KAST=0.70, money=0, inventory=[]) that contaminate downstream ML training, (2) **thread safety gaps** — the circuit breaker, caching proxy singleton, FlareSolverr session, and demo registry all lack proper synchronization despite being called from concurrent daemons, and (3) **HLTV ToS compliance** — browser fingerprint spoofing (webdriver detection disabled) creates legal risk that is acknowledged but not mitigated.

The ingestion pipeline handles the critical invariant "every tick is sacred" (CLAUDE.md Rule 8) through three-pass demo parsing but introduces heuristic ceilings (nade duration capping at 20s) and thrower position fallback (15-tick backward search) that silently corrupt temporal and spatial training data without flagging the degradation to downstream consumers.

### 1.2 Critical Findings Summary

| ID | Severity | File | Finding |
|----|----------|------|---------|
| R3-01 | HIGH | demo_parser.py | Hardcoded KAST fallback (0.70) contaminates ML training data with fabricated values |
| R3-02 | HIGH | demo_loader.py | Money field fallback chain silently defaults to 0 when all fields missing |
| R3-03 | HIGH | hltv_api_service.py | ~~REMOVED — hltv_api_service.py no longer exists~~ |
| R3-04 | HIGH | run_ingestion.py | ~~RESOLVED — demo name now normalized via Path().stem~~ |
| R3-05 | HIGH | cache/proxy.py | ~~REMOVED — cache/proxy.py no longer exists~~ |
| R3-06 | HIGH | ingest_manager.py | ~~RESOLVED — file existence guard added before enqueue~~ |
| R3-07 | MEDIUM | stat_fetcher.py | CSS selector fragility — HLTV redesign silently breaks all statistics extraction |
| R3-08 | MEDIUM | registry.py | ~~RESOLVED — registry now uses threading.Lock + FileLock~~ |
| R3-09 | MEDIUM | faceit_integration.py | ~~RESOLVED — match_id sanitized against directory traversal~~ |
| R3-10 | MEDIUM | browser/manager.py | ~~REMOVED — browser/manager.py no longer exists~~ |

### 1.3 Quantitative Overview

| Metric | Value |
|--------|-------|
| Files Audited | 62 |
| Python Files | 43 |
| README Files | 15 |
| SQL Files | 1 |
| Other Config Files | 3 (init files) |
| Total Lines of Code (Python) | 7,871 |
| Classes Analyzed | 22 |
| Functions/Methods Analyzed | ~185 |
| Findings: CRITICAL | 0 |
| Findings: HIGH | 8 (3 resolved, 2 removed — 3 active) |
| Findings: MEDIUM | 15 (2 resolved, 6 removed — 7 active) |
| Findings: LOW | 12 |
| Findings: INFO | 7 |
| Remediation Items Previously Fixed | 18 (F5-*, F6-*, F7-* codes) |
| Remaining Deferred Items | 2 (G-05, steam path consolidation) |

### 1.4 Risk Heatmap

```
                    Low Impact    Medium Impact    High Impact
                   ┌────────────┬───────────────┬─────────────┐
High Likelihood    │            │ R3-07 R3-08   │ R3-01 R3-02 │
                   │            │ R3-10         │ R3-03       │
                   ├────────────┼───────────────┼─────────────┤
Medium Likelihood  │ R3-L01     │ R3-06 R3-09   │ R3-04 R3-05 │
                   │ R3-L02     │               │             │
                   ├────────────┼───────────────┼─────────────┤
Low Likelihood     │ R3-L03-L12 │ R3-M11-M15    │             │
                   │            │               │             │
                   └────────────┴───────────────┴─────────────┘
```

---

## 2. AUDIT METHODOLOGY

### 2.1 Standards Applied
- **ISO/IEC 25010** — Software product quality (functionality, reliability, usability, efficiency, maintainability, portability, security, compatibility)
- **ISO/IEC 27001** — Information security management (external API credential handling, PII in scraped data)
- **OWASP Top 10 2021** — Web/application security (injection, broken access control, security misconfiguration)
- **IEEE 730** — Software quality assurance
- **CLAUDE.md Constitution** — Project-specific engineering rules (Rules 1-7, Dev Rules 1-11)
- **STRIDE** — Threat modeling (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)

### 2.2 Analysis Techniques
- **Static Analysis**: Line-by-line code review of all 43 Python files, AST-level import graph construction
- **Data Flow Analysis**: Demo file → parser → DataFrame → bulk insert → DB tracing
- **API Contract Analysis**: Steam/FaceIT/HLTV endpoint mapping, error code handling
- **Concurrency Analysis**: Thread safety of shared state across Tri-Daemon architecture
- **Security Analysis**: STRIDE threat model for all external integration points
- **Performance Analysis**: Algorithmic complexity of parsing loops, network I/O patterns

### 2.3 Severity Classification

| Severity | Definition | SLA |
|----------|------------|-----|
| CRITICAL | System failure, data loss, security breach, or correctness violation affecting core functionality | Immediate fix required |
| HIGH | Significant functional impact, data quality degradation affecting ML training, security weakness under realistic conditions | Fix within current sprint |
| MEDIUM | Moderate impact on reliability, performance, or maintainability; does not block core functionality | Fix within next 2 sprints |
| LOW | Minor code quality issues, documentation gaps, optimization opportunities with <10% impact | Fix during next refactoring cycle |
| INFO | Observations, positive findings, architectural notes | No SLA — informational |

### 2.4 Cross-Reference Protocol
Findings cross-referenced to: prior remediation phases (F5-*, F6-*, F7-* codes), PIPELINE_AUDIT_REPORT.md (C-codes), AUDIT_REPORT.md (top 30), CLAUDE.md rules.

---

## 3. DEMO PARSING & FORMAT ADAPTATION

### 3.1 `demo_parser.py` — Demo file parsing with HLTV 2.0 rating

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 476 |
| Classes | 0 (module-level functions) |
| Functions | 8 |
| Cyclomatic Complexity (max) | 12 (`parse_demo`) |
| Import Count | 7 |

**Architecture & Design:**
Core parsing module wrapping the demoparser2 Rust library. Extracts per-tick and per-round data from CS2 `.dem` files, computing HLTV 2.0 rating metrics (KPR, DPR, ADR, KAST, Impact). Called by `run_ingestion.py` and `demo_loader.py` for the aggregate stats extraction pass.

**Correctness Analysis:**
- HLTV 2.0 rating formula (lines 180-220) correctly implements the weighted combination: `0.0073*KAST + 0.3591*KPR - 0.5329*DPR + 0.2372*Impact + 0.0032*ADR + 0.1587`
- **Finding R3-01**: Hardcoded KAST fallback `0.70` (line 139) when per-round KAST unavailable. This fabricated value contaminates ML training — 70% KAST is a reasonable average but using it as a default means the model cannot distinguish "data missing" from "player had 70% KAST". Should mark as NaN and let training pipeline filter.
- Data quality flagging system (lines 95-115) correctly identifies missing columns and returns `data_quality: "degraded"` in the result dict — but KAST fallback bypasses this flagging.
- Vectorized operations via pandas ensure parsing scales linearly with demo size.

**Security Analysis:**
- Input is a file path to `.dem` file — no user-controlled data enters SQL or shell commands.
- demoparser2 is a Rust library with memory-safe parsing; no buffer overflow risk from malformed demos.

**Performance Analysis:**
- Single-pass aggregate parsing: O(n) where n = total ticks (~100K-2M per demo)
- Rating computation is vectorized (pandas operations), not per-row iteration
- Typical timing: 5-30 seconds per demo depending on file size

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-01 | HIGH | Correctness | Hardcoded KAST fallback (0.70) fabricates training data when per-round KAST unavailable | Mark as NaN, flag `data_quality: "kast_missing"`, let training pipeline filter |
| R3-11 | MEDIUM | Correctness | Quadratic string filtering in column name matching (lines 282-283) — pre-lowercasing columns once would eliminate repeated `.lower()` calls | Pre-lowercase column names in single pass |
| R3-L01 | LOW | Correctness | `data_quality` flag not propagated to `PlayerMatchStats` DB model — downstream consumers cannot filter degraded records | Add `data_quality` column to PlayerMatchStats |

**Positive Observations:**
- HLTV 2.0 rating formula is correctly implemented with proper coefficient values
- Data quality flagging system (degraded status) is a sound architecture
- Event stats extraction (kills, assists, deaths, flash assists, headshots) is comprehensive

---

### 3.2 `demo_format_adapter.py` — Format validation and conversion

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 284 |
| Classes | 1 (`DemoFormatAdapter`) |
| Functions | 12 |
| Cyclomatic Complexity (max) | 8 |
| Import Count | 5 |

**Architecture & Design:**
Validates demo file format by checking magic bytes (`HL2DEMO`), header fields, and file structure. Maintains a changelog (lines 91-110) of known Valve schema changes for version detection. Provides format conversion between demoparser2 output and internal schemas.

**Correctness Analysis:**
- Magic byte validation (lines 45-55) correctly checks first 8 bytes for `HL2DEMO\x00` signature
- File size bounds: MIN_DEMO_SIZE = 1KB, MAX_DEMO_SIZE = 5GB — 1KB is unrealistically small for a valid CS2 demo (typical: 50MB-2GB), should be raised to at least 1MB
- Corruption heuristic (lines 160-180): checks for truncated headers, invalid map names, zero-length network data
- No active schema drift detection — changelog documents 3 known Valve changes but doesn't check if current demo uses an unknown schema version

**Security Analysis:**
- File path validated for existence before opening
- Binary file parsing uses struct.unpack with explicit format strings — no injection vector
- No network access — purely local file validation

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M01 | MEDIUM | Correctness | MIN_DEMO_SIZE = 1KB too small — a 1KB .dem file is certainly corrupt/truncated | Raise to 1MB minimum |
| R3-M02 | MEDIUM | Maintainability | Schema changelog (3 entries) not actively checked — no warning if demo uses unknown schema version | Add version detection with warning for unknown versions |

**Positive Observations:**
- Magic byte validation is the correct approach for binary file format detection
- Corruption heuristics are well-thought-out (truncated headers, zero-length network data)
- DemoFormatAdapter follows single-responsibility principle cleanly

---

### 3.3 `event_registry.py` — Event type registration and dispatch

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 356 |
| Classes | 2 (`EventType` enum, `EventRegistry`) |
| Functions | 14 |
| Import Count | 4 |

**Architecture & Design:**
Centralized registry for all 26 CS2 demo event types with handler path routing. Each event type maps to a handler function via string path reference. Currently 11/26 events are implemented (42% coverage).

**Correctness Analysis:**
- Event types comprehensively cover CS2 game events (player_death, bomb_planted, round_end, etc.)
- Handler path strings (e.g., `"backend.data_sources.demo_parser.handle_player_death"`) are not validated at registration time — stale references fail silently at dispatch
- Dispatch mechanism uses `importlib.import_module()` with `getattr()` — correct but adds runtime import overhead per event

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M03 | MEDIUM | Correctness | Handler paths not validated at registration — stale references fail silently at runtime | Add startup validation that all registered handler paths resolve to callable objects |
| R3-I01 | INFO | Coverage | 11/26 event types implemented (42%) — remaining 15 are registered but have no handler | Document which events are intentionally unimplemented vs planned |

**Positive Observations:**
- Comprehensive event type enumeration covering all CS2 game events
- Registry pattern enables extensible event handling without modifying core parsing logic

---

### 3.4 `round_context.py` — Round boundary extraction and tick assignment

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 224 |
| Classes | 0 |
| Functions | 5 |
| Import Count | 4 |

**Architecture & Design:**
Extracts round boundaries from demo events (`round_freeze_end`, `round_end`) and assigns round numbers to tick-level data using efficient `pd.merge_asof()` join — O(n log m) complexity where n = ticks and m = rounds.

**Correctness Analysis:**
- Round boundary fallback logic (lines 88-97): if `round_freeze_end` missing, uses previous `round_end` as start — correct for boundary but `time_in_round` will be off by freeze time (~15 seconds)
- `assign_round_to_ticks()` uses `np.searchsorted()` — O(m log k) binary search, correct and efficient
- `bomb_exploded` event (line 139) may not be standard demoparser2 event — silent failure if unsupported
- `time_in_round` clipped to 175s maximum (line 211) — correct for CS2 but silently hides data corruption

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-L02 | LOW | Correctness | bomb_exploded event may not be standard demoparser2 event — verify support in real demos | Add runtime check for event availability before extraction |
| R3-L03 | LOW | Correctness | time_in_round clipping to 175s hides data quality issues without logging | Log warning when clipping occurs |

**Positive Observations:**
- `merge_asof` is an excellent choice for temporal data joining — avoids O(n²) manual loop
- Separation of boundary extraction from tick assignment enables independent testing
- Fallback logic is pragmatic and correctly documented

---

### 3.5 `trade_kill_detector.py` — Trade kill identification from death events

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 353 |
| Classes | 1 (`TradeKillResult` dataclass) |
| Functions | 6 |
| Import Count | 4 |

**Architecture & Design:**
Identifies trade kills (teammate avenges a fallen player within 3-second window) using backward temporal search within same-round scope. Well-documented algorithm derived from cstat-main reference.

**Correctness Analysis:**
- TRADE_WINDOW_TICKS = 192 (3 seconds at 64 tick) — correct constant with clear derivation
- Algorithm correctly searches backward from each kill for victim's prior kills on the killer's team (lines 206-242)
- **Boundary condition M-05** (line 212): `tick - prior_tick >= trade_window` is exclusive boundary — a kill at exactly 192 ticks (3.0 seconds) is excluded. Comment says "inclusive" but code is exclusive. Should use `>` for true inclusive 3-second window.
- Team roster built from early 10% of ticks (line 76) — players joining mid-match will be missed
- Performance: O(m²) worst-case on nested death loop, but early-exit on window boundary keeps practical complexity at O(m × window_kills) — acceptable for typical matches (~300-500 deaths)

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-L04 | LOW | Correctness | Trade window boundary `>=` is exclusive — kills at exactly 192 ticks (3.0s) excluded despite "inclusive" comment | Change to `>` for true inclusive boundary |
| R3-L05 | LOW | Correctness | Team roster built from early 10% of ticks — mid-match player substitutions not captured | Document limitation; for competitive CS2 this is acceptable |

**Positive Observations:**
- Well-documented algorithm with clear reference to cstat-main specification
- `TradeKillResult` dataclass with derived properties (`trade_kill_ratio`, `was_traded_ratio`) is clean API design
- Round-scoped search (line 216-217) correctly prevents cross-round false matches
- Per-player aggregation (`get_player_trade_stats`) enables individual coaching insights

---

## 4. EXTERNAL API INTEGRATIONS

### 4.1 `steam_api.py` — Steam Web API integration

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 106 |
| Classes | 0 |
| Functions | 3 |
| Import Count | 3 |

**Architecture & Design:**
Provides Steam Web API integration for profile resolution (vanity URL → SteamID64) and profile data fetching. Uses exponential backoff retry (3 attempts, [1, 2, 4]s delays) with distinction between transient errors (retry) and client errors (fail fast).

**Correctness Analysis:**
- Retry logic correctly differentiates HTTPError (don't retry) from ConnectionError/Timeout (retry) (lines 21-33)
- Auto-vanity URL resolution (lines 69-76) detects non-numeric IDs and resolves via additional API call
- **Error handling inconsistency**: 403 Forbidden raises ValueError (lines 85-87) but empty player list returns None (line 94) — inconsistent error semantics
- No validation that steam_id is valid 17-digit SteamID64 format

**Security Analysis:**
- API key passed as URL query parameter (line 79) — standard for Steam API but visible in server access logs
- No explicit TLS verification flag — defaults to `verify=True` (safe)
- No rate limiting — Steam API has undocumented rate limits; code will fail silently if rate-limited

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M04 | MEDIUM | Correctness | No input validation on steam_id format — non-17-digit values accepted silently | Validate `len(str(steam_id)) == 17 and str(steam_id).isdigit()` |
| R3-L06 | LOW | Correctness | Inconsistent error handling — 403 raises, empty results return None | Standardize: return typed Result or always raise |

**Positive Observations:**
- Exponential backoff implementation is clean and correct
- Vanity URL auto-resolution is good UX — accepts both SteamID64 and custom URLs

---

### 4.2 `steam_demo_finder.py` — Steam installation and demo file discovery

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 252 |
| Classes | 1 (`SteamDemoFinder`) |
| Functions | 7 + 1 convenience function |
| Import Count | 6 |

**Architecture & Design:**
Multi-platform Steam installation discovery with dynamic Windows drive detection via `ctypes.windll.kernel32.GetLogicalDrives()`. Supports Windows (registry + filesystem scan), Linux (home directory paths), with fallback chain.

**Correctness Analysis:**
- Dynamic path generation (lines 49-74) enumerates all available drives at runtime — robust for multi-drive Windows systems
- Registry lookup correctly handles ImportError (non-Windows) and OSError (registry access denied)
- CS2_REPLAY_PATH hardcoded to standard Steam installation — custom Steam library folders not searched
- **Duplicate with steam_locator.py** (F6-11 acknowledged) — two implementations of Steam path discovery that may diverge

**Security Analysis:**
- No path canonicalization — `Path` objects from registry not `.resolve()`'d — symlink following could traverse to sensitive directories (unlikely in practice)
- Glob pattern `*.dem` is safe — no user-controlled input in path construction

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M05 | MEDIUM | Maintainability | Duplicate Steam path discovery — steam_demo_finder.py and steam_locator.py implement same logic independently (F6-11) | Consolidate into single `core/path_utils.py` module |
| R3-L07 | LOW | Correctness | CS2_REPLAY_PATH hardcoded — custom Steam library folders on alternate drives not searched | Parse `libraryfolders.vdf` for all library paths |

**Positive Observations:**
- Dynamic drive detection is well-engineered — runtime enumeration rather than hardcoded drive letters
- Multi-platform support (Windows/Linux) with appropriate platform-specific discovery mechanisms
- `auto_discover_steam_demos()` convenience function is clean entry point

---

### 4.3 `faceit_api.py` — Simple FaceIT API wrapper

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 37 |
| Classes | 0 |
| Functions | 3 |
| Import Count | 2 |

**Architecture & Design:**
Minimal wrapper around FaceIT API v4 endpoints. Returns raw JSON responses without validation or retry logic. **Duplicate of faceit_integration.py** which provides a full-featured implementation.

**Correctness Analysis:**
- No retry logic — network failures propagate as exceptions
- No rate limiting — FaceIT API may throttle without handling
- Returns empty dict `{}` on all errors (lines 34-36) — callers cannot distinguish "no data" from "API error"

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M06 | MEDIUM | Architecture | Duplicate FaceIT client — faceit_api.py (37 LOC) duplicates faceit_integration.py (274 LOC) | Remove faceit_api.py; use faceit_integration.py exclusively |
| R3-L08 | LOW | Correctness | Silent empty-dict error return — callers cannot distinguish "no data" from "API failure" | Raise exceptions for API errors; return None for "no data" |

---

### 4.4 `faceit_integration.py` — Full-featured FaceIT platform integration

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 274 |
| Classes | 1 (`FaceitIntegration`) |
| Functions | 8 |
| Import Count | 6 |

**Architecture & Design:**
Complete FaceIT API client with rate limiting (6s per request = 10 req/min), exponential backoff on 429, Retry-After header respect, session-based HTTP, and demo file downloading with streaming I/O.

**Correctness Analysis:**
- Rate limiting correctly enforced (line 78): `time.sleep(max(0, delay - elapsed))` ensures minimum 6s between requests
- Retry on 429 with Retry-After header parsing (line 92) — correct HTTP semantics
- Demo download uses streaming 8KB chunks (line 194) — correct for large files
- **Directory traversal risk**: `match_id` used directly in file path (line 187) — if match_id contains `../`, could write outside output directory

**Security Analysis:**
- API key stored in session headers (line 54) — if session object is logged or dumped, key is exposed
- No `__repr__()` override to redact sensitive headers
- `requests.Session()` never explicitly closed — resource leak in long-running services

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-09 | MEDIUM | Security | ~~RESOLVED — match_id sanitized against directory traversal~~ | — |
| R3-M07 | MEDIUM | Resource | requests.Session() never closed — resource leak in long-running FaceIT sync | Use context manager or atexit hook |
| R3-L09 | LOW | Security | API key in session headers could be exposed if session is logged/dumped | Override `__repr__()` to redact Authorization header |

**Positive Observations:**
- Rate limiting with Retry-After header parsing is correct HTTP practice
- Streaming download for large demo files prevents memory exhaustion
- Convenience function `sync_faceit_matches()` provides clean workflow orchestration

---

## 5. HLTV SCRAPING SUBSYSTEM

### 5.1 `hltv_api_service.py` — Main HLTV scraping service with circuit breaker

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 287 |
| Classes | 2 (`_CircuitBreaker`, `HLTVApiService`) |
| Functions | 10 |
| Import Count | 8 |

**Architecture & Design:**
Primary HLTV scraping service implementing circuit breaker pattern (MAX_FAILURES=10, RESET_WINDOW_S=3600), Cloudflare detection with FlareSolverr fallback, cache-first strategy, and lazy FlareSolverr initialization.

**Correctness Analysis:**
- Circuit breaker correctly implements failure counting with time-based reset — after 10 consecutive failures, service enters "open" state for 1 hour
- Cloudflare detection uses 4 heuristics (status code, page content patterns) — fragile but functional
- **Finding R3-03**: `_CircuitBreaker` is NOT thread-safe — `_failures` counter and `_last_failure_ts` are modified without any lock. Multiple threads calling `record_failure()` concurrently will corrupt the counter.
- Impact stat defaults to 0.0 if missing (line 252-254) with only a warning — contaminates ML baselines
- `_build_stats_dict()` string parsing (`.split()[0]`) fragile against malformed input

**Security Analysis:**
- User-Agent spoofing and webdriver detection disabling violate HLTV Terms of Service (F6-02 acknowledged)
- No input validation on player IDs — relies on SQLModel parameterization for SQL injection protection
- FlareSolverr instance used as HTTP proxy — if exposed to network, anyone can use it

**Concurrency Analysis:**
- **Circuit breaker race**: `time.monotonic()` check + increment not atomic — multi-threaded access will corrupt state
- **Lazy FlareSolverr init**: First concurrent call to `_try_flaresolverr_fallback()` could create multiple instances
- **Playwright page**: Single-threaded by design — concurrent `sync_range()` calls will crash

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-03 | HIGH | Concurrency | ~~REMOVED — hltv_api_service.py no longer exists~~ | — |
| R3-M08 | MEDIUM | Correctness | ~~REMOVED — hltv_api_service.py no longer exists~~ | — |
| R3-M09 | MEDIUM | Correctness | ~~REMOVED — hltv_api_service.py no longer exists~~ | — |

**Positive Observations:**
- Circuit breaker pattern is architecturally correct — prevents cascading failures
- Cache-first strategy minimizes redundant HLTV requests
- Cloudflare detection with FlareSolverr fallback is resilient against anti-bot measures

---

### 5.2 `stat_fetcher.py` — Deep web scraping for player statistics

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 377 |
| Classes | 1 (`HLTVStatFetcher`) |
| Functions | 12 |
| Import Count | 7 |

**Architecture & Design:**
Multi-page deep crawler that extracts comprehensive player statistics from HLTV.org. Fetches main profile page plus 3 sub-pages (clutches, multikills, career history) per player. Uses FlareSolverr for Cloudflare bypass with BeautifulSoup parsing.

**Correctness Analysis:**
- `_safe_float()` (lines 234-243) provides robust error handling for malformed stat values — catches ValueError, returns 0.0
- Division by zero handled (line 284): `dpr == 0` produces 0.0 K/D ratio — correct but a player with 0 deaths in non-trivial sample is a data quality anomaly
- **CSS selector fragility**: All selectors (`.stats-row`, `.playerCol a`, `.statistics`) are hardcoded strings that break silently when HLTV redesigns
- Missing trait sections silently return empty dict (lines 304-331) — no warning that Firepower/Entrying/Utility categories were not found
- Random sleep unseeded (lines 60, 111, 226) — intentional for anti-detection but makes testing non-deterministic

**Security Analysis:**
- BeautifulSoup parses arbitrary HTML — no validation that HTML is well-formed
- PII in detailed_stats_json (career history contains player names/nicknames) — no PII masking before storage
- FlareSolverr session shared across all requests — cookie cross-contamination possible

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-07 | MEDIUM | Correctness | CSS selector fragility — `.stats-row` and other selectors break silently on HLTV redesign | Add selector validation tests with sample pages; log warning if no elements found |
| R3-M10 | MEDIUM | Correctness | Missing trait sections silently return empty dict — downstream doesn't know Firepower/Entrying/Utility were missing | Log warning when expected sections not found; flag in ProPlayerStatCard |
| R3-L10 | LOW | Correctness | Random sleep unseeded — non-deterministic testing (intentional for anti-detection) | Provide optional seed parameter for test mocking |

**Positive Observations:**
- `_safe_float()` is robust defensive parsing — handles all malformed input gracefully
- Trait section mapping uses flexible key-phrase matching — more resilient than exact CSS selector matching
- Anti-fabrication: `_parse_required_stat()` raises ValueError on missing required stats instead of using fallback defaults

---

### 5.3 `selectors.py` — CSS selectors and URL construction

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 29 |
| Classes | 2 (`HLTVURLBuilder`, `PlayerStatsSelectors`) |
| Functions | 1 |
| Import Count | 0 |

**Architecture & Design:**
Centralizes CSS selectors and URL construction for HLTV page parsing. Static factory pattern for URL building.

**Correctness Analysis:**
- **EXTREMELY FRAGILE**: Every CSS selector is a single point of failure tied to HLTV's HTML structure
- Selectors duplicated in consumers — `hltv_api_service.py` hardcodes `.statistics`, `stat_fetcher.py` hardcodes `.stats-row` — defeating the purpose of centralization
- No tests for selector validity

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M11 | MEDIUM | Architecture | CSS selectors centralized here but duplicated in consumers — changing selectors requires updating 3+ files | Export all selectors as constants; use exclusively in consumers |
| R3-I02 | INFO | Maintainability | No automated tests for selector validity — silent failures on HLTV redesign | Add integration test with cached sample HTML pages |

---

### 5.4 `rate_limit.py` — HLTV request rate limiting

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 33 |
| Classes | 1 (`RateLimiter`) |
| Functions | 1 |
| Import Count | 2 |

**Architecture & Design:**
Tiered backoff system with 4 levels: micro (2-3.5s), standard (4-8s), heavy (10-20s), backoff (45-90s). Random jitter added for human-like behavior. Minimum 2.0s floor enforced.

**Correctness Analysis:**
- Jitter applied after range selection (line 23): `random.uniform(-0.5, 0.5)` — minimum could theoretically drop below floor, but `max(2.0, ...)` at line 25 catches this. Correct.
- Unseeded randomness (F6-25) is intentional for anti-detection — correct philosophy but makes testing non-deterministic.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-I03 | INFO | Testing | Unseeded randomness makes tests non-deterministic — provide seeding option for testing | Add optional `seed` parameter for deterministic test execution |

**Positive Observations:**
- Tiered backoff is well-designed — different delays for different operation types
- Minimum floor enforcement (2.0s) guarantees rate limit compliance

---

### 5.5 `docker_manager.py` — FlareSolverr Docker container management

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 138 |
| Functions | 7 |
| Import Count | 4 |

**Architecture & Design:**
Manages FlareSolverr Docker container lifecycle: start, stop, health check with polling (3s intervals, 45s timeout). Falls back to docker-compose if container doesn't exist.

**Correctness Analysis:**
- Health check polling (lines 40-44) correctly catches all exceptions and returns boolean
- Subprocess timeout (lines 28-35) prevents hangs — correct
- Hardcoded port 8191 — no way to override if user runs on different port
- Error messages partially in Italian (lines 76, 81, 90, 101) — breaks i18n

**Security Analysis:**
- No validation of docker-compose.yml contents — could execute arbitrary commands via shell expansion
- subprocess.run uses list args (not shell=True) — safe against shell injection

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-L11 | LOW | Configuration | Hardcoded port 8191 for FlareSolverr — no override mechanism | Accept port from config or environment variable |
| R3-I04 | INFO | Maintainability | Some error messages in Italian instead of English — inconsistent with codebase | Standardize all log messages to English |

---

### 5.6 `flaresolverr_client.py` — FlareSolverr REST client

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 145 |
| Classes | 1 (`FlareSolverrClient`) |
| Functions | 5 |
| Import Count | 3 |

**Architecture & Design:**
REST client wrapper for FlareSolverr's /v1 endpoint. Session persistence via browser session creation for cookie reuse. All exceptions caught and return None — no error propagation.

**Correctness Analysis:**
- Timeout calculation correct: `timeout=self._timeout + 15` gives buffer for server processing
- Session creation is idempotent — multiple calls overwrite `_session_id`
- **Silent error suppression**: All exceptions caught, return None — callers cannot distinguish timeout from "page doesn't exist" from "Cloudflare blocked"
- Stale session not handled — if session deleted server-side, requests fail silently until client recreated

**Concurrency Analysis:**
- `_session_id` shared across threads — concurrent `.get()` calls use same session, cookies may cross-contaminate

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M12 | MEDIUM | Correctness | Silent error suppression — all exceptions return None, losing error context for callers | Return error envelope (status, error_type, message) or raise typed exceptions |
| R3-L12 | LOW | Concurrency | _session_id shared across threads — cookie cross-contamination possible in concurrent requests | Use thread-local storage or session pool |

---

### 5.7 `browser/manager.py` — Playwright browser automation

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 61 |
| Classes | 1 (`BrowserManager`) |
| Functions | 4 |
| Import Count | 2 |

**Architecture & Design:**
Context manager for Playwright Chromium browser lifecycle. Implements anti-detection: custom User-Agent, webdriver property spoofing via `init_script`, disabled Blink automation features.

**Correctness Analysis:**
- Context manager correctly returns `False` in `__exit__` — exceptions propagate as expected
- Close is idempotent — checks each resource before closing
- `init_script` fragile — `Object.defineProperty(navigator, 'webdriver', {get: () => undefined})` may not work in all browser contexts

**Security Analysis:**
- **ToS violation** (F6-02): Disabling webdriver detection violates HLTV Terms of Service. Acknowledged in comments but no mitigation — legal risk for production deployment.
- No origin policy checks — Playwright allows cross-origin requests

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-10 | MEDIUM | Security/Legal | ~~REMOVED — browser/manager.py no longer exists~~ | — |
| R3-I05 | INFO | Correctness | init_script assumes navigator.webdriver is configurable — may fail in Secure Context (HTTPS) silently | Add try-catch in init_script |

---

### 5.8 `cache/proxy.py` — HLTV response caching with TTL

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 121 |
| Classes | 1 (`HLTVCachingProxy`) |
| Functions | 5 |
| Import Count | 4 |

**Architecture & Design:**
SQLite-based persistent cache with TTL expiration. Singleton pattern via module-level `_proxy_instance`. Uses `INSERT OR REPLACE` for idempotent writes.

**Correctness Analysis:**
- **Finding R3-05**: TTL uses naive datetime (`datetime.datetime.now()`) at line 92, but `hltv_api_service.py` uses timezone-aware `datetime.now(timezone.utc)` at line 273. This inconsistency causes TTL calculation errors at DST boundaries — cached entries may expire early or persist beyond intended TTL.
- Singleton `get_proxy()` not thread-safe (lines 113-120): check-then-set race condition could create multiple instances
- No expired record cleanup — SQLite DB grows unbounded as old records accumulate
- Parameterized queries used throughout — SQL injection safe

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-05 | HIGH | Correctness | ~~REMOVED — cache/proxy.py no longer exists~~ | — |
| R3-M13 | MEDIUM | Concurrency | ~~REMOVED — cache/proxy.py no longer exists~~ | — |
| R3-I06 | INFO | Performance | No expired record cleanup — SQLite DB grows unbounded | Add periodic VACUUM or cleanup on startup |

---

### 5.9 `collectors/players.py` — Player data collection via ID enumeration

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 163 |
| Classes | 1 (`PlayerCollector`) |
| Functions | 5 |
| Import Count | 4 |

**Architecture & Design:**
Two-pass player discovery: (1) enumerate player IDs 1-35000 checking for valid profiles, (2) extract stats from validated profiles. Uses Playwright page navigation with rate limiting.

**Correctness Analysis:**
- Profile validation multi-layered (HTTP status + URL check + visible element check) — robust
- Reference player ID 21266 appended for calibration — consistent with hltv_api_service.py
- **Performance concern**: Brute-force ID enumeration of 35k IDs at 2s per attempt = 19.4 hours. No parallelization.
- URL parsing fragile (line 81): `url.split("/")[-1]` assumes URL ends with player name — trailing `/` or query params break parsing

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M14 | MEDIUM | Performance | ~~REMOVED — collectors/players.py no longer exists~~ | — |
| R3-M15 | MEDIUM | Correctness | ~~REMOVED — collectors/players.py no longer exists~~ | — |

**Positive Observations:**
- Anti-fabrication philosophy: `_parse_required_stat()` raises ValueError on missing required stats rather than using fallback defaults — strong design principle
- Multi-layered profile validation prevents false positives in player enumeration

---

### 5.10 `hltv_scraper.py` — HLTV sync entry point

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 58 |
| Classes | 0 |
| Functions | 1 |
| Import Count | 1 |

**Architecture & Design:**
Thin entry point delegating to `HLTVStatFetcher`. Lazy import pattern allows skipping HLTV sync if dependencies (beautifulsoup4) not installed.

**Correctness Analysis:**
- ImportError caught with helpful user message — good UX
- Returns 0 on all errors — ambiguous: callers cannot distinguish "sync ran, 0 players found" from "sync failed to start"
- No partial failure tracking — if 40/50 players succeed and 10 fail, returns 40 without indicating failures

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-I07 | INFO | Correctness | Return value 0 ambiguous — "no players found" vs "import/sync failed" | Return None on failure, 0 for "no players found" |

---

## 6. INGESTION PIPELINE

### 6.1 `demo_loader.py` — Main demo loading and caching orchestrator

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 507 |
| Classes | 1 (`DemoLoader`) |
| Functions | 10 + 4 helpers |
| Cyclomatic Complexity (max) | 15 |
| Import Count | 11 |

**Architecture & Design:**
Three-pass demo parsing with HMAC-signed pickle caching:
1. Position extraction (baseline)
2. Nade parsing (trajectory reconstruction)
3. Full state extraction (game frames)

HMAC key derived from hostname + UID — single-user system integrity protection.

**Correctness Analysis:**
- **Finding R3-02**: Money field fallback chain (`balance` → `cash` → `money` → `m_iAccount`) silently defaults to 0 when all fields missing. No assertion or warning that money field was not found. ML models will see 0.0 money for all players when field is missing — indistinguishable from "player has $0".
- `inventory=[]` hardcoded (line 420) — equipment tracking disabled entirely. Equipment-based ML features all receive zero input.
- Nade duration capping at MAX_NADE_DURATION=20s is arbitrary heuristic (lines 165-169) — admitted in comment. When end events missing, durations capped without visibility to downstream consumers.
- Nade thrower fallback: 15-tick backward search (lines 154-159) could return position from different round — spatially invalid
- Map-agnostic segmentation: single `default_map` assumed even for multi-map tournaments

**Security Analysis:**
- Pickle deserialization after HMAC verification (line 50) — safe as long as HMAC key not compromised
- HMAC key derived from hostname + UID — sufficient for single-user systems
- Cache files in predictable location adjacent to `__file__` — on shared systems, other users could read cached game state

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-02 | HIGH | Correctness | Money field fallback chain defaults to 0 when all fields missing — ML models cannot distinguish "missing" from "$0" | Return None/NaN for missing money; add `data_quality: "money_missing"` flag |
| R3-H01 | HIGH | Correctness | inventory=[] hardcoded — all equipment-based ML features receive zero input | Implement equipment tracking from demoparser2 tick data |
| R3-H02 | HIGH | Correctness | Nade duration capping at 20s heuristic — temporal ML models learn false duration distributions | Flag capped values as approximate; exclude from training or mark quality |

**Positive Observations:**
- HMAC-signed pickle caching is well-designed — provides integrity verification without crypto overhead
- Three-pass architecture allows incremental parsing — cache hit on first pass skips expensive re-parsing
- File-size-based cache invalidation is pragmatic and correct

---

### 6.2 `integrity.py` — Demo file integrity validation

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 54 |
| Functions | 3 |
| Import Count | 3 |

**Architecture & Design:**
Thin wrapper around `demo_format_adapter.validate_demo_file()` with streaming SHA-256 computation (8KB chunks).

**Correctness Analysis:**
- SHA-256 streaming (8KB chunks) is optimal for filesystem cache alignment
- MIN_SIZE and MAX_SIZE constants defined but never used — misleading

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-I08 | INFO | Maintainability | Unused MIN_SIZE/MAX_SIZE constants — validation delegated to adapter | Remove or mark as deprecated |

---

### 6.3 `steam_locator.py` — Multi-fallback Steam installation discovery

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 136 |
| Functions | 9 |
| Import Count | 5 |

**Architecture & Design:**
Multi-fallback path discovery: Windows Registry → hardcoded paths → psutil partition scan → hardcoded drive letters. Duplicate of `steam_demo_finder.py` (F6-11 acknowledged).

**Correctness Analysis:**
- Registry lookup error handling too broad — `except Exception` catches everything without logging specific error type
- psutil fallback partition scan covers non-standard drive configurations
- Hardcoded Linux paths include `.steam/steam` and `.local/share/Steam` but miss Flatpak/Proton paths
- No result caching — path discovery re-executed on every call

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M16 | MEDIUM | Maintainability | Duplicate of steam_demo_finder.py — two independent implementations (F6-11) | Consolidate into single module (same as R3-M05) |

---

### 6.4 `pipelines/json_tournament_ingestor.py` — Tournament JSON batch import

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 129 |
| Functions | 7 |
| Import Count | 4 |

**Architecture & Design:**
Recursive JSON traversal for tournament data export files. Extracts per-round, per-team statistics into flat records for CSV output.

**Correctness Analysis:**
- Division by zero handled gracefully (accuracy = hits/shots if shots > 0 else 0) — but 0 is indistinguishable from "missing"
- No JSON schema validation — malformed tournament exports silently produce partial/incorrect output
- Match ID nullable — `data.get("id")` could be None, passed without validation

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M17 | MEDIUM | Correctness | No JSON schema validation — malformed tournament data silently produces incorrect output | Add schema validation with descriptive error messages |

---

### 6.5 `pipelines/user_ingest.py` — User demo ingestion pipeline

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 56 |
| Functions | 4 |
| Import Count | 5 |

**Architecture & Design:**
Thin pipeline wrapper delegating to `parse_demo()` and `extract_match_stats()`. Archives demo after successful processing.

**Correctness Analysis:**
- Only match-level stats extracted — round-level and event-level data NOT extracted here, requiring separate enrichment calls
- **No transaction rollback**: Demo archived (shutil.move) even if ML pipeline trigger fails — cannot recover or retry
- Circular dependency: imports `run_ml_pipeline` from `run_ingestion` inside function (line 48) — avoids module-level cycle but adds runtime import cost

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-H03 | HIGH | Reliability | Demo archived before ML pipeline completion — if ML fails, demo is "processed" but analysis incomplete | Archive only after full pipeline success |

---

### 6.6 `registry/lifecycle.py` — TTL-based demo cleanup

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 26 |
| Classes | 1 (`DemoLifecycleManager`) |
| Functions | 2 |

**Architecture & Design:**
Simple TTL-based cleanup: deletes processed demos older than 30 days.

**Correctness Analysis:**
- Unix timestamp arithmetic correct: `now - (days * 86400)` — ignores leap seconds but acceptable
- No dry-run option — always destructive
- Hardcoded 30-day TTL — no configuration

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-I09 | INFO | Configuration | Hardcoded 30-day TTL with no configuration option | Accept TTL parameter from config |

---

### 6.7 `registry/registry.py` — JSON-backed demo tracking

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 87 |
| Classes | 1 (`DemoRegistry`) |
| Functions | 6 |

**Architecture & Design:**
JSON-serialized list with in-memory Set[str] for O(1) lookup (F6-20). Backup recovery on corruption with two-stage fallback.

**Correctness Analysis:**
- **Finding R3-08**: No thread safety — `mark_processed()` reads set, adds element, writes file as non-atomic sequence. Concurrent callers corrupt JSON file.
- If `_save()` fails, in-memory set is updated but file is unchanged — reboot causes re-processing
- Backup created BEFORE write — if backup creation fails, write proceeds anyway

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-08 | MEDIUM | Concurrency | ~~RESOLVED — registry now uses threading.Lock + FileLock~~ | — |
| R3-H04 | HIGH | Reliability | In-memory set diverges from file on write failure — reboot causes duplicate processing | Use write-ahead pattern: write temp file, atomic rename |

---

### 6.8 `registry/schema.sql` — Registry database schema

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 0 (empty file) |

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-I10 | INFO | Completeness | Empty schema file — placeholder or not yet implemented | Remove if not needed; implement if SQLite registry is planned |

---

## 7. BACKEND INGESTION LAYER

### 7.1 `csv_migrator.py` — CSV data migration to database

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 207 |
| Classes | 1 (`CSVMigrator`) |
| Functions | 4 |
| Import Count | 5 |

**Architecture & Design:**
Migrates CSV data (playstyle profiles, tournament statistics) into SQLModel tables with idempotency checks and batch commits (1000 rows per transaction).

**Correctness Analysis:**
- Playstyle idempotency: checks `player_name + team_name` uniqueness before insert — correct
- **Tournament stats idempotency DISABLED** (lines 169-170) — "For speed" comment. Re-running migration duplicates records.
- Role mapping hardcoded: string "Lurker" → binary probabilities. Fuzzy roles ("Lurker/Entry") fail silently.
- External match_id stored but match_id=0 hardcoded (line 174) — orphaned reference

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-H05 | HIGH | Correctness | Tournament stats idempotency disabled — re-running migration duplicates data | Re-enable idempotency check; accept performance cost |
| R3-M18 | MEDIUM | Correctness | Role mapping hardcoded with binary probabilities — fuzzy roles silently produce all-zero vectors | Use fuzzy matching or explicit mapping table |

---

### 7.2 `resource_manager.py` — System resource monitoring and throttling

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 202 |
| Classes | 1 (`ResourceManager`) |
| Functions | 8 (all static) |
| Import Count | 5 |

**Architecture & Design:**
CPU monitoring with 10-sample moving average, hysteresis-based throttle control (separate high/low thresholds to prevent toggle thrashing), and per-lock separation for CPU sampling vs throttle state.

**Correctness Analysis:**
- Hysteresis control is well-designed (F6-18) — prevents rapid throttle on/off switching
- Non-blocking CPU sampling via `psutil.cpu_percent(interval=None)` — uses cached value
- Bootstrap CPU sample blocks for 50ms on first call — could stall caller
- No upper bound on worker count — `total_cores - 1` could be very large on NUMA systems (256+ cores)
- `is_gui_active()` calls `psutil.process_iter()` — O(num_processes) scan, 50-200ms per call

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M19 | MEDIUM | Performance | `is_gui_active()` scans all system processes (50-200ms) — called frequently from ingestion loop | Cache result with 1-second TTL |

---

### 7.3 `watcher.py` — Filesystem event monitoring for demo files

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 217 |
| Classes | 2 (`DemoFileHandler`, `IngestionWatcher`) |
| Functions | 13 |
| Import Count | 6 |

**Architecture & Design:**
Watchdog-based filesystem monitoring with stability debouncing (waits for file size to stabilize before queueing). Uses threading.Timer for delayed stability checks and event-based wake-up signals to session_engine.

**Correctness Analysis:**
- Stability debouncing prevents ingesting partial files — bounded at MAX_STABILITY_ATTEMPTS=30 (~30 seconds)
- FILE_MINIMUM_SIZE = 1024 bytes (1KB) — too small for valid CS2 demos (should be 5-10MB)
- Timer cancellation race: if timer is already executing when `cancel()` called, no effect — could process file prematurely
- File accessibility check uses read-only open (F6-24) — doesn't mutate file timestamp

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M20 | MEDIUM | Correctness | FILE_MINIMUM_SIZE = 1KB too small for valid CS2 demos — corrupted 1KB files will be accepted | Raise to 5MB minimum |

---

## 8. BACKEND CONTROL LAYER

### 8.1 `console.py` — Unified system controller and service supervisor

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 495 |
| Classes | 3 (`SystemState`, `ServiceSupervisor`, `Console`) |
| Functions | 18 |
| Import Count | 12 |

**Architecture & Design:**
Central control module implementing singleton Console with thread-safe initialization, service supervisor with PID tracking and auto-restart, TTL-based status caching (baseline: 60s, training_data: 120s), and cascade initialization with partial cleanup on failure.

**Correctness Analysis:**
- Double-checked locking for singleton initialization (lines 179-187) — correct
- **Timer-based auto-restart race**: Timer fires after lock released (line 149). If process restarted manually before timer fires, could spawn duplicate process.
- **Stale cache after DB failure**: `_get_baseline_status()` catches exceptions, caches empty dict for 60s — DB recovery won't show until cache expires
- `Path.rglob("*.dem")` for demo counting (line 434) — can hang indefinitely on network drives

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-H06 | HIGH | Concurrency | Timer-based auto-restart race — manual restart + timer fire can spawn duplicate processes | Add guard flag checked before restart; use Lock in timer callback |
| R3-M21 | MEDIUM | Correctness | Stale cache after DB failure — empty status cached for 60s despite DB recovery | Invalidate cache on error instead of caching error state |

---

### 8.2 `db_governor.py` — Database audit and integrity enforcement

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 125 |
| Classes | 1 (`DatabaseGovernor`) |
| Functions | 4 |
| Import Count | 4 |

**Architecture & Design:**
Authoritative controller for three-tier storage (Monolith, HLTV metadata, per-match). Provides audit, integrity verification (fast/full modes), index rebuilding, and match data pruning.

**Correctness Analysis:**
- `PRAGMA quick_check` is NOT transactional — concurrent writes during check produce inconsistent results
- Full integrity check can take 5-30 minutes on 16GB database — no timeout, blocks caller
- Size calculation double-counts WAL files (ephemeral, reclaimed on checkpoint)

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-H07 | HIGH | Concurrency | PRAGMA quick_check blocks for minutes with no timeout — freezes UI thread if called from status endpoint | Run only from background thread; add timeout via separate thread with join(timeout) |
| R3-M22 | MEDIUM | Concurrency | hltv_metadata.db creation not atomic — two threads could both create file simultaneously | Use atomic file creation with exclusive lock |

---

### 8.3 `ingest_manager.py` — Threaded queue processing orchestrator

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 258 |
| Classes | 2 (`IngestMode`, `IngestionManager`) |
| Functions | 10 |
| Import Count | 7 |

**Architecture & Design:**
Unified queue processor with three modes (SINGLE, CONTINUOUS/30s rescan, TIMED). Event-based stop signal avoids busy-polling. Crash recovery resets stuck tasks to queued state with retry counter.

**Correctness Analysis:**
- **Finding R3-06**: Race between discovery and enqueue — `list_new_demos()` called at line 113, but files could be deleted between discovery and enqueue loop (lines 126-130). Could enqueue file that no longer exists.
- `_is_running` and `_stop_requested` not interlocked — race between `scan_all()` check-and-set and concurrent `stop()` call
- Session lifetime confusion: session created for `_queue_files`, closed before ingestion — `_ingest_single_demo` accessing same task object could trigger DetachedInstanceError

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-06 | HIGH | Concurrency | ~~RESOLVED — file existence guard added before enqueue~~ | — |
| R3-H08 | HIGH | Correctness | ~~RESOLVED — task data extracted inside session, re-fetched for update~~ | — |

---

### 8.4 `ml_controller.py` — Training lifecycle control

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 121 |
| Classes | 2 (`MLControlContext`, `MLController`) |
| Functions | 7 |
| Import Count | 3 |

**Architecture & Design:**
Control context token pattern: `MLControlContext` passed to training loop, allowing real-time intervention (pause/resume/stop/throttle). Event-based pause avoids busy-wait. Custom `TrainingStopRequested` exception replaces StopIteration for thread safety.

**Correctness Analysis:**
- `check_state()` uses Event-based blocking for pause — efficient, avoids CPU spinning
- `_stop_requested` checked without lock (line 34) — race with concurrent `request_stop()`
- `_throttle_factor` is a float, not atomic — torn reads possible under concurrent modification
- `TrainingStopRequested` replaces `StopIteration` correctly — avoids Python generator interaction issues

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M23 | MEDIUM | Concurrency | check_state() reads _stop_requested without lock — race with concurrent request_stop() | Add Lock to stop_requested check-and-act sequence |

**Positive Observations:**
- Control context token pattern is excellent design — allows clean separation between training loop and control plane
- Event-based pause is the correct mechanism — no CPU waste during pause
- `TrainingStopRequested` custom exception is the right approach for thread-safe training interruption

---

## 9. ENTRY POINTS & SERVICE DAEMONS

### 9.1 `run_ingestion.py` — Core demo parsing and ML pipeline trigger

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 1,180 |
| Classes | 0 |
| Functions | ~20 |
| Cyclomatic Complexity (max) | 18 |
| Import Count | 15 |

**Architecture & Design:**
The largest single module in the data acquisition domain. Implements two-phase parsing (aggregate stats + sequential ticks), vectorized bulk insertion via `pandas.to_sql()` (achieving 8x speedup from 762s to 97s), circular angle interpolation for yaw/pitch wrap-around, and bounded state lookup caching.

**Correctness Analysis:**
- **Finding R3-04**: Duplicate demo check uses `demo_name` as-is (line 47-71), but `_save_player_stats` uses `Path(demo_name).stem` (line 449) — "match_123.dem" vs "match_123" could bypass duplicate detection
- NaN/Inf in player stats not sanitized — `_sanitize_value()` exists but never called on aggregate stats
- Circular angle interpolation (lines 495-527) correctly uses arctan2 for wrap-around handling — yaw normalized to [0, 360)
- State lookup bounded at 50k entries (line 570) — prevents OOM but uses linear scan for eviction instead of true LRU
- Pro demo handling may bloat legacy table with per-player duplicate rows (lines 1091-1097)
- Progress percentages hardcoded and non-proportional (10% → 20% → 25% → 40%) — misleading UX

**Performance Analysis:**
- Vectorized bulk insert: `pandas.to_sql()` bypasses ORM overhead — 8x speedup confirmed
- Circular interpolation: vectorized sin/cos/arctan2 via pandas — efficient for 2.4M rows
- State lookup: bounded at 50k entries — prevents OOM on large demos

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-04 | HIGH | Correctness | ~~RESOLVED — demo name now normalized via Path().stem~~ | — |
| R3-H09 | HIGH | Correctness | NaN/Inf in player stats not sanitized before DB insert — _sanitize_value() exists but unused for aggregates | Call _sanitize_value() on all aggregate stats before DB insertion |
| R3-M24 | MEDIUM | Performance | State lookup eviction uses linear scan instead of LRU — O(n) per eviction | Use collections.OrderedDict for true LRU eviction |

**Positive Observations:**
- Vectorized bulk insert achieving 8x speedup is excellent engineering
- Circular angle interpolation is mathematically correct (arctan2 + sin/cos decomposition)
- Bounded state lookup cache prevents OOM on large demos
- Module is well-commented with explicit F-code remediation references

---

### 9.2 `run_worker.py` — Background queue worker

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 149 |
| Functions | 5 |
| Import Count | 6 |

**Architecture & Design:**
Standalone background worker with signal-based graceful shutdown. Self-healing: recovers stuck tasks on startup. Shares stop signal file with HLTV service.

**Correctness Analysis:**
- Task fetching correctly extracts dict from SQLModel object before session closes — prevents DetachedInstanceError
- Archive directory not validated before file move — could fail on symlinks or directories
- Duplicate task execution: no atomic check-and-lock — two workers could fetch same task
- Pro task skip logic is racy — task count check and sleep not atomic

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M25 | MEDIUM | Concurrency | No atomic task claiming — two workers could fetch and execute same demo simultaneously | Use database UPDATE ... WHERE status='queued' RETURNING for atomic task claiming |

---

### 9.3 `hltv_sync_service.py` — Background daemon for pro stats scraping

**File Metrics:**

| Metric | Value |
|--------|-------|
| Lines of Code | 180 |
| Functions | 5 |
| Import Count | 5 |

**Architecture & Design:**
Background daemon for HLTV pro player statistics scraping. Dormant mode on failure (6-hour sleep), FlareSolverr auto-start, persistent session reuse, PID file coordination.

**Correctness Analysis:**
- Dormant sleep checks stop signal every 1 second — responsive to shutdown
- FlareSolverr availability check has no explicit timeout — could hang indefinitely
- PID file race condition — two processes could both check "no PID file", both write
- No exponential backoff on persistent FlareSolverr errors mid-loop

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-M26 | MEDIUM | Resilience | FlareSolverr availability check has no timeout — could hang indefinitely on slow network | Add explicit timeout to FlareSolverr health check |

---

## 10. PACKAGE & MODULE INIT FILES

The following `__init__.py` files are empty module markers with 0-1 LOC:

| File | LOC | Assessment |
|------|-----|------------|
| `backend/data_sources/__init__.py` | 1 | Module marker |
| `backend/data_sources/hltv/__init__.py` | 1 | Module marker |
| `backend/data_sources/hltv/browser/__init__.py` | 1 | Empty |
| `backend/data_sources/hltv/cache/__init__.py` | 1 | Re-exports `HLTVCachingProxy, get_proxy` |
| `backend/data_sources/hltv/collectors/__init__.py` | 1 | Empty |
| `ingestion/__init__.py` | 1 | Module marker |
| `ingestion/pipelines/__init__.py` | 1 | Empty |
| `ingestion/registry/__init__.py` | 1 | Empty |
| `backend/ingestion/__init__.py` | 1 | Module marker |
| `backend/control/__init__.py` | 0 | Empty |

All init files are appropriate — no unnecessary imports, no circular dependency risks.

---

## 11. README DOCUMENTATION ASSESSMENT

15 README files (5 sets × 3 languages: EN/IT/PT) cover the data sources, HLTV, ingestion, pipelines, and registry sub-packages.

**Accuracy Assessment:**
- `backend/data_sources/README.md` references `hltv_metadata.py` which doesn't exist as a standalone file — stale reference
- `ingestion/README.md` references `hltv_orchestrator.py` and `downloader.py` which don't exist in the current codebase — stale references from removed modules
- HLTV README correctly describes rate limiting, caching, and error handling architecture
- All READMEs consistently available in three languages (EN/IT/PT) — good i18n discipline

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R3-I11 | INFO | Documentation | READMEs reference removed modules (hltv_metadata.py, hltv_orchestrator.py, downloader.py) | Update READMEs to match current file inventory |

---

## 12. CONSOLIDATED FINDINGS MATRIX

### Findings by Severity

#### HIGH Findings (8)

| ID | File | Category | Finding | Recommendation | Cross-Ref |
|----|------|----------|---------|----------------|-----------|
| R3-01 | demo_parser.py | Correctness | Hardcoded KAST fallback (0.70) fabricates ML training data | Mark as NaN; let training pipeline filter | C-05 |
| R3-02 | demo_loader.py | Correctness | Money field fallback chain silently defaults to 0 | Return NaN; add data_quality flag | C-04 |
| R3-03 | hltv_api_service.py | Concurrency | ~~REMOVED — hltv_api_service.py no longer exists~~ | — | F6-10 |
| R3-04 | run_ingestion.py | Correctness | ~~RESOLVED — demo name now normalized via Path().stem~~ | — | — |
| R3-05 | cache/proxy.py | Correctness | ~~REMOVED — cache/proxy.py no longer exists~~ | — | F6-04 |
| R3-06 | ingest_manager.py | Concurrency | ~~RESOLVED — file existence guard added before enqueue~~ | — | — |
| R3-H01 | demo_loader.py | Correctness | inventory=[] hardcoded — equipment ML features all zero | Implement equipment tracking | — |
| R3-H02 | demo_loader.py | Correctness | Nade duration capping at 20s — false temporal distributions | Flag as approximate; exclude from training | — |
| R3-H03 | user_ingest.py | Reliability | Demo archived before ML pipeline completion | Archive only after full success | — |
| R3-H04 | registry.py | Reliability | In-memory set diverges from file on write failure | Write-ahead pattern: temp file → atomic rename | — |
| R3-H05 | csv_migrator.py | Correctness | Tournament stats idempotency disabled | Re-enable idempotency check | — |
| R3-H06 | console.py | Concurrency | Timer-based auto-restart race — duplicate process spawn | Add guard flag in timer callback | — |
| R3-H07 | db_governor.py | Concurrency | PRAGMA quick_check blocks for minutes with no timeout | Run from background thread with timeout | F5-31 |
| R3-H08 | ingest_manager.py | Correctness | ~~RESOLVED — task data extracted inside session, re-fetched for update~~ | — | — |
| R3-H09 | run_ingestion.py | Correctness | NaN/Inf in player stats not sanitized before DB insert | Call _sanitize_value() on aggregates | — |

#### MEDIUM Findings (15)

| ID | File | Category | Finding | Recommendation | Cross-Ref |
|----|------|----------|---------|----------------|-----------|
| R3-07 | stat_fetcher.py | Correctness | CSS selector fragility — HLTV redesign breaks extraction silently | Add selector validation tests | — |
| R3-08 | registry.py | Concurrency | ~~RESOLVED — registry now uses threading.Lock + FileLock~~ | — | F6-20 |
| R3-09 | faceit_integration.py | Security | ~~RESOLVED — match_id sanitized against directory traversal~~ | — | OWASP A01 |
| R3-10 | browser/manager.py | Security/Legal | ~~REMOVED — browser/manager.py no longer exists~~ | — | F6-02 |
| R3-M01 | demo_format_adapter.py | Correctness | MIN_DEMO_SIZE = 1KB too small | Raise to 1MB | — |
| R3-M03 | event_registry.py | Correctness | Handler paths not validated at registration | Add startup validation | — |
| R3-M04 | steam_api.py | Correctness | No input validation on steam_id format | Validate 17-digit format | — |
| R3-M05 | steam_demo_finder.py | Maintainability | Duplicate Steam path discovery (F6-11) | Consolidate into core/path_utils.py | F6-11 |
| R3-M06 | faceit_api.py | Architecture | Duplicate FaceIT client | Remove; use faceit_integration.py | — |
| R3-M08 | hltv_api_service.py | Correctness | ~~REMOVED — hltv_api_service.py no longer exists~~ | — | — |
| R3-M12 | flaresolverr_client.py | Correctness | Silent error suppression — all exceptions return None | Return error envelopes | — |
| R3-M13 | cache/proxy.py | Concurrency | ~~REMOVED — cache/proxy.py no longer exists~~ | — | — |
| R3-M17 | json_tournament_ingestor.py | Correctness | No JSON schema validation | Add schema validation | — |
| R3-M20 | watcher.py | Correctness | FILE_MINIMUM_SIZE = 1KB too small | Raise to 5MB | — |
| R3-M25 | run_worker.py | Concurrency | No atomic task claiming — duplicate execution possible | Use UPDATE...WHERE...RETURNING | — |

#### LOW Findings (12)

| ID | File | Category | Finding |
|----|------|----------|---------|
| R3-L01 | demo_parser.py | Correctness | data_quality flag not propagated to DB model |
| R3-L02 | round_context.py | Correctness | bomb_exploded event may not be standard demoparser2 |
| R3-L03 | round_context.py | Correctness | time_in_round clipping hides data quality issues |
| R3-L04 | trade_kill_detector.py | Correctness | Trade window boundary exclusive despite "inclusive" comment |
| R3-L05 | trade_kill_detector.py | Correctness | Team roster misses mid-match player substitutions |
| R3-L06 | steam_api.py | Correctness | Inconsistent error handling (403 raises, empty returns None) |
| R3-L07 | steam_demo_finder.py | Correctness | CS2_REPLAY_PATH hardcoded — custom libraries not searched |
| R3-L08 | faceit_api.py | Correctness | Silent empty-dict error return |
| R3-L09 | faceit_integration.py | Security | API key in session headers could be exposed |
| R3-L10 | stat_fetcher.py | Correctness | Random sleep unseeded — non-deterministic testing |
| R3-L11 | docker_manager.py | Configuration | Hardcoded port 8191 for FlareSolverr |
| R3-L12 | flaresolverr_client.py | Concurrency | _session_id shared across threads |

#### INFO Findings (7)

| ID | File | Category | Finding |
|----|------|----------|---------|
| R3-I01 | event_registry.py | Coverage | 11/26 event types implemented (42%) |
| R3-I02 | selectors.py | Maintainability | No automated tests for selector validity |
| R3-I03 | rate_limit.py | Testing | Unseeded randomness for anti-detection |
| R3-I04 | docker_manager.py | Maintainability | Italian error messages mixed with English |
| R3-I05 | browser/manager.py | Correctness | init_script may fail silently in Secure Context |
| R3-I06 | cache/proxy.py | Performance | No expired record cleanup — DB grows unbounded |
| R3-I07 | hltv_scraper.py | Correctness | Return value 0 ambiguous |
| R3-I08 | integrity.py | Maintainability | Unused MIN_SIZE/MAX_SIZE constants |
| R3-I09 | lifecycle.py | Configuration | Hardcoded 30-day TTL |
| R3-I10 | schema.sql | Completeness | Empty schema file |
| R3-I11 | READMEs | Documentation | References to removed modules |

### Findings by Category

| Category | HIGH | MED | LOW | INFO | Total |
|----------|------|-----|-----|------|-------|
| Correctness | 7 | 6 | 6 | 3 | 22 |
| Concurrency | 5 | 3 | 1 | 0 | 9 |
| Security | 0 | 2 | 1 | 0 | 3 |
| Reliability | 2 | 0 | 0 | 0 | 2 |
| Architecture | 0 | 1 | 0 | 0 | 1 |
| Performance | 0 | 1 | 0 | 1 | 2 |
| Maintainability | 0 | 2 | 0 | 2 | 4 |
| Configuration | 0 | 0 | 1 | 1 | 2 |
| Documentation | 0 | 0 | 0 | 1 | 1 |
| Coverage | 0 | 0 | 0 | 1 | 1 |
| **Total** | **14** | **15** | **10** | **9** | **47** |

### Findings Trend (vs Prior Audits)
- **Previously Fixed**: 18 items from F5-*, F6-*, F7-* remediation phases (circuit breaker pattern, timezone awareness, logging format, process cleanup)
- **Persisting**: Steam path duplication (F6-11) remains unresolved across two implementations
- **New**: 42 new findings identified in this audit, primarily in concurrency (9), correctness (22), and data quality contamination areas

---

## 13. RECOMMENDATIONS

### Immediate Actions (HIGH severity)

1. **R3-01 — Remove KAST Fallback**: Replace hardcoded 0.70 KAST with NaN/None. Add `data_quality` flag to `PlayerMatchStats`. Estimated complexity: LOW (single-file change + migration).

2. **R3-02 — Money Field Flagging**: Return NaN for missing money fields. Add `data_quality: "money_missing"` flag. Estimated complexity: LOW.

3. **R3-03 — Circuit Breaker Threading**: Add `threading.Lock` to `_CircuitBreaker.record_failure()` and `record_success()`. Estimated complexity: LOW (4-line change).

4. **R3-04 — Normalize Demo Name**: Use `Path(demo_name).stem` consistently in duplicate detection. Estimated complexity: LOW.

5. **R3-05 — Timezone Consistency**: Replace `datetime.now()` with `datetime.now(timezone.utc)` in cache/proxy.py line 92. Estimated complexity: LOW.

6. **R3-06 — File Existence Validation**: Validate file existence at processing time in ingest_manager.py, not just at discovery. Estimated complexity: LOW.

### Short-Term Actions (MEDIUM severity)

7. **R3-07 — Selector Validation**: Add integration tests with cached sample HLTV HTML pages. Estimated complexity: MEDIUM.

8. **R3-08 — Registry Thread Safety**: Migrate DemoRegistry from JSON file to SQLite-backed storage, or add file-level locking. Estimated complexity: MEDIUM.

9. **R3-09 — Match ID Sanitization**: Add regex sanitization to FaceIT download path. Estimated complexity: LOW.

10. **R3-10 — ToS Configuration**: Add configuration flag for webdriver spoofing, require explicit opt-in. Estimated complexity: LOW.

11. **R3-M05/M06 — Code Consolidation**: Remove `faceit_api.py` (duplicate). Consolidate Steam path discovery into shared utility. Estimated complexity: MEDIUM.

### Long-Term Actions (LOW + Strategic)

12. **Data Quality Pipeline**: Implement comprehensive data quality tracking — every field that uses a fallback should be flagged with its quality status, propagated to training pipeline for filtering.

13. **Atomic Operations**: Implement write-ahead logging pattern for demo registry, atomic task claiming in worker, and archive-after-success semantics in user_ingest.

14. **HLTV Resilience**: Implement progressive player discovery (start from rankings, not brute-force IDs), add selector versioning with fallback to previous known-good selectors.

### Architectural Recommendations

15. **Silent Fallback Elimination**: Adopt project-wide policy — no silent defaults that contaminate ML training. Every fallback must be flagged with `data_quality` metadata.

16. **Concurrency Model**: The data acquisition domain is the most concurrency-sensitive in the project (Tri-Daemon + background workers + HLTV sync). Consider adopting a formal concurrency model: either full thread-safety with explicit locks, or move to asyncio for I/O-bound operations.

---

## APPENDIX A: COMPLETE FILE INVENTORY

| # | File Path | LOC | Classes | Functions | Findings |
|---|-----------|-----|---------|-----------|----------|
| 1 | backend/data_sources/__init__.py | 1 | 0 | 0 | 0 |
| 2 | backend/data_sources/demo_parser.py | 476 | 0 | 8 | 3 (1H/1M/1L) |
| 3 | backend/data_sources/demo_format_adapter.py | 284 | 1 | 12 | 2 (2M) |
| 4 | backend/data_sources/event_registry.py | 356 | 2 | 14 | 2 (1M/1I) |
| 5 | backend/data_sources/round_context.py | 224 | 0 | 5 | 2 (2L) |
| 6 | backend/data_sources/trade_kill_detector.py | 353 | 1 | 6 | 2 (2L) |
| 7 | backend/data_sources/steam_api.py | 106 | 0 | 3 | 2 (1M/1L) |
| 8 | backend/data_sources/steam_demo_finder.py | 252 | 1 | 8 | 2 (1M/1L) |
| 9 | backend/data_sources/faceit_api.py | 37 | 0 | 3 | 2 (1M/1L) |
| 10 | backend/data_sources/faceit_integration.py | 274 | 1 | 8 | 3 (2M/1L) |
| 11 | backend/data_sources/hltv_scraper.py | 58 | 0 | 1 | 1 (1I) |
| 12 | backend/data_sources/hltv/__init__.py | 1 | 0 | 0 | 0 |
| 13 | backend/data_sources/hltv/hltv_api_service.py | 287 | 2 | 10 | 3 (1H/2M) |
| 14 | backend/data_sources/hltv/stat_fetcher.py | 377 | 1 | 12 | 3 (1M/1M/1L) |
| 15 | backend/data_sources/hltv/selectors.py | 29 | 2 | 1 | 2 (1M/1I) |
| 16 | backend/data_sources/hltv/rate_limit.py | 33 | 1 | 1 | 1 (1I) |
| 17 | backend/data_sources/hltv/docker_manager.py | 138 | 0 | 7 | 2 (1L/1I) |
| 18 | backend/data_sources/hltv/flaresolverr_client.py | 145 | 1 | 5 | 2 (1M/1L) |
| 19 | backend/data_sources/hltv/browser/__init__.py | 1 | 0 | 0 | 0 |
| 20 | backend/data_sources/hltv/browser/manager.py | 61 | 1 | 4 | 2 (1M/1I) |
| 21 | backend/data_sources/hltv/cache/__init__.py | 1 | 0 | 0 | 0 |
| 22 | backend/data_sources/hltv/cache/proxy.py | 121 | 1 | 5 | 3 (1H/1M/1I) |
| 23 | backend/data_sources/hltv/collectors/__init__.py | 1 | 0 | 0 | 0 |
| 24 | backend/data_sources/hltv/collectors/players.py | 163 | 1 | 5 | 2 (2M) |
| 25 | ingestion/__init__.py | 1 | 0 | 0 | 0 |
| 26 | ingestion/demo_loader.py | 507 | 1 | 14 | 3 (3H) |
| 27 | ingestion/integrity.py | 54 | 0 | 3 | 1 (1I) |
| 28 | ingestion/steam_locator.py | 136 | 0 | 9 | 1 (1M) |
| 29 | ingestion/pipelines/__init__.py | 1 | 0 | 0 | 0 |
| 30 | ingestion/pipelines/json_tournament_ingestor.py | 129 | 0 | 7 | 1 (1M) |
| 31 | ingestion/pipelines/user_ingest.py | 56 | 0 | 4 | 1 (1H) |
| 32 | ingestion/registry/__init__.py | 1 | 0 | 0 | 0 |
| 33 | ingestion/registry/lifecycle.py | 26 | 1 | 2 | 1 (1I) |
| 34 | ingestion/registry/registry.py | 87 | 1 | 6 | 2 (1M/1H) |
| 35 | ingestion/registry/schema.sql | 0 | 0 | 0 | 1 (1I) |
| 36 | backend/ingestion/__init__.py | 1 | 0 | 0 | 0 |
| 37 | backend/ingestion/csv_migrator.py | 207 | 1 | 4 | 2 (1H/1M) |
| 38 | backend/ingestion/resource_manager.py | 202 | 1 | 8 | 1 (1M) |
| 39 | backend/ingestion/watcher.py | 217 | 2 | 13 | 1 (1M) |
| 40 | backend/control/console.py | 495 | 3 | 18 | 2 (1H/1M) |
| 41 | backend/control/db_governor.py | 125 | 1 | 4 | 2 (1H/1M) |
| 42 | backend/control/ingest_manager.py | 258 | 2 | 10 | 2 (2H) |
| 43 | backend/control/ml_controller.py | 121 | 2 | 7 | 1 (1M) |
| 44 | run_ingestion.py | 1,180 | 0 | 20 | 3 (1H/1H/1M) |
| 45 | run_worker.py | 149 | 0 | 5 | 1 (1M) |
| 46 | hltv_sync_service.py | 180 | 0 | 5 | 1 (1M) |
| 47 | backend/control/__init__.py | 0 | 0 | 0 | 0 |
| 48-62 | README files (15) | ~1,200 | — | — | 1 (1I) |

---

## APPENDIX B: GLOSSARY

| Term | Definition |
|------|-----------|
| KAST | Kills, Assists, Survived, Traded — percentage of rounds where player contributed |
| KPR | Kills Per Round |
| DPR | Deaths Per Round |
| ADR | Average Damage per Round |
| HLTV 2.0 Rating | Composite performance metric: 0.0073×KAST + 0.3591×KPR - 0.5329×DPR + 0.2372×Impact + 0.0032×ADR + 0.1587 |
| FlareSolverr | Proxy service for bypassing Cloudflare browser challenges via headless Chrome |
| Circuit Breaker | Resilience pattern — stops retrying after N consecutive failures, resets after timeout |
| WAL | Write-Ahead Logging — SQLite journaling mode for concurrent read/write access |
| TRADE_WINDOW_TICKS | 192 ticks (3 seconds at 64Hz) — maximum gap for trade kill detection |
| Tri-Daemon | Three-daemon architecture: Scanner (Hunter), Digester, Teacher |
| COPER | Coaching pipeline: Correction → Observation → Planning → Execution → Review |
| DetachedInstanceError | SQLAlchemy error when accessing ORM object attributes after session close |

---

## APPENDIX C: CROSS-REFERENCE INDEX

| Report Finding | Remediation Code | Status |
|----------------|-----------------|--------|
| R3-03 (Circuit breaker thread safety) | F6-10 | ~~REMOVED — hltv_api_service.py no longer exists~~ |
| R3-05 (Timezone consistency) | F6-04 | ~~REMOVED — cache/proxy.py no longer exists~~ |
| R3-10 (ToS violation) | F6-02 | ~~REMOVED — browser/manager.py no longer exists~~ |
| R3-M05 (Steam path duplication) | F6-11 | Deferred — comment acknowledges duplication |
| R3-08 (Registry thread safety) | F6-20 | ~~RESOLVED — registry now uses threading.Lock + FileLock~~ |
| R3-H07 (PRAGMA timeout) | F5-31 | Acknowledged — comment notes slow performance, no timeout added |
| R3-01 (KAST fallback) | C-05 | Related — data quality contamination category |
| R3-02 (Money fallback) | C-04 | Related — data quality contamination category |
| R3-09 (Directory traversal) | OWASP A01 | ~~RESOLVED — match_id sanitized against directory traversal~~ |

---

## APPENDIX D: DEPENDENCY GRAPH

```
                          ┌─────────────┐
                          │  main.py    │
                          └──────┬──────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              ┌─────▼─────┐ ┌───▼───┐  ┌─────▼─────┐
              │ console.py │ │worker │  │hltv_sync  │
              └─────┬──────┘ └───┬───┘  └─────┬─────┘
                    │            │            │
         ┌──────┬──┴──┬─────┐   │      ┌─────▼──────┐
         │      │     │     │   │      │stat_fetcher│
    ┌────▼──┐ ┌─▼──┐ ┌▼───┐│   │      │ hltv_api   │
    │db_gov │ │ml_ │ │ing.││   │      │ browser    │
    │       │ │ctrl│ │mgr ││   │      │ cache      │
    └───────┘ └────┘ └─┬──┘│   │      │ collector  │
                       │   │   │      │ flaresolv  │
                 ┌─────▼───▼───▼──┐   └────────────┘
                 │ run_ingestion  │
                 └───────┬────────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
     ┌─────▼──────┐ ┌───▼────┐  ┌─────▼─────┐
     │demo_parser │ │demo_   │  │user_ingest│
     │format_adpt │ │loader  │  │json_tourn │
     │event_reg   │ │integrity│ │csv_migrat │
     │round_ctx   │ │steam_loc│ └───────────┘
     │trade_kill  │ │registry │
     └────────────┘ └─────────┘
           │
     ┌─────▼──────┐
     │ steam_api  │
     │ steam_find │
     │ faceit_int │
     └────────────┘
```

---

## APPENDIX E: DATA FLOW DIAGRAMS

### Demo Ingestion Pipeline

```
.dem File
    │
    ▼
┌──────────────────┐     ┌──────────────┐
│ integrity.py     │────▶│ format_adpt  │
│ (SHA-256 + magic)│     │ (validate)   │
└────────┬─────────┘     └──────────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────┐
│ demo_parser.py   │────▶│ DataFrames   │
│ (demoparser2)    │     │ (ticks/events│
└────────┬─────────┘     │  /stats)     │
         │               └──────┬───────┘
         │                      │
    ┌────▼─────┐          ┌─────▼──────┐
    │demo_load │          │round_ctx   │
    │(3-pass + │          │(boundaries)│
    │ cache)   │          └─────┬──────┘
    └────┬─────┘                │
         │               ┌─────▼──────┐
         │               │trade_kill  │
         │               │(detection) │
         │               └─────┬──────┘
         │                      │
         ▼                      ▼
┌──────────────────────────────────────┐
│ run_ingestion.py                     │
│ (interpolation + vectorized insert)  │
│ ┌─────────────┐  ┌────────────────┐  │
│ │ pd.to_sql() │  │ _sanitize()    │  │
│ │ (bulk ins.) │  │ (type coerce)  │  │
│ └──────┬──────┘  └────────────────┘  │
└────────┼─────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ database.db      │
│ (PlayerMatchStats│
│  PlayerTickState │
│  RoundStats)     │
└──────────────────┘
```

### HLTV Scraping Pipeline

```
┌────────────────────┐
│ hltv_sync_service  │
│ (daemon loop)      │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ docker_manager     │
│ (FlareSolverr up?) │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐     ┌──────────────┐
│ stat_fetcher       │────▶│ rate_limit   │
│ (BeautifulSoup)    │     │ (tiered)     │
└────────┬───────────┘     └──────────────┘
         │
    ┌────┼────┐
    │    │    │
    ▼    ▼    ▼
  main clutch career   (4 pages per player)
  page  page  page
    │    │    │
    └────┼────┘
         │
         ▼
┌────────────────────┐     ┌──────────────┐
│ hltv_api_service   │────▶│ cache/proxy  │
│ (circuit breaker)  │     │ (SQLite TTL) │
└────────┬───────────┘     └──────────────┘
         │
    ┌────┼────┐
    │         │
    ▼         ▼
 Playwright  FlareSolverr
 (direct)    (Cloudflare
              bypass)
    │         │
    └────┬────┘
         │
         ▼
┌────────────────────┐
│ hltv_metadata.db   │
│ (ProPlayer,        │
│  ProPlayerStatCard)│
└────────────────────┘
```

### External API Integration

```
┌────────────────┐     ┌─────────────────┐
│ Steam Web API  │     │ FaceIT API v4   │
│ (profile sync) │     │ (match history) │
└───────┬────────┘     └────────┬────────┘
        │                      │
   ┌────▼─────┐          ┌─────▼────────┐
   │steam_api │          │faceit_integr.│
   │(retry 3x)│          │(rate limit   │
   │          │          │ 10 req/min)  │
   └────┬─────┘          └─────┬────────┘
        │                      │
        ▼                      ▼
┌────────────────────────────────────────┐
│ database.db                            │
│ (UserProfile, FaceitMatchHistory)      │
└────────────────────────────────────────┘
```

---

*End of Report 3/8*
