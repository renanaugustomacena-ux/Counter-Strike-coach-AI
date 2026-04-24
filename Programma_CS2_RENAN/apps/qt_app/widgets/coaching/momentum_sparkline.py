"""MomentumSparkline — mini chart of the last N round momentum multipliers.

The backend computes a round-by-round momentum multiplier (~0.85 on
tilt, ~1.2 when on fire). Visualising it as a compact sparkline with a
tilt (❄) / hot (🔥) glyph on the right gives a match-detail card a
distinctive coaching signal no stat-table competitor exposes.

Geometry-only painting (no QPainterPath animations) so the widget is
cheap to redraw when the momentum stream updates mid-match.
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

_TILT_THRESHOLD = 0.90
_HOT_THRESHOLD = 1.15


class MomentumSparkline(QWidget):
    """Horizontal mini sparkline of momentum multipliers.

    Accepts an ordered sequence of floats (one per round). Latest value
    on the right. Auto-scales the y-axis to a [0.7, 1.3] clamp so the
    centerline (1.0) always reads as neutral.
    """

    _MIN = 0.7
    _MAX = 1.3

    def __init__(
        self,
        values: Optional[Sequence[float]] = None,
        label: str = "Momentum",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setMinimumWidth(220)
        self._values: list[float] = list(values or [])
        self._label = label

    # ── Public API ──────────────────────────────────────────────────────

    def set_values(self, values: Sequence[float]) -> None:
        self._values = list(values)
        self.update()

    def set_label(self, text: str) -> None:
        self._label = text
        self.update()

    # ── Paint ───────────────────────────────────────────────────────────

    def paintEvent(self, event):  # noqa: D401
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Allocate regions: label (top), glyph+readout (right), plot (rest).
        plot_rect = QRectF(12, 22, self.width() - 68, self.height() - 34)
        readout_rect = QRectF(self.width() - 48, 0, 44, self.height())
        label_rect = QRectF(8, 2, self.width() - 48, 18)

        # Label
        painter.setPen(QColor(tokens.text_secondary))
        painter.setFont(QFont("Inter", tokens.font_size_caption, QFont.Medium))
        painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, self._label.upper())

        # Baseline at 1.0
        baseline = self._plot_y(1.0, plot_rect)
        painter.setPen(QPen(QColor(tokens.border_default), 1, Qt.DashLine))
        painter.drawLine(
            QPointF(plot_rect.left(), baseline),
            QPointF(plot_rect.right(), baseline),
        )

        if self._values:
            # Sparkline polyline
            step = plot_rect.width() / max(1, len(self._values) - 1)
            points: list[QPointF] = []
            for i, v in enumerate(self._values):
                x = plot_rect.left() + i * step
                y = self._plot_y(v, plot_rect)
                points.append(QPointF(x, y))
            painter.setPen(QPen(QColor(tokens.chart_line_primary), 2, Qt.SolidLine, Qt.RoundCap))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(QPolygonF(points))
            # Dot on the latest point
            last = self._values[-1]
            dot_color = self._band_color(last, tokens)
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(points[-1], 3.5, 3.5)

            # Readout (latest value) + glyph
            painter.setPen(QColor(tokens.text_primary))
            painter.setFont(QFont("JetBrains Mono", 14, QFont.Bold))
            painter.drawText(
                readout_rect.adjusted(0, 4, 0, -18),
                Qt.AlignCenter,
                f"{last:.2f}",
            )
            painter.setPen(dot_color)
            painter.setFont(QFont("Inter", 16, QFont.Bold))
            glyph = self._glyph(last)
            painter.drawText(readout_rect.adjusted(0, 22, 0, 0), Qt.AlignCenter, glyph)
        else:
            painter.setPen(QColor(tokens.text_tertiary))
            painter.setFont(QFont("Inter", tokens.font_size_caption))
            painter.drawText(plot_rect, Qt.AlignCenter, "no data")
        painter.end()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _plot_y(self, value: float, rect: QRectF) -> float:
        clamped = max(self._MIN, min(self._MAX, value))
        t = (clamped - self._MIN) / (self._MAX - self._MIN)
        # Flip: higher value → higher on screen (lower y)
        return rect.bottom() - t * rect.height()

    @staticmethod
    def _band_color(value: float, tokens) -> QColor:
        if value < _TILT_THRESHOLD:
            return QColor(tokens.error)
        if value > _HOT_THRESHOLD:
            return QColor(tokens.accent_primary)
        return QColor(tokens.text_primary)

    @staticmethod
    def _glyph(value: float) -> str:
        if value < _TILT_THRESHOLD:
            return "❄"
        if value > _HOT_THRESHOLD:
            return "🔥"
        return "—"
