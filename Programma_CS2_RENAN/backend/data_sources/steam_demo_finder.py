"""
Steam Demo Auto-Discovery Module

Automatically discovers CS2 demos from Steam installation directory.
Scans for recent replays and enqueues them for processing.

Adheres to GEMINI.md principles:
- Explicit path detection with fallback strategies
- Fail-fast validation
- Clear error messaging
"""

import os
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

# winreg imported conditionally inside _get_steam_path_from_registry()


class SteamNotFoundError(Exception):
    """Raised when Steam installation cannot be located."""

    pass


class SteamDemoFinder:
    """
    Discovers CS2 demo files from Steam installation.

    Detection Strategy:
    1. Check registry (Windows)
    2. Check common installation paths
    3. Check environment variables
    """

    # Common Steam installation paths
    # Common Steam installation paths - DYNAMICALLY GENERATED
    WINDOWS_PATHS = []

    @classmethod
    def _generate_windows_paths(cls):
        """Dynamically generate search paths based on available drives."""
        paths = []
        import string
        from ctypes import windll

        # Get available drives
        drives = []
        try:
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:/")
                bitmask >>= 1
        except Exception as e:
            import logging

            logging.getLogger("cs2analyzer.steam_finder").warning("Drive detection failed: %s", e)
            drives = ["C:/", "D:/", "E:/"]  # Fallback

        # Common suffixes
        suffixes = ["Program Files (x86)/Steam", "Program Files/Steam", "Steam"]

        for drive in drives:
            for suffix in suffixes:
                paths.append(Path(drive) / suffix)

        return paths

    def __init__(self):
        # Initialize dynamic paths if on Windows
        if platform.system() == "Windows":
            self.WINDOWS_PATHS = self._generate_windows_paths()

    LINUX_PATHS = [
        Path.home() / ".steam" / "steam",
        Path.home() / ".local" / "share" / "Steam",
    ]

    # CS2 replay subdirectory
    CS2_REPLAY_PATH = "steamapps/common/Counter-Strike Global Offensive/game/csgo/replays"

    def find_steam_directory(self) -> Optional[Path]:
        """
        Locate Steam installation directory.

        Returns:
            Path to Steam directory, or None if not found
        """
        system = platform.system()

        if system == "Windows":
            # Try registry first
            steam_path = self._get_steam_path_from_registry()
            if steam_path:
                return steam_path

            # Fallback to common paths
            for path in self.WINDOWS_PATHS:
                if path.exists():
                    return path

        elif system == "Linux":
            for path in self.LINUX_PATHS:
                if path.exists():
                    return path

        return None

    def _get_steam_path_from_registry(self) -> Optional[Path]:
        """
        Get Steam installation path from Windows registry.

        Registry key: HKEY_CURRENT_USER\\Software\\Valve\\Steam\\SteamPath
        """
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)

            path = Path(steam_path)
            if path.exists():
                return path
        except (ImportError, FileNotFoundError, OSError):
            pass

        return None

    def find_cs2_replay_directory(self) -> Optional[Path]:
        """
        Locate CS2 replay directory.

        Returns:
            Path to CS2 replays folder, or None if not found
        """
        steam_dir = self.find_steam_directory()
        if not steam_dir:
            return None

        replay_dir = steam_dir / self.CS2_REPLAY_PATH
        if replay_dir.exists():
            return replay_dir

        return None

    def scan_recent_demos(self, days: int = 7) -> List[Tuple[Path, datetime]]:
        """
        Find demo files from last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of (filepath, modification_time) tuples
        """
        replay_dir = self.find_cs2_replay_directory()
        if not replay_dir:
            return []

        cutoff_time = datetime.now() - timedelta(days=days)
        recent_demos = []

        for dem_file in replay_dir.glob("*.dem"):
            try:
                mtime = datetime.fromtimestamp(dem_file.stat().st_mtime)
                if mtime >= cutoff_time:
                    recent_demos.append((dem_file, mtime))
            except OSError:
                continue  # Skip files we can't access

        # Sort by modification time (newest first)
        recent_demos.sort(key=lambda x: x[1], reverse=True)
        return recent_demos

    def get_demo_metadata(self, filepath: Path) -> dict:
        """
        Extract basic metadata from demo filename.

        CS2 demo naming: match<timestamp>_<map>.dem
        Example: match20260103_de_mirage.dem
        """
        filename = filepath.stem
        metadata = {
            "filename": filepath.name,
            "filepath": str(filepath),
            "size_mb": filepath.stat().st_size / (1024 * 1024),
            "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
        }

        # Try to extract map name
        if "_" in filename:
            parts = filename.split("_", 1)
            if len(parts) == 2:
                metadata["map"] = parts[1]

        return metadata


def auto_discover_steam_demos(days: int = 7) -> List[dict]:
    """
    Convenience function to discover recent Steam demos.

    Args:
        days: Number of days to look back

    Returns:
        List of demo metadata dictionaries
    """
    finder = SteamDemoFinder()
    recent_demos = finder.scan_recent_demos(days=days)

    return [finder.get_demo_metadata(filepath) for filepath, _ in recent_demos]


if __name__ == "__main__":
    # Self-test
    finder = SteamDemoFinder()

    print("=== Steam Demo Auto-Discovery ===\n")

    steam_dir = finder.find_steam_directory()
    if steam_dir:
        print(f"[OK] Steam directory: {steam_dir}")
    else:
        print("[!] Steam directory not found")

    replay_dir = finder.find_cs2_replay_directory()
    if replay_dir:
        print(f"[OK] CS2 replays: {replay_dir}\n")

        recent = finder.scan_recent_demos(days=7)
        print(f"Found {len(recent)} demos from last 7 days:\n")

        for filepath, mtime in recent[:5]:  # Show first 5
            metadata = finder.get_demo_metadata(filepath)
            print(f"  - {metadata['filename']}")
            print(f"    Size: {metadata['size_mb']:.1f} MB")
            print(f"    Modified: {metadata['modified']}\n")
    else:
        print("[!] CS2 replay directory not found")
