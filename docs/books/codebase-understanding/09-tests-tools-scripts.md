# Chapter 9: Tests, Tools, and Scripts

> Exhaustive reference covering every class, function, test case, fixture, constant, and design mechanism found in the `Programma_CS2_RENAN/tools/` directory (17 files), the `Programma_CS2_RENAN/tests/` directory (~100 test files), and the top-level `tools/headless_validator.py`.

---

## Part I: Tools Infrastructure and Shared Foundations

### 1. `tools/__init__.py` (0 lines)

Empty package marker. No imports, classes, or functions.

---

### 2. `tools/_infra.py` (438 lines)

Shared infrastructure for ALL tool files. This is the foundation layer that every validator and tool imports.

#### Constants

| Name | Value | Purpose |
|------|-------|---------|
| `EXPECTED_VENV` | `"cs2analyzer"` | Virtual environment name for the venv guard |
| `PROJECT_ROOT` | `Path` (resolved at import) | Absolute path to repo root |
| `SOURCE_ROOT` | `Path` (resolved at import) | Absolute path to `Programma_CS2_RENAN/` |

#### Functions

- **`require_venv()`** -- Exits with code 2 if not inside a virtualenv. Bypassed when `CI` environment variable is set. Prevents misleading import failures from system Python.

- **`path_stabilize() -> tuple[Path, Path]`** -- Canonical path resolver. Walks up from `_infra.py` to discover `SOURCE_ROOT` (parent) and `PROJECT_ROOT` (grandparent). Adds `PROJECT_ROOT` to `sys.path`. Sets `KIVY_NO_ARGS=1` to prevent Kivy from hijacking CLI arguments. Reconfigures `sys.stdout` to UTF-8 on Windows.

- **`validate_tool_contract(file_path: Path) -> List[str]`** -- Verifies a tool file follows project conventions: has `if __name__ == "__main__":` guard, is syntactically valid Python. Returns a list of violation strings (empty means pass).

#### Classes

**`Severity(Enum)`**
Members: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `HEALTHY`. Used throughout the reporting pipeline to classify check results.

**`ToolResult` (dataclass)**
Fields: `phase: str`, `name: str`, `passed: bool`, `error: Optional[str]`, `duration_ms: float`, `severity: Severity`. Represents a single check outcome. String representation: `[PASS|FAIL] phase/name`.

**`ToolReport`**
Aggregates `ToolResult` instances into a structured report.
- **Properties**: `passed` (count), `failed` (count -- only CRITICAL/ERROR), `warnings` (count -- WARNING/INFO failures), `total`, `all_passed` (True if `failed == 0`), `elapsed_s`
- **Methods**: `add(phase, name, passed, error, duration_ms, severity) -> ToolResult`, `failures() -> List[ToolResult]`, `to_dict() -> Dict`, `to_json(indent) -> str`
- JSON serialization normalizes `Severity` enum across Python versions (handles Enum instances on <3.12 and primitive values on >=3.12).

**`Console`**
Lightweight terminal formatting using ANSI escape codes, with no external dependency on Rich.
- **Class attributes**: `_COLORS` (10 ANSI codes), `SEVERITY_STYLES` (maps Severity to style tuples)
- **Methods**: `_detect_color() -> bool` (respects `NO_COLOR`, detects Windows Terminal via `WT_SESSION`), `_apply(text, *styles) -> str`, `header(title, version)`, `section(name, index, total)`, `check(name, passed, detail, severity)`, `severity_badge(sev, text) -> str`, `summary(report: ToolReport)`
- The `summary()` method prints hard failures and warnings separately, with color-coded labels.

**`BaseValidator(ABC)`**
Abstract base for all validation tools. Implements the Template Method pattern.
- **Constructor**: Creates `ToolReport`, `Console`, stores `args=None`
- **Abstract**: `define_checks()` -- subclasses implement this to register all checks
- **`run() -> int`**: Parses args, sets quiet mode, prints header, calls `define_checks()`, prints summary, optionally outputs JSON. Returns 0 (pass) or 1 (fail). Catches unhandled exceptions as CRITICAL failures.
- **`check(phase, name, condition, error, detail, severity) -> bool`**: Registers a check result and prints it. Returns the condition value.
- **`_parse_args()`**: Standard argparse with `--verbose`, `--json`, `--quiet` flags.
- **`_add_extra_args(parser)`**: Hook for subclasses to add tool-specific arguments.

---

### 3. `tools/aggregate_match_stats_sql.py` (915 lines)

D2A SQL-only `PlayerMatchStats` aggregator. The largest tool file. Reads each `match_*.db` shard, runs SQL aggregations against `matchtickstate` and `match_event_state` tables, computes 25 Class-A `PlayerMatchStats` fields, and UPSERTs rows tagged `data_quality='full_sql'`.

#### Constants

| Name | Value | Purpose |
|------|-------|---------|
| `MIN_VALID_ROUND_COUNT` | `13` | Minimum rounds for CS2 MR12 (13-0 sweep) |
| `MAX_VALID_ROUND_COUNT` | `36` | Maximum rounds with overtime (regulation 24 + 2 OTs) |
| `DATA_QUALITY_FULL_SQL` | `"full_sql"` | Quality tag for SQL-derived rows |
| `DATA_QUALITY_FULL_SQL_ROUND_ANOMALY` | `"full_sql_round_count_anomaly"` | Quality tag when round count outside [13, 36] |
| `DATA_QUALITY_COMPLETE` | `"complete"` | Quality tag for fully-parsed rows (D2B) |
| `DATA_QUALITY_REGISTERED_ONLY` | `"registered_only"` | Quality tag for registered but unprocessed |
| `DATA_QUALITY_PARTIAL` | `"partial"` | Quality tag for partially processed |
| `MIN_NONZERO_FIELDS_FOR_REAL_PLAYER` | `1` | Threshold to filter observer/caster/bot rows |
| `RECONCILE_FIELD_TOLERANCE_PCT` | `5.0` | Drift tolerance percentage per field |
| `RECONCILE_ROW_HALT_PCT` | `10.0` | Row drift percentage that triggers halt |
| `RECONCILE_FIELDS` | Tuple of 23 strings | Class-A fields checked during reconciliation |

#### Functions

- **`_build_arg_parser() -> ArgumentParser`** -- CLI with flags: `--match-id`, `--limit`, `--dry-run` (default True), `--commit`, `--reconcile`, `--force`, `--really-force`, `--no-lock`, `--checkpoint-file`, `--report-out`.

- **`_ds_split_for_demo(demo_name: str) -> str`** -- Deterministic 70/15/15 train/val/test split using MD5 hash of demo name. Ensures all player rows from the same match land in the same split (no data leakage).

- **`_safe_float(v) -> float`** -- Coerces DB values to finite float. Maps None/NaN/Inf to 0.0.

- **`_read_match_metadata(match_db_path: Path) -> Optional[dict]`** -- Opens a match shard as read-only immutable SQLite, reads `match_metadata` table. Derives `round_count` from `MAX(round_number)` if metadata has 0. Parses `match_date` with ISO format fallback to file mtime.

- **`_aggregate_per_player(match_db_path: Path) -> list[dict]`** -- The core aggregation function. Uses cumulative `MAX(*_total)` columns as source of truth (not per-round counters, which undercount). Computes: kills, deaths, assists, headshot kills, score, cash spent, per-round damage/kills/utility arrays, utility damage from event stream (HE, molotov, smoke), trade kill detection via `detect_trade_kills()`. Builds team roster from early ticks (first 10%) using majority vote on team name. Handles full team name strings (`TERRORIST`, `CT`, `COUNTER-TERRORIST`). Returns list of dicts with 20+ fields per player.

- **`_stdev(values: list[float]) -> float`** -- Sample standard deviation with Bessel's correction. Returns 0.0 for fewer than 2 values.

- **`_build_player_match_stats(meta, agg, source_path) -> PlayerMatchStats`** -- Composes a SQLModel instance. Computes: avg_kills, avg_deaths, avg_adr, avg_hs, KPR, DPR, KD ratio, KAST (via `kast_mod.estimate_kast_from_stats`), HLTV 2.0 rating (replicates `rating.compute_hltv2_rating` logic for per-component breakdown), kill_std, adr_std, impact_rounds (share of rounds with >= 1 kill), trade ratios, utility per round. Tags `data_quality` based on round count validity. Overrides `is_pro` from path heuristic (`DEMO_PRO_PLAYERS` in path).

- **`_existing_quality(session, demo_name, player_name) -> Optional[str]`** -- Queries existing `data_quality` for a player-match pair.

- **`_reconcile_against_complete(report_path: Path) -> dict`** -- Diffs fresh SQL aggregates against existing `data_quality='complete'` rows. Computes per-field percentage drift. Writes JSON report. Returns verdict: `"within_tolerance"` or `"drift_detected"` (halt if >10% of rows show >5% drift on any field).

- **`main(argv: Optional[list[str]]) -> int`** -- Entry point. Handles modes: reconcile-only, dry-run, commit. Acquires `d_track_running` lock for writes. `--really-force` has a 5-second countdown before overwriting `complete` rows. Iterates match shards, aggregates, and UPSERTs.

---

### 4. `tools/backend_validator.py` (610 lines)

**`BackendValidator(BaseValidator)`** -- Unified backend validation gate. Version 3.0. Replaces the older `Clinical_Integration_Validator` and `system_audit_suite`.

Seven sections, each a private method called from `define_checks()`:

1. **`_check_environment()`** -- PyTorch availability and version (>=2.0), CUDA status (INFO severity), critical dependencies (psutil, kivymd, sklearn, demoparser2, sqlmodel), METADATA_DIM > 0.

2. **`_check_database()`** -- Calls `init_database()` and `get_db_manager()`. Verifies: `SELECT 1` connectivity, WAL mode active (`PRAGMA journal_mode`), required tables (playerprofile, coachinginsight, playermatchstats, playertickstate, coachstate, roundstats), CoachState CRUD smoke test, backup recency (<7 days, WARNING severity).

3. **`_check_model_zoo()`** -- Instantiates models via `ModelFactory.get_model()`: default (TeacherRefinementNN) with inference shape check, JEPA, VL-JEPA with `forward_vl()` validation (16 concepts), NeuralRoleHead with softmax sum-to-1.0 check.

4. **`_check_analysis_modules()`** -- Verifies: DemoFormatAdapter changelog, TemporalBaselineDecay weight range, EngagementRangeAnalyzer profile, AdaptiveBeliefCalibrator auto_calibrate + MIN_SAMPLES, CoachingDialogueEngine availability + methods, Chronovisor CriticalMoment context_ticks + suggested_review.

5. **`_check_coaching_pipeline()`** -- CoachingService (COPER mode) generate + coper methods, ExperienceBank add + retrieve, KnowledgeRetriever retrieve.

6. **`_check_resource_integrity()`** -- layout.kv existence, PHOTO_GUI directory (>5 assets), Models directory, Settings file, map_config.json validity, integrity manifest freshness (<168h, WARNING), model checkpoint freshness (<30d, WARNING).

7. **`_check_service_health()`** -- HLTV sync daemon PID file + psutil alive check (INFO), Windows registry auto-start entry, SQLModel version >= 0.0.14.

---

### 5. `tools/build_tools.py` (368 lines)

Consolidated build pipeline with 4 subcommands. Uses `Console` from `_infra.py`.

#### Constants

- `ERROR_PATTERNS` -- Dict mapping 7 regex patterns to error categories: `MISSING_MODULE`, `IMPORT_ERROR`, `MISSING_FILE`, `SYNTAX_ERROR`, `PERMISSION_ERROR`, `MISSING_DLL`, `ENCODING_ERROR`.

#### Functions

- **`run_command(cmd, label, cwd, capture)`** -- Executes a command via `subprocess.run` with `shell=False`, 600s timeout. Reports via `console.check()`.

- **`calculate_sha256(filepath) -> str`** -- Chunked SHA-256 hash computation (8192-byte chunks).

- **`cmd_build(args)`** -- Full pipeline: Black format check, isort import check, pytest suite (abort on failure), Alembic migration (abort on failure), PyInstaller build from `macena.spec`, SHA-256 hash generation for dist binaries (platform-aware: `.exe` on Windows, executable files on Linux/macOS), writes `build_manifest.json`.

- **`cmd_verify(args)`** -- Post-build integrity verification. Checks forbidden file patterns in dist/ (`.db`, `.dem`, `.pt`, `.pth`, `user_settings.json`, `.env`, `.pem`, `.key`, `.log`). Validates required files (macena.spec), build manifest SHA-256.

- **`analyze_error(line) -> Optional[str]`** -- Categorizes a build error line against `ERROR_PATTERNS`.

- **`cmd_debug_build(args)`** -- Runs PyInstaller build with real-time error categorization via `subprocess.Popen`. Streams stdout, categorizes errors, writes `build_report.json`.

- **`cmd_manifest(args)`** -- Generates or verifies the integrity manifest. `--verify-only` loads and counts files. Generation delegates to `sync_integrity_manifest.py`.

- **`main()`** -- CLI with subparser dispatch: `build`, `verify`, `debug-build`, `manifest`.

---

### 6. `tools/context_gatherer.py` (578 lines)

Gathers relational context for any file: imports, dependents, tests, API, git history.

#### Constants

- `VERSION = "1.0"`
- `SEP = " ▪ "` (Unicode black small square separator)
- `STDLIB` -- Set of stdlib module names (from `sys.stdlib_module_names` on Python 3.10+, or hardcoded fallback of 41 names)

#### Functions

- **`_safe(fn, fallback=None)`** -- Try/except wrapper that logs warnings and returns fallback on failure.

- **`resolve_target(target: str) -> Path`** -- Resolves file path or dotted module name to absolute Path. Tries: absolute path, relative from PROJECT_ROOT, relative from SOURCE_ROOT, dotted module name to `.py` file, dotted package to `__init__.py`.

- **`collect_file_info(p: Path) -> dict`** -- Returns: path, LOC, size_kb, modified date.

- **`collect_structure(p: Path) -> dict`** -- AST-based class and function extraction. Returns class names with method lists, function names with args and return types.

- **`_classify_import(module_name: str) -> str`** -- Classifies imports as "proj" (Programma_CS2_RENAN), "std" (stdlib), or "ext" (third-party).

- **`collect_imports(p: Path) -> dict`** -- AST-based import collection. Returns `{proj, std, ext}` sorted lists.

- **`collect_forward_deps(p: Path, imports: dict) -> list`** -- Resolves project imports to actual file paths.

- **`collect_reverse_deps(p: Path) -> list`** -- Finds all `.py` files in SOURCE_ROOT that contain a substring matching this module's dotted path. Note F8-11: substring matching can create false positives from comments/strings.

- **`collect_related_tests(p: Path) -> list`** -- Finds test files referencing this module by stem or dotted name.

- **`collect_git_history(p: Path) -> list`** -- Last 5 git commits touching this file (`git log -5`). Uses list args with `shell=False` and 10s timeout.

- **`collect_public_api(p: Path) -> list`** -- AST-based extraction of public (non-underscore) classes and functions with signatures.

- **`_format_signature(node) -> str`** -- Formats a function/method AST node as human-readable signature.

- **`format_compact(data) -> str`** -- Formats all collected context into a compact multi-line text report.

