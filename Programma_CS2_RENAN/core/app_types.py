from enum import Enum, auto
from typing import Any, Dict, List, NewType, Optional, Tuple, TypedDict

MatchID = NewType("MatchID", int)
Tick = NewType("Tick", int)
PlayerID = NewType("PlayerID", int)


class Team(Enum):
    """Numeric team identifiers for internal processing.

    Note: demo_frame.py defines a separate Team enum with string values
    ("ct", "t", "spectator") for demo-parser compatibility. Import the correct
    enum for your context: use this one for DB/UI, demo_frame.Team for parser data.
    """

    SPECTATOR = 0
    T = 1
    CT = 2


class PlayerRole(str, Enum):
    """Canonical CS2 player role classification (P3-01).

    Single source of truth — imported by role_features.py, role_classifier.py,
    and all downstream consumers.  Values are lowercase identifiers suitable
    for serialisation, DB storage, and cross-module comparison.
    """

    ENTRY = "entry"
    AWPER = "awper"
    SUPPORT = "support"
    LURKER = "lurker"
    IGL = "igl"
    FLEX = "flex"
    UNKNOWN = "unknown"

    @property
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        _DISPLAY = {
            "entry": "Entry Fragger",
            "awper": "AWPer",
            "support": "Support",
            "lurker": "Lurker",
            "igl": "IGL",
            "flex": "Flex",
            "unknown": "Unknown",
        }
        return _DISPLAY.get(self.value, self.value.title())


class IngestionStatus(Enum):
    QUEUED = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()


class DemoMetadata(TypedDict):
    demo_name: str
    map_name: str
    tick_rate: float
    total_ticks: int
    processed_at: str
    is_pro: bool
    last_tick_processed: int


class PlayerStats(TypedDict):
    name: str
    kills: int
    deaths: int
    adr: float
    hs_percent: float
    kast: float
    rating: float
