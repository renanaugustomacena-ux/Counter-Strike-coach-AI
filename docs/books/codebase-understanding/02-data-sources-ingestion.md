# Chapter 2: Data Sources and Ingestion

This chapter provides an exhaustive reference of every class, function, constant, and mechanism found in the data-source and ingestion subsystems of the Macena CS2 Analyzer. The material is organized into four major sections that mirror the physical layout of the codebase: **Data Sources** (the modules that acquire raw data from demos, Steam, FACEIT, and HLTV), **Backend Ingestion** (CSV migration, resource governance, and filesystem watching), **Top-Level Ingestion** (the demo loader, integrity checking, pipelines, registry, and Steam locator), and **Root-Level Scripts** (the entry points that orchestrate batch ingestion, single-demo processing, background workers, and HLTV synchronization).

---

## 1. Data Sources (`backend/data_sources/`)

### 1.1 `__init__.py`

Empty init file. The package exposes no public API at the `__init__` level; consumers import individual modules directly.

---

### 1.2 `demo_format_adapter.py`

**Purpose.** Version-aware CS2 demo file handling. Provides pre-parse validation (size, header magic bytes, corruption detection), format version detection, field-name mapping for version-specific column names, and a changelog of known protobuf schema transitions. This module wraps the existing `demo_parser` -- it does not replace it.

#### Constants

| Name | Value | Description |
|------|-------|-------------|
| `DEMO_MAGIC_V2` | `b"PBDEMS2\x00"` | CS2 demo file magic bytes (first 8 bytes). |
| `DEMO_MAGIC_LEGACY` | `b"HL2DEMO\x00"` | CS:GO legacy demo format magic bytes (unsupported). |
| `MIN_DEMO_SIZE` | `10 * 1024 * 1024` (10 MB) | DS-12 invariant. Real CS2 demos are 50+ MB; anything smaller is likely corrupted. |
| `MAX_DEMO_SIZE` | `5 * 1024**3` (5 GB) | Safety cap preventing pathological files from consuming resources. |

#### Dataclass `FormatVersion` (frozen)

Fields: `name: str`, `magic: bytes`, `description: str`, `supported: bool`. Represents a known CS2 demo format specification.

#### Dict `FORMAT_VERSIONS`

Maps version name strings to `FormatVersion` instances. Two entries:

- `"cs2_protobuf"` -- Source 2 protobuf format, supported.
- `"csgo_legacy"` -- Source 1 legacy format, not supported.

#### Dataclass `ProtoChange` (frozen)

Fields: `date: str`, `description: str`, `affected_events: Tuple[str, ...]`, `migration_notes: str`. Records a known protobuf schema change. The `affected_events` field uses `Tuple` instead of `List` to satisfy the frozen-dataclass constraint (F6-30).

#### List `PROTO_CHANGELOG`

Three known protobuf changes:

1. 2024-03-01: Initial format stabilization.
2. 2024-09-15: Sub-tick movement data update (backward compatible).
3. 2025-06-01: Updated `player_death` event with additional flags (`wipe`, `noreplay`).

#### Class `DemoFormatAdapter`

**`validate_demo(demo_path: str) -> Dict`** -- Comprehensive pre-parse validation. Checks file existence, size bounds (`MIN_DEMO_SIZE` to `MAX_DEMO_SIZE`), reads 8-byte header and matches against known format versions, verifies the format is supported, and runs corruption pattern checks. Returns a dict with keys: `valid` (bool), `version` (str), `file_size` (int), `error` (str or None), `warnings` (List[str]).

**`_detect_version(header: bytes) -> str`** -- Iterates `FORMAT_VERSIONS` comparing magic bytes; returns the version name or `"unknown"`.

**`_check_corruption_patterns(demo_path: str, file_size: int) -> List[str]`** -- Two patterns: (1) file size not 4-byte aligned suggests truncation; (2) file under 50 MB suggests partial/corrupted recording.

**`get_field_mapping(version: str) -> Dict[str, str]`** -- Returns a dict mapping canonical Macena field names to actual demoparser2 field names. Currently returns the default mapping (stable demoparser2 conventions) regardless of version, but the interface enables future adaptation.

**`get_changelog() -> List[ProtoChange]`** -- Returns a copy of `PROTO_CHANGELOG`.

#### Function `validate_demo_file(demo_path: str) -> Dict`

Convenience wrapper. Instantiates `DemoFormatAdapter` and calls `validate_demo()`.

---

### 1.3 `demo_parser.py`

**Purpose.** Core demo parsing module. Uses `demoparser2.DemoParser` to extract aggregate player statistics and sequential tick data from CS2 `.dem` files. Implements HLTV 2.0 rating calculation inline (vectorized DataFrame version).

#### Constants

| Name | Value | Description |
|------|-------|-------------|
| `RATING_BASELINE_KPR` | Imported `BASELINE_KPR` from `rating.py` | HLTV 2.0 kills-per-round baseline. |
| `RATING_BASELINE_SURVIVAL` | Imported `BASELINE_DPR_COMPLEMENT` | HLTV 2.0 survival baseline (1 - deaths per round). |
| `RATING_BASELINE_KAST` | Imported `BASELINE_KAST` | HLTV 2.0 KAST baseline. |
| `RATING_BASELINE_ADR` | Imported `BASELINE_ADR` | HLTV 2.0 average damage per round baseline. |
| `RATING_BASELINE_ECON` | `85.0` | Economy-specific baseline (not part of HLTV 2.0). |
| `DEFAULT_KAST_FALLBACK` | `None` | R3-01: No fabricated fallback. NaN propagates to rating. |
| `DEMO_PARSE_TIMEOUT_SECONDS` | `300` (5 minutes) | Base timeout for demo parsing operations. |

#### Function `parse_demo(demo_path: str, target_player: Optional[str] = None) -> pd.DataFrame`

Primary aggregate-stats entry point. Creates a `DemoParser`, parses `round_end` events in a `ThreadPoolExecutor` with a dynamic timeout (from `_get_parse_timeout`). Returns an empty DataFrame on timeout, missing events, or any exception. On success, delegates to `_extract_stats_with_full_fields`.

#### Function `_extract_stats_with_full_fields(parser, total_rounds, target_player) -> pd.DataFrame`

Parses tick data for `player_name`, `name`, `kills_total`, `deaths_total`, `damage_total`. Groups by player, computes per-round averages (`avg_kills`, `avg_deaths`, `avg_adr`, `kd_ratio`). Calls `_add_event_stats_safe` for headshot/accuracy/KAST. Computes per-round variance via `_compute_per_round_variance`. Then applies the full HLTV 2.0 rating pipeline:

1. `kpr` and `dpr` from per-round averages.
2. `rating_impact` = `kpr * 2.13 + avg_adr / 100 * 0.42`.
3. `rating_survival` = `1.0 - dpr`.
4. `rating_kast`, `rating_kpr`, `rating_adr` stored as components.
5. Normalized rating: average of five components each scaled to their baseline.
6. `econ_rating` = `avg_adr / RATING_BASELINE_ECON`.
7. `impact_rounds` aliased to `rating_impact` for legacy frontend/ML compatibility.

#### Function `_resolve_name_column(df: pd.DataFrame, candidates: list) -> Optional[str]`

Finds the player name column from a prioritized candidate list. Different demoparser2 event types use different column names (`player_name`, `attacker_name`, `user_name`).

#### Function `_compute_per_round_variance(parser) -> Optional[pd.DataFrame]`

Parses `player_death` and `player_hurt` events. Groups kills and damage by player and round number. Returns a DataFrame with `kill_std` and `adr_std` per player. Returns `None` on failure.

#### Function `_add_event_stats_safe(parser, df, total_rounds)`

Extracts per-player headshot percentage, accuracy, and KAST from `player_hurt`, `weapon_fire`, and `player_death` events. Initializes all stats to `0.0` (meaning "no data", not "0%"). Sets a `data_quality` flag: `"none"` (no event data), `"partial"` (some players missing), `"complete"` (all players have real data). Uses `estimate_kast_from_stats` for KAST calculation. Tries multiple column name candidates for the assister column (`assister_name`, `assister`, `assist_player_name`) per C-05.

#### Function `_get_parse_timeout(demo_path: str) -> int`

H-02: Dynamic timeout scaled by file size. Returns `max(300, file_size_mb * 3)` seconds. Large pro demos need more time.

#### Function `parse_sequential_ticks(demo_path: str, target_player: str, rate: int = None, start_tick: int = 0) -> pd.DataFrame`

