import os
from pathlib import Path

from sqlmodel import select  # F6-31: moved from inside _queue_if_new() to module level

from Programma_CS2_RENAN.backend.storage.database import get_db_manager  # F6-31
from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask  # F6-31
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.steam_locator")


# F6-11: Steam path discovery is also performed in backend/data_sources/steam_demo_finder.py
# (supplementary). steam_locator.py is the primary authority. Consolidation deferred;
# ensure both use identical precedence order when modifying path resolution logic.
def get_steam_path():
    """Finds the Steam installation path."""
    if os.name == "nt":
        return _get_win_steam_path()
    return _get_linux_steam_path()


def _get_win_steam_path():
    try:
        import winreg

        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        p, _ = winreg.QueryValueEx(k, "SteamPath")
        return Path(p)
    except Exception as e:
        logger.error("Registry failed: %s", e)
        return None


def _get_linux_steam_path():
    linux_paths = [
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    for p in linux_paths:
        if p.exists():
            return p
    return None


def find_cs2_replays():
    """Locates the CS2 replays folder."""
    steam_path = get_steam_path()
    cs2_rel = Path("steamapps/common/Counter-Strike Global Offensive/game/csgo/replays")

    if steam_path and (steam_path / cs2_rel).exists():
        return steam_path / cs2_rel

    if os.name == "nt":
        return _get_fallback_win_path()
    return None


def _get_fallback_win_path():
    """
    Search for CS2 replays across all writable drives.
    Falls back when registry lookup fails.
    """
    try:
        import psutil

        # Get all writable partitions dynamically
        partitions = [
            p.mountpoint
            for p in psutil.disk_partitions()
            if "rw" in p.opts and os.path.isdir(p.mountpoint)
        ]
        logger.info("Discovered %s writable partitions via psutil", len(partitions))
    except Exception as e:
        # Fallback to common drive letters if psutil fails
        logger.warning("psutil unavailable or failed (%s), using hardcoded partition list", e)
        if os.name == "nt":
            # Extended list covering most common Windows drive letters
            partitions = ["C:\\", "D:\\", "E:\\", "F:\\", "G:\\", "H:\\"]
            logger.info("Searching hardcoded Windows partitions: %s", partitions)
        else:
            partitions = ["/"]
            logger.info("Searching root partition: /")

    # Common Steam installation subdirectories
    steam_subdirs = [
        "Program Files (x86)\\Steam",
        "Program Files\\Steam",
        "Steam",
        "Games\\Steam",
        "SteamLibrary",
    ]

    cs2_rel_path = "steamapps\\common\\Counter-Strike Global Offensive\\game\\csgo\\replays"

    # Search all combinations
    for drive in partitions:
        for steam_subdir in steam_subdirs:
            replay_path = Path(drive) / steam_subdir / cs2_rel_path
            if replay_path.exists():
                logger.info("Found CS2 replays: %s", replay_path)
                return replay_path

    logger.warning("No CS2 replay folder found on any drive")
    return None


def sync_steam_demos(target_dir):
    """Discovers local Steam demos and queues them."""
    if os.path.exists(target_dir):
        _iterate_demo_patterns(target_dir)


def _iterate_demo_patterns(target_dir):
    patterns = ["**/*.dem", "*.dem"]
    for p in patterns:
        _find_and_queue_demos(target_dir, p)


def _find_and_queue_demos(target_dir, pattern):
    demos = Path(target_dir).glob(pattern)
    for d in demos:
        _queue_if_new(d)


def _queue_if_new(demo_path):
    db = get_db_manager()
    p_str = str(demo_path)
    with db.get_session() as s:
        exist = s.exec(select(IngestionTask).where(IngestionTask.demo_path == p_str)).first()
        if not exist:
            logger.info("Queuing discovered Steam demo: %s", p_str)
            s.add(IngestionTask(demo_path=p_str, is_pro=False, status="queued"))
            s.commit()
