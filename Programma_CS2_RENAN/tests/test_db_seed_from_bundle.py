"""Install round (WP4a) — the bundled HLTV metadata database seeds the user's
db folder on first boot; an existing user copy is never overwritten.
"""

from __future__ import annotations

from unittest.mock import MagicMock


def test_seed_copies_the_bundle_only_when_the_target_is_absent(tmp_path):
    from Programma_CS2_RENAN.backend.storage import database

    seed = tmp_path / "bundle" / "hltv_metadata.db"
    seed.parent.mkdir()
    seed.write_bytes(b"seed")
    target = tmp_path / "db" / "hltv_metadata.db"

    assert database.seed_hltv_metadata_if_absent(target, seed) is True
    assert target.read_bytes() == b"seed"

    target.write_bytes(b"mine")
    assert database.seed_hltv_metadata_if_absent(target, seed) is False
    assert target.read_bytes() == b"mine"


def test_seed_is_a_noop_for_the_same_file_or_a_missing_bundle(tmp_path):
    from Programma_CS2_RENAN.backend.storage import database

    same = tmp_path / "hltv_metadata.db"
    same.write_bytes(b"x")
    assert database.seed_hltv_metadata_if_absent(same, same) is False
    assert same.read_bytes() == b"x"

    assert (
        database.seed_hltv_metadata_if_absent(tmp_path / "new.db", tmp_path / "missing.db") is False
    )
    assert not (tmp_path / "new.db").exists()


def test_init_database_seeds_before_creating_tables(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.backend.storage import database

    seed = tmp_path / "bundle" / "hltv_metadata.db"
    seed.parent.mkdir()
    seed.write_bytes(b"seed")
    target = tmp_path / "db" / "hltv_metadata.db"

    monkeypatch.setattr(database, "HLTV_DATABASE_URL", f"sqlite:///{target}")
    monkeypatch.setattr(database, "get_resource_path", lambda rel: str(seed))
    order: list[tuple[str, bool]] = []
    hltv = MagicMock()
    hltv.create_db_and_tables.side_effect = lambda: order.append(("tables", target.exists()))
    monkeypatch.setattr(database, "get_db_manager", lambda: MagicMock())
    monkeypatch.setattr(database, "get_hltv_db_manager", lambda: hltv)
    monkeypatch.setattr(database, "_restrict_db_permissions", lambda url: None)

    database.init_database()

    assert order == [("tables", True)]
    assert target.read_bytes() == b"seed"
