"""
R2-01 DEPRECATION NOTICE
=========================
This is a LEGACY migration directory. The authoritative Alembic migration
chain lives at the repository root: ``alembic/`` (13+ migrations).

ALL new migrations MUST be created in the root ``alembic/`` directory:
    alembic revision --autogenerate -m "description"

Do NOT add new migrations here. This directory is retained only for
historical reference (baseline_schema + add_rating_components).
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import os

# IMPORTS FOR ALEMBIC
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from sqlmodel import SQLModel

from Programma_CS2_RENAN.backend.storage.db_models import *

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    R2-01: DEPRECATED — this migration chain is superseded by the root
    ``alembic/`` directory. Raising to prevent accidental execution.
    """
    raise RuntimeError(
        "DEPRECATED: This legacy migration chain (backend/storage/migrations/) "
        "is no longer active. Use the canonical chain at the project root: "
        "  cd <project_root> && alembic upgrade head"
    )


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    R2-01: DEPRECATED — this migration chain is superseded by the root
    ``alembic/`` directory. Raising to prevent accidental execution.
    """
    raise RuntimeError(
        "DEPRECATED: This legacy migration chain (backend/storage/migrations/) "
        "is no longer active. Use the canonical chain at the project root: "
        "  cd <project_root> && alembic upgrade head"
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
