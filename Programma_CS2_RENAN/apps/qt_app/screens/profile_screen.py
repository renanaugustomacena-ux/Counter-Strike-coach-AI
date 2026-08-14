"""Profile screen — In-Game Name editor per frame 17.

Left: description + mono name input + case-sensitivity caption + Save
with a transient "✓ Saved" success chip (persistence unchanged:
``save_user_setting("CS2_PLAYER_NAME", …)`` + PlayerProfile insert on
first save). Right: DbRecordCard mirroring the PlayerProfile row.
Below: Related navigation mini-cards, a "Stored locally" TipBox and the
mono data-source footer.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.db_record_card import DbRecordCard
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mini_link_card import MiniLinkCard
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mono_footer import MonoFooter
from Programma_CS2_RENAN.apps.qt_app.widgets.components.tip_box import TipBox
from Programma_CS2_RENAN.core.config import get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_profile")

# Related mini-cards (frame 17): key → (target screen, title i18n, caption i18n).
_RELATED_LINKS = {
    "steam": (
        "steam_config",
        ("quick_link_steam", "Steam Config"),
        ("related_steam_caption", "Link SteamID64 and Steam API key"),
    ),
    "faceit": (
        "faceit_config",
        ("quick_link_faceit", "FaceIt Config"),
        ("related_faceit_caption", "Connect FACEIT API token + ELO sync"),
    ),
    "history": (
        "match_history",
        ("match_history_title", "Match History"),
        ("related_history_caption", "See every match analyzed under this name"),
    ),
}


class ProfileScreen(QWidget):
    """In-Game Name editor with a live database-record card (frame 17)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self):
        self._name_input.setText(get_setting("CS2_PLAYER_NAME", ""))
        self._saved_chip.setVisible(False)
        self._refresh_record_card()

    def retranslate(self):
        """Update translatable text when language changes."""
        self._back_btn.setText(i18n.get_text("back_btn", "← Back"))
        self._title.setText(i18n.get_text("ingame_name_title", "In-Game Name"))
        self._desc.setText(
            i18n.get_text(
                "profile_desc",
                "Set your CS2 in-game name. This is used to identify your "
                "stats in demo files and match history.",
            )
        )
        self._case_caption.setText(
            i18n.get_text(
                "profile_case_caption",
                "Must match the name shown in demo files (case-sensitive).",
            )
        )
        self._save_btn.setText(i18n.get_text("save_btn", "Save"))
        self._saved_chip.setText(i18n.get_text("saved_chip", "✓ Saved"))
        self._record_card.set_title(i18n.get_text("db_record", "Database record"))
        self._record_card.set_subtitle(
            i18n.get_text("db_record_caption", "PlayerProfile row auto-created on save.")
        )
        self._related_card.set_title(i18n.get_text("related", "Related"))
        for key, card in self._related_cards.items():
            _target, title_spec, caption_spec = _RELATED_LINKS[key]
            card.set_title(i18n.get_text(*title_spec) + " →")
            card.set_caption(i18n.get_text(*caption_spec))
        self._tip_box.set_title(i18n.get_text("stored_locally", "Stored locally"))
        self._tip_box.set_body(
            i18n.get_text(
                "stored_locally_body",
                "CS2_PLAYER_NAME lives in user_settings.json (chmod 0o600). "
                "Nothing uploaded anywhere. FE-04.",
            )
        )
        self._refresh_record_card()

    # ── UI Construction ──

    def _build_ui(self):
        tokens = get_tokens()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Back button + title
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        self._back_btn = QPushButton(i18n.get_text("back_btn", "← Back"))
        self._back_btn.setProperty("variant", "secondary")
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.setFixedWidth(90)
        self._back_btn.clicked.connect(lambda: self._navigate("settings"))
        title_row.addWidget(self._back_btn)
        self._title = QLabel(i18n.get_text("ingame_name_title", "In-Game Name"))
        Typography.apply(self._title, "h1")
        title_row.addWidget(self._title, 1)
        layout.addLayout(title_row)

        # Content row: editor card (left) + database record card (right)
        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        editor_card = Card()
        self._desc = QLabel(
            i18n.get_text(
                "profile_desc",
                "Set your CS2 in-game name. This is used to identify your "
                "stats in demo files and match history.",
            )
        )
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        editor_card.layout().addWidget(self._desc)

        self._name_input = QLineEdit()
        self._name_input.setFont(Typography.font("mono"))
        self._name_input.setPlaceholderText(i18n.get_text("nickname_hint", "In-Game Nickname"))
        self._name_input.returnPressed.connect(self._save)
        editor_card.layout().addWidget(self._name_input)

        self._case_caption = QLabel(
            i18n.get_text(
                "profile_case_caption",
                "Must match the name shown in demo files (case-sensitive).",
            )
        )
        self._case_caption.setProperty("variant", "caption")
        editor_card.layout().addWidget(self._case_caption)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self._save_btn = QPushButton(i18n.get_text("save_btn", "Save"))
        self._save_btn.setProperty("variant", "primary")
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setFixedSize(120, 38)
        self._save_btn.clicked.connect(self._save)
        btn_row.addWidget(self._save_btn)

        self._saved_chip = QLabel(i18n.get_text("saved_chip", "✓ Saved"))
        self._saved_chip.setStyleSheet(
            f"color: {tokens.success}; border: 1px solid {tokens.success}; "
            f"border-radius: {tokens.radius_md}px; padding: 8px 16px; "
            f"background: transparent; font-weight: 700;"
        )
        self._saved_chip.setVisible(False)
        btn_row.addWidget(self._saved_chip)
        btn_row.addStretch()
        editor_card.layout().addLayout(btn_row)
        editor_card.layout().addStretch()
        content_row.addWidget(editor_card, 3)

        self._record_card = DbRecordCard(
            title=i18n.get_text("db_record", "Database record"),
            subtitle=i18n.get_text("db_record_caption", "PlayerProfile row auto-created on save."),
        )
        content_row.addWidget(self._record_card, 2)
        layout.addLayout(content_row)

        # Related navigation mini-cards
        self._related_card = Card(title=i18n.get_text("related", "Related"))
        related_row = QHBoxLayout()
        related_row.setSpacing(12)
        self._related_cards: dict[str, MiniLinkCard] = {}
        for key, (target, title_spec, caption_spec) in _RELATED_LINKS.items():
            card = MiniLinkCard(
                title=i18n.get_text(*title_spec) + " →",
                caption=i18n.get_text(*caption_spec),
            )
            card.clicked.connect(lambda t=target: self._navigate(t))
            self._related_cards[key] = card
            related_row.addWidget(card, 1)
        self._related_card.layout().addLayout(related_row)
        layout.addWidget(self._related_card)

        # Storage facts callout — key/file/permission verified in
        # core/config.py (save_user_setting → SETTINGS_PATH, FE-04 chmod).
        self._tip_box = TipBox(
            title=i18n.get_text("stored_locally", "Stored locally"),
            body=i18n.get_text(
                "stored_locally_body",
                "CS2_PLAYER_NAME lives in user_settings.json (chmod 0o600). "
                "Nothing uploaded anywhere. FE-04.",
            ),
        )
        layout.addWidget(self._tip_box)

        layout.addStretch()
        layout.addWidget(
            MonoFooter(
                'profile_screen.py · save_user_setting("CS2_PLAYER_NAME", ...) '
                "· PlayerProfile insert on first save"
            )
        )

    # ── Database record card ──

    def _refresh_record_card(self, row: dict | None = None):
        """Render the PlayerProfile row card.

        # FIELD-GAP: no profile ViewModel exists — screens must not open
        # new DB read paths (DB access belongs to VMs via Worker), so
        # outside of a save only ``player_name`` (from settings) is
        # real; id refreshes after the grandfathered save block runs.
        # created_at/matches_analyzed/last_match render "—" until a VM
        # provides them.
        """
        name = self._name_input.text().strip() or get_setting("CS2_PLAYER_NAME", "")
        row = row or {}
        self._record_card.set_sql(
            f'SELECT * FROM PlayerProfile\nWHERE player_name = "{name or "…"}"'
        )
        self._record_card.set_rows(
            [
                ("id", str(row.get("id", "—")), None),
                ("player_name", str(row.get("player_name", name or "—")), None),
                ("created_at", str(row.get("created_at", "—")), None),
                ("matches_analyzed", str(row.get("matches_analyzed", "—")), "success"),
                ("last_match", str(row.get("last_match", "—")), None),
            ]
        )

    # ── Actions ──

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
        profile_id = None
        try:
            from sqlmodel import select

            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import PlayerProfile

            with get_db_manager().get_session() as session:
                existing = session.exec(
                    select(PlayerProfile).where(PlayerProfile.player_name == name)
                ).first()
                if not existing:
                    existing = PlayerProfile(player_name=name)
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                    logger.info("Created PlayerProfile for '%s'", name)
                profile_id = existing.id
        except Exception:
            logger.exception("Failed to ensure PlayerProfile exists")

        row = {"player_name": name}
        if profile_id is not None:
            row["id"] = profile_id
        self._refresh_record_card(row)

        self._saved_chip.setVisible(True)
        QTimer.singleShot(2500, lambda: self._saved_chip.setVisible(False))
        logger.info("Player name saved: %s", name)
