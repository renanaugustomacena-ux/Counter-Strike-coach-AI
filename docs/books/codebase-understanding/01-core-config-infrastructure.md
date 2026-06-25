# Chapter 01 -- Core Configuration and Infrastructure

Exhaustive reference for every root-level file, the `Programma_CS2_RENAN/core/` module,
the `Programma_CS2_RENAN/observability/` module, and the Alembic migration stub.
Written 2026-06-24.

---

## Part A -- Root-Level Files

### A.1  CLAUDE.md

The project's primary instruction file for AI agents. Establishes:

- **Identity line**: Macena CS2 Analyzer -- Python 3.10+, PySide6/Qt, PyTorch, SQLite-WAL,
  Alembic, demoparser2, BS4+FlareSolverr.  Package root is `Programma_CS2_RENAN`.
- **Sibling docs**: links to `REFERENCE.md`, `AUDIT.md`, `TASKS.md`, `docs/DIAGNOSIS_2026-05.md`.
  Rule: never spawn new diagnostic dump files.
- **Principles**: Correctness over elegance.  No silent failures.  Deterministic
  (`GLOBAL_SEED=42`).  Zero-trust at boundaries.  Atomic commits.  **Tick decimation
  is FORBIDDEN** (never downsample tick data).
- **Commands**: launch (`launch.sh`, `python -m Programma_CS2_RENAN.apps.qt_app.app`,
  `console.py`, `goliath.py`), test (`pytest`), mandatory post-task
  (`python tools/headless_validator.py` must exit 0), lint (`pre-commit`, `black`,
  `isort`, `mypy`), DB (`alembic upgrade head`), HLTV infra (`docker compose up -d`).
- **Critical Invariants** (7 items):
  - **P-RSB-03**: `round_won` excluded from training features (label leak).
  - **NN-MEM-01**: Hopfield bypassed until >= 2 forward passes.
  - **NN-16**: EMA `apply_shadow()` must `.clone()` shadows.
  - **NN-JM-04**: Target encoder `requires_grad=False` during EMA.
  - **DS-12**: `MIN_DEMO_SIZE=10MB`.
  - **P-VEC-02/P3-A**: NaN/Inf clamp + >5% batch triggers `DataQualityError`.
  - **METADATA_DIM=25** -- sole source in `vectorizer.py`.
- **DO NOT** list: HLTV is not demo management, never read config globals in daemons
  (use `get_setting()`/`get_credential()`), never grow 25-dim without updating
  `FEATURE_NAMES`+`METADATA_DIM`+model `input_dim`, never use `round_won` as feature,
  never `extract()` without `map_name`, never Python `hash()` (use `hashlib.md5`),
  never instantiate `DatabaseManager`/`HLTVDatabaseManager` directly, never skip
  Hopfield bypass, never tick decimation.
- **DO** list: `set_global_seed(42)` pre-training, `_config_override` in `extract()`
  for batch, type-hint public API, `get_logger("cs2analyzer.<mod>")` only.
- **Skills**: `/validate` is mandatory post-task; `/pre-commit` for hooks; path-triggered
  skills mapped by module path.

### A.2  REFERENCE.md

Static reference companion to CLAUDE.md containing 11 sections:

1. **Architecture Overview**: eight logical AI subsystems with file tree.
2. **25-Dim Metadata Contract (P-X-01)**: `METADATA_DIM=25` in `vectorizer.py:32`,
   `FEATURE_NAMES` at lines 151-177, import-time assert.  Index map of all 25 features
   (health, armor, has_helmet, has_defuser, equipment_value, is_crouching, is_scoped,
   is_blinded, enemies_visible, pos_x, pos_y, pos_z, view_yaw_sin, view_yaw_cos,
   view_pitch, z_penalty, kast_estimate, **map_id at index 17**, round_phase,
   weapon_class, time_in_round, bomb_planted, teammates_alive, enemies_alive,
   team_economy).  ContractGuard test pins value/length/order.
3. **Critical Invariants**: 10 rows covering P-X-01, P-RSB-03, NN-MEM-01, NN-16,
   NN-JM-04, DS-12, P-VEC-02/P3-A, P9-02, G-01, DET-01, REPR-01.
4. **Phase 0 Hygiene Gates**: F3-25, F3-08, G-01, P9-02, section-8.3, ContractGuard --
   all FIXED as of 2026-04-25.
5. **Storage Architecture**: Three databases (Monolith `database.db`, HLTV
   `hltv_metadata.db`, per-match shards `match_{id}.db`).  Singletons mandatory:
   `get_db_manager()`, `get_hltv_db_manager()`.  Settings file `user_settings.json`
   (gitignored), read via `get_setting()`, write via `save_user_setting()`.
6. **Global Constants & Defaults**: GLOBAL_SEED=42, METADATA_DIM=25, MIN_DEMO_SIZE=10MB,
   EMA tau_base=0.996, InfoNCE tau=learnable init log(0.07), embedding-collapse
   threshold 0.01/2 epochs, concept_temperature clamped [0.01,1.0], label_source alarm
   1%/5min, BATCH_SIZE=16, latent_dim=256, MoCo queue 4096, VICReg lambdas, MoE
   load-balance aux, _MIN_TRAINING_SAMPLES=100, P3-C fallback-rate gates 10%/30%.
7. **Skills -- When to Trigger**: mandatory (`/validate`, `/pre-commit`),
   path-triggered (storage->db-review, nn->ml-check, jepa->jepa-audit, etc.),
   multi-file skills.
8. **Tests -- Where to Look**: 8 test files enumerated.  Run patterns documented.
   Determinism probe: three seeds, val/train ratio variance < 0.05.
9. **Configs / Env Vars**: CS2_LOG_LEVEL, CS2_INTEGRATION_TESTS, CS2_NONDETERMINISTIC,
   CI, KIVY_NO_ARGS/KIVY_LOG_LEVEL, QT_QUICK_BACKEND.
10. **Open Documentation Debt**: hltv_metadata.db not under Alembic, per-match shard
    archival strategy undocumented, 14 arxiv papers indexed.
11. **Cross-references**: to CLAUDE.md, AUDIT.md, TASKS.md, completion programme,
    modernization reports.

### A.3  TASKS.md

Single source of actionable work items.  Convention: `#N . status . priority . title`.

**Active items** (as of reading):
- #17 DONE: MOE-02 dense->sparse gate.
- #33 TODO MED: Streaming Gemma chat.
- #37 TODO MED: Always-on NN inference for non-player_query intents.
- #38 TODO MED: HLTV rescrape for 24 placeholder players.
- #39-42 DONE: Various GAP fixes and finale gate.
- #43-48 TODO LOW: Mixed precision, sub-tick data, pause/resume events, HLTV alembic,
  full LLM A/B baseline.
- #49-50 DONE: CI pipeline restoration and CI-red notification.

**Refactor queues**:
- #30 CLOSED: Original 5 targets all refactored.
- #30-bis CLOSED: AST census successor, all actionable targets resolved.
- #51-55: Various items (seed rotation DONE, single-sample quality gate TODO,
  NaN/Inf throttle TODO, POV-TBL-01 DONE, Console TUI/CLI DONE).

**#28 Broad-except narrowing queue**: 32 sites across files, per-site analysis strategy
documented for coaching_service.py (12), session_engine.py (20), demo_parser.py (3),
lifecycle.py (3).

**Done sections**: Sessions 2-4 detailed with fixes, false-positives verified, and
validator results (up to 1925 passed, 0 failed).

### A.4  AUDIT.md

Living document replacing scattered diagnostic dumps.  11 sections:

1. **Repo Hygiene & Bloat**: 12 MB PyCharm XMLs, Windows-path artifact, duplicate docs,
   committed logs, IDE artifacts.
2. **Static-Analysis Triage**: P0 real bugs (11 items all fixed), P1 significant smells
   (optional-dep guards, session.execute migration, missing requirements, dead imports,
   broad except), P2 tech debt (outdated deps, invalid JSON, cross-class access,
   duplicated DB queries), P4 suppressed noise.
3. **ML/AI Deep Audit**: CONFIRMED findings (EMA-01, QT-i18n-01, TEST-01, LLM-01 all
   fixed), CONFIRMED file-only (LEAK-01/02, LOSS-02, MOE-02, DRIFT-01, DATA-01,
   REPR-01, DET-01/02, LOSS-01, EMA-02/03, MEM-01, TEST-COV), FALSE-POSITIVE
   (LOSS-03, MoE-01, DIM-01, LOSS-04).
4. **Coaching Service & Chatbot LLM**: Gemma 4 verification pass, silent model-fallback
   bug fixed.
5. **DB / WAL / Alembic**: 14 migrations reviewed, no issues.
6. **Validator Runs**: references to session summaries.
7. **Resolved / Closed**: comprehensive list of session 2 fixes and verified
   false-positives.
