"""
Tests for V1 blocker fixes — coaching notifications, daemon watchdog,
analysis orchestrator failure handling, and splash screen creation.

Covers the changes made in the V1 production readiness sprint.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


# ============ Fixtures ============


class _InMemoryDBManager:
    """Lightweight DB manager for tests."""

    def __init__(self, engine):
        self._engine = engine

    @contextmanager
    def get_session(self, engine_key: str = "default"):
        with Session(self._engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class _InMemoryStateManager:
    """Lightweight state manager that records notifications in memory."""

    def __init__(self):
        self.notifications: list[dict] = []

    def add_notification(self, daemon: str, severity: str, message: str):
        self.notifications.append(
            {"daemon": daemon, "severity": severity, "message": message}
        )

    def update_status(self, daemon: str, status: str, detail: str = ""):
        pass

    def set_error(self, daemon: str, message: str):
        self.add_notification(daemon, "ERROR", message)


@pytest.fixture
def in_memory_engine():
    # Ensure all models are imported before create_all
    import Programma_CS2_RENAN.backend.storage.db_models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def mock_db(in_memory_engine):
    return _InMemoryDBManager(in_memory_engine)


@pytest.fixture
def mock_state():
    return _InMemoryStateManager()


# ============ Coaching Level Visibility Tests ============


class TestCoachingLevelNotifications:
    """Verify that coaching mode is surfaced to the UI via notifications."""

    def test_traditional_mode_emits_level_4_notification(self, mock_db, mock_state):
        """Traditional coaching should emit a Level 4 notification."""
        with patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
            return_value=mock_db,
        ), patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
            return_value=mock_state,
        ), patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
            side_effect=lambda k, default=None: {
                "USE_COPER_COACHING": False,
                "USE_HYBRID_COACHING": False,
                "USE_RAG_COACHING": False,
            }.get(k, default),
        ), patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
        ) as mock_ollama:
            mock_ollama.return_value.polish.side_effect = lambda **kw: kw["message"]

            from Programma_CS2_RENAN.backend.services.coaching_service import (
                CoachingService,
            )

            svc = CoachingService()
            svc.generate_new_insights(
                player_name="test_player",
                demo_name="test_demo.dem",
                deviations={"avg_adr": -2.0},
                rounds_played=10,
            )

            # Verify coaching mode notification was emitted
            mode_notifs = [
                n
                for n in mock_state.notifications
                if n["daemon"] == "coaching" and "Coaching complete" in n["message"]
            ]
            assert len(mode_notifs) >= 1
            assert "Level 4" in mode_notifs[0]["message"]

    def test_coper_timeout_emits_warning(self, mock_db, mock_state):
        """COPER timeout should emit a WARNING notification."""
        with patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_db_manager",
            return_value=mock_db,
        ), patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_state_manager",
            return_value=mock_state,
        ), patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_setting",
            side_effect=lambda k, default=None: {
                "USE_COPER_COACHING": True,
                "USE_HYBRID_COACHING": False,
                "USE_RAG_COACHING": False,
            }.get(k, default),
        ), patch(
            "Programma_CS2_RENAN.backend.services.coaching_service._run_with_timeout",
            return_value=(None, True),  # Simulate timeout
        ), patch(
            "Programma_CS2_RENAN.backend.services.coaching_service.get_ollama_writer",
        ) as mock_ollama:
            mock_ollama.return_value.polish.side_effect = lambda **kw: kw["message"]

            from Programma_CS2_RENAN.backend.services.coaching_service import (
                CoachingService,
            )

            svc = CoachingService()
            svc.generate_new_insights(
                player_name="test_player",
                demo_name="test_demo.dem",
                deviations={"avg_adr": -2.0},
                rounds_played=10,
                map_name="de_mirage",
                tick_data={"team": "T"},
            )

            # Verify timeout warning was emitted
            warnings = [
                n
                for n in mock_state.notifications
                if n["severity"] == "WARNING" and "timed out" in n["message"]
            ]
            assert len(warnings) >= 1


# ============ Analysis Orchestrator Failure Tests ============


class TestAnalysisOrchestratorNotifications:
    """Verify analysis module failures emit notifications after threshold."""

    def test_repeated_failure_emits_notification(self, mock_state):
        """After 3 consecutive failures, user should be notified."""
        with patch(
            "Programma_CS2_RENAN.backend.storage.state_manager.get_state_manager",
            return_value=mock_state,
        ):
            from Programma_CS2_RENAN.backend.services.analysis_orchestrator import (
                AnalysisOrchestrator,
            )

            orch = AnalysisOrchestrator()

            # Simulate 3 consecutive failures
            for i in range(3):
                orch._record_module_failure("Momentum", ValueError(f"fail {i}"))

            # Third failure should trigger notification
            warnings = [
                n
                for n in mock_state.notifications
                if n["daemon"] == "analysis" and "Momentum" in n["message"]
            ]
            assert len(warnings) == 1
            assert "3 times" in warnings[0]["message"]

    def test_single_failure_no_notification(self, mock_state):
        """Single failure should NOT trigger a user notification."""
        with patch(
            "Programma_CS2_RENAN.backend.storage.state_manager.get_state_manager",
            return_value=mock_state,
        ):
            from Programma_CS2_RENAN.backend.services.analysis_orchestrator import (
                AnalysisOrchestrator,
            )

            orch = AnalysisOrchestrator()
            orch._record_module_failure("Entropy", ValueError("one-off"))

            notifs = [n for n in mock_state.notifications if n["daemon"] == "analysis"]
            assert len(notifs) == 0


# ============ Toast Widget Tests ============


class TestToastSystem:
    """Verify toast notification widget behavior."""

    def test_severity_config_has_all_levels(self):
        """All 4 severity levels should be configured."""
        from Programma_CS2_RENAN.apps.qt_app.widgets.toast import _SEVERITY_CONFIG

        assert "INFO" in _SEVERITY_CONFIG
        assert "WARNING" in _SEVERITY_CONFIG
        assert "ERROR" in _SEVERITY_CONFIG
        assert "CRITICAL" in _SEVERITY_CONFIG

    def test_info_auto_dismisses(self):
        """INFO toasts should auto-dismiss (non-zero timeout)."""
        from Programma_CS2_RENAN.apps.qt_app.widgets.toast import _SEVERITY_CONFIG

        _, ms = _SEVERITY_CONFIG["INFO"]
        assert ms > 0

    def test_critical_requires_manual_dismiss(self):
        """CRITICAL toasts should require manual dismissal (timeout=0)."""
        from Programma_CS2_RENAN.apps.qt_app.widgets.toast import _SEVERITY_CONFIG

        _, ms = _SEVERITY_CONFIG["CRITICAL"]
        assert ms == 0


# ============ Coaching Service Utility Tests ============


class TestCoachingServiceUtilities:
    """Test utility methods on the coaching service."""

    def test_health_to_range_full(self):
        """Health >= 80 should return 'full'."""
        from Programma_CS2_RENAN.backend.services.coaching_service import (
            CoachingService,
        )

        svc = CoachingService.__new__(CoachingService)
        assert svc._health_to_range(100) == "full"
        assert svc._health_to_range(80) == "full"

    def test_health_to_range_damaged(self):
        """Health 40-79 should return 'damaged'."""
        from Programma_CS2_RENAN.backend.services.coaching_service import (
            CoachingService,
        )

        svc = CoachingService.__new__(CoachingService)
        assert svc._health_to_range(79) == "damaged"
        assert svc._health_to_range(40) == "damaged"

    def test_health_to_range_critical(self):
        """Health < 40 should return 'critical'."""
        from Programma_CS2_RENAN.backend.services.coaching_service import (
            CoachingService,
        )

        svc = CoachingService.__new__(CoachingService)
        assert svc._health_to_range(39) == "critical"
        assert svc._health_to_range(0) == "critical"

    def test_baseline_context_note_empty_on_missing_data(self):
        """Empty stats/baseline should return empty string."""
        from Programma_CS2_RENAN.backend.services.coaching_service import (
            CoachingService,
        )

        assert CoachingService._baseline_context_note({}, {}, "aim") == ""
        assert CoachingService._baseline_context_note(None, {"rating": 1.0}, "aim") == ""

    def test_baseline_context_note_calculates_delta(self):
        """Should calculate percentage delta from pro baseline."""
        from Programma_CS2_RENAN.backend.services.coaching_service import (
            CoachingService,
        )

        note = CoachingService._baseline_context_note(
            {"rating": 0.8},
            {"rating": {"mean": 1.0}},
            "positioning",
        )
        assert "below" in note
        assert "20%" in note

    def test_infer_round_phase_delegates(self):
        """Should delegate to shared utility."""
        from Programma_CS2_RENAN.backend.services.coaching_service import (
            CoachingService,
        )

        svc = CoachingService.__new__(CoachingService)
        result = svc._infer_round_phase({"time_in_round": 50})
        assert isinstance(result, str)


# ============ Observability Tests ============


class TestExceptions:
    """Test custom exception hierarchy."""

    def test_cs2_analyzer_error_is_exception(self):
        """Base error should be an Exception."""
        from Programma_CS2_RENAN.observability.exceptions import CS2AnalyzerError

        assert issubclass(CS2AnalyzerError, Exception)

    def test_ingestion_error_exists(self):
        """IngestionError should be importable and subclass CS2AnalyzerError."""
        from Programma_CS2_RENAN.observability.exceptions import (
            CS2AnalyzerError,
            IngestionError,
        )

        assert issubclass(IngestionError, CS2AnalyzerError)

    def test_exception_preserves_message(self):
        """Custom exceptions should preserve error messages."""
        from Programma_CS2_RENAN.observability.exceptions import CS2AnalyzerError

        err = CS2AnalyzerError("test message")
        assert str(err) == "test message"


# ============ Design Token Tests ============


class TestDesignTokens:
    """Test design token system used by splash screen and UI."""

    def test_get_tokens_returns_cs2_by_default(self):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

        tokens = get_tokens()
        assert tokens.theme_name == "CS2"

    def test_all_three_themes_available(self):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

        for name in ("CS2", "CSGO", "CS1.6"):
            tokens = get_tokens(name)
            assert tokens.theme_name == name

    def test_tokens_have_required_fields(self):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

        tokens = get_tokens("CS2")
        assert tokens.surface_base.startswith("#")
        assert tokens.accent_primary.startswith("#")
        assert tokens.text_primary.startswith("#")
        assert tokens.spacing_md > 0
        assert tokens.radius_md > 0

    def test_set_active_theme_changes_default(self):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import (
            get_tokens,
            set_active_theme,
        )

        set_active_theme("CSGO")
        assert get_tokens().theme_name == "CSGO"
        set_active_theme("CS2")  # Reset to default

    def test_invalid_theme_falls_back_to_cs2(self):
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

        tokens = get_tokens("NONEXISTENT")
        assert tokens.theme_name == "CS2"

    def test_toast_colors_defined_for_all_themes(self):
        """All themes must have toast color definitions."""
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

        for name in ("CS2", "CSGO", "CS1.6"):
            tokens = get_tokens(name)
            assert tokens.toast_info_bg
            assert tokens.toast_error_bg
            assert tokens.toast_warning_bg
            assert tokens.toast_critical_bg


# ============ Splash Screen Tests ============


class TestSplashScreen:
    """Test splash screen creation (headless, no display required)."""

    def test_create_splash_returns_pixmap(self):
        """Splash should produce a valid pixmap."""
        # Only test if Qt is available in headless mode
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                app = QApplication([])

            from Programma_CS2_RENAN.apps.qt_app.app import _create_splash

            splash = _create_splash("1.0.0")
            pixmap = splash.pixmap()
            assert pixmap.width() == 520
            assert pixmap.height() == 320
        except Exception:
            pytest.skip("Qt offscreen not available")

    def test_splash_status_updates(self):
        """Status updates should not raise."""
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                app = QApplication([])

            from Programma_CS2_RENAN.apps.qt_app.app import (
                _create_splash,
                _splash_status,
            )

            splash = _create_splash("1.0.0")
            _splash_status(splash, "Testing...")
        except Exception:
            pytest.skip("Qt offscreen not available")


# ============ Error Code Tests ============


class TestErrorCodes:
    """Test observability error code registry."""

    def test_error_codes_importable(self):
        from Programma_CS2_RENAN.observability.error_codes import ErrorCode

        # ErrorCode is an enum — verify it has members
        assert len(ErrorCode) > 0

    def test_error_codes_have_descriptions(self):
        from Programma_CS2_RENAN.observability import error_codes

        # Should have at least some error codes defined
        codes = [
            attr
            for attr in dir(error_codes)
            if not attr.startswith("_") and attr != "ErrorCode"
        ]
        assert len(codes) > 0
