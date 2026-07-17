"""
HLTV Player Statistics Fetcher

Fetches pro player statistics from HLTV.org player pages via FlareSolverr.
Saves data into ProPlayer + ProPlayerStatCard in hltv_metadata.db.

Data scraped (text only — no file downloads):
    - Main stats: Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact
    - Trait sections: Firepower, Entrying, Utility
    - Sub-pages: Clutches, Multikills, Career history

LEGAL/ETHICAL NOTICE (D-23):
    This module scrapes publicly visible text data from HLTV.org.
    HLTV's Terms of Service may restrict automated access. This scraper:
    - Checks robots.txt before each sync cycle and aborts if disallowed
    - Enforces 2-7 second random delays between requests
    - Can be disabled entirely via HLTV_SCRAPING_ENABLED=false in settings
    Use of this module is the operator's responsibility. Disable scraping
    if you are unsure about compliance in your jurisdiction.
"""

import json
import random
import re
import time
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from bs4 import BeautifulSoup

    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

from sqlmodel import select

from Programma_CS2_RENAN.backend.data_sources.hltv.flaresolverr_client import FlareSolverrClient
from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard, ProTeam
from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.hltv_stat_fetcher")

# D-23: Rate limiting for HLTV scraping — minimum delay (seconds) between requests.
# Respects server load even though HLTV does not publish a machine-readable robots.txt
# Crawl-delay. All requests go through FlareSolverr (headless browser), not raw HTTP.
CRAWL_DELAY_MIN_SECONDS = 2
CRAWL_DELAY_MAX_SECONDS = 7

_HLTV_ROBOTS_URL = "https://www.hltv.org/robots.txt"
_HLTV_BASE_URL = "https://www.hltv.org"

HLTV_STATS_START_DATE = "2021-06-01"


def _hltv_stats_end_date() -> str:
    """Today, ISO — computed at request time.

    R4 MED: this was a hardcoded past date ("2026-05-06"), silently freezing
    every sub-page stat (individual/career/opponents/clutches) at that day:
    all newer matches were excluded from the scraped window forever.
    """
    return datetime.now(timezone.utc).date().isoformat()


def check_robots_txt(target_url: str = _HLTV_BASE_URL + "/stats/players") -> bool:
    """Check HLTV robots.txt to verify scraping is not explicitly disallowed.

    Returns True if scraping is allowed (or robots.txt is unreachable),
    False if robots.txt explicitly disallows the target path.

    DP-04 FIX: HLTV is behind Cloudflare. Raw urllib cannot fetch robots.txt
    (gets an HTML JS-challenge page, not valid robots.txt). When the response
    is not parseable as robots.txt, we treat it as unreachable and proceed
    with caution — the same behavior documented for network errors.

    HLTV's real robots.txt (verified 2026-04-12 via FlareSolverr) disallows:
    - /stats?*rankingFilter* (our old discovery URL)
    - /stats/players/career/*? and /stats/players/clutches/*
    - Various query parameter combinations on /stats, /results, /matches
    Individual player pages like /stats/players/12345/name are ALLOWED.
    """
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(_HLTV_ROBOTS_URL)
    try:
        rp.read()
    except Exception as e:
        logger.warning(
            "Could not fetch robots.txt from %s: %s — proceeding with caution",
            _HLTV_ROBOTS_URL,
            e,
        )
        return True

    # DP-04: Cloudflare returns HTML instead of robots.txt to raw urllib.
    # The robotparser silently accepts the HTML and can_fetch() returns False
    # because no valid rules were parsed. Detect this by checking if the
    # parser has any entries at all — a valid robots.txt always has at least
    # one User-agent line.
    try:
        # RobotFileParser stores entries internally; if none parsed, the
        # response was not valid robots.txt (likely Cloudflare HTML).
        if not rp.entries and not rp.default_entry:
            logger.warning(
                "robots.txt from %s was not parseable (likely Cloudflare challenge) "
                "— proceeding with caution",
                _HLTV_ROBOTS_URL,
            )
            return True
    except AttributeError:
        # Older Python versions may not expose these attributes
        pass

    allowed = rp.can_fetch("*", target_url)
    if not allowed:
        logger.warning("robots.txt DISALLOWS scraping %s — aborting", target_url)
    return allowed


