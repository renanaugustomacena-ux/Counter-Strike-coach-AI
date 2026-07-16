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
