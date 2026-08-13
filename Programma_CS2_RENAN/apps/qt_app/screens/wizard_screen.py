"""Setup Wizard — first-run 5-step flow: Name → Brain Path → Demo Path → Finish."""

import errno
import os
import shutil

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mono_footer import MonoFooter
from Programma_CS2_RENAN.apps.qt_app.widgets.components.stepper import Stepper
from Programma_CS2_RENAN.apps.qt_app.widgets.components.tip_box import TipBox
from Programma_CS2_RENAN.core.config import save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_wizard")

_BRAIN_SUBDIRS = ("knowledge", "models", "datasets")

# Frame-18 stepper captions: (i18n key, fallback) per step.
_STEP_LABELS = (
    ("wizard_step_intro", "Intro"),
    ("wizard_step_name", "Name"),
    ("wizard_step_brain", "Brain Path"),
    ("wizard_step_demo", "Demo Path"),
    ("wizard_step_launch", "Launch"),
)

# Directory-tree caption lines (frame 18) per created subdir.
_TREE_CAPTIONS = {
    "knowledge": "RAG embeddings · TacticalKnowledge entries · 384-dim vectors",
    "models": "checkpoint .pt files · JEPA + RAP · latest.pt + history",
    "datasets": "cached tensors · parsed demos · train/val/test splits",
}

# The only safely-skippable step: Demo Path is optional by design (name
# and brain path block Next until valid; intro/finish have no skip).
_SKIPPABLE_STEPS = frozenset({3})


def _step_labels() -> list[str]:
    return [i18n.get_text(key, fallback) for key, fallback in _STEP_LABELS]


