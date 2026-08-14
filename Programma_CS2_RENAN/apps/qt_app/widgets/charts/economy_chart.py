"""Economy bar chart — equipment value per round, side-colored (frame 11).

Pure QPainter (the previous chart-view library was GPLv3-or-commercial;
this repo ships none of it). Only ``plot()`` is preserved from that
version; ``set_half_marker()`` is NEW in this rewrite:

    chart = EconomyChart()
    chart.plot(rounds)              # list of dicts (see match_detail_vm.py)
    chart.set_half_marker(13)       # NEW: dashed divider before round 13

Rounds payload shape (MatchDetailViewModel.data_changed rounds list):
    {"round_number": int, "side": "CT"|"T", "equipment_value": int, ...}
Bars are colored by each round's own ``side`` (T = chart_line_secondary,
CT = chart_line_primary). When a round lacks a known side ("CT"/"T"),
the half marker decides: rounds before it read as T, after as CT
(frame-11 layout).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.charts import token_color

_BAR_FRACTION = 0.68  # bar width as a fraction of its round slot


def _half_x(round_no: int, n_rounds: int, plot_w: float) -> float:
    """X offset of the half divider: the LEFT edge of ``round_no``'s slot."""
    if n_rounds <= 0:
        return 0.0
    return plot_w * (round_no - 1) / n_rounds


def _bar_rect(idx: int, n: int, value: float, vmax: float, plot: QRectF) -> QRectF:
    """Baseline-anchored bar rect for slot ``idx`` of ``n``; height >= 0."""
    slot_w = plot.width() / max(1, n)
    bar_w = slot_w * _BAR_FRACTION
    x = plot.left() + idx * slot_w + (slot_w - bar_w) / 2.0
    frac = 0.0 if vmax <= 0 else max(0.0, min(1.0, value / vmax))
    height = plot.height() * frac
    return QRectF(x, plot.bottom() - height, bar_w, height)


def _top_rounded(rect: QRectF, radius: float) -> QPainterPath:
    """Bar silhouette rounded only at the top corners (2px per frame spec)."""
    r = min(radius, rect.width() / 2.0, rect.height())
    path = QPainterPath(QPointF(rect.left(), rect.bottom()))
    path.lineTo(rect.left(), rect.top() + r)
    path.quadTo(rect.topLeft(), QPointF(rect.left() + r, rect.top()))
    path.lineTo(rect.right() - r, rect.top())
    path.quadTo(rect.topRight(), QPointF(rect.right(), rect.top() + r))
    path.lineTo(rect.right(), rect.bottom())
    path.closeSubpath()
    return path


