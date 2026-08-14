"""ChatPanel — frame-07 coaching chat surface (VM-agnostic).

Header (bold Chat + status dot + mono backend caption + Clear + collapse
chevron), scrollable bubble list (coach left / user right / system
centered), optional mono meta footnote inside a bubble ("confidence
0.82 · 4 demos referenced · RAP-Pedagogy"), suggestion-chip row, and an
input row (Return or Send submits).

The panel never talks to a ViewModel directly — a screen wires it:

    panel.message_submitted.connect(vm.send_message)
    vm.messages_changed.connect(lambda msgs: ...panel.add_message(...))
    vm.is_available_changed.connect(lambda ok: panel.set_status(ok, ...))
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button

_ROLES = ("coach", "user", "system")


class ChatPanel(QWidget):
    """Embeddable coaching chat panel per frame 07."""

    suggestion_clicked = Signal(str)
    message_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(get_tokens().spacing_sm)

        # ── Header row ──
        header = QHBoxLayout()
        header.setSpacing(get_tokens().spacing_sm)

        self._title = QLabel(i18n.get_text("chat.title", "Chat"))
        self._title.setObjectName("chat_title")
        header.addWidget(self._title)

        self._status_dot = QLabel("●")
        self._status_dot.setObjectName("chat_status_dot")
        header.addWidget(self._status_dot)

        self._status_text = QLabel(i18n.get_text("chat.offline", "Offline"))
        self._status_text.setObjectName("chat_status_text")
        header.addWidget(self._status_text)

        self._backend_label = QLabel("")
        self._backend_label.setObjectName("chat_backend")
        header.addWidget(self._backend_label)
        header.addStretch()

        self._clear_btn = make_button(i18n.get_text("chat.clear", "Clear"), variant="ghost")
        self._clear_btn.clicked.connect(self.clear)
        header.addWidget(self._clear_btn)

        self._collapse_btn = make_button("▾", variant="ghost")
        self._collapse_btn.setFixedSize(28, 28)
        self._collapse_btn.clicked.connect(self._toggle_collapsed)
        header.addWidget(self._collapse_btn)
        root.addLayout(header)

        # ── Collapsible body: bubbles + suggestions + input ──
        self._body = QWidget()
        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(get_tokens().spacing_sm)
        root.addWidget(self._body, 1)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMinimumHeight(220)
        self._scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._messages_host = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_host)
        self._messages_layout.setContentsMargins(0, 0, get_tokens().spacing_sm, 0)
        self._messages_layout.setSpacing(get_tokens().spacing_md)
        self._messages_layout.addStretch()
        self._scroll.setWidget(self._messages_host)
        body.addWidget(self._scroll, 1)

        self._suggestions_row = QWidget()
        self._suggestions_layout = QHBoxLayout(self._suggestions_row)
        self._suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self._suggestions_layout.setSpacing(get_tokens().spacing_sm)
        self._suggestions_row.setVisible(False)
        body.addWidget(self._suggestions_row)

        input_row = QHBoxLayout()
        input_row.setSpacing(get_tokens().spacing_sm)
        self._input = QLineEdit()
        self._input.setPlaceholderText(i18n.get_text("chat.placeholder", "Ask your coach…"))
        self._input.returnPressed.connect(self._submit)
        input_row.addWidget(self._input, 1)
        self._send_btn = make_button(i18n.get_text("chat.send", "Send"), variant="primary")
        self._send_btn.clicked.connect(self._submit)
        input_row.addWidget(self._send_btn)
        body.addLayout(input_row)

        self._bubbles: list[QFrame] = []
        self.set_status(False, "", "")

    # ── Public API ──

    def set_status(self, online: bool, backend: str, model: str) -> None:
        """Update the header status dot, Online/Offline text, and backend caption."""
        tokens = get_tokens()
        color = tokens.success if online else tokens.error
        self._status_dot.setStyleSheet(f"color: {color}; background: transparent;")
        key, fallback = ("chat.online", "Online") if online else ("chat.offline", "Offline")
        self._status_text.setText(i18n.get_text(key, fallback))
        self._backend_label.setText(f"{backend} · {model}" if backend or model else "")

    def add_message(self, role: str, text: str, meta: str | None = None) -> None:
        """Append a chat bubble. ``role`` ∈ {"coach", "user", "system"}."""
        if role not in _ROLES:
            role = "system"
        insert_at = self._messages_layout.count() - 1  # before the stretch

        if role == "system":
            label = QLabel(text)
            label.setObjectName("chat_system")
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            self._messages_layout.insertWidget(insert_at, label)
            self._scroll_to_bottom()
            return

        bubble = QFrame()
        bubble.setObjectName("chat_bubble")
        bubble.setProperty("role", role)
        bubble_layout = QVBoxLayout(bubble)
        pad_h, pad_v = get_tokens().spacing_md, get_tokens().spacing_sm
        bubble_layout.setContentsMargins(pad_h, pad_v, pad_h, pad_v)
        bubble_layout.setSpacing(2)

        text_label = QLabel(text)
        text_label.setObjectName("chat_bubble_text")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble_layout.addWidget(text_label)

        # Natural (unwrapped) width of the widest content line — the
        # bubble hugs it up to the 60% cap instead of the narrow width
        # word-wrapped QLabels prefer by default.
        natural = max(
            (text_label.fontMetrics().horizontalAdvance(line) for line in text.split("\n")),
            default=0,
        )

        if meta:
            meta_label = QLabel(meta)
            meta_label.setObjectName("chat_bubble_meta")
            meta_label.setWordWrap(True)
            bubble_layout.addWidget(meta_label)
            natural = max(natural, meta_label.fontMetrics().horizontalAdvance(meta))

        bubble.setProperty("natural_width", natural)
        bubble._text_label = text_label  # for width recompute on resize

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        if role == "user":
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:  # coach — left aligned
            row_layout.addWidget(bubble)
            row_layout.addStretch()

        self._bubbles.append(bubble)
        self._apply_bubble_width(bubble)
        self._messages_layout.insertWidget(insert_at, row)
        self._scroll_to_bottom()

    def set_suggestions(self, suggestions: list[str]) -> None:
        """Replace the suggestion-chip row (ghost buttons; click re-emits text)."""
        while self._suggestions_layout.count():
            item = self._suggestions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)  # detach now — deleteLater is deferred
                widget.deleteLater()
        for text in suggestions:
            chip = make_button(text, variant="ghost")
            chip.clicked.connect(lambda _=False, s=text: self.suggestion_clicked.emit(s))
            self._suggestions_layout.addWidget(chip)
        self._suggestions_layout.addStretch()
        self._suggestions_row.setVisible(bool(suggestions))

    def update_last_message(self, text: str) -> None:
        """Replace the last bubble's text in place (streaming updates).

        Reuses the same natural-width recompute path ``add_message`` uses so
        the bubble keeps hugging its widest line as chunks land. No-op when
        no bubbles exist yet.
        """
        if not self._bubbles:
            return
        bubble = self._bubbles[-1]
        bubble._text_label.setText(text)
        natural = max(
            (bubble._text_label.fontMetrics().horizontalAdvance(line) for line in text.split("\n")),
            default=0,
        )
        meta_label = bubble.findChild(QLabel, "chat_bubble_meta")
        if meta_label is not None:
            natural = max(natural, meta_label.fontMetrics().horizontalAdvance(meta_label.text()))
        bubble.setProperty("natural_width", natural)
        self._apply_bubble_width(bubble)
        self._scroll_to_bottom()

    def clear(self) -> None:
        """Remove every message bubble (suggestions and status stay)."""
        while self._messages_layout.count() > 1:  # keep the trailing stretch
            item = self._messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)  # detach now — deleteLater is deferred
                widget.deleteLater()
        self._bubbles.clear()

    # ── Internals ──

    def _submit(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.message_submitted.emit(text)

    def _toggle_collapsed(self) -> None:
        collapsed = self._body.isVisible()
        self._body.setVisible(not collapsed)
        self._collapse_btn.setText("▸" if collapsed else "▾")

    def _apply_bubble_width(self, bubble: QFrame) -> None:
        # Frame 07: bubbles hug their content, capped at ~60% panel width.
        panel_w = self.width() if self.width() > 160 else 800
        max_w = int(panel_w * 0.6)
        bubble.setMaximumWidth(max_w)
        natural = bubble.property("natural_width") or 0
        pad = 2 * get_tokens().spacing_md + 2  # bubble margins + border
        bubble._text_label.setMinimumWidth(min(int(natural), max_w - pad))

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def resizeEvent(self, event) -> None:  # noqa: N802 — Qt override
        super().resizeEvent(event)
        for bubble in self._bubbles:
            self._apply_bubble_width(bubble)
