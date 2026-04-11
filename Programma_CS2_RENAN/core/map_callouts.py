"""
Map Callout System — Coordinate-to-callout translation for CS2 maps.

Canonical source for named map positions (callouts). Provides:
1. NamedPosition dataclass for position metadata
2. NamedPositionRegistry with nearest-neighbor lookup
3. get_callout() convenience function for human-readable position names

WR-77: This module is the single source of truth for callout data.
Other modules (engagement_range.py, round_reconstructor.py) import from here.

Usage:
    from Programma_CS2_RENAN.core.map_callouts import get_callout, get_callout_registry

    callout = get_callout("de_mirage", -290, -2080, 0)  # -> "A Site"
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.core.map_callouts")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NamedPosition:
    """A known map callout position with spatial and tactical metadata."""

    name: str  # "Triple Box", "Ticket Booth", "Window"
    map_name: str  # "de_mirage"
    center_x: float  # World X coordinate
    center_y: float  # World Y coordinate
    center_z: float  # World Z coordinate
    radius: float  # Engagement area radius (world units)
    level: str = "default"  # "default", "upper", "lower"


# ---------------------------------------------------------------------------
# Hardcoded callout positions for 9 competitive maps.
# Expanded from engagement_range.py with additional common callouts.
# ---------------------------------------------------------------------------

_NAMED_POSITIONS: List[NamedPosition] = [
    # ===== de_mirage =====
    NamedPosition("A Site", "de_mirage", -290, -2080, 0, 400),
    NamedPosition("B Site", "de_mirage", -2180, 540, 0, 350),
    NamedPosition("Mid", "de_mirage", -460, -530, 0, 350),
    NamedPosition("A Ramp", "de_mirage", 240, -1600, 0, 250),
    NamedPosition("B Apartments", "de_mirage", -1350, 520, 0, 300),
    NamedPosition("Window", "de_mirage", -1250, -545, 0, 150),
    NamedPosition("Connector", "de_mirage", -1100, -1200, 0, 250),
    NamedPosition("Jungle", "de_mirage", -1350, -1690, 0, 200),
    NamedPosition("Palace", "de_mirage", -600, -2550, 0, 250),
    NamedPosition("T Spawn", "de_mirage", 1400, -230, 0, 300),
    NamedPosition("CT Spawn", "de_mirage", -950, -2300, 0, 250),
    NamedPosition("Underpass", "de_mirage", -950, -320, -100, 200),
    NamedPosition("Catwalk", "de_mirage", -150, -1050, 0, 200),
    NamedPosition("Short", "de_mirage", -680, -1550, 0, 200),
    NamedPosition("Top Mid", "de_mirage", 100, -530, 0, 200),
    NamedPosition("B Short", "de_mirage", -1700, 250, 0, 200),
    NamedPosition("Market", "de_mirage", -1650, -1550, 0, 200),
    NamedPosition("Kitchen", "de_mirage", -2000, 150, 0, 200),
    NamedPosition("Van", "de_mirage", -850, -1950, 0, 150),
    NamedPosition("Ticket Booth", "de_mirage", -500, -2200, 0, 150),
    NamedPosition("Triple Box", "de_mirage", -80, -2000, 0, 150),
    NamedPosition("Firebox", "de_mirage", -450, -1850, 0, 150),
    NamedPosition("Stairs", "de_mirage", -600, -2080, 0, 150),
    # ===== de_inferno =====
    NamedPosition("A Site", "de_inferno", 2160, 300, 0, 400),
    NamedPosition("B Site", "de_inferno", 125, 2900, 0, 350),
    NamedPosition("Banana", "de_inferno", 370, 1270, 0, 300),
    NamedPosition("Mid", "de_inferno", 1450, 640, 0, 300),
    NamedPosition("Apartments", "de_inferno", 730, -150, 0, 300),
    NamedPosition("Pit", "de_inferno", 2340, -260, 0, 200),
    NamedPosition("Library", "de_inferno", 1920, 720, 0, 200),
    NamedPosition("CT Spawn", "de_inferno", 2500, 800, 0, 250),
    NamedPosition("T Spawn", "de_inferno", -900, -400, 0, 300),
    NamedPosition("Arch", "de_inferno", 1750, 320, 0, 200),
    NamedPosition("Boiler", "de_inferno", 1200, -100, 0, 150),
    NamedPosition("Dark", "de_inferno", 450, 2600, 0, 200),
    NamedPosition("Construction", "de_inferno", -100, 2550, 0, 250),
    NamedPosition("Graveyard", "de_inferno", 2100, 550, 0, 200),
    NamedPosition("Balcony", "de_inferno", 2300, 200, 0, 150),
    NamedPosition("Second Mid", "de_inferno", 400, 640, 0, 250),
    NamedPosition("Top Banana", "de_inferno", 370, 750, 0, 200),
    NamedPosition("Bottom Banana", "de_inferno", 350, 1800, 0, 200),
    NamedPosition("Car", "de_inferno", 450, 1600, 0, 150),
    NamedPosition("Coffins", "de_inferno", 2050, -50, 0, 150),
    NamedPosition("Moto", "de_inferno", 1500, 100, 0, 150),
    # ===== de_dust2 =====
    NamedPosition("A Site", "de_dust2", 1230, 2500, 0, 350),
    NamedPosition("B Site", "de_dust2", -1375, 2560, 0, 350),
    NamedPosition("Mid Doors", "de_dust2", -470, 1050, 0, 200),
    NamedPosition("Long A", "de_dust2", 1560, 620, 0, 400),
    NamedPosition("Short A (Catwalk)", "de_dust2", 380, 1800, 0, 300),
    NamedPosition("B Tunnels", "de_dust2", -975, 1050, 0, 300),
    NamedPosition("CT Spawn", "de_dust2", 420, 2870, 0, 250),
    NamedPosition("T Spawn", "de_dust2", -650, -430, 0, 300),
    NamedPosition("A Long Doors", "de_dust2", 1500, 250, 0, 250),
    NamedPosition("A Cross", "de_dust2", 620, 2350, 0, 200),
    NamedPosition("A Platform", "de_dust2", 950, 2700, 0, 200),
    NamedPosition("Goose", "de_dust2", 1050, 2800, 0, 150),
    NamedPosition("Pit", "de_dust2", 1600, 2900, 0, 200),
    NamedPosition("Car", "de_dust2", 660, 2600, 0, 150),
    NamedPosition("B Window", "de_dust2", -1550, 2100, 0, 200),
    NamedPosition("B Closet", "de_dust2", -1600, 2750, 0, 150),
    NamedPosition("B Back Site", "de_dust2", -1200, 2850, 0, 200),
    NamedPosition("Upper Tunnels", "de_dust2", -1100, 600, 0, 250),
    NamedPosition("Lower Tunnels", "de_dust2", -1600, 1200, 0, 250),
    NamedPosition("T Mid", "de_dust2", -300, 250, 0, 200),
    NamedPosition("Xbox", "de_dust2", -50, 1350, 0, 150),
    NamedPosition("Palm", "de_dust2", -550, 1500, 0, 200),
    # ===== de_anubis =====
    NamedPosition("A Site", "de_anubis", -640, -680, 0, 350),
    NamedPosition("B Site", "de_anubis", 690, 1390, 0, 350),
    NamedPosition("Mid", "de_anubis", -200, 360, 0, 350),
    NamedPosition("Canal", "de_anubis", 560, -100, 0, 300),
    NamedPosition("CT Spawn", "de_anubis", 450, 500, 0, 250),
    NamedPosition("T Spawn", "de_anubis", -1400, 600, 0, 300),
    NamedPosition("A Main", "de_anubis", -900, -300, 0, 250),
    NamedPosition("B Main", "de_anubis", 200, 1100, 0, 250),
    NamedPosition("Connector", "de_anubis", 100, 200, 0, 250),
    NamedPosition("A Long", "de_anubis", -300, -1100, 0, 250),
    NamedPosition("Palace", "de_anubis", -650, -250, 0, 200),
    NamedPosition("Bridge", "de_anubis", -200, -50, 0, 200),
    NamedPosition("Water", "de_anubis", 500, 600, 0, 250),
    NamedPosition("Ruins", "de_anubis", 900, 1000, 0, 200),
    NamedPosition("Alley", "de_anubis", -1000, 300, 0, 200),
    # ===== de_nuke =====
    NamedPosition("A Site (Upper)", "de_nuke", -370, -720, -400, 400, "upper"),
    NamedPosition("B Site (Lower)", "de_nuke", 475, -750, -750, 400, "lower"),
    NamedPosition("Ramp", "de_nuke", 410, -1170, -400, 300),
    NamedPosition("Outside", "de_nuke", -1900, -760, -400, 500),
    NamedPosition("Secret", "de_nuke", 510, -400, -750, 250, "lower"),
    NamedPosition("Heaven", "de_nuke", -550, -850, -350, 200, "upper"),
    NamedPosition("Hell", "de_nuke", -250, -550, -400, 200, "upper"),
    NamedPosition("Vent", "de_nuke", 200, -600, -600, 200),
    NamedPosition("Lobby", "de_nuke", 500, -1350, -400, 250),
    NamedPosition("Radio", "de_nuke", -600, -1100, -400, 200, "upper"),
    NamedPosition("Hut", "de_nuke", -550, -600, -400, 150, "upper"),
    NamedPosition("Garage", "de_nuke", -1500, -1150, -400, 250),
    NamedPosition("T Roof", "de_nuke", -1800, -400, -300, 250),
    NamedPosition("CT Spawn", "de_nuke", 100, -1400, -400, 250),
    NamedPosition("T Spawn", "de_nuke", -1400, 0, -400, 300),
    NamedPosition("Squeaky", "de_nuke", -200, -900, -400, 150, "upper"),
    NamedPosition("Main", "de_nuke", -900, -650, -400, 250, "upper"),
    NamedPosition("Mini", "de_nuke", -130, -580, -400, 150, "upper"),
    NamedPosition("Decon", "de_nuke", 600, -600, -750, 200, "lower"),
    # ===== de_ancient =====
    NamedPosition("A Site", "de_ancient", -340, -200, 0, 350),
    NamedPosition("B Site", "de_ancient", 1090, 1460, 0, 350),
    NamedPosition("Mid", "de_ancient", 270, 560, 0, 350),
    NamedPosition("Donut", "de_ancient", -350, 400, 0, 200),
    NamedPosition("CT Spawn", "de_ancient", 600, 850, 0, 250),
    NamedPosition("T Spawn", "de_ancient", -1200, 300, 0, 300),
    NamedPosition("A Main", "de_ancient", -750, -200, 0, 250),
    NamedPosition("B Ramp", "de_ancient", 750, 1200, 0, 250),
    NamedPosition("Cave", "de_ancient", -100, 100, 0, 200),
    NamedPosition("Temple", "de_ancient", 100, -100, 0, 200),
    NamedPosition("Elbow", "de_ancient", 500, 300, 0, 200),
    NamedPosition("Tunnel", "de_ancient", -650, 500, 0, 200),
    NamedPosition("Water", "de_ancient", 900, 600, 0, 200),
    NamedPosition("Jaguar", "de_ancient", -200, -400, 0, 150),
    # ===== de_overpass =====
    NamedPosition("A Site", "de_overpass", -2100, 200, 0, 400),
    NamedPosition("B Site", "de_overpass", -1900, -600, 0, 350),
    NamedPosition("Connector", "de_overpass", -2600, -300, 0, 300),
    NamedPosition("Bathrooms", "de_overpass", -1400, -350, 0, 250),
    NamedPosition("Monster", "de_overpass", -2200, -1100, 0, 300),
    NamedPosition("Playground", "de_overpass", -2700, 400, 0, 250),
    NamedPosition("Bank", "de_overpass", -1600, 400, 0, 200),
    NamedPosition("Fountain", "de_overpass", -2200, 700, 0, 250),
    NamedPosition("CT Spawn", "de_overpass", -1600, 100, 0, 250),
    NamedPosition("T Spawn", "de_overpass", -3200, -100, 0, 300),
    NamedPosition("Party", "de_overpass", -2550, 200, 0, 200),
    NamedPosition("Tunnels", "de_overpass", -2000, -950, 0, 250),
    NamedPosition("Short", "de_overpass", -1700, -200, 0, 200),
    NamedPosition("Long", "de_overpass", -2800, -500, 0, 250),
    NamedPosition("Water", "de_overpass", -2100, -800, -200, 250),
    NamedPosition("Heaven", "de_overpass", -2300, 400, 100, 200),
    NamedPosition("Trash", "de_overpass", -1800, -750, 0, 150),
    NamedPosition("Graffiti", "de_overpass", -1950, -400, 0, 150),
    # ===== de_vertigo =====
    NamedPosition("A Site", "de_vertigo", -700, -500, 11900, 350, "upper"),
    NamedPosition("B Site", "de_vertigo", -1700, -450, 11900, 350, "upper"),
    NamedPosition("Mid", "de_vertigo", -1200, -100, 11900, 300, "upper"),
    NamedPosition("Ramp", "de_vertigo", -1500, -700, 11900, 250, "upper"),
    NamedPosition("Scaffolding", "de_vertigo", -1100, 100, 11500, 300, "lower"),
    NamedPosition("Lower B", "de_vertigo", -1700, -200, 11500, 300, "lower"),
    NamedPosition("CT Spawn", "de_vertigo", -1100, -650, 11900, 250, "upper"),
    NamedPosition("T Spawn", "de_vertigo", -500, 300, 11900, 300, "upper"),
    NamedPosition("A Stairs", "de_vertigo", -500, -300, 11700, 200),
    NamedPosition("B Stairs", "de_vertigo", -1600, -100, 11700, 200),
    NamedPosition("Elevator", "de_vertigo", -900, -400, 11700, 200),
    NamedPosition("Generator", "de_vertigo", -1400, -600, 11900, 200, "upper"),
    # ===== de_train =====
    NamedPosition("A Site", "de_train", -400, 1100, 0, 400),
    NamedPosition("B Site", "de_train", -200, -100, 0, 350),
    NamedPosition("Ivy", "de_train", -800, 400, 0, 300),
    NamedPosition("Connector", "de_train", 100, 500, 0, 250),
    NamedPosition("Upper B Hall", "de_train", 200, -350, 0, 250),
    NamedPosition("T Main", "de_train", -1100, -100, 0, 300),
    NamedPosition("Old Bomb", "de_train", -650, 850, 0, 250),
    NamedPosition("CT Spawn", "de_train", 400, 600, 0, 250),
    NamedPosition("T Spawn", "de_train", -1400, 200, 0, 300),
    NamedPosition("Ladder", "de_train", -300, 200, 0, 200),
    NamedPosition("Showers", "de_train", 300, 0, 0, 200),
    NamedPosition("Brown Halls", "de_train", -100, -400, 0, 200),
    NamedPosition("Z Connector", "de_train", -550, 300, 0, 200),
    NamedPosition("Pop Dog", "de_train", -200, 700, 0, 150),
    NamedPosition("Heaven", "de_train", 200, 1000, 100, 200),
    NamedPosition("Hell", "de_train", 0, 1100, -50, 150),
]

# Total: ~160 callout positions across 9 maps


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class NamedPositionRegistry:
    """
    Registry of known map callout positions.

    Supports lookup by proximity: given a world position, finds the nearest
    named position within a configurable radius.
    """

    def __init__(self):
        self._positions: List[NamedPosition] = list(_NAMED_POSITIONS)
        self._by_map: Dict[str, List[NamedPosition]] = {}
        self._rebuild_index()
        self._load_json_extensions()

    def _rebuild_index(self):
        self._by_map.clear()
        for pos in self._positions:
            self._by_map.setdefault(pos.map_name, []).append(pos)

    def _load_json_extensions(self):
        """Auto-load additional callouts from data/map_callouts.json if present."""
        json_path = _DATA_DIR / "map_callouts.json"
        if json_path.exists():
            self.load_from_json(json_path)

    def get_positions(self, map_name: str) -> List[NamedPosition]:
        """Get all named positions for a map."""
        return self._by_map.get(map_name, [])

    def find_nearest(
        self,
        map_name: str,
        x: float,
        y: float,
        z: float = 0.0,
        max_distance: float = 600.0,
    ) -> Optional[NamedPosition]:
        """
        Find the nearest named position to a world coordinate.

        Args:
            map_name: Map identifier (e.g., "de_mirage").
            x, y, z: World coordinates.
            max_distance: Maximum search radius in world units.

        Returns:
            Nearest NamedPosition within max_distance, or None.
        """
        candidates = self._by_map.get(map_name, [])
        if not candidates:
            return None

        best = None
        best_dist = max_distance

        for pos in candidates:
            dist = math.sqrt(
                (x - pos.center_x) ** 2 + (y - pos.center_y) ** 2 + (z - pos.center_z) ** 2
            )
            if dist < best_dist:
                best_dist = dist
                best = pos

        return best

    def add_position(self, position: NamedPosition):
        """Add a new named position to the registry."""
        self._positions.append(position)
        self._rebuild_index()

    def load_from_json(self, json_path: Path) -> int:
        """
        Load additional named positions from a JSON file.

        Returns:
            Number of positions loaded.
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            for entry in data:
                pos = NamedPosition(
                    name=entry["name"],
                    map_name=entry["map_name"],
                    center_x=entry["center_x"],
                    center_y=entry["center_y"],
                    center_z=entry.get("center_z", 0.0),
                    radius=entry.get("radius", 300.0),
                    level=entry.get("level", "default"),
                )
                self._positions.append(pos)
                count += 1
            self._rebuild_index()
            logger.info("Loaded %d named positions from %s", count, json_path)
            return count
        except Exception as e:
            logger.warning("Failed to load named positions from %s: %s", json_path, e)
            return 0


# ---------------------------------------------------------------------------
# Module-level singleton and convenience API
# ---------------------------------------------------------------------------

_registry: Optional[NamedPositionRegistry] = None


def get_callout_registry() -> NamedPositionRegistry:
    """Get or create the singleton NamedPositionRegistry."""
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = NamedPositionRegistry()
    return _registry


def get_callout(
    map_name: str,
    x: float,
    y: float,
    z: float = 0.0,
    max_distance: float = 600.0,
) -> str:
    """
    Translate a world coordinate to a human-readable callout name.

    Args:
        map_name: Map identifier (e.g., "de_mirage").
        x, y, z: World coordinates.
        max_distance: Maximum search radius in world units.

    Returns:
        Callout name (e.g., "A Site", "Jungle") or "unknown area" if no
        named position is within range.
    """
    registry = get_callout_registry()
    pos = registry.find_nearest(map_name, x, y, z, max_distance)
    if pos is not None:
        return pos.name
    return "unknown area"
