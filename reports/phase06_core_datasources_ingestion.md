# Deep Audit Report — Phase 6: Core Engine + Data Sources + Ingestion

**Total Files Audited: 38 / 38**
**Issues Found: 34**
**CRITICAL: 4 | HIGH: 6 | MEDIUM: 16 | LOW: 8**
**Author: Renan Augusto Macena**
**Date: 2026-02-27**
**Auditor: Claude Code (Deep Audit Protocol)**

---

## Scope

Phase 6 covers the core engine layer (session engine, playback, spatial engine, asset management, localization), data sources (demo parser, event registry, trade kill detection, Steam API, HLTV metadata/scraping, FACEIT API, demo format adapter), backend ingestion (watcher, resource manager, CSV migrator), top-level ingestion pipelines (demo loader, downloader, HLTV orchestrator, integrity, steam locator, HLTV API service, rate limiter, browser manager, caching proxy, player collector, JSON ingestor, user/pro ingest, demo registry, lifecycle), and the main ingestion entry point (`run_ingestion.py`).

### Files Audited

| # | File | LOC | Status |
|---|---:|---|---|
| 1 | `core/session_engine.py` | 400 | Audited |
| 2 | `core/asset_manager.py` | 253 | Audited |
| 3 | `core/localization.py` | 274 | Audited |
| 4 | `core/map_manager.py` | 88 | Audited |
| 5 | `core/playback.py` | 114 | Audited |
| 6 | `core/playback_engine.py` | 247 | Audited |
| 7 | `core/spatial_engine.py` | 89 | Audited |
| 8 | `core/constants.py` | 0 | Audited (empty) |
| 9 | `backend/data_sources/demo_parser.py` | 367 | Audited |
| 10 | `backend/data_sources/event_registry.py` | 353 | Audited |
| 11 | `backend/data_sources/trade_kill_detector.py` | 346 | Audited |
| 12 | `backend/data_sources/steam_api.py` | 106 | Audited |
| 13 | `backend/data_sources/hltv_metadata.py` | 73 | Audited |
| 14 | `backend/data_sources/hltv_scraper.py` | 47 | Audited |
| 15 | `backend/data_sources/demo_format_adapter.py` | 281 | Audited |
| 16 | `backend/data_sources/faceit_api.py` | 33 | Audited |
| 17 | `backend/data_sources/steam_demo_finder.py` | 245 | Audited |
| 18 | `backend/data_sources/faceit_integration.py` | 274 | Audited |
| 19 | `backend/ingestion/watcher.py` | 197 | Audited |
| 20 | `backend/ingestion/resource_manager.py` | 197 | Audited |
| 21 | `backend/ingestion/csv_migrator.py` | 201 | Audited |
| 22 | `ingestion/demo_loader.py` | 502 | Audited |
| 23 | `ingestion/downloader.py` | 111 | Audited |
| 24 | `ingestion/hltv_orchestrator.py` | 243 | Audited |
| 25 | `ingestion/integrity.py` | 54 | Audited |
| 26 | `ingestion/steam_locator.py` | 134 | Audited |
| 27 | `ingestion/hltv/hltv_api_service.py` | 188 | Audited |
| 28 | `ingestion/hltv/rate_limit.py` | 28 | Audited |
| 29 | `ingestion/hltv/selectors.py` | 29 | Audited |
| 30 | `ingestion/hltv/browser/manager.py` | 46 | Audited |
| 31 | `ingestion/hltv/cache/proxy.py` | 122 | Audited |
| 32 | `ingestion/hltv/collectors/players.py` | 128 | Audited |
| 33 | `ingestion/pipelines/json_tournament_ingestor.py` | 126 | Audited |
| 34 | `ingestion/pipelines/user_ingest.py` | 53 | Audited |
| 35 | `ingestion/pipelines/pro_ingest.py` | 41 | Audited |
| 36 | `ingestion/registry/registry.py` | 83 | Audited |
| 37 | `ingestion/registry/lifecycle.py` | 26 | Audited |
| 38 | `run_ingestion.py` | ~700 | Audited |

---

## Architecture Summary