- **`main()`** -- CLI: `target` (required), `--json`, `--quiet`. Runs all collectors and outputs formatted or JSON result.

---

### 7. `tools/db_inspector.py` (526 lines)

Compact database diagnostics tool. Produces a full DB state report without manual queries.

#### Constants

- `VERSION = "1.0"`, `SEP = " ▪ "` (bullet separator)
- `PROJECT_ROOT, SOURCE_ROOT` from `path_stabilize()`
- `logger` named `"cs2analyzer.db_inspector"`

#### Functions

- **`_validate_table_name(name: str, allowed: set) -> str`** -- Validates table name against a whitelist to prevent SQL injection. Raises `ValueError` if not in `allowed`.

- **`_safe(fn, fallback=None)`** -- Generic safe-execution wrapper with logging.

- **`_get_db()`** -- Imports `get_db_manager` and `init_database`, initializes database, returns manager.

- **`collect_connectivity()`** -- Returns dict with `connected`, `wal` (journal mode), `sync` (synchronous mode), `timeout` (busy_timeout in seconds), `db_mb` (file size). Uses PRAGMAs.

- **`collect_tables()`** -- Uses SQLAlchemy inspector to get table names. Runs `SELECT COUNT(*)` for each (with whitelist validation). Returns `{"total": int, "tables": [...]}` sorted by row count descending.

- **`collect_storage()`** -- Scans `DATABASE_URL`, `HLTV_DATABASE_URL`, `MATCH_DATA_PATH`. Returns main/hltv file sizes and match_data statistics (count, total_gb, min_mb, max_mb, avg_mb).

- **`collect_ingestion()`** -- Queries `ingestiontask` for status distribution, oldest queued item, and last error message (truncated to 80 chars).

- **`collect_coach_state()`** -- Queries `coachstate` for single row: status, heartbeat, epoch, target_epoch, loss, matches, hunter, digester, teacher.

- **`collect_alembic()`** -- Checks `alembic_version` table existence and reads `version_num`.

- **`collect_splits()`** -- Queries `playermatchstats` for `dataset_split` distribution and `is_pro` distribution.

- **`collect_table_schema(table_name)`** -- Uses SQLAlchemy inspector to get columns (name, type, nullable, default, primary_key), foreign keys, indexes, and row count.

- **`format_compact(data, table_detail=None)`** -- Produces human-readable multi-section report. CLI: `--json`, `--quiet`, `--table`.

- **`main()`** -- CLI entry point with JSON or compact text output.

---

### 8. `tools/demo_inspector.py` (346 lines)

Unified demo file (.dem) inspection tool. Merges and supersedes 7 legacy probe scripts: `probe_demo_data`, `probe_entity_track`, `probe_events_advanced`, `probe_inventory`, `probe_stats_fields`, `probe_trajectories`, `probe_inv_direct`.

#### Functions

- **`find_demo(demo_path=None)`** -- Locates a `.dem` file by checking: explicit path, `SOURCE_ROOT/data/`, `demos_to_process`, `ingestion/cache`, `PRO_DEMO_PATH` from config.

- **`get_parser(demo_path)`** -- Returns `DemoParser(demo_path)` from `demoparser2`. Exits if not installed.

- **`extract_df(event_result)`** -- Handles multiple return formats from DemoParser: raw DataFrame, list of tuples, list of dicts.

- **`cmd_events(args)`** -- Lists all game event types. Probes 5 critical events: `player_death`, `bomb_planted`, `round_end`, `weapon_fire`, `player_hurt`. Shows occurrence counts, columns, and 2-row samples.

- **`cmd_fields(args)`** -- Probes player stats fields (health, kills_total, deaths_total, money, player_name, team_num), weapon inventory fields, and inventory blob.

- **`cmd_track(args)`** -- Accepts `entity_type` argument: `"smoke"`, `"grenade"`, or `"all"`. Smoke tracking: parses `smokegrenade_detonate` events, tracks entity trajectory over 300 ticks. Grenade tracking: parses `grenade_thrown` events. Entity listing: filters for projectile entities.

- **`cmd_all(args)`** -- Calls `cmd_events`, `cmd_fields`, `cmd_track` in sequence.

- **`main()`** -- CLI with subparsers: `events`, `fields`, `track` (with `--entity-type`), `all`.

---

### 9. `tools/Goliath_Hospital.py` (1122 lines)

Comprehensive multi-department health diagnostic system v3.0. 11 specialized "departments" each check a different aspect of project health.

#### Constants

- `EXCLUDE_DIRS` (14 entries) -- Directories skipped during file walks.
- `FORBIDDEN_PATTERNS` (4 regex patterns) -- Sensitive data detection: Linux/Windows desktop paths, hardcoded passwords, hardcoded API keys.
- `MOCK_DATA_INDICATORS` (17 strings) -- Indicators of mock/fake data in production code.
- `DEPRECATED_PATTERNS` (2 regex/description tuples) -- Debug prints, backup file presence.
- `CRITICAL_MODULES` (18 relative paths) -- Critical modules that must exist.
- `IMPORT_CHAINS` (24 tuples) -- `(name, module_path, attribute)` for import chain verification.
- `ANALYSIS_FACTORIES` (11 factory names) -- Factory functions for analysis engines.
- `CONTROL_MODULES` (4 filenames) -- Control layer modules.
- `REQUIRED_MAPS` (7 map names) -- Required CS2 maps.
- `_ONCOLOGY_LENGTH_EXCLUSIONS` (9 paths) -- Files excluded from long-function checks.
- `DEPARTMENT_NAMES` (11 names) -- ER, RADIOLOGY, PATHOLOGY, CARDIOLOGY, NEUROLOGY, ONCOLOGY, PEDIATRICS, ICU, PHARMACY, TOOL_CLINIC, ENDOCRINOLOGY.

#### Class: `GoliathHospital(BaseValidator)`

- **`_walk_py_files(root)` [static]** -- Generator yielding `.py` files, filtering `EXCLUDE_DIRS`.
- **`_run_with_timeout(func, timeout_sec=15, label)`** -- Runs function in daemon thread with timeout.

**11 Departments:**

1. **ER (Emergency Room)** -- Syntax check via `ast.parse()`, forbidden pattern scan, namespace collision check (bare imports without `Programma_CS2_RENAN` prefix).
2. **Radiology (Asset Integrity)** -- PHOTO_GUI directory, 3 theme directories (>= 5 assets each), map radar files for 7 maps, models directory, layout.kv.
3. **Pathology (Data Quality)** -- Mock data indicator scan, DB data quality check for test/mock/MCIV player names.
4. **Cardiology (Core Health)** -- 18 critical modules, DB connection, config loading, settings.json validity, TemporalBaselineDecay weight, 11 analysis factory functions, ResourceManager, observability, 4 control layer modules.
5. **Neurology (ML/AI)** -- Imports and instantiates `UltimateMLDebugger`.
6. **Oncology (Tech Debt)** -- Deprecated pattern scan, commented-out code blocks (5+ consecutive lines), long functions (>100 lines via AST).
7. **Pediatrics (Recent Files)** -- Counts files modified within 1 day and 7 days.
8. **ICU (Integration)** -- 24 import chain tests, CoachingService instantiation, FeatureExtractor + DB integration.
9. **Pharmacy (Dependencies)** -- 5 critical deps (torch, sqlmodel, numpy, pandas, sklearn), 4 optional deps, requirements.txt.
10. **Tool Clinic** -- Syntax check, `__main__` guard, module docstring for all tool files.
11. **Endocrinology (System Integration)** -- Entry point files, Alembic migration chain, JSON config validation, headless_validator.py.

---

### 10. `tools/migrate_hltv_schema_2026_05.py` (160 lines)

Idempotent one-off migration script to extend `hltv_metadata.db` schema. Creates 4 new tables (`ProEvent`, `ProTournament`, `ProHead2Head`, `ProMapRecord`) without touching existing schemas.

#### Functions

- **`_hltv_engine()`** -- Returns HLTV DB engine.
- **`_existing_tables(engine) -> set[str]`** -- Returns set of table names via SQLAlchemy inspector.
- **`main() -> int`** -- Acquires `hltv_schema_migration` lock. Calls `SQLModel.metadata.create_all(engine, tables=new_table_objects, checkfirst=True)`. Includes separation guard: verifies 17 main-DB tables did NOT leak into HLTV DB. Returns 0 (success), 2 (missing tables), 3 (separation violated).

---

### 11. `tools/project_snapshot.py` (438 lines)

Compact project state snapshot producing all key facts in under 60 lines of output.

#### Constants

- `CRITICAL_DEPS` (8 packages) -- sqlmodel, kivymd, demoparser2, ncps, numpy, psutil, scikit-learn, torch.
- `KEY_TABLES` (5 tables) -- playermatchstats, roundstats, coachinginsight, coachingexperience, playerprofile.

#### Functions

- **`collect_git()`** -- Branch, modified/untracked counts, last commit, dirty flag. Uses `subprocess` with 10s timeout.
- **`collect_runtime()`** -- Python version, platform, torch version, CUDA device.
- **`collect_db()`** -- Connectivity, WAL mode, table row counts, ingestion status, coach state.
- **`collect_checkpoints()`** -- Scans for `.pt`/`.pth` files. Returns name, MB, age_days.
- **`collect_manifest()`** -- Reads `core/integrity_manifest.json`, compares hashes, reports drift.
- **`collect_deps()`** -- Uses `importlib.metadata.version()` for each critical dep.
- **`collect_config()`** -- METADATA_DIM, DATABASE_URL, match_db counts.
- **`format_compact(data)`** -- Multi-section report.
- **`main()`** -- CLI with `--json`, `--quiet`.

---

### 12. `tools/register_orphan_matches.py` (411 lines)

Registration-only pass for orphan `match_*.db` files. Walks per-match SQLite databases and creates `PlayerMatchStats` rows without re-parsing the `.dem` source file.

#### Constants

- `MIN_NONZERO_FIELDS = 1` -- Threshold for filtering noise rows.
- `DATA_QUALITY_REGISTERED = "registered_only"` -- Quality marker.
- `REQUIRED_TABLES = {"match_metadata", "matchtickstate"}` -- Required tables in each match DB.

#### Dataclasses

- **`MatchSummary`** (frozen) -- Fields: `demo_name`, `map_name`, `round_count`, `match_date`, `is_pro_match`.
- **`PlayerAggregate`** (frozen) -- Fields: `player_name`, `total_kills`, `total_deaths`, `total_damage`, `total_headshots`, `rounds_played`. Property `is_noise -> bool`: True if fewer than `MIN_NONZERO_FIELDS` stats are nonzero.

#### Functions

- **`_build_arg_parser()`** -- Arguments: `--match-data-dir`, `--commit`, `--force`, `--limit`, `--verbose`.
- **`_resolve_match_data_dir(cli_dir)`** -- Falls back to `get_setting("PRO_DEMO_PATH")`.
- **`_iter_match_files(root, limit)`** -- Globs `match_*.db`, sorted, with limit.
- **`_load_match_summary(con, src)`** -- Reads `match_metadata`, falls back to `MAX(round_number)` and file mtime.
- **`_player_aggregates(con)`** -- Nested SQL query: inner gets per-round MAX of cumulative counters, outer sums across rounds per player.
- **`_build_player_match_stats(summary, agg)`** -- Creates `PlayerMatchStats` with computed avg_kills, avg_deaths, avg_adr, avg_hs, kd_ratio.
- **`_existing_data_quality(session, demo_name, player_name)`** -- Queries existing data_quality.
- **`main(argv)`** -- Iterates match files, validates tables, aggregates, UPSERTs. Tracks 6 statistics: seen, inserted, skipped_complete, skipped_noise, failed.

---

### 13. `tools/seed_hltv_top20.py` (1454 lines)

Seeds the HLTV database tables with top-20 CS2 teams, their rosters (100 players), and stat cards. Data sourced from HLTV.org (March 2026).

#### Constants