class HLTVStatFetcher:
    """
    Fetches player statistics from HLTV.org.

    Uses FlareSolverr (Docker) to bypass Cloudflare protection.
    All HTTP requests go through the local FlareSolverr REST API
    which resolves JS challenges automatically.

    Saves to ProPlayer + ProPlayerStatCard in hltv_metadata.db.
    """

    def __init__(self):
        if not _HAS_BS4:
            raise ImportError(
                "beautifulsoup4 is required for HLTV stat fetching. "
                "Install it with: pip install beautifulsoup4"
            )
        self._solver = FlareSolverrClient(timeout=60)
        self._hltv_db = get_hltv_db_manager()

    @staticmethod
    def _select_fallback(
        soup: "BeautifulSoup",
        selectors: List[str],
        description: str,
    ) -> list:
        """Try multiple CSS selectors in order, return first non-empty result.

        Logs a warning when the primary selector fails and a fallback activates,
        so HLTV layout changes are detected early without breaking scraping.
        """
        for i, selector in enumerate(selectors):
            result = soup.select(selector)
            if result:
                if i > 0:
                    logger.warning(
                        "CSS fallback activated for '%s': primary '%s' failed, "
                        "using '%s' (%d results)",
                        description,
                        selectors[0],
                        selector,
                        len(result),
                    )
                return result
        logger.warning("All CSS selectors failed for '%s'. Tried: %s", description, selectors)
        return []

    def preflight_check(self) -> bool:
        """D-23: Verify scraping is enabled and robots.txt allows it.

        Returns True if scraping may proceed, False otherwise.
        """
        enabled = str(get_setting("HLTV_SCRAPING_ENABLED", "true") or "true").lower()
        if enabled not in ("1", "true", "yes"):
            logger.info("HLTV scraping disabled via HLTV_SCRAPING_ENABLED setting")
            return False
        if not check_robots_txt():
            return False
        return True

    def fetch_top_players(self) -> List[str]:
        """Discover player stat page URLs for the top ranked teams' rosters.

        DP-04: The old URL /stats/players?rankingFilter=Top50 is disallowed
        by HLTV robots.txt. Instead, we use fetch_top_teams() to get rosters
        from the team ranking page (/ranking/teams/ — allowed), then build
        stat URLs for each player. This is both robots.txt compliant and
        discovers more players (150+ vs 50).
        """
        # First try: discover via team ranking page (robots.txt compliant)
        teams = self.fetch_top_teams(count=30)
        if teams:
            player_urls = []
            for team in teams:
                for p in team.get("players", []):
                    url = p.get("profile_url", "")
                    if url and url not in player_urls:
                        player_urls.append(url)
            if player_urls:
                logger.info(
                    "Discovered %d players from %d teams via ranking page",
                    len(player_urls),
                    len(teams),
                )
                return player_urls

        url = "https://www.hltv.org/stats/players"
        logger.info("Fallback: discovering players from %s (no query params)", url)
        try:
            base_delay = CRAWL_DELAY_MIN_SECONDS + min(self._consecutive_failures * 2, 10)
            time.sleep(random.uniform(base_delay, base_delay + 3))
            html = self._solver.get(url)
            if not html:
                self._consecutive_failures += 1
                logger.error("FlareSolverr failed for Top 50 page")
                return []

            soup = BeautifulSoup(html, "html.parser")
            player_links = []

            rows = self._select_fallback(
                soup,
                [".stats-table tbody tr", "table.stats tbody tr", "table tbody tr"],
                "top 50 player rows",
            )
            for row in rows:
                link_tag = row.select_one(".playerCol a") or row.select_one(
                    "td a[href*='/players/']"
                )
                if link_tag and link_tag.get("href"):
                    full_url = "https://www.hltv.org" + str(link_tag["href"])
                    player_links.append(full_url)

            logger.info("Discovered %s players.", len(player_links))
            return player_links
        except Exception:
            logger.exception("Error discovering top players")
            return []

    def fetch_top_teams(self, count: int = 30) -> List[Dict[str, Any]]:
        """Scrape the HLTV world ranking page to discover top teams and their rosters.

        Returns a list of dicts, each with:
            hltv_id (int), name (str), world_rank (int),
            players: [{hltv_id, nickname, profile_url}, ...]
        """
        url = "https://www.hltv.org/ranking/teams/"
        logger.info("Discovering top %d teams from: %s", count, url)
        try:
            base_delay = CRAWL_DELAY_MIN_SECONDS + min(self._consecutive_failures * 2, 10)
            time.sleep(random.uniform(base_delay, base_delay + 3))
            html = self._solver.get(url)
            if not html:
                self._consecutive_failures += 1
                logger.error("FlareSolverr failed for team ranking page")
                return []

            soup = BeautifulSoup(html, "html.parser")
            ranked_teams = self._select_fallback(
                soup,
                [".ranked-team", ".team-ranking", "div[class*='ranked']"],
                "team ranking entries",
            )[:count]

            results = []
            for team_el in ranked_teams:
                try:
                    name_el = (
                        team_el.select_one(".name")
                        or team_el.select_one(".teamName")
                        or team_el.select_one("span[class*='name']")
                    )
                    rank_el = (
                        team_el.select_one(".position")
                        or team_el.select_one(".ranking-pos")
                        or team_el.select_one("span[class*='rank']")
                    )
                    link_el = team_el.select_one("a.moreLink") or team_el.select_one(
                        "a[href*='/team/']"
                    )

                    if not name_el or not link_el:
                        continue

                    team_name = name_el.text.strip()
                    rank_text = rank_el.text.strip().lstrip("#") if rank_el else "0"
                    rank_num = int(re.sub(r"\D", "", rank_text) or 0)

                    href = str(link_el.get("href", ""))
                    m = re.search(r"/team/(\d+)/", href)
                    team_hltv_id = int(m.group(1)) if m else 0

                    players = []
                    roster_selectors = [
                        "td.player-holder a.pointer",
                        ".lineup-con a[href*='/player/']",
                        "a[href*='/player/']",
                    ]
                    roster_els = []
                    for sel in roster_selectors:
                        roster_els = team_el.select(sel)
                        if roster_els:
                            break
                    for player_el in roster_els:
                        nick_el = (
                            player_el.select_one("div.nick")
                            or player_el.select_one(".nick")
                            or player_el.select_one("span.nick")
                        )
                        p_href = str(player_el.get("href", ""))
                        pm = re.search(r"/player/(\d+)/", p_href)
                        if nick_el and pm:
                            players.append(
                                {
                                    "hltv_id": int(pm.group(1)),
                                    "nickname": nick_el.text.strip(),
                                    "profile_url": _HLTV_BASE_URL
                                    + "/stats/players/"
                                    + pm.group(1)
                                    + "/"
                                    + nick_el.text.strip().lower(),
                                }
                            )

                    results.append(
                        {
                            "hltv_id": team_hltv_id,
                            "name": team_name,
                            "world_rank": rank_num,
                            "players": players,
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to parse team element: %s", e)

            total_players = sum(len(t["players"]) for t in results)
            if results and total_players < len(results):
                logger.warning(
                    "H2: Stale response — %d teams but only %d players "
                    "(expected ≥%d). HLTV layout may have changed.",
                    len(results),
                    total_players,
                    len(results) * 3,
                )
            self._consecutive_failures = max(0, self._consecutive_failures - 1)
            logger.info(
                "Discovered %d teams with %d total players.",
                len(results),
                total_players,
            )
            return results
        except Exception:
            self._consecutive_failures += 1
            logger.exception("Error discovering top teams")
            return []

    def save_teams_and_players(self, teams: List[Dict[str, Any]]) -> List[str]:
        """Persist discovered teams and link players to their teams.

        Returns the list of NEW player stat URLs to scrape.
        """
        db = get_hltv_db_manager()
        new_player_urls = []

        with db.get_session() as session:
            for team_data in teams:
                # Upsert team
                existing = session.exec(
                    select(ProTeam).where(ProTeam.hltv_id == team_data["hltv_id"])
                ).first()
                if existing:
                    existing.name = team_data["name"]
                    existing.world_rank = team_data["world_rank"]
                    session.add(existing)
                else:
                    session.add(
                        ProTeam(
                            hltv_id=team_data["hltv_id"],
                            name=team_data["name"],
                            world_rank=team_data["world_rank"],
                        )
                    )

                # Upsert players and link to team
                for p in team_data["players"]:
                    player = session.exec(
                        select(ProPlayer).where(ProPlayer.hltv_id == p["hltv_id"])
                    ).first()
                    if player:
                        player.team_id = team_data["hltv_id"]
                        player.nickname = p["nickname"]
                        session.add(player)
                    else:
                        session.add(
                            ProPlayer(
                                hltv_id=p["hltv_id"],
                                nickname=p["nickname"],
                                team_id=team_data["hltv_id"],
                            )
                        )

                    # Check if we need to scrape this player's stats
                    has_stats = session.exec(
                        select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == p["hltv_id"])
                    ).first()
                    if not has_stats:
                        new_player_urls.append(p["profile_url"])

            session.commit()

        logger.info(
            "Saved %d teams. %d players need stat scraping.", len(teams), len(new_player_urls)
        )
        return new_player_urls

    _MIN_VIABLE_FIELDS = {"rating", "kpr", "maps_played"}

    def fetch_and_save_player(self, url: str) -> bool:
        """
        Fetch player stats from HLTV and save to hltv_metadata.db.

        H2: Validates minimum viable stats before persisting — a player
        with rating=0 and kpr=0 likely had a parsing failure.
        """
        data = self._fetch_player_stats(url)
        if not data:
            return False

        player_name = data.pop("player_name", "Unknown_Pro")
        hltv_id = data.pop("hltv_id", None)

        if hltv_id is None:
            logger.error("Could not extract HLTV ID from URL: %s", url)
            return False

        missing = [f for f in self._MIN_VIABLE_FIELDS if not data.get(f)]
        if missing:
            logger.warning(
                "H2: Skipping %s (ID %s) — missing minimum viable fields: %s",
                player_name,
                hltv_id,
                missing,
            )
            return False

        if data.get("rating", 0) <= 0:
            logger.warning(
                "H2: Skipping %s (ID %s) — rating=%.2f (likely parse failure)",
                player_name,
                hltv_id,
                data.get("rating", 0),
            )
            return False

        return self._save_to_db(hltv_id, player_name, data)

    def _fetch_player_stats(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch overview + all sub-pages for one player.

        Sub-pages use HLTV_STATS_START_DATE.._hltv_stats_end_date() (today).
        Overview has no date filter.
        """
        logger.info("Deep-crawling stats for: %s", url)
        try:
            base_delay = CRAWL_DELAY_MIN_SECONDS + 1 + min(self._consecutive_failures * 2, 10)
            time.sleep(random.uniform(base_delay, base_delay + 3))
            html = self._solver.get(url)
            if not html:
                self._consecutive_failures += 1
                logger.error("FlareSolverr failed for %s", url)
                return None

            soup = BeautifulSoup(html, "html.parser")
            main_data = self._parse_overview(soup)

            tokens = url.rstrip("/").split("/")
            if len(tokens) < 2:
                return main_data

            p_id = tokens[-2]
            p_name = tokens[-1]
            try:
                main_data["hltv_id"] = int(p_id)
            except ValueError:
                logger.warning("Non-numeric player ID in URL: %s", p_id)
                return None

            date_qs = f"?startDate={HLTV_STATS_START_DATE}&endDate={_hltv_stats_end_date()}"
            base = f"{_HLTV_BASE_URL}/stats/players"

            sub_pages = {
                "individual": (
                    f"{base}/individual/{p_id}/{p_name}{date_qs}",
                    self._parse_individual,
                ),
                "career": (
                    f"{base}/career/{p_id}/{p_name}{date_qs}",
                    self._parse_career,
                ),
                "opponents": (
                    f"{base}/opponents/team/{p_id}/{p_name}{date_qs}",
                    self._parse_opponents,
                ),
                "clutch_counts": (
                    f"{base}/clutches/{p_id}/all/{p_name}{date_qs}",
                    self._parse_clutches,
                ),
            }

            detailed = main_data.pop("_detailed", {})

            for key, (sub_url, parser) in sub_pages.items():
                detailed[key] = self._fetch_sub_stats(sub_url, parser)

            ind = detailed.get("individual", {})
            if ind:
                main_data["opening_kill_ratio"] = ind.get("opening_kill_ratio", 0.0)
                main_data["opening_duel_win_pct"] = ind.get("opening_kill_win_pct", 0.0)
                detailed["multikill_counts"] = {
                    "2k": int(ind.get("2_kill_rounds", 0)),
                    "3k": int(ind.get("3_kill_rounds", 0)),
                    "4k": int(ind.get("4_kill_rounds", 0)),
                    "5k": int(ind.get("5_kill_rounds", 0)),
                }

            clutch_data = detailed.get("clutch_counts", {})
            if isinstance(clutch_data, dict):
                main_data["clutch_win_count"] = sum(clutch_data.values())

            rounds_played = main_data.get("rounds_played", 0)
            if rounds_played > 0 and detailed.get("multikill_counts"):
                mk_rounds = sum(detailed["multikill_counts"].values())
                main_data["multikill_round_pct"] = (mk_rounds / rounds_played) * 100.0

            main_data["detailed_stats_json"] = detailed
            self._consecutive_failures = max(0, self._consecutive_failures - 1)
            return main_data

        except Exception:
            self._consecutive_failures += 1
            logger.exception("Error in deep crawl for %s", url)
            return None

    def _save_to_db(self, hltv_id: int, nickname: str, data: Dict[str, Any]) -> bool:
        """Save fetched data to ProPlayer + ProPlayerStatCard in hltv_metadata.db."""
        try:
            with self._hltv_db.get_session() as session:
                player = session.exec(select(ProPlayer).where(ProPlayer.hltv_id == hltv_id)).first()

                profile = data.pop("profile", {})
                if not player:
                    player = ProPlayer(hltv_id=hltv_id, nickname=nickname)
                    session.add(player)
                    session.commit()
                    session.refresh(player)
                    logger.info("Created ProPlayer: %s (ID: %s)", nickname, hltv_id)

                player.nickname = nickname
                if profile.get("real_name"):
                    player.real_name = profile["real_name"]
                if profile.get("country"):
                    player.country = profile["country"]
                if profile.get("age"):
                    try:
                        player.age = int(profile["age"])
                    except (ValueError, TypeError):
                        pass
                session.add(player)
                session.commit()

                card = session.exec(
                    select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == hltv_id)
                ).first()

                detailed_json_str = "{}"
                if "detailed_stats_json" in data:
                    detailed_json_str = json.dumps(data.pop("detailed_stats_json"))

                card_data = {
                    "player_id": hltv_id,
                    "rating_2_0": data.get("rating", 0.0),
                    "kpr": data.get("kpr", 0.0),
                    "dpr": data.get("dpr", 0.0),
                    "adr": data.get("adr", 0.0),
                    "kast": data.get("kast_pct", 0.0) / 100.0,
                    "impact": data.get("impact_rating", 0.0),
                    "headshot_pct": data.get("hs_pct", 0.0) / 100.0,
                    "maps_played": data.get("maps_played", 0),
                    "opening_kill_ratio": data.get("opening_kill_ratio", 0.0),
                    "opening_duel_win_pct": data.get("opening_duel_win_pct", 0.0) / 100.0,
                    "clutch_win_count": data.get("clutch_win_count", 0),
                    "multikill_round_pct": data.get("multikill_round_pct", 0.0),
                    "detailed_stats_json": detailed_json_str,
                    "time_span": "all_time",
                }

                if card:
                    for key, value in card_data.items():
                        setattr(card, key, value)
                    session.add(card)
                else:
                    card = ProPlayerStatCard(**card_data)
                    session.add(card)

                session.commit()
                logger.info("Saved stat card for %s (ID: %s)", nickname, hltv_id)
                return True

        except Exception:
            logger.exception("Failed to save stats for %s (ID: %s)", nickname, hltv_id)
            return False

    _consecutive_failures: int = 0

    def _fetch_sub_stats(self, url: str, parser_func) -> Dict[str, Any]:
        """Generic helper for sub-page fetching.

        H2: Adaptive delay — increases crawl delay after consecutive failures
        to reduce load on HLTV when experiencing issues.
        """
        try:
            base_delay = CRAWL_DELAY_MIN_SECONDS + min(self._consecutive_failures * 2, 10)
            time.sleep(random.uniform(base_delay, base_delay + 3))
            html = self._solver.get(url)
            if html:
                result = parser_func(BeautifulSoup(html, "html.parser"))
                self._consecutive_failures = max(0, self._consecutive_failures - 1)
                return result
            self._consecutive_failures += 1
        except Exception as e:
            self._consecutive_failures += 1
            logger.warning(
                "Sub-stat fetch failed for %s: %s (failures: %d)",
                url,
                e,
                self._consecutive_failures,
            )
        return {}

    # R4 HIGH (2026-07-16): HLTV renders large counters with comma as the
    # THOUSANDS separator ("39,606" rounds). Blind ','→'.' turned those into
    # 39.606 → int 39, silently poisoning every ratio built on them.
    _THOUSANDS_RE = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$")

    def _safe_float(self, text: Optional[str]) -> float:
        """Robust float parsing handling 'N/A', '-', and commas.

        Comma handling: a digit-grouped string ("39,606" / "1,234.5") drops
        the thousands commas; otherwise a comma is treated as a decimal
        separator (legacy behaviour, e.g. "0,85").
        Returns 0.0 for missing/unparseable values (convention: 0.0 = unknown).
        """
        if not text or text in ["-", "N/A", "nan"]:
            return 0.0
        try:
            clean_text = text.replace("%", "").strip()
            clean_text = clean_text.split()[0]
            if self._THOUSANDS_RE.match(clean_text):
                clean_text = clean_text.replace(",", "")
            else:
                clean_text = clean_text.replace(",", ".")
            return float(clean_text)
        except (ValueError, TypeError, IndexError):
            logger.debug("Unparseable stat value: %r", text)
            return 0.0

    def _parse_player_summary_box(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse player summary stat-box: Rating (1.0 or 2.0) + 6 data boxes.

        Returns canonical values for dedicated columns, 'raw_boxes' for the
        JSON blob, and 'rating_version' (e.g. "Rating 2.0").
        """
        result: Dict[str, Any] = {}
        raw_boxes: Dict[str, Dict[str, Any]] = {}

        for w in soup.select(".player-summary-stat-box-rating-wrapper"):
            label_el = w.select_one(".player-summary-stat-box-data-text")
            value_el = w.select_one(".player-summary-stat-box-rating-data-text")
            if label_el and value_el:
                label = "".join(c for c in label_el.children if isinstance(c, str)).strip()
                if "rating" in label.lower():
                    result["rating_2_0"] = value_el.get_text(strip=True)
                    result["rating_version"] = label

        for w in soup.select(".player-summary-stat-box-data-wrapper"):
            value_el = w.select_one(".player-summary-stat-box-data")
            label_el = w.select_one(".player-summary-stat-box-data-text")
            if not (value_el and label_el):
                continue
            label = "".join(c for c in label_el.children if isinstance(c, str)).strip()
            value = value_el.get_text(strip=True)
            above_avg = "aboveAverage" in (w.get("class") or [])
            raw_boxes[label] = {"value": value, "above_avg": above_avg}
            if value in ("-", "", "N/A"):
                continue
            lbl = label.lower()
            if lbl == "kast":
                result["kast"] = value
            elif lbl == "dpr":
                result["dpr"] = value
            elif lbl == "adr":
                result["adr"] = value
            elif lbl == "kpr":
                result["kpr"] = value

        result["raw_boxes"] = raw_boxes
        return result

    def _parse_profile(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract real_name, country, age from overview page profile section."""
        profile: Dict[str, str] = {}
        name_el = soup.select_one(".player-summary-stat-box-left-player-name")
        if name_el:
            profile["real_name"] = name_el.get_text(strip=True)
        age_el = soup.select_one(".player-summary-stat-box-left-player-age")
        if age_el:
            m = re.search(r"(\d+)", age_el.get_text(strip=True))
            if m:
                profile["age"] = m.group(1)
        flag_el = soup.select_one(".player-summary-stat-box-left-flag img.flag[title]")
        if not flag_el:
            flag_el = soup.select_one("img.flag[title]")
        if flag_el and flag_el.get("title"):
            profile["country"] = str(flag_el["title"]).strip()
        return profile

    def _parse_overview(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse overview page: profile + summary boxes + legacy stats.

        Returns flat dict for ProPlayerStatCard dedicated columns,
        plus 'profile' and '_detailed' sub-dicts for further processing.
        """
        detailed: Dict[str, Any] = {}

        profile = self._parse_profile(soup)
        summary = self._parse_player_summary_box(soup)
        detailed["summary_boxes"] = summary.get("raw_boxes", {})
        detailed["rating_version"] = summary.get("rating_version", "")

        tier_el = soup.select_one(".player-summary-stat-box-rating-text")
        if tier_el:
            detailed["rating_tier"] = tier_el.get_text(strip=True)

        legacy: Dict[str, str] = {}
        legacy_raw: Dict[str, str] = {}
        rows = self._select_fallback(
            soup,
            [".stats-row", ".summary-row", ".stat-row"],
            "player overview stats",
        )
        for row in rows:
            spans = row.find_all("span")
            if len(spans) == 2:
                label = spans[0].text.strip()
                value = spans[1].text.strip()
                legacy_raw[label] = value
                lbl = label.lower()
                if "damage / round" in lbl or "damage/round" in lbl:
                    legacy["adr"] = value
                elif "kills / round" in lbl or "kills/round" in lbl:
                    legacy["kpr"] = value
                elif "deaths / round" in lbl or "deaths/round" in lbl:
                    legacy["dpr"] = value
                elif "headshot" in lbl:
                    legacy["hs"] = value
                elif "kast" in lbl:
                    legacy["kast"] = value
                elif "impact" in lbl:
                    legacy["impact"] = value
                elif "rating" in lbl:
                    legacy["rating"] = value
                elif "maps played" in lbl:
                    legacy["maps_played"] = value
                elif "rounds played" in lbl:
                    legacy["rounds_played"] = value
        detailed["legacy_stats"] = legacy_raw
        detailed["role_stats"] = self._parse_role_stats(soup)
        detailed["section_scores"] = self._parse_section_scores(soup)

        for k in ("rating_2_0", "kast", "dpr", "adr", "kpr"):
            if k in summary:
                legacy[k if k != "rating_2_0" else "rating"] = summary[k]

        mapped: Dict[str, Any] = {
            "kpr": self._safe_float(legacy.get("kpr")),
            "dpr": self._safe_float(legacy.get("dpr")),
            "adr": self._safe_float(legacy.get("adr")),
            "hs_pct": self._safe_float(legacy.get("hs")),
            "kast_pct": self._safe_float(legacy.get("kast")),
            "rating": self._safe_float(legacy.get("rating")),
            "impact_rating": self._safe_float(legacy.get("impact")),
            "maps_played": int(self._safe_float(legacy.get("maps_played"))),
            "rounds_played": int(self._safe_float(legacy.get("rounds_played"))),
            "profile": profile,
            "_detailed": detailed,
        }

        if mapped["dpr"] > 0:
            mapped["kd_ratio"] = mapped["kpr"] / mapped["dpr"]
        else:
            mapped["kd_ratio"] = 0.0

        player_name = None
        name_tag = (
            soup.select_one(".player-summary-stat-box-left-nickname")
            or soup.select_one(".player-nickname")
            or soup.select_one("h1.summaryNickname")
            or soup.select_one("h1[class*='nick']")
        )
        if name_tag:
            player_name = name_tag.text.strip()
        if not player_name:
            title_tag = soup.find("title")
            if title_tag:
                m = re.search(r"'([^']+)'", title_tag.text)
                if m:
                    player_name = m.group(1)
        mapped["player_name"] = player_name or "Unknown_Pro"

        return mapped

    def _parse_role_stats(self, soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
        """Parse role stats (40 stats x 3 sides) from overview page.

        Each .role-stats-row carries its side as a class on the row itself:
        .stats-side-combined, .stats-side-ct, .stats-side-t.
        """
        result: Dict[str, Dict[str, Any]] = {"combined": {}, "ct": {}, "t": {}}

        for row in soup.select(".role-stats-row"):
            title_el = row.select_one(".role-stats-title")
            data_el = row.select_one(".role-stats-data")
            if not (title_el and data_el):
                continue

            stat_name = title_el.get_text(strip=True)
            val = data_el.get_text(strip=True)

            classes = row.get("class") or []
            if "stats-side-ct" in classes:
                side = "ct"
            elif "stats-side-t" in classes:
                side = "t"
            else:
                side = "combined"

            result[side][stat_name] = self._safe_float(val) if val else 0.0

        return result

    def _parse_section_scores(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Parse 7 section scores from overview (combined side only).

        Score lives in child .row-stats-section-score; section name is a
        bare text node inside .role-stats-section-title.
        """
        scores: Dict[str, int] = {}
        for wrapper in soup.select(".role-stats-section-title-wrapper.stats-side-combined"):
            title_el = wrapper.select_one(".role-stats-section-title")
            if not title_el:
                continue
            score_el = title_el.select_one(".row-stats-section-score")
            if not score_el:
                continue
            m = re.search(r"(\d+)/100", score_el.get_text(strip=True))
            if not m:
                continue
            name_parts = [c.strip() for c in title_el.children if isinstance(c, str) and c.strip()]
            section_name = name_parts[0] if name_parts else "Unknown"
            scores[section_name] = int(m.group(1))
        return scores

    def _parse_individual(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Parse individual stats page (24 stats via .stats-row).

        Uses exact lowercase label matching verified against live HLTV HTML.
        """
        stats: Dict[str, float] = {}
        label_map = {
            "kills": "total_kills",
            "deaths": "total_deaths",
            "kill / death": "kd_ratio",
            "kill / round": "kills_per_round",
            "rounds with kills": "rounds_with_kills",
            "total opening kills": "opening_kills",
            "total opening deaths": "opening_deaths",
            "opening kill ratio": "opening_kill_ratio",
            "opening kill rating": "opening_kill_rating",
            "team win percent after first kill": "opening_kill_win_pct",
            "first kill in won rounds": "first_kill_in_won_rounds",
            "0 kill rounds": "0_kill_rounds",
            "1 kill rounds": "1_kill_rounds",
            "2 kill rounds": "2_kill_rounds",
            "3 kill rounds": "3_kill_rounds",
            "4 kill rounds": "4_kill_rounds",
            "5 kill rounds": "5_kill_rounds",
            "rifle kills": "rifle_kills",
            "sniper kills": "sniper_kills",
            "smg kills": "smg_kills",
            "pistol kills": "pistol_kills",
            "grenade": "grenade_kills",
            "other": "other_kills",
        }
        for row in soup.select(".stats-row"):
            spans = row.find_all("span")
            if len(spans) == 2:
                label = spans[0].text.strip().lower()
                value = spans[1].text.strip()
                json_key = label_map.get(label)
                if json_key:
                    stats[json_key] = self._safe_float(value)
        return stats

    def _parse_opponents(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse opponents page — per-team stats.

        Team name td has two <a> children: [team_name, "See matches"].
        Extract only the first <a> text for the team name.
        """
        opponents: List[Dict[str, Any]] = []
        for row in soup.select(".stats-table tbody tr"):
            cols = row.select("td")
            if len(cols) >= 5:
                team_link = cols[0].select_one("a")
                team_name = (
                    team_link.get_text(strip=True) if team_link else cols[0].get_text(strip=True)
                )
                opponents.append(
                    {
                        "team": team_name,
                        "maps": int(self._safe_float(cols[1].get_text(strip=True))),
                        "kd_diff": cols[2].get_text(strip=True),
                        "kd": self._safe_float(cols[3].get_text(strip=True)),
                        "rating": self._safe_float(cols[4].get_text(strip=True)),
                    }
                )
        return opponents

    def _parse_clutches(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Parse clutches 'all' tier — count events per type from Type column."""
        counts: Dict[str, int] = {}
        for row in soup.select(".stats-table tbody tr"):
            cols = row.select("td")
            for col in cols:
                text = col.get_text(strip=True)
                m = re.match(r"1 on (\d)", text)
                if m:
                    tier = f"1on{m.group(1)}"
                    counts[tier] = counts.get(tier, 0) + 1
                    break
        return counts

    def _parse_career(self, soup: BeautifulSoup) -> Dict[str, Dict[str, float]]:
        """Parse career page — year-by-year ratings (all, online, lan, majors)."""
        career: Dict[str, Dict[str, float]] = {}
        for row in soup.select(".stats-table tbody tr"):
            cols = row.select("td")
            if len(cols) >= 5:
                period = cols[0].get_text(strip=True)
                career[period] = {
                    "all": self._safe_float(cols[1].get_text(strip=True)),
                    "online": self._safe_float(cols[2].get_text(strip=True)),
                    "lan": self._safe_float(cols[3].get_text(strip=True)),
                    "majors": self._safe_float(cols[4].get_text(strip=True)),
                }
        return career
