"""MiniSparkline — chrome-less line chart for at-a-glance trend rendering.

Unlike ``RatingSparkline`` (QChartView with axes, title, and reference
lines, sized for the Performance screen), this is a true sparkline:
QPainter-based, ~60px tall, no labels, no axes. Used in dashboard
hero cards where you want trend-shape only, not exact values.

API:
    spark = MiniSparkline()
    spark.set_values([1.05, 1.12, 0.98, 1.21, 1.34])

Empty input renders an empty surface (still safe to call ``set_values([])``).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class MiniSparkline(QWidget):
    """Lightweight sparkline — paints a line + gradient fill from a value list."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._values: list[float] = []
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_values(self, values: list[float]) -> None:
        self._values = [float(v) for v in values if v is not None]
        self.update()

    def paintEvent(self, event):  # noqa: ARG002 — Qt requires this signature
        if not self._values:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        tokens = get_tokens()
        accent = QColor(tokens.chart_line_primary)

        rect = self.rect().adjusted(2, 4, -2, -4)
        n = len(self._values)
        if n == 1:
            # Single point — render a horizontal stub at mid-height
            mid_y = rect.center().y()
            pen = QPen(accent, 2)
            painter.setPen(pen)
            painter.drawLine(rect.left(), mid_y, rect.right(), mid_y)
            return

        v_min = min(self._values)
        v_max = max(self._values)
        v_span = v_max - v_min
        if v_span < 1e-6:
            v_span = 1.0  # avoid div-by-zero on flat data

        def to_point(i: int, v: float) -> QPointF:
            x = rect.left() + (rect.width() * i / max(1, n - 1))
            # Invert y because Qt's y axis goes down
            y = rect.bottom() - ((v - v_min) / v_span) * rect.height()
            return QPointF(x, y)

        # Build line + closed area path
        line_path = QPainterPath()
        line_path.moveTo(to_point(0, self._values[0]))
        for i in range(1, n):
            line_path.lineTo(to_point(i, self._values[i]))

        area_path = QPainterPath(line_path)
        area_path.lineTo(QPointF(rect.right(), rect.bottom()))
        area_path.lineTo(QPointF(rect.left(), rect.bottom()))
        area_path.closeSubpath()

        # Gradient fill — accent at top, transparent at bottom
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        fill_top = QColor(accent)
        fill_top.setAlphaF(0.30)
        fill_bot = QColor(accent)
        fill_bot.setAlphaF(0.0)
        gradient.setColorAt(0.0, fill_top)
        gradient.setColorAt(1.0, fill_bot)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(area_path)

        # Line
        line_pen = QPen(accent, 2)
        line_pen.setJoinStyle(Qt.RoundJoin)
        line_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(line_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(line_path)

        # End-point dot — anchors the trend's "now" position
        end_pt = to_point(n - 1, self._values[-1])
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(end_pt, 3.0, 3.0)
