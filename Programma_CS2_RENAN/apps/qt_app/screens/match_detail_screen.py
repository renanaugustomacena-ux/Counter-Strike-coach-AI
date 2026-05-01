"""Match Detail — tabbed drill-down for one analyzed demo.

Composition:
    Header rail   ← Back   |  MAP · DATE                       [Rating chip]
    Tabs (pill)   Overview · Rounds · Economy · Highlights
    Body          per-tab content (each rehoused in styled Cards)

The tab QSS hook ``QTabBar[variant="pill"]`` lives in ``base.qss.template``;
this screen sets the property and lets the template do the rest. All
inline hex codes from the previous incarnation are routed through
``get_tokens()`` so theme cycling lands cleanly.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import (
    extract_map_name,
    map_short_name,
)
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
    rating_color,
    rating_label,
)
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.viewmodels.match_detail_vm import (
    MatchDetailViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.economy_chart import EconomyChart
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.momentum_chart import MomentumChart
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.hero_stats_strip import (
    HeroStat,
    HeroStatsStrip,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_match_detail")


def _format_match_date(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return str(value)


def _kd_sentiment(value: float) -> str:
    if value >= 1.0:
        return "positive"
    if value < 0.85:
        return "negative"
    return "neutral"


def _adr_sentiment(value: float) -> str:
    if value >= 75:
        return "positive"
    if value < 55:
        return "negative"
    return "neutral"


def _kast_sentiment(value: float) -> str:
    if value >= 0.7:
        return "positive"
    if value < 0.5:
        return "negative"
    return "neutral"


def _rating_sentiment(value: float) -> str:
    if value >= 1.10:
        return "positive"
    if value < 0.90:
        return "negative"
    return "neutral"


class MatchDetailScreen(QWidget):
    """Tabbed match detail screen."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._vm = MatchDetailViewModel()
        self._vm.data_changed.connect(self._on_data)
        self._vm.error_changed.connect(self._on_error)
        self._demo_name: str = ""
        self._build_ui()

    # ── Lifecycle ──

    def load_demo(self, demo_name: str) -> None:
        """Called externally (from match list / dashboard recent strip)."""
        self._demo_name = demo_name
        self._title_label.setText(map_short_name(demo_name).upper() or "MATCH")
        self._subtitle_label.setText("")
        self._rating_chip.set_label("Loading…")
        self._rating_chip.set_severity("neutral")
        self._tabs.setVisible(False)
        self._empty_state.set_title("Loading match details…")
        self._empty_state.set_description("")
        self._empty_state.set_cta_text("")
        self._empty_state.setVisible(True)
        self._vm.load_detail(demo_name)

    def on_enter(self) -> None:
        if self._demo_name:
            self.load_demo(self._demo_name)

    def retranslate(self) -> None:
        """Tab labels are static English for now."""
        return

    # ── UI Construction ──

    def _build_ui(self) -> None:
        tokens = get_tokens()

        root = QVBoxLayout(self)
        root.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        root.setSpacing(tokens.spacing_md)

        # ── Header rail ──
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(tokens.spacing_md)

        back_btn = make_button("← Back", variant="ghost", fixed_width=88)
        back_btn.setFixedHeight(32)
        back_btn.clicked.connect(lambda: self._navigate("match_history"))
        header.addWidget(back_btn)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(0)

        self._title_label = QLabel("MATCH")
        Typography.apply(self._title_label, "h1")
        title_col.addWidget(self._title_label)

        self._subtitle_label = QLabel("")
        self._subtitle_label.setFont(Typography.font("mono"))
        self._subtitle_label.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        title_col.addWidget(self._subtitle_label)

        header.addLayout(title_col, 1)

        self._rating_chip = StatusChip("—", severity="neutral")
        header.addWidget(self._rating_chip)

        root.addLayout(header)

        # ── Empty / loading state ──
        self._empty_state = EmptyState(
            icon_text="◎",
            title="Loading match details…",
            description="",
        )
        self._empty_state.setVisible(False)
        root.addWidget(self._empty_state)

        # ── Tabs ──
        self._tabs = QTabWidget()
        tab_bar = self._tabs.tabBar()
        tab_bar.setProperty("variant", "pill")
        tab_bar.setDrawBase(False)
        # Force re-polish so the property selector kicks in even when the
        # widget is constructed before its style sheet is applied.
        tab_bar.style().unpolish(tab_bar)
        tab_bar.style().polish(tab_bar)
        self._tabs.setVisible(False)
        root.addWidget(self._tabs, 1)

    # ── Data → UI ──

    def _on_data(
        self,
        stats: dict,
        rounds: list,
        insights: list,
        hltv: dict,
    ) -> None:
        self._empty_state.setVisible(False)
        self._tabs.setVisible(True)
        self._tabs.clear()

        if not stats and not rounds:
            self._tabs.setVisible(False)
            self._empty_state.set_title("No match data available")
            self._empty_state.set_description(
                "The demo may still be processing, or analysis hasn't completed."
            )
            self._empty_state.set_cta_text("Back to Match History")
            self._empty_state.action_clicked.connect(
                lambda: self._navigate("match_history")
            )
            self._empty_state.setVisible(True)
            return

        # Header
        demo_name = stats.get("demo_name") or self._demo_name
        self._title_label.setText(map_short_name(demo_name).upper() or "MATCH")
        date_str = _format_match_date(stats.get("match_date"))
        self._subtitle_label.setText(
            f"{extract_map_name(demo_name)}   ·   {date_str}" if date_str else
            extract_map_name(demo_name)
        )

        rating = float(stats.get("rating") or 0.0)
        self._rating_chip.set_label(f"Rating {rating:.2f} · {rating_label(rating)}")
        self._rating_chip.set_severity(
            "online" if rating >= 1.10 else "offline" if rating < 0.90 else "warning"
        )

        # Tabs
        self._tabs.addTab(self._build_overview(stats, hltv, rounds), "Overview")
        if rounds:
            self._tabs.addTab(self._build_rounds(rounds), "Rounds")
            self._tabs.addTab(self._build_economy(rounds), "Economy")
        self._tabs.addTab(self._build_highlights(rounds, insights), "Highlights")

    def _on_error(self, msg: str) -> None:
        if not msg:
            return
        self._tabs.setVisible(False)
        self._empty_state.set_title("Couldn't load match")
        self._empty_state.set_description(str(msg))
        self._empty_state.set_cta_text("Back to Match History")
        self._empty_state.action_clicked.connect(
            lambda: self._navigate("match_history")
        )
        self._empty_state.setVisible(True)

    def _navigate(self, screen_name: str) -> None:
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen(screen_name)

    # ── Tab: Overview ──

    def _build_overview(self, stats: dict, hltv: dict, rounds: list) -> QWidget:
        tokens = get_tokens()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, tokens.spacing_md, 0, tokens.spacing_md)
        layout.setSpacing(tokens.spacing_lg)

        # Hero stats row
        rating = float(stats.get("rating") or 0.0)
        kd = float(stats.get("kd_ratio") or 0.0)
        adr = float(stats.get("avg_adr") or 0.0)
        kast = float(stats.get("avg_kast") or 0.0)
        hs = float(stats.get("avg_hs") or 0.0)

        hero = HeroStatsStrip(
            stats=[
                HeroStat(f"{rating:.2f}", "Rating", _rating_sentiment(rating)),
                HeroStat(f"{kd:.2f}", "K / D", _kd_sentiment(kd)),
                HeroStat(f"{adr:.0f}", "ADR", _adr_sentiment(adr)),
                HeroStat(f"{kast * 100:.0f}%", "KAST", _kast_sentiment(kast)),
                HeroStat(f"{hs * 100:.0f}%", "Headshot", "neutral"),
            ]
        )
        layout.addWidget(hero)

        # Round outcome strip — color-coded W/L per round, in a Card.
        if rounds:
            layout.addWidget(self._build_round_strip_card(rounds))

        # HLTV breakdown
        if hltv:
            layout.addWidget(self._build_hltv_card(hltv))

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_round_strip_card(self, rounds: list) -> Card:
        tokens = get_tokens()
        card = Card(title="Round outcomes", depth="raised")
        body = card.content_layout

        wins = sum(1 for r in rounds if r.get("round_won"))
        total = len(rounds)
        score_label = QLabel(f"{wins} W   ·   {total - wins} L   ·   {total} rounds")
        score_label.setFont(Typography.font("mono"))
        score_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        body.addWidget(score_label)

        strip = QHBoxLayout()
        strip.setContentsMargins(0, 0, 0, 0)
        strip.setSpacing(3)
        for r in rounds:
            won = bool(r.get("round_won"))
            cell = QLabel("●")
            cell.setAlignment(Qt.AlignCenter)
            cell.setFixedSize(14, 14)
            cell.setStyleSheet(
                f"color: {tokens.success if won else tokens.error}; "
                f"background: transparent; font-size: 12px;"
            )
            strip.addWidget(cell)
        strip.addStretch(1)
        body.addLayout(strip)
        return card

    def _build_hltv_card(self, hltv: dict) -> Card:
        tokens = get_tokens()
        card = Card(title="HLTV 2.0 components", depth="raised")
        body = card.content_layout
        body.setSpacing(tokens.spacing_xs)

        for comp, val in hltv.items():
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(tokens.spacing_md)

            name = QLabel(comp.replace("_", " ").title())
            name.setFont(Typography.font("body"))
            name.setFixedWidth(180)
            name.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent;"
            )
            row.addWidget(name)

            val_color = rating_color(val)
            value = QLabel(f"{val:.2f}")
            value.setFont(Typography.font("mono"))
            value.setFixedWidth(60)
            value.setStyleSheet(
                f"color: {val_color.name()}; background: transparent;"
            )
            row.addWidget(value)

            bar_bg = QFrame()
            bar_bg.setFixedHeight(6)
            bar_bg.setFixedWidth(180)
            bar_bg.setStyleSheet(
                f"background: {tokens.surface_sunken}; "
                f"border-radius: {tokens.radius_sm}px;"
            )
            bar_fill = QFrame(bar_bg)
            fill_w = max(1, min(180, int((val / 2.0) * 180)))
            bar_fill.setGeometry(0, 0, fill_w, 6)
            bar_fill.setStyleSheet(
                f"background: {val_color.name()}; "
                f"border-radius: {tokens.radius_sm}px;"
            )
            row.addWidget(bar_bg)

            row.addStretch(1)
            body.addLayout(row)

        return card

    # ── Tab: Rounds ──

    def _build_rounds(self, rounds: list) -> QWidget:
        tokens = get_tokens()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, tokens.spacing_md, 0, tokens.spacing_md)
        layout.setSpacing(tokens.spacing_md)

        card = Card(title="", depth="raised")
        body = card.content_layout
        body.setSpacing(2)

        header = QLabel(
            f"{'RND':<6} {'W/L':<6} {'SIDE':<6} {'K':<4} {'D':<4} "
            f"{'DMG':<8} {'EQUIP':<8}"
        )
        header.setFont(Typography.font("mono"))
        Typography.apply(header, "caption")
        header.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent; "
            f"padding-bottom: {tokens.spacing_xs}px;"
        )
        body.addWidget(header)

        for r in rounds:
            rnum = int(r.get("round_number") or 0)
            side = str(r.get("side") or "?")
            won = bool(r.get("round_won"))
            kills = int(r.get("kills") or 0)
            deaths = int(r.get("deaths") or 0)
            dmg = int(r.get("damage_dealt") or 0)
            opening = bool(r.get("opening_kill"))
            equip = int(r.get("equipment_value") or 0)

            result_color = tokens.success if won else tokens.error
            side_color = tokens.info if side == "CT" else tokens.warning
            fk_marker = (
                f"   <span style=\"color:{tokens.accent_primary}\">FK</span>"
                if opening
                else ""
            )

            row_html = (
                f"<span style='color:{tokens.text_tertiary}'>R{rnum:<3}</span> "
                f"  <span style='color:{result_color}'>{'W' if won else 'L':<4}</span> "
                f"  <span style='color:{side_color}'>{side:<4}</span> "
                f"  <span style='color:{tokens.text_primary}'>{kills:<3}</span> "
                f"  <span style='color:{tokens.text_primary}'>{deaths:<3}</span> "
                f"  <span style='color:{tokens.text_primary}'>{dmg:<6}</span> "
                f"  <span style='color:{tokens.text_secondary}'>${equip:<6}</span>"
                f"{fk_marker}"
            )
            row_label = QLabel(row_html)
            row_label.setTextFormat(Qt.RichText)
            row_label.setFont(Typography.font("mono"))
            body.addWidget(row_label)

        layout.addWidget(card)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    # ── Tab: Economy ──

    def _build_economy(self, rounds: list) -> QWidget:
        tokens = get_tokens()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, tokens.spacing_md, 0, tokens.spacing_md)

        card = Card(title="Economy by round", depth="raised")
        body = card.content_layout
        chart = EconomyChart()
        chart.setMinimumHeight(320)
        chart.plot(rounds)
        body.addWidget(chart)
        layout.addWidget(card)
        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    # ── Tab: Highlights ──

    def _build_highlights(self, rounds: list, insights: list) -> QWidget:
        tokens = get_tokens()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, tokens.spacing_md, 0, tokens.spacing_md)
        layout.setSpacing(tokens.spacing_lg)

        # Insights card
        insights_card = Card(title="Coaching insights", depth="raised")
        insights_body = insights_card.content_layout
        insights_body.setSpacing(tokens.spacing_md)

        if insights:
            for ins in insights:
                insights_body.addWidget(self._build_insight_card(ins))
        else:
            empty = QLabel(
                "No coaching insights for this match yet — once analysis "
                "completes, suggestions will surface here."
            )
            empty.setWordWrap(True)
            empty.setFont(Typography.font("body"))
            empty.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent;"
            )
            insights_body.addWidget(empty)

        layout.addWidget(insights_card)

        # Momentum chart
        if rounds:
            momentum_card = Card(title="Momentum", depth="raised")
            momentum_body = momentum_card.content_layout
            momentum = MomentumChart()
            momentum.setMinimumHeight(260)
            momentum.plot(rounds)
            momentum_body.addWidget(momentum)
            layout.addWidget(momentum_card)

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_insight_card(self, ins: dict) -> QFrame:
        tokens = get_tokens()
        sev = (ins.get("severity") or "info").lower()
        if sev == "critical":
            border_color = tokens.error
            badge_color = tokens.error
        elif sev == "warning":
            border_color = tokens.warning
            badge_color = tokens.warning
        else:
            border_color = tokens.info
            badge_color = tokens.info

        card = QFrame()
        card.setObjectName("dashboard_card")
        card.setProperty("depth", "raised")
        card.setStyleSheet(
            f"QFrame#dashboard_card {{ "
            f"background: {tokens.surface_raised}; "
            f"border-left: 3px solid {border_color}; "
            f"border-top-left-radius: 0px; "
            f"border-bottom-left-radius: 0px; "
            f"padding: {tokens.spacing_md}px; "
            f"}}"
        )
        body = QVBoxLayout(card)
        body.setSpacing(tokens.spacing_xs)
        body.setContentsMargins(
            tokens.spacing_md, tokens.spacing_md, tokens.spacing_md, tokens.spacing_md
        )

        title = QLabel(ins.get("title", ""))
        title.setTextFormat(Qt.PlainText)  # FE-01: never trust DB-sourced labels
        title.setFont(Typography.font("subtitle"))
        title.setStyleSheet(
            f"color: {badge_color}; background: transparent;"
        )
        body.addWidget(title)

        message = QLabel(ins.get("message", ""))
        message.setTextFormat(Qt.PlainText)
        message.setWordWrap(True)
        message.setFont(Typography.font("body"))
        message.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        body.addWidget(message)

        focus = ins.get("focus_area")
        if focus:
            focus_label = QLabel(f"Focus  ·  {focus}")
            focus_label.setTextFormat(Qt.PlainText)
            focus_label.setFont(Typography.font("caption"))
            focus_label.setStyleSheet(
                f"color: {tokens.text_tertiary}; background: transparent;"
            )
            body.addWidget(focus_label)

        return card