8. **Interactive Coaching Chat**: 8 findings (CHAT-01 through MDM-01), all resolved.
9. **Whitebox Security Audit**: 0 CRITICAL, 4 HIGH (BE-03, FE-01, DB-01, DB-02), 8 MED,
   4 LOW -- all FIXED.  9.4 verified-clean categories.
10. **Pipeline Integrity Sweep**: GAP-01 through GAP-07 + GAP-09/10/Finale -- all fixed.
    Baseline eval report, deferred GAPs, destructive actions requiring authorization.
11. **CI Pipeline Restoration**: 19 consecutive failed runs resolved.  4 root causes
    (Python 3.10->3.11, hashlib md5 usedforsecurity, detect-secrets false-positives,
    test drifts).

### A.5  jepa.md

Comprehensive Italian-language architectural analysis document (948 lines, ~62 KB).
Written 2026-02-21 by automated codebase analysis.  10 chapters:

1. **Introduction & Scientific Context**: LeCun's JEPA vision paper (June 2022), why
   JEPA for CS2 (partial observability analogy), document scope.
2. **From Vision to Game Stats**: The fundamental transformation.  JEPA does NOT process
   vision -- operates on 25-dim numeric vector.  FeatureExtractor is the bridge.
   Feature table with normalization details.  Loss/preservation analysis.
