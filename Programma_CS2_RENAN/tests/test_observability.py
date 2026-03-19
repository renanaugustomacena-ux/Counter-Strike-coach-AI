"""
Observability infrastructure tests.

Validates: JSON formatter output, correlation ID propagation, log level
env var override, error code registry completeness, tool logger file
creation, and log retention cleanup.
"""

import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from Programma_CS2_RENAN.observability.error_codes import (
    ErrorCode,
    get_all_codes,
    log_with_code,
)
from Programma_CS2_RENAN.observability.logger_setup import (
    JSONFormatter,
    _CorrelationFilter,
    _resolve_log_level,
    configure_log_level,
    configure_retention,
    get_correlation_id,
    get_logger,
    get_tool_logger,
    set_correlation_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_json_output(logger_instance: logging.Logger, message: str, **kwargs) -> dict:
    """Log a message and capture the JSON output from the first handler."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    buf: list[str] = []
    handler.emit = lambda record: buf.append(handler.format(record))  # type: ignore[assignment]
    logger_instance.addHandler(handler)
    try:
        logger_instance.warning(message, **kwargs)
        assert buf, "No log output captured"
        return json.loads(buf[0])
    finally:
        logger_instance.removeHandler(handler)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJSONFormatter:
    """JSON formatter produces valid, complete log entries."""

    def test_output_fields(self):
        """Verify mandatory fields: ts, lvl, mod, thread, msg."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="cs2analyzer.test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        raw = formatter.format(record)
        data = json.loads(raw)
        assert "ts" in data
        assert data["lvl"] == "WARNING"
        assert data["mod"] == "cs2analyzer.test"
        assert "thread" in data
        assert data["msg"] == "hello world"

    def test_includes_exception(self):
        """Verify exc_type, exc_msg, traceback fields when exc_info is set."""
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="cs2analyzer.test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="boom",
                args=(),
                exc_info=sys.exc_info(),
            )
        raw = formatter.format(record)
        data = json.loads(raw)
        assert data["exc_type"] == "ValueError"
        assert data["exc_msg"] == "test error"
        assert "traceback" in data
        assert "ValueError" in data["traceback"]

    def test_no_exception_fields_when_clean(self):
        """No exception fields when exc_info is None."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="cs2analyzer.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="clean",
            args=(),
            exc_info=None,
        )
        raw = formatter.format(record)
        data = json.loads(raw)
        assert "exc_type" not in data
        assert "traceback" not in data


class TestCorrelationID:
    """Correlation ID propagation via thread-local filter."""

    def test_set_and_get(self):
        cid = set_correlation_id("abc123")
        assert cid == "abc123"
        assert get_correlation_id() == "abc123"

    def test_auto_generate(self):
        cid = set_correlation_id()
        assert cid is not None
        assert len(cid) == 12

    def test_filter_injects_cid(self):
        set_correlation_id("test-cid")
        filt = _CorrelationFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="", args=(), exc_info=None,
        )
        filt.filter(record)
        assert record.correlation_id == "test-cid"  # type: ignore[attr-defined]

    def test_cid_in_json_output(self):
        set_correlation_id("json-cid")
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="msg", args=(), exc_info=None,
        )
        # Manually apply filter
        filt = _CorrelationFilter()
        filt.filter(record)
        raw = formatter.format(record)
        data = json.loads(raw)
        assert data["cid"] == "json-cid"


class TestLogLevelResolution:
    """CS2_LOG_LEVEL env var controls log level."""

    def test_default_is_info(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CS2_LOG_LEVEL", None)
            assert _resolve_log_level() == logging.INFO

    def test_debug_override(self):
        with mock.patch.dict(os.environ, {"CS2_LOG_LEVEL": "DEBUG"}):
            assert _resolve_log_level() == logging.DEBUG

    def test_invalid_falls_back_to_info(self):
        with mock.patch.dict(os.environ, {"CS2_LOG_LEVEL": "BANANA"}):
            assert _resolve_log_level() == logging.INFO


class TestConfigureLogLevel:
    """configure_log_level() changes all cs2analyzer loggers."""

    def test_changes_cs2analyzer_loggers(self):
        # Create a few test loggers
        a = logging.getLogger("cs2analyzer.test_a")
        b = logging.getLogger("cs2analyzer.test_b")
        a.setLevel(logging.INFO)
        b.setLevel(logging.INFO)

        configure_log_level(logging.DEBUG)

        assert a.level == logging.DEBUG
        assert b.level == logging.DEBUG

        # Restore
        configure_log_level(logging.INFO)


class TestGetLoggerIdempotent:
    """get_logger() returns the same instance without duplicate handlers."""

    def test_same_instance(self):
        logger1 = get_logger("cs2analyzer.idempotent_test")
        handler_count_1 = len(logger1.handlers)
        logger2 = get_logger("cs2analyzer.idempotent_test")
        assert logger1 is logger2
        assert len(logger2.handlers) == handler_count_1


class TestGetToolLogger:
    """get_tool_logger() creates logs/tools/ directory and JSON file."""

    def test_creates_tool_log(self, tmp_path):
        import Programma_CS2_RENAN.observability.logger_setup as ls

        original_log_dir = ls._log_dir
        ls._log_dir = str(tmp_path)
        try:
            # Use a unique name to avoid handler caching
            unique_name = f"test_tool_{os.getpid()}_{id(tmp_path)}"
            tool_logger = get_tool_logger(unique_name)
            tool_logger.info("test message from tool logger")

            tool_dir = tmp_path / "tools"
            assert tool_dir.is_dir()
            log_files = list(tool_dir.glob(f"{unique_name}_*.json"))
            assert len(log_files) >= 1
        finally:
            ls._log_dir = original_log_dir


class TestErrorCodeRegistry:
    """Error code registry is complete and well-formed."""

    def test_all_members_have_nonempty_fields(self):
        for member in ErrorCode:
            defn = member.value
            assert defn.code, f"{member.name} has empty code"
            assert defn.severity is not None, f"{member.name} has no severity"
            assert defn.module, f"{member.name} has empty module"
            assert defn.description, f"{member.name} has empty description"
            assert defn.remediation, f"{member.name} has empty remediation"

    def test_no_duplicate_codes(self):
        codes = [m.value.code for m in ErrorCode]
        assert len(codes) == len(set(codes)), f"Duplicate codes: {[c for c in codes if codes.count(c) > 1]}"

    def test_get_all_codes_returns_list(self):
        result = get_all_codes()
        assert isinstance(result, list)
        assert len(result) == len(ErrorCode)
        for entry in result:
            assert "code" in entry
            assert "severity" in entry
            assert "module" in entry


class TestLogWithCode:
    """log_with_code() correctly prefixes messages."""

    def test_format(self):
        result = log_with_code(ErrorCode.LS_01, "Handler unavailable for %s")
        assert result == "[LS-01] Handler unavailable for %s"

    def test_all_codes_format(self):
        for member in ErrorCode:
            result = log_with_code(member, "test")
            assert result.startswith("["), f"{member.name}: {result}"
            assert "] test" in result


class TestConfigureRetention:
    """configure_retention() removes old log files."""

    def test_removes_old_files(self, tmp_path):
        import Programma_CS2_RENAN.observability.logger_setup as ls

        original_log_dir = ls._log_dir
        ls._log_dir = str(tmp_path)
        try:
            # Create old and new log files
            old_file = tmp_path / "old.log"
            new_file = tmp_path / "new.log"
            old_file.write_text("old")
            new_file.write_text("new")

            # Set old file modification time to 60 days ago
            old_time = time.time() - (60 * 86400)
            os.utime(old_file, (old_time, old_time))

            configure_retention(max_days=30)

            assert not old_file.exists(), "Old file should have been deleted"
            assert new_file.exists(), "New file should remain"
        finally:
            ls._log_dir = original_log_dir

    def test_leaves_non_log_files(self, tmp_path):
        import Programma_CS2_RENAN.observability.logger_setup as ls

        original_log_dir = ls._log_dir
        ls._log_dir = str(tmp_path)
        try:
            txt_file = tmp_path / "readme.txt"
            txt_file.write_text("keep me")
            old_time = time.time() - (60 * 86400)
            os.utime(txt_file, (old_time, old_time))

            configure_retention(max_days=1)

            assert txt_file.exists(), "Non-log files should not be deleted"
        finally:
            ls._log_dir = original_log_dir

    def test_handles_missing_directory(self):
        import Programma_CS2_RENAN.observability.logger_setup as ls

        original_log_dir = ls._log_dir
        ls._log_dir = "/nonexistent/path/that/does/not/exist"
        try:
            # Should not raise
            configure_retention(max_days=1)
        finally:
            ls._log_dir = original_log_dir
