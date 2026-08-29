"""Performance — aggregate analytics dashboard (frame 12).

Composition:
    Title rail        Advanced Analytics       47 personal demos analyzed
    Pro-overview banner   (visible when no personal data yet)
    Hero stats row    Avg rating · Matches · K/D · ADR · KAST
    Context strip     percentile rank vs the pro cohort (Cluster F)
    Row 1 (50/50)     Rating Trend card (label/value rows + RatingSparkline)
                      | Strengths & Weaknesses (vs Pro Average) card
    Per-map card      3-column grid of MapTile widgets.
    Utility card      6 metric rows (value + tinted vs-pro delta) left,
                      grouped you-vs-pro UtilityBarChart right.

Body is housed in a QStackedWidget so loading / empty / data swaps
don't push the title rail around.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
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
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import map_short_name
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.viewmodels.performance_vm import PerformanceViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.rating_sparkline import RatingSparkline
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.utility_bar_chart import UtilityBarChart
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.hero_stats_strip import (
    HeroStat,
    HeroStatsStrip,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.map_tile import MapTile
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
        self._vm.context_changed.connect(self._on_context)
        self._vm.error_changed.connect(self._on_error)
        self._vm.is_loading_changed.connect(self._on_loading)

        self._latest_context: dict = {}
        self._demo_count: int = 0
        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self) -> None:
        self._show_loading()
        self._vm.load_performance()

    def on_leave(self) -> None:
        return

    def retranslate(self) -> None:
        self._title_label.setText(i18n.get_text("advanced_analytics"))
        self._update_count_caption(self._demo_count)

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
        # Frame 12: plain right-aligned caption, not a chip.
        self._count_caption = QLabel("")
        Typography.apply(self._count_caption, "caption")
        self._count_caption.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        title_row.addWidget(self._count_caption)
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
        self._empty_state.action_clicked.connect(lambda: self._navigate("home"))
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

    def _on_context(self, context: dict) -> None:
        """Cluster F — store the latest percentile dict.

        R4 MED contract: the VM emits ``context_changed`` BEFORE
        ``data_changed`` (direct same-thread connections), so this cache is
        already fresh when the data_changed slot rebuilds the UI and
        ``_build_context_strip`` reads it. The previous ordering (data
        first) rendered the prior load's percentiles on every visit.
        """
        self._latest_context = dict(context or {})

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
            self._update_count_caption(0)
            self._pro_banner.setVisible(False)
            return

        self._pro_banner.setVisible(is_pro_overview)
        self._update_count_caption(len(history) if history else 0)

        # Hero strip — top-of-page snapshot.
        self._content_layout.insertWidget(
            self._content_layout.count() - 1,
            self._build_hero(history, utility),
        )

        # Cluster F — context strip: percentile rank vs the pro cohort.
        # Lives directly under the hero strip so the user sees their
        # absolute number and its rank-against-pros side by side.
        self._content_layout.insertWidget(
            self._content_layout.count() - 1,
            self._build_context_strip(),
        )

        # Row 1 (frame 12): Rating Trend | Strengths & Weaknesses, 50/50.
        # When S&W has no data the trend card takes the full row width.
        trend_card = None
        try:
            trend_card = self._build_trend(history, is_pro_overview)
        except Exception as e:
            logger.error("trend section failed: %s", e)

        sw_card = None
        if not is_pro_overview and sw and (sw.get("strengths") or sw.get("weaknesses")):
            try:
                sw_card = self._build_strengths_weaknesses(sw)
            except Exception as e:
                logger.error("strengths/weaknesses failed: %s", e)

        if trend_card is not None or sw_card is not None:
            row1 = QWidget()
            row1_layout = QHBoxLayout(row1)
            row1_layout.setContentsMargins(0, 0, 0, 0)
            row1_layout.setSpacing(get_tokens().spacing_lg)
            for half in (trend_card, sw_card):
                if half is not None:
                    row1_layout.addWidget(half, 1)
            self._content_layout.insertWidget(self._content_layout.count() - 1, row1)

        if map_stats:
            try:
                self._content_layout.insertWidget(
                    self._content_layout.count() - 1,
                    self._build_map_grid(map_stats, is_pro_overview),
                )
            except Exception as e:
                logger.error("map grid failed: %s", e)

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
            float(h.get("rating") or 0) for h in (history or []) if h.get("rating") is not None
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

    def _build_context_strip(self) -> QWidget:
        """Cluster F — small Card showing percentile rank vs pro cohort.

        Bound to ``self._latest_context`` so future context_changed
        emissions repaint this widget in place. The widget is rebuilt
        on each load_performance() call (the parent layout clears
        between loads), so capturing the dict snapshot at construction
        time is fine.
        """
        tokens = get_tokens()
        ctx = self._latest_context or {}
        card = Card(title="Versus pro cohort", depth="raised")
        body = card.content_layout

        if not ctx:
            self._add_body_label(
                body,
                "No pro percentile data — the pro cohort is empty or you have " "no matches yet.",
                muted=True,
            )
            return card

        def _fmt_pct(p: float) -> str:
            return f"{p * 100:.0f}th %"

        def _sentiment(p: float) -> str:
            if p >= 0.66:
                return tokens.success
            if p <= 0.33:
                return tokens.error
            return tokens.text_secondary

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_lg)

        for key, label in (
            ("rating", "Rating"),
            ("kd", "K/D"),
            ("adr", "ADR"),
            ("kast", "KAST"),
        ):
            p = ctx.get(key)
            if p is None:
                continue
            cell = QVBoxLayout()
            cell.setContentsMargins(0, 0, 0, 0)
            value_lbl = QLabel(_fmt_pct(float(p)))
            value_lbl.setFont(
                Typography.font("stat")
            )  # R4 LOW: "h3" is not a role — it silently fell back to 13px body
            value_lbl.setStyleSheet(f"color: {_sentiment(float(p))}; background: transparent;")
            label_lbl = QLabel(label)
            label_lbl.setFont(Typography.font("caption"))
            label_lbl.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
            cell.addWidget(value_lbl)
            cell.addWidget(label_lbl)
            wrap = QWidget()
            wrap.setLayout(cell)
            row.addWidget(wrap)
        row.addStretch(1)
        body.addLayout(row)
        return card

    def _build_trend(self, history: list, is_pro_overview: bool) -> Card:
        title = i18n.get_text("perf.rating_trend", "Rating Trend") + (
            " — pro reference" if is_pro_overview else ""
        )
        card = Card(title=title, depth="raised")
        body = card.content_layout
        tokens = get_tokens()

        ratings = [
            float(h.get("rating") or 0) for h in (history or []) if h.get("rating") is not None
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
            arrow, trend_color = "▲", tokens.success
            trend_word = i18n.get_text("perf.improving", "Improving")
        elif avg_recent < avg_r - 0.05:
            arrow, trend_color = "▼", tokens.error
            trend_word = i18n.get_text("perf.declining", "Declining")
        else:
            arrow, trend_color = "─", tokens.text_secondary
            trend_word = i18n.get_text("perf.stable", "Stable")

        # Frame-12 rows. The average is an informational value (tokens.info):
        # the frame's green fill would break the >1.10 rating-color contract.
        rows = (
            (
                i18n.get_text("perf.matches_analyzed", "Matches analyzed:"),
                f"{len(history)}",
                tokens.text_primary,
            ),
            (
                i18n.get_text("perf.average_rating", "Average rating:"),
                f"{avg_r:.2f}",
                tokens.accent_primary,  # Q3: the player's headline stat speaks the accent
            ),
            (
                i18n.get_text("perf.range", "Range:"),
                f"{min_r:.2f} — {max_r:.2f}",
                tokens.text_primary,
            ),
            (
                i18n.get_text("perf.recent_trend", "Recent trend:"),
                f"{avg_recent:.2f}  {arrow} {trend_word}",
                trend_color,
            ),
        )
        for label, value, color in rows:
            body.addWidget(self._kv_row(label, value, color))

        # Sparkline strip: "Last N matches" caption + last-8 rating trend.
        tail = ratings[-8:]
        if len(tail) >= 2:
            strip = QHBoxLayout()
            strip.setContentsMargins(0, tokens.spacing_sm, 0, 0)
            strip.setSpacing(tokens.spacing_md)
            caption = QLabel(
                i18n.get_text("perf.last_matches", "Last {n} matches").format(n=len(tail))
            )
            Typography.apply(caption, "caption")
            caption.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
            strip.addWidget(caption, 0, Qt.AlignBottom)
            spark = RatingSparkline()
            spark.set_values(tail)
            # Default 64px squeezes the three HLTV ref captions into each
            # other when the data spans 0.71–1.34 — give them air.
            spark.setMinimumHeight(100)
            strip.addWidget(spark, 1)
            wrap = QWidget()
            wrap.setLayout(strip)
            body.addWidget(wrap)
        return card

    def _build_map_grid(self, map_stats: dict, is_pro_overview: bool) -> Card:
        title = i18n.get_text("perf.per_map_title", "Per-Map Performance") + (
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
            # Payload keys are demo-style ("de_mirage") — frame shows "Mirage".
            display = map_short_name(str(map_name)).title()
            tile = MapTile()
            tile.set_data(
                display,
                float(stats.get("rating") or 0),
                float(stats.get("adr") or 0),
                float(stats.get("kd") or 0),
                int(stats.get("matches") or 0),
            )
            grid.addWidget(tile, idx // cols, idx % cols)

        body.addWidget(grid_widget)
        return card

    def _build_strengths_weaknesses(self, sw: dict) -> Card:
        card = Card(
            title=i18n.get_text("perf.sw_title", "Strengths & Weaknesses (vs Pro Average)"),
            depth="raised",
        )
        body = card.content_layout
        tokens = get_tokens()

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_xl)

        row.addWidget(
            self._sw_column(
                i18n.get_text("perf.strengths", "Strengths"),
                sw.get("strengths") or [],
                tokens.success,
                i18n.get_text("perf.above_avg", "above avg"),
                "+",
            ),
            1,
        )
        row.addWidget(
            self._sw_column(
                i18n.get_text("perf.weaknesses", "Weaknesses"),
                sw.get("weaknesses") or [],
                tokens.error,
                i18n.get_text("perf.below_avg", "below avg"),
                "-",
            ),
            1,
        )

        wrapper = QWidget()
        wrapper.setLayout(row)
        body.addWidget(wrapper)
        return card

    def _sw_column(
        self,
        title: str,
        entries: list,
        color: str,
        relation: str,
        sign: str,
    ) -> QWidget:
        """One frame-12 column: tinted bold header + "+1.8 above avg — X" rows."""
        tokens = get_tokens()
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(tokens.spacing_xs)

        header = QLabel(title)
        header.setFont(Typography.font("body", QFont.Bold))
        header.setStyleSheet(f"color: {color}; background: transparent;")
        col.addWidget(header)

        if not entries:
            empty = QLabel("No data")
            empty.setFont(Typography.font("body"))
            empty.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
            col.addWidget(empty)
        else:
            for name, z in entries:
                # Analytics ships curated display names ("Clutch Win %") —
                # only raw fallback keys need their underscores spaced out
                # (.title() would mangle "HS %" into "Hs %").
                display = str(name).replace("_", " ")
                lbl = QLabel(f"{sign}{abs(float(z)):.1f} {relation} — {display}")
                lbl.setFont(Typography.font("body"))
                lbl.setStyleSheet(f"color: {color}; background: transparent;")
                col.addWidget(lbl)
        col.addStretch(1)

        wrapper = QWidget()
        wrapper.setLayout(col)
        return wrapper

    def _build_utility(self, utility: dict, is_pro_overview: bool) -> Card:
        title = (
            "Utility effectiveness — pro reference"
            if is_pro_overview
            else i18n.get_text("perf.utility_title", "Utility Effectiveness (vs Pro)")
        )
        card = Card(title=title, depth="raised")
        body = card.content_layout
        tokens = get_tokens()

        user = utility.get("user") or {}
        pro = utility.get("pro") or {}
        if not user or all((v or 0) == 0 for v in user.values()):
            self._add_body_label(body, "No utility data available yet.", muted=True)
            return card

        per_match = i18n.get_text("perf.per_match", "/match")
        per_round = i18n.get_text("perf.per_round", "/round")
        # (payload key, i18n key, fallback, value formatter, higher-is-waste)
        specs = (
            ("he_damage", "perf.he_damage", "HE Damage/Round:", lambda v: f"{v:.1f}", False),
            (
                "molotov_damage",
                "perf.molotov_damage",
                "Molotov Damage/Round:",
                lambda v: f"{v:.1f}",
                False,
            ),
            ("smokes_per_round", "perf.smokes", "Smokes/Round:", lambda v: f"{v:.2f}", False),
            (
                "flash_blind_time",
                "perf.flash_blind",
                "Flash Blind Time:",
                lambda v: f"{v:.1f}s",
                False,
            ),
            (
                "flash_assists",
                "perf.flash_assists",
                "Flash Assists:",
                lambda v: f"{v:.1f}{per_match}",
                False,
            ),
            (
                "unused_utility",
                "perf.unused_utility",
                "Unused Utility:",
                lambda v: f"{v:.1f}{per_round}",
                True,
            ),
        )

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(tokens.spacing_sm)
        for key, label_key, fallback, fmt, is_waste in specs:
            left.addWidget(
                self._utility_row(
                    i18n.get_text(label_key, fallback),
                    float(user.get(key, 0) or 0),
                    float(pro.get(key, 0) or 0),
                    fmt,
                    is_waste,
                    is_pro_overview,
                )
            )
        left.addStretch(1)
        left_wrap = QWidget()
        left_wrap.setLayout(left)

        columns = QHBoxLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(tokens.spacing_xl)
        columns.addWidget(left_wrap, 1)

        # Right column: grouped you-vs-pro bars for the frame-12 quartet.
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(tokens.spacing_sm)
        chart_caption = QLabel(
            i18n.get_text("perf.vs_pro_grouped", "You vs Pro Average — grouped bars")
        )
        # body-bold, not the caption QFont role — that role uppercases and
        # letterspaces, but the frame caption is mixed-case.
        chart_caption.setFont(Typography.font("body", QFont.Bold))
        chart_caption.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        right.addWidget(chart_caption)

        chart_keys = (
            ("perf.bar_he", "HE", "he_damage"),
            ("perf.bar_moly", "Moly", "molotov_damage"),
            ("perf.bar_flash", "Flash", "flash_assists"),
            ("perf.bar_waste", "Waste", "unused_utility"),
        )
        if not is_pro_overview and any(float(pro.get(k, 0) or 0) > 0 for _, _, k in chart_keys):
            chart = UtilityBarChart()
            chart_rows: list[tuple] = []
            for label_key, fallback, key in chart_keys:
                label = i18n.get_text(label_key, fallback)
                you_v = float(user.get(key, 0) or 0)
                pro_v = float(pro.get(key, 0) or 0)
                if key == "unused_utility":
                    # Frame 12 tints the waste you-bar error red.
                    chart_rows.append((label, you_v, pro_v, tokens.error))
                else:
                    chart_rows.append((label, you_v, pro_v))
            chart.set_rows(chart_rows)
            right.addWidget(chart)
        else:
            # FIELD-GAP: no pro utility baseline in the DB yet (requires pro
            # demos ingested) — degrade to the same "—" the metric rows use.
            self._add_body_label(right, "—", muted=True)
        right.addStretch(1)
        right_wrap = QWidget()
        right_wrap.setLayout(right)
        columns.addWidget(right_wrap, 1)

        columns_wrap = QWidget()
        columns_wrap.setLayout(columns)
        body.addWidget(columns_wrap)
        return card

    def _utility_row(
        self,
        label: str,
        user_val: float,
        pro_val: float,
        fmt,
        is_waste: bool,
        is_pro_overview: bool,
    ) -> QWidget:
        """Frame-12 utility metric row: label · bold mono value · tinted delta.

        The waste row's value is warning-tinted (frame 12) since a high
        number is a problem even before the vs-pro comparison lands.
        """
        tokens = get_tokens()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)

        name = QLabel(label)
        name.setFont(Typography.font("body"))
        name.setFixedWidth(220)
        name.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        row.addWidget(name)

        value = QLabel(fmt(user_val))
        value.setFont(Typography.font("mono", QFont.Bold))
        value.setFixedWidth(110)
        value.setStyleSheet(
            f"color: {tokens.warning if is_waste else tokens.text_primary}; "
            f"background: transparent;"
        )
        row.addWidget(value)

        delta_text, delta_color = self._utility_delta(user_val, pro_val, is_waste, is_pro_overview)
        delta = QLabel(delta_text)
        delta.setFont(Typography.font("mono"))
        delta.setStyleSheet(f"color: {delta_color}; background: transparent;")
        row.addWidget(delta, 1)

        wrap = QWidget()
        wrap.setLayout(row)
        return wrap

    def _utility_delta(
        self, user_val: float, pro_val: float, is_waste: bool, is_pro_overview: bool
    ) -> tuple[str, str]:
        """Compose the vs-pro delta caption + its color.

        Band: within ±5% of the pro baseline reads "≈ pro level" — frame 12
        tags +8% as a real ▲, so the previous ±10% band was too wide. The
        sign follows SENTIMENT, not the raw delta: the frame presents more
        waste than pro as "▼ -31% vs pro (waste)".
        """
        tokens = get_tokens()
        if is_pro_overview:
            return "", tokens.text_tertiary
        if pro_val <= 0:
            # FIELD-GAP: pro baseline absent for this metric (no pro demos
            # ingested) — placeholder rather than a fake comparison.
            return "—", tokens.text_tertiary

        pct = ((user_val - pro_val) / pro_val) * 100
        if abs(pct) <= 5:
            return i18n.get_text("perf.pro_level", "≈ pro level"), tokens.text_secondary

        vs_pro = i18n.get_text("perf.vs_pro", "vs pro")
        good = (pct < 0) if is_waste else (pct > 0)
        arrow = "▲" if good else "▼"
        sign = "+" if good else "-"
        text = f"{arrow} {sign}{abs(pct):.0f}% {vs_pro}"
        if is_waste and not good:
            text += f" {i18n.get_text('perf.waste', '(waste)')}"
        return text, tokens.success if good else tokens.error

    # ── Helpers ──

    def _kv_row(self, label: str, value: str, value_color: str) -> QWidget:
        """Frame-12 card row: secondary label column, bold value at a fixed tab."""
        tokens = get_tokens()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)

        lbl = QLabel(label)
        lbl.setFont(Typography.font("body"))
        lbl.setFixedWidth(180)
        lbl.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        row.addWidget(lbl)

        val = QLabel(value)
        val.setFont(Typography.font("body", QFont.Bold))
        val.setStyleSheet(f"color: {value_color}; background: transparent;")
        row.addWidget(val, 1)

        wrap = QWidget()
        wrap.setLayout(row)
        return wrap

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

    def _update_count_caption(self, count: int) -> None:
        self._demo_count = int(count)
        word = i18n.get_text("perf.demos_analyzed", "personal demos analyzed")
        self._count_caption.setText(f"{self._demo_count} {word}" if self._demo_count else "")

    def _clear_content(self) -> None:
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
