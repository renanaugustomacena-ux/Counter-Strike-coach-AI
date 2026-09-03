# HLTV Professional Player Statistics Scraper

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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
- Fetches from the overview page: role stats (40 stats across combined/CT/T sides) and section scores (0-100, e.g. Firepower)
- Fetches sub-pages: Individual (incl. multikill rounds 2k-5k and opening duels), Career rating history, Opponents, Clutches (per-tier counts 1on1-1on5)
- Auto-discovers player URLs via the HLTV world team ranking (top 30 teams, ~150 players). Falls back to `/stats/players` if team discovery returns zero
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
| `__init__.py` | 0 | Package initialization (empty marker) |
| `docker_manager.py` | 138 | Docker/FlareSolverr container lifecycle: `ensure_flaresolverr()`, health-check, `stop_flaresolverr()` |
| `flaresolverr_client.py` | 162 | REST client for FlareSolverr API: session management (`create_session`/`destroy_session`), `get()` via proxy with retries (backoff 5s/15s/45s) |
| `stat_fetcher.py` | 969 | `HLTVStatFetcher`: discovery (`fetch_top_teams`, `fetch_top_players`), HTML parsing via inline `soup.select()`, rate limiting via `CRAWL_DELAY_MIN/MAX_SECONDS` + adaptive backoff, database persistence |

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
                        |   - fetch_top_teams(30)  |
                        |   - fetch_top_players()  |
                        |   - fetch_and_save_player|
                        |   Inline soup.select()   |
                        |   CRAWL_DELAY 2-7s       |
                        +------------+-------------+
                                     |
                                     v
                                     +----------+---------+
                                     | flaresolverr_      |
                                     | client.py          |
                                     | REST via :8191     |
                                     +----------+---------+
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
3. **Discovery**: `fetch_top_teams(count=30)` scrapes `/ranking/teams/` (robots.txt-compliant)
   to extract the top teams and their rosters, yielding ~150 player stat URLs. If team discovery
   returns zero, the caller falls back to `fetch_top_players()` which targets `/stats/players`
   (note: `/stats/players?rankingFilter=Top50` is disallowed by HLTV `robots.txt` as of
   2026-04-12 — see `check_robots_txt()` at stat_fetcher.py:70).
4. **Per-player fetch**: For each player URL, `fetch_and_save_player()` triggers a deep crawl:
   - Overview page: Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played, profile
     (real name, country, age), role stats and section scores (parsed from the same page)
   - Sub-pages (separate HTTP request each): Individual, Career, Opponents, Clutches.
     Sub-pages are date-filtered from `HLTV_STATS_START_DATE` (2021-06-01) to **today**,
     computed at request time (R4 MED: a hardcoded end date used to freeze the window).
   - Multikill counts (2k-5k) and opening-duel stats are derived from the Individual page;
     there is no separate Multikills sub-page.
5. **Parsing**: BeautifulSoup4 parses the HTML responses using CSS selectors defined inline
   in `stat_fetcher.py` via `soup.select()` with multi-selector fallback (`_select_fallback()`).
6. **Persistence**: After an H2 minimum-viable-stats check (players with missing core fields
   or rating <= 0 are skipped as likely parse failures), data is upserted into `ProPlayer` and
   `ProPlayerStatCard` in `hltv_metadata.db` via SQLModel. KAST, HS%, and opening duel win %
   are converted from percentage to ratio (P-SAN-01).

---

## Rate Limiting

Rate limiting is implemented directly in `stat_fetcher.py` as module-level constants, not as
a separate class:

```python
CRAWL_DELAY_MIN_SECONDS = 2  # stat_fetcher.py:51
CRAWL_DELAY_MAX_SECONDS = 7  # stat_fetcher.py:52
```

Every HTTP request through FlareSolverr is preceded by an adaptive sleep:
`base_delay = CRAWL_DELAY_MIN_SECONDS + min(consecutive_failures * 2, 10)` followed by
`time.sleep(random.uniform(base_delay, base_delay + 3))`. When healthy the effective
delay is therefore uniform in **2-5 seconds** (player overview pages add +1s: 3-6
seconds), growing by up to +10 seconds under consecutive failures (adaptive backoff;
each success decrements the failure counter).

Random jitter is intentionally **unseeded** (F6-25): deterministic jitter would create
detectable request patterns. Anti-scraping detection relies on apparent human randomness.
Additional dormant sleeps (one hour between sync cycles, six hours when HLTV is unreachable)
are enforced by the caller `hltv_sync_service.run_sync_loop()`.

---

## Data Model (What Gets Stored)

### `ProPlayer` table