Parses full per-tick data with all WP6 fields (identity, position/view, vitals, tactical state, equipment/economy, round context, cumulative stats, technical). Fields list includes 37 columns. Runs in a `ThreadPoolExecutor` with dynamic timeout. Renames columns for downstream compatibility: `weapon_name` -> `active_weapon`, `current_equip_value` -> `equipment_value`, player name column -> `player_name`. Applies sampling rate (`rate` parameter, defaults to 1 -- no decimation per project invariant). Filters by `start_tick` and `target_player`.

---

### 1.4 `event_registry.py`

**Purpose.** Canonical specification of CS2 game events. A documentation and coverage-tracking registry derived from SteamDatabase game event dumps.

#### Dataclass `GameEventSpec` (frozen)

Fields: `name: str`, `category: str` (one of "round", "combat", "utility", "economy", "movement", "meta"), `fields: Dict[str, str]`, `priority: str` ("critical", "standard", "optional"), `implemented: bool`, `handler_path: Optional[str]`, `notes: str`.

Note F6-33: `handler_path` references are not validated at registration time. Stale references are silent.

#### Dict `EVENT_REGISTRY`

Contains 22 event specifications organized by category:

**Round lifecycle** (5 events): `round_end` (critical, implemented), `round_start` (standard, not implemented), `round_freeze_end` (standard, implemented), `round_mvp` (optional, not implemented), `begin_new_match` (standard, not implemented).

**Combat** (3 events): `player_death` (critical, implemented), `player_hurt` (critical, implemented), `weapon_fire` (critical, implemented).

**Bomb** (4 events): `bomb_planted` (critical, implemented), `bomb_defused` (critical, implemented), `bomb_pickup` (optional, not implemented), `bomb_dropped` (optional, not implemented).

**Utility** (7 events): `flashbang_detonate` (standard, not implemented), `hegrenade_detonate` (standard, not implemented), `smokegrenade_detonate` (standard, not implemented), `inferno_startburn` (standard, not implemented), `inferno_expire` (optional, not implemented), `decoy_started` (optional, not implemented), `player_blind` (critical, implemented).

**Economy** (2 events): `item_purchase` (optional, not implemented), `item_pickup` (optional, not implemented).

**Player state / meta** (3 events): `player_connect` (optional, not implemented), `player_disconnect` (optional, not implemented), `player_team` (standard, not implemented).

#### Functions

**`get_implemented_events() -> List[str]`** -- Returns names of all events where `implemented=True`.

**`get_unimplemented_events(priority: Optional[str] = None) -> List[str]`** -- Returns unimplemented event names, optionally filtered by priority.

**`get_events_by_category(category: str) -> List[GameEventSpec]`** -- Returns all events in a given category.

**`get_coverage_report() -> Dict[str, Any]`** -- Generates a coverage report with total/implemented/unimplemented counts, overall percentage, breakdowns by priority and category.

---

### 1.5 `faceit_api.py`

**Purpose.** Lightweight FACEIT data fetcher for Elo and Level lookup.

#### Function `fetch_faceit_data(nickname: str) -> Dict[str, Any]`

Fetches FACEIT Elo and skill level for a CS2 player by nickname. Uses the `FACEIT_API_KEY` from `get_setting()`. Returns empty dict if the key is missing or set to `"YOUR_FACEIT_KEY"`. Makes an HTTP GET to `https://open.faceit.com/data/v4/players` with a 10-second timeout. Returns `faceit_id`, `faceit_elo`, `faceit_level` on success.

---

### 1.6 `faceit_integration.py`

**Purpose.** Full FACEIT API client with rate limiting, match history fetching, and demo downloading.

#### Exception `FACEITAPIError`

Raised on FACEIT API request failures.

#### Class `FACEITIntegration`

**Constants:** `BASE_URL = "https://open.faceit.com/data/v4"`, `RATE_LIMIT_DELAY = 6` (seconds, enforcing 10 req/min free tier limit).

**`__init__(api_key: Optional[str] = None)`** -- Initializes with API key from parameter or `get_setting("FACEIT_API_KEY")`. Creates a `requests.Session` with Bearer auth header.

**`_rate_limited_request(endpoint, params, _retry_count) -> dict`** -- Enforces rate limit delay between requests. Handles 429 (rate limit) with exponential backoff up to `MAX_429_RETRIES=3`. Caps `Retry-After` at 300 seconds.

**`get_player_id(nickname: str) -> Optional[str]`** -- Resolves FACEIT nickname to player ID.

**`fetch_match_history(player_id, game="cs2", limit=20) -> List[Dict]`** -- Fetches recent match history. Caps limit at 100.

**`get_match_details(match_id: str) -> Optional[Dict]`** -- Gets detailed match information.

**`download_demo(match_id: str, output_dir: Path) -> Optional[Path]`** -- Downloads demo file for a match. Sanitizes `match_id` to prevent directory traversal (R3-09). Validates HTTPS URL scheme to prevent SSRF (DS-08). Streams download with `MAX_DEMO_SIZE` cap. Returns the output path on success.

#### Function `sync_faceit_matches(nickname, output_dir, limit=20) -> List[Dict]`

Convenience function. Instantiates `FACEITIntegration`, resolves player ID, fetches match history, attempts demo download for each match. Returns a list of match metadata dicts with download status.

---

### 1.7 HLTV Subpackage (`hltv/`)

#### 1.7.1 `hltv/__init__.py`

Empty init file.

#### 1.7.2 `hltv/docker_manager.py`

**Purpose.** FlareSolverr Docker container lifecycle management. Ensures the container is running before HLTV sync starts.

**Constants:**

| Name | Value | Description |
|------|-------|-------------|
| `_HEALTH_URL` | `"http://localhost:8191/"` | FlareSolverr health endpoint. |
| `_HEALTH_TIMEOUT_S` | `5` | Health check HTTP timeout. |
| `_MAX_WAIT_S` | `45` | Maximum wait for container readiness. |
| `_POLL_INTERVAL_S` | `3` | Polling interval during wait. |

**Functions:**

**`_is_docker_available() -> bool`** -- Runs `docker info` with a 10-second timeout. Returns True if returncode is 0.

**`_is_flaresolverr_healthy() -> bool`** -- GETs the health URL. Returns True on HTTP 200.

**`_wait_for_healthy(timeout_s) -> bool`** -- Polls health endpoint at `_POLL_INTERVAL_S` intervals until healthy or deadline.

**`ensure_flaresolverr(project_root: str | None = None) -> bool`** -- Main entry point. Strategy: (1) already healthy -> True; (2) `docker start flaresolverr`; (3) `docker compose -f docker-compose.yml up -d` if `project_root` provided and file exists (DS-05: validates path before subprocess); (4) returns False if all attempts fail.

**`stop_flaresolverr() -> None`** -- Gracefully stops the container with `docker stop flaresolverr`.

#### 1.7.3 `hltv/flaresolverr_client.py`

**Purpose.** REST client for the local FlareSolverr Docker container. Bypasses Cloudflare via a headless browser proxy.

**Constants:** `_DEFAULT_URL = "http://localhost:8191/v1"`, `_DEFAULT_TIMEOUT = 60`.

**Class `FlareSolverrClient`:**

**`__init__(base_url, timeout)`** -- Stores config. `_session_id` starts as None.

**`is_available() -> bool`** -- Hits root health endpoint (strips `/v1`). Returns True on HTTP 200.

**`create_session() -> str | None`** -- POSTs `sessions.create` to FlareSolverr. Stores session ID for cookie reuse. Returns the session ID or None.

**`destroy_session() -> None`** -- POSTs `sessions.destroy` if a session exists.

**`get(url, max_retries=None) -> str | None`** -- Fetches a URL through FlareSolverr. Class constants: `_MAX_RETRIES=3`, `_BACKOFF_BASE=5`. Retries with exponential backoff (`5s, 15s, 45s`). Stores `self.last_error` on failure. Returns decoded HTML body on success or `None` on any error. If a session exists, includes session ID in payload for cookie reuse.

#### 1.7.4 `hltv/stat_fetcher.py`

**Purpose.** Deep HLTV player statistics scraper. Fetches pro player stats from HLTV.org player pages via FlareSolverr and saves to `ProPlayer` + `ProPlayerStatCard` in `hltv_metadata.db`.

**Constants:**

| Name | Value | Description |
|------|-------|-------------|
| `CRAWL_DELAY_MIN_SECONDS` | `2` | Minimum delay between requests. |
| `CRAWL_DELAY_MAX_SECONDS` | `7` | Maximum delay between requests. |
| `_HLTV_ROBOTS_URL` | `"https://www.hltv.org/robots.txt"` | robots.txt URL for compliance check. |
| `_HLTV_BASE_URL` | `"https://www.hltv.org"` | HLTV base URL. |
| `HLTV_STATS_START_DATE` | `"2021-06-01"` | Date range start for sub-page queries. |
| `HLTV_STATS_END_DATE` | `"2026-05-06"` | Date range end for sub-page queries. |

