"""FocusInsightCard — paired hero showing "what to work on" + open-CTA.

Two states (managed via QStackedLayout):
    Data — caption + focus area title + body insight + ghost CTA.
    Empty — short prompt encouraging the user to play more matches.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button


class FocusInsightCard(QFrame):
    """Pair-card for LastMatchHeroCard — surfaces a coachable focus area."""

    open_clicked = Signal(str)  # navigate_to screen name

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self.setProperty("depth", "raised")
        self.setMinimumHeight(190)

        tokens = get_tokens()

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        self._stack.setSpacing(0)

        self._navigate_to = ""

        self._data_view = self._build_data_view()
        self._empty_view = self._build_empty_view()
        self._stack.addWidget(self._data_view)
        self._stack.addWidget(self._empty_view)

        self.set_empty()

    # ── State ──

    def set_insight(self, area: str, body: str, navigate_to: str = "") -> None:
        self._navigate_to = navigate_to
        self._area_label.setText(area)
        self._body_label.setText(body)
        self._open_btn.setVisible(bool(navigate_to))
        self._stack.setCurrentWidget(self._data_view)

    def set_empty(self) -> None:
        self._stack.setCurrentWidget(self._empty_view)

    # ── Subviews ──

    def _build_data_view(self) -> QWidget:
        tokens = get_tokens()

        view = QWidget()
        outer = QVBoxLayout(view)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(tokens.spacing_sm)

        caption = QLabel("FOCUS THIS WEEK")
        Typography.apply(caption, "caption")
        caption.setStyleSheet(
            f"color: {tokens.accent_primary}; background: transparent;"
        )
        outer.addWidget(caption)

        self._area_label = QLabel("")
        self._area_label.setFont(Typography.font("h1"))
        self._area_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        outer.addWidget(self._area_label)

        self._body_label = QLabel("")
        self._body_label.setFont(Typography.font("body"))
        self._body_label.setWordWrap(True)
        self._body_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        outer.addWidget(self._body_label)

        outer.addStretch(1)

        cta_row = QHBoxLayout()
        cta_row.setContentsMargins(0, 0, 0, 0)
        cta_row.addStretch(1)
        self._open_btn = make_button("Open analysis →", variant="ghost")
        self._open_btn.setFixedHeight(32)
        self._open_btn.clicked.connect(self._on_open_clicked)
        cta_row.addWidget(self._open_btn)
        outer.addLayout(cta_row)

        return view

    def _build_empty_view(self) -> QWidget:
        tokens = get_tokens()

        view = QWidget()
        outer = QVBoxLayout(view)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(tokens.spacing_sm)

        caption = QLabel("FOCUS THIS WEEK")
        Typography.apply(caption, "caption")
        caption.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        outer.addWidget(caption)

        title = QLabel("Coming into focus")
        title.setFont(Typography.font("title"))
        title.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        outer.addWidget(title)

        body = QLabel(
            "Once you've analyzed a few matches, your top delta vs. pro "
            "baseline will surface here as a focused weekly target."
        )
        body.setFont(Typography.font("body"))
        body.setWordWrap(True)
        body.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        outer.addWidget(body)

        outer.addStretch(1)

        return view

    # ── Internal ──

    def _on_open_clicked(self) -> None:
        if self._navigate_to:
            self.open_clicked.emit(self._navigate_to)
