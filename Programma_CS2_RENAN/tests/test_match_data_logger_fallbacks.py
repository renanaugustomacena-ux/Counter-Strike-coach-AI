"""F-0012 regression: the fallback branches of _default_window_ticks must
WARN and return the 64 tick/s window — the module defines only `_logger`,
and the old bare `logger.warning(...)` raised NameError from exactly the
paths meant to keep RAP/POV window fetching alive on sparse metadata."""

from unittest.mock import MagicMock

from Programma_CS2_RENAN.backend.storage.match_data_manager import MatchDataManager


def _shell() -> MatchDataManager:
    return MatchDataManager.__new__(MatchDataManager)


def test_invalid_tick_rate_warns_and_falls_back():
    mgr = _shell()
    mgr.get_metadata = MagicMock(return_value=MagicMock(tick_rate=0))
    assert mgr._default_window_ticks(1) == int(mgr.MEMORY_WINDOW_SECONDS * 64)


def test_metadata_lookup_failure_warns_and_falls_back():
    mgr = _shell()
    mgr.get_metadata = MagicMock(side_effect=RuntimeError("shard gone"))
    assert mgr._default_window_ticks(2) == int(mgr.MEMORY_WINDOW_SECONDS * 64)


def test_valid_rate_used_directly():
    mgr = _shell()
    mgr.get_metadata = MagicMock(return_value=MagicMock(tick_rate=128))
    assert mgr._default_window_ticks(3) == int(mgr.MEMORY_WINDOW_SECONDS * 128)
