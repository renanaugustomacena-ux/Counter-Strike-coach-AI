> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data Sources -- External Integrations

> **Authority:** `backend/data_sources/`
> **Skill:** `/resilience-check`, `/api-contract-review`, `/security-scan`
> **Consumers:** `ingestion/`, `backend/processing/`, `backend/coaching/pro_bridge.py`

## Overview

The data sources package is the boundary layer between the CS2 Analyzer and all external
systems. It provides adapters for demo file parsing, Steam profile lookups, FACEIT match
history retrieval, and professional player statistics scraping from HLTV. Every external
integration lives here so that the rest of the codebase never touches raw I/O, HTTP
clients, or third-party data formats directly.

The package follows a strict **zero-trust-at-boundaries** principle: all data entering
from external sources is validated, normalized, and converted into internal schemas
before being passed to downstream consumers.

> **IMPORTANT -- HLTV Clarification:**
> The HLTV integration scrapes **professional player statistics** from hltv.org
> (Rating 2.0, K/D, ADR, KAST, HS%, clutch stats, career history). It does **NOT**
> download demos, fetch demo metadata, or interact with .dem files in any way. The
> HLTV scraper and the demo parser are completely independent subsystems.

## File Inventory

| File | Primary Export | Purpose |
|------|---------------|---------|
| `__init__.py` | Package root | (empty -- namespace only) |
| `demo_parser.py` | `parse_demo()`, `parse_sequential_ticks()` | demoparser2 wrapper with HLTV 2.0 rating calculation; real parse timeout (F-0013) and per-demo tick rate read from the header |
| `parse_guard.py` | `is_parse_error()` | F-0006 parse-guard SSOT: classifies which exceptions a demoparser2 guard may absorb (incl. pyo3 `PanicException`); `KeyboardInterrupt`/`SystemExit`/`GeneratorExit` always propagate |
| `demo_format_adapter.py` | `DemoFormatAdapter` | Format validation and conversion between demo parser outputs and internal schemas (`MIN_DEMO_SIZE=10MB`) |
| `event_registry.py` | `EVENT_REGISTRY` | Canonical schema registry of CS2 game events (fields, priority, handler coverage) -- documentation/coverage tool, not a runtime dispatcher |
| `trade_kill_detector.py` | `detect_trade_kills()`, `analyze_demo_trades()` | Identifies trade frags from death events using a 3-second window converted to ticks from the demo's tick rate |
| `round_context.py` | `extract_round_context()` | Pairs freeze_end/round_end events into round windows, extracts bomb events, assigns rounds to ticks via `merge_asof` |
| `steam_api.py` | `fetch_steam_profile()` | Steam Web API profile lookup with vanity URL resolution and bounded retry/backoff |
| `steam_demo_finder.py` | `SteamDemoFinder` | Locates CS2 demo files in Steam userdata directories (supplementary to `ingestion/steam_locator.py`, F6-11) |
| `faceit_api.py` | `fetch_faceit_data()` | Minimal FACEIT API wrapper: fetches Elo and level for a nickname |
| `faceit_integration.py` | `FACEITIntegration` | FACEIT client with rate limiting: match history, match details, demo download; `sync_faceit_matches()` entry point |
| `hltv_scraper.py` | `run_hltv_sync_cycle()` | Thin entry point that runs one HLTV stats sync cycle (default limit 50 players) via the `hltv/` sub-package; the Hunter daemon uses `hltv_sync_service.py` instead |
| `hltv/` | Sub-package | Active HLTV implementation: FlareSolverr client, Docker manager, stat fetcher (CSS selectors + rate limiting inline) |

### HLTV Sub-Package (`hltv/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Sub-package root (empty namespace marker) |
| `flaresolverr_client.py` | REST client that posts requests to the local FlareSolverr container (port 8191) to bypass Cloudflare |
| `docker_manager.py` | Manages the FlareSolverr Docker container lifecycle (`docker start`, `docker compose up -d`, health check) |
| `stat_fetcher.py` | `HLTVStatFetcher`: discovery, HTML parsing, persistence. Inline CSS selectors via `soup.select()`; rate limiting via `CRAWL_DELAY_MIN/MAX_SECONDS` (2-7s) + `random.uniform()` + adaptive backoff on consecutive failures |

## Data Flow Diagram

```
                    External Systems
                    ================

  .dem files       Steam Web API      FACEIT API        hltv.org
      |                 |                 |                 |
      v                 v                 v                 v
 demo_format_      steam_api.py     faceit_api.py    hltv_sync_service.py
 adapter.py             |           faceit_          (Hunter daemon)
 (validation)      steam_demo_      integration.py        |
      |            finder.py             |                v
      v                 |                |           hltv/ sub-package
 demo_parser.py         |                |           (FlareSolverr)
 + parse_guard.py       |                |                |
      |                 |                |                v
      v                 |                |           hltv_metadata.db
 round_context.py       |                |           (ProPlayer,
 trade_kill_            |                |            ProPlayerStatCard,
 detector.py            |                |            ProTeam)
 (via backend/          |                |
  processing/)          |                |
      +--------+--------+--------+-------+
               |
               v
        Internal Schemas
     (ingestion/ pipeline,
      backend/storage/,
      match_data/<id>.db)
```

