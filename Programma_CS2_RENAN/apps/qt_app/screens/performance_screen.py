"""Performance Dashboard — rating trends, per-map stats, strengths/weaknesses, utility."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
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

    def _on_data(
        self, history: list, map_stats: dict, sw: dict, utility: dict, is_pro_overview: bool = False
    ):
        self._skeleton.setVisible(False)
        self._status.setVisible(False)
        self._scroll.setVisible(True)
        self._clear_content()

        if not history and not map_stats:
            self._show_status("No performance data. Play some matches!")
            return

        # Provenance banner when showing pro data as reference
        if is_pro_overview:
            banner = QLabel(
                "No personal demos analyzed yet. Showing aggregated stats from all "
                "parsed pro matches (multiple players across multiple teams). "
                "Analyze your own demos to see your personal analytics."
            )
            banner.setWordWrap(True)
            banner.setStyleSheet(
                "color: #d96600; background: #1a1200; border: 1px solid #3a2a00; "
                "border-radius: 6px; padding: 10px; font-size: 13px;"
            )
            self._content_layout.insertWidget(0, banner)

        # Each section is wrapped in try/except so a chart rendering crash
        # doesn't kill the entire app (segfaults on some Linux GPU drivers).
        # Section 1: Rating Trend
        try:
            self._build_trend(history, is_pro_overview)
        except Exception as e:
            logger.error("Failed to build rating trend: %s", e)

        # Section 2: Per-Map Stats
        if map_stats:
            try:
                self._build_map_stats(map_stats, is_pro_overview)
            except Exception as e:
                logger.error("Failed to build map stats: %s", e)

        # Section 3: Strengths & Weaknesses — hidden in pro overview (Z-scores are meaningless)
        if not is_pro_overview and sw and (sw.get("strengths") or sw.get("weaknesses")):
            try:
                self._build_sw(sw)
            except Exception as e:
                logger.error("Failed to build strengths/weaknesses: %s", e)

        # Section 4: Utility
        if utility and utility.get("user"):
            try:
                self._build_utility(utility, is_pro_overview)
            except Exception as e:
                logger.error("Failed to build utility breakdown: %s", e)

    def _on_error(self, msg: str):
        if msg:
            self._skeleton.setVisible(False)
            self._show_status(msg)

    # ── Section builders ──

    def _build_trend(self, history: list, is_pro_overview: bool = False):
        title = "Rating Trend (Pro Reference Data)" if is_pro_overview else "Rating Trend"
        card = self._section(title)
        if not history:
            card.layout().addWidget(QLabel("Not enough data for trend analysis."))
            return

        # Text-based trend display (QChartView causes segfault on some Linux GPU drivers)
        ratings = [h.get("rating", 0) for h in history if h.get("rating") is not None]
        if not ratings:
            card.layout().addWidget(QLabel("No rating data available."))
            return

        avg_r = sum(ratings) / len(ratings)
        min_r = min(ratings)
        max_r = max(ratings)
        recent_5 = ratings[-5:] if len(ratings) >= 5 else ratings
        avg_recent = sum(recent_5) / len(recent_5)

        trend_text = (
            f"Matches analyzed: {len(ratings)}\n"
            f"Average rating: {avg_r:.2f}\n"
            f"Range: {min_r:.2f} — {max_r:.2f}\n"
            f"Recent trend ({len(recent_5)} matches): {avg_recent:.2f}"
        )

        if avg_recent > avg_r + 0.05:
            trend_text += "  ▲ Improving"
        elif avg_recent < avg_r - 0.05:
            trend_text += "  ▼ Declining"
        else:
            trend_text += "  ─ Stable"

        lbl = QLabel(trend_text)
        lbl.setStyleSheet("font-size: 14px; line-height: 1.6;")
        card.layout().addWidget(lbl)

    def _build_map_stats(self, map_stats: dict, is_pro_overview: bool = False):
        title = (
            "Per-Map Performance (Pro Reference Data)" if is_pro_overview else "Per-Map Performance"
        )
        card = self._section(title)

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

    def _build_utility(self, utility: dict, is_pro_overview: bool = False):
        title = (
            "Utility Effectiveness (Pro Reference Data)"
            if is_pro_overview
            else "Utility Effectiveness (vs Pro)"
        )
        card = self._section(title)

        user = utility.get("user", {})
        pro = utility.get("pro", {})
        if not user or all(v == 0 for v in user.values()):
            card.layout().addWidget(QLabel("No utility data available yet."))
            return

        # Text-based utility comparison (QChartView causes segfault on some Linux GPU drivers)
        labels = {
            "he_damage": "HE Damage/Round",
            "molotov_damage": "Molotov Damage/Round",
            "smokes_per_round": "Smokes/Round",
            "flash_blind_time": "Flash Blind Time",
            "flash_assists": "Flash Assists",
            "unused_utility": "Unused Utility",
        }
        for key, display_name in labels.items():
            u_val = user.get(key, 0)
            p_val = pro.get(key, 0) if pro else 0
            comparison = ""
            if p_val > 0:
                pct = ((u_val - p_val) / p_val) * 100 if p_val != 0 else 0
                if pct > 10:
                    comparison = f"  (▲ {pct:+.0f}% vs pro)"
                elif pct < -10:
                    comparison = f"  (▼ {pct:+.0f}% vs pro)"
                else:
                    comparison = f"  (≈ pro level)"
            lbl = QLabel(f"{display_name}: {u_val:.2f}{comparison}")
            lbl.setStyleSheet("font-size: 13px;")
            card.layout().addWidget(lbl)

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
