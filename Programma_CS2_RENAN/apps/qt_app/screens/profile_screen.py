"""Profile screen — edit in-game name (CS2_PLAYER_NAME config key)."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from Programma_CS2_RENAN.core.config import get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_profile")


class ProfileScreen(QWidget):
    """Simple form for setting the in-game player name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def on_enter(self):
        self._name_input.setText(get_setting("CS2_PLAYER_NAME", ""))
        self._saved_label.setVisible(False)

    def retranslate(self):
        """Update translatable text when language changes."""
        pass  # Profile labels are English-only; wire i18n when translations added

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
        title = QLabel("In-Game Name")
        title.setObjectName("section_title")
        title.setFont(QFont("Roboto", 20, QFont.Bold))
        title_row.addWidget(title, 1)
        layout.addLayout(title_row)

        desc = QLabel(
            "Set your CS2 in-game name. This is used to identify your stats\n"
            "in demo files and match history."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        layout.addWidget(desc)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter your in-game nickname...")
        self._name_input.returnPressed.connect(self._save)
        layout.addWidget(self._name_input)

        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(120)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        self._saved_label = QLabel("Saved!")
        self._saved_label.setStyleSheet("color: #4caf50; font-size: 13px;")
        self._saved_label.setVisible(False)
        layout.addWidget(self._saved_label)

        layout.addStretch()

    def _navigate(self, screen_name: str):
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen(screen_name)

    def _save(self):
        name = self._name_input.text().strip()
        if not name:
            return
        save_user_setting("CS2_PLAYER_NAME", name)

        # Ensure a PlayerProfile row exists in DB for the coaching pipeline
        try:
            from sqlmodel import select

            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import PlayerProfile

            with get_db_manager().get_session() as session:
                existing = session.exec(
                    select(PlayerProfile).where(PlayerProfile.player_name == name)
                ).first()
                if not existing:
                    session.add(PlayerProfile(player_name=name))
                    session.commit()
                    logger.info("Created PlayerProfile for '%s'", name)
        except Exception:
            logger.exception("Failed to ensure PlayerProfile exists")

        self._saved_label.setVisible(True)
        logger.info("Player name saved: %s", name)
