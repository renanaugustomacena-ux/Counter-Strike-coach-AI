"""Help screen — frame 19: topic rail + structured article panel.

Left: ``TOPICS · {n}`` rows (bold title + caption, selected accent
left-bar) + ``EXTERNAL`` web links. Right: article panel — topic h1;
the Getting Started topic renders the structured frame-19 article
(numbered steps, DEMO FOLDER callout), other topics render their doc
content; below: RELATED topic mini-cards, KEYBOARD HINTS rows and the
``Docs source`` TipBox. Search (top-right) filters topics.

Topics come from ``help_system`` (``Programma_CS2_RENAN/data/docs/*.md``)
with a built-in fallback set when the knowledge base is unavailable.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mini_link_card import MiniLinkCard
from Programma_CS2_RENAN.apps.qt_app.widgets.components.numbered_step import NumberedStep
from Programma_CS2_RENAN.apps.qt_app.widgets.components.tip_box import TipBox
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_help")

# Help system loads real docs from Programma_CS2_RENAN/data/docs/*.md
try:
    from Programma_CS2_RENAN.backend.knowledge_base.help_system import get_help_system

    _HELP_AVAILABLE = True
except ImportError:
    _HELP_AVAILABLE = False

_FALLBACK_TOPICS = [
    {
        "id": "getting_started",
        "title": "Getting Started",
        "content": (
            "Welcome to Macena CS2 Analyzer!\n\n"
            "1. Go to Settings and set your in-game name in Profile\n"
            "2. Set your demo folder path (where CS2 saves .dem files)\n"
            "3. The app will automatically detect and analyze your matches\n"
            "4. View your match history, performance stats, and AI coaching\n\n"
            "Your CS2 demo folder is typically located at:\n"
            "  Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/replays/"
        ),
    },
    {
        "id": "demo_analysis",
        "title": "Demo Analysis",
        "content": (
            "How Demo Analysis Works\n\n"
            "1. Place your .dem files in the configured demo folder\n"
            "2. The analyzer detects new files and queues them for processing\n"
            "3. Each demo is parsed tick-by-tick to extract player actions\n"
            "4. Features are computed: positioning, utility usage, economy, etc.\n"
            "5. Results appear in Match History and Performance screens\n\n"
            "Pro demos can also be ingested to build a reference baseline\n"
            "that the AI coach uses to compare your play against pro patterns."
        ),
    },
    {
        "id": "ai_coach",
        "title": "AI Coach",
        "content": (
            "The AI Coach Screen\n\n"
            "The coach provides personalized insights based on your analyzed demos.\n\n"
            "Features:\n"
            "- Belief State: shows model confidence based on data volume\n"
            "- Recent Insights: actionable coaching advice ranked by severity\n"
            "- Chat: interactive conversation with the AI coach (requires Ollama)\n\n"
            "To enable chat:\n"
            "1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh\n"
            "2. Pull the model: ollama pull gemma4:e2b\n"
            "3. Start Ollama: ollama serve\n"
            "4. Open the Chat panel in the Coach screen"
        ),
    },
    {
        "id": "steam_setup",
        "title": "Steam Integration",
        "content": (
            "Connecting Your Steam Account\n\n"
            "Navigate to the Steam Config screen from the Dashboard.\n\n"
            "SteamID64:\n"
            "- Your unique 17-digit Steam identifier\n"
            "- Find it at steamid.io by entering your Steam profile URL\n\n"
            "Steam API Key:\n"
            "- Required for advanced stats retrieval\n"
            "- Register at steamcommunity.com/dev/apikey\n"
            "- Use 'localhost' as the domain name when registering"
        ),
    },
    {
        "id": "keyboard_shortcuts",
        "title": "Navigation",
        "content": (
            "App Navigation\n\n"
            "Use the sidebar on the left to switch between screens:\n\n"
            "- Home: Dashboard overview and quick actions\n"
            "- Coach: AI coaching insights and chat\n"
            "- Match History: Browse analyzed demos\n"
            "- Performance: Advanced analytics and stats\n"
            "- Tactical Viewer: 2D demo replay viewer\n"
            "- Settings: Theme, fonts, paths, language\n"
            "- Help: This screen"
        ),
    },
    {
        "id": "troubleshooting",
        "title": "Troubleshooting",
        "content": (
            "Common Issues\n\n"
            "No matches showing:\n"
            "- Verify your demo folder path in Settings\n"
            "- Ensure .dem files are present in the folder\n"
            "- Check that ingestion has run (Dashboard status)\n\n"
            "Coach chat offline:\n"
            "- Ollama must be installed and running\n"
            "- Run 'ollama serve' in a terminal\n"
            "- Ensure the gemma4:e2b model is downloaded\n\n"
            "Fonts not changing:\n"
            "- Some custom fonts require the font files in PHOTO_GUI/\n"
            "- Restart the app after changing fonts"
        ),
    },
]

# Left-rail captions per known topic id (frame 19) — i18n key, fallback.
_TOPIC_CAPTIONS = {
    "getting_started": ("topic_caption_getting_started", "First-run setup · essentials"),
    "demo_analysis": ("topic_caption_demo_analysis", "How .dem files are processed"),
    "ai_coach": ("topic_caption_ai_coach", "Belief state · insights · chat"),
    "steam_setup": ("topic_caption_steam_setup", "SteamID64 · API key setup"),
    "keyboard_shortcuts": ("topic_caption_keyboard_shortcuts", "Sidebar · screen guide"),
    "troubleshooting": ("topic_caption_troubleshooting", "No matches · chat offline · fonts"),
    "features": ("topic_caption_features", "Feature tour · what each screen does"),
}

# External link rows (frame 19): (i18n key, fallback label, url). GitHub =
# the real origin remote; the other URLs are the ones the help content
# itself references.
_EXTERNAL_LINKS = (
    (
        "help.ext_github",
        "GitHub repo",
        "https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI",
    ),
    ("help.ext_ollama", "Ollama install docs", "https://ollama.com/download"),
    ("help.ext_steamid", "SteamID lookup", "https://steamid.io"),
    ("help.ext_steamkey", "Steam API key", "https://steamcommunity.com/dev/apikey"),
)

# Frame-19 Getting Started article — 5 steps: (i18n key stem, title, desc).
_GETTING_STARTED_STEPS = (
    (
        "help_step1",
        "Set your in-game name",
        "Go to Settings → Quick Links → In-Game Name",
    ),
    (
        "help_step2",
        "Point to your demo folder",
        "Home → Demo Analysis → Select Demo Folder",
    ),
    (
        "help_step3",
        "Let the analyzer ingest your .dem files",
        'Click "Analyze Demos" — or leave the Scanner daemon running',
    ),
    (
        "help_step4",
        "Explore Match History and Performance",
        "Your stats, per-map breakdown, strengths & weaknesses",
    ),
    (
        "help_step5",
        "Chat with the AI Coach",
        "Requires Ollama + gemma4:e2b model — see AI Coach section",
    ),
)

# Keyboard hint rows (frame 19) — both verified against the codebase
# (nav sidebar 220→60 collapse; chat input returnPressed; back buttons).
_KEYBOARD_HINTS = (
    (
        "hint_collapse",
        "Click hamburger ≡ (top of sidebar) to collapse the nav sidebar 220 → 60 px",
    ),
    (
        "hint_keys",
        "Return in chat input sends the message · Esc closes dialogs · "
        "Back button on drill-down screens returns",
    ),
)


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)


class _TopicRow(QFrame):
    """Left-rail topic row — bold title + caption, accent bar when selected."""

    clicked = Signal(str)

    def __init__(self, topic_id: str, title: str, caption: str, parent=None):
        super().__init__(parent)
        self.setObjectName("help_topic_row")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.topic_id = topic_id
        tokens = get_tokens()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(
            tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm
        )
        lay.setSpacing(2)
        self._title_label = QLabel(title)
        self._title_label.setObjectName("help_topic_title")
        lay.addWidget(self._title_label)
        if caption:
            caption_label = QLabel(caption)
            caption_label.setObjectName("help_topic_caption")
            caption_label.setWordWrap(True)
            lay.addWidget(caption_label)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        _repolish(self)
        _repolish(self._title_label)

    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.topic_id)
        super().mousePressEvent(event)


class HelpScreen(QWidget):
    """Two-panel help browser: topic rail + structured article (frame 19)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._topics = []
        self._topic_rows: list[_TopicRow] = []
        self._selected_id: str | None = None
        self._build_ui()

    def on_enter(self):
        """Load topics when screen becomes visible."""
        self._load_topics()

    def retranslate(self):
        """Update all translatable text when language changes."""
        self._title_label.setText(i18n.get_text("help_center"))
        self._search_input.setPlaceholderText(i18n.get_text("search_placeholder"))
        self._related_header.setText(i18n.get_text("related_header", "RELATED"))
        self._hints_header.setText(i18n.get_text("keyboard_hints_header", "KEYBOARD HINTS"))
        for label, (key, fallback) in zip(self._hint_labels, _KEYBOARD_HINTS):
            label.setText(i18n.get_text(key, fallback))
        self._external_header.setText(i18n.get_text("external_header", "EXTERNAL"))
        for link, (key, fallback, url) in zip(self._external_links, _EXTERNAL_LINKS):
            link.setText(self._external_link_html(key, fallback, url))
        self._docs_tip.set_title(i18n.get_text("docs_source_title", "Docs source"))
        self._docs_tip.set_body(
            i18n.get_text(
                "docs_source_body",
                "Programma_CS2_RENAN/data/docs/*.md · loaded via help_system.py",
            )
        )
        self._welcome_label.setText(
            i18n.get_text("help_welcome", "Welcome to Macena CS2 Analyzer!")
        )
        for step, (stem, title, desc) in zip(self._step_rows, _GETTING_STARTED_STEPS):
            step.set_title(i18n.get_text(f"{stem}_title", title))
            step.set_description(i18n.get_text(f"{stem}_desc", desc))
        # Rebuild the rail (captions + TOPICS · n) and re-render the article
        self._populate_list(self._visible_topics())

    # ── UI ──

    @staticmethod
    def _external_link_html(key: str, fallback: str, url: str) -> str:
        """Anchor markup for an EXTERNAL rail row, label resolved via i18n."""
        tokens = get_tokens()
        return (
            f'<a style="color: {tokens.info}; text-decoration: none;" '
            f'href="{url}">↗ {i18n.get_text(key, fallback)}</a>'
        )

    def _build_ui(self):
        tokens = get_tokens()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header: title left, search right (frame 19)
        header = QHBoxLayout()
        header.setSpacing(12)
        self._title_label = QLabel(i18n.get_text("help_center"))
        # QLabel#section_title QSS rule provides the token-driven font
        # and text_inverse color — no per-widget literals needed.
        self._title_label.setObjectName("section_title")
        header.addWidget(self._title_label)
        header.addStretch()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(i18n.get_text("search_placeholder"))
        self._search_input.textChanged.connect(self._on_search)
        self._search_input.setFixedWidth(320)
        header.addWidget(self._search_input)
        layout.addLayout(header)

        # Two-panel layout
        panels = QHBoxLayout()
        panels.setSpacing(12)

        # ── Left Panel: TOPICS rail + EXTERNAL links ──
        left = QFrame()
        left.setObjectName("dashboard_card")
        left.setFixedWidth(300)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(
            tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg
        )
        left_layout.setSpacing(8)

        self._topics_header = QLabel(i18n.get_text("topics_header", "TOPICS"))
        self._topics_header.setObjectName("help_panel_header")
        left_layout.addWidget(self._topics_header)

        self._topics_col = QVBoxLayout()
        self._topics_col.setSpacing(4)
        left_layout.addLayout(self._topics_col)
        left_layout.addStretch()

        self._external_header = QLabel(i18n.get_text("external_header", "EXTERNAL"))
        self._external_header.setObjectName("help_panel_header")
        left_layout.addWidget(self._external_header)
        self._external_links: list[QLabel] = []
        for key, fallback, url in _EXTERNAL_LINKS:
            link = QLabel(self._external_link_html(key, fallback, url))
            link.setTextFormat(Qt.RichText)
            link.setOpenExternalLinks(True)
            link.setStyleSheet(f"font-size: {tokens.font_size_caption}px; background: transparent;")
            self._external_links.append(link)
            left_layout.addWidget(link)

        panels.addWidget(left)

        # ── Right Panel: structured article ──
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        article = QWidget()
        article_layout = QVBoxLayout(article)
        article_layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_sm, tokens.spacing_lg, tokens.spacing_sm
        )
        article_layout.setSpacing(tokens.spacing_lg)

        self._article_title = QLabel("")
        Typography.apply(self._article_title, "h1")
        article_layout.addWidget(self._article_title)

        # Structured Getting Started block (frame 19) — welcome line,
        # five numbered steps, DEMO FOLDER callout.
        self._structured_box = QWidget()
        structured = QVBoxLayout(self._structured_box)
        structured.setContentsMargins(0, 0, 0, 0)
        structured.setSpacing(tokens.spacing_lg)
        self._welcome_label = QLabel(
            i18n.get_text("help_welcome", "Welcome to Macena CS2 Analyzer!")
        )
        self._welcome_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        structured.addWidget(self._welcome_label)
        self._step_rows = []
        for number, (stem, title, desc) in enumerate(_GETTING_STARTED_STEPS, start=1):
            step = NumberedStep(
                number,
                i18n.get_text(f"{stem}_title", title),
                i18n.get_text(f"{stem}_desc", desc),
            )
            self._step_rows.append(step)
            structured.addWidget(step)

        # DEMO FOLDER mono callout. Path per frame (Linux/Steam target);
        # the ≥10 MB guard is real: MIN_DEMO_SIZE (DS-12) in
        # backend/data_sources/demo_format_adapter.py.
        callout = QFrame()
        callout.setObjectName("demo_folder_callout")
        callout_lay = QVBoxLayout(callout)
        callout_lay.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md
        )
        callout_lay.setSpacing(tokens.spacing_xs)
        self._callout_title = QLabel(
            i18n.get_text("demo_folder_title", "DEMO FOLDER · WHERE CS2 SAVES .DEM FILES")
        )
        self._callout_title.setObjectName("demo_folder_title")
        callout_lay.addWidget(self._callout_title)
        self._callout_body = QLabel(
            i18n.get_text("demo_folder_body", "Typical path on Linux / Steam:")
        )
        self._callout_body.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        callout_lay.addWidget(self._callout_body)
        callout_path = QLabel(
            "~/.steam/steam/steamapps/common/Counter-Strike Global Offensive" "/game/csgo/replays/"
        )
        callout_path.setObjectName("demo_folder_path")
        callout_path.setWordWrap(True)
        callout_lay.addWidget(callout_path)
        self._callout_caption = QLabel(
            i18n.get_text(
                "demo_folder_caption",
                "The analyzer expects .dem files ≥ 10 MB (DS-12 guard).",
            )
        )
        self._callout_caption.setStyleSheet(
            f"color: {tokens.text_tertiary}; "
            f"font-size: {tokens.font_size_caption}px; background: transparent;"
        )
        callout_lay.addWidget(self._callout_caption)
        structured.addWidget(callout)
        article_layout.addWidget(self._structured_box)

        # Plain content body (non-structured topics keep their doc text)
        self._content_label = QLabel(i18n.get_text("select_topic"))
        self._content_label.setWordWrap(True)
        self._content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._content_label.setFont(Typography.font("body"))
        self._content_label.setStyleSheet(
            f"color: {get_tokens().text_primary}; background: transparent;"
        )
        article_layout.addWidget(self._content_label)

        # RELATED — other topics as mini navigation cards
        self._related_header = QLabel(i18n.get_text("related_header", "RELATED"))
        self._related_header.setObjectName("help_panel_header")
        article_layout.addWidget(self._related_header)
        self._related_row = QHBoxLayout()
        self._related_row.setSpacing(12)
        article_layout.addLayout(self._related_row)

        # KEYBOARD HINTS — sunken rows
        self._hints_header = QLabel(i18n.get_text("keyboard_hints_header", "KEYBOARD HINTS"))
        self._hints_header.setObjectName("help_panel_header")
        article_layout.addWidget(self._hints_header)
        self._hint_labels = []
        for key, fallback in _KEYBOARD_HINTS:
            row = QFrame()
            row.setObjectName("hint_row")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(
                tokens.spacing_lg, tokens.spacing_sm, tokens.spacing_lg, tokens.spacing_sm
            )
            hint_label = QLabel(i18n.get_text(key, fallback))
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
            row_lay.addWidget(hint_label)
            self._hint_labels.append(hint_label)
            article_layout.addWidget(row)

        # Docs source — the REAL load path (help_system.docs_dir =
        # get_resource_path("data/docs"), *.md scanned at refresh).
        self._docs_tip = TipBox(
            title=i18n.get_text("docs_source_title", "Docs source"),
            body=i18n.get_text(
                "docs_source_body",
                "Programma_CS2_RENAN/data/docs/*.md · loaded via help_system.py",
            ),
        )
        article_layout.addWidget(self._docs_tip)

        article_layout.addStretch()
        right_scroll.setWidget(article)
        panels.addWidget(right_scroll, 1)
        layout.addLayout(panels, 1)

    # ── Data ──

    def _load_topics(self):
        if _HELP_AVAILABLE:
            try:
                hs = get_help_system()
                real_topics = hs.get_all_topics()
                if real_topics:
                    self._topics = real_topics
                    logger.info("Loaded %d help topics from knowledge base", len(real_topics))
                else:
                    logger.info("Knowledge base returned empty — using fallback topics")
                    self._topics = list(_FALLBACK_TOPICS)
            except Exception as e:
                logger.warning("help_system failed (%s), using fallback topics", e)
                self._topics = list(_FALLBACK_TOPICS)
        else:
            self._topics = list(_FALLBACK_TOPICS)

        self._populate_list(self._topics)

    def _visible_topics(self) -> list:
        query = self._search_input.text().strip().lower()
        if not query:
            return list(self._topics)
        return [
            t
            for t in self._topics
            if query in t.get("title", "").lower() or query in t.get("content", "").lower()
        ]

    def _populate_list(self, topics: list):
        while self._topics_col.count() > 0:
            item = self._topics_col.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._topic_rows = []

        self._topics_header.setText(f"{i18n.get_text('topics_header', 'TOPICS')} · {len(topics)}")
        for topic in topics:
            topic_id = topic.get("id", "")
            caption_spec = _TOPIC_CAPTIONS.get(topic_id)
            caption = i18n.get_text(*caption_spec) if caption_spec else ""
            row = _TopicRow(topic_id, topic.get("title", "Untitled"), caption)
            row.clicked.connect(self._select_topic)
            self._topic_rows.append(row)
            self._topics_col.addWidget(row)

        if not topics:
            self._selected_id = None
            return
        # Keep the previous selection when still visible; otherwise
        # default to Getting Started (the frame-19 landing article),
        # falling back to the first row.
        wanted = self._selected_id
        if not any(t.get("id") == wanted for t in topics):
            ids = [t.get("id", "") for t in topics]
            wanted = "getting_started" if "getting_started" in ids else ids[0]
        self._select_topic(wanted)

    # ── Actions ──

    def _select_topic(self, topic_id: str):
        self._selected_id = topic_id
        for row in self._topic_rows:
            row.set_selected(row.topic_id == topic_id)

        topic = next((t for t in self._topics if t.get("id") == topic_id), None)
        if topic is None:
            return
        self._article_title.setText(topic.get("title", ""))

        # Getting Started renders the structured frame-19 article; other
        # topics render their doc content verbatim (richer than frame).
        structured = topic_id == "getting_started"
        self._structured_box.setVisible(structured)
        self._content_label.setVisible(not structured)
        if not structured:
            self._content_label.setText(topic.get("content", ""))

        self._rebuild_related(topic_id)

    def _rebuild_related(self, current_id: str):
        while self._related_row.count() > 0:
            item = self._related_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        others = [t for t in self._topics if t.get("id") != current_id][:3]
        for topic in others:
            topic_id = topic.get("id", "")
            caption_spec = _TOPIC_CAPTIONS.get(topic_id)
            caption = i18n.get_text(*caption_spec) if caption_spec else ""
            card = MiniLinkCard(title=f"→ {topic.get('title', '')}", caption=caption)
            card.clicked.connect(lambda tid=topic_id: self._select_topic(tid))
            self._related_row.addWidget(card, 1)
        self._related_header.setVisible(bool(others))

    def _on_search(self, _text: str):
        self._populate_list(self._visible_topics())
