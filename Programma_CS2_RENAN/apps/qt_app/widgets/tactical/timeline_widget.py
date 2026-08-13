"""Interactive timeline scrubber with event markers, round dividers, and
chronovisor star markers (frame 13).

Stars are 5-point QPainterPath glyphs at each critical moment's peak tick;
clicking one seeks to the moment's start tick. A mono `t={tick}` caption
tracks the playhead in the strip above the bar.
"""

import math
from typing import Callable, List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.core.demo_frame import EventType, GameEvent

# Bar geometry: caption strip above + 32px scrub bar (frame 13).
_BAR_HEIGHT = 32
_CAPTION_STRIP = 16
_STAR_OUTER_R = 7.0
_STAR_HIT_RADIUS = 9.0


def _with_alpha(color: QColor, alpha: int) -> QColor:
    """Return a copy of ``color`` with the given 0-255 alpha."""
    c = QColor(color)
    c.setAlpha(alpha)
    return c


def _star_path(cx: float, cy: float, outer_r: float) -> QPainterPath:
    """5-point star centered at (cx, cy), point up."""
    path = QPainterPath()
    inner_r = outer_r * 0.45
    for i in range(10):
        radius = outer_r if i % 2 == 0 else inner_r
        angle = -math.pi / 2 + i * math.pi / 5
        point = QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
        if i == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


