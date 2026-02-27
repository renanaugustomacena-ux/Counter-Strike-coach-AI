from pathlib import Path

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.lifecycle")


class DemoLifecycleManager:
    def __init__(self, raw_dir: Path, processed_dir: Path):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir

    def cleanup_old_demos(self, days: int = 30):
        """Removes demos older than X days to save space."""
        import time

        now = time.time()
        _purge_expired_demos(self.processed_dir, now, days)


def _purge_expired_demos(directory, now, days):
    for f in directory.glob("*.dem"):
        if f.stat().st_mtime < now - (days * 86400):
            f.unlink()
            logger.info("Cleaned up old demo: %s", f.name)
