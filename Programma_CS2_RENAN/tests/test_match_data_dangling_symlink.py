"""A dangling match_data symlink must fail loudly, not self-repair.

2026-07-26: MatchDataManager.__init__ detected a broken symlink, os.unlink'd it
and created an empty real directory in its place (AUDIT §8.8, whose actual
concern was only that os.makedirs(exist_ok=True) raises FileExistsError on a
dangling link). The side effect was severe: on another machine, or with a USB
drive simply unplugged, the app started with zero shards and no error — and the
symlink, the only record of where the data lived, was gone. Returning to the
original machine then required recreating it by hand.

A dangling symlink is positive evidence that storage was configured and is
currently unreachable. That is an error, not a prompt to invent empty storage.
A path that is merely absent is still the normal fresh-install case and is
still created.
"""

import os

import pytest

from Programma_CS2_RENAN.backend.storage import match_data_manager as mdm
from Programma_CS2_RENAN.backend.storage.match_data_manager import (
    MatchDataManager,
    MatchDataUnavailableError,
)


@pytest.fixture
def dangling_link(tmp_path):
    """A match_data symlink whose target does not exist."""
    dead_target = tmp_path / "unplugged_drive" / "match_data"
    link = tmp_path / "match_data"
    link.symlink_to(dead_target)
    assert os.path.islink(link) and not os.path.exists(link)
    return link, dead_target


class TestDanglingSymlinkIsAnError:
    def test_construction_raises(self, dangling_link):
        link, _ = dangling_link
        with pytest.raises(MatchDataUnavailableError):
            MatchDataManager(str(link))

    def test_symlink_survives(self, dangling_link):
        """The regression that matters: the pointer must not be destroyed."""
        link, dead_target = dangling_link
        with pytest.raises(MatchDataUnavailableError):
            MatchDataManager(str(link))
        assert os.path.islink(link), "the symlink was deleted"
        assert os.readlink(link) == str(dead_target), "the symlink was repointed"

    def test_no_empty_directory_is_invented(self, dangling_link):
        link, _ = dangling_link
        with pytest.raises(MatchDataUnavailableError):
            MatchDataManager(str(link))
        assert not os.path.isdir(link), "an empty directory replaced the link"

    def test_message_names_link_and_dead_target(self, dangling_link):
        link, dead_target = dangling_link
        with pytest.raises(MatchDataUnavailableError) as excinfo:
            MatchDataManager(str(link))
        message = str(excinfo.value)
        assert str(link) in message
        assert str(dead_target) in message

    def test_singleton_factory_propagates_and_caches_nothing(self, dangling_link, monkeypatch):
        link, _ = dangling_link
        monkeypatch.setattr(mdm, "_match_data_manager", None)
        with pytest.raises(MatchDataUnavailableError):
            mdm.get_match_data_manager(str(link))
        assert mdm._match_data_manager is None, "a broken manager was cached"


class TestReachableLocationsStillWork:
    def test_absent_directory_is_created(self, tmp_path):
        """Fresh install: nothing there at all is not an error."""
        target = tmp_path / "match_data"
        MatchDataManager(str(target))
        assert target.is_dir()

    def test_existing_directory_is_used(self, tmp_path):
        target = tmp_path / "match_data"
        target.mkdir()
        (target / "match_1.db").write_bytes(b"payload")
        MatchDataManager(str(target))
        assert (target / "match_1.db").exists()

    def test_live_symlink_is_followed(self, tmp_path):
        """The normal relocated-storage setup must be untouched."""
        real = tmp_path / "elsewhere" / "match_data"
        real.mkdir(parents=True)
        (real / "match_1.db").write_bytes(b"payload")
        link = tmp_path / "match_data"
        link.symlink_to(real)

        manager = MatchDataManager(str(link))

        assert manager.match_data_path == str(link)
        assert os.path.islink(link)
        assert (real / "match_1.db").exists()
