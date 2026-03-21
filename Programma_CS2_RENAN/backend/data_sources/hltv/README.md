# HLTV Professional Player Statistics Scraper

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## Authority and Skill

| Attribute | Value |
|-----------|-------|
| **Domain** | Professional CS2 player statistics from hltv.org |
| **Technology** | BeautifulSoup4 + FlareSolverr (Docker) for Cloudflare bypass |
| **Database** | `hltv_metadata.db` (SQLite WAL) |
| **Models** | `ProPlayer`, `ProPlayerStatCard`, `ProTeam` |
| **Entry Point** | `hltv_sync_service.py` (orchestrator, outside this package) |
| **Package** | `Programma_CS2_RENAN.backend.data_sources.hltv` |

---

## MANDATORY Clarification: What This Service Does and Does NOT Do

### What it DOES

- Scrapes **publicly visible text statistics** from professional player pages on hltv.org
- Fetches: Rating 2.0, K/D, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played
- Fetches trait sections: Firepower, Entrying, Utility stats
- Fetches sub-pages: Clutches (1v1, 1v2, 1v3), Multikills (3k, 4k, 5k), Career rating history
- Auto-discovers the Top 50 players from HLTV's ranking page
- Saves all data into `ProPlayer` + `ProPlayerStatCard` tables in `hltv_metadata.db`
- Respects `robots.txt` and enforces rate limiting between requests
- Uses FlareSolverr (Docker container) to bypass Cloudflare protection on hltv.org

### What it does NOT do

- **Does NOT fetch demos** -- demo files (`.dem`) are handled by a completely separate pipeline
- **Does NOT download demos** -- there is no demo download functionality anywhere in this package
- **Does NOT manage `.dem` files** -- demo ingestion lives in `ingestion/`
- **Does NOT interact with demo ingestion** -- this package and demo ingestion are fully isolated
- **Does NOT fetch match replay files** -- only text-based player statistics
- **Does NOT use Playwright** -- all browser automation goes through the FlareSolverr Docker container

This distinction is critical. The HLTV service exists solely to build a professional player
statistics baseline that the coaching engine uses to compare user performance against pro standards.

---

## File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Package initialization (empty marker) |
| `docker_manager.py` | 139 | Docker/FlareSolverr container lifecycle: start, health-check, stop |
| `flaresolverr_client.py` | 141 | REST client for FlareSolverr API: session management, HTTP GET via proxy |
| `rate_limit.py` | 33 | `RateLimiter` with tiered delays to mimic human browsing patterns |
| `selectors.py` | 29 | `HLTVURLBuilder` (URL construction) + `PlayerStatsSelectors` (CSS selectors) |
| `stat_fetcher.py` | 438 | `HLTVStatFetcher`: main fetching logic, HTML parsing, database persistence |

---

## Architecture Diagram

```
                        +--------------------------+
                        |   hltv_sync_service.py   |
                        |   (orchestrator — calls   |
                        |    HLTVStatFetcher)       |
                        +------------+-------------+
                                     |
                                     v
                        +------------+-------------+
                        |     stat_fetcher.py      |
                        |   HLTVStatFetcher class  |
                        |   - preflight_check()    |
                        |   - fetch_top_players()  |
                        |   - fetch_and_save()     |
                        +---+--------+--------+----+
                            |        |        |
                   +--------+   +----+----+   +--------+
                   |            |         |            |
                   v            v         v            v
          +--------+--+  +-----+------+  +-----+------+
          | selectors |  | rate_limit |  | flaresolverr |
          | .py       |  | .py        |  | _client.py   |
          | URL build |  | Tiered     |  | REST client  |
          | CSS select|  | delays     |  | for proxy    |
          +-----------+  +------------+  +------+-------+
                                                |
                                                v
                                     +----------+---------+
                                     |  docker_manager.py |
                                     |  Container start/  |
                                     |  stop/health-check |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     |  FlareSolverr      |
                                     |  Docker Container  |
                                     |  (port 8191)       |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     |    hltv.org        |
                                     |  (Cloudflare CDN)  |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     |  HTML Response     |
                                     |  (BeautifulSoup4   |
                                     |   parses into      |
                                     |   structured data) |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     | hltv_metadata.db   |
                                     | - ProPlayer        |
                                     | - ProPlayerStatCard|
                                     | - ProTeam          |
                                     +--------------------+
```