| Column | Type | Description |
|--------|------|-------------|
| `hltv_id` | int | Unique HLTV player identifier (from URL) |
| `nickname` | str | Player nickname (e.g., "FalleN", "s1mple") |
| `real_name` | str? | Real name from the profile box (optional) |
| `country` | str? | Country from the profile box (optional) |
| `age` | int? | Age from the profile box (optional) |
| `team_id` | int? | FK to `ProTeam.hltv_id` (ON DELETE SET NULL, R2-07) |
| `last_updated` | datetime | UTC timestamp of the last sync |

### `ProPlayerStatCard` table

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | int | FK to `ProPlayer.hltv_id` (ON DELETE CASCADE, R2-07) |
| `rating_2_0` | float | HLTV Rating 2.0 |
| `kpr` | float | Kills per round |
| `dpr` | float | Deaths per round |
| `adr` | float | Average damage per round |
| `kast` | float | KAST ratio [0, 1] (converted from percentage via P-SAN-01) |
| `impact` | float | Impact rating |
| `headshot_pct` | float | Headshot ratio [0, 1] (converted from percentage) |
| `maps_played` | int | Total maps played |
| `opening_kill_ratio` | float | Opening kill ratio |
| `opening_duel_win_pct` | float | Opening duel win ratio [0, 1] (converted from percentage) |
| `clutch_win_count` | int | Sum of clutch counts across tiers (from the Clutches page) |
| `multikill_round_pct` | float | Multikill rounds (2k-5k) as % of rounds played |
| `detailed_stats_json` | str | JSON blob: see structure below (size-capped by a validator) |
| `time_span` | str | Always `"all_time"` (current implementation) |
| `last_updated` | datetime | UTC timestamp of the last sync |

### `detailed_stats_json` structure

```json
{
  "summary_boxes": {"...": "raw overview summary-box values"},
  "rating_version": "2.1",
  "rating_tier": "...",
  "legacy_stats": {"...": "raw label/value pairs from the overview stats rows"},
  "role_stats": {"combined": {"...": 0.0}, "ct": {"...": 0.0}, "t": {"...": 0.0}},
  "section_scores": {"Firepower": 85, "Entrying": 62},
  "individual": {"opening_kill_ratio": 1.2, "2_kill_rounds": 300},
  "career": {"2023": {"all": 1.10, "online": 1.08, "lan": 1.15, "majors": 1.05}},
  "opponents": [{"...": "per-opponent rows"}],
  "clutch_counts": {"1on1": 142, "1on2": 31, "1on3": 8},
  "multikill_counts": {"2k": 300, "3k": 215, "4k": 42, "5k": 7}
}
```

---

## Error Handling

- **FlareSolverr unreachable**: `docker_manager.py` tries `docker start`, then `docker compose up -d`,
  then returns `False`. The sync service logs an error and aborts.
- **Cloudflare challenge failure**: FlareSolverr returns a non-200 status; `flaresolverr_client.py`
  logs the error via `self.last_error` and returns `None`.
- **HTML parsing failures**: `_select_fallback()` logs a WARNING when all candidate CSS
  selectors fail; unparseable stat values default to `0.0` via `_safe_float()` (logged at
  DEBUG). `_safe_float()` distinguishes thousands commas ("39,606") from decimal commas
  ("0,85") — R4 HIGH fix.
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
- `cs2analyzer.hltv_stat_fetcher` -- player discovery, parsing, database persistence

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `HLTV_SCRAPING_ENABLED` | `"true"` | Master switch to enable/disable scraping |

### Selector Maintenance

When HLTV changes its page layout, update CSS selectors inline in `stat_fetcher.py`. The
`_select_fallback()` helper (stat_fetcher.py:145) takes an ordered list of candidate
selectors and logs a warning when a primary selector fails and a fallback activates, so
layout drift is detected early without breaking scraping. Inspect the WARNING logs for
"CSS fallback activated" messages and add new primary selectors above the existing ones.

### FlareSolverr Session Management

`FlareSolverrClient` supports persistent browser sessions for cookie reuse across multiple
requests. Sessions are created with `create_session()` and destroyed with `destroy_session()`.
If no session is active, each request creates a fresh browser context.

### Key Invariants

| ID | Rule |
|----|------|
| P-SAN-01 | KAST (and other %) converted from percentage (74.0) to ratio (0.74) before storage |
| D-23 | `robots.txt` checked before every sync cycle; aborts if disallowed |
| DS-05 | `project_root` path resolved and validated before subprocess `cwd` |
| DS-07 | Sub-page fetch failures logged at WARNING, do not abort player fetch |
| H2 | Minimum-viable-stats validation before persisting (skip likely parse failures) |
| F6-25 | Random jitter intentionally unseeded to avoid detectable patterns |
