"""QPainter chart widgets — no chart-library dependency (license-clean)."""

import re

from PySide6.QtGui import QColor

_RGBA_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")


def token_color(value: str) -> QColor:
    """Parse a design-token color string into a QColor.

    Accepts:
        "#RRGGBB"           -> opaque hex
        "rgba(R, G, B, A)"  -> where A is either 0-255 integer or 0.0-1.0 float
        "rgb(R, G, B)"      -> opaque rgb

    Qt's ``QColor(str)`` ctor does not parse ``rgba(...)`` — we match the
    syntax the design-token JSON uses (see design/tokens/design-tokens.json)
    so chart widgets can pull grid/axis colors directly from tokens.
    """
    if not value:
        return QColor()
    if value.startswith("#"):
        return QColor(value)
    match = _RGBA_RE.match(value)
    if match:
        r, g, b = (int(match.group(i)) for i in (1, 2, 3))
        a_raw = match.group(4)
        if a_raw is None:
            alpha = 255
        else:
            a = float(a_raw)
            alpha = int(a * 255) if a <= 1.0 else int(a)
        return QColor(r, g, b, max(0, min(255, alpha)))
    # Fallback — let Qt try; it will likely yield an invalid color but
    # returning here keeps call-sites simple.
    return QColor(value)


def paint_chart_empty(painter, rect, tokens, hint: str) -> None:
    """Q4 (workbench): character for empty chart panels.

    Draws the panel's resting state — a faint tactical grid, a scope-ring
    crosshair at center, and a mono hint line — instead of the bare
    ``chart_bg`` rectangle the charts used to leave when no data arrived.
    Pure QPainter (the Linux QGraphicsEffect ban applies to all chart code).
    """
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QPen

    from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

    painter.save()
    # Faint grid, 32px pitch, clipped to the panel rect.
    grid_pen = QPen(token_color(tokens.chart_grid), 1)
    painter.setPen(grid_pen)
    step = 32.0
    x = rect.left() + step
    while x < rect.right():
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        x += step
    y = rect.top() + step
    while y < rect.bottom():
        painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        y += step

    # Scope rings + tick marks around the panel center.
    center = rect.center()
    ring = token_color(tokens.accent_primary)
    ring.setAlphaF(0.16)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(ring, 1.5))
    painter.drawEllipse(center, 26.0, 26.0)
    ring.setAlphaF(0.08)
    painter.setPen(QPen(ring, 1.5))
    painter.drawEllipse(center, 44.0, 44.0)
    tick = token_color(tokens.accent_primary)
    tick.setAlphaF(0.35)
    painter.setPen(QPen(tick, 1.5))
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        painter.drawLine(
            QPointF(center.x() + dx * 20.0, center.y() + dy * 20.0),
            QPointF(center.x() + dx * 30.0, center.y() + dy * 30.0),
        )

    # Mono hint under the rings.
    painter.setFont(Typography.mono_caption())
    painter.setPen(token_color(tokens.text_tertiary))
    painter.drawText(
        QRectF(rect.left(), center.y() + 52.0, rect.width(), 20.0),
        Qt.AlignHCenter | Qt.AlignTop,
        hint,
    )
    painter.restore()


# Chart widget exports (import AFTER token_color is defined — the chart
# modules pull token_color from this package during their own import).
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.economy_chart import EconomyChart  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.momentum_chart import (  # noqa: E402
    MomentumChart,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.radar_chart import RadarChart  # noqa: E402

__all__ = ["EconomyChart", "MomentumChart", "RadarChart", "paint_chart_empty", "token_color"]
