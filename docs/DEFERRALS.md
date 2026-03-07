# Macena CS2 Analyzer — F-Code Deferral Registry

> **Last Updated:** 2026-03-07
> **Total F-Codes:** 148
> **Authority:** Deep Code Audit + Remediation Phases 0–9
> **Purpose:** Central registry of every audit finding annotation (F-code) in the codebase

---

## Overview

F-codes are inline annotation markers placed during the deep code audit and subsequent remediation phases. Each F-code documents a finding, fix, workaround, or known limitation. The format is `F<audit-domain>-<sequence>` where the domain corresponds to the audit scope:

| Domain | Scope |
|--------|-------|
| F2-xx | Processing & Feature Engineering |
| F3-xx | Neural Network & ML Pipeline |
| F4-xx | Backend Analysis & Coaching |
| F5-xx | Services, Control & Knowledge |
| F6-xx | Data Sources & Ingestion |
| F7-xx | Frontend/UI & Localization |
| F8-xx | Tools & Diagnostics |
| F9-xx | Tests |

### Status Legend

| Status | Meaning |
|--------|---------|
| **FIXED** | Issue identified and resolved in-place |
| **DEFERRED** | Known issue, resolution postponed to future phase |
| **ACCEPTED** | Deliberate design decision, no change planned |
| **MONITORING** | Fixed but requires validation with production data |

### Severity Legend

| Severity | Impact |
|----------|--------|
| **CRITICAL** | Produces wrong results or data corruption |
| **HIGH** | Significant limitation or risk |
| **MEDIUM** | Code quality, maintainability, or minor risk |
| **LOW** | Cosmetic, documentation, or optimization |

---

## F2-xx: Processing & Feature Engineering

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F2-02 | `backend/processing/tensor_factory.py:88` | ACCEPTED | MEDIUM | 128-dim output contract depends on RAPPerception's `input_dim`; change requires coordinated update |
| F2-03 | `backend/processing/tensor_factory.py:59` | ACCEPTED | MEDIUM | Calibrated for 64 tick/s; 128-tick demos (FACEIT/ESEA) may need adjustment |
| F2-04 | `backend/processing/tensor_factory.py:23` | ACCEPTED | LOW | scipy is a required dependency; import fails at module level if missing (intentional) |
| F2-08 | `backend/processing/player_knowledge.py:527` | ACCEPTED | MEDIUM | Using SMOKE_RADIUS (200 units) as proxy for flash effective radius — no official source |
| F2-10 | `backend/processing/round_stats_builder.py:65` | ACCEPTED | LOW | First round (i==0) start_tick=0 may include warmup ticks |
| F2-15 | `backend/processing/feature_engineering/vectorizer.py:203` | ACCEPTED | LOW | (0,0,0) could be valid position on some maps; sentinel check is heuristic |
| F2-16 | `backend/processing/feature_engineering/vectorizer.py:307` | MONITORING | MEDIUM | NaN/Inf clamp is a safety net, not a substitute for fixing upstream anomalies |
| F2-19 | `backend/processing/baselines/role_thresholds.py:105` | MONITORING | MEDIUM | Threshold validation checks individual values but not inter-threshold consistency |
| F2-20 | `backend/processing/feature_engineering/role_features.py:10` | ACCEPTED | LOW | Role signatures (aggression, entry, support) are heuristic approximations |
| F2-22 | `backend/processing/data_pipeline.py:224` | FIXED | MEDIUM | GET+SET+ADD queries avoid SQLite session timeouts on large datasets |
| F2-23 | `backend/processing/data_pipeline.py:85` | FIXED | MEDIUM | DataFrames used for batch processing |
| F2-26 | `backend/processing/validation/dem_validator.py:40` | FIXED | LOW | Backslash included in filename blocklist to prevent shell escape sequences |
| F2-28 | `backend/processing/feature_engineering/base_features.py:160` | FIXED | HIGH | Old ADR formula summed averages incorrectly; corrected to proper weighted average |
| F2-35 | `backend/processing/feature_engineering/kast.py:146` | ACCEPTED | LOW | KAST threshold is empirical observation at pro level; no formal statistical source |
| F2-39 | `backend/processing/feature_engineering/rating.py:123` | MONITORING | LOW | `compute_hltv2_rating_regression` is dead code — never called in production |
| F2-40 | `backend/processing/feature_engineering/rating.py:115` | ACCEPTED | LOW | Per-component average deliberately diverges from official HLTV 2.0 formula |
| F2-41 | `backend/processing/baselines/nickname_resolver.py:62` | ACCEPTED | MEDIUM | Substring + fuzzy lookup is O(n) per query, O(n²) total — acceptable for <1000 players |
| F2-44 | `backend/processing/baselines/meta_drift.py:66` | FIXED | LOW | Guard filters incomplete/None tuples to ensure uniform shape |
| F2-45 | `backend/processing/baselines/meta_drift.py:93` | ACCEPTED | LOW | 0/1e-6 = 0 keeps stat_drift at 0.0 in degenerate case — correct behavior |
| F2-46 | `backend/processing/connect_map_context.py:9` | ACCEPTED | LOW | Distance normalisation constants are fixed per-map values |
| F2-48 | `backend/processing/validation/schema.py:78` | MONITORING | MEDIUM | `int()` truncates floats (1.5→1), masking upstream parser bugs |

