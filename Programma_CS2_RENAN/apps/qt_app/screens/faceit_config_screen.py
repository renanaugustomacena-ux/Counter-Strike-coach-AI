"""FaceIT configuration screen — API key setup."""

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.core.config import get_credential, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_faceit_config")

try:
    import keyring  # noqa: F401

    _KEYRING_AVAILABLE = keyring is not None
except ImportError:
    _KEYRING_AVAILABLE = False


class FaceitConfigScreen(QWidget):
    """Configure FaceIT integration: API key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def on_enter(self):
        """Pre-fill field from saved config."""
        api_key = get_credential("FACEIT_API_KEY")
        if api_key and api_key != "PROTECTED_BY_WINDOWS_VAULT":
            self._api_key_input.setText(api_key)
        self._saved_label.setVisible(False)

    def retranslate(self):
        """Update translatable text when language changes."""
        pass  # All labels are English-only for now; wire i18n when translations added

    # ── UI ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Back button + title
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        back_btn = QPushButton("\u2190 Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(lambda: self._navigate("home"))
        title_row.addWidget(back_btn)
        title = QLabel("FaceIT Competitive Stats")
        Typography.apply(title, "h1")
        title_row.addWidget(title, 1)
        layout.addLayout(title_row)

        # ── Keyring Warning ──
        if not _KEYRING_AVAILABLE:
            warn = QLabel(
                "System keyring unavailable — API keys will be stored in plaintext on disk. "
                "Install the 'keyring' package for secure storage."
            )
            warn.setWordWrap(True)
            warn.setStyleSheet(
                "color: #ffcc00; background-color: #332b00; "
                "border: 1px solid #665500; border-radius: 4px; "
                "padding: 8px; font-size: 13px;"
            )
            layout.addWidget(warn)

        # ── API Key Card ──
        card = QFrame()
        card.setObjectName("dashboard_card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        card_title = QLabel("FaceIT API Key")
        card_title.setFont(QFont("Roboto", 14, QFont.Bold))
        card_title.setStyleSheet(f"color: {get_tokens().text_primary};")
        card_layout.addWidget(card_title)

        desc = QLabel(
            "Connect your FaceIT account to compare your performance\n"
            "against competitive rankings and track your ELO progression."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {get_tokens().text_secondary}; font-size: 13px;")
        card_layout.addWidget(desc)

        link_btn = QPushButton("Get FaceIT API Key")
        link_btn.setCursor(Qt.PointingHandCursor)
        link_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://developers.faceit.com/"))
        )
        card_layout.addWidget(link_btn)

        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("FaceIT API Client Key")
        self._api_key_input.setEchoMode(QLineEdit.Password)
        card_layout.addWidget(self._api_key_input)

        layout.addWidget(card)

        # ── Save Button ──
        save_btn = QPushButton("Save FaceIT Config")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        self._saved_label = QLabel("Saved!")
        self._saved_label.setStyleSheet(f"color: {get_tokens().success}; font-size: 14px; font-weight: bold;")
        self._saved_label.setAlignment(Qt.AlignCenter)
        self._saved_label.setVisible(False)
        layout.addWidget(self._saved_label)

        layout.addStretch()

    def _navigate(self, screen_name: str):
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen(screen_name)

    # ── Actions ──

    def _on_save(self):
        api_key = self._api_key_input.text().strip()
        if api_key:
            save_user_setting("FACEIT_API_KEY", api_key)

        self._saved_label.setVisible(True)
        QTimer.singleShot(3000, lambda: self._saved_label.setVisible(False))
        logger.info("FaceIT configuration saved")