3. **JEPA Model Architecture**: JEPAEncoder (25->512->256 MLP, ~145K params),
   JEPAPredictor (256->512->256 bottleneck expansion), JEPACoachingModel (composite:
   2x encoder + predictor + LSTM + 3-expert MoE + gate + tanh), four forward paths
   (forward_jepa_pretrain, forward_coaching, forward_selective, forward).  EMA update
   formula.  InfoNCE contrastive loss (divergence from original JEPA's Smooth L1).
4. **VL-JEPA -- Concept Alignment**: VLJEPACoachingModel extends with concept_embeddings
   (16 concepts x 256-dim), concept_projector, learnable concept_temperature.  16
   coaching concepts across 5 dimensions (positioning, utility, decision, engagement,
   psychology).  ConceptLabeler label leakage problem documented.
5. **TensorFactory**: map_tensor (3,128,128), view_tensor (3,224,224), motion_tensor
   (3,224,224).  Danger channel is placeholder (all zeros).  Motion tensor is scalar
   broadcast.  These feed RAP Coach, NOT JEPA.
6. **Training Pipeline**: Two entry points (jepa_train.py standalone vs
   training_orchestrator.py integrated).  Data preparation, JEPATrainer, two-stage
   protocol (pre-train on pro demos, fine-tune on user data).
7. **Inference & Selective Decoding**: forward_selective cosine-distance gating
   (threshold 0.05).  Gap: JEPA not wired to GhostEngine or CoachingService.
8. **Coach Introspection Observatory**: 4-level monitoring (TrainingCallback ABC,
   TensorBoardCallback, MaturityObservatory with 5 signals and conviction_index
   state machine, EmbeddingProjector).
9. **Architectural Comparison**: Systematic table comparing Meta V-JEPA vs Macena JEPA
   across 13 dimensions.  Philosophical divergences (contrastive vs non-contrastive).
10. **Critical Evaluation**: What works, what doesn't, what's aspirational, roadmap.

### A.6  CONSOLE_ARCHITECTURE.md

Technical design document for the Unified Control Console.  5 phases (1-3 complete,
4 pending).

**Components**:
- **Console** singleton (`console.py`): Thread-safe via `__new__` + `_lock`.  State enum
  (IDLE/BUSY/MAINTENANCE/ERROR).  Attributes: project_root, state, supervisor,
  ingest_manager, db_governor, ml_controller.  Methods: boot(), shutdown(),
  get_system_status(), start/stop/pause/resume_training(), _audit_databases(),
  _compute_state(), _get_baseline_status().
- **ServiceSupervisor** (`console.py`): Manages background daemons as subprocesses.
  Registered service: "hunter" (hltv_sync_service.py).  Auto-restart max 3 retries,
  1hr reset.  5s terminate->kill escalation.
- **MLController + MLControlContext** (`ml_controller.py`): MLControlContext provides
  check_state() for cooperative interruption (pause/resume via busy-wait, soft stop
  via StopIteration, throttle via sleep injection).  MLController is thread wrapper.
- **IngestionManager** (`ingest_manager.py`): 3 modes (SINGLE/CONTINUOUS/TIMED).
  Strict sequential processing: queue 1 file -> ingest -> 5s pause -> next.  Task
  tracking via IngestionTask DB model.
- **DatabaseGovernor** (`db_governor.py`): audit_storage() scans Tier 1/2/3,
  verify_integrity() runs PRAGMA integrity_check, prune_match_data(), rebuild_indexes().

**State machines**: SystemState (IDLE/ERROR), ServiceStatus
(STOPPED->STARTING->RUNNING->CRASHED with auto-restart).

**API Contract** (Phase 4, pending): `/api/console/status` GET,
`/api/console/control/ml` POST, `/api/console/control/ingest` POST,
`/api/console/services/{name}` POST, `/api/console/audit/db` GET.

### A.7  pyproject.toml

Build system configuration:

- **Build**: setuptools >= 68.0.
- **Project metadata**: name `macena-cs2-analyzer`, version 1.0.0, requires-python >=3.10,
  license Proprietary.
- **Optional dependencies**: `rap = ["ncps>=1.0", "hflayers>=0.1"]`.
- **Packages**: includes `Programma_CS2_RENAN*`.
- **Black**: line-length 100, target-version py310, excludes external_analysis/dist/.venv.
- **isort**: profile "black", line_length 100, same skip globs.
- **mypy**: python_version 3.10, warn_return_any, ignore_missing_imports,
  check_untyped_defs, excludes external_analysis/dist/.venv/tests.
- **Coverage run**: source `Programma_CS2_RENAN`, omits tests/.venv/tools/legacy
  kivy/entry-point scripts.
- **Coverage report**: fail_under 40, show_missing, exclude pragmas/main-guards/TYPE_CHECKING.

### A.8  pytest.ini

Test configuration:

- **testpaths**: `tests` and `Programma_CS2_RENAN/tests`.
- **Discovery**: `test_*.py` files, `Test*` classes, `test_*` functions.
- **Options**: `-v --tb=short --strict-markers`.
- **Global timeout**: 30 seconds (requires pytest-timeout plugin).
- **Markers**: slow, integration, unit, portability, known_fail, flaky.
- **norecursedirs**: .git, .github, dist, build, egg-info, __pycache__, .venv, venv,
  D:*, external_libs, latest, reports, docs.

### A.9  alembic.ini

Standard Alembic configuration:

- **script_location**: `alembic` (at project root).
- **prepend_sys_path**: `.` (current directory).
- **path_separator**: `os` (OS-dependent).
- **sqlalchemy.url**: `sqlite:///Programma_CS2_RENAN/backend/storage/database.db`.
- **Logging**: root WARNING, sqlalchemy.engine WARNING, alembic INFO.  Console handler
  with generic formatter.

### A.10  docker-compose.yml

Single service:

- **flaresolverr**: Image `ghcr.io/flaresolverr/flaresolverr:v3.4.6`.  Container name
  `flaresolverr`.  Port 8191:8191.  Environment: LOG_LEVEL=info, TZ=America/Sao_Paulo.
  Restart unless-stopped.  Healthcheck: curl localhost:8191 every 30s, timeout 10s,
  3 retries, 15s start period.

FlareSolverr is used to bypass Cloudflare protection when scraping HLTV.org for
professional player statistics.

### A.11  schema.py

Master Database & Migration Suite (328 lines).  Usage: `python schema.py {inspect|migrate|import|fix|reset}`.

**Module-level constants**:
- `_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")` -- SQL identifier validation.
- `_SAFE_COL_TYPE_RE = re.compile(r"^[A-Z]+(?: DEFAULT [0-9.]+)?$")` -- column type whitelist.
- `PROJECT_ROOT` -- derived from `__file__`.
- `DB_PATH` -- `PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"`.
- `KNOWLEDGE_DB_PATH` -- `PROJECT_ROOT / "Programma_CS2_RENAN" / "knowledge_graph.db"`.

**Class `SchemaSuite`**:
- `__init__(self)`: Sets db_path and knowledge_db_path.
- `_validate_identifier(name: str) -> str`: Static method. Validates SQL identifier
  against `_IDENTIFIER_RE`.  Raises ValueError for unsafe identifiers.
- `_safe_pragma_table_info(cursor, table) -> list`: Executes `PRAGMA table_info` with
  validated identifier (bracket-quoted).
- `_safe_select_count(cursor, table) -> int`: `SELECT COUNT(*)` with validated identifier.
- `_safe_alter_add_column(cursor, table, col_name, col_type)`: ALTER TABLE ADD COLUMN
  with all identifiers validated and column type checked against `_SAFE_COL_TYPE_RE`.
- `_get_connection(db_path=None)`: Opens sqlite3 connection. Exits if DB not found.
- `run_inspect(target="main")`: Prints journal mode, table count with column counts,
  total index count.  Supports "main" and "knowledge" targets.
- `run_migrate()`: If DB missing, calls `init_database()`.  Otherwise applies column
  migrations: `coachstate.current_epoch` (INTEGER DEFAULT 0), `coachstate.train_loss`
  (FLOAT DEFAULT 0.0), `playertickstate.demo_name` (TEXT).
- `_apply_column_migration(table, col_name, col_type)`: Check-then-add column pattern.
- `run_import(source_path)`: Imports data from external DB.  Transfers `playerprofile`
  and `playermatchstats` tables using INSERT OR IGNORE.
- `_transfer_table(table, src, dest)`: Table-by-table transfer with row count reporting.
- `run_fix(fix_type="all")`: Resets SQLite sequences with backup to
  `_sqlite_sequence_backup` table.
- `run_reset(target="alembic")`: Drops alembic_version table or clears coachstate.

**Function `main()`**: Argparse CLI with 5 subcommands (inspect, migrate, import, fix,
reset).

### A.12  setup.py

Minimal backward-compatibility shim: `from setuptools import setup; setup()`.
All real configuration lives in pyproject.toml.

### A.13  launch.sh

Bash script for Qt application launch:

1. Sets `set -e` (exit on error).
2. Locates `.venv/bin/python3` relative to script.
3. Verifies Python >= 3.10 via `sys.version_info.minor`.
4. Clears stale `__pycache__` directories under `Programma_CS2_RENAN`.
5. Sets `QT_QUICK_BACKEND=software` (prevents segfault on some Linux GPU drivers).
6. Sets `QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu"`.
7. Executes `python -m Programma_CS2_RENAN.apps.qt_app.app`.

### A.14  train.sh

Bash script for full-cycle AI training:

- Supports short flags (-d dry-run, -r resume, -T no-tensorboard, -e epochs,
  -m model-type, -t tb-logdir) rewritten to canonical long forms.
- Default EPOCHS=100, MODEL_TYPE=all.
- Venv at `$HOME/.venvs/cs2analyzer/bin/python`.
- Logs to `logs/train_<timestamp>.log`.
- Pipes through `tee` and captures exit code via `PIPESTATUS[0]`.

### A.15  ingest.sh

Bash script for one-shot pro-demo ingestion:

- Supports `--show-status` (inline Python snippet that queries IngestionTask counts
  from database.db in read-only mode).
- Short flags: -w workers, -l limit, -D demo-dir, -v verbose (sets CS2_LOG_LEVEL=DEBUG).
- Always passes `--no-train` to `batch_ingest.py`.
- Logs to `logs/ingest_<timestamp>.log`.

### A.16  train_docker.sh

Docker GPU training wrapper for ROCm:

- Uses `rocm/pytorch:latest` image.
- Mounts project root and data root as `/workspace`.
- Copies `hflayers` from local venv (not on PyPI).
- Passes `--device=/dev/kfd --device=/dev/dri --group-add video --shm-size=8g`.
- Sets PYTHONPATH, PRO_DEMO_PATH, PYTORCH_CUDA_ALLOC_CONF, keyring backend.
- Installs project deps from `.cs2_req_no_torch.txt` and `ncps`.
- Verifies GPU before training.
- Target: RX 9070 XT (gfx1201, native ROCm 7.2 support).

### A.17  _rocm_smoke.sh

ROCm + PyTorch GPU smoke test:

- Runs `rocminfo`, `rocm-smi` for GPU state.
- Python script verifies `torch.version.hip`, `torch.cuda.is_available()`,
  device properties (gcnArchName, total_mem, multi_processor_count).
- Fails with explicit message if GPU not detected (gfx1201 Navi 48).
- Minimal compute test: 2048x2048 matrix multiply on CUDA.

---

## Part B -- Package Root

### B.1  Programma_CS2_RENAN/__init__.py

Single line: `__version__ = "1.0.0"`.  This is the package initialization marker.
The version string is consumed by Sentry setup (`sentry_setup.py:101`).

### B.2  Programma_CS2_RENAN/core/__init__.py

Empty file.  Marks `core` as a Python package.

---

## Part C -- Core Module: Types and Enums

### C.1  core/app_types.py

Central type definitions with careful enum separation.

**NewType aliases**:
- `MatchID = NewType("MatchID", int)`
- `Tick = NewType("Tick", int)`
- `PlayerID = NewType("PlayerID", int)`

**Class `Team(Enum)`** -- Numeric team identifiers (SPECTATOR=0, T=1, CT=2):
- Custom `__eq__`: Raises `TypeError` with code AT-01 if compared against a different
  `Team` enum from another module (cross-enum comparison guard).  Checks
  `type(other).__name__ == "Team"` and `type(other).__module__ != type(self).__module__`.
- Custom `__hash__`: Delegates to `Enum.__hash__`.

**Class `PlayerRole(str, Enum)`** -- P3-01 canonical role classification:
- Values: ENTRY="entry", AWPER="awper", SUPPORT="support", LURKER="lurker", IGL="igl",
  FLEX="flex", UNKNOWN="unknown".
- Property `display_name -> str`: Returns human-readable names via lookup dict
  (e.g., "entry" -> "Entry Fragger", "awper" -> "AWPer").

**Class `IngestionStatus(Enum)`**: QUEUED, PROCESSING, COMPLETED, FAILED (auto-valued).

**Class `DemoMetadata(TypedDict)`**: demo_name, map_name, tick_rate (float), total_ticks
(int), processed_at (str), is_pro (bool), last_tick_processed (int).

**Class `PlayerStats(TypedDict)`**: name, kills, deaths, adr (float), hs_percent (float),
kast (float), rating (float).

**Function `team_from_demo_frame(demo_team) -> Team`**: R1-02 safe bridge between
string-valued `demo_frame.Team` and numeric `app_types.Team`.  Accepts enum or raw
string.  Raises ValueError for unknown values (fail-fast).

### C.2  core/demo_frame.py

Data models for a single tick of a CS2 demo.  All dataclasses.

**Class `Team(Enum)`** -- String values for demo parser compatibility:
- CT="ct", T="t", SPECTATOR="spectator".
- R1-02 docstring warning about the separate numeric Team in app_types.py.

**Class `PlayerState`** (dataclass):
- Fields: player_id (int), name (str), team (Team), x/y/z (float), yaw (float),
  hp (int), armor (int), is_alive/is_flashed/has_defuser (bool), weapon (str),
  money (int).
- Optional fields with defaults: kills=0, deaths=0, assists=0, mvps=0,
  inventory (List[str]), is_crouching=False, is_scoped=False, equipment_value=0.
- `__post_init__`: DF-01 sanitization -- replaces NaN/Inf coordinates (x, y, z) with
  0.0 to prevent downstream spatial calculation failures.

**Class `GhostState`** (dataclass): player_id, name, team, x, y, yaw, is_paused=False,
manual_offset_x=0.0, manual_offset_y=0.0.  Used for selectable/draggable
previous-round shadows.

**Class `NadeType(str, Enum)`**: SMOKE, MOLOTOV, FLASH, HE, DECOY.

**Class `NadeState`** (frozen dataclass): base_id (entity ID), nade_type, x/y/z,
starting_tick, ending_tick, throw_tick (Optional), trajectory (List[tuple]),
thrower_id (Optional), is_duration_estimated (bool, H-05 flag).

**Class `EventType(str, Enum)`**: KILL, BOMB_PLANT, BOMB_DEFUSE, ROUND_START, ROUND_END.

**Class `GameEvent`** (frozen dataclass): tick, event_type, x=0.0, y=0.0, details="".

**Class `BombState`** (dataclass): x, y, z, is_planted, is_defused,
time_remaining (Optional float).

**Class `KillEvent`** (dataclass): killer_id, victim_id, weapon, is_headshot, is_wallbang.

**Class `DemoFrame`** (dataclass): tick, round_number, time_in_round (float), map_name
(str), players (List[PlayerState]), nades (List[NadeState]), bomb (Optional[BombState]),
kills (List[KillEvent]).  Metadata flags: is_round_start, is_round_end, is_bomb_plant.

---

## Part D -- Core Module: Configuration

### D.1  core/config.py

Central configuration module.  504 lines.  Handles settings persistence, path
resolution, credential management, and module-level global variables.

**Environment Detection**:
- `IS_FROZEN = getattr(sys, "frozen", False)` -- PyInstaller detection.
- `_settings_lock = threading.RLock()` -- Reentrant lock for thread-safe settings access.

**Function `stabilize_paths() -> str`**: Standardizes sys.path and returns project root.
Computed by navigating two directories up from `__file__`.

**Function `get_base_dir() -> str`**: Returns parent of core/ folder (i.e.,
Programma_CS2_RENAN/) for source mode, or executable directory for frozen mode.

**Constant `BASE_DIR`**: Result of `get_base_dir()`.

**Function `get_writeable_dir() -> str`**: Returns LOCALAPPDATA/MacenaCS2Analyzer for
frozen mode, BASE_DIR for source mode.

**Constants**:
- `STORAGE_ROOT`: Initially from `get_writeable_dir()`, later reassigned to
  `USER_DATA_ROOT`.
- `SETTINGS_PATH`: `get_writeable_dir() / "user_settings.json"`.  Computed before
  STORAGE_ROOT reassignment to stay stable.

**Function `get_resource_path(relative_path) -> str`**: Returns absolute path to
read-only resources.  Uses `sys._MEIPASS` for frozen mode.

**Keyring Integration**:
- `import keyring` with `ImportError` fallback (C-03 warning).
- `get_secret(key, default) -> str`: Retrieves from OS keyring
  ("MacenaCS2Analyzer" service).  Returns default on missing.  Logs errors but doesn't
  crash.
- `set_secret(key, value) -> bool`: Stores in keyring.  Returns False if unavailable.
  Raises RuntimeError on storage failure.
- `mask_secret(value) -> str`: Returns "first4...last4" or "****" for short values.

**Function `load_user_settings() -> dict`**: Under `_settings_lock`:
1. Defines comprehensive defaults dict with 40+ keys (CS2_PLAYER_NAME, STEAM_ID,
   API keys, paths, UI preferences, ML flags, coaching flags, dock settings, LLM model).
2. Reads SETTINGS_PATH JSON, merges with defaults.
3. Docker/CI override: PATH-based settings (PRO_DEMO_PATH, DEFAULT_DEMO_PATH,
   BRAIN_DATA_ROOT, CUSTOM_STORAGE_PATH) can be overridden by environment variables.
4. Keyring retrieval: STEAM_API_KEY, FACEIT_API_KEY, STORAGE_API_KEY read from keyring.
   Disk value "PROTECTED_BY_WINDOWS_VAULT" treated as empty fallback.

**Constants** (module-level convenience, C-01 warning about staleness):
- CS2_PLAYER_NAME, STEAM_ID, STEAM_API_KEY, FACEIT_API_KEY, DEFAULT_DEMO_PATH,
  PRO_DEMO_PATH, BRAIN_DATA_ROOT.
- MIN_DEMOS_FOR_COACHING=1, MAX_DEMOS_PER_MONTH=10, MAX_TOTAL_DEMOS_PER_USER=100.

**Function `_resolve_match_data_path() -> str`**: Uses PRO_DEMO_PATH/match_data if
available, else in-project backend/storage/match_data.

**Path Architecture** (critical comment block):
- CORE_DB_DIR always in project folder (single source of truth for training data).
- USER_DATA_ROOT uses BRAIN_DATA_ROOT if available, else CUSTOM_STORAGE_PATH, else
  BASE_DIR.
- DB_DIR = CORE_DB_DIR (core database always in project folder).
- LOG_DIR, DATA_DIR, MODELS_DIR, RUNS_DIR under USER_DATA_ROOT.
- All directories created with `os.makedirs(exist_ok=True)`.
- `configure_log_dir(LOG_DIR)` wired to logger_setup to break circular import.

**Database URLs**:
- `DATABASE_URL`: `sqlite:///Programma_CS2_RENAN/backend/storage/database.db`
- `KNOWLEDGE_DATABASE_URL`: `sqlite:///<DATA_DIR>/knowledge_base.db`
- `HLTV_DATABASE_URL`: `sqlite:///<CORE_DB_DIR>/hltv_metadata.db`

**Thread-safe accessor functions**:
- `get_setting(key, default=None) -> Any`: Reads `_settings` under lock.
- `get_pro_demo_base() -> Path`: Resolves PRO_DEMO_PATH with DP-06 auto-detection
  (scans /media/<user>/*/ for Counter-Strike-coach-AI directory structure when
  configured path doesn't exist).
- `get_credential(key) -> str`: Thread-safe credential lookup for daemon threads (C-01).
- `refresh_settings()`: Reloads from disk under lock, updates all global variables.
- `get_all_settings() -> dict`: Returns thread-safe copy.

**Function `save_user_setting(key, value)`**: Under `_settings_lock`:
1. Routes API keys (STEAM_API_KEY, FACEIT_API_KEY, STORAGE_API_KEY) through keyring.
   On success, replaces value with "PROTECTED_BY_WINDOWS_VAULT" for disk storage.
2. Reads existing settings, updates key, writes atomically via temp file + os.replace.
3. `os.chmod(SETTINGS_PATH, 0o600)` for FE-04 security (POSIX-only).
4. Keeps original unmasked value in `_settings` and globals for current session.

### D.2  core/constants.py

Project-wide temporal and spatial constants.  All derived tick values computed from
seconds at import time using `TICK_RATE`.

**Constants**:
- `TICK_RATE: int = 64` -- CS2 standard tick rate.
- `FOV_DEGREES: float = 90.0` -- Standard CS2 horizontal FOV.
- `Z_FLOOR_THRESHOLD: float = 200.0` -- Minimum Z-distance for different floors (H-11).
- Utility durations in seconds and ticks:
  - `SMOKE_DURATION_S = 18.0` -> `SMOKE_MAX_DURATION_TICKS = 1152`
  - `MOLOTOV_DURATION_S = 7.0` -> `MOLOTOV_MAX_DURATION_TICKS = 448`
  - `FLASH_DURATION_S = 2.0` -> `FLASH_DURATION_TICKS = 128`
- Memory decay constants:
  - `MEMORY_DECAY_TAU_S = 2.5` -> `MEMORY_DECAY_TAU_TICKS = 160`
  - `MEMORY_CUTOFF_S = 7.5` (L-28: 3*tau) -> `MEMORY_CUTOFF_TICKS = 480`
- Trade kill: `TRADE_WINDOW_S = 3.0` -> `TRADE_WINDOW_TICKS = 192`

---

## Part E -- Core Module: Spatial Systems

### E.1  core/spatial_data.py

Map metadata and coordinate transformations.  422 lines.

**Module-level constants**:
- `Z_LEVEL_THRESHOLD = 200` -- Relative Z units separating level floors.
- `Z_PENALTY_FACTOR = 2.0` -- Multiplier for cross-level distance.

**Class `MapMetadata`** (frozen dataclass):
- Fields: pos_x, pos_y (top-left corner in world space), scale (world units per pixel),
  z_cutoff (Optional float for multi-level maps), level ("default"/"upper"/"lower").
- `world_to_radar(x, y, radar_width=1024) -> (float, float)`: Converts Source 2 world
  coordinates to normalized radar coordinates (0.0-1.0).  Formula:
  `pixel_x = (x - pos_x) / scale; norm_x = pixel_x / radar_width`.  Y-axis inverted:
  `pixel_y = (pos_y - y) / scale`.
- `radar_to_world(norm_x, norm_y, radar_width=1024) -> (float, float)`: Inverse
  transformation.
- Property `is_multi_level -> bool`: True if z_cutoff is not None.

**Fallback Registry** (`_FALLBACK_REGISTRY`): 11 entries for 9 maps.  Standard maps
(de_mirage, de_inferno, de_dust2, de_overpass, de_ancient, de_anubis, de_train) have
single-level metadata.  Multi-level maps have paired entries:
- de_nuke (z_cutoff=-495, level="upper") + de_nuke_lower (level="lower")
- de_vertigo (z_cutoff=11700, level="upper") + de_vertigo_lower (level="lower")

**Fallback Landmarks** (`_FALLBACK_LANDMARKS`): de_mirage (5), de_dust2 (5), de_nuke (5)
with (x, y) world coordinates for T-Spawn, CT-Spawn, sites, mid.

**Fallback Competitive Maps**: 9 maps (nuke, inferno, mirage, dust2, ancient, overpass,
vertigo, anubis, train).

**Class `SpatialConfigLoader`** (singleton):
- Thread-safe via double-checked locking with `_loader_lock`.
- `_load_config()`: Loads from `data/map_config.json` with fallback to hardcoded
  defaults.  SD-02: validates numeric types before constructing MapMetadata.
- `reload()`: Force reload under lock.

**Module-level accessor functions**:
- `__getattr__(name)`: Lazy-loads SPATIAL_REGISTRY, LANDMARKS, COMPETITIVE_MAPS from
  the singleton loader.
- `get_map_metadata(map_name) -> MapMetadata | None`: Cleans name (lowercase, removes
  extensions/prefixes), tries exact match, then partial match.  SD-03: warns on
  ambiguous partial matches.  Skips `_lower` variants for default lookup.
- `get_map_metadata_for_z(map_name, z) -> MapMetadata | None`: Automatic level selection
  based on Z coordinate.  Returns lower variant if z < z_cutoff.
- `is_multi_level_map(map_name) -> bool`: Checks z_cutoff via dynamic registry.
- `get_landmarks(map_name) -> Dict[str, tuple[float, float]]`.
- `reload_spatial_config()`: Force reload.
- `classify_vertical_level(z_position, map_name, transition_band=50.0) -> str`: Returns
  "upper", "lower", "transition", or "default".
- `compute_z_penalty(z_position, map_name) -> float`: Normalized penalty [0.0, 1.0]
  based on distance from z_cutoff.  0.0 for single-level maps.  Saturates at 500 units.

### E.2  core/spatial_engine.py

Coordinate transformation engine.  93 lines.

**Constant**: `RADAR_REFERENCE_SIZE = 1024.0` -- must match MapMetadata.world_to_radar
default.

**Class `SpatialEngine`** (all static methods):
- `world_to_normalized(x, y, map_name) -> (float, float)`: Delegates to
  `MapMetadata.world_to_radar()`.  Returns (0.5, 0.5) if map unknown.  F6-26: Z
  coordinate ignored (multi-level maps projected to single 2D plane).
- `normalized_to_pixel(nx, ny, viewport_w, viewport_h) -> (float, float)`: Linear
  scaling.
- `pixel_to_normalized(px, py, viewport_w, viewport_h) -> (float, float)`: Inverse
  linear scaling.  Returns (0.0, 0.0) for zero-sized viewport.
- `world_to_pixel(x, y, map_name, viewport_w, viewport_h) -> (float, float)`:
  Composition of world_to_normalized + normalized_to_pixel.
- `pixel_to_world(px, py, map_name, viewport_w, viewport_h) -> (float, float)`:
  Inverse using `scale * RADAR_REFERENCE_SIZE` formula.

### E.3  core/map_callouts.py

Coordinate-to-callout translation.  374 lines.  WR-77: single source of truth.

**Class `NamedPosition`** (frozen dataclass): name, map_name, center_x, center_y,
center_z, radius, level="default".

**Hardcoded positions** (`_NAMED_POSITIONS`): ~160 callout positions across 9 maps:
- de_mirage (23): A Site, B Site, Mid, A Ramp, B Apartments, Window, Connector, Jungle,
  Palace, T Spawn, CT Spawn, Underpass, Catwalk, Short, Top Mid, B Short, Market,
  Kitchen, Van, Ticket Booth, Triple Box, Firebox, Stairs.
- de_inferno (21): A/B Sites, Banana, Mid, Apartments, Pit, Library, CT/T Spawn, Arch,
  Boiler, Dark, Construction, Graveyard, Balcony, Second Mid, Top/Bottom Banana, Car,
  Coffins, Moto.
- de_dust2 (22): A/B Sites, Mid Doors, Long A, Short A, B Tunnels, CT/T Spawn, A Long
  Doors, A Cross, Platform, Goose, Pit, Car, B Window, B Closet, B Back Site,
  Upper/Lower Tunnels, T Mid, Xbox, Palm.
- de_anubis (15): A/B Sites, Mid, Canal, CT/T Spawn, A/B Main, Connector, A Long,
  Palace, Bridge, Water, Ruins, Alley.
- de_nuke (19): A Site (Upper), B Site (Lower), Ramp, Outside, Secret, Heaven, Hell,
  Vent, Lobby, Radio, Hut, Garage, T Roof, CT/T Spawn, Squeaky, Main, Mini, Decon.
  Level annotations present.
- de_ancient (14), de_overpass (18), de_vertigo (12), de_train (15).

**Class `NamedPositionRegistry`**:
- `__init__()`: Copies hardcoded positions, builds by-map index, loads JSON extensions.
- `_rebuild_index()`: Groups positions by map_name.
- `_load_json_extensions()`: Auto-loads from `data/map_callouts.json` if present.
- `get_positions(map_name) -> List[NamedPosition]`.
- `find_nearest(map_name, x, y, z=0.0, max_distance=600.0) -> Optional[NamedPosition]`:
  Linear scan with Euclidean distance.  Returns closest within max_distance.
- `add_position(position)`: Appends and rebuilds index.
- `load_from_json(json_path) -> int`: Loads positions from JSON file with error handling.

**Module-level API**:
- `_registry: Optional[NamedPositionRegistry] = None` -- lazy singleton.
- `get_callout_registry() -> NamedPositionRegistry`: Creates or returns singleton.
- `get_callout(map_name, x, y, z=0.0, max_distance=600.0) -> str`: Returns callout name
  or "unknown area".

---

## Part F -- Core Module: Asset Management

### F.1  core/asset_manager.py

Unified Asset Authority.  258 lines.  Replaces former AsyncMapRegistry and MapAssetManager.

**Class `SmartAsset`** (dataclass):
- Fields: path (str), theme="regular", is_fallback=False, _texture (Optional Kivy
  Texture, lazy-loaded).
- Property `texture -> Optional[Texture]`: Lazy-loads on first access.  Fallback assets
  get checkered texture.  File assets loaded via `CoreImage`.  Missing files fall back
  to checkered texture.
- Property `exists -> bool`: `os.path.exists(path) and not is_fallback`.

**Class `AssetAuthority`** (singleton via `__new__`):
- Class-level `_cache: Dict[str, SmartAsset]` (F6-32 note about singleton safety).
- Class-level `_fallback_texture: Optional[Texture]`.
- `get_maps_directory() -> str`: Returns `PHOTO_GUI/maps` via `get_resource_path`.
- `get_map_asset(map_name, theme="regular") -> SmartAsset`: Normalizes name, checks
  cache, builds path with theme suffix (_dark, _light), falls back to regular theme,
  then to fallback asset.
- `_normalize_map_name(map_name) -> str`: Handles "mirage", "de_mirage", "de_mirage.dem",
  "maps/de_mirage" -> "de_mirage".  Uses SPATIAL_REGISTRY for validation and partial
  matching.
- `_create_fallback_asset() -> SmartAsset`: Checkered fallback with `is_fallback=True`.
- `_generate_checkered_texture() -> Texture`: 64x64 magenta/black 8x8 checkerboard
  pattern in RGB.  Cached as class-level singleton.  Superior to old "Mirage fallback"
  because it clearly indicates missing data.
- `clear_cache()`: Clears both asset cache and fallback texture.

**Class `MapAssetManager`** (DEPRECATED):
- `get_map_source(map_name) -> str`: Delegates to AssetAuthority.
- `_get_fallback() -> str`: Delegates to AssetAuthority.

### F.2  core/map_manager.py

High-level interface wrapping AssetAuthority with Kivy async loading.  97 lines.

**Class `MapManager`** (all static methods):
- `get_map_path(map_name, theme="regular") -> str`: Returns absolute path.
- `get_map_asset(map_name, theme="regular") -> SmartAsset`: Returns SmartAsset.
- `load_map_async(map_name, callback, theme="regular")`: Async Kivy texture loading.
  MM-01: Logs warning when fallback is used, schedules callback via Clock for
  consistency.  Returns ProxyImage for load-state tracking, or None for fallbacks.
- `get_map_metadata(map_name)`: Delegates to `spatial_data.get_map_metadata()`.

---

## Part G -- Core Module: Application Lifecycle

### G.1  core/frozen_hook.py

PyInstaller/Windows compatibility hook.  17 lines.  Called at import time (`hook()`
invoked at module level).

**Function `hook()`**:
1. `multiprocessing.freeze_support()` -- mandatory for Windows compiled binaries using
   daemons/workers.
2. If frozen: `os.chdir(sys._MEIPASS)` -- sets working directory to PyInstaller
   extraction folder for relative paths.

### G.2  core/lifecycle.py

Centralized application lifecycle controller.  168 lines.

**Class `AppLifecycleManager`**:
- Class attributes: `_instance_mutex = None`, `_daemon_process = None`.
- `__init__()`: Sets `mutex_name = "Global\\MacenaCS2Analyzer_Unique_Lock_v1"`,
  computes `project_root` (3 levels up from __file__).  Pre-initializes `_out_log` and
  `_err_log` to None (CORE-12: prevents AttributeError on first launch_daemon call).

- `ensure_single_instance() -> bool`: Windows Named Mutex via ctypes.  Returns True if
  sole instance, False if ERROR_ALREADY_EXISTS (183).  Non-Windows: no-op (returns True).
  Catches OSError and AttributeError; fails closed (returns False) to protect DB.

- `launch_daemon() -> Optional[Popen]`: Launches `session_engine.py` as subprocess.
  - Skips if daemon already running (`poll() is None`).
  - CORE-12: Closes old log handles before opening new ones on re-launch.
  - Opens `daemon_out.log` and `daemon_err.log` at project root.
  - `subprocess.Popen` with PYTHONPATH injection, stdin=PIPE (IPC capability).
  - Registers `self.shutdown` via `atexit`.
  - Catches OSError/ValueError/SubprocessError; closes file handles on failure.

- `shutdown()`: Graceful termination sequence:
  1. `terminate()` with 3s timeout.
  2. Force `kill()` if resistant.
  3. Closes daemon log handles.
  4. Releases Windows mutex via `CloseHandle`.

**Global Singleton**: `lifecycle = AppLifecycleManager()`.

### G.3  core/session_engine.py

The Session Engine daemon -- backbone of background processing.  597 lines.

**Module-level path bootstrap** (F6-06): Adds project root to sys.path for direct
script execution.

**Threading events**:
- `_shutdown_event = threading.Event()` -- signals all daemons to stop.
- `_work_available_event = threading.Event()` -- wakes Digester daemon.
- `_backup_failed = threading.Event()` -- F6-SE flag for Teacher warning.

**Function `_monitor_stdin()`**: Reads stdin for "STOP" command or pipe close
(parent-death detection).  Sets `_shutdown_event` on either condition.

**Function `signal_work_available()`**: Sets `_work_available_event`.

**Function `run_session_loop()`**: Main entry point.  Flow:
1. `init_database()` -- ensures DB tables exist.
2. Automated backup via `BackupManager.should_run_auto_backup()` /
   `create_checkpoint("startup_auto")`.
3. H-02: One-time knowledge base population (checks TacticalKnowledge count).
4. Starts stdin monitor thread (life-line to parent process).
5. Resets status via state_manager.
6. `_cleanup_zombie_tasks()`.
7. Starts IngestionWatcher.
8. Launches 4 daemon threads: Scanner, Digester, Teacher, Pulse.
9. Main keep-alive loop with SE-WD watchdog (30s interval): restarts dead daemon
   threads.
10. Graceful shutdown: sets _shutdown_event, stops watcher, joins threads (5s timeout).

**Function `_cleanup_zombie_tasks()`**: P4-B configurable threshold
(`_ZOMBIE_THRESHOLD_SECONDS = 1800`, overridable via `ZOMBIE_TASK_THRESHOLD_SECONDS`
setting).  SE-04: validates type and range.  Resets tasks stuck in 'processing' state
beyond threshold.

**Function `_check_disk_space(path, min_gb=5)`**: Warns and sends notification if
free space below threshold.

**Four Daemon Loops**:

1. **`_scanner_daemon_loop()`** (DAEMON A -- File Scanner "The Gatekeeper"):
   - SCAN_INTERVAL = 10s, DISK_CHECK_INTERVAL = 300s.
   - OBS-07: Sets correlation ID per cycle.
   - SE-07: Refreshes settings once per cycle.
   - Calls `process_new_demos(is_pro=True/False)`.
   - Attempts Steam auto-discovery via `find_cs2_replays()`/`sync_steam_demos()`.
   - 1s idle sleep between cycles.

2. **`_digester_daemon_loop()`** (DAEMON B -- Processing Worker):
   - Processes 1 task at a time (`process_queued_tasks(limit=1)`) for pro and user demos.
   - IM-03: Event wait-then-clear ordering to prevent lost wakeup signals.
   - 2s timeout on `_work_available_event.wait()`.

3. **`_teacher_daemon_loop()`** (DAEMON C -- Cognitive ML Trainer):
   - F6-SE: Warns once if backup failed.
   - NN-02: Acquires `_TRAINING_LOCK` before training (prevents concurrent with
     Console-triggered MLController).
   - Runs `CoachTrainingManager().run_full_cycle()`.
   - Commits trained sample count after success.
   - Meta-shift detection (Proposal 11) via `TemporalBaselineDecay`.
   - G-07: Belief calibration after each retraining cycle.
   - 300s wait between cycles.

4. **`_pulse_daemon_loop()`**: Heartbeat update every 5s via `get_state_manager().heartbeat()`.

**Helper functions**:
- `_get_current_baseline_snapshot() -> dict`: Captures temporal baseline.
- `_check_meta_shift(old_baseline) -> dict`: Compares baselines, logs shifts.
- `_check_retraining_trigger() -> int`: Returns pro_count when retraining needed
  (>= 110% of last trained count, or first 10 samples).
- `_commit_trained_sample_count(count)`: Persists count to CoachState.

---

## Part H -- Core Module: Playback and Interpolation

### H.1  core/playback_engine.py

Demo playback engine with frame interpolation.  257 lines.

**Class `InterpolatedPlayerState`** (dataclass): All PlayerState fields plus
`is_ghost: bool = False`.

**Class `InterpolatedFrame`** (dataclass): tick (int), players
(List[InterpolatedPlayerState]), nades (List[NadeState]).

**Class `PlaybackEngine`**:
- `SPEED_NORMAL = 1.0`.
- `__init__()`: Initializes _frames, _current_index, _sub_tick (float 0-1 between
  frames), _is_playing, _speed, _clock_event, _on_frame_update callback, _tick_rate=64.
- `load_frames(frames, tick_rate=64)`: Stores frames and builds `_ticks_cache` list.
- `set_on_frame_update(callback)`: Registers frame update callback.
- `play()`: Starts Kivy Clock interval at ~60 FPS.  Loops to start if at end.
  Falls back to warning if Kivy unavailable.
- `pause()`: Cancels clock event.
- `toggle_play_pause()`.
- `set_speed(speed)`: Clamped to [0.25, 8.0].
- `seek_to_tick(tick)`: Binary search via `bisect.bisect_left` on cached ticks.
- `get_current_tick() -> int`, `get_total_ticks() -> int`, `is_playing() -> bool`.
- `_tick(dt)`: Advances _sub_tick by `dt * tick_rate * speed`.  Advances frame index
  when sub_tick >= 1.0.  Pauses at end.
- `_emit_frame()`: Calls callback with interpolated frame.
- `_interpolate_players(current, next_, t)`: Per-player linear interpolation of x/y/z
  and angle.  HP interpolated linearly.  Flash state ORed between frames.
- `_player_to_interpolated(p)`: Direct conversion without interpolation.
- `_interpolate_angle(a, b, t)` (static): CORE-10 NaN sanitization.  Handles 360-degree
  wraparound by normalizing diff to [-180, 180].

---

## Part I -- Core Module: Localization

### I.1  core/localization.py

Multilingual i18n system.  452 lines.  Supports English, Portuguese, Italian.

**Hardcoded `TRANSLATIONS` dict**: Three top-level keys ("en", "pt", "it"), each with
~90 translation keys covering: app_name, dashboard, coaching, settings, profile,
upload rules, visual theme, analysis paths, appearance, language, wallpaper controls,
folder selection, font settings, pro knowledge, personalization, tactical analysis,
coach status, belief state, inference stability, learning intensity, pro comparison,
audit path, Steam/FaceIT integration, wizard steps (intro, step1 brain storage, step2
demo folder, finish), tactical analyzer, quick actions (F7-17), UI strings (F7-18),
search (F7-26), baseline degraded warning (P10-03), dialog strings (F10-01).

**Function `_load_json_translations() -> dict`**: Loads from `assets/i18n/{lang}.json`.
Expands `{home_dir}` placeholders.

**Kivy compatibility layer**: If Kivy is loaded, inherits from EventDispatcher with
StringProperty.  Otherwise, uses plain object with lambda stub for StringProperty.

**Class `LocalizationManager(EventDispatcher)`**:
- `lang = StringProperty("en")`.
- `get_text(key, trigger=None) -> str`: LOC-02 priority chain:
  1. JSON (current lang)
  2. Hardcoded (current lang)
  3. Hardcoded English fallback
  4. Raw key with LOC-03 debug log.
- `set_language(lang_code)`: Updates `lang` if code exists in either dict.

**Singleton**: `i18n = LocalizationManager()`.

---

## Part J -- Core Module: Lock Files and Concurrency

### J.1  core/lock_files.py

Lock file utilities for D-track / HLTV-track concurrency.  150 lines.

**Design**: Repo-local `.locks/` directory (survives sessions, not reboots).  Lock file
format: `<pid> <iso_timestamp>`.  Stale locks reclaimed if holder PID is dead.

**Module-level state**:
- `_LOCK_DIR = Path(__file__).resolve().parents[2] / ".locks"`.
- `_held_locks: Set[str]` -- tracks currently held lock names.

**Class `LockConflict(RuntimeError)`**: Raised when lock held by live process.

**Functions**:
- `_lock_path(name) -> Path`: Sanitizes name (replaces `/`, `..`, os.sep with `_`).
- `_read_lock(path) -> Optional[Tuple[int, str]]`: Parses pid and timestamp from lock
  file.
- `_is_pid_alive(pid) -> bool`: Uses `os.kill(pid, 0)` liveness probe.
  ProcessLookupError = dead, PermissionError = alive (different user).
- `acquire(name) -> Path`: Creates lock directory, checks for existing lock, reclaims
  if stale.  Writes PID + ISO timestamp.  Adds to `_held_locks`.
- `release(name)`: Unlinks lock file.  Idempotent.
- `is_held(name) -> bool`: Checks if live process holds lock.
- `holder_pid(name) -> Optional[int]`: Returns PID or None.
- `lock(name)` (context manager): Acquire on enter, release on exit.
- `_release_all_on_signal(signum, _frame)`: Releases all held locks, re-raises original
  signal with default disposition.
- `install_signal_handlers()`: Installs SIGTERM/SIGINT handlers.  Idempotent.

---

## Part K -- Core Module: Platform Utilities

### K.1  core/platform_utils.py

Drive detection and platform identification.  85 lines.

**Function `_get_platform() -> str`**: Returns "win", "macosx", "linux", or raw
sys.platform.

**Module-level constant**: `platform = _get_platform()`.

**Function `get_available_drives() -> List[str]`**:
- PU-02: Explicit platform handling.
- Windows: `_get_windows_drives()`.
- Linux/macOS: Returns `["/"]`.
- Other: Falls back to validated home directory.

**Function `_get_windows_drives() -> List[str]`**:
1. ctypes `GetLogicalDrives()` bitmask, validates each drive with `os.path.isdir`.
2. Fallback: `psutil.disk_partitions()` for writable partitions.
3. Final fallback: home directory or `"C:\\"`.

---

## Part L -- Core Module: Registry

### L.1  core/registry.py

KivyMD Screen registration system.  53 lines.

**`_registry_lock = threading.Lock()`**: REG-01 thread safety.

**Class `ScreenRegistry`**:
- Class-level `_mapping: Dict[str, Type[MDScreen]]`.
- `register(name)` (classmethod decorator): Thread-safe registration.  Raises KeyError
  on duplicate.
- `get_screen_class(name) -> Optional[Type[MDScreen]]`: Thread-safe lookup.
- `list_screens() -> List[str]`: Returns sorted names.

**Global**: `registry = ScreenRegistry()`.

---

## Part M -- Observability Module

### M.1  observability/__init__.py

Empty file.  Marks `observability` as a Python package.

### M.2  observability/error_codes.py

Centralized Error Code Registry.  308 lines.

**Class `Severity(Enum)`**: LOW, MEDIUM, HIGH, CRITICAL.

**Class `ErrorCodeDef(NamedTuple)`**: code (str), severity (Severity), module (str),
description (str), remediation (str).

**Class `ErrorCode(Enum)`**: 24 registered error codes across 8 prefixes:
- **LS (Logger Setup)**: LS_01 -- RotatingFileHandler unavailable (MEDIUM).
- **RP (RASP)**: RP_01 -- CS2_MANIFEST_KEY not set (HIGH).
- **DA (Data Access)**: DA_01_03 -- Malformed JSON from DB (LOW).
- **P (Pipeline)**: P0_07 (LOW), P3_01 (LOW), P4_B (MEDIUM), P7_01 (HIGH), P7_02 (HIGH).
- **F (Feature/Fix)**: F6_03, F6_06 (LOW), F6_SE (HIGH), F7_12, F7_19 (LOW), F7_30 (MEDIUM).
- **SE (Session Engine)**: SE_02 (MEDIUM), SE_04 (MEDIUM), SE_05 (HIGH), SE_06 (LOW),
  SE_07 (MEDIUM).
- **IM (Ingestion)**: IM_03 (MEDIUM).
- **NN (Neural Network)**: NN_02 (MEDIUM).
- **G (Game Analysis)**: G_07 (LOW).
- **H (Knowledge/HLTV)**: H_02 (LOW).
- **CO (Console Control)**: CO_01 (HIGH), CO_02 (MEDIUM), CO_03 (HIGH), CO_04 (MEDIUM).
- **R1 (Release/Manifest)**: R1_12 (HIGH).

**Utility functions**:
- `log_with_code(error_code, message) -> str`: Prefixes message with formal code
  (e.g., `[LS-01] message`).
- `get_all_codes() -> list[dict]`: Returns all codes as list of dicts for programmatic
  access.

### M.3  observability/exceptions.py

Domain exception hierarchy.  50 lines.

**Class `CS2AnalyzerError(Exception)`**: Base exception.  Accepts `error_code: ErrorCode | None`.

**Subclasses** (all inherit from CS2AnalyzerError):
- `ConfigurationError` -- Invalid or missing configuration.
- `DatabaseError` -- Database operation failure.
- `IngestionError` -- Demo file ingestion failure.
- `TrainingError` -- ML training pipeline failure.
- `IntegrationError` -- External service integration failure (Steam, FACEIT, HLTV).
- `UIError` -- UI rendering or interaction failure.

### M.4  observability/label_source_monitor.py

G-01 concept-labelling telemetry.  162 lines.

**Constants**:
- `LABEL_SOURCE_ROUND_STATS = "round_stats"`.
- `LABEL_SOURCE_SKIPPED_NO_ROUND_STATS = "skipped_no_round_stats"`.
- `VALID_LABEL_SOURCES` -- frozenset of the above.

**Class `LabelSourceMonitor`**: Thread-safe sliding-window monitor.
- `__init__(window_seconds=300.0, skipped_rate_threshold=0.01, min_samples=50)`:
  - `_events: Deque[Tuple[float, str]]` -- timestamped label source decisions.
  - `_lock: threading.Lock()`.
  - Persistent counters: `total_round_stats`, `total_skipped`.
  - `alarm_active: bool = False` -- one-shot latch.

- `record(label_source, *, ts=None)`: Validates label_source (raises ValueError on
  unknown).  Appends to deque, increments counters, evicts old events, checks alarm.

- `_evict_locked(now)`: Removes events older than `now - window_seconds`.

- `_check_alarm_locked()`: If >= min_samples in window and SKIPPED rate >
  skipped_rate_threshold, fires alarm (sets `alarm_active = True`, logs
  `logger.error` with G-01 prefix).  One-shot: only fires once until reset.

- `check_alarm() -> bool`: Returns alarm state under lock.

- `reset()`: Clears alarm latch and event history.  Persistent counters NOT reset.

- `stats() -> dict`: Snapshot of all monitor state (window_seconds, threshold,
  min_samples, window_samples, window_skipped, rate, alarm_active, totals).

### M.5  observability/logger_setup.py

Centralized logging infrastructure.  327 lines.

**Module-level state**:
- `_log_dir: str | None = None` -- configurable via `configure_log_dir()`.
- `_correlation_local: threading.local()` -- thread-local storage for correlation IDs.

**Correlation ID management**:
- `set_correlation_id(cid=None) -> str`: Sets UUID hex[:12] on current thread.
- `get_correlation_id() -> Optional[str]`: Reads from thread-local.
- **Class `_CorrelationFilter(logging.Filter)`**: Injects correlation_id into every log
  record.

**Class `JSONFormatter(logging.Formatter)`**: Structured JSON output.
- Guaranteed fields: ts, lvl, mod, thread, msg.
- Optional fields: cid (correlation ID), code (error code), exc_type, exc_msg, traceback.
- Uses `json.dumps(log_entry, default=str)`.

**Function `_resolve_log_level() -> int`**: Reads `CS2_LOG_LEVEL` env var, defaults to
INFO.

**Function `configure_log_dir(log_dir)`**: Sets `_log_dir`.  Called by config.py to
break circular import.

**Function `_create_file_handler(log_path, formatter) -> Handler`**:
RotatingFileHandler (5 MB x 3 backups).  LS-01 fallback to plain FileHandler on
PermissionError (Windows daemon handle contention).

**Function `get_logger(name) -> Logger`**: Core factory.
- Returns cached logger if handlers already attached.
- Sets level from `_resolve_log_level()`.
- Attaches JSON file handler to `cs2_analyzer.log`.
- Attaches console handler (WARNING threshold, human-readable format:
  `%(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s`).
- Attaches `_CorrelationFilter`.
- Sets `propagate = False`.

**Function `get_tool_logger(tool_name, console=True) -> Logger`**: Factory for
standalone CLI tools.  Produces `cs2analyzer.tools.<tool_name>` logger with
per-invocation timestamped JSON log file in `logs/tools/`.

**Runtime reconfiguration**:
- `configure_log_level(level)`: Changes level of all `cs2analyzer.*` loggers at runtime.
- `configure_retention(max_days=30)`: Purges `.log` and `.json` files older than
  max_days.  Best-effort, errors silently ignored.

**Lazy app_logger** (WR-26):
- **Class `_LazyAppLogger`**: Proxy that defers logger creation via `__getattr__`.
- `app_logger = _LazyAppLogger()` -- avoids file handler creation before
  configure_log_dir() is called.

### M.6  observability/rasp.py

Runtime Application Self-Protection.  193 lines.

**HMAC Key** (R1-12):
- Read from `CS2_MANIFEST_KEY` env var.
- RP-01: Warns if not set, falls back to `"macena-cs2-integrity-v1"`.
- Encoded to bytes as `_MANIFEST_HMAC_KEY`.

**Class `IntegrityError(Exception)`**: Raised on integrity violations.

**Class `RASPGuard`**:
- `__init__(project_root: Path)`: Resolves manifest path dynamically.
- `_resolve_manifest_path() -> Path`: Checks multiple PyInstaller locations (root,
  flattened, full structure) for frozen mode.  Development: `Programma_CS2_RENAN/core/integrity_manifest.json`.

- `verify_runtime_integrity() -> Tuple[bool, List[str]]`:
  1. Checks manifest existence.  Missing in frozen mode = critical violation.
  2. Loads manifest JSON.
  3. R1-12: Verifies HMAC signature (recomputes canonical JSON, compares via
     `hmac.compare_digest`).
  4. Resolves base path for file hashes (sys._MEIPASS for frozen, manifest parent.parent
     for dev).
  5. For each file in `hashes` dict: verifies existence and SHA-256 match.
  6. Returns (success, violations).

- `_calculate_sha256(file_path) -> str`: Standard 4096-byte chunked SHA-256.

- `sign_manifest(manifest_path)` (static): R1-12 build-time signing.  Removes old
  signature, computes HMAC over canonical JSON (sorted keys, compact separators),
  writes back with signature field.

- `check_frozen_binary() -> bool`: Verifies .exe extension on Windows for PyInstaller
  binaries.

**Function `run_rasp_audit(project_root) -> bool`**: Convenience wrapper.  Logs
violations via centralized logger.  Returns False on any violation.

### M.7  observability/sentry_setup.py

Remote error reporting via Sentry SDK.  152 lines.  Double opt-in required.

**PII Scrubbing**:
- `_scrub_string(value, home) -> str`: Replaces home directory paths.
- `_before_send(event, hint) -> Optional[dict]`: Strips:
  1. `server_name` -> "redacted".
  2. Exception stacktrace filenames/abs_paths.
  3. Breadcrumb messages and data values.

**Function `init_sentry(dsn=None, enabled=False) -> bool`**: Triple gate:
1. pytest detection (skips in test environment).
2. Explicit `enabled=True` required.
3. Non-empty DSN required.

Configures Sentry SDK with:
- `traces_sample_rate=0.1`.
- `send_default_pii=False`.
- `before_send=_before_send` (PII scrubber).
- Release from `__version__`.
- LoggingIntegration (captures WARNING breadcrumbs, ERROR events).

**Function `add_breadcrumb(category, message, level="info", **data)`**: Records Sentry
breadcrumb if SDK active.  No-op otherwise.

---

## Part N -- Alembic Migration Stub

### N.1  Programma_CS2_RENAN/migrations/env.py

Deprecated migration chain (16 lines).  Raises `RuntimeError` immediately to prevent
accidental use.  The canonical Alembic configuration lives at `<project_root>/alembic/env.py` referenced by `alembic.ini` (`script_location = alembic`).

---

## Part O -- Cross-Cutting Concerns and Design Patterns

### O.1  Singleton Pattern Usage

The codebase uses singletons extensively:
- `AssetAuthority` (via `__new__`).
- `SpatialConfigLoader` (via `__new__` with double-checked locking).
- `AppLifecycleManager` (module-level `lifecycle` instance).
- `LocalizationManager` (module-level `i18n` instance).
- `ScreenRegistry` (module-level `registry` instance).
- `NamedPositionRegistry` (lazy via `_registry` module variable).
- `Console` (via `__new__` + `_lock`, documented in CONSOLE_ARCHITECTURE.md).
- `DatabaseManager` / `HLTVDatabaseManager` (via `get_db_manager()` / `get_hltv_db_manager()`).

### O.2  Thread Safety Mechanisms

- `_settings_lock = threading.RLock()` in config.py (reentrant for nested get/set).
- `_loader_lock = threading.Lock()` in spatial_data.py.
- `_registry_lock = threading.Lock()` in registry.py.
- `LabelSourceMonitor._lock = threading.Lock()`.
- `threading.Event()` for daemon coordination (shutdown, work_available, backup_failed).
- Thread-local storage for correlation IDs (`_correlation_local`).

### O.3  Error Handling Philosophy

- **Typed exceptions**: `CS2AnalyzerError` hierarchy for domain errors.
- **Formal error codes**: `ErrorCode` enum with severity/module/description/remediation.
- **Cross-enum comparison guard**: AT-01 in `app_types.Team.__eq__` prevents silent
  mismatches between numeric and string Team enums.
- **NaN/Inf sanitization**: DF-01 in `PlayerState.__post_init__`, CORE-10 in
  `PlaybackEngine._interpolate_angle`.
- **Fail-fast at boundaries**: R1-02 in `team_from_demo_frame` raises ValueError for
  unknown values.
- **SQL injection prevention**: `_IDENTIFIER_RE` and `_SAFE_COL_TYPE_RE` in schema.py.
- **Lock file concurrency**: `LockConflict` exception with PID-based stale detection.

### O.4  Observability Stack

Four layers:
1. **Structured JSON logging** via `get_logger()` with correlation IDs.
2. **Error code registry** with severity classification.
3. **Label source telemetry** (sliding-window alarm for concept-labelling degradation).
4. **Sentry integration** (double opt-in, PII scrubbed).
5. **RASP integrity verification** (HMAC-signed manifest, SHA-256 file hashes).

### O.5  Configuration Architecture

Three-tier configuration:
1. **Hardcoded defaults** in `load_user_settings()` (40+ keys).
2. **user_settings.json** on disk (atomic write via temp+rename, 0o600 permissions).
3. **Environment variable overrides** for Docker/CI (path-based settings).
4. **OS keyring** for secrets (STEAM_API_KEY, FACEIT_API_KEY, STORAGE_API_KEY).

Thread-safe access enforced via:
- `get_setting(key)` / `get_credential(key)` for daemon threads.
- `refresh_settings()` for full reload.
- Module-level globals retained for backward compatibility but marked stale-risk (C-01).

### O.6  Database Architecture

Three databases (documented in REFERENCE.md S5):
1. **Monolith** (`database.db`): Training data, match stats, round stats, ingestion
   tasks, coaching insights, user state.  Managed by Alembic.
2. **HLTV metadata** (`hltv_metadata.db`): Scraped pro stats.  Schema via
   `SQLModel.metadata.create_all()` (not yet under Alembic -- TASKS#47).
3. **Per-match shards** (`match_{id}.db`): Tick-level rich features.  Schema via
   `_MATCH_DB_MIGRATIONS`.

Access exclusively through singletons: `get_db_manager()`, `get_hltv_db_manager()`.

### O.7  Daemon Architecture

Four background daemons managed by Session Engine:
1. **Scanner** (10s interval): File discovery, queue creation.
2. **Digester** (event-driven): Demo parsing, 1 task at a time.
3. **Teacher** (300s interval): ML retraining when triggered.
4. **Pulse** (5s interval): Heartbeat updates.

All daemons:
- Run as daemon threads.
- Check `_shutdown_event.is_set()` for cooperative termination.
- Set correlation IDs per cycle (OBS-07).
- Are monitored by a 30s watchdog that restarts dead threads.

### O.8  Map Coordinate System

Source 2 world coordinates (x, y, z in game units) are transformed through:
1. `MapMetadata.world_to_radar()`: World -> normalized (0-1) using pos_x, pos_y, scale.
2. `SpatialEngine.normalized_to_pixel()`: Normalized -> viewport pixels.
3. Multi-level maps (Nuke, Vertigo) use z_cutoff for level selection.
4. `compute_z_penalty()` provides normalized vertical distance for neural network input.
5. `get_callout()` translates coordinates to human-readable names via nearest-neighbor
   lookup across ~160 hardcoded positions.

---

*End of Chapter 01 -- Core Configuration and Infrastructure.*