**Function `check_robots_txt(target_url) -> bool`** -- Checks HLTV robots.txt. Handles Cloudflare interference (DP-04): if the response is not parseable as valid robots.txt (no entries found), it proceeds with caution and returns True. Returns False only if explicitly disallowed.

**Class `HLTVStatFetcher`:**

**`__init__()`** -- Requires `beautifulsoup4`. Instantiates `FlareSolverrClient` and `get_hltv_db_manager()`.

**Class attribute `_consecutive_failures: int = 0`** -- Tracks consecutive failures for adaptive delay calculation.

**Class attribute `_MIN_VIABLE_FIELDS = {"rating", "kpr", "maps_played"}`** -- Minimum fields required before persisting a player's stats (H2 validation).

**`_select_fallback(soup, selectors, description) -> list`** -- Static method. Tries multiple CSS selectors in order, returns first non-empty result. Logs a warning when a primary selector fails and a fallback activates.

**`preflight_check() -> bool`** -- Verifies scraping is enabled via `HLTV_SCRAPING_ENABLED` setting and `check_robots_txt()`.

**`fetch_top_players() -> List[str]`** -- Discovers player stat page URLs. Primary strategy: uses `fetch_top_teams()` to get rosters from the team ranking page (robots.txt compliant), then builds stat URLs per player. Fallback: scrapes `/stats/players` directly (no query params to stay compliant).

**`fetch_top_teams(count=30) -> List[Dict[str, Any]]`** -- Scrapes `/ranking/teams/` for team rankings and rosters. Returns list of dicts with `hltv_id`, `name`, `world_rank`, `players` (list of `{hltv_id, nickname, profile_url}`). Uses fallback CSS selectors for resilience against layout changes. Validates stale responses (H2): warns if team count exceeds player count.

**`save_teams_and_players(teams) -> List[str]`** -- Upserts `ProTeam` and `ProPlayer` records in `hltv_metadata.db`. Links players to teams. Returns URLs of players that need stat scraping (no existing `ProPlayerStatCard`).

**`fetch_and_save_player(url) -> bool`** -- Fetches player stats and saves to DB. Validates minimum viable fields (H2): skips players missing `rating`, `kpr`, or `maps_played`, or with `rating <= 0`.

**`_fetch_player_stats(url) -> Optional[Dict[str, Any]]`** -- Deep crawl of one player. Parses overview page, then fetches sub-pages (individual, career, opponents, clutches) with date-range queries. Assembles composite data including opening kill ratio, multikill counts, clutch win count, and multikill round percentage. Stores detailed stats as JSON blob.

**`_save_to_db(hltv_id, nickname, data) -> bool`** -- Upserts `ProPlayer` (with profile metadata: real_name, country, age) and `ProPlayerStatCard` (rating_2_0, kpr, dpr, adr, kast, impact, hs_pct, maps_played, opening stats, clutch stats, detailed JSON blob).

**`_fetch_sub_stats(url, parser_func) -> Dict`** -- Generic sub-page fetcher with adaptive delay (increases crawl delay after consecutive failures).

**`_safe_float(text) -> float`** -- Robust float parsing handling `"-"`, `"N/A"`, `"nan"`, commas, and percentage signs. Returns `0.0` for unparseable values.

**`_parse_player_summary_box(soup) -> Dict`** -- Parses the player summary stat-box on overview pages. Extracts `rating_2_0`, `kast`, `dpr`, `adr`, `kpr` from dedicated elements. Returns `raw_boxes` dict with `above_avg` flags.

**`_parse_profile(soup) -> Dict`** -- Extracts `real_name`, `country`, `age` from the profile section.

**`_parse_overview(soup) -> Dict`** -- Main overview page parser. Combines profile, summary boxes, and legacy stats rows. Maps extracted values to canonical field names. Computes `kd_ratio` from `kpr/dpr`. Extracts player nickname from multiple fallback selectors.

**`_parse_role_stats(soup) -> Dict`** -- Parses 40 role stats across 3 sides (combined, CT, T) from `.role-stats-row` elements. Side detection via CSS class (`.stats-side-combined`, `.stats-side-ct`, `.stats-side-t`).

**`_parse_section_scores(soup) -> Dict[str, int]`** -- Parses 7 section scores (e.g., Firepower, Entrying, Utility) from the combined side. Extracts `N/100` score values.

**`_parse_individual(soup) -> Dict[str, float]`** -- Parses 24 individual stats from the individual stats page. Maps labels to canonical keys using an explicit `label_map` dict covering kills, deaths, KD ratio, opening kills/deaths, multi-kill rounds (0k through 5k), and weapon-type kills (rifle, sniper, SMG, pistol, grenade, other).

**`_parse_opponents(soup) -> List[Dict]`** -- Parses per-team opponent stats: team name, maps played, KD diff, KD ratio, rating.

**`_parse_clutches(soup) -> Dict[str, int]`** -- Parses clutch tier counts (1on1, 1on2, etc.) from the all-tier clutches page.

**`_parse_career(soup) -> Dict[str, Dict[str, float]]`** -- Parses year-by-year career ratings across contexts (all, online, LAN, majors).

---

### 1.8 `hltv_scraper.py`

**Purpose.** HLTV statistics sync entry point. Thin wrapper around `HLTVStatFetcher`.

#### Function `run_hltv_sync_cycle(limit=50) -> int`

Instantiates `HLTVStatFetcher`, runs preflight check, discovers top players, and syncs up to `limit` players. Returns the count of successfully synced players. Handles `ImportError` (missing beautifulsoup4) gracefully.

---

### 1.9 `round_context.py`

**Purpose.** Extracts round boundaries and bomb events from CS2 demos for enriching tick data with round numbers and time-in-round.

#### Function `extract_round_context(demo_path: str) -> pd.DataFrame`

Parses `round_freeze_end` and `round_end` events. Builds a DataFrame with columns `round_number` (1-based), `round_start_tick` (when freeze time ends), `round_end_tick`. Pairs freeze_end ticks to round_end ticks using temporal matching: for each round, selects the last freeze_end tick that falls between the previous round_end and the current round_end. Falls back to previous round_end as start when no matching freeze_end is found.

#### Function `extract_bomb_events(demo_path: str) -> pd.DataFrame`

Parses `bomb_planted`, `bomb_defused`, and `bomb_exploded` (H-07) events. Returns a DataFrame with `tick` and `event_type` ("planted", "defused", "exploded") columns, sorted by tick.

#### Function `assign_round_to_ticks(df_ticks, round_context, tick_rate=64.0) -> pd.DataFrame`

Assigns `round_number` and `time_in_round` to each tick row using `pd.merge_asof` for efficient O(n log m) assignment. Each tick is matched to the round whose `round_start_tick` is the largest value <= tick. Warmup ticks (before first round) default to round 1. `time_in_round` is computed as `(tick - round_start_tick) / tick_rate`, clipped to [0.0, 115.0] seconds.

---

### 1.10 `steam_api.py`

**Purpose.** Steam Web API client for profile fetching and vanity URL resolution.

#### Constants

| Name | Value | Description |
|------|-------|-------------|
| `MAX_RETRIES` | `3` | Maximum HTTP retry attempts. |
| `BACKOFF_DELAYS` | `[1, 2, 4]` | Exponential backoff delays in seconds. |

#### Function `_request_with_retry(url, params, timeout=5, max_total_timeout=20) -> requests.Response`

HTTP GET with exponential backoff retry. DS-03: enforces a `max_total_timeout` hard ceiling via monotonic clock to prevent unbounded blocking. Per-request timeout is capped to remaining time budget. Does not retry on HTTP 4xx/5xx (raises immediately).

#### Function `resolve_vanity_url(vanity_url, api_key) -> Optional[str]`

Resolves a Steam Custom URL to a 64-bit Steam ID via `ISteamUser/ResolveVanityURL/v0001/`. Returns the steamid string or None.

#### Function `fetch_steam_profile(steam_id, api_key) -> Optional[dict]`

Fetches a player profile from `ISteamUser/GetPlayerSummaries/v0002/`. Auto-resolves vanity URLs if `steam_id` is not numeric. Validates Steam64 ID format (R3-M04: 17-digit numeric string). Returns the first player dict or None. Provides specific error message for 403 Forbidden (invalid/restricted API key).

