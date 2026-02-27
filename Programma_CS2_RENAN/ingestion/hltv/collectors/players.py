import datetime

import torch

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.ingestion.hltv.selectors import HLTVURLBuilder, PlayerStatsSelectors


class PlayerCollector:
    def __init__(self, page, limiter):
        self.page = page
        self.limiter = limiter

    def discover_player_ids(self, start_id=1, end_id=35000):
        ids_to_check = _prepare_id_list(start_id, end_id)
        print(f"Starting Discovery Pass for IDs {start_id} to {end_id}...")
        return _execute_discovery_loop(self, ids_to_check)

    def scrape_from_list(self, url_list):
        print(f"Starting Extraction Pass for {len(url_list)} validated URLs...")
        return _execute_extraction_loop(self, url_list)


def _prepare_id_list(start, end):
    ids = list(range(start, end + 1))
    if 21266 not in ids:
        ids.append(21266)
        ids.sort()
    return ids


def _execute_discovery_loop(collector, ids):
    valid_urls = []
    for pid in ids:
        url = f"https://www.hltv.org/player/{pid}/_"
        _check_single_player_id(collector, pid, url, valid_urls)
    return valid_urls


def _check_single_player_id(coll, pid, url, results):
    try:
        print(f"Checking ID {pid}...")
        resp = coll.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        coll.limiter.wait("micro")
        if _is_profile_valid(coll.page, resp, pid):
            print(f"[Valid] ID {pid} -> {coll.page.url}")
            results.append(coll.page.url)
    except Exception as e:
        print(f"[Error] Failed ID {pid}: {e}")
        coll.limiter.wait("backoff")


def _is_profile_valid(page, resp, pid):
    if resp.status >= 400 or "/player/" not in page.url or f"/{pid}/" not in page.url:
        return False
    return (
        page.locator(".playerRealname").is_visible() or page.locator(".playerNickname").is_visible()
    )


def _execute_extraction_loop(collector, url_list):
    db_manager = get_db_manager()
    count = 0
    for url in url_list:
        collector.limiter.wait("heavy")
        if _extract_player_data(collector, url, db_manager):
            count += 1
    return count


def _extract_player_data(coll, url, db):
    detailed_url = url.replace("/player/", "/stats/players/individual/")
    player_name = url.split("/")[-1]
    print(f"Extracting stats for {player_name}...")
    try:
        coll.page.goto(detailed_url, wait_until="domcontentloaded", timeout=60000)
        coll.limiter.wait("standard")
        return _process_extraction_page(coll, player_name, db)
    except Exception as e:
        print(f"[Error] Failed {url}: {e}")
        return False


def _process_extraction_page(coll, name, db):
    if not coll.page.locator(".statistics").is_visible():
        return False
    stats = coll.page.eval_on_selector(".statistics", _get_stats_js())
    match_stats = _map_stats_to_model(name, stats, coll.page.content())
    db.upsert(match_stats)
    print(f"[Success] Fully synced {name}")
    return True


def _get_stats_js():
    return """el => {
        const rows = Array.from(el.querySelectorAll('.stat-row'));
        const d = {};
        rows.forEach(r => {
            const label = r.firstChild.innerText.trim();
            const value = r.lastChild.innerText.trim();
            d[label] = value;
        });
        return d;
    }"""


def _map_stats_to_model(name, stats, html):
    return PlayerMatchStats(
        user_id="system",
        player_name=name,
        demo_name=f"hltv_discovered_{name}.dem",
        avg_kills=float(stats.get("Kills per round", "0.7").split()[0]),
        avg_deaths=float(stats.get("Deaths per round", "0.6").split()[0]),
        avg_adr=float(stats.get("Damage / round", "80.0").split()[0]),
        avg_hs=0.5,
        avg_kast=float(stats.get("KAST", "70%").replace("%", "")) / 100,
        rating=float(stats.get("Rating 2.0", stats.get("Rating 1.0", "1.0"))),
        kd_ratio=float(stats.get("K/D Ratio", "1.0")),
        kill_std=0.1,
        adr_std=5.0,
        impact_rounds=float(stats.get("Impact", "1.0")),
        anomaly_score=0.0,
        sample_weight=1.0,
        is_pro=True,
        processed_at=datetime.datetime.utcnow(),
    )
