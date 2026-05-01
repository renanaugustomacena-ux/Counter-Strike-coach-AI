"""Coach — AI coaching surface with insights + collapsible chat composer.

Top section is the analytics surface (belief ring + recent insights);
the chat composer slides up from the bottom on demand. Both areas use
the redesigned chrome (cards, status chip, accent borders, mono code
where appropriate) and route every color through ``get_tokens()`` so
themes propagate.

VM contracts are unchanged — both ``CoachViewModel`` and
``CoachingChatViewModel`` interact through the same signals as before.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.viewmodels.coach_vm import CoachViewModel
from Programma_CS2_RENAN.apps.qt_app.viewmodels.coaching_chat_vm import (
    CoachingChatViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.progress_ring import ProgressRing
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_coach")

_QUICK_ACTION_KEYS = [
    ("quick_action_positioning", "How can I improve positioning?"),
    ("quick_action_utility", "Analyze utility usage"),
    ("quick_action_focus", "What should I focus on improving?"),
]

_MAP_RE = re.compile(
    r"(mirage|inferno|dust2|overpass|ancient|anubis|nuke|vertigo|train)"
)


def _map_from_demo(demo_name: str) -> str:
    if not demo_name:
        return ""
    m = _MAP_RE.search(demo_name.lower())
    return m.group(1).title() if m else ""


def _severity_color(severity: str, tokens) -> str:
    sev = (severity or "").lower()
    if sev == "high":
        return tokens.error
    if sev == "medium":
        return tokens.warning
    return tokens.success


class CoachScreen(QWidget):
    """AI coach dashboard + chat composer."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._coach_vm = CoachViewModel()
        self._chat_vm = CoachingChatViewModel()
        self._state_connected = False
        self._chat_open = False
        self._insight_widgets: list[QFrame] = []

        self._coach_vm.insights_loaded.connect(self._on_insights)
        self._chat_vm.messages_changed.connect(self._render_messages)
        self._chat_vm.is_loading_changed.connect(self._on_chat_loading)
        self._chat_vm.is_available_changed.connect(self._on_chat_availability)

        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self) -> None:
        if not self._state_connected:
            get_app_state().belief_confidence_changed.connect(self._on_belief)
            self._state_connected = True
        current = get_app_state().cached_state.get("belief_confidence", 0.0)
        if current > 0:
            self._on_belief(current)
        self._coach_vm.load_insights()
        self._chat_vm.check_availability()

    def on_leave(self) -> None:
        self._typing_label.setVisible(False)

    def retranslate(self) -> None:
        self._title_label.setText(i18n.get_text("rap_coach_dashboard"))
        self._belief_card.set_title(i18n.get_text("belief_state"))
        self._belief_desc_label.setText(i18n.get_text("belief_desc"))
        self._insights_card.set_title(i18n.get_text("recent_insights"))
        self._typing_label.setText(i18n.get_text("coach_thinking"))
        self._chat_input.setPlaceholderText(i18n.get_text("ask_your_coach"))
        for btn, key in self._qa_buttons:
            btn.setText(i18n.get_text(key))

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

        # Title rail with chat toggle on the right
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(tokens.spacing_md)

        self._title_label = QLabel(i18n.get_text("rap_coach_dashboard"))
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)

        self._chat_status_chip = StatusChip("Coach: Checking…", severity="neutral")
        title_row.addWidget(self._chat_status_chip)

        self._chat_toggle_btn = make_button(
            "Open chat", variant="secondary", fixed_width=120
        )
        self._chat_toggle_btn.setFixedHeight(32)
        self._chat_toggle_btn.clicked.connect(self._toggle_chat)
        title_row.addWidget(self._chat_toggle_btn)
        content_layout.addLayout(title_row)

        # Belief confidence card
        self._belief_card = self._build_belief_card()
        content_layout.addWidget(self._belief_card)

        # Insights card
        self._insights_card = self._build_insights_card()
        content_layout.addWidget(self._insights_card)

        content_layout.addStretch(1)
        self._main_scroll.setWidget(content)
        root.addWidget(self._main_scroll, 1)

        # ── Chat panel (sticky bottom, hidden by default) ──
        self._chat_panel = self._build_chat_panel()
        self._chat_panel.setVisible(False)
        root.addWidget(self._chat_panel)

    def _build_belief_card(self) -> Card:
        tokens = get_tokens()
        card = Card(title=i18n.get_text("belief_state"), depth="raised")
        body = card.content_layout
        body.setSpacing(tokens.spacing_md)

        self._belief_desc_label = QLabel(i18n.get_text("belief_desc"))
        self._belief_desc_label.setWordWrap(True)
        self._belief_desc_label.setFont(Typography.font("body"))
        self._belief_desc_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        body.addWidget(self._belief_desc_label)

        ring_row = QHBoxLayout()
        ring_row.setContentsMargins(0, 0, 0, 0)
        self._belief_ring = ProgressRing(value=0.0, size=96, thickness=8)
        ring_row.addWidget(self._belief_ring)

        # Adjacent context: caption + numeric label
        ctx = QVBoxLayout()
        ctx.setContentsMargins(0, 0, 0, 0)
        ctx.setSpacing(2)

        ctx_caption = QLabel("BELIEF CONFIDENCE")
        Typography.apply(ctx_caption, "caption")
        ctx_caption.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        ctx.addWidget(ctx_caption)

        self._belief_value_label = QLabel("—")
        self._belief_value_label.setFont(Typography.font("display"))
        self._belief_value_label.setStyleSheet(
            f"color: {tokens.accent_primary}; background: transparent;"
        )
        ctx.addWidget(self._belief_value_label)

        ctx_subtitle = QLabel("How confident the model is in its current read")
        ctx_subtitle.setFont(Typography.font("body"))
        ctx_subtitle.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        ctx_subtitle.setWordWrap(True)
        ctx.addWidget(ctx_subtitle)

        ring_row.addSpacing(tokens.spacing_lg)
        ring_row.addLayout(ctx, 1)
        body.addLayout(ring_row)
        return card

    def _build_insights_card(self) -> Card:
        tokens = get_tokens()
        card = Card(title=i18n.get_text("recent_insights"), depth="raised")
        self._insights_container = card.content_layout
        self._insights_container.setSpacing(tokens.spacing_md)

        self._insights_empty = EmptyState(
            icon_text="◌",
            title="No insights yet",
            description=(
                "Once you analyze a few demos, coaching insights will land "
                "here automatically."
            ),
        )
        self._insights_container.addWidget(self._insights_empty)
        return card

    # ── Chat panel ──

    def _build_chat_panel(self) -> QFrame:
        tokens = get_tokens()
        panel = QFrame()
        panel.setObjectName("chat_panel")
        panel.setStyleSheet(
            f"QFrame#chat_panel {{ "
            f"background-color: {tokens.surface_sidebar}; "
            f"border-top: 1px solid {tokens.border_subtle}; "
            f"}}"
        )
        panel.setFixedHeight(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm
        )
        layout.setSpacing(tokens.spacing_sm)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(tokens.spacing_sm)

        chat_title = QLabel("CHAT")
        Typography.apply(chat_title, "caption")
        chat_title.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        header.addWidget(chat_title)

        self._inline_status_chip = StatusChip("Checking…", severity="neutral")
        header.addWidget(self._inline_status_chip)

        header.addStretch(1)

        clear_btn = make_button("Clear", variant="ghost", fixed_width=70)
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_chat)
        header.addWidget(clear_btn)

        collapse_btn = make_button("▼", variant="ghost", fixed_width=36)
        collapse_btn.setFixedHeight(28)
        collapse_btn.clicked.connect(self._toggle_chat)
        header.addWidget(collapse_btn)

        layout.addLayout(header)

        # Messages
        msg_scroll = QScrollArea()
        msg_scroll.setWidgetResizable(True)
        msg_scroll.setFrameShape(QFrame.NoFrame)
        msg_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        self._msg_container = QWidget()
        self._msg_container.setStyleSheet("background: transparent;")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(0, 0, 0, 0)
        self._msg_layout.setSpacing(tokens.spacing_sm)
        self._msg_layout.addStretch(1)
        msg_scroll.setWidget(self._msg_container)
        self._msg_scroll = msg_scroll
        layout.addWidget(msg_scroll, 1)

        # Typing indicator
        self._typing_label = QLabel(i18n.get_text("coach_thinking"))
        self._typing_label.setFont(Typography.font("caption"))
        self._typing_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        self._typing_label.setVisible(False)
        layout.addWidget(self._typing_label)

        # Quick action chips
        qa_row = QHBoxLayout()
        qa_row.setContentsMargins(0, 0, 0, 0)
        qa_row.setSpacing(tokens.spacing_sm)
        self._qa_buttons: list[tuple[QWidget, str]] = []
        for i18n_key, payload in _QUICK_ACTION_KEYS:
            btn = make_button(i18n.get_text(i18n_key), variant="secondary")
            btn.setFixedHeight(28)
            btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked, t=payload: self._send_quick(t))
            qa_row.addWidget(btn)
            self._qa_buttons.append((btn, i18n_key))
        qa_row.addStretch(1)
        layout.addLayout(qa_row)

        # Composer
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(tokens.spacing_sm)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText(i18n.get_text("ask_your_coach"))
        self._chat_input.setFixedHeight(36)
        self._chat_input.setStyleSheet(
            f"QLineEdit {{ "
            f"background: {tokens.surface_raised}; "
            f"color: {tokens.text_primary}; "
            f"border: 1px solid {tokens.border_default}; "
            f"border-radius: {tokens.radius_md}px; "
            f"padding: 0 {tokens.spacing_md}px; "
            f"font-size: {tokens.font_size_body}px; "
            f"}}"
            f"QLineEdit:focus {{ border: 1px solid {tokens.accent_primary}; }}"
        )
        self._chat_input.returnPressed.connect(self._send_message)
        input_row.addWidget(self._chat_input, 1)

        send_btn = make_button("Send", variant="primary", fixed_width=80)
        send_btn.setFixedHeight(36)
        send_btn.clicked.connect(self._send_message)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        return panel

    # ── Actions ──

    def _toggle_chat(self) -> None:
        self._chat_open = not self._chat_open
        self._chat_panel.setVisible(self._chat_open)
        self._chat_toggle_btn.setText("Hide chat" if self._chat_open else "Open chat")
        if self._chat_open:
            player = get_setting("CS2_PLAYER_NAME", "")
            if player:
                self._chat_vm.check_and_start(player)
            else:
                self._chat_vm.check_availability()
            self._chat_input.setFocus()

    def _send_message(self) -> None:
        text = self._chat_input.text().strip()
        if text:
            self._chat_vm.send_message(text)
            self._chat_input.clear()

    def _send_quick(self, text: str) -> None:
        self._chat_vm.send_message(text)

    def _clear_chat(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clear Chat",
            "Clear the current coaching session?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._chat_vm.clear_session()

    # ── Signal slots ──

    def _on_belief(self, confidence: float) -> None:
        # AppState emits 0..1 (or 0..100 historically). Normalize.
        normalized = float(confidence)
        if normalized > 1.0:
            normalized = normalized / 100.0
        self._belief_ring.set_value(max(0.0, min(1.0, normalized)))
        self._belief_value_label.setText(f"{normalized * 100:.0f}%")

    def _on_insights(self, insights: list) -> None:
        # Clear existing
        for w in self._insight_widgets:
            self._insights_container.removeWidget(w)
            w.deleteLater()
        self._insight_widgets.clear()

        if not insights:
            self._insights_empty.set_title("No insights yet")
            self._insights_empty.set_description(
                "Once you analyze a few demos, coaching insights will land "
                "here automatically."
            )
            self._insights_empty.setVisible(True)
            return

        self._insights_empty.setVisible(False)
        for insight in insights:
            card = self._build_insight_card(insight)
            self._insights_container.addWidget(card)
            self._insight_widgets.append(card)

    def _build_insight_card(self, insight: dict) -> QFrame:
        tokens = get_tokens()
        sev_color = _severity_color(insight.get("severity", ""), tokens)

        card = QFrame()
        card.setObjectName("insight_card")
        card.setStyleSheet(
            f"QFrame#insight_card {{ "
            f"background: {tokens.surface_raised}; "
            f"border: 1px solid {tokens.border_subtle}; "
            f"border-left: 3px solid {sev_color}; "
            f"border-radius: {tokens.radius_md}px; "
            f"}}"
        )

        body = QVBoxLayout(card)
        body.setContentsMargins(
            tokens.spacing_md, tokens.spacing_md, tokens.spacing_md, tokens.spacing_md
        )
        body.setSpacing(tokens.spacing_xs)

        # Optional pro context
        if insight.get("is_pro"):
            pro_name = insight.get("player_name", "Pro")
            map_tag = _map_from_demo(insight.get("demo_name", ""))
            ctx_text = f"PRO ANALYSIS · {pro_name.upper()}"
            if map_tag:
                ctx_text += f" ON {map_tag.upper()}"
            ctx = QLabel(ctx_text)
            Typography.apply(ctx, "caption")
            ctx.setStyleSheet(
                f"color: {tokens.accent_primary}; background: transparent;"
            )
            body.addWidget(ctx)

        # Title row + severity badge
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        title = QLabel(insight.get("title", "Insight"))
        title.setTextFormat(Qt.PlainText)  # FE-01 — block HTML rendering
        title.setFont(Typography.font("subtitle"))
        title.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        title_row.addWidget(title)
        title_row.addStretch(1)

        sev_chip = QLabel((insight.get("severity") or "info").upper())
        Typography.apply(sev_chip, "caption")
        sev_chip.setStyleSheet(
            f"color: {sev_color}; background: transparent;"
        )
        title_row.addWidget(sev_chip)
        body.addLayout(title_row)

        # Message
        msg = QLabel(insight.get("message", ""))
        msg.setTextFormat(Qt.PlainText)
        msg.setWordWrap(True)
        msg.setFont(Typography.font("body"))
        msg.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        body.addWidget(msg)

        # Meta row
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        focus = insight.get("focus_area")
        if focus:
            focus_lbl = QLabel(f"Focus  ·  {focus}")
            focus_lbl.setTextFormat(Qt.PlainText)
            focus_lbl.setFont(Typography.font("caption"))
            focus_lbl.setStyleSheet(
                f"color: {tokens.text_tertiary}; background: transparent;"
            )
            meta_row.addWidget(focus_lbl)
        meta_row.addStretch(1)
        date_str = insight.get("created_at") or ""
        if date_str:
            date_lbl = QLabel(str(date_str))
            date_lbl.setFont(Typography.font("mono"))
            date_lbl.setStyleSheet(
                f"color: {tokens.text_tertiary}; background: transparent; "
                f"font-size: {tokens.font_size_caption}px;"
            )
            meta_row.addWidget(date_lbl)
        body.addLayout(meta_row)

        return card

    def _render_messages(self, messages: list) -> None:
        # Clear existing bubbles (preserve trailing stretch at index 0; we
        # always insert via takeAt(1) so the stretch at top stays intact).
        # Actually our _msg_layout appends bubbles after the stretch, so
        # walk from the end.
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(self._msg_layout.count() - 1)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                # spacer / stretch — stop loop
                break

        # Re-add stretch (since we may have removed it)
        if self._msg_layout.count() == 0:
            self._msg_layout.addStretch(1)

        tokens = get_tokens()
        for msg in messages:
            role = msg.get("role", "assistant")
            is_user = role == "user"
            is_system = role == "system"

            bubble = QFrame()
            bubble.setObjectName("chat_bubble")
            if is_system:
                bg = tokens.toast_error_bg
                border = tokens.error
                text_color = tokens.error
            elif is_user:
                bg = tokens.accent_muted_25
                border = tokens.accent_primary
                text_color = tokens.text_primary
            else:
                bg = tokens.surface_raised
                border = tokens.border_subtle
                text_color = tokens.text_primary

            bubble.setStyleSheet(
                f"QFrame#chat_bubble {{ "
                f"background: {bg}; "
                f"border: 1px solid {border}; "
                f"border-radius: {tokens.radius_md}px; "
                f"padding: {tokens.spacing_sm}px {tokens.spacing_md}px; "
                f"}}"
            )
            bubble.setMaximumWidth(560)
            b_layout = QVBoxLayout(bubble)
            b_layout.setContentsMargins(
                tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm
            )

            content_text = msg.get("content", "")
            text_label = QLabel(content_text)
            text_label.setWordWrap(True)
            text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            text_label.setFont(Typography.font("body"))
            text_label.setStyleSheet(
                f"color: {text_color}; background: transparent;"
            )
            b_layout.addWidget(text_label)

            wrapper = QWidget()
            wrap_layout = QHBoxLayout(wrapper)
            wrap_layout.setContentsMargins(0, 0, 0, 0)
            if is_user:
                wrap_layout.addStretch(1)
                wrap_layout.addWidget(bubble)
            elif is_system:
                wrap_layout.addWidget(bubble, 1)
            else:
                wrap_layout.addWidget(bubble)
                wrap_layout.addStretch(1)

            self._msg_layout.addWidget(wrapper)

        self._scroll_chat_bottom()

    def _on_chat_loading(self, loading: bool) -> None:
        self._typing_label.setVisible(loading)
        if loading:
            self._scroll_chat_bottom()

    def _on_chat_availability(self, available: bool) -> None:
        if available:
            self._inline_status_chip.set_label("Online")
            self._inline_status_chip.set_severity("online")
            self._chat_status_chip.set_label("Coach: Online")
            self._chat_status_chip.set_severity("online")
        else:
            self._inline_status_chip.set_label("Offline")
            self._inline_status_chip.set_severity("offline")
            self._chat_status_chip.set_label("Coach: Offline")
            self._chat_status_chip.set_severity("offline")

    # ── Internals ──

    def _scroll_chat_bottom(self) -> None:
        QTimer.singleShot(
            50,
            lambda: self._msg_scroll.verticalScrollBar().setValue(
                self._msg_scroll.verticalScrollBar().maximum()
            ),
        )