---

## How It Works (Step by Step)

1. **Preflight**: `HLTVStatFetcher.preflight_check()` verifies that `HLTV_SCRAPING_ENABLED` is
   true in settings and that `robots.txt` does not disallow the target paths.
2. **Docker check**: `docker_manager.ensure_flaresolverr()` guarantees the FlareSolverr container
   is running on port 8191. It tries `docker start flaresolverr` first, then falls back to
   `docker compose up -d` if the container does not exist.
3. **Discovery**: `fetch_top_players()` scrapes the Top 50 ranking page to collect player profile
   URLs automatically.
4. **Per-player fetch**: For each player URL, `fetch_and_save_player()` triggers a deep crawl:
   - Overview page: Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played
   - Trait sections: Firepower, Entrying, Utility (parsed from the same page)
   - Sub-pages: Clutches, Multikills, Career history (separate HTTP requests each)
5. **Parsing**: BeautifulSoup4 parses the HTML responses using CSS selectors defined in
   `selectors.py` and inline in `stat_fetcher.py`.
6. **Persistence**: Parsed data is upserted into `ProPlayer` and `ProPlayerStatCard` tables in
   `hltv_metadata.db` via SQLModel. KAST is converted from percentage to ratio (P-SAN-01).

---

## Rate Limiting

The `RateLimiter` class uses a **tiered delay system** (not a token bucket) that mimics human
browsing behavior with randomized jitter to avoid detection:

| Tier | Delay Range | Purpose |
|------|-------------|---------|
| `micro` | 2.0 -- 3.5s | Small waits within a page sequence |
| `standard` | 4.0 -- 8.0s | Normal page navigation between players |
| `heavy` | 10.0 -- 20.0s | Transition between different stat sections |
| `backoff` | 45.0 -- 90.0s | After a suspected block or network failure |

Additionally, `stat_fetcher.py` enforces its own `CRAWL_DELAY_MIN_SECONDS = 2` and
`CRAWL_DELAY_MAX_SECONDS = 7` between every HTTP request, using `random.uniform()`.

Random jitter is intentionally **unseeded** (F6-25): deterministic jitter would create detectable
request patterns. Anti-scraping detection relies on apparent human randomness.

The minimum effective delay between any two requests is **2.0 seconds** (hard floor).

---

## Data Model (What Gets Stored)

### `ProPlayer` table

| Column | Type | Description |
|--------|------|-------------|
| `hltv_id` | int | Unique HLTV player identifier (from URL) |
| `nickname` | str | Player nickname (e.g., "FalleN", "s1mple") |

### `ProPlayerStatCard` table

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | int | FK to `ProPlayer.hltv_id` |
| `rating_2_0` | float | HLTV Rating 2.0 |
| `kpr` | float | Kills per round |
| `dpr` | float | Deaths per round |
| `adr` | float | Average damage per round |
| `kast` | float | KAST ratio [0, 1] (converted from percentage via P-SAN-01) |
| `impact` | float | Impact rating |
| `headshot_pct` | float | Headshot percentage |
| `maps_played` | int | Total maps played |
| `opening_kill_ratio` | float | Opening kill ratio |
| `opening_duel_win_pct` | float | Opening duel win percentage |
| `detailed_stats_json` | str | JSON blob: clutches, multikills, career, trait sections |
| `time_span` | str | Always `"all_time"` (current implementation) |

### `detailed_stats_json` structure

```json
{
  "firepower": {"kpr": 0.85, "adr": 82.3, "adr_win": 95.1, "kpr_win": 1.02},
  "entrying": {"opening_win_pct": 55.2, "traded_deaths_pct": 18.7},
  "utility": {"flash_assists": 0.12},
  "clutches": {"1on1_wins": 142, "1on1_losses": 98, "1on2_wins": 31, "1on3_wins": 8},
  "multikills": {"3k": 215, "4k": 42, "5k": 7},
  "career": {"rating_history": {"2020": 1.12, "2021": 1.08, "2022": 1.15, "2023": 1.10}}
}
```

