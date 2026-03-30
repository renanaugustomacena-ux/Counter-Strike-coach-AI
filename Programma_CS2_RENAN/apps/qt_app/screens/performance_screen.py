"""Performance Dashboard — rating trends, per-map stats, strengths/weaknesses, utility."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
    COLOR_GREEN,
    COLOR_RED,
    rating_color,
    rating_label,
    rgba_to_qcolor,
)
from Programma_CS2_RENAN.apps.qt_app.viewmodels.performance_vm import PerformanceViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.rating_sparkline import RatingSparkline
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.utility_bar_chart import UtilityBarChart
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.skeleton import SkeletonTable
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_performance")

_GREEN = rgba_to_qcolor(list(COLOR_GREEN))
_RED = rgba_to_qcolor(list(COLOR_RED))


class PerformanceScreen(QWidget):
    """Aggregate performance dashboard with native Qt charts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = PerformanceViewModel()
        self._vm.data_changed.connect(self._on_data)
        self._vm.error_changed.connect(self._on_error)
        self._vm.is_loading_changed.connect(self._on_loading)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Title
        self._title_label = QLabel(i18n.get_text("advanced_analytics"))
        self._title_label.setObjectName("section_title")
        self._title_label.setFont(QFont("Roboto", 20, QFont.Bold))
        layout.addWidget(self._title_label)

        # Status (error / empty — NOT used for loading)
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("color: #a0a0b0; font-size: 14px;")
        self._status.setVisible(False)
        layout.addWidget(self._status)

        # Skeleton loader
        self._skeleton = SkeletonTable(row_count=3)
        self._skeleton.setVisible(False)
        layout.addWidget(self._skeleton)

        # Scrollable content
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(16)
        self._content_layout.addStretch()
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

    def on_enter(self):
        self._show_loading()
        self._vm.load_performance()

    def on_leave(self):
        pass  # No pending work to cancel; skeleton hides on next on_enter

    def retranslate(self):
        """Update all translatable text when language changes."""
        self._title_label.setText(i18n.get_text("advanced_analytics"))

    def _on_loading(self, loading: bool):
        if loading:
            self._show_loading()

    def _on_data(self, history: list, map_stats: dict, sw: dict, utility: dict):
        self._skeleton.setVisible(False)
        self._status.setVisible(False)
        self._scroll.setVisible(True)
        self._clear_content()

        if not history and not map_stats:
            self._show_status("No performance data. Play some matches!")
            return

        # Each section is wrapped in try/except so a chart rendering crash
        # doesn't kill the entire app (segfaults on some Linux GPU drivers).
        # Section 1: Rating Trend
        try:
            self._build_trend(history)
        except Exception as e:
            logger.error("Failed to build rating trend: %s", e)

        # Section 2: Per-Map Stats
        if map_stats:
            try:
                self._build_map_stats(map_stats)
            except Exception as e:
                logger.error("Failed to build map stats: %s", e)

        # Section 3: Strengths & Weaknesses
        if sw and (sw.get("strengths") or sw.get("weaknesses")):
            try:
                self._build_sw(sw)
            except Exception as e:
                logger.error("Failed to build strengths/weaknesses: %s", e)

        # Section 4: Utility
        if utility and utility.get("user"):
            try:
                self._build_utility(utility)
            except Exception as e:
                logger.error("Failed to build utility breakdown: %s", e)

    def _on_error(self, msg: str):
        if msg:
            self._skeleton.setVisible(False)
            self._show_status(msg)

    # ── Section builders ──

    def _build_trend(self, history: list):
        card = self._section("Rating Trend")
        if not history:
            card.layout().addWidget(QLabel("Not enough data for trend analysis."))
            return

        chart = RatingSparkline()
        chart.setMinimumHeight(250)
        chart.plot(history)
        card.layout().addWidget(chart)

    def _build_map_stats(self, map_stats: dict):
        card = self._section("Per-Map Performance")

        grid = QGridLayout()
        grid.setSpacing(12)
        cols = 3

        for idx, (map_name, stats) in enumerate(map_stats.items()):
            map_card = QFrame()
            map_card.setObjectName("dashboard_card")
            mc_layout = QVBoxLayout(map_card)
            mc_layout.setSpacing(4)

            name = QLabel(map_name.replace("de_", "").title())
            name.setFont(QFont("Roboto", 12, QFont.Bold))
            mc_layout.addWidget(name)

            r = stats.get("rating", 1.0)
            r_color = rating_color(r)
            rating_lbl = QLabel(f"Rating: {r:.2f} ({rating_label(r)})")
            rating_lbl.setFont(QFont("Roboto", 11, QFont.Bold))
            rating_lbl.setStyleSheet(f"color: {r_color.name()};")
            mc_layout.addWidget(rating_lbl)

            adr = stats.get("adr", 0)
            kd = stats.get("kd", 0)
            detail = QLabel(f"ADR: {adr:.0f}  K/D: {kd:.2f}")
            detail.setObjectName("section_subtitle")
            mc_layout.addWidget(detail)

            matches_n = stats.get("matches", 0)
            count = QLabel(f"{matches_n} matches")
            count.setObjectName("section_subtitle")
            mc_layout.addWidget(count)

            grid.addWidget(map_card, idx // cols, idx % cols)

        card.layout().addLayout(grid)

    def _build_sw(self, sw: dict):
        card = self._section("Strengths & Weaknesses (vs Pro Average)")

        row = QHBoxLayout()

        # Strengths column
        str_col = QVBoxLayout()
        str_title = QLabel("Strengths")
        str_title.setFont(QFont("Roboto", 12, QFont.Bold))
        str_title.setStyleSheet(f"color: {_GREEN.name()};")
        str_col.addWidget(str_title)

        for name, z in sw.get("strengths", []):
            display = name.replace("_", " ").title()
            lbl = QLabel(f"+{z:.1f} above avg \u2014 {display}")
            lbl.setStyleSheet(f"color: {_GREEN.name()};")
            str_col.addWidget(lbl)

        if not sw.get("strengths"):
            str_col.addWidget(QLabel("No data"))

        # Weaknesses column
        weak_col = QVBoxLayout()
        weak_title = QLabel("Weaknesses")
        weak_title.setFont(QFont("Roboto", 12, QFont.Bold))
        weak_title.setStyleSheet(f"color: {_RED.name()};")
        weak_col.addWidget(weak_title)

        for name, z in sw.get("weaknesses", []):
            display = name.replace("_", " ").title()
            lbl = QLabel(f"{z:.1f} below avg \u2014 {display}")
            lbl.setStyleSheet(f"color: {_RED.name()};")
            weak_col.addWidget(lbl)

        if not sw.get("weaknesses"):
            weak_col.addWidget(QLabel("No data"))

        row.addLayout(str_col)
        row.addLayout(weak_col)
        card.layout().addLayout(row)

    def _build_utility(self, utility: dict):
        card = self._section("Utility Effectiveness (vs Pro)")

        user = utility.get("user", {})
        if not user or all(v == 0 for v in user.values()):
            card.layout().addWidget(QLabel("No utility data available yet."))
            return

        chart = UtilityBarChart()
        chart.setMinimumHeight(280)
        chart.plot(utility)
        card.layout().addWidget(chart)

    # ── Helpers ──

    def _section(self, title: str) -> Card:
        """Create a titled card section and add it to the content layout."""
        card = Card(title=title)
        self._content_layout.insertWidget(self._content_layout.count() - 1, card)
        return card

    def _show_loading(self):
        self._clear_content()
        self._status.setVisible(False)
        self._scroll.setVisible(False)
        self._skeleton.setVisible(True)

    def _show_status(self, text: str):
        self._clear_content()
        self._skeleton.setVisible(False)
        self._scroll.setVisible(True)
        self._status.setText(text)
        self._status.setVisible(True)

    def _clear_content(self):
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setVisible(False)
                w.setParent(None)  # Immediate detach, avoids GPU segfault from deleteLater()
