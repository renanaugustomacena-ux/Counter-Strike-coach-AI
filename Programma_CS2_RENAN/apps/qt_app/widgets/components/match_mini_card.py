"""MatchMiniCard — compact clickable preview of a single match.

Used in the dashboard's "Recent Matches" horizontal strip. Vertical
composition: map name (caption), rating (display, color-coded),
K/D summary (mono caption), relative timestamp (mono caption).

Click → emits ``clicked(demo_name)`` so the host screen can navigate
to MatchDetail.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import map_short_name
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography


class MatchMiniCard(QFrame):
    """Compact match preview card — fixed width, click-through to detail."""

    clicked = Signal(str)  # demo_name

    def __init__(self, match: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self.setProperty("depth", "raised")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(140, 124)

        self._demo_name = str(match.get("demo_name", ""))

        tokens = get_tokens()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm
        )
        layout.setSpacing(tokens.spacing_xs)

        # Map name (caption, uppercase via Typography role)
        map_label = QLabel(map_short_name(self._demo_name).upper())
        Typography.apply(map_label, "caption")
        map_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        layout.addWidget(map_label)

        # Rating (big display number, semantic-colored)
        rating_value = float(match.get("rating") or 0.0)
        rating_label = QLabel(f"{rating_value:.2f}")
        rating_font = Typography.font("display")
        rating_label.setFont(rating_font)
        rating_label.setStyleSheet(
            f"color: {rating_color(rating_value).name()}; background: transparent;"
        )
        layout.addWidget(rating_label)

        layout.addStretch(1)

        # K/D mono — last completed line of context
        kd = float(match.get("kd_ratio") or 0.0)
        kd_label = QLabel(f"K/D {kd:.2f}")
        kd_label.setFont(Typography.font("mono"))
        kd_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        layout.addWidget(kd_label)

        # Relative time
        ts_label = QLabel(_relative_time(match.get("match_date")))
        ts_label.setFont(Typography.font("mono"))
        ts_label.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        layout.addWidget(ts_label)

    def demo_name(self) -> str:
        return self._demo_name

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._demo_name:
            self.clicked.emit(self._demo_name)
        super().mousePressEvent(event)


def _relative_time(match_date: Any) -> str:
    """Best-effort relative time string. Robust to None / naive / aware dt."""
    if match_date is None:
        return "—"
    if isinstance(match_date, str):
        try:
            match_date = datetime.fromisoformat(match_date)
        except ValueError:
            return match_date[:10]
    if not isinstance(match_date, datetime):
        return "—"
    if match_date.tzinfo is None:
        match_date = match_date.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - match_date
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks}w ago"
    return match_date.strftime("%Y-%m-%d")