- **`TEAMS`** (20 entries) -- Dict with `hltv_id`, `name`, `world_rank`. Teams: Vitality (#1) through Aurora (#20).
- **`PLAYERS`** (100 entries) -- Dict with `hltv_id`, `nickname`, `real_name`, `country`, `team_id`. 5 per team.
- **`PLAYER_STATS`** (40 entries) -- Dict keyed by `hltv_id` with `rating_2_0`, `kpr`, `dpr`, `adr`, `kast`, `impact`, `headshot_pct`, `maps_played`, `opening_kill_ratio`, `opening_duel_win_pct`. Stats period: 2025 full year.
- **`DEFAULT_STATS`** -- Baseline stats for unlisted players.
- **`_TOP20_MAP`** (19 entries) -- Maps `hltv_id` to HLTV top-20 rank.
- **`_TEAM_RANK_MAP`** -- Maps team `hltv_id` to `world_rank`.

#### Functions

- **`main()`** -- 3 upsert phases (teams, players, stat cards). Normalizes percentage fields from percentage to ratio when value > 1.0 (V-2 FIX). Creates `detailed_stats_json` with source, period, hltv_top20_rank, team_world_rank.
- **`_get_top20_rank(hltv_id)`** -- Looks up `_TOP20_MAP`.
- **`_get_team_rank(team_hltv_id)`** -- Looks up `_TEAM_RANK_MAP`.

---

### 14. `tools/sync_integrity_manifest.py` (165 lines)

Pre-commit hook that regenerates or verifies `core/integrity_manifest.json` containing SHA-256 hashes of all production `.py` files.

#### Constants

- `MANIFEST_PATH` -- `SOURCE_ROOT / "core" / "integrity_manifest.json"`.
- `_HASH_EXCLUDES` -- Set of 6 excluded directories: tools, tests, __pycache__, PHOTO_GUI, data, models.

#### Functions

- **`_compute_hashes() -> dict`** -- Walks `SOURCE_ROOT` for `*.py` files, normalizes CRLF to LF, computes SHA-256 hex digest.
- **`_load_manifest() -> dict`** -- Loads existing manifest.
- **`_write_manifest(hashes)`** -- Writes manifest JSON with version "2.0", sorted keys, trailing newline.

#### Class: `ManifestValidator(BaseValidator)`

- **`_verify_mode()`** -- Computes fresh hashes, diffs against manifest. Reports changed/new/removed files.
- **`_regenerate_mode()`** -- Computes hashes, writes manifest, reports file count.

---

### 15. `tools/ui_diagnostic.py` (375 lines)

Headless UI validation tool. Merges: `gui_health_check`, `Omni_UI_Diagnostic`, `coordinate_audit`, `verify_setpos`. Covers 6 sections.

#### Class: `UIDiagnostic(BaseValidator)`

1. **Resources** -- layout.kv existence, PHOTO_GUI count, DB connectivity.
2. **Localization** -- TRANSLATIONS loaded, key parity across languages.
3. **Assets** -- 3 theme directories, map radar images (>= 3), font files.
4. **KV Validation** -- 3-space indentation check, widget ID uniqueness, screen class completeness.
5. **Qt Frontend** -- `apps/qt_app` directory, screen modules (>= 10, AST syntax check), QSS themes (>= 1), ViewModels (>= 5), app.py entry point.
6. **Spatial Coordinates** -- SPATIAL_REGISTRY non-empty, normalization roundtrip, pixel bidirectionality for dust2/mirage/inferno.

---

### 16. `tools/Ultimate_ML_Coach_Debugger.py` (519 lines)

Neural belief state and decision logic falsification tool with 9 audit phases.

#### Constants

- `_BELIEF_STABILITY_VARIANCE_THRESHOLD` -- from `get_setting("ML_BELIEF_VARIANCE_THRESHOLD", 0.5)`.
- `_DEAD_NEURON_THRESHOLD = 0.001` -- Weight magnitude below which neurons are "dead".
- `_OVERFITTING_DIVERGENCE = 0.20` -- val_loss > train_loss * (1 + threshold).
- `_OVERFITTING_CONSECUTIVE_EPOCHS = 5`.

#### Class: `UltimateMLDebugger(BaseValidator)`

9 audit phases:

1. **Data Fidelity** -- Queries `PlayerTickState` and `PlayerMatchStats` counts for player.
2. **Belief Stability** -- Loads tick states, creates model, runs forward pass, checks variance against threshold.
3. **Decision Traceability** -- Queries `CoachingInsight`, checks ratio with non-None `demo_name` (>= 80%).
4. **Model Zoo** -- Tests 6 model types (LEGACY, JEPA, VL_JEPA, ROLE_HEAD, RAP, RAP_LITE). Forward-pass smoke test.
5. **Dimensional Consistency** -- Checks INPUT_DIM == METADATA_DIM, TRAINING_FEATURES count, OUTPUT_DIM == 10.
6. **Data Quality Gate** -- Runs `run_pre_training_quality_check` in daemon thread with 15s timeout.
7. **Weight Health** -- Loads checkpoints, counts NaN/Inf params and dead neurons.
8. **Training Convergence** -- Reads `training_progress.json`, checks for overfitting streaks and final loss finiteness.
9. **Maturity State** -- Uses `MaturityObservatory` to classify state, checks not "doubt" or "crisis".

---

### 17. `tools/user_tools.py` (316 lines)

Consolidated interactive utilities. Provides 5 subcommands.

#### Functions

- **`cmd_personalize(args)`** -- Prompts for CS2 player name, Steam ID, Steam Web API Key, FACEIT API Key. Keys printed as `***` (no partial credential exposure).
- **`cmd_customize(args)`** -- GUI preferences: language (en/pt/it), theme, font type.
- **`cmd_manual_entry(args)`** -- Manual HLTV pro player stats entry loop. Creates `PlayerMatchStats` with `is_pro=True`.
- **`cmd_weights(args)`** -- ML feature weight overrides: view, set, reset.
- **`cmd_heartbeat(args)`** -- System health: ingestion queue, match stats count, coach state, system resources (psutil), HLTV daemon PID check.
- **`main()`** -- CLI with 5 subcommands.

---

## Part II: Top-Level Tools

### `tools/headless_validator.py` (2897 lines)

The **mandatory post-task regression guard** (`python tools/headless_validator.py`). Must exit 0 for any task to be considered complete. Runs 26 phases of validation in ~15-20 seconds without GUI.

The file is **not importable** -- it raises `ImportError` if `__name__ != "__main__"`. Runs as a sequential script that accumulates `CheckResult` dataclasses into `_results: List[CheckResult]`.

#### Helper Functions

- **`check(phase, name, fn)`** -- Runs `fn()`, records pass/fail.
- **`warn(phase, name, fn)`** -- Same as `check()` but records failures as warnings (non-blocking).
- **`try_import(module_path) -> callable`** -- Returns a callable that imports a module.
- **`verify_contract(mod_path, cls_name, methods, attrs)`** -- Generic contract verifier.
- **`_get_production_files() -> List[Path]`** -- Cached list of production `.py` files.
- **`_verify_json_file(label, rel_path, required_keys, min_entries)`** -- Generic JSON config validator.

#### Phase Summary (26 phases)

| Phase | Name | Checks |
|-------|------|--------|
| 1 | Environment | Project root exists, 26 critical directories exist |
| 2 | Core Imports | 11 core modules + 4 Kivy-dependent modules |
| 3 | Backend Storage | 9 storage modules |
| 3b | Backend Processing | 17 processing modules |
| 3c | Backend Neural Networks | 30+ NN modules |
| 3d | Backend Analysis | 10 analysis modules |
| 3e | Backend Coaching | 6 coaching modules |
| 3f | Backend Services | 8 service modules |
| 3g | Backend Knowledge | 5 knowledge modules |
| 3h | Backend Control | 4 control modules |
| 3i | Backend Data Sources | 14 data source modules |
| 3j | Backend Ingestion & Onboarding | 5 modules |
| 3k | Ingestion Pipelines | 6 modules |
| 3l | Reporting & Observability | 2 modules |
| 4 | Database Schema | 20 expected tables, CoachState CRUD |
| 5 | Config & Data | map_config.json, METADATA_DIM==25, feature alignment |
| 6 | ML Smoke | JEPA/ModelFactory/NeuralRoleHead |
| 6b-6f | Extended ML | Baseline, DemoFormatAdapter, GPU, Training, Coaching |
| 7 | UI Components | Qt app + 13 screen modules |
| 8 | Cross-Platform | pathlib paths, no hardcoded drive letters |
| 9 | Cross-Module Contracts | 13 contract checks |
| 10 | Deep ML Invariants | 11 checks including OUTPUT_DIM, JEPA shapes, EMA cycle |
| 11 | Database Model Integrity | 8 checks |
| 12 | Code Quality | No bare except, no eval/exec, no hardcoded secrets |
| 13 | Package Structure | __init__.py completeness, JSON configs, Qt structure |
| 14 | Feature Pipeline | extract shape==(25,), feature names, NaN guards |
| 15 | Dependencies | torch/sqlmodel/numpy ops, SQLite WAL |
| 16 | RAP Coach | Full forward pass, sparsity loss, RAP_POSITION_SCALE |
| 17 | Belief Model & Analysis | BeliefState, DeathProbability, GameTree, SpatialEngine |
| 18 | MLControlContext | Stop signal, pause/resume, throttle |
| 20 | Shared Utilities | round_utils.infer_round_phase() |
| 21 | Integrity & Security | Manifest hash sampling, no unsafe torch.load, RASP guard |
| 22 | Configuration | map_config per-map schema, requirements.txt |
| 23 | Advanced Code Quality | No functions >200 lines, no circular imports, type hints >=50% |
| 24 | Qt Frontend Imports | Core Qt modules, 14 screens, 7 viewmodels |
| 25 | Design Token Freshness | Python/JSON/TypeScript sync |
| 26 | Web Marquee Scaffold | tactical-viewer, match-detail, coach-chat |

Exit codes: 0 = PASS (warnings allowed), 1 = FAIL.

---

## Part III: Test Infrastructure

### `tests/conftest.py` (650 lines)

Central test configuration file.

#### Venv Guard

Checks `sys.prefix != sys.base_prefix`; bypassed by `CI` or `GITHUB_ACTIONS` environment variables.

#### pytest Hooks

- **`pytest_configure(config)`** -- Registers `"integration"` marker.
- **`pytest_collection_modifyitems(config, items)`** -- Skips `@pytest.mark.integration` unless `CS2_INTEGRATION_TESTS=1`.

#### Fixtures (14 total)

1. **`in_memory_db`** (session scope) -- In-memory SQLite engine, `SQLModel.metadata.create_all()`.
2. **`seeded_db_session`** (function scope) -- 6 PlayerMatchStats (s1mple, ZywOo, dev1ce, NiKo, electronic, b1t), 12 RoundStats, 1 PlayerProfile.
3. **`seeded_player_stats`** -- All PlayerMatchStats from seeded session.
4. **`seeded_round_stats`** -- All RoundStats from seeded session.
5. **`real_db_session`** -- File-backed SQLite in `tmp_path`.
6. **`real_player_stats`** -- From real_db_session.
7. **`real_round_stats`** -- From real_db_session.
8. **`torch_no_grad`** -- Wraps test in `torch.no_grad()`.
9. **`rap_model`** -- `RAPCoachModel(metadata_dim=METADATA_DIM, output_dim=10)` in eval mode.
10. **`rap_inputs`** -- Dict with view/map/motion (2,3,64,64), metadata (2,5,METADATA_DIM), skill_vec (2,8).
11. **`mock_db_manager`** -- InMemoryDBManager with get_session/get/create_db_and_tables/upsert.
12. **`isolated_settings`** (autouse=False) -- Monkeypatches `_settings` in config module.
13. **`seeded_hltv_session`** -- 2 ProTeams, 4 ProPlayers, 4 ProPlayerStatCards.
14. **`match_data_dir`** -- Temp match_data directory with minimal `match_1.db`.

### `tests/automated_suite/__init__.py` (1 line)

Package marker: `# Automated Test Suite for CS2 Analyzer`.

---

## Part IV: Test Files -- Detailed Coverage

### 4.1 Automated Test Suite

#### `automated_suite/test_smoke.py` (85 lines, 4 tests)

- **`test_imports()`** -- Verifies pandas, torch, TeacherRefinementNN (has callable forward), init_database, i18n (get_text, set_language).
- **`test_database_init()`** -- Calls `init_database()`, asserts manager not None, queries sqlite_master.
- **`test_config_loading()`** -- Asserts METADATA_DIM == 25, get_setting returns str.
- **`test_model_factory_types()`** -- Asserts ModelFactory has get_model, get_checkpoint_name, and 5 type constants.

#### `automated_suite/test_unit.py` (91 lines, 5 tests)

- **`test_extract_match_stats_logic()`** -- 3-row DataFrame, asserts avg_kills==1.0, kd_ratio==1.5, accuracy==30/90.
- **`test_extract_match_stats_single_round()`** -- Single row, asserts avg_kills==3.0, kd_ratio==3.0.
- **`test_localization_switching()`** -- EN/PT/IT: "dashboard" translations.
- **`test_localization_missing_key_returns_key()`** -- Unknown key returns itself (LOC-02 fallback).
- **`test_localization_all_supported_languages()`** -- 3 languages produce non-empty strings.

#### `automated_suite/test_functional.py` (24 lines, 1 test)

- **`test_config_persistence(isolated_settings)`** -- Save then load user setting roundtrip.

#### `automated_suite/test_e2e.py` (71 lines, 1 test, integration)

- **`test_e2e_user_journey(isolated_settings)`** -- Full lifecycle: init_database, save player name, skip-gate (needs >= 5 real records), run training cycle, verify coach state.

#### `automated_suite/test_system_regression.py` (56 lines, 2 tests)

- **`test_database_schema_regression()`** -- Constructs PlayerMatchStats with 16 fields, asserts dataset_split and accuracy attributes.
- **`test_full_system_ingestion_query()`** (integration) -- Skip-gate, queries real data, asserts non-None fields.

---

### 4.2 Analysis Engine Tests

#### `test_analysis_engines.py` (248 lines, 4 classes, 18 tests)

- **`TestWinProbabilityPredictor`** (7 tests) -- Initialization, even match [0.3,0.7], man advantage >0.80, economy advantage ordering, zero players == 0.0, all enemies dead == 1.0, dict prediction.
- **`TestRoleClassifier`** (4 tests) -- Initialization, cold start returns FLEX, role profiles exist for all 5 roles, coaching tips.
- **`TestUtilityAnalyzer`** (3 tests) -- PRO_BASELINES non-empty, overall_score [0,1], low utility recommendations.
- **`TestEconomyOptimizer`** (5 tests) -- WEAPON_COSTS non-empty, pistol round (confidence >0.9), full buy, eco, force buy decisions.

#### `test_analysis_engines_extended.py` (428 lines, 10 classes, 29 tests)

- **`TestMomentumState`** (3 tests) -- Default neutral, tilted threshold (<0.80), hot threshold (>1.25).
- **`TestMomentumTracker`** (7 tests) -- Win/loss streaks, clamped multiplier (MULTIPLIER_MAX/MIN), half switch reset (MR12), streak transitions, history accumulation.
- **`TestFromRoundStats`** (2 tests) -- Round stats list conversion, sorted input.
- **`TestPredictPerformanceAdjustment`** (1 test) -- Multiplier 1.2 with base 1.0 -> adjusted ~1.2.
- **`TestBeliefState`** (3 tests) -- No enemies -> 0.0, visible enemies, decay with age.
- **`TestDeathProbabilityEstimator`** (7 tests) -- Full HP prior, critical HP higher probability, bounded [0,1], is_high_risk, hp_to_bracket, calibration with data, empty calibration.
- **`TestAdaptiveBeliefCalibrator`** (3 tests) -- Insufficient samples, missing weapon column, insufficient threat decay.
- **`TestEntropyAnalyzer`** (5 tests) -- Empty positions, single position, uniform max entropy, utility throw analysis, rank utility usage.
- **`TestGameState`** (2 tests) -- Defaults, custom values.
- **`TestWinProbabilityNN`** (3 tests) -- Forward shape (3,12)->(3,1), bounded outputs, gradient flow.

#### `test_analysis_gaps.py` (562 lines, 12 classes, 38 tests)

- **`TestRoleClassifierColdStart`** (1 test) -- Cold start returns FLEX/0.0.
- **`TestRoleClassifierWarm`** (6 tests) -- Classify returns tuple(3), AWPer detection, entry fragger, lurker, score dict, scores normalized to 1.0.
- **`TestRoleClassifierScoring`** (6 tests) -- Score functions for AWPer, entry, support (utility bonus), IGL (balanced KD), lurker.
- **`TestConsensus`** (3 tests) -- Agree boosts confidence, neural wins when higher, heuristic wins tie.
- **`TestClassifyTeam`** (2 tests) -- Team dict length, no duplicate AWPer.
- **`TestAuditTeamBalance`** (6 tests) -- Balanced team, multiple AWPers, missing entry/support, all same role CRITICAL, multiple lurkers.
- **`TestRoleProfiles`** (2 tests) -- All roles have profiles, fallback tips exist.
- **`TestDeceptionMetrics`** (2 tests) -- Defaults, custom values.
- **`TestDeceptionAnalyzer`** (12 tests) -- Empty round, flash baits (no events, no flashes, all ineffective, all effective), rotation feints (no positions, few samples, straight line), sound deception (no crouching, all crouching, no crouching), composite bounded.
- **`TestDeceptionCompareToBaseline`** (4 tests) -- Above/below/aligns baseline, rotation feint feedback.
- **`TestDeceptionFactory`** (2 tests) -- Factory returns non-None, 6 constants verified (weights sum to 1.0).

#### `test_analysis_orchestrator.py` (186 lines, 2 classes, 8 tests)

- **`TestAnalysisOrchestrator`** (7 tests) -- Instantiation (6 sub-analyzers), factory function, momentum tilt detection (7 losses), hot streak (7 wins), empty data, game states with strategy insights, insight structure validation.
- **`TestMatchAnalysis`** (1 test) -- all_insights aggregates match + round insights.

---

### 4.3 Belief Model and Game Theory Tests

#### `test_belief_model_extended.py` (368 lines, 7 classes, 7 tests)

- **`TestExtractDeathEventsEmptyDB`** (1 test) -- Monkeypatched empty DB returns empty DataFrame with columns ["health", "died"].
- **`TestAutoCalibratePartialColumns`** (1 test) -- 200-row DataFrame with only health+died, hp_priors non-empty, weapon_lethality empty.
- **`TestCalibrateInsufficientSamples`** (1 test) -- 20 rows (below MIN_CALIBRATION_SAMPLES=30), _calibrated False, priors match _DEFAULT_PRIORS.
- **`TestWeaponLethalityBounded`** (1 test) -- 200-row DataFrame with weapon_class, all multipliers in [0.1, 3.0].
- **`TestThreatDecayNanGuard`** (1 test) -- Monkeypatched np.polyfit returns NaN -> calibrate_threat_decay returns None.
- **`TestGetDeathEstimatorSingleton`** (1 test) -- Thread-safe singleton: 2 threads via Barrier, both get same object.
- **`TestDeathEstimatorEstimateBounded`** (1 test) -- 6 extreme cases (max threat, min threat, zero HP, unknown weapon, negative HP, very large HP), all results in [0.0, 1.0].

#### `test_blind_spots_extended.py` (132 lines, 1 class, 5 tests)

- **`TestBlindSpotDetectorExtended`** -- Instantiation (detect + generate_training_plan), empty rounds -> empty list, empty spots -> "No strategic blind spots", multiple spots training plan, BlindSpot dataclass fields (priority = frequency * impact_rating).

#### `test_game_theory.py` (979 lines, 12 classes, 58 tests)

- **`TestBeliefModel`** (6 tests) -- Initialization, update, threat_level bounds, reset, position_probability, multiple updates.
- **`TestDeceptionAnalyzer`** (5 tests) -- Initialization, analyze_round, deception_index range, fake_execute, no data.
- **`TestMomentumTracker`** (5 tests) -- Initialization, record_round, momentum_score bounds, streak detection, reset.
- **`TestEntropyAnalyzer`** (5 tests) -- Initialization, analyze_positions, non-negative, uniform vs clustered, empty.
- **`TestExpectiminimaxSearch`** (6 tests) -- Initialization, evaluate, depth limiting, pruning, opponent model, action ordering.
- **`TestBlindSpots`** (5 tests) -- Initialization, detect, spot fields, multiple kills, empty data.
- **`TestEngagementRange`** (5 tests) -- Initialization, compute_profile, range classification, empty data, extreme distances.
- **`TestNamedPositions`** (4 tests) -- Position lookup, nearest_position, unknown map, custom positions.
- **`TestFactoryFunctions`** (4 tests) -- create_belief_model, create_deception_analyzer, create_momentum_tracker, create_entropy_analyzer.
- Plus 3 classes for parametrized edge cases.

#### `test_game_tree.py` (575 lines, 14 classes, ~60 tests)

TestOpponentModel, TestGameNode, TestExpectiminimax, TestApplyAction, TestEvaluate, TestBestAction, TestFactory -- covering state transitions, alpha-beta pruning, position scoring, health weighting, equipment value, optimal action selection.

---

### 4.4 Coaching and Dialogue Tests

#### `test_coaching_dialogue.py` (150 lines, 4 classes, 13 tests)

- **`TestFormatCoperMessage`** (5 tests) -- Basic message, pro references, no pro references, baseline note, zero confidence.
- **`TestBaselineContextNote`** (4 tests) -- Empty stats, empty baseline, positioning focus, unknown focus defaults to rating.
- **`TestCoachingServiceHealthRange`** (3 tests) -- Full (100,80), damaged (79,40), critical (39,1).
- **`TestCoachingServiceInferRoundPhase`** (1 test) -- Delegates to round_utils: 800->"pistol", 5000->"full_buy".

#### `test_coaching_dialogue_tutor_mode.py` (72 lines, 1 class, 11 tests)

- **`TestThirdPersonTransform`** -- Regression tests for CHAT-02 third-person tutor mode. Tests: "You are" -> "They are", possessive "Your" -> "Their", "You were" -> "They were", mixed case, midsentence lowercase, no pronouns with attribute=True, no double prefix, attribute=False strips prefix, preserves stat numbers/percentages, handles empty string, word boundary check for "your" substrings.

#### `test_coaching_engines.py` (552 lines, 6 classes, 54 tests)

- **`TestExplanationGenerator`** (14 tests) -- Silence threshold (0.1 < 0.2 -> ""), negative/positive mechanics, positioning, utility with context, timing, decision, unknown category, low skill level simplification, severity classification (High/Medium/Low). Constants: SILENCE_THRESHOLD==0.2, SEVERITY_HIGH_BOUNDARY==1.5, SEVERITY_MEDIUM_BOUNDARY==0.8.
- **`TestPlayerCardAssimilator`** (16 tests) -- Valid/invalid/None JSON init, coach baseline keys/values, zero DPR kd_ratio, HS ratio extraction, map detailed metrics (valid/invalid), archetypes (Star Fragger/Support Anchor/Sniper Specialist/All-Rounder), factory function.
- **`TestTokenResolverHelpers`** (7 tests) -- Token dict structure (identity, core_metrics, tactical_baselines, granular_data, metadata), identity fields, malformed JSON, compare_performance_to_token, underperforming detection.
- **`TestNNRefinement`** (4 tests) -- Basic refinement (weighted_z 1.0 -> 1.5), no matching adjustment, multiple corrections, preserves other fields.
- **`TestCorrectionEngine`** (7 tests) -- Feature importance default (avg_kast -> 1.5), unknown -> 1.0, basic corrections (max 3), sorted by importance, confidence scaling (150 < 300 rounds), tuple input, nn adjustments. Constant: CONFIDENCE_ROUNDS_CEILING==300.
- **`TestLongitudinalEngine`** (7 tests) -- Regression insight, improvement insight, low confidence filtered, stability warning upgrades severity, max 3 insights, empty trends, zero slope.

#### `test_coaching_service_contracts.py` (347 lines, 5 classes, 14 tests)

- **`TestCoachingModeSelection`** (3 tests) -- COPER precedence, hybrid fallback, traditional fallback.
- **`TestHealthRangeClassification`** (3 tests) -- Full/damaged/critical.
- **`TestCoperTickDataValidation`** (3 tests) -- Non-dict tick_data safety (Bug #8), empty dict, minimal valid tick_data.
- **`TestBaselineContextNote`** (4 tests) -- Empty stats/baseline, valid comparison "below"/"above".
- **`TestSingletonFactory`** (1 test) -- Same instance returned twice.

#### `test_coaching_service_fallback.py` (293 lines, 3 classes, 11 tests)

- **`TestModeSelection`** (6 tests) -- Traditional when all flags off, traditional+RAG enhancement, hybrid over traditional, COPER over hybrid, COPER falls to hybrid without tick_data, COPER falls to traditional without map/ticks.
- **`TestFallbackChain`** (2 tests) -- COPER exception falls to hybrid, COPER exception falls to traditional when hybrid off.
- **`TestArchitecturalDocumentation`** (3 tests) -- Class docstring contains "COPER"/"Hybrid"/"Traditional"/"Fallback", method docstring, singleton factory.

#### `test_coaching_service_flows.py` (617 lines, 6 classes, 22 tests)

- **`TestFormatCoperMessage`** (4 tests) -- Narrative, pro references, baseline note, zero confidence.
- **`TestTraditionalCoachin`** (2 tests) -- Corrections saved to DB, empty deviations -> generic fallback insight.
- **`TestCoperFallbackChain`** (2 tests) -- COPER failure falls back to traditional, non-dict tick_data no crash.
- **`TestGetLatestInsights`** (4 tests) -- Empty, correct player filter, limit respected, ordered by created_at desc.
- **`TestSaveCorrections`** (4 tests) -- Basic correction severity "High", RAG correction severity "Info", severity "Medium" for small z, severity "High" for large z.
- **`TestLongitudinalCoaching`** (2 tests) -- Not enough history, enough history.
- **`TestBaselineContextNoteEdgeCases`** (4 tests) -- Scalar baseline, missing key, zero mean, aim focus.

#### `test_coach_manager_flows.py` (806 lines, 12 classes, 54 tests)

- **`TestMaturityGate`** (5 tests) -- No CoachState, below threshold, at threshold, above threshold, null total_matches.
- **`TestMaturityTier`** (5 tests) -- CALIBRATING (10), LEARNING (100), MATURE (300), boundary tests.
- **`TestConfidenceMultiplier`** (3 tests) -- 0.5/0.8/1.0 for calibrating/learning/mature.
- **`TestIncrementMaturityCounter`** (3 tests) -- Creates if missing, increments existing, multiple increments.
- **`TestDatasetSplits`** (6 tests) -- Empty DB, 10-match split (7/1/2), temporal order, pro/user independence, single match -> test, two matches -> [train, test].
- **`TestCalculateDeltas`** (4 tests) -- Zero delta, negative delta, clipped [-1,1], output length.
- **`TestPrepareTensorsFlow`** (4 tests) -- Output shapes, float32, no NaN, y clipped.
- **`TestProBaselineVector`** (4 tests) -- Correct shape, DB baseline, defaults for missing, scalar baseline.
- **`TestCheckPrerequisites`** (5 tests) -- Ready with pros, not ready without data, gathering partial, user demos insufficient, exception returns false.
- **`TestGetUserBaselineVector`** (2 tests) -- Fallback to pro, mean of user data.
- **`TestGetSkillRadarData`** (3 tests) -- Calibrating, mature (values [-100,100]), error.
- **`TestModuleLevelFunctions`** (6 tests) -- _extract_feature_vector, missing key default, _calculate_pro_mean, _apply_dynamic_window_targets (with/without outcomes, strategy clamped).
- **`TestRunFullCycleGuards`** (1 test) -- Skips when prerequisites fail.

#### `test_coach_manager_tensors.py` (243 lines, 4 classes, 14 tests)

- **`TestFeatureListIntegrity`** (5 tests) -- TRAINING_FEATURES count, MATCH_AGGREGATE_FEATURES count, no duplicates, TARGET_INDICES bounds.
- **`TestPrepareTensorsNoneHandling`** (4 tests) -- Bug #4 exposure: None in dict not replaced by default, None causes NaN in numpy. Feature vector dimensions.
- **`TestDemoTiersAndConfidence`** (4 tests) -- Contiguous boundaries, valid multipliers, MATURE full confidence, CALIBRATING lowest.
- **`TestProBaselineVector`** (1 test) -- Defaults cover all 25 MATCH_AGGREGATE_FEATURES.

---

### 4.5 Configuration and Infrastructure Tests

#### `test_config_extended.py` (190 lines, 5 classes, 20 tests)

- **`TestPaths`** (5 tests) -- stabilize_paths returns string, adds to sys.path, get_base_dir, parent is Programma, get_resource_path.
- **`TestMaskSecret`** (4 tests) -- Short/long/exactly-8/None inputs.
- **`TestSettings`** (5 tests) -- Existing/default/None settings, get_all returns dict, returns copy.
- **`TestSaveUserSetting`** (1 test) -- Save and read roundtrip via tmp_path.
- **`TestConstants`** (5 tests) -- MIN_DEMOS_FOR_COACHING==1, MAX_DEMOS_PER_MONTH==10, DATABASE_URL format, dirs exist, get_writeable_dir.

#### `test_config_resolution.py` (289 lines, 7 classes, 22 tests)

- **`TestConfigDefaults`** (5 tests) -- Default player name, demo path, coaching flags, setup_completed, 11 required keys.
- **`TestJsonOverridesDefaults`** (5 tests) -- JSON overrides, coaching flags, preserves unset, corrupted JSON fallback, non-dict JSON fallback.
- **`TestSaveUserSetting`** (4 tests) -- Creates file, preserves existing keys, updates in-memory, atomic (no .tmp files).
- **`TestGetSetting`** (3 tests) -- Saved value, default for unknown, None for unknown.
- **`TestRefreshSettings`** (1 test) -- Picks up external disk changes.
- **`TestThreadSafety`** (2 tests) -- 10 concurrent saves no corruption, 20 concurrent reads no errors.
- **`TestConstants`** (2 tests) -- MIN_DEMOS==1, MAX_DEMOS==10.

#### `test_concept_temperature_saturation.py` (148 lines, 7 standalone tests)

Tests for PRE-6 concept_temperature saturation alarm. VL-JEPA concept_temperature clamped to [0.01, 1.0], observatory detects saturation after 10 consecutive epochs.

- Healthy temperature never alarms (20 epochs at 0.5).
- Lower saturation at 0.011 alarms after 10 epochs.
- 9 epochs does not alarm.
- Upper saturation at 0.99 alarms.
- Recovery resets streak.
- Model without concept_temperature: no alarm.
- Alarm latch does not spam logs.

---

### 4.6 Data Pipeline Tests

#### `test_data_pipeline_contracts.py` (191 lines, 3 classes, 11 tests)

- **`TestFeatureExtractorObjectInput`** (3 tests) -- Object input produces valid vector, dict and object produce same result, missing attribute uses default.
- **`TestRoundPhaseEncoding`** (4 tests) -- Pistol (vec[18]==0.0), eco (0.33), force (0.66), full_buy (1.0).
- **`TestMapIdEncoding`** (4 tests) -- Same map same hash, different maps different hash, no map -> 0.0, deterministic across calls.

#### `test_coper_pathway.py` (1168 lines, 13 classes, 66 tests)

The largest test file. Comprehensive COPER pathway testing.

- **`TestExperienceContext`** (8 tests) -- Query string fields, position inclusion, health range, alive counts, hash determinism, different hashes, SHA256 verification.
- **`TestSynthesizedAdvice`** (1 test) -- All field creation.
- **`TestInferRoundPhase`** (6 tests) -- Pistol/eco/force/full_buy/missing key/non-dict.
- **`TestCorrectionEngine`** (5 tests) -- Max 3 corrections, confidence scales with rounds, tuple/list deviations, sorted by importance.
- **`TestExplainability`** (8 tests) -- Silence threshold, negative/positive narratives, severity classification, unknown category fallback, low skill simplification.
- **`TestEmbeddingSerialization`** (2 tests) -- Roundtrip, legacy JSON format.
- **`TestExperienceBankDB`** (12 tests) -- Add/add pro/retrieve brute force/map filter/confidence filter/pro examples/synthesize empty/with experiences/pro references/feedback positive/missing/count.
- **`TestExperienceBankHelpers`** (10 tests) -- Health ranges, action inference, action-to-focus mapping, cosine similarity.
- **`TestRunWithTimeout`** (4 tests) -- Success result, timeout returns None, exception reraised, args/kwargs passing.
- **`TestCoachingServiceModeSelection`** (4 tests) -- COPER enabled, traditional when disabled, missing map fallback, timeout fallback.
- **`TestCoperInsightsGuards`** (1 test) -- Non-dict tick_data rejected.
- **`TestBaselineContextNote`** (4 tests) -- Empty inputs, calculates delta, above baseline, missing metric.
- **`TestFormatCoperMessage`** (3 tests) -- Basic format, baseline note, no pro references.

#### `test_ingestion_boundary.py` (138 lines, 2 standalone tests)

HLTV module isolation from ingestion pipeline. Import isolation and state leak verification.

#### `test_ingestion_pipeline.py` (268 lines, 4 classes, 14 tests)

- **`TestDuplicateDemoCheck`** (3 tests), **`TestProfileReadiness`** (4 tests), **`TestStatSanitization`** (4 tests), **`TestCorrectionEngine`** (3 tests).

#### `test_ingestion_tickrate.py` (142 lines, 12 standalone tests)

Tick rate parsing: CS2 default (64), CS:GO legacy (128), custom rates, missing header fallback, range [16, 256].

#### `test_debug_ingestion.py` (81 lines, 1 class, 3 tests)

- **`TestExtractMatchStats`** -- Basic aggregation (avg_kills==1.5, kd_ratio==3.0), empty DataFrame, zero division safety.

---

### 4.7 Database Tests

#### `test_database_layer.py` (427 lines, 3 classes, 27 tests)

- **`TestDatabaseManager`** (8 tests) -- Create tables, get session, commit on success, rollback on error, upsert new/update, get existing/nonexistent.
- **`TestStateManager`** (12 tests) -- Default state, same id, update status (hunter/digester/teacher/global), parsing/training progress, heartbeat, error notification, add notification, unknown daemon, no state.
- **`TestStatCardAggregator`** (7 tests) -- Persist new/update player card, missing data, persist new/update team, missing team data, core stats mapping (KAST normalization 68.0 -> 0.68).

#### `test_database_wal_enforcement.py` (170 lines, 5 classes, 14 tests)

- **`TestDatabaseManagerWAL`** (5 tests) -- journal_mode==wal, synchronous==1, busy_timeout==30000, PRAGMAs on every connection, WAL file existence.
- **`TestHLTVDatabaseManagerWAL`** (3 tests) -- Same PRAGMAs for HLTV DB.
- **`TestPoolConfiguration`** (2 tests) -- pool_size==1, max_overflow==4.
- **`TestSessionManagement`** (3 tests) -- Usable session, commit persists, rollback on error.
- **`TestMatchDataManagerWAL`** (1 test) -- match_data_dir fixture WAL mode.

#### `test_db_backup.py` (200 lines, 5 classes, 11 tests, 2 skipped)

- **`TestBackupMonolith`** (2 tests, SKIPPED) -- Backup creation and SQLite validity. Skipped due to F9-04/F9-01 DB lock hang risk.
- **`TestRestoreBackup`** (3 tests) -- Valid restore, missing file, empty file.
- **`TestRotateBackups`** (3 tests) -- Prune excess (7 -> 2), no excess, empty dir.
- **`TestAlembicPreMigrationHook`** (1 test) -- _pre_migration_backup defined and called in env.py.
- **`TestBackupManagerIntegrity`** (2 tests) -- Valid integrity, corrupted file.

#### `test_db_governor_integration.py` (225 lines, 2 classes, 9 tests)

- **`TestDatabaseGovernor`** (5 tests) -- Audit storage structure, no DB anomalies, verify integrity light/full, rebuild indexes, prune match data.
- **`TestE2EPipeline`** (4 tests, skipif no RAP deps) -- Factory creates RAP model, full forward pass, skill_vec modulates output, no NaN, sparsity loss scalar.

#### `test_knowledge_graph.py` (240 lines, 1 class, 17 tests)

Node CRUD, edge creation, WAL mode, subgraph queries, disconnected nodes, bulk operations, transaction rollback.

#### `test_match_shard_schema_contract.py` (88 lines, 2 classes, 5 tests)

- **`TestTableNamePinning`** (3 tests) -- Exact table names.
- **`TestShardCreation`** (2 tests) -- Schema creation, FK validation.

#### `test_strategy_label_migration.py` (143 lines, 6 standalone tests)

Alembic migration: upgrade, downgrade, idempotency, data preservation, defaults, constraints.

---

### 4.8 Demo and Parser Tests

#### `test_dem_validator.py` (131 lines, 1 class, 7 tests)

- **`TestDEMValidator`** -- CS2 demo (PBDEMS2), CSGO demo (HL2DEMO), file not found, too small, too large, invalid magic, processing time estimation (1s/10MB), convenience function.

#### `test_demo_format_adapter.py` (253 lines, 5 classes, 16 tests)

- **`TestValidation`** (7 tests) -- Nonexistent file, empty, tiny, valid CS2, legacy CSGO (unsupported), unknown header, corruption warnings.
- **`TestFieldMapping`** (2 tests) -- Dict with >10 entries, 10 required canonical keys.
- **`TestChangelog`** (2 tests) -- Non-empty ProtoChange instances, chronological order.
- **`TestFormatVersions`** (3 tests) -- >= 2 entries, cs2_protobuf supported, csgo_legacy not supported.
- **`TestIntegration`** (4 tests) -- demo_parser imports kast, integrity delegates to adapter, CS2 accepted/legacy rejected, convenience function parity.

#### `test_demo_parser.py` (184 lines, 4 classes, 11 tests)

- **`TestParseDemoEdgeCases`** (2 tests) -- Nonexistent file returns empty DataFrame.
- **`TestParseSequentialTicksEdgeCases`** (1 test) -- Nonexistent file.
- **`TestRatingFormulas`** (6 tests) -- KD ratio, per-round averages, HLTV 2.0 rating components, final rating at baseline ~1.0, econ_rating, high performer > 1.0.
- **`TestDemoParserIntegration`** (2 tests, integration) -- Real demo parse, sequential ticks.

#### `test_grenade_thrown_extraction.py` (237 lines, 4 standalone tests)

HE grenade, flashbang, smoke, molotov throw events with position/player/tick verification.

---

### 4.9 Neural Network Tests

#### `test_jepa_model.py` (537 lines, 7 classes, 31 tests)

- **`TestJEPAEncoder`** (4) -- Output shape, latent dim, gradient flow, batch independence.
- **`TestJEPAPredictor`** (4) -- Prediction shape, context dependence, no NaN.
- **`TestJEPAModel`** (6) -- Forward pass, coaching output, selective forward, encoder freezing, target encoder update.
- **`TestVLJEPA`** (6) -- forward_vl keys, concept_probs (batch,16), coaching output, top_concepts, concept activation.
- **`TestConceptLabeler`** (5) -- label_tick (16,), values [0,1], label_batch, determinism, known patterns.
- **`TestCheckpointMigration`** (3) -- Old checkpoint, key renaming, missing keys with defaults.
- **`TestModelConfig`** (3) -- Default/custom dimensions, latent_dim propagation.

#### `test_jepa_training_pipeline.py` (636 lines, 11 classes, 40 tests)

- **`TestSelfSupervisedDataset`** (5) -- Length, __getitem__, windowing, edge cases, empty.
- **`TestContrastiveLoss`** (4) -- Computation, gradient flow, symmetry, temperature scaling.
- **`TestNegativeSampling`** (4) -- Count, no overlap, deterministic, batch handling.
- **`TestEMAMomentum`** (5) -- Decay, divergence, schedule, state_dict, apply/restore cycle.
- **`TestTargetEncoderFreezing`** (3) -- requires_grad=False, no gradient, parameter count match.
- **`TestCheckpointSaveLoad`** (4) -- Completeness, strict load, optimizer state, epoch counter.
- **`TestPretrainPhase`** (5) -- Shape, loss decreases, negative sampling, non-overlap, batch norm.
- **`TestFinetunePhase`** (4) -- Shape, frozen encoder, LR schedule, loss components.
- **`TestTwoStageProtocol`** (2) -- Pretrain-then-finetune, checkpoint loading.
- **`TestDataAugmentation`** (2) -- Noise injection, temporal jitter.
- **`TestTrainingReproducibility`** (2) -- Same seed same loss, different seeds differ.

#### `test_nn_config_reproducibility.py` (147 lines, 3 classes, 17 tests)

- **`TestGlobalSeed`** (6) -- GLOBAL_SEED==42, set_global_seed affects torch/numpy/random, deterministic ops, CUDA flag.
- **`TestConfigConstants`** (6) -- INPUT_DIM==METADATA_DIM, OUTPUT_DIM==10, HIDDEN_DIM==128, LATENT_DIM, LEARNING_RATE, BATCH_SIZE.
- **`TestReproducibility`** (5) -- Model init/forward/training determinism.

#### `test_nn_extensions.py` (385 lines, 10 classes, 35 tests)

NeuralRoleHead, ExtractRoleFeatures, NNConfig, ProPerformanceDataset, SelfSupervisedDataset, CoachNNConfig, AdvancedCoachNN, ModelManager, and helpers.

#### `test_nn_infrastructure.py` (382 lines, 4 classes, 31 tests)

- **`TestEMA`** (10) -- Construction, decay, update, apply_shadow, restore, state_dict round-trip, convergence, decay=0/1, clone in apply (NN-16).
- **`TestModelFactory`** (8) -- All types, checkpoint names, unknown raises ValueError, dimension propagation.
- **`TestPersistence`** (7) -- Save/load, strict, missing/extra keys, device mapping.
- **`TestSuperpositionLayer`** (6) -- Forward shape, gate weights, gradient flow, custom experts, sparse routing.

#### `test_nn_training.py` (191 lines, 3 classes, 17 tests)

EarlyStopping, TrainingDecision, TrainingControllerHelpers.

#### `test_moe_sparse_gate.py` (198 lines, 12 standalone tests)

Top-k routing, normalization, entropy regularization, gradient flow, expert utilization, load balancing, capacity factor, zero-expert fallback.

---

### 4.10 Training Pipeline Tests

#### `test_training_orchestrator_flows.py` (855 lines, 14 classes, 50 tests)

- **`TestResolveMapName`** (8) -- From metadata, de_ prefix, demo name pattern, case insensitive, fallback, cache, exception, all maps.
- **`TestComputeAdvantage`** (8) -- Balanced, numerical advantage/disadvantage, bomb planted T/CT, dead players, range [0,1], no players.
- **`TestClassifyTacticalRole`** (9) -- Save, CT/T default, retake, lurk, entry, aggressive, anchor, support.
- **`TestFetchBatches`** (5) -- Correct count, train/val split, epoch seed rotation, val fixed.
- **`TestPrepareTensorBatchJEPA`** (8) -- Keys, shapes, too small, short batch, exact 10, target follows context.
- **`TestRunTrainingEdgeCases`** (2) -- Abort no data, progress delegation.
- **`TestPerEpochSeedRotation`** (4) -- Same/different seeds, val stable, refetches.
- **`TestSubsampleSizeConfig`** (5) -- Default/custom train/val, custom passed.
- **`TestPatienceConfig`** (3) -- Default, custom, early stop.
- **`TestBestValLossResume`** (4) -- Restore from sidecar, no sidecar, without extra, save persists.
- **`TestEMATotalSteps`** (1) -- set_total_steps called.
- **`TestConstants`** (2) -- Advantage weights sum to 1, role indices contiguous.

#### `test_training_orchestrator_logic.py` (195 lines, 4 classes, 12 tests)

OrchestratorInit, EarlyStopping, EmptyBatchHandling, DeterministicNegativeSampling.

#### `test_training_callbacks.py` (258 lines, 5 classes, 16 tests)

TrainingCallback, CallbackRegistry, CallbackRegistryFire, CloseAll, TensorBoardCallback.

#### `test_dry_run_checkpoint_integrity.py` (93 lines, 2 standalone integration tests)

- **`test_dry_run_writes_no_checkpoint(tmp_path)`** -- Runs `run_full_training_cycle.py --dry-run` as subprocess, asserts no `.pt` files.
- **`test_real_run_writes_checkpoint(tmp_path)`** -- Runs with `--epochs 1`, asserts at least one `.pt` file.

---

### 4.11 RAP Coach Tests

#### `test_rap_coach.py` (628 lines, 9 classes, ~50 tests)

- **`TestResNetBlock`** (5) -- Identity/projection shortcut, output shapes, gradient flow.
- **`TestRAPPerception`** (4) -- dim==128, batch, no NaN, different spatial sizes.
- **`TestRAPMemory`** (4) -- Shapes, hidden passthrough, no NaN, Hopfield bypass (NN-MEM-01).
- **`TestRAPStrategy`** (4) -- Shape, gates sum to 1, custom experts, sparse top-2.
- **`TestRAPPedagogy`** (3) -- Value shape, skill vector, advantage gap.
- **`TestCausalAttributor`** (4) -- Diagnose shape, concepts, view delta, utility_need bounded.
- **`TestRAPCoachModel`** (13) -- Forward keys, shapes (advice/belief/value/gate/optimal_pos/attribution), sparsity loss, no NaN, deterministic, without skill vector, heuristic config.
- **`TestRAPCommunication`** (6) -- Low confidence suppresses, skill tiers, output is string, default skill level.
- **`TestRAPTrainer`** (7) -- Train step metrics, loss decreases, Z-penalty, weighted position loss, with/without target, scheduler.

#### `test_rap_training_dry_run.py` (245 lines, 3 classes)

- **`TestRAPOrchestratorGate`** (2) -- RAP disabled raises, enabled constructs.
- **`TestRAPDryRunSmoke`** (1, integration) -- Full dry-run smoke test.
- **`TestRAPLTCFixIsLoaded`** (2) -- Memory module importable, ODE solver shape patch.

---

### 4.12 Feature Engineering Tests

#### `test_feature_extractor_contracts.py` (270 lines, 6 classes, 18 tests)

MetadataDim (2), ExtractShape (3), FeatureRanges (4), NaNGuards (4), ConfigOverride (3), FeatureNames (2).

#### `test_features.py` (75 lines, 1 class, 3 tests)

Basic feature extraction: empty, populated, count consistency.

#### `test_metadata_dim_contract.py` (121 lines, 5 standalone tests)

METADATA_DIM==25 across vectorizer, coach_manager, nn config, feature names.

#### `test_tactical_features.py` (76 lines, 1 class, 7 tests)

UtilityAnalyzer smoke, economy phases (pistol/full_buy/eco/force_buy/half_buy/overtime).

#### `test_feature_kast_roles.py` (663 lines, 11 classes, 39 tests)

KAST Calculation (15 tests), Role Classification (12 tests), Coaching Dialogue (12 tests).

---

### 4.13 Experience Bank and Knowledge Tests

#### `test_experience_bank_db.py` (746 lines, 9 classes, 40 tests)

CRUD, embedding similarity, synthesis, feedback, temporal decay, dedup, thread safety.

#### `test_experience_bank_dedup.py` (89 lines, 1 class, 7 tests)

Hash-based dedup, similarity threshold, merge strategy, conflict resolution.

#### `test_experience_bank_logic.py` (123 lines, 2 classes, 8 tests)

ExperienceContext (5), SynthesizedAdvice (3).

#### `test_rag_knowledge.py` (290 lines, 4 classes, all integration)

KnowledgeEmbedder (3), KnowledgePopulator (2), KnowledgeRetriever (4), RAGCoaching (2).

---

### 4.14 Spatial and Map Tests

#### `test_spatial_engine.py` (63 lines, 5 standalone tests)

Coordinate transforms: dust2/mirage canonical points, pixel mapping, round-trip, unknown map.

#### `test_spatial_and_baseline.py` (125 lines, 4 classes, 9 tests)

Z-penalty (3), fuzzy nickname matching (2), outlier trimming (2), soft gate tiers (2).

#### `test_z_penalty.py` (153 lines, 3 classes, 26 tests)

Computation (10), vertical level classification (8), integration with training (8).

#### `test_map_manager.py` (105 lines, 8 standalone tests)

Path resolution, smart loading, fallback, theme variants, normalization.

---

### 4.15 Tensor Factory Tests

#### `test_tensor_factory.py` (853 lines, 17 classes, ~58 tests)

TensorConfig (4), TensorFactoryInit (2), MapTensorLegacy (7), MapTensorPOV (6), ViewTensorLegacy (6), ViewTensorPOV (3), MotionTensor (10), LegacyMotion (3), GenerateAllTensors (4), WorldToGrid (3), Normalize (3), FOVMask (3), DrawCircle (3), Singleton (3), GaussianBlur (1), ResolutionIndependence (1 parametrized: 16/32/64/128), EdgeCases (5).

---

### 4.16 Trade Kill and Round Stats Tests

#### `test_trade_kill_detector.py` (364 lines, 5 classes, ~21 tests)

TradeKillResult (6), AssignRoundNumbers (5), DetectTradeKills (12), GetPlayerTradeStats (5), Constants (1).

#### `test_trade_timing.py` (193 lines, 6 standalone tests)

Accumulate response ticks, skip zero/negative, aggregate avg, zero when no trades, multi-trade averaging, exception logging.

#### `test_round_stats_enrichment.py` (298 lines, 2 classes, 18 tests)

AggregateRoundStatsToMatch (15), EnrichFromDemoImport (3).

#### `test_round_utils.py` (310 lines, 4 classes)

InferRoundPhase (13), ExperienceContext (16), SynthesizedAdvice (2), ExperienceBankHelpers (14).

---

### 4.17 EMA, Drift, and Embedding Tests

#### `test_ema_hopfield_drift_invariants.py` (148 lines, 6 standalone tests)

- EMA restore breaks backup aliasing (NN-16).
- EMA apply_shadow breaks shadow aliasing (NN-16 original bug).
- Hopfield bypass after partial load (MEM-01).
- MoE sparse strategy outputs nonzero per sample (MOE-01).
- Tick feature drift monitor detects per-dim shift (DRIFT-01).
- Drift monitor no-ops without reference (raises RuntimeError).

#### `test_embedding_collapse_detector.py` (118 lines, 10 standalone tests)

P9-02 hard-stop guard: healthy variances (20 epochs), single collapsed epoch, two consecutive abort, recovery resets, at-threshold healthy, NaN treated as collapse, negative variance collapse, reset clears state, custom patience=3, error message diagnostic hints (InfoNCE/EMA/VICReg/data).

#### `test_drift_and_heuristics.py` (252 lines, 4 classes, 12 tests)

- **`TestDriftMonitor`** (3 tests) -- Detects drift on shifted batch, no drift on matching, report structure.
- **`TestShouldRetrain`** (3 tests) -- Triggers on 3/5 drifted, no trigger on 2/5, insufficient history.
- **`TestHeuristicConfig`** (4 tests) -- Defaults, serialization roundtrip, unknown keys ignored, load_learned_heuristics defaults.
- **`TestDifferentialHeatmap`** (2 tests) -- Static import, has generate method.

#### `test_engagement_range_extended.py` (142 lines, 2 classes, 5 tests)

- **`TestEngagementRangeAnalyzerExtended`** (4 tests) -- Instantiation (5 method attributes), same-point distance==0, 3D distance, negative coords.
- **`TestNamedPositionRegistryExtended`** (1 test) -- Empty registry, analyze empty kills.

---

### 4.18 Checkpoint and Persistence Tests

#### `test_checkpoint_normalizer_versioning.py` (172 lines, 10 standalone tests)

Sidecar creation (schema_version, metadata_dim, feature_names, heuristic_config), roundtrip save/load, metadata_dim mismatch raises StaleCheckpointError, feature_names mismatch, schema_version mismatch, missing feature_names, corrupt JSON, legacy checkpoint without sidecar (warns and loads), extra_meta roundtrip, atomicity (disk full rolls back both files).

#### `test_persistence_stale_checkpoint.py` (230 lines, 3 classes, 10 tests)

StaleCheckpointDetection (4), CorruptedFiles (3), CheckpointNormalization (3).

#### `test_model_factory_contracts.py` (226 lines, 5 classes, 18 tests)

ModelTypes (5), DimensionPropagation (4), CheckpointNames (4), UnknownType (2), TypeConstants (3).

#### `test_models.py` (75 lines, 1 class, 8 tests)

Database model defaults for PlayerMatchStats, PlayerTickState, CoachState.

---

### 4.19 Session and Lifecycle Tests

#### `test_session_engine.py` (463 lines, 8 classes, 22 tests)

ZombieTaskCleanup (3), RetrainingTrigger (4), BaselineSnapshot (3), MetaShift (3), StdinMonitor (2), plus 3 lifecycle edge case classes.

#### `test_lifecycle.py` (82 lines, 1 class, 9 tests)

AppLifecycleManager: single instance, shutdown sequence, daemon threads, state transitions, error recovery.

---

### 4.20 Deployment and Integration Tests

#### `test_deployment_readiness.py` (391 lines, 6 classes, 8 tests, heavily parametrised)

- **`TestForwardPassReliability`** (1 parametrised over 5 types) -- 100 forward passes, NaN count == 0.
- **`TestInferenceLatency`** (1 parametrised over 3 types) -- Median < budget * CI multiplier.
- **`TestBatchSizeInvariance`** (1 parametrised over 5 types) -- Batch 1 matches batch 4.
- **`TestDeterministicReproducibility`** (1 parametrised over 2 types) -- 5 runs with same seed.
- **`TestOODGracefulHandling`** (2 parametrised) -- OOD inputs no crash, NaN input graceful.
- **`TestDeploymentVerdict`** (2 tests) -- Pass rate >= 75%, NaN ratio <= 10%.

#### `test_dimension_chain_integration.py` (125 lines, 1 class, 9 tests)

METADATA_DIM==INPUT_DIM, ==25, OUTPUT_DIM==10, legacy/JEPA model accept METADATA_DIM, feature extractor output matches model input, TRAINING_FEATURES/MATCH_AGGREGATE_FEATURES count, HIDDEN_DIM==128, model output shape.

#### `test_integration.py` (71 lines, 1 class, 4 tests)

Analytics engine, win probability, pro baseline comparison, dataset construction.

---

### 4.21 Temporal and Baseline Tests

#### `test_temporal_baseline.py` (243 lines, 5 classes, 18 tests)

ComputeWeight (8), ComputeWeightedBaseline (5), DetectMetaShift (4), GetTemporalBaseline (1), MetricToBaselineKey (2).

#### `test_baselines.py` (425 lines, 6 classes, 28 tests)

- **`TestHardDefaultBaseline`** (4 tests) -- Dict, 8 expected keys, mean/std structure, std positive.
- **`TestGetDefaultProBaseline`** (2 tests) -- Returns dict with provenance, contains all hard keys.
- **`TestCalculateDeviations`** (6 tests) -- Z-score, negative Z, zero std skip, missing player stat, multiple metrics, scalar baseline.
- **`TestTemporalBaselineDecay`** (14 tests) -- Weight today/future/half-life/very old, monotone decreasing, weighted baseline empty/single, detect meta shift, metric_to_baseline_key, constants (HALF_LIFE_DAYS==90, MIN_WEIGHT==0.1).
- **`TestLearnedThreshold`** (2 tests) -- Defaults, custom values.
- **`TestRoleThresholdStore`** (12 tests) -- Cold start, thresholds, insufficient/sufficient samples, consistency, readiness report, 9 expected keys, learn from pro data empty/real/updates, MIN_SAMPLES==30.

---

### 4.22 Observability and Security Tests

#### `test_observability.py` (334 lines, 9 classes, 20 tests)

JSONFormatter (3), CorrelationID (3), LogLevelResolution (3), ErrorCodes (3), Retention (2), plus 4 structured logging classes.

#### `test_security.py` (153 lines, 1 class, 9 tests)

No hardcoded API keys/passwords, .env/.db in .gitignore, no sensitive files, no eval, integrity manifest, no debug prints, subprocess shell=False.

#### `test_security_hardening.py` (268 lines, 5 classes + 3 standalone)

SanitizeLLMContext (9: null byte, bell, escape, DEL stripped; newline/tab preserved; length cap; empty/None; Unicode), SafeIdentifier (5 valid/9 invalid), SafeColType (7 valid/5 invalid), SafeDefaultLiteral (9 valid/6 invalid), BackupLabel (6 valid/7 invalid), system prompt curly braces, monolith foreign keys, DBManager pragma handler.

---

### 4.23 Skill Assessment Tests

#### `test_skill_assessment.py` (354 lines, 6 classes, 28 tests)

SkillAxes (4), SkillVector (6), SigmoidApproximation (4), CurriculumLevel (5), SkillTensor (5), Integration (4).

#### `test_skill_model.py` (191 lines, 5 classes, 14 tests)

SkillLatentModel (4), LowPerformance (3), ProPerformance (3), plus edge cases.

---

### 4.24 UI and Frontend Tests

#### `test_qt_core.py` (387 lines, 5 classes)

- **`TestI18nBridge`** (5) -- Known key, fallback, set_language, rejects unknown, JSON loaded.
- **`TestScreenContracts`** (6) -- Importable (parametrised), has on_enter, constructable, settings, placeholder.
- **`TestWorker`** (3) -- Success/error/finished signals.
- **`TestAppStateApply`** (4) -- Emit on change, skip unchanged, handle None, notifications.
- **`TestThemeEngine`** (6) -- All themes, required slots, rating color good/bad, rating labels, default theme.

#### `test_v1_blockers.py` (460 lines, 8 classes, 23 tests)

Coaching notifications, toast/snackbar, design tokens, splash screen, error codes, UI state machine, accessibility, keyboard navigation.

#### `test_playback_engine.py` (166 lines, 2 classes, 8 tests)

DemoFrame (3), PlaybackEngine (5: init, iteration, speed, seek, pause/resume).

#### `test_detonation_overlays.py` (115 lines, 2 classes, 8 tests)

- **`TestGrenadeConstants`** (5 tests) -- All nade types have radii (HE=350, MOLOTOV=180, SMOKE=144, FLASH=1000), positive, colors defined, RGB tuples.
- **`TestTacticalMapOverlayProperty`** (3 tests) -- Property in source, draw method exists, integrated in draw_nade.

#### `test_chronovisor_highlights.py` (376 lines, 4 classes, 12 tests)

- **`TestCriticalMomentAnnotation`** (6 tests) -- Structure, severity classification (>0.3 critical, >0.15 significant, else notable), backward compat, context_ticks default, context_ticks in dict, scale names.
- **`TestMultiScaleDeduplication`** (4 tests) -- Micro preferred, higher severity wins, distant kept, empty.
- **`TestRenderCriticalMoments`** (5 tests) -- Produces .png file, empty returns None, without positions, with scale info, scale marker sizes in source.
- **`TestGenerateHighlightReport`** (1 test) -- Importable and callable.

#### `test_chronovisor_scanner.py` (265 lines, 5 classes, 14 tests)

- **`TestScanResult`** (4 tests) -- empty_success, not_empty_success, is_failure, not_failure.
- **`TestCriticalMoment`** (3 tests) -- to_dict, to_highlight_annotation, all fields.
- **`TestScaleConfig`** (3 tests) -- Creation, 3 scales defined, micro values (window=64, lag=16, threshold=0.10).
- **`TestDeduplication`** (4 tests) -- Empty, single, distant kept, overlapping severity.
- **`TestAnalyzeSignalAtScale`** (3 tests) -- Flat no moments, spike detected, insufficient data.

---

### 4.25 Onboarding Tests

#### `test_onboarding.py` (88 lines, 3 classes, 8 tests)

OnboardingStage (3), CacheInvalidation (3), StageProgression (2).

#### `test_onboarding_training.py` (157 lines, 4 classes, 10 tests)

FeatureExtraction (3), CosineSimilarity (3), Diversity (2), MonthlyLimit (2).

---

### 4.26 Miscellaneous Tests

#### `test_auto_enqueue.py` (140 lines, 1 class, 6 tests, integration)

Task creation, default status, pro demo flag, multiple tasks queued, timestamps within 60s, task ordering by created_at.

#### `test_utility_economy_extended.py` (147 lines, 4 classes, 4 tests)

Economy optimizer decisions, utility analyzer coverage.

#### `test_hybrid_engine.py` (229 lines, 3 classes, 11 tests)

Deviation detection (4), priority ordering (4), confidence scoring (3).

#### `test_handoff_regressions.py` (343 lines, 8 classes)

WAL/SHM cleanup, COPER timeout fallback, dialogue context preservation, time clip, NaN yaw, SSRF prevention.

#### `test_phase0_3_regressions.py` (575 lines, 11 classes, 26 tests)

CoachState singleton, backup atomicity, connection leak prevention, early stopping checkpoint, JEPA collapse guard, insufficient data, negative sampling bounds, PlayerRole unification, avg_kills normalization, tuple/list ambiguity.

#### `test_state_reconstructor.py` (102 lines, 2 classes, 9 tests)

WindowSegmentation (5), RAPStateReconstruction (4).

#### `test_label_source_monitor.py` (145 lines, 9 standalone tests)

Skip rate tracking, sliding window, alarm thresholds, source identification, log integration.

#### `test_pro_demo_miner.py` (195 lines, 1 class, 5 tests)

ProStatsMiner: initialization, stat card retrieval, player matching, data quality, error handling.

#### `test_profile_service.py` (139 lines, 3 classes, 10 tests)

ProfileServiceGuards (4), SteamResponseParsing (3), ProfileUpdate (3).

#### `test_services.py` (99 lines, 4 classes, 7 tests)

CoachingService (2), AnalysisService (2), VisualizationService (2), CoachingDialogueEngine (1).

#### `test_entropy_extended.py` (149 lines, 5 classes, 5 tests)

Non-negative, uniform vs clustered, empty, thread safety, effectiveness cap.

#### `test_momentum_extended.py` (135 lines, 5 classes, 5 tests)

Initialization, streaks, performance adjustment, reset, multi-round consistency.

---

## Part V: Cross-Cutting Design Patterns

### Test Infrastructure Patterns

1. **Venv Guard**: Both `conftest.py` and `_infra.py` enforce virtual environment usage, bypassed by `CI=1` or `GITHUB_ACTIONS=1`.

2. **In-Memory SQLite**: Tests use `sqlite:///:memory:` engines for isolation. File-backed databases use `tmp_path` for WAL mode tests. `StaticPool` used for cross-thread sharing.

3. **Fixture Hierarchy**: `conftest.py` provides 14 foundational fixtures (seeded sessions, model instances, mock managers). Test files compose these via pytest injection.

4. **Marker System**: `@pytest.mark.integration` for external resources (skipped by default), `@pytest.mark.timeout(N)` for NN-heavy tests, `@pytest.mark.skipif` for optional dependencies.

5. **BaseValidator Pattern**: Tools extend `BaseValidator(ABC)` with `define_checks()` to create consistent validation gates with structured reporting via `ToolReport`.

6. **`__new__()` Shell Construction**: Used extensively in coaching tests to create service objects without running `__init__()`, enabling isolated method testing.

7. **Deferred Imports**: Many test files import domain modules inside test methods rather than at module level to avoid import-time failures when modules are broken.

8. **Skip-Gate Pattern**: Integration tests query real data first; if insufficient records exist, they `pytest.skip()` rather than injecting synthetic data.

### Invariant Enforcement

Tests systematically verify these critical invariants:

- **METADATA_DIM=25**: `test_metadata_dim_contract.py`, `test_feature_extractor_contracts.py`, `test_dimension_chain_integration.py`, headless validator phases 5, 10, 14.
- **NN-MEM-01 Hopfield Bypass**: `test_rap_coach.py::TestRAPMemory::test_hopfield_bypass_training_mode`, `test_ema_hopfield_drift_invariants.py`.
- **NN-16 EMA Clone**: `test_nn_infrastructure.py::TestEMA` (10 tests), `test_ema_hopfield_drift_invariants.py`.
- **P-RSB-03 round_won Exclusion**: Verified through feature name contract tests.
- **DS-12 MIN_DEMO_SIZE**: `test_dem_validator.py`, `test_demo_format_adapter.py`.
- **P9-02 Embedding Collapse**: `test_embedding_collapse_detector.py` (10 tests).
- **DRIFT-01 Tick Feature Drift**: `test_ema_hopfield_drift_invariants.py`, `test_drift_and_heuristics.py`.
- **MOE-01 Sparse Routing**: `test_ema_hopfield_drift_invariants.py`, `test_moe_sparse_gate.py`.

### Reporting Architecture

All tools produce structured reports via `ToolReport` (JSON-serializable, with severity-aware failure counting). The headless validator uses a simpler `CheckResult` dataclass with `severity: "fail"|"warn"` for exit code determination.

### Bug Documentation Tests

Several test files explicitly document and expose known bugs:
- **Bug #4** (test_coach_manager_tensors.py): `dict.get(key, 0.0)` returns None when key exists with None value, causing NaN poisoning.
- **Bug #8** (test_coaching_service_contracts.py): COPER path doesn't validate tick_data type.
- **CHAT-02** (test_coaching_dialogue_tutor_mode.py): Third-person tutor mode rewriter regression tests.
- **F9-04/F9-01** (test_db_backup.py): Backup monolith hang risk from DB lock (tests skipped).

#### `test_demo_format_adapter.py` (253 lines, 5 classes, 16 tests)

- **`TestValidation`** (7 tests) -- Nonexistent file, empty, tiny, valid CS2, legacy CSGO (unsupported), unknown header, corruption warnings.
- **`TestFieldMapping`** (2 tests) -- Dict with >10 entries, 10 required canonical keys.
- **`TestChangelog`** (2 tests) -- Non-empty ProtoChange instances, chronological order.
- **`TestFormatVersions`** (3 tests) -- >= 2 entries, cs2_protobuf supported, csgo_legacy not supported.
- **`TestIntegration`** (4 tests) -- demo_parser imports kast, integrity delegates to adapter, CS2 accepted/legacy rejected, convenience function parity.

#### `test_demo_parser.py` (184 lines, 4 classes, 11 tests)

- **`TestParseDemoEdgeCases`** (2 tests) -- Nonexistent file returns empty DataFrame.
- **`TestParseSequentialTicksEdgeCases`** (1 test) -- Nonexistent file.
- **`TestRatingFormulas`** (6 tests) -- KD ratio, per-round averages, HLTV 2.0 rating components, final rating at baseline ~1.0, econ_rating, high performer > 1.0.
- **`TestDemoParserIntegration`** (2 tests, integration) -- Real demo parse, sequential ticks.

#### `test_grenade_thrown_extraction.py` (237 lines, 4 standalone tests)

HE grenade, flashbang, smoke, molotov throw events with position/player/tick verification.

---

### 4.9 Neural Network Tests

#### `test_jepa_model.py` (537 lines, 7 classes, 31 tests)

- **`TestJEPAEncoder`** (4) -- Output shape, latent dim, gradient flow, batch independence.
- **`TestJEPAPredictor`** (4) -- Prediction shape, context dependence, no NaN.
- **`TestJEPAModel`** (6) -- Forward pass, coaching output, selective forward, encoder freezing, target encoder update.
- **`TestVLJEPA`** (6) -- forward_vl keys, concept_probs (batch,16), coaching output, top_concepts, concept activation.
- **`TestConceptLabeler`** (5) -- label_tick (16,), values [0,1], label_batch, determinism, known patterns.
- **`TestCheckpointMigration`** (3) -- Old checkpoint, key renaming, missing keys with defaults.
- **`TestModelConfig`** (3) -- Default/custom dimensions, latent_dim propagation.

#### `test_jepa_training_pipeline.py` (636 lines, 11 classes, 40 tests)

- **`TestSelfSupervisedDataset`** (5) -- Length, __getitem__, windowing, edge cases, empty.
- **`TestContrastiveLoss`** (4) -- Computation, gradient flow, symmetry, temperature scaling.
- **`TestNegativeSampling`** (4) -- Count, no overlap, deterministic, batch handling.
- **`TestEMAMomentum`** (5) -- Decay, divergence, schedule, state_dict, apply/restore cycle.
- **`TestTargetEncoderFreezing`** (3) -- requires_grad=False, no gradient, parameter count match.
- **`TestCheckpointSaveLoad`** (4) -- Completeness, strict load, optimizer state, epoch counter.
- **`TestPretrainPhase`** (5) -- Shape, loss decreases, negative sampling, non-overlap, batch norm.
- **`TestFinetunePhase`** (4) -- Shape, frozen encoder, LR schedule, loss components.
- **`TestTwoStageProtocol`** (2) -- Pretrain-then-finetune, checkpoint loading.
- **`TestDataAugmentation`** (2) -- Noise injection, temporal jitter.
- **`TestTrainingReproducibility`** (2) -- Same seed same loss, different seeds differ.

#### `test_nn_config_reproducibility.py` (147 lines, 3 classes, 17 tests)

- **`TestGlobalSeed`** (6) -- GLOBAL_SEED==42, set_global_seed affects torch/numpy/random, deterministic ops, CUDA flag.
- **`TestConfigConstants`** (6) -- INPUT_DIM==METADATA_DIM, OUTPUT_DIM==10, HIDDEN_DIM==128, LATENT_DIM, LEARNING_RATE, BATCH_SIZE.
- **`TestReproducibility`** (5) -- Model init/forward/training determinism.

#### `test_nn_extensions.py` (385 lines, 10 classes, 35 tests)

NeuralRoleHead, ExtractRoleFeatures, NNConfig, ProPerformanceDataset, SelfSupervisedDataset, CoachNNConfig, AdvancedCoachNN, ModelManager, and helpers.

#### `test_nn_infrastructure.py` (382 lines, 4 classes, 31 tests)

- **`TestEMA`** (10) -- Construction, decay, update, apply_shadow, restore, state_dict round-trip, convergence, decay=0/1, clone in apply (NN-16).
- **`TestModelFactory`** (8) -- All types, checkpoint names, unknown raises ValueError, dimension propagation.
- **`TestPersistence`** (7) -- Save/load, strict, missing/extra keys, device mapping.
- **`TestSuperpositionLayer`** (6) -- Forward shape, gate weights, gradient flow, custom experts, sparse routing.

#### `test_nn_training.py` (191 lines, 3 classes, 17 tests)

EarlyStopping, TrainingDecision, TrainingControllerHelpers.

#### `test_moe_sparse_gate.py` (198 lines, 12 standalone tests)

Top-k routing, normalization, entropy regularization, gradient flow, expert utilization, load balancing, capacity factor, zero-expert fallback.

---

### 4.10 Training Pipeline Tests

#### `test_training_orchestrator_flows.py` (855 lines, 14 classes, 50 tests)

- **`TestResolveMapName`** (8) -- From metadata, de_ prefix, demo name pattern, case insensitive, fallback, cache, exception, all maps.
- **`TestComputeAdvantage`** (8) -- Balanced, numerical advantage/disadvantage, bomb planted T/CT, dead players, range [0,1], no players.
- **`TestClassifyTacticalRole`** (9) -- Save, CT/T default, retake, lurk, entry, aggressive, anchor, support.
- **`TestFetchBatches`** (5) -- Correct count, train/val split, epoch seed rotation, val fixed.
- **`TestPrepareTensorBatchJEPA`** (8) -- Keys, shapes, too small, short batch, exact 10, target follows context.
- **`TestRunTrainingEdgeCases`** (2) -- Abort no data, progress delegation.
- **`TestPerEpochSeedRotation`** (4) -- Same/different seeds, val stable, refetches.
- **`TestSubsampleSizeConfig`** (5) -- Default/custom train/val, custom passed.
- **`TestPatienceConfig`** (3) -- Default, custom, early stop.
- **`TestBestValLossResume`** (4) -- Restore from sidecar, no sidecar, without extra, save persists.
- **`TestEMATotalSteps`** (1) -- set_total_steps called.
- **`TestConstants`** (2) -- Advantage weights sum to 1, role indices contiguous.

#### `test_training_orchestrator_logic.py` (195 lines, 4 classes, 12 tests)

OrchestratorInit, EarlyStopping, EmptyBatchHandling, DeterministicNegativeSampling.

#### `test_training_callbacks.py` (258 lines, 5 classes, 16 tests)

TrainingCallback, CallbackRegistry, CallbackRegistryFire, CloseAll, TensorBoardCallback.

#### `test_dry_run_checkpoint_integrity.py` (93 lines, 2 standalone integration tests)

- **`test_dry_run_writes_no_checkpoint(tmp_path)`** -- Runs `run_full_training_cycle.py --dry-run` as subprocess, asserts no `.pt` files.
- **`test_real_run_writes_checkpoint(tmp_path)`** -- Runs with `--epochs 1`, asserts at least one `.pt` file.

---

### 4.11 RAP Coach Tests

#### `test_rap_coach.py` (628 lines, 9 classes, ~50 tests)

- **`TestResNetBlock`** (5) -- Identity/projection shortcut, output shapes, gradient flow.
- **`TestRAPPerception`** (4) -- dim==128, batch, no NaN, different spatial sizes.
- **`TestRAPMemory`** (4) -- Shapes, hidden passthrough, no NaN, Hopfield bypass (NN-MEM-01).
- **`TestRAPStrategy`** (4) -- Shape, gates sum to 1, custom experts, sparse top-2.
- **`TestRAPPedagogy`** (3) -- Value shape, skill vector, advantage gap.
- **`TestCausalAttributor`** (4) -- Diagnose shape, concepts, view delta, utility_need bounded.
- **`TestRAPCoachModel`** (13) -- Forward keys, shapes (advice/belief/value/gate/optimal_pos/attribution), sparsity loss, no NaN, deterministic, without skill vector, heuristic config.
- **`TestRAPCommunication`** (6) -- Low confidence suppresses, skill tiers, output is string, default skill level.
- **`TestRAPTrainer`** (7) -- Train step metrics, loss decreases, Z-penalty, weighted position loss, with/without target, scheduler.

#### `test_rap_training_dry_run.py` (245 lines, 3 classes)

- **`TestRAPOrchestratorGate`** (2) -- RAP disabled raises, enabled constructs.
- **`TestRAPDryRunSmoke`** (1, integration) -- Full dry-run smoke test.
- **`TestRAPLTCFixIsLoaded`** (2) -- Memory module importable, ODE solver shape patch.

---

### 4.12 Feature Engineering Tests

#### `test_feature_extractor_contracts.py` (270 lines, 6 classes, 18 tests)

MetadataDim (2), ExtractShape (3), FeatureRanges (4), NaNGuards (4), ConfigOverride (3), FeatureNames (2).

#### `test_features.py` (75 lines, 1 class, 3 tests)

Basic feature extraction: empty, populated, count consistency.

#### `test_metadata_dim_contract.py` (121 lines, 5 standalone tests)

METADATA_DIM==25 across vectorizer, coach_manager, nn config, feature names.

#### `test_tactical_features.py` (76 lines, 1 class, 7 tests)

UtilityAnalyzer smoke, economy phases (pistol/full_buy/eco/force_buy/half_buy/overtime).

#### `test_feature_kast_roles.py` (663 lines, 11 classes, 39 tests)

KAST Calculation (15 tests), Role Classification (12 tests), Coaching Dialogue (12 tests).

---

### 4.13 Experience Bank and Knowledge Tests

#### `test_experience_bank_db.py` (746 lines, 9 classes, 40 tests)

CRUD, embedding similarity, synthesis, feedback, temporal decay, dedup, thread safety.

#### `test_experience_bank_dedup.py` (89 lines, 1 class, 7 tests)

Hash-based dedup, similarity threshold, merge strategy, conflict resolution.

#### `test_experience_bank_logic.py` (123 lines, 2 classes, 8 tests)

ExperienceContext (5), SynthesizedAdvice (3).

#### `test_rag_knowledge.py` (290 lines, 4 classes, all integration)

KnowledgeEmbedder (3), KnowledgePopulator (2), KnowledgeRetriever (4), RAGCoaching (2).

---

### 4.14 Spatial and Map Tests

#### `test_spatial_engine.py` (63 lines, 5 standalone tests)

Coordinate transforms: dust2/mirage canonical points, pixel mapping, round-trip, unknown map.

#### `test_spatial_and_baseline.py` (125 lines, 4 classes, 9 tests)

Z-penalty (3), fuzzy nickname matching (2), outlier trimming (2), soft gate tiers (2).

#### `test_z_penalty.py` (153 lines, 3 classes, 26 tests)

Computation (10), vertical level classification (8), integration with training (8).

#### `test_map_manager.py` (105 lines, 8 standalone tests)

Path resolution, smart loading, fallback, theme variants, normalization.

---

### 4.15 Tensor Factory Tests

#### `test_tensor_factory.py` (853 lines, 17 classes, ~58 tests)

TensorConfig (4), TensorFactoryInit (2), MapTensorLegacy (7), MapTensorPOV (6), ViewTensorLegacy (6), ViewTensorPOV (3), MotionTensor (10), LegacyMotion (3), GenerateAllTensors (4), WorldToGrid (3), Normalize (3), FOVMask (3), DrawCircle (3), Singleton (3), GaussianBlur (1), ResolutionIndependence (1 parametrized: 16/32/64/128), EdgeCases (5).

---

### 4.16 Trade Kill and Round Stats Tests

#### `test_trade_kill_detector.py` (364 lines, 5 classes, ~21 tests)

TradeKillResult (6), AssignRoundNumbers (5), DetectTradeKills (12), GetPlayerTradeStats (5), Constants (1).

#### `test_trade_timing.py` (193 lines, 6 standalone tests)

Accumulate response ticks, skip zero/negative, aggregate avg, zero when no trades, multi-trade averaging, exception logging.

#### `test_round_stats_enrichment.py` (298 lines, 2 classes, 18 tests)

AggregateRoundStatsToMatch (15), EnrichFromDemoImport (3).

#### `test_round_utils.py` (310 lines, 4 classes)

InferRoundPhase (13), ExperienceContext (16), SynthesizedAdvice (2), ExperienceBankHelpers (14).

---

### 4.17 EMA, Drift, and Embedding Tests

#### `test_ema_hopfield_drift_invariants.py` (148 lines, 6 standalone tests)

- EMA restore breaks backup aliasing (NN-16).
- EMA apply_shadow breaks shadow aliasing (NN-16 original bug).
- Hopfield bypass after partial load (MEM-01).
- MoE sparse strategy outputs nonzero per sample (MOE-01).
- Tick feature drift monitor detects per-dim shift (DRIFT-01).
- Drift monitor no-ops without reference (raises RuntimeError).

#### `test_embedding_collapse_detector.py` (118 lines, 10 standalone tests)

P9-02 hard-stop guard: healthy variances (20 epochs), single collapsed epoch, two consecutive abort, recovery resets, at-threshold healthy, NaN treated as collapse, negative variance collapse, reset clears state, custom patience=3, error message diagnostic hints (InfoNCE/EMA/VICReg/data).

#### `test_drift_and_heuristics.py` (252 lines, 4 classes, 12 tests)

- **`TestDriftMonitor`** (3 tests) -- Detects drift on shifted batch, no drift on matching, report structure.
- **`TestShouldRetrain`** (3 tests) -- Triggers on 3/5 drifted, no trigger on 2/5, insufficient history.
- **`TestHeuristicConfig`** (4 tests) -- Defaults, serialization roundtrip, unknown keys ignored, load_learned_heuristics defaults.
- **`TestDifferentialHeatmap`** (2 tests) -- Static import, has generate method.

#### `test_engagement_range_extended.py` (142 lines, 2 classes, 5 tests)

- **`TestEngagementRangeAnalyzerExtended`** (4 tests) -- Instantiation (5 method attributes), same-point distance==0, 3D distance, negative coords.
- **`TestNamedPositionRegistryExtended`** (1 test) -- Empty registry, analyze empty kills.

---

### 4.18 Checkpoint and Persistence Tests

#### `test_checkpoint_normalizer_versioning.py` (172 lines, 10 standalone tests)

Sidecar creation (schema_version, metadata_dim, feature_names, heuristic_config), roundtrip save/load, metadata_dim mismatch raises StaleCheckpointError, feature_names mismatch, schema_version mismatch, missing feature_names, corrupt JSON, legacy checkpoint without sidecar (warns and loads), extra_meta roundtrip, atomicity (disk full rolls back both files).

#### `test_persistence_stale_checkpoint.py` (230 lines, 3 classes, 10 tests)

StaleCheckpointDetection (4), CorruptedFiles (3), CheckpointNormalization (3).

#### `test_model_factory_contracts.py` (226 lines, 5 classes, 18 tests)

ModelTypes (5), DimensionPropagation (4), CheckpointNames (4), UnknownType (2), TypeConstants (3).

#### `test_models.py` (75 lines, 1 class, 8 tests)

Database model defaults for PlayerMatchStats, PlayerTickState, CoachState.

---

### 4.19 Session and Lifecycle Tests

#### `test_session_engine.py` (463 lines, 8 classes, 22 tests)

ZombieTaskCleanup (3), RetrainingTrigger (4), BaselineSnapshot (3), MetaShift (3), StdinMonitor (2), plus 3 lifecycle edge case classes.

#### `test_lifecycle.py` (82 lines, 1 class, 9 tests)

AppLifecycleManager: single instance, shutdown sequence, daemon threads, state transitions, error recovery.

---

### 4.20 Deployment and Integration Tests

#### `test_deployment_readiness.py` (391 lines, 6 classes, 8 tests, heavily parametrized)

- **`TestForwardPassReliability`** (1 parametrized over 5 types) -- 100 forward passes, NaN count == 0.
- **`TestInferenceLatency`** (1 parametrized over 3 types) -- Median < budget * CI multiplier.
- **`TestBatchSizeInvariance`** (1 parametrized over 5 types) -- Batch 1 matches batch 4.
- **`TestDeterministicReproducibility`** (1 parametrized over 2 types) -- 5 runs with same seed.
- **`TestOODGracefulHandling`** (2 parametrized) -- OOD inputs no crash, NaN input graceful.
- **`TestDeploymentVerdict`** (2 tests) -- Pass rate >= 75%, NaN ratio <= 10%.

#### `test_dimension_chain_integration.py` (125 lines, 1 class, 9 tests)

METADATA_DIM==INPUT_DIM, ==25, OUTPUT_DIM==10, legacy/JEPA model accept METADATA_DIM, feature extractor output matches model input, TRAINING_FEATURES/MATCH_AGGREGATE_FEATURES count, HIDDEN_DIM==128, model output shape.

#### `test_integration.py` (71 lines, 1 class, 4 tests)

Analytics engine, win probability, pro baseline comparison, dataset construction.

---

### 4.21 Temporal and Baseline Tests

#### `test_temporal_baseline.py` (243 lines, 5 classes, 18 tests)

ComputeWeight (8), ComputeWeightedBaseline (5), DetectMetaShift (4), GetTemporalBaseline (1), MetricToBaselineKey (2).

#### `test_baselines.py` (425 lines, 6 classes, 28 tests)

- **`TestHardDefaultBaseline`** (4 tests) -- Dict, 8 expected keys, mean/std structure, std positive.
- **`TestGetDefaultProBaseline`** (2 tests) -- Returns dict with provenance, contains all hard keys.
- **`TestCalculateDeviations`** (6 tests) -- Z-score, negative Z, zero std skip, missing player stat, multiple metrics, scalar baseline.
- **`TestTemporalBaselineDecay`** (14 tests) -- Weight today/future/half-life/very old, monotone decreasing, weighted baseline empty/single, detect meta shift, metric_to_baseline_key, constants (HALF_LIFE_DAYS==90, MIN_WEIGHT==0.1).
- **`TestLearnedThreshold`** (2 tests) -- Defaults, custom values.
- **`TestRoleThresholdStore`** (12 tests) -- Cold start, thresholds, insufficient/sufficient samples, consistency, readiness report, 9 expected keys, learn from pro data empty/real/updates, MIN_SAMPLES==30.

---

### 4.22 Observability and Security Tests

#### `test_observability.py` (334 lines, 9 classes, 20 tests)

JSONFormatter (3), CorrelationID (3), LogLevelResolution (3), ErrorCodes (3), Retention (2), plus 4 structured logging classes.

#### `test_security.py` (153 lines, 1 class, 9 tests)

No hardcoded API keys/passwords, .env/.db in .gitignore, no sensitive files, no eval, integrity manifest, no debug prints, subprocess shell=False.

#### `test_security_hardening.py` (268 lines, 5 classes + 3 standalone)

SanitizeLLMContext (9: null byte, bell, escape, DEL stripped; newline/tab preserved; length cap; empty/None; Unicode), SafeIdentifier (5 valid/9 invalid), SafeColType (7 valid/5 invalid), SafeDefaultLiteral (9 valid/6 invalid), BackupLabel (6 valid/7 invalid), system prompt curly braces, monolith foreign keys, DBManager pragma handler.

---

### 4.23 Skill Assessment Tests

#### `test_skill_assessment.py` (354 lines, 6 classes, 28 tests)

SkillAxes (4), SkillVector (6), SigmoidApproximation (4), CurriculumLevel (5), SkillTensor (5), Integration (4).

#### `test_skill_model.py` (191 lines, 5 classes, 14 tests)

SkillLatentModel (4), LowPerformance (3), ProPerformance (3), plus edge cases.

---

### 4.24 UI and Frontend Tests

#### `test_qt_core.py` (387 lines, 5 classes)

- **`TestI18nBridge`** (5) -- Known key, fallback, set_language, rejects unknown, JSON loaded.
- **`TestScreenContracts`** (6) -- Importable (parametrized), has on_enter, constructable, settings, placeholder.
- **`TestWorker`** (3) -- Success/error/finished signals.
- **`TestAppStateApply`** (4) -- Emit on change, skip unchanged, handle None, notifications.
- **`TestThemeEngine`** (6) -- All themes, required slots, rating color good/bad, rating labels, default theme.

#### `test_v1_blockers.py` (460 lines, 8 classes, 23 tests)

Coaching notifications, toast/snackbar, design tokens, splash screen, error codes, UI state machine, accessibility, keyboard navigation.

#### `test_playback_engine.py` (166 lines, 2 classes, 8 tests)

DemoFrame (3), PlaybackEngine (5: init, iteration, speed, seek, pause/resume).

#### `test_detonation_overlays.py` (115 lines, 2 classes, 8 tests)

- **`TestGrenadeConstants`** (5 tests) -- All nade types have radii (HE=350, MOLOTOV=180, SMOKE=144, FLASH=1000), positive, colors defined, RGB tuples.
- **`TestTacticalMapOverlayProperty`** (3 tests) -- Property in source, draw method exists, integrated in draw_nade.

#### `test_chronovisor_highlights.py` (376 lines, 4 classes, 12 tests)

- **`TestCriticalMomentAnnotation`** (6 tests) -- Structure, severity classification (>0.3 critical, >0.15 significant, else notable), backward compat, context_ticks default, context_ticks in dict, scale names.
- **`TestMultiScaleDeduplication`** (4 tests) -- Micro preferred, higher severity wins, distant kept, empty.
- **`TestRenderCriticalMoments`** (5 tests) -- Produces .png file, empty returns None, without positions, with scale info, scale marker sizes in source.
- **`TestGenerateHighlightReport`** (1 test) -- Importable and callable.

#### `test_chronovisor_scanner.py` (265 lines, 5 classes, 14 tests)

- **`TestScanResult`** (4 tests) -- empty_success, not_empty_success, is_failure, not_failure.
- **`TestCriticalMoment`** (3 tests) -- to_dict, to_highlight_annotation, all fields.
- **`TestScaleConfig`** (3 tests) -- Creation, 3 scales defined, micro values (window=64, lag=16, threshold=0.10).
- **`TestDeduplication`** (4 tests) -- Empty, single, distant kept, overlapping severity.
- **`TestAnalyzeSignalAtScale`** (3 tests) -- Flat no moments, spike detected, insufficient data.

---

### 4.25 Onboarding Tests

#### `test_onboarding.py` (88 lines, 3 classes, 8 tests)

OnboardingStage (3), CacheInvalidation (3), StageProgression (2).

#### `test_onboarding_training.py` (157 lines, 4 classes, 10 tests)

FeatureExtraction (3), CosineSimilarity (3), Diversity (2), MonthlyLimit (2).

---

### 4.26 Miscellaneous Tests

#### `test_auto_enqueue.py` (140 lines, 1 class, 6 tests, integration)

Task creation, default status, pro demo flag, multiple tasks queued, timestamps within 60s, task ordering by created_at.

#### `test_utility_economy_extended.py` (147 lines, 4 classes, 4 tests)

Economy optimizer decisions, utility analyzer coverage.

#### `test_hybrid_engine.py` (229 lines, 3 classes, 11 tests)

Deviation detection (4), priority ordering (4), confidence scoring (3).

#### `test_handoff_regressions.py` (343 lines, 8 classes)

WAL/SHM cleanup, COPER timeout fallback, dialogue context preservation, time clip, NaN yaw, SSRF prevention.

#### `test_phase0_3_regressions.py` (575 lines, 11 classes, 26 tests)

CoachState singleton, backup atomicity, connection leak prevention, early stopping checkpoint, JEPA collapse guard, insufficient data, negative sampling bounds, PlayerRole unification, avg_kills normalization, tuple/list ambiguity.

#### `test_state_reconstructor.py` (102 lines, 2 classes, 9 tests)

WindowSegmentation (5), RAPStateReconstruction (4).

#### `test_label_source_monitor.py` (145 lines, 9 standalone tests)

Skip rate tracking, sliding window, alarm thresholds, source identification, log integration.

#### `test_pro_demo_miner.py` (195 lines, 1 class, 5 tests)

ProStatsMiner: initialization, stat card retrieval, player matching, data quality, error handling.

#### `test_profile_service.py` (139 lines, 3 classes, 10 tests)

ProfileServiceGuards (4), SteamResponseParsing (3), ProfileUpdate (3).

#### `test_services.py` (99 lines, 4 classes, 7 tests)

CoachingService (2), AnalysisService (2), VisualizationService (2), CoachingDialogueEngine (1).

#### `test_entropy_extended.py` (149 lines, 5 classes, 5 tests)

Non-negative, uniform vs clustered, empty, thread safety, effectiveness cap.

#### `test_momentum_extended.py` (135 lines, 5 classes, 5 tests)

Initialization, streaks, performance adjustment, reset, multi-round consistency.

---

## Part V: Cross-Cutting Design Patterns

### Test Infrastructure Patterns

1. **Venv Guard**: Both `conftest.py` and `_infra.py` enforce virtual environment usage, bypassed by `CI=1` or `GITHUB_ACTIONS=1`.

2. **In-Memory SQLite**: Tests use `sqlite:///:memory:` engines for isolation. File-backed databases use `tmp_path` for WAL mode tests. `StaticPool` used for cross-thread sharing.

3. **Fixture Hierarchy**: `conftest.py` provides 14 foundational fixtures (seeded sessions, model instances, mock managers). Test files compose these via pytest injection.

4. **Marker System**: `@pytest.mark.integration` for external resources (skipped by default), `@pytest.mark.timeout(N)` for NN-heavy tests, `@pytest.mark.skipif` for optional dependencies.

5. **BaseValidator Pattern**: Tools extend `BaseValidator(ABC)` with `define_checks()` to create consistent validation gates with structured reporting via `ToolReport`.

6. **`__new__()` Shell Construction**: Used extensively in coaching tests to create service objects without running `__init__()`, enabling isolated method testing.

7. **Deferred Imports**: Many test files import domain modules inside test methods rather than at module level to avoid import-time failures when modules are broken.

8. **Skip-Gate Pattern**: Integration tests query real data first; if insufficient records exist, they `pytest.skip()` rather than injecting synthetic data.

### Invariant Enforcement

Tests systematically verify these critical invariants:

- **METADATA_DIM=25**: `test_metadata_dim_contract.py`, `test_feature_extractor_contracts.py`, `test_dimension_chain_integration.py`, headless validator phases 5, 10, 14.
- **NN-MEM-01 Hopfield Bypass**: `test_rap_coach.py::TestRAPMemory::test_hopfield_bypass_training_mode`, `test_ema_hopfield_drift_invariants.py`.
- **NN-16 EMA Clone**: `test_nn_infrastructure.py::TestEMA` (10 tests), `test_ema_hopfield_drift_invariants.py`.
- **P-RSB-03 round_won Exclusion**: Verified through feature name contract tests.
- **DS-12 MIN_DEMO_SIZE**: `test_dem_validator.py`, `test_demo_format_adapter.py`.
- **P9-02 Embedding Collapse**: `test_embedding_collapse_detector.py` (10 tests).
- **DRIFT-01 Tick Feature Drift**: `test_ema_hopfield_drift_invariants.py`, `test_drift_and_heuristics.py`.
- **MOE-01 Sparse Routing**: `test_ema_hopfield_drift_invariants.py`, `test_moe_sparse_gate.py`.

### Reporting Architecture

All tools produce structured reports via `ToolReport` (JSON-serializable, with severity-aware failure counting). The headless validator uses a simpler `CheckResult` dataclass with `severity: "fail"|"warn"` for exit code determination.

### Bug Documentation Tests

Several test files explicitly document and expose known bugs:
- **Bug #4** (test_coach_manager_tensors.py): `dict.get(key, 0.0)` returns None when key exists with None value, causing NaN poisoning.
- **Bug #8** (test_coaching_service_contracts.py): COPER path doesn't validate tick_data type.
- **CHAT-02** (test_coaching_dialogue_tutor_mode.py): Third-person tutor mode rewriter regression tests.
- **F9-04/F9-01** (test_db_backup.py): Backup monolith hang risk from DB lock (tests skipped).