---

### 1.11 `steam_demo_finder.py`

**Purpose.** Automatic discovery of CS2 demo files from the Steam installation directory.

#### Exception `SteamNotFoundError`

Raised when Steam installation cannot be located.

#### Class `SteamDemoFinder`

**Class attributes:** `LINUX_PATHS` (two paths: `~/.steam/steam`, `~/.local/share/Steam`), `CS2_REPLAY_PATH` (relative path to CS2 replays directory).

**`__init__()`** -- On Windows, dynamically generates `WINDOWS_PATHS` via `_generate_windows_paths()`.

**`_generate_windows_paths() -> List[Path]`** (classmethod) -- Enumerates all available drive letters using `windll.kernel32.GetLogicalDrives()` bitmasking. Combines each drive with common Steam subdirectory suffixes (`Program Files (x86)/Steam`, `Program Files/Steam`, `Steam`).

**`find_steam_directory() -> Optional[Path]`** -- Locates Steam installation. On Windows: tries registry first (`_get_steam_path_from_registry`), then common paths. On Linux: checks known paths.

**`_get_steam_path_from_registry() -> Optional[Path]`** -- Reads `HKEY_CURRENT_USER\Software\Valve\Steam\SteamPath` from Windows registry.

**`find_cs2_replay_directory() -> Optional[Path]`** -- Combines Steam directory with `CS2_REPLAY_PATH`.

**`scan_recent_demos(days=7) -> List[Tuple[Path, datetime]]`** -- Globs `*.dem` in replay directory. Filters by modification time (UTC). Returns sorted list (newest first) of (filepath, mtime) tuples.

**`get_demo_metadata(filepath: Path) -> dict`** -- Extracts metadata from demo filename and filesystem: `filename`, `filepath`, `size_mb`, `modified` (ISO format), and extracted `map` name if filename contains underscore.

#### Function `auto_discover_steam_demos(days=7) -> List[dict]`

Convenience function. Instantiates `SteamDemoFinder`, scans recent demos, returns list of metadata dicts.

Note F6-11: Steam path discovery is also performed in `ingestion/steam_locator.py` (primary). This module is supplementary. Consolidation deferred.

---

### 1.12 `trade_kill_detector.py`

**Purpose.** Identifies trade kills from demo death events. A trade kill occurs when a player is killed within a short time window after they killed an opponent, and the retaliating killer is a teammate of the original victim.

#### Constants

| Name | Value | Description |
|------|-------|-------------|
| `TRADE_WINDOW_S` | `3.0` | Trade window in seconds. |
| `DEFAULT_TICK_RATE` | `64` | Default server tick rate. |
| `TRADE_WINDOW_TICKS` | `192` (`3.0 * 64`) | Trade window in ticks at default rate. |

#### Dataclass `TradeKillResult`

Fields: `total_kills: int`, `trade_kills: int`, `players_traded: int`, `trade_details: List[Dict]`. Properties: `trade_kill_ratio` (trade_kills / total_kills), `was_traded_ratio` (players_traded / total_kills).

#### Function `build_team_roster(parser) -> Dict[str, int]`

Builds a `player_name -> team_num` mapping from early-match tick data. Uses the first 10th percentile of ticks for stable team assignment. `team_num` values 2 and 3 represent the two competing teams. Returns lowercase-keyed dict.

#### Function `get_round_boundaries(parser) -> List[int]`

Extracts round-end tick boundaries from `round_end` events. Prepends 0 as match start.

#### Function `assign_round_numbers(death_ticks: pd.Series, round_boundaries: List[int]) -> pd.Series`

Assigns round numbers to death events using `np.searchsorted` (right-sided). Returns 1-indexed round numbers.

#### Function `detect_trade_kills(deaths_df, team_roster, trade_window=None, tick_rate=DEFAULT_TICK_RATE) -> TradeKillResult`

Core detection algorithm. For each kill K at tick T in round R: looks backward in the SAME ROUND for kills by the victim; if the victim killed a teammate of K's killer within the trade window, marks K as a trade kill. M-05: uses exclusive boundary (`tick - prior_tick >= trade_window` to stop). Only counts the most recent trade opportunity per kill.

#### Function `get_player_trade_stats(result, team_roster) -> Dict[str, Dict[str, float]]`

Aggregates trade kill statistics per player: `trade_kills`, `times_traded`, `avg_response_ticks`.

#### Function `analyze_demo_trades(parser) -> Tuple[TradeKillResult, Dict]`

Full pipeline entry point. Steps: (1) build team roster, (2) parse `player_death` events, (3) assign round numbers, (4) detect trade kills (DS-07: uses actual tick_rate from demo header), (5) per-player aggregation.

---

## 2. Backend Ingestion (`backend/ingestion/`)

### 2.1 `__init__.py`

Empty init file.

---

### 2.2 `csv_migrator.py`

**Purpose.** Migrates external CSV datasets into the project database. Handles player playstyle roles and tournament advanced statistics.

#### Functions

**`_safe_float(value, default=0.0) -> float`** -- F6-17: Module-level safe float parser.

**`_safe_int(value, default=0) -> int`** -- Module-level safe int parser.

#### Class `CSVMigrator`

**`__init__(db_manager: DatabaseManager)`** -- Sets data directory to `Programma_CS2_RENAN/data/external`.

**`run_migration()`** -- Orchestrates migration of all CSVs. Calls `migrate_playstyles()` then `migrate_tournament_stats()`.

**`migrate_playstyles()`** -- Reads `cs2_playstyle_roles_2024.csv`. For each row, checks for existing record by `(player_name, team_name)` for idempotency. Maps `role_overall` to binary role probabilities across 6 roles: `lurker`, `entry` (Spacetaker), `support`, `awper`, `anchor`, `igl`. Creates `Ext_PlayerPlaystyle` records with raw metrics `tapd`, `oap`, `podt`.

**`migrate_tournament_stats()`** -- Reads `tournament_advanced_stats.csv`. Batch commits every 1000 rows. Idempotency check by `(external_match_id, round_num, team_name)` (R3-H05). Creates `Ext_TeamRoundStats` records with kills, deaths, damage, hits, shots, utility_value, money_spent, headshots, first_kills, first_deaths, accuracy, econ_rating.

---

### 2.3 `resource_manager.py`

**Purpose.** Governs system resource usage for background tasks. Ensures the "Digester" daemon does not impact user experience.

#### Module-Level Constants and State

| Name | Value | Description |
|------|-------|-------------|
| `_CPU_SAMPLE_WINDOW` | `10` | Seconds of CPU history to maintain. |
| `_CPU_SAMPLE_COUNT` | `10` | Number of samples in sliding window. |
| `_THROTTLE_HIGH_THRESHOLD` | `85` | Start throttling above this CPU%. |
| `_THROTTLE_LOW_THRESHOLD` | `70` | Stop throttling below this CPU%. |

Module-level state: `_cpu_samples` (deque), `_cpu_sample_lock` (Lock), `_last_cpu_sample_time`, `_current_throttle_state` (bool), `_throttle_lock` (Lock, F6-18: separate from CPU sample lock).

#### Class `ResourceManager`

All methods are `@staticmethod`.

**`_sample_cpu()`** -- Non-blocking CPU sample collection. Only samples if enough time has passed since last sample (`_CPU_SAMPLE_WINDOW / _CPU_SAMPLE_COUNT` interval). Uses `psutil.cpu_percent(interval=None)` for cached value.

**`get_system_stats() -> dict`** -- Returns `cpu` (smoothed average), `cpu_instant`, `ram` (percent). Bootstraps with a quick sample if no history.

**`should_throttle() -> bool`** -- Hysteresis-based throttle decision. In HP mode (`HP_MODE=1` env var), never throttles. RAM > 90% forces throttling immediately. CPU uses hysteresis: starts throttling above 85%, stops below 70%. F6-18: thread-safe read-modify-write under `_throttle_lock`.

**`get_optimal_worker_count(is_high_priority=False) -> int`** -- High priority: `total_cores - 1`. Throttled background: 1. Normal background: `max(1, total_cores // 4)`.

**`is_gui_active() -> bool`** -- Checks for `MacenaCS2Analyzer.exe` or `python.exe` running `main.py` (excluding current process).

**`set_low_priority()`** -- Sets process to `IDLE_PRIORITY_CLASS` on Windows.

**`set_high_priority()`** -- Sets process to `HIGH_PRIORITY_CLASS` on Windows. Falls back to `NORMAL_PRIORITY_CLASS` on failure.

**`log_current_priority()`** -- Logs the actual Windows priority class name.

---

