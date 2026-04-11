"""Match History Screen — scrollable list of user matches with color-coded ratings."""

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color, rating_label
from Programma_CS2_RENAN.apps.qt_app.viewmodels.match_history_vm import MatchHistoryViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.skeleton import SkeletonTable
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_match_history")

_MAP_PATTERN = re.compile(r"(de_\w+|cs_\w+|ar_\w+)")
_KNOWN_MAPS = frozenset(
    {
        "mirage",
        "inferno",
        "dust2",
        "overpass",
        "ancient",
        "anubis",
        "nuke",
        "vertigo",
        "train",
        "cache",
        "office",
    }
)


def _extract_map_name(demo_name: str) -> str:
    m = _MAP_PATTERN.search(demo_name)
    if m:
        return m.group(1)
    # Fallback: match bare map names in pro demo filenames (e.g. "m1-mirage.dem")
    demo_lower = demo_name.lower()
    for known in _KNOWN_MAPS:
        if known in demo_lower:
            return f"de_{known}"
    return "Unknown Map"


class MatchCard(QFrame):
    """Clickable card for a single match entry."""

    clicked = Signal(str)  # demo_name

    def __init__(self, match: dict, parent=None):
        super().__init__(parent)
        self._demo_name = match.get("demo_name", "")
        self.setObjectName("dashboard_card")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Rating badge
        rating = match.get("rating", 1.0) or 1.0
        r_color = rating_color(rating)
        badge = QLabel(f"{rating:.2f}\n{rating_label(rating)}")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedWidth(60)
        badge.setFont(QFont("Roboto", 12, QFont.Bold))
        badge.setStyleSheet(f"color: {r_color.name()}; background: transparent;")
        layout.addWidget(badge)

        # PRO badge (if pro match)
        is_pro = match.get("is_pro", False)
        if is_pro:
            pro_badge = QLabel("PRO")
            pro_badge.setAlignment(Qt.AlignCenter)
            pro_badge.setFixedWidth(40)
            pro_badge.setFixedHeight(20)
            pro_badge.setFont(QFont("Roboto", 9, QFont.Bold))
            pro_badge.setStyleSheet(
                "color: #ff9900; background: #2a1a00; border-radius: 4px; "
                "border: 1px solid #ff9900; padding: 2px 4px;"
            )
            layout.addWidget(pro_badge)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(2)

        map_name = _extract_map_name(self._demo_name)
        date_str = ""
        if match.get("match_date"):
            try:
                date_str = match["match_date"].strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = str(match["match_date"])

        if is_pro:
            pro_player = match.get("player_name", "")
            top_text = f"{map_name}  |  {pro_player}  |  {date_str}"
        else:
            top_text = f"{map_name}  |  {date_str}"
        top = QLabel(top_text)
        top.setFont(QFont("Roboto", 12))
        top.setStyleSheet("color: #dcdcdc; background: transparent;")
        info.addWidget(top)

        avg_kills = match.get("avg_kills", 0.0)
        avg_deaths = match.get("avg_deaths", 0.0)
        avg_adr = match.get("avg_adr", 0.0)
        kd = match.get("kd_ratio", 0.0)
        bottom = QLabel(
            f"K/D: {kd:.2f}  |  ADR: {avg_adr:.1f}  |  "
            f"Kills: {avg_kills:.1f}  Deaths: {avg_deaths:.1f}"
        )
        bottom.setFont(QFont("Roboto", 10))
        bottom.setStyleSheet("color: #a0a0b0; background: transparent;")
        info.addWidget(bottom)

        layout.addLayout(info, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._demo_name)
        super().mousePressEvent(event)


class MatchHistoryScreen(QWidget):
    """User's match list, ordered by date."""

    match_selected = Signal(str)  # demo_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = MatchHistoryViewModel()
        self._vm.matches_changed.connect(self._on_matches_loaded)
        self._vm.error_changed.connect(self._on_error)
        self._vm.is_loading_changed.connect(self._on_loading_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Title
        self._title_label = QLabel(i18n.get_text("match_history_title"))
        self._title_label.setObjectName("section_title")
        self._title_label.setFont(QFont("Roboto", 20, QFont.Bold))
        layout.addWidget(self._title_label)

        # Status label (error / empty — NOT used for loading anymore)
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("color: #a0a0b0; font-size: 14px;")
        self._status.setVisible(False)
        layout.addWidget(self._status)

        # Skeleton loader (shown during data fetch)
        self._skeleton = SkeletonTable(row_count=4)
        self._skeleton.setVisible(False)
        layout.addWidget(self._skeleton)

        # Empty state
        self._empty_state = EmptyState(
            title="No matches found",
            description="Play some games and they'll appear here.",
        )
        self._empty_state.setVisible(False)
        layout.addWidget(self._empty_state)

        # Scrollable match list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(6)
        self._container_layout.addStretch()
        scroll.setWidget(self._container)
        self._scroll = scroll
        layout.addWidget(scroll, 1)

    def retranslate(self):
        """Update all translatable text when language changes."""
        self._title_label.setText(i18n.get_text("match_history_title"))

    def on_enter(self):
        self._show_loading()
        self._vm.load_matches()

    def on_leave(self):
        self._vm.cancel()

    def _on_loading_changed(self, loading: bool):
        if loading:
            self._show_loading()

    def _on_matches_loaded(self, matches: list):
        self._clear_container()
        self._skeleton.setVisible(False)
        if not matches:
            self._scroll.setVisible(False)
            self._empty_state.setVisible(True)
            return

        # Show banner when all matches are pro (no personal data yet)
        has_personal = any(not m.get("is_pro", False) for m in matches)
        if not has_personal:
            banner = QLabel(
                "No personal matches yet — showing pro reference matches below. "
                "Analyze your own demos from the Dashboard to see your match history."
            )
            banner.setWordWrap(True)
            banner.setStyleSheet(
                "color: #d96600; background: #1a1200; border: 1px solid #3a2a00; "
                "border-radius: 6px; padding: 10px; font-size: 13px;"
            )
            self._container_layout.insertWidget(0, banner)

        self._status.setVisible(False)
        self._empty_state.setVisible(False)
        self._scroll.setVisible(True)
        for m in matches:
            card = MatchCard(m)
            card.clicked.connect(self._on_match_clicked)
            self._container_layout.insertWidget(self._container_layout.count() - 1, card)
        Animator.fade_in(self._container, duration=200)

    def _on_error(self, msg: str):
        if msg:
            self._skeleton.setVisible(False)
            self._show_status(msg)

    def _on_match_clicked(self, demo_name: str):
        self.match_selected.emit(demo_name)

    def _show_loading(self):
        self._clear_container()
        self._status.setVisible(False)
        self._empty_state.setVisible(False)
        self._scroll.setVisible(False)
        self._skeleton.setVisible(True)

    def _show_status(self, text: str):
        self._clear_container()
        self._skeleton.setVisible(False)
        self._scroll.setVisible(True)
        self._status.setText(text)
        self._status.setVisible(True)

    def _clear_container(self):
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
