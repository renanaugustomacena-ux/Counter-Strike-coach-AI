"""EmptyState component — centered message with optional CTAs and loading skeleton.

Replaces bare "No data found" labels with a structured empty state that
guides the user toward the next action. Two display modes:

    Default — illustration / icon / title / description / [primary] [ghost]
    Loading — three skeleton bars instead of icon+title+description, CTAs hidden.

The illustration slot accepts either an emoji/unicode character (``icon_text``)
OR a path relative to ``design/frames/`` (``illustration``) for a Frame-20
style illustrated empty state.

Frame-20 anatomy details:
    * the icon sits inside a 64px rounded-square ``surface_sunken`` well
      (QSS ``QFrame#empty_state_well``);
    * an optional info-colored ghost link row renders under the CTAs
      (``link_text`` / ``link_cb`` — e.g. "Or read the Getting Started
      guide →").
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button

# Project-root-relative base so design frames resolve in source-layout
# runs; PyInstaller builds will need a dedicated resource copy.
_DESIGN_FRAMES_DIR = Path(__file__).resolve().parents[4] / "design" / "frames"


class EmptyState(QWidget):
    """Centered empty state with icon, title, description, and up to two CTAs.

    Args:
        icon_text: Large emoji or unicode character displayed at top.
        title: Main message (e.g. "No matches found").
        description: Secondary explanation text.
        cta_text: Primary CTA label. If empty, no primary button is shown.
        secondary_cta_text: Optional ghost CTA label, shown beside the primary.
        illustration: Optional SVG filename under design/frames/.
        parent: Parent widget.
        link_text: Optional ghost link row under the CTAs (frame 20's
            "Or read the Getting Started guide →"). Empty = no row.
        link_cb: Optional callable invoked on link click (also emitted
            as ``link_clicked`` for signal-style wiring).
    """

    action_clicked = Signal()
    secondary_action_clicked = Signal()
    link_clicked = Signal()

    def __init__(
        self,
        icon_text: str = "",
        title: str = "",
        description: str = "",
        cta_text: str = "",
        secondary_cta_text: str = "",
        illustration: Optional[str] = None,
        parent: QWidget | None = None,
        link_text: str = "",
        link_cb: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(tokens.spacing_md)
        layout.setContentsMargins(
            tokens.spacing_xxl,
            tokens.spacing_xxxl,
            tokens.spacing_xxl,
            tokens.spacing_xxxl,
        )

        # Illustration slot (SVG) — falls back to icon_text path if missing.
        self._svg: Optional[QSvgWidget] = None
        if illustration:
            svg_path = _DESIGN_FRAMES_DIR / illustration
            if os.path.exists(svg_path):
                self._svg = QSvgWidget(str(svg_path))
                self._svg.setFixedSize(200, 140)
                layout.addWidget(self._svg, alignment=Qt.AlignCenter)

        # Icon (text fallback / companion) — sits centered inside a 64px
        # rounded-square surface_sunken well per frame 20.
        self._icon_label = QLabel(icon_text)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFont(Typography.font("display"))
        self._icon_label.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")

        self._icon_well = QFrame()
        self._icon_well.setObjectName("empty_state_well")
        self._icon_well.setFixedSize(64, 64)
        well_layout = QVBoxLayout(self._icon_well)
        well_layout.setContentsMargins(0, 0, 0, 0)
        well_layout.addWidget(self._icon_label, alignment=Qt.AlignCenter)
        if icon_text and self._svg is None:
            layout.addWidget(self._icon_well, alignment=Qt.AlignHCenter)
        else:
            self._icon_well.setVisible(False)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setFont(Typography.font("title"))
        self._title_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        self._title_label.setWordWrap(True)
        layout.addWidget(self._title_label)

        # Description
        self._desc_label = QLabel(description)
        self._desc_label.setAlignment(Qt.AlignCenter)
        self._desc_label.setFont(Typography.font("body"))
        self._desc_label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        self._desc_label.setWordWrap(True)
        if description:
            layout.addWidget(self._desc_label)
        else:
            self._desc_label.setVisible(False)

        # CTAs (primary + optional ghost secondary in a single row)
        self._cta_row = QWidget()
        cta_row_layout = QHBoxLayout(self._cta_row)
        cta_row_layout.setContentsMargins(0, 0, 0, 0)
        cta_row_layout.setSpacing(tokens.spacing_md)
        cta_row_layout.addStretch()

        self._cta_button = make_button(cta_text, variant="primary")
        self._cta_button.setFixedHeight(36)
        self._cta_button.clicked.connect(self.action_clicked.emit)
        if cta_text:
            cta_row_layout.addWidget(self._cta_button)
        else:
            self._cta_button.setVisible(False)

        self._secondary_button = make_button(secondary_cta_text, variant="ghost")
        self._secondary_button.setFixedHeight(36)
        self._secondary_button.clicked.connect(self.secondary_action_clicked.emit)
        if secondary_cta_text:
            cta_row_layout.addWidget(self._secondary_button)
        else:
            self._secondary_button.setVisible(False)

        cta_row_layout.addStretch()
        if cta_text or secondary_cta_text:
            layout.addWidget(self._cta_row)
        else:
            self._cta_row.setVisible(False)

        # Ghost link row (frame 20) — info-colored flat text button.
        self._link_button = QPushButton(link_text)
        self._link_button.setObjectName("empty_state_link")
        self._link_button.setCursor(Qt.PointingHandCursor)
        self._link_button.setFlat(True)
        self._link_button.clicked.connect(self.link_clicked.emit)
        if link_cb is not None:
            self._link_button.clicked.connect(lambda: link_cb())
        if link_text:
            layout.addWidget(self._link_button, alignment=Qt.AlignHCenter)
        else:
            self._link_button.setVisible(False)

        # Skeleton bars for loading mode (built lazily so non-loading
        # callers don't pay the layout cost).
        self._skeleton: Optional[QWidget] = None
        self._loading: bool = False

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        """Q4 (workbench): tactical motif behind every empty state.

        A faint grid across the widget plus a scope-ring crosshair centered
        on the icon well — pure QPainter (QGraphicsEffect stays banned on
        Linux), tokens re-read per paint so it tracks theme switches.
        Hidden while the loading skeleton is up: the skeleton IS the state.
        """
        super().paintEvent(event)
        if self._loading:
            return
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        grid = QColor(tokens.text_primary)
        grid.setAlphaF(0.025)
        painter.setPen(QPen(grid, 1))
        step = 28.0
        x = step
        while x < self.width():
            painter.drawLine(QPointF(x, 0.0), QPointF(x, float(self.height())))
            x += step
        y = step
        while y < self.height():
            painter.drawLine(QPointF(0.0, y), QPointF(float(self.width()), y))
            y += step

        # Crosshair rings track the icon well when shown, else the center.
        if self._icon_well.isVisibleTo(self):
            center = QPointF(self._icon_well.geometry().center())
        else:
            center = QPointF(self.rect().center())
        ring = QColor(tokens.accent_primary)
        painter.setBrush(Qt.NoBrush)
        for radius, alpha in ((58.0, 0.10), (86.0, 0.05)):
            ring.setAlphaF(alpha)
            painter.setPen(QPen(ring, 1.5))
            painter.drawEllipse(center, radius, radius)
        tick = QColor(tokens.accent_primary)
        tick.setAlphaF(0.28)
        painter.setPen(QPen(tick, 1.5))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            painter.drawLine(
                QPointF(center.x() + dx * 50.0, center.y() + dy * 50.0),
                QPointF(center.x() + dx * 66.0, center.y() + dy * 66.0),
            )

    # ── Public API ──

    def set_title(self, text: str):
        self._title_label.setText(text)

    def set_description(self, text: str):
        self._desc_label.setText(text)
        self._desc_label.setVisible(bool(text) and not self._loading)

    def set_cta_text(self, text: str):
        self._cta_button.setText(text)
        self._cta_button.setVisible(bool(text) and not self._loading)
        self._update_cta_row_visibility()

    def set_secondary_cta_text(self, text: str):
        self._secondary_button.setText(text)
        self._secondary_button.setVisible(bool(text) and not self._loading)
        self._update_cta_row_visibility()

    def set_link_text(self, text: str):
        self._link_button.setText(text)
        self._link_button.setVisible(bool(text) and not self._loading)

    def set_loading(self, loading: bool) -> None:
        """Toggle loading mode — content hidden, skeleton shown."""
        if loading == self._loading:
            return
        self._loading = loading
        if loading:
            self._build_skeleton_if_needed()
        # Toggle content vs skeleton visibility
        self._title_label.setVisible(not loading and bool(self._title_label.text()))
        self._desc_label.setVisible(not loading and bool(self._desc_label.text()))
        self._icon_well.setVisible(
            not loading and bool(self._icon_label.text()) and self._svg is None
        )
        if self._svg is not None:
            self._svg.setVisible(not loading)
        self._link_button.setVisible(not loading and bool(self._link_button.text()))
        self._update_cta_row_visibility()
        if self._skeleton is not None:
            self._skeleton.setVisible(loading)

    # ── Internals ──

    def _update_cta_row_visibility(self) -> None:
        # F-0035: isVisible() is EFFECTIVE visibility — false whenever any
        # ancestor (the row we are toggling!) is hidden, so once the row
        # hid, the buttons could never bring it back. isVisibleTo(self)
        # asks only for the widget's OWN intended visibility.
        any_cta_visible = (not self._loading) and (
            (bool(self._cta_button.text()) and self._cta_button.isVisibleTo(self))
            or (bool(self._secondary_button.text()) and self._secondary_button.isVisibleTo(self))
        )
        self._cta_row.setVisible(any_cta_visible)

    def _build_skeleton_if_needed(self) -> None:
        if self._skeleton is not None:
            return
        tokens = get_tokens()
        skeleton = QWidget(self)
        skel_layout = QVBoxLayout(skeleton)
        skel_layout.setAlignment(Qt.AlignCenter)
        skel_layout.setSpacing(tokens.spacing_sm)
        skel_layout.setContentsMargins(0, 0, 0, 0)

        # Three placeholder bars: title, body, body
        for width, height in [(220, 22), (320, 14), (260, 14)]:
            bar = QFrame()
            bar.setFixedSize(width, height)
            bar.setStyleSheet(
                f"background-color: {tokens.surface_raised}; "
                f"border-radius: {tokens.radius_sm}px;"
            )
            skel_layout.addWidget(bar, alignment=Qt.AlignCenter)

        self._skeleton = skeleton
        # Insert after the icon slot (index 0 if no svg/well, otherwise after it)
        layout = self.layout()
        insert_at = 1 if (self._svg is not None or self._icon_well.isVisible()) else 0
        layout.insertWidget(insert_at, skeleton)
        skeleton.setVisible(False)