class WizardScreen(QWidget):
    """5-step setup wizard: Intro → Player Name → Brain Path → Demo Path → Finish."""

    setup_completed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._brain_path = ""
        self._demo_path = ""
        self._player_name = ""

        self._build_ui()

    def on_enter(self):
        """Reset to first step when entering the wizard."""
        self._go_to(0)
        self._next_btn.setVisible(True)

    def retranslate(self):
        """Update translatable text when language changes."""
        self._brand.setText(i18n.get_text("app_name", "Macena CS2 Analyzer").upper())
        self._title.setText(i18n.get_text("wizard_title", "Setup Wizard"))
        self._back_btn.setText(i18n.get_text("wizard_back", "Back"))
        self._skip_btn.setText(i18n.get_text("wizard_skip_step", "Skip this step"))
        self._stepper.set_labels(_step_labels())
        # Brain-page copy
        self._brain_title.setText(
            i18n.get_text("wizard_brain_title", "Choose a folder for your AI brain data")
        )
        self._brain_desc.setText(
            i18n.get_text(
                "wizard_brain_desc",
                "This is where models, knowledge base, and datasets will be stored.",
            )
        )
        self._tree_header.setText(
            i18n.get_text("dir_tree_header", "DIRECTORY TREE (will be created)")
        )
        self._folder_path_label.setText(i18n.get_text("folder_path_label", "Folder path:"))
        self._val_writable_key.setText(i18n.get_text("val_writable", "Writable:"))
        self._val_free_key.setText(i18n.get_text("val_free_space", "Free space:"))
        self._val_est_key.setText(i18n.get_text("val_estimated", "Estimated use:"))
        self._val_est_value.setText(
            i18n.get_text("val_estimated_value", "~12 GB first year")
        )
        self._val_existing_key.setText(i18n.get_text("val_existing", "Existing data:"))
        self._brain_tip.set_title(i18n.get_text("wizard_tip_title", "Tip"))
        self._brain_tip.set_body(
            i18n.get_text(
                "wizard_tip_body",
                "Choose a drive with at least 50 GB free. The knowledge base + "
                "model checkpoints grow as you ingest more demos.",
            )
        )
        self._refresh_brain_validation()
        # Step caption + Next label depend on the current index
        step = self._stack.currentIndex()
        self._step_label.setText(
            i18n.get_text("wizard_step", "Step {n} of 5").replace("{n}", str(step + 1))
        )
        self._next_btn.setText(self._next_label_for(step))

    # ── UI Construction ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header — brand + h1 top-left, "Step n of 5" + labeled stepper
        # top-right (frame 18).
        header = QHBoxLayout()
        header.setSpacing(16)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self._brand = QLabel(i18n.get_text("app_name", "Macena CS2 Analyzer").upper())
        self._brand.setObjectName("wizard_brand")
        title_col.addWidget(self._brand)
        self._title = QLabel(i18n.get_text("wizard_title", "Setup Wizard"))
        Typography.apply(self._title, "h1")
        title_col.addWidget(self._title)
        header.addLayout(title_col)
        header.addStretch()

        step_col = QVBoxLayout()
        step_col.setSpacing(4)
        self._step_label = QLabel("Step 1 of 5")
        self._step_label.setAlignment(Qt.AlignRight)
        self._step_label.setStyleSheet(
            f"color: {get_tokens().text_secondary}; "
            f"font-size: {get_tokens().font_size_caption}px; background: transparent;"
        )
        step_col.addWidget(self._step_label)
        self._stepper = Stepper(step_count=5, current_step=0, labels=_step_labels())
        step_col.addWidget(self._stepper, alignment=Qt.AlignRight)
        header.addLayout(step_col)
        layout.addLayout(header)

        # 5-page stack
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { background: transparent; }")
        self._stack.addWidget(self._build_intro_page())  # 0
        self._stack.addWidget(self._build_name_page())  # 1
        self._stack.addWidget(self._build_brain_page())  # 2
        self._stack.addWidget(self._build_demo_page())  # 3
        self._stack.addWidget(self._build_finish_page())  # 4

        # P1 (UX visual audit): float the step content on a frosted panel so the
        # intro/finish copy stays legible over the desktop wallpaper instead of
        # rendering directly on the busy background. frost_bg is ~0.78 alpha and
        # theme-driven, so legibility stays consistent across CS2 / CSGO / CS16.
        content_panel = Card(depth="frosted")
        content_panel.content_layout.setContentsMargins(28, 28, 28, 28)
        content_panel.content_layout.addWidget(self._stack)
        layout.addWidget(content_panel, 1)

        # Bottom bar — Back / Skip this step (ghost, optional steps only)
        # ... Next → (frame 18).
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        self._back_btn = QPushButton(i18n.get_text("wizard_back", "Back"))
        self._back_btn.setProperty("variant", "secondary")
        self._back_btn.setFixedHeight(40)
        self._back_btn.setMinimumWidth(100)
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.clicked.connect(self._on_back)
        self._back_btn.setVisible(False)  # Hidden on intro page
        bottom.addWidget(self._back_btn)
        self._skip_btn = QPushButton(i18n.get_text("wizard_skip_step", "Skip this step"))
        self._skip_btn.setProperty("variant", "ghost")
        self._skip_btn.setFixedHeight(40)
        self._skip_btn.setCursor(Qt.PointingHandCursor)
        self._skip_btn.clicked.connect(self._on_skip)
        self._skip_btn.setVisible(False)
        bottom.addWidget(self._skip_btn)
        bottom.addStretch()
        self._next_btn = QPushButton(i18n.get_text("wizard_get_started", "Get Started"))
        self._next_btn.setProperty("variant", "primary")
        self._next_btn.setFixedHeight(40)
        self._next_btn.setMinimumWidth(140)
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_next)
        bottom.addWidget(self._next_btn)
        layout.addLayout(bottom)

        layout.addWidget(
            MonoFooter(
                "wizard_screen.py · QStackedWidget with 5 pages · shown on first run only"
            )
        )

    def _build_intro_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(16)

        welcome = QLabel("Welcome to Macena CS2 Analyzer")
        welcome.setFont(Typography.font("title"))
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setStyleSheet(f"color: {get_tokens().text_primary};")
        lay.addWidget(welcome)

        desc = QLabel(
            "This wizard will help you set up the essentials.\n\n"
            "You'll enter your in-game name, choose where to store\n"
            "AI models and knowledge base, and optionally point to\n"
            "your CS2 demo folder."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {get_tokens().text_secondary}; font-size: {get_tokens().font_size_subtitle}px;"
        )
        lay.addWidget(desc)

        return page

    def _build_name_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)

        desc = QLabel(
            "Enter your CS2 in-game name.\n"
            "This must match the name shown in demo files so the analyzer\n"
            "can identify your stats."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {get_tokens().text_secondary}; font-size: {get_tokens().font_size_body}px;"
        )
        lay.addWidget(desc)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Your in-game nickname (e.g. s1mple)")
        self._name_input.returnPressed.connect(self._on_next)
        lay.addWidget(self._name_input)

        self._name_error = QLabel("")
        self._name_error.setStyleSheet(
            f"color: {get_tokens().error}; font-size: {get_tokens().font_size_caption}px;"
        )
        self._name_error.setVisible(False)
        lay.addWidget(self._name_error)

        lay.addStretch()
        return page

    def _build_brain_page(self) -> QWidget:
        tokens = get_tokens()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)

        self._brain_title = QLabel(
            i18n.get_text("wizard_brain_title", "Choose a folder for your AI brain data")
        )
        self._brain_title.setFont(Typography.font("title"))
        self._brain_title.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        lay.addWidget(self._brain_title)

        self._brain_desc = QLabel(
            i18n.get_text(
                "wizard_brain_desc",
                "This is where models, knowledge base, and datasets will be stored.",
            )
        )
        self._brain_desc.setWordWrap(True)
        self._brain_desc.setStyleSheet(
            f"color: {tokens.text_secondary}; font-size: {tokens.font_size_body}px; "
            "background: transparent;"
        )
        lay.addWidget(self._brain_desc)

        # Directory tree preview — the subdirs _validate_brain really
        # creates (_BRAIN_SUBDIRS), with frame-18 caption lines.
        tree_card = QFrame()
        tree_card.setObjectName("dir_tree_card")
        tree_lay = QVBoxLayout(tree_card)
        tree_lay.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md
        )
        tree_lay.setSpacing(tokens.spacing_xs)
        self._tree_header = QLabel(
            i18n.get_text("dir_tree_header", "DIRECTORY TREE (will be created)")
        )
        self._tree_header.setObjectName("dir_tree_header")
        tree_lay.addWidget(self._tree_header)
        self._tree_root = QLabel("")
        self._tree_root.setObjectName("dir_tree_root")
        tree_lay.addWidget(self._tree_root)
        tree_body = QLabel(self._tree_body_html())
        tree_body.setObjectName("dir_tree_body")
        tree_body.setTextFormat(Qt.RichText)
        tree_lay.addWidget(tree_body)
        lay.addWidget(tree_card)

        self._folder_path_label = QLabel(i18n.get_text("folder_path_label", "Folder path:"))
        self._folder_path_label.setStyleSheet(
            f"color: {tokens.text_secondary}; font-size: {tokens.font_size_caption}px; "
            "background: transparent;"
        )
        lay.addWidget(self._folder_path_label)

        # Manual entry
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._brain_input = QLineEdit()
        self._brain_input.setFont(Typography.font("mono"))
        self._brain_input.setPlaceholderText("Enter path or use Select Folder...")
        self._brain_input.returnPressed.connect(self._on_next)
        self._brain_input.textChanged.connect(self._refresh_brain_validation)
        input_row.addWidget(self._brain_input, 1)
        browse_btn = QPushButton(i18n.get_text("wizard_select_folder", "Select Folder"))
        browse_btn.setProperty("variant", "secondary")
        browse_btn.clicked.connect(self._pick_brain_folder)
        input_row.addWidget(browse_btn)
        lay.addLayout(input_row)

        # Validation row — writable / free space / estimated use /
        # existing data (frame 18). Cheap inline os.access + disk_usage
        # against the nearest existing ancestor; recomputed per keystroke.
        val_row = QHBoxLayout()
        val_row.setSpacing(tokens.spacing_sm)

        def _pair(key_text: str) -> tuple[QLabel, QLabel]:
            key = QLabel(key_text)
            key.setStyleSheet(
                f"color: {tokens.text_secondary}; "
                f"font-size: {tokens.font_size_caption}px; background: transparent;"
            )
            value = QLabel("—")
            value.setFont(Typography.font("mono"))
            val_row.addWidget(key)
            val_row.addWidget(value)
            val_row.addSpacing(tokens.spacing_lg)
            return key, value

        self._val_writable_key, self._val_writable = _pair(
            i18n.get_text("val_writable", "Writable:")
        )
        self._val_free_key, self._val_free = _pair(
            i18n.get_text("val_free_space", "Free space:")
        )
        self._val_est_key, self._val_est_value = _pair(
            i18n.get_text("val_estimated", "Estimated use:")
        )
        self._val_est_value.setText(i18n.get_text("val_estimated_value", "~12 GB first year"))
        self._val_est_value.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        self._val_existing_key, self._val_existing = _pair(
            i18n.get_text("val_existing", "Existing data:")
        )
        val_row.addStretch()
        lay.addLayout(val_row)

        # Selected path display (fallback notices from _validate_brain)
        self._brain_path_label = QLabel("")
        self._brain_path_label.setStyleSheet(
            f"color: {tokens.text_primary}; font-size: {tokens.font_size_caption}px;"
        )
        self._brain_path_label.setWordWrap(True)
        lay.addWidget(self._brain_path_label)

        # Error display
        self._brain_error = QLabel("")
        self._brain_error.setStyleSheet(
            f"color: {tokens.error}; font-size: {tokens.font_size_caption}px;"
        )
        self._brain_error.setWordWrap(True)
        self._brain_error.setVisible(False)
        lay.addWidget(self._brain_error)

        self._brain_tip = TipBox(
            title=i18n.get_text("wizard_tip_title", "Tip"),
            body=i18n.get_text(
                "wizard_tip_body",
                "Choose a drive with at least 50 GB free. The knowledge base + "
                "model checkpoints grow as you ingest more demos.",
            ),
        )
        lay.addWidget(self._brain_tip)

        lay.addStretch()
        self._refresh_brain_validation()
        return page

    def _tree_body_html(self) -> str:
        """Static tree lines for the subdirs the wizard will create."""
        tokens = get_tokens()
        glyphs = ["├──"] * (len(_BRAIN_SUBDIRS) - 1) + ["└──"]
        pipes = ["│"] * (len(_BRAIN_SUBDIRS) - 1) + ["&nbsp;"]
        lines = []
        for sub, glyph, pipe in zip(_BRAIN_SUBDIRS, glyphs, pipes):
            lines.append(f"{glyph} <b>{sub}/</b>")
            lines.append(
                f'{pipe}&nbsp;&nbsp;&nbsp;<span style="color:{tokens.info};">'
                f"{_TREE_CAPTIONS[sub]}</span>"
            )
        return "<br>".join(lines)

    def _refresh_brain_validation(self):
        """Recompute the writable/free-space/existing-data row (frame 18)."""
        tokens = get_tokens()
        text = self._brain_input.text().strip()
        path = os.path.normpath(os.path.expanduser(text)) if text else ""
        self._tree_root.setText(f"{path or '…'}{os.sep}")

        if not path:
            for label in (self._val_writable, self._val_free, self._val_existing):
                label.setText("—")
                label.setStyleSheet(
                    f"color: {tokens.text_tertiary}; background: transparent;"
                )
            return

        # Nearest existing ancestor — the path itself usually doesn't
        # exist yet ("will be created").
        probe = path
        while probe and not os.path.exists(probe):
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent

        writable = os.path.exists(probe) and os.access(probe, os.W_OK)
        if writable:
            self._val_writable.setText(i18n.get_text("val_yes", "✓ yes"))
            self._val_writable.setStyleSheet(
                f"color: {tokens.success}; background: transparent;"
            )
        else:
            self._val_writable.setText(i18n.get_text("val_no", "✗ no"))
            self._val_writable.setStyleSheet(
                f"color: {tokens.error}; background: transparent;"
            )

        try:
            free_gb = shutil.disk_usage(probe).free // (1024**3)
            self._val_free.setText(f"{free_gb} GB")
            self._val_free.setStyleSheet(
                f"color: {tokens.success}; background: transparent;"
            )
        except OSError:
            self._val_free.setText("—")
            self._val_free.setStyleSheet(
                f"color: {tokens.text_tertiary}; background: transparent;"
            )

        try:
            has_data = os.path.isdir(path) and bool(os.listdir(path))
        except OSError:
            has_data = False
        if has_data:
            self._val_existing.setText(i18n.get_text("val_existing_found", "found"))
            self._val_existing.setStyleSheet(
                f"color: {tokens.warning}; background: transparent;"
            )
        else:
            self._val_existing.setText(i18n.get_text("val_existing_none", "none"))
            self._val_existing.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent;"
            )

    def _build_demo_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)

        desc = QLabel(
            "Select your CS2 demo folder (optional).\n"
            "This is where your .dem replay files are located.\n"
            "You can skip this step and set it later in Settings."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {get_tokens().text_secondary}; font-size: {get_tokens().font_size_body}px;"
        )
        lay.addWidget(desc)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._demo_input = QLineEdit()
        self._demo_input.setPlaceholderText("Enter path or use Select Folder...")
        self._demo_input.returnPressed.connect(self._on_next)
        input_row.addWidget(self._demo_input, 1)
        browse_btn = QPushButton("Select Folder")
        browse_btn.clicked.connect(self._pick_demo_folder)
        input_row.addWidget(browse_btn)
        lay.addLayout(input_row)

        self._demo_path_label = QLabel("")
        self._demo_path_label.setStyleSheet(
            f"color: {get_tokens().text_primary}; font-size: {get_tokens().font_size_caption}px;"
        )
        self._demo_path_label.setWordWrap(True)
        lay.addWidget(self._demo_path_label)

        self._demo_error = QLabel("")
        self._demo_error.setStyleSheet(
            f"color: {get_tokens().error}; font-size: {get_tokens().font_size_caption}px;"
        )
        self._demo_error.setWordWrap(True)
        self._demo_error.setVisible(False)
        lay.addWidget(self._demo_error)

        lay.addStretch()
        return page

    def _build_finish_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(16)

        done = QLabel("You're all set!")
        done.setFont(Typography.font("title"))
        done.setAlignment(Qt.AlignCenter)
        done.setStyleSheet(f"color: {get_tokens().text_primary};")
        lay.addWidget(done)

        info = QLabel(
            "Your player name, brain data, and demo paths have been configured.\n"
            "You can change these anytime in Settings or Profile."
        )
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        info.setStyleSheet(
            f"color: {get_tokens().text_secondary}; font-size: {get_tokens().font_size_subtitle}px;"
        )
        lay.addWidget(info)

        return page

    # ── Navigation ──

    def _on_next(self):
        step = self._stack.currentIndex()
        if step == 0:
            self._go_to(1)
        elif step == 1:
            if self._validate_name():
                self._go_to(2)
        elif step == 2:
            if self._validate_brain():
                self._go_to(3)
        elif step == 3:
            self._validate_demo()
            self._go_to(4)
        elif step == 4:
            self._finish()

    def _on_back(self):
        step = self._stack.currentIndex()
        if step > 0:
            self._go_to(step - 1)

    def _on_skip(self):
        """Skip an optional step without validating or persisting it."""
        step = self._stack.currentIndex()
        if step in _SKIPPABLE_STEPS:
            self._go_to(step + 1)

    def _next_label_for(self, index: int) -> str:
        if index == 0:
            return i18n.get_text("wizard_get_started", "Get Started")
        if index == 4:
            return i18n.get_text("wizard_launch", "Launch App")
        return i18n.get_text("wizard_next", "Next") + " →"

    def _go_to(self, index: int):
        self._stack.setCurrentIndex(index)
        # Update button visibility and labels
        self._back_btn.setVisible(index > 0)
        self._skip_btn.setVisible(index in _SKIPPABLE_STEPS)
        self._stepper.current_step = index
        self._step_label.setText(
            i18n.get_text("wizard_step", "Step {n} of 5").replace("{n}", str(index + 1))
        )
        self._next_btn.setText(self._next_label_for(index))

    # ── Folder Pickers ──

    def _pick_brain_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Brain Data Folder", os.path.expanduser("~")
        )
        if path:
            self._brain_input.setText(path)
            self._brain_path = path
            self._brain_path_label.setText(f"Selected: {path}")

    def _pick_demo_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Demo Folder", os.path.expanduser("~"))
        if path:
            self._demo_input.setText(path)
            self._demo_path = path
            self._demo_path_label.setText(f"Selected: {path}")

    # ── Validation ──

    def _validate_name(self) -> bool:
        """Validate and save the player name. Returns True on success."""
        self._name_error.setVisible(False)
        name = self._name_input.text().strip()
        if not name:
            self._name_error.setText("Please enter your CS2 in-game name.")
            self._name_error.setVisible(True)
            return False
        self._player_name = name
        save_user_setting("CS2_PLAYER_NAME", name)
        logger.info("Player name set to %s", name)
        return True

    def _validate_brain(self) -> bool:
        """Validate brain path, create subdirectories. Returns True on success."""
        self._brain_error.setVisible(False)
        text = self._brain_input.text().strip()
        if not text:
            self._brain_error.setText("Please select or enter a brain data path.")
            self._brain_error.setVisible(True)
            return False

        # WZ-01: normalize
        path = os.path.normpath(os.path.expanduser(text))

        try:
            os.makedirs(path, exist_ok=True)
            for sub in _BRAIN_SUBDIRS:
                os.makedirs(os.path.join(path, sub), exist_ok=True)
        except OSError as e:
            if e.errno in (errno.EACCES, errno.EPERM):
                # WZ-04: try fallback paths
                fallback = self._find_writable_fallback()
                if fallback:
                    path = fallback
                    try:
                        os.makedirs(path, exist_ok=True)
                        for sub in _BRAIN_SUBDIRS:
                            os.makedirs(os.path.join(path, sub), exist_ok=True)
                    except OSError as e2:
                        self._brain_error.setText(f"Cannot create directories: {e2}")
                        self._brain_error.setVisible(True)
                        return False
                    self._brain_path_label.setText(f"Using fallback: {path}")
                else:
                    self._brain_error.setText(f"Permission denied and no fallback available: {e}")
                    self._brain_error.setVisible(True)
                    return False
            else:
                self._brain_error.setText(f"Cannot create directory: {e}")
                self._brain_error.setVisible(True)
                return False

        self._brain_path = path
        save_user_setting("BRAIN_DATA_ROOT", path)
        logger.info("Brain data root set to %s", path)
        return True

    def _validate_demo(self):
        """Validate demo path (optional). Non-blocking on error."""
        self._demo_error.setVisible(False)
        text = self._demo_input.text().strip()
        if not text:
            return  # Optional — skip

        # WZ-01: normalize
        path = os.path.normpath(os.path.expanduser(text))

        # WZ-03: non-blocking directory creation
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            logger.warning("Could not create demo path %s: %s", path, e)
            self._demo_error.setText(f"Warning: could not create folder ({e}). Path saved anyway.")
            self._demo_error.setVisible(True)

        self._demo_path = path
        save_user_setting("DEFAULT_DEMO_PATH", path)
        logger.info("Demo path set to %s", path)

    def _find_writable_fallback(self) -> str:
        """WZ-04: find a writable fallback path for brain data."""
        home = os.path.expanduser("~")
        for candidate in (
            os.path.join(home, "Documents", "DataCoach"),
            os.path.join(home, "DataCoach"),
        ):
            parent = os.path.dirname(candidate)
            if os.path.isdir(parent) and os.access(parent, os.W_OK):
                return candidate
        return ""

    # ── Finish ──

    def _finish(self):
        # Create PlayerProfile in DB so coaching pipeline can find it
        if self._player_name:
            try:
                from sqlmodel import select

                from Programma_CS2_RENAN.backend.storage.database import get_db_manager
                from Programma_CS2_RENAN.backend.storage.db_models import PlayerProfile

                with get_db_manager().get_session() as session:
                    existing = session.exec(
                        select(PlayerProfile).where(PlayerProfile.player_name == self._player_name)
                    ).first()
                    if not existing:
                        session.add(PlayerProfile(player_name=self._player_name))
                        session.commit()
                        logger.info("Created PlayerProfile for '%s'", self._player_name)
            except Exception:
                logger.exception("Failed to create PlayerProfile during wizard finish")

        save_user_setting("SETUP_COMPLETED", True)
        logger.info("Setup wizard completed")
        self.setup_completed.emit()
