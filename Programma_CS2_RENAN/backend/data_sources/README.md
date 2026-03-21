> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data Sources -- External Integrations

> **Authority:** `backend/data_sources/`
> **Skill:** `/resilience-check`, `/api-contract-review`, `/security-scan`
> **Consumers:** `ingestion/`, `backend/services/`, `backend/coaching/pro_bridge.py`

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
| `demo_parser.py` | `parse_demo()` | demoparser2 wrapper with HLTV 2.0 rating calculation, exports per-tick and per-round data |
| `demo_format_adapter.py` | `DemoFormatAdapter` | Format validation and conversion between demo parser outputs and internal schemas (`MIN_DEMO_SIZE=10MB`) |
| `event_registry.py` | Event dispatch | Event type registration and dispatch for demo events (kills, plants, defuses, etc.) |
| `trade_kill_detector.py` | `TradeKillDetector` | Identifies trade frags from tick data using a 3-second sliding window |
| `round_context.py` | Round context helper | Enriches per-round data with contextual metadata (economy state, site control, etc.) |
| `steam_api.py` | `SteamAPI` | Steam Web API integration for profile synchronization, friend lists, game stats |
| `steam_demo_finder.py` | `SteamDemoFinder` | Locates CS2 demo files in Steam userdata directories on the local filesystem |
| `faceit_api.py` | `FaceitAPI` | FACEIT platform API wrapper for match history and player statistics |
| `faceit_integration.py` | `FaceitIntegration` | High-level FACEIT data ingestion orchestration |
| `hltv_scraper.py` | `HLTVScraper` | Scrapes professional player statistics from hltv.org (Rating 2.0, K/D, ADR, KAST, HS%) |
| `hltv/` | Sub-package | Active HLTV implementation: FlareSolverr client, Docker manager, CSS selectors, rate limiting, stat fetcher |

### HLTV Sub-Package (`hltv/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Sub-package root |
| `flaresolverr_client.py` | HTTP client that routes requests through FlareSolverr/Docker to bypass Cloudflare protection |
| `docker_manager.py` | Manages the FlareSolverr Docker container lifecycle (start, stop, health check) |
| `selectors.py` | CSS selectors for parsing HLTV HTML pages (player profiles, stat tables) |
| `rate_limit.py` | Rate limiting logic to avoid being blocked by hltv.org |
| `stat_fetcher.py` | High-level stat fetching orchestrator that coordinates the above modules |

## Data Flow Diagram

```
                    External Systems
                    ================

  .dem files       Steam Web API      FACEIT API        hltv.org
      |                 |                 |                 |
      v                 v                 v                 v
 demo_parser.py    steam_api.py     faceit_api.py    hltv_scraper.py
      |                 |                 |                 |
      v                 |                 v                 |
 demo_format_         steam_demo_    faceit_          hltv/ sub-package
 adapter.py           finder.py      integration.py   (FlareSolverr)
      |                 |                 |                 |
      v                 v                 v                 v
 event_registry.py      |                 |           hltv_metadata.db
      |                 |                 |           (ProPlayer,
      v                 |                 |            ProPlayerStatCard,
 trade_kill_            |                 |            ProTeam)
 detector.py            |                 |
      |                 |                 |
      +--------+--------+---------+-------+
               |
               v
        Internal Schemas
     (ingestion/ pipeline,
      backend/storage/,
      match_data/<id>.db)
```

## Module Descriptions

### demo_parser.py -- parse_demo()

The central demo parsing function. Wraps the `demoparser2` library to extract per-tick
player state (position, health, armor, equipment) and per-round aggregated statistics
(kills, deaths, assists, damage). Computes HLTV 2.0 rating on the fly during parsing.
Returns structured data ready for the ingestion pipeline. This is one of the most
performance-critical modules in the system, processing millions of tick rows per demo.

### demo_format_adapter.py -- DemoFormatAdapter

Validates and converts demo parser output into internal schemas. Enforces `MIN_DEMO_SIZE
= 10 MB` (invariant DS-12) to reject truncated or corrupted demo files -- real CS2 demos
are 50+ MB. Performs schema alignment so that downstream consumers (feature engineering,
database storage) receive a consistent data shape regardless of parser version changes.

### event_registry.py -- Event Dispatch

Registers and dispatches demo events (player_death, bomb_planted, bomb_defused,
round_start, round_end, etc.) to subscribers. Uses an observer pattern so that multiple
analysis modules can react to the same event stream without coupling to each other.

### trade_kill_detector.py -- TradeKillDetector

Post-parse analysis module that identifies trade frags from tick-level kill data. A trade
kill is defined as a kill occurring within a 3-second window after a teammate's death,
targeting the same enemy who made the original kill. Trade kill data feeds into tactical
analysis and coaching recommendations about trade discipline.

