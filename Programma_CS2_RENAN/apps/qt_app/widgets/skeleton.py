"""
Skeleton loader widgets — pulsing placeholder rectangles shown while data loads.

Replaces bare "Loading..." text labels with animated placeholders that signal
to the user that content is being fetched. Matches the skeleton-screen pattern
used by scope.gg and FACEIT.
"""

from PySide6.QtCore import QSequentialAnimationGroup, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class SkeletonRect(QWidget):
    """Pulsing gray rectangle — the atomic skeleton building block.

    Paints a rounded rectangle in the theme's border_default color,
    then pulses its opacity between 0.3 and 0.8 on a 1200ms loop.
    """

    def __init__(self, width: int = 0, height: int = 24, parent: QWidget | None = None):
        super().__init__(parent)
        if width > 0:
            self.setFixedWidth(width)
        self.setFixedHeight(height)
        self._pulse_anim: QSequentialAnimationGroup | None = None

    def showEvent(self, event):
        super().showEvent(event)
        if self._pulse_anim is None:
            self._pulse_anim = Animator.pulse(self, low=0.3, high=0.8, duration=1200)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._pulse_anim is not None:
            self._pulse_anim.stop()
            self._pulse_anim = None

    def paintEvent(self, event):
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(tokens.border_default)
        color.setAlphaF(0.4)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        painter.drawPath(path)
        painter.end()


class SkeletonCard(QFrame):
    """Card-shaped skeleton with 3 placeholder lines inside.

    Mimics a data card during loading. Uses the dashboard_card object name
    so it inherits the theme's card styling.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self.setFixedHeight(120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title placeholder (wider, taller)
        layout.addWidget(SkeletonRect(width=200, height=20))
        # Two body line placeholders
        layout.addWidget(SkeletonRect(height=14))
        layout.addWidget(SkeletonRect(width=280, height=14))
        layout.addStretch()


class SkeletonTable(QWidget):
    """Stacked skeleton cards mimicking a data table or list.

    Shows `row_count` SkeletonCard widgets. Call hide() and replace
    with real content when data arrives.
    """

    def __init__(self, row_count: int = 3, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for _ in range(row_count):
            layout.addWidget(SkeletonCard())
        layout.addStretch()