## Module Descriptions

### demo_parser.py -- parse_demo() / parse_sequential_ticks()

The central demo parsing module. Wraps the `demoparser2` library: `parse_demo()` builds
per-player aggregated statistics (scoreboard totals read at each player's **last**
observed tick, not `max()`, to exclude stale warmup counters) and computes HLTV 2.0
rating on the fly; `parse_sequential_ticks()` exports every native tick 1:1 -- the
legacy sampling stride was removed entirely (tick decimation is forbidden). The tick
rate is always read from the demo header (`parser.parse_header()`); `DEFAULT_TICK_RATE`
from `core/tick_rate.py` is only a fallback when the header itself fails to parse.
Parser calls run under a real timeout (F-0013): a hung demoparser2 call is abandoned
loudly instead of blocking the Digester daemon, with the timeout scaled by file size
(H-02: `max(300s, 3s per MB)`). All guards route through `parse_guard.is_parse_error()`.

### parse_guard.py -- is_parse_error()

F-0006 single source of truth for demo-parse exception handling. demoparser2 is a Rust
extension: a malformed .dem can raise a pyo3 `PanicException`, which subclasses
`BaseException` and used to fly past every `except Exception` guard, aborting whole
ingestion runs. `is_parse_error()` tells a guard whether to absorb an exception; the
name-based check is required because pyo3 creates the class lazily at first panic.
`KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` always propagate.

### demo_format_adapter.py -- DemoFormatAdapter

Validates and converts demo parser output into internal schemas. Enforces `MIN_DEMO_SIZE
= 10 MB` (invariant DS-12) to reject truncated or corrupted demo files -- real CS2 demos
are 50+ MB. Performs schema alignment so that downstream consumers (feature engineering,
database storage) receive a consistent data shape regardless of parser version changes.

### event_registry.py -- EVENT_REGISTRY

Canonical schema registry of CS2 game events (derived from SteamDatabase Game Events
dumps): for every event it records the category, field types, priority, whether Macena
handles it, and the handler file path. Exposes `get_implemented_events()`,
`get_unimplemented_events()`, and `get_coverage_report()` for parser-coverage tracking
and expansion planning. It is a documentation/coverage tool -- it does **not** dispatch
events at runtime.

### trade_kill_detector.py -- detect_trade_kills() / analyze_demo_trades()

Post-parse analysis module that identifies trade frags from death events. A kill counts
as a trade when the victim had killed a teammate of the killer within the trade window
(`TRADE_WINDOW_S = 3.0` seconds, converted to ticks at runtime from the demo's actual
tick rate read from the header -- DS-07). `analyze_demo_trades()` returns a
`TradeKillResult` plus per-player trade stats; consumed by
`backend/processing/round_stats_builder.py`. Trade kill data feeds into tactical
analysis and coaching recommendations about trade discipline.

### round_context.py -- extract_round_context()

Builds per-round context directly from demo events: pairs `freeze_end` / `round_end`
events into round windows (`extract_round_context()`), extracts bomb plant/defuse events
(`extract_bomb_events()`), and assigns round numbers to tick data with a pandas
`merge_asof` join (`assign_round_to_ticks()`). This contextual enrichment helps
downstream coaching modules produce more relevant advice.

### steam_api.py -- fetch_steam_profile()

Module-level functions for the Steam Web API: `fetch_steam_profile()` retrieves the
player profile (GetPlayerSummaries), auto-resolving vanity URLs via
`resolve_vanity_url()` and validating the Steam64 ID format (R3-M04). Retries use
exponential backoff (1s/2s/4s) under a hard total-time ceiling (DS-03, default 20s) so
the loop can never block unboundedly. The API key is passed in by callers, which read it
via `get_credential("STEAM_API_KEY")` from `core/config.py`.

### steam_demo_finder.py -- SteamDemoFinder

Locates CS2 demo files on the local filesystem by scanning known Steam replay
directories. Platform-aware (Windows, Linux, macOS); also exposes
`auto_discover_steam_demos(days=7)`. Note F6-11: the primary Steam path discovery lives
in `ingestion/steam_locator.py`; this module is supplementary and is not currently wired
into the runtime pipeline.

### faceit_api.py -- fetch_faceit_data()

Minimal wrapper around the FACEIT platform API: resolves a nickname to a player ID and
returns the CS2 Elo and skill level. Reads the API key via
`get_setting("FACEIT_API_KEY")` and returns an empty dict when the key is missing or a
request fails.

### faceit_integration.py -- FACEITIntegration

FACEIT client with built-in rate limiting (10 requests/minute free tier, 6s spacing,
exponential backoff on 429). Retrieves match history and match details, and can download
demo files when FACEIT provides a `demo_url` (HTTPS-only, capped by `MAX_DEMO_SIZE` from
`demo_format_adapter.py`). The `sync_faceit_matches(nickname, output_dir, limit=20)`
entry point fetches recent matches and attempts a demo download for each.

