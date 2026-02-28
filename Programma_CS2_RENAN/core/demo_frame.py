"""
demo_frame.py
Data models for representing a single frame (tick) of a CS2 demo.

These dataclasses provide a clean, typed representation of game state
that the PlaybackEngine will interpolate between.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Team(Enum):
    """Player team enum."""

    CT = "ct"
    T = "t"
    SPECTATOR = "spectator"


@dataclass
class PlayerState:
    """Represents a player's state at a single tick."""

    player_id: int
    name: str
    team: Team
    x: float  # World X
    y: float  # World Y
    z: float  # World Z (for vertical maps like Nuke)
    yaw: float  # View angle (0-360)
    hp: int  # Health points (0-100)
    armor: int
    is_alive: bool
    is_flashed: bool
    has_defuser: bool
    weapon: str  # Current weapon name
    money: int
    # Stats for HUD
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    mvps: int = 0
    inventory: List[str] = field(default_factory=list)
    is_crouching: bool = False
    is_scoped: bool = False
    equipment_value: int = 0


@dataclass
class GhostState:
    """Represents a selectable/draggable previous-round shadow."""

    player_id: int
    name: str
    team: str
    x: float
    y: float
    yaw: float
    is_paused: bool = False
    manual_offset_x: float = 0.0
    manual_offset_y: float = 0.0


class NadeType(str, Enum):
    SMOKE = "smoke"
    MOLOTOV = "molotov"
    FLASH = "flash"
    HE = "he"
    DECOY = "decoy"


@dataclass(frozen=True)
class NadeState:
    """Represents an active grenade projectile or effect."""

    base_id: int  # Entity ID
    nade_type: NadeType
    x: float
    y: float
    z: float
    # For rendering:
    starting_tick: int  # Detonation/Effect Start
    ending_tick: int  # Effect End
    throw_tick: Optional[int] = None
    trajectory: List[tuple[float, float, float]] = field(default_factory=list)
    thrower_id: Optional[int] = None


class EventType(str, Enum):
    KILL = "kill"
    BOMB_PLANT = "plant"
    BOMB_DEFUSE = "defuse"
    ROUND_START = "round_start"
    ROUND_END = "round_end"


@dataclass(frozen=True)
class GameEvent:
    tick: int
    event_type: EventType
    x: float = 0.0  # World Coordinates
    y: float = 0.0
    details: str = ""  # e.g. "S1mple -> Zywoo (AK-47)"


@dataclass
class BombState:
    """Represents the bomb state."""

    x: float
    y: float
    z: float
    is_planted: bool
    is_defused: bool
    time_remaining: Optional[float] = None  # Seconds until detonation


@dataclass
class KillEvent:
    """Represents a kill that occurred during this tick."""

    killer_id: int
    victim_id: int
    weapon: str
    is_headshot: bool
    is_wallbang: bool


@dataclass
class DemoFrame:
    """
    A single snapshot of the game state at a specific tick.
    This is the primary data structure used by the PlaybackEngine.
    """

    tick: int
    round_number: int
    time_in_round: float  # Seconds since round start
    map_name: str
    players: List[PlayerState] = field(default_factory=list)
    nades: List[NadeState] = field(default_factory=list)
    bomb: Optional[BombState] = None
    kills: List[KillEvent] = field(default_factory=list)

    # Metadata for timeline events
    is_round_start: bool = False
    is_round_end: bool = False
    is_bomb_plant: bool = False
