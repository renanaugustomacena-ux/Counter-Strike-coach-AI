"""EmptyState component — centered message with optional CTAs and loading skeleton.

Replaces bare "No data found" labels with a structured empty state that
guides the user toward the next action. Two display modes:

    Default — illustration / icon / title / description / [primary] [ghost]
    Loading — three skeleton bars instead of icon+title+description, CTAs hidden.

The illustration slot accepts either an emoji/unicode character (``icon_text``)
OR a path relative to ``design/frames/`` (``illustration``) for a Frame-20
style illustrated empty state.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
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
    """

    action_clicked = Signal()
    secondary_action_clicked = Signal()

    def __init__(
        self,
        icon_text: str = "",
        title: str = "",
        description: str = "",
        cta_text: str = "",
        secondary_cta_text: str = "",
        illustration: Optional[str] = None,
        parent: QWidget | None = None,
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

        # Icon (text fallback / companion)
        self._icon_label = QLabel(icon_text)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFont(QFont("Roboto", 48))
        self._icon_label.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        if icon_text and self._svg is None:
            layout.addWidget(self._icon_label)
        else:
            self._icon_label.setVisible(False)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setFont(QFont("Roboto", tokens.font_size_title, QFont.Bold))
        self._title_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        self._title_label.setWordWrap(True)
        layout.addWidget(self._title_label)

        # Description
        self._desc_label = QLabel(description)
        self._desc_label.setAlignment(Qt.AlignCenter)
        self._desc_label.setFont(QFont("Roboto", tokens.font_size_body))
        self._desc_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
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

        # Skeleton bars for loading mode (built lazily so non-loading
        # callers don't pay the layout cost).
        self._skeleton: Optional[QWidget] = None
        self._loading: bool = False

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
        self._icon_label.setVisible(
            not loading and bool(self._icon_label.text()) and self._svg is None
        )
        if self._svg is not None:
            self._svg.setVisible(not loading)
        self._update_cta_row_visibility()
        if self._skeleton is not None:
            self._skeleton.setVisible(loading)

    # ── Internals ──

    def _update_cta_row_visibility(self) -> None:
        any_cta_visible = (
            (not self._loading)
            and (
                (bool(self._cta_button.text()) and self._cta_button.isVisible())
                or (
                    bool(self._secondary_button.text())
                    and self._secondary_button.isVisible()
                )
            )
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
        # Insert after the icon slot (index 0 if no svg, otherwise after svg)
        layout = self.layout()
        insert_at = 1 if (self._svg is not None or self._icon_label.isVisible()) else 0
        layout.insertWidget(insert_at, skeleton)
        skeleton.setVisible(False)
