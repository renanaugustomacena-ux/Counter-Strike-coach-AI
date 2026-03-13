"""Steam configuration screen — SteamID64 and API key setup."""

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.core.config import get_credential, get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_steam_config")


class SteamConfigScreen(QWidget):
    """Configure Steam integration: SteamID64 and API key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def on_enter(self):
        """Pre-fill fields from saved config."""
        self._steam_id_input.setText(get_setting("STEAM_ID", ""))
        api_key = get_credential("STEAM_API_KEY")
        if api_key and api_key != "PROTECTED_BY_WINDOWS_VAULT":
            self._api_key_input.setText(api_key)
        self._saved_label.setVisible(False)

    # ── UI ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Steam Profile Integration")
        title.setObjectName("section_title")
        title.setFont(QFont("Roboto", 20, QFont.Bold))
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # ── SteamID64 Card ──
        id_card = self._make_card("SteamID64")
        id_layout = id_card.layout()

        id_desc = QLabel(
            "Your 17-digit Steam ID is required to link your CS2 match history.\n"
            "You can find it on your Steam profile URL or use the link below."
        )
        id_desc.setWordWrap(True)
        id_desc.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        id_layout.addWidget(id_desc)

        id_link_btn = QPushButton("Find My Steam ID (steamid.io)")
        id_link_btn.setCursor(Qt.PointingHandCursor)
        id_link_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://steamid.io/"))
        )
        id_layout.addWidget(id_link_btn)

        self._steam_id_input = QLineEdit()
        self._steam_id_input.setPlaceholderText("17-digit SteamID64")
        self._steam_id_input.setMaxLength(20)
        id_layout.addWidget(self._steam_id_input)

        content_layout.addWidget(id_card)

        # ── Steam API Key Card ──
        key_card = self._make_card("Steam API Key")
        key_layout = key_card.layout()

        key_desc = QLabel(
            "A Steam Web API key enables advanced stats retrieval.\n"
            "Register one at the link below — use 'localhost' as the domain name."
        )
        key_desc.setWordWrap(True)
        key_desc.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        key_layout.addWidget(key_desc)

        key_link_btn = QPushButton("Get Steam API Key")
        key_link_btn.setCursor(Qt.PointingHandCursor)
        key_link_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://steamcommunity.com/dev/apikey")
            )
        )
        key_layout.addWidget(key_link_btn)

        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("Paste your Steam API Key")
        self._api_key_input.setEchoMode(QLineEdit.Password)
        key_layout.addWidget(self._api_key_input)

        content_layout.addWidget(key_card)

        # ── Save Button ──
        save_btn = QPushButton("Save Configuration")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._on_save)
        content_layout.addWidget(save_btn)

        self._saved_label = QLabel("Saved!")
        self._saved_label.setStyleSheet("color: #4caf50; font-size: 14px; font-weight: bold;")
        self._saved_label.setAlignment(Qt.AlignCenter)
        self._saved_label.setVisible(False)
        content_layout.addWidget(self._saved_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def _make_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("dashboard_card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        lbl = QLabel(title)
        lbl.setFont(QFont("Roboto", 14, QFont.Bold))
        lbl.setStyleSheet("color: #dcdcdc;")
        card_layout.addWidget(lbl)
        return card

    # ── Actions ──

    def _on_save(self):
        steam_id = self._steam_id_input.text().strip()
        api_key = self._api_key_input.text().strip()

        if steam_id:
            save_user_setting("STEAM_ID", steam_id)
        if api_key:
            save_user_setting("STEAM_API_KEY", api_key)

        self._saved_label.setVisible(True)
        QTimer.singleShot(3000, lambda: self._saved_label.setVisible(False))
        logger.info("Steam configuration saved (ID=%s)", "set" if steam_id else "empty")
