"""Pro Player Comparison — frame 15: radar + head-to-head, Pro vs Pro or Me vs Pro.

Composition (frame 15):
    Title        Pro Player Comparison
    Mode chips   [Pro vs Pro] [Me vs Pro]
    Selectors    "Select Players" card: Player A [combo][Details]
                 Player B [combo][Details]  [Compare]   {n} pros loaded · HLTVDatabase
    Results 50/50
        left     "Skill Radar — 8 axes (0-100)" card (RadarChart + legend chips)
        right    "Head-to-head metrics" card (13-row table with WINNER column,
                 Style summary sunken box, MonoFooter data-provenance line)

Me vs Pro is belief-gated: with fewer than ``_MIN_PERSONAL_MATCHES`` analyzed
personal matches the results area renders an EmptyState (frame-20 pattern)
instead of a half-empty radar.

Emits ``pro_detail_requested(int hltv_id)`` when either Details button is
clicked. The MainWindow / app.py wires this to ProPlayerDetailScreen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
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
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button, navigate_to
from Programma_CS2_RENAN.apps.qt_app.viewmodels.pro_comparison_vm import ProComparisonViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.charts.radar_chart import RadarChart
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.filter_chip import FilterChip
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mono_footer import MonoFooter
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_pro_comparison")

# Me-vs-Pro belief gate: the VM's availability signal is the user-side stats
# dict itself — ``_get_user_stats`` returns ``{}`` when no player name is set
# or no personal matches exist, and otherwise includes ``maps_played`` (the
# COUNT of analyzed personal matches). Below this count the comparison is
# statistically meaningless, so the screen gates instead of rendering.
_MIN_PERSONAL_MATCHES = 10

# ── Frame-15 head-to-head row spec ──────────────────────────────────────────
# (payload_key, i18n_key, fallback_label, kind, even_eps)
#   payload_key  key into the ``comparison_ready`` stats dicts. Two virtual
#                keys are derived from real VM fields:
#                  "_kd"       = kpr / dpr        (K/D Ratio row)
#                  "_survival" = 1 - dpr          (Survival Rate row)
#   kind         "ratio" → 2 dp · "value1" → 1 dp · "pct" → fraction ×100,
#                0 dp % · "int" → integer
#   even_eps     |a-b| <= eps ⇒ WINNER column reads "even" (tertiary).
#                None ⇒ neutral row (sample-size context, no winner ever).
# All rows are higher-is-better (the two dpr-based rows are already inverted
# by their derivation). Keys absent from a payload render "—" (R4 HIGH: never
# fabricate a 0 that reads like a real score).
# # FIELD-GAP: clutch_win_pct, he_damage_per_round, flash_assists_per_match,
# smoke_kill_pct and trade_kill_ratio are not columns on ProPlayerStatCard and
# are not emitted by ProComparisonViewModel today — those rows show "—" until
# the HLTV scrape pipeline provides them.
_H2H_ROWS: list[tuple[str, str, str, str, float | None]] = [
    ("rating_2_0", "procomp.m.rating", "HLTV Rating", "ratio", 0.02),
    ("_kd", "procomp.m.kd", "K/D Ratio", "ratio", 0.02),
    ("adr", "procomp.m.adr", "ADR", "value1", 0.5),
    ("kast", "procomp.m.kast", "KAST %", "pct", 0.01),
    ("headshot_pct", "procomp.m.hs", "Headshot %", "pct", 0.01),
    ("opening_duel_win_pct", "procomp.m.opening", "Opening Duel Win %", "pct", 0.01),
    ("clutch_win_pct", "procomp.m.clutch", "Clutch Win %", "pct", 0.01),
    ("he_damage_per_round", "procomp.m.he", "HE Damage/Round", "value1", 0.5),
    ("flash_assists_per_match", "procomp.m.flash", "Flash Assists/Match", "value1", 0.5),
    ("smoke_kill_pct", "procomp.m.smoke", "Thru-smoke Kill %", "pct", 0.01),
    ("trade_kill_ratio", "procomp.m.trade", "Trade Kill Ratio", "ratio", 0.02),
    ("_survival", "procomp.m.survival", "Survival Rate", "pct", 0.01),
    ("maps_played", "procomp.m.maps", "Maps Played", "int", None),
]

# ── Frame-15 radar: VM metric keys → 8 axes ─────────────────────────────────
# Axis raw score = mean of per-key subscores; each subscore is the player's
# value divided by the pairwise max for that key (so every axis lands on a
# 0-100 scale normalized ACROSS THE PAIR). A key contributes only when BOTH
# sides carry it (pairwise comparability); an axis left with no usable keys
# renders the neutral midpoint 50/50 for both players — equal values cannot
# mislead about who is better, and the polygon never spikes to center.
#   Aim          ← headshot_pct + smoke_kill_pct (precision proxy)
#   Opening      ← opening_duel_win_pct + opening_kill_ratio
#   Utility      ← he_damage_per_round + flash_assists_per_match  # FIELD-GAP
#   Clutch       ← clutch_win_pct (# FIELD-GAP) + clutch_win_count
#   Positioning  ← kast + (1 - dpr)  (alive & contributing)
#   Aggression   ← kpr + opening_kill_ratio
#   Economy      ← rating_2_0 + kast  # FIELD-GAP: no eco-round stats in
#                  ProPlayerStatCard — consistency proxy until scraped
#   Survival     ← 1 - dpr
_RADAR_AXIS_KEYS: list[list[str]] = [
    ["headshot_pct", "smoke_kill_pct"],
    ["opening_duel_win_pct", "opening_kill_ratio"],
    ["he_damage_per_round", "flash_assists_per_match"],
    ["clutch_win_pct", "clutch_win_count"],
    ["kast", "_survival"],
    ["kpr", "opening_kill_ratio"],
    ["rating_2_0", "kast"],
    ["_survival"],
]

_RADAR_AXIS_I18N: list[tuple[str, str]] = [
    ("procomp.axis.aim", "Aim"),
    ("procomp.axis.opening", "Opening"),
    ("procomp.axis.utility", "Utility"),
    ("procomp.axis.clutch", "Clutch"),
    ("procomp.axis.positioning", "Positioning"),
    ("procomp.axis.aggression", "Aggression"),
    ("procomp.axis.economy", "Economy"),
    ("procomp.axis.survival", "Survival"),
]


def _sentence_caption_font() -> QFont:
    """Caption-sized font WITHOUT the role's all-uppercase transform.

    Frame 15 renders legend team captions and style-summary detail lines in
    sentence case; the shared caption role forces AllUppercase, so undo just
    that (still token-driven — no literal QFont construction).
    """
    font = Typography.font("caption")
    font.setCapitalization(QFont.MixedCase)
    font.setLetterSpacing(QFont.AbsoluteSpacing, 0.0)
    return font


def _metric_value(stats: dict, key: str) -> float | None:
    """Resolve ``key`` from a comparison payload — including derived keys.

    Returns None for absent keys AND for zero values: the VM back-fills
    missing DB columns with 0.0, and a zero rating/KAST is not a real score.
    """
    if key == "_kd":
        kpr, dpr = stats.get("kpr"), stats.get("dpr")
        if not kpr or not dpr:
            return None
        return float(kpr) / float(dpr)
    if key == "_survival":
        dpr = stats.get("dpr")
        if not dpr:
            return None
        return max(0.0, 1.0 - float(dpr))
    value = stats.get(key)
    if not value:
        return None
    return float(value)


def _h2h_winner(val_a: float | None, val_b: float | None, eps: float | None) -> int | None:
    """Which side wins a higher-is-better row.

    Returns 1 (A wins), -1 (B wins), 0 (both present but within ``eps`` —
    "even"), or None (no winner semantics: a side is missing, or the row is
    neutral ``eps=None`` such as Maps Played).
    """
    if eps is None or val_a is None or val_b is None:
        return None
    diff = val_a - val_b
    if abs(diff) <= eps:
        return 0
    return 1 if diff > 0 else -1


def _fmt_metric(kind: str, value: float | None) -> str:
    if value is None:
        return "—"
    if kind == "ratio":
        return f"{value:.2f}"
    if kind == "value1":
        return f"{value:.1f}"
    if kind == "pct":
        return f"{value * 100:.0f}%"
    return f"{int(value)}"


def _fmt_delta(kind: str, diff: float) -> str:
    diff = abs(diff)
    if kind == "pct":
        return f"+{diff * 100:.0f}%"
    if kind == "value1":
        return f"+{diff:.1f}"
    return f"+{diff:.2f}"


def _radar_axes(metrics_a: dict, metrics_b: dict) -> tuple[list[float], list[float]]:
    """Map two comparison payloads onto the 8 frame-15 radar axes (0-100).

    See the ``_RADAR_AXIS_KEYS`` comment for the key→axis mapping and the
    pairwise normalization / neutral-midpoint fallback rules.
    """
    out_a: list[float] = []
    out_b: list[float] = []
    for keys in _RADAR_AXIS_KEYS:
        subs_a: list[float] = []
        subs_b: list[float] = []
        for key in keys:
            val_a = _metric_value(metrics_a, key)
            val_b = _metric_value(metrics_b, key)
            if val_a is None or val_b is None:
                continue  # pairwise comparability — skip one-sided keys
            peak = max(val_a, val_b)
            if peak <= 0:
                continue
            subs_a.append(max(0.0, val_a) / peak)
            subs_b.append(max(0.0, val_b) / peak)
        if subs_a:
            out_a.append(100.0 * sum(subs_a) / len(subs_a))
            out_b.append(100.0 * sum(subs_b) / len(subs_b))
        else:
            # FIELD-GAP fallback: no usable keys on this axis for this pair —
            # neutral midpoint, never a broken spike-to-center polygon.
            out_a.append(50.0)
            out_b.append(50.0)
    return out_a, out_b


def _style_summary(metrics_a: dict, metrics_b: dict) -> tuple[str, str]:
    """Archetype (headline, dominant-metrics line) for player A vs player B.

    Rule ladder (first match wins; missing keys are never dominant):
        1. KAST + utility dominance   ⇒ team-enabling support
        2. K/D + opening dominance    ⇒ aggressive entry rifler
        3. clutch + survival dominance⇒ late-round anchor
        4. ADR dominance              ⇒ damage-first playmaker
        5. fallback                   ⇒ balanced all-rounder
    Call with swapped arguments for player B's summary.
    """

    def adv(key: str) -> bool:
        val_a = _metric_value(metrics_a, key)
        val_b = _metric_value(metrics_b, key)
        return val_a is not None and val_b is not None and val_a > val_b

    utility_adv = adv("he_damage_per_round") or adv("flash_assists_per_match")
    clutch_adv = adv("clutch_win_pct") or adv("clutch_win_count")

    if adv("kast") and utility_adv:
        return (
            i18n.get_text("procomp.style.support", "team-enabling support"),
            i18n.get_text("procomp.style.support_detail", "Higher KAST, more utility damage"),
        )
    if adv("_kd") and adv("opening_duel_win_pct"):
        return (
            i18n.get_text("procomp.style.entry", "aggressive entry rifler"),
            i18n.get_text("procomp.style.entry_detail", "Higher K/D, wins opening duels"),
        )
    if clutch_adv and adv("_survival"):
        return (
            i18n.get_text("procomp.style.anchor", "late-round anchor"),
            i18n.get_text("procomp.style.anchor_detail", "Wins clutches, survives more rounds"),
        )
    if adv("adr"):
        return (
            i18n.get_text("procomp.style.damage", "damage-first playmaker"),
            i18n.get_text("procomp.style.damage_detail", "Higher average damage per round"),
        )
    return (
        i18n.get_text("procomp.style.balanced", "balanced all-rounder"),
        i18n.get_text("procomp.style.balanced_detail", "No single dominant metric family"),
    )


class ProComparisonScreen(QWidget):
    """Compare two pros, or yourself against a pro."""

    pro_detail_requested = Signal(int)  # emits hltv_id when Details clicked

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._vm = ProComparisonViewModel()
        self._vm.players_loaded.connect(self._on_players_loaded)
        self._vm.comparison_ready.connect(self._on_comparison)
        self._vm.error_changed.connect(self._on_error)

        self._mode = "pro_vs_pro"
        self._players: list[dict] = []
        self._build_ui()

    def on_enter(self) -> None:
        self._vm.load_pro_list()

    def retranslate(self) -> None:
        self._title_label.setText(i18n.get_text("procomp.title", "Pro Player Comparison"))
        self._selector_card.set_title(i18n.get_text("procomp.select_players", "Select Players"))
        self._chip_p_vs_p.set_label(i18n.get_text("procomp.mode_pvp", "Pro vs Pro"))
        self._chip_m_vs_p.set_label(i18n.get_text("procomp.mode_mvp", "Me vs Pro"))
        self._compare_btn.setText(i18n.get_text("procomp.compare", "Compare"))
        # Refresh Player A / Compare-against labels WITHOUT resetting the
        # body stack — a language change must not wipe visible results.
        self._set_mode(self._mode, reset_view=False)

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
        self._title_label = QLabel(i18n.get_text("procomp.title", "Pro Player Comparison"))
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)
        root.addLayout(title_row)

        # Mode chips
        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(tokens.spacing_sm)

        self._chip_p_vs_p = FilterChip(
            i18n.get_text("procomp.mode_pvp", "Pro vs Pro"), checked=True
        )
        self._chip_p_vs_p.toggled.connect(lambda _c: self._set_mode("pro_vs_pro"))
        mode_row.addWidget(self._chip_p_vs_p)

        self._chip_m_vs_p = FilterChip(
            i18n.get_text("procomp.mode_mvp", "Me vs Pro"), checked=False
        )
        self._chip_m_vs_p.toggled.connect(lambda _c: self._set_mode("me_vs_pro"))
        mode_row.addWidget(self._chip_m_vs_p)

        mode_row.addStretch(1)
        root.addLayout(mode_row)

        # Selector card — frame 15 "Select Players"
        self._selector_card = Card(
            title=i18n.get_text("procomp.select_players", "Select Players"), depth="raised"
        )
        sel_body = self._selector_card.content_layout
        sel_body.setSpacing(tokens.spacing_md)

        sel_row = QHBoxLayout()
        sel_row.setContentsMargins(0, 0, 0, 0)
        sel_row.setSpacing(tokens.spacing_md)

        self._label_a = QLabel(i18n.get_text("procomp.player_a", "Player A:"))
        self._label_a.setFont(Typography.font("body"))
        self._label_a.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        sel_row.addWidget(self._label_a)

        self._combo_a = QComboBox()
        self._combo_a.setMinimumWidth(220)
        self._combo_a.setEditable(True)
        self._combo_a.setInsertPolicy(QComboBox.NoInsert)
        sel_row.addWidget(self._combo_a)

        self._details_a_btn = make_button(
            i18n.get_text("procomp.details", "Details"), variant="secondary", fixed_width=90
        )
        self._details_a_btn.setFixedHeight(36)
        self._details_a_btn.clicked.connect(lambda: self._open_details(self._combo_a))
        sel_row.addWidget(self._details_a_btn)

        self._label_b = QLabel(i18n.get_text("procomp.player_b", "Player B:"))
        self._label_b.setFont(Typography.font("body"))
        self._label_b.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        sel_row.addWidget(self._label_b)

        self._combo_b = QComboBox()
        self._combo_b.setMinimumWidth(220)
        self._combo_b.setEditable(True)
        self._combo_b.setInsertPolicy(QComboBox.NoInsert)
        sel_row.addWidget(self._combo_b)

        self._details_b_btn = make_button(
            i18n.get_text("procomp.details", "Details"), variant="secondary", fixed_width=90
        )
        self._details_b_btn.setFixedHeight(36)
        self._details_b_btn.clicked.connect(lambda: self._open_details(self._combo_b))
        sel_row.addWidget(self._details_b_btn)

        self._compare_btn = make_button(
            i18n.get_text("procomp.compare", "Compare"), variant="primary", fixed_width=120
        )
        self._compare_btn.setFixedHeight(36)
        self._compare_btn.clicked.connect(self._on_compare)
        sel_row.addWidget(self._compare_btn)

        # Right mono caption — "312 pros loaded · HLTVDatabase" (frame 15).
        sel_row.addSpacing(tokens.spacing_md)
        self._count_caption = MonoFooter(i18n.get_text("procomp.loading_pros", "Loading pros…"))
        self._count_caption.setWordWrap(False)
        sel_row.addWidget(self._count_caption)

        sel_row.addStretch(1)
        sel_body.addLayout(sel_row)
        root.addWidget(self._selector_card)

        # Body stack: empty / error / results / me-vs-pro belief gate
        self._body_stack = QStackedWidget()
        root.addWidget(self._body_stack, 1)

        self._empty_state = EmptyState(
            icon_text="◌",
            title=i18n.get_text("procomp.empty_title", "Pick two players to compare"),
            description=i18n.get_text(
                "procomp.empty_desc",
                "Choose pros above (or switch to 'Me vs Pro') and click "
                "Compare to see a side-by-side breakdown.",
            ),
        )
        self._body_stack.addWidget(self._empty_state)

        self._error_state = EmptyState(
            icon_text="◎",
            title=i18n.get_text("procomp.error_title", "Comparison failed"),
            description="",
        )
        self._body_stack.addWidget(self._error_state)

        # Results — scrollable card column (one container widget per compare
        # so _clear_results can take it in a single pass).
        self._results_scroll = QScrollArea()
        self._results_scroll.setWidgetResizable(True)
        self._results_scroll.setFrameShape(QFrame.NoFrame)
        self._results = QWidget()
        self._results_layout = QVBoxLayout(self._results)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(tokens.spacing_lg)
        self._results_layout.addStretch(1)
        self._results_scroll.setWidget(self._results)
        self._body_stack.addWidget(self._results_scroll)

        # Me-vs-Pro belief gate (frame-20 EmptyState pattern) — shown instead
        # of a half-empty radar when the personal sample is too small.
        self._gate_state = EmptyState(
            icon_text="◔",
            title=i18n.get_text("procomp.gate_title", "Not enough personal data yet"),
            description=i18n.get_text(
                "procomp.gate_desc",
                "The coach's belief in your profile grows with every analyzed "
                "demo. Analyze at least 10 matches to unlock a fair "
                "side-by-side against a pro.",
            ),
            cta_text=i18n.get_text("procomp.gate_cta", "Analyze Demos"),
            link_text=i18n.get_text("procomp.gate_link", "Or read the Getting Started guide →"),
        )
        self._gate_state.action_clicked.connect(lambda: self._navigate("home"))
        self._gate_state.link_clicked.connect(lambda: self._navigate("help"))
        self._body_stack.addWidget(self._gate_state)

        self._page_empty = 0
        self._page_error = 1
        self._page_results = 2
        self._page_gate = 3

    # ── Mode switching ──

    def _set_mode(self, mode: str, reset_view: bool = True) -> None:
        self._mode = mode
        self._chip_p_vs_p.set_checked(mode == "pro_vs_pro")
        self._chip_m_vs_p.set_checked(mode == "me_vs_pro")
        is_pvp = mode == "pro_vs_pro"
        if is_pvp:
            self._label_a.setText(i18n.get_text("procomp.player_a", "Player A:"))
            self._label_a.setVisible(True)
            self._combo_a.setVisible(True)
            self._details_a_btn.setVisible(True)
            self._label_b.setText(i18n.get_text("procomp.player_b", "Player B:"))
        else:
            self._label_a.setVisible(False)
            self._combo_a.setVisible(False)
            # In Me-vs-Pro mode, hide combo_a's Details button — there's
            # no pro selected on side A (it's "you").
            self._details_a_btn.setVisible(False)
            self._label_b.setText(i18n.get_text("procomp.compare_against", "Compare against:"))

        if reset_view:
            self._body_stack.setCurrentIndex(self._page_empty)

    # ── Details routing ──

    def _open_details(self, combo: QComboBox) -> None:
        """Emit pro_detail_requested with the combo's current hltv_id.

        MainWindow / app.py wires the signal to ProPlayerDetailScreen.
        Silently ignores empty selections — Details on an unset combo
        is a no-op rather than an error popup.
        """
        hltv_id = combo.currentData()
        if hltv_id is None:
            return
        try:
            self.pro_detail_requested.emit(int(hltv_id))
        except (TypeError, ValueError):
            logger.warning("pro_detail_requested: non-int currentData(): %r", hltv_id)

    def _navigate(self, screen_name: str) -> None:
        navigate_to(self, screen_name)

    # ── Data flow ──

    def _on_players_loaded(self, players: list) -> None:
        self._players = players
        self._combo_a.clear()
        self._combo_b.clear()
        for p in players:
            rank = p.get("team_rank", 0)
            rank_prefix = f"#{rank} " if rank and rank < 999 else ""
            label = f"{p['nickname']} ({rank_prefix}{p['team']})"
            self._combo_a.addItem(label, p["hltv_id"])
            self._combo_b.addItem(label, p["hltv_id"])
        if len(players) >= 2:
            self._combo_b.setCurrentIndex(1)

        # Case-insensitive substring search: typing "zyw" matches "ZywOo (#3 Vitality)"
        # and typing "vit" matches every Vitality player. Default Qt completer
        # is prefix-only and case-sensitive, which is unusable for nicknames
        # whose canonical casing varies (HObbit, Hobbit, m0NESY, m0nesy).
        for combo in (self._combo_a, self._combo_b):
            self._install_contains_completer(combo)

        self._count_caption.setText(
            i18n.get_text("procomp.pros_loaded", "{n} pros loaded · HLTVDatabase").format(
                n=len(players)
            )
        )

    @staticmethod
    def _install_contains_completer(combo: QComboBox) -> None:
        completer = combo.completer()
        if completer is None:
            completer = QCompleter(combo)
            combo.setCompleter(completer)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)

    def _on_compare(self) -> None:
        self._body_stack.setCurrentIndex(self._page_empty)
        self._empty_state.set_title(i18n.get_text("procomp.comparing", "Comparing…"))
        self._empty_state.set_description("")

        if self._mode == "pro_vs_pro":
            id_a = self._combo_a.currentData()
            id_b = self._combo_b.currentData()
            if id_a is not None and id_b is not None:
                self._vm.compare_pros(id_a, id_b)
        else:
            id_b = self._combo_b.currentData()
            if id_b is not None:
                self._vm.compare_user_vs_pro(id_b)

    def _on_comparison(self, stats_a: dict, stats_b: dict, name_a: str, name_b: str) -> None:
        tokens = get_tokens()

        # Me-vs-Pro belief gate: never render a half-empty radar. The VM's
        # availability signal is stats_a itself — {} when no personal data,
        # else it carries maps_played = count of analyzed personal matches.
        if self._mode == "me_vs_pro":
            sample = int(stats_a.get("maps_played") or 0) if stats_a else 0
            if sample < _MIN_PERSONAL_MATCHES:
                self._body_stack.setCurrentIndex(self._page_gate)
                return

        self._clear_results()

        row_container = QWidget()
        row = QHBoxLayout(row_container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_lg)
        row.addWidget(self._build_radar_card(stats_a, stats_b, name_a, name_b), 1)
        row.addWidget(self._build_h2h_card(stats_a, stats_b, name_a, name_b), 1)
        self._results_layout.insertWidget(self._results_layout.count() - 1, row_container)

        self._body_stack.setCurrentIndex(self._page_results)

    def _on_error(self, msg: str) -> None:
        self._error_state.set_title(i18n.get_text("procomp.error_title", "Comparison failed"))
        self._error_state.set_description(str(msg))
        self._body_stack.setCurrentIndex(self._page_error)

    # ── Results builders ──

    def _build_radar_card(self, stats_a: dict, stats_b: dict, name_a: str, name_b: str) -> Card:
        tokens = get_tokens()
        card = Card(
            title=i18n.get_text("procomp.radar_title", "Skill Radar — 8 axes (0-100)"),
            depth="raised",
        )
        card.content_layout.setSpacing(tokens.spacing_md)

        radar = RadarChart()
        radar.set_axes([i18n.get_text(key, fb) for key, fb in _RADAR_AXIS_I18N])
        radar.set_range(0.0, 100.0)
        values_a, values_b = _radar_axes(stats_a, stats_b)
        radar.add_series(name_a, values_a, QColor(tokens.accent_primary))
        radar.add_series(name_b, values_b, QColor(tokens.info))
        radar.setMinimumHeight(400)
        card.content_layout.addWidget(radar, 1)

        legend = QHBoxLayout()
        legend.setContentsMargins(0, 0, 0, 0)
        legend.setSpacing(tokens.spacing_lg)
        legend.addWidget(self._legend_chip(name_a, tokens.accent_primary))
        legend.addWidget(self._legend_chip(name_b, tokens.info))
        legend.addStretch(1)
        card.content_layout.addLayout(legend)
        return card

    def _legend_chip(self, name: str, color: str) -> QWidget:
        tokens = get_tokens()
        chip = QWidget()
        lay = QHBoxLayout(chip)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(tokens.spacing_sm)

        swatch = QFrame()
        swatch.setFixedSize(12, 12)
        swatch.setStyleSheet(f"background: {color}; border-radius: 3px;")
        lay.addWidget(swatch)

        name_lbl = QLabel(name)
        name_font = Typography.font("body")
        name_font.setBold(True)
        name_lbl.setFont(name_font)
        name_lbl.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        lay.addWidget(name_lbl)

        team_caption = self._team_caption(name)
        if team_caption:
            team_lbl = QLabel(team_caption)
            team_lbl.setFont(_sentence_caption_font())
            team_lbl.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
            lay.addWidget(team_lbl)
        return chip

    def _team_caption(self, name: str) -> str:
        """`(#1 Vitality)` when the roster row for ``name`` is known, else ''."""
        for p in self._players:
            if p.get("nickname") == name:
                team = p.get("team") or ""
                rank = p.get("team_rank") or 0
                if team and team != "—":
                    return f"(#{rank} {team})" if 0 < rank < 999 else f"({team})"
                return ""
        return ""

    def _build_h2h_card(self, stats_a: dict, stats_b: dict, name_a: str, name_b: str) -> Card:
        tokens = get_tokens()
        # FIELD-GAP: frame 15 titles this "Head-to-head metrics · {period}
        # form" — the comparison payload carries no period/time_span field,
        # so the period fragment is omitted until the VM exposes it.
        card = Card(
            title=i18n.get_text("procomp.h2h_title", "Head-to-head metrics"), depth="raised"
        )
        card.content_layout.setSpacing(tokens.spacing_md)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(tokens.spacing_md)
        grid.setVerticalSpacing(tokens.spacing_xs)
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 3)
        grid.setColumnStretch(3, 4)

        grid.addWidget(
            self._grid_header_label(i18n.get_text("procomp.metric", "Metric"), Qt.AlignLeft),
            0,
            0,
        )
        grid.addWidget(
            self._grid_header_label(name_a, Qt.AlignHCenter, tokens.accent_primary, keep_case=True),
            0,
            1,
        )
        grid.addWidget(
            self._grid_header_label(name_b, Qt.AlignHCenter, tokens.info, keep_case=True), 0, 2
        )
        grid.addWidget(
            self._grid_header_label(i18n.get_text("procomp.winner", "Winner"), Qt.AlignRight),
            0,
            3,
        )

        for row_idx, (key, i18n_key, fallback, kind, eps) in enumerate(_H2H_ROWS, start=1):
            val_a = _metric_value(stats_a, key)
            val_b = _metric_value(stats_b, key)
            winner = _h2h_winner(val_a, val_b, eps)

            metric = QLabel(i18n.get_text(i18n_key, fallback))
            metric.setFont(Typography.font("body"))
            metric.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
            grid.addWidget(metric, row_idx, 0)

            # Better raw value green-tinted per frame; absent values tertiary.
            color_a = (
                tokens.success
                if winner == 1
                else (tokens.text_tertiary if val_a is None else tokens.text_primary)
            )
            color_b = (
                tokens.success
                if winner == -1
                else (tokens.text_tertiary if val_b is None else tokens.text_primary)
            )
            grid.addWidget(self._stat_cell(_fmt_metric(kind, val_a), color_a), row_idx, 1)
            grid.addWidget(self._stat_cell(_fmt_metric(kind, val_b), color_b), row_idx, 2)

            if winner == 1:
                win_text, win_color = (
                    f"{name_a} {_fmt_delta(kind, val_a - val_b)}",
                    tokens.accent_primary,
                )
            elif winner == -1:
                win_text, win_color = f"{name_b} {_fmt_delta(kind, val_b - val_a)}", tokens.info
            elif winner == 0:
                win_text, win_color = i18n.get_text("procomp.even", "even"), tokens.text_tertiary
            else:
                win_text, win_color = "—", tokens.text_tertiary
            win_cell = self._stat_cell(win_text, win_color)
            win_cell.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(win_cell, row_idx, 3)

        card.content_layout.addWidget(grid_widget)
        card.content_layout.addWidget(self._build_style_summary(stats_a, stats_b, name_a, name_b))
        card.content_layout.addWidget(self._build_footer(stats_a, stats_b))
        card.content_layout.addStretch(1)
        return card

    def _build_style_summary(
        self, stats_a: dict, stats_b: dict, name_a: str, name_b: str
    ) -> QFrame:
        tokens = get_tokens()
        box = QFrame()
        box.setStyleSheet(
            f"background: {tokens.surface_sunken}; " f"border-radius: {tokens.radius_md}px;"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(
            tokens.spacing_md, tokens.spacing_md, tokens.spacing_md, tokens.spacing_md
        )
        lay.setSpacing(tokens.spacing_xs)

        title = QLabel(i18n.get_text("procomp.style_title", "Style summary"))
        title_font = Typography.font("body")
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        lay.addWidget(title)

        for name, pair, color in (
            (name_a, (stats_a, stats_b), tokens.accent_primary),
            (name_b, (stats_b, stats_a), tokens.info),
        ):
            archetype, detail = _style_summary(*pair)
            head = QLabel(f"{name} — {archetype}")
            head.setFont(Typography.font("body"))
            head.setStyleSheet(f"color: {color}; background: transparent;")
            head.setWordWrap(True)
            lay.addWidget(head)

            detail_lbl = QLabel(detail)
            detail_lbl.setFont(_sentence_caption_font())
            detail_lbl.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
            detail_lbl.setWordWrap(True)
            lay.addWidget(detail_lbl)
        return box

    def _build_footer(self, stats_a: dict, stats_b: dict) -> MonoFooter:
        """Data-provenance mono line per frame 15.

        # FIELD-GAP: ProPlayerStatCard.last_updated (the HLTV scrape date)
        is not part of the comparison payload — the "HLTV scraped {date}"
        fragment is omitted until the VM exposes it.
        """
        lines = ["ProPlayer · ProPlayerStatCard"]
        maps_a = int(stats_a.get("maps_played") or 0) if stats_a else 0
        maps_b = int(stats_b.get("maps_played") or 0) if stats_b else 0
        if maps_a and maps_b and maps_a == maps_b:
            lines.append(
                i18n.get_text(
                    "procomp.footer_sample", "Sample: last {n} official matches per player"
                ).format(n=maps_a)
            )
        elif maps_a and maps_b:
            lines.append(
                i18n.get_text(
                    "procomp.footer_sample_uneven", "Sample: {a} / {b} official matches"
                ).format(a=maps_a, b=maps_b)
            )
        return MonoFooter("\n".join(lines))

    # ── Helpers ──

    def _grid_header_label(
        self,
        text: str,
        align: Qt.AlignmentFlag = Qt.AlignHCenter,
        color: str | None = None,
        keep_case: bool = False,
    ) -> QLabel:
        # keep_case: player nicknames keep their canonical casing per frame 15
        # ("ZywOo", "donk") while METRIC/WINNER render caption-uppercase.
        tokens = get_tokens()
        lbl = QLabel(text if keep_case else text.upper())
        if keep_case:
            lbl.setFont(_sentence_caption_font())
        else:
            Typography.apply(lbl, "caption")
        lbl.setAlignment(align | Qt.AlignVCenter)
        lbl.setStyleSheet(
            f"color: {color or tokens.text_secondary}; background: transparent; "
            f"padding: {tokens.spacing_xs}px 0;"
        )
        return lbl

    def _stat_cell(self, text: str, color: str, mono: bool = True) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(Typography.font("mono") if mono else Typography.font("body"))
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
        return lbl

    def _clear_results(self) -> None:
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