### Session Engine (`core/session_engine.py`)
Tri-daemon architecture coordinating background operations:
- **Scanner Daemon (Hunter)**: Polls file system for new `.dem` files every 10 seconds
- **Digester Daemon**: Consumes IngestionTask queue via `process_queued_tasks()`
- **Teacher Daemon**: ML retraining trigger at 10% sample growth, meta-shift detection after training
- **Pulse Daemon**: Heartbeat every 5 seconds

All daemons share `_shutdown_event` (threading.Event) for coordinated shutdown. Stdin pipe closure detects parent death (IPC life-line pattern).

### Data Sources Layer
- **demo_parser.py**: Hand-tuned HLTV 2.0 rating approximation with explicit NO HARDCODED FALLBACKS policy
- **event_registry.py**: 24 canonical CS2 events as GameEventSpec dataclasses
- **trade_kill_detector.py**: Temporal scan algorithm within TRADE_WINDOW_TICKS=192 (3s at 64 tick)
- **steam_api.py**: HTTP GET with exponential backoff retry (3 attempts, 1/2/4s delays)
- **demo_format_adapter.py**: Magic byte validation (PBDEMS2 vs HL2DEMO), corruption detection

### HLTV Scraping Pipeline
Multi-component Playwright-based scraping:
- `browser/manager.py`: Headless Chromium with anti-detection features
- `rate_limit.py`: 4-tier delay system (micro/standard/heavy/backoff)
- `cache/proxy.py`: SQLite-backed HTML cache with 7-day TTL
- `hltv_api_service.py`: Per-player stat extraction with Cloudflare detection
- `collectors/players.py`: Batch player discovery and extraction

### Ingestion Pipeline
1. **Discovery**: `watcher.py` (watchdog-based) + `scanner daemon` (polling-based)
2. **Queueing**: IngestionTask DB records (status: queued/processing/completed/failed)
3. **Processing**: `run_ingestion.py._ingest_single_demo()` — parse stats, save sequential ticks, extract events
4. **Archival**: Processed demos moved to archive directory

---

## Findings

### F6-01 | CRITICAL | Anti-Fabrication Violation — Hardcoded Fallback Stats in Player Collector
**File:** `ingestion/hltv/collectors/players.py:108-127`
**Skills:** deep-audit, ml-check, correctness-check

```python
def _map_stats_to_model(name, stats, html):
    return PlayerMatchStats(
        avg_kills=float(stats.get("Kills per round", "0.7").split()[0]),    # fabricated 0.7
        avg_deaths=float(stats.get("Deaths per round", "0.6").split()[0]),  # fabricated 0.6
        avg_adr=float(stats.get("Damage / round", "80.0").split()[0]),      # fabricated 80.0
        avg_hs=0.5,                                                          # ALWAYS fabricated
        avg_kast=float(stats.get("KAST", "70%").replace("%", "")) / 100,    # fabricated 70%
        rating=float(stats.get("Rating 2.0", stats.get("Rating 1.0", "1.0"))),  # fabricated 1.0
        kd_ratio=float(stats.get("K/D Ratio", "1.0")),                     # fabricated 1.0
        kill_std=0.1,                                                        # placeholder
        adr_std=5.0,                                                         # placeholder
    )
```

Every stat field has a hardcoded fallback value. If HLTV page structure changes and a field is missing, fabricated "average-looking" values silently enter the pro baseline database. Compare with `hltv_api_service.py:124-135` which correctly raises `ValueError` for missing fields.

**Blast Radius**: Corrupts pro baseline data, which is used by coaching service, belief calibrator, and temporal baseline decay. Every downstream coaching insight could be based on fabricated data.

---

### F6-02 | CRITICAL | Anti-Bot Evasion via webdriver Property Override
**File:** `ingestion/hltv/browser/manager.py:44`
**Skills:** security-scan

```python
page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
```

Combined with spoofed user agents in:
- `downloader.py:28`: `"Mozilla/5.0 ... Chrome/120 Safari/537.36"`
- `hltv_orchestrator.py:95`: Same spoofed UA
- `browser/manager.py:39`: `"Mozilla/5.0 ... Chrome/121.0.0.0 Safari/537.36"`

This manipulates browser fingerprinting to bypass anti-automation detection on HLTV.org. This may violate HLTV's Terms of Service and could result in IP bans that silently break all HLTV-dependent features (pro baseline sync, match discovery).

