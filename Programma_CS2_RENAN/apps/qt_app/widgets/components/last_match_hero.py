"""LastMatchHeroCard — dashboard hero showing the latest match + rating trend.

Two states:
    Data — caption + display-rating + map/time meta + MiniSparkline trend.
    Empty — EmptyState with "Analyze your first demo" CTA.

Click on the data view emits ``detail_clicked(demo_name)``; the empty
CTA emits ``analyze_clicked``.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import map_short_name
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color, rating_label
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.mini_sparkline import MiniSparkline
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.match_mini_card import (
    _relative_time,
)


class LastMatchHeroCard(QFrame):
    """Dashboard hero card — last match + rating trend."""

    analyze_clicked = Signal()
    detail_clicked = Signal(str)  # demo_name

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self.setProperty("depth", "highlighted")
        self.setMinimumHeight(190)

        tokens = get_tokens()

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        self._stack.setSpacing(0)

        self._data_view = self._build_data_view()
        self._empty_view = self._build_empty_view()
        self._stack.addWidget(self._data_view)
        self._stack.addWidget(self._empty_view)

        self.set_state(None, [])

    # ── State ──

    def set_state(
        self, last_match: dict[str, Any] | None, history: list[float]
    ) -> None:
        if last_match is None:
            self._stack.setCurrentWidget(self._empty_view)
            return

        self._current_demo = str(last_match.get("demo_name", ""))
        rating_value = float(last_match.get("rating") or 0.0)
        self._rating_label.setText(f"{rating_value:.2f}")
        self._rating_label.setStyleSheet(
            f"color: {rating_color(rating_value).name()}; background: transparent;"
        )

        map_short = map_short_name(self._current_demo)
        time_str = _relative_time(last_match.get("match_date"))
        self._meta_label.setText(f"{map_short.upper()}  ·  {time_str}")

        kd = float(last_match.get("kd_ratio") or 0.0)
        adr = float(last_match.get("avg_adr") or 0.0)
        self._kd_label.setText(f"K/D {kd:.2f}    ADR {adr:.0f}")
        self._tag_label.setText(rating_label(rating_value))

        self._spark.set_values(history if history else [rating_value])

        self._stack.setCurrentWidget(self._data_view)

    # ── Subviews ──

    def _build_data_view(self) -> QWidget:
        tokens = get_tokens()

        view = QWidget()
        outer = QVBoxLayout(view)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(tokens.spacing_sm)

        caption = QLabel("LAST MATCH")
        Typography.apply(caption, "caption")
        caption.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        outer.addWidget(caption)

        # ── Body row: text column + sparkline ──
        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(tokens.spacing_xl)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(tokens.spacing_xs)

        # Rating row: big number + tag chip
        rating_row = QHBoxLayout()
        rating_row.setContentsMargins(0, 0, 0, 0)
        rating_row.setSpacing(tokens.spacing_sm)

        self._rating_label = QLabel("—")
        self._rating_label.setFont(Typography.font("display"))
        self._rating_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        rating_row.addWidget(self._rating_label, 0, Qt.AlignBottom)

        self._tag_label = QLabel("")
        self._tag_label.setFont(Typography.font("caption"))
        self._tag_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
            f"padding-bottom: 8px;"
        )
        rating_row.addWidget(self._tag_label, 0, Qt.AlignBottom)
        rating_row.addStretch(1)

        text_col.addLayout(rating_row)

        # Meta line: MAP · time
        self._meta_label = QLabel("")
        self._meta_label.setFont(Typography.font("body"))
        self._meta_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        text_col.addWidget(self._meta_label)

        # K/D + ADR mono
        self._kd_label = QLabel("")
        self._kd_label.setFont(Typography.font("mono"))
        self._kd_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        text_col.addWidget(self._kd_label)
        text_col.addStretch(1)

        body_row.addLayout(text_col, 1)

        self._spark = MiniSparkline()
        self._spark.setMinimumWidth(220)
        body_row.addWidget(self._spark, 1)

        outer.addLayout(body_row)

        # Click anywhere on the data view → emit detail_clicked
        view.setCursor(Qt.PointingHandCursor)
        view.mousePressEvent = self._on_data_clicked  # type: ignore[assignment]

        return view

    def _build_empty_view(self) -> QWidget:
        empty = EmptyState(
            icon_text="◎",
            title="No matches analyzed yet",
            description="Point the analyzer at your demo folder to start seeing your trend.",
            cta_text="Analyze a demo",
        )
        empty.action_clicked.connect(self.analyze_clicked.emit)
        return empty

    # ── Internal ──

    def _on_data_clicked(self, _event):
        if getattr(self, "_current_demo", ""):
            self.detail_clicked.emit(self._current_demo)
