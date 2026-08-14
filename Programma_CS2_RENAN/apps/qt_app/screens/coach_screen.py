"""Coach — RAP Coach Dashboard per frames 06/07.

Row 1 (50/50): Belief State Confidence (COACH ring + drivers list) and
Recent Insights (severity-worded rows). Row 2: Advanced Analytics empty
state. Bottom: an embedded ``ChatPanel`` dock wired to
``CoachingChatViewModel``, toggled by the top-right Chat button. The old
standalone "LLM Coach" card dissolved into a compact model combo beside
the chat header.

VM contracts are unchanged — both ``CoachViewModel`` and
``CoachingChatViewModel`` interact through the same signals as before.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import severity_bucket, severity_color
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.viewmodels.coach_vm import CoachViewModel
from Programma_CS2_RENAN.apps.qt_app.viewmodels.coaching_chat_vm import CoachingChatViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.coaching import ChatPanel
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.drivers_list import DriversList
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.progress_ring import ProgressRing
from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_coach")

_QUICK_ACTION_KEYS = [
    ("quick_action_positioning", "How can I improve positioning?"),
    ("quick_action_utility", "Analyze utility usage"),
    ("quick_action_focus", "What should I focus on improving?"),
]

# map-SSOT (CP0 #2): alternation comes from the authority list.
from Programma_CS2_RENAN.core.known_maps import MAP_NAME_RE as _MAP_RE

_EM_DASH = "—"


def _map_from_demo(demo_name: str) -> str:
    if not demo_name:
        return ""
    m = _MAP_RE.search(demo_name.lower())
    return m.group(1).title() if m else ""


# Ranking order for the top-3 shortlist (research 29.4): severity bucket
# first; Python's stable sort then preserves the VM's recency-desc order
# within each bucket.
_SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


class CoachScreen(QWidget):
    """RAP Coach Dashboard + embedded chat dock (frames 06/07)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._coach_vm = CoachViewModel()
        self._chat_vm = CoachingChatViewModel()
        self._state_connected = False
        self._chat_open = False
        self._chat_online = False
        self._llm_model_name = str(get_setting("LLM_COACH_MODEL", "") or "")
        self._llm_models_loaded = False
        self._insight_widgets: list[QWidget] = []
        self._last_insights: list[dict] = []
        # Belief drivers — sample count is reachable today via AppState
        # total_matches; the rest have no data source yet and render "—".
        # # FIELD-GAP: complete/partial/none demo-quality counts (frame 06
        # # "Data quality" driver) — no parser-quality column exists yet.
        # # FIELD-GAP: per-map coverage counts (frame 06 "Map coverage"
        # # driver) — needs a distinct-map aggregate the VM doesn't expose.
        self._driver_stats: dict = {
            "samples": None,
            "complete": None,
            "partial": None,
            "none": None,
            "maps_seen": None,
            "maps_total": None,
        }
        # True while a stream is mid-flight and the trailing coach bubble is
        # the live one (ChatPanel.update_last_message targets it) — the old
        # QFrame handle is no longer needed.
        self._streaming_active = False

        self._coach_vm.insights_loaded.connect(self._on_insights)
        self._chat_vm.messages_changed.connect(self._render_messages)
        self._chat_vm.is_loading_changed.connect(self._on_chat_loading)
        # R4 LOW / DR-14: streamed chunks live-update the trailing coach
        # bubble instead of a detached label.
        self._chat_vm.streaming_changed.connect(self._on_stream_progress)
        self._chat_vm.is_available_changed.connect(self._on_chat_availability)

        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self) -> None:
        state = get_app_state()
        if not self._state_connected:
            state.belief_confidence_changed.connect(self._on_belief)
            state.total_matches_changed.connect(self._on_total_matches)
            self._state_connected = True
        current = state.cached_state.get("belief_confidence", 0.0)
        if current > 0:
            self._on_belief(current)
        total = state.cached_state.get("total_matches")
        if total:
            self._on_total_matches(int(total))
        self._coach_vm.load_insights()
        self._chat_vm.check_availability()
        # Lazy-populate the model combo on first show — Ollama /api/tags is
        # a local call but still deferred past __init__ for snappy startup.
        if not self._llm_models_loaded:
            self._refresh_llm_models()

    def on_leave(self) -> None:
        self._typing_label.setVisible(False)

    def retranslate(self) -> None:
        self._title_label.setText(i18n.get_text("coach.page_title", "RAP Coach Dashboard"))
        self._chat_toggle_btn.setText(i18n.get_text("chat.title", "Chat"))
        self._belief_card.set_title(i18n.get_text("belief_state"))
        self._belief_desc1.setText(i18n.get_text("belief_desc"))
        self._belief_desc2.setText(
            i18n.get_text("belief_desc_2", "This grows as you ingest more of your own matches.")
        )
        self._drivers_caption.setText(i18n.get_text("coach.drivers", "Drivers:"))
        self._confidence_caption.setText(
            i18n.get_text("coach.confidence_grows", "confidence grows as you ingest more maps")
        )
        self._update_drivers()
        self._insights_card.set_title(i18n.get_text("recent_insights"))
        # Driver rows + the n-chip are i18n-composed from cached stats —
        # re-render them in the new language.
        self._update_drivers()
        self._on_insights(list(self._last_insights))
        self._analytics_card.set_title(
            i18n.get_text("coach.advanced_analytics", "Advanced Analytics")
        )
        self._analytics_empty.set_title(
            i18n.get_text(
                "coach.analytics_empty_title",
                "Trend graphs and radar charts will appear here after demo analysis.",
            )
        )
        self._analytics_empty.set_description(
            i18n.get_text("coach.analytics_empty_desc", "Analyze matches to populate this section.")
        )
        self._llm_caption.setText(i18n.get_text("coach.llm_model", "Model"))
        self._llm_refresh_btn.setToolTip(
            i18n.get_text("coach.llm_refresh_tip", "Re-query Ollama for installed models")
        )
        self._typing_label.setText(i18n.get_text("coach_thinking"))
        self._chat_panel.set_suggestions(self._suggestion_texts())

    # ── UI Construction ──

    def _build_ui(self) -> None:
        tokens = get_tokens()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Main scrollable surface ──
        self._main_scroll = QScrollArea()
        self._main_scroll.setWidgetResizable(True)
        self._main_scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        content_layout.setSpacing(tokens.spacing_lg)

        # Title rail — h1 + Chat toggle (frame 06 top-right)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(tokens.spacing_md)

        self._title_label = QLabel(i18n.get_text("coach.page_title", "RAP Coach Dashboard"))
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)

        self._chat_toggle_btn = make_button(
            i18n.get_text("chat.title", "Chat"), variant="secondary", fixed_width=100
        )
        self._chat_toggle_btn.setFixedHeight(32)
        self._chat_toggle_btn.clicked.connect(self._toggle_chat)
        title_row.addWidget(self._chat_toggle_btn)
        content_layout.addLayout(title_row)

        # Row 1 — Belief (left) + Recent Insights (right), 50/50
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(tokens.spacing_lg)
        self._belief_card = self._build_belief_card()
        row1.addWidget(self._belief_card, 1)
        self._insights_card = self._build_insights_card()
        row1.addWidget(self._insights_card, 1)
        content_layout.addLayout(row1)

        # Row 2 — Advanced Analytics (empty until charts exist)
        self._analytics_card = self._build_analytics_card()
        content_layout.addWidget(self._analytics_card)

        content_layout.addStretch(1)
        self._main_scroll.setWidget(content)
        root.addWidget(self._main_scroll, 1)

        # ── Chat dock (frame 07) — hidden until the Chat button opens it ──
        self._chat_dock = self._build_chat_dock()
        self._chat_dock.setVisible(False)
        root.addWidget(self._chat_dock)

    def _build_belief_card(self) -> Card:
        tokens = get_tokens()
        card = Card(title=i18n.get_text("belief_state"), depth="raised")
        body = card.content_layout
        body.setSpacing(tokens.spacing_sm)

        self._belief_desc1 = QLabel(i18n.get_text("belief_desc"))
        self._belief_desc2 = QLabel(
            i18n.get_text("belief_desc_2", "This grows as you ingest more of your own matches.")
        )
        for label in (self._belief_desc1, self._belief_desc2):
            label.setWordWrap(True)
            label.setFont(Typography.font("body"))
            label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
            body.addWidget(label)

        ring_row = QHBoxLayout()
        ring_row.setContentsMargins(0, tokens.spacing_sm, 0, 0)
        ring_row.setSpacing(tokens.spacing_lg)

        self._belief_ring = ProgressRing(value=0.0, size=ProgressRing.COACH, thickness=8)

        # Ring + sample-size chip beneath (research 29.3: "trust is a
        # designed surface" — the belief % is only believable next to the
        # evidence count it rests on). Fed by the same driver wiring as the
        # sample-count row: _on_total_matches (live) / _set_driver_stats
        # (fixture) both land in _update_drivers(). Hidden until a count
        # exists — never renders "n=— demos".
        ring_col = QVBoxLayout()
        ring_col.setContentsMargins(0, 0, 0, 0)
        ring_col.setSpacing(tokens.spacing_xs)
        ring_col.addWidget(self._belief_ring, 0, Qt.AlignHCenter)
        self._belief_n_chip = QLabel("")
        self._belief_n_chip.setFont(Typography.font("mono"))
        self._belief_n_chip.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        self._belief_n_chip.setAlignment(Qt.AlignHCenter)
        self._belief_n_chip.setVisible(False)
        ring_col.addWidget(self._belief_n_chip)
        ring_col.addStretch(1)
        ring_row.addLayout(ring_col)

        drivers_col = QVBoxLayout()
        drivers_col.setContentsMargins(0, 0, 0, 0)
        drivers_col.setSpacing(tokens.spacing_sm)

        self._drivers_caption = QLabel(i18n.get_text("coach.drivers", "Drivers:"))
        self._drivers_caption.setFont(Typography.font("body"))
        self._drivers_caption.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        drivers_col.addWidget(self._drivers_caption)

        self._drivers_list = DriversList()
        drivers_col.addWidget(self._drivers_list)

        self._confidence_caption = QLabel(
            i18n.get_text("coach.confidence_grows", "confidence grows as you ingest more maps")
        )
        # Mixed-case small accent line (frame 07) — the caption Typography
        # role force-uppercases, so downsize the body font via QSS instead.
        self._confidence_caption.setFont(Typography.font("body"))
        self._confidence_caption.setStyleSheet(
            f"color: {tokens.accent_primary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        self._confidence_caption.setWordWrap(True)
        drivers_col.addWidget(self._confidence_caption)
        drivers_col.addStretch(1)

        ring_row.addLayout(drivers_col, 1)
        body.addLayout(ring_row)
        self._update_drivers()
        return card

    def _build_insights_card(self) -> Card:
        tokens = get_tokens()
        card = Card(title=i18n.get_text("recent_insights"), depth="raised")
        self._insights_container = card.content_layout
        self._insights_container.setSpacing(tokens.spacing_md)

        self._insights_empty = EmptyState(
            icon_text="◌",
            title=i18n.get_text("coach.no_insights_title", "No insights yet"),
            description=i18n.get_text(
                "coach.no_insights_desc",
                "Once you analyze a few demos, coaching insights will land here automatically.",
            ),
        )
        self._insights_container.addWidget(self._insights_empty)
        return card

    def _build_analytics_card(self) -> Card:
        card = Card(
            title=i18n.get_text("coach.advanced_analytics", "Advanced Analytics"), depth="raised"
        )
        self._analytics_empty = EmptyState(
            title=i18n.get_text(
                "coach.analytics_empty_title",
                "Trend graphs and radar charts will appear here after demo analysis.",
            ),
            description=i18n.get_text(
                "coach.analytics_empty_desc", "Analyze matches to populate this section."
            ),
        )
        card.content_layout.addWidget(self._analytics_empty)
        return card

    # ── Chat dock ──

    def _build_chat_dock(self) -> QFrame:
        tokens = get_tokens()
        dock = QFrame()
        dock.setObjectName("coach_chat_dock")
        dock.setStyleSheet(
            f"QFrame#coach_chat_dock {{ "
            f"background-color: {tokens.surface_sidebar}; "
            f"border-top: 1px solid {tokens.border_subtle}; "
            f"}}"
        )
        dock.setFixedHeight(470)
        layout = QVBoxLayout(dock)
        layout.setContentsMargins(
            tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm
        )
        layout.setSpacing(tokens.spacing_sm)

        # Model picker row beside the chat header — the old standalone
        # "LLM Coach" card dissolved into this compact combo (kept
        # capability: discover Ollama models, persist the pick).
        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(tokens.spacing_sm)

        self._typing_label = QLabel(i18n.get_text("coach_thinking"))
        self._typing_label.setFont(Typography.font("body"))
        self._typing_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        self._typing_label.setVisible(False)
        model_row.addWidget(self._typing_label)
        model_row.addStretch(1)

        self._llm_caption = QLabel(i18n.get_text("coach.llm_model", "Model"))
        self._llm_caption.setFont(Typography.font("caption"))
        self._llm_caption.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
        model_row.addWidget(self._llm_caption)

        self._llm_model_combo = QComboBox()
        self._llm_model_combo.setFixedHeight(28)
        self._llm_model_combo.setMinimumWidth(160)
        self._llm_model_combo.setMaximumWidth(260)
        if self._llm_model_name:
            # Reflect the saved pick before discovery so the header caption
            # and combo agree on cold start.
            self._llm_model_combo.addItem(self._llm_model_name, self._llm_model_name)
        self._llm_model_combo.currentTextChanged.connect(self._on_llm_model_picked)
        model_row.addWidget(self._llm_model_combo)

        self._llm_refresh_btn = make_button("↻", variant="ghost", fixed_width=28)
        self._llm_refresh_btn.setFixedHeight(28)
        self._llm_refresh_btn.setToolTip(
            i18n.get_text("coach.llm_refresh_tip", "Re-query Ollama for installed models")
        )
        self._llm_refresh_btn.clicked.connect(self._refresh_llm_models)
        model_row.addWidget(self._llm_refresh_btn)
        layout.addLayout(model_row)

        # Frame-07 chat surface — VM-agnostic panel; the screen wires it.
        self._chat_panel = ChatPanel()
        self._chat_panel.message_submitted.connect(self._chat_vm.send_message)
        self._chat_panel.suggestion_clicked.connect(self._chat_vm.send_message)
        self._chat_panel.set_suggestions(self._suggestion_texts())
        # ChatPanel owns Clear/collapse internally; this screen routes them
        # to the VM and the dock instead (same-package rewiring — the dock,
        # not the panel body, is what frames 06/07 collapse).
        self._chat_panel._clear_btn.clicked.disconnect()
        self._chat_panel._clear_btn.clicked.connect(self._on_clear_clicked)
        self._chat_panel._collapse_btn.clicked.disconnect()
        self._chat_panel._collapse_btn.clicked.connect(self._toggle_chat)
        layout.addWidget(self._chat_panel, 1)

        return dock

    def _suggestion_texts(self) -> list[str]:
        return [i18n.get_text(key, fallback) for key, fallback in _QUICK_ACTION_KEYS]

    # ── Actions ──

    def _toggle_chat(self) -> None:
        self._set_chat_open(not self._chat_open)
        if self._chat_open:
            player = get_setting("CS2_PLAYER_NAME", "")
            if player:
                self._chat_vm.check_and_start(player)
            else:
                self._chat_vm.check_availability()

    def _set_chat_open(self, open_: bool) -> None:
        """Pure UI toggle — shows/hides the dock, kicks no VM work."""
        self._chat_open = bool(open_)
        self._chat_dock.setVisible(self._chat_open)

    def _on_clear_clicked(self) -> None:
        # Clear locally first so a degraded engine (clear_session returning
        # early) still leaves a clean panel; the VM's messages_changed([])
        # re-render is then a no-op.
        self._streaming_active = False  # any in-flight stream lost its bubble
        self._chat_panel.clear()
        self._chat_vm.clear_session()

    # ── LLM model picker ──

    def _refresh_llm_models(self) -> None:
        """Re-query Ollama and rebuild the model combo.

        Runs on the main thread because /api/tags is local with a short
        timeout; plumbing a Worker would cost more than the request.
        """
        from Programma_CS2_RENAN.backend.services.llm_service import get_llm_service

        try:
            service = get_llm_service()
            models = service.list_models()
        except Exception as exc:  # noqa: BLE001 — degraded picker beats a dead screen
            logger.warning("ollama model discovery failed: %s", exc)
            return

        self._llm_model_combo.blockSignals(True)
        self._llm_model_combo.clear()
        if not models:
            self._llm_model_combo.addItem(
                i18n.get_text("coach.llm_no_models", "no models found — run: ollama pull"), ""
            )
            self._llm_model_combo.setEnabled(False)
            self._llm_model_combo.blockSignals(False)
            return

        self._llm_model_combo.setEnabled(True)
        # Gemma family first (production default), then alphabetical.
        models.sort(key=lambda m: (not m["name"].startswith("gemma"), m["name"]))
        for m in models:
            size_mb = m["size"] // (1024 * 1024) if m["size"] else 0
            label = f"{m['name']}  ({size_mb} MB)" if size_mb else m["name"]
            self._llm_model_combo.addItem(label, m["name"])

        saved = self._llm_model_name
        idx = 0
        if saved:
            idx = -1
            for i in range(self._llm_model_combo.count()):
                if self._llm_model_combo.itemData(i) == saved:
                    idx = i
                    break
            if idx < 0:
                # The persisted pick isn't installed anymore — keep advertising
                # the SAVED name (truth vs the persisted backend key) instead of
                # silently swapping to whatever Ollama lists first. Selecting a
                # real model later persists exactly as before.
                not_installed = i18n.get_text("coach.llm_not_installed", "not installed")
                self._llm_model_combo.insertItem(0, f"{saved} ({not_installed})", saved)
                idx = 0
        self._llm_model_combo.setCurrentIndex(idx)
        self._llm_model_combo.blockSignals(False)
        picked = self._llm_model_combo.itemData(idx)
        if isinstance(picked, str) and picked:
            self._llm_model_name = picked
            self._apply_chat_status()
        self._llm_models_loaded = True

    def _on_llm_model_picked(self, _label: str) -> None:
        """Persist the pick (bare model name lives on the item's userData)."""
        from Programma_CS2_RENAN.core.config import save_user_setting

        idx = self._llm_model_combo.currentIndex()
        if idx < 0:
            return
        model_name = self._llm_model_combo.itemData(idx)
        if not model_name or not isinstance(model_name, str):
            return
        save_user_setting("LLM_COACH_MODEL", model_name)
        self._llm_model_name = model_name
        self._apply_chat_status()

    def _set_llm_model(self, name: str) -> None:
        """Reflect ``name`` in the combo + header caption WITHOUT persisting
        (state-sync slot — also the harness fixture's entry point)."""
        if not name:
            return
        self._llm_model_name = name
        combo = self._llm_model_combo
        combo.blockSignals(True)
        idx = -1
        for i in range(combo.count()):
            if combo.itemData(i) == name:
                idx = i
                break
        if idx < 0:
            combo.addItem(name, name)
            idx = combo.count() - 1
        combo.setCurrentIndex(idx)
        combo.setEnabled(True)
        combo.blockSignals(False)
        self._apply_chat_status()

    def _apply_chat_status(self) -> None:
        if self._llm_model_name:
            self._chat_panel.set_status(self._chat_online, "ollama", self._llm_model_name)
        else:
            # No model known yet — skip the backend caption entirely rather
            # than render a dangling "ollama · ".
            self._chat_panel.set_status(self._chat_online, "", "")

    # ── Signal slots ──

    def _on_belief(self, confidence: float) -> None:
        # AppState emits 0..1 (or 0..100 historically). Normalize.
        normalized = float(confidence)
        if normalized > 1.0:
            normalized = normalized / 100.0
        normalized = max(0.0, min(1.0, normalized))
        # Sweep only on a real change — repeated polls must not re-animate.
        if abs(normalized - getattr(self, "_last_belief", -1.0)) < 0.001:
            return
        self._last_belief = normalized
        Animator.sweep_ring(self._belief_ring, normalized)

    def _on_total_matches(self, total: int) -> None:
        self._driver_stats["samples"] = int(total)
        self._update_drivers()

    def _set_driver_stats(self, stats: dict) -> None:
        """Merge driver stats (fixture / future VM aggregate) and re-render."""
        self._driver_stats.update(stats or {})
        self._update_drivers()

    def _update_drivers(self) -> None:
        s = self._driver_stats

        def fmt(value) -> str:
            return _EM_DASH if value is None else str(value)

        sample_text = i18n.get_text(
            "coach.driver_sample", "Sample count · {n} personal demos analyzed"
        ).format(n=fmt(s.get("samples")))
        quality_text = i18n.get_text(
            "coach.driver_quality",
            "Data quality · {complete} complete · {partial} partial · {none} none",
        ).format(
            complete=fmt(s.get("complete")), partial=fmt(s.get("partial")), none=fmt(s.get("none"))
        )
        maps_text = i18n.get_text(
            "coach.driver_maps", "Map coverage · {seen} of {total} competitive maps seen"
        ).format(seen=fmt(s.get("maps_seen")), total=fmt(s.get("maps_total")))

        rows = [
            ("success" if s.get("samples") else "warning", sample_text),
            # Unknown data → neutral square (DriversList falls back to tertiary).
            ("success" if s.get("complete") is not None else "", quality_text),
            ("warning" if s.get("maps_seen") is not None else "", maps_text),
        ]
        self._drivers_list.set_rows(rows)

        # Sample-size chip under the belief ring — same source of truth.
        samples = s.get("samples")
        if samples is None:
            self._belief_n_chip.setVisible(False)
        else:
            self._belief_n_chip.setText(
                i18n.get_text("coach.belief_n", "n={n} demos").format(n=samples)
            )
            self._belief_n_chip.setVisible(True)

    def _on_insights(self, insights: list) -> None:
        self._last_insights = list(insights or [])
        for w in self._insight_widgets:
            self._insights_container.removeWidget(w)
            w.deleteLater()
        self._insight_widgets.clear()

        if not insights:
            self._insights_empty.set_title(
                i18n.get_text("coach.no_insights_title", "No insights yet")
            )
            self._insights_empty.set_description(
                i18n.get_text(
                    "coach.no_insights_desc",
                    "Once you analyze a few demos, coaching insights will land here automatically.",
                )
            )
            self._insights_empty.setVisible(True)
            return

        self._insights_empty.setVisible(False)

        # Research 29.4 (Garmin Catalyst "3 Opportunities"): advice ships as
        # a ranked shortlist of exactly three, never a 10-row dump. Severity
        # buckets rank first; recency (the VM's emit order) breaks ties.
        ranked = sorted(
            self._last_insights,
            key=lambda i: _SEV_ORDER[severity_bucket(i.get("severity", ""))],
        )
        top, overflow = ranked[:3], ranked[3:]

        for rank, insight in enumerate(top, start=1):
            row = self._build_insight_row(insight, rank=rank)
            self._insights_container.addWidget(row)
            self._insight_widgets.append(row)

        if overflow:
            self._insights_overflow = QWidget()
            overflow_col = QVBoxLayout(self._insights_overflow)
            overflow_col.setContentsMargins(0, 0, 0, 0)
            overflow_col.setSpacing(get_tokens().spacing_md)
            for insight in overflow:
                overflow_col.addWidget(self._build_insight_row(insight))
            # Collapsed on every reload — the shortlist is the default view.
            self._insights_overflow.setVisible(False)
            self._insights_container.addWidget(self._insights_overflow)
            self._insight_widgets.append(self._insights_overflow)

            self._show_all_btn = make_button(
                self._overflow_btn_text(expanded=False), variant="ghost"
            )
            self._show_all_btn.clicked.connect(self._toggle_insights_overflow)
            self._insights_container.addWidget(self._show_all_btn, 0, Qt.AlignLeft)
            self._insight_widgets.append(self._show_all_btn)

    def _overflow_btn_text(self, expanded: bool) -> str:
        if expanded:
            return i18n.get_text("coach.show_top", "Show top 3")
        return i18n.get_text("coach.show_all", "Show all ({n})").format(n=len(self._last_insights))

    def _toggle_insights_overflow(self) -> None:
        expanded = not self._insights_overflow.isVisible()
        self._insights_overflow.setVisible(expanded)
        self._show_all_btn.setText(self._overflow_btn_text(expanded))

    def _build_insight_row(self, insight: dict, rank: int | None = None) -> QWidget:
        """Flat frame-06 insight row: bold title + severity word right,
        desc, mono provenance + timestamp caption.

        ``rank`` (1-based) prints an accent-mono 01/02/03 numeral left of
        the title — only the severity-ranked top three carry one.
        """
        tokens = get_tokens()
        bucket = severity_bucket(insight.get("severity", ""))
        # severity_color maps the bucket words directly: high→error,
        # medium→warning, low→success — identical to the old local dict.
        sev_color = severity_color(bucket).name()
        sev_word = {
            "high": i18n.get_text("coach.sev_high", "High"),
            "medium": i18n.get_text("coach.sev_medium", "Medium"),
            "low": i18n.get_text("coach.sev_low", "Low"),
        }[bucket]

        row = QWidget()
        body = QVBoxLayout(row)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(tokens.spacing_xs)

        # Optional pro context (accent caption, frame 06 first row)
        if insight.get("is_pro"):
            player = insight.get("player_name") or "Pro"
            map_tag = _map_from_demo(insight.get("demo_name", ""))
            if map_tag:
                ctx_text = i18n.get_text(
                    "coach.pro_analysis", "Pro Analysis: {player} on {map}"
                ).format(player=player, map=map_tag)
            else:
                ctx_text = i18n.get_text(
                    "coach.pro_analysis_nomap", "Pro Analysis: {player}"
                ).format(player=player)
            ctx = QLabel(ctx_text)
            ctx.setTextFormat(Qt.PlainText)
            # Mixed-case per frame 06 ("Pro Analysis: ZywOo on Mirage") —
            # caption Typography would force-uppercase it.
            ctx.setFont(Typography.font("body"))
            ctx.setStyleSheet(
                f"color: {tokens.accent_primary}; background: transparent; "
                f"font-size: {tokens.font_size_caption}px;"
            )
            body.addWidget(ctx)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(tokens.spacing_sm)

        if rank is not None:
            rank_lbl = QLabel(f"{rank:02d}")
            rank_lbl.setFont(Typography.font("mono", weight=700))
            rank_lbl.setStyleSheet(
                f"color: {tokens.accent_primary}; background: transparent; "
                f"font-size: {tokens.font_size_subtitle}px;"
            )
            title_row.addWidget(rank_lbl, 0, Qt.AlignTop)

        title = QLabel(insight.get("title", ""))
        title.setTextFormat(Qt.PlainText)  # FE-01 — block HTML rendering
        title.setFont(Typography.font("subtitle"))
        title.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        title_row.addWidget(title)
        title_row.addStretch(1)

        sev_label = QLabel(sev_word)
        sev_label.setFont(Typography.font("subtitle"))
        sev_label.setStyleSheet(f"color: {sev_color}; background: transparent;")
        title_row.addWidget(sev_label, 0, Qt.AlignTop)
        body.addLayout(title_row)

        message = insight.get("message", "")
        if message:
            msg = QLabel(message)
            msg.setTextFormat(Qt.PlainText)
            msg.setWordWrap(True)
            msg.setFont(Typography.font("body"))
            msg.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
            body.addWidget(msg)

        # ── Mono provenance line (research 29.3: provenance badges on every
        # AI claim). Composed ONLY from fields the CoachViewModel payload
        # actually carries: focus_area · source demo file · created_at.
        # Absent segments are omitted — never faked with placeholders.
        # # FIELD-GAP: model/confidence/reference provenance ("RAP-Pedagogy
        # # · conf 0.82 · 4 demos") — CoachingInsight rows expose no such
        # # columns; chat bubbles already render those fields when their
        # # payload carries them (_compose_meta), so nothing is duplicated
        # # or invented here.
        # # FIELD-GAP: "revalidated {date}" caption for advice older than
        # # the latest model retrain — no retrain-timestamp field reaches
        # # any qt_app VM payload today.
        focus = insight.get("focus_area") or ""
        demo_src = str(insight.get("demo_name") or "")
        date_str = str(insight.get("created_at") or "")
        provenance = " · ".join(seg for seg in (str(focus).lower(), demo_src) if seg)
        if provenance or date_str:
            meta_row = QHBoxLayout()
            meta_row.setContentsMargins(0, 0, 0, 0)
            if provenance:
                prov_lbl = QLabel(provenance)
                prov_lbl.setTextFormat(Qt.PlainText)
                prov_lbl.setFont(Typography.font("mono"))
                prov_lbl.setStyleSheet(
                    f"color: {tokens.text_tertiary}; background: transparent; "
                    f"font-size: {tokens.font_size_caption}px;"
                )
                meta_row.addWidget(prov_lbl)
            meta_row.addStretch(1)
            if date_str:
                date_lbl = QLabel(date_str)
                date_lbl.setFont(Typography.font("mono"))
                date_lbl.setStyleSheet(
                    f"color: {tokens.text_tertiary}; background: transparent; "
                    f"font-size: {tokens.font_size_caption}px;"
                )
                meta_row.addWidget(date_lbl)
            body.addLayout(meta_row)

        return row

    # ── Chat slots ──

    def _render_messages(self, messages: list) -> None:
        self._streaming_active = False
        self._chat_panel.clear()
        for msg in messages:
            role_raw = msg.get("role", "assistant")
            if role_raw == "user":
                role = "user"
            elif role_raw == "system":
                role = "system"
            else:
                role = "coach"
            meta = self._compose_meta(msg)
            self._chat_panel.add_message(role, str(msg.get("content", "")), meta or None)

    @staticmethod
    def _compose_meta(msg: dict) -> str:
        """Mono footnote from optional payload confidence fields.

        # FIELD-GAP: CoachingChatViewModel rows carry only role/content
        # today; these are the names a confidence-annotated payload WOULD
        # use (frame 07: "confidence 0.82 · 4 demos referenced ·
        # RAP-Pedagogy"). Absent fields simply omit the footnote.
        """
        parts: list[str] = []
        conf = msg.get("confidence")
        if conf is not None:
            parts.append(
                i18n.get_text("coach.meta_confidence", "confidence {v}").format(
                    v=f"{float(conf):.2f}"
                )
            )
        refs = msg.get("references", msg.get("demos_referenced"))
        if refs:
            parts.append(i18n.get_text("coach.meta_refs", "{n} demos referenced").format(n=refs))
        source = msg.get("source")
        if source:
            parts.append(str(source))
        return " · ".join(parts)

    def _on_stream_progress(self, accumulated: str) -> None:
        """DR-14: live-update the trailing coach bubble as chunks land.
        The final committed message still arrives via messages_changed."""
        if not accumulated:
            return
        self._typing_label.setVisible(False)
        if not self._streaming_active:
            # First chunk creates the bubble; later chunks update it via
            # the panel's public streaming API.
            self._chat_panel.add_message("coach", accumulated)
            self._streaming_active = True
        else:
            self._chat_panel.update_last_message(accumulated)

    def _on_chat_loading(self, loading: bool) -> None:
        self._typing_label.setVisible(bool(loading))
        if not loading:
            # A cancelled stream never re-emits messages_changed — drop the
            # stale streaming state here as well.
            self._streaming_active = False

    def _on_chat_availability(self, available: bool) -> None:
        self._chat_online = bool(available)
        self._apply_chat_status()