**Total F2-xx: 21 codes** | FIXED: 4 | ACCEPTED: 12 | MONITORING: 4 | DEFERRED: 1

---

## F3-xx: Neural Network & ML Pipeline

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F3-02 | `backend/nn/training_orchestrator.py:42` | FIXED | HIGH | Deterministic RNG for JEPA negative sampling |
| F3-05 | `backend/nn/config.py:153` | FIXED | MEDIUM | Canonical scale factor shared between GhostEngine and overlay code |
| F3-06 | `backend/nn/inference/ghost_engine.py:163` | FIXED | LOW | Column name inconsistency (pos_x vs X vs x) — tries pos_x first |
| F3-07 | `backend/nn/experimental/rap_coach/model.py:105` | FIXED | HIGH | Gate weights passed explicitly for thread-safety instead of caching on self |
| F3-08 | `backend/nn/jepa_train.py:107` | DEFERRED | HIGH | np.tile creates 20 IDENTICAL frames from single match-aggregate — temporal learning is nullified |
| F3-11 | `backend/nn/training_orchestrator.py:485` | MONITORING | HIGH | Track zero-tensor fallback rate — train step proceeds but tensors are meaningless |
| F3-18 | `backend/nn/evaluate.py:40` | MONITORING | MEDIUM | Zero-vector SHAP baseline biases attributions toward features with large absolute values |
| F3-21 | `backend/nn/experimental/rap_coach/chronovisor_scanner.py:183` | FIXED | MEDIUM | Tick fetch limited to prevent 250K+ tick matches saturating RAM |
| F3-22 | `backend/nn/coach_manager.py:324` | DEFERRED | MEDIUM | No LIMIT on PlayerMatchStats query — loads ALL rows into memory |
| F3-25 | `backend/nn/jepa_train.py:59` | MONITORING | MEDIUM | Uses unseeded global random state — window selection is non-reproducible |
| F3-26 | `backend/nn/jepa_train.py:338` | DEFERRED | HIGH | Placeholder uses synthetic random data — violates anti-fabrication principle |
| F3-28 | `backend/nn/coach_manager.py:884` | ACCEPTED | LOW | Mean of round_outcome across temporal window creates a smoothed signal |
| F3-29 | `backend/nn/experimental/rap_coach/perception.py:60` | FIXED | MEDIUM | Stale checkpoint detection by load_nn() raises StaleCheckpointError |
| F3-30 | `backend/nn/ema.py:92` | ACCEPTED | LOW | EMA updates weights through in-place modifications (by design) |
| F3-31 | `backend/nn/training_callbacks.py:32` | ACCEPTED | LOW | No @abstractmethod by design — callbacks are opt-in, not mandatory |
| F3-32 | `backend/nn/role_head.py:189` | FIXED | LOW | Local generator for reproducibility; doesn't affect global torch state |
| F3-34 | `backend/nn/dataset.py:51` | FIXED | LOW | max(0, ...) guards against edge-case negative values |
| F3-35 | `backend/nn/tensorboard_callback.py:198` | ACCEPTED | LOW | lr/group_0 hardcoded — models with multiple param groups need extension |
| F3-37 | `backend/nn/experimental/rap_coach/communication.py:68` | DEFERRED | MEDIUM | `angle` always resolves to "the flank" — advice is static regardless of actual direction |
| F3-38 | `backend/nn/experimental/rap_coach/test_arch.py:19` | ACCEPTED | LOW | Controlled 64x64 inputs match TrainingTensorConfig |

