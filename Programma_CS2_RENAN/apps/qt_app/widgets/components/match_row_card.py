"""MatchRowCard — wide horizontal row for the Match History list.

Companion to ``MatchMiniCard`` (vertical, fixed-width strip card). Same
data inputs, same click contract — different shape:

    [ MAP        |  RATING tag        |  K/D  ADR  K/D-counts  |  PRO? ]
      9h ago

Click anywhere on the row → ``clicked(demo_name)``.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import map_short_name
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color, rating_label
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.components.match_mini_card import (
    _relative_time,
)


class MatchRowCard(QFrame):
    """Single-row match entry with three columns + optional PRO marker."""

    clicked = Signal(str)  # demo_name

    def __init__(self, match: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self.setProperty("depth", "raised")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)

        self._demo_name = str(match.get("demo_name", ""))
        is_pro = bool(match.get("is_pro", False))

        tokens = get_tokens()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_sm, tokens.spacing_lg, tokens.spacing_sm
        )
        layout.setSpacing(tokens.spacing_lg)

        # ── Column 1: map + relative time ──
        map_col = QVBoxLayout()
        map_col.setContentsMargins(0, 0, 0, 0)
        map_col.setSpacing(2)

        map_label = QLabel(map_short_name(self._demo_name).upper())
        Typography.apply(map_label, "caption")
        map_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )

        date_label = QLabel(_relative_time(match.get("match_date")))
        date_label.setFont(Typography.font("mono"))
        date_label.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )

        if is_pro:
            player = str(match.get("player_name") or "").strip()
            if player:
                map_label.setText(
                    f"{map_short_name(self._demo_name).upper()}  ·  {player.upper()}"
                )

        map_col.addWidget(map_label)
        map_col.addWidget(date_label)
        map_col_w = QWidget()
        map_col_w.setLayout(map_col)
        map_col_w.setFixedWidth(220)
        layout.addWidget(map_col_w)

        # ── Column 2: rating + label tag ──
        rating_value = float(match.get("rating") or 0.0)
        rating_col = QVBoxLayout()
        rating_col.setContentsMargins(0, 0, 0, 0)
        rating_col.setSpacing(0)

        rating_label_widget = QLabel(f"{rating_value:.2f}")
        rating_label_widget.setFont(Typography.font("h1"))
        rating_label_widget.setStyleSheet(
            f"color: {rating_color(rating_value).name()}; background: transparent;"
        )
        rating_col.addWidget(rating_label_widget)

        rating_tag = QLabel(rating_label(rating_value).upper())
        Typography.apply(rating_tag, "caption")
        rating_tag.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        rating_col.addWidget(rating_tag)

        rating_col_w = QWidget()
        rating_col_w.setLayout(rating_col)
        rating_col_w.setFixedWidth(140)
        layout.addWidget(rating_col_w)

        # ── Column 3: stats mono ──
        stats_col = QVBoxLayout()
        stats_col.setContentsMargins(0, 0, 0, 0)
        stats_col.setSpacing(2)

        kd = float(match.get("kd_ratio") or 0.0)
        adr = float(match.get("avg_adr") or 0.0)
        kills = float(match.get("avg_kills") or 0.0)
        deaths = float(match.get("avg_deaths") or 0.0)

        primary = QLabel(f"K/D {kd:.2f}    ADR {adr:.0f}")
        primary.setFont(Typography.font("mono"))
        primary.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        stats_col.addWidget(primary)

        secondary = QLabel(f"{kills:.0f} kills  ·  {deaths:.0f} deaths")
        secondary.setFont(Typography.font("mono"))
        secondary.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        stats_col.addWidget(secondary)

        layout.addLayout(stats_col, 1)

        # ── PRO marker (right-most) ──
        if is_pro:
            pro_chip = QLabel("PRO")
            Typography.apply(pro_chip, "caption")
            pro_chip.setAlignment(Qt.AlignCenter)
            pro_chip.setFixedSize(48, 22)
            pro_chip.setStyleSheet(
                f"color: {tokens.accent_primary}; "
                f"background: {tokens.accent_muted_15}; "
                f"border: 1px solid {tokens.accent_muted_30}; "
                f"border-radius: {tokens.radius_sm}px;"
            )
            layout.addWidget(pro_chip)

    def demo_name(self) -> str:
        return self._demo_name

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._demo_name:
            self.clicked.emit(self._demo_name)
        super().mousePressEvent(event)
