"""HLTV table-registry contract (R4 CRIT finding, 2026-07-16).

``HLTVDatabaseManager._reconcile_stale_schema()`` DROPS any table found in
hltv_metadata.db that is not listed in ``_HLTV_TABLES`` (orphan cleanup).
When Phase H1 added four new Pro* models without updating that registry,
every startup destroyed the H1 tables and their scraped data. These tests
pin the registry to the model set so that class of bug cannot recur.
"""

import inspect

from sqlmodel import SQLModel, select

import Programma_CS2_RENAN.backend.storage.database as db_mod
import Programma_CS2_RENAN.backend.storage.db_models as models_mod
from Programma_CS2_RENAN.backend.storage.db_models import ProEvent


def _pro_model_table_names():
    """Every table=True SQLModel in db_models whose class name starts with Pro."""
    names = set()
    for name, obj in vars(models_mod).items():
        if not (inspect.isclass(obj) and issubclass(obj, SQLModel)):
            continue
        if not name.startswith("Pro"):
            continue
        table = getattr(obj, "__table__", None)
        if table is not None:
            names.add(table.name)
    return names


class TestHLTVTableRegistry:
    def test_every_pro_model_is_registered(self):
        """A Pro* model missing from _HLTV_TABLES gets dropped as an orphan."""
        registered = {t.name for t in db_mod._HLTV_TABLES}
        missing = _pro_model_table_names() - registered
        assert not missing, (
            f"Pro* tables not in _HLTV_TABLES — _reconcile_stale_schema() will "
            f"DROP them on next startup: {sorted(missing)}"
        )

    def test_h1_tables_present(self):
        """The four Phase-H1 tables are explicitly registered."""
        registered = {t.name for t in db_mod._HLTV_TABLES}
        for expected in ("proevent", "protournament", "prohead2head", "promaprecord"):
            assert expected in registered

    def test_no_overlap_with_monolith(self):
        """HLTV and monolith table sets must stay disjoint (DB separation)."""
        hltv = {t.name for t in db_mod._HLTV_TABLES}
        monolith = {t.name for t in db_mod._MONOLITH_TABLES}
        assert not (hltv & monolith)

    def test_second_startup_preserves_h1_data(self, tmp_path, monkeypatch):
        """Functional anti-data-loss probe: re-initialising the HLTV schema
        must NOT drop rows written into an H1 table by a prior run."""
        url = f"sqlite:///{(tmp_path / 'hltv_registry_probe.db').as_posix()}"
        monkeypatch.setattr(db_mod, "HLTV_DATABASE_URL", url)

        # Direct instantiation is deliberate: the get_hltv_db_manager()
        # singleton is bound to the real production DB path.
        mgr = db_mod.HLTVDatabaseManager()
        mgr.create_db_and_tables()

        with mgr.get_session() as s:
            s.add(
                ProEvent(
                    hltv_id=7907,
                    name="IEM Katowice 2026",
                    tier="S-Tier",
                    location="Katowice, Poland",
                )
            )

        # Second startup on the same file — this is where the orphan-drop
        # loop destroyed the H1 tables before the fix.
        mgr2 = db_mod.HLTVDatabaseManager()
        mgr2.create_db_and_tables()

        with mgr2.get_session() as s:
            survivors = s.exec(select(ProEvent).where(ProEvent.hltv_id == 7907)).all()
        assert len(survivors) == 1, "H1 row destroyed by schema reconciliation"


class TestProMapRecordUniqueness:
    """R4 MED: SQLite NULLs are distinct in UNIQUE indexes — the old
    3-column constraint never fired because the XOR check guarantees one
    subject column is always NULL. Partial unique indexes must reject
    duplicate (subject, map) rows."""

    def _mgr(self, tmp_path, monkeypatch):
        url = f"sqlite:///{(tmp_path / 'hltv_unique_probe.db').as_posix()}"
        monkeypatch.setattr(db_mod, "HLTV_DATABASE_URL", url)
        mgr = db_mod.HLTVDatabaseManager()
        mgr.create_db_and_tables()
        return mgr

    def test_duplicate_team_map_rejected(self, tmp_path, monkeypatch):
        import pytest as _pytest
        from sqlalchemy.exc import IntegrityError

        from Programma_CS2_RENAN.backend.storage.db_models import ProMapRecord

        mgr = self._mgr(tmp_path, monkeypatch)
        with mgr.get_session() as s:
            s.add(ProMapRecord(team_hltv_id=4608, map_name="de_mirage", maps_played=10))
        with _pytest.raises(IntegrityError):
            with mgr.get_session() as s:
                s.add(ProMapRecord(team_hltv_id=4608, map_name="de_mirage", maps_played=99))

    def test_same_map_different_subjects_allowed(self, tmp_path, monkeypatch):
        from Programma_CS2_RENAN.backend.storage.db_models import ProMapRecord

        mgr = self._mgr(tmp_path, monkeypatch)
        with mgr.get_session() as s:
            s.add(ProMapRecord(team_hltv_id=4608, map_name="de_inferno"))
            s.add(ProMapRecord(team_hltv_id=6667, map_name="de_inferno"))
            s.add(ProMapRecord(player_hltv_id=7998, map_name="de_inferno"))


