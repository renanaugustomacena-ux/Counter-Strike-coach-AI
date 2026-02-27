# Deep Audit Report — Phase 1: Foundation + Storage + Observability

**Total Files Audited: 29 / 29**
**Issues Found: 37**
**CRITICAL: 2 | HIGH: 3 | MEDIUM: 15 | LOW: 17**
**Author: Renan Augusto Macena**
**Date: 2026-02-27**
**Skills Applied: deep-audit, db-review, data-lifecycle-review, state-audit, observability-audit, security-scan, correctness-check**

---

## [1]. match_data_manager.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/backend/storage/match_data_manager.py`
**LOC:** 708 | **Priority:** MODIFIED (+226 MatchEventState)
**Skills:** deep-audit, db-review, data-lifecycle-review

### Logic Summary
Three-Tier Storage Architecture (Tier 3): per-match SQLite databases for telemetry isolation. Three SQLModel tables: `MatchTickState` (per-tick player state ~100 fields), `MatchEventState` (Player-POV events — NEW), `MatchMetadata` (match context). `MatchDataManager` class manages engine caching (LRU, max 50), WAL mode, and session lifecycle. Singleton pattern via `get_match_data_manager()` with one-time auto-migration from old in-project location.

### Findings

* **Line 100, 148** — `default_factory=datetime.utcnow`
  **Classification:** Maintenance Concern
  **Severity:** LOW
  **Evidence:** `datetime.utcnow` is deprecated since Python 3.12 (PEP 587). Should use `datetime.now(timezone.utc)`. Both `MatchTickState.created_at` (L100) and `MatchEventState.created_at` (L148) use this deprecated factory. All existing timestamps remain consistent (same deprecation everywhere), so functional impact is zero today but will emit warnings on Python 3.12+.

* **Line 146** — `entity_id: int = Field(default=0)`
  **Classification:** Silent Failure Risk
  **Severity:** HIGH
  **Evidence:** `get_active_utilities()` (L389-428) matches smoke/molotov start/end events by `entity_id`. Default value is `0`. If event extraction fails to populate `entity_id`, ALL start events default to `entity_id=0`, and a SINGLE end event with `entity_id=0` would mark ALL active utilities as expired. The filter at L427-428 (`if s.entity_id not in ended_entities`) would produce an empty list, making the coach believe NO utilities are active when they actually are. **Consequence:** PlayerKnowledgeBuilder receives zero utility zones, degrading the Player-POV perception quality silently.
  ```python
  ended_entities = {e.entity_id for e in ends}
  return [s for s in starts if s.entity_id not in ended_entities]
  ```

* **Line 235-241** — WAL pragma listener registration per engine creation
  **Classification:** Correctness Observation (PASS)
  **Severity:** LOW (informational)
  **Evidence:** `@event.listens_for(engine, "connect")` is registered inside `_get_or_create_engine()` which only runs once per match_id (engines are cached). The listener correctly fires on every new connection opened by the engine's pool. WAL mode, synchronous=NORMAL, and busy_timeout=30000ms are all correct for concurrent per-match access. **No issue found.**

* **Line 244-251** — `SQLModel.metadata.create_all` with `tables=` filter
  **Classification:** Correctness Observation (PASS with caveat)
  **Severity:** MEDIUM
  **Evidence:** `SQLModel.metadata` is a GLOBAL registry containing ALL table definitions from the entire application (~20 tables from `db_models.py`). The `tables=[MatchTickState.__table__, MatchEventState.__table__, MatchMetadata.__table__]` filter is CRITICAL — without it, main DB tables (PlayerMatchStats, CoachState, etc.) would be created in every match database file. This is correct but FRAGILE: if a developer removes the `tables=` parameter, match databases silently bloat with 20+ empty tables. No guard or assertion exists to prevent this regression.

* **Line 272-274** — Exception handling in `get_match_session`
  **Classification:** Correctness Observation (PASS)
  **Severity:** LOW (informational)
  **Evidence:** Catches `Exception`, rolls back, re-raises. This is the correct pattern for SQLAlchemy session management. The broad catch is acceptable here because the rollback MUST happen for any exception type, and the re-raise ensures callers see the original error.

* **Line 500** — `start_tick = max(0, center_tick - window_size)` in `get_all_players_tick_window`
  **Classification:** Correctness Observation (PASS)
  **Severity:** LOW (informational)
  **Evidence:** Correctly bounds the window to prevent negative tick values. At 64 tick/s with window_size=320 (~5 seconds), the query returns ~3200 records maximum. The tick index ensures efficient range scan.

* **Line 612** — f-string in logger call
  **Classification:** False Negative (logging optimization)
  **Severity:** LOW
  **Evidence:** `_logger.info(f"One-time migration: {_OLD_IN_PROJECT} -> {match_data_path}")` — uses f-string instead of lazy `%s` formatting. This means the string interpolation happens even if logging level suppresses INFO messages. Functional impact is negligible (migration runs once), but violates structured logging best practices.

* **Line 705** — `except OSError: pass`
  **Classification:** Silent Failure
  **Severity:** MEDIUM
  **Evidence:** Silent exception swallowing when attempting to remove the old empty directory after migration. Violates CLAUDE.md "no silent exception handling". While the comment says "Not critical", a failed `os.rmdir` could indicate permission issues that mask other problems. Should log at DEBUG minimum.
  ```python
  except OSError:
      pass  # Not critical
  ```

