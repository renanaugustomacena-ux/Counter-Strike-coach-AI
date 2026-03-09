"""Platform-specific utilities (drive detection, etc.)."""

import os
from typing import List

from kivy.utils import platform

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.platform_utils")


def get_available_drives() -> List[str]:
    """Returns available drive roots. Windows: drive letters. Unix: ['/']."""
    if platform != "win":
        return ["/"]

    import string

    try:
        from ctypes import windll

        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(letter + ":\\")
            bitmask >>= 1
        return drives
    except Exception as e:
        logger.debug("Win32 drive detection failed: %s", e)
        try:
            import psutil

            writable_drives = [
                p.mountpoint
                for p in psutil.disk_partitions()
                if "rw" in p.opts and os.path.isdir(p.mountpoint)
            ]
            return writable_drives if writable_drives else [os.path.expanduser("~")]
        except Exception as e2:
            logger.debug("psutil drive detection failed: %s", e2)
            return [os.path.expanduser("~")]
