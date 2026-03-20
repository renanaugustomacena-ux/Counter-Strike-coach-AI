"""Qt frontend tests — core modules, screen contracts, and signal logic.

First test coverage for the PySide6 frontend. Targets highest-risk areas:
i18n bridge, screen contracts, Worker signals, AppState diffing, ThemeEngine data.

Requires PySide6 installed. No pytest-qt dependency needed.
"""

import importlib
import sys
from pathlib import Path

import pytest

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
        from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import (
            _JSON_TRANSLATIONS,
        )

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
        mod = importlib.import_module(
            f"Programma_CS2_RENAN.apps.qt_app.screens.{module_name}"
        )
        assert mod is not None

    @pytest.mark.parametrize("module_name,class_name", _SIMPLE_SCREENS)
    def test_screen_has_on_enter(self, module_name, class_name):
        """Every screen class must have an on_enter method."""
        mod = importlib.import_module(
            f"Programma_CS2_RENAN.apps.qt_app.screens.{module_name}"
        )
        cls = getattr(mod, class_name)
        assert hasattr(cls, "on_enter"), f"{class_name} missing on_enter()"
        assert callable(getattr(cls, "on_enter"))

    @pytest.mark.parametrize("module_name,class_name", _SIMPLE_SCREENS)
    def test_screen_constructable(self, qapp, module_name, class_name):
        """Screens with (parent=None) signature must construct without error."""
        mod = importlib.import_module(
            f"Programma_CS2_RENAN.apps.qt_app.screens.{module_name}"
        )
        cls = getattr(mod, class_name)
        widget = cls(parent=None)
        assert widget is not None
        widget.deleteLater()

    def test_settings_screen_has_on_enter(self):
        """SettingsScreen (requires theme_engine) must have on_enter."""
        from Programma_CS2_RENAN.apps.qt_app.screens.settings_screen import (
            SettingsScreen,
        )

        assert hasattr(SettingsScreen, "on_enter")

    def test_settings_screen_constructable(self, qapp):
        """SettingsScreen constructs with a ThemeEngine instance."""
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
        from Programma_CS2_RENAN.apps.qt_app.screens.settings_screen import (
            SettingsScreen,
        )

        engine = ThemeEngine()
        widget = SettingsScreen(theme_engine=engine, parent=None)
        assert widget is not None
        widget.deleteLater()

    def test_placeholder_screen_constructable(self, qapp):
        """PlaceholderScreen constructs with title arg."""
        from Programma_CS2_RENAN.apps.qt_app.screens.placeholder import (
            PlaceholderScreen,
        )

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

        state._apply({
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
        })

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
        state.notification_received.connect(
            lambda sev, msg: received.append((sev, msg))
        )

        state._apply({
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
        })

        assert ("info", "Demo ingested successfully") in received


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ThemeEngine (pure data tests, no rendering)
# ═══════════════════════════════════════════════════════════════════════════════


class TestThemeEngine:
    """Test palette data and rating functions."""

    def test_palettes_all_themes_present(self):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import PALETTES

        assert "CS2" in PALETTES
        assert "CSGO" in PALETTES
        assert "CS1.6" in PALETTES

    def test_palette_has_required_slots(self):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import PALETTES

        required = {"surface", "surface_alt", "accent_primary", "chart_bg"}
        for name, palette in PALETTES.items():
            assert required.issubset(set(palette.keys())), f"{name} missing slots"

    def test_rating_color_good(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
            COLOR_GREEN,
            rating_color,
        )

        color = rating_color(1.20)
        # Should be green
        assert color.greenF() > color.redF()

    def test_rating_color_bad(self, qapp):
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
            COLOR_RED,
            rating_color,
        )

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
        from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine

        engine = ThemeEngine()
        assert engine.active_theme == "CS2"
        assert engine.chart_bg == "#1a1a1a"
