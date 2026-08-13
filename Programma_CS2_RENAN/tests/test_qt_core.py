"""Qt frontend tests — core modules, screen contracts, and signal logic.

First test coverage for the PySide6 frontend. Targets highest-risk areas:
i18n bridge, screen contracts, Worker signals, AppState diffing, ThemeEngine data.

Requires PySide6 installed. No pytest-qt dependency needed.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest

# Must be set BEFORE any PySide6 import — enables headless CI (no display server).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ── Path stabilization (same pattern as headless_validator) ──
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# ── QApplication fixture ──


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for the entire test session."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════════════════
# 1. i18n Bridge (no QApplication needed for most tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestI18nBridge:
    """Tests for QtLocalizationManager and translation loading."""

    def test_get_text_returns_known_key(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n

        result = i18n.get_text("app_name")
        assert result == "Macena CS2 Analyzer"

    def test_get_text_falls_back_to_key(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n

        result = i18n.get_text("nonexistent_key_xyz_12345")
        assert result == "nonexistent_key_xyz_12345"

    def test_set_language_switches(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n

        original = i18n.lang
        try:
            i18n.set_language("pt")
            assert i18n.lang == "pt"
            # The Portuguese translation for "app_name" should still work
            result = i18n.get_text("app_name")
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            i18n.set_language(original)

    def test_set_language_rejects_unknown(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n

        original = i18n.lang
        i18n.set_language("zz")
        assert i18n.lang == original  # should not change

    def test_json_translations_loaded(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import _JSON_TRANSLATIONS

        # At least English should be loaded from assets/i18n/en.json
        assert "en" in _JSON_TRANSLATIONS
        assert isinstance(_JSON_TRANSLATIONS["en"], dict)
        assert len(_JSON_TRANSLATIONS["en"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Screen Contract Validation
# ═══════════════════════════════════════════════════════════════════════════════

# Screens that can be constructed with just parent=None
_SIMPLE_SCREENS = [
    ("home_screen", "HomeScreen"),
    ("coach_screen", "CoachScreen"),
    ("match_history_screen", "MatchHistoryScreen"),
    ("match_detail_screen", "MatchDetailScreen"),
    ("performance_screen", "PerformanceScreen"),
    ("tactical_viewer_screen", "TacticalViewerScreen"),
    ("help_screen", "HelpScreen"),
    ("user_profile_screen", "UserProfileScreen"),
    ("profile_screen", "ProfileScreen"),
    ("steam_config_screen", "SteamConfigScreen"),
    ("faceit_config_screen", "FaceitConfigScreen"),
    ("wizard_screen", "WizardScreen"),
]

# All screen modules (including those needing special args)
_ALL_SCREEN_MODULES = [
    "home_screen",
    "coach_screen",
    "match_history_screen",
    "match_detail_screen",
    "performance_screen",
    "tactical_viewer_screen",
    "settings_screen",
    "help_screen",
    "user_profile_screen",
    "profile_screen",
    "steam_config_screen",
    "faceit_config_screen",
    "wizard_screen",
    "placeholder",
]


class TestScreenContracts:
    """Validate that all Qt screens are importable and follow the contract."""

    @pytest.mark.parametrize("module_name", _ALL_SCREEN_MODULES)
    def test_screen_module_importable(self, module_name):
        """Every screen module must import without error."""
        mod = importlib.import_module(f"Programma_CS2_RENAN.apps.qt_app.screens.{module_name}")
        assert mod is not None

    @pytest.mark.parametrize("module_name,class_name", _SIMPLE_SCREENS)
    def test_screen_has_on_enter(self, module_name, class_name):
        """Every screen class must have an on_enter method."""
        mod = importlib.import_module(f"Programma_CS2_RENAN.apps.qt_app.screens.{module_name}")
        cls = getattr(mod, class_name)
        assert hasattr(cls, "on_enter"), f"{class_name} missing on_enter()"
        assert callable(getattr(cls, "on_enter"))

    @pytest.mark.parametrize("module_name,class_name", _SIMPLE_SCREENS)
    def test_screen_constructable(self, qapp, module_name, class_name):
        """Screens with (parent=None) signature must construct without error."""
        mod = importlib.import_module(f"Programma_CS2_RENAN.apps.qt_app.screens.{module_name}")
        cls = getattr(mod, class_name)
        widget = cls(parent=None)
        assert widget is not None
        widget.deleteLater()

    def test_settings_screen_has_on_enter(self):
        """SettingsScreen (requires theme_engine) must have on_enter."""
        from Programma_CS2_RENAN.apps.qt_app.screens.settings_screen import SettingsScreen

        assert hasattr(SettingsScreen, "on_enter")

    def test_settings_screen_constructable(self, qapp):
        """SettingsScreen constructs with a ThemeEngine instance."""
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
        from Programma_CS2_RENAN.apps.qt_app.screens.settings_screen import SettingsScreen

        engine = ThemeEngine()
        widget = SettingsScreen(theme_engine=engine, parent=None)
        assert widget is not None
        widget.deleteLater()

    def test_placeholder_screen_constructable(self, qapp):
        """PlaceholderScreen constructs with title arg."""
        from Programma_CS2_RENAN.apps.qt_app.screens.placeholder import PlaceholderScreen

        widget = PlaceholderScreen(title="Test", description="desc")
        assert widget is not None
        widget.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Worker
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorker:
    """Tests for the background Worker/WorkerSignals pattern."""

    @staticmethod
    def _drain(qapp, timeout_ms=500):
        """Process events repeatedly to ensure cross-thread signals are delivered."""
        import time

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

    def test_worker_success_emits_result(self, qapp):
        from PySide6.QtCore import QThreadPool

        from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker

        results = []
        worker = Worker(lambda: 42)
        worker.signals.result.connect(lambda r: results.append(r))
        QThreadPool.globalInstance().start(worker)
        QThreadPool.globalInstance().waitForDone(3000)
        self._drain(qapp)
        assert 42 in results

    def test_worker_error_emits_error(self, qapp):
        from PySide6.QtCore import QThreadPool

        from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker

        errors = []

        def failing():
            raise ValueError("test error")

        worker = Worker(failing)
        worker.signals.error.connect(lambda e: errors.append(e))
        QThreadPool.globalInstance().start(worker)
        QThreadPool.globalInstance().waitForDone(3000)
        self._drain(qapp)
        assert any("test error" in e for e in errors)

    def test_worker_always_emits_finished(self, qapp):
        from PySide6.QtCore import QThreadPool

        from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker

        finished = []
        worker = Worker(lambda: "ok")
        worker.signals.finished.connect(lambda: finished.append(True))
        QThreadPool.globalInstance().start(worker)
        QThreadPool.globalInstance().waitForDone(3000)
        self._drain(qapp)
        assert len(finished) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AppState._apply (signal diffing logic)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAppStateApply:
    """Test the _apply signal-diffing logic without polling DB."""

    def _make_app_state(self):
        from Programma_CS2_RENAN.apps.qt_app.core.app_state import AppState

        return AppState()

    def test_apply_emits_on_change(self, qapp):
        state = self._make_app_state()
        received = []
        state.coach_status_changed.connect(lambda s: received.append(s))

        state._apply(
            {
                "service_active": True,
                "coach_status": "Training",
                "parsing_progress": 0.0,
                "belief_confidence": 0.0,
                "total_matches": 0,
                "current_epoch": 1,
                "total_epochs": 10,
                "train_loss": 0.5,
                "val_loss": 0.6,
                "eta_seconds": 120.0,
                "notifications": [],
            }
        )

        assert "Training" in received

    def test_apply_skips_unchanged(self, qapp):
        state = self._make_app_state()
        data = {
            "service_active": True,
            "coach_status": "Idle",
            "parsing_progress": 0.5,
            "belief_confidence": 0.7,
            "total_matches": 5,
            "current_epoch": 1,
            "total_epochs": 10,
            "train_loss": 0.5,
            "val_loss": 0.6,
            "eta_seconds": 0.0,
            "notifications": [],
        }

        # First apply
        state._apply(data)

        # Second apply with same data — should NOT re-emit
        received = []
        state.coach_status_changed.connect(lambda s: received.append(s))
        state._apply(data)

        assert len(received) == 0

    def test_apply_handles_none(self, qapp):
        state = self._make_app_state()
        # Should be a no-op, not raise
        state._apply(None)

    def test_apply_notifications(self, qapp):
        state = self._make_app_state()
        received = []
        state.notification_received.connect(lambda sev, msg: received.append((sev, msg)))

        state._apply(
            {
                "service_active": False,
                "coach_status": "Idle",
                "parsing_progress": 0.0,
                "belief_confidence": 0.0,
                "total_matches": 0,
                "current_epoch": 0,
                "total_epochs": 0,
                "train_loss": 0.0,
                "val_loss": 0.0,
                "eta_seconds": 0.0,
                "notifications": [
                    {"severity": "info", "message": "Demo ingested successfully"},
                ],
            }
        )

        assert ("info", "Demo ingested successfully") in received


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ThemeEngine (pure data tests, no rendering)
# ═══════════════════════════════════════════════════════════════════════════════


class TestThemeEngine:
    """Test token-derived palette behavior and rating functions."""

    def test_all_themes_resolvable(self):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import THEME_NAMES

        assert set(THEME_NAMES) == {"CS2", "CSGO", "CS1.6"}
        for name in THEME_NAMES:
            assert get_tokens(name).theme_name == name

    def test_qpalette_derives_from_tokens(self, qapp):
        from PySide6.QtGui import QColor

        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine

        engine = ThemeEngine()
        engine.apply_theme("CS2", qapp)
        pal = qapp.palette()
        tokens = get_tokens("CS2")
        assert pal.color(pal.ColorRole.Window) == QColor(tokens.surface_base)
        assert pal.color(pal.ColorRole.Highlight) == QColor(tokens.accent_primary)
        assert pal.color(pal.ColorRole.Base) == QColor(tokens.surface_sunken)
        # Restore default so later session-scoped tests see the boot theme.
        engine.apply_theme("CS2", qapp)

    def test_rating_color_good(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color

        color = rating_color(1.20)
        # Should be green
        assert color.greenF() > color.redF()

    def test_rating_color_bad(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color

        color = rating_color(0.80)
        # Should be red
        assert color.redF() > color.greenF()

    def test_rating_label_values(self):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_label

        assert rating_label(1.25) == "Excellent"
        assert rating_label(1.15) == "Good"
        assert rating_label(1.00) == "Average"
        assert rating_label(0.80) == "Below Avg"

    def test_theme_engine_default(self):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import CS2_TOKENS
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine

        engine = ThemeEngine()
        assert engine.active_theme == "CS2"
        # Read expected value from the design-token source of truth so the
        # test doesn't drift every time the P1-P4 aesthetic uplift bumps
        # a color. (The previous hard-coded `#1a1a1a` survived ec0a24a's
        # re-theming and broke CI once install got past numpy==2.4.3.)
        assert engine.chart_bg == CS2_TOKENS.chart_bg


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Typography (role fonts for painters and non-QLabel widgets)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTypography:
    """Test Typography.font() role sizing and the optional weight override."""

    def test_font_role_sizes_come_from_tokens(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

        tokens = get_tokens()
        assert Typography.font("title").pointSize() == tokens.font_size_title
        assert Typography.font("body").pointSize() == tokens.font_size_body
        assert Typography.font("stat").pointSize() == tokens.font_size_stat

    def test_font_weight_override_applies(self, qapp):
        from PySide6.QtGui import QFont

        from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

        default = Typography.font("body")
        assert default.weight() == QFont.Normal

        bold = Typography.font("body", QFont.Bold)
        assert bold.weight() == QFont.Bold
        # Weight override must not disturb the role's size or family.
        assert bold.pointSize() == default.pointSize()
        assert bold.family() == default.family()

    def test_font_mono_keeps_mono_family(self, qapp):
        from PySide6.QtGui import QFont

        from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

        mono_bold = Typography.font("mono", QFont.Bold)
        assert "Mono" in mono_bold.family()
        assert mono_bold.weight() == QFont.Bold

    def test_font_unknown_role_falls_back_to_body(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

        fallback = Typography.font("no_such_role")
        body = Typography.font("body")
        assert fallback.pointSize() == body.pointSize()
        assert fallback.family() == body.family()


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Component library alignment — frames 33/20 (Task 8)
# ═══════════════════════════════════════════════════════════════════════════════


class TestComponentLibrary:
    """ProBadge, StatBadge rating variant, EmptyState well/link, toast anatomy."""

    def test_pro_badge_side_property_roundtrip(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import ProBadge

        badge = ProBadge()
        assert badge.objectName() == "pro_badge"
        assert badge.text() == "PRO"
        assert badge.side() is None

        badge.set_side("ct")
        assert badge.side() == "ct"
        assert badge.property("side") == "ct"

        badge.set_side("t")
        assert badge.side() == "t"

        badge.set_side(None)
        assert badge.side() is None

    def test_stat_badge_rating_variant_colors_by_threshold(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import StatBadge

        badge = StatBadge()
        badge.set_rating(1.28, "> 1.10 · GREEN")
        assert badge._value_label.text() == "1.28"
        assert badge._label.text() == "> 1.10 · GREEN"
        assert rating_color(1.28).name() in badge._value_label.styleSheet()

        badge.set_rating(0.84, "< 0.90 · RED")
        assert rating_color(0.84).name() in badge._value_label.styleSheet()

    def test_empty_state_icon_well_and_ghost_link(self, qapp):
        from PySide6.QtWidgets import QFrame, QPushButton

        from Programma_CS2_RENAN.apps.qt_app.widgets.components import EmptyState

        clicks: list[str] = []
        state = EmptyState(
            icon_text="X",
            title="No matches found",
            cta_text="Select Demo Folder",
            link_text="Or read the guide →",
            link_cb=lambda: clicks.append("cb"),
        )
        well = state.findChild(QFrame, "empty_state_well")
        assert well is not None
        assert well.width() == well.height() == 64

        link = state.findChild(QPushButton, "empty_state_link")
        assert link is not None and link.text() == "Or read the guide →"
        state.link_clicked.connect(lambda: clicks.append("signal"))
        link.click()
        assert "cb" in clicks and "signal" in clicks

    def test_toast_title_and_auto_caption(self, qapp):
        from PySide6.QtWidgets import QLabel

        from Programma_CS2_RENAN.apps.qt_app.widgets.toast import ToastWidget

        info = ToastWidget("INFO", "Demo analysis complete")
        title = info.findChild(QLabel, "toast_title")
        assert title is not None and title.text() == "Info"
        caption = info.findChild(QLabel, "toast_caption")
        assert caption is not None and caption.text() == "auto · 5s"

        # CRITICAL never auto-dismisses → no caption row.
        critical = ToastWidget("CRITICAL", "Teacher daemon crashed")
        assert critical.findChild(QLabel, "toast_caption") is None
        assert critical.findChild(QLabel, "toast_title").text() == "Critical"

    def test_progress_ring_size_presets(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import ProgressRing

        presets = (ProgressRing.SMALL, ProgressRing.DEFAULT, ProgressRing.COACH, ProgressRing.HERO)
        assert presets == (48, 64, 80, 128)
        ring = ProgressRing(0.73)
        assert ring.width() == ProgressRing.DEFAULT
        assert ring._thickness == 8

    def test_toast_container_eviction_and_refit(self, qapp):
        """MAX_VISIBLE eviction + sizeHint-based refit survive the wrapper restructure."""
        from Programma_CS2_RENAN.apps.qt_app.widgets.toast import _MAX_VISIBLE, ToastContainer

        container = ToastContainer()
        for i in range(4):
            container.add_toast("INFO", f"toast {i}")
        qapp.processEvents()
        assert len(container._toasts) == _MAX_VISIBLE
        # Height must fit every visible toast's real (title+caption) hint.
        assert container.height() >= sum(t.sizeHint().height() for t in container._toasts)
        assert container.isVisibleTo(container.parentWidget()) or container.isVisible()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ChatPanel — frame 07 (Task 9)
# ═══════════════════════════════════════════════════════════════════════════════


class TestChatPanel:
    """Bubble anatomy, meta footnotes, suggestion chips, submit contract."""

    @staticmethod
    def _bubbles(panel):
        from PySide6.QtWidgets import QFrame

        return [f for f in panel.findChildren(QFrame) if f.objectName() == "chat_bubble"]

    def test_add_message_with_meta_builds_bubble(self, qapp):
        from PySide6.QtWidgets import QLabel

        from Programma_CS2_RENAN.apps.qt_app.widgets.coaching import ChatPanel

        panel = ChatPanel()
        panel.add_message(
            "coach",
            "Three patterns from your data vs ZywOo pro reference.",
            meta="confidence 0.82 · 4 demos referenced · RAP-Pedagogy",
        )
        bubbles = self._bubbles(panel)
        assert len(bubbles) == 1
        assert bubbles[0].property("role") == "coach"
        meta = panel.findChild(QLabel, "chat_bubble_meta")
        assert meta is not None
        assert meta.text() == "confidence 0.82 · 4 demos referenced · RAP-Pedagogy"

    def test_roles_and_clear(self, qapp):
        from PySide6.QtWidgets import QLabel

        from Programma_CS2_RENAN.apps.qt_app.widgets.coaching import ChatPanel

        panel = ChatPanel()
        panel.add_message("coach", "Hey macena — analyzed your last 10 Mirage matches.")
        panel.add_message("user", "How can I improve positioning?")
        panel.add_message("system", "Coach is offline.")
        bubbles = self._bubbles(panel)
        assert len(bubbles) == 2  # system renders as centered caption, not a bubble
        assert {b.property("role") for b in bubbles} == {"coach", "user"}
        assert panel.findChild(QLabel, "chat_system").text() == "Coach is offline."

        panel.clear()
        assert self._bubbles(panel) == []

    def test_suggestion_click_emits_text(self, qapp):
        from PySide6.QtWidgets import QPushButton

        from Programma_CS2_RENAN.apps.qt_app.widgets.coaching import ChatPanel

        panel = ChatPanel()
        panel.set_suggestions(["Analyze utility usage", "How can I improve positioning?"])
        received: list[str] = []
        panel.suggestion_clicked.connect(received.append)
        chips = [
            b
            for b in panel._suggestions_row.findChildren(QPushButton)
            if b.text() == "Analyze utility usage"
        ]
        assert len(chips) == 1
        chips[0].click()
        assert received == ["Analyze utility usage"]

    def test_submit_clears_input_and_emits(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.coaching import ChatPanel

        panel = ChatPanel()
        received: list[str] = []
        panel.message_submitted.connect(received.append)
        panel._input.setText("  What should I focus on improving?  ")
        panel._input.returnPressed.emit()
        assert received == ["What should I focus on improving?"]
        assert panel._input.text() == ""
        # Empty input never emits
        panel._input.setText("   ")
        panel._input.returnPressed.emit()
        assert len(received) == 1

    def test_set_status_updates_header(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.widgets.coaching import ChatPanel

        panel = ChatPanel()
        panel.set_status(True, "ollama", "gemma3:e2b")
        assert panel._status_text.text() == "Online"
        assert panel._backend_label.text() == "ollama · gemma3:e2b"
        assert get_tokens().success in panel._status_dot.styleSheet()

        panel.set_status(False, "ollama", "gemma3:e2b")
        assert panel._status_text.text() == "Offline"
        assert get_tokens().error in panel._status_dot.styleSheet()


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Shared primitives — frames 06/17/18/19 furniture (Task 10)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSharedPrimitives:
    """Construction + text round-trip for the five frame-furniture primitives."""

    def test_drivers_list_rows(self, qapp):
        from PySide6.QtWidgets import QFrame, QLabel

        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import DriversList

        drivers = DriversList()
        drivers.set_rows(
            [
                ("success", "Sample count · 47 personal demos analyzed"),
                ("warning", "Map coverage · 6 of 9 competitive maps seen"),
            ]
        )
        texts = [
            label.text()
            for label in drivers.findChildren(QLabel)
            if label.objectName() == "drivers_text"
        ]
        assert texts == [
            "Sample count · 47 personal demos analyzed",
            "Map coverage · 6 of 9 competitive maps seen",
        ]
        squares = [f for f in drivers.findChildren(QFrame) if f.objectName() == "drivers_square"]
        assert len(squares) == 2 and squares[0].width() == 8
        assert get_tokens().success in squares[0].styleSheet()
        assert get_tokens().warning in squares[1].styleSheet()

        drivers.set_rows([("info", "one row")])  # replaces, not appends
        squares = [f for f in drivers.findChildren(QFrame) if f.objectName() == "drivers_square"]
        assert len(squares) == 1

    def test_tip_box_text_roundtrip(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import TipBox

        tip = TipBox("Stored locally", "Nothing uploaded anywhere. FE-04.")
        assert tip.objectName() == "tip_box"
        assert tip._title_label.text() == "Stored locally"
        assert tip._body_label.text() == "Nothing uploaded anywhere. FE-04."
        tip.set_title("Tip")
        tip.set_body("Choose a drive with at least 50 GB free.")
        assert tip._title_label.text() == "Tip"
        assert tip._body_label.text() == "Choose a drive with at least 50 GB free."

    def test_numbered_step_texts(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import NumberedStep

        step = NumberedStep(3, "Let the analyzer ingest your .dem files", "Click Analyze Demos")
        assert step._circle.text() == "3"
        assert step._circle.objectName() == "numbered_step_circle"
        assert step._title_label.text() == "Let the analyzer ingest your .dem files"
        assert step._desc_label.text() == "Click Analyze Demos"

    def test_db_record_card_rows_and_value_color(self, qapp):
        from PySide6.QtWidgets import QLabel

        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import DbRecordCard

        card = DbRecordCard(
            "Database record", 'SELECT * FROM PlayerProfile WHERE player_name = "macena"'
        )
        assert card._title_label.text() == "Database record"
        assert "PlayerProfile" in card._sql_label.text()

        card.set_rows(
            [
                ("id", "42", None),
                ("matches_analyzed", "47", "success"),
            ]
        )
        values = [
            label for label in card.findChildren(QLabel) if label.objectName() == "db_record_value"
        ]
        assert [v.text() for v in values] == ["42", "47"]
        assert get_tokens().success in values[1].styleSheet()
        assert values[0].styleSheet() == ""

    def test_mono_footer_text(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import MonoFooter

        footer = MonoFooter("PlayerMatchStats · rating_components from hltv_components JSON")
        assert footer.objectName() == "mono_footer"
        assert footer.text() == "PlayerMatchStats · rating_components from hltv_components JSON"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. MapTile + MetricBarRow (per-map grid and HLTV bar-row primitives)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMapTile:
    def test_construction_and_value_roundtrip(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components.map_tile import MapTile

        tile = MapTile()
        tile.set_data("Mirage", 1.22, 84, 1.19, 12)
        assert tile._map_name == "Mirage"
        assert tile._rating == pytest.approx(1.22)
        assert tile._adr == pytest.approx(84)
        assert tile._kd == pytest.approx(1.19)
        assert tile._matches == 12
        # Bottom bar fill = min(rating / 1.5, 1.0) in the rating color.
        assert tile._fill_frac() == pytest.approx(1.22 / 1.5)
        tile.set_data("Ancient", 2.4, 53, 0.72, 6)
        assert tile._fill_frac() == pytest.approx(1.0)  # clamps at full
        tile.resize(320, 130)
        assert not tile.grab().isNull()
        tile.deleteLater()

    def test_exported_from_components_package(self):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import (  # noqa: F401
            MapTile,
            MetricBarRow,
        )


class TestMetricBarRow:
    def test_construction_and_value_roundtrip(self, qapp):
        from PySide6.QtGui import QColor

        from Programma_CS2_RENAN.apps.qt_app.widgets.components.metric_bar_row import (
            MetricBarRow,
        )

        row = MetricBarRow()
        row.set_metric("Rating Impact", "1.28", 1.28 / 1.5, QColor("#4caf50"))
        assert row._label == "Rating Impact"
        assert row._value_text == "1.28"
        assert row._frac == pytest.approx(1.28 / 1.5)
        row.set_metric("Clutch Win%", "67%", 1.7, QColor("#4caf50"))
        assert row._frac == pytest.approx(1.0)  # overshoot clamps
        row.set_metric("Was Traded", "0.62", -0.4, QColor("#00D9FF"))
        assert row._frac == pytest.approx(0.0)  # negative clamps
        row.resize(420, 28)
        assert not row.grab().isNull()
        row.deleteLater()


class TestDeltaChip:
    """Benchmark-relative ± chip (research 29.2): text, tint, hide rules."""

    def test_construction_and_delta_directions(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import DeltaChip

        chip = DeltaChip()
        assert chip.objectName() == "delta_chip"
        assert chip.isHidden()  # starts hidden until a real delta lands

        chip.set_delta(0.09, "vs 30-day avg")
        assert chip.text() == "▲ +0.09 vs 30-day avg"
        assert get_tokens().success in chip.styleSheet()
        assert not chip.isHidden()

        chip.set_delta(-0.12, "vs 47-match avg")
        assert chip.text() == "▼ -0.12 vs 47-match avg"
        assert get_tokens().error in chip.styleSheet()
        assert not chip.isHidden()
        chip.deleteLater()

    def test_zero_none_and_rounded_zero_hide(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components import DeltaChip

        chip = DeltaChip()
        chip.set_delta(0.2, "vs avg")  # show first so hiding is observable
        assert not chip.isHidden()

        chip.set_delta(0.0, "vs avg")
        assert chip.isHidden() and chip.text() == ""

        chip.set_delta(0.3, "vs avg")
        chip.set_delta(None, "vs avg")
        assert chip.isHidden()

        # A delta that FORMATS to zero must not claim an arrow ("+0.00").
        chip.set_delta(0.004, "vs avg")
        assert chip.isHidden()
        chip.set_delta(-0.004, "vs avg")
        assert chip.isHidden()

        # Custom fmt: same value is meaningful at higher precision.
        chip.set_delta(0.004, "vs avg", fmt="{:+.3f}")
        assert chip.text() == "▲ +0.004 vs avg"
        chip.deleteLater()


class TestProComparisonPure:
    """Frame-15 pure functions: radar mapping, winner rule, style archetypes."""

    def _fixture_pair(self):
        from tools.ui_fixtures import (
            PRO_COMPARISON_STATS_DONK,
            PRO_COMPARISON_STATS_ZYWOO,
        )

        return dict(PRO_COMPARISON_STATS_ZYWOO), dict(PRO_COMPARISON_STATS_DONK)

    def test_radar_axes_frame15_shape(self):
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _radar_axes,
        )

        a, b = self._fixture_pair()
        vals_a, vals_b = _radar_axes(a, b)
        assert len(vals_a) == len(vals_b) == 8
        assert all(0.0 <= v <= 100.0 for v in vals_a + vals_b)
        # Frame 15: ZywOo leads Aim/Utility/Clutch/Positioning/Economy/Survival,
        # donk leads Opening/Aggression (axis order per _RADAR_AXIS_KEYS).
        zywoo_leads = (0, 2, 3, 4, 6, 7)
        donk_leads = (1, 5)
        for i in zywoo_leads:
            assert vals_a[i] > vals_b[i], f"axis {i}: expected ZywOo lead"
        for i in donk_leads:
            assert vals_b[i] > vals_a[i], f"axis {i}: expected donk lead"

    def test_radar_axes_empty_axis_renders_neutral_midpoint(self):
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _radar_axes,
        )

        # No utility/clutch keys on either side (today's real VM payload):
        # those axes must fall back to 50/50, never spike to center.
        a = {"rating_2_0": 1.1, "kpr": 0.7, "dpr": 0.6, "kast": 0.7,
             "headshot_pct": 0.5, "opening_duel_win_pct": 0.5}
        b = {"rating_2_0": 1.0, "kpr": 0.8, "dpr": 0.7, "kast": 0.65,
             "headshot_pct": 0.55, "opening_duel_win_pct": 0.52}
        vals_a, vals_b = _radar_axes(a, b)
        assert vals_a[2] == vals_b[2] == 50.0  # Utility
        assert vals_a[3] == vals_b[3] == 50.0  # Clutch
        # One-sided keys are skipped pairwise: smoke on A only must not
        # distort Aim.
        a_smoke = dict(a, smoke_kill_pct=0.2)
        vals_a2, vals_b2 = _radar_axes(a_smoke, b)
        assert vals_a2[0] == pytest.approx(vals_a[0])
        assert vals_b2[0] == pytest.approx(vals_b[0])

    def test_h2h_winner_rule(self):
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _h2h_winner,
        )

        assert _h2h_winner(1.28, 1.24, 0.02) == 1        # ZywOo +0.04
        assert _h2h_winner(88.2, 92.7, 0.5) == -1        # donk +4.5
        assert _h2h_winner(2.8, 2.9, 0.5) == 0           # flash assists: even
        assert _h2h_winner(20, 20, None) is None         # neutral row (maps)
        assert _h2h_winner(None, 1.2, 0.02) is None      # absent side: no winner

    def test_h2h_fixture_outcomes_match_frame15(self):
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _H2H_ROWS,
            _h2h_winner,
            _metric_value,
        )

        a, b = self._fixture_pair()
        outcomes = [
            _h2h_winner(_metric_value(a, key), _metric_value(b, key), eps)
            for key, _i18n, _fb, _kind, eps in _H2H_ROWS
        ]
        # rating kd adr kast hs opening clutch he flash smoke trade survival maps
        assert outcomes == [1, -1, -1, 1, -1, -1, 1, 1, 0, 1, -1, 1, None]

    def test_style_summary_support_and_entry(self):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _style_summary,
        )

        a, b = self._fixture_pair()
        headline_a, detail_a = _style_summary(a, b)
        assert headline_a == i18n.get_text("procomp.style.support", "team-enabling support")
        assert detail_a
        headline_b, _ = _style_summary(b, a)
        assert headline_b == i18n.get_text("procomp.style.entry", "aggressive entry rifler")

    def test_style_summary_anchor_branch(self):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _style_summary,
        )

        a = {"kast": 0.70, "he_damage_per_round": 10.0, "kpr": 0.60, "dpr": 0.50,
             "opening_duel_win_pct": 0.48, "clutch_win_pct": 0.62, "adr": 70.0}
        b = {"kast": 0.75, "he_damage_per_round": 12.0, "kpr": 0.78, "dpr": 0.60,
             "opening_duel_win_pct": 0.55, "clutch_win_pct": 0.50, "adr": 85.0}
        headline, _ = _style_summary(a, b)
        assert headline == i18n.get_text("procomp.style.anchor", "late-round anchor")

    def test_style_summary_damage_branch(self):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _style_summary,
        )

        a = {"adr": 95.0, "kast": 0.70, "kpr": 0.60, "dpr": 0.60,
             "opening_duel_win_pct": 0.50}
        b = {"adr": 80.0, "kast": 0.70, "kpr": 0.60, "dpr": 0.60,
             "opening_duel_win_pct": 0.50}
        headline, _ = _style_summary(a, b)
        assert headline == i18n.get_text("procomp.style.damage", "damage-first playmaker")

    def test_style_summary_balanced_fallback(self):
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
        from Programma_CS2_RENAN.apps.qt_app.screens.pro_comparison_screen import (
            _style_summary,
        )

        a, _b = self._fixture_pair()
        headline, _ = _style_summary(dict(a), dict(a))  # identical → nothing dominant
        assert headline == i18n.get_text("procomp.style.balanced", "balanced all-rounder")
        empty_headline, _ = _style_summary({}, {})
        assert empty_headline == i18n.get_text("procomp.style.balanced", "balanced all-rounder")


class TestValueAnimations:
    """Task 28 micro-motions: deterministic under the kill-switch, live otherwise."""

    def test_count_up_disabled_sets_immediately(self, qapp, monkeypatch):
        from PySide6.QtWidgets import QLabel

        from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator

        monkeypatch.setenv("MACENA_UI_ANIMATIONS", "0")
        label = QLabel()
        anim = Animator.count_up(label, 1.34, fmt="{:.2f}")
        assert anim is None
        assert label.text() == "1.34"
        label.deleteLater()

    def test_sweep_ring_disabled_sets_immediately(self, qapp, monkeypatch):
        from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
        from Programma_CS2_RENAN.apps.qt_app.widgets.components.progress_ring import (
            ProgressRing,
        )

        monkeypatch.setenv("MACENA_UI_ANIMATIONS", "0")
        ring = ProgressRing()
        assert Animator.sweep_ring(ring, 0.73) is None
        assert ring._value == pytest.approx(0.73)
        ring.deleteLater()

    def test_count_up_enabled_reaches_end_value(self):
        """Live-animation path runs in a SUBPROCESS.

        Running a real QVariantAnimation to completion inside this shared
        pytest process poisons Qt's global animation driver on the Windows
        offscreen platform: the suite then aborts natively (Fatal Python
        error) during a later processEvents — reproduced 5/5 in-suite,
        0/10 with the smoke file alone, and bisected to exactly this test.
        Subprocess isolation keeps the enabled-path coverage without the
        cross-test poison. The real app is unaffected (native platform).
        """
        import subprocess
        import sys
        import textwrap

        code = textwrap.dedent(
            """
            import os, sys, time
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            os.environ["MACENA_UI_ANIMATIONS"] = "1"
            sys.path.insert(0, os.getcwd())
            from PySide6.QtCore import QAbstractAnimation
            from PySide6.QtWidgets import QApplication, QLabel
            app = QApplication([])
            from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
            label = QLabel()
            anim = Animator.count_up(label, 47.0, fmt="{:.0f}", duration=60)
            assert anim is not None
            deadline = time.monotonic() + 5.0
            while anim.state() != QAbstractAnimation.Stopped:
                if time.monotonic() > deadline:
                    raise SystemExit("animation never finished")
                app.processEvents()
                time.sleep(0.01)
            assert label.text() == "47", label.text()
            print("OK")
            """
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_project_root),
        )
        assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        assert "OK" in proc.stdout


class TestStepperLabels:
    """Task 27: optional per-step captions (frame 18) stay backward-compatible."""

    def test_unlabeled_geometry_unchanged(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components.stepper import Stepper

        s = Stepper(step_count=5, current_step=0)
        # Width formula: n*dot_diameter + (n-1)*bar + 8 padding. Height:
        # dot + 2*6px margin — 6px (was 4) so the current-step ring's 2px
        # stroke at r+4 no longer clips 1px at the top and bottom edges.
        assert s.width() == 5 * 14 + 4 * 48 + 8
        assert s.height() == 14 + 12
        assert s.labels == []
        s.deleteLater()

    def test_labeled_mode_grows_and_paints(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components.stepper import Stepper

        labels = ["Intro", "Name", "Brain Path", "Demo Path", "Launch"]
        plain = Stepper(step_count=5)
        s = Stepper(step_count=5, current_step=2, labels=labels)
        assert s.labels == labels
        assert s.height() > plain.height()  # caption row added
        assert s.width() >= plain.width()
        assert not s.grab().isNull()  # labeled paint path runs clean
        s.deleteLater()
        plain.deleteLater()

    def test_labels_must_match_step_count(self, qapp):
        import pytest as _pytest

        from Programma_CS2_RENAN.apps.qt_app.widgets.components.stepper import Stepper

        with _pytest.raises(ValueError):
            Stepper(step_count=5, labels=["only", "three", "labels"])
        s = Stepper(step_count=3)
        with _pytest.raises(ValueError):
            s.set_labels(["a", "b"])
        s.set_labels(["a", "b", "c"])
        assert s.labels == ["a", "b", "c"]
        s.set_labels(None)
        assert s.labels == []
        s.deleteLater()

    def test_navigation_still_works_with_labels(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.widgets.components.stepper import Stepper

        s = Stepper(step_count=5, labels=["A", "B", "C", "D", "E"])
        seen = []
        s.step_changed.connect(seen.append)
        s.advance()
        s.advance()
        s.retreat()
        assert s.current_step == 1
        assert seen == [1, 2, 1]
        s.current_step = 99  # clamps to last step
        assert s.current_step == 4
        s.deleteLater()
