"""Packaging round (WP4c) — the bundle ships the factory models, the HLTV
seed, the coach book and alembic.ini exactly where the runtime looks for
them (D-32), and no test modules.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = PROJECT_ROOT / "packaging" / "cs2_analyzer_win.spec"


def _spec() -> str:
    return SPEC.read_text(encoding="utf-8")


def test_the_spec_ships_models_seed_book_and_alembic_ini():
    text = _spec()
    assert '"Programma_CS2_RENAN/models/global"' in text
    assert '.glob("*.pt*")' in text, "factory models are globbed at build time"
    assert (
        '(str(APP_DIR / "backend" / "storage" / "hltv_metadata.db"), "Programma_CS2_RENAN/backend/storage")'
        in text
    )
    assert (
        '(str(APP_DIR / "backend" / "knowledge" / "book"), "Programma_CS2_RENAN/backend/knowledge/book")'
        in text
    )
    assert '(str(PROJECT_ROOT / "alembic.ini"), ".")' in text


def test_the_spec_ships_the_svg_icon_sprite_where_the_provider_looks():
    # svg_icon_provider resolves design/assets/icons/sprite.svg from the
    # project root (= _MEIPASS when frozen); the first packaged run fell back
    # to QPainterPath icons because the sprite was not bundled.
    text = _spec()
    assert (
        '(str(PROJECT_ROOT / "design" / "assets" / "icons" / "sprite.svg"), "design/assets/icons")'
        in text
    )
    assert (PROJECT_ROOT / "design" / "assets" / "icons" / "sprite.svg").is_file()


def test_the_spec_leaves_the_test_suite_out_of_the_bundle():
    text = _spec()
    assert '"Programma_CS2_RENAN.tests"' in text.split("excludes=", 1)[1]
    assert 'startswith("Programma_CS2_RENAN.tests")' in text


def test_factory_model_path_matches_the_bundle_layout(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.backend.nn import persistence
    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(config, "IS_FROZEN", True)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    path = persistence.get_factory_model_path("jepa_v2_encoder")
    assert path == tmp_path / "Programma_CS2_RENAN" / "models" / "global" / "jepa_v2_encoder.pt"


def test_alembic_ini_and_hltv_seed_resolve_where_the_spec_puts_them(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.backend.storage import db_migrate
    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(config, "IS_FROZEN", True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    ini, scripts = db_migrate._alembic_paths()
    assert Path(ini) == tmp_path / "alembic.ini"
    assert Path(scripts) == tmp_path / "alembic"
    seed = config.get_resource_path(os.path.join("backend", "storage", "hltv_metadata.db"))
    assert (
        Path(seed) == tmp_path / "Programma_CS2_RENAN" / "backend" / "storage" / "hltv_metadata.db"
    )