**Total F3-xx: 20 codes** | FIXED: 7 | ACCEPTED: 5 | MONITORING: 3 | DEFERRED: 5

---

## F4-xx: Backend Analysis & Coaching

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F4-01 | `backend/analysis/belief_model.py:40` | FIXED | MEDIUM | Maximum rows fetched from RoundStats for belief calibration (bounded query) |
| F4-02 | `backend/coaching/hybrid_engine.py:112` | FIXED | HIGH | `_using_fallback_baseline` flag tags insights as degraded when pro baseline fails |
| F4-03 | `backend/analysis/blind_spots.py:164` | FIXED | MEDIUM | Evaluate action via game tree public API (proper encapsulation) |
| F4-04 | `backend/coaching/hybrid_engine.py:98` | ACCEPTED | MEDIUM | DB must be initialized at app startup before instantiating HybridEngine |

**Total F4-xx: 4 codes** | FIXED: 3 | ACCEPTED: 1 | MONITORING: 0 | DEFERRED: 0

---

## F5-xx: Services, Control & Knowledge

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F5-03 | `backend/knowledge/init_knowledge_base.py:77` | FIXED | MEDIUM | COUNT query avoids loading all rows into memory |
| F5-04 | `backend/knowledge/rag_knowledge.py:445` | FIXED | MEDIUM | Singleton factory avoids re-loading SBERT model on every call |
| F5-06 | `backend/services/coaching_dialogue.py:147` | FIXED | MEDIUM | Append user message only after valid response (prevents phantom messages) |
| F5-07 | `backend/control/console.py:428` | FIXED | MEDIUM | rglob on network/large drives capped at 10,000 entries with error handling |
| F5-08 | `backend/knowledge/graph.py:31` | FIXED | LOW | Config constant instead of fragile `__file__` traversal |
| F5-10 | `backend/knowledge/experience_bank.py:655` | FIXED | MEDIUM | Query capped at 1000 to prevent OOM on large experience banks |
| F5-14 | `backend/services/analysis_orchestrator.py:74` | FIXED | MEDIUM | Per-module failure counter for observability of persistent silent failures |
| F5-15 | `backend/control/ml_controller.py:25` | FIXED | MEDIUM | Event-based pause avoids busy-wait polling loop |
| F5-16 | `backend/control/ml_controller.py:35` | FIXED | LOW | Custom exception replaces StopIteration (reserved for generators/iterators) |
| F5-18 | `backend/services/lesson_generator.py:23` | FIXED | LOW | Named thresholds — no magic numbers in lesson generation |
| F5-19 | `backend/services/visualization_service.py:19` | FIXED | MEDIUM | Matplotlib operations wrapped — rendering can fail on empty stats |
| F5-20 | `backend/knowledge/round_utils.py:5` | FIXED | MEDIUM | `infer_round_phase` extracted to shared utility to eliminate duplication |
| F5-21 | `backend/services/profile_service.py:100` | FIXED | LOW | `get_session()` context manager auto-commits on clean exit |
| F5-22 | `backend/services/profile_service.py:9` | FIXED | LOW | API keys loaded from env vars / keyring — not hard-coded |
| F5-23 | `backend/knowledge/rag_knowledge.py:155` | FIXED | HIGH | `init_database()` removed from constructor — must be called once at startup |
| F5-24 | `backend/services/ollama_writer.py:20` | ACCEPTED | LOW | System prompt is module constant; to tune without code changes, move to config |
| F5-25 | `backend/control/console.py:37` | FIXED | LOW | Named constants — no magic numbers in restart/TTL logic |
| F5-27 | `backend/knowledge/rag_knowledge.py:367` | ACCEPTED | LOW | `__main__` block is development self-test only |
| F5-30 | `backend/knowledge/graph.py:72` | FIXED | LOW | Renamed param from `type` to `entity_type` to avoid shadowing builtin |
| F5-31 | `backend/control/db_governor.py:100` | ACCEPTED | MEDIUM | PRAGMA quick_check can take minutes on large DBs (16+ GB) |
| F5-32 | `backend/control/ingest_manager.py:40` | FIXED | LOW | Default 30-minute re-scan interval, overridable via `set_mode()` |
| F5-33 | `backend/services/profile_service.py:14` | FIXED | LOW | Structured logging for profile service |
| F5-34 | `backend/control/console.py:287` | FIXED | MEDIUM | Log warning if timeout hit without clean shutdown |
| F5-35 | `backend/control/ingest_manager.py:43` | FIXED | MEDIUM | Event-based stop signal avoids 1-second polling in wait loops |
| F5-37 | `backend/services/analysis_orchestrator.py:532` | FIXED | LOW | Singleton factory avoids re-instantiating 7 analysis modules per call |
| F5-38 | `backend/services/coaching_service.py:708` | FIXED | LOW | Singleton factory consistent with other service accessors |

