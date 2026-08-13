"""MetricBarRow — labeled metric with a colored fill bar (frame 09).

One row of the Match Detail HLTV 2.0 two-column grid (and any bar-row
list): label left, mono value tinted like the fill, then an 8px sunken
track with a proportional colored fill.

API:
    row = MetricBarRow()
    row.set_metric("Rating Impact", "1.28", 1.28 / 1.5, QColor(tokens.success))

``frac`` is clamped to [0, 1]. Chrome colors are read from
``get_tokens()`` inside ``paintEvent`` so the row theme-tracks; the fill
color is caller-chosen (typically a semantic token).
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

_TRACK_H = 8.0
_LABEL_SHARE = 0.42  # fraction of the row width given to the label column


def _value_font():
    """Mono family at caption size — value captions (sizes from tokens)."""
    font = Typography.font("mono")
    font.setPointSize(get_tokens().font_size_caption)
    return font


class MetricBarRow(QWidget):
    """Label + mono value + 8px track/fill bar in one paint pass."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._label: str = ""
        self._value_text: str = ""
        self._frac: float = 0.0
        self._color: QColor = QColor()
        self.setMinimumHeight(26)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_metric(self, label: str, value_text: str, frac: float, color: QColor) -> None:
        self._label = str(label)
        self._value_text = str(value_text)
        self._frac = max(0.0, min(1.0, float(frac)))
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        if not self._label and not self._value_text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = get_tokens()
        height = float(self.height())
        width = float(self.width())

        # Label column.
        label_font = Typography.font("body")
        painter.setFont(label_font)
        painter.setPen(QColor(tokens.text_secondary))
        label_w = width * _LABEL_SHARE
        painter.drawText(
            QRectF(0, 0, label_w - 8.0, height), Qt.AlignLeft | Qt.AlignVCenter, self._label
        )

        # Mono value, tinted like the fill.
        value_font = _value_font()
        value_fm = QFontMetricsF(value_font)
        value_w = max(value_fm.horizontalAdvance(self._value_text), 30.0) + 10.0
        painter.setFont(value_font)
        painter.setPen(self._color)
        painter.drawText(
            QRectF(label_w, 0, value_w - 10.0, height),
            Qt.AlignRight | Qt.AlignVCenter,
            self._value_text,
        )

        # Track + fill.
        track_x = label_w + value_w
        track_w = width - track_x
        if track_w < 20:
            return
        track_y = (height - _TRACK_H) / 2.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(tokens.surface_sunken))
        painter.drawRoundedRect(QRectF(track_x, track_y, track_w, _TRACK_H), 3, 3)
        fill_w = track_w * self._frac
        if fill_w > 1:
            painter.setBrush(self._color)
            painter.drawRoundedRect(QRectF(track_x, track_y, fill_w, _TRACK_H), 3, 3)
