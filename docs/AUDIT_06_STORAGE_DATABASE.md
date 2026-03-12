# Audit Report 06 — Storage & Database

**Scope:** `backend/storage/`, Alembic — 30 files, ~4,890 lines | **Date:** 2026-03-10
**Open findings:** 1 HIGH (arch debt) | 15 MEDIUM | 8 LOW

---

## HIGH — Acknowledged Debt

| ID | File | Finding |
|---|---|---|
| S-28 | backup_manager.py + db_backup.py | Dual backup systems (VACUUM INTO vs Online Backup API). Both serve distinct triggers (startup vs migration). Tracked as architectural debt. |

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| S-01 | database.py | pool_size=1, max_overflow=4 allows 5 concurrent connections — SQLite single-writer risk |
| S-03 | database.py | Double-commit: callers + context manager auto-commit (confusing contract) |
| S-05 | database.py | `_reconcile_stale_schema()` drops/recreates HLTV tables aggressively — data loss risk |
| S-08 | db_models.py | `Ext_PlayerPlaystyle` conflates playstyle stats with user account metadata |
| S-09 | db_models.py | Rating upper bound 5.0 may be too restrictive for outlier matches |
| S-10 | db_models.py | Dangling FK `fk_pro_player_stats` to proplayer (now in separate HLTV DB) |
| S-11 | db_models.py | Field comments use question marks — uncertain semantics (tapd, oap, podt) |
| S-14 | db_models.py | `CoachState.status` stored as plain string — no constraint on valid values |
| S-15 | storage_manager.py | `list_new_demos()` loads ALL paths into Python sets — O(n) memory |
| S-18 | match_data_manager.py | `delete_match()` engine cleanup not under `_engine_lock` |
| S-19 | match_data_manager.py | `get_match_session()` no `expire_all()` after rollback |
| S-24 | state_manager.py | `get_state()` triggers write transaction even on read |
| S-25 | state_manager.py | `update_status()` swallows exceptions — callers can't detect failure |
| S-29 | backup_manager.py | Label variable shadowing in `create_checkpoint()` |
| S-31 | db_backup.py | `PRAGMA integrity_check` (full) on routine backups — minutes for large DBs |
| S-33 | db_backup.py | `restore_backup()` overwrites original before verifying integrity of copy |
| S-34 | maintenance.py | `prune_old_metadata()` loads all qualifying demo names without LIMIT |
| S-35 | maintenance.py | Partial pruning: earlier chunks committed, later failure leaves inconsistent state |
| S-37 | remote_file_server.py | `ARCHIVE_PATH.mkdir(parents=True)` without parent dir validation |
| S-42 | alembic.ini | Hardcoded relative DB path (env.py overrides at runtime) |
| S-43 | alembic/env.py | Only 7 of 17 monolith models imported — autogenerate misses 10 tables |
| S-45 | migration f769fbe | Dead migration: columns moved to Ext_PlayerPlaystyle |
| S-46 | migration 89850b6 | Creates HLTV tables in monolith (predates HLTV split) |
| S-47 | migration 8a93567 | Creates dangling FK to proplayer (cross-DB) |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| S-02 | database.py | Deprecated `engine_key` parameter still in signature |
| S-04 | database.py | SELECT + INSERT upsert (2 round-trips) instead of ON CONFLICT |
| S-06 | database.py | Unnecessary double-quoting with regex-validated identifiers |
| S-12 | db_models.py | `last_upload_month` monthly quota reset not automated |
| S-16 | storage_manager.py | Path traversal check blocks legitimate subdirectory paths |
| S-21 | match_data_manager.py | GIL-dependent double-checked locking in singleton factory |
| S-23 | match_data_manager.py | Variable `logger` should be `_logger` at line 277 |
| S-40 | db_migrate.py | `ensure_database_current()` creates separate engine vs singleton |

## Cross-Cutting

1. **Session Auto-Commit Contract** — `get_session()` auto-commits; several callers also explicitly commit. Inconsistency suggests contract not well-understood.
2. **Migration Chain vs Architecture** — Chain written for monolith-only; HLTV split means 3 migrations are architecturally incorrect for new installs.
3. **JSON Field Size Governance** — `parameters_json` (CalibrationSnapshot) and `embedding` fields have no size cap.
