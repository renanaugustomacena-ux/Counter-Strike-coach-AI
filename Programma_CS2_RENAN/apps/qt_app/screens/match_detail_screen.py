"""Match Detail Screen — tabbed drill-down: Overview, Rounds, Economy, Highlights."""

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    rating_color,
    rating_label,
    rgba_to_qcolor,
)
from Programma_CS2_RENAN.apps.qt_app.viewmodels.match_detail_vm import MatchDetailViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.economy_chart import EconomyChart
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.momentum_chart import MomentumChart
from Programma_CS2_RENAN.apps.qt_app.widgets.components.stat_badge import StatBadge
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_match_detail")

_COLOR_CT = QColor("#5C9EE8")
_COLOR_T = QColor("#E8C95C")

_MAP_PATTERN = re.compile(r"(de_\w+|cs_\w+|ar_\w+)")

_SEVERITY_COLORS = {
    "critical": rgba_to_qcolor(list(COLOR_RED)),
    "warning": rgba_to_qcolor(list(COLOR_YELLOW)),
    "info": _COLOR_CT,
}


def _extract_map_name(demo_name: str) -> str:
    m = _MAP_PATTERN.search(demo_name)
    return m.group(1) if m else "Unknown Map"


class MatchDetailScreen(QWidget):
    """Tabbed match detail: Overview, Round Timeline, Economy, Highlights."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = MatchDetailViewModel()
        self._vm.data_changed.connect(self._on_data)
        self._vm.error_changed.connect(self._on_error)
        self._demo_name = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Back button + Title
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        back_btn = QPushButton("\u2190 Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(lambda: self._navigate("match_history"))
        title_row.addWidget(back_btn)
        self._title = QLabel("Match Detail")
        self._title.setObjectName("section_title")
        self._title.setFont(QFont("Roboto", 20, QFont.Bold))
        title_row.addWidget(self._title, 1)
        layout.addLayout(title_row)

        # Status
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("color: #a0a0b0; font-size: 14px;")
        self._status.setVisible(False)
        layout.addWidget(self._status)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setVisible(False)
        layout.addWidget(self._tabs, 1)

    def load_demo(self, demo_name: str):
        """Called externally to load a specific match."""
        self._demo_name = demo_name
        self._title.setText(f"Match Detail — {_extract_map_name(demo_name)}")
        self._status.setText("Loading match details...")
        self._status.setVisible(True)
        self._tabs.setVisible(False)
        self._vm.load_detail(demo_name)

    def on_enter(self):
        if self._demo_name:
            self.load_demo(self._demo_name)

    def retranslate(self):
        """Update translatable text when language changes."""
        pass  # Tab labels are English-only; wire i18n when translations added

    def _on_data(self, stats: dict, rounds: list, insights: list, hltv: dict):
        self._status.setVisible(False)
        self._tabs.setVisible(True)
        self._tabs.clear()

        if not stats and not rounds:
            self._status.setText("No match data available.")
            self._status.setVisible(True)
            self._tabs.setVisible(False)
            return

        # Tab 1: Overview
        self._tabs.addTab(self._build_overview(stats, hltv, rounds), "Overview")

        # Tab 2: Rounds
        if rounds:
            self._tabs.addTab(self._build_rounds(rounds), "Rounds")

        # Tab 3: Economy
        if rounds:
            self._tabs.addTab(self._build_economy(rounds), "Economy")

        # Tab 4: Highlights
        self._tabs.addTab(self._build_highlights(rounds, insights), "Highlights")

    def _on_error(self, msg: str):
        if msg:
            self._status.setText(msg)
            self._status.setVisible(True)
            self._tabs.setVisible(False)

    def _navigate(self, screen_name: str):
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen(screen_name)

    # ── Tab builders ──

    def _build_overview(self, stats: dict, hltv: dict, rounds: list) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        tokens = get_tokens()

        rating = stats.get("rating", 1.0) or 1.0

        # Map + date header
        map_name = _extract_map_name(stats.get("demo_name", ""))
        date_str = ""
        if stats.get("match_date"):
            try:
                date_str = stats["match_date"].strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = str(stats["match_date"])
        info = QLabel(f"{map_name}  |  {date_str}")
        info.setFont(QFont("Roboto", 14))
        layout.addWidget(info)

        # StatBadge row
        kd = stats.get("kd_ratio", 0.0)
        adr = stats.get("avg_adr", 0.0)
        kast = stats.get("avg_kast", 0.0)
        hs = stats.get("avg_hs", 0.0)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(16)

        badge_row.addWidget(
            StatBadge(
                value=f"{rating:.2f}",
                label=f"Rating ({rating_label(rating)})",
                sentiment="positive" if rating >= 1.0 else "negative",
            )
        )
        badge_row.addWidget(
            StatBadge(
                value=f"{kd:.2f}",
                label="K/D Ratio",
                sentiment="positive" if kd >= 1.0 else "negative",
            )
        )
        badge_row.addWidget(
            StatBadge(
                value=f"{adr:.1f}",
                label="ADR",
                sentiment="positive" if adr >= 70 else "negative" if adr < 50 else "neutral",
            )
        )
        badge_row.addWidget(
            StatBadge(
                value=f"{kast * 100:.0f}%",
                label="KAST",
                sentiment="positive" if kast >= 0.7 else "negative" if kast < 0.5 else "neutral",
            )
        )
        badge_row.addWidget(
            StatBadge(
                value=f"{hs * 100:.0f}%",
                label="Headshot %",
                sentiment="neutral",
            )
        )
        badge_row.addStretch()
        layout.addLayout(badge_row)

        # Round outcome strip (green/red dots per round)
        if rounds:
            strip_row = QHBoxLayout()
            strip_row.setSpacing(3)
            strip_lbl = QLabel("Rounds:")
            strip_lbl.setFont(QFont("Roboto", 11))
            strip_lbl.setStyleSheet(f"color: {tokens.text_secondary};")
            strip_row.addWidget(strip_lbl)
            for r in rounds:
                won = r.get("round_won", False)
                dot = QLabel("\u25CF")
                dot.setStyleSheet(
                    f"color: {tokens.success if won else tokens.error}; font-size: 10px;"
                )
                dot.setFixedWidth(12)
                strip_row.addWidget(dot)
            strip_row.addStretch()
            layout.addLayout(strip_row)

        # HLTV breakdown with bar indicators
        if hltv:
            sep = QLabel("HLTV 2.0 Components")
            sep.setFont(QFont("Roboto", 14, QFont.Bold))
            sep.setStyleSheet(f"color: {tokens.text_primary}; margin-top: 12px;")
            layout.addWidget(sep)

            for comp, val in hltv.items():
                row = QHBoxLayout()
                name_lbl = QLabel(comp.replace("_", " ").title())
                name_lbl.setFixedWidth(180)
                name_lbl.setStyleSheet(f"color: {tokens.text_secondary};")
                row.addWidget(name_lbl)

                val_color = rating_color(val)
                val_lbl = QLabel(f"{val:.2f}")
                val_lbl.setStyleSheet(f"color: {val_color.name()};")
                val_lbl.setFont(QFont("Roboto", 11, QFont.Bold))
                row.addWidget(val_lbl)

                # Inline bar indicator (0.0–2.0 mapped to bar width)
                bar_bg = QFrame()
                bar_bg.setFixedHeight(6)
                bar_bg.setFixedWidth(120)
                bar_bg.setStyleSheet(f"background: {tokens.surface_raised}; border-radius: 3px;")
                bar_fill = QFrame(bar_bg)
                fill_w = max(1, min(120, int(val / 2.0 * 120)))
                bar_fill.setGeometry(0, 0, fill_w, 6)
                bar_fill.setStyleSheet(f"background: {val_color.name()}; border-radius: 3px;")
                row.addWidget(bar_bg)

                row.addStretch()
                layout.addLayout(row)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _build_rounds(self, rounds: list) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(2)

        # Header
        hdr = QLabel("Rnd   W/L   Side   K  D   DMG     $Equip")
        hdr.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        hdr.setStyleSheet("color: #a0a0b0;")
        layout.addWidget(hdr)

        for r in rounds:
            rnum = r.get("round_number", 0)
            side = r.get("side", "?")
            won = r.get("round_won", False)
            kills = r.get("kills", 0)
            deaths = r.get("deaths", 0)
            dmg = r.get("damage_dealt", 0)
            opening = r.get("opening_kill", False)
            equip = r.get("equipment_value", 0)

            side_color = _COLOR_CT.name() if side == "CT" else _COLOR_T.name()
            result_color = "#4CAF50" if won else "#F44336"
            result_text = "W" if won else "L"
            fk_text = "  FK" if opening else ""

            row_text = (
                f"R{rnum:<3}  "
                f'<span style="color:{result_color}">{result_text}</span>    '
                f'<span style="color:{side_color}">{side:>2}</span>    '
                f"{kills}  {deaths}   {dmg:>4}   ${equip:>5}"
                f'<span style="color:#ffaa00">{fk_text}</span>'
            )

            lbl = QLabel(row_text)
            lbl.setTextFormat(Qt.RichText)
            lbl.setFont(QFont("JetBrains Mono", 10))
            layout.addWidget(lbl)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _build_economy(self, rounds: list) -> QWidget:
        chart = EconomyChart()
        chart.plot(rounds)
        return chart

    def _build_highlights(self, rounds: list, insights: list) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(8)

        # Coaching insights
        if insights:
            sec = QLabel("Coaching Insights")
            sec.setFont(QFont("Roboto", 14, QFont.Bold))
            sec.setStyleSheet("color: #dcdcdc;")
            layout.addWidget(sec)

            for ins in insights:
                sev = ins.get("severity", "info")
                sev_color = _SEVERITY_COLORS.get(sev, _COLOR_CT)

                card = QFrame()
                card.setObjectName("dashboard_card")
                card_layout = QVBoxLayout(card)
                card_layout.setSpacing(4)

                title_lbl = QLabel(ins.get("title", ""))
                # FE-01 (AUDIT §9.1): force PlainText on DB-sourced labels
                # so Qt.AutoText cannot flip to RichText and render <a href="file://...">
                title_lbl.setTextFormat(Qt.PlainText)
                title_lbl.setFont(QFont("Roboto", 12, QFont.Bold))
                title_lbl.setStyleSheet(f"color: {sev_color.name()};")
                card_layout.addWidget(title_lbl)

                msg_lbl = QLabel(ins.get("message", ""))
                msg_lbl.setTextFormat(Qt.PlainText)  # FE-01
                msg_lbl.setWordWrap(True)
                msg_lbl.setStyleSheet("color: #dcdcdc;")
                card_layout.addWidget(msg_lbl)

                focus = ins.get("focus_area", "")
                if focus:
                    focus_lbl = QLabel(f"Focus: {focus}")
                    focus_lbl.setTextFormat(Qt.PlainText)  # FE-01
                    focus_lbl.setStyleSheet("color: #666666; font-style: italic;")
                    card_layout.addWidget(focus_lbl)

                layout.addWidget(card)
        else:
            layout.addWidget(QLabel("No coaching insights for this match yet."))

        # Momentum chart
        if rounds:
            sec = QLabel("Momentum")
            sec.setFont(QFont("Roboto", 14, QFont.Bold))
            sec.setStyleSheet("color: #dcdcdc; margin-top: 12px;")
            layout.addWidget(sec)

            momentum = MomentumChart()
            momentum.setMinimumHeight(250)
            momentum.plot(rounds)
            layout.addWidget(momentum)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll
