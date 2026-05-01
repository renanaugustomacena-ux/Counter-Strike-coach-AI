"""Performance — aggregate analytics dashboard.

Composition:
    Title rail        Performance               [● N matches]
    Pro-overview banner   (visible when no personal data yet)
    Hero stats row    Avg rating · Matches · K/D · ADR · KAST
    Section: Trend    average / range / recent (text summary; chart-free
                      to avoid GPU segfaults on some Linux drivers, per
                      the prior implementation's note).
    Section: Per-map  3-column grid of map mini-cards.
    Section: S/W vs pro  two columns (when not pro-overview).
    Section: Utility  ADR/round comparison row vs pro baseline.

Body is housed in a QStackedWidget so loading / empty / data swaps
don't push the title rail around.
"""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
    rating_color,
    rating_label,
)
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.viewmodels.performance_vm import (
    PerformanceViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.hero_stats_strip import (
    HeroStat,
    HeroStatsStrip,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.apps.qt_app.widgets.skeleton import SkeletonTable
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_performance")


def _rating_sentiment(value: float) -> str:
    if value >= 1.10:
        return "positive"
    if value < 0.90:
        return "negative"
    return "neutral"


def _kd_sentiment(value: float) -> str:
    if value >= 1.0:
        return "positive"
    if value < 0.85:
        return "negative"
    return "neutral"


class PerformanceScreen(QWidget):
    """Aggregate performance dashboard with sectioned cards."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._vm = PerformanceViewModel()
        self._vm.data_changed.connect(self._on_data)
        self._vm.error_changed.connect(self._on_error)
        self._vm.is_loading_changed.connect(self._on_loading)

        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self) -> None:
        self._show_loading()
        self._vm.load_performance()

    def on_leave(self) -> None:
        return

    def retranslate(self) -> None:
        self._title_label.setText(i18n.get_text("advanced_analytics"))

    # ── UI Construction ──

    def _build_ui(self) -> None:
        tokens = get_tokens()

        root = QVBoxLayout(self)
        root.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        root.setSpacing(tokens.spacing_md)

        # Title rail
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        self._title_label = QLabel(i18n.get_text("advanced_analytics"))
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)
        self._count_chip = StatusChip("0 matches", severity="neutral")
        title_row.addWidget(self._count_chip)
        root.addLayout(title_row)

        # Provenance banner — visible only when surfacing pro data as ref
        self._pro_banner = QLabel(
            "No personal demos analyzed yet. Showing aggregated stats from "
            "all parsed pro matches (multiple players across multiple teams). "
            "Analyze your own demos to see your personal analytics."
        )
        self._pro_banner.setWordWrap(True)
        self._pro_banner.setFont(Typography.font("body"))
        self._pro_banner.setStyleSheet(
            f"color: {tokens.accent_primary}; "
            f"background: {tokens.accent_muted_15}; "
            f"border: 1px solid {tokens.accent_muted_30}; "
            f"border-radius: {tokens.radius_md}px; "
            f"padding: {tokens.spacing_md}px;"
        )
        self._pro_banner.setVisible(False)
        root.addWidget(self._pro_banner)

        # Body stack: skeleton | empty | content
        self._body_stack = QStackedWidget()
        root.addWidget(self._body_stack, 1)

        self._skeleton = SkeletonTable(row_count=3)
        self._body_stack.addWidget(self._skeleton)

        self._empty_state = EmptyState(
            icon_text="◎",
            title="No performance data yet",
            description="Analyze a demo to start seeing your aggregate trends.",
            cta_text="Open Dashboard",
        )
        self._empty_state.action_clicked.connect(
            lambda: self._navigate("home")
        )
        self._body_stack.addWidget(self._empty_state)

        self._content_scroll = QScrollArea()
        self._content_scroll.setWidgetResizable(True)
        self._content_scroll.setFrameShape(QFrame.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(tokens.spacing_lg)
        self._content_layout.addStretch(1)
        self._content_scroll.setWidget(self._content)
        self._body_stack.addWidget(self._content_scroll)

        self._page_skeleton = 0
        self._page_empty = 1
        self._page_content = 2

    # ── Plumbing ──

    def _on_loading(self, loading: bool) -> None:
        if loading:
            self._show_loading()

    def _show_loading(self) -> None:
        self._clear_content()
        self._body_stack.setCurrentIndex(self._page_skeleton)

    def _on_error(self, msg: str) -> None:
        if not msg:
            return
        self._empty_state.set_title("Couldn't load performance")
        self._empty_state.set_description(str(msg))
        self._body_stack.setCurrentIndex(self._page_empty)

    def _navigate(self, screen_name: str) -> None:
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen(screen_name)

    # ── Data → UI ──

    def _on_data(
        self,
        history: list,
        map_stats: dict,
        sw: dict,
        utility: dict,
        is_pro_overview: bool = False,
    ) -> None:
        self._clear_content()

        if not history and not map_stats:
            self._empty_state.set_title("No performance data yet")
            self._empty_state.set_description(
                "Analyze a demo to start seeing your aggregate trends."
            )
            self._body_stack.setCurrentIndex(self._page_empty)
            self._update_count_chip(0)
            self._pro_banner.setVisible(False)
            return

        self._pro_banner.setVisible(is_pro_overview)
        self._update_count_chip(len(history) if history else 0)

        # Hero strip — top-of-page snapshot.
        self._content_layout.insertWidget(
            self._content_layout.count() - 1,
            self._build_hero(history, utility),
        )

        # Sections: trend, map stats, strengths/weaknesses, utility.
        try:
            self._content_layout.insertWidget(
                self._content_layout.count() - 1,
                self._build_trend(history, is_pro_overview),
            )
        except Exception as e:
            logger.error("trend section failed: %s", e)

        if map_stats:
            try:
                self._content_layout.insertWidget(
                    self._content_layout.count() - 1,
                    self._build_map_grid(map_stats, is_pro_overview),
                )
            except Exception as e:
                logger.error("map grid failed: %s", e)

        if not is_pro_overview and sw and (sw.get("strengths") or sw.get("weaknesses")):
            try:
                self._content_layout.insertWidget(
                    self._content_layout.count() - 1,
                    self._build_strengths_weaknesses(sw),
                )
            except Exception as e:
                logger.error("strengths/weaknesses failed: %s", e)

        if utility and utility.get("user"):
            try:
                self._content_layout.insertWidget(
                    self._content_layout.count() - 1,
                    self._build_utility(utility, is_pro_overview),
                )
            except Exception as e:
                logger.error("utility section failed: %s", e)

        self._body_stack.setCurrentIndex(self._page_content)

    # ── Section builders ──

    def _build_hero(self, history: list, utility: dict) -> QWidget:
        ratings = [
            float(h.get("rating") or 0)
            for h in (history or [])
            if h.get("rating") is not None
        ]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        # Aggregate K/D and ADR from history if present
        kds = [float(h.get("kd_ratio") or 0) for h in (history or []) if h.get("kd_ratio")]
        adrs = [float(h.get("avg_adr") or 0) for h in (history or []) if h.get("avg_adr")]
        kasts = [float(h.get("avg_kast") or 0) for h in (history or []) if h.get("avg_kast")]

        avg_kd = sum(kds) / len(kds) if kds else 0.0
        avg_adr = sum(adrs) / len(adrs) if adrs else 0.0
        avg_kast = sum(kasts) / len(kasts) if kasts else 0.0

        stats: list[HeroStat] = [
            HeroStat(
                f"{avg_rating:.2f}" if ratings else "—",
                "Avg rating",
                _rating_sentiment(avg_rating) if ratings else "neutral",
            ),
            HeroStat(f"{len(ratings)}" if ratings else "0", "Matches", "neutral"),
            HeroStat(
                f"{avg_kd:.2f}" if kds else "—",
                "K / D",
                _kd_sentiment(avg_kd) if kds else "neutral",
            ),
            HeroStat(
                f"{avg_adr:.0f}" if adrs else "—",
                "ADR",
                "positive" if avg_adr >= 70 else "negative" if avg_adr < 50 else "neutral",
            ),
            HeroStat(
                f"{avg_kast * 100:.0f}%" if kasts else "—",
                "KAST",
                "positive" if avg_kast >= 0.7 else "negative" if avg_kast < 0.5 else "neutral",
            ),
        ]
        return HeroStatsStrip(stats)

    def _build_trend(self, history: list, is_pro_overview: bool) -> Card:
        title = "Rating trend" + (" — pro reference" if is_pro_overview else "")
        card = Card(title=title, depth="raised")
        body = card.content_layout
        tokens = get_tokens()

        ratings = [
            float(h.get("rating") or 0)
            for h in (history or [])
            if h.get("rating") is not None
        ]
        if not ratings:
            self._add_body_label(body, "Not enough data for trend analysis.", muted=True)
            return card

        avg_r = sum(ratings) / len(ratings)
        min_r = min(ratings)
        max_r = max(ratings)
        recent = ratings[-5:] if len(ratings) >= 5 else ratings
        avg_recent = sum(recent) / len(recent)

        if avg_recent > avg_r + 0.05:
            arrow = "▲"
            arrow_color = tokens.success
            sub = "Improving"
        elif avg_recent < avg_r - 0.05:
            arrow = "▼"
            arrow_color = tokens.error
            sub = "Declining"
        else:
            arrow = "─"
            arrow_color = tokens.text_secondary
            sub = "Stable"

        # Strip layout: average · range · recent · trend arrow
        strip = QHBoxLayout()
        strip.setContentsMargins(0, 0, 0, 0)
        strip.setSpacing(tokens.spacing_xxl)

        strip.addWidget(self._stat_block(f"{avg_r:.2f}", "AVERAGE"))
        strip.addWidget(
            self._stat_block(f"{min_r:.2f} — {max_r:.2f}", "RANGE", mono=True)
        )
        strip.addWidget(
            self._stat_block(
                f"{avg_recent:.2f}", f"LAST {len(recent)}", color_value=tokens.text_primary
            )
        )

        trend_block = self._stat_block(
            f"{arrow}  {sub}", "TREND", color_value=arrow_color
        )
        strip.addWidget(trend_block)
        strip.addStretch(1)

        wrapper = QWidget()
        wrapper.setLayout(strip)
        body.addWidget(wrapper)
        return card

    def _build_map_grid(self, map_stats: dict, is_pro_overview: bool) -> Card:
        title = "Per-map performance" + (
            " — pro reference" if is_pro_overview else ""
        )
        card = Card(title=title, depth="raised")
        body = card.content_layout
        tokens = get_tokens()

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(tokens.spacing_md)
        cols = 3

        for idx, (map_name, stats) in enumerate(map_stats.items()):
            grid.addWidget(self._build_map_tile(map_name, stats), idx // cols, idx % cols)

        body.addWidget(grid_widget)
        return card

    def _build_map_tile(self, map_name: str, stats: dict) -> QFrame:
        tokens = get_tokens()
        tile = QFrame()
        tile.setObjectName("dashboard_card")
        tile.setProperty("depth", "flat")

        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(
            tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm
        )
        tile_layout.setSpacing(2)

        name = QLabel(map_name.replace("de_", "").upper())
        Typography.apply(name, "caption")
        name.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        tile_layout.addWidget(name)

        rating_value = float(stats.get("rating") or 0)
        rating_label_widget = QLabel(f"{rating_value:.2f}")
        rating_label_widget.setFont(Typography.font("h1"))
        rating_label_widget.setStyleSheet(
            f"color: {rating_color(rating_value).name()}; background: transparent;"
        )
        tile_layout.addWidget(rating_label_widget)

        adr = float(stats.get("adr") or 0)
        kd = float(stats.get("kd") or 0)
        detail = QLabel(f"K/D {kd:.2f}    ADR {adr:.0f}")
        detail.setFont(Typography.font("mono"))
        detail.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        tile_layout.addWidget(detail)

        n_matches = int(stats.get("matches") or 0)
        meta = QLabel(f"{n_matches} matches  ·  {rating_label(rating_value)}")
        meta.setFont(Typography.font("caption"))
        meta.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        tile_layout.addWidget(meta)
        return tile

    def _build_strengths_weaknesses(self, sw: dict) -> Card:
        card = Card(title="Strengths & weaknesses vs pro", depth="raised")
        body = card.content_layout
        tokens = get_tokens()

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_xl)

        row.addWidget(
            self._sw_column("Strengths", sw.get("strengths") or [], tokens.success)
        )
        row.addWidget(
            self._sw_column(
                "Weaknesses", sw.get("weaknesses") or [], tokens.error, sign_inverse=True
            )
        )
        row.addStretch(1)

        wrapper = QWidget()
        wrapper.setLayout(row)
        body.addWidget(wrapper)
        return card

    def _sw_column(
        self,
        title: str,
        entries: list,
        color: str,
        sign_inverse: bool = False,
    ) -> QWidget:
        tokens = get_tokens()
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(tokens.spacing_xs)

        header = QLabel(title.upper())
        Typography.apply(header, "caption")
        header.setStyleSheet(f"color: {color}; background: transparent;")
        col.addWidget(header)

        if not entries:
            empty = QLabel("No data")
            empty.setFont(Typography.font("body"))
            empty.setStyleSheet(
                f"color: {tokens.text_tertiary}; background: transparent;"
            )
            col.addWidget(empty)
        else:
            for name, z in entries:
                display = name.replace("_", " ").title()
                sign = "−" if sign_inverse else "+"
                lbl = QLabel(f"{sign}{abs(z):.1f}σ   {display}")
                lbl.setFont(Typography.font("body"))
                lbl.setStyleSheet(
                    f"color: {color}; background: transparent;"
                )
                col.addWidget(lbl)

        wrapper = QWidget()
        wrapper.setLayout(col)
        return wrapper

    def _build_utility(self, utility: dict, is_pro_overview: bool) -> Card:
        title = "Utility effectiveness" + (
            " — pro reference" if is_pro_overview else " vs pro"
        )
        card = Card(title=title, depth="raised")
        body = card.content_layout
        tokens = get_tokens()

        user = utility.get("user") or {}
        pro = utility.get("pro") or {}
        if not user or all((v or 0) == 0 for v in user.values()):
            self._add_body_label(body, "No utility data available yet.", muted=True)
            return card

        labels = {
            "he_damage": "HE damage / round",
            "molotov_damage": "Molotov damage / round",
            "smokes_per_round": "Smokes / round",
            "flash_blind_time": "Flash blind time",
            "flash_assists": "Flash assists",
            "unused_utility": "Unused utility",
        }
        for key, display_name in labels.items():
            user_val = float(user.get(key, 0) or 0)
            pro_val = float((pro or {}).get(key, 0) or 0)

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(tokens.spacing_md)

            name = QLabel(display_name)
            name.setFont(Typography.font("body"))
            name.setFixedWidth(220)
            name.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent;"
            )
            row.addWidget(name)

            value = QLabel(f"{user_val:.2f}")
            value.setFont(Typography.font("mono"))
            value.setFixedWidth(80)
            value.setStyleSheet(
                f"color: {tokens.text_primary}; background: transparent;"
            )
            row.addWidget(value)

            comparison_color = tokens.text_tertiary
            comparison_text = ""
            if pro_val > 0 and not is_pro_overview:
                pct = ((user_val - pro_val) / pro_val) * 100
                if pct > 10:
                    comparison_text = f"▲ {pct:+.0f}% vs pro"
                    # "More" is good for damage stats, bad for unused — keep neutral
                    comparison_color = tokens.success if key != "unused_utility" else tokens.error
                elif pct < -10:
                    comparison_text = f"▼ {pct:+.0f}% vs pro"
                    comparison_color = tokens.error if key != "unused_utility" else tokens.success
                else:
                    comparison_text = "≈ pro level"
                    comparison_color = tokens.text_secondary
            comparison = QLabel(comparison_text)
            comparison.setFont(Typography.font("mono"))
            comparison.setStyleSheet(
                f"color: {comparison_color}; background: transparent;"
            )
            row.addWidget(comparison, 1)

            wrapper = QWidget()
            wrapper.setLayout(row)
            body.addWidget(wrapper)

        return card

    # ── Helpers ──

    def _stat_block(
        self,
        value: str,
        label: str,
        mono: bool = False,
        color_value: str | None = None,
    ) -> QWidget:
        tokens = get_tokens()
        block = QWidget()
        col = QVBoxLayout(block)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)

        v = QLabel(value)
        if mono:
            v.setFont(Typography.font("mono"))
        else:
            v.setFont(Typography.font("h1"))
        v.setStyleSheet(
            f"color: {color_value or tokens.text_primary}; background: transparent;"
        )
        col.addWidget(v)

        l = QLabel(label)
        Typography.apply(l, "caption")
        l.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        col.addWidget(l)
        return block

    def _add_body_label(self, layout, text: str, muted: bool = False) -> None:
        tokens = get_tokens()
        lbl = QLabel(text)
        lbl.setFont(Typography.font("body"))
        lbl.setStyleSheet(
            f"color: {tokens.text_tertiary if muted else tokens.text_primary}; "
            f"background: transparent;"
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

    def _update_count_chip(self, count: int) -> None:
        self._count_chip.set_label(f"{count} matches")
        self._count_chip.set_severity("online" if count > 0 else "neutral")

    def _clear_content(self) -> None:
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