class TimelineWidget(QWidget):
    """QPainter-based timeline with event/star markers and seek interaction."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_tick = 0
        self._max_tick = 0
        self._game_events: List[GameEvent] = []
        self._round_marks: List[int] = []
        self._star_marks: List[tuple[int, int]] = []  # (peak_tick, seek_tick)
        self._seek_callback: Optional[Callable[[int], None]] = None

        self.setFixedHeight(_BAR_HEIGHT + _CAPTION_STRIP)
        self.setMouseTracking(False)

    def _palette(self) -> dict[str, QColor]:
        """Token-derived paint palette, refreshed each paintEvent.

        Reading get_tokens() per paint keeps the timeline theme-tracking.
        Marker alphas (204) mirror the retired module constants.
        """
        t = get_tokens()
        return {
            "bg": QColor(t.surface_sunken),
            "progress": _with_alpha(QColor(t.accent_primary), 64),
            "playhead": QColor(t.accent_primary),
            "round_mark": QColor(t.chart_axis),
            "star": QColor(t.warning),
            "kill": _with_alpha(QColor(t.error), 204),
            "plant": _with_alpha(QColor(t.warning), 204),
            "defuse": _with_alpha(QColor(t.info), 204),
            "empty_text": _with_alpha(QColor(t.text_secondary), 204),
        }

    # ── Public API ──

    @property
    def current_tick(self) -> int:
        return self._current_tick

    @current_tick.setter
    def current_tick(self, value: int):
        if self._current_tick != value:
            self._current_tick = value
            self.update()

    @property
    def max_tick(self) -> int:
        return self._max_tick

    @max_tick.setter
    def max_tick(self, value: int):
        self._max_tick = value
        self.update()

    def set_events(self, events: List[GameEvent]):
        self._game_events = events
        self.update()

    def set_round_marks(self, ticks: List[int]):
        """Round-boundary dividers (frame 13) — start tick per round."""
        self._round_marks = sorted(int(t) for t in ticks or [])
        self.update()

    def set_critical_moments(self, moments: List) -> None:
        """Star markers from ChronovisorScanner moments.

        Accepts scanner objects (``peak_tick``/``start_tick``) or dicts with
        the same keys; anything unreadable is skipped.
        """
        marks: list[tuple[int, int]] = []
        for m in moments or []:
            getter = m.get if isinstance(m, dict) else lambda k, _m=m: getattr(_m, k, None)
            peak = getter("peak_tick")
            start = getter("start_tick")
            if peak is None and start is None:
                continue
            peak = int(peak if peak is not None else start)
            start = int(start if start is not None else peak)
            marks.append((peak, start))
        self._star_marks = sorted(marks)
        self.update()

    def set_seek_callback(self, callback: Callable[[int], None]):
        self._seek_callback = callback

    def star_hit_test(self, x: float, y: float) -> Optional[int]:
        """Seek tick of the star under (x, y), else None. Used by
        mousePressEvent and directly by tests."""
        if self._max_tick <= 0 or self.width() <= 0 or y < _CAPTION_STRIP:
            return None
        for peak, start in self._star_marks:
            star_x = (peak / self._max_tick) * self.width()
            if abs(x - star_x) <= _STAR_HIT_RADIUS:
                return start
        return None

    # ── Paint ──

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        bar_top = h - _BAR_HEIGHT
        pal = self._palette()

        # Background (bar strip only — caption strip stays transparent)
        p.fillRect(QRectF(0, bar_top, w, _BAR_HEIGHT), pal["bg"])

        if self._max_tick <= 0:
            # Empty state
            p.setPen(pal["empty_text"])
            p.setFont(Typography.font("body"))
            p.drawText(
                QRectF(0, bar_top, w, _BAR_HEIGHT),
                Qt.AlignCenter,
                i18n.get_text("tactical.timeline_empty", "Load a demo to enable timeline"),
            )
            p.end()
            return

        ratio = max(0.0, min(1.0, self._current_tick / self._max_tick))
        playhead_x = w * ratio

        # Progress fill (muted accent) up to the playhead
        p.fillRect(QRectF(0, bar_top, playhead_x, _BAR_HEIGHT), pal["progress"])

        # Round-boundary dividers
        for tick in self._round_marks:
            if 0 < tick < self._max_tick:
                x = (tick / self._max_tick) * w
                p.fillRect(QRectF(x, bar_top + 4, 2, _BAR_HEIGHT - 8), pal["round_mark"])

        # Event markers
        for evt in self._game_events:
            if evt.event_type == EventType.KILL:
                p.fillRect(self._marker_rect(evt, w, bar_top, 0.5), pal["kill"])
            elif evt.event_type == EventType.BOMB_PLANT:
                p.fillRect(self._marker_rect(evt, w, bar_top, 1.0), pal["plant"])
            elif evt.event_type == EventType.BOMB_DEFUSE:
                p.fillRect(self._marker_rect(evt, w, bar_top, 1.0), pal["defuse"])

        # Chronovisor stars
        if self._star_marks:
            p.setPen(Qt.NoPen)
            p.setBrush(pal["star"])
            cy = bar_top + _BAR_HEIGHT / 2
            for peak, _start in self._star_marks:
                if 0 <= peak <= self._max_tick:
                    p.drawPath(_star_path((peak / self._max_tick) * w, cy, _STAR_OUTER_R))

        # Playhead line + mono `t={tick}` caption above it
        p.fillRect(QRectF(playhead_x - 1, bar_top, 2, _BAR_HEIGHT), pal["playhead"])
        caption = f"t={self._current_tick:,}"
        font = Typography.font("mono")
        font.setPointSize(get_tokens().font_size_caption)
        p.setFont(font)
        p.setPen(pal["playhead"])
        fm = p.fontMetrics()
        text_w = fm.horizontalAdvance(caption)
        text_x = max(0.0, min(w - text_w, playhead_x - text_w / 2))
        p.drawText(QPointF(text_x, bar_top - (_CAPTION_STRIP - fm.ascent()) / 2 - 1), caption)

        p.end()

    def _marker_rect(self, evt: GameEvent, w: float, bar_top: float, h_factor: float) -> QRectF:
        evt_x = (evt.tick / self._max_tick) * w
        return QRectF(evt_x, bar_top, 2, _BAR_HEIGHT * h_factor)

    # ── Mouse Handling ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            star_seek = self.star_hit_test(event.position().x(), event.position().y())
            if star_seek is not None:
                if self._seek_callback:
                    self._seek_callback(star_seek)
                return
            self._handle_seek(event.position().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._handle_seek(event.position().x())

    def _handle_seek(self, x: float):
        if self._max_tick <= 0 or self.width() <= 0:
            return
        ratio = max(0.0, min(1.0, x / self.width()))
        target_tick = int(ratio * self._max_tick)
        if self._seek_callback:
            self._seek_callback(target_tick)
