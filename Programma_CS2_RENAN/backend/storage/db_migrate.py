"""
Database Migration Utility for Macena CS2 Analyzer.

Provides programmatic access to Alembic migrations for auto-upgrade
on application startup (TASK 2.20.1).
"""

import os
import sys
from pathlib import Path

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.db_migrate")


def _alembic_paths() -> tuple[str, str]:
    """``(alembic.ini, alembic/)`` -- the repo root in a checkout, the bundle
    root (``_MEIPASS``) in a frozen build (WP4a: never the install directory
    joined with the package dir, which exists in neither layout).
    """
    if getattr(sys, "frozen", False):
        root = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        root = str(Path(__file__).resolve().parents[3])
    return os.path.join(root, "alembic.ini"), os.path.join(root, "alembic")


def ensure_database_current() -> bool:
    """
    Automatically upgrade the database to the latest schema version.

    This should be called early in the startup sequence, after path
    stabilization but before heavy imports or UI initialization.

    Returns:
        True if migration succeeded or was not needed, False on error.
    """
    try:
        from sqlalchemy import create_engine

        from alembic import command
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from Programma_CS2_RENAN.core.config import DATABASE_URL

        # Locate alembic.ini
        alembic_ini, alembic_scripts = _alembic_paths()
        if not os.path.exists(alembic_ini):
            logger.warning("alembic.ini not found at %s. Skipping migration.", alembic_ini)
            return True  # Not an error - development may not have alembic

        # Create Alembic config
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        alembic_cfg.set_main_option("script_location", alembic_scripts)

        # Check current vs target revision
        engine = create_engine(DATABASE_URL)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
        finally:
            # R4 LOW: release the pool/file handle (was never disposed).
            engine.dispose()

        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()

        if current_rev == head_rev:
            logger.debug("Database is current (revision: %s)", current_rev)
            return True

        # Upgrade needed
        logger.info("Upgrading database: %s -> %s", current_rev, head_rev)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migration completed successfully")
        return True

    except ImportError as e:
        # Alembic not installed - this is OK in frozen builds
        logger.debug("Alembic not available: %s", e)
        return True

    except Exception as e:
        logger.error("Database migration failed: %s", e)
        # In development, log full traceback
        if not getattr(sys, "frozen", False):
            import traceback

            logger.error(traceback.format_exc())
        return False


def get_current_revision() -> str | None:
    """Get the current database schema revision."""
    try:
        from sqlalchemy import create_engine

        from alembic.runtime.migration import MigrationContext
        from Programma_CS2_RENAN.core.config import DATABASE_URL

        engine = create_engine(DATABASE_URL)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()
        finally:
            engine.dispose()
    except Exception:
        logger.debug("Could not retrieve current DB revision", exc_info=True)
        return None


def get_head_revision() -> str | None:
    """Get the target (head) schema revision."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        alembic_ini, alembic_scripts = _alembic_paths()
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("script_location", alembic_scripts)

        script = ScriptDirectory.from_config(alembic_cfg)
        return script.get_current_head()
    except Exception:
        logger.debug("Could not retrieve head revision", exc_info=True)
        return None
