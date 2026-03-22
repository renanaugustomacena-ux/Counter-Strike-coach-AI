"""IconWidget — renders a named icon from IconProvider at a given size/color."""

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.icons import IconProvider


class IconWidget(QWidget):
    """Standalone widget that renders a QPainterPath icon.

    Args:
        icon_func: A callable from IconProvider (e.g. IconProvider.home).
        size: Pixel size for the icon (square).
        color: Hex color string. Defaults to tokens.text_primary.
        parent: Parent widget.
    """

    def __init__(self, icon_func=None, size: int = 24, color: str = "", parent=None):
        super().__init__(parent)
        self._icon_func = icon_func or IconProvider.home
        self._size = size
        self._color = color or get_tokens().text_primary
        self.setFixedSize(size, size)

    def set_color(self, color: str):
        """Update the icon color and repaint."""
        self._color = color
        self.update()

    def paintEvent(self, event):
        icon = self._icon_func(self._size, self._color)
        pixmap = icon.pixmap(self._size, self._size)
        painter = QPainter(self)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