### hltv_scraper.py -- run_hltv_sync_cycle()

Thin entry point that runs one professional-statistics sync cycle (default `limit=50`
players) by delegating to the `hltv/` sub-package. The fetched data covers Rating 2.0,
K/D ratio, ADR (Average Damage per Round), KAST percentage, HS% (Headshot percentage),
and team affiliation, saved to `hltv_metadata.db` in the `ProPlayer`,
`ProPlayerStatCard`, and `ProTeam` tables. In production the Hunter daemon runs the
sync loop via `hltv_sync_service.py` (package root), which calls `HLTVStatFetcher`
directly. **This module scrapes statistics only -- it has no connection to demo file
management.**

### hltv/ Sub-Package

The active HLTV implementation that handles Cloudflare-protected page retrieval.
`docker_manager.py` manages the FlareSolverr container lifecycle, `flaresolverr_client.py`
routes HTTP requests through it, and `stat_fetcher.py` orchestrates discovery, HTML
parsing (inline CSS selectors via BeautifulSoup4), rate limiting (randomized crawl delay
with adaptive backoff on consecutive failures), and database persistence.

## Integration Points

| Consumer | Data Source Module | What It Gets |
|----------|--------------------|--------------|
| `ingestion/` pipeline (`run_ingestion.py`, `ingestion/pipelines/user_ingest.py`) | `demo_parser.py`, `parse_guard.py` | Parsed demo data for database storage |
| `ingestion/demo_loader.py`, `ingestion/integrity.py`, `backend/ingestion/watcher.py` | `demo_format_adapter.py` | Demo file validation (size/header/version checks) |
| `backend/processing/` (`round_stats_builder.py`, `tick_enrichment.py`) | `trade_kill_detector.py`, `round_context.py` | Trade kill analysis and round context for feature engineering |
| `backend/coaching/pro_bridge.py` | `hltv/` sub-package (via `hltv_metadata.db`) | Professional player baselines for coaching comparison |
| `backend/control/console.py`, `hltv_sync_service.py` | `hltv/docker_manager.py` | FlareSolverr container lifecycle (start on boot, stop on shutdown) |

The Steam/FACEIT adapters (`steam_api.py`, `faceit_api.py`, `faceit_integration.py`,
`steam_demo_finder.py`) and `event_registry.py` are standalone modules exercised by the
test suite and validator tools; live profile fetching in the app is currently implemented
in `backend/services/profile_service.py` with its own HTTP calls.

## Development Notes

- **Boundary validation:** All external data must be validated before crossing into
  internal schemas. Never trust raw API responses or parser output without schema checks.
- **Credential management:** API keys (Steam, FACEIT) are stored in settings and read via
  `get_credential()` / `get_setting()` from `core/config.py`. Never hard-code secrets or
  log them.
- **Tick rate is per-demo:** The tick rate is always read from the demo header at parse
  time; `DEFAULT_TICK_RATE` (`core/tick_rate.py`, the 26-NORM-01 SSOT) is only a fallback
  when the header itself fails to parse. Never hardcode 64.
- **No tick decimation:** `parse_sequential_ticks()` maps every input tick 1:1 to one
  output row. The legacy sampling stride was removed (supreme invariant, 2026-07-16);
  do not reintroduce any form of tick decimation.
- **MIN_DEMO_SIZE invariant:** `demo_format_adapter.py` enforces `MIN_DEMO_SIZE = 10 MB`
  (invariant DS-12). Do not lower this threshold -- truncated demos cause silent
  corruption in downstream processing.
- **HLTV is stats only:** The HLTV integration fetches professional player statistics.
  It does not download demos, manage .dem files, or interact with the demo ingestion
  pipeline. Confusing HLTV with demo management is a documented anti-pattern.
- **Docker dependency:** The HLTV scraper requires FlareSolverr running in Docker to
  bypass Cloudflare. The `hltv/docker_manager.py` handles container lifecycle.
- **Structured logging:** Modules log via `get_logger("cs2analyzer.<name>")` (e.g.
  `cs2analyzer.demo_parser`, `cs2analyzer.faceit`, `cs2analyzer.hltv_stat_fetcher`).
- **Rate limiting:** The HLTV and FACEIT integrations include rate limiting; Steam
  requests use bounded retry/backoff. Do not bypass rate limits -- it leads to IP bans.
- **Testing:** Use `mock_db_manager` for database-dependent tests. HLTV and API tests
  require `@pytest.mark.integration` and `CS2_INTEGRATION_TESTS=1`.

## Dependencies

- **demoparser2** -- CS2 demo file parsing engine
- **FlareSolverr/Docker** -- Cloudflare bypass for HLTV scraping
- **requests** -- HTTP client for Steam and FACEIT APIs
- **BeautifulSoup4** -- HTML parsing for HLTV pages
- **SQLModel** -- Database persistence for pro player statistics