### Action
* Add validation/assertion in `_get_or_create_engine` that `entity_id != 0` for utility events before relying on it for start/end pairing
* Replace `except OSError: pass` with `except OSError as e: logger.debug("...")`
* Convert f-string logger calls to `%s` format (cosmetic)
* Consider adding a regression test that verifies `SQLModel.metadata.create_all` only creates exactly 3 tables in match databases

---

## [2]. db_models.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/backend/storage/db_models.py`
**LOC:** 573 | **Priority:** HIGH
**Skills:** deep-audit, db-review, data-lifecycle-review

### Logic Summary
Central monolith database schema — 20 SQLModel table definitions, 2 enums (DatasetSplit, CoachStatus). Tables span: player statistics (PlayerMatchStats, PlayerTickState, RoundStats), pro player data (ProTeam, ProPlayer, ProPlayerStatCard), coaching (CoachingInsight, CoachingExperience, CoachState), knowledge (TacticalKnowledge), ingestion tracking (IngestionTask, HLTVDownload), match results (MatchResult, MapVeto), calibration (CalibrationSnapshot, RoleThresholdRecord), external data (Ext_TeamRoundStats, Ext_PlayerPlaystyle), notifications (ServiceNotification), and user profile (PlayerProfile).

### Findings

* **Lines 41, 43, 107, 151, 225, 226, 241, 253, 255, 262, 268, 292, 331, 343, 355, 364, 376, 412, 417, 419, 429, 480, 505, 560, 573** — `datetime.utcnow` pervasive
  **Classification:** Maintenance Concern
  **Severity:** LOW
  **Evidence:** 25+ usages of deprecated `datetime.utcnow` as `default_factory`. Same issue as match_data_manager.py. Functional impact is zero today. All timestamps are internally consistent (all naive UTC). Migration to `timezone.utc` aware timestamps would require schema migration.

* **Line 211-213** — Mixed concerns in `Ext_PlayerPlaystyle`
  **Classification:** Data Model Concern
  **Severity:** MEDIUM
  **Evidence:** `social_links_json`, `pc_specs_json`, `graphic_settings_json`, `cfg_file_path` are user profile attributes mixed into a playstyle model originally designed for CSV-imported role probabilities. The model conflates two concerns: (1) CS2 playstyle statistical profile, (2) user account metadata. This makes the table name misleading and queries awkward. However, renaming/splitting would break existing data.
  ```python
  social_links_json: Optional[str] = Field(default="{}")
  pc_specs_json: Optional[str] = Field(default="{}")
  graphic_settings_json: Optional[str] = Field(default="{}")
  ```

* **Line 254-255** — `IngestionTask.updated_at` not auto-refreshed
  **Classification:** Data Lifecycle Concern
  **Severity:** MEDIUM
  **Evidence:** Comment on L254 explicitly states `updated_at must be manually refreshed in run_ingestion.py update paths`. This is a documented design choice but creates a maintenance trap — any new code path that updates an IngestionTask without manually setting `updated_at` will silently leave stale timestamps. No database trigger or ORM event exists to enforce this.
  ```python
  # NOTE: updated_at must be manually refreshed in run_ingestion.py update paths
  updated_at: datetime = Field(default_factory=datetime.utcnow)
  ```

* **Line 460** — `game_state_json` unbounded string in CoachingExperience
  **Classification:** Data Lifecycle Concern
  **Severity:** MEDIUM
  **Evidence:** `game_state_json: str = Field(default="{}")` stores "full tick data at moment of experience" as JSON. With 10 players × ~30 fields each, a single snapshot could be 5-10KB. Over thousands of experiences, this becomes a significant DB size concern. No `max_length` or size validation exists. SQLite handles large TEXT columns fine, but query performance degrades for scanning.

* **Line 543** — `RoundStats.round_rating` is Optional
  **Classification:** Data Model Concern
  **Severity:** LOW
  **Evidence:** `round_rating: Optional[float] = Field(default=None)` — this field should always be computed via `compute_round_rating()` in `round_stats_builder.py`. Making it Optional means consumers must handle None cases. If the computation pipeline fails silently, round_rating stays None and downstream analytics silently skip the round. This is intentional (rounds with incomplete data may not have a rating), but consumers should explicitly handle None.

### Action
* Document the Ext_PlayerPlaystyle dual-purpose nature in a code comment or consider a future migration to split user profile fields
* Add an ORM event or utility function for IngestionTask.updated_at auto-refresh
* Consider adding a max_length or retention policy for game_state_json in CoachingExperience
* Audit all consumers of RoundStats.round_rating for None handling

---

## [3]. config.py

### Status: FAIL
**File:** `Programma_CS2_RENAN/core/config.py`
**LOC:** 330 | **Priority:** HIGH
**Skills:** deep-audit, state-audit, observability-audit, security-scan

### Logic Summary
Application configuration hub. Handles: path resolution (frozen/source mode), secret management (keyring integration), user settings (JSON file), database URL construction, directory creation. Thread-safe settings via `_settings_lock` (RLock). Settings refreshable via `refresh_settings()`. Secrets stored in Windows Credential Vault ("MacenaCS2Analyzer" service). Global module-level constants populated at import time.

### Findings

