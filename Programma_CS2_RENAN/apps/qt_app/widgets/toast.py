"""Toast notification widgets — displays ephemeral status messages.

Frame-20 anatomy: severity-tinted card with a bold title row above the
message, and a tiny mono ``auto · Ns`` caption bottom-right BELOW the
card (omitted for CRITICAL, which never auto-dismisses). The styled
card is an inner frame so the caption can sit outside its border while
``ToastWidget`` stays one widget for the container's stacking logic.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
from Programma_CS2_RENAN.apps.qt_app.core.easing import Easing
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n

# Severity → (icon, auto-dismiss milliseconds; 0 = manual dismiss only)
_SEVERITY_CONFIG = {
    "INFO": ("\u2139", 5000),  # i
    "WARNING": ("\u26a0", 8000),  # warning triangle
    "ERROR": ("\u2716", 12000),  # X mark
    "CRITICAL": ("\u2620", 0),  # skull
}

# Severity title i18n keys (bold row per frames 20/33)
_SEVERITY_TITLE_KEY = {
    "INFO": ("toast.info", "Info"),
    "WARNING": ("toast.warning", "Warning"),
    "ERROR": ("toast.error", "Error"),
    "CRITICAL": ("toast.critical", "Critical"),
}

_MAX_VISIBLE = 3


class ToastWidget(QFrame):
    """A single toast notification bar with auto-dismiss."""

    dismissed = Signal()

    def __init__(self, severity: str, message: str, parent=None):
        super().__init__(parent)
        severity = severity.upper()
        icon_char, auto_ms = _SEVERITY_CONFIG.get(severity, ("\u2139", 8000))
        title_key, title_fallback = _SEVERITY_TITLE_KEY.get(severity, ("toast.info", "Info"))

        # Outer widget is transparent (no objectName): it stacks the
        # severity-styled card + the outside auto-dismiss caption.
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Severity-styled card (QSS QFrame#toast_<severity>)
        card = QFrame()
        card.setObjectName(f"toast_{severity.lower()}")
        card.setMinimumHeight(50)
        outer.addWidget(card)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(8)

        # Severity icon
        icon_label = QLabel(icon_char)
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Title (bold severity word) + message stacked
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)

        title_label = QLabel(i18n.get_text(title_key, title_fallback))
        title_label.setObjectName("toast_title")
        text_col.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setObjectName("toast_message")
        msg_label.setWordWrap(True)
        msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        text_col.addWidget(msg_label)
        layout.addLayout(text_col, 1)

        # Dismiss button
        dismiss = QPushButton("\u2715")  # multiplication X
        dismiss.setObjectName("toast_dismiss")
        dismiss.setFixedSize(24, 24)
        dismiss.setCursor(Qt.PointingHandCursor)
        dismiss.clicked.connect(self._remove)
        layout.addWidget(dismiss, alignment=Qt.AlignTop)

        # Auto-dismiss caption below the card, bottom-right, mono numeric
        # (frame 20). CRITICAL is manual-only → no caption.
        if auto_ms > 0:
            caption = QLabel(f"auto · {auto_ms // 1000}s")
            caption.setObjectName("toast_caption")
            outer.addWidget(caption, alignment=Qt.AlignRight)
            # F-0036: bind the timer to THIS widget as receiver context —
            # Qt then cancels the callback when the toast is destroyed
            # (container eviction), instead of firing on a corpse.
            QTimer.singleShot(auto_ms, self, self._remove)

    def _remove(self):
        Animator.fade_out(self, duration=200, hide_on_finish=True)
        QTimer.singleShot(220, self, self._cleanup)  # F-0036: receiver-bound

    def _cleanup(self):
        self.setParent(None)
        self.deleteLater()
        self.dismissed.emit()


class ToastContainer(QWidget):
    """Floating toast stack positioned at the top-right of its parent.

    This widget is NOT placed inside a layout manager.  It floats as a direct
    child, manually sized to tightly fit visible toasts and hidden when empty,
    so it never blocks mouse events on the underlying UI.
    """

    _CONTAINER_WIDTH = 520

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
        layout.setContentsMargins(0, 12, 12, 0)
        layout.setSpacing(6)

        self._toasts: list[ToastWidget] = []
        self.hide()  # Hidden until first toast — zero event interception

    def add_toast(self, severity: str, message: str):
        """Add a toast notification. Oldest removed if exceeding max visible."""
        while len(self._toasts) >= _MAX_VISIBLE:
            oldest = self._toasts.pop(0)
            oldest._remove()

        toast = ToastWidget(severity, message, self)
        toast.dismissed.connect(lambda t=toast: self._on_dismissed(t))
        self.layout().addWidget(toast)
        self._toasts.append(toast)
        self.refit()
        # Slide from the right edge with a subtle overshoot. Geometry
        # animation (not opacity effect) stays safe on mid-repaint — see
        # `core/animation.py` note on the Linux QPainter/opacity crash.
        Animator.slide_in(
            toast,
            direction="right",
            distance_px=64,
            duration=260,
            easing=Easing.OutBack,
        )

    def _on_dismissed(self, toast: ToastWidget):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self.refit()

    def refit(self):
        """Resize and reposition to tightly fit visible toasts (SA-24: public API)."""
        if not self._toasts:
            self.hide()
            return
        self.show()
        n = len(self._toasts)
        # 12px top margin + per-toast hint heights (card + caption vary
        # with severity/word-wrap) + 6px spacing between + 6px pad.
        h = 12 + sum(t.sizeHint().height() for t in self._toasts) + max(0, n - 1) * 6 + 6
        w = self._CONTAINER_WIDTH
        parent = self.parentWidget()
        if parent:
            self.setGeometry(max(0, parent.width() - w), 0, w, h)
        else:
            self.resize(w, h)
        self.raise_()
