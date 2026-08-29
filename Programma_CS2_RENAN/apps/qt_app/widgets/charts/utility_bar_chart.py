"""UtilityBarChart — horizontal utility bars, grouped you-vs-pro or single-series.

Frames 12/34. Two modes:
    grouped  set_rows([(label, you, pro)])         — per row, a you-bar
             (accent_primary — Q3: the player's series speaks the accent)
             over a pro-bar (info cyan, the comparison voice) on sunken
             tracks, with right-aligned mono captions "you 12.4" /
             "pro 15.2" tinted per series. A 4th tuple element optionally
             overrides the you-bar color (frame 12 tints the waste row red).
    single   set_single([(label, value, QColor)])  — one caller-colored bar
             per row with a value caption at the bar end and a bottom tick
             ladder with vertical gridlines (frame 34 utility counts).

Rows are 34px tall; the value scale is auto-fit to the data maximum.
Chrome colors are read from ``get_tokens()`` inside ``paintEvent``.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.charts import token_color

_ROW_H = 34.0
_AXIS_H = 22.0  # single-mode tick ladder strip
_BAR_H = 10.0  # grouped-mode bar thickness
_SINGLE_BAR_H = 16.0


def _w(value: float, vmax: float, wmax: float) -> float:
    """Proportional bar width; zero-max safe, clamped to [0, wmax]."""
    if vmax <= 0:
        return 0.0
    return max(0.0, min(1.0, value / vmax)) * wmax


class UtilityBarChart(QWidget):
    """Horizontal grouped (you-vs-pro) or single-series utility bar chart."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows: list[tuple] = []
        self._mode: str = "grouped"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._sync_height()

    def set_rows(self, rows: list[tuple]) -> None:
        """Grouped mode. Tuples: (label, you, pro) or (label, you, pro, you_color)."""
        self._rows = list(rows)
        self._mode = "grouped"
        self._sync_height()
        self.update()

    def set_single(self, rows: list[tuple]) -> None:
        """Single mode. Tuples: (label, value, QColor)."""
        self._rows = list(rows)
        self._mode = "single"
        self._sync_height()
        self.update()

    def _sync_height(self) -> None:
        extra = _AXIS_H if self._mode == "single" else 0.0
        self.setMinimumHeight(int(max(1, len(self._rows)) * _ROW_H + extra))

    # ── Painting ──

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        if not self._rows:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = get_tokens()
        label_font = Typography.font("body")
        cap_font = Typography.mono_caption()
        cap_fm = QFontMetricsF(cap_font)
        label_fm = QFontMetricsF(label_font)
        label_w = max(label_fm.horizontalAdvance(str(r[0])) for r in self._rows) + 12.0
        if self._mode == "grouped":
            self._paint_grouped(painter, tokens, label_font, cap_font, cap_fm, label_w)
        else:
            self._paint_single(painter, tokens, label_font, cap_font, cap_fm, label_w)

    def _paint_grouped(self, painter, tokens, label_font, cap_font, cap_fm, label_w):
        you_word = i18n.get_text("chart_caption_you", "you")
        pro_word = i18n.get_text("chart_caption_pro", "pro")
        vmax = max(max(float(r[1]), float(r[2])) for r in self._rows)
        cap_w = (
            max(
                max(
                    cap_fm.horizontalAdvance(f"{you_word} {float(r[1]):g}"),
                    cap_fm.horizontalAdvance(f"{pro_word} {float(r[2]):g}"),
                )
                for r in self._rows
            )
            + 10.0
        )
        track_x = label_w
        track_w = self.width() - label_w - cap_w - 4.0
        if track_w < 20:
            return
        for i, row in enumerate(self._rows):
            label, you, pro = str(row[0]), float(row[1]), float(row[2])
            # Q3 (workbench): you-bar speaks the accent; the pro baseline keeps
            # the informational cyan voice so the pair never reads as CT/T.
            you_color = QColor(row[3]) if len(row) > 3 else QColor(tokens.accent_primary)
            pro_color = QColor(tokens.info)
            top = i * _ROW_H
            pair_h = 2 * _BAR_H + 4.0
            y_you = top + (_ROW_H - pair_h) / 2.0
            y_pro = y_you + _BAR_H + 4.0

            painter.setFont(label_font)
            painter.setPen(QColor(tokens.text_secondary))
            painter.drawText(
                QRectF(0, top, label_w - 8.0, _ROW_H), Qt.AlignLeft | Qt.AlignVCenter, label
            )

            painter.setPen(Qt.NoPen)
            for y_bar, value, color in ((y_you, you, you_color), (y_pro, pro, pro_color)):
                painter.setBrush(QColor(tokens.surface_sunken))
                painter.drawRoundedRect(QRectF(track_x, y_bar, track_w, _BAR_H), 2, 2)
                painter.setBrush(color)
                bar_w = _w(value, vmax, track_w)
                if bar_w > 0:
                    painter.drawRoundedRect(QRectF(track_x, y_bar, bar_w, _BAR_H), 2, 2)

            painter.setFont(cap_font)
            cap_x = track_x + track_w + 8.0
            painter.setPen(you_color)
            painter.drawText(
                QRectF(cap_x, y_you - 2, cap_w, _BAR_H + 4),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{you_word} {you:g}",
            )
            painter.setPen(pro_color)
            painter.drawText(
                QRectF(cap_x, y_pro - 2, cap_w, _BAR_H + 4),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{pro_word} {pro:g}",
            )

    def _paint_single(self, painter, tokens, label_font, cap_font, cap_fm, label_w):
        vmax = max(float(r[1]) for r in self._rows)
        scale_max = vmax if vmax > 0 else 1.0
        cap_w = max(cap_fm.horizontalAdvance(f"{float(r[1]):g}") for r in self._rows) + 12.0
        plot_x = label_w
        plot_w = self.width() - label_w - cap_w - 4.0
        plot_h = len(self._rows) * _ROW_H
        if plot_w < 20:
            return

        # Vertical gridlines + bottom tick ladder at quarters of the max
        # (frame 34: 0 / 8 / 16 / 24 / 32 for a max of 32).
        painter.setFont(cap_font)
        for quarter in range(5):
            tick = scale_max * quarter / 4.0
            x = plot_x + _w(tick, scale_max, plot_w)
            painter.setPen(QPen(token_color(tokens.chart_grid), 1))
            painter.drawLine(int(x), 0, int(x), int(plot_h))
            painter.setPen(QColor(tokens.text_tertiary))
            painter.drawText(
                QRectF(x - 40.0, plot_h + 4.0, 80.0, _AXIS_H - 4.0),
                Qt.AlignHCenter | Qt.AlignTop,
                f"{round(tick, 1):g}",
            )

        for i, (label, value, color) in enumerate(self._rows):
            top = i * _ROW_H
            y_bar = top + (_ROW_H - _SINGLE_BAR_H) / 2.0
            painter.setFont(label_font)
            painter.setPen(QColor(tokens.text_secondary))
            painter.drawText(
                QRectF(0, top, label_w - 8.0, _ROW_H),
                Qt.AlignLeft | Qt.AlignVCenter,
                str(label),
            )
            bar_w = _w(float(value), scale_max, plot_w)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(plot_x, y_bar, max(bar_w, 1.0), _SINGLE_BAR_H), 2, 2)
            painter.setFont(cap_font)
            painter.setPen(QColor(tokens.text_primary))
            painter.drawText(
                QRectF(plot_x + bar_w + 6.0, top, cap_w, _ROW_H),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{float(value):g}",
            )