---

### F6-03 | CRITICAL | Missing session.commit() in _commit_trained_sample_count()
**File:** `core/session_engine.py:385-395`
**Skills:** db-review, state-audit, correctness-check

```python
def _commit_trained_sample_count(count: int) -> None:
    db = get_db_manager()
    try:
        with db.get_session() as s:
            st = s.exec(select(CoachState)).first()
            if st:
                st.last_trained_sample_count = count
                s.add(st)
                # BUG: Missing s.commit() — changes are rolled back on session close
    except Exception as e:
        logger.error("Failed to commit trained sample count: %s", e)
```

The `get_session()` context manager does NOT auto-commit. The mutation is lost when the session closes. The Teacher daemon calls `_commit_trained_sample_count()` after successful training, then on the next cycle `_check_retraining_trigger()` compares against the stale (uncommitted) count, potentially triggering retraining every cycle.

**Blast Radius**: Infinite retraining loop — Teacher daemon wastes GPU resources retraining every 5 minutes instead of only when 10% new data arrives.

---

### F6-04 | CRITICAL | Deprecated datetime.utcnow() Across Scraping Layer
**Files:** `hltv_orchestrator.py:132,160`, `hltv_api_service.py:174`, `collectors/players.py:126`
**Skills:** correctness-check

```python
# hltv_orchestrator.py:132
"date": datetime.utcnow().isoformat(),

# hltv_api_service.py:174
"processed_at": datetime.datetime.utcnow(),

# collectors/players.py:126
processed_at=datetime.datetime.utcnow(),
```

`datetime.utcnow()` is deprecated since Python 3.12 and returns a naive datetime (no timezone info). Will emit `DeprecationWarning` now and will be removed in Python 3.14+. Should use `datetime.now(datetime.UTC)`.

---

### F6-05 | HIGH | print() Instead of Structured Logging
**Files:** `rate_limit.py:21`, `collectors/players.py:17,22,42,47,50,75,81,91`, `csv_migrator.py:148`, `steam_demo_finder.py:223-244`
**Skills:** observability-audit

```python
# rate_limit.py:21
print(f"[Limiter] Sleeping for {delay:.2f}s (Tier: {tier})")

# collectors/players.py — 8 print() calls throughout the file
print(f"Starting Discovery Pass for IDs {start_id} to {end_id}...")
print(f"Checking ID {pid}...")
print(f"[Valid] ID {pid} -> {coll.page.url}")
print(f"[Error] Failed ID {pid}: {e}")
```

Direct violation of CLAUDE.md: "Structured logging with correlation IDs — no `print()` debugging".

---

### F6-06 | HIGH | sys.path Manipulation at Module Import Time
**Files:** `session_engine.py:7-11`, `hltv_metadata.py:10-12`, `csv_migrator.py:7-8`, `json_tournament_ingestor.py:9-11`
**Skills:** correctness-check, security-scan

```python
# session_engine.py:7-11
current = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
if root not in sys.path:
    sys.path.insert(0, root)
```

Four separate files manipulate `sys.path` at module level. This creates non-deterministic import behavior and makes package resolution dependent on execution context. Could also introduce path injection if `__file__` is under attacker control.

---

### F6-07 | HIGH | Hardcoded DB Path in HLTV Cache Proxy
**File:** `ingestion/hltv/cache/proxy.py:27-33`
**Skills:** db-review, correctness-check

```python
DB_PATH = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
    "data",
    "hltv_cache.db",
)
```

Path is computed via `__file__` relative traversal (4 levels up). Breaks when:
- Package is frozen/bundled (PyInstaller)
- File is symlinked
- Run from different working directory

Also uses raw `sqlite3` instead of the project's ORM/DatabaseManager, creating a shadow database outside the governance of `DatabaseGovernor`.

---

### F6-08 | HIGH | BrowserManager Missing __exit__ Method
**File:** `ingestion/downloader.py:19-32`
**Skills:** correctness-check, resilience-check

```python
class BrowserManager:
    def __enter__(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(...)
        self.context = self.browser.new_context(...)
        self.page = self.context.new_page()
        return self.page
    # NO __exit__ method — browser never closes
```

