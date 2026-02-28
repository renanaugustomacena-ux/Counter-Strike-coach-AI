import json
import shutil
from pathlib import Path
from typing import Set

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.demo_registry")


class DemoRegistry:
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self._load()

    def _load(self):
        data = _execute_registry_load(self.registry_path)
        # F6-20: Convert list → set for O(1) membership checks.
        # JSON serializes as list; we deserialize as set internally.
        self._processed: Set[str] = set(data.get("processed_demos", []))

    def _save(self):
        # Create backup before overwriting
        if self.registry_path.exists():
            backup_path = self.registry_path.with_suffix(".json.backup")
            try:
                shutil.copy2(self.registry_path, backup_path)
                logger.debug("Registry backup created: %s", backup_path)
            except Exception as e:
                logger.warning("Failed to create registry backup: %s", e)

        # F6-20: Serialize set back to list for JSON compatibility
        with open(self.registry_path, "w") as f:
            json.dump({"processed_demos": list(self._processed)}, f, indent=4)

    def is_processed(self, demo_name: str) -> bool:
        return demo_name in self._processed  # F6-20: O(1) set lookup

    def mark_processed(self, demo_name: str):
        if demo_name not in self._processed:  # F6-20: O(1) set lookup
            self._processed.add(demo_name)
            self._save()


def _execute_registry_load(path):
    """
    Load demo registry with backup recovery.

    If registry is corrupted, attempts to restore from .backup file.
    Only resets to empty if both primary and backup are unavailable.
    """
    if not path.exists():
        logger.info("Registry does not exist, creating new: %s", path)
        return {"processed_demos": []}

    # Try loading primary registry
    try:
        with open(path, "r") as f:
            data = json.load(f)
            logger.debug(
                "Registry loaded: %s demos processed", len(data.get("processed_demos", []))
            )
            return data
    except json.JSONDecodeError as e:
        logger.error("Registry file corrupted (JSON decode error): %s", e)
    except Exception as e:
        logger.error("Failed to load registry: %s", e)

    # Primary corrupted - attempt backup recovery
    backup_path = path.with_suffix(".json.backup")
    if backup_path.exists():
        try:
            with open(backup_path, "r") as f:
                data = json.load(f)
                logger.warning(
                    "Registry recovered from backup: %s demos", len(data.get("processed_demos", []))
                )
                # Restore backup to primary
                shutil.copy2(backup_path, path)
                return data
        except Exception as e:
            logger.error("Backup recovery also failed: %s", e)

    # Both primary and backup failed - reset to empty
    logger.critical("Registry reset to empty - all demo history lost!")
    return {"processed_demos": []}
