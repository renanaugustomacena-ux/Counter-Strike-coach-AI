"""QWebChannel host — bridges Python coaching state to web marquee apps.

The marquee screens (tactical viewer, match detail, coach chat) load a
React + D3 / Three.js app inside a ``QWebEngineView``. The web side needs
to observe Python state (current tick, frame payloads, coach output)
and to invoke Python slots (seek, player select, ghost-AI request).

This bridge exposes a single ``MarqueeBridge(QObject)`` that a host
screen can instantiate, register on its ``QWebChannel``, then feed via
its existing ViewModel signals. The TypeScript side (`web/shared/
qwebchannel.ts`) provides a typed wrapper so the JS calls read the same
way as a Python method call.

Why one class, not per-screen subclasses:
    The payloads are small and shape-identical across marquee screens
    (tick + JSON frame). A single bridge keeps the TS typings tiny and
    makes the web shared module reusable. If a marquee surface grows
    its own semantic surface (e.g. coach chat needs streaming deltas),
    subclass here rather than fork — preserves the wire protocol.
"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.qt_web_bridge")


class MarqueeBridge(QObject):
    """Python-side endpoint for a marquee web app.

    Properties (observable from JS via QWebChannel property change):
        current_tick (int)
        frame_payload (str — JSON blob of player / nade / event state)
        coach_state (str — JSON blob of belief / momentum / skill axes)
        ready (bool — set True once Python has emitted first frame)

    Signals (JS subscribes via channel.objects.<name>.<signal>.connect):
        tick_changed(int)
        frame_ready(str)
        coach_state_changed(str)

    Slots (JS calls channel.objects.<name>.<slot>(args)):
        seek_to_tick(tick: int)
        select_player(player_id: int)
        request_ghost(tick: int) -> str  (JSON)
        log(level: str, message: str)     (web-side console bridge)
    """

    tick_changed = Signal(int)
    frame_ready = Signal(str)
    coach_state_changed = Signal(str)
    ready_changed = Signal(bool)
    map_name_changed = Signal(str)
    segments_ready = Signal(str)  # JSON: {round_name: start_tick}
    events_ready = Signal(str)  # JSON: [{tick, kind, ...}]
    ghost_ready = Signal(str)  # JSON: [{x, y, team, name}]

    # Emitted when a user interacts with the web UI — host screen
    # subscribes and forwards to the playback ViewModel.
    seek_requested = Signal(int)
    player_selected = Signal(int)
    ghost_requested = Signal(int)

    def __init__(self, name: str = "bridge", parent: QObject | None = None):
        super().__init__(parent)
        self._name = name
        self._current_tick: int = 0
        self._frame_payload: str = "{}"
        self._coach_state: str = "{}"
        self._ready: bool = False
        self._map_name: str = ""
        self._segments: str = "{}"
        self._events: str = "[]"
        self._ghost: str = "[]"

    # ── Python-side setters (call these from the host screen's VM signals) ──

    def publish_tick(self, tick: int) -> None:
        if tick == self._current_tick:
            return
        self._current_tick = int(tick)
        self.tick_changed.emit(self._current_tick)

    def publish_frame(self, frame: dict[str, Any]) -> None:
        """Emit a frame payload. ``frame`` is serialized to JSON once here."""
        try:
            payload = json.dumps(frame, separators=(",", ":"), default=str)
        except (TypeError, ValueError) as exc:
            _logger.warning("MarqueeBridge[%s]: frame serialize failed: %s", self._name, exc)
            return
        self._frame_payload = payload
        self.frame_ready.emit(payload)
        if not self._ready:
            self._ready = True
            self.ready_changed.emit(True)

    def publish_coach_state(self, coach: dict[str, Any]) -> None:
        try:
            payload = json.dumps(coach, separators=(",", ":"), default=str)
        except (TypeError, ValueError) as exc:
            _logger.warning(
                "MarqueeBridge[%s]: coach_state serialize failed: %s",
                self._name,
                exc,
            )
            return
        self._coach_state = payload
        self.coach_state_changed.emit(payload)

    def publish_map(self, map_name: str) -> None:
        """Tell the web side which radar image to load."""
        if map_name == self._map_name:
            return
        self._map_name = map_name
        self.map_name_changed.emit(map_name)

    def publish_segments(self, segments: dict[str, int]) -> None:
        """Publish round boundaries — dict of round_name -> start_tick."""
        try:
            payload = json.dumps(segments, separators=(",", ":"), default=str)
        except (TypeError, ValueError) as exc:
            _logger.warning(
                "MarqueeBridge[%s]: segments serialize failed: %s",
                self._name,
                exc,
            )
            return
        self._segments = payload
        self.segments_ready.emit(payload)

    def publish_events(self, events: list[dict[str, Any]]) -> None:
        """Publish tick-indexed events (kills, plants, defuses) for the timeline."""
        try:
            payload = json.dumps(events, separators=(",", ":"), default=str)
        except (TypeError, ValueError) as exc:
            _logger.warning(
                "MarqueeBridge[%s]: events serialize failed: %s",
                self._name,
                exc,
            )
            return
        self._events = payload
        self.events_ready.emit(payload)

    def publish_ghost(self, ghosts: list[dict[str, Any]]) -> None:
        """Publish ghost-AI predicted positions for the current tick."""
        try:
            payload = json.dumps(ghosts, separators=(",", ":"), default=str)
        except (TypeError, ValueError) as exc:
            _logger.warning(
                "MarqueeBridge[%s]: ghost serialize failed: %s",
                self._name,
                exc,
            )
            return
        self._ghost = payload
        self.ghost_ready.emit(payload)

    # ── Q_PROPERTIES (observable by the JS side) ──

    def _get_current_tick(self) -> int:
        return self._current_tick

    current_tick = Property(int, _get_current_tick, notify=tick_changed)

    def _get_frame_payload(self) -> str:
        return self._frame_payload

    frame_payload = Property(str, _get_frame_payload, notify=frame_ready)

    def _get_coach_state(self) -> str:
        return self._coach_state

    coach_state = Property(str, _get_coach_state, notify=coach_state_changed)

    def _get_ready(self) -> bool:
        return self._ready

    ready = Property(bool, _get_ready, notify=ready_changed)

    def _get_map_name(self) -> str:
        return self._map_name

    map_name = Property(str, _get_map_name, notify=map_name_changed)

    def _get_segments(self) -> str:
        return self._segments

    segments = Property(str, _get_segments, notify=segments_ready)

    def _get_events(self) -> str:
        return self._events

    events = Property(str, _get_events, notify=events_ready)

    def _get_ghost(self) -> str:
        return self._ghost

    ghost = Property(str, _get_ghost, notify=ghost_ready)

    # ── Slots invoked from JS ──

    @Slot(int)
    def seek_to_tick(self, tick: int) -> None:
        """User dragged the timeline in the web app."""
        _logger.debug("MarqueeBridge[%s]: seek_to_tick(%d)", self._name, tick)
        self.seek_requested.emit(int(tick))

    @Slot(int)
    def select_player(self, player_id: int) -> None:
        _logger.debug("MarqueeBridge[%s]: select_player(%d)", self._name, player_id)
        self.player_selected.emit(int(player_id))

    @Slot(int)
    def request_ghost(self, tick: int) -> None:
        """Web asked for ghost-AI overlay at a specific tick."""
        _logger.debug("MarqueeBridge[%s]: request_ghost(%d)", self._name, tick)
        self.ghost_requested.emit(int(tick))

    @Slot(str, str)
    def log(self, level: str, message: str) -> None:
        """Web-side console bridge — route TS logs into the Python logger."""
        log_fn = {
            "debug": _logger.debug,
            "info": _logger.info,
            "warn": _logger.warning,
            "warning": _logger.warning,
            "error": _logger.error,
        }.get(level.lower(), _logger.info)
        log_fn("[web:%s] %s", self._name, message)