**Total F5-xx: 26 codes** | FIXED: 20 | ACCEPTED: 4 | MONITORING: 0 | DEFERRED: 2

---

## F6-xx: Data Sources & Ingestion

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F6-01 | `backend/data_sources/hltv/collectors/players.py:1` | FIXED | LOW | Removed unused imports; anti-fabrication: hardcoded fallback defaults removed |
| F6-02 | `backend/data_sources/hltv/browser/manager.py:56` | ACCEPTED | HIGH | Requires explicit ToS compliance sign-off before production HLTV scraping |
| F6-03 | `core/session_engine.py:458` | FIXED | MEDIUM | Explicit commit persists trained sample count (context manager doesn't auto-commit) |
| F6-04 | `backend/data_sources/hltv/collectors/players.py:3` | FIXED | LOW | `datetime.utcnow()` → `datetime.now(timezone.utc)` (timezone-aware) |
| F6-05 | `backend/data_sources/steam_demo_finder.py:22` | FIXED | LOW | Replaced print() calls with structured logger |
| F6-06 | `core/session_engine.py:7` | ACCEPTED | LOW | sys.path bootstrap required when daemon executed directly as script |
| F6-07 | `backend/data_sources/hltv/cache/proxy.py:19` | FIXED | LOW | Config constant instead of fragile 4-level `__file__` traversal |
| F6-08 | `backend/data_sources/hltv/browser/manager.py:29` | FIXED | MEDIUM | Context manager protocol prevents browser resource leaks |
| F6-09 | `backend/data_sources/trade_kill_detector.py:247` | FIXED | LOW | %s format instead of f-string in logger call |
| F6-10 | `backend/data_sources/hltv/hltv_api_service.py:22` | FIXED | HIGH | Circuit breaker stops loop after MAX_FAILURES consecutive failures |
| F6-11 | `ingestion/steam_locator.py:13` | ACCEPTED | LOW | Steam path discovery duplicated with `steam_demo_finder.py` (different consumers) |
| F6-13 | `run_ingestion.py:329` | ACCEPTED | MEDIUM | Objects fetched in one session; do not access lazy-loaded attrs after close |
| F6-14 | `run_ingestion.py:569` | FIXED | MEDIUM | Bounded state_lookup prevents OOM on large match files (>50k tick rows) |
| F6-16 | `backend/ingestion/watcher.py:21` | FIXED | MEDIUM | Maximum stability attempts before timeout (~30s at 1s interval) |
| F6-17 | `backend/ingestion/csv_migrator.py:24` | FIXED | LOW | Extracted safe_float to module level — was redefined inside every loop |
| F6-18 | `backend/ingestion/resource_manager.py:23` | FIXED | MEDIUM | Separate lock for throttle state — thread-safe CPU sample reads/writes |
| F6-19 | `ingestion/pipelines/user_ingest.py:16` | ACCEPTED | LOW | Pipeline stores basic PlayerMatchStats only; RoundStats added separately |
| F6-20 | `ingestion/registry/registry.py:18` | FIXED | LOW | Convert list → set for O(1) membership checks |
| F6-21 | `backend/data_sources/hltv/hltv_api_service.py:146` | FIXED | MEDIUM | Robust Cloudflare challenge/block page detection |
| F6-22 | `core/playback.py:80` | FIXED | LOW | Type hint added to `get_players_at_tick` |
| F6-23 | `core/localization.py:9` | DEFERRED | LOW | Translations hardcoded as dicts; migrate to JSON in `assets/i18n/` for runtime locale switching |
| F6-24 | `backend/ingestion/watcher.py:146` | FIXED | LOW | Read-only open check avoids timestamp mutation |
| F6-25 | `backend/data_sources/hltv/rate_limit.py:21` | ACCEPTED | LOW | Randomness intentionally unseeded — deterministic jitter would synchronize scrapers |
| F6-26 | `core/spatial_engine.py:20` | ACCEPTED | MEDIUM | Z coordinate ignored; multi-level maps (Nuke, Vertigo) place all on same plane |
| F6-27 | `core/constants.py:2` | FIXED | LOW | Constants centralized instead of scattered across modules |
| F6-29 | `backend/data_sources/faceit_api.py:11` | FIXED | LOW | Type hints added to fetch_faceit_data |
| F6-30 | `backend/data_sources/demo_format_adapter.py:86` | FIXED | LOW | Tuple instead of List in frozen dataclass |
| F6-31 | `ingestion/steam_locator.py:4` | FIXED | LOW | Imports moved from inside function to module level |
| F6-32 | `core/asset_manager.py:91` | ACCEPTED | LOW | Class-level cache shared across all AssetAuthority instances |
| F6-33 | `backend/data_sources/event_registry.py:32` | MONITORING | MEDIUM | Handler path references not validated at registration time |

**Total F6-xx: 30 codes** | FIXED: 18 | ACCEPTED: 8 | MONITORING: 1 | DEFERRED: 3

---

## F7-xx: Frontend/UI & Localization

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F7-02 | `main.py:1329` | FIXED | LOW | Explicit `nonlocal` reference prevents stale closure capture |
| F7-03 | `apps/desktop_app/wizard_screen.py:153` | DEFERRED | MEDIUM | Demo path wizard step not yet implemented (stub) |
| F7-04 | `main.py:775` | FIXED | LOW | `datetime.utcnow()` → `datetime.now(timezone.utc)` (timezone-aware) |
| F7-06 | `apps/desktop_app/wizard_screen.py:161` | DEFERRED | LOW | Duplicate of `_get_available_drives()` in main.py — consolidation deferred |
| F7-07 | `goliath.py:108,188,192,303` | FIXED | LOW | Logging uses `%s` format (lazy evaluation) instead of f-strings |
| F7-08 | `main.py:1826` | ACCEPTED | LOW | Deprecation warning kept for backward compatibility |
| F7-09 | `apps/desktop_app/help_screen.py:12` | DEFERRED | MEDIUM | help_system module not yet implemented; HelpScreen shows placeholder |
| F7-10 | `console.py:810` | ACCEPTED | MEDIUM | `stderr_file` intentionally not closed — spawned subprocess owns the handle; OS closes on process exit |
| F7-11 | `main.py:1708` | FIXED | LOW | Register temp file for cleanup on app exit |
| F7-12 | `console.py:40` | ACCEPTED | LOW | sys.path bootstrap acceptable for root-level CLI entry points |
| F7-13 | `apps/desktop_app/match_detail_screen.py:20` | DEFERRED | LOW | COLOR_GREEN/YELLOW/RED duplicated in match_history_screen.py; consolidate to shared module |
| F7-14 | `apps/desktop_app/player_sidebar.py:346` | FIXED | LOW | Explicit cache clear prevents growth across matches |
| F7-16 | `main.py:1049` | FIXED | MEDIUM | Iterative BFS replaces recursive tree walk — avoids stack overflow on deep widget trees |
| F7-17 | `core/localization.py:94` | FIXED | MEDIUM | Quick action prompt strings added to i18n dictionaries |
| F7-18 | `apps/desktop_app/layout.kv:76` | FIXED | MEDIUM | Hardcoded UI strings replaced with i18n.get_text() calls |
| F7-19 | `main.py:440` | FIXED | LOW | Properties required by TrainingStatusCard in layout.kv |
| F7-21 | `apps/desktop_app/tactical_map.py:291` | FIXED | LOW | FIFO eviction for texture cache instead of aggressive clear() |
| F7-22 | `apps/desktop_app/tactical_map.py:514` | FIXED | LOW | Uses min(width, height) for uniform scaling on non-square widgets |
| F7-23 | `main.py:763` | FIXED | MEDIUM | Progressive backoff when daemon is offline |
| F7-24 | `apps/desktop_app/coaching_chat_vm.py:36` | FIXED | HIGH | Threading lock protects messages list from concurrent access |
| F7-25 | `apps/desktop_app/tactical_viewmodels.py:197` | FIXED | MEDIUM | Cooperative cancellation flag for background scan threads |
| F7-26 | `core/localization.py:110` | FIXED | LOW | Missing "search" key added to all translation dictionaries |
| F7-27 | `apps/desktop_app/tactical_viewer_screen.py:187` | FIXED | MEDIUM | Guard against stale callback firing after screen navigation |
| F7-28 | `core/localization.py:6` | ACCEPTED | LOW | `os.path.expanduser('~')` evaluated at import time — acceptable for desktop app |
| F7-29 | `goliath.py:87` | DEFERRED | HIGH | TODO: terminate running child processes before exit to prevent orphaned processes |
| F7-30 | `console.py:731` | ACCEPTED | LOW | Showing last 4 chars of API key is accepted practice until keyring integration |
| F7-31 | `apps/desktop_app/layout.kv:1050` | DEFERRED | LOW | `current_topic_title` property on HelpScreen depends on F7-09 fix |
| F7-32 | `console.py:841` | ACCEPTED | LOW | No dry-run flag for cache clear — safe operation (caches regenerate) |
| F7-33 | `apps/desktop_app/timeline.py:63` | FIXED | LOW | Clamp seek position to [0.0, 1.0] — prevents out-of-range seeks |
| F7-34 | `goliath.py:223` | DEFERRED | MEDIUM | `dept_map` doesn't include all `Department` enum values — unmapped departments fall through to full diagnostic |
| F7-36 | `apps/desktop_app/widgets.py:97` | FIXED | LOW | Radar chart guard: minimum 3 data points for meaningful polygon |
| F7-37 | `main.py:986` | ACCEPTED | LOW | Notifications marked as read immediately on retrieval |
| F7-38 | `apps/desktop_app/ghost_pixel.py:18` | ACCEPTED | LOW | GhostPixel debug overlay importable in production — no functional risk |
| F7-39 | `apps/desktop_app/layout.kv:126` | ACCEPTED | MEDIUM | Two full-resolution FitImage textures held in memory for crossfade transitions |

**Total F7-xx: 30 codes** | FIXED: 17 | ACCEPTED: 8 | MONITORING: 0 | DEFERRED: 5

---

## F8-xx: Tools & Diagnostics

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F8-03 | `tools/dead_code_detector.py:66` | FIXED | LOW | Dot-delimited boundary check prevents false import matches |
| F8-05 | `tools/Goliath_Hospital.py:2012` | ACCEPTED | LOW | Health rating thresholds — adjust if project error/warning baseline changes |
| F8-06 | `tools/Goliath_Hospital.py:1374` | MONITORING | LOW | Regex-based import scan matches "import" in comments and strings |
| F8-07 | `tools/headless_validator.py:129` | ACCEPTED | LOW | Schema validation uses in-memory SQLite for speed (no WAL mode testing) |
| F8-08 | `tools/user_tools.py:153` | FIXED | LOW | Timezone-aware UTC datetime |
| F8-09 | `tools/Ultimate_ML_Coach_Debugger.py:67` | FIXED | MEDIUM | Converted module-level functions to proper instance methods |
| F8-10 | `tools/user_tools.py:54` | FIXED | LOW | No key fragment in log — avoids partial credential exposure |
| F8-11 | `tools/context_gatherer.py:290` | MONITORING | LOW | Substring matching creates false reverse deps from comments/strings |
| F8-12 | `tools/db_inspector.py:315` | ACCEPTED | LOW | table_name from SQLAlchemy introspection (not user input) — injection risk minimal |
| F8-13 | `tools/Goliath_Hospital.py:1441` | FIXED | LOW | Timezone-aware UTC datetime |
| F8-15 | `tools/Goliath_Hospital.py:1273` | FIXED | LOW | Detect both `#def` and `# def` patterns (with or without space) |
| F8-16 | `tools/backend_validator.py:217` | ACCEPTED | LOW | Model Zoo uses torch.randn() inputs — smoke tests only, not accuracy tests |
| F8-18 | `tools/dead_code_detector.py:22` | ACCEPTED | LOW | apps/ excluded from dead-code analysis (KivyMD screens loaded dynamically) |
| F8-19 | `tools/Goliath_Hospital.py:46` | ACCEPTED | LOW | Goliath Hospital uses print() for console output rather than structured logging |
| F8-20 | `tools/Ultimate_ML_Coach_Debugger.py:27` | ACCEPTED | MEDIUM | Variance threshold 0.5 for neural belief stability is heuristic upper bound |
| F8-22 | `tools/Goliath_Hospital.py:1396` | FIXED | LOW | startswith() prevents 'internal_tools/' false match on 'tools/' prefix |
| F8-23 | `tools/db_inspector.py:243` | FIXED | LOW | Log suppressed queries instead of silent suppress |
| F8-24 | `tools/db_inspector.py:254` | FIXED | LOW | Log suppressed pro/user queries |
| F8-25 | `tools/context_gatherer.py:545` | FIXED | LOW | Return exit code 1 to signal failure to calling scripts |
| F8-26 | `tools/dead_code_detector.py:104` | FIXED | LOW | Capture rglob once to avoid redundant directory traversal |
| F8-28 | `tools/Ultimate_ML_Coach_Debugger.py:4` | ACCEPTED | LOW | Neural belief state and decision logic falsification tool |
| F8-29 | `tools/Goliath_Hospital.py:1674` | ACCEPTED | LOW | hflayers is root-level custom implementation, not pip-installed |
| F8-30 | `tools/Goliath_Hospital.py:2164` | DEFERRED | LOW | `--department` flag defined but not wired to selective execution |
| F8-33 | `tools/Goliath_Hospital.py:2128` | ACCEPTED | LOW | argparse imported inside main() as lazy import |
| F8-34 | `tools/context_gatherer.py:345` | FIXED | MEDIUM | subprocess.run() uses list args (shell=False) with timeout=10 |
| F8-35 | `tools/user_tools.py:273` | FIXED | LOW | Stale PID file detection for HLTV daemon |
| F8-37 | `tools/Goliath_Hospital.py:1441` | FIXED | LOW | Timezone-aware UTC datetime (combined with F8-13) |
| F8-38 | `tools/Goliath_Hospital.py:2083` | FIXED | LOW | UTC timestamp for unambiguous filenames |

**Total F8-xx: 28 codes** | FIXED: 14 | ACCEPTED: 10 | MONITORING: 2 | DEFERRED: 2

---

## F9-xx: Tests

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F9-01 | `tests/test_db_backup.py:20` | ACCEPTED | MEDIUM | backup_monolith() may hang waiting on DB lock — test skipped by default |
| F9-02 | `tests/test_onboarding_training.py:9` | MONITORING | MEDIUM | TestExtractFeatures creates synthetic data — borderline anti-fabrication |
| F9-04 | `tests/test_db_backup.py:20` | ACCEPTED | MEDIUM | DB lock contention risk — combined with F9-01 skip marker |
| F9-08 | `tests/automated_suite/test_smoke.py:4` | ACCEPTED | LOW | Import-only smoke tests — verify modules load without crashing |
| F9-09 | `tests/test_onboarding_training.py:9` | MONITORING | MEDIUM | Borderline anti-fabrication — synthetic data in test fixtures |
| F9-20 | `tests/test_rag_knowledge.py:221` | FIXED | LOW | Prefix isolates test rows from production data; teardown cleans up |

**Total F9-xx: 6 codes** | FIXED: 1 | ACCEPTED: 3 | MONITORING: 2 | DEFERRED: 0

---

## F10-xx: Phase 10 Findings

| Code | File:Line | Status | Severity | Description |
|------|-----------|--------|----------|-------------|
| F10-01 | `main.py` (multiple) | DEFERRED | MEDIUM | Dialog strings in main.py bypass i18n system ("Daemon Startup Failed", "Service Offline", etc.) |

**Total F10-xx: 1 code** | DEFERRED: 1

---

## Summary Statistics

| Domain | Fixed | Accepted | Monitoring | Deferred | Total |
|--------|-------|----------|------------|----------|-------|
| F2-xx Processing | 4 | 12 | 4 | 1 | 21 |
| F3-xx Neural/ML | 7 | 5 | 3 | 5 | 20 |
| F4-xx Analysis | 3 | 1 | 0 | 0 | 4 |
| F5-xx Services | 20 | 4 | 0 | 2 | 26 |
| F6-xx Ingestion | 18 | 8 | 1 | 3 | 30 |
| F7-xx Frontend | 18 | 9 | 0 | 7 | 34 |
| F8-xx Tools | 14 | 10 | 2 | 2 | 28 |
| F9-xx Tests | 1 | 3 | 2 | 0 | 6 |
| F10-xx Phase 10 | 0 | 0 | 0 | 1 | 1 |
| **Total** | **85** | **52** | **12** | **21** | **170** |

---

## Deferred Items Requiring Future Work

### High Priority

| Code | Description | Target Phase |
|------|-------------|--------------|
| F3-08 | np.tile creates identical frames from single aggregate — temporal learning nullified | Phase 1 (ML Pipeline) |
| F3-26 | Placeholder uses synthetic random data — violates anti-fabrication | Phase 1 (ML Pipeline) |
| F3-11 | Zero-tensor fallback rate tracking — meaningless training steps | Phase 1 (ML Pipeline) |
| F3-22 | No LIMIT on PlayerMatchStats query — potential OOM | Phase 1 (ML Pipeline) |
| F7-29 | Goliath: no child process termination on signal — orphaned processes | Phase 11+ |

### Medium Priority

| Code | Description | Target Phase |
|------|-------------|--------------|
| F3-37 | Communication angle always resolves to "the flank" — static advice | Phase 9 (Architecture) |
| F7-03 | Demo path wizard step stub | Phase 4 (UI/UX) |
| F7-09 | Help system module not implemented | Phase 4 (UI/UX) |
| F10-01 | Dialog strings in main.py bypass i18n | Phase 11+ |
| F7-34 | Goliath `dept_map` missing Department enum values — silent fallthrough | Phase 11+ |
| F8-30 | `--department` flag defined but not wired | Phase 11+ |

### Low Priority

| Code | Description | Target Phase |
|------|-------------|--------------|
| F6-23 | Translations hardcoded as dicts — migrate to JSON files | Phase 11+ |
| F7-06 | `_get_available_drives()` duplicated in wizard_screen and main.py | Phase 4 (UI/UX) |
| F7-13 | Color constants duplicated between match_detail and match_history | Phase 4 (UI/UX) |
| F7-31 | HelpScreen `current_topic_title` depends on F7-09 | Phase 4 (UI/UX) |

---

## Accepted Design Decisions (No Change Planned)

| Code | Description | Rationale |
|------|-------------|-----------|
| F2-02 | 128-dim output depends on RAPPerception input_dim | Architectural contract; documented |
| F2-03 | Calibrated for 64 tick/s | CS2 matchmaking default; FACEIT/ESEA is edge case |
| F3-30 | EMA in-place weight modification | Standard EMA implementation; copy would waste memory |
| F3-31 | No @abstractmethod on callbacks | Opt-in design; mandatory callbacks would break extensibility |
| F6-02 | HLTV scraping requires ToS compliance | Legal requirement; not a code issue |
| F6-25 | Unseeded random jitter in rate limiter | Deterministic jitter would synchronize scrapers |
| F7-10 | stderr_file not closed in console spawn | Subprocess owns the handle; OS closes on process exit |
| F7-38 | GhostPixel debug overlay importable in production | No functional risk; useful for diagnostics |
| F7-39 | Two FitImage textures for crossfade | UX quality tradeoff; ~20MB memory acceptable |
| F8-07 | In-memory SQLite for schema validation | Speed vs fidelity tradeoff; WAL tested separately |
| F8-19 | Goliath Hospital uses print() | Console diagnostic tool; structured logging unnecessary |