---

## Error Handling

- **FlareSolverr unreachable**: `docker_manager.py` tries `docker start`, then `docker compose up -d`,
  then returns `False`. The sync service logs an error and aborts.
- **Cloudflare challenge failure**: FlareSolverr returns a non-200 status; `flaresolverr_client.py`
  logs the error via `self.last_error` and returns `None`.
- **HTML parsing failures**: If CSS selectors find no matching elements, values default to `0.0`
  via `_safe_float()`. This is logged at DEBUG level.
- **Network timeouts**: FlareSolverr client has a 60-second default timeout. Docker health-check
  polls for up to 45 seconds at 3-second intervals.
- **Sub-page failures**: Individual sub-page fetch failures (clutches, multikills, career) are
  logged at WARNING (DS-07) but do not abort the overall player fetch. The corresponding JSON
  section will be an empty dict `{}`.
- **robots.txt check**: `check_robots_txt()` aborts the entire sync if HLTV explicitly disallows
  the target path. If `robots.txt` is unreachable (Cloudflare blocks raw requests), scraping
  proceeds with a warning.

---

## Legal / Ethical Notice (D-23)

This module scrapes publicly visible text data from hltv.org. HLTV's Terms of Service may
restrict automated access. The scraper:

- Checks `robots.txt` before each sync cycle and aborts if disallowed
- Enforces 2--7 second random delays between every HTTP request
- Can be disabled entirely via `HLTV_SCRAPING_ENABLED=false` in user settings

Use of this module is the operator's responsibility. Disable scraping if you are unsure about
compliance in your jurisdiction.

---

## Development Notes

### Prerequisites

- Docker Desktop (or Docker Engine) must be installed and running
- FlareSolverr container image: `ghcr.io/flaresolverr/flaresolverr:v3.4.6`
- Python dependency: `beautifulsoup4` (optional import; raises `ImportError` at instantiation)

### Quick Start

```bash
# Pull and run FlareSolverr
docker pull ghcr.io/flaresolverr/flaresolverr:v3.4.6
docker run -d --name flaresolverr -p 8191:8191 \
    -e LOG_LEVEL=info -e TZ=America/Sao_Paulo \
    --restart unless-stopped \
    ghcr.io/flaresolverr/flaresolverr:v3.4.6

# Verify health
curl http://localhost:8191/
```

### Logging

All modules use structured logging via `get_logger("cs2analyzer.<module>")`:
- `cs2analyzer.docker_manager` -- container lifecycle events
- `cs2analyzer.flaresolverr` -- FlareSolverr REST API interactions
- `cs2analyzer.hltv.rate_limit` -- delay tier and sleep duration
- `cs2analyzer.hltv_stat_fetcher` -- player discovery, parsing, database persistence

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `HLTV_SCRAPING_ENABLED` | `"true"` | Master switch to enable/disable scraping |

### Selector Maintenance

When HLTV changes its page layout, update CSS selectors in two places:
1. `selectors.py` -- `PlayerStatsSelectors` class (table rows, name column, rating column)
2. `stat_fetcher.py` -- inline `soup.select()` calls in parsing methods

### FlareSolverr Session Management

`FlareSolverrClient` supports persistent browser sessions for cookie reuse across multiple
requests. Sessions are created with `create_session()` and destroyed with `destroy_session()`.
If no session is active, each request creates a fresh browser context.

### Key Invariants

| ID | Rule |
|----|------|
| P-SAN-01 | KAST converted from percentage (74.0) to ratio (0.74) before storage |
| D-23 | `robots.txt` checked before every sync cycle; aborts if disallowed |
| DS-05 | `project_root` path resolved and validated before subprocess `cwd` |
| DS-07 | Sub-page fetch failures logged at WARNING, do not abort player fetch |
| F6-05 | Rate limiter delay logged at DEBUG with tier name |
| F6-25 | Random jitter intentionally unseeded to avoid detectable patterns |