The `with BrowserManager() as page:` pattern at line 78 will enter the context but never exit it. Playwright browser process leaks on every call. Will also leak if an exception occurs during `__enter__` after `.start()`.

---

### F6-09 | HIGH | f-string in Logger Calls
**Files:** `trade_kill_detector.py:244-246`, `demo_format_adapter.py:196-198`
**Skills:** observability-audit

```python
# trade_kill_detector.py:244
logger.info(
    f"Trade kill analysis: {result.trade_kills}/{result.total_kills} kills were trades "
    f"({result.trade_kill_ratio:.1%}), {result.players_traded} deaths traded"
)
```

f-strings in logger calls bypass lazy evaluation — the string is always formatted even if the log level would suppress it. Should use `%s` style: `logger.info("Trade kill analysis: %d/%d ...", result.trade_kills, result.total_kills, ...)`.

---

### F6-10 | HIGH | No Circuit Breaker on HLTV Scraping Pipeline
**Files:** `hltv_api_service.py:28-35`, `collectors/players.py:15-18`
**Skills:** resilience-check

```python
# hltv_api_service.py
def sync_range(self, start_id, end_id):
    ids = self._get_ids_range(start_id, end_id)
    synced = _sync_ids_loop(self, page, db_manager, ids)
    # No circuit breaker, no max failure count, no timeout
```

`_sync_ids_loop` iterates up to 35,000 player IDs with individual 60s timeouts. If Cloudflare blocks the IP, each ID gets a 45-90s backoff. Worst case: 35000 * 90s = 36 days of sleeping. No circuit breaker pattern to abort after N consecutive failures.

---

### F6-11 | MEDIUM | Duplicate Steam Path Discovery Implementations
**Files:** `ingestion/steam_locator.py`, `backend/data_sources/steam_demo_finder.py`
**Skills:** correctness-check

Both files implement independent Steam directory discovery:
- `steam_locator.py`: Registry lookup + psutil-based drive enumeration
- `steam_demo_finder.py`: Registry lookup + ctypes windll drive enumeration

Different fallback strategies, different path lists, different error handling. Should be consolidated into a single authority.

---

### F6-12 | MEDIUM | Undefined Function Reference in Downloader
**File:** `ingestion/downloader.py:41`
**Skills:** correctness-check

```python
def extract_match_metadata(page):
    ...
    date_val = _extract_date(page)  # Function never defined
```

`_extract_date` is called but never defined in the file or imported. Will crash with `NameError` at runtime when `extract_match_metadata()` is invoked.

---

### F6-13 | MEDIUM | Detached Object in process_queued_tasks
**File:** `run_ingestion.py:327-331`
**Skills:** db-review, correctness-check

```python
# Tasks fetched in session A (line 314-318), then later:
with db_manager.get_session() as session:
    session.add(task)       # task is detached from original session
    task.status = "processing"
    session.commit()
```

The `task` objects are fetched in one session context, but then manipulated in a different session. With SQLModel/SQLAlchemy, adding a detached object to a new session may cause `DetachedInstanceError` or silently duplicate the row.

---

### F6-14 | MEDIUM | Unbounded Memory in Event Extraction State Lookup
**File:** `run_ingestion.py:559-566`
**Skills:** correctness-check, resilience-check

```python
state_lookup = {}
if not df_ticks.empty and "player_name" in df_ticks.columns:
    for _, row in df_ticks.iterrows():
        key = (int(row["tick"]), str(row["player_name"]).strip().lower())
        state_lookup[key] = {...}
```

For a typical CS2 match with ~500K ticks and 10 players, this creates ~5 million dictionary entries. No memory cap, no sampling. Large matches could exhaust available RAM.

---

### F6-15 | MEDIUM | Undefined Variable `app_logger` in hltv_metadata.py
**File:** `backend/data_sources/hltv_metadata.py:26,36,43,51,55,65`
**Skills:** correctness-check

```python
logger = get_logger("cs2analyzer.hltv_metadata")  # line 7: named 'logger'
...
app_logger.info("[DEBUG] Fetching URL...")          # line 26: references 'app_logger'
```

Variable `app_logger` is never defined. All 6 logging calls will crash with `NameError`. The variable at line 7 is named `logger`, not `app_logger`.

---

