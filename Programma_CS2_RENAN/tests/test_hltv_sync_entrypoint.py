"""F-0014 regression: the detached spawn targets a REAL entry point, and
the dormant path RETRIES instead of exiting while promising a retry.

Pre-fix: start_detached launched the deleted Kivy-era main.py (child
died instantly, stderr DEVNULL, PID file recorded a corpse) and the
HLTV-unreachable branch slept 6 h then returned — service dead while
the WR-15 notification said 'Retrying in 6 hours'."""

import importlib.util
import sys
from unittest.mock import MagicMock, patch

import pytest

# NB: hltv_sync_service is imported INSIDE tests — the entry script
# self-inserts Programma_CS2_RENAN into sys.path (S5), which at collection
# time shadows the root `tools` namespace for later-collected root tests.


def _svc():
    from Programma_CS2_RENAN import hltv_sync_service

    return hltv_sync_service


def test_detached_spawn_targets_importable_module(tmp_path, monkeypatch):
    svc = _svc()
    monkeypatch.setattr(svc, "PID_FILE", tmp_path / "hltv_sync.pid")
    with patch.object(svc.subprocess, "Popen") as popen:
        popen.return_value.pid = 4242
        svc.start_detached()
    cmd = popen.call_args[0][0]
    assert cmd[0] == sys.executable
    assert cmd[1] == "-m"
    target = cmd[2]
    assert "main.py" not in " ".join(str(c) for c in cmd), "phantom entry is back"
    assert importlib.util.find_spec(target) is not None, f"{target} is not importable"


class _StopLoop(Exception):
    pass


def test_dormant_path_retries_connectivity(monkeypatch):
    svc = _svc()
    solver = MagicMock()
    solver.is_available.return_value = True
    # First connectivity probe fails -> dormant; second succeeds -> proceed.
    solver.get.side_effect = [None, "<html>stats</html>"]
    solver.create_session.side_effect = _StopLoop  # escape before the real loop

    sleeps = []
    monkeypatch.setattr(svc, "_dormant_sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(svc, "FlareSolverrClient", lambda: solver)
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.data_sources.hltv.docker_manager.ensure_flaresolverr",
        lambda root: True,
    )
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.storage.state_manager.get_state_manager",
        lambda: MagicMock(),
    )

    with pytest.raises(_StopLoop):
        svc.run_sync_loop()

    assert len(sleeps) == 1, "dormant sleep must have happened once"
    assert solver.get.call_count == 2, "connectivity must be RE-tested after dormancy"