class TestNonDestructiveReconciliation:
    """#47/GAP-14 hardening: schema drift must never silently destroy rows."""

    def _mgr(self, tmp_path, monkeypatch, name="hltv_reconcile_probe.db"):
        url = f"sqlite:///{(tmp_path / name).as_posix()}"
        monkeypatch.setattr(db_mod, "HLTV_DATABASE_URL", url)
        mgr = db_mod.HLTVDatabaseManager()
        mgr.create_db_and_tables()
        return mgr

    def _raw(self, mgr, sql):
        import sqlalchemy

        with mgr.engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(sql))
            conn.commit()
            return result

    def test_additive_drift_adds_column_in_place(self, tmp_path, monkeypatch):
        mgr = self._mgr(tmp_path, monkeypatch)
        with mgr.get_session() as s:
            s.add(ProEvent(hltv_id=1001, name="BLAST Fall 2026", tier="S-Tier"))
        # Simulate an OLDER schema: the DB lacks a column the model has.
        self._raw(mgr, 'ALTER TABLE "proevent" DROP COLUMN "tier"')

        mgr2 = db_mod.HLTVDatabaseManager()
        mgr2.create_db_and_tables()

        with mgr2.get_session() as s:
            survivors = s.exec(select(ProEvent).where(ProEvent.hltv_id == 1001)).all()
        assert len(survivors) == 1, "additive drift must preserve rows"
        assert survivors[0].tier is None  # re-added column, honest NULL

    def test_non_additive_drift_preserves_stale_snapshot(self, tmp_path, monkeypatch):
        import sqlalchemy

        mgr = self._mgr(tmp_path, monkeypatch, name="hltv_nonadditive_probe.db")
        with mgr.get_session() as s:
            s.add(ProEvent(hltv_id=2002, name="IEM Cologne 2026", tier="S-Tier"))
        # Simulate incompatible drift: model column gone AND foreign column present.
        self._raw(mgr, 'ALTER TABLE "proevent" DROP COLUMN "tier"')
        self._raw(mgr, 'ALTER TABLE "proevent" ADD COLUMN "legacy_junk" TEXT')

        mgr2 = db_mod.HLTVDatabaseManager()
        mgr2.create_db_and_tables()

        with mgr2.engine.connect() as conn:
            tables = [
                r[0]
                for r in conn.execute(
                    sqlalchemy.text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            ]
        stale = [t for t in tables if t.startswith("proevent_stale_")]
        assert len(stale) == 1, f"expected preserved snapshot, tables={tables}"
        with mgr2.engine.connect() as conn:
            count = conn.execute(sqlalchemy.text(f'SELECT COUNT(*) FROM "{stale[0]}"')).scalar()
        assert count == 1, "snapshot must keep the old rows"

        # Fresh table exists and is empty.
        with mgr2.get_session() as s:
            assert s.exec(select(ProEvent).where(ProEvent.hltv_id == 2002)).all() == []

        # A third startup must NOT purge the stale snapshot as an orphan.
        mgr3 = db_mod.HLTVDatabaseManager()
        mgr3.create_db_and_tables()
        with mgr3.engine.connect() as conn:
            tables3 = [
                r[0]
                for r in conn.execute(
                    sqlalchemy.text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            ]
        assert stale[0] in tables3, "stale snapshot must survive orphan purge"

    def test_true_orphans_still_dropped(self, tmp_path, monkeypatch):
        import sqlalchemy

        mgr = self._mgr(tmp_path, monkeypatch, name="hltv_orphan_probe.db")
        self._raw(mgr, 'CREATE TABLE "junk_table" (id INTEGER)')

        mgr2 = db_mod.HLTVDatabaseManager()
        mgr2.create_db_and_tables()

        with mgr2.engine.connect() as conn:
            tables = [
                r[0]
                for r in conn.execute(
                    sqlalchemy.text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            ]
        assert "junk_table" not in tables
