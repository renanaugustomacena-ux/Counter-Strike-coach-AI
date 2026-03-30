import threading
from contextlib import contextmanager
from typing import Any, Generator, Type, TypeVar

import sqlalchemy
from sqlalchemy import Pool, event
from sqlmodel import Session, SQLModel, create_engine, select

from Programma_CS2_RENAN.core.config import DATABASE_URL, HLTV_DATABASE_URL
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.database")

from .db_models import (
    CalibrationSnapshot,
    CoachingExperience,
    CoachingInsight,
    CoachState,
    DataLineage,
    DataQualityMetric,
    Ext_PlayerPlaystyle,
    Ext_TeamRoundStats,
    IngestionTask,
    MapVeto,
    MatchResult,
    PlayerMatchStats,
    PlayerProfile,
    PlayerTickState,
    ProPlayer,
    ProPlayerStatCard,
    ProTeam,
    RoleThresholdRecord,
    RoundStats,
    ServiceNotification,
    TacticalKnowledge,
)

# All tables that belong exclusively to the monolith database (database.db).
# Keeping this explicit list prevents per-match tables (MatchTickState, MatchEventState,
# MatchMetadata from match_data_manager.py) from leaking into the monolith if their
# modules are imported before create_db_and_tables() is called.
_MONOLITH_TABLES = [
    CalibrationSnapshot.__table__,
    CoachingExperience.__table__,
    CoachingInsight.__table__,
    CoachState.__table__,
    DataLineage.__table__,
    DataQualityMetric.__table__,
    Ext_PlayerPlaystyle.__table__,
    Ext_TeamRoundStats.__table__,
    IngestionTask.__table__,
    MapVeto.__table__,
    MatchResult.__table__,
    PlayerMatchStats.__table__,
    PlayerProfile.__table__,
    PlayerTickState.__table__,
    RoleThresholdRecord.__table__,
    RoundStats.__table__,
    ServiceNotification.__table__,
    TacticalKnowledge.__table__,
]

# Tables that belong exclusively to the HLTV metadata database (hltv_metadata.db).
# Separated from the monolith to eliminate write lock contention between
# the HLTV background service (separate process) and session_engine daemons.
_HLTV_TABLES = [
    ProPlayer.__table__,
    ProPlayerStatCard.__table__,
    ProTeam.__table__,
]

T = TypeVar("T", bound=SQLModel)


