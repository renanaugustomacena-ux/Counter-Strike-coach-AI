"""Match Detail — tabbed drill-down for one analyzed demo (frames 09/10/11).

Composition:
    Header rail   ← Back   |  Match Detail — {map}  (h1)
    Tabs          Overview · Rounds · Economy · Highlights (underline style)
    Overview      meta row · 5 hero tiles · round dot strip · HLTV 2.0
                  two-column MetricBarRow grid · Kill Enrichment band ·
                  Utility Per Round band · MonoFooter
    Rounds        per-round table
    Economy       equipment chart
    Highlights    momentum + coaching insights

The screen renders exclusively from ``MatchDetailViewModel.data_changed``
payloads; the last payload is kept so ``retranslate()`` can rebuild in the
new language without a DB round-trip.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import extract_map_name
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color, rating_label
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.viewmodels.match_detail_vm import MatchDetailViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.economy_chart import EconomyChart
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.momentum_chart import MomentumChart
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.metric_bar_row import MetricBarRow
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mono_footer import MonoFooter
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


def _sentiment_hex(sentiment: str) -> str:
    tokens = get_tokens()
    if sentiment == "positive":
        return tokens.success
    if sentiment == "negative":
        return tokens.error
    return tokens.text_primary


def _pct_color(frac: float) -> QColor:
    """Win-percentage semantics: >= 60% good, < 40% bad, else mid."""
    tokens = get_tokens()
    if frac >= 0.6:
        return QColor(tokens.success)
    if frac < 0.4:
        return QColor(tokens.error)
    return QColor(tokens.warning)


def _mono_font(caption: bool = False):
    font = Typography.font("mono")
    if caption:
        font.setPointSize(get_tokens().font_size_caption)
    return font


class MatchDetailScreen(QWidget):
    """Tabbed match detail screen (frames 09/10/11)."""

    # (demo_name, demo tick) — emitted by Highlights critical-moment cards.
    # The app orchestrator wires this to the Tactical Viewer deep-link.
    moment_selected = Signal(str, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._vm = MatchDetailViewModel()
        self._vm.data_changed.connect(self._on_data)
        self._vm.error_changed.connect(self._on_error)
        self._demo_name: str = ""
        self._payload: tuple | None = None
        self._tab_index: dict[str, int] = {}
        self._build_ui()

    # ── Lifecycle ──

    def load_demo(self, demo_name: str) -> None:
        """Called externally (from match list / dashboard recent strip)."""
        self._demo_name = demo_name
        self._payload = None
        self._title_label.setText(self._compose_title(demo_name))
        self._tabs.setVisible(False)
        self._empty_state.set_title(i18n.get_text("md_loading", "Loading match details…"))
        self._empty_state.set_description("")
        self._empty_state.set_cta_text("")
        self._empty_state.setVisible(True)
        self._vm.load_detail(demo_name)

    def on_enter(self) -> None:
        if self._demo_name:
            self.load_demo(self._demo_name)

    def retranslate(self) -> None:
        self._back_btn.setText(i18n.get_text("md_back", "← Back"))
        self._title_label.setText(self._compose_title(self._demo_name))
        if self._payload is not None:
            self._on_data(*self._payload)

    def set_active_tab(self, name: str) -> None:
        """Activate a tab by canonical name (overview|rounds|economy|highlights).

        Used by the screenshot harness (``--md-tab``) and safe to call any
        time — unknown names and not-yet-built tabs are ignored.
        """
        index = self._tab_index.get(str(name).strip().lower())
        if index is not None and 0 <= index < self._tabs.count():
            self._tabs.setCurrentIndex(index)

    # ── UI Construction ──

    def _compose_title(self, demo_name: str) -> str:
        base = i18n.get_text("md_title", "Match Detail")
        map_name = extract_map_name(demo_name) if demo_name else ""
        if map_name and map_name != "Unknown Map":
            return f"{base} — {map_name}"
        return base

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

        self._back_btn = make_button(
            i18n.get_text("md_back", "← Back"), variant="secondary", fixed_width=88
        )
        self._back_btn.setFixedHeight(32)
        self._back_btn.clicked.connect(lambda: self._navigate("match_history"))
        header.addWidget(self._back_btn)

        self._title_label = QLabel(self._compose_title(""))
        Typography.apply(self._title_label, "h1")
        header.addWidget(self._title_label, 1)

        root.addLayout(header)

        # ── Empty / loading state ──
        self._empty_state = EmptyState(
            icon_text="◎",
            title=i18n.get_text("md_loading", "Loading match details…"),
            description="",
        )
        self._empty_state.setVisible(False)
        # R4 LOW: connect ONCE — reconnecting on every failed load
        # accumulated duplicate slots (N failures → N navigations per click).
        self._empty_state.action_clicked.connect(lambda: self._navigate("match_history"))
        root.addWidget(self._empty_state)

        # ── Tabs (default underline variant per frame 09) ──
        self._tabs = QTabWidget()
        self._tabs.tabBar().setDrawBase(False)
        # Frames place tab content on the flat base surface — suppress the
        # template's raised translucent pane without introducing literals.
        self._tabs.setStyleSheet("QTabWidget::pane { border: none; background: transparent; }")
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
        # Kept verbatim so retranslate() can rebuild in the active language.
        # ``hltv`` (cross-match aggregate from analytics.get_hltv2_breakdown)
        # stays in the VM contract; frame 09 renders the per-match component
        # fields carried in ``stats`` instead.
        self._payload = (stats, rounds, insights, hltv)
        self._empty_state.setVisible(False)
        self._tabs.setVisible(True)

        if not stats and not rounds:
            self._tabs.setVisible(False)
            self._empty_state.set_title(
                i18n.get_text("md_no_data_title", "No match data available")
            )
            self._empty_state.set_description(
                i18n.get_text(
                    "md_no_data_desc",
                    "The demo may still be processing, or analysis hasn't completed.",
                )
            )
            self._empty_state.set_cta_text(
                i18n.get_text("md_back_history", "Back to Match History")
            )
            self._empty_state.setVisible(True)
            return

        # Header
        demo_name = stats.get("demo_name") or self._demo_name
        self._demo_name = demo_name
        self._title_label.setText(self._compose_title(demo_name))

        # Tabs — drop old pages explicitly (QTabWidget.clear() only detaches)
        prev_index = self._tabs.currentIndex()
        while self._tabs.count():
            page = self._tabs.widget(0)
            self._tabs.removeTab(0)
            if page is not None:
                page.deleteLater()
        self._tab_index = {}

        def _add_tab(key: str, widget: QWidget, label_key: str, fallback: str) -> None:
            self._tab_index[key] = self._tabs.count()
            self._tabs.addTab(widget, i18n.get_text(label_key, fallback))

        _add_tab("overview", self._build_overview(stats, rounds), "md_tab_overview", "Overview")
        if rounds:
            _add_tab("rounds", self._build_rounds(rounds), "md_tab_rounds", "Rounds")
            _add_tab("economy", self._build_economy(rounds), "md_tab_economy", "Economy")
        _add_tab(
            "highlights",
            self._build_highlights(rounds, insights),
            "md_tab_highlights",
            "Highlights",
        )
        if 0 <= prev_index < self._tabs.count():
            self._tabs.setCurrentIndex(prev_index)

    def _on_error(self, msg: str) -> None:
        if not msg:
            return
        self._tabs.setVisible(False)
        self._empty_state.set_title(i18n.get_text("md_error_title", "Couldn't load match"))
        self._empty_state.set_description(str(msg))
        self._empty_state.set_cta_text(i18n.get_text("md_back_history", "Back to Match History"))
        self._empty_state.setVisible(True)

    def _navigate(self, screen_name: str) -> None:
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen(screen_name)

    # ── Tab: Overview (frame 09) ──

    def _build_overview(self, stats: dict, rounds: list) -> QWidget:
        tokens = get_tokens()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, tokens.spacing_md, 0, tokens.spacing_md)
        layout.setSpacing(tokens.spacing_lg)

        layout.addLayout(self._build_meta_row(stats, rounds))
        layout.addWidget(self._build_hero_row(stats))
        if rounds:
            layout.addLayout(self._build_round_strip(rounds))

        layout.addWidget(self._section_title(i18n.get_text("md_hltv_title", "HLTV 2.0 Components")))
        layout.addLayout(self._build_hltv_grid(stats))

        layout.addWidget(
            self._section_title(i18n.get_text("md_enrich_title", "Kill Enrichment"))
        )
        layout.addWidget(self._build_enrichment_band(stats, rounds))

        layout.addWidget(
            self._section_title(i18n.get_text("md_util_title", "Utility Per Round"))
        )
        layout.addWidget(self._build_utility_band(stats))

        layout.addStretch(1)
        demo_name = stats.get("demo_name") or self._demo_name
        layout.addWidget(
            MonoFooter(
                i18n.get_text(
                    "md_footer_overview",
                    "PlayerMatchStats · demo_name={demo} · "
                    "rating_components from hltv_components JSON",
                ).format(demo=demo_name)
            )
        )
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _section_title(text: str) -> QLabel:
        tokens = get_tokens()
        label = QLabel(text)
        label.setFont(Typography.font("subtitle"))
        label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        return label

    def _build_meta_row(self, stats: dict, rounds: list) -> QHBoxLayout:
        tokens = get_tokens()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)

        demo_name = stats.get("demo_name") or self._demo_name
        date_str = _format_match_date(stats.get("match_date"))
        left_text = extract_map_name(demo_name)
        if date_str:
            left_text = f"{left_text}  |  {date_str}"
        left = QLabel(left_text)
        left.setFont(Typography.font("body"))
        left.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        row.addWidget(left)
        row.addStretch(1)

        # FIELD-GAP: demo file size is stored in no DB model, and duration is
        # only derivable from the per-match shard (MatchMetadata.tick_count /
        # tick_rate via match_data_manager) — neither is wired into
        # MatchDetailViewModel yet. The fixture supplies display-only values;
        # absent segments are simply omitted.
        segments: list[str] = []
        size_mb = stats.get("demo_size_mb")
        if size_mb:
            segments.append(i18n.get_text("md_meta_demo", "demo {size} MB").format(size=size_mb))
        if rounds:
            segments.append(i18n.get_text("md_meta_rounds", "{n} rounds").format(n=len(rounds)))
        duration_min = stats.get("duration_min")
        if duration_min:
            segments.append(i18n.get_text("md_meta_minutes", "{n} min").format(n=duration_min))
        right = QLabel(" · ".join(segments))
        right.setFont(_mono_font(caption=True))
        right.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        row.addWidget(right)
        return row

    def _build_hero_row(self, stats: dict) -> QWidget:
        tokens = get_tokens()
        rating = float(stats.get("rating") or 0.0)
        kd = float(stats.get("kd_ratio") or 0.0)
        adr = float(stats.get("avg_adr") or 0.0)
        kast = float(stats.get("avg_kast") or 0.0)
        hs = float(stats.get("avg_hs") or 0.0)

        tiles = [
            (
                f"{rating:.2f}",
                i18n.get_text("md_hero_rating", "Rating ({label})").format(
                    label=rating_label(rating)
                ),
                rating_color(rating).name(),
            ),
            (f"{kd:.2f}", i18n.get_text("md_hero_kd", "K/D Ratio"), _sentiment_hex(_kd_sentiment(kd))),
            (f"{adr:.1f}", i18n.get_text("md_hero_adr", "ADR"), _sentiment_hex(_adr_sentiment(adr))),
            (
                f"{kast * 100:.0f}%",
                i18n.get_text("md_hero_kast", "KAST"),
                _sentiment_hex(_kast_sentiment(kast)),
            ),
            (f"{hs * 100:.0f}%", i18n.get_text("md_hero_hs", "Headshot %"), tokens.text_primary),
        ]

        row_host = QWidget()
        row = QHBoxLayout(row_host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)
        for value, caption, color in tiles:
            row.addWidget(self._hero_tile(value, caption, color), 1)
        return row_host

    @staticmethod
    def _hero_tile(value: str, caption: str, color: str) -> QFrame:
        tokens = get_tokens()
        tile = QFrame()
        tile.setObjectName("dashboard_card")
        tile.setProperty("depth", "raised")
        style = tile.style()
        if style is not None:
            style.unpolish(tile)
            style.polish(tile)

        col = QVBoxLayout(tile)
        col.setContentsMargins(
            tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg
        )
        col.setSpacing(tokens.spacing_xs)

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setFont(Typography.font("stat"))
        value_label.setStyleSheet(f"color: {color}; background: transparent;")
        col.addWidget(value_label)

        caption_label = QLabel(caption)
        caption_label.setAlignment(Qt.AlignCenter)
        caption_label.setFont(Typography.font("body"))
        caption_label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        col.addWidget(caption_label)
        return tile

    def _build_round_strip(self, rounds: list) -> QHBoxLayout:
        tokens = get_tokens()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_xs)

        label = QLabel(i18n.get_text("md_rounds_label", "Rounds:"))
        label.setFont(Typography.font("body"))
        label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        row.addWidget(label)
        row.addSpacing(tokens.spacing_sm)

        prev_side = None
        for r in rounds:
            side = r.get("side")
            if prev_side is not None and side in ("CT", "T") and side != prev_side:
                divider = QFrame()
                divider.setFixedSize(1, 14)
                divider.setStyleSheet(f"background: {tokens.border_default};")
                row.addSpacing(tokens.spacing_xs)
                row.addWidget(divider)
                row.addSpacing(tokens.spacing_xs)
            if side in ("CT", "T"):
                prev_side = side
            won = bool(r.get("round_won"))
            dot = QLabel("●")
            dot.setAlignment(Qt.AlignCenter)
            dot.setFixedSize(14, 14)
            dot.setStyleSheet(
                f"color: {tokens.success if won else tokens.error}; "
                f"background: transparent; font-size: {tokens.font_size_caption}px;"
            )
            row.addWidget(dot)

        wins = sum(1 for r in rounds if r.get("round_won"))
        losses = len(rounds) - wins

        row.addSpacing(tokens.spacing_lg)
        score = QLabel(f"{wins} — {losses}")
        score.setFont(Typography.font("subtitle"))
        score.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        row.addWidget(score)

        t_rounds = [r for r in rounds if r.get("side") == "T"]
        ct_rounds = [r for r in rounds if r.get("side") == "CT"]
        if t_rounds and ct_rounds:
            t_w = sum(1 for r in t_rounds if r.get("round_won"))
            ct_w = sum(1 for r in ct_rounds if r.get("round_won"))
            caption_text = i18n.get_text(
                "md_score_final", "final · T-side {t} · CT-side {ct}"
            ).format(t=f"{t_w}-{len(t_rounds) - t_w}", ct=f"{ct_w}-{len(ct_rounds) - ct_w}")
        else:
            caption_text = i18n.get_text("md_score_final_plain", "final")
        caption = QLabel(caption_text)
        caption.setFont(Typography.font("body"))
        caption.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        row.addSpacing(tokens.spacing_sm)
        row.addWidget(caption)
        row.addStretch(1)
        return row

    def _build_hltv_grid(self, stats: dict) -> QGridLayout:
        tokens = get_tokens()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(tokens.spacing_xxl)
        grid.setVerticalSpacing(tokens.spacing_sm)

        def _value(key: str) -> float:
            return float(stats.get(key) or 0.0)

        # (i18n key, fallback, value, kind) — kinds drive format/frac/color.
        left_specs = [
            ("md_metric_impact", "Rating Impact", _value("rating_impact"), "rating"),
            ("md_metric_survival", "Rating Survival", _value("rating_survival"), "rating"),
            ("md_metric_kast", "Rating KAST", _value("rating_kast"), "rating"),
            ("md_metric_kpr", "Rating KPR", _value("rating_kpr"), "rating"),
            ("md_metric_adr", "Rating ADR", _value("rating_adr"), "rating"),
        ]
        right_specs = [
            ("md_metric_trade_ratio", "Trade Kill Ratio", _value("trade_kill_ratio"), "ratio"),
            ("md_metric_was_traded", "Was Traded", _value("was_traded_ratio"), "ratio"),
            ("md_metric_opening_win", "Opening Duel Win%", _value("opening_duel_win_pct"), "pct"),
            ("md_metric_clutch_win", "Clutch Win%", _value("clutch_win_pct"), "pct"),
            (
                "md_metric_aggression",
                "Positional Aggression",
                _value("positional_aggression_score"),
                "score",
            ),
        ]

        for col, specs in enumerate((left_specs, right_specs)):
            for row_idx, (key, fallback, value, kind) in enumerate(specs):
                bar = MetricBarRow()
                if kind == "rating":
                    text, frac, color = f"{value:.2f}", value / 1.5, rating_color(value)
                elif kind == "ratio":
                    text, frac, color = f"{value:.2f}", value, QColor(tokens.info)
                elif kind == "pct":
                    text, frac, color = f"{value * 100:.0f}%", value, _pct_color(value)
                else:  # "score" — stylistic 0-1 metric, mid-tone per frame
                    text, frac, color = f"{value:.2f}", value, QColor(tokens.warning)
                bar.set_metric(i18n.get_text(key, fallback), text, frac, color)
                grid.addWidget(bar, row_idx, col)
        return grid

    @staticmethod
    def _build_stat_band(cells: list[tuple[str, str, str, str]]) -> QFrame:
        """Sunken band of stat columns: (caption, value, value_color, sub)."""
        tokens = get_tokens()
        band = QFrame()
        band.setObjectName("surface_sunken")
        row = QHBoxLayout(band)
        row.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        row.setSpacing(tokens.spacing_xl)

        for caption, value, value_color, sub in cells:
            col = QVBoxLayout()
            col.setSpacing(tokens.spacing_xs)

            caption_label = QLabel(caption)
            caption_label.setFont(Typography.font("body"))
            caption_label.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent;"
            )
            col.addWidget(caption_label)

            value_label = QLabel(value)
            value_label.setFont(Typography.font("title"))
            value_label.setStyleSheet(f"color: {value_color}; background: transparent;")
            col.addWidget(value_label)

            if sub:
                sub_label = QLabel(sub)
                sub_label.setFont(_mono_font(caption=True))
                sub_label.setStyleSheet(
                    f"color: {tokens.text_tertiary}; background: transparent;"
                )
                col.addWidget(sub_label)
            col.addStretch(1)
            row.addLayout(col, 1)
        return band

    def _build_enrichment_band(self, stats: dict, rounds: list) -> QFrame:
        tokens = get_tokens()
        kills_total = int(round(float(stats.get("avg_kills") or 0.0)))

        def _pct_cell(key: str, label_key: str, fallback: str) -> tuple[str, str, str, str]:
            frac = float(stats.get(key) or 0.0)
            sub = ""
            if kills_total:
                sub = i18n.get_text("md_enrich_of_kills", "{n} of {total} kills").format(
                    n=int(round(frac * kills_total)), total=kills_total
                )
            return (
                i18n.get_text(label_key, fallback),
                f"{frac * 100:.0f}%",
                tokens.text_primary,
                sub,
            )

        cells = [
            _pct_cell("thrusmoke_kill_pct", "md_enrich_thrusmoke", "Thru-smoke kills"),
            _pct_cell("wallbang_kill_pct", "md_enrich_wallbang", "Wallbang kills"),
            _pct_cell("noscope_kill_pct", "md_enrich_noscope", "No-scope kills"),
            _pct_cell("blind_kill_pct", "md_enrich_blind", "Blind kills"),
        ]

        # Opening kills: computed from the rounds payload (RoundStats
        # opening_kill / opening_death / round_won are all real columns).
        if rounds:
            ok_rounds = [r for r in rounds if r.get("opening_kill")]
            ok = len(ok_rounds)
            ok_w = sum(1 for r in ok_rounds if r.get("round_won"))
            od = sum(1 for r in rounds if r.get("opening_death"))
            sub = i18n.get_text("md_enrich_ok_detail", "{w}W {l}L ({delta} OK delta)").format(
                w=ok_w, l=ok - ok_w, delta=f"{ok - od:+d}"
            )
            value = str(ok)
            color = tokens.success if ok > 0 else tokens.text_primary
        else:
            value, sub, color = "—", "", tokens.text_primary
        cells.append(
            (i18n.get_text("md_enrich_opening", "Opening Kills"), value, color, sub)
        )
        return self._build_stat_band(cells)

    def _build_utility_band(self, stats: dict) -> QFrame:
        tokens = get_tokens()
        he = float(stats.get("he_damage_per_round") or 0.0)
        molotov = float(stats.get("molotov_damage_per_round") or 0.0)
        smokes = float(stats.get("smokes_per_round") or 0.0)
        flash = float(stats.get("flash_assists") or 0.0)
        unused = float(stats.get("unused_utility_per_round") or 0.0)
        # Wasted utility reads as a warning once it crosses ~1 nade/round.
        unused_color = tokens.warning if unused >= 1.0 else tokens.text_primary

        cells = [
            (i18n.get_text("md_util_he", "HE damage/round"), f"{he:.1f}", tokens.text_primary, ""),
            (
                i18n.get_text("md_util_molotov", "Molotov dmg/round"),
                f"{molotov:.1f}",
                tokens.text_primary,
                "",
            ),
            (
                i18n.get_text("md_util_smokes", "Smokes/round"),
                f"{smokes:.1f}",
                tokens.text_primary,
                "",
            ),
            (
                i18n.get_text("md_util_flash", "Flash assists"),
                f"{flash:.0f}",
                tokens.text_primary,
                "",
            ),
            (
                i18n.get_text("md_util_unused", "Unused util/round"),
                f"{unused:.1f}",
                unused_color,
                "",
            ),
        ]
        return self._build_stat_band(cells)

    # ── Tab: Rounds (frame 10) ──

    # (key, i18n key, fallback header, pixel width; -1 = stretch) — widths
    # trace the frame-10 column grid so header and rows always align.
    _ROUND_COLS = (
        ("rnd", "md_col_rnd", "Rnd", 64),
        ("wl", "md_col_wl", "W/L", 60),
        ("side", "md_col_side", "Side", 80),
        ("k", "md_col_k", "K", 40),
        ("d", "md_col_d", "D", 40),
        ("dmg", "md_col_dmg", "DMG", 80),
        ("equip", "md_col_equip", "Equip $", 100),
        ("fk", "md_col_first_kill", "First Kill", 100),
        ("bomb", "md_col_bomb", "Bomb", 100),
        ("left", "md_col_enemies", "Enemies left", 120),
        ("note", "md_col_notes", "Notes", -1),
    )

    def _build_rounds(self, rounds: list) -> QWidget:
        tokens = get_tokens()
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, tokens.spacing_md, 0, 0)
        page_layout.setSpacing(tokens.spacing_sm)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._round_header_row())
        for idx, r in enumerate(rounds):
            layout.addWidget(self._round_row(r, striped=bool(idx % 2)))
            next_side = rounds[idx + 1].get("side") if idx + 1 < len(rounds) else None
            side = r.get("side")
            side_change = side in ("CT", "T") and next_side in ("CT", "T") and next_side != side
            if side_change or (side not in ("CT", "T") and idx == 11 and len(rounds) > 12):
                separator = QFrame()
                separator.setFixedHeight(2)
                separator.setStyleSheet(f"background: {tokens.accent_muted_30}; border: none;")
                layout.addSpacing(tokens.spacing_sm)
                layout.addWidget(separator)
                layout.addSpacing(tokens.spacing_sm)
        layout.addStretch(1)
        scroll.setWidget(content)
        page_layout.addWidget(scroll, 1)
        page_layout.addWidget(self._round_totals_row(rounds))
        return page

    def _round_header_row(self) -> QFrame:
        tokens = get_tokens()
        row = QFrame()
        row.setStyleSheet(
            f"background: {tokens.surface_sunken}; border: none; "
            f"border-radius: {tokens.radius_sm}px;"
        )
        box = QHBoxLayout(row)
        box.setContentsMargins(tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm)
        box.setSpacing(0)
        for _key, i18n_key, fallback, width in self._ROUND_COLS:
            label = QLabel(i18n.get_text(i18n_key, fallback))
            label.setFont(_mono_font(caption=True))
            label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
            if width > 0:
                label.setFixedWidth(width)
                box.addWidget(label)
            else:
                box.addWidget(label, 1)
        return row

    def _round_row(self, r: dict, striped: bool) -> QFrame:
        tokens = get_tokens()
        rnum = int(r.get("round_number") or 0)
        side = str(r.get("side") or "")
        won = bool(r.get("round_won"))
        kills = int(r.get("kills") or 0)
        deaths = int(r.get("deaths") or 0)
        dmg = int(r.get("damage_dealt") or 0)
        equip = int(r.get("equipment_value") or 0)
        opening = bool(r.get("opening_kill"))

        side_known = side in ("CT", "T")
        side_color = tokens.chart_line_primary if side == "CT" else tokens.chart_line_secondary

        bomb = r.get("bomb")  # FIELD-GAP: bomb outcome is not in the
        # RoundStats payload (it lives in the per-match shard's
        # MatchEventState); fixture-only until the VM joins that data.
        if bomb in ("planted", "defused"):
            bomb_text = i18n.get_text(f"md_bomb_{bomb}", str(bomb))
            bomb_color = tokens.success
        elif bomb == "lost":
            bomb_text = i18n.get_text("md_bomb_lost", "lost")
            bomb_color = tokens.text_secondary
        else:
            bomb_text, bomb_color = "—", tokens.text_secondary

        enemies_left = r.get("enemies_left")  # FIELD-GAP: not in RoundStats;
        # fixture-only display field.
        left_text = "—" if enemies_left is None else str(enemies_left)

        note = r.get("note")
        if note:
            severity = str(r.get("note_severity") or "").lower()
        else:
            # FIELD-GAP: RoundStats carries no notes text — fall back to the
            # duel flags the payload does have.
            if r.get("opening_death"):
                note, severity = i18n.get_text("md_note_opening_death", "opening death"), ""
            elif opening:
                note, severity = i18n.get_text("md_note_opening_kill", "opening kill"), ""
            else:
                note, severity = "—", ""
        if severity == "warning":
            note_color = tokens.warning
        elif severity == "success":
            note_color = tokens.success
        else:
            note_color = tokens.text_tertiary

        wl_text = (
            i18n.get_text("md_round_win", "W") if won else i18n.get_text("md_round_loss", "L")
        )
        cells = {
            "rnd": (f"R{rnum:2d}", tokens.text_primary, False),
            "wl": (wl_text, tokens.success if won else tokens.error, True),
            "side": (side if side_known else "—", side_color if side_known else tokens.text_secondary, True),
            "k": (str(kills), tokens.text_primary, False),
            "d": (str(deaths), tokens.text_primary, False),
            "dmg": (str(dmg), tokens.text_primary, False),
            "equip": (f"${equip}", tokens.text_primary, False),
            "fk": ("FK" if opening else "", tokens.warning, True),
            "bomb": (bomb_text, bomb_color, False),
            "left": (left_text, tokens.text_secondary, False),
            "note": (note, note_color, False),
        }

        row = QFrame()
        background = tokens.surface_raised if striped else "transparent"
        row.setStyleSheet(f"background: {background}; border: none;")
        row.setFixedHeight(28)
        box = QHBoxLayout(row)
        box.setContentsMargins(tokens.spacing_md, 0, tokens.spacing_md, 0)
        box.setSpacing(0)
        for key, _i18n_key, _fallback, width in self._ROUND_COLS:
            text, color, bold = cells[key]
            label = QLabel(text)
            label.setTextFormat(Qt.PlainText)  # FE-01: DB/fixture-sourced text
            font = _mono_font()
            font.setBold(bold)
            label.setFont(font)
            label.setStyleSheet(f"color: {color}; background: transparent;")
            if width > 0:
                label.setFixedWidth(width)
                box.addWidget(label)
            else:
                box.addWidget(label, 1)
        return row

    def _round_totals_row(self, rounds: list) -> QWidget:
        tokens = get_tokens()
        wins = sum(1 for r in rounds if r.get("round_won"))
        losses = len(rounds) - wins
        kills = sum(int(r.get("kills") or 0) for r in rounds)
        deaths = sum(int(r.get("deaths") or 0) for r in rounds)
        dmg = sum(int(r.get("damage_dealt") or 0) for r in rounds)
        fk_rounds = [r for r in rounds if r.get("opening_kill")]
        fk_w = sum(1 for r in fk_rounds if r.get("round_won"))

        host = QWidget()
        box = QHBoxLayout(host)
        box.setContentsMargins(tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, 0)
        box.setSpacing(tokens.spacing_md)

        def _mono_label(text: str, color: str, bold: bool = False) -> QLabel:
            label = QLabel(text)
            font = _mono_font()
            font.setBold(bold)
            label.setFont(font)
            label.setStyleSheet(f"color: {color}; background: transparent;")
            return label

        box.addWidget(
            _mono_label(i18n.get_text("md_total", "Total:"), tokens.text_secondary, bold=True)
        )
        box.addWidget(
            _mono_label(
                i18n.get_text("md_total_w", "{n} W").format(n=wins), tokens.success, bold=True
            )
        )
        box.addWidget(
            _mono_label(
                i18n.get_text("md_total_l", "{n} L").format(n=losses), tokens.error, bold=True
            )
        )
        box.addSpacing(tokens.spacing_md)
        box.addWidget(
            _mono_label(
                i18n.get_text("md_total_kdmg", "{k} K · {d} D · {dmg} DMG").format(
                    k=kills, d=deaths, dmg=dmg
                ),
                tokens.text_primary,
            )
        )
        box.addSpacing(tokens.spacing_md)
        box.addWidget(
            _mono_label(
                i18n.get_text("md_total_fk", "{n} First Kills ({w}W / {l}L)").format(
                    n=len(fk_rounds), w=fk_w, l=len(fk_rounds) - fk_w
                ),
                tokens.warning,
            )
        )
        box.addStretch(1)

        footer = MonoFooter(
            i18n.get_text(
                "md_footer_rounds", "RoundStats · {n} rows · MatchEventState JOIN on demo_name"
            ).format(n=len(rounds))
        )
        footer.setWordWrap(False)
        box.addWidget(footer)
        return host

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
            empty.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
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
        title.setStyleSheet(f"color: {badge_color}; background: transparent;")
        body.addWidget(title)

        message = QLabel(ins.get("message", ""))
        message.setTextFormat(Qt.PlainText)
        message.setWordWrap(True)
        message.setFont(Typography.font("body"))
        message.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        body.addWidget(message)

        focus = ins.get("focus_area")
        if focus:
            focus_label = QLabel(f"Focus  ·  {focus}")
            focus_label.setTextFormat(Qt.PlainText)
            focus_label.setFont(Typography.font("caption"))
            focus_label.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
            body.addWidget(focus_label)

        return card
