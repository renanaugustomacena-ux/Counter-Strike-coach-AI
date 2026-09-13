"""Boot round (WP3) — the Session Engine daemon launch contract.

The daemon used to be spawned as a bare ``python.exe session_engine.py``
with no hidden-console flag: every windowless launch (pythonw, an Explorer
shortcut, the packaged exe) popped a blank black console window, and in a
frozen build ``sys.executable`` IS the GUI exe, so the "daemon" was a
second copy of the dashboard that tripped the single-instance guard.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from Programma_CS2_RENAN.core.lifecycle import AppLifecycleManager

_MODULE = "Programma_CS2_RENAN.core.session_engine"


def test_daemon_command_dev_uses_module_form():
    mgr = AppLifecycleManager()
    assert mgr.daemon_command() == [sys.executable, "-m", _MODULE]


def test_daemon_command_frozen_relaunches_self_with_daemon_flag(monkeypatch, tmp_path):
    exe = tmp_path / "Macena_CS2_Analyzer.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    mgr = AppLifecycleManager()
    assert mgr.daemon_command() == [str(exe), "--daemon"]


def test_hidden_console_kwargs_match_the_platform():
    kwargs = AppLifecycleManager.hidden_console_kwargs()
    if os.name == "nt":
        assert kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW
        info = kwargs["startupinfo"]
        assert info.dwFlags & subprocess.STARTF_USESHOWWINDOW
        assert info.wShowWindow == subprocess.SW_HIDE
    else:
        assert kwargs == {}


class _FakeProc:
    pid = 4242

    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


def _capture_popen(monkeypatch):
    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return _FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    return captured


def test_launch_daemon_hides_console_and_logs_under_log_dir(monkeypatch, tmp_path):
    import Programma_CS2_RENAN.core.config as config

    monkeypatch.setattr(config, "LOG_DIR", str(tmp_path))
    captured = _capture_popen(monkeypatch)
    mgr = AppLifecycleManager()
    try:
        proc = mgr.launch_daemon()
        assert proc is not None
        assert captured["cmd"] == mgr.daemon_command()
        kwargs = captured["kwargs"]
        assert kwargs["stdin"] is subprocess.PIPE
        assert Path(kwargs["stdout"].name) == tmp_path / "daemon_out.log"
        assert Path(kwargs["stderr"].name) == tmp_path / "daemon_err.log"
        if os.name == "nt":
            assert kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW
            assert kwargs["startupinfo"].wShowWindow == subprocess.SW_HIDE
    finally:
        mgr._daemon_process = None
        mgr.shutdown()


def test_launch_daemon_frozen_needs_no_source_file(monkeypatch, tmp_path):
    """A frozen build ships no ``session_engine.py``; the exe re-enters itself."""
    import Programma_CS2_RENAN.core.config as config

    monkeypatch.setattr(config, "LOG_DIR", str(tmp_path))
    exe = tmp_path / "Macena_CS2_Analyzer.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    captured = _capture_popen(monkeypatch)
    mgr = AppLifecycleManager()
    mgr.project_root = tmp_path / "nowhere"  # no source tree at all
    try:
        assert mgr.launch_daemon() is not None
        assert captured["cmd"] == [str(exe), "--daemon"]
        assert captured["kwargs"]["cwd"] == str(tmp_path)
    finally:
        mgr._daemon_process = None
        mgr.shutdown()


def test_launch_daemon_dev_still_refuses_a_missing_source_tree(monkeypatch, tmp_path):
    import Programma_CS2_RENAN.core.config as config

    monkeypatch.setattr(config, "LOG_DIR", str(tmp_path))
    captured = _capture_popen(monkeypatch)
    mgr = AppLifecycleManager()
    mgr.project_root = tmp_path / "nowhere"
    assert mgr.launch_daemon() is None
    assert "cmd" not in captured


@pytest.mark.parametrize("flag", ["--daemon"])
def test_session_engine_entry_survives_module_invocation(flag):
    """``python -m Programma_CS2_RENAN.core.session_engine`` must import cleanly."""
    import importlib

    mod = importlib.import_module(_MODULE)
    assert callable(mod.run_session_loop)
