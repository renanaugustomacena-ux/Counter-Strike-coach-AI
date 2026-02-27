import datetime
import re

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.core.logger import app_logger
from Programma_CS2_RENAN.ingestion.hltv.browser.manager import BrowserManager
from Programma_CS2_RENAN.ingestion.hltv.cache import get_proxy
from Programma_CS2_RENAN.ingestion.hltv.rate_limit import RateLimiter
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.hltv_service")

# Reference player for calibration — s1mple (HLTV ID 7998 maps to stats page 21266)
REFERENCE_PLAYER_ID = 21266

# Default metadata values for fields not available from HLTV scraping
KILL_STD_DEFAULT = 0.1  # Placeholder — HLTV does not expose per-round variance
ADR_STD_DEFAULT = 5.0  # Placeholder — HLTV does not expose per-round variance


class HLTVApiService:
    def __init__(self, headless=True):
        self.browser_manager = BrowserManager(headless=headless)
        self.limiter = RateLimiter()
        self.proxy = get_proxy()

    def sync_range(self, start_id, end_id):
        page = self.browser_manager.start()
        db_manager = get_db_manager()
        ids = self._get_ids_range(start_id, end_id)
        app_logger.info("Starting Stability Sync for IDs %s...", ids)
        synced = _sync_ids_loop(self, page, db_manager, ids)
        self.browser_manager.close()
        return synced

    def _get_ids_range(self, start, end):
        ids = list(range(start, end + 1))
        if REFERENCE_PLAYER_ID not in ids:
            ids.append(REFERENCE_PLAYER_ID)
        ids.sort()
        return ids

    def _sync_player(self, page, db_manager, pid):
        # TASK 2.8.1: Check cache first
        cached_html = self.proxy.get_player_html(pid)

        if cached_html:
            app_logger.info("Cache HIT for ID %s", pid)
            # Load cached HTML into page to reuse JS extraction logic
            page.set_content(cached_html, wait_until="domcontentloaded")
            return _process_player_page(self, page, db_manager, pid)

        # Cache Miss - Fetch Live
        url = f"https://www.hltv.org/stats/players/individual/{pid}/_"
        app_logger.info("Fetching live from HLTV for ID %s...", pid)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Save to cache
            html_content = page.content()
            self.proxy.save_player_html(pid, html_content)

            self.limiter.wait("standard")
            return _process_player_page(self, page, db_manager, pid)

        except Exception as e:
            app_logger.error("Failed to fetch ID %s: %s", pid, e)
            return False

    def _extract_stats(self, page):
        return page.eval_on_selector(".statistics", _get_stats_js_eval())

    def _get_nickname(self, page, pid):
        if page.locator(".player-nickname").is_visible():
            return page.locator(".player-nickname").inner_text().strip()
        return f"Player_{pid}"

    def _map_to_model(self, data, nick, pid, html):
        stats = _build_stats_dict(data, nick, pid, html)
        m = PlayerMatchStats(**stats)
        _apply_hs_ratio(m, html)
        return m


def _sync_ids_loop(svc, page, db, id_list):
    count = 0
    for pid in id_list:
        try:
            if svc._sync_player(page, db, pid):
                count += 1
        except Exception as e:
            app_logger.error("Fail ID %s: %s", pid, e)
            svc.limiter.wait("backoff")
    return count


def _process_player_page(svc, page, db, pid):
    if "just a moment" in page.title().lower():
        app_logger.warning("Cloudflare detected: %s", pid)
        svc.limiter.wait("backoff")
        return False
    if not page.locator(".statistics").is_visible():
        app_logger.warning("No stats: %s", pid)
        return False
    _finalize_extraction(svc, page, db, pid)
    return True


def _finalize_extraction(svc, page, db, pid):
    data = svc._extract_stats(page)
    nick = svc._get_nickname(page, pid)
    m = svc._map_to_model(data, nick, pid, page.content())
    db.upsert(m)
    app_logger.info("Synced %s", nick)


def _get_stats_js_eval():
    return "el => { const rows = Array.from(el.querySelectorAll('.stat-row')); const d = {}; rows.forEach(r => { d[r.firstChild.innerText.trim()] = r.lastChild.innerText.trim(); }); return d; }"


def _build_stats_dict(d, nick, pid, html):
    # Validate required fields are present (no hardcoded fallbacks allowed)
    required_fields = {
        "Kills per round": d.get("Kills per round"),
        "Deaths per round": d.get("Deaths per round"),
        "Damage / round": d.get("Damage / round"),
        "KAST": d.get("KAST"),
    }

    missing = [k for k, v in required_fields.items() if v is None]
    if missing:
        logger.error("Player %s (%s) missing required fields: %s", pid, nick, missing)
        raise ValueError(f"Incomplete HLTV data for player {pid}: missing {missing}")

    # Extract rating (2.0 preferred, fallback to 1.0 if neither exists)
    rating_20 = d.get("Rating 2.0")
    rating_10 = d.get("Rating 1.0")
    if not rating_20 and not rating_10:
        logger.error("Player %s (%s) missing both Rating 2.0 and Rating 1.0", pid, nick)
        raise ValueError(f"No rating data for player {pid}")
    rating = float(rating_20 or rating_10)

    # K/D Ratio required
    kd_ratio_str = d.get("K/D Ratio")
    if not kd_ratio_str:
        logger.error("Player %s (%s) missing K/D Ratio", pid, nick)
        raise ValueError(f"No K/D ratio for player {pid}")

    # Impact (optional - defaults to 0.0 if missing)
    impact_str = d.get("Impact")
    impact = float(impact_str) if impact_str else 0.0
    if not impact_str:
        logger.warning("Player %s (%s) missing Impact stat - defaulting to 0.0", pid, nick)

    return {
        "user_id": "system",
        "player_name": nick,
        "demo_name": f"api_{pid}.dem",
        "avg_kills": float(required_fields["Kills per round"].split()[0]),
        "avg_deaths": float(required_fields["Deaths per round"].split()[0]),
        "avg_adr": float(required_fields["Damage / round"].split()[0]),
        "avg_hs": 0.0,  # Populated by _apply_hs_ratio from HTML regex
        "avg_kast": float(required_fields["KAST"].replace("%", "")) / 100,
        "rating": rating,
        "kd_ratio": float(kd_ratio_str),
        "kill_std": KILL_STD_DEFAULT,
        "adr_std": ADR_STD_DEFAULT,
        "impact_rounds": impact,
        "anomaly_score": 0.0,  # Computed later by drift detection
        "sample_weight": 1.0,  # Default weight for pro data
        "is_pro": True,
        "processed_at": datetime.datetime.utcnow(),
    }


def _apply_hs_ratio(m, html):
    match = re.search(r"Headshot %.*?(\d+\.\d+)%", html)
    if match:
        m.avg_hs = float(match.group(1)) / 100
    else:
        logger.warning(
            "Failed to extract Headshot % for %s (ID: %s) - avg_hs remains 0.0",
            m.player_name,
            m.demo_name,
        )