### 2.4 `watcher.py`

**Purpose.** Filesystem watcher using `watchdog` library. Monitors demo directories for new `.dem` files, waits for file stability, and creates `IngestionTask` records in the database.

#### Constants

| Name | Value | Description |
|------|-------|-------------|
| `FILE_STABILITY_CHECK_INTERVAL` | `1.0` | Seconds between size stability checks. |
| `FILE_STABILITY_REQUIRED_CHECKS` | `2` | File must be stable for this many consecutive checks. |
| `FILE_MINIMUM_SIZE` | Imported `MIN_DEMO_SIZE` from `demo_format_adapter` | R3-M20: Uses canonical minimum to prevent accepting files the adapter will reject. |
| `_MAX_STABILITY_ATTEMPTS` | `120` | F6-16: Maximum stability check iterations (~120 seconds at 1s interval). |

#### Class `DemoFileHandler` (extends `FileSystemEventHandler`)

**`__init__(is_pro_folder=False)`** -- Tracks `_pending_files: Dict[str, threading.Timer]` with a threading lock.

**`on_created(event)`** -- Triggers stability check for new `.dem` files.

**`on_moved(event)`** -- Triggers stability check for moved/renamed `.dem` files.

**`_schedule_stability_check(file_path)`** -- Cancels any existing timer for the file, schedules a new `_check_file_stability` call.

**`_check_file_stability(file_path, last_size, stable_count, attempt_count)`** -- Checks if file size has stabilized (not being written to). Guards against infinite timer accumulation (F6-16: max attempts). Handles TOCTOU races (DS-02: wraps `os.path.getsize` in try-except). When stable: verifies minimum size, checks file accessibility (read-only open test), then queues via `_queue_file`.

**`_reschedule_check(file_path, current_size, stable_count, attempt_count)`** -- Reschedules stability check with updated state.

**`_is_file_accessible(file_path) -> bool`** -- F6-24: Opens file in read-only mode to check for write locks.

**`_queue_file(file_path)`** -- IM-01: Final existence check before DB insertion. Creates `IngestionTask` with `status="queued"`. Signals `session_engine.signal_work_available()` for event-driven wake-up.

#### Class `IngestionWatcher`

**`__init__()`** -- Creates a `watchdog.Observer` and two `DemoFileHandler` instances (user and pro).

**`start()`** -- C-01 fix: reads current paths via `get_setting()` instead of stale module-level imports. Ensures directories exist. Schedules observers for both user and pro directories (non-recursive).

**`stop()`** -- Stops and joins the observer.

---

## 3. Top-Level Ingestion (`ingestion/`)

### 3.1 `__init__.py`

Empty init file.

---

### 3.2 `demo_loader.py`

**Purpose.** Handles loading and parsing of CS2 `.dem` files into `DemoFrame` objects for the 2D replay viewer. Implements a multi-pass architecture, HMAC-signed caching, and restricted deserialization.

#### Security Infrastructure

**`_ALLOWED_MODULES`** -- Dict mapping module names to sets of allowed class names for the restricted unpickler. Only `demo_frame` dataclasses and builtins are permitted.

**Class `_SafeUnpickler`** (extends `pickle.Unpickler`) -- DS-01: Blocks deserialization of classes outside the allowlist. Raises `pickle.UnpicklingError` for unauthorized classes.

**`_get_cache_hmac_key() -> bytes`** -- BE-12 / FE-02: Generates a 32-byte random HMAC key on first use, persists with mode 0600. Atomic write (tmp + replace). Subsequent runs read the key back. If key disappears, new key is created and prior caches fail HMAC verification (correct behavior).

**`_pickle_dump_signed(obj, path)`** -- Serializes with pickle, writes HMAC-SHA256 signature (first 32 bytes). Uses atomic write (temp file + fsync + os.replace) to prevent corruption.

**`_pickle_load_verified(path) -> object`** -- Verifies HMAC integrity before deserialization. Uses `_SafeUnpickler` instead of `pickle.loads()`.

#### Class `DemoLoader`

**Class attributes:** `CACHE_DIR` (derived from `DATA_DIR`), `CACHE_VERSION = "v21_vectorized_parse"` (D-26).

**`_try_load_cache(cache_path) -> Optional`** -- Returns cached data if file exists and HMAC verifies; None otherwise.

**`_pass1_positions(parser) -> (pos_by_tick, pass1_failed)`** -- Pass 1: Extracts per-tick `(steamid -> (x,y,z))` positions. Returns dict keyed by tick, values are dicts keyed by steamid. C-08: guards against NULL steamid. Returns `pass1_failed` flag; grenade trajectories will be empty on failure.

**`_pass2_nades(parser, tick_rate, pos_by_tick) -> dict`** -- Pass 2: Links grenade detonations to throws via baseline positions. Returns `nades_by_tick` dict (tick -> List[NadeState]). Processes four types:
- Smoke: start/end pair (`smokegrenade_detonate`/`smokegrenade_expired`)
- Molotov: start/end pair (`inferno_startburn`/`inferno_expire`)
- Flash: single event with 0.5s duration
- HE: single event with 0.5s duration

Each grenade gets a `NadeState` with throw origin (looked up via `get_throw_data`), trajectory, entity ID, and `is_duration_estimated` flag (DS-14) for capped durations. H-05: `MAX_NADE_DURATION = 20 * tick_rate` is a heuristic ceiling. `FADE_TICKS = 5 * tick_rate` extends visibility after ending_tick.

**`_extract_round_starts(parser) -> List[int]`** -- Sorted ticks of `round_freeze_end` events.

**`_extract_bomb_events(parser) -> (plant_events, defuse_ticks)`** -- WR-40: Parses `bomb_planted` (with x/y/z) and `bomb_defused`.

**`_pass3_load_dataframe(parser) -> pd.DataFrame`** -- Pass 3: Parses 22 per-tick fields including steamid, name, position, health, armor, alive state, team, weapon, balance, equipment, round stats, cumulative stats, and movement state. Renames `current_equip_value` -> `equipment_value`.

**`_pass3_preprocess_dataframe(rows_df, round_starts)`** -- D-26: Vectorized preprocessing. Money column resolution (H-03: tries `balance`, `cash`, `money`, `m_iAccount`). Team classification via vectorized string matching. Round index via `np.searchsorted` (O(n log m)). NaN-safe numeric defaults via vectorized fillna.

**`_pass3_build_frames(rows_df, tick_rate, default_map, round_starts, bomb_plant_events, bomb_defuse_ticks, nades_by_tick) -> List[DemoFrame]`** -- Builds `DemoFrame` list from preprocessed data. Groups by tick. Creates `PlayerState` objects per player per tick. Maintains bomb state via sorted-pointer forward scan across all ticks. Creates `BombState` when planted, clears on defuse or new round.

**`_extract_kill_events(parser, pos_by_tick) -> List[GameEvent]`** -- Resolves `player_death` events into `GameEvent[KILL]` positioned at victim's location. DS-09: guards against None/NaN steamid from bot kills or warmup.

**`_compute_segments(round_starts) -> Dict[str, int]`** -- Builds match-half/overtime segment anchors: "Full Match" (tick 0), "First Half" (round 1), "Second Half" (round 13), "Overtime" (round 25).

**`_inject_map_tensors(result, default_map)`** -- ING-02: Attaches map-specific tensors from `data/map_tensors.json` if available.

**`load_demo(path, force_reparse=False) -> Dict[str, Tuple[List[DemoFrame], List[GameEvent], Dict[str, int]]]`** -- Main entry point. Steps: (1) check cache, (2) validate via `validate_demo_file`, (3) parse header for tick_rate and map_name, (4) Pass 1 positions, (5) Pass 2 nades, (6) Pass 3 full states + segmentation (round starts, bomb events, dataframe load, preprocess, build frames), (7) extract kill events, (8) compute segments, (9) inject map tensors, (10) cache result with HMAC signature. Returns dict keyed by map name containing `(frames, game_events, segments)`.

---

### 3.3 `integrity.py`

**Purpose.** Demo file integrity validation. Delegates to `DemoFormatAdapter`.

#### Constants (Legacy)

| Name | Value | Description |
|------|-------|-------------|
| `MIN_SIZE` | `50_000` (50 KB) | Legacy sanity floor (no longer used for validation). |
| `MAX_SIZE` | `900_000_000` (900 MB) | Legacy safety ceiling (no longer used for validation). |

#### Function `compute_sha256(path: str) -> str`

Computes SHA-256 hash of file contents in 8KB chunks.

#### Function `validate_dem_file(path: str) -> bool`

