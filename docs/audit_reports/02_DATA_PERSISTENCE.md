# Data Persistence, Schema Integrity, and Migration Governance
# Macena CS2 Analyzer — Technical Audit Report 2/8

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| Report ID | AUDIT-2026-02 |
| Date | 2026-03-08 |
| Version | 1.0 |
| Classification | Internal — Engineering Review |
| Auditor | Engineering Audit Protocol v3 |
| Scope | 80 files across database models, ORM, migrations, backup, state management, storage managers, and data corpus |
| Total LOC Audited | ~5,800 (Python) + ~2,400 (migrations) + ~1,200 (config/data) |
| Audit Standard | ISO/IEC 25010, ISO/IEC 27001, OWASP Top 10, IEEE 730, CLAUDE.md Rules 1-4 |
| Previous Audit | N/A (baseline audit) |

---

## TABLE OF CONTENTS

- [1. Executive Summary](#1-executive-summary)
- [2. Audit Methodology](#2-audit-methodology)
- [3. ORM and Data Models](#3-orm-and-data-models)
- [4. Database Engine Management](#4-database-engine-management)
- [5. Migration Infrastructure](#5-migration-infrastructure)
- [6. Backup and Recovery](#6-backup-and-recovery)
- [7. State Management](#7-state-management)
- [8. Storage and File Management](#8-storage-and-file-management)
- [9. Remote Access Layer](#9-remote-access-layer)
- [10. Data Corpus Assessment](#10-data-corpus-assessment)
- [11. Consolidated Findings Matrix](#11-consolidated-findings-matrix)
- [12. Recommendations](#12-recommendations)
- [Appendix A: Complete File Inventory](#appendix-a-complete-file-inventory)
- [Appendix B: Glossary](#appendix-b-glossary)
- [Appendix C: Cross-Reference Index](#appendix-c-cross-reference-index)
- [Appendix D: Schema Entity-Relationship Diagram](#appendix-d-schema-entity-relationship-diagram)
- [Appendix E: Migration Chain Diagram](#appendix-e-migration-chain-diagram)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Domain Health Assessment

**Overall Rating: SOUND**

The data persistence layer is the structural backbone of the Macena CS2 Analyzer, managing three database tiers (monolith, HLTV metadata, per-match ephemeral), 18 ORM models, 15 Alembic migrations across 3 independent chains, and a comprehensive backup/recovery system. The architecture demonstrates mature engineering with WAL-mode concurrency, atomic backup API usage, double-checked locking for singleton factories, and defense-in-depth security patterns.

The most significant architectural concern is the **dual Alembic migration system** — two independent chains (`alembic/` and `backend/storage/migrations/`) can write to the same database without coordination. This creates forward-only schema lock risks and potential conflicts. Additionally, one backend migration has an empty downgrade (forward-only), and another has a destructive downgrade that loses data.

The match data manager implements a true LRU cache (OrderedDict with eviction) for per-match engine instances, and the backup system uses SQLite's Online Backup API for atomic, WAL-safe backups with post-backup integrity verification.

### 1.2 Critical Findings Summary

| ID | Severity | File | Finding |
|----|----------|------|---------|
| R2-01 | HIGH | Migration infrastructure | Dual Alembic systems with no coordination mechanism — risk of schema conflict |
| ~~R2-02~~ | ~~HIGH~~ | ~~`5d5764ef9f26`~~ | ~~RESOLVED — downgrade now implements proper column drops~~ |
| ~~R2-03~~ | ~~HIGH~~ | ~~`match_data_manager.py`~~ | ~~RESOLVED — `create_all()` now uses explicit `tables=_MATCH_TABLES` + defensive assertion~~ |
| R2-04 | MEDIUM | `db_models.py` | `Ext_PlayerPlaystyle` conflates game statistics with user profile fields — schema debt |
| R2-05 | MEDIUM | `db_models.py` | `IngestionTask.updated_at` has no ORM-level auto-refresh — stale timestamp trap |
| R2-06 | MEDIUM | `b609a11e13cc` | Downgrade is destructive — drops `ingestiontask_archive` and recreates with NULL values |
| R2-07 | MEDIUM | `db_models.py` | No FK cascade semantics defined — orphan records possible on parent deletion |

### 1.3 Quantitative Overview

| Metric | Value |
|--------|-------|
| Files Audited | 80 |
| Total Lines of Code | ~9,400 |
| ORM Models | 18 tables across 3 database tiers |
| Alembic Migrations | 15 (13 main + 2 backend) |
| Database Tiers | 3 (monolith, HLTV, per-match) |
| Findings: CRITICAL | 0 |
| Findings: HIGH | 1 (was 3; R2-02, R2-03 resolved) |
| Findings: MEDIUM | 8 |
| Findings: LOW | 6 |
| Findings: INFO | 8 |
| Remediation Items Previously Fixed | 12 (P0-04, P0-05, P0-06, P2-02, P2-03, P2-04, P2-06, P2-08, P7-04, M-18, M-27) |

### 1.4 Risk Heatmap

```
                    IMPACT
              Low    Medium    High    Critical
         ┌─────────┬─────────┬─────────┬─────────┐
  High   │         │  R2-05  │  R2-01  │         │
L        │         │         │  R2-03  │         │
I  Med   │  R2-10  │  R2-04  │  R2-02  │         │
K        │         │  R2-06  │         │         │
E  Low   │  R2-12  │  R2-07  │         │         │
L        │  R2-14  │         │         │         │
I  VLow  │ INFO x8 │  R2-08  │         │         │
         └─────────┴─────────┴─────────┴─────────┘
```

---

## 2. AUDIT METHODOLOGY

### 2.1 Standards Applied

- **ISO/IEC 25010** — Data integrity, reliability, maintainability, performance efficiency
- **ISO/IEC 27001** — Data classification, access control, backup integrity
- **OWASP Top 10** — SQL injection, broken access control, security misconfiguration
- **IEEE 730** — Configuration management, verification, validation
- **CLAUDE.md Rules 1-4** — Correctness, backend sovereignty, data/persistence governance
- **STRIDE** — Tampering, Information Disclosure, Denial of Service on data layer

### 2.2 Analysis Techniques

- **Schema Analysis**: Column-by-column model inspection, constraint verification, index coverage
- **Migration Chain Analysis**: Linear dependency verification, reversibility assessment, conflict detection
- **Concurrency Analysis**: WAL mode verification, connection pooling assessment, lock contention patterns
- **Data Flow Analysis**: Write path tracing (ingestion → storage → query), backup integrity chain
- **Security Analysis**: SQL injection vectors, path traversal, credential handling, PII exposure

### 2.3 Severity Classification

| Severity | Definition | SLA |
|----------|------------|-----|
| CRITICAL | Data loss, corruption, or security breach in persistence layer | Immediate fix |
| HIGH | Schema integrity risk, migration irreversibility, or significant data quality impact | Current sprint |
| MEDIUM | Moderate reliability or maintainability concern in data layer | Next 2 sprints |
| LOW | Minor schema debt, documentation gaps, or optimization opportunities | Next refactoring |
| INFO | Positive observations, architectural notes | No SLA |

---

## 3. ORM AND DATA MODELS

### 3.1 `backend/storage/db_models.py` — Complete ORM definition

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 604 |
| Classes | 18 SQLModel classes |
| Fields Total | ~280 across all models |
| Check Constraints | 5 |
| Indices | 28 |
| Foreign Keys | 6 |
| Validators | 1 (`@field_validator` on game_state_json) |

**Three-Tier Architecture:**

| Tier | Tables | Database | Purpose |
|------|--------|----------|---------|
| **Monolith** | PlayerMatchStats, PlayerTickState, PlayerProfile, CoachingInsight, IngestionTask, TacticalKnowledge, CoachState, ServiceNotification, CoachingExperience, RoundStats, CalibrationSnapshot, RoleThresholdRecord | `database.db` | Core application state |
| **HLTV** | ProTeam, ProPlayer, ProPlayerStatCard, MatchResult, MapVeto | `hltv_metadata.db` | Pro reference data (isolated for concurrency) |
| **Per-Match** | MatchTickState, MatchEventState, MatchMetadata | `match_data/<demo_name>.db` | High-fidelity tick data (ephemeral, pruneable) |

**Key Model Analysis:**

**PlayerMatchStats** (71 fields):
- Primary aggregate for match performance — kills, deaths, ADR, KAST, rating components
- Unique constraint: `(demo_name, player_name)` — prevents duplicate player stats per match
- 4 CheckConstraints: non-negative kills/ADR, rating in [0, 5.0]
- Trade kill metrics added in Fusion Plan migration (R2 P8.3)

**CoachState** (singleton):
- Check constraint enforces `id=1` only — guarantees exactly one row
- Tracks all daemon statuses, training progress, heartbeat, system load
- Critical for Tri-Daemon coordination (see Report 1)

**CoachingExperience** (COPER framework):
- `game_state_json` validated at ORM level: `MAX_GAME_STATE_JSON_BYTES = 16384` (16 KB)
- `context_hash` for O(1) retrieval of relevant experiences
- Outcome tracking + effectiveness scoring for feedback loop

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-04 | MEDIUM | Schema | `Ext_PlayerPlaystyle` conflates 32 fields mixing game stats (role probabilities, metrics) with user account data (steam_id, social_links_json, specs_json). | Split into `PlaystyleStats` + `UserProfile` tables. |
| R2-05 | MEDIUM | Correctness | `IngestionTask.updated_at` has no ORM-level auto-refresh. Callers must manually set `task.updated_at = datetime.now(timezone.utc)`. Forgetting this leads to stale timestamps. | Add SQLAlchemy `onupdate` clause or document as project invariant in CLAUDE.md. |
| R2-07 | MEDIUM | Data Integrity | No FK cascade semantics defined. `ProPlayerStatCard → ProPlayer`, `CoachingExperience → MatchResult` have no DELETE CASCADE. Orphan records possible. | Add `ON DELETE CASCADE` or `ON DELETE SET NULL` to FK definitions. |
| R2-08 | MEDIUM | Data Quality | `PlayerTickState.demo_name` defaults to `"unknown"` — enables silent data quality degradation if parser fails to set it. | Add a NOT NULL constraint without default; force parser to always provide demo_name. |
| R2-15 | INFO | Architecture | CoachState singleton pattern via CHECK constraint (`id=1`) is elegant and database-enforced. | None — exemplary design. |
| R2-16 | INFO | Security | `game_state_json` size validation via `@field_validator` prevents unbounded DB growth (P2-02 fix). However, direct SQL inserts bypass this check. | Consider adding a SQLite CHECK constraint on JSON length for defense-in-depth. |

**Positive Observations:**
- 18 models covering all application domains with clear separation between tiers.
- Composite indices on `(demo_name, player_name)` and `(demo_name, round_number)` optimize the most common query patterns.
- `DatasetSplit` and `CoachStatus` enums enforce valid discrete values at ORM level.
- CheckConstraints on `PlayerMatchStats` prevent nonsensical values (negative kills, rating > 5.0).

---

## 4. DATABASE ENGINE MANAGEMENT

### 4.1 `backend/storage/database.py` — Engine and session management

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 289 |
| Classes | 2 (DatabaseManager, HLTVDatabaseManager) |
| Functions/Methods | 14 |
| Singletons | 2 (`get_db_manager()`, `get_hltv_db_manager()`) |

**Architecture:**

Two manager classes for the two primary database tiers:

**DatabaseManager** (monolith):
- WAL mode enforced via event listener on every connection
- `pool_size=1, max_overflow=4` — prevents SQLite write-lock contention
- `timeout=30s` — bounded wait for lock acquisition
- `session.merge()` for atomic upsert operations
- Special `_upsert_player_stats()` handles unique constraint conflicts

**HLTVDatabaseManager** (isolated HLTV metadata):
- Separate engine from monolith — concurrent Tri-Daemon access without contention
- Schema reconciliation: `_reconcile_stale_schema()` drops orphan tables and recreates stale ones
- Table name validation via regex before SQL interpolation (P7-04 fix)

**Concurrency Analysis:**
- Double-checked locking with `threading.Lock()` for both singleton factories — correct pattern
- WAL mode + `synchronous=NORMAL` + `timeout=30` provides safe concurrent access
- `pool_size=1` limits concurrent writes but `max_overflow=4` allows burst reads

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-09 | LOW | Performance | `pool_size=1` may create bottleneck under Tri-Daemon concurrent write load. With `max_overflow=4`, up to 5 connections can exist but only 1 is persistent. | Profile under production load. WAL mode should handle this well for SQLite, but monitor for lock timeouts. |
| R2-17 | INFO | Security | Table name validation regex prevents SQL injection in `_reconcile_stale_schema()` (P7-04). | None — correctly fixed. |
| R2-18 | INFO | Architecture | Monolith/HLTV separation via independent managers is correct for Tri-Daemon concurrency isolation. | None — good architecture. |

**Positive Observations:**
- WAL mode enforcement via event listener ensures every connection operates in WAL — no configuration drift.
- Double-checked locking is correct and efficient for singleton creation.
- Session context managers (`get_session()`) ensure proper cleanup.

---

### 4.2 `backend/storage/match_data_manager.py` — Per-match database lifecycle

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 742 |
| Classes | 4 (MatchTickState, MatchEventState, MatchMetadata, MatchDataManager) |
| Functions/Methods | 28 |

**Architecture:**
Manages individual SQLite databases for each match (Tier 3). Key innovations:

- **True LRU Cache**: `OrderedDict` with `move_to_end()` / `popitem(last=False)` for engine lifecycle management (M-18 fix). Max 8 concurrent engines.
- **WAL Per-Match**: Each match database independently configured for WAL mode.
- **No-Wallhack Design**: `MatchEventState` excludes steamid to prevent cross-player information leakage.
- **Entity ID Sentinel**: `-1` sentinel prevents false pairing of smoke/molotov events when parser fails to populate entity_id.

**Correctness Analysis:**
- Schema filtering: `SQLModel.metadata.create_all(engine, tables=[...])` MUST receive explicit table list. Omitting `tables=` parameter causes monolith tables to leak into per-match databases — this is **fragile**.
- Auto-migration from old in-project location runs once on first startup.
- Bulk insert methods (`store_tick_batch()`, `store_event_batch()`) use `session.bulk_save_objects()` for performance.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| ~~R2-03~~ | ~~HIGH~~ | ~~Correctness~~ | ~~RESOLVED: `create_all()` now uses explicit `tables=_MATCH_TABLES` parameter (line 270) with defensive assertion verifying table count (lines 271-273).~~ | ~~Done~~ |
| R2-19 | INFO | Architecture | True LRU with OrderedDict (M-18 fix) is correct. Previous FIFO implementation could evict recently-used engines. | None — properly fixed. |
| R2-20 | INFO | Performance | Bulk insert via `bulk_save_objects()` provides ~8x speedup over individual inserts (documented in commit history: 762s → 97s). | None — excellent optimization. |

**Positive Observations:**
- LRU engine cache prevents memory exhaustion from too many open database connections.
- Entity ID sentinel (`-1`) is a practical solution to parser gaps.
- Per-match WAL mode enables concurrent analysis reads during ingestion writes.

---

## 5. MIGRATION INFRASTRUCTURE

### 5.1 Three-System Architecture

The project maintains **three independent Alembic configurations**:

| System | Location | Target DB | Active Migrations | Head |
|--------|----------|-----------|-------------------|------|
| **Main** | `alembic/` | `database.db` | 13 versions | `3c6ecb5fe20e` |
| **Backend** | `backend/storage/migrations/` | `database.db` | 2 versions | `5d5764ef9f26` |
| **Programma** | `Programma_CS2_RENAN/migrations/` | `database.db` | 0 versions (ORM-only) | — |

**Critical Issue**: Both Main and Backend systems target the **same database** (`database.db`) with no coordination mechanism.

### 5.2 Main Migration Chain Analysis

13 migrations in linear chain (no branching):

```
f769fbe67229 (Foundation) → 7a30a0ea024e (Calibration) → cab9c431dfc6 (Align)
  → 89850b6e0a49 (Pro Stats) → 8a93567a2798 (Pro Link) → c8a2308770e5 (Retraining)
  → 8c443d3d9523 (Triple Daemon) → 609fed4b4dce (Tick Track) → e3013f662fd4 (Sync)
  → 57a72f0df21e (Heartbeat) → da7a6be5c0c7 (Notifications) → 19fcff36ea0a (Telemetry)
  → 3c6ecb5fe20e (Fusion Plan) [HEAD]
```

**Total Schema Mutations**: 43 operations across 13 migrations.

**Reversibility Assessment**: All 13 main migrations have complete downgrade implementations. All use conservative ADD COLUMN operations with server defaults.

**Notable Migrations:**
- `89850b6e0a49`: Creates the Pro Stats system (ProTeam, ProPlayer, ProPlayerStatCard) — foundation for HLTV integration
- `8c443d3d9523`: Adds triple-daemon status tracking — essential for Tri-Daemon observability
- `3c6ecb5fe20e` (HEAD): Fusion Plan — adds trade kill metrics and coaching experience feedback loop (11 + 6 new columns)

### 5.3 Backend Migration Chain Analysis

2 migrations in independent chain:

```
b609a11e13cc (Baseline) → 5d5764ef9f26 (Rating Components) [HEAD]
```

**Reversibility Issues:**
- `b609a11e13cc`: Downgrade **destructive** — drops `ingestiontask_archive` and recreates with NULL values (original data lost)
- `5d5764ef9f26`: Downgrade is **empty** (`pass`) — columns added cannot be removed via Alembic

### 5.4 `alembic/env.py` — Migration executor

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 120 |

**Key Features:**
- Pre-migration backup via `backup_monolith()` — non-fatal if backup fails
- Uses `NullPool` — correct for SQLite (avoids connection pool confusion)
- Imports 6 core models for autogenerate support
- Both offline and online migration modes supported

### 5.5 `schema.py` — Unified CLI controller

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 271 |

**Commands:** `inspect`, `migrate`, `import`, `fix`, `reset`

Contains hardcoded "common column migrations" that apply columns via `ALTER TABLE ADD COLUMN` — a safety net for schema drift between Alembic and runtime `create_all()`.

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-01 | HIGH | Architecture | Two Alembic systems (main + backend) target the same database with no coordination mechanism. If both run, schema could diverge. `schema.py` selects which to apply but is error-prone. | Consolidate into single Alembic chain. Merge backend migrations into main chain as dependent versions. |
| ~~R2-02~~ | ~~HIGH~~ | ~~Migration~~ | ~~RESOLVED: Downgrade now properly drops all columns added in upgrade (lines 102-115, tagged with R2-02 comment).~~ | ~~Done~~ |
| R2-06 | MEDIUM | Migration | `b609a11e13cc` downgrade drops `ingestiontask_archive` and recreates with NULL values. Original archive data is irreversibly lost. | Implement data-preserving downgrade or document as forward-only with explicit warning. |
| R2-10 | LOW | Migration | `cab9c431dfc6_align_schema.py` is an empty no-op migration (both upgrade and downgrade are `pass`). | Remove if no longer needed as a synchronization checkpoint. |
| R2-11 | LOW | Maintainability | `schema.py` contains hardcoded column migrations (lines 96-100) that duplicate Alembic logic. Two parallel paths for schema modification. | Phase out hardcoded migrations as Alembic coverage becomes complete. |
| R2-21 | INFO | Architecture | Pre-migration backup in `alembic/env.py` is defense-in-depth — even if backup fails, migration proceeds (non-fatal). | None — pragmatic design. |

**Positive Observations:**
- Linear main chain with no branching — clean dependency graph.
- All main migrations use conservative ADD COLUMN with server defaults — safe for production.
- Migration template includes both upgrade and downgrade stubs — encourages reversible migrations.

---

## 6. BACKUP AND RECOVERY

### 6.1 `backend/storage/db_backup.py` — WAL-safe backup utilities

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 221 |
| Functions | 4 |

**Architecture:**
- `backup_monolith()`: Uses `sqlite3.backup()` (Online Backup API) — atomic, handles concurrent writes
- Post-backup `PRAGMA integrity_check` verification
- `backup_match_data()`: Archives match_data directory as tar.gz, excluding WAL/SHM transient files
- `rotate_backups()`: Retention-based cleanup (default 5 backups)
- `restore_backup()`: Pre-restore integrity check + rollback file preservation

**Previously Fixed Issues:**
- P0-05: TOCTOU race between WAL checkpoint and file copy → now uses atomic backup API
- P0-06: Connection leak on checkpoint → now uses try/finally blocks
- P2-08: Post-backup integrity verification added

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-22 | INFO | Architecture | `sqlite3.backup()` is the gold standard for SQLite backup — atomic, WAL-safe, handles concurrent access. | None — exemplary implementation. |

### 6.2 `backend/storage/backup_manager.py` — Hot backup with rotation

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 220 |
| Classes | 1 (BackupManager) |

**Architecture:**
- Uses `VACUUM INTO` for non-blocking hot backup (SQLite 3.27+)
- Retention: 7 daily + 4 weekly backups
- Label-based organization (auto, manual, pre_migration)
- Pre-backup integrity verification
- Path traversal prevention via regex validation + path resolution

**Security:**
- Label sanitization: `re.match(r"^[a-zA-Z0-9_\-]+$", label)` blocks injection
- SQL quote escaping: `target_path.replace("'", "''")`  before interpolation into `VACUUM INTO`

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-12 | LOW | Security | `VACUUM INTO` path is built via string interpolation with quote escaping. While escaping is correct, parameterized queries would be more robust. | Consider using parameterized approach if SQLite supports it for `VACUUM INTO`. |
| R2-23 | INFO | Architecture | Dual-backup strategy (Online Backup API + VACUUM INTO) provides redundancy. Either can serve as primary. | None — defense-in-depth. |

**Positive Observations:**
- Non-blocking hot backup allows backups during active usage.
- Rotation policy prevents unbounded disk growth.
- Integrity pre-verification prevents corrupted backups from being accepted.

---

## 7. STATE MANAGEMENT

### 7.1 `backend/storage/state_manager.py` — Application state DAO

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 207 |
| Classes | 1 (StateManager) |
| Functions/Methods | 11 |

**Architecture:**
- Centralized DAO for CoachState singleton (CHECK constraint `id=1`)
- Thread-safe: lock on all state mutations (P0-04 fix)
- Status tracking for all four daemons (hunter, digester, teacher, global)
- Notification pruning: auto-deletes old notifications (P2-06 fix)
- Telemetry non-critical: training doesn't crash if telemetry update fails

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-13 | LOW | Correctness | Daemon status names ("hunter", "digester", "teacher", "global") are hardcoded strings, not enum-validated. Typos would create orphan status records. | Consider an enum for daemon names. |
| R2-24 | INFO | Architecture | P0-04 fix correctly prevents duplicate CoachState rows via lock-before-query pattern. | None — properly fixed. |

---

### 7.2 `backend/storage/storage_manager.py` — Filesystem storage management

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 259 |
| Classes | 1 (StorageManager) |

**Architecture:**
- Demo file lifecycle: discovery → validation → ingestion → archival
- Path traversal prevention: `Path(filename).name` strips directory components (P2-03 fix)
- Deduplication: checks both full paths AND stems to prevent re-ingestion
- Drive unavailability handling: gracefully logs warning, doesn't crash
- Pro demo archival exclusion: user-managed pro demos not archived (M-27)

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-25 | INFO | Security | Path traversal prevention via `Path.name` is correct and effective. | None — properly implemented. |

---

### 7.3 `backend/storage/maintenance.py` — Data pruning

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 54 |
| Functions | 1 |

**Architecture:**
- Prunes high-fidelity tick data for old demos (default threshold: 30 days)
- Preserves aggregate stats in PlayerMatchStats
- Batches deletes in 500-row chunks to avoid SQLite bind parameter overflow (max 999)

**Positive Observations:**
- Batch chunking prevents SQL parameter overflow — correct for SQLite's 999-parameter limit.
- Preserving aggregates while pruning tick data is the correct data lifecycle approach.

---

### 7.4 `backend/storage/stat_aggregator.py` — Pro data persistence

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 100 |
| Classes | 1 (StatCardAggregator) |

**Architecture:**
- Upsert pattern: query for existing → create if missing
- JSON blob storage for raw spider data (Bridge use)
- Per-session isolation ensures atomic operations

---

## 8. STORAGE AND FILE MANAGEMENT

### 8.1 `db_migrate.py` — Startup migration wrapper

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 113 |
| Functions | 3 |

**Architecture:**
- Checks current vs head revision
- Auto-upgrades if needed
- Graceful degradation: returns True if Alembic not installed (frozen builds)
- No downgrade support — upgrade-only at startup

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-14 | LOW | Maintainability | Startup migration is upgrade-only. No mechanism for controlled downgrade from application code. | Acceptable for production. Add CLI option for manual downgrade if needed. |

---

## 9. REMOTE ACCESS LAYER

### 9.1 `backend/storage/remote_file_server.py` — FastAPI demo file server

**File Metrics:**
| Metric | Value |
|--------|-------|
| Lines of Code | 214 |
| Classes | 2 (_RateLimiter, RateLimitMiddleware) |

**Architecture:**
- FastAPI server for remote demo file access
- Authentication: API key header with `hmac.compare_digest()` (timing-safe)
- Rate limiting: sliding-window per-IP (10 req/min)
- Path traversal prevention: `Path.is_relative_to()` (P2-04 fix)
- TLS support with non-localhost warning

**Security Analysis:**
- Timing-safe comparison prevents timing attacks on API key
- Per-IP rate limiting defends against brute-force key guessing
- `is_relative_to()` prevents directory traversal via prefix manipulation
- TLS warning for non-localhost deployment — correct security posture

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-26 | INFO | Security | Comprehensive defense-in-depth: timing-safe auth, rate limiting, path traversal prevention, TLS warnings. | None — exemplary security implementation. |

---

## 10. DATA CORPUS ASSESSMENT

### 10.1 Knowledge Base Files

The project maintains a comprehensive knowledge corpus across multiple formats:

**Coaching Knowledge** (`data/knowledge/`):
- 7 map-specific coaching files (ancient, anubis, dust2, inferno, mirage, nuke, overpass) in plain text format
- Each file has an OCR variant (generated from screenshot extraction)
- Structured coaching advice: positions, utility lineups, timings, economy management
- `coaching_knowledge_base.json` + OCR variant — indexed knowledge for RAG retrieval
- `extraction_summary.json` — metadata about knowledge extraction process

**Tactical Knowledge** (`backend/knowledge/tactical_knowledge.json`):
- Structured tactical data: map-specific strategies, callouts, angles
- Consumed by RAG pipeline for coaching context

**Map Configuration** (`data/map_config.json`, `data/map_tensors.json`):
- Map coordinate metadata matching `spatial_data.py` definitions
- Tensor dimensions for spatial neural network inputs

**Pro Baseline** (`data/pro_baseline.csv`):
- Professional player statistics for comparative analysis
- Consumed by `baselines/pro_baseline.py`

**Dataset** (`data/dataset.csv`):
- Training/evaluation data for ML models

**Tactics** (`tactics/mirage_defaults.json`):
- Default tactical configurations for map analysis

### 10.2 Storage Artifacts

- `database.db.PRE_FIX` — Pre-remediation database backup (historical reference)
- `hltv_metadata.db.bak` — HLTV database backup
- `remote_telemetry/match_display_123_User_Test_001.json` — Example telemetry output
- `ingestion/.validated_cache.json` — Validation result cache for demo files

**Findings:**

| ID | Severity | Category | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R2-27 | INFO | Data Quality | Knowledge base files provide comprehensive coaching coverage for 7 competitive maps with both original and OCR-extracted variants. | None — thorough coverage. |

---

## 11. CONSOLIDATED FINDINGS MATRIX

### Findings by Severity

#### HIGH Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R2-01 | Migration infra | Architecture | Dual Alembic systems target same DB without coordination | Schema conflict, migration failures | Consolidate into single chain | — |
| ~~R2-02~~ | | | ~~RESOLVED — downgrade now implements proper column drops~~ | | | — |
| ~~R2-03~~ | | | ~~RESOLVED — `create_all()` uses `tables=_MATCH_TABLES` + defensive assertion~~ | | | — |

#### MEDIUM Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R2-04 | `db_models.py` | Schema | `Ext_PlayerPlaystyle` conflates game stats + user profile | Schema debt, hard to evolve independently | Split into two tables | — |
| R2-05 | `db_models.py` | Correctness | `IngestionTask.updated_at` no auto-refresh | Stale timestamps if callers forget | Add `onupdate` clause | — |
| R2-06 | `b609a11e13cc` | Migration | Destructive downgrade — data loss on rollback | Cannot safely downgrade | Implement data-preserving downgrade | — |
| R2-07 | `db_models.py` | Data Integrity | No FK cascade semantics | Orphan records on parent deletion | Add CASCADE/SET NULL | — |
| R2-08 | `db_models.py` | Data Quality | `demo_name` defaults to "unknown" | Silent data quality degradation | Make NOT NULL without default | — |
| R2-09 | `database.py` | Performance | `pool_size=1` may bottleneck | Lock contention under heavy load | Profile under load | — |
| R2-10 | `cab9c431dfc6` | Maintainability | Empty no-op migration | Clutters migration chain | Remove if unnecessary | — |
| R2-11 | `schema.py` | Maintainability | Hardcoded column migrations duplicate Alembic | Two parallel schema paths | Phase out hardcoded migrations | — |

#### LOW Findings

| ID | File | Category | Finding | Impact | Recommendation | Cross-Ref |
|----|------|----------|---------|--------|----------------|-----------|
| R2-09 | `database.py` | Performance | pool_size=1 bottleneck risk | Monitor for lock timeouts | Profile under production load | — |
| R2-12 | `backup_manager.py` | Security | VACUUM INTO path via string interpolation | Minor injection vector | Use parameterized if possible | — |
| R2-13 | `state_manager.py` | Correctness | Daemon names as hardcoded strings | Typo risk | Use enum | — |
| R2-14 | `db_migrate.py` | Maintainability | No downgrade from application code | Limited rollback | Add CLI option | — |

#### INFO Findings

| ID | File | Category | Finding | Cross-Ref |
|----|------|----------|---------|-----------|
| R2-15 | `db_models.py` | Architecture | CoachState singleton via CHECK constraint — exemplary | — |
| R2-16 | `db_models.py` | Security | game_state_json size validation — good but ORM-only | P2-02 |
| R2-17 | `database.py` | Security | Table name regex validation — properly fixed | P7-04 |
| R2-18 | `database.py` | Architecture | Monolith/HLTV separation — correct for concurrency | — |
| R2-19 | `match_data_manager.py` | Architecture | True LRU with OrderedDict — properly fixed | M-18 |
| R2-20 | `match_data_manager.py` | Performance | Bulk insert 8x speedup via bulk_save_objects | — |
| R2-21 | `alembic/env.py` | Architecture | Pre-migration backup — defense-in-depth | — |
| R2-22 | `db_backup.py` | Architecture | sqlite3.backup() — gold standard for SQLite | P0-05 |
| R2-23 | `backup_manager.py` | Architecture | Dual-backup strategy (Online + VACUUM INTO) | — |
| R2-24 | `state_manager.py` | Architecture | P0-04 duplicate row prevention — properly fixed | P0-04 |
| R2-25 | `storage_manager.py` | Security | Path traversal prevention — properly implemented | P2-03 |
| R2-26 | `remote_file_server.py` | Security | Defense-in-depth auth + rate limiting | P2-04 |
| R2-27 | Knowledge files | Data Quality | Comprehensive coaching coverage — 7 maps | — |

### Findings by Category

| Category | CRIT | HIGH | MED | LOW | INFO | Total |
|----------|------|------|-----|-----|------|-------|
| Correctness | 0 | 1 | 2 | 1 | 0 | 4 |
| Security | 0 | 0 | 0 | 1 | 4 | 5 |
| Performance | 0 | 0 | 1 | 0 | 1 | 2 |
| Architecture | 0 | 1 | 0 | 0 | 7 | 8 |
| Data Integrity | 0 | 0 | 1 | 0 | 0 | 1 |
| Data Quality | 0 | 0 | 1 | 0 | 1 | 2 |
| Migration | 0 | 1 | 2 | 0 | 1 | 4 |
| Schema | 0 | 0 | 1 | 0 | 1 | 2 |
| Maintainability | 0 | 0 | 2 | 1 | 0 | 3 |
| **Total** | **0** | **3** | **10** | **3** | **15** | **31** |

### Findings Trend (vs Prior Audits)

| Category | Fixed in Phases 1-12 | New in This Audit | Status |
|----------|---------------------|-------------------|--------|
| P0-04 (CoachState duplication) | Fixed (Phase 1) | — | Resolved |
| P0-05 (TOCTOU backup race) | Fixed (Phase 1) | — | Resolved |
| P0-06 (Connection leak) | Fixed (Phase 1) | — | Resolved |
| P2-02 (Unbounded JSON) | Fixed (Phase 2) | — | Resolved |
| P2-03 (Path traversal) | Fixed (Phase 2) | — | Resolved |
| P2-04 (Remote path traversal) | Fixed (Phase 2) | — | Resolved |
| P2-06 (Notification pruning) | Fixed (Phase 2) | — | Resolved |
| P2-08 (Post-backup integrity) | Fixed (Phase 2) | — | Resolved |
| P7-04 (SQL injection) | Fixed (Phase 7) | — | Resolved |
| M-18 (FIFO→LRU cache) | Fixed (Phase 12) | — | Resolved |
| M-27 (Pro archival exclusion) | Fixed (Phase 12) | — | Resolved |
| Dual Alembic systems | — | R2-01 (HIGH) | New |
| Forward-only migration | — | R2-02 (HIGH) | New |
| Schema filtering fragility | — | R2-03 (HIGH) | New |

---

## 12. RECOMMENDATIONS

### Immediate Actions (HIGH)

1. **[R2-01] Consolidate Alembic chains**: Merge the 2 backend migrations into the main `alembic/` chain as dependent versions. Remove `backend/storage/migrations/` as an independent system. Estimated complexity: Medium (4 hours).

2. **[R2-02] Implement downgrade for `5d5764ef9f26`**: Add `op.drop_column()` calls for all 7 `playermatchstats` columns and 6 `proplayerstatcard` columns. Estimated complexity: Low (1 hour).

3. **[R2-03] Fix schema filtering fragility**: Either (a) use a separate `DeclarativeBase` for per-match models, or (b) add an assertion in `MatchDataManager._create_tables()` that verifies only 3 tables exist post-creation. Estimated complexity: Medium (3 hours).

### Short-Term Actions (MEDIUM)

4. **[R2-04] Split `Ext_PlayerPlaystyle`**: Separate game statistics from user profile fields into two tables with FK relationship. Requires migration. Estimated complexity: High (8 hours).

5. **[R2-05] Fix `updated_at` auto-refresh**: Add `onupdate=lambda: datetime.now(timezone.utc)` to the column definition, or create a `before_flush` event listener. Estimated complexity: Low (30 minutes).

6. **[R2-07] Add FK cascade semantics**: Define `ON DELETE CASCADE` or `ON DELETE SET NULL` for all FK relationships. Requires migration. Estimated complexity: Medium (2 hours + migration).

7. **[R2-08] Strengthen `demo_name` constraint**: Make NOT NULL without default on `PlayerTickState.demo_name`. Estimated complexity: Low (1 hour + migration).

### Long-Term Actions (LOW + Strategic)

8. **[R2-11] Phase out `schema.py` hardcoded migrations**: As Alembic coverage becomes complete, remove the `_apply_column_migration()` safety net. Estimated complexity: Low (ongoing).

9. **[R2-13] Create daemon name enum**: Replace hardcoded string names with a `DaemonName` enum for type safety. Estimated complexity: Low (1 hour).

### Architectural Recommendations

1. **Single Migration Authority**: The three-system Alembic setup is the most significant architectural debt in the persistence layer. Consolidation into a single chain eliminates the coordination problem entirely.

2. **Data Lifecycle Documentation**: Create a `DATA_LIFECYCLE.md` documenting retention policies (tick data: 30 days, aggregates: indefinite, backups: 7 daily + 4 weekly).

3. **Migration Testing**: Add a CI job that runs the full migration chain (from empty DB to HEAD) on every PR to catch migration ordering issues.

---

## APPENDIX A: COMPLETE FILE INVENTORY

| # | File Path | LOC | Type | Findings |
|---|-----------|-----|------|----------|
| 1 | `backend/__init__.py` | 1 | Package | 0 |
| 2 | `backend/storage/__init__.py` | 1 | Package | 0 |
| 3 | `backend/storage/database.py` | 289 | Engine mgmt | 2 (L, I) |
| 4 | `backend/storage/db_models.py` | 604 | ORM models | 5 (M×3, I×2) |
| 5 | `backend/storage/db_backup.py` | 221 | Backup | 1 (I) |
| 6 | `backend/storage/db_migrate.py` | 113 | Migration | 1 (L) |
| 7 | `backend/storage/backup_manager.py` | 220 | Hot backup | 2 (L, I) |
| 8 | `backend/storage/maintenance.py` | 54 | Pruning | 0 |
| 9 | `backend/storage/match_data_manager.py` | 742 | Per-match DB | 3 (H, I×2) |
| 10 | `backend/storage/state_manager.py` | 207 | State DAO | 2 (L, I) |
| 11 | `backend/storage/storage_manager.py` | 259 | File mgmt | 1 (I) |
| 12 | `backend/storage/stat_aggregator.py` | 100 | Pro data | 0 |
| 13 | `backend/storage/remote_file_server.py` | 214 | API server | 1 (I) |
| 14 | `backend/storage/datasets/__init__.py` | 1 | Package | 0 |
| 15 | `backend/storage/models/__init__.py` | 1 | Package | 0 |
| 16 | `alembic.ini` | 148 | Config | 0 |
| 17 | `alembic/env.py` | 120 | Executor | 1 (I) |
| 18 | `alembic/script.py.mako` | 28 | Template | 0 |
| 19-31 | `alembic/versions/*.py` (13 files) | 1,213 | Migrations | 2 (L) |
| 32 | `backend/storage/migrations/env.py` | 89 | Executor | 0 |
| 33 | `backend/storage/migrations/script.py.mako` | 28 | Template | 0 |
| 34-35 | `backend/storage/migrations/versions/*.py` (2) | 376 | Migrations | 2 (H, M) |
| 36 | `Programma_CS2_RENAN/migrations/env.py` | 84 | Executor | 0 |
| 37 | `Programma_CS2_RENAN/migrations/script.py.mako` | 28 | Template | 0 |
| 38 | `schema.py` | 271 | CLI | 2 (H, L) |

*Files 39-80 comprise data corpus files (CSVs, JSONs, knowledge TXTs), storage artifacts, and READMEs reviewed for completeness.*

---

## APPENDIX B: GLOSSARY

| Term | Definition |
|------|-----------|
| **CoachState** | Singleton row (CHECK `id=1`) tracking global application state: daemon statuses, training progress, system metrics |
| **COPER** | Coaching framework: Experience Bank → RAG → Pro Bridge. `CoachingExperience` table stores experiences. |
| **LRU Cache** | Least Recently Used eviction — OrderedDict implementation in `MatchDataManager` (max 8 engines) |
| **Monolith DB** | Primary `database.db` — core application state (PlayerMatchStats, CoachState, etc.) |
| **Per-Match DB** | Individual SQLite database per demo file (`match_data/<demo>.db`) — high-fidelity tick data |
| **Three-Tier Architecture** | Monolith (aggregate stats) → HLTV (pro reference) → Per-Match (tick data) |
| **VACUUM INTO** | SQLite command for non-blocking database copy (requires SQLite 3.27+) |
| **WAL Mode** | Write-Ahead Logging — enables concurrent reads during writes |

---

## APPENDIX C: CROSS-REFERENCE INDEX

| Finding ID | Remediation Code | Pipeline Code | CLAUDE.md Rule |
|------------|-----------------|---------------|----------------|
| R2-01 | — | — | Rule 4 (single authoritative owner) |
| ~~R2-02~~ | — | — | ~~RESOLVED~~ |
| ~~R2-03~~ | — | — | ~~RESOLVED~~ |
| R2-04 | — | — | Rule 4 (data modeling) |
| R2-05 | — | — | Rule 1 (correctness) |
| R2-06 | — | — | Rule 4 (migration reversibility) |
| R2-07 | — | — | Rule 4 (referential integrity) |
| R2-08 | — | — | Rule 4 (validate at ingress) |

---

## APPENDIX D: SCHEMA ENTITY-RELATIONSHIP DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONOLITH DATABASE (database.db)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │ PlayerMatchStats  │────►│    RoundStats     │                 │
│  │ (demo, player)   │     │ (demo, round, pl) │                 │
│  └──────────────────┘     └──────────────────┘                 │
│           │                                                     │
│           │ (FK)           ┌──────────────────┐                 │
│           └───────────────►│  PlayerTickState   │                 │
│                            │ (demo, tick, pl)  │                 │
│                            └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  CoachState (1)   │     │ ServiceNotification│                 │
│  │  (singleton)      │     │ (daemon, severity) │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │ IngestionTask     │     │ CoachingInsight    │                 │
│  │ (demo_path UQ)    │     │ (demo, player)    │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │ CoachingExperience│     │TacticalKnowledge  │                 │
│  │ (context_hash)    │     │ (384-dim embed)   │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │ PlayerProfile     │     │ CalibrationSnap   │                 │
│  │ (player UQ)       │     │ (type, params)    │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │ RoleThreshold     │     │ Ext_PlayerPlaystyle│                 │
│  │ (stat_name UQ)    │     │ (SCHEMA DEBT)     │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐                                           │
│  │Ext_TeamRoundStats │                                           │
│  │ (external CSV)    │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  HLTV DATABASE (hltv_metadata.db)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │    ProTeam        │◄────│    ProPlayer      │                 │
│  │  (hltv_id UQ)     │ FK  │  (hltv_id UQ)     │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                    │                            │
│                                    │ FK                         │
│                                    ▼                            │
│                           ┌──────────────────┐                 │
│                           │ProPlayerStatCard  │                 │
│                           │ (rating, stats)   │                 │
│                           └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │   MatchResult     │◄────│    MapVeto        │                 │
│  │  (match_id PK)    │ FK  │ (pick/ban/left)   │                 │
│  └──────────────────┘     └──────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              PER-MATCH DATABASE (match_data/<demo>.db)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  MatchTickState   │     │  MatchEventState  │                 │
│  │  (46 fields/tick) │     │  (weapons, nades)  │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐                                           │
│  │  MatchMetadata    │                                           │
│  │  (map, teams)     │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## APPENDIX E: MIGRATION CHAIN DIAGRAM

```
MAIN ALEMBIC CHAIN (alembic/)
═════════════════════════════

  f769fbe67229  ← ROOT (2025-12-26)
  │  Foundation: ingestiontask + playerprofile enrichment
  ▼
  7a30a0ea024e  (2026-01-11)
  │  Calibration: calibrationsnapshot + rolethresholdrecord
  ▼
  cab9c431dfc6  (2026-01-11)  ← NO-OP CHECKPOINT
  │
  ▼
  89850b6e0a49  (2026-01-11)
  │  Pro Stats: proteam + proplayer + proplayerstatcard
  ▼
  8a93567a2798  (2026-01-11)
  │  Pro Link: FK playermatchstats → proplayer
  ▼
  c8a2308770e5  (2026-01-11)
  │  Retraining: last_trained_sample_count
  ▼
  8c443d3d9523  (2026-01-11)
  │  Triple Daemon: hltv_status + ingest_status + ml_status
  ▼
  609fed4b4dce  (2026-01-12)
  │  Tick Tracking: last_tick_processed
  ▼
  e3013f662fd4  (2026-01-12)
  │  Sync Intervals: pro_ingest_interval + sync timestamps
  ▼
  57a72f0df21e  (2026-01-12)
  │  Heartbeat: last_heartbeat
  ▼
  da7a6be5c0c7  (2026-01-12)
  │  Notifications: servicenotification table
  ▼
  19fcff36ea0a  (2026-01-13)
  │  Telemetry: service_pid + system_load_cpu/mem
  ▼
  3c6ecb5fe20e  (2026-02-15)  ← HEAD
     Fusion Plan: trade kills + utility + coaching feedback loop


BACKEND CHAIN (backend/storage/migrations/)  ← INDEPENDENT
═════════════════════════════════════════════

  b609a11e13cc  ← ROOT (2026-01-22)
  │  Baseline: matchresult + mapveto + coachstate hardening
  │  ⚠️ Downgrade DESTRUCTIVE
  ▼
  5d5764ef9f26  (2026-01-22)  ← HEAD
     Rating Components: kpr, dpr, impact, survival, kast...
     ⚠️ Downgrade EMPTY (pass)


PROGRAMMA CHAIN (Programma_CS2_RENAN/migrations/)
═════════════════════════════════════════════════

  (empty — ORM-only, no active migrations)
```

---

*End of Report 2/8 — Data Persistence, Schema Integrity, and Migration Governance*
