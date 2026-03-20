"""Toast notification widgets — displays ephemeral status messages."""

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

# Severity → (icon, auto-dismiss milliseconds; 0 = manual dismiss only)
_SEVERITY_CONFIG = {
    "INFO": ("\u2139", 5000),  # i
    "WARNING": ("\u26A0", 8000),  # warning triangle
    "ERROR": ("\u2716", 12000),  # X mark
    "CRITICAL": ("\u2620", 0),  # skull
}

_MAX_VISIBLE = 3


class ToastWidget(QFrame):
    """A single toast notification bar with auto-dismiss."""

    dismissed = Signal()

    def __init__(self, severity: str, message: str, parent=None):
        super().__init__(parent)
        severity = severity.upper()
        icon_char, auto_ms = _SEVERITY_CONFIG.get(severity, ("\u2139", 8000))

        self.setObjectName(f"toast_{severity.lower()}")
        self.setFixedHeight(50)
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(8)

        # Severity icon
        icon_label = QLabel(icon_char)
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Message
        msg_label = QLabel(message)
        msg_label.setObjectName("toast_message")
        msg_label.setWordWrap(True)
        msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(msg_label, 1)

        # Dismiss button
        dismiss = QPushButton("\u2715")  # multiplication X
        dismiss.setObjectName("toast_dismiss")
        dismiss.setFixedSize(24, 24)
        dismiss.setCursor(Qt.PointingHandCursor)
        dismiss.clicked.connect(self._remove)
        layout.addWidget(dismiss)

        # Auto-dismiss timer
        if auto_ms > 0:
            QTimer.singleShot(auto_ms, self._remove)

    def _remove(self):
        self.setParent(None)
        self.deleteLater()
        self.dismissed.emit()


class ToastContainer(QWidget):
    """Manages a vertical stack of toast notifications (top-right overlay)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
        layout.setContentsMargins(0, 12, 12, 0)
        layout.setSpacing(6)

        self._toasts: list[ToastWidget] = []

    def add_toast(self, severity: str, message: str):
        """Add a toast notification. Oldest removed if exceeding max visible."""
        while len(self._toasts) >= _MAX_VISIBLE:
            oldest = self._toasts.pop(0)
            oldest._remove()

        toast = ToastWidget(severity, message, self)
        toast.dismissed.connect(lambda t=toast: self._on_dismissed(t))
        self.layout().addWidget(toast)
        self._toasts.append(toast)

    def _on_dismissed(self, toast: ToastWidget):
        if toast in self._toasts:
            self._toasts.remove(toast)