Validates CS2 demo file via `DemoFormatAdapter.validate_demo()`. Raises `FileNotFoundError` if file missing. Raises `ValueError` with specific message for unsupported CS:GO format or other validation failures. Returns True on success.

---

### 3.4 Pipelines (`ingestion/pipelines/`)

#### 3.4.1 `pipelines/__init__.py`

Empty init file.

#### 3.4.2 `pipelines/json_tournament_ingestor.py`

**Purpose.** Parses tournament JSON files and extracts advanced round-level metrics into CSV.

**Constants:** `_REQUIRED_TOP_KEYS = {"id", "slug", "match_maps"}`, `_REQUIRED_MAP_KEYS = {"map_name", "games"}`.

**Function `process_tournament_jsons(json_dir, output_csv)`** -- Globs `*.json` in directory, processes each, saves results to CSV. Logs progress every 100 files.

**Function `_validate_tournament_json(data, file_path) -> bool`** -- R3-M17: Validates expected JSON structure. Checks top-level keys, `match_maps` is list, each map entry is dict with required keys.

**Function `_process_single_json(file_path) -> List`** -- Loads JSON, validates, extracts match stats.

**Functions `_extract_match_stats`, `_extract_map_stats`, `_extract_game_stats`, `_extract_round_stats`** -- Hierarchical extraction: match -> maps -> games -> rounds -> team stats.

**Function `_safe_int(val, default=0) -> int`** -- DS-04: Coerce to int, return default on failure.

**Function `_build_flat_stat(t_stats, match_id, match_slug, map_name, round_num) -> dict`** -- Builds flat stat record. Computes `accuracy` (hits/shots) and `econ_rating` (damage/money_spent).

**Functions `_log_progress`, `_save_results`** -- Progress logging and CSV output.

#### 3.4.3 `pipelines/user_ingest.py`

**Purpose.** User demo ingestion pipeline. Processes user demos into `PlayerMatchStats` records.

**Function `ingest_user_demos(source_dir, processed_dir)`** -- Globs `*.dem`, processes each via `_process_single_user_demo`.

**Function `_process_single_user_demo(demo_path, db_manager, processed_dir)`** -- Calls `parse_demo`, then `_map_and_pipeline_user`.

**Function `_map_and_pipeline_user(demo_path, rounds_df, db_manager, processed_dir)`** -- Extracts match stats, creates `PlayerMatchStats` record (R3-04: uses `.stem` for demo_name), triggers ML pipeline, archives demo only after all pipeline steps succeed (R3-H03).

**Function `_trigger_ml_pipeline(db_manager, demo_name, stats) -> bool`** -- Calls `run_ml_pipeline` from `run_ingestion`. Returns False if result is None (early exit, profile not ready).

**Function `_archive_user_demo(demo_path, processed_dir)`** -- Moves demo to processed directory.

F6-19: This pipeline stores basic `PlayerMatchStats` only. Full enrichment requires calling `enrich_from_demo()` and `_extract_and_store_events()` from `run_ingestion.py`.

---

### 3.5 Registry (`ingestion/registry/`)

#### 3.5.1 `registry/__init__.py`

Empty init file.

#### 3.5.2 `registry/lifecycle.py`

**Purpose.** Demo lifecycle management (cleanup).

**Class `DemoLifecycleManager`**

**`__init__(raw_dir, processed_dir)`** -- Stores directory paths.

**`cleanup_old_demos(days=30)`** -- Removes demos older than `days` days from the processed directory.

**Function `_purge_expired_demos(directory, now, days)`** -- Globs `*.dem`, compares `st_mtime` against age threshold, unlinks expired files.

#### 3.5.3 `registry/registry.py`

**Purpose.** JSON-file-based demo processing registry with backup recovery and thread/process safety.

**Class `DemoRegistry`**

**`__init__(registry_path: Path)`** -- Creates both a `threading.Lock` (R3-08: thread-safe) and a `FileLock` (R3-08: cross-process safety via `filelock` library). Calls `_load()`.

**`_load()`** -- Acquires locks in consistent order (thread lock -> file lock, DS-08). Loads JSON, converts `processed_demos` list to a set for O(1) lookups (F6-20).

**`_save()`** -- Caller must hold `self._lock`. Acquires file lock. Delegates to `_save_inner()`.

**`_save_inner()`** -- Creates backup before overwriting. R3-H04: Write-ahead pattern (write to temp file, then atomic rename via `os.replace`). Cleans up temp file on failure.

**`is_processed(demo_name) -> bool`** -- Thread-safe O(1) set lookup.

**`mark_processed(demo_name)`** -- Thread-safe. Adds to set and saves if new.

**Function `_execute_registry_load(path) -> dict`** -- Load with backup recovery. If primary is corrupted (JSON decode error), attempts backup recovery from `.json.backup` file. Validates backup structure (F6-REG: must have `processed_demos` key containing a list). Restores backup to primary on success. Resets to empty as last resort.

---

### 3.6 `steam_locator.py`

**Purpose.** Primary Steam installation path discovery and demo queue management.

F6-11: This is the primary authority for Steam path discovery. `backend/data_sources/steam_demo_finder.py` is supplementary.

#### Function `get_steam_path() -> Optional[Path]`

Dispatches to platform-specific implementation.

#### Function `_get_win_steam_path() -> Optional[Path]`

Reads `HKEY_CURRENT_USER\Software\Valve\Steam\SteamPath` from Windows registry.

#### Function `_get_linux_steam_path() -> Optional[Path]`

Checks three paths: `~/.local/share/Steam`, `~/.steam/steam`, `~/.var/app/com.valvesoftware.Steam/.local/share/Steam`.

#### Function `find_cs2_replays() -> Optional[Path]`

Combines Steam path with relative CS2 replay path. Falls back to `_get_fallback_win_path()` on Windows.

#### Function `_get_fallback_win_path() -> Optional[Path]`