class DatabaseManager:
    """
    Industrial-Grade Monolithic Database Manager.
    Enforces Single-Source-of-Truth (database.db) with WAL Concurrency.
    """

    def __init__(self):
        # Industrial Configuration:
        # 1. check_same_thread=False: Allows multiple threads (Daemons + UI) to use the connection
        # 2. timeout=30: Busy timeout for WAL contention
        # 3. pool_size=1: SQLite single-writer safety (comment was stale "pool_size=20")
        self.engine = create_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False, "timeout": 30},
            pool_size=1,
            max_overflow=4,
        )

        # Force WAL Mode on every connection check-out
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")  # 30s wait
            cursor.close()

    def _get_engine(self):
        """One Engine to Rule Them All."""
        return self.engine

    def create_db_and_tables(self):
        """Creates schema in the Monolith, adding missing columns to existing tables."""
        try:
            SQLModel.metadata.create_all(self.engine, tables=_MONOLITH_TABLES)
            self._add_missing_columns()
        except Exception as e:
            logger.critical("Failed to initialize database schema: %s", e, exc_info=True)
            raise

    def _add_missing_columns(self):
        """Add columns that exist in the ORM model but not in the database.

        SQLAlchemy's create_all() only creates missing TABLES, not missing columns.
        This handles schema evolution for databases created with older code.
        """
        from sqlalchemy import inspect as sa_inspect, text

        inspector = sa_inspect(self.engine)
        existing_tables = inspector.get_table_names()

        for table in _MONOLITH_TABLES:
            if table.name not in existing_tables:
                continue

            db_cols = {c["name"] for c in inspector.get_columns(table.name)}
            model_cols = {c.name for c in table.columns}
            missing = model_cols - db_cols

            if not missing:
                continue

            with self.engine.connect() as conn:
                for col_name in missing:
                    col = table.columns[col_name]
                    col_type = col.type.compile(self.engine.dialect)
                    # Only use simple scalar defaults — skip callables/server defaults
                    default = ""
                    if col.default is not None and col.default.arg is not None:
                        arg = col.default.arg
                        if isinstance(arg, (int, float, str, bool)):
                            default = f" DEFAULT {arg!r}"
                    elif not col.nullable:
                        default = " DEFAULT ''"

                    sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{col_name}" {col_type}{default}'
                    try:
                        conn.execute(text(sql))
                        logger.info("Schema: added column %s.%s (%s)", table.name, col_name, col_type)
                    except Exception as e:
                        if "duplicate column" in str(e).lower():
                            pass
                        else:
                            logger.warning("Schema: failed to add %s.%s: %s", table.name, col_name, e)
                conn.commit()

    @contextmanager
    def get_session(self, engine_key: str = "default") -> Generator[Session, None, None]:
        """
        Provides a transactional scope.
        'engine_key' argument is deprecated but kept for compatibility.
        """
        with Session(self.engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                # DB-02: Expire all cached instances after rollback so callers
                # never see stale attribute values from a failed transaction.
                session.expire_all()
                raise

    def upsert(self, model_instance: T) -> T:
        """Atomic upsert."""
        # Special handling for PlayerMatchStats to maintain legacy logic
        if isinstance(model_instance, PlayerMatchStats):
            return self._upsert_player_stats(model_instance)

        with self.get_session() as session:
            return session.merge(model_instance)

    def _upsert_player_stats(self, model_instance) -> Any:
        """Upsert PlayerMatchStats using INSERT ... ON CONFLICT DO UPDATE.

        Uses SQLite's native conflict resolution instead of SELECT-then-INSERT
        to eliminate the TOCTOU race condition under concurrent daemon access.
        """
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        data = model_instance.model_dump(exclude_unset=True)
        # Remove 'id' — let DB auto-assign on INSERT, preserve existing on UPDATE
        data.pop("id", None)

        with self.get_session() as session:
            stmt = sqlite_insert(PlayerMatchStats).values(**data)
            # On conflict (demo_name, player_name), update all provided columns
            update_cols = {
                k: stmt.excluded[k] for k in data if k not in ("demo_name", "player_name")
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=["demo_name", "player_name"],
                set_=update_cols,
            )
            session.execute(stmt)
            session.flush()

            # Return the persisted instance
            result = session.exec(
                select(PlayerMatchStats).where(
                    PlayerMatchStats.demo_name == model_instance.demo_name,
                    PlayerMatchStats.player_name == model_instance.player_name,
                )
            ).first()
            return result

    def get(self, model_class: Type[T], pk: Any) -> T | None:
        """Retrieves a record."""
        with self.get_session() as session:
            return session.get(model_class, pk)

    def delete_match_cascade(self, match_id: int, demo_name: str) -> dict:
        """P5-A: Delete all data associated with a match across all stores.

        FK-safe deletion order: children first, then parent.

        Returns:
            dict with keys: tables_cleared (list[str]), files_deleted (int)
        """
        result = {"tables_cleared": [], "files_deleted": 0}

        with self.get_session() as session:
            # Child tables (FK → MatchResult or demo_name reference)
            for model, col, val in [
                (MapVeto, MapVeto.match_id, match_id),
                (CoachingExperience, CoachingExperience.pro_match_id, match_id),
                (PlayerTickState, PlayerTickState.demo_name, demo_name),
                (RoundStats, RoundStats.demo_name, demo_name),
                (PlayerMatchStats, PlayerMatchStats.demo_name, demo_name),
                (CoachingInsight, CoachingInsight.demo_name, demo_name),
            ]:
                deleted = session.query(model).filter(col == val).delete(synchronize_session=False)
                if deleted:
                    result["tables_cleared"].append(f"{model.__tablename__}({deleted})")

            # Parent table
            deleted = (
                session.query(MatchResult)
                .filter(MatchResult.match_id == match_id)
                .delete(synchronize_session=False)
            )
            if deleted:
                result["tables_cleared"].append(f"matchresult({deleted})")

        # Delete per-match DB file
        try:
            from Programma_CS2_RENAN.backend.storage.match_data_manager import (
                get_match_data_manager,
            )

            mdm = get_match_data_manager()
            if mdm.delete_match(match_id):
                result["files_deleted"] += 1
        except Exception as e:
            logger.warning("P5-A: Could not delete match DB file for %s: %s", match_id, e)

        logger.info("P5-A: Cascade delete match %s (%s): %s", match_id, demo_name, result)
        return result

    @staticmethod
    def detect_orphans() -> dict:
        """P5-B: Detect orphan match DBs without corresponding MatchResult.

        Returns:
            dict with keys: orphan_match_ids (list[int]), orphan_count (int)
        """
        try:
            from Programma_CS2_RENAN.backend.storage.match_data_manager import (
                get_match_data_manager,
            )

            mdm = get_match_data_manager()
            file_match_ids = set(mdm.list_available_matches())

            db = get_db_manager()
            with db.get_session() as session:
                db_match_ids = set(
                    row[0] for row in session.exec(select(MatchResult.match_id)).all()
                )

            orphans = sorted(file_match_ids - db_match_ids)
            if orphans:
                logger.warning(
                    "P5-B: Found %d orphan match DB files without MatchResult: %s",
                    len(orphans),
                    orphans[:10],
                )
            return {"orphan_match_ids": orphans, "orphan_count": len(orphans)}
        except Exception as e:
            logger.error("P5-B: Orphan detection failed: %s", e)
            return {"orphan_match_ids": [], "orphan_count": 0}


# Lazy singleton — avoids import-time engine creation
_db_manager = None
_db_manager_lock = threading.Lock()


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        with _db_manager_lock:
            # Double-checked locking: re-test inside the lock to prevent two threads
            # from each creating a DatabaseManager (and two SQLAlchemy engines).
            if _db_manager is None:
                _db_manager = DatabaseManager()
    return _db_manager


class HLTVDatabaseManager:
    """
    Dedicated Database Manager for HLTV metadata (hltv_metadata.db).

    Eliminates write lock contention between the HLTV background service
    (long-running scrape operations in a separate process) and the
    session_engine daemons (Scanner, Digester, Teacher) on the monolith.
    """

    def __init__(self):
        self.engine = create_engine(
            HLTV_DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False, "timeout": 30},
            pool_size=1,
            max_overflow=4,
        )

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    def create_db_and_tables(self):
        """Creates schema in the HLTV metadata database.

        Handles pre-existing hltv_metadata.db files with stale schemas by
        dropping and recreating tables whose columns don't match the model.
        """
        try:
            self._reconcile_stale_schema()
            SQLModel.metadata.create_all(self.engine, tables=_HLTV_TABLES)
        except Exception as e:
            logger.critical("Failed to initialize HLTV database schema: %s", e, exc_info=True)
            raise

    def _reconcile_stale_schema(self):
        """Drop HLTV tables whose column set doesn't match the current model."""
        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(self.engine)
        existing_tables = inspector.get_table_names()

        for table in _HLTV_TABLES:
            tbl_name = table.name
            if tbl_name not in existing_tables:
                continue

            db_cols = {c["name"] for c in inspector.get_columns(tbl_name)}
            model_cols = {c.name for c in table.columns}

            if not model_cols.issubset(db_cols):
                missing = model_cols - db_cols
                logger.warning(
                    "HLTV table '%s' missing columns %s — recreating with current schema.",
                    tbl_name,
                    missing,
                )
                table.drop(self.engine, checkfirst=True)
        # Also drop tables that don't belong in the HLTV database
        hltv_table_names = {t.name for t in _HLTV_TABLES}
        import re as _re

        _SAFE_TABLE_NAME = _re.compile(r"^[a-zA-Z0-9_]+$")
        for orphan in set(existing_tables) - hltv_table_names:
            if orphan in ("sqlite_sequence",):
                continue
            # P7-04: Validate table name before using in SQL to prevent injection
            if not _SAFE_TABLE_NAME.match(orphan):
                logger.error("Invalid table name in HLTV reconciliation: %s — skipped", orphan)
                continue
            logger.info("Dropping orphan table '%s' from HLTV database.", orphan)
            with self.engine.connect() as conn:
                conn.execute(sqlalchemy.text(f'DROP TABLE IF EXISTS "{orphan}"'))
                conn.commit()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provides a transactional scope for HLTV data."""
        with Session(self.engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                session.expire_all()
                raise

    def upsert(self, model_instance: T) -> T:
        """Atomic upsert for HLTV models."""
        with self.get_session() as session:
            return session.merge(model_instance)


_hltv_db_manager = None
_hltv_db_manager_lock = threading.Lock()


def get_hltv_db_manager() -> HLTVDatabaseManager:
    global _hltv_db_manager
    if _hltv_db_manager is None:
        with _hltv_db_manager_lock:
            if _hltv_db_manager is None:
                _hltv_db_manager = HLTVDatabaseManager()
    return _hltv_db_manager


def init_database():
    get_db_manager().create_db_and_tables()
    get_hltv_db_manager().create_db_and_tables()