### F6-16 | MEDIUM | No Maximum Retry in File Stability Check
**File:** `backend/ingestion/watcher.py:65-109`
**Skills:** resilience-check

```python
def _check_file_stability(self, file_path, last_size, stable_count):
    ...
    # If not stable, reschedule indefinitely
    self._reschedule_check(file_path, current_size, stable_count)
```

No maximum attempt counter. If a file is continuously growing (e.g., an active recording), the watcher creates new Timer objects indefinitely. Each timer retains references to the handler and arguments, accumulating memory.

---

### F6-17 | MEDIUM | Nested Function Definitions Inside Loop
**File:** `backend/ingestion/csv_migrator.py:73-77,162-163`
**Skills:** correctness-check

```python
for row in reader:
    def safe_float(key, default=0.0):    # recreated every iteration
        try:
            return float(row.get(key, default))
```

`safe_float` is redefined on every loop iteration. It also closes over `row` from the enclosing loop scope, which creates subtle bugs if the inner function is referenced later. Should be extracted as a module-level helper.

---

### F6-18 | MEDIUM | Global Mutable State Without Lock Protection
**File:** `backend/ingestion/resource_manager.py:21-22`
**Skills:** state-audit, correctness-check

```python
_current_throttle_state = False  # module-level global

class ResourceManager:
    @staticmethod
    def should_throttle():
        global _current_throttle_state
        # Read and write without lock — called from multiple daemon threads
```

`should_throttle()` is called from the Digester daemon and potentially the Scanner daemon concurrently. The global `_current_throttle_state` is read and written without any synchronization primitive. While Python's GIL prevents data corruption, the hysteresis logic could produce inconsistent throttle decisions across threads.

---

### F6-19 | MEDIUM | Legacy Pipeline Bypasses Enrichment
**Files:** `ingestion/pipelines/user_ingest.py`, `ingestion/pipelines/pro_ingest.py`
**Skills:** data-lifecycle-review, correctness-check

```python
# user_ingest.py — calls old pipeline directly
rounds_df = parse_demo(str(demo_path))
match_stats_dict = extract_match_stats(rounds_df)
db_manager.upsert(match_stats)
```

These pipeline files call `parse_demo()` → `extract_match_stats()` → `upsert()` directly, bypassing the enrichment pipeline added in Fusion Phase 1:
- No `enrich_from_demo()` call (RoundStats creation)
- No `_extract_and_store_events()` call (MatchEventState persistence)
- No `_save_sequential_data()` call (PlayerTickState persistence)

If these pipelines are invoked, match data will lack per-round stats, events, and tick-level telemetry.

---

### F6-20 | MEDIUM | O(n) Lookup in Demo Registry
**File:** `ingestion/registry/registry.py:33`
**Skills:** correctness-check

```python
def is_processed(self, demo_name: str) -> bool:
    return demo_name in self.data["processed_demos"]  # list scan
```

`processed_demos` is a JSON list. Membership check is O(n). For registries with thousands of processed demos, this degrades performance. Should use a set for O(1) lookup.

---

### F6-21 | MEDIUM | Fragile Cloudflare Detection
**File:** `ingestion/hltv/hltv_api_service.py:100`
**Skills:** resilience-check

```python
if "just a moment" in page.title().lower():
    app_logger.warning("Cloudflare detected: %s", pid)
```

String matching on page title is brittle. Cloudflare frequently updates their challenge page. If the title changes, detection fails silently and the code attempts to parse challenge page HTML as stats data.

---

### F6-22 | MEDIUM | TimelineController Returns Unstructured Data
**File:** `core/playback.py:78-90`
**Skills:** api-contract-review

```python
def get_players_at_tick(self, tick: int):
    if not self._demo_data:
        return []
    return self._demo_data.get("positions", {}).get(tick, [])
```

No type annotation on return, no documentation of expected structure, no validation of `demo_data["positions"]` format. Consumers must guess the return type.

---

### F6-23 | MEDIUM | Hardcoded Translation Dictionaries
**File:** `core/localization.py:6-256`
**Skills:** correctness-check

All 256 lines are hardcoded translation strings in a Python dict. Issues:
- `os.path.expanduser('~')` called at import time (lines 66, 149, 232) — value baked into module at load
- Adding a language requires modifying source code
- No external `.json` or `.po` file support