* **Line 141-173** — `_settings_lock` scope too narrow in `load_user_settings()`
  **Classification:** Silent Failure (Race Condition)
  **Severity:** CRITICAL
  **Evidence:** The lock only covers the `defaults` dict construction (L142-160). Lines 162-173 (file I/O + keyring retrieval) execute OUTSIDE the lock:
  ```python
  def load_user_settings():
      with _settings_lock:          # Lock acquired
          defaults = { ... }        # Lock covers only this
                                    # Lock RELEASED here
      current = defaults.copy()     # OUTSIDE lock
      if os.path.exists(SETTINGS_PATH):
          with open(SETTINGS_PATH, "r") as f:   # File read: OUTSIDE lock
              data = json.load(f)
              current.update(data)
      current["STEAM_API_KEY"] = get_secret(...)  # Keyring: OUTSIDE lock
      return current
  ```
  If `refresh_settings()` (which calls `load_user_settings()`) runs from one thread while `save_user_setting()` runs from another, the file read and write can interleave. This could produce inconsistent settings (partial old + partial new). **Consequence:** Session engine daemon threads calling `refresh_settings()` while UI thread saves settings could corrupt the in-memory configuration. The RLock is present but ineffective.

* **Line 186-190** — API keys in module-level globals
  **Classification:** Security Observation
  **Severity:** MEDIUM
  **Evidence:** `STEAM_API_KEY` and `FACEIT_API_KEY` are assigned to module-level globals at import time. Any module that imports `config` can read these values. While they come from keyring (good), they persist as plaintext Python strings in memory for the entire application lifetime. This is standard practice for desktop apps but noted for security awareness. `mask_secret()` (L134) exists but is not applied to these globals.

* **Line 244** — `STORAGE_ROOT` reassigned
  **Classification:** Correctness Observation
  **Severity:** LOW
  **Evidence:** `STORAGE_ROOT` is first defined at L50 via `get_writeable_dir()`, then overwritten at L244 to `USER_DATA_ROOT`. This shadow reassignment means the initial `SETTINGS_PATH = os.path.join(STORAGE_ROOT, "user_settings.json")` (L51) uses the FIRST value (writeable dir), while all later references to `STORAGE_ROOT` use the SECOND value (user data root). This is intentional (settings file must be in a writeable location independent of BRAIN_DATA_ROOT), but the variable reuse is confusing and could mislead developers.

