"""Match History — grouped, filterable list of analyzed demos.

Composition:
    Title rail        Match History                       [● 47 matches]
    Source filters    [All] [Personal] [Pro]
    Map filters       [All maps] [Mirage] [Dust2] ...
    Body              TODAY        ── MatchRowCard ──
                      THIS WEEK    ── MatchRowCard ──
                      EARLIER      ── MatchRowCard ──

Pro-only banner appears when the user has zero personal matches yet
(unchanged from the previous flow — surface still drives users to the
Dashboard's Analyze action).

Empty + skeleton states are routed through the shared design-system
``EmptyState`` / ``SkeletonTable`` components.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import map_short_name
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.viewmodels.match_history_vm import (
    MatchHistoryViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.filter_chip import FilterChip
from Programma_CS2_RENAN.apps.qt_app.widgets.components.match_row_card import (
    MatchRowCard,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.apps.qt_app.widgets.skeleton import SkeletonTable
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_match_history")

_SOURCE_ALL = "all"
_SOURCE_PERSONAL = "personal"
_SOURCE_PRO = "pro"
_MAP_ALL = "__all__"


def _to_aware(dt: Any) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _bucket(match_date: Any, now: datetime) -> str:
    """Return one of TODAY / THIS WEEK / EARLIER for a match timestamp.

    Uses elapsed time (24h / 7d) rather than calendar boundaries — a
    match 9 hours ago should read as "today" even if it crossed midnight.
    """
    dt = _to_aware(match_date)
    if dt is None:
        return "EARLIER"
    seconds = (now - dt).total_seconds()
    if seconds < 24 * 60 * 60:
        return "TODAY"
    if seconds < 7 * 24 * 60 * 60:
        return "THIS WEEK"
    return "EARLIER"


_BUCKET_ORDER = ("TODAY", "THIS WEEK", "EARLIER")


class MatchHistoryScreen(QWidget):
    """Filterable match history with grouped sections."""

    match_selected = Signal(str)  # demo_name

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._vm = MatchHistoryViewModel()
        self._vm.matches_changed.connect(self._on_matches_loaded)
        self._vm.error_changed.connect(self._on_error)
        self._vm.is_loading_changed.connect(self._on_loading_changed)

        self._all_matches: list[dict[str, Any]] = []
        self._source_filter: str = _SOURCE_ALL
        self._map_filter: str = _MAP_ALL
        self._source_chips: dict[str, FilterChip] = {}
        self._map_chips: dict[str, FilterChip] = {}

        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self):
        self._show_loading()
        self._vm.load_matches()

    def on_leave(self):
        self._vm.cancel()

    def retranslate(self):
        self._title_label.setText(i18n.get_text("match_history_title"))

    # ── UI Construction ──

    def _build_ui(self):
        tokens = get_tokens()

        root = QVBoxLayout(self)
        root.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        root.setSpacing(tokens.spacing_md)

        # ── Title rail ──
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        self._title_label = QLabel(i18n.get_text("match_history_title"))
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)
        self._count_chip = StatusChip("0 matches", severity="neutral")
        title_row.addWidget(self._count_chip)
        root.addLayout(title_row)

        # ── Source filter chips (mutually exclusive) ──
        self._source_row = QHBoxLayout()
        self._source_row.setContentsMargins(0, 0, 0, 0)
        self._source_row.setSpacing(tokens.spacing_sm)
        for key, label in (
            (_SOURCE_ALL, "All"),
            (_SOURCE_PERSONAL, "Personal"),
            (_SOURCE_PRO, "Pro"),
        ):
            chip = FilterChip(label, checked=(key == self._source_filter), count=None)
            chip.toggled.connect(lambda _checked, k=key: self._on_source_chip(k))
            self._source_row.addWidget(chip)
            self._source_chips[key] = chip
        self._source_row.addStretch(1)
        root.addLayout(self._source_row)

        # ── Map filter row (built dynamically as data arrives) ──
        self._map_row_widget = QWidget()
        self._map_row = QHBoxLayout(self._map_row_widget)
        self._map_row.setContentsMargins(0, 0, 0, 0)
        self._map_row.setSpacing(tokens.spacing_sm)
        self._map_row.addStretch(1)
        self._map_row_widget.setVisible(False)
        root.addWidget(self._map_row_widget)

        # ── Pro-only banner (shown when user has no personal matches) ──
        self._pro_banner = QLabel(
            "No personal matches yet — showing pro reference matches below. "
            "Analyze your own demos from the Dashboard to see your match history."
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

        # ── Body stack: skeleton | empty | filter_empty | match_list ──
        # Single stretchy slot; the inner stack swaps so the surrounding
        # layout doesn't stretch / wobble between data states.
        self._body_stack = QStackedWidget()
        root.addWidget(self._body_stack, 1)

        self._skeleton = SkeletonTable(row_count=4)
        self._body_stack.addWidget(self._skeleton)

        self._empty_state = EmptyState(
            icon_text="◎",
            title="No matches found",
            description="Play and analyze a demo to see it here.",
            cta_text="Open Dashboard",
        )
        self._empty_state.action_clicked.connect(self._navigate_home)
        self._body_stack.addWidget(self._empty_state)

        self._filter_empty = EmptyState(
            icon_text="◌",
            title="No matches match these filters",
            description="Try clearing one of the filter chips above.",
            cta_text="Clear filters",
        )
        self._filter_empty.action_clicked.connect(self._reset_filters)
        self._body_stack.addWidget(self._filter_empty)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(tokens.spacing_md)
        self._container_layout.addStretch(1)
        self._scroll.setWidget(self._container)
        self._body_stack.addWidget(self._scroll)

        # Page index helpers
        self._page_skeleton = 0
        self._page_empty = 1
        self._page_filter_empty = 2
        self._page_list = 3

    # ── Loading / error / empty plumbing ──

    def _on_loading_changed(self, loading: bool):
        if loading:
            self._show_loading()

    def _on_error(self, msg: str):
        if not msg:
            return
        self._empty_state.set_title("Couldn't load matches")
        self._empty_state.set_description(str(msg))
        self._body_stack.setCurrentIndex(self._page_empty)

    def _show_loading(self):
        self._clear_container()
        self._body_stack.setCurrentIndex(self._page_skeleton)

    # ── Data → render ──

    def _on_matches_loaded(self, matches: list):
        self._all_matches = list(matches)

        # No data at all → empty state, hide everything else
        if not self._all_matches:
            self._pro_banner.setVisible(False)
            self._map_row_widget.setVisible(False)
            self._empty_state.set_title("No matches found")
            self._empty_state.set_description(
                "Play and analyze a demo to see it here."
            )
            self._body_stack.setCurrentIndex(self._page_empty)
            self._update_count_chip(0)
            return

        # Pro-only banner — visible until user has at least one personal match.
        has_personal = any(not m.get("is_pro", False) for m in self._all_matches)
        self._pro_banner.setVisible(not has_personal)

        # Refresh source chip counts
        all_count = len(self._all_matches)
        personal_count = sum(1 for m in self._all_matches if not m.get("is_pro"))
        pro_count = all_count - personal_count
        self._source_chips[_SOURCE_ALL].set_count(all_count)
        self._source_chips[_SOURCE_PERSONAL].set_count(personal_count)
        self._source_chips[_SOURCE_PRO].set_count(pro_count)

        # Refresh map filter row
        self._rebuild_map_chips()

        # Update title status chip
        self._update_count_chip(all_count)

        # Render filtered + grouped rows
        self._render_filtered()

    def _render_filtered(self):
        self._clear_container()

        filtered = self._apply_filters(self._all_matches)
        if not filtered:
            self._body_stack.setCurrentIndex(self._page_filter_empty)
            return

        self._body_stack.setCurrentIndex(self._page_list)

        now = datetime.now(timezone.utc)
        groups: dict[str, list[dict]] = defaultdict(list)
        for match in filtered:
            groups[_bucket(match.get("match_date"), now)].append(match)

        tokens = get_tokens()
        for bucket in _BUCKET_ORDER:
            bucket_matches = groups.get(bucket, [])
            if not bucket_matches:
                continue
            header = QLabel(bucket)
            Typography.apply(header, "caption")
            header.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent; "
                f"padding: {tokens.spacing_md}px 0 {tokens.spacing_xs}px 0;"
            )
            self._container_layout.insertWidget(
                self._container_layout.count() - 1, header
            )

            for match in bucket_matches:
                row = MatchRowCard(match)
                row.clicked.connect(self._on_match_clicked)
                self._container_layout.insertWidget(
                    self._container_layout.count() - 1, row
                )

        Animator.fade_in(self._container, duration=200)

    def _apply_filters(self, matches: list[dict]) -> list[dict]:
        out = matches
        if self._source_filter == _SOURCE_PERSONAL:
            out = [m for m in out if not m.get("is_pro")]
        elif self._source_filter == _SOURCE_PRO:
            out = [m for m in out if m.get("is_pro")]
        if self._map_filter != _MAP_ALL:
            out = [
                m
                for m in out
                if map_short_name(m.get("demo_name", "")).lower() == self._map_filter
            ]
        return out

    # ── Map chip rebuild ──

    def _rebuild_map_chips(self) -> None:
        # Clear existing map chips (preserve trailing stretch)
        while self._map_row.count() > 1:
            item = self._map_row.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._map_chips.clear()

        # Count maps in current source-filtered set
        scoped = self._all_matches
        if self._source_filter == _SOURCE_PERSONAL:
            scoped = [m for m in scoped if not m.get("is_pro")]
        elif self._source_filter == _SOURCE_PRO:
            scoped = [m for m in scoped if m.get("is_pro")]

        counts: dict[str, int] = defaultdict(int)
        for m in scoped:
            short = map_short_name(m.get("demo_name", "")).lower()
            if short in {"—", "unknown map", ""}:
                continue
            counts[short] += 1

        if not counts:
            self._map_row_widget.setVisible(False)
            return

        self._map_row_widget.setVisible(True)

        all_chip = FilterChip(
            "All maps",
            checked=(self._map_filter == _MAP_ALL),
            count=sum(counts.values()),
        )
        all_chip.toggled.connect(lambda _checked: self._on_map_chip(_MAP_ALL))
        self._map_row.insertWidget(self._map_row.count() - 1, all_chip)
        self._map_chips[_MAP_ALL] = all_chip

        # Sort maps by count (descending), cap to top 8 to keep the row scannable
        for short, count in sorted(counts.items(), key=lambda kv: -kv[1])[:8]:
            chip = FilterChip(
                short.title(),
                checked=(self._map_filter == short),
                count=count,
            )
            chip.toggled.connect(lambda _checked, k=short: self._on_map_chip(k))
            self._map_row.insertWidget(self._map_row.count() - 1, chip)
            self._map_chips[short] = chip

    # ── Filter handlers ──

    def _on_source_chip(self, key: str) -> None:
        # Single-select: ensure only the clicked one stays checked, others off
        for k, chip in self._source_chips.items():
            chip.set_checked(k == key)
        self._source_filter = key
        self._rebuild_map_chips()  # map counts depend on source scope
        self._render_filtered()

    def _on_map_chip(self, key: str) -> None:
        for k, chip in self._map_chips.items():
            chip.set_checked(k == key)
        self._map_filter = key
        self._render_filtered()

    def _reset_filters(self) -> None:
        self._on_source_chip(_SOURCE_ALL)
        self._on_map_chip(_MAP_ALL)

    # ── Misc ──

    def _on_match_clicked(self, demo_name: str) -> None:
        self.match_selected.emit(demo_name)

    def _navigate_home(self) -> None:
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen("home")

    def _update_count_chip(self, count: int) -> None:
        self._count_chip.set_label(f"{count} matches")
        self._count_chip.set_severity("online" if count > 0 else "neutral")

    def _clear_container(self) -> None:
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