---

### F6-24 | MEDIUM | File Accessibility Check Uses Append Mode
**File:** `backend/ingestion/watcher.py:123-130`
**Skills:** security-scan, correctness-check

```python
def _is_file_accessible(self, file_path: str) -> bool:
    try:
        with open(file_path, "ab") as f:
            pass
        return True
```

Opening a file in `"ab"` (append binary) mode to test accessibility. While this is unlikely to corrupt data (no bytes written), it modifies the file's access timestamp and could trigger other watchers.

---

### F6-25 | MEDIUM | Unseeded Randomness in Rate Limiter
**File:** `ingestion/hltv/rate_limit.py:17-20`
**Skills:** correctness-check

```python
jitter = random.uniform(-0.5, 0.5)
delay = max(2.0, random.uniform(min_d, max_d) + jitter)
```

CLAUDE.md requires: "randomness must be seeded, isolated, documented." While random delays are intentionally non-deterministic for anti-detection, this should be documented with a comment explaining why seeding is deliberately omitted.

---

### F6-26 | MEDIUM | SpatialEngine Ignores Z-Level Coordination
**File:** `core/spatial_engine.py:16-23`
**Skills:** correctness-check

```python
def world_to_normalized(x, y, map_name):
    meta = get_map_metadata(map_name)
    return meta.world_to_radar(x, y)
```

The spatial engine passes only (x, y) to `world_to_radar()`. For multi-level maps (Nuke, Vertigo), Z-level determines which floor's radar to use. The Z coordinate is never considered in this pipeline, potentially placing players on the wrong level.

---

### F6-27 | LOW | Empty constants.py File
**File:** `core/constants.py`

File contains no code — only an empty line. Dead file that should be removed or populated.

---

### F6-28 | LOW | Pro Ingest Hardcodes "ProPlayer" Name
**File:** `ingestion/pipelines/pro_ingest.py:36`

```python
match_stats = PlayerMatchStats(
    player_name="ProPlayer", demo_name=demo_path.name, is_pro=True, **match_stats_dict
)
```

All pro players get the same name. The main pipeline (`run_ingestion.py`) correctly extracts per-player names via `parse_demo()`. This legacy pipeline is misleading if used.

---

### F6-29 | LOW | Missing Type Hints in faceit_api.py
**File:** `backend/data_sources/faceit_api.py:9`

```python
def fetch_faceit_data(nickname):  # no type annotation
```

Public function without type hints. CLAUDE.md requires "Type hints on all public interfaces."

---

### F6-30 | LOW | Mutable List in Frozen Dataclass
**File:** `backend/data_sources/demo_format_adapter.py:87`

```python
@dataclass(frozen=True)
class ProtoChange:
    affected_events: List[str]  # mutable list inside frozen dataclass
```

`List[str]` is mutable even inside a `frozen=True` dataclass. The list itself can be modified despite the frozen flag. Should use `tuple` for true immutability.

---

### F6-31 | LOW | Repeated Imports Inside Functions
**File:** `ingestion/steam_locator.py:121-124`

```python
def _queue_if_new(demo_path):
    from sqlmodel import select
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask
```

Imports executed on every function call. While this avoids circular imports, it adds overhead for each demo file queued.

---

### F6-32 | LOW | Class-Level Mutable Cache in AssetAuthority
**File:** `core/asset_manager.py:93`

```python
class AssetAuthority:
    _cache: Dict[str, SmartAsset] = {}  # shared across all instances
```

Class-level mutable dict shared across instances. Since AssetAuthority is a singleton, this works correctly, but the pattern is fragile — if the singleton invariant is ever broken, all instances share stale cache.

---

### F6-33 | LOW | Event Registry Entries May Have Stale Handler References
**File:** `backend/data_sources/event_registry.py`

Pure data file with 24 event specifications. Some entries have `implemented=True` and `handler_path` values that reference specific module paths. If those handlers are moved or renamed, the registry becomes stale. No runtime validation of handler existence.

---

### F6-34 | LOW | Lifecycle Manager Deletes Without Soft-Delete
**File:** `ingestion/registry/lifecycle.py:24`

```python
f.unlink()
logger.info("Cleaned up old demo: %s", f.name)
```

