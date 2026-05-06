"""Card component — themed container with title, optional subtitle, and content area.

Replaces the ad-hoc _make_card() helpers duplicated across 4 screens.
Uses the dashboard_card QSS object name for theme-consistent styling.

Depth tiers (opt-in via ``depth=`` kwarg):
    flat         default — 1px subtle border, no shadow.
    raised       QSS tier: raised surface + top highlight (no QPainter cost).
    highlighted  QSS tier: raised surface + 3px accent left edge — used
                 sparingly to draw the eye to the most important card on
                 a screen. No shadow.
    floating     QGraphicsDropShadowEffect (blur=20, offset=(0,4), 35% alpha).
                 Guarded against cards containing QChartView / QtCharts —
                 combining drop shadow + chart redraw causes a 10-20x FPS
                 drop (documented Qt issue). When a chart child is detected
                 at first render, depth silently downgrades to 'raised' and
                 emits one WARNING via cs2analyzer.qt_app.card.
    frosted      Soft-frost surface — semi-transparent fill (frost_bg),
                 hairline highlight border (frost_border), and an
                 elevated drop shadow tinted with the theme's accent
                 (frost_glow). Approximates the visual of a backdrop-blur
                 panel without true backdrop compositing (which Qt does
                 not natively support). Same QChartView guard as floating.
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
        depth: Literal["flat", "raised", "highlighted", "floating", "frosted"] = "flat",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self._depth = depth
        # The QSS `QFrame#dashboard_card[depth="..."]` rules apply when
        # this property is set; polish() re-evaluates selectors.
        self.setProperty("depth", depth)
        tokens = get_tokens()
        # Apply theme-aware frost stylesheet inline — the dashboard_card
        # QSS doesn't ship a frosted variant in the global theme rules,
        # so push the rgba fill / hairline border directly onto the
        # widget instance. Stays consistent across CS2 / CSGO / CS16
        # palettes because the tokens themselves are theme-driven.
        if depth == "frosted":
            self.setStyleSheet(
                f"#dashboard_card {{ "
                f"background-color: {tokens.frost_bg}; "
                f"border: 1px solid {tokens.frost_border}; "
                f"border-radius: 12px; "
                f"}}"
            )

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

        ``floating`` and ``frosted`` both mount a QGraphicsDropShadowEffect.
        Both are guarded against QChartView descendants — drop-shadow +
        chart redraw causes a 10-20x FPS drop. When a chart child is
        present, the depth silently downgrades to ``raised`` with one
        WARNING so the bug is visible without needing a profiler.
        """
        if self._depth not in ("floating", "frosted"):
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
                "Card depth=%s downgraded to raised on %r: "
                "QChartView child present (drop-shadow + chart redraw "
                "causes 10-20x FPS drop)",
                self._depth,
                self.title_label.text() or "<untitled>",
            )
            self._depth = "raised"
            self.setProperty("depth", "raised")
            self.style().unpolish(self)
            self.style().polish(self)
            self.setGraphicsEffect(None)
            return

        if self._depth == "frosted":
            tokens = get_tokens()
            # Parse the rgba(r, g, b, a) glow string into a QColor so the
            # shadow tints with the theme's accent (orange for CS2, gold
            # for CSGO, dark-gold for CS16). frost_glow is rgba; extract
            # the channels directly without depending on an alpha multiplier.
            r, g, b, a = _parse_rgba(tokens.frost_glow, fallback=(0, 0, 0, 0.35))
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(tokens.frost_elevation_blur)
            effect.setOffset(0, tokens.frost_elevation_offset)
            effect.setColor(QColor(r, g, b, int(a * 255)))
            self.setGraphicsEffect(effect)
            return

        # 'floating' fallback — soft ambient drop shadow, theme-neutral.
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(20)
        effect.setOffset(0, 4)
        # rgba(0,0,0,0.35) ~ alpha 89. Soft ambient, not a hard drop.
        effect.setColor(QColor(0, 0, 0, 89))
        self.setGraphicsEffect(effect)


def _parse_rgba(s: str, fallback: tuple[int, int, int, float]) -> tuple[int, int, int, float]:
    """Parse 'rgba(r, g, b, a)' or 'rgb(r, g, b)' into channel ints + alpha float.

    Tolerant of whitespace; returns the fallback tuple if the string
    doesn't match the expected shape. Used by Card._apply_depth_effect
    to translate frost_glow (rgba string) into a QColor.
    """
    import re

    m = re.match(
        r"^\s*rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)\s*$",
        s,
    )
    if not m:
        return fallback
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    a = float(m.group(4)) if m.group(4) is not None else 1.0
    return (r, g, b, a)