Searches for CS2 replays across all writable drives. Uses `psutil.disk_partitions()` for dynamic drive detection, falls back to hardcoded drive letters (`C:\` through `H:\`). Tries five common Steam subdirectory patterns per drive.

#### Function `sync_steam_demos(target_dir)`

Entry point for Steam demo discovery.

#### Function `_iterate_demo_patterns(target_dir)`

Runs two glob patterns: `**/*.dem` (recursive) and `*.dem` (flat).

#### Function `_find_and_queue_demos(target_dir, pattern)`

Globs demos and calls `_queue_if_new` for each.

#### Function `_queue_if_new(demo_path)`

F6-31: Module-level imports for `select`, `get_db_manager`, `IngestionTask`. Checks for existing `IngestionTask` record. Creates new task with `is_pro=False, status="queued"` if none exists.

---

## 4. Root-Level Scripts

### 4.1 `batch_ingest.py`

**Purpose.** Parallel batch ingestion script for pro CS2 demo files. Uses multiprocessing to leverage all CPU cores. Resumable: skips already-ingested demos.

#### Function `ingest_one_demo(demo_path_str: str) -> dict`

Worker function running in a separate process. Steps:

1. Ensures `IngestionTask` record exists; resets `"failed"` tasks to `"queued"` for retry.
2. Sets task status to `"processing"` before work starts (so stale-lock sweeps can identify in-flight rows by `updated_at` age).
3. Calls `_ingest_single_demo(db, storage, demo_path, is_pro=True)`.
4. **Authoritative final status update in `finally:` block** -- guarantees task is flipped to `"completed"` or `"failed"` regardless of exceptions. Error messages truncated to 512 chars for DB column safety.

Returns dict with `demo`, `success`, `msg`, `elapsed`.

#### Function `get_already_ingested() -> Set[str]`

Returns set of demo stems already in `PlayerMatchStats` via distinct query.

#### Function `main()`

CLI entry point. Argument parsing:
- `--workers N` (0 = auto-detect based on RAM)
- `--limit N` (0 = all)
- `--demo-dir` (default: `PRO_DEMO_PATH` setting via `get_pro_demo_base()`)
- `--no-train` (skip auto-training after ingestion)

Auto-detects workers: `~6 GB RAM per worker, 12 GB headroom`. Caps at `min(max_by_ram, max_by_cpu, 8)`.

Uses `ProcessPoolExecutor` with `max_tasks_per_child=1` on Python 3.11+ to prevent DataFrame-accumulation memory leaks.

Logs detailed progress: demos/min throughput, ETA, success/fail counts.

After ingestion, calls `run_training_after_ingestion()` unless `--no-train`.

#### Function `run_training_after_ingestion()`

Three-step ML training pipeline:
1. `CoachTrainingManager.assign_dataset_splits()` -- 70/15/15 train/val/test.
2. JEPA self-supervised pre-training on pro data.
3. Supervised training on pro baseline. Saves model via `save_nn("latest")`.

---

### 4.2 `run_ingestion.py`

**Purpose.** The main ingestion orchestrator. Handles single-demo processing, ML pipeline execution, sequential tick data storage, event extraction, and match database management. The largest and most complex file in the ingestion subsystem.

#### Function `_check_duplicate_demo(db_manager, demo_name: str) -> bool`

Unified duplicate detection across three data stores:
1. `IngestionTask` table (exact path, excludes "error"/"processing" statuses).
2. `PlayerMatchStats` table (by demo_name stem, R3-04).
3. Per-match DB file existence (SHA-256 based match_id).

#### Function `run_ml_pipeline(db_manager, player_name, current_demo_name, stats)`

Main ML ingestion pipeline. Steps:
1. Checks profile readiness via `_is_profile_ready`.
2. Calculates skill vector and curriculum level via `SkillLatentModel`.
3. Computes feature trends via `_get_feature_trends`.
4. Runs level-conditioned RAP inference via `_get_rap_inference`.
5. Saves insights via `_save_insights`.

Note: Pro-baseline deviations live in `hltv_metadata.db` and are computed only during coaching inference, not during demo ingestion.

#### Function `_is_profile_ready(db_manager, player_name) -> bool`

Requires a `PlayerProfile` row and at least `MIN_DEMOS_FOR_COACHING` non-pro demos.

#### Function `_get_feature_trends(db_manager, player_name) -> List[FeatureTrend]`

Fetches last 10 matches, computes trend (slope, volatility, confidence) for `avg_kills`, `avg_adr`, `avg_kast`, `accuracy`. Requires at least 3 matches.

#### Function `_get_rap_inference(db_manager, player_name, skill_level=5) -> List`

Wraps `_execute_rap_logic` in error handling.

#### Function `_execute_rap_logic(db_manager, player_name, skill_level=5) -> List`

Loads `PlayerTickState` data, loads RAP model checkpoint, segments match into windows (limit 5), reconstructs belief tensors, generates advice with confidence 0.85.

#### Function `_save_insights(db_manager, p_name, demo_name, deviations, trends, rap_advices, skill_level=5)`

Deletes existing insights for the demo. Generates longitudinal coaching insights. Generates corrections. Saves all via `_save_batch_insights`.

#### Function `_save_batch_insights(session, p_name, demo_name, rap, corr, long_i, skill_level)`

Creates `CoachingInsight` records for:
- RAP behavioral insights (severity "Medium", focus "Decision").
- Correction insights with grounded narratives via `ExplanationGenerator`. Maps features to categories (mechanics, positioning, decision). Classifies severity based on weighted z-score. Uses "Silence is a Valid Action" pattern (skips empty messages).
- Longitudinal insights.

#### Function `process_new_demos(is_pro=False, high_priority=False, limit=0)`

Scans for new demos in ingest folders. Reloads settings from disk (critical for dynamic folder changes from UI). Sets process priority. Queues files and processes the queue.

#### Function `process_queued_tasks(db_manager, storage, is_pro, high_priority, limit=0)`

Orchestrates ingestion of queued tasks with throttling. For each task: sets status to "processing", updates `CoachState.parsing_progress`, checks for duplicates, calls `_ingest_single_demo`, updates final status. Resets progress when batch is done.

#### Function `_queue_files(session, files, is_pro)`

Creates `IngestionTask` records for files not already in the queue.

#### Function `_ingest_single_demo(db_manager, storage, demo_path, is_pro) -> Tuple[bool, str]`

Core single-demo ingestion function shared between `run_ingestion`, `run_worker`, and `batch_ingest`. Steps:
1. Reads `last_tick_processed` from task for incremental ingestion.
2. If `start_tick == 0`: parses aggregate stats via `parse_demo`, saves per-player stats via `_save_player_stats`.
3. Parses sequential data via `_save_sequential_data`.
4. Updates task progress. Archives demo on success.

#### Function `_save_player_stats(db_manager, row, demo_name, is_pro)`

Sanitizes stats before DB insertion (R3-H09: NaN/Inf -> 0.0). Clamps rating to [0, 5.0] range. Clamps `avg_kills` and `avg_adr` to >= 0. Uses stem for demo_name normalization. Upserts `PlayerMatchStats` record.

#### Function `_sanitize_value(value, default, value_type=float)`

Sanitization bridge for NaN/None/invalid values.

#### Function `_interpolate_position(df_ticks) -> pd.DataFrame`

Intelligent position interpolation with alive-boundary safety:
- Positions interpolated only within contiguous alive segments per player (no bleed across death events).
- Angles (yaw/pitch) use circular interpolation (sin/cos decomposition) for correct wrap-around handling.
- R4-14-01: Counts remaining (0,0,0) positions after interpolation for data quality monitoring. Fills final NaN with 0.0 for DB compatibility.
- Forward-fills integer fields (health, armor, equipment, WP6 fields).

#### Constants (Tick DataFrame Defaults)

**`_TICK_INT_DEFAULTS`** -- Dict of 24 integer column defaults (e.g., `round_number: 1`, `armor: 0`, `teammates_alive: 4`, `enemies_alive: 5`).

**`_TICK_FLOAT_DEFAULTS`** -- Dict of 6 float column defaults (X, Y, Z, yaw, pitch, time_in_round, all 0.0).

**`_TICK_BOOL_DEFAULTS`** -- Dict of 6 boolean column defaults (is_crouching, is_scoped, is_blinded, has_helmet, has_defuser, bomb_planted, all False).

**`_EVENT_DEFAULT_STATE`** -- Dict of default values for event state lookup (health: 100, armor: 0, equipment_value: 0, team: "", pos: 0.0).

#### Function `_apply_tick_dataframe_defaults(df_ticks, meta_map_name)`

Vectorized NaN/None/non-numeric fill. Logs warnings when non-numeric values are coerced (R3-02). Handles critical columns: health (default 100), is_alive (default True), team_name (default "CT"), active_weapon (default "unknown", handles "nan" string), map_name.

#### Class `_EventExtractor`

Per-demo event-extraction helper. Owns the `(tick, player_name)` state index and `steamid->name` mapping.

**`__init__(parser, df_ticks)`** -- F6-14-v2: Builds a MultiIndex DataFrame (`_state_index`) indexed by `(tick, player_name_lower)` for O(1) state lookups. Avoids the old bounded dict that caused eviction warnings for pro demos with 1.5M+ ticks. Builds `sid_to_name` mapping from steamid/player_name columns.

**`_row_to_state(row) -> dict`** -- Static method. Converts a state row to default-safe dict.

**`_lookup_state(tick, player_name) -> dict`** -- Looks up player state at a tick with nearest-tick fallback (+-5 ticks).

**`_resolve_name(row, name_cols) -> str`** -- Resolves player name from event row, trying multiple column names. Falls back to steamid lookup.

**`_get_round(row) -> int`** -- Extracts round number from `total_rounds_played` field.

**`_row_pos(row) -> Tuple[float, float, float]`** -- Extracts (x, y, z) position from event row.

**`_safe_parse(names, log_label) -> List[Tuple[str, DataFrame]]`** -- Parses one or more event names. Normalizes output to list of `(name, df)` tuples.

**`extract_weapon_fire()`** -- Creates `MatchEventState` records for weapon_fire events with player state context.

**`extract_player_hurt()`** -- Creates records for player_hurt events with both attacker and victim state.

**`extract_player_death()`** -- Creates records for player_death events with attacker/victim state and headshot flag.

**`_extract_grenade_pair(evt_pair, etype_keyword_map, weapon_label, log_label)`** -- Helper for start/end pair events (smoke, molotov). Resolves player via steamid.

**`extract_smoke()`** -- Smoke start/end events.

**`extract_molotov()`** -- Molotov start/end events.

**`_extract_grenade_single(event_name, etype, weapon_label, log_label)`** -- Helper for single-event detonations (flash, HE).

**`extract_flashbang()`** -- Flashbang detonation events.

**`extract_he_grenade()`** -- HE grenade detonation events.

**`extract_grenade_thrown()`** -- GAP-02: `grenade_thrown` schema lacks x/y/z; throw origin resolved from tick state. Uses position from `_lookup_state`.

**`extract_bomb()`** -- bomb_planted and bomb_defused events.

**`extract_all() -> List`** -- Runs all extractors in fixed order. Returns accumulated events list.

#### Function `_extract_and_store_events(demo_path, match_id, match_manager, df_ticks) -> int`

Creates `DemoParser`, instantiates `_EventExtractor`, calls `extract_all()`, stores events via `match_manager.store_event_batch()`.

#### Function `_parse_demo_header_meta(demo_path) -> tuple[str, float]`

GAP-01: Extracts `(map_name, tick_rate)` from demo header. Validates tick_rate in [32, 256] range. Returns safe defaults ("de_unknown", 64.0) on failure.

#### Function `_build_match_tick_dataframe(df_ticks) -> pd.DataFrame`

Builds per-match `MatchTickState` DataFrame with ALL players. Vectorized renames and dtype casts. Tick decimation FORBIDDEN. Maps 38 columns including position, view angles, health/armor, weapon, economy, round stats, cumulative stats, team economy, bomb state, and map name.

#### Function `_build_legacy_tick_dataframe(df_ticks, demo_name, target_player, meta_map_name) -> pd.DataFrame`

Builds legacy `PlayerTickState` DataFrame. Filtered to target_player for user demos, ALL players for pro demos. Maps 30 columns. Uses `ducking` field for crouch state, `flash_duration > 0` for blind state.

#### Function `_finalize_match_record(match_manager, match_id, demo_name, demo_path, df_ticks, meta_map_name, meta_tick_rate, meta_player_count, last_tick, start_tick)`

Persists match metadata (GAP-01: stores detected tick_rate). Extracts events on fresh ingestion only (start_tick == 0). Marks match as complete (P4-A: only after all ticks + events land).

#### Function `_save_sequential_data(db_manager, demo_path, target_player, start_tick=0) -> int`

The main sequential data pipeline. Steps:
1. Progress 10%: Parse ALL players via `parse_sequential_ticks("ALL")`.
2. Progress 20%: Interpolate positions via `_interpolate_position`.
3. Progress 25%: Enrich tick data via `enrich_tick_data` (cross-player features, round context, bomb state).
4. Progress 40%: Apply defaults, build match and legacy DataFrames.
5. Progress 40-95%: Chunked dual-write to per-match DB + monolith DB via `to_sql()`. Batch size: 10000 in HP mode, 2000 otherwise.
6. Finalize match record.

DA-03-01: Match ID computed as `SHA-256(demo_stem) % (2^63 - 1)`.

---

### 4.3 `run_worker.py`

**Purpose.** Background ingestion worker with self-healing capabilities. Polls for queued `IngestionTask` records and processes them.

#### Function `_recover_stale_tasks(db)`

IM-02: Recovers tasks stuck in "processing" state whose `updated_at` is older than 5 minutes. Resets them to "queued".

#### Function `_fetch_next_task_data(db) -> Optional[dict]`

R3-M25: Atomically claims next queued task by setting status to "processing" in the same transaction that reads it. Prevents duplicate claims by concurrent workers. Returns dict with `id`, `is_pro`, `demo_path`.

#### Function `_mark_task_status(db, task_id, status)`

Sets task status and updates timestamp.

#### Function `_should_skip_pro_task(db, is_pro) -> bool`

Skips pro tasks if there are fewer than 10 queued pro demos and no existing pro data in `PlayerMatchStats`. Prevents processing isolated pro demos without sufficient context.

#### Function `_execute_task(db, storage, task_id, demo_path, is_pro)`

Checks for file existence (including in `processed/` subdirectory). Calls `_ingest_single_demo`. Updates task status based on result.

#### Function `_mark_task_status_failed(db, task_id, error_msg)`

Sets task to "failed" with error message.

#### Function `_process_next_task_cycle(db, storage)`

Single cycle: fetch next task, check skip conditions, execute. Sleeps 5s if no task available, 10s if pro task skipped.

#### Function `run_worker()`

Main loop. Initializes database, creates DB manager and StorageManager, recovers stale tasks. Polls continuously until `hltv_sync.stop` signal file appears. Error recovery: sleeps 10s and retries on exceptions.

---

### 4.4 `hltv_sync_service.py`

**Purpose.** Background daemon for pro player statistics scraping from HLTV.org. Periodically fetches text data only (no demo downloads).

#### Constants

| Name | Value | Description |
|------|-------|-------------|
| `PID_FILE` | `SCRIPT_DIR / "hltv_sync.pid"` | PID file for detecting running instances. |
| `STOP_SIGNAL` | `SCRIPT_DIR / "hltv_sync.stop"` | Signal file for graceful shutdown. |
| `_DORMANT_SLEEP_S` | `21600` (6 hours) | Sleep duration when HLTV is unreachable. |
| `_FULL_REFRESH_INTERVAL_S` | `604800` (7 days) | Full refresh cadence for team rankings. |
| `_INCREMENTAL_INTERVAL_S` | `86400` (24 hours) | Incremental refresh for top 30 players. |
| `_INTER_CYCLE_REST_S` | `3600` (1 hour) | Rest between batches. |

#### Function `_dormant_sleep(seconds: int)`

Sleeps in 1-second increments, checking the stop signal each iteration.

#### Function `run_sync_loop()`

Main background loop. Preflight checks:
1. Auto-starts FlareSolverr Docker container via `ensure_flaresolverr()`.
2. Verifies FlareSolverr availability.
3. Tests HLTV connectivity via FlareSolverr.
4. Creates persistent browser session for cookie reuse.

Main loop (until stop signal):
1. Runs `preflight_check()` (settings + robots.txt).
2. Determines mode: full refresh (every 7 days) or incremental.
3. Discovers top 30 teams and rosters.
4. Full refresh: re-scrapes all players. Incremental: scrapes only new players.
5. Falls back to `fetch_top_players()` if team discovery fails.
6. Syncs each player URL.
7. Updates `CoachState` via `get_state_manager()` (status, notifications).
8. Rests for `_INTER_CYCLE_REST_S` between cycles.

Cleans up persistent session on exit.

#### Function `_is_pid_alive(pid: int) -> bool`

Checks if a process with the given PID is still running via `os.kill(pid, 0)`.

#### Function `start_detached()`

Starts the sync service as a detached background process. DA-06-01: Checks if stored PID is actually alive before rejecting (handles stale PID files). Launches `main.py --hltv-service` via `subprocess.Popen` with `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` on Windows.

#### Function `stop_service()`

Creates the stop signal file. Logs the PID that will stop.

---

## 5. Cross-Module Linkages and Architectural Mechanisms

### 5.1 Duplicate Detection

Two independent deduplication mechanisms coexist:

1. **`DemoRegistry`** (`ingestion/registry/registry.py`) -- JSON file with file lock. Set-based O(1) lookup. Used for filesystem-level dedup tracking.
2. **`IngestionTask`** table (DB-based) -- Database records with status state machine. Used by `watcher.py`, `run_worker.py`, `run_ingestion.py`, and `batch_ingest.py`. The `_check_duplicate_demo` function in `run_ingestion.py` cross-checks three data stores (IngestionTask, PlayerMatchStats, per-match DB files).

### 5.2 Demo Validation Chain

`demo_format_adapter.validate_demo_file()` is the canonical validation entry point, called by:
- `integrity.validate_dem_file()` (wraps with exception types)
- `demo_loader.DemoLoader.load_demo()` (pre-parse validation)
- `watcher.py` imports `MIN_DEMO_SIZE` for file stability gating (R3-M20)

### 5.3 HLTV Scraping Pipeline

Chain: `docker_manager.ensure_flaresolverr()` -> `FlareSolverrClient` -> `HLTVStatFetcher` (deep crawl) -> `hltv_sync_service.run_sync_loop()` (daemon orchestration). The `hltv_scraper.run_hltv_sync_cycle()` provides a simpler one-shot interface.

### 5.4 Shared Ingestion Core

`_ingest_single_demo()` in `run_ingestion.py` is the shared core, called from:
- `run_ingestion.process_queued_tasks()` (direct invocation)
- `run_worker._execute_task()` (background worker)
- `batch_ingest.ingest_one_demo()` (parallel worker process)

### 5.5 Steam Path Discovery

Two modules with overlapping responsibility (F6-11, consolidation deferred):
- `ingestion/steam_locator.py` -- Primary authority. Registry lookup + fallback partition scan.
- `backend/data_sources/steam_demo_finder.py` -- Supplementary. Adds recent-demo scanning and metadata extraction.

### 5.6 Tick Decimation Prohibition

Enforced as a project invariant (CLAUDE.md). Both `parse_sequential_ticks` (demo_parser) and `_build_match_tick_dataframe` / `_build_legacy_tick_dataframe` (run_ingestion) preserve 1:1 tick-to-row mapping. The sampling rate in `parse_sequential_ticks` defaults to 1 (no decimation).
