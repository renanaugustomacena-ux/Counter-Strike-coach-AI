"""RadarChart — QPainter N-axis skill radar with dual-overlay support.

Frames 15/34: concentric polygon ring grid, spokes, one filled polygon per
series (25% alpha fill + 2px outline + vertex dots), axis labels outside
the outer ring. Legend is rendered by the parent screen, not the widget.

API:
    radar = RadarChart()
    radar.set_axes(["Aim", "Opening", ...])          # any N >= 3
    radar.add_series("ZywOo", [97, 88, ...], QColor(tokens.accent_primary))
    radar.add_series("donk", [96, 85, ...], QColor(tokens.info))
    radar.set_range(0.0, 100.0)                      # default
    radar.clear_series()

All chrome colors are read from ``get_tokens()`` inside ``paintEvent`` so
the widget repaints correctly after a theme switch. Series colors are
chosen by the caller (screen) from tokens.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.charts import token_color

_RINGS = 4  # concentric grid rings at 25/50/75/100%
_LABEL_GAP = 14.0  # px between outer ring and axis label anchor


def _vertex(cx: float, cy: float, r: float, idx: int, n: int, frac: float) -> tuple[float, float]:
    """Return the (x, y) of axis ``idx`` of ``n`` at ``frac`` of radius ``r``.

    Axis 0 points straight up; axes proceed clockwise (Qt y grows down).
    angle = -90° + idx * 360 / n.
    """
    angle = math.radians(-90.0 + idx * 360.0 / n)
    return (cx + r * frac * math.cos(angle), cy + r * frac * math.sin(angle))


class RadarChart(QWidget):
    """N-axis radar plot (N >= 3) with any number of overlaid series."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._axes: list[str] = []
        self._series: list[tuple[str, list[float], QColor]] = []
        self._lo: float = 0.0
        self._hi: float = 100.0
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ── API ──

    def set_axes(self, labels: list[str]) -> None:
        self._axes = [str(label) for label in labels]
        self.update()

    def add_series(self, name: str, values: list[float], color: QColor) -> None:
        self._series.append((name, [float(v) for v in values], QColor(color)))
        self.update()

    def clear_series(self) -> None:
        self._series = []
        self.update()

    def set_range(self, lo: float = 0.0, hi: float = 100.0) -> None:
        self._lo, self._hi = float(lo), float(hi)
        self.update()

    # ── Painting ──

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        n = len(self._axes)
        if n < 3:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = get_tokens()

        label_font = Typography.font("caption")
        fm = QFontMetricsF(label_font)
        # Horizontal margin must clear the widest label (caption role renders
        # uppercase — measure the uppercased text); vertical only its height.
        widest = max((fm.horizontalAdvance(t.upper()) for t in self._axes), default=0.0)
        h_margin = _LABEL_GAP + widest + 4
        v_margin = _LABEL_GAP + fm.height() + 4
        rect = self.rect()
        radius = min(rect.width() / 2.0 - h_margin, rect.height() / 2.0 - v_margin)
        if radius <= 8:
            return
        cx = rect.center().x()
        cy = rect.center().y()

        self._paint_grid(painter, tokens, cx, cy, radius, n)
        self._paint_series(painter, cx, cy, radius, n)
        self._paint_labels(painter, tokens, label_font, fm, cx, cy, radius, n)

    def _paint_grid(self, painter, tokens, cx, cy, radius, n) -> None:
        grid_pen = QPen(token_color(tokens.chart_grid), 1)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(grid_pen)
        for ring in range(1, _RINGS + 1):
            frac = ring / _RINGS
            poly = QPolygonF([QPointF(*_vertex(cx, cy, radius, i, n, frac)) for i in range(n)])
            painter.drawPolygon(poly)

        spoke_pen = QPen(token_color(tokens.chart_axis), 1)
        painter.setPen(spoke_pen)
        center = QPointF(cx, cy)
        for i in range(n):
            painter.drawLine(center, QPointF(*_vertex(cx, cy, radius, i, n, 1.0)))

    def _paint_series(self, painter, cx, cy, radius, n) -> None:
        span = self._hi - self._lo
        if span <= 0:
            span = 1.0
        for _name, values, color in self._series:
            points = []
            for i in range(n):
                value = values[i] if i < len(values) else self._lo
                frac = max(0.0, min(1.0, (value - self._lo) / span))
                points.append(QPointF(*_vertex(cx, cy, radius, i, n, frac)))
            poly = QPolygonF(points)

            fill = QColor(color)
            fill.setAlphaF(0.25)
            painter.setPen(QPen(color, 2))
            painter.setBrush(fill)
            painter.drawPolygon(poly)

            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            for point in points:
                painter.drawEllipse(point, 3.0, 3.0)

    def _paint_labels(self, painter, tokens, label_font, fm, cx, cy, radius, n) -> None:
        painter.setFont(label_font)
        painter.setPen(QColor(tokens.text_secondary))
        eps = 0.5
        for i, text in enumerate(self._axes):
            lx, ly = _vertex(cx, cy, radius + _LABEL_GAP, i, n, 1.0)
            dx, dy = lx - cx, ly - cy
            # Quadrant-aware anchoring: the label box grows away from the plot.
            if dx > eps:
                left, width, h_flag = lx, 300.0, Qt.AlignLeft
            elif dx < -eps:
                left, width, h_flag = lx - 300.0, 300.0, Qt.AlignRight
            else:
                left, width, h_flag = lx - 150.0, 300.0, Qt.AlignHCenter
            if dy < -eps:
                top, height, v_flag = ly - 2 * fm.height(), 2 * fm.height(), Qt.AlignBottom
            elif dy > eps:
                top, height, v_flag = ly, 2 * fm.height(), Qt.AlignTop
            else:
                top, height, v_flag = ly - fm.height(), 2 * fm.height(), Qt.AlignVCenter
            painter.drawText(QRectF(left, top, width, height), h_flag | v_flag, text)
