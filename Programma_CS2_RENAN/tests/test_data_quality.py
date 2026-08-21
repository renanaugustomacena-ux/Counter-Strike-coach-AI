"""OI-1 regression tests for backend.nn.data_quality.

The match-completeness enumeration used to sit inside ONE try/except: the
first shard whose metadata read raised aborted the whole loop at iteration 0,
the failure was logged at DEBUG, and the report printed
"Complete matches: 0, Incomplete: 0" while still saying PASS.
"""

import logging
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from Programma_CS2_RENAN.backend.nn.data_quality import run_pre_training_quality_check


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def one(self):
        return self._value


class _FakeSession:
    """Returns canned counts for the four count queries the check runs."""

    def __init__(self):
        self.calls = 0

    def exec(self, _query):
        self.calls += 1
        if self.calls == 1:
            return _FakeResult(5000)  # total tick rows
        if self.calls in (2, 3, 4):
            return _FakeResult(100)  # train/val/test split counts
        return _FakeResult(0)  # zero-position count


class _FakeDB:
    def __init__(self):
        self._session = _FakeSession()

    @contextmanager
    def get_session(self):
        yield self._session


class _FakeMDM:
    """Three matches: the FIRST raises, the second is complete, third not."""

    def list_available_matches(self):
        return [101, 102, 103]

    def get_metadata(self, mid):
        if mid == 101:
            raise OSError("simulated unreadable shard")
        if mid == 102:
            return SimpleNamespace(match_complete=True)
        return SimpleNamespace(match_complete=False)


@pytest.fixture
def patched_backends(monkeypatch):
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.storage.database.get_db_manager",
        lambda: _FakeDB(),
    )
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.storage.match_data_manager.get_match_data_manager",
        lambda: _FakeMDM(),
    )


class TestPerItemCompletenessEnumeration:
    def test_one_bad_shard_does_not_abort_the_loop(self, patched_backends):
        report = run_pre_training_quality_check()
        # 102 is complete; 101 (unreadable) and 103 count as incomplete.
        assert report.complete_matches == 1
        assert report.incomplete_matches == 2

    def test_bad_shard_is_logged_at_warning(self, patched_backends, caplog):
        with caplog.at_level(logging.WARNING, logger="cs2analyzer.nn.data_quality"):
            run_pre_training_quality_check()
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("101" in r.getMessage() for r in warnings)

    def test_report_still_passes_on_good_data(self, patched_backends):
        report = run_pre_training_quality_check()
        assert report.passed is True
