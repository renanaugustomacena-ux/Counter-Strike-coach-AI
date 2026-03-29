"""
playback_engine.py
Core logic for demo playback, including:
1. Managing playback time and speed.
2. Handling frame lookup and seeking.
3. Interpolating between frames for smooth animation.
4. Schedule updates via Kivy's Clock.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from Programma_CS2_RENAN.core.demo_frame import DemoFrame, NadeState, PlayerState, Team
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.playback_engine")


@dataclass
class InterpolatedPlayerState:
    """
    Result of interpolating between two frames for a single player.
    """

    player_id: int
    name: str
    team: Team
    x: float
    y: float
    z: float
    yaw: float
    hp: int
    armor: int
    is_alive: bool
    is_flashed: bool
    weapon: str
    money: int
    kills: int
    deaths: int
    assists: int
    mvps: int
    inventory: List[str] = field(default_factory=list)
    is_crouching: bool = False
    is_scoped: bool = False
    equipment_value: int = 0
    is_ghost: bool = False


@dataclass
class InterpolatedFrame:
    """
    A single frame ready for rendering by the UI.
    Contains interpolated positions for current tick.
    """

    tick: int
    players: List[InterpolatedPlayerState]
    nades: List[NadeState]


class PlaybackEngine:
    """
    Handles playback state and interpolation logic.
    """

    SPEED_NORMAL = 1.0

    def __init__(self):
        self._frames: List[DemoFrame] = []
        self._current_index: int = 0
        self._sub_tick: float = 0.0  # Normalized progress between current and next frame
        self._is_playing: bool = False
        self._speed: float = self.SPEED_NORMAL
        self._clock_event: Optional[object] = None
        self._on_frame_update: Optional[Callable[[InterpolatedFrame], None]] = None
        self._tick_rate: int = 64

    def load_frames(self, frames: List[DemoFrame], tick_rate: int = 64):
        self._frames = frames
        self._tick_rate = tick_rate
        self._current_index = 0
        self._sub_tick = 0.0
        self._ticks_cache = [f.tick for f in frames]
        logger.debug("Loaded %d frames.", len(frames))

    def set_on_frame_update(self, callback: Callable[[InterpolatedFrame], None]):
        self._on_frame_update = callback

    def play(self):
        if not self._is_playing and len(self._frames) > 0:
            # If at the end, loop back to start
            if self._current_index >= len(self._frames) - 1:
                self._current_index = 0
                self._sub_tick = 0.0

            self._is_playing = True
            # Update at ~60 FPS
            try:
                from kivy.clock import Clock

                self._clock_event = Clock.schedule_interval(self._tick, 1.0 / 60.0)
            except ImportError:
                logger.warning("Kivy not available — subclass must override play()")
                self._is_playing = False
                return
            logger.debug("Play")

    def pause(self):
        if self._is_playing:
            self._is_playing = False
            if self._clock_event:
                self._clock_event.cancel()
                self._clock_event = None
            logger.debug("Pause")

    def toggle_play_pause(self):
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def set_speed(self, speed: float):
        self._speed = max(0.25, min(speed, 8.0))

    def seek_to_tick(self, tick: int):
        if not self._frames:
            return

        # Binary search using cached ticks
        import bisect

        idx = bisect.bisect_left(self._ticks_cache, tick)

        if idx < len(self._frames):
            self._current_index = idx
        else:
            self._current_index = len(self._frames) - 1

        self._sub_tick = 0.0
        self._emit_frame()

    def get_current_tick(self) -> int:
        return self._frames[self._current_index].tick if self._frames else 0

    def get_total_ticks(self) -> int:
        return self._frames[-1].tick if self._frames else 0

    def is_playing(self) -> bool:
        return self._is_playing

    def _tick(self, dt):
        if not self._is_playing or not self._frames:
            return

        # Advance sub-tick based on real time delta and tick rate
        self._sub_tick += dt * self._tick_rate * self._speed

        # Advance frames if needed
        while self._sub_tick >= 1.0:
            if self._current_index < len(self._frames) - 1:
                self._current_index += 1
                self._sub_tick -= 1.0
            else:
                self._sub_tick = 0.0
                self.pause()
                break

        self._emit_frame()

    def _emit_frame(self):
        if not self._on_frame_update or not self._frames:
            return
        cf = self._frames[self._current_index]

        # Interpolation
        if self._current_index < len(self._frames) - 1:
            nf = self._frames[self._current_index + 1]
            players = self._interpolate_players(cf.players, nf.players, self._sub_tick)
        else:
            players = [self._player_to_interpolated(p) for p in cf.players]

        self._on_frame_update(InterpolatedFrame(cf.tick, players, cf.nades))

    def _interpolate_players(self, current, next_, t):
        res = []
        n_lookup = {p.player_id: p for p in next_}
        for p in current:
            if p.player_id in n_lookup:
                n = n_lookup[p.player_id]
                res.append(
                    InterpolatedPlayerState(
                        player_id=p.player_id,
                        name=p.name,
                        team=p.team,
                        x=p.x + (n.x - p.x) * t,
                        y=p.y + (n.y - p.y) * t,
                        z=p.z + (n.z - p.z) * t,
                        yaw=self._interpolate_angle(p.yaw, n.yaw, t),
                        hp=int(p.hp + (n.hp - p.hp) * t),
                        armor=p.armor,
                        is_alive=p.is_alive,
                        is_flashed=p.is_flashed or n.is_flashed,
                        is_crouching=p.is_crouching,
                        is_scoped=p.is_scoped,
                        equipment_value=p.equipment_value,
                        weapon=p.weapon,
                        money=p.money,
                        kills=p.kills,
                        deaths=p.deaths,
                        assists=p.assists,
                        mvps=p.mvps,
                        inventory=p.inventory,
                    )
                )
            else:
                res.append(self._player_to_interpolated(p))
        return res

    def _player_to_interpolated(self, p: PlayerState):
        return InterpolatedPlayerState(
            player_id=p.player_id,
            name=p.name,
            team=p.team,
            x=p.x,
            y=p.y,
            z=p.z,
            yaw=p.yaw,
            hp=p.hp,
            armor=p.armor,
            is_alive=p.is_alive,
            is_flashed=p.is_flashed,
            is_crouching=p.is_crouching,
            is_scoped=p.is_scoped,
            equipment_value=p.equipment_value,
            weapon=p.weapon,
            money=p.money,
            kills=p.kills,
            deaths=p.deaths,
            assists=p.assists,
            mvps=p.mvps,
            inventory=p.inventory,
        )

    @staticmethod
    def _interpolate_angle(a, b, t):
        # CORE-10: Sanitize NaN yaw — DF-01 covers x/y/z but not angles
        import math

        if math.isnan(a) or math.isnan(b):
            return b if not math.isnan(b) else (a if not math.isnan(a) else 0.0)
        diff = b - a
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        return a + diff * t
