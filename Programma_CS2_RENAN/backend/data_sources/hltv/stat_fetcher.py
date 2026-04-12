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
        enabled = str(get_setting("HLTV_SCRAPING_ENABLED", "true")).lower()
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

        # Fallback: direct stats page (may be blocked by robots.txt)
        url = "https://www.hltv.org/stats/players"
        logger.info("Fallback: discovering players from %s (no query params)", url)
        try:
            time.sleep(random.uniform(CRAWL_DELAY_MIN_SECONDS, CRAWL_DELAY_MIN_SECONDS + 2))
            html = self._solver.get(url)
            if not html:
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
                    full_url = "https://www.hltv.org" + link_tag["href"]
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
            time.sleep(random.uniform(CRAWL_DELAY_MIN_SECONDS, CRAWL_DELAY_MIN_SECONDS + 2))
            html = self._solver.get(url)
            if not html:
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
                    name_el = team_el.select_one(".name")
                    rank_el = team_el.select_one(".position")
                    link_el = team_el.select_one("a.moreLink")

                    if not name_el or not link_el:
                        continue

                    team_name = name_el.text.strip()
                    rank_text = rank_el.text.strip().lstrip("#") if rank_el else "0"
                    rank_num = int(re.sub(r"\D", "", rank_text) or 0)

                    href = link_el.get("href", "")
                    m = re.search(r"/team/(\d+)/", href)
                    team_hltv_id = int(m.group(1)) if m else 0

                    # Extract roster from ranking page (avoids extra HTTP request)
                    players = []
                    for player_el in team_el.select("td.player-holder a.pointer"):
                        nick_el = player_el.select_one("div.nick")
                        p_href = player_el.get("href", "")
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

            logger.info(
                "Discovered %d teams with %d total players.",
                len(results),
                sum(len(t["players"]) for t in results),
            )
            return results
        except Exception:
            logger.exception("Error discovering top teams")
            return []

    def save_teams_and_players(self, teams: List[Dict[str, Any]]) -> int:
        """Persist discovered teams and link players to their teams.

        Returns the number of NEW player stat URLs to scrape.
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

    def fetch_and_save_player(self, url: str) -> bool:
        """
        Fetch player stats from HLTV and save to hltv_metadata.db.

        Args:
            url: HLTV player stats URL (e.g. https://www.hltv.org/stats/players/2023/fallen)

        Returns:
            True if successfully fetched and saved, False otherwise.
        """
        data = self._fetch_player_stats(url)
        if not data:
            return False

        player_name = data.pop("player_name", "Unknown_Pro")
        hltv_id = data.pop("hltv_id", None)

        if hltv_id is None:
            logger.error("Could not extract HLTV ID from URL: %s", url)
            return False

        return self._save_to_db(hltv_id, player_name, data)

    def _fetch_player_stats(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetches Main Stats + Deep Dives (Clutches, Multikills, Career).
        """
        logger.info("Deep-Crawling stats for: %s", url)
        try:
            time.sleep(random.uniform(CRAWL_DELAY_MIN_SECONDS + 1, CRAWL_DELAY_MAX_SECONDS))
            html = self._solver.get(url)
            if not html:
                logger.error("FlareSolverr failed for %s", url)
                return None

            soup = BeautifulSoup(html, "html.parser")
            main_data = self._parse_overview(soup)

            # Extract ID and Name from URL: .../stats/players/{id}/{name}
            tokens = url.rstrip("/").split("/")
            if len(tokens) >= 2:
                p_id = tokens[-2]
                p_name = tokens[-1]

                # Try to parse HLTV ID
                try:
                    main_data["hltv_id"] = int(p_id)
                except ValueError:
                    logger.warning("Non-numeric player ID in URL: %s", p_id)
                    return None

                detailed = {}
                detailed.update(self._parse_trait_sections(soup))

                # Sub-pages
                clutch_url = url.replace("/stats/players/", "/stats/players/clutches/").replace(
                    f"/{p_id}/", f"/{p_id}/all/"
                )
                detailed["clutches"] = self._fetch_sub_stats(clutch_url, self._parse_clutches)

                multikill_url = url.replace(
                    "/stats/players/", "/stats/players/multikills/"
                ).replace(f"/{p_id}/", f"/{p_id}/all/")
                detailed["multikills"] = self._fetch_sub_stats(
                    multikill_url, self._parse_multikills
                )

                career_url = url.replace("/stats/players/", "/stats/players/career/")
                detailed["career"] = self._fetch_sub_stats(career_url, self._parse_career)

                main_data["detailed_stats_json"] = detailed

            return main_data

        except Exception:
            logger.exception("Error in Deep Crawl for %s", url)
            return None

    def _save_to_db(self, hltv_id: int, nickname: str, data: Dict[str, Any]) -> bool:
        """Save fetched data to ProPlayer + ProPlayerStatCard in hltv_metadata.db."""
        try:
            with self._hltv_db.get_session() as session:
                # Upsert ProPlayer
                player = session.exec(select(ProPlayer).where(ProPlayer.hltv_id == hltv_id)).first()

                if not player:
                    player = ProPlayer(hltv_id=hltv_id, nickname=nickname)
                    session.add(player)
                    session.commit()
                    session.refresh(player)
                    logger.info("Created ProPlayer: %s (ID: %s)", nickname, hltv_id)
                else:
                    player.nickname = nickname
                    session.add(player)
                    session.commit()

                # Upsert ProPlayerStatCard
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
                    # P-SAN-01: HLTV shows KAST as percentage (e.g. 74.0%);
                    # system stores as ratio [0, 1] (e.g. 0.74).
                    "kast": data.get("kast_pct", 0.0) / 100.0,
                    "impact": data.get("impact_rating", 0.0),
                    # V-2 FIX: Normalize headshot_pct to ratio [0, 1] (same as KAST above).
                    "headshot_pct": data.get("hs_pct", 0.0) / 100.0,
                    "maps_played": data.get("maps_played", 0),
                    "opening_kill_ratio": data.get("opening_kill_ratio", 0.0),
                    "opening_duel_win_pct": data.get("opening_duel_win_pct", 0.0),
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

    def _fetch_sub_stats(self, url: str, parser_func) -> Dict[str, Any]:
        """Generic helper for sub-page fetching."""
        try:
            time.sleep(random.uniform(CRAWL_DELAY_MIN_SECONDS, CRAWL_DELAY_MIN_SECONDS + 3))
            html = self._solver.get(url)
            if html:
                return parser_func(BeautifulSoup(html, "html.parser"))
        except Exception as e:
            # DS-07: Log at WARNING so production failures are visible.
            logger.warning("Sub-stat fetch failed for %s: %s", url, e)
        return {}

    def _safe_float(self, text: str | None) -> float:
        """Robust float parsing handling 'N/A', '-', and commas.

        Returns 0.0 for missing/unparseable values (convention: 0.0 = unknown).
        """
        if not text or text in ["-", "N/A", "nan"]:
            return 0.0
        try:
            clean_text = text.replace("%", "").replace(",", ".").strip()
            clean_text = clean_text.split()[0]
            return float(clean_text)
        except (ValueError, TypeError):
            logger.debug("Unparseable stat value: %r", text)
            return 0.0

    def _parse_overview(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parses the player overview page."""
        stats = {}
        rows = self._select_fallback(
            soup,
            [".stats-row", ".summary-row", ".stat-row", "div[class*='stats'] .row"],
            "player overview stats",
        )
        for row in rows:
            spans = row.find_all("span")
            if len(spans) == 2:
                label = spans[0].text.strip().lower()
                value = spans[1].text.strip()

                if "damage / round" in label:
                    stats["adr"] = value
                if "kills / round" in label:
                    stats["kpr"] = value
                if "deaths / round" in label:
                    stats["dpr"] = value
                if "headshot" in label:
                    stats["hs"] = value
                if "kast" in label:
                    stats["kast"] = value
                if "rating" in label:
                    stats["rating"] = value
                if "impact" in label:
                    stats["impact"] = value
                if "maps played" in label:
                    stats["maps_played"] = value

        mapped = {
            "kpr": self._safe_float(stats.get("kpr")),
            "dpr": self._safe_float(stats.get("dpr")),
            "adr": self._safe_float(stats.get("adr")),
            "hs_pct": self._safe_float(stats.get("hs")),
            "kast_pct": self._safe_float(stats.get("kast")),
            "rating": self._safe_float(stats.get("rating")),
            "impact_rating": self._safe_float(stats.get("impact")),
            "maps_played": int(self._safe_float(stats.get("maps_played"))),
        }

        # K/D ratio
        if mapped["dpr"] > 0:
            mapped["kd_ratio"] = mapped["kpr"] / mapped["dpr"]
        else:
            mapped["kd_ratio"] = 0.0

        # Player nickname (fallback chain for HLTV layout variants)
        player_name = None
        name_tag = (
            soup.select_one(".player-nickname")
            or soup.select_one("h1.summaryNickname")
            or soup.select_one(".playerNick")
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

    def _parse_trait_sections(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parses Firepower, Entrying, Utility columns from Main Stats Page."""
        traits = {}

        section_map = {
            "Kills per round": ("firepower", "kpr"),
            "Damage per round": ("firepower", "adr"),
            "Opening duel win": ("entrying", "opening_win_pct"),
            "Traded deaths": ("entrying", "traded_deaths_pct"),
            "Flash assists": ("utility", "flash_assists"),
            "Damage per round win": ("firepower", "adr_win"),
            "Kills per round win": ("firepower", "kpr_win"),
        }

        rows = soup.select("tr") + soup.select(".stats-row")

        for row in rows:
            text = row.text.strip()
            for key_phrase, (category, json_key) in section_map.items():
                if key_phrase.lower() in text.lower():
                    chunks = [t.strip() for t in row.text.split("\n") if t.strip()]
                    if len(chunks) >= 2:
                        val = self._safe_float(chunks[-1])
                        if category not in traits:
                            traits[category] = {}
                        traits[category][json_key] = val

        return traits

    def _parse_clutches(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parses the Clutches table."""
        clutches = {}
        rows = soup.select(".stats-table tr")
        for row in rows:
            cols = row.select("td")
            text = row.text.lower()
            if "1 on 1" in text and len(cols) >= 2:
                clutches["1on1_wins"] = self._safe_float(cols[-2].text)
                clutches["1on1_losses"] = self._safe_float(cols[-1].text)
            elif "1 on 2" in text and len(cols) >= 2:
                clutches["1on2_wins"] = self._safe_float(cols[-2].text)
            elif "1 on 3" in text and len(cols) >= 2:
                clutches["1on3_wins"] = self._safe_float(cols[-2].text)
        return clutches

    def _parse_multikills(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parses Multi-Kill summary."""
        mk = {}
        rows = soup.select(".stats-table tr")
        for row in rows:
            text = row.text
            if "3 kills" in text:
                mk["3k"] = self._safe_float(row.select("td")[-1].text)
            if "4 kills" in text:
                mk["4k"] = self._safe_float(row.select("td")[-1].text)
            if "5 kills" in text:
                mk["5k"] = self._safe_float(row.select("td")[-1].text)
        return mk

    def _parse_career(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parses Career Rating history."""
        career = {}
        rows = soup.select(".stats-table tbody tr")
        history = {}
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 2:
                period = cols[0].text.strip()
                rating = self._safe_float(cols[1].text)
                if period.isdigit():
                    history[period] = rating
        career["rating_history"] = history
        return career
