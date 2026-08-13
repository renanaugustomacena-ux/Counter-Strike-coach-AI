"""RatingSparkline — rating trend line with HLTV reference lines (frames 12/34).

Unlike ``MiniSparkline`` (chrome-less trend shape only), this sparkline
carries reading aids: dashed reference lines at the HLTV rating thresholds
with right-edge mono captions (0.90 red / 1.00 neutral / 1.10 green), an
area fill under the polyline, per-point dots, and an accent endpoint dot.

API:
    spark = RatingSparkline()
    spark.set_values([1.02, 1.06, ..., 1.17])
    spark.set_reference_lines((0.90, 1.00, 1.10))   # default

Chrome colors are read from ``get_tokens()`` inside ``paintEvent`` so the
widget repaints correctly after a theme switch.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

_PAD = 6.0  # px padding above/below the drawable band (see _y)


def _y(value: float, lo: float, hi: float, h: float) -> float:
    """Map ``value`` in [lo, hi] to a y pixel in [_PAD, h - _PAD] (inverted).

    Flat ranges (hi <= lo) map every value to the vertical center.
    """
    span = hi - lo
    if span <= 0:
        return h / 2.0
    frac = (value - lo) / span
    return (h - _PAD) - frac * (h - 2.0 * _PAD)


class RatingSparkline(QWidget):
    """Rating trend sparkline with dashed, labeled HLTV reference lines."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._values: list[float] = []
        self._refs: tuple[float, ...] = (0.90, 1.00, 1.10)
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_values(self, values: list[float]) -> None:
        self._values = [float(v) for v in values if v is not None]
        self.update()

    def set_reference_lines(self, refs: tuple[float, ...] = (0.90, 1.00, 1.10)) -> None:
        self._refs = tuple(float(r) for r in refs)
        self.update()

    def _ref_color(self, ref: float, tokens) -> QColor:
        """Lowest reference reads as the bad line, highest as the good one."""
        ordered = sorted(self._refs)
        if len(ordered) >= 2 and ref == ordered[0]:
            return QColor(tokens.error)
        if len(ordered) >= 2 and ref == ordered[-1]:
            return QColor(tokens.success)
        return QColor(tokens.text_secondary)

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        if not self._values:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = get_tokens()
        line_color = QColor(tokens.chart_line_primary)

        font = Typography.mono_caption()
        fm = QFontMetricsF(font)
        label_w = fm.horizontalAdvance("0.00") + 8.0
        h = float(self.height())
        plot_left = 2.0
        plot_right = self.width() - label_w - 4.0
        if plot_right - plot_left < 10:
            return

        pool = list(self._values) + list(self._refs)
        lo, hi = min(pool), max(pool)

        def to_point(i: int, v: float) -> QPointF:
            n = len(self._values)
            x = plot_left + (plot_right - plot_left) * (i / max(1, n - 1))
            return QPointF(x, _y(v, lo, hi, h))

        # Reference lines: dashed + right-edge mono caption.
        painter.setFont(font)
        for ref in self._refs:
            color = self._ref_color(ref, tokens)
            ry = _y(ref, lo, hi, h)
            pen = QPen(color, 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(QPointF(plot_left, ry), QPointF(plot_right, ry))
            painter.drawText(
                QPointF(plot_right + 6.0, ry + fm.ascent() / 2.0 - 1.0), f"{ref:.2f}"
            )

        # Area fill under the polyline (18% alpha of the line color).
        line_path = QPainterPath(to_point(0, self._values[0]))
        for i in range(1, len(self._values)):
            line_path.lineTo(to_point(i, self._values[i]))
        area = QPainterPath(line_path)
        area.lineTo(QPointF(plot_right, h - _PAD))
        area.lineTo(QPointF(plot_left, h - _PAD))
        area.closeSubpath()
        fill = QColor(line_color)
        fill.setAlphaF(0.18)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawPath(area)

        # Polyline + per-point dots.
        pen = QPen(line_color, 2)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(line_path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(line_color)
        for i, v in enumerate(self._values):
            painter.drawEllipse(to_point(i, v), 2.5, 2.5)

        # Endpoint dot in the accent color anchors "now".
        painter.setBrush(QColor(tokens.accent_primary))
        painter.drawEllipse(to_point(len(self._values) - 1, self._values[-1]), 3.5, 3.5)