Direct `unlink()` (hard delete) of demo files without soft-delete option. CLAUDE.md recommends "Soft delete preferred over hard delete for critical data."

---

## Cross-Phase Verification

### Quality Gate: Timeout/Retry/Circuit-Breaker on External APIs

| API | Timeout | Retry | Circuit Breaker |
|-----|---------|-------|-----------------|
| Steam Web API | 5s | 3x exponential (1/2/4s) | None |
| FACEIT API | 10s | Rate-limited (6s/req) | Max 3 retries on 429 |
| HLTV Scraping | 60s per page | Backoff tier (45-90s) | **MISSING** |
| HLTV Downloader | 120s download | None | None |

**Verdict**: Steam API has good resilience. FACEIT has bounded retries. HLTV scraping pipeline lacks circuit breaker (F6-10).

### Quality Gate: Credential Handling

| Service | Key Source | Storage | Exposure Risk |
|---------|-----------|---------|---------------|
| Steam API | `get_setting("STEAM_API_KEY")` | Config DB | Logged in debug (steam_api.py:44) |
| FACEIT API | `get_setting("FACEIT_API_KEY")` | Config DB | Not logged |
| HLTV | No key needed | N/A | IP-based rate limiting |

**Verdict**: API keys sourced from config (not hardcoded). Steam API key potentially logged at DEBUG level via `app_logger.debug("Resolving vanity URL '%s'", vanity_url.strip())` — the key itself is not logged, but the request function passes it in params. Acceptable at DEBUG level.

### Quality Gate: Session Engine Cross-Reference with Phase 5

| Phase 5 Component | Session Engine Integration | Status |
|--------------------|---------------------------|--------|
| IngestionManager | Parallel implementation — `_digester_daemon_loop` uses `run_ingestion.process_queued_tasks()` | Dual pipeline exists |
| Console/ServiceSupervisor | Console starts services; session_engine runs daemons | Complementary |
| Belief Calibration (G-07) | `_run_belief_calibration()` NOT wired into Teacher daemon | **CONFIRMED MISSING** |
| Meta-shift detection | `_check_meta_shift()` called after retraining | Wired correctly |

### AIstate.md Reconciliation

| Issue | Phase 6 Finding | Status |
|-------|-----------------|--------|
| G-07: Belief Calibration Teacher wiring | Confirmed: `_run_belief_calibration()` does NOT exist in session_engine.py | **Still missing** |
| G-03: Missing commit | F6-03 confirms `_commit_trained_sample_count()` lacks `session.commit()` | **NEW FINDING** |

---

## Summary Statistics

### By Severity
| Severity | Count | Percentage |
|----------|------:|----------:|
| CRITICAL | 4 | 11.8% |
| HIGH | 6 | 17.6% |
| MEDIUM | 16 | 47.1% |
| LOW | 8 | 23.5% |
| **Total** | **34** | **100%** |

### By Category
| Category | Count |
|----------|------:|
| Anti-Fabrication | 1 |
| Security/Legal | 1 |
| Data Integrity (missing commit) | 1 |
| Deprecation | 1 |
| Logging Discipline | 2 |
| Code Hygiene (sys.path, duplicates) | 3 |
| Resilience (circuit breaker, retries) | 3 |
| Correctness (undefined vars/functions) | 4 |
| Architecture (legacy pipeline, governance) | 3 |
| Other (memory, threading, immutability) | 15 |

### Cumulative Audit Statistics (Phases 1-6)
| Phase | Files | Issues | CRITICAL | HIGH | MEDIUM | LOW |
|-------|------:|-------:|---------:|-----:|-------:|----:|
| Phase 1 | 29 | 37 | 2 | 3 | 15 | 17 |
| Phase 2 | 25 | 42 | 4 | 5 | 18 | 15 |
| Phase 3 | 41 | 38 | 4 | 6 | 19 | 9 |
| Phase 4 | 19 | 24 | 1 | 3 | 14 | 6 |
| Phase 5 | 20 | 38 | 3 | 5 | 20 | 10 |
| Phase 6 | 38 | 34 | 4 | 6 | 16 | 8 |
| **Total** | **172** | **213** | **18** | **28** | **102** | **65** |
