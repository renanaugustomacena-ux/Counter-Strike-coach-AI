"""
DEPRECATED — This migration chain is NOT active.

The canonical Alembic configuration lives at:
    <project_root>/alembic/env.py  (referenced by <project_root>/alembic.ini)

This file is retained only to prevent accidental re-creation.
Running alembic against this directory will raise RuntimeError.
"""

raise RuntimeError(
    "DEPRECATED: This migration env.py is not the active chain. "
    "Use the canonical 'alembic/' directory at the project root instead. "
    "See alembic.ini → script_location = alembic"
)