* **Line 330** — `globals()[key] = original_value` dynamic global mutation
  **Classification:** Correctness Observation
  **Severity:** MEDIUM
  **Evidence:** `save_user_setting()` uses `globals()[key]` to dynamically update module-level variables. This is guarded by `_SETTING_NAME_TO_GLOBAL` set (L291-304), but any thread reading a global variable (e.g., `CS2_PLAYER_NAME`) while another thread is in `save_user_setting()` could see a partially-updated state. The `_settings_lock` protects `_settings` dict but does NOT protect the `globals()` write (it's inside the lock, but other threads read globals without acquiring the lock).

### Action
* **CRITICAL:** Extend `_settings_lock` scope in `load_user_settings()` to cover file I/O and keyring retrieval — the entire function body should be inside the lock
* Document STORAGE_ROOT reassignment with a clear comment explaining the intentional dual-assignment
* Consider making globals read-only and requiring all access through `get_setting()` which can be lock-protected

---

## [4]. spatial_data.py

### Status: PASS (minor observations)
**File:** `Programma_CS2_RENAN/core/spatial_data.py`
**LOC:** 380 | **Priority:** HIGH
**Skills:** deep-audit, correctness-check

### Logic Summary
Map metadata for Source 2 world-to-radar coordinate transformations. Frozen `MapMetadata` dataclass with Z-axis multi-level support (Nuke z_cutoff=-495, Vertigo z_cutoff=11700). `SpatialConfigLoader` singleton loads from JSON config (`data/map_config.json`) with hardcoded fallback registry. Module-level `__getattr__` lazy-loads `SPATIAL_REGISTRY`, `LANDMARKS`, `COMPETITIVE_MAPS`. Public API: `get_map_metadata()`, `get_map_metadata_for_z()`, `classify_vertical_level()`, `compute_z_penalty()`.

### Findings

* **Line 128** — `_MULTI_LEVEL_MAPS` set is dead code
  **Classification:** Dead Code
  **Severity:** LOW
  **Evidence:** `_MULTI_LEVEL_MAPS = {"de_nuke", "de_vertigo"}` is defined but never referenced. The `is_multi_level_map()` function (L311-318) dynamically checks `meta.z_cutoff is not None` from the registry instead. This set is a remnant of an earlier implementation.

* **Line 140-143** — Singleton `__new__` not thread-safe
  **Classification:** Correctness Observation
  **Severity:** MEDIUM
  **Evidence:** `SpatialConfigLoader.__new__()` checks `cls._instance is None` without synchronization. If two threads call `_get_loader()` simultaneously before the singleton is initialized, two instances could be created. In practice, this is called at import time on the main thread, so the risk is low but the pattern is fragile.

* **Line 184, 187** — Logging inconsistency in exception handler
  **Classification:** Observability Deviation
  **Severity:** LOW
  **Evidence:** Uses `import logging` and `logging.getLogger()` locally instead of the project-standard `get_logger()` from `observability/logger_setup.py`. Also uses f-string formatting (`f"Failed to load..."`) in the logger call instead of lazy `%s` formatting.

* **Line 378** — Magic number 500.0
  **Classification:** Correctness Observation (PASS)
  **Severity:** LOW
  **Evidence:** `min(dist / 500.0, 1.0)` — the 500 units saturation value is documented in the comment (L375-376) as covering "typical CS2 vertical play space". Acceptable as a domain constant, though extracting to a named constant would improve readability.

### Action
* Remove dead `_MULTI_LEVEL_MAPS` set or mark as `# DEPRECATED`
* Consider `threading.Lock` in singleton if thread-safety is ever required

---

## [5]. storage_manager.py

### Status: PASS (minor observations)
**File:** `Programma_CS2_RENAN/backend/storage/storage_manager.py`
**LOC:** 236 | **Priority:** NORMAL
**Skills:** deep-audit, db-review

### Logic Summary
Manages local storage for CS2 demos. Ingest folders (user-placed files), archive (post-processing), and pro demo paths. Quota enforcement via `enforce_quota()`. Demo deduplication in `list_new_demos()` cross-references `IngestionTask.demo_path` and `PlayerMatchStats.demo_name`. Path resolution respects `DEFAULT_DEMO_PATH`, `PRO_DEMO_PATH`, and `BRAIN_DATA_ROOT` settings.

### Findings

* **Line 129** — Double `stat()` call per file
  **Classification:** Performance Observation
  **Severity:** LOW
  **Evidence:** `_archive_old_files()` calls `f.stat().st_mtime` and `f.stat().st_size` separately, issuing two syscalls per file. Should cache `stat_result = f.stat()` and use `stat_result.st_mtime`, `stat_result.st_size`.

* **Line 189, 193** — Unbounded queries in `list_new_demos()`
  **Classification:** Data Lifecycle Concern
  **Severity:** MEDIUM
  **Evidence:** `session.exec(select(IngestionTask.demo_path)).all()` and `session.exec(select(PlayerMatchStats.demo_name)).all()` load ALL recorded demo paths/names into memory. With thousands of ingested demos, this creates unnecessary memory pressure. Should use a set-based EXISTS subquery or parameterized lookup instead.

### Action
* Cache `stat()` result in `_archive_old_files()`
* Refactor `list_new_demos()` to use database-side filtering instead of Python-side set difference

---

## [6]. backup_manager.py

### Status: FAIL
**File:** `Programma_CS2_RENAN/backend/storage/backup_manager.py`
**LOC:** 219 | **Priority:** NORMAL
**Skills:** deep-audit, db-review, data-lifecycle-review

### Logic Summary
Hot backup via SQLite `VACUUM INTO`, with retention policy (7 daily + 4 weekly). `BackupManager.create_checkpoint()` creates backup, validates integrity, prunes old backups. Path validation was added to prevent directory traversal in backup label.

### Findings

* **Line 58-63** — `target_path.stem` and `.resolve()` on `str` object
  **Classification:** Silent Failure (Type Error)
  **Severity:** CRITICAL
  **Evidence:** `target_path` is constructed via `os.path.join()` at L46, which returns a `str`. Lines 58-63 call `.stem`, `.resolve()`, and `.parent` which are `pathlib.Path` attributes — not available on `str`. This causes `AttributeError: 'str' object has no attribute 'stem'` **BEFORE** the `VACUUM INTO` executes, meaning **no backup is ever created**. The exception is caught by L88, logged as "Backup Failed", and the function returns `False`. The application continues without any backup protection.
  ```python
  # L46: target_path is str (from os.path.join)
  target_path = os.path.join(self.backup_dir, filename)
  # ...
  # L58-59: CRASH — str has no .stem
  label = target_path.stem
  if not re.match(r"^[a-zA-Z0-9_\-]+$", label):
  # L62: ALSO would crash — str has no .resolve()
  resolved = target_path.resolve()
  # L63: ALSO would crash — str has no .parent
  if not str(resolved).startswith(str(target_path.parent.resolve())):
  ```
  **Consequence:** Since the validation code was added, `create_checkpoint()` has ALWAYS failed. The `should_run_auto_backup()` check at L195-218 still works (checks file existence), so the app retries daily — and fails daily. **No backups exist.** This violates CLAUDE.md Rule 4: "untested backups = no backups".

* **Line 81** — `format(1024, ".2f")` produces string, not number
  **Classification:** Silent Failure (Type Error)
  **Severity:** MEDIUM (unreachable — blocked by L59 crash)
  **Evidence:** `os.path.getsize(target_path) / 1024 / format(1024, ".2f")` — `format(1024, ".2f")` returns the string `"1024.00"`, not a number. Dividing a float by a string would produce `TypeError`. This code is currently **unreachable** because L59 crashes first, but would become the next crash point if L59 were fixed.

### Action
* **CRITICAL FIX:** Convert `target_path` to `Path` object: `target_path = Path(self.backup_dir) / filename` at L46
* Fix L81: Replace `format(1024, ".2f")` with `1024` (or `1024**2` for MB conversion)
* **Verify after fix**: Run `BackupManager().create_checkpoint("test")` and confirm a backup file is created

---

## [7]. db_backup.py

### Status: PASS
**File:** `Programma_CS2_RENAN/backend/storage/db_backup.py`
**LOC:** 200 | **Priority:** NORMAL
**Skills:** deep-audit, db-review, data-lifecycle-review

### Logic Summary
WAL-safe backup system for three-tier architecture. `backup_monolith()`: WAL checkpoint(TRUNCATE) + shutil.copy2. `backup_match_data()`: per-match WAL checkpoint + tar.gz archive (skips .db-wal/.db-shm). `rotate_backups()`: keep N newest, delete excess. `restore_backup()`: copy + integrity check + rollback on failure.

### Findings

* **Line 36** — `datetime.utcnow()` deprecated
  **Classification:** Maintenance Concern
  **Severity:** LOW
  **Evidence:** Same pattern as throughout the project. Functional impact is zero.

* **Line 140** — `old_backup.unlink()` without try/except
  **Classification:** Correctness Observation
  **Severity:** LOW
  **Evidence:** In `rotate_backups()`, if `old_backup.unlink()` fails (permission denied, file locked by antivirus), the entire rotation loop stops. Should wrap in try/except with logging.

### Action
* Wrap L140 `old_backup.unlink()` in try/except to avoid rotation loop abort

---

## [8]. state_manager.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/backend/storage/state_manager.py`
**LOC:** 161 | **Priority:** NORMAL
**Skills:** deep-audit, state-audit

### Logic Summary
Centralized DAO for managing global `CoachState` in the monolith database. Thread-safe updates via `threading.Lock`. Methods: `get_state()`, `update_status()`, `update_parsing_progress()`, `update_training_progress()`, `heartbeat()`, `set_error()`, `add_notification()`. Module-level singleton `state_manager` created at import time.

### Findings

* **Line 1** — Uses `import logging` instead of `get_logger()`
  **Classification:** Observability Deviation
  **Severity:** LOW
  **Evidence:** Inconsistent with project standard. All other storage modules use `get_logger()` from `observability/logger_setup.py`.

* **Line 28** — `get_session("knowledge")` deprecated parameter
  **Classification:** Correctness Observation
  **Severity:** LOW
  **Evidence:** The `engine_key` parameter in `DatabaseManager.get_session()` is documented as deprecated (L73-76 of database.py). Passing `"knowledge"` has no effect — all sessions use the single engine. This is harmless but misleading, suggesting there was once a multi-engine setup.

* **Line 60** — Raw string passed where enum may be expected
  **Classification:** Correctness Observation
  **Severity:** MEDIUM
  **Evidence:** `state.status = status` sets the `CoachState.status` field using the raw `status` string parameter. While `CoachState.status` is typed as `str` in db_models.py, the `CoachStatus` enum exists for this purpose. No validation ensures the passed string matches any valid status value. Any typo in the status string silently corrupts state.

* **Line 160** — Module-level singleton creates DB connection at import time
  **Classification:** Correctness Observation
  **Severity:** LOW
  **Evidence:** `state_manager = StateManager()` at module level calls `get_db_manager()` which creates the SQLAlchemy engine. This means importing `state_manager.py` triggers database initialization, even if state management isn't needed. Consistent with `database.py`'s lazy singleton pattern.

### Action
* Consider validating `status` against `CoachStatus` enum values in `update_status()`
* Use `get_logger()` consistently

---

## [9]. database.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/backend/storage/database.py`
**LOC:** 136 | **Priority:** NORMAL
**Skills:** deep-audit, db-review

### Logic Summary
Industrial monolith database manager. Single SQLAlchemy engine with WAL mode (journal_mode=WAL, synchronous=NORMAL, busy_timeout=30000ms). pool_size=1, max_overflow=4. Session context manager with auto-commit/rollback. Lazy singleton via `get_db_manager()`. Upsert with special handling for `PlayerMatchStats` (composite key: demo_name + player_name).

### Findings

* **Line 1** — Uses `import logging` instead of `get_logger()`
  **Classification:** Observability Deviation
  **Severity:** LOW
  **Evidence:** Inconsistent with project standard.

* **Line 42** — Misleading comment: `pool_size=20` vs actual `pool_size=1`
  **Classification:** Correctness Observation
  **Severity:** LOW
  **Evidence:** Comment on L42 says `pool_size=20: Keeps connections open to avoid handshake overhead` but the actual parameter is `pool_size=1` (L47). The comment is stale — pool was downsized for SQLite single-writer safety. Misleading for developers.

* **Line 67** — `SQLModel.metadata.create_all(self.engine)` without `tables=` filter
  **Classification:** Data Model Concern
  **Severity:** MEDIUM
  **Evidence:** Unlike `match_data_manager.py` which correctly filters `tables=[...]`, the monolith's `create_db_and_tables()` uses `create_all(self.engine)` without filtering. `SQLModel.metadata` is a GLOBAL registry. If `match_data_manager.py` is imported BEFORE `create_db_and_tables()` is called, per-match tables (`MatchTickState`, `MatchEventState`, `MatchMetadata`) would be created in the monolith database. In current startup order this is unlikely, but the code is fragile — any import reordering could introduce table leakage.

* **Line 127-131** — Singleton not thread-safe
  **Classification:** Correctness Observation
  **Severity:** MEDIUM
  **Evidence:** `get_db_manager()` checks `_db_manager is None` without synchronization. If two threads call this simultaneously before initialization, two `DatabaseManager` instances (and two SQLAlchemy engines) could be created. Since `DatabaseManager.__init__()` registers event listeners on `self.engine`, this would result in one engine missing WAL pragmas. In practice, `init_database()` is called early on the main thread.

### Action
* Fix L42 comment to match actual pool_size=1
* Add `tables=` filter to `create_db_and_tables()` to explicitly list monolith-only tables
* Consider `threading.Lock` in `get_db_manager()` singleton

---

## [10]. db_migrate.py

### Status: FAIL
**File:** `Programma_CS2_RENAN/backend/storage/db_migrate.py`
**LOC:** 111 | **Priority:** NORMAL
**Skills:** deep-audit, db-review

### Logic Summary
Alembic migration utility for auto-upgrade on startup. `ensure_database_current()`: checks current vs head revision, runs `command.upgrade()` if needed. `get_current_revision()` and `get_head_revision()` for status queries.

### Findings

* **Line 33** — Imports non-existent `PROJECT_ROOT` from config
  **Classification:** Silent Failure (ImportError masked)
  **Severity:** HIGH
  **Evidence:** `from Programma_CS2_RENAN.core.config import DATABASE_URL, PROJECT_ROOT` — `PROJECT_ROOT` does NOT exist in `config.py`. The available constant is `BASE_DIR`. This `ImportError` is caught by L65:
  ```python
  except ImportError as e:
      # Alembic not installed - this is OK in frozen builds
      logger.debug("Alembic not available: %s", e)
      return True
  ```
  The error handler assumes "Alembic not installed" but the real cause is a wrong import name. The function returns `True` (success), so callers believe the database is current. **Consequence:** Alembic migrations NEVER execute, even when Alembic IS installed. Any schema change requiring a migration will silently fail to apply.

* **Line 101** — Same `PROJECT_ROOT` import in `get_head_revision()`
  **Classification:** Silent Failure
  **Severity:** LOW (secondary to L33)
  **Evidence:** `from Programma_CS2_RENAN.core.config import PROJECT_ROOT` — same non-existent import. Caught by `except Exception: return None` at L109. Always returns `None`.

### Action
* **HIGH FIX:** Replace `PROJECT_ROOT` with `BASE_DIR` in both L33 and L101
* Verify that `alembic.ini` and migration directory exist at the resolved path
* Consider adding a startup log message confirming migration status

---

## [11]. remote_file_server.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/backend/storage/remote_file_server.py`
**LOC:** 105 | **Priority:** NORMAL
**Skills:** deep-audit, security-scan

### Logic Summary
Lightweight FastAPI server for personal demo file sharing between machines. Endpoints: `/list` (demo files with metadata), `/download/{filename}` (file download), `/health`. API key authentication via `access_token` header. Path traversal protection at L84-85 via `.resolve()` + `startswith()`.

### Findings

* **Line 35, 43** — `api_key_header` can be `None` → TypeError in hmac
  **Classification:** Silent Failure (Type Error)
  **Severity:** HIGH
  **Evidence:** `APIKeyHeader(name=API_KEY_NAME, auto_error=False)` at L35 means when no header is provided, `api_key_header` is `None`. At L43, `hmac.compare_digest(api_key_header, API_KEY)` receives `None` as first argument, causing `TypeError: a bytes-like object is required, not 'NoneType'`. This results in an unhandled 500 Internal Server Error. While not a security bypass (request is rejected), it exposes implementation details in the error response.
  ```python
  api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

  async def get_api_key(api_key_header: str = Security(api_key_header)):
      if not API_KEY:
          raise HTTPException(status_code=503, ...)
      import hmac
      if hmac.compare_digest(api_key_header, API_KEY):  # api_key_header can be None!
  ```

* **Line 84-85** — Path traversal protection
  **Classification:** Correctness Observation (PASS)
  **Severity:** LOW (informational)
  **Evidence:** `file_path = (ARCHIVE_PATH / filename).resolve()` followed by `if not str(file_path).startswith(str(ARCHIVE_PATH.resolve()))` correctly prevents directory traversal attacks like `../../etc/passwd`. Implementation is correct.

### Action
* Add `if not api_key_header:` check before `hmac.compare_digest()` at L43, raising HTTPException(403)

---

## [12]. stat_aggregator.py

### Status: PASS
**File:** `Programma_CS2_RENAN/backend/storage/stat_aggregator.py`
**LOC:** 100 | **Priority:** NORMAL
**Skills:** deep-audit, correctness-check

### Logic Summary
HLTV spider data persistence. Functions for persisting scraped pro team/player data into the monolith database. Handles ProTeam, ProPlayer, ProPlayerStatCard, MatchResult, and MapVeto records. Uses `session.merge()` for upsert behavior.

### Findings

* **No significant issues found.** Minor observation: some functions call `session.commit()` explicitly within a `db.get_session()` context manager that already auto-commits on exit. This is redundant but not harmful (double-commit is a no-op in SQLAlchemy).

---

## [13]. maintenance.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/backend/storage/maintenance.py`
**LOC:** 55 | **Priority:** NORMAL
**Skills:** deep-audit, data-lifecycle-review

### Logic Summary
Old metadata pruning and optional demo compression. `prune_old_metadata()`: removes `PlayerTickState` records for matches older than N days while preserving `PlayerMatchStats` aggregates. `compress_archived_demos()`: stub function (body is `pass`).

### Findings

* **Line 35-36** — `.in_()` clause may exceed SQLite parameter limit
  **Classification:** Correctness Observation
  **Severity:** MEDIUM
  **Evidence:** `PlayerTickState.demo_name.in_(old_demo_names)` — if there are more than 999 old demo names, this exceeds SQLite's maximum number of terms in a compound SELECT (SQLITE_MAX_VARIABLE_NUMBER). The query would fail with `OperationalError: too many SQL variables`. Should batch the delete in chunks of 500.

* **Line 48-54** — `compress_archived_demos()` is dead code
  **Classification:** Dead Code
  **Severity:** LOW
  **Evidence:** Function body is `pass`. Comment says "Currently handled by StorageManager". Should be removed or implemented.

### Action
* Batch the `.in_()` delete into chunks of 500 to respect SQLite limits
* Remove or implement `compress_archived_demos()`

---

## [14]. demo_frame.py

### Status: PASS
**File:** `Programma_CS2_RENAN/core/demo_frame.py`
**LOC:** 151 | **Priority:** NORMAL
**Skills:** deep-audit, correctness-check

### Logic Summary
Core data models for game state representation. Dataclasses: `PlayerState` (comprehensive player state at a tick), `DemoFrame` (full tick snapshot with both teams), `NadeState` (grenade tracking), `BombState`, `NadeType` enum. Used as intermediate representation between parser output and database storage.

### Findings

* **No issues found.** Clean dataclass definitions with appropriate defaults. `NadeType` enum correctly maps to CS2 grenade types.

---

## [15]. lifecycle.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/core/lifecycle.py`
**LOC:** 141 | **Priority:** NORMAL
**Skills:** deep-audit, state-audit

### Logic Summary
Application lifecycle management. Single-instance enforcement via Windows Named Mutex (`Global\MacenaCS2Analyzer_Unique_Lock_v1`). Daemon process management: launches `session_engine.py` as subprocess with PYTHONPATH injection. Graceful shutdown with terminate → 3s wait → kill escalation. Module-level singleton `lifecycle`.

### Findings

* **Line 79-80** — Open file handles without `with` statement
  **Classification:** Resource Leak Risk
  **Severity:** MEDIUM
  **Evidence:** `self._out_log = open(...)` and `self._err_log = open(...)` are stored as instance attributes without `with` context managers. If `subprocess.Popen()` fails at L82, the file handles are leaked (never closed). The `shutdown()` method (L121-126) does close them, but only if shutdown is called. The `atexit.register(self.shutdown)` at L95 helps, but atexit handlers are not guaranteed to run on all termination paths (e.g., SIGKILL, power failure).

* **Line 89** — `close_fds=True` on Windows
  **Classification:** Correctness Observation
  **Severity:** LOW
  **Evidence:** On Windows, `close_fds=True` with `subprocess.Popen` cannot be used when redirecting stdin/stdout/stderr (pre-Python 3.7 behavior). Since Python 3.7+ on Windows, `close_fds=True` is the default and works with redirected handles, so this is technically correct but the explicit flag is unnecessary.

* **Line 134** — Uses `import logging` in shutdown handler
  **Classification:** Observability Deviation
  **Severity:** LOW
  **Evidence:** `import logging` and `logging.getLogger()` used instead of the already-imported `logger` at L10. This was likely added as a safety measure in case the `logger` reference was garbage-collected during shutdown, but it's inconsistent.

### Action
* Wrap file handle creation in try/finally or use a helper that closes on Popen failure
* Remove unnecessary `close_fds=True` or add a comment explaining the intent

---

## [16]. logger.py

### Status: WARNING
**File:** `Programma_CS2_RENAN/core/logger.py`
**LOC:** 35 | **Priority:** LOW
**Skills:** deep-audit, observability-audit

### Logic Summary
Legacy logger setup module. Creates file handlers for rotating logs and a console handler. Returns configured logger instances.

### Findings

* **File-level concern** — Potential handler duplication with `observability/logger_setup.py`
  **Classification:** Observability Deviation
  **Severity:** LOW
  **Evidence:** Both `core/logger.py` and `observability/logger_setup.py` configure logging handlers. If both modules are imported, handlers accumulate on the root logger, causing duplicate log entries. The project should consolidate to a single logging setup — `observability/logger_setup.py` appears to be the canonical one (used by most modules).

### Action
* Deprecate `core/logger.py` in favor of `observability/logger_setup.py`
* Verify no module exclusively depends on `core/logger.py`

---

## [17]. constants.py

### Status: PASS
**File:** `Programma_CS2_RENAN/core/constants.py`
**LOC:** 0 (empty) | **Priority:** LOW

### Findings
* Empty file. No issues. May be a placeholder for future constants.

---

## [18]. logger_setup.py

### Status: PASS
**File:** `Programma_CS2_RENAN/observability/logger_setup.py`
**LOC:** 49 | **Priority:** LOW
**Skills:** deep-audit, observability-audit

### Logic Summary
Primary structured logging setup. `get_logger(name)` function creates loggers with console handler (StreamHandler). Avoids `TimedRotatingFileHandler` for Windows compatibility. Uses `%(asctime)s` format with module name.

### Findings

* **No issues found.** Clean implementation. Correctly avoids adding duplicate handlers by checking existing handlers before setup.

---

## [19]. rasp.py

### Status: PASS
**File:** `Programma_CS2_RENAN/observability/rasp.py`
**LOC:** 136 | **Priority:** NORMAL
**Skills:** deep-audit, security-scan

### Logic Summary
Runtime Application Self-Protection (RASP) Guard. `RASPGuard.verify_runtime_integrity()`: loads `integrity_manifest.json`, verifies SHA-256 hashes of critical files. `check_frozen_binary()`: validates executable environment for PyInstaller builds. Gracefully skips in development mode if manifest not generated.

### Findings

* **No issues found.** Correct SHA-256 implementation with 4096-byte block reads. Development mode skip is appropriate. Multiple manifest path candidates handled for PyInstaller packaging variations.

---

## [20]. registry.py

### Status: PASS
**File:** `Programma_CS2_RENAN/core/registry.py`
**LOC:** 43 | **Priority:** LOW

### Logic Summary
KivyMD Screen registry for dynamic screen management in the desktop application.

### Findings

* **No issues found.** Simple, correct implementation.

---

## [21]. frozen_hook.py

### Status: PASS
**File:** `Programma_CS2_RENAN/core/frozen_hook.py`
**LOC:** 18 | **Priority:** LOW

### Logic Summary
PyInstaller freeze support hook. Adjusts import paths and working directory for frozen builds.

### Findings

* **No issues found.** Minimal, correct implementation.

---

## [22]. sentry_setup.py

### Status: PASS
**File:** `Programma_CS2_RENAN/observability/sentry_setup.py`
**LOC:** 153 | **Priority:** NORMAL
**Skills:** deep-audit, observability-audit, security-scan

### Logic Summary
Sentry error reporting with double opt-in (user setting + DSN availability). PII scrubbing via `_before_send()` callback: strips user IP, sanitizes exception values containing paths/emails/IPs, removes sensitive headers. Graceful no-op if Sentry SDK not installed.

### Findings

* **No issues found.** Well-implemented PII scrubbing. Double opt-in respects user privacy. The `_before_send` callback correctly sanitizes all event data before transmission.

---

## [23]. app_types.py

### Status: PASS
**File:** `Programma_CS2_RENAN/core/app_types.py`
**LOC:** 47 | **Priority:** LOW

### Logic Summary
Type aliases (`MatchID`, `Tick`, `PlayerID`), `Team` enum (numeric: 0=Unknown, 1=CT, 2=T), `IngestionStatus` enum, and TypedDicts for demo data interchange. Note: `Team` enum here uses numeric values while `demo_frame.py` uses string-based Team representation — both are documented.

### Findings

* **No issues found.** Clean type definitions with appropriate documentation.

---

## [R]. Rapid Scan — `__init__.py` Stubs + `migrations/env.py`

| File | LOC | Status | Notes |
|---|---:|---|---|
| `backend/__init__.py` | ~1 | PASS | Empty or minimal |
| `backend/storage/__init__.py` | ~1 | PASS | Empty or minimal |
| `core/__init__.py` | ~1 | PASS | Empty or minimal |
| `observability/__init__.py` | ~1 | PASS | Empty or minimal |
| `migrations/__init__.py` | ~1 | PASS | Empty or minimal |

No issues in any `__init__.py` stub files.

---

## Phase 1 — Cross-Phase Notes

### Pattern: `datetime.utcnow` (Pervasive — LOW)
Found in: match_data_manager.py, db_models.py (25+ usages), db_backup.py, state_manager.py.
All timestamps are naive UTC and internally consistent. Migration to `datetime.now(timezone.utc)` would require a coordinated schema migration across all tables. **Recommendation:** Track as a single low-priority batch migration task, not per-file fixes.

### Pattern: `import logging` vs `get_logger()` (Inconsistency)
Found in: spatial_data.py (exception handler), state_manager.py, database.py, lifecycle.py (shutdown handler).
Four modules use `import logging` / `logging.getLogger()` instead of the project-standard `get_logger()` from `observability/logger_setup.py`. **Recommendation:** Standardize to `get_logger()` in all storage and core modules.

### Pattern: Module-Level Singletons at Import Time
Found in: state_manager.py (`state_manager`), lifecycle.py (`lifecycle`), database.py (`_db_manager` lazy but triggered by importers).
These trigger database connections, file system access, and Windows API calls at import time. While acceptable for a desktop application with a single entry point, this makes unit testing and static analysis harder.

---

## Phase 1 — Quality Gate Verification

### DB Model Field Names (Cross-reference AIstate.md Catena 3/4)
- `PlayerMatchStats`: Confirmed `avg_kills`, `avg_deaths`, `avg_kast` (NOT `kills`/`deaths`/`kast_pct`) ✓
- `RoundStats`: Confirmed `damage_dealt` (NOT `damage`) ✓
- `CoachState`: Fields match state_manager.py accessors ✓
- `MatchEventState.entity_id`: Default=0 issue documented (Finding #1.2) ✓

### Config Constants
- `DATABASE_URL`, `CORE_DB_DIR`, `DB_DIR`, `BASE_DIR` all correctly defined ✓
- `PROJECT_ROOT` does NOT exist → breaks db_migrate.py (Finding #10.1) ✗
- `MATCH_DATA_PATH` correctly resolves via `_resolve_match_data_path()` ✓

### Storage Contracts
- Monolith WAL mode enforced via `@event.listens_for` in both database.py and match_data_manager.py ✓
- Per-match `tables=` filter in match_data_manager.py prevents leakage ✓
- Monolith `create_all` missing `tables=` filter — fragile (Finding #9.3) ✗
- Backup system non-functional due to type error (Finding #6.1) ✗

### AIstate.md Reconciliation
- **G-07** (Teacher daemon wiring): Confirmed — `_run_belief_calibration()` does NOT exist in session_engine.py (will be audited in Phase 6)
- **Catena 3/4** (field names): All verified correct in db_models.py ✓

---

## Phase 1 — Issue Priority Matrix

| # | File | Severity | Finding | Blast Radius |
|---|---|---|---|---|
| 6.1 | backup_manager.py | **CRITICAL** | `str.stem` crash → no backups ever created | Data loss risk — no backup protection |
| 3.1 | config.py | **CRITICAL** | Lock scope too narrow → race condition | Config corruption under concurrent access |
| 10.1 | db_migrate.py | **HIGH** | `PROJECT_ROOT` missing → migrations never run | Schema drift — new columns never added |
| 11.1 | remote_file_server.py | **HIGH** | `None` api_key → TypeError | 500 errors on unauthenticated requests |
| 1.2 | match_data_manager.py | **HIGH** | `entity_id=0` default → utility tracking breaks | Player-POV perception degradation |
