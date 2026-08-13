"""Momentum chart — per-round K-D swing bars, side-colored (frame 34).

Pure QPainter (the previous chart-view library was GPLv3-or-commercial;
this repo ships none of it). Public API is preserved: ``plot(rounds)``.

Per round, momentum = (kills - deaths) normalized by the match's largest
absolute swing, drawn as a ±100 bar from the zero axis. Rounds with no
swing draw a 2px stub so every round stays visible. Bars are colored by
the round's ``side`` (T = chart_line_secondary, CT = chart_line_primary;
see match_detail_vm.py rounds payload). The HALF divider lands on the
first side change (fallback: before round 13 when sides are absent).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.charts import token_color

_BAR_FRACTION = 0.6


def _caption_font():
    """Mono family at caption size — chart tick captions (sizes from tokens)."""
    font = Typography.font("mono")
    font.setPointSize(get_tokens().font_size_caption)
    return font


class MomentumChart(QWidget):
    """Per-round kill-death swing bars around a zero axis, side-colored."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._rounds: list = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def plot(self, rounds: list) -> None:
        self._rounds = list(rounds or [])
        self.update()

    def _half_index(self) -> int:
        """Index of the first round of the second half; 0 = no divider."""
        first = self._rounds[0].get("side") if self._rounds else None
        for i, r in enumerate(self._rounds):
            if first is not None and r.get("side") not in (None, first):
                return i
        return 12 if len(self._rounds) >= 13 else 0

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = get_tokens()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(tokens.chart_bg))
        painter.drawRoundedRect(self.rect(), tokens.radius_md, tokens.radius_md)

        cap_font = _caption_font()
        cap_fm = QFontMetricsF(cap_font)
        title_font = Typography.font("subtitle")
        title_h = QFontMetricsF(title_font).height() + 8.0
        painter.setFont(title_font)
        painter.setPen(QColor(tokens.text_primary))
        painter.drawText(
            QRectF(0, 4, self.width(), title_h), Qt.AlignHCenter | Qt.AlignVCenter,
            i18n.get_text("chart_momentum_title", "Momentum (Kill-Death Delta)"),
        )
        if not self._rounds:
            return

        n = len(self._rounds)
        deltas = [
            float(r.get("kills") or 0) - float(r.get("deaths") or 0) for r in self._rounds
        ]
        peak = max((abs(d) for d in deltas), default=0.0) or 1.0

        ladder_w = cap_fm.horizontalAdvance("+100") + 8.0
        bottom_h = cap_fm.height() * 2 + 12.0  # x ticks + legend row
        plot = QRectF(
            ladder_w + 8.0, title_h + cap_fm.height() + 4.0,
            self.width() - ladder_w - 20.0,
            self.height() - title_h - cap_fm.height() - bottom_h - 10.0,
        )
        if plot.width() < 40 or plot.height() < 30:
            return
        zero_y = plot.center().y()

        # ±100 gridlines + captions, then the solid zero axis.
        painter.setFont(cap_font)
        for text, y in (("+100", plot.top()), ("0", zero_y), ("-100", plot.bottom())):
            painter.setPen(QPen(token_color(tokens.chart_grid), 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(tokens.text_tertiary))
            painter.drawText(
                QRectF(0.0, y - cap_fm.height() / 2.0, ladder_w - 4.0, cap_fm.height()),
                Qt.AlignRight | Qt.AlignVCenter, text,
            )
        painter.setPen(QPen(token_color(tokens.chart_axis), 1))
        painter.drawLine(QPointF(plot.left(), zero_y), QPointF(plot.right(), zero_y))

        # Side-colored swing bars; zero rounds draw a 2px stub on the axis.
        half_idx = self._half_index()
        slot_w = plot.width() / n
        bar_w = slot_w * _BAR_FRACTION
        tick_every = max(1, (n + 11) // 12)
        for i, r in enumerate(self._rounds):
            side = r.get("side") or ("CT" if half_idx and i >= half_idx else "T")
            color = QColor(
                tokens.chart_line_primary if side == "CT" else tokens.chart_line_secondary
            )
            x = plot.left() + i * slot_w + (slot_w - bar_w) / 2.0
            extent = (plot.height() / 2.0) * (deltas[i] / peak)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            if abs(extent) < 1.0:
                painter.drawRect(QRectF(x, zero_y - 1.0, bar_w, 2.0))
            elif extent > 0:
                painter.drawRoundedRect(QRectF(x, zero_y - extent, bar_w, extent), 2, 2)
            else:
                painter.drawRoundedRect(QRectF(x, zero_y, bar_w, -extent), 2, 2)
            if i % tick_every == 0:
                painter.setPen(QColor(tokens.text_tertiary))
                painter.setFont(cap_font)
                painter.drawText(
                    QRectF(x + bar_w / 2.0 - 20.0, plot.bottom() + 4.0,
                           40.0, cap_fm.height()),
                    Qt.AlignHCenter | Qt.AlignTop, str(r.get("round_number", i + 1)),
                )

        # HALF divider: dashed vertical at the side change + caption above.
        if half_idx:
            x = plot.left() + slot_w * half_idx
            painter.setPen(QPen(QColor(tokens.text_tertiary), 1, Qt.DashLine))
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            painter.setPen(QColor(tokens.accent_primary))
            painter.setFont(cap_font)
            painter.drawText(
                QRectF(x - 40.0, plot.top() - cap_fm.height() - 2.0, 80.0, cap_fm.height()),
                Qt.AlignHCenter | Qt.AlignBottom, i18n.get_text("chart_half_label", "half"),
            )

        # Legend chips: CT side / T side (frame 34).
        painter.setFont(cap_font)
        chip = cap_fm.height() - 2.0
        legend_y = plot.bottom() + cap_fm.height() + 6.0
        entries = [
            (i18n.get_text("chart_legend_ct_side", "CT side"), tokens.chart_line_primary),
            (i18n.get_text("chart_legend_t_side", "T side"), tokens.chart_line_secondary),
        ]
        widths = [chip + 4.0 + cap_fm.horizontalAdvance(t) + 16.0 for t, _ in entries]
        x = plot.center().x() - sum(widths) / 2.0
        for (text, color), w in zip(entries, widths):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(x, legend_y, chip, chip), 2, 2)
            painter.setPen(QColor(tokens.text_secondary))
            painter.drawText(
                QRectF(x + chip + 4.0, legend_y - 2.0, w - chip - 4.0, chip + 4.0),
                Qt.AlignLeft | Qt.AlignVCenter, text,
            )
            x += w