### round_context.py -- Round Context Helper

Enriches per-round data with contextual metadata that is not directly present in raw
demo output. Computes derived fields such as economy advantage, site control metrics,
and utility usage patterns. This contextual enrichment helps downstream coaching modules
produce more relevant advice.

### steam_api.py -- SteamAPI

Integration with the Steam Web API for profile synchronization. Retrieves player profile
information, friend lists, and CS2-specific game statistics. Requires a Steam API key
stored via the credential system (`get_credential("STEAM_API_KEY")`). Includes retry
logic and rate limiting to handle API transient failures.

### steam_demo_finder.py -- SteamDemoFinder

Locates CS2 demo files on the local filesystem by scanning known Steam userdata
directories. Platform-aware (Windows, Linux, macOS). Used by the ingestion pipeline to
discover new demos for automated processing without requiring the user to manually
specify file paths.

### faceit_api.py -- FaceitAPI

Low-level wrapper around the FACEIT platform API. Retrieves match history, player
statistics, and ELO ratings. Requires a FACEIT API key stored via the credential system.
Handles pagination, rate limiting, and error responses from the FACEIT API.

### faceit_integration.py -- FaceitIntegration

High-level orchestration layer that coordinates FACEIT data ingestion. Manages the flow
from API calls through data normalization to database storage. Provides a single
`sync_player()` entry point that handles the full lifecycle of fetching and persisting
FACEIT data for a given player.

### hltv_scraper.py -- HLTVScraper

Scrapes professional player statistics from hltv.org. Extracts: Rating 2.0, K/D ratio,
ADR (Average Damage per Round), KAST percentage, HS% (Headshot percentage), clutch
statistics, and career history. Data is saved to `hltv_metadata.db` in the `ProPlayer`,
`ProPlayerStatCard`, and `ProTeam` tables. **This module scrapes statistics only -- it
has no connection to demo file management.**

### hltv/ Sub-Package

The active HLTV implementation that handles Cloudflare-protected page retrieval.
`docker_manager.py` manages the FlareSolverr container, `flaresolverr_client.py` routes
HTTP requests through it, `selectors.py` provides CSS selectors for HTML parsing,
`rate_limit.py` prevents aggressive scraping, and `stat_fetcher.py` orchestrates the
full stat-fetching workflow.

## Integration Points

| Consumer | Data Source Module | What It Gets |
|----------|--------------------|--------------|
| `ingestion/` pipeline | `demo_parser.py`, `demo_format_adapter.py` | Parsed, validated demo data for database storage |
| `backend/processing/` | `event_registry.py`, `trade_kill_detector.py` | Event streams and trade kill analysis for feature engineering |
| `backend/coaching/pro_bridge.py` | `hltv_scraper.py` (via `hltv_metadata.db`) | Professional player baselines for coaching comparison |
| `backend/services/` | `steam_api.py`, `faceit_integration.py` | Player profile data for session context |
| `core/session_engine.py` | `steam_demo_finder.py` | Auto-discovered demo file paths for the IngestionWatcher |

## Development Notes

- **Boundary validation:** All external data must be validated before crossing into
  internal schemas. Never trust raw API responses or parser output without schema checks.
- **Credential management:** API keys (Steam, FACEIT) are stored via `get_credential()`
  from `core/config.py`. Never hard-code secrets or log them.
- **MIN_DEMO_SIZE invariant:** `demo_format_adapter.py` enforces `MIN_DEMO_SIZE = 10 MB`
  (invariant DS-12). Do not lower this threshold -- truncated demos cause silent
  corruption in downstream processing.
- **HLTV is stats only:** The HLTV integration fetches professional player statistics.
  It does not download demos, manage .dem files, or interact with the demo ingestion
  pipeline. Confusing HLTV with demo management is a documented anti-pattern.
- **Docker dependency:** The HLTV scraper requires FlareSolverr running in Docker to
  bypass Cloudflare. The `hltv/docker_manager.py` handles container lifecycle.
- **Structured logging:** All modules use `get_logger("cs2analyzer.data_sources.<module>")`.
- **Rate limiting:** Both HLTV and Steam integrations include rate limiting. Do not bypass
  rate limits -- it leads to IP bans.
- **Testing:** Use `mock_db_manager` for database-dependent tests. HLTV and API tests
  require `@pytest.mark.integration` and `CS2_INTEGRATION_TESTS=1`.

## Dependencies

- **demoparser2** -- CS2 demo file parsing engine
- **FlareSolverr/Docker** -- Cloudflare bypass for HLTV scraping
- **requests** -- HTTP client for Steam and FACEIT APIs
- **BeautifulSoup4** -- HTML parsing for HLTV pages
- **SQLModel** -- Database persistence for pro player statistics
