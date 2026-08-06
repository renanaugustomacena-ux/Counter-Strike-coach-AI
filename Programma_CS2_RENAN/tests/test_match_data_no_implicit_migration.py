"""Constructing a MatchDataManager must never relocate shard data.

2026-07-26: get_match_data_manager() ran a "one-time migration" that
shutil.move()d every match_*.db from the in-project directory to whatever
MATCH_DATA_PATH currently resolved to. The trigger was a path comparison, not
a persisted marker, so it re-armed in every process whose config differed —
and PRO_DEMO_PATH defaulted to $HOME, which always exists. Running the test
suite therefore relocated the production shard corpus twice in one afternoon:
45 shards off the external volume (ENOSPC mid-move killed that run), then 313
shards off /data, taking the root disk from 42 GB to 2 GB free.

Relocation is now explicit — migrate_match_data() still works, but nothing
calls it implicitly.
"""

import os

import pytest

from Programma_CS2_RENAN.backend.storage import match_data_manager as mdm


def _seed_shards(directory, count):
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    for i in range(count):
        name = f"match_{1000 + i}.db"
        (directory / name).write_bytes(b"sqlite-ish payload")
        names.append(name)
    return names


@pytest.fixture
def legacy_dir(tmp_path, monkeypatch):
    """Point the legacy-location probe at a temp dir, never the real repo."""
    legacy = tmp_path / "legacy_match_data"
    legacy.mkdir()
    monkeypatch.setattr(mdm, "legacy_in_project_match_data_dir", lambda: str(legacy))
    return legacy


class TestNoImplicitMigration:
    def test_construction_never_invokes_migration(self, tmp_path, monkeypatch):
        """The invariant, stated without reference to any directory layout.

        Deliberately does NOT patch the legacy-location probe, so it reads the
        real in-project directory and would have caught the original defect on
        a working checkout. Spying rather than asserting on files means nothing
        is at risk if the guarantee is ever broken again.
        """
        calls = []
        monkeypatch.setattr(mdm, "migrate_match_data", lambda *a, **k: calls.append((a, k)) or {})
        monkeypatch.setattr(mdm, "_match_data_manager", None)
        active = tmp_path / "somewhere_else"
        active.mkdir()

        mdm.get_match_data_manager(str(active))

        assert calls == [], f"construction moved data: migrate_match_data{calls[0][0]}"

    def test_manager_construction_does_not_move_shards(self, tmp_path, legacy_dir, monkeypatch):
        names = _seed_shards(legacy_dir, 5)
        active = tmp_path / "active_match_data"
        active.mkdir()
        monkeypatch.setattr(mdm, "_match_data_manager", None)

        mdm.get_match_data_manager(str(active))

        assert sorted(os.listdir(legacy_dir)) == sorted(names), "shards were moved out"
        assert os.listdir(active) == [], "shards were moved in"

    def test_stale_location_is_reported(self, tmp_path, legacy_dir, caplog):
        _seed_shards(legacy_dir, 3)
        active = tmp_path / "active_match_data"
        active.mkdir()

        with caplog.at_level("WARNING"):
            found = mdm.warn_if_shards_in_legacy_location(str(active))

        assert found == 3
        assert "will NOT be moved automatically" in caplog.text

    def test_active_equals_legacy_is_not_reported(self, legacy_dir, caplog):
        _seed_shards(legacy_dir, 2)
        with caplog.at_level("WARNING"):
            assert mdm.warn_if_shards_in_legacy_location(str(legacy_dir)) == 0
        assert "will NOT be moved" not in caplog.text

    def test_empty_legacy_dir_is_silent(self, tmp_path, legacy_dir, caplog):
        active = tmp_path / "active_match_data"
        active.mkdir()
        with caplog.at_level("WARNING"):
            assert mdm.warn_if_shards_in_legacy_location(str(active)) == 0
        assert caplog.text == ""

    def test_missing_legacy_dir_is_silent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            mdm, "legacy_in_project_match_data_dir", lambda: str(tmp_path / "does_not_exist")
        )
        assert mdm.warn_if_shards_in_legacy_location(str(tmp_path)) == 0


class TestExplicitMigrationStillWorks:
    """The capability is retained — only the implicit invocation is gone."""

    def test_migrate_match_data_moves_when_called_directly(self, tmp_path, monkeypatch):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        names = _seed_shards(src, 4)
        monkeypatch.setattr(mdm, "_match_data_manager", None)

        result = mdm.migrate_match_data(str(src), str(dst))

        assert result["moved"] == 4
        assert not result["errors"]
        assert sorted(os.listdir(dst)) == sorted(names)

    def test_migration_skips_files_already_at_destination(self, tmp_path, monkeypatch):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        _seed_shards(src, 3)
        dst.mkdir()
        (dst / "match_1000.db").write_bytes(b"newer payload at destination")
        monkeypatch.setattr(mdm, "_match_data_manager", None)

        result = mdm.migrate_match_data(str(src), str(dst))

        assert result["skipped"] == 1
        assert result["moved"] == 2
        assert (dst / "match_1000.db").read_bytes() == b"newer payload at destination"
