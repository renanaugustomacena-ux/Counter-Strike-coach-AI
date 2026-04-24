"""Card component — themed container with title, optional subtitle, and content area.

Replaces the ad-hoc _make_card() helpers duplicated across 4 screens.
Uses the dashboard_card QSS object name for theme-consistent styling.

Depth tiers (opt-in via ``depth=`` kwarg):
    flat      default — 1px subtle border, no shadow.
    raised    QSS tier: raised surface + top highlight (no QPainter cost).
    floating  QGraphicsDropShadowEffect (blur=20, offset=(0,4), 35% alpha).
              Guarded against cards containing QChartView / QtCharts —
              combining drop shadow + chart redraw causes a 10-20x FPS
              drop (documented Qt issue). When a chart child is detected
              at first render, depth silently downgrades to 'raised' and
              emits one WARNING via cs2analyzer.qt_app.card.
"""

from typing import Literal

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.qt_app.card")


class Card(QFrame):
    """Standard card with title, optional subtitle, and content area.

    Args:
        title: Card title text.
        subtitle: Optional description below the title.
        depth: Elevation tier — ``flat`` | ``raised`` | ``floating``.
        parent: Parent widget.
    """

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        depth: Literal["flat", "raised", "floating"] = "flat",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self._depth = depth
        # The QSS `QFrame#dashboard_card[depth="..."]` rules apply when
        # this property is set; polish() re-evaluates selectors.
        self.setProperty("depth", depth)
        tokens = get_tokens()

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(tokens.spacing_sm)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setFont(QFont("Roboto", tokens.font_size_subtitle, QFont.Bold))
        self._title_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        if title:
            self._layout.addWidget(self._title_label)
        else:
            self._title_label.setVisible(False)

        # Subtitle
        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setStyleSheet(
            f"color: {tokens.text_secondary}; font-size: {tokens.font_size_body}px; "
            f"background: transparent;"
        )
        if subtitle:
            self._layout.addWidget(self._subtitle_label)
        else:
            self._subtitle_label.setVisible(False)

    @property
    def title_label(self) -> QLabel:
        """Access the title QLabel for retranslation or updates."""
        return self._title_label

    @property
    def content_layout(self) -> QVBoxLayout:
        """The layout where child widgets should be added."""
        return self._layout

    def set_title(self, text: str):
        """Update the card title."""
        self._title_label.setText(text)
        self._title_label.setVisible(bool(text))

    def set_subtitle(self, text: str):
        """Update the card subtitle."""
        self._subtitle_label.setText(text)
        self._subtitle_label.setVisible(bool(text))

    def showEvent(self, event):
        """Attach the floating shadow once the card is actually visible.

        Done on showEvent (not __init__) so ``findChildren`` sees the
        final subtree — callers add chart widgets into ``content_layout``
        after the Card is constructed.
        """
        super().showEvent(event)
        self._apply_depth_effect()

    def _apply_depth_effect(self) -> None:
        """Attach or strip the drop-shadow effect based on self._depth.

        ``floating`` + a QChartView descendant = FPS tank; downgrade to
        ``raised`` with one warning so the bug is visible without
        needing a profiler.
        """
        if self._depth != "floating":
            self.setGraphicsEffect(None)
            return

        # Lazy-imported to avoid forcing QtCharts onto every screen at
        # import time; only pay the cost when we're about to decide.
        try:
            from PySide6.QtCharts import QChartView  # type: ignore
        except ImportError:  # pragma: no cover — QtCharts is always in Essentials
            QChartView = None  # type: ignore

        if QChartView is not None and self.findChildren(QChartView):
            _logger.warning(
                "Card depth=floating downgraded to raised on %r: "
                "QChartView child present (drop-shadow + chart redraw "
                "causes 10-20x FPS drop)",
                self.title_label.text() or "<untitled>",
            )
            self._depth = "raised"
            self.setProperty("depth", "raised")
            self.style().unpolish(self)
            self.style().polish(self)
            self.setGraphicsEffect(None)
            return

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(20)
        effect.setOffset(0, 4)
        # rgba(0,0,0,0.35) ~ alpha 89. Soft ambient, not a hard drop.
        effect.setColor(QColor(0, 0, 0, 89))
        self.setGraphicsEffect(effect)
