"""QPainterPath vector icon provider — no SVG dependency.

All icons drawn programmatically in a 24x24 coordinate space, scaled
at render time to any requested size. Color-injected at runtime.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _render(path: QPainterPath, size: int, color: str, stroke: float = 1.5) -> QPixmap:
    """Render a QPainterPath into a QPixmap at the given size and color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    pen = QPen(QColor(color), stroke)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    # Scale from 24x24 design space to actual size
    if size != 24:
        painter.scale(size / 24.0, size / 24.0)

    painter.drawPath(path)
    painter.end()
    return pixmap


class IconProvider:
    """Generates QIcon from QPainterPath shapes — 24x24 design grid."""

    @staticmethod
    def home(size: int = 24, color: str = "#ffffff") -> QIcon:
        """House: peaked roof + body."""
        p = QPainterPath()
        p.moveTo(12, 3)
        p.lineTo(22, 12)
        p.lineTo(19, 12)
        p.lineTo(19, 21)
        p.lineTo(5, 21)
        p.lineTo(5, 12)
        p.lineTo(2, 12)
        p.closeSubpath()
        # Door
        p.addRect(QRectF(9, 15, 6, 6))
        return QIcon(_render(p, size, color))

    @staticmethod
    def brain(size: int = 24, color: str = "#ffffff") -> QIcon:
        """Brain: circle with inner partitions (coaching/intelligence)."""
        p = QPainterPath()
        p.addEllipse(QRectF(3, 3, 18, 18))
        # Center line
        p.moveTo(12, 5)
        p.lineTo(12, 19)
        # Left bump
        p.moveTo(12, 8)
        p.cubicTo(7, 6, 5, 11, 12, 12)
        # Right bump
        p.moveTo(12, 12)
        p.cubicTo(17, 11, 19, 16, 12, 16)
        return QIcon(_render(p, size, color))

    @staticmethod
    def list_icon(size: int = 24, color: str = "#ffffff") -> QIcon:
        """Three horizontal lines (list/history)."""
        p = QPainterPath()
        for y in (6, 12, 18):
            p.moveTo(4, y)
            p.lineTo(20, y)
        # Bullet dots
        for y in (6, 12, 18):
            p.addEllipse(QRectF(1, y - 1.5, 3, 3))
        return QIcon(_render(p, size, color))

    @staticmethod
    def chart(size: int = 24, color: str = "#ffffff") -> QIcon:
        """Three ascending bars (performance/stats)."""
        p = QPainterPath()
        p.addRect(QRectF(3, 14, 5, 8))
        p.addRect(QRectF(10, 8, 5, 14))
        p.addRect(QRectF(17, 3, 5, 19))
        return QIcon(_render(p, size, color))

    @staticmethod
    def crosshair(size: int = 24, color: str = "#ffffff") -> QIcon:
        """Crosshair target (tactical)."""
        p = QPainterPath()
        p.addEllipse(QRectF(4, 4, 16, 16))
        p.addEllipse(QRectF(9, 9, 6, 6))
        # Cross lines
        p.moveTo(12, 1)
        p.lineTo(12, 7)
        p.moveTo(12, 17)
        p.lineTo(12, 23)
        p.moveTo(1, 12)
        p.lineTo(7, 12)
        p.moveTo(17, 12)
        p.lineTo(23, 12)
        return QIcon(_render(p, size, color))

    @staticmethod
    def gear(size: int = 24, color: str = "#ffffff") -> QIcon:
        """Gear/cog (settings)."""
        p = QPainterPath()
        p.addEllipse(QRectF(8, 8, 8, 8))
        # Teeth (simplified — 4 notches at N/S/E/W)
        for angle_deg in (0, 90, 180, 270):
            import math

            rad = math.radians(angle_deg)
            cx, cy = 12, 12
            dx, dy = math.cos(rad), math.sin(rad)
            p.moveTo(cx + dx * 7, cy + dy * 7)
            p.lineTo(cx + dx * 10, cy + dy * 10)
        # Diagonal teeth
        for angle_deg in (45, 135, 225, 315):
            import math

            rad = math.radians(angle_deg)
            cx, cy = 12, 12
            dx, dy = math.cos(rad), math.sin(rad)
            p.moveTo(cx + dx * 7, cy + dy * 7)
            p.lineTo(cx + dx * 10, cy + dy * 10)
        return QIcon(_render(p, size, color))

    @staticmethod
    def help_circle(size: int = 24, color: str = "#ffffff") -> QIcon:
        """Question mark in circle (help)."""
        p = QPainterPath()
        p.addEllipse(QRectF(2, 2, 20, 20))
        # Question mark
        p.moveTo(9, 9)
        p.cubicTo(9, 5, 15, 5, 15, 9)
        p.cubicTo(15, 12, 12, 12, 12, 14)
        # Dot
        p.addEllipse(QRectF(11, 17, 2, 2))
        return QIcon(_render(p, size, color))
