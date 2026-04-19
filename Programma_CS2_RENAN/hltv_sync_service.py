"""
HLTV Sync Service — Background daemon for pro player statistics scraping.

Periodically fetches player statistics (text data) from HLTV.org player pages
and saves to ProPlayer + ProPlayerStatCard in hltv_metadata.db.

This service does NOT download demo files — it only reads web pages
and extracts statistical data (Rating 2.0, K/D, ADR, KAST, HS%, etc.).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from Programma_CS2_RENAN.backend.data_sources.hltv.flaresolverr_client import FlareSolverrClient
from Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher import HLTVStatFetcher
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.hltv_sync_service")

# --- Path Stabilization ---
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = SCRIPT_DIR / "hltv_sync.pid"
STOP_SIGNAL = SCRIPT_DIR / "hltv_sync.stop"

# Dormant mode sleep duration (6 hours) when HLTV is unreachable
_DORMANT_SLEEP_S = 21600


def _dormant_sleep(seconds: int) -> None:
    """Sleep in 1-second increments, checking the stop signal."""
    for _ in range(seconds):
        if STOP_SIGNAL.exists():
            break
        time.sleep(1)


def run_sync_loop():
    """
    Main background loop.
    Fetches pro player statistics from HLTV.org player pages.
    Uses FlareSolverr (Docker) to bypass Cloudflare protection.
    """
    logger.info("HLTV Sync Service Loop started.")

    # --- Pre-flight: Auto-start FlareSolverr Docker container ---
    from Programma_CS2_RENAN.backend.data_sources.hltv.docker_manager import ensure_flaresolverr
    from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

    project_root = str(Path(__file__).resolve().parent.parent)
    if not ensure_flaresolverr(project_root):
        logger.error("FlareSolverr could not be started automatically.")
        get_state_manager().update_status("hunter", "Blocked", "FlareSolverr/Docker unavailable")
        get_state_manager().add_notification(
            "hunter",
            "error",
            "HLTV sync blocked: FlareSolverr unavailable and auto-start failed. "
            "Verify that Docker Desktop is running.",
        )
        return

    # --- Pre-flight: FlareSolverr availability (safety net) ---
    solver = FlareSolverrClient()
    if not solver.is_available():
        logger.error("FlareSolverr unavailable after auto-start! Run: docker start flaresolverr")
        get_state_manager().update_status("hunter", "Blocked", "FlareSolverr unreachable")
        get_state_manager().add_notification(
            "hunter",
            "error",
            "HLTV sync blocked: FlareSolverr unavailable. " "Run: docker start flaresolverr",
        )
        return

    # --- Pre-flight: HLTV connectivity test ---
    logger.info("Testing HLTV connectivity via FlareSolverr...")
    test_html = solver.get("https://www.hltv.org/stats")
    if not test_html:
        logger.error(
            "HLTV unreachable even via FlareSolverr. Dormant mode (%s hours).",
            _DORMANT_SLEEP_S // 3600,
        )
        get_state_manager().update_status("hunter", "Blocked", "HLTV unreachable via FlareSolverr")
        # WR-15: Notify user that HLTV is unreachable and scraper is dormant
        get_state_manager().add_notification(
            "hunter",
            "WARNING",
            f"HLTV unreachable via FlareSolverr. " f"Retrying in {_DORMANT_SLEEP_S // 3600} hours.",
        )
        _dormant_sleep(_DORMANT_SLEEP_S)
        return

    logger.info("HLTV connectivity test passed. Creating persistent session...")

    # Create persistent session for cookie reuse across requests
    solver.create_session()

    fetcher = HLTVStatFetcher()

    if STOP_SIGNAL.exists():
        os.remove(STOP_SIGNAL)

    while not STOP_SIGNAL.exists():
        try:
            # D-23: Check config flag + robots.txt before each cycle
            if not fetcher.preflight_check():
                get_state_manager().update_status(
                    "hunter", "Blocked", "Scraping disabled or disallowed by robots.txt"
                )
                # WR-15: Notify user that scraping is blocked
                get_state_manager().add_notification(
                    "hunter",
                    "INFO",
                    "HLTV scraping paused: disabled in settings or blocked by robots.txt. "
                    "Retrying in 1 hour.",
                )
                _dormant_sleep(3600)
                continue

            get_state_manager().update_status(
                "hunter", "Running", f"Stats sync cycle active at {time.ctime()}"
            )

            # 1. Discover top 30 teams and their rosters from HLTV ranking
            logger.info("Discovering top 30 teams and rosters...")
            teams = fetcher.fetch_top_teams(count=30)

            if teams:
                # 2. Persist teams and players, get URLs needing stat scraping
                player_urls = fetcher.save_teams_and_players(teams)
                logger.info(
                    "%d teams saved, %d players need stat scraping",
                    len(teams),
                    len(player_urls),
                )
            else:
                # Fallback: use legacy top-50 individual discovery
                logger.warning("Team discovery returned 0 — falling back to top 50 individuals")
                player_urls = fetcher.fetch_top_players()

            # 3. Deep crawl each player's stats
            synced = 0
            for url in player_urls:
                if STOP_SIGNAL.exists():
                    break
                if fetcher.fetch_and_save_player(url):
                    synced += 1

            logger.info("Cycle complete: %s players synced. Sleeping for 1 hour...", synced)
            get_state_manager().update_status(
                "hunter", "Idle", f"Sync complete: {synced} players. Next cycle in 1 hour."
            )
            if synced > 0:
                # WR-15: Notify user of successful sync with count
                get_state_manager().add_notification(
                    "hunter",
                    "INFO",
                    f"HLTV sync complete: {synced} pro player stats updated.",
                )
            _dormant_sleep(3600)

        except Exception as e:
            logger.error("Sync Loop Error: %s", e)
            time.sleep(60)

    # Cleanup persistent session
    solver.destroy_session()

    logger.info("Sync Loop received stop signal. Exiting.")
    if PID_FILE.exists():
        os.remove(PID_FILE)


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def start_detached():
    """Starts the sync service as a detached background process."""
    if PID_FILE.exists():
        # DA-06-01: Check if stored PID is actually alive before rejecting
        try:
            stored_pid = int(PID_FILE.read_text().strip())
            if _is_pid_alive(stored_pid):
                logger.warning("Sync service already running (PID: %s).", stored_pid)
                return
            logger.warning(
                "Stale PID file found (PID %s is dead). Removing and restarting.",
                stored_pid,
            )
            PID_FILE.unlink()
        except (ValueError, OSError) as e:
            logger.warning("Corrupt PID file, removing: %s", e)
            PID_FILE.unlink(missing_ok=True)

    python_exe = sys.executable
    main_script = SCRIPT_DIR / "main.py"

    process = subprocess.Popen(
        [python_exe, str(main_script), "--hltv-service"],
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            if os.name == "nt"
            else 0
        ),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(SCRIPT_DIR.parent),
    )

    PID_FILE.write_text(str(process.pid))
    logger.info("HLTV Sync Service launched in background (PID: %s)", process.pid)


def stop_service():
    """Signals the background service to stop and cleans up."""
    STOP_SIGNAL.touch()
    logger.info("Stop signal sent to HLTV Sync Service.")

    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            logger.info("Background process %s will stop at next cycle check.", pid)
        except Exception as e:
            logger.warning("Failed to read PID file during stop: %s", e)


if __name__ == "__main__":
    run_sync_loop()
