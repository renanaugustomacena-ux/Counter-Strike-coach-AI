"""
Smoke tests for Macena CS2 Analyzer automated suite.

Verify that core modules import, critical classes expose expected interfaces,
and foundational services (DB, config, localization) initialize correctly.
"""

import os
import sys

import pytest

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_imports():
    """Core modules import and expose expected interfaces."""
    import pandas  # noqa: F401
    import torch

    from Programma_CS2_RENAN.backend.nn.model import TeacherRefinementNN
    from Programma_CS2_RENAN.backend.storage.database import init_database
    from Programma_CS2_RENAN.core.localization import i18n

    # TeacherRefinementNN must have a callable forward method
    assert hasattr(TeacherRefinementNN, "forward")
    assert callable(getattr(TeacherRefinementNN, "forward"))

    # init_database must be callable
    assert callable(init_database)

    # i18n must support get_text and set_language
    assert callable(getattr(i18n, "get_text", None))
    assert callable(getattr(i18n, "set_language", None))

    # torch must provide tensor operations
    t = torch.zeros(1)
    assert t.shape == (1,)


def test_database_init():
    """Database initializes and returns a functional manager."""
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database

    init_database()
    db = get_db_manager()
    assert db is not None

    # Manager must provide get_session context manager
    assert hasattr(db, "get_session")
    with db.get_session() as session:
        # Verify schema exists — at least one table queryable
        result = session.execute(
            __import__("sqlalchemy").text(
                "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
            )
        ).fetchone()
        assert result is not None, "No tables found after init_database()"


def test_config_loading():
    """Config system loads and returns expected types."""
    # METADATA_DIM is critical — must be 25
    from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import METADATA_DIM
    from Programma_CS2_RENAN.core.config import get_setting

    assert METADATA_DIM == 25

    # get_setting must return a value for known keys
    player_name = get_setting("CS2_PLAYER_NAME")
    assert isinstance(player_name, str)


def test_model_factory_types():
    """ModelFactory exposes all expected model types."""
    from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

    assert hasattr(ModelFactory, "get_model")
    assert hasattr(ModelFactory, "get_checkpoint_name")

    # All required type constants exist
    for attr in ("TYPE_LEGACY", "TYPE_JEPA", "TYPE_VL_JEPA", "TYPE_RAP", "TYPE_ROLE_HEAD"):
        assert hasattr(ModelFactory, attr), f"ModelFactory missing {attr}"