class EconomyChart(QWidget):
    """Bar chart: equipment value per round, cyan=CT, orange=T (frame 11)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._rounds: list = []
        self._half: int = 0  # 0 = no divider
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def plot(self, rounds: list) -> None:
        """Plot from a list of dicts with equipment_value and side keys."""
        self._rounds = list(rounds or [])
        self.update()

    def set_half_marker(self, round_no: int = 13) -> None:
        """Draw a dashed divider caption'd "half" before ``round_no``."""
        self._half = int(round_no)
        self.update()

    def _side_color(self, r: dict, idx: int, tokens) -> QColor:
        raw = r.get("side")
        side = str(raw).upper() if raw else ""
        # Any unknown side value (None, "", "unknown", …) engages the
        # documented half-marker fallback — not just a missing key.
        if side not in ("CT", "T") and self._half:
            side = "T" if idx + 1 < self._half else "CT"
        return QColor(tokens.chart_line_primary if side == "CT" else tokens.chart_line_secondary)

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = get_tokens()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(tokens.chart_bg))
        painter.drawRoundedRect(self.rect(), tokens.radius_md, tokens.radius_md)

        cap_font = Typography.mono_caption()
        cap_fm = QFontMetricsF(cap_font)
        title_font = Typography.font("subtitle")
        title_h = QFontMetricsF(title_font).height() + 8.0

        painter.setFont(title_font)
        painter.setPen(QColor(tokens.text_primary))
        painter.drawText(
            QRectF(0, 4, self.width(), title_h),
            Qt.AlignHCenter | Qt.AlignVCenter,
            i18n.get_text("chart_economy_title", "Economy per Round"),
        )
        if not self._rounds:
            return

        n = len(self._rounds)
        values = [float(r.get("equipment_value") or 0) for r in self._rounds]
        step = 1000.0 if max(values) <= 6000 else 2000.0
        vmax = max(step, step * -(-max(values) // step))  # ceil to step multiple

        ladder_w = cap_fm.horizontalAdvance(f"${int(vmax)}") + 8.0
        bottom_h = cap_fm.height() * 2 + 26.0  # ticks + axis title + legend
        plot = QRectF(
            ladder_w + cap_fm.height() + 10.0,
            title_h + cap_fm.height() + 4.0,
            self.width() - ladder_w - cap_fm.height() - 22.0,
            self.height() - title_h - cap_fm.height() - bottom_h - 8.0,
        )
        if plot.width() < 40 or plot.height() < 30:
            return

        # $ ladder + horizontal gridlines.
        painter.setFont(cap_font)
        money = 0.0
        while money <= vmax + 1e-9:
            y = plot.bottom() - plot.height() * (money / vmax)
            painter.setPen(QPen(token_color(tokens.chart_grid), 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(tokens.text_tertiary))
            painter.drawText(
                QRectF(
                    plot.left() - ladder_w - 4.0,
                    y - cap_fm.height() / 2.0,
                    ladder_w,
                    cap_fm.height(),
                ),
                Qt.AlignRight | Qt.AlignVCenter,
                f"${int(money)}",
            )
            money += step

        # Rotated y-axis title.
        painter.save()
        painter.setPen(QColor(tokens.text_secondary))
        painter.translate(cap_fm.height(), plot.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-plot.height() / 2.0, -cap_fm.height() / 2.0, plot.height(), cap_fm.height()),
            Qt.AlignCenter,
            i18n.get_text("chart_equipment_axis", "Equipment ($)"),
        )
        painter.restore()

        # Bars (side-colored, 2px top radius) + x tick labels.
        tick_every = max(1, (n + 11) // 12)
        painter.setPen(Qt.NoPen)
        for i, r in enumerate(self._rounds):
            rect = _bar_rect(i, n, values[i], vmax, plot)
            if rect.height() > 0.5:
                painter.setBrush(self._side_color(r, i, tokens))
                painter.drawPath(_top_rounded(rect, 2.0))
            if i % tick_every == 0:
                painter.setPen(QColor(tokens.text_tertiary))
                painter.setFont(cap_font)
                painter.drawText(
                    QRectF(rect.center().x() - 20.0, plot.bottom() + 4.0, 40.0, cap_fm.height()),
                    Qt.AlignHCenter | Qt.AlignTop,
                    str(r.get("round_number", i + 1)),
                )
                painter.setPen(Qt.NoPen)

        # Half divider: dashed vertical + "half" caption above.
        if 1 < self._half <= n:
            x = plot.left() + _half_x(self._half, n, plot.width())
            painter.setPen(QPen(QColor(tokens.text_tertiary), 1, Qt.DashLine))
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            painter.setPen(QColor(tokens.accent_primary))
            painter.setFont(cap_font)
            painter.drawText(
                QRectF(x - 40.0, plot.top() - cap_fm.height() - 2.0, 80.0, cap_fm.height()),
                Qt.AlignHCenter | Qt.AlignBottom,
                i18n.get_text("chart_half_label", "half"),
            )

        # X-axis title + CT/T legend chips.
        painter.setFont(cap_font)
        painter.setPen(QColor(tokens.text_secondary))
        axis_y = plot.bottom() + cap_fm.height() + 6.0
        painter.drawText(
            QRectF(plot.left(), axis_y, plot.width(), cap_fm.height()),
            Qt.AlignHCenter | Qt.AlignTop,
            i18n.get_text("chart_round_axis", "Round number"),
        )
        chip = cap_fm.height() - 2.0
        legend_y = axis_y + cap_fm.height() + 4.0
        entries = [("CT", tokens.chart_line_primary), ("T", tokens.chart_line_secondary)]
        widths = [chip + 4.0 + cap_fm.horizontalAdvance(t) + 16.0 for t, _ in entries]
        x = plot.center().x() - sum(widths) / 2.0
        for (text, color), w in zip(entries, widths):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(x, legend_y, chip, chip), 2, 2)
            painter.setPen(QColor(tokens.text_secondary))
            painter.drawText(
                QRectF(x + chip + 4.0, legend_y - 2.0, w - chip - 4.0, chip + 4.0),
                Qt.AlignLeft | Qt.AlignVCenter,
                text,
            )
            x += w
